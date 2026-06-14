---
name: making-notebook-built
description: "Front-end teaching notebook (making.ipynb, Slice 2b) BUILT — the ore→billet→defects twin of steel.ipynb; shared retry-wrapped harness"
metadata:
  node_type: memory
  type: project
---

**Notebook/app backfill — Slice 2b (the front-end teaching notebook) BUILT ✓ 2026-06-14** ("commit
what is uncommitted and then Slice 2b … a separate batch by design: it carries the kernel-wedge
flakiness and needs its own retry-wrapped test harness"). `steel/making.ipynb` (44 cells, 13 banked
figures) + `tests/test_making_notebook.py` + the extracted `tests/_notebook_exec.py`. **Closes the §7
notebook/app backfill** (Slice 2a = the consequences app; this = the notebook). No engine, no ADR, no
constant — fast lane unchanged at **829** (the test is `@slow`, no fast tests added). Amends
[[consequences-app-built]] / [[making-app-built]]; companion to [[gallery-page]] / [[upstream-pr-filed]].

**Scope — user-confirmed FULL front-end make→break in ONE notebook** (not making-only). The advisor's
crux: the deferred list names exactly one artifact ("the front-end teaching notebook"), `steel.ipynb`
is one notebook for the *whole* back end, and the gallery already tags the impurity consequences
"(front-end)" — so the symmetric deliverable is one notebook: *ore → billet → and what goes wrong*
(F1 reduction → `Heat` spine → F2 refining + slag → F3 ladle → F4 casting + solidification, then the
six defect consequences). The **apps** were kept separate three times ("separate, not appended") — but
that principle was about paper-thin `main()` focus, **not narrative**; a linear teaching notebook is a
different object and the make→break arc is a natural single read. Asked the user before sinking the
hours (advisor flagged it as the one decision worth a confirm) → "Full front-end".

**DURABLE — compute reuse: the notebook imports the SAME tested readout helpers the apps use.**
`from steel import app_making as M, app_consequences as C` is bare-install-safe (Streamlit is lazy
inside `main()`), so each `interact` callback and static verdict calls `M.spine_readout` /
`C.tme_readout` etc. — **no duplicated scenario logic**, and the deliberately-restricted TME grade set
(`C.TME_GRADES` = 4140/8620/1045, the Slice-2a landmine: never surface an input the model excludes)
comes along **for free** (no re-typed constant to drift). House style otherwise unchanged from
`steel.ipynb`: a **direct** compute cell banks each section's `demo_*.compute()` + `plots.*` figure,
`interact` is sugar — load-bearing because `ipywidgets.interact` swallows exceptions into an `Output`,
so a validated call living only in an interact would never reach the smoke test.

**DURABLE — the execution smoke test checks "runs clean", NOT verdict correctness; bank + READ the
outputs.** `test_making_notebook.py` only asserts no cell raises (`allow_errors=False`). A real
semantic bug slipped through it: the spine `_mark(bad)` helper (✗ if the heat FAILED) was called with
`_mark(not soft_core)` in the spine cells only → the banked stdout read "✗ on-spec through-hardens / ✓
under-dosed soft core" (inverted). Caught by **dumping every cell's banked stdout and reading the 13
verdict blocks against the known hero numbers**, not by the green test. Every other section passed the
flag directly and was correct. Fixed in the generator, regenerated, re-banked, re-verified.

**Harness — extracted, not duplicated (the advisor's other crux).** "Its own retry-wrapped harness" =
*covered by* the retry, not a 190-line copy that drifts. Pulled `_execute_once` / `execute_with_retry`
/ the child `__main__` notebook executor + the importorskip/kernelspec gates + the CI skip into
`tests/_notebook_exec.py`; both `test_steel_notebook.py` and the new `test_making_notebook.py` are now
~25-line thin call sites. **The load-bearing fix: timeouts are PER-NOTEBOOK parameters, not constants.**
The old `_OUTER_TIMEOUT = PER_CELL_TIMEOUT + 30` conflated per-cell with whole-notebook and was tuned
for the ~7 s back-end notebook; `making.ipynb` runs **~16 s clean** (measured twice; slowest cells ~5 s
= the latent-heat solidification solve + the spine/ladle/casting `heat_treat`s), so a clean run could
have been misclassified as a hang → 5× retry → false failure. Sized it: making = per_cell 60 / outer
120; steel kept at 45 / 75. Both stay `@slow` + `xdist_group("heavy")` (one slow-tail worker → never
two kernels in parallel) + the `skip_in_ci()` gate. Both notebook tests pass through pytest (~44 s).

**Gallery/README wiring.** Front-end CATALOG topics are all tagged "(front-end)" / "Front-end spine",
so `_card_html` keys the 2nd notebook URL (`MAKING_NOTEBOOK_URL`) off `"front-end" in e.topic.lower()`
— **no per-entry field, no 13× repetition**. All 13 front-end cards now §-link the making notebook
(§F1/§spine/§F2a/§F2b/§F3/§F4a/§F4b/§D1–§D6); the "ways to explore" Notebook card + footer surface both
notebooks; drift-guard regenerated/green. Both READMEs updated (run command, Notebooks bullet, the 13
guided-tour rows' *Also interactive* column, the steel/README dev-pointer + Slice-2b "built ✓" note),
and the plan §7 gets an "as built — Slice 2" annotation closing both halves. The
one-`Heat`-through-the-whole-run **integration capstone** stays the separate larger item.
