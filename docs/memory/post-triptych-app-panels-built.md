---
name: post-triptych-app-panels-built
description: "Notebook/app backfill Slice A — the 5 post-triptych modules surfaced as app panels (consequences +3, making +2); notebook (Slice B) DEFERRED by user"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66a8df9c-7b88-4e8b-b6e4-309b2a458b96
---

**Notebook/app backfill — Slice A (the apps half) BUILT ✓ 2026-06-15** (commit `119ac12`,
from the "what is next" menu → notebook/app backfill). The five front-end modules built **after**
the triptych apps now have interactive panels; **+11 tests, 942 passed / 2 skipped** (measured `-n0`
on the two app files, full suite default lane), **NO engine, NO ADR, no constant** (ADR-0002 reach,
same posture as [[consequences-app-built]] / [[making-app-built]]).

**What was missing (grep-confirmed, not dates):** `app_consequences.py` had 6 panels but not
**peritectic / sulfide_morphology / wootz**; `app_making.py` had the ladle panel but not
**carbon_carry_in / deox_recovery** (both "Ladle trim (front-end)"). Added: consequences **+3**
(peritectic after hot-tear = the casting trio; then the two SIGNED foils), making **+2** after the F3
trim panel.

**The advisor's load-bearing pre-write crux: the panel pattern is "re-compose the sealed model with
the KNOB", NOT "wrap the zero-arg `compute()`".** All 5 `demo_*.compute()` are zero-arg (fixed demo
object), so each readout had to find the *parameterized* model entry point and confirm its **real
lever**. Per-module landmines (two are TME-1080-class traps):
- **sulfide_morphology — knob = `shape_controlled` (MORPHOLOGY), never an S slider** (else it re-derives
  the red-short panel; the build's own catch). Grade selector (cited 1144/1045 backbones) + shape toggle.
- **deox_recovery — a READOUT CONTRAST, CANNOT trip off-grade (sub-window).** Surfaced as `st.info` +
  `in_band=True` + the Mn-tax % + the porosity-risk flag from the weak kill; NO pass/fail off-grade line
  (the [[deox-recovery-built]] "why the gross hero stays hand-set").
- **wootz — 3 cited gates + the INTENT-gated flag preserved** (`forged_as_wootz = hyper AND
  forged_in_window`; flag fires only under intent). Real bug caught: `wz.forging_window()` **raises** on
  sub-hypereutectoid C — the display call would crash the panel when the C slider drops; **guarded +
  regression-tested**.
- **peritectic — knob = NOMINAL carbon (+ Si/Cr Cp lever), Wolf-FP classifier**; non-monotonic hero
  (0.11 %C cracks, leaner+richer sound). **carbon_carry_in — HC vs LC ferroalloy** → off-grade-on-C +
  over-hard (HV 702 vs 628). Both clean.

**Q2 (signed foils in a "what goes wrong" app) = narrative-fit, NOT a landmine** (advisor): the gallery
already files sulfide/wootz under "Impurity consequences (front-end)" and the whole front-end thread is
"the signed-impurity foil". Nudged the intro toward "what the impurity does — and it isn't always bad".

**Slice B (the front-end notebook) — DEFERRED when this was written; since BUILT ✓ 2026-06-15 →
[[post-triptych-notebook-slice-b-built]].** Scope (as built):
insert 5 sections into `making.ipynb` (surgical, byte-identical others, re-bank+READ outputs — the
[[making-notebook-built]] inverted-verdict landmine) **+** add `notebook="§…"` to the 5 `gallery.py`
CATALOG entries, regenerate `docs/index.html`. **No dead anchors exist today** — `_card_html` only emits
a `making.ipynb` link when `e.notebook` is set, and the 5 entries have no `notebook=` field (advisor
feared dead links; ground-truth grep showed none). Amends [[consequences-app-built]] /
[[making-app-built]]; companion to [[gallery-page]].
