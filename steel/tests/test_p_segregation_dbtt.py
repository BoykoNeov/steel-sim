"""A2-B — the phosphorus GB-coverage → DBTT mechanism (the flag behind grain.ITT_K_P).

These tests pin the *durable* facts of :mod:`steel.p_segregation_dbtt`, a mechanistic overlay with
**no claimable tooth** (the discipline of the temper-embrittlement gate and the B3 legs). The load
-bearing assertions are: (1) the cited coverage→DBTT relations are transcribed correctly and are
**per-steel / cross-domain** (slope span ≈ 4.3×, grain-size span ≈ 2×); (2) the McLean bridge is a
monotone, flagged **sensitivity** leg; (3) composing the two reproduces the documented 40–78 °C/0.1 wt%
bulk bracket **as a span that contains it**, never as a pin; and (4) — the NO-TOOTH guard — there is no
independent in-domain holdout (the only ferritic/transgranular relation is the fitted IF steel), and
the engine's :data:`steel.grain.ITT_K_P` is read but **not changed**. Claims are asserted as
signs / rankings / order-of-magnitude bands, never exact numbers.
"""
from __future__ import annotations

import pytest

from steel import grain
from steel import p_segregation_dbtt as ps


# --------------------------------------------------------------------------- #
# Transcription guard (di-crosscheck) + the cited relations are reproduced exactly
# --------------------------------------------------------------------------- #
def test_relations_transcription_guard_clean():
    """The stored (slope, intercept) coefficients evaluate self-consistently (no fat-fingered digit)."""
    assert ps.validate_relations() is True


def test_cited_equations_reproduced():
    """Each cited line evaluates to its published form — the numbers behind the bias map."""
    assert ps.IF_STEEL.dbtt_C(10.0) == pytest.approx(3.12 * 10.0 - 118.87)
    assert ps.SA508_FIXED_H.dbtt_C(10.0) == pytest.approx(13.31 * 10.0 - 339.28)
    assert ps.SA508_PAGS_34.dbtt_C(10.0) == pytest.approx(13.13 * 10.0 - 335.70)
    assert ps.SA508_PAGS_112.dbtt_C(10.0) == pytest.approx(6.69 * 10.0 - 223.87)


def test_coverage_must_be_nonnegative():
    with pytest.raises(ValueError):
        ps.IF_STEEL.dbtt_C(-1.0)


# --------------------------------------------------------------------------- #
# Gap 2 — the bias map: per-steel, cross-domain, NON-transferable
# --------------------------------------------------------------------------- #
def test_slope_spans_several_fold_across_steels():
    """The coverage→DBTT slope is not universal — it spans ≈ 4× (the front-end '8620 wall')."""
    s = ps.summary()
    assert s.slope_span == pytest.approx(4.27, abs=0.2)
    assert s.slope_span > 3.0                      # unambiguously non-transferable


def test_within_steel_grain_size_moves_the_slope():
    """Even within ONE steel the slope moves ≈ 2× with prior-austenite grain size (13.13 vs 6.69)."""
    span = ps.naive_transfer_bias(ps.SA508_PAGS_112, ps.SA508_PAGS_34)
    assert span == pytest.approx(1.96, abs=0.1)


def test_naive_transfer_bias_is_the_cost_of_assuming_universality():
    """Applying the IF slope to SA508 under-states its P sensitivity ~4× — the concrete graft cost."""
    assert ps.naive_transfer_bias(ps.IF_STEEL, ps.SA508_FIXED_H) == pytest.approx(4.27, abs=0.2)


def test_no_relation_is_in_the_transgranular_engine_domain():
    """The domain split: EVERY coverage→DBTT relation is intergranular — none is the engine's
    transgranular-cleavage domain, so there is no in-domain holdout at all (the stronger no-tooth fact).

    IF is ferritic in *matrix* but intergranular in *fracture* (interstitial-free → no solute carbon
    competes with P at the boundaries — the cold-work-embrittlement literature is explicit it is
    intergranular). The SA508 rows are tempered-martensite/intergranular. So `in_pickering_domain` is
    False for all.
    """
    assert [r for r in ps.COVERAGE_DBTT_RELATIONS if r.in_pickering_domain] == []
    for r in ps.COVERAGE_DBTT_RELATIONS:
        assert r.fracture == "intergranular"
    assert ps.IF_STEEL.matrix == "ferritic"      # ferritic MATRIX, but intergranular FRACTURE


# --------------------------------------------------------------------------- #
# Gap 1 — the McLean bridge is a monotone, FLAGGED sensitivity leg
# --------------------------------------------------------------------------- #
def test_mclean_coverage_zero_at_zero_phosphorus():
    assert ps.mclean_gb_coverage(0.0, 450.0) == 0.0


def test_mclean_coverage_is_a_fraction():
    x = ps.mclean_gb_coverage(0.10, 400.0)
    assert 0.0 < x < 1.0


def test_mclean_rises_with_bulk_P_and_falls_with_T_seg():
    """Monotone both ways — more P segregates, hotter boundaries hold less (the entropy term)."""
    assert ps.mclean_gb_coverage(0.03, 450.0) > ps.mclean_gb_coverage(0.01, 450.0)
    assert ps.mclean_gb_coverage(0.03, 350.0) > ps.mclean_gb_coverage(0.03, 550.0)


def test_mclean_rejects_bad_inputs():
    with pytest.raises(ValueError):
        ps.mclean_gb_coverage(-0.01, 450.0)
    with pytest.raises(ValueError):
        ps.mclean_gb_coverage(0.03, -300.0)      # below absolute zero


# --------------------------------------------------------------------------- #
# The synthesis — the composed bulk slope reproduces the bracket AS A SPAN (never a pin)
# --------------------------------------------------------------------------- #
def test_composed_slope_falls_with_segregation_temperature():
    """The bulk slope inherits the McLean T-sensitivity — one steel gives a *range*, not a value."""
    hot = ps.composed_bulk_slope_C_per_0p1(ps.SA508_FIXED_H, 550.0)
    cool = ps.composed_bulk_slope_C_per_0p1(ps.SA508_FIXED_H, 350.0)
    assert cool > hot > 0.0


def test_composed_range_contains_the_documented_bracket_and_the_engine_flag():
    """The ~20× composed span brackets the documented 40–78 and the engine's flagged 50 — the payoff."""
    s = ps.summary()
    assert s.composed_min < 40.0 and s.composed_max > 78.0     # span straddles the bracket
    assert s.bracket_contained is True
    assert s.engine_value_inside is True


def test_no_single_pinned_value_the_span_is_wide():
    """The whole point: the composed slope is a *wide* band (order of magnitude), not a coefficient."""
    s = ps.summary()
    assert s.composed_max / s.composed_min > 10.0             # irreducibly steel-/path-dependent


# --------------------------------------------------------------------------- #
# THE NO-TOOTH GUARD + no engine touch (the honest posture, defended by tests)
# --------------------------------------------------------------------------- #
def test_no_independent_in_domain_holdout_so_no_tooth():
    """The teeth verdict: the only in-domain steel is the fitted IF steel → cross-steel is cross-domain."""
    assert ps.summary().has_independent_in_domain_holdout is False


def test_engine_itt_k_p_is_untouched_and_flagged():
    """This module reads grain.ITT_K_P for cross-reference but changes NOTHING — it stays 500 °C/wt%."""
    assert grain.ITT_K_P == 500.0
    assert ps.ITT_K_P_AS_C_PER_0P1 == 50.0
    lo, hi = ps.BULK_SLOPE_BRACKET_C_PER_0P1
    assert lo < ps.ITT_K_P_AS_C_PER_0P1 < hi                  # the flag sits mid-bracket


def test_segregation_energy_matches_the_repo_cited_value():
    """ΔG_seg is the SAME cited Yang–Chen/Erhart–Grabke value the repo already carries."""
    assert (ps.DG_SEG_A, ps.DG_SEG_B) == (-34469.0, 22.9)
