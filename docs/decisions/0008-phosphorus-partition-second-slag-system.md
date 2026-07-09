# 0008 — The cited Healy L_P model is graded on a second slag system: it generalizes, with a non-CaO-basicity edge

Status: Accepted — 2026-07-10
Scope: `steel/slag.py`'s dephosphorization path (`phosphorus_partition`, the Healy 1970 L_P
correlation) and the new validation module `steel/slag_lp2_validation.py`. **No engine or frozen
pipeline is touched** — this ADR records a decision to *keep* the cited model unchanged and *extend
its measured bias map onto a second, independent slag system*. It closes the second of the two legs
`docs/plans/next-directions.md` left open for the front-end validation direction (B3): "a second
independent slag *system*", which ADR 0007 explicitly deferred.

## Context

ADR 0006 holdout-validated the sulfur / C_S leg; ADR 0007 holdout-graded the phosphorus / L_P leg
(Healy 1970) against Drain 2018 and recorded a **quantified bias map** — Healy carries ~×1.0 at
moderate basicity, over-predicts ~×2 at high lime. ADR 0007's own stated weakness was that it rested
on **one slag family at one temperature**: 33 BOS heats (CaO–SiO₂–MgO–FetO), 30 of them at 1650 °C.
Its named follow-up was a **second independent slag system**.

The trap is that the obvious open-access, tabulated "different systems" for L_P are **hot-metal
dephosphorization** sets (Zhou 2017, Im 1996) measured at ~1573 K against **carbon-saturated** iron.
Those were fetched and assessed and **rejected**: at 1300 °C — ~300 K below the converter fit — Healy's
unbounded `22350/T` term alone over-predicts L_P by ×200–500 (the `22350/T` gap from 1873 K to 1573 K
is +2.28 log units = ×190 by itself), so they measure a *temperature extrapolation*, not slag-system
generalization; and the C-saturated metal (which raises the phosphorus activity coefficient) is a
second confound. A clean second-system test must hold **temperature and metal chemistry fixed** and
vary only the **slag**. A re-scout for open-access, tabulated, converter-temperature (~1600 °C),
liquid-low-carbon-steel L_P in a genuinely different slag system returned essentially "data-gated" —
the classic 1980s–90s equilibrium studies survive only as PDF-image tables or behind paywalls.

**The source that clears the gates** is Suito & Inoue, *Transactions ISIJ* **24** (1984) 47 — open
access (CC BY-NC-ND, J-STAGE), committed at `docs/sources/suito_inoue_1984_naba_phosphorus_partition.pdf`.
Its Tables 1 & 2 are **printed tables** (image-embedded in the vintage PDF, transcribed from the
rendered page — the Nzotta / Im pattern, *not* figure-scraping). They give 23 measured equilibrium
heats of **liquid low-carbon iron** against **CaO–MgO_sat–FeO_x–SiO₂ slags carrying a foreign basic
flux** — 12 with BaO ≈ 4 % (Table 1), 11 with Na₂O 7–13 % (Table 2) — all at **1550 °C = 1823 K**.

Three independence facts make it a clean second-system holdout:

1. **Temporal** — measured 1984, fourteen years after Healy's 1970 fit (Tohoku), and independent of
   Drain's 2018 data.
2. **Parametric** — Healy reads only %CaO, %Fe_t and T with fixed 1970 coefficients and no optical
   basicity; zero parameters fit to these data.
3. **System** — the slag carries **Na₂O / BaO**, basic fluxes absent from Drain's BOS *and* from
   Healy's fit. Since Healy's basicity term is **%CaO alone**, these slags test whether that
   single-oxide basicity generalizes when another basic oxide does part of the dephosphorization.

Critically, the confounds that sank the hot-metal sets are absent: the **temperature (1823 K) sits in
Drain's own 1550–1700 °C window**, and the metal is **liquid and low-carbon** — the source tabulates
dissolved [%O] ≈ 0.085–0.19 % (an oxidizing FeO_x system, incompatible with carbon saturation). So
this varies the *slag*, not the temperature or the metal.

**Two transcription guards** run in the suite (Suito & Inoue tabulate no L_P or k_P column, unlike
Drain's three-column P redundancy): (a) `validate_kp_consistency` recomputes the equilibrium quotient
`log k_P = log[(%P₂O₅)/([%P]²(%Fe_tO)⁵)]` from the FeO/Fe₂O₃/P₂O₅/[%P] columns and checks it against
the paper's own **Eq. (3)** fit `0.145·[(%CaO)+0.3(%MgO)−0.5(%P₂O₅)+c·%flux] + 22810/T − 20.506`
(c = 1.2 Na₂O, 0.9 BaO) from the CaO/MgO/flux columns — a multi-column cross-check with the paper's
Fig. 1 scatter as the tolerance, sharp on [%P]/P₂O₅ typos via the `(%Fe_tO)⁵` leverage (coarse at the
extreme-composition fit edge — 809/810/712 — a named limit); (b) `validate_oxide_sum` checks every
row's seven oxide columns sum to 100 ± 2 mass %.

Findings (`slag_lp2_validation.summary`, computed not asserted):

- **BaO leg — Healy carries, independently confirming the Drain result.** On the 12 BaO slags (a minor
  4 % flux) Healy over-predicts a consistent **≈ ×1.56** (scatter ×1.6), and its high-basicity rows run
  highest (row 805, v≈2 → ×2) — the *same* mild high-lime over-prediction the Drain leg measured
  (≈ ×1.48 pooled, ×2 high-lime), now reproduced by a different lab, decade and slag system at
  converter temperature. Healy's ~×1.5 posture is not an artifact of Drain's one BOS family.
- **Na₂O leg — a named non-CaO-basicity edge, the signed opposite of the high-lime bias.** On the 11
  Na₂O slags Healy **under**-predicts. The robust, per-row read (each point's own CaO *and* Fe_t inside
  its Healy prediction) is the **pooled under-prediction ≈ ×0.30** and the Na₂O residual sitting ~0.5–0.7
  below the BaO series across the whole lime range; the two tables' pooled residuals differ by ≈ 0.72,
  and the matched-CaO window (%CaO ≈ 15–22) gives a consistent gap ≈ 0.69 — so the soda under-predicts
  **~×5** relative to baryta, robust across both reads. (Within Table 2, Na₂O and CaO are anti-correlated
  — the flux replaces lime — so the *within-table* gradient is CaO-confounded and is **not** used; the
  between-table reads isolate the flux.) This is **order-consistent** with the paper's own 1.2×/0.9×
  CaO-equivalencies (≈ 0.7 log units on Healy's 0.08 term) — reported as *same-paper, order-of-magnitude*
  corroboration, **not** a precise match: the small matched-CaO window is not also Fe_t-matched (BaO ~40 %
  vs Na₂O ~33 % Fe_t ≈ 0.17 log of Healy's Fe_t term), so the exact factor is uncertain and the 0.69 ≈
  0.67 coincidence is not over-read.

## Decision

**Keep the cited Healy L_P correlation unchanged; record that its ~×1.5 measured bias generalizes to a
second, independent slag system (the BaO leg reproduces Drain), and extend the bias map with the
signed non-CaO-basicity edge the Na₂O leg measures (Healy under-predicts ~×4–5 at matched CaO because
it reads %CaO alone).** The validation lives in `steel/slag_lp2_validation.py` and is wired into
nothing — `slag.phosphorus_partition` is byte-identical and the frozen pipeline is untouched.

This is a **scientific bias-map extension, not an engine behaviour change**: the engine's slags
(acid Bessemer / basic converter / ladle) carry no soda or baryta flux, so no caller path reads the
Na₂O edge. The honest posture is exactly ADR 0007's: an independent confirmation on the "does Healy
carry" axis, plus a located, quantified edge on the axis Healy is structurally blind to. No parameter
is fitted or grafted — a refit would manufacture coherence over a structural (single-oxide basicity)
limitation.

## Consequences

- `+` ADR 0007's stated weakness (one slag family, one temperature) is **closed on the composition
  axis**: Healy's over-prediction is now confirmed on a genuinely different oxide system at converter
  temperature, and the bias map gains a signed non-CaO-basicity edge with a stated mechanism.
- `+` **Zero blast radius.** New module + demo + figure + gallery/README rows + tests + the committed
  primary-source PDF; `slag.py` and every engine module untouched and byte-identical (only the module
  docstring's provenance paragraph changed).
- `+` The hot-metal temperature extrapolation was measured and **rejected on principle** (a confounded
  test), not shipped as a spurious "validation" — the anti-manufactured-coherence discipline held.
- `−` The finding still rests on a **single temperature** (1823 K) — like ADR 0007's, it tests the
  composition terms, not an independent T-slope (Suito & Inoue vary only the slag). The temperature leg
  of the L_P validation remains confounded across both legs.
- `−` The Na₂O/BaO edge is **outside the engine's slag chemistry**, so it is caller guidance for a
  regime the repo does not simulate — scientific completeness, not a behaviour the pipeline exercises.

## Alternatives considered

- **Ship the hot-metal sets (Zhou 2017 / Im 1996) as the second system** — rejected: at 1573 K against
  C-saturated iron they measure a temperature extrapolation (×200–500 over-prediction, ~entirely the
  `22350/T` term) plus a metal-chemistry confound, not slag-system generalization. Computing the bias
  before framing is what caught this; shipping it would have been a preordained failure dressed as a
  finding.
- **Declare the leg data-gated** — the re-scout's formal verdict (no open-access, tabulated,
  converter-temperature, liquid-low-C L_P in a different system) — set aside once Suito & Inoue 1984
  was recognised as viable: its "image table" is a *printed* table this project transcribes routinely
  (Nzotta, Im), not the figure-scraping the gate forbids.
- **Refit / add a Na₂O (and BaO) basicity term to Healy** — rejected: it would break the "cited, not
  calibrated" posture, the engine never sees soda/baryta slags, and the edge is reported, not tuned
  away. (Suito & Inoue's own Eq. 3 already *is* that refit; using it as the model would compare fits,
  not test one against data — the ADR 0007 caution. Here Eq. 3 serves only as a transcription guard.)
- **Grade Healy against Suito & Inoue's *correlation* (Eq. 3)** — rejected for the ADR 0007 reason
  (Eq. 3 is a fit; that compares models). Their **measured heats** are the holdout, exactly as Drain's
  were.
