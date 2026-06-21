"""State-transition (``game.md`` §3/§8) — each turn pushes one new immutable ``Heat``; restart is clean.

The new surface the game stands up (``game.md`` §3): a live ``Heat`` evolving across turns. Because
``Heat`` is frozen and append-only, the turn structure is exact — :func:`game.state.advance` runs **one**
sealed stage and the trail grows by **exactly one** ``ProcessStep``, the receiver is never mutated, and a
restart resets to a fresh origin. These pin that the game *drives* the spine's history rather than
inventing its own.
"""
import dataclasses

import pytest

from game import state as gs
from steel.demo_capstone import REF_CARBON


def test_new_game_starts_at_the_charge_origin():
    state = gs.new_game(REF_CARBON)
    assert state.stage == 0 and not state.done
    assert len(state.heat.history) == 1 and state.heat.history[0].name == "hot-metal charge"
    assert state.carbon_target == REF_CARBON


def test_advance_appends_exactly_one_step_and_is_immutable():
    before = gs.new_game(REF_CARBON)
    n_before = len(before.heat.history)
    after = gs.advance(before)

    assert len(after.heat.history) == n_before + 1     # exactly one ProcessStep added
    assert after.stage == before.stage + 1
    assert after.heat is not before.heat               # a new immutable Heat
    assert len(before.heat.history) == n_before        # the receiver is untouched (frozen)
    assert before.stage == 0


def test_every_turn_grows_the_trail_by_one_to_the_finished_part():
    state = gs.new_game(REF_CARBON)
    counts = [len(state.heat.history)]
    while not state.done:
        state = gs.advance(state)
        counts.append(len(state.heat.history))
    assert all(b - a == 1 for a, b in zip(counts, counts[1:])), counts
    assert state.done and state.stage == len(gs.STAGES)
    assert state.next_stage is None


def test_advancing_past_the_end_raises():
    state = gs.play_to_end(REF_CARBON)
    assert state.done
    with pytest.raises(RuntimeError):
        gs.advance(state)


def test_restart_resets_cleanly():
    played = gs.play_to_end(REF_CARBON)
    fresh = gs.new_game(REF_CARBON)                     # "restart" is just a new game
    assert fresh.stage == 0 and len(fresh.heat.history) == 1
    assert played.done and not fresh.done               # the old state is independent, unchanged


def test_every_stage_but_cast_carries_a_player_knob():
    # The Slice-1 gauntlet: every stage is a decision except casting, which is an honest pass-through
    # (no pass/fail lever on this grade — modulus only sets the Chvorinov time).
    knob_stages = {s.name: s.knob for s in gs.STAGES}
    assert knob_stages["cast"] is None
    assert all(s.knob is not None for s in gs.STAGES if s.name != "cast")


def test_every_stage_knob_names_a_real_recipe_field():
    # Each stage's knob must point at an actual Recipe field, or the UI/attribution would dangle.
    recipe_fields = {f.name for f in dataclasses.fields(gs.Recipe)}
    for stage in gs.STAGES:
        if stage.knob is not None:
            assert stage.knob in recipe_fields, f"{stage.name} knob {stage.knob!r} not a Recipe field"


def test_reference_recipe_reproduces_the_capstone_and_is_the_default():
    # REFERENCE = every knob at the capstone's sound value; new_game() with no args plays it.
    assert gs.REFERENCE == gs.Recipe()
    assert gs.new_game().recipe == gs.REFERENCE
    assert gs.new_game(REF_CARBON).recipe.carbon == REF_CARBON
