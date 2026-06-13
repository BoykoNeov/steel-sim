"""Tests for F2 slag-partition refining (Slice 2): dephosphorization, desulfurization + the seam.

The non-circularity split (as in ``test_refining.py`` / ``test_casting.py`` / ``test_reduction.py``):

* **Teeth (could-have-missed):** the **opposite oxygen dependence** of P and S — dephosphorization's L_P
  *rises* with the slag's oxidizing power while desulfurization's L_S *falls* with dissolved oxygen, two
  signs from two **independently sourced** correlations (Healy 1970 vs the sulfide-capacity partition), so
  their being opposite is computed not tuned; the acid/basic endpoint (an acid slag leaves L_P ≈ O(1) — why
  Bessemer couldn't dephosphorize); the order of magnitude vs measured plant L (BOF L_P 50–200, ladle L_S
  10²–10³); dephosphorization favoured *cool*; and — the structural tooth of this slice — **P/S are inert in
  the validated back end** (changing them does not move the heat-treat outcome: the honesty posture, pinned).
* **By construction (NOT teeth):** the metal↔slag mass-balance partition (``[%X] = [%X]₀/(1+L·R)`` is the
  balance solved, so it conserves), the Mn:S → MnS stoichiometry (conservation-clean by definition, §14
  theme B), and the Fe–FeO oxygen link (a cited anchor evaluated). They guard transcription.

The seam tests pin that the orchestrator lowers the right composition field, reads the Heat's oxygen for the
desulfurization coupling, and raises the right flags; the end-to-end route is exercised in ``test_demo_slag``.
"""
import math
from dataclasses import replace

import pytest

from steel import slag as sg
from steel import refining as rf
from steel.slag import (
    Slag, ACID_BESSEMER_SLAG, BASIC_CONVERTER_SLAG, LADLE_DESULF_SLAG,
    phosphorus_partition, sulfide_capacity, sulfur_partition, metal_oxygen_for_feo,
    partition_remaining, manganese_sulfide, MN_PER_S,
    dephosphorize, desulfurize, HIGH_PHOSPHORUS, HIGH_SULFUR,
    MAX_PHOSPHORUS_PCT, MAX_SULFUR_PCT,
)
from steel.heat_state import Heat
from steel.sweep import Steel, STEELS, evaluate


# --------------------------------------------------------------------------- #
# Teeth — the opposite oxygen dependence (the headline, cross-source)
# --------------------------------------------------------------------------- #
def test_opposite_oxygen_dependence_is_the_headline():
    # Dephosphorization is an oxidation → L_P RISES as the slag gets more oxidizing (more FeO). Computed at
    # fixed basicity (vary only FeO), from Healy's +2.5·log %Fe_t.
    base = BASIC_CONVERTER_SLAG
    Lp_low_O = phosphorus_partition(replace(base, FeO=5.0))
    Lp_high_O = phosphorus_partition(replace(base, FeO=35.0))
    assert Lp_high_O > Lp_low_O                                  # oxidizing favours P removal

    # Desulfurization is a reduction → L_S FALLS as the metal oxygen rises (the −log a_O term), same slag.
    Ls_low_O = sulfur_partition(LADLE_DESULF_SLAG, 3.0)
    Ls_high_O = sulfur_partition(LADLE_DESULF_SLAG, 80.0)
    assert Ls_high_O < Ls_low_O                                 # reducing favours S removal

    # The teeth: the two oxygen dependences have OPPOSITE sign — independently sourced (Healy for P, the
    # sulfide-capacity conversion for S), so this is not a tuned contrast.
    dLp = math.log10(Lp_high_O) - math.log10(Lp_low_O)          # > 0
    dLs = math.log10(Ls_high_O) - math.log10(Ls_low_O)          # < 0
    assert dLp > 0.0 > dLs


def test_acid_slag_cannot_dephosphorize_basic_can():
    # The Bessemer/Thomas endpoint: an acid (lime-poor) slag leaves L_P of order 1 even though oxidizing —
    # phosphorus stays in the steel; a basic slag pulls it into the hundreds. The qualitative jump, not a
    # coefficient (it is the 0.08·%CaO term sweeping the lime range).
    Lp_acid = phosphorus_partition(ACID_BESSEMER_SLAG)
    Lp_basic = phosphorus_partition(BASIC_CONVERTER_SLAG)
    assert Lp_acid < 5.0                                        # ≈ O(1): can't dephosphorize
    assert Lp_basic > 100.0                                     # hundreds: the Thomas advantage
    assert Lp_basic / Lp_acid > 50.0                            # the orders-of-magnitude basicity swing


def test_phosphorus_partition_in_order_of_magnitude_of_measured_bof():
    # Benchmark, order-of-magnitude only (Healy is the source-sensitive tier and over-predicts at high lime):
    # the basic-converter L_P must land within a factor of several of the measured BOF range 50–200.
    Lp = phosphorus_partition(BASIC_CONVERTER_SLAG)
    assert 50.0 < Lp < 1000.0                                   # measured 50–200; Healy runs ~2–4× high, named


def test_sulfur_partition_brackets_the_measured_ladle_range():
    # Deoxidized ladle conditions (a few ppm O) → L_S in the 10²–10³ band good ladle slags reach; the same
    # slag at the un-killed blow oxygen (tens of ppm) collapses toward O(1–10) — the deox-first lesson.
    Ls_ladle = sulfur_partition(LADLE_DESULF_SLAG, 4.0)
    Ls_converter = sulfur_partition(LADLE_DESULF_SLAG, 80.0)
    assert 50.0 < Ls_ladle < 2000.0
    assert Ls_converter < 20.0
    assert Ls_ladle / Ls_converter > 10.0                       # the oxygen leverage


def test_dephosphorization_favoured_cool():
    # The 22350/T term: lower temperature → higher L_P (dephosphorization is exothermic-favoured). Right
    # direction, un-tuned.
    assert phosphorus_partition(BASIC_CONVERTER_SLAG, 1550.0) > phosphorus_partition(BASIC_CONVERTER_SLAG, 1700.0)


def test_sulfide_capacity_and_partition_reject_bad_inputs():
    # a_O undefined as [%O] → 0.
    with pytest.raises(ValueError):
        sulfur_partition(LADLE_DESULF_SLAG, 0.0)


# --------------------------------------------------------------------------- #
# Teeth — the honesty posture: P/S are inert in the validated back end
# --------------------------------------------------------------------------- #
def test_phosphorus_sulfur_inert_in_back_end():
    # The structural tooth that fixes this slice's posture: P and S thread the composition but NO validated
    # model reads them (minor() is C/Si/Mn/Ni/Cr/Mo). So a wildly off-spec-P/S heat heat-treats IDENTICALLY
    # to a clean one — the benchmarked chemistry sets state, its consequence is deferred. If this ever fails,
    # something started consuming P/S and the "consequence deferred" framing is no longer honest.
    clean = STEELS["4140"]
    dirty = replace(clean, P=0.5, S=0.3)
    assert clean.minor() == dirty.minor()                       # P/S excluded from the back-end dict
    out_clean = evaluate(clean, medium="oil", diameter=0.015)
    out_dirty = evaluate(dirty, medium="oil", diameter=0.015)
    assert out_clean.HV == out_dirty.HV
    assert out_clean.result.martensite == out_dirty.result.martensite


# --------------------------------------------------------------------------- #
# By construction (NOT teeth) — the mass balances and the Fe–FeO link
# --------------------------------------------------------------------------- #
def test_partition_conserves_mass_between_metal_and_slag():
    # By construction: [%X] = [%X]₀/(1+L·R) is the balance solved, so metal + slag = initial exactly.
    X0, L, R = 0.085, 200.0, 0.05
    metal = partition_remaining(X0, L, R)
    slag_content = L * metal                                    # (%X)_slag = L·[%X]_metal
    # mass balance: [%X]₀·m_metal = [%X]·m_metal + (%X)_slag·m_slag, with m_slag/m_metal = R
    assert metal + slag_content * R == pytest.approx(X0, rel=1e-12)


def test_partition_remaining_monotone_in_L_and_ratio():
    # More partition or more slag ⇒ less left in the metal (a sanity guard on the balance, by construction).
    assert partition_remaining(0.1, 400.0, 0.1) < partition_remaining(0.1, 50.0, 0.1)
    assert partition_remaining(0.1, 200.0, 0.2) < partition_remaining(0.1, 200.0, 0.05)


def test_manganese_sulfide_stoichiometry_conserves():
    # §14 theme B, by construction: with Mn:S ≥ 1.71 all sulfur ties as MnS, none free; Mn consumed =
    # bound_S × 1.71 and MnS = bound_S × (M_MnS/M_S). Mushet's fix as arithmetic.
    b = manganese_sulfide(Mn_pct=0.90, S_pct=0.030)
    assert b.forms_mns and b.free_sulfur_pct == 0.0
    assert b.mns_pct == pytest.approx(0.030 * (sg.M_MNS / sg.M_S), rel=1e-12)

    # A manganese-short, sulfur-rich foil (Mn:S < 1.71): leftover free sulfur (the FeS / red-short risk).
    bad = manganese_sulfide(Mn_pct=0.30, S_pct=0.30)
    assert not bad.forms_mns and bad.free_sulfur_pct > 0.0
    bound_S = 0.30 / MN_PER_S
    assert bad.free_sulfur_pct == pytest.approx(0.30 - bound_S, rel=1e-12)


def test_fe_feo_link_rises_with_feo():
    # The cited Fe–FeO anchor, evaluated (by construction): more slag FeO ⇒ more equilibrium metal oxygen.
    low = metal_oxygen_for_feo(replace(BASIC_CONVERTER_SLAG, FeO=2.0))
    high = metal_oxygen_for_feo(replace(BASIC_CONVERTER_SLAG, FeO=40.0))
    assert high > low > 0.0
    # The reducing ladle slag sits far below the oxidizing converter slag (consistent with Slice 1's numbers).
    assert metal_oxygen_for_feo(LADLE_DESULF_SLAG) < metal_oxygen_for_feo(BASIC_CONVERTER_SLAG)


def test_basicity_and_optical_basicity():
    # Plain readouts (by construction): binary basicity and the acid/basic ordering of optical basicity.
    assert BASIC_CONVERTER_SLAG.basicity > 1.0 > ACID_BESSEMER_SLAG.basicity
    assert LADLE_DESULF_SLAG.optical_basicity > ACID_BESSEMER_SLAG.optical_basicity


# --------------------------------------------------------------------------- #
# The seam — dephosphorize / desulfurize fill the right field and flag the right defect
# --------------------------------------------------------------------------- #
def _impure_charge(P=0.10, S=0.06):
    backbone = replace(STEELS["4140"], P=P, S=S)
    return rf.from_hot_metal(backbone)


def test_dephosphorize_lowers_P_and_flags_acid():
    charge = _impure_charge()
    basic = dephosphorize(charge, BASIC_CONVERTER_SLAG)
    acid = dephosphorize(charge, ACID_BESSEMER_SLAG)

    assert basic.composition.P < charge.composition.P          # phosphorus removed
    assert basic.composition.P < MAX_PHOSPHORUS_PCT and not basic.has_defect(HIGH_PHOSPHORUS)
    assert acid.composition.P > MAX_PHOSPHORUS_PCT and acid.has_defect(HIGH_PHOSPHORUS)
    # Immutable: the charge is untouched, a fresh Heat with one more trail entry is returned.
    assert charge.composition.P == 0.10
    assert basic.history[-1].name == "dephosphorize"
    # Sulfur is not touched by the converter dephos step.
    assert basic.composition.S == charge.composition.S


def test_desulfurize_reads_oxygen_coupling():
    # The coupling tooth at the seam: the SAME ladle slag on a deoxidized heat vs an un-killed (high-O) one.
    charge = _impure_charge()
    killed = Heat(composition=charge.composition, oxygen_ppm=4.0)        # post-kill: a few ppm O
    unkilled = Heat(composition=charge.composition, oxygen_ppm=80.0)     # raw blow: tens of ppm O

    good = desulfurize(killed, LADLE_DESULF_SLAG)
    poor = desulfurize(unkilled, LADLE_DESULF_SLAG)
    assert good.composition.S < poor.composition.S                      # low oxygen desulfurizes far better
    assert good.composition.S < MAX_SULFUR_PCT and not good.has_defect(HIGH_SULFUR)
    assert poor.has_defect(HIGH_SULFUR)
    assert good.history[-1].name == "desulfurize"


def test_desulfurize_without_recorded_oxygen_uses_undeoxidized_oxygen():
    # oxygen_ppm None (no kill recorded) ⇒ fall back to the C–O-equilibrium oxygen at the heat's carbon (high),
    # so an out-of-order desulf honestly under-performs rather than silently assuming a clean bath.
    raw = Heat(composition=replace(STEELS["4140"], C=0.05, S=0.06))     # low-carbon ⇒ high C–O oxygen
    out = desulfurize(raw, LADLE_DESULF_SLAG)
    # The implied oxygen is the undeoxidized C–O number — large — so very little sulfur comes out.
    assert out.composition.S > 0.04


def test_seam_preserves_other_composition_fields():
    charge = _impure_charge()
    out = desulfurize(dephosphorize(charge, BASIC_CONVERTER_SLAG), LADLE_DESULF_SLAG)
    # Only P and S move; the alloy backbone and carbon round-trip unchanged through the partition seam.
    for field in ("C", "Mn", "Si", "Ni", "Cr", "Mo"):
        assert getattr(out.composition, field) == getattr(charge.composition, field)
