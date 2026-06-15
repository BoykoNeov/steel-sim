"""Integration test for the sulfide-morphology demo — same sulfur, the shape decides, end to end.

The demo reads one resulfurized heat as-rolled and shape-controlled, plus a plain heat, all the way to the
raised flag. Its compute pipeline is the check that the SAME heat is free-machining either way but anisotropic
only as-rolled (the build's reason to exist — the lever is the shape, not the sulfur), and that the plain heat
is tough but not free-machining. The banked figure is checked only for "builds without error" (ADR 0002),
skipped without the viz extra.
"""
from __future__ import annotations

import pytest

from steel.demo_sulfide_morphology import compute


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_same_sulfur_the_shape_decides(demo):
    # readings: (label, S, MnS vol%, machinability, free_machining, transverse_ratio, anisotropic, risk)
    rolled, globular, plain = demo.readings
    assert rolled[1] == globular[1]                                # the SAME sulfur (and MnS volume) ...
    assert rolled[2] == pytest.approx(globular[2])
    assert rolled[4] and globular[4]                              # ... both free-machining ...
    assert rolled[6] and not globular[6]                         # ... but anisotropic only as-rolled (the lever)


def test_plain_heat_is_tough_but_not_free_machining(demo):
    _rolled, _globular, plain = demo.readings
    assert not plain[4] and not plain[6]                          # not free-machining, and isotropic
    assert plain[2] < demo.free_machining_floor_volpct           # too little MnS to break the chip


def test_one_mns_two_opposite_signs(demo):
    # machinability rises with MnS volume, short-transverse toughness (elongated) falls with it — by construction
    assert demo.machinability_curve[-1] > demo.machinability_curve[0]
    assert demo.transverse_elongated_curve[-1] < demo.transverse_elongated_curve[0]
    assert demo.transverse_globular_curve[0] == pytest.approx(demo.transverse_globular_curve[-1])  # globular flat


def test_high_sulfur_risk_fires_on_the_free_machining_heat(demo):
    # the demo's disambiguation premise: slag's flat risk is already raised on the resulfurized heat by design
    rolled, globular, plain = demo.readings
    assert rolled[7] is True and globular[7] is True             # risk (index 7) raised on the free-machining heat
    assert plain[7] is False


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import sulfide_morphology_figure
    fig = sulfide_morphology_figure(demo)
    assert len(fig.axes) == 5                                     # four panels + one twin axis (top-left)
