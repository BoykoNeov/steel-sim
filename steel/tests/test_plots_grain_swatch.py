"""Size-accuracy + geometry checks for the Voronoi grain swatch (the grain-morphology viz).

This is the deferred grain-*morphology* view — **reach, not physics** (ADR 0002), so these are
plumbing / consistency checks, NOT a triad with teeth. The one quantitative claim is the grain
**number density**: grain.py defines ``N_A = 1/d²`` (``astm_grain_size_number``), so a fixed field
of side ``W`` holds ``(W/d)²`` grains and a *finer* grain shows strictly **more** of them. The cell
shapes / size-spread are decorative. All gated on the viz extra (``plots`` imports matplotlib at
module scope).
"""
import numpy as np
import pytest

pytest.importorskip("matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from steel import plots


def test_grain_cell_count_matches_number_density():
    # N = (W/d)^2 — grain.py's N_A = 1/d^2 times the field area W^2.
    assert plots.grain_cell_count(10.0, 100.0) == 100         # (100/10)^2
    assert plots.grain_cell_count(20.0, 100.0) == 25          # (100/20)^2
    # Finer grain ⇒ strictly more grains in the SAME field — the size-accurate claim.
    counts = [plots.grain_cell_count(d, 150.0) for d in (60.0, 30.0, 15.0, 8.0)]
    assert counts == sorted(counts) and counts[0] < counts[-1]
    # Clamped to ≥ 1 and to the safety cap; rejects nonsense.
    assert plots.grain_cell_count(1e6, 100.0) == 1
    assert plots.grain_cell_count(1e-6, 100.0) == plots._GRAIN_SWATCH_MAX_CELLS
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError):
            plots.grain_cell_count(bad, 100.0)
        with pytest.raises(ValueError):
            plots.grain_cell_count(10.0, bad)


def test_grain_swatch_window_round_trips_to_target_cells():
    # W = sqrt(target)*d_coarsest, so the coarsest grain shows ~target cells.
    W = plots.grain_swatch_window_um(40.0, target_coarse_cells=9.0)
    assert W == pytest.approx(3.0 * 40.0)
    assert plots.grain_cell_count(40.0, W) == 9
    with pytest.raises(ValueError):
        plots.grain_swatch_window_um(0.0)
    with pytest.raises(ValueError):
        plots.grain_swatch_window_um(40.0, target_coarse_cells=0.0)


def test_bounded_voronoi_returns_one_finite_cell_per_seed():
    W = 100.0
    pts = np.random.default_rng(3).uniform(0.0, W, size=(40, 2))
    cells = plots._bounded_voronoi_cells(pts, W)
    assert len(cells) == len(pts)                             # mirror padding bounds every cell
    for poly in cells:
        assert poly.shape[1] == 2 and len(poly) >= 3          # a real polygon
        assert np.isfinite(poly).all()
        # the original cells tile [0, W]^2 — vertices stay within the window (small FP tol).
        assert poly.min() >= -1e-6 and poly.max() <= W + 1e-6


def test_swatch_draws_a_size_accurate_count_and_is_deterministic():
    fig, (ax1, ax2) = plt.subplots(1, 2)
    plots.grain_voronoi_swatch(ax1, 20.0, window_um=120.0, seed=7)
    plots.grain_voronoi_swatch(ax2, 20.0, window_um=120.0, seed=7)
    n_expected = plots.grain_cell_count(20.0, 120.0)
    assert len(ax1.collections[0].get_paths()) == n_expected  # one polygon per size-accurate grain
    assert len(ax1.collections[0].get_paths()) == len(ax2.collections[0].get_paths())  # deterministic
    plt.close(fig)

    fig2, ax3 = plt.subplots()
    plots.grain_voronoi_swatch(ax3, 12.0)                     # auto window → ~36 grains
    assert len(ax3.collections[0].get_paths()) == 36
    plt.close(fig2)

    fig3, ax4 = plt.subplots()
    with pytest.raises(ValueError):
        plots.grain_voronoi_swatch(ax4, 0.0)                  # rejects a non-positive grain size
    plt.close(fig3)


def test_morphology_figure_fine_shows_more_grains_than_coarse():
    from steel.demo_grain import compute

    fine, coarse = compute()
    fig = plots.grain_morphology_figure(fine, coarse, name="1018")
    assert len(fig.axes) == 2                                 # two swatches, one common field
    n_fine = len(fig.axes[0].collections[0].get_paths())
    n_coarse = len(fig.axes[1].collections[0].get_paths())
    assert n_fine > n_coarse                                  # finer grain ⇒ more cells, same window
    # the count ratio tracks (d_coarse/d_fine)^2 (the size-accurate density), modulo rounding.
    assert n_fine / n_coarse == pytest.approx((coarse.ferrite_um / fine.ferrite_um) ** 2, rel=0.25)
    plt.close(fig)
