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
