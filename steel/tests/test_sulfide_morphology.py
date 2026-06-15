"""Tests for sulfide_morphology.py — the signed sulfur foil (MnS as asset and liability).

The worked-product sibling of forging-stage red-shortness (:mod:`steel.hot_work`); where red-short reads the
**free** sulfur, this reads the **tied** MnS, which is itself signed. Honest map (mirrors the module docstring):

  * there is **NO claimable tooth** — the MnS amount is :mod:`steel.slag`'s by-construction stoichiometry, its
    volume fraction is a cited density ratio, and the two verdicts are by-construction ``if`` rules; the checks
    here are by-construction / structural / discriminating;
  * the **machinability index is representative** (MnS contribution only — confounded by hardness/carbon and
    Pb/Ca/Te), so it is tested for *direction and reuse*, never against an absolute rating;
  * the **load-bearing design call** — the anisotropy flag is gated on **morphology**, never on a sulfur
    threshold (slag already flags high sulfur, and it fires on every free-machining grade by design) — is
    pinned by the shape-control lever and the "high-S shape-controlled heat is sound" tests;
  * the transverse-toughness debit is its **own directional axis** (independent of carbon/hardness), pinned by
    a carbon-invariance test — it is not the hardness toughness proxy or the DBTT.

All analytic (closed-form stoichiometry + density ratio) — no solver, fast lane.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from steel import slag
from steel import sulfide_morphology as sm
from steel.heat_state import Heat, heat_treat
from steel.sweep import STEELS, evaluate

# A free-machining 1144-type heat and a plain 1045 — only Mn, S, and the sulfide shape move.
_FREE_MACHINING = replace(STEELS["1045"], C=0.45, Mn=1.40, Si=0.25, P=0.0, S=0.24, name="1144")
_PLAIN = replace(STEELS["1045"], C=0.45, Mn=0.75, Si=0.25, P=0.0, S=0.020, name="1045")


def _heat(comp):
    return Heat(composition=comp)


# --------------------------------------------------------------------------- #
# By construction — the MnS amount/volume reuse slag's stoichiometry + a density ratio
# --------------------------------------------------------------------------- #
def test_volume_fraction_exceeds_weight_fraction_and_is_monotone():
    # BY CONSTRUCTION: the lighter sulfide (ρ ≈ 4.0 vs 7.87) occupies a LARGER volume than weight fraction,
    # and more MnS → more volume. Zero maps to zero.
    assert sm.mns_volume_fraction(0.0) == 0.0
    assert sm.mns_volume_fraction(0.65) > 0.65                  # vol % > wt %
    assert sm.mns_volume_fraction(1.0) > sm.mns_volume_fraction(0.5) > sm.mns_volume_fraction(0.1)


def test_machinability_reuses_the_slag_balance_and_the_volume_law():
    # BY CONSTRUCTION: machinability_index is _machinability_from_volpct of the volume fraction of slag's mns_pct.
    Mn, S = 1.40, 0.24
    f_v = sm.mns_volume_fraction(slag.manganese_sulfide(Mn, S).mns_pct)
    assert sm.machinability_index(Mn, S) == pytest.approx(sm._machinability_from_volpct(f_v))


def test_transverse_ratio_reuses_the_same_volume_and_an_elongation_multiplier():
    # BY CONSTRUCTION: the transverse ratio reads the SAME MnS volume fraction, scaled by the elongation set by
    # the sulfide shape (globular = 0 = isotropic).
    Mn, S = 1.40, 0.24
    f_v = sm.mns_volume_fraction(slag.manganese_sulfide(Mn, S).mns_pct)
    assert sm.transverse_toughness_ratio(Mn, S) == pytest.approx(
        sm._transverse_ratio_from_volpct(f_v, sm.ELONGATED))
    assert sm.transverse_toughness_ratio(Mn, S, shape_controlled=True) == pytest.approx(
        sm._transverse_ratio_from_volpct(f_v, sm.GLOBULAR))


# --------------------------------------------------------------------------- #
# One MnS, two opposite signs — the pedagogical point, by construction (NOT a tooth)
# --------------------------------------------------------------------------- #
def test_more_mns_raises_machinability_and_lowers_transverse_toughness():
    # The same MnS volume read with opposite signs: machinability UP, short-transverse toughness DOWN. One
    # number, two laws — by construction, not a coincidence and not a benchmark.
    lean = sm.sulfide_morphology_assessment(Mn_pct=0.75, S_pct=0.05)
    rich = sm.sulfide_morphology_assessment(Mn_pct=1.40, S_pct=0.24)
    assert rich.mns_volume_fraction > lean.mns_volume_fraction
    assert rich.machinability_index > lean.machinability_index          # good half rises ...
    assert rich.transverse_ratio < lean.transverse_ratio                # ... bad half falls, same volume


def test_transverse_ratio_is_its_own_axis_independent_of_carbon():
    # The transverse debit is the inclusion-stringer axis — NOT the hardness toughness proxy or the DBTT, both
    # of which move strongly with carbon. Two heats differing ONLY in carbon (same Mn/S) work to the SAME
    # short-transverse ratio, because it is a function of the MnS volume, not the matrix hardness. The
    # back-end hardness, by contrast, would differ — that is what makes this a separate, third toughness axis.
    soft = replace(_FREE_MACHINING, C=0.20)
    hard = replace(_FREE_MACHINING, C=0.55)
    a_soft = sm.sulfide_morphology_assessment(soft.Mn, soft.S)
    a_hard = sm.sulfide_morphology_assessment(hard.Mn, hard.S)
    assert a_soft.transverse_ratio == a_hard.transverse_ratio == pytest.approx(
        sm.transverse_toughness_ratio(_FREE_MACHINING.Mn, _FREE_MACHINING.S))
    # the matrix hardness the OTHER toughness axes read DOES move with carbon (so this axis is genuinely distinct)
    assert evaluate(hard, medium="oil", diameter=0.015).HV > evaluate(soft, medium="oil", diameter=0.015).HV


# --------------------------------------------------------------------------- #
# The shape-control lever — the discrimination, the build's reason to exist
# --------------------------------------------------------------------------- #
def test_shape_control_clears_the_anisotropy_at_the_same_sulfur():
    # The SAME heat: as-rolled the elongated MnS is anisotropic; globularized (Ca/RE/Te) it is not. Only the
    # shape changed — the lever is the shape, not the sulfur (the load-bearing distinction from red-short).
    as_rolled = sm.sulfide_morphology_assessment(1.40, 0.24, shape_controlled=False)
    globular = sm.sulfide_morphology_assessment(1.40, 0.24, shape_controlled=True)
    assert as_rolled.anisotropic and not globular.anisotropic
    assert as_rolled.free_machining and globular.free_machining          # both keep the benefit
    assert globular.transverse_ratio == pytest.approx(1.0)               # globular MnS is isotropic


def test_anisotropy_is_gated_on_morphology_not_a_sulfur_threshold():
    # THE LOAD-BEARING DESIGN CALL: a high-sulfur heat (over slag's flat 0.040 % line) shape-controlled is NOT
    # anisotropic — so the gate is morphology, never the sulfur level. If this fails, the flag has collapsed
    # into red-short and would brand every free-machining steel defective for being itself.
    assert _FREE_MACHINING.S > slag.MAX_SULFUR_PCT                       # slag raises high-sulfur ...
    sound = sm.sulfide_morphology_assessment(_FREE_MACHINING.Mn, _FREE_MACHINING.S, shape_controlled=True)
    assert not sound.anisotropic                                        # ... yet shape control makes it sound


# --------------------------------------------------------------------------- #
# Free-machining needs the MnS — the other end of the trade
# --------------------------------------------------------------------------- #
def test_resulfurized_heat_is_free_machining_plain_heat_is_not():
    rich = sm.sulfide_morphology_assessment(_FREE_MACHINING.Mn, _FREE_MACHINING.S)
    plain = sm.sulfide_morphology_assessment(_PLAIN.Mn, _PLAIN.S)
    assert rich.free_machining and rich.mns_volume_fraction >= sm.FREE_MACHINING_MIN_VOLPCT
    assert not plain.free_machining and plain.mns_volume_fraction < sm.FREE_MACHINING_MIN_VOLPCT
    assert plain.transverse_ratio > rich.transverse_ratio               # the plain heat keeps its toughness


def test_sulfur_free_heat_has_no_mns_no_benefit_no_debit():
    a = sm.sulfide_morphology_assessment(Mn_pct=1.00, S_pct=0.0)
    assert a.mns_volume_fraction == 0.0 and not a.free_machining
    assert a.transverse_ratio == pytest.approx(1.0) and not a.anisotropic


# --------------------------------------------------------------------------- #
# The two-tier disagreement — the flat high-sulfur risk both over- and under-warns
# --------------------------------------------------------------------------- #
def test_high_sulfur_risk_over_warns_when_shape_controlled():
    # slag's flat line flags the free-machining heat (S over spec), but shape control keeps it sound — the
    # consequence corrects the flat line's over-warning (the same shape as gas-porosity / hot-tear).
    assert _FREE_MACHINING.S > slag.MAX_SULFUR_PCT
    out = sm.sulfide_morphology_check(_heat(_FREE_MACHINING), shape_controlled=True)
    assert not out.has_defect(sm.SULFIDE_ANISOTROPY)


# --------------------------------------------------------------------------- #
# Inert in the hardenability back end — the split (morphology reads state, the quench ignores it)
# --------------------------------------------------------------------------- #
def test_sulfide_anisotropy_is_inert_in_the_hardenability_back_end():
    # The anisotropy verdict reads state and raises a flag, but moves NO composition and is invisible to the
    # quench: an anisotropic heat heat-treats byte-identically to the same composition untouched. If this ever
    # fails, the hardenability chain started reading the morphology, where it must stay inert.
    h = _heat(_FREE_MACHINING)
    worked = sm.sulfide_morphology_check(h)                              # raises sulfide-anisotropy
    assert worked.has_defect(sm.SULFIDE_ANISOTROPY)
    assert worked.composition == h.composition                          # morphology moves no composition
    base = evaluate(h.as_steel(), medium="oil", diameter=0.015)
    after = evaluate(worked.as_steel(), medium="oil", diameter=0.015)
    assert base.HV == after.HV and base.result.martensite == after.result.martensite
    # and through the spine's own seam: the quench step is identical whether or not the flag is present
    assert heat_treat(worked, medium="oil", diameter=0.015).history[-1].summary == \
        heat_treat(h, medium="oil", diameter=0.015).history[-1].summary


# --------------------------------------------------------------------------- #
# The orchestrator seam + the two-tier flag
# --------------------------------------------------------------------------- #
def test_check_raises_anisotropy_flag_and_records_a_step():
    out = sm.sulfide_morphology_check(_heat(_FREE_MACHINING))            # as-rolled → anisotropic
    assert out.has_defect(sm.SULFIDE_ANISOTROPY)
    assert out.history[-1].name == "sulfide-morphology" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (sm.SULFIDE_ANISOTROPY,)


def test_check_sound_heat_stays_clean():
    out = sm.sulfide_morphology_check(_heat(_PLAIN))                     # too little MnS to stringer
    assert not out.has_defect(sm.SULFIDE_ANISOTROPY)
    assert out.is_clean and out.history[-1].in_spec is True


def test_check_does_not_change_composition():
    h = _heat(_FREE_MACHINING)
    assert sm.sulfide_morphology_check(h).composition == h.composition


def test_check_flag_is_idempotent():
    once = sm.sulfide_morphology_check(_heat(_FREE_MACHINING))
    twice = sm.sulfide_morphology_check(once)
    assert twice.defects.count(sm.SULFIDE_ANISOTROPY) == 1
    assert twice.history[-1].flags_added == ()


# --------------------------------------------------------------------------- #
# The verdict string names both halves
# --------------------------------------------------------------------------- #
def test_verdict_names_free_machining_and_the_morphology():
    rolled = sm.sulfide_morphology_assessment(_FREE_MACHINING.Mn, _FREE_MACHINING.S).verdict
    globular = sm.sulfide_morphology_assessment(_FREE_MACHINING.Mn, _FREE_MACHINING.S,
                                                shape_controlled=True).verdict
    plain = sm.sulfide_morphology_assessment(_PLAIN.Mn, _PLAIN.S).verdict
    assert "free-machining" in rolled and "ANISOTROPIC" in rolled
    assert "free-machining" in globular and "isotropic" in globular
    assert "not free-machining" in plain
