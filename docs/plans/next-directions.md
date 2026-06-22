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
physics left to invent. **Size: large.** **Status: build plan written (2026-06-21)
→ `docs/plans/game.md`; Slices 0 AND 1 BUILT ✓ 2026-06-21.** Slice 0 stood the
`game/` package up (the B2 capstone chain made playable behind the F2 blow-endpoint
knob, the immutable-`Heat` turn surface, educational why-cards, the structural tests;
the one engine touch was promoting `demo_capstone`'s casting re-base to the public
`casting.cast_billet_onto` seam). **Slice 1 = the gauntlet** (scope widened from the
plan's "deox knob" by the user): **every stage a decision** (a `Recipe` choices vector
+ `choices.py` option tables + `postmortem.py`, the sealed consequence engines judging
the finished part), with **losability** as the acceptance bar — seven losable knobs
(decarb, dephos, deoxidizer-choice, degas, desulf-via-cleanliness-spec, carbon-pickup,
quench), one test each; casting an honest no-loss pass-through (no pass/fail lever on
4140). Slices 2+ (the method/era tech tree, economy) remain. The repo-split is
deferred; the in-repo `game/` home was authorized.

### A2. P → DBTT slope — **Outcome A BUILT ✓ 2026-06-22**
`steel-making.md` §14.5 flagged it: the P→strength axis carries teeth (Thiele–Hošek,
+237 MPa/at%), but `grain.cottrell_petch_dbtt_C`'s P→ductile-brittle-transition
slope (`ITT_K_P`) was **representative, not pinned**. **The sourcing gate was run
(2026-06-22) and the slope CANNOT earn teeth** — the bulk-wt% slope is a
path-dependent *reduced form* of grain-boundary *coverage* physics (the clean
teeth-bearing form is GB at% → DBTT, Song 2011, via a McLean isotherm). **Outcome A
(chosen over the new-physics B-escalation):** keep `ITT_K_P` a *flagged* bulk
coefficient but make it **traceable** — re-pinned 500 → **600 °C/wt%** (≈ 60 °C/0.1
wt%), the centre of a documented bracket ≈ 40–78 °C/0.1 wt% (upper anchor 7–7.8 °C/
0.01 % P, IDOT PRR-174). Bloomery PDF assessed (RT-only + slag-confounded, unusable);
the **McLean GB-coverage model (B) remains deferred** as new physics with its own
triad. One constant + its test band + §14.5; no engine semantics change, no ADR.
**Size: small (as filed).** **Status: BUILT (Outcome A); B-escalation deferred.**

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

### B1. Fracture-side coupling — the one genuine *new-physics* thread — **BUILT ✓ 2026-06-20**
`steel-making.md` §14.5 gestured at it: a P/S **inclusion as the stress
concentrator** that turns §18's sub-critical residual-stress field into an actual
quench crack. It coupled the two existing axes — impurity inclusions
(`slag`/`sulfide_morphology`) and the residual-stress profile (§18) — into a
**fracture-initiation criterion** (Murakami √area vs as-quenched K_Ic, a two-tier
`quench-crack-risk`→`quench-crack` gate). The advisor crux was a **phase-split
yield** (the uniform-raise was falsified by experiment); √area is a *representative*
input (the slag/sulfide-morphology bridge is a named deferral). **Size: medium.**
**Status: BUILT** — no tooth (sign-reversal + martemper consumed from residual).

### B2. Full-chain capstone — ore→billet→part in one narrated run — **BUILT ✓ 2026-06-21**
The apps and notebooks were split front (`making`) / back (heat-treat), and even within `app_making`
each stage was shown **independently** (every stage started from its own fresh origin —
`refining.from_hot_metal` preloads the alloys, `ladle.from_tap` is a separate lean origin,
`casting.cast_billet` emits fresh-trail heats — so nothing ever threaded **one** `Heat` end to end).
**Status: BUILT** (`demo_capstone.py` + `plots.capstone_figure` + 9 tests; gallery entry; no engine
touch, no ADR). One `Heat` is threaded the whole way — hot-metal charge → decarburize → dephosphorize →
deoxidize → degas → desulfurize → trim to grade → cast → quench — on a **single, un-rewritten provenance
trail**. Two heats take the identical chain and differ by a **single knob**, the F2 blow endpoint: the
reference (blown to the grade carbon) lands a **sound** part (on grade, through-hardened, the seeded tramp
P/S driven below spec end to end); the over-blown foil (0.25 %C) is wrong from the blow, caught
**off-grade** at the trim, and **soft-cores** at the quench — the longest propagation in the repo, one
mistake surfaced two stages apart. **Integration + pedagogy, no new physics** — the spine's posture
(structural teeth: continuous trail, ordered field-fill, cross-chain propagation; the reference clears
every sealed-engine spec). The lone front-end seam that takes a `Steel` (casting) is **re-based** onto the
`Heat` via `evolve` (Option A, demo-local; **promotion trigger** = a second surface needing the same glue
→ promote to a `Heat`-consuming casting seam). **Notebook section (slice 2) — BUILT ✓ 2026-06-21**
(`14a55b5`): a static banked `## §capstone` section in `making.ipynb`, placed as the make-arc finale
(between §F4b solidification and the "what goes wrong" pivot) and reusing `demo_capstone.compute` /
`print_summary` verbatim (the inverted-verdict landmine class). The surgical op added 2 cells and edited
2 markdown cells (the section-index table row + an epilogue scope note), leaving 57 of the 59 originals
byte-identical (content-hash proven); gallery `notebook="§capstone"` + both READMEs wired. The promotion
trigger was **not** tripped — the notebook calls `compute()`, so the casting re-base stays inside the
demo. **B2 is now fully closed.**

### B3. Front-end validation deepening — **BUILT ✓ 2026-06-20** (sulfide-capacity slice)
Replicate the §20 bainite cross-composition validation pattern (`cct_validation.py`)
for the front end — benchmark F2 dephosphorization/desulfurization (Healy L_P,
sulfide-capacity L_S) across more measured heats, turning "benchmarked physics" into
a holdout-validated claim. **Size: medium.** **Status: C_S slice BUILT** (`slag_validation.py`
+ `demo_slag_validation.py` + `plots.slag_validation_figure` + 15 tests; ADR 0006). Per the
advisor's "lead with C_S" steer, the Sosinsky–Sommerville sulfide-capacity correlation was
graded against an **independent measured dataset** — Nzotta–Sichen–Seetharaman, *ISIJ Int.* 38
(1998) 1170, Table 6 (Al₂O₃–CaO–MgO–SiO₂, measured after the 1986 fit, MnO/FeO-free so no
fitted Λ is in the loop; the open-access PDF is committed at `docs/sources/`). Verdict: the
model **carries** for basic slags (~×1.4, ×1.2 scatter, *exact* within-temperature ranking,
T-slope reproduced) — a *positive* out-of-sample result that upgraded `slag.py`'s C_S posture;
the **acidic** (Λ ≲ 0.6, ~×4 low) and **MnO** (~×5 high) edges are named, not tuned away. The
data-gate that deferred the scoping spike was cleared by getting the **primary source in hand**
(open-access tabular data, not figure-scraped). **Still open:** the Healy L_P leg (needs an
independent measured-partition dataset) and a second slag system beyond Al₂O₃–CaO–MgO–SiO₂.

---

## C. Program horizon (different repo)
The ADRs (`docs/decisions/`) reference the program build order **Steel → Microchip →
Planet**. **Microchip** (project #2) and then **Planet** (#3) are the next
*simulators* — "something new entirely" at program scale, but outside this repo. The
per-project test gate (ADR 0003) is explicitly scheduled to land *after* Microchip.
