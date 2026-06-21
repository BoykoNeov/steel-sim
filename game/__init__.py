"""``game/`` — the playable spine on the proven production chain (``docs/plans/game.md``).

The one package in this repo that clears **no physics validation triad** *by design* (plan §2): it
**orchestrates** the sealed ``steel`` engines into a stateful, multi-turn game; it reimplements no
material behaviour and defines no physics constant. Its discipline is **structural**, the same class
as the ``heat_state`` spine and the ``demo_capstone`` integration finale:

* **Firewall** (plan §4 = ``steel-making.md`` §8) — ``game`` imports only public engine surfaces; every
  cited number lives in ``steel``. The only ``import streamlit`` is in the paper-thin :mod:`game.app_game`.
* **Three layers** (the ``app.py`` idiom) — :mod:`game.state` / :mod:`game.knobs` / :mod:`game.teach`
  are pure logic (no streamlit, no matplotlib, always-green unit tests); :mod:`game.figures` wraps the
  render layer with matplotlib imported lazily; :mod:`game.app_game` is the only UI.

**Slice 0** (the first build): the already-proven B2 capstone chain (``demo_capstone``) made playable —
one method, one player knob (the F2 decarb blow endpoint, value-selection on the C–O τ-curve), the
sealed chain auto-running the rest, the part judged by the back-end physics (sound / soft-core), the
``Heat`` provenance trail as the post-mortem — plus the opt-in **educational mode** (why-cards on the
one knob, every number read *live* from the engine).
"""
