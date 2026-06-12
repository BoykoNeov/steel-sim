"""Cross-composition bainite validation (§20) — the wall quantified, the verdict asserted.

These tests pin the *durable* facts of :mod:`steel.cct_validation`: the bias-immune cited-anchor
wall (1080↔4340, no factor-2 reads), the eight-steel quantification, the even-handed factor
grading (no cited factor wins both metrics → per-steel anchoring vindicated), and the minimal-DOF
refit diagnosis. Claims are asserted as **rankings / sign-inversions / inequalities / order-of-
magnitude bands** — never exact numbers — the right register for ~factor-2 atlas reads.
"""
from __future__ import annotations

import math

import pytest

from steel import cct_validation as cv
from steel import austemper as au
from steel import kinetics as kin


# --------------------------------------------------------------------------- #
# The observable is well-posed: 700 °F is bainitic (Mₛ < 371.1 < Bs) for every steel
# --------------------------------------------------------------------------- #
def test_all_steels_in_austempering_window():
    for s in cv.CROSSCHECK_STEELS:
        assert cv.in_window(s), f"{s.name}: 371.1 °C not strictly inside Ms<T<Bs"


def test_two_anchors_are_the_cited_austemper_reads():
    """The two cited anchors carry austemper's careful read-offs verbatim (shared provenance)."""
    for name in ("1080", "4340"):
        assert cv.CROSSCHECK_BY_NAME[name].cited
        assert cv.CROSSCHECK_BY_NAME[name].t50_700F == pytest.approx(
            au.ATLAS_STEELS[name].t50_anchor)


# --------------------------------------------------------------------------- #
# The headline: bias-immune wall from the two CITED anchors only
# --------------------------------------------------------------------------- #
def test_cited_anchor_wall_is_sign_inverted():
    w = cv.cited_anchor_wall()
    assert w.measured_ratio > 1.0          # atlas: 4340 SLOWER than 1080
    assert w.bc_ratio < 1.0                # cited BC: 4340 predicted FASTER than 1080
    assert w.sign_inverted
    assert w.miss > 20.0                   # the ratio is missed by ≳ ×20 (≈ ×40)


def test_wall_reproduces_austemper_scale_gap():
    """The cited-anchor miss reproduces austemper's INDEPENDENT 1080/4340 scale gap → harness is correct."""
    gap = au.ANCHORED_SCALES["1080"] / au.ANCHORED_SCALES["4340"]
    assert cv.cited_anchor_wall().miss == pytest.approx(gap, rel=0.05)


# --------------------------------------------------------------------------- #
# The eight-steel quantification + even-handed factor grading
# --------------------------------------------------------------------------- #
def test_cited_bainite_factor_fails_cross_composition():
    g = cv.grade_factor("bainite")
    assert g.spearman < 0.3                 # essentially no cross-steel rank skill (the wall)
    assert g.inverts_1080                   # predicts the fastest-measured steel (1080) as slow


def test_metrics_are_anchor_invariant():
    """The two grading metrics cannot be an artifact of the anchor choice (a hostile-reviewer check)."""
    a = cv.grade_factors(anchor="1080")
    b = cv.grade_factors(anchor="4340")     # a slow, alloyed anchor — maximally different
    for which in ("bainite", "ferrite", "pearlite"):
        assert a[which].spearman == pytest.approx(b[which].spearman)
        assert a[which].log_resid_spread == pytest.approx(b[which].log_resid_spread)
        assert a[which].inverts_1080 == b[which].inverts_1080


def test_no_cited_factor_combines_ranking_and_magnitude():
    """PC ranks best, FC has tightest spread, none is both — so no usable cross-steel law stands."""
    g = cv.grade_factors()
    bc, pc, fc = g["bainite"], g["pearlite"], g["ferrite"]
    # Ranking (anchor-invariant): alloy-weighted factors order bainite better than the carbon-dominated one.
    assert pc.spearman > fc.spearman > bc.spearman
    assert bc.spearman == min(bc.spearman, pc.spearman, fc.spearman)         # BC fails ranking — the wall
    # Magnitude spread (anchor-invariant): FC tightest, PC widest — the best ranker is NOT the tightest.
    assert fc.log_resid_spread < bc.log_resid_spread
    assert fc.log_resid_spread < pc.log_resid_spread
    assert pc.log_resid_spread == max(bc.log_resid_spread, pc.log_resid_spread, fc.log_resid_spread)
    # None wins both: the best-ranking factor is not the tightest-magnitude factor.
    best_rank = max(g.values(), key=lambda x: x.spearman).which
    best_mag = min(g.values(), key=lambda x: x.log_resid_spread).which
    assert best_rank != best_mag
    # Even the tightest spread (~×3) is far worse than per-steel anchoring (~×1.3) → anchoring stands.
    assert 10 ** fc.log_resid_spread > 2.0


# --------------------------------------------------------------------------- #
# The minimal-DOF refit: a diagnosis (alloy-driven), not a new law
# --------------------------------------------------------------------------- #
def test_carbon_rebalance_improves_out_of_sample():
    h = cv.carbon_rebalance_holdout()
    assert h.lam < 1.0                                  # the fit down-weights carbon (the diagnosed bug)
    assert h.test_spearman_refit > h.test_spearman_bc   # better ranking on the disjoint TEST split
    assert h.test_spread_refit < h.test_spread_bc       # and tighter magnitude (both anchor-invariant)


def test_ranking_is_alloy_carried_not_confound_carried():
    """The carbon-deleted win is carried by the residual cited alloy factor, not by Bs/grain."""
    d = cv.refit_decomposition()
    assert d["alloy_only"] > d["Bs_and_grain_only"]     # composition drives the order, not the confounds
    assert d["alloy_only"] > 0.5                          # and it does so with real skill
    assert abs(d["grain_only"]) < 0.2                    # grain alone carries ~nothing


# --------------------------------------------------------------------------- #
# Provenance + non-circularity: this study reads the cited factors, never re-tunes them
# --------------------------------------------------------------------------- #
def test_cited_factors_are_unmodified_kinetics():
    """The graded factors are the unchanged kinetics coefficients (no shadow re-tuning here)."""
    assert kin.BAINITE_BC_COEFFS["C"] == 10.18          # the carbon coefficient under test
    s = cv.CROSSCHECK_BY_NAME["4340"]
    direct = kin.bainite_BC(s.comp["C"], Mn=s.comp["Mn"], Ni=s.comp["Ni"],
                            Cr=s.comp["Cr"], Mo=s.comp["Mo"])
    assert cv._factor_value(s.comp, "bainite") == pytest.approx(direct)
