"""Nonlinear diffusivity ``D(u)``: the re-seal of the unfrozen v1.1 path (ADR 0004).

Phase-1a froze the solver with ``D`` as scalar / ``D(x)`` / ``D(t)`` — all *independent*
of the solution. Steel's carburizing work (the concentration-dependent Tibbetts ``D(C)``)
needs a diffusivity that depends on the **solution**, so the engine was unfrozen to add an
opt-in nonlinear ``D_of_u`` (CONTRACT.md invariant 6). The change is **additive**: the
linear path is byte-identical, so the original five seal files (``test_erfc`` /
``test_conservation`` / ``test_stability`` / ``test_time_order`` / ``test_variable_d``)
are unchanged and still pass — this file is the *added* seal for the nonlinear path.

The triad for ``D(u)``:

  1. **consistency** — a constant ``D(u)`` reproduces the scalar-``D`` run to machine
     precision (so the unfreeze cannot have perturbed the frozen linear behaviour);
  2. **the nonlinear analytical leg** — a varying ``D(u)`` matches the **Boltzmann
     self-similar** reference, solved *independently* with ``scipy.solve_bvp``;
  3. **conservation** — exact under no-flux *and* through the boundary flux identity
     (machine-precise because :meth:`flux` uses the cached accepted-assembly D-field, not
     a re-evaluation that would differ by the Picard residual);
  4. **monotonicity** — no new extrema at large ``dt`` (the discrete maximum principle);
  5. **Picard** — the converged step is independent of the tolerance, and a starved
     iteration cap **raises** rather than silently returning an unconverged state.
"""
import numpy as np
import pytest
from scipy.integrate import solve_bvp

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet, Neumann


def _boltzmann_reference(D_of_u, u_surface, u_far, x, t):
    """Self-similar reference ``u(x,t) = U(η = x/√t)`` for ``∂u/∂t = ∂ₓ(D(u) ∂ₓu)``.

    For a constant-surface semi-infinite problem the Boltzmann variable ``η = x/√t``
    collapses the PDE to the ODE  ``d/dη(D(U) dU/dη) + (η/2) dU/dη = 0``, ``U(0)=u_surface``,
    ``U(∞)=u_far``. Solved as a BVP — an *independent* numeric (not the engine) so the
    match in :func:`test_nonlinear_D_matches_boltzmann_similarity` is a real cross-check.
    Pure test scaffolding; deliberately **not** added to the engine's frozen surface.
    """
    D_hi = float(np.max(D_of_u(np.array([u_surface, u_far], dtype=float))))
    eta_max = 12.0 * np.sqrt(D_hi)
    eta = np.linspace(0.0, eta_max, 400)

    def odes(e, y):
        U, w = y                         # w = D(U)·dU/dη  (the flux variable)
        dU = w / D_of_u(U)
        return np.vstack((dU, -0.5 * e * dU))

    def bc(ya, yb):
        return np.array([ya[0] - u_surface, yb[0] - u_far])

    U0 = u_far + (u_surface - u_far) * (1.0 - eta / eta_max)
    w0 = D_of_u(U0) * np.gradient(U0, eta)
    sol = solve_bvp(odes, bc, eta, np.vstack((U0, w0)), tol=1e-8, max_nodes=20000)
    assert sol.success, sol.message
    return sol.sol(np.clip(np.asarray(x, dtype=float) / np.sqrt(t), 0.0, eta_max))[0]


def test_constant_D_of_u_reproduces_scalar_D():
    # The backward-compat seal: a constant nonlinear D(u)=c gives EXACTLY the scalar-D run
    # the original five seal files validate — the unfreeze did not move the linear path.
    g = uniform_grid(1.0, 80)
    ic = np.cos(np.pi * g.centers)
    u_lin = Diffusion1D(g, 0.6, Neumann(0.0), Neumann(0.0)).solve(ic.copy(), 0.2, 0.005)
    u_nl = Diffusion1D(g, None, Neumann(0.0), Neumann(0.0),
                       D_of_u=lambda u: np.full_like(u, 0.6)).solve(ic.copy(), 0.2, 0.005)
    assert np.max(np.abs(u_lin - u_nl)) < 1e-14


def test_nonlinear_D_matches_boltzmann_similarity():
    # The nonlinear analytical leg (the teeth). With D(u)=D0(1+βu) the profile is no longer
    # erfc, but the constant-surface semi-infinite problem stays Boltzmann self-similar, so
    # the finite-volume Picard solve must match the independently-solved similarity ODE.
    D0, beta = 0.3, 1.0
    D_of_u = lambda u: D0 * (1.0 + beta * u)
    us, u0 = 1.0, 0.0
    L, N, t_end = 2.0, 600, 0.12
    g = uniform_grid(L, N)
    solver = Diffusion1D(g, None, Dirichlet(us), Neumann(0.0), D_of_u=D_of_u)
    u = solver.solve(np.full(N, u0), t_end, t_end / 1200)
    ref = _boltzmann_reference(D_of_u, us, u0, g.centers, t_end)
    active = (ref - u0) > 1e-3 * (us - u0)
    active[0] = False                                  # drop the Dirichlet half-cell
    rel = np.abs(u[active] - ref[active]) / (us - u0)
    assert np.max(rel) < 1.5e-2                         # two independent solvers agree


def test_nonlinear_conservation_exact_under_no_flux():
    # Conservation is structural AND exact on the nonlinear path because flux() (and the
    # operator's interior telescoping) use the cached accepted-assembly D-field — not a
    # re-evaluation that would differ by the Picard residual. No-flux both ends → Σ uᵢΔxᵢ
    # constant to machine precision, for a genuinely nonlinear D(u)=0.25(1+u²).
    g = uniform_grid(1.0, 100)
    s = Diffusion1D(g, None, Neumann(0.0), Neumann(0.0), D_of_u=lambda u: 0.25 * (1.0 + u**2))
    u = 0.5 + 0.4 * np.cos(np.pi * g.centers)
    t0 = s.total(u)
    for _ in range(40):
        u = s.step(u, 0.05)
    assert abs(s.total(u) - t0) < 1e-12


def test_nonlinear_flux_identity_exact_with_dirichlet():
    # The exact discrete identity  total(stepped) − total = dt·(flux_L − flux_R),
    # re-confirmed for a Dirichlet inflow with D(u): the cached-field flux makes the
    # accumulated surface flux equal the integral rise to machine precision — the carburizing
    # conservation leg, now valid for the concentration-dependent diffusivity too.
    g = uniform_grid(1.0, 120)
    s = Diffusion1D(g, None, Dirichlet(1.0), Neumann(0.0), D_of_u=lambda u: 0.2 * (1.0 + u))
    u = np.zeros(g.n); acc = 0.0; t = 0.0; dt = 0.01
    t_start = s.total(u)
    for _ in range(80):
        u = s.step(u, dt, t0=t); t += dt
        acc += dt * s.flux(u, "left", t=t)
    assert abs((s.total(u) - t_start) - acc) < 1e-12


def test_nonlinear_is_monotone_no_new_extrema():
    # Discrete maximum principle on the nonlinear path: with D(u) > 0 a no-flux relaxation
    # of a step introduces no new extrema even at an enormous dt (no oscillation) — each
    # Picard sub-solve is the monotone backward-Euler M-matrix, so the converged step is too.
    g = uniform_grid(1.0, 64)
    u0 = np.where(g.centers < 0.5, 1.0, 0.0)            # a step — the stiff case
    s = Diffusion1D(g, None, Neumann(0.0), Neumann(0.0), D_of_u=lambda u: 0.1 * (1.0 + u))
    u = s.step(u0, 100.0)                                # enormous dt
    assert u.min() >= u0.min() - 1e-12
    assert u.max() <= u0.max() + 1e-12


def test_picard_tol_independence_and_raises():
    # The converged step is independent of how hard we converge (tight vs loose tol agree),
    # and a starved iteration cap RAISES rather than silently returning an unconverged state.
    g = uniform_grid(1.0, 80)
    D_of_u = lambda u: 0.2 * (1.0 + u)
    u0 = 0.5 + 0.4 * np.cos(np.pi * g.centers)
    a = Diffusion1D(g, None, Neumann(0.0), Neumann(0.0), D_of_u=D_of_u, picard_tol=1e-8).step(u0, 0.1)
    b = Diffusion1D(g, None, Neumann(0.0), Neumann(0.0), D_of_u=D_of_u, picard_tol=1e-13).step(u0, 0.1)
    assert np.max(np.abs(a - b)) < 1e-7
    with pytest.raises(RuntimeError):
        Diffusion1D(g, None, Neumann(0.0), Neumann(0.0),
                    D_of_u=lambda u: 1.0 * (1.0 + 5.0 * u), picard_max_iters=1).step(u0, 50.0)
