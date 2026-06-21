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
- **Losability (Slice 1)** — the gauntlet's acceptance bar: every claimed knob has a wrong setting that
  flips the finished-part verdict to a *distinct* defect, end to end (one test apiece). A green
  firewall/golden-run says nothing about this — a gauntlet of cosmetic knobs would pass all of them.
  (`tests/test_game_losability.py`.)

## Slice 0 — the hero heat, interactive

The B2 capstone chain made playable: one method (the 4140 BOF/EAF route), the sealed chain auto-running
every stage **except one player knob** — the F2 decarb blow endpoint (value-selection on the C–O τ-curve,
not reflex timing). Set the endpoint → the sealed chain runs a stage per turn → the part is judged
**sound / soft-core** → the live `Heat`'s provenance trail is the post-mortem. An opt-in **educational
mode** adds why-cards on the one knob (prose may live here; every *number* is read live from the engine,
every physics claim cites the engine's own source).

## Slice 1 — the gauntlet (every stage a decision)

Slice 0's critique was *"nothing to get wrong in the other steps."* Slice 1 answers it: a frozen `Recipe`
gives **every stage a knob** (defaults = the capstone reference), and a wrong call plants a latent flaw the
finished part is judged on by the **post-mortem** (`postmortem.py`), which runs the sealed consequence
engines (`gas_porosity`, `hydrogen_flaking`, `hot_work` red-short, `hot_tear`, `cold_short_check`) on the
part *without* mutating the spine — so the golden run stays exact. **Seven knobs are losable** (decarb →
off-grade/soft-core, dephos → cold-short, **deox = the kill metal** Al ≫ Si > Mn → gas porosity, degas →
flaking, desulf → sulfur over the cleanliness spec, trim carbon-pickup → off-grade, quench/section → soft
core); **casting is an honest no-loss pass-through** (no pass/fail lever on this grade — stated, not faked).
Take every recommendation and the part is sound — and reproduces `run_chain` exactly.

## Layout (the `app.py` three-layer discipline)

| Module | Layer | Role |
|---|---|---|
| `state.py` | logic | the `Recipe` choices vector + session-state schema + turn transitions (`Heat` in → `Heat` out), the verdict readout |
| `knobs.py` | logic | the blow τ-curve — validated C–O reads + the labelled flavor trajectory |
| `choices.py` | logic | the per-stage decision tables (named options; the recommended one reproduces the reference) |
| `postmortem.py` | logic | the gauntlet judge — the sealed consequence engines run on the finished part (no spine mutation) |
| `teach.py` | logic | educational why-cards, one per knob (prose here, numbers read live) |
| `figures.py` | figure | the blow-curve figure (matplotlib imported lazily) |
| `demo_game.py` | demo | the headless golden run (`python -m game.demo_game`) + figure bank |
| `app_game.py` | ui | the **only** `import streamlit`; paper-thin `main()` |

## Run it

```powershell
pip install -e ".[viz,app]"          # matplotlib (viz) + streamlit (app)
python -m game.demo_game             # headless: play the gauntlet safe (sound) then rough (spoiled), bank the figure
streamlit run game/app_game.py       # interactive: decide every stage, run the chain, read the post-mortem
```

## Scope ceiling (Slices 0–1)

One method, the 4140 route; **no reflex timing** (value-selection only — real-time timing is deferred to a
non-Streamlit surface); the economy is a placeholder. Casting carries no losable lever on this grade (an
honest pass-through, not a faked knob). Educational mode is the toggle + a why-card per decision; surfacing
the verified-vs-flavor labels as styled UI **chips** + the physics-shape explainer (tier 2) is deferred.
Slices 2+ (the method/era tech tree, economy and discrete events) are specified in
[`docs/plans/game.md`](../docs/plans/game.md) §6.
