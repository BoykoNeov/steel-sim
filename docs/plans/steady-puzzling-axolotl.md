# Phase 7 — Inverse design / recipe selection

> Promoted from `steel-production.md` §11 item 4 (the "inverse design capstone",
> `[available]`). Chosen 2026-06-10.

## Context

Steel's forward model is complete and heavily validated (Phases 1–6 + the §9
experimentation surface): *composition × quench × temper → microstructure →
hardness*. Every existing surface runs that model **forwards**. The capstone
flips it: **target a property, get a recipe**. Given a hardness spec for a
section of a given size, search the real-grade × quench × temper space for
recipes that meet it — the engineer's actual question ("what steel and heat
treatment gives me 45 HRC at this size, as cheaply as possible?").

Per the program doctrine (§11) this is an **optimization/UX layer over the
existing `sweep` harness — no new core physics, no new calibrated constant**. It
inherits the exact posture of `sweep.py`: *pure re-composition of validated
modules, so it has **no physics triad of its own** — its tests are
harness-correctness* (advisor-confirmed; see "Validation" below).

## The shape of the inverse (advisor-shaped)

**Outer discrete enumeration × inner continuous temper root-find.**

- **Outer (discrete, enumerated):** grade ∈ `sweep.STEELS` × medium ∈
  `sweep.DEFAULT_MEDIA`, at a **given** section `diameter` (the part geometry is
  a *constraint*, not a swept axis). Staying on the `STEELS` registry is the
  **non-circularity win, not a limitation**: a continuous-composition optimizer
  would wander into `Mn=0` "leaner-hypothetical" steels that `ccurve_for_steel`
  explicitly warns about and no benchmark covers. Frame the phase as **recipe
  selection / what-if inversion**, not "optimization over composition space".
- **Inner (continuous, root-found):** the temper axis is the *one genuinely
  invertible core*. `properties.tempered_martensite_HV` is strictly
  monotone-decreasing in the Hollomon–Jaffe parameter `P` (hence in temper `T`
  at fixed `t`), with achievable range `[HV_floor, HV_aq]`. So "what temper `T`
  hits the target hardness for this quenched grade?" has a **unique** solution →
  solve by **bisection**, giving an *exact* temper recommendation and the
  phase's only test with real solver content. The temper branch applies **only
  to a fully-martensitic as-quenched candidate** (the validated martensite-only
  temper scope); a mixed/pearlitic candidate is judged as-quenched only.

Per outer (grade, medium) candidate at the fixed diameter:
1. As-quenched `Outcome = sweep.evaluate(steel, medium, diameter)` → `HV`.
2. If as-quenched `HV` is in the target band → **feasible**, `temper=None`.
3. Else if as-quenched is fully martensitic **and** the band lies within
   `[HV_floor, HV_aq]` → **bisect** temper `T` for the band centre → **feasible**,
   `temper=T`. (Target above `HV_aq` ⇒ can't temper *up*; below `HV_floor` ⇒
   below the spheroidite floor — both are honest **infeasible**, the bracketing
   failure surfaced, never a silent nearest-miss.)
4. Else **infeasible** at this (grade, medium).

**The feasible *set* is the deliverable.** Every returned recipe is
**re-evaluated through the forward model** and asserted in-band. The
cost-sorted "recommended recipe" is **labelled sugar, not a claim**: a
transparent convenience sort (leaner alloy + milder quench + no/less temper
preferred = the real "cheapest steel, gentlest quench that hits spec" logic),
explicitly *not* validation (the demonstration-vs-teeth discipline).

## Honest edges (inherited / named, the project signature)

- **Diameter = 0-D *bulk* hardness of a section** (section size enters only
  through cooling rate in the lumped cooler) — **not** a radial profile. The
  centre-of-a-round-bar story is Phase-6c's `D_c`; one docstring sentence settles
  it, no conflation.
- **Biot validity propagates:** a feasible recipe that needs a water quench of a
  thick section carries `Outcome.lumped_valid = False` (flagged, not hidden).
- **HV is the internal currency** (defined everywhere); HRC is the boundary unit
  (`nan` below ~20 HRC). The API targets **HV**; the surface accepts an HRC
  target via a new `properties.rockwell_c_to_vickers` (the monotone-interp
  inverse of the existing `vickers_to_rockwell_c`, `nan` outside ~20–67 HRC).
- **Temper is martensite-only** (the validated scope) — the temper branch fires
  only for fully-martensitic candidates.

## Validation — harness-correctness, **NOT a physics triad** (advisor, load-bearing)

Like `sweep.py`, this phase invents no physics, so it has **no triad of its
own**. The tests check *solver/plumbing* correctness. The categories, honestly
labelled:

- **Lead invariant (the strongest assertion — open the test file with it):**
  *no returned recipe ever re-evaluates out-of-band.* Every recipe in the
  feasible set, re-run through `sweep.evaluate` (as-quenched) or
  `tempered_martensite_HV` (tempered), lands in `[target − tol, target + tol]`.
- **Temper root-find correctness (the only test with real solver content):** the
  bisection recovers an interior target to tolerance for a martensitic grade,
  **and** correctly reports infeasible (bracketing failure) for a target above
  as-quenched or below the floor.
- **Infeasible is first-class:** an out-of-envelope target (e.g. 65 HRC bulk
  hardness of a thick furnace-cooled section) returns an **empty** feasible set,
  not a nearest miss.
- **Round-trip wiring check — labelled by-construction, NOT teeth:** a registry
  recipe's own forward hardness is recoverable from the grid. Status: passes by
  construction (the Phase-4 "pinned-invariant / wiring-check" status), kept as a
  smoke test, *not* dressed as a benchmark.
- **End-to-end sanity — consistency, NOT teeth:** a deep-section hardening target
  yields a feasible set that ranks alloy grades (4140) above plain-carbon (1045)
  — by construction from the forward model (which already encodes 4140's
  hardenability), a plumbing sanity, explicitly not a falsifiable result.

## Scope ceiling & deferrals (named)

- **Hardness-only target in v1.** Yield is incoherent as a co-target:
  `grain.coupled_grain_properties` returns `nan` yield for martensitic
  structures — exactly the high-hardness regime an inverse-hardness search
  returns — so hardness and yield can't share a recipe. **Yield-target
  inversion** (FP/slow-cool regime) and **case-depth inversion** (carburize — a
  *different process axis*) are named as separate future inversions, not v1 knobs.
- **No continuous-composition optimization** (the `Mn=0` trap) — registry grades only.
- **No new solver / no engine touch / `pathint`/`kinetics` byte-identical** —
  pure re-composition; every frozen benchmark unchanged.

## Files

**Slice A — the headless harness + banked artifact (the core):**
- `steel/design.py` *(new)* — `Recipe` + `DesignResult` dataclasses;
  `find_recipes(target_HV, tol_HV, diameter, grades=…, media=…, t_hours=1.0)`
  (outer enumeration); `_temper_to_target(...)` (inner bisection over
  `properties.tempered_martensite_HV`); `_recipe_cost(...)` (the labelled sort
  key). Reuses `sweep.evaluate`/`Steel`/`STEELS`/`DEFAULT_MEDIA`,
  `properties.{tempered_martensite_HV, vickers_martensite, vickers_ferrite_pearlite,
  vickers_to_rockwell_c}`.
- `steel/properties.py` — add `rockwell_c_to_vickers` (the symmetric inverse of
  `vickers_to_rockwell_c`, lines ~337–356; monotone `np.interp` over the same
  `_E140` table, `nan` outside band). Small, reuse-driven, additive.
- `steel/plots.py` — add `design_figure(result)`: the grade × medium feasibility
  map (cells annotated with achieved/tempered hardness, the target band
  highlighted, the recommended recipe called out). Render-layer only, invents no
  physics (ADR 0002) — mirrors `sweep_comparison_figure` (plots.py:482).
- `steel/demo_design.py` *(new)* — `compute()/print_summary()/save_figure()/main()`
  (the `demo_grain.py` pattern), banking `docs/figures/steel-design.png`. A
  concrete worked spec, e.g. "≈ 45 HRC bulk in a 30 mm section" → the feasible
  recipes + the recommended one.
- `steel/tests/test_design.py` *(new)* — the harness-correctness tests above
  (lead with the no-out-of-band invariant).
- `steel/tests/test_demo_design.py` *(new)* — the demo smoke test (compute +
  figure build under `[viz]`), the `test_demo_grain.py` pattern.

**Slice B — the thin-skin surfaces (the UX, the inverse-design payoff made interactive):**
- `steel/app.py` — a **§7 Design** section: matplotlib/streamlit-free
  `design_outcome(...)` + `design_readout(...)` helpers (the always-green
  `grain_outcome`/`grain_readout` pattern, app.py:262) + paper-thin `main()`
  wiring (target HRC slider + section-size slider → the feasible-recipe table +
  the recommended recipe + the `design_figure`).
- `steel/tests/test_app.py` — always-green helper tests + a `[viz]`-gated figure
  build (the existing app-test discipline).
- `steel/steel.ipynb` — a **§7 Design** narrative cell (thin skin, direct
  compute call + `interact` sugar, the slice-1 discipline).
- `docs/plans/steel-production.md` — record **Phase 7 as-built** in §13/§11 (per
  program invariant 6, doc updates are part of every change).

## Verification

- `./run_tests.ps1` (or `pytest -q steel/tests/test_design.py`) — the new
  harness-correctness suite green; full not-slow gate still green (no frozen
  benchmark moved — assert `pathint`/`kinetics`/four-curves/Jominy unchanged).
- `python -m steel.demo_design` — prints the feasible recipes + recommended one
  and saves `docs/figures/steel-design.png` (under `.[viz]`).
- `streamlit run steel/app.py` — the §7 Design section drives the target sliders
  end-to-end (Slice B); `python steel/app.py` reaches `import streamlit` only in
  `main()` (the existing top-level-script guard).
- Spot-check the inverse against the forward model by hand: pick the recommended
  recipe, run `sweep.evaluate` (+ temper) on it, confirm the hardness matches the
  target band — the same round-trip the lead test automates.
