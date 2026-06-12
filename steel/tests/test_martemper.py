"""Phase-6e validation: martempering — austempering's short-hold sibling.

Martempering adds **no new physics and no new constant**: it composes 6d's atlas-anchored bainite
kinetics, Andrews ``Mₛ``, Koistinen–Marburger, the rule-of-mixtures hardness and the frozen heat
engine into a *process* (the same "composed, not modelled" stance as Phase 7 inverse design). So
the triad is consistency + conservation + structural teeth, not a new calibrated number:

* **Consistency** — a sub-``t_crit`` hold is hardness-identical to an ideal nose-missing quench
  (exact by construction); martemper and austemper are one continuous hold-time axis (delegation,
  so byte-identical fractions); ``critical_hold_time`` is the boundary between them.
* **Conservation** — product fractions sum to 1 on :mod:`pathint`'s stable five-key set.
* **Structural teeth** — the nose-avoidance guard is *discriminating* (a finite ``t_crit`` at a
  martempering bath, not the toothless single-curve ∞ — the load-bearing architecture check); the
  feasibility boundary reproduces the textbook section-size limit (thin feasible, 4340's thick
  plate infeasible); and the spatial distortion proxy is far smaller for the martemper than the
  direct quench (the reason the process exists).

Plus the inherited guards (``Mₛ < T_bath < Bs``) and that nothing upstream is perturbed
(austemper byte-identical — martemper only *reads* it).
"""
import math
import warnings

import numpy as np
import pytest

from steel import martemper as mt
from steel import austemper as au
from steel.austemper import ATLAS_STEELS, anchored_reaction
from steel.kinetics import andrews_Ms

STEELS = ("1080", "4340")


def _bath(steel: str, above_Ms: float = 20.0) -> float:
    """A bath temperature inside the martempering window: ``Mₛ + above_Ms`` °C."""
    return andrews_Ms(**ATLAS_STEELS[steel].comp) + above_Ms


# --------------------------------------------------------------------------- #
# Consistency: short hold ≡ ideal quench; martemper/austemper are one axis
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("steel", STEELS)
def test_short_hold_is_hardness_identical_to_ideal_quench(steel):
    # The defining martempering claim: a hold kept under t_crit forms negligible bainite, so the
    # surviving austenite shears to martensite exactly as an ideal (nose-missing) direct quench
    # would. Exact by construction, conditional on nose-avoidance.
    iq = mt.ideal_quench(steel)
    r = mt.martemper(steel, _bath(steel), t_hold=10.0)
    assert r.bainite_safe
    assert r.bainite < mt.BAINITE_CONTAMINATION_TOL
    assert r.martensite == pytest.approx(iq.martensite, abs=1e-3)
    assert r.HV == pytest.approx(iq.HV, abs=0.5)
    assert r.HV == pytest.approx(r.quench_HV, abs=0.5)


@pytest.mark.parametrize("steel", STEELS)
def test_martemper_and_austemper_are_one_hold_time_axis(steel):
    # martemper delegates the hold+cool microstructure to austemper, so the same (steel, T, t)
    # gives byte-identical fractions — the two routes ARE one axis, read at different hold times.
    T = _bath(steel)
    t_hold = 50.0
    r = mt.martemper(steel, T, t_hold)
    a = au.austemper(steel, T, t_hold)
    assert r.bainite == a.bainite
    assert r.martensite == a.martensite
    assert r.retained_austenite == a.retained_austenite
    assert r.HV == a.HV


@pytest.mark.parametrize("steel", STEELS)
def test_critical_hold_time_is_the_martemper_austemper_boundary(steel):
    # At exactly t_crit the hold has formed the contamination tolerance of bainite (the boundary);
    # a longer hold drifts into austempering (bainite_safe flips false), a shorter one stays safe.
    T = _bath(steel)
    t_crit = mt.critical_hold_time(steel, T)
    assert math.isfinite(t_crit) and t_crit > 0.0
    at_crit = mt.martemper(steel, T, t_crit)
    assert at_crit.bainite == pytest.approx(mt.BAINITE_CONTAMINATION_TOL, rel=0.05)
    assert mt.martemper(steel, T, 0.5 * t_crit).bainite_safe
    assert not mt.martemper(steel, T, 3.0 * t_crit).bainite_safe


# --------------------------------------------------------------------------- #
# Conservation: fractions sum to 1 on the stable key set
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("steel", STEELS)
def test_fractions_sum_to_one(steel):
    for res in (mt.martemper(steel, _bath(steel), 30.0), mt.ideal_quench(steel)):
        f = res.fractions()
        assert set(f) == {"ferrite", "pearlite", "bainite", "martensite", "retained_austenite"}
        assert sum(f.values()) == pytest.approx(1.0, abs=1e-9)
        assert all(v >= -1e-12 for v in f.values())


# --------------------------------------------------------------------------- #
# Structural teeth 1: the nose-avoidance guard is discriminating (the architecture check)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("steel", STEELS)
def test_guard_is_discriminating_not_toothless(steel):
    # THE load-bearing check (advisor): the guard uses austemper's anchored bainite kinetics, so
    # t_crit is FINITE at a martempering bath — not the ∞ a toothless single-pearlite-curve guard
    # would give near Mₛ (which would make the whole max-hold prediction vacuous).
    t_crit = mt.critical_hold_time(steel, _bath(steel))
    assert math.isfinite(t_crit)
    assert 1.0 < t_crit < 1.0e6


@pytest.mark.parametrize("steel", STEELS)
def test_bath_window_guards(steel):
    Ms = andrews_Ms(**ATLAS_STEELS[steel].comp)
    Bs = anchored_reaction(steel).Bs
    with pytest.raises(ValueError):
        mt.martemper(steel, Ms - 5.0, 10.0)          # at/below Ms: martensite on the way in
    with pytest.raises(ValueError):
        mt.martemper(steel, Bs + 5.0, 10.0)          # at/above Bs: no bainite reaction (an anneal)


def test_unknown_steel_refused():
    with pytest.raises(ValueError):
        mt.ideal_quench("9999")
    with pytest.raises(ValueError):
        mt.martemper("9999", 300.0, 10.0)


# --------------------------------------------------------------------------- #
# Structural teeth 2: the feasibility boundary (the textbook section-size limit)
# --------------------------------------------------------------------------- #
def test_feasibility_thin_sections_clear_both_steels():
    for steel in STEELS:
        f = mt.feasibility(steel, 0.005)             # 10 mm plate
        assert f.feasible
        assert f.tau_equalize < f.t_crit
        assert math.isfinite(f.tau_equalize)


def test_feasibility_boundary_thick_4340_fails():
    # The teeth: martempering needs hardenability AND a thin section. 4340's deep plate cannot
    # equalise before bainite nucleates (τ_equalize > t_crit), while 1080's huge near-Mₛ t_crit
    # keeps even a thick section feasible.
    thick = 0.020                                    # 40 mm plate
    assert not mt.feasibility("4340", thick).feasible
    assert mt.feasibility("1080", thick).feasible


def test_feasibility_margin_shrinks_with_thickness():
    # A thicker section takes longer to equalise (more conduction), so the safety margin falls.
    margins = [mt.feasibility("4340", L).margin for L in (0.004, 0.008, 0.016)]
    assert margins[0] > margins[1] > margins[2]


# --------------------------------------------------------------------------- #
# Structural teeth 3: the spatial distortion proxy (the reason martempering exists)
# --------------------------------------------------------------------------- #
def test_distortion_gradient_is_far_smaller_for_martemper():
    dc = mt.distortion_comparison("1080", half_thickness=0.010)
    # The direct quench builds a real through-section gradient at the Mₛ crossing; the martemper
    # equalises first, so its gradient nearly vanishes — a large reduction factor, same hardness.
    assert abs(dc.gradient_direct) > 20.0
    assert abs(dc.gradient_martemper) < 5.0
    assert dc.reduction > 8.0


def test_direct_quench_surface_leads_centre_through_Ms():
    # The physical content of "surface transforms first": in a direct quench the surface reaches Mₛ
    # before the centre. The martemper's slow final cool delays the crossing far past the quench.
    dc = mt.distortion_comparison("1080", half_thickness=0.010)
    t_surf = dc.direct.crossing_time("surface", dc.Ms)
    t_cent = dc.direct.crossing_time("center", dc.Ms)
    assert math.isfinite(t_surf) and math.isfinite(t_cent)
    assert t_surf < t_cent
    assert dc.martemper.crossing_time("surface", dc.Ms) > t_cent


def test_slab_history_two_stage_bc_swap_changes_cooling():
    # The two-stage solve swaps the surface BC (bath → slow air) at t_hold: before the swap the
    # surface chases the bath; after it the whole (equalised) section drifts toward room far slower.
    Ms = andrews_Ms(**ATLAS_STEELS["1080"].comp)
    h = mt.slab_thermal_history(0.010, 850.0, mt.cooling.H_WATER, Ms + 20.0,
                                t_hold=100.0, n_t=4000)
    # Centre and surface are within a few °C of each other by the end of the hold (equalised)...
    i_hold = int(np.searchsorted(h.t, 100.0))
    assert abs(h.surface[i_hold] - h.center[i_hold]) < 10.0
    # ...and the section is still well above room — the slow cool has barely begun.
    assert h.center[i_hold] > 150.0


# --------------------------------------------------------------------------- #
# Nothing upstream perturbed: austemper unchanged (martemper only reads it)
# --------------------------------------------------------------------------- #
def test_austemper_unchanged_by_martemper():
    # martemper imports austemper but must not mutate it; a direct austemper call is unaffected.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = au.austemper("1080", 343.3, 600.0)
    assert a.dominant() == "bainite"
    assert a.bainite > 0.9
