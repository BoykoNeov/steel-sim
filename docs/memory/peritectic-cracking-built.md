---
name: peritectic-cracking-built
description: "Carbon-peritectic surface cracking BUILT — the carbon sibling of hot_tear (δ→γ contraction), closing the hot-tear carbon-peritectic deferral"
metadata: 
  node_type: memory
  type: project
  originSessionId: 16612a78-ea41-4f58-bba3-14023d194adc
---

**Carbon-peritectic surface cracking BUILT ✓ 2026-06-14** (user: "work on carbon-peritectic hot-tear"). Closes
the one named deferral [[hot-tear-built]] left open — the **carbon-driven** casting-cracking sibling of the
**sulfur-driven** `hot_tear`. `steel/peritectic.py` + demo + `plots.peritectic_figure` + `test_peritectic.py`
(+`test_demo_peritectic.py`), **+23 tests, fast lane 839 green**; standalone, **NO engine, NO ADR**; gallery card
(Casting section) + root-README row + plan as-built banner. Commit `73165f9`.

**The mechanism (NOT sulfur):** the peritectic `L+δ→γ` is a **BCC→FCC volume contraction** that, concentrated
high in the continuous-casting mould, shrinks the thin shell off the wall → longitudinal facial cracks; the
hypo-peritectic **~0.10–0.16 %C** grades are the worst, **non-monotonically** (a *leaner* OR *richer* steel
casts more soundly — "more carbon is safer", the hero, sibling of gas-porosity's "same O, carbon decides").

**Verdict = Wolf's cited ferrite-potential band `FP = 2.5(0.5−Cp)`** (crack band `0.8<FP<1.05` ≈ 0.08–0.18 %C
plain; a labelled classifier, like `MIN_MARTENSITE_SPEC`). **Mechanism = the Fe–C lever rule** on cited
invariants `L(0.53)+δ(0.09)→γ(0.17)` at **1495 °C** (web-verified; the point `casting.PERITECTIC_C` names) —
by-construction carbon mass balance, the figure's "why". **`Cp` carbon equivalent = REPRESENTATIVE tier-2**
(signs unambiguous: austenite stabilizers Mn/Ni ↑, ferrite Si/Cr/Mo/P ↓; magnitudes spread, single-Cp itself
approximate per the ISIJ-2015 multicomponent critique — same honest tier as `casting.py`'s ISIJ k's). The
plain-C hero needs no coefficients; alloying is the "same C, alloying decides" 2nd lever (Si+Cr pull a safe
0.20 %C into the band — a *hypothetical*, NOT real 8620, which lands FP 0.76 honestly just outside).

**THREE durable advisor catches:**
1. **Load-bearing — read NOMINAL carbon, NEVER the Scheil last liquid (the *reverse* of [[hot-tear-built]]).**
   Peritectic δ→γ is a **primary-solidification / shell** phenomenon on bulk aim chemistry (Wolf's FP is
   ladle-carbon; `casting.py` already disowns C-enrichment). So `peritectic` reads `heat.composition.C`;
   `hot_tear` reads `casting.scheil_liquid_composition`. A clean stated contrast, tested.
2. **[[di-crosscheck-source]] caught ME this time, not an AI table.** I printed "MMTB 51:1937 2020" in three
   permanent docs from memory (the Springer fetch had failed on auth) → advisor flagged the unverified
   absolute → ADS bibcode `2020MMTB...51.1875A` showed the real page is **1875** (Azizi & Thomas), 1937 was
   misremembered. **Verify reconstructed citations before baking, exactly as for extracted tables.**
3. **NO tooth, soft COHERENCE note named NOT independent** (both rest on the Fe–C peritectic): the lever rule
   and Wolf's empirical FP place the trouble at the same ~0.1 %C window — the mechanism *explains why* the band
   is there (NOT "two independent constructions agree"). And **coherent ≠ identical**: the FP low edge (0.08 %C)
   reaches *below* the binary δ-onset (Cδ 0.09), so a 0.08–0.09 %C heat is FP-flagged but pre-peritectic
   (`delta_consumed=0`) — the verdict **names the incipient strip** instead of self-contradicting ("sub-peritectic
   + contraction"). Advisor caught this latent (the hero clears the strip); a fitted band conflicting with a
   sharp invariant by ~0.01 %C is *evidence for* the framing. **Consumed-δ peaks at the band edge Cγ=0.17, NOT
   the empirical worst (~0.11) — left unpatched**, named ceiling (exact worst-carbon needs δ→γ kinetics + shell
   mechanics — underdetermined, the [[temper-embrittlement-built]] landing). Skipped the optional lattice→
   dilatometry tooth (contraction magnitude is verdict-independent → orphaned check; keep the clean no-tooth
   sibling landing). Amends [[hot-tear-built]]; sibling [[gas-porosity-built]]/[[f4-casting-built]].
