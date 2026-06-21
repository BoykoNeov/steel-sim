"""Losability (``game.md`` §6, the Slice-1 acceptance bar) — every claimed knob has a way to lose.

Slice 0's critique was *"there is nothing to get wrong"*: one knob, seven auto-run stages, no other
decision and no other failure. Slice 1's bar, set by the advisor, is **losability** — for each stage that
claims a decision there must exist a wrong setting (every other knob at reference) that flips the finished
part's verdict to a **distinct** defect, *end to end*. A green firewall/golden-run/state test says nothing
about this: a gauntlet of purely cosmetic knobs passes all three while reproducing exactly the complaint.
So this file is the real teeth — one assertion per knob, against the **finished-part** readout.

The honest bound is pinned too: casting carries **no** losable lever on this grade (modulus sets only the
Chvorinov time; segregation is ``fs``-based and lands on the centerline, not the judged nominal part), so
a heavy section stays sound — a documented concession, not a fake slider (``test_cast_*`` below). And the
field-survival check pins the post-mortem's correctness: the flaw fields it reads on the part are the same
values their stage locked (the consequences are physical, not read off a drifted composition).

These numbers are emergent from the sealed engines (probed before they were written down), never scripted.
"""
import dataclasses

import pytest

from game import postmortem as pm
from game import state as gs


def _readout(**overrides) -> dict:
    """Play a whole heat with one or more knobs off reference; return the finished-part readout."""
    recipe = dataclasses.replace(gs.REFERENCE, **overrides)
    return gs.final_readout(gs.play_to_end(recipe=recipe))


def _flags(readout: dict) -> set[str]:
    """Everything wrong with the part: the post-mortem consequences + the chain's hard defects."""
    out = {c["flag"] for c in readout["consequences"]}
    if readout["off_grade"]:
        out.add("off-grade")
    if readout["soft_core"]:
        out.add("soft-core")
    return out


def test_the_reference_heat_is_sound():
    # The baseline every losability case is measured against: with no wrong call, the part is sound.
    r = gs.final_readout(gs.play_to_end(recipe=gs.REFERENCE))
    assert r["sound"] and not _flags(r)


# (label, knob override, the DISTINCT flaw that must appear) — one row per losable knob, the advisor's bar.
LOSABLE = [
    ("decarb · over-blow",   dict(carbon=0.25),          "off-grade"),
    ("decarb · under-blow",  dict(carbon=0.55),          "off-grade"),
    ("dephos · skipped",     dict(dephosphorize=False),  "cold-short"),
    # NB: the deox→porosity loss rides a thin ~2% supersaturation margin (a weak kill pins O on the C–O line,
    # S≈1.02 just over the CO product at the reference carbon). Deterministic, but if this row ever fails it
    # means the CO-line margin moved (an upstream carbon-dilution drift), not that the gauntlet itself broke.
    ("deox · weak Si kill",  dict(deoxidizer="Si"),      "gas-porosity"),
    ("deox · weak Mn kill",  dict(deoxidizer="Mn"),      "gas-porosity"),
    ("degas · shallow",      dict(degas_p_H2=0.1),       "hydrogen-flaking"),
    ("degas · none",         dict(degas_p_H2=1.0),       "hydrogen-flaking"),
    ("desulf · skipped",     dict(desulfurize=False),    pm.HIGH_SULFUR_SPEC),
    ("trim · carbon pickup", dict(carbon_pickup=True),   "off-grade"),
    ("quench · air (mild)",  dict(quench_medium="air"),  "soft-core"),
    ("quench · thick part",  dict(part_diameter=0.05),   "soft-core"),
]


@pytest.mark.parametrize("label, override, flaw", LOSABLE, ids=[r[0] for r in LOSABLE])
def test_a_wrong_knob_flips_the_verdict_to_its_own_defect(label, override, flaw):
    r = _readout(**override)
    assert not r["sound"], f"{label}: the part came out sound — the knob is cosmetic, nothing to get wrong"
    assert flaw in _flags(r), f"{label}: expected {flaw!r}, got {sorted(_flags(r))}"


def test_cast_modulus_is_an_honest_no_loss_pass_through():
    # The documented concession: casting cannot flip the verdict on this grade. Pinned so a later change
    # can't quietly turn it into a fake slider — if a real lever is found, this test should be rewritten.
    for modulus in (0.05, 0.10, 0.30):
        r = _readout(cast_modulus=modulus)
        assert r["sound"], f"modulus {modulus}: cast unexpectedly flipped the verdict — re-evaluate the knob"


def _heat_after(recipe, stage_name):
    """The live ``Heat`` right after the named stage runs — for the field-survival check."""
    state = gs.new_game(recipe=recipe)
    seen = None
    while not state.done:
        running = state.next_stage.name
        state = gs.advance(state)
        if running == stage_name:
            seen = state.heat
    return seen


def test_consequence_fields_survive_from_the_cast_lock_to_the_finished_part():
    # The post-mortem judges the finished part, but porosity/hot-tear/flaking physically lock at casting.
    # That read is only correct if the flaw fields survive unchanged through the composition-inert quench —
    # this pins it (the advisor's correctness concern), so the consequences are physical, not drift.
    recipe = dataclasses.replace(gs.REFERENCE, desulfurize=False, deoxidizer="Mn")
    cast_heat = _heat_after(recipe, "cast")
    part = gs.play_to_end(recipe=recipe).heat
    assert part.composition.C == cast_heat.composition.C
    assert part.composition.P == cast_heat.composition.P
    assert part.composition.S == cast_heat.composition.S
    assert part.composition.Mn == cast_heat.composition.Mn
    assert part.oxygen_ppm == cast_heat.oxygen_ppm
    assert part.hydrogen_ppm == cast_heat.hydrogen_ppm
