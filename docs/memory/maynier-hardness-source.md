---
name: maynier-hardness-source
description: Maynier (1978) constituent-hardness equations + coefficients — the source BigSim Phase 3a grafted
metadata: 
  node_type: memory
  type: reference
  originSessionId: c66de8de-4fa0-4c60-b400-c9cde0200a47
---

The **Maynier (1978)** Vickers constituent-hardness equations (Maynier, Dollet &
Bastien) — the published method BigSim's steel property model uses (`HV = Σ fᵢ·HVᵢ`,
the rule of mixtures over constituents). Canonical coefficients (reproduced e.g. in
*Scandinavian Journal of Metallurgy* 33:98–104, 2004,
https://mmm.sjtu.edu.cn/userfiles/1/files/2004-SCANDINAVIAN-JOURNAL-OF-METALLURGY.pdf):

- `HV_M   = 127 + 949C + 27Si + 11Mn + 8Ni + 16Cr + 21·log10(Vr)`
- `HV_B   = -323 + 185C + 330Si + 153Mn + 65Ni + 144Cr + 191Mo + (89 + 53C - 55Si - 22Mn - 10Ni - 20Cr - 33Mo)·log10(Vr)`
- `HV_F+P = 42 + 223C + 53Si + 30Mn + 12.6Ni + 7Cr + 19Mo + (10 - 19Si + 4Ni + 8Cr + 130V)·log10(Vr)`

`Vr` = cooling rate at **700 °C in °C/hour**; `log10`; composition wt%.

**How BigSim Phase 3a uses them (a graft, NOT pure Maynier — see [[bigsim-program]]):**
Maynier's martensite carbon term is **linear** (949C); BigSim instead keeps 2c's
*independently-anchored* baselines (Hodge–Orehoski √C martensite `92+828√C`,
normalized-plain-carbon linear FP `90+260C`) and bolts on **only the non-carbon
deltas** above (minor-alloy + the cooling-rate slope, reference-zeroed). Not
self-consistent (Maynier fit his alloy/Vr coeffs jointly with his own carbon terms),
but a defensible teaching graft. Coded in `projects/steel/properties.py` as
`MAYNIER_ALLOY` / `MAYNIER_VR_SLOPE`; martensite Vr-term dropped, bainite terms
deferred (its coeffs are too large to graft onto the placeholder baseline).
