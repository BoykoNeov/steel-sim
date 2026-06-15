"""Tests for the defect-consequences what-if app (Steel plan §14).

``app_consequences.py`` adds **no new physics** — it re-skins the consequence chain (:mod:`grain`,
:mod:`hot_work`, :mod:`temper_embrittlement`, :mod:`tempered_martensite_embrittlement`,
:mod:`hydrogen_flaking`, :mod:`gas_porosity`, :mod:`hot_tear`), each sealed behind its own validation
triad. Per ADR 0002 the *UI itself is not unit-tested* (``main()`` needs the Streamlit runtime). What
these cover is the part that must stay correct and headless: the **compute helpers** — deliberately
**always-green** (they import neither Streamlit nor matplotlib, so they run on a bare core install
exactly like the ``app`` / ``app_making`` tests).

The checks mirror each consequence's *validated demo behaviour* (the cold-short ↔ red-short window, the
four temper-embrittlement levers, the carbon-driven TME trough, the section-decided flaking, the
carbon-decides porosity, the segregation-amplified hot-tear) — not new numbers, so they cannot drift
from the sealed models they re-compose.
"""
import sys

import pytest

from steel import app_consequences as app


# --------------------------------------------------------------------------- #
# 0. The layering guard — importing app_consequences must not require streamlit
# --------------------------------------------------------------------------- #
def test_importing_app_consequences_does_not_import_streamlit():
    # The load-bearing discipline: the compute layer is headless and `import streamlit` is confined to
    # main(). If it imported at module top, the helpers (and this suite) would need the optional [app] extra.
    assert "streamlit" not in sys.modules
    assert callable(app.main)                       # the entry point exists, but we never call it


# --------------------------------------------------------------------------- #
# 1. Cold-short + red-short — the impurity window brackets a clean vs dirty heat
# --------------------------------------------------------------------------- #
def test_impurity_window_clean_is_workable_dirty_brackets_both_ends():
    clean = app.impurity_readout(0.01, 0.80, 0.01)      # low P, Mushet Mn, low S
    dirty = app.impurity_readout(0.35, 0.05, 0.05)      # high P, no Mn, high S — the acid-Bessemer victim
    assert clean["cold_short"] is False
    assert clean["red_short"] is False
    assert dirty["cold_short"] is True                  # high P pushes the DBTT above service
    assert dirty["red_short"] is True                   # free sulfur (no Mn to tie it) films the boundaries
    # The signed-impurity foil: phosphorus strengthens AND embrittles — the dirty heat is STRONGER yet brittle.
    assert dirty["yield_MPa"] > clean["yield_MPa"]
    assert dirty["dbtt_C"] > clean["dbtt_C"]


def test_impurity_window_mushet_manganese_clears_red_short():
    # Same sulfur, the manganese decides red-shortness: enough Mn ties the sulfur up as benign MnS.
    starved = app.impurity_readout(0.01, 0.05, 0.05)
    mushet = app.impurity_readout(0.01, 0.80, 0.05)
    assert starved["red_short"] is True
    assert mushet["red_short"] is False
    assert mushet["free_S"] < starved["free_S"]


# --------------------------------------------------------------------------- #
# 2. Temper embrittlement — the susceptible victim is saved by any one lever
# --------------------------------------------------------------------------- #
def test_temper_embrittlement_four_levers():
    fail = app.temper_embrittlement_readout(0.025, 0.0, True, 620.0)    # dirty, no Mo, slow cool: the failure
    fast = app.temper_embrittlement_readout(0.025, 0.0, False, 620.0)   # fast cool through the window
    cure = app.temper_embrittlement_readout(0.025, 0.55, True, 620.0)   # +0.5 % Mo (the classic cure)
    clean = app.temper_embrittlement_readout(0.005, 0.0, True, 620.0)   # clean heat (low J)
    assert fail["embrittled"] is True
    assert fast["embrittled"] is False
    assert cure["embrittled"] is False
    assert clean["embrittled"] is False
    # The clean heat drops below the J-factor susceptibility threshold; the dirty one clears it.
    assert fail["susceptible"] is True
    assert clean["susceptible"] is False
    assert clean["J"] < fail["J"]


# --------------------------------------------------------------------------- #
# 3. Tempered-martensite embrittlement — carbon-driven, irreversible, hardenability-gated
# --------------------------------------------------------------------------- #
def test_tme_trough_recovery_and_carbon_gate():
    trough = app.tme_readout("4140", 300.0)             # in the 260–370 °C trough → embrittled
    recovered = app.tme_readout("4140", 450.0)          # over the trough → recovered (one-way)
    low_carbon = app.tme_readout("8620", 300.0)         # 0.20 %C — exempt even when hardened
    assert trough["embrittled"] is True
    assert recovered["embrittled"] is False
    assert low_carbon["embrittled"] is False
    # The carbon gate, not a hardenability miss: 8620 still hardens here, it just lacks the carbon.
    assert low_carbon["martensite"] >= 0.50
    assert low_carbon["carbon"] < trough["carbon"]


# --------------------------------------------------------------------------- #
# 4. Hydrogen flaking — same ladle hydrogen, the section + bake decide
# --------------------------------------------------------------------------- #
def test_hydrogen_flaking_section_and_bake_lever():
    thin = app.hydrogen_flaking_readout(50, 48.0)       # degasses fast → sound
    thick = app.hydrogen_flaking_readout(500, 48.0)     # heavy forging traps it → flakes
    thick_long = app.hydrogen_flaking_readout(500, 400.0)  # the bake lever saves the thick section
    assert thin["flakes"] is False
    assert thick["flakes"] is True
    assert thick_long["flakes"] is False
    # Same ladle hydrogen across the three (geometry/time decide), and the longer bake leaves less residual.
    assert thin["ladle_H_ppm"] == pytest.approx(thick["ladle_H_ppm"])
    assert thick_long["residual_ppm"] < thick["residual_ppm"]


# --------------------------------------------------------------------------- #
# 5. Gas (CO) porosity — same oxygen spec, the carbon decides
# --------------------------------------------------------------------------- #
def test_gas_porosity_carbon_decides_and_deox_lever():
    high_c = app.gas_porosity_readout("1080", 0.0015)   # under-killed high carbon → blows holes
    low_c = app.gas_porosity_readout("8620", 0.0015)    # same light kill, low carbon → sound
    killed = app.gas_porosity_readout("1080", 0.04)     # the deox lever saves the high-carbon heat
    assert high_c["porous"] is True
    assert low_c["porous"] is False
    assert killed["porous"] is False
    # The carbon decides, not the oxygen: the porous high-carbon heat carries LESS oxygen than the sound one.
    assert high_c["oxygen_ppm"] < low_c["oxygen_ppm"]
    assert high_c["supersaturation"] > 1.0


# --------------------------------------------------------------------------- #
# 6. Hot-tearing — same sulfur, the manganese (Mn:S in the last liquid) decides
# --------------------------------------------------------------------------- #
def test_hot_tear_manganese_decides_through_segregation():
    tear = app.hot_tear_readout(0.30, 0.030)            # Mn:S 10 (in spec) — but the segregated film tears
    sound = app.hot_tear_readout(0.66, 0.030)           # Mn:S 22 — the Mushet lever, sound
    assert tear["hot_tear"] is True
    assert sound["hot_tear"] is False
    # Both clear the flat sulfur risk line (same S, in spec) — segregation, not the risk line, decides.
    assert tear["risk"] is False
    assert sound["risk"] is False
    # The segregated film Mn:S falls below stoichiometry for the tearing heat, stays above for the sound one.
    assert tear["film_mn_s"] < tear["stoich"] < sound["film_mn_s"]


# --------------------------------------------------------------------------- #
# 6b. Peritectic surface cracking — the non-monotonic carbon hero + the alloy lever
# --------------------------------------------------------------------------- #
def test_peritectic_non_monotonic_carbon_and_alloy_lever():
    lean = app.peritectic_readout(0.05, False)           # sub-peritectic — solidifies fully δ, sound
    peri = app.peritectic_readout(0.11, False)           # hypo-peritectic — in Wolf's depression band, cracks
    rich = app.peritectic_readout(0.45, False)           # austenitic — sound
    # The counter-intuitive hero: the MIDDLE carbon cracks; both a leaner AND a richer steel cast soundly.
    assert peri["crack"] is True
    assert lean["crack"] is False
    assert rich["crack"] is False
    # The alloy lever: at a FIXED 0.20 %C, ferrite stabilizers (Si+Cr) pull the carbon-equivalent into the band.
    plain = app.peritectic_readout(0.20, False)
    alloyed = app.peritectic_readout(0.20, True)
    assert plain["crack"] is False
    assert alloyed["crack"] is True
    assert alloyed["Cp"] < plain["Cp"]                   # ferrite stabilizers lower the carbon equivalent


# --------------------------------------------------------------------------- #
# 7. Sulfide morphology (signed foil) — same sulfur, the SHAPE decides
# --------------------------------------------------------------------------- #
def test_sulfide_morphology_shape_is_the_lever_not_the_sulfur():
    fm_key = "1144 — resulfurized (S ≈ 0.24 %)"
    plain_key = "1045 — plain (S ≈ 0.020 %)"
    as_rolled = app.sulfide_morphology_readout(fm_key, False)
    shaped = app.sulfide_morphology_readout(fm_key, True)
    plain = app.sulfide_morphology_readout(plain_key, False)
    # Same heat, same sulfur, same MnS volume — only the morphology changed, and it flips the anisotropy
    # WITHOUT touching the machinability (the lever is the shape, not the sulfur level).
    assert as_rolled["anisotropic"] is True
    assert shaped["anisotropic"] is False
    assert as_rolled["free_machining"] is True and shaped["free_machining"] is True
    assert shaped["machinability"] == pytest.approx(as_rolled["machinability"])
    assert shaped["mns_volpct"] == pytest.approx(as_rolled["mns_volpct"])
    # The other end of the trade: the plain heat is tough/isotropic but carries too little MnS to free-machine.
    assert plain["free_machining"] is False
    assert plain["anisotropic"] is False


# --------------------------------------------------------------------------- #
# 8. Wootz / Damascus banding (signed GOOD-impurity foil) — three gates, intent-flagged
# --------------------------------------------------------------------------- #
def test_wootz_three_gates_and_intent_gated_flag():
    in_window = 882.0                                    # mid the 1.5 %C forging window (857–907 °C)
    genuine = app.wootz_readout(1.5, 60.0, in_window)    # all three gates hold → the pattern develops
    clean = app.wootz_readout(1.5, 5.0, in_window)       # V below threshold → forged as wootz but FAILS
    plain_c = app.wootz_readout(0.45, 60.0, 850.0)       # not hypereutectoid → no pattern intent
    too_hot = app.wootz_readout(1.5, 60.0, 977.0)        # above A_cm → cementite dissolves, no intent
    assert genuine["patterned"] is True
    assert genuine["pattern_failed"] is False
    # The flag fires ONLY under intent (forged as wootz) when the trace former falls short — the signed miss.
    assert clean["pattern_failed"] is True
    assert clean["forged_as_wootz"] is True
    # A bar never forged as wootz raises NO flag, even though its former is fine / its carbon is plain.
    assert plain_c["pattern_failed"] is False and plain_c["forged_as_wootz"] is False
    assert too_hot["pattern_failed"] is False and too_hot["forged_as_wootz"] is False
    # The trace 'impurity' is exactly what separates the asset from the miss (same forging, V decides).
    assert genuine["effective_former_ppm"] > genuine["v_threshold"] > clean["effective_former_ppm"]


def test_wootz_readout_survives_sub_hypereutectoid_carbon():
    # Regression: the forging window is defined only for hypereutectoid carbon — the readout must guard the
    # display call so dragging the carbon slider below the eutectoid does not raise (it would crash the panel).
    r = app.wootz_readout(0.40, 60.0, 700.0)
    assert r["hypereutectoid"] is False
    assert r["pattern_failed"] is False


# --------------------------------------------------------------------------- #
# 9. Figure builders — a build-only smoke test, viz-gated (ADR 0002: render is reach)
# --------------------------------------------------------------------------- #
# Mirrors test_app.py / test_app_making.py's layer 3: each *_overview_figure must actually render through
# the plots layer, so a future plots.* signature change can't break the app's st.pyplot calls silently.
@pytest.mark.parametrize("builder", [
    app.impurity_window_overview_figure,
    app.temper_embrittlement_overview_figure,
    app.tme_overview_figure,
    app.hydrogen_flaking_overview_figure,
    app.gas_porosity_overview_figure,
    app.hot_tear_overview_figure,
    app.peritectic_overview_figure,
    app.sulfide_morphology_overview_figure,
    app.wootz_overview_figure,
])
def test_overview_figure_builds_when_viz_present(builder):
    pytest.importorskip("matplotlib").use("Agg")
    from matplotlib import pyplot
    fig = builder()
    assert len(fig.axes) >= 1                             # it actually drew something
    pyplot.close(fig)
