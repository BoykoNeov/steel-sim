"""Harness tests for the inverse-design surface (``design.py``, Steel Phase 7).

``design.py`` adds **no new physics** — it inverts the validated forward chain (``sweep.evaluate``
+ ``properties.tempered_martensite_HV``). So, exactly like ``test_sweep.py``, these tests do **not**
re-validate metallurgy; they validate the *harness / solver*, with the project's discipline:

  * **The lead invariant (the strongest assertion):** *no returned recipe ever re-evaluates
    out-of-band.* Every recipe in a feasible set, re-run through the forward model, lands in the
    target band. If the inverse ever returns a recipe that does not actually meet the spec, this
    fails — the one bug that would make the whole surface dishonest.
  * **The temper root-find (the only test with real solver content):** the bisection recovers an
    interior target to tolerance and reports honest *infeasible* (a bracketing failure) above
    as-quenched / below the spheroidite floor.
  * **Infeasible is first-class** — an out-of-envelope target returns an **empty** set, not a
    silent nearest-miss.
  * **Round-trip / alloy-ranking are wiring checks, NOT teeth** — labelled by-construction (they
    pass because the forward model already encodes the answer; the Phase-4 "pinned-invariant"
    status), kept as smoke tests, not dressed as benchmarks.
"""
import numpy as np
import pytest

from steel import design
from steel import sweep
from steel import properties as prop
from steel.design import find_recipes, find_recipes_for_HRC, Recipe, _temper_to_target


# Re-evaluate a recipe through the FORWARD model — the independent check that a recipe really does
# what the inverse claims. Tempered ⇒ the martensite-only temper model; as-quenched ⇒ the full chain.
def _forward_HV(rec: Recipe) -> float:
    if rec.tempered:
        return prop.tempered_martensite_HV(rec.steel.C, rec.temper_C, rec.t_hours,
                                           comp=rec.steel.minor())
    return sweep.evaluate(rec.steel, medium=rec.medium, diameter=rec.diameter).HV


# A spread of (target_HV, tol_HV, diameter) specs that between them exercise as-quenched feasibility,
# the temper branch, multiple grades, and several section sizes.
_SPECS = [
    (300.0, 25.0, 0.010),
    (446.0, 25.0, 0.010),     # ~45 HRC, the demo spec
    (513.0, 20.0, 0.010),     # ~50 HRC
    (446.0, 25.0, 0.030),     # same target, thick section (Biot-stretched territory)
    (350.0, 30.0, 0.020),
]


# --------------------------------------------------------------------------- #
# 1. THE LEAD INVARIANT — no returned recipe ever re-evaluates out-of-band
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("target_HV, tol_HV, diameter", _SPECS)
def test_every_feasible_recipe_reevaluates_in_band(target_HV, tol_HV, diameter):
    result = find_recipes(target_HV, tol_HV=tol_HV, diameter=diameter)
    lo, hi = result.target_band
    for rec in result.recipes:
        # (a) the reported hardness is in band ...
        assert lo <= rec.HV <= hi, f"reported {rec.HV:.1f} HV outside [{lo:.1f}, {hi:.1f}]: {rec.label()}"
        # (b) ... AND re-running the forward model independently confirms it (the real teeth of the
        # harness: the reported number is not a fiction, it is what the forward chain produces).
        assert lo <= _forward_HV(rec) <= hi, f"forward re-eval out of band: {rec.label()}"
        # The HRC reading is the table conversion of HV (or nan off-scale) — consistent, not invented.
        assert np.isnan(rec.HRC) or rec.HRC == pytest.approx(prop.vickers_to_rockwell_c(rec.HV))


def test_reported_HV_matches_forward_model_exactly():
    # Stronger than "in band": the reported HV IS the forward model's output (no drift in plumbing).
    result = find_recipes(446.0, tol_HV=25.0, diameter=0.010)
    assert result.feasible
    for rec in result.recipes:
        assert rec.HV == pytest.approx(_forward_HV(rec), abs=1.0)


# --------------------------------------------------------------------------- #
# 2. THE TEMPER ROOT-FIND — the only test with real solver content
# --------------------------------------------------------------------------- #
def test_temper_bisection_recovers_interior_target():
    s = sweep.STEELS["4140"]                       # deep-hardening: a real martensitic start
    comp = s.minor()
    HV_aq = prop.vickers_martensite(s.C, comp=comp)
    HV_floor = prop.vickers_ferrite_pearlite(s.C, comp=comp)
    # An interior target, strictly between the floor and the as-quenched hardness.
    target = 0.5 * (HV_aq + HV_floor)
    T = _temper_to_target(s.C, target, t_hours=1.0, comp=comp)
    assert T is not None
    # The recovered temper genuinely lands on the target (the inversion is faithful) ...
    assert prop.tempered_martensite_HV(s.C, T, 1.0, comp=comp) == pytest.approx(target, abs=0.5)
    # ... and sits in the physically sensible tempering range (softening onset → over-tempered).
    assert 150.0 < T < 700.0


def test_temper_bisection_is_monotone_inverse():
    # A harder target must need a LOWER temper than a softer one (the monotone-inverse sanity).
    s = sweep.STEELS["4140"]
    comp = s.minor()
    T_hard = _temper_to_target(s.C, 520.0, 1.0, comp)
    T_soft = _temper_to_target(s.C, 420.0, 1.0, comp)
    assert T_hard is not None and T_soft is not None
    assert T_hard < T_soft


def test_temper_infeasible_above_as_quenched_and_below_floor():
    s = sweep.STEELS["4140"]
    comp = s.minor()
    HV_aq = prop.vickers_martensite(s.C, comp=comp)
    HV_floor = prop.vickers_ferrite_pearlite(s.C, comp=comp)
    # Above as-quenched: you cannot temper a steel HARDER — honest infeasible (bracketing failure).
    assert _temper_to_target(s.C, HV_aq + 100.0, 1.0, comp) is None
    # Below the spheroidite floor: you cannot soften past it — honest infeasible.
    assert _temper_to_target(s.C, HV_floor - 50.0, 1.0, comp) is None


# --------------------------------------------------------------------------- #
# 3. INFEASIBLE IS FIRST-CLASS — an empty set, never a nearest miss
# --------------------------------------------------------------------------- #
def test_out_of_envelope_target_returns_empty_set():
    # ~67 HRC bulk hardness (900 HV) exceeds every grade's achievable as-quenched hardness here.
    result = find_recipes(900.0, tol_HV=10.0, diameter=0.010)
    assert not result.feasible
    assert result.recipes == ()
    assert result.recommended is None


def test_non_martensitic_above_band_is_not_offered_a_temper():
    # 1045 water-quenched at 10 mm is only ~0.88 martensite (below MARTENSITE_TEMPER_MIN), so the
    # martensite-only temper model does NOT apply — the honest scope edge. It must be absent from the
    # 45-HRC feasible set even though it is "above band", not silently tempered as if fully martensitic.
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    assert all(not (r.steel.name == "1045") for r in result.recipes)


# --------------------------------------------------------------------------- #
# 4. ROUND-TRIP / ALLOY-RANK — wiring checks, NOT teeth (labelled by-construction)
# --------------------------------------------------------------------------- #
def test_round_trip_recovers_a_known_recipe_by_construction():
    # WIRING CHECK (passes by construction — the Phase-4 "pinned invariant" status, NOT a benchmark):
    # a grade's OWN forward hardness is recoverable from the grid it lives in.
    s = sweep.STEELS["4140"]
    known = sweep.evaluate(s, medium="oil", diameter=0.010)        # 4140 oil → its as-quenched HV
    result = find_recipes(known.HV, tol_HV=15.0, diameter=0.010)
    assert any(r.steel.name == "4140" and r.medium == "oil" and not r.tempered for r in result.recipes)


def test_alloy_outranks_carbon_for_a_deep_section_target():
    # CONSISTENCY CHECK (by construction from the forward model, which already encodes 4140's
    # hardenability — NOT a falsifiable result): in a section deep enough that plain-carbon's
    # shallow hardenability gives out (40 mm — at 25 mm a 1045 water quench still lands a 50/50
    # martensite mix in band), only the alloy grade can reach a hard target. The inverse search
    # reproducing this is the textbook "deep section ⇒ alloy steel" fact, end-to-end.
    result = find_recipes_for_HRC(45.0, tol_HRC=3.0, diameter=0.040)
    grades = {r.steel.name for r in result.recipes}
    assert "4140" in grades
    assert "1045" not in grades


# --------------------------------------------------------------------------- #
# 5. THE RESULT SHAPE — sorting, cost, Biot honesty, input flexibility
# --------------------------------------------------------------------------- #
def test_feasible_set_is_cost_sorted_and_recommended_is_cheapest():
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    assert result.feasible
    costs = [r.cost for r in result.recipes]
    assert costs == sorted(costs)                          # ascending
    assert result.recommended is result.recipes[0]
    assert result.recommended.cost == min(costs)


def test_recommended_demo_recipe_is_4140_oil_temper():
    # The banked demo's headline (a regression guard on the recommendation, not a physics claim):
    # to reach ~45 HRC in a 10 mm section the cheapest lumped-VALID recipe is oil-quench-and-temper.
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    rec = result.recommended
    assert rec.steel.name == "4140" and rec.medium == "oil" and rec.tempered
    assert rec.lumped_valid                                # oil at 10 mm is inside Bi < 0.1


def test_cost_prefers_milder_quench_leaner_alloy_no_temper():
    s = sweep.STEELS["1045"]
    # Milder quench ⇒ lower cost (same steel, no temper).
    assert design._recipe_cost(s, "oil", None) < design._recipe_cost(s, "water", None)
    assert design._recipe_cost(s, "air", None) < design._recipe_cost(s, "oil", None)
    # More alloy ⇒ higher cost (same quench).
    assert design._recipe_cost(sweep.STEELS["1045"], "oil", None) < \
           design._recipe_cost(sweep.STEELS["4140"], "oil", None)
    # An extra temper step costs more than as-quenched (same grade/quench).
    assert design._recipe_cost(s, "oil", None) < design._recipe_cost(s, "oil", 400.0)


def test_biot_flag_propagates_to_recipes():
    # A 30 mm water quench exceeds lumped validity (Bi > 0.1); any recipe built on it must say so.
    result = find_recipes_for_HRC(45.0, tol_HRC=3.0, diameter=0.030)
    water = [r for r in result.recipes if r.medium == "water"]
    assert water, "expected at least one water-quench recipe at this thick-section target"
    assert all(not r.lumped_valid for r in water)


def test_grades_accepts_keys_and_objects_equivalently():
    by_key = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010, grades=["4140"])
    by_obj = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010, grades=[sweep.STEELS["4140"]])
    assert [r.label() for r in by_key.recipes] == [r.label() for r in by_obj.recipes]


def test_find_recipes_for_HRC_rejects_unconvertible_band():
    # Below ~20 HRC Rockwell-C is undefined ⇒ converting the band edge is nan ⇒ the wrapper refuses
    # (the honest "give the target in HV for soft material"), not a nan-poisoned search.
    with pytest.raises(ValueError):
        find_recipes_for_HRC(10.0, tol_HRC=2.0, diameter=0.010)
