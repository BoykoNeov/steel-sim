"""Harness tests for the experimentation surface (``sweep.py``).

``sweep.py`` adds **no new physics** — it re-composes modules each sealed behind its own
validation triad. So these tests do not re-validate the physics; they validate the
*harness*, and the discipline mirrors the rest of the project:

  * **Cross-consistency** (the load-bearing leg). A steel's one composition object must
    reach **both** faces of the model — the kinetics (the hardenability ``τ``-shift and
    Andrews Mₛ) *and* the hardness (the Maynier minor-alloy delta) — from a single
    :meth:`Steel.minor` dict. The "exact re-composition" check is near-tautological (same
    code, same inputs); its only teeth are that both faces actually received the comp.
  * **Monotone trends** — the experimentation payoff, asserted *qualitatively* (robust, not
    brittle exact numbers, like ``test_demo_four_curves``), and **in HV** (defined
    everywhere) not HRC (``nan`` below ~20 HRC, exactly for the lean steels that make the
    composition axis interesting).
  * **The 0-D discrimination lesson** — at a fixed medium every steel sees the *same*
    cooling path (composition does not move the lumped ``T(t)``), so an alloy-hardenability
    trend only speaks at an *intermediate* medium; at the saturated ends (water/furnace)
    steels are identical. A test that read the alloy trend at water would assert nothing.
  * **Conservation passthrough** + **Biot honesty** (the model flags where it is stretched).
"""
import math
import warnings

import numpy as np
import pytest

from projects.steel import sweep
from projects.steel import properties as prop
from projects.steel.kinetics import ccurve_for_steel, hardenability_factor, andrews_Ms
from projects.steel.sweep import (
    Steel, STEELS, evaluate, cooling_rate_sweep, composition_sweep, sweep_grid, temper_sweep,
)


# --------------------------------------------------------------------------- #
# 1. Cross-consistency — one composition reaches BOTH the kinetics and the hardness
# --------------------------------------------------------------------------- #
def test_one_composition_threads_into_both_kinetics_and_hardness():
    # The single most load-bearing harness property: Steel.minor() must drive BOTH faces.
    s = STEELS["4140"]
    out = evaluate(s, medium="oil")

    # Kinetics face: the C-curve carries this comp's hardenability shift and Andrews Mₛ.
    assert out.ccurve.tau_factor == pytest.approx(
        hardenability_factor(Mn=s.Mn, Ni=s.Ni, Cr=s.Cr, Mo=s.Mo, Si=s.Si)
    )
    assert out.ccurve.Ms == pytest.approx(andrews_Ms(s.C, Mn=s.Mn, Ni=s.Ni, Cr=s.Cr, Mo=s.Mo))
    assert out.ccurve.tau_factor > 1.5                       # 4140 is genuinely shifted right

    # Hardness face: the SAME comp raised the hardness (Maynier minor-alloy delta fired).
    Vr = float(out.Vr)
    hv_with = prop.hardness_HV(out.fractions(), s.C, comp=s.minor(), Vr=Vr)
    hv_without = prop.hardness_HV(out.fractions(), s.C, comp=None, Vr=Vr)
    assert out.HV == pytest.approx(hv_with)                  # the outcome used the comp
    assert hv_with > hv_without                              # and the comp actually changed it


def test_evaluate_is_exact_recomposition():
    # The wiring smoke-test: evaluate() == the hand-wired pipeline, byte-for-byte. Near
    # tautological (it IS the same calls) — it guards against the harness silently dropping
    # a step or an argument, not against a physics error.
    from projects.steel import cooling, pathint
    s = STEELS["1045"]
    out = evaluate(s, medium="oil")

    cc = ccurve_for_steel(s.C, Mn=s.Mn, Ni=s.Ni, Cr=s.Cr, Mo=s.Mo, Si=s.Si)
    path = cooling.cooling_path("oil", T0=850.0, T_env=25.0,
                                diameter=sweep.STANDARD_DIAMETER, warn_biot=False)
    result = pathint.transform_along_path(path.t, path.T, cc)
    Vr = path.cooling_rate() * prop.SECONDS_PER_HOUR
    Vr_arg = float(Vr) if np.isfinite(Vr) else None
    HV = prop.hardness_HV(result.fractions(), s.C, comp=s.minor(), Vr=Vr_arg)

    assert out.HV == HV
    assert out.fractions() == result.fractions()
    assert out.ccurve.tau_factor == cc.tau_factor and out.ccurve.Ms == cc.Ms


# --------------------------------------------------------------------------- #
# 2. Conservation passthrough — the four fractions still partition the austenite
# --------------------------------------------------------------------------- #
def test_fractions_sum_to_one_across_a_grid():
    grid = sweep_grid(["1045", "1080", "4140"], media=sweep.DEFAULT_MEDIA)
    for row in grid:
        for out in row:
            assert sum(out.fractions().values()) == pytest.approx(1.0, abs=1e-12)


# --------------------------------------------------------------------------- #
# 3. The cooling-rate axis — faster quench, harder steel (the dramatic axis)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("grade", ["1080", "4140"])
def test_hardness_rises_monotonically_with_quench_severity(grade):
    # furnace → air → oil → water: more severe quench → more martensite → harder. Asserted
    # in HV (defined everywhere; the slow end of a lean steel is off the HRC scale).
    outs = cooling_rate_sweep(STEELS[grade])
    assert [o.medium for o in outs] == list(sweep.DEFAULT_MEDIA)
    HV = [o.HV for o in outs]
    martensite = [o.result.martensite for o in outs]
    assert HV == sorted(HV)                                  # non-decreasing furnace → water
    assert martensite == sorted(martensite)                 # martensite only ever increases
    assert HV[-1] - HV[0] > 100.0                            # a genuinely dramatic span


def test_continuous_cooling_rate_axis_via_raw_h():
    # The cooling-rate axis is continuous, not just the four presets: a raw h (W/m²·K) works,
    # and a stronger h cools faster (higher Vr) → at least as hard.
    soft = evaluate(STEELS["4140"], medium=50.0)
    hard = evaluate(STEELS["4140"], medium=2000.0)
    assert hard.Vr > soft.Vr
    assert hard.HV >= soft.HV


# --------------------------------------------------------------------------- #
# 4. The composition axis — alloy hardenability, read at a discriminating point
# --------------------------------------------------------------------------- #
def test_alloy_hardens_deeper_at_an_intermediate_medium():
    # The 0-D discrimination lesson: at OIL (intermediate) the deep-hardening alloy keeps far
    # more martensite than the lean steel — the hardenability divergence. Both ~0.4 %C, so
    # this is the C-curve shift speaking, not carbon.
    lean, alloy = composition_sweep(["1045", "4140"], medium=sweep.DISCRIMINATING_MEDIUM)
    assert alloy.result.martensite > lean.result.martensite + 0.3
    assert alloy.HV > lean.HV


def test_saturated_ends_do_not_discriminate_composition():
    # The other half of the lesson: the *slow* (furnace) end saturates — both steels go fully
    # ferrite+pearlite (martensite ≈ 0, soft, near-identical HV), so composition says ~nothing
    # there. The *fast* (water) end is now only *nearly* saturated: both are mostly martensitic,
    # but the shallow 1045 forms a little proeutectoid ferrite even at water (Phase 6a — it does
    # not fully through-harden a 10 mm section; and water on that section is already the 0-D
    # model's stretched Biot > 0.1 regime), so it reads marginally *softer* than the deep 4140
    # (~20 HV), not harder. Either way the trend is cleanest read in the middle (oil).
    lean, alloy = composition_sweep(["1045", "4140"], medium="furnace")
    assert lean.result.martensite == pytest.approx(alloy.result.martensite, abs=0.05)  # both ≈ 0
    assert lean.HV == pytest.approx(alloy.HV, abs=15.0)                                 # both soft FP
    lean, alloy = composition_sweep(["1045", "4140"], medium="water")
    assert lean.result.martensite == pytest.approx(alloy.result.martensite, abs=0.1)    # both mostly martensitic
    assert lean.HV == pytest.approx(alloy.HV, abs=25.0)                                 # 1045 marginally softer (a little α)


# --------------------------------------------------------------------------- #
# 5. The carbon axis — clean kinetic + hardness consequences (no mixed-structure noise)
# --------------------------------------------------------------------------- #
def test_carbon_lowers_Ms_and_raises_martensite_hardness():
    carbons = [0.2, 0.4, 0.6, 0.8]
    Ms = [evaluate(Steel(C=C)).ccurve.Ms for C in carbons]
    # Andrews Mₛ falls with carbon (carbon threaded into the kinetics face).
    assert Ms == sorted(Ms, reverse=True)
    # As-quenched martensite hardness rises with carbon (the √C curve, via the harness) —
    # read on the pure-martensite hardness (temper sweep's left limit), free of the
    # retained-austenite noise a mixed water-quench outcome would carry at high C.
    HV_aq = [temper_sweep(Steel(C=C)).HV_as_quenched for C in carbons]
    assert HV_aq == sorted(HV_aq)
    assert HV_aq[-1] > HV_aq[0] + 200.0


# --------------------------------------------------------------------------- #
# 6. The tempering axis — softening, the strength/toughness trade-off, alloy resistance
# --------------------------------------------------------------------------- #
def test_tempering_softens_and_trades_strength_for_toughness():
    tr = temper_sweep(STEELS["4140"], t_hours=1.0)
    # Hollomon–Jaffe P rises with tempering temperature; hardness falls monotonically.
    assert np.all(np.diff(tr.P) > 0)
    assert np.all(np.diff(tr.HV) <= 0)
    # The trade-off: toughness rises as the steel softens (opposite direction to hardness).
    assert np.all(np.diff(tr.toughness) >= 0)
    # The left limit (100 °C/1 h is a sub-onset temper) is the as-quenched value exactly —
    # the byte-exact seam properties.py guarantees below the softening onset.
    assert tr.HV[0] == pytest.approx(tr.HV_as_quenched)
    # Strength tracks hardness where the ISO-18265 band applies (it is nan for the hardest
    # untempered end — above ~550 HV — by design); where both are defined, UTS falls too.
    uts = tr.UTS_MPa
    defined = np.isfinite(uts)
    assert defined.sum() >= 3
    assert np.all(np.diff(uts[defined]) < 0)


def test_alloy_steel_resists_tempering():
    # Emergent (not a fitted term): threading comp through both master-curve endpoints makes
    # the alloy steel stay harder than a plain steel of the same carbon at EVERY temper.
    alloy = temper_sweep(STEELS["4140"], t_hours=1.0)
    plain = temper_sweep(Steel(C=0.40), t_hours=1.0)
    assert np.all(alloy.HV >= plain.HV)
    assert alloy.HV_as_quenched > plain.HV_as_quenched


def test_time_temperature_equivalence_passes_through():
    # The validated form of the Hollomon–Jaffe parameter survives the harness: a hotter,
    # shorter temper that lands on the same P gives the same hardness (same node on the curve).
    # P = T_K·(20 + log10 t): 540 °C/1 h and 466 °C/100 h land on (nearly) the same P, so
    # the hotter-shorter temper substitutes for the cooler-longer one — equal hardness.
    s = STEELS["4140"]
    a = temper_sweep(s, temper_C=[540.0], t_hours=1.0)
    b = temper_sweep(s, temper_C=[466.0], t_hours=100.0)
    assert a.P[0] == pytest.approx(b.P[0], rel=0.01)
    assert a.HV[0] == pytest.approx(b.HV[0], rel=0.02)


# --------------------------------------------------------------------------- #
# 7. Biot honesty + the registry's real compositions
# --------------------------------------------------------------------------- #
def test_biot_flag_is_carried_and_no_warning_is_emitted():
    thin = evaluate(STEELS["1045"], medium="furnace", diameter=0.005)
    thick = evaluate(STEELS["1045"], medium="water", diameter=0.05)
    assert thin.lumped_valid and thin.biot < 0.1
    assert not thick.lumped_valid and thick.biot >= 0.1
    # A multi-node sweep must stay quiet (warn_biot=False) even where it is stretched —
    # it reports Biot in the data, it does not spew one warning per call.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        evaluate(STEELS["1045"], medium="water", diameter=0.05)
        sweep_grid(["1045", "4140"], media=("water",), diameter=0.05)


def test_registry_1080_is_the_calibrated_reference_steel():
    # The registry ships REAL compositions (not the Mn=0 "leaner hypothetical" trap): 1080 is
    # the kinetics' reference steel, so its hardenability shift is exactly identity.
    assert evaluate(STEELS["1080"]).ccurve.tau_factor == pytest.approx(1.0)
    # And a bare carbon-only Steel(0.80) is the leaner steel the docs warn about — a faster
    # nose (M < 1), distinct from the reference: the registry exists precisely to avoid it.
    assert evaluate(Steel(C=0.80)).ccurve.tau_factor < 1.0


def test_sweep_grid_shape_and_indexing():
    steels = ["1045", "4140"]
    media = ("air", "oil", "water")
    grid = sweep_grid(steels, media=media)
    assert len(grid) == len(steels)
    assert all(len(row) == len(media) for row in grid)
    # grid[i][j] is steel i in medium j.
    assert grid[0][0].steel.name == "1045" and grid[0][0].medium == "air"
    assert grid[1][2].steel.name == "4140" and grid[1][2].medium == "water"
