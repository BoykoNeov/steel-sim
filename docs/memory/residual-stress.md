---
name: residual-stress
description: Steel §18 residual stress & distortion on quench (§11 Option-#2, first solid mechanics) — built 2026-06-12 (incremental elastic-perfectly-plastic; sign-reversal teeth; no new fitted number; suite 465 green)
metadata:
  type: project
---

Steel **§18 residual stress & distortion on quench BUILT ✓ 2026-06-12** (`steel/residual.py` + demo +
figure + 18 tests; suite **465 green**). The **§11 Option-#2** axis — the biggest genuinely-new modelling left and the
**first solid mechanics**. Answers *what the quench does to the part* (residual stress, quench-crack
risk), and makes the §17 martempering distortion story **quantitative in stress** (not just the thermal
proxy). Reuses §17 `martemper.slab_thermal_history` on the **frozen heat engine** — **no engine touch,
no ADR, no number fitted to a stress measurement** (the §14/§16/§17 "no new calibrated number" stance).

**The crux (advisor — not a close call): incremental elastic–perfectly-plastic with T-dependent yield,
NOT pure-elastic.** Pure-elastic eigenstrain misfit gives **zero** residual on a through-hardened part
(uniform final eigenstrain → σ=0) → it **inverts the headline risk ranking** (calls the deepest, most
crack-prone quench the safest). Residual stress is **path-dependent** — locked in by *plastic yielding
while hot & soft*; which fibres yield while soft IS the mechanism, so elastic+yield-clip also fails. So
the model marches the quench step-by-step with a return-map.

**Mechanical model (advisor geometry steer — slab, NOT the Jominy fin bar).** 1-D infinite plate cooled
symmetrically (= §17 slab geometry; maps **exactly** onto equibiaxial plate, gives direct-vs-martemper
free). Traction-free faces → through-thickness σ=0, in-plane **equibiaxial** σ, one membrane strain ε*
shared by all fibres (flat, symmetric ⇒ no bending), equilibrium = **∫σ dx = 0**. Per step: trial
`σ = E(T)/(1−ν)·(ε* − ε_free − ε_pl)`, clip to `±σ_Y(T)` (von Mises equibiaxial = `|σ|≤σ_Y`; excess →
plastic), bisect ε* for ∫σ=0 (clipped σ monotone in ε*). `ε_free` = thermal `α(T−T_ref)` + KM martensite
**dilatation** `ε_tr·f_M` (f_M from running-min undercooling per cell). Residual = stress at final
uniform-T — nonzero via **non-uniform locked plastic strain**, self-equilibrated by construction.

**Cited vs representative.** CITED — lattice params (Roberts/Kurdjumov–Lyssak) → `ε_tr=⅓·ΔV/V` (~0.9–1.3%
for 1080/4340); **Eurocode 3** elevated-T reduction factors for `E(T)`,`σ_Y(T)`; Andrews Mₛ, KM, frozen
solver. REPRESENTATIVE — `ν=0.30`, `E₂₀=210 GPa`, yield base `σ_Y,20=400 MPa`, `α=1.5e-5` (status of
ρ,c_p,k). Absolute magnitude scales with these (named edge); **teeth are structural** (signs/equilibrium/
ratios), independent of the values.

**Teeth (advisor: verify BOTH signs before declaring — done before any test written; probe found the
regime).**
* **Sign reversal (headline):** thermal-only → surface **compression**; martensite dilatation **flips it
  to tension** (surface transforms first, late-expanding core stretches it = crack-prone). Shown via
  **transform ON vs OFF toggle** (both atlas steels through-harden → neither gives surface compression
  *with* transformation; the thermal-only run is the reference). 4340, 50 mm plate, still water:
  **OFF −141 MPa → ON +386 MPa**, core −391.
* **Severity gate (real finding):** a *mild* quench leaves NO residual — gradient must be severe enough
  (**Biot ≳ 1**) to plastically yield the hot core; 20 mm/`H_WATER` (Biot 0.5) deforms nothing. So the
  thermal-compression sign appears only once the quench actually yields the steel → 4340/50 mm is the demo
  (1080's low Mₛ also suppresses its transformation residual in thin sections — it transforms after
  equalising).
* **Self-equilibrium:** ∫σ dx ≈ 1e-8 Pa (machine precision — Jominy-energy-balance analogue).
* **Magnitude order:** peak |σ|≈396 MPa ~ the 400 MPa yield base (severe quench reaches yield-level).
* **Martemper ≪ direct (the §17 tie-in in stress):** direct +386 → martemper ≈ 0 (near-uniform slow cool
  transforms in step). Near-*complete* removal = idealised (thermally-thin air-cool + TRIP unmodelled), a
  best case (named). **Resolution-converged** (advisor catch — the martemper run marches a ~10-h air cool,
  so a coarse linspace grid could *starve* the early bath-quench transient → spurious zero): ≈0 holds
  across n_t 4000→64000 (bath quench then resolved by ~340 steps), OFF too → physical (martempering
  replaces the deep-cool-under-gradient phase that builds the *direct* thermal residual), not an artifact.
  Pinned by `test_martemper_near_zero_is_resolution_converged`. **Lesson: resolution-check the side with
  the multi-scale time grid, not just the headline case.**

**Named edges:** (1) **NO transformation plasticity (TRIP/Greenwood–Johnson, Leblond)** = the **#1
deferred refinement** (raises magnitudes, not signs); (2) **through-hardening (martensitic) only** — every
cell → KM martensite; hardenability-limited core (pearlite/bainite, different dilatation) not modelled (so
route comparison is honest = timing not product); (3) one-way coupling, no latent-heat feedback; (4) single
non-phase-split `σ_Y(T)` (hard martensite not given separate yield → caps surface tension at σ_Y,20);
(5) absolute magnitude property-sensitive (don't fit a published stress *profile* = geometry/HTC-specific,
the named trap).

**Triad:** `test_residual.py`(15)+`test_demo_residual.py`(2). New surfaces: `residual`, `demo_residual`,
`plots.residual_stress_figure` + banked `docs/figures/steel-residual-stress.png` (2 panels: sign reversal;
direct-vs-martemper). `engines/diffusion`/`martemper`/`austemper`/`pathint`/`properties` byte-identical
(module only imports them). As-built record = plan §18.

**Why:** records the non-obvious build shape so a later session doesn't reach for pure-elastic (which
inverts the risk ranking) or re-derive the EPP membrane solve. **How to apply:** future quench-mechanics
work (TRIP, hardenability-limited cores, residual-stress-aware design/inverse) builds on this EPP slab
seam; the cited Eurocode/lattice property functions are reusable. Makes §17 quantitative — amends
[[martemper]]; sibling of [[di-crosscheck-source]]/[[mixed-temper-next]] ("no new physics/fitted number"
stance). Remaining §11 menu = only the unified-KV-pearlite rebuild (6b deepening).
