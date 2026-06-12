"""Integration test for the Ellingham demo (Steel-making F1 — the demo IS the integration test).

The F1 demo wires the reduction thermodynamics — ``reduction``'s ΔG° lines, the carbon/wüstite
crossover, the iron-oxide stability stack, and the equilibrium oxygen potential — into the banked
artifact (``demo_reduction.compute`` → ``plots.ellingham_figure``). So its compute pipeline is the
end-to-end check that those compose into the headline reads (carbon reduces wüstite in the textbook
window; the iron oxides stack into the reduction sequence; the deoxidizer hierarchy orders
Ca/Al below Fe), not brittle exact numbers (those are pinned in ``test_reduction.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", and skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_reduction import compute, CARBON, WUSTITE
from steel import reduction as red


def test_demo_pipeline_reduction_window_and_stacks():
    d = compute()
    # The headline: carbon reduces wüstite in the textbook window (and the demo carries it).
    assert 650.0 < d.carbon_wustite_crossover_C < 800.0
    assert d.carbon_wustite_crossover_C == pytest.approx(
        red.crossover_temperature(red.REACTIONS[CARBON], red.REACTIONS[WUSTITE]))

    # The iron-oxide stack is the stepwise reduction sequence (most stable / Fe→FeO first).
    iron_keys = [k for k, _ in d.iron_stack]
    assert iron_keys == ["Fe->FeO", "FeO->Fe3O4", "Fe3O4->Fe2O3"]
    # ΔG° increases down the stack (less stable oxides toward the top of the diagram).
    iron_dG = [g for _, g in d.iron_stack]
    assert iron_dG[0] < iron_dG[1] < iron_dG[2]

    # The deoxidizer hierarchy orders Ca/Al below Fe (the strong deoxidizers at the bottom).
    hier_keys = [k for k, _ in d.hierarchy_stack]
    assert hier_keys[0] == "Ca->CaO" and hier_keys[1] == "Al->Al2O3"
    assert hier_keys[-1] == "Fe->FeO"


def test_demo_lines_and_pO2_arrays_are_aligned():
    d = compute()
    n = len(d.temps_C)
    assert n > 2 and d.temps_C[0] < d.temps_C[-1]
    for k, ys in d.lines.items():
        assert len(ys) == n, f"line {k} length mismatch"
    for k, ys in d.pO2.items():
        assert len(ys) == n, f"pO2 {k} length mismatch"
    # The carbon line is the least-negative (top) at the cold end; an oxide line is far below it.
    assert d.lines["C->CO"][0] > d.lines["Ca->CaO"][0]


def test_ellingham_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import ellingham_figure

    d = compute()
    fig = ellingham_figure(d)
    assert len(fig.axes) == 2                        # the diagram + the oxygen-potential panel
    plt.pyplot.close(fig)
