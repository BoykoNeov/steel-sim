# 0004 — Unfreeze the diffusion engine for native nonlinear `D(u)`

Status: Accepted — 2026-06-11
Scope: `engines/diffusion` (the reusable spine). Re-seals the v1.0 `CONTRACT.md`
at **v1.1**; inherited by every consumer of the engine.

## Context

Phase 1a (2026-06-08) froze the 1-D conservative parabolic solver with the
diffusivity `D` allowed as a scalar, a cell array `D(x)`, or a callable `D(t)` —
all **independent of the solution**. The contract listed **nonlinear `D(u)`**
(a diffusivity that depends on `u` itself) as its one named omission ("v1.1, not
built — keeps v1 small"), and froze the surface behind its five seal tests.

Steel's carburizing model (Phase 3c) needs exactly that. Its constant-`D` erfc
solution is the validated *analytical limit*, but it **under-predicts the absolute
case depth**, because real carbon diffusivity in austenite rises with carbon
content (Tibbetts 1980 — independent steady-state diffusion data). Closing that
named gap requires a concentration-dependent `D(C)`, i.e. a solution-dependent
`D(u)`.

Two routes were on the table:

- **(A) Compose around the freeze** — keep the engine untouched and re-linearize
  `D(C)` in the *consumer*, reassembling the sealed engine each step with a fresh
  `D(x)` array (the ADR-0001 array seam, the way `jominy` composes its lateral
  sink). Minimal blast radius; the spine stays literally frozen.
- **(B) Unfreeze the engine** — add native nonlinear `D_of_u` to the solver,
  change the contract, and re-seal. The capability lives in the spine, where it is
  validated once and inherited by every future consumer.

The contract's own rule is explicit: *changing the sealed surface means a new ADR
+ re-running the seal.* This ADR is that record. **Route (B) was chosen** (the
capability belongs in the spine, and the consumers — carburizing now, and any
future consumer — should not each re-implement a lagged nonlinear
solve around the engine).

## Decision

Add an **opt-in, additive** nonlinear diffusivity to `engines/diffusion`:

1. **`D_of_u`** — a new keyword-only constructor parameter, a callable
   `D_of_u(u_cells) -> D array`, mutually exclusive with `D` (kept a *separate*
   parameter so the `D(t)`-of-time and `D(u)`-of-state callable shapes never alias
   on one argument). With `D_of_u` the backward-Euler step is **nonlinear** and is
   solved by **Picard iteration** inside `step`: evaluate `D` from the current
   iterate, assemble, solve, repeat until the state update falls below `picard_tol`
   (cap `picard_max_iters`; `step` **raises** on non-convergence rather than
   returning an unconverged state). Each sub-solve is the ordinary backward-Euler
   M-matrix (positive `D`), so the converged step is unconditionally stable and
   **monotone**. Restricted to `method="backward_euler"` — the monotone scheme the
   stability/conservation seal covers.

2. **The linear path is byte-identical.** When `D_of_u` is `None` the original code
   path runs unchanged, so the five v1.0 seal files (`test_erfc`,
   `test_conservation`, `test_stability`, `test_time_order`, `test_variable_d`) are
   **unmodified and still pass** — the proof the unfreeze did not perturb the frozen
   behaviour.

3. **Cache the accepted-assembly D-field — the load-bearing correctness point.**
   The discrete conservation identity
   `total(stepped) − total(state) = dt·(flux_left − flux_right)` is exact only when
   `flux` uses the **same** D-field the solve assembled. On the nonlinear path the
   final solve assembles with `D(u^k)`; if `flux` re-evaluated `D_of_u` from the
   returned state it would differ by the Picard residual, degrading conservation to
   *Picard tolerance*. So `step` caches the accepted assembly's D-field and `flux`
   uses it, keeping conservation **machine-precise** (invariant 2 holds uniformly
   across the linear and nonlinear paths). Verified: a Dirichlet-inflow `D(u)` run
   closes the flux identity to ~1e-15, and carburizing `D(C)` to ~1e-18.

4. **Re-seal at v1.1** with `test_nonlinear_d.py`: constant-`D(u)` ≡ scalar-`D`
   (machine precision); a varying `D(u)` matches the **Boltzmann self-similar**
   reference (independent `solve_bvp`); exact conservation under no-flux and through
   the flux identity; monotonicity at large `dt`; Picard tolerance-independence and
   the raise-on-non-convergence. The Boltzmann solver is **test scaffolding**, not a
   public engine function — the frozen surface grows only by `D_of_u` + the two
   Picard parameters.

First consumer: `steel/carburize.py` `solve_carburize(D_of_C=…)` with the cited
`carbon_diffusivity_tibbetts`. The consumer drops to a single `Diffusion1D` with
`D_of_u` and an ordinary march — no per-step reassembly, no operator splitting. The
constant-`D` erfc path stays the default and byte-identical; `D(C)` deepens the
0.4 %C effective case depth from ~0.66 mm to ~0.97 mm (into the published ~1 mm
band) and is validated against the consumer-level Boltzmann reference.

## Consequences

- `+` The nonlinear capability lives in the **spine**, validated once, inherited by
  every consumer; carburizing's `D(C)` consumer code is simpler and cleaner than the
  array-seam workaround would have been.
- `+` **Backward-compatible.** Any consumer of the engine inherits a *richer* contract; the
  linear behaviour it depends on is byte-identical, so nothing downstream breaks.
- `+` **ADR 0001 data-boundary is preserved.** `D_of_u` is *construction-time
  configuration* that is evaluated *inside* matrix assembly and reduces to numbers; it
  never enters or crosses the plain-array `state` boundary. A compiled reimplementation
  parameterizes the `D(u)` coefficients natively, exactly as it does `D₀,Q`. The
  dual-purpose extension/language seam is intact.
- `−` `flux` becomes **step-coupled on the nonlinear path** (it reflects the most
  recent `step`, via the cache) — the one documented wart, the price of machine-exact
  conservation. The linear path's `flux` stays stateless.
- `−` `D_of_u` is **backward-Euler only** (the monotone scheme the seal covers);
  Crank–Nicolson + `D(u)` is deferred (it would weaken the monotonicity claim).
- `−` The spine is no longer "frozen and never touched" — but the re-seal process,
  the byte-identical linear path, and the additive surface preserve the *intent* of
  the freeze-before-reuse doctrine (ARCHITECTURE.md §5–6): consumers still load one
  page and trust a sealed surface.

## Alternatives considered

- **(A) Compose around the freeze (consumer-side lagged Picard / array seam)** — the
  minimal-disruption route, and the one initially recommended for *not* touching the
  spine. Rejected (by direction) in favour of native support: the capability is
  general (concentration-dependent diffusivity is not carburizing-specific), and
  re-implementing a lagged nonlinear solve in each consumer is the duplication the
  engine exists to prevent.
- **Newton iteration instead of Picard** — rejected: the carburizing nonlinearity is
  mild (Tibbetts `D` varies ~2× smoothly over the carbon range), so Picard converges
  in 2–4 iterations, is simpler, and keeps each sub-solve a monotone M-matrix. Newton
  is the escalation path if a future consumer's `D(u)` is stiff.
- **Crank–Nicolson on the nonlinear path** — deferred: it would forfeit the clean
  monotonicity guarantee the backward-Euler M-matrix gives, for temporal accuracy no
  current consumer needs.
