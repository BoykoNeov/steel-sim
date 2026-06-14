"""Tests for tempered_martensite_embrittlement.py — the irreversible, carbon-driven tempering trough.

The OTHER tempering-axis embrittlement, the foil to the reversible one (temper_embrittlement.py). Like that
slice and the sulfur / red-short slice, this is a NEW consumer with NO strict tooth: cited constants + a
by-construction verdict. The would-be tooth — the 260–370 °C trough emerging from ε→cementite / interlath-RA
kinetics — was gated on paper and failed (the repo has no stage-III carbide thermodynamics), so no carbide model
was built to manufacture one. What the tests pin: the by-construction verdict rule (the two gates — carbon AND a
hardened martensitic structure — plus the trough window), the peak-temper IRREVERSIBILITY (one-way, the
distinction from the reversible sibling), the orchestrator wiring, and that the verdict composes with the frozen
back-end quench (a section that did not harden is immune).
"""
from __future__ import annotations

from dataclasses import replace

from steel import tempered_martensite_embrittlement as tme
from steel.heat_state import Heat
from steel.sweep import STEELS, Steel

VICTIM = STEELS["4140"]          # medium-carbon Cr-Mo — the classic TME victim; oil 10 mm → ~96 % martensite
HARD = 0.96                      # a representative as-quenched martensite fraction for a hardened part


# --------------------------------------------------------------------------- #
# The verdict rule — the trough window (BY CONSTRUCTION, not a tooth)
# --------------------------------------------------------------------------- #
def test_peak_temper_in_the_trough_embrittles_a_hardened_medium_carbon_steel():
    a = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=300.0)
    assert a.martensitic and a.carbon_sufficient and a.in_trough and a.embrittled


def test_below_the_trough_is_tough():
    a = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=200.0)
    assert (not a.in_trough) and (not a.embrittled)


def test_above_the_recovery_is_tough_and_recovered():
    a = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=450.0)
    assert a.recovered and (not a.in_trough) and (not a.embrittled)


def test_just_above_the_trough_reads_recovering_not_below():
    # The (370, 400) band: above the trough, not yet at the recovery threshold — the verdict string must say
    # "recovering", not "below the trough" (the flag is correctly tough either way).
    a = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=385.0)
    assert (not a.embrittled) and (not a.recovered) and ("recovering" in a.verdict)


def test_the_trough_edges_match_the_cited_window():
    lo, hi = tme.TME_WINDOW_C
    assert tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=lo).embrittled
    assert tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=hi).embrittled
    assert not tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=hi + 1.0).embrittled


# --------------------------------------------------------------------------- #
# The two gates — carbon AND a hardened martensitic structure (by construction)
# --------------------------------------------------------------------------- #
def test_low_carbon_martensite_is_immune_even_when_fully_hardened():
    # 8620 (0.20 %C) is a case-hardening grade: even at 98 % martensite it carries too little carbon to form the
    # embrittling cementite films. The carbon gate — and the guard against the inverted bulk-RA ranking.
    low_c = STEELS["8620"]
    a = tme.tempered_martensite_embrittlement_assessment(low_c, 0.98, peak_temper_C=300.0)
    assert a.martensitic and (not a.carbon_sufficient) and (not a.embrittled)


def test_a_structure_that_did_not_harden_is_immune():
    # No tempered martensite to embrittle — TME acts on a hardened structure. The martensitic gate.
    a = tme.tempered_martensite_embrittlement_assessment(VICTIM, 0.21, peak_temper_C=300.0)
    assert (not a.martensitic) and (not a.embrittled)


def test_clean_steel_still_embrittles_the_distinction_from_reversible_te():
    # The headline distinction: TME is carbon/microstructure, not impurity — so a CLEAN (low-P) heat still
    # embrittles, where the reversible sibling needs phosphorus to. P is not in the verdict.
    clean = replace(VICTIM, P=0.003)
    assert tme.tempered_martensite_embrittlement_assessment(clean, HARD, peak_temper_C=300.0).embrittled


def test_carbon_threshold_is_the_gate_boundary():
    just_under = Steel(C=tme.MIN_CARBON_FOR_TME - 0.01, Mn=0.8)
    just_over = Steel(C=tme.MIN_CARBON_FOR_TME + 0.01, Mn=0.8)
    assert not tme.tempered_martensite_embrittlement_assessment(just_under, HARD, peak_temper_C=300.0).embrittled
    assert tme.tempered_martensite_embrittlement_assessment(just_over, HARD, peak_temper_C=300.0).embrittled


# --------------------------------------------------------------------------- #
# Irreversibility — keyed on the PEAK temper (the one-way distinction from reversible TE)
# --------------------------------------------------------------------------- #
def test_over_tempering_then_re_entering_the_trough_stays_tough():
    # The cycle that names it IRreversible: temper in trough (embrittled) → over-temper (recovered) → re-enter
    # the trough with the peak still high → STAYS TOUGH. The carbide morphology is set by the peak — one-way.
    lo = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=300.0)
    recovered = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=450.0)
    re_entered = tme.tempered_martensite_embrittlement_assessment(VICTIM, HARD, peak_temper_C=max(450.0, 300.0))
    assert [lo.embrittled, recovered.embrittled, re_entered.embrittled] == [True, False, False]


def test_check_threads_the_prior_peak():
    # Through the orchestrator: a part previously over-tempered (prior peak past recovery) does not re-embrittle
    # when tempered back in the trough — the irreversibility, threaded by prior_peak_temper_C.
    out = tme.tempered_martensite_embrittlement_check(
        Heat(composition=VICTIM), temper_T_C=300.0, prior_peak_temper_C=450.0
    )
    assert not out.has_defect(tme.TEMPERED_MARTENSITE_EMBRITTLED) and out.history[-1].in_spec is True


# --------------------------------------------------------------------------- #
# The orchestrator seam — quench-and-temper evolves the Heat and raises the flag
# --------------------------------------------------------------------------- #
def test_check_raises_flag_and_records_a_step():
    out = tme.tempered_martensite_embrittlement_check(Heat(composition=VICTIM), temper_T_C=300.0)
    assert out.has_defect(tme.TEMPERED_MARTENSITE_EMBRITTLED)
    assert out.history[-1].name == "tme-check" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (tme.TEMPERED_MARTENSITE_EMBRITTLED,)


def test_check_high_temper_stays_clean():
    out = tme.tempered_martensite_embrittlement_check(Heat(composition=VICTIM), temper_T_C=600.0)
    assert (not out.has_defect(tme.TEMPERED_MARTENSITE_EMBRITTLED)) and out.is_clean
    assert out.history[-1].in_spec is True


def test_check_composes_with_hardenability_soft_section_is_immune():
    # A plain-carbon 1045 in a mild quench does not through-harden (≈ 21 % martensite) → no tempered martensite
    # to embrittle, even tempered squarely in the trough. The verdict rides the same frozen back-end quench.
    out = tme.tempered_martensite_embrittlement_check(
        Heat(composition=STEELS["1045"]), temper_T_C=300.0, medium="oil", diameter=0.010
    )
    assert not out.has_defect(tme.TEMPERED_MARTENSITE_EMBRITTLED)


def test_check_does_not_change_composition():
    h = Heat(composition=VICTIM)
    assert tme.tempered_martensite_embrittlement_check(h, temper_T_C=300.0).composition == h.composition


def test_check_flag_is_idempotent():
    once = tme.tempered_martensite_embrittlement_check(Heat(composition=VICTIM), temper_T_C=300.0)
    twice = tme.tempered_martensite_embrittlement_check(once, temper_T_C=300.0)
    assert twice.defects.count(tme.TEMPERED_MARTENSITE_EMBRITTLED) == 1 and twice.history[-1].flags_added == ()
