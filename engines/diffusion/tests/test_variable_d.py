"""Variable-diffusivity invariants: the callable ``D(t)`` and array ``D(x)`` paths.

The frozen contract permits ``D`` as a scalar, a cell-centered array ``D(x)``, or
a callable ``D(t)``. The three named seal tests all use a *scalar* ``D``, so these
two surfaces — and the harmonic-mean face diffusivity that exists solely for
unequal ``D`` — would otherwise be frozen untested. ``D(t)`` is not hypothetical:
it is exactly steel's mass mode when carbon diffuses *during* cooling (Phase 1c).
"""
import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet, Neumann


def test_callable_D_constant_equals_scalar():
    # A constant callable D(t)=c must reproduce the scalar-D run exactly.
    g = uniform_grid(1.0, 64)
    ic = np.cos(np.pi * g.centers)
    u_call = Diffusion1D(g, lambda t: 0.7, Neumann(0.0), Neumann(0.0)).solve(ic.copy(), 0.2, 0.01)
    u_scal = Diffusion1D(g, 0.7, Neumann(0.0), Neumann(0.0)).solve(ic.copy(), 0.2, 0.01)
    assert np.allclose(u_call, u_scal, rtol=0.0, atol=1e-12)


def test_callable_D_time_dependent_matches_tau_substitution():
    # For spatially-uniform D(t), the change of variable τ(t)=∫₀ᵗD(s)ds maps the
    # equation to the constant-D=1 equation. The cos eigenmode under no-flux then
    # decays as exp(−π²τ/L²)·cos(πx/L). Validate the callable D(t) run against
    # both the constant-D run to τ and the closed-form analytic field.
    L, N, t_end = 1.0, 200, 0.5
    g = uniform_grid(L, N)
    x = g.centers
    ic = np.cos(np.pi * x / L)
    g_of_t = lambda t: 0.5 + t                      # ∫₀ᵗ = 0.5t + t²/2
    tau = 0.5 * t_end + 0.5 * t_end ** 2

    u_var = Diffusion1D(g, g_of_t, Neumann(0.0), Neumann(0.0)).solve(ic.copy(), t_end, t_end / 5000)
    u_const = Diffusion1D(g, 1.0, Neumann(0.0), Neumann(0.0)).solve(ic.copy(), tau, tau / 5000)
    analytic = np.exp(-np.pi ** 2 * tau / L ** 2) * np.cos(np.pi * x / L)

    assert np.max(np.abs(u_var - u_const)) < 1e-4   # shared spatial error cancels
    assert np.max(np.abs(u_var - analytic)) < 1e-3  # vs closed form (O(Δx²)+O(dt))


def test_array_D_two_layer_steady_state_uses_harmonic_mean():
    # Two-layer medium, Dirichlet both ends. At steady state the flux is constant
    # through both layers (series resistances R_i = (L/2)/D_i), giving an exact
    # piecewise-linear profile with interface value u* = (D₁u_L + D₂u_R)/(D₁+D₂).
    # The cell-centered scheme reproduces this *exactly* only because the interface
    # face diffusivity is the harmonic mean (exact flux continuity); an arithmetic
    # mean would mis-predict u* by ~0.1 here.
    N = 200
    g = uniform_grid(1.0, N)
    x = g.centers
    D1, D2, uL, uR = 10.0, 1.0, 1.0, 0.0
    Dx = np.where(x < 0.5, D1, D2)  # interface coincides with a cell face (even N)
    solver = Diffusion1D(g, Dx, Dirichlet(uL), Dirichlet(uR))
    u = solver.solve(np.full(N, 0.5), t_end=5.0, dt=0.02)  # long enough → steady

    u_star = (D1 * uL + D2 * uR) / (D1 + D2)
    analytic = np.where(
        x < 0.5,
        uL + (u_star - uL) * (x / 0.5),
        u_star + (uR - u_star) * ((x - 0.5) / 0.5),
    )
    assert np.max(np.abs(u - analytic)) < 1e-9  # exact series-resistance profile

    # steady state ⇒ flux continuity, and it equals (u_L−u_R)/(R₁+R₂).
    j_left = solver.flux(u, "left")
    j_right = solver.flux(u, "right")
    j_series = (uL - uR) / (0.5 / D1 + 0.5 / D2)
    assert np.isclose(j_left, j_right, rtol=1e-9, atol=1e-9)
    assert np.isclose(j_left, j_series, rtol=1e-9, atol=1e-9)
