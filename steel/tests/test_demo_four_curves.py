"""Integration test for the anchor demo (Steel plan §3 — "the demo IS the integration test").

The four-curves demo wires every Phase-1 module together — ``fe_c`` (A₁ driving
force) → ``kinetics`` (C-curve + Mₛ) → ``cooling`` (the four paths) → ``pathint``
(path → fractions). So its compute pipeline is the end-to-end check that they
compose, asserted on the *robust* qualitative outcome (the four-materials thesis),
not brittle exact fractions.

The figure itself is **not** in the correctness path (ADR 0002): rendering is
checked only for "builds without error", and is skipped where the optional viz
extra is absent — the core suite stays matplotlib-free.
"""
import math

import pytest

from steel.demo_four_curves import compute, compute_hardness


def test_demo_pipeline_spans_pearlite_to_martensite():
    ccurve, paths, results = compute()
    assert [p.name for p in paths] == ["furnace", "air", "oil", "water"]
    assert len(results) == 4

    # Every product is a valid partition of the austenite (conservation end-to-end).
    for r in results:
        assert sum(r.fractions().values()) == pytest.approx(1.0, abs=1e-12)

    furnace, air, oil, water = results
    # The honest thesis: the slow ends are pearlitic, the fast end martensitic, and
    # the intermediate carries substantial bainite. Asserted on fractions, not strict
    # `dominant()`, because oil's bainite vs pearlite/martensite split hinges on the
    # Bs-vs-nose gap (a labeling convention) — see test below and pathint docs.
    assert furnace.dominant() == "pearlite"
    assert air.dominant() == "pearlite"
    assert oil.bainite > 0.3                 # a genuine bainite-dominant mixture
    assert water.dominant() == "martensite"
    # Three genuinely distinct phase constitutions across the four rates.
    assert len({r.dominant() for r in results}) >= 3


def test_demo_pearlite_formation_temperature_distinguishes_furnace_from_air():
    # Furnace and air both give pearlite, but the furnace transforms higher on the
    # C-curve (slower cool) → coarser. The kinetic quantity that separates them.
    _, _, results = compute()
    furnace, air = results[0], results[1]
    assert furnace.formation_T > air.formation_T
    assert air.formation_T > results[2].formation_T  # oil (bainite) forms lower still


def test_demo_martensite_rises_monotonically_with_quench_severity():
    # The dramatic axis, end-to-end: furnace → water, martensite only ever increases.
    _, _, results = compute()
    martensite = [r.martensite for r in results]
    assert martensite == sorted(martensite)


def test_demo_real_hardness_spans_and_orders():
    # Phase 3 rewire: the demo now reports the REAL properties-model hardness (the retired
    # INDICATIVE_HARDNESS placeholders are gone). The dramatic axis end-to-end, in real
    # numbers: hardness rises monotonically furnace → water and spans soft pearlite to hard
    # martensite. All four are on the HRC scale here (eutectoid pearlite ~30 HRC, not nan).
    _, paths, results = compute()
    hardness = compute_hardness(paths, results)
    HV = [hv for hv, _ in hardness]
    HRC = [hrc for _, hrc in hardness]
    assert all(math.isfinite(h) for h in HRC)                 # all on-scale (≥ 20 HRC)
    assert HV == sorted(HV)                                   # furnace ≤ air < oil < water
    furnace, air, oil, water = HRC
    assert 26.0 <= furnace <= 32.0 and 26.0 <= air <= 32.0    # pearlite, ~29–30 HRC
    assert abs(air - furnace) < 2.0                           # honest: cooling-rate term is small
    assert water > 58.0                                       # martensite, file-hard
    assert water - furnace > 25.0                             # the dramatic property span


def test_anchor_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import four_curves_figure

    ccurve, paths, results = compute()
    fig = four_curves_figure(ccurve, paths, results)
    assert len(fig.axes) == 2               # TTT panel + microstructure-bars panel
    plt.pyplot.close(fig)
