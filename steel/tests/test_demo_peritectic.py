"""Integration test for the peritectic demo — carbon decides, non-monotonically, end to end.

The demo assesses three plain-carbon heats (lean / peritectic / rich) and an alloying-lever pair, all the way
to the raised flag. Its compute pipeline is the check that the verdict is non-monotonic in carbon (the build's
reason to exist) and that the alloying lever shifts the carbon equivalent across the band. The banked figure
is checked only for "builds without error" (ADR 0002), skipped without the viz extra.
"""
from __future__ import annotations

import pytest

from steel.demo_peritectic import compute


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_carbon_decides_non_monotonically(demo):
    # three heats, carbon the only axis: lean sound, peritectic CRACK, rich sound — non-monotonic
    lean, peri, rich = demo.heroes
    assert not lean[4] and peri[4] and not rich[4]                 # crack flag (index 4)
    assert lean[6] is False and peri[6] is True and rich[6] is False   # flag actually raised on the Heat (6)


def test_hero_carbons_straddle_the_band(demo):
    lean, peri, rich = demo.heroes
    assert lean[3] >= demo.fp_high                                 # lean: ferritic side (FP index 3)
    assert demo.fp_low < peri[3] < demo.fp_high                    # peritectic: in the band
    assert rich[3] <= demo.fp_low                                  # rich: austenitic side


def test_alloying_lever_pulls_same_carbon_into_the_band(demo):
    plain, alloyed = demo.alloy_pair
    assert plain[1] == alloyed[1]                                  # identical carbon (index 1)
    assert not plain[4] and alloyed[4]                             # plain sound, alloyed cracks (index 4)
    assert alloyed[2] < plain[2]                                   # ferrite stabilizers lowered Cp (index 2)


def test_band_edges_sit_near_one_tenth_percent(demo):
    # the soft coherence note surfaced in the demo: plain-carbon crack band ≈ 0.08–0.18 %C
    assert demo.c_band_low == pytest.approx(0.08, abs=0.01)
    assert demo.c_band_high == pytest.approx(0.18, abs=0.01)


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import peritectic_figure
    fig = peritectic_figure(demo)
    assert len(fig.axes) == 4                                      # four panels, no colorbar/twin
