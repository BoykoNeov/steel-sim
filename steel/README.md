# `projects/steel` — the steel production simulator

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
- **To use the diffusion/heat spine:** load `engines/diffusion/CONTRACT.md` only —
  the frozen one-pager. You never need the engine's internals.
- The Fe-C boundaries here are **parametrized approximations** (linear between
  pinned invariant points). Phase 4 swaps them for CALPHAD; consumers are unaffected.
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
| 1 | `sweep.py`, `app.py`, `steel.ipynb` | experimentation surface (sweeps, Streamlit, notebook) | planned |
| 2a | `jominy.py` | end-quench **spatial thermal** model (fin equation; frozen heat solver + lateral loss) → cooling-rate-vs-distance | **built ✓** (2026-06-08) |
| 2b | `kinetics.py` (`hardenability_factor`, `ccurve_for_steel`) | alloy **hardenability** = a Grossmann-potency multiplicative C-curve time-shift (Mn/Cr/Mo → right; default identity) | **built ✓** (2026-06-08) |
| 2c | `properties.py`, `demo_jominy.py` | microstructure→hardness map (rule of mixtures) → the Jominy **hardness**-vs-distance artifact; 1045/4140 hardness benchmark | **built ✓** (2026-06-08) |
| 3 | `properties.py` (extend), `carburize.py` | hardness map + cooling-rate/alloy terms, tempering, strength/toughness; case-hardening gradient | planned |
| 4 | `calphad_backend.py` | optional pycalphad equilibrium | planned |

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
from projects.steel.fe_c import phase_fractions, equilibrium_constituents

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
from projects.steel.kinetics import CCurve, andrews_Ms
from projects.steel import cooling, pathint
cc = CCurve(Ms=andrews_Ms(0.8))                 # 1080: A₁=727, Ms≈201, nose≈550 °C/1 s
p = cooling.cooling_path("water", T0=850)        # a 0-D cooling history (t, T)
r = pathint.transform_along_path(p.t, p.T, cc)   # → mostly martensite + retained γ
```

### The anchor demo (`demo_four_curves.py`)

```powershell
pip install -e .[viz]                  # one-time: matplotlib for the figure
python -m projects.steel.demo_four_curves
```

One 1080 specimen, four quench rates → the figure
[`docs/figures/steel-four-curves.png`](../../docs/figures/steel-four-curves.png):
cooling paths drawn *across* the C-curve (the mechanism) beside the resulting
microstructures (the consequence). **Honest result:** four rates give **three**
distinct phase constitutions — furnace & air both pearlite (differing only in
formation temperature → coarseness), oil a bainite-dominant *mixture* (plain 1080
resists clean continuous-cooling bainite; austempering would be needed), water
martensite. The drama is the **property span** (~20 → ~63 HRC indicative). Coarse/
fine pearlite resolution and real hardness numbers are Phase 3.

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
from projects.steel.jominy import JominyBar, solve_thermal_field, jominy_distances
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
from projects.steel.kinetics import ccurve_for_steel
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
from projects.steel.jominy import solve_thermal_field, JominyBar, jominy_distances
from projects.steel.kinetics import ccurve_for_steel
from projects.steel import properties as prop
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
python -m projects.steel.demo_jominy
```

One ASTM A255 bar, two ~0.4 %C steels → the figure
[`docs/figures/steel-jominy-hardness.png`](../../docs/figures/steel-jominy-hardness.png):
hardness vs distance for plain-carbon 1045 and low-alloy 4140 overlaid on representative
published points — they share the quenched end and diverge with depth (4140's deep plateau
vs 1045's soft, off-HRC-scale tail).

**Two follow-ups for a future session:** (1) `plots.py`'s `INDICATIVE_HARDNESS` placeholders
(the four-curves figure's "~20/45/63 HRC") are now superseded by `properties.py` but still
drive that figure — Phase 3 rewires the four-curves demo onto the real model (left as-is now to
preserve the 2b byte-identity guarantee). (2) **D_I cross-check** (compute the ideal critical
diameter *from* the finished model — ideal-quench a series of diameters, find the critical one
— vs published `D_I`) is the immediate next step; it's *available*, not required, for the triad.

## Run the tests

```powershell
./run_tests.ps1 projects/steel        # from repo root  (or just ./run_tests.ps1 for the whole suite)
```

The `fe_c` suite is the Phase-1b validation triad: invariant points + exact
lever-rule fractions (analytical limit), carbon conservation + constituent↔phase
consistency (conservation), and the AISI 1045/1080 published-fact comparison
(benchmark).
