"""Stability invariant #3: unconditional stability, no oscillatory blow-up.

A learner may pick any dt without the solution exploding. Backward Euler is
unconditionally stable *and monotone* — the discrete maximum principle forbids
new extrema, so even at absurd dt the field stays bounded by its initial/boundary
data and relaxes smoothly to steady state. Crank–Nicolson is unconditionally
stable but *not* monotone; we assert only boundedness (no blow-up) for it, which
documents the per-method guarantee the CONTRACT states.
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet


def _hot_gaussian(centers):
    return np.exp(-((centers - 0.5) / 0.05) ** 2)


def test_backward_euler_max_principle_at_huge_dt():
    g = uniform_grid(1.0, 80)
    D = 1.0
    solver = Diffusion1D(g, D, Dirichlet(0.0), Dirichlet(0.0))
    u = _hot_gaussian(g.centers)
    hi = u.max()
    cfl = (g.length / g.n) ** 2 / (2.0 * D)
    dt = 1e6 * cfl  # a million times the explicit stability limit

    for _ in range(50):
        u = solver.step(u, dt)
        assert np.isfinite(u).all()
        # no new extrema: bounded by IC max and the (zero) boundary
        assert u.max() <= hi + 1e-12
        assert u.min() >= -1e-12
    assert u.max() < 1e-6  # fully relaxed to the steady state (zero)


def test_crank_nicolson_bounded_at_huge_dt():
    g = uniform_grid(1.0, 80)
    solver = Diffusion1D(g, 1.0, Dirichlet(0.0), Dirichlet(0.0), method="crank_nicolson")
    u = _hot_gaussian(g.centers)
    dt = 1e4 * ((g.length / g.n) ** 2 / 2.0)
    for _ in range(50):
        u = solver.step(u, dt)
        assert np.isfinite(u).all()  # unconditionally stable: never blows up...
    assert np.abs(u).max() < 2.0  # ...though it may briefly oscillate (not monotone)
