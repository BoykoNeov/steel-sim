"""Tests for the steel-making front-end what-if app (Steel plan §7).

``app_making.py`` adds **no new physics** — it re-skins the front-end chain (:mod:`reduction`,
:mod:`refining`, :mod:`slag`, :mod:`ladle`, :mod:`casting`, :mod:`heat_state`), each step of which is
sealed behind its own validation triad. Per ADR 0002 the *UI itself is not unit-tested* (``main()``
needs the Streamlit runtime). What these cover is the part that must stay correct and headless: the
**compute helpers** — deliberately **always-green** (they import neither Streamlit nor matplotlib, so
they run on a bare core install exactly like the ``app``/``sweep`` tests).

The checks mirror each stage's *validated demo behaviour* (the crossover, the Al ≫ Si > Mn ladder, the
acid-vs-basic dephos gap, the recovery-shortfall double flag, the centerline hard band) — not new
numbers, so they cannot drift from the sealed models they re-compose.
"""
import sys

import pytest

from steel import app_making as app
from steel import refining


# --------------------------------------------------------------------------- #
# 0. The layering guard — importing app_making must not require/trigger streamlit
# --------------------------------------------------------------------------- #
def test_importing_app_making_does_not_import_streamlit():
    # The load-bearing discipline: the compute layer is headless and `import streamlit` is confined
    # to main(). If it imported at module top, the helpers (and this suite) would need the optional
    # [app] extra. Importing app_making above must leave streamlit unloaded.
    assert "streamlit" not in sys.modules
    assert callable(app.main)                       # the entry point exists, but we never call it
    assert app.DEOX_SYMBOLS == list(refining.DEOXIDIZERS)


# --------------------------------------------------------------------------- #
# 1. F1 — reduction: the crossover, the spontaneity flip, the stability ladder
# --------------------------------------------------------------------------- #
def test_reduction_crossover_and_spontaneity_flip():
    # The headline F1 benchmark: carbon (→CO) reduces wüstite above ~746 °C, not below.
    hot = app.reduction_readout(1500.0)
    cold = app.reduction_readout(500.0)
    assert hot["carbon_reduces_wustite"] is True
    assert cold["carbon_reduces_wustite"] is False
    assert 700.0 < hot["crossover_C"] < 800.0          # the cited ~746 °C window


def test_reduction_stability_ladder_orders_oxides():
    # Most stable first: CaO at the top (hardest to reduce), wüstite (Fe→FeO) at the bottom — the
    # Ca < Al < Si < Mn < Cr < Fe deoxidizer ladder the kill chemistry reads.
    order = app.reduction_readout(1200.0)["hierarchy_order"]
    assert order[0] == "Ca->CaO"
    assert order[-1] == "Fe->FeO"


# --------------------------------------------------------------------------- #
# 2. The spine — an under-dosed 4140 propagates to a soft core
# --------------------------------------------------------------------------- #
def test_spine_under_dose_propagates_to_soft_core():
    well = app.spine_readout(1.0, 0.20)                 # on-spec Cr/Mo
    under = app.spine_readout(0.10, 0.0)                # the demo's under-dose
    assert well["soft_core"] is False
    assert under["soft_core"] is True
    # The flag is the emergent martensite crossing the spec — the well-dosed heat hardens more.
    assert well["martensite"] > under["martensite"]
    assert well["martensite"] >= well["spec"]


# --------------------------------------------------------------------------- #
# 3. F2 — deoxidation: the Al ≫ Si > Mn ladder and the aluminium minimum
# --------------------------------------------------------------------------- #
def test_refining_deox_hierarchy_and_aluminium_minimum():
    r = app.refining_deox_readout("Al", 0.05)
    # Strongest first: aluminium leaves the least dissolved oxygen, then silicon, then manganese.
    syms = [s for s, _ in r["hierarchy"]]
    assert syms == ["Al", "Si", "Mn"]
    # The closed-form Al–O minimum location depends only on e_O^Al → ~0.074 %, source-robust.
    assert r["al_min_pct"] == pytest.approx(0.074, abs=0.005)
    # The interaction is what bends the curve: with it, the oxygen differs from the dilute cartoon.
    assert r["oxygen_ppm"] != pytest.approx(r["oxygen_ppm_cartoon"], rel=1e-3)


# --------------------------------------------------------------------------- #
# 4. F2 — slag partition: acid can't dephosphorize, basic can
# --------------------------------------------------------------------------- #
def test_slag_partition_acid_versus_basic_dephos_gap():
    acid = app.slag_partition_readout("acid Bessemer", 30.0)
    basic = app.slag_partition_readout("basic converter (Thomas/BOF)", 30.0)
    # The history-defining gap: an acid slag leaves phosphorus in the steel (L_P ≈ 1), a basic one
    # pulls it into the slag (L_P in the hundreds) — the ~500× Thomas-vs-acid-Bessemer advantage.
    assert acid["L_P"] < 5.0
    assert basic["L_P"] > 100.0
    assert basic["L_P"] > acid["L_P"] * 50.0
    assert basic["L_S"] > 0.0


# --------------------------------------------------------------------------- #
# 5. F3 — ladle trim: full recovery lands, a shortfall double-flags
# --------------------------------------------------------------------------- #
def test_ladle_trim_recovery_shortfall_double_flags():
    good = app.ladle_trim_readout(1.0)
    bad = app.ladle_trim_readout(0.5)                   # Cr/Mo recovery halved — the demo's bad heat
    assert good["on_grade"] is True
    assert good["soft_core"] is False
    # One mistake, two flags: off-grade (F3's catch) and a soft core (the validated consequence).
    assert bad["off_grade"] is True
    assert bad["soft_core"] is True
    assert bad["landed_Cr"] < good["landed_Cr"]


# --------------------------------------------------------------------------- #
# 5b. F3 — carbon carry-in: the ferroalloy carbon grade decides off-grade-on-C
# --------------------------------------------------------------------------- #
def test_carbon_carryin_high_vs_low_carbon_ferroalloys():
    hc = app.ladle_carbon_carryin_readout(False)         # charge-grade ferroalloys — carbon carries in
    lc = app.ladle_carbon_carryin_readout(True)          # refined low-carbon ferroalloys — carbon holds
    # The high-carbon trim drags the heat off the carbon window (a different mistake than the Cr/Mo shortfall);
    # the low-carbon trim lands on grade. The off-grade flag fires on CARBON, not Cr/Mo.
    assert hc["off_grade"] is True
    assert hc["off_elements"] == ["C"]
    assert lc["off_grade"] is False
    # Same trim, same charges: the high-carbon set carries an order of magnitude more carbon in, over-hardening.
    assert hc["pickup_C"] > 10.0 * lc["pickup_C"]
    assert hc["landed_C"] > lc["landed_C"]
    assert hc["HV"] > lc["HV"]


# --------------------------------------------------------------------------- #
# 5c. F2 → F3 — the deox→recovery seam: a sub-window readout, not an off-grade flag
# --------------------------------------------------------------------------- #
def test_deox_recovery_taxes_oxidizable_alloys_but_stays_sub_window():
    killed = app.ladle_deox_recovery_readout("Al — proper kill (0.04 %)")
    hot = app.ladle_deox_recovery_readout("Si — insufficient kill (0.05 %)")
    # The under-killed bath leaves more dissolved oxygen, so it taxes the oxidizable Mn recovery harder.
    assert hot["oxygen_ppm"] > killed["oxygen_ppm"]
    assert hot["mn_tax_pct"] > killed["mn_tax_pct"]
    # But the magnitude is MODEST — the landed Mn dips yet stays in the band: the coupling cannot trip
    # off-grade (which is exactly why the gross under-trim hero in the F3 panel has to be hand-set).
    assert hot["in_band"] is True
    assert hot["off_grade"] is False
    assert hot["mn_tax_pct"] < 10.0
    # The insufficient kill leaves the heat over the porosity-risk line (F2's own flag, one root cause).
    assert hot["porosity_risk"] is True
    assert killed["porosity_risk"] is False


# --------------------------------------------------------------------------- #
# 6. F4 — casting: the segregated centerline is a harder band than the bulk
# --------------------------------------------------------------------------- #
def test_casting_centerline_is_an_enriched_hard_band():
    c = app.casting_readout("4140", 25.0)
    # Every substitutional alloy enriches at the centerline (Scheil ratio > 1).
    assert all(r > 1.0 for r in c["centerline_ratios"].values())
    # So the centerline hardens more than the nominal bulk — the uneven-hardenability band.
    assert c["centerline_HV"] > c["nominal_HV"]
    assert c["band_HV"] > 0.0
    assert c["chvorinov_s"] > 0.0


# --------------------------------------------------------------------------- #
# 7. Figure builders — a build-only smoke test, viz-gated (ADR 0002: render is reach)
# --------------------------------------------------------------------------- #
# Mirrors test_app.py's layer 3: each *_overview_figure must actually render through the plots
# layer, so a future plots.* signature change can't break the app's st.pyplot calls silently.
@pytest.mark.parametrize("builder", [
    app.reduction_overview_figure,
    app.spine_overview_figure,
    app.refining_overview_figure,
    app.slag_overview_figure,
    app.ladle_overview_figure,
    app.carbon_carryin_overview_figure,
    app.deox_recovery_overview_figure,
    app.casting_overview_figure,
])
def test_overview_figure_builds_when_viz_present(builder):
    pytest.importorskip("matplotlib").use("Agg")
    from matplotlib import pyplot
    fig = builder()
    assert len(fig.axes) >= 1                             # it actually drew something
    pyplot.close(fig)


def test_solidification_overview_figure_builds_when_viz_present():
    # The one heavy builder: compute the chill-slab demo ONCE (not per-param), as main() memoizes it.
    pytest.importorskip("matplotlib").use("Agg")
    from matplotlib import pyplot
    fig = app.solidification_overview_figure(app.solidification_compute())
    assert len(fig.axes) >= 1
    pyplot.close(fig)
