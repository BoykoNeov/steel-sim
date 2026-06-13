"""The F2 anchor demo: refine a heat — carbon carries a *validated* mistake, gas fields fill the rest.

*Hot metal in, a tapped heat out — with its dissolved-gas and inclusion state finally on the record.* This
is the demonstrable artifact for **F2 Slice 1** (``docs/plans/steel-making.md`` §7) and the **middle of the
chain**: the BOF/EAF refining that sits between F1 (ore → iron) and F4 (cast billet), and the phase that
fills the ``oxygen_ppm`` / ``hydrogen_ppm`` / ``nitrogen_ppm`` / ``inclusion_*`` fields the
:class:`~steel.heat_state.Heat` record has carried as ``None`` since the spine was built.

What it shows
-------------
1. **The tap-chemistry sequence (the refining physics).** Charge carbon-saturated hot metal (~4.5 %C, a few
   ppm O), **blow** it to the grade's carbon (oxygen climbs — the inverse C–O coupling), **kill** it with
   aluminium (oxygen drops to the deoxidation equilibrium, alumina inclusions generated), **vacuum-degas**
   (hydrogen below the flaking limit). Each step returns a new ``Heat`` with one more entry on the trail and
   the matching field filled.

2. **The carbon axis is the *validated* propagation (the headline).** The blow sets carbon, and carbon is
   the one refining output the already-benchmarked back end consumes. Aim for 0.40 %C and the part
   through-hardens; **over-blow** to 0.20 %C and the *same* oil quench misses — the existing
   :func:`~steel.heat_state.heat_treat` raises its soft-core flag, not because F2 scripted it but because
   the back-end martensite fraction crossed a spec line. A real front-end mistake → a real, validated
   back-end consequence — the same class as the spine's Cr/Mo under-dose (a chosen composition error
   reaching the benchmarked back end), *not* F4's band (where Scheil computes the enrichment): here F2's
   new physics sits on the deferred-consequence side, the validated link rides the carbon control input.

3. **The new state, honestly bounded.** The deoxidation curve has a **minimum** (over-killing past ~0.07 %
   Al raises oxygen again); the Sieverts √p law sets the vacuum the 2 ppm flaking limit demands; the Al ≫ Si
   > Mn deoxidizer hierarchy is the **same** oxide-stability ordering F1's Ellingham diagram draws. But the
   *downstream* consequence of residual oxygen / hydrogen (porosity, flaking, hot-tear) lives in F4 Slice 2
   / the game layer — F2 sets that propagation up, it does not yet close it.

The posture (carried from :mod:`refining`): equilibrium endpoints, never the transport *rate*; dissolved
gas is the solubility *limit* (real pick-up is below it); inclusion content is *generated* oxide (flotation
not modelled); the deox constants are the source-sensitive tier (ranking + order of magnitude), while the
C–O product, the Sieverts solubilities, and the minimum's *location* are the robust-anchor teeth.

Run headless (prints the tap chemistry + the front-to-back divergence):

    python -m steel.demo_refining
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import heat_state as hs
from . import refining as rf
from .heat_state import Heat
from .sweep import STEELS, evaluate

# The hero grade backbone (continuity with the spine + F4 demos) and the refining set-points.
GRADE = "4140"
CHARGE_CARBON = 4.5                 # blast-furnace hot metal, carbon-saturated
TARGET_C = 0.40                     # the grade's carbon — on-spec blow
OVERBLOW_C = 0.20                   # over-blown (decarburized past target) → the soft-core failure
ALUMINIUM_PCT = 0.04               # the aluminium kill (near, just under, the Al–O minimum)
VACUUM_H2_ATM = 0.003              # the deep vacuum (a few mbar) that beats the flaking limit
TREAT_MEDIUM = "oil"
TREAT_DIAMETER = 0.015             # the discriminating section: 0.40 %C through-hardens, 0.20 %C does not

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-refining.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-refining.png"


@dataclass(frozen=True)
class RefiningDemo:
    """What the demo produced — the refined heats, the propagation, and the figure arrays.

    ``on_spec`` / ``over_blown`` the two refined Heats *after* :func:`~steel.heat_state.heat_treat` (the
    proof: only the over-blow soft-cores); ``on_spec_fM`` / ``over_fM`` and the ``spec`` line the back-end
    numbers behind the flags. The arrays draw the four panels: ``al_grid`` + (``o_vs_al``, ``o_vs_al_dilute``,
    ``o_vs_al_si``) the deoxidation curve with its minimum and the silicon comparison; ``al_min`` /
    ``o_min`` the marked Al–O minimum; ``carbon_grid`` + ``o_vs_carbon`` the C–O coupling, with the charge /
    target / over-blow points; ``pressure_grid`` + (``h_vs_p``, ``n_vs_p``) the Sieverts √p degassing curves
    with ``vacuum_for_2ppm``; ``carbon_axis`` + ``fM_vs_carbon`` the validated soft-core propagation.
    """

    on_spec: Heat
    over_blown: Heat
    on_spec_fM: float
    over_fM: float
    on_spec_HV: float
    over_HV: float
    spec: float
    # deoxidation curve (panel A)
    al_grid: np.ndarray
    o_vs_al: np.ndarray
    o_vs_al_dilute: np.ndarray
    o_vs_al_si: np.ndarray
    al_min: float
    o_min: float
    hierarchy: list[tuple[str, float]]
    # C–O coupling (panel B)
    carbon_grid: np.ndarray
    o_vs_carbon: np.ndarray
    charge_point: tuple[float, float]
    target_point: tuple[float, float]
    overblow_point: tuple[float, float]
    # Sieverts degassing (panel C)
    pressure_grid: np.ndarray
    h_vs_p: np.ndarray
    n_vs_p: np.ndarray
    vacuum_for_2ppm: float
    # carbon-axis propagation (panel D)
    carbon_axis: np.ndarray
    fM_vs_carbon: np.ndarray


def _refine(target_carbon: float) -> Heat:
    """Run the full refining sequence to ``target_carbon`` and heat-treat it — one tapped, treated Heat."""
    charge = rf.from_hot_metal(STEELS[GRADE], charge_carbon=CHARGE_CARBON)
    blown = rf.decarburize(charge, target_carbon)
    killed = rf.deoxidize(blown, "Al", ALUMINIUM_PCT)
    degassed = rf.degas(killed, p_H2=VACUUM_H2_ATM)
    return hs.heat_treat(degassed, medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)


def compute() -> RefiningDemo:
    """Refine on-spec and over-blown heats, then assemble the four-panel tap-chemistry arrays."""
    on_spec = _refine(TARGET_C)
    over_blown = _refine(OVERBLOW_C)

    # The back-end numbers behind the soft-core flags (identical constants ⇒ match the flags).
    on_o = evaluate(on_spec.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)
    over_o = evaluate(over_blown.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)

    # Panel A — the Al–O deoxidation curve (with the minimum) vs the dilute cartoon, and the Si comparison.
    d_al, d_si = rf.DEOXIDIZERS["Al"], rf.DEOXIDIZERS["Si"]
    al_grid = np.linspace(0.004, 0.40, 300)
    o_vs_al = np.array([rf.equilibrium_oxygen_after_deox(d_al, a) for a in al_grid])
    o_vs_al_dilute = np.array([rf.equilibrium_oxygen_after_deox(d_al, a, with_interaction=False) for a in al_grid])
    o_vs_al_si = np.array([rf.equilibrium_oxygen_after_deox(d_si, a) for a in al_grid])
    al_min, o_min = rf.aluminium_oxygen_minimum()
    hierarchy = rf.deoxidizing_power(0.05)

    # Panel B — the C–O coupling: dissolved O vs carbon (the inverse product), with the process points.
    carbon_grid = np.logspace(np.log10(0.08), np.log10(5.0), 300)
    o_vs_carbon = np.array([rf.equilibrium_oxygen(c) for c in carbon_grid])
    charge_point = (CHARGE_CARBON, rf.equilibrium_oxygen(CHARGE_CARBON))
    target_point = (TARGET_C, rf.equilibrium_oxygen(TARGET_C))
    overblow_point = (OVERBLOW_C, rf.equilibrium_oxygen(OVERBLOW_C))

    # Panel C — Sieverts √p degassing: H and N vs hydrogen partial pressure, with the flaking-limit vacuum.
    pressure_grid = np.logspace(-3.3, 0.0, 200)        # 0.5 mbar → 1 atm
    h_vs_p = np.array([rf.sieverts_solubility("H", p) for p in pressure_grid])
    n_vs_p = np.array([rf.sieverts_solubility("N", p) for p in pressure_grid])
    vacuum_for_2ppm = rf.vacuum_for_gas_target("H", rf.MAX_HYDROGEN_PPM)

    # Panel D — the validated propagation: martensite fraction vs the carbon turndown (the soft-core axis).
    backbone = STEELS[GRADE]
    carbon_axis = np.linspace(0.10, 0.50, 120)
    from dataclasses import replace
    fM_vs_carbon = np.array([
        evaluate(replace(backbone, C=float(c)), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER).result.martensite
        for c in carbon_axis
    ])

    return RefiningDemo(
        on_spec=on_spec, over_blown=over_blown,
        on_spec_fM=on_o.result.martensite, over_fM=over_o.result.martensite,
        on_spec_HV=on_o.HV, over_HV=over_o.HV, spec=hs.MIN_MARTENSITE_SPEC,
        al_grid=al_grid, o_vs_al=o_vs_al, o_vs_al_dilute=o_vs_al_dilute, o_vs_al_si=o_vs_al_si,
        al_min=al_min, o_min=o_min, hierarchy=hierarchy,
        carbon_grid=carbon_grid, o_vs_carbon=o_vs_carbon,
        charge_point=charge_point, target_point=target_point, overblow_point=overblow_point,
        pressure_grid=pressure_grid, h_vs_p=h_vs_p, n_vs_p=n_vs_p, vacuum_for_2ppm=vacuum_for_2ppm,
        carbon_axis=carbon_axis, fM_vs_carbon=fM_vs_carbon,
    )


def print_summary(demo: RefiningDemo) -> None:
    """Print the tap-chemistry trail, the deoxidizer hierarchy, and the front-to-back carbon divergence."""
    print(f"\nF2 — refine a {GRADE} heat: the blow sets carbon (validated), and the gas/inclusion fields fill\n")

    print("Tap-chemistry sequence (the on-spec heat), step by step:")
    for step in demo.on_spec.history:
        if step.name == "heat-treat":
            continue
        print(f"    • {step.name:<16} {step.summary}")

    print(f"\nDeoxidizer hierarchy (equilibrium dissolved O at 0.05 % addition) — the F1 Ellingham order:")
    for sym, O in demo.hierarchy:
        print(f"    {sym}: {O:8.1f} ppm O")
    print(f"    ⇒ Al ≫ Si > Mn — the same Al₂O₃ < SiO₂ < MnO oxide-stability ordering F1 draws, reached "
          f"from\n      independently-sourced dissolved-state equilibria. Al–O minimum at "
          f"[Al] = {demo.al_min:.3f} % → {demo.o_min:.1f} ppm (over-killing past it RAISES oxygen).")
    print(f"    Vacuum to beat the {rf.MAX_HYDROGEN_PPM:.0f} ppm H flaking limit: "
          f"p_H₂ ≤ {demo.vacuum_for_2ppm * 1000:.1f} mbar (Sieverts √p).")

    print(f"\nThe carbon axis — same {TREAT_MEDIUM} quench, Ø{TREAT_DIAMETER * 1000:.0f} mm, "
          f"the blow decides:")
    print(f"    on-spec  (C {TARGET_C:.2f} %): {demo.on_spec_fM:.0%} martensite, {demo.on_spec_HV:.0f} HV"
          f"  {'(soft core)' if demo.on_spec.has_defect(hs.SOFT_CORE) else '— through-hardens'}")
    print(f"    over-blown (C {OVERBLOW_C:.2f} %): {demo.over_fM:.0%} martensite, {demo.over_HV:.0f} HV"
          f"  {'← SOFT CORE' if demo.over_blown.has_defect(hs.SOFT_CORE) else ''}")
    dHV = demo.on_spec_HV - demo.over_HV
    print(f"\n→ Over-decarburize by {TARGET_C - OVERBLOW_C:.2f} %C and the same quench loses {dHV:.0f} HV and "
          f"drops below the\n  {demo.spec:.0%}-martensite spec — a real refining mistake propagating into a "
          f"validated back-end soft core.\n  The dissolved O/H/N and inclusion state ride alongside on the "
          f"Heat; their porosity/flaking consequences\n  are F4-Slice-2 / game-layer (set up here, not yet "
          f"closed).")


def save_figure(demo: RefiningDemo) -> Path:
    """Render and bank the tap-chemistry artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import refining_figure

    fig = refining_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ₂, ≫ on legacy codepages

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
