"""Choices (``game.md`` §6) — the gauntlet's decisions are well-formed and the recommendation is the capstone.

The load-bearing property: **taking every recommended option reproduces the sound reference run** (so the
golden-run equality is what the player gets for playing it safe), and every stage but casting offers a real
decision. If a "recommended" value drifted off the reference, the safe path would silently stop matching
``run_chain`` — these pin that it can't.
"""
import dataclasses

import pytest

from game import choices as ch
from game import state as gs


def test_stage_decisions_cover_every_stage_exactly():
    assert set(ch.STAGE_DECISIONS) == {s.name for s in gs.STAGES}
    assert ch.STAGE_DECISIONS["cast"] == ()                       # the honest pass-through asks nothing
    assert all(ch.STAGE_DECISIONS[s.name] for s in gs.STAGES if s.name != "cast")


def test_every_named_knob_has_a_decision_table():
    named = {k for knobs in ch.STAGE_DECISIONS.values() for k in knobs if k != "carbon"}
    assert named == set(ch.DECISIONS)
    recipe_fields = {f.name for f in dataclasses.fields(gs.Recipe)}
    assert named <= recipe_fields


@pytest.mark.parametrize("knob, decision", list(ch.DECISIONS.items()), ids=list(ch.DECISIONS))
def test_each_decision_has_one_recommendation_that_matches_the_reference(knob, decision):
    recommended = [o for o in decision.options if o.recommended]
    assert len(recommended) == 1, f"{knob}: exactly one option must be recommended"
    assert len(decision.options) >= 2, f"{knob}: a decision needs at least one alternative to be losable"
    # The recommendation IS the capstone reference value — the safe path reproduces run_chain.
    assert recommended[0].value == getattr(gs.REFERENCE, knob)
    assert decision.options[decision.default_index()] is decision.recommended()


def test_taking_every_recommendation_is_the_reference_recipe():
    recipe = gs.REFERENCE
    for knobs in ch.STAGE_DECISIONS.values():
        for knob in knobs:
            if knob in ch.DECISIONS:
                recipe = dataclasses.replace(recipe, **{knob: ch.DECISIONS[knob].recommended().value})
    assert recipe == gs.REFERENCE                                 # nothing drifted off the sound reference
