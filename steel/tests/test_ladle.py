"""Tests for F3 ladle trim (Slice 1): the mixing arithmetic, the grade window, and the trim seam.

The non-circularity split — and the honest fact that **F3 is spine-class** (like ``test_heat_state``, not
``test_refining``): there is no new physics here, so most checks are *structural*, not a benchmark.

* **Structural (could catch a transcription/wiring bug, but are by-construction, NOT a physics benchmark):**
  the inverse→forward round-trip reproduces the aim (forward and inverse are the same mass balance read two
  ways); the element conservation closes (added = recovered into steel + lost to slag); the added mass
  *dilutes* the untrimmed carbon; the cited SAE window bands are wired correctly at their edges; the trim
  seam fills the composition and raises the off-grade flag deterministically; the ``Heat`` is immutable.
* **The labelled spec (NOT teeth):** the grade window itself — a commercial chemistry tolerance, the same
  kind of line as ``heat_state.MIN_MARTENSITE_SPEC`` / ``refining.MAX_DISSOLVED_OXYGEN_PPM``. Aiming at the
  window and accounting for recovery lands inside it by construction.

The genuinely *validated* content — an under-trim propagating to a back-end **soft core** (the same class as
the spine's hand-set under-dose, now produced by a recovery shortfall) — rides the already-benchmarked back
end and is exercised in ``test_demo_ladle``.
"""
import pytest

from steel import ladle as ld
from steel.ladle import (
    FERROALLOYS, LOW_CARBON_FERROALLOYS, GRADE_WINDOWS, HEAT_MASS_KG, OFF_GRADE,
    OXIDIZABLE_TRIM_ELEMENTS, mix, additions_for_grade, slag_loss, carbon_pickup_pct,
    oxidation_recovery_loss, recovery_after_deox,
    in_window, off_grade_elements, is_on_grade, from_tap, trim_to_grade,
)
from steel import refining as rf
from steel.heat_state import Heat, SOFT_CORE
from steel.sweep import Steel, STEELS


# --------------------------------------------------------------------------- #
# The mixing arithmetic — structural (round-trip, conservation, dilution)
# --------------------------------------------------------------------------- #
def test_inverse_then_forward_reproduces_the_aim():
    # Structural identity (NOT teeth): additions_for_grade sizes the charges, mix puts them in, and the
    # trimmed elements land on the aim — because forward and inverse are the same mass balance. Guards the
    # closed-form transcription; it cannot fail "informatively" about physics.
    tap = from_tap("4140").composition
    aim = STEELS["4140"]
    charges = additions_for_grade(tap, aim)
    trimmed, _ = mix(tap, charges)
    for el in ("Mn", "Si", "Cr", "Mo"):
        assert getattr(trimmed, el) == pytest.approx(getattr(aim, el), abs=1e-6)


def test_conservation_added_equals_recovered_plus_slag():
    # The mass-balance check (as in test_casting's conservation leg): for each addition the element added
    # (charge × assay) is exactly the element recovered into steel + the element lost to slag. Crosses the
    # recovery split, so a wrong slag/recovery wiring would break it.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    loss = slag_loss(charges)
    for e, a in charges.items():
        fa = FERROALLOYS[e]
        added = a * fa.element_fraction
        recovered = added * fa.recovery
        assert added == pytest.approx(recovered + loss[e], rel=1e-12)


def test_mixing_dilutes_the_untrimmed_carbon():
    # The "dilution exact" leg: the ~3 t of additions raise the bath mass, so carbon (never trimmed) lands
    # BELOW the tap value. A model that ignored dilution would leave carbon unchanged — this catches that.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    trimmed, bath = mix(tap, charges)
    assert bath > HEAT_MASS_KG                         # mass was added
    assert trimmed.C < tap.C                           # and it diluted the carbon
    assert trimmed.C == pytest.approx(tap.C * HEAT_MASS_KG / bath, rel=1e-9)


def test_under_recovery_lands_short_of_target():
    # Sizing for full recovery but delivering half lands the element short (the failure mechanism). Direction
    # check on the recovery wiring: less recovery ⇒ less landed.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])           # sized for nominal recovery
    full, _ = mix(tap, charges)
    half, _ = mix(tap, charges, recovery={"Cr": FERROALLOYS["Cr"].recovery * 0.5})
    assert half.Cr < full.Cr
    assert full.Cr == pytest.approx(STEELS["4140"].Cr, abs=1e-6)  # full recovery hits aim


def test_additions_only_trim_deficient_substitutionals_never_carbon():
    # By construction: an element already at/above aim gets no charge, and carbon is never trimmed (held on
    # F2's axis) even though the tap carbon equals the aim carbon.
    tap = Steel(C=0.40, Mn=1.20, Si=0.05, Cr=0.05, Mo=0.0, name="4140")   # Mn already over aim
    charges = additions_for_grade(tap, STEELS["4140"])
    assert "Mn" not in charges                          # already above target
    assert "C" not in charges                           # carbon is never a trim element
    assert "Cr" in charges and "Mo" in charges


# --------------------------------------------------------------------------- #
# The grade window — the labelled spec (membership wired to the cited bands)
# --------------------------------------------------------------------------- #
def test_window_membership_at_the_cited_band_edges():
    # Transcription guard for the SAE J404 numbers: a composition exactly at the 4140 band edges is IN; one
    # just outside a single band is OUT (and names that element). Not a physics benchmark — a wiring check.
    w = GRADE_WINDOWS["4140"].bands
    edge = Steel(C=w["C"][0], Mn=w["Mn"][1], Si=w["Si"][0], Cr=w["Cr"][0], Mo=w["Mo"][1], name="4140")
    assert is_on_grade(edge, "4140")
    just_low_cr = Steel(C=0.40, Mn=0.90, Si=0.25, Cr=w["Cr"][0] - 0.01, Mo=0.20, name="4140")
    assert off_grade_elements(just_low_cr, "4140") == ["Cr"]


def test_off_grade_elements_flags_low_cr_and_mo():
    under = Steel(C=0.40, Mn=0.90, Si=0.25, Cr=0.50, Mo=0.10, name="4140")
    off = off_grade_elements(under, "4140")
    assert set(off) == {"Cr", "Mo"}
    assert not is_on_grade(under, "4140")


def test_phosphorus_sulphur_are_not_in_the_window():
    # The named deferral: the Steel vector carries no P/S, so the residual bands are absent (not silently
    # passing). Only the elements the back end reads are checked.
    assert set(GRADE_WINDOWS["4140"].bands) == {"C", "Mn", "Si", "Cr", "Mo"}
    assert "P" not in GRADE_WINDOWS["4140"].bands and "S" not in GRADE_WINDOWS["4140"].bands


# --------------------------------------------------------------------------- #
# The carbon carry-in — the Slice-1 default (off), and the opt-in consequence
# --------------------------------------------------------------------------- #
def test_carbon_carry_in_default_off_holds_carbon_on_f2_axis():
    # The Slice-1 default: high-carbon ferroalloys WOULD add carbon (a sizeable fraction of the grade's), but
    # mix() with the default apply_carbon_pickup=False holds carbon on F2's axis (only dilutes it down).
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    assert carbon_pickup_pct(charges) > 0.10           # ~0.18 %C of carry-in with the HC alloys
    trimmed, _ = mix(tap, charges)
    assert trimmed.C <= tap.C + 1e-12                  # default: mix does NOT add carbon (only dilutes)
    assert trimmed == mix(tap, charges, apply_carbon_pickup=False)[0]   # the flag default is a no-op


def test_high_carbon_pickup_drags_carbon_off_the_grade_band():
    # The consequence on: the carbon the high-carbon ferroalloys carry is added (net of dilution), pushing the
    # bath above 4140's carbon ceiling — so off-grade fires on CARBON through the existing window machinery.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    trimmed, _ = mix(tap, charges, apply_carbon_pickup=True)
    assert trimmed.C > GRADE_WINDOWS["4140"].bands["C"][1]   # above the 0.43 % ceiling
    assert "C" in off_grade_elements(trimmed, "4140")        # the verdict is off-grade-on-carbon


def test_low_carbon_ferroalloys_carry_the_same_trim_on_grade():
    # The lever: the SAME charges (LC and HC size identically — same assay/recovery), but the refined
    # low-carbon grades carry ~no carbon, so the heat stays on its carbon band and on grade.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    lo, hi = GRADE_WINDOWS["4140"].bands["C"]
    trimmed, _ = mix(tap, charges, apply_carbon_pickup=True, ferroalloys=LOW_CARBON_FERROALLOYS)
    assert lo <= trimmed.C <= hi                             # carbon stays in band
    assert is_on_grade(trimmed, "4140")                      # and on grade (alloys landed, carbon held)
    assert carbon_pickup_pct(charges, ferroalloys=LOW_CARBON_FERROALLOYS) < 0.02   # an OoM less carry-in


def test_carbon_carry_in_conserves_mass():
    # By construction: the carbon the bath gains equals exactly Σ charge × carbon_fraction (recovered ~fully —
    # carbon does not oxidise off). Reads the new carbon mass against the bath mix() returns.
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    trimmed, bath = mix(tap, charges, apply_carbon_pickup=True)
    gained = trimmed.C / 100.0 * bath - tap.C / 100.0 * HEAT_MASS_KG
    expected = sum(charges[e] * FERROALLOYS[e].carbon_fraction for e in charges)
    assert gained == pytest.approx(expected, rel=1e-9)


def test_trim_to_grade_carbon_pickup_raises_off_grade_on_carbon():
    # End-to-end seam: a high-carbon trim raises off-grade (on carbon); the same trim with low-carbon grades
    # lands clean — one mistake (the wrong ferroalloy grade), distinct from the recovery shortfall.
    hc = trim_to_grade(from_tap("4140"), "4140", apply_carbon_pickup=True)
    assert hc.has_defect(OFF_GRADE)
    assert off_grade_elements(hc.composition, "4140") == ["C"]
    lc = trim_to_grade(from_tap("4140"), "4140", apply_carbon_pickup=True, ferroalloys=LOW_CARBON_FERROALLOYS)
    assert lc.is_clean


# --------------------------------------------------------------------------- #
# The orchestrator seam — fills the composition, raises the off-grade flag
# --------------------------------------------------------------------------- #
def test_from_tap_is_alloy_lean_on_carbon():
    tap = from_tap("4140")
    assert tap.composition.C == STEELS["4140"].C       # carbon set by the F2 blow
    assert tap.composition.Cr < 0.10 and tap.composition.Mo == 0.0   # lean in the alloys, to be trimmed
    assert tap.composition.name == "4140"              # keeps the target grade so the window check knows it
    assert tap.history[0].name == "tap"
    assert tap.is_clean


def test_trim_to_grade_lands_on_grade_at_assumed_recovery():
    # Delivered = assumed ⇒ on grade, no flag (the labelled spec is met by construction when recovery holds).
    trimmed = trim_to_grade(from_tap("4140"), "4140")
    assert is_on_grade(trimmed.composition, "4140")
    assert trimmed.is_clean
    assert trimmed.history[-1].name == "trim"


def test_trim_to_grade_under_recovery_raises_off_grade():
    # The failure: the bath delivers half the assumed Cr/Mo recovery, so the heat lands below the window and
    # the off-grade flag is raised (with Cr/Mo named on the trail).
    assumed = {e: FERROALLOYS[e].recovery for e in ("Mn", "Si", "Cr", "Mo")}
    actual = {**assumed, "Cr": assumed["Cr"] * 0.5, "Mo": assumed["Mo"] * 0.5}
    bad = trim_to_grade(from_tap("4140"), "4140", actual_recovery=actual)
    assert bad.has_defect(OFF_GRADE)
    assert set(off_grade_elements(bad.composition, "4140")) == {"Cr", "Mo"}
    assert bad.composition.Cr < GRADE_WINDOWS["4140"].bands["Cr"][0]


def test_trim_to_grade_is_immutable():
    # Carried from the spine: trimming returns a new Heat; the tap is untouched.
    tap = from_tap("4140")
    trim_to_grade(tap, "4140")
    assert tap.composition.Cr < 0.10                   # still the lean tap
    assert tap.is_clean and len(tap.history) == 1


def test_8620_also_trims_into_its_window():
    # The "land a named grade" check on a second, different grade (carburizing 8620 carries Ni) — the trim
    # is not over-fit to 4140.
    trimmed = trim_to_grade(from_tap("8620"), "8620")
    assert is_on_grade(trimmed.composition, "8620")
    assert trimmed.composition.Ni == pytest.approx(STEELS["8620"].Ni, abs=1e-6)


# --------------------------------------------------------------------------- #
# The deox→recovery coupling — F2's dissolved oxygen taxes the oxidizable trim (the F2→F3 seam)
# --------------------------------------------------------------------------- #
# This is spine-class arithmetic, NOT a physics benchmark: the tax is the same mass balance refining's
# generated_oxide uses (oxygen × stoichiometry), read onto recovery. The checks are structural — selectivity
# (which elements carry a deox reaction), direction (more O ⇒ less recovery), and the *honest magnitude* (the
# tax is sub-window, which is why demo_ladle's gross hero is hand-set).
def test_oxidizable_trim_is_exactly_the_deoxidizing_elements():
    # Selectivity by construction: the taxed set is the trim elements that carry a deox reaction (Mn, Si),
    # never the noble hardenability alloys (Cr/Mo/Ni). This is the intersection, computed not asserted.
    assert OXIDIZABLE_TRIM_ELEMENTS == ("Mn", "Si")
    assert all(e in rf.DEOXIDIZERS for e in OXIDIZABLE_TRIM_ELEMENTS)
    assert not any(e in rf.DEOXIDIZERS for e in ("Cr", "Mo", "Ni"))


def test_oxidation_tax_falls_only_on_mn_si_not_the_noble_alloys():
    charges = additions_for_grade(from_tap("4140").composition, STEELS["4140"])
    loss = oxidation_recovery_loss(charges, oxygen_ppm=105.0)
    assert set(loss) <= {"Mn", "Si"}                         # only the oxidizable alloys are taxed
    assert loss["Mn"] > 0.0                                  # and they genuinely are
    rec = recovery_after_deox(charges, oxygen_ppm=105.0)
    for noble in ("Cr", "Mo"):
        assert rec[noble] == pytest.approx(FERROALLOYS[noble].recovery)   # noble recovery is oxygen-independent


def test_oxidation_tax_rises_with_oxygen_and_is_zero_at_zero():
    # Direction + the no-oxygen limit: a hotter bath taxes Mn more; a (hypothetical) oxygen-free bath does not.
    charges = additions_for_grade(from_tap("4140").composition, STEELS["4140"])
    assert oxidation_recovery_loss(charges, 0.0) == {}
    lo = oxidation_recovery_loss(charges, 30.0)["Mn"]
    hi = oxidation_recovery_loss(charges, 110.0)["Mn"]
    assert 0.0 < lo < hi


def test_oxidation_tax_matches_the_stoichiometric_mass_balance():
    # The arithmetic IS conservation (NOT a benchmark): the Mn mass lost = its share of the dissolved-oxygen
    # mass × the MnO metal-per-oxygen stoichiometry. Recomputed independently from the cited oxide data.
    charges = {"Mn": 800.0, "Si": 200.0, "Cr": 100.0}       # Cr present but noble (gets no oxygen)
    O_ppm = 80.0
    delivered = {e: charges[e] * FERROALLOYS[e].element_fraction for e in ("Mn", "Si")}
    total = sum(delivered.values())
    O_mass = O_ppm * 1e-6 * HEAT_MASS_KG
    d = rf.DEOXIDIZERS["Mn"]
    metal_per_O = (1.0 - d.oxide_O_mass_frac) / d.oxide_O_mass_frac
    expected_mn = (O_mass * delivered["Mn"] / total) * metal_per_O / delivered["Mn"]
    assert oxidation_recovery_loss(charges, O_ppm)["Mn"] == pytest.approx(expected_mn, rel=1e-12)


def test_tax_is_sub_window_cannot_trip_off_grade():
    # The honest magnitude (the build's whole point): even a fully under-killed bath at 4140's carbon leaves
    # the landed Mn ABOVE the window floor — the dissolved-O coupling alone cannot drive a heat off grade,
    # which is why demo_ladle's gross under-trim hero must be hand-set.
    tap = from_tap("4140")
    charges = additions_for_grade(tap.composition, STEELS["4140"])
    O = rf.equilibrium_oxygen(tap.composition.C)             # ~53 ppm, the un-killed C–O equilibrium
    trimmed, _ = mix(tap.composition, charges, recovery=recovery_after_deox(charges, O))
    assert trimmed.Mn > GRADE_WINDOWS["4140"].bands["Mn"][0]     # still in window
    assert oxidation_recovery_loss(charges, O)["Mn"] / FERROALLOYS["Mn"].recovery < 0.05   # a few %, not halved


def test_couple_deox_recovery_produces_the_shortfall_from_the_heats_oxygen():
    # The seam wired through trim_to_grade: an under-killed Heat (high oxygen_ppm) lands Mn LOWER than a
    # well-killed one, from the SAME charges — the recovery shortfall produced, not hand-set. Cr holds.
    well = rf.deoxidize(from_tap("4140"), "Al", 0.04)        # O ~4 ppm
    under = rf.deoxidize(from_tap("4140"), "Si", 0.05)       # O ~53 ppm, porosity-risk
    tw = trim_to_grade(well, "4140", couple_deox_recovery=True)
    tu = trim_to_grade(under, "4140", couple_deox_recovery=True)
    assert tu.composition.Mn < tw.composition.Mn                 # the under-killed heat lands Mn short
    # noble Cr is oxygen-independent in RECOVERY; its landed wt % shifts only by the tiny bath-mass dilution
    # coupling (less Mn/Si retained ⇒ a hair lighter bath ⇒ a hair more concentrated), not the oxygen tax.
    charges = additions_for_grade(under.composition, STEELS["4140"])
    assert recovery_after_deox(charges, under.oxygen_ppm)["Cr"] == pytest.approx(FERROALLOYS["Cr"].recovery)
    assert tu.composition.Cr == pytest.approx(tw.composition.Cr, abs=1e-3)
    assert is_on_grade(tu.composition, "4140")                  # but still on grade (sub-window tax)
    assert tu.has_defect("porosity-risk") and not tu.has_defect(OFF_GRADE)   # one cause: F2's flag, no new one


def test_couple_deox_recovery_is_a_no_op_without_oxygen_state():
    # When the Heat carries no oxygen_ppm (a bare tap), the coupling cannot fire — it falls back to the nominal
    # recovery and lands on grade, exactly as the default trim. The hand-set actual_recovery still wins if given.
    tap = from_tap("4140")
    assert tap.oxygen_ppm is None
    coupled = trim_to_grade(tap, "4140", couple_deox_recovery=True)
    assert is_on_grade(coupled.composition, "4140") and coupled.is_clean
