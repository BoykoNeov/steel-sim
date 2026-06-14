"""Tests for peritectic.py — the carbon-driven casting-cracking consequence (δ→γ contraction).

The carbon sibling of the sulfur-driven :mod:`steel.hot_tear`. Honest map (mirrors the module docstring):

  * there is **NO claimable tooth** — the verdict *is* Wolf's cited ferrite-potential band on a
    (representative) carbon equivalent, and the mechanism *is* the Fe–C peritectic lever rule (carbon mass
    balance), so neither can independently "fail"; the checks here are by-construction / structural;
  * the build's reason to exist is the **non-monotonic carbon hero** — a peritectic-carbon heat cracks while
    BOTH a leaner and a richer heat are sound ("more carbon is safer") — a real discrimination, not the
    FP-band rule asserted back to itself;
  * the **nominal-not-Scheil** contract is load-bearing (the *reverse* of hot-tear): the shell phenomenon
    reads bulk aim carbon, never the segregated last liquid;
  * the one soft note is a **coherence** (carefully NOT independent — both rest on the Fe–C peritectic): the
    lever rule's hypo-peritectic window and Wolf's empirical FP band sit at the same ~0.1 %C; the consumed-δ
    peak is honestly at the band EDGE (Cγ), not the empirical worst (the named kinetics/shell-mechanics
    ceiling).

All analytic (Wolf FP + closed-form lever rule) — no solver, fast lane.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from steel import peritectic as pk
from steel.heat_state import Heat
from steel.sweep import Steel, STEELS

_BACKBONE = replace(STEELS["1045"], C=0.11, Mn=0.0, Si=0.0, Cr=0.0, Mo=0.0, Ni=0.0, P=0.0, S=0.0,
                    name="cast structural")


def _heat(C, **alloy):
    return Heat(composition=replace(_BACKBONE, C=C, **alloy))


# --------------------------------------------------------------------------- #
# By construction — Wolf's FP, the carbon equivalent, and the lever rule
# --------------------------------------------------------------------------- #
def test_ferrite_potential_is_wolfs_formula():
    # BY CONSTRUCTION: FP = 2.5(0.5 − Cp); maximal peritectic at Cp = 0.10 (FP = 1).
    assert pk.ferrite_potential(0.10) == pytest.approx(pk.FP_PERITECTIC_MAX)
    assert pk.ferrite_potential(0.50) == pytest.approx(0.0)
    assert pk.ferrite_potential(0.0) == pytest.approx(pk.FP_SLOPE * pk.FP_REFERENCE_C)


def test_carbon_equivalent_is_carbon_for_plain_carbon():
    # Plain-carbon: Cp == %C (the hero needs no coefficients).
    assert pk.carbon_equivalent(Steel(C=0.13, name="x")) == pytest.approx(0.13)


def test_carbon_equivalent_signs_austenite_raises_ferrite_lowers():
    # The SIGNS are unambiguous: austenite stabilizers (Mn, Ni) raise Cp; ferrite stabilizers (Si, Cr, Mo, P)
    # lower it. (Magnitudes are representative — the named ceiling — but the directions are physics.)
    base = pk.carbon_equivalent(Steel(C=0.13, name="x"))
    assert pk.carbon_equivalent(Steel(C=0.13, Mn=1.0, name="x")) > base   # austenite stabilizer ↑
    assert pk.carbon_equivalent(Steel(C=0.13, Ni=1.0, name="x")) > base
    assert pk.carbon_equivalent(Steel(C=0.13, Si=1.0, name="x")) < base   # ferrite stabilizer ↓
    assert pk.carbon_equivalent(Steel(C=0.13, Cr=1.0, name="x")) < base


def test_lever_rule_endpoints_by_construction():
    # δ at the front: 1 below C_δ (fully δ), 0 above C_L (fully γ), the lever between.
    assert pk.delta_fraction_above_peritectic(0.05) == 1.0
    assert pk.delta_fraction_above_peritectic(0.60) == 0.0
    assert pk.delta_fraction_above_peritectic(pk.C_GAMMA_PERITECTIC) == pytest.approx(
        (pk.C_LIQUID_PERITECTIC - pk.C_GAMMA_PERITECTIC) / (pk.C_LIQUID_PERITECTIC - pk.C_DELTA_PERITECTIC))


def test_delta_consumed_is_zero_outside_the_peritectic_reaction_range():
    # No peritectic reaction below C_δ (solidifies fully δ, transforms slowly in the solid state) or above
    # C_L (solidifies fully γ) — so no rapid high-T contraction there.
    assert pk.delta_consumed_by_peritectic(0.05) == 0.0
    assert pk.delta_consumed_by_peritectic(0.60) == 0.0
    assert pk.delta_consumed_by_peritectic(0.13) > 0.0


# --------------------------------------------------------------------------- #
# The named ceiling — the consumed-δ peaks at the band EDGE, not the empirical worst
# --------------------------------------------------------------------------- #
def test_consumed_delta_peaks_at_the_gamma_invariant_not_the_empirical_worst():
    # HONEST CEILING: the equilibrium lever's contraction source peaks at C = Cγ = 0.17 (the upper band
    # edge), whereas the empirically worst grade is nearer ~0.11 — NOT patched with a manufactured weighting.
    grid = [i / 1000 for i in range(90, 531)]
    peak_C = max(grid, key=pk.delta_consumed_by_peritectic)
    assert peak_C == pytest.approx(pk.C_GAMMA_PERITECTIC, abs=0.002)
    # and the empirical worst (~0.11) sits BELOW that peak — the offset the ceiling names
    assert pk.delta_consumed_by_peritectic(0.11) < pk.delta_consumed_by_peritectic(pk.C_GAMMA_PERITECTIC)


# --------------------------------------------------------------------------- #
# The soft coherence note (NOT a tooth) — lever window ≈ Wolf's empirical FP band, ~0.1 %C
# --------------------------------------------------------------------------- #
def test_fp_band_and_lever_window_coincide_near_one_tenth_percent():
    # The crack band carbon edges (plain carbon) and the hypo-peritectic lever range both sit at ~0.1 %C —
    # the coherence (the mechanism explains WHY the empirical band is there; NOT two independent agreements).
    c_low = pk.FP_REFERENCE_C - pk.FP_CRACK_HIGH / pk.FP_SLOPE     # FP = 1.05 edge
    c_high = pk.FP_REFERENCE_C - pk.FP_CRACK_LOW / pk.FP_SLOPE     # FP = 0.80 edge
    assert c_low == pytest.approx(0.08, abs=0.01)
    assert c_high == pytest.approx(0.18, abs=0.01)
    # the hypo-peritectic lever range (Cδ..Cγ) lies inside the FP band's span
    assert c_low < pk.C_DELTA_PERITECTIC and pk.C_GAMMA_PERITECTIC < c_high


def test_band_edge_strip_is_fp_flagged_but_pre_peritectic_not_self_contradictory():
    # COHERENT, NOT IDENTICAL: the FP band's low edge (Cp = 0.08) reaches below the δ-onset (Cδ = 0.09), so a
    # 0.085 %C heat is FP-flagged yet its lever-rule peritectic reaction has not started. The verdict must
    # NOT assert the δ→γ contraction there (it would self-contradict "sub-peritectic + contraction").
    a = pk.peritectic_assessment(Steel(C=0.085, name="x"))
    assert a.crack_susceptible                                     # FP band catches it ...
    assert a.regime == "sub-peritectic" and a.delta_consumed == 0.0   # ... but the reaction has not started
    assert "incipient" in a.verdict and "strains the thin shell" not in a.verdict


# --------------------------------------------------------------------------- #
# The verdict — Wolf's crack band on the carbon equivalent
# --------------------------------------------------------------------------- #
def test_crack_band_membership():
    assert pk.is_crack_susceptible(1.0)                            # FP = 1 (max peritectic) → in band
    assert not pk.is_crack_susceptible(1.10)                       # above → ferritic sticker
    assert not pk.is_crack_susceptible(0.70)                       # below → austenitic


# --------------------------------------------------------------------------- #
# The hero — carbon decides, NON-MONOTONICALLY (the build's reason to exist)
# --------------------------------------------------------------------------- #
def test_peritectic_carbon_cracks_while_leaner_and_richer_are_sound():
    # The discrimination: a 0.11 %C heat cracks though BOTH a leaner (0.05) and a richer (0.45) heat are
    # sound — non-monotonic, "more carbon is safer". This is the real discrimination, not the if-rule.
    lean = pk.peritectic_assessment(replace(_BACKBONE, C=0.05))
    peri = pk.peritectic_assessment(replace(_BACKBONE, C=0.11))
    rich = pk.peritectic_assessment(replace(_BACKBONE, C=0.45))
    assert not lean.crack_susceptible
    assert peri.crack_susceptible
    assert not rich.crack_susceptible
    # the lean heat is OUT on the ferritic side, the rich heat OUT on the austenitic side (different reasons)
    assert lean.fp >= pk.FP_CRACK_HIGH and rich.fp <= pk.FP_CRACK_LOW


def test_regimes_track_the_invariant_points():
    assert pk.peritectic_regime(0.05) == "sub-peritectic"
    assert pk.peritectic_regime(0.11) == "hypo-peritectic"
    assert pk.peritectic_regime(0.30) == "hyper-peritectic"
    assert pk.peritectic_regime(0.60) == "super-peritectic"


# --------------------------------------------------------------------------- #
# The alloying lever — same carbon, the stabilizers decide
# --------------------------------------------------------------------------- #
def test_ferrite_stabilizers_pull_a_safe_carbon_into_the_band():
    # Same 0.20 %C: plain is austenitic (sound); Si+Cr pull the carbon EQUIVALENT into the band (crack).
    plain = pk.peritectic_assessment(replace(_BACKBONE, C=0.20))
    alloyed = pk.peritectic_assessment(replace(_BACKBONE, C=0.20, Si=0.50, Cr=1.00))
    assert not plain.crack_susceptible
    assert alloyed.crack_susceptible
    assert alloyed.Cp < plain.Cp                                   # ferrite stabilizers lowered Cp
    assert alloyed.C == plain.C                                    # ... at identical carbon


# --------------------------------------------------------------------------- #
# The nominal-not-Scheil contract (load-bearing — the reverse of hot-tear)
# --------------------------------------------------------------------------- #
def test_assessment_reads_nominal_carbon_not_an_enriched_value():
    # The shell phenomenon reads the BULK aim carbon — the assessment's carbon is exactly the composition's,
    # never a Scheil-enriched (higher) last-liquid value (which would push a sound grade into the band).
    comp = replace(_BACKBONE, C=0.45)
    a = pk.peritectic_assessment(comp)
    assert a.C == comp.C                                           # not enriched
    assert not a.crack_susceptible                                 # a rich heat stays sound (no enrichment)


# --------------------------------------------------------------------------- #
# The orchestrator seam + the flag
# --------------------------------------------------------------------------- #
def test_peritectic_crack_check_raises_flag_and_records_a_step():
    out = pk.peritectic_crack_check(_heat(C=0.11))
    assert out.has_defect(pk.PERITECTIC_CRACK)
    assert out.history[-1].name == "peritectic-crack-check" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (pk.PERITECTIC_CRACK,)


def test_peritectic_crack_check_sound_heat_stays_clean():
    out = pk.peritectic_crack_check(_heat(C=0.45))
    assert not out.has_defect(pk.PERITECTIC_CRACK)
    assert out.is_clean and out.history[-1].in_spec is True


def test_peritectic_crack_check_does_not_change_composition():
    h = _heat(C=0.11)
    out = pk.peritectic_crack_check(h)
    assert out.composition == h.composition                       # the verdict reads state


def test_peritectic_crack_check_flag_is_idempotent():
    once = pk.peritectic_crack_check(_heat(C=0.11))
    twice = pk.peritectic_crack_check(once)
    assert twice.defects.count(pk.PERITECTIC_CRACK) == 1
    assert twice.history[-1].flags_added == ()


def test_verdict_string_names_the_band_and_mechanism():
    crack = pk.peritectic_assessment(replace(_BACKBONE, C=0.11)).verdict
    sound = pk.peritectic_assessment(replace(_BACKBONE, C=0.45)).verdict
    assert "PERITECTIC-CRACK" in crack and "depression band" in crack
    assert "sound surface" in sound
