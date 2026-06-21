---
name: game-slice0-built
description: "A1 game/ spinoff Slice 0 BUILT — the B2 capstone made playable; structural (no physics triad), golden-run == run_chain exactly; one engine touch = promoted casting.cast_billet_onto"
metadata:
  node_type: memory
  type: project
  originSessionId: 2f2c32f1-dd62-4154-841c-b0a18b03ce37
---

**A1 `game/` spinoff — Slice 0 BUILT ✓ 2026-06-21** (the first `game/` code; build plan was
`docs/plans/game.md`, written same day). The **B2 capstone chain made playable**: a **top-level `game/`
package** (sibling of `steel/`, not under it), 3-layer `app.py` idiom — `state.py`/`knobs.py`/`teach.py`
(pure logic, no streamlit/matplotlib) + `figures.py` (lazy mpl) + `app_game.py` (the ONLY `import
streamlit`, lazy in `main()`) + `demo_game.py` (headless golden run) + `tests/` (4 structural checks → 24
tests). pyproject: `game*` in `packages.find` + `game` in `testpaths`. Banked `steel-game-blow.png`;
gallery *Game* card; root + `steel/` + new `game/README.md` wired. **1010 fast-lane green.**

**The one knob = the F2 decarb blow endpoint, as VALUE-SELECTION on the C–O τ-curve** (the plan's honest
reframe of the Bessemer "flame-drop" — Streamlit reruns do reflex timing badly). `knobs.py` reads the
**validated** `refining.equilibrium_oxygen(C)` (O climbs as C falls; window 0.38–0.43, aim 0.40, product
≈0.0021) + a **labelled flavor** first-order blow trajectory (Tier-3 kinetics, normalized so it lands on
the chosen endpoint). Over-blow = a **position readout** ("off-grade + bath over-oxidized"), not a clock.

**Turn structure (the load-bearing new surface):** frozen `GameState(heat, carbon_target, stage,
educational)`; `advance(state)` runs ONE sealed stage on the live `Heat` → exactly one `ProcessStep`
appended → immutable. Charge origin from `from_hot_metal`; 8 stages (decarb knob, dephos, deox, degas,
desulf, trim, cast, heat-treat) single-sourced from `demo_capstone` constants. UI auto-drives `advance`
after the knob is set; **per-click vs auto-run is cosmetic — `advance` is the tested unit** (advisor).

**STRONGEST TOOTH = golden-run equality:** `state.play_to_end(c).heat == demo_capstone.run_chain(c).part`
**exactly** (frozen-dataclass deep eq over composition + filled fields + defects + the whole 9-step trail),
for both REF (0.40 → sound) and FOIL (0.25 → off-grade + soft-core). That equality **IS** the proof the
game adds no physics — it calls the same seams in the same order, so it cannot diverge. The failure is
emergent (martensite < `MIN_MARTENSITE_SPEC`), never a scripted branch.

**The ONE engine touch = promoting the casting re-base** (advisor: "promote, don't replay or duplicate").
The capstone's documented **promotion trigger fired** — the game spine is the *second surface* needing the
F4 glue, so `demo_capstone._cast_onto` → public **`casting.cast_billet_onto(parent, *, modulus) ->
CastSection`** (nominal re-based onto the parent via `evolve`; centerline + all else identical to bare
`cast_billet`, since cast only Scheil-enriches the *centerline* — nominal carries the input composition).
Behaviour-preserving refactor: `test_demo_capstone` green **and `print_summary` byte-identical** (the
inverted-verdict landmine guard, diffed before/after) + 2 focused `cast_billet_onto` tests. No new
physics/triad/ADR — pure repack, same class as `Heat.evolve`.

**Educational mode = info-overlay why-cards** (`teach.py`, tier 1): prose lives in `game/`, every **number
read LIVE** from the engine. The discriminating label test (advisor: don't test "returns a string") drives
**two endpoints and asserts the quoted O ppm MOVES** (53@0.40 vs 84@0.25) + matches `equilibrium_oxygen`
exactly → catches a baked constant; verified cards cite an engine, the flavor card wears "plausible".

**`game/` clears NO physics-validation triad — by design.** Its discipline is **structural** (the 4
checks): **firewall** (source-scan for real import *statements* not substrings — streamlit confined to
`app_game`, lazy; no `_`-private steel imports); **golden-run**; **state-transition**; **label +
endpoint-consistency** (curve values == `equilibrium_oxygen` exactly, targets == cited F2 numbers).

**Gallery extension:** `Entry` gained a `package` field ("steel"|"game"); `_card_html` resolves
source/run-cmd under it; `test_gallery` coverage scan made package-aware (scans `steel/`+`game/` for
`demo_*.py`); 38 entries, drift-guard regenerated. Slices 1+ (2nd knob = deox kill, method/era tech tree,
economy/discrete events) remain plan-only. Amends [[next-directions-catalogue]]; wraps
[[full-chain-capstone-built]] (the spine Slice 0 plays); reuses [[gallery-page]] discipline.
