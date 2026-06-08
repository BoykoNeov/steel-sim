"""Temporal-order invariant: backward Euler is 1st-order, Crank–Nicolson is 2nd.

The CONTRACT advertises Crank–Nicolson as "2nd-order in time"; nothing else in the
seal checks temporal accuracy (the erfc convergence test deliberately couples
dt∝Δx² and uses backward Euler, so it measures *spatial* order only). Here the
spatial error is held fixed (one grid) and removed by differencing against a
tiny-dt reference solution, so the measured slopes are purely temporal.

The test field is the no-flux eigenmode u(x,t)=exp(−Dπ²t/L²)·cos(πx/L); cos(πx/L)
has zero slope at both walls, so Neumann(0)/Neumann(0) holds it exactly.
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Neumann


def _temporal_slopes(method):
    L, N, D, t_end = 1.0, 100, 1.0, 0.1
    g = uniform_grid(L, N)
    ic = np.cos(np.pi * g.centers / L)
    solver = Diffusion1D(g, D, Neumann(0.0), Neumann(0.0), method=method)
    u_ref = solver.solve(ic.copy(), t_end, dt=t_end / 20000)  # ~exact in time
    dts = [t_end / 10, t_end / 20, t_end / 40, t_end / 80]
    errs = np.array([np.max(np.abs(solver.solve(ic.copy(), t_end, dt) - u_ref)) for dt in dts])
    return np.log(errs[:-1] / errs[1:]) / np.log(2.0)


def test_backward_euler_first_order_in_time():
    slopes = _temporal_slopes("backward_euler")
    assert np.all(slopes > 0.9), f"backward Euler not ~1st order: {slopes}"


def test_crank_nicolson_second_order_in_time():
    slopes = _temporal_slopes("crank_nicolson")
    assert np.all(slopes > 1.9), f"Crank–Nicolson not ~2nd order: {slopes}"
