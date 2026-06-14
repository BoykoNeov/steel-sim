"""Integration test for the tempered-martensite-embrittlement demo — the irreversible tempering trough.

The demo sweeps the temper axis for a hardened 4140, runs the two gates (carbon + hardenability) at 300 °C, and
traces the irreversibility cycle. There is no strict tooth (the carbide-kinetics trough gate failed), so the
checks are that the by-construction verdicts land where the cited mechanism says. The banked figure draws the
same numbers — per ADR 0002, only "builds without error".
"""
import pytest

from steel.demo_tempered_martensite_embrittlement import compute
from steel.tempered_martensite_embrittlement import TME_WINDOW_C


def test_axis_map_embrittles_exactly_in_the_cited_trough():
    d = compute()
    lo, hi = TME_WINDOW_C
    for T, emb in d.axis_map:
        assert emb == (lo <= T <= hi)              # the verdict tracks the cited window, nothing outside it


def test_two_gates_medium_carbon_embrittles_low_carbon_and_unhardened_do_not():
    d = compute()
    by_label = {lab.split(chr(10))[0]: emb for lab, _C, _M, emb in d.discriminator}
    assert by_label["4140 hardened"] is True       # medium-carbon, hardened → embrittled
    assert by_label["1080 hardened"] is True        # high-carbon, hardened → embrittled
    assert by_label["8620 hardened"] is False       # low carbon (0.20 %C) → immune even fully hardened
    assert by_label["1045 mild quench"] is False    # un-hardened → no tempered martensite to embrittle


def test_irreversibility_cycle_embrittles_recovers_stays_tough():
    d = compute()
    states = [emb for _, emb in d.cycle]
    assert states == [True, False, False]          # embrittle → recover → re-enter trough STAYS tough (one-way)


def test_tempered_martensite_embrittlement_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import tempered_martensite_embrittlement_figure

    fig = tempered_martensite_embrittlement_figure(compute())
    assert len(fig.axes) == 4                       # trough map, two gates, irreversibility, contrast
    plt.pyplot.close(fig)
