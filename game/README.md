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
- **The purity-control ramp (Slice 2)** — the tech tree's acceptance bar: each era conquers *exactly* the
  tramp the history says it did, so a dirty ore walks the player up the tree (acid Bessemer cold-shorts on
  phosphorus, Thomas fixes it, only the modern ladle takes the sulfur), and the modern reference still
  reproduces the golden run. (`tests/test_game_methods.py`.)

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

## Slice 2 — methods & the era ramp (the tech tree)

The `steel-making.md` §15.2 method→engine map made playable: make the **same** grade (4140) through the
methods of history — **acid Bessemer** (1856), **Thomas / basic Bessemer** (1879), **basic open hearth**,
the **BOF**, and modern **EAF + ladle metallurgy** — each a *constrained walk* through the same validated
F1–F4 engines. A `Method` (`presets.py`) fixes the era's refining chemistry: which dephosphorization slag
runs (acid `slag.ACID_BESSEMER_SLAG`, L_P≈1 → phosphorus stays; basic `slag.BASIC_CONVERTER_SLAG`, L_P in the
hundreds → conquered) and whether the era has the secondary-metallurgy stages (reducing-ladle desulfurization;
vacuum degassing). An `Ore` sets the charge's **tramp load**, and the **purity-control ramp** is the
difficulty curve:

- a **phosphoric** ore is cold-short in acid Bessemer, phosphorus-fixed-but-still-dirty in Thomas (no ladle
  desulf yet), and **sound only in the modern ladle era**;
- a **clean (non-phosphoric)** ore is sound even in acid Bessemer — exactly why the early Bessemer trade
  fought over it.

The two era-gated tramps are **phosphorus and sulfur** (the benchmarked slag-partition physics). Hydrogen is
**not** era-gated (the model introduces no charge hydrogen, so "no vacuum" makes no flaking claim), and the
kill, speed, scale, and nitrogen are **flavor** (labelled). The basic open hearth and the BOF share Thomas'
chemistry in this model — their distinction is flavor, *said and pinned by a test*; the **bloomery** is the
named era-0 floor (a different product below the F1 crossover), not a played 4140 route. In a historical era
the **method and ore are the decision** (the blow endpoint is still yours); the full per-stage gauntlet is
the modern era.

## Layout (the `app.py` three-layer discipline)

| Module | Layer | Role |
|---|---|---|
| `state.py` | logic | the `Recipe` choices vector + session-state schema + turn transitions (`Heat` in → `Heat` out), the verdict readout; the era method/ore wiring (Slice 2) |
| `knobs.py` | logic | the blow τ-curve — validated C–O reads + the labelled flavor trajectory |
| `choices.py` | logic | the per-stage decision tables (named options; the recommended one reproduces the reference); the era knob-gating |
| `presets.py` | logic | the method/era tech tree + the ore table (Slice 2) — each era a constrained walk through the engines |
| `postmortem.py` | logic | the gauntlet judge — the sealed consequence engines run on the finished part (no spine mutation) |
| `teach.py` | logic | educational why-cards — one per knob (Slice 1) + one per era + the purity-ramp timeline (Slice 2); prose here, numbers read live |
| `figures.py` | figure | the blow-curve figure + the purity-ramp figure (matplotlib imported lazily) |
| `demo_game.py` | demo | the headless gauntlet golden run (`python -m game.demo_game`) + figure bank |
| `demo_game_methods.py` | demo | the headless era tech tree (`python -m game.demo_game_methods`) + figure bank |
| `app_game.py` | ui | the **only** `import streamlit`; paper-thin `main()` |

## Run it

```powershell
pip install -e ".[viz,app]"             # matplotlib (viz) + streamlit (app)
python -m game.demo_game                # headless: play the gauntlet safe (sound) then rough (spoiled), bank the figure
python -m game.demo_game_methods        # headless: the era tech tree — the purity ramp across the methods of history
streamlit run game/app_game.py          # interactive: pick a method + ore, decide the stages, read the post-mortem
```

## Scope ceiling (Slices 0–2)

The methods are the **converter-era purity ramp judged as 4140** — every era makes the same grade and they
differ in *which tramp they can clean*. The §15.2 methods that make a **different product on a different
walk** (the bloomery's wrought iron, cementation, crucible, wootz) each need their own win-condition and are
a **named deferral**. **No reflex timing** (value-selection only — real-time timing is deferred to a
non-Streamlit surface); the economy is a placeholder. Casting carries no losable lever on this grade (an
honest pass-through, not a faked knob). The verified-vs-flavor labels as styled UI **chips** + the
physics-shape explainer (tier 2) remain deferred. Slice 3+ (economy, scale, discrete events) is specified in
[`docs/plans/game.md`](../docs/plans/game.md) §6.
