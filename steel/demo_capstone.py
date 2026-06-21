"""The full-chain capstone: **one** ``Heat`` threaded ore → billet → part, in a single narrated run.

The integration artifact the front-end and back-end stories were each built toward (the *next-directions*
B2 thread). The repo already has every stage — F1 reduction, F2 refining + slag partition, F3 ladle trim,
F4 casting, the back-end quench — and each is sealed behind its own validation triad. But until now they
were only ever shown **independently**: :mod:`app_making` is explicit that "the stages compose by the
``Heat`` they hand on, not by a shared slider," and each stage there starts from its *own* fresh origin
(:func:`~steel.refining.from_hot_metal` preloads the alloys, :func:`~steel.ladle.from_tap` is a separate
lean origin, :func:`~steel.casting.cast_billet` emits fresh-trail heats). So no single artifact ever
carried **one** ``Heat`` — one continuous provenance trail — from the blast furnace to a finished, judged
part. This demo does, and that is its only job: **integration + pedagogy, no new physics** (it reimplements
nothing; every number comes from a sealed engine).

The thread — ore → billet → part, one Heat
------------------------------------------
1. **F1 · reduction (preamble).** Above the carbon/wüstite Ellingham crossover (read from
   :mod:`steel.reduction`, ~746 °C) the blast furnace can pull the last oxygen off the ore. Thermodynamics,
   no state to carry — so it is narrated, not threaded.
2. **F2 · the hot-metal charge** (:func:`~steel.refining.from_hot_metal`) — a carbon-saturated, **alloy-lean**
   tap seeded with the **tramp phosphorus and sulfur** real blast-furnace iron carries (that is *why* you
   refine). This is the chain origin; the trail starts here.
3. **F2 · decarburize** — blow carbon down to the grade aim (raises dissolved oxygen, C–O coupled).
4. **F2 · dephosphorize** — a basic converter slag pulls the tramp phosphorus down (oxidizing, while the
   oxygen is still high — the correct order).
5. **F2 · deoxidize** — an aluminium kill drops the dissolved oxygen and books the alumina inclusions.
6. **F2 · degas** — a deep vacuum strips hydrogen below the flaking limit (and reports nitrogen).
7. **F2 · desulfurize** — a reducing ladle slag pulls the tramp sulfur down, reading the *now-low* oxygen
   the kill left (the coupling that is why desulfurization waits for the killed ladle).
8. **F3 · trim to grade** (:func:`~steel.ladle.trim_to_grade`) — ferroalloy additions bring the lean heat
   up to the 4140 alloy window. **This step consumes the refined ``Heat`` directly** — the F2 → F3 seam
   threads with no glue.
9. **F4 · cast the billet** (:func:`~steel.casting.cast_billet`) — Chvorinov solidification + Scheil
   centerline segregation. (See *the one seam that needs glue* below.)
10. **back end · heat-treat** (:func:`~steel.heat_state.heat_treat`) — the same oil quench the whole repo
    judges parts with: does the finished section through-harden, or land a soft core?

The point — one upstream knob, the whole chain
----------------------------------------------
Two heats take the **identical** chain, differing in a *single* knob: the F2 blow endpoint. The
**reference** is blown to the grade carbon (0.40 %) and lands a **sound** part — on grade, through-hardened,
every spec cleared end to end (the chain *composes*). The **foil** is **over-blown** (0.25 %C); the carbon
is wrong from step 3, but nothing catches it until the F3 grade window (**off-grade**), and the consequence
only lands at the very last step — the section won't through-harden (**soft-core**). One mistake at the
second stage, surfaced two ways at the eighth and ninth: the longest propagation in the repo, and not a
scripted branch — the soft core is the back-end martensite fraction crossing the spec line, carried on the
same ``Heat`` that flowed down from the furnace.

What is real here vs what is scaffolding — the honesty discipline (carried from :mod:`heat_state`)
-------------------------------------------------------------------------------------------------
* **No new physics, no cited constant, no triad.** This is the spine's posture (:mod:`heat_state`): the
  demo *threads* state through engines that are already benchmarked, so its teeth are **structural**, not a
  new benchmark — the trail is one continuous, un-rewritten history; the state fields fill in the right
  order; the seeded tramp is driven below spec; the finished-part verdict falls out of the back-end physics;
  and a mistake raised upstream is present on the part. ``test_demo_capstone`` pins exactly these.
* **The knobs are a good-practice recipe, not a calibration.** Deep vacuum, basic converter slag, a proper
  aluminium kill, a reducing ladle slag — the choices a clean heat actually uses. They are *chosen* so the
  reference clears every sealed-engine spec; none is fitted.
* **The one seam that needs glue — now a public casting seam.** Casting is the lone front-end stage whose
  bare seam takes a :class:`~steel.sweep.Steel` and emits a **fresh-trail** ``Heat`` (its siblings
  :func:`~steel.refining.deoxidize`, :func:`~steel.slag.desulfurize`, :func:`~steel.ladle.trim_to_grade`
  all consume a ``Heat``). To keep one continuous trail across F4 this chain casts through
  :func:`~steel.casting.cast_billet_onto`, the ``Heat``-consuming twin that **re-bases** the nominal section
  onto the incoming ``Heat`` (a :meth:`~steel.heat_state.Heat.evolve` repack — no new physics). That seam is
  the **promotion** of this demo's original demo-local ``_cast_onto`` (next-directions B2, Option A): its
  named trigger — *a second surface needs the same glue → promote, don't duplicate* — fired when the
  ``game/`` spine was built on this chain, so the re-base now lives once, in :mod:`steel.casting`, and both
  surfaces call it.
* **Casting forks; the headline follows the nominal section.** A casting produces a nominal section *and* a
  Scheil-enriched centerline. The headline thread follows the **nominal** section to the part (apples to
  apples for the reference/foil contrast); the centerline is surfaced as the segregation read — the harder
  band the same casting feeds the back end (uneven hardenability, not a soft core).

Run headless (prints the ore → billet → part story):

    python -m steel.demo_capstone
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import casting as cast
from . import heat_state as hs
from . import ladle as ld
from . import reduction as red
from . import refining as ref
from . import slag as sl
from .heat_state import Heat
from .sweep import Steel, evaluate

# --------------------------------------------------------------------------- #
# 0. The recipe — a good-practice chain + the single knob that distinguishes the foil
# --------------------------------------------------------------------------- #
GRADE = "4140"

# The blast-furnace hot-metal backbone: alloy-LEAN (the alloys are F3's job, so the trim is meaningful)
# and seeded with the tramp phosphorus and sulfur real pig iron carries — the impurities the refining
# half exists to remove (without them dephosphorize/desulfurize would be no-ops and "we refined it" hollow).
LEAN_BACKBONE = Steel(C=0.40, Mn=0.15, Si=0.05, Cr=0.05, Mo=0.0, P=0.090, S=0.050, name=GRADE)
CHARGE_CARBON = 4.5            # carbon-saturated hot metal

# The single knob that separates the two heats: the F2 blow endpoint.
REF_CARBON = 0.40             # blown to the grade aim → a sound part
FOIL_CARBON = 0.25           # OVER-blown (decarburized too far) → off-grade on carbon + a soft core

# The good-practice refining knobs (chosen so the reference clears every sealed-engine spec, not fitted).
DEOX_LEVEL = 0.04            # aluminium kill near the Al–O minimum
DEGAS_P_H2 = 0.006           # a deep vacuum — drops hydrogen below the 2 ppm flaking limit
CONVERTER_SLAG = sl.BASIC_CONVERTER_SLAG   # basic, iron-rich → dephosphorizes
LADLE_SLAG = sl.LADLE_DESULF_SLAG          # reducing CaO–Al2O3 → desulfurizes the killed bath

# F4 / back end — the billet and the section the part is quenched as.
CAST_MODULUS = 0.025         # a 25 mm-modulus billet (sets the Chvorinov time; segregation is fs-based)
QUENCH_MEDIUM = "oil"
# A 20 mm section is chosen to *separate* the two heats at the quench: the reference through-hardens
# (~92 % martensite, clear of the 90 % spec), the over-blown foil does not (~85 %). The reference's
# margins are deterministic passes but deliberately thin — the trim dilutes carbon to ~0.388 % (just
# inside the 0.38 % floor), and a smaller section would harden the foil too, a larger one would soft-core
# the reference. The contrast, not the absolute margin, is the point.
PART_DIAMETER = 0.020

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-capstone.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-capstone.png"


# --------------------------------------------------------------------------- #
# 1. The thread — refine, trim, cast, heat-treat, all on one Heat
# --------------------------------------------------------------------------- #
def _refine(carbon_target: float) -> Heat:
    """F2 on one ``Heat``: charge → decarburize → dephosphorize → deoxidize → degas → desulfurize.

    The canonical refining order, each step a sealed seam appending to the same trail. Dephosphorization
    runs while the oxygen is still high (oxidizing); desulfurization runs after the kill (reducing, reading
    the low oxygen the deoxidation left) — the order the physics of each step expects.
    """
    heat = ref.from_hot_metal(LEAN_BACKBONE, charge_carbon=CHARGE_CARBON)
    heat = ref.decarburize(heat, carbon_target)
    heat = sl.dephosphorize(heat, CONVERTER_SLAG)
    heat = ref.deoxidize(heat, "Al", DEOX_LEVEL)
    heat = ref.degas(heat, p_H2=DEGAS_P_H2)
    heat = sl.desulfurize(heat, LADLE_SLAG)
    return heat


@dataclass(frozen=True)
class Chain:
    """One full ore → billet → part run — the threaded ``Heat`` plus the reads the figure draws.

    ``part`` is the finished, heat-treated **nominal**-section ``Heat`` (the headline thread; clean for the
    reference, off-grade + soft-core for the foil). ``part_martensite`` / ``part_HV`` are the back-end reads
    the soft-core flag was set from; ``centerline_martensite`` / ``centerline_HV`` are the same quench on the
    Scheil-enriched centerline (the segregation band the casting feeds the back end). ``p_trail`` /
    ``s_trail`` are the residual phosphorus / sulfur (wt %) at the four traced stages (charge → after
    dephos → after desulf → cast part) — the front-end impurity-removal proof. ``carbon_target`` is the
    F2 blow endpoint that distinguishes the two heats.
    """

    carbon_target: float
    part: Heat
    part_martensite: float
    part_HV: float
    centerline_martensite: float
    centerline_HV: float
    p_trail: tuple[float, ...]
    s_trail: tuple[float, ...]


def run_chain(carbon_target: float) -> Chain:
    """Thread one ``Heat`` from the hot-metal charge to a heat-treated part and capture the figure reads."""
    refined = _refine(carbon_target)
    trimmed = ld.trim_to_grade(refined, GRADE)

    # Casting is the lone front-end seam that takes a Steel; the promoted casting.cast_billet_onto re-bases
    # the nominal section onto the trimmed heat so one continuous trail threads across F4 (see *the one seam
    # that needs glue* in the module docstring). The centerline is the segregation-band read.
    section = cast.cast_billet_onto(trimmed, modulus=CAST_MODULUS)
    part = hs.heat_treat(section.nominal_heat, medium=QUENCH_MEDIUM, diameter=PART_DIAMETER)

    nom_o = evaluate(section.nominal_heat.composition, medium=QUENCH_MEDIUM, diameter=PART_DIAMETER)
    ctr_o = evaluate(section.centerline_heat.composition, medium=QUENCH_MEDIUM, diameter=PART_DIAMETER)

    # Residual P / S at the four traced stages (the refining half driving the seeded tramp below spec).
    charge = ref.from_hot_metal(LEAN_BACKBONE, charge_carbon=CHARGE_CARBON)
    after_dephos = sl.dephosphorize(
        ref.decarburize(charge, carbon_target), CONVERTER_SLAG
    )
    p_trail = (LEAN_BACKBONE.P, after_dephos.composition.P, refined.composition.P, part.composition.P)
    s_trail = (LEAN_BACKBONE.S, after_dephos.composition.S, refined.composition.S, part.composition.S)

    return Chain(
        carbon_target=carbon_target,
        part=part,
        part_martensite=nom_o.result.martensite,
        part_HV=nom_o.HV,
        centerline_martensite=ctr_o.result.martensite,
        centerline_HV=ctr_o.HV,
        p_trail=p_trail,
        s_trail=s_trail,
    )


@dataclass(frozen=True)
class CapstoneDemo:
    """What the capstone produced — the two chains plus the shared figure scalars.

    ``reference`` is the sound heat (blown to grade carbon, clean end to end); ``foil`` is the over-blown
    heat (off-grade + soft-core). ``spec`` is the through-hardening line both parts are judged against;
    ``crossover_C`` the F1 carbon/wüstite Ellingham crossover (read from the model, the reduction preamble);
    ``p_spec`` / ``s_spec`` the phosphorus / sulfur limits the refining half clears.
    """

    reference: Chain
    foil: Chain
    spec: float
    crossover_C: float
    p_spec: float
    s_spec: float


def compute() -> CapstoneDemo:
    """Run both full chains and return the heats + figure scalars — the check the whole chain composes."""
    carbon = red.REACTIONS["C->CO"]
    wustite = red.REACTIONS["Fe->FeO"]
    crossover = red.crossover_temperature(carbon, wustite)
    return CapstoneDemo(
        reference=run_chain(REF_CARBON),
        foil=run_chain(FOIL_CARBON),
        spec=hs.MIN_MARTENSITE_SPEC,
        crossover_C=float(crossover) if crossover is not None else float("nan"),
        p_spec=sl.MAX_PHOSPHORUS_PCT,
        s_spec=sl.MAX_SULFUR_PCT,
    )


# --------------------------------------------------------------------------- #
# 2. The figure — bank the integration artifact (needs the optional viz extra)
# --------------------------------------------------------------------------- #
def save_figure(demo: CapstoneDemo) -> Path:
    """Render and bank the capstone artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import capstone_figure

    fig = capstone_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


# --------------------------------------------------------------------------- #
# 3. The narrated run — the ore → billet → part story
# --------------------------------------------------------------------------- #
def _print_trail(heat: Heat) -> None:
    """Print a heat's label and its full provenance trail — one continuous history, end to end."""
    print(f"  {heat.label()}")
    for step in heat.history:
        mark = "·" if step.in_spec is None else ("✓" if step.in_spec else "✗")
        print(f"    {mark} {step.name}: {step.summary}")


def print_summary(demo: CapstoneDemo) -> None:
    """Print the capstone story — one Heat, the whole chain, a sound part and the over-blown foil."""
    ref_chain, foil = demo.reference, demo.foil

    print("\nFull-chain capstone — one Heat threaded ore → billet → part\n")
    print(f"F1 · reduction (preamble): above the carbon/wüstite Ellingham crossover ({demo.crossover_C:.0f} °C) "
          f"the furnace can pull the oxygen off the ore — ironmaking is spontaneous.\n")
    print("Then ONE Heat flows down the chain. Both heats take the identical route; only the F2 blow "
          "endpoint differs.\n")

    print(f"Reference — blown to the grade carbon ({REF_CARBON:.2f} %C):")
    _print_trail(ref_chain.part)
    print(f"    → {ref_chain.part_martensite:.0%} martensite, {ref_chain.part_HV:.0f} HV at a "
          f"Ø{PART_DIAMETER * 1000:.0f} mm oil quench — a SOUND part: on grade, through-hardened, "
          f"every spec cleared end to end.")

    print(f"\nFoil — over-blown ({FOIL_CARBON:.2f} %C, the single changed knob):")
    _print_trail(foil.part)
    print(f"    → {foil.part_martensite:.0%} martensite, {foil.part_HV:.0f} HV — a SOFT CORE "
          f"(under the {demo.spec:.0%} spec). The carbon was wrong from the blow (step 3); the grade window "
          f"caught it at the trim (off-grade), and the quench is where it finally bites.")

    print(f"\n→ One mistake at the second stage, surfaced at the eighth and ninth — {len(foil.part.history)} steps, "
          f"one un-rewritten trail. The soft core is not scripted: it is the back-end martensite fraction "
          f"crossing the spec line, carried on the same Heat that flowed down from the furnace.")

    print("\n" + "-" * 78)
    print("\nThe front end did its job — the seeded tramp driven below spec (reference heat):")
    print(f"  phosphorus  {ref_chain.p_trail[0]:.3f} → {ref_chain.p_trail[-1]:.3f} %  "
          f"(spec ≤ {demo.p_spec:.3f} %) — basic converter slag, oxidizing")
    print(f"  sulfur      {ref_chain.s_trail[0]:.3f} → {ref_chain.s_trail[-1]:.3f} %  "
          f"(spec ≤ {demo.s_spec:.3f} %) — reducing ladle slag on the killed bath")

    band = ref_chain.centerline_HV - ref_chain.part_HV
    print(f"\nCasting segregation (reference): the same billet's Scheil-enriched centerline hardens to "
          f"{ref_chain.centerline_HV:.0f} HV — a {band:+.0f} HV band the nominal section misses "
          f"(uneven hardenability the back end inherits, not a soft core).")


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ✓/✗ on legacy codepages

    demo = compute()
    print_summary(demo)
    try:
        saved = save_figure(demo)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
