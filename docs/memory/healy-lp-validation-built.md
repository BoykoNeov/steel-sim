---
name: healy-lp-validation-built
description: "B3 phosphorus leg — holdout-grade the cited Healy L_P dephosphorization model vs Drain 2018; BUILT 2026-07-06 as a QUANTIFIED BIAS MAP (not 'validated' like C_S) + microchip/planet scrub"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2273d4f5-332f-4c26-a4f9-303b34d5bbe3
---

**B3 phosphorus leg (holdout-grade the F2 Healy L_P dephosphorization correlation, the sulfur/C_S
twin) BUILT ✓ 2026-07-06**, closing the last-but-one open leg of [[b3-front-end-validation-built]]
("Still open: the Healy L_P leg"). Same data-gate discipline: cleared by the **primary source in
hand** — Drain–Monaghan–Longbottom–Chapman–Zhang–Chew, *ISIJ International* **58** (2018) 1965,
Table 4 (**open access CC BY-NC-ND** → `docs/sources/drain_2018_phosphorus_partition_bos.pdf`), 33 of
the authors' **own measured equilibrium heats**, `L_P = (%P)/[%P]` mass ratio **exactly as Healy
defines it** (not a phosphate capacity). Extracted with `pypdf` (digital PDF, non-OCR) — NOT the
"Ismail" author I first mis-named the file after.

**Independence is CLEANER than the C_S leg's:** temporal — measured 2018, **48 yr** after Healy 1970;
parametric — Healy reads only `%CaO`, total-Fe `%Fe_t`, `T` with fixed 1970 coeffs and **no optical
basicity at all**, so (unlike S–S) there isn't even a fitted-Λ input to dodge → zero params fit to
these data.

**VERDICT = a QUANTIFIED BIAS MAP, deliberately WEAKER than C_S's "validated" (the honest,
anti-confirmation-bias call).** Pooled ×1.48 / scatter ×1.54 (n=33), but the bias is **NOT uniform —
it climbs monotonically with basicity**: B2 (v≈2, Healy's fit domain) **×1.02 near-exact** → R ×1.18
→ T ×1.39 → B4 (v≈4) ×1.95 → B5 (v≈5) ×1.98; split by lime `%CaO<50` ×1.13 vs `%CaO≥55` **×2.29**.
Mechanism = structural: Healy's `+0.08·%CaO` is **linear/unbounded** but real L_P **saturates** beyond
v≈2.5. So slag.py's vague flag "over-predicts at high lime" → a **measured map (~×1.0 at v≈2 → ~×2 at
v≈5)**; L_P stays **benchmarked/order-of-magnitude, NOT upgraded to "validated"** (the high-lime bias
is real). Temperature direction reproduced (L_P falls with T, rows 8–10) but **magnitude confounded**
(3 pts co-vary in composition) → a direction check, NOT a second tooth (contrast the C_S leg's clean
T-slope). Named structural ceiling = the ~20% FetO **maximum** Healy's monotonic `+2.5·log(%Fe_t)`
can't represent. **No refit.**

**Two transcription guards** (Table 4 has no repeat-reading column): `validate_lp_consistency`
(recompute L_P from the `%P₂O₅`/`[%P]` columns within both-column rounding — coarse on low-`[%P]`
rows, named) + `reproducibility_crosscheck` (7 R-series repeats reproduce the paper's **prose-stated**
"mean 190, std 7" = ~3.7% scatter floor). **Advisor catch (my own di-crosscheck lesson):** these guard
the P₂O₅/[%P]/L_P columns but NOT the **composition columns** (CaO/SiO₂/FetO — Healy's actual inputs)
→ closed by cross-checking all 33 rows of every composition column against the source extraction (0
mismatches; named limit = same-extraction, not a 2nd-tool read — pdfminer/pdfplumber absent, only
pypdf; layout-mode parse was inconclusive). **Second slag system now BUILT ✓ 2026-07-10 → [[slag-lp2-validation-built]]**
(Suito–Inoue 1984 Na2O/BaO fluxes at converter T: Healy CARRIES ×1.56 on BaO = reproduces this Drain
result on a 2nd system, + a signed non-CaO-basicity edge on Na2O; ADR 0008). The Assis EAF path stayed
403'd; the hot-metal 1573 K sets were assessed and REJECTED (a `22350/T` temperature strawman).

**Surfaces (no engine touch):** `steel/slag_lp_validation.py` + `demo_slag_lp_validation.py` +
`plots.slag_lp_validation_figure` → `docs/figures/steel-slag-lp-validation.png` + gallery 3rd
"Validation" card + README demo row + `test_slag_lp_validation.py` (14). **ADR 0007.** `slag.py` L_P
docstring/comment posture upgraded. Fast lane **1082→1096**, full **1114 green** (2 env-skips,
freshly run). **Still open:** a 2nd slag system beyond these BOS/ladle systems (the MDPI Assis 2019
EAF set 403'd + is further out of Healy's domain).

Sibling/predecessor [[b3-front-end-validation-built]] (the C_S leg); physics under test is
[[slag-f2-slice2-built]]; back-end twin pattern [[cross-composition-validation]]; di-crosscheck
discipline [[di-crosscheck-source]]. Same-batch: the microchip/planet scrub → see
[[repo-self-contained]] / [[next-directions-catalogue]].
