"""Integration test for the carbon carry-in demo (a second F3 ladle mistake, front-to-back).

The demo wires the trim arithmetic with the carry-in on (:mod:`steel.ladle`) → the F-spine
(:mod:`steel.heat_state`) → the validated back end (:func:`steel.sweep.evaluate`): trim a 4140 with the
*same charges* two ways, and the ferroalloy carbon grade decides whether the heat lands on its own carbon
band. These checks pin the **verdict**, not merely that the pipeline runs — the high-carbon heat is off-grade
on carbon and a *harder* steel (over-hard, not soft), the low-carbon heat is clean. The banked figure draws
the same numbers; per ADR 0002 it is checked only for "builds without error".
"""
import pytest

from steel.demo_carbon_carry_in import compute, GRADE
from steel import heat_state as hs
from steel import ladle as ld
from steel.sweep import STEELS


def test_high_carbon_trim_lands_off_grade_on_carbon():
    d = compute()
    # The consequence: the carbon the high-carbon ferroalloys carry drags the bath above 4140's carbon
    # ceiling, so off-grade fires on CARBON (the same window machinery the recovery demo uses on the alloys).
    assert d.hc_C > d.c_window[1]                         # above the 0.43 % ceiling
    assert d.hc_off == ("C",)                             # off-grade on carbon specifically
    assert d.hc.has_defect(ld.OFF_GRADE)


def test_low_carbon_trim_carries_the_same_trim_on_grade():
    d = compute()
    # The lever: the SAME charges with refined low-carbon grades keep the heat on its carbon band and on grade.
    lo, hi = d.c_window
    assert lo <= d.lc_C <= hi
    assert d.lc.is_clean


def test_the_verdict_is_over_hard_not_soft_core():
    d = compute()
    # The honest nuance: the over-carbon heat is HARDER (more carbon → more as-quenched hardness), not soft —
    # martensite stays above the spec, so this is the over-hard foil to the recovery-shortfall soft core.
    assert not d.hc.has_defect(hs.SOFT_CORE)
    assert d.hc_HV > d.lc_HV + 40.0                       # a real hardness rise from the carry-in carbon


def test_carry_in_magnitude_is_oom_coherent():
    d = compute()
    # The point is the magnitude: ~0.16–0.18 %C, roughly 40 % of 4140's spec carbon — and the low-carbon
    # grades carry an order of magnitude less. (Cited assays → an OoM coherence number, not a benchmark.)
    assert 0.14 < d.pickup_hc < 0.22
    assert d.pickup_hc > 0.30 * STEELS[GRADE].C           # a sizeable fraction of the grade's carbon
    assert d.pickup_lc < 0.1 * d.pickup_hc                # the low-carbon lever is an OoM cleaner


def test_demo_records_the_full_trim_trail():
    d = compute()
    # The chain on the trail: tap → trim → (back-end) heat-treat — same shape as the recovery demo.
    assert [s.name for s in d.hc.history] == ["tap", "trim", "heat-treat"]


def test_demo_figure_arrays_are_aligned():
    d = compute()
    assert len(d.bar_labels) == len(d.bar_carbon) == 3
    assert len(d.carbon_grid) == len(d.hv_curve)
    # The propagation curve must actually span both operating points (so they ride the validated curve).
    assert d.carbon_grid.min() <= d.lc_C and d.hc_C <= d.carbon_grid.max()
    assert d.hv_curve.max() > d.hv_curve.min()            # hardness genuinely rises with carbon


def test_carbon_carry_in_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import carbon_carry_in_figure

    fig = carbon_carry_in_figure(compute())
    assert len(fig.axes) == 2                             # carbon bars + the hardness propagation
    plt.pyplot.close(fig)
