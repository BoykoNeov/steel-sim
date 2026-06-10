"""Integration test for the austemper demo (Steel Phase 6d — the atlas-anchored hold recipe).

The demo wires the anchored recipe into the three-panel artifact: the anchored isothermal diagram
with the atlas measurements on it, the hold's completion history, and the hardness-vs-hold-time
trade with the minimum full-transform hold. Its compute pipeline is the end-to-end check that the
story holds together — the holdout prediction lands, the headline hold goes fully bainitic, the
hardness descends monotonically from the untempered-martensite plateau to the bainite plateau —
not brittle exact numbers (those are pinned in ``test_austemper.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from projects.steel.demo_austemper import compute
from projects.steel.properties import vickers_bainite


def test_demo_pipeline_holdout_hold_and_sweep():
    d = compute()
    # The headline hold sits at a HOLDOUT temperature (343.3 °C, not the 371.1 °C anchor) and the
    # predicted 50 % time lands on the atlas measurement within the claimed ±25 %.
    assert d.T_hold != d.anchor_T
    assert np.isfinite(d.measured_t50_here)
    assert d.predicted_t50_here == pytest.approx(d.measured_t50_here, rel=0.25)

    # The hold history: U(t) monotone from 0 to fully bainitic, the recipe quiet (no race flag).
    assert d.hold.U[0] == 0.0
    assert np.all(np.diff(d.hold.U) >= 0.0)
    assert d.hold.bainite > 0.99
    assert not d.hold.pearlite_race_flagged

    # The hardness sweep: monotone non-increasing from the untempered-martensite plateau down to
    # the bainite placeholder plateau, with the minimum full-transform hold inside the sweep and
    # the bainite fraction capped beyond it.
    assert np.all(np.diff(d.sweep_HV) <= 1e-9)
    assert d.sweep_t[0] < d.min_full_hold < d.sweep_t[-1]
    assert d.sweep_HV[0] > d.sweep_HV[-1] + 100.0          # the trade is visible, not flat
    assert d.sweep_HV[-1] == pytest.approx(vickers_bainite(0.79), rel=1e-9)
    assert np.all(d.sweep_bainite[d.sweep_t > 2.0 * d.min_full_hold] > 0.99)


def test_austemper_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from projects.steel.plots import austemper_figure

    fig = austemper_figure(compute())
    assert len(fig.axes) == 3                          # the three panels
    plt.pyplot.close(fig)
