---
name: notebook-kernel-wedge-rootcause
description: "Steel steel.ipynb smoke-test wedge ROOT-CAUSED 2026-06-10: upstream pyzmq/asyncio-on-Windows lost-execute_reply (load- & version-independent, content-innocent); mitigated by retry-on-wedge in test_steel_notebook.py; Selector-loop 'fix' is WORSE; CI skip stays (separate Ubuntu hang)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1c1b85d3-9634-464d-982b-28a8a3fb21a9
---

> **CORRECTION 2026-06-14 (direct measurement revised the *mechanism*, not the symptom).**
> A follow-up dug in with client-side bridge tracing (`select()` entry/return on the tornado
> selector thread + a safe main-loop `getsockopt(EVENTS)` probe per socket) and kernel-CPU
> sampling, on an isolated venv. Findings, in order of confidence:
> - **No version fixes it** — identical ~33 % on tornado **6.5.5 *and* 6.5.7**; pyzmq's async
>   path is byte-frozen since 27.1.0; jupyter_client/ipykernel bumps are off the path.
> - **tornado is exonerated** — at a wedge its selector thread is *correctly blocked* in
>   `select()` on the shell fd for the full 45 s; it isn't dropping a wake, it never gets one.
> - **The "missed FD-readiness one layer below nbclient" (client-side pyzmq/tornado) claim is
>   NOT supported.** A probe read `getsockopt(EVENTS)` 318× across the silence and saw POLLIN
>   **never** — the reply is *not sitting at the client socket*; there is no edge to lose.
> - **"kernel idle (0 % CPU)" is CONFIRMED.** So the loss is **between the idle kernel's send
>   and the client recv queue** — at/below the kernel's message-send path or the transport —
>   *not* the client asyncio/FD layer. Deeper and less tractable; still no clean in-code fix.
> - **No connection flap (Rung-0 socket-monitor probe, 2026-06-14).** A zmq socket monitor armed
>   on the client SHELL socket (read by a sync shadow-context thread, independent of the suspect
>   loop) saw **zero transport events across all three 45 s silences** (3/8 runs wedged, ~37 %, so
>   the monitor doesn't suppress the bug). DISCONNECTED/CONNECT_RETRIED appear only at *post-wedge
>   teardown* — identical to a clean run's shutdown — so the connection stays nominally healthy and
>   the reply is lost with **no reset**. This rules out a transient shell-channel flap; it does
>   **not** discriminate a kernel-send-stall from a transport-buffer loss (a monitor reports
>   connection *state*, not message *delivery* — there is no "message dropped" event). Both remain
>   open for a Rung-1 raw-pyzmq reproducer.
> - **Bare transport exonerated (Rung-1 standalone-pyzmq reproducer, 2026-06-14).** A no-Jupyter
>   DEALER/ROUTER rig reproducing the real loop *asymmetry* — verified from source: **ipykernel's
>   forced Selector sender** (`_init_asyncio_patch` overrides the Proactor policy on Windows) ×
>   **Proactor client running the same `add_reader` tornado shim** (the documented `zmq/_future.py`
>   warning, reproduced) — over loopback TCP with strict request/reply (which makes the sender
>   quiescent right after each send, the "kernel goes idle" trigger, for free). It ran **240 runs /
>   9 600 cells across three escalating-fidelity variants** (minimal; + GC/thread churn; + a
>   figure-sized **iopub firehose** of ~0.5–1 MB/cell fired on the **one shared libzmq io_thread**
>   right before each shell reply, with a concurrent client drain) and saw **zero wedges** — where
>   the real stack wedges ~33 %/run (~75 expected). So bare libzmq transport, the asyncio/Proactor
>   readiness layer, **and** shared-io_thread contention are all exonerated: the lost reply does
>   **not** reproduce below the Jupyter/kernel *application* layer. Combined with Rung-0 (connection
>   healthy) and the earlier POLLIN-never, this narrows the locus **by elimination** to the
>   application send/receive machinery (ipykernel's ZMQStream/Session send path; jupyter_client) —
>   not the wire. **Advisor crux** (load-bearing, twice): the sender must *not* be reliable-by-
>   construction (a warm sync loop hides the suspected idle-after-send stall — the strict cadence
>   supplies the idle window instead); and POLLIN-never is *consistent with* (not against) a stalled
>   **shared io_thread**, which is why the iopub firehose was the decisive variant. Pinning the
>   residual locus needs a **kernel-side Rung-2** (instrument ipykernel), now done (next bullet).
> - **Kernel-side RECEIVE path implicated — the "lost reply" is actually an unprocessed REQUEST
>   (Rung-2 kernel-instrumented reproducer, 2026-06-14). This OVERTURNS the send-path attribution
>   above.** A `sitecustomize.py` injected into the kernel subprocess via `PYTHONPATH` monkeypatched
>   ipykernel's reply *and* request path; both client and kernel logs were captured on a wedge.
>   ipykernel 7's shell socket is read on a dedicated **shell-channel thread** that forwards each
>   request over an inproc PAIR to the main thread; the main thread runs the cell and sends
>   `execute_reply` back the same way. On a wedge: (a) the kernel's **reply send path is clean** —
>   for every cell it processes, `execute_reply` goes main→inproc PAIR→shell-channel-thread→shell
>   ROUTER and the **ROUTER `send_multipart` completes** (libzmq accepts the bytes); (b) the kernel
>   produces **exactly N replies for the N code cells *before* the wedged one and NONE for the wedged
>   cell** — it never runs it; (c) the kernel's shell-channel thread **never delivers the wedged
>   request to its `on_recv` callback** (no instrumented `RECV_SHELL_REQ` fires after the last
>   reply); (d) meanwhile the **client successfully flushed that `execute_request` into libzmq** (the
>   sync DEALER `send_multipart` *and* `Session.send` both returned). By the pre-registered rule +
>   Rung-1 (the wire reliably moves bytes once a sender's libzmq accepts them), the request **reached
>   the kernel's libzmq recv queue but the kernel's shell-channel event loop never woke to read it**
>   = **H-kernel**: a kernel-side **missed inbound FD-readiness** on the shell ROUTER intake — the
>   *receive-side mirror* of the client-side Proactor `add_reader` miss, on the kernel's shell-channel
>   thread. This finally explains the old **client POLLIN-never**: no reply was ever sent *because the
>   request was never picked up*. Evidence: **4 wedges** over two instrumented real-notebook runs (one
>   count-based 2/2, one full client+kernel 2/6 ≈ the historical ~33% → instrumentation does **not**
>   suppress it, no Heisenbug); an **uninstrumented** real-notebook control wedged on run 0 (bug
>   alive); a **trivial-cell** notebook ran **50/50 clean** (the matplotlib/ipywidgets-heavy real
>   notebook — far more inbound shell traffic incl. widget `comm` messages — is needed to hit the
>   race; a sterile notebook does not). **Advisor crux:** don't swap one premature attribution
>   (send-path) for another — the client+recv-callback variant was required to *measure* the side, not
>   infer it (the very error this banner exists to fix); H-client (client never delivered the request)
>   stayed live until the client log showed the request's send completing. **NOT established
>   (Rung-3):** *why* a forced-**Selector** loop (ipykernel's `_init_asyncio_patch`, where `add_reader`
>   is native) misses an inbound POLLIN on the shell-channel thread; the H-kernel localization rests on
>   the Rung-1 wire-reliability inference, **not** a direct kernel-side `EVENTS`/POLLIN read (hazardous:
>   cross-thread `getsockopt` on a wedged-loop socket, and the wedged loop can't schedule the probe).
> The retry mitigation remains correct. The original paragraph below is the *symptom* record;
> read its mechanism attribution as superseded — and note the Rung-2 refinement: the failure is on
> the kernel's request-**intake** path, not its reply-send path.

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
