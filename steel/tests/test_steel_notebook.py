"""Execution smoke-test for the teaching notebook (Steel plan §9, slice 1).

Per ADR 0002 the notebook (`steel.ipynb`) is a **reach** layer, not a correctness
one: its physics is already validated behind the `sweep`/`properties`/`fe_c`
triads, and it is a *thin skin* — each compute cell calls those harness functions
directly. So this test asks the one thing the plan names: **does it execute clean,
top to bottom**, no cell raising. It is *not* a physics check.

Why the discipline matters here (and why the load-bearing compute lives in plain
cells, not `interact` callbacks): `ipywidgets.interact` runs its callback inside an
`Output` context manager that *captures* exceptions and paints them as output
instead of re-raising — so a broken `sweep.*` call inside an interact callback
would leave the cell "successful" and this test green. The notebook therefore puts
every validated call in a direct cell (`allow_errors=False` below makes any such
cell's exception fail this test); the interact cells are sugar on top.

Three gates keep a headless / clean checkout *skipping* rather than *erroring*,
like the viz/calphad tests: the optional `[notebook]` execution stack, matplotlib
(`[viz]`), and a **registered Jupyter kernelspec** — separate from merely having
`ipykernel` importable, so it is checked explicitly.

**Why a subprocess — and why it retries.** The notebook is executed in a *fresh*
child process (the ``__main__`` block at the bottom). That gives a clean kernel and
lets ``subprocess.run(timeout=…)`` wall-clock each attempt. It does **not**, on its
own, make execution reliable: on Windows the kernel client talks zmq over asyncio,
and the kernel's ``execute_reply`` is intermittently lost at the pyzmq/asyncio
layer — the kernel finishes a cell and goes idle (0 % CPU) but the client never
sees the reply and the cell hangs until its timeout. Root-caused 2026-06-10 to a
*missed FD-readiness notification* in pyzmq/asyncio on Windows: the default
**Proactor** loop's tornado selector-thread shim drops the reply (~24 % of runs,
*even with no other load* — it is load-independent, not a full-suite-load effect),
while forcing the **Selector** loop instead misses the socket-readable edge and adds
a full timeout-length stall to *every* run (verified worse — its stall scales to the
cell timeout and can blow the outer guard). The wedge is **content-innocent**: the
hanging cell's index wanders run to run, and it reproduces identically on Python 3.13
and 3.14 (so it is an upstream pyzmq/Jupyter bug, not our notebook and not a 3.14
regression). There is no clean in-code fix; the mitigation is to **retry the fresh
subprocess** on the wedge signature (`CellTimeoutError` → child exit 2, retryable),
which a real cell error (`CellExecutionError` → child exit 1) is *not* — a content
bug fails fast on the first attempt. ``MAX_ATTEMPTS`` runs drive the ~24 % per-attempt
wedge to ``0.24**MAX_ATTEMPTS`` (≈0.08 % at 5) while a clean run still passes on the
first ~7 s attempt. See the chip-notebook flake.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / "steel.ipynb"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Retry budget for the upstream pyzmq/asyncio-on-Windows lost-`execute_reply` wedge
# (see the module docstring). PER_CELL_TIMEOUT is generous for every real cell (the
# whole notebook's slowest is <1 s) yet caps a wedged attempt: the wedge never
# recovers, so a short bound detects it cheaply without false-positiving real work.
MAX_ATTEMPTS = 5
PER_CELL_TIMEOUT = 45  # seconds, per cell, per attempt
_OUTER_TIMEOUT = PER_CELL_TIMEOUT + 30  # subprocess wall-clock backstop (startup + slack)

# steel.ipynb is CI-skipped on a *separate*, unreproduced hang: in commit a00f66a the
# Jupyter kernel wedged on the GitHub Actions (Ubuntu) runner. That Linux hang has NOT
# been root-caused here — the lost-reply wedge analysed above and mitigated by retry was
# reproduced only on local Windows, where Linux uses the selector loop and cannot hit the
# same Proactor shim. So we keep skipping ONLY under CI to keep the badge meaningful, and
# REMOVE this gate once the *Ubuntu* hang is reproduced and confirmed cleared (the local
# Windows flake is handled by the retry below, not by this skip). See the chip-notebook flake.
_SKIP_IN_CI = os.environ.get("CI", "").lower() in {"true", "1"}


def _execute_once(kernel):
    """Run steel.ipynb once in a fresh child process. Returns (status, result) where
    status is 'clean' | 'wedge' | 'content' | 'hang' and result is the CompletedProcess
    (or TimeoutExpired). 'wedge'/'hang' are the retryable infra failure; 'content' is a
    real cell error (do not retry)."""
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        str(NOTEBOOK), str(REPO_ROOT), kernel, str(PER_CELL_TIMEOUT),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=_OUTER_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        return "hang", exc  # total wall-clock hang — treat like a wedge (retryable)
    status = {0: "clean", 1: "content", 2: "wedge"}.get(proc.returncode, "wedge")
    return status, proc


def _execute_with_retry(kernel, max_attempts=MAX_ATTEMPTS):
    """Retry the fresh-subprocess run on the infra wedge; a real cell error is fatal
    immediately. Returns (passed, attempts, status, last_result)."""
    status, result = "wedge", None
    for attempt in range(1, max_attempts + 1):
        status, result = _execute_once(kernel)
        if status == "clean":
            return True, attempt, status, result
        if status == "content":
            return False, attempt, status, result  # notebook bug — don't burn retries
        # 'wedge' / 'hang' — the upstream lost-reply; try again in a clean kernel
    return False, max_attempts, status, result


@pytest.mark.slow
@pytest.mark.skipif(
    _SKIP_IN_CI,
    reason="steel.ipynb kernel wedged on the CI (Ubuntu) runner in a00f66a — a separate, "
    "unreproduced hang from the local-Windows lost-reply wedge (which the retry below handles); "
    "skipped only in CI until the Ubuntu hang is itself reproduced — see the chip-notebook flake",
)
def test_steel_notebook_executes_clean():
    # @slow (ADR 0003): spawns a fresh kernel in a child process (~7 s clean) — deselected
    # from the fast inner loop (`pytest -m "not slow"`), always run in the full commit gate.
    # Gate on the optional execution stack (the [notebook] extra) + the render dep.
    pytest.importorskip("nbformat")
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    pytest.importorskip("ipywidgets")
    pytest.importorskip("matplotlib")

    # importorskip checks the *packages*; executing also needs a registered Jupyter
    # kernelspec (NOT guaranteed by `pip install ipykernel` alone). Skip — don't
    # error — if none is available, mirroring the importorskip philosophy.
    from jupyter_client.kernelspec import KernelSpecManager

    specs = KernelSpecManager().find_kernel_specs()
    kernel = "python3" if "python3" in specs else next(iter(specs), None)
    if kernel is None:
        pytest.skip("no registered Jupyter kernelspec to execute the notebook")

    assert NOTEBOOK.exists(), f"missing teaching notebook: {NOTEBOOK}"

    # Execute, retrying only the upstream infra wedge (a real cell error fails on attempt 1).
    passed, attempts, status, result = _execute_with_retry(kernel)

    if status == "content":
        # A notebook cell actually raised (allow_errors=False) — the real failure we test for.
        assert passed, (
            "steel.ipynb has a failing cell (not the infra wedge):\n"
            f"--- stdout ---\n{result.stdout[-2000:]}\n--- stderr ---\n{result.stderr[-3000:]}"
        )
    assert passed, (
        f"steel.ipynb wedged on all {attempts} attempts — the upstream pyzmq/asyncio-on-Windows "
        f"lost-`execute_reply` hang (~24% per attempt; see the module docstring). Last status "
        f"{status!r}.\n--- stderr (last attempt) ---\n"
        f"{getattr(result, 'stderr', str(result))[-3000:]}"
    )


if __name__ == "__main__":
    # Child entry: execute the notebook headless in a fresh kernel. Exit codes let the
    # parent distinguish the retryable infra wedge from a real cell error:
    #   0 = clean | 1 = a cell raised (CellExecutionError, content bug, fatal) |
    #   2 = the lost-`execute_reply` wedge (CellTimeoutError, retryable).
    # Invoked as `python <thisfile> <notebook> <repo_root> <kernel_name> [cell_timeout_s]`.
    import nbformat as nbf
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError

    nb_path, repo_root, kernel_name = sys.argv[1], sys.argv[2], sys.argv[3]
    cell_timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 90
    notebook = nbf.read(nb_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=cell_timeout,
        kernel_name=kernel_name,
        resources={"metadata": {"path": repo_root}},
    )
    try:
        client.execute()
    except CellTimeoutError as exc:  # kernel idle, reply never arrived → infra wedge (retry)
        print(f"WEDGE (CellTimeoutError): {exc}", file=sys.stderr)
        sys.exit(2)
    except CellExecutionError as exc:  # a cell genuinely raised → content bug (do not retry)
        print(f"CELL ERROR (CellExecutionError): {exc}", file=sys.stderr)
        sys.exit(1)
    print("steel.ipynb executed clean")
    sys.exit(0)
