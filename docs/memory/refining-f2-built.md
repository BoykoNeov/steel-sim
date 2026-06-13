---
name: refining-f2-built
description: "front-end F2 (primary refining — decarb/deox/degas) BUILT 2026-06-13; the gas/inclusion-field-filling middle of the chain, carbon-axis validated, slag partition deferred to Slice 2"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba27d758-2b7d-4c48-9812-f3db100496a1
---

**front-end F2 (primary refining, Slice 1) BUILT ✓ 2026-06-13** — the **middle of the chain** (BOF/EAF
between F1 ironmaking and F4 casting): `refining.py` + `demo_refining.py` + `plots.refining_figure` + 26
tests (`test_refining.py` 20 + `test_demo_refining.py` 6); fast lane 588→**614 green**; **no solver, no
engine/back-end touch, no ADR** (plan §7 is the record). The user's ask was literally "exercise the Heat
gas/inclusion fields that currently sit None" → F2 **fills** `oxygen_ppm`/`hydrogen_ppm`/`nitrogen_ppm`/
`inclusion_*` (None since the spine).

**Advisor reframe BEFORE any code = the crux (my first honesty read was half-wrong).** I framed F2 as
"back end doesn't consume O/N/H → F2 only *fills fields*, F1-like." Advisor: the back end **does** consume
**carbon**, and the blow sets it → **over-blow → C below target → the EXISTING `heat_state.heat_treat`
raises soft-core** = a genuine *validated* end-to-end propagation. But the exact analogue is the **spine's
Cr/Mo under-dose** (a chosen composition/control error reaching the benchmarked back end), **NOT F4's band**
— F4's Scheil *computes* the enrichment from new cited physics, whereas **F2's new physics (C-O/deox/Sieverts)
ALL sit on the DEFERRED-consequence side** (oxygen→porosity, H→flaking, hot-tear → F4-Slice-2/game-layer,
§6 "F2 new + F4 new"). Got this phrasing wrong in 4 durable docs first pass → fixed (the done-review note).

**Two more advisor catches that shaped the build:** (1) **oxygen was backwards** — carbon-saturated charge
is high-C/**LOW-O** (~5 ppm), O *rises* through the blow (0.40%C→53ppm, over-blow 0.20%C→105ppm), peaks at
turndown (inverse C-O product). (2) **the deox curve has a MINIMUM** — a dilute Henrian model is a monotonic
cartoon that silently drops the diagram's most famous feature → **include `e_O^Al`**. Done. (3, done-review)
the K-independence test was **vacuous** (asserted the closed form `−m/(n·ln10·e_O)` equals itself) → fixed to
a **numerical argmin on the curve** for two K's (my own teeth-vs-by-construction discipline).

**Constants (di-crosscheck applied — [[di-crosscheck-source]], two tiers like F4's `k`):** robust-anchor
**teeth** — C-O product `[%C][%O]≈0.0022` @1600C (ΔG°=−19840−40.65T, Vidhyasagar/JSW AISTech 2023 + standard;
**benchmarked vs measured** BOP 27±3 / EAF 26±2 ppm·%C, higher than 22 equilibrium from slag FeO); Sieverts
**H≈26 ppm** (logK=−1900/T+2.423) and **N≈450 ppm** (ΔG°=3598+23.89T Pehlke-Elliott; cross-checked 3000ppm@50atm
→424@1atm); **e_O^Al=−3.9** (Sigworth-Elliott 1974, verified in the AIST interaction-param table). Source-
sensitive tier = absolute deox K_Al/K_Si/K_Mn (Turkdogan-class; Al-O equilibrium scatters factor-several →
ranking + order-of-magnitude only). **Deox hierarchy Al≫Si>Mn COMPUTED from pinned constants AND verified to
match F1's Ellingham oxide-stability order** (Al₂O₃<SiO₂<MnO) — independently sourced (Henrian deox vs Raoultian
ΔG°f) so the agreement is a real cross-module coherence tooth, *computed not asserted* (advisor: "compute the
consistency"). **Al-O minimum at ~0.074% Al** (= −m/(n·ln10·e_O^Al)) — its **location is K-independent**, so the
headline tooth doesn't ride the scattered K_Al; only the depth (~4 ppm) moves with K.

**Carbon-axis operating point (probed in the back end first, not assumed):** 4140 alloy backbone (held fixed —
alloy trim is F3's job, holding it isolates the carbon axis), **oil Ø15mm**: on-target 0.40%C → 94%M/628HV
through-hardens; over-blow 0.20%C → 84%M/450HV **soft-core**. (Lean steels go 0%M at oil/thick — the carbon
soft-core split only shows for an alloy backbone at a discriminating section.)

**Seam:** `from_hot_metal` (high-C/low-O charge) → `decarburize` (C↓ O↑, no flag — consequence downstream) →
`deoxidize` (O↓ + Al₂O₃ inclusion fields, **porosity-risk** flag if under-killed, O>30ppm spec) → `degas`
(H/N via Sieverts, **hydrogen-flaking-risk** flag if under-degassed, H>2ppm spec). **Nitrogen is reported,
NOT spec-flagged** (the Sieverts value is the solubility *limit* ~399ppm, not kinetically-limited actual — a
hard N spec would flag every heat; labelled "(limit)" on the trail). Spec thresholds = labelled design
requirements (like `MIN_MARTENSITE_SPEC`), not fitted constants.

**Ceiling (named):** equilibrium endpoints, never the transport *rate* (blow/flotation/pickup kinetics = the
front-end tar pit, §4); dilute Henrian, single dominant deoxidizer, f_M≈1; dissolved gas = solubility limit;
inclusions = *generated* oxide (flotation removal not modelled). **Slag partition (L_S/L_P vs basicity —
desulf/dephos) = Slice 2 DEFERRED** because the `Heat`/`Steel` carries **no S/P state field** (a state extension
is its own call — advisor: don't bolt S/P on just to widen the slice).

**Surfacing:** banked figure (`docs/figures/steel-refining.png`: 2×2 — deox curve+minimum, C-O coupling,
Sieverts √p, carbon-axis propagation), gallery **"Refining (front-end)"** card ([[gallery-page]], inserted
before Casting so the front-end reads chain-forward), both READMEs, plan §7/§13 as-built. **Notebook & app
deferred** (heat-treatment-framed, same as F1/spine/F4). **Next = F3 (ladle trim — the hero-demo off-spec
input)** or a Slice 2 (F2 slag partition / F4 latent-heat map). Amends [[f4-casting-built]] /
[[heat-state-spine-built]]; builds on [[steel-making-frontend-plan]].
