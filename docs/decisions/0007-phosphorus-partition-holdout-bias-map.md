# 0007 — The cited Healy phosphorus-partition model is holdout-graded: a quantified bias map, not "validated"

Status: Accepted — 2026-07-06
Scope: `steel/slag.py`'s dephosphorization path (`phosphorus_partition`, the Healy 1970 L_P
correlation) and the new validation module `steel/slag_lp_validation.py`. **No engine or frozen
pipeline is touched** — this ADR records a decision to *keep* the cited model unchanged and *replace
its vague "over-predicts at high lime" caveat with a measured bias map*, having graded it against an
independent measured dataset. It is the **phosphorus twin of ADR 0006** (which did the sulfur / C_S
leg), and closes the first of the two legs `docs/plans/next-directions.md` left open for the front-end
validation direction (B3): the Healy L_P leg. (The second — a second independent slag *system* — stays
open.)

## Context

The front-end refining slice (`slag.py`, [[slag-f2-slice2-built]]) uses Healy (1970) for the
phosphorus partition:

```
log10 L_P = 22350/T + 0.08·%CaO + 2.5·log10(%Fe_t) − 16     (T in K),   L_P = (%P)_slag / [%P]_metal
```

That module flagged the absolute correlation as the **source-sensitive tier** — "ranking + order of
magnitude only" — with a specific hand-waved weakness: Healy is "known to *over*-predict at high
lime." ADR 0006 holdout-validated the *C_S* leg but explicitly left Healy's L_P uncovered. The named
follow-up (B3, phosphorus leg) is to apply the same `cct_validation.py` / `slag_validation.py` pattern
to Healy: grade it against measured L_P **from a source the fit could not have seen**, and turn the
vague caveat into a number.

The crux is the same **circularity gate**: Healy is a regression *fit*, so grading it against its own
training data is the vacuous-benchmark trap. The block that deferred the C_S spike was
**extractability to the [[di-crosscheck-source]] standard** — it was cleared here the same way, by
obtaining the **primary source in hand**: Drain–Monaghan–Longbottom–Chapman–Zhang–Chew, *ISIJ
International* **58** (2018) 1965, an **open-access** paper (CC BY-NC-ND) whose Table 4 tabulates 33
measured equilibrium heats directly (committed at `docs/sources/drain_2018_phosphorus_partition_bos.pdf`).

Two facts make the chosen holdout (`slag_lp_validation.HOLDOUT`, Drain Table 4,
CaO–SiO₂–MgO–FetO–(MnO–Al₂O₃–TiO₂–P₂O₅)) a clean out-of-sample test — in fact *cleaner* than the C_S
leg's:

1. **Temporal independence** — measured 2018, **forty-eight years after** the 1970 correlation, in a
   different laboratory (Wollongong / BlueScope). It cannot be in Healy's fit.
2. **Parametric independence** — Healy's L_P reads **only** %CaO, total slag iron %Fe_t and T, with
   four fixed 1970 coefficients and **no optical basicity** in the formula. So — unlike
   Sosinsky–Sommerville, whose fitted MnO/FeO Λ forced the C_S holdout to dodge those oxides — there is
   not even a fitted-Λ input to avoid. The composite under test has **zero parameters fit to these
   data**.

The measured L_P is defined **exactly as Healy's** — the mass ratio (%P)/[%P] (Drain Eq. 8), not a
phosphate capacity C_PO₄ and not a distribution on (%P₂O₅) — so the numbers are directly comparable
with no standard-state offset. The experimental temperatures (1550–1700 °C) are the steelmaking range
Healy addresses; the slag basicity `v = %CaO/%SiO₂` sweeps ≈ 1.8 → 5.6, i.e. from Healy's fit domain
up into a **high-lime extrapolation** — the region the flag already warned about.

**Two transcription guards** run in the suite (Table 4 has no repeat-reading column, so the C_S leg's
single guard is replaced by two): (a) `validate_lp_consistency` recomputes L_P from each row's
(%P₂O₅) and [%P] columns and brackets the tabulated L_P (a typo in any of the three P columns breaks
the bracket; coarse on the lowest-[%P] rows, a named limit); (b) `reproducibility_crosscheck`
recomputes the seven R-series repeats' mean and standard deviation and reproduces the paper's
**prose-stated** "mean L_P 190, std 7" — cross-checking the L_P column against a statistic printed
outside the table, and fixing the ~3.7 % measurement scatter floor.

Findings (`slag_lp_validation.summary`, computed not asserted):

- **It carries at moderate basicity.** On the B2 series (v ≈ 2, %CaO ≈ 46 — Healy's own fit domain)
  the model is near-exact: mean bias ≈ ×1.02. The pooled fit over all 33 points is a mild
  over-prediction, ≈ ×1.48 with ×1.54 scatter — inside the factor-2–3 such correlations carry.
- **It over-predicts at high lime — the pre-registered flag, now measured.** The bias is **not
  uniform: it climbs monotonically with basicity** — B2 (v≈2) ×1.02 → R (v≈2.8) ×1.18 → T (v≈2.7)
  ×1.39 → B4 (v≈4) ×1.95 → B5 (v≈5) ×1.98; and on the raw lime axis, %CaO < 50 → ×1.13 vs %CaO ≥ 55 →
  ×2.29. The mechanism is structural: Healy's +0.08·%CaO term is **linear and unbounded**, but the
  real L_P **saturates** with basicity (Drain, and others, report L_P levelling beyond v ≈ 2.5). So
  extrapolating the linear-lime term above its fit domain inflates L_P.
- **The temperature direction is right (magnitude confounded).** The dedicated T-series (rows 8–10,
  1550 → 1700 °C) has measured L_P falling with temperature, and Healy's +22350/T term reproduces that
  direction. It is **not** a cleanly isolated slope — the three points co-vary in composition (FetO
  16 → 22 %) — so the direction is confirmed but the magnitude is confounded; reported as such, not as
  a second independent axis (contrast the C_S leg, where a genuinely isolated T-slope *was* the tooth).
- **A named structural ceiling.** The dataset documents a maximum L_P at ≈ 20 % FetO for a given
  basicity; Healy's +2.5·log(%Fe_t) is monotonic and cannot represent that optimum — a structural
  limit of the bulk correlation, named, not a fitted defect.

## Decision

**Keep the cited Healy L_P correlation unchanged; replace `slag.py`'s vague "over-predicts at high
lime" caveat with the measured bias map — ≈ ×1.0 at v≈2 rising to ≈ ×2 at v≈5 (%CaO ≥ 55 ≈ ×2.3) —
and keep the L_P leg's posture at "benchmarked / order-of-magnitude," _not_ upgraded to "validated."**
The validation lives in `steel/slag_lp_validation.py` and is wired into nothing —
`slag.phosphorus_partition` is byte-identical and the frozen pipeline is untouched.

This is deliberately a **weaker** conclusion than ADR 0006's. There the attempt to break the C_S
correlation ended in an out-of-sample *pass* (upgrade to "holdout-validated"). Here the attempt to
break Healy's L_P ended in a *located, quantified failure* of exactly the weakness the module already
flagged — plus a positive "carries at moderate basicity" result. The honest outcome is therefore a
**bias map, not a validation**: the high-lime over-prediction is real and ~×2, so calling L_P
"validated" would overclaim. No parameter is fitted or grafted — a refit is unlicensed (it would
manufacture coherence over a structural, saturating-vs-linear mismatch, and the model already carries
in its domain).

## Consequences

- `+` `slag.py`'s L_P claim is now **measured, not asserted** — the "over-predicts at high lime" flag
  is a number (≈ ×1.0 → ×2 across v≈2 → 5) with a stated mechanism, at the same non-circularity rigour
  as ADR 0006 (independent dataset, two transcription guards, edges named).
- `+` **Zero blast radius.** New module + demo + figure + gallery/README rows + tests + the committed
  primary-source PDF; `slag.py` and every engine module untouched and byte-identical (only docstrings
  and comments in `slag.py` changed).
- `+` The bias map is concrete caller guidance: trust Healy L_P to ~×1.1 at moderate basicity, expect
  ~×2 over-prediction at high lime, and do not read the ~20 % FetO optimum from it at all.
- `−` The finding rests on **one system / one temperature for most points** — 33 heats, 30 of them at
  1650 °C, one slag family (Drain's). It is a steelmaking-relevant BOS system, but a broader holdout
  (a second lab's L_P, or a wider temperature spread with fixed composition) would strengthen the
  temperature leg, which is confounded here.
- `−` The metal-partition conversions (C_S→L_S) remain uncovered by any holdout — order-of-magnitude,
  as before.

## Alternatives considered

- **Refit the 0.08·%CaO term (or add a saturation term) to close the high-lime bias** — rejected: the
  model already carries in its fit domain, the mismatch is a *structural* saturating-vs-linear one (not
  a coefficient a 33-point refit should memorise), and a refit would break the "cited, not calibrated"
  posture the whole front end holds. The bias is reported, not tuned away.
- **Upgrade L_P to "holdout-validated" (parallel to ADR 0006)** — rejected as overclaiming: the
  high-lime over-prediction is a real ~×2, not the mild uniform C_S bias. The honest label is
  "benchmarked, with a measured bias map."
- **Grade Healy against another *correlation* (Assis, Suito–Inoue) instead of measured heats** —
  rejected: those are fits too, so it would compare models, not test one against data. Drain's **own
  measured heats** are the holdout; that the authors separately compare them to Assis is irrelevant to
  grading Healy.
- **Use the MDPI Assis 2019 EAF dataset** — set aside: it 403'd on fetch, and its high-alumina EAF
  slags test Healy further out of domain than the BOS system does. Drain's open-access BOS table is the
  cleaner in-domain holdout; the EAF/alumina extension is a named future option, not this build.
