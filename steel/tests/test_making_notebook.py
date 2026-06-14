"""Execution smoke-test for the front-end teaching notebook (`making.ipynb`, Steel plan §7 / §9).

The twin of :mod:`test_steel_notebook`, for the *ore → billet → and what goes wrong* notebook — the
make-then-break front-end story (F1 reduction → the `Heat` spine → F2 refining + slag → F3 ladle →
F4 casting + solidification, then the six defect consequences). Same *reach*-not-physics posture
(ADR 0002): every compute cell is a thin call into a validated harness — in fact the *same* tested
readout helpers `app_making` / `app_consequences` use — so the only question is whether it executes
clean, top to bottom, no cell raising.

It is a **separate** test file (and a separate notebook) by design — the front-end notebook carries
the upstream pyzmq/asyncio-on-Windows kernel-wedge flakiness in isolation, with its own retry-wrapped
harness. All that machinery is shared from :mod:`_notebook_exec` (executor, retry-on-wedge,
importorskip/kernelspec gates, CI skip); this file just points it at `making.ipynb` with timeouts
sized to it. It is heavier than the back-end notebook (clean in ~16 s; the latent-heat solidification
solve and the spine/ladle/casting heat-treats are its ~5 s cells), so it gets a larger per-cell cap
and a wider outer backstop — the very reason :mod:`_notebook_exec` parametrizes the timeouts instead
of hard-coding the back-end's tight numbers.
"""
from pathlib import Path

import pytest

from . import _notebook_exec as nbx

NOTEBOOK = Path(__file__).resolve().parents[1] / "making.ipynb"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Sized to the heavier front-end notebook: PER_CELL_TIMEOUT clears its ~5 s heaviest cell (the
# latent-heat solidification solve) with >10× margin yet still caps a wedge cheaply; OUTER_TIMEOUT
# clears the ~16 s clean run with generous headroom so a clean run is never misclassified as a hang.
PER_CELL_TIMEOUT = 60  # seconds, per cell, per attempt
OUTER_TIMEOUT = 120    # subprocess wall-clock backstop (startup + slack)


@pytest.mark.slow
@pytest.mark.xdist_group("heavy")  # share the single slow-tail worker with the other @slow tests
# (the back-end notebook, the live-CALPHAD/ferrite tests) under `--dist loadgroup`, so two Jupyter
# kernels never run in parallel under the half-core worker cap. NOT a wedge fix — the wedge is
# load-INDEPENDENT (see _notebook_exec.py); the retry is its only mitigation.
@pytest.mark.skipif(
    nbx.skip_in_ci(),
    reason="making.ipynb shares the steel.ipynb kernel-wedge story — CI-skipped until the separate, "
    "unreproduced Ubuntu kernel hang (a00f66a) is itself reproduced; the local-Windows lost-reply "
    "wedge is handled by the retry, not this skip — see _notebook_exec.py",
)
def test_making_notebook_executes_clean():
    # @slow (ADR 0003): spawns a fresh kernel in a child process (~16 s clean) — deselected from the
    # fast inner loop (`pytest -m "not slow"`), always run in the full commit gate.
    kernel = nbx.require_notebook_stack()
    assert NOTEBOOK.exists(), f"missing front-end teaching notebook: {NOTEBOOK}"

    # Execute, retrying only the upstream infra wedge (a real cell error fails on attempt 1).
    passed, attempts, status, result = nbx.execute_with_retry(
        NOTEBOOK, REPO_ROOT, kernel, per_cell_timeout=PER_CELL_TIMEOUT, outer_timeout=OUTER_TIMEOUT
    )
    nbx.assert_executed_clean("making.ipynb", passed, attempts, status, result)
