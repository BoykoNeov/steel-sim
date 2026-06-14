"""Tests for hot_tear.py — the casting-stage sulfur consequence (solidification cracking).

The segregation-amplified sibling of forging-stage red-shortness (:mod:`steel.hot_work`). Honest map
(mirrors the module docstring):

  * there is **NO claimable tooth** — the verdict *is* the cited Scheil partition (Won & Thomas ``k``,
    :mod:`steel.casting`) feeding the cited MnS stoichiometry (``1.71``, :mod:`steel.slag`), so it cannot
    independently "fail"; the checks here are by-construction / structural;
  * the one soft **OoM-coherence note** is that segregation amplifies the stoichiometric ``1.71`` into the
    **tens** (``critical_bulk_mn_s``) — robust in order, cutoff-tuned in value (tested for both);
  * the **segregation flips a bulk-clear heat** result (a heat that clears bulk stoichiometry still tears) is
    the demonstration and the build's reason to exist — the two readings disagree because of segregation;
  * NOT asserted as a benchmark: "free S in the last liquid ⇒ hot-tear" is the module's own rule (the
    vacuous-benchmark trap). The discriminating behaviour (the hero, the Mushet lever) is tested instead.

All analytic (closed-form Scheil + stoichiometry) — no solver, fast lane.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from steel import casting
from steel import hot_tear as ht
from steel import slag
from steel.heat_state import Heat
from steel.sweep import STEELS

_BACKBONE = replace(STEELS["1045"], C=0.18, Mn=0.0, Si=0.30, P=0.0, S=0.0, name="cast structural")


def _heat(Mn, S):
    return Heat(composition=replace(_BACKBONE, Mn=Mn, S=S))


# --------------------------------------------------------------------------- #
# By construction — the segregation amplification reuses casting's Scheil liquid enrichment
# --------------------------------------------------------------------------- #
def test_segregation_factor_is_the_scheil_liquid_ratio():
    # BY CONSTRUCTION: the suppression of the film Mn:S is the ratio of the two Scheil LIQUID enrichments
    # (1-fs)^(k_Mn - k_S), built from casting's cited partition coefficients — never the solid.
    fs = ht.FS_LAST_LIQUID
    k_Mn = casting.partition_coefficient("Mn", ht.DEFAULT_PHASE)
    k_S = casting.partition_coefficient("S", ht.DEFAULT_PHASE)
    assert ht.segregation_factor() == pytest.approx((1.0 - fs) ** (k_Mn - k_S))
    assert ht.segregation_factor() < 1.0                       # the film is Mn:S-POORER than the bath


def test_last_liquid_uses_the_scheil_liquid_composition_for_both_solutes():
    # The film is a LIQUID phenomenon — both Mn and S come from scheil_liquid_composition (sulfur piles up in
    # the residual liquid, it is not depleted into the solid).
    Mn, S, fs = 0.40, 0.030, ht.FS_LAST_LIQUID
    Mn_L, S_L = ht.last_liquid_mn_s(Mn, S, fs)
    assert Mn_L == pytest.approx(
        casting.scheil_liquid_composition(Mn, casting.partition_coefficient("Mn", ht.DEFAULT_PHASE), fs))
    assert S_L == pytest.approx(
        casting.scheil_liquid_composition(S, casting.partition_coefficient("S", ht.DEFAULT_PHASE), fs))
    assert S_L > S and Mn_L > Mn                               # both enriched ...
    assert (S_L / S) > (Mn_L / Mn)                             # ... but sulfur far more (the amplification)


def test_film_mn_s_is_the_bulk_ratio_times_the_segregation_factor():
    # The film Mn:S is the bulk Mn:S suppressed by the segregation factor (the amplification, by construction).
    a = ht.hot_tear_assessment(0.40, 0.030)
    assert a.last_liquid_mn_s == pytest.approx(a.bulk_mn_s * ht.segregation_factor())


# --------------------------------------------------------------------------- #
# The soft OoM-coherence note — segregation amplifies 1.71 into the TENS (order robust, value cutoff-tuned)
# --------------------------------------------------------------------------- #
def test_critical_bulk_mn_s_is_in_the_tens_not_stoichiometric():
    # The bulk Mn:S a casting needs is an ORDER of magnitude above the stoichiometric 1.71 — the soft OoM note
    # reproducing the empirical "sound castings need Mn:S in the tens" rule from cited k, no tuning.
    crit = ht.critical_bulk_mn_s()                             # f_s = 0.95
    assert 10.0 < crit < 20.0
    assert crit > 8.0 * ht.MN_S_STOICH                         # an order of magnitude above stoichiometry


def test_critical_bulk_mn_s_rises_with_the_cutoff_but_stays_in_the_tens():
    # The ORDER is cutoff-robust; the specific value is cutoff-tuned (f_s is a free knob).
    c90, c95, c99 = ht.critical_bulk_mn_s(0.90), ht.critical_bulk_mn_s(0.95), ht.critical_bulk_mn_s(0.99)
    assert c90 < c95 < c99                                     # deeper cutoff → more enrichment → higher bar
    assert 5.0 < c90 and c99 < 60.0                            # but always the tens, never near 1.71


def test_critical_bulk_mn_s_brackets_the_empirical_anchor():
    # The amplification straddles the cited empirical line (Toledo 1993, ~20) across the plausible cutoff band.
    assert ht.critical_bulk_mn_s(0.90) < ht.EMPIRICAL_MN_S_CASTING < ht.critical_bulk_mn_s(0.99)


# --------------------------------------------------------------------------- #
# The demonstration — segregation flips a BULK-CLEAR heat (the build's reason to exist)
# --------------------------------------------------------------------------- #
def test_segregation_tears_a_heat_that_clears_bulk_stoichiometry():
    # A heat comfortably above the bulk MnS stoichiometry (Mn:S 10 ≥ 1.71 → NOT red-short at the forge) still
    # hot-tears, because the segregated interdendritic film falls below 1.71. This is the disagreement the
    # build exists to show — it is a real discrimination, not the module's if-rule asserted back to itself.
    a = ht.hot_tear_assessment(Mn_pct=0.30, S_pct=0.030)       # bulk Mn:S = 10
    assert a.bulk_forms_mns                                    # the bath clears stoichiometry ...
    assert not a.film_forms_mns and a.hot_tear                 # ... but the film does not → tear


def test_mushet_lever_more_manganese_same_sulfur_closes_the_hot_tear():
    # The fix is manganese (Mushet), but the threshold is segregation-amplified (the tens, not 1.71).
    S = 0.030
    low = ht.hot_tear_assessment(Mn_pct=0.30, S_pct=S)         # bulk Mn:S 10 < critical (~14) → tears
    fixed = ht.hot_tear_assessment(Mn_pct=0.66, S_pct=S)       # bulk Mn:S 22 > critical → sound
    assert low.hot_tear and not fixed.hot_tear
    assert low.bulk_mn_s < low.critical_bulk_mn_s < fixed.bulk_mn_s


# --------------------------------------------------------------------------- #
# The two-tier disagreement — the flat sulfur risk line both under- and over-warns
# --------------------------------------------------------------------------- #
def test_in_spec_low_manganese_heat_still_tears_risk_line_under_warns():
    # Sulfur within slag's flat 0.040 % spec (the high-sulfur risk NOT raised) yet the casting tears — the
    # flat, Mn-blind line cannot see the segregation. (slag raises HIGH_SULFUR on exactly S > MAX_SULFUR_PCT,
    # so this predicate IS slag's risk gate — no need to route a heat through slag.desulfurize to confirm it.)
    S = 0.030
    assert S < slag.MAX_SULFUR_PCT                             # slag would clear it (no high-sulfur flag)
    assert ht.hot_tear_assessment(Mn_pct=0.30, S_pct=S).hot_tear


def test_over_spec_high_manganese_heat_is_sound_risk_line_over_warns():
    # Sulfur over the spec (risk-flagged) but enough manganese to keep even the segregated film MnS — sound.
    S = 0.060
    assert S > slag.MAX_SULFUR_PCT                             # slag raises the high-sulfur risk ...
    assert not ht.hot_tear_assessment(Mn_pct=1.50, S_pct=S).hot_tear   # ... yet the casting is sound


# --------------------------------------------------------------------------- #
# Phase + time / by construction — sulfur-free always sound; the balance is slag's
# --------------------------------------------------------------------------- #
def test_sulfur_free_heat_never_tears():
    a = ht.hot_tear_assessment(Mn_pct=0.50, S_pct=0.0)
    assert a.film_forms_mns and not a.hot_tear

def test_manganese_free_sulfurous_heat_tears():
    assert ht.hot_tear_assessment(Mn_pct=0.0, S_pct=0.030).hot_tear

def test_film_free_sulfur_is_the_slag_balance_on_the_film():
    # BY CONSTRUCTION: the film free sulfur is exactly slag.manganese_sulfide applied to the enriched liquid.
    Mn, S = 0.30, 0.030
    a = ht.hot_tear_assessment(Mn, S)
    Mn_L, S_L = ht.last_liquid_mn_s(Mn, S)
    assert a.free_sulfur_film_pct == slag.manganese_sulfide(Mn_L, S_L).free_sulfur_pct


def test_verdict_string_names_the_segregation_contrast():
    torn = ht.hot_tear_assessment(0.30, 0.030).verdict        # bulk-clear but film tears
    sound = ht.hot_tear_assessment(0.66, 0.030).verdict
    assert "bath clears" in torn and "HOT-TEAR" in torn
    assert "sound casting" in sound


# --------------------------------------------------------------------------- #
# The orchestrator seam + the two-tier flag
# --------------------------------------------------------------------------- #
def test_hot_tear_check_raises_flag_and_records_a_step():
    out = ht.hot_tear_check(_heat(Mn=0.30, S=0.030))
    assert out.has_defect(ht.HOT_TEAR)
    assert out.history[-1].name == "hot-tear-check" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (ht.HOT_TEAR,)


def test_hot_tear_check_sound_heat_stays_clean():
    out = ht.hot_tear_check(_heat(Mn=0.66, S=0.030))
    assert not out.has_defect(ht.HOT_TEAR)
    assert out.is_clean and out.history[-1].in_spec is True


def test_hot_tear_check_does_not_change_composition():
    h = _heat(Mn=0.30, S=0.030)
    out = ht.hot_tear_check(h)
    assert out.composition == h.composition                    # the verdict reads state, it does not move S


def test_hot_tear_check_flag_is_idempotent():
    once = ht.hot_tear_check(_heat(Mn=0.30, S=0.030))
    twice = ht.hot_tear_check(once)
    assert twice.defects.count(ht.HOT_TEAR) == 1
    assert twice.history[-1].flags_added == ()
