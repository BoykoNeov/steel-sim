# 0006 — The cited sulfide-capacity model is holdout-validated (basic domain); two edges named

Status: Accepted — 2026-06-20
Scope: `steel/slag.py`'s sulfide-capacity path (`sulfide_capacity` / `sulfur_partition`, the
Sosinsky–Sommerville optical-basicity correlation) and the new validation module
`steel/slag_validation.py`. **No engine or frozen pipeline is touched** — this ADR records a
decision to *keep* the cited model and *upgrade its documented posture* from "order-of-magnitude
only" to "holdout-validated within the basic domain," having graded it against an independent
measured dataset.

## Context

The front-end refining slice (`slag.py`, [[slag-f2-slice2-built]]) uses Sosinsky–Sommerville (1986)
for sulfide capacity:

```
log10 C_S = (22690 − 54640·Λ)/T + 43.6·Λ − 25.2     (1400–1700 °C)
```

with the Duffy–Ingram component optical basicities. That module flagged the absolute correlation as
the **source-sensitive tier** — "ranking + order of magnitude only" — because it was never tested
out-of-sample in this repo. The named follow-up (B3, `docs/plans/next-directions.md`) was to apply
the §20 `cct_validation.py` pattern to the front-end: grade the cited correlation against measured
C_S **from a source the fit could not have seen.**

The crux is the **circularity gate** (the project's standing non-circularity discipline): S–S is a
regression *fit*, so grading it against its own training data is the vacuous-benchmark trap. The
B3 scoping spike (2026-06-20) initially deferred the build, blocked not on data *existence* but on
**extractability to the [[di-crosscheck-source]] standard** — the web artifacts were model/review
papers citing the data without tabulating it. That block was cleared by obtaining the **primary
source in hand**: Nzotta–Sichen–Seetharaman, *ISIJ International* **38** (1998) 1170, an
**open-access** paper (CC BY-NC-ND) whose Tables 5/6/9 tabulate measured C_S directly (committed at
`docs/sources/nzotta_1998_sulphide_capacities.pdf`).

Two facts make the chosen holdout (`slag_validation.HOLDOUT`, Table 6, Al₂O₃–CaO–MgO–SiO₂) a clean
out-of-sample test:

1. **Temporal independence** — measured 1998, twelve years after the 1986 correlation, in a
   different laboratory (KTH). It cannot be in the 1986 fit.
2. **Parametric independence** — Table 6 carries **no MnO and no FeO**, whose optical basicities in
   `slag.py` are *themselves optimized from C_S data*. The four components present (CaO/SiO₂/Al₂O₃/
   MgO) carry spectroscopic Duffy–Ingram values fit to nothing in this chain. So the composite
   under test — Λ(spectroscopic) → S–S(1986) — has **zero parameters fit to these data**.

The temperatures (1773–1923 K) sit inside S–S's stated 1400–1700 °C validity, so any edge is
compositional, not an out-of-range artifact. A **transcription guard** (`validate_transcription`,
run in the suite) checks every tabulated average against the mean of its raw repeat readings — the
"verify an AI-extracted table against a direct read" discipline, automated.

Findings (`slag_validation.summary`):

- **It carries.** Table 6 is **four distinct basic compositions** (Q2/Q3/Q4/Q5, Λ ≳ 0.65), each
  measured at up to three temperatures (ten points). On the nine basic points the model is a
  **consistent ~×1.4 overprediction** (mean log-residual +0.16, std 0.07 → ×1.18), and the
  consistency holds on *both* axes — **each composition carries the same ~×1.4 bias** (Q2 ×1.57,
  Q3 ×1.35, Q4 ×1.38, Q5 ×1.41) — well inside the factor-2–3 inter-laboratory scatter the source
  itself documents. The **genuinely independent corroboration is the temperature slope**: a constant
  log-bias leaves the slope untouched, so the S–S `(22690 − 54640·Λ)/T` term is tested *on its own*
  when the repeated compositions (Q2, Q3 at three temperatures) reproduce the measured C_S(T)
  movement — ≈ +0.44 model vs +0.47 measured per +100 K. (Within-temperature composition ranking is
  also exact, ρ = 1.0 at 1773 K and 1873 K, but over only 3–4 closely-spaced slags with S–S
  monotonic in Λ — a supporting footnote, not the headline.)
- **Two edges, flagged honestly.** (1) **The acidic edge — a single-point flag, not an established
  trend.** The one most-acidic slag tested (Q1, Λ ≈ 0.60) flips sign and under-predicts ~×4. The
  *independent literature* (Table 9: Abraham–Richardson / Kärsrud / Kalyanram, pre-1986 —
  corroboration only, weaker independence) has its worst miss at its lowest-Λ point too, **but** a
  near-identical-Λ neighbour fits fine and the two differ ~7× in measured C_S at the same basicity:
  that is the dataset's internal scatter at low Λ, not a reproduced acidic trend. So the acidic edge
  rests on Q1 alone. (2) **The MnO edge.** The Table-5 MnO diagnostic over-predicts ~×5 — but it
  tests `slag.py`'s *fitted* MnO Λ = 1.00 in the steep high-Λ regime, so it is a weak-independence
  tier and is reported as a located weak link, not part of the headline.

## Decision

**Keep the cited Sosinsky–Sommerville model unchanged; upgrade its documented posture for C_S from
"order-of-magnitude only" to "holdout-validated to ~×1.4 with ×1.2 scatter and exact ranking within
the basic domain (Λ ≳ 0.65)," and name the two edges (acidic Λ ≲ 0.6 under-prediction; MnO
over-prediction).** The validation lives in `steel/slag_validation.py` and is wired into nothing —
`slag.sulfide_capacity` / `sulfur_partition` are byte-identical and the frozen pipeline is
untouched. This is the *positive* mirror of ADR 0005: there the attempt to break a wall ended at a
diagnosis (per-steel anchoring vindicated); here the attempt to break a correlation ended in an
**out-of-sample pass**, which is the more valuable outcome and the one the data licensed.

No parameter is fitted or grafted — a refit would be unnecessary (the model already carries) and
unlicensed (the acidic edge is a single point with an un-isolated cause — amphoteric Al₂O₃ and/or
out-of-domain use — not a knob to tune on 10 points; the MnO edge is the fitted-Λ tier).

## Consequences

- `+` `slag.py`'s sulfide-capacity claim is now **measured, not asserted** — a genuine validation
  increment with the same non-circularity rigour as §20 (independent dataset, transcription guard,
  T-confound removed, edges named).
- `+` **Zero blast radius.** New module + demo + figure + gallery/README rows + tests + the
  committed primary-source PDF; `slag.py` and every engine module untouched and byte-identical.
- `+` The two edges are a concrete map of where the optical-basicity C_S model should *not* be
  trusted (acid slags; MnO-rich slags / the steep high-Λ regime) — useful guidance for any caller.
- `−` The headline rests on **one system** (Al₂O₃–CaO–MgO–SiO₂) — the only post-1986, MnO/FeO-free
  table in the source. It is the steelmaking-relevant ladle-slag system, but a broader holdout
  would need a second independent primary source in hand (the same gate that blocked the spike).
- `−` The model is **not** validated acid-side or for MnO-rich slags — those remain the named
  source-sensitive edges, exactly as before but now *quantified* (~×4 / ~×5) rather than vague.
- `−` The acidic edge is **one holdout point (Q1)**; its cause is **not isolated** (candidate causes:
  the amphoteric Al₂O₃ value Λ = 0.605, genuinely uncertain, and/or S–S used at the high-alumina
  composition extreme). It is a flag to confirm with more low-Λ data, not an established law.

## Alternatives considered

- **Refit S–S (or the Al₂O₃ optical basicity) to close the acidic edge** — rejected: the model
  already carries in its domain; a refit on 10 points would manufacture coherence and risk the
  amphoteric-Al₂O₃ knob memorising the one acidic outlier. The edge is reported, not tuned away.
- **Lead with, or include in the headline, the MnO tables (more points)** — rejected: MnO Λ is
  fit-to-C_S in `slag.py`, so those points do not test independent inputs. They are kept as an
  explicitly weak-independence diagnostic that *locates* the model's worst error, never as the
  validation claim.
- **Use Table 9's literature values as a second holdout** — rejected: Abraham–Richardson/Kärsrud/
  Kalyanram are pre-1986 and may sit inside the S–S training set. They corroborate the trend (and
  the acidic edge) but cannot be a non-circular holdout.
- **Scrape the measured points from the model/review papers' figures** — rejected: that is the
  single-sourced fabrication path that dropped the "AI Table A7 D_I" ([[di-crosscheck-source]]).
  The build waited for the primary-source PDF with the numbers tabulated as text.
