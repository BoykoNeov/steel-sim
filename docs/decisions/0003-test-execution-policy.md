# 0003 — Test execution policy (the tiered gate)

Status: Accepted — 2026-06-09 (amended same day — see Amendment)
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

**2. The routine commit gate is the fast lane; the full gate is exceptional.**
*(Reversed 2026-06-09 — see the Amendment. Originally bare `pytest` was the
per-commit default; that does not scale, below.)*

- *Routine commit gate* — `pytest -m "not slow"` (~8 s, ~240 tests). The
  **whole-repo** fast lane: every project's pure tests **and** the frozen engines'
  tests (the "used modules"). This runs before an ordinary commit.
- *Full gate* — bare `pytest` → **everything**, incl. the live-solver / kernel
  tests (the tracked 248). Run only in **exceptional** cases: editing a shared
  `engines/` module (the cross-cutting §6 case — blast radius is every consumer),
  a root-config change (`pyproject`/`conftest`), a release, or CI.
- *Docs-only change* — **no gate**. A commit touching only Markdown / `docs/` runs
  no tests.
- *Scoped dev* — `pytest projects/<name>` (or a single file) while iterating on one
  module.

The governing constraint is wall-clock at portfolio scale (~200 s × every commit ×
N projects). The full gate's cost is concentrated in the live-solver tail, which a
routine commit does not need to re-run; "run everything every commit" multiplies an
already-too-large number by the whole portfolio.

**3. The canonical green count is the full-gate number, verified at full-gate
moments.** "248 green" stays the single source of truth, but it is now confirmed at
the *exceptional* full-gate runs (engine edits, releases, CI) — **not** on every
commit. Routine commits verify the fast subset (240 / ~8 s). The fast count is a
derived convenience, never a competing invariant.

**4. Breadth scoping is a principle, not a system (the §8 deferral).** Don't build
per-project markers, a git-diff classifier, dependency-aware selection
(`pytest-testmon`), or parallelism (`pytest-xdist`) now. The two load-bearing reasons:
(a) **with one project the scopes are identical sets** — `pytest projects/steel` *is*
essentially the whole repo's fast tests today, so a classifier distinguishes the same
thing twice; and (b) the fast lane is already ~8 s, so scoping buys ~nothing while a
classifier adds a real **silent-skip failure mode** (a path rule that quietly omits a
test that should have run is worse than a convention) plus a dependency map to maintain.

A secondary note, *not* a load-bearing reason: `pytest projects/steel` collects only
the test *files* under that path, so the engine's own `engines/diffusion/tests/` are
not run **as tests**. The engine *code* is still exercised (steel imports it), and —
because the engine is **frozen** — a steel-only commit cannot regress those engine
tests anyway, so not collecting them is *harmless* here, not a real loss. It only
matters when you actually edit the engine, which is the cross-cutting **full-gate**
case. So whole-repo fast lane wins on (a)+(b), not on "scoping would miss a regression."

**When this gets built:** the committed point is **after Microchip lands** — a
manifest-backed per-project gate (see *Successor* below). The ~30 s fast-lane time is an
*earlier* signal: revisit sooner if it trips before Microchip is done.

## Consequences

- `+` The routine commit drops ~200 s → ~8 s with a one-line command, and the cost
  no longer multiplies by the portfolio — a commit to project #N never re-runs the
  other projects' live-solver tails.
- `+` `-m "not slow"` is a crisp, self-checking definition ("no live engine"),
  not a brittle time cutoff that drifts as hardware/tests change.
- `+` The fast lane behaves identically whether or not the optional CALPHAD /
  notebook stacks are installed (the live tests are deselected either way, rather
  than skip-vs-run depending on the environment).
- `+` No new tooling: `run_tests.ps1` already passes args through, so
  `./run_tests.ps1 -m "not slow"` *is* the routine gate — nothing to maintain.
- `−` The full gate no longer runs every commit, so the live-solver tests, the
  known flake (below), and (once project #2 lands) cross-project regressions run
  ~never unless something forces it. **This is the real cost** — its proper
  mitigation is CI running the full gate on push (see the Amendment), not a 200 s
  local default.
- `−` Two invocations is a small discipline cost: a contributor must know the
  *routine* gate is `-m "not slow"` and the full gate is the exceptional one.
  Mitigated by this ADR, the `pyproject`/`run_tests.ps1` comments, and the
  end-of-batch ritual.

### Open issue (tracked, not closed by this ADR)

A live multicomponent CALPHAD solve was observed to fail once non-reproducibly
(`1 failed, 247 passed`). The `slow` split is *orthogonal* to this — it does not
fix or excuse it. Owner action when it next surfaces: determine whether the live
solve is nondeterministic (solver start point / phase-set ambiguity) or the
frozen-reference tolerance is too tight, and either loosen the band with a stated
reason or pin the solve. Until then it is a known, full-gate-visible flake.

## Alternatives considered

- **Keep bare `pytest` = full as the per-commit default** — the original decision
  #2; **reversed same-day** (Amendment): it costs ~200 s on every commit even with
  one project (the cost is Steel's own live-CALPHAD tail), and multiplies by the
  portfolio. The honesty it bought (no rot) is recovered via CI, not a slow local
  default.
- **A git-diff classifier / per-project gate script now** — rejected (would repeat
  the very over-build this ADR's §4 warns against): with one project it scopes
  between identical sets, the fast lane is already ~8 s so scoping buys ~nothing, and
  a classifier that silently skips a needed test is a worse failure mode than a
  convention. Deferred to the ~30 s trigger. (See §4 for why the "narrow scoping drops
  the used-module/engine tests" framing is only a secondary, frozen-harmless note, not
  the reason.)
- **Mark by a time threshold (e.g. `> 2 s`)** — rejected: brittle (drifts with
  hardware and incidental test growth) and not self-documenting. "Drives a live
  external engine" is a stable, intent-revealing rule.
- **`pytest-xdist` parallelism instead of a marker** — rejected for now: with the
  cost in 8 tests (some serialized behind a shared solver/import) parallelism
  yields far less than simply not running them in the inner loop. Reconsider at
  the ~30 s fast-lane trigger.
- **Per-project / dependency-aware selection now** — rejected as premature (§8): two
  packages and an ~8 s core do not justify the machinery. The committed successor (see
  *Successor* below) is a **declared manifest** (project → used modules → test suites),
  not an auto-detecting heuristic like `pytest-testmon` — an explicit single source of
  truth, built once Microchip gives it a second entry to validate against.

## Amendment (2026-06-09)

Decision #2 originally kept bare `pytest` = the full gate as the per-commit default,
to keep the gate honest (heavy/flaky live tests cannot rot if they run every commit).
**Reversed the same day at the user's direction: that default does not scale.** The
full gate's ~200 s is *Steel's own* live-CALPHAD tail, so it costs ~200 s on every
commit even before a second project exists — and the program is a portfolio of many
projects. "Run everything on every commit" multiplies an already-too-large number by
the whole catalog.

New policy (Decision #2 above): the routine commit gate is the whole-repo fast lane
(`-m "not slow"`); the full gate is exceptional (shared-engine edit / root-config /
release / CI); docs-only commits run no gate.

**The trade-off this accepts, stated plainly (not hidden):** the live-CALPHAD tests,
the known flake (above), and — once project #2 lands — cross-project regressions now
run ~never unless something forces the full gate. The honesty concern that motivated
the original default-full is real; its correct home is **CI running the full gate on
push**, off the developer's critical path, *not* a 200 s local default. Full-gate CI
carries the pycalphad-on-Python-3.14 symengine install wrinkle (Phase 4 notes), so it
is a deliberate separate step the user opts into; a cheap interim is CI running
`-m "not slow"` (no optional stack).

**Built 2026-06-09** (at the user's direction — "full gate CI on push - do it"):
`.github/workflows/full-gate.yml` runs bare `pytest` (all 248, incl. the live-solver /
kernel tests) on every push + manual dispatch, ubuntu-latest, single job. Key choices,
all to make the gate *honest* (the failure mode of a full gate is a green run that
silently *skipped* the optional-stack tests rather than running them):

- **Python 3.12, not 3.14** — sidesteps the symengine wrinkle entirely (a plain
  `pip install -e .[calphad]` resolves on <3.14), rather than scripting the two-step
  dance in CI. Accepted cost: CI can't catch a 3.14-only regression in the slow tests
  (the local fast lane covers 3.14).
- **Three silent-skip guards** — a loud post-install import check (a missing extra
  fails red, not skips green), explicit `ipykernel install` (a kernelspec is *not*
  registered by `pip install ipykernel`, and the notebook test skips without one), and
  `pytest -rs` so every skip reason prints in the run log.
- **The ODbL steel TDB is downloaded at CI time** (cached, never committed — plan §6),
  so the multicomponent live test — the Open Issue's known flake — actually *runs*.
  Per this Amendment that is the flake's intended home, so it is allowed to be visible;
  the softener if it gets noisy is `pytest-rerunfailures` on the slow set, not skipping
  the TDB.

## Successor — a per-project gate, after Microchip (project #2) lands

This whole-repo tiered gate is **interim**. By user direction (2026-06-09), once
Microchip lands the gate becomes **per-project**: *a commit to a project runs only the
tests concerning that project* — its own tests **plus the tests of the modules it
uses** — not the whole-repo fast lane. Detailed design is deliberately deferred to that
build ("develop it there and then"), but the shape is fixed now:

- **A single source of truth** declaring, per project, *what it uses and which tests
  run for it* (project → used engines/modules → test suites). The per-project gate reads
  that manifest; it is **not** a heuristic git-diff guesser. Including the used modules'
  tests is the whole point of the manifest — "tests concerning the project" means the
  engine tests it depends on run *with* it, not just its own folder.

Why wait for Microchip rather than build it now: with one project the per-project scope
*is* the whole-repo fast lane (Decision #4 — identical sets), so the manifest would hold
a single trivial entry that no second consumer could validate. Microchip is the first
point the mapping has two distinct entries to get right.

**Still open to settle at that milestone** (not yet committed):

- **The `slow` set** — Microchip adds its own potentially-heavy tests (Deal–Grove,
  litho, any live numerics) to classify by the same live-solver/kernel/subprocess rule.
- **The rot mitigation actually in place** — full-gate CI on push **was** set up
  (`.github/workflows/full-gate.yml`, 2026-06-09 — see the Amendment), so the
  live-CALPHAD tests + the known flake now run on every push, not ~never. At the
  Microchip milestone, settle instead: does Microchip add its slow tests to the same
  workflow, and is the known multicomponent flake still unresolved (then either pin the
  solve / loosen the band, or add `pytest-rerunfailures`)?
