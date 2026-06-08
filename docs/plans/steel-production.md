# Steel Production Simulator — Project Plan

> Per-project plan #1 of the educational-simulator program. Built to the
> **Section 10 template** of `ARCHITECTURE.md`; inherits Sections
> 2–9 as fixed invariants (compliance check in §8 below). This is the
> **first** project in build order (Steel → Microchip → Planet) and the one
> that **builds and freezes the diffusion/heat solver** — the spine the other
> two inherit.

---

## 1. One-line vision & the dramatic early win

**Vision.** *Cooling curve in, microstructure out:* take a steel of a chosen
composition, austenitize it, cool it along any path you like, and watch which
phases form — and therefore what material you end up with — emerge from real
thermodynamics and transformation kinetics, not a lookup table.

**The anchor demo (Phase 1's banked artifact).** *Same steel, four cooling
curves, four different materials.* One eutectoid-ish steel (AISI 1080,
0.8 wt% C) austenitized at ~850 °C, then cooled four ways — furnace, still air,
oil quench, water quench — overlaid on its own TTT/CCT diagram. Out come four
microstructures (coarse pearlite → fine pearlite → bainite → martensite) and
four hardness numbers spanning ~150 HB to ~65 HRC. One steel, one figure, four
materials: the cheapest, most counter-intuitive payoff in the whole portfolio,
and it is *simultaneously* the integration test for every Phase-1 module.

---

## 2. Shared engines consumed

| Engine | Status here | Contract pointer |
|---|---|---|
| **Diffusion/heat (Fick / erfc)** — the program spine | **`[FROZEN ✓ — Phase 1a, 2026-06-08]`** | `engines/diffusion/CONTRACT.md` (now the real frozen contract; §4 below is the original draft). This is *the* deliverable other projects inherit: Chip's dopant profiles = the carbon-diffusion code; Planet's EBM heat transport = the heat-conduction instantiation. |
| **ODE / path-integrator (minimal)** | `[build minimal here — steel-local]` | `projects/steel/pathint.py`. The lightweight piece Steel needs: marching the Scheil additivity integral and Avrami fraction along a cooling path, plus an optional lumped-capacitance 0-D cooler. Kept in `projects/steel/`, **not** `engines/` — only steel uses it, so per invariant 5 / rule-of-three it is *not* promoted to the shared toolkit until a stabilized interface has ≥3 uses. The heavy symplectic/RK4 family (jet, star, galaxy) is not built here. |

No other shared engine is touched. CALPHAD (Phase 4) is consumed as a
**validation reference and optional backend** (pycalphad), *not* reimplemented —
see §5 scope ceiling and §6 terms of use.

> **Freeze-before-reuse (invariant 5 / ARCHITECTURE.md §6).** The diffusion solver is
> sealed behind its passing validation suite at the **end of Phase 1**, before
> Microchip or Planet are allowed to depend on it. Its CONTRACT.md is the
> one-page unit of context those projects load instead of this codebase.

**Language & performance.** Default is Python + NumPy/SciPy. A profiled hotspot
is accelerated in place (Numba/Cython, or JAX/CuPy on GPU); if an engine ever
needs a compiled core it is reimplemented behind its frozen `CONTRACT.md`
without touching consumers. Engine contracts stay data-oriented (arrays in/out)
so that same boundary doubles as the seam for deferred heavy modules. Full
rationale + alternatives: `docs/decisions/0001-language-and-performance.md`.

---

## 3. Phases — each a complete, demonstrable artifact

Every phase below names its **validation triad** concretely: an *analytical
limit*, a *conservation law*, and a *published benchmark* (program invariant 3 /
ARCHITECTURE.md §7). The triad is not boilerplate — it is the project's externalized
memory and the test that lets a later session change a solver and *know* it
still honors its contract.

### Phase 1 — "Cooling curve in, microstructure out" (the foundation)

Phase 1 is deliberately **both** the erfc-validated diffusion/heat
solver **and** the Fe-C + Avrami core. It is internally staged (1a→1c) but banks
**one** artifact: the four-curves-four-microstructures demo. Nothing is reused
downstream until 1a is frozen.

- **1a — Diffusion/heat solver** (the spine). Generic conservative 1-D parabolic
  PDE, implicit/unconditionally stable, finite-volume. Two instantiations used
  by steel: *mass mode* (carbon in austenite, `D(T)` Arrhenius) and *heat mode*
  (transient conduction with a convective quench boundary). **Frozen** at end of
  1a behind its test suite. Contract in §4.
- **1b — Fe-C equilibrium.** Metastable Fe–Fe₃C diagram via published
  boundary approximations (A₁ = 727 °C; A₃ from 912 °C → 727 °C; A_cm to
  1147 °C / 2.11 % C; eutectoid 0.76 % C). **Lever rule** → equilibrium phase
  fractions (pro-eutectoid ferrite/cementite + pearlite). This is the *endpoint*
  and the thermodynamic driving force for kinetics. *Note:* the pro-eutectoid
  lever-rule teaching moment is **degenerate on eutectoid 1080** (pro-eutectoid
  fraction ≈ 0 — there the lever rule is just the ferrite/cementite split
  *within* pearlite); show the dramatic pro-eutectoid split on a **hypoeutectoid
  1045** instead.
- **1c — Transformation kinetics.** Isothermal **JMAK/Avrami** `X(t)=1−exp(−k(T)tⁿ)`
  → TTT diagram (the C-curve nose from the driving-force × mobility product).
  **Scheil additivity** `∫dt/τ(T(t))=1` bridges isothermal → continuous cooling
  (CCT). **Koistinen–Marburger** athermal martensite `f=1−exp(−α(M_s−T))` with
  **Andrews** `M_s` from composition. A lumped/0-D cooler (or 1a in heat mode)
  supplies `T(t)`.

**Validation triad — Phase 1**
- *Analytical limit:* (a) erfc semi-infinite-solid carbon profile
  `(C−C₀)/(C_s−C₀)=erfc(x/2√(Dt))` — exact, the solver's headline check;
  (b) lever-rule fractions exact at a chosen `(T, %C)`; (c) Avrami round-trip —
  the `ln(−ln(1−X))` vs `ln t` fit recovers the input `(n, k)` (a Feigenbaum-style
  "recover the constant" check); (d) KM fraction at `T`.
- *Conservation:* carbon mass `∫C dx` constant to machine precision under
  no-flux BCs (finite-volume guarantee); enthalpy bookkeeping in heat mode;
  phase fractions sum to 1 across all products.
- *Benchmark:* TTT-nose temperature/time for AISI 1080 vs a published TTT
  diagram (ASM-style, used as *reference facts*, not redistributed); `M_s` from
  Andrews vs published values.

**Banked artifact:** the anchor figure of §1, produced through a small
**sweep / what-if harness** (`sweep.py`) — parameter sweeps over cooling rate
and composition are a *named Phase-1 feature*, not a one-off script (ARCHITECTURE.md §1
makes experimentation a core target and ties sweeps to "the cheapest
verification").

### Phase 2 — Jominy hardenability (the spatial step)

Now the heat solver earns its keep *spatially*: the standard end-quench bar
(one end water-cooled via a Robin BC, rest cooling to air) → a cooling-rate
profile vs distance → CCT → hardness vs distance from the quenched end. Adds
**alloying effect on hardenability** (Mn/Cr/Mo shift the TTT curves right,
flattening the Jominy curve). First real external-dataset validation.

**Validation triad — Phase 2**
- *Analytical limit:* lumped-capacitance cooling (Biot `Bi=hL/k < 0.1`) gives
  exponential `T(t)`; the solver must reproduce it in that regime.
- *Conservation:* heat extracted = `∫ρc_p ΔT dx` (energy balance on the bar).
- *Benchmark:* Jominy hardness-vs-distance curves for **AISI 1045 and 4140** vs
  published end-quench data.

**Banked artifact:** interactive Jominy curve — pick a steel, see the
hardenability band; compare a plain-carbon vs an alloy steel side by side.

### Phase 3 — Structure → properties & carburizing case-hardening

Closes steel's **process → properties** loop (the analogue of chip's
process→device loop). A property model maps (phase fractions, composition,
cooling rate / interlamellar spacing) → hardness, with a rough
strength/toughness trade-off. **Carburizing** reunites both faces of the spine:
the *mass-diffusion* instantiation computes a surface-enriched carbon profile
(erfc), then position-dependent `%C` feeds the transformation + property model →
a **case-hardened gradient** (hard, wear-resistant surface over a tough core).

**Validation triad — Phase 3**
- *Analytical limit:* case depth scales as `√(Dt)` (erfc), exact.
- *Conservation:* carbon mass uptake = surface flux integrated over time.
- *Benchmark:* case depth & surface hardness vs published carburizing tables;
  microstructure→hardness vs published hardness ranges for the named phases.

**Banked artifact:** a carburized gear-tooth cross-section — carbon profile,
microstructure gradient, and hardness traverse, all from the *same* solver.

### Phase 4 — CALPHAD-backed equilibrium (the bounded deep end)

Swap Phase-1's parametrized Fe-C boundaries for **pycalphad**-computed multi-
component equilibria; extend to low-alloy steels (Mn, Cr, Mo, Ni). This is the
`→ CALPHAD` endpoint of the portfolio table — and it stops **hard** at the scope
ceiling (§5): equilibrium thermodynamics and path-integrated kinetics only,
**no phase-field**.

**Validation triad — Phase 4**
- *Analytical limit:* Fe-C invariant points reproduced (eutectoid 0.76 % /
  727 °C; γ max solubility 2.11 % / 1147 °C).
- *Conservation:* lever-rule mass balance holds against CALPHAD-returned phase
  fractions.
- *Benchmark:* phase boundaries & fractions agree with pycalphad within
  tolerance on a low-alloy composition.

**Banked artifact:** the Phase-1 demo, re-run on a real 4140 composition with
CALPHAD thermodynamics, showing what the parametrized version got wrong.

---

## 4. Module map & contracts

Repository layout (Python; NumPy/SciPy core — chosen to match the program's
reference ecosystem: pycalphad, climlab, REBOUND, MESA are all Python). Files
are deliberately small so any single task loads with its neighbors' *contracts*,
not their internals (ARCHITECTURE.md §6).

```
BigSim/
  PORTFOLIO.md                      # the project catalog (30+ sims)
  ARCHITECTURE.md                   # program doctrine, invariants, §10 plan template
  docs/
    plans/steel-production.md       # this plan
    decisions/                      # ADR-style decision log (one file per call)
  engines/                          # shared toolkit — standalone, separately tested
    diffusion/
      diffusion1d.py                # the solver
      CONTRACT.md                   # the FROZEN one-page API (below)
      tests/                        # erfc, conservation, stability — the seal
  viz/                              # shared viz toolkit (peer to engines/); seeded by rule-of-three
  projects/steel/
    fe_c.py                         # phase diagram + lever rule           (1b)
    kinetics.py                     # Avrami/TTT, additivity/CCT, KM, Andrews Ms (1c)
    pathint.py                      # steel-local path-integrator: additivity ∫dt/τ + Avrami-along-path + 0-D cooler
    cooling.py                      # cooling-path presets (h for air/oil/water/furnace)
    sweep.py                        # sweep / what-if harness — parameter sweeps → side-by-side comparison
    properties.py                   # microstructure → hardness/strength    (Phase 3)
    jominy.py                       # end-quench hardenability               (Phase 2)
    carburize.py                    # case-hardening gradient                (Phase 3)
    calphad_backend.py              # optional pycalphad equilibrium         (Phase 4)
    plots.py                        # steel-local plot helpers (→ promote to viz/ by rule-of-three)
    app.py                          # thin Streamlit what-if app (sliders → live re-run)
    steel.ipynb                     # teaching notebook (narrative + ipywidgets sliders)
    demo_four_curves.py             # the anchor artifact (static figure via plots.py)
    README.md                       # per-module map + per-session load pointer
    tests/
  pyproject.toml
  run_tests.ps1 / run_tests.sh      # single-command runner (§7)
```

### The diffusion/heat solver contract (FROZEN at end of Phase 1)

This is the cross-cutting interface the whole program hinges on; it is specified
here precisely because a vague contract is the one mistake that propagates to
Chip and Planet (ARCHITECTURE.md §5–6).

> **Built & frozen (Phase 1a, 2026-06-08).** The authoritative contract now lives
> in `engines/diffusion/CONTRACT.md`; the draft below is preserved as the
> planning record. Two deliberate refinements made during the build: (1) the
> engine is kept **generic / D-agnostic** — the Arrhenius `D₀,Q` (and `α,h`) are
> the *consumer's* and are validated in steel's mass/heat usage, not in 1a, so
> the frozen seal promises a correct generic solver, not specific constants; and
> (2) the per-method stability guarantee is made explicit (backward-Euler is the
> unconditionally-stable *and monotone* default; Crank–Nicolson can oscillate at
> large dt). A `source`-term seal was added since `S` is part of the frozen API.

Draft of `engines/diffusion/CONTRACT.md`:

- **Solves** the conservative 1-D parabolic PDE
  `∂u/∂t = ∂/∂x( D(x,…) ∂u/∂x ) + S(x,t)` on `x∈[0,L]`, where `u` is a generic
  conserved intensive scalar. **Two instantiations** ship with steel:
  - *mass mode:* `u = %C`, `D = D₀·exp(−Q/RT)` (carbon in austenite,
    `D₀≈2.3e-5 m²/s`, `Q≈148 kJ/mol`; values **fit & validated**, not asserted).
    Conserved: `∫C dx`.
  - *heat mode:* `ρc_p ∂T/∂t = ∂/∂x(k ∂T/∂x)`; pass `D = α = k/(ρc_p)`; quench
    via Robin BC with `h`. Conserved: enthalpy `∫ρc_p T dx`.
- **Discretization:** cell-centered **finite volume** (conservation exact under
  no-flux) + **implicit** time stepping (backward-Euler default, Crank–Nicolson
  optional) → **unconditionally stable**, so a learner may pick any `dt` without
  blow-up. Tridiagonal solve (`scipy.linalg.solve_banded`).
- **Boundary conditions** (each end, independently): **Dirichlet** `u=u_b`;
  **Neumann** `flux=q` (`q=0` ⇒ insulated/symmetry/conservation); **Robin**
  `−D ∂u/∂x = h(u−u_ext)` (Newton cooling / quench).
- **`D`** may be constant, `D(x)`, or a callable `D(T)`/`D(t)`. Full nonlinear
  `D(u)` (e.g. `D(C)`) is **v1.1**, flagged not built, to keep v1 small.
- **API sketch:**
  `solver = Diffusion1D(grid, D, bc_left, bc_right, source=None)` →
  `state = solver.step(state, dt)` / `solver.solve(state, t_end, dt)`;
  diagnostics `solver.total(state)` (∫u dx), `solver.flux(state, end)`.
- **Frozen invariants (what the test suite guarantees, = the contract):**
  1. erf/erfc semi-infinite solution within tol; ~2nd-order spatial convergence.
  2. Exact conservation under no-flux (`Σ uᵢΔxᵢ` constant to machine precision).
  3. Stability for any `dt>0` (no oscillatory blow-up).
- **Units:** SI throughout; mass vs heat mode differ only by relabeling
  `u, D`, and BC parameters — that symmetry is *why* one engine serves both.

> Once this file's tests pass, the solver is **sealed**. Chip and Planet load
> *this page*, never `projects/steel/`.

---

## 5. Scope ceiling — consequence, not mechanism

**The named tar pit:** spatially-resolved **phase-field** modeling of dendrite /
microstructure morphology on a mesh (ARCHITECTURE.md §8). It is a research/compute wall,
not a token problem.

**What we target instead — the consequence:** *path-integrated kinetics.* We
compute **phase fractions and properties** as a functional of the cooling path
(TTT + additivity + KM), never the spatial morphology that produced them. A
learner sees *"40 % bainite, 60 % martensite, 58 HRC,"* not a simulated dendrite
field. The deep end here is **CALPHAD-grade thermodynamics + multicomponent
kinetics (Phase 4)** — rich, validated, and feasible — with phase-field left
explicitly outside the line.

**Loose-coupling / extensibility hook (ARCHITECTURE.md §8 mandate):** modules exchange plain
arrays (a cooling path `T(t)`; a `%C(x)` profile; a phase-fraction dict). That
boundary is exactly where a future phase-field module *could* be slotted to
consume a local thermal history — designed-for but not built. Nothing in v1
forecloses it.

---

## 6. Terms-of-use status

**Clean per ARCHITECTURE.md §9** — steel is published fundamental science:
no copyright dimension (implement equations from principles, original code/prose,
no verbatim listings/figures) and **no export-control dimension**.

**The one dataset diligence item — CALPHAD databases (Phase 4).** pycalphad
itself is open-source, but TDB thermodynamic databases vary in license.
*Action:* use only openly-licensed Fe-C/low-alloy assessments; treat any
commercial/research DB as **validation-only, never redistributed**; never commit
a `.tdb` (already in `.gitignore`). Published TTT/CCT/Jominy curves are used as
**reference facts for comparison**, not copied as datasets or figures.

---

## 7. Test runner

Single command, fast, runs the whole suite (engines + steel) so any session can
verify cheaply (ARCHITECTURE.md §6 hygiene):

```powershell
# from repo root
./run_tests.ps1          # wraps:  pytest -q
```

`run_tests.ps1` (and a `run_tests.sh` twin) invoke `pytest -q` over
`engines/**/tests` and `projects/steel/tests`. The erfc + conservation +
stability tests under `engines/diffusion/tests/` are the **seal** that freezes
the spine; they must stay green for any change anywhere downstream.

---

## 8. Invariant-compliance check (against ARCHITECTURE.md §2–9 — not re-litigated)

| Program invariant | How this plan honors it |
|---|---|
| 1 — build toolkit once, solver-heavy first | Phase 1a builds & freezes the diffusion/heat spine; Chip/Planet recompose it. |
| 2 — phase so each stage banks a working artifact | Four phases, each with an explicit banked artifact; Phase 1 alone is demonstrable. |
| 3 — validation triad from day one | Instantiated *concretely per phase* in §3 (analytic + conservation + benchmark). |
| 4 — target consequence where mechanism is a wall | §5: path-integrated kinetics instead of phase-field. |
| 5 — reuse only frozen modules | Solver sealed behind its test suite at end of 1a, before any downstream use. |
| 6 — updating docs is part of every change | ARCHITECTURE.md + per-module READMEs + `docs/decisions/` log are Phase-1 deliverables and maintained per change. |
| Terms of use (ARCHITECTURE.md §9) | §6: clean; CALPHAD DB licensing flagged as the lone diligence item. |

---

## 9. Visualization & UX

Per ARCHITECTURE.md §12 (and ADR 0002): compute stays headless; these views
consume the engine's plain outputs.

- **Floor (universal):** the §1 anchor figure — four cooling curves, four
  microstructures, four hardness numbers — as a static matplotlib figure, the
  banked Phase-1 artifact (testable against golden/numeric output).
- **Mechanism view:** the cooling path **animated across the TTT/CCT C-curve**,
  so the learner *sees* why a fast quench misses the nose and lands in
  martensite — the "teach the mechanism" payoff (target #1), not a bare hardness
  readout.
- **Experimentation:** a `sweep.py`-backed what-if surface delivered two ways — a
  **teaching notebook** (`steel.ipynb`, narrative + ipywidgets sliders for %C,
  cooling rate, quench medium) and a **thin Streamlit app** (`app.py`, shareable
  slider UI). Steel is the program's flagship, so it ships **both** as the
  demonstrator; later sims build only the interactive surface their pedagogy
  needs.
- **Toolkit:** plot primitives start as steel-local `plots.py` and are promoted
  to the shared `viz/` by rule-of-three (ARCHITECTURE.md §6), like `pathint.py`.

Responsiveness is free here: Phase-1 compute is sub-second (ADR 0001 scope), so
slider → re-run → re-plot needs no special engineering.

---

## 10. Immediate next step

**Phase 1a is built and frozen ✓** (2026-06-08) — `engines/diffusion/` (solver +
`CONTRACT.md` + a 5-file test seal: erfc/2nd-order convergence, exact no-flux
conservation, per-method stability, source-augmented conservation, heat-mode
Robin + flux bookkeeping). The diffusion spine the entire trio inherits is sealed.

**Phase 1b is built ✓** (2026-06-08) — `projects/steel/fe_c.py`. Metastable
Fe–Fe₃C boundaries linear between the pinned invariant points (A₁=727 °C; A₃
912→727 °C; A_cm 727→1147 °C / 2.11 % C; eutectoid 0.76 % C) + the **lever rule**.
Two readings: `phase_fractions(C0, T)` → the phase dict (ferrite/austenite/
cementite), and `equilibrium_constituents(C0)` → pro-eutectoid ferrite/cementite +
pearlite (the teaching split — dramatic on 1045, near-degenerate on 1080). A
42-test triad: exact invariant points + lever-rule fractions (analytical), carbon
mass balance `Σ fᵢCᵢ=C0` + constituent↔phase consistency (conservation), AISI
1045/1080 published facts (benchmark). Full suite green (60 tests). The 727 °C
isotherm convention is documented + pinned.

**Phase 1c is built ✓** (2026-06-08) — `kinetics.py` + `pathint.py` + `cooling.py`
+ the banked anchor demo. Isothermal **JMAK/Avrami** with a **TTT C-curve** whose
nose is the *driving-force × mobility* product (`τ=τ₀·exp(Q/RT)·exp(K_N/(T·ΔT²))`,
ΔT the undercooling below `fe_c`'s A₁, abs T in kelvin); **Scheil additivity**
∫dt/τ=1 → CCT start (reduces to the isothermal τ under a hold — the consistency
leg); **Koistinen–Marburger** athermal martensite with **Andrews** `M_s`, applied
to the *retained* austenite so the products sum to 1 exactly; a 0-D lumped Newton
cooler supplies `T(t)`, each path flagged by **Biot number** (water exceeds the
lumped-validity 0.1 → the honest hand-off to Phase-2's spatial solve). Calibrated
1080 nose ≈ 550 °C / 1.0 s (matches published TTT). 68-test triad; full suite
**128 green**. The anchor figure (`docs/figures/steel-four-curves.png`, via the
opt-in `[viz]` extra) shows one 1080 cooled four ways: a **property span from soft
pearlite (~20 HRC) to very-hard martensite (~63 HRC)**. *Honest scope note:* the
four rates yield **three** distinct phase constitutions, not four — furnace and air
both give pearlite, separated only by formation temperature (coarseness); the §1
"four microstructures" phrasing was an idealization, and coarse/fine pearlite +
real hardness numbers are Phase 3.

**Phase 2a is built ✓** (2026-06-08) — `projects/steel/jominy.py`, the first
*spatial* reuse of the frozen heat solver. The end-quench bar is the **transient
fin equation** (axial conduction + lateral air convection), *not* pure axial
conduction: a timescale check (`√(αt) ≈ 8 mm at 10 s`) shows adiabatic sides leave
the far half uncooled for ~25 min, so lateral loss is what makes the real Jominy
gradient. Robin (water jet) at the quenched end, insulated tip. The frozen
`source` can't carry the lateral sink (it depends on the live `T`), so it is
composed *around* the engine by **Strang operator splitting** — an analytic-
exponential lateral half-step (exact, unconditionally stable) on either side of one
frozen implicit conduction step; the sealed engine is never touched (the ADR-0001
array seam as designed). Subtle unit pinned by test: engine Robin `h_eng =
h_phys/(ρc_p)`. Two triad legs banked: the **analytical limit** (thermally-thin
`Bi < 0.1` reduces to `cooling.py`'s 0-D Newton cooling, `τ_lat = ρc_p(d/4)/h` —
matched to 1e-12; a both-ends-Robin slab pins the h-conversion) and **conservation**
(two-sink energy balance `Δ∫T dx = end-flux + lateral-loss` to ~1e-11), plus a
**thermal benchmark**: cooling-rate-vs-distance tracks the published Jominy
distance↔rate equivalence at 700 °C (mean ratio ~0.92, mid-range within the ~±25 %
literature spread) and is **resolution-converged** (< 1.2 % under 2× refinement) — so
it's fin physics, not a discretization artifact. This thermal curve is frozen *before*
the 2b hardenability calibration on purpose (below). The near end runs hot (`h_quench`
is the one free thermal knob, martensite-saturated → hardness-irrelevant). 11 tests;
full suite **139 green**.

**Next: Phase 2b/2c** — the calibration-heavy half and the third triad leg.
**2b:** hardenability = an alloy shift of the `CCurve` (Mn/Cr/Mo move it right;
default identity so the 1080 demo stays byte-identical). **2c:** a
microstructure→hardness map (seed a minimal `properties.py`; Phase 3 extends it) →
the **Jominy hardness-vs-distance** artifact + the **1045/4140 benchmark**. To keep
the benchmark *validating* rather than curve-fitting three knobs (h_water, τ-shift,
hardness) against one curve, exploit the pair's structure — both are ~0.4 %C so they
share a quenched-end hardness (validates the hardness model alone) and they diverge
with distance (validates the hardenability shift alone) — and anchor each sub-model
to its own published data. The subtler confound is that the **mid-range thermal
accuracy** (not `h_quench`) is what the τ-shift could absorb — both act on the
~5–25 mm knee — which is exactly why Phase 2a froze its thermal benchmark *before*
this calibration begins. **Deferred from Phase 1c:** the experimentation surface
(`sweep.py`, `app.py`, `steel.ipynb`) — the static-figure floor is banked; the
interactive layer is the next viz increment. Nothing downstream touches the frozen
solver's internals — only its `CONTRACT.md`.
