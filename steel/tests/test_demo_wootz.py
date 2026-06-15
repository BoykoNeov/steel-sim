"""Integration test for the wootz demo — same ultra-high-carbon steel, the trace vanadium decides, end to end.

The demo reads the genuine (V-bearing) and clean (V-poor) cakes forged identically, plus the carbon-gate and
forging-gate cases, all the way to the raised flag. Its compute pipeline is the check that the SAME 1.5 %C steel
forged the SAME way patterns only when the trace vanadium is present (the build's reason to exist — off-spec by
lacking a good impurity), and that dropping the carbon or the forging gate also kills the pattern but raises no
flag (no wootz intent). The banked figure is checked only for "builds without error" (ADR 0002), skipped
without the viz extra.
"""
from __future__ import annotations

import pytest

from steel import wootz as wz
from steel.demo_wootz import compute


@pytest.fixture(scope="module")
def demo():
    return compute()


def test_same_steel_same_forging_trace_vanadium_decides(demo):
    # readings: (label, C, V ppm, effective former, patterned, pattern_failed, hyper, forged_as_wootz)
    genuine, clean, plain, too_hot = demo.readings
    assert genuine[1] == clean[1]                                    # the SAME carbon ...
    assert genuine[7] and clean[7]                                   # ... both forged as wootz ...
    assert genuine[4] and not clean[4]                              # ... only the V-bearing cake patterns
    assert clean[5]                                                 # the clean cake is the flagged miss


def test_three_gates_each_kills_the_pattern(demo):
    genuine, clean, plain, too_hot = demo.readings
    assert genuine[4]                                               # all three gates met → patterns
    assert not clean[4] and clean[5]                                # former gate → fails (flag)
    assert not plain[4] and not plain[5] and not plain[6]           # carbon gate → no pattern, no flag, not hyper
    assert not too_hot[4] and not too_hot[5] and too_hot[6]         # forging gate → no pattern, no flag, hyper


def test_only_the_clean_cake_raises_the_flag(demo):
    # The intent gate, end to end: exactly one of the four cases is the signed-impurity miss.
    assert sum(1 for r in demo.readings if r[5]) == 1
    assert demo.readings[1][5]                                      # the clean modern UHC cake


def test_same_scheil_engine_opposite_sign(demo):
    # the carbide-former enrichment (asset) and the centerline segregation (defect) are BOTH the rising Scheil
    # solid ratio — one engine, two signs; the former piles up > 1 in the interdendritic bands
    assert demo.former_enrichment_curve[-1] > demo.former_enrichment_curve[0]
    assert demo.centerline_defect_curve[-1] > demo.centerline_defect_curve[0]
    assert demo.former_enrichment_at_band > 1.0


def test_forging_window_is_below_acm(demo):
    lo, hi = demo.window
    assert hi < demo.acm_C                                          # the window is below the cementite solvus
    assert lo <= demo.genuine_peak_C <= hi                          # the genuine peak sits inside it
    assert demo.too_hot_peak_C > demo.acm_C                         # the too-hot peak is above it


def test_figure_builds(demo):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from steel.plots import wootz_figure
    fig = wootz_figure(demo)
    assert len(fig.axes) == 4                                       # four panels
