"""The grain-morphology swatch: the two grains of the Phase-5c demo, drawn to scale.

A spatial companion to :mod:`steel.demo_grain` (which banks the yield/DBTT *co-benefit* figure).
That demo shows what grain refinement **buys** — stronger AND tougher; this one shows what it
**looks like**: the cool vs the hot austenitize of the *same* steel (≈ AISI 1018) rendered as
size-accurate Voronoi grain swatches in **one common field of view**, so the over-austenitized
structure reads as a handful of coarse grains and the normalized one as a fine mosaic in the same
area.

Reach, not physics (ADR 0002): the one faithful quantity is the grain **number density**
(grain.py's ``N_A = 1/d²`` — so a finer grain packs ``(d_coarse/d_fine)²`` times as many cells
into the field); the cell shapes and the absence of a real size distribution / twins / texture are
decorative. This is the deferred grain-*morphology* view — it complements
:func:`steel.plots.microstructure_schematic` (which shows phase *fractions*), and replaces nothing.

Run headless (saves the figure, prints the table):

    python -m steel.demo_grain_morphology
"""
from __future__ import annotations

from pathlib import Path

from . import grain
from .demo_grain import compute, DEMO_STEEL_NAME

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-grain-morphology.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-grain-morphology.png"


def print_summary(fine: grain.GrainProperties, coarse: grain.GrainProperties) -> None:
    """Print the cool-vs-hot grain contrast and the same-field grain-count ratio."""
    print(f"\nGrain morphology — {DEMO_STEEL_NAME}: a cool vs a hot austenitize, one field of view\n")
    hdr = f"{'austenitize':>22} {'ferrite':>9} {'ASTM G':>7}"
    print(hdr)
    print("-" * len(hdr))
    for g, tag in ((fine, "fine / normalized"), (coarse, "coarse / overheated")):
        G = grain.astm_grain_size_number(g.ferrite_um)
        print(f"{tag + f' {g.austenitizing_T:.0f}':>22} {g.ferrite_um:8.1f}µ {G:7.1f}")
    ratio = (coarse.ferrite_um / fine.ferrite_um) ** 2
    print(f"\nSame field of view: the fine swatch shows ~{ratio:.0f}× as many grains as the coarse "
          f"one\n(grains/area ∝ 1/d² — grain.py's ASTM Nₐ). That finer mosaic is *both* stronger "
          f"and tougher;\nsee demo_grain for the yield/DBTT payoff behind the picture.")


def save_figure(fine: grain.GrainProperties, coarse: grain.GrainProperties) -> Path:
    """Render and save the grain-morphology artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import grain_morphology_figure

    fig = grain_morphology_figure(fine, coarse, name=DEMO_STEEL_NAME)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, µ on legacy codepages

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
