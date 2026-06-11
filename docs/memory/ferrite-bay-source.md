---
name: ferrite-bay-source
description: "Steel Phase 6a+6b — cited Li(1998)/Kirkaldy–Venugopalan proeutectoid-ferrite (and pearlite/bainite) CCT-start kinetics + composition factors that kinetics.py pins; 6b = bainite reaction BUILT standalone but the bay PROVEN unrealisable in this model (descoped negative result)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3b3ab216-e0f7-4ebd-96fa-a7d99f73616f
---

Source pinned for **Steel Phase 6a** (the proeutectoid-ferrite bay, `kinetics.py` §5):
the **Li, Niebuhr, Meekisho & Atteridge (1998)** "A computational model for the prediction
of steel hardenability", *Metall. Mater. Trans. B* 29:661 — the **modified Kirkaldy–
Venugopalan** (1983, *Phase Transformations in Ferrous Alloys*) semi-empirical CCT model.
Equation form **verified via the academia.edu copy of the Li 1998 paper** (WebFetch, 2026-06-09);
qualitative behaviour cross-checked against the open MDPI "Rapid CCT Predictor" and the Cambridge
phase-trans notes.

**The reaction-start kinetics** (per diffusional reaction; site-saturation):

    τ(X,T) = S(X) / [ 2^(0.41·G) · ΔT^n · exp(−Q/RT) · (1/F_comp) ]
    S(X)   = ∫₀ˣ dX' / [ X'^(0.4(1−X')) · (1−X')^(0.4X') ]   (the KV sigmoidal shape integral)

with **Q = 27 500 cal/mol** (all reactions; so the gas constant is **R = 1.987 cal/mol·K**, NOT
the SI 8.314 J — the unit trap), the ASTM grain-size factor `2^(0.41·G)` (ferrite), and the
undercooling exponent **n = 3** for ferrite & pearlite, **n = 1** for bainite. The composition
factor `F_comp` multiplies τ (larger ⇒ slower ⇒ more retarded):

* **Ferrite:** ΔT = (Ae3 − T); `FC = exp(1.00 + 6.31·C + 1.78·Mn + 0.31·Si + 1.12·Ni + 2.70·Cr + 4.06·Mo)`
* **Pearlite:** ΔT = (Ae1 − T); `PC = exp(−4.25 + 4.12·C + 4.36·Mn + 0.44·Si + 1.71·Ni + 3.33·Cr + 5.19·√Mo)`
* **Bainite:** ΔT = (Bs − T);  `BC = exp(−10.23 + 10.18·C + 0.85·Mn + 0.55·Ni + 0.90·Cr + 0.36·Mo)`  *(for Phase 6b)*

**What Phase 6a pins / uses:** the **ferrite FC coefficients** (carbon 6.31, Cr 2.70, Mo 4.06 are
the strong retarders) and the ferrite start form. The teeth = the **cited retardation ratio
FC(4140)/FC(1045) ≈ 32×** (4140 stays deep, not tuned). The reaction is integrated in `kinetics`
as `dU/dt = K(T)·g(U)` (the rate form of the above), capped at the equilibrium proeutectoid-ferrite
fraction (`fe_c.equilibrium_constituents`), with **Ae3 = the cited alloy-aware Andrews Ae3**
(reused from `calphad_reference.andrews_Ae3`, Phase 4's independent benchmark) as the ceiling,
overridable by a CALPHAD-computed transus (the "couple CALPHAD into live kinetics" seam).

**The one calibrated knob** (`FERRITE_KINETIC_SCALE = 8.0`) is NOT from this source — it reconciles
KV's absolute time base to the project's separately-calibrated pearlite curve, **bounded by the
sanity ceiling** that a 0.2 %C core (8620) stays in its published ~30–40 HRC band (KV's large
carbon coefficient → low-C austenite forms ferrite readily, so one global scale can't fully shallow
0.45 %C 1045 without over-softening the core — the named 6a limitation, lifted only by per-reaction
*absolute* kinetics in 6b). Pearlite/bainite F-factors recorded here for **Phase 6b** (bainite bay).

**Phase 6b OUTCOME (939c80d, merged 2026-06-10) — descoped negative result, the 6a
"design-fork" pattern again.** The cited `BainiteReaction` is BUILT standalone (Steven–Haynes
Bs ceiling, **n = 1** undercooling — ΔT¹ not ferrite/pearlite's ΔT³ — and the BC factor above);
the ferrite `completion_step` was refactored onto a shared `_kv_site_saturation_step`
(behaviour-preserving). **The teeth (cited, scale-free): BC's Cr 0.90 / Mo 0.36 ≪ ferrite FC's
Cr 2.70 / Mo 4.06 — alloy retards displacive bainite ~5.7× for 4140 but reconstructive ferrite
~166× (~29× gap). That IS the bay's mechanism**, the §4 fix at the coefficient level
(`docs/figures/steel-bainite.png`). But the bay **cannot be wired into `pathint`** here, proven
three ways: (1) pearlite's Jominy-pinned Grossmann shift is ~8× for 4140 vs the ~100× a real bay
needs — retuning breaks the 2c anchor; (2) the carbon-flat 550 °C pearlite nose sits inside the
bainite band for lean steels (1045 Bs = 641 > 550) — relabelling mislabels either way; (3) the
**8620 carbon-spread ceiling**: BC's carbon 10.18 makes the 0.20 %C 8620 core the fastest bainite
of any benchmark (~800× eutectoid), so any scale big enough to matter in 1045/4140 drives the 8620
oil core out of its 30–40 HRC band. At every 8620-safe scale the crude 540-split stand-in is
BETTER — wiring would regress. `pathint` left **byte-identical**; `BAINITE_KINETIC_SCALE` =
demonstration-only (isothermal nose position, absolute times unanchored/named); bainite hardness
stays the carbon-only placeholder (never load-bearing). **Forward options for the human:**
(a) the full unified KV pearlite+bainite+ferrite rebuild (steel plan §13 — would open the bay,
discards the calibrated pearlite curve = large/risky), or (b) proceed to **6c** (D_I
ideal-critical-diameter cross-check). Steel fast gate 307 → 319. **6c BUILT 2026-06-10 →
[[di-crosscheck-source]] (Phase 6 now complete); option (a) is the only remaining named deepening.**
