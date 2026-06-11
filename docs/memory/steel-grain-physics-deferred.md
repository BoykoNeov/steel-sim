---
name: steel-grain-physics-deferred
description: "Steel grain physics: was deferred (schematic stand-in in steel.ipynb); PROMOTED to Phase 5, COMPLETE (5a growth + 5b Hall–Petch yield/Cottrell–Petch DBTT + 5c coupling), SURFACED interactively §5 (2026-06-09). The last deferral — grain *morphology* (Voronoi swatch) — now BUILT 2026-06-10 (viz-reach, alongside the schematic). Notebook §5 cell still deferred"
metadata: 
  node_type: memory
  type: project
  originSessionId: c86aa66a-a37e-4467-8db7-26b9c0a66b2f
---

The steel models have **no grain-size physics** — no Hall–Petch strengthening, no
austenite grain-growth during austenitization, no ASTM grain number. When the user
asked (2026-06-09) for "visualization of grain variation," the fork was made explicit
(schematic cartoon now vs. real grain physics later) and they chose **both**: the
cartoon shipped this round, the physics is deferred.

**Shipped stand-in:** `projects/steel/plots.py::microstructure_schematic` + the
steel.ipynb "build-your-own-steel" cell render a **schematic** swatch whose cell
*areas* are the validated phase fractions but whose grain shapes/sizes are decorative —
labelled "illustration, not a grain simulation" per ADR 0002 (reach, not evidence). It
is NOT a grain model; do not let it masquerade as one.

**Deferred Phase (build only when the user revisits it):** a real grain-size module —
austenite grain growth (time/temperature at austenitising T) → Hall–Petch
`σ_y = σ0 + k·d^(−½)` feeding the [[bigsim-program]] property model — with its own
validated triad (analytic limit + a published Hall–Petch-coefficient benchmark). New
physics ⇒ a Phase with a short plan first, NOT a notebook tweak. **How to apply:**
offer to write that plan when grain physics comes up again; until then the schematic is
the honest answer.

**REVISITED 2026-06-09 → PROMOTED to active Phase 5; OPTION (b) chosen (plan WRITTEN, build
pending).** User chose the grain-size/Hall–Petch route from a 4-direction "future of steel"
menu (others — residual-stress / deepen-gaps / inverse-design — `[available]`, plan §11), then
chose **option (b)** (model *demonstrates* the strength-AND-toughness co-benefit, not just
narrates it). Detailed sub-plan = `docs/plans/steel-production.md` **§12**. Crux decisions:
(1) **TWO new quantities** the hardness chain withholds — **yield** (Tabor `H≈3σ`=flow not
yield) AND the **DBTT** (ductile-brittle transition *temperature*) — both f(grain size);
orthogonal, frozen benchmarks byte-identical, engine untouched, `toughness_index(HV)` NOT
modified. (2) **The (b) spine = two laws of the SAME Hall–Petch form, opposite grain-size
signs** (the **Pickering ferrite-pearlite equation pair**): `σ_y=f(comp,%pearl)+k_y·d^(−½)`
(grain term +) and `DBTT=g(comp,%pearl)−k_T·d^(−½)` (grain term −). Si/N/pearlite raise BOTH
(embrittle); only the grain term flips sign → grain refinement = the lone co-improving lever.
`%pearlite` from **fe_c** (Phase 1b) → carbon embrittles. (3) **3b reconciliation (load-bearing):
DBTT = a transition TEMPERATURE on the grain-size axis (monotone Cottrell–Petch), NOT the full
Charpy curve** — shelf energies + tempering-axis non-monotonicity (tempered-mart/temper
embrittlement) stay 3b's named ceiling, untouched. (4) **ADVISOR CIRCULARITY CATCH (critical):**
the sign-opposition is **NOT the validation teeth** — citing BOTH Pickering eqns makes it true
**by construction** (no holdout can falsify it = Phase-4 "wiring check, not probative" status);
it stays as the *pedagogical payoff / a consistency-check-that-passes-by-construction*, the
figure, the reason (b)>(a). **The ONLY real teeth = 5a's grain-growth kinetics benchmark**
(independent grain-size-vs-austenitizing-T data that genuinely can fail); σ_y/DBTT lines =
*calibrated*; plain-carbon (σ_y,DBTT) in published band = *loose in-distribution* sanity (Pickering
= general correlation, ~nothing held out). DON'T write a test asserting sign-opposition as the
benchmark leg. (5) "conservation" leg = **dissipative monotone invariant** (`dd/dt≥0`, rate→0,
boundary area shrinks); no mass-conservation analogue. (6) **isolate PAGS at fixed cooling rate**
(ferrite grain ∝ cooling rate too, often > PAGS — 3c single-quench move). (7) **UNITS TRAP** —
Pickering uses `d` in **mm**, bare Hall–Petch MPa·m^(½) uses `d` in **m**; grain.py pins internal
**µm**, converts at each boundary, registry-tested (chip-CGS / oxidation-µm trap). (8) defer
martensite packet-HP + martensite toughness; grain *size* not *morphology* (Voronoi=viz, ADR-0002).
Build 5a (growth+ASTM-G) → 5b (BOTH laws, `nan` for martensitic, cited Pickering pair) → 5c
(couple+co-benefit figure+yield≤UTS guard). Sources to pin: (1) grain-growth-vs-T dataset + (2)
Pickering σ_y/ITT pair — **INDEPENDENT** of each other.

**5a BUILT 2026-06-09** — `projects/steel/grain.py` + `tests/test_grain.py` (13 tests, steel
gate **249→262**, all `not slow`, orthogonal/additive — no engine touch). Source pinned →
[[grain-growth-source]] (S960MC, open-access PMC9737238): **Q=329.95 kJ/mol CITED** (Arrhenius
T-scaling=teeth), `m≈4.22/D₀≈14.46µm/K₀` calibrated to the isothermal table (paper's headline
m=3.03=continuous-heating fit, isothermal data prefer m≈4.2; lit spread n2.6–6.5/Q256–572).
Triad: analytic=law-linear-in-t + `D∝t^(1/m)` + Q-recovery + ASTM `G↔d` exact (G1→254µm/G8→22.5µm);
dissipative-invariant=monotone+decelerating rate; **benchmark teeth=HOLDOUT** (fit 900&1200°C →
predict 1000&1100°C within ~16%), full-table reproduction asserted LOOSE (Q weakly determined →
modest teeth, named). Units µm/hours/K (registered trap; 5b Pickering uses d in **mm**).

**5b BUILT 2026-06-09** — `grain.py` §3 (`hall_petch_yield_MPa`, `cottrell_petch_dbtt_C`) + 16 new
tests (steel gate **262→278** fast lane / 286 with slow optional stack). The **two grain-size
property laws** = the cited **Pickering ferrite-pearlite pair**, same Hall–Petch form, OPPOSITE
grain-size signs: `σ_y=53.9+32.34Mn+83.16Si+354.2√N+k_pearl·%pearl+17.402·d^(−½)` (grain **+**) /
`DBTT=−19+44Si+700√N+2.2·%pearl−11.5·d^(−½)` (grain **−**), d in **mm**. Source (2) pinned →
[[pickering-strength-dbtt-source]] (Pickering 1978), INDEPENDENT of [[grain-growth-source]]. Cited
vs calibrated: yield Mn/Si/N/grain + DBTT Si/N/pearl/grain all **cited** (−11.5 grain & +44 Si
**WEB-CONFIRMED**; −19/700/2.2 recalled-canonical, structurally cross-checked); **ONE calibrated** =
pearlite-in-yield `≈2 MPa/%` (rule-of-mixtures, flagged, NOT tuned to 5c — Pickering's yield eqn is
ferrite-matrix-controlled, no pearlite term). The **one external right-answer** = textbook "refine
10µm→1µm lowers DBTT ~250K" → model gives −248.7°C (= the −11.5 coeff, pins d-in-mm). Else
by-construction/in-distribution & labelled so (sign-opposition = demo passing by construction = NOT
teeth, as advisor-caught). **nan for martensite** (`f_martensite>0.5`; bainite named
loosely-out-of-domain). `%pearlite` = equilibrium slow-cool from `fe_c` (Phase 1b). N_free flagged
default 0.005 wt% (√, wt%≠ppm registry-tested). `toughness_index` UNTOUCHED (DBTT=temp on a
different axis from 3b's tempering-Charpy ceiling). Co-benefit already visible numerically (1045
refined 80→5µm: yield 299→484 MPa, DBTT 127→5°C). **NEXT: 5c** (couple PAGS→ferrite grain at fixed
cooling rate + banked co-benefit figure + `yield≤UTS`/DBTT-sanity guards + `demo_grain`).

**5c BUILT 2026-06-09 → PHASE 5 COMPLETE.** `grain.py` §4 (`ferrite_grain_size`, `GrainProperties`,
`coupled_grain_properties`) + `plots.grain_figure` + `demo_grain.py` + 10 tests (7 in test_grain §5c
+ 3 in test_demo_grain); steel gate **278→288** fast lane. **The coupling:** austenitize (T,t) →
PAGS (5a) → **ferrite grain via the ONE calibrated `FERRITE_PAGS_RATIO≈0.5`** (austenite GBs nucleate
pro-eutectoid ferrite → finer γ→finer α; ratio<1 = several α per γ) → equilibrium %pearlite from
`fe_c` (1b) → 5b yield+DBTT. **Isolated at fixed cooling rate** (ferrite grain ∝ cooling rate too,
folded into the ratio — the 3c single-quench move, named). Takes `(C,comp)` not a `Steel` (keeps
grain.py off sweep.py; `grain→fe_c,properties` acyclic). Engine untouched, no frozen benchmark moved,
`toughness_index` untouched. **DEMO STEEL = 1018 (0.18%C) NOT 1045 (advisor):** the leaner-hypothetical
trap is a `ccurve_for_steel(Mn=0)` *kinetics* caution — 5c never calls it (only grain-growth + fe_c +
Pickering), so it doesn't bind; 1045's ~58% pearlite leans on the lone calibrated coeff (pearlite-in-yield)
AND its coupled DBTT never crosses RT (39→103°C), while **1018's ~21% pearlite puts coupled DBTT at
−43°C(900°C)→+21°C(1200°C) = CROSSES ZERO** so the ductile→brittle story lands (refine 31→8µm ferrite:
**yield 261→358 MPa(+97) while DBTT +21→−43°C(−64)**). **Figure = 3 panels:** (A) co-benefit yield↑&DBTT↓
vs d^(−½); (B) **lever comparison in the (yield,DBTT) trade-off PLANE = conscious divergence from the
plan's drafted "two panels sharing d^(−½) axis"** (the plane is where the strength-toughness front
reads — refine-grain arrow down-right vs add-pearlite/Si arrows up-right, all to the same yield; lever
endpoints exact from cited Pickering coeff ratios; plan §12 figure-desc annotated for invariant 6); (C)
overheating penalty vs austenitizing T. **NON-CIRCULARITY (as planned):** co-benefit/lever directions =
**by construction** from the two cited Pickering signs = *demonstration, NOT teeth* (Phase-4 wiring-check
status); Phase-5's only teeth stay 5a's holdout. **`yield≤UTS` = CONSISTENCY/scope-boundary NOT teeth**
(advisor — plan files it so): Pickering yield vs hardness-derived ISO-18265 UTS of the *same* FP structure
(`vickers_ferrite_pearlite`→`tensile_strength_MPa`); never bites in-window (yield≈0.48–0.66·UTS), would
fail only at **sub-micron ferrite** the austenitizing route never reaches; nan UTS (C outside 150–550 HV
band)⇒no-violation; carried as `GrainProperties.yield_below_uts`, asserted across the austenitizing range.
**PHASE 5 DONE (5a/5b/5c)** — Steel's first post-v1 phase complete. Grain *morphology* (Voronoi swatch in
notebook/app) stays the ADR-0002 viz-reach deferral, not physics. §11 menu (residual-stress / deepen-gaps /
inverse-design) stays `[available]`, appetite-driven. **DISCOVERED this session:** an unrelated **complete
but uncommitted planet-interactive-map batch** sits in the tree (`planetmap.py`/`planet_spec.py` + tests +
`planet-map.html` + README/ARCHITECTURE/pyproject `[webviz]` edits, [[planet-interactive-map-design]]/ADR
0004) — left UNTOUCHED; my steel-5c commit staged ONLY steel files. Planet README pre-wrote "468 tests/453
fast lane" which 5c's +10 makes stale → bump when planet is committed.

**SURFACED IN THE INTERACTIVE TWINS 2026-06-09 (commit 828bd05) — the "stand-in" framing above is now
scoped to MORPHOLOGY only.** 5a/5b/5c shipped grain.py + the banked `plots.grain_figure` + `demo_grain`
but left BOTH §9 surfaces still rendering the pre-Phase-5 schematic cartoon — steel.ipynb literally still
said "real grain-size physics is a future phase" (false). User caught it ("is there a meaningful/pedagogical
viz for Phase 5 in notebook & app? if not, add"). Now both carry a **§5 grain section** driving the
*validated* `grain.coupled_grain_properties` (austenitize T, hold t, C≤eutectoid, Mn, Si → PAGS+ASTM G →
ferrite → yield+DBTT) via a NEW render-layer figure **`plots.grain_interactive_figure`** (single-state,
slider companion to the fixed fine/coarse `grain_figure`): left = grain-growth kinetics + ASTM G, right =
yield↑/DBTT↓ vs austenitizing T with the **room-temperature service line** (`grain.ROOM_TEMPERATURE_C=20°C`,
a *display* constant used by NO physics fn → app.py stays matplotlib-free while sharing one value). Hook =
the **over-austenitizing penalty** (drag T up → grain coarsens → DBTT crosses RT, ductile→brittle). Thin-skin
held: figure render-layer-owned; app `grain_outcome`/`grain_readout` matplotlib/streamlit-free + always-green
tested (test_app §8, +3); steel gate fast **288→291**, full **299**. **Advisor calls baked in:** (1) the
by-construction caveat carried inline in BOTH surfaces (directions follow from the 2 cited Pickering signs =
demonstration, teeth = 5a holdout); (2) §5 = the **normalized/slow-cool ferrite-pearlite regime** with its
OWN knobs, deliberately NOT wired to the quench-medium slider (those quench→martensite which the laws nan —
the §3 isolation idiom); (3) carbon capped at eutectoid. **The §3 schematic swatch STAYS** (areas∝validated
fractions are honest), §3 captions reworded to point at §5; **DELIBERATE: the figure-baked
`microstructure_schematic` disclaimer "shapes illustrative (not a grain simulation)" LEFT as-is** — true of
the *shapes* (morphology still deferred), and baking a "§5" ref into a render primitive = layering smell.
The grain *morphology* (Voronoi swatch) remains the lone ADR-0002 viz-reach deferral. **FOLLOW-UP — DONE
(commit 3619f5e, user-directed "update docs, commit and push"):** root `README.md` reconciled once the
planet batch was already committed+pushed (tree clean, no contention) — steel.ipynb slider line now names
the austenitizing soak → grain → yield/DBTT, and the suite counts moved **470 → 474 full / 455 → 458 fast
lane** (measured by collection: +3 steel grain helpers all `not slow`, +1 planet notebook `slow`).
NOTE the surprise: my steel §5 commit 828bd05 was **already on origin/main before I pushed** — the planet
agent's `git push` carried it up (shared `main`, my commit was HEAD at push time), so on a shared branch a
co-agent's push can publish your local commits.

**PEDAGOGY DEEPENED 2026-06-09 (commit 6cdc1f0, user-directed "add intermediate/expert level, hide under
expandable sections; hide notebook code collapsed"):** added 3 collapsed-by-default expert deep-dives to
BOTH steel.ipynb & app.py — (1) **crystal structures** FCC↔BCC↔BCT (the atomic why: carbon trapped→BCT→hard,
TTT=diffusion clock), (2) **alloying-element field guide** (interstitial C/N vs substitutional Mn/Si/Cr/Mo/Ni/V,
austenite vs ferrite stabilizers, Ni-lowers/Si-raises-DBTT fork, V/Nb/Ti microalloying→grain refinement), (3)
**why grain refinement is the lone co-improver** (grain boundaries = dislocation barriers [Hall-Petch +] AND
cleavage-crack deflectors [DBTT −]). Advisor audited the metallurgy = SOUND (FCC 2.1%/BCC 0.02% match fe_c's
2.11/0.022; FCC-larger-octahedral-holes paradox resolution correct). **TWO REUSABLE NOTEBOOK TECHNIQUES:**
(a) **collapse code by default** = set `cell.metadata.jupyter.source_hidden=True` on code cells (JupyterLab-only;
GitHub web ignores it & shows code — README points to `jupyter lab` so OK); re-execution preserves the flag so
set it AFTER `NotebookClient.execute()`. (b) **renderable markdown inside a collapsible** = `<details>` /
`<summary>…</summary>` then a **BLANK LINE** before the inner markdown (and before `</details>`), else the table
renders as raw HTML — nbconvert-verified the tables render. App deep-dives = `st.expander(...)` (default
expanded=False), pure st.markdown (no new physics/tests). Advisor caught one slip: the grain deep-dive credited
a "lever/middle panel" that exists only in the banked 3-panel `grain_figure`, NOT the inline 2-panel
`grain_interactive_figure` → reworded to credit `demo_grain`. Steel gate unchanged (no new tests); root README
slider line already covers it (no doc churn needed). See [[notebook-slider-flicker]] for the sibling nb-technique.

**GRAIN-MORPHOLOGY VORONOI SWATCH BUILT 2026-06-10 — the last grain-viz deferral closed (viz-reach, NOT
physics; ADR 0002).** User picked it from the "smaller deferrals" bucket, then clarified **"keep the current
schematic, just add a new one"** — so `microstructure_schematic` (phase *fractions*) STAYS and the new swatch
ADDS the grain-size length scale it disclaims. `plots.grain_voronoi_swatch` (one ax) / `grain_swatch_figure`
(single fig) / `grain_morphology_figure` (banked fine-vs-coarse pair → `docs/figures/steel-grain-morphology.png`)
+ `demo_grain_morphology.py` (reuses `demo_grain.compute()`'s 1018 fine/coarse) + app §5
`grain_morphology_overview_figure`. **THE ONE FAITHFUL QUANTITY = grain NUMBER DENSITY (advisor):** `grain.py`
defines `N_A=1/d²` (`astm_grain_size_number`), so a field of side W holds **N=(W/d)²** grains and a Voronoi of
N seeds has mean cell area W²/N=d² — finer grain⇒MORE cells in the SAME field; cell shapes/size-spread/twins/
texture DECORATIVE (captioned, + scale bar for absolute size). Phrase the claim as "grains/area matches the
module's N_A" — it's the square-grain area=d² convention, **NOT mean-lineal-intercept** (advisor: claim no more).
**ADVISOR'S LOAD-BEARING CATCH = FIXED window:** if the window auto-scales with d the swatch always shows ~36
grains and a slider only relabels the scale bar (the size point dies in the one place it matters); so the app §5
swatch + the pair use a FIXED window (sized from the coarsest reachable grain, ~6–9 coarse cells), and `window_um=None`
auto-window (~36) is reserved for a stand-alone snapshot. Bounded cells = standard mirror-padding (reflect seeds
across 4 edges+4 corners → `scipy.spatial.Voronoi`; scipy = the core dep `solve_banded` already uses). Tests =
**plumbing/consistency NOT teeth** (ADR 0002): `test_plots_grain_swatch.py` (5: (W/d)² count monotone-in-d,
determinism, bounded geometry, pair fine>coarse) + `test_demo_grain_morphology.py` (2) + `test_app.py` (+1
fixed-field coarsening). Full gate **385→393 passed / 2 skipped**; no physics, no engine touch, every frozen
benchmark byte-identical. **NOTEBOOK §5 CELL ADDED (user picked option B after a pros/cons of A/app-only / B/clean-partial-reexec /
C/full-Run-All).** Reusable technique banked: **surgical single-cell insertion** = execute ONLY `[setup cell +
the new self-contained cell]` in a fresh kernel (`NotebookClient`, cwd=repo root so the bootstrap finds
pyproject), embed JUST that cell's output, splice into the real nb → other 37 cells **byte-identical**. The
enabler check = a **no-op `nbformat` round-trip is byte-identical** here (so write() preserves formatting; diff
= 80 insertions / 0 deletions). Match section style: set `metadata.jupyter.source_hidden=True` + `execution_count
= max(existing)+1` on the inserted code cell. Verified clean 3 ways (isolated `pytest` PASS, executor child 7.9s
rc0, the insertion's own kernel run embedded a valid PNG). **CAVEAT (now SUPERSEDED) — the `slow` notebook smoke-test
(`test_steel_notebook`) was a documented infra flake; ROOT-CAUSED + mitigated 2026-06-10** → see
[[notebook-kernel-wedge-rootcause]]: it is an upstream pyzmq/asyncio-on-Windows lost-`execute_reply`
(load-INDEPENDENT — ~24 % in bare repetition, so the "under full-suite load" wording here was wrong —
content-innocent, version-independent 3.13&3.14), now handled by **retry-on-wedge** in the test (not the
CI skip, which stays for the separate Ubuntu hang). Don't chase it as a content bug. Joins the nb-technique
toolkit ([[notebook-slider-flicker]] + collapse-code/details-blocks).
