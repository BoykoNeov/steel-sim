"""Integration test for the F3 ladle demo (the demo IS the front-to-back integration test).

The demo wires the trim arithmetic (:mod:`steel.ladle`) → the F-spine (:mod:`steel.heat_state`) → the
validated back end (:func:`steel.sweep.evaluate`) into one run: trim a heat to grade, and when the bath
under-recovers the Cr/Mo, the *same* oil quench that through-hardens the on-grade heat lands a soft core. So
its compute pipeline is the check that the validated axis **closes front-to-back** — one ladle mistake
carrying both F3's off-grade flag and the back end's soft-core flag. The banked figure draws the same
numbers; per ADR 0002 it is checked only for "builds without error".
"""
import pytest

from steel.demo_ladle import compute, BAD_RECOVERY_FACTOR
from steel import heat_state as hs
from steel import ladle as ld


def test_under_trim_propagates_to_a_back_end_soft_core():
    d = compute()
    # The validated proof: same oil quench, same section — only the landed Cr/Mo differ (a recovery
    # shortfall). On-grade through-hardens (clears the spec); the under-recovered heat falls under it.
    # Emergent from the back-end martensite fraction crossing the spec line, not a scripted branch.
    assert not d.good.has_defect(hs.SOFT_CORE)
    assert d.bad.has_defect(hs.SOFT_CORE)
    assert d.good_fM >= d.spec > d.bad_fM
    assert d.good_HV > d.bad_HV + 30.0                  # a real hardness loss, not marginal


def test_one_mistake_carries_two_flags():
    d = compute()
    # F3's distinctive point: a single recovery shortfall raises BOTH F3's own off-grade flag (the cited
    # window) and the back end's soft-core flag (the validated consequence). The on-grade heat carries none.
    assert d.good.is_clean
    assert d.bad.has_defect(ld.OFF_GRADE) and d.bad.has_defect(hs.SOFT_CORE)


def test_off_grade_fires_before_soft_core():
    d = compute()
    # The honest ordering (the window is the conservative early warning): every still-in-grade point on the
    # recovery sweep — landed Cr at or above the band floor — STILL clears the soft-core spec at this
    # section. You go off-grade at a milder shortfall than you soft-core.
    in_grade = d.cr_vs_recovery >= d.cr_floor
    assert in_grade.any()
    assert d.fM_vs_recovery[in_grade].min() >= d.spec
    # …and the off-grade hero point is past both lines.
    assert d.bad_point[1] < d.cr_floor                 # landed Cr below the window floor
    assert d.bad_point[2] < d.spec                     # and below the soft-core spec


def test_demo_records_the_full_trim_trail():
    d = compute()
    # The chain, on the trail: tap → trim → (back-end) heat-treat.
    names = [s.name for s in d.good.history]
    assert names == ["tap", "trim", "heat-treat"]


def test_demo_bad_heat_lands_below_the_window_floor():
    d = compute()
    # The under-recovered heat is genuinely off-grade (Cr and Mo both below their floors), not just soft.
    assert set(ld.off_grade_elements(d.bad.composition, "4140")) >= {"Cr", "Mo"}
    assert d.bad_point[0] == BAD_RECOVERY_FACTOR


def test_demo_figure_arrays_are_aligned():
    d = compute()
    assert len(d.recovery_ratio) == len(d.cr_vs_recovery) == len(d.fM_vs_recovery)
    assert len(d.bar_elements) == len(d.bars_tap) == len(d.bars_good) == len(d.bars_bad)
    assert len(d.window_lo) == len(d.window_hi) == len(d.bar_elements)
    # The propagation curve must actually cross the spec (so the soft-core point is real, not extrapolated).
    assert d.fM_vs_recovery.min() < d.spec < d.fM_vs_recovery.max()


def test_ladle_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import ladle_figure

    fig = ladle_figure(compute())
    assert len(fig.axes) == 4                           # trim bars + recovery + propagation + verdict
    plt.pyplot.close(fig)
