"""Front-end B3 (phosphorus leg #2) — the cited Healy L_P model vs a SECOND slag system (Suito & Inoue 1984).

These tests pin the *durable* facts of :mod:`steel.slag_lp2_validation`: both transcription guards
(the Eq.(3) k_P multi-column cross-check; the per-row oxide-sum) are satisfied, the holdout is a
genuine second system (Na₂O/BaO fluxes absent from Drain's BOS, at converter temperature with liquid
low-carbon iron — not the rejected hot-metal sets), and the finding is *carries-plus-an-edge*: the BaO
leg independently reproduces the Drain over-prediction (~×1.5), while the Na₂O leg under-predicts —
read cleanly as the matched-CaO contrast (Healy blind to soda's basicity). Claims are asserted as
**signs / order-of-magnitude bands** — never exact numbers. Crucially: this study **fits nothing** —
it reads the pinned 1970 Healy coefficients from :mod:`steel.slag`, which the tests assert are unchanged.
"""
from __future__ import annotations

import pytest

from steel import slag_lp2_validation as lv
from steel import slag
from steel.slag import phosphorus_partition


# --------------------------------------------------------------------------- #
# The transcription guards — the di-crosscheck baked into the suite (the blocking items)
# --------------------------------------------------------------------------- #
def test_kp_consistency_guard_clean():
    """Every row's observed log k_P matches the paper's Eq.(3) within its Fig.1 scatter (no fat-fingered digit)."""
    bad = lv.validate_kp_consistency()
    assert bad == [], f"k_P inconsistent with Eq.(3) on rows: {bad}"


def test_oxide_sum_guard_clean():
    """Every row's seven oxide columns sum to 100 ± 2 mass % (a dropped/duplicated-column catch)."""
    bad = lv.validate_oxide_sum()
    assert bad == [], f"oxide columns do not sum to ~100 on rows: {bad}"


def test_summary_reports_both_guards_clean():
    v = lv.summary()
    assert v.kp_consistency_clean is True
    assert v.oxide_sum_clean is True


# --------------------------------------------------------------------------- #
# The holdout is a genuine SECOND system at controlled conditions (the circularity + confound gates)
# --------------------------------------------------------------------------- #
def test_holdout_shape_and_converter_temperature():
    """23 heats (12 BaO + 11 Na₂O), all at 1550 °C = 1823 K — inside Drain's 1550–1700 °C window."""
    assert len(lv.HOLDOUT) == 23
    assert len(lv.HOLDOUT_BAO) == 12 and len(lv.HOLDOUT_NA2O) == 11
    for p in lv.HOLDOUT:
        assert p.T_K == pytest.approx(1823.15, abs=0.5)     # single converter temperature, not hot metal


def test_holdout_is_a_different_slag_system():
    """Every row carries a foreign basic flux (Na₂O or BaO) absent from Drain's BOS — the 'second system'."""
    for p in lv.HOLDOUT:
        assert p.flux in ("Na2O", "BaO")
        assert p.flux_pct > 0.0
    assert {p.flux for p in lv.HOLDOUT} == {"Na2O", "BaO"}


def test_metal_is_liquid_low_carbon_not_hot_metal():
    """The metal carries measurable dissolved [%O] (oxidizing FeO_x system) — evidence it is NOT C-saturated.

    The rejected hot-metal sets (Zhou/Im) used carbon-saturated iron at 1300 °C; here the tabulated
    [%O] ≈ 0.085–0.19 % is incompatible with carbon saturation, so temperature AND metal chemistry match
    Healy's converter regime and only the slag varies.
    """
    for p in lv.HOLDOUT:
        assert 0.05 < p.o_metal < 0.25


def test_lp_defined_as_healy_mass_ratio():
    """Measured L_P is the (%P)/[%P] mass ratio — same definition as Healy (not a phosphate capacity)."""
    p = lv.HOLDOUT_BAO[0]
    assert p.lp == pytest.approx(p.p2o5 * lv.P_IN_P2O5 / p.p_metal, rel=1e-9)


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


def test_total_iron_maps_from_feo_plus_ferric():
    """feto_total = FeO + 0.9·Fe₂O₃ feeds Slag.FeO, so pct_Fe_total recovers the %Fe_t Healy reads."""
    p = lv.HOLDOUT_BAO[0]
    s = lv.slag_from_point(p)
    assert s.FeO == pytest.approx(p.FeO + lv.FEO_PER_FE2O3 * p.Fe2O3, rel=1e-9)
    assert s.pct_Fe_total == pytest.approx(s.FeO * (55.85 / 71.85), rel=1e-3)


def test_healy_reads_no_flux_oxide():
    """The reconstructed Slag has no Na₂O/BaO field — Healy is structurally blind to the flux (the leg's point)."""
    assert not hasattr(lv.slag_from_point(lv.HOLDOUT_NA2O[0]), "Na2O")
    assert not hasattr(lv.slag_from_point(lv.HOLDOUT_BAO[0]), "BaO")


# --------------------------------------------------------------------------- #
# The finding — BaO carries (confirms Drain on a 2nd system); Na₂O is a signed non-CaO-basicity edge
# --------------------------------------------------------------------------- #
def test_bao_leg_carries_like_drain():
    """The BaO slags over-predict a modest, consistent ~×1.5 — reproducing the Drain leg on a 2nd system."""
    b = lv.summary().bao
    assert b.n == 12
    assert b.mean_log > 0.0                 # over-predicts, like Drain
    assert 10 ** b.mean_log < 2.5           # modest — a benchmark, not a failure (Drain was ×1.48)
    assert 10 ** b.std_log < 2.5            # tight, consistent bias


def test_bao_high_lime_over_predicts_the_drain_pattern():
    """Within the BaO leg the high-basicity rows run highest — the same high-lime over-prediction as Drain."""
    rs = {r.label: r.resid for r in lv.residuals(lv.HOLDOUT_BAO)}
    assert rs[805] > 0.2                    # v≈2 high-lime row over-predicts ~×2, as Drain's B-series did


def test_na2o_leg_under_predicts():
    """The Na₂O slags UNDER-predict — Healy is blind to soda's basicity (the signed opposite of high-lime bias)."""
    n = lv.summary().na2o
    assert n.n == 11
    assert n.mean_log < -0.2                # under-predicts (negative log-residual), pooled ≳ ×0.4 low


def test_matched_cao_contrast_isolates_the_soda_effect():
    """At matched CaO the BaO rows sit above the Na₂O rows — the CaO-isolated non-CaO-basicity gap (the tooth)."""
    c = lv.summary().contrast
    assert c.n_bao >= 3 and c.n_na2o >= 3
    assert c.bao_mean > c.na2o_mean         # soda dephosphorizes more than baryta at the same lime
    assert c.gap > 0.4                      # a real ≳ ×2.5 gap Healy's CaO-only term cannot see
    assert c.bao_mean > 0.0 > c.na2o_mean   # BaO over-, Na₂O under-predicts within the window


def test_soda_under_prediction_is_robust_across_reads():
    """The ~×5 soda under-prediction shows up in BOTH the full-range pooled difference AND the window.

    The window is matched on CaO but NOT on Fe_t, so it alone is not a clean flux-only measure; the
    robustness is that the full-range pooled per-table difference (each row's own CaO+Fe_t inside its
    Healy prediction) agrees with the window gap. Both land at ~0.7 log (~×5).
    """
    v = lv.summary()
    pooled_gap = v.bao.mean_log - v.na2o.mean_log
    assert pooled_gap > 0.4                                    # Na₂O under-predicts vs BaO over the full range
    assert abs(pooled_gap - v.contrast.gap) < 0.2             # window agrees with the full-range read


def test_gap_is_order_consistent_with_paper_cao_equivalency():
    """The soda gap is the right ORDER as the paper's 1.2×/0.9× CaO-equivalency — order-of-magnitude, not precise.

    Deliberately a wide band: the matched-CaO window is not Fe_t-matched, so the 0.69 ≈ 0.67 near-match
    is partly coincidental — this only pins the sign and rough magnitude (same-paper corroboration).
    """
    v = lv.summary()
    assert v.equiv_expectation > 0.0
    assert 0.3 < v.equiv_expectation < 1.1                     # a ~0.7 log CaO-equivalency expectation
    assert abs(v.contrast.gap - v.equiv_expectation) < 0.5    # SAME ORDER — not asserted as a tight match
