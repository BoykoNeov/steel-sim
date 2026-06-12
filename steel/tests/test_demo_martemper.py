"""Integration test for the martemper demo (Steel Phase 6e — same hardness, less distortion).

The demo wires the distortion comparison into the two-panel artifact: the *same* slab quenched two
ways on the frozen heat engine, the surface−centre gradient at ``Mₛ`` read off each. Its compute
pipeline is the end-to-end check that the story holds together — the martemper equalises so its
transformation gradient nearly vanishes while the direct quench's is large — not brittle exact
numbers (those are pinned in ``test_martemper.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_martemper import compute


def test_demo_pipeline_distortion_reduction():
    dc = compute()
    # The headline: same slab, the martemper's through-section gradient at Mₛ is far smaller than
    # the direct quench's — the reason the process exists.
    assert abs(dc.gradient_direct) > 20.0
    assert abs(dc.gradient_martemper) < abs(dc.gradient_direct)
    assert dc.reduction > 8.0
    # The two slab histories are real cooling curves: surface and centre both start hot and cool.
    assert dc.direct.surface[0] > 800.0 and dc.direct.center[0] > 800.0
    assert dc.direct.surface[-1] < dc.Ms and dc.martemper.surface[-1] < dc.Ms


def test_martemper_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import martemper_distortion_figure

    fig = martemper_distortion_figure(compute())
    assert len(fig.axes) == 2                          # the two panels (direct / martemper)
    plt.pyplot.close(fig)
