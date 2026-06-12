"""The Phase-6e demo: martempering — same hardness, far less distortion.

*Steel + section in, the direct-quench hardness out — with the through-section gradient that drives
distortion cut by a large factor.* Martempering (:mod:`martemper`) is austempering's short-hold
sibling: quench into a bath just above ``Mₛ``, hold only long enough to **equalise** the section
(well under the bainite clock), then slow-cool to martensite. The microstructure and hardness match
what a direct quench would give point-for-point (exact by construction — *not* a claim a shallow
steel through-hardens a thick section); what changes is the *spatial* picture at the moment of
transformation.

The headline figure (``plots.martemper_distortion_figure``) banks that, the *same* slab quenched
two ways on the frozen heat engine:

* **direct quench** — the surface reaches ``Mₛ`` and transforms while the centre is still tens of
  degrees hotter: a large through-section gradient at the onset of transformation (the distortion /
  quench-crack driver);
* **martemper** — the bath hold equalises the section *below the nose*, and the slow final cool then
  takes surface and centre through ``Mₛ`` slowly and near-uniformly (both steps essential): the
  gradient nearly vanishes.

The text summary adds the two pieces of falsifiable content: the **equivalence** (martemper HV =
ideal-quench HV) and the **feasibility boundary** — martempering needs the section to equalise
before bainite nucleates (``τ_equalize < t_crit``), which thin/hardenable sections clear and thick
ones do not (4340's 40 mm plate fails — the textbook section-size limit, reproduced).

Run headless (saves the figure, prints the summary):

    python -m steel.demo_martemper
"""
from __future__ import annotations

from pathlib import Path

from . import martemper as mt

AUSTENITIZE_T = 850.0        # °C — fully austenitic before the quench

# The headline distortion case: 1080, a 20 mm plate (0.010 m half-thickness) — thick enough that a
# direct water quench builds a real surface/centre gradient (Bi ≈ 0.25), and 1080's huge near-Mₛ
# t_crit makes the equalising hold comfortably feasible.
DEMO_STEEL = "1080"
DEMO_HALF_THICKNESS = 0.010  # m  → a 20 mm plate

# The feasibility table: a thin and a thick section for each anchored steel, to show the boundary.
FEAS_HALF_THICKNESSES = (0.005, 0.020)   # 10 mm and 40 mm plates

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-martemper-distortion.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-martemper-distortion.png"


def compute(half_thickness: float = DEMO_HALF_THICKNESS):
    """Run the headline distortion comparison (the slab solve feeding the figure)."""
    return mt.distortion_comparison(DEMO_STEEL, half_thickness, T0=AUSTENITIZE_T)


def print_summary(dc) -> None:
    """Print the equivalence, the distortion reduction, and the feasibility boundary."""
    print(f"\nMartempering — austenitized {AUSTENITIZE_T:.0f} °C, atlas-anchored bainite kinetics\n")

    # 1. Equivalence: same hardness as a direct quench (exact by construction, conditional on hold).
    print("Equivalence (martemper ≡ ideal nose-missing quench):")
    for steel in ("1080", "4340"):
        iq = mt.ideal_quench(steel)
        r = mt.martemper(steel, T_bath=iq.Ms + 20.0, t_hold=30.0)
        flag = "✓ true martemper" if r.bainite_safe else "✗ drifted to austemper"
        print(f"  {steel}: martemper {r.HV:5.0f} HV / {r.HRC:4.1f} HRC   "
              f"ideal quench {r.quench_HV:5.0f} HV / {r.quench_HRC:4.1f} HRC   "
              f"bainite {r.bainite:.4f}  {flag}")

    # 2. The headline distortion reduction (the figure's number).
    print(f"\nDistortion proxy ({DEMO_STEEL}, {2_000.0 * dc.half_thickness:.0f} mm plate) — "
          f"surface−centre gradient at the Mₛ crossing:")
    print(f"  direct quench : ΔT = {abs(dc.gradient_direct):5.1f} °C   "
          f"(surface transforms with the centre still {abs(dc.gradient_direct):.0f} °C hotter)")
    print(f"  martemper     : ΔT = {abs(dc.gradient_martemper):5.1f} °C   "
          f"→ {dc.reduction:.0f}× smaller gradient, the direct-quench hardness (point-for-point)")

    # 3. Feasibility: the equalise-before-bainite race (the section-size / hardenability limit).
    print("\nFeasibility (τ_equalize < t_crit — can the section equalise before bainite?):")
    print(f"  {'steel':>5s} {'plate':>8s} {'τ_eq (s)':>9s} {'t_crit (s)':>11s} "
          f"{'Bi':>5s} {'margin':>7s}   verdict")
    for steel in ("1080", "4340"):
        for L in FEAS_HALF_THICKNESSES:
            f = mt.feasibility(steel, L)
            verdict = "feasible" if f.feasible else "INFEASIBLE — forms bainite first"
            margin = f"{f.margin:5.1f}×" if f.margin != float("inf") else "  ∞ "
            print(f"  {steel:>5s} {2_000.0 * L:6.0f}mm {f.tau_equalize:9.1f} {f.t_crit:11.1f} "
                  f"{f.biot:5.2f} {margin:>7s}   {verdict}")
    print("\nThe boundary is the textbook limit: martempering needs hardenability AND a thin enough\n"
          "section — 4340's 40 mm plate cannot equalise before bainite nucleates. (t_crit near Mₛ is\n"
          "an optimistic estimate — the unmodelled near-Mₛ acceleration — so margins are a best case.)")


def save_figure(dc) -> Path:
    """Render and save the martempering distortion artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import martemper_distortion_figure

    fig = martemper_distortion_figure(dc)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, subscripts, × on legacy codepages

    dc = compute()
    print_summary(dc)
    try:
        saved = save_figure(dc)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
