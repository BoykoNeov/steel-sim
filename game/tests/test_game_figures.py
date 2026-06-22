"""Figure-builder smoke test (viz-gated) — the blow-curve figure builds without error.

Layer-2 coverage the firewall and gallery tests do **not** give: the firewall test only *imports*
:mod:`game.figures` (never calls the builder), and ``test_gallery`` only checks the PNG *exists on disk* —
so a broken builder would pass both silently. This is the same guard every sibling surface carries
(``test_capstone_figure_builds``, the apps' per-panel viz-gated smoke tests). It is a **smoke** test
(builds, the two expected axes), never a correctness check (ADR 0002), and skips cleanly without the extra.
"""
import pytest

from game import knobs as kn


@pytest.mark.parametrize("carbon", [0.40, 0.25, 0.50])   # on-aim, over-blow, under-blow — all zone branches
def test_blow_curve_figure_builds(carbon):
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from game.figures import blow_curve_figure

    fig = blow_curve_figure(carbon)
    assert len(fig.axes) == 2                            # the flavor trajectory + the validated C–O readout
    plt.pyplot.close(fig)


def test_blow_curve_figure_builds_at_the_grade_aim():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from game.figures import blow_curve_figure

    fig = blow_curve_figure(kn.grade_carbon_aim())
    assert len(fig.axes) == 2
    plt.pyplot.close(fig)


def test_methods_figure_builds():
    # Slice 2's purity-ramp figure: the two panels (residual P and S down the era tech tree). Smoke only.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from game.demo_game_methods import compute
    from game.figures import methods_figure

    fig = methods_figure(compute())
    assert len(fig.axes) == 2                            # residual phosphorus + residual sulfur
    plt.pyplot.close(fig)
