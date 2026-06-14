---
name: carbon-carry-in-built
description: "F3 carbon carry-in (HC vs LC ferroalloys) BUILT 2026-06-14 — same trim, carbon grade decides off-grade-on-C + over-hard; no tooth"
metadata: 
  node_type: memory
  type: project
  originSessionId: 195e4ca5-c1a7-4ef8-bc26-4b4b03075a5f
---

**Carbon carry-in (the F3 ladle carbon deferral) BUILT ✓ 2026-06-14** — picked
from the consequence/flavor backlog menu (user chose it over peritectic-hot-tear
/ free-machining-S / themes C-E). Closes the deferral named in `steel-making.md`
§7 and scaffolded in `ladle.py` (`carbon_pickup_pct`, `Ferroalloy.carbon_fraction`):
makes the carry-in **real** and routes it through the validated back end.

**What was built.** `ladle.py` physics (default byte-identical): `LOW_CARBON_FERROALLOYS`
(same deliverers, identical assay/recovery so they **size the trim identically** —
only `carbon_fraction` differs: ~0.5 %C LC vs 6-8 %C HC); `mix(apply_carbon_pickup=False)`
opt-in carry-in (`Σ charge·carbon_fraction`, carbon recovered ~fully, no η — the mass
was already in `bath` as inert carrier, the flag only re-attributes it to carbon);
`carbon_pickup_pct`/`trim_to_grade` gain a `ferroalloys` selector. **Separate** demo
`demo_carbon_carry_in.py` + `plots.carbon_carry_in_figure` (2-panel) + gallery card
(notebook=None — NOT in making.ipynb) + README row + 13 tests. **816 fast green**,
no engine/ADR. Hero: one 4140 tap, ONE charge set — HC drags C ~+0.18 → **0.56 %C
off-grade-on-C + 702 HV**; LC stays 0.40 %C on grade, 628 HV. *Why LC ferroalloys exist.*

**Posture (advisor pre-write gate + the F3 spine-class doctrine): NO claimable tooth.**
Carry-in is mass-balance on cited assays (by-construction); **verdict = OFF_GRADE on
the C band through the EXISTING window machinery (no new flag)**; hardness rise is
propagation **colour** (validated back end consuming the carry-in), NOT a second
pass/fail line. The ~0.18 %C (~40-45 % of grade C) magnitude = OoM coherence note,
not a 2-sig-fig benchmark (assays are tier-2). Deox-state recovery + P/S bands stay
deferred. Don't reach for `QUENCH_CRACK_RISK` (fixed-4340, not composition-aware) to
dress the overshoot as a verdict.

**3 advisor / process catches, all load-bearing:**
1. **Spot-check the back end FIRST** (the repo's recurring lesson): ran `evaluate`
   at 0.56 %C BEFORE writing — 0.56 is well outside 4140's fit range. It returned
   sane/monotonic (702 vs 628 HV) → over-hard narrative holds. If it had clamped →
   fall back to OFF_GRADE-on-C as the sole consequence, build still stands.
2. **Over-hard, NOT soft-core** — higher C *lowers* martensite slightly (0.944→0.908,
   Ms-drop/retained-austenite) but it STAYS above the 0.90 spec, so the over-carbon
   heat is the over-hard FOIL to the recovery-shortfall soft core. A test pins
   `not hc.has_defect(SOFT_CORE)` so it can't silently mis-flag.
3. **Done-gate figure bug** (in the banked PNG): the carry-in arrow spanned the
   **bar-to-bar** delta (`hc_C-lc_C`=0.16, bath-diluted) but was labelled `+0.18`
   (`carbon_pickup_pct`, **heat_mass** basis). Two numbers, two bases. Fixed the
   arrow to its drawn length (0.16/~40 %); ~0.18 stays in prose where heat_mass is
   right. **DURABLE: an eyeball figure check confirms LAYOUT, not numbers-against-
   each-other** — measure the drawn artifact against its labels.

**Design call (tipped from the advisor's lean):** advisor leaned *extend `demo_ladle`*
(LadleDemo already had a `carbon_carry_in` field = design intent), but the ladle
figure is a **full 2×2** (all recovery story) with no room for a carbon panel → that
broke the tie toward a **separate** demo (which advisor called "defensible"). Carbon
grade is a **distinct** mistake from the recovery shortfall, matching the one-
consequence-one-demo pattern. "Separate not appended" was an apps/notebook rule, but
figure-full made separate the lower-friction *visible* path. 816-vs-829 fast count =
selection/skip artifact, not a dropped test.

Amends [[ladle-f3-built]]; sibling of the other backlog consequences; [[gallery-page]].
