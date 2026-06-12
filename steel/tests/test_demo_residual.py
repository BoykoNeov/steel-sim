"""Integration test for the residual-stress demo (Steel Phase 6f — §11 Option-#2, solid mechanics).

The demo wires the three slab-mechanics solves into the two-panel artifact: the *same* 4340 plate
quenched thermal-only, with transformation, and martempered. Its compute pipeline is the end-to-end
check that the story holds together — transformation flips the surface sign and martempering removes
the tension — not brittle exact numbers (those are pinned in ``test_residual.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import pytest

from steel.demo_residual import compute


def test_demo_pipeline_sign_reversal_and_martemper():
    on, off, marte = compute()
    # The headline: thermal-only leaves surface compression; transformation flips it to tension.
    assert off.surface_stress < 0.0 < on.surface_stress
    # And martempering removes the surface tension (the §17 benefit, now in stress).
    assert abs(marte.surface_stress) < 0.1 * abs(on.surface_stress)
    # The fields are real residual profiles: self-equilibrated to machine precision.
    assert abs(on.mean_stress) < 1.0          # Pa — ∫σ dx ≈ 0


def test_residual_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import residual_stress_figure

    fig = residual_stress_figure(*compute())
    assert len(fig.axes) == 2                  # the two panels (sign reversal / route)
    plt.pyplot.close(fig)
