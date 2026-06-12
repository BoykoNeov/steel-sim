---
name: martemper
description: Steel §17 martempering — austempering's short-hold sibling; built 2026-06-11 (no new physics, distortion-proxy payoff)
metadata:
  type: project
---

Steel **§17 martempering BUILT ✓ 2026-06-11** (`steel/martemper.py` + demo + figure + 22 tests;
suite 425→**447 green**). The smaller §11 deferral, user-chosen. Marquench: quench into a bath
**just above Mₛ** (`Mₛ<T_bath<Bs`), hold only to **thermally equalise**, slow-cool to martensite →
same hardness as a direct quench, far less distortion. **No new physics, no new constant** (the §14
inverse-design "composed process" stance).

**The crux (advisor redirect):** martempering = **austempering's sibling** — *same* two-stage
path, differing only in **hold time** (austemper holds past the bainite reaction → bainite;
martemper holds short → martensite). So it is **built on 6d `austemper.py`'s atlas-anchored bainite
kinetics, NOT re-derived** from `cooling`/`pathint` primitives. 6d's docstring had already named
this seam ("at/below Mₛ … martempering, the same hold machinery, deliberately not built").

**The architecture-gating check, run BEFORE writing (advisor):** `transform_along_path`'s single
pearlite-calibrated curve labels sub-Bs product "bainite" but near Mₛ its τ≈∞ → a **toothless**
guard. The nose-avoidance guard MUST use 6d's **anchored** kinetics (`hold_time_to_fraction`),
which give a finite discriminating onset (1080 t_crit≈7767 s, 4340≈221 s at Mₛ+20) — pinned by
`test_guard_is_discriminating_not_toothless`. The durable lesson = the descoped 6b single-curve is
not a usable bainite guard; the 6d anchor is.

**Unification (advisor):** equivalence + nose-avoidance are ONE quantity — `critical_hold_time` =
bath bainite-onset = the martemper↔austemper boundary. Below it martemper ≡ `ideal_quench` (full
austenite→KM) **exact by construction conditional on nose-avoidance** (consistency leg, not a
benchmark). Empirically: 4340 (deep-hardener) ≡ real water quench *exactly*; 1080 marginally
*harder* than water (cleaner nose-miss than real water's ~5% bainite clip) — reported.

**Spatial payoff (advisor: don't ship 0-D-only — hollow):** distortion is inherently spatial.
`slab_thermal_history` marches a planar slab on the **frozen `engines/diffusion`** (heat mode,
symmetry `Neumann(0)` centreline, **two-stage Robin surface** — bath then air, swapped at t_hold
mid-march = the Jominy pattern, **no Strang splitting**). Reduction comes from **two steps, both
essential** (advisor): hold equalises below the nose + **slow cool** takes it through Mₛ near-uniformly
(Mₛ crossing is deep in the slow cool, not the hold). Surface−centre gradient at Mₛ: direct −40 °C vs
martemper −0.6 °C → **62× reduction** (resolution-converged 62.1→62.2× at 4×res), at **the
direct-quench hardness point-for-point** (NOT "fully through-hardened" — shallow 1080 won't harden a
20 mm centre in either route). Gradient = **thermal proxy** for distortion; **NO solid mechanics**
(true residual stress = the deferred §11 Option-#2 axis, untouched — don't conflate). Banked
`docs/figures/steel-martemper-distortion.png`.

**Feasibility teeth:** `τ_equalize < t_crit` (τ_equalize from the actual slab solve) — a **conservative
hold-side proxy** (the dominant real limit, outrunning the nose on the descent *to* the bath, is
idealised away with the instant quench-in). Illustrates the textbook limit — **4340's 40 mm plate
FAILS** (342 s > 221 s), 1080's passes; verdicts survive a fuller hold+slow-cool-dwell check
(4340 613>221 fail, 1080 795<7767 pass). Needs hardenability AND thinness.

**Named edges:** per-steel only (anchored 1080/4340 — the 6d cross-composition BC failure); t_crit
near Mₛ **optimistic** (unmodelled near-Mₛ bainite acceleration, a 6d edge → margins best-case); slow
final cool 0-D-immaterial **only near Mₛ** (a higher bath forms bainite the instant-KM misses; always
matters for the spatial gradient). No ADR (engine reused not modified);
`austemper`/`pathint`/`properties` + all frozen benchmarks byte-identical.

**Why:** records the non-obvious build shape so a later session doesn't re-derive martempering from
primitives or try to use the toothless single-curve as a bainite guard. **How to apply:** future
hold-route work builds on `austemper`'s anchored kinetics; the two-stage Robin slab on the frozen
engine is the reusable section-quench thermal seam. Remaining §11 menu = residual-stress (Option-#2,
real solid mechanics) + the unified-KV rebuild (6b deepening). Amends [[bainite-anchoring-probe]];
sibling of [[di-crosscheck-source]]/[[mixed-temper-next]] (the §14/§16 "no new physics" stance).
