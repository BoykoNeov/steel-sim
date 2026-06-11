---
name: grain-growth-source
description: "Steel Phase 5a: cited S960MC austenite grain-growth Arrhenius (Q + isothermal grain-size table) that grain.py pins; Q cited / m,K0,D0 calibrated to the table; holdout = the teeth"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7cd3511c-deb8-43c9-80f3-7466ba1fc23f
---

Steel **Phase 5a** (grain growth, `projects/steel/grain.py`) pins its austenite
grain-growth kinetics to a published S960MC dataset (open-access; "Determination of
Grain Growth Kinetics of S960MC Steel", NCBI PMC9737238). The **independent** companion
source is [[pickering-strength-dbtt-source]] (source (2), pinned 2026-06-09 = the Pickering
ferrite-pearlite σ_y/ITT pair the 5b/5c property laws use) — kept distinct so the 5c
coupling stays non-circular.

**Form** `Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t` (D mean austenite grain diameter, T abs).

**What is CITED vs CALIBRATED (the non-circularity split):**
- **CITED: Q = 329.95 kJ/mol** (the paper's activation energy). This is what carries the
  benchmark's teeth — the Arrhenius **temperature** scaling across 900–1200 °C.
- **CALIBRATED to the published isothermal table** (Q held at the cited value): exponent
  **m ≈ 4.22**, **D₀ ≈ 14.46 µm**, **K₀ ≈ 1.89e19 µm^m/h** (internal units µm, hours).
  Caveat NAMED: the paper's *headline* m = 3.03 comes from a different (non-isothermal /
  continuous-heating) fit; the paper's own **isothermal** table prefers m ≈ 4.2, and the
  literature spread is huge (n ≈ 2.6–6.5, Q ≈ 256–572 kJ/mol) — so the time-exponent is
  steel-/method-specific and is calibrated, not cited.

**The published isothermal table (the benchmark data — µm vs T,t):**
```
T(°C) \ t(h):  0.5    1     2     4     6     8
 900          13.1  15.4  16.0  16.8  20.4  24.7
1000          25.3  26.0  29.4  30.8  32.8  39.2
1100          38.5  39.2  45.5  48.8  54.1  58.8
1200          60.1  64.5  71.4  80.0  95.2 111.1
```

**The teeth = a HOLDOUT (advisor's "only real teeth of Phase 5"):** fit (m, K₀, D₀) on the
**900 & 1200 °C** rows only (with Q cited), then **predict the held-out 1000 & 1100 °C
rows** → within **16 % / mean 3.6 µm**. A genuine cross-temperature prediction that could
have missed (vs the by-construction sign-opposition demo of 5c). The full-table
reproduction with the locked constants is mean 3.06 µm / max 19 % — asserted **loosely**
(grain-growth fits are inherently scattered). `Q` is only weakly determined by this data
(free-fit gives 379 kJ/mol, ~equal residuals), so the teeth are real-but-modest — name it.

**ASTM E112 G↔d** (exact-by-construction round-trip, the analytic leg): grains/in² @100×
`n = 2^(G−1)`; real grains/mm² `N_A = 15.500·n`; mean diameter `d(mm)=1/√N_A` ⇒
`d_µm = 1000/√(15.500·2^(G−1))`. Anchors: G1→254 µm, G8→22.5 µm (textbook). The 15.500 =
645.16 mm²/in² ÷ 100² (the 100× magnification convention).
