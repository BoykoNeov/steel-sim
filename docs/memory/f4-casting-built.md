---
name: f4-casting-built
description: "F4 casting (Slice 1: Scheil microseg + Chvorinov + front-to-back handoff) BUILT 2026-06-12; the new-physics reframe, the slice boundary, the two-tier k provenance, next = F2/F3 or Slice 2"
metadata:
  node_type: memory
  type: project
  originSessionId: current
---

**Front-end F4 (casting & solidification, Slice 1) BUILT ✓ 2026-06-12** — the link that **closes the
chain front-to-back inside steel-sim** ([[steel-making-frontend-plan]]; plan `docs/plans/steel-making.md`
§7 = as-built record). `steel/casting.py` (+ `demo_casting.py`, `plots.casting_figure`, `test_casting.py`
17 + `test_demo_casting.py` 5; fast lane **542→564 green**). **No solver, no engine touch, no ADR.**

**THE REFRAME (load-bearing — the plan's premises were wrong):** the user/plan pictured F4 as "thin reuse:
the frozen heat engine + the existing Scheil." Two findings (verify these yourself, don't trust the plan
wording): (1) the repo's "Scheil" is **additivity** (transformation kinetics, `pathint.py`), **NOT
microsegregation** — the solute-redistribution `C_s=k·C₀·(1−f_s)^(k−1)` is *new*; (2) there is **no
solidification thermodynamics** in the repo at all (no liquidus/solidus/latent-heat/partition data). So F4
is a **new-physics phase**, not a reuse. **Advisor's decisive steer:** the front-to-back proof rides on the
**microsegregation → composition handoff through the [[heat-state-spine-built]] spine, NOT the latent-heat
solve** → Slice 1 builds the proof and needs **NO solver at all** (the heat-engine reuse is entirely in
deferred Slice 2). User okayed Slice 1 now / Slice 2 deferred (AskUserQuestion).

**Slice 1 (built):** Scheil microseg + **centerline-enriched Heat** handoff (a real `"cast"` origin
replacing `Heat.from_grade`'s back-end stand-in — `cast_billet` emits nominal + centerline Heats) +
**Chvorinov** `t=B·M²` + liquidus (Won-Thomas Eq.13, T_pure(Fe)=1536). **The proof:** a 4140 casting
heat-treats **non-uniformly** — same oil quench, bulk 64%M/533HV (soft-core) vs enriched centerline
91%M/626HV = **+93 HV hard band** (the §6 uneven-hardenability link), all cited physics.

**VERIFY-THE-DIVERGENCE-FIRST (the gate, advisor):** before building, I probed enriched-centerline comp →
`evaluate` and confirmed the over-hardening is **large and robust across δ/γ + f_s∈[0.9,0.95]** (not
marginal). Lean the enrichment on **substitutional alloys** (Mn/Cr/Mo/Ni/Si — segregate AND drive
hardenability); **carbon EXCLUDED by default** (`enrich_carbon=False`) because Scheil over-predicts
interstitial C (the no-back-diffusion ceiling) — else the headline rests on the most-overstated variable.

**Teeth (could-have-missed):** (1) **conservation mass balance** `solute_in_solid(numeric ∫C_s) +
solute_in_liquid(analytic lever) → C₀` — **CAUGHT A REAL BUG**: my first `scheil_mean_solid` was a uniform
midpoint quadrature that badly under-resolves the f_s→1 singularity → falsely read 0.90 (C), 0.45 (S) not
1.0; the mass-balance form (two independently-written closed forms reconciling) is accurate AND
non-tautological (the advisor's "not 'the closed form integrates to its own value'"); (2) **severity
ordering** smallest-k (S,C,P) enriches the *last liquid* most, Cr/Ni mild — un-tuned data reproducing *why*
S/P are the dangerous segregators. **NB the profile plots LIQUID enrichment** `C_L/C₀=(1−f_s)^(k−1)` not
solid: for tiny-k S, the SOLID stays depleted till f_s≈1 (S rejected to a liquid film → MnS/hot-tear) so a
solid-ratio plot misleads; centerline solid inherits k× the last liquid.

**k PROVENANCE = TWO HONEST TIERS ([[di-crosscheck-source]] lesson, advisor caught the overclaim):**
C/Si/Mn/P/S = **Won-Thomas 2001 Table I, δ AND γ, read from the PDF (primary-source verified)** — the teeth
rest here. Cr/Ni/Mo = **ISIJ in-situ (ISIJ Int. 60(2):2020)**: Cr 0.96, Ni 0.97 ≈constant, Mo 0.70→0.60 —
**γ-mode-measured, used as a SINGLE representative value (δ NOT separately pinned)**; my first pass took
these from a WebSearch *paraphrase* and wrote unsourced 0.86 γ-values + claimed "di-crosscheck applied"
across all — advisor flagged it, I WebFetched the ISIJ paper to verify and softened the claim. δ/γ-differ
test moved to **Si** (Won-Thomas δ0.77/γ0.52, a verified split). Don't let "verified" span data you didn't
crosscheck.

**FRAMING NOTE (user directive):** "frozen engine is an artifact, no frozen engines now" → dropped
frozen/SEALED/Chip-Planet language from F4 docs; solver = a plain library. **Repo-wide CONTRACT.md/ADR/old-
memory de-frost = a SEPARATE pass the user approved for "new work only, for now"** (NOT done — ~15 memories +
`engines/diffusion/CONTRACT.md` still say "frozen"/"SEALED"). Slice-1 doesn't touch the solver anyway.

**Ceiling:** Scheil = no-back-diffusion **upper bound**; δ/γ peritectic (C>0.53%; demo grades below it),
coarsening, f_s→1 singularity (cutoff f_s*=0.95) omitted. Chvorinov B process-specific (rank-grade).
**Slice 2 DEFERRED (named):** latent-heat solidification **T-field map** (apparent-cp/enthalpy — **NOT a
trivial `source` term**: the solver PDE has no LHS capacity coeff, needs a nonlinear consumer-side
formulation; my "source covers it" was optimistic) + defect criteria (Niyama/hot-tear, mostly game-layer).
Map is iconic but does NOT feed the handoff → not gating.

**Next:** build-order item 4 = **F2/F3 (refining + ladle, the middle of the chain)**, OR **F4 Slice 2**
(latent-heat map + defects), then `game/` last. Amends [[heat-state-spine-built]] (its "next=F4" now done).
Surfacing: demo+figure+gallery "Casting (front-end)" card+both READMEs+plan §7. Notebook/app deferred.
