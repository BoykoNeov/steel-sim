"""Phase-1c validation triad for the path-integrator (Steel plan §3).

* **Analytical limit** — (a) the 0-D **Newton cooler** reproduces its exact
  exponential (``T(τ_th) = T_env + ΔT/e``); (b) the **additivity reduction**: held
  isothermally at ``T*``, the Scheil sum ``∫dt/τ`` reaches 1 at exactly the
  isothermal start time ``τ_X(T*)`` — the bridge from TTT to CCT, checked against
  the isothermal curve it must reduce to.
* **Conservation** — the product fractions
  ``pearlite + bainite + martensite + retained_austenite`` sum to 1 to machine
  precision for *every* cooling rate, because Koistinen–Marburger is applied to the
  *retained* austenite ``(1 − X_diff)``, not the total.
* **Benchmark / behaviour** — the dramatic axis the whole simulator exists to show:
  **faster cooling → less pearlite, more martensite** (monotone), with a slow path
  giving ~full pearlite and a fast quench giving martensite + retained austenite.
"""
import math

import numpy as np
import pytest

from projects.steel.kinetics import CCurve, andrews_Ms, koistinen_marburger
from projects.steel import pathint as pi


def eutectoid_ccurve() -> CCurve:
    """The calibrated plain-carbon-eutectoid (1080) C-curve used across the tests."""
    return CCurve(Ms=andrews_Ms(0.8))


# --------------------------------------------------------------------------- #
# Analytical limit (a): the 0-D Newton cooler is the exact exponential
# --------------------------------------------------------------------------- #
def test_newton_cooling_exact_exponential():
    T0, T_env, tau_th = 850.0, 25.0, 4.0
    assert pi.newton_cooling(0.0, T0, T_env, tau_th) == pytest.approx(T0, rel=0.0, abs=1e-12)
    # one time constant: ΔT decays by 1/e
    assert pi.newton_cooling(tau_th, T0, T_env, tau_th) == pytest.approx(
        T_env + (T0 - T_env) / math.e, rel=0.0, abs=1e-12
    )
    # long time: → environment
    assert pi.newton_cooling(60.0 * tau_th, T0, T_env, tau_th) == pytest.approx(T_env, abs=1e-9)


def test_newton_cooling_monotone_decreasing():
    t = pi.log_time_grid(100.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 5.0)
    assert np.all(np.diff(T) <= 0.0)


def test_newton_cooling_rejects_bad_time_constant():
    with pytest.raises(ValueError):
        pi.newton_cooling(1.0, 850.0, 25.0, 0.0)


# --------------------------------------------------------------------------- #
# Analytical limit (b): additivity reduces to the isothermal start time
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("T_star", [600.0, 550.0, 500.0, 400.0, 300.0])
@pytest.mark.parametrize("X", [0.01, 0.5])
def test_additivity_reduces_to_isothermal_tau(T_star, X):
    # THE consistency leg: under an isothermal hold the Scheil sum ∫dt/τ_X is just
    # t/τ_X(T*), so it reaches 1 at exactly the isothermal time-to-X. This is what
    # makes the CCT construction reduce to the TTT curve it is built from.
    cc = eutectoid_ccurve()
    tau_X = cc.time_to_fraction(T_star, X)
    t = pi.log_time_grid(5.0 * tau_X, t_start=1e-4 * tau_X)
    T = np.full_like(t, T_star)
    t_start = pi.additivity_start_time(t, T, cc, X=X)
    assert t_start == pytest.approx(tau_X, rel=1e-6)


def test_additivity_start_infinite_when_nose_missed():
    # A fast quench whose path never lets the Scheil sum reach 1 → no diffusional
    # start (the austenite reaches Mₛ untransformed).
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(20.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 0.4)           # water-like
    assert pi.additivity_start_time(t, T, cc, X=0.01) == math.inf


def test_additivity_start_finite_for_slow_cool():
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(80000.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 6000.0)        # furnace-like
    start = pi.additivity_start_time(t, T, cc, X=0.01)
    assert math.isfinite(start) and start > 0.0


# --------------------------------------------------------------------------- #
# Conservation: product fractions sum to 1 for every cooling rate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tau_th", [6000.0, 300.0, 60.0, 30.0, 10.0, 2.0, 0.4])
def test_fractions_sum_to_one(tau_th):
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(max(60.0, 40.0 * tau_th))
    T = pi.newton_cooling(t, 850.0, 25.0, tau_th)
    r = pi.transform_along_path(t, T, cc)
    assert sum(r.fractions().values()) == pytest.approx(1.0, rel=0.0, abs=1e-12)
    assert all(v >= -1e-15 for v in r.fractions().values())


def test_martensite_is_km_on_retained_austenite():
    # The bookkeeping that makes the sum exact: martensite and retained austenite
    # partition the (1 − X_diff) that survived the diffusional path, per KM at T_min.
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(40.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 8.0)
    r = pi.transform_along_path(t, T, cc)
    retained_total = 1.0 - r.X_diffusional
    f_km = koistinen_marburger(r.T_min, cc.Ms)
    assert r.martensite == pytest.approx(retained_total * f_km, **dict(rel=0.0, abs=1e-12))
    assert r.retained_austenite == pytest.approx(retained_total * (1.0 - f_km), abs=1e-12)
    assert r.martensite + r.retained_austenite == pytest.approx(retained_total, abs=1e-12)


# --------------------------------------------------------------------------- #
# Behaviour: the dramatic axis — faster cooling → less pearlite, more martensite
# --------------------------------------------------------------------------- #
def test_slow_cool_is_fully_pearlitic():
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(80000.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 6000.0)        # furnace
    r = pi.transform_along_path(t, T, cc)
    assert r.pearlite > 0.99
    assert r.martensite == pytest.approx(0.0, abs=1e-9)
    assert r.dominant() == "pearlite"
    # The diffusional product formed somewhere on the C-curve, between Mₛ and A₁.
    assert cc.Ms < r.formation_T < cc.T_eq


def test_fast_quench_is_martensitic():
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(20.0)
    T = pi.newton_cooling(t, 850.0, 25.0, 0.4)           # water
    r = pi.transform_along_path(t, T, cc)
    assert r.martensite > 0.8
    assert r.pearlite < 0.01
    assert r.dominant() == "martensite"


def test_monotone_more_martensite_with_faster_cooling():
    # Sweep from slow to fast; martensite must rise monotonically and pearlite fall.
    cc = eutectoid_ccurve()
    taus = [6000.0, 300.0, 60.0, 30.0, 15.0, 5.0, 1.0, 0.4]
    martensite, pearlite = [], []
    for tau_th in taus:
        t = pi.log_time_grid(max(60.0, 40.0 * tau_th))
        T = pi.newton_cooling(t, 850.0, 25.0, tau_th)
        r = pi.transform_along_path(t, T, cc)
        martensite.append(r.martensite)
        pearlite.append(r.pearlite)
    assert martensite == sorted(martensite)             # faster → more martensite
    assert pearlite == sorted(pearlite, reverse=True)   # faster → less pearlite


def test_path_above_ms_leaves_austenite_untransformed():
    # A path that never reaches Mₛ and outruns the nose → all retained austenite
    # (no diffusional product, no martensite). Fractions still sum to 1.
    cc = eutectoid_ccurve()
    t = pi.log_time_grid(5.0)
    T = pi.newton_cooling(t, 850.0, 300.0, 0.2)          # quench into a 300 °C bath (> Mₛ)
    r = pi.transform_along_path(t, T, cc)
    assert r.T_min > cc.Ms
    assert r.martensite == 0.0
    assert r.retained_austenite == pytest.approx(1.0 - r.X_diffusional, abs=1e-12)


def test_transform_rejects_mismatched_arrays():
    cc = eutectoid_ccurve()
    with pytest.raises(ValueError):
        pi.transform_along_path(np.array([0.0, 1.0]), np.array([850.0]), cc)
