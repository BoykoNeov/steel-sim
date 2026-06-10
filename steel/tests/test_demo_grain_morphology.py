"""Integration + smoke test for the grain-morphology demo (the deferred grain-viz).

Reach, not physics (ADR 0002): the demo reuses :mod:`steel.demo_grain`'s validated fine/coarse
pair and draws it as size-accurate Voronoi swatches. So the checks here are (a) it reuses that
pair and the size contrast points the right way (coarse ferrite > fine, so the *same* field shows
fewer coarse grains), and (b) the figure builds. The grain physics is pinned in ``test_grain.py``;
the swatch's size-accuracy is in ``test_plots_grain_swatch.py``.
"""
import pytest

from steel.demo_grain_morphology import compute, DEMO_STEEL_NAME


def test_demo_reuses_the_grain_pair_with_a_real_size_contrast():
    fine, coarse = compute()
    assert coarse.ferrite_um > fine.ferrite_um               # hotter austenitize ⇒ coarser grain
    # same field of view ⇒ the coarse swatch shows fewer grains by (d_coarse/d_fine)^2.
    assert (coarse.ferrite_um / fine.ferrite_um) ** 2 > 2.0
    assert DEMO_STEEL_NAME == "1018"


def test_grain_morphology_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import grain_morphology_figure

    fine, coarse = compute()
    fig = grain_morphology_figure(fine, coarse, name=DEMO_STEEL_NAME)
    assert len(fig.axes) == 2                                # two swatches, no twin axes
    plt.pyplot.close(fig)
