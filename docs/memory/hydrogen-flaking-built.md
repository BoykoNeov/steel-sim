---
name: hydrogen-flaking-built
description: "hydrogen-flaking consequence BUILT 2026-06-14 — closes F2's deferred dissolved-H downstream; standalone analytic out-diffusion (Crank), the ONE tooth = OoM coherence of pinned D_H with cited bake practice"
metadata:
  node_type: memory
  type: project
---

**Hydrogen flaking — the dissolved-H consequence BUILT ✓ 2026-06-14** — closes the hydrogen downstream F2
(:mod:`steel.refining`) deferred. User picked it off the physics-deferral menu (over `game/` / F4 hot-tear /
ladle carbon carry-in / tempered-martensite-embrittlement). `hydrogen_flaking.py` + demo + figure + 12+5
tests; **739 fast green** (+17); **standalone (closed-form, NO engine, NO ADR)**.

**Two-tier flag (the structural point):** refining's `degas` ALREADY fills `Heat.hydrogen_ppm` and raises a
chemistry-state **`hydrogen-flaking-risk`** (H > 2 ppm at the ladle). This build closes the **consequence** —
whether a *part* actually flakes — via a NEW **`hydrogen-flaking`** flag. The cold-short(propagation) /
red-short(new-consumer) precedent: refining sets the risk, this sets the consequence. (thin section: risk
only; thick: risk AND flaking.)

**ADVISOR CRUX — the model-depth decision (3 options):**
- **A (thin threshold consumer: H>2 AND thick→flake) was REJECTED as DUPLICATIVE** — the "coherence: does the
  Sieverts √p vacuum clear the 2 ppm limit?" is ALREADY in refining.py (`vacuum_for_gas_target`). A pure
  threshold flag would be the vacuous-A trap.
- **B (analytic out-diffusion, standalone) chosen — and the REASON is sharp: C (engine solve) buys NO NEW
  TOOTH**, NOT that C is heavy (it's a cheap linear mass-mode solve). The engine is **already sealed against
  the analytic diffusion solution** (`engines/diffusion/tests/test_erfc.py`) → an engine H-solve would only
  re-exercise that seal. The flaking verdict is a **scalar** (peak/centre residual H after a cool/bake), which
  the closed-form **Crank slab-desorption series** gives directly. Standalone like reduction / casting Slice 1.

**THE ONE GENUINE TOOTH — soft, OoM cross-source coherence (di-crosscheck gate run on paper FIRST, passed
WITHOUT tuning):** the dehydrogenation time from an **independently pinned** lattice `D_H` reproduces cited
industrial bake-vs-section practice. `D_H = 1e-7·exp(−6000/RT) m²/s` pinned to reproduce the **accepted room-T
α-Fe lattice value ~8.9×10⁻⁹ m²/s** (Kiuchi–McLellan 1983 experimental reanalysis of 62 datasets;
cross-checked DFT/MD Jiang–Carter / Hasan 2020: D0≈1–1.5e-7, Ea≈0.04–0.06 eV) — pinned to a *room-T
diffusivity*, the anchors are *bake times*, so the agreement is a real check, not arithmetic. Result, no
tuning: 1-inch → ~0.6 h (the "1 h/inch" rule), 500 mm forging → ~10 days, 1 m rotor → ~6 weeks (heavy
forgings → days-to-weeks). **OoM/ranking-grade** — real steel traps H 10–100× below the lattice value →
the model is a **conservative LOWER bound** on bake time (named scatter). **By construction (NOT teeth):** the
`τ ∝ L²` scaling (Chvorinov-`M²` class) and the verdict rule. **Cited INPUTS (≠ tooth):** D_H Arrhenius, the
~650 °C ferritic bake (below A₁=727, where H diffuses fastest), the ~2 ppm limit (= `refining.MAX_HYDROGEN_PPM`).

**Hero = same ladle H, the section decides** (the only genuinely-new content vs refining.py): 4140 degassed to
~3.6 ppm (risk set), two sections + the *same* bake → **thin sound, thick FLAKES** (residual 3.3 ppm > 2),
thick saved by a long hold (the bake lever). Analog of "same quench, two compositions → soft core" /
"same casting, two locations → hard band". **Ceiling:** out-diffusion only ("can the H escape in time?") —
NOT the γ→α solubility-collapse supersaturation / H₂ void-pressure thermodynamics (the crack itself).
Expected a thin red-short-class consumer, got exactly that + one OoM tooth. Demo `demo_hydrogen_flaking`
(4 panels: hero bars / out-diffusion dynamics / coherence tooth ∝L² / cited D_H Arrhenius). Amends
[[refining-f2-built]]; consumer-sibling [[impurity-consequence-built]] / [[temper-embrittlement-built]];
gate discipline [[di-crosscheck-source]]. Gas porosity + F4 hot-tear remain deferred.
