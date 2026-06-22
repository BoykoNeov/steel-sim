# The `game/` build plan — the playable spine on the proven chain

> **Status: Slice 0 BUILT ✓ (2026-06-21).** The `game/` package is stood up —
> `state.py` / `knobs.py` / `teach.py` (logic) + `figures.py` + `app_game.py` +
> `demo_game.py` + `tests/` (the four structural checks), banked figure
> `steel-game-blow.png`, a gallery *Game* card, and the root + `steel/` READMEs
> wired. The one engine touch the slice needed was promoting `demo_capstone`'s
> demo-local casting re-base to the public `casting.cast_billet_onto` seam (its
> documented promotion trigger — done as a behaviour-preserving refactor, the
> capstone's `print_summary` output byte-identical).
>
> **Status: Slice 1 BUILT ✓ (2026-06-21) — the gauntlet.** Scope was widened from the
> plan's original "second knob (deox kill)" to **every stage a decision** (the user's
> call): a frozen `Recipe` (one knob per stage, defaults = the capstone reference) +
> `choices.py` (tested option tables) + `postmortem.py` (the sealed consequence
> engines run on the finished part, never mutating the spine, so the golden run stays
> exact). **Seven knobs are genuinely losable** (probed empirically, one losability
> test each — the advisor's acceptance bar); **casting is an honest no-loss
> pass-through** (no pass/fail lever on 4140 — said so, not faked); deox became the
> **deoxidizer-choice** knob (Al ≫ Si > Mn) and desulf is losable via the **cleanliness
> spec** (the trim's Mn masks red-short — the masking became the lesson).
>
> **Status: Slice 2 BUILT ✓ (2026-06-22) — the era tech tree.** The §15.2 method→engine
> map made playable: a `presets.py` table of **methods** (acid Bessemer → Thomas → basic
> open hearth → BOF → modern EAF + ladle) and **ores** (a phosphoric and a clean charge),
> each method a *constrained walk* through the same validated F1–F4 engines. A `Method`
> fixes the era's refining chemistry — which dephosphorization slag runs (acid `L_P≈1` vs
> basic `L_P` in the hundreds, read live from `slag.phosphorus_partition`) and whether the
> era has the secondary-metallurgy stages (reducing-ladle desulf, vacuum degas) — and the
> **purity-control ramp** is the difficulty curve: a phosphoric ore is cold-short in acid
> Bessemer, phosphorus-fixed-but-dirty in Thomas, sound only in the modern ladle era; a
> clean ore is sound even in acid Bessemer. The acceptance bar (the Slice-2 analogue of
> losability) is **the ramp** — each era conquers exactly the tramp the history says it did,
> pinned by `test_game_methods.py`, with the modern reference still reproducing the golden
> run exactly. The two era-gated tramps are **P and S** (the benchmarked slag physics);
> **hydrogen is deliberately not era-gated** (the model carries no charge H, so "no vacuum"
> makes no flaking claim), and the kill / speed / scale / nitrogen / the Al & vacuum
> anachronism are **flavor** (labelled). The basic open hearth and BOF share Thomas'
> chemistry in this model — *said and pinned by a test*; the **bloomery** is the named era-0
> floor, not a played 4140 route (a different product, deferred). **No engine touch, no
> ADR** (`presets.py` + the `state.py`/`choices.py`/`teach.py` wiring + `demo_game_methods.py`
> + the purity-ramp figure + 35 new tests, 95 game). Slice 3 remains plan-only.
> The rest of this document is the build plan that **promotes** the game
> *doctrine* —
> already written in depth in `steel-making.md` **§8** (the firewall), **§15**
> (methods as paths through the built engines), and **§16** (the Tier-3
> physics-shaped dynamics) — into a **sliced, testable build order**. It does
> **not** re-derive that doctrine: it **cross-references** it and adds the two
> things those sections leave open — the **stateful interaction surface** and the
> **slice ladder** — plus the user's new first-class requirement, an opt-in
> **educational mode**.
>
> **Why now.** Both §15.4 front-end physics gaps (P/S slag partition; wootz V/Mo
> banding) are **built**, and the **B2 full-chain capstone** (`demo_capstone.py`,
> 2026-06-21) already threads **one `Heat` ore → billet → part** with a
> reference/foil contrast on a **single** knob (the F2 blow endpoint). So there is
> **no physics left to invent** for the game — it is pure orchestration + UX on a
> spine that is already benchmarked end to end. This is exactly the condition
> `steel-making.md` §13 set for building `game/` **last**: *on a proven verified
> spine, never first.* That condition is now met.

---

## 1. What this plan is — and what it deliberately is not

- **It IS** the build order for a `game/` package: the slices, their banked
  artifacts, their **structural** tests, their scope ceilings, and the one
  genuinely new design surface (stateful, multi-turn play).
- **It is NOT** a restatement of the doctrine. The firewall rule, the
  method→engine map, the Type-A/Type-B trajectory archetypes, and the
  verified-vs-flavor labeling contract live in `steel-making.md` §8/§15/§16 and
  are **load-bearing references here, not copies** (two copies would drift). When
  this plan says "the firewall" it means §8; "the method map," §15.2; "Type B,"
  §16.2.
- **It IS** honest that `game/` is the one package in this repo that clears **no
  validation triad** — see §2. Its discipline is structural, the same class as
  the `heat_state` spine, F3 ladle trim, and the B2 capstone.

---

## 2. The honesty posture — `game/` clears no physics triad (and must not pretend to)

Every `steel/` engine earns its place by clearing the validation triad
(analytical limit + conservation law + published benchmark). **`game/` cannot and
must not** — it computes no new material behaviour. Its checks are **structural**,
exactly as the spine's and the capstone's are (`heat_state`, `demo_capstone`):

1. **Firewall guard** — `game/` imports only the **public** engine surfaces and
   defines **no physics constant**; every number with a citation lives in
   `steel/` or `engines/`. (Mirrors the `app.py` layering guard, §8.)
2. **Endpoint-consistency** — every flavor τ-dynamic (§16) **relaxes toward a
   validated F1–F4 endpoint** and may not overshoot or contradict it (Type-A
   monotone to the floor/ceiling; Type-B turns around a validated optimum — the
   *optimum* is physics, only the excursion is feel).
3. **Label-correctness** — every field the UI shows is tagged **verified**
   (engine number + citation) or **flavor** (feel-tuned, "plausible, not
   validated"), and a test asserts the tag matches the source.
4. **Golden-run determinism** — a scripted play-through (the capstone's
   reference + foil endpoints) produces the **same** verdicts the sealed engines
   already produce: the reference through-hardens, the over-blow soft-cores. The
   game adds no scripted "you failed" branch — the failure is the back-end
   martensite fraction crossing the spec line (§6), reached through play.

> The claim on the box (the §9 one-liner, verbatim): *"Every link is individually
> grounded in cited physics; the chain is a physically-consistent composition,
> not a validated whole."* That sentence **is** the boundary between the verified
> library and the game.

---

## 3. The new surface — stateful, multi-turn play (the load-bearing new design)

The existing apps (`app.py`, `app_making.py`, `app_consequences.py`) are
**stateless what-if panels**: sliders in → readout out, nothing persists between
actions. A game is **stateful and multi-step** — a live `Heat` evolving across
turns. This is a genuinely new interaction surface with **no analog in the repo**,
so the plan specifies it rather than assuming it.

### 3.1 Session-state schema (what persists between reruns)

Streamlit reruns the script top-to-bottom on every interaction, so all game state
lives in `st.session_state`:

| Key | Type | Role |
|---|---|---|
| `heat` | `Heat` | the live heat — the **current** node of an immutable, append-only chain |
| `stage` | `int`/enum | the stage cursor (which step the player is about to run) |
| `method` | preset id | the chosen route (Slice 0: one preset; Slice 2+: the §15.2 map) |
| `educational` | `bool` | the opt-in education toggle, chosen at start (§5) |
| `score` / `verdict` | scalars/flags | running economy + the §6 flags fired so far |

### 3.2 Turn structure (clean, because `Heat` is immutable)

`Heat` is a **frozen, append-only** dataclass (every orchestrator step returns a
*new* `Heat` with one `ProcessStep` appended — `heat_state` §5). So **each player
action = run one sealed stage on `st.session_state.heat`, get a new `Heat`, write
it back.** The provenance trail is the history list on that `Heat` — the game's
post-mortem comes free, already built. No new history machinery; the game *drives*
the spine's existing one. A "restart" is just resetting `session_state.heat` to
the chosen origin.

### 3.3 The Type-B knob, reframed honestly (advisor catch)

§16.2's iconic dynamic is the **decarb blow** — a Type-B *targeted optimum* you
can over- or under-shoot. The vision's "Bessemer flame-drop, stop NOW" is a
**reflex** mechanic, and **Streamlit reruns do reflex timing badly.** The
idiomatic, honest version is **value-selection on the τ-curve**:

- The player sets the **blow endpoint** with a slider (carbon target), not a
  reaction test.
- The curve is drawn: carbon falling first-order toward the target, then —
  **past** the validated C–O target — dissolved oxygen / FeO **climbing again**
  (the over-blow region). The "flame drop" becomes a **position readout** ("you
  are past the optimum — FeO climbing, bath over-oxidized"), not a clock.
- The **turning point is the validated F2 number** (`refining.carbon_oxygen_product`);
  only the over-/under-shoot *region* around it is flavor (§16.4).

**Real-time / reflex timing is named as needing a different surface** (a canvas /
non-Streamlit front end) and is **deferred** — the plan does not promise a
minigame the tech can't deliver.

---

## 4. The firewall (= §8) and its guard test

The rule is §8 verbatim: `game/` may **orchestrate** engines and own the loop,
economy, score, RNG, and UI; it may **never reimplement physics.** The
deliverable that enforces it is a **guard test** (mirrors `app.py`'s layering
guard): `game/` imports only public engine surfaces; physics constants stay in the
verified packages; the only `import streamlit` lives in the paper-thin `main()`.

**Three-layer discipline (the `app.py`/`app_making.py` idiom, §ADR-0002), which
also makes the game testable:**

1. **Compute/logic helpers** — τ-curves, state transitions, verdicts,
   educational-content selection, score. Plain functions, **no** streamlit/matplotlib
   import, **always-green** unit tests. *All game logic lives here.*
2. **Figure builders** — thin wrappers over the existing `demo_*.compute()`
   pipelines + `steel.plots`, matplotlib imported lazily. The game invents **no
   figure of its own**.
3. **`main()`** — the **only** place `import streamlit` lives; paper-thin, every
   value computed/formatted by a tested helper above.

The **golden-run test drives the helpers, not the UI.**

---

## 5. Educational mode (the user's first-class requirement)

**At the start, the player chooses optional additional guides and information —
an opt-in "educational mode" with more help, tips, and info.** It is a
**first-class requirement from Slice 0**: the startup toggle exists in v0. The
*rich content* phases in (so we learn whether the loop is fun before investing in
a content system).

### 5.1 Scope — info-overlay, NOT a difficulty axis (decided, to stop creep)

Educational mode is **purely an information overlay**: it surfaces *more*
explanation; it does **not** change the physics, the difficulty, the available
knobs, or auto-pilot hard stages. (A separate *difficulty / assist* axis —
auto-running hard stages for beginners — is a **distinct, deferred** idea, named
here only so the two don't blur.) The base game is fully playable with the
overlay **off**; nothing gates progress on reading.

### 5.2 The three tiers (phased across slices)

| Tier | What it surfaces | Lands in |
|---|---|---|
| **Why-cards** | per-knob "what this step does / what over- and under-shoot mean," the validated target named | **Slice 0** (the one knob) |
| **Physics-shape explainer** | the Type-A asymptote vs Type-B optimum (§16.2), the curve annotated; the verified-vs-flavor chip explained | Slice 1 |
| **Cited post-mortem** | the provenance trail deep-dive with the **source citation** per verified number + "learn more" links into `making.ipynb` / the gallery / the relevant `demo_*` | Slice 2 |

### 5.3 The educational-mode firewall line (sharpened — advisor)

Educational **prose may live in `game/`** (text is content, not physics). But two
rules keep it from becoming a backdoor for un-sourced claims:

1. **Every number it quotes is read LIVE from the engine at runtime — never
   hardcoded.** (The why-card says "the C–O target here is *{value from
   `refining.carbon_oxygen_product` at the current state}*," not a baked-in
   string.)
2. **Every physics claim cites the SAME source the engine cites.** A claim with
   no engine behind it is **flavor** and wears the "plausible, not validated"
   label like any other flavor — including game-feel tips ("watch for the flame
   to drop").

This is the §15.5 verified-vs-flavor contract applied to teaching text.

---

## 6. The slice ladder

Each slice banks one playable artifact + its structural tests; each names its
scope ceiling. **Build in order; stop and play after each** (the loop must be fun
before it grows).

### Slice 0 — the hero heat, interactive (the playable capstone) — **BUILT ✓ 2026-06-21**
- **As built.** The `game/` package stood up exactly to this spec: the immutable-`Heat` turn
  surface (`state.advance` runs one sealed stage per turn — the golden-run test asserts stepping the
  chain reproduces `demo_capstone.run_chain`'s sealed verdict *exactly*, the proof it adds no physics);
  the one F2 blow-endpoint knob as value-selection on the C–O τ-curve (`knobs.py`, over
  `refining.equilibrium_oxygen`); the opt-in educational why-cards with every number read live from the
  engine (`teach.py`); the blow-curve figure (`figures.py`); the paper-thin Streamlit skin (`app_game.py`,
  the only `import streamlit`); the headless golden run `demo_game.py`; and the four structural tests
  (firewall + golden-run + state-transition + label/endpoint-consistency). The lone engine touch — promoting
  the casting re-base to `casting.cast_billet_onto` — closed the capstone's named promotion trigger. The
  per-knob-click vs auto-run choice was left cosmetic (the UI drives `advance`; the tested unit is `advance`).
- **Goal.** Make the **already-built B2 capstone chain playable**: one method
  (the capstone's 4140 BOF/EAF route), the chain auto-running every stage **except
  one** player knob — the **F2 decarb blow endpoint** (§3.3, value-selection on
  the τ-curve). Player sets the endpoint → the sealed chain runs → the part is
  judged (sound / soft-core) → the **provenance trail is the post-mortem.**
- **Build.** `game/` package; the stateful Streamlit surface (§3); compute helpers
  wrapping `demo_capstone.run_chain` / the F2 stages; the τ-curve figure (over
  `refining` + `plots`); the startup screen with the **educational toggle** +
  **why-cards on the one knob** (§5.2 tier 1).
- **Banked artifact.** The playable + a banked screenshot/figure for a new gallery
  **"Game"** card; root + `steel/` READMEs wired.
- **Tests.** Firewall guard; golden-run determinism (reference endpoint → sound,
  over-blow → soft-core, byte-stable verdicts, driving **helpers**); state-transition
  (each action pushes a new immutable `Heat`, trail grows by one); label-correctness
  (the blow target is tagged verified + cites `refining`); educational-content
  numbers read live (no hardcoded value).
- **Ceiling.** One method, one knob; **no reflex timing** (value-selection only,
  §3.3); economy is a placeholder; educational mode = toggle + why-cards only.

### Slice 1 — the gauntlet (every stage a decision) — **BUILT ✓ 2026-06-21**
**As-built (scope widened from the original "second knob" plan, the user's call).** Slice 0's
critique was *"nothing to get wrong in the other steps."* Slice 1 answers it: **every stage is a
decision**, each wrong call planting a latent flaw the finished part is judged on by the sealed
consequence engines.
- **Spine.** A frozen `Recipe` carries one knob per stage, every field defaulting to the capstone
  reference; each stage seam reads its choice. The canonical `Heat` is still built only from the eight
  stage seams → `play_to_end(reference) == run_chain` holds **verbatim** (golden run preserved).
- **Post-mortem (`postmortem.py`).** The consequence engines (`gas_porosity`, `hydrogen_flaking`,
  `hot_work` red-short, `hot_tear`, `cold_short_check`) run on the **finished part** without mutating
  the spine, attributing each defect to the stage that planted it. Cold-short is P-gated (carbon also
  raises DBTT — that's the carbon mistake, not the dephos knob).
- **Losability is the acceptance bar (the advisor's block).** Seven knobs are genuinely losable, each
  with one test proving a wrong setting flips the verdict end-to-end: decarb (off-grade/soft-core),
  dephos (cold-short), **deox = deoxidizer choice** Al ≫ Si > Mn (gas porosity), degas (flaking),
  desulf (**sulfur over the cleanliness spec** — the trim's Mn ties it so it does *not* red-short; the
  masking became the lesson), trim carbon-pickup (off-grade), heat-treat quench/section (soft core).
- **Casting is an honest no-loss pass-through** — modulus only sets the Chvorinov time, segregation is
  `fs`-based and lands on the centerline not the judged nominal, and there is no validated casting spec
  to cross. Reported plainly (a pinned test), **not** shipped as a fake slider.
- **`choices.py`** holds the tested option tables (every "recommended" option provably reproduces the
  reference); **educational mode** grows a **why-card per knob** (numbers read live, the threshold each
  engine cites). Surfacing the verified-vs-flavor labels as styled UI chips + the physics-shape
  explainer (tier 2) is **deferred** to a later pass — the labels exist; the *chip styling* did not ship.

### Slice 2 — methods & the era ramp (the tech tree) — **BUILT ✓ 2026-06-22**
**As built (Cut A — the converter-era purity ramp judged as 4140, the user's `AskUserQuestion` choice over
the fuller different-product tree).** The **§15.2 method→engine map** became a `presets.py` table of
`Method`s (acid Bessemer 1856 → Thomas 1879 → basic open hearth → BOF → modern EAF + ladle) and `Ore`s (a
phosphoric and a clean charge), each method a **constrained walk** through the same validated F1–F4 engines
behind the firewall — no `Heat` flag it fires is new, the era only chooses *which sealed seams run with what
chemistry*.
- **The era lever is the slag regime + the secondary-metallurgy unlocks**, all already built in `slag.py`:
  a `Method` carries the dephosphorization slag (`ACID_BESSEMER_SLAG`, `L_P≈1` — *runs and visibly fails* —
  vs `BASIC_CONVERTER_SLAG`, `L_P` in the hundreds) and the `can_desulfurize` / `can_degas` capability flags.
  More honest than "skip the stage": acid Bessemer *runs* a dephos stage that barely moves P.
- **The purity-control ramp is the difficulty curve** (§14 theme C / §15.2), driven by a new **ore axis**
  (the charge's tramp load) so the gates bite: a **phosphoric** ore is cold-short in acid Bessemer,
  phosphorus-fixed-but-still-dirty in Thomas/OH/BOF (no ladle desulf), sound only in the modern ladle era; a
  **clean** ore is sound even in acid Bessemer (*the* reason early Bessemer needed non-phosphoric ore).
- **The two era-gated tramps are P and S** — the benchmarked slag-partition physics. **Hydrogen is
  deliberately NOT era-gated** (probe-confirmed: the model introduces no charge H — `degas` only *sets* a
  Sieverts equilibrium — so "no vacuum" makes no flaking claim, rather than faking one). The kill, process
  speed, scale, nitrogen, and the **aluminium/vacuum anachronism** in old eras are **flavor**, labelled
  (§15.5). The basic open hearth and BOF **share Thomas' chemistry** in this model — said outright and
  **pinned by a test** (their distinction is flavor). The **bloomery** is named as the era-0 floor (a
  different product below the F1 crossover), **not** a played 4140 route (a named deferral).
- **The acceptance bar** (the Slice-2 analogue of Slice-1 losability) is **the ramp itself**: each era
  conquers exactly the tramp the history says it did, the modern reference still reproduces the golden run
  exactly, and the verdict matrix was **probed empirically before** `presets.py` was written.
- Educational mode grew to **tier 3** — per-era cited why-cards (`teach.method_why_cards`, numbers read live
  from the slag engine) + the purity-ramp `timeline`, pairing with the §14 historical surface.
- **Deferred (named):** the different-product methods (bloomery wrought iron, cementation, crucible, wootz —
  each needs its own win-condition); the verified-vs-flavor **chip styling** + the tier-2 physics-shape
  explainer (still open from Slice 1).

### Slice 3+ — economy, scale, discrete events (flavor, last)
- **Economy-scale anchors** (§16.3) — bloomery ~kg/day → crucible ~tens-of-kg →
  BOF ~300 t / 40 min — **flavor anchored to real orders of magnitude**, not a
  validated rate.
- **Type-A relaxation dynamics** with feel-tuned τ (§16.3 table) — degassing,
  flotation, desulf kinetics — labeled plausible, endpoint-consistent.
- **Physically-rated discrete events** (refractory breakout, slag carryover, ladle
  skull, §6.2) — rare, tied to a physical driver, **not** free-floating bad luck.
- (Deferred, named: real-time/reflex timing on a non-Streamlit surface, §3.3.)

---

## 7. Module map (proposed)

`game/` is the new sibling package §10 of `steel-making.md` already reserved:

```
game/
  __init__.py
  state.py        # the session-state schema + turn transitions (Heat in / Heat out)   [logic]
  knobs.py        # the τ-curves: Type-A relaxation, Type-B optimum (endpoint, deox)    [logic]
  presets.py      # the §15.2 method→engine recipes + per-field verified/flavor labels  [logic]
  teach.py        # educational-mode content selection (prose in game/, numbers live)   [logic]
  figures.py      # thin wrappers over demo_*.compute() + steel.plots                   [figure]
  app_game.py     # the ONLY `import streamlit`; paper-thin main()                      [ui]
  tests/
```

Physics stays in `steel/` / `engines/`; `game/` only orchestrates.

---

## 8. Validation & test surface (structural, per §2)

- **Firewall guard** (`test_game_firewall`) — `game/` imports no private engine
  internals, defines no physics constant, and `import streamlit` appears only in
  `app_game.main`.
- **Golden-run determinism** (`test_game_golden_run`) — drives the **helpers**:
  the reference blow endpoint → sound part, the over-blow → soft-core, verdicts
  byte-stable against the sealed-engine output.
- **State-transition** (`test_game_state`) — each action returns a new immutable
  `Heat`, the trail grows by exactly one `ProcessStep`, restart resets cleanly.
- **Label-correctness** (`test_game_labels`) — every UI field's verified/flavor
  tag matches its source; every educational number is read live (a baked-in
  physics number fails the test).
- **Endpoint-consistency** (`test_game_knobs`) — each τ-curve relaxes toward (Type
  A) / turns around (Type B) the validated F1–F4 endpoint and never overshoots it.

---

## 9. Invariant-compliance check (the `steel-making.md` §12 form)

| Invariant | How this plan honors it |
|---|---|
| Build the toolkit once; reuse frozen | `game/` touches **no** engine; it orchestrates the public surfaces only (the §8 firewall). |
| Phase so each stage banks an artifact | Slices 0–3 each bank one playable + its tests; Slice 0 alone is demonstrable. |
| Validation triad from day one | **N/A by design** — `game/` clears no physics triad; its discipline is the **structural** four-check set (§2/§8), stated up front, not skipped. |
| Target the consequence where the mechanism is a wall | Process *rates/dynamics* (the §4 transport-kinetics tar pit) stay **flavor** (Tier-3, §16); only validated endpoints are claimed. |
| Updating docs is part of every change | This plan, the per-slice READMEs, the gallery card, and any ADR are deliverables of each slice. |
| Terms of use | §11 below — clean, published science; flavor labeled. |

---

## 10. Terms of use

Same posture as `steel-making.md` §11. The game adds **no** new physics data, so
it introduces no new sourcing surface; all cited numbers are the engines' own.
Educational prose is original; every physics claim in it carries the **engine's**
citation (§5.3). Flavor (τ values, economy, discrete-event rates) is original and
**labeled plausible**.

---

## 11. Sequencing & immediate next step

**Build order:** Slice 0 (playable capstone + educational toggle) → Slice 1
(the gauntlet — every stage a decision) → Slice 2 (methods + the era ramp) → Slice 3+
(economy / flavor / discrete events). **Stop and play after each.**

**Immediate next step.** **Slices 0, 1 and 2 are BUILT ✓ (0/1 2026-06-21, 2 2026-06-22).** Slice 0 stood up
the `game/` package (firewall guard, the session-state surface §3, the Type-B blow knob
§3.3, the educational toggle §5.2, the structural tests §8) on the proven capstone chain.
Slice 1 made **every stage a decision** (the gauntlet): a `Recipe` choices vector + `choices.py` option
tables + `postmortem.py` (the sealed consequence engines judging the finished part), with **losability** as
the acceptance bar. Slice 2 made **the methods of history playable** (the era tech tree, Cut A — the
converter-era purity ramp judged as 4140): `presets.py` (the `Method`/`Ore` tables), the era-aware stage
seams, per-era tier-3 cards + the purity-ramp timeline, with **the ramp itself** as the acceptance bar
(probed first, pinned by `test_game_methods.py`). The next build is **Slice 3** (economy / scale / discrete
events, §6), the **different-product methods** (bloomery wrought iron, cementation, crucible, wootz — each a
new win-condition), or the long-**deferred Slice-1 polish** (the verified-vs-flavor labels as styled UI chips
+ the tier-2 physics-shape explainer). Stop and play first.
