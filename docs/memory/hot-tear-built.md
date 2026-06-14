---
name: hot-tear-built
description: "Hot-tearing (solidification cracking) consequence BUILT — the last F4/F2 casting defect closed as a segregation-amplified Mn:S film criterion"
metadata:
  node_type: memory
  type: project
---

**Hot-tearing — the casting-stage sulfur consequence BUILT ✓ 2026-06-14** (user: "work on hot tear"). Closes
the **last open F4/F2 defect** and the §6 row "under-desulfurization → hot-tear susceptibility".
`steel/hot_tear.py` + demo + `plots.hot_tear_figure` + **18 tests**; **764 → 783 green**; **standalone, NO
engine, NO ADR**; gallery card + root-README tour row + plan as-built banner. Sibling of
[[gas-porosity-built]] / [[hydrogen-flaking-built]] / [[impurity-consequence-built]].

**Two-tier:** slag's flat, Mn-blind **`high-sulfur`** risk (S > 0.040 %) → new **`hot-tear`** consequence —
the **casting-stage sibling of forging-stage red-shortness** (`hot_work.py`). Both close the sulfur
consequence [[slag-f2-slice2-built]] set up; this one reads it during **solidification**.

**The model = segregation-amplified film Mn:S.** Hot-tearing is in the **last liquid to freeze**, which is
**Scheil-enriched**: read the interdendritic **LIQUID** Mn:S (`casting.scheil_liquid_composition` for *both*
solutes), feed the *same* `slag.manganese_sulfide` red-short uses → free S in the film (film Mn:S < 1.71
stoichiometric) ⇒ Fe–FeS film ⇒ tear. Sulfur (small k) piles up ~10× faster than Mn → film Mn:S ~10× poorer
than the bath. Reuses [[f4-casting-built]]'s Scheil.

**TWO advisor catches BEFORE writing, both load-bearing:** (1) **Use the LIQUID Scheil, NEVER
`centerline_enriched_composition`** — that returns the depleted *solid* (low-k means little S in the solid;
at f_s=0.95 solid-S ratio ~0.63 *depleted* vs liquid ~18× enriched) AND reconstructs `Steel(...)` dropping
S/P to 0 → would invert the model (Mn enriched, S gone). The film is a LIQUID phenomenon. (2) **Web-verify
the Mn:S≈20 anchor before pinning** (don't bake from memory): confirmed **Toledo 1993** "Mn:S < 20 →
intergranular embrittlement in continuous casting" is genuinely **hot-ductility, NOT primarily inclusion
morphology** (Category-II sulfides = Mn+S enriched *between dendrites during solidification* — exactly the
mechanism); band ~6–36, S-dependent. ([[di-crosscheck-source]] discipline.)

**The red-short non-vacuity = phase + time, NOT homogenization (advisor).** Hot-tear reads the *transient
interdendritic liquid* during freezing; red-short reads the *bulk solid* at the forging reheat. Different
phase, different time → a heat can legitimately **fail one gate, pass the other** (castability ≠
forgeability). There is no "bulk" liquid during freezing — segregation is intrinsic, not a refinement.

**NO claimable tooth — by construction + cited inputs (the [[temper-embrittlement-built]]/gas-porosity
landing).** Verdict = cited Scheil partition (Won–Thomas k) × cited MnS stoichiometry (1.71 = M_Mn/M_S, reused
wholesale) — can't independently fail. **One soft OoM-coherence note:** `critical_bulk_mn_s` (bulk Mn:S the
amplified film needs) lands in the **tens** (≈9 at f_s 0.90, ≈14 at 0.95, ≈45 at 0.99) — reproducing the
empirical "Mn:S in the tens" rule from the stoichiometric 1.71 with NO tuning. **ORDER cutoff-robust, value
cutoff-tuned** (f_s* a free knob). Really by-construction.

**Hero = same sulfur, the Mn:S decides** (mirrors gas-porosity's "same O, carbon decides"): two heats same S
(both in the 0.040 % spec, both clearing *bulk* MnS), low-Mn (Mn:S 10) tears (film ~1.2), higher-Mn (Mn:S 22)
sound — the **Mushet lever**, threshold now in the *tens*; a 3rd (S>spec, Mn:S 25) sound → flat risk line
both under- and over-warns. Don't assert the if-rule (free S → tear); the hero + Mushet discriminations are
the non-vacuous checks.

**Ceiling:** S-film *sub-mechanism* only. RDG / Clyne–Davies feeding-strain driver (freezing-range / mushy-
span *magnitude*) lives illustratively already in `solidification.py` ([[f4-slice2-solidification-built]]) —
referenced, not duplicated; **carbon-peritectic** δ→γ contraction (the ~0.1 %C continuous-casting window) a
named deferral (different mechanism, needs δ/γ volumetric thermo); 1.71 on the *final* liquid ignores
progressive MnS precipitation. Amends [[refining-f2-built]] / [[slag-f2-slice2-built]]; the centerline a
casting enriches ([[f4-casting-built]]), freezes last ([[f4-slice2-solidification-built]]) AND tears = one
place, three reasons.
