---
name: f1-ellingham-built
description: "F1 Ellingham (front-end first slice) BUILT 2026-06-12 — reduction.py, standalone, the verified/by-construction split, the crossover teeth, next = heat_state.py"
metadata: 
  node_type: memory
  type: project
  originSessionId: 710aa9bb-3c78-4ec1-8804-6faadd3f1fc4
---

**Front-end F1 (Ellingham reduction thermodynamics) BUILT ✓ 2026-06-12** — the first slice of
the steel-*making* half ([[steel-making-frontend-plan]]; plan `docs/plans/steel-making.md` §7 =
as-built record). `steel/reduction.py` (+ `demo_reduction.py`, `plots.ellingham_figure`, 17+3
tests; fast lane **526→546 green**). **Standalone — no engine touch, no back-end touch, no ADR**
(this plan is the record); same additive-new-module posture as grain/residual.

**Physics.** Per-species standard ΔHf,298 / S°298 (Fe, FeO, Fe₃O₄, Fe₂O₃, C(gr), CO, CO₂, H₂,
H₂O(g) + Al/Si/Mn/Cr/Ca oxides for the hierarchy) → reaction ΔG°(T)=ΔH°−T·ΔS° **per mole O₂** (the
Ellingham normalization — the registered unit trap). **No fitted constant** — every number is a
sourced physical constant.

**The non-circularity split (load-bearing, advisor-shaped — like test_grain.py):**
- **Teeth (un-tuned data, could-have-missed):** (1) carbon/wüstite crossover lands **746 °C**
  (window **650–800** deliberately generous); (2) Fe₂O₃→Fe₃O₄→FeO→Fe stack orders right (the
  **stepwise inter-oxide reactions** `6FeO+O₂→2Fe₃O₄` etc., not the bare formation lines —
  advisor caught that the sequence lives there); (3) Ca<Al<Si<Mn<Cr<Fe hierarchy orders right;
  (4) **honesty bound** — linear ΔCp=0 model hits the famous JANAF ΔfG°(CO,1000 K)≈−200 kJ/mol
  anchor to <1 kJ → omitted-kink error is small.
- **By construction (NOT teeth, framed as such):** element/O balance (typo guard), ΔG°(298)≡
  ΔH−298ΔS identity (tautological), Hess path-independence (automatic from state-function data).

**[[di-crosscheck-source]] applied:** the crossover is a **ratio of differences of large numbers**
→ hypersensitive, so ΔHf/S° were **WebFetch-verified vs NIST/CODATA before pinning** (CO −110.53/
197.66, CO₂ −393.51/213.79, Fe₂O₃/Fe₃O₄, FeO S°=60.75). **FeO is non-stoichiometric** (wüstite
Fe₁₋ₓO): ΔHf ranges **−266…−272 kJ/mol** → crossover **710…746 °C** — both in-window; that range
is *why* the window is generous not pinned (don't tune the data to pull 746→canonical-727).

**Scope ceiling (named):** straight lines, **ΔCp≈0 → melting/boiling KINKS OMITTED**; reduction
sequence is the high-T one (wüstite disproportionates <≈570 °C, not encoded). pO₂ **built**
(`equilibrium_oxygen_pressure` = the oxygen-potential ladder, bridge to F2); CO/CO₂ & H₂/H₂O
**nomographic margin scales deferred** (viz flourish).

**Surfacing:** demo + banked figure (`docs/figures/steel-ellingham.png`, 2-panel: Ellingham + pO₂
ladder) + gallery card (new **"Ironmaking"** section, regen `index.html` → [[gallery-page]]) +
root-README tour row. **Notebook & app DEFERRED** (advisor: both surfaces are 100% heat-treatment-
framed; an ironmaking section is a narrative call for when there's >1 front-end phase to anchor it).

**Next front-end slice = build-order item 2: `heat_state.py`** — the `Heat` physical-state record
+ thin orchestrator seam (unpacks Heat→arrays→frozen engine→repacks; engines stay array-in/out).
Then F4 casting (reuses frozen heat engine + Scheil), then F2/F3, then `game/`.

**UPDATE 2026-06-12: item 2 (`heat_state.py`) now BUILT → [[heat-state-spine-built]].** Next is
build-order item 3 = **F4 casting** (frozen heat engine in heat mode + the existing Scheil).
