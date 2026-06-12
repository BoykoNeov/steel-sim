"""The F-spine anchor demo: a ``Heat`` flows through the chain and an upstream mistake *propagates*.

*Composition in, a flagged part out.* This is the demonstrable artifact for the front-end **spine**
(``docs/plans/steel-making.md`` §5, build-order item 2): not a new physics phase but a proof that the
:class:`~steel.heat_state.Heat` record + the thin orchestrator seam let a step **compose** and a failure
**propagate** — the mechanic the whole gamified chain rests on.

What it shows
-------------
1. **The general failure-propagation proof (the headline, runs for any composition).** Two 4140 heats —
   one properly dosed, one with Cr/Mo under-dosed upstream (the ``steel-making.md`` §6 canonical cause) —
   take the *same* oil quench through :func:`~steel.heat_state.heat_treat`. The well-dosed heat
   through-hardens (~96 % martensite); the under-dosed heat lands a soft, ferrite-dominant core (~40 %)
   and the **soft-core** flag is raised on it — straight out of the back-end physics crossing the
   :data:`~steel.heat_state.MIN_MARTENSITE_SPEC` line, no scripted failure branch. Each heat's provenance
   trail names the step where it went off spec.

2. **The fixed atlas-steel quench-crack illustration (the same seam, a second engine, honestly bounded).**
   A 4340 heat is run through :func:`~steel.heat_state.quench_crack_check`, which repacks the §18
   residual-stress solve into the ``Heat``: the surface locks into tension → the **quench-crack-risk**
   flag. This is **not** the off-spec-composition → crack chain (the §18 engine is atlas-anchored to a
   *grade*, not a composition — that chain is deferred, ``steel-making.md`` §6); it shows the orchestrator
   pattern generalising across engines.

The posture (carried from :mod:`heat_state`): the spine adds **no physics** — it threads state through
already-benchmarked engines — so its tests are *seam correctness* (round-trip, immutability, propagation),
not a new benchmark. It is a text/structural artifact: no figure is forced on an architecture seam.

Run headless (prints the propagation story):

    python -m steel.demo_heat_state
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import heat_state as hs
from .heat_state import Heat
from .sweep import Steel, evaluate

# The worked alloy-dosing mistake — under-dose Cr/Mo on a 4140 (Mn kept on-spec, so the only
# difference is the deep-hardening alloy the back end reads as a τ-shift; steel-making.md §6).
WELL_DOSED_GRADE = "4140"
UNDER_DOSED = Steel(C=0.40, Mn=0.90, Si=0.25, Cr=0.10, Mo=0.0, name="4140 (under-dosed Cr/Mo)")

# The shared quench — the same treatment both heats see, so the divergence is the composition's.
QUENCH_MEDIUM = "oil"
SECTION_M = 0.010

# The fixed atlas-steel for the quench-crack illustration (an anchored grade — see quench_crack_check).
ATLAS_GRADE = "4340"
ATLAS_COMPOSITION = Steel(C=0.40, Mn=0.70, Si=0.25, Ni=1.80, Cr=0.80, Mo=0.25, name=ATLAS_GRADE)
ATLAS_HALF_THICKNESS = 0.025          # a 50 mm plate — through-hardens, so transformation locks tension

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-heat-state.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-heat-state.png"


@dataclass(frozen=True)
class HeatStateDemo:
    """What the demo produced — the flagged heats plus the quantitative reads the figure draws.

    ``well`` / ``under`` are the two 4140 heats *after* :func:`~steel.heat_state.heat_treat` (the
    propagation proof: ``under`` carries the soft-core flag, ``well`` is clean); ``cracked`` is the
    4340 heat after :func:`~steel.heat_state.quench_crack_check` (the atlas illustration, carrying the
    quench-crack-risk flag and the repacked surface residual). The scalars
    (``well_martensite`` / ``under_martensite`` core-martensite fractions, ``well_HV`` / ``under_HV``,
    the ``spec`` line they are judged against, and the ``atlas_surface_MPa`` surface residual) are the
    same back-end numbers the flags were set from — pulled out for the figure's bars.
    """

    well: Heat
    under: Heat
    cracked: Heat
    well_martensite: float
    under_martensite: float
    well_HV: float
    under_HV: float
    spec: float
    atlas_surface_MPa: float


def compute() -> HeatStateDemo:
    """Run both seams and return the heats + the figure scalars — the check the spine composes."""
    well_in = Heat.from_grade(WELL_DOSED_GRADE)
    under_in = Heat(composition=UNDER_DOSED)
    # The demonstrated seam: heat_treat threads each heat through the back end and flags it.
    well = hs.heat_treat(well_in, medium=QUENCH_MEDIUM, diameter=SECTION_M)
    under = hs.heat_treat(under_in, medium=QUENCH_MEDIUM, diameter=SECTION_M)
    cracked = hs.quench_crack_check(Heat(composition=ATLAS_COMPOSITION), ATLAS_HALF_THICKNESS,
                                    grade=ATLAS_GRADE)
    # The *same* back-end evaluation, captured for the figure's quantitative bars (identical
    # constants ⇒ these numbers are exactly the ones heat_treat set its flags from).
    wo = evaluate(well_in.as_steel(), medium=QUENCH_MEDIUM, diameter=SECTION_M)
    uo = evaluate(under_in.as_steel(), medium=QUENCH_MEDIUM, diameter=SECTION_M)
    return HeatStateDemo(
        well=well, under=under, cracked=cracked,
        well_martensite=wo.result.martensite, under_martensite=uo.result.martensite,
        well_HV=wo.HV, under_HV=uo.HV, spec=hs.MIN_MARTENSITE_SPEC,
        atlas_surface_MPa=cracked.residual_stress_MPa,
    )


def save_figure(demo: HeatStateDemo) -> Path:
    """Render and bank the propagation artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import heat_state_figure

    fig = heat_state_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def _print_trail(heat: Heat) -> None:
    """Print a heat's label and its provenance trail — where it went, and where it went off spec."""
    print(f"  {heat.label()}")
    for step in heat.history:
        mark = "·" if step.in_spec is None else ("✓" if step.in_spec else "✗")
        print(f"    {mark} {step.name}: {step.summary}")


def print_summary(demo: HeatStateDemo) -> None:
    """Print the propagation story — the two 4140 heats diverging, then the atlas crack illustration."""
    print("\nHeat-state spine — an upstream alloy mistake propagates to a downstream defect\n")
    print(f"Same treatment for both: {QUENCH_MEDIUM} quench, {SECTION_M * 1000:.0f} mm section. "
          f"Only the composition differs (Cr/Mo under-dosed upstream).\n")

    print("Properly-dosed heat:")
    _print_trail(demo.well)
    print("\nUnder-dosed heat (the same quench, a soft core falls out of the physics):")
    _print_trail(demo.under)

    soft = hs.SOFT_CORE
    print(f"\n→ The under-dosed heat carries the '{soft}' flag; the well-dosed one is clean. "
          f"The failure was not scripted — it is the back-end martensite fraction crossing the "
          f"{hs.MIN_MARTENSITE_SPEC:.0%}-martensite spec line, carried on the Heat that flows downstream.")

    print("\n" + "-" * 78)
    print("\nFixed atlas-steel illustration — the same seam, a second engine (§18 residual stress):\n")
    _print_trail(demo.cracked)
    print(f"\n→ The atlas {ATLAS_GRADE} heat's surface locks into tension → the "
          f"'{hs.QUENCH_CRACK_RISK}' flag, and the residual is repacked onto the Heat "
          f"({demo.cracked.residual_stress_MPa:+.0f} MPa). This is the *fixed-grade* illustration: the "
          f"§18 engine is atlas-anchored, so the off-spec-composition → crack chain is deferred "
          f"(steel-making.md §6).")


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
