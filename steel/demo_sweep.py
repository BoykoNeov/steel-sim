"""The experimentation-surface demo: composition × cooling rate, side by side (Steel plan §9).

Where ``demo_four_curves`` takes **one** steel down the cooling-rate axis, this demo adds the
**composition axis** — several real steels × the four quench media — the genuinely-new view
the sweep harness (:mod:`sweep`) unlocks. It is the banked artifact of the experimentation
surface and the data the Streamlit app / notebook will drive interactively.

The thesis the figure makes visible (the hardenability story, in 0-D form): in the lumped
model every steel sees the *same* cooling path at a given medium, so the steels **share the
fast-quench (martensitic) and slow-cool (pearlitic) ends and diverge only in the middle** —
and the deep-hardening alloy (4140) keeps martensite down to far lower cooling rates than the
lean plain-carbon steel (1045). Same four media, three steels, a property grid spanning soft
ferrite-pearlite to file-hard martensite.

Run headless (prints the tables, saves the figure):

    python -m steel.demo_sweep
"""
from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np

from . import sweep
from . import properties as prop

# The lean / reference / alloy trio — the cleanest hardenability contrast (1045 and 4140 are
# both ~0.4 %C, so their divergence is the alloy C-curve shift, not carbon; 1080 is the
# high-carbon reference steel). Real compositions from the sweep registry.
DEMO_STEELS = ["1045", "1080", "4140"]

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-sweep.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-sweep.png"


def compute():
    """Run the composition × cooling-rate sweep; return the ``grid`` (rows = steels, cols = media)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # Biot reported in the table/figure, not warned
        return sweep.sweep_grid(DEMO_STEELS, media=sweep.DEFAULT_MEDIA)


def print_grid(grid) -> None:
    """Print the hardness/microstructure grid — the demo's payoff in text form."""
    media = [o.medium for o in grid[0]]
    print("\nComposition × cooling-rate sweep   (austenitize 850 °C → bath 25 °C, 10 mm cylinder)")
    print("Hardness HRC (HV) and dominant constituent per cell:\n")
    hdr = f"{'steel':7s} " + " ".join(f"{str(m):>20s}" for m in media)
    print(hdr)
    print("-" * len(hdr))
    for row in grid:
        cells = []
        for o in row:
            hrc = f"{o.HRC:.0f}HRC" if math.isfinite(o.HRC) else "soft"
            flag = "*" if not o.lumped_valid else " "
            cells.append(f"{hrc:>6s} {o.HV:4.0f}HV {o.dominant()[:5]:>5s}{flag}")
        print(f"{row[0].steel.label():7s} " + " ".join(f"{c:>20s}" for c in cells))
    print("\n(* = beyond the 0-D lumped Biot range — a severe quench of this section needs the "
          "Phase-2 spatial solve;\n soft = below the ~20 HRC scale floor, reported in HV. "
          "Steels share the fast/slow ends, diverge in the middle.)")


def print_temper(grade: str = "4140") -> None:
    """Print the quench-and-temper response of one steel — the tempering axis (martensite-only)."""
    steel = sweep.STEELS[grade]
    tr = sweep.temper_sweep(steel, temper_C=np.array([150.0, 300.0, 450.0, 600.0]), t_hours=1.0)
    print(f"\nQuench-and-temper response of {steel.label()} (1 h temper, full-martensite start):")
    print(f"{'T(°C)':>6s} {'P':>7s} {'HV':>6s} {'HRC':>6s} {'UTS(MPa)':>9s} {'toughness':>10s}")
    print(f"{'as-q':>6s} {'—':>7s} {tr.HV_as_quenched:6.0f} "
          f"{_fmt(prop.vickers_to_rockwell_c(tr.HV_as_quenched))} {'—':>9s} {'—':>10s}")
    for i, T in enumerate(tr.temper_C):
        uts = f"{tr.UTS_MPa[i]:9.0f}" if math.isfinite(tr.UTS_MPa[i]) else f"{'nan':>9s}"
        print(f"{T:6.0f} {tr.P[i]:7.0f} {tr.HV[i]:6.0f} {_fmt(tr.HRC[i])} {uts} {tr.toughness[i]:10.2f}")
    print("(hardness falls and toughness rises with tempering — the strength/toughness trade-off; "
          "an alloy\n steel resists softening as an emergent consequence of its harder, higher-floor "
          "endpoints.)")


def _fmt(hrc: float) -> str:
    return f"{hrc:6.1f}" if math.isfinite(hrc) else f"{'soft':>6s}"


def save_figure(grid) -> Path:
    """Render and save the banked sweep-comparison figure (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                        # headless
    from .plots import sweep_comparison_figure

    fig = sweep_comparison_figure(grid)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C / subscripts on a legacy codepage

    grid = compute()
    print_grid(grid)
    print_temper("4140")
    try:
        saved = save_figure(grid)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
