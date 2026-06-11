---
name: bainite-anchoring-probe
description: "6b follow-up probe (2026-06-10) — austempering anchoring of BainiteReaction against US Steel 1951 atlas; per-steel PASS (~×1.3), cross-composition FAIL (×14-35, wrong direction); Phase 6d BUILT on this basis 2026-06-10 (austemper.py, plan §13 = as-built record)"
metadata: 
  node_type: memory
  type: project
  originSessionId: bd5569e2-923c-4690-a1d4-6800f98b226c
---

**The probe (run 2026-06-10, throwaway scripts in gitignored `outputs/probe_6b/`,
NOT committed):** can `BAINITE_KINETIC_SCALE` be anchored against cited isothermal
data so an austempering recipe (the one valid home for the descoped [[ferrite-bay-source]]
6b reaction) has teeth? Measured data = **US Steel "Atlas of Isothermal Transformation
Diagrams" (1951), public domain, archive.org scan** (`atlas_of_isothermal_transformation_diagrams`):
1080 p.42 (C .79/Mn .76/grain 6) + 4340 p.105 (C .42/Mn .78/Ni 1.79/Cr .80/Mo .33/grain 7-8).
Read-offs extracted **computationally** (IIIF page crops → gridline-pattern fit, rms ~1 px,
~173 px/decade; curve tracing by row-scan chaining — label letters drop out as short traces).
Atlas conventions pinned: begin line ≈0.1% transformed; dashes = <2 s/uncertain; dotted = 50%.

**Verdict — the design fork for any future austempering phase:**
1. **Per-steel anchoring PASSES** (the grain-growth-holdout pattern): one scale fit at one
   (T, t) point predicts that steel's isothermal window within ~×1.3 — 1080 begin-line
   ×1.0–1.3 over 435→288 °C (50%-line ×1.06!); 4340 ×0.7–1.3 over 427→371 °C. The ΔT¹·Arrhenius
   (Q=27500) shape is genuinely good in the practical austempering band.
2. **Cross-composition FAILS ×14–35, wrong direction**: cited BC says 4340 ~7× *faster* than
   1080 (carbon coeff 10.18 dominates); atlas measures 4340 ~4–5× *slower*. Per-steel anchored
   scales differ ×36 (1080 ≈ 1.6e3 begin / 6.8e3 t50; 4340 ≈ 46 / 165; literature base = 1 →
   absolute KV-as-implemented ~10³–10⁴ slow, quantifying 6b's "named, not validated").
   → an austempering phase needs a **per-steel anchored-scale table**; BC must NOT be used
   for absolute cross-steel times. **The 6b teeth survive**: the atlas confirms the *mechanism*
   (4340 bainite retarded only ~4× while its pearlite is retarded ~10³×) — what fails is BC's
   carbon-vs-alloy arithmetic, not the Cr/Mo-weak-on-bainite story.
3. **Named edges**: near-Ms acceleration unmodeled (1080 @260 °C ×2.9); above-nose ×1.4
   (model 4340 nose 458 °C vs measured ~430); begin→50% spacing model ×39.5 vs measured
   ×9.5–14 (g(U) late-stage vs atlas begin-sensitivity ambiguity) → **anchor and predict at
   the 50% line only**; S-H Bs extrapolated beyond 0.55 %C for 1080 (worked fine).

**Why:** settles "is there a point in partial/optional 6b integration" — yes for a per-steel
austempering recipe (real holdout teeth available), no for any global-scale or BC-trusting wiring.
**How to apply:** **Phase 6d BUILT on this basis 2026-06-10** (steel-work): `austemper.py`
(cited `AtlasSteel` table = the read-off contract, now in code; per-steel scales derived at
import — 1080 6.82e3 / 4340 165, gap ×41 = the pinned negative), `demo_austemper.py` +
`plots.austemper_figure` → `docs/figures/steel-austemper.png`, notebook §6 + app §6 (anchored
steels only, sliders clamped inside Mₛ/Bs), 20 new tests, steel not-slow gate 319→339,
pathint/kinetics byte-identical. Plan §13 Phase 6d = the as-built record incl. the deltas:
per-steel atlas G (6 / 7.5) absorbed into the scales; the 4340 begin-shape holdout anchors at
the mid-window **398.9 °C** point (371.1-anchoring puts 426.7 at ×1.40, outside the ×1.35
claim); pearlite-race police = single-curve fictitious time over the **live race window** (hold
capped at bainite completion 0.99), warn threshold 0.15 — silent in the anchored band, loud
near Bs; guards refuse (ValueError) outside Mₛ<T<Bs; martempering = the named unbuilt seam.
The probe scripts in gitignored `outputs/probe_6b/` are scaffolding only.
The atlas's E-Q hardenability panels were flagged in §13 as a candidate independent benchmark
for 6c — **CHECKED AND DROPPED 2026-06-10** ([[di-crosscheck-source]]): the 1951 atlas is an
*IT* atlas, the "4340 E-Q panel p.105" collided with `austemper.py`'s 4340 *IT diagram* p.105 (the
panels were speculative). 6c instead used SAE J1268/J406/EMJ measured H-bands; **6c BUILT, Phase 6 complete.**
