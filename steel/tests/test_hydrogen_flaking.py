"""Unit tests for the hydrogen-flaking consequence — the OoM coherence tooth + by-construction verdict.

Honest map (mirrors the module docstring):
  * the **one genuine tooth** is the soft, OoM cross-source coherence — D_H pinned to the room-T α-Fe lattice
    value reproduces cited bake-vs-section practice (~1 h/inch; heavy forgings days) without tuning;
  * the ``τ ∝ L²`` scaling and the flaking verdict are **by construction**;
  * the section-size and bake levers are the demonstration (same hydrogen, geometry/schedule decide).

All analytic (closed-form slab desorption) — no solver, fast lane.
"""
from __future__ import annotations

import math

import pytest

from steel import hydrogen_flaking as hf
from steel import refining
from steel.heat_state import Heat
from steel.sweep import STEELS


# --------------------------------------------------------------------------- #
# The cited input — D_H pinned INDEPENDENTLY of bake practice (the basis of the tooth)
# --------------------------------------------------------------------------- #
def test_diffusivity_reproduces_accepted_room_temperature_lattice_value():
    # the pin: ~8–9×10⁻⁹ m²/s at 25 °C (accepted α-Fe lattice value) — set without reference to bake times
    assert 5e-9 < hf.hydrogen_diffusivity(25.0) < 2e-8


def test_diffusivity_increases_with_temperature():
    assert hf.hydrogen_diffusivity(650.0) > hf.hydrogen_diffusivity(25.0)


# --------------------------------------------------------------------------- #
# THE TOOTH (soft, OoM): the pinned D_H reproduces cited bake-vs-section practice, no tuning
# --------------------------------------------------------------------------- #
def test_dehydrogenation_time_matches_cited_practice_order_of_magnitude():
    one_inch_h = hf.dehydrogenation_time(0.0254 / 2.0) / 3600.0      # ~1 h/inch rule
    heavy_forging_h = hf.dehydrogenation_time(0.500 / 2.0) / 3600.0  # 500 mm → "days"
    assert 0.1 < one_inch_h < 5.0                                    # order ~1 hour
    assert heavy_forging_h > 100.0                                   # order days


def test_section_size_scaling_is_L_squared():
    """By construction: dehydrogenation time scales as section² — ×4 per doubling (Chvorinov-M² class)."""
    t1 = hf.dehydrogenation_time(0.05)
    t2 = hf.dehydrogenation_time(0.10)
    assert 3.7 < t2 / t1 < 4.3


# --------------------------------------------------------------------------- #
# The analytic slab desorption closed forms
# --------------------------------------------------------------------------- #
def test_residual_fractions_start_full_and_decay():
    D = hf.hydrogen_diffusivity(650.0)
    assert hf.centre_residual_fraction(D, 0.0, 0.05) == pytest.approx(1.0)
    assert hf.mean_residual_fraction(D, 0.0, 0.05) == pytest.approx(1.0)
    # after a long time both → 0, and the mean (whole part) is below the centre (the core degasses last)
    t = 50.0 * 3600.0
    centre = hf.centre_residual_fraction(D, t, 0.05)
    mean = hf.mean_residual_fraction(D, t, 0.05)
    assert 0.0 <= mean < centre < 1.0


# --------------------------------------------------------------------------- #
# The demonstration — same hydrogen, the section and the bake decide
# --------------------------------------------------------------------------- #
def test_same_hydrogen_thin_sound_thick_flakes():
    H0 = 5.0
    thin = hf.flaking_assessment(H0, 0.025, hold_time_s=48 * 3600.0)
    thick = hf.flaking_assessment(H0, 0.250, hold_time_s=48 * 3600.0)
    assert not thin.flakes                       # thin degasses below the limit
    assert thick.flakes                          # thick traps it
    assert thick.residual_centre_ppm > thin.residual_centre_ppm


def test_bake_lever_saves_the_thick_section():
    H0 = 5.0
    short = hf.flaking_assessment(H0, 0.250, hold_time_s=48 * 3600.0)
    long = hf.flaking_assessment(H0, 0.250, hold_time_s=600 * 3600.0)
    assert short.flakes and not long.flakes
    assert long.residual_centre_ppm < short.residual_centre_ppm


def test_clean_heat_is_sound_regardless_of_section():
    # hydrogen already below the limit → sound even with no bake in a thick section
    a = hf.flaking_assessment(1.5, 0.250, hold_time_s=0.0)
    assert not a.flakes


# --------------------------------------------------------------------------- #
# The orchestrator seam + the two-tier flag (risk → consequence)
# --------------------------------------------------------------------------- #
def _degassed_heat(p_H2: float = 0.02) -> Heat:
    return refining.degas(Heat(composition=STEELS["4140"]), p_H2=p_H2)


def test_two_tier_flag_risk_then_consequence():
    heat = _degassed_heat()
    assert heat.has_defect(refining.HYDROGEN_FLAKING_RISK)            # F2 chemistry-state risk
    thin = hf.hydrogen_flaking_check(heat, half_thickness=0.025, hold_time_s=48 * 3600.0)
    thick = hf.hydrogen_flaking_check(heat, half_thickness=0.250, hold_time_s=48 * 3600.0)
    assert not thin.has_defect(hf.HYDROGEN_FLAKING)                   # thin: risk only, no consequence
    assert thick.has_defect(hf.HYDROGEN_FLAKING)                      # thick: risk AND the flaking consequence
    assert thick.has_defect(refining.HYDROGEN_FLAKING_RISK)           # the upstream flag is carried forward


def test_orchestrator_appends_step_and_preserves_composition():
    heat = _degassed_heat()
    out = hf.hydrogen_flaking_check(heat, half_thickness=0.250, hold_time_s=48 * 3600.0)
    assert out.history[-1].name == "hydrogen-flaking-check"
    assert out.composition == heat.composition                        # out-diffusion moves trace H, not alloy


def test_orchestrator_idempotent_flag():
    heat = _degassed_heat()
    once = hf.hydrogen_flaking_check(heat, half_thickness=0.250, hold_time_s=48 * 3600.0)
    twice = hf.hydrogen_flaking_check(once, half_thickness=0.250, hold_time_s=48 * 3600.0)
    assert twice.defects.count(hf.HYDROGEN_FLAKING) == 1


def test_orchestrator_requires_hydrogen_state():
    bare = Heat(composition=STEELS["4140"])                           # no F2 degas → no hydrogen_ppm
    with pytest.raises(ValueError):
        hf.hydrogen_flaking_check(bare, half_thickness=0.05, hold_time_s=0.0)
