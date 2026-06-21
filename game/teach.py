"""``game.teach`` — opt-in educational content (``game.md`` §5), the why-cards on Slice 0's one knob.

The user's first-class requirement: at the start the player can switch on an **educational mode** with
more help and explanation. Slice 0 lands **tier 1** — *why-cards on the one knob* (``game.md`` §5.2): for
the F2 decarb blow, what the step does, what over- and under-shoot mean, the validated target named.

The educational-mode firewall line (``game.md`` §5.3, sharpened by the advisor) — two rules keep teaching
text from becoming a backdoor for un-sourced claims:

1. **Every number a card quotes is read LIVE from the engine at runtime, never hardcoded.** A why-card
   says "the dissolved oxygen here is *{value from* :func:`steel.refining.equilibrium_oxygen` *at the
   current endpoint}*," not a baked-in string. (The label-correctness test drives two endpoints and
   asserts the quoted number *moves* — a baked constant would fail.)
2. **Every physics claim cites the SAME source the engine cites.** A claim with no engine behind it is
   **flavor** and wears the "plausible, not validated" label like any other feel-tuned content (here, the
   blow *trajectory shape*).

Prose may live here (text is content, not physics); the *numbers* never do. No streamlit, no matplotlib.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import knobs as kn

# The two label tiers (the verified-vs-flavor contract, ``game.md`` §5.3 / ``steel-making.md`` §15.5).
VERIFIED: str = "verified"
FLAVOR: str = "flavor"
FLAVOR_SOURCE: str = "plausible, not validated"


@dataclass(frozen=True)
class WhyCard:
    """One educational why-card: prose + the verified/flavor tag + the source it cites.

    ``label`` is :data:`VERIFIED` (the body quotes an engine number, ``source`` names the engine function)
    or :data:`FLAVOR` (feel-tuned, ``source`` is :data:`FLAVOR_SOURCE`). The UI renders the tag as a chip,
    so a player sees *which* numbers are grounded and which are game feel.
    """

    title: str
    body: str
    label: str
    source: str


def blow_why_cards(carbon_target: float) -> list[WhyCard]:
    """The tier-1 why-cards for the decarb blow at the player's ``carbon_target`` — numbers read **live**.

    Three cards: what the blow does (verified — the C–O oxygen reading at this endpoint, the cited grade
    window), why over-blowing hurts (verified — the C–O product coupling), and the trajectory feel (flavor
    — the first-order shape is not a validated rate). Every quoted number is computed here from
    :mod:`game.knobs` (which is a pass-through to the F2 engine), so the cards track the current endpoint.
    """
    pos = kn.endpoint_position(carbon_target)
    lo, hi = pos.window
    product = kn.carbon_oxygen_product()

    zone_phrase = {
        "on-aim": f"on aim — inside the {lo:.2f}–{hi:.2f} % window",
        "over-blow": f"OVER-BLOWN — below the {lo:.2f} % floor (off-grade low, and the bath over-oxidized)",
        "under-blow": f"under-blown — above the {hi:.2f} % ceiling (off-grade high, carbon left in)",
    }[pos.zone]

    return [
        WhyCard(
            "What the decarb blow does",
            f"The blow burns carbon out of the carbon-saturated bath. You are aiming for the 4140 carbon "
            f"window {lo:.2f}–{hi:.2f} % (grade aim {pos.aim:.2f} %). Your {pos.carbon:.2f} %C endpoint is "
            f"{zone_phrase}, sitting in C–O equilibrium at {pos.oxygen_ppm:.0f} ppm dissolved oxygen.",
            label=VERIFIED,
            source="refining.equilibrium_oxygen / ladle.GRADE_WINDOWS",
        ),
        WhyCard(
            "Why over-blowing hurts",
            f"Carbon and oxygen are coupled — [%C]·[%O] ≈ {product:.4f} at tap temperature — so driving "
            f"carbon below the window drives dissolved oxygen UP (an over-oxidized bath) and lands the heat "
            f"off-grade on the low side. That carbon shortfall is what soft-cores the part at the quench, "
            f"two stages later. Stopping short instead leaves carbon high (off-grade high).",
            label=VERIFIED,
            source="refining.carbon_oxygen_product",
        ),
        WhyCard(
            "Reading the trajectory",
            "Carbon falls fast at the start of the blow, then slows as it nears your endpoint. That "
            "first-order *shape* is game feel — a plausible relaxation, not a validated rate (real decarb "
            "kinetics are the transport tar-pit the project keeps as flavor). Only the shape is feel; both "
            "ends it runs between — the charge carbon and your endpoint — are real.",
            label=FLAVOR,
            source=FLAVOR_SOURCE,
        ),
    ]


def intro_text(educational: bool) -> str:
    """The startup blurb — one line, longer when educational mode is on (the toggle's first visible effect)."""
    base = (
        "Make one heat of 4140 the whole way — set the decarb blow endpoint, then run the sealed chain "
        "and see whether the part comes out sound or soft-cored."
    )
    if not educational:
        return base
    return (
        base + " **Educational mode is on:** each knob carries why-cards explaining what it does, what "
        "over- and under-shoot mean, and the validated target — every number read live from the engine, "
        "every physics claim citing the model's own source (game-feel bits are labelled “plausible”)."
    )
