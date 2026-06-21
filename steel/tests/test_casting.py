"""Tests for F4 casting/solidification (Slice 1): Scheil microsegregation + Chvorinov + the handoff.

The non-circularity split (as in ``test_reduction.py`` / ``test_grain.py``):

* **Teeth (could-have-missed):** the **conservation** mass balance (solute in solid + liquid returns C₀,
  two independently-written closed forms reconciling — *not* the tautological "the formula integrates to its
  own value"); the **severity ordering** (smallest cited ``k`` segregates the last liquid most: S, C, P the
  dangerous ones, Cr/Ni mild — falls out of the un-tuned Won-Thomas/ISIJ ``k``); and the cited-``k`` sanity
  bound (every ``0 < k ≤ 1``, the di-crosscheck typo guard on the pinned table).
* **By construction (NOT teeth):** ``C_s(f_s=0) = k·C₀`` and ``C_L(f_s=0) = C₀`` (the closed form at the
  start), ``t ∝ M²`` exactly (the Chvorinov definition). They guard transcription, they cannot fail
  informatively.

The cast→back-end **handoff** (the front-to-back proof) is exercised end to end in ``test_demo_casting.py``;
here we pin the casting physics and that ``cast_billet`` emits two real, correctly-enriched Heats.
"""
import pytest

from steel import casting as cast
from steel.casting import (
    SOLUTES, scheil_solid_composition, scheil_liquid_composition, segregation_ratio,
    solute_in_solid, solute_in_liquid, scheil_mass_balance, liquidus_temperature,
    casting_modulus, chvorinov_time, centerline_enriched_composition, cast_billet,
    cast_billet_onto, partition_coefficient, T_PURE_FE, PERITECTIC_C, FS_CENTERLINE,
)
from steel.heat_state import Heat, ProcessStep
from steel.sweep import Steel, STEELS


# --------------------------------------------------------------------------- #
# Cited data — the di-crosscheck typo guard on the partition-coefficient table
# --------------------------------------------------------------------------- #
def test_partition_coefficients_are_physical():
    # Every k is a fraction in (0, 1]: a solute either partitions evenly (k→1) or segregates (k<1); a
    # value outside this is a transcription error in the pinned Won-Thomas / ISIJ table.
    for el, s in SOLUTES.items():
        for k in (s.k_delta, s.k_gamma):
            assert 0.0 < k <= 1.0, f"{el}: k={k} outside (0, 1]"


def test_demonstrator_grades_solidify_primary_delta():
    # The δ-phase k's are the correct primary set only below the peritectic carbon — verify the grades
    # the demo leans on sit there (so phase="delta" is honest, not a convenient default).
    for g in ("4140", "8620"):
        assert STEELS[g].C < PERITECTIC_C


# --------------------------------------------------------------------------- #
# Scheil closed form (by construction) + the severity ordering (teeth)
# --------------------------------------------------------------------------- #
def test_scheil_start_of_freeze_is_by_construction():
    k, C0 = 0.30, 1.0
    assert scheil_solid_composition(C0, k, 0.0) == pytest.approx(k * C0)   # first solid = k·C₀
    assert scheil_liquid_composition(C0, k, 0.0) == pytest.approx(C0)       # liquid starts at nominal


def test_segregation_severity_ordering_matches_cited_k():
    # The teeth: at a fixed solid fraction the interdendritic LIQUID enriches most for the smallest k.
    # Ordering by liquid enrichment (descending) must equal ordering by k (ascending) — and put S, C, P
    # (the dangerous segregators) at the top, Cr/Ni at the bottom, straight from the un-tuned data.
    fs = 0.9
    by_enrichment = sorted(SOLUTES, key=lambda e: scheil_liquid_composition(1.0, SOLUTES[e].k_delta, fs),
                           reverse=True)
    by_k = sorted(SOLUTES, key=lambda e: SOLUTES[e].k_delta)
    assert by_enrichment == by_k
    assert set(by_enrichment[:3]) == {"S", "C", "P"}
    assert set(by_enrichment[-2:]) == {"Cr", "Ni"}


def test_segregation_grows_with_solid_fraction():
    # A k<1 solute's residual liquid only gets richer as freezing proceeds (more reaches f_s, steeper).
    k = SOLUTES["Mn"].k_delta
    enr = [scheil_liquid_composition(1.0, k, f) for f in (0.2, 0.5, 0.8, 0.95)]
    assert enr == sorted(enr) and enr[0] > 1.0


# --------------------------------------------------------------------------- #
# Conservation — the real tooth (mass balance, not a tautology)
# --------------------------------------------------------------------------- #
def test_mass_balance_returns_C0_for_every_solute():
    # Solute frozen into the solid (numeric ∫C_s) + solute left in the liquid (analytic lever) = C₀, at
    # every moderate solid fraction, for every solute — including the tiny-k impurities. Two independently
    # written formulas reconciling: a genuine conservation check.
    C0 = 0.5
    for s in SOLUTES.values():
        for fs in (0.3, 0.5, 0.7, 0.9):
            assert scheil_mass_balance(C0, s.k_delta, fs) == pytest.approx(C0, abs=1e-3)


def test_numeric_solid_integral_matches_its_closed_form():
    # The numeric ∫₀^{fs} C_s df' equals the analytic cumulative C₀·(1−(1−fs)^k) — confirms the quadrature
    # and the closed form agree (the solid side of the balance is trustworthy).
    C0 = 1.0
    for el in ("S", "C", "Mn", "Cr"):
        k = SOLUTES[el].k_delta
        for fs in (0.4, 0.8):
            assert solute_in_solid(C0, k, fs) == pytest.approx(C0 * (1.0 - (1.0 - fs) ** k), abs=2e-4)


def test_solute_in_liquid_is_the_lever():
    C0, k, fs = 1.0, 0.5, 0.6
    assert solute_in_liquid(C0, k, fs) == pytest.approx((1.0 - fs) * scheil_liquid_composition(C0, k, fs))


def test_scheil_solid_composition_rejects_bad_fraction():
    with pytest.raises(ValueError):
        scheil_solid_composition(1.0, 0.5, 1.0)        # f_s = 1 is the singularity, disallowed


# --------------------------------------------------------------------------- #
# Liquidus & Chvorinov
# --------------------------------------------------------------------------- #
def test_liquidus_below_pure_iron_and_carbon_dominates():
    s = STEELS["4140"]
    comp = {"C": s.C, "Mn": s.Mn, "Si": s.Si, "Ni": s.Ni, "Cr": s.Cr, "Mo": s.Mo}
    T_liq = liquidus_temperature(comp)
    assert T_liq < T_PURE_FE                            # alloy depresses the melting point
    assert 1480.0 < T_liq < 1520.0                     # a low-alloy steel liquidus, ballpark
    # Carbon (m = 78) dominates the depression: removing it lifts the liquidus most.
    no_C = dict(comp, C=0.0)
    assert liquidus_temperature(no_C) - T_liq == pytest.approx(78.0 * s.C, abs=1e-6)


def test_chvorinov_scales_with_modulus_squared():
    t1 = chvorinov_time(0.02)
    t2 = chvorinov_time(0.04)                           # double the modulus
    assert t2 / t1 == pytest.approx(4.0)               # → 4× the time (t ∝ M²)
    assert chvorinov_time(0.0) == 0.0


def test_casting_modulus_is_volume_over_area():
    assert casting_modulus(1.0e-3, 0.5) == pytest.approx(2.0e-3)
    with pytest.raises(ValueError):
        casting_modulus(1.0, 0.0)


# --------------------------------------------------------------------------- #
# The centerline enrichment + the cast_billet handoff
# --------------------------------------------------------------------------- #
def test_centerline_enriches_alloys_but_not_carbon_by_default():
    s = STEELS["4140"]
    ctr = centerline_enriched_composition(s, FS_CENTERLINE, "delta")
    # The substitutional alloys are enriched (the hardenability drivers); carbon is left at nominal.
    assert ctr.Mn > s.Mn and ctr.Cr > s.Cr and ctr.Mo > s.Mo and ctr.Si > s.Si
    assert ctr.C == s.C
    # Each alloy enrichment is exactly its solid segregation ratio (the handoff uses C_s, not C_L).
    assert ctr.Mn == pytest.approx(s.Mn * segregation_ratio(partition_coefficient("Mn", "delta"), FS_CENTERLINE))


def test_centerline_can_enrich_carbon_when_asked():
    s = STEELS["4140"]
    assert centerline_enriched_composition(s, FS_CENTERLINE, "delta", enrich_carbon=True).C > s.C


def test_gamma_phase_segregates_alloys_differently_than_delta():
    s = STEELS["4140"]
    d = centerline_enriched_composition(s, FS_CENTERLINE, "delta")
    g = centerline_enriched_composition(s, FS_CENTERLINE, "gamma")
    # The phase switch must change the enrichment, tested on Si — a solute with a *primary-source-verified*
    # δ/γ split (Won-Thomas: kδ 0.77 vs kγ 0.52 → γ segregates Si far more). (The Cr/Ni/Mo coefficients are
    # a single representative value across phases, so they are deliberately NOT the discriminator here.)
    assert g.Si > d.Si
    assert SOLUTES["Si"].k_gamma < SOLUTES["Si"].k_delta


def test_cast_billet_emits_two_real_heats_with_cast_origin():
    s = STEELS["4140"]
    section = cast_billet(s, modulus=0.025)
    assert isinstance(section.nominal_heat, Heat) and isinstance(section.centerline_heat, Heat)
    # Nominal carries the ladle composition; the centerline is the enriched one.
    assert section.nominal_heat.as_steel() is s
    assert section.centerline_heat.composition.Mn > s.Mn
    # Both start their provenance with a real front-end "cast" origin (not from_grade's stand-in).
    for h in (section.nominal_heat, section.centerline_heat):
        assert h.history[0].name == "cast"
    # Chvorinov + liquidus were computed and are physical.
    assert section.solidification_time > 0.0
    assert section.liquidus < T_PURE_FE
    assert section.solidification_time == pytest.approx(chvorinov_time(0.025))


def test_cast_billet_accepts_a_raw_steel():
    # A composition straight off the ladle (not a registry grade) casts fine — the front end produces
    # arbitrary compositions, not just the four named grades.
    s = Steel(C=0.35, Mn=0.8, Cr=0.5, name="custom")
    section = cast_billet(s, modulus=0.03)
    assert section.centerline_heat.composition.Cr > s.Cr


# --------------------------------------------------------------------------- #
# cast_billet_onto — the Heat-consuming seam (the promoted demo-local re-base)
# --------------------------------------------------------------------------- #
def _parent_with_history() -> Heat:
    """A live Heat already carrying an upstream trail + a filled field + a defect — what a real chain hands
    the casting seam (so the re-base has a non-trivial provenance to thread through)."""
    origin = ProcessStep("trim", "trim to 4140", in_spec=True, flags_added=())
    return Heat(composition=STEELS["4140"], temperature_C=1550.0, oxygen_ppm=4.4,
                defects=("off-grade-composition",), history=(origin,))


def test_cast_billet_onto_rebases_the_nominal_onto_the_parents_trail():
    # The Heat-consuming twin threads ONE continuous trail across F4: the nominal section inherits the
    # parent's whole history (and filled fields + defects) with the SAME "cast" step appended — it does not
    # start a fresh trail the way bare cast_billet does.
    parent = _parent_with_history()
    onto = cast_billet_onto(parent, modulus=0.025)
    bare = cast_billet(parent.as_steel(), modulus=0.025)

    nominal = onto.nominal_heat
    assert nominal.history[:-1] == parent.history                  # the upstream trail is carried, unbroken
    assert nominal.history[-1] == bare.nominal_heat.history[-1]    # the appended step IS cast_billet's "cast"
    assert nominal.history[-1].name == "cast"
    assert nominal.defects == parent.defects                       # carried-forward flags ride the re-base
    assert nominal.oxygen_ppm == parent.oxygen_ppm                 # and the filled upstream fields


def test_cast_billet_onto_changes_nothing_but_the_nominal_trail():
    # The re-base is a pure repack: the nominal composition equals the parent's (cast_billet enriches only
    # the centerline), and every other CastSection field — centerline, Chvorinov time, liquidus — is exactly
    # bare cast_billet's. The seam adds no physics, only a continuous trail.
    parent = _parent_with_history()
    onto = cast_billet_onto(parent, modulus=0.025)
    bare = cast_billet(parent.as_steel(), modulus=0.025)

    assert onto.nominal_heat.as_steel() is parent.composition      # nominal == input (no enrichment)
    assert onto.nominal_heat.temperature_C == 25.0                 # solidus-cooled, like bare cast_billet
    assert onto.centerline_heat == bare.centerline_heat            # the segregation read is untouched
    for f in ("steel", "fs_centerline", "phase", "modulus", "solidification_time", "liquidus"):
        assert getattr(onto, f) == getattr(bare, f)
