"""Integration test for the B3 front-end validation demo.

The demo wires the holdout study into its two-panel artifact. Its compute pipeline is the
end-to-end check that the story holds together — the transcription guard passes, the basic holdout
carries, the named edges are present — not brittle exact numbers (those live in
``test_slag_validation.py``). The figure is checked only for "builds without error" (ADR 0002),
skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_slag_validation import compute


def test_demo_pipeline_holdout_and_edges():
    d = compute()
    v = d.verdict

    # The clean holdout is the 10 Table-6 points; the basic pool drops the one named acidic edge.
    assert len(d.holdout) == 10
    assert v.holdout_basic.n == 9
    assert v.transcription_clean is True

    # It carries: consistent modest overprediction, tight scatter, perfect within-T ranking.
    assert 1.2 < 10 ** v.holdout_basic.mean_log < 1.7
    assert 10 ** v.holdout_basic.std_log < 1.4
    assert all(rho == pytest.approx(1.0) for rho, _ in v.ranking.values())

    # Both named edges are present and pointed in opposite directions.
    assert v.edge.resid < 0                       # acidic edge under-predicts
    assert 10 ** v.mno.mean_log > 3.0             # MnO tier over-predicts


def test_slag_validation_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import slag_validation_figure

    fig = slag_validation_figure(compute())
    assert len(fig.axes) == 2                      # the two panels
    plt.pyplot.close(fig)
