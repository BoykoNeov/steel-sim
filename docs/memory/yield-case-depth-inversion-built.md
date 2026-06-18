---
name: yield-case-depth-inversion-built
description: Phase 7 v2 — yield-target + case-depth inversions BUILT 2026-06-15; regime/module separation was the crux
metadata: 
  node_type: memory
  type: project
  originSessionId: 957874eb-3f07-4bd2-80e4-d3a2e9be1822
---

**Phase 7 v2 — the yield-target + case-depth inversions BUILT ✓ 2026-06-15**, the two
"future inversions" the v1 hardness-only scope ceiling named. **No new physics** (each
inverts an already-validated forward model; same harness-only posture as
[[di-crosscheck-source]]/sweep — tests check the SOLVER, not metallurgy). +12 solver
tests / +2 demo tests; full suite **932 green / 2 skipped**. No engine touch, no ADR,
no new source. Catalogued in `docs/plans/next-directions.md` §A3.

- **Yield inversion → `design.find_yield_recipes`** (+ `YieldRecipe`/`YieldDesignResult`
  + `_austenitize_to_yield`). Fits `design.py`'s outer-enumerate × inner-bisect shape but
  in the **ferrite-pearlite slow-cool regime where yield is defined**: enumerate grade,
  bisect the **austenitizing T** (monotone — hotter → coarser PAGS → coarser ferrite →
  lower yield) over `grain.coupled_grain_properties`. A `YieldRecipe` is *grade +
  austenitize T/t under a normalized cool* — **no quench medium, no temper, no Biot**.
  Cooling rate is NOT a knob (baked into calibrated `grain.FERRITE_PAGS_RATIO`). Carries
  the **DBTT co-property** for free (the §5b foil — grain refinement raises yield AND
  lowers DBTT; demo shows 1045 hits 370 MPa at +80 °C DBTT vs alloyed 8620 same yield at
  −35 °C, the toughness the alloy-cost sort ignores).
- **Case-depth inversion → `carburize.carburize_time_for_case_depth` /
  `…_temperature_for_case_depth`**. Lives in `carburize.py` next to its forward
  `analytic_case_depth` — a **closed-form** inverse of `x = 2·erfc⁻¹(r)·√(Dt)` (time-at-T,
  or T-at-t via Arrhenius inversion). Round-trip recovers target to **machine precision**.
  Ceilings: **D(C) Tibbetts not closed-form invertible**; **hardness-based** case depth
  would couple back to the quench model. `r∉(0,1)`→`nan`; out-of-window T surfaced.
  Review hardening (`400ce0b`, 2026-06-15): two advisor-flagged gaps closed by tests only
  (no source change) — round-trip at a **non-default carbon span** (proves any erfc level
  set `r`, not just 0.8/0.2/0.4) + a **surface-don't-clamp guard** (out-of-window T is
  finite + unclamped both directions). Suite 932→**958 green**. Inverse correctness =
  forward-anchored (`test_numeric_case_depth_matches_closed_form`) + round-trip-consistent.

**Why:** The advisor's load-bearing catch was **regime + module separation**: (1) yield is
`nan` in the martensitic regime the hardness search returns, so it is a SEPARATE recipe
space, not a co-target — do NOT reuse `Recipe`/`DesignResult`, and a test asserts
`YieldRecipe` carries no `medium`/`temper_C`/`biot` (the conflation guard). (2) Case-depth
does NOT fit `design.py`'s mold (no grade enum, reuses none of its machinery) → it belongs
next to `analytic_case_depth`, NOT forced into the enumeration shape.

**How to apply:** When inverting a forward model here, first ask *which regime/process axis
is the property defined in* — a different regime means a different recipe dataclass and
often a different module. Invert the validated/closed-form leg only and NAME what stays
un-invertible (D(C), hardness-based case depth) as a ceiling. Amends [[steel-grain-physics-deferred]]
(Phase 5 yield) and the Phase-7 record; sibling of [[carburize-diffusivity-source]].
