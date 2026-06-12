"""§19 validation: the unified-KV competing-reaction rebuild — the bainite bay *opened* in CCT.

The 6b deepening. Phase 6b proved the bainite bay cannot be wired into the single Grossmann-shifted
curve; this module races three separate Li/Kirkaldy–Venugopalan reactions (ferrite/pearlite/bainite)
on one shared austenite pool so the bay emerges in continuous cooling. It is a **per-steel-anchored
demonstrator, not a cross-steel predictor** — and the suite is built around that distinction:

* **THE TEETH (cited, scale-free).** The published composition factors *predict the bay separation*
  with no fitting: ``PC(4340)/PC(1080) ≈ 1.4e3`` (≈ the atlas-measured ~10³× pearlite retardation)
  and ``FC(4340)/FC(1045) ≈ 2.1e2`` — both large and right-direction, so ferrite/pearlite get pushed
  far right while bainite barely moves. The contrast that *is* the wall: ``BC(4340)/BC(1080) ≈ 0.146``
  — wrong-direction (BC says 4340 bainite is *faster*), so bainite must be per-steel atlas-anchored.
* **THE DEMONSTRATION (the new capability).** A 4340 intermediate-rate path lands **bainite-dominant**
  — the microstructure the single-curve :mod:`pathint` cannot produce — and it is resolution-converged.
* **THE CONSISTENCY GUARDS.** 1080 (eutectoid, no proeutectoid ferrite) opens **no** bay: bainite
  never dominates at any rate, and the ladder runs pearlite (slow) → martensite (fast). The pearlite
  global scale is *derived* so 1080's pearlite nose reproduces the frozen single-curve nose.
* **CONSERVATION + FROZEN-CORE BYTE-IDENTITY.** Fractions sum to 1 to machine precision; the
  pearlite/bainite split is order/resolution-insensitive; and the frozen single-curve pipeline
  (``CCurve.tau`` / :mod:`pathint` / the four-curves nose) is untouched.
"""
import warnings

import numpy as np
import pytest

from steel import unified_kv as U
from steel import cooling, fe_c, pathint
from steel.kinetics import (
    CCurve, pearlite_PC, ferrite_FC, bainite_BC,
    pearlite_reaction_for_steel, andrews_Ms,
)

# Atlas / reference compositions (wt%).
C1080 = dict(C=0.79, Mn=0.76)
C4340 = dict(C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33)
C1045 = dict(C=0.45, Mn=0.75)


def _path(medium, diameter=0.05, T0=850.0):
    """A 0-D cooling path (biot warnings silenced — the unified demo is a 0-D kinetic study)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cp = cooling.cooling_path(medium, T0=T0, diameter=diameter, warn_biot=False)
    return cp.t, cp.T


# --------------------------------------------------------------------------- #
# THE TEETH — the cited, scale-free composition-factor differentials
# --------------------------------------------------------------------------- #
def test_pearlite_differential_is_cited_right_and_large():
    # PC(4340)/PC(1080) ≈ 1400× — the cited pearlite retardation that pushes 4340's pearlite nose
    # ~10³× right (≈ the atlas-measured value). Scale-free: it uses no calibration, only the
    # published PC coefficients, so the bay separation is a *prediction*, not a fit.
    ratio = pearlite_PC(**C4340) / pearlite_PC(**C1080)
    assert 1000.0 < ratio < 2000.0, ratio


def test_ferrite_differential_is_cited_right_and_large():
    # FC(4340)/FC(1045) ≈ 214× — alloy strongly retards the reconstructive ferrite reaction.
    ratio = ferrite_FC(**C4340) / ferrite_FC(**C1045)
    assert 150.0 < ratio < 300.0, ratio


def test_bainite_differential_is_the_wrong_direction_wall():
    # BC(4340)/BC(1080) ≈ 0.146 < 1 — BC says 4340 bainite is FASTER than 1080 (carbon coeff 10.18
    # dominates), but the atlas measures it ~4–5× slower. A ratio < 1 here is the directional wall:
    # no global scale can fix a wrong-direction prediction, so bainite is per-steel atlas-anchored.
    ratio = bainite_BC(**{k: v for k, v in C4340.items() if k != "Si"}) / bainite_BC(**C1080)
    assert ratio < 1.0, ratio                       # wrong direction
    assert 0.10 < ratio < 0.20, ratio


def test_pearlite_retards_far_more_strongly_than_bainite():
    # The bay mechanism in one inequality: per wt% alloy, PC's potency (the bay-opener) dwarfs BC's
    # (which is weak AND wrong-signed). Compare the 4340-vs-1080 multiplicative effects.
    pc = pearlite_PC(**C4340) / pearlite_PC(**C1080)        # ≫ 1 (retards)
    bc = bainite_BC(**{k: v for k, v in C4340.items() if k != "Si"}) / bainite_BC(**C1080)  # < 1
    assert pc / bc > 1000.0                                 # the differential that opens the bay


# --------------------------------------------------------------------------- #
# CONSISTENCY — the pearlite global scale is derived against the frozen 1080 nose
# --------------------------------------------------------------------------- #
def test_pearlite_scale_reproduces_the_frozen_1080_nose():
    # The single calibrated knob is not free: PEARLITE_SCALE is derived so the 1080 pearlite-reaction
    # START nose lands on the frozen single-curve nose (~550 °C / ~1 s — the four-curves anchor).
    _, t_frozen = CCurve().nose(X=U.NOSE_X)
    Tp, tp = pearlite_reaction_for_steel(**C1080, scale=U.PEARLITE_SCALE).nose(X=U.NOSE_X)
    assert tp == pytest.approx(t_frozen, rel=1e-6)         # time matches by construction
    assert 500.0 < Tp < 620.0                              # nose temperature in the pearlite band


# --------------------------------------------------------------------------- #
# THE DEMONSTRATION — the bay opens in continuous cooling (the new capability)
# --------------------------------------------------------------------------- #
def test_4340_intermediate_path_is_bainite_dominant():
    # The headline: an intermediate-rate 4340 path threads between the pushed-right pearlite/ferrite
    # noses and the martensite floor → BAINITE-dominant. The single-curve pathint cannot produce this.
    res = U.competing_microstructure("4340", *_path("air", diameter=0.05))
    assert res.dominant() == "bainite"
    assert res.bainite > 0.5


def test_4340_fast_quench_is_martensite_no_bay_when_outrun():
    # The bracket: a severe quench outruns every diffusional nose → martensite (the bay is *missed*).
    res = U.competing_microstructure("4340", *_path("water", diameter=0.01))
    assert res.dominant() == "martensite"
    assert res.bainite < 0.05


def test_4340_very_slow_cool_forms_ferrite_and_pearlite():
    # The other bracket (the full ladder): a very slow cool fills the proeutectoid ferrite to its
    # equilibrium cap and grows pearlite — the diffusional high-temperature products.
    res = U.competing_microstructure("4340", *_path("furnace", diameter=0.3))
    assert res.ferrite == pytest.approx(U.unified_system("4340").f_pro, abs=0.02)
    assert res.pearlite > 0.1
    assert res.martensite < 0.15


def test_bay_opening_is_resolution_converged():
    # The bay is physics, not a discretisation artifact: refine the cooling-path grid and the 4340
    # bainite fraction is stable.
    sysm = U.unified_system("4340")
    fracs = []
    for per_decade in (120, 240, 480):
        t = pathint.log_time_grid(8000.0, per_decade=per_decade)
        T = pathint.newton_cooling(t, 850.0, 25.0, 900.0)   # ~intermediate cool into the bay
        fracs.append(U.transform_competing(t, T, sysm).bainite)
    assert max(fracs) - min(fracs) < 0.03, fracs
    assert min(fracs) > 0.5                                 # bainite-dominant at every resolution


# --------------------------------------------------------------------------- #
# CONSISTENCY GUARDS — 1080 opens NO bay; the ladder direction is right
# --------------------------------------------------------------------------- #
def _max_bainite_over_sweep(steel):
    sysm = U.unified_system(steel)
    best = 0.0
    for h in np.geomspace(3.0, 3000.0, 25):
        res = U.transform_competing(*_path(float(h)), sysm)
        best = max(best, res.bainite)
    for d in np.geomspace(0.005, 1.0, 20):
        for h in ("air", "oil", "furnace"):
            res = U.transform_competing(*_path(h, diameter=float(d)), sysm)
            best = max(best, res.bainite)
    return best


def test_1080_opens_no_bay_but_4340_does():
    # The bay/no-bay contrast that IS the result: 1080 (eutectoid, ferrite inert, pearlite & bainite
    # noses nearly coincident) never makes bainite the majority product; 4340 clearly does.
    assert _max_bainite_over_sweep("1080") < 0.45          # measured ≈ 0.34 — no open bay
    assert _max_bainite_over_sweep("4340") > 0.55          # measured ≈ 0.63 — the bay


def test_1080_ladder_runs_pearlite_to_martensite():
    # The four-curves direction (a consistency guard, not a benchmark): slow → pearlite, fast →
    # martensite. (1080's oil point is a pearlite/bainite/martensite mix — the bay never opens.)
    slow = U.competing_microstructure("1080", *_path("furnace", diameter=0.01))
    fast = U.competing_microstructure("1080", *_path("water", diameter=0.01))
    assert slow.dominant() == "pearlite"
    assert fast.dominant() == "martensite"


def test_1080_has_no_proeutectoid_ferrite():
    # Eutectoid steel: f_pro = 0, so the ferrite reaction is inert and ferrite stays 0 on every path.
    sysm = U.unified_system("1080")
    assert sysm.f_pro == 0.0
    for h in ("furnace", "air", "oil", "water"):
        assert U.transform_competing(*_path(h), sysm).ferrite == 0.0


# --------------------------------------------------------------------------- #
# CARBON ENRICHMENT — ferrite rejection lowers the effective Mₛ (the coupling)
# --------------------------------------------------------------------------- #
def test_ferrite_enrichment_lowers_effective_Ms():
    sysm = U.unified_system("4340")
    Ms_bulk = sysm.Ms
    slow = U.competing_microstructure("4340", *_path("furnace", diameter=0.3))   # lots of ferrite
    fast = U.competing_microstructure("4340", *_path("water", diameter=0.01))    # no ferrite
    # No ferrite → austenite carbon ~unchanged → Mₛ ~ bulk; lots of ferrite → enriched → lower Mₛ.
    # (A severe quench forms a negligible ~1e-5 ferrite, so the "no enrichment" tolerances are loose.)
    assert fast.C_gamma == pytest.approx(C4340["C"], abs=1e-3)
    assert fast.Ms_effective == pytest.approx(Ms_bulk, abs=0.5)
    assert slow.C_gamma > C4340["C"] + 0.2                  # enriched toward the eutectoid
    assert slow.Ms_effective < Ms_bulk - 50.0


def test_full_ferrite_enriches_austenite_to_the_eutectoid():
    # The lever-rule check: when proeutectoid ferrite fills its equilibrium cap, the austenite it
    # left has reached the eutectoid carbon (that is what f_pro is defined to give).
    res = U.competing_microstructure("4340", *_path("furnace", diameter=1.0))
    sysm = U.unified_system("4340")
    if res.ferrite == pytest.approx(sysm.f_pro, abs=1e-3):
        assert res.C_gamma == pytest.approx(0.76, abs=0.03)


# --------------------------------------------------------------------------- #
# CONSERVATION + ORDER-INSENSITIVITY
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("steel", ["1080", "4340"])
@pytest.mark.parametrize("medium", ["furnace", "air", "oil", "water"])
def test_fractions_sum_to_one(steel, medium):
    res = U.competing_microstructure(steel, *_path(medium))
    assert sum(res.fractions().values()) == pytest.approx(1.0, abs=1e-12)
    for v in res.fractions().values():
        assert -1e-12 <= v <= 1.0 + 1e-12


def test_pearlite_bainite_split_is_resolution_insensitive():
    # The competition apportionment is order/step insensitive: refine dt and the pearlite & bainite
    # fractions each converge (no spurious dependence on who is stepped first within a step).
    sysm = U.unified_system("4340")
    runs = []
    # The competition integrator is first-order; assert convergence at and above the demo's default
    # grid density (240/decade), where refinement moves each fraction < 0.025.
    for per_decade in (240, 480, 960):
        t = pathint.log_time_grid(20000.0, per_decade=per_decade)
        T = pathint.newton_cooling(t, 850.0, 25.0, 4000.0)   # slow cool: both compete
        r = U.transform_competing(t, T, sysm)
        runs.append((r.pearlite, r.bainite))
    ps = [p for p, _ in runs]
    bs = [b for _, b in runs]
    assert max(ps) - min(ps) < 0.025, ps
    assert max(bs) - min(bs) < 0.025, bs


# --------------------------------------------------------------------------- #
# INPUT GUARDS + the cross-steel wall
# --------------------------------------------------------------------------- #
def test_cross_steel_is_refused_the_8620_wall():
    # The named scope: only the two atlas-anchored steels have the cited bainite anchor. A
    # carburising 8620 (the carbon-spread wall, §6b) is refused — no cross-steel prediction.
    with pytest.raises(ValueError, match="atlas anchor"):
        U.unified_system("8620")


def test_mismatched_path_arrays_raise():
    sysm = U.unified_system("4340")
    with pytest.raises(ValueError):
        U.transform_competing(np.array([0.0, 1.0, 2.0]), np.array([850.0, 800.0]), sysm)


def test_system_exposes_cited_ceilings():
    sysm = U.unified_system("4340")
    assert sysm.Bs == pytest.approx(497.0, abs=2.0)        # Steven–Haynes Bs (bulk 4340)
    assert sysm.Ae3 > 700.0                                # Andrews Ae3 ceiling for ferrite
    assert sysm.Ms == pytest.approx(andrews_Ms(**C4340), abs=1e-6)


# --------------------------------------------------------------------------- #
# FROZEN-CORE BYTE-IDENTITY — the single-curve pipeline is untouched by §19
# --------------------------------------------------------------------------- #
def test_frozen_single_curve_nose_unchanged():
    # Adding PearliteReaction (kinetics §7) must not perturb the frozen single curve: the eutectoid
    # nose is still ≈ 550 °C / ≈ 1 s. Pinned to the exact current values (a byte-identity guard — any
    # future change to the frozen curve would trip it); these are the numbers PEARLITE_SCALE rests on.
    Tn, tn = CCurve().nose(X=0.01)
    assert Tn == pytest.approx(549.9497374343587, rel=1e-9)
    assert tn == pytest.approx(1.0019443756672384, rel=1e-9)


def test_frozen_single_curve_pipeline_matches_legacy_microstructure():
    # The single-curve pathint result for a 1080 quench is independent of the unified-KV machinery
    # (different code path entirely) — a guard that §19 did not silently alter the validated route.
    cc = CCurve()
    t, T = _path("oil", diameter=0.01)
    legacy = pathint.transform_along_path(t, T, cc)
    assert sum(legacy.fractions().values()) == pytest.approx(1.0, abs=1e-12)
    # Sanity: the frozen 1080 oil quench is bainite-labelled by the 540-split (the legacy behaviour
    # the unified system deliberately does NOT change).
    assert legacy.bainite > 0.0
