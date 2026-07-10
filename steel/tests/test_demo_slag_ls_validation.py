"""Integration test for the B3 sulfur metal-partition validation demo.

The demo wires the L_S holdout probe into its two-panel artifact. Its compute pipeline is the
end-to-end check that the story holds together — both guards pass, the clean waterless grade
under-predicts, the measured atmosphere ladder rises, the anchor reads low — not brittle exact numbers
(those live in ``test_slag_ls_validation.py``). The figure is checked only for "builds without error"
(ADR 0002), skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_slag_ls_validation import compute


def test_demo_pipeline_probe_and_edges():
    d = compute()
    v = d.verdict

    # The clean grade is the 8 waterless CO/CO2 heats; the supplement is the 35 H2/H2O heats (S8 dropped).
    assert len(d.co_residuals) == 8
    assert len(d.h2o_residuals) == 35
    assert v.logls_consistency_clean is True and v.oxide_sum_clean is True

    # It is a PROBE: the clean grade under-predicts, direction robust across the a_O method.
    assert v.co_gas.mean_log < 0.0 and v.co_feo.mean_log < 0.0
    assert 10 ** v.co_gas.mean_log < 0.7

    # The two signed side-findings are present: the water ladder rises, the FeO anchor reads low.
    lad = {r.atmosphere: r for r in v.ladder}
    assert lad["CO/CO2"].mean_log_ls < lad["mix"].mean_log_ls < lad["H2/H2O"].mean_log_ls
    assert v.anchor.mean_log_ratio > 0.0


def test_slag_ls_validation_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import slag_ls_validation_figure

    fig = slag_ls_validation_figure(compute())
    assert len(fig.axes) == 2                      # the two panels
    plt.pyplot.close(fig)
