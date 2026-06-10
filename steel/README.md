# `steel` — the steel production simulator

*Cooling curve in, microstructure out.* The program's flagship and the project
that **builds & freezes the diffusion/heat spine** (`engines/diffusion`) the other
sims inherit. Full plan: [`docs/plans/steel-production.md`](../../docs/plans/steel-production.md).

## Load pointer (per-session working set, ARCHITECTURE.md §11)

- **To work on the equilibrium core (Phase 1b):** `fe_c.py` + its `tests/`. To
  *use* it from another module, the module docstring of `fe_c.py` is the page.
- **To work on the kinetics (Phase 1c):** `kinetics.py` + `pathint.py` +
  `cooling.py` and their `tests/`; each module docstring is its contract. They
  consume `fe_c` (the A₁ driving force) and produce phase-fraction dicts.
- **To work on Jominy (Phase 2a):** `jominy.py` + `test_jominy.py`; it loads the
  frozen `engines/diffusion/CONTRACT.md` (heat mode) and reuses `cooling.py`
  constants + `pathint.py`. The module docstring is its contract.
- **To work on hardenability (Phase 2b):** `kinetics.py`'s `hardenability_factor` +
  `ccurve_for_steel` and `tests/test_hardenability.py`. Composition → a multiplicative
  `τ`-factor on the `CCurve`; `ccurve_for_steel(C, Mn, …)` is the entry point for a
  named steel (bundles A₁, Andrews Mₛ, and the shift).
- **To work on the hardness map (Phase 2c):** `properties.py` + `tests/test_properties.py`
  (the map) and `demo_jominy.py` + `tests/test_demo_jominy.py` (the Jominy artifact). It
  consumes `pathint`'s fractions dict + carbon → HV (rule of mixtures) → HRC. The module
  docstring is its contract.
- **To work on the full property model (Phase 3a):** `properties.py` (the Maynier graft —
  `MAYNIER_ALLOY`/`MAYNIER_VR_SLOPE` + the optional `comp`/`Vr` args on every constituent),
  `cooling.py`'s `cooling_rate_through`/`CoolingPath.cooling_rate` (the `Vr` metric), and
  `demo_four_curves.py` (`compute_hardness`, rewired onto the real model). Tests:
  `tests/test_properties.py`'s Phase-3a section + `tests/test_demo_four_curves.py`.
- **To work on tempering + strength/toughness (Phase 3b):** `properties.py`'s section 5
  (`hollomon_jaffe_parameter` / `tempered_martensite_HV` / `tensile_strength_MPa` /
  `toughness_index`) + `tests/test_properties.py`'s Phase-3b section. Additive on the
  as-quenched model — tempers a martensitic structure between two anchored endpoints (3a
  martensite + the FP floor); the frozen 2c/3a benchmarks are untouched.
- **To work on carburizing (Phase 3c):** `carburize.py` + `tests/test_carburize.py`
  (the mass-mode triad) and `demo_carburize.py` + `tests/test_demo_carburize.py` (the
  gear-tooth artifact). It loads the frozen `engines/diffusion/CONTRACT.md` (**mass mode**:
  Dirichlet surface / Neumann core) for the erfc carbon profile, then reuses
  `kinetics`/`pathint`/`properties` for the gradient. The module docstring is its contract.
- **To use the diffusion/heat spine:** load `engines/diffusion/CONTRACT.md` only —
  the frozen one-pager. You never need the engine's internals.
- **To work on CALPHAD equilibrium (Phase 4):** `calphad_backend.py` (the optional
  pycalphad wrapper) + `calphad_reference.py` (the frozen table) + `tests/test_calphad.py`
  (committed-vs-live) and `demo_calphad.py` + `tests/test_demo_calphad.py` (the artifact).
  Needs the `[calphad]` extra (+ a steel TDB via `download_mc_fe()` for the multicomponent
  half); the committed tests run without it. The module docstring is its contract.
- **To work on the experimentation surface (`sweep.py`):** `sweep.py` + `tests/test_sweep.py`
  (the harness) and `demo_sweep.py` + `tests/test_demo_sweep.py` (the artifact). It is **pure
  re-composition** of the validated chain (`ccurve_for_steel` → `cooling` → `pathint` →
  `properties`) — no new physics — so its tests check *harness* correctness (cross-consistency,
  monotone trends, conservation passthrough), not new triad legs. The module docstring is its
  contract; `sweep.STEELS` ships the real compositions the surface defaults to.
- **To work on the teaching notebook (§9 slice 1):** `steel.ipynb` + `tests/test_steel_notebook.py`.
  A *thin skin* on `sweep`/`properties`/`fe_c` — each compute cell calls the harness **directly**
  (a static figure per section, embedded in the committed `.ipynb`), with `ipywidgets.interact` as
  sugar on top; the test executes it headless (`nbclient`) and asserts no cell errors (gated on the
  `[notebook]` extra **and** a registered kernelspec — a clean checkout skips). Needs
  `pip install -e .[viz,notebook]`. **Why the direct cells, not interact callbacks:** `interact`
  captures exceptions in an `Output` widget, so a break in an interact callback never reaches the
  test — the validated calls must live in plain cells (verified by deliberate break).
- **To work on the Streamlit app (§9 slice 2):** `app.py` + `tests/test_app.py`. A *thin skin*
  on `sweep` in three layers: **compute helpers** (pure `sweep` re-composition, streamlit/
  matplotlib-free → unit-tested **always-green**), **figure builders** (lazy-import wrappers over
  `plots.py`'s `four_curves_figure`/`sweep_comparison_figure`), and **`main()`** (the *only* place
  `import streamlit` lives; not unit-tested — ADR 0002). Two non-obvious points: (1) the module
  bootstraps the repo root onto `sys.path` and imports **absolutely**, because `streamlit run
  app.py` runs the file as a top-level script (no package parent, `steel/` — not repo root
  — on the path) where relative imports fail; verify with `python steel/app.py` (it must
  reach `import streamlit` inside `main()` and die only there). (2) `main()` is kept paper-thin so
  only `st.*` calls can raise — every value is computed/formatted in a tested helper. Needs
  `pip install -e .[viz,app]`. The temper view uses streamlit-native `st.line_chart`, one chart per
  quantity (HV/HRC/UTS/toughness live on different scales).
- **To work on grain growth (Phase 5a):** `grain.py` + `tests/test_grain.py`. The grain-size axis —
  austenite grain growth `Dᵐ−D₀ᵐ=K₀·exp(−Q/RT)·t` + ASTM E112 `G↔d`; **orthogonal** to the hardness
  chain (no engine touch, no frozen benchmark moved). Its kinetics are pinned to a cited S960MC
  study (`Q` cited, `m/D₀/K₀` calibrated to the isothermal table); the benchmark with teeth is a
  cross-temperature **holdout**. Units **µm/hours/K** (the registered trap — 5b's Pickering laws use
  `d` in mm). The Hall–Petch yield + Cottrell–Petch DBTT (5b) and the coupling/figure (5c) build on
  it; plan §12.
- **To work on the competing-reaction kinetics (Phase 6a/6b):** `kinetics.py` §§5–6
  (`FerriteReaction` — wired into `pathint` sequentially; `BainiteReaction` — deliberately
  standalone, the §6 negative result) + `tests/test_ferrite.py` / `test_bainite.py` and
  `demo_bainite.py`. The kinetics module docstring sections are the contract; plan §13 holds
  the full diagnosis-and-descope story.
- **To work on austempering (Phase 6d):** `austemper.py` + `tests/test_austemper.py` (the
  atlas anchor table + the `austemper()` hold recipe) and `demo_austemper.py` +
  `tests/test_demo_austemper.py` (the three-panel artifact). It consumes the 6b
  `BainiteReaction` unchanged (per-steel `scale` via `dataclasses.replace`, derived at import
  from one cited US-Steel-1951-atlas point each), `kinetics`' Mₛ/KM, and `properties`'
  hardness blend. The module docstring is its contract — including the named edges (claims
  stop at the 50 % line; bainite hardness = the carbon-only placeholder, now load-bearing).
- **To work on the D_I cross-check (Phase 6c):** `ideal_diameter.py` + `tests/test_ideal_diameter.py`
  (the validation leg) and `demo_ideal_diameter.py` + `tests/test_demo_ideal_diameter.py` (the
  two-panel artifact). **Pure re-composition** of the validated Jominy chain (`solve_thermal_field` →
  `ccurve_for_steel` → `jominy_hardness`) + two cited lookup tables (EMJ p.29 J→`D_c` water-quench
  conversion; SAE J406/Hodge–Orehoski 50 %M hardness) + cited measured H-bands (SAE J1268 / EMJ) — no new physics, no
  engine touch, `pathint`/`kinetics` byte-identical. The module docstring is its contract (the teeth
  caveat: benchmark MEASURED, not Grossmann; the circularity roles anchor/teeth/edge).
- **To work on inverse design (Phase 7):** `design.py` + `tests/test_design.py` (the harness) and
  `demo_design.py` + `tests/test_demo_design.py` (the artifact), plus the §7 surfaces in `app.py`
  and `steel.ipynb`. *Target a hardness, get a recipe* — **pure inversion** of the validated
  forward chain (`sweep.evaluate` + `properties.tempered_martensite_HV`): no new physics, no engine
  touch, `pathint`/`kinetics` byte-identical. Structure = **outer grade×quench enumeration × inner
  temper root-find** (bisection over the monotone public temper curve). Like `sweep.py` it has **no
  triad of its own** — tests are *harness correctness*, led by the *no-recipe-re-evaluates-out-of-band*
  invariant. The module docstring is its contract (hardness-only v1; the cost sort is labelled
  convenience, not validation; `diameter` is 0-D bulk hardness, not a radial profile). Plan §14.
- The Fe-C boundaries in `fe_c.py` are **parametrized approximations** (linear between
  pinned invariant points). Phase 4 (`calphad_backend.py`) computes them from real
  thermodynamics instead — `CalphadBackend().phase_fractions(C0, T)` is a drop-in for
  `fe_c.phase_fractions` — and quantifies the parametrization's error.
- **Viz is opt-in** (ADR 0002): `plots.py`/demos need `pip install -e .[viz]`
  (matplotlib); the compute core and the test suite stay headless.

## Status & module map

| Phase | File | What | Status |
|---|---|---|---|
| 1a | `engines/diffusion/` | conservative 1-D parabolic (diffusion/heat) solver — the spine | **frozen ✓** (2026-06-08) |
| 1b | `fe_c.py` | metastable Fe–Fe₃C boundaries + lever rule → equilibrium phase fractions & constituents | **built ✓** |
| 1c | `kinetics.py` | Avrami/TTT, Scheil additivity/CCT, Koistinen–Marburger, Andrews `M_s` | **built ✓** |
| 1c | `pathint.py` | steel-local path-integrator (additivity ∫dt/τ + Avrami-along-path + 0-D cooler) | **built ✓** |
| 1c | `cooling.py` | cooling-path presets (`h` for furnace/air/oil/water) + Biot validity flag | **built ✓** |
| 1 | `plots.py`, `demo_four_curves.py` | the anchor artifact (four rates → pearlite→martensite); needs `[viz]` extra | **built ✓** |
| 1 | `sweep.py`, `demo_sweep.py`, `plots.py` | experimentation surface — the headless sweep/what-if harness (composition × cooling rate) + the comparison artifact | **built ✓** (2026-06-08) |
| 1 | `steel.ipynb` | interactive **teaching notebook** (narrative + ipywidgets sliders) layered on the sweep harness — §9 **slice 1** | **built ✓** (2026-06-08) |
| 1 | `app.py` | interactive **Streamlit** what-if app on the same harness — §9 **slice 2** | **built ✓** (2026-06-09) |
| 2a | `jominy.py` | end-quench **spatial thermal** model (fin equation; frozen heat solver + lateral loss) → cooling-rate-vs-distance | **built ✓** (2026-06-08) |
| 2b | `kinetics.py` (`hardenability_factor`, `ccurve_for_steel`) | alloy **hardenability** = a Grossmann-potency multiplicative C-curve time-shift (Mn/Cr/Mo → right; default identity) | **built ✓** (2026-06-08) |
| 2c | `properties.py`, `demo_jominy.py` | microstructure→hardness map (rule of mixtures) → the Jominy **hardness**-vs-distance artifact; 1045/4140 hardness benchmark | **built ✓** (2026-06-08) |
| 3a | `properties.py` (extend), `demo_four_curves.py` (rewire), `cooling.py` | Maynier **minor-alloy + cooling-rate** terms grafted on the 2c carbon baselines; four-curves demo on the **real** hardness model (placeholders retired) | **built ✓** (2026-06-08) |
| 3b | `properties.py` (extend) | tempering (Hollomon–Jaffe master curve) + ISO-18265 strength + rough strength/toughness trade-off | **built ✓** (2026-06-08) |
| 3c | `carburize.py`, `demo_carburize.py` | carburizing case-hardening: frozen engine in **mass mode** (erfc carbon profile) → microstructure + hardness gradient (gear-tooth artifact) | **built ✓** (2026-06-08) |
| 4 | `calphad_backend.py`, `calphad_reference.py`, `demo_calphad.py` | CALPHAD-backed equilibrium (optional pycalphad): boundaries *emerge* from Gibbs-energy minimisation + multicomponent low-alloy steels; frozen reference table keeps the triad green pycalphad-free | **built ✓** (2026-06-08) |
| 5a | `grain.py` | **post-v1** — austenite grain growth `Dᵐ−D₀ᵐ=K₀·exp(−Q/RT)·t` + ASTM E112 `G↔d`; the grain-size axis Hall–Petch/DBTT (5b/5c) build on. Orthogonal to the hardness model | **built ✓** (2026-06-09) |
| 5b | `grain.py` (extend) | the **Pickering pair** — Hall–Petch **yield** + Cottrell–Petch **DBTT**, same form / opposite grain-size signs (refine → stronger *and* tougher) | **built ✓** (2026-06-09) |
| 5c | `grain.py` (extend), `plots.grain_figure`, `demo_grain.py` | **coupling** (austenitize → PAGS → ferrite grain → yield + DBTT) + the banked co-benefit figure; `yield ≤ UTS` consistency check | **built ✓** (2026-06-09) |
| 5 | `steel.ipynb` §5, `app.py` §5, `plots.grain_interactive_figure` | Phase 5 **surfaced in the §9 interactive twins** — slider-driven austenitize → grain → yield + DBTT, the over-austenitizing penalty (DBTT crossing room temperature); replaces the schematic-cartoon stand-in | **built ✓** (2026-06-09) |
| 6a | `kinetics.py` §5 (extend), `pathint.py` | the **proeutectoid-ferrite bay** — Li/Kirkaldy–Venugopalan ferrite reaction (ceiling A₃) run *before* the pearlite curve; the corrected "A₁-not-A₃" diagnosis; 1045 knee shallows, 4140 stays deep by cited Cr/Mo (plan §13) | **built ✓** (2026-06-09) |
| 6b | `kinetics.py` §6 (extend), `demo_bainite.py` | the **cited bainite reaction** (Steven–Haynes `Bs`, ΔT¹, `BC`) + the bay's *mechanism* (BC Cr/Mo ≪ FC Cr/Mo) — **descoped as a proven negative**: wiring it into `pathint` would regress the 8620 band, so it stays standalone (plan §13) | **built ✓** (2026-06-09, descoped) |
| 6d | `austemper.py`, `demo_austemper.py`, `steel.ipynb` §6, `app.py` §6 | **austempering** — the isothermal bainite hold, the 6b reaction's valid home: per-steel anchors to the US Steel 1951 atlas (scales derived at import), holdout-proven 50 %-line, KM on the remainder, the minimum-full-transform-hold exercise | **built ✓** (2026-06-10) |
| 6c | `ideal_diameter.py`, `demo_ideal_diameter.py` | the **critical-diameter (D_c) / measured-Jominy cross-check** — compute the critical diameter *from* the model (`fM=0.5` → EMJ p.29 water-quench conversion) vs **measured** H-bands (SAE J1268 / EMJ; *not* Grossmann-computed): the hardenability **ranking is correct**, 4340 **under-predicted** (Ni potency), 4140 in-band by construction (plan §13) | **built ✓** (2026-06-10) |
| 7 | `design.py`, `demo_design.py`, `plots.design_figure`, `steel.ipynb` §7, `app.py` §7 | **post-v1 — inverse design**: *name a hardness, get the recipe* — outer grade×quench enumeration × inner temper root-find over the validated forward chain; feasible set cheapest-first, infeasible first-class, Biot honesty. No new physics (plan §14) | **built ✓** (2026-06-10) |
| viz | `plots.grain_voronoi_swatch` / `grain_morphology_figure`, `demo_grain_morphology.py`, `app.py` §5 | **grain-morphology swatch** — size-accurate Voronoi *illustration* of the scalar grain size `d` (grains/area ∝ ASTM `N_A = 1/d²`; shapes decorative, scale bar). Reach not physics (ADR 0002); **alongside** `microstructure_schematic`, not replacing it (plan §12) | **built ✓** (2026-06-10) |

## `fe_c.py` — metastable Fe–Fe₃C equilibrium (Phase 1b)

The thermodynamic endpoint: which phases coexist at a given (carbon, temperature),
and in what mass proportion — the equilibrium the Phase-1c kinetics drive toward.

**Two readings** (the subtlety this module exists to teach):

- `phase_fractions(C0, T)` → the raw **phase** fractions as a plain dict
  `{"ferrite", "austenite", "cementite"}` (the inter-module currency, plan §5).
- `equilibrium_constituents(C0)` → the slow-cooled **microstructural constituents**
  (`Constituents`): *pro-eutectoid* ferrite/cementite + *pearlite*, plus the total
  ferrite/cementite once pearlite is resolved into its lamellae.

```python
from steel.fe_c import phase_fractions, equilibrium_constituents

phase_fractions(0.45, 727)        # 1045 just above A₁ → ~42% ferrite, ~58% austenite
equilibrium_constituents(0.45)    # → 42% pro-eutectoid ferrite + 58% pearlite (the showcase)
equilibrium_constituents(0.80)    # 1080: ~0.7% pro-eutectoid cementite — near-degenerate
```

Boundary helpers (`A1`, `A3`, `Acm`, the composition inverses, `ferrite_C`) and the
pinned invariant-point constants are exported for plotting the diagram and for the
kinetics layer (undercooling below `A1`/`A3` is the driving force).

### Design notes (the non-obvious choices)

- **Mass fractions, not volume/mole.** The lever rule is a carbon mass balance on
  wt%, so every fraction is a mass fraction — fixed here because Phase-3 properties
  depend on it.
- **Linear boundaries between pinned invariant points.** Makes the invariant points
  (eutectoid 0.76 %/727 °C, γ-max 2.11 %/1147 °C, pure-iron A₃ 912 °C) *exact by
  construction* — exactly what the validation triad's "exact at a chosen (T,%C)" leg
  needs. The ferrite solvus is held at 0.022 % below A₁ (a documented sub-percent
  simplification).
- **727 °C is a real discontinuity** (the eutectoid reaction is isothermal). By
  convention `T = 727` returns the **austenite-bearing** side, so the austenite
  fraction there equals the pearlite it becomes — the consistency the tests pin.
- **°C, not kelvin.** The diagram convention; the kinetics layer converts at its
  Arrhenius/Andrews boundary.

## Phase 1c — transformation kinetics (`kinetics.py` + `pathint.py` + `cooling.py`)

*How fast, and what if it never arrives.* Where `fe_c` gives the equilibrium
endpoint, 1c gives the **path-dependent** outcome: the undercooling below `fe_c`'s
A₁ is the driving force the kinetics consume.

- `kinetics.py` — the laws. **Avrami** `X(t)=1−exp(−(t/τ)ⁿ)` (+ `fit_avrami`, the
  round-trip that recovers `(n,τ)`); the **TTT C-curve** `CCurve.tau(T)` built as
  *driving force × mobility* (`exp(Q/RT)·exp(K_N/(T·ΔT²))`, abs `T` in kelvin) so
  the **nose** emerges from their product; **Andrews** `andrews_Ms(C,Mn,…)`;
  **Koistinen–Marburger** `koistinen_marburger(T,Ms)`.
- `pathint.py` — the integration. A 0-D **Newton cooler** + **Scheil additivity**
  `∫dt/τ=1` (→ CCT start; reduces to the isothermal τ under a hold) +
  fictitious-time **Avrami-along-path**. `transform_along_path(t,T,ccurve)` →
  `TransformResult` (pearlite/bainite/martensite/retained γ). KM acts on the
  **retained** austenite `(1−X_diff)`, so the four fractions sum to 1 by construction.
- `cooling.py` — `h` presets (furnace/air/oil/water) → lumped `τ_th`, each path
  carrying its **Biot number** (`Bi≥0.1` ⇒ the 0-D model is stretched and warns —
  the honest hand-off to the Phase-2 spatial solve).

```python
from steel.kinetics import CCurve, andrews_Ms
from steel import cooling, pathint
cc = CCurve(Ms=andrews_Ms(0.8))                 # 1080: A₁=727, Ms≈201, nose≈550 °C/1 s
p = cooling.cooling_path("water", T0=850)        # a 0-D cooling history (t, T)
r = pathint.transform_along_path(p.t, p.T, cc)   # → mostly martensite + retained γ
```

### The anchor demo (`demo_four_curves.py`)

```powershell
pip install -e .[viz]                  # one-time: matplotlib for the figure
python -m steel.demo_four_curves
```

One 1080 specimen, four quench rates → the figure
[`docs/figures/steel-four-curves.png`](../../docs/figures/steel-four-curves.png):
cooling paths drawn *across* the C-curve (the mechanism) beside the resulting
microstructures (the consequence). **Honest result:** four rates give **three**
distinct phase constitutions — furnace & air both pearlite (differing only in
formation temperature → coarseness), oil a bainite-dominant *mixture* (plain 1080
resists clean continuous-cooling bainite; austempering would be needed), water
martensite. **Phase 3a** put **real** `properties.py` hardness on the bars (the old
indicative placeholders are retired): ~29–30 HRC pearlite → 52 HRC bainite-mixture →
~62 HRC martensite, a ~30 HRC span. The furnace-vs-air pearlite difference is only
~5 HV — the honest size of the plain-carbon cooling-rate term (the coarseness is the
kinetic `formation_T`, not a big hardness gap).

## Phase 2a — Jominy spatial thermal model (`jominy.py`)

The first *spatial* reuse of the frozen heat solver. The standard end-quench bar
(ASTM A255) is modelled as the **transient fin equation** — axial conduction *plus*
lateral convection to air — because a timescale check (`√(αt) ≈ 8 mm at 10 s`) shows
a bar with adiabatic sides cannot cool its far half on the transformation timescale;
the lateral air loss is what produces the real Jominy gradient. A strong Robin
(water jet) cools the quenched end; the tip is insulated.

The frozen engine solves pure conduction, so the lateral sink (which depends on the
live `T`, not expressible as the engine's `S(x,t)` source) is composed *around* it by
**Strang operator splitting**: an analytic-exponential lateral half-step (exact,
unconditionally stable) on either side of one frozen implicit conduction step — the
engine is never modified (the ADR-0001 array seam working as intended).

```python
from steel.jominy import JominyBar, solve_thermal_field, jominy_distances
f = solve_thermal_field(JominyBar(), T0=850.0)          # T(x,t) over the bar
cr = f.cooling_rate_at(jominy_distances(16), T_ref=700) # K/s vs distance (the Jominy metric)
t, T = f.history(0)                                      # the (t,T) path at a depth → pathint (2b)
```

**Validated** (`test_jominy.py`): the thermally-thin limit (Bi < 0.1) reduces exactly
to `cooling.py`'s 0-D Newton cooling (`τ_lat = ρc_p·(d/4)/h` — the same `L_c`); a
both-ends Robin slab pins the engine's `h_eng = h_phys/(ρc_p)` unit convention; and
energy balances over the bar's *two* sinks (`Δ∫T dx = end-flux + lateral-loss`) to
machine precision. The **thermal benchmark**: the cooling-rate-vs-distance curve
tracks the published Jominy distance↔rate equivalence at 700 °C (mean ratio ~0.92,
mid-range within the ~±25 % literature spread) and is **resolution-converged**
(< 1.2 % under 2× cells × 2× time) — fin physics, not a discretization artifact.
Freezing this thermal curve *before* the Phase-2b hardenability calibration is
deliberate: the mid-range knee (~5–25 mm) is where the cooling rate and the alloy
τ-shift both act, so a validated thermal curve stops the τ-shift from absorbing
thermal error. **Scope:** 2a banks the thermal spine and its analytical +
conservation + thermal-benchmark legs; the hardenability alloy C-curve shift, the
microstructure→hardness map, and the 1045/4140 *hardness* benchmark are Phase 2b/2c.

## Phase 2b — alloy hardenability (the C-curve shift)

Mn, Cr, Mo make a steel *hardenable*: they slide the whole TTT C-curve to longer times
(right), so martensite survives a slower quench — and therefore reaches deeper into a
section. `kinetics.hardenability_factor(Mn, Ni, Cr, Mo, Si)` returns the multiplicative
time-shift `M` (`τ → M·τ`, shape- and nose-temperature-preserving); `ccurve_for_steel(C,
Mn, …)` bundles it with the A₁ ceiling and Andrews Mₛ into a ready `CCurve` for a named steel.

```python
from steel.kinetics import ccurve_for_steel
cc_1045 = ccurve_for_steel(0.45, Mn=0.75, Si=0.22)                   # shallow-hardening, M ≈ 1
cc_4140 = ccurve_for_steel(0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)  # deep-hardening,   M ≈ 8
```

`M` is the **Grossmann** alloy multiplying-factor product taken *relative to the 1080
reference* (≈ 0.7 % Mn) and raised to one calibrated scale — Grossmann for the *relative*
element potencies (Cr, Mo ≫ Ni), the scale set so 4140 lands ≈ 8× right (its deep-hardening
band). Grossmann's own magnitude lives in ideal-critical-*diameter* space, which already
convolves the thermal physics the fin solver models — so using it for *scale* would
double-count the mid-range knee Phase 2a froze its thermal curve to protect; the magnitude
is anchored to the pure-kinetic **TTT nose** instead. **Default identity:** a bare `CCurve`
keeps `tau_factor = 1.0`, so the four-curves demo is byte-identical; the factory expects
*real* compositions (for the demo's idealized carbon-only 1080, use the direct constructor).

**Validated** (`test_hardenability.py`): the shift is a clean multiplicative scaling (nose
*temperature* fixed, time × `M`); 4140 calibrated to band while **1045 falls out ≈ identity
— a non-circular prediction**; and — the real check on the mechanism — fed the *same* Jominy
bar histories, 4140 stays martensitic far deeper (≈ 0.6 at 25 mm) than 1045 (gone by ~13 mm)
while both share the quenched end. **Scope:** the quenched-end hardness *number* and the
Jominy hardness-vs-distance artifact + 1045/4140 hardness benchmark are Phase 2c; v1 uses one
factor for pearlite+bainite (no separate bainite bay) and holds `T_eq` at the eutectoid A₁.

## Phase 2c — microstructure → hardness + the Jominy artifact (`properties.py`, `demo_jominy.py`)

The property model (a **minimal seed**; Phase 3 extends it) that closes the spatial
chain. Hardness is a **rule of mixtures over the constituents** — `HV = Σ fᵢ·HVᵢ(C)`,
exactly the structure of the **Maynier (1978)** Jominy-prediction method — computed in
**Vickers** (linear, additive, defined for soft material) and converted to **HRC** only at
the reporting boundary via an **ASTM E140** table, valid ~20–65 HRC (below 20 HRC Rockwell-C
is undefined → `nan`, the honest output for a soft pearlitic tail).

```python
from steel.jominy import solve_thermal_field, JominyBar, jominy_distances
from steel.kinetics import ccurve_for_steel
from steel import properties as prop
f  = solve_thermal_field(JominyBar(), T0=850.0)                       # one shared thermal field
cc = ccurve_for_steel(0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)       # 4140's C-curve (its M-shift)
h  = prop.jominy_hardness(f, cc, 0.40, jominy_distances(16))         # → HV, HRC, fM vs distance
```

The discipline that keeps this *validating*, not curve-fitting: each constituent hardness is
anchored to an **independent** dataset — martensite to the as-quenched-martensite-vs-%C curve
(Hodge–Orehoski/Krauss), ferrite-pearlite to normalized plain-carbon hardness (ASM) — so the
Jominy curve is a genuine cross-check. v1 drops Maynier's cooling-rate and minor-alloy terms
(carbon-only constituents — the Phase-3 extension).

**Validated** (`test_properties.py`) — the **third leg of the Phase-2 triad** (the analytical
+ conservation legs were banked thermally in 2a):
- *The map in isolation.* HV→HRC pinned to E140 pairs; martensite hardness on the as-quenched
  curve across **0.2–0.8 %C** (the slope, not one point — both benchmark steels are ~0.4 %C);
  rule-of-mixtures exact at a pure phase, bounded, monotone in martensite fraction; and the
  **50 %-martensite hardness criterion** (Hodge–Orehoski, ~43 HRC at 0.4 %C) — a *mixture*
  anchor independent of both endpoints, read at fM = 0.5 *regardless of where it falls on a
  bar*, so it validates the map in the transition decoupled from the kinetics.
- *The benchmark / consequence.* 1045 and 4140 (both ~0.4 %C) **share the quenched-end
  hardness** (~55–57 HRC — full martensite, so the hardness model alone speaks, the 2b shift
  silent) and then **diverge with distance**. Precisely: **4140 is a quantitative match** to
  its published deep-hardening plateau (~55 HRC at ½ in, ~49 at 1 in); **1045's endpoints and
  the dramatic divergence match**, with its *knee ~2–3 mm deeper* than a lean published 1040 —
  a *verified*-upstream artifact (re-running 1045 at `T_eq ≈ A₃ = 780` moves the knee shallower)
  of the documented Phase-2b A₁-not-A₃ simplification, **not** a hardness-map error (the linear
  rule cannot mismap the transition without breaking the validated quenched-end anchor).

### The Jominy hardness artifact (`demo_jominy.py`)

```powershell
pip install -e .[viz]
python -m steel.demo_jominy
```

One ASTM A255 bar, two ~0.4 %C steels → the figure
[`docs/figures/steel-jominy-hardness.png`](../../docs/figures/steel-jominy-hardness.png):
hardness vs distance for plain-carbon 1045 and low-alloy 4140 overlaid on representative
published points — they share the quenched end and diverge with depth (4140's deep plateau
vs 1045's soft, off-HRC-scale tail).

**Follow-ups:** (1) ~~`plots.py`'s `INDICATIVE_HARDNESS` placeholders drive the four-curves
figure~~ — **done (Phase 3a):** the placeholders are retired and the four-curves demo now shows
the real `properties.py` hardness. (2) **D_I cross-check** (compute the critical diameter *from* the
finished model vs measured data) — **done (Phase 6c):** `ideal_diameter.py` reads the critical
diameter `D_c` from the model's `fM=0.5` Jominy distance (EMJ p.29 water-quench conversion) and
compares it to **measured** H-bands (not Grossmann-computed — that would be circular); the
hardenability ranking comes out correct, 4340 is under-predicted (Ni potency), 4140 lands in-band by
construction. See "Phase 6c" below + plan §13.

## Phase 3a — the full property model (Maynier minor-alloy + cooling-rate terms)

2c's constituent hardnesses were the moderate-cooling-rate, **carbon-only** limit. Phase 3a
adds the two terms Maynier's full method carries — a **minor-alloy** term (Si/Mn/Ni/Cr/Mo
raise each constituent) and a **cooling-rate** term (faster cooling → finer product → harder,
via `Vr`, the cooling rate at 700 °C). It is an honest **graft**, not a switch to "pure
Maynier": we keep 2c's *independently-anchored* carbon baselines and bolt on only Maynier's
*non-carbon* deltas (the cooling-rate one **reference-zeroed** about a normalizing rate). The
new `comp`/`Vr` args are **optional and default to the 2c carbon-only value byte-for-byte**, so
the frozen 2c benchmark is unchanged — the new terms fire only where a caller passes them.

```python
from steel import properties as prop
prop.vickers_martensite(0.40)                              # 2c value (carbon-only)
prop.vickers_martensite(0.40, comp={"Mn": 0.9, "Cr": 1.0, "Si": 0.25})   # + Maynier alloy delta
prop.vickers_ferrite_pearlite(0.80, Vr=80000.0)           # + cooling-rate term (°C/h at 700 °C)
```

What it buys (all validated in `test_properties.py`'s Phase-3a section, anchored to the cited
Maynier coefficients): the **minor-alloy term on martensite closes the gap 2c flagged** — 4140's
quenched end came out ~1 HRC below 1045's; with Cr/Mn it lands ~equal, matching published. The
**cooling-rate term on ferrite-pearlite** is honestly *small* for plain carbon (~10 HV/decade →
furnace-vs-air pearlite differ ~5 HV). Deliberate omissions: **martensite is kept
cooling-rate-independent** (protects the validated quenched-end anchor), and **bainite's terms
are deferred** (Maynier's bainite coefficients are too large to graft onto the placeholder
baseline — it would exceed martensite). The banked Jominy figure stays **carbon-only** on
purpose — it is a prior phase's deliverable (reworking it mid-3a is scope creep) and the
alloy-lifted 1045 tail sits right on the 240 HV / 20 HRC scale floor, so a demo assertion
there would be resolution-fragile (the gap-closing is validated in `test_properties` instead).

## Phase 3b — tempering (Hollomon–Jaffe) + the strength/toughness trade-off

Everything in 2c/3a is the **as-quenched** model. Phase 3b adds the step every real
quench-hardened part takes — **tempering** — and closes the loop to engineering
properties. The **Hollomon–Jaffe** parameter `P = T·(C_hj + log₁₀ t)` (T in kelvin,
t in hours) collapses tempering temperature and time into one number; tempered-martensite
hardness is a decreasing master curve `HV(P)` running between two **independently-anchored**
endpoints — the Phase-3a as-quenched martensite and the ferrite-pearlite/spheroidite floor.

```python
from steel import properties as prop
prop.tempered_martensite_HV(0.40, 400.0, 1.0)                       # plain 0.4%C, 1 h @ 400 °C → ~425 HV (~43 HRC)
prop.tempered_martensite_HV(0.40, 400.0, 1.0, comp={"Cr":1.0,"Mn":0.9,"Mo":0.2,"Si":0.25})  # 4140 → ~466 HV (resists)
prop.tensile_strength_MPa(425.0)                                    # ISO 18265: ~1370 MPa
prop.toughness_index(425.0)                                        # relative toughness ~0.44 (rises as you temper)
```

What is **validated** (asserted tightly) vs **calibrated** (flagged, loose) — the same
non-circularity discipline as 2c/2b:
- *Validated — the parameter's form.* The **time–temperature equivalence** (two `(T, t)`
  on the same `P` give the same hardness — *convention-independent*, so it holds for any
  carbon and any `C_hj`); the monotone softening in both `T` and `t`; and the bound between
  the two anchored endpoints (a sub-onset temper returns the as-quenched value exactly; a
  deep over-temper bottoms out on the floor). Threading `comp` through both endpoints makes
  an **alloy steel resist tempering softening as an emergent consequence** (4140 stays harder
  than plain 0.4 %C at every temper — it starts harder *and* floors higher).
- *Calibrated — the magnitude.* The value of `C_hj` (≈ 20, a **cited** low-alloy-steel
  constant, defaulted not fitted) and the two `P` breakpoints that set the softening size —
  the Phase-3b analogue of Phase-2b's `HARDENABILITY_SCALE`. Calibrated so ~0.4 %C martensite
  tempered 1 h follows the known response (high-50s HRC as-quenched → low-40s at 400 °C → ~25
  HRC at 600 °C, Grange/ASM charts); asserted only with **loose sanity bands**, not dressed
  as a validation.
- *Benchmark leg — a prediction.* Because the plain-carbon bands are self-consistency (the
  breakpoints were calibrated to them), the **independent** benchmark is **4140's 1 h tempering
  response** (~55 HRC @ 200 °C → ~45 @ 400 °C → ~33 @ 600 °C, ASM/Bhadeshia): calibrated only on
  plain-carbon breakpoints + the Maynier-anchored (3a) `comp` deltas through both endpoints, with
  *nothing* fit to 4140 tempering data — the inverse of Phase-2b's "calibrate 4140, 1045 falls out".

Strength is read from the published **ISO 18265 / ASTM A370** hardness→tensile-strength
conversion (an interpolated table like the E140 one, valid ~150–550 HV — it degrades above
~550 HV, i.e. untempered martensite, returning `nan` there honestly). Toughness is a
deliberately **rough, relative** direction opposite to hardness — *no Charpy-J is invented*,
because real impact toughness is steel/heat-specific and **non-monotone** through the
tempered-martensite (~260–370 °C) and temper-embrittlement (~375–575 °C, alloy) troughs (the
named scope ceiling). Tempering is **martensite-only** here (pearlite barely tempers; a mixed
traverse would temper per-constituent — deferred). No new figure: 3b is a `properties.py`
extension validated by the test triad.

## Phase 3c — carburizing case-hardening (`carburize.py`, `demo_carburize.py`)

The **mass-diffusion face of the spine**. Phase 2 reused the frozen `engines/diffusion`
in *heat* mode (the Jominy bar); 3c reunites the other face — the *same* sealed engine in
**mass mode**, diffusing carbon into the surface of a low-carbon part (≈ 8620, 0.2 %C core)
held at 925 °C in a 0.8 %C-potential atmosphere. Constant `D` + a Dirichlet surface give the
textbook **erfc** carbon profile; the position-dependent `%C` then feeds the *same*
`kinetics`/`pathint`/`properties` chain → a **case-hardened gradient**: a hard (~65 HRC)
martensite case over a tougher, softer (~48 HRC) core.

```python
from steel import carburize as cb
p  = cb.solve_carburize(C_surface=0.8, C_core=0.2, T_carburize=925.0, t_hours=8.0)  # erfc C(x)
p.case_depth(0.4)                       # effective case depth to 0.4 %C  (~0.66 mm)
tr = cb.carburized_traverse(p)          # 8620, oil quench → fractions + hardness vs depth
tr.HRC[0], tr.HRC[-1]                   # ~66 HRC case, ~48 HRC core
```

This is the **cleanest validation triad in the project**, because its two headline legs are
the frozen engine's *own* guarantees re-instantiated — no new calibration:

- *Analytical limit.* The numeric profile matches **erfc** in the interior, and the case
  depth scales **exactly** as `√(Dt)` (the self-similar variable `x/2√(Dt)`). The scaling is
  asserted *tightly*; the *absolute* case depth is asserted *loosely* — carbon potential and
  case-depth definition vary across sources, and the cited constant-`D` (vs the concentration-
  enhanced Tibbetts `D(C)`) under-predicts the absolute depth, a **named** scope limitation.
- *Conservation.* `Δ∫C dx` equals the integrated surface flux `Σ dt·flux(left)` to machine
  precision — the engine's exact backward-Euler flux identity (confirmed for the **Dirichlet**
  surface, the core being no-flux), plus the semi-infinite tie `Δ∫C dx = 2(Cs−C0)√(Dt/π)`.
- *Benchmark — genuine cross-checks.* The 50-HRC effective case depth (~1.4 mm at 925 °C/8 h)
  lands in the published rule-of-thumb band, and the surface hardness cross-checks the
  independently-anchored martensite curve (~65 HRC for ~0.8 %C). Both are cross-checks because
  `D0, Q` are **cited diffusion data** (not fit to case depth) and the martensite hardness is
  anchored to Hodge–Orehoski (not to carburizing).

**The retained-austenite fork (advisor).** Running the full kinetics to room temperature at the
high-carbon surface predicts substantial **retained austenite** (low surface `Ms`) — real
heavy-case physics, *and* where Andrews `Ms` / KM / the √C martensite curve are pushed past their
~0.8 %C anchor. So the **surface-hardness benchmark** is anchored to the martensite **potential**
(`tr.HV` — the case as designed, what a published spec represents), while the RA is reported as the
microstructure gradient (`tr.retained_austenite`) and an honest as-quenched curve (`tr.HV_as_quenched`,
which dips below the potential *only* near the surface) — **not** asserted against the published band.
This is the carbon-gradient story isolated: a **single** quench is applied at every depth, so the
case's hardness gradient is **carbon-driven** (the thin case is thermally near-uniform on the
transformation timescale) — the complement to the *cooling-rate*-driven gradients of 1c/2.

### The carburized gear-tooth artifact (`demo_carburize.py`)

```powershell
pip install -e .[viz]
python -m steel.demo_carburize
```

One carburized 8620 section → the figure
[`docs/figures/steel-carburize-gradient.png`](../../docs/figures/steel-carburize-gradient.png):
three panels sharing the depth axis — the carbon profile (numeric + erfc overlay + case-depth
marker), the microstructure gradient (martensite case, retained-γ rising into the surface), and
the hardness traverse (martensite potential over the as-quenched curve, with the published surface
band sitting honestly between them). **Scope named:** constant `D` (vs Tibbetts `D(C)`), Dirichlet
constant potential (vs a Robin finite-surface-reaction / boost-diffuse ramp), and the high-carbon
extrapolation. The **D_I cross-check** is now **built (Phase 6c)** — `ideal_diameter.py`, below.

## Phase 4 — CALPHAD-backed equilibrium (`calphad_backend.py`, `calphad_reference.py`, `demo_calphad.py`)

The **bounded deep end**. Where `fe_c` *draws* the Fe-C diagram as straight chords between
pinned invariant points, Phase 4 lets the boundaries **emerge** from a real Gibbs-energy
minimisation (**pycalphad**, *consumed not reimplemented*) — and reaches **multicomponent
low-alloy steels** `fe_c` cannot represent at all.

```powershell
pip install symengine==0.14.1; pip install "pycalphad>=0.11" --no-deps   # Py3.14: override the symengine pin
pip install xarray pint tinydb runtype pandas
python -c "from steel.calphad_backend import download_mc_fe; download_mc_fe()"  # ODbL steel DB → data/tdb/
python -m steel.demo_calphad
```

```python
from steel.calphad_backend import CalphadBackend, default_steel_database_path
be = CalphadBackend()                       # bundled Fe-C database
be.phase_fractions(0.40, 760.0)             # → {ferrite, austenite, cementite} — a drop-in for fe_c
be.eutectoid()                              # → (~726.6 °C, ~0.757 %C) — emerges, not pinned
steel = CalphadBackend(default_steel_database_path())          # multicomponent (mc_fe)
steel.alloy_transus({"C":0.40,"Cr":0.95,"Mn":0.875,"Mo":0.20,"Si":0.25})   # 4140 → (A1, A3)
```

**Optional, never-committed databases** (plan §6): the binary **Fe-C** (`cfe_broshe.tdb`) ships
*inside* installed pycalphad; the multicomponent **MatCalc steel** database (`mc_fe_v2.060.tdb`,
**ODbL 1.0** — openly licensed) is fetched to a gitignored `data/tdb/`. Two documented Python-3.14
shims (a `symengine<0.14` override and a one-line PEP-749 `Workspace.__init__` fix, never editing
site-packages) are *validated by the physical results*. `load_clean_database` keeps only the TDB
commands pycalphad's grammar parses and prunes broken phases; the active phase set is curated and
corrupted-not-absent phases are excluded.

**Option C** keeps the triad green without a committed `.tdb`: a **frozen reference table**
(`calphad_reference.REFERENCE`), generated from the exact functions the live test calls, lets the
**committed tests validate `fe_c` with no pycalphad/database** (clean-checkout green), while
`importorskip` **live tests** re-derive it and match by construction. **Validated** (`test_calphad.py`):
- *Analytical limit (loose — a wiring check).* The eutectoid (726.6 °C/0.757 %C) and γ-max
  (1148 °C/2.04 %C) **emerge** from the free energies near `fe_c`'s pinned values — but since `fe_c`
  pins them, agreeing there is necessary, not probative.
- *Conservation.* Recombining CALPHAD's phase amounts × per-phase compositions recovers the input
  carbon to **machine precision** (`Σ fᵢ·Cᵢ = C0`).
- *Benchmark — the leg with teeth.* `fe_c`'s **linear A₃ chord over-predicts** the CALPHAD curve by
  +15→+29 °C (worst ~29 °C at 0.3 %C) — the quantified parametrization error; and **4140**'s A₁/A₃
  (720.7/771.8 °C) brackets the independent **Andrews** Ae1/Ae3 (737/762 °C) within loose ±20 °C
  bands (no directional claim — they straddle 727 °C, and the alloy A₁ sits amid stable Cr-carbides).

The banked artifact [`docs/figures/steel-calphad.png`](../../docs/figures/steel-calphad.png) overlays
the linear-chord-vs-curved A₃ (left) and 4140's equilibrium phase fractions vs temperature — with a
**chromium carbide** `fe_c` has no key for (right).

## Experimentation surface (`sweep.py`, `demo_sweep.py`)

ARCHITECTURE.md §1 makes experimentation a core target and ties parameter sweeps to "the
cheapest verification"; `sweep.py` is the headless harness that delivers it — the foundation
the interactive surfaces (`steel.ipynb` ✓, `app.py` ✓) import. It is **pure
re-composition** of the already-validated chain — *no new physics, no new calibration* —
turning the §1 "cooling curve in, microstructure out" into a sweepable what-if over
**cooling rate** and **composition**.

```python
from steel import sweep
sweep.evaluate(sweep.STEELS["4140"], medium="oil")          # one what-if → an Outcome
sweep.cooling_rate_sweep(sweep.STEELS["1080"])              # one steel × four media (the cooling-rate axis)
sweep.composition_sweep(["1045", "4140"], medium="oil")    # steels at one medium (the composition axis)
sweep.sweep_grid(["1045", "1080", "4140"])                 # the composition × cooling-rate grid
sweep.temper_sweep(sweep.STEELS["4140"], t_hours=1.0)      # the martensite-only Q&T temper curve
```

Two design choices keep it honest:

- **Real compositions by default** (`sweep.STEELS`: 1045/1080/4140/8620, matching the grades
  used across the project) — so the surface avoids the documented `ccurve_for_steel(0.80, Mn=0)`
  "leaner hypothetical steel" trap, and one `Steel.minor()` dict threads into **both** the
  kinetics (the hardenability `τ`-shift) **and** the hardness (the Maynier minor-alloy term),
  self-consistently. 1080 is the kinetics' reference steel, so its shift is exactly identity.
- **The 0-D discrimination lesson, surfaced not hidden.** In the lumped cooler the cooling
  path depends on `h`/section, **not** composition — so a composition sweep at a fixed medium
  feeds every steel the *same* `(t, T)` path, and the alloy effect only speaks at an
  *intermediate* medium (oil): steels **share the martensitic fast end and pearlitic slow end,
  diverge in the middle**. Each `Outcome` also carries its Biot validity flag (a severe quench
  of a thick section exceeds the 0-D range → the cue for the Phase-2 spatial solve), and
  hardness is compared in **HV** (defined everywhere; HRC is `nan` on soft tails). Tempering is
  kept to its own `temper_sweep` (the validated **martensite-only** `tempered_martensite_HV`) —
  not folded into the as-quenched sweeps, respecting the deferred mixed-structure temper.

**Validated** (`test_sweep.py`) — *harness* correctness, not new physics: **cross-consistency**
(one composition reaches both the kinetics and the hardness face); **monotone trends** (faster
cool → harder; more C → harder martensite + lower Mₛ; more alloy → martensite survives a slower
quench; more tempering → softer, with the strength↔toughness trade-off and emergent alloy
temper-resistance); **conservation passthrough** (the four fractions sum to 1 at every node).

### The sweep-comparison artifact (`demo_sweep.py`)

```powershell
pip install -e .[viz]
python -m steel.demo_sweep
```

Three steels × four media → the figure
[`docs/figures/steel-sweep.png`](../../docs/figures/steel-sweep.png): the **composition axis**
the four-curves demo cannot show. Left, the mechanism — martensite fraction vs cooling rate,
one line per steel, the deep-hardening 4140 staying martensitic down to far lower rates (its
hardenability), the lean 1045 needing a fast quench, both converging at the saturated ends.
Right, the consequence — a hardness grid (HRC), soft cells flagged off-scale, severe-quench
nodes ringed as beyond the 0-D Biot range.

## Interactive surfaces — the teaching notebook (`steel.ipynb`, §9 slice 1)

The *education* artifact (target #1): the sweep harness with the knobs exposed. It opens with an
**entry-level primer + glossary**, then a guided "cooling curve in, microstructure out" narrative —
Fe-C endpoint → TTT C-curve → the four-curves anchor → composition × cooling-rate hardenability →
tempering — with **ipywidgets sliders** re-running `sweep`/`properties`/`fe_c` live. The
hardenability section adds a **build-your-own-steel** view (live C/Mn/Cr/Mo/Ni sliders that slide the
C-curve right, read out at the discriminating oil quench) with a **schematic microstructure** swatch
(cell areas ∝ the computed phase fractions — illustrative, *not* a grain simulation) and UTS +
relative toughness alongside hardness.

```powershell
pip install -e .[viz,notebook]        # matplotlib (viz) + jupyterlab + ipywidgets + the nbclient/ipykernel run stack
jupyter lab steel/steel.ipynb    # (classic UI: `pip install notebook`, then `jupyter notebook`)
```

It is a **thin skin** (ADR 0002): every *compute* cell calls the validated harness **directly**
(a static figure per section, embedded in the committed `.ipynb` so it reads on GitHub without a
kernel), and `interact` is sugar layered on top. That split is load-bearing, not stylistic —
`ipywidgets.interact` runs its callback inside an `Output` that **captures** exceptions, so a break
inside an interact callback would never reach the smoke-test; the validated calls therefore live in
plain cells (verified: a `raise` in a direct cell fails the test, the same `raise` in an interact
callback does not). The test (`tests/test_steel_notebook.py`) executes the notebook headless
(`nbclient`, `allow_errors=False`) and asserts **no cell errors** — *that it runs clean*, not a
physics check (ADR 0002) — gated on the `[notebook]` stack **and a registered kernelspec**, so a
headless/clean checkout skips rather than errors. The shareable **Streamlit** twin (`app.py`) is
slice 2 (below).

## Interactive surfaces — the Streamlit what-if app (`app.py`, §9 slice 2)

The *shareable* interactive twin of the notebook: the same sweep harness re-skinned as a
slider UI you can `streamlit run` and hand someone a link to. Like the notebook it adds **reach,
not correctness** (ADR 0002) — pure `sweep` re-composition, no new physics.

```powershell
pip install -e .[viz,app]                 # matplotlib (viz) + streamlit (app)
streamlit run steel/app.py
```

It is laid out in **three layers** so the deliverable is both testable and runnable:

- **Compute helpers** (`single_steel_outcomes` / `evaluate_one` / `comparison_grid` /
  `temper_curve_data` / `hardness_readout` / `custom_steel_outcome` / `custom_readout` /
  `composition_warnings`) call `sweep` directly and import **neither** Streamlit
  **nor** matplotlib — so the module imports on a bare core install and the helpers are unit-tested
  **always-green** (`tests/test_app.py`), exactly like `test_sweep` (not gated like the notebook).
- **Figure builders** (`mechanism_figure`, `comparison_figure`, `custom_figure`) are lazy-import
  wrappers over the existing `plots.py` figures (`four_curves_figure`, `sweep_comparison_figure`,
  `single_steel_figure`); the tempering view
  uses Streamlit-native `st.line_chart` (one chart per quantity — HV/HRC/UTS/toughness live on very
  different scales — rather than inventing a matplotlib temper figure in a prior phase's render layer).
- **`main()`** is the **only** place `import streamlit` lives, and is kept paper-thin: every value
  it shows is computed/formatted by a tested helper, so the only statements that can raise are
  literal `st.*` calls — the sole defence for a surface neither the test nor a headless checkout can
  exercise.

**Two non-obvious points** (both verified, not assumed):

- **Run-as-script imports.** `streamlit run app.py` executes the file as a top-level script
  (`__main__`, no package parent) with `steel/` — *not* the repo root — on `sys.path`, so a
  relative `from . import sweep` raises "no known parent package" and a bare `from steel
  import sweep` raises `ModuleNotFoundError`. The module therefore puts the repo root on `sys.path`
  first (the `parents[2]` idiom the demos use) and imports **absolutely**. Verify cheaply, no
  streamlit needed: `python steel/app.py` must reach `import streamlit` inside `main()` and
  die only there (if it dies on a `from …` line, the bootstrap is wrong).
- **The grade dropdown for the main what-ifs; a *guarded* free slider for build-your-own.**
  Cooling/hardness/temper use the `STEELS` registry (real compositions) to dodge the documented
  `Mn = 0` "leaner hypothetical steel" trap — the same discipline as the notebook. The
  build-your-own view deliberately reopens a free C/Mn/Cr/Mo/Ni slider (the experimentation payoff)
  and pays for that reach honestly: the Mn slider floors at 0.30 and `composition_warnings()` flags
  alloy content past the 1080/4140 calibration envelope. HV/HRC honesty (`off HRC scale` where
  Rockwell-C is undefined) and the Biot validity flag (severe quench of a thick section → the
  Phase-2 spatial-solve cue) are surfaced in the readout, not hidden.

It drives **four views** (plus an entry-level on-ramp, open by default): a single grade's
**mechanism + microstructure + hardness readout** (the four-curves figure for the chosen steel,
now with **UTS + relative toughness** beside the hardness), the **composition × cooling-rate
comparison grid** (the hardenability story side by side), a **build-your-own-steel** what-if
(free C/Mn/Cr/Mo/Ni sliders → the C-curve slides right with alloy + a schematic microstructure
swatch, at a fixed oil quench — the same view the notebook's §3 carries), and the
**quench-and-temper response** (martensite-only, the softening / strength↔toughness trade-off).
`tests/test_app.py` exercises every compute helper always-green, asserts importing `app` does
**not** pull Streamlit (the layering guard), and build-smoke-tests the figures under the optional
`[viz]` extra.

## Phase 5a — austenite grain growth (`grain.py`)

Steel's first **post-v1** phase (plan §12). Phases 1–4 mapped a cooling path to a
microstructure and that to **hardness**; Phase 5 adds the structural *length scale* none of
that carried — the **grain size** — and through it (in 5b/5c) the two quantities the hardness
chain withholds: **yield strength** (Hall–Petch) and the **ductile-brittle transition
temperature** (Cottrell–Petch). 5a builds the foundation: the austenite grain a part inherits
from its austenitizing hold, and the ASTM E112 bookkeeping. It is **orthogonal** — it touches
neither the frozen engine nor any frozen benchmark.

```python
from steel import grain
grain.austenite_grain_size(1100.0, t_hours=2.0)   # PAGS after 2 h at 1100 °C → ~45 µm
grain.astm_grain_size_number(22.5)                # → ASTM G ≈ 8  (G↔d round-trips exactly)
```

The kinetics `Dᵐ−D₀ᵐ=K₀·exp(−Q/RT)·t` are pinned to a cited open-access S960MC study: the
**activation energy `Q = 329.95 kJ/mol` is CITED** (the Arrhenius temperature scaling — the
benchmark's teeth), while `m≈4.22 / D₀≈14.46 µm / K₀` are **calibrated** to that study's
isothermal grain-size table (the paper's headline `m=3.03` is a continuous-heating fit; its
isothermal data prefer `m≈4.2` — named, since the literature spread is large). **Validated**
(`test_grain.py`): the law is exactly linear in `t` and `D∝t^(1/m)` for `D≫D₀`, `Q` recovers
from two temperatures, ASTM `G↔d` round-trips (G1→254 µm, G8→22.5 µm); growth is monotone and
the rate decelerates (the dissipative-direction invariant — grain growth has no
mass-conservation analogue); and **the teeth are a holdout** — fit on the 900 & 1200 °C rows,
**predict the held-out 1000 & 1100 °C rows within ~16 %**. Units are **µm / hours / K** (the
registered trap: 5b's Pickering laws cite `d` in mm). The Hall–Petch yield + DBTT (5b) and the
co-benefit figure (5c) are next.

## Phase 6 — competing-reaction CCT kinetics, austempering & the D_I cross-check (6a/6b/6d/6c)

The post-v1 "close the known simplifications" arc (plan §13 is the full story; the module
docstrings are the contracts). **6a** added the missing **proeutectoid-ferrite reaction**
(Li/Kirkaldy–Venugopalan, ceiling A₃) ahead of the byte-identical pearlite curve — the corrected
diagnosis of the 1045 knee ("A₁-not-A₃" was a *mis*diagnosis; A₁ is right for pearlite). **6b**
added the **cited bainite reaction** and *proved* it cannot enter the continuous-cooling race
(the 8620 carbon-spread ceiling) — descoped as a documented negative, the reaction standalone.
**6d** gave that reaction its valid home: **austempering**, the isothermal hold route. **6c**
closed the chain's last un-checked leg — the **D_I / measured-Jominy cross-check** (below).

```python
from steel import austemper as au
au.austemper("1080", 343.3, 600.0)          # quench → hold (650 °F salt bath) → fully bainitic, ~49 HRC
au.minimum_full_hold("1080", 343.3)         # ≈ 305 s — the exercise the §6 surfaces drive
au.hold_time_to_fraction("4340", 371.1, 0.5)  # = 391 s, the cited anchor (by construction)
```

The discipline (a named step down from 6a's one global knob): **one scale per steel**, each
derived **at import** from a single cited `(T, t₅₀)` point of the US Steel *Atlas of Isothermal
Transformation Diagrams* (1951) — because the anchoring probe showed per-steel anchoring
**predicts** (1080 t₅₀ holdouts ×1.06/×0.96 — the teeth, `test_austemper.py`) while the cited
cross-composition arithmetic is **wrong-signed** (atlas: 4340 ~5× slower than 1080; `BC` says
~7× faster — so the two derived scales differ ×41 and `BC` is never used cross-steel, a pinned
negative). Claims stop at the atlas **50 % line**; the quench in is idealized instantaneous; the
un-modeled pearlite race is **policed** (a warning near Bs), not modeled; `pathint` stays
byte-identical. Artifact: [`docs/figures/steel-austemper.png`](../../docs/figures/steel-austemper.png);
surfaces: notebook §6 + app §6 (anchored steels only — deliberately no build-your-own here).

### Phase 6c — the D_I / measured-Jominy cross-check (`ideal_diameter.py`)

The Jominy chain's one un-checked leg: every 2a–2c/6a calibration was anchored to its *own* data
(thermal curve, TTT nose, constituent hardnesses), but the **absolute depth of hardening** the
combination predicts was never directly validated. The **critical diameter** — the round-bar
diameter that is 50 % martensite at its centre — measures exactly that. 6c computes it *from the
finished model* and lays it beside **measured** end-quench data. (We report `D_c`, the water-quench
centre-equivalent diameter directly tabulated in EMJ p.29; the *ideal* `D_I` is its `H→∞` upper
bound — see the conversion note below.)

```python
from steel import ideal_diameter as idd
res = idd.crosscheck_all()                 # {grade: CrossCheck} — model fM=0.5 D_c vs measured band
res["4340"].model.Dc_mm                     # ≈ 119 mm  (water-quench centre-equivalent)
res["4340"].verdict                         # "under-predicts (below measured band)"  ← the teeth
sorted(res, key=lambda n: res[n].model.Dc_mm)   # ['1045', '8620', '4140', '4340'] — ranking correct
```

The **non-circularity** is the whole point: the model's hardenability rides Grossmann *relative
potencies*, so a Grossmann-computed `D_I` would be a tautology — the benchmark is therefore
**measured** H-bands (SAE J1268 1045H exact + 4140H/8620H callouts; EMJ band charts for 4340; EMJ
p.29 for the cited J→diameter conversion; SAE J406 / Hodge–Orehoski for the cited 50 %-martensite
hardness the measured side is read at). The conversion is applied **identically** to both sides so
its accuracy cancels — the discrimination lives in where `J50` falls (model from `fM=0.5`, isolating
hardenability; measured from the cited 50 %M hardness, so the model never grades its own benchmark).
**The conversion fix (advisor catch):** a first attempt used an AI-extracted "SAE J406 Table A7
ideal-`D_I`" table; it was **dropped because *the extraction* was unreliable** (self-contradictory
across attempts, and falling on the EMJ *oil* column below water — impossible for an ideal `D_I`,
since `D_I ≥ D_water ≥ D_oil`) — **not** a claim that J406's real table is wrong (it was never
actually seen). The physics check `D_I ≥ D_water` caught the bad extraction; the durable lesson is to
verify AI-extracted tables against an independent direct read. The directly-read EMJ p.29 water column
is the cited conversion; `D_c` is a defensible lower bound on the ideal `D_I`.

**Validated** (`test_ideal_diameter.py`) — read the *shape*, not "within X %": (1) the **ranking is
correct** (1045 35 < 8620 51 < 4140 104 < 4340 119 mm — alloy beats carbon, the headline); (2) **4340
is under-predicted** (model at/below the measured band's lower edge, whose upper edge runs off the
standard bar — the Cr-Mo-calibrated scale under-captures 4340's **Ni** potency, the strongest
non-circular result); (3) the **directional bias** — shallow grades (1045, 8620) ride high through
the knee (knee + low-carbon hardness-map), the deep grade under-predicts. **4140 is the calibration
anchor** — it lands in its (wide) band *by construction*, not teeth. 4340 is **benchmark-local** (not
in `sweep.STEELS`/the app). Artifact:
[`docs/figures/steel-ideal-diameter.png`](../../docs/figures/steel-ideal-diameter.png). No new
physics/geometry — pure re-composition of the validated Jominy chain + two cited tables.

## Run the tests

```powershell
./run_tests.ps1 steel        # from repo root  (or just ./run_tests.ps1 for the whole suite)
```

The `fe_c` suite is the Phase-1b validation triad: invariant points + exact
lever-rule fractions (analytical limit), carbon conservation + constituent↔phase
consistency (conservation), and the AISI 1045/1080 published-fact comparison
(benchmark).
