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

> **As built — 2026-06-12 (build-order item 2).** `steel/heat_state.py` (+ `demo_heat_state.py`,
> `plots.heat_state_figure`, `tests/test_heat_state.py` 15 + `test_demo_heat_state.py` 5; fast lane
> 522 → **542 green**). No engine touch, no back-end touch, no ADR (this plan is the record). The
> build, vs the plan:
> - **The carrier.** `Heat` is a frozen, **immutable** dataclass: every orchestrator step returns a
>   *new* `Heat` with one `ProcessStep` appended (the provenance trail), so history can't be rewritten.
>   It **composes the existing back-end `Steel`** as its composition field (not a parallel type) — so
>   `Heat.as_steel()` is a no-op unpack and the round trip `Steel → Heat → Steel` is exact. The §5
>   fields a not-yet-built phase would fill (dissolved O/N/H from F2, inclusions from F3, residual from
>   §18/F4) default to **`None` = "no engine has produced this yet"** — the honest "unmeasured".
> - **The seam.** `heat_treat` **unpacks `Heat` → `Steel`, calls the public `sweep.evaluate`** (which
>   wraps the frozen array engine one level down — the orchestrator does *not* reach into the diffusion
>   core), and **repacks**: a spec miss raises the **soft-core** flag. This is the **general path** (any
>   composition), which is why the failure-propagation proof rides here: a properly-dosed 4140 oil-quenches
>   to 96 % martensite / 632 HV; under-dose its Cr/Mo and the *same* quench lands 40 % / 416 HV → flagged,
>   carried downstream. No scripted failure — the back-end martensite fraction crossing the
>   `MIN_MARTENSITE_SPEC` line (a *spec*, labelled, not a fitted constant).
> - **Honest bound (advisor catch).** The §18 residual engine is **grade-keyed and atlas-anchored**
>   (`ATLAS_STEELS` = {1080, 4340}), so an *off-spec composition → quench-crack* chain **cannot run
>   today** — it is **deferred**. `quench_crack_check` demonstrates the *same repack pattern* over §18
>   for a *fixed* atlas grade (4340: +386 MPa surface tension → quench-crack-risk), clearly labelled as
>   the stand-in, so the spine is shown composing across two engines without overclaiming.
> - **No new physics, no triad.** The spine computes no material behaviour; its "teeth" are
>   **structural** — round-trip identity, immutability, deterministic flag propagation (same posture as
>   inverse design). The §6 defect catalogue stays as-engines-land; this builds the carrier + the
>   pattern + one general propagation flag (+ the bounded atlas illustration), nothing more.
> - **Surfacing.** Demo (text trail) + banked figure (`docs/figures/steel-heat-state.png`: the
>   propagation bars + the atlas residual panel) + gallery card (new **"Front-end spine"** section) +
>   root-README tour row + `steel/README.md` module-map row. **Notebook & app deferred** (same reasoning
>   as F1 — both surfaces are heat-treatment-framed).

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

> **As built — 2026-06-12.** `steel/reduction.py` (+ `demo_reduction.py`,
> `plots.ellingham_figure`, `tests/test_reduction.py` 17 + `test_demo_reduction.py` 3;
> fast lane 526 → **546 green**). Standalone — touches no engine and no back-end module;
> no ADR (this plan is the record). The build, vs the plan:
> - **Physics.** Per-species standard ΔHf,298 / S°298 (Fe, FeO, Fe₃O₄, Fe₂O₃, C(gr), CO,
>   CO₂, H₂, H₂O(g), + Al/Si/Mn/Cr/Ca oxides for the hierarchy) → reaction ΔG°(T) =
>   ΔH° − T·ΔS° **per mole O₂**. The crossover-driving values were **verified against
>   NIST/CODATA before pinning** (the `di-crosscheck-source` discipline — the crossover is a
>   ratio of differences of large numbers, hypersensitive). **No fitted constant.**
> - **Triad — what cleared, honestly.** *Teeth* (un-tuned data, could have missed): the
>   carbon/wüstite crossover lands **746 °C** (window 650–800; wüstite non-stoichiometry
>   would slide it to ~710), the Fe₂O₃→Fe₃O₄→FeO→Fe stack orders right (the stepwise
>   inter-oxide reactions), the Ca<Al<Si<Mn<Cr<Fe hierarchy orders right, and the linear
>   model hits the famous JANAF ΔfG°(CO,1000 K) ≈ −200 kJ/mol anchor to <1 kJ (bounds the
>   omitted-kink error). *By construction* (not teeth): element/O balance, the ΔG°(298)≡ΔH−298ΔS
>   identity, Hess path-independence.
> - **Scope ceiling (named).** Straight lines, **ΔCp ≈ 0** — melting/boiling kinks omitted;
>   the reduction sequence is the high-T one (wüstite disproportionates below ≈ 570 °C, not
>   encoded); wüstite is non-stoichiometric (ΔHf −266…−272 kJ/mol — why the window is generous).
> - **Surfacing.** Demo + banked figure (`docs/figures/steel-ellingham.png`) + gallery card
>   (new "Ironmaking" section) + README tour row. **Notebook & app deferred** (both are
>   heat-treatment-framed; an ironmaking section is a narrative call for when there's >1
>   front-end phase to anchor it — advisor).
> - **pO₂ in, nomographic scales out** (the CO/CO₂ & H₂/H₂O margin nomographs are a viz
>   flourish, deferred). The equilibrium oxygen potential `equilibrium_oxygen_pressure` *is*
>   built — the bridge to F2.

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

> **As built — 2026-06-13 (build-order item 4, Slice 1).** `steel/refining.py` (+ `demo_refining.py`,
> `plots.refining_figure`, `tests/test_refining.py` 20 + `test_demo_refining.py` 6; fast lane → **614 green**,
> +26). **Standalone — no solver, no engine/back-end touch, no ADR** (this plan is the record). The advisor
> reframed the honesty before any code, and the build follows that reframe:
> - **The carbon axis is the *validated* propagation — the proof rides there.** My first read ("the back end
>   doesn't consume O/N/H, so F2 only *fills fields*") was half-wrong: the back end **does** consume carbon,
>   and the blow sets it. So **over-blow → carbon below target → the existing** `heat_state.heat_treat` **raises
>   its soft-core flag** — a real refining mistake → a real, *benchmarked* back-end consequence. This is the same
>   class as the **spine's Cr/Mo under-dose propagation** (a chosen composition/control error reaching the
>   already-benchmarked back end) — *not* F4's centerline band, where Scheil **computes** the enrichment from new
>   cited physics; here F2's new physics (next bullet) sits on the *deferred*-consequence side, while the
>   validated link rides a control input the back end already responds to. Built: a 4140-backbone heat blown to
>   0.40 %C through-hardens (94 % M,
>   628 HV) at oil/Ø15 mm; over-blow to 0.20 %C and the *same* quench drops to 84 % M / 450 HV → **soft core**.
>   Emergent (martensite fraction crossing `MIN_MARTENSITE_SPEC`), not scripted.
> - **The gas/inclusion fields — the user's ask — are filled; their consequences are honestly deferred.** The
>   decarburization that sets carbon **raises dissolved O** (the inverse C–O product), deoxidation removes it
>   (generating Al₂O₃), degassing strips H/N — so `oxygen_ppm` / `hydrogen_ppm` / `nitrogen_ppm` /
>   `inclusion_*`, **`None` since the spine**, are now populated. But the *downstream* of that state (porosity,
>   flaking, hot-tear) is F4-Slice-2 / game-layer (the §6 links marked "F2 new + F4 new"): F2 **sets up** that
>   propagation, it does not yet close it. Under-deoxidize → **porosity-risk** flag; under-degas → **hydrogen-
>   flaking-risk** flag (consequences deferred). Nitrogen is **reported, not spec-flagged** (the Sieverts value
>   is the solubility *limit*, not the kinetically-limited actual — a hard N spec would flag every heat).
> - **Physics & the two-tier provenance (di-crosscheck applied).** *Robust-anchor teeth:* the carbon–oxygen
>   product `[%C][%O] ≈ 0.0022` at 1600 °C (ΔG° = −19840 − 40.65·T; Vidhyasagar 2023 / standard, benchmarked
>   vs measured BOP 27±3, EAF 26±2 ppm·%C), the Sieverts solubilities **H ≈ 26 ppm** (log K = −1900/T + 2.423)
>   and **N ≈ 450 ppm** (ΔG° = 3598 + 23.89·T, Pehlke–Elliott; cross-checked 3000 ppm @ 50 atm → 424 @ 1 atm),
>   and `e_O^Al = −3.9` (Sigworth & Elliott 1974) — all read from the sources before pinning. The **deoxidizer
>   hierarchy Al ≫ Si > Mn** is *computed* from the pinned constants and verified to match **F1's Ellingham
>   oxide-stability order** (Al₂O₃ < SiO₂ < MnO) — independently sourced (Henrian deox constants vs Raoultian
>   ΔG°f), so their agreement is a real cross-module coherence tooth, not an assertion. The **Al–O minimum**
>   (~0.07 % Al; the dilute cartoon misses it) is the headline artifact feature — and its *location* is
>   `−m/(n·ln10·e_O^Al)`, **independent of the scattered `K_Al`**, so the tooth doesn't ride the source-
>   sensitive tier (the absolute deox constants are Turkdogan-class, ranking + order-of-magnitude only).
> - **Scope ceiling (named).** Equilibrium endpoints, never the transport *rate* (the blow/flotation/pick-up
>   kinetics — the front-end tar pit, §4); 1-wt% Henrian dilute, a single dominant deoxidizer with `f_M ≈ 1`;
>   dissolved gas is the solubility *limit* (real pick-up below it); inclusion content is *generated* oxide
>   (flotation removal not modelled). **Slag partition (L_S, L_P vs basicity — desulfurization /
>   dephosphorization) is Slice 2**, deferred because it needs S/P state the `Heat`/`Steel` does not carry
>   (a state extension is its own call) — *not* pulled in just to widen the slice.
> - **Surfacing.** Demo (tap-chemistry trail + the carbon divergence) + banked figure
>   (`docs/figures/steel-refining.png`: the deoxidation curve with its minimum, the C–O coupling, Sieverts √p
>   degassing, the carbon-axis propagation) + gallery card (new **"Refining (front-end)"** section) + both
>   READMEs. **Notebook & app deferred** (same as F1/spine/F4 — all heat-treatment-framed).

> **As built — 2026-06-13 (Slice 2 — slag partition).** `steel/slag.py` (+ `demo_slag.py`, `plots.slag_figure`,
> `tests/test_slag.py` 16 + `test_demo_slag.py` 7; suite 642 → **665 passed / 2 skipped**, +23). **One back-end touch — the
> deferred state extension, now authorized:** `sweep.Steel` gains `P` / `S` (default 0). It is **additive and
> inert** — every existing call names its arguments (field order moot), `minor()` deliberately excludes P/S,
> and the full suite stays green byte-identical (the non-breaking proof). No solver, no engine touch, no ADR
> (additive inert fields don't change `Steel`'s semantics; this plan is the record). The advisor's pre-code
> review set the posture, and the build follows it:
> - **This is benchmarked physics (the F1/F4 class), NOT a spine-class propagation — the load-bearing honesty.**
>   Slice 1's carbon axis was a *validated* end-to-end propagation because the back end **consumes** carbon.
>   **P and S have no such consumer** — hardenability/hardness read C/Si/Mn/Ni/Cr/Mo only — so this slice's
>   proof is the *physics checked against published facts*, and its downstream consequence (P → GB
>   embrittlement / DBTT; S → red-shortness / MnS / hot-tear) is **honestly deferred** (the §6 rows "F2 new +
>   F4 new", §14's unpinned P→DBTT slope). A structural test pins it: an off-spec-P/S heat heat-treats
>   *identically* to a clean one. F2 Slice 2 **sets the impurity state; it does not yet close its consequence.**
> - **The teeth avoid the vacuous-benchmark trap.** "L rises with basicity" is baked into any correlation with
>   a basicity term — asserting it proves nothing. The teeth that could have come out wrong: (1) **the opposite
>   oxygen dependence of P and S**, the headline — dephosphorization is an oxidation (Healy 1970 carries
>   **+2.5·log %Fe_t**), desulfurization a reduction (the sulfide-capacity partition carries **−log a_O**), two
>   signs from two *independently sourced* correlations, so their being opposite is **computed, not tuned** (it
>   cross-coheres with Slice 1 exactly as the Al≫Si>Mn deox hierarchy cohered with F1's Ellingham order):
>   `desulfurize` **reads the Heat's dissolved oxygen** (Slice 1's kill), so the *same* ladle slag barely works
>   on the un-killed blow (L_S≈12 at ~53 ppm O) and strips sulfur after the kill (L_S≈140 at ~4 ppm O) — the
>   physics *dictates the process order* dephos (oxidizing) → deox → desulf (reducing); (2) **the acid/basic
>   endpoint** — an acid slag leaves L_P≈O(1) even though oxidizing (lime-poor → no stable phosphate) = *why
>   acid Bessemer rails cracked*, vs basic L_P~400 (Thomas); (3) **order of magnitude vs measured plant L** —
>   basic-converter L_P lands ~400 (measured BOF 50–200; Healy over-predicts at high lime, named), ladle L_S in
>   the 10²–10³ band. By construction (NOT teeth): the metal↔slag mass-balance partition (`[%X]=[%X]₀/(1+L·R)`)
>   and the **Mn:S → MnS** stoichiometry (conservation-clean — Mushet's manganese that made Bessemer sound,
>   §14 theme B).
> - **Physics & two-tier provenance (di-crosscheck applied).** *Source-sensitive tier (ranking + order of
>   magnitude):* Healy 1970 `log L_P = 22350/T + 0.08·%CaO + 2.5·log %Fe_t − 16`; Sosinsky–Sommerville sulfide
>   capacity `log C_S = (22690 − 54640·Λ)/T + 43.6·Λ − 25.2`; the C_S→L_S conversion `log L_S = log C_S − log
>   a_O − 770/T + 1.30`; Duffy–Ingram component optical basicities (FeO/MnO themselves optimized from
>   sulfide-capacity data); the Fe–FeO anchor `[%O]=0.213·a_FeO` (used only to put L_P and L_S on a shared
>   oxidizing-power axis). *Robust reads (the teeth):* the **signs** of the two oxygen dependences, the
>   acid/basic endpoint, the measured-range benchmark. P/S equilibria scatter by a factor of several between
>   studies — the read is ranking + order of magnitude.
> - **Scope ceiling (named).** Equilibrium partition endpoints, never the slag-metal mass-transfer *rate* (§4);
>   a single lumped slag of fixed mass ratio; dilute 1-wt% Henrian metal (`a_O ≈ [%O]`); theoretical optical
>   basicity; `a_FeO ≈ X_FeO` (Raoultian) where the metal-oxygen link is drawn. P/S **carried but inert** (no
>   validated consumer); the P/S that high-impurity ferroalloys would *add back* in the ladle trim is a named
>   deferral (like F3's carbon carry-in), not modelled.
> - **Surfacing.** Demo (the working route + the two history failures + Mn:S→MnS) + banked figure
>   (`docs/figures/steel-slag.png`: L_P vs basicity, L_S vs oxygen, the opposite-oxygen contrast, the residual
>   P/S trail) + gallery card (a second **"Refining (front-end)"** card) + both READMEs. **Notebook & app
>   deferred** (same as the other front-end phases). **The P/S slag-partition gap §15.4 flagged as the single
>   highest-leverage front-end build is now closed** — the §14 theme-C purity ramp and the Thomas-vs-acid-Bessemer
>   distinction are expressible (§15.2 map updated). Wootz V/Mo carbide banding (§14.5) remains future research.

> **As built — 2026-06-14 (the hydrogen consequence — closing F2's deferred dissolved-gas downstream).**
> `steel/hydrogen_flaking.py` (+ `demo_hydrogen_flaking.py`, `plots.hydrogen_flaking_figure`,
> `tests/test_hydrogen_flaking.py` 12 + `test_demo_hydrogen_flaking.py` 5). **Standalone (closed-form, no
> engine, no ADR);** this plan is the record. F2's `degas` already *fills* `hydrogen_ppm` and raises the
> chemistry-state **`hydrogen-flaking-risk`**; this closes the **consequence** F2 deferred — whether a *part*
> actually flakes — which is a **geometric** (out-diffusion) question, the two-tier cold-short(propagation) /
> red-short(new-consumer) pattern: refining sets the risk, this the consequence (`hydrogen-flaking` flag).
> - **Model = analytic slab desorption (Crank), NOT the engine.** Advisor's sharpening: an engine H-solve
>   would be **redundant with the engine's existing analytic seal** (`test_erfc.py`), not a new check — the
>   flaking verdict is a scalar (peak/centre residual H after a cool/bake), which the closed-form series gives
>   directly. Standalone like reduction / casting Slice 1.
> - **The ONE genuine tooth — soft, OoM cross-source coherence (gate run on paper FIRST).** The
>   dehydrogenation time from an **independently pinned** lattice `D_H` reproduces cited bake-vs-section
>   practice **without tuning**: `D_H` set to the accepted room-T α-Fe lattice value (~8.9×10⁻⁹ m²/s; Kiuchi–
>   McLellan 1983 reanalysis, cross-checked DFT/MD Jiang–Carter/Hasan 2020), then the **lead anchor = a 500 mm
>   forging takes ~10 days** (heavy forgings → days-to-weeks) — the load-bearing check. The 1-inch → ~0.6 h
>   "1 h/inch" thin-section number is **OoM sanity only** (a generic soak-to-temperature rule, not
>   dehydrogenation-specific). Two independent sources (a room-T diffusivity vs bake times), so the agreement
>   is a real check. **OoM-grade**: real steel traps H 10–100× below lattice → the model is a conservative
>   *lower bound* (named scatter); absolute magnitudes also ride on the `target_fraction=0.25` (75 %-removal)
>   criterion (90 % removal ~1.5×, 95 % ~doubles) — the `τ ∝ L²` scaling is robust to it. By construction
>   (NOT teeth): the `τ ∝ L²` scaling (Chvorinov-`M²` class) and the verdict rule. **Ceiling:** out-diffusion
>   only — *not* the γ→α supersaturation / H₂ void-pressure thermodynamics (the "can the H escape in time?"
>   geometric question, not the crack itself).
> - **Hero = same ladle H, the section decides** (the only genuinely-new content vs refining.py): a 4140 heat
>   degassed to ~3.6 ppm (risk set), cast into two sections + the *same* bake → thin sound, thick **flakes**
>   (adds `hydrogen-flaking`), thick saved by a long enough hold (the bake lever). The analog of "same quench,
>   two compositions → soft core" and "same casting, two locations → hard band". Suite **+17 tests**, all
>   green; no engine touch, no ADR. **Notebook & app deferred** (as the other front-end phases). Gas
>   **porosity** (the other F2 `porosity-risk` consequence) is now BUILT (next banner); hot-tear remains deferred.

> **As built — 2026-06-14 (the gas-porosity consequence — closing F2's deferred dissolved-oxygen downstream).**
> `steel/gas_porosity.py` (+ `demo_gas_porosity.py`, `plots.gas_porosity_figure`,
> `tests/test_gas_porosity.py` 17 + `test_demo_gas_porosity.py` 6; suite 741 → **764 passed / 2 skipped**, +23).
> **Standalone (closed-form, no engine, no ADR);** this plan is the record. F2's `deoxidize` already *fills*
> `oxygen_ppm` and raises the chemistry-state **`porosity-risk`** when the killed-bath oxygen clears a single,
> **carbon-blind** line (`MAX_DISSOLVED_OXYGEN_PPM` = 30 ppm); this closes the **consequence** F2 deferred —
> whether a *casting* actually blows **CO holes** — which is a fundamentally **carbon-aware** question. The
> two-tier cold-short / red-short / flaking pattern: refining sets the risk, this the consequence
> (`gas-porosity` flag). **The sibling of hydrogen-flaking, but where flaking's second lever was geometric,
> this one is the *carbon*.**
> - **Model = the carbon-aware CO product (the SAME C–O equilibrium F2 runs on), held oxygen.** CO evolves
>   and is trapped where the dissolved product `[%C]·[%O] > K_CO` (= `refining.carbon_oxygen_product`, the
>   converter's own equilibrium, here at a representative freezing-front T ≈ 1530 °C / p_CO = 1 atm). The
>   verdict is the **supersaturation** `S = [%C][%O]/K_CO` (> 1 ⇒ porous). The cooling-supersaturation
>   mechanism is physical: the heat equilibrates with CO at tap (1600 °C) but K_CO *falls* as it cools to the
>   front, so a tap-line (undeoxidized) heat tips supersaturated — killing it (dropping O below the line)
>   buys the margin. No solver; the latent-heat field (`solidification.py`) would buy **no new content** (the
>   verdict is a chemistry scalar, not a T-map) — the same B-over-C logic that kept hydrogen-flaking
>   standalone.
> - **TWO advisor catches BEFORE writing (paper-gate), both load-bearing.** (1) **Do NOT Scheil-enrich the
>   dissolved oxygen** — reprecipitation pins O in killed steel as T falls, so naive O-Scheil is *wrong* (not
>   a "named ceiling"): it false-positives sound killed steel (a killed 0.4 %C/3 ppm heat would cross at
>   f_s ≈ 0.81). **Hold O at the as-refined value** (bonus: no k_O to pin). (2) **Carbon-Scheil enrichment is
>   a trap** — `casting.py` explicitly disowns it (`enrich_carbon=False`, "Scheil over-predicts interstitial
>   C"); making it the load-bearing amplifier would contradict our own ceiling. **My spot-check confirmed it
>   worse than feared:** a well-killed *high-carbon* heat (1.0 %C/3 ppm) crosses at f_s ≈ 0.90 < cutoff → the
>   enrichment-verdict false-flags it **porous**, yet 1095/52100 cast sound routinely (the Scheil f_s→1
>   singularity drives *any* held O over the line). So the **bath/front product is the load-bearing verdict**;
>   carbon-Scheil survives only as a **conservative, decorative secondary** (`solidification_co_fraction` — a
>   "freezing erodes the margin" indicator, cutoff-dominated, never the pass/fail).
> - **NO claimable tooth — by-construction + cited inputs (the reversible-TE / TME landing, a feature).** The
>   criterion *is* the cited C–O equilibrium evaluated against held composition, so it cannot independently
>   "fail". The one soft **OoM-coherence note** (really by-construction): the critical oxygen
>   `O_crit(C) = K_CO/[%C]` falls as `1/C` with **no tuning**, reproducing "high-carbon steels must be killed,
>   only low-carbon steels can be rimmed / semi-killed" — and exposing the carbon-blindness of a flat oxygen
>   spec (the 30 ppm line crosses `O_crit` near C ≈ 0.67 %: leaner it over-warns, richer it under-warns).
>   Nothing else claimed.
> - **Hero = same oxygen, the carbon decides** (the non-duplication, made the demo's job per the advisor):
>   1080 and 8620 given the *same* light kill, **both within the 30 ppm spec → both risk-cleared**, yet the
>   1080 sits right on the CO line (O_crit ≈ 25 ppm) and **blows holes** while the 8620 has an order of
>   magnitude of carbon-margin (O_crit ≈ 100 ppm) and is **sound** — the 1080 carrying *less* oxygen than the
>   sound 8620. A full kill saves the 1080 (the deox lever). The two flags **disagree because of carbon**:
>   without that, the consequence would be refining restated. **The 1080's modest S ≈ 1.05 is sign-robust, not
>   marginal (advisor sharpening, verified):** the C–O coupling self-limits a high-carbon heat's dissolved O
>   to ~its C–O equilibrium, so the under-killed 1080 sits *exactly on the tap C–O line* (`C·O = K_CO(1600)`
>   to machine precision) — its verdict therefore reduces to the **cooling-supersaturation ratio**
>   `S = K_CO(tap)/K_CO(front)`, which is `> 1` for *any* front below tap (physically certain, not a coin-flip
>   on the 1530 pin) and *grows* as the front cools toward the true freezing range (verified S: 1.000 at 1600,
>   1.051 at 1530, 1.091 at 1480). The named ~7 % absolute-K_CO scatter largely **cancels in that ratio** (the
>   ΔG° *slope* is better constrained than the absolute level). So a high-C steel is never *deeply* porous from
>   O — it lives at the boundary and must be killed — but the *sign* of that verdict is guaranteed.
> - **Ceiling:** the CO-*evolution criterion*, not the bubble nucleation/escape kinetics that set how much
>   porosity actually results; p_CO pinned at 1 atm (the **ferrostatic head** that suppresses CO deep in a
>   tall section — the deep ingot rims less — is a named over-conservatism); shrinkage / Niyama porosity (a
>   feeding problem) stays the F4-Slice-2 deferral. Suite **+23 tests**, all green; no engine touch, no ADR.
> **Notebook & app deferred** (as the other front-end phases). Hot-tear remains the last open F4/F2 defect.

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

> **As built — 2026-06-13 (build-order item 5, Slice 1).** `steel/ladle.py` (+ `demo_ladle.py`,
> `plots.ladle_figure`, `tests/test_ladle.py` 14 + `test_demo_ladle.py` 7; fast lane 590 → **611**,
> full suite **618 passed / 2 skipped**). **Standalone — no solver, no engine touch, no ADR** (this plan
> is the record). The advisor's pre-code reframe set the slice; two of its calls were load-bearing:
> - **Grade-band miss ≠ soft-core — probe the back end first.** A *marginal* recovery miss lands inside
>   the wide commercial window (Cr 0.95→0.80 recovery ≈ 0.86 % Cr, still in 4140's 0.80–1.10 band) and
>   nowhere near a soft core; the spine's soft core needed a *substantial* under-dose. Probed at 4140 oil
>   Ø15 mm: the bottom corner of the band still through-hardens (~89–92 % M), and you must drop to ~half
>   recovery (Cr ≈ 0.53) to fire **both** flags. So the hero is a **gross under-trim** (recovery roughly
>   halved), not scatter — the "in-band but still soft at a bigger section" subtlety is **deferred**.
> - **F3 is spine-class, not a physics phase.** No new thermodynamics: the trim is mass-balance arithmetic
>   + cited recovery + cited windows. So — like the `heat_state` spine — its own checks are **structural**
>   (round-trip identity, conservation, dilution, immutability), *labelled* by-construction, and the grade
>   window is a **labelled spec** (the SAE J404 band, like `MIN_MARTENSITE_SPEC`), not a benchmark. The
>   genuinely **validated** content is the back-end propagation (under-trim Cr/Mo → soft core), the **same
>   class as the spine's hand-set under-dose** — F3's new value is that the under-dose is now **produced by
>   a modeled ladle operation**: the additions were sized for an *assumed* recovery the bath did not
>   deliver. The tier-2 scatter in the cited recovery factor *is* the failure mechanism (turning the weak
>   input into the point), and it is the front-end consequence of F2's deox state.
> - **Built — the seam.** `from_tap` (alloy-lean post-refining origin, on F2's carbon) → `trim_to_grade`
>   sizes ferroalloy charges with a **dilution-exact closed-form inverse** (`additions_for_grade`) and mixes
>   them at the *actual* recovery (`mix`). On-grade when recovery holds (Cr 1.00/Mo 0.20 → 94 % M, in-band,
>   through-hardens); the under-recovered heat lands Cr 0.53/Mo 0.10 → **off-grade flag** (F3) + **soft-core
>   flag** (back end) at the same oil Ø15 mm quench → 81 % M. **One mistake, two flags;** *at this section*
>   off-grade fires *before* soft-core (the window is the conservative early warning) — but the ordering is
>   **section-dependent** (a thicker section can soft-core an *on-grade* heat: the chemistry-spec ≠ H-band
>   point, the same "in-band but still soft" subtlety deferred above).
> - **Named deferrals (not built).** **Carbon carry-in** — high-carbon ferrochrome/ferromanganese carry
>   ~6–8 % C, so the 4140 trim *would* add **+0.18 %C** (~45 % of the grade's carbon — quantified by
>   `carbon_pickup_pct`, the reason low-carbon ferroalloys exist); held off F2's carbon axis here. The
>   deox-state-dependent recovery coupling (F2 → F3). **P/S residual bands and desulf/dephos** stay out of
>   the window — the `Steel`/`Heat` vector carries no P/S (the same state gap as F2 Slice 2).
> - **Notebook & app deferred** (heat-treatment-framed, as F1/spine/F2/F4). Gallery "Ladle trim" card
>   inserted before Casting (chain-forward); both READMEs updated.

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

> **As built — 2026-06-12 (build-order item 3, Slice 1).** `steel/casting.py` (+ `demo_casting.py`,
> `plots.casting_figure`, `tests/test_casting.py` 17 + `test_demo_casting.py` 5; fast lane 542 →
> **564 green**). **Standalone — no solver, no engine touch, no ADR** (this plan is the record). Two
> findings reshaped the plan's "thin reuse" wording into a **new-physics phase**, and the build was
> **sliced** accordingly (the user okayed Slice 1 now, Slice 2 deferred):
> - **The plan's premises were wrong, and the slice follows from fixing them.** (1) The repo's "Scheil"
>   is *additivity* (transformation kinetics, `pathint.py`), **not microsegregation** — the
>   ``C_s = k·C₀·(1−f_s)^(k−1)`` solute-redistribution is *new* (small, closed-form). (2) There is **no
>   solidification thermodynamics** in the repo (no liquidus/solidus/latent-heat/partition data) — also
>   new. So F4 is new physics, not a reuse. The advisor's reframe: the **front-to-back proof rides on the
>   microsegregation → composition handoff through the `heat_state` spine, NOT the latent-heat solve** —
>   so Slice 1 builds the proof and needs **no solver at all** (the "reuse the heat engine" move is
>   entirely in the deferred Slice 2).
> - **Slice 1 (built).** Scheil microsegregation (cited partition coefficients ``k`` in two honest tiers:
>   **Won & Thomas 2001** Table I for C/Si/Mn/P/S in δ *and* γ — **read from the paper, primary-source
>   verified**, the teeth rest here; **ISIJ in-situ** for Cr/Ni/Mo — **verified against that paper but
>   γ-mode-measured, used as a single representative value, δ not separately pinned**, the demo verified
>   robust across the δ/γ spread so it does not rest there) + the **centerline-enriched Heat** handed to the
>   back end (a real "cast" origin
>   replacing `from_grade`'s stand-in) + **Chvorinov** ``t = B·M²``. **The chain closes front-to-back:** a
>   4140 casting heat-treats **non-uniformly** — bulk under-hardens (soft core), the enriched centerline
>   over-hardens into a **+93 HV hard band** (the §6 uneven-hardenability link), all from cited physics.
> - **Triad — what cleared, honestly.** *Teeth:* the **conservation** mass balance (solute in solid +
>   liquid returns C₀ — two independently-written closed forms reconciling, *not* the tautological
>   "the closed form integrates to its own value"); the **severity ordering** (smallest cited ``k`` — S,
>   C, P — enriches the last liquid most; Cr/Ni mild, the un-tuned data reproducing *why* S/P are the
>   dangerous segregators). *By construction:* ``C_s(f_s=0)=k·C₀``, ``t ∝ M²``.
> - **Scope ceiling (named).** Scheil is the **no-back-diffusion upper bound** (over-predicts segregation);
>   **carbon is the worst case** (interstitial, fast back-diffusion) → the handoff leans on the
>   **substitutional** alloys (Mn/Cr/Mo/Ni/Si, which also drive hardenability) and leaves C at nominal.
>   The δ/γ **peritectic** (C > 0.53 %; the demo grades are below it), dendrite coarsening, and the
>   ``f_s → 1`` singularity (characterised at a cutoff ``f_s*``) are omitted.
> - **Slice 2 (deferred, named).** The **latent-heat solidification temperature-field map** on the
>   diffusion solver (an apparent-heat-capacity / enthalpy formulation — *not* a trivial source term,
>   because the solver's PDE carries no LHS capacity coefficient) and the **defect criteria** (Niyama
>   shrinkage-porosity, hot-tear — mostly game-layer "plausible, not validated"). The map is iconic but
>   does **not** feed the composition handoff the proof rides on, so it does not gate Slice 1.
> - **Surfacing.** Demo + banked figure (`docs/figures/steel-casting.png`: Scheil profile + Chvorinov +
>   the centerline band) + gallery card (new **"Casting (front-end)"** section) + both READMEs. **Notebook
>   & app deferred** (same as F1/spine). The "frozen engine" framing is dropped from this build's docs (a
>   monorepo artifact; the solver is used as a plain library — Slice 2 only).

> **As built — 2026-06-13 (F4 Slice 2).** `steel/solidification.py` (+ `demo_solidification.py`,
> `plots.solidification_figure`, `tests/test_solidification.py` 14 + `test_demo_solidification.py` 5).
> **Second solver-bearing front-end physics, NO engine touch, NO ADR** — latent heat rides the engine's
> *already-unfrozen* nonlinear `D(u)` path (ADR 0004); this plan is the record.
> - **The formulation — the enthalpy method (the one trap avoided).** The advisor confirmed the tempting
>   shortcut is **physically wrong**: folding an apparent capacity into a *temperature-mode* diffusivity
>   `D(T)=k/(ρc_app(T))` does not reduce cleanly when `c_app` varies in space (a spurious `k∂ₓT·∂ₓ(1/ρc_app)`
>   term; the engine would conserve `∫T dx`, not enthalpy). The conservation-correct route is **state =
>   specific enthalpy** `u=h` (the engine's heat-mode invariant *is* `∫h dx`): recast as `∂h/∂t = ∂ₓ(D(h)∂ₓh)`
>   with `D(h)=(k/ρ)dT/dh`, which drops in the mushy range → the front slows (the plateau), conserved exactly
>   (the engine caches the accepted D-field → machine-precision identity). Maps onto `D_of_u` natively.
> - **Smoothing `f_s` is numerical REGULARIZATION, not a physics claim** (advisor's framing). A lever top-hat
>   makes `D(h)` a step function → **Picard oscillates and fails**; a smooth `sin²` `f_s` makes `D(h)`
>   continuous → converges. Legitimacy is *proven by the tooth*: the Stefan front depends on latent-heat
>   **content** + `α`, not the mushy profile shape (`∫df_l=1` for any shape), so it is insensitive to `sin²`.
> - **BC = a fixed-temperature chill** (`Dirichlet`). With `u=h` the engine's `Robin` would cool toward an
>   *enthalpy*, wrong for Newton cooling → enthalpy method is `Dirichlet`/`Neumann` only (the named scope
>   edge; convective cooling is the `martemper`/`residual` idiom on `u=T`). A chill / water-cooled mold is
>   exactly `Dirichlet` and exact (`T(h)` monotone).
> - **HEADLINE TOOTH (validated, untuned): the analytic one-phase Stefan/Neumann benchmark.** The numerical
>   `f_s=0.5` front **converges to** `X=2λ√(αt)` under grid refinement: **~3 % below analytic at the demo /
>   test grid (n=144/216: `0.958→0.969`), tightening toward ~1 % under further refinement** (an in-session
>   n=800/1600 study, not committed), the ratio climbing monotonically toward 1 as Δx halves. The residual is
>   grid resolution — the `ΔT→0` sharp limit *under-resolves* on a fixed grid (the named numerical limit — do
>   **not** show convergence by narrowing ΔT) — plus, if one tracks the fully-solid *solidus* front instead,
>   a defined isotherm offset (named, not hidden). Plus **enthalpy conservation** exact to machine precision
>   (~1e-13). A broken latent coupling misses by tens of %.
> - **Directional (NOT a tooth):** the latent ON/OFF toggle slows the freeze-through ~×3 (order
>   `L/c_pΔT`; the exact multiplier is profile-shape-dependent — advisor's correction, demoting it from the
>   headline it was first pitched as). **By construction (NOT teeth):** Niyama `Ny=G/√Ṫ` (cited *form*) and
>   the last-to-freeze hot spot — the insulated centre freezes last, *the same centerline Slice 1 enriches*
>   (porosity + macro-seg, one place, two reasons); named illustrative up front (the Mushet/TE-nose
>   discipline). **Chvorinov stays scaling-only** (a metal-conduction chill is a different heat-extraction
>   regime than mold-diffusion `B`). **Notebook & app deferred** (as F1/spine/F4 Slice 1). Hot-tear and a
>   defect-feeding model remain deferred.

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
1. **F1 — Ellingham. ✅ BUILT 2026-06-12** (as-built record under §7). Cleanest
   standalone classic; cleared the triad; zero integration risk. The front end's
   "dramatic early win."
2. **`heat_state.py` — the `Heat` record + orchestrator seam. ✅ BUILT 2026-06-12**
   (as-built record under §5). The spine that lets steps compose and failures
   propagate.
3. **F4 — casting link. ✅ BUILT 2026-06-12 (Slice 1; as-built record under §7).**
   Proves the chain runs **front-to-back inside steel-sim** (Scheil microsegregation
   → centerline `Heat` → back-end divergence) — a *new-physics* phase, not the "thin
   reuse" first imagined. The latent-heat solidification map is **deferred to Slice 2**.
4. **F2 — refining. ✅ BUILT 2026-06-13 (Slice 1; as-built record under §7).** The
   middle of the chain: decarburize / deoxidize / degas. **Fills the dissolved-gas /
   inclusion fields the spine left `None`**, and the *carbon* the blow sets carries a
   **validated** propagation (over-blow → back-end soft core). Slag partition (S/P,
   desulf/dephos) is **deferred to Slice 2** (needs S/P state the `Heat` lacks).
5. **F3 — ladle + alloy trim. ✅ BUILT 2026-06-13 (Slice 1; as-built record under §7).**
   Where the grade composition is finalized — the hero-demo's off-spec input,
   **produced** (recovery shortfall) rather than hand-set. Spine-class (no new
   physics): the validated under-trim → soft-core link rides the back end, with F3's
   own off-grade window flag as the front-end early warning.
6. **`game/`.** The loop/economy/UI on a *proven verified spine* — last, by
   design, never first.

**Immediate next step.** ~~Plan only — this document.~~ **F1 (Ellingham), the
`heat_state.py` spine, F4 casting (Slice 1), F2 refining (Slice 1), and F3 ladle trim
(Slice 1) are built** (2026-06-12/13; as-built records under §7, §5, §7, §7, §7). The
**entire front-end chain is now built inside steel-sim** — ore → iron (F1), the spine
that composes steps, refine (F2), trim to grade (F3), cast (F4) — each link **composing**
through the `Heat` carrier (each phase produces the `Heat` *type* the next consumes, and
under-spec output reaches the validated back end). The links are not yet piped into a
single hot-metal → … → quench execution (F2's `from_hot_metal` takes a fully-alloyed
backbone, F3's `from_tap` starts alloy-lean — composed by type, not chained in one run).
What remains
is a **Slice 2** (F2 slag partition / S/P state, F4 latent-heat map + defects) or the
deferred state extensions (P/S on `Steel`) — then **`game/` last**, on the proven spine.

---

## 14. Historical impure steel — the pedagogical surface & the failure-propagation grounding (folded 2026-06-12, plan-only)

> **Why this lives here, in the game/front-end plan.** "Bad steel" is mostly
> game-domain (impurity → defect → failure), but it carries a genuine
> *pedagogical* surface **and** it grounds the §6 failure-propagation catalogue
> in **cited archaeometallurgy data** — published measurements on genuinely
> impure historical iron (P, S, slag inclusions). Recorded here as a research
> fold, **not** a build; the *back-end* engine candidates it implies are pointed
> to from `steel-production.md` §11. "Just plan, don't build yet" stands.

> **BUILT ✓ 2026-06-13 — the impurity *consequences* are now closed (themes A + B).** The two
> consequences F2 Slice 2 set as inert state are wired to a downstream verdict, as **two distinct
> classes** (the load-bearing honesty):
> - **Phosphorus → cold-shortness = a PROPAGATION.** `grain.py` §3 gained a `P_pct` term in *both*
>   Pickering laws; `heat_state.cold_short_check` normalizes a `Heat` and flags **cold-short** when the
>   P-aware DBTT lands above the service temperature. **Teeth (the strength axis):** Thiele–Hošek
>   **+237 MPa/at% P** — now **PDF-verified** (eq. ΔR_p0.2 = G·ε·X_c/100, G = 83 000 MPa, ε = 0.286 from
>   Fe/P radii), not snippet-level — and the teeth are *cross-source coherence*: ≈427 MPa/wt% (after the
>   ×1.803 at%→wt% conversion, the registered unit trap) sits inside Total Materia's independent
>   365–620 MPa/wt% bracket, and the hardness increment 119.8 vs lit 123–125 vs theoretical 127 HV/wt%
>   coheres within ~6 %. **The P→DBTT slope stays FLAGGED representative** (`grain.ITT_K_P` ≈ 500 °C/wt%,
>   the §14.1 unpinned band) — clean relations use grain-boundary *segregation* at%, not bulk wt%; the
>   strength term carries the teeth, the slope does not.
> - **Sulfur → red-shortness = a NEW consumer with NO strict tooth.** New module `hot_work.py` (`hot_work`
>   orchestrator → **red-short** flag): free sulfur (the slag-reused `manganese_sulfide` balance) forms a
>   Fe–FeS grain-boundary film above the eutectic when forged. This slice is **cited constants +
>   by-construction**, the same shape slag.py labels "by construction (NOT teeth)" — it carries no
>   falsifiable benchmark, and that is fine (a thin, honest consumer). The Mn:S ≥ 1.71 threshold reproducing
>   *Mushet's manganese* is the **historical-coherence anchor (a RESULT, by-construction — 1.71 = M_Mn/M_S
>   cannot come out wrong)**, NOT the analog of slag.py's acid/basic `L_P` endpoint (that emerges from a
>   Healy correlation that could have failed history; this cannot). The transition temperatures are
>   di-crosschecked, pinned **inputs** (verification ≠ tooth): Fe–FeS **eutectic 988 °C** (the GB-film onset,
>   confirmed *distinct* from FeS melting ~1192 °C — the advisor's trap), MnS **1610 °C**. The temperature
>   *ordering* is mechanism narrative, **never asserted as a tooth** (vacuous-benchmark trap avoided).
>
> **So the whole build adds exactly ONE genuine tooth: the P-strength cross-source coherence (above).**
> Everything else is cited / flagged / by-construction — the P→DBTT slope flagged representative, the
> cold-short verdict riding that flagged slope (the demo's +96 °C is illustrative), and the entire S slice
> cited-constants + by-construction. The *value* of the build is the closed consequence + the §5b foil +
> the historical arc, not a second benchmark.
>
> **The split** (`test_phosphorus_sulfur_inert_in_the_hardenability_back_end`, renamed): P/S now propagate
> on **exactly one path each** — consumed in `cold_short_check` / `hot_work`, still **inert in
> `heat_treat`** (hardenability/hardness/martensite read C/Si/Mn/Ni/Cr/Mo only). **Demo + figure +
> gallery card:** `demo_impurity_window` — the *same* high-P, sulfurous pig iron made cold-short **and**
> red-short by acid Bessemer / no manganese, and sound by basic + Mushet + ladle desulf; four panels
> (P→DBTT with the yield foil; free-S vs Mn:S Mushet threshold; the signed yield–DBTT foil; the closing
> workable window). Suite **668 green / 2 skipped**, no engine touch, no ADR (additive `P_pct` + two new
> orchestrators, not a semantics change). **Named deferrals:** MnS inclusion fracture-anisotropy /
> transverse-toughness debit, the "good-impurity" free-machining use of S (resulfurized 11xx), and the
> kinetic hot-ductility *trough shape*. (Temper embrittlement — the martensitic-P deferral named here — is
> now BUILT; see the next banner.) Theme C (purity ramp), D (inverse hardness) and E (Scheil ghost lines)
> remain as written below.

> **BUILT ✓ 2026-06-13 — temper embrittlement closes phosphorus' MARTENSITIC path (theme A, the other half).**
> `cold_short_check` closed the ferritic/normalized P path (DBTT); `temper_embrittlement.py` closes the
> quench-and-tempered one. Reversible, alloy-driven: P co-segregates with Ni/Cr to prior-austenite grain
> boundaries on slow cooling through **375–575 °C** → intergranular fracture; **Mo (~0.5 %) is the cure**;
> **reversible** (reheat >600 °C + fast cool resets it). `temper_embrittlement_check` orchestrator → the
> **`temper-embrittled`** flag. **NO claimable tooth — the gate was run before coding and could not be pinned
> (the load-bearing discipline).** The tempting tooth — "the segregation C-curve *nose* emerges at the
> observed ~490–550 °C from cited ΔG_seg(P) + D_P(α-Fe), without tuning" — was **tested on paper before any
> code**: a tractable Langmuir–McLean model with the cited ΔG_seg = −34469 + 22.9·T J/mol (Yang–Chen/Erhart–
> Grabke) and cited D_P runs ~100× faster than the source's own kinetic anchor (450 °C → ~10 h) and gives no
> single time-stable nose. The 100× is the tell, not the verdict: the real kinetics add an Fe₃P-cluster step
> the model omits, and *correcting* for the missing slowness pushes the peak **up** from ~410 °C **toward**
> the observed window — the model is **underdetermined, not wrong-placed**, and pinning it faithfully is out
> of scope. So **no claimable tooth**, and the segregation model was **not built to manufacture one.** This
> slice is **cited constants + by-construction** (the J-factor `(Mn+Si)(P+Sn)·10⁴`, Watanabe, is regression-
> fit → "high J ⇒ susceptible" cannot miss; the danger window / ≥600 °C reset / 0.5 % Mo are cited inputs) —
> symmetric with the S/red-short slice, no benchmark. The teaching beat (a coherence note, not a tooth): in
> the registry only the dirty Ni-Cr victim (J ≈ 225) is susceptible; 1080/1045/8620/4140 (J ≈ 108–138) are
> safe **by low J**, *not* by Mo — 4140/8620 carry only ~0.2 % Mo, below the 0.5 % threshold, so the model
> never marks them Mo-protected. Mo is the cited cure, demonstrated on the J ≈ 225 victim. **Demo + figure +
> gallery card:** `demo_temper_embrittlement` — one dirty Ni-Cr forging, four
> levers (fast cool / Mo / clean heat / reheat) each save it; the reversibility cycle. Suite **685 green /
> 2 skipped** (+17), no engine touch, no ADR. **Deferrals:** absolute ΔFATT (scattered), the full Guttmann
> co-segregation / Fe₃P-cluster C-curve. (The irreversible *tempered-martensite* embrittlement — the
> 260–370 °C cementite-film one, a different mechanism — is now BUILT; see the next banner.) **Phosphorus'
> coverage is now complete** (ferritic cold-short + martensitic temper-embrittlement).

> **BUILT ✓ 2026-06-14 — tempered-martensite embrittlement closes the OTHER tempering-axis trough (the
> irreversible one).** Reversible temper embrittlement closed phosphorus' *segregation* path; this closes the
> *microstructural* one — the trough `steel-production.md` §11 named as the back-end `toughness_index` ceiling
> but never modelled. `tempered_martensite_embrittlement.py` → the **`tempered-martensite-embrittled`** flag.
> Tempering as-quenched martensite in **260–370 °C** precipitates cementite as **films** along the interlath /
> prior-austenite boundaries (Horn–Ritchie: fed by interlath retained-austenite decomposition) and toughness
> troughs. The slice is the **foil** that completes the pair, opposite on every axis: TME is **carbon-driven**
> (not impurity — a *clean* medium-carbon steel still embrittles, the headline distinction), **microstructural**
> (not equilibrium segregation), and **irreversible** — modelled as a **one-way verdict keyed on the *peak*
> temper reached** (temper 300 → embrittled, temper 450 → recovered, re-enter 300 → *stays tough*, the direct
> foil to reversible TE's re-embrittling cycle). **NO claimable tooth — the gate was run before coding (the
> discipline, symmetric with reversible TE):** the tempting tooth — "the 260–370 °C trough *emerges* from
> ε→cementite / interlath-RA kinetics without tuning" — fails the same way the reversible-TE nose did (the repo
> carries no stage-III carbide thermodynamics → the trough onset is underdetermined here), so **no carbide model
> was built to manufacture one**. The trough window, the ~400 °C recovery, and the cementite-film mechanism are
> **cited inputs**; the carbon gate (`MIN_CARBON_FOR_TME`) and the verdict rule are **by construction**. **The
> faithful part is architecture, not a tooth:** the check runs the **same frozen back-end quench** the spine uses
> (`sweep.evaluate`) and gates on its **martensite fraction**, so the verdict composes with hardenability (a
> soft-core section is immune — no tempered martensite to embrittle). **Two advisor catches, both durable:** (1)
> the irreversibility I first stated **backwards** (I had the >600 °C reheat *failing* to clear TME and
> re-austenitization *clearing* it — the reverse: the reheat is above recovery so it *relieves* TME, and
> re-austenitizing *restores* susceptibility; the genuine distinction is the **cycling toggle**, not a failed
> reset); (2) the RA-as-severity-driver **inverted trap** — *bulk* retained austenite ranks high-carbon
> *plate*-martensite (eutectoid 1080) worst, where the interlath-film mechanism does not apply, so RA is cited as
> the *mechanism* only and **carbon drives the gate** (8620 at 0.20 %C confirms the low-carbon exemption even when
> fully hardened — the discriminating check, run before committing). **Demo + figure + gallery card:**
> `demo_tempered_martensite_embrittlement` — the trough on the temper axis, the two gates (carbon +
> hardenability), the irreversibility cycle, and the reversible↔irreversible contrast. Suite **742 green / 2
> skipped** (+20), no engine touch, no ADR. **Deferrals:** the absolute trough depth (no Charpy-J — the back-end
> ceiling stands), the P-aggravation magnitude, and the explicit ε→Fe₃C carbide sequence.

**The reframe that makes it useful.** The originally-named tramp axes
(hardenability/Jominy, CCT kinetics, residual stress) are the *weakest* for our
verified engines. A two-turn scan of the archaeometallurgy literature showed the
measured data actually clusters on **ferritic bloomery / phosphoric / wrought
iron** — i.e. the **toughness, embrittlement, and inclusion-cracking** axes,
exactly where tramps bite and exactly the failure-propagation payoff. The
history *corroborates* the verified/plausible split rather than overturning it.

### 14.1 What "bad steel" teaches about metallurgy

- **A — Phosphorus is the signed-impurity *foil* to grain refinement (§5b).**
  The single best teaching beat, and it is *repo-native*: back-end §5b already
  teaches that grain refinement is the **lone** lever that raises strength **and**
  improves toughness, because it acts on **one** variable (boundary area) that
  helps both. Phosphorus is the clean inverse — strength **↑** by solid-solution
  lattice strengthening, toughness **↓** by grain-boundary *segregation
  chemistry* — **two different mechanisms pulling opposite ways.** That contrast
  is *why* refinement is special, and historical phosphoric iron (bog-ore,
  0.1–0.7 wt% P, used deliberately because it was hard) is the cleanest
  illustration. **The two axes are NOT equally pinned (the load-bearing honesty):**
  - *Strength:* one clean cited number — **+237 MPa proof strength per 1 at% P**
    (Thiele–Hošek; ferrite ≈142 HV). Triad-candidate (a property correlation,
    same class as Maynier/Pickering).
  - *Toughness:* a strong, well-attested effect but an **unpinned slope** —
    published ≈ **+40 to +70 °C of DBTT per 0.1 wt% P** (7 °C/0.01% extrapolates
    to 70; another source says 40 — ~1.75× apart). **Real effect, NOT a
    calibrated coefficient.** (Symmetry with the prior turn: then "don't let the
    strengthening number masquerade as the DBTT term"; now "don't let *having* a
    DBTT number imply it's calibrated.")
  - *Unit-basis trap (before comparing or pinning either number):* the strength
    number is quoted **per at% P**, the toughness slope **per wt% P** — and
    **1 at% P ≈ 0.56 wt% P**, so the two are ~5.6× apart in their P basis.
    Convert to a common basis first; their proximity above is *not*
    comparability.

- **B — Red-short vs cold-short = a *closing* working-temperature window** (echoes
  the window-thinking already in back-end §17 martempering, Mₛ < T_bath < Bs).
  **Sulfur → red-shortness:** FeS melts ~988 °C, wets grain boundaries, the
  piece hot-tears → pushes the hot ceiling **down**. **Phosphorus →
  cold-shortness:** GB embrittlement raises DBTT → pushes the cold floor **up**.
  Clean steel = wide forging window; bad steel = the window closes from both
  ends. **Historical fix (a history-of-technology beat):** add Mn so S forms
  benign higher-melting MnS not FeS — target **Mn:S ≳ 2** — which *is* Mushet's
  manganese addition that made the **Bessemer** process work. The stoichiometry
  S + Mn → MnS is **conservation-clean** → the strongest *new* triad candidate of
  the set.

- **C — The metallurgy timeline is a purity-control ramp = the motivation for F2.**
  Bloomery (high P) → Bessemer (acid: can't remove P, retains embrittling N) →
  **Thomas basic lining** (removes P) → BOF (removes N) → ladle metallurgy
  (removes S). Each generation conquers one tramp — and that arc **is the
  L_P-vs-basicity slag-partition curve F2 (§7) is planned to compute.** "Why does
  basicity matter?" answers as "because acid Bessemer made rails that cracked from
  phosphorus." History → the front-end engine's reason to exist.

### 14.2 What archaeometallurgy's *methods* teach (the bridge to the archaeology framing)

Both **reuse engines the repo already has** — pedagogically lovely, *not* new
physics:

- **D — Hardness as an *inverse* proxy.** Maynier/Jominy run hardness *forward*
  (composition → HV). Thiele runs it *backward* — measure an artifact's hardness,
  back out its P content. The teaching inversion ("given a number on an ancient
  blade, what compositions are consistent?") is the existing forward engine run
  in reverse.
- **E — Scheil → P banding → ghost lines → provenance.** The **existing** Scheil
  microsegregation (F4) produces P banding (low solubility → micro-segregates);
  Stead's/Klemm etchant reveals it as "ghost lines"; archaeologists read those to
  fingerprint provenance. One built engine → a metallography phenomenon → a real
  archaeological method, zero new physics.

### 14.3 The triad-readiness gradient (depth ≠ overselling)

| Theme | Pedagogical value | Triad status |
|---|---|---|
| A-strength — P solid-solution strengthening | High (the §5b foil) | **Cleanest new clearer** — property correlation, single cited number |
| B-Mn:S — S → MnS stoichiometry | High (+ Mushet/Bessemer history free) | **Passes the conservation leg cleanly** |
| A-toughness — P → DBTT slope | High | **Real effect, slope unpinned** — not calibrated |
| C — history / L_P-vs-basicity | High (motivates F2) | = the planned F2 engine |
| D, E — inverse hardness, Scheil ghost lines | High (the archaeology bridge) | **Reuse existing engines** — not new physics |

### 14.4 Where it would surface (placement, not a build)

The natural pedagogy home is a notebook cell **adjacent to back-end §5b** (the
foil only lands in context), an `app.py` "P slider → yield ↑, DBTT ↑, *workable
cold?* verdict flips" what-if, and a gallery figure. Game-side it slots into the
§6 catalogue: **S under-desulfurized → MnS/FeS → hot-tear** and **P off-spec →
cold-short / quench-crack-via-inclusion** (the inclusion is the stress
concentrator that turns §18's sub-critical residual field into a crack — the
fracture-side coupling).

### 14.5 Side note — future research (only if a build is ever authorized)

The one piece that would need *new* sourcing before it could clear the triad is
the **P → DBTT slope** (unpinned above). Candidate cited benchmarks already
located, for whoever picks this up:
- **Thiele–Hošek 2015** — P-from-hardness; the +237 MPa/at%, 142 HV numbers.
  Open-access PDF `acta.uni-obuda.hu/Thiele_Hosek_60.pdf`. **VERIFIED against the
  PDF and PINNED 2026-06-13** (the §14.0 build): eq. ΔR_p0.2 = G·ε·X_c/100,
  G = 83 000 MPa, ε = 0.286, "237 MPa for 1 at% P"; hardness increment 119.8
  HV/wt% (eq. 4) — the strength axis now carries teeth. **Unit-basis trap
  (handled at the function boundary):** this strength number is **per at% P**, the
  §14.1 DBTT slope is **per wt% P** (1 at% P ≈ 0.56 wt% P) — converted before use.
  *The P→DBTT slope itself remains the unpinned piece (flagged representative, not
  pinned with teeth) — clean relations use GB-segregation at%, not bulk wt%.*
- **Medieval-bloomery Charpy + tensile vs. a modern S235JRG2 control** — the most
  triad-relevant hit (measured properties on genuinely impure steel **with a
  modern reference**): `bucavasgyuro.net/.../2015PP_Mech_props.pdf` (PDF did not
  parse on fetch — needs a mirror / manual read for exact figures).
- **"Iron–phosphorus–carbon system"** (Stewart / Charles / Wallach) —
  controlled-lab composition → property data + the Stead's/ghost-line
  metallography for theme E.
- **The inverse "good impurity" caveat (wootz / Damascus):** trace **V > ~0.03%**
  and **Mo < ~100 ppm** are *necessary-good* impurities (carbide banding) — so
  "bad steel" is really "**off-spec composition**," signed either way. Keep this
  as the honest framing nuance.

**Status: folded as a research record, assess-only.** No engine, no notebook
cell, no F-phase started. Sources are listed in the session and in the
[[historical-impurity-pedagogy]] memory.

---

## 15. Historical & modern production *methods* as paths through the built chain (folded 2026-06-13, plan-only)

> **Why this lives here.** A natural question for the §8 game — *"can it include
> different historical and modern methods of steelmaking?"* — has a sharp answer
> that falls straight out of the §4 scope ceiling, so it is recorded here as a
> **feasibility assessment, not a build.** The load-bearing reframe: **a
> production method is a particular *path* through the equilibrium endpoints
> F1–F4 already compute** — so most methods are a `game/` *preset / recipe over
> built engines*, not new physics. Companion to §14 (which supplies the
> purity-control-ramp history this section leans on). "Just plan, don't build
> yet" stands.

### 15.1 The reframe — and the one distinction that splits "method"

Because §4 deliberately built **equilibrium endpoints + lumped rates** (never
transport-resolved kinetics), the methods differ along axes the engines already
parametrize: reduction route (F1 Ellingham C/CO crossover), carbon endpoint
(F2 C–O product), deox/gas state (F2), alloy trim (F3), solidification (F4). A
"method" is then a *sequence of states*, which the §8 game layer can orchestrate
without touching a constant — exactly what the firewall (`game/` orchestrates,
never reimplements physics) is built for.

But the word "method" blurs two things that must stay separate:

- **Chemical outcome** — the `Heat` state a method *yields*. **Built**, producible
  as a preset over F1–F4 (and reaching the validated back end through the §5
  carrier, so a bad method fires the §6 flags on its own).
- **Process dynamics** — what makes a method *feel* different in play (blow time,
  fuel, the solid-vs-liquid regime, productivity / yield, spark-and-flame cues).
  This is the **§4 tar pit** (transport-resolved kinetics) → **game-flavor,
  labeled "plausible, not validated."** Not a gap to close; it is the doctrine
  working.

The honest one-liner: **the *chemistry* of nearly every method is already a path
through built engines; the *process feel* is game-layer by design.**

### 15.2 The method → engine map

| Method | Era | Distinguishing physics | Status in repo |
|---|---|---|---|
| **Bloomery** (direct / solid-state) | ancient | reduce *below* the C/CO crossover; stays solid; low-C; slag-laden | F1 crossover **built** (746 °C); "no-decarb + slag retention" = preset + flavor |
| **Blast furnace → pig iron** | medieval+ | full reduction to liquid ~4 %C iron | F1 **built** |
| **Finery / puddling** | early-modern | decarburize pig iron by oxidation | F2 C–O endpoint **built** |
| **Cementation / blister** | 1600s | solid-state carburization of wrought bars | **`carburize.py` BUILT** — essentially free |
| **Crucible (Huntsman)** | 1740s | melt + homogenize + slag flotation | homogenization = preset (composition averaging) |
| **Wootz / Damascus** | ancient | trace V/Mo → carbide banding | **future-research gap** (§14.5) — beyond P/S |
| **Acid Bessemer** | 1856 | air-blow decarb; **can't** remove P; N pickup | F2 decarb **built**; dephos (acid L_P≈1) **built (Slice 2)**; N pickup = flavor |
| **Thomas (basic Bessemer)** | 1879 | basic slag removes P (L_P vs basicity) | **F2 Slice 2 BUILT** — basic L_P~400 vs acid ≈1, the dephos advantage |
| **Siemens–Martin open hearth** | 1860s+ | same endpoints, slower; basic P/S removal | endpoints **built**; P/S **built (Slice 2)**; time = flavor |
| **BOF** (basic oxygen) | 1950s | O₂ blow, fast, low-N, dephos | F2 **essentially models this** (benchmarks BOP 27 ppm·%C; dephos Slice 2) |
| **EAF** (electric arc) | modern | melt scrap + refine | F2 **built** (benchmarks EAF 26 ppm·%C) |
| **Ladle / secondary metallurgy** | modern | alloy trim, degas, desulf | F3 **built**; desulf **built (F2 Slice 2 — reads the kill)** |
| **Ingot / continuous casting** | modern | solidification, microsegregation | F4 Scheil + Chvorinov **built** |

The map reads as the §14.3 theme-C *purity-control ramp* in engine terms: each
historical generation conquers one tramp element, and that arc is precisely the
F2 slag-partition curve (§7) — bloomery (high P) → acid Bessemer (no dephos) →
Thomas (dephos) → BOF (low N) → ladle (desulf).

### 15.3 The three feasibility tiers

- **Tier 1 — recombine what's built (HIGH; orchestration, not physics).** Modern
  grade-steel routes (BOF/EAF → ladle → cast) and several historical ones
  (bloomery via the F1 crossover, cementation via `carburize.py`, crucible via
  homogenization, finery/puddling via F2 decarb) are expressible *now* as `game/`
  presets. F2 already benchmarks against BOP and EAF carbon–oxygen numbers, so
  those routes are **grounded**, not just plausible.
- **Tier 2 — the one gap that gates the *interesting* history (MEDIUM; bounded,
  named).** The historically pivotal distinctions — *why Thomas beat acid
  Bessemer, why ladle desulfurization mattered* — are the **P/S slag-partition**
  axis: F2 **Slice 2** (L_P / L_S vs basicity) plus **P/S state on
  `Heat`/`Steel`** (the state gap §7's F2/F3 records already flag). This is
  **already planned and triad-ready** (the Mn:S → MnS stoichiometry is
  conservation-clean, §14 theme B), not speculative. Without it the game can
  express modern *grades* but **not the purity-control ramp that is the most
  teachable history** (§14 theme C).
- **Tier 3 — the tar pit, correctly excluded (LOW → game-flavor only).** Process
  *rates and dynamics* — blow time, fuel efficiency, bloomery reduction kinetics,
  productivity — are transport-resolved kinetics (§4 wall). They live in `game/`
  as tuned-for-feel flavor, labeled plausible. Not a limitation to fix; the
  doctrine working.

### 15.4 The two genuine physics gaps (so "mostly built" stays honest)

1. **P/S slag partition — the load-bearing one. ✓ BUILT 2026-06-13 (F2 Slice 2,
   `steel/slag.py`).** Gated Thomas vs acid Bessemer, open-hearth/BOF dephos, and
   ladle desulf (Tier 2) — now closed: dephosphorization (Healy L_P) and
   desulfurization (sulfide-capacity L_S) on the `Steel.P`/`Steel.S` state
   extension, with the opposite-oxygen coupling reading the kill state. It was the
   single highest-leverage front-end build for *historical* coverage. (Benchmarked
   physics, not a propagation — P/S inert downstream; consequence deferred.)
2. **Wootz / Damascus carbide banding — beyond P/S.** The signature V/Mo-driven
   carbide banding is **future research** (§14.5), not a recombination of existing
   endpoints. So not *every* experientially-distinctive method reduces to a built
   engine — this one has a real physics gap of its own.

### 15.5 Where it would surface (placement, not a build)

The game home is a **`game/` method-preset table** behind the §8 firewall: each
preset is a `Heat` *recipe* over the F1–F4 engines + the set of §6 flags it can
fire + an explicit **verified-vs-flavor** label per field (chemistry from a
cited engine = verified; dynamics tuned for feel = plausible). A method is thus a
named walk through the built chain, and a *bad* method (e.g. acid-Bessemer P
carry-through, once Tier 2 lands) propagates to the back end on its own — the §6
mechanic, no scripted failure branch. Pedagogy-side it pairs naturally with the
§14 historical surface (the timeline *is* the ramp).

**Status: folded as a feasibility assessment, plan-only.** No engine, no preset,
no `game/` package started. The verdict: **chemistry of nearly every method = a
path over built engines (Tier 1); the historically richest distinctions need one
named, scoped extension (P/S partition, Tier 2); one method (wootz) has a physics
gap beyond that; process *feel* is game-layer by design (Tier 3).**

---

## 16. The Tier-3 game-flavor layer — physics-shaped process dynamics (folded 2026-06-13, plan-only)

> **Why this lives here.** §15.3 placed *process rates and dynamics* in Tier 3 —
> correctly **excluded from the validated `steel/` engines** by the §4
> transport-kinetics wall. But "excluded from the validated engines" is **not**
> "arbitrary RNG in the game." This section records a forward-looking **design
> doctrine** for the `game/` flavor layer so its dynamics are *physics-shaped
> approximations, labeled plausible* — the user's "game, but based on physics and
> chemistry, with approximations." It is the constructive other half of "Tier-3
> exclusion is the doctrine working." Plan-only: no `game/` code, no τ-law.

### 16.1 The organizing principle — relaxation toward a validated endpoint

Every Tier-3 dynamic animates the **path** to an endpoint the F1–F4 engines
already compute. The *shape* of the path is textbook (first-order, Arrhenius,
Stokes); the *time constant* τ is feel-tuned and lives in `game/`. Three
properties keep the §8 firewall intact:

- **Endpoint in `steel/`, τ in `game/`.** The validated number (F1 crossover, F2
  C–O / Sieverts / deox, F3 trim, F4 Scheil/Chvorinov) is the *destination* and is
  never re-derived — flavor **animates** the approach, it never **recomputes** the
  physics.
- **Flavor cannot contradict a built engine** (see the per-type contract in §16.4).
- **The player's knobs become a control surface routed through validated physics.**
  Working the bellows, timing the blow, killing the heat, holding for clean steel —
  each is a knob on τ or on *when you stop*, and **stopping at the wrong moment is a
  physically-meaningful failure** that fires the §6 flags on its own. A grounded
  failure source, not a scripted branch.

### 16.2 Two trajectory archetypes (the load-bearing distinction)

A single "monotone relaxation" frame is **wrong** for the most iconic Tier-3
process. There are two shapes:

- **Type A — one-sided asymptotic approach.** State relaxes *monotonically* toward
  a floor/ceiling the engine fixes; you can only fall **short**.
  `s(t) = s∞ − (s∞ − s₀)·e^(−t/τ)`, and `t → ∞` recovers the validated endpoint
  exactly. Reduction extent, degassing (H/N → Sieverts floor), inclusion
  flotation, desulf/dephos → slag-partition equilibrium. **Failure = stop short.**
- **Type B — targeted optimum / overshoot-capable.** *No* fixed asymptote — the
  endpoint is a **target with a turning point** you can under- *or* over-shoot, and
  "knowing when to stop" is the mechanic. The **decarb blow** drives C down, then
  past the target the O₂ begins oxidizing iron → FeO in the metal (**over-blow**).
  **Deoxidation** has a genuine *minimum* in dissolved O — F2's `e_O^Al = −3.9`
  curve (Al-O minimum ≈ 0.074 %): add Al past it and dissolved O climbs again.
  **Failure = both under- and over-shoot.** The Bessemer **flame-drop** is the
  canonical in-world "you've hit it — stop now" cue.

Type B is the iconic Tier-3 dynamic (the decarb blow *is* the whole §14 theme-C
Bessemer story), so it must not be flattened into an asymptote — and timing /
overshoot failures are both richer game design and physically real.

### 16.3 The candidate-dynamics table

| Dynamic | Type | Physics shape (approx) | Player knob | Validated endpoint it rides | Stop-wrong failure | Routable today? |
|---|---|---|---|---|---|---|
| **Bloomery reduction** (extent / yield) | A | Arrhenius `k(T)` × approach; `ξ = 1 − e^(−k t)` | bellows/airflow, time, charcoal:ore | F1 crossover (reduction above 746 °C) | cold/short → ore lost to slag, low yield, low-C sponge | partial — low-C carries via §5; yield = flavor |
| **Decarb blow** (Bessemer / finery / BOF) | **B** | first-order C decay, then Fe oxidation past target | blow time, air/O₂ rate | F2 C–O product | under → high residual C (soft); **over → FeO / over-oxidized bath** | **YES — carbon → soft-core is the built, proven §6 exemplar** |
| **Deoxidation** (Al / Si kill) | **B** | dissolved-O **minimum** vs deox dose (`e_O^Al = −3.9`) | deoxidizer dose | F2 deox-curve minimum | under → O retained (porosity); over → alumina clusters | partial — O floor is F2; porosity = F4 Slice 2 |
| **Degassing** (H / N) | A | first-order → Sieverts floor; `k ∝` stir/vacuum | vacuum / stir time | F2 Sieverts gas | short → retained H → flaking risk | needs deferred state (H-flaking, F4 Slice 2) |
| **Inclusion flotation** (cleanliness) | A | Stokes `v ∝ r²Δρ/μ` → first-order clearance | quiet-hold time | F4 inclusion floor | rushed → dirty steel, inclusion stress-raisers | needs fracture coupling (§14.4) |
| **Desulf / dephos kinetics** | A | approach to slag-partition equilibrium | slag basicity, stir, time | F2 **Slice 2** `L_P`/`L_S` (Tier 2) | short → tramp carry-through | needs Tier-2 P/S state (§15.4) |
| **Thermal / fuel** (hold-feasibility) | gate¹ | lumped heat balance | fuel rate, blast temp | "bath hot enough to stay liquid / reach T?" | too cold → freeze-up, can't cast/trim | partial — couples to existing Biot / lumped-valid gates |
| **Casting / teeming speed** | A | Chvorinov time (built) vs withdrawal rate | cast speed | F4 solidification time | too fast → solidification defects | flavor (defect engine deferred, F4 Slice 2) |

¹ *Thermal/fuel is a feasibility **gate**, not a relaxation curve — it decides
whether a step can run at all, then hands off to the trajectory dynamics.*

**Not in the trajectory frame — productivity / throughput.** This is a *separate
category*: an **economy-scale anchor**, not a relaxation-toward-endpoint dynamic
(bloomery ~kg/day → crucible ~tens-of-kg/heat → BOF ~300 t / 40 min). Keep it as
flavor **anchored to historical orders of magnitude** — it grounds the §8
economy's *scale* in real proportions without pretending to be a validated rate.

### 16.4 What keeps it honest (the labeling contract)

- **Shapes textbook; constants feel-tuned.** First-order / Arrhenius / Stokes are
  real; the τ values are tuned for play, **not** benchmarked → every τ-driven
  field is labeled **plausible, not validated** (the §8 / §15.5 verified-vs-flavor
  contract).
- **Type-A endpoint-consistency:** asymptotic dynamics must be **monotone and may
  not overshoot** the validated floor/ceiling — so they can't silently contradict
  a built engine.
- **Type-B target-consistency:** these *do* turn around, but the **turning point
  itself** (the C–O target, the deox minimum) is the **validated** F2 number; only
  the over-/under-shoot *region* around it is flavor. The optimum is physics, the
  excursion is feel.
- **Nothing is promoted to `steel/`.** The §4 wall stands; this is `game/` design
  doctrine for how the flavor layer *behaves*, not transport-resolved kinetics.
- **Routability is explicit.** Only failures whose endpoint already lives in the
  validated back end propagate **today** (carbon → soft-core); the rest are tagged
  *needs deferred state* (H-flaking, inclusion fracture coupling, P/S Tier-2,
  casting defects), so the table doubles as a **build-order backlog**.

### 16.5 Why this is the doctrine *working*, not a compromise

Excluding transport kinetics from the **validated** engines does not forfeit
physical **grounding** in the game. The relaxation-toward-endpoint structure means
the game's most hands-on moments — work the bellows, time the blow, kill the heat,
hold for clean steel — are physics-shaped and consequence-bearing **without a
single new triad claim**: endpoints stay validated, the paths to them stay
plausible-and-labeled, and the player's mistakes propagate through the built
chain via §6. That is the firewall paying off.

**Status: folded as a forward-looking design sketch, plan-only.** No `game/`
package, no τ-law, no engine. The doctrine: **Tier-3 dynamics = physics-shaped
relaxation toward (Type A) — or a targeted optimum at (Type B: decarb, deox) — a
validated F1–F4 endpoint; shapes textbook, constants plausible-labeled, firewall
intact; stop-wrong failures route through §6 where the back-end state already
exists (carbon today; H / inclusion / P-S / casting-defect as their states land).**
