"""Conservation invariant #2: exact mass conservation under no-flux boundaries.

The finite-volume guarantee. With Neumann(0) at both ends, ``Σ uᵢ Δxᵢ`` is
constant for *any* dt and *any* grid (uniform or not), because interior face
fluxes telescope. In exact arithmetic the conservation is exact; in floating
point the only residual is accumulated ``solve_banded`` backward-error (largest
at absurd dt, where the implicit matrix is ill-conditioned for the conserved
mode) — measured here at the ~1e-11 level over a long huge-dt run, so a 1e-9
relative bound is a strong "machine-precision conservation" seal with margin.
Also checks the consistent corollary that a prescribed Neumann inflow changes the
total at exactly the prescribed rate.
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, grid_from_edges, Neumann


def test_conservation_no_flux_uniform_grid():
    g = uniform_grid(2.0, 50)
    solver = Diffusion1D(g, 0.7, Neumann(0.0), Neumann(0.0))
    rng = np.random.default_rng(0)
    u = 1.0 + rng.random(g.n)  # lumpy positive initial condition
    total0 = solver.total(u)
    for _ in range(100):
        u = solver.step(u, dt=10.0)  # huge dt — conservation must not care
    assert np.isclose(solver.total(u), total0, rtol=1e-9, atol=1e-12)
    # and it must actually diffuse toward the uniform mean (not conserve by idling)
    assert np.allclose(u, total0 / g.length, atol=1e-6)


def test_conservation_no_flux_nonuniform_grid():
    g = grid_from_edges([0.0, 0.1, 0.3, 0.6, 1.0, 1.7, 2.0])
    solver = Diffusion1D(g, 1.2, Neumann(0.0), Neumann(0.0))
    u = np.array([5.0, 1.0, 3.0, 0.0, 2.0, 4.0])
    total0 = solver.total(u)
    for _ in range(200):
        u = solver.step(u, dt=5.0)
    assert np.isclose(solver.total(u), total0, rtol=1e-9, atol=1e-12)
    assert np.allclose(u, total0 / g.length, atol=1e-6)


def test_conservation_mass_mode_arrhenius_scalar():
    # mass mode: the consumer supplies D(T) as a scalar at the hold temperature.
    R, D0, Q, T = 8.314, 2.3e-5, 148e3, 1123.0  # carbon in austenite, ~850 °C
    D = D0 * np.exp(-Q / (R * T))
    g = uniform_grid(1e-3, 40)  # 1 mm, SI metres
    solver = Diffusion1D(g, D, Neumann(0.0), Neumann(0.0))
    C = np.where(g.centers < 5e-4, 1.0, 0.2)  # a step in %C
    total0 = solver.total(C)
    for _ in range(500):
        C = solver.step(C, dt=1.0)
    assert np.isclose(solver.total(C), total0, rtol=1e-9, atol=1e-14)


def test_neumann_influx_changes_total_at_prescribed_rate():
    # d/dt total = J_left − J_right; a steady left inflow J=0.5 raises the total
    # by exactly 0.5·t_end (backward Euler honours the flux balance exactly).
    g = uniform_grid(1.0, 20)
    solver = Diffusion1D(g, 1.0, Neumann(0.5), Neumann(0.0))
    u = np.zeros(g.n)
    total0 = solver.total(u)
    t_end = 2.0
    u = solver.solve(u, t_end, dt=0.1)
    assert np.isclose(solver.total(u), total0 + 0.5 * t_end, rtol=1e-10, atol=1e-12)
