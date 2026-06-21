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

**Notebook slice 2 — BUILT ✓ 2026-06-21 (`14a55b5`), B2 now FULLY CLOSED.** The deferred `making.ipynb`
section shipped: a static `## §capstone` placed as the **make-arc finale** (between §F4b solidification
and the "what goes wrong" pivot, NOT the whole-notebook grand finale). **Advisor crux = placement and
framing must agree** — the header is framed "the chain, fully threaded" (the capstone's break is the
§spine soft-core, not a D-series defect; it threads F1→F4, touches no D1–D9 content); the grand-finale
prose ("the synthesis the front and back halves were each built toward") stays the GALLERY blurb's, which
would only fit a post-§D9 placement. **Static, no Live cell** (§F4b is already markdown+single-code, no
`interact`) → deletes the whole `metadata.widgets` merge AND dodges the interact-swallows-exceptions
guard-gap. **Inverted-verdict landmine (bit this notebook twice) cleared by reusing `demo_capstone.print_summary`
VERBATIM** — the banked stdout then IS the CLI run, so dump-and-read collapses to "does it match?"
(confirmed: ref 92%/sound, foil 85%/soft-core+off-grade@trim, P 0.090→0.002, S 0.050→0.013). **Promotion
trigger NOT tripped** — the cell calls `compute()`, so `_cast_onto` stays inside the demo (a 2nd CALLER ≠
a 2nd implementation). **Surgical op** (script in gitignored `outputs/`, re-derived per [[notebook-surgical-insertion]]):
deepcopy setup cell 3 → bank ONE code cell in a fresh kernel → insert [header, code] at idx 30 → +
2 markdown edits (the §capstone section-index table row in the mental-model cell; an epilogue scope note
that the capstone draws its OWN demo summary, having no app — the advisor's flagged categorical-claim
edge) → **57 of 59 originals byte-identical** (content-hash + git-HEAD proven; count is 58 after 1 edit,
57 after the epilogue edit too) → CRLF. `test_making_notebook` clean ~28s, fast lane 984, gallery
drift-guard green; gallery `notebook="§capstone"` + both READMEs flipped deferred→built. No engine, no
ADR, no new test.

Amends [[next-directions-catalogue]]; sibling [[heat-state-spine-built]]; same recent batch as
[[fracture-coupling-built]] / [[b3-front-end-validation-built]]; notebook surgery mirrors
[[post-triptych-notebook-slice-b-built]] (same deepcopy/hash-guard/CRLF discipline).
