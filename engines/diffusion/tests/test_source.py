"""Source-term invariant: exact source-augmented conservation.

``source`` is part of the frozen API and the PDE, so it carries its own seal. A
spatially-uniform source ``S`` with no-flux boundaries and a uniform initial
field keeps the field uniform, so every cell rises by exactly ``S·t`` and the
total by ``S·L·t`` — both to machine precision (backward Euler is exact for a
spatially-uniform state, where the diffusion operator is identically zero).
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Neumann


def test_uniform_source_exact_rise():
    g = uniform_grid(1.5, 30)
    S, u_init, t_end = 0.4, 2.0, 3.0
    solver = Diffusion1D(g, 1.0, Neumann(0.0), Neumann(0.0), source=S)
    u = np.full(g.n, u_init)
    u = solver.solve(u, t_end, dt=0.3)
    assert np.allclose(u, u_init + S * t_end, rtol=0.0, atol=1e-12)
    assert np.isclose(solver.total(u), (u_init + S * t_end) * g.length, rtol=1e-12, atol=1e-12)


def test_callable_source_uniform_rise():
    # a time-callable source S(t) = const exercises the callable plumbing too.
    g = uniform_grid(1.0, 16)
    solver = Diffusion1D(g, 0.5, Neumann(0.0), Neumann(0.0), source=lambda t: 0.25)
    u = np.full(g.n, 1.0)
    u = solver.solve(u, t_end=2.0, dt=0.25)
    assert np.allclose(u, 1.0 + 0.25 * 2.0, rtol=0.0, atol=1e-12)
