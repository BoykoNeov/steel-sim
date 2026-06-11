# steel-sim — a steel heat-treatment simulator

[![full-gate](https://github.com/BoykoNeov/steel-sim/actions/workflows/full-gate.yml/badge.svg)](https://github.com/BoykoNeov/steel-sim/actions/workflows/full-gate.yml)

*Composition + cooling in, microstructure and properties out.* An educational simulator for
the heat treatment of steels: Jominy hardenability, CCT/TTT transformation kinetics, the
martensite/bainite/ferrite-pearlite reactions, carburizing, tempering, austenite grain growth,
austempering, and a CALPHAD equilibrium backend — each validated against cited metallurgical
references.

It owns and **freezes** the program's core numerical engine: a separately-validated 1-D
diffusion/heat solver (`engines/diffusion`) with its own contract and test suite. The Jominy
end-quench *is* a heat-conduction solve; carburizing *is* a mass-diffusion solve — the same
frozen engine, two boundary-condition faces.

## Layout

```
engines/diffusion/   # the frozen 1-D diffusion/heat solver (+ its own tests)
steel/               # the simulator: jominy, kinetics, pathint, cooling, properties,
                     #   carburize, grain, ferrite/bainite, austemper, ideal_diameter,
                     #   fe_c + calphad_backend, sweep, plots, app.py, demos, steel.ipynb
docs/decisions/      # ADRs 0001–0003 (language/perf, visualization/UX, test policy)
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
./run_tests.ps1 -m "not slow"     # routine fast lane — 386 tests
./run_tests.ps1                   # full suite — 395 tests (adds slow live-CALPHAD, notebook + kinetics checks)
./run_tests.ps1 -n0               # force serial (the default is `-n auto`, parallel)
```

The suite runs **in parallel by default** — `addopts` sets `-n auto --dist loadgroup`
(pytest-xdist, in the `[test]` extra), so xdist is required to run it (`-n0` forces serial for
a clean single-test traceback). `--dist loadgroup` keeps the live-CALPHAD tests on one worker
(`xdist_group("calphad")`) so their solver is built once and no two heavy solves run at once —
see the [ADR 0003 xdist amendment](docs/decisions/0003-test-execution-policy.md).

The suite is **395 tests**, all green. The **live-CALPHAD** cross-checks need the
`[calphad]` extra (pycalphad) and otherwise skip — they run in CI on Python 3.12, where
`pip install -e .[calphad]` resolves cleanly (on 3.14 see the `[calphad]` note in
`pyproject.toml`). The frozen-table Phase-4 validation runs pycalphad-free. Optional stacks
are importorskip-gated, so a headless checkout skips rather than errors. The ODbL steel TDB is
never committed — it is fetched at CI time by `steel.calphad_backend.download_mc_fe()`.

## Provenance

steel-sim was developed inside the **BigSim** monorepo — an educational program of three
simulators (steel, microchip, planet) sharing two separately-validated solver engines — then
extracted into a standalone repo with its history. steel is where the diffusion/heat engine was
first frozen; the sibling simulators (microchip, planet) reused it and live in their own repos.
The archive: [github.com/BoykoNeov/BigSim](https://github.com/BoykoNeov/BigSim).
