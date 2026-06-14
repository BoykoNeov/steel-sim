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
> dual-use-socket edge drain, and the in-kernel recovery) and **NOT-CONFIRMED** (the reply-send as
> the *in-kernel* trigger; the exact zmqstream line) — please treat them differently.
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

### Suspected trigger: the reply-send on the dual-use shell socket

The FD *mechanism* is measured; what is **not** confirmed is that it is the in-kernel trigger.
Two of three links are established, one is not:

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

- **(B) NOT confirmed in-kernel:** that the strands we caught were *actually* triggered by a
  reply-send. We could not isolate the formation race below the application layer (a raw
  DEALER/ROUTER reproducer ran 9,600 messages with **zero** strands), and our instrument observes
  the *aftermath*, not the formation instant. So the reply-send is a **strongly-suggested**
  trigger, not a proven one.

Suggested sequence: a new `execute_request` arrives just as the kernel sends the previous cell's
`execute_reply` on the same ROUTER; the reply `send_multipart` drains the read edge (A); because
that send is not `ZMQStream`-mediated, the read side is never re-armed and the request strands.
It fits that the loss is on the request-**intake** path, that the kernel produced replies for
every cell *before* the wedged one and none for it, and that heavier `comm`/reply traffic is
needed to hit it.

**Confirming (B):** instrument the shell-channel thread to log whether each caught strand is
immediately preceded by a `send_multipart` on the shell socket; and/or apply targeted fix #1 and
check the wedge rate goes to zero — a clean fix that eliminates the wedge would itself confirm
the trigger.

---

## Why `WindowsSelectorEventLoopPolicy` does not fix it

It is the standard suggestion for the *client* Proactor warning, but the **kernel already runs a
selector loop** (ipykernel forces it) and still loses the edge. Forcing it has no bearing on the
kernel side, and on the client side it trades the random wedge for a deterministic
timeout-length stall on every run. Not a fix.

## Suggested fixes (in order of shippability)

1. **ipykernel — re-arm the read after an out-of-band send (targeted, likely shippable).**
   After `_send_on_shell_channel`'s `send_multipart` on the shell ROUTER, re-check the stream's
   read readiness and reschedule its handler, e.g. schedule
   `shell_stream._handle_events(shell_stream.socket, 0)` on the shell-channel loop (the same
   thing `_update_handler` does). This closes the dual-use-socket window without polling.
   *Premise: the reply-send is the trigger — measured as a mechanism (§1.5, A), provable in source
   (the raw send is on the stream's own socket), but not yet confirmed as the in-kernel cause (B).
   Applying this fix and seeing the wedge vanish would itself confirm the trigger.*
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
