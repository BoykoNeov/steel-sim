"""Integration test for the deox→recovery demo (the F2→F3 seam, front-end).

The demo chains F2's deoxidation (:func:`steel.refining.deoxidize`) into F3's trim
(:func:`steel.ladle.trim_to_grade` with ``couple_deox_recovery=True``): the bath's dissolved oxygen taxes the
*oxidizable* trim alloys' recovery. These checks pin the **readout** — the selectivity (Mn/Si taxed, Cr/Mo
held), the honest modest magnitude (sub-window, no off-grade flag), and the carbon→oxygen coherence — not
merely that the pipeline runs. The banked figure draws the same numbers; per ADR 0002 it is checked only for
"builds without error".
"""
import pytest

from steel.demo_deox_recovery import compute, GRADE, LEAN_GRADE
from steel import ladle as ld
from steel import refining as rf


def test_same_charges_only_the_deox_state_differs():
    d = compute()
    # The hero setup: one tap, one set of charges, two deox states. The under-killed bath sits at higher
    # dissolved oxygen than the well-killed one — that difference is the whole input.
    assert d.well_O < rf.MAX_DISSOLVED_OXYGEN_PPM < d.under_O
    assert d.under.has_defect("porosity-risk") and d.well.is_clean


def test_the_oxygen_tax_is_selective_mn_si_drop_cr_mo_hold():
    d = compute()
    # Selectivity is the headline: the oxidizable Mn/Si land lower in the under-killed bath; the noble Cr/Mo
    # land identically (oxygen-independent recovery).
    assert d.under_Mn < d.well_Mn                            # Mn taxed
    assert d.under.composition.Si < d.well.composition.Si + 1e-9
    # the noble Cr/Mo hold (oxygen-independent recovery); they shift only by the tiny bath-mass dilution
    # coupling, not the oxygen tax, so they are equal to ~1e-3, not to machine precision.
    assert d.under.composition.Cr == pytest.approx(d.well.composition.Cr, abs=1e-3)
    assert d.under.composition.Mo == pytest.approx(d.well.composition.Mo, abs=1e-3)


def test_the_tax_is_modest_and_stays_in_window():
    d = compute()
    # The honest magnitude (the build's point): the Mn tax is a few percent, and the landed Mn stays ABOVE the
    # window floor — sub-window, so no off-grade flag. This is why the gross under-trim hero must be hand-set.
    assert 0.0 < d.mn_loss_pct < 5.0
    assert d.under_Mn > d.mn_floor
    assert not d.under.has_defect(ld.OFF_GRADE)


def test_lower_carbon_grade_is_taxed_more_the_carbon_oxygen_coherence():
    d = compute()
    # The coherence with F2's C–O coupling: the leaner LEAN_GRADE sits at higher dissolved oxygen than GRADE,
    # so the same skipped kill taxes its Mn more — kill-before-you-trim matters most where carbon is lowest.
    assert d.lean_under_O > d.under_O
    assert d.lean_mn_loss_pct > d.mn_loss_pct


def test_demo_records_the_f2_to_f3_trail():
    d = compute()
    # The seam on the trail: tap → (F2) deoxidize → (F3) trim — no heat-treat (this is a front-end recovery
    # readout, not a back-end propagation).
    assert [s.name for s in d.under.history] == ["tap", "deoxidize", "trim"]


def test_demo_figure_arrays_are_aligned():
    d = compute()
    for e in d.elements:
        assert len(d.rec_curves[e]) == len(d.oxygen_grid)
    # the noble curves are flat (oxygen-independent), the oxidizable ones slope down
    assert d.rec_curves["Cr"].min() == pytest.approx(d.rec_curves["Cr"].max())
    assert d.rec_curves["Mn"][0] > d.rec_curves["Mn"][-1]
    for g in d.grades:
        assert len(d.landed_mn[g]) == len(d.oxygen_grid)
    assert set(d.grades) == {GRADE, LEAN_GRADE}


def test_deox_recovery_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import deox_recovery_figure

    fig = deox_recovery_figure(compute())
    assert len(fig.axes) == 2                                # selectivity + landed-Mn panels
    plt.pyplot.close(fig)
