"""Integration test for the inverse-design demo (Steel Phase 7 — the demo IS the integration test).

The design demo wires the inverse chain — ``design.find_recipes_for_HRC`` (outer grade × medium
enumeration + the inner temper root-find) + ``sweep.sweep_grid`` (the as-quenched landscape) →
``plots.design_figure``. So its compute pipeline is the end-to-end check that those compose, on the
*robust* headline (the canonical 45-HRC-in-10-mm spec resolves to an oil-quench-and-temper 4140
recommendation, lumped-valid) — not brittle exact numbers (those are pinned in ``test_design.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", and skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_design import compute, TARGET_HRC, TOL_HRC, DIAMETER_M


def test_demo_pipeline_recommends_oil_quench_and_temper():
    result, grid = compute()
    # The spec is feasible and the cheapest answer is the textbook quench-and-temper 4140.
    assert result.feasible
    rec = result.recommended
    assert rec.steel.name == "4140" and rec.medium == "oil" and rec.tempered
    assert rec.lumped_valid                                   # oil at 10 mm is inside Bi < 0.1

    # Every feasible recipe genuinely lands in the target band (the harness invariant, end-to-end).
    lo, hi = result.target_band
    assert all(lo <= r.HV <= hi for r in result.recipes)

    # The landscape grid matches the search axes (4 grades × 4 media) — the figure's input.
    assert len(grid) == 4 and all(len(row) == 4 for row in grid)


def test_demo_spec_is_the_canonical_quench_and_temper_problem():
    # A regression guard on the worked spec (the demo's framing is load-bearing — see its docstring).
    assert TARGET_HRC == 45.0
    assert DIAMETER_M == pytest.approx(0.010)
    assert 0.0 < TOL_HRC <= 3.0


def test_design_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import design_figure

    result, grid = compute()
    fig = design_figure(result, grid)
    assert len(fig.axes) >= 2                                 # map + ranked recipes (+ colorbar)
    plt.pyplot.close(fig)
