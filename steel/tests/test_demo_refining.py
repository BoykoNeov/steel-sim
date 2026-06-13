"""Integration test for the F2 refining demo (the demo IS the front-to-back integration test).

The demo wires the refining physics (:mod:`steel.refining`) → the F-spine (:mod:`steel.heat_state`) → the
validated back end (:func:`steel.sweep.evaluate`) into one run: refine a heat, and the *carbon* the blow
sets propagates into a divergent heat-treat response (over-blow → soft core). So its compute pipeline is the
check that the validated axis **closes front-to-back**; the gas/inclusion fields are checked for being
*filled* (the user-facing point of F2), not for exact ppm (those are owned by the unit tests). The banked
figure draws the same numbers; per ADR 0002 it is checked only for "builds without error".
"""
import pytest

from steel.demo_refining import compute, TARGET_C, OVERBLOW_C
from steel import heat_state as hs


def test_overblow_carbon_propagates_to_a_back_end_soft_core():
    d = compute()
    # The validated proof: the same oil quench, the same alloy backbone — only the blow's carbon differs.
    # On-spec through-hardens (clears the soft-core spec); the over-blow falls under it. Emergent from the
    # back-end martensite fraction crossing the spec line, not a scripted branch.
    assert not d.on_spec.has_defect(hs.SOFT_CORE)
    assert d.over_blown.has_defect(hs.SOFT_CORE)
    assert d.on_spec_fM >= d.spec > d.over_fM
    assert d.on_spec_HV > d.over_HV + 80.0                  # a substantial hardness loss, not marginal


def test_demo_heats_record_the_full_refining_trail():
    d = compute()
    # The chain, on the trail: charge → blow → kill → degas → (back-end) heat-treat.
    names = [s.name for s in d.on_spec.history]
    assert names == ["hot-metal charge", "decarburize", "deoxidize", "degas", "heat-treat"]


def test_demo_refined_heat_has_every_gas_inclusion_field_filled():
    d = compute()
    # F2's headline deliverable: the fields the spine left None are populated by the time the heat taps.
    h = d.on_spec
    for field in ("oxygen_ppm", "hydrogen_ppm", "nitrogen_ppm",
                  "inclusion_volume_fraction", "inclusion_type"):
        assert getattr(h, field) is not None, f"{field} still None after refining"
    assert h.inclusion_type == "Al2O3"
    assert h.hydrogen_ppm < 2.0                             # the degas beat the flaking limit


def test_demo_deox_hierarchy_and_minimum_are_present():
    d = compute()
    assert [sym for sym, _ in d.hierarchy] == ["Al", "Si", "Mn"]
    assert 0.05 < d.al_min < 0.10                          # the cited Al–O minimum location
    # The interaction curve dips below the dilute cartoon's tail somewhere (the minimum's signature).
    assert min(d.o_vs_al) < d.o_vs_al[-1]


def test_demo_figure_arrays_are_aligned():
    d = compute()
    assert len(d.al_grid) == len(d.o_vs_al) == len(d.o_vs_al_dilute) == len(d.o_vs_al_si)
    assert len(d.carbon_grid) == len(d.o_vs_carbon)
    assert len(d.pressure_grid) == len(d.h_vs_p) == len(d.n_vs_p)
    assert len(d.carbon_axis) == len(d.fM_vs_carbon)
    # The propagation curve must actually cross the spec (so the over-blow point is real, not extrapolated).
    assert d.fM_vs_carbon.min() < d.spec < d.fM_vs_carbon.max()


def test_refining_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import refining_figure

    fig = refining_figure(compute())
    assert len(fig.axes) == 4                               # deox curve + C–O + degassing + propagation
    plt.pyplot.close(fig)
