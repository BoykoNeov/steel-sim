# Steel *Making* — Front-End Production Chain & the Gamified Full-Chain Spinoff

> **Companion plan to `steel-production.md`.** That plan is the **back half** of
> the chain — steel *heat-treatment*: composition in → microstructure &
> properties out, built and benchmarked through §20. **This** plan is the
> **front half** — steel *making*: ore → reduced iron → refined, cast,
> composition-on-spec billet — plus the **gamified full-chain spinoff** that
> threads both halves together with *failure propagation*.
>
> **Status: plan-only (2026-06-12). Nothing here is built yet.** This is a
> roadmap and a set of decisions, written to the same conventions as
> `steel-production.md` (per-phase **validation triad**, **scope-ceiling-as-
> consequence**, one **banked artifact** per phase, *freeze-before-reuse*).
>
> **Self-contained.** This repo is standalone; it does **not** depend on any
> former monorepo `ARCHITECTURE.md`/`PORTFOLIO.md`. Cross-references point only
> to the local `steel-production.md` and `docs/decisions/`.

---

## 1. One-line vision & the dramatic payoff

**Vision.** *Ore in, part out — and every step can fail.* Run the full
production chain — reduce ore to iron, refine and deoxidize it, trim it to a
grade, cast it, then heat-treat it (the existing back end) — as a game where
each step has real control inputs with real tolerances, **failures emerge from
the physics**, and a **failure upstream changes what the next step can produce.**
Teaching first, fun close behind, grounded in real formulas wherever the physics
is tractable and honestly labeled "plausible, not validated" wherever it isn't.

**The dramatic payoff (build this demo first — its back end is *already*
validated).** *Mis-set the alloy upstream → the part won't harden, or it
quench-cracks downstream.* Under-dose Cr/Mo (or mis-set carbon) during refining
/ ladle trim → the **hardenability C-curve shift** (back-end §2b Grossmann
factors, **built**) lands wrong → the **Jominy / through-hardening** response
(§2, **built**) misses → the quench produces either soft core or, the
spectacular failure, **tensile residual stress past yield → a quench crack**
(§18 residual-stress engine, **built**). Every link in that consequence chain is
already benchmarked. That is the hero demo: a *verified* end-to-end propagation
of an upstream mistake.

---

## 2. Relationship to the existing project — and the shared spine

| Half | Plan | Domain | State |
|---|---|---|---|
| **Back** | `steel-production.md` | Heat-treatment: composition → microstructure → properties (CCT, hardenability, tempering, residual stress, properties) | Built through §20 |
| **Front** | **this doc** | Steel-making: ore → iron → refined → cast → composition-on-spec billet | Plan-only |

- **Shared spine = the frozen `engines/diffusion` heat/mass solver.** Casting
  (F4) reuses it in **heat mode** with a mold Robin BC — *exactly* the move
  Jominy (§2a) and carburizing (§3c) already made. The solver is **not touched**;
  the front end composes *around* its frozen array seam, same as the back end.
- **The seam between the halves is the composition vector + initial state.** The
  front end's job is to *produce* the `Heat` (composition, dissolved gas,
  inclusions, cast structure, grain size) that the back end *already consumes*.
  F3 (ladle trim) is literally where the grade composition the back end reads is
  finalized — so the two halves meet at a data boundary that already exists.

---

## 3. The decision rule — what gets real physics (the triad gate)

The user's "decide step by step which steps get concrete formulas" already has
an answer in this repo: **the validation triad is the gate.**

> A production step becomes a **verified steel-sim engine** *if and only if* it
> can clear all three legs — an **analytical limit**, a **conservation law**, and
> a **published benchmark**. A step that cannot clear the triad lives in the
> **game layer**, explicitly labeled *"plausible, not validated."*

This is not a new rule — it is the existing scope-ceiling doctrine ("target the
*consequence* where the *mechanism* is a wall") applied to the front end. It
draws the verified/plausible boundary mechanically, step by step, instead of by
taste.

---

## 4. Scope ceiling — the front-end wall (consequence, not mechanism)

**Tractable, citable, triad-clearing (→ real engines):** *equilibrium
thermodynamics + lumped rates.*
- Oxide-reduction ΔG(T) (Ellingham) and equilibrium oxygen potential.
- Slag–metal partition ratios (S, P) vs slag basicity.
- Deoxidation equilibria (Al–O, Si–O products).
- Sieverts gas solubility ([H], [N] ∝ √p).
- Solidification time (Chvorinov) and microsegregation (Scheil — **already in
  the repo**).

**The named tar pit (→ game layer only, *not* built):** *transport-resolved
kinetics.* Reduction rate, decarburization/desulfurization kinetics, inclusion
flotation, dendrite growth. This is the mass-transfer / CFD wall — the
**front-end analogue of the phase-field wall** the back-end plan already named
and excluded (`steel-production.md` §5). We target equilibrium **endpoints** and
**lumped** rates, never the transport field that produced them — exactly as the
back end computes path-integrated phase *fractions*, never the dendrite *field*.

---

## 5. The physical-state record — the carrier of failure propagation

A lightweight **`Heat`** record is the object that flows through the chain and
*carries* an upstream failure to the next step.

- **Fields (physical only):** composition vector (wt%), dissolved gas ppm
  (O / N / H), inclusion volume-fraction & type, temperature / T-field, grain
  size (PAGS), residual stress, defect flags, and a short process-history /
  provenance trail.
- **Where it lives — the load-bearing architecture call (advisor):** `Heat` is
  **steel-sim *data*, threaded by a thin orchestrator — it is NOT passed into
  the frozen engines.** The engines stay **array-in / array-out** (the existing
  loose-coupling boundary, `steel-production.md` §5); the frozen diffusion core
  must stay untouched so Chip/Planet keep inheriting it. The orchestrator
  **unpacks `Heat` → plain arrays → calls the pure engine → repacks the result
  into `Heat`.** Engines never "read and mutate" the record; that would
  contaminate the reusable core.
- **What stays *out* of `Heat`:** anything game-y — cost, score, RNG seeds, time
  pressure, UI state. Those live in the game layer. `Heat` is physics only, so
  it remains a candidate steel-sim data type even if the game is later split out.

---

## 6. Failure propagation — emergent from physics, not scripted RNG

The mechanic that makes this both grounded *and* fun:

1. **Most failures emerge from physics + sampled input variance.** Each step has
   control inputs (temperature, additions, time) with tolerances. Sample the
   real process scatter, let the engine compute the resulting state, and define
   **failure = a state field crossing a spec threshold.** The downstream engine
   then propagates the off-spec state into bad properties *on its own* — no
   scripted "you failed" branch.
2. **A few genuinely-stochastic discrete events** (refractory breakout, slag
   carryover, ladle skull) are modeled as **physically-rated probabilities** —
   discrete, rare, and tied to a physical driver, not free-floating bad luck.

**Lead the demo with the chain whose back end is already validated** (§1): alloy
dosing/purity → hardenability shift (§2b, built) → Jominy (§2, built) →
quench-crack via residual stress (§18, built).

**Teachable failure links (the propagation catalogue — to be filled in as
engines land):**

| Upstream cause | `Heat` field hit | Downstream consequence | Engine status |
|---|---|---|---|
| Under-dose Cr/Mo or mis-set C (F2/F3) | composition | low hardenability → soft core **or** quench crack | **built** (§2b/§2/§18) |
| Insufficient deoxidation (F2) | dissolved O ↑ | gas/shrinkage porosity in casting → crack-initiation sites | F2 new + F4 new |
| Under-desulfurization (F2) | S ↑ | hot-tear susceptibility, MnS inclusions → toughness loss | F2 new + F4 new |
| Hydrogen not removed (F2) | H ↑ | flaking / hydrogen cracking on cooling | F2 new (Sieverts) |
| Too-fast / too-slow cast (F4) | T-field, segregation | centerline segregation → banding → uneven hardenability | F4 new (reuses Scheil) |

The right column is the discipline: a link is "real" only where its engine
clears the triad; the rest is game-layer plausibility, labeled as such.

---

## 7. Front-end phases — each a triad-gated, demonstrable artifact

Lettered **F1–F4** to avoid colliding with the back end's §-numbers. Each names
its triad concretely (the project's externalized memory) and banks one artifact.
Exact cited constants get pinned at *build* time (as every back-end phase did) —
the numbers below are illustrative targets, not asserted results.

### F1 — Reduction thermodynamics (Ellingham): ore → iron
Oxide-reduction free energy ΔG(T); reductant selection (C, CO, H₂); crossover
temperatures; equilibrium oxygen potential. The classic standalone teaching
artifact, and the cleanest possible triad clear.
- **Triad.** *Analytical:* ΔG = ΔH − TΔS straight lines; C/CO and CO/CO₂
  crossovers at known temperatures. *Conservation:* element + oxygen mass balance
  and electron (redox) balance on each reduction. *Benchmark:* tabulated ΔG_f
  (JANAF-class data, implemented from principles) — the carbon-reduces-iron-oxide
  crossover (~650–700 °C region), and the stepwise Fe₂O₃ → Fe₃O₄ → FeO → Fe
  reduction sequence.
- **Banked artifact.** An Ellingham diagram with the *reduction window*
  highlighted — which reductant reduces which oxide above which temperature.

### F2 — Primary refining (BOF/EAF): decarburize, deoxidize, partition, degas
Carbon–oxygen equilibrium for decarburization (C + ½O₂ → CO); deoxidation of
killed steel (equilibrium [Al]·[O], [Si]·[O] products); desulfurization /
dephosphorization as **slag partition** (L_S, L_P vs basicity B = CaO/SiO₂);
dissolved-gas removal by **Sieverts' law** ([H], [N] ∝ √p).
- **Triad.** *Analytical:* equilibrium constants K(T); Sieverts √p law exact.
  *Conservation:* mass + energy balance (a balance conserves by construction);
  element partition mass-conserving across slag/metal. *Benchmark:* published
  deoxidation equilibria, slag partition ratios vs basicity, and H/N solubility
  in liquid iron — used as reference facts, not copied data.
- **Banked artifact.** A "tap chemistry" panel — set blow/additions, watch C, O,
  S, P, H, N land in or out of spec; the deoxidation curve [O] vs Al added.

### F3 — Ladle / secondary metallurgy + alloy trim (the seam to the back end)
Trim the heat to a **target grade** by ferroalloy additions with recovery/yield;
inclusion control. **This is where the composition vector the back end consumes
is finalized** — so its *failure* output is the hero-demo input.
- **Triad.** *Analytical:* mixing/dilution exact. *Conservation:* mass balance on
  additions with recovery factors. *Benchmark:* hit a named grade window (e.g.
  land 4140 / 8620 within spec band).
- **Banked artifact.** "Alloy to grade" — start from F2 tap chemistry, add
  ferroalloys, land (or miss) the grade window. A *missed* spec feeds the back
  end and triggers the §6 propagation demo.

### F4 — Casting & solidification (reuses the frozen heat engine + existing Scheil)
Solidification heat extraction (frozen engine, heat mode, mold Robin BC);
solidification time (Chvorinov, t ∝ (V/A)²); microsegregation (the **existing**
Scheil); defect criteria as *consequences* — centerline segregation, shrinkage
porosity (a feeding / Niyama-style proxy), hot-tear susceptibility.
- **Triad.** *Analytical:* Chvorinov t ∝ (V/A)²; Scheil C_s(f_s) closed form;
  semi-infinite solidification √t. *Conservation:* enthalpy / latent-heat
  bookkeeping (the engine's existing guarantee). *Benchmark:* solidification time
  vs casting-modulus tables; segregation ratio vs published; defect onset vs
  cooling-rate windows.
- **Banked artifact.** A cast section — solidification map, segregation profile,
  and a defect-risk readout, all from the *same* frozen solver.

**Hand-off.** After F4 the `Heat` is a real cast billet; it flows into the back
end's grain → heat-treatment → properties chain, and the loop is **end-to-end**.

---

## 8. The game layer & the spinoff strategy

- **In-repo `game/` package now — *not* a separate repo yet (advisor; reverses
  the initial lean).** A separate repo means pip-packaging and version-pinning
  steel-sim into the game: real friction, no payoff for a solo educational
  project. The boundary that *matters* is verified-vs-plausible, and that is
  enforceable **inside this repo** with a `game/` package + convention + tests —
  the same firewall already kept between `engines/` and `steel/`. The split is
  **reversible**; do it later only if the game stabilizes and the verified core
  needs to ship independently. (This also matches the user's own hedge.)
- **The firewall rule.** `game/` may **orchestrate** engines and add the loop,
  economy, score, RNG, and UI; it may **never reimplement physics.** Any number
  with a citation + a triad-passing test lives in `steel/` or `engines/`; any
  number tuned "for feel" lives in `game/` and is labeled plausible-not-validated.
- **A guard test** asserts the firewall (mirrors the `app.py` layering guard):
  `game/` imports only the public engine surfaces; physics constants stay in the
  verified packages.

---

## 9. Verification honesty (stated up front)

Each **link** is grounded to its cited benchmark via the triad. The **chain** is
a *plausible composition*, **not end-to-end validated** — no public dataset spans
ore → part. The game's honest claim, and the teachable point itself:

> *"Every link is individually grounded in cited physics; the chain is a
> physically-consistent composition, not a validated whole."*

That sentence **is** the boundary between the verified library and the game.

---

## 10. Module map (proposed)

Keep the flat `steel/` convention; front-end modules sit alongside the back-end
ones. `game/` is a new sibling package.

```
steel/
  heat_state.py    # the Heat physical-state record + the thin orchestrator seam   (F-spine)
  reduction.py     # Ellingham ΔG, reduction equilibria                            (F1)
  refining.py      # decarb / deox / slag partition / Sieverts gas                 (F2)
  ladle.py         # alloy trim to grade, recovery, inclusion control              (F3)
  casting.py       # solidification (frozen heat engine) + Scheil + defect criteria (F4)
  demo_*.py        # one banked artifact per phase
  tests/
game/              # loop / economy / score / RNG / UI — orchestrates, never reimplements
```

---

## 11. Terms of use

**Clean** — published fundamental science. Thermo data (Ellingham/JANAF-class),
slag/gas equilibria, and partition/solubility relations are **implemented from
the equations**, with original code/prose and **no verbatim listings or
figures**; published curves are used as *reference facts for comparison*, never
copied as datasets. No export-control dimension. (Same posture as
`steel-production.md` §6.)

---

## 12. Invariant-compliance check

| Invariant | How this plan honors it |
|---|---|
| Build the toolkit once; reuse frozen | F4 reuses the **frozen** `engines/diffusion` spine in heat mode; nothing in the core is touched. |
| Phase so each stage banks an artifact | F1–F4 each name one banked artifact; F1 alone is demonstrable. |
| Validation triad from day one | Instantiated concretely per phase in §7. |
| Target the consequence where the mechanism is a wall | §4: equilibrium endpoints + lumped rates, **not** transport-resolved kinetics. |
| Updating docs is part of every change | This plan, per-module READMEs, and `docs/decisions/` entries are deliverables of each F-phase. |
| Terms of use | §11: clean, published science. |

---

## 13. Sequencing & immediate next step

**Build order (when we start):**
1. **F1 — Ellingham.** Cleanest standalone classic; clears the triad trivially;
   zero integration risk. The front end's "dramatic early win."
2. **`heat_state.py` — the `Heat` record + orchestrator seam.** The spine that
   lets steps compose and failures propagate.
3. **F4 — casting link.** Reuses the frozen heat engine + existing Scheil; proves
   the chain runs **front-to-back inside steel-sim** before any game scaffolding.
4. **F2 / F3 — refining + ladle.** Fill in the middle of the chain.
5. **`game/`.** The loop/economy/UI on a *proven verified spine* — last, by
   design, never first.

**Immediate next step (this session): plan only — this document. No code.** The
recommended first build slice, on the user's go, is **F1 (Ellingham)**.
