"""Integration test for the F2 Slice-2 slag-partition demo (the working route + the history failures).

The demo wires the partition physics (:mod:`steel.slag`) with Slice 1 (:mod:`steel.refining`) into one run:
the route that works (basic dephos → blow + kill → ladle desulf) drives phosphorus and sulfur below spec,
and the two history failures (acid Bessemer; desulfurize before the kill) retain their tramp and fire a flag.
Unlike Slice 1 there is **no back-end propagation** — P/S are inert downstream — so the demo's check is that
the *chemistry* lands where benchmarked, not that a back-end property moved. The banked figure draws the same
numbers; per ADR 0002 it is checked only for "builds without error".
"""
import pytest

from steel.demo_slag import compute, CHARGE_P, CHARGE_S
from steel import slag as sg


def test_working_route_drives_P_and_S_below_spec():
    d = compute()
    # The route that works: both tramps below their specs, no flag — the clean heat.
    assert d.clean.composition.P < sg.MAX_PHOSPHORUS_PCT
    assert d.clean.composition.S < sg.MAX_SULFUR_PCT
    assert d.clean.is_clean
    # And it actually removed a lot (not a marginal trim).
    assert d.clean.composition.P < 0.2 * CHARGE_P
    assert d.clean.composition.S < 0.5 * CHARGE_S


def test_acid_bessemer_retains_phosphorus():
    d = compute()
    # The Bessemer failure: an acid slag leaves almost all the phosphorus → high-phosphorus flag.
    assert d.acid.composition.P > 0.8 * CHARGE_P                # phosphorus essentially retained
    assert d.acid.has_defect(sg.HIGH_PHOSPHORUS)


def test_desulfurize_before_kill_retains_sulfur():
    d = compute()
    # The out-of-order failure: desulfurizing the still-oxidized heat barely works → high-sulfur flag.
    assert d.early_desulf.composition.S > sg.MAX_SULFUR_PCT
    assert d.early_desulf.has_defect(sg.HIGH_SULFUR)
    # The working route's ladle desulf (low oxygen) clears far more sulfur than the early one (high oxygen).
    assert d.clean.composition.S < 0.5 * d.early_desulf.composition.S


def test_working_route_records_the_full_trail():
    d = compute()
    names = [s.name for s in d.clean.history]
    # The textbook converter sequence: blow first, then dephosphorize at the oxidizing turndown, then kill,
    # then desulfurize in the reducing ladle (the carbon/FeO-consistent order).
    assert names == ["hot-metal charge", "decarburize", "dephosphorize", "deoxidize", "desulfurize"]


def test_manganese_ties_sulfur_as_mns_on_the_clean_heat():
    d = compute()
    # §14 theme B: the clean heat has plenty of Mn (4140 ~0.9 %) → all sulfur reports as benign MnS; the
    # low-Mn foil leaves free sulfur (red-short).
    assert d.mns.forms_mns and d.mns.free_sulfur_pct == 0.0
    assert not d.mns_bad.forms_mns and d.mns_bad.free_sulfur_pct > 0.0


def test_demo_figure_arrays_are_aligned_and_show_the_contrast():
    d = compute()
    assert len(d.B_grid) == len(d.Lp_vs_B)
    assert len(d.o_grid) == len(d.Ls_vs_o)
    assert len(d.contrast_o) == len(d.Lp_contrast) == len(d.Ls_contrast)
    assert len(d.steps) == len(d.p_trail) == len(d.s_trail)
    # The opposite-oxygen contrast must actually appear on the shared axis: L_P rises across the oxygen sweep,
    # L_S falls — the headline tooth, drawn.
    assert d.Lp_contrast[-1] > d.Lp_contrast[0]
    assert d.Ls_contrast[-1] < d.Ls_contrast[0]
    # The residual trail ends below the charge for both tramps.
    assert d.p_trail[-1] < d.p_trail[0] and d.s_trail[-1] < d.s_trail[0]


def test_slag_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import slag_figure

    fig = slag_figure(compute())
    assert len(fig.axes) == 4                                   # L_P–basicity + L_S–oxygen + contrast + trail
    plt.pyplot.close(fig)
