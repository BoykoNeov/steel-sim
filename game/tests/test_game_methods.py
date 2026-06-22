"""Slice 2 — methods & the era ramp (``game.md`` §6): the tech tree's acceptance bar.

Slice 1's bar was **losability** (a wrong knob flips the verdict). Slice 2's analogue is the **purity-control
ramp** (``steel-making.md`` §14 theme C / §15.2): each era must conquer *exactly* the tramp the history says
it did, so a dirty ore walks the player up the tech tree — and the modern reference must still reproduce the
sealed capstone golden run exactly (the game adds no physics). These tests pin the matrix, the progression,
and the honesty calls the era ramp deliberately makes (no hydrogen claim pre-modern; the basic open hearth /
BOF share Thomas' chemistry — their distinction is flavor; the bloomery is a named ceiling, not a played run).
"""
import pytest

from game import choices as ch
from game import presets as pr
from game import state as gs
from game import teach as tc
from steel import heat_state as hs
from steel import slag as sl
from steel.demo_capstone import REF_CARBON, FOIL_CARBON, run_chain


# --------------------------------------------------------------------------- #
# The golden run, preserved through the Slice-2 method API
# --------------------------------------------------------------------------- #
def test_modern_phosphoric_reference_is_the_capstone_golden_run():
    # The modern method on the phosphoric ore (the capstone's seeded backbone) with the reference recipe IS
    # the sealed chain — the new method/ore layer cannot have shifted the golden run.
    for carbon in (REF_CARBON, FOIL_CARBON):
        finished = gs.play_to_end(carbon, method=pr.MODERN, ore=pr.PHOSPHORIC_ORE).heat
        assert finished == run_chain(carbon).part


def test_default_new_game_is_modern_on_the_phosphoric_ore():
    # new_game() with no era/ore args defaults to the modern full chain on the phosphoric ore — so every
    # Slice-0/1 test (which never passes a method) keeps playing exactly the route it always did.
    state = gs.new_game()
    assert state.method is pr.MODERN and state.ore is pr.PHOSPHORIC_ORE


# --------------------------------------------------------------------------- #
# Phosphorus — the acid/basic slag lever (the headline)
# --------------------------------------------------------------------------- #
def test_acid_bessemer_cannot_dephosphorize_a_phosphoric_ore():
    # Acid Bessemer runs a dephos stage, but its acid slag (L_P≈1) barely moves the phosphorus → the part is
    # cold-short. The forced failure that needed Thomas to fix (and a clean ore to avoid).
    r = gs.final_readout(gs.play_to_end(method=pr.ACID_BESSEMER, ore=pr.PHOSPHORIC_ORE))
    assert not r["sound"]
    assert any("cold-short" in c["headline"] for c in r["consequences"])


def test_basic_slag_conquers_phosphorus():
    # Thomas' basic slag drops phosphorus below spec — no cold-short anymore (the 1879 fix). The heat is still
    # spoiled, but on SULFUR (no ladle yet), not phosphorus — the progression, one tramp at a time.
    r = gs.final_readout(gs.play_to_end(method=pr.THOMAS, ore=pr.PHOSPHORIC_ORE))
    assert not any("cold-short" in c["headline"] for c in r["consequences"])
    part = gs.play_to_end(method=pr.THOMAS, ore=pr.PHOSPHORIC_ORE).heat
    assert part.composition.P <= sl.MAX_PHOSPHORUS_PCT


def test_removes_phosphorus_reads_the_sealed_engine():
    # Method.removes_phosphorus is not a hardcoded flag — it reads slag.phosphorus_partition live. The acid
    # endpoint lands O(1), the basic one in the hundreds: the orders-of-magnitude jump that is the lesson.
    assert not pr.ACID_BESSEMER.removes_phosphorus
    assert pr.THOMAS.removes_phosphorus
    assert sl.phosphorus_partition(pr.ACID_BESSEMER.dephos_slag) < 10.0
    assert sl.phosphorus_partition(pr.THOMAS.dephos_slag) > 100.0


# --------------------------------------------------------------------------- #
# Sulfur — the ladle unlock (the last tramp)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", [pr.ACID_BESSEMER, pr.THOMAS, pr.OPEN_HEARTH, pr.BOF])
def test_pre_ladle_eras_leave_sulfur_over_spec(method):
    # No reducing ladle → tramp sulfur rides through over the cleanliness spec (the Mn ties it as MnS so it
    # does not red-short, but it is off-grade dirty). Sulfur waited for secondary metallurgy.
    part = gs.play_to_end(method=method, ore=pr.PHOSPHORIC_ORE).heat
    assert part.composition.S > sl.MAX_SULFUR_PCT


def test_only_the_modern_ladle_lands_a_sound_phosphoric_heat():
    # The full chain (basic dephos + reducing-ladle desulf + degas) is the only era that cleans the phosphoric
    # ore end to end — the top of the tech tree.
    sound = [m for m in pr.METHODS if gs.final_readout(gs.play_to_end(method=m, ore=pr.PHOSPHORIC_ORE))["sound"]]
    assert sound == [pr.MODERN]


# --------------------------------------------------------------------------- #
# The ore axis — clean ore is sound even in the oldest process
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", list(pr.METHODS))
def test_clean_ore_is_sound_in_every_era(method):
    # A non-phosphoric, low-sulfur ore is sound even in acid Bessemer — the historical reason the early
    # Bessemer trade fought over clean ore. The era only matters when the ore is dirty.
    r = gs.final_readout(gs.play_to_end(method=method, ore=pr.CLEAN_ORE))
    assert r["sound"], f"{method.name} should make sound steel from clean ore"


# --------------------------------------------------------------------------- #
# The honesty calls the era ramp deliberately makes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", [pr.ACID_BESSEMER, pr.THOMAS, pr.OPEN_HEARTH, pr.BOF])
def test_pre_modern_eras_make_no_hydrogen_claim(method):
    # The model introduces no charge hydrogen, so "no vacuum" cannot mean "leaves H in" — pre-modern eras
    # leave the hydrogen field unset (no flaking claim). The modern era fills it (the degas knob's domain).
    assert gs.play_to_end(method=method, ore=pr.PHOSPHORIC_ORE).heat.hydrogen_ppm is None
    assert gs.play_to_end(method=pr.MODERN, ore=pr.PHOSPHORIC_ORE).heat.hydrogen_ppm is not None


@pytest.mark.parametrize("twin", [pr.OPEN_HEARTH, pr.BOF])
def test_open_hearth_and_bof_share_thomas_chemistry(twin):
    # The honesty point: by this model's chemistry the basic open hearth and the BOF make the SAME heat as
    # Thomas (they conquered phosphorus the same way). Their distinction (scale, speed, low N) is flavor — so
    # the finished composition and defects are identical, and that equality is asserted, not hand-waved.
    a = gs.play_to_end(method=pr.THOMAS, ore=pr.PHOSPHORIC_ORE).heat
    b = gs.play_to_end(method=twin, ore=pr.PHOSPHORIC_ORE).heat
    assert a.composition == b.composition and a.defects == b.defects


def test_bloomery_is_named_as_a_ceiling_not_a_played_method():
    # The bloomery is the era-0 floor (a different product on a different walk, below the F1 crossover) — named
    # in prose, deliberately NOT a playable 4140 method (the named deferral, not a faked verdict).
    assert pr.BLOOMERY_NOTE and "bloomery" in pr.BLOOMERY_NOTE.lower()
    assert all("bloomery" not in m.name.lower() for m in pr.METHODS)


# --------------------------------------------------------------------------- #
# Label-correctness — the educational cards (verified numbers live, flavor labelled)
# --------------------------------------------------------------------------- #
def test_method_cards_quote_live_partition_numbers():
    # The phosphorus card quotes L_P read LIVE from the engine: the acid card a small value, the basic card a
    # large one. A baked constant would make them quote the same number — this discriminates against that.
    acid = tc.method_why_cards(pr.ACID_BESSEMER)[0].body
    basic = tc.method_why_cards(pr.THOMAS)[0].body
    assert f"{sl.phosphorus_partition(pr.ACID_BESSEMER.dephos_slag):.1f}" in acid
    assert f"{sl.phosphorus_partition(pr.THOMAS.dephos_slag):.0f}" in basic


def test_method_cards_split_verified_from_flavor():
    # Every era's cards: the P and S cards are verified (engine-cited); the era-feel card is flavor.
    for m in pr.METHODS:
        cards = tc.method_why_cards(m)
        verified = [c for c in cards if c.label == tc.VERIFIED]
        flavor = [c for c in cards if c.label == tc.FLAVOR]
        assert len(verified) == 2 and all(c.source != tc.FLAVOR_SOURCE for c in verified)
        assert flavor and all(c.source == tc.FLAVOR_SOURCE for c in flavor)


def test_open_hearth_card_states_the_same_as_thomas_honesty_in_flavor():
    # The "it makes the same heat as Thomas" admission must live in the FLAVOR card (it is a modelling
    # honesty, not an engine claim) — so a reader is told the chemical equality outright.
    flavor = next(c for c in tc.method_why_cards(pr.OPEN_HEARTH) if c.label == tc.FLAVOR)
    assert "thomas" in flavor.body.lower()


def test_timeline_is_the_era_ladder_oldest_first():
    rows = tc.timeline()
    assert [r["name"] for r in rows] == [m.name for m in pr.METHODS]
    assert rows == sorted(rows, key=lambda r: r["year"])


# --------------------------------------------------------------------------- #
# Knob gating — historical eras expose only the universal carbon blow
# --------------------------------------------------------------------------- #
def test_historical_eras_expose_only_the_carbon_blow():
    # In a historical era the era's technology is the decision; the rest runs fixed good practice. Only the
    # decarburize stage offers a knob (carbon), and it is the blow endpoint.
    for stage in ch.STAGE_DECISIONS:
        knobs = ch.stage_decisions(stage, pr.ACID_BESSEMER)
        assert knobs in ((), ("carbon",))
    assert ch.stage_decisions("decarburize", pr.ACID_BESSEMER) == ("carbon",)


def test_modern_era_exposes_the_full_gauntlet():
    # The modern era is unchanged — every Slice-1 knob is still offered.
    for stage, knobs in ch.STAGE_DECISIONS.items():
        assert ch.stage_decisions(stage, pr.MODERN) == knobs


# --------------------------------------------------------------------------- #
# The demo — compute + narrate (smoke; the matrix is the structured output)
# --------------------------------------------------------------------------- #
def test_demo_compute_covers_every_method_and_ore():
    from game import demo_game_methods as dm

    demo = dm.compute()
    assert len(demo.outcomes) == len(pr.METHODS) * len(pr.ORES)
    # the phosphoric-ore ramp: spoiled until the modern era, then sound (the tech tree, top to bottom)
    ramp = demo.for_ore(pr.PHOSPHORIC_ORE)
    assert [o.sound for o in ramp] == [m is pr.MODERN for m in pr.METHODS]


def test_demo_print_summary_runs(capsys):
    from game import demo_game_methods as dm

    dm.print_summary(dm.compute())
    out = capsys.readouterr().out
    assert "purity-control ramp" in out and "Acid Bessemer" in out
