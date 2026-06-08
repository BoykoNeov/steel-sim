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
| 2 | `jominy.py` | end-quench hardenability (heat solver, spatial) | planned |
| 3 | `properties.py`, `carburize.py` | microstructure → hardness; case-hardening gradient | planned |
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

## Run the tests

```powershell
./run_tests.ps1 projects/steel        # from repo root  (or just ./run_tests.ps1 for the whole suite)
```

The `fe_c` suite is the Phase-1b validation triad: invariant points + exact
lever-rule fractions (analytical limit), carbon conservation + constituent↔phase
consistency (conservation), and the AISI 1045/1080 published-fact comparison
(benchmark).
