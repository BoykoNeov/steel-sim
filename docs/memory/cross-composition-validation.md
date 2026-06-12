---
name: cross-composition-validation
description: "Steel §20 — cross-composition bainite validation vs the cited US Steel 1951 IT atlas (8 steels): the per-steel 'wall' MEASURED not asserted; cited BC fails (carbon-dominated), alloy-weighted FC/PC rank better (none wins both metrics) → per-steel anchoring VINDICATED; one-knob refit = diagnosis not law (ADR 0005); BUILT 2026-06-12, no engine touch"
metadata:
  type: project
---

**§20 — cross-composition bainite validation BUILT ✓ 2026-06-12** (validation-hardening on the project's
own named edge, NOT a new demonstrator). Direction = "widen the 8620 wall to N steels AND attempt to break
it" — the most in-character validation-first move. New `steel/cct_validation.py` + `demo_cct_validation.py`
+ `plots.cct_validation_figure` → `docs/figures/steel-cct-validation.png` + gallery "Validation" topic +
README row + `test_cct_validation.py` (9) / `test_demo_cct_validation.py` (2). **ADR 0005.** **No engine
touch** — `kinetics`/`austemper`/`unified_kv`/`pathint` byte-identical; the study only *reads* the cited
factors. Always-on (`not slow`) lane **500→511 passed** (+11; full suite 520 collected, 9 slow-marked).

**The data (the binding constraint was EXTRACTION FEASIBILITY, advisor).** Same already-cited public-domain
source = US Steel 1951 IT atlas (`atlas_of_isothermal_transformation_diagrams`, zero new provenance risk) —
NOT a copyrighted measured-CCT atlas (that's the *other* §19 gap, left untouched: IT anchors don't benchmark
a CCT bay). Pulled pages via **archive.org IIIF native-res region crops** (`iiif.archive.org/iiif/<id>$<N>/
pct:x,y,w,h/full/0/default.jpg`, IIIF index N = PDF page N+1); the searchable PDF is **2-page spreads**.
8620 *is* in the atlas (p.113). Reads **calibrated against the known 4340 anchor** (t50@700°F=391s reproduced
~factor-1.3) → **factor-2 reads: fine for ranking, marginal for magnitude.** Observable = bainite **50%-time
at 700°F (371.1°C)** (commensurable with the 2 cited austemper anchors 1080=70.6/4340=391), for 8 steels with
`Ms<371.1<Bs`: 1080,4340 (cited) + 4360,8660,4150,4640,6150,6145 (6 new). Low-C grades (8620/8630/4130/4140)
EXCLUDED (Ms≳700°F → martensite confound).

**The harness (model-faithful).** Predict each steel anchored on 1080 via the REAL `BainiteReaction.rate`
(carries per-steel grain `2^(0.41G)` + ceiling `(Bs−T)` — the cross-steel confounds advisor flagged), **swap
ONLY the composition factor** BC→PC→FC (`replace(rxn, BC=pearlite_PC(...))`) = a controlled test, same
undercooling shape. Spearman = Pearson-on-ranks (no scipy needed).

**The result (advisor tightened all 3 headline claims before commit):**
* **HEADLINE IS BIAS-IMMUNE — 2 CITED anchors only.** Cited BC predicts 4340 *faster* than 1080; atlas =
  ×5.5 *slower* → **×41 sign-inverted**, which *reproduces austemper's independent 1080/4340 scale gap* (the
  harness self-checks). No factor-2 read needed for the wall. **The 6 new reads were taken HYPOTHESIS-AWARE
  (confirmation-bias exposure — exactly what [[di-crosscheck-source]] warns); they CORROBORATE (ρ≈0.1, ×36),
  don't carry. 4640 most marginal (50°C above Ms), NOT rested on.**
* **NONE combines ranking + magnitude → per-steel anchoring VINDICATED. BOTH metrics ANCHOR-INVARIANT**
  (advisor's late hostile-reviewer catch: anchor-referenced "median miss" FLIPS which factor looks best on
  re-anchoring — FC-best@1080 but BC-best@4340; a single anchor only shifts all log-residuals by a const, so
  Spearman + the *spread* (std of log-resid) are invariant, the central "miss" is NOT → use spread). **Rank:**
  PC 0.81 > FC 0.48 > BC 0.10 (BC = the wall, carbon coeff 10.18 ≫ alloy → calls 1080 *slowest* when *fastest*).
  **Spread:** FC ×3.1 tightest, BC ×4.6 (small ONLY because BC is nearly FLAT = no-skill, not tracking), PC ×6.7
  widest. PC ranks-but-scatters, FC most-balanced, none both → no usable law. Mechanistic: **bainite
  retardation is ALLOY-driven, BC under-weights alloy vs carbon.** Don't spotlight PC (metric cherry-pick).
* **One-knob refit = DIAGNOSIS not law.** Fit single λ (carbon weight) on TRAIN, predict disjoint TEST
  (minimal-DOF — 5-coeff fit on 8 factor-2 pts = memorised noise): λ→floor (carbon removed) lifts TEST ρ
  0.4→0.8. **Decomposition** (`refit_decomposition`): gain carried by residual **cited alloy** coeffs
  (alloy-only ρ≈0.67 ≫ Bs+grain-only ρ≈0.26), NOT the confounds. Under-identified (1080 lone no-alloy steel;
  Bs absorbs carbon) → grafted into **nothing**.

**Decision = keep per-steel anchoring (ADR 0005).** User said "attempt the refit"; attempt made, honest
verdict = no cited single factor predicts cross-steel bainite *magnitude* better than ~×3 → wall **measured
and explained, NOT broken**. A real replacement law = new physics = its own ADR. This *strengthens* the
per-steel discipline (principled, not a shortcut). Amends/extends [[bainite-anchoring-probe]] (2 steels → 8)
and [[unified-kv-rebuild]]'s named wall.

**Durable lessons:** (1) advisor's "let read quality pick the branch" + "rest the headline on bias-immune
cited data, caveat hypothesis-aware reads" saved this from a confirmation-bias trap. (2) `_factor_value`
swap-in-place (`replace(BainiteReaction, BC=...)`) is the clean way to test alternative composition factors
without touching the engine. (3) IIIF region crops >> the downsampled PDF for reading 1951 scans.
