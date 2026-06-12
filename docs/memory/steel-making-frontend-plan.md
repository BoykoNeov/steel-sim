---
name: steel-making-frontend-plan
description: "the front-end (ore->billet) steel-MAKING plan + gamified full-chain spinoff direction, with its load-bearing architecture decisions"
metadata: 
  node_type: memory
  type: project
  originSessionId: 55c2e42b-5c24-47f9-af85-02b125532ba7
---

**Direction set 2026-06-12 (plan-only, nothing built yet).** A new plan doc
`docs/plans/steel-making.md` opens the **FRONT half** of the production chain —
steel *making*: ore -> reduced iron -> refined -> cast -> composition-on-spec
billet — as companion to `steel-production.md` (the heat-*treatment* BACK half,
built through §20). The eventual payoff is a **gamified full chain** where each
step can fail and a failure upstream changes what the next step can produce.

**Why this isn't a new domain:** the repo already owns the back half; the front
half is the unbuilt-but-equally-tractable other end of the same pipe. They meet
at the composition vector + initial state the back end already consumes.

**Load-bearing decisions (so a future session doesn't re-litigate them):**
- **Triad-gate rule:** a step becomes a real `steel/` engine iff it clears the
  analytical+conservation+benchmark triad; everything else is game-layer
  "plausible, not validated." (Existing scope-ceiling doctrine, applied front.)
- **Front-end wall = transport-resolved kinetics** (reduction/decarb rate,
  inclusion flotation, dendrite growth) — the front-end analogue of the named
  phase-field wall. Build only **equilibrium endpoints + lumped rates**
  (Ellingham ΔG, slag partition, deoxidation, Sieverts gas, Chvorinov, the
  **existing Scheil**).
- **`Heat` physical-state record lives in a thin ORCHESTRATOR, not in the frozen
  engines** — engines stay array-in/array-out, the frozen `engines/diffusion`
  core is untouched (Chip/Planet inherit it). Don't propose engines that mutate
  `Heat`. Game-y state (cost/score/RNG) stays out of `Heat`.
- **In-repo `game/` package now; separate-repo split DEFERRED** (reversible; a
  solo project shouldn't pay the pip-packaging tax yet). Firewall =
  verified-vs-plausible, enforced by convention + a layering guard test.
- **Hero failure-propagation demo** = alloy dosing/purity -> hardenability shift
  (§2b, built) -> Jominy (§2, built) -> quench crack via residual stress (§18,
  built): a *verified* end-to-end propagation. Lead with this; its back end is
  already benchmarked. See [[di-crosscheck-source]], [[residual-stress]],
  [[bainite-anchoring-probe]].

**Build order when we start:** F1 Ellingham (recommended first slice) ->
`heat_state.py` -> F4 casting link (reuses frozen heat engine + Scheil, proves
front-to-back) -> F2/F3 refining+ladle -> `game/` last. The advisor reviewed and
sharpened this framing (it reversed my initial lean toward an immediate repo
split). Plan doc is self-contained (no monorepo `ARCHITECTURE.md` refs — that
file doesn't exist here; [[repo-self-contained]]).
