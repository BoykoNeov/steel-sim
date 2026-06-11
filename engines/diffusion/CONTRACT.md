# `engines.diffusion` — 1-D conservative parabolic solver — CONTRACT

> **Status: SEALED — v1.1, re-sealed 2026-06-11** (Steel Phase 1a froze v1.0 on
> 2026-06-08; v1.1 **unfroze and re-sealed** the surface to add native nonlinear
> `D(u)` — see ADR 0004). Held behind its passing validation suite
> (`engines/diffusion/tests/`, run via `./run_tests.ps1`). This one page is the unit
> of context downstream projects load — Microchip and Planet depend on *this*, never
> on `steel/`. The v1.0 **linear surface is byte-identical** under v1.1 (the original
> five seal files are unchanged and still pass); only the *additive*, opt-in `D_of_u`
> path is new, with its own seal (`test_nonlinear_d.py`). Changing the sealed surface
> below means a new ADR + re-running the seal (ARCHITECTURE.md §5–6).

## What it solves

The conservative 1-D parabolic PDE

```
∂u/∂t = ∂/∂x( D(x, t, u) ∂u/∂x ) + S(x,t)        on   x ∈ [0, L]
```

`u` is a generic conserved intensive scalar. `D` may be constant, `D(x)`, `D(t)`, or
— the v1.1 addition — **nonlinear `D(u)`** (a diffusivity that depends on the solution,
solved by an in-step Picard iteration; see the API + invariant 6 below). The engine is
**material-agnostic**; two usage patterns ship with Steel (the physics constants live in
the *consumer*, not here — see "Validation boundary"):

| Mode | `u` | `D` | Conserved quantity | Quench BC |
|---|---|---|---|---|
| **mass** | `%C` | `D(T) = D₀·exp(−Q/RT)` (carbon in austenite) | `∫C dx` | — |
| **heat** | `T` | `α = k/(ρc_p)` | enthalpy `∫ρc_p T dx` | Robin `h` |

The two differ *only* by relabelling `(u, D, BC params)` — that symmetry is why
one engine serves both, and why Planet's EBM heat transport is the same code.

## Discretization (fixed)

- **Cell-centered finite volume.** The flux leaving a cell across a face equals
  the flux entering its neighbour across that face, so interior fluxes telescope
  and `Σ uᵢΔxᵢ` changes *only* through boundary fluxes → conservation is
  structural and exact. Holds on **non-uniform** grids too.
- **θ-method implicit time stepping**, one tridiagonal solve per step
  (`scipy.linalg.solve_banded`): `backward_euler` (θ=1, default),
  `crank_nicolson` (θ=½, optional).
- Interior **face diffusivity = harmonic mean** of the two cell values (exact
  flux continuity across a D-discontinuity; reduces to D for constant D).

## API

```python
from engines.diffusion import (
    Diffusion1D, Grid, uniform_grid, grid_from_edges,
    Dirichlet, Neumann, Robin,
)

grid   = uniform_grid(length, n)          # or grid_from_edges([...])  (non-uniform)
solver = Diffusion1D(grid, D, bc_left, bc_right, source=None,
                     method="backward_euler")   # or "crank_nicolson"

# nonlinear D(u) (v1.1): pass D=None + a callable of the state (backward Euler only)
solver = Diffusion1D(grid, None, bc_left, bc_right, method="backward_euler",
                     D_of_u=lambda u: D0*(1 + beta*u),   # D as a function of the solution
                     picard_tol=1e-10, picard_max_iters=50)

state = solver.step(state, dt, t0=0.0)            # one step; returns new array
state = solver.solve(state, t_end, dt, t0=0.0)    # march to t0+t_end
q     = solver.total(state)                       # ∫u dx = Σ uᵢΔxᵢ
J     = solver.flux(state, end, t=0.0)            # end ∈ {"left","right"}
```

- **`D`**: scalar, length-`n` cell-centered array `D(x)`, or callable `D(t)`
  returning either. (`D(T)` is expressed as a callable closing over a temperature
  schedule: `lambda t: D0*np.exp(-Q/(R*T(t)))`.) Pass `None` when using `D_of_u`.
- **`D_of_u`** (v1.1, opt-in): a callable `D_of_u(u_cells) -> D array` giving a
  **nonlinear, solution-dependent** diffusivity. The implicit step is then nonlinear,
  solved by **Picard iteration** (`method="backward_euler"` required); `picard_tol` /
  `picard_max_iters` control convergence and `step` **raises** if it does not converge.
  Mutually exclusive with `D` (provide exactly one). The accepted assembly's D-field is
  **cached** so `flux` — and hence the conservation identity — stays *exact* on the
  nonlinear path; the one documented wart is that `flux` then reflects the most recent
  `step`. Steel's carburizing `D(C)` (Tibbetts) is the first consumer (ADR 0004).
- **`source`**: scalar, length-`n` array, or callable `S(t)`; units of `u`/time.
- **Boundary conditions** (each end, independently):
  - `Dirichlet(value)` — `u = value` at the face (`value` scalar or `value(t)`).
  - `Neumann(flux=0.0)` — physical flux `J = −D ∂u/∂x = flux` in **+x**;
    `flux=0` is insulated / symmetry / no-flux (the conservation BC).
  - `Robin(h, u_ext)` — convective, applied with the **outward normal**:
    `−D ∂u/∂n = h(u − u_ext)`, so a single `h>0` cools toward `u_ext` at **both**
    ends (the expected quench). Series-resistance coefficient
    `U_eff = 1/(Δx/2D + 1/h)`.

### Sign convention

Flux is `J = −D ∂u/∂x` (Fick), positive in **+x**. So at `"left"` `J>0` is inflow,
at `"right"` `J>0` is outflow. The exact backward-Euler identity
`total(stepped) − total(state) = dt·(flux(left) − flux(right))` holds to machine
precision (test `test_flux_bookkeeping_exact_backward_euler`).

### The frozen data boundary (ADR 0001)

`state` is a **plain 1-D `ndarray`** of cell-centered `u`. That array — and only
it — crosses the per-step boundary: `step`/`solve` consume and return it,
`total`/`flux` consume it. No live objects cross. `Grid`, `D` (or `D_of_u`), and BCs
are **construction-time configuration** that reduces to numbers during matrix assembly;
the nonlinear `D_of_u` is evaluated *inside* assembly and never enters the `state`
representation, so the data boundary is **unchanged** by v1.1. A compiled reimplementation
(PyO3/Cython/…) parameterizes them natively (e.g. `D₀,Q`; a BC enum + params; the `D(u)`
coefficients) and exposes the same `state` array. The viz layer (ADR 0002) consumes the
same `state` — never a live solver object.

## Frozen invariants (what the test suite guarantees — = the contract)

1. **erfc semi-infinite profile** within tolerance, and **~2nd-order spatial
   convergence** (`test_erfc.py`; measured rates ≈ 2.00). The headline analytical
   limit — the carbon-into-austenite profile the whole program inherits.
2. **Exact conservation under no-flux** (`test_conservation.py`): `Σ uᵢΔxᵢ`
   constant, *any* dt, uniform or non-uniform grid. Exact in exact arithmetic; in
   floating point the only residual is accumulated linear-solver backward-error
   (~1e-11 over a long huge-dt run). Includes the source-augmented exact case
   (`test_source.py`).
3. **Unconditional stability, per method** (`test_stability.py`):
   - `backward_euler` — unconditionally stable **and monotone** (discrete maximum
     principle: no new extrema, no oscillation, any dt>0). *This is the
     "no oscillatory blow-up" guarantee the stability invariant names.*
   - `crank_nicolson` — unconditionally stable but **not monotone** (can produce
     decaying oscillations at large dt). Use it where temporal accuracy matters
     and dt is moderate, not for the headline stability claim.
4. **Temporal order, per method** (`test_time_order.py`): backward Euler is
   1st-order, Crank–Nicolson 2nd-order in time (measured against a tiny-dt
   reference so the slopes are purely temporal).
5. **Variable diffusivity** (`test_variable_d.py`): the callable `D(t)` path
   matches the τ=∫D time-substitution analytic field (the carbon-during-cooling
   case steel uses next), and an array `D(x)` two-layer medium reproduces the
   exact series-resistance steady state — the one check that exercises the
   harmonic-mean face diffusivity.
6. **Nonlinear `D(u)`** (`test_nonlinear_d.py`, the v1.1 re-seal): a constant `D(u)`
   reproduces the scalar-`D` run to machine precision (the linear path is unperturbed);
   a varying `D(u)` matches the **Boltzmann self-similar** reference (independent
   `solve_bvp`); conservation stays exact under no-flux *and* through the flux identity
   (the cached accepted-assembly D-field); the converged step is **monotone** for `D>0`;
   and the Picard solve is tolerance-independent and **raises** on non-convergence.

## Validation boundary (what 1a does *not* claim)

Phase 1a validates the **solver machinery** with constant/given `D`. The
material parameter *values* — the Arrhenius `D₀, Q` for carbon, the `α` and
convective `h` for heat — are supplied by the **consumer** (`steel/`)
and validated **there**, against the erfc carbon-profile benchmark and published
TTT/Jominy data (Steel plan §3, Phases 1–2). The frozen seal here promises a
*correct generic parabolic solver*, not specific physical constants.

## Units & scope

- **SI throughout.** Mass vs heat mode differ only by relabelling.
- **Not in scope:** 2-D/3-D; explicit time stepping. (Nonlinear `D(u)` *was* v1.0's
  named omission — it is now **built in v1.1**, ADR 0004.) The array-`state` boundary
  is the seam where a deferred heavy regime (or a compiled core) is later slotted without
  touching consumers (ARCHITECTURE.md §8, ADR 0001).
