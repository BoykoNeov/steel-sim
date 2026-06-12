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
   **← next: item 4 (F2/F3), or Slice 2 (latent-heat map + defects).**
4. **F2 / F3 — refining + ladle.** Fill in the middle of the chain.
5. **`game/`.** The loop/economy/UI on a *proven verified spine* — last, by
   design, never first.

**Immediate next step.** ~~Plan only — this document.~~ **F1 (Ellingham), the
`heat_state.py` spine, and F4 casting (Slice 1) are built** (2026-06-12; as-built
records under §7, §5, §7). The chain now **runs front-to-back inside steel-sim** (cast
billet → segregated centerline `Heat` → back-end divergence). The next slice is the
**middle of the chain (F2/F3 — refining + ladle)**, or **F4 Slice 2** (the latent-heat
solidification map + defect criteria) — then `game/` last.

---

## 14. Historical impure steel — the pedagogical surface & the failure-propagation grounding (folded 2026-06-12, plan-only)

> **Why this lives here, in the game/front-end plan.** "Bad steel" is mostly
> game-domain (impurity → defect → failure), but it carries a genuine
> *pedagogical* surface **and** it grounds the §6 failure-propagation catalogue
> in **cited archaeometallurgy data** — published measurements on genuinely
> impure historical iron (P, S, slag inclusions). Recorded here as a research
> fold, **not** a build; the *back-end* engine candidates it implies are pointed
> to from `steel-production.md` §11. "Just plan, don't build yet" stands.

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
  Open-access PDF `acta.uni-obuda.hu/Thiele_Hosek_60.pdf`. *Numbers are
  search-snippet level — verify against the PDF before pinning any constant.*
  **Unit-basis trap:** this strength number is **per at% P**, the §14.1 DBTT
  slope is **per wt% P** (1 at% P ≈ 0.56 wt% P) — convert before comparing or
  pinning.
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
