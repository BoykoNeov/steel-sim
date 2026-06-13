"""Seam-correctness tests for the front-end spine (``heat_state`` — the Heat record + orchestrator).

The spine adds **no physics** — it threads state through engines that are already benchmarked
elsewhere — so these are **structural** checks, not a new benchmark (the posture ``test_design.py``
takes for inverse design). They guard the things that make the seam trustworthy: the unpack is
non-lossy (round-trip identity), the record is immutable (a step never mutates its input), the trail
grows by exactly one entry per step, and a spec miss propagates deterministically to a defect flag.
The *numbers* (the 4140 martensite fractions, the 4340 residual sign) are owned by the back-end and
§18 tests; here we assert the seam carries them, not that they are right.
"""
import pytest

from dataclasses import replace

from steel import heat_state as hs
from steel.heat_state import (
    Heat, ProcessStep, heat_treat, quench_crack_check, cold_short_check, add_defect,
    SOFT_CORE, QUENCH_CRACK_RISK, COLD_SHORT, MIN_MARTENSITE_SPEC,
)
from steel.sweep import Steel, STEELS


# --------------------------------------------------------------------------- #
# The unpack seam — composition is the existing Steel, round trip is exact
# --------------------------------------------------------------------------- #
def test_as_steel_is_identity():
    # Heat *composes* the back-end Steel, so Steel → Heat → Steel returns the SAME object.
    s = STEELS["4140"]
    assert Heat(composition=s).as_steel() is s


def test_round_trip_preserves_composition_fields():
    s = Steel(C=0.41, Mn=0.92, Si=0.24, Ni=0.1, Cr=1.05, Mo=0.21, name="probe")
    back = Heat(composition=s).as_steel()
    assert (back.C, back.Mn, back.Si, back.Ni, back.Cr, back.Mo, back.name) == \
           (s.C, s.Mn, s.Si, s.Ni, s.Cr, s.Mo, s.name)


# --------------------------------------------------------------------------- #
# Immutability + the provenance trail
# --------------------------------------------------------------------------- #
def test_heat_is_frozen():
    h = Heat(composition=STEELS["1045"])
    with pytest.raises(Exception):           # FrozenInstanceError (a dataclasses subclass)
        h.temperature_C = 500.0              # type: ignore[misc]


def test_evolve_returns_new_heat_and_appends_one_step():
    h0 = Heat(composition=STEELS["1045"])
    step = ProcessStep("probe", "did a thing", in_spec=True)
    h1 = h0.evolve(step, temperature_C=42.0)
    assert h1 is not h0                       # a fresh Heat
    assert h0.history == () and h0.temperature_C is None   # the original is untouched
    assert h1.history == (step,) and h1.temperature_C == 42.0


def test_heat_treat_grows_history_by_exactly_one_and_leaves_input_untouched():
    h0 = Heat.from_grade("4140")             # one origin step
    n0 = len(h0.history)
    h1 = heat_treat(h0)
    assert len(h1.history) == n0 + 1
    assert h1.history[:n0] == h0.history      # the prior trail is carried verbatim
    assert len(h0.history) == n0 and h0.defects == ()   # input Heat unchanged


# --------------------------------------------------------------------------- #
# Failure propagation through the general path (heat_treat, any composition)
# --------------------------------------------------------------------------- #
def test_under_dosed_alloy_raises_soft_core_well_dosed_does_not():
    well = heat_treat(Heat.from_grade("4140"), medium="oil", diameter=0.010)
    under = heat_treat(
        Heat(composition=Steel(C=0.40, Mn=0.90, Si=0.25, Cr=0.10, Mo=0.0, name="lean")),
        medium="oil", diameter=0.010)
    # The whole point: same treatment, the off-spec composition is the one that fails.
    assert well.is_clean and not well.has_defect(SOFT_CORE)
    assert under.has_defect(SOFT_CORE) and not under.is_clean
    # The step records WHY (in_spec tracks the flag).
    assert well.history[-1].in_spec is True
    assert under.history[-1].in_spec is False
    assert under.history[-1].flags_added == (SOFT_CORE,)


def test_soft_core_flag_tracks_the_spec_threshold():
    # The flag is the martensite fraction crossing the spec line — push the spec and a passing
    # heat fails, with nothing else changed. Confirms the threshold is the discriminator.
    h = Heat.from_grade("4140")
    lenient = heat_treat(h, medium="oil", diameter=0.010, min_martensite=0.50)
    strict = heat_treat(h, medium="oil", diameter=0.010, min_martensite=0.999)
    assert not lenient.has_defect(SOFT_CORE)      # ~96% martensite clears 0.50
    assert strict.has_defect(SOFT_CORE)           # ~96% martensite misses 0.999


def test_default_spec_is_a_fraction():
    assert 0.0 < MIN_MARTENSITE_SPEC <= 1.0


# --------------------------------------------------------------------------- #
# Flag bookkeeping — no duplicates, additive
# --------------------------------------------------------------------------- #
def test_add_defect_is_idempotent():
    assert add_defect((), SOFT_CORE) == (SOFT_CORE,)
    assert add_defect((SOFT_CORE,), SOFT_CORE) == (SOFT_CORE,)        # no duplicate
    assert add_defect((SOFT_CORE,), QUENCH_CRACK_RISK) == (SOFT_CORE, QUENCH_CRACK_RISK)


def test_re_quenching_a_flagged_heat_does_not_duplicate_the_flag():
    under = heat_treat(
        Heat(composition=Steel(C=0.40, Mn=0.90, Si=0.25, Cr=0.10, Mo=0.0, name="lean")),
        medium="oil", diameter=0.010)
    again = heat_treat(under, medium="oil", diameter=0.010)
    assert again.defects.count(SOFT_CORE) == 1
    assert again.history[-1].flags_added == ()       # already flagged → this step adds none


# --------------------------------------------------------------------------- #
# from_grade origin
# --------------------------------------------------------------------------- #
def test_from_grade_seeds_an_origin_step():
    h = Heat.from_grade("8620")
    assert h.composition is STEELS["8620"]
    assert len(h.history) == 1 and h.history[0].name == "charge" and h.is_clean


def test_from_grade_rejects_unknown_grade():
    with pytest.raises(KeyError):
        Heat.from_grade("inconel-718")


# --------------------------------------------------------------------------- #
# The fixed atlas-steel quench-crack illustration (a second engine, honestly bounded)
# --------------------------------------------------------------------------- #
def test_quench_crack_check_repacks_residual_and_flag_for_an_atlas_steel():
    h = Heat(composition=Steel(C=0.40, Mn=0.70, Si=0.25, Ni=1.80, Cr=0.80, Mo=0.25, name="4340"))
    out = quench_crack_check(h, 0.025, grade="4340")
    # The seam repacked a number onto the Heat, and the flag agrees with the engine's own criterion.
    assert out.residual_stress_MPa is not None
    assert out.has_defect(QUENCH_CRACK_RISK) == (out.residual_stress_MPa > 0.0)
    # A through-hardening 4340 plate with transformation ON locks the surface into tension → crack-risk.
    assert out.has_defect(QUENCH_CRACK_RISK)
    assert out.history[-1].name == "quench-crack-check"


def test_quench_crack_check_thermal_only_reference_is_safe():
    # transform=False removes the dilatation → no surface tension → no flag (the §18 sign reversal,
    # carried through the seam unchanged). Pairs with the ON case above.
    h = Heat(composition=Steel(C=0.40, name="4340"))
    out = quench_crack_check(h, 0.025, grade="4340", transform=False)
    assert not out.has_defect(QUENCH_CRACK_RISK)
    assert out.residual_stress_MPa < 0.0          # compression — the safe reference


def test_quench_crack_check_rejects_non_atlas_grade():
    # The honest bound: the §18 engine is atlas-anchored, so a non-atlas Heat raises rather than
    # silently pretending the off-spec-composition → crack chain exists (it is deferred).
    with pytest.raises(ValueError):
        quench_crack_check(Heat.from_grade("4140"), 0.025)


# --------------------------------------------------------------------------- #
# cold_short_check — the phosphorus consequence, a PROPAGATION through grain.py
# --------------------------------------------------------------------------- #
# Closes the F2-Slice-2 deferral for phosphorus: P threads the EXISTING Pickering DBTT law (grain.py), so an
# off-spec-P heat normalizes brittle. This is the spine-class propagation (unlike sulfur's new hot_work
# consumer). The teeth are in grain.py (the P strengthening rate); here we test the SEAM and the SPLIT.
_STRUCT = replace(STEELS["1045"], C=0.12, Mn=0.50, Si=0.15, name="structural")


def test_phosphorus_split_inert_in_heat_treat_consumed_in_cold_short():
    # THE SPLIT (steel-making.md §14): phosphorus now propagates on EXACTLY ONE path. CONSUMED in
    # cold_short_check (off-spec-P normalizes brittle, clean stays ductile) yet INERT in heat_treat
    # (hardenability / hardness / martensite read C/Si/Mn/Ni/Cr/Mo only — minor() excludes P).
    clean = Heat(composition=replace(_STRUCT, P=0.005))
    dirty = Heat(composition=replace(_STRUCT, P=0.35))          # acid-Bessemer-retained, phosphoric
    # consumed in cold_short_check — the off-spec heat flips to brittle
    assert not cold_short_check(clean).has_defect(COLD_SHORT)
    assert cold_short_check(dirty).has_defect(COLD_SHORT)
    # still inert in heat_treat — martensite and hardness identical (P excluded from the back-end dict)
    from steel.sweep import evaluate
    ec = evaluate(clean.composition, medium="oil", diameter=0.015)
    ed = evaluate(dirty.composition, medium="oil", diameter=0.015)
    assert ec.HV == ed.HV and ec.result.martensite == ed.result.martensite
    assert clean.composition.minor() == dirty.composition.minor()


def test_cold_short_check_evolves_heat_and_records_a_step():
    out = cold_short_check(Heat(composition=replace(_STRUCT, P=0.35)))
    assert out.has_defect(COLD_SHORT)
    assert out.history[-1].name == "cold-short-check" and out.history[-1].in_spec is False
    assert out.history[-1].flags_added == (COLD_SHORT,)
    assert out.grain_size_um is not None and out.grain_size_um > 0.0   # PAGS repacked from the normalize


def test_cold_short_check_clean_heat_stays_clean():
    out = cold_short_check(Heat(composition=replace(_STRUCT, P=0.005)))
    assert not out.has_defect(COLD_SHORT) and out.is_clean and out.history[-1].in_spec is True


def test_cold_short_check_service_temperature_raises_the_bar():
    # A colder service temperature is harder to pass: a heat ductile at room temperature can be cold-short
    # for cryogenic service (the DBTT must beat the service temperature).
    h = Heat(composition=replace(_STRUCT, P=0.10))
    assert not cold_short_check(h, service_T=20.0).has_defect(COLD_SHORT)   # DBTT below room temp
    assert cold_short_check(h, service_T=-80.0).has_defect(COLD_SHORT)      # but above −80 °C
