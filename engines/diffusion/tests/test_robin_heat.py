"""Heat-mode boundary checks: Robin (convective quench) + flux bookkeeping.

Not one of the three named seal invariants, but it covers the shipped heat-mode
boundary and pins the :meth:`flux` sign convention. Scope guard: this stays a
unit check of the BC math — the lumped-capacitance / Jominy validation belongs to
the Steel Phase-2 triad, not here.
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet, Robin


def test_robin_cools_both_ends_to_u_ext():
    g = uniform_grid(1.0, 40)
    # one h > 0 must cool at BOTH ends (outward-normal convention)
    solver = Diffusion1D(g, 1.0, Robin(2.0, 0.0), Robin(2.0, 0.0))
    u = np.full(g.n, 100.0)
    total_hot = solver.total(u)
    u1 = solver.step(u, dt=0.01)
    assert solver.total(u1) < total_hot  # heat leaves
    for _ in range(3000):
        u = solver.step(u, dt=0.05)  # unconditionally stable → large dt equilibrates fast
    assert np.allclose(u, 0.0, atol=1e-3)  # equilibrates to u_ext everywhere


def test_robin_asymmetric_u_ext_drives_toward_external():
    g = uniform_grid(1.0, 30)
    solver = Diffusion1D(g, 0.5, Robin(3.0, 20.0), Robin(3.0, 20.0))
    u = np.full(g.n, 80.0)
    for _ in range(5000):
        u = solver.step(u, dt=0.05)
    assert np.allclose(u, 20.0, atol=1e-2)


def test_flux_bookkeeping_exact_backward_euler():
    # Exact discrete identity for backward Euler:
    #   total(u1) − total(u0) == dt · (J_left − J_right)   at t1.
    # Mixed Robin/Dirichlet ends and a lumpy state exercise flux() signs fully.
    g = uniform_grid(1.0, 35)
    D = 0.8
    solver = Diffusion1D(g, D, Robin(1.5, 10.0), Dirichlet(50.0))
    rng = np.random.default_rng(1)
    u0 = 20.0 + 5.0 * rng.random(g.n)
    dt = 0.05
    u1 = solver.step(u0, dt, t0=0.0)
    j_left = solver.flux(u1, "left", t=dt)
    j_right = solver.flux(u1, "right", t=dt)
    lhs = solver.total(u1) - solver.total(u0)
    rhs = dt * (j_left - j_right)
    assert np.isclose(lhs, rhs, rtol=1e-10, atol=1e-12)
