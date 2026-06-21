# `game/` — the playable spine on the proven production chain

The gamified spinoff of the simulator, built **last, on a proven verified spine** (the condition
`steel-making.md` §13 set). Its build order is [`docs/plans/game.md`](../docs/plans/game.md); the
doctrine it promotes lives in `steel-making.md` §8 (the firewall), §15 (methods as paths through the
engines), and §16 (the Tier-3 physics-shaped dynamics).

## The honesty posture — `game/` clears no physics triad (by design)

Every `steel/` engine earns its place by clearing the validation triad (analytical limit + conservation
law + published benchmark). **`game/` cannot and must not** — it computes no new material behaviour. It
**orchestrates** the sealed public engines and owns the loop, the knobs, and the UI; it reimplements no
physics and defines no physics constant. Its discipline is **structural** (`game.md` §2):

- **Firewall** — `game` imports only public engine surfaces; the only `import streamlit` is the lazy one
  in `app_game.py`. (`tests/test_game_firewall.py`.)
- **Golden-run determinism** — stepping the game chain to completion reproduces
  `steel.demo_capstone.run_chain`'s sealed verdict *exactly*; that equality is the proof the game adds no
  physics. (`tests/test_game_golden_run.py`.)
- **State-transition / label-correctness / endpoint-consistency** — one immutable `Heat` per turn;
  every educational number read live from the engine; the knob's curve is the validated F2 reading.

## Slice 0 — the hero heat, interactive

The B2 capstone chain made playable: one method (the 4140 BOF/EAF route), the sealed chain auto-running
every stage **except one player knob** — the F2 decarb blow endpoint (value-selection on the C–O τ-curve,
not reflex timing). Set the endpoint → the sealed chain runs a stage per turn → the part is judged
**sound / soft-core** → the live `Heat`'s provenance trail is the post-mortem. An opt-in **educational
mode** adds why-cards on the one knob (prose may live here; every *number* is read live from the engine,
every physics claim cites the engine's own source).

## Layout (the `app.py` three-layer discipline)

| Module | Layer | Role |
|---|---|---|
| `state.py` | logic | the session-state schema + turn transitions (`Heat` in → `Heat` out), the verdict readout |
| `knobs.py` | logic | the blow τ-curve — validated C–O reads + the labelled flavor trajectory |
| `teach.py` | logic | educational why-cards (prose here, numbers read live) |
| `figures.py` | figure | the blow-curve figure (matplotlib imported lazily) |
| `demo_game.py` | demo | the headless golden run (`python -m game.demo_game`) + figure bank |
| `app_game.py` | ui | the **only** `import streamlit`; paper-thin `main()` |

## Run it

```powershell
pip install -e ".[viz,app]"          # matplotlib (viz) + streamlit (app)
python -m game.demo_game             # headless: play the chain twice (reference vs over-blow), bank the figure
streamlit run game/app_game.py       # interactive: set the blow endpoint, run the chain a stage at a time
```

## Scope ceiling (Slice 0)

One method, one knob; **no reflex timing** (value-selection only — real-time timing is deferred to a
non-Streamlit surface); the economy is a placeholder; educational mode is the toggle + why-cards tier.
Slices 1+ (second knob + visible verified/flavor chips, the method/era tech tree, economy and discrete
events) are specified in [`docs/plans/game.md`](../docs/plans/game.md) §6.
