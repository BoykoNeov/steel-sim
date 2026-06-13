"""Tests for hot_work.py — the sulfur consequence (red-shortness), the F5 forging-stage consumer.

This slice CLOSES what F2 Slice 2 left inert for sulfur. It is a NEW consumer (not a propagation), but — the
load-bearing honesty — it carries **no strict tooth of its own**: cited constants + a by-construction verdict
over a reused balance, the same shape slag.py labels "by construction (NOT teeth)". The one genuine tooth of
the impurity-consequence build is in grain.py (the P-strength cross-source coherence). The tests reflect that:

  * THE HISTORICAL-COHERENCE ANCHOR (a RESULT, by-construction — NOT a tooth) — the Mn:S ≥ 1.71 threshold
    reproduces Mushet (manganese makes sulfurous steel forgeable). It is the reason the slice is worth
    building, but 1.71 = M_Mn/M_S is arithmetic that cannot come out wrong; it is NOT the analog of slag.py's
    acid/basic L_P endpoint (that emerges from a Healy correlation that could have failed to reproduce
    history). slag.py labels this exact stoichiometry "by construction", and so do we.
  * NOT A TOOTH (avoided): the temperature *ordering* (eutectic 988 < forge < MnS 1610). Those are looked-up
    numbers; "free S above the eutectic cracks" is the module's own rule. The temperature-gate test below
    checks that RULE's behaviour (a by-construction wiring check), it does not assert the ordering is a
    benchmark — that would be the vacuous-benchmark trap.
  * BY CONSTRUCTION — the free-sulfur balance is slag.manganese_sulfide; the cited temps; the wiring.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from steel import hot_work as hw
from steel import slag as sg
from steel.heat_state import Heat
from steel.sweep import STEELS

_BACKBONE = replace(STEELS["1045"], C=0.12, Mn=0.0, Si=0.15, name="structural")


def _heat(Mn, S):
    return Heat(composition=replace(_BACKBONE, Mn=Mn, S=S))


# --------------------------------------------------------------------------- #
# The historical-coherence ANCHOR — the Mn:S threshold reproduces Mushet (by construction, NOT a tooth)
# --------------------------------------------------------------------------- #
def test_mushet_threshold_is_the_red_short_boundary():
    # At a fixed sulfur, sweeping manganese across the stoichiometric Mn:S = 1.71: below it free sulfur
    # remains and the steel is red-short at the forge; at/above it all sulfur is MnS and the steel is sound.
    # This reproduces Mushet's fix — but 1.71 is M_Mn/M_S arithmetic (slag.py's by-construction balance), so
    # it is the headline RESULT, not a falsifiable tooth.
    S = 0.05
    just_below = hw.red_short_assessment(Mn_pct=1.60 * S, S_pct=S)   # Mn:S = 1.60 < 1.71
    just_above = hw.red_short_assessment(Mn_pct=1.80 * S, S_pct=S)   # Mn:S = 1.80 > 1.71
    assert just_below.free_sulfur_pct > 0.0 and just_below.red_short
    assert just_above.free_sulfur_pct == 0.0 and not just_above.red_short


def test_mushet_manganese_fixes_red_shortness_the_historical_arc():
    # The 1850s fix as the model reproduces it: sulfurous Bessemer steel with NO manganese is red-short;
    # add Mushet's manganese (spiegeleisen) to clear the 1.71 threshold and it becomes forgeable.
    no_mn = hw.red_short_assessment(Mn_pct=0.0, S_pct=0.05)
    mushet = hw.red_short_assessment(Mn_pct=0.20, S_pct=0.05)        # Mn:S = 4.0
    assert no_mn.red_short and not no_mn.forms_mns
    assert (not mushet.red_short) and mushet.forms_mns


def test_free_sulfur_reuses_the_slag_balance():
    # BY CONSTRUCTION: the free sulfur is exactly slag.manganese_sulfide's (no reimplementation).
    Mn, S = 0.04, 0.06
    a = hw.red_short_assessment(Mn, S)
    assert a.free_sulfur_pct == sg.manganese_sulfide(Mn, S).free_sulfur_pct
    assert a.mn_s_ratio == pytest.approx(Mn / S)


# --------------------------------------------------------------------------- #
# The temperature gate — a BY-CONSTRUCTION wiring check of the verdict rule (NOT teeth)
# --------------------------------------------------------------------------- #
def test_free_sulfur_is_red_short_only_above_the_eutectic():
    # The rule: red-shortness needs BOTH free sulfur AND a working temperature at/above the Fe–FeS eutectic.
    # The SAME manganese-short heat cracks at the forge but is workable cold. (This checks our verdict rule's
    # behaviour — it is not a claim that the eutectic temperature is a benchmark.)
    hot = hw.red_short_assessment(Mn_pct=0.0, S_pct=0.05, temp_C=1150.0)
    cold = hw.red_short_assessment(Mn_pct=0.0, S_pct=0.05, temp_C=700.0)
    assert hot.red_short and hot.above_eutectic
    assert (not cold.red_short) and (not cold.above_eutectic) and cold.free_sulfur_pct > 0.0


def test_sulfur_free_heat_is_always_sound():
    # No sulfur ⇒ no FeS ⇒ never red-short, at any temperature (ratio is infinite, free S is zero).
    a = hw.red_short_assessment(Mn_pct=0.8, S_pct=0.0, temp_C=1200.0)
    assert a.free_sulfur_pct == 0.0 and a.forms_mns and not a.red_short


def test_cited_constants_are_the_di_crosschecked_values():
    # Pinned constants, NOT teeth — guarded only so an edit cannot silently move the load-bearing eutectic.
    # The eutectic (the GB liquid-film onset) is the Fe–FeS *eutectic*, distinct from FeS melting (~1192 °C).
    assert hw.FE_FES_EUTECTIC_C == 988.0
    assert hw.MNS_MELTING_C == 1610.0
    assert hw.FE_FES_EUTECTIC_C < hw.DEFAULT_FORGE_TEMP_C < hw.MNS_MELTING_C   # the mechanism narrative


# --------------------------------------------------------------------------- #
# The orchestrator seam — hot_work evolves the Heat and raises the flag
# --------------------------------------------------------------------------- #
def test_hot_work_raises_red_short_flag_and_records_a_step():
    out = hw.hot_work(_heat(Mn=0.0, S=0.05), 1150.0)
    assert out.has_defect(hw.RED_SHORT)
    assert out.history[-1].name == "hot-work" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (hw.RED_SHORT,)
    assert out.temperature_C == 1150.0


def test_hot_work_sound_heat_stays_clean():
    out = hw.hot_work(_heat(Mn=0.80, S=0.02), 1150.0)
    assert not out.has_defect(hw.RED_SHORT)
    assert out.is_clean and out.history[-1].in_spec is True


def test_hot_work_does_not_change_composition():
    # Forging does not move sulfur — only the temperature set-point and the defect state evolve.
    h = _heat(Mn=0.0, S=0.05)
    out = hw.hot_work(h, 1150.0)
    assert out.composition == h.composition


def test_hot_work_flag_is_idempotent():
    # A second hot-work of an already-flagged heat does not re-add the flag (no duplicates).
    once = hw.hot_work(_heat(Mn=0.0, S=0.05), 1150.0)
    twice = hw.hot_work(once, 1150.0)
    assert twice.defects.count(hw.RED_SHORT) == 1
    assert twice.history[-1].flags_added == ()
