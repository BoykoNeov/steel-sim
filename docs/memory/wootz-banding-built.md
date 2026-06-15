---
name: wootz-banding-built
description: "Wootz/Damascus V/Mo carbide banding (the signed GOOD-impurity foil) BUILT 2026-06-15 — closes §14.5/§15.4, the one genuine front-end physics gap"
metadata:
  node_type: memory
  type: project
---

**Wootz / Damascus carbide banding — the SIGNED GOOD-IMPURITY FOIL — BUILT ✓ 2026-06-15** (user: "do Wootz V/Mo
carbide banding"). Closes the **one genuine front-end physics gap** the plan flagged (§14.5 / §15.4) — the only
named method that is *not* a recombination of existing engines but genuinely new cited physics.
`steel/wootz.py` + demo + `plots.wootz_figure` + tests (19 + 6 = **+25**, fast lane **923 green**); standalone,
**NO engine, NO ADR**; gallery card (34 entries) + root-README row + plan §14 banner + §14.5/§15.2/§15.4/§15.5
"future-research" lines flipped to BUILT.

**The module = the MIRROR IMAGE of every bad-impurity story** (P cold-short, S red-short, MnS anisotropy
[[sulfide-morphology-built]]): here a trace carbide-forming "impurity" — chiefly **vanadium** — that a modern
clean-steel spec would REJECT is the one the wootz smith REQUIRES. So §14.5's framing nuance ("bad steel is
really off-spec composition, signed either way") became the engine. **Three gates, all required** (Verhoeven &
Pendray 1998, JOM 50(9):58, verified via the dtrinkle.illinois.edu mirror + the CCC Won&Thomas PDF read
directly): (1) **hypereutectoid carbon** (~1.5 %, > eutectoid → proeutectoid Fe₃C network to band; reuses
`fe_c.equilibrium_constituents` lever rule); (2) **trace former ≥ threshold** — **V ≥ 40 ppmw** (the cited
"quite effective" line; ~100 ppm = nucleation agent; genuine blades <10–270 ppmw), or weaker **Mn ≥ 200 ppmw**;
(3) **cyclic forging 50–100 °C below A_cm** (`fe_c.Acm` cementite solvus), ≥6 cycles — hotter dissolves the
carbide. Hero = the SAME 1.5 %C steel forged the SAME way: V-bearing cake waters into Damascus, clean modern
twin comes out plain. **Bespoke ~1.5 %C compositions** (repo grades top out at 1080=0.80 %C).

**THE ADVISOR RULING (pre-code): NO tooth, and the band-spacing↔SDAS coherence DECLINED as the
manufactured-coherence trap.** Tempting to compute SDAS from a solidification time and match it to the measured
30–70 µm band spacing (hydrogen-flaking-style OoM tooth) — but that has **three soft knobs** (cake modulus,
Chvorinov B "rule-of-thumb grade", wide-spread SDAS constant) aimed at a target already **2× wide**, so you hit
it whether the physics is right or not. Contrast hydrogen-flaking: ONE pinned D_H → a single cited bake, zero
freedom. So band spacing (30–70 µm) is reported as **two consistent CITED facts** (Verhoeven metallography +
"SDAS in slow-cooled crucible steel is tens of µm"), NEVER a computed prediction. **Second advisor catch: do
NOT derive the V-40 vs Mn-200 effectiveness ratio from segregation coefficients** — effectiveness is
carbide-forming thermodynamics, not microsegregation strength (Mn's k≈0.77 is unremarkable). The 0.2× Mn weight
is read STRAIGHT off the two cited thresholds (40/200), by construction.

**The reuse beat — SAME Scheil engine, opposite sign (by construction, NOT a coherence note):** the
interdendritic former enrichment that aligns the bands is the SAME `casting.segregation_ratio` that makes
centerline segregation a hardenability DEFECT ([[f4-casting-built]]). Read in the **γ** phase because
hypereutectoid wootz (C ≫ 0.53 % peritectic) solidifies as PRIMARY AUSTENITE — `casting` defaults to δ for its
<0.53 %C grades, so phase="gamma" is the physically-correct call here. Amplitude shown via the repo's
**already-pinned Mo former** (k_γ=0.70, ISIJ-sourced in casting) as the exemplar — k_V NOT separately pinned
(Won&Thomas Table I has only C/Si/Mn/P/S), so representative not benchmarked. One engine read two ways, like
"one MnS two signs" — labelled by-construction, not dressed as coherence.

**The flag is gated on INTENT (advisor confirm):** `wootz-pattern-failed` fires ONLY when forged-as-wootz
(hypereutectoid AND correctly cycled) but former < threshold = "the smith did everything right; the ore lacked
the vanadium". Plain bar never forged as wootz → CLEAN, in_spec=None (no intent — the model is
[[sulfide-morphology-built]]'s plain heat). Too-hot heat = technique miss not impurity miss → no flag either.
Gating on the trace threshold is CORRECT here (unlike the sulfur case) because it collapses into no other
flag — genuinely novel physics. **Inert in back end** (trace V/Mo aren't even in `Steel` — keyword inputs);
byte-identical heat_treat test carries over. Sibling [[sulfide-morphology-built]]; reuses [[f4-casting-built]] +
fe_c. **This was the LAST named front-end deferral — chain + all consequences + both signed foils now built;
next = `game/` package.**
