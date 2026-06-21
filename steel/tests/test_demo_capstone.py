"""Integration test for the full-chain capstone demo (the demo IS the integration test).

The capstone threads **one** ``Heat`` from the hot-metal charge through F2 refining, F3 trim, F4 casting,
and the back-end quench (``demo_capstone.compute`` → a sound reference and an over-blown foil). Like the
spine (:mod:`test_demo_heat_state`), it adds no physics, so these checks are **structural** — the seam
composes end to end — not brittle exact numbers (those are owned by each stage's own tests). The teeth:
one continuous, un-rewritten provenance trail; the state fields fill in the right order; the seeded tramp
is driven below spec; the reference lands sound while a single upstream knob propagates to the foil's
finished-part defects. The banked figure is checked only for "builds without error" (ADR 0002).
"""
import pytest

from steel.demo_capstone import compute, run_chain, REF_CARBON, FOIL_CARBON, GRADE, LEAN_BACKBONE
from steel import heat_state as hs
from steel import ladle as ld
from steel.sweep import STEELS

# The whole chain, one Heat — the expected step names in order (origin → … → finished part).
EXPECTED_TRAIL = (
    "hot-metal charge", "decarburize", "dephosphorize", "deoxidize", "degas",
    "desulfurize", "trim", "cast", "heat-treat",
)


def test_reference_is_a_sound_part_end_to_end():
    # The headline: the whole chain composes to spec — a clean, on-grade, through-hardened part.
    d = compute()
    part = d.reference.part
    assert part.is_clean
    assert d.reference.part_martensite >= d.spec               # through-hardened (back-end physics)
    assert ld.is_on_grade(part.composition, GRADE)             # on the 4140 alloy window
    assert part.history[-1].name == "heat-treat" and part.history[-1].in_spec is True


def test_foil_propagates_one_upstream_mistake_to_the_finished_part():
    # A single changed knob (the F2 blow endpoint) surfaces twice downstream: off-grade at the F3 trim,
    # soft-core at the back-end quench — and the soft core is a real martensite-fraction miss.
    d = compute()
    foil = d.foil.part
    assert foil.has_defect(ld.OFF_GRADE)
    assert foil.has_defect(hs.SOFT_CORE)
    assert d.foil.part_martensite < d.spec
    # The off-grade flag was raised at the trim, and it RIDES the cast + heat-treat steps to the part
    # (propagation across the whole chain, not just the step that raised it).
    trim_step = next(s for s in foil.history if s.name == "trim")
    assert ld.OFF_GRADE in trim_step.flags_added
    assert foil.history[-1].name == "heat-treat" and foil.history[-1].in_spec is False


def test_one_continuous_un_rewritten_trail():
    # Both heats carry a single monotonic history of the same nine stages, in order — one Heat, one trail.
    d = compute()
    for part in (d.reference.part, d.foil.part):
        assert tuple(s.name for s in part.history) == EXPECTED_TRAIL


def test_only_the_blow_endpoint_distinguishes_the_two_heats():
    # The contrast is single-variable: the reference lands inside the grade carbon window, the over-blown
    # foil below it — everything else on the two trails is the identical recipe.
    d = compute()
    c_lo, c_hi = ld.GRADE_WINDOWS[GRADE].bands["C"]
    assert c_lo <= d.reference.part.composition.C <= c_hi
    assert d.foil.part.composition.C < c_lo
    # Same chain otherwise: the trims add the same alloys to the same grade window.
    assert ld.is_on_grade(d.reference.part.composition, GRADE)


def test_state_fields_fill_along_the_chain():
    # The carrier accumulates the engines' reads in order: F2 fills gas + inclusions, F3/F4 the grade comp.
    part = compute().reference.part
    assert part.oxygen_ppm is not None and part.oxygen_ppm > 0.0
    assert part.hydrogen_ppm is not None and part.nitrogen_ppm is not None
    assert part.inclusion_volume_fraction is not None and part.inclusion_type is not None
    assert part.temperature_C == 25.0                          # the quenched part sits at bath temperature


def test_front_end_drives_the_seeded_tramp_below_spec():
    # The refining half exists to remove the tramp the hot metal carries — seeded above spec, driven below.
    d = compute()
    p, s = d.reference.p_trail, d.reference.s_trail
    assert p[0] == LEAN_BACKBONE.P and s[0] == LEAN_BACKBONE.S  # the seeded charge
    assert p[0] > d.p_spec and s[0] > d.s_spec                  # genuinely off-spec to begin with
    assert p[-1] < d.p_spec and s[-1] < d.s_spec               # cleared at the cast part
    assert list(p) == sorted(p, reverse=True)                  # monotonically non-increasing along the route
    assert list(s) == sorted(s, reverse=True)


def test_casting_segregation_is_a_harder_band_not_a_soft_core():
    # The same casting's Scheil-enriched centerline is MORE hardenable than the nominal section — the band
    # the back end inherits (uneven hardenability), distinct from the foil's soft core.
    d = compute()
    assert d.reference.centerline_HV > d.reference.part_HV
    assert d.reference.centerline_martensite >= d.reference.part_martensite


def test_run_chain_carbon_targets_match_the_demo_knobs():
    # The two chains are exactly the reference / foil blow endpoints (guards the single-knob contrast).
    assert run_chain(REF_CARBON).part.is_clean
    assert not run_chain(FOIL_CARBON).part.is_clean
    assert REF_CARBON == STEELS[GRADE].C and FOIL_CARBON < REF_CARBON


def test_capstone_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import capstone_figure

    fig = capstone_figure(compute())
    assert len(fig.axes) == 2                                  # the finished-part bars + the P/S trail
    plt.pyplot.close(fig)
