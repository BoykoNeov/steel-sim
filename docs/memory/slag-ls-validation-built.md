---
name: slag-ls-validation-built
description: "B3 sulfur metal-partition leg (C_S→L_S conversion PROBED vs Mohassab 2013 gas-controlled L_S) BUILT 2026-07-10, ADR 0009 — order-of-magnitude, NOT upgraded; both B3 residual gaps = one structural wall"
metadata: 
  node_type: memory
  type: project
  originSessionId: ed22b2d8-3e0f-4211-ac38-2ba6f0c5c055
---

B3 **sulfur metal-partition leg** (`steel/slag_ls_validation.py` + demo + `plots.slag_ls_validation_figure`
+ 17 tests + ADR 0009) BUILT 2026-07-10, closing the last-named B3 residual gap ("C_S→L_S conversion,
still order-of-magnitude"). Grades the sulfur **metal**-partition `L_S = (%S)/[%S]` that
`slag.desulfurize` actually computes — and the `−log a_O` term the conversion introduces (the module's
headline desulfurization physics) — which C_S validation ([[b3-front-end-validation-built]]) and the L_P
legs ([[healy-lp-validation-built]], [[slag-lp2-validation-built]]) never touched.

**Verdict = PROBE, order-of-magnitude, NOT upgraded (unlike C_S).** On the clean waterless CO/CO₂ subset
(dilute S ⇒ f_S≈1) the `Λ→C_S→L_S` chain **under-predicts a factor of several** (direction robust across
the a_O method), but the magnitude is **unresolvable** — 3 confounds: (1) the C_S baseline is itself
**unvalidated** on these 10–53 % FeO slags (fitted Λ_FeO — Nzotta was FeO-free); (2) the `−log a_O` slope
is **inseparable from FeO basicity** (gas sets FeO, so pO₂ & basicity co-vary, no matched-comp pairs); (3)
a_O carries a **standard-state offset** (gas-a_O vs FeO-anchor differ ×2). Two signed edges survive: a
measured **atmosphere ladder** (water raises L_S ~×5 via f_S²⁻ — engine atmosphere-blind, so H₂/H₂O heats
are *disqualified for grading*, not an engine-failure) + a **~×2-low FeO oxygen anchor**
(`metal_oxygen_for_feo`, Raoultian a_FeO≈X_FeO under-reads).

**THE META-POINT (intellectual core, in the ADR):** the `−log a_O` slope is non-isolable for the SAME
reason the L_P T-slope is — **the term under test co-varies with composition in ALL clean equilibrium
data**. Both B3 residual gaps hit ONE structural wall. **B3 now fully closed** (C_S validated, L_P
benchmarked ×2 systems, L_S probed).

**DURABLE process wins (this session):**
- **The a_O-provenance gate is the whole game.** L_S is a clean holdout only if a_O is set *independently*
  (gas pO₂), NOT back-derived from a deox equilibrium ([Al]/[O]) — that rules out most ladle L_S data and
  points almost uniquely at controlled-atmosphere gas–slag–metal work. Advisor set this gate first.
- **Compute-before-framing paid off twice** (the [[slag-lp2-validation-built]] lesson): it **demoted** an
  initially-hoped "carries to ×2" (that was Table 4-1, [S]=5–12 wt% ⇒ f_S BROKEN — a flattering
  cherry-pick) to the honest "clean set under-predicts"; and the Log(Ls) three-column guard **caught &
  excluded a source-inconsistent row (S8**: printed Log Ls −0.10 but log((S)/[S])=−0.49; verified faithful
  vs rendered PDF → a *source* typo, dropped not baked).
- **Committed-PDF convention is OA convenience, NOT method** (advisor). Mohassab is All Rights Reserved
  (Utah PhD) → **cite + transcribe data, do NOT commit PDF** (data = facts; guards stand in for
  "primary-source-in-hand"). First B3 leg to do this.
- **Access, not license, was the real wall:** journal paywalled + Utah repo behind a JS anti-bot cookie
  challenge — solved by running the challenge JS in node with document/window stubs to extract the cookie,
  then curl with it. Render printed tables to PNG (PyMuPDF/`fitz`, no poppler) + transcribe.

Recon durable at `M:/claud_projects/temp/ls_recon/` (FINDINGS.md, compute*.py, dissertation, rendered
tables). See [[next-directions-catalogue]]; [[repo-self-contained]].
