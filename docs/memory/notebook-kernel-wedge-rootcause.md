---
name: notebook-kernel-wedge-rootcause
description: "Steel steel.ipynb smoke-test wedge ROOT-CAUSED 2026-06-10: upstream pyzmq/asyncio-on-Windows lost-execute_reply (load- & version-independent, content-innocent); mitigated by retry-on-wedge in test_steel_notebook.py; Selector-loop 'fix' is WORSE; CI skip stays (separate Ubuntu hang)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1c1b85d3-9634-464d-982b-28a8a3fb21a9
---

The `slow` `test_steel_notebook` wedge (a cell that runs in <1 s hanging past its
timeout) was **root-caused 2026-06-10** to an **upstream pyzmq/asyncio-on-Windows
lost-`execute_reply`**: the kernel finishes the cell and goes **idle (0 % CPU)** but the
client never receives the reply (a *missed FD-readiness notification* one layer below
nbclient). Diagnosed by an instrumented repro loop (fresh-subprocess executor +
`record_timing` + kernel-CPU sampling + `faulthandler`).

Three properties, each killing a wrong theory the old docs implied:
- **Load-INDEPENDENT** — ~24 % wedge rate in *bare repetition with zero other load* (80-run
  loop). The inherited "wedges under full-suite load" framing was **wrong**; load only
  jiggles the race window. A 3 s→∞ (binary, not proportional) stall = deadlock/lost-message,
  never CPU starvation.
- **Content-innocent** — the wedged cell index *wanders* run to run (kernel-idle proves it
  isn't the notebook's code). Not a content bug; don't chase it as one.
- **Version-INDEPENDENT** — reproduces identically on Python **3.13 and 3.14** (same
  nbclient 0.11), so NOT a 3.14 regression; pinning the interpreter won't help.

**DON'T "fix" it with `WindowsSelectorEventLoopPolicy`.** pyzmq's own warning recommends it,
and it does remove the Proactor shim's *drop* — but the Selector loop then **misses the
socket-readable edge and adds a full timeout-length stall to EVERY run** (verified: clean but
~20–30 s at a 12 s cell-timeout, ~90 s at a 90 s timeout → two stalls would blow the 180 s
outer guard). Strictly worse and *dangerous* at the production timeout. Empirically falsified
the advisor's "Selector = 0/N fast" prediction; surfaced and reconciled.

**Mitigation (user-chosen 2026-06-10): retry-on-wedge** in `steel/tests/test_steel_notebook.py`.
The child entry exits **2 on the retryable `CellTimeoutError` wedge** vs **1 on a fatal
`CellExecutionError` content bug** (disjoint exception types — `CellTimeoutError` derives from
`CellControlSignal`, not `CellExecutionError`); the parent retries only the wedge, up to
`MAX_ATTEMPTS=5` with a tight `PER_CELL_TIMEOUT=45 s` per attempt (real cells <1 s, the wedge
never recovers, so a short bound detects it cheaply without false-positiving). 24 %→`0.24⁵`≈0.08 %.
**Verified 25/25** with retries observed firing (4 runs wedged on attempt 1, all recovered on
attempt 2; verification ran at budget 4 — the shipped 5 is strictly safer, matching the chosen option). Keeps the fast 7 s clean path.

**`_SKIP_IN_CI` STAYS.** The CI (Ubuntu/Linux) kernel hang from commit a00f66a is a **separate,
unreproduced** beast — Linux uses the selector loop and **cannot** hit the Proactor shim above,
so this Windows root-cause does *not* address it. "REMOVE once root-caused" now scopes to that
Ubuntu hang specifically. Amends the stale flake note in [[steel-grain-physics-deferred]].

**Portable handoff** (other BigSim repos share the `test_*_notebook.py` child-subprocess pattern —
the chip notebook hit "the same wedge", so siblings likely have this or a lookalike) =
`docs/handoffs/notebook-kernel-wedge.md`: recognition checklist → the **kernel busy/idle/startup
3-way triage** (busy=heavy cell/fix-the-cell, idle=this comms-race/retry, never-reaches-cell-1=
startup) → the retry-on-wedge exit-code pattern → a throwaway diagnostic harness to confirm before
applying. Committed to steel-sim so it travels by copy.
