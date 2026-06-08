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
| 3a | `properties.py` (extend), `demo_four_curves.py` (rewire), `cooling.py` | Maynier **minor-alloy + cooling-rate** terms grafted on the 2c carbon baselines; four-curves demo on the **real** hardness model (placeholders retired) | **built ✓** (2026-06-08) |
| 3b | `properties.py` (extend) | tempering (Hollomon–Jaffe master curve) + ISO-18265 strength + rough strength/toughness trade-off | **built ✓** (2026-06-08) |
| 3c | `carburize.py`, `demo_carburize.py` | carburizing case-hardening: frozen engine in **mass mode** (erfc carbon profile) → microstructure + hardness gradient (gear-tooth artifact) | **built ✓** (2026-06-08) |
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

**Follow-ups:** (1) ~~`plots.py`'s `INDICATIVE_HARDNESS` placeholders drive the four-curves
figure~~ — **done (Phase 3a):** the placeholders are retired and the four-curves demo now shows
the real `properties.py` hardness. (2) **D_I cross-check** (compute the ideal critical diameter
*from* the finished model — ideal-quench a series of diameters, find the critical one — vs
published `D_I`) is still *available*, not required, for the triad.

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
from projects.steel import properties as prop
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
from projects.steel import properties as prop
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
from projects.steel import carburize as cb
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
python -m projects.steel.demo_carburize
```

One carburized 8620 section → the figure
[`docs/figures/steel-carburize-gradient.png`](../../docs/figures/steel-carburize-gradient.png):
three panels sharing the depth axis — the carbon profile (numeric + erfc overlay + case-depth
marker), the microstructure gradient (martensite case, retained-γ rising into the surface), and
the hardness traverse (martensite potential over the as-quenched curve, with the published surface
band sitting honestly between them). **Scope named:** constant `D` (vs Tibbetts `D(C)`), Dirichlet
constant potential (vs a Robin finite-surface-reaction / boost-diffuse ramp), and the high-carbon
extrapolation. The **D_I cross-check** remains *available, not built* (not triad-required).

## Run the tests

```powershell
./run_tests.ps1 projects/steel        # from repo root  (or just ./run_tests.ps1 for the whole suite)
```

The `fe_c` suite is the Phase-1b validation triad: invariant points + exact
lever-rule fractions (analytical limit), carbon conservation + constituent↔phase
consistency (conservation), and the AISI 1045/1080 published-fact comparison
(benchmark).
