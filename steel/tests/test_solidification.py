"""Unit tests for F4 Slice 2 — the latent-heat solidification field, its Stefan tooth, and the defect reads.

The honest map (mirrors the module docstring):
  * the **headline tooth** is the analytic one-phase Stefan benchmark — the numerical front *converges* to
    the closed form ``2λ√(αt)`` under grid refinement (a tuning-free, cited check);
  * **enthalpy conservation** is exact (machine precision) — the engine's invariant on the nonlinear path;
  * the latent ON/OFF toggle is a **directional** sanity check (right sign / order of magnitude);
  * Niyama and the last-to-freeze hot spot are **by construction** (named, not benchmarks).

Grids are kept small and in the Picard-robust regime (Δx ≲ 1.0 mm) so the whole file runs in the fast lane.
"""
from __future__ import annotations

import numpy as np
import pytest

from steel import solidification as sol
from steel.solidification import FreezingPath
from steel.sweep import STEELS

PATH = FreezingPath(T_sol=1438.0, T_liq=1498.0)        # ~4140, 60 °C freezing range


@pytest.fixture(scope="module")
def field():
    """One small chill-slab solve, shared across the by-construction tests (40 mm half-section)."""
    return sol.solidify_chill_slab(PATH, half_thickness=0.04, chill_T=100.0, n_cells=80, n_t=2000, t_end=200.0)


# --------------------------------------------------------------------------- #
# The constitutive enthalpy path (regularized) — round-trips and shape
# --------------------------------------------------------------------------- #
def test_enthalpy_temperature_round_trip():
    T = np.linspace(1000.0, 1600.0, 50)
    assert np.allclose(PATH.temperature(PATH.specific_enthalpy(T)), T, atol=0.5)


def test_enthalpy_is_monotonic_in_temperature():
    T = np.linspace(1000.0, 1600.0, 200)
    assert np.all(np.diff(PATH.specific_enthalpy(T)) > 0.0)


def test_solid_fraction_endpoints_and_midpoint():
    assert PATH.solid_fraction(PATH.T_liq + 10) == pytest.approx(0.0)
    assert PATH.solid_fraction(PATH.T_sol - 10) == pytest.approx(1.0)
    assert PATH.solid_fraction(0.5 * (PATH.T_sol + PATH.T_liq)) == pytest.approx(0.5, abs=1e-9)


def test_apparent_capacity_spikes_only_in_the_freezing_range():
    # cp outside (the regularization ramps continuously to cp at both ends), > cp inside (latent heat).
    assert PATH.apparent_capacity(PATH.T_liq + 50) == pytest.approx(PATH.cp)
    assert PATH.apparent_capacity(PATH.T_sol - 50) == pytest.approx(PATH.cp)
    assert PATH.apparent_capacity(0.5 * (PATH.T_sol + PATH.T_liq)) > 5.0 * PATH.cp
    # the diffusivity therefore DROPS in the mushy range (the front slows — the plateau)
    D_solid = PATH.diffusivity_of_h(PATH.specific_enthalpy(PATH.T_sol - 50))
    D_mush = PATH.diffusivity_of_h(PATH.specific_enthalpy(0.5 * (PATH.T_sol + PATH.T_liq)))
    assert D_mush < 0.3 * D_solid


def test_freezing_path_for_uses_casting_liquidus():
    from steel import casting
    s = STEELS["4140"]
    comp = {"C": s.C, "Mn": s.Mn, "Si": s.Si, "Ni": s.Ni, "Cr": s.Cr, "Mo": s.Mo}
    p = sol.freezing_path_for(s, freezing_range_C=55.0)
    assert p.T_liq == pytest.approx(casting.liquidus_temperature(comp))
    assert p.T_sol == pytest.approx(p.T_liq - 55.0)


# --------------------------------------------------------------------------- #
# The Stefan analytic machinery + the HEADLINE TOOTH (convergence under refinement)
# --------------------------------------------------------------------------- #
def test_stefan_lambda_solves_the_transcendental():
    St = 3.0
    lam = sol.stefan_lambda(St)
    from scipy.special import erf
    assert lam * np.exp(lam * lam) * erf(lam) == pytest.approx(St / np.sqrt(np.pi), rel=1e-6)


def test_stefan_number_formula_and_guard():
    St = sol.stefan_number(PATH, 100.0, T_freeze=1450.0)
    assert St == pytest.approx(PATH.cp * (1450.0 - 100.0) / PATH.L)
    with pytest.raises(ValueError):
        sol.stefan_lambda(-1.0)            # chill above the freezing point


def test_numerical_front_converges_to_analytic_stefan():
    """THE TOOTH: the numerical freezing front approaches the closed-form Stefan front as Δx halves."""
    coarse = sol.one_phase_stefan_validation(PATH, chill_T=25.0, domain=0.12, n_cells=120, n_t=2400,
                                             t_end=350.0, n_samples=4)
    fine = sol.one_phase_stefan_validation(PATH, chill_T=25.0, domain=0.12, n_cells=180, n_t=3600,
                                           t_end=350.0, n_samples=4)
    # within a few percent at a physical freezing range, and below the analytic (solidus offset / resolution)
    assert 0.90 < fine.ratio.mean() < 1.01
    # the discriminating assertion: refining the grid moves the front TOWARD the analytic solution
    assert abs(fine.ratio.mean() - 1.0) < abs(coarse.ratio.mean() - 1.0)


# --------------------------------------------------------------------------- #
# Enthalpy conservation (the engine invariant) + the latent ON/OFF directional check
# --------------------------------------------------------------------------- #
def test_enthalpy_conservation_is_machine_precision(field):
    resid = abs(field.enthalpy_drift - field.boundary_flux) / abs(field.boundary_flux)
    assert resid < 1e-9


def test_latent_heat_slows_freezing(field):
    """Directional sanity: turning latent heat off freezes the centre faster (right sign, right order)."""
    off_path = FreezingPath(T_sol=PATH.T_sol, T_liq=PATH.T_liq, L=0.0)
    off = sol.solidify_chill_slab(off_path, half_thickness=0.04, chill_T=100.0, n_cells=80, n_t=2000, t_end=200.0)

    def centre_freeze(f):
        _, t = sol.local_solidification_time(f)
        return t[np.isfinite(t)][-1]

    on_time, off_time = centre_freeze(field), centre_freeze(off)
    assert on_time > off_time                       # latent heat stalls the cool-down
    assert 2.0 < on_time / off_time < 12.0          # order of 1 + L/(c_p ΔT) (shape-dependent, not exact)


# --------------------------------------------------------------------------- #
# By-construction defect reads — the last-to-freeze hot spot and Niyama collapse
# --------------------------------------------------------------------------- #
def test_centre_is_last_to_freeze(field):
    x, t_sol = sol.local_solidification_time(field)
    finite = t_sol[np.isfinite(t_sol)]
    assert finite[-1] == finite.max()               # the insulated centre freezes last (the hot spot)
    # monotone increasing through the interior (skip the chill-pinned leading cells at t≈0)
    interior = finite[finite > 1.0]
    assert np.all(np.diff(interior) > 0.0)


def test_niyama_collapses_toward_the_porosity_prone_centre(field):
    x, ny = sol.niyama_field(field)
    valid = ny[np.isfinite(ny)]
    assert np.all(valid > 0.0)                      # a real positive criterion across the solidified section
    # the centre (last finite) is well below the interior peak — the porosity-prone core (by construction)
    assert valid[-1] < 0.5 * valid.max()


def test_field_temperature_increases_from_chill_to_centre(field):
    """The field is physically ordered (no h→T clamping): coldest at the chill, hottest at the centre."""
    final = field.T[-1]
    assert final[-1] > final[0]                     # centre hotter than the chilled surface
    assert np.all(np.diff(final) >= -1e-6)          # monotone increasing chill → centre


def test_porosity_prone_fraction_is_a_fraction(field):
    frac = sol.porosity_prone_fraction(field)
    assert 0.0 <= frac <= 1.0
