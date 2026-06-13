---
name: slag-f2-slice2-built
description: "front-end F2 Slice 2 (slag partition — dephos/desulf, P/S state) BUILT 2026-06-13; benchmarked physics NOT a propagation, opposite-oxygen tooth, the deferred state extension authorized"
metadata: 
  node_type: memory
  type: project
  originSessionId: 80259b78-3d39-425c-bf3a-1af1ee0d1535
---

**front-end F2 Slice 2 (slag partition — dephosphorize / desulfurize) BUILT ✓ 2026-06-13** — the
deferred "partition" half of F2 (`docs/plans/steel-making.md` §7). `slag.py` + `demo_slag.py` +
`plots.slag_figure` + 23 tests (`test_slag.py` 16 + `test_demo_slag.py` 7); suite 642 → **665 passed / 2
skipped**. **ONE back-end touch — the state extension the F2/F3 builds kept deferring, now user-authorized:**
`sweep.Steel` gains `P`/`S` (default 0). **Additive & inert** — all callers keyword (field order moot),
`minor()` deliberately excludes P/S, full suite green byte-identical (the non-breaking proof = this slice's
round-trip-identity analog). No solver, no engine touch, **no ADR** (additive inert fields ≠ a semantics
change; advisor: "ADR only if you change Steel's *semantics*"). Closes the **§15.4 gap #1** (the named
single-highest-leverage front-end build); the §14 theme-C purity ramp + Thomas-vs-acid-Bessemer now
expressible. Wootz V/Mo banding (§14.5) still future research.

**The load-bearing honesty (advisor pre-code crux): this is BENCHMARKED PHYSICS (the F1/F4 class), NOT a
spine-class propagation.** Slice 1's carbon axis was *validated* end-to-end because the back end **consumes**
carbon. **P/S have NO validated consumer** — hardenability/hardness read C/Si/Mn/Ni/Cr/Mo only (I verified:
`minor()` excludes them; `casting.py` Scheil takes explicit `C0`, doesn't read a P/S field). So the proof is
the *physics vs published facts*, and the consequence (P→GB-embrittlement/DBTT; S→red-short/MnS/hot-tear) is
**deferred** (§6 "F2 new + F4 new"; §14's unpinned P→DBTT slope). A **structural tooth pins the posture:**
an off-spec-P/S heat heat-treats *identically* to a clean one (`test_phosphorus_sulfur_inert_in_back_end`).
F2 Slice 2 **sets the impurity state; it does not close its consequence.** (Same "filled-but-inert" pattern
as the gas fields on `Heat`, but now on the composition vector.)

**The teeth — avoiding the documented vacuous-benchmark trap** (advisor: "'L rises with basicity' is baked
into any correlation with a basicity term — my repeat failure"). Real teeth, all could-have-missed:
- **THE HEADLINE — opposite oxygen dependence of P vs S, falling out of INDEPENDENT sources.**
  Dephosphorization oxidizes (Healy 1970 `log L_P = 22350/T + 0.08·%CaO + 2.5·log %Fe_t − 16` → **+2.5·log
  %Fe_t**); desulfurization reduces (Sosinsky–Sommerville `log C_S=(22690−54640·Λ)/T+43.6·Λ−25.2` + the
  conversion `log L_S = log C_S − log a_O − 770/T + 1.30` → **−log a_O**). Two signs, two independently-sourced
  correlations → opposite is **computed not tuned** (cross-coheres with Slice 1 exactly as Al≫Si>Mn cohered
  with F1 Ellingham). `desulfurize` **READS `Heat.oxygen_ppm`** (Slice 1's kill) → same ladle slag gives
  L_S≈12 at the un-killed blow (~53 ppm O, barely works) vs L_S≈140 after the kill (~4 ppm O, strips S) →
  physics **dictates the process order dephos(oxidizing)→deox→desulf(reducing)**.
- **Acid/basic endpoint** = why Bessemer rails cracked: acid slag L_P≈0.85 (O(1), lime-poor → no stable
  phosphate) vs basic L_P≈411 (Thomas). ~500× basicity swing.
- **Order-of-magnitude vs measured plant L** (independent benchmark): basic L_P≈411 (measured BOF 50–200,
  Healy **over-predicts at high lime** = named source-sensitive tier); ladle L_S≈140–200 in the measured
  10²–10³ band.

**By construction (NOT teeth, labelled like F1 Hess/balance):** metal↔slag mass-balance partition
`[%X]=[%X]₀/(1+L·R)` (R=slag/metal mass ratio, converter 0.10 / ladle 0.02); **Mn:S→MnS** stoichiometry
(M_Mn/M_S=1.71 wt for 1:1; target Mn:S≳2 = Mushet's manganese that made Bessemer sound, §14 theme B);
Fe–FeO `[%O]=0.213·a_FeO` (k_Fe cited, used only to put L_P/L_S on a shared oxidizing-power axis with
a_FeO≈X_FeO Raoultian).

**Constants (di-crosscheck applied — [[di-crosscheck-source]]):** source-sensitive tier = all absolute
coefficients (Healy, Sosinsky–Sommerville, the C_S→L_S conversion `−770/T+1.30`, Duffy–Ingram component
optical basicities {CaO1.0,SiO2 0.48,Al2O3 0.605,MgO0.78,FeO/MnO≈1.0 — FeO/MnO themselves *optimized* from
C_S data}, k_Fe=0.213). Robust reads (teeth) = the two oxygen **signs**, the acid/basic endpoint, the
measured ranges. P/S equilibria scatter factor-several → ranking + OoM only.

**Seam:** `dephosphorize(heat, slag=BASIC_CONVERTER_SLAG, slag_ratio=0.10)` → lowers `composition.P`, flags
`HIGH_PHOSPHORUS` if > spec; `desulfurize(heat, slag=LADLE_DESULF_SLAG, slag_ratio=0.02)` → reads oxygen,
lowers `S`, flags `HIGH_SULFUR`. Specs = labelled (P 0.035 / S 0.040, standard SAE-class, editable like
`MIN_MARTENSITE_SPEC`). 3 named slags (ACID_BESSEMER / BASIC_CONVERTER (Thomas/BOF) / LADLE_DESULF). Demo =
working route (basic dephos→blow+kill→ladle desulf, P 0.10→0.002 / S 0.06→0.016, clean) + 2 history failures
(acid Bessemer P retained→HIGH_P; desulf-before-kill S retained→HIGH_S) + Mn:S→MnS. Charge = `replace(
STEELS["4140"], P=0.10, S=0.06)` (pig-iron impurity; `from_hot_metal`'s `replace` preserves P/S).

**Named deferrals:** P/S **carried but inert** downstream (no consumer); P/S **add-back from high-impurity
ferroalloys** in the F3 trim (like F3's carbon carry-in); slag-metal mass-transfer *rate* (§4 tar pit). Gallery
2nd "Refining (front-end)" card; both READMEs + plan §7/§15.2/§15.4 as-built. **Notebook & app deferred**
(all front-end phases are). Amends [[refining-f2-built]] (its named Slice-2 gap) / [[ladle-f3-built]] (its P/S
deferral) / [[historical-impurity-pedagogy]] (§14 theme B/C now have an engine); builds on
[[steel-making-frontend-plan]].
