"""Integration test for the Jominy hardness demo (Steel Phase 2c — the demo IS the integration test).

The Jominy demo wires the whole spatial chain together — ``jominy`` (one shared thermal
field) → ``pathint`` (path → microstructure) → ``kinetics`` (``ccurve_for_steel``, the
hardenability shift) → ``properties`` (microstructure → hardness). So its compute pipeline
is the end-to-end check that they compose, asserted on the *robust* qualitative thesis
(shared quenched end, diverge with distance), not brittle exact numbers (those are pinned
in ``test_properties.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only
for "builds without error", and skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_jominy import compute, STEELS, PUBLISHED


def test_demo_pipeline_shared_end_then_diverges():
    field, curves = compute(n_cells=160, per_decade=80)
    assert set(curves) == set(STEELS) == {"1045", "4140"}
    h1045, h4140 = curves["1045"], curves["4140"]

    # Shared quenched end: both martensitic, within a couple HRC (the hardness model alone).
    assert abs(h1045.HRC[0] - h4140.HRC[0]) < 3.0
    assert h1045.HRC[0] > 54.0 and h4140.HRC[0] > 54.0

    # Diverge with distance: by the far read point the alloy steel is much harder (HV is
    # defined everywhere, so compare there — the 1045 tail is off the HRC scale).
    assert h4140.HV[-1] - h1045.HV[-1] > 250.0
    # 1045 ran off the HRC scale (soft pearlite), 4140 did not (deep-hardening plateau).
    assert np.isnan(h1045.HRC[-1])
    assert np.isfinite(h4140.HRC[-1]) and h4140.HRC[-1] > 44.0


def test_demo_published_reference_points_present():
    # The artifact overlays representative published points for both steels (reference
    # facts) — a regression guard that the demo carries them for the figure.
    assert set(PUBLISHED) == {"1045", "4140"}
    for pts in PUBLISHED.values():
        assert all(0.0 < d < 30.0 and 15.0 < hrc < 70.0 for d, hrc in pts)


def test_jominy_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import jominy_hardness_figure

    _, curves = compute(n_cells=120, per_decade=60)
    fig = jominy_hardness_figure(curves)
    assert len(fig.axes) == 1
    plt.pyplot.close(fig)
