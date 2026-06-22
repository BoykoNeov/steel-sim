"""``game.state`` — the stateful, multi-turn play surface (``game.md`` §3, the load-bearing new design).

The existing apps (``app.py``, ``app_making.py``, ``app_consequences.py``) are **stateless** what-if
panels: sliders in → readout out, nothing persists. A game is **stateful** — a live ``Heat`` evolving
across turns. Because :class:`~steel.heat_state.Heat` is a **frozen, append-only** dataclass (every
orchestrator step returns a *new* ``Heat`` with one :class:`~steel.heat_state.ProcessStep` appended), the
turn structure is clean and needs no new history machinery: **each turn = run one sealed stage on the
current ``Heat``, get a new ``Heat``, advance the cursor.** The provenance trail *is* the post-mortem,
already built — the game only drives the spine's existing one.

**Slice 1 — the gauntlet (``game.md`` §6, extended).** Slice 0 made the B2 capstone chain *playable* with
a single knob (the F2 blow endpoint); every other stage auto-ran a fixed recipe, so there was nothing else
to get wrong. Slice 1 makes **every stage a decision**: a :class:`Recipe` carries one knob per stage, each
field **defaulting to the capstone's reference value** (single-sourced from :mod:`steel.demo_capstone`).
A wrong choice **plants a latent flaw** in the live ``Heat`` (carbon off the window, oxygen the kill left
high, hydrogen the vacuum left in, sulfur the slag left, off-grade alloy) and the finished part is judged
by the **post-mortem** (:mod:`game.postmortem`) — the sealed consequence engines, run on the part, report
which defect each mistake became. You win by landing a sound, on-grade part; you lose by planting a defect.

**The golden-run invariant is preserved exactly.** The canonical ``Heat`` is built **only** from the eight
stage seams (the post-mortem reads the finished part, it never mutates the spine), and every ``Recipe``
field defaults to the reference value, so stepping the *reference* recipe reproduces
``demo_capstone.run_chain``'s sealed-engine verdict **exactly** — the golden-run test still pins that
equality, which *is* the proof the game adds no physics. ``play_to_end(c)`` is the one-knob Slice-0 view of
the same machine: ``Recipe(carbon=c)`` with every other knob at reference.

**Slice 2 — methods & the era ramp (``game.md`` §6).** The gauntlet plays one technology; Slice 2 layers the
**§15.2 method→engine map** on top: a :class:`~game.presets.Method` (the era — which dephosphorization slag
runs, whether the era has ladle desulfurization / vacuum degassing) and an :class:`~game.presets.Ore` (the
charge's tramp load) become the new top-level choices. The stage seams read the method for the era's refining
*chemistry* and the ore for the origin; the **purity-control ramp** is the difficulty curve — a phosphoric
ore is cold-short in acid Bessemer (acid slag, L_P≈1), phosphorus-fixed-but-still-dirty in Thomas (basic
slag, no ladle desulf), and sound only in the modern ladle era. Both default to the modern chain on the
phosphoric ore, so the golden-run equality is untouched.

Pure logic: no streamlit, no matplotlib (the ``app.py`` three-layer firewall). The always-green tests pin
the turn structure (one ``ProcessStep`` per turn, immutable), the golden-run equality, and — the Slice-1
acceptance bar — **losability**: for every claimed knob there is a wrong setting that flips the verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, TYPE_CHECKING

from steel import casting as cast
from steel import demo_capstone as dc
from steel import heat_state as hs
from steel import ladle as ld
from steel import refining as ref
from steel import slag as sl
from steel.heat_state import Heat, ProcessStep
from steel.sweep import evaluate

if TYPE_CHECKING:                                    # avoid a presets↔state import cycle at module load
    from .presets import Method, Ore


def _method_of(state: "GameState") -> "Method":
    """The state's method, defaulting to the modern full chain (lazy import avoids a presets↔state cycle).

    Slice 2 layers the era tech tree (:mod:`game.presets`) on the gauntlet: a method fixes the era's refining
    chemistry (which dephosphorization slag runs, whether the era has ladle desulfurization / vacuum
    degassing). A ``GameState`` built without one (back-compat, e.g. a hand-built state) plays the modern
    method — the same route Slices 0/1 always played.
    """
    if state.method is not None:
        return state.method
    from . import presets
    return presets.MODERN


# --------------------------------------------------------------------------- #
# 1. The recipe — one knob per stage, each defaulting to the capstone reference
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Recipe:
    """The player's choices for a whole heat — **one knob per stage**, defaults = the capstone reference.

    Every field defaults to the value :mod:`steel.demo_capstone` uses for its **sound** reference heat
    (``game.md`` §6), so :data:`REFERENCE` (= ``Recipe()``) reproduces ``run_chain`` exactly and the
    golden-run equality holds. A field set away from its default is a **wrong call** that plants a latent
    flaw the post-mortem surfaces:

    * ``carbon`` — the F2 blow endpoint (wt %). Off the 4140 window → off-grade; far below → a soft core.
    * ``dephosphorize`` — run the basic converter slag, or skip it (tramp phosphorus stays → cold-short).
    * ``deoxidizer`` — the kill metal, ``"Al"`` / ``"Si"`` / ``"Mn"`` (the F1 Ellingham strength hierarchy
      Al ≫ Si > Mn). The strong aluminium kill drops dissolved oxygen far below the C–O line; a weak Si/Mn
      kill cannot, leaving the bath at the carbon-set oxygen → gas porosity at the cast.
    * ``degas_p_H2`` — the vacuum depth (atm H₂). A shallow vacuum leaves hydrogen → flaking.
    * ``desulfurize`` — run the reducing ladle slag, or skip it (tramp sulfur stays over the cleanliness
      spec — the trim's manganese still ties it as MnS, so it does **not** red-short, but it is off-spec).
    * ``carbon_pickup`` — trim with high-carbon ferroalloys that carry carbon into the bath (→ off-grade).
    * ``cast_modulus`` — the billet section modulus (m). **Not a losable knob on this grade**: it sets the
      Chvorinov time only (segregation is ``fs``-based, judged on the centerline, not the nominal part the
      verdict follows), so casting is an honest pass-through, kept here for golden-run fidelity.
    * ``quench_medium`` / ``part_diameter`` — the quench severity and section; too mild / too thick → soft core.
    """

    carbon: float = dc.REF_CARBON
    dephosphorize: bool = True
    deoxidizer: str = "Al"
    degas_p_H2: float = dc.DEGAS_P_H2
    desulfurize: bool = True
    carbon_pickup: bool = False
    cast_modulus: float = dc.CAST_MODULUS
    quench_medium: str = dc.QUENCH_MEDIUM
    part_diameter: float = dc.PART_DIAMETER


#: The reference recipe — every knob at the capstone's sound value (``run_chain`` reproduces this).
REFERENCE = Recipe()


# --------------------------------------------------------------------------- #
# 2. The stages — each a sealed Heat → Heat seam reading the player's recipe
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Stage:
    """One turn of the chain: a sealed ``Heat`` → ``Heat`` seam plus its display name.

    ``run`` takes the current ``Heat`` and the :class:`GameState` (so each stage can read the player's
    :class:`Recipe`) and returns the next ``Heat``. ``knob`` names the :class:`Recipe` field this stage
    consumes (``None`` for none); ``blurb`` is a one-line "what this step does" for the UI (prose only — the
    *numbers* come from the ``Heat`` the seam returns).
    """

    name: str
    run: Callable[[Heat, "GameState"], Heat]
    blurb: str
    knob: str | None = None


def _skipped(heat: Heat, name: str, why: str) -> Heat:
    """A deliberately-omitted stage: append one ``ProcessStep`` that changes nothing but records the choice.

    Keeps the **one ``ProcessStep`` per turn** invariant true even when the player skips a refining step —
    the trail then *tells the story* (the omission is a node, not a gap), and the latent flaw it leaves
    rides on to the post-mortem unchanged.
    """
    step = ProcessStep(name, why, in_spec=None, flags_added=())
    return heat.evolve(step)


def _decarburize(heat: Heat, state: "GameState") -> Heat:
    return ref.decarburize(heat, state.recipe.carbon)            # knob: the player's blow endpoint


def _dephosphorize(heat: Heat, state: "GameState") -> Heat:
    # The era's slag runs (Slice 2): an acid Bessemer slag lands L_P≈1 (phosphorus stays — you watch it
    # fail), a basic Thomas/BOF slag L_P in the hundreds (phosphorus conquered). The player can additionally
    # SKIP the stage in the modern gauntlet. Defaults to the modern basic slag (= the golden-run path).
    if not state.recipe.dephosphorize:
        return _skipped(heat, "dephosphorize", "skipped — no basic slag, tramp phosphorus stays in the bath")
    return sl.dephosphorize(heat, _method_of(state).dephos_slag)


def _deoxidize(heat: Heat, state: "GameState") -> Heat:
    # knob: the kill metal (Al strong / Si, Mn weak — the F1 Ellingham hierarchy); the level is the recipe's.
    return ref.deoxidize(heat, state.recipe.deoxidizer, dc.DEOX_LEVEL)


def _degas(heat: Heat, state: "GameState") -> Heat:
    # Vacuum degassing is a modern (secondary-metallurgy) capability (Slice 2): pre-modern eras have no
    # vacuum, and since this model introduces no charge hydrogen there is nothing to strip, so they make no
    # flaking claim (the field stays unset). The modern era reads the player's vacuum-depth knob.
    if not _method_of(state).can_degas:
        return _skipped(heat, "degas", "no vacuum in this era — a 20th-century step (no hydrogen claim made)")
    return ref.degas(heat, p_H2=state.recipe.degas_p_H2)         # knob: the vacuum depth


def _desulfurize(heat: Heat, state: "GameState") -> Heat:
    # Desulfurization is a reducing LADLE step (the Slice-2 sulfur unlock): pre-ladle eras have no such
    # stage, so tramp sulfur rides through (off-grade dirty, or red-short if Mn can't tie it as MnS). In the
    # modern era the player can additionally skip it (the gauntlet knob).
    if not _method_of(state).can_desulfurize:
        return _skipped(heat, "desulfurize", "no ladle desulfurization in this era — tramp sulfur stays in")
    if not state.recipe.desulfurize:
        return _skipped(heat, "desulfurize", "skipped — no reducing slag, tramp sulfur stays in the bath")
    return sl.desulfurize(heat, dc.LADLE_SLAG)


def _trim(heat: Heat, state: "GameState") -> Heat:
    # knob: high-carbon ferroalloys carry carbon into the bath (apply_carbon_pickup); reference is a clean trim.
    return ld.trim_to_grade(heat, dc.GRADE, apply_carbon_pickup=state.recipe.carbon_pickup)


def _cast(heat: Heat, state: "GameState") -> Heat:
    # The lone front-end seam that takes a Steel; cast_billet_onto re-bases the nominal section onto the
    # live Heat so the trail stays continuous (the promoted public seam — game.md §3 / casting).
    return cast.cast_billet_onto(heat, modulus=state.recipe.cast_modulus).nominal_heat


def _heat_treat(heat: Heat, state: "GameState") -> Heat:
    return hs.heat_treat(heat, medium=state.recipe.quench_medium, diameter=state.recipe.part_diameter)


# The chain AFTER the hot-metal charge (which is the origin, created by :func:`new_game`). Every stage reads
# the player's recipe; the order is the canonical refining order the capstone documents.
STAGES: tuple[Stage, ...] = (
    Stage("decarburize", _decarburize,
          "Blow carbon out of the bath to your endpoint — too far over-blows the heat off grade.",
          knob="carbon"),
    Stage("dephosphorize", _dephosphorize,
          "A basic converter slag pulls tramp phosphorus out — oxidizing, while the oxygen is high.",
          knob="dephosphorize"),
    Stage("deoxidize", _deoxidize,
          "The kill metal drops the dissolved oxygen the blow raised — a weak one (Si, Mn) can't.",
          knob="deoxidizer"),
    Stage("degas", _degas,
          "A deep vacuum strips hydrogen below the flaking limit — a shallow one leaves it in.",
          knob="degas_p_H2"),
    Stage("desulfurize", _desulfurize,
          "A reducing ladle slag pulls tramp sulfur out — reading the now-low oxygen the kill left.",
          knob="desulfurize"),
    Stage("trim", _trim,
          "Ferroalloy additions bring the lean heat up to the 4140 window — high-carbon alloys carry carbon.",
          knob="carbon_pickup"),
    Stage("cast", _cast,
          "Chvorinov solidification + Scheil centerline segregation — the segregation band the back end "
          "inherits (an honest pass-through: no pass/fail lever on this grade).",
          knob=None),
    Stage("heat-treat", _heat_treat,
          "The oil quench the whole repo judges parts with: does the section through-harden?",
          knob="quench_medium"),
)


# --------------------------------------------------------------------------- #
# 3. The game state — the live Heat + the cursor + the player's recipe + the toggle
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GameState:
    """The persistable game state (what lives in ``st.session_state``; ``game.md`` §3.1).

    ``heat`` the **live** ``Heat`` — the current node of the immutable, append-only chain. ``stage`` the
    cursor: the index into :data:`STAGES` of the **next** stage to run (``0``..``len(STAGES)``;
    ``len(STAGES)`` = the part is finished). ``recipe`` the player's choices, one knob per stage (Slice 1),
    fixed at the start of the heat. ``educational`` the opt-in education toggle (``game.md`` §5). Frozen,
    like ``Heat`` — :func:`advance` returns a *new* ``GameState``, never mutates.
    """

    heat: Heat
    recipe: Recipe
    stage: int = 0
    educational: bool = False
    method: "Method | None" = None       # the era/technology (Slice 2); None → the modern full chain
    ore: "Ore | None" = None             # the charge feedstock (Slice 2); None → the phosphoric ore

    @property
    def carbon_target(self) -> float:
        """The F2 blow endpoint (the Slice-0 one-knob view of the recipe) — back-compat convenience."""
        return self.recipe.carbon

    @property
    def done(self) -> bool:
        """``True`` when every stage has run — the part is finished and ready to judge."""
        return self.stage >= len(STAGES)

    @property
    def next_stage(self) -> Stage | None:
        """The stage the next :func:`advance` will run, or ``None`` when the heat is finished."""
        return None if self.done else STAGES[self.stage]


# --------------------------------------------------------------------------- #
# 4. The turn structure — new_game / advance / play_to_end
# --------------------------------------------------------------------------- #
def new_game(carbon_target: float | None = None, *, recipe: Recipe | None = None,
             method: "Method | None" = None, ore: "Ore | None" = None,
             educational: bool = False) -> GameState:
    """Start a heat: the hot-metal charge origin + the player's recipe, cursor at the first stage.

    Pass a full :class:`Recipe` (the Slice-1 gauntlet), or just a ``carbon_target`` (the Slice-0 one-knob
    view — every other knob takes its reference value). Slice 2 adds the era ``method`` (the technology — see
    :mod:`game.presets`) and the ``ore`` (the charge's tramp load); both default to the modern full chain on
    the phosphoric ore, so ``new_game()`` is the *same* origin ``run_chain`` builds and the golden-run
    equality holds from step one. The origin is :func:`steel.refining.from_hot_metal` on the chosen ore's
    alloy-lean backbone (single-sourced from :mod:`steel.demo_capstone`). A "restart" is just calling this
    again.
    """
    from . import presets
    method = method if method is not None else presets.MODERN
    ore = ore if ore is not None else presets.PHOSPHORIC_ORE
    if recipe is None:
        recipe = REFERENCE if carbon_target is None else replace(REFERENCE, carbon=float(carbon_target))
    charge = ref.from_hot_metal(ore.backbone, charge_carbon=dc.CHARGE_CARBON)
    return GameState(heat=charge, recipe=recipe, stage=0, method=method, ore=ore, educational=educational)


def advance(state: GameState) -> GameState:
    """Run the **next** sealed stage on the live ``Heat`` and return a new ``GameState`` (one turn).

    The whole turn structure: run ``STAGES[stage]`` on ``state.heat`` (reading ``state.recipe``), advance
    the cursor by one. Because the seam returns a new ``Heat`` with exactly one ``ProcessStep`` appended,
    the trail grows by **one** per turn — the state-transition test pins that. Raises :class:`RuntimeError`
    if the heat is already finished (the UI checks ``state.done`` first).
    """
    if state.done:
        raise RuntimeError("the heat is finished — no stage left to advance (check state.done first)")
    stage = STAGES[state.stage]
    return replace(state, heat=stage.run(state.heat, state), stage=state.stage + 1)


def play_to_end(carbon_target: float | None = None, *, recipe: Recipe | None = None,
                method: "Method | None" = None, ore: "Ore | None" = None,
                educational: bool = False) -> GameState:
    """Run a whole heat to the finished part — the headless driver the golden-run test and the demo use."""
    state = new_game(carbon_target, recipe=recipe, method=method, ore=ore, educational=educational)
    while not state.done:
        state = advance(state)
    return state


# --------------------------------------------------------------------------- #
# 5. The verdict readout — read the finished part off the Heat (pure formatting)
# --------------------------------------------------------------------------- #
def final_readout(state: GameState) -> dict:
    """The finished-part verdict, read off the live ``Heat`` — sound vs spoiled, on-grade vs off-grade.

    Reads the back-end physics (``sweep.evaluate`` on the part composition, the *same* read ``run_chain``
    does), the flags the chain itself raised (off-grade, soft-core, and the refining risk flags), and the
    **gauntlet post-mortem** (:func:`game.postmortem.post_mortem`) — the sealed consequence engines run on
    the finished part, reporting which latent flaw each wrong choice became. The post-mortem **does not
    mutate** the canonical ``Heat`` (golden-run stays exact); it is a separate read. The verdict is
    **emergent, not scripted**. All formatting here, so the UI only forwards strings (+ the flags). Raises
    if the heat is not finished (call after :attr:`GameState.done`).
    """
    from . import postmortem as pm

    if not state.done:
        raise RuntimeError("the heat is not finished yet — advance to the end before reading the verdict")
    part = state.heat
    o = evaluate(part.as_steel(), medium=state.recipe.quench_medium, diameter=state.recipe.part_diameter)
    soft = part.has_defect(hs.SOFT_CORE)
    off_grade = part.has_defect(ld.OFF_GRADE)
    spec = hs.MIN_MARTENSITE_SPEC

    consequences = pm.post_mortem(part, recipe=state.recipe)     # the manifested defects, stage by stage
    spoiled = bool(consequences) or not part.is_clean
    sound = not spoiled

    if sound:
        verdict = (f"SOUND part — {o.result.martensite:.0%} martensite (clears the {spec:.0%} spec), on "
                   f"grade, every spec cleared end to end.")
    else:
        flaws = ", ".join(c.headline for c in consequences) if consequences else "off spec"
        verdict = (f"SPOILED — {flaws}. "
                   f"{o.result.martensite:.0%} martensite, {o.HV:.0f} HV. "
                   f"A wrong call upstream propagated to the finished part.")

    return {
        "sound": sound,
        "soft_core": soft,
        "off_grade": off_grade,
        "martensite": float(o.result.martensite),
        "HV": float(o.HV),
        "spec": float(spec),
        "carbon": float(part.composition.C),
        "label": part.label(),
        "martensite_str": f"{o.result.martensite:.0%} martensite, {o.HV:.0f} HV",
        "consequences": [c.as_dict() for c in consequences],
        "verdict": verdict,
        "trail": [
            {
                "name": s.name,
                "summary": s.summary,
                "mark": "·" if s.in_spec is None else ("✓" if s.in_spec else "✗"),
            }
            for s in part.history
        ],
    }
