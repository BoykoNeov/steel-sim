# 0009 — The cited C_S→L_S conversion is probed against measured sulfur distribution: order-of-magnitude, not upgraded

Status: Accepted — 2026-07-10
Scope: `steel/slag.py`'s desulfurization path (`sulfur_partition` — the capacity→metal-partition
conversion `log L_S = log C_S − log a_O − 770/T + 1.30`) and the new validation module
`steel/slag_ls_validation.py`. **No engine or frozen pipeline is touched** — this ADR records a
decision to *keep* the cited conversion unchanged and *leave L_S order-of-magnitude*, now probed across
a second regime. It closes the last of the B3 residual gaps `docs/plans/next-directions.md` left open:
"the C_S→L_S conversion, still order-of-magnitude."

## Context

ADR 0006 holdout-**validated** the sulfur *capacity* `C_S` (Sosinsky–Sommerville, gas–slag, Nzotta
1998) — upgrading it to "~×1.4 within the basic domain." ADR 0007/0008 graded the *phosphorus*
metal-partition `L_P` (Healy) against two slag systems. But `L_S` — the sulfur **metal**-partition that
`slag.desulfurize` actually computes — was never graded, and the step that turns the validated `C_S`
into `L_S` (the `−log a_O` term, the module's headline desulfurization physics and the mirror of
Healy's `+2.5·log %Fe_t`) had no holdout. Its posture stayed "order-of-magnitude only."

**The a_O-provenance gate is what makes or breaks this leg.** The whole point of `L_S` is the `−log a_O`
term, so the test is clean *only if the metal oxygen is set independently* — not back-derived from a
deoxidation equilibrium ([Al]/[O], [Si]/[O]), which would import an external deox model into the exact
term under test (the `L_S` analog of the carbon-saturation strawman ADR 0008 rejected). That rules out
most ladle-metallurgy `L_S` data (Al-killed). The clean shape is **controlled-atmosphere gas–slag–metal
equilibration**, where pO₂ (hence a_O) is fixed by the gas — the analog of Nzotta's gas–slag method.

**The source that clears the gate** is the Mohassab flash-ironmaking corpus: MgO-saturated
CaO–FeO–Al₂O₃–SiO₂ slag vs **liquid low-carbon iron** under **H₂/H₂O, CO/CO₂ and CO/CO₂/H₂/H₂O** gas
mixtures at 1550–1650 °C, pO₂ (hence a_O) fixed and computed from the gas by HSC. Peer-reviewed
(*Ind. Eng. Chem. Res.* **51** (2012) 3639, DOI 10.1021/ie201970r; *Steel Research Int.* **86** (2015)
753); the tabulated data used is from the **open** PhD dissertation (Y. Mohassab, Univ. of Utah 2013,
`collections.lib.utah.edu/ark:/87278/s6mp8bdj`), Ch. 4, Tables 4-1/4-2 (36 H₂/H₂O heats) and Table 4-3
(20 heats across the three atmospheres). Unlike the CC-BY-NC-ND sources of ADR 0006–0008, the
dissertation is **All Rights Reserved**, so its PDF is **cited and transcribed, not committed** —
numerical data are facts, and the transcription guards stand in for "primary source in hand." (This is a
deliberate methodological point: the committed-PDF convention of the prior legs was a *convenience* of
their OA sources, not a requirement — the discipline is reading and transcribing the primary source with
guards, which is satisfied here.)

**Two transcription guards** run in the suite: (a) `validate_logls_consistency` — Table 4-1's three
chemically-linked columns must satisfy `Log(Ls) = log₁₀[(%S)/[%S]]`; (b) `validate_oxide_sum` — every
row's five oxide columns sum into the MgO-saturated closure band (100–112 %). The Log(Ls) guard **caught
a source inconsistency**: dissertation row **S8** prints `(S)=2.03, [%S]=6.21, Log Ls=−0.10`, but
`log₁₀(2.03/6.21) = −0.49`. A di-crosscheck against the *rendered* PDF confirmed the transcription is
faithful and the *source itself* is internally inconsistent (its twin row S4, also Log Ls −0.10, has a
different `(%S)/[%S]`, so which column is the typo is unresolvable). S8 is **excluded** — an unresolvable
source typo is dropped, not baked — and the exclusion is recorded (`SOURCE_INCONSISTENT_ROW`).

Findings (`slag_ls_validation.summary`, computed not asserted — the compute-before-framing discipline):

- **Order-of-magnitude, with a systematic under-prediction on the clean-a_O reducing set.** On the 8
  **waterless CO/CO₂** heats (dilute metal S ⇒ `f_S ≈ 1` — the cleanest subset) the full chain
  `Λ → C_S → (−log a_O) → L_S` under-predicts `L_S` by a **factor of several**, and *both* a_O methods
  (gas-fixed, and the engine's own `metal_oxygen_for_feo`) agree on the **direction**. The 35 **H₂/H₂O**
  heats (an oxidizing supplement, [S] = 5–12 wt %, `f_S` broken) straddle unity and are shown, not
  headlined. Across both regimes the agreement is order-of-magnitude — matching `slag.py`'s existing
  `L_S` posture in a *new* regime (BF slags, moderate basicity, higher oxygen) than the ladle anchor it
  was written for.
- **Signed edge #1 — the measured atmosphere ladder.** At matched pO₂/basicity/T the **measured** `L_S`
  rises `CO/CO₂ (≈0.9) → CO/CO₂/H₂/H₂O (≈2.2) → H₂/H₂O (≈4.7)` — water dissolving in the slag lowers the
  sulfide activity coefficient `f_S²⁻` (Mohassab Figs 4-8/9). The engine has **no atmosphere term** —
  which is *why* the clean grade uses the waterless CO/CO₂ subset and treats H₂/H₂O as a supplement, not
  a matched-condition engine failure (a real ladle is not under a controlled H₂/H₂O atmosphere).
- **Signed edge #2 — the shared-axis oxygen anchor.** `metal_oxygen_for_feo` (the `a_FeO ≈ X_FeO`
  Raoultian bridge) reads ~×2 **below** the gas-equilibrium a_O across the set — a located
  order-of-magnitude bias, from Raoultian FeO activity under-reading its positive deviation in basic
  slags.

## Decision

**Keep the cited C_S→L_S conversion unchanged; leave the `L_S` posture at "order-of-magnitude only,"
now probed across a second regime (BF slags) rather than merely asserted; record the atmosphere and
anchor edges.** The validation lives in `steel/slag_ls_validation.py` and is wired into nothing —
`slag.sulfur_partition` is byte-identical and the frozen pipeline is untouched.

This is a **probe that confirms the existing posture, not an upgrade** (deliberately weaker than the
`C_S` leg's "validated"), because three structural confounds mean the data **cannot isolate the
conversion**:

1. **The conversion is inseparable from the C_S baseline, which is itself unvalidated here.** The graded
   number is the whole `Λ → C_S → L_S` chain; ADR 0006 validated `C_S` only for **FeO-free** basic
   slags, and these carry 10–53 % FeO, whose Λ = 1.00 is the *fitted* value the C_S leg excluded. Any
   residual is a sum of C_S-baseline and conversion error that **cannot be apportioned**.
2. **The `−log a_O` slope cannot be isolated.** In gas-controlled equilibration the slag FeO is set by
   the gas, so pO₂ and FeO co-vary, and FeO is a basic oxide (Λ = 1.00) — the desulfurization `−log a_O`
   penalty and FeO's basicity benefit are structurally coupled, with no matched-composition/different-pO₂
   pairs. **This is the desulfurization analog of the L_P single-temperature confound (ADR 0007/0008):
   the term one wants to test co-varies with composition in *all* clean data. Both B3 residual gaps hit
   the same structural wall** — the intellectual core of this leg.
3. **Part of the absolute offset is a standard-state artifact, not the engine.** The conversion's `+1.30`
   embeds an oxygen standard-state term; reconstructing a_O from pO₂ uses an independent Fe–O equilibrium
   constant (Sigworth–Elliott), so a mismatch is a constant method offset — which is why the gas-a_O and
   FeO-anchor grades differ by ~×2. The *magnitude* of the bias is not trustworthy; only its **direction
   and order of magnitude** are.

No parameter is fitted or grafted — a refit would manufacture coherence over confounds the data cannot
resolve, and would falsely upgrade a conversion the holdout can only bound to order-of-magnitude.

## Consequences

- `+` The last B3 residual gap is **closed on the honest terms the data supports**: `L_S` is probed
  against 43 independent gas-controlled heats across a new regime and confirmed order-of-magnitude, with
  two located edges (atmosphere, anchor) and a stated mechanism for each.
- `+` **Zero blast radius.** New module + demo + figure + gallery/README rows + tests; `slag.py` and
  every engine module untouched and byte-identical (only the module docstring's posture paragraph
  changed). No PDF committed (rights-respecting; data transcribed + cited).
- `+` The **compute-before-framing discipline held twice**: it demoted an initially-hoped "carries to
  ×2" (Table 4-1, `f_S` broken) to the honest "under-predicts on the clean set," and the transcription
  guard caught and excluded a genuine source typo (S8).
- `+` The **structural meta-point is now on the record**: both residual B3 gaps (L_P temperature, L_S
  `−log a_O`) are non-isolable for the same reason — the term under test co-varies with composition in
  all clean equilibrium data.
- `−` `L_S` is **not upgraded** to "validated" like `C_S` — the conversion could not be isolated from the
  (FeO-laden, hence unvalidated) `C_S` baseline; the leg bounds the composite, not the conversion alone.
- `−` The clean grade rests on **8 waterless heats** at moderate basicity in a **BF-slag/oxidizing**
  regime, not the reducing ladle `slag.desulfurize` targets — so the ladle end (L_S ~10²–10³) remains an
  extrapolation of a conversion confirmed only to order-of-magnitude here.
- `−` The **atmosphere edge is outside the engine's scope** (no ladle runs under controlled H₂/H₂O), so
  it is a documented data property that disqualifies the H₂/H₂O subset for grading, not a behaviour the
  pipeline exercises.

## Alternatives considered

- **Headline the Table 4-1 (H₂/H₂O) ×0.65 grade** — rejected: that set has metal [S] = 5–12 wt % (SO₂-
  imposed), so `f_S ≈ 1` is badly broken and the flattering near-unity number is not trustworthy. The
  cleaner (dilute-S) Table 4-3 CO/CO₂ set is *worse* (under-predicts), and honesty requires leading with
  it; Table 4-1 is a caveated supplement.
- **Upgrade `L_S` to "validated ~×N" like C_S** — rejected: the ~×2–6 factor is not resolvable (C_S
  baseline unvalidated on FeO slags, `−log a_O` non-isolable, a_O standard-state offset), so an upgrade
  would over-claim. Order-of-magnitude is what the data supports.
- **Grade against Al/Si-killed ladle L_S data** (abundant, ladle-relevant) — rejected on the
  a_O-provenance gate: a_O there is back-derived from a deox equilibrium, importing an external model
  into the exact `−log a_O` term under test.
- **Fall back to the other residual gap (the L_P single-temperature confound)** — set aside: it is
  intrinsically data-starved (fixed-composition/varying-T L_P barely exists, for the *same* structural
  reason), and the L_S leg tests the never-graded metal-partition the pipeline actually uses. The
  shared structural wall between the two gaps is itself the finding.
- **Refit / add an atmosphere or FeO-basicity term to the conversion** — rejected: it breaks the
  "cited, not calibrated" posture, the engine never sees controlled-atmosphere slags, and the edges are
  reported, not tuned away.
