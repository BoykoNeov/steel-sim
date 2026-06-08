"""Analytical-limit invariant #1: the erfc semi-infinite-solid profile.

The headline check of the spine. A semi-infinite solid initially at ``u0`` with a
surface held at ``us`` from t=0 develops

    u(x, t) = u0 + (us − u0) · erfc( x / (2 √(D t)) ).

This is the exact carbon-into-austenite profile the whole program inherits. The
second test confirms the discretization is ~2nd-order in space; per the design
note we couple ``dt ∝ Δx²`` (backward Euler) so the temporal error tracks the
spatial order and the measured slope reflects the spatial scheme, not a fixed
time-stepping floor.
"""
import numpy as np
from scipy.special import erfc

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet


def _erfc_profile(x, t, D, u0, us):
    return u0 + (us - u0) * erfc(x / (2.0 * np.sqrt(D * t)))


def test_erfc_semi_infinite_accuracy():
    D, u0, us, L, N = 1.0, 0.0, 1.0, 1.0, 400
    t_end = 0.01  # penetration depth ~4√(Dt) = 0.4 < L, so the far end stays ≈ u0
    g = uniform_grid(L, N)
    solver = Diffusion1D(g, D, Dirichlet(us), Dirichlet(u0))
    u = np.full(N, u0)
    u = solver.solve(u, t_end, dt=t_end / 4000)

    exact = _erfc_profile(g.centers, t_end, D, u0, us)
    mask = g.centers < 0.6  # well inside the domain, clear of the far truncation
    max_err = np.max(np.abs(u[mask] - exact[mask]))
    assert max_err < 5e-3  # < 0.5% of (us − u0)


def test_erfc_second_order_spatial_convergence():
    D, u0, us, L, t_end = 1.0, 0.0, 1.0, 1.0, 0.01
    Ns = [25, 50, 100, 200]
    errs = []
    for N in Ns:
        g = uniform_grid(L, N)
        dx = L / N
        dt = 0.2 * dx * dx / D  # dt ∝ Δx²  → BE temporal error O(dt) tracks O(Δx²)
        solver = Diffusion1D(g, D, Dirichlet(us), Dirichlet(u0))
        u = solver.solve(np.full(N, u0), t_end, dt)
        exact = _erfc_profile(g.centers, t_end, D, u0, us)
        mask = g.centers < 0.6
        l2 = np.sqrt(np.sum((u[mask] - exact[mask]) ** 2 * g.widths[mask]))
        errs.append(l2)

    errs = np.array(errs)
    rates = np.log(errs[:-1] / errs[1:]) / np.log(2.0)
    assert np.all(rates > 1.8), f"convergence rates {rates} not ~2nd order"
