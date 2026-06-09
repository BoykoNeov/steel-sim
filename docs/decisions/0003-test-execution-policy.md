# 0003 — Test execution policy (the tiered gate)

Status: Accepted — 2026-06-09
Scope: Program-level invariant; inherited by every per-project plan.

## Context

The program grows by accretion: many loosely-coupled modules across `engines/`
and `projects/`, each banking its own validation triad (ARCHITECTURE.md §6–§7).
"A fast single-command test runner" is named as practical hygiene (§6), but with
the Steel flagship complete the single `pytest` had grown to **248 tests in
~165 s** — and the cost was not spread evenly. Measurement (the trigger for this
ADR):

- **~95 % of the wall-clock lives in 8 tests** that drive a *live external
  solver* (the pycalphad CALPHAD solves — `test_calphad` live cases and the
  `test_demo_calphad` panels, ~15–80 s each) or a *kernel subprocess* (the
  notebook execution smoke-test, ~5 s).
- **The other 240 tests run in ~8 s** — `engines/diffusion` alone is 18 tests in
  ~3 s.
- One live CALPHAD run was observed *flaky* (`1 failed, 247 passed`): the
  heavyweight tail is also the least deterministic part of the suite.

So the cumbersome-gate problem is, today, **a heaviness problem (8 tests), not a
breadth problem.** "Many modules → many tests" is a *future* multiplier on top of
a fast core that is currently ~8 s. Per §8 ("design for extension, do not build
the extension") this ADR fixes the present cost and *names* — without building —
the mechanism for the breadth axis when it arrives.

Forces in play:

- The inner edit loop must be fast (seconds) or the agent stops running it.
- The gate must stay *honest*: bare `pytest` must keep meaning "the whole project
  is green," or heavyweight/flaky tests rot silently between commits.
- The tracked invariant ("248 green") is externalized contract memory (§6–§7);
  it must have **one** canonical source, not a fast-count competing with it.
- Freeze-before-reuse (§6) already makes the dependency graph a DAG: a frozen
  engine's tests can only break when that engine is edited.

## Decision

**1. One `slow` marker, applied by *kind*, not by stopwatch.** A test is `slow`
iff it **drives a live external solver, a notebook kernel, or a subprocess**.
That heuristic — not a time threshold — is the rule a contributor applies without
re-measuring, and it is exactly the set that is both expensive *and*
nondeterminism-prone. Registered in `pyproject.toml` so it never warns. Today's
set is 8: the 4 live-pycalphad `test_calphad` cases, the 3 live-pycalphad
`test_demo_calphad` cases (whole file — a module-scoped fixture is shared by the
figure smoke-test, so a per-test mark would leak the fixture setup into the fast
lane), and the 1 notebook-subprocess test. A pure convergence test that merely
takes ~1 s (e.g. `test_time_order`) is **not** `slow` — it is fast core that
happens to compute.

**2. Three lanes; the default stays the full gate.**

- *Inner loop* — `pytest -m "not slow"` → the pure/deterministic core (~8 s,
  240 tests). The explicit fast lane.
- *Commit gate* — `pytest` → **everything** (the tracked 248). Run at the
  end-of-batch ritual, in CI, and before any push. **Unchanged default on
  purpose:** bare `pytest` must keep meaning "the gate," so the heavyweight/flaky
  live tests cannot rot between commits.
- *Scoped dev* — `pytest projects/<name>` (or a single file) → just the module
  under edit, using the directory grain that already exists.

**3. The canonical number is the full-gate count.** "248 green" stays the single
source of truth in docs and memory. The fast lane is documented as a *derived*
convenience ("240 in ~8 s"), never as a competing invariant.

**4. Breadth scoping is a principle, not a system (the §8 deferral).** Scope by
path during development; run the full gate at commit; **a frozen engine's tests
only need re-running when that engine is edited** (freeze-before-reuse makes this
safe). This needs *no* tooling — `pytest projects/chip` already works. Do **not**
build per-project markers, dependency-aware selection (`pytest-testmon`), or
parallelism (`pytest-xdist`) now: with the cost concentrated in 8 tests they buy
little. **Trigger to revisit:** mechanize only when the *fast lane itself* crosses
~30 s.

## Consequences

- `+` Inner loop drops ~165 s → ~8 s with a one-line command; the gate's meaning
  and tracked count are untouched.
- `+` `-m "not slow"` is a crisp, self-checking definition ("no live engine"),
  not a brittle time cutoff that drifts as hardware/tests change.
- `+` The fast lane behaves identically whether or not the optional CALPHAD /
  notebook stacks are installed (the live tests are deselected either way, rather
  than skip-vs-run depending on the environment).
- `−` Two ways to invoke the suite is a small discipline cost: contributors must
  know the commit gate is bare `pytest`, not the fast lane. Mitigated by the
  default staying full and by this ADR + the `pyproject` comment.
- `−` The `slow` marker pulls the *flaky* live CALPHAD test out of the inner loop,
  where flakiness could hide. **Mitigation:** the full gate still runs it every
  commit, and the flakiness is tracked as an open issue (below) rather than
  silently quarantined.

### Open issue (tracked, not closed by this ADR)

A live multicomponent CALPHAD solve was observed to fail once non-reproducibly
(`1 failed, 247 passed`). The `slow` split is *orthogonal* to this — it does not
fix or excuse it. Owner action when it next surfaces: determine whether the live
solve is nondeterministic (solver start point / phase-set ambiguity) or the
frozen-reference tolerance is too tight, and either loosen the band with a stated
reason or pin the solve. Until then it is a known, full-gate-visible flake.

## Alternatives considered

- **Flip the default to fast (`addopts = -m "not slow"`), run full only in CI** —
  rejected: bare `pytest` would stop meaning "the gate," and the heaviest/flakiest
  tests would rot between commits. The fast lane is opt-*in*, not the default.
- **Mark by a time threshold (e.g. `> 2 s`)** — rejected: brittle (drifts with
  hardware and incidental test growth) and not self-documenting. "Drives a live
  external engine" is a stable, intent-revealing rule.
- **`pytest-xdist` parallelism instead of a marker** — rejected for now: with the
  cost in 8 tests (some serialized behind a shared solver/import) parallelism
  yields far less than simply not running them in the inner loop. Reconsider at
  the ~30 s fast-lane trigger.
- **Per-project / dependency-aware selection (`pytest-testmon`) now** — rejected
  as premature (§8): two packages and an ~8 s core do not justify the machinery.
  Named as the breadth-axis mechanism to add at the trigger, not before.
