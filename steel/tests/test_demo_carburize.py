"""Integration test for the carburizing demo (Steel Phase 3c — the demo IS the integration test).

The carburize demo wires the whole mass-mode chain together — ``carburize.solve_carburize``
(the frozen engine's erfc carbon profile) → ``carburize.carburized_traverse`` (per-depth
``ccurve_for_steel`` → ``pathint`` → ``properties``) → ``plots``. So its compute pipeline is the
end-to-end check that they compose, asserted on the *robust* thesis (a hard martensite case over
a softer core, carbon conserved, RA at the surface), not brittle exact numbers (those are pinned
in ``test_carburize.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", and skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_carburize import compute, PUBLISHED_SURFACE_HRC


def test_demo_pipeline_hard_case_over_soft_core():
    profile, traverse = compute(t_hours=8.0)
    # Carbon was driven in (surface enriched, core untouched) and mass is conserved.
    assert profile.C[0] > profile.C[-1]
    assert abs(profile.mass_uptake - profile.surface_flux_uptake) < 1e-12

    # The case-hardened gradient: hard martensite case → softer core, monotone in hardness.
    assert traverse.HRC[0] > 60.0                          # hard case (potential)
    assert 40.0 <= traverse.HRC[-1] <= 52.0                # softer, tougher core
    assert traverse.HV[0] > traverse.HV[-1]
    assert np.all(np.diff(traverse.HV) <= 1e-9)            # monotone decreasing with depth

    # Retained austenite is the surface effect (reported, not asserted vs the published band).
    assert traverse.retained_austenite[0] > traverse.retained_austenite[-1]


def test_demo_published_surface_band_sane():
    # The artifact overlays a representative published carburized-surface band (reference
    # facts) — a regression guard that the demo carries a sane band for the figure.
    lo, hi = PUBLISHED_SURFACE_HRC
    assert 55.0 < lo < hi < 67.0


def test_carburize_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import carburize_figure

    profile, traverse = compute(t_hours=8.0)
    fig = carburize_figure(profile, traverse)
    assert len(fig.axes) == 3                              # carbon / microstructure / hardness
    plt.pyplot.close(fig)
