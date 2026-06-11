---
name: di-crosscheck-source
description: Steel Phase 6c D_I/measured-Jominy cross-check — the cited sources + the build-as-built record
metadata: 
  node_type: memory
  type: reference
  originSessionId: a3c74f36-8dbc-41c7-8fc3-f414d2c0c9e2
---

Steel **Phase 6c — the D_I (ideal critical diameter) / measured-Jominy cross-check** BUILT
2026-06-10 (`projects/steel/ideal_diameter.py` + `demo_ideal_diameter.py` + `plots.ideal_diameter_figure`
→ `docs/figures/steel-ideal-diameter.png` + `tests/test_ideal_diameter.py` 13 + `test_demo_ideal_diameter.py` 2;
**+15 tests → 354 lineage / 333 green headless**; no engine change, `pathint`/`kinetics` byte-identical).
Completes Phase 6 (6a✓/6b✓-descoped/6d✓/6c✓). Closes the Jominy chain's one un-checked leg: the
**absolute depth of hardening** (every 2a–2c/6a calibration anchored its own data, never D_I).

**The teeth caveat → the source decision (durable).** Benchmark must be **measured**, NOT
Grossmann-computed — the model's hardenability rides Grossmann *relative potencies* ([[maynier-hardness-source]]
is separate; the Grossmann factor lives in `kinetics.GROSSMANN_B`/`HARDENABILITY_SCALE`), so a
Grossmann D_I = base×multiplying-factors would be a tautology. **The 6d-probe's atlas-E-Q-panel
candidate ([[bainite-anchoring-probe]]) was CHECKED AND DROPPED**: the US Steel 1951 atlas is an
*isothermal-transformation* atlas — the plan's "4340 E-Q panel p.105" collided with `austemper.py`'s
already-cited 4340 *IT diagram* p.105 (the panels were speculative; advisor flagged the page collision).

**THE CONVERSION FIX (advisor catch — durable).** First pinned an **AI-extracted "SAE J406 Table A7
ideal-D_I"** (J16→2.97in); **DROPPED because the EXTRACTION was unreliable, NOT because J406's real
table is wrong** (never actually seen — fetch failed; the pdfcoffee text-extraction self-contradicted
across attempts: J8→2.97 then J8→1.75). The tell: extracted values fell on the EMJ **oil** column
(below water), IMPOSSIBLE for an ideal D_I (`D_I ≥ D_water ≥ D_oil` — severer quench through-hardens a
bigger bar). The physics check `D_I ≥ D_water` flagged the bad extraction (every test was
A7-invariant/relative → blind to it; this is the one load-bearing absolute input). Lesson: **verify an
AI-extracted table against an independent directly-read source before baking absolute numbers into
docs** (attribute the failure to the extraction, not the cited source). Switched to:

**Cited sources pinned (`ideal_diameter.py`):**
- **EMJ Reference Book p.29** (directly READ from the PDF, not AI) — J (1/16 in) → centre-of-round
  diameter (inch) at equal hardness, **water** (the deeper reference, the reported `D_c`) + **oil**
  (bracket): water J2→0.6, J8→2.3, J16→3.9, J24→5.0, J32→5.6 in. `D_c` = water-quench centre-equivalent,
  a **lower bound on the ideal D_I**. Used ONLY as the conversion applied *identically* to model &
  measured curves, so its error **cancels** (advisor); the discrimination lives in J50.
- **SAE J406 Table A5 / Hodge–Orehoski 50 %-martensite hardness vs C**: 0.20→30, 0.30→37, 0.40→43,
  0.45→45, 0.50→47, 0.60→50 HRC. The measured side's J50 locator (**cited**, not the model's 50/50
  blend — the model must not grade its own benchmark; load-bearing: cited-30 puts 8620 in-band where
  the model's 35 would push it above).
- **SAE J1268** (Hardenability Bands for Carbon & Alloy H Steels, MAY2010) — **1045H exact tabulated**
  (Fig.4, read from the preview PDF); **4140H J8=42-54** + **8620H J4=27-41** (confirmed callouts).
  Also carries the full composition tables (Tables 1/2) for all H-grades.
- **EMJ Reference Book** (Earle M. Jorgensen, Mech. Properties & Hardenability) — band *charts* for
  4340 (p.17), 4142≈4140 (p.15), 8620 (p.23) read off.

**Method (standard, both ways):** model J50 from `fM=0.5` (isolates hardenability from the 2c
hardness map — clean headline); measured J50 where the band crosses cited h50(C); both → D_c via EMJ p.29.

**Result (read the SHAPE, not "within X%"):** (1) **ranking correct** — model D_c 1045 35 < 8620 51 <
4140 104 < 4340 119 mm (alloy beats carbon = headline; an H-band is a *wide* envelope so "in band" is
weak teeth); (2) **4340 UNDER-predicted** — model at/below the measured band's low edge (~132mm),
upper edge off the standard bar (EMJ p.29 tops J32≈142mm); Cr-Mo-(4140)-calibrated scale under-captures
4340's **Ni** potency = strongest non-circular result; (3) directional bias — shallow grades (1045,
8620) ride high through the knee (knee + low-C hardness-map, not pure hardenability). **Circularity
roles:** 4140=**anchor** (HARDENABILITY_SCALE set to its nose → in-band by construction, NOT teeth);
4340+8620=**teeth**; 1045=**edge** (documented ~2-3mm knee, [[ferrite-bay-source]]). 4340 added
**benchmark-local** (not `sweep.STEELS`/app — advisor). Engine is Cartesian-only (no radial round-bar
sim) and none needed — SAE J406 Jominy↔diameter equivalence IS how D_I is got from end-quench data.
