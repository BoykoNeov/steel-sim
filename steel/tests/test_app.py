"""Tests for the Streamlit what-if app (Steel plan §9, slice 2).

``app.py`` adds **no new physics** — it re-skins the :mod:`sweep` harness, each step of which
is sealed behind its own validation triad. Per ADR 0002 the *UI itself is not unit-tested*
(``main()`` needs the Streamlit runtime). What these tests cover is the part that must stay
correct and headless: the **compute helpers** — and they are deliberately **always-green**
(not gated like the notebook), because the helpers import neither Streamlit nor matplotlib,
so they run on a bare core install exactly like the ``sweep`` tests.

The one structural guard worth its own test: importing ``app`` must **not** pull Streamlit.
``streamlit run`` aside, the whole layering (compute headless, ``import streamlit`` confined
to ``main()``) collapses if a top-level ``import streamlit`` creeps back in — so we assert the
module imported without it. (Streamlit is an optional ``[app]`` dependency; in a clean test
environment it is absent, which makes this assertion exact.)
"""
import math
import sys

import numpy as np
import pytest

from steel import app
from steel import sweep


# --------------------------------------------------------------------------- #
# 0. The layering guard — importing app must not require/trigger streamlit
# --------------------------------------------------------------------------- #
def test_importing_app_does_not_import_streamlit():
    # The load-bearing discipline: the compute layer is headless and `import streamlit` is
    # confined to main(). If it imported at module top, the helpers (and this whole suite)
    # would need the optional [app] extra. Importing app above must leave streamlit unloaded.
    assert "streamlit" not in sys.modules
    assert callable(app.main)                       # the entry point exists, but we never call it
    # The dropdown vocabularies are the real-composition registry (no Mn=0 leaner-hypothetical).
    assert app.GRADES == list(sweep.STEELS)
    assert app.MEDIA == list(sweep.DEFAULT_MEDIA)


# --------------------------------------------------------------------------- #
# 1. The single-steel mechanism data — one grade down the cooling-rate axis
# --------------------------------------------------------------------------- #
def test_single_steel_outcomes_is_the_cooling_rate_axis():
    outs = app.single_steel_outcomes("1080")
    assert [o.medium for o in outs] == app.MEDIA          # furnace → air → oil → water
    # Conservation passthrough: every outcome partitions the austenite.
    for o in outs:
        assert sum(o.fractions().values()) == pytest.approx(1.0, abs=1e-12)
    # Faster quench → harder (in HV, defined everywhere) — the dramatic axis.
    HV = [o.HV for o in outs]
    assert HV == sorted(HV)
    # The four share one composition-determined C-curve (so mechanism_figure can take outs[0]).
    assert all(o.ccurve.Ms == outs[0].ccurve.Ms for o in outs)
    assert all(o.ccurve.tau_factor == outs[0].ccurve.tau_factor for o in outs)


def test_single_steel_outcomes_honours_section_size():
    # A thicker section cools slower → lower Vr at a fixed medium (the diameter knob is wired).
    thin = app.single_steel_outcomes("4140", diameter=0.005)
    thick = app.single_steel_outcomes("4140", diameter=0.050)
    # Compare the same (oil) column; both finite cooling rates.
    oil_thin = next(o for o in thin if o.medium == "oil")
    oil_thick = next(o for o in thick if o.medium == "oil")
    assert oil_thick.Vr < oil_thin.Vr


# --------------------------------------------------------------------------- #
# 2. The single what-if + the hardness readout (the nan/HRC formatting lives here)
# --------------------------------------------------------------------------- #
def test_evaluate_one_and_readout_for_a_hard_quench():
    out = app.evaluate_one("4140", "water")
    r = app.hardness_readout(out)
    assert r["HV"].endswith("HV")
    assert "HRC" in r["HRC"]                              # 4140 water → on-scale hard, real HRC
    assert math.isfinite(out.HRC)
    assert sum(r["fractions"].values()) == pytest.approx(1.0, abs=1e-12)
    assert r["dominant"] in ("martensite", "retained austenite")


def test_readout_reports_soft_tail_off_scale():
    # A slow-cooled lean steel is soft (pearlite) — below the ~20 HRC floor, HRC is undefined.
    # The readout must say so honestly rather than print a nan number.
    out = app.evaluate_one("1045", "furnace")
    assert not math.isfinite(out.HRC)
    assert app.hardness_readout(out)["HRC"] == "off HRC scale (soft)"
    assert app.format_hrc(float("nan")) == "off HRC scale (soft)"
    assert app.format_hrc(45.0) == "45 HRC"


def test_readout_carries_the_biot_flag():
    # A severe quench of a thick section is beyond the 0-D lumped range — surfaced, not hidden.
    out = app.evaluate_one("1045", "water", diameter=0.05)
    r = app.hardness_readout(out)
    assert r["lumped_valid"] is False and r["biot"] >= 0.1


# --------------------------------------------------------------------------- #
# 3. The comparison grid
# --------------------------------------------------------------------------- #
def test_comparison_grid_shape_and_indexing():
    grid = app.comparison_grid(["1045", "4140"])
    assert len(grid) == 2 and all(len(row) == len(app.MEDIA) for row in grid)
    assert grid[0][0].steel.name == "1045"
    assert grid[1][0].steel.name == "4140"
    # The hardenability divergence at the intermediate (oil) column — alloy keeps more martensite.
    oil_lean = next(o for o in grid[0] if o.medium == "oil")
    oil_alloy = next(o for o in grid[1] if o.medium == "oil")
    assert oil_alloy.result.martensite > oil_lean.result.martensite


# --------------------------------------------------------------------------- #
# 4. The temper curve data (plain columns for st.line_chart)
# --------------------------------------------------------------------------- #
def test_temper_curve_data_columns_are_consistent():
    td = app.temper_curve_data("4140", t_hours=1.0)
    n = len(td["temper_C"])
    assert n > 1
    for key in ("HV", "HRC", "UTS_MPa", "toughness"):
        assert len(td[key]) == n                          # equal length → chartable as columns
    # Tempering softens monotonically; toughness rises (the trade-off).
    assert np.all(np.diff(td["HV"]) <= 0)
    assert np.all(np.diff(td["toughness"]) >= 0)
    # The left limit is the as-quenched value (the byte-exact sub-onset seam).
    assert td["HV"][0] == pytest.approx(td["HV_as_quenched"])
    # Temper time threads through: a longer hold at fixed temperature softens at least as much
    # (more time on the Hollomon–Jaffe curve). (The same-carbon "alloy resists tempering"
    # physics is validated upstream in test_sweep, not re-asserted here — harness test, not physics.)
    longer = app.temper_curve_data("4140", t_hours=4.0)
    assert np.all(longer["HV"] <= td["HV"] + 1e-9)


# --------------------------------------------------------------------------- #
# 5. Figure builders — a build-only smoke test, viz-gated (ADR 0002: render is reach)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("grade", app.GRADES)
def test_mechanism_figure_builds_for_every_selectable_grade(grade):
    # The app lets a user pick ANY registry grade as the single steel, so the mechanism figure
    # must build for each — not just 1080 (the four-curves reference). 8620/4140 push the
    # 1080-calibrated C-curve into regimes (0.2 %C, heavy hardenability shift) the demo never
    # exercises; the helpers finite-filter, but assert it rather than infer it.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.mechanism_figure(app.single_steel_outcomes(grade), grade)
    assert len(fig.axes) >= 2                             # paths-on-TTT + microstructure bars
    plt.pyplot.close(fig)


def test_comparison_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    grid = app.comparison_grid(["1045", "1080", "4140"])
    fig = app.comparison_figure(grid)
    assert len(fig.axes) >= 2                             # hardenability curve + hardness grid
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 6. UTS / toughness now surfaced in the readout (the strength/toughness consequence)
# --------------------------------------------------------------------------- #
def test_format_uts_is_honest_off_scale():
    assert app.format_uts(1200.0) == "1,200 MPa"
    assert app.format_uts(float("nan")) == "off-scale (as-quenched)"


def test_readout_carries_uts_and_toughness():
    # A soft slow-cooled steel has a real ISO-18265 UTS; toughness is a finite [0, 1] proxy.
    soft = app.hardness_readout(app.evaluate_one("1045", "furnace"))
    assert soft["UTS"].endswith("MPa")
    assert 0.0 <= float(soft["toughness"]) <= 1.0
    # As-quenched hard martensite is past the ISO band — surfaced as off-scale, not a nan number.
    hard = app.hardness_readout(app.evaluate_one("4140", "water"))
    assert hard["UTS"] == "off-scale (as-quenched)"


# --------------------------------------------------------------------------- #
# 7. Build-your-own: the free-composition what-if + its readout + the guardrails
# --------------------------------------------------------------------------- #
def test_custom_steel_outcome_runs_the_chain_at_the_discriminating_medium():
    out = app.custom_steel_outcome(0.45, 0.75, 0.0, 0.0, 0.0)
    assert out.medium == sweep.DISCRIMINATING_MEDIUM    # oil — never the saturated ends
    assert out.steel.name == "your steel"
    assert sum(out.fractions().values()) == pytest.approx(1.0, abs=1e-12)  # conservation passthrough


def test_custom_composition_threads_hardenability():
    # Adding alloy (Cr/Mo) at fixed C/Mn must slide the C-curve right (tau_factor up) — the
    # hardenability payoff, threaded composition → kinetics. tau_factor is the robust signal
    # (guaranteed by the kinetics regardless of saturation); martensite follows non-decreasing.
    lean = app.custom_steel_outcome(0.45, 0.75, 0.0, 0.0, 0.0)
    alloy = app.custom_steel_outcome(0.45, 0.75, 1.0, 0.20, 0.0)
    assert alloy.ccurve.tau_factor > lean.ccurve.tau_factor
    assert alloy.result.martensite >= lean.result.martensite


def test_custom_readout_is_display_ready():
    cr = app.custom_readout(app.custom_steel_outcome(0.45, 0.75, 1.0, 0.20, 0.0))
    assert set(cr) == {"Ms", "hardenability", "martensite", "HV", "HRC", "UTS", "toughness"}
    assert cr["Ms"].endswith("°C") and cr["hardenability"].endswith("×")
    assert cr["martensite"].endswith("%") and cr["HV"].endswith("HV")


def test_composition_warnings_flags_the_envelope():
    # Inside the calibration envelope (a 1045-like chemistry) — no caution.
    assert app.composition_warnings(0.45, 0.75, 0.0, 0.0, 0.0) == []
    # Sub-floor Mn is the *programmatic* guard: main() floors the slider at MN_FLOOR, so a drag
    # cannot reach this — but a direct call must still flag the leaner-hypothetical trap.
    low_mn = app.composition_warnings(0.45, app.MN_FLOOR - 0.1, 0.0, 0.0, 0.0)
    assert any("Mn" in w for w in low_mn)
    # Heavy alloy past the calibration grades is the live, UI-reachable caution.
    heavy = app.composition_warnings(0.45, 0.75, 2.0, 0.5, 0.0)
    assert any("beyond the calibration grades" in w for w in heavy)


def test_custom_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.custom_figure(app.custom_steel_outcome(0.45, 0.75, 1.0, 0.20, 0.0))
    assert len(fig.axes) >= 2                             # path-on-TTT + schematic swatch
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 8. Grain size (Phase 5): the austenitize → grain → yield + DBTT what-if
# --------------------------------------------------------------------------- #
def test_grain_outcome_runs_the_coupled_chain():
    # The grain helper is a pure re-composition of the validated 5c coupling — a hotter / longer
    # hold must coarsen the grain (the over-austenitizing direction), nothing more invented here.
    cool = app.grain_outcome(900.0, 1.0, 0.20, 0.75, 0.20)
    hot = app.grain_outcome(1200.0, 1.0, 0.20, 0.75, 0.20)
    assert hot.pags_um > cool.pags_um
    assert hot.ferrite_um > cool.ferrite_um < cool.pags_um   # ferrite finer than its parent PAGS
    # The co-benefit / penalty: the finer (cooler) hold is stronger AND tougher (lower DBTT).
    assert cool.yield_MPa > hot.yield_MPa
    assert cool.dbtt_C < hot.dbtt_C


def test_grain_readout_is_display_ready_and_flags_brittleness():
    gr = app.grain_readout(app.grain_outcome(900.0, 1.0, 0.20, 0.75, 0.20))
    assert set(gr) == {"pags", "ferrite", "yield", "dbtt", "at_room", "brittle", "f_pearlite"}
    assert gr["ferrite"].endswith(")") and "ASTM G" in gr["ferrite"]   # µm + grain-size number
    assert gr["yield"].endswith("MPa") and gr["dbtt"].endswith("°C")
    # A cool, normalized hold is ductile at room temperature; an over-austenitized one is brittle.
    cool = app.grain_readout(app.grain_outcome(900.0, 1.0, 0.20, 0.75, 0.20))
    hot = app.grain_readout(app.grain_outcome(1250.0, 1.0, 0.20, 0.75, 0.20))
    assert cool["brittle"] is False and cool["at_room"] == "ductile at room temperature"
    assert hot["brittle"] is True and hot["at_room"] == "brittle at room temperature"


def test_grain_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    gp = app.grain_outcome(1000.0, 1.0, 0.20, 0.75, 0.20)
    fig = app.grain_overview_figure(gp, 0.20, {"Mn": 0.75, "Si": 0.20}, name="your steel")
    assert len(fig.axes) == 3                             # grain-growth panel + yield/DBTT twin axis
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 9. Austempering (Phase 6d): the anchored hold what-if + its readout + the UI guards
# --------------------------------------------------------------------------- #
def test_austemper_vocabulary_is_the_anchored_table_only():
    # The dropdown offers ONLY atlas-anchored steels — cross-composition BC is probe-falsified,
    # so a free-composition austemper would dress an invalid extrapolation as a knob.
    assert app.AUSTEMPER_STEELS == ["1080", "4340"]
    # The slider clamp keeps every reachable hold strictly inside (Ms, Bs) — the refuse-guards
    # are programmatically unreachable from a drag (the MN_FLOOR pattern).
    for steel in app.AUSTEMPER_STEELS:
        Ms, Bs = app.austemper_window(steel)
        assert Ms + app.AUSTEMPER_T_MARGIN < Bs - app.AUSTEMPER_T_MARGIN   # a real window survives
        r = app.austemper_outcome(steel, Ms + app.AUSTEMPER_T_MARGIN, 60.0)
        assert 0.0 <= r.bainite <= 1.0


def test_austemper_outcome_suppresses_the_warning_but_carries_the_flag():
    # A high hold near Bs: the helper must not leak the console UserWarning (st.warning surfaces
    # the structured flag instead), but the flag and shadow must arrive on the result.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")                    # any escaped warning fails the test
        r = app.austemper_outcome("1080", 480.0, 100.0)
    assert r.pearlite_race_flagged


def test_austemper_readout_is_display_ready():
    ar = app.austemper_readout(app.austemper_outcome("1080", 343.0, 600.0))
    assert set(ar) == {"bainite", "martensite", "retained", "HV", "HRC", "dominant",
                       "t50", "min_full_hold", "window", "race_flagged", "race_shadow"}
    assert ar["bainite"].endswith("%") and ar["HV"].endswith("HV")
    assert ar["t50"].endswith("s") and ar["min_full_hold"].endswith("s")
    assert ar["race_flagged"] is False                    # the anchored band is quiet
    assert ar["dominant"] == "bainite"                    # the classic hold goes fully bainitic


def test_austemper_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.austemper_overview_figure("4340", 380.0, 600.0)
    assert len(fig.axes) == 3                             # diagram + U(t) + hardness-vs-hold
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 10. Inverse design (Phase 7): the hardness-spec → recipe what-if + its readout
# --------------------------------------------------------------------------- #
def test_design_outcome_inverts_to_recipes_in_band():
    # The helper is a pure inversion of the validated forward chain — every recipe it returns must
    # actually meet the band (the harness invariant, re-asserted at the app boundary).
    res = app.design_outcome(45.0, 2.0, 10.0)             # ~45 HRC in a 10 mm section
    assert res.feasible
    lo, hi = res.target_band
    assert all(lo <= r.HV <= hi for r in res.recipes)
    # The section-size knob is in mm and wired through to metres (a thick section is harder to hit).
    assert res.diameter == pytest.approx(0.010)


def test_design_outcome_reports_infeasible_honestly():
    # An out-of-envelope spec returns an EMPTY set (no near-miss) — the first-class infeasible.
    res = app.design_outcome(60.0, 1.0, 60.0)             # ~60 HRC bulk in a 60 mm section
    assert not res.feasible and res.recipes == ()


def test_design_readout_is_display_ready():
    dr = app.design_readout(app.design_outcome(45.0, 2.0, 10.0), 45.0, 2.0)
    assert set(dr) == {"target", "band_HV", "feasible", "n", "recommended",
                       "recommended_hardness", "recommended_valid", "rows"}
    assert dr["target"] == "45 ± 2 HRC" and dr["band_HV"].endswith("HV")
    assert dr["feasible"] and dr["n"] == len(dr["rows"])
    # Each table row is fully formatted strings (main() forwards them, formats nothing).
    row = dr["rows"][0]
    assert set(row) == {"recipe", "HV", "HRC", "rel. cost", "0-D model"}
    assert "4140" in dr["recommended"]                    # the textbook Q&T answer


def test_design_readout_handles_infeasible_without_crashing():
    dr = app.design_readout(app.design_outcome(60.0, 1.0, 60.0), 60.0, 1.0)
    assert dr["feasible"] is False
    assert dr["recommended"] is None and dr["rows"] == []


def test_design_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.design_overview_figure(app.design_outcome(45.0, 2.0, 10.0))
    assert len(fig.axes) >= 2                             # feasibility map + ranked recipes
    plt.pyplot.close(fig)
