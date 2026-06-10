"""Integration test for the experimentation-surface demo (the sweep artifact).

The demo wires the whole chain through the :mod:`sweep` harness across a grid of real steels;
its compute pipeline is the end-to-end check that the composition × cooling-rate sweep
composes, asserted on the robust qualitative outcome (the hardenability story), not brittle
exact numbers. The figure itself is **not** in the correctness path (ADR 0002): rendering is
a build-only smoke test, skipped without the optional viz extra.
"""
import math

import pytest

from steel.demo_sweep import compute, DEMO_STEELS


def test_demo_grid_tells_the_hardenability_story():
    grid = compute()
    assert len(grid) == len(DEMO_STEELS)
    assert [row[0].steel.name for row in grid] == DEMO_STEELS
    assert all(len(row) == 4 for row in grid)               # four media per steel

    # Every cell is a valid partition of the austenite (conservation, end-to-end).
    for row in grid:
        for o in row:
            assert sum(o.fractions().values()) == pytest.approx(1.0, abs=1e-12)

    # Index the steels by name for the qualitative claims.
    by_name = {row[0].steel.name: row for row in grid}
    lean, alloy = by_name["1045"], by_name["4140"]
    # Media columns are slow → fast.
    assert [o.medium for o in lean] == ["furnace", "air", "oil", "water"]

    # Per steel, hardness rises (non-decreasing) from furnace to water (in HV — defined
    # everywhere, unlike HRC which is nan on the soft slow-cooled ends).
    for row in grid:
        HV = [o.HV for o in row]
        assert HV == sorted(HV)

    # The hardenability divergence reads at the intermediate medium (oil), not the saturated
    # ends: the alloy keeps far more martensite than the lean steel there.
    oil_lean, oil_alloy = lean[2], alloy[2]
    assert oil_alloy.result.martensite > oil_lean.result.martensite + 0.3
    # …and they converge at the water (fast) end — both essentially martensitic.
    assert abs(lean[3].result.martensite - alloy[3].result.martensite) < 0.1


def test_demo_sweep_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import sweep_comparison_figure

    grid = compute()
    fig = sweep_comparison_figure(grid)
    assert len(fig.axes) >= 2               # the hardenability-curve panel + the hardness grid
    plt.pyplot.close(fig)
