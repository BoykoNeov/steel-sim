"""Tests for fracture.py — the inclusion as quench-crack initiator (B1, residual × cleanliness coupling).

Honest map (mirrors the module docstring):

  * there is **NO claimable tooth** — the surface-sign reversal and the martemper benefit are *consumed*
    from :mod:`steel.residual` (downstream of its formula sign), the LEFM relation and Murakami's √area
    factor are *cited*, and the as-quenched ``K_Ic`` / martensite-yield / clean-dirty ``√area`` are
    *representative* (the absolute threshold ∝ K_Ic² is a named scope edge);
  * so the checks here are **structural / discriminating**: the LEFM primitives are self-consistent
    (``K`` and ``√area_c`` invert each other), the two-factor gate **discriminates clean from dirty in the
    same residual field** (the load-bearing design call — it must NOT collapse to ``residual.crack_risk``),
    the gate is monotone in section size and cleanliness, the **route lever** (martemper) and the
    **thermal-only** reference clear the crack via the surface stress, and the atlas-steel guard holds.

The §18 phase-split residual solve is the only slow leg → the coupled-assessment tests are marked ``slow``;
the closed-form LEFM-primitive tests stay in the fast lane.
"""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

from steel import fracture as fr
from steel.heat_state import QUENCH_CRACK, QUENCH_CRACK_RISK, Heat, quench_crack_check
from steel.sweep import STEELS

# A thick 4340 section is the heavy-section quench-crack hero (the through-hardener that reaches the
# crack-driving surface tension under the phase-split solve).
STEEL = "4340"
HT = 0.05  # half-thickness (m) → 100 mm plate
_4340_COMP = replace(STEELS["4140"], C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33, name="4340")


# --------------------------------------------------------------------------- #
# The LEFM primitives — closed form, cited relations, self-consistent (fast lane)
# --------------------------------------------------------------------------- #
def test_critical_flaw_inverts_the_stress_intensity():
    # CITED/STRUCTURAL: a flaw exactly at √area_c carries K = K_Ic (the two closed forms invert each other).
    sigma, K_Ic = 800.0, 18.0
    a_c = fr.critical_flaw_size_um(sigma, K_Ic)
    K_at_ac = fr.murakami_stress_intensity(sigma, a_c)
    assert K_at_ac == pytest.approx(K_Ic, rel=1e-9)


def test_stress_intensity_uses_the_cited_surface_factor():
    # CITED: K = Y·σ·√(π·√area) with Y = 0.65 for a surface defect (Murakami 2002).
    sigma, a_um = 800.0, 200.0
    expected = fr.MURAKAMI_Y_SURFACE * sigma * math.sqrt(math.pi * a_um * 1e-6)
    assert fr.murakami_stress_intensity(sigma, a_um) == pytest.approx(expected)
    # the interior factor is the smaller 0.50 → a lower K for the same flaw/stress
    assert fr.murakami_stress_intensity(sigma, a_um, surface=False) < fr.murakami_stress_intensity(sigma, a_um)


def test_compression_is_never_cracking_at_the_primitive_level():
    # STRUCTURAL (necessary condition): a non-tensile surface carries no opening intensity and an infinite
    # critical flaw — no flaw can crack a surface that is not in tension.
    assert fr.murakami_stress_intensity(-300.0, 1000.0) == 0.0
    assert fr.murakami_stress_intensity(0.0, 1000.0) == 0.0
    assert fr.critical_flaw_size_um(-300.0) == math.inf
    assert fr.critical_flaw_size_um(0.0) == math.inf


def test_critical_flaw_shrinks_with_stress_and_grows_with_toughness():
    # STRUCTURAL: √area_c ∝ (K_Ic/σ)² — a tougher steel tolerates a bigger flaw; a higher stress a smaller one.
    assert fr.critical_flaw_size_um(1000.0) < fr.critical_flaw_size_um(500.0)
    assert fr.critical_flaw_size_um(800.0, K_Ic_MPa=25.0) > fr.critical_flaw_size_um(800.0, K_Ic_MPa=15.0)


# --------------------------------------------------------------------------- #
# The load-bearing design call — same residual field, the cleanliness decides
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_clean_survives_and_dirty_cracks_in_the_same_field():
    # THE HERO / THE LOAD-BEARING CALL: one section, one quench, ONE residual surface tension — the clean
    # heat's flaw is sub-critical (no crack) while the dirty heat's flaw is super-critical (crack). The gate
    # does NOT collapse to residual.crack_risk: both heats see the same tensile surface, cleanliness decides.
    clean = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_CLEAN_UM)
    dirty = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_DIRTY_UM)
    assert clean.surface_stress_MPa == pytest.approx(dirty.surface_stress_MPa)  # identical field
    assert clean.surface_tension and dirty.surface_tension                      # both in tension (risk fires)
    assert not clean.cracks                                                     # clean: sub-critical flaw
    assert dirty.cracks                                                         # dirty: super-critical flaw


@pytest.mark.slow
def test_straddle_has_comfortable_margin_not_knife_edge():
    # DISCRIMINATING (the advisor's margin check): the clean flaw sits well below √area_c and the dirty flaw
    # clearly above — the representative constants make √area_c land BETWEEN them with margin, not on a knife
    # edge (a named scope edge, the reason the coupling discriminates).
    clean = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_CLEAN_UM)
    dirty = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_DIRTY_UM)
    assert clean.margin > 3.0      # clean flaw ≥ 3× below the critical size
    assert dirty.margin < 0.8      # dirty flaw comfortably above it


@pytest.mark.slow
def test_two_tier_clean_is_risk_but_not_realized_crack():
    # THE TWO-TIER IDIOM: the clean heat in a tensile field IS flagged quench-crack-RISK (residual) but NOT
    # the realized quench-crack (fracture) — the new flag is strictly stronger than the risk flag.
    heat = Heat(composition=_4340_COMP)
    risked = quench_crack_check(heat, HT, grade=STEEL)            # residual: surface-tension risk
    realized = fr.fracture_check(heat, HT, fr.SQRT_AREA_CLEAN_UM, grade=STEEL)
    assert risked.has_defect(QUENCH_CRACK_RISK)                  # tension → risk fires
    assert not realized.has_defect(QUENCH_CRACK)                 # clean → no realized crack


@pytest.mark.slow
def test_dirty_heat_raises_the_realized_quench_crack_flag():
    heat = Heat(composition=_4340_COMP)
    out = fr.fracture_check(heat, HT, fr.SQRT_AREA_DIRTY_UM, grade=STEEL)
    assert out.has_defect(QUENCH_CRACK)
    step = out.history[-1]
    assert step.name == "fracture-check" and step.in_spec is False
    assert QUENCH_CRACK in step.flags_added


# --------------------------------------------------------------------------- #
# Monotonicity — the gate moves the right way with section size and cleanliness
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_crack_window_opens_with_section_size():
    # STRUCTURAL: a thicker section → steeper gradient → higher surface tension → SMALLER tolerable flaw.
    thin = fr.quench_crack_fracture(STEEL, 0.02, fr.SQRT_AREA_DIRTY_UM)
    thick = fr.quench_crack_fracture(STEEL, 0.05, fr.SQRT_AREA_DIRTY_UM)
    assert thick.surface_stress_MPa > thin.surface_stress_MPa
    assert thick.critical_flaw_um < thin.critical_flaw_um


@pytest.mark.slow
def test_a_dirtier_heat_is_never_safer_at_fixed_field():
    # STRUCTURAL: at one section, increasing the flaw size only ever moves toward cracking (monotone gate).
    sizes = [fr.SQRT_AREA_CLEAN_UM, 150.0, fr.SQRT_AREA_DIRTY_UM, 600.0]
    Ks = [fr.quench_crack_fracture(STEEL, HT, s).K_applied_MPa for s in sizes]
    assert Ks == sorted(Ks)


# --------------------------------------------------------------------------- #
# The route lever and the thermal-only reference — both clear via the surface stress
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_martemper_saves_the_dirty_part():
    # CONSUMED FROM residual (NOT a tooth): martempering collapses the surface tension, so √area_c → large /
    # ∞ and the SAME dirty heat that cracks on a direct quench clears — the §17/§18 benefit, now in fracture.
    direct = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_DIRTY_UM, route="direct")
    marte = fr.quench_crack_fracture(STEEL, HT, fr.SQRT_AREA_DIRTY_UM, route="martemper")
    assert direct.cracks
    assert not marte.cracks
    assert marte.surface_stress_MPa < direct.surface_stress_MPa
    assert marte.critical_flaw_um > direct.critical_flaw_um


@pytest.mark.slow
def test_thermal_only_surface_compression_never_cracks():
    # CONSUMED FROM residual (NOT a tooth): with the transformation dilatation off the surface ends in
    # COMPRESSION (the §18 sign), so the gate's necessary condition fails — no crack, whatever the flaw.
    out = fr.quench_crack_fracture(STEEL, HT, 5000.0, transform=False)
    assert not out.surface_tension
    assert not out.cracks


# --------------------------------------------------------------------------- #
# The named ceiling — the atlas-steel guard (inherited from the residual engine)
# --------------------------------------------------------------------------- #
def test_non_atlas_steel_is_refused():
    with pytest.raises(ValueError, match="atlas"):
        fr.quench_crack_fracture("1045", HT, fr.SQRT_AREA_DIRTY_UM)
