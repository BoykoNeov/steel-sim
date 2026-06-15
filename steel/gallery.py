"""The gallery generator: one catalog, one clickable page, kept honest by a test.

`python -m steel.gallery` renders **docs/index.html** — a self-contained, clickable
front door to every surface of the simulator: the banked **visualizations**, the runnable
**demos**, the **experiments** (the composition x cooling sweep and the what-if app), and
the teaching **notebook**.

Why a generator and not a hand-written page? So it cannot rot. `CATALOG` below is the *single*
source of truth (topic, demo module, banked figure, where the same idea lives in the notebook
and the app, and a one-line blurb). The HTML is derived from it, the figures are referenced by
path so a re-banked PNG shows up automatically, and `steel/tests/test_gallery.py` fails the build
if a demo is added without a catalog entry, a figure goes missing, or the committed page drifts
from what this module would regenerate. To refresh after editing the catalog (or adding a demo):

    python -m steel.gallery        # rewrites docs/index.html in place

The page is **GitHub-Pages-ready** (serve from the `/docs` folder): figure `src`s are relative
(`figures/...`) so they render both on Pages and when the file is opened locally; links out to
source, the notebook, and the READMEs are absolute GitHub URLs (Pages only serves `/docs`).
This module has no third-party imports — it is pure stdlib so it runs in any checkout.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

# --- repo geography -----------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCS = _REPO_ROOT / "docs"
_FIGURES = _DOCS / "figures"
_INDEX = _DOCS / "index.html"

# Absolute GitHub base for out-links (Pages serves only /docs, so these can't be relative).
GH = "https://github.com/BoykoNeov/steel-sim/blob/main"
NOTEBOOK_URL = f"{GH}/steel/steel.ipynb"            # back-end: cooling curve → microstructure
MAKING_NOTEBOOK_URL = f"{GH}/steel/making.ipynb"    # front-end: ore → billet → and what goes wrong
ROOT_README_URL = f"{GH}/README.md"
STEEL_README_URL = f"{GH}/steel/README.md"


@dataclass(frozen=True)
class Entry:
    """One runnable surface. `module` is the `demo_*` stem under steel/ (so the run command is
    `python -m steel.<module>` and the source link is steel/<module>.py); `figure` is the banked
    PNG filename under docs/figures/; `notebook`/`app` name where the same idea lives interactively
    (None when that surface doesn't cover it)."""

    topic: str
    module: str
    figure: str
    title: str
    blurb: str
    notebook: str | None = None  # e.g. "§1-2" — links to the notebook on GitHub
    app: str | None = None  # e.g. "four fates" — text cue only (the app runs locally)


# The single source of truth. Order = the suggested learning path (it also drives the README
# "guided tour" table — keep the two consistent, but only the demo *names* are guarded by the
# test; blurb wording may differ between surfaces). Topics are emitted as section headers in order.
CATALOG: tuple[Entry, ...] = (
    Entry(
        "Core", "demo_four_curves", "steel-four-curves.png",
        "Four fates of one steel",
        "One 1080 steel, four quench rates → pearlite → bainite → martensite "
        "— the C-curve mechanism beside the microstructure it produces.",
        notebook="§1-2", app="four fates",
    ),
    Entry(
        "Core", "demo_sweep", "steel-sweep.png",
        "Composition × cooling sweep  —  the experiment surface",
        "Every composition against every cooling rate, side by side — the hardenability "
        "axis the four-curves view can't show. This is the experimentation surface; the app makes "
        "it interactive.",
        notebook="§3", app="grid / build-your-own",
    ),
    Entry(
        "Hardenability", "demo_jominy", "steel-jominy-hardness.png",
        "Jominy end-quench",
        "One end-quench bar: shallow-hardening 1045 against deep-hardening 4140, hardness versus "
        "depth from the quenched end.",
        notebook="§3", app="Jominy",
    ),
    Entry(
        "Hardenability", "demo_ideal_diameter", "steel-ideal-diameter.png",
        "Ideal critical diameter",
        "Critical diameter read *from* the model against measured H-band data — does it rank "
        "the steels' hardenability in the right order?",
        notebook="§3",
    ),
    Entry(
        "Tempering", "demo_tempered_jominy", "steel-tempered-jominy.png",
        "Tempered Jominy traverse",
        "A *tempered* Jominy traverse — per-constituent temper of a mixed structure, not a "
        "single hardness knocked down by one number.",
        notebook="§4", app="quench-and-temper",
    ),
    Entry(
        "Grain size", "demo_grain", "steel-grain.png",
        "Grain refinement",
        "Grain refinement — the lone lever that raises strength *and* toughness at once "
        "(same Hall–Petch form, opposite grain-size signs).",
        notebook="§5", app="§5",
    ),
    Entry(
        "Grain size", "demo_grain_morphology", "steel-grain-morphology.png",
        "Grain morphology swatch",
        "Those two grains drawn to scale — a size-accurate microstructure swatch beside the "
        "schematic.",
        notebook="§5", app="§5",
    ),
    Entry(
        "Process routes", "demo_austemper", "steel-austemper.png",
        "Austempering",
        "Quench past the nose, hold isothermally inside the diagram, grow bainite — the "
        "atlas-anchored isothermal hold.",
        notebook="§6", app="§6",
    ),
    Entry(
        "Process routes", "demo_martemper", "steel-martemper-distortion.png",
        "Martempering",
        "The same hardness as a direct quench, far less distortion — the surface−centre "
        "temperature gap closed before the martensite forms.",
        notebook="§6d", app="martempering",
    ),
    Entry(
        "Process routes", "demo_unified_kv", "steel-unified-kv-bay.png",
        "Bainite bay, opened in continuous cooling",
        "The bainite bay *opened* in continuous cooling — three competing reactions "
        "(ferrite / pearlite / bainite) raced on one shared austenite pool.",
        notebook="§6b", app="§6b",
    ),
    Entry(
        "Process routes", "demo_bainite", "steel-bainite.png",
        "Bainite reaction (the negative result)",
        "The cited bainite reaction on its own, and why its bay *can't* form in a plain continuous "
        "cool — the negative-result companion to the unified model.",
    ),
    Entry(
        "Validation", "demo_cct_validation", "steel-cct-validation.png",
        "Cross-composition bainite wall, measured",
        "Does any cited composition factor predict bainite kinetics *across* steels? Eight atlas "
        "steels say no — the per-steel-only wall, measured and quantified (not just asserted), and "
        "the alloy-vs-carbon diagnosis behind it.",
        notebook="§6c",
    ),
    Entry(
        "Stress", "demo_residual", "steel-residual-stress.png",
        "Residual stress & distortion",
        "The residual stress and distortion a quench locks into a section — the "
        "solid-mechanics axis (incremental elastic–perfectly-plastic, transform dilatation "
        "and all).",
        notebook="§6e", app="residual stress",
    ),
    Entry(
        "Case hardening", "demo_carburize", "steel-carburize-gradient.png",
        "Carburizing",
        "A carburized gear tooth: carbon diffused in at the surface, case hardness profiled out "
        "— the same sealed engine as Jominy, a mass-diffusion face.",
        notebook="§8", app="carburizing",
    ),
    Entry(
        "Inverse design", "demo_design", "steel-design.png",
        "Inverse design",
        "Run the simulator backwards: name a target hardness, get a feasible recipe — grade, "
        "quench medium, and temper.",
        notebook="§7", app="§7",
    ),
    Entry(
        "Equilibrium", "demo_calphad", "steel-calphad.png",
        "CALPHAD equilibrium",
        "Real CALPHAD thermodynamics against the parametrised Fe-C diagram the rest of the sim "
        "uses (needs the optional `.[calphad]` extra).",
    ),
    Entry(
        "Ironmaking (front-end)", "demo_reduction", "steel-ellingham.png",
        "Ellingham diagram — ore → iron",
        "The front end begins: which reductant pulls the oxygen off which oxide, above which "
        "temperature. The carbon→CO line dives under the iron-oxide lines at ~750 °C — where "
        "ironmaking begins — and the oxygen-potential ladder shows why Al and Ca deoxidize a "
        "steel bath that Fe, Mn, Si cannot.",
        notebook="§F1",
    ),
    Entry(
        "Front-end spine", "demo_heat_state", "steel-heat-state.png",
        "Failure propagation — a mistake travels down the chain",
        "The spine that lets steps compose: a Heat record threads through the back end, and an "
        "upstream alloy mistake (under-dosed Cr/Mo) propagates into a downstream defect — the same "
        "oil quench that through-hardens a proper 4140 leaves a soft, ferrite-dominant core, "
        "flagged on the Heat. Not a scripted failure — the back-end martensite fraction crossing a "
        "spec line.",
        notebook="§spine",
    ),
    Entry(
        "Refining (front-end)", "demo_refining", "steel-refining.png",
        "Primary refining — the blow sets carbon, the gas fields fill",
        "The middle of the chain: blow carbon-saturated hot metal to the grade's carbon, kill it with "
        "aluminium, vacuum-degas. The blow's carbon is the one output the validated back end consumes — "
        "over-blow and the same quench leaves a soft core (a real refining mistake, a real downstream "
        "consequence). Alongside, the dissolved O / H / N and inclusion fields the Heat carried empty are "
        "filled: the deoxidation curve with its minimum, the C–O coupling, and Sieverts √p degassing.",
        notebook="§F2a",
    ),
    Entry(
        "Refining (front-end)", "demo_slag", "steel-slag.png",
        "Slag partition — phosphorus out in the converter, sulfur in the ladle",
        "The second half of refining: the two tramp impurities the blast furnace leaves in, partitioned into "
        "slag. The headline is the opposite oxygen dependence — dephosphorization wants the oxidizing "
        "converter (L_P rises with slag FeO), desulfurization wants the reducing ladle (L_S falls with "
        "dissolved oxygen) — two independently sourced correlations whose opposite signs dictate the process "
        "order. It reproduces the purity-control history: acid Bessemer can't dephosphorize (rails crack), "
        "Thomas' basic lining can, and sulfur only comes out once the heat is killed. P/S are carried but "
        "inert in the back end — the chemistry is benchmarked, the embrittlement consequence deferred.",
        notebook="§F2b",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_impurity_window", "steel-impurity-window.png",
        "Closing the impurity consequences — phosphorus (cold-short) and sulfur (red-short)",
        "What the tramp impurities finally DO. The same high-phosphorus, sulfurous pig iron, made into "
        "cracking steel by the acid Bessemer process and into sound steel by the basic process + Mushet's "
        "manganese + ladle desulfurization. Phosphorus threads the existing Pickering DBTT law (it "
        "strengthens AND embrittles — the signed foil) so the off-spec heat is brittle in the hand; free "
        "sulfur forms a Fe–FeS grain-boundary film above the 988 °C eutectic so it tears when forged "
        "(Mushet's manganese ties it as benign MnS). Together they bracket the workable temperature "
        "window — the consequence F2's slag partition set as state, now closed: phosphorus by propagation "
        "through the toughness law, sulfur through a new hot-working verdict.",
        notebook="§D1",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_temper_embrittlement", "steel-temper-embrittlement.png",
        "Temper embrittlement — the reversible Ni-Cr-Mo phosphorus trap",
        "Phosphorus' OTHER consequence — the quench-and-tempered (martensitic) path, completing its coverage "
        "(cold-short was the ferritic one). A dirty Ni-Cr forging with residual phosphorus and no molybdenum, "
        "slow-cooled through ~375–575 °C, segregates phosphorus to the prior-austenite grain boundaries and "
        "fractures intergranularly. Four independent cures: a fast cool through the window, molybdenum (the "
        "classic remedy for susceptible Ni-Cr forgings), a clean heat, or a reheat above 600 °C (the "
        "reversibility that names it). The Watanabe J-factor ranks susceptibility — in the registry only the "
        "dirty Ni-Cr victim clears the threshold; 4140/8620 are safe by low J, not their sub-threshold Mo. No "
        "strict tooth — the segregation-C-curve-nose gate was run on paper and could not be pinned (a "
        "tractable model is ~100× too fast and underdetermined; the faithful nose needs Fe₃P-cluster "
        "kinetics, out of scope), so the model was not built to manufacture one.",
        notebook="§D2",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_tempered_martensite_embrittlement",
        "steel-tempered-martensite-embrittlement.png",
        "Tempered-martensite embrittlement — the other trough, irreversible",
        "Reversible temper embrittlement has a sibling on the SAME tempering axis — and the two are opposites. "
        "Temper as-quenched martensite in 260–370 °C and cementite precipitates as films along the interlath / "
        "grain boundaries (fed by retained-austenite decomposition); toughness drops into a trough. It is "
        "carbon-driven, not impurity-driven — so a *clean* medium-carbon steel still embrittles, where the "
        "reversible one needs phosphorus — and it is ONE-WAY: temper above ~400 °C and it recovers, but "
        "re-entering the trough cannot restore the film (the carbide morphology is set by the peak temper). Two "
        "gates, on the same frozen quench the spine uses: 4140 embrittles, 8620 (0.20 %C) is immune even fully "
        "hardened, and a section that did not harden has no tempered martensite to embrittle. No strict tooth — "
        "the trough-from-carbide-kinetics gate was run on paper and failed (the repo carries no stage-III "
        "carbide thermodynamics), so no carbide model was built to manufacture one; the trough window and the "
        "~400 °C recovery are cited, the carbon gate and verdict rule by-construction.",
        notebook="§D3",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_hydrogen_flaking", "steel-hydrogen-flaking.png",
        "Hydrogen flaking — same ladle hydrogen, the section decides",
        "What dissolved hydrogen finally does — and why it is a *geometric* consequence, not a number. "
        "Refining fills the ladle hydrogen and flags the chemistry-state risk; whether a *part* flakes "
        "(internal hairline cracks) is set by whether the hydrogen can diffuse out before the section cools "
        "into the brittle range. Same 4140 heat at ~3.6 ppm, two sections, same dehydrogenation bake: the "
        "thin section degasses and is sound, the thick one traps it and flakes — and a long enough bake saves "
        "the thick one (the time scales as section²). Two-tier, like cold-short/red-short: refining sets the "
        "risk, this the consequence. Closed-form slab desorption (Crank) — no engine, no ADR. One genuine "
        "tooth: the bake time from an independently-pinned lattice D_H reproduces cited practice without "
        "tuning — a 500 mm forging → ~10 days (heavy forgings → days, the load-bearing anchor; the 1 h/inch "
        "thin-section rule is OoM sanity only) — OoM-grade; the L² scaling and verdict are by-construction.",
        notebook="§D4",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_gas_porosity", "steel-gas-porosity.png",
        "Gas (CO) porosity — same oxygen spec, the carbon decides",
        "What dissolved oxygen finally does — and why it is a *carbon-aware* consequence, not a single number. "
        "Refining flags a carbon-blind risk (O > 30 ppm); whether a *casting* blows CO holes is set by the "
        "carbon the oxygen reacts with: gas evolves where [%C]·[%O] crosses the same CO equilibrium the "
        "converter runs on. Same light kill, two carbons, both within the 30 ppm spec: the high-carbon 1080 "
        "sits right on the CO line (limit ~25 ppm) and blows holes — carrying *less* oxygen than the sound "
        "low-carbon 8620 (limit ~100 ppm). A full kill saves it (the deox lever). Two-tier, like "
        "cold-short/red-short/flaking: refining sets the risk, this the consequence — and the two disagree "
        "because of carbon. No engine, no ADR, and honestly **no claimable tooth** (the criterion is the "
        "cited C–O equilibrium against held composition); the soft OoM note is 'high-C must be killed, low-C "
        "can be rimmed' from O_crit ∝ 1/C, no tuning. The solidification CO-margin is a conservative "
        "secondary (Scheil over-predicts carbon), not the verdict.",
        notebook="§D5",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_hot_tear", "steel-hot-tear.png",
        "Hot-tearing — same sulfur, the Mn:S decides (segregation)",
        "What residual sulfur does at the *casting* stage — the segregation-amplified sibling of forging-stage "
        "red-shortness. Slag flags a flat, Mn-blind risk (S > 0.040 %); whether a *casting* grows a Fe–FeS "
        "interdendritic film and hot-tears is set by the Mn:S in the **last liquid to freeze**, which is "
        "Scheil-enriched — sulfur piles up ~10× faster than manganese, so the film Mn:S is ~10× poorer than "
        "the bath. Two heats, same sulfur (both within spec, both clearing bulk MnS stoichiometry): the "
        "lower-Mn one (Mn:S 10) tears because its film falls to ~1.2, the higher-Mn one (Mn:S 22) stays sound "
        "— the Mushet lever again, only the threshold is in the *tens*. Distinct from red-short by **phase + "
        "time** (interdendritic liquid during freezing vs bulk solid at the forge — castability ≠ "
        "forgeability), not duplicated. No engine, no ADR, and **no claimable tooth** (the verdict is cited "
        "Scheil partition feeding cited MnS stoichiometry); the soft OoM note is that segregation amplifies "
        "the stoichiometric 1.71 into the tens — reproducing the empirical 'castings need Mn:S ≳ 20' rule "
        "(Toledo 1993) with no tuning, order-robust but cutoff-tuned. The RDG/feeding driver and the "
        "carbon-peritectic contribution are named deferrals.",
        notebook="§D6",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_sulfide_morphology", "steel-sulfide-morphology.png",
        "MnS morphology — the signed sulfur foil (same MnS, asset and liability)",
        "The same manganese sulfide is signed: a deliberate **free-machining** asset (the reason the "
        "resulfurized 11xx grades exist — MnS breaks the chip) *and* an unintended **through-thickness "
        "toughness** liability (hot working elongates the plastic MnS into stringers that gut the "
        "short-transverse direction). Slag raises one flat, shape-blind `high-sulfur` risk (S > 0.040 %) that "
        "fires on every free-machining grade by design; this **splits** it into its good and bad halves. The "
        "hero: one resulfurized 1144-type heat read two ways — as-rolled it is free-machining **and** "
        "anisotropic; a calcium treatment globularizes the MnS and it is free-machining **and** isotropic, the "
        "same sulfur, the same MnS *volume* — only the shape changed (the lever is the shape, not the sulfur, "
        "which is why the anisotropy flag is gated on **morphology**, never an S-threshold). A plain low-S heat "
        "is tough but cannot free-machine — the other end of the trade. The worked-product sibling of "
        "forging-stage red-shortness (it reads the *tied* MnS, where red-short reads the *free* sulfur). No "
        "engine, no ADR, and **no claimable tooth**: the MnS amount is cited stoichiometry, its volume a cited "
        "density ratio, the two verdicts by-construction; 'one MnS, two opposite signs' is the pedagogical "
        "point, by construction. The machinability index is the MnS contribution only (hardness/carbon and "
        "Pb/Ca/Te confound the real rating); the transverse debit is its own directional axis (not the hardness "
        "toughness proxy or DBTT). Stringer aspect ratio (∝ rolling reduction) is a named ceiling.",
    ),
    Entry(
        "Impurity consequences (front-end)", "demo_wootz", "steel-wootz.png",
        "Wootz / Damascus carbide banding — the signed good-impurity foil",
        "The mirror image of every other impurity story: the watered Damascus pattern needs a trace "
        "carbide-forming **\"impurity\"** — chiefly **vanadium** — that a modern clean-steel spec would reject as "
        "off-spec pickup, yet the wootz smith *requires*. So \"bad steel\" and \"good steel\" are the same "
        "statement, signed either way — the one genuine front-end physics gap (`steel-making.md` §14.5 / §15.4), "
        "now filled. The carbide banding develops only through **three gates, all required** (Verhoeven & Pendray "
        "1998): **hypereutectoid carbon** (~1.5 %, so a proeutectoid Fe₃C network exists to band — `fe_c` lever "
        "rule); a **trace former above threshold** (**V ≥ 40 ppm**, or the weaker Mn ≥ 200 ppm); and **cyclic "
        "forging 50–100 °C below A_cm** (the cementite solvus — forge hotter and it dissolves). The hero: the "
        "*same* 1.5 %C steel forged the *same* way — the V-bearing cake waters into Damascus; the clean modern "
        "twin, forged identically, comes out plain and raises **`wootz-pattern-failed`** (\"the smith did "
        "everything right; the ore lacked the vanadium\"). A plain bar never forged as wootz raises no flag — the "
        "flag is gated on **intent**. The reuse beat: the interdendritic former enrichment that aligns the bands "
        "is the *same* Scheil solid-segregation ratio (`casting.segregation_ratio`) that makes centerline "
        "segregation a hardenability *defect* — one engine, two signs (γ coefficients, since hypereutectoid wootz "
        "solidifies as primary austenite). No engine, no ADR, and **no claimable tooth**: the three gates are "
        "cited threshold lines, the cementite is `fe_c`'s lever rule, the enrichment is `casting`'s Scheil. The "
        "band spacing (30–70 µm) is a **cited observation** (it traces the interdendritic spacing), **not** "
        "computed — that would be a manufactured coherence (cake modulus, Chvorinov B, and the SDAS law are all "
        "soft knobs aimed at a 2×-wide target). The enrichment ratio is representative (the pinned Mo former as "
        "the exemplar). The verdict is yes/no, not a rendered etch — a named ceiling.",
    ),
    Entry(
        "Ladle trim (front-end)", "demo_ladle", "steel-ladle.png",
        "Alloy to grade — where the composition is finalized (and missed)",
        "The seam to the back end: trim an alloy-lean tap up to a grade by ferroalloy additions, sized for "
        "an assumed recovery. A bath that under-delivers (Cr/Mo recovery halved) lands below the cited 4140 "
        "window — F3 flags off-grade — and the same oil quench that through-hardens the on-grade heat leaves "
        "a soft core. One ladle mistake, two flags: the front-end early warning and the validated back-end "
        "consequence — the hero-demo's off-spec input, produced rather than hand-set.",
        notebook="§F3",
    ),
    Entry(
        "Ladle trim (front-end)", "demo_carbon_carry_in", "steel-carbon-carry-in.png",
        "Carbon carry-in — same trim, the ferroalloy carbon grade decides",
        "A *second* ladle mistake beside the recovery shortfall: the carbon the ferroalloys carry. One "
        "alloy-lean 4140 tap, one set of charges sized to reach grade (identical assay/recovery either way) — "
        "but mixed in with cheap high-carbon (charge-grade) ferrochrome/ferromanganese (6–8 % C) the bath "
        "picks up ~+0.18 %C and lands at ~0.56 %C, **off-grade on its own carbon band** and a harder steel "
        "(~700 HV vs the on-grade ~625). The refined low-carbon grades carry the same trim without the "
        "pickup — *this is why low-carbon ferroalloys exist*. The verdict is off-grade fired on the carbon "
        "band through the same window machinery (no new flag); the hardness rise is the validated back end "
        "consuming the carry-in carbon — propagation colour, not a second pass/fail line. No engine, no ADR, "
        "and **no claimable tooth** (mass-balance on cited assays); the ~40 %-of-the-grade's-carbon magnitude "
        "is an order-of-magnitude coherence note. Carbon recovery taken ~full; deox-state-dependent recovery is "
        "now its own panel (next); P/S bands stay deferred.",
    ),
    Entry(
        "Ladle trim (front-end)", "demo_deox_recovery", "steel-deox-recovery.png",
        "The F2→F3 seam — dissolved oxygen taxes the oxidizable trim",
        "The seam that closes the ladle module's last named deferral: where demo_ladle *hand-set* the recovery "
        "shortfall and demo_carbon_carry_in turned on the ferroalloy carbon, this one turns on F2's **deox "
        "state**. Trim the same charges into a well-killed bath (Al-killed, O ~4 ppm) and Mn/Si recover in full; "
        "trim them into an under-killed one (a weak, insufficient kill — O ~53 ppm, **porosity-risk**) and the "
        "dissolved oxygen ties up a stoichiometric mass of the oxidizable additions as oxide, so Mn/Si land "
        "short — while the noble Cr/Mo/Ni land identically (**selectivity**: the tax falls only on the alloys "
        "that deoxidize). The magnitude is honest and **modest** — even a fully under-killed bath taxes Mn only "
        "~2 % at 4140's carbon (~4 % at 8620's lower carbon, which sits at higher dissolved O), so the landed Mn "
        "dips but stays *in-window*: the dissolved-O coupling alone cannot trip off-grade — quantitatively why "
        "demo_ladle's gross under-trim hero must be hand-set. The carbon→oxygen→tax coherence ties F2's C–O "
        "coupling straight into F3 recovery (kill-before-you-trim matters most where carbon is lowest). No "
        "engine, no ADR, and **no claimable tooth** (conservation arithmetic on cited oxide stoichiometry; the "
        "gross slag-FeO reoxidation distribution is the named ceiling). The only flag is F2's porosity-risk.",
    ),
    Entry(
        "Casting (front-end)", "demo_casting", "steel-casting.png",
        "Casting & solidification — segregation runs front-to-back",
        "The chain closes front-to-back: cast a billet and Scheil microsegregation enriches the "
        "last-to-freeze centerline (S, P, C the worst), so the *same* casting heat-treats "
        "non-uniformly — the enriched centerline over-hardens into a hard band the bulk never "
        "reaches. A real front-end engine produces the Heat the validated back end consumes. "
        "Chvorinov solidification time alongside.",
        notebook="§F4a",
    ),
    Entry(
        "Casting (front-end)", "demo_solidification", "steel-solidification.png",
        "Solidification map & casting defects — validated against Stefan",
        "Casting's deferred half (F4 Slice 2): the latent-heat temperature field of a section freezing "
        "against a chill, solved on the *same sealed heat engine* (enthalpy method, no engine touch). The "
        "iconic solidification map, the latent-heat arrest at the thermal centre, and — the headline tooth "
        "— the numerical freezing front *converging to the analytic one-phase Stefan closed form* "
        "2λ√(αt) under grid refinement, conservation exact. The insulated centre freezes last (the "
        "shrinkage hot spot — the same centerline Slice 1 enriches); the cited Niyama criterion collapses "
        "there. Stefan match is the validated tooth; the Niyama/hot-spot reads are by-construction.",
        notebook="§F4b",
    ),
    Entry(
        "Casting (front-end)", "demo_peritectic", "steel-peritectic.png",
        "Peritectic surface cracking — carbon decides, non-monotonically",
        "The carbon-driven sibling of sulfur hot-tearing: the peritectic transformation L + δ → γ is a "
        "BCC→FCC volume contraction that, concentrated high in the continuous-casting mould, shrinks the thin "
        "shell off the wall into longitudinal facial cracks — so the hypo-peritectic ~0.10–0.16 %C grades are "
        "the worst surface-crackers, and counter-intuitively a *leaner* OR a *richer* steel casts more "
        "soundly. Three plain-carbon heats, carbon the only axis: 0.05 %C (fully δ, sound), 0.11 %C (Wolf's "
        "ferrite potential in the depression band, cracks), 0.45 %C (austenitic, sound) — *more carbon is "
        "safer*. The verdict is Wolf's cited FP = 2.5(0.5 − Cp) band (0.8–1.05); the mechanism is the Fe–C "
        "peritectic lever rule (cited invariants 0.09/0.17/0.53 at 1495 °C, by construction). Reads NOMINAL "
        "carbon (the shell phenomenon), the *reverse* of hot-tear's last-liquid read. A second lever: same "
        "0.20 %C, ferrite stabilizers (Si+Cr) pull Cp into the band — alloying decides. No engine, no ADR, and "
        "**no claimable tooth** (cited classifier + by-construction lever); the soft note is a coherence "
        "(carefully *not* independent — both rest on the Fe–C peritectic): the lever rule and Wolf's empirical "
        "FP place the trouble at the same ~0.1 %C window. The consumed-δ peaks at the band edge (Cγ 0.17), not "
        "the empirical worst — the exact worst-carbon needs δ→γ kinetics + shell mechanics (underdetermined).",
    ),
)


# --- rendering ----------------------------------------------------------------------------
_CSS = """\
:root {
  --bg: #0f1115; --panel: #171a21; --panel2: #1d2129; --ink: #e7e9ee; --muted: #9aa3b2;
  --line: #2a2f3a; --accent: #ff8a3d; --accent2: #5ab0ff; --code: #0b0d11;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent2); text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 32px 20px 64px; }
header h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: -0.01em; }
header .tag { color: var(--muted); margin: 0 0 22px; font-size: 16px; }
.ways { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;
        margin: 0 0 14px; }
.way { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.way h3 { margin: 0 0 4px; font-size: 15px; }
.way p { margin: 0; color: var(--muted); font-size: 13.5px; }
code, .cmd { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.cmd { display: block; background: var(--code); border: 1px solid var(--line); border-radius: 8px;
       padding: 7px 10px; font-size: 13px; color: #cfe3ff; overflow-x: auto; }
.note { color: var(--muted); font-size: 13.5px; margin: 6px 0 26px; }
h2.section { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent);
             border-bottom: 1px solid var(--line); padding-bottom: 6px; margin: 34px 0 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 18px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
        display: flex; flex-direction: column; transition: border-color .15s, transform .15s; }
.card:hover { border-color: #3a4150; transform: translateY(-2px); }
.card .shot { display: block; background: var(--panel2); border-bottom: 1px solid var(--line); }
.card .shot img { display: block; width: 100%; height: 188px; object-fit: contain; background: #fff; }
.card .body { padding: 13px 15px 15px; display: flex; flex-direction: column; gap: 9px; flex: 1; }
.card h3 { margin: 0; font-size: 17px; }
.card .blurb { margin: 0; color: var(--muted); font-size: 13.5px; flex: 1; }
.card .links { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 13px; padding-top: 2px;
               border-top: 1px solid var(--line); margin-top: 2px; }
.card .links .sep { color: var(--line); }
.chip { display: inline-block; font-size: 11px; color: var(--muted); border: 1px solid var(--line);
        border-radius: 999px; padding: 1px 8px; }
footer { color: var(--muted); font-size: 13px; margin-top: 44px; border-top: 1px solid var(--line);
         padding-top: 18px; }
em { color: #c8cee0; font-style: italic; }
"""


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _card_html(e: Entry) -> str:
    fig_rel = f"figures/{e.figure}"
    src = f"{GH}/steel/{e.module}.py"
    links = [
        f'<a href="{fig_rel}" target="_blank" rel="noopener">figure ↗</a>',
        f'<a href="{src}" target="_blank" rel="noopener">source ↗</a>',
    ]
    if e.notebook:
        # Front-end topics (all tagged "(front-end)" / "Front-end spine") live in the making
        # notebook; everything else in the back-end one — so a §-link lands in the right notebook.
        nb_url = MAKING_NOTEBOOK_URL if "front-end" in e.topic.lower() else NOTEBOOK_URL
        links.append(
            f'<a href="{nb_url}" target="_blank" rel="noopener">notebook {_esc(e.notebook)} ↗</a>'
        )
    if e.app:
        links.append(f'<span class="chip">app: {_esc(e.app)}</span>')
    links_html = '<span class="sep">|</span>'.join(links)
    return (
        '    <article class="card">\n'
        f'      <a class="shot" href="{fig_rel}" target="_blank" rel="noopener">'
        f'<img src="{fig_rel}" alt="{_esc(e.title)}" loading="lazy"></a>\n'
        '      <div class="body">\n'
        f'        <h3>{_esc(e.title)}</h3>\n'
        f'        <p class="blurb">{_esc(e.blurb)}</p>\n'
        f'        <code class="cmd">python -m steel.{e.module}</code>\n'
        f'        <div class="links">{links_html}</div>\n'
        '      </div>\n'
        '    </article>'
    )


def _sections_html() -> str:
    out: list[str] = []
    current: str | None = None
    for e in CATALOG:
        if e.topic != current:
            if current is not None:
                out.append("  </div>")  # close previous grid
            out.append(f'  <h2 class="section">{_esc(e.topic)}</h2>')
            out.append('  <div class="grid">')
            current = e.topic
        out.append(_card_html(e))
    if current is not None:
        out.append("  </div>")
    return "\n".join(out)


def render_html() -> str:
    """Render the full index page as a string. Deterministic (no timestamps) so the drift test
    can byte-compare it against the committed file."""
    ways = (
        '  <div class="ways">\n'
        '    <div class="way"><h3>▶ Demos &amp; visualizations</h3>'
        '<p>Each card runs one <code>python -m steel.&lt;name&gt;</code> demo, prints its validation '
        'table, and banks the figure shown. Needs only <code>.[viz]</code>.</p></div>\n'
        f'    <div class="way"><h3>\U0001f9ea Experiments</h3>'
        '<p>The <strong>composition × cooling sweep</strong> below, the back-end interactive '
        '<strong>what-if app</strong> (<code>streamlit run steel/app.py</code>) — pick a grade, '
        'quench, and section size and watch the microstructure move — its front-end '
        '<strong>ore→billet twin</strong> (<code>streamlit run steel/app_making.py</code>), and the '
        '<strong>defect-consequences</strong> app '
        '(<code>streamlit run steel/app_consequences.py</code>).</p></div>\n'
        f'    <div class="way"><h3>\U0001f4d3 Notebooks</h3>'
        f'<p>Two narrative teaching paths with sliders. New here? Open the back-end '
        f'<a href="{NOTEBOOK_URL}" target="_blank" rel="noopener">notebook</a> '
        '(cooling curve → microstructure), read "Start here — the 30-second mental model", then go '
        f'top to bottom — or its front-end '
        f'<a href="{MAKING_NOTEBOOK_URL}" target="_blank" rel="noopener">making notebook</a> '
        '(ore → billet → and what goes wrong).</p></div>\n'
        '  </div>'
    )
    body = (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <title>steel-sim — visual gallery &amp; guided tour</title>\n'
        f'  <style>\n{_CSS}  </style>\n'
        '</head>\n'
        '<body>\n'
        '  <div class="wrap">\n'
        '  <header>\n'
        '    <h1>steel-sim — visual gallery &amp; guided tour</h1>\n'
        '    <p class="tag">Composition + cooling in, microstructure and properties out. '
        'Click any card to open its figure full-size, or copy its run command. '
        'Every surface of the simulator — visualizations, demos, experiments, and the '
        'notebook — in one place.</p>\n'
        '  </header>\n'
        f'{ways}\n'
        '  <p class="note">Suggested first pass: '
        '<code>demo_four_curves</code> → <code>demo_jominy</code> → '
        '<code>demo_sweep</code> → <code>demo_tempered_jominy</code>, then branch by interest. '
        'Install &amp; launch commands are in the '
        f'<a href="{ROOT_README_URL}" target="_blank" rel="noopener">README</a>; the physics and '
        f'validation behind each demo are in '
        f'<a href="{STEEL_README_URL}" target="_blank" rel="noopener">steel/README.md</a>.</p>\n'
        f'{_sections_html()}\n'
        '  <footer>\n'
        '    This page is generated by <code>python -m steel.gallery</code> from a single catalog '
        'in <code>steel/gallery.py</code>, and a test (<code>test_gallery.py</code>) fails the build '
        'if it drifts — add a demo and its figure, regenerate, and it appears here automatically. '
        f'&nbsp;·&nbsp; <a href="{ROOT_README_URL}" target="_blank" rel="noopener">README</a> '
        f'&nbsp;·&nbsp; <a href="{NOTEBOOK_URL}" target="_blank" rel="noopener">notebook</a> '
        f'&nbsp;·&nbsp; <a href="{MAKING_NOTEBOOK_URL}" target="_blank" rel="noopener">making notebook</a> '
        f'&nbsp;·&nbsp; <a href="https://github.com/BoykoNeov/steel-sim" target="_blank" '
        'rel="noopener">repository</a>\n'
        '  </footer>\n'
        '  </div>\n'
        '</body>\n'
        '</html>\n'
    )
    return body


def write_index(path: Path = _INDEX) -> Path:
    """Write the rendered page to `path` with LF newlines (so the byte-compare test is stable on
    Windows + autocrlf). Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(), encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    written = write_index()
    print(f"wrote {written.relative_to(_REPO_ROOT)}  ({len(CATALOG)} entries)")
