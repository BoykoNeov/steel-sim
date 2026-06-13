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
    FERROALLOYS, GRADE_WINDOWS, HEAT_MASS_KG, OFF_GRADE,
    mix, additions_for_grade, slag_loss, carbon_pickup_pct,
    in_window, off_grade_elements, is_on_grade, from_tap, trim_to_grade,
)
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
# The carbon carry-in deferral — named and quantified, not applied
# --------------------------------------------------------------------------- #
def test_carbon_carry_in_is_quantified_but_not_applied():
    # The deferred coupling made concrete: high-carbon ferroalloys WOULD add carbon (a sizeable fraction of
    # the grade's), but mix() holds carbon on F2's axis (only dilutes it down, never up).
    tap = from_tap("4140").composition
    charges = additions_for_grade(tap, STEELS["4140"])
    assert carbon_pickup_pct(charges) > 0.10           # ~0.18 %C of carry-in if HC alloys were used
    trimmed, _ = mix(tap, charges)
    assert trimmed.C <= tap.C + 1e-12                   # mix does NOT add that carbon (carbon only dilutes)


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
