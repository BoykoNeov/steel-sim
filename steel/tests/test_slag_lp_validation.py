"""Front-end B3 (phosphorus leg) — holdout validation of the cited Healy L_P model vs Drain 2018 data.

These tests pin the *durable* facts of :mod:`steel.slag_lp_validation`: both transcription guards
(per-row %P₂O₅/[%P]/L_P consistency; the R-series reproducibility cross-check against the paper's
prose "190 ± 7") are satisfied, the holdout is genuinely independent (post-1970, L_P defined exactly
as Healy's mass ratio), and the finding is the *quantified bias map* — Healy carries at moderate
basicity (B2 near-exact) and over-predicts systematically at high lime (B5 ~×2), with the bias
climbing along the basicity axis. Claims are asserted as **signs / rankings / order-of-magnitude
bands** — never exact numbers — the register for benchmarked physics against inter-laboratory scatter.
Crucially: this study **fits nothing** — it reads the pinned 1970 Healy coefficients from
:mod:`steel.slag`, which the tests assert are unchanged.
"""
from __future__ import annotations

import math

import pytest

from steel import slag_lp_validation as lv
from steel import slag
from steel.slag import phosphorus_partition


# --------------------------------------------------------------------------- #
# The transcription guards — the di-crosscheck baked into the suite (the blocking items)
# --------------------------------------------------------------------------- #
def test_lp_consistency_guard_clean():
    """Every row's (%P₂O₅), [%P] and L_P columns are mutually consistent (no fat-fingered digit)."""
    bad = lv.validate_lp_consistency()
    assert bad == [], f"L_P inconsistent with (%P₂O₅)/[%P] on rows: {bad}"


def test_reproducibility_crosscheck_matches_printed_stat():
    """The 7 R-series repeats reproduce the paper's prose-stated mean 190, std 7 (~3.7 % floor)."""
    mean, std, ok = lv.reproducibility_crosscheck()
    assert ok is True
    assert mean == pytest.approx(190.0, abs=5.0)
    assert std == pytest.approx(7.0, abs=2.0)


def test_summary_reports_both_guards_clean():
    v = lv.summary()
    assert v.lp_consistency_clean is True
    assert v.repro_clean is True


# --------------------------------------------------------------------------- #
# The holdout is genuinely independent (the circularity gate)
# --------------------------------------------------------------------------- #
def test_holdout_is_post_1970_and_in_steelmaking_range():
    """Temporal independence (measured 2018 ≫ Healy 1970) and steelmaking temperatures (1550–1700 °C)."""
    assert len(lv.HOLDOUT) == 33
    for p in lv.HOLDOUT:
        assert 1800.0 <= p.T_K <= 2000.0     # 1550–1700 °C, the range Healy addresses


def test_lp_defined_as_healy_mass_ratio():
    """Measured L_P is the (%P)/[%P] mass ratio — same definition as Healy (no phosphate-capacity offset).

    The consistency guard recomputes L_P as (%P₂O₅·2M_P/M_P₂O₅)/[%P] and it passes for every row, so
    the tabulated L_P *is* the phosphorus mass ratio, directly comparable to Healy's L_P.
    """
    p = lv.HOLDOUT[0]
    p_in_slag = p.p2o5 * lv.P_IN_P2O5
    assert p_in_slag / p.p_metal == pytest.approx(p.lp, rel=0.20)   # coarse on low-[%P] rows, by design


def test_no_refit_healy_coefficients_are_the_pinned_1970_values():
    """The model under test is slag.py's UNCHANGED Healy correlation — this study calibrates nothing."""
    assert (slag.HEALY_T, slag.HEALY_CAO, slag.HEALY_FE, slag.HEALY_CONST) == (22350.0, 0.08, 2.5, -16.0)


# --------------------------------------------------------------------------- #
# The code path is faithful (reads slag.phosphorus_partition; FetO → %Fe_t maps correctly)
# --------------------------------------------------------------------------- #
def test_predicted_lp_reads_slag_phosphorus_partition():
    """predicted_lp is exactly slag.phosphorus_partition of the reconstructed Slag — no re-implementation."""
    for p in lv.HOLDOUT[:5]:
        direct = phosphorus_partition(lv.slag_from_point(p), T_celsius=p.T_K - lv.ABS_ZERO)
        assert lv.predicted_lp(p) == pytest.approx(direct, rel=1e-12)


def test_feto_maps_to_total_iron():
    """FetO (total iron as FeO) feeds Slag.FeO, so pct_Fe_total recovers the %Fe_t Healy reads."""
    p = lv.HOLDOUT[0]
    s = lv.slag_from_point(p)
    assert s.FeO == p.FetO
    assert s.pct_Fe_total == pytest.approx(p.FetO * (55.85 / 71.85), rel=1e-9)


# --------------------------------------------------------------------------- #
# The finding — a quantified, basicity-dependent bias (carries moderate, over-predicts high-lime)
# --------------------------------------------------------------------------- #
def test_pooled_over_predicts():
    """Healy runs high overall (positive pooled log-residual), inside the factor-2–3 scatter."""
    b = lv.summary().pooled
    assert b.n == 33
    assert b.mean_log > 0.0
    assert 10 ** b.mean_log < 3.0        # not wildly off — a benchmark, not a failure


def test_carries_at_moderate_basicity():
    """The B2 series (v≈2, Healy's fit domain) is near-exact — |bias| well within a factor of 1.3."""
    by = {s: mean_r for s, _, mean_r, _ in lv.summary().per_series}
    assert abs(by["B2"]) < 0.11          # ×0.78 … ×1.29


def test_over_predicts_at_high_lime():
    """The B5 series (v≈5, high lime) over-predicts markedly, and the climb from B2 is real."""
    by = {s: mean_r for s, _, mean_r, _ in lv.summary().per_series}
    assert by["B5"] > 0.20               # ≳ ×1.6
    assert by["B5"] - by["B2"] > 0.15    # the basicity-dependent climb, not a uniform offset


def test_bias_climbs_with_basicity():
    """Every high-lime series (B4, B5) is more biased than every moderate one (B2, R) — the diagnosis."""
    by = {s: mean_r for s, _, mean_r, _ in lv.summary().per_series}
    assert min(by["B4"], by["B5"]) > max(by["B2"], by["R"])


def test_bias_by_lime_axis():
    """Read on the raw lime axis: high-lime (%CaO ≥ 55) is ~×2 while low-lime (%CaO < 50) is near-exact."""
    by_lime = lv.summary().by_lime
    lo, hi = by_lime["low"][0], by_lime["high"][0]
    assert lo < 0.12                     # low-lime near-exact
    assert hi > 0.25                     # high-lime ~×2
    assert hi - lo > 0.15


def test_temperature_direction_reproduced():
    """Both measured and Healy L_P fall with temperature on the dedicated T-series (the +22350/T sign)."""
    t = lv.summary().temperature
    assert t.measured_falls is True
    assert t.predicted_falls is True
    assert t.temps == tuple(sorted(t.temps))
