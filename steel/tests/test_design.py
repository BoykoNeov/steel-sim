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
from steel import grain
from steel import properties as prop
from steel.design import find_recipes, find_recipes_for_HRC, Recipe, _temper_to_target
from steel.design import find_yield_recipes, YieldRecipe, _austenitize_to_yield


# Re-evaluate a recipe through the FORWARD model — the independent check that a recipe really does
# what the inverse claims. Tempered ⇒ the per-constituent mixed-temper model applied to the *same*
# as-quenched fractions (the §16 unlock — a recipe may be a partial-martensite mixed temper, so the
# re-eval must temper the whole mixture, not assume full martensite); as-quenched ⇒ the full chain.
def _forward_HV(rec: Recipe) -> float:
    out = sweep.evaluate(rec.steel, medium=rec.medium, diameter=rec.diameter)
    if rec.tempered:
        Vr = out.Vr if np.isfinite(out.Vr) else None     # match sweep.evaluate's nan→None handling
        return prop.tempered_hardness_HV(out.fractions(), rec.steel.C, rec.temper_C, rec.t_hours,
                                         comp=rec.steel.minor(), Vr=Vr)
    return out.HV


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
# The pure-martensite mixture — the §16 generalization's Seam-A case: _temper_to_target over
# {martensite: 1.0} must reduce *exactly* to the old pure-martensite bisection (these three tests
# carry over the original solver content under the new mixture signature).
_PURE_M = {"martensite": 1.0}


def test_temper_bisection_recovers_interior_target():
    s = sweep.STEELS["4140"]                       # deep-hardening: a real martensitic start
    comp = s.minor()
    HV_aq = prop.vickers_martensite(s.C, comp=comp)
    HV_floor = prop.vickers_ferrite_pearlite(s.C, comp=comp)
    # An interior target, strictly between the floor and the as-quenched hardness.
    target = 0.5 * (HV_aq + HV_floor)
    T = _temper_to_target(_PURE_M, s.C, target, t_hours=1.0, comp=comp)
    assert T is not None
    # The recovered temper genuinely lands on the target (the inversion is faithful) ...
    assert prop.tempered_martensite_HV(s.C, T, 1.0, comp=comp) == pytest.approx(target, abs=0.5)
    # ... and sits in the physically sensible tempering range (softening onset → over-tempered).
    assert 150.0 < T < 700.0


def test_temper_bisection_is_monotone_inverse():
    # A harder target must need a LOWER temper than a softer one (the monotone-inverse sanity).
    s = sweep.STEELS["4140"]
    comp = s.minor()
    T_hard = _temper_to_target(_PURE_M, s.C, 520.0, 1.0, comp)
    T_soft = _temper_to_target(_PURE_M, s.C, 420.0, 1.0, comp)
    assert T_hard is not None and T_soft is not None
    assert T_hard < T_soft


def test_temper_infeasible_above_as_quenched_and_below_floor():
    s = sweep.STEELS["4140"]
    comp = s.minor()
    HV_aq = prop.vickers_martensite(s.C, comp=comp)
    HV_floor = prop.vickers_ferrite_pearlite(s.C, comp=comp)
    # Above as-quenched: you cannot temper a steel HARDER — honest infeasible (bracketing failure).
    assert _temper_to_target(_PURE_M, s.C, HV_aq + 100.0, 1.0, comp) is None
    # Below the spheroidite floor: you cannot soften past it — honest infeasible.
    assert _temper_to_target(_PURE_M, s.C, HV_floor - 50.0, 1.0, comp) is None


def test_temper_bisection_recovers_interior_target_for_a_mixture():
    # The §16 unlock: the bisection inverts a real partial-martensite MIXTURE, not just pure
    # martensite. 1045 water-quenched at 10 mm is ~0.88 martensite (the rest temper-inert FP/bainite);
    # an interior target between the as-quenched mixture and its over-tempered floor is recoverable,
    # and tempering the *whole mixture* at the solved T lands on it (the inert legs hold, only the
    # martensite leg softens). This is the new solver content the mixed-structure temper adds.
    s = sweep.STEELS["1045"]
    comp = s.minor()
    o = sweep.evaluate(s, medium="water", diameter=0.010)
    fracs = o.fractions()
    Vr = o.Vr if np.isfinite(o.Vr) else None
    assert fracs["martensite"] == pytest.approx(0.877, abs=0.03)       # a genuine mixture, not ~1.0
    HV_aq = prop.tempered_hardness_HV(fracs, s.C, 20.0, 1.0, comp=comp, Vr=Vr)      # sub-onset ceiling
    HV_floor = prop.tempered_hardness_HV(fracs, s.C, 760.0, 1.0, comp=comp, Vr=Vr)  # over-tempered floor
    target = 0.5 * (HV_aq + HV_floor)
    T = _temper_to_target(fracs, s.C, target, 1.0, comp, Vr)
    assert T is not None
    assert prop.tempered_hardness_HV(fracs, s.C, T, 1.0, comp=comp, Vr=Vr) == pytest.approx(target, abs=0.5)


# --------------------------------------------------------------------------- #
# 3. INFEASIBLE IS FIRST-CLASS — an empty set, never a nearest miss
# --------------------------------------------------------------------------- #
def test_out_of_envelope_target_returns_empty_set():
    # ~67 HRC bulk hardness (900 HV) exceeds every grade's achievable as-quenched hardness here.
    result = find_recipes(900.0, tol_HV=10.0, diameter=0.010)
    assert not result.feasible
    assert result.recipes == ()
    assert result.recommended is None


def test_high_retained_austenite_structure_is_not_offered_a_temper():
    # The §16 RA guard (the load-bearing scope edge now that the gate admits mixtures). 1080
    # water-quenched at 10 mm is martensite-DOMINANT (~0.78) but carries ~0.18 retained austenite —
    # above RA_TEMPER_MAX. RA is modelled temper-inert, which is exactly wrong there (RA → bainite /
    # fresh martensite on tempering can RAISE hardness), and this surface RECOMMENDS, so the search
    # must NOT offer a 1080 temper recipe (a confidently-wrong recommendation), even though it is
    # "above band". The honest hold-out, replacing Phase-7's "non-martensitic 1045" scope edge.
    s1080 = sweep.STEELS["1080"]
    o = sweep.evaluate(s1080, medium="water", diameter=0.010)
    assert o.fractions()["martensite"] >= design.MARTENSITE_TEMPER_MIN      # passes the dominance gate ...
    assert o.fractions()["retained_austenite"] > design.RA_TEMPER_MAX       # ... but the RA cap stops it
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    assert all(r.steel.name != "1080" for r in result.recipes)


def test_partial_martensite_grade_is_now_temperable():
    # The §16 unlock (the inverse of Phase-7's old scope edge): 1045 water at 10 mm is ~0.88
    # martensite with LOW retained austenite — so the per-constituent temper model now applies and
    # 1045 IS a feasible (tempered) recipe at 45 HRC, no longer dishonestly withheld. Its label flags
    # the partial-martensite mixed temper, and re-evaluating it through the forward model confirms it.
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    r1045 = [r for r in result.recipes if r.steel.name == "1045"]
    assert r1045, "1045 water-temper should now be feasible (the §16 mixed-structure unlock)"
    r = r1045[0]
    assert r.tempered and r.martensite < design.MARTENSITE_NEARLY_FULL     # a genuine partial-M temper
    assert "martensite" in r.label()                                       # the honesty cue is surfaced
    lo, hi = result.target_band
    assert lo <= _forward_HV(r) <= hi                                       # forward re-eval confirms it


def test_is_temperable_gate_dominance_and_RA_cap():
    # The gate unit test: martensite-DOMINANT and RA-CAPPED, both load-bearing.
    # 1080 oil is bainite-heavy (~0.24 martensite) → fails the dominance floor;
    # 1080 water is dominant (~0.78) but ~0.18 RA → fails the RA cap (the guard);
    # 1045 water (~0.88 M, ~0.03 RA) and 4140 oil (~0.96 M, ~0.04 RA) → temperable.
    ev = lambda g, m: sweep.evaluate(sweep.STEELS[g], medium=m, diameter=0.010)
    assert not design._is_temperable(ev("1080", "oil"))     # not martensite-dominant
    assert not design._is_temperable(ev("1080", "water"))   # dominant but high RA — the guard fires
    assert design._is_temperable(ev("1045", "water"))       # the unlocked partial-martensite mixture
    assert design._is_temperable(ev("4140", "oil"))         # the classic fully martensitic case


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
def test_feasible_set_is_cost_sorted():
    # The feasible set is cost-sorted (cheapest first) — including the §16-unlocked Biot-stretched
    # recipes, which keep their place in the ranking (surfaced honestly, not dropped).
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    assert result.feasible
    costs = [r.cost for r in result.recipes]
    assert costs == sorted(costs)                          # ascending


def test_recommended_is_the_cheapest_lumped_valid_recipe():
    # The §16 recommended re-derivation (Option B — the cheapest *lumped-valid* recipe, the §14
    # intent): the outright-cheapest recipe at 45 HRC / 10 mm is now a 1045 water-temper, but it is
    # Biot-stretched (Bi ≥ 0.1) — a recipe the model flags as outside its own 0-D validity must NOT be
    # headlined as the answer. `recommended` is the cheapest recipe that IS lumped-valid; the cheaper
    # Biot-stretched one stays in the set, flagged, but is not the recommendation.
    result = find_recipes_for_HRC(45.0, tol_HRC=2.0, diameter=0.010)
    valid = [r for r in result.recipes if r.lumped_valid]
    assert valid, "expected at least one lumped-valid recipe at this spec"
    assert result.recommended is valid[0]                 # cost-sorted ⇒ first valid = cheapest valid
    assert result.recommended.lumped_valid
    # And the outright-cheapest is cheaper but stretched — the honest capability the unlock surfaces.
    assert result.recipes[0].cost <= result.recommended.cost
    if not result.recipes[0].lumped_valid:
        assert result.recipes[0] is not result.recommended


def test_recommended_falls_back_to_cheapest_when_none_lumped_valid():
    # The fallback branch, exercised for real (not a guarded no-op): a 45 HRC target in a 30 mm
    # section is feasible but reachable ONLY by Biot-stretched quenches (4140 oil tips past Bi 0.1 at
    # this size), so NO recipe is lumped-valid. `recommended` then falls back to the outright cheapest
    # — still the best honest option, carrying its ⚠ flag, rather than None-on-feasible. Asserted
    # unconditionally: if the model ever shifts so a valid recipe appears here, this fails loudly
    # (the fallback case moved) instead of silently passing vacuous.
    result = find_recipes_for_HRC(45.0, tol_HRC=3.0, diameter=0.030)
    assert result.feasible
    assert not any(r.lumped_valid for r in result.recipes), \
        "precondition moved: this spec is meant to be feasible-but-all-Biot-stretched"
    assert result.recommended is result.recipes[0]         # the outright cheapest
    assert not result.recommended.lumped_valid             # ... carrying its ⚠ flag, honestly


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


# =========================================================================== #
# 7. PHASE 7 v2 — the yield-target inversion (FP slow-cool regime)
# =========================================================================== #
# Same harness posture: no new physics (this inverts grain.coupled_grain_properties), so these test
# the SOLVER, not metallurgy. The lead invariant is again "no recipe re-evaluates out of band"; the
# bisection tests carry the only real solver content; infeasible is first-class.

def _forward_yield(rec: YieldRecipe) -> float:
    """Re-run the FORWARD Phase-5 model on a yield recipe — the independent check it does what it claims."""
    return grain.coupled_grain_properties(
        rec.austenitize_T, rec.austenitize_t, rec.steel.C, comp=rec.steel.minor()).yield_MPa


# A target 370 MPa is feasible for several registry grades at once (1045/4140/8620 windows bracket
# it; 1080 sits entirely above), so it exercises multiple recipes and the cost sort.
def test_every_yield_recipe_reevaluates_in_band():
    result = find_yield_recipes(370.0, tol_MPa=15.0)
    lo, hi = result.target_band
    assert result.feasible
    for rec in result.recipes:
        assert lo <= rec.yield_MPa <= hi, f"reported {rec.yield_MPa:.1f} MPa out of band: {rec.label()}"
        # ... AND the forward Phase-5 model independently confirms the reported yield (no plumbing drift).
        assert rec.yield_MPa == pytest.approx(_forward_yield(rec), abs=0.5), rec.label()


def test_yield_bisection_recovers_interior_target():
    s = sweep.STEELS["1045"]                       # a clean FP-yield grade
    Y_hi = grain.coupled_grain_properties(design._AUSTENITIZE_T_LO, 1.0, s.C, comp=s.minor()).yield_MPa
    Y_lo = grain.coupled_grain_properties(design._AUSTENITIZE_T_HI, 1.0, s.C, comp=s.minor()).yield_MPa
    target = 0.5 * (Y_hi + Y_lo)                    # strictly interior
    T = _austenitize_to_yield(s, target, t_hours=1.0, N_free_pct=grain.DEFAULT_N_FREE_PCT, P_pct=0.0)
    assert T is not None
    got = grain.coupled_grain_properties(T, 1.0, s.C, comp=s.minor()).yield_MPa
    assert got == pytest.approx(target, abs=0.5)
    assert design._AUSTENITIZE_T_LO < T < design._AUSTENITIZE_T_HI


def test_yield_bisection_is_monotone_inverse():
    # yield(T) decreasing ⇒ a HIGHER yield target needs a LOWER (cooler, finer-grain) austenitize.
    s = sweep.STEELS["1045"]
    kw = dict(t_hours=1.0, N_free_pct=grain.DEFAULT_N_FREE_PCT, P_pct=0.0)
    T_strong = _austenitize_to_yield(s, 430.0, **kw)
    T_weak = _austenitize_to_yield(s, 370.0, **kw)
    assert T_strong is not None and T_weak is not None
    assert T_strong < T_weak


def test_yield_target_outside_every_grade_envelope_is_infeasible():
    # Above the strongest grade's finest-grain ceiling (1080 ≈ 519 MPa) ⇒ empty; and below the
    # weakest grade's coarsest-grain floor (8620 ≈ 298 MPa) ⇒ empty. Honest infeasible, not a miss.
    assert find_yield_recipes(600.0, tol_MPa=15.0).recipes == ()
    assert find_yield_recipes(250.0, tol_MPa=15.0).recipes == ()


def test_yield_recipe_carries_no_quench_regime_fields():
    # The regime-separation guard: a yield recipe is grade + austenitize under a normalized cool —
    # it must NOT carry the martensitic Recipe's quench medium / temper / Biot (conflating the two
    # regimes is the one way this surface would lie about what it solved).
    rec = find_yield_recipes(370.0).recipes[0]
    assert isinstance(rec, YieldRecipe) and not isinstance(rec, Recipe)
    for absent in ("medium", "temper_C", "biot", "HV", "HRC"):
        assert not hasattr(rec, absent), f"yield recipe should not carry quench-regime field {absent!r}"


def test_yield_recommended_is_cheapest_feasible():
    result = find_yield_recipes(370.0, tol_MPa=15.0)
    assert result.feasible
    assert result.recommended is result.recipes[0]                 # cost-sorted head
    assert all(result.recommended.cost <= r.cost for r in result.recipes)


def test_yield_dbtt_co_property_is_the_same_phase5_call():
    # The carried DBTT is exactly the coupled forward call's DBTT (the §5b foil reported for free).
    rec = find_yield_recipes(370.0).recipes[0]
    gp = grain.coupled_grain_properties(rec.austenitize_T, rec.austenitize_t, rec.steel.C,
                                        comp=rec.steel.minor())
    assert rec.dbtt_C == pytest.approx(gp.dbtt_C, abs=1e-6)
