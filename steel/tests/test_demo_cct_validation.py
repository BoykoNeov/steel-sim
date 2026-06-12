"""Integration test for the §20 cross-composition validation demo.

The demo wires the validation study into its two-panel artifact. Its compute pipeline is the
end-to-end check that the story holds together — the bias-immune cited-anchor wall is sign-inverted,
the grading is even-handed (no cited factor wins both metrics), the refit improves out-of-sample —
not brittle exact numbers (those live in ``test_cct_validation.py``). The figure is checked only for
"builds without error" (ADR 0002), skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_cct_validation import compute


def test_demo_pipeline_wall_grading_and_refit():
    d = compute()
    # Eight steels, two of them the cited anchors.
    assert len(d.names) == 8
    assert int(d.cited_mask.sum()) == 2

    # The bias-immune headline: cited BC inverts the cited 1080↔4340 ordering by ≳ ×20.
    assert d.wall.sign_inverted
    assert d.wall.miss > 20.0

    # Even-handed grading (anchor-invariant): alloy-weighted factors rank better; FC tightest spread.
    bc, pc, fc = d.grades["bainite"], d.grades["pearlite"], d.grades["ferrite"]
    assert pc.spearman > fc.spearman > bc.spearman
    assert fc.log_resid_spread < bc.log_resid_spread

    # The one-knob refit improves the ranking out-of-sample, alloy-carried.
    assert d.holdout.test_spearman_refit > d.holdout.test_spearman_bc
    assert d.decomposition["alloy_only"] > d.decomposition["Bs_and_grain_only"]


def test_cct_validation_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import cct_validation_figure

    fig = cct_validation_figure(compute())
    assert len(fig.axes) == 2                           # the two panels
    plt.pyplot.close(fig)
