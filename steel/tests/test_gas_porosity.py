"""Unit tests for the gas-porosity consequence — the carbon-aware CO criterion + by-construction posture.

Honest map (mirrors the module docstring):
  * there is **NO claimable tooth** — the criterion *is* the cited C–O equilibrium evaluated against held
    composition, so it cannot independently "fail"; the checks here are by-construction / structural;
  * the one soft **OoM-coherence note** is "high-C must be killed, low-C can be rimmed" — ``O_crit ∝ 1/C``
    with no tuning (tested for shape + the crossover with refining's flat 30 ppm line);
  * the carbon-decides verdict (same oxygen, opposite outcome) is the demonstration and the build's reason
    to exist (the two flags **disagree** because of carbon);
  * the solidification CO-margin is a **conservative secondary**, NOT the verdict (asserted as such).

All analytic (closed-form CO product) — no solver, fast lane.
"""
from __future__ import annotations

import pytest

from steel import gas_porosity as gp
from steel import refining
from steel.heat_state import Heat
from steel.sweep import STEELS


# --------------------------------------------------------------------------- #
# The cited input — K_CO is the SAME C–O equilibrium F2 runs on (no new constant)
# --------------------------------------------------------------------------- #
def test_co_equilibrium_product_is_refinings_carbon_oxygen_product():
    # the consequence reuses refining's pinned C–O equilibrium, just at the freezing-front T/p
    assert gp.co_equilibrium_product() == refining.carbon_oxygen_product(gp.T_SOLIDIFICATION_C, gp.P_CO_FRONT)
    assert 0.0015 < gp.co_equilibrium_product() < 0.0025          # ~0.002 wt%² near the freezing range


# --------------------------------------------------------------------------- #
# The soft OoM-coherence note: O_crit(C) = K_CO/C falls as 1/C, crosses 30 ppm near C≈0.67%
# --------------------------------------------------------------------------- #
def test_critical_oxygen_falls_as_inverse_carbon():
    """High-carbon steels must be killed hard; low-carbon steels tolerate far more oxygen (O_crit ∝ 1/C)."""
    assert gp.critical_oxygen(0.20) > gp.critical_oxygen(0.40) > gp.critical_oxygen(0.80)
    # the 1/C shape: doubling carbon halves the critical oxygen
    assert gp.critical_oxygen(0.40) == pytest.approx(gp.critical_oxygen(0.80) * 2.0, rel=1e-9)


def test_critical_oxygen_crosses_refining_spec_near_two_thirds_carbon():
    # where the carbon-aware line equals the flat 30 ppm spec — leaner spec over-warns, richer under-warns
    crossover_C = gp.co_equilibrium_product() / (gp.POROSITY_RISK_O_PPM * 1e-4)
    assert 0.5 < crossover_C < 0.85
    assert gp.critical_oxygen(crossover_C) == pytest.approx(gp.POROSITY_RISK_O_PPM, rel=1e-9)


def test_critical_oxygen_requires_positive_carbon():
    with pytest.raises(ValueError):
        gp.critical_oxygen(0.0)


# --------------------------------------------------------------------------- #
# The verdict driver — supersaturation S is carbon-aware (the whole point)
# --------------------------------------------------------------------------- #
def test_supersaturation_is_carbon_aware_at_fixed_oxygen():
    """Same dissolved oxygen, more carbon → larger S — a flat oxygen line cannot see this."""
    s_low = gp.co_supersaturation(0.20, 28.0)
    s_high = gp.co_supersaturation(0.80, 28.0)
    assert s_high > s_low
    assert s_high == pytest.approx(s_low * 4.0, rel=1e-9)          # S ∝ C at fixed O


def test_supersaturation_scales_with_oxygen_at_fixed_carbon():
    assert gp.co_supersaturation(0.40, 60.0) == pytest.approx(gp.co_supersaturation(0.40, 30.0) * 2.0, rel=1e-9)


def test_undeoxidized_heat_is_sign_robust_by_cooling_supersaturation():
    """An under-killed heat sits on the tap C–O line → S = K_CO(tap)/K_CO(front), guaranteed > 1 below tap.

    The high-carbon hero's modest S ≈ 1.05 is NOT a coin-flip on the freezing-T pin: a heat at its C–O
    equilibrium oxygen (undeoxidized) has C·O = K_CO(tap), so the verdict is a pure cooling ratio that is > 1
    for any front colder than tap and grows as it cools — and the absolute-K_CO scatter cancels in the ratio.
    """
    C, T_tap = 0.80, refining.T_TAP_C
    O_on_line = refining.equilibrium_oxygen(C, T_tap)                    # the tap C–O equilibrium oxygen
    assert C * (O_on_line * 1e-4) == pytest.approx(refining.carbon_oxygen_product(T_tap), rel=1e-12)
    s_prev = 0.0
    for T_front in (1600.0, 1560.0, 1530.0, 1500.0, 1480.0):            # tap → cooling toward the front
        S = gp.co_supersaturation(C, O_on_line, T_celsius=T_front)
        assert S >= 1.0 - 1e-9                                          # never sound below/at tap
        assert S > s_prev                                              # grows monotonically as the front cools
        s_prev = S


# --------------------------------------------------------------------------- #
# The demonstration — same oxygen, the carbon decides (the two flags disagree)
# --------------------------------------------------------------------------- #
def test_same_oxygen_high_carbon_porous_low_carbon_sound():
    O = 28.0
    high = gp.porosity_assessment(0.80, O)
    low = gp.porosity_assessment(0.20, O)
    assert high.porous and not low.porous                          # identical oxygen, carbon decides
    assert not high.risk_flagged and not low.risk_flagged          # BOTH within refining's 30 ppm spec


def test_well_killed_high_carbon_is_sound():
    # a high-carbon heat is fine once killed below its (low) carbon-aware limit — not porous by construction
    assert not gp.porosity_assessment(0.80, 5.0).porous
    assert not gp.porosity_assessment(1.00, 5.0).porous


def test_low_carbon_tolerates_oxygen_over_the_refining_spec():
    # over the 30 ppm spec (refining would flag) yet sound — too lean in carbon to evolve CO
    a = gp.porosity_assessment(0.10, 60.0)
    assert a.risk_flagged and not a.porous                         # the other disagreement direction


def test_verdict_string_names_the_carbon_blindness():
    over_spec_sound = gp.porosity_assessment(0.10, 60.0).verdict
    under_spec_porous = gp.porosity_assessment(0.80, 28.0).verdict
    assert "lean in carbon" in over_spec_sound
    assert "within the 30 ppm" in under_spec_porous


# --------------------------------------------------------------------------- #
# The conservative secondary — NOT the verdict (asserted as such)
# --------------------------------------------------------------------------- #
def test_solidification_margin_is_zero_when_already_over_the_bath_line():
    # bath already porous → freezing crossing fraction is 0 (crosses from the start)
    assert gp.solidification_co_fraction(0.80, 60.0) == 0.0


def test_solidification_margin_is_between_zero_and_one_for_a_bath_sound_heat():
    fs = gp.solidification_co_fraction(0.40, 10.0)
    assert 0.0 < fs < 1.0


def test_solidification_margin_shrinks_with_carbon_but_does_not_set_the_verdict():
    # higher carbon → less freezing margin (smaller crossing fraction) ...
    assert gp.solidification_co_fraction(0.80, 10.0) < gp.solidification_co_fraction(0.20, 10.0)
    # ... but the VERDICT is the bath supersaturation: this well-killed high-C heat is SOUND even though its
    # Scheil crossing fraction is below the cutoff (the singularity false-flags — why it is not the verdict)
    a = gp.porosity_assessment(0.80, 10.0)
    assert a.solidification_co_fraction < gp.FS_CO_CUTOFF
    assert not a.porous


# --------------------------------------------------------------------------- #
# The orchestrator seam + the two-tier flag (risk → consequence)
# --------------------------------------------------------------------------- #
def _refined_heat(grade: str, al_pct: float) -> Heat:
    h = refining.from_hot_metal(STEELS[grade])
    h = refining.decarburize(h, STEELS[grade].C)
    return refining.deoxidize(h, "Al", al_pct)


def test_two_tier_flag_disagrees_because_of_carbon():
    high = _refined_heat("1080", 0.0015)                           # under-killed high-C, within 30 ppm spec
    low = _refined_heat("8620", 0.0015)                            # same kill, low-C
    assert not high.has_defect(refining.POROSITY_RISK)             # refining clears both (carbon-blind)
    assert not low.has_defect(refining.POROSITY_RISK)
    high_out = gp.gas_porosity_check(high)
    low_out = gp.gas_porosity_check(low)
    assert high_out.has_defect(gp.GAS_POROSITY)                    # but the high-C casting blows holes
    assert not low_out.has_defect(gp.GAS_POROSITY)                 # and the low-C one is sound


def test_orchestrator_appends_step_and_preserves_composition():
    heat = _refined_heat("1080", 0.0015)
    out = gp.gas_porosity_check(heat)
    assert out.history[-1].name == "gas-porosity-check"
    assert out.composition == heat.composition                     # the verdict reads state, not the alloy


def test_orchestrator_idempotent_flag():
    heat = _refined_heat("1080", 0.0015)
    once = gp.gas_porosity_check(heat)
    twice = gp.gas_porosity_check(once)
    assert twice.defects.count(gp.GAS_POROSITY) == 1


def test_orchestrator_requires_oxygen_state():
    bare = Heat(composition=STEELS["1080"])                        # no F2 deoxidize → no oxygen_ppm
    with pytest.raises(ValueError):
        gp.gas_porosity_check(bare)
