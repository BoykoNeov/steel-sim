"""Integration test for the A2-B grain-boundary-coverage demo.

The demo wires the P-coverage mechanism into its three-panel artifact. Its compute pipeline is the
end-to-end check that the story holds together — the coverage→DBTT slope is per-steel, the composed
bulk slope straddles the documented bracket, and there is no in-domain holdout (so no tooth) — not
brittle exact numbers (those live in ``test_p_segregation_dbtt.py``). The figure is checked only for
"builds without error" (ADR 0002), skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_p_segregation_dbtt import compute


def test_demo_pipeline_bias_map_and_no_tooth():
    d = compute()
    s = d.summary

    # Gap 2 is per-steel/cross-domain; Gap 1+2 composed straddles the documented bracket.
    assert s.slope_span > 3.0
    assert s.composed_min < 40.0 and s.composed_max > 78.0
    assert s.bracket_contained is True and s.engine_value_inside is True

    # The honest posture, defended: no independent in-domain holdout ⇒ no tooth.
    assert s.has_independent_in_domain_holdout is False
    assert len(d.relations) == 4


def test_p_segregation_dbtt_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import p_segregation_dbtt_figure

    fig = p_segregation_dbtt_figure(compute())
    assert len(fig.axes) == 3                       # the three panels
    plt.pyplot.close(fig)
