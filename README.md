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
                     #   ideal_diameter, fe_c + calphad_backend, sweep, plots, app.py, demos,
                     #   steel.ipynb (back-end) + making.ipynb (front-end: ore→billet→defects)
docs/index.html      # generated clickable gallery — every demo/figure/notebook in one page (python -m steel.gallery)
docs/decisions/      # ADRs 0001–0004 (language/perf, visualization/UX, test policy, engine unfreeze)
docs/plans/          # steel-production.md — the full build plan
docs/figures/        # banked figures (steel-*.png)
```

## Quickstart

```powershell
pip install -e ".[viz]"                 # compute + figures
python steel/demo_jominy.py             # any demo prints its validation table + banks a figure
streamlit run steel/app.py              # the back-end what-if app (needs .[viz,app])
streamlit run steel/app_making.py       # the front-end (ore→billet) what-if twin (needs .[viz,app])
streamlit run steel/app_consequences.py # the defect-consequences app (needs .[viz,app])
streamlit run game/app_game.py          # the playable spinoff — pick an era + ore, make one heat (needs .[viz,app])
python -m game.demo_game                # the game's headless golden run (prints the contrast, banks a figure)
python -m game.demo_game_methods        # the era tech tree — the purity ramp across the methods of history
jupyter lab steel/steel.ipynb           # the back-end teaching notebook (needs .[viz,notebook])
jupyter lab steel/making.ipynb          # the front-end (ore→billet→defects) teaching notebook
```

→ **New here, or not sure which to run?** See [**What you can run**](#what-you-can-run--a-guided-tour)
below — a map of every demo, notebook section, and app view, with a suggested order.

**Run the tests** (the tiered gate — [ADR 0003](docs/decisions/0003-test-execution-policy.md)):

```powershell
./run_tests.ps1 -m "not slow"     # routine fast lane — 1082 tests
./run_tests.ps1                   # full suite — 1100 tests (adds slow live-CALPHAD, notebook + kinetics checks)
./run_tests.ps1 -n0               # force serial (the default is `-n auto`, parallel)
```

The suite runs **in parallel by default** — `addopts` sets `-n auto --dist loadgroup`
(pytest-xdist, in the `[test]` extra), so xdist is required to run it (`-n0` forces serial for
a clean single-test traceback). `conftest.py` caps the worker count at **half the logical
cores** (the slow tail is internally threaded, so one-worker-per-core oversubscribes).
`--dist loadgroup` keeps the whole slow tail (every live-CALPHAD test + the notebook kernel)
on **one** worker (`xdist_group("heavy")`) so solvers build once and no two heavy tests run at
once — see the [ADR 0003 xdist amendment](docs/decisions/0003-test-execution-policy.md).

The suite is **1100 tests**, all green (2 env-skips). The **live-CALPHAD** cross-checks need the
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
- **Notebooks** — two narrative teaching paths with sliders, each opening with a **"Start here —
  the 30-second mental model"** cell. `steel/steel.ipynb` is the back-end (cooling curve →
  microstructure); `steel/making.ipynb` is the front-end twin — *ore → billet → and what goes
  wrong* (reduction → spine → refining/slag → ladle → casting, then the six defect consequences).
- **App** (`steel/app.py`) — the interactive back-end what-if: pick a grade, quench medium, and
  section size and watch the microstructure and hardness move.
- **Making app** (`steel/app_making.py`) — the front-end (ore→billet) twin: walk reduction → refining
  → slag → ladle trim (alloy, carbon carry-in, the deox→recovery seam) → casting and watch an upstream
  mistake propagate to a downstream soft core.
- **Consequences app** (`steel/app_consequences.py`) — the third panel of the triptych: turn the
  knobs on each defect (cold/red-short, temper & tempered-martensite embrittlement, hydrogen flaking,
  CO porosity, hot-tearing, peritectic surface cracking) and see the flat upstream risk line disagree
  with the real consequence — then the *signed* foils, where the same impurity is an asset (the
  free-machining sulfide, the Wootz/Damascus carbide pattern), not only a defect.
- **Game** (`game/app_game.py`, headless `python -m game.demo_game` / `python -m game.demo_game_methods`) —
  the playable spinoff (the `game/` build plan, [`docs/plans/game.md`](docs/plans/game.md)). **Slice 1 — *the
  gauntlet*:** the full-chain capstone made *playable*, where **every stage is a decision**. Take every
  recommendation and the part comes out sound (and reproduces the capstone golden run exactly); one wrong
  call — a weak kill, a shallow vacuum, skipped dephos, carbon pickup — plants a latent flaw the finished
  part is judged on by the sealed consequence engines (porosity, flaking, cold-short, off-grade), emergent
  not scripted (the bar is *losability*). **Slice 2 — *the era tech tree*:** make the same grade through the
  methods of history (acid Bessemer → Thomas → open hearth → BOF → modern EAF + ladle), each a constrained
  walk through the same engines, with the **purity-control ramp** the difficulty curve — a phosphoric ore is
  cold-short in acid Bessemer (acid slag, L_P≈1), phosphorus-fixed-but-dirty in Thomas, and sound only in the
  modern ladle era; a clean ore is sound even in acid Bessemer. `game/` orchestrates the validated engines
  and reimplements **no** physics — its discipline is structural (a firewall guard + golden-run determinism +
  losability + the purity ramp).

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
| **Validation** | `demo_slag_validation` | — | Does the cited optical-basicity sulfide-capacity model predict C_S *out-of-sample*? An independent measured dataset (Nzotta 1998, post-1986, MnO/FeO-free) says yes for basic slags — ~×1.4, tight, perfect ranking — and names the acidic and MnO edges. |
| **Stress** | `demo_residual` | notebook §6e · app *residual stress* | The residual stress and distortion a quench locks into a section (the solid-mechanics axis). |
| **Stress** | `demo_fracture` | — | Quench cracking as the coupling of two axes: the residual-stress field (§18, consumed as code) and a **representative** cleanliness input — a worst-case surface flaw `√area` — joined by a linear-elastic fracture-mechanics gate (Murakami √area vs the as-quenched martensite K_Ic). Hero: one thick 4340, one direct water quench, **one** surface tension — a clean heat (largest surface flaw √area ≈ 30 µm) sits below the critical flaw size and survives, while a dirty heat (√area ≈ 400 µm) in the *identical* field exceeds it and **quench-cracks**. So the flat `quench-crack-risk` (surface in tension) splits two-tier into a realized `quench-crack` only when tension **and** a critical flaw coincide — cleanliness is load-bearing, not a relabel. Martempering the dirty part collapses the surface tension (→ compression), √area_c → ∞, crack clears (the §17/§18 distortion benefit, now in fracture). Needs the **phase-split yield** path (hard martensite surface holds the tension a single-yield solve caps at σ_Y,20) — lifting residual.py's own named scope edge, the one genuine new mechanics here. **No claimable tooth** (sign reversal + martemper benefit consumed from residual; LEFM + Murakami factor cited; as-quenched K_Ic, martensite-yield base and clean/dirty √area representative — the absolute threshold ∝ K_Ic² is a named scope edge). Ceilings: surface-initiated only, atlas-steel (4340) only, one flaw per heat, and the `√area` input is **not** wired to the inclusion engines (`slag` / `sulfide_morphology`) — a bulk volume fraction is not a largest-flaw size, so that bridge is a named deferral, not a tuned number. |
| **Case hardening** | `demo_carburize` | notebook §8 · app *carburizing* | A carburized gear tooth: carbon diffused in at the surface, case hardness out. |
| **Inverse design** | `demo_design` | notebook §7 · app §7 | Name a target hardness, get a feasible recipe (grade + quench + temper). |
| **Equilibrium** | `demo_calphad` | — | Real CALPHAD thermodynamics vs the parametrised Fe-C diagram (needs the `.[calphad]` extra). |
| **Ironmaking** (front-end) | `demo_reduction` | making nb §F1 · app *making* | The Ellingham diagram: which reductant reduces which oxide, above which temperature — the front-end "ore → iron" first slice (F1). |
| **Front-end spine** | `demo_heat_state` | making nb §spine · app *making* | Failure propagation: a `Heat` record carries an upstream alloy mistake (under-dosed Cr/Mo) into a downstream soft-core defect — the spine that lets the front-end steps compose. |
| **Refining** (front-end) | `demo_refining` | making nb §F2a · app *making* | Primary refining (BOF/EAF): blow hot metal to the grade's carbon (over-blow → a *validated* soft core), kill it with aluminium, vacuum-degas — filling the `Heat`'s dissolved O/H/N + inclusion fields (the deoxidation curve with its minimum, the C–O coupling, Sieverts √p) (F2 Slice 1). |
| **Slag partition** (front-end) | `demo_slag` | making nb §F2b · app *making* | Refining's second half: dephosphorize and desulfurize by **slag partition**. The headline is the *opposite oxygen dependence* — P comes out in the oxidizing converter (L_P ∝ +FeO), S in the reducing ladle (L_S ∝ −[O]) — which reproduces the history: acid Bessemer can't dephosphorize, Thomas' basic lining can. P/S are carried but inert downstream — chemistry benchmarked, consequence deferred (F2 Slice 2). |
| **Impurity consequences** (front-end) | `demo_impurity_window` | making nb §D1 · app *consequences* | What the tramp impurities finally *do*: the same high-P, sulfurous pig iron made cracking by acid Bessemer and sound by basic + Mushet Mn + ladle desulfurization. P threads the *existing* Pickering DBTT law (strengthens *and* embrittles — the signed foil → cold-short in the hand); free S forms a Fe–FeS grain-boundary film above the 988 °C eutectic (red-short when forged, unless Mn ties it as MnS). Together they bracket the workable temperature window — F2's slag-partition impurity state, its consequence now *closed* (P by propagation through the toughness law, S by a new hot-work verdict). |
| **Temper embrittlement** (front-end) | `demo_temper_embrittlement` | making nb §D2 · app *consequences* | Phosphorus' *other* consequence — the quench-and-tempered (martensitic) path, completing its coverage (`cold_short_check` was the ferritic one). A dirty Ni-Cr forging with residual P and no Mo, slow-cooled through ~375–575 °C, segregates P to the prior-austenite grain boundaries → intergranular fracture. Four cures: fast cool, **molybdenum** (the classic remedy for susceptible Ni-Cr forgings), a clean heat, or a reheat >600 °C (the *reversibility* that names it). Watanabe J-factor ranks susceptibility — in the registry only the dirty Ni-Cr victim clears the threshold; 4140/8620 are safe by low J, not their sub-threshold Mo. No strict tooth — the segregation-nose gate was run on paper and could not be pinned (a tractable model is ~100× too fast and underdetermined; the faithful nose needs Fe₃P-cluster kinetics, out of scope). |
| **Tempered-martensite embrittlement** (front-end) | `demo_tempered_martensite_embrittlement` | making nb §D3 · app *consequences* | Reversible temper embrittlement's *irreversible* sibling on the same tempering axis (the back-end `toughness_index` ceiling, now a front-end consumer). Temper as-quenched martensite in **260–370 °C** → cementite films along the interlath/grain boundaries (fed by retained-austenite decomposition) → a toughness trough. The opposites: it is **carbon-driven** (a *clean* medium-carbon steel still embrittles, where reversible TE needs P) and **one-way** (temper above ~400 °C recovers, but re-entering the trough can't restore the film — keyed on the *peak* temper). Two gates on the same frozen quench: 4140 embrittles, 8620 (0.20 %C) is immune even fully hardened, an un-hardened section has no tempered martensite to embrittle. No strict tooth — the trough-from-carbide-kinetics gate was run on paper and failed (no stage-III carbide thermo); trough window + ~400 °C recovery cited, carbon gate + verdict by-construction. |
| **Hydrogen flaking** (front-end) | `demo_hydrogen_flaking` | making nb §D4 · app *consequences* | What dissolved hydrogen finally *does*, and why it is a *geometric* consequence: F2 fills the ladle hydrogen and flags the chemistry-state risk; whether a *part* flakes (internal hairline cracks) is set by whether the hydrogen can diffuse out before the section cools into the brittle range. Same 4140 heat at ~3.6 ppm, two sections, same dehydrogenation bake → the thin one is sound, the thick one flakes (and a long bake saves it; time ∝ section²). Two-tier like cold-short/red-short. Closed-form slab desorption (Crank), no engine/ADR. One tooth: the bake time from an *independently-pinned* lattice D_H reproduces cited practice (~1 h/inch, heavy forgings days) without tuning — OoM-grade; the L² scaling and verdict are by-construction. |
| **Gas (CO) porosity** (front-end) | `demo_gas_porosity` | making nb §D5 · app *consequences* | What dissolved oxygen finally *does*, and why it is a *carbon-aware* consequence: F2 flags a carbon-blind risk (O > 30 ppm); whether a *casting* blows CO holes is set by the carbon the oxygen reacts with — gas evolves where `[%C]·[%O]` crosses the same CO equilibrium the converter runs on. Same light kill, two carbons, both within the 30 ppm spec → the high-carbon 1080 sits on the CO line (limit ~25 ppm) and blows holes, carrying *less* oxygen than the sound low-carbon 8620 (limit ~100 ppm); a full kill saves it. Two-tier like cold-short/red-short/flaking — and the two flags disagree because of carbon. No engine/ADR, **no claimable tooth** (the criterion is the cited C–O equilibrium vs held composition); soft OoM note `O_crit ∝ 1/C`; the solidification CO-margin is a conservative secondary, not the verdict. |
| **Hot-tearing** (front-end) | `demo_hot_tear` | making nb §D6 · app *consequences* | What residual sulfur does at the *casting* stage — the segregation-amplified sibling of forging-stage red-shortness: slag flags a flat, Mn-blind risk (S > 0.040 %); whether a *casting* grows a Fe–FeS interdendritic film and hot-tears is set by the Mn:S in the **last liquid to freeze**, which is Scheil-enriched — sulfur piles up ~10× faster than manganese, so the film Mn:S is ~10× poorer than the bath. Two heats, same sulfur (both in spec, both clearing bulk MnS stoichiometry): the lower-Mn one (Mn:S 10) tears (film ~1.2), the higher-Mn one (Mn:S 22) is sound — the Mushet lever, threshold now in the *tens*. Distinct from red-short by **phase + time** (interdendritic liquid during freezing vs bulk solid at the forge), not duplicated. No engine/ADR, **no claimable tooth** (cited Scheil partition × cited MnS stoichiometry); soft OoM note: segregation amplifies 1.71 into the tens, reproducing the empirical "Mn:S ≳ 20" rule (Toledo 1993), order-robust/cutoff-tuned. RDG-feeding + carbon-peritectic deferred. |
| **MnS morphology** (front-end) | `demo_sulfide_morphology` | making nb §D8 · app *consequences* | The **signed sulfur foil**: the same manganese sulfide is a deliberate **free-machining** asset (why the resulfurized 11xx grades exist — MnS breaks the chip) *and* an unintended **through-thickness toughness** liability (hot working elongates the plastic MnS into stringers that gut the short-transverse direction). Slag's one flat, shape-blind `high-sulfur` risk (S > 0.040 %) fires on every free-machining grade by design; this **splits** it. Hero: one resulfurized 1144-type heat, as-rolled it is free-machining **and** anisotropic; a calcium treatment globularizes the MnS → free-machining **and** isotropic — same sulfur, same MnS *volume*, only the shape changed (so the anisotropy flag is gated on **morphology**, never an S-threshold). A plain low-S heat is tough but can't free-machine — the other end of the trade. Worked-product sibling of red-shortness (it reads the *tied* MnS, where red-short reads the *free* sulfur). No engine/ADR, **no claimable tooth** (MnS amount = cited stoichiometry, volume = cited density ratio, both verdicts by-construction); 'one MnS, two opposite signs' is the pedagogical point, by construction. The machinability index is the MnS contribution only (hardness/carbon + Pb/Ca/Te confound the real rating); the transverse debit is its own directional axis (not the hardness toughness proxy or DBTT). Stringer aspect ratio (∝ rolling reduction) is a named ceiling. |
| **Wootz / Damascus banding** (front-end) | `demo_wootz` | making nb §D9 · app *consequences* | The **signed *good*-impurity foil** and the one genuine front-end physics gap (`steel-making.md` §14.5 / §15.4), now filled: the watered Damascus pattern needs a trace carbide-forming **"impurity"** — chiefly **vanadium** — that a modern clean-steel spec would reject, yet the wootz smith *requires*; "bad steel" and "good steel" are the same composition, signed either way. Carbide banding develops only through **three gates** (Verhoeven & Pendray 1998): **hypereutectoid carbon** (~1.5 %, a proeutectoid Fe₃C network to band — `fe_c` lever rule), a **trace former ≥ threshold** (**V ≥ 40 ppm**, or weaker Mn ≥ 200 ppm), and **cyclic forging 50–100 °C below A_cm** (forge hotter and the carbide dissolves). Hero: the *same* 1.5 %C steel forged the *same* way — the V-bearing cake waters into Damascus; the clean modern twin comes out plain and raises **`wootz-pattern-failed`** ("the smith did everything right; the ore lacked the vanadium"). A plain bar never forged as wootz raises no flag — gated on **intent**. Reuse beat: the interdendritic former enrichment that bands the carbide is the *same* Scheil ratio (`casting.segregation_ratio`) that makes centerline segregation a *defect* — one engine, two signs (γ coefficients; hypereutectoid wootz solidifies as primary austenite). No engine/ADR, **no claimable tooth** (three cited threshold lines + `fe_c` lever rule + `casting` Scheil); band spacing 30–70 µm is a **cited observation**, *not* computed (cake modulus / Chvorinov B / SDAS law are soft knobs aimed at a 2×-wide target — a manufactured coherence declined). |
| **Ladle trim** (front-end) | `demo_ladle` | making nb §F3 · app *making* | Alloy to grade: trim an alloy-lean tap up to a grade by ferroalloy additions sized for an assumed recovery — a bath that under-delivers lands below the cited 4140 window (off-grade) and the same quench leaves a soft core. One ladle mistake, two flags — the hero-demo input produced, not hand-set (F3). |
| **Carbon carry-in** (front-end) | `demo_carbon_carry_in` | making nb §F3b · app *making* | A *second* ladle mistake: the carbon the ferroalloys carry. Same charges, the ferroalloy carbon grade decides — cheap high-carbon (charge-grade) ferrochrome/ferromanganese (6–8 % C) drag a 4140 trim up ~+0.18 %C to ~0.56 %C, **off-grade on its own carbon band** and a harder steel (~700 HV vs the on-grade ~625); the refined low-carbon grades carry the same trim clean — *why low-carbon ferroalloys exist*. Off-grade fires on carbon through the same window machinery (no new flag); the hardness rise is the validated back end consuming the carry-in — propagation colour, not a verdict. No engine/ADR, **no claimable tooth** (mass-balance on cited assays); the ~40 %-of-the-grade's-carbon magnitude is an OoM coherence note. Deox-state recovery now its own panel (next); P/S bands deferred. |
| **Deox→recovery seam** (front-end) | `demo_deox_recovery` | making nb §F3c · app *making* | The F2→F3 seam: the bath's dissolved oxygen taxes the *oxidizable* trim alloys' recovery. The same charges into a well-killed bath (Al-killed, O ~4 ppm) recover Mn/Si in full; into an under-killed one (a weak kill — O ~53 ppm, **porosity-risk**) the dissolved oxygen ties up a stoichiometric mass of Mn/Si as oxide so they land short — while the noble Cr/Mo/Ni land identically (**selectivity**: only the alloys that deoxidize pay the tax). Honest and **modest**: even a fully under-killed bath taxes Mn ~2 % at 4140's carbon (~4 % at 8620's, lower carbon → higher dissolved O), so the landed Mn dips but stays *in-window* — the dissolved-O coupling alone can't trip off-grade, which is quantitatively why `demo_ladle`'s gross under-trim hero must be hand-set. Carbon→oxygen→tax coherence ties F2's C–O coupling straight into F3 recovery (kill-before-you-trim matters most where carbon is lowest). No engine/ADR, **no claimable tooth** (conservation arithmetic on cited oxide stoichiometry); the gross slag-FeO reoxidation distribution is the named ceiling. The only flag is F2's porosity-risk. |
| **Casting** (front-end) | `demo_casting` | making nb §F4a · app *making* | The chain closes front-to-back: Scheil microsegregation enriches a casting's centerline → the same billet heat-treats non-uniformly into a hard centerline band (Chvorinov solidification time too). |
| **Solidification** (front-end) | `demo_solidification` | making nb §F4b · app *making* | Casting's deferred half (F4 Slice 2): the latent-heat temperature field of a section freezing against a chill, on the *same sealed heat engine* (enthalpy method, no engine touch). The iconic solidification map, the latent-heat arrest, and the headline tooth — the numerical front *converges to the analytic one-phase Stefan form* `2λ√(αt)` under grid refinement (conservation exact). The insulated centre freezes last (the shrinkage hot spot — the same centerline Slice 1 enriches); the cited Niyama criterion collapses there. Stefan = the validated tooth; Niyama/hot-spot = by-construction. |
| **Peritectic cracking** (front-end) | `demo_peritectic` | making nb §D7 · app *consequences* | The carbon-driven sibling of sulfur hot-tearing: the peritectic transformation `L + δ → γ` is a BCC→FCC volume contraction that, concentrated high in the continuous-casting mould, shrinks the thin shell off the wall into longitudinal facial cracks — so the hypo-peritectic ~0.10–0.16 %C grades are the worst surface-crackers, and counter-intuitively a *leaner* OR a *richer* steel casts more soundly. Three plain-carbon heats, carbon the only axis: 0.05 %C (fully δ, sound), 0.11 %C (cracks), 0.45 %C (austenitic, sound) — *more carbon is safer*. Verdict = Wolf's cited ferrite-potential band `FP = 2.5(0.5 − Cp)` (0.8–1.05); mechanism = the Fe–C peritectic lever rule (cited invariants 0.09/0.17/0.53 at 1495 °C, by construction). Reads **nominal** carbon (the shell phenomenon) — the *reverse* of hot-tear's last-liquid read. Second lever: same 0.20 %C, ferrite stabilizers (Si+Cr) pull Cp into the band. No engine/ADR, **no claimable tooth** (cited classifier + by-construction lever); soft *coherence* note (carefully **not** independent — both rest on the Fe–C peritectic): the lever rule and Wolf's empirical FP place the trouble at the same ~0.1 %C window. Consumed-δ peaks at the band edge (Cγ 0.17), not the empirical worst — exact worst-carbon needs δ→γ kinetics + shell mechanics (underdetermined). |
| **Full-chain capstone** (front-end) | `demo_capstone` | making nb §capstone | The synthesis the front and back halves were each built toward: **one** `Heat` threaded the whole way — hot-metal charge → decarburize → dephosphorize → deoxidize → degas → desulfurize → trim to grade → cast → quench — on a single, un-rewritten provenance trail (until now the stages were only ever shown *independently*, each from its own fresh origin). Two heats take the identical chain and differ by a **single knob**, the F2 blow endpoint: the reference (blown to the grade carbon) lands a **sound** part — on grade, through-hardened, the seeded tramp P/S driven below spec end to end; the over-blown foil (0.25 %C) is wrong from the blow, caught **off-grade** at the trim, and **soft-cores** at the quench — the longest propagation in the repo, one mistake surfaced two stages apart. Integration, **not new physics** (the spine's posture): every number comes from a sealed engine, and the lone seam that takes a `Steel` (casting) is re-based onto the `Heat` so the trail stays continuous. |

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

## License

Licensed under the **Boyko Non-Commercial License v1.0 (BNCL-1.0)** — see
[`LICENSE`](LICENSE). Commercial use is prohibited unless separately licensed by the copyright
holder. Redistributions and derivative works must retain both the [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE) files.
