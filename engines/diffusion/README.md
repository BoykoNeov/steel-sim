# `engines/diffusion` — the diffusion/heat spine

The first and most-reused engine in the program (ARCHITECTURE.md §5): a
conservative 1-D parabolic (diffusion / heat) solver. **Sealed** at Steel
Phase 1a behind its validation suite, then inherited by Microchip (dopant
profiles) and Planet (EBM heat transport). **Re-sealed at v1.1** (2026-06-11)
to add an opt-in **nonlinear `D(u)`** (a solution-dependent diffusivity, solved
by an in-step Picard iteration) — the linear surface stays byte-identical, so the
v1.0 inheritors are unaffected. See `CONTRACT.md` + [ADR 0004](../../docs/decisions/0004-unfreeze-nonlinear-diffusivity.md).

## Load pointer (per-session working set, §11)

- **To *use* this engine** (from Steel/Chip/Planet): load **`CONTRACT.md`** only
  — the sealed (v1.1) one-page API. You do not need this folder's internals.
- **To *modify* this engine:** `CONTRACT.md` + `diffusion1d.py` + `tests/`. The
  tests are the seal — they must stay green, and they *are* the externalized
  memory of every contract downstream relies on (§6).

## Files

| File | What |
|---|---|
| `CONTRACT.md` | **The sealed API (v1.1).** Start here. PDE, modes, API (incl. the opt-in nonlinear `D_of_u`), sign conventions, the six invariants, the validation boundary. |
| `diffusion1d.py` | The solver: `Diffusion1D`, `Grid`/`uniform_grid`/`grid_from_edges`, `Dirichlet`/`Neumann`/`Robin`. Cell-centered finite volume + θ-method implicit stepping; opt-in nonlinear `D_of_u` (Picard-in-step, backward Euler). |
| `tests/` | The seal (24 tests): `test_erfc` (analytical limit + 2nd-order spatial convergence), `test_conservation` (exact no-flux mass balance), `test_stability` (unconditional stability, per method), `test_source` (source-augmented conservation), `test_variable_d` (callable `D(t)` + array `D(x)`/harmonic mean), `test_time_order` (BE 1st- / CN 2nd-order in time), `test_robin_heat` (heat-mode Robin + flux bookkeeping), `test_nonlinear_d` (the **v1.1 D(u) re-seal**: const-D(u)≡scalar-D, Boltzmann self-similar match, exact conservation, monotonicity, Picard convergence). |

## Run the seal

```powershell
./run_tests.ps1 engines/diffusion        # from repo root  (or just ./run_tests.ps1)
```

## Design notes (the non-obvious choices)

- **Conservation is structural, not enforced.** Finite-volume face fluxes
  telescope, so `Σ uᵢΔxᵢ` moves only through the boundaries — true on
  non-uniform grids and at any dt. The residual in the test is accumulated
  linear-solver roundoff, not a scheme defect.
- **Backward Euler is the default for a reason.** It is unconditionally stable
  *and monotone* (discrete maximum principle), so a learner picks any dt without
  blow-up or spurious oscillation. Crank–Nicolson (θ=½) is offered for temporal
  accuracy but can oscillate at large dt — see `CONTRACT.md`.
- **The engine carries no material constants.** Arrhenius `D₀,Q`, `α`, `h` are
  the consumer's; the engine consumes a generic `D` and BCs. This keeps the
  frozen surface minimal and the validation boundary honest.
- **The `state` array is the whole data contract** (ADR 0001): the seam for a
  future compiled core or a deferred heavy regime, and what the viz layer
  (ADR 0002) consumes.
