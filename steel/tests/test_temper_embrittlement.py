"""Tests for temper_embrittlement.py — the martensitic phosphorus consequence (reversible TE).

The third impurity consequence, and the second half of phosphorus' story. Like the sulfur / red-short slice
this is a NEW consumer with NO strict tooth: cited constants + a by-construction verdict. The would-be tooth
— the segregation C-curve nose emerging at the observed ~490–550 °C from the cited ΔG_seg(P) + D_P(α-Fe) —
was FALSIFIED ON PAPER before any code was written (the McLean model puts the peak at ~390–435 °C, drifts
with exposure time, and runs ~100× faster than the source's own kinetic anchor), so the segregation model was
NOT built to manufacture a tooth. What the tests pin: the by-construction J-factor, the verdict rule (the
four levers + reversibility), the orchestrator wiring, and the coherence note that the Mo-bearing registry
grades are not susceptible (NOT a benchmark — the J-factor is regression-fit, so it cannot 'miss').
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from steel import temper_embrittlement as te
from steel.heat_state import Heat
from steel.sweep import STEELS, Steel

# The classic victim: a dirty Ni-Cr forging steel with residual phosphorus and no molybdenum.
VICTIM = Steel(C=0.40, Mn=0.60, Si=0.30, Ni=3.30, Cr=1.60, Mo=0.0, P=0.025, name="Ni-Cr victim")
TEMPER_HI = 620.0          # a temper ABOVE the 375–575 window — the cool THROUGH it is the variable


# --------------------------------------------------------------------------- #
# The J-factor — Watanabe's susceptibility index (BY CONSTRUCTION, not a tooth)
# --------------------------------------------------------------------------- #
def test_j_factor_is_the_watanabe_formula():
    s = Steel(C=0.4, Mn=0.6, Si=0.3, P=0.02)
    assert te.j_factor(s) == pytest.approx((0.6 + 0.3) * (0.02 + 0.0) * 1e4)          # = 180
    assert te.j_factor(s, Sn_pct=0.01) == pytest.approx((0.6 + 0.3) * (0.02 + 0.01) * 1e4)
    # rises with each co-segregant (P, Mn, Si) — a regression-fit ranking, so this cannot fail
    assert te.j_factor(replace(s, P=0.04)) > te.j_factor(s)
    assert te.j_factor(replace(s, Mn=1.2)) > te.j_factor(s)


def test_registry_workhorses_are_not_susceptible_a_coherence_note():
    # The Mo-bearing workhorses (4140/8620) at clean residual P fall below the J limit; the dirty Ni-Cr heat
    # is the one that pokes past. A COHERENCE NOTE (the cure lives in the workhorse), NOT a tooth — the
    # J-factor is regression-fit so "low J ⇒ not susceptible" cannot come out wrong.
    for name in STEELS:
        assert te.j_factor(replace(STEELS[name], P=0.012)) < te.J_SUSCEPTIBLE
    assert te.j_factor(VICTIM) >= te.J_SUSCEPTIBLE


# --------------------------------------------------------------------------- #
# The four levers — the verdict rule (by construction): any one saves a susceptible heat
# --------------------------------------------------------------------------- #
def test_susceptible_heat_slow_cooled_through_window_embrittles():
    a = te.temper_embrittlement_assessment(VICTIM, exposure_T_C=TEMPER_HI, slow_cool=True)
    assert a.susceptible and a.exposed and not a.mo_protected and a.embrittled


def test_fast_cool_through_window_saves_it():
    # Tempered above the window, a fast cool never dwells where P segregates — the cooling-rate control.
    a = te.temper_embrittlement_assessment(VICTIM, exposure_T_C=TEMPER_HI, slow_cool=False)
    assert a.susceptible and (not a.exposed) and (not a.embrittled)


def test_molybdenum_suppresses_even_when_slow_cooled():
    a = te.temper_embrittlement_assessment(replace(VICTIM, Mo=0.55), exposure_T_C=TEMPER_HI, slow_cool=True)
    assert a.susceptible and a.exposed and a.mo_protected and (not a.embrittled)


def test_clean_heat_is_not_susceptible():
    a = te.temper_embrittlement_assessment(replace(VICTIM, P=0.005), exposure_T_C=TEMPER_HI, slow_cool=True)
    assert (not a.susceptible) and (not a.embrittled)


def test_held_in_window_embrittles_even_fast_cooled():
    # 540 °C is INSIDE the danger window — a part tempered/held there is already segregating; you cannot
    # fast-cool out of a hold (the cooling lever only escapes a cool THROUGH the window from above it).
    a = te.temper_embrittlement_assessment(VICTIM, exposure_T_C=540.0, slow_cool=False)
    assert a.exposed and a.embrittled


def test_reversibility_reheat_above_600_fast_cool_resets():
    # The behaviour that names the phenomenon (a cited qualitative fact, NOT a tooth): reheating above the
    # de-embrittlement threshold and cooling fast leaves a fresh heat tough.
    embrittled = te.temper_embrittlement_check(Heat(composition=VICTIM), exposure_T_C=TEMPER_HI, slow_cool=True)
    assert embrittled.has_defect(te.TEMPER_EMBRITTLED)
    reset = te.temper_embrittlement_assessment(VICTIM, exposure_T_C=650.0, slow_cool=False)
    assert not reset.embrittled


def test_phosphorus_drives_the_consequence():
    # The point of the slice: it is PHOSPHORUS that tips a Ni-Cr heat into temper embrittlement.
    base = replace(VICTIM, P=0.003)
    assert not te.temper_embrittlement_assessment(base, exposure_T_C=TEMPER_HI, slow_cool=True).embrittled
    assert te.temper_embrittlement_assessment(replace(base, P=0.03), exposure_T_C=TEMPER_HI, slow_cool=True).embrittled


# --------------------------------------------------------------------------- #
# The orchestrator seam — temper_embrittlement_check evolves the Heat and raises the flag
# --------------------------------------------------------------------------- #
def test_check_raises_flag_and_records_a_step():
    out = te.temper_embrittlement_check(Heat(composition=VICTIM), exposure_T_C=TEMPER_HI, slow_cool=True)
    assert out.has_defect(te.TEMPER_EMBRITTLED)
    assert out.history[-1].name == "temper-embrittle-check" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (te.TEMPER_EMBRITTLED,)


def test_check_clean_heat_stays_clean():
    out = te.temper_embrittlement_check(Heat(composition=replace(VICTIM, P=0.005)), exposure_T_C=TEMPER_HI)
    assert (not out.has_defect(te.TEMPER_EMBRITTLED)) and out.is_clean and out.history[-1].in_spec is True


def test_check_does_not_change_composition():
    h = Heat(composition=VICTIM)
    assert te.temper_embrittlement_check(h, exposure_T_C=TEMPER_HI).composition == h.composition


def test_check_flag_is_idempotent():
    once = te.temper_embrittlement_check(Heat(composition=VICTIM), exposure_T_C=TEMPER_HI, slow_cool=True)
    twice = te.temper_embrittlement_check(once, exposure_T_C=TEMPER_HI, slow_cool=True)
    assert twice.defects.count(te.TEMPER_EMBRITTLED) == 1 and twice.history[-1].flags_added == ()
