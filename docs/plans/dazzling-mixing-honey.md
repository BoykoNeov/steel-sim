# Unified-KV competing-reaction rebuild — the "6b deepening"

> Working plan for the one item the steel plan still lists `[available]` in the §11
> menu: replace the single Grossmann-shifted pearlite curve with **ferrite +
> pearlite + bainite raced as one Kirkaldy–Venugopalan competing-reaction system**,
> so the **bainite bay opens in continuous cooling** — the thing Phase 6b proved
> the pinned-pearlite path cannot produce. This is the biggest physics lift left and
> the riskiest, because it is adjacent to the frozen kinetics core. On approval it
> becomes the steel plan's **§19** as-built record.

---

## 1. Context — the problem, the wall, and the intended outcome

The simulator models the diffusional transformation as a **single** TTT C-curve
(`kinetics.CCurve.tau`) with ceiling A₁, calibrated to a plain-carbon-eutectoid nose
(≈ 550 °C / ≈ 1 s), and slides it right for alloy steels by one multiplicative
**Grossmann** factor `M = tau_factor` (`HARDENABILITY_SCALE`, ≈ 8× for 4140). Pearlite
vs bainite is just a **temperature label** at `Bs = 540 °C` (the "540-split"). Phase 6a
added a *parallel* proeutectoid-ferrite reaction; Phase 6b built a standalone cited
`BainiteReaction` but **proved the bay cannot be wired into the current `pathint`**
three ways (Jominy-pinned `M` ≈ 8× vs the ~100× a bay needs; carbon-flat 550 °C nose
inside the bainite band; the 8620 carbon-spread ceiling). The bay — the temperature
window where alloy pushes ferrite/pearlite far right while barely moving bainite, so a
cooling path threads between them into bainite — is therefore **absent from the
continuous-cooling microstructure** today.

**Why now / intended outcome.** This is the last named deepening. The outcome is a
**new, opt-in unified-KV competing-reaction integrator** that *does* open the bay in
continuous cooling for an alloy steel (4340), built on the cited Li/Kirkaldy–
Venugopalan reaction family already in the codebase, **leaving every frozen benchmark
byte-identical**.

## 2. The decisive constraint (settled before any code) — a *demonstrator*, not a *predictor*

The 2026-06-10 bainite-anchoring probe ([[bainite-anchoring-probe]], banked in
`austemper.py`) settled the epistemics, and the cited coefficients confirm it
arithmetically:

* **Ferrite/pearlite differential is cited-and-right** → it opens the bay, and it is
  **teeth**. Scale-free cited ratios, computed from `FERRITE_FC_COEFFS` /
  the pearlite `PC` factor:
  * `PC(4340)/PC(1080) ≈ 1400×` ≈ the atlas-measured ~10³× pearlite retardation.
  * `FC(4340)/FC(1045) ≈ 214×` (and 6a's `FC(4140)/FC(1045) ≈ 32×`).
* **Bainite differential is cited-and-WRONG** → `BC(4340)/BC(1080) ≈ 0.146` says 4340
  bainite is ~7× *faster* than 1080; the atlas measures it ~4–5× *slower*. BC's carbon
  coefficient (10.18) is **directionally** wrong — **no global scale fixes a
  wrong-direction prediction.** So bainite **must** carry a **per-steel atlas-anchored
  scale** (exactly `austemper.py`'s machinery); BC is never used for absolute
  cross-steel times.

**Consequence (the load-bearing scope decision):** this can only be a **per-steel-
anchored CCT demonstrator**. A unified-KV with cited factors + one global scale would
reproduce 6b's negative result. We do **not** attempt cross-steel bainite prediction;
the 8620 carbon-spread ceiling returns the instant we claim cross-steel, so the
deliverable is scoped to the two atlas-anchored steels (1080, 4340) and 8620/cross-comp
is **named as the wall**.

## 3. Architecture — parallel, opt-in, frozen core byte-identical

Reject the steel plan's "discard the calibrated pearlite curve" option **outright**
(advisor): the four-curves demo + 1045/4140 Jominy benchmarks are the project's entire
validated value; trading them for a per-steel-anchored demonstrator is a strict
downgrade. Instead, **add alongside**, the same discipline as 6a/6b/6d/§17/§18:

* **`kinetics.CCurve.tau`, `pathint.transform_along_path`, `HARDENABILITY_SCALE`, the
  540-split — all untouched and byte-identical.** The new system is a *separate*
  integrator; the existing pipeline and every frozen figure/benchmark are unchanged.
* The one **additive** edit to the frozen-core *file* is a new `kinetics.py` **§7
  `PearliteReaction`** class + `pearlite_PC`/`pearlite_reaction_for_steel`, mirroring
  6a's §5 `FerriteReaction` and 6b's §6 `BainiteReaction` (those phases also *added* to
  `kinetics.py` without changing the frozen surfaces — the precedent). No existing
  symbol changes signature or value.
* Everything else lives in a **new module `steel/unified_kv.py`** (peer of
  `austemper.py`), so `pathint` stays byte-identical.

## 4. The new physics

### 4a. `PearliteReaction` (the one missing reaction object) — `kinetics.py` §7
The cited Li/KV **pearlite** member of the same site-saturation family as ferrite/bainite:
ceiling **Ae1** (= `fe_c.A1()`, 727 °C — pearlite cannot form above A₁), undercooling
exponent **ΔT³** (like ferrite, not bainite's ΔT¹), composition factor
**`PC = exp(−4.25 + 4.12·C + 4.36·Mn + 0.44·Si + 1.71·Ni + 3.33·Cr + 5.19·√Mo)`**
(cited, [[ferrite-bay-source]] — note the **√Mo** term, the one functional-form
difference from FC/BC's linear Mo). Reuses the shared `_kv_shape_g` /
`_kv_site_saturation_step` helpers and `KV_Q = 27500 cal/mol`. `rate(T) = scale·2^(0.41·G)·
(Ae1 − T)³·exp(−Q/R_cal·T)/PC`. Same dataclass shape as `FerriteReaction`.

### 4b. The competing integrator — `unified_kv.py` (the actual lift)
Three reactions sharing **one austenite pool** along a cooling path `(t, T)` — genuine
parallel competition, **not** 6a's sequential ferrite-then-pearlite. Per cooling step
`(T, dt)`:

1. **Ferrite** (if `T < Ae3` and `m_f < f_pro`): advance its completion
   `U_f ← U_f + K_f·g(U_f)·dt`; new mass `dm_f = ΔU_f · f_pro`.
2. **Carbon enrichment (the coupling the advisor flagged):** ferrite (~0.02 %C) rejects
   carbon into the remaining austenite — recompute `C_γ` by lever-rule mass balance
   `C_γ = (C0 − m_f·C_α)/(1 − m_f)`. This **raises** `C_γ`, which lowers the pearlite/
   bainite ceilings (`Bs` via Steven–Haynes at `C_γ`) and `Ms` (Andrews at `C_γ`),
   feeding back into the competitors. Bounded, lever-rule-principled.
3. **Pearlite** (if `T < Ae1`) and **bainite** (if `T < Bs(C_γ)`): advance their own
   completions `U_p`, `U_b`; their mass increments draw from the **remaining austenite**
   `γ = 1 − m_f − m_p − m_b`, apportioned by their instantaneous rates and clipped so the
   pool never goes negative (small `dt` ⇒ order-insensitive; pinned by a mass-conservation
   + order-insensitivity test).
4. At path end, the surviving austenite `γ_final` shears to **martensite** per
   Koistinen–Marburger at `T_min` (using `Ms(C_γ_final)`), the rest **retained**.

**Bookkeeping invariant:** `ferrite + pearlite + bainite + martensite + retained = 1`
exactly, by construction (the `pathint`/`austemper` discipline). Emits the same stable
five-key `fractions()` dict so `properties.hardness_HV` consumes it unchanged.

### 4c. Per-steel time-base assembly (the honest scale split)
* **Ferrite** — 6a's **one global** `FERRITE_KINETIC_SCALE = 8.0` (validated, keeps
  8620 in band; FC is right-direction). Reused, not re-tuned.
* **Pearlite** — **one global** new scale, **calibrated so 1080's unified pearlite nose
  reproduces the frozen ~550 °C / ~1 s pearlite nose** (ties the new system to the
  four-curves anchor → *consistency*, not a free knob). Then **4340's pearlite nose is
  predicted** from the cited PC ratio with no 4340 tuning — the teeth.
* **Bainite** — **per-steel atlas-anchored** scale (`austemper.ANCHORED_SCALES`:
  1080 ≈ 6.8e3, 4340 ≈ 165; the ×~40 gap *is* the cross-composition wall). Reused via
  `austemper.anchored_reaction`. By construction for the absolute bainite time; the wall,
  not teeth.

So the 4340 bay = **predicted** (1080-calibrated PC, global ferrite) pearlite/ferrite
noses pushed ~10³× right, vs the **atlas-anchored** bainite nose barely moved — the
pearlite/ferrite side is non-circular and atlas-confirmed.

## 5. The teeth, the consistency guards, the named gaps (pin before writing)

**Teeth (asserted):**
1. **Cross-composition differential (cited, atlas-confirmed).** The scale-free
   `PC`/`FC`-vs-`BC` ratios reproduce 4340's measured within-steel bay separation
   (pearlite/ferrite ~10³× slower than 1080; bainite only ~4–5×). Pinned as a ratio test
   on the reaction objects (no integrator needed).
2. **Per-steel bainite holdout (austemper's).** Anchor 4340 bainite at one cited
   `(T, t₅₀)`, predict another atlas temperature within ~×1.3 — reuses
   `austemper.hold_time_to_fraction` (already validated; re-asserted in this context).
3. **The bay opens in continuous cooling (the NEW capability — a demonstration, not a
   benchmark).** A 4340 path at an intermediate rate threads between the pushed-right
   pearlite/ferrite noses and the martensite floor → a **bainite-dominant**
   microstructure the single-curve `pathint` cannot produce. This is the headline and is
   labelled *demonstration*, not teeth.

**Consistency guards (must-not-contradict, not new teeth):**
* **1080 four-curves ladder.** The unified system on 1080 must still give
  pearlite → bainite → martensite across furnace/air/oil/water and show **no spurious
  bay** (eutectoid plain carbon: merged C-curve). Asserted as a guard.
* **8620 carbon-spread ceiling** returns the moment cross-steel is claimed → deliverable
  scoped to anchored steels; 8620/cross-comp named as the wall.

**Named gaps (state plainly):**
* **CCT-source gap.** The atlas is *isothermal*. "Realised in CCT" means **emergent from
  the per-steel-anchored IT curves bridged by the already-frozen Scheil additivity**, not
  validated against a measured CCT diagram (we don't have one). No CCT benchmark is
  implied.
* **Bainite hardness** stays the carbon-only placeholder (`properties.vickers_bainite`),
  load-bearing here as in `austemper` — under-ranks alloyed bainite; microstructure, not
  hardness, is the headline.
* **Claims stop at the 50 % line** (probe edge); near-Mₛ acceleration unmodeled; the model
  nose runs a little high — all inherited from `austemper`'s named edges.

## 6. Deliverables (mirrors the austemper / residual as-built pattern)

| File | What |
|---|---|
| `steel/kinetics.py` (§7, **additive**) | `PearliteReaction`, `pearlite_PC`, `pearlite_reaction_for_steel` — frozen surfaces byte-identical |
| `steel/unified_kv.py` (**new**) | the competing integrator + carbon enrichment + per-steel assembly (ferrite global / pearlite global / bainite atlas-anchored) + a `UnifiedResult` dataclass with `fractions()`/`dominant()` |
| `steel/demo_unified_kv.py` (**new**) | the 4340 bay demonstrator + 1080 consistency panel |
| `steel/plots.py` (additive helper) | `unified_kv_figure` — two panels: (left) the three KV C-curves for 4340 with a cooling path threading the open bay → bainite; (right) 1080's merged curve (no bay) |
| `docs/figures/steel-unified-kv-bay.png` | banked figure |
| `steel/tests/test_unified_kv.py` | the teeth + guards + mass-conservation + order-insensitivity + input guards |
| `steel/tests/test_demo_unified_kv.py` | demo smoke + figure build |
| `steel/steel.ipynb` (new §) | a teaching section presenting the unified-KV bay (see narrative below) — surgical single-cell insertion per [[steel-grain-physics-deferred]]'s nbformat round-trip discipline, other cells byte-identical |
| `steel/app.py` (new §) | a Streamlit section (anchored-steels dropdown 1080/4340, intermediate-rate path → the open bay) on tested compute helpers, mirroring austemper §6 |
| `steel/tests/test_app.py` (+helpers) | always-green compute-helper tests for the new app section (the austemper-§6 pattern) |
| `docs/plans/steel-production.md` §19 | as-built record |
| `steel/README.md`, `docs/memory/` | load pointer + module map; a memory note |

**Surface scope (chosen):** surface the unified-KV bay in **both** `steel.ipynb` and
`app.py` (like austemper §6), and — the user's explicit requirement — make **both
sections carry the two-model narrative**:
* **Why the unified-KV system exists** — to open the bainite bay in continuous cooling,
  the thing the single Grossmann-shifted curve (and 6b) could not.
* **The limitations of each model, side by side:**
  * *Single-curve pipeline* (the **taught/validated default**): one C-curve + Grossmann
    `M`, no separate bay, pearlite/bainite split by temperature — but it carries the
    validated four-curves + 1045/4140 Jominy benchmarks and works for *any* composition.
  * *Unified-KV system* (the **demonstrator**): opens a real bay from cited
    differentials, but is a **per-steel atlas-anchored demonstrator** (1080/4340 only),
    cannot predict cross-steel bainite (the BC wall), bridges IT→CCT by Scheil additivity
    with **no measured-CCT validation**, and uses the carbon-only bainite hardness.
  The narrative must make clear they are **not** rivals to pick between: the single curve
  stays the validated workhorse; the unified-KV view is the mechanism-deepening lens.

## 7. Verification (end-to-end)

* `./run_tests.ps1` — full suite stays green; assert the **byte-identity** guards
  (four-curves, Jominy, `pathint`, `austemper`, `kinetics.CCurve` unchanged) explicitly,
  the way §16/§17/§18 did.
* New `test_unified_kv.py`: (1) PC/FC-vs-BC ratio teeth on the reaction objects;
  (2) `∫ fractions = 1` to machine precision over many paths; (3) order-insensitivity of
  the pearlite/bainite split under `dt` refinement; (4) the **bay-opens** assertion
  (4340 intermediate-rate path → bainite-dominant) and its **resolution-convergence**;
  (5) the **1080 no-spurious-bay** guard + four-curves ladder; (6) input guards
  (unknown steel, bad path).
* Build the figure headless (`python steel/demo_unified_kv.py`) and eyeball the open bay
  on 4340 vs the merged 1080 curve.
* **Notebook/app:** `test_app.py` exercises the new compute helpers (always-green, no
  Streamlit import); the notebook section is verified by the existing
  `test_steel_notebook` headless run (with its retry-on-wedge machinery,
  [[notebook-kernel-wedge-rootcause]]); `python steel/app.py` must still reach
  `import streamlit` only inside `main()`.
* Before declaring done: re-run the cited-ratio sanity numbers in §2 against the built
  reaction objects (they should reproduce ~1400× / ~214× / ~0.146).

## 8. Risk register (this is the riskiest item — name them)

* **It could still collapse to a partial result** if the predicted 4340 pearlite/ferrite
  noses don't actually clear the bainite region in CCT. Mitigation: the §2 hand-computed
  ratios already show ~10³× separation, so the bay *should* open; if a path can't be found
  that lands bainite-dominant, that is itself a reportable finding (and the demonstrator
  becomes the isothermal-diagram bay, still a real artifact).
* **Carbon-enrichment feedback** can balloon scope. Mitigation: keep it lever-rule simple
  (one `C_γ` update per step), named as a first-order coupling; it is the *competition*
  that matters, not a full multicomponent partition model.
* **Frozen-core proximity.** Mitigation: `PearliteReaction` is purely additive; a
  byte-identity test on `CCurve`/`pathint`/four-curves/Jominy is written *first* and must
  stay green throughout.
* **No new ADR / no engine touch** (the frozen `engines/diffusion` is not involved at all
  — this is pure `steel/`-local kinetics).
