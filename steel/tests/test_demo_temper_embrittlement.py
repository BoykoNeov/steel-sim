"""Integration test for the temper-embrittlement demo — the martensitic-P consequence and its four levers.

The demo ranks J-factor susceptibility, runs the four levers (slow-cool/fast-cool/Mo/clean) on one dirty
Ni-Cr heat, and traces the reversibility cycle. There is no strict tooth (the segregation-nose gate failed),
so the checks are that the by-construction verdicts land where the cited mechanism says. The banked figure
draws the same numbers — per ADR 0002, only "builds without error".
"""
import pytest

from steel.demo_temper_embrittlement import compute
from steel.temper_embrittlement import J_SUSCEPTIBLE


def test_ranking_separates_the_victim_from_the_clean_registry():
    d = compute()
    # The registry grades sit below the susceptibility limit; the dirty Ni-Cr heat is the only one above.
    above = [(name, J) for name, J, _ in d.ranking if J >= J_SUSCEPTIBLE]
    assert all("Ni" in name for name, _ in above)          # only the Ni-Cr heats poke past
    assert any(J < J_SUSCEPTIBLE for _, J, _ in d.ranking)  # the registry workhorses are clean


def test_any_one_lever_saves_the_susceptible_heat():
    d = compute()
    # The first lever is the failure (slow cool through the window); the other three each save it.
    assert d.levers[0][1] is True                          # slow-cool → embrittled
    assert all(emb is False for _, emb in d.levers[1:])     # fast-cool / +Mo / clean → tough


def test_reversibility_cycle_embrittles_resets_re_embrittles():
    d = compute()
    states = [emb for _, emb in d.cycle]
    assert states == [True, False, True]                   # embrittle → reset → re-embrittle


def test_temper_embrittlement_figure_builds():
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import temper_embrittlement_figure

    fig = temper_embrittlement_figure(compute())
    assert len(fig.axes) == 4                               # ranking, window, levers, reversibility
    plt.pyplot.close(fig)
