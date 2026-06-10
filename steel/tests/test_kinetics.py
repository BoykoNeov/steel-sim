"""Phase-1c validation triad for the transformation laws (Steel plan §3).

The three legs, kept separate (the analytical leg must not inherit benchmark slop):

* **Analytical limit** — (a) the **Avrami round-trip**: data generated from a known
  ``(n, τ)`` is recovered by :func:`fit_avrami` to ~machine precision (the
  "recover the constant" check); (b) Koistinen–Marburger hits its exact closed-form
  values; (c) the C-curve readings invert each other exactly.
* **Conservation / structure** — the C-curve genuinely has a single **nose**:
  ``τ(T)`` diverges at both ends (``T → T_eq``: no driving force; ``T → Mₛ``: no
  mobility) and is unimodal between, and the start/finish lines are parallel
  (scaled ``τ``).
* **Benchmark** — the C-curve nose lands where published 1080 TTT diagrams put it
  (~550 °C / ~1 s start), and **Andrews Mₛ** lands in the published ranges for
  named steels (1080 / 1045 / 4140). The exact-coefficient assertion is a *pin*,
  not the benchmark — the range checks are the non-circular leg.
"""
import math

import numpy as np
import pytest

from steel.kinetics import (
    avrami_fraction, avrami_time_for_fraction, fit_avrami,
    CCurve, andrews_Ms, koistinen_marburger,
    KM_ALPHA, ABS_ZERO,
)
from steel import fe_c

EXACT = dict(rel=0.0, abs=1e-12)


# --------------------------------------------------------------------------- #
# Analytical limit (a): the Avrami round-trip — recover (n, τ)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n_true, tau_true", [(1.0, 5.0), (2.5, 1.0), (4.0, 120.0), (3.0, 0.03)])
def test_avrami_round_trip_recovers_n_and_tau(n_true, tau_true):
    # Pick fractions directly across a well-conditioned window (away from the X→0/1
    # extremes where computing 1−X from X cancels catastrophically), derive the
    # matching times, then recover the constants. The relation is exactly linear in
    # log-log, so a clean window recovers (n, τ) to ~float precision.
    X = np.linspace(0.05, 0.95, 200)
    t = np.array([avrami_time_for_fraction(x, tau_true, n_true) for x in X])
    n_fit, tau_fit = fit_avrami(t, X)
    assert n_fit == pytest.approx(n_true, rel=1e-9)
    assert tau_fit == pytest.approx(tau_true, rel=1e-9)


def test_avrami_characteristic_time_is_632_percent():
    # X(τ) = 1 − e⁻¹ ≈ 0.632 for any n — the definition of the characteristic time.
    for n in (1.0, 2.5, 4.0):
        assert avrami_fraction(7.3, 7.3, n) == pytest.approx(1.0 - math.exp(-1.0), **EXACT)


def test_avrami_endpoints_and_monotonicity():
    assert avrami_fraction(0.0, 2.0, 2.5) == 0.0
    assert avrami_fraction(1e9, 2.0, 2.5) == pytest.approx(1.0, abs=1e-12)
    t = np.linspace(0.0, 20.0, 100)
    X = avrami_fraction(t, 2.0, 2.5)
    assert np.all(np.diff(X) >= 0.0)            # monotonically increasing


def test_avrami_time_inverts_fraction():
    # avrami_time_for_fraction and avrami_fraction are exact inverses.
    tau, n = 3.7, 2.2
    for X in (0.01, 0.1, 0.5, 0.9, 0.99):
        t = avrami_time_for_fraction(X, tau, n)
        assert avrami_fraction(t, tau, n) == pytest.approx(X, **EXACT)


@pytest.mark.parametrize("bad_X", [-0.1, 0.0, 1.0, 1.5])
def test_avrami_time_rejects_out_of_range_fraction(bad_X):
    with pytest.raises(ValueError):
        avrami_time_for_fraction(bad_X, 1.0, 2.0)


# --------------------------------------------------------------------------- #
# Analytical limit (b): Koistinen–Marburger exact values
# --------------------------------------------------------------------------- #
def test_km_zero_at_and_above_ms():
    assert koistinen_marburger(200.0, 200.0) == 0.0     # exactly at Mₛ
    assert koistinen_marburger(250.0, 200.0) == 0.0     # above Mₛ → clamped to 0


def test_km_closed_form_value():
    # 100 K below Mₛ with α = 0.011: f = 1 − exp(−1.1) ≈ 0.6671.
    Ms = 200.0
    assert koistinen_marburger(Ms - 100.0, Ms) == pytest.approx(1.0 - math.exp(-1.1), **EXACT)
    # full closed form at an arbitrary undercooling
    assert koistinen_marburger(20.0, 350.0, alpha=0.011) == pytest.approx(
        1.0 - math.exp(-0.011 * 330.0), **EXACT
    )


def test_km_increases_with_undercooling_and_bounded():
    Ms = 220.0
    Ts = [219.0, 180.0, 120.0, 25.0, -100.0]
    fs = [koistinen_marburger(T, Ms) for T in Ts]
    assert all(0.0 < f < 1.0 for f in fs)
    assert fs == sorted(fs)                              # more undercooling → more martensite


# --------------------------------------------------------------------------- #
# Analytical limit (c): the C-curve readings invert each other
# --------------------------------------------------------------------------- #
def test_ccurve_fraction_inverts_time_to_fraction():
    cc = CCurve(Ms=andrews_Ms(0.8))
    for T in (560.0, 500.0, 400.0, 300.0):
        for X in (0.01, 0.5, 0.99):
            t = cc.time_to_fraction(T, X)
            assert cc.fraction(T, t) == pytest.approx(X, **EXACT)


# --------------------------------------------------------------------------- #
# Structure: the nose — τ(T) diverges at both ends, unimodal between
# --------------------------------------------------------------------------- #
def test_tau_diverges_at_equilibrium_and_is_finite_inside():
    cc = CCurve(Ms=andrews_Ms(0.8))
    assert cc.tau(cc.T_eq) == math.inf                  # no driving force at A₁
    assert cc.tau(cc.T_eq + 50.0) == math.inf           # above A₁ too
    assert math.isfinite(cc.tau(550.0))                 # inside the window


def test_ccurve_has_single_nose_unimodal():
    cc = CCurve(Ms=andrews_Ms(0.8))
    T_nose, _ = cc.nose(X=0.01)
    # On the finite interior, τ strictly decreases from above the nose down to it,
    # then strictly increases from the nose down toward Mₛ — the defining C-shape.
    # (The divergence at the very edges is checked separately; here we stay where
    # τ is finite so the monotonicity is testable.)
    upper = np.linspace(680.0, T_nose, 40)              # descending temperature
    lower = np.linspace(T_nose, cc.Ms + 10.0, 40)
    tau_upper = [cc.tau(float(T)) for T in upper]
    tau_lower = [cc.tau(float(T)) for T in lower]
    assert all(math.isfinite(x) for x in tau_upper + tau_lower)
    assert np.all(np.diff(tau_upper) < 0.0)             # falling toward the nose
    assert np.all(np.diff(tau_lower) > 0.0)             # rising away from it
    assert cc.tau(T_nose) == pytest.approx(min(tau_upper + tau_lower), rel=1e-6)


def test_ttt_start_finish_ordered_and_parallel():
    cc = CCurve(Ms=andrews_Ms(0.8))
    # Start (1%) is always before finish (99%); the ratio to τ is T-independent
    # (the lines are the same C-curve scaled by (−ln(1−X))^{1/n}).
    ratios_start, ratios_finish = [], []
    for T in (600.0, 550.0, 450.0, 350.0):
        t_start = cc.time_to_fraction(T, 0.01)
        t_finish = cc.time_to_fraction(T, 0.99)
        assert t_start < t_finish
        ratios_start.append(t_start / cc.tau(T))
        ratios_finish.append(t_finish / cc.tau(T))
    assert np.allclose(ratios_start, ratios_start[0], rtol=1e-12)
    assert np.allclose(ratios_finish, ratios_finish[0], rtol=1e-12)


# --------------------------------------------------------------------------- #
# Benchmark: nose location vs published 1080 TTT; Andrews Mₛ vs published
# --------------------------------------------------------------------------- #
def test_benchmark_1080_nose_location():
    # Published AISI 1080 isothermal TTT: pearlite nose at ~550 °C, start at ~1 s.
    cc = CCurve(Ms=andrews_Ms(0.8))
    T_nose, t_nose = cc.nose(X=0.01)
    assert 520.0 <= T_nose <= 580.0                     # nose temperature
    assert 0.3 <= t_nose <= 3.0                         # nose start time (s)


def test_benchmark_andrews_named_steels_in_published_ranges():
    # The non-circular Andrews check: named compositions land in published Mₛ bands.
    ms_1080 = andrews_Ms(0.80)                          # plain eutectoid (C only)
    ms_1045 = andrews_Ms(0.45, Mn=0.75)                 # medium-carbon
    ms_4140 = andrews_Ms(0.40, Mn=0.90, Cr=1.0, Mo=0.20)
    assert 190.0 <= ms_1080 <= 225.0                    # 1080 Mₛ ≈ 200–220 °C
    assert 300.0 <= ms_1045 <= 345.0                    # 1045 Mₛ ≈ 320 °C
    assert 315.0 <= ms_4140 <= 345.0                    # 4140 Mₛ ≈ 330 °C


def test_andrews_coefficient_pin_and_trends():
    # A regression *pin* on the implemented coefficients (NOT the benchmark): the
    # exact Andrews linear value for plain 0.8 % C.
    assert andrews_Ms(0.80) == pytest.approx(539.0 - 423.0 * 0.80, **EXACT)
    # Carbon dominates and lowers Mₛ; every alloying addition lowers it further.
    assert andrews_Ms(0.20) > andrews_Ms(0.80)
    base = andrews_Ms(0.40)
    assert andrews_Ms(0.40, Mn=1.0) < base
    assert andrews_Ms(0.40, Ni=1.0) < base
    assert andrews_Ms(0.40, Cr=1.0) < base
    assert andrews_Ms(0.40, Mo=1.0) < base


# --------------------------------------------------------------------------- #
# Wiring: the driving force is fe_c's undercooling, and units are kelvin-correct
# --------------------------------------------------------------------------- #
def test_default_T_eq_is_fe_c_A1():
    # The C-curve's equilibrium ceiling defaults to fe_c's eutectoid A₁ — the
    # undercooling below it IS the driving force this module consumes (plan §3).
    assert CCurve().T_eq == fe_c.A1()


def test_input_guards():
    with pytest.raises(ValueError):
        avrami_fraction(1.0, tau=0.0, n=2.0)
    with pytest.raises(ValueError):
        avrami_fraction(1.0, tau=1.0, n=0.0)
    with pytest.raises(ValueError):
        fit_avrami(np.array([1.0]), np.array([0.5]))    # need ≥2 fittable points
