"""The Phase-7 anchor demo: inverse design — *target a hardness, get a recipe*.

The whole simulator, run **backwards**. Every other demo runs the forward model (*composition ×
quench × temper → hardness*); this one inverts it: given a hardness spec for a section of a given
size, it searches the real-grade × quench × temper space for the recipes that meet it, and names
the cheapest. The worked spec is the textbook one — **~45 HRC in a 10 mm section** — and the model
recovers the textbook answer: **4140, oil quench, temper ~425 °C/1 h**, the classic medium-section
quench-and-temper recipe.

What it shows (the inverse-design payoff, each an honest edge):
  * with the **§16 mixed-structure unlock**, plain-carbon **1045 *is* feasible** here — its 10 mm
    water quench is ~0.88 martensite, so its martensite leg tempers down into band (a *partial-
    martensite* mixed temper, the recipe labels the fraction) — and by raw cost it is the cheapest;
    but it is **Biot-stretched** (a 10 mm water quench sits past the 0-D lumped-model range), so it
    stays in the ranked set *flagged*, and is **not** the recommendation;
  * the high-retained-austenite hazard is fenced: a hard-quenched **1080** (~0.18 retained
    austenite) is **held out** of the temper branch — RA decomposes non-monotonically on tempering
    and can *raise* hardness, and this surface *recommends*, so it is not offered a confidently-wrong
    recipe;
  * the **recommended** recipe is the cheapest *lumped-valid* one — **4140 oil-quench-and-temper**,
    the textbook answer: a recipe the model flags as outside its own 0-D validity is never headlined
    (the cheaper Biot-stretched 1045 stays surfaced, but the recommendation is the cheapest recipe
    that actually holds). A transparent convenience sort, *not* a validated cost model.

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

# The v2 yield-inversion worked spec — a normalized (slow-cool) target in the regime where yield is
# defined. 370 MPa is reachable by several registry grades at once (1045/4140/8620 austenitizing
# windows bracket it), so the cost sort has something to order.
TARGET_YIELD_MPA = 370.0
YIELD_TOL_MPA = 15.0
AUSTENITIZE_HOURS = 1.0

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
    print(f"\nRecommended (cheapest lumped-valid that hits spec): {rec.label()} "
          f"→ {rec.HV:.0f} HV / {rec.HRC:.1f} HRC.")
    print("The classic medium-section quench-and-temper answer — recovered by running the simulator "
          "backwards. A cheaper but Biot-stretched recipe may rank above it (surfaced, flagged, not "
          "recommended). (Cost ordering is a transparent convenience, not a validated model.)")


def compute_yield(
    target_MPa: float = TARGET_YIELD_MPA, tol_MPa: float = YIELD_TOL_MPA,
    t_hours: float = AUSTENITIZE_HOURS,
):
    """Run the v2 yield-target inversion (the FP slow-cool regime); return the feasible recipe set."""
    return design.find_yield_recipes(target_MPa, tol_MPa=tol_MPa, t_hours=t_hours)


def print_yield_summary(result, target_MPa: float = TARGET_YIELD_MPA,
                        tol_MPa: float = YIELD_TOL_MPA) -> None:
    """Print the yield spec and the feasible *normalized* recipes (grade + austenitizing schedule).

    The point of contrast with the hardness inversion above: a *different regime* (slow-cool
    ferrite-pearlite, where yield is defined), a *different recipe* (no quench, no temper — just an
    austenitizing schedule under a normalized cool), and the DBTT co-property carried for free (grain
    refinement is the lone lever that raises yield *and* lowers DBTT — the §5b foil).
    """
    lo, hi = result.target_band
    print(f"\nYield inversion (v2) — target {target_MPa:.0f} ± {tol_MPa:.0f} MPa, normalized cool\n")
    if not result.feasible:
        print("  No grade reaches this yield by normalizing in the 850–1100 °C austenitizing window "
              "— the honest infeasible (a higher target needs a leaner-grain route, a lower one a "
              "coarser grade).")
        return
    hdr = f"{'#':>2}  {'recipe':<52} {'yield':>6} {'DBTT':>6} {'ferrite':>8} {'cost':>5}"
    print(hdr)
    print("-" * len(hdr))
    for i, r in enumerate(result.recipes, 1):
        star = "★" if r is result.recommended else " "
        print(f"{star}{i:>1}  {r.label():<52} {r.yield_MPa:5.0f}  {r.dbtt_C:5.0f}  "
              f"{r.ferrite_um:6.1f}µm {r.cost:5.2f}")
    rec = result.recommended
    print(f"\nRecommended (leanest alloy / coolest austenitize that hits spec): {rec.label()} "
          f"→ {rec.yield_MPa:.0f} MPa, DBTT {rec.dbtt_C:.0f} °C.")
    print("Yield is the property the hardness chain refuses to give (Tabor's H≈3σ is flow stress, "
          "not yield); the inverse recovers it in the slow-cool regime — no physics added, the "
          "validated Phase-5 model run backwards.")


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
    print_yield_summary(compute_yield())              # the v2 yield-target inversion (FP regime)
    try:
        saved = save_figure(result, grid)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
