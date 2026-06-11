---
name: mixed-temper-next
description: "steel-sim mixed-structure tempering (plan §16): ALL STEPS 1-6 BUILT 2026-06-11 — steps 1-3 (validated core, properties.py §6) + steps 4-6 (design.py guarded unlock + Biot-aware recommended + §14 re-derivation)"
metadata: 
  node_type: memory
  type: project
  originSessionId: de815651-624e-4ad4-a0ce-d4922d12fd67
---

**Mixed-structure (per-constituent) tempering** — the named 3b deferral (temper a phase
*mixture*, not a fully-martensitic structure), plan **§16**, the §11 "smaller deferral". **COMPLETE
2026-06-11 (all 6 steps).** No engine touch, no new calibrated constant; the frozen set
(2c/3a/3b/Jominy/four-curves + `tempered_martensite_HV`/`hardness_HV`) stays **byte-identical**
(`properties.py` untouched by steps 4-6; only `design.py` + its own Phase-7 tests changed). Suite
**425 green** (+2 env-skips).

**STEPS 1–3 (the validated core — `properties.py` §6).** `tempered_hardness_HV(fractions, C,
T_temper, t_hours, comp, Vr, C_hj)` + `tempered_hardness_HRC` + `TEMPER_ACTIVE={"martensite"}`: rule
of mixtures, martensite → `tempered_martensite_HV`, FP/bainite/RA **temper-inert** *delegating* to
`CONSTITUENT_HV[name](C,comp,Vr)` (byte-exact no-op). `tempered_jominy_hardness` = the teeth
(near-end full-M softens hard / far-end inert byte-exact, differential `drop_near≫drop_far==0`).
Figure `docs/figures/steel-tempered-jominy.png`. 3 exact seams (A mart=1→3b / B mart=0→`hardness_HV`
/ C sub-onset→as-quenched) + diff-softening unit test. Figure in **HV not HRC**; near-end **band**
not `==` (KM sliver→RA); tempered traverse **non-monotone in distance**. NO extracted numbers
([[di-crosscheck-source]]).

**STEPS 4–6 (the design.py guarded unlock — `design.py`).**
- **Gate:** `_is_fully_martensitic` → **`_is_temperable`** = martensite-**dominant**
  (`MARTENSITE_TEMPER_MIN 0.95→0.50`) **AND** RA-**capped** (`RA_TEMPER_MAX=0.05`, the load-bearing
  guard). Values **data-grounded** (not guessed): at 10 mm the temperable martensitic grades sit at
  RA ≤ 0.035, the **hazard 1080-water at RA 0.175** (passes dominance ~0.78 M, *only* the RA cap
  stops it); dominance excludes 1080-oil (0.24 M bainite-heavy). RA guard = the new honest scope edge
  (RA→bainite/fresh-M on temper is non-monotone, can *raise* hardness, and `design` **recommends**).
- **Inverse:** `_temper_to_target` now inverts **`tempered_hardness_HV(fractions,…)`** over the
  mixture (bracket read from the function itself; `{martensite:1.0}` recovers pure-M exactly). **`Vr`
  threads (nan→None, matching `sweep.evaluate`)** or Seam-C breaks. `Recipe` gained **`martensite`**
  field; `label()` appends "(NN% martensite)" for a partial-M temper.
- **§14 HEADLINE RE-DERIVATION (the crux, advisor-confirmed — Option B).** At 45 HRC/10 mm cost-sorted
  set = `1045 water-temper (88% M, ⚠Biot) < 4140 oil-temper < 4140 water-temper(⚠) < 8620 water(⚠)`.
  The cheapest **1045-water is feasible** (the unlock) **but Biot-stretched** → **`recommended` made
  Biot-aware** (cheapest *lumped-valid*, fallback cheapest). **Textbook 4140-oil-temper recommendation
  HOLDS** — now by design, not by the old accident of 1045 being excluded. **Durable reasoning:** §14
  *already* said "cheapest *lumped-valid*"; the unlock just forced the intent explicit. The rejected
  alternative (pure-cost recommended, let it flip to 1045-water) would force a regression test
  asserting the tool's #1 recommendation is flagged outside its own 0-D validity = a guard asserting
  incoherence (the reductio). `test_recommended_demo_recipe_is_4140_oil_temper` stayed green unchanged.
- **Surfaces:** demo docstring/summary re-derived; `docs/figures/steel-design.png` regenerated;
  **notebook §7 surgically refreshed** — the Biot-aware recommended exposed a real `recipes[1:]` **bug**
  (assumed recommended==recipes[0]) → fixed to skip-recommended; both outputs re-harvested via a minimal
  [setup+cell] kernel run; **other 38 cells byte-identical** (the surgical single-cell technique, cf.
  [[steel-grain-physics-deferred]]). No app-table change — `label()` already carries the partial-M cue.

**Still named, not validated (unchanged):** **bainite-inert** & **RA-inert** (cited for pearlite only);
tempering changes **hardness only, never fractions**. Modeling bainite's *own* temper response = a
further deferral (same boundary as the as-quenched bainite placeholder). [[commit-push-end-of-batch]].
