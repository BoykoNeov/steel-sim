---
name: fracture-coupling-built
description: "B1 fracture-side coupling (inclusion as quench-crack initiator — residual×LEFM gate) BUILT 2026-06-20; the one genuine NEW-physics thread on the next-directions menu, user-picked"
metadata:
  node_type: memory
  type: project
---

**B1 FRACTURE-SIDE COUPLING — the inclusion as quench-crack initiator — BUILT ✓ 2026-06-20** (user picked B1
off [[next-directions-catalogue]], "the one genuine new-physics thread"). `steel/fracture.py` + `demo_fracture.py`
+ `plots.fracture_figure` + `tests/test_fracture.py` (13) + `residual.py` phase-split (+3 residual tests) +
`heat_state.QUENCH_CRACK` flag + gallery card + README row + `docs/plans/fracture-coupling.md`. **955 fast-lane
green.** Commit `feat(fracture)` on `main` (+ a prose-reconcile follow-up). Couples the two axes the repo
carried separately: §18 residual field ([[residual-stress]]) × a cleanliness flaw, joined by an LEFM gate.

**The gate (cited form):** Murakami small-defect `K = Y·σ·√(π·√area)`, **Y=0.65 surface** (0.50 interior),
crack when `K ≥ K_Ic`; equivalently critical flaw `√area_c = (1/π)(K_Ic/(Yσ))²`. **Two-factor AND** = surface
tension (σ>0, from residual) AND flaw > √area_c (cleanliness). **Two-tier flag** like
[[hydrogen-flaking-built]]: existing `quench-crack-risk` (residual, surface-in-tension = NECESSARY) → new
`quench-crack` (tension AND critical flaw = REALIZED). **Hero:** thick 4340 (ht=0.05, 100mm plate), one direct
quench, ONE surface tension (+1045 MPa) — clean heat (√area 30µm, 7.5× below a_c=224µm) survives, dirty heat
(√area 400µm, K=24 ≥ 18) **cracks**. SAME field, cleanliness decides → the load-bearing call (NOT a relabel of
`crack_risk`). Martemper collapses σ→−94 (a_c→∞) → saves it (§17/§18 in fracture); thermal-only = surface
compression → never cracks.

**THE CRUX = phase-split yield (the one real new mechanics).** At residual's DEFAULT single-yield cap (σ_Y,20
≈400 MPa) a_c is 1–35 mm → single inclusions NEVER critical → gate collapses to "never cracks". **Advisor
rescue #1 (uniform yield raise) FALSIFIED by my own experiment** — raising the yield base COLLAPSES the
residual to ~0 (residual needs plastic lock-in; a uniformly strong body stays elastic and relaxes; |σ_res|≤σ_Y).
**Surfaced the conflict → advisor refined: phase-SPLIT, not uniform** — soft austenite core (400, must yield to
GENERATE the eigenstrain mismatch) blended to hard martensite surface (`SIGMA_Y_MARTENSITE_20C=1500e6`, HOLDS
the tension) by the local `f_M`. Lifts residual.py's OWN named scope edge ("yield not phase-split → capped at
σ_Y,20"). **Verified: thick 4340 → 899–1045 MPa, a_c 155–373µm, clean/dirty straddle with margin.** Number is
**mismatch-limited NOT cap-limited** (1045 < 1500 martensite cap) = a genuine computed result. `phase_split_yield`
opt-in, default-preserving (all §18 teeth unchanged); fracture consumes `phase_split_yield=True`.

**NO claimable tooth (advisor-confirmed twice).** Sign-reversal + martemper benefit = CONSUMED from residual
(downstream of its formula sign), not new teeth (dressing them = manufactured-coherence trap). Carbon two-leg
(more C → lower K_Ic [worse] AND lower dilatation→less σ [better]) is the known "high-C cracks more" fact but
**not isolable** — only 2 atlas steels (1080 never even reaches surface tension; 4340 confounded by alloying).
Cited = LEFM + Murakami factor; **representative (named edges) = as-quenched K_Ic 18 (scatters, ∝K_Ic² sets the
absolute threshold), martensite-yield base, clean/dirty √area**; constants chosen so a_c lands BETWEEN clean/dirty
(named, not hidden). Checks = structural/discriminating (straddle, martemper-raises-a_c monotone, tension-required,
K↔a_c self-consistent).

**DURABLE advisor catch (final review, BLOCKING): prose oversold the coupling.** `fracture.py` does NOT import
`slag`/`sulfide_morphology` — **√area is a free representative scalar input**, yet docstring/plan/README claimed
it "couples the inclusion/cleanliness axis (slag/sulfide_morphology)". In this prose-obsessive repo that reads as
overselling the user's charter line. **Fix = reconcile prose to the choice, NOT undo it** (advisor): √area named a
**representative cleanliness input**; the inclusion-model bridge a **NAMED DEFERRAL** — and deliberately not faked
because **bulk vol% ≠ largest-flaw √area** and scales don't line up (micro-inclusions ~10–50µm vs the
discriminating √area = hundreds of µm = clusters/exogenous/segregated colonies); a derived vol%→√area would be
TUNED not physical. Lesson: when a module's headline is "couple axis A × axis B", grep for the `import` — if B is
a passed knob, say so. **Ceilings:** surface-initiated only (interior/core-tension bursting separate), atlas-steel
(4340) only, one flaw per heat (not extreme-value), static LEFM, cleanliness-not-wired (the deferral).

Amends [[residual-stress]] (now has phase-split + a fracture consumer); sibling no-tooth posture of
[[sulfide-morphology-built]]/[[wootz-banding-built]]; closes B1 on [[next-directions-catalogue]] (B1→BUILT).
**Next forward menu** = A1 `game/` spinoff (large, all physics gaps closed), A2 P→DBTT slope (small), B2 full-chain
capstone, B3 front-end validation deepening.
