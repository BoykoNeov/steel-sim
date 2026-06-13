"""Integration test for the hydrogen-flaking demo — the two-tier consequence, end to end.

The demo degasses a heat (F2), then reads whether two sections flake. Its compute pipeline is the check
that the chain runs risk → consequence and that geometry/schedule decide. The banked figure is checked only
for "builds without error" (ADR 0002), skipped without the viz extra.
"""
from __future__ import annotations

import pytest

from steel.demo_hydrogen_flaking import compute
from steel import hydrogen_flaking as hf


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_same_hydrogen_thin_sound_thick_flakes(demo):
    assert not demo.thin_flakes
    assert demo.thick_flakes
    assert demo.thick_residual_ppm > demo.thin_residual_ppm


def test_bake_lever_saves_the_thick_section(demo):
    assert not demo.thick_long_flakes
    assert demo.thick_long_residual_ppm < demo.thick_residual_ppm


def test_two_tier_risk_flag_was_set_in_the_ladle(demo):
    assert demo.risk_flag                          # refining's chemistry-state risk precedes the consequence
    assert demo.ladle_H_ppm > demo.critical_ppm


def test_coherence_tooth_matches_practice_order(demo):
    # the cited anchors fall out without tuning: ~1 h/inch, heavy forging → days
    one_inch_h = float(demo.bake_time_h[demo.section_mm.tolist().index(25)])
    heavy_h = float(demo.bake_time_h[demo.section_mm.tolist().index(500)])
    assert 0.1 < one_inch_h < 5.0
    assert heavy_h > 100.0


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import hydrogen_flaking_figure
    fig = hydrogen_flaking_figure(demo)
    assert len(fig.axes) == 4                       # four panels, no colorbar/twin
