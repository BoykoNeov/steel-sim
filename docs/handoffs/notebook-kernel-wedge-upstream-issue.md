# Upstream issue draft: intermittent lost `execute_request` on the shell channel (Windows)

> **Status:** draft, ready to file. **Where to file:** primarily **ipykernel**
> (`ipython/ipykernel`) — that is where the user-visible hang occurs and where the cleanest
> fix lives — with a **cross-reference to pyzmq** (`zeromq/pyzmq`), since the layer that loses
> the message is `zmq.eventloop.zmqstream.ZMQStream`'s edge-trigger handling. Trim the
> ipykernel-specific framing if filing against pyzmq.
>
> Source of this report: a five-rung diagnosis recorded in
> `docs/memory/notebook-kernel-wedge-rootcause.md` and `docs/handoffs/notebook-kernel-wedge.md`.
> Everything below is split into **MEASURED** (reproduced this session — the FD mechanism, the
> dual-use-socket edge drain, the in-kernel recovery, and now a **validated fix**: a re-arm after
> the reply send drives the wedge 0/20 where control/sham are ~25%) and **NOT-CONFIRMED** (only the
> exact zmqstream line that loses the edge) — please treat them differently. The reply-send trigger,
> earlier "strongly-suggested", is now **confirmed** by the fix experiment (§4).
>
> **Before filing:** dup-search both trackers for an existing report — pyzmq and ipykernel for
> `ZMQ_FD` edge / "lost execute_request" / "ZMQStream missed event" / "kernel hang Windows
> execute_reply" — so this lands as a comment on an open issue or a clean new one, not a duplicate.

---

## Title

**ipykernel 7 on Windows intermittently drops an `execute_request`: a coalesced `ZMQ_FD` read
edge on the shell-channel `ZMQStream` is never re-armed, so the kernel never runs the cell and
the client times out waiting for `execute_reply`.**

## TL;DR

On Windows, executing a notebook headless (`nbclient`) intermittently hangs (~30 % of runs in
our measurements): a cell that normally runs in <1 s blows past its timeout with
`CellTimeoutError` / `Timeout waiting for execute reply`. At the hang the **kernel is idle
(0 % CPU)** and the **client never receives the reply**. We traced it into the kernel: the
`execute_request` *does reach the kernel's shell ROUTER libzmq recv queue*, but the
shell-channel `ZMQStream` **never delivers it to `on_recv`** (`Kernel.shell_channel_thread_main`),
so the cell never runs and no reply is ever sent. The request sits **queued-but-unread on a registered fd that `select()` reports
non-readable** — the libzmq `ZMQ_FD` edge-trigger trap. Forcing
`WindowsSelectorEventLoopPolicy` does **not** fix it (the kernel already runs a selector loop).
**A targeted re-arm of the shell `ZMQStream` read after the out-of-band reply send eliminates the
hang (0/20 vs a ~25 % control/sham baseline, same session) — fix #1 below, validated (§4).**

## Environment

- Windows 11 (26200); reproduced on **Python 3.14.3 and 3.13** (version-independent).
- `pyzmq` 27.1.0, `libzmq` 4.3.5
- `ipykernel` 7.2.0, `jupyter_client` 8.9.0, `tornado` 6.5.5, `nbclient` 0.11.0
- Default Windows asyncio policy on the client (Proactor); ipykernel forces
  `WindowsSelectorEventLoopPolicy` for the kernel via `_init_asyncio_patch`.

## Symptom

- A `@slow` notebook smoke-test (execute the notebook in a fresh kernel subprocess) hangs
  intermittently; **which cell** hangs wanders run to run (content-innocent).
- `nbclient.exceptions.CellTimeoutError`; `traitlets ERROR Timeout waiting for execute reply`.
- **Load-independent** (~30 % even in bare repetition with zero other load).
- The stall is **binary** (fast-or-infinite), the fingerprint of a lost message, not throughput.
- Heavier notebooks (matplotlib / ipywidgets `comm` traffic) hit it; a trivial notebook ran
  50/50 clean — more inbound shell traffic is needed to hit the race.

---

## What is MEASURED

### 1. The `ZMQ_FD` re-signalling rule (raw pyzmq, no Jupyter — deterministic)

`getsockopt(ZMQ_EVENTS)` itself **consumes/drains the edge-triggered `ZMQ_FD`**, and **while a
backlog is already pending (`EVENTS` nonzero) a fresh arrival does not produce a new edge**.
Minimal, self-contained reproduction:

```python
import select, time, zmq
def readable(fd): return bool(select.select([fd], [], [], 0)[0])

ctx = zmq.Context()
a = ctx.socket(zmq.PAIR); b = ctx.socket(zmq.PAIR)
a.bind("tcp://127.0.0.1:5703"); b.connect("tcp://127.0.0.1:5703"); time.sleep(0.3)
fd = b.getsockopt(zmq.FD)
b.getsockopt(zmq.EVENTS)                         # clear any connection-setup edge
assert not readable(fd)                          # clean baseline: non-readable, no messages
assert not (b.getsockopt(zmq.EVENTS) & zmq.POLLIN)

a.send(b"m1"); a.send(b"m2"); time.sleep(0.2)
assert readable(fd)                              # the messages set the fd edge
b.getsockopt(zmq.EVENTS)                          # <-- reading EVENTS drains the edge
assert not readable(fd)                           # fd no longer readable...
assert b.getsockopt(zmq.EVENTS) & zmq.POLLIN      # ...while POLLIN stays set, 0 recv'd

a.send(b"m3"); time.sleep(0.2)                     # a 3rd message arrives while a backlog is pending
assert not readable(fd)                            # NO new edge (EVENTS already nonzero)
assert [b.recv(zmq.NOBLOCK) for _ in range(3)] == [b"m1", b"m2", b"m3"]  # all 3 truly queued

assert not (b.getsockopt(zmq.EVENTS) & zmq.POLLIN) and not readable(fd)   # drained to empty
a.send(b"m4"); time.sleep(0.2)
assert readable(fd)                                # 0->nonzero transition re-arms the edge
```

Consequence: **once a read edge is consumed without fully draining the socket, the queued
message strands** — the fd stays non-readable, and (crucially) **no later arrival re-arms it**,
because there is no `0 -> nonzero` `EVENTS` transition. The strand is *terminal*. This matches
the "kernel idle, no further progress" symptom exactly.

### 1.5 An out-of-band **send** on a dual-use socket drains its **read** edge (raw pyzmq)

The same drain happens on a `send` — measured on a **ROUTER** (the kernel's shell socket type):
with a request pending unread, a `send_multipart` on the *same* socket leaves the read edge
gone while the request is still queued-but-unread.

```python
a = ctx.socket(zmq.DEALER); a.setsockopt(zmq.IDENTITY, b"A")
b = ctx.socket(zmq.ROUTER)
b.bind("tcp://127.0.0.1:5704"); a.connect("tcp://127.0.0.1:5704"); time.sleep(0.3)
bfd = b.getsockopt(zmq.FD)

a.send(b"hello"); time.sleep(0.2)                  # warmup: ROUTER learns route 'A', clear setup edges
assert b.recv_multipart() == [b"A", b"hello"]
b.getsockopt(zmq.EVENTS)
assert not readable(bfd) and not (b.getsockopt(zmq.EVENTS) & zmq.POLLIN)   # clean baseline

a.send(b"req1"); time.sleep(0.2)                   # a new request arrives, UNREAD
assert readable(bfd)                               # read edge is set

b.send_multipart([b"A", b"reply"]); time.sleep(0.05)   # OUT-OF-BAND send on the same ROUTER
assert not readable(bfd)                           # <-- the send DRAINED the read edge
assert b.getsockopt(zmq.EVENTS) & zmq.POLLIN       # ...while POLLIN stays set...
assert b.recv_multipart(zmq.NOBLOCK) == [b"A", b"req1"]   # ...and the request was still queued
```

This is the documented `ZMQ_FD` corollary ("after `zmq_send` the socket may become readable
without triggering a read event") shown concretely: **a send on a socket that something else is
reading via an edge-triggered fd can strand a concurrently-arrived request.**

### 2. The request is queued-but-unread at the hang (in-kernel)

Instrumenting the kernel subprocess (PYTHONPATH `sitecustomize`) on the shell-channel thread at
a hang, every time:

- shell socket is a **ROUTER**, its `ZMQ_FD` is **registered** in the loop's selector
  (`loop._selector.get_map()`), and the loop is a **native** `_WindowsSelectorEventLoop` /
  `SelectSelector` (no Proactor selector-thread shim — that is client-only).
- `socket.EVENTS == 3` (`POLLIN` set) while `select([fd]) == False` — the coalesced-edge state
  from §1, reproduced in the live kernel.
- The client's `execute_request` `Session.send` **completed**, but `on_recv`
  (`Kernel.shell_channel_thread_main`) **never fired** for it.
- A **lone `getsockopt(EVENTS)` repeated ×3** leaves `POLLIN` set / fd non-readable / `on_recv`
  unchanged — reading EVENTS alone does **not** recover it.

### 3. Re-running the registered read handler recovers it; merely waking the loop does not

A self-rescheduling watchdog on the shell-channel loop (loop-owned thread, so socket ops are
safe), three arms × **20** real notebook runs each:

| Arm | Action on the shell-channel loop | Wedged |
| --- | --- | --- |
| control | none | **6 / 20** |
| bare | reschedule only — wake `select()` every 0.2 s, never touch the socket | **8 / 20** (≈ control) |
| drain | on a >3 s `on_recv` gap, re-fire the **registered** reader handle: `loop._selector.get_map()[fd].data[0]._run()` (which is tornado's `_handle_events` → `ZMQStream._handle_events`) | **0 / 20**, **6 strands caught, all 6 recovered** |

- **bare ≈ control** ⇒ merely waking `select()` does **not** recover (and the timer's presence
  does not suppress the bug) — it is not a stale/over-long `select()`; the OS edge is genuinely
  gone.
- **drain** recovers every strand. Per-strand log (representative, identical ×6):

  ```
  STRAND gap=3.07s EVENTS=3 POLLIN=True fd_readable=False
    | lone-getsockopt x3 -> POLLIN/readable=[(True,False),(True,False),(True,False)]
      on_recv_count 41->41 (unchanged across getsockopts)
    | reader._callback=BaseAsyncIOLoop._handle_events  reader._args=(fd, READ)  fd_is_ROUTER_fd=True
  STRAND RECOVERED: on_recv fired (41->43) within the +0.3s poll of reader._run()
  ```

  The `on_recv` count jumps by ≥2: `reader._run()` recvs one multipart, then `ZMQStream`'s own
  `_update_handler` reschedule drains the rest — i.e. **multiple messages had coalesced behind
  the one lost edge**, exactly as §1 predicts. (`+0.3 s` is the poll interval, an upper bound,
  not the latency.) The watchdog's caught-strand count (6) matches the natural wedge band
  (control 6, bare 8), so it is **catching** the natural strands, not manufacturing them.

So the active ingredient is **re-running the read handler** — not reading `EVENTS`, not waking
the loop.

### 4. Re-arming after the **reply send** eliminates the wedge (validated fix, confirms the trigger)

§3's watchdog *recovers* a strand reactively (it polls, so it heals a strand regardless of how it
formed). This section tests the **preventive** fix and thereby the *cause*: re-arm the read
**immediately after each out-of-band reply send**, and only send-caused strands can be prevented —
so `0/N` here means the reply-send *is* the trigger. A PYTHONPATH-`sitecustomize` monkeypatched the
single raw send (`SubshellManager._send_on_shell_channel` — every reply, main + subshells, funnels
through it) to schedule, after the send, the **exact reschedule `ZMQStream._update_handler` already
runs internally**: `add_callback(lambda: shell_stream._handle_events(shell_stream.socket, 0))`. (The
prototype resolved the stream via `Kernel.instance().shell_stream` at send time; fix #1 below gives
the equivalent constructor-threaded form — what is validated here is the re-arm **effect**, not that
exact diff.) Three arms × **20** real `steel.ipynb` runs, one session:

| Arm | Action after the reply `send_multipart` | Wedged |
| --- | --- | --- |
| control | none (no patch) | **5 / 20** |
| sham | same overhead + lazy kernel/stream lookup + `add_callback(lambda: None)` — **no re-arm** | **5 / 20** (≈ control) |
| fix | `add_callback(lambda: shell_stream._handle_events(shell_stream.socket, 0))` | **0 / 20** |

- **sham ≈ control** ⇒ the patch-site timing perturbation and the scheduled callback are **not** the
  cure (the sham noop is *send-gated*, not a periodic timer, so it cannot incidentally recover by
  waking `select()`). The active ingredient is the **re-arm** alone.
- **fix = 0/20** against the pooled ~25 % null (control+sham 10/40): `P(0/20) ≈ 0.75²⁰ ≈ 0.003`. The
  bug was alive all session (both controls 5/20); the fix arm ran last on the same machine.
- **Engagement instrumented:** `mismatch = 0` across **1082** sends (sham 528 + fix 554) ⇒ the
  dual-use invariant `shell_stream.socket is self._shell_socket` held on **every** send; no errors;
  `fix` produced 20 genuine clean exits (no content-error/hang masking).

This brackets the mechanism end-to-end: §1.5 measured "the reply send drains the read edge", §4
measures "re-arming after that send closes the window". The re-arm fires after *every* send, so on
its own one could read it as "drains the socket often enough to catch strands however they form" —
but **the kernel goes idle (0 % CPU, no further sends) once a request strands** (measured: at the
hang the kernel is idle, and the synchronous client waits for the reply before sending the next
request, so no send follows a strand): the re-arm that prevents *each* wedge is the one after the **strand-adjacent**
send, which places strand formation at the reply-send. And that send is **the only** un-mediated
operation on the shell ROUTER that can drain its read edge — verified by grep of the kernel path:
there is **no `getsockopt(EVENTS)` on the shell socket at all**; the other `getsockopt`s on it are
`LAST_ENDPOINT` (one-time setup) and `ROUTING_ID` (debugger-only), neither of which touches the
event signaler. So the **reply-send is the operative in-kernel trigger**.

---

## Mechanism

`ZMQStream` already knows about the edge-trigger trap. `ZMQStream._handle_events`
(`zmq/eventloop/zmqstream.py`) reads `socket.EVENTS` (which drains the fd edge, per §1), then
`_handle_recv` recvs **one** multipart with `NOBLOCK`, then `_rebuild_io_state` →
`_update_handler` re-reads `socket.events` and **conditionally** reschedules itself:

```python
def _update_handler(self, state):
    if self.socket is None:
        return
    if state & self.socket.events:
        # events still exist that haven't been processed
        # explicitly schedule handling to avoid missing events due to edge-triggered FDs
        self.io_loop.add_callback(lambda: self._handle_events(self.socket, 0))
```

That `add_callback` reschedule is the **only** edge-trap defense, and it runs **only at the tail
of `_handle_events`**. What we measured at the wedge is narrower than a specific code path: **the
read side is never driven to a successful recv for the queued request — `on_recv` never fires
even though the message is in the recv queue and `EVENTS&POLLIN` is set.** We did *not* wrap
`_handle_events`/`_handle_recv`, so we cannot distinguish "`_handle_events` was never called for
that edge" from "it was called and its `recv_multipart(NOBLOCK)` raced an `EAGAIN`
(zmqstream.py:619-623) with the `_update_handler` re-check then missing it" — different lines in
the same file; we leave the exact localization to maintainers. Either way **the read side ends up
un-re-armed on a registered fd with the message stranded**, and re-running `_handle_events` (our
§3 `reader._run()`) recovers it.

### Confirmed trigger: the reply-send on the dual-use shell socket

The FD *mechanism* is measured, and the reply-send as the in-kernel trigger is now **confirmed by
the fix experiment (§4)**. All three links hold:

- **(A) MEASURED (§1.5):** an out-of-band `send` on a socket read via an edge-triggered fd drains
  its read edge, stranding a concurrently-queued message.
- **MEASURED (from source):** ipykernel 7's shell ROUTER socket is **dual-use** on the
  shell-channel thread — `ZMQStream` reads requests off it (`kernelbase.py`:
  `self.shell_stream.on_recv(self.shell_channel_thread_main)`), while replies go back over the
  **same socket via a raw `send_multipart`** that bypasses the stream (`subshell_manager.py`):

  ```python
  def _send_on_shell_channel(self, msg) -> None:
      assert current_thread().name == SHELL_CHANNEL_THREAD_NAME
      self._shell_socket.send_multipart(msg)     # raw send on the ZMQStream's own socket
  ```

- **(B) CONFIRMED in-kernel (§4):** re-arming the read *after the reply send* drives the wedge from
  ~25 % (control, sham) to **0/20**, while a same-overhead noop (sham) does not — so the strands are
  send-caused. We still cannot watch the formation *instant* (a raw DEALER/ROUTER reproducer ran
  9,600 messages with zero strands, and our instrument observes the aftermath), but preventing the
  strand by closing the post-send window is a causal test, not just correlation.

Sequence: a new `execute_request` arrives just as the kernel sends the previous cell's
`execute_reply` on the same ROUTER; the reply `send_multipart` drains the read edge (A); because
that send is not `ZMQStream`-mediated, the read side is never re-armed and the request strands.
It fits that the loss is on the request-**intake** path, that the kernel produced replies for
every cell *before* the wedged one and none for it, and that heavier `comm`/reply traffic is
needed to hit it — and §4's fix (re-arm after the send) closes exactly this window, to 0/20.

---

## Why `WindowsSelectorEventLoopPolicy` does not fix it

It is the standard suggestion for the *client* Proactor warning, but the **kernel already runs a
selector loop** (ipykernel forces it) and still loses the edge. Forcing it has no bearing on the
kernel side, and on the client side it trades the random wedge for a deterministic
timeout-length stall on every run. Not a fix.

## Suggested fixes (in order of shippability)

1. **ipykernel — re-arm the read after the out-of-band reply send (targeted; VALIDATED 0/20, §4).**
   After `_send_on_shell_channel`'s `send_multipart` on the shell ROUTER, schedule the shell stream's
   read handler on the shell-channel loop — the same edge-trap reschedule `ZMQStream._update_handler`
   already runs internally — closing the dual-use-socket window without polling. Thread the
   `shell_stream` (built in `kernelapp.init_kernel`) through `SubshellManager`'s constructor:

   ```diff
   --- a/ipykernel/subshell_manager.py
   +++ b/ipykernel/subshell_manager.py
   @@ def __init__(self, context, shell_channel_io_loop, shell_socket):
   +        shell_stream=None,
            ...
            self._shell_socket = shell_socket
   +        # ZMQStream that reads `shell_socket`. Replies are sent on this same socket
   +        # out-of-band below, draining its edge-triggered ZMQ_FD read edge; re-arm the
   +        # stream after each send so a concurrently-arrived request cannot strand unread.
   +        self._shell_stream = shell_stream
   @@ def _send_on_shell_channel(self, msg) -> None:
            assert current_thread().name == SHELL_CHANNEL_THREAD_NAME
            self._shell_socket.send_multipart(msg)
   +        stream = self._shell_stream
   +        if stream is not None and stream.socket is self._shell_socket:
   +            self._shell_channel_io_loop.add_callback(
   +                lambda: stream._handle_events(stream.socket, 0)
   +            )
   ```

   plus the two wiring lines (`ShellChannelThread.__init__` gains a `shell_stream` attr passed into
   `SubshellManager(...)`; `kernelapp.init_kernel` sets `self.shell_channel_thread.shell_stream =
   shell_stream` after building it). The validated `_handle_events(socket, 0)` call **is**
   `_update_handler`'s own reschedule moved to the post-send site; **`shell_stream.flush(zmq.POLLIN)`**
   (a *public* ZMQStream method ipykernel already calls in `kernelbase.py`) is the equivalent
   public-API form and is the cleaner shape for the PR.
   *Validated vs proposed: the re-arm **effect** is what ran 0/20 (§4) — the prototype resolved the
   stream via `Kernel.instance().shell_stream` inside the patched send. The constructor-threading
   above is the clean upstream form, equivalent but not the literal code that ran: the lazy `manager`
   is first built in `kernelbase.start()`, which runs after `init_kernel` sets the attr, so the
   ordering holds — reasoned, not separately run.*
2. **pyzmq — make `ZMQStream` robust to read edges consumed by un-mediated operations on its
   socket.** Document/handle that any `send`/`getsockopt(EVENTS)` on a stream's socket from
   outside the stream can strand a pending recv; consider a guarded re-check on `on_recv`
   registration and/or after sends the stream is aware of.
3. **Periodic unconditional re-check (proof-of-mechanism, NOT recommended for shipping).** Our
   `reader._run()` watchdog recovers 100 % of strands but reaches into asyncio `_selector`
   internals and private `tornado`/`pyzmq` `Handle` objects and is version-coupled — it is an
   existence proof and a diagnostic, not a fix.

## Current user mitigation (works today, mechanism-agnostic)

Re-run the fresh kernel subprocess on the wedge signature: child exit-codes distinguish the
retryable `CellTimeoutError` wedge from a real `CellExecutionError` cell bug; the parent retries
only the wedge. `~30 %` per attempt → `0.30**N` after `N` attempts. This is orthogonal to the
root cause and stays the recommended mitigation regardless of how the upstream fix lands.

## Reproduction harness

A throwaway `sitecustomize` (PYTHONPATH-injected into the kernel) that installs the
shell-channel watchdog, plus a driver that runs the notebook N× per arm, reproduces the
measurements above. Available on request; the deterministic `ZMQ_FD` snippets in §1 and §1.5 need
no Jupyter at all (raw pyzmq).
