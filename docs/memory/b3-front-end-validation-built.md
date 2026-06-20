---
name: b3-front-end-validation-built
description: "B3 front-end validation deepening (holdout-validate the F2 slag sulfide-capacity C_S) — BUILT 2026-06-20 against an independent measured dataset; the cited model CARRIES out-of-sample"
metadata:
  node_type: memory
  type: project
---

**B3 (front-end validation deepening — the §20 `cct_validation.py` pattern applied to F2 slag
chemistry) BUILT ✓ 2026-06-20**, unblocking the 2026-06-20 deferral ([[b3-front-end-validation-blocked]],
now superseded). The block was never on data *existence* — it was on **extractability to the
[[di-crosscheck-source]] standard**. Cleared by getting the **primary source in hand**: Nzotta–
Sichen–Seetharaman, *ISIJ International* 38 (1998) 1170, is **open access (CC BY-NC-ND)** and its
Tables 5/6/9 tabulate measured C_S as **text** (not figures) → downloaded to
`docs/sources/nzotta_1998_sulphide_capacities.pdf` and transcribed from the page tables, not
figure-scraped (the fabrication path that dropped the AI Table A7 D_I).

**Surfaces (no engine touch — reads `slag.sulfide_capacity` only, the cct_validation posture):**
`steel/slag_validation.py` (the study) + `demo_slag_validation.py` + `plots.slag_validation_figure`
→ `docs/figures/steel-slag-validation.png` + gallery "Validation" 2nd card + README row +
`test_slag_validation.py` (13) / `test_demo_slag_validation.py` (2). **ADR 0006.** Fast lane
**949 green**. `slag.py` C_S provenance docstring upgraded from "order-of-magnitude only" to
"holdout-validated within the basic domain."

**The model under test = Sosinsky–Sommerville 1986** `log C_S = (22690 − 54640·Λ)/T + 43.6·Λ −
25.2`. **The circularity gate (load-bearing):** S–S is a *fit*, so the holdout must be a source it
could not have seen. Two independence facts make Table 6 (Al₂O₃–CaO–MgO–SiO₂, present work) clean:
**(1) temporal** — measured 1998, after the 1986 fit (KTH lab); **(2) parametric** — no MnO/no FeO,
whose optical basicities in slag.py are *themselves fit-to-C_S*; the four components present carry
spectroscopic Duffy–Ingram values → the composite under test has **zero params fit to these data**.
In-domain on T (1773–1923 K ⊂ S–S's 1400–1700 °C) → any edge is compositional.

**Verdict = it CARRIES (the positive out-of-sample result the advisor flagged as more valuable than
another wall).** Table 6 = **4 distinct basic compositions (Q2/Q3/Q4/Q5, Λ≳0.65) × up to 3 temps**
(10 pts). Basic pool: **~×1.4 overprediction**, **×1.18 scatter** (inside the source's own factor-2–3
inter-lab band), and **consistent on BOTH axes** — each composition carries the same bias (Q2 ×1.57 /
Q3 ×1.35 / Q4 ×1.38 / Q5 ×1.41). **The genuinely independent axis is the T-SLOPE** (a constant bias
leaves it untouched → tests the (…−54640·Λ)/T term alone): repeated comps (Q2/Q3 at 3 temps) give
≈+0.44 model vs +0.47 meas /100 K. (Within-T ranking ρ=1 is a *footnote* — thin, n=3–4 close slags,
S–S monotonic in Λ.) **Two named edges:** (a) **acidic = a SINGLE-POINT flag, NOT a trend** — only
Q1 (Λ≈0.60) misses (~×4 low); the literature's lowest-Λ point also misses but a near-identical-Λ
neighbour fits fine (~7× spread in C_S at the SAME Λ = internal scatter, not corroboration), and the
cause is NOT isolated (amphoteric Al₂O₃ Λ=0.605 vs out-of-domain high-alumina); (b) **MnO** — Table 5
(tests slag.py's *fitted* MnO Λ=1.0, steep high-Λ) over-predicts ~×5 = located weak link, NOT headline.

**Durable advisor catches:** (1) the **blocking** one — OCR was garbled, so transcribe from the page
*images* and bake a **transcription guard** (`validate_transcription`: tabulated avg ≈ mean of its
listed repeats, runs in the suite). **Scope-limited though** — it guards the **C_S column only**; the
composition/T columns (which drive Λ) are cross-checked only *partially* via `overlap_crosscheck` (the
4 rows printed in BOTH Table 6 & Table 9 agree on composition+C_S = 4/10 rows end-to-end). A
composition typo outside those 4 (e.g. a mis-read MgO in the MnO tier) is NOT caught. **That residual
gap was closed by HUMAN CONFIRMATION 2026-06-20: the user opened the open-access PDF and verified
all of Table 6 cell-by-cell + the one flagged ambiguity (the two C4/MnO rows carry DIFFERENT MgO
0.087 vs 0.121 because their TEMPERATURES differ — both correct, not a typo) + the rest → the whole
holdout is now primary-source-verified, not just internally consistent. The di-crosscheck standard is
fully met (automated C_S/overlap guards + human eyes on the composition columns the guard is blind
to).** (2) **Compute
ALL points before framing** — my 2-point preview ("carries high-Λ / breaks low-Λ") was *wrong*; the
full set is "consistent mild overpred across the 4 basic comps + Q1 as a single sign-flipped 4×
outlier." (3) **The acidic edge "recurs across labs" was noise-mining** (advisor): the literature's
worst-miss==lowest-Λ test passes by luck on one outlier → reframed as a single-point Q1 flag.
**No refit** (model already carries; tuning 10 pts = manufactured coherence). **Still open:** the
Healy **L_P** leg (needs an independent measured-partition dataset) and a 2nd slag system beyond
Al₂O₃–CaO–MgO–SiO₂. Amends [[next-directions-catalogue]]; sibling [[cross-composition-validation]]
(the §20 back-end twin); physics under test is [[slag-f2-slice2-built]].
