---
name: deox-recovery-built
description: "F2→F3 deox→recovery seam BUILT 2026-06-15 — dissolved O taxes oxidizable Mn/Si recovery; modest/sub-window, no tooth; closes ladle's last named deferral"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4e41556e-d8fb-4265-8437-70cc22bd193c
---

**The F2→F3 deox→recovery coupling — the SEAM — BUILT ✓ 2026-06-15** (user picked it from a what-next menu).
Closes the **last named deferral** [[ladle-f3-built]] carried: the deox-state-dependent recovery coupling.
`steel/ladle.py` gains `oxidation_recovery_loss` / `recovery_after_deox` / `OXIDIZABLE_TRIM_ELEMENTS` +
`trim_to_grade(couple_deox_recovery=True)`; `demo_deox_recovery.py` + `plots.deox_recovery_figure` (2-panel) +
14 tests (7 in `test_ladle.py` + `test_demo_deox_recovery.py` 7). Fast lane **884 → 898 green** (full 906/2skip,
the 2 skips pre-existing `@slow` notebook-exec). Standalone, **no engine touch, no ADR, no tooth**.

**The mechanism (by-construction mass balance):** the dissolved oxygen F2 leaves on the `Heat` (`oxygen_ppm`)
ties up a stoichiometric mass of the oxidizable trim additions as oxide — the SAME conservation
`refining.generated_oxide` uses, read onto recovery (`metal_per_O = (1−f_O)/f_O` from `Deoxidizer.oxide_O_mass_frac`).
So Mn/Si recovery falls below nominal; the noble Cr/Mo/Ni hold (no deox reaction in `refining.DEOXIDIZERS` →
oxygen-independent). `couple_deox_recovery=True` **produces** the recovery shortfall from the deox state instead
of hand-setting it (the move F3 made over the spine, one level up). Hero = **readout contrast** (not a flag-trip):
same charges into a well-killed bath (Al 0.04, O ~4 ppm) → Mn/Si recover full; into an under-killed one (weak Si
kill, O ~53 ppm 4140 / ~105 ppm 8620, carries F2's `porosity-risk`) → Mn taxed ~2 % / ~4 %, Si less, Cr/Mo
identical. One root cause (skipped kill), one flag (porosity-risk) + one readout — no new flag.

**THE LOAD-BEARING ADVISOR THREAD — the magnitude IS the result, modest by physics:** even a fully under-killed
bath taxes Mn only ~2–4 % at the demonstrator carbons → **sub-window** (landed Mn dips but stays in the band) →
the dissolved-O coupling **cannot trip off-grade**, which is *quantitatively why* [[ladle-f3-built]]'s gross
under-trim hero (Cr/Mo recovery ~halved) had to be **hand-set** — the plan's own "marginal miss = in-window"
note (lines 522-527), now derived. **A 20–35 % tax I briefly computed was a CARBON MISMATCH** (the FeO-route O
~430 ppm belongs to a *low-carbon* slag a 0.40 %C bath can't sit under — the carbon boil reduces it; advisor
caught it: `[O]=22/[%C]`). So the demo is a readout contrast (the sulfide-morphology good-half precedent — a
positive readout, no `add_defect`), NOT a manufactured failure-hero.

**Two more durable catches:** (1) **Ceiling verified against the code, not assumed.** Advisor's first framing
called the slag reservoir "not modelled"; a grep proved it INACCURATE — `slag.py` carries the `FeO` field +
Fe–FeO O-anchor `K_FE_FEO`. So the ceiling is named precisely: the tax here is the **one-shot scavenge of the
bath's dissolved O**; the *gross* losses are the **alloy-reoxidation distribution** (Mn/Si/Cr into an oxidizing
FeO slag), an equilibrium NOT built (FeO could seed it, no metal→slag alloy partition, FeO not wired to set bath
O at trim) — the real driver of the gross hero, and a legitimate next build (may carry a coherence tooth: the
Mn≫Si≫Cr reoxidation order = F1's Ellingham order again). (2) **Selectivity exact, magnitude split not.** The
oxidizable(Mn,Si)-vs-noble(Cr,Mo,Ni) split is exact; the within-pair Mn>Si steepness in panel A is a mass-split
artifact (I split the O pool by delivered mass; Si is actually the *stronger* deoxidizer) → DON'T present Mn>Si
as a finding, stated as a simplification in the docstring, prose scoped to oxidizable-vs-noble. **Don't** add a
Cr-O path or a competitive Si-Mn solver (over-engineering for a sub-window effect — declined, advisor-endorsed).

**Coherence bonus (genuine, not manufactured):** lower-carbon 8620 sits at higher dissolved O (F2's inverse C–O
coupling) → bigger tax → kill-before-you-trim matters most where carbon is lowest; ties F2's validated C–O number
straight into F3 recovery. Amends [[ladle-f3-built]]/[[refining-f2-built]]/[[gallery-page]]. **Front-end chain +
all consequences + this seam now built**; next = `game/` or Wootz V/Mo carbide banding (the one real physics gap).
