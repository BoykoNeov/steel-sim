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
    steel.ipynb                     # teaching notebook (narrative + ipywidgets sliders)  ✓ slice 1
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

### Slice plan — the interactive surfaces (on the built `sweep.py` harness)

`sweep.py` (the headless harness) is **built ✓** (2026-06-08). The two interactive
layers are thin surfaces on it — both just wire sliders to `sweep.evaluate` /
`cooling_rate_sweep` / `composition_sweep` / `sweep_grid` / `temper_sweep` and reuse the
existing figures (`four_curves_figure`, `sweep_comparison_figure`, `plot_ttt`). They extend
*reach*, not correctness: per ADR 0002 the static figures + the `sweep`/properties triads are
the validation; a UI layer's test is an **execution smoke-test**, not new physics. Three
slices, in order:

1. **Slice 1 — `steel.ipynb` (the teaching notebook).** **Built ✓** (2026-06-08). The
   *education* artifact (target #1): a guided "cooling curve in, microstructure out" narrative —
   Fe-C endpoint → TTT C-curve → the four-curves anchor → composition × cooling-rate
   hardenability → tempering — with ipywidgets sliders (%C, grade, quench medium, section size,
   temper T/t) re-running the harness live. **Banked:** the committed, executed `.ipynb` (its
   five static figures embedded so it reads on GitHub without a kernel). **Dep:** the new
   `[notebook]` extra (`ipywidgets` + the `nbclient`/`nbformat`/`ipykernel` run machinery;
   matplotlib stays in `[viz]`, so the runnable combo is `.[viz,notebook]`). **Discipline as
   built:** every *compute* cell calls a `sweep`/`properties`/`fe_c` function **directly** (a
   static figure per section), with `interact` layered on top as sugar — because
   `ipywidgets.interact` runs its callback inside an `Output` that *captures* exceptions, so a
   broken call inside an interact callback would never reach `nbclient`; the load-bearing compute
   therefore lives in plain cells (verified empirically: a `raise` in a direct cell turns the
   test red, the same `raise` in an interact callback stays green). The **test**
   (`tests/test_steel_notebook.py`) executes the notebook top-to-bottom headless (`nbclient`,
   `allow_errors=False`) and asserts no cell errors — gated on the `[notebook]` stack **and a
   registered kernelspec** (separate from `pip install ipykernel`), so a clean/headless checkout
   *skips*, never errors. The `%C` slider drives only the Fe-C *equilibrium* cell (where minor
   alloy genuinely doesn't enter); the cooling/hardness/temper sections use the `STEELS` grade
   dropdown to avoid the documented "leaner hypothetical" (`Mn = 0`) trap. *That it executes
   clean*, not a physics check.

2. **Slice 2 — `app.py` (the thin Streamlit what-if app).** *Next.* The shareable slider UI — the same
   harness re-skinned for the web: sidebar sliders → the mechanism view (paths on the TTT), the
   microstructure bars, the hardness readout, the temper curve, and a two-steel side-by-side
   (`composition_sweep`/`sweep_grid`). Cheap after slice 1 (same compute wiring; only the widget
   framework differs). **Banks:** a runnable `app.py` (`streamlit run`). **Dep:** `streamlit` (a
   new `[app]` extra). **Discipline:** keep all compute in importable helpers that call `sweep`
   directly, Streamlit calls confined to `main()`; the **test** imports the module and exercises
   the compute helpers (the UI itself is not unit-tested — ADR 0002).

3. **Slice 3 — D_I cross-check *or* begin Microchip (decide on arrival).** After slices 1–2 the
   experimentation surface is complete, so **all of Steel's planned work (Phases 1–4 + the §9
   flagship surface) is done**. *Recommendation: begin **Microchip**.* It is the program's core
   thesis (reuse the frozen `engines/diffusion` spine — Phase 1a = dopant erfc profiles, a fast
   validated win), and starting it from a 100 %-complete Steel is the clean program move
   (ARCHITECTURE.md §4). The **D_I** cross-check (ideal-quench diameters → critical one, vs
   published `D_I`) stays the *available, not-required* alternative — it adds only modest marginal
   validation to an already heavily-benchmarked Steel and blocks nothing, so it is the
   "button Steel up 100 %, including the optional benchmark, before leaving" option, not the
   priority. Appetite-driven; revisit when slices 1–2 land.

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

**Phase 2b is built ✓** (2026-06-08) — `kinetics.hardenability_factor` +
`ccurve_for_steel`, the alloy **hardenability** C-curve shift. Mn/Cr/Mo slide the whole
TTT curve to longer times by a single multiplicative factor `M` on `τ` (shape- *and*
nose-temperature-preserving): `M` is the **Grossmann** alloy multiplying-factor product
taken *relative to the 1080 reference composition* and raised to one calibrated scale —
Grossmann used only for its **relative element potencies**, because its own magnitude lives
in ideal-critical-*diameter* space (which already convolves the thermal physics the fin
solver models, so using it for scale would double-count the very 5–25 mm knee Phase 2a
froze its thermal curve to protect). The reference carries 1080's ~0.7 % Mn, so `M = 1` is
the *calibrated reference steel* (default `tau_factor = 1.0` → the four-curves demo is
byte-identical) and a medium-carbon plain steel (1045) is **not** spuriously over-shifted.
The magnitude is calibrated to a defensible ≈ 8× shift for 4140 (its deep-hardening TTT
band) under which **1045 falls out ≈ identity — a non-circular prediction**. What is
*validated* (not merely calibrated) is the **mechanism**: fed the same Jominy bar's cooling
histories, 4140 stays martensitic far deeper (still ~0.6 at 25 mm) than 1045 (gone by
~13 mm) while both share the quenched-end martensite — the hardenability divergence, which
nothing but the shift can produce. v1 simplifications flagged: one factor shifts
pearlite+bainite together (no separate bainite bay), and `T_eq` is held at the eutectoid A₁
for hypoeutectoid steels. 8-test triad (identity + shape-preservation, the 4140-band
calibration + 1045 prediction, the divergence integration); full suite **147 green**.

**Phase 2c is built ✓** (2026-06-08) — `projects/steel/properties.py` + `demo_jominy.py`,
the microstructure→hardness map and the banked Phase-2 artifact, completing the **third
(benchmark) leg** of the Phase-2 triad (the analytical + conservation legs were banked
thermally in 2a). Hardness is a **rule of mixtures over the constituents** (`HV = Σ fᵢ·HVᵢ(C)`
— exactly the **Maynier 1978** Jominy-prediction structure), computed in **Vickers** (linear,
additive, soft-defined) and converted to **HRC** only at the boundary via an **ASTM E140**
table valid ~20–65 HRC (below 20 HRC Rockwell-C is undefined → `nan`, the honest output for a
soft pearlitic tail — the memory note). The discipline that keeps it *validating* not
curve-fitting (advisor): every constituent hardness is anchored to an **independent** dataset
— martensite to the **as-quenched-martensite-vs-%C** curve (Hodge–Orehoski/Krauss),
ferrite-pearlite to **normalized plain-carbon hardness** (ASM) — so the Jominy curve is a
genuine cross-source check, *not* tuned to the benchmark it is validated against. v1 drops
Maynier's cooling-rate and minor-alloy terms (carbon-only constituents → the minimal seed
Phase 3 extends). **What the benchmark leg actually shows** (recorded precisely, not flattened
to "validated ✓"): (1) the map in isolation — E140 pairs pinned, the martensite curve hit
across **0.2–0.8 %C** (the *slope*, since both benchmark steels are ~0.4 %C), pure-phase-exact
+ bounded + monotone mixing, **and** the **50 %-martensite criterion** (Hodge–Orehoski, ~43 HRC
at 0.4 %C — a *mixture* anchor independent of both endpoints, read at fM = 0.5 regardless of
spatial position, so it validates the transition decoupled from the kinetics); (2) the
consequence — 1045 & 4140 (both ~0.4 %C) **share the quenched-end hardness** (~55–57 HRC; full
martensite, the 2b shift silent → the hardness model alone) and **diverge with distance**, with
**4140 a quantitative match** to its published deep-hardening plateau (~55 HRC @ ½ in, ~49 @
1 in) and **1045's endpoints + the divergence matching**. The 1045 **knee sits ~2–3 mm deeper**
than a lean published 1040 — a *verified*-upstream artifact (re-running 1045 at `T_eq ≈ A₃ =
780` moves the knee shallower) of the documented Phase-2b **A₁-not-A₃** simplification, **not** a
hardness-map error: the linear rule cannot mismap the transition without breaking the validated
quenched-end anchor, so the well-anchored claims are asserted tightly and the 1045 knee
*position* loosely. 20-test file; full suite **167 green** (16 `test_properties` + 3
`test_demo_jominy` + the figure `docs/figures/steel-jominy-hardness.png`).

**Phase 3a is built ✓** (2026-06-08) — `properties.py` extended with **Maynier's (1978)
minor-alloy + cooling-rate terms**, and `demo_four_curves` **rewired** onto the real model
(the `INDICATIVE_HARDNESS` placeholders retired). It is an honest **graft**, not a switch to
"pure Maynier": 2c's *independently-anchored* carbon baselines (Hodge–Orehoski √C martensite;
normalized-plain-carbon linear ferrite-pearlite — the latter is the load-bearing quenched-end
anchor) are kept, and only Maynier's **non-carbon deltas** are bolted on — the minor-alloy
contribution and the cooling-rate slope, the latter **reference-zeroed** about a normalizing
`Vr` (the cooling rate at 700 °C, °C/h — one metric shared with `jominy` via
`cooling.cooling_rate_through`). **The seam (advisor):** every constituent gains optional
`comp`/`Vr` args whose defaults reproduce the 2c carbon-only value *byte-for-byte*, so the frozen
2c benchmark is unchanged and the new terms fire only where a caller passes them (the demos, the
case-hardening gradient). **What it buys** (validated in `test_properties.py`, anchored to the
cited Maynier coefficients — Scand. J. Metall. 33:98, 2004): the **minor-alloy term on martensite
closes the 4140≈1045 quenched-end gap** (was ~1.4 HRC, 4140 reading low on its 0.05 % less C;
now ~0.5 HRC, matching published "≈ equal") and lifts 1045's soft tail from off-HRC-scale onto
~20 HRC (≈ published 22). **Deliberate, measured honesty (advisor):** martensite is kept
**cooling-rate-independent** (its small `21·log Vr` term dropped — protects the quenched-end
anchor); the FP cooling-rate term is **small for plain carbon** (~10 HV/decade → furnace-vs-air
pearlite differ only ~5 HV, *not* oversold as resolving coarse/fine — that is the kinetic
`formation_T`); and **bainite's terms are deferred** (Maynier's bainite coefficients are large and
fit against his own `−323+185C` base, so grafting them onto 2c's placeholder baseline gives
unphysical `> martensite` hardness — bainite stays the least-anchored constituent). The four-curves
figure now reports a **real ~29 → ~62 HRC** property span. The banked Jominy figure is kept
**carbon-only** on purpose — it is a prior phase's deliverable (reworking it mid-3a is scope creep)
and the alloy-lifted 1045 tail sits right on the 240 HV / 20 HRC scale floor, so a demo assertion
there would be resolution-fragile; the gap-closing is validated in `test_properties` instead.
*Domain limit named:* because FP gets the alloy boost but bainite is deferred, the m>b>fp ordering
is guaranteed only for low-to-medium-alloy steels (a ~2 % Si steel could under-rank bainite). 9 new
tests; full suite **176 green**.

**Phase 3b is built ✓** (2026-06-08) — `properties.py` extended (section 5) with **tempering**
(the **Hollomon–Jaffe** parameter `P = T(C_hj + log₁₀ t)`, T in kelvin / t in hours) plus the
**ISO-18265 hardness→tensile-strength** conversion and a **rough strength/toughness trade-off** —
all *additive*, leaving the as-quenched model and the frozen 2c/3a/four-curves/Jominy benchmarks
byte-identical. Tempered-martensite hardness is a decreasing master curve `HV(P)` running between
two **independently-anchored** endpoints: the Phase-3a as-quenched martensite and the
ferrite-pearlite/spheroidite floor — so only the *transition* is calibrated, the same
anchored-endpoints + calibrated-transition shape as the 2c rule of mixtures. **The non-circularity
split (advisor, the crux — mirrors 2b/2c):** what is *validated* (asserted tightly) is the
parameter's **form** — the **time–temperature equivalence** (two `(T,t)` on the same `P` soften to
the same hardness; **convention-independent**, holding for any carbon and any `C_hj` because the
hardness depends on `(T,t)` only through `P`), the monotone softening in both `T` and `t`, and the
endpoint bound (a sub-onset temper returns the as-quenched value *exactly* — the seam; a deep
over-temper bottoms out on the floor *exactly*); what is *calibrated* (flagged, **not** dressed as
validation) is the value of `C_hj` (≈ 20, a **cited** low-alloy-steel constant — [[hollomon-jaffe-tempering-source]] — defaulted not fitted; its mild carbon-dependence left as an optional caller
override rather than baked in with unverifiable coefficients) and the softening **magnitude** (two
`P` breakpoints, the Phase-3b analogue of 2b's `HARDENABILITY_SCALE`), asserted only with **loose
sanity bands** the way the 1045 knee position was — calibrated so ~0.4 %C martensite tempered 1 h
follows the known Grange/ASM response (high-50s HRC as-quenched → low-40s at 400 °C → ~25 HRC at
600 °C). **Emergent (not a fitted term):** threading `comp` through *both* endpoints makes an alloy
steel **resist tempering softening** — 4140 stays harder than plain 0.4 %C at every temper (starts
harder *and* floors higher), matching published 4140 1 h data (~56→47→32 HRC at 200/400/600 °C).
**Strength** is the published **ISO 18265 / ASTM A370** conversion as an interpolated table (like
E140), valid ~150–550 HV with `nan` outside — it **degrades above ~550 HV** (untempered martensite
is exactly where the linear hardness–strength relation is least valid), the honest band edge; yield
is *not* returned (Tabor's `H≈3σ` is flow stress, not yield — reporting it would over-claim).
**Toughness** is a deliberately **rough, relative** dimensionless direction opposite to hardness —
**no Charpy-J is invented** because real impact toughness is steel/heat-specific and **non-monotone**
through the **tempered-martensite (~260–370 °C)** and **temper-embrittlement (~375–575 °C, alloy)**
troughs (the named scope ceiling). Tempering is **martensite-only** (pearlite barely tempers; a mixed
Jominy traverse would temper per-constituent — deferred). **The triad's benchmark leg (advisor):**
the plain-carbon bands are self-consistency (they were calibrated to), so the *independent* benchmark
is **4140's predicted 1 h tempering response** — calibrated only on plain-carbon breakpoints + the
Maynier-anchored (3a) comp deltas threaded through both endpoints, nothing fit to 4140 tempering data
— matching published ASM/Bhadeshia (~55 HRC @200 °C → ~45 @400 °C → ~33 @600 °C, loose ±~4 HRC), the
inverse of 2b's "calibrate 4140, 1045 falls out". No new figure (3b is a `properties.py` extension;
the test triad carries it). 10 new tests; full suite **186 green**.

**Phase 3c is built ✓** (2026-06-08) — `projects/steel/carburize.py` + `demo_carburize.py`, the
**mass-diffusion face of the spine**. The *same* frozen `engines/diffusion` that cooled the Jominy
bar in heat mode now runs in **mass mode**: carbon diffuses into a low-carbon part (≈ 8620, 0.2 %C
core) held at 925 °C in a 0.8 %C-potential atmosphere — a **Dirichlet** surface at the carbon
potential and a **Neumann(0)** core (symmetry plane *and* semi-infinite far field), constant `D`
from a *cited* (Callister) carbon-in-austenite Arrhenius, so the profile is the textbook **erfc**.
Position-dependent `%C(x)` then feeds the *same* `kinetics`/`pathint`/`properties` chain → the
**case-hardened gradient** (hard ~65 HRC martensite case over a softer ~48 HRC core; the banked
gear-tooth figure `docs/figures/steel-carburize-gradient.png`). This is the **cleanest triad in the
project**: its two headline legs are the frozen engine's own guarantees re-instantiated with **no
new calibration** — (analytical) the interior erfc match + case depth ∝ √(Dt) *exact* (asserted
tight; the *absolute* depth loose — constant-`D` under-predicts vs Tibbetts `D(C)`, a named scope
limit); (conservation) `Δ∫C dx = Σ dt·flux(left)` to machine precision (the engine's exact
backward-Euler flux identity, re-confirmed for the **Dirichlet** surface, core no-flux) + the
semi-infinite tie `2(Cs−C0)√(Dt/π)`; (benchmark) the 50-HRC effective case depth (~1.4 mm) in the
published band and the surface hardness cross-checking the independently-anchored martensite curve
(~65 HRC) — genuine cross-checks because `D0,Q` are cited diffusion data, not fit to case depth.
**The retained-austenite fork (advisor):** full kinetics at the high-carbon surface predicts heavy
retained austenite (low `Ms`; also past the ~0.8 %C anchor of Andrews/KM/√C-martensite), so the
surface-hardness benchmark is anchored to the martensite **potential** (the case as designed) while
RA is *reported* as the microstructure gradient + an honest as-quenched curve, **not** asserted vs
the published band. One quench is applied at all depths on purpose — the gradient is **carbon-driven**
(the complement to the cooling-rate-driven gradients of 1c/2; the thin case is thermally near-uniform
on the transformation timescale). 18 new tests; full suite **204 green**. **Available cross-check
(not triad-required):** the **D_I** downstream check (ideal-quench a series of diameters, find the
critical one, vs published `D_I`) — still available. **Still deferred from Phase 1c:** the
experimentation surface (`sweep.py`, `app.py`, `steel.ipynb`). Nothing downstream touched the frozen
solver's internals — only its `CONTRACT.md`.

**Phase 4 is built ✓** (2026-06-08) — `projects/steel/calphad_backend.py` + `calphad_reference.py` +
`demo_calphad.py`, the **CALPHAD-backed equilibrium** (the bounded deep end). Phase 1b's `fe_c` drew
the Fe-C diagram as **linear chords** between pinned invariant points; Phase 4 lets the boundaries
*emerge* from a real **Gibbs-energy minimisation** (**pycalphad**, *consumed not reimplemented* — plan
§2/§6) and **extends to multicomponent low-alloy steels** `fe_c` cannot represent. pycalphad is an
**optional `[calphad]` extra**; thermodynamic databases are **never committed** (plan §6): the binary
**Fe-C** assessment (`cfe_broshe.tdb`) ships *inside* the installed pycalphad, and the multicomponent
**MatCalc steel database** (`mc_fe_v2.060.tdb`, **openly licensed ODbL 1.0** — TU Wien / Povoden-Karadeniz;
[[matcalc-mc-fe-database-source]]) is fetched to a gitignored `data/tdb/` by `download_mc_fe()`. Runs on
**Python 3.14** via two documented, physically-validated shims: overriding pycalphad's conservative
`symengine<0.14` pin (only 0.14.1 has a 3.14 wheel) and a one-line `type(self).__annotations__` PEP-749
fix to `Workspace.__init__` (idempotent, applied only when the bug is present — never edits site-packages).
A minimal `load_clean_database` keeps only the TDB commands pycalphad's *own grammar* parses (dropping
molar-volume/mobility params + MatCalc metadata + ~8 wildcard-`G` params on excluded auxiliary phases) and
prunes constituent-less phases; the active phase set is curated and the **corrupted-not-absent**
`BCC_DISL`/`SIGMA`/`PDMN_B2` (which lost a Gibbs term in preprocessing) are deliberately excluded.

**Option C** (advisor) reconciles "no committed `.tdb`" with the validation-triad-must-be-green doctrine:
a **frozen reference table** (`calphad_reference.REFERENCE`) is generated *from the exact functions the
live test calls*, so the committed tests validate `fe_c` against it with **no pycalphad/database needed**
(they run on a clean checkout — verified), while `importorskip`-gated **live tests** re-derive the table
and assert it matches by construction (the binary half uses the bundled Fe-C DB → runs whenever pycalphad
is installed; the multicomponent half skips unless the steel TDB is present). **The non-circularity split
(advisor, mirrors 2b/2c/3b):** the **invariant points** *emerge* — eutectoid ≈ 726.6 °C / 0.757 %C, γ-max
≈ 1148 °C / 2.04 %C — but `fe_c` **pins** them by construction, so agreeing there is only a **wiring
smoke-test** (asserted *loose*); the leg with **teeth** is CALPHAD's *curved* A₃ vs `fe_c`'s *linear chord*
(**the chord over-predicts by +15→+29 °C across the hypoeutectoid range, worst ~29 °C at 0.3 %C** — the
quantified "what the parametrization got wrong", asserted in a 20–40 °C band) and the **multicomponent**
A₁/A₃ that `fe_c` cannot produce: **4140 (Fe-C-Cr-Mn-Mo-Si) → A₁ 720.7 °C, A₃ 771.8 °C** cross-checked
against the **independent Andrews Ae1/Ae3** empirical formulae (737/762 °C) within **loose ±20 °C bands** —
*not* a directional claim (CALPHAD and Andrews **straddle** the plain-carbon 727 °C; an alloy A₁ amid stable
**Cr-carbides** is not a sharp eutectoid). **Conservation:** recombining CALPHAD's phase amounts and per-phase
compositions recovers the input carbon to **machine precision** (`Σ fᵢ·Cᵢ = C0` — a free check on the
equilibrium output). Banked artifact: `docs/figures/steel-calphad.png` (two panels — the chord-vs-curve A₃
overlay + 4140's phase-fractions-vs-T with the **M7C3 chromium carbide** `fe_c` has no key for). The cleaned
database is cached by path+mtime so the live tests don't re-parse the 460 KB MatCalc file. 13 new tests
(6 committed always-green + 4 live + 3 demo); full suite **217 green** (210 without the optional stack).

**Experimentation surface — `sweep.py` built ✓** (2026-06-08) — `projects/steel/sweep.py` +
`demo_sweep.py` + a `plots.sweep_comparison_figure`. The first of the §9 experimentation
deliverables: the headless **sweep/what-if harness** ARCHITECTURE.md §1 ties to "the cheapest
verification". It is **pure re-composition** of the validated chain (`ccurve_for_steel` →
`cooling` → `pathint` → `properties`) — *no new physics, no new calibration, no new constant* —
so it carries **no triad of its own**; its tests (`test_sweep.py`) check *harness* correctness.
The single what-if `evaluate(steel, medium, …) → Outcome` (as-quenched microstructure + HV/HRC +
Vr + Biot flag) is swept over the **cooling-rate** axis (`cooling_rate_sweep`), the **composition**
axis (`composition_sweep`), and their **grid** (`sweep_grid`, the banked
`docs/figures/steel-sweep.png`), with tempering kept to its own **martensite-only** `temper_sweep`
(honouring the deferred mixed-structure-temper scope). Three design crux-points (advisor): (1) a
`STEELS` registry of **real** compositions so the surface avoids the `ccurve_for_steel(0.80, Mn=0)`
"leaner-hypothetical" trap and **one `Steel.minor()` dict threads into both the kinetics
(hardenability `τ`-shift) and the hardness (Maynier minor-alloy term)** — the cross-consistency
the harness tests assert (the near-tautological "exact re-composition" leg has teeth only there);
(2) the **0-D discrimination lesson** — in the lumped cooler the path is composition-independent,
so steels **share the martensitic fast end and pearlitic slow end and diverge only in the middle**,
hence the alloy-hardenability trend is read at an *intermediate* medium (oil), never the saturated
ends; (3) trends asserted **in HV** (defined everywhere; HRC is `nan` on soft tails) and Biot
carried per-`Outcome` with `warn_biot=False` (no per-node warning spew). 17 new tests.

**§9 slice 1 — `steel.ipynb` (teaching notebook) built ✓** (2026-06-08) — `projects/steel/steel.ipynb`
+ `tests/test_steel_notebook.py` + the `[notebook]` extra. The *education* artifact (target #1): a
guided narrative — Fe-C endpoint → TTT C-curve → four-curves anchor → composition × cooling-rate
hardenability → tempering — with **ipywidgets** sliders (%C, grade, quench medium, section size,
temper T/t) re-running the `sweep`/`properties`/`fe_c` harness live. It is a **thin skin** (ADR
0002): each *compute* cell calls the validated harness **directly** (one static figure per section,
executed-and-embedded so the `.ipynb` reads on GitHub without a kernel), with `interact` layered on
top as sugar. **Crux (advisor):** `ipywidgets.interact` runs its callback inside an `Output` that
**captures** exceptions, so a broken call inside an interact callback never reaches `nbclient` — the
load-bearing compute therefore lives in *plain* cells (verified empirically: a `raise` in a direct
cell fails the test, the same `raise` in an interact callback does not). The test executes the
notebook **in a fresh subprocess** (process-isolation dodges a Windows pyzmq/asyncio Proactor-loop
deadlock that a pre-existing in-process event loop can trigger; `subprocess.run(timeout=…)` wall-clocks
a hang into a fast failure instead of wedging the suite) and asserts no cell errors — gated on the
`[notebook]` stack **and a registered kernelspec** (so a clean/headless checkout *skips*, never
errors). The `%C` slider drives only the Fe-C *equilibrium* cell; cooling/hardness/temper use the
`STEELS` grade dropdown, dodging the documented `Mn = 0` "leaner-hypothetical" trap. 1 new test
(execution smoke-test, not a physics check); full suite **235 green** (226 without the optional
pycalphad/viz/notebook stack).

**Next:** Steel's planned phases (1–4) are complete and the §9 surface is **2/3 done** (`sweep.py` ✓,
`steel.ipynb` ✓ slice 1; **`app.py` Streamlit = slice 2**, next). The *available, not-required* **D_I**
cross-check is still open; after slice 2 the program's build order (ARCHITECTURE.md §4) advances to
**Microchip**, which first **reuses the frozen `engines/diffusion` spine** (dopant profiles = the
carbon-diffusion code).
