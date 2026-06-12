"""Integration test for the F4 casting demo (the demo IS the front-to-back integration test).

The demo wires the casting physics (:mod:`steel.casting`) → the F-spine (:mod:`steel.heat_state`) → the
validated back end (:func:`steel.sweep.evaluate`) into one run: cast a billet, and a Scheil-segregated
centerline propagates into a divergent heat-treat response. So its compute pipeline is the check that the
**chain closes front-to-back** — a real front-end origin reaches a real back-end divergence — not brittle
exact numbers (those are owned by the casting / back-end unit tests). The banked figure draws those same
numbers; per ADR 0002 it is checked only for "builds without error" and skipped without the viz extra.
"""
import pytest

from steel.demo_casting import compute
from steel import heat_state as hs


def test_demo_segregation_propagates_to_a_centerline_band():
    d = compute()
    # The front-to-back proof: the same casting, same quench, but the enriched centerline is markedly
    # more hardenable than the nominal section — a real divergence the uniform-grade assumption misses.
    assert d.centerline_fM > d.nominal_fM
    assert d.centerline_HV > d.nominal_HV + 40.0            # a substantial hard band (not marginal)


def test_demo_heats_carry_a_real_cast_origin():
    d = compute()
    # Both treated heats trace back to a "cast" origin (the front-end engine produced them), then a
    # "heat-treat" step (the back end consumed them) — the chain, recorded on the trail.
    for h in (d.nominal_treated, d.centerline_treated):
        assert h.history[0].name == "cast"
        assert h.history[-1].name == "heat-treat"


def test_demo_centerline_enriches_substitutional_alloys():
    d = compute()
    nominal = d.section.steel
    centerline = d.section.centerline_heat.composition
    assert centerline.Mn > nominal.Mn and centerline.Mo > nominal.Mo and centerline.Cr > nominal.Cr
    assert centerline.C == nominal.C                       # carbon left at nominal (Scheil over-predicts it)


def test_demo_figure_arrays_are_aligned():
    d = compute()
    n = len(d.fs)
    assert n > 2 and d.fs[0] == 0.0
    for el, arr in d.liquid_ratio.items():
        assert len(arr) == n, f"{el} profile length mismatch"
    assert len(d.modulus_grid) == len(d.time_grid)


def test_casting_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import casting_figure

    fig = casting_figure(compute())
    assert len(fig.axes) == 3                               # segregation + Chvorinov + the band
    plt.pyplot.close(fig)
