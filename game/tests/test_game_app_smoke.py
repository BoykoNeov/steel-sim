"""UI smoke test (``game.md`` §4) — the Streamlit decision paths render without raising, on a fake ``st``.

ADR 0002 keeps the UI out of unit tests (it is reach), and the firewall test only *reads* ``app_game.py`` —
so the Slice-1 rewrite (per-stage ``_render_decision``, ``st.radio`` over ``Option`` dataclasses, the
two-knob heat-treat stage, the post-mortem panel) was covered by **nothing**: a syntax or attribute error
would pass the whole suite, and the player's first action is ``streamlit run game/app_game.py``. The screen
helpers take ``st`` as a parameter (injectable), so a minimal fake ``st`` drives every render path here
without importing streamlit — a smoke test (it renders, no exception), never a correctness check.
"""
import dataclasses

from game import app_game as app
from game import state as gs


class _Box:
    """A no-op context manager — stands in for ``st.expander(...)``."""
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Col:
    def metric(self, *a, **k): pass


class FakeSt:
    """A minimal streamlit stand-in: widgets return canned values, everything else is a no-op."""

    def __init__(self, *, slider=None, radio_index=None, checkbox=False, button=False):
        self._slider = slider
        self._radio_index = radio_index
        self._checkbox = checkbox
        self._button = button
        self.session_state: dict = {}

    def slider(self, label, lo, hi, value, step=None, help=None):
        return self._slider if self._slider is not None else value

    def radio(self, prompt, options, index=0, format_func=None):
        i = self._radio_index if self._radio_index is not None else index
        if format_func is not None:
            format_func(options[i])                      # exercise the label formatter too
        return options[i]

    def checkbox(self, *a, **k): return self._checkbox
    def button(self, *a, **k): return self._button
    def columns(self, n): return [_Col() for _ in range(n)]
    def expander(self, *a, **k): return _Box()
    def progress(self, *a, **k): pass
    def pyplot(self, *a, **k): pass

    def __getattr__(self, name):                         # markdown/caption/success/warning/info/title/rerun/...
        def _noop(*a, **k): return None
        return _noop


def test_render_decision_walks_every_stage_with_education_on():
    # Walk the whole gauntlet through the UI render path (educational on → exercises every why-card,
    # the carbon slider + figure, each named radio, and the cast empty branch). Each returns overrides.
    state = gs.new_game(educational=True)
    for stage in gs.STAGES:
        overrides = app._render_decision(FakeSt(), state, stage)
        assert isinstance(overrides, dict)
        knobs = {k for k in overrides}
        assert knobs <= {f.name for f in dataclasses.fields(gs.Recipe)}
        state = gs.advance(dataclasses.replace(state, recipe=dataclasses.replace(state.recipe, **overrides)))
    assert state.done


def test_post_mortem_block_renders_sound_and_spoiled():
    sound = gs.final_readout(gs.play_to_end(recipe=gs.REFERENCE))
    app._post_mortem_block(FakeSt(), sound)              # no consequences branch
    spoiled = gs.final_readout(gs.play_to_end(
        recipe=dataclasses.replace(gs.REFERENCE, deoxidizer="Mn", desulfurize=False)))
    assert spoiled["consequences"]                       # the rough heat really did plant defects
    app._post_mortem_block(FakeSt(), spoiled)            # the consequences-list branch


def test_play_screen_renders_mid_game_and_finished():
    app._play_screen(FakeSt(), gs.new_game(educational=True))        # not done → renders a decision
    app._play_screen(FakeSt(), gs.play_to_end(recipe=gs.REFERENCE))  # done → renders the post-mortem


def test_start_screen_starts_a_heat_on_the_button():
    app._start_screen(FakeSt())                          # button not pressed → nothing stored
    pressed = FakeSt(button=True)
    app._start_screen(pressed)
    assert app._SESSION_KEY in pressed.session_state and not pressed.session_state[app._SESSION_KEY].done
