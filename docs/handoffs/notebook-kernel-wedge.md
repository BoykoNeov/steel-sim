# Handoff: the notebook smoke-test kernel wedge (pyzmq/asyncio-on-Windows lost `execute_reply`)

**Status:** root-caused + fixed in **steel-sim** (commit `3814646`, 2026-06-10). Written to
travel: other BigSim projects share the `test_*_notebook.py` smoke-test pattern (a `slow` test
that executes the teaching notebook headless in a child process), so several likely have this
bug *or a sibling of it*. The original observation that prompted this was "the same wedge the
**chip** notebook hit."

**Audience:** whoever (human or agent) is chasing an intermittently-hanging notebook smoke-test
in a BigSim repo. Budget ~30 min to confirm, ~30 min to fix and verify.

---

## TL;DR

A `slow` notebook smoke-test intermittently hangs: a cell that runs in **<1 s** blows past its
per-cell timeout (`CellTimeoutError` / "Timeout waiting for execute reply"). On **Windows** this
is an **upstream pyzmq/asyncio bug** — the kernel finishes the cell and goes **idle**, but the
client never receives the reply (a *missed FD-readiness notification* under the default Proactor
event loop). It is **not your notebook**. There is **no clean in-code fix**; the mitigation is to
**retry the fresh subprocess** on the wedge signature. **Do not** "fix" it by forcing
`WindowsSelectorEventLoopPolicy` — that is measurably *worse*.

Before you assume you have *this* bug, run the 5-minute triage below — a notebook-test hang has
**three** distinct causes and only one of them is this one.

---

## 1. Do you have a notebook-test hang at all? (recognition)

You probably have *some* version of this if:

- A `@pytest.mark.slow` test executes a notebook headless (via `nbclient.NotebookClient`,
  usually in a child process) and **intermittently** fails or hangs.
- The failure is `nbclient.exceptions.CellTimeoutError`, often with a
  `traitlets ERROR Timeout waiting for execute reply (Ns)` line in stderr.
- A cell that is normally **fast** is the one that "timed out" — and **which** cell it is
  **changes between runs**.
- It may already be papered over: skipped in CI (`CI=true`), `@pytest.mark.flaky`, a bumped
  timeout, or a comment calling it a "documented infra flake / kernel hang."

If instead the test fails *deterministically* on the *same* cell every time, you have a content
bug, not this — stop here and fix the cell.

---

## 2. The 5-minute triage: which of THREE causes is it?

A notebook execution can hang for three mechanically-different reasons. **Reasoning can't tell
them apart — you must catch one wedged instance and look.** The single cheap discriminator is:
**when it's hung, is the kernel process pegging a CPU core, or sitting at ~0 %?**

| Observation at the wedge | Cause | Fix lives in |
| --- | --- | --- |
| Kernel **idle (~0 % CPU)**, client still waiting; reply never arrives; stall is **binary** (fast-or-infinite, not a gradual slowdown) | **Comms race** — the lost `execute_reply` *(this handoff)* | the harness (retry); upstream |
| Kernel **busy (pegging a core)** | A cell legitimately doing heavy first-run work — e.g. **pycalphad/symengine** JIT compile, or a **matplotlib font-cache** rebuild in a fresh kernel | the **cell** (warm the cache / precompute / raise *that cell's* budget) |
| Execution **never reaches cell 1** | Kernel **startup** hang (zmq handshake / kernelspec) | startup (`startup_timeout`, kernelspec) |

Two signatures that confirm the **comms-race** row specifically (i.e. *this* bug, not a lookalike):

- **`3 s → ∞`, not `3 s → 20 s`.** CPU starvation would slow a cell *proportionally*. A clean
  "fast every time, then once in a while *never* finishes" is the fingerprint of a **lost
  message / deadlock**, not throughput contention.
- **The pyzmq warning** in the child's stderr (Windows):
  `RuntimeWarning: Proactor event loop does not implement add_reader family of methods required
  for zmq. Registering an additional selector thread for add_reader support via tornado.` That
  selector-thread shim is the racing component.

It is also **load-independent** (reproduces in bare repetition with zero other load — don't trust
an "only under full-suite load" story), **content-innocent** (cell index wanders), and
**version-independent** across at least Python 3.13 and 3.14 (so it is *not* a 3.14 regression and
pinning the interpreter won't help).

> Use the **diagnostic harness in the Appendix** to catch a wedge and read the kernel CPU + which
> cell + the stack. Don't skip this — "confirm, don't assume" is the whole lesson; the inherited
> "Windows Proactor only / under load / content" stories were each wrong until measured.

---

## 3. Root cause (one paragraph)

> **CAVEAT — 2026-06-14 (direct measurement revised this mechanism).** A follow-up traced both
> sides of the bridge (`select()` entry/return on the tornado selector thread + a safe main-loop
> `getsockopt(EVENTS)` probe per client socket) plus kernel-CPU sampling. It found: (a) **no
> version fixes it** (same ~33 % on tornado 6.5.5 *and* 6.5.7; pyzmq async path frozen); (b)
> **tornado's selector is faithful** — it sits *correctly blocked* in `select()` on the shell fd
> the whole time; (c) the reply is **not at the client socket at all** — `getsockopt(EVENTS)`
> never shows POLLIN across the silence, so there is **no dropped readability notification** to
> drop; (d) the kernel is **confirmed idle (0 % CPU)**; (e) **no connection flap** — a zmq socket
> monitor armed on the client shell socket saw *zero* transport events across all three 45 s
> silences (DISCONNECTED/CONNECT_RETRIED fire only at *post-wedge teardown*, identical to a clean
> run), so the connection stays nominally healthy with no reset to blame; (f) **bare transport is
> exonerated** — a no-Jupyter raw-pyzmq DEALER/ROUTER reproducer matching the real loop *asymmetry*
> (ipykernel forces a **Selector** sender via `_init_asyncio_patch`; the **Proactor** client runs the
> same `add_reader` tornado shim), over loopback TCP, ran **240 runs / 9 600 cells** across three
> fidelity tiers — up to a figure-sized **iopub firehose** (~0.5–1 MB/cell) on the one shared libzmq
> io_thread fired right before each shell reply — with **zero** wedges (vs ~33 %/run real). So the
> loss is **in the kernel/jupyter *application* send path** (ipykernel's ZMQStream/Session), above
> libzmq transport (Rung-1-exonerated) and above the client recv queue — **not** the client-side
> selector-shim "dropped notification" described below. The paragraph below is kept
> as the original symptom/triage account; treat its *mechanism* as superseded (see
> `docs/memory/notebook-kernel-wedge-rootcause.md`). **The retry mitigation in §5 is unaffected
> and remains correct** — it recovers any intermittent lost-reply regardless of the layer.

The kernel finishes a cell, emits `execute_reply` on the shell channel, and goes idle. The client
reads zmq sockets over asyncio. On Windows the default **Proactor** event loop cannot drive zmq's
`add_reader` directly, so pyzmq bridges it through an extra tornado **selector thread** — and that
bridge intermittently **drops the readability notification**, so the reply is never consumed and
the client waits until the per-cell timeout (`CellTimeoutError`). It's a missed FD-readiness
notification one layer below `nbclient`. (Linux uses a selector loop natively and does **not** hit
this shim — see §6 on the separate CI/Linux hang.)

---

## 4. The trap: do NOT force `WindowsSelectorEventLoopPolicy`

pyzmq's own warning recommends
`asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`. **It is a worse fix, and
it is dangerous** — verified empirically, interleaved in one session to rule out contamination:

| Event loop | Wedge rate | Clean-run time |
| --- | --- | --- |
| **Proactor** (default) | ~24 % hard wedge | ~7.9 s |
| **Selector** (forced) | 0 % | ~20–31 s — a **timeout-length stall on every run** |

The Selector loop trades the random hard-wedge for a *deterministic* stall whose length **equals
the cell timeout**: ~12 s at a 12 s timeout, **~90 s at a 90 s timeout**. Two such stalls in one
run blow a typical outer subprocess guard. So forcing the Selector policy can turn a 24 %
intermittent flake into a reliable **timeout**. Don't ship it.

---

## 5. The fix: retry-on-wedge (the pattern)

Because the wedge is a transient lost message that *never* recovers within an attempt, but a
*fresh* kernel almost always succeeds, the robust mitigation is to **re-run the fresh subprocess**
— while keeping a real cell error fatal so the test still catches a broken notebook. The lever is
an **exit-code protocol** between the child executor and the parent test:

- child exit **0** = clean
- child exit **1** = a cell raised → `CellExecutionError` → **content bug, fatal, do NOT retry**
- child exit **2** = `CellTimeoutError` → **the lost-reply wedge, retryable**

These two exceptions are **disjoint** (`CellTimeoutError` derives from `CellControlSignal`, not
`CellExecutionError`), so the split is clean. Tune two knobs: a **tight per-attempt cell timeout**
(real cells are sub-second, the wedge never recovers, so a short bound detects it cheaply without
false-positiving real work) and **`MAX_ATTEMPTS`** (`0.24**MAX_ATTEMPTS` residual — 5 ⇒ ≈0.08 %).

### Child executor (the `__main__` of the test file)

```python
if __name__ == "__main__":
    # python <thisfile> <notebook> <repo_root> <kernel_name> [cell_timeout_s]
    import sys
    import nbformat as nbf
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError

    nb_path, repo_root, kernel_name = sys.argv[1], sys.argv[2], sys.argv[3]
    cell_timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 90
    client = NotebookClient(
        nbf.read(nb_path, as_version=4),
        timeout=cell_timeout, kernel_name=kernel_name,
        resources={"metadata": {"path": repo_root}},
    )
    try:
        client.execute()
    except CellTimeoutError as exc:      # kernel idle, reply never arrived → wedge (retry)
        print(f"WEDGE (CellTimeoutError): {exc}", file=sys.stderr); sys.exit(2)
    except CellExecutionError as exc:    # a cell genuinely raised → content bug (do not retry)
        print(f"CELL ERROR (CellExecutionError): {exc}", file=sys.stderr); sys.exit(1)
    print("executed clean"); sys.exit(0)
```

### Parent retry loop (used by the test body)

```python
import subprocess, sys
from pathlib import Path

MAX_ATTEMPTS = 5
PER_CELL_TIMEOUT = 45            # generous for real cells (<1 s), caps a wedged attempt
_OUTER_TIMEOUT = PER_CELL_TIMEOUT + 30

def _execute_once(kernel):
    cmd = [sys.executable, str(Path(__file__).resolve()),
           str(NOTEBOOK), str(REPO_ROOT), kernel, str(PER_CELL_TIMEOUT)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=_OUTER_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        return "hang", exc          # total wall-clock hang — treat like a wedge (retryable)
    return {0: "clean", 1: "content", 2: "wedge"}.get(proc.returncode, "wedge"), proc

def _execute_with_retry(kernel, max_attempts=MAX_ATTEMPTS):
    status, result = "wedge", None
    for attempt in range(1, max_attempts + 1):
        status, result = _execute_once(kernel)
        if status == "clean":
            return True, attempt, status, result
        if status == "content":
            return False, attempt, status, result   # notebook bug — don't burn retries
        # 'wedge' / 'hang' — retry in a clean kernel
    return False, max_attempts, status, result
```

The test body then calls `_execute_with_retry`, asserts a clean pass, and — critically — surfaces
a `content` failure with the cell traceback so a **real broken notebook still fails the gate**
(it fails on attempt 1, never masked by retries).

> Full reference: [`steel/tests/test_steel_notebook.py`](../../steel/tests/test_steel_notebook.py)
> at commit `3814646` — copy its structure verbatim; only the notebook path / extra-stack
> `importorskip`s differ per project.

---

## 6. Scope & caveats (read before you touch CI)

- **This fixes the Windows-local manifestation only.** If your CI hangs too, treat it as a
  **separate, unverified** bug. steel-sim's CI runs **Ubuntu**, which uses a selector loop natively
  and **cannot** hit the Proactor shim — so the Windows root-cause does *not* explain a Linux CI
  hang. **Keep any existing CI skip**; do not remove it on the strength of this Windows fix until
  you've reproduced the CI hang yourself. (The retry is mechanism-agnostic, so it *might* also
  clear a transient CI wedge — but if the CI hang is a *hard* hang, every attempt re-hangs and the
  gate goes red. Reproduce before relying on it.)
- **Retries are silent in normal pytest output.** A future *creep* in the wedge rate stays
  invisible until it breaches all `MAX_ATTEMPTS`. If you want a tripwire, have the parent print the
  attempt count (visible under `pytest -s` / `-rA`) or log when `attempts > 1`.
- **Keep the per-attempt timeout generous enough** that no *real* cell trips it. If your notebook
  legitimately has a slow cell (a live solver, a big sweep), either raise `PER_CELL_TIMEOUT` or
  precompute that cell — otherwise the retry will burn all attempts on a false positive.

---

## 7. If your triage landed on a *different* row (the "similar bug")

- **Kernel busy at the wedge** → not this bug. Find the heavy cell and fix *it*: warm the
  matplotlib font cache, precompute/import-lazily a pycalphad/symengine path, or give that one cell
  a bigger budget. Retrying won't help (the slowness is real and repeatable).
- **Never reaches cell 1** → kernel-startup hang. Look at `startup_timeout`, the kernelspec, and
  the zmq connection-file handshake — not the per-cell retry.

The retry-on-wedge pattern is correct **only** for the kernel-**idle**, lost-message row.

---

## Appendix — the diagnostic harness (throwaway; use to confirm)

Drop these two files in the repo root, run the driver, and let it loop until it catches a wedge.
They mirror production exactly (fresh child subprocess per run) but add `record_timing`, a tight
timeout, a `faulthandler` client-stack dump, and **kernel-CPU sampling** (the busy/idle
discriminator). Delete them afterwards — do **not** commit.

`tmp_nb_child.py` (instrumented single run):

```python
import faulthandler, os, sys, threading, time
from pathlib import Path
import nbformat as nbf, psutil
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError

NB   = Path(os.environ.get("NB_PATH", "<your_notebook>.ipynb")).resolve()
REPO = Path(os.environ.get("REPO_ROOT", ".")).resolve()
KERNEL = os.environ.get("NB_KERNEL", "python3")
TIMEOUT = int(os.environ.get("NB_TIMEOUT", "15"))

class Timed(NotebookClient):
    current_index = None
    async def async_execute_cell(self, cell, idx, *a, **k):
        self.current_index = idx; t0 = time.time()
        try:
            return await super().async_execute_cell(cell, idx, *a, **k)
        finally:
            sys.stderr.write(f"[cell {idx}] {time.time()-t0:5.2f}s\n"); sys.stderr.flush()

def watchdog(c, stop):
    if stop.wait(TIMEOUT + 1.0):     # fires just after a cell would time out
        return
    sys.stderr.write("=== WATCHDOG: sampling kernel CPU (busy core vs ~0%?) ===\n")
    kids = psutil.Process(os.getpid()).children(recursive=True)
    for p in kids:
        try: p.cpu_percent(None)
        except psutil.Error: pass
    time.sleep(1.0)
    for p in kids:
        try: sys.stderr.write(f"  kernel pid={p.pid} cpu={p.cpu_percent(None):.1f}%\n")
        except psutil.Error: pass
    sys.stderr.write(f"  client at cell {getattr(c,'current_index','?')}\n"); sys.stderr.flush()

client = Timed(nbf.read(str(NB), as_version=4), timeout=TIMEOUT,
               kernel_name=KERNEL, resources={"metadata": {"path": str(REPO)}},
               record_timing=True)
stop = threading.Event()
threading.Thread(target=watchdog, args=(client, stop), daemon=True).start()
faulthandler.dump_traceback_later(TIMEOUT + 8, exit=False)
try:
    client.execute()
except CellTimeoutError as e:
    sys.stderr.write(f"WEDGE cell {client.current_index}: {e}\n"); sys.exit(2)
except CellExecutionError as e:
    sys.stderr.write(f"CELL ERROR: {e}\n"); sys.exit(1)
finally:
    stop.set(); faulthandler.cancel_dump_traceback_later()
print("clean"); sys.exit(0)
```

`tmp_nb_driver.py` (loop until a wedge is caught):

```python
import os, subprocess, sys
from pathlib import Path
N = int(sys.argv[1]) if len(sys.argv) > 1 else 80
TIMEOUT = sys.argv[2] if len(sys.argv) > 2 else "12"
env = dict(os.environ, NB_TIMEOUT=TIMEOUT, PYTHONUNBUFFERED="1")
child = str(Path(__file__).resolve().parent / "tmp_nb_child.py")
hist = {}
for i in range(N):
    try:
        rc = subprocess.run([sys.executable, child], capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            timeout=int(TIMEOUT)+25, env=env)
        code, err = rc.returncode, rc.stderr
    except subprocess.TimeoutExpired as e:
        code, err = 99, (e.stderr or "")
    hist[code] = hist.get(code, 0) + 1
    print(f"iter {i:3d} rc={code} {'WEDGE' if code in (2,99) else ''}", flush=True)
    if code in (2, 99) and not Path("tmp_wedge.log").exists():
        Path("tmp_wedge.log").write_text(err, encoding="utf-8")   # the evidence
print("histogram:", hist)
```

Run: `python tmp_nb_driver.py 80 12` → read `tmp_wedge.log`. The lines you want are the
**`kernel pid=… cpu=…%`** (idle ⇒ comms race) and the wedged cell index. To rule out a Python
version, register a kernelspec from a sibling interpreter's venv and rerun with `NB_KERNEL=` that
spec (both client *and* kernel must be that version).

**To verify the fix** afterward: import the production `_execute_with_retry` and call it ~25×;
expect every call to pass with the attempt distribution showing some runs at `attempts > 1` — i.e.
real wedges caught and **recovered**, not merely absent.

---

## References

- Reference implementation: `steel/tests/test_steel_notebook.py` @ `3814646` (steel-sim).
- Test-execution policy (why the notebook test is `slow` + CI-homed): `docs/decisions/0003-test-execution-policy.md`.
- steel-sim plan as-built record: `docs/plans/steel-production.md` (search "lost-`execute_reply`").
- Upstream: pyzmq + asyncio Proactor `add_reader` shim; the warning text in §2 is the search key.
