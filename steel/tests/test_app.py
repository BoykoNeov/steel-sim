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


def test_grain_morphology_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    gp = app.grain_outcome(1000.0, 1.0, 0.20, 0.75, 0.20)
    fig = app.grain_morphology_overview_figure(gp, name="your steel")
    assert len(fig.axes) == 1                             # a single size-accurate Voronoi swatch
    # the fixed field of view coarsens the picture across the sliders: a hot soak shows fewer
    # grains than a cool one, in the SAME window (the size-accurate point).
    hot = app.grain_morphology_overview_figure(app.grain_outcome(1250.0, 8.0, 0.20, 0.75, 0.20))
    cool = app.grain_morphology_overview_figure(app.grain_outcome(850.0, 0.25, 0.20, 0.75, 0.20))
    assert len(hot.axes[0].collections[0].get_paths()) < len(cool.axes[0].collections[0].get_paths())
    for f in (fig, hot, cool):
        plt.pyplot.close(f)


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
# 9b. The unified-KV bay (§19): the competing-reaction what-if + its readout
# --------------------------------------------------------------------------- #
def test_unified_vocabulary_is_the_atlas_pair_only():
    # The selectbox offers ONLY the atlas-anchored steels — unified_system raises on anything else
    # (the BC / 8620 cross-steel wall), so a dropdown with a third grade would crash the render.
    assert app.UNIFIED_STEELS == list(app.aus.ATLAS_STEELS)
    assert set(app.UNIFIED_STEELS) == {"1080", "4340"}


def test_unified_outcome_threads_the_bay_for_4340():
    # The headline through the app boundary: an intermediate cool lands 4340 bainite-dominant (the
    # bay), a fast quench lands martensite, a very slow cool lands ferrite/pearlite — one helper.
    fast = app.unified_outcome("4340", app.UNIFIED_COOLING["very fast — thin water quench"])
    mid = app.unified_outcome("4340", app.UNIFIED_COOLING["intermediate — air cool"])
    slow = app.unified_outcome("4340", app.UNIFIED_COOLING["very slow — furnace anneal"])
    assert fast.dominant() == "martensite"
    assert mid.dominant() == "bainite" and mid.bainite > 0.5
    assert slow.ferrite > 0.3                              # proeutectoid ferrite fills in
    assert sum(mid.fractions().values()) == pytest.approx(1.0, abs=1e-12)


def test_unified_outcome_opens_no_bay_for_1080():
    # The consistency contrast at the app boundary: 1080 never reaches bainite-dominant on any
    # offered cooling rate (no bay) — the only bulk-bainite route is the austempering hold above.
    doms = {app.unified_outcome("1080", tau).dominant() for tau in app.UNIFIED_COOLING.values()}
    assert "bainite" not in doms


def test_unified_readout_is_display_ready_and_flags_the_bay():
    ur = app.unified_readout(app.unified_outcome("4340", app.UNIFIED_COOLING["intermediate — air cool"]))
    assert set(ur) == {"dominant", "ferrite", "pearlite", "bainite", "martensite",
                       "retained", "C_gamma", "Ms_eff", "bay_hit"}
    assert ur["bainite"].endswith("%") and ur["C_gamma"].endswith("%C")
    assert ur["Ms_eff"].endswith("°C")
    assert ur["bay_hit"] is True and ur["dominant"] == "bainite"


def test_unified_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.unified_overview_figure()
    assert len(fig.axes) == 2                             # the 4340 bay + the 1080 no-bay panels
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


# --------------------------------------------------------------------------- #
# 10. The Jominy end-quench (Phase 2): hardness vs depth, shallow vs deep
# --------------------------------------------------------------------------- #
def test_jominy_read_distances_are_the_standard_points():
    # The select_slider walks the standard ASTM-A255 read points, so a drag lands on a sampled
    # cell (no interpolation). The quenched end is the first, ~25 mm the last of the 16.
    assert app.JOMINY_READ_MM[0] == pytest.approx(1.6, abs=0.1)
    assert app.JOMINY_READ_MM[-1] == pytest.approx(25.4, abs=0.2)
    assert len(app.JOMINY_READ_MM) == 16


def test_jominy_readout_shares_the_end_and_diverges_with_depth():
    curves = app.jominy_traverses()
    near = app.jominy_readout_at(curves, app.JOMINY_READ_MM[0])     # the quenched end
    far = app.jominy_readout_at(curves, 19.0)                       # deep in the bar
    # At the end both steels are ~fully martensitic → both report a hard HRC (the shared-end claim).
    assert all(v["HRC"].endswith("HRC") for v in near["steels"].values())
    assert float(near["steels"]["1045"]["martensite"].rstrip("%")) >= 90
    assert float(near["steels"]["4140"]["martensite"].rstrip("%")) >= 90
    # Deep in the bar 4140 holds its plateau while 1045 has collapsed (less martensite) — divergence.
    f1045 = float(far["steels"]["1045"]["martensite"].rstrip("%"))
    f4140 = float(far["steels"]["4140"]["martensite"].rstrip("%"))
    assert f4140 > f1045
    assert set(near) == {"distance_mm", "steels", "quenched_end"}


def test_jominy_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.jominy_overview_figure(app.jominy_traverses())
    assert len(fig.axes) >= 1
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 11. Martempering (Phase 6e): same hardness as a direct quench, less distortion
# --------------------------------------------------------------------------- #
def test_martemper_vocabulary_is_the_anchored_pair_only():
    # Only the atlas-anchored steels are offered — the same per-steel wall austempering rides.
    assert app.MARTEMPER_STEELS == list(app.aus.ATLAS_STEELS)


def test_martemper_outcome_is_the_distortion_comparison():
    # The headline case from the demo: 1080, a 20 mm plate. The thickness knob is in mm and halves
    # to the model's metres (a 20 mm plate → 0.010 m half-thickness).
    dc = app.martemper_outcome("1080", 20)
    assert dc.half_thickness == pytest.approx(0.010)
    assert dc.reduction > 1.0                             # martemper cuts the surface−centre gradient


def test_martemper_readout_carries_equivalence_and_feasibility():
    mr = app.martemper_readout("1080", app.martemper_outcome("1080", 20))
    assert set(mr) == {"HV", "HRC", "quench_HV", "quench_HRC", "gradient_direct",
                       "gradient_martemper", "reduction", "feasible", "margin", "biot", "Ms"}
    # The equivalence: martemper HV equals the ideal nose-missing quench's HV (exact by construction).
    assert mr["HV"] == mr["quench_HV"]
    assert mr["reduction"].endswith("×") and mr["HV"].endswith("HV")
    # A thin 1080 plate is comfortably feasible; a thick 4340 plate is the textbook limit (infeasible).
    assert mr["feasible"] is True
    thick = app.martemper_readout("4340", app.martemper_outcome("4340", 40))
    assert thick["feasible"] is False                     # 4340's 40 mm plate forms bainite first


def test_martemper_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.martemper_overview_figure(app.martemper_outcome("1080", 20))
    assert len(fig.axes) == 2                             # direct-quench vs martemper histories
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 12. Residual stress (Phase 6f): the solid-mechanics surface-sign reversal
# --------------------------------------------------------------------------- #
def test_residual_vocabulary_is_the_anchored_pair_in_severe_media():
    assert app.RESIDUAL_STEELS == list(app.aus.ATLAS_STEELS)
    # Only severe quenches are offered — a mild one never yields the hot core, so there is no
    # transformation residual to show (the Biot ≳ 1 gate the section's caption names).
    assert app.RESIDUAL_MEDIA == ["water", "oil"]


def test_residual_solves_show_the_surface_sign_reversal():
    # The headline tooth through the app boundary: the SAME plate flips the surface from compression
    # (thermal only) to tension (with the martensite dilatation). n_t kept coarse — the teeth (the
    # signs, ∫σ=0) are resolution-robust, so the test stays fast.
    on, off, marte = app.residual_solves("4340", 50, "water", n_t=800)
    rr = app.residual_readout(on, off, marte)
    assert set(rr) == {"surface_off", "surface_off_kind", "surface_on", "surface_on_kind",
                       "surface_marte", "center_on", "peak", "equilibrium", "Ms", "surface_tension"}
    assert off.surface_stress < 0 < on.surface_stress     # compression OFF → tension ON
    assert rr["surface_tension"] is True
    assert "compression" in rr["surface_off_kind"] and "tension" in rr["surface_on_kind"]
    # Self-equilibrium: the profile integrates to ~0 (machine precision) — conservation, not a fit.
    assert abs(on.mean_stress) < 1.0                      # Pa, vs ~1e8 Pa peak stresses


def test_residual_mild_quench_leaves_no_surface_tension():
    # A mild quench on a thin section never builds the gradient that yields the core → no tension
    # (the section's honest "too mild" branch). This is physics, not a model edge.
    on, off, marte = app.residual_solves("1080", 10, "oil", n_t=800)
    assert app.residual_readout(on, off, marte)["surface_tension"] is False


def test_residual_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    on, off, marte = app.residual_solves("4340", 50, "water", n_t=800)
    fig = app.residual_overview_figure(on, off, marte)
    assert len(fig.axes) == 2
    plt.pyplot.close(fig)


# --------------------------------------------------------------------------- #
# 13. Carburizing (Phase 3c): a hard case over a tough core, set by carbon
# --------------------------------------------------------------------------- #
def test_carburize_outcome_runs_the_mass_mode_chain():
    profile, traverse = app.carburize_outcome(0.8, 8, 925, "oil")
    # Carbon diffused IN: the surface is at the potential, the core stays at the lean default.
    assert profile.C[0] == pytest.approx(0.8, abs=0.05)
    assert profile.C[-1] == pytest.approx(profile.C_core, abs=0.02)
    # The case is harder than the core (the whole point — a carbon gradient, one quench throughout).
    assert traverse.HV[0] > traverse.HV[-1]


def test_carburize_readout_is_display_ready_and_splits_case_from_core():
    cbr = app.carburize_readout(*app.carburize_outcome(0.8, 8, 925, "oil"))
    assert set(cbr) == {"case_depth_C", "case_depth_HRC", "surface_HRC", "surface_HV",
                        "core_HRC", "core_HV", "retained_surface", "D"}
    assert cbr["case_depth_HRC"].endswith("mm") and cbr["surface_HV"].endswith("HV")
    assert cbr["retained_surface"].endswith("%")          # the heavy-case effect, reported
    # A longer cycle deepens the case (√(D·t) scaling) — a real, monotone what-if.
    shallow = app.carburize_readout(*app.carburize_outcome(0.8, 4, 925, "oil"))
    assert (float(cbr["case_depth_C"].rstrip(" mm"))
            > float(shallow["case_depth_C"].rstrip(" mm")))


def test_carburize_overview_figure_builds_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    fig = app.carburize_overview_figure(*app.carburize_outcome(0.8, 8, 925, "oil"))
    assert len(fig.axes) == 3                             # carbon + microstructure + hardness
    plt.pyplot.close(fig)
