"""Integration test for the bainite demo (Steel Phase 6b — the cited reaction & the bay mechanism).

The bainite demo wires the Phase-6b standalone reaction into the two-panel artifact: the scale-free
coefficient bay (``BC`` vs ``FC`` retardation) and the 4140 pearlite + bainite TTT start curves. Its
compute pipeline is the end-to-end check that those produce the *honest* story — alloy retards
bainite far less than ferrite (the teeth), the bainite reaction has its own nose below ``Bs``, and
the time axis is unanchored — not brittle exact numbers (those are pinned in ``test_bainite.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from projects.steel.demo_bainite import compute


def test_demo_pipeline_teeth_and_curves():
    d = compute()
    # THE TEETH: 4140's alloy load retards the reconstructive ferrite reaction far more than the
    # displacive bainite reaction — the cause of the bay, scale-free.
    assert d.alloy_ferrite_retardation > 10.0 * d.alloy_bainite_retardation
    # The Cr sweep shows the same gap growing: ferrite retardation outruns bainite at every Cr > 0.
    assert d.ferrite_retardation[0] == pytest.approx(1.0) and d.bainite_retardation[0] == pytest.approx(1.0)
    assert np.all(d.ferrite_retardation[1:] > d.bainite_retardation[1:])

    # The bainite reaction is real: a finite nose below its Steven–Haynes ceiling.
    Tb, tb = d.bainite_nose
    assert 100.0 < Tb < d.bs_4140
    assert np.isfinite(tb) and tb > 0.0
    # The bainite start curve only exists below Bs (nan above the ceiling).
    assert np.all(np.isnan(d.bainite_tau[d.temps >= d.bs_4140]))
    assert np.any(np.isfinite(d.bainite_tau[d.temps < d.bs_4140]))


def test_bainite_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from projects.steel.plots import bainite_figure

    fig = bainite_figure(compute())
    assert len(fig.axes) == 2                          # the two panels
    plt.pyplot.close(fig)
