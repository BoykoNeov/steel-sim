"""Front-end B3 — holdout validation of the cited C_S model against measured Nzotta 1998 data.

These tests pin the *durable* facts of :mod:`steel.slag_validation`: the transcription guard
(di-crosscheck) is satisfied, the holdout is genuinely independent (no MnO/FeO, post-1986,
in-temperature-domain), the model **carries** on the basic slags (consistent mild bias, tight
scatter, perfect within-temperature ranking, reproduced temperature slope), and the two named
edges (acidic under-prediction, MnO over-prediction) are real and located. Claims are asserted as
**rankings / sign / order-of-magnitude bands** — never exact numbers — the right register for
benchmarked physics against factor-2–3 inter-laboratory scatter.
"""
from __future__ import annotations

import math

import pytest

from steel import slag_validation as sv
from steel.slag import sulfide_capacity


# --------------------------------------------------------------------------- #
# The transcription guard — the di-crosscheck baked into the suite (the blocking item)
# --------------------------------------------------------------------------- #
def test_transcription_average_consistency():
    """Every tabulated average C_S reproduces the mean of its listed repeats (no fat-fingered digit)."""
    bad = sv.validate_transcription()
    assert bad == [], f"transcription mismatch (tabulated avg ≠ mean of repeats): {bad}"


def test_summary_reports_transcription_clean():
    assert sv.summary().transcription_clean is True


# --------------------------------------------------------------------------- #
# The holdout is genuinely independent (the circularity gate)
# --------------------------------------------------------------------------- #
def test_holdout_has_no_mno_or_feo():
    """The clean holdout dodges slag.py's fit-to-C_S Λ values — no MnO, no FeO in any point."""
    for p in sv.HOLDOUT:
        assert p.x.get("MnO", 0.0) == 0.0
        s = sv.slag_from_point(p)
        assert s.MnO == 0.0 and s.FeO == 0.0


def test_holdout_is_post_1986_and_in_temperature_domain():
    """Temporal independence (measured 1998 > S–S 1986) and in-domain temperatures (1400–1700 °C)."""
    for p in sv.HOLDOUT:
        assert p.source == "Nzotta 1998 (present work)"
        assert 1673.0 <= p.T_K <= 1973.0     # inside S–S's stated 1400–1700 °C validity


def test_composition_mole_fractions_sum_to_one():
    """SiO₂ is filled as the remainder — the listed cations + SiO₂ must close to unity."""
    for p in sv.HOLDOUT + sv.MNO_DIAGNOSTIC + sv.LITERATURE_1773:
        assert sum(p.x.values()) == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# The code path is faithful (wt%-reconstruction round-trips; reads slag.sulfide_capacity)
# --------------------------------------------------------------------------- #
def test_slag_reconstruction_recovers_optical_basicity_and_cs():
    """Q2/1873 (the advisor's hand-verified path): Λ ≈ 0.683 and log C_S ≈ −3.24."""
    q2 = next(p for p in sv.HOLDOUT if p.label == "Q2" and p.T_K == 1873)
    s = sv.slag_from_point(q2)
    assert s.optical_basicity == pytest.approx(0.683, abs=0.005)
    pred = sv.predicted_log_cs(q2)
    assert pred == pytest.approx(-3.24, abs=0.02)
    # and it really is reading slag.sulfide_capacity (not a private re-implementation)
    assert pred == pytest.approx(math.log10(sulfide_capacity(s, T_celsius=1873 - 273.15)))


# --------------------------------------------------------------------------- #
# THE HEADLINE: it carries on the basic slags (consistent bias, tight scatter)
# --------------------------------------------------------------------------- #
def test_basic_holdout_carries_tight_and_consistent():
    """The 9 basic slags: a consistent mild bias (~×1.4) with tight scatter (< ×1.4) — it carries."""
    bb = sv.summary().holdout_basic
    assert bb.n == 9
    assert 1.2 < 10 ** bb.mean_log < 1.7          # consistent, modest overprediction
    assert 10 ** bb.std_log < 1.4                 # tight — well inside inter-lab factor-2–3 scatter


def test_within_temperature_ranking_is_perfect():
    """Composition ordering within each temperature is exact (the cross-composition skill)."""
    ranking = sv.within_temperature_ranking(sv.HOLDOUT)
    assert set(ranking) == {1773.0, 1823.0, 1873.0}      # 1923 K has a lone point → excluded
    for T, (rho, n) in ranking.items():
        assert rho == pytest.approx(1.0), f"{T} K ranking not perfect: ρ={rho}"


def test_temperature_slope_is_reproduced():
    """The S–S temperature term reproduces the measured C_S(T) slope on the repeated compositions."""
    slopes = sv.temperature_slopes(sv.HOLDOUT)
    assert slopes, "expected at least one repeated-composition slope (Q2, Q3, Q4)"
    for s in slopes:
        assert s.measured_slope > 0 and s.predicted_slope > 0          # both rise with temperature
        assert abs(s.predicted_slope - s.measured_slope) < 0.15        # within ~0.1 per 100 K


# --------------------------------------------------------------------------- #
# The two named edges are real and located (not asserted away)
# --------------------------------------------------------------------------- #
def test_acidic_edge_is_the_lowest_basicity_point_and_under_predicts():
    """The acidic edge: the lowest-Λ slag (Q1), sign-flipped and ≳ ×3 LOW."""
    e = sv.acidic_edge(sv.HOLDOUT)
    assert e.label == "Q1"
    assert e.Lambda == min(r.Lambda for r in sv.residuals(sv.HOLDOUT))
    assert e.resid < 0                            # under-predicts (sign-flipped vs the basic cluster)
    assert 10 ** abs(e.resid) > 3.0               # by more than a factor of three


def test_acidic_edge_is_a_single_point_flag_not_a_clean_literature_trend():
    """The literature does NOT cleanly corroborate the acidic edge — it is a single-point (Q1) flag.

    The literature's worst miss is its lowest-Λ point, but a *near-identical-Λ* neighbour fits fine
    and the two differ several-fold in measured C_S at the same basicity — internal scatter, not a
    reproduced acidic trend. This test pins the honest framing (advisor catch): the edge rests on Q1.
    """
    lit = sv.residuals(sv.LITERATURE_1773)
    by_lambda = sorted(lit, key=lambda r: r.Lambda)
    lowest, neighbour = by_lambda[0], by_lambda[1]
    assert abs(lowest.Lambda - neighbour.Lambda) < 0.01           # essentially the same basicity
    # yet their residuals diverge by more than a factor of three — that is scatter, not a trend
    assert abs(lowest.resid - neighbour.resid) > 0.5


def test_overlap_rows_cross_check_composition_and_cs():
    """The 4 rows printed in both Table 6 and Table 9 agree on composition AND C_S (end-to-end guard)."""
    assert sv.overlap_crosscheck() == [], "Table-6↔Table-9 overlap rows disagree"
    assert sv.summary().overlap_clean is True


def test_each_basic_composition_carries_the_same_bias():
    """Consistency on BOTH axes: every distinct basic composition (Q2/Q3/Q4/Q5) over-predicts ~×1.4."""
    pc = sv.per_composition_bias(sv.HOLDOUT)
    basic = {lab: b for lab, b in pc.items() if lab != "Q1"}
    assert set(basic) == {"Q2", "Q3", "Q4", "Q5"}
    for lab, b in basic.items():
        assert 1.2 < 10 ** b < 1.7, f"{lab} bias ×{10 ** b:.2f} outside the consistent band"


def test_mno_tier_over_predicts_and_is_weaker_independence():
    """The MnO diagnostic over-predicts ≳ ×3 — the located weak link (slag.py's fitted MnO Λ)."""
    mno = sv.summary().mno
    assert 10 ** mno.mean_log > 3.0               # systematic over-prediction
    # it is the weak-independence tier precisely because these points carry MnO
    assert all(p.x.get("MnO", 0.0) > 0.0 for p in sv.MNO_DIAGNOSTIC)


# --------------------------------------------------------------------------- #
# Posture: this study reads the model, it does not touch it
# --------------------------------------------------------------------------- #
def test_literature_sits_inside_the_inter_lab_band():
    """Corroboration: the model lands within the inter-laboratory scatter (bias within ~×2)."""
    lit = sv.summary().literature
    assert 0.5 < 10 ** lit.mean_log < 2.0
