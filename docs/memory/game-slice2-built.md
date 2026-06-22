---
name: game-slice2-built
description: A1 game/ Slice 2 BUILT — the era tech tree (the purity-control ramp). Methods as constrained walks over F1-F4; P/S era-gated by slag regime; golden run preserved; the ramp is the acceptance bar
metadata: 
  node_type: memory
  type: project
  originSessionId: dd5041d2-d517-425f-b292-ef47c8699345
---

**A1 `game/` Slice 2 BUILT ✓ 2026-06-22 — the era tech tree.** The `steel-making.md` §15.2 method→engine map
made playable: make the **same grade (4140)** through the methods of history, each a **constrained walk** over
the same validated F1–F4 engines. Wraps [[game-slice1-built]]; amends [[next-directions-catalogue]]; reuses
[[slag-f2-slice2-built]] (the slag physics it gates on) + [[gallery-page]]. **Cut A** = the user's
`AskUserQuestion` choice (converter-era purity ramp judged as 4140) over the fuller different-product tree.

**Spine.** `game/presets.py` (NEW) = `Method` table (acid Bessemer 1856 → Thomas 1879 → basic open hearth →
BOF → modern EAF+ladle) + `Ore` table (phosphoric = `dc.LEAN_BACKBONE`; clean = same backbone, P 0.012/S 0.018).
A `Method` carries `dephos_slag` (acid vs basic) + `can_desulfurize`/`can_degas` flags; `state.py` stage seams
`_dephosphorize/_desulfurize/_degas` made **method-aware** (read `_method_of(state)`, lazy presets import to
dodge a cycle). `GameState` gained `method`/`ore` (default None→MODERN/PHOSPHORIC). **Golden run UNTOUCHED**:
`new_game()` defaults = modern+phosphoric+REFERENCE → `play_to_end == run_chain` EXACTLY (existing test stands).

**The era lever = the SLAG REGIME, already built in `slag.py`** (no new physics, no engine touch, no ADR):
acid `ACID_BESSEMER_SLAG` lands `L_P≈1` (P stays — *runs and visibly fails*, more honest than "skip the
stage"), basic `BASIC_CONVERTER_SLAG` `L_P` in the hundreds. Desulf = a reducing-ladle (modern) unlock; degas
likewise. **The purity-control ramp is the difficulty curve**, made to bite by the NEW **ore axis**:
phosphoric ore → cold-short in acid Bessemer, P-fixed-but-still-dirty(S) in Thomas/OH/BOF, **sound only in the
modern ladle era**; clean ore → sound even in acid Bessemer (*the* reason early Bessemer needed non-phosphoric
ore). Matrix **probed empirically BEFORE writing presets.py** (the Slice-1 discipline).

**Honesty calls (advisor-endorsed, don't reopen):** (1) **Only P and S are era-gated** — the benchmarked
slag-partition tramps. **Hydrogen is deliberately NOT era-gated**: the model carries no charge H (`degas` only
*sets* a Sieverts equilibrium), so "no vacuum" makes **no flaking claim** rather than faking one — the
strongest honesty move. (2) **deox fixed = Al across all eras** (avoids a false porosity always-fail; the
Al/vacuum anachronism in old eras is labelled flavor). (3) **OH/BOF share Thomas' chemistry in-model** —
their distinction (scale/speed/low-N) is flavor, *said and pinned by a test*. (4) **Bloomery = named era-0
floor** (`BLOOMERY_NOTE`, a different product below the F1 crossover), NOT a played 4140 route (deferred).

**Acceptance bar = the ramp itself** (the Slice-2 analogue of [[game-slice1-built]] losability): each era
conquers exactly the tramp history says it did, pinned by `test_game_methods.py` (35 new tests, **60→95
game, 1098 fast-lane green**). Tier-3 educational = `teach.method_why_cards` (per-era cards, L_P read LIVE
from the slag engine) + the purity-ramp `timeline`. `demo_game_methods.py` + `figures.methods_figure`
(purity-ramp figure `steel-game-methods.png`) + gallery entry (39) + READMEs + `game.md` plan all wired.
**Advisor fix folded:** demo stdout now states "SPOILED = can't make MODERN 4140, not a failed historical
process" + the OH/BOF-identical-rows note. **Plan's gate: stop and PLAYTEST before Slice 3.**

**Deferred (named):** the different-product methods (bloomery wrought iron, cementation `carburize.py`,
crucible, wootz `wootz.py` — each needs its own win-condition); the verified-vs-flavor **chip styling** +
tier-2 physics-shape explainer (still open from Slice 1); Slice 3 (economy/scale/discrete events).
