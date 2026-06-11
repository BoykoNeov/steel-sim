---
name: hollomon-jaffe-tempering-source
description: Hollomon–Jaffe tempering-parameter source/convention + the C_hj constant BigSim Phase 3b uses
metadata:
  node_type: memory
  type: reference
  originSessionId: phase-3b
---

The **Hollomon–Jaffe (1945)** tempering parameter — the published method BigSim's
Phase-3b tempering model uses (`tempered_martensite_HV` in `projects/steel/properties.py`):

    P = T·(C_hj + log₁₀ t)      T in KELVIN, t in HOURS

collapses tempering temperature and time into one number so that any two `(T, t)` on the
same `P` soften a quench-hardened steel to the **same** hardness (the time–temperature
equivalence — the same functional form as the **Larson–Miller** creep parameter).

**The constant `C_hj`** is ≈ **20** for low-alloy steels with `T` in kelvin and `t` in
hours — the commonly-cited value (Hollomon & Jaffe, *Trans. AIME* 162:223, 1945). It is
mildly carbon-dependent in the original work (often quoted ~`21.3 − 5.8·%C`), but BigSim
**defaults to the single constant 20** and leaves the carbon-dependence as an optional
caller override (`C_hj=` arg) rather than baking in coefficients it can't independently
verify — **only the parameter's *form* (the equivalence) is validated in the suite; the
value of `C_hj` is an assumed literature constant.** Coded as `properties.HJ_CONSTANT`.

**How BigSim Phase 3b uses it (see [[bigsim-program]]):** tempered-martensite hardness is a
decreasing master curve `HV(P)` between two *independently-anchored* endpoints (the 3a
as-quenched martensite and the FP/spheroidite floor); only the *transition* is calibrated,
via two `P` breakpoints (`P_TEMPER_ONSET=8500`, `P_OVERTEMPERED=19500`) — the Phase-3b
analogue of Phase-2b's calibrated `HARDENABILITY_SCALE`, set so ~0.4 %C martensite tempered
1 h follows the known **Grange/ASM** tempering response (high-50s HRC as-quenched → low-40s
at 400 °C → ~25 HRC at 600 °C). Parallel to the Maynier graft ([[maynier-hardness-source]]):
a named published method, anchored, with the calibrated knob flagged honestly.
