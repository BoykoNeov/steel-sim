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

**Why a subprocess.** The notebook is executed in a *fresh* child process rather than
in-process. On Windows the kernel client polls zmq over asyncio, and if this process
already has a running/cached event loop (left by another test in the suite), nbclient
takes a thread-runner path that can deadlock pyzmq on the Proactor loop. A clean child
process always gets the fast path (~4 s), and `subprocess.run(timeout=…)` wall-clocks
it so a pathological hang fails *this test* fast instead of wedging the whole suite.
The child entry point is the ``__main__`` block at the bottom of this file.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / "steel.ipynb"
REPO_ROOT = Path(__file__).resolve().parents[2]

# steel.ipynb executes clean locally (~5 s), but on the GitHub Actions runner the Jupyter kernel
# wedges at the zmq/asyncio comms layer and a cell hangs past the per-cell timeout — an infra
# hang, NOT a notebook-content failure (a cell that runs in ~3 s locally blew past 90 s on the
# runner; the same wedge the chip notebook hit). The fast lane never runs this `slow` test, and
# the *local* full gate still does (where it is reliable), so we skip it ONLY in CI to keep the
# badge meaningful instead of permanently red. REMOVE this gate once the kernel-startup hang is
# root-caused. See the chip-notebook flake.
_SKIP_IN_CI = os.environ.get("CI", "").lower() in {"true", "1"}


@pytest.mark.slow
@pytest.mark.skipif(
    _SKIP_IN_CI,
    reason="steel.ipynb kernel wedges on the CI runner (infra hang, not a content failure); "
    "runs in the local full gate — see the chip-notebook flake",
)
def test_steel_notebook_executes_clean():
    # @slow (ADR 0003): spawns a fresh kernel in a child process (~5 s) — deselected from
    # the fast inner loop (`pytest -m "not slow"`), always run in the full commit gate.
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

    # Run the executor (this file's __main__) in a clean child process. It exits
    # non-zero with a traceback on any cell error (allow_errors=False); a clean run
    # exits 0. errors="replace" keeps a unicode traceback (°C, →) from masking the
    # real failure behind a decode error on a legacy codepage.
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(NOTEBOOK), str(REPO_ROOT), kernel],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode == 0, (
        "steel.ipynb did not execute clean:\n"
        f"--- stdout ---\n{proc.stdout[-2000:]}\n--- stderr ---\n{proc.stderr[-3000:]}"
    )


if __name__ == "__main__":
    # Child entry: execute the notebook headless; raise (→ non-zero exit) on any cell
    # error. Invoked as `python <thisfile> <notebook> <repo_root> <kernel_name>`.
    import nbformat as nbf
    from nbclient import NotebookClient

    nb_path, repo_root, kernel_name = sys.argv[1], sys.argv[2], sys.argv[3]
    notebook = nbf.read(nb_path, as_version=4)
    NotebookClient(
        notebook,
        timeout=90,
        kernel_name=kernel_name,
        resources={"metadata": {"path": repo_root}},
    ).execute()
    print("steel.ipynb executed clean")
