---
name: post-triptych-notebook-slice-b-built
description: Notebook/app backfill Slice B — the 5 post-triptych modules surfaced as making.ipynb sections; closes the deferred notebook half
metadata: 
  node_type: memory
  type: project
  originSessionId: 84917e10-06a2-4194-bb80-432a3be4867a
---

**Notebook/app backfill — Slice B (the front-end notebook half) BUILT ✓ 2026-06-15** (commit
`a9df20b`), closing the [[post-triptych-app-panels-built]] "Slice B DEFERRED by user". The five
modules built **after** the triptych now have `making.ipynb` sections: **§F3b** carbon carry-in +
**§F3c** deox→recovery (after the F3 ladle section), and **§D7** peritectic + **§D8** MnS morphology
+ **§D9** Wootz (after §D6 hot-tear). 44 → **59 cells**; **NO engine, NO ADR, no constant, NO new test
function** — full default lane stays **942 passed / 2 skipped** (engines + steel; measured via
junit-xml because the project's `-q -n auto` addopts suppress the terminal summary line).

**House shape reused verbatim:** each section = a markdown header + a *direct* banked compute cell
(`from steel.demo_X import compute`; `plots.X_figure(...)`; then the verdict prints) + a `# Live:`
`interact` cell — calling the **same** tested `app_making` (`M.`) / `app_consequences` (`C.`) readout
helpers the apps use, so no scenario logic is duplicated. Discrete knobs use
`widgets.Dropdown(options=[(label, value)…])` (incl. bool toggles), continuous ones the KNOB-styled
`FloatSlider`; constants (`M.DEOX_KILLS`, `C.PK_C_MIN`, `C.SM_BACKBONES`, `C.WZ_*`) come from the apps.

**DURABLE — the [[making-notebook-built]] inverted-verdict landmine was actively cleared, not trusted.**
`test_making_notebook` only asserts "runs clean" (no cell raises) — it does **not** check verdict
correctness. So I (a) empirically verified every hero *before* writing the cells, and (b) **dumped and
READ all five banked verdict blocks** against those heroes. The trap zones, all read correct: deox =
**readout-not-flag** (no off-grade ✗/✓ line — both kills land in-band, sub-window; only F2's
porosity-risk fires); sulfide = **dual sign** (`_mark(not free_machining)` for the asset, `_mark(anisotropic)`
for the liability — the shape toggle flips toughness only); wootz = **three-tier glyph** (✓ watered /
✗ failed / · no-flag, never a binary pass/fail); peritectic = non-monotonic (✓/✗/✓).

**DURABLE (sharpened by a post-build self-review 2026-06-15) — `interact` SWALLOWS exceptions, so the
live `# Live:` cells are guarded by NOTHING the suite checks.** Proven empirically: a `KeyError` raised
*inside* an `interact` callback does **not** raise `CellExecutionError` and banks **0** cell-level error
outputs (the traceback lands in the widget's Output area) — so "runs clean" is blind to a bad readout key
in a live cell. The live cells legitimately use keys the bank cells never exercise (`grade_verdict`,
`verdict`, `why`, `free_verdict`, `aniso_verdict`); the **only** real guard is a *direct* key-existence
check against the readout dicts (done — all present). So the landmine is two-pronged: bank cells need the
verdict **READ**, live cells need the **keys verified by calling the readout**, not by trusting the run.
Self-review also re-confirmed: 5 §-anchors all match real headers; widget state 167 models / 0
referenced-but-missing / 0 dangling internal refs (additive merge orphaned nothing); gallery drift-guard
byte-identical; wootz readout survives ALL slider corners (sub-hypereutectoid C=0.4 guard holds).

**DURABLE — surgical insertion verified by content hash, NOT by the git line-diff.** The notebook diff
is huge (+2856 / −643) purely from 5 inline base64 figures + `nbformat` JSON re-serialization; that
number is meaningless for correctness. The real proof: `git show HEAD:…ipynb` vs current →
**40/44 original cells byte-identical** (only the 4 markdown cells I edited for the counts/anchors
changed), **non-widget metadata identical**, **0 code/figure/timestamp deletions**. Method = bank the
10 new code cells in **ONE fresh kernel session** (so widget state is internally consistent), then merge
its `metadata.widgets` state **additively** into the notebook (`dict.update` → **120 existing models
preserved byte-identical, 47 added, 0 removed**). `copy.deepcopy(setup_cell)` before executing (the
NotebookClient-mutates-in-place trap), descending-index inserts, and **write CRLF** via
`open(newline="\r\n")` (translates only structural `\n`; the JSON-escaped `\n` in strings is literal
backslash-n). Build script in gitignored `outputs/` (re-derive per [[notebook-surgical-insertion]]).

**Gallery wiring — the two prior memories were each HALF-right (reconciled from `gallery.py` code):**
`_card_html` emits a notebook link **only when `e.notebook` is set** (the post-triptych memory) **and**
routes to `MAKING_NOTEBOOK_URL` because the topic contains `"front-end"` (the [[making-notebook-built]]
memory) — both true, neither alone. The `e.notebook` value (`"§D7"`) is **link TEXT only — there is no
`#anchor` in the href**, so the §-labels just have to match the headers a reader scans for. Added
`notebook="§…"` to the 5 CATALOG entries, regenerated `docs/index.html`, drift-guard green. Both READMEs:
the 5 guided-tour "Also interactive" rows (`making nb §X · app *making/consequences*`) + the notebook now
covers "nine defect consequences". Amends [[post-triptych-app-panels-built]] / [[making-notebook-built]] /
[[gallery-page]]; the one-`Heat`-through-the-whole-run integration capstone stays the separate larger item.
