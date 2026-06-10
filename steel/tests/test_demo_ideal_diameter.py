"""Integration test for the D_I cross-check demo (Steel Phase 6c — the measured-Jominy leg).

The demo wires the cross-check into the two-panel artifact: D_I (model vs measured band) per grade,
and the model Jominy curves over the measured envelopes. Its compute pipeline is the end-to-end
check that the *story* holds — the ranking is right, the anchor lands in band, the deep grade
under-predicts — not brittle exact numbers (those are pinned in ``test_ideal_diameter.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_ideal_diameter import compute


def test_demo_pipeline_ranking_anchor_and_teeth():
    d = compute()
    di = {n: d.checks[n].model.Dc_mm for n in d.order}

    # The headline: hardenability ranking correct (alloy beats carbon).
    assert di["1045"] < di["8620"] < di["4140"] < di["4340"]

    # The anchor lands in its (wide) band by construction; the deep teeth grade under-predicts;
    # the shallow edge rides high — the directional shape the figure shows.
    assert d.checks["4140"].in_band
    assert d.checks["4340"].verdict.startswith("under-predicts")
    assert d.checks["1045"].verdict.startswith("rides high")

    # Every grade carries a finite, positive measured lower-edge D_I (the band is well-formed).
    for cc in d.checks.values():
        assert np.isfinite(cc.measured.Dc_min_mm) and cc.measured.Dc_min_mm > 0.0


def test_ideal_diameter_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import ideal_diameter_figure

    fig = ideal_diameter_figure(compute())
    assert len(fig.axes) == 2                          # the two panels
    plt.pyplot.close(fig)
