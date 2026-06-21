"""``game.app_game`` — the paper-thin Streamlit surface (the ONLY place ``import streamlit`` lives).

The one UI layer of the ``game/`` package (``game.md`` §4): every value it shows is computed by a tested
helper in :mod:`game.state` / :mod:`game.knobs` / :mod:`game.choices` / :mod:`game.teach` /
:mod:`game.figures`, so the only statements here that can raise are ``st.*`` calls and the figure builder
(matplotlib-absent → an ``st.info`` hint). Not unit-tested (ADR 0002 — the UI is reach); the firewall test
asserts ``streamlit`` is confined to this file and imported lazily.

**Slice 1 — the gauntlet.** Slice 0 made the capstone chain playable with a single knob; every other stage
auto-ran, so there was nothing else to get wrong. Slice 1 makes **every stage a decision** (:mod:`game.choices`):
before each sealed stage runs, the player chooses (blow endpoint, dephosphorization, kill metal, vacuum,
desulfurization, ferroalloys, quench). A wrong call plants a latent flaw the live ``Heat`` carries; the
finished part is judged by the **post-mortem** (:mod:`game.postmortem`), which reports which defect each
mistake became. Take every recommendation and the part is sound — and *exactly* reproduces the capstone
golden run (the recipe never drifts off the reference). Casting is an honest pass-through (no pass/fail
lever on this grade), surfaced as such.

Run it::

    pip install -e .[viz,app]                 # matplotlib (viz) + streamlit (app)
    streamlit run game/app_game.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

# --- run-as-script bootstrap: repo root on sys.path BEFORE the absolute imports (the app.py idiom).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game import choices as ch
from game import knobs as kn
from game import state as gs
from game import teach as tc
from game.figures import blow_curve_figure

_SESSION_KEY = "game_state"
_VIZ_HINT = "Install the figure: `pip install -e .[viz,app]`"


def _why_cards(st, knob: str, *, carbon_target: float | None = None) -> None:
    """Render the educational why-card(s) for a knob (numbers read live; verified/flavor chipped)."""
    for card in tc.knob_why_cards(knob, carbon_target=carbon_target):
        chip = "✅ verified" if card.label == tc.VERIFIED else "🟡 flavor"
        with st.expander(f"{chip} · {card.title}"):
            st.markdown(card.body)
            st.caption(f"source: {card.source}")


def _carbon_decision(st, state: gs.GameState) -> dict:
    """The decarb blow — the one continuous knob: a slider over the validated C–O τ-curve + the figure."""
    carbon = st.slider(
        "Blow endpoint — carbon (wt %)", kn.BLOW_C_MIN, kn.BLOW_C_MAX, float(state.recipe.carbon), 0.01,
        help="Where you stop the carbon blow. The 4140 grade window is the aim.",
    )
    pos = kn.endpoint_position(carbon)
    lo, hi = pos.window
    msg = {
        "on-aim": f"On aim — {carbon:.2f} %C is inside the {lo:.2f}–{hi:.2f} % grade window.",
        "over-blow": f"Over-blown — {carbon:.2f} %C is below the {lo:.2f} % floor (off-grade + over-oxidized).",
        "under-blow": f"Under-blown — {carbon:.2f} %C is above the {hi:.2f} % ceiling (carbon left in).",
    }[pos.zone]
    (st.success if pos.zone == "on-aim" else st.warning)(msg)
    try:
        st.pyplot(blow_curve_figure(carbon))
    except ImportError:
        st.info(_VIZ_HINT)
    if state.educational:
        _why_cards(st, "carbon", carbon_target=carbon)
    return {"carbon": carbon}


def _named_decision(st, state: gs.GameState, knob: str) -> dict:
    """A named-choice knob (slag / kill metal / vacuum / ferroalloy / quench) from the tested option table."""
    decision = ch.DECISIONS[knob]
    choice = st.radio(
        decision.prompt, decision.options, index=decision.default_index(),
        format_func=lambda o: o.label,
    )
    (st.caption if choice.recommended else st.warning)(
        ("Recommended — " if choice.recommended else "Risky — ") + choice.note)
    if state.educational:
        _why_cards(st, knob)
    return {knob: choice.value}


def _render_decision(st, state: gs.GameState, stage: gs.Stage) -> dict:
    """Render the upcoming stage's decision(s) and return the chosen recipe overrides (``{}`` for casting)."""
    knobs = ch.STAGE_DECISIONS[stage.name]
    if not knobs:                                          # casting — the honest pass-through
        st.caption("No decision here: on this grade casting can't spoil the part — it sets the segregation "
                   "band the heat-treat inherits (Chvorinov time + Scheil centerline).")
        return {}
    overrides: dict = {}
    for knob in knobs:
        overrides.update(_carbon_decision(st, state) if knob == "carbon" else _named_decision(st, state, knob))
    return overrides


def _trail_block(st, heat) -> None:
    """Render the live provenance trail — the post-mortem the spine builds for free."""
    st.markdown("##### Provenance trail — one Heat, the whole chain")
    for step in heat.history:
        mark = "·" if step.in_spec is None else ("✓" if step.in_spec else "✗")
        st.markdown(f"{mark} **{step.name}** — {step.summary}")


def _post_mortem_block(st, r: dict) -> None:
    """The finished-part verdict: sound vs spoiled + the consequences, each tied to the stage that planted it."""
    m1, m2 = st.columns(2)
    m1.metric("Finished part", r["martensite_str"])
    m2.metric("Verdict", "SOUND" if r["sound"] else "SPOILED")
    (st.success if r["sound"] else st.error)(r["verdict"])
    if r["consequences"]:
        st.markdown("##### What went wrong — the post-mortem")
        for c in r["consequences"]:
            st.markdown(f"**{c['headline']}** — planted at *{c['planted_by']}*")
            st.caption(c["detail"])
    elif not r["sound"]:
        st.caption("Off the grade window — the blow or the trim put the composition out of spec.")
    st.caption("Every verdict is the sealed engines' own, read off the one Heat you played — the game adds "
               "no physics (`game.md` §2).")


def _start_screen(st) -> None:
    """The startup: opt into educational mode, then start the heat (decisions happen stage by stage)."""
    st.subheader("Start a heat")
    educational = st.checkbox(
        "Educational mode — a why-card on every decision, the validated targets named", value=False,
        help="An information overlay only: it explains more, it does not change the physics or difficulty.",
    )
    st.markdown(tc.intro_text(educational))
    if st.button("Start the heat ▶", type="primary"):
        st.session_state[_SESSION_KEY] = gs.new_game(educational=educational)
        st.rerun()


def _play_screen(st, state: gs.GameState) -> None:
    """The turn loop: choose the upcoming stage, run it, build the trail, judge the part at the end."""
    st.subheader("Making one heat of 4140")
    st.progress(state.stage / len(gs.STAGES), text=f"stage {state.stage} of {len(gs.STAGES)}")

    if not state.done:
        nxt = state.next_stage
        st.info(f"**Next — {nxt.name}.** {nxt.blurb}")
        overrides = _render_decision(st, state, nxt)
        if st.button(f"Run {nxt.name} ▶", type="primary"):
            chosen = dataclasses.replace(state, recipe=dataclasses.replace(state.recipe, **overrides))
            st.session_state[_SESSION_KEY] = gs.advance(chosen)
            st.rerun()
    else:
        _post_mortem_block(st, gs.final_readout(state))

    _trail_block(st, state.heat)
    if st.button("New heat ↺"):
        del st.session_state[_SESSION_KEY]
        st.rerun()


def main() -> None:
    """Render the Slice-1 gauntlet. Streamlit-only; not unit-tested (ADR 0002 — the UI is reach)."""
    import streamlit as st

    st.set_page_config(page_title="Steel — make one heat", layout="centered")
    st.title("Make one heat — ore to part")
    st.caption(
        "A playable run of the validated production chain (Steel `game/` plan, Slice 1). **Every stage is a "
        "decision** — take every recommendation and the part comes out sound (and reproduces the capstone "
        "exactly); one wrong call plants a flaw the finished part is judged on. Every number is produced by "
        "a model behind its own validation triad; the game only chooses and threads the `Heat`."
    )

    state = st.session_state.get(_SESSION_KEY)
    if state is None:
        _start_screen(st)
    else:
        _play_screen(st, state)


if __name__ == "__main__":
    main()
