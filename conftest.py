"""Root pytest config — cap `-n auto` at half the logical cores.

`addopts` (pyproject.toml) sets `-n auto`, which would otherwise spin up one worker per
*logical* core. This hook halves that. Why half:

  * The slow tail is CPU-bound and already internally threaded — pycalphad/symengine spawns
    its own threads per live solve — so one worker per logical core oversubscribes and can
    aggravate the known multicomponent flake and the notebook kernel wedge. Half leaves real
    headroom for those internal threads while still parallelising the ~240-test fast lane.
  * The slow tests additionally share one xdist_group ("heavy", see the test files), so under
    `--dist loadgroup` they all land on a SINGLE worker — serialised, never two heavy solves
    at once — while the other (half-core) workers churn the fast lane.

This is xdist's own hook, invoked while it resolves `-n auto`, so it engages reliably — unlike
setting `numprocesses` from `pytest_configure`, which runs after xdist has already resolved the
worker count. `optionalhook=True` keeps a bare `pytest` in an xdist-less environment from
erroring on an unknown hook (it just never fires). An explicit `-n N` overrides this; `-n0`
forces in-process serial.
"""
import os

import pytest


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config):
    return max(1, (os.cpu_count() or 2) // 2)
