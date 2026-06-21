"""Endpoint-consistency (``game.md`` §2/§8) — the knob's τ-curve rides validated F2 endpoints.

The one knob is value-selection on the C–O curve. These pin that the curve is the **validated** engine, not
a game re-derivation: the dissolved-oxygen readout is *exactly* :func:`steel.refining.equilibrium_oxygen`,
it climbs monotonically as carbon falls (the C–O coupling), and the targets the readout names — the grade
window and the C–O product — are the cited F2 numbers. The flavor trajectory is checked for what it must
honour (its endpoints are real); its *shape* is feel and deliberately unpinned.
"""
from game import knobs as kn
from steel import ladle as ld
from steel import refining as ref
from steel.sweep import STEELS


def test_oxygen_curve_is_exactly_the_refining_engine():
    # No game arithmetic on top of the physics: every point on the drawn curve is the engine's own value.
    carbons, oxygens = kn.oxygen_curve()
    assert oxygens == [ref.equilibrium_oxygen(c) for c in carbons]


def test_oxygen_climbs_monotonically_as_carbon_falls():
    # The validated C–O coupling: over-blow (less carbon) → more dissolved oxygen, strictly. This is the
    # whole reason over-blowing is a real mistake, not a game penalty.
    carbons, oxygens = kn.oxygen_curve()
    # carbons ascend; oxygens must strictly descend along them (more carbon → less oxygen).
    assert all(b > a for a, b in zip(carbons, carbons[1:]))
    assert all(o_hi < o_lo for o_lo, o_hi in zip(oxygens, oxygens[1:]))


def test_the_named_targets_are_the_cited_F2_numbers():
    # The "turning point" the readout names is physics, not feel: the grade window and aim are ladle's
    # cited band, the C–O product is refining's. The game stores none of these — it reads them live.
    assert kn.grade_carbon_window() == tuple(float(x) for x in ld.GRADE_WINDOWS[kn.GRADE].bands["C"])
    assert kn.grade_carbon_aim() == STEELS[kn.GRADE].C
    assert kn.carbon_oxygen_product() == ref.carbon_oxygen_product()


def test_endpoint_position_zones_track_the_window():
    lo, hi = kn.grade_carbon_window()
    assert kn.endpoint_position((lo + hi) / 2).zone == "on-aim"
    assert kn.endpoint_position(lo - 0.05).zone == "over-blow"     # carbon below the floor
    assert kn.endpoint_position(hi + 0.05).zone == "under-blow"    # carbon above the ceiling
    # the readout's oxygen is the live engine value, not a stored one
    assert kn.endpoint_position(0.30).oxygen_ppm == ref.equilibrium_oxygen(0.30)


def test_blow_trajectory_runs_between_real_endpoints():
    # The flavor shape is unpinned, but its ENDS must be honest: it starts at the real charge carbon and
    # lands at the player's endpoint (the over-/under-shoot region around them is the only feel).
    target = 0.40
    progress, carbons = kn.blow_trajectory(target)
    assert progress[0] == 0.0 and progress[-1] == 1.0
    assert abs(carbons[0] - kn.CHARGE_CARBON) < 1e-9               # starts at the real charge
    assert abs(carbons[-1] - target) < 1e-9                        # lands exactly on the chosen endpoint
    assert all(b <= a + 1e-9 for a, b in zip(carbons, carbons[1:]))  # monotone falling (a blow only removes C)
