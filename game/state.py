"""``game.state`` — the stateful, multi-turn play surface (``game.md`` §3, the load-bearing new design).

The existing apps (``app.py``, ``app_making.py``, ``app_consequences.py``) are **stateless** what-if
panels: sliders in → readout out, nothing persists. A game is **stateful** — a live ``Heat`` evolving
across turns. Because :class:`~steel.heat_state.Heat` is a **frozen, append-only** dataclass (every
orchestrator step returns a *new* ``Heat`` with one :class:`~steel.heat_state.ProcessStep` appended), the
turn structure is clean and needs no new history machinery: **each turn = run one sealed stage on the
current ``Heat``, get a new ``Heat``, advance the cursor.** The provenance trail *is* the post-mortem,
already built — the game only drives the spine's existing one.

Slice 0 (``game.md`` §6) makes the **B2 capstone chain playable**: the capstone's 4140 route, the chain
auto-running every stage *except* the one player knob — the F2 decarb blow endpoint (:mod:`game.knobs`,
value-selection on the C–O τ-curve). The recipe is **single-sourced from** :mod:`steel.demo_capstone`
(``LEAN_BACKBONE``, the slag/kill/cast constants), so stepping this chain to completion reproduces
``demo_capstone.run_chain``'s sealed-engine verdict **exactly** — the golden-run test pins that equality,
which *is* the proof the game adds no physics. The lone seam that takes a ``Steel`` (casting) threads
through the promoted :func:`steel.casting.cast_billet_onto`, so the whole chain is one continuous ``Heat``.

Pure logic: no streamlit, no matplotlib (the ``app.py`` three-layer firewall). The always-green tests pin
the turn structure (one ``ProcessStep`` per turn, immutable) and the golden-run equality.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from steel import casting as cast
from steel import demo_capstone as dc
from steel import heat_state as hs
from steel import ladle as ld
from steel import refining as ref
from steel import slag as sl
from steel.heat_state import Heat
from steel.sweep import evaluate


# --------------------------------------------------------------------------- #
# 1. The stages — each a sealed Heat → Heat seam; only the blow reads a player value
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Stage:
    """One turn of the chain: a sealed ``Heat`` → ``Heat`` seam plus its display name.

    ``run`` takes the current ``Heat`` and the :class:`GameState` (so the one knob stage can read
    ``state.carbon_target``) and returns the next ``Heat``. ``is_knob`` marks the single stage that
    consumes a player choice (the F2 blow); all others auto-run a fixed-recipe seam. ``blurb`` is a
    one-line "what this step does" for the UI (prose only — the *numbers* come from the ``Heat`` the seam
    returns).
    """

    name: str
    run: Callable[[Heat, "GameState"], Heat]
    blurb: str
    is_knob: bool = False


def _decarburize(heat: Heat, state: "GameState") -> Heat:
    return ref.decarburize(heat, state.carbon_target)            # THE one knob: the player's blow endpoint


def _dephosphorize(heat: Heat, state: "GameState") -> Heat:
    return sl.dephosphorize(heat, dc.CONVERTER_SLAG)


def _deoxidize(heat: Heat, state: "GameState") -> Heat:
    return ref.deoxidize(heat, "Al", dc.DEOX_LEVEL)


def _degas(heat: Heat, state: "GameState") -> Heat:
    return ref.degas(heat, p_H2=dc.DEGAS_P_H2)


def _desulfurize(heat: Heat, state: "GameState") -> Heat:
    return sl.desulfurize(heat, dc.LADLE_SLAG)


def _trim(heat: Heat, state: "GameState") -> Heat:
    return ld.trim_to_grade(heat, dc.GRADE)


def _cast(heat: Heat, state: "GameState") -> Heat:
    # The lone front-end seam that takes a Steel; cast_billet_onto re-bases the nominal section onto the
    # live Heat so the trail stays continuous (the promoted public seam — game.md §3 / casting).
    return cast.cast_billet_onto(heat, modulus=dc.CAST_MODULUS).nominal_heat


def _heat_treat(heat: Heat, state: "GameState") -> Heat:
    return hs.heat_treat(heat, medium=dc.QUENCH_MEDIUM, diameter=dc.PART_DIAMETER)


# The chain AFTER the hot-metal charge (which is the origin, created by :func:`new_game`). The decarb blow
# is the one knob; the rest auto-run. The order is the canonical refining order the capstone documents.
STAGES: tuple[Stage, ...] = (
    Stage("decarburize", _decarburize,
          "Blow carbon out of the bath to your endpoint — the one knob you set.", is_knob=True),
    Stage("dephosphorize", _dephosphorize,
          "A basic converter slag pulls tramp phosphorus out — oxidizing, while the oxygen is high."),
    Stage("deoxidize", _deoxidize,
          "An aluminium kill drops the dissolved oxygen the blow raised, booking alumina inclusions."),
    Stage("degas", _degas,
          "A deep vacuum strips hydrogen below the flaking limit (and reports nitrogen)."),
    Stage("desulfurize", _desulfurize,
          "A reducing ladle slag pulls tramp sulfur out — reading the now-low oxygen the kill left."),
    Stage("trim", _trim,
          "Ferroalloy additions bring the lean heat up to the 4140 alloy window."),
    Stage("cast", _cast,
          "Chvorinov solidification + Scheil centerline segregation — the billet is frozen."),
    Stage("heat-treat", _heat_treat,
          "The oil quench the whole repo judges parts with: does the section through-harden?"),
)


# --------------------------------------------------------------------------- #
# 2. The game state — the live Heat + the cursor + the one knob + the toggle
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GameState:
    """The persistable game state (what lives in ``st.session_state``; ``game.md`` §3.1).

    ``heat`` the **live** ``Heat`` — the current node of the immutable, append-only chain. ``stage`` the
    cursor: the index into :data:`STAGES` of the **next** stage to run (``0``..``len(STAGES)``;
    ``len(STAGES)`` = the part is finished). ``carbon_target`` the player's blow endpoint, the one knob,
    fixed at the start of the heat (Slice 0). ``educational`` the opt-in education toggle (``game.md`` §5).
    Frozen, like ``Heat`` — :func:`advance` returns a *new* ``GameState``, never mutates.
    """

    heat: Heat
    carbon_target: float
    stage: int = 0
    educational: bool = False

    @property
    def done(self) -> bool:
        """``True`` when every stage has run — the part is finished and ready to judge."""
        return self.stage >= len(STAGES)

    @property
    def next_stage(self) -> Stage | None:
        """The stage the next :func:`advance` will run, or ``None`` when the heat is finished."""
        return None if self.done else STAGES[self.stage]


# --------------------------------------------------------------------------- #
# 3. The turn structure — new_game / advance / play_to_end
# --------------------------------------------------------------------------- #
def new_game(carbon_target: float, *, educational: bool = False) -> GameState:
    """Start a heat: the hot-metal charge origin + the chosen blow endpoint, cursor at the first stage.

    The origin is :func:`steel.refining.from_hot_metal` on the capstone's seeded, alloy-lean backbone
    (single-sourced from :mod:`steel.demo_capstone`) — the *same* origin ``run_chain`` builds, so the
    golden-run equality holds from step one. A "restart" is just calling this again.
    """
    charge = ref.from_hot_metal(dc.LEAN_BACKBONE, charge_carbon=dc.CHARGE_CARBON)
    return GameState(heat=charge, carbon_target=float(carbon_target), stage=0, educational=educational)


def advance(state: GameState) -> GameState:
    """Run the **next** sealed stage on the live ``Heat`` and return a new ``GameState`` (one turn).

    The whole turn structure: run ``STAGES[stage]`` on ``state.heat`` (the decarb blow reads
    ``state.carbon_target``; the rest auto-run), advance the cursor by one. Because the seam returns a new
    ``Heat`` with exactly one ``ProcessStep`` appended, the trail grows by **one** per turn — the
    state-transition test pins that. Raises :class:`RuntimeError` if the heat is already finished (the UI
    checks ``state.done`` first).
    """
    if state.done:
        raise RuntimeError("the heat is finished — no stage left to advance (check state.done first)")
    stage = STAGES[state.stage]
    return replace(state, heat=stage.run(state.heat, state), stage=state.stage + 1)


def play_to_end(carbon_target: float, *, educational: bool = False) -> GameState:
    """Run a whole heat to the finished part — the headless driver the golden-run test and the demo use."""
    state = new_game(carbon_target, educational=educational)
    while not state.done:
        state = advance(state)
    return state


# --------------------------------------------------------------------------- #
# 4. The verdict readout — read the finished part off the Heat (pure formatting)
# --------------------------------------------------------------------------- #
def final_readout(state: GameState) -> dict:
    """The finished-part verdict, read off the live ``Heat`` — sound vs soft-core, on-grade vs off-grade.

    Reads the back-end physics (``sweep.evaluate`` on the part composition, the *same* read
    ``run_chain`` does) and the flags the chain raised. The verdict is **emergent, not scripted**: the
    soft core is the martensite fraction crossing :data:`steel.heat_state.MIN_MARTENSITE_SPEC`, reached
    through the player's blow choice. All formatting here, so the UI only forwards strings (+ the flags).
    Raises if the heat is not finished (call after :attr:`GameState.done`).
    """
    if not state.done:
        raise RuntimeError("the heat is not finished yet — advance to the end before reading the verdict")
    part = state.heat
    o = evaluate(part.as_steel(), medium=dc.QUENCH_MEDIUM, diameter=dc.PART_DIAMETER)
    soft = part.has_defect(hs.SOFT_CORE)
    off_grade = part.has_defect(ld.OFF_GRADE)
    sound = part.is_clean
    spec = hs.MIN_MARTENSITE_SPEC
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
        "verdict": (
            f"SOUND part — {o.result.martensite:.0%} martensite (clears the {spec:.0%} spec), on grade, "
            f"every spec cleared end to end."
            if sound else
            f"{'OFF-GRADE + ' if off_grade else ''}"
            f"{'SOFT CORE' if soft else 'off spec'} — only {o.result.martensite:.0%} martensite "
            f"(under the {spec:.0%} spec). The blow endpoint propagated to the finished part."
        ),
        "trail": [
            {
                "name": s.name,
                "summary": s.summary,
                "mark": "·" if s.in_spec is None else ("✓" if s.in_spec else "✗"),
            }
            for s in part.history
        ],
    }
