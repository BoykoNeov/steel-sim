"""Integration test for the heat-state spine demo (the demo IS the integration test).

The demo wires the ``Heat`` record and the orchestrator seam into the end-to-end propagation story
(``demo_heat_state.compute`` → two 4140 heats diverging + the atlas crack illustration). So its
compute pipeline is the check that the spine *composes* — an upstream alloy mistake reaches a
downstream flag — not brittle exact numbers (those are owned by the back-end / §18 tests; the seam
behaviour is pinned in ``test_heat_state.py``). The banked figure draws those same numbers (the
propagation, plotted); per ADR 0002 it is checked only for "builds without error" and skipped where
the optional viz extra is absent.
"""
import pytest

from steel.demo_heat_state import compute
from steel import heat_state as hs


def test_demo_propagates_the_alloy_mistake_to_a_flag():
    d = compute()
    # The headline: same treatment, only the under-dosed heat fails — and it fails because of the
    # physics (a real martensite-fraction miss), recorded on the heat that flows downstream.
    assert d.well.is_clean
    assert d.under.has_defect(hs.SOFT_CORE)
    # Both carry a heat-treat step; the under-dosed one marks it off-spec.
    assert d.well.history[-1].name == "heat-treat" and d.well.history[-1].in_spec is True
    assert d.under.history[-1].in_spec is False


def test_demo_atlas_illustration_repacks_residual_and_flags_crack_risk():
    d = compute()
    assert d.cracked.has_defect(hs.QUENCH_CRACK_RISK)
    assert d.cracked.residual_stress_MPa is not None and d.cracked.residual_stress_MPa > 0.0
    assert d.cracked.history[-1].name == "quench-crack-check"


def test_demo_heats_are_distinct_and_provenance_is_non_empty():
    d = compute()
    assert d.well is not d.under is not d.cracked
    for heat in (d.well, d.under, d.cracked):
        assert len(heat.history) >= 1


def test_demo_figure_scalars_match_the_flags():
    # The figure draws the same numbers the flags were set from: the well bar clears the spec, the
    # under bar falls below it — consistent with the heats' soft-core flags.
    d = compute()
    assert d.well_martensite >= d.spec and not d.well.has_defect(hs.SOFT_CORE)
    assert d.under_martensite < d.spec and d.under.has_defect(hs.SOFT_CORE)
    assert d.atlas_surface_MPa == d.cracked.residual_stress_MPa


def test_heat_state_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import heat_state_figure

    fig = heat_state_figure(compute())
    assert len(fig.axes) == 2                        # the propagation bars + the atlas residual panel
    plt.pyplot.close(fig)
