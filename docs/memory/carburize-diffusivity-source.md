---
name: carburize-diffusivity-source
description: Cited carbon-in-austenite diffusivities for carburizing — constant Callister D(T) (default, erfc) AND concentration-dependent Tibbetts 1980 D(C) (opt-in, BUILT 2026-06-11 when the diffusion engine was unfrozen for native nonlinear D(u), re-sealed v1.1; ADR 0004)
metadata:
  node_type: memory
  type: reference
  originSessionId: phase-3c
---

The **carbon-in-austenite diffusivity** BigSim's Phase-3c carburizing model uses
(`carbon_diffusivity` in `projects/steel/carburize.py`):

    D(T) = D0·exp(−Q/RT),   D0 = 2.3e-5 m²/s,   Q = 148 kJ/mol   (T in kelvin)

the **cited Callister/Shewmon** value for carbon in **FCC γ-iron** (Callister,
*Materials Science & Engineering*, the diffusion-coefficients appendix). It is the
*same* pair the diffusion engine's `CONTRACT.md` names as its mass-mode example
(`D₀≈2.3e-5 m²/s, Q≈148 kJ/mol`). At 925 °C it gives ≈ 8.1e-12 m²/s, so √(Dt) ≈ 0.48 mm
over an 8 h cycle — the right case-depth scale (`carbon_diffusivity(925) ≈ 8.12e-12`,
pinned in `test_carburize.py`).

**Why it's load-bearing for the non-circularity story (see [[bigsim-program]]):** these
constants are anchored to *diffusion* data, **not** fit to case-depth tables — which is
exactly what makes Phase 3c's case-depth benchmark a genuine **cross-check** (predict case
depth from independently-cited D, compare to published carburizing tables), parallel to the
way the Hodge–Orehoski martensite anchor ([[maynier-hardness-source]] uses the same √C
baseline) makes the surface-hardness benchmark a cross-check rather than a refit.

**Named scope limitation:** the value is treated as **constant in carbon content**
(concentration-independent), which is the standard textbook reduction and is *what makes the
erfc solution exact* (the validated analytical limit). Real carbon diffusivity in austenite
**rises with carbon content** (Tibbetts), so a real carburized profile is somewhat fuller and
the real case depth deeper — the constant-D form under-predicts the *absolute* case depth by a
modest factor (the 0.4 %C effective case depth comes out ~0.66 mm at 925 °C/8 h, below the
~1 mm published rule of thumb). So Phase 3c (constant-D default) asserts the **∝√(Dt) scaling
tightly** and the **absolute case depth loosely**, attributing the gap to this named simplification.

**Tibbetts D(C) BUILT 2026-06-11 (the gap closed).** The concentration-dependent Tibbetts (1980,
*J. Appl. Phys.* 51(9):4813) diffusivity is now the opt-in `carbon_diffusivity_tibbetts` →
`solve_carburize(D_of_C=…)` in `steel/carburize.py`:

    D = 0.47·exp(−1.6·C)·exp[−(37000−6600·C)/(R_cal·T)]  cm²/s   (C wt%, R_cal=1.987 cal/mol·K, T in K)

measured by the **steady-state** method (975–1075 °C, ≤1.3 %C) → **independent diffusion data, NOT
fit to case depth**, so the case-depth benchmark stays a genuine cross-check (same non-circularity
discipline as the Callister constant-D). D rises with C (the −6600·C activation lowering beats the
−1.6·C prefactor decay): at 925 °C ~1.05e-11 (0.2 %C) → 1.34e-11 (0.4 %C) → 2.13e-11 (0.8 %C), all
above the constant 8.1e-12 → **a fuller profile, ECD ~0.66 → ~0.97 mm** (into the published band).
Validated vs the **Boltzmann self-similar** reference (the profile is no longer erfc but stays
self-similar in η = x/√t, so the **√t case-depth scaling survives**). Mild named edge: the default
925 °C is ~50 °C below Tibbetts' measured 975–1075 °C floor (the standard carburizing-sim extrapolation).

**This required UNFREEZING the diffusion engine** (`engines/diffusion`): D(C) is *solution*-dependent,
so the v1.0 "flagged-not-built nonlinear `D(u)`" was **built** as a native opt-in `D_of_u` (Picard
in-step, backward-Euler only, with the **cached accepted-assembly D-field** so conservation stays
machine-exact — the load-bearing design catch), and the spine was **re-sealed at v1.1**
(`test_nonlinear_d.py`, the 6th seal file); the linear path is **byte-identical**. Full record →
**ADR 0004** + plan **§15** + `engines/diffusion/CONTRACT.md`. *User-directed:* the alternative —
composing a lagged D(C) *around* the frozen engine via the ADR-0001 array seam — was set aside to put
the capability in the spine, inherited (backward-compatibly) by Microchip/Planet.
