# Next directions — the forward menu once the named backlog closed

> **Status: catalogue (2026-06-15).** The steel-making front half (F1–F4), the
> make→break→heat-treat triptych, the post-triptych consequence/foil modules, the
> back-half Phases 1–7, and the `steel-production.md` §11 menu are all **built**.
> Wootz banding (`fca1ed8`) closed the one named front-end *physics* gap. So
> "what's next" is no longer a deferral to pick up — it is a direction to choose.
> This file records the candidate directions (the ones the older plans already
> discuss, plus new ones) with an honest size + status per entry, so the choice is
> made against a written menu rather than re-derived each session. It is a
> **catalogue, not a build plan**: a chosen direction still gets its own short plan,
> its own validation triad, and the validated-vs-calibrated discipline.

---

## A. Already discussed in the older plans

### A1. The `game/` historical-methods spinoff — the big named direction
`steel-making.md` §8 + §15 spec a gamified layer where each historical/modern
steelmaking method is a **preset recipe over the F1–F4 engines** behind a firewall
(`game/` orchestrates, never reimplements physics). The method→engine map is
already written (§15.2): bloomery, blast furnace, finery/puddling, cementation,
crucible, wootz, acid Bessemer, Thomas, open hearth, BOF, EAF, ladle, continuous
casting — each a `Heat` recipe + the set of §6 flags it can fire + a per-field
**verified-vs-flavor** label. **Both §15.4 physics gaps are now closed** (P/S slag
partition; wootz V/Mo banding), so this is fully grounded — orchestration + UX, no
physics left to invent. **Size: large.** **Status: unstarted** (no `game/` dir).
The repo-split is deferred; the in-repo `game/` home was authorized.

### A2. P → DBTT slope — the one still-unpinned *physics* piece
`steel-making.md` §14.5 flags it: the P→strength axis carries teeth (Thiele–Hošek,
+237 MPa/at%), but `grain.cottrell_petch_dbtt_C`'s P→ductile-brittle-transition
slope (`ITT_K_P`) is **representative, not pinned** — clean relations use
grain-boundary-segregation at%, not bulk wt%. Candidate sources are located (one
medieval-bloomery Charpy PDF needs a working mirror). **Size: small, self-contained
sourcing + calibration.** **Status: research record, assess-only.**

### A3. Yield- / case-depth inversion — Phase 7 v2 → **IN PROGRESS (2026-06-15)**
Inverse design (`design.py`) shipped **hardness-only**; the §14 as-built record
names yield-target and case-depth inversions as separate future inversions (yield
is `nan` in the martensitic regime an inverse-hardness search returns, so it cannot
share a recipe). **This is the direction being built now** — an optimization/UX
layer over already-validated forward models, **no new physics**:
- **Yield inversion** lives in `design.py` (it fits the outer-enumerate ×
  inner-bisect shape), but in the **ferrite-pearlite slow-cool regime** where yield
  is defined: enumerate grade, bisect the austenitizing temperature (monotone:
  hotter → coarser grain → lower yield) over `grain.coupled_grain_properties`. A
  yield recipe is *grade + austenitize T/t under normalized cool* — **no quench
  medium, no temper, no Biot** (a separate recipe space from the hardness search).
- **Case-depth inversion** lives in `carburize.py` next to `analytic_case_depth`:
  a **closed-form** inverse of `x = 2·erfc⁻¹(r)·√(Dt)` (time-at-T, and T-at-t via
  Arrhenius inversion). The D(C) Tibbetts leg is not closed-form invertible (named
  ceiling); a hardness-based effective case depth would couple back into the quench
  model (named extension). **Size: small.**

### A4. The §11 four-option menu — fully consumed
Grain/Hall–Petch (Phase 5), residual-stress & distortion (§18), the KV/bainite-bay
deepening (§19), and inverse design (Phase 7) are all built. **Nothing left here.**

---

## B. New directions (not in the older plans)

### B1. Fracture-side coupling — the one genuine *new-physics* thread
`steel-making.md` §14.5 gestures at it without scoping it: a P/S **inclusion as the
stress concentrator** that turns §18's sub-critical residual-stress field into an
actual quench crack. This would couple the two existing axes — impurity inclusions
(`slag`/`sulfide_morphology`) and the residual-stress profile (§18) — into a
**fracture-initiation criterion** (a linear-elastic-fracture-mechanics or
critical-flaw-size gate). It is the one direction here that needs *new* cited
physics and its own validation triad. **Size: medium–large.** **Status: discussed,
unscoped** (the user's stated interest as of 2026-06-15).

### B2. Full-chain capstone — ore→billet→part in one narrated run
The apps and notebooks are currently split front (`making`) / back (heat-treat). A
single capstone run/notebook that threads one `Heat` from reduction through casting,
refining, ladle trim, and heat treatment to a finished part would make the
front-meets-back seam concrete. **Integration + pedagogy, no new physics.** **Size:
small–medium.** **Status: idea.**

### B3. Front-end validation deepening
Replicate the §20 bainite cross-composition validation pattern (`cct_validation.py`)
for the front end — benchmark F2 dephosphorization/desulfurization (Healy L_P,
sulfide-capacity L_S) across more measured heats, turning "benchmarked physics" into
a holdout-validated claim. **Size: medium.** **Status: idea.**

---

## C. Program horizon (different repo)
The ADRs (`docs/decisions/`) reference the program build order **Steel → Microchip →
Planet**. **Microchip** (project #2) and then **Planet** (#3) are the next
*simulators* — "something new entirely" at program scale, but outside this repo. The
per-project test gate (ADR 0003) is explicitly scheduled to land *after* Microchip.
