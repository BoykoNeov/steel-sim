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

from projects.steel import app
from projects.steel import sweep


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
def test_figures_build_when_viz_present():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")

    outs = app.single_steel_outcomes("1080")
    fig = app.mechanism_figure(outs, "1080")
    assert len(fig.axes) >= 2                             # paths-on-TTT + microstructure bars
    plt.pyplot.close(fig)

    grid = app.comparison_grid(["1045", "1080", "4140"])
    fig2 = app.comparison_figure(grid)
    assert len(fig2.axes) >= 2                            # hardenability curve + hardness grid
    plt.pyplot.close(fig2)
