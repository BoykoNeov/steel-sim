# B1 — Fracture-side coupling (the inclusion as quench-crack initiator)

> **Status: as-built plan (2026-06-20).** The one genuine *new-physics* thread on the
> `next-directions.md` menu (B1). It couples the two axes the repo already carries —
> the **residual-stress field** (§18, `residual.py`) and the **inclusion/cleanliness**
> axis (`slag` / `sulfide_morphology`) — into a **linear-elastic-fracture-mechanics
> (LEFM) quench-crack gate**. This is the direction the user picked; it gets its own
> short plan, its own honest cited-vs-representative map, and the validated-vs-calibrated
> discipline, like every slice before it.

## The physics — an LEFM gate over the residual field

A pre-existing flaw of effective size √area, under a tensile stress σ, carries a stress
intensity (Murakami's small-defect form, surface defect):

    K = Y · σ · √(π · √area),     Y = 0.65 (surface), 0.50 (interior)

A crack runs when `K ≥ K_Ic` (the surface martensite's fracture toughness). Equivalently
there is a **critical flaw size**

    √area_c = (1/π) · (K_Ic / (Y·σ))²

below which the flaw is sub-critical (no crack) and above which it propagates. The gate is
therefore a **two-factor AND**: a quench crack needs **both** a tensile surface (σ > 0,
from the residual solve) **AND** a flaw larger than √area_c (from the cleanliness axis).

## The load-bearing design call — must NOT collapse to `residual.crack_risk`

`residual.crack_risk` (and `heat_state.quench_crack_check` → `quench-crack-risk`) already
return *surface in tension*. B1 only earns its keep if the **inclusion is load-bearing**:
the same residual field gives a crack for a dirty heat and no crack for a clean one. This
is the repo's **two-tier idiom** (cf. `hydrogen-flaking-RISK → hydrogen-flaking`):

* `quench-crack-risk` (existing) = surface tension — the *necessary* condition.
* `quench-crack` (new, this build) = tension **AND** largest flaw > √area_c — the realized crack.

**Hero (verified to exist before building):** thick 4340, direct water quench, *same*
section and hardness — a clean heat (√area ≈ 25 µm) survives while a dirty heat
(√area ≈ 300 µm) cracks. Martempering the same dirty part collapses the surface tension
(√area_c → ∞) and saves it — the §17/§18 route benefit extended into fracture.

## The stress-cap obstruction and its resolution (phase-split yield)

The deciding numbers (computed up front): at the residual engine's **default** surface
tensions (≤ ~400 MPa, capped at the representative yield) with realistic as-quenched
`K_Ic` (15–25 MPa√m), √area_c is **1–35 mm** — far above any inclusion, so single
inclusions are *never* critical and the gate would collapse to "never cracks".

The cap is `residual.py`'s **own named scope edge** ("yield not phase-split → surface
tension capped at σ_Y,20"). Lifting it is squarely B1's mandate. The fix is **phase-split
yield** (standard in real quench-residual FEM): soft austenite core (`SIGMA_Y_REF_20C`,
must yield to *generate* the eigenstrain mismatch) blended to a hard martensite surface
(`SIGMA_Y_MARTENSITE_20C ≈ 1.5 GPa`, *holds* the tension without yielding) by the local
martensite fraction `f_M`. **Verified:** thick 4340 then reaches 900–1045 MPa, √area_c
falls to 155–373 µm (K_Ic 15–20), and clean (25 µm) vs dirty (300 µm) straddle it with
margin. A uniform yield raise was tried first and **falsified** (it stiffens the hot core,
kills the mismatch generator, and the residual relaxes to ~0) — the split is the physical fix.

`residual.quench_residual_stress(..., phase_split_yield=True)` is opt-in; the default path
and all existing §18 teeth are untouched.

## Cited vs representative vs NOT a tooth (the discipline)

* **CITED (the load-bearing form).** The LEFM relation `K = Y·σ·√(πa)` (Anderson, *Fracture
  Mechanics*); Murakami's √area small-defect model and the surface/interior geometry factors
  `Y = 0.65 / 0.50` (Murakami, *Metal Fatigue: Effects of Small Defects and Nonmetallic
  Inclusions*, 2002); the **form** "K_Ic falls as hardness/strength rises" for high-strength
  martensitic steel.
* **REPRESENTATIVE (named scope edges, NOT benchmarked).** The as-quenched martensite
  `K_Ic` magnitude (notoriously scattered — temper, PAGS, impurities all move it ±); the
  hard-martensite yield base (1.5 GPa, same status as σ_Y,20); the clean/dirty √area
  population sizes. The **absolute** crack/no-crack threshold is doubly property-sensitive
  (σ capped at the representative martensite yield; √area_c ∝ K_Ic²) — it is **not**
  benchmarkable, and the representative constants are chosen so √area_c lands *between* the
  clean and dirty inclusion sizes. That is what makes the coupling *discriminate*; it is
  named, not hidden.
* **NO claimable tooth (confirmed twice with the advisor).** The surface-sign reversal and
  the martemper benefit are **consumed from `residual.py`**, downstream of its formula sign —
  not new teeth (dressing them as such is the manufactured-coherence trap). The one *candidate*
  real tooth — the emergent **carbon ranking** (more C → lower K_Ic [worse] *and* lower
  dilatation → less σ [better]; net?) — is **not isolable**: only two atlas steels exist
  (1080 / 4340) and they differ in alloying and section, so the two legs cannot be separated.
  Default **no tooth**, like the `sulfide_morphology` / `wootz` siblings. The checks are
  **structural / discriminating**: the two-factor straddle, the martemper-raises-√area_c
  monotonicity, tension-required, and `√area_c = (K_Ic/(Yσ))²/π` self-consistency.

## Named ceilings (each a real limit, not hidden)

* **Surface-initiated only.** The gate reads the *surface* tension against a *surface*
  geometry factor (Y = 0.65). Interior bursting / core-tension flaws (the thermal-only or
  martemper case puts tension at the **core**) are a separate problem — **not** modelled.
* **Atlas-steel-only.** Inherits `residual.py`'s name-keyed guard (1080 / 4340). An
  arbitrary off-spec composition → crack chain stays deferred (same bound as
  `heat_state.quench_crack_check`).
* **One representative flaw per heat, not an extreme-value distribution.** √area is taken as
  a single representative "largest surface inclusion" for the cleanliness class, not drawn
  from a Murakami extreme-value statistics-of-extremes fit over a control volume.
* **Static LEFM, no R-curve / no short-crack / no residual-stress redistribution on cracking.**
  A one-shot initiation criterion, not a propagation simulation.

## Deliverables

1. `residual.py` — optional `phase_split_yield` (**done**, default-preserving).
2. `steel/fracture.py` — the LEFM gate: `murakami_K`, `critical_flaw_size`,
   `QuenchCrackAssessment`, `quench_crack_fracture(...)`, and a `Heat` seam
   `fracture_check(...)` raising the new `QUENCH_CRACK` flag.
3. `demo_fracture.py` — the clean-vs-dirty hero on thick 4340 + martemper-saves.
4. `tests/test_fracture.py` — structural / discriminating checks (no benchmark).
5. `gallery.py` CATALOG entry + regenerate `docs/index.html`.
6. Memory doc + commit + push.
