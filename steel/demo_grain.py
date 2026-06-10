"""The Phase-5c anchor demo: grain refinement — the lone strength-AND-toughness lever.

*Austenitizing hold in, yield + DBTT out.* Phase 5 added the one structural length scale the
hardness chain never carried — the **grain size** — and through it the two engineering
quantities :mod:`properties` deliberately withholds: **yield strength** (Hall–Petch) and the
**ductile-brittle transition temperature** (Cottrell–Petch). This demo couples them: a hot vs a
cool austenitize → a coarse vs a fine prior-austenite grain (5a) → a coarse vs a fine ferrite
grain (the 5c coupling) → *both* properties (5b). It banks the figure that makes option (b)'s
payoff visible — grain refinement raising yield while *lowering* DBTT, the famous exception to
the strength↔toughness trade-off.

The steel is a low-carbon structural grade (**≈ AISI 1018**, 0.18 %C). Carbon choice is
load-bearing for *this* demo (advisor): 1018's ~21 % equilibrium pearlite keeps the DBTT in a
window that **crosses room temperature** across the austenitizing range (cool ≈ −43 °C →
overheated ≈ +21 °C), so the ductile→brittle story actually lands; a medium-carbon 1045
(~58 % pearlite) would sit brittle throughout *and* lean on the one calibrated coefficient
(pearlite-in-yield). The structure is read at a **fixed (slow) cooling rate** — the equilibrium
ferrite-pearlite the 5b laws describe; the PAGS kinetics are the S960MC-calibrated grain-growth
model reused for any steel (:mod:`grain`). The coupling isolates the PAGS effect at one cooling
rate (named), the 3c single-quench analogue.

This is the banked Phase-5c artifact and the integration test of the 5a→coupling→5b chain:
``grain.coupled_grain_properties`` (PAGS → ferrite → yield + DBTT) → ``plots.grain_figure``.

The honest scope (carried from §12): the co-benefit / lever directions are **by construction**
from the two cited Pickering signs — a *demonstration*, not a benchmark with teeth (those are
5a's grain-growth holdout). The ``yield ≤ UTS`` line is a **consistency / scope-boundary**
cross-check (it would bite only at sub-micron ferrite the austenitizing route never reaches).

Run headless (saves the figure, prints the table):

    python -m steel.demo_grain
"""
from __future__ import annotations

from pathlib import Path

from . import grain

# The demo steel — a low-carbon ferrite-pearlite structural grade (≈ AISI 1018). Real nominal
# composition (wt %), so the Pickering laws run in-distribution (not a leaner hypothetical).
DEMO_STEEL_NAME = "1018"
DEMO_STEEL_C = 0.18
DEMO_STEEL_COMP = {"Mn": 0.75, "Si": 0.20}

# Two austenitizing holds (1 h each) — a sound normalize vs a coarsening over-austenitize. The
# whole co-benefit is the contrast between the resulting fine and coarse grain.
T_AUSTENITIZE_FINE = 900.0       # °C — a sound normalizing temperature → fine PAGS
T_AUSTENITIZE_COARSE = 1200.0    # °C — over-austenitized → coarse PAGS (the cautionary case)
T_HOURS = 1.0

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-grain.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-grain.png"


def compute(
    T_fine: float = T_AUSTENITIZE_FINE, T_coarse: float = T_AUSTENITIZE_COARSE,
    t_hours: float = T_HOURS,
) -> tuple[grain.GrainProperties, grain.GrainProperties]:
    """Run the 5c coupling for the cool and hot austenitize; return ``(fine, coarse)``."""
    fine = grain.coupled_grain_properties(
        T_fine, t_hours, DEMO_STEEL_C, comp=DEMO_STEEL_COMP,
    )
    coarse = grain.coupled_grain_properties(
        T_coarse, t_hours, DEMO_STEEL_C, comp=DEMO_STEEL_COMP,
    )
    return fine, coarse


def print_summary(fine: grain.GrainProperties, coarse: grain.GrainProperties) -> None:
    """Print the austenitize → grain → yield + DBTT contrast — the demo's payoff in text."""
    print(f"\nGrain refinement co-benefit — {DEMO_STEEL_NAME} (C {DEMO_STEEL_C:.2f} %, "
          f"Mn {DEMO_STEEL_COMP['Mn']:.2f}, Si {DEMO_STEEL_COMP['Si']:.2f}), "
          f"equilibrium pearlite {fine.f_pearlite * 100:.0f} %\n")
    hdr = f"{'austenitize':>20} {'PAGS':>7} {'ferrite':>8} {'yield':>8} {'DBTT':>8} {'UTS':>7} {'y≤UTS':>6}"
    print(hdr)
    print(f"{'(°C, 1 h)':>20} {'(µm)':>7} {'(µm)':>8} {'(MPa)':>8} {'(°C)':>8} {'(MPa)':>7}")
    print("-" * len(hdr))
    for g, tag in ((fine, "fine / normalized"), (coarse, "coarse / overheated")):
        print(f"{tag + f' {g.austenitizing_T:.0f}':>20} {g.pags_um:7.1f} {g.ferrite_um:8.1f} "
              f"{g.yield_MPa:8.0f} {g.dbtt_C:8.1f} {g.uts_MPa:7.0f} {str(g.yield_below_uts):>6}")
    dY = fine.yield_MPa - coarse.yield_MPa
    dT = fine.dbtt_C - coarse.dbtt_C
    print(f"\nRefining {coarse.ferrite_um:.0f} µm → {fine.ferrite_um:.0f} µm ferrite: "
          f"yield {coarse.yield_MPa:.0f} → {fine.yield_MPa:.0f} MPa (+{dY:.0f}) "
          f"while DBTT {coarse.dbtt_C:.0f} → {fine.dbtt_C:.0f} °C ({dT:+.0f}).")
    print("Stronger AND tougher from the same lever — the exception to the strength–toughness "
          "trade-off. Adding pearlite or Si to reach the same yield would *raise* DBTT instead.")


def save_figure(fine: grain.GrainProperties, coarse: grain.GrainProperties) -> Path:
    """Render and save the grain co-benefit artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import grain_figure

    fig = grain_figure(fine, coarse, DEMO_STEEL_C, DEMO_STEEL_COMP, name=DEMO_STEEL_NAME)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, µ, ≤ on legacy codepages

    fine, coarse = compute()
    print_summary(fine, coarse)
    try:
        saved = save_figure(fine, coarse)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
