"""The Phase-7 anchor demo: inverse design — *target a hardness, get a recipe*.

The whole simulator, run **backwards**. Every other demo runs the forward model (*composition ×
quench × temper → hardness*); this one inverts it: given a hardness spec for a section of a given
size, it searches the real-grade × quench × temper space for the recipes that meet it, and names
the cheapest. The worked spec is the textbook one — **~45 HRC in a 10 mm section** — and the model
recovers the textbook answer: **4140, oil quench, temper ~425 °C/1 h**, the classic medium-section
quench-and-temper recipe.

What it shows (the inverse-design payoff, each an honest edge):
  * plain-carbon **1045 is infeasible** here — its 10 mm water quench is only ~0.88 martensite,
    below the martensite-only temper model's scope, so the search will not dishonestly place it;
  * the same 45 HRC is reachable by a more-severe **water** quench too, but that costs more *and*
    trips the **Biot flag** (a 10 mm water quench sits past the 0-D lumped-model range) — surfaced,
    not hidden;
  * the **recommended** recipe is the cheapest lumped-valid one — leaner alloy + milder quench +
    the smallest treatment that hits spec (a transparent convenience sort, *not* a validated cost
    model).

This is the banked Phase-7 artifact and the integration test of the inverse chain:
``design.find_recipes_for_HRC`` (outer grade × medium enumeration + the inner temper root-find) →
``plots.design_figure`` (the feasibility map + the cost-ranked recipes).

The posture (carried from :mod:`design`): inverse design adds **no physics** — it inverts the
already-validated forward chain — so its tests are *harness correctness*, not a new benchmark.

Run headless (saves the figure, prints the recipes):

    python -m steel.demo_design
"""
from __future__ import annotations

from pathlib import Path

from . import design, sweep

# The worked spec — the canonical quench-and-temper problem.
TARGET_HRC = 45.0
TOL_HRC = 2.0
DIAMETER_M = 0.010                 # a 10 mm section (the part geometry — a constraint, not swept)
TEMPER_HOURS = 1.0

# Repo root = the parent of the ``steel`` package (``…/steel-sim``) — ``parents[1]`` in the
# standalone layout (the pre-flatten ``parents[2]`` overshot one level; corrected repo-wide).
_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-design.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-design.png"


def compute(
    target_HRC: float = TARGET_HRC, tol_HRC: float = TOL_HRC,
    diameter: float = DIAMETER_M, t_hours: float = TEMPER_HOURS,
):
    """Run the inverse search and the matching as-quenched landscape; return ``(result, grid)``.

    ``result`` is the feasible recipe set (cost-sorted); ``grid`` is the
    :func:`~steel.sweep.sweep_grid` over the same grades × media × diameter — the as-quenched map the
    figure colours and judges against the target band.
    """
    result = design.find_recipes_for_HRC(
        target_HRC, tol_HRC=tol_HRC, diameter=diameter, t_hours=t_hours)
    grid = sweep.sweep_grid(list(sweep.STEELS), media=sweep.DEFAULT_MEDIA, diameter=diameter)
    return result, grid


def print_summary(result, target_HRC: float = TARGET_HRC, tol_HRC: float = TOL_HRC) -> None:
    """Print the spec, the feasible recipes (cheapest first), and the recommendation."""
    lo, hi = result.target_band
    print(f"\nInverse design — target {target_HRC:.0f} ± {tol_HRC:.0f} HRC "
          f"({lo:.0f}–{hi:.0f} HV) in a {result.diameter * 1000:.0f} mm section\n")
    if not result.feasible:
        print("  No feasible recipe in this design space — the target is outside the achievable "
              "envelope (try a different section size or hardness).")
        return
    hdr = f"{'#':>2}  {'recipe':<48} {'HV':>5} {'HRC':>5} {'cost':>5}  0-D model"
    print(hdr)
    print("-" * len(hdr))
    for i, r in enumerate(result.recipes, 1):
        flag = "valid" if r.lumped_valid else "STRETCHED (Bi>0.1)"
        star = "★" if r is result.recommended else " "
        print(f"{star}{i:>1}  {r.label():<48} {r.HV:5.0f} {r.HRC:5.1f} {r.cost:5.2f}  {flag}")
    rec = result.recommended
    print(f"\nRecommended (cheapest that hits spec): {rec.label()} → {rec.HV:.0f} HV / {rec.HRC:.1f} HRC.")
    print("The classic medium-section quench-and-temper answer — recovered by running the simulator "
          "backwards. (Cost ordering is a transparent convenience, not a validated model.)")


def save_figure(result, grid) -> Path:
    """Render and save the inverse-design artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import design_figure

    fig = design_figure(result, grid)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, ★, → on legacy codepages

    result, grid = compute()
    print_summary(result)
    try:
        saved = save_figure(result, grid)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
