"""``game.teach`` — opt-in educational content (``game.md`` §5), the why-cards on Slice 0's one knob.

The user's first-class requirement: at the start the player can switch on an **educational mode** with
more help and explanation. Slice 0 lands **tier 1** — *why-cards on the one knob* (``game.md`` §5.2): for
the F2 decarb blow, what the step does, what over- and under-shoot mean, the validated target named. Slice 1
grows a why-card per gauntlet knob (:func:`knob_why_cards`); **Slice 2** adds **tier 3** — per-era cards
(:func:`method_why_cards`) and the purity-ramp :func:`timeline`, teaching why each historical method conquered
the tramp it did (the §14 history surface, the §15.2 method map).

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

from steel import heat_state as hs
from steel import hydrogen_flaking as hf
from steel import slag as sl

from . import knobs as kn
from . import presets as pr

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


def knob_why_cards(knob: str, *, carbon_target: float | None = None) -> list[WhyCard]:
    """The tier-1 why-cards for a stage's knob — what the decision does and what a wrong call plants.

    The carbon blow delegates to :func:`blow_why_cards` (the τ-curve, numbers moving with the slider). Every
    other knob gets a **verified** card: it names the engine's own spec/threshold (read live from the model
    constant, so the quoted number tracks the engine, never a baked string) and the defect a wrong choice
    becomes. The desulfurization card is the honest one — it states the manganese-tie masking outright (the
    sulfur stays over spec, but does not red-short), turning the gauntlet's subtlest physics into the lesson.
    """
    if knob == "carbon":
        return blow_why_cards(carbon_target if carbon_target is not None else kn.grade_carbon_aim())

    lo, hi = kn.grade_carbon_window()
    product = kn.carbon_oxygen_product()
    cards = {
        "dephosphorize": WhyCard(
            "Why dephosphorize",
            f"Tramp phosphorus must come below {sl.MAX_PHOSPHORUS_PCT:.3f} %. A basic, oxidizing converter "
            f"slag pulls it out while the dissolved oxygen is still high (the right order). Skip it and the "
            f"phosphorus rides on — it raises the ductile-to-brittle transition over service temperature, "
            f"so the finished part is cold-short (it cracks cold).",
            VERIFIED, "slag.MAX_PHOSPHORUS_PCT / grain Pickering DBTT"),
        "deoxidizer": WhyCard(
            "Why the kill metal matters",
            f"Aluminium is a far stronger deoxidizer than silicon or manganese — the F1 Ellingham order "
            f"Al ≫ Si > Mn. A strong Al kill drops dissolved oxygen far below the carbon–oxygen line "
            f"([%C]·[%O] ≈ {product:.4f} at tap); a weak Si or Mn kill cannot, so at the cast the bath is "
            f"still over the CO product and the casting blows gas-porosity holes.",
            VERIFIED, "refining.DEOXIDIZERS / gas_porosity"),
        "degas_p_H2": WhyCard(
            "Why degas",
            f"Dissolved hydrogen must be vacuum-stripped below {hf.CRITICAL_FLAKING_H_PPM:.0f} ppm. A deep "
            f"vacuum does it; a shallow one leaves hydrogen in, and as the section cools the trapped hydrogen "
            f"precipitates into internal hairline cracks — flakes.",
            VERIFIED, "hydrogen_flaking.CRITICAL_FLAKING_H_PPM / Sieverts"),
        "desulfurize": WhyCard(
            "Why desulfurize (and the manganese catch)",
            f"Tramp sulfur must come below {sl.MAX_SULFUR_PCT:.3f} %. A reducing ladle slag pulls it out, "
            f"reading the now-low oxygen the kill left. Skip it and the sulfur stays — but here is the catch: "
            f"the trim's manganese ties it up as high-melting MnS, so the heat does NOT red-short at this "
            f"level. It is still over the cleanliness spec, though — off-grade dirty.",
            VERIFIED, "slag.MAX_SULFUR_PCT / hot_work Mushet Mn:S"),
        "carbon_pickup": WhyCard(
            "Why the ferroalloy carbon matters",
            f"High-carbon ferroalloys (FeMn, FeCr at 6–8 %C) carry carbon into the bath as they dissolve. "
            f"On a heat already blown to the 4140 aim, that pickup pushes carbon over the {hi:.2f} % grade "
            f"ceiling — off-grade, and over-hard. Low-carbon ferroalloys hit the alloy window cleanly.",
            VERIFIED, "ladle.carbon_pickup_pct / GRADE_WINDOWS"),
        "quench_medium": WhyCard(
            "Why the quench and section matter",
            f"The section has to through-harden to at least {hs.MIN_MARTENSITE_SPEC:.0%} martensite. Too mild "
            f"a quench (air) or too thick a bar cools the core below the critical rate, so it transforms to "
            f"softer products — a soft core under a hard case. Oil at the reference section clears the spec.",
            VERIFIED, "sweep.evaluate / heat_state.MIN_MARTENSITE_SPEC"),
    }
    cards["part_diameter"] = cards["quench_medium"]               # the heat-treat pair share one why-card
    return [cards[knob]] if knob in cards else []


def method_why_cards(method: "pr.Method") -> list[WhyCard]:
    """Tier-3 educational cards for an era/method (``game.md`` §6 Slice 2) — the purity-ramp physics, live.

    Two **verified** cards — the phosphorus slag lever and the sulfur capability — each reading the sealed
    slag engine *live* (so a baked constant would fail the label test), plus one **flavor** card for the era's
    period detail / speed / scale (labelled "plausible, not validated"). Together they teach why each era
    conquered the tramp it did: phosphorus with the basic slag (Thomas), sulfur with the reducing ladle.
    """
    Lp = sl.phosphorus_partition(method.dephos_slag)
    cards: list[WhyCard] = []

    if method.removes_phosphorus:
        p_body = (
            f"This era runs a **basic** dephosphorization slag ({method.dephos_slag.label()}, "
            f"B = {method.dephos_slag.basicity:.1f}): the lime fixes phosphorus as a stable phosphate, so "
            f"L_P ≈ {Lp:.0f} — phosphorus partitions hundreds-to-one into the slag, taking it below the "
            f"{sl.MAX_PHOSPHORUS_PCT:.3f} % spec. Phosphorus conquered (Thomas' 1879 fix)."
        )
    else:
        p_body = (
            f"This era's slag is **acid** ({method.dephos_slag.label()}, B = {method.dephos_slag.basicity:.1f}): "
            f"oxidizing, but lime-poor, so it cannot fix the phosphate — L_P ≈ {Lp:.1f}, barely one-to-one. "
            f"Tramp phosphorus stays in the steel and the part comes out cold-short. This is exactly why acid "
            f"Bessemer needed a non-phosphoric ore — and why Thomas' basic lining changed history."
        )
    cards.append(WhyCard("Phosphorus — the slag", p_body, VERIFIED, "slag.phosphorus_partition (Healy 1970)"))

    if method.can_desulfurize:
        s_body = (
            f"This era has secondary metallurgy: a **reducing ladle** slag on the killed (low-oxygen) bath "
            f"pulls sulfur below the {sl.MAX_SULFUR_PCT:.3f} % spec. Desulfurization is a *reducing* partition "
            f"— it needs the low oxygen the kill leaves, which is why it is a ladle step, not a converter one."
        )
    else:
        s_body = (
            f"This era has no reducing ladle step, so tramp sulfur rides through. If the manganese can tie it "
            f"as high-melting MnS it does not red-short, but it stays over the {sl.MAX_SULFUR_PCT:.3f} % "
            f"cleanliness spec — off-grade dirty. Sulfur was the last tramp conquered; it waited for the ladle."
        )
    cards.append(WhyCard("Sulfur — the ladle", s_body, VERIFIED, "slag.sulfur_partition / slag.MAX_SULFUR_PCT"))

    if method.flavor:
        cards.append(WhyCard("The era's feel", "; ".join(method.flavor) + ".", FLAVOR, FLAVOR_SOURCE))
    return cards


def timeline() -> list[dict]:
    """The era ladder for the educational timeline (the §14 purity ramp) — what each era newly conquered.

    Prose, drawn from :data:`game.presets.METHODS` (oldest → newest); the bloomery floor is named separately
    (:data:`game.presets.BLOOMERY_NOTE`) since it is not a playable 4140 route. The UI renders this as the
    "history is the difficulty curve" panel.
    """
    return [{"name": m.name, "year": m.year, "era": m.era, "conquers": m.conquers} for m in pr.METHODS]


def intro_text(educational: bool) -> str:
    """The startup blurb — one line, longer when educational mode is on (the toggle's first visible effect)."""
    base = (
        "Make one heat of 4140 the whole way — every stage is a decision (blow endpoint, slags, kill metal, "
        "vacuum, ferroalloys, quench). Take every recommendation and the part comes out sound; one wrong "
        "call plants a flaw — porosity, flaking, cold-short, off-grade — that the finished part is judged on."
    )
    if not educational:
        return base
    return (
        base + " **Educational mode is on:** each decision carries a why-card explaining what it does and "
        "the defect a wrong call becomes — every number read live from the engine, every physics claim "
        "citing the model's own source (game-feel bits are labelled “plausible”)."
    )
