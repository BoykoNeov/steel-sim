---
name: heat-state-spine-built
description: "front-end F-spine (heat_state.py — the Heat record + thin orchestrator seam) BUILT 2026-06-12; the off-spec→crack deferral, structural-teeth-not-triad, next = F4 casting"
metadata:
  node_type: memory
  type: project
  originSessionId: current
---

**Front-end SPINE (build-order item 2: `heat_state.py`) BUILT ✓ 2026-06-12** — the carrier + thin
orchestrator seam that lets the front-end steps compose and **failures propagate**
([[steel-making-frontend-plan]]; plan `docs/plans/steel-making.md` §5 = as-built record). `steel/heat_state.py`
(+ `demo_heat_state.py`, `plots.heat_state_figure`, `tests/test_heat_state.py` 15 + `test_demo_heat_state.py`
5; fast lane **522→542 green**). **No engine touch, no back-end touch, no ADR** (plan is the record);
same additive-new-module posture as [[f1-ellingham-built]]/grain/residual.

**The carrier.** `Heat` = frozen, **immutable** dataclass; every orchestrator step returns a *new* Heat with
one `ProcessStep` appended (provenance trail — history can't be rewritten). **Composes the existing back-end
`Steel`** as its composition field (NOT a parallel type) → `Heat.as_steel()` is a no-op unpack, round-trip
`Steel→Heat→Steel` exact. §5 fields a not-yet-built phase fills (O/N/H gas F2, inclusions F3, residual §18/F4)
default **`None` = "no engine produced it yet"** (the honest "unmeasured", distinct from a real 0). Game-y
state (cost/score/RNG) stays OUT.

**The seam.** `heat_treat` **unpacks Heat→Steel, calls the public `sweep.evaluate`** (which wraps the frozen
array engine one level down — orchestrator does NOT reach into the diffusion core), **repacks** → a spec miss
raises the **soft-core** flag. The **general path** (any composition) — why the propagation proof rides here:
properly-dosed 4140 oil-quench = 96% martensite/632 HV; under-dose Cr/Mo → *same* quench = 40%/416 HV → flagged,
carried downstream. No scripted failure — back-end martensite fraction crossing `MIN_MARTENSITE_SPEC` (a **spec**,
labelled, NOT a fitted constant — the verified/game boundary).

**The load-bearing advisor catch (off-spec→crack DEFERRED):** the §18 residual engine
(`residual.quench_residual_stress`) is **grade-keyed and atlas-anchored** (`ATLAS_STEELS`={1080,4340}; back-end
`STEELS`={1045,1080,4140,8620}, intersection only 1080) — it takes a grade *name*, not a composition. So an
arbitrary **off-spec composition → quench-crack** chain **CANNOT run today** → DEFERRED. Propagation must route
through `evaluate` (general). `quench_crack_check` demos the *same repack pattern* over §18 for a **fixed atlas
grade** (4340: +386 MPa surface tension → quench-crack-risk, consistent with [[residual-stress]] "ON +386"),
clearly labelled the stand-in. (I'd planned to center the hero chain on residual; advisor caught it can't run
off-spec — verify ATLAS vs STEELS membership yourself before wiring.)

**No new physics, no triad** — structural teeth only (round-trip identity, immutability, deterministic flag
propagation, atlas guard, idempotent flags), same posture as inverse design. §6 defect catalogue stays
as-engines-land; this builds carrier + pattern + one general flag (+ bounded atlas illustration).

**Gallery drift-guard forced a figure where I'd planned none** (advisor reversed its own "no figure" steer):
`test_catalog_covers_exactly_the_demos_on_disk` requires EVERY `demo_*.py` catalogued WITH a banked figure +
README mention → a figure-less demo fails the build. Discriminating check (escape hatch to a figure-less Entry):
*can you draw the demo's actual output without a contrived diagram?* Yes — grouped bars (well-vs-under martensite
+ spec line) + atlas residual panel = the propagation *plotted*, legitimate (on par with grain-morphology
ADR 0002). So Option A (add figure) over B (Optional-figure Entry, too much infra for one demo) / C (exemption set,
erodes the guard). New **"Front-end spine"** gallery section → regen `index.html` ([[gallery-page]]).

**Surfacing:** demo (text trail) + figure `docs/figures/steel-heat-state.png` + gallery card + both READMEs +
plan §5 as-built. **Notebook & app DEFERRED** (same as F1 — both surfaces heat-treatment-framed).

**Next front-end slice = build-order item 3: F4 casting link** — reuse the frozen heat engine (heat mode, mold
Robin BC) + the **existing Scheil**, proving the chain runs front-to-back inside steel-sim before any `game/`
scaffolding. Then F2/F3 (refining+ladle), then `game/` last. Amends [[f1-ellingham-built]] (its "next" pointer
is now done).
