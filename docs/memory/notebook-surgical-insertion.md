---
name: notebook-surgical-insertion
description: How to safely add a cell to steel.ipynb keeping every other cell byte-identical — the deepcopy-the-setup-cell trap
metadata: 
  node_type: memory
  type: project
  originSessionId: 8509c3cf-51ea-4357-99cf-d9daef29bb66
---

Reusable technique for inserting sections into `steel.ipynb` while keeping every
**other** cell byte-identical (the discipline behind §6b [[unified-kv-rebuild]] and the
five §9-surfacing sections added 2026-06-12). The insert scripts live in gitignored
`outputs/` (e.g. `outputs/insert_nb_sections.py`), so this technique does **not** persist
in the repo — re-derive it from here.

The recipe: `nbformat.read` → build `new_markdown_cell` / `new_code_cell` → execute **only**
`[setup_cell, new_code_cell]` in a fresh `NotebookClient` kernel to embed authentic output
(so no other cell is re-run) → insert → write back with `.replace("\n","\r\n")` (the **CRLF
trap**: nbformat writes LF, the stored file is CRLF). Insert multiple sections at their
**original** indices in **descending** order — a lower-index insert shifts higher content
uniformly, so no shift arithmetic. Keep each code cell **self-contained** (re-imports what it
needs; relies only on `plt`/`np` from setup) so top-to-bottom execution holds. Prefer **static**
banked-figure + readout cells over `interact` widgets (the kernel-wedge hazard
[[notebook-kernel-wedge-rootcause]]; the app owns interactivity).

**Why / the load-bearing trap:** `NotebookClient.execute()` writes `outputs` + `execution_count`
**back into the cell objects it runs** — so passing the real `nb.cells[3]` setup cell into the
temp notebook **mutates cell 3 in place**, silently corrupting it. The original
`outputs/probe_unified_kv/insert_nb.py` does exactly this and only "got lucky" because the setup
cell's print output is deterministic (re-execution reproduced it). **FIX: `copy.deepcopy(setup_cell)`
before executing.** And **hash-guard**: snapshot `sha256(json.dumps(cell,sort_keys=True))` of every
original cell before, re-check after — this caught the mutation. Markdown-only edits (e.g. an
epilogue tweak) need no kernel and no re-run of `test_steel_notebook` (markdown cells don't execute);
re-run the notebook test only when a **code** cell changed.

**How to apply:** placement that avoids renumbering keeps the guard absolute (no existing cell
changes) — use `###` sub-sections + letter-suffix `##` numbers, and grep `README.md` /
`steel/README.md` / `docs/` / `gallery.py` for `§\d` cues before touching any number. After adding a
demo's notebook/app surface, update the `CATALOG` cues in `gallery.py` ([[gallery-page]]),
regenerate (`python -m steel.gallery`), and mirror the README guided-tour "Also interactive" column.
