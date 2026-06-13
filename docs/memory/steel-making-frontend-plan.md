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

**§15 folded 2026-06-13 (plan-only) — "can the game include different historical
& modern production methods?"** Answer-as-doc-section (advisor-endorsed framing).
The load-bearing reframe: **a production *method* is a path/recipe through the
F1–F4 equilibrium endpoints already built** (because §4 built endpoints + lumped
rates, methods differ along axes the engines parametrize) → most methods are a
`game/` preset over existing engines, **not new physics**. Split: **chemical
outcome = built** vs **process dynamics (blow time/fuel/yield/feel) = §4 tar pit
→ game-flavor**. Three tiers: (1) recombine-what's-built HIGH (BOF/EAF — F2
already benchmarks BOP 27/EAF 26 ppm·%C; bloomery via F1 crossover; **cementation
≈ free via existing `carburize.py`**; crucible/finery); (2) **the P/S
slag-partition gap = the one that gates the historically richest distinctions**
(Thomas vs acid Bessemer, the §14 theme-C purity-control ramp) = F2 **Slice 2** +
P/S state — bounded, named, triad-ready, NOT speculative; (3) transport kinetics
excluded. Two honest physics gaps: P/S (above) and **wootz V/Mo carbide banding =
future research** (§14.5, beyond P/S — advisor caught this as the don't-overclaim
point). Companion to [[historical-impurity-pedagogy]] (§14). Still plan-only.

**§16 folded 2026-06-13 (plan-only) — "explore Tier 3 (the tar pit) → physics-based
game flavor for future exploration."** Elaborates §15.3 Tier 3 (process dynamics,
correctly EXCLUDED from validated `steel/` engines by the §4 wall) into a `game/`
design doctrine: **excluded-from-validated ≠ arbitrary RNG.** Load-bearing principle:
**every Tier-3 dynamic = a physics-SHAPED relaxation toward a validated F1–F4
endpoint** — shape textbook (first-order/Arrhenius/Stokes), time-constant τ
feel-tuned and in `game/`, endpoint in `steel/` (flavor animates the path, never
recomputes the number). **Advisor's blocking fix (don't re-flatten): TWO trajectory
archetypes, not one** — (A) one-sided asymptotic approach (reduction/degas/flotation/
desulf: `s(t)=s∞−(s∞−s₀)e^(−t/τ)`, fail = stop short) vs (B) **targeted optimum /
overshoot-capable** (decarb blow drives C down then over-blows → FeO; deox has a
genuine MINIMUM in dissolved O — F2's `e_O^Al=−3.9`, Al-O min ≈0.074% — over-add and
O climbs). **Decarb is Type B and is the iconic Tier-3 dynamic** (= the §14 theme-C
Bessemer story; the flame-drop = the "stop now" cue) → must NOT ship as a monotone
asymptote. The mechanic: **stopping at the wrong moment is a physically-meaningful
failure** routed through §6 (not scripted). Routability discipline = only failures
whose endpoint already lives in the validated back end propagate TODAY (**carbon →
soft-core, the one built/proven exemplar**); rest tagged *needs deferred state*
(H-flaking/inclusion-fracture/P-S-Tier2/casting-defect) → table doubles as a
build-order backlog. Productivity/throughput kept but flagged as an **economy-scale
anchor** (bloomery kg/day → BOF 300t/40min), NOT a relaxation dynamic. Firewall
intact, nothing promoted to `steel/`. Still plan-only.
