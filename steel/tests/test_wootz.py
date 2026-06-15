"""Tests for wootz.py — the signed GOOD-impurity foil (trace V/Mo make the Damascus pattern).

The mirror image of the bad-impurity stories (P cold-short, S red-short, MnS anisotropy): here a trace
carbide-former a clean-steel spec would reject is the one the wootz smith requires. Honest map (mirrors the
module docstring):

  * there is **NO claimable tooth** — the three gates are Verhoeven & Pendray's cited threshold lines (V ≥ 40
    ppm; Mn ≥ 200 ppm; the 50–100 °C-below-A_cm forging window), the proeutectoid cementite is
    :mod:`steel.fe_c`'s lever rule, and the interdendritic enrichment is :mod:`steel.casting`'s Scheil; the
    checks here are by-construction / structural / discriminating;
  * the **relative former effectiveness is read straight off the two cited thresholds** (Mn at ~0.2× V), NOT
    derived from segregation coefficients — pinned by the weighting test;
  * the **flag is gated on INTENT** — forged as wootz (hypereutectoid *and* correctly cycled) but the former
    fell short — never on a bare composition; a plain bar forged normally reads clean (the model is
    :mod:`steel.sulfide_morphology`'s plain heat);
  * the band spacing is a **cited observation**, not computed; the enrichment ratio is **representative**
    (the pinned Mo former as the exemplar).

All analytic (closed-form thresholds + reused lever rule / Scheil) — no solver, fast lane.
"""
from __future__ import annotations

import pytest

from steel import casting, fe_c
from steel import wootz as wz
from steel.heat_state import Heat, heat_treat
from steel.sweep import Steel, evaluate

# A genuine wootz cake and a clean modern UHC twin — bespoke ~1.5 %C (repo grades top out near eutectoid).
_WOOTZ = Steel(C=1.5, Mn=0.30, Si=0.10, name="wootz")
_CLEAN = Steel(C=1.5, Mn=0.30, Si=0.10, name="clean UHC")
_PLAIN = Steel(C=0.45, Mn=0.75, Si=0.25, name="1045")

_V_GENUINE = 60.0
_V_CLEAN = 5.0


def _heat(comp):
    return Heat(composition=comp)


def _mid_window(C: float) -> float:
    lo, hi = wz.forging_window(C)
    return (lo + hi) / 2.0


# --------------------------------------------------------------------------- #
# By construction — the gates reuse cited thresholds + fe_c lever rule + casting Scheil
# --------------------------------------------------------------------------- #
def test_effective_former_weights_are_the_cited_thresholds_not_segregation():
    # BY CONSTRUCTION: V and Mo count full weight (Verhoeven: the two most effective formers); Mn counts at the
    # cited threshold RATIO 40/200 = 0.2× — read straight off the two cited threshold numbers, NOT derived from
    # partition coefficients (effectiveness is carbide-forming thermodynamics, not microsegregation strength).
    assert wz.effective_carbide_former_ppm(v_ppm=60) == pytest.approx(60.0)
    assert wz.effective_carbide_former_ppm(mo_ppm=60) == pytest.approx(60.0)         # Mo equals V
    assert wz.effective_carbide_former_ppm(mn_ppm=200) == pytest.approx(40.0)        # 200 ppm Mn ≈ 40 ppm V
    ratio = wz.V_BANDING_MIN_PPM / wz.MN_BANDING_MIN_PPM
    assert wz.effective_carbide_former_ppm(mn_ppm=100) == pytest.approx(100 * ratio)
    # negatives floored to zero
    assert wz.effective_carbide_former_ppm(v_ppm=-5) == 0.0


def test_former_sufficiency_is_the_cited_V_threshold():
    assert wz.former_sufficient_for_banding(v_ppm=wz.V_BANDING_MIN_PPM)          # exactly 40 ppm clears
    assert not wz.former_sufficient_for_banding(v_ppm=wz.V_BANDING_MIN_PPM - 0.1)
    assert wz.former_sufficient_for_banding(mn_ppm=wz.MN_BANDING_MIN_PPM)        # 200 ppm Mn clears too
    assert not wz.former_sufficient_for_banding(mn_ppm=wz.MN_BANDING_MIN_PPM - 1)


def test_proeutectoid_cementite_reuses_fe_c_lever_rule():
    # BY CONSTRUCTION: zero below the eutectoid (no excess carbide), and exactly fe_c's proeutectoid cementite
    # fraction above it — not re-derived here.
    assert wz.proeutectoid_cementite_pct(0.45) == 0.0
    assert wz.proeutectoid_cementite_pct(wz.HYPEREUTECTOID_MIN_C) == 0.0
    expected = 100.0 * fe_c.equilibrium_constituents(1.5).f_proeutectoid
    assert wz.proeutectoid_cementite_pct(1.5) == pytest.approx(expected)
    assert wz.proeutectoid_cementite_pct(1.5) > wz.proeutectoid_cementite_pct(1.0) > 0.0


def test_interdendritic_enrichment_reuses_casting_scheil_and_exceeds_one():
    # BY CONSTRUCTION: the SAME casting.segregation_ratio used for the centerline defect, for the pinned Mo
    # former in the gamma phase (wootz is hypereutectoid → primary austenite). > 1 = the former piles up in the
    # interdendritic bands. This is the "same engine, opposite sign" beat — a mechanism display, not a tooth.
    k = casting.partition_coefficient("Mo", "gamma")
    assert wz.former_interdendritic_enrichment() == pytest.approx(
        casting.segregation_ratio(k, wz.FS_INTERDENDRITIC))
    assert wz.former_interdendritic_enrichment() > 1.0


def test_forging_window_reuses_fe_c_acm_and_is_below_it():
    lo, hi = wz.forging_window(1.5)
    acm = fe_c.Acm(1.5)
    assert (lo, hi) == pytest.approx((acm - wz.FORGE_BELOW_ACM_MAX_C, acm - wz.FORGE_BELOW_ACM_MIN_C))
    assert hi < acm                                                  # the whole window is below A_cm
    with pytest.raises(ValueError):                                  # undefined for non-hypereutectoid C
        wz.forging_window(0.45)


# --------------------------------------------------------------------------- #
# The hero — same steel, same forging, the trace V decides (the signed-impurity headline)
# --------------------------------------------------------------------------- #
def test_same_steel_same_forging_trace_vanadium_decides_the_pattern():
    peak = _mid_window(_WOOTZ.C)
    genuine = wz.wootz_assessment(_WOOTZ.C, v_ppm=_V_GENUINE, forge_peak_C=peak, forge_cycles=7)
    clean = wz.wootz_assessment(_CLEAN.C, v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7)
    assert _WOOTZ.C == _CLEAN.C                                      # the SAME carbon ...
    assert genuine.forged_as_wootz and clean.forged_as_wootz        # ... forged identically ...
    assert genuine.patterned and not clean.patterned                # ... only the V-bearing cake patterns
    assert clean.pattern_failed                                     # the clean cake is the off-spec miss


# --------------------------------------------------------------------------- #
# Three gates, each independently necessary
# --------------------------------------------------------------------------- #
def test_carbon_gate_a_plain_bar_never_patterns_whatever_its_vanadium():
    # Gate 1: no proeutectoid cementite below the eutectoid → no pattern, even with ample V and correct forging.
    a = wz.wootz_assessment(0.45, v_ppm=200, forge_peak_C=850, forge_cycles=8)
    assert not a.hypereutectoid and not a.patterned
    assert a.proeutectoid_cementite_pct == 0.0


def test_former_gate_a_clean_hypereutectoid_steel_fails_to_pattern():
    # Gate 2: hypereutectoid and forged correctly, but the trace former is below threshold → no pattern (flag).
    peak = _mid_window(1.5)
    a = wz.wootz_assessment(1.5, v_ppm=10, forge_peak_C=peak, forge_cycles=8)
    assert not a.former_sufficient and not a.patterned and a.pattern_failed


def test_forging_gate_too_hot_loses_the_pattern():
    # Gate 3: above A_cm the cementite dissolves → the pattern is lost even with ample V.
    acm = fe_c.Acm(1.5)
    a = wz.wootz_assessment(1.5, v_ppm=_V_GENUINE, forge_peak_C=acm + 20, forge_cycles=8)
    assert not a.forged_in_window and not a.patterned


def test_forging_gate_too_few_cycles_loses_the_pattern():
    peak = _mid_window(1.5)
    a = wz.wootz_assessment(1.5, v_ppm=_V_GENUINE, forge_peak_C=peak, forge_cycles=wz.MIN_FORGING_CYCLES - 1)
    assert not a.forged_in_window and not a.patterned


# --------------------------------------------------------------------------- #
# The flag is gated on INTENT — off-spec by lacking a good impurity, never a bare composition
# --------------------------------------------------------------------------- #
def test_flag_fires_only_when_forged_as_wootz_but_former_short():
    # THE LOAD-BEARING DESIGN CALL: the clean cake, forged as wootz, raises wootz-pattern-failed — the smith did
    # everything right; the ore lacked the vanadium. The signed miss.
    peak = _mid_window(1.5)
    out = wz.wootz_pattern_check(_heat(_CLEAN), v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7)
    assert out.has_defect(wz.WOOTZ_PATTERN_FAILED)
    assert out.history[-1].name == "wootz" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (wz.WOOTZ_PATTERN_FAILED,)


def test_plain_bar_never_forged_as_wootz_reads_clean_no_flag():
    # The intent gate: a plain bar (not hypereutectoid, not forged as wootz) never intended a pattern, so it
    # raises NO flag and spec-checks nothing (in_spec None). If this fails, the flag has stopped being about
    # intent and started branding ordinary steel "defective" for not being Damascus.
    out = wz.wootz_pattern_check(_heat(_PLAIN))
    assert not out.has_defect(wz.WOOTZ_PATTERN_FAILED)
    assert out.is_clean and out.history[-1].in_spec is None


def test_too_hot_heat_raises_no_flag_it_was_a_technique_miss_not_an_impurity_miss():
    # A hypereutectoid V-bearing heat forged too hot lost its pattern, but that is a forging miss, not the
    # signed-impurity miss — so no wootz-pattern-failed flag (the flag is specifically the missing former).
    acm = fe_c.Acm(1.5)
    out = wz.wootz_pattern_check(_heat(_WOOTZ), v_ppm=_V_GENUINE, forge_peak_C=acm + 20, forge_cycles=8)
    assert not out.has_defect(wz.WOOTZ_PATTERN_FAILED)
    assert out.history[-1].in_spec is None                          # not forged as wootz → spec-checks nothing


def test_genuine_wootz_patterns_and_stays_clean():
    peak = _mid_window(1.5)
    out = wz.wootz_pattern_check(_heat(_WOOTZ), v_ppm=_V_GENUINE, forge_peak_C=peak, forge_cycles=7)
    assert not out.has_defect(wz.WOOTZ_PATTERN_FAILED)
    assert out.is_clean and out.history[-1].in_spec is True


def test_flag_is_idempotent():
    peak = _mid_window(1.5)
    once = wz.wootz_pattern_check(_heat(_CLEAN), v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7)
    twice = wz.wootz_pattern_check(once, v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7)
    assert twice.defects.count(wz.WOOTZ_PATTERN_FAILED) == 1
    assert twice.history[-1].flags_added == ()


# --------------------------------------------------------------------------- #
# Inert in the hardenability back end — the pattern reads state, the quench ignores it
# --------------------------------------------------------------------------- #
def test_wootz_pattern_is_inert_in_the_hardenability_back_end():
    # The verdict reads state and may raise a flag, but moves NO composition and is invisible to the quench: a
    # flagged heat heat-treats byte-identically to the same composition untouched. If this ever fails, the
    # hardenability chain started reading the pattern, where it must stay inert. (Trace V/Mo are not even in the
    # Steel vector — they are keyword inputs here.)
    peak = _mid_window(1.5)
    h = _heat(_CLEAN)
    worked = wz.wootz_pattern_check(h, v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7)
    assert worked.has_defect(wz.WOOTZ_PATTERN_FAILED)
    assert worked.composition == h.composition                      # the pattern moves no composition
    base = evaluate(h.as_steel(), medium="oil", diameter=0.015)
    after = evaluate(worked.as_steel(), medium="oil", diameter=0.015)
    assert base.HV == after.HV and base.result.martensite == after.result.martensite
    assert heat_treat(worked, medium="oil", diameter=0.015).history[-1].summary == \
        heat_treat(h, medium="oil", diameter=0.015).history[-1].summary


def test_check_does_not_change_composition():
    peak = _mid_window(1.5)
    h = _heat(_WOOTZ)
    assert wz.wootz_pattern_check(h, v_ppm=_V_GENUINE, forge_peak_C=peak, forge_cycles=7).composition == h.composition


# --------------------------------------------------------------------------- #
# The verdict string names the outcome and its reason
# --------------------------------------------------------------------------- #
def test_verdict_names_the_pattern_and_the_reason_for_each_gate():
    peak = _mid_window(1.5)
    patterned = wz.wootz_assessment(1.5, v_ppm=_V_GENUINE, forge_peak_C=peak, forge_cycles=7).verdict
    clean = wz.wootz_assessment(1.5, v_ppm=_V_CLEAN, forge_peak_C=peak, forge_cycles=7).verdict
    plain = wz.wootz_assessment(0.45, v_ppm=_V_GENUINE, forge_peak_C=850, forge_cycles=7).verdict
    not_forged = wz.wootz_assessment(1.5, v_ppm=_V_GENUINE).verdict
    assert "Damascus pattern develops" in patterned
    assert "clean ore" in clean and "threshold" in clean
    assert "not hypereutectoid" in plain
    assert "not forged as wootz" in not_forged


def test_band_spacing_is_the_cited_range_not_computed():
    a = wz.wootz_assessment(1.5, v_ppm=_V_GENUINE, forge_peak_C=_mid_window(1.5), forge_cycles=7)
    assert a.band_spacing_um == (wz.BAND_SPACING_MIN_UM, wz.BAND_SPACING_MAX_UM)
    assert a.band_spacing_um == (30.0, 70.0)
