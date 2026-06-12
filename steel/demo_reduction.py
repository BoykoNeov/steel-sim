"""The F1 anchor demo: the Ellingham diagram — which reductant wins, above which temperature.

*Oxide in, reduction window out.* F1 is the first slice of the front end (steel **making**, ore →
iron) — and the Ellingham diagram is its cleanest possible artifact. This demo reads the
:mod:`steel.reduction` thermodynamics into the classic picture: every oxidation's ΔG°(T) line
drawn per mole O₂, the **carbon → CO** line sloping *down* across the metal-oxide lines, and the
**carbon / wüstite crossover** (~746 °C) shaded as the temperature above which carbon reduces iron
oxide — where ironmaking begins. A second panel reads the same numbers as the **equilibrium oxygen
potential** p_O₂(T): the ladder that shows *why* Al and Ca are such strong deoxidizers (their
oxides survive down to 10⁻³⁵–10⁻⁴² bar O₂) — the bridge to F2 refining.

The honest scope (module ceiling): straight ΔG° lines with the melting/boiling **kinks omitted**
(ΔCp ≈ 0), and the Fe₂O₃ → Fe₃O₄ → FeO → Fe sequence is the high-temperature one (below ≈ 570 °C
wüstite disproportionates — not encoded). No constant is fitted; the per-species ΔHf/S° are
NIST/CODATA-sourced and the crossover/ordering land where the un-tuned data put them
(``test_reduction.py``).

This is the banked F1 artifact and the integration check that the reduction pieces compose:
``reduction`` (ΔG° lines, crossover, stability order, p_O₂) → ``plots.ellingham_figure``.

Run headless (saves the figure, prints the table):

    python -m steel.demo_reduction
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from . import reduction as red

# Temperature window for the diagram — room temperature up past steelmaking (°C).
T_MIN_C = 0.0
T_MAX_C = 1600.0
N_POINTS = 200

# The lines drawn, grouped (the grouping drives the figure's colour families).
REDUCTANT_LINES = ("C->CO", "H2->H2O", "CO->CO2")
IRON_LINES = red.IRON_OXIDATION_CHAIN                       # Fe->FeO, FeO->Fe3O4, Fe3O4->Fe2O3
HIERARCHY_LINES = red.HIERARCHY_KEYS                        # Ca, Al, Si, Mn, Cr oxides
# The oxides whose oxygen potential the right panel ladders (most→least stable).
PO2_LINES = ("Ca->CaO", "Al->Al2O3", "Si->SiO2", "Cr->Cr2O3", "Fe->FeO")

# The headline crossover: carbon (→CO) reducing wüstite — where ironmaking begins.
CARBON = "C->CO"
WUSTITE = "Fe->FeO"

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-ellingham.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-ellingham.png"


@dataclass(frozen=True)
class EllinghamDemo:
    """Everything the figure draws — already-validated numbers (the render layer only plots them).

    ``temps_C`` the temperature axis; ``lines`` maps a reaction key → its ΔG° array in **kJ/mol
    O₂**; ``pO2`` maps a reaction key → its equilibrium log₁₀(p_O₂/bar) array. The scalar reads
    (the carbon/wüstite crossover, the ordered iron and hierarchy stacks) are the demo's payoff
    in text.
    """

    temps_C: list[float]
    lines: dict[str, list[float]]
    pO2: dict[str, list[float]]
    carbon_wustite_crossover_C: float
    iron_stack: list[tuple[str, float]]          # (key, ΔG° kJ/mol O₂) most stable first, @ T_ref
    hierarchy_stack: list[tuple[str, float]]      # (key, ΔG° kJ/mol O₂) most stable first, @ T_ref
    T_ref_C: float


def compute(t_min: float = T_MIN_C, t_max: float = T_MAX_C, n: int = N_POINTS) -> EllinghamDemo:
    """Build the Ellingham line set, the crossover, the stability stacks, and the p_O₂ ladder."""
    temps = [t_min + (t_max - t_min) * i / (n - 1) for i in range(n)]
    all_keys = tuple(dict.fromkeys(REDUCTANT_LINES + IRON_LINES + HIERARCHY_LINES))
    lines = {
        k: [red.standard_free_energy(red.REACTIONS[k], T) / 1000.0 for T in temps]  # kJ/mol O₂
        for k in all_keys
    }
    pO2 = {
        k: [_safe_log10_pO2(k, T) for T in temps]
        for k in PO2_LINES
    }
    crossover = red.crossover_temperature(red.REACTIONS[CARBON], red.REACTIONS[WUSTITE])
    T_ref = 1200.0
    iron_stack = [(k, g / 1000.0) for k, g in red.stability_order(IRON_LINES, T_ref)]
    hierarchy = [(k, g / 1000.0) for k, g in red.stability_order(HIERARCHY_LINES + (WUSTITE,), T_ref)]
    return EllinghamDemo(
        temps_C=temps, lines=lines, pO2=pO2,
        carbon_wustite_crossover_C=float(crossover),
        iron_stack=iron_stack, hierarchy_stack=hierarchy, T_ref_C=T_ref,
    )


def _safe_log10_pO2(key: str, T_celsius: float) -> float:
    return math.log10(red.equilibrium_oxygen_pressure(red.REACTIONS[key], T_celsius))


def print_summary(d: EllinghamDemo) -> None:
    """Print the reduction window, the iron reduction sequence, and the deoxidizer ladder."""
    print("\nEllingham reduction thermodynamics (F1) — ΔG° per mole O₂, straight-line model\n")
    Tc = d.carbon_wustite_crossover_C
    print(f"Carbon (→CO) reduces wüstite (FeO) above ~{Tc:.0f} °C — this is where ironmaking begins.")
    print("Below it, carbon cannot pull the last oxygen off iron; above it, the C→CO line dives "
          "under the\nFe→FeO line and the reduction turns spontaneous (the figure's shaded window).\n")

    print(f"Iron-oxide stability at {d.T_ref_C:.0f} °C (most stable / hardest to reduce first):")
    for k, g in d.iron_stack:
        print(f"   {red.REACTIONS[k].label:24s}  ΔG° = {g:8.1f} kJ/mol O₂")
    print("   ⇒ reduction sequence: Fe₂O₃ → Fe₃O₄ → FeO → Fe (remove oxygen from the top down)\n")

    print(f"Deoxidizer / slag-oxide hierarchy at {d.T_ref_C:.0f} °C (lower line = stronger affinity "
          "for oxygen):")
    for k, g in d.hierarchy_stack:
        po2 = red.equilibrium_oxygen_pressure(red.REACTIONS[k], d.T_ref_C)
        print(f"   {red.REACTIONS[k].label:24s}  ΔG° = {g:8.1f} kJ/mol O₂   p_O₂,eq = {po2:.1e} bar")
    print("   ⇒ Al and Ca sit at the bottom — why they deoxidize a steel bath that Fe/Mn/Si cannot.")


def save_figure(d: EllinghamDemo) -> Path:
    """Render and save the Ellingham artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import ellingham_figure

    fig = ellingham_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, ΔG, ₂, → on legacy codepages

    d = compute()
    print_summary(d)
    try:
        saved = save_figure(d)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
