"""Integration test for the impurity-window demo — closing the P (cold-short) and S (red-short) consequences.

The demo carries the SAME high-phosphorus, sulfurous pig iron through two real refining routes (acid Bessemer
with no manganese vs basic + Mushet + ladle desulfurization) and reads both impurity consequences: phosphorus
through the existing Pickering DBTT law (a propagation), sulfur through the new hot-work verdict. The thesis
the test pins: the acid heat is cold-short AND red-short AND (the signed foil) STRONGER; the basic heat is
clean and workable. The banked figure draws the same numbers — per ADR 0002, only "builds without error".
"""
import pytest

from steel.demo_impurity_window import compute
from steel.heat_state import COLD_SHORT
from steel.hot_work import RED_SHORT
from steel.slag import HIGH_PHOSPHORUS, MN_PER_S


def test_acid_heat_is_cold_short_and_red_short():
    d = compute()
    # The 1856 acid-Bessemer failure: phosphorus retained (the acid slag can't fix it) → cold-short; no
    # manganese → free sulfur → red-short. All three flags ride on the heat after the consequence checks.
    assert d.acid.cold_short and d.acid.red_short
    assert set(d.acid.after_checks.defects) >= {HIGH_PHOSPHORUS, COLD_SHORT, RED_SHORT}


def test_basic_mushet_heat_is_clean_and_workable():
    d = compute()
    # The basic + Mushet + ladle-desulf route makes sound steel: P removed (ductile), sulfur tied as MnS.
    assert not d.basic.cold_short and not d.basic.red_short
    assert d.basic.after_checks.is_clean


def test_the_signed_foil_acid_heat_is_stronger_yet_brittle():
    d = compute()
    # The signed-impurity foil: phosphorus strengthens AND embrittles — so the acid heat out-yields the
    # clean one (even with far less manganese) while being the brittle one. That contrast is the whole point.
    assert d.acid.yield_MPa > d.basic.yield_MPa            # stronger (P in solid solution)
    assert d.acid.dbtt_C > d.basic.dbtt_C                  # yet far more brittle


def test_cold_short_onset_brackets_the_two_heats():
    d = compute()
    # The DBTT crosses service temperature at P* — the clean heat sits below it (ductile), the acid heat
    # above it (cold-short): the consequence is genuinely produced by the phosphorus difference.
    assert d.basic.P < d.P_star < d.acid.P


def test_panel_arrays_show_the_two_mechanisms():
    d = compute()
    assert len(d.P_grid) == len(d.dbtt_vs_P) == len(d.yield_vs_P)
    assert len(d.ratio_grid) == len(d.freeS_vs_ratio)
    # P → cold-short: DBTT rises with phosphorus (and so does yield — the foil drawn on the twin axis).
    assert d.dbtt_vs_P[-1] > d.dbtt_vs_P[0]
    assert d.yield_vs_P[-1] > d.yield_vs_P[0]
    # S → red-short: free sulfur is present at low Mn:S and vanishes at Mushet's 1.71 (the headline tooth).
    assert d.freeS_vs_ratio[0] > 0.0
    assert d.freeS_vs_ratio[-1] == 0.0
    below = d.freeS_vs_ratio[d.ratio_grid < MN_PER_S]
    at_or_above = d.freeS_vs_ratio[d.ratio_grid >= MN_PER_S]
    assert (below[1:] > 0.0).all() and (at_or_above == 0.0).all()


def test_signed_foil_arrows_split_vertically():
    d = compute()
    # Both levers strengthen (Δyield > 0), but phosphorus RAISES DBTT while grain refinement LOWERS it —
    # the arrows go up and down from the shared baseline. The §5b co-improver vs the signed impurity.
    dyP, dtP = d.foil_P_arrow
    dyG, dtG = d.foil_grain_arrow
    assert dyP > 0.0 and dtP > 0.0          # +P: stronger AND brittler
    assert dyG > 0.0 and dtG < 0.0          # refine: stronger AND tougher


def test_impurity_window_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import impurity_window_figure

    fig = impurity_window_figure(compute())
    assert len(fig.axes) >= 4                 # P→DBTT (+ twin yield), S→red-short, foil, window
    plt.pyplot.close(fig)
