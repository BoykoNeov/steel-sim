"""Integration test for the unified-KV demo (§19 — the bainite bay, opened in continuous cooling).

The demo wires the competing integrator into the two-panel artifact: the 4340 bay (three KV
C-curves + three cooling paths threading it) and the 1080 no-bay contrast. Its compute pipeline is
the end-to-end check that those tell the *honest* story — 4340 opens a wide bay (pearlite nose far
later than bainite) and a cooling ladder lands martensite / bainite / ferrite+pearlite; 1080 opens
no bay (coincident noses, no proeutectoid ferrite) — not brittle exact numbers (those live in
``test_unified_kv.py``).

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_unified_kv import compute


def test_demo_pipeline_opens_the_4340_bay():
    d = compute()
    b = d.bay
    # The bay: 4340's pearlite (and ferrite) nose sits far later than its bainite nose — the cited
    # PC≫BC differential, the time gap a cooling path threads into bainite.
    assert b.has_ferrite                                   # 4340 is hypoeutectoid
    assert b.pearlite_nose[1] > 50.0 * b.bainite_nose[1]   # the bay separation (~×125 measured)
    assert b.ferrite_nose[1] > 5.0 * b.bainite_nose[1]
    # Each start curve only exists below its ceiling (nan above).
    assert np.all(np.isnan(b.bainite_tau[b.temps >= b.Bs]))
    assert np.any(np.isfinite(b.bainite_tau[b.temps < b.Bs]))
    assert np.all(np.isnan(b.pearlite_tau[b.temps >= b.Ae1]))


def test_demo_ladder_is_martensite_bainite_ferrite():
    d = compute()
    doms = [p.dominant for p in d.paths]
    assert doms == ["martensite", "bainite", "ferrite"]    # fast / intermediate / slow
    # The bay path is genuinely bainite-dominant; the fast path outran every nose.
    bay_path = d.paths[1]
    assert bay_path.dominant == "bainite" and bay_path.fractions["bainite"] > 0.5
    assert d.paths[0].fractions["martensite"] > 0.9
    # Cooling rate ladder is monotone decreasing (fast → slow).
    assert d.paths[0].Vr > d.paths[1].Vr > d.paths[2].Vr


def test_demo_1080_opens_no_bay():
    d = compute()
    nb = d.nobay
    assert not nb.has_ferrite                              # eutectoid: no proeutectoid ferrite
    # Pearlite and bainite noses nearly coincide — no bay (within a small factor, vs 4340's ×125).
    ratio = nb.pearlite_nose[1] / nb.bainite_nose[1]
    assert 0.2 < ratio < 5.0


def test_unified_kv_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import unified_kv_figure

    fig = unified_kv_figure(compute())
    assert len(fig.axes) == 2                              # the two panels
    plt.pyplot.close(fig)
