"""Integration test for the F4 Slice-2 solidification demo (the demo IS the validated-physics run).

The demo solves the latent-heat thermal field on the sealed engine and reads the headline tooth (the Stefan
benchmark), the latent arrest, and the by-construction defect localisation off it. ``compute()`` drives the
diffusion solver several times, so it is computed **once** here (module-scoped fixture) and shared. The
banked figure is checked only for "builds without error" (ADR 0002), skipped without the viz extra.
"""
from __future__ import annotations

import numpy as np
import pytest

from steel.demo_solidification import compute


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_stefan_benchmark_converges_under_refinement(demo):
    """The headline tooth, end-to-end: the numerical front approaches the analytic Stefan front as Δx halves."""
    coarse, fine = demo.stefan
    assert fine.n_cells > coarse.n_cells
    assert 0.90 < fine.ratio.mean() < 1.01
    assert abs(fine.ratio.mean() - 1.0) < abs(coarse.ratio.mean() - 1.0)


def test_enthalpy_conservation_is_machine_precision(demo):
    assert demo.conservation_resid < 1e-9


def test_latent_heat_stalls_the_centre_cooldown(demo):
    """Directional sanity: latent heat lengthens the centre's freeze-through (the recalescence plateau)."""
    assert demo.centre_freeze_on > demo.centre_freeze_off
    assert 2.0 < demo.centre_freeze_on / demo.centre_freeze_off < 12.0


def test_centre_is_the_last_to_freeze_hot_spot(demo):
    """By construction: the insulated thermal centre freezes last — the shrinkage hot spot (and Slice 1's
    enriched centerline), so porosity and macro-segregation concentrate in one place."""
    finite = demo.solidification_time[np.isfinite(demo.solidification_time)]
    assert finite[-1] == finite.max()


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import solidification_figure
    fig = solidification_figure(demo)
    # four panels + the map's colorbar + the Niyama twin axis on the defect panel
    assert len(fig.axes) == 6
