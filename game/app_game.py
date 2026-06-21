"""``game.app_game`` — the paper-thin Streamlit surface (the ONLY place ``import streamlit`` lives).

The one UI layer of the ``game/`` package (``game.md`` §4): every value it shows is computed by a tested
helper in :mod:`game.state` / :mod:`game.knobs` / :mod:`game.teach` / :mod:`game.figures`, so the only
statements here that can raise are ``st.*`` calls and the figure builder (matplotlib-absent → an
``st.info`` hint). Not unit-tested (ADR 0002 — the UI is reach); the firewall test asserts ``streamlit`` is
confined to this file and imported lazily.

**Slice 0 — the playable capstone.** The stateful, multi-turn surface (``game.md`` §3): a live ``Heat``
in ``st.session_state`` evolving one sealed stage per turn. At the start the player sets the **one knob**
— the F2 decarb blow endpoint, value-selection on the C–O τ-curve — and opts into **educational mode**;
then the sealed chain runs a stage per click, the provenance trail building as the post-mortem, until the
part is judged sound or soft-cored by the back-end physics.

Run it::

    pip install -e .[viz,app]                 # matplotlib (viz) + streamlit (app)
    streamlit run game/app_game.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- run-as-script bootstrap: repo root on sys.path BEFORE the absolute imports (the app.py idiom).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game import knobs as kn
from game import state as gs
from game import teach as tc
from game.figures import blow_curve_figure

_SESSION_KEY = "game_state"
_VIZ_HINT = "Install the figure: `pip install -e .[viz,app]`"


def _start_screen(st) -> None:
    """The startup: set the one knob (blow endpoint) + the educational toggle, then start the heat."""
    st.subheader("Start a heat — set the blow endpoint")
    educational = st.checkbox(
        "Educational mode — extra why-cards, tips, and the validated targets named", value=False,
        help="An information overlay only: it explains more, it does not change the physics or difficulty.",
    )
    st.markdown(tc.intro_text(educational))

    carbon_target = st.slider(
        "F2 decarb blow endpoint — carbon (wt %)", kn.BLOW_C_MIN, kn.BLOW_C_MAX, float(kn.grade_carbon_aim()),
        0.01, help="The one knob: where you stop the carbon blow. The grade window is the aim.",
    )
    pos = kn.endpoint_position(carbon_target)
    lo, hi = pos.window
    msg = {
        "on-aim": f"On aim — {carbon_target:.2f} %C is inside the {lo:.2f}–{hi:.2f} % grade window.",
        "over-blow": f"Over-blown — {carbon_target:.2f} %C is below the {lo:.2f} % floor (off-grade + over-oxidized).",
        "under-blow": f"Under-blown — {carbon_target:.2f} %C is above the {hi:.2f} % ceiling (carbon left in).",
    }[pos.zone]
    (st.success if pos.zone == "on-aim" else st.warning)(msg)

    try:
        st.pyplot(blow_curve_figure(carbon_target))
    except ImportError:
        st.info(_VIZ_HINT)

    if educational:
        st.markdown("##### Why-cards — the decarb blow")
        for card in tc.blow_why_cards(carbon_target):
            chip = "✅ verified" if card.label == tc.VERIFIED else "🟡 flavor"
            with st.expander(f"{chip} · {card.title}"):
                st.markdown(card.body)
                st.caption(f"source: {card.source}")

    if st.button("Start the heat ▶", type="primary"):
        st.session_state[_SESSION_KEY] = gs.new_game(carbon_target, educational=educational)
        st.rerun()


def _trail_block(st, heat) -> None:
    """Render the live provenance trail — the post-mortem the spine builds for free."""
    st.markdown("##### Provenance trail — one Heat, the whole chain")
    for step in heat.history:
        mark = "·" if step.in_spec is None else ("✓" if step.in_spec else "✗")
        st.markdown(f"{mark} **{step.name}** — {step.summary}")


def _play_screen(st, state: gs.GameState) -> None:
    """The turn loop: show the live Heat + trail, run one sealed stage per click, judge at the end."""
    st.subheader(f"Making one heat of 4140 — blow endpoint {state.carbon_target:.2f} %C")
    done = state.done
    progress = state.stage / len(gs.STAGES)
    st.progress(progress, text=f"stage {state.stage} of {len(gs.STAGES)}")

    if not done:
        nxt = state.next_stage
        st.info(f"**Next stage — {nxt.name}.** {nxt.blurb}")
        if state.educational and nxt.is_knob:
            for card in tc.blow_why_cards(state.carbon_target):
                chip = "✅ verified" if card.label == tc.VERIFIED else "🟡 flavor"
                with st.expander(f"{chip} · {card.title}"):
                    st.markdown(card.body)
                    st.caption(f"source: {card.source}")

    _trail_block(st, state.heat)

    if done:
        r = gs.final_readout(state)
        m1, m2 = st.columns(2)
        m1.metric("Finished part", r["martensite_str"])
        m2.metric("Verdict", "SOUND" if r["sound"] else ("SOFT CORE" if r["soft_core"] else "OFF SPEC"))
        (st.success if r["sound"] else st.error)(r["verdict"])
        st.caption(
            "The verdict is emergent, not scripted: the soft core is the back-end martensite fraction "
            f"crossing the {r['spec']:.0%} spec, reached through your blow choice — carried on the same "
            "Heat that flowed down the chain."
        )

    c1, c2 = st.columns(2)
    if not done:
        if c1.button("Run next stage ▶", type="primary"):
            st.session_state[_SESSION_KEY] = gs.advance(state)
            st.rerun()
    if c2.button("New heat ↺"):
        del st.session_state[_SESSION_KEY]
        st.rerun()


def main() -> None:
    """Render the Slice-0 game. Streamlit-only; not unit-tested (ADR 0002 — the UI is reach)."""
    import streamlit as st

    st.set_page_config(page_title="Steel — make one heat", layout="centered")
    st.title("Make one heat — ore to part")
    st.caption(
        "A playable run of the validated production chain (Steel `game/` plan, Slice 0). You set **one** "
        "knob — the F2 decarb blow endpoint — and the sealed engines run the rest. Every number is "
        "produced by a model behind its own validation triad; the game only turns the knob and threads the "
        "`Heat` (it adds no physics — `game.md` §2)."
    )

    state = st.session_state.get(_SESSION_KEY)
    if state is None:
        _start_screen(st)
    else:
        _play_screen(st, state)


if __name__ == "__main__":
    main()
