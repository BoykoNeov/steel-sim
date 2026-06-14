---
name: gas-porosity-built
description: "Gas (CO) porosity consequence BUILT — F2's deferred porosity-risk closed as a carbon-aware CO criterion"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1f4b9c60-acbe-4fcd-a034-bbdfb696b54a
---

**Gas (CO) porosity — the dissolved-oxygen consequence BUILT ✓ 2026-06-14** (user picked it from a "what's
next" menu after TME). Closes F2's deferred `porosity-risk` (the sibling of [[hydrogen-flaking-built]] — the
other F2 dissolved-gas consequence). `steel/gas_porosity.py` + demo + `plots.gas_porosity_figure` + 17 + 6
tests; **741 → 764 green (+23)**; **standalone, NO engine / NO ADR**; gallery card + root-README tour row.

**Two-tier flag:** refining's carbon-blind `porosity-risk` (O > 30 ppm) → new `gas-porosity` consequence.
Mirror of cold-short(propagation)/red-short/flaking. **Where flaking's 2nd lever was geometric, this one is
the CARBON.**

**Model = carbon-aware CO product, the SAME C–O equilibrium F2 runs on.** CO evolves where `[%C]·[%O] > K_CO`
(`refining.carbon_oxygen_product` at freezing-front T≈1530 °C / p_CO=1). Verdict = supersaturation
`S = [%C][%O]/K_CO > 1`. **Cooling-supersaturation is the real mechanism**: heat equilibrates with CO at tap
(1600) but K_CO *falls* on cooling to the front → a tap-line (undeoxidized) heat tips porous; killing it
(O below the line) buys margin. No solver — latent-heat field would buy no new content (B-over-C logic).

**TWO advisor catches BEFORE writing (paper-gate), both load-bearing:** (1) **Do NOT Scheil-enrich dissolved
O** — reprecipitation pins O in killed steel, so naive O-Scheil is WRONG (false-positives sound killed
steel), not a "named ceiling" → **hold O at as-refined** (bonus: no k_O to pin). (2) **Carbon-Scheil is a
trap** — `casting.py` disowns it (`enrich_carbon=False`). My spot-check confirmed worse than feared: a
*well-killed high-C* heat (1.0%C/3ppm) crosses at f_s≈0.90 → enrichment-verdict false-flags it porous, yet
1095/52100 cast sound (Scheil f_s→1 singularity). → **bath product = load-bearing verdict; carbon-Scheil only
a conservative DECORATIVE secondary** (`solidification_co_fraction`, cutoff-dominated, never pass/fail).

**NO claimable tooth — by-construction + cited inputs (reversible-TE/TME landing, a feature).** Criterion IS
the cited C–O equilibrium vs held composition → can't independently fail. Soft OoM note (really
by-construction): `O_crit(C)=K_CO/C` falls as 1/C, no tuning → "high-C must be killed, low-C can be rimmed";
the flat 30 ppm spec crosses O_crit at C≈0.67% (leaner over-warns, richer under-warns).

**Hero = same oxygen, carbon decides** (non-duplication made the demo's job, per advisor): 1080 & 8620 same
light kill, **both within 30 ppm spec (both risk-cleared)**, yet 1080 (O_crit≈25) blows holes carrying LESS O
than the sound 8620 (O_crit≈100); full kill saves 1080 (deox lever). **The two flags disagree because of
carbon** — else it's refining restated. **1080's modest S≈1.05 is SIGN-ROBUST not marginal (advisor
sharpening, verified):** C–O coupling self-limits a high-C heat's O to ~its C–O equilibrium → under-killed
1080 sits *exactly on the tap C–O line* (`C·O=K_CO(1600)` to machine precision) → verdict reduces to the
**cooling-supersaturation ratio `K_CO(tap)/K_CO(front)`**, `>1` for ANY front below tap (certain, not a
coin-flip on the 1530 pin; grows as front cools — S 1.000@1600/1.051@1530/1.091@1480); ~7% absolute scatter
CANCELS in the ratio (slope better-constrained than absolute). High-C steel is never *deeply* O-porous — it
lives at the boundary and must be killed — but the verdict *sign* is guaranteed.

**Ceiling:** CO-evolution criterion, not bubble nucleation/escape kinetics; p_CO=1 atm (ferrostatic head deep
in a tall section = named over-conservatism); shrinkage/Niyama porosity (a feeding problem) stays the
F4-Slice-2 deferral. **Hot-tear is the last open F4/F2 defect.** Amends [[refining-f2-built]]; sibling
[[hydrogen-flaking-built]] / [[impurity-consequence-built]].
