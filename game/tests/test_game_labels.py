"""Label-correctness + educational-numbers-live (``game.md`` §5.3/§8) — teaching text cannot smuggle claims.

Two rules keep educational prose honest (``game.md`` §5.3): every number a why-card quotes is read **live**
from the engine (never hardcoded), and every physics claim cites the **same** source the engine cites
(else it is flavor, labelled "plausible"). The discriminating test (per the advisor) is *not* "the card
returns a string": it drives **two** different endpoints and asserts the quoted oxygen number **moves**,
and that it matches the live engine value — a baked-in constant would fail both.
"""
from game import knobs as kn
from game import teach as tc
from steel import refining as ref


def test_quoted_oxygen_moves_with_the_endpoint():
    # Drive two endpoints; the verified "what the blow does" card must quote a DIFFERENT oxygen number
    # (a baked constant would not move). This is the catch for a hardcoded teaching number.
    low_blow = tc.blow_why_cards(0.40)[0].body
    high_blow = tc.blow_why_cards(0.25)[0].body
    assert low_blow != high_blow, "the why-card did not change with the endpoint — a baked-in number?"


def test_quoted_oxygen_matches_the_live_engine_value():
    # The quoted ppm must be exactly the refining engine's reading at that endpoint (read live, not stored).
    for carbon in (0.40, 0.30, 0.25):
        card = tc.blow_why_cards(carbon)[0]
        expected = f"{ref.equilibrium_oxygen(carbon):.0f} ppm dissolved oxygen"
        assert expected in card.body, f"C={carbon}: card does not quote the live engine oxygen ({expected!r})"


def test_verified_cards_cite_an_engine_flavor_card_is_labelled_plausible():
    cards = tc.blow_why_cards(0.40)
    verified = [c for c in cards if c.label == tc.VERIFIED]
    flavor = [c for c in cards if c.label == tc.FLAVOR]
    assert verified and flavor, "Slice 0 should carry both a verified and a flavor why-card"
    # Every verified card names a real steel engine in its source (refining / ladle), not a bare assertion.
    for c in verified:
        assert any(eng in c.source for eng in ("refining", "ladle")), c.source
    # The flavor card wears the "plausible, not validated" label (the feel-tuned trajectory shape).
    for c in flavor:
        assert c.source == tc.FLAVOR_SOURCE


def test_label_tag_matches_the_source_kind():
    # Tag/source consistency: a "verified" card cites an engine, a "flavor" card cites the plausible label —
    # never crossed (a verified card with the flavor source, or vice-versa, is a labelling bug).
    for c in tc.blow_why_cards(0.40):
        if c.label == tc.VERIFIED:
            assert c.source != tc.FLAVOR_SOURCE
        else:
            assert c.label == tc.FLAVOR and c.source == tc.FLAVOR_SOURCE


def test_intro_text_grows_only_when_educational():
    # The educational toggle's first visible effect: more text when on, the base blurb when off.
    off, on = tc.intro_text(False), tc.intro_text(True)
    assert on != off and off in on and "Educational mode" in on
