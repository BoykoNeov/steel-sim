"""Shared execution harness for the teaching notebooks (Steel plan §9; the making-chain §7).

Both `steel.ipynb` (back-end heat-treatment) and `making.ipynb` (front-end ore→billit→defects)
are **reach** layers, not correctness ones (ADR 0002): their physics is validated behind the
`sweep`/`properties`/`reduction`/… triads, and each is a *thin skin* — every compute cell calls
those harness functions directly. So the one thing the test asks is what the plan names: **does the
notebook execute clean, top to bottom**, no cell raising. It is *not* a physics check.

Why the discipline matters (and why the load-bearing compute lives in plain cells, not `interact`
callbacks): `ipywidgets.interact` runs its callback inside an `Output` context manager that
*captures* exceptions and paints them as output instead of re-raising — so a broken harness call
inside an interact callback would leave the cell "successful" and the test green. The notebooks
therefore put every validated call in a direct cell (`allow_errors=False` below makes any such
cell's exception fail the test); the interact cells are sugar on top.

**Why a subprocess — and why it retries.** The notebook is executed in a *fresh* child process
(the ``__main__`` block at the bottom). That gives a clean kernel and lets
``subprocess.run(timeout=…)`` wall-clock each attempt. It does **not**, on its own, make execution
reliable: on Windows the kernel client talks zmq over asyncio, and the kernel's ``execute_reply``
is intermittently lost at the pyzmq/asyncio layer — the kernel finishes a cell and goes idle (0 %
CPU) but the client never sees the reply and the cell hangs until its timeout. Root-caused 2026-06-10
to a *missed FD-readiness notification* in pyzmq/asyncio on Windows: the default **Proactor** loop's
tornado selector-thread shim drops the reply (~24 % of runs, load-*independent*), while forcing the
**Selector** loop instead misses the socket-readable edge and adds a full timeout-length stall to
*every* run (verified worse). The wedge is **content-innocent**: the hanging cell's index wanders
run to run, and it reproduces on Python 3.13/3.14 (an upstream pyzmq/Jupyter bug, not our notebooks).
There is no clean in-code fix (the upstream fix is filed as ipython/ipykernel#1529); the mitigation
is to **retry the fresh subprocess** on the wedge signature (``CellTimeoutError`` → child exit 2,
retryable), which a real cell error (``CellExecutionError`` → child exit 1) is *not* — a content bug
fails fast on the first attempt. ``MAX_ATTEMPTS`` runs drive the ~24 % per-attempt wedge to
``0.24**MAX_ATTEMPTS`` (≈0.08 % at 5) while a clean run still passes on the first attempt.

Timeouts are **per-notebook parameters**, not constants here: ``per_cell_timeout`` must clear the
slowest legitimate cell with margin yet stay short enough to detect a wedge cheaply, and
``outer_timeout`` (the whole-notebook subprocess wall-clock backstop) must clear a *clean* run with
generous headroom so good code is never misclassified as a hang. `steel.ipynb` runs clean in ~7 s,
`making.ipynb` in ~16 s — the two call sites pass numbers sized to each.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Retry budget for the upstream pyzmq/asyncio-on-Windows lost-`execute_reply` wedge (see docstring).
MAX_ATTEMPTS = 5


def skip_in_ci() -> bool:
    """True under CI. The notebooks are CI-skipped on a *separate*, unreproduced Ubuntu kernel hang
    (commit a00f66a): the lost-reply wedge analysed above + mitigated by retry was reproduced only on
    local Windows, where Linux uses the selector loop and cannot hit the Proactor shim. We skip ONLY
    under CI to keep the badge meaningful; remove the gate once the Ubuntu hang is itself reproduced
    (the local-Windows flake is handled by the retry, not by this skip). See the chip-notebook flake."""
    return os.environ.get("CI", "").lower() in {"true", "1"}


def require_notebook_stack() -> str:
    """importorskip the optional execution + render stack and return a registered Jupyter kernelspec
    name, or ``pytest.skip`` if none is available. Three gates keep a headless / clean checkout
    *skipping* rather than *erroring* (like the viz/calphad tests): the optional ``[notebook]``
    execution stack, matplotlib (``[viz]``), and — separate from merely importing ``ipykernel`` — a
    **registered kernelspec** (NOT guaranteed by ``pip install ipykernel`` alone)."""
    pytest.importorskip("nbformat")
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    pytest.importorskip("ipywidgets")
    pytest.importorskip("matplotlib")

    from jupyter_client.kernelspec import KernelSpecManager

    specs = KernelSpecManager().find_kernel_specs()
    kernel = "python3" if "python3" in specs else next(iter(specs), None)
    if kernel is None:
        pytest.skip("no registered Jupyter kernelspec to execute the notebook")
    return kernel


def _execute_once(notebook: Path, repo_root: Path, kernel: str,
                  per_cell_timeout: int, outer_timeout: int):
    """Run ``notebook`` once in a fresh child process. Returns (status, result) where status is
    'clean' | 'wedge' | 'content' | 'hang' and result is the CompletedProcess (or TimeoutExpired).
    'wedge'/'hang' are the retryable infra failure; 'content' is a real cell error (do not retry)."""
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        str(notebook), str(repo_root), kernel, str(per_cell_timeout),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=outer_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return "hang", exc  # total wall-clock hang — treat like a wedge (retryable)
    status = {0: "clean", 1: "content", 2: "wedge"}.get(proc.returncode, "wedge")
    return status, proc


def execute_with_retry(notebook: Path, repo_root: Path, kernel: str, *,
                       per_cell_timeout: int, outer_timeout: int, max_attempts: int = MAX_ATTEMPTS):
    """Retry the fresh-subprocess run on the infra wedge; a real cell error is fatal immediately.
    Returns (passed, attempts, status, last_result)."""
    status, result = "wedge", None
    for attempt in range(1, max_attempts + 1):
        status, result = _execute_once(notebook, repo_root, kernel, per_cell_timeout, outer_timeout)
        if status == "clean":
            return True, attempt, status, result
        if status == "content":
            return False, attempt, status, result  # notebook bug — don't burn retries
        # 'wedge' / 'hang' — the upstream lost-reply; try again in a clean kernel
    return False, max_attempts, status, result


def assert_executed_clean(label: str, passed: bool, attempts: int, status: str, result) -> None:
    """The two-assert verdict shared by both notebook tests: a *content* failure (a cell genuinely
    raised under ``allow_errors=False``) reports the cell output; otherwise an all-attempts wedge
    reports the upstream infra hang. Either way ``passed`` must be True."""
    if status == "content":
        assert passed, (
            f"{label} has a failing cell (not the infra wedge):\n"
            f"--- stdout ---\n{result.stdout[-2000:]}\n--- stderr ---\n{result.stderr[-3000:]}"
        )
    assert passed, (
        f"{label} wedged on all {attempts} attempts — the upstream pyzmq/asyncio-on-Windows "
        f"lost-`execute_reply` hang (~24% per attempt; see _notebook_exec.py). Last status "
        f"{status!r}.\n--- stderr (last attempt) ---\n"
        f"{getattr(result, 'stderr', str(result))[-3000:]}"
    )


if __name__ == "__main__":
    # Child entry: execute the notebook headless in a fresh kernel. Exit codes let the parent
    # distinguish the retryable infra wedge from a real cell error:
    #   0 = clean | 1 = a cell raised (CellExecutionError, content bug, fatal) |
    #   2 = the lost-`execute_reply` wedge (CellTimeoutError, retryable).
    # Invoked as `python _notebook_exec.py <notebook> <repo_root> <kernel_name> [cell_timeout_s]`.
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
    print(f"{Path(nb_path).name} executed clean")
    sys.exit(0)
