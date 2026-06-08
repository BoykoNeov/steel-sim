# 0001 — Implementation language & performance-scaling strategy

Status: Accepted — 2026-06-08
Scope: Program-level invariant; inherited by every per-project plan.

## Context

The program handoff is silent on implementation language; the Steel production
plan (`docs/plans/steel-production.md`) introduced Python + NumPy/SciPy. The
question was raised: wouldn't a faster language (Rust, C++, Julia) scale better
for future compute-intensive features?

Forces in play:

- **Numerics already run compiled.** The heavy work executes in C/Fortran under
  NumPy/SciPy (BLAS/LAPACK, FFTW), so vectorized array code sits within a small
  factor of C — not the order-of-magnitude gap the question assumes. Two of the
  program's own validation references embody this: REBOUND (C core, Python skin)
  and climlab (Fortran radiation core).
- **Compute-bound regimes are deferred, not foreclosed.** The scope-ceiling
  doctrine (handoff §8) defers phase-field, TCAD, GCM, and CFD out of the
  *first implementation*, but mandates loose coupling so they remain
  **expansion paths**, addable later behind module seams.
- **Agent context budget.** The program is explicitly built to be developed by
  an LLM agent with a fixed context window across the portfolio (handoff §6). A
  terse, high-exposure language minimizes context per task and failure modes
  versus C++ build systems / headers / manual memory or Rust's borrow checker.
- **Validation ecosystem is Python-native.** pycalphad, climlab, REBOUND,
  Landlab, and the MESA interfaces — the program's benchmark tools (handoff §7,
  the methodology) — are Python-reachable.
- **Contract boundaries make language a per-module choice** (handoff §6).
- **Product goal is interactive education** (responsive on a laptop), not
  maximum throughput.

## Decision

Python + NumPy/SciPy is the **default** implementation language.

Performance is addressed by escalation, not by an up-front language bet:

1. Vectorize with NumPy.
2. Accelerate a *profiled* hotspot in place — Numba (`@njit`) or Cython;
   JAX / CuPy for GPU.
3. If a single engine genuinely needs a compiled core, reimplement **that
   engine** behind its frozen `CONTRACT.md` (Rust / C++ / Julia) — consumers
   untouched. No portfolio-wide language commitment.

Engine contracts are kept **data-oriented** — plain arrays / numeric records in
and out, no leaked Python objects (no live class instances or callbacks across
an engine boundary). This makes a single boundary serve *both* as the extension
seam for a deferred heavy module (phase-field, GCM…) *and* as the language
boundary at which that module may be a compiled implementation (built as a
Python extension via PyO3 / pybind11 / Cython, or — for the heaviest — run as a
separate process exchanging arrays). This property is stated and frozen in each
engine's `CONTRACT.md`.

## Consequences

- `+` Development velocity, ecosystem reuse, and agent-friendliness now.
- `+` The escape hatch is preserved: performance is localizable to the one
  module that needs it, when profiling proves it needs it.
- `+` **The extension seam and the language seam coincide.** The regimes most
  likely to need a compiled core are exactly the deferred heavy ones, so one
  contract boundary localizes both their addition and their language.
- `−` Not maximum throughput out of the box; a future kernel rewrite is real
  work — but localized to a single module behind its contract.
- `−` Requires discipline: contracts must not leak Python-specific objects
  across engine boundaries, or the dual-purpose seam erodes.
- `−` Contributors follow the "vectorize → Numba → kernel" escalation rather
  than hand-optimizing early.

## Alternatives considered

- **Julia** — the runner-up; solves the two-language problem (C-speed +
  high-level in one language). Lost on the Python-native validation ecosystem
  and (for an agent-built program) model familiarity. Worth revisiting *if* the
  portfolio's center of gravity shifts to sustained heavy compute and the
  ecosystem tie weakens.
- **C++ / Rust from day one** — rejected: a portfolio-wide cost paid up front to
  serve compute that is explicitly out of first-implementation scope.
- **Cython / Numba everywhere** — rejected as premature optimization; apply at
  profiled hotspots only.
