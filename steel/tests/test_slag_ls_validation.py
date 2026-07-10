"""Front-end B3 (sulfur metal-partition leg) — PROBING the cited C_S→L_S conversion (Mohassab 2013).

These tests pin the *durable* facts of :mod:`steel.slag_ls_validation`: both transcription guards (the
Table-4-1 Log(Ls) three-column self-consistency; the per-row oxide-sum) are satisfied and the one
source-inconsistent row (S8) is excluded on purpose; the a_O-provenance gate holds (oxygen fixed by the
**gas**, not a deox equilibrium); and the finding is a *probe, not a validation* — the clean waterless
CO/CO₂ grade under-predicts L_S in a direction robust across the a_O method, the measured atmosphere
ladder rises with pH₂O (the engine-blind water edge), and the FeO oxygen anchor reads low. Every claim
is a **sign / order-of-magnitude band** — never an exact number. Crucially: this study **fits nothing** —
it reads the pinned Sosinsky–Sommerville + conversion coefficients from :mod:`steel.slag`, asserted
unchanged.
"""
from __future__ import annotations

import math

import pytest

from steel import slag
from steel import slag_ls_validation as lv
from steel.slag import sulfur_partition


# --------------------------------------------------------------------------- #
# The transcription guards — the di-crosscheck baked into the suite (the blocking items)
# --------------------------------------------------------------------------- #
def test_logls_consistency_guard_clean():
    """Every included Table-4-1 row's Log(Ls) equals log₁₀[(%S)/[%S]] (no fat-fingered digit)."""
    bad = lv.validate_logls_consistency()
    assert bad == [], f"Log(Ls) inconsistent with (%S)/[%S] on rows: {bad}"


def test_oxide_sum_guard_clean():
    """Every row's five oxide columns sum into the MgO-saturated closure band (a dropped-column catch)."""
    bad = lv.validate_oxide_sum()
    assert bad == [], f"oxide columns fall outside the closure band on rows: {bad}"


def test_source_inconsistent_row_is_excluded_on_purpose():
    """S8 (dissertation prints (S)=2.03, [%S]=6.21, Log Ls=-0.10 → but log10(2.03/6.21)=-0.49) is dropped.

    A di-crosscheck against the rendered PDF confirmed the transcription is faithful and the *source* is
    internally inconsistent; an unresolvable source typo is excluded, not baked. It must not reappear.
    """
    assert lv.SOURCE_INCONSISTENT_ROW == "S8"
    assert all(p.label != "S8" for p in lv.HOLDOUT)


def test_summary_reports_both_guards_clean():
    v = lv.summary()
    assert v.logls_consistency_clean is True
    assert v.oxide_sum_clean is True


# --------------------------------------------------------------------------- #
# The a_O-provenance gate + holdout shape (the circularity/confound gates)
# --------------------------------------------------------------------------- #
def test_holdout_shapes():
    """35 H₂/H₂O supplement heats (36 − S8) + 8 waterless CO/CO₂ + 8 mixed + 4 H₂/H₂O(Table 4-3)."""
    assert len(lv.HOLDOUT_H2O) == 35
    assert len(lv.HOLDOUT_CO) == 8
    assert len(lv.HOLDOUT_MIX) == 8
    assert len(lv.HOLDOUT_H2_T43) == 4
    assert len(lv.HOLDOUT) == 55


def test_a_O_is_gas_fixed_not_deox_derived():
    """Every heat carries a gas pO₂ that sets a_O — the independent oxygen lever (the clean-holdout gate).

    The whole point of L_S is the −log a_O term; a deox-derived a_O ([Al]/[O]) would import an external
    model into it. Here a_O comes from pO₂ via the Fe–O gas equilibrium, monotonic in pO₂.
    """
    for p in lv.HOLDOUT:
        assert p.pO2 > 0.0
    hot = lv.a_O_from_po2(1e-8, 1600.0)
    cold = lv.a_O_from_po2(1e-10, 1600.0)
    assert hot > cold > 0.0                                   # a_O rises with pO₂, both positive


def test_waterless_subset_is_dilute_and_low_carbon_regime():
    """The clean CO/CO₂ grade sits at dilute metal S (f_S ≈ 1) — unlike the SO₂-loaded Table-4-1 heats."""
    assert all(p.dilute for p in lv.HOLDOUT_CO)               # f_S ≈ 1 holds on the clean grade
    assert all(p.atmosphere == "CO/CO2" for p in lv.HOLDOUT_CO)
    assert not all(p.dilute for p in lv.HOLDOUT_H2O)          # the supplement is NOT dilute (named limit)


def test_no_refit_sulfide_and_conversion_coefficients_are_pinned():
    """The model under test is slag.py's UNCHANGED S–S C_S + conversion — this study calibrates nothing."""
    assert (slag.CS_A, slag.CS_B, slag.CS_C, slag.CS_D) == (22690.0, 54640.0, 43.6, -25.2)
    assert (slag.LS_T, slag.LS_CONST) == (-770.0, 1.30)


# --------------------------------------------------------------------------- #
# The code path is faithful (reads slag.sulfur_partition; no re-implementation)
# --------------------------------------------------------------------------- #
def test_predicted_reads_slag_sulfur_partition():
    """predicted_log_ls is exactly log10(slag.sulfur_partition(...)) at the gas-a_O — no re-implementation."""
    for p in lv.HOLDOUT_CO[:4]:
        direct = math.log10(sulfur_partition(lv.slag_from_point(p), lv.oxygen_ppm_gas(p), T_celsius=p.T_C))
        assert lv.predicted_log_ls(p) == pytest.approx(direct, rel=1e-12)


def test_slag_reconstruction_has_no_atmosphere_field():
    """The reconstructed Slag has no gas-atmosphere field — the engine is structurally blind (the edge's point)."""
    s = lv.slag_from_point(lv.HOLDOUT_H2_T43[0])
    assert not hasattr(s, "atmosphere")
    assert s.FeO > 0.0                                        # FeO carried (drives both Λ and the confound)


# --------------------------------------------------------------------------- #
# The finding — a PROBE (order-of-magnitude, under-predicts), not a validation
# --------------------------------------------------------------------------- #
def test_clean_grade_under_predicts_direction_robust_across_a_O_method():
    """The waterless CO/CO₂ grade under-predicts L_S — and BOTH a_O methods agree on the direction."""
    v = lv.summary()
    assert v.co_gas.n == 8
    assert v.co_gas.mean_log < 0.0                            # gas-a_O: under-predicts
    assert v.co_feo.mean_log < 0.0                            # FeO-anchor a_O: also under-predicts
    assert 10 ** v.co_gas.mean_log < 0.7                      # a factor of several low (order-of-magnitude)


def test_it_stays_order_of_magnitude_not_a_clean_factor():
    """The two a_O methods differ by ~×2 (a standard-state artifact) — so only order-of-magnitude is claimed."""
    v = lv.summary()
    gap = v.co_feo.mean_log - v.co_gas.mean_log               # FeO-anchor sits above gas-a_O
    assert 0.15 < gap < 0.7                                   # ~×1.5–5 method spread — magnitude not resolvable


def test_measured_atmosphere_ladder_rises_with_water():
    """The MEASURED L_S climbs CO/CO₂ < mixed < H₂/H₂O (the paper's own water edge — engine-independent)."""
    lad = {r.atmosphere: r for r in lv.summary().ladder}
    assert lad["CO/CO2"].mean_log_ls < lad["mix"].mean_log_ls < lad["H2/H2O"].mean_log_ls
    water = lad["H2/H2O"].mean_log_ls - lad["CO/CO2"].mean_log_ls
    assert water > 0.4                                        # water raises L_S ≳ ×2.5 (measured ~×5)


def test_atmosphere_edge_is_from_measurement_not_the_model():
    """The ladder is built from measured L_S only — the engine reads no atmosphere, so it cannot produce it."""
    rungs = lv.atmosphere_ladder()
    assert {r.atmosphere for r in rungs} == {"CO/CO2", "mix", "H2/H2O"}
    # the model's predicted L_S does NOT reproduce the measured rise (it is atmosphere-blind):
    pred_co = sum(r.predicted for r in lv.residuals(lv.HOLDOUT_CO)) / len(lv.HOLDOUT_CO)
    pred_h2 = sum(r.predicted for r in lv.residuals(lv.HOLDOUT_H2_T43)) / len(lv.HOLDOUT_H2_T43)
    assert pred_h2 - pred_co < 0.4                            # engine predicts far less spread than measured ~0.7


def test_feo_oxygen_anchor_reads_below_gas_equilibrium():
    """metal_oxygen_for_feo (Raoultian a_FeO≈X_FeO) sits ~×2 below the independent gas-equilibrium a_O."""
    a = lv.summary().anchor
    assert a.n == 55
    assert a.mean_log_ratio > 0.0                            # gas a_O > FeO-anchor a_O (the anchor reads low)
    assert 1.3 < 10 ** a.mean_log_ratio < 4.0               # ~×2, order-of-magnitude
