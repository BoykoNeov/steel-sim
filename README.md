# steel-sim — a steel heat-treatment simulator

[![full-gate](https://github.com/BoykoNeov/steel-sim/actions/workflows/full-gate.yml/badge.svg)](https://github.com/BoykoNeov/steel-sim/actions/workflows/full-gate.yml)

*Composition + cooling in, microstructure and properties out.* An educational simulator for
the heat treatment of steels: Jominy hardenability, CCT/TTT transformation kinetics, the
martensite/bainite/ferrite-pearlite reactions, carburizing, tempering, austenite grain growth,
austempering, martempering, and the **residual stress & distortion** a quench locks into a section
(solid mechanics), plus a CALPHAD equilibrium backend — each validated against cited metallurgical
references.

It owns and **seals** the program's core numerical engine: a separately-validated 1-D
diffusion/heat solver (`engines/diffusion`) with its own contract and test suite (sealed v1.0,
re-sealed **v1.1** for native nonlinear `D(u)` — [ADR 0004](docs/decisions/0004-unfreeze-nonlinear-diffusivity.md)).
The Jominy end-quench *is* a heat-conduction solve; carburizing *is* a mass-diffusion solve —
the same sealed engine, two boundary-condition faces.

## Layout

```
engines/diffusion/   # the sealed 1-D diffusion/heat solver (v1.1, + opt-in nonlinear D(u)) (+ its own tests)
steel/               # the simulator: jominy, kinetics, pathint, cooling, properties,
                     #   carburize, grain, ferrite/bainite, austemper, martemper, residual,
                     #   ideal_diameter, fe_c + calphad_backend, sweep, plots, app.py, demos, steel.ipynb
docs/index.html      # generated clickable gallery — every demo/figure/notebook in one page (python -m steel.gallery)
docs/decisions/      # ADRs 0001–0004 (language/perf, visualization/UX, test policy, engine unfreeze)
docs/plans/          # steel-production.md — the full build plan
docs/figures/        # banked figures (steel-*.png)
```

## Quickstart

```powershell
pip install -e ".[viz]"                 # compute + figures
python steel/demo_jominy.py             # any demo prints its validation table + banks a figure
streamlit run steel/app.py              # the what-if app (needs .[viz,app])
jupyter lab steel/steel.ipynb           # the teaching notebook (needs .[viz,notebook])
```

→ **New here, or not sure which to run?** See [**What you can run**](#what-you-can-run--a-guided-tour)
below — a map of every demo, notebook section, and app view, with a suggested order.

**Run the tests** (the tiered gate — [ADR 0003](docs/decisions/0003-test-execution-policy.md)):

```powershell
./run_tests.ps1 -m "not slow"     # routine fast lane — 458 tests
./run_tests.ps1                   # full suite — 467 tests (adds slow live-CALPHAD, notebook + kinetics checks)
./run_tests.ps1 -n0               # force serial (the default is `-n auto`, parallel)
```

The suite runs **in parallel by default** — `addopts` sets `-n auto --dist loadgroup`
(pytest-xdist, in the `[test]` extra), so xdist is required to run it (`-n0` forces serial for
a clean single-test traceback). `conftest.py` caps the worker count at **half the logical
cores** (the slow tail is internally threaded, so one-worker-per-core oversubscribes).
`--dist loadgroup` keeps the whole slow tail (every live-CALPHAD test + the notebook kernel)
on **one** worker (`xdist_group("heavy")`) so solvers build once and no two heavy tests run at
once — see the [ADR 0003 xdist amendment](docs/decisions/0003-test-execution-policy.md).

The suite is **467 tests**, all green (2 env-skips). The **live-CALPHAD** cross-checks need the
`[calphad]` extra (pycalphad) and otherwise skip — they run in CI on Python 3.12, where
`pip install -e .[calphad]` resolves cleanly (on 3.14 see the `[calphad]` note in
`pyproject.toml`). The frozen-table Phase-4 validation runs pycalphad-free. Optional stacks
are importorskip-gated, so a headless checkout skips rather than errors. The ODbL steel TDB is
never committed — it is fetched at CI time by `steel.calphad_backend.download_mc_fe()`.

## What you can run — a guided tour

**Prefer a clickable page?** Open **[`docs/index.html`](docs/index.html)** — a generated visual
gallery of every demo, its banked figure, and where the same idea lives in the notebook and app.
It's produced by `python -m steel.gallery` from a single catalog, and a test fails the build if it
drifts, so it stays current. Once [GitHub Pages](https://docs.github.com/pages) is enabled for the
`/docs` folder it is served at `https://boykoneov.github.io/steel-sim/`. The table below is the
same map in Markdown.

Three ways into the same validated core (install + launch commands are in
[Quickstart](#quickstart) above):

- **Demos** — `python -m steel.<name>` — each prints its validation table and banks a figure
  under `docs/figures/`. The fastest way to see a result; needs only `.[viz]`.
- **Notebook** (`steel/steel.ipynb`) — the narrative teaching path with sliders. New to heat
  treatment? Open it and read the **"Start here — the 30-second mental model"** cell, then go
  top to bottom.
- **App** (`steel/app.py`) — the interactive what-if: pick a grade, quench medium, and section
  size and watch the microstructure and hardness move.

The table is ordered as a suggested path — top rows first. Every demo is its own
`python -m steel.<name>`; the *Also interactive* column points to where the same idea lives in
the notebook (§) and the app.

| Topic | Demo (`python -m steel.…`) | Also interactive | What it shows |
|---|---|---|---|
| **Core** | `demo_four_curves` | notebook §1–2 · app *four fates* | One 1080 steel, four quench rates → pearlite → bainite → martensite — the C-curve mechanism beside the resulting microstructure. |
| **Core** | `demo_sweep` | notebook §3 · app *grid / build-your-own* | Composition × cooling rate, side by side — the hardenability axis the four-curves view can't show. |
| **Hardenability** | `demo_jominy` | notebook §3 · app *Jominy* | One end-quench bar: shallow 1045 vs deep-hardening 4140, hardness vs depth. |
| **Hardenability** | `demo_ideal_diameter` | notebook §3 | Critical diameter read *from* the model vs measured H-band data — does it rank hardenability right? |
| **Tempering** | `demo_tempered_jominy` | notebook §4 · app *quench-and-temper* | A *tempered* Jominy traverse — per-constituent temper of a mixed structure. |
| **Grain size** | `demo_grain` | notebook §5 · app §5 | Grain refinement — the lone lever that raises strength *and* toughness at once. |
| **Grain size** | `demo_grain_morphology` | notebook §5 · app §5 | Those two grains drawn to scale — a size-accurate microstructure swatch. |
| **Process routes** | `demo_austemper` | notebook §6 · app §6 | Austempering: quench past the nose, hold inside the diagram, grow bainite. |
| **Process routes** | `demo_martemper` | notebook §6d · app *martempering* | Martempering: the same hardness as a direct quench, far less distortion. |
| **Process routes** | `demo_unified_kv` | notebook §6b · app §6b | The bainite bay *opened* in continuous cooling — three competing reactions raced on one austenite pool. |
| **Process routes** | `demo_bainite` | — | The cited bainite reaction, and why its bay can't form in a plain continuous cool (the negative-result companion). |
| **Validation** | `demo_cct_validation` | notebook §6c | Does any cited composition factor predict bainite kinetics *across* steels? Eight atlas steels say no — the per-steel-only wall, measured and quantified. |
| **Stress** | `demo_residual` | notebook §6e · app *residual stress* | The residual stress and distortion a quench locks into a section (the solid-mechanics axis). |
| **Case hardening** | `demo_carburize` | notebook §8 · app *carburizing* | A carburized gear tooth: carbon diffused in at the surface, case hardness out. |
| **Inverse design** | `demo_design` | notebook §7 · app §7 | Name a target hardness, get a feasible recipe (grade + quench + temper). |
| **Equilibrium** | `demo_calphad` | — | Real CALPHAD thermodynamics vs the parametrised Fe-C diagram (needs the `.[calphad]` extra). |
| **Ironmaking** (front-end) | `demo_reduction` | — | The Ellingham diagram: which reductant reduces which oxide, above which temperature — the front-end "ore → iron" first slice (F1). |
| **Front-end spine** | `demo_heat_state` | — | Failure propagation: a `Heat` record carries an upstream alloy mistake (under-dosed Cr/Mo) into a downstream soft-core defect — the spine that lets the front-end steps compose. |
| **Refining** (front-end) | `demo_refining` | — | Primary refining (BOF/EAF): blow hot metal to the grade's carbon (over-blow → a *validated* soft core), kill it with aluminium, vacuum-degas — filling the `Heat`'s dissolved O/H/N + inclusion fields (the deoxidation curve with its minimum, the C–O coupling, Sieverts √p) (F2 Slice 1). |
| **Slag partition** (front-end) | `demo_slag` | — | Refining's second half: dephosphorize and desulfurize by **slag partition**. The headline is the *opposite oxygen dependence* — P comes out in the oxidizing converter (L_P ∝ +FeO), S in the reducing ladle (L_S ∝ −[O]) — which reproduces the history: acid Bessemer can't dephosphorize, Thomas' basic lining can. P/S are carried but inert downstream — chemistry benchmarked, consequence deferred (F2 Slice 2). |
| **Impurity consequences** (front-end) | `demo_impurity_window` | — | What the tramp impurities finally *do*: the same high-P, sulfurous pig iron made cracking by acid Bessemer and sound by basic + Mushet Mn + ladle desulfurization. P threads the *existing* Pickering DBTT law (strengthens *and* embrittles — the signed foil → cold-short in the hand); free S forms a Fe–FeS grain-boundary film above the 988 °C eutectic (red-short when forged, unless Mn ties it as MnS). Together they bracket the workable temperature window — F2's slag-partition impurity state, its consequence now *closed* (P by propagation through the toughness law, S by a new hot-work verdict). |
| **Temper embrittlement** (front-end) | `demo_temper_embrittlement` | — | Phosphorus' *other* consequence — the quench-and-tempered (martensitic) path, completing its coverage (`cold_short_check` was the ferritic one). A dirty Ni-Cr forging with residual P and no Mo, slow-cooled through ~375–575 °C, segregates P to the prior-austenite grain boundaries → intergranular fracture. Four cures: fast cool, **molybdenum** (the classic remedy for susceptible Ni-Cr forgings), a clean heat, or a reheat >600 °C (the *reversibility* that names it). Watanabe J-factor ranks susceptibility — in the registry only the dirty Ni-Cr victim clears the threshold; 4140/8620 are safe by low J, not their sub-threshold Mo. No strict tooth — the segregation-nose gate was run on paper and could not be pinned (a tractable model is ~100× too fast and underdetermined; the faithful nose needs Fe₃P-cluster kinetics, out of scope). |
| **Tempered-martensite embrittlement** (front-end) | `demo_tempered_martensite_embrittlement` | — | Reversible temper embrittlement's *irreversible* sibling on the same tempering axis (the back-end `toughness_index` ceiling, now a front-end consumer). Temper as-quenched martensite in **260–370 °C** → cementite films along the interlath/grain boundaries (fed by retained-austenite decomposition) → a toughness trough. The opposites: it is **carbon-driven** (a *clean* medium-carbon steel still embrittles, where reversible TE needs P) and **one-way** (temper above ~400 °C recovers, but re-entering the trough can't restore the film — keyed on the *peak* temper). Two gates on the same frozen quench: 4140 embrittles, 8620 (0.20 %C) is immune even fully hardened, an un-hardened section has no tempered martensite to embrittle. No strict tooth — the trough-from-carbide-kinetics gate was run on paper and failed (no stage-III carbide thermo); trough window + ~400 °C recovery cited, carbon gate + verdict by-construction. |
| **Hydrogen flaking** (front-end) | `demo_hydrogen_flaking` | — | What dissolved hydrogen finally *does*, and why it is a *geometric* consequence: F2 fills the ladle hydrogen and flags the chemistry-state risk; whether a *part* flakes (internal hairline cracks) is set by whether the hydrogen can diffuse out before the section cools into the brittle range. Same 4140 heat at ~3.6 ppm, two sections, same dehydrogenation bake → the thin one is sound, the thick one flakes (and a long bake saves it; time ∝ section²). Two-tier like cold-short/red-short. Closed-form slab desorption (Crank), no engine/ADR. One tooth: the bake time from an *independently-pinned* lattice D_H reproduces cited practice (~1 h/inch, heavy forgings days) without tuning — OoM-grade; the L² scaling and verdict are by-construction. |
| **Ladle trim** (front-end) | `demo_ladle` | — | Alloy to grade: trim an alloy-lean tap up to a grade by ferroalloy additions sized for an assumed recovery — a bath that under-delivers lands below the cited 4140 window (off-grade) and the same quench leaves a soft core. One ladle mistake, two flags — the hero-demo input produced, not hand-set (F3). |
| **Casting** (front-end) | `demo_casting` | — | The chain closes front-to-back: Scheil microsegregation enriches a casting's centerline → the same billet heat-treats non-uniformly into a hard centerline band (Chvorinov solidification time too). |
| **Solidification** (front-end) | `demo_solidification` | — | Casting's deferred half (F4 Slice 2): the latent-heat temperature field of a section freezing against a chill, on the *same sealed heat engine* (enthalpy method, no engine touch). The iconic solidification map, the latent-heat arrest, and the headline tooth — the numerical front *converges to the analytic one-phase Stefan form* `2λ√(αt)` under grid refinement (conservation exact). The insulated centre freezes last (the shrinkage hot spot — the same centerline Slice 1 enriches); the cited Niyama criterion collapses there. Stefan = the validated tooth; Niyama/hot-spot = by-construction. |

**Suggested first pass:** `demo_four_curves` → `demo_jominy` → `demo_sweep` →
`demo_tempered_jominy`, then branch by interest. Or just open the notebook and read it top to
bottom.

For the physics behind each demo, the validation discipline, and per-module deep dives, see
**[`steel/README.md`](steel/README.md)** — its "Status & module map" is the full file-by-file index.

## Provenance

This repository is **standalone and self-contained** — everything needed to use, test, and
develop it is here, and nothing depends on any other repository existing. It was originally
developed inside the **BigSim** monorepo (an educational program of three simulators — steel,
microchip, planet — sharing two separately-validated solver engines) and then extracted with its
history. steel is where the diffusion/heat engine was first frozen and the sibling sims reused it.

That origin is why some docs cite `ARCHITECTURE.md §N` or `PORTFOLIO.md`: those were the
monorepo's **program-level** doctrine and catalog files. They are **historical context — not part
of this repo and not required to build, test, or develop it**; the rationale that matters is
restated locally where it is used (`docs/decisions/` ADRs, `docs/plans/steel-production.md`, and
each module's docstring). Where the dated plan and ADRs still cite them, that is a record of what
the build was authored against — like a commit message naming a since-removed file — not a live
dependency.
