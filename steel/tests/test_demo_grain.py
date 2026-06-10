"""Integration test for the grain demo (Steel Phase 5c — the demo IS the integration test).

The grain demo wires the 5c chain — ``grain.coupled_grain_properties`` (5a PAGS → the calibrated
ferrite-grain coupling → fe_c equilibrium pearlite → the 5b Pickering yield + DBTT pair) →
``plots.grain_figure``. So its compute pipeline is the end-to-end check that those compose, on
the *robust* thesis (refining raises yield while lowering DBTT; the DBTT crosses room temperature
across the austenitizing range; yield ≤ UTS), not brittle exact numbers (those are pinned in
``test_grain.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", and skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_grain import compute, DEMO_STEEL_C, DEMO_STEEL_COMP


def test_demo_pipeline_co_benefit_and_crossover():
    fine, coarse = compute()
    # Hotter austenitize ⇒ coarser PAGS ⇒ coarser ferrite (the coupling direction).
    assert coarse.pags_um > fine.pags_um
    assert coarse.ferrite_um > fine.ferrite_um < coarse.pags_um   # ferrite finer than PAGS

    # The co-benefit: refining (fine) is stronger AND tougher than the overheated (coarse) grain.
    assert fine.yield_MPa > coarse.yield_MPa        # stronger
    assert fine.dbtt_C < coarse.dbtt_C              # tougher (lower DBTT)

    # The demo steel is chosen so the DBTT spans the ductile→brittle crossover.
    assert fine.dbtt_C < 0.0 < coarse.dbtt_C

    # The consistency / scope-boundary cross-check holds at both operating points.
    assert fine.yield_below_uts and coarse.yield_below_uts


def test_demo_steel_is_low_carbon_in_distribution():
    # A regression guard that the demo carries a sane low-carbon ferrite-pearlite grade
    # (the carbon choice is load-bearing — see demo_grain's docstring).
    assert 0.10 <= DEMO_STEEL_C <= 0.25
    assert DEMO_STEEL_COMP["Mn"] > 0.0


def test_grain_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import grain_figure

    fine, coarse = compute()
    fig = grain_figure(fine, coarse, DEMO_STEEL_C, DEMO_STEEL_COMP, name="1018")
    # three panels (co-benefit / lever comparison / overheating), two of them with a twin axis.
    assert len(fig.axes) == 5                       # 3 primary + 2 twinx
    plt.pyplot.close(fig)
