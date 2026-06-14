"""Integration test for the gas-porosity demo — the carbon-aware consequence, end to end.

The demo refines a high-carbon and a low-carbon heat to the *same* light kill, then reads whether each
casting blows CO holes. Its compute pipeline is the check that the chain runs risk → consequence and that
the **carbon**, not the oxygen number, decides (the two flags disagree). The banked figure is checked only
for "builds without error" (ADR 0002), skipped without the viz extra.
"""
from __future__ import annotations

import pytest

from steel.demo_gas_porosity import compute
from steel import gas_porosity as gp


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_same_oxygen_carbon_decides(demo):
    # both heats within refining's 30 ppm oxygen spec (risk-cleared), opposite porosity verdict
    assert not demo.high_risk and not demo.low_risk
    assert demo.high_porous and not demo.low_porous
    assert demo.high_S > 1.0 > demo.low_S


def test_high_carbon_heat_carries_no_more_oxygen_yet_blows_holes(demo):
    # the carbon-blindness made concrete: the porous heat is NOT the higher-oxygen one
    assert demo.high_O_ppm <= demo.low_O_ppm
    assert demo.high_Ocrit < demo.low_Ocrit                        # its carbon-aware limit is far lower


def test_deox_lever_saves_the_high_carbon_heat(demo):
    assert not demo.killed_porous
    assert demo.killed_S < demo.high_S


def test_carbon_blindness_crossover_is_between_a_half_and_one_percent(demo):
    assert 0.5 < demo.crossover_C < 0.85


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import gas_porosity_figure
    fig = gas_porosity_figure(demo)
    assert len(fig.axes) == 4                                       # four panels, no colorbar/twin
