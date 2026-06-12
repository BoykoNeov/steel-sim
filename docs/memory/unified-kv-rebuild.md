---
name: unified-kv-rebuild
description: "Steel §19 — the unified-KV competing-reaction rebuild (the 6b deepening): three cited Li/KV reactions raced on one austenite pool so the bainite bay opens in CCT; per-steel-anchored DEMONSTRATOR (not cross-steel predictor), opt-in & parallel, frozen single-curve pipeline byte-identical; BUILT 2026-06-12"
metadata:
  type: project
---

**§19 — the unified-KV competing-reaction rebuild BUILT ✓ 2026-06-12** (the "6b deepening", the
**last** `[available]` §11 menu item → menu now empty). `steel/unified_kv.py` + `kinetics.py` **§7
`PearliteReaction`** (the one additive new reaction object) + `demo_unified_kv.py` +
`plots.unified_kv_figure` (+ shared `_draw_competing_ccurves`) → `docs/figures/steel-unified-kv-bay.png`
+ notebook/app **§6b** + `test_unified_kv.py` (28) / `test_demo_unified_kv.py` (4) / +5 app-helper tests.
**Suite 465→502 green** (+2 env-skips). **No ADR, no engine touch.**

**What it does:** races **three** cited Li/Kirkaldy–Venugopalan reactions — ferrite (`FC`, ΔT³, Ae3),
pearlite (`PC`, ΔT³, Ae1 — the new object; **√Mo** term, the one form quirk), bainite (`BC`, ΔT¹, Bs)
— on **one shared austenite pool** along a cooling path, with lever-rule **carbon enrichment** from
ferrite. So the **bainite bay opens in continuous cooling** — the thing 6b proved the single
Grossmann-shifted curve can't (4340 intermediate cool → bainite-dominant ≈0.62, the full ladder
martensite→bainite→ferrite+pearlite). Genuine parallel competition, **not** 6a's sequential
ferrite-then-pearlite.

**The crux (advisor, settled before any code): a per-steel-anchored CCT _demonstrator_, NOT a
cross-steel _predictor_.** The cited coefficients prove the split arithmetically (I hand-computed them,
matched the build exactly): **ferrite/pearlite differentials are cited-and-RIGHT** = the teeth —
`PC(4340)/PC(1080) ≈ 1435×` (≈ the atlas-measured ~10³× pearlite retardation), `FC(4340)/FC(1045) ≈
214×`; **bainite's is cited-and-WRONG** — `BC(4340)/BC(1080) ≈ 0.146` says 4340 bainite ~7× *faster*
where the atlas measures it ~4–5× *slower* (BC carbon coeff 10.18 is **directionally** wrong; no global
scale fixes a wrong-direction prediction). So bainite carries a **per-steel atlas-anchored scale**
(reused verbatim from `austemper.anchored_reaction` → [[bainite-anchoring-probe]]); the 8620
carbon-spread ceiling returns the instant cross-steel is claimed → scoped to the two atlas steels
(1080/4340), the wall named.

**Architecture = the 6a/6b/6d/§17/§18 discipline: parallel, opt-in, frozen core byte-identical.**
REJECTED the plan's "discard the calibrated pearlite curve" (would trade the four-curves + 1045/4140
Jominy benchmarks for a per-steel demonstrator = strict downgrade). `CCurve.tau`/`pathint`/
`HARDENABILITY_SCALE`/the 540-split **untouched**; `PearliteReaction` is purely additive (kinetics §7,
the 6a §5 / 6b §6 precedent). **Scale split (the honesty):** ferrite **global** (6a's 8.0), pearlite
**global** (`PEARLITE_SCALE` *derived at import* vs the frozen `CCurve().nose()` 1080 ~550°C/1s — the
"no magic number" rule, ≈0.50; then 4340's pearlite nose is *predicted* from cited PC = teeth), bainite
**per-steel atlas anchor**.

**Named edges (the CCT-source gap is the headline — keep docs at "demonstrated", never "validated"):**
(1) **no measured-CCT validation** — atlas is *isothermal*, "realised in CCT" = emergent from anchored
IT curves bridged by frozen Scheil additivity, a demonstration; (2) **carbon enrichment is first-order**
— feeds the final Mₛ (lever rule, right direction), but the diffusional kinetics use **bulk-composition**
factors/ceilings (in the slow regime bainite still races bulk `Bs≈497` though enriched `Bs≈405` — no
atlas support to re-derive per carbon, and enrichment is small in the bay); (3) **1080/4340 only**;
(4) carbon-only bainite hardness. **Consistency kicker (advisor):** 1080 opens **no** bay (bainite never
dominant on any continuous cool, max ≈0.34 vs 4340's 0.63) — for eutectoid plain carbon the only route
to bulk bainite is an isothermal **hold**, which is *exactly why austempering* ([[bainite-anchoring-probe]]
§6d) exists; deep consistency, not a discrepancy with four-curves.

**How-to lessons banked:** the notebook §6b was a **surgical single-cell insertion** (markdown + 1 light
code cell reusing `demo_unified_kv.compute()` — NO rate-sweep, the [[notebook-kernel-wedge-rootcause]]
hazard), other 39 cells byte-identical — the enabler here was **nbformat write is LF but the file is
CRLF**, so write to string then `.replace("\n","\r\n")` to stay byte-identical (verified the no-op
round-trip first). App §6b restricts the selector to 1080/4340 (`unified_system` raises otherwise → a
dropdown crash). Plan §19 = the as-built record; amends [[ferrite-bay-source]] (option (a) now built).
