---
name: slag-lp2-validation-built
description: "B3 second slag system for Healy L_P (Suito-Inoue 1984 Na2O/BaO fluxes) BUILT 2026-07-10 — Healy CARRIES on a 2nd system + a signed non-CaO-basicity edge; compute-before-framing killed two false legs. ADR 0008"
metadata:
  node_type: memory
  type: project
---

**B3 second-slag-system leg for the Healy L_P dephosphorization model BUILT ✓ 2026-07-10 (ADR 0008,
`steel/slag_lp2_validation.py`)**, closing ADR 0007's stated one-system/one-temperature weakness and
the last open item of [[healy-lp-validation-built]] / [[b3-front-end-validation-built]] ("still open: a
2nd slag system"). **B3 now fully closed** (both slag chemistries × 2 systems). Sibling of
[[healy-lp-validation-built]] (leg #1, Drain BOS) and [[cross-composition-validation]] (§20 back-end
twin); physics under test [[slag-f2-slice2-built]]; transcription discipline [[di-crosscheck-source]].

**Source = Suito & Inoue, *Trans. ISIJ* 24 (1984) 47** (open-access CC BY-NC-ND, J-STAGE →
`docs/sources/suito_inoue_1984_naba_phosphorus_partition.pdf`). 23 heats of **liquid low-C iron** vs
**Na2O(7–13 %) / BaO(~4 %)-fluxed CaO–MgO–FeO_x–SiO₂ slags at 1550 °C**. Na2O/BaO are basic fluxes
**absent from Drain's BOS and from Healy's fit** → a genuine second *system*; 1550 °C is in Drain's
window and `[%O]` 0.09–0.19 % proves the metal is oxidizing/low-C (not C-saturated) → **T and metal
held fixed, only the slag varies.**

**VERDICT = carries + a signed edge.** BaO leg (minor 4 % flux): Healy over-predicts **×1.56**, high-lime
rows highest — **independently reproduces Drain's ×1.48 from a different lab/decade/system** (the
generalization result). Na2O leg (major base): Healy **under**-predicts (pooled ×0.30,
per-row) — blind to soda's basicity. Soda under-predicts **~×5** vs baryta, robust across BOTH the
full-range pooled per-table diff (≈ +0.72) and the matched-CaO window (gap ≈ +0.69). The **signed
OPPOSITE** of leg #1's high-lime *over*-prediction; **order-consistent** (NOT a precise match — the
small window is not Fe_t-matched, ~0.17 log) with Suito–Inoue's own 1.2×/0.9× CaO-equivalency (~+0.7). **Scientific bias-map extension only** — the
engine's slags carry no soda/baryta, so no behaviour changes. No refit, no engine touch (docstring
posture only). Guards: Eq.(3) `k_P` multi-column cross-check + oxide-sum≈100. 16 tests; full 1128 green.

**TWO DURABLE LESSONS (both = "compute the bias BEFORE framing," which twice stopped a bad ship):**
1. **A big out-of-domain failure is a STRAWMAN, not a finding.** First candidates were hot-metal sets
   (Zhou 2017 / Im 1996, 1573 K, **C-saturated** iron). Healy over-predicts ×200–500 there — but that's
   **~entirely the unbounded `22350/T` term extrapolated ~300 K below the converter fit** (the 1873→1573 K
   gap alone = +2.28 log = ×190), i.e. a *temperature* extrapolation + a metal-chemistry confound, NOT
   slag-system generalization. Advisor: "a preordained failure dressed as a finding." **Rejected on
   principle.** A clean second-*system* test must hold T + metal fixed and vary only the slag.
2. **Guard the tooth against a hidden collinearity.** My first Na2O tooth ("under-prediction scales with
   Na2O") was **CaO-confounded** — within Table 2, Na2O and CaO are anti-correlated (flux replaces lime),
   so "more Na2O" = "less CaO" and Healy's `0.08·%CaO` term alone explains the within-table gradient. The
   clean signal is the **matched-CaO contrast BETWEEN the two tables** (BaO vs Na2O at fixed %CaO), which
   differences the CaO term out. Advisor catch.

**Process lesson:** the re-scout agent mechanically flagged this leg "data-gated" because Suito–Inoue's
tables are **image-embedded** — but a *printed* table rendered from a clean PDF and transcribed with
guards is routine here ([[b3-front-end-validation-built]] Nzotta, and Im 1996), NOT the figure-scraping
the gate forbids. Rendered pages via PyMuPDF (`fitz`, poppler-free) → read visually → transcribe. Don't
let "image table" auto-kill an open-access printed-table source.
