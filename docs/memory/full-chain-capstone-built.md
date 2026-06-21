---
name: full-chain-capstone-built
description: "B2 full-chain capstone BUILT — one Heat threaded ore→billet→part on a single provenance trail; integration, no new physics"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c3e7630-5738-46c7-8530-b022a3dd1305
---

**B2 full-chain capstone BUILT ✓ 2026-06-21** (`b6507b0`'s successor): the integration finale —
**one** `Heat` threaded ore→billet→part (`from_hot_metal` → `decarburize` → `dephosphorize` →
`deoxidize` → `degas` → `desulfurize` → `trim_to_grade` → `cast_billet` → `heat_treat`) on a
**single, un-rewritten provenance trail**. `demo_capstone.py` + `plots.capstone_figure` + 9 tests +
gallery entry (37 now) + both READMEs + next-directions B2 promoted in-place. **No engine touch, no ADR,
984 green.**

**The gap (the orientation finding):** the seams existed but **nothing threaded one Heat** — each stage
started from its **own fresh origin** (`refining.from_hot_metal` preloads the alloys; `ladle.from_tap` is
a separate lean origin; `casting.cast_billet` takes a `Steel` and emits **fresh-trail** heats), which is
exactly why `app_making` shows stages **independently** ("compose by the Heat they hand on, not a shared
slider"). So B2 was genuine *integration*, not narration over an existing chain.

**Crux = the F4 trail-break + Option A.** Casting is the **lone** front-end seam that takes a `Steel`
(its siblings `deoxidize`/`desulfurize`/`trim_to_grade` all consume a `Heat`). Chose **Option A =
demo-local re-base** (`parent.evolve(cast_step, composition=…)`, the same repack primitive the seams use)
— **zero sealed-module touch**. F2→F3 threads with NO glue (`trim_to_grade` consumes the refined Heat;
just pass an **alloy-lean** backbone to `from_hot_metal` so F3's trim is meaningful). **Promotion trigger
(named deferral):** if a 2nd surface (the notebook) needs the same glue → promote to a `Heat`-consuming
casting seam rather than duplicate the re-base.

**Advisor-forced empiricism — "compute & look BEFORE prose" (the B3 lesson again).** Ran the chain and
printed defects/trail first; three default seams trip and had to be set to a **good-practice recipe**
(NOT calibration): **deep vacuum `p_H2=0.006`** (default 1.0 → ~25 ppm H ≫ 2 ppm flaking limit),
**seeded tramp P 0.090 / S 0.050** into the lean backbone (else dephos/desulf are no-ops → "we refined
it" hollow; verified driven below the 0.035/0.040 specs), Al kill 0.04 clears porosity, **decarb to the
grade nominal**, **F1 crossover read from the model** not hardcoded. Swept quench Ø to **separate** the
heats: **Ø20 mm** → reference 92% M (clean, margin thin-but-deterministic: trim dilutes C to ~0.388, just
inside the 0.38 floor), foil 85% M (soft).

**Foil = carbon over-blow (single isolated knob).** Both heats identical except the F2 blow endpoint
(0.40 vs 0.25 %C) → reference sound vs foil **off-grade (at the trim) + soft-core (at the quench)** —
the **longest propagation in the repo** (mistake at step 3, surfaced at steps 7 & 9). Advisor warned
**don't run `cold_short_check` on a quenched part** (normalize-vs-quench route mismatch); the carbon foil
stays on the quench route. **NO tooth** — structural integration only (continuous 9-step trail, ordered
field-fill, cross-chain propagation, reference clears every sealed-engine spec), the `heat_state` posture.

Amends [[next-directions-catalogue]]; sibling [[heat-state-spine-built]]; same recent batch as
[[fracture-coupling-built]] / [[b3-front-end-validation-built]]; notebook slice 2 deferred per the
notebook-discipline lesson ([[post-triptych-notebook-slice-b-built]]).
