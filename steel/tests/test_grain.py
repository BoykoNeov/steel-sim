"""Phase-5a validation: austenite grain growth + ASTM E112 bookkeeping.

5a is the foundation of Phase 5 (grain size & Hall–Petch — steel-production.md §12). Its
triad, in the project's three-leg shape:

* **Analytic limit ("recover the constant").** The growth law ``Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t``
  is *linear in t* by construction, so ``(Dᵐ − D₀ᵐ)/t`` is constant (the exact structure),
  the power-law asymptote ``D ∝ t^(1/m)`` holds for ``D ≫ D₀``, and the input ``Q`` is
  recovered from two temperatures (the grain-growth analogue of 1c's Avrami round-trip). The
  ASTM E112 ``G ↔ d`` pair round-trips exactly.
* **Dissipative-direction invariant (the rigor leg — grain growth has no mass-conservation
  analogue).** Growth is monotone (``D`` non-decreasing in t *and* T), the rate ``dD/dt`` is
  ``≥ 0`` and *decreasing* in t (the curvature driving force falls as grains coarsen) — a
  one-way direction, the dissipative cousin of an energy balance.
* **Benchmark — the teeth are a HOLDOUT.** Fit the kinetic constants on the 900 & 1200 °C
  rows of the cited S960MC table (with ``Q`` held at its cited value) and *predict* the
  held-out 1000 & 1100 °C rows → within ~16 %. A genuine cross-temperature prediction that
  could have missed. The full-table reproduction with the locked module constants is asserted
  only *loosely* (grain-growth fits are inherently scattered, and ``Q`` is weakly determined
  by this data — see grain-growth-source). This is the *only* genuinely falsifiable leg of
  Phase 5; 5c's sign-opposition is a by-construction demonstration, not teeth.
"""
import math

import numpy as np
import pytest
from scipy.optimize import least_squares

from projects.steel import grain
from projects.steel.kinetics import R_GAS, ABS_ZERO


# --------------------------------------------------------------------------- #
# Analytic limit — recover the constant
# --------------------------------------------------------------------------- #
def test_zero_hold_returns_initial_size_exactly():
    # The seam: no hold ⇒ the grain size entering the hold, byte-for-byte.
    assert grain.austenite_grain_size(1000.0, 0.0, d0=12.0) == pytest.approx(12.0, abs=0.0)


def test_growth_law_is_exactly_linear_in_time():
    # Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t  ⇒  (Dᵐ − D₀ᵐ)/t is constant in t (the conserved structure).
    d0, m = grain.GROWTH_D0, grain.GROWTH_M
    slopes = []
    for t in (0.5, 1.0, 2.0, 4.0, 8.0):
        D = grain.austenite_grain_size(1100.0, t, d0=d0)
        slopes.append((D ** m - d0 ** m) / t)
    assert np.allclose(slopes, slopes[0], rtol=1e-12)


def test_power_law_asymptote_d_proportional_t_to_1_over_m():
    # For D ≫ D₀ the initial size drops out and D ∝ t^(1/m): doubling t multiplies D by 2^(1/m).
    d0 = 0.01  # tiny seed so Dᵐ ≫ D₀ᵐ across the window
    t1, t2 = 100.0, 200.0
    D1 = grain.austenite_grain_size(1100.0, t1, d0=d0)
    D2 = grain.austenite_grain_size(1100.0, t2, d0=d0)
    assert D2 / D1 == pytest.approx(2.0 ** (1.0 / grain.GROWTH_M), rel=1e-6)


def test_arrhenius_Q_recovered_from_two_temperatures():
    # ln[(Dᵐ−D₀ᵐ) ratio] / (1/T1 − 1/T2) = −Q/R  → recover the input Q (the round-trip leg).
    d0, m = grain.GROWTH_D0, grain.GROWTH_M
    T1, T2, t = 950.0, 1150.0, 2.0
    g1 = grain.austenite_grain_size(T1, t, d0=d0) ** m - d0 ** m
    g2 = grain.austenite_grain_size(T2, t, d0=d0) ** m - d0 ** m
    inv = 1.0 / (T1 + ABS_ZERO) - 1.0 / (T2 + ABS_ZERO)
    Q_recovered = -R_GAS * math.log(g1 / g2) / inv
    assert Q_recovered == pytest.approx(grain.GROWTH_Q, rel=1e-9)


def test_astm_grain_size_number_round_trips_exactly():
    for G in (1.0, 4.5, 8.0, 10.0, 12.0):
        d = grain.grain_diameter_um(G)
        assert grain.astm_grain_size_number(d) == pytest.approx(G, abs=1e-12)


def test_astm_anchors_match_textbook():
    # The two universally-tabulated ASTM E112 anchors.
    assert grain.grain_diameter_um(1.0) == pytest.approx(254.0, rel=2e-3)
    assert grain.grain_diameter_um(8.0) == pytest.approx(22.5, rel=5e-3)


# --------------------------------------------------------------------------- #
# Dissipative-direction invariant — growth is one-way, the rate decays
# --------------------------------------------------------------------------- #
def test_grain_size_monotone_in_time_and_temperature():
    times = np.linspace(0.0, 10.0, 40)
    sizes = [grain.austenite_grain_size(1050.0, t) for t in times]
    assert np.all(np.diff(sizes) >= -1e-12)                       # never shrinks with time
    temps = np.linspace(850.0, 1250.0, 40)
    sizes_T = [grain.austenite_grain_size(T, 1.0) for T in temps]
    assert np.all(np.diff(sizes_T) >= -1e-12)                     # never shrinks with temperature


def test_growth_rate_nonnegative_and_decelerating():
    rates = [grain.grain_growth_rate(1100.0, t) for t in (0.5, 1.0, 2.0, 4.0, 8.0)]
    assert all(r >= 0.0 for r in rates)                          # one-way (dD/dt ≥ 0)
    assert np.all(np.diff(rates) < 0.0)                          # decelerates as grains coarsen


def test_growth_rate_rises_with_temperature():
    # The Arrhenius driving force, read at the SAME grain size (t = 0 ⇒ D = D₀ for both), so the
    # comparison is the rate *constant*, not confounded by the hotter sample's already-coarser
    # grain at a later instant. ~69× over 1000 → 1200 °C.
    assert grain.grain_growth_rate(1200.0, 0.0) > 10.0 * grain.grain_growth_rate(1000.0, 0.0)


# --------------------------------------------------------------------------- #
# Benchmark — the teeth: a cross-temperature HOLDOUT of the cited S960MC data
# --------------------------------------------------------------------------- #
def _fit_constants(temp_C, time_h, grain_um, Q=grain.GROWTH_Q):
    """Refit (log10 K0, D0, m) to a grain-size table with Q held at its cited value."""
    Tg, tg = np.meshgrid(temp_C + ABS_ZERO, time_h, indexing="ij")
    Tf, tf, Df = Tg.ravel(), tg.ravel(), grain_um.ravel()

    def resid(p):
        logK0, D0, m = p
        return (D0 ** m + 10.0 ** logK0 * np.exp(-Q / (R_GAS * Tf)) * tf) ** (1.0 / m) - Df

    sol = least_squares(resid, [19.0, 14.0, 4.2])
    logK0, D0, m = sol.x
    return 10.0 ** logK0, D0, m


def test_holdout_predicts_unseen_temperatures():
    # Fit on the EXTREME temperatures (900 & 1200 °C), predict the held-out middle rows.
    fit_idx, hold_idx = [0, 3], [1, 2]
    K0, D0, m = _fit_constants(
        grain.S960MC_TEMP_C[fit_idx], grain.S960MC_TIME_H, grain.S960MC_GRAIN_UM[fit_idx],
    )
    err_pct = []
    for i in hold_idx:
        T = grain.S960MC_TEMP_C[i]
        for j, t in enumerate(grain.S960MC_TIME_H):
            pred = grain.austenite_grain_size(T, t, d0=D0, m=m, K0=K0)
            measured = grain.S960MC_GRAIN_UM[i, j]
            err_pct.append(abs(pred - measured) / measured)
    err_pct = np.array(err_pct)
    # A genuine prediction of unseen temperatures — could have missed; lands within ~16 %.
    assert err_pct.max() < 0.20
    assert err_pct.mean() < 0.10


def test_locked_constants_reproduce_full_table_loosely():
    # The shipped module constants vs the whole cited table — asserted LOOSELY (scattered data).
    abs_err, pct_err = [], []
    for i, T in enumerate(grain.S960MC_TEMP_C):
        for j, t in enumerate(grain.S960MC_TIME_H):
            pred = grain.austenite_grain_size(T, t)
            measured = grain.S960MC_GRAIN_UM[i, j]
            abs_err.append(abs(pred - measured))
            pct_err.append(abs(pred - measured) / measured)
    assert np.mean(abs_err) < 4.0          # mean abs error a few µm on 13–111 µm grains
    assert np.max(pct_err) < 0.22          # worst case on the smallest (900 °C) grains


def test_overheating_coarsens_grain_the_teaching_point():
    # The §12 payoff in 5a terms: a hotter austenitize gives a markedly coarser PAGS.
    fine = grain.austenite_grain_size(900.0, 1.0)
    coarse = grain.austenite_grain_size(1200.0, 1.0)
    assert coarse > 3.0 * fine
    # ...and a coarser grain is a smaller ASTM number (G falls as d rises).
    assert grain.astm_grain_size_number(coarse) < grain.astm_grain_size_number(fine)


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        grain.austenite_grain_size(1000.0, -1.0)
    with pytest.raises(ValueError):
        grain.austenite_grain_size(1000.0, 1.0, d0=0.0)
    with pytest.raises(ValueError):
        grain.austenite_grain_size(-300.0, 1.0)          # below absolute zero
    with pytest.raises(ValueError):
        grain.astm_grain_size_number(0.0)
