---
name: mixed-temper-next
description: "steel-sim mixed-structure tempering (plan §16): steps 1-3 BUILT 2026-06-11; steps 4+ (design.py RA-guarded unlock) = what's next"
metadata: 
  node_type: memory
  type: project
  originSessionId: de815651-624e-4ad4-a0ce-d4922d12fd67
---

**Mixed-structure (per-constituent) tempering** — the named 3b deferral (temper a phase
*mixture*, not a fully-martensitic structure), plan **§16**. The §11 "smaller deferral" the user
picked over residual-stress / KV-pearlite rebuild.

**STEPS 1–3 BUILT ✓ 2026-06-11** (the validated core; no engine touch, no new calibrated constant —
a new function, so 2c/3a/3b/Jominy/four-curves + `tempered_martensite_HV`/`hardness_HV` stay
byte-identical; full suite **420 green** +2 env-skips):
- `properties.py` §6: `tempered_hardness_HV(fractions, C, T_temper, t_hours, comp, Vr, C_hj)` +
  `tempered_hardness_HRC` + `TEMPER_ACTIVE = frozenset({"martensite"})`. Rule of mixtures: martensite
  → `tempered_martensite_HV`; ferrite/pearlite/bainite/RA **temper-inert**, *delegating* to
  `CONSTITUENT_HV[name](C, comp, Vr)` (the *identical* call `hardness_HV` makes → byte-exact no-op).
  Unknown key raises (key-set = `CONSTITUENT_HV`, mirrors `hardness_HV`).
- `tempered_jominy_hardness` mirrors `jominy_hardness` (reuses `JominyHardness`), swaps in the
  tempered mixture. **The teeth.**
- Tests (`test_properties.py`): 3 exact **seams** asserted `==` (A mart=1→3b; B mart=0→`hardness_HV`;
  C sub-onset 120°C/1h, g=1→as-quenched) + monotone/bounded + differential-softening unit test +
  3 tempered-Jominy bracketing tests; `test_demo_tempered_jominy.py`. Figure
  `docs/figures/steel-tempered-jominy.png` via `demo_tempered_jominy.py` + `plots.tempered_jominy_figure`.

**Build facts that bit / matter (advisor-flagged, verified empirically):**
- **Figure in HV, not HRC** — the "far end barely moves" story is soft pearlite *below* the ~20 HRC
  E140 floor (HRC = nan there). Deliberate departure from `jominy_hardness_figure`.
- **Far-end byte-exact** holds because 1045 far end has martensite *exactly* 0.0 at 25.4 mm →
  `tj.HV[mart==0] == aq.HV[mart==0]` (Seam B along the bar). Test masks on `martensite==0.0`, not "far end".
- **Near end is NOT exactly 1.0 martensite** (KM leaves ~0.96, an RA sliver) → use the *band*
  (4140 400°C/1h = 41–49 HRC, 3b's validated response), **never** `==`, for the Jominy near end.
- **Tempered traverse is non-monotone in distance** even at 400°C/1h → do NOT assert monotonicity;
  the durable claim is the differential (`drop_near≈188 HV ≫ drop_far==0` for 1045 carbon-only).

**STEPS 4+ = WHAT'S NEXT (planned, not built):** `design.py` guarded unlock (relax
`_is_fully_martensitic` MARTENSITE_TEMPER_MIN, invert the mixed curve — still monotone in T so the
bisection transfers) **gated on a retained-austenite guard** (RA→bainite/fresh-martensite on temper
is non-monotone, can *raise* hardness; `design` *recommends* unlike Jominy which only *reports*, so
keep martensite-dominant/RA-capped, do NOT relax to "martensite>0") + **consciously re-derive §14**
(1045 10mm-water ~0.88M today-infeasible may become feasible-via-temper; the 45 HRC→4140-oil headline
can flip; design.py's own Phase-7 tests expected to change — NOT a frozen-benchmark violation) +
surfaces + close-out. `bainite`/RA-inert are **named, not validated** (cited for pearlite). See plan §16.
