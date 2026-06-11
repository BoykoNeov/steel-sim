---
name: pickering-strength-dbtt-source
description: "Steel Phase 5b: cited Pickering ferrite-pearlite yield + impact-transition-temperature (DBTT) equation pair (Mn/Si/N/pearlite + grain terms, opposite grain-size signs) that grain.py §3 pins; source (2), independent of grain-growth-source"
metadata:
  node_type: memory
  type: reference
  originSessionId: c86aa66a-a37e-4467-8db7-26b9c0a66b2f
---

Steel **Phase 5b** (`projects/steel/grain.py` §3 — `hall_petch_yield_MPa`,
`cottrell_petch_dbtt_C`) pins its two grain-size property laws to the **Pickering
ferrite-pearlite correlation** (F.B. Pickering, *Physical Metallurgy and the Design of
Steels*, 1978; the impact-transition form from Pickering's "Towards Improved Toughness
and Ductility", 1971). This is the Phase-5 plan's **source (2)** — kept **independent**
of [[grain-growth-source]] (source (1), the S960MC grain-growth kinetics) so the 5c
coupled sign-opposition stays non-circular. See `docs/plans/steel-production.md` §12.

**The pair — two laws of the SAME Hall–Petch form, OPPOSITE grain-size signs** (the whole
point of plan option (b); grain size `d` in **MILLIMETRES** in both cited forms):

```
σ_y  [MPa] = 53.9 + 32.34·Mn + 83.16·Si + 354.2·√(N_free) + (pearlite) + 17.402·d^(−½)   grain +
DBTT [°C]  = −19  + 44·Si    + 700·√(N_free)  + 2.2·(%pearlite)        − 11.5·d^(−½)       grain −
```

Mn/Si/N/%pearlite raise **both** (strength↑ AND DBTT↑ = embrittle); only the grain term
flips sign → **grain refinement is the lone co-improving lever**.

**What is CITED vs CALIBRATED vs WEB-CONFIRMED (the non-circularity discipline):**
- **WEB-CONFIRMED** (real external right-answer): (a) the full **yield** equation
  coefficients `53.9 / 32.34·Mn / 83.16·Si / 17.402·d^(−½)` (ScienceDirect "Ferrite Grain
  Size" topic — the search engine misparsed the `354.2·√N_free` term as "354.2 Ni"; the √
  free-nitrogen form is canonical Pickering and physical, an interstitial ∝ √c; magnitude
  check `354.2·√0.005 ≈ 25 MPa` is meaningful, a linear-N reading `≈2 MPa` would contradict
  N's known strong effect); (b) the DBTT **grain coefficient −11.5** and **Si coefficient
  +44** — the +44 °C/%Si is verbatim in Total Materia ("fracture of steel"), and −11.5 is
  pinned by the textbook fact that **refining 10 µm → 1 µm lowers DBTT by ~250 K**:
  `−11.5·[(0.001)^(−½) − (0.01)^(−½)] = −11.5·(31.62 − 10) = −248.7 °C` (an exact match —
  this is also what pins the **d-in-mm** convention). The external anchoring is in *that
  manual derivation* against the published 250 K fact; the `grain.py` test reproducing
  −248.7 °C is therefore a **unit/wiring regression guard** (−11.5 was *chosen* to match
  250 K, so the test is by-construction), not an independent re-validation (advisor).
- **RECALLED-CANONICAL, cross-checked structurally** (standard Pickering, not independently
  re-fetched, labelled calibrated/not-teeth): the DBTT base **−19**, the **700·√N_free**,
  the **2.2·%pearlite**. Even if a few °C off, the demonstration rests on the *signs* + the
  confirmed grain coefficient, and these are by-construction in the model anyway.
- **CALIBRATED (the ONE free coefficient):** the **pearlite contribution to YIELD ≈ 2 MPa per
  % pearlite**. Pickering's cited yield equation is *ferrite-matrix-controlled* and carries
  **no** pearlite term; the ~2 MPa/% is a **rule-of-mixtures** slope (eutectoid pearlite
  lower-yield ≈ 400–450 MPa vs ferrite matrix ≈ 200–250 MPa → (425−225)/100 ≈ 2). Flagged,
  **NOT tuned to the 5c figure** (the sign-opposition is by-construction → tuning buys nothing,
  costs honesty). 5c's lever comparison therefore **leads with Si** (fully cited 83.16/44),
  pearlite corroborates (advisor).

**Free nitrogen** `N_free` is **not** in the `STEELS` registry → flagged default
`DEFAULT_N_FREE_PCT = 0.005 wt%` (≈ 50 ppm, semi-killed; clean Al-killed ≈ 0.002),
override-able. It enters both laws under a √ (an embrittler) but does **not** affect the
grain-term sign-opposition; the grain/Si/pearlite terms carry the story.

**`σ₀ ≈ 70 / k_y ≈ 0.6 MPa·√m` (plan numbers)** are the *bare* round-number teaching limit;
the cited Pickering exact values are `σ₀ = 53.9` and `k_y = 17.402 MPa·mm^(−½) ≡ 0.55 MPa·m^(−½)`.
Bare ferrite at 10 µm = **228 MPa**; a real mild steel (Mn~0.45, Si~0.2, N~0.005) lands
**~280 MPa** (the plan's "≈260 @ 10 µm" in-distribution band). The bare Pickering call
(`comp=None, f_pearlite=0`) **is** the two-constant Hall–Petch limit — one model, not two.

**Validation status (= plan §12 triad):** Phase 5's only real teeth are 5a's grain-growth
holdout. Here, the d^(−½) **linearity** of both laws and the **G↔d** round-trip are exact by
construction; the **sign-opposition / lever comparison** is a *demonstration that passes by
construction* (both equations cited → no holdout can falsify it = Phase-4 "wiring check"
status — DON'T write a test asserting it as the benchmark leg); a plain-carbon steel's
(σ_y, DBTT) landing in band is *loose in-distribution* sanity. The laws return **nan** for a
martensitic structure (`f_martensite > 0.5`; martensite packet-HP deferred; bainite named
loosely-out-of-domain, not guarded). **Units trap** (registry-tested): grain µm→mm at the
`_d_mm` boundary; `N_free` in wt% under a √ (wt%/ppm mix-up = ~√1000 error).
