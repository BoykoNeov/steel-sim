---
name: temper-embrittlement-built
description: "temper embrittlement (martensitic-P, reversible) BUILT 2026-06-13 — closes P's 2nd half; the paper-nose GATE was run before coding and FAILED → built thin #1 (no tooth), did NOT manufacture one"
metadata:
  node_type: memory
  type: project
---

**Temper embrittlement BUILT ✓ 2026-06-13** — closes phosphorus' **martensitic** path, the named deferral
from [[impurity-consequence-built]]; **P's coverage is now complete** (ferritic cold-short via
`cold_short_check` + martensitic temper-embrittlement via new `temper_embrittlement.py`). Reversible,
alloy-driven: P co-segregates with Ni/Cr to prior-austenite GBs on slow cooling through **375–575 °C** →
intergranular fracture; **Mo ~0.5 % is the cure**; **reversible** (reheat >600 °C + fast cool resets).
`temper_embrittlement_check` orchestrator → the `temper-embrittled` flag (mirrors `heat_treat`/`hot_work`).
Suite 668→**685 green / 2 skipped** (+17), no engine touch, no ADR.

**THE DURABLE LESSON — the paper-nose GATE, run BEFORE coding, FAILED → built the thin slice, did NOT
manufacture a tooth.** This is the discipline the advisor set after I nearly manufactured the Mushet "headline
tooth" last session ([[impurity-consequence-built]]) — applied *successfully* this time. The advisor reframed
#1 (thin, no tooth) vs #2 (build a McLean segregation model for an emergent tooth) as a **gate**: *compute the
would-be tooth on paper FIRST* — "does the embrittlement C-curve **nose** emerge at the observed ~490–550 °C
from independently-cited segregation thermo + diffusion kinetics, without tuning?" Yes→#2; have-to-nudge→#1.
I pinned cited **ΔG_seg(P) = −34469 + 22.9·T J/mol** (Yang–Chen/ORNL & Erhart–Grabke) + cited **D_P(α-Fe) =
8×10⁵·exp(−3.2 eV/kT) cm²/s** (the **α-Fe/BCC** value — advisor's catch: "diffusion is in α not γ"), built a
Langmuir–McLean equilibrium × kinetics calc, and it **COULD NOT PIN THE NOSE**: it runs **~100× faster than
the paper's own anchor** (450 °C → ~10 h) and gives no single time-stable nose. **The honest framing is
"underdetermined," NOT "lands at the wrong place"** (advisor's post-commit catch — verified): the 100× is the
tell, not the verdict — the real kinetics add a Fe₃P-cluster step the model omits, and the verification
(*"does the nose move up or down if you divide D by 100?"*) confirms that **correcting the missing slowness
pushes the peak UP** from ~410 °C **toward** the observed 490–550 window (412→436→462→490 °C as D scaled
1→0.1→0.01→0.001, t=10 h). So the tractable model can't pin the nose and the faithful version needs the
cluster kinetics (out of scope) → **no *claimable* tooth**; I did **not** build the segregation model to land
it → **build #1**. The negative result IS the honest record. (Same class of discipline as the deox-curve
minimum and the Fe–FeS eutectic checks; [[di-crosscheck-source]].)

**The honest map — NO strict tooth in this slice** (cited + by-construction, symmetric with the S/red-short
slice — that's a fine thing to be):
- **By construction (NOT teeth):** the **J-factor `(Mn+Si)(P+Sn)·10⁴`** (Watanabe) — regression-fit, so
  "high J ⇒ susceptible" cannot miss (the advisor's "don't reach for it as a tooth"); the verdict rule
  (susceptible AND exposed-in-window AND not Mo-protected).
- **Cited mechanism INPUTS (verification ≠ tooth):** danger window 375–575 (nose 490–550), ≥600 °C reset,
  0.5 % Mo cure, Ni/Cr promotion.
- **Coherence note (NOT a tooth):** in the registry only the dirty Ni-Cr victim (J 225, no Mo) clears
  `J_SUSCEPTIBLE=150` (a labelled spec like `MIN_MARTENSITE_SPEC`); 1080/1045/8620/4140 (J 108–138) are safe
  **by LOW J, NOT by Mo** — 4140/8620 carry only ~0.2 % Mo, *below* the 0.5 % threshold, so the model never
  marks them Mo-protected (advisor's post-commit catch: don't say "the cure is in the workhorse"). Mo IS the
  cited cure but the demo proves it on the genuinely-susceptible J 225 victim, not on the registry grades.

**Built the RIGHT embrittlement:** *reversible* TE (P GB-segregation, the named deferral) — BUILT;
*tempered-martensite* embrittlement (irreversible ~260–370 °C cementite-film, a different mechanism) —
DEFERRED. Also deferred: absolute ΔFATT (scattered), full Guttmann co-segregation / Fe₃P-cluster C-curve.
Back-end `properties.toughness_index` UNTOUCHED — this is a front-end susceptibility consumer, not a back-end
toughness curve (`steel-production.md` §scope pointer added). Demo `demo_temper_embrittlement` (4 panels:
J-ranking, danger-window cooling-rate control, the four levers, reversibility cycle). Amends
[[impurity-consequence-built]] (its TE deferral now closed). **Next = `game/`** (the full front-end chain +
all consequences now built) or another named deferral.
