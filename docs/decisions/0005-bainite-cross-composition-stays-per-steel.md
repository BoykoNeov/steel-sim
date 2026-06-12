# 0005 — The bainite cross-composition wall stays per-steel-anchored (refit is a diagnosis, not a law)

Status: Accepted — 2026-06-12
Scope: `steel/kinetics.py` bainite composition factor `BC`, `steel/austemper.py` per-steel
anchoring, and the new validation module `steel/cct_validation.py`. **No engine or frozen
pipeline is touched** — this ADR records a decision to *not* graft a new law, having tried.

## Context

The project repeatedly names a real edge: bainite kinetics are **per-steel only** (the "8620
wall"). The cited Li/KV bainite composition factor `BC = exp(−10.23 + 10.18·C + 0.85·Mn +
0.55·Ni + 0.90·Cr + 0.36·Mo)` has a carbon coefficient (10.18) that dwarfs its alloy
coefficients, so it cannot rank bainite kinetics across compositions. The austempering probe
([[bainite-anchoring-probe]], ADR-less, §13/6d) established this as a **two-steel** negative
(1080 vs 4340: `BC` says 4340 ~7× faster, the atlas measures it ~5× slower) and responded by
anchoring each steel's bainite scale to one cited atlas point — never using `BC` for absolute
cross-steel times.

A validation pass (2026-06-12, §20) was directed to **widen that to N steels and actively
attempt to break the wall** by refitting a bainite composition law. Eight US Steel 1951 IT-atlas
steels (the same already-cited public-domain source) were read at a common austempering-window
observable — the bainite 50 %-transformation time at 700 °F (371.1 °C), where `Mₛ < 371.1 < Bs`
for all eight. The harness predicts each steel's time from one anchor via the real
`BainiteReaction.rate` (carrying the per-steel grain `2^(0.41·G)` and ceiling `Bs − T`), swapping
only the composition factor — a controlled test.

Findings (`cct_validation.grade_factors`, `cited_anchor_wall`, `carbon_rebalance_holdout`):

- **The wall is real and bias-immune.** From the **two cited anchors alone** (no factor-2 reads),
  `BC` inverts the 1080↔4340 ordering by **×41, wrong-signed** — and that ×41 *reproduces*
  austemper's independently-derived 1080/4340 scale gap, confirming the harness.
- **Quantified across 8:** cited `BC` ranks the measured 50 %-line at Spearman ρ ≈ 0.1 — no
  cross-steel order skill. The six new reads were taken **hypothesis-aware** at ~factor-2
  (confirmation-bias exposure, named); the headline rests on the cited anchors, the reads only
  size it.
- **No single cited factor combines ranking with magnitude (both metrics anchor-invariant).** On
  rank skill: `PC` 0.81 > `FC` 0.48 > `BC` 0.10 (the alloy-weighted diffusional factors order
  bainite, the carbon-dominated bainite factor does not). On magnitude spread (std of log-residual,
  the anchor-invariant ×-band): `FC` ~×3.1 tightest, `BC` ~×4.6 (small only because `BC` is nearly
  *flat* — the no-skill mode), `PC` ~×6.7 widest. So `PC` ranks best but scatters widest, `FC` is
  most balanced (yet only ρ ≈ 0.48 / ~×3), none is both. The mechanistic finding: **bainite
  cross-steel retardation is alloy-driven**, which `BC`'s carbon-dominated factor under-weights.
  (Both metrics are anchor-invariant by construction — a single anchor only shifts every
  log-residual by a constant, so it cannot change the order or the spread; an anchor-*referenced*
  "median miss" was deliberately avoided because it flips which factor looks best on re-anchoring.)
- **A one-knob refit confirms the diagnosis, not a law.** Fitting a single parameter (the carbon
  weight λ) on a train split and predicting a disjoint split drives λ to its floor (carbon term
  removed) and lifts TEST ρ 0.4→0.8; a decomposition shows the gain is carried by the residual
  *cited* alloy coefficients (alloy-only ρ ≈ 0.67 ≫ Bs+grain-only ρ ≈ 0.26), not the confounds.

## Decision

**Keep per-steel atlas anchoring; do not graft a cross-composition bainite law into the engine.**
The refit is recorded as a **diagnosis** in `steel/cct_validation.py` and is wired into nothing —
`kinetics.BC` and `austemper.anchored_reaction` are unchanged and the frozen pipeline stays
byte-identical. A genuine replacement law would be new physics and would require its own ADR; this
ADR is the record that the attempt was made and *why it stops at a diagnosis*:

1. **No cited single factor predicts cross-steel bainite magnitude better than ~×3.** `FC` is the
   closest, but it is the *ferrite* factor — borrowing it would be ungrounded for bainite, and it
   still ranks worse than `PC`. None is a defensible drop-in.
2. **The refit is under-identified.** The carbon/alloy axis is confounded: 1080 is the *only*
   no-alloy steel (the low-carbon grades that would decorrelate carbon from alloy sit above `Mₛ`
   at 700 °F and were excluded), and `Bs` (Steven–Haynes) already absorbs carbon dependence. λ→0
   says "alloy drives it, carbon corrupts it," not a trustworthy coefficient.
3. **The data is ~factor-2 and hypothesis-aware.** Eight visual reads of a 1951 scan's faint
   dotted line cannot license a baked-in absolute law ([[di-crosscheck-source]]: verify
   AI-extracted numbers before baking absolutes). The minimal-DOF bound (advisor) was one
   parameter; a 5-coefficient fit would memorise noise.

The study therefore **strengthens** per-steel anchoring: it is principled, not a shortcut — the
cross-composition wall is now *measured* (8 steels), the bug is *located* (carbon over-domination),
and the honest conclusion is that the cited diffusional framework does not carry bainite across
compositions on this evidence.

## Consequences

- `+` The "per-steel only / 8620 wall" edge is now **quantified and explained**, not just asserted
  — a validation increment with teeth (the cited-anchor inversion is bias-immune; the wall ρ ≈ 0.1
  is reproducible).
- `+` **Zero blast radius.** New module + tests + figure + docs only; `kinetics`, `austemper`,
  `unified_kv`, `pathint` untouched and byte-identical. No re-seal, no frozen-surface change.
- `+` The mechanistic finding (alloy-driven bainite retardation, `BC` under-weights alloy) is a
  concrete pointer for any future cross-composition bainite model — and names the cited factors
  that order it better.
- `−` The wall is **not broken** — cross-steel bainite prediction still requires a per-steel atlas
  anchor. This was the likeliest honest outcome (bainite's displacive / incomplete-reaction
  character may be irreducible to the additive-KV undercooling form), and is accepted as such.
- `−` The atlas is **isothermal**: this validates cross-*composition* kinetics, and leaves the
  separate "no measured-CCT validation" gap (§19) exactly where it was — IT anchors do not
  benchmark a continuous-cooling bay.

## Alternatives considered

- **Graft the λ-rebalanced `BC` (or `PC`) into the engine** — rejected: under-identified,
  factor-2, hypothesis-aware data; no cited factor predicts magnitude well enough; would be a new
  physics law masquerading as a fit. Exactly the tautology the non-circularity discipline forbids.
- **Add the 8 steels to `austemper.ATLAS_STEELS` as production anchors** — rejected: the six new
  times are ~factor-2 validation-grade reads, not the carefully-read 1080/4340 anchors; mixing
  them into the austempering recipe path would pollute its precision. They live in the validation
  module, labelled as such.
- **Chase a measured-CCT dataset to attack the other gap instead** — out of scope here and
  provenance-risky (CCT atlases are largely copyrighted; the project commits nothing
  redistributable). The isothermal atlas was already cited and committed-clean.
