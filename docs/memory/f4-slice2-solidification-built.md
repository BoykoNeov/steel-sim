---
name: f4-slice2-solidification-built
description: "F4 Slice 2 (latent-heat solidification field + casting defects) BUILT 2026-06-13 — 2nd solver-bearing front-end physics, enthalpy method on the sealed engine (NO touch/ADR); headline tooth = analytic Stefan benchmark"
metadata:
  node_type: memory
  type: project
---

**F4 Slice 2 — latent-heat solidification field + casting defects BUILT ✓ 2026-06-13** (the deferred half of
F4 named in [[f4-casting-built]]). `steel/solidification.py` + demo + `plots.solidification_figure` + 14+5
tests; **722 fast-lane green** (+19); **NO engine touch, NO ADR** — the **second solver-bearing front-end
physics** (after back-end Jominy/carburize), reusing the sealed heat engine's *already-unfrozen* nonlinear
`D(u)` path (ADR 0004). User picked this off the "physics deferral" menu (over `game/` / H-flaking / carbon
carry-in / tempered-martensite-embrittlement).

**THE FORMULATION CRUX — enthalpy method, NOT apparent-capacity-via-D(T) (the trap the advisor confirmed).**
The engine solves `∂u/∂t=∂ₓ(D∂ₓu)` with **unit LHS capacity** + a source that is `S(t)` only → latent heat
is not a simple source. The tempting shortcut (fold `c_app(T)` into a *temperature-mode* `D(T)=k/ρc_app`) is
**physically WRONG**: `ρc_app∂T/∂t=∂ₓ(k∂ₓT)` doesn't reduce when `c_app` varies in space (spurious
`k∂ₓT·∂ₓ(1/ρc_app)`; engine would conserve `∫T dx` ≠ enthalpy). Right route = **state `u`=specific
enthalpy** (the engine's heat-mode invariant IS `∫h dx`): `∂h/∂t=∂ₓ(D(h)∂ₓh)`, `D(h)=(k/ρ)dT/dh` drops in the
mushy range → front slows (the plateau), conserved exactly (D-cache → machine-precision identity ~1e-13).
Maps onto `D_of_u` natively.

**DURABLE NUMERICAL LESSONS (spot-checked BEFORE building, per advisor — both standard forms fight in naive
shape):**
- **Picard on a step-function `D(h)` FAILS** (lever-rule top-hat `f_s` linear in T → `D` jumps ~9× at the
  mushy edges → oscillation). Fix = **smooth `f_s` (sin²) = numerical REGULARIZATION, not a physics claim**
  (advisor framing); legitimacy *proven by the tooth*: the Stefan front depends on latent **content** + α,
  not the profile shape (`∫df_l=1` for any shape) → insensitive to sin². Do NOT defend "sin² is real `f_s`".
- **Naive explicit latent-heat SOURCE (Option C) was UNSTABLE** — dumps a cell's whole latent heat in one
  step, 3 sub-iters didn't converge → toggle came out **backwards** (0.07× instead of >1). So enthalpy +
  smoothing + Dirichlet was the working path (advisor's A-if-Picard-cooperates, after it cooperated *with*
  smoothing).
- **BC locked to Dirichlet/Neumann** — with `u=h` the engine's `Robin` cools toward an *enthalpy* (wrong for
  Newton's law on T) → narrative committed to a **fixed-temperature chill** (chill/water-cooled mold; exact
  since `T(h)` monotone). Convective cooling = named scope edge (the `martemper`/`residual` idiom on `u=T`).
- **`h→T` inversion table must span below the chill temp** — a clamping bug (table started at `T_sol−400`)
  pinned all cold cells to 1038 °C; caught by the round-trip + map tests, fixed to span −50 °C upward.

**TEETH POSTURE (advisor FLIPPED their own first steer — surfaced inline):**
- **HEADLINE TOOTH (validated, untuned): analytic one-phase Stefan/Neumann benchmark.** Numerical `f_s=0.5`
  front **converges to** `X=2λ√(αt)` (λ from `λe^{λ²}erf(λ)=St/√π`) under grid refinement. **Be faithful to
  what's REPRODUCIBLE (advisor completion catch):** the committed demo/test grid (n=144/216) lands **~3 %
  below analytic (`0.958→0.969`)**; the **~1 % match was the in-session n=800/1600 study, NOT committed** — so
  the durable records say "~3 % at the demo grid, tightening toward ~1 % under refinement," not a bare
  "~1–2 %" (which slipped into the first commit msg/plan/memory → corrected in a follow-up). Residual = grid
  resolution (`ΔT→0` *under-resolves* on a fixed grid — do NOT show convergence by narrowing ΔT; advisor
  caught the common-asymptote tell) + a solidus-isotherm offset if tracking the fully-solid front. Pattern =
  carburize-vs-erfc.
- **Directional sanity (NOT a tooth):** latent ON/OFF toggle slows freeze-through ~×3 (order `L/c_pΔT`;
  shape-dependent). Advisor **demoted this from the headline it first proposed** (≈9.24×) — my data (5×/3×)
  showed it's profile-dependent, so it's a sanity check, the Stefan match is the clean quantitative tooth.
- **By construction (NOT teeth):** Niyama `Ny=G/√Ṫ` (cited *form*; ~constant in the directional region — the
  textbook signature a chill casting is sound — collapsing at the insulated centre where `G→0`) + the
  last-to-freeze **hot spot** (the insulated centre freezes last = *the same centerline [[f4-casting-built]]
  Slice 1 enriches* → porosity + macro-seg, one place, two reasons). Named illustrative up front (the
  Mushet/TE-nose discipline → [[temper-embrittlement-built]]). **Chvorinov stays scaling-only** (metal-
  conduction chill ≠ mold-diffusion `B` regime).

Demo `demo_solidification` (4 panels: map / latent arrest / Stefan benchmark / hot-spot+Niyama). Notebook &
app deferred (as F1/spine/F4 Slice 1). Hot-tear + a defect-feeding model remain deferred. Amends
[[f4-casting-built]]; companion solver-physics to [[residual-stress]]/[[martemper]]; di-crosscheck discipline
[[di-crosscheck-source]].
