"""Execution smoke-test for the back-end teaching notebook (`steel.ipynb`, Steel plan §9).

A *reach* test, not a physics one (ADR 0002): it asks the one thing the plan names — **does the
notebook execute clean, top to bottom**, no cell raising (`allow_errors=False`). All the shared
machinery — the fresh-subprocess executor, the retry-on-wedge logic for the upstream
pyzmq/asyncio-on-Windows lost-`execute_reply` hang, the importorskip/kernelspec gates, and the
CI skip — lives in :mod:`_notebook_exec`; this file just points it at `steel.ipynb` with timeouts
sized to it (clean in ~7 s, slowest cell < 1 s). See that module's docstring for the full forensics.
"""
from pathlib import Path

import pytest

from . import _notebook_exec as nbx

NOTEBOOK = Path(__file__).resolve().parents[1] / "steel.ipynb"
REPO_ROOT = Path(__file__).resolve().parents[2]

# PER_CELL_TIMEOUT is generous for every real cell (the whole notebook's slowest is <1 s) yet caps a
# wedged attempt cheaply; OUTER_TIMEOUT (whole-notebook backstop) clears the ~7 s clean run 10× over.
PER_CELL_TIMEOUT = 45  # seconds, per cell, per attempt
OUTER_TIMEOUT = PER_CELL_TIMEOUT + 30  # subprocess wall-clock backstop (startup + slack)


@pytest.mark.slow
@pytest.mark.xdist_group("heavy")  # join the shared slow-tail worker (test_calphad.py /
# test_demo_calphad.py / test_ferrite live + the making notebook) under `--dist loadgroup` (pyproject
# addopts). Why: the user asked to group the slow tests, and under the half-core worker cap keeping the
# whole slow tail on one worker avoids general CPU oversubscription. This is NOT a wedge fix — the
# kernel wedge is documented load-INDEPENDENT (~24% even with no other load; see _notebook_exec.py), so
# grouping does not change its odds; the retry-on-wedge logic is its only mitigation.
@pytest.mark.skipif(
    nbx.skip_in_ci(),
    reason="steel.ipynb kernel wedged on the CI (Ubuntu) runner in a00f66a — a separate, "
    "unreproduced hang from the local-Windows lost-reply wedge (which the retry handles); "
    "skipped only in CI until the Ubuntu hang is itself reproduced — see the chip-notebook flake",
)
def test_steel_notebook_executes_clean():
    # @slow (ADR 0003): spawns a fresh kernel in a child process (~7 s clean) — deselected from the
    # fast inner loop (`pytest -m "not slow"`), always run in the full commit gate.
    kernel = nbx.require_notebook_stack()
    assert NOTEBOOK.exists(), f"missing teaching notebook: {NOTEBOOK}"

    # Execute, retrying only the upstream infra wedge (a real cell error fails on attempt 1).
    passed, attempts, status, result = nbx.execute_with_retry(
        NOTEBOOK, REPO_ROOT, kernel, per_cell_timeout=PER_CELL_TIMEOUT, outer_timeout=OUTER_TIMEOUT
    )
    nbx.assert_executed_clean("steel.ipynb", passed, attempts, status, result)
