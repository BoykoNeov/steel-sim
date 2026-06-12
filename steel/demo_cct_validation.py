"""The §20 demo: cross-composition bainite validation against the IT atlas.

*Does any cited composition factor predict bainite kinetics across steels?* This runs the
:mod:`steel.cct_validation` study and banks the verdict: the bias-immune cited-anchor wall, the
eight-steel grading of the three Li/KV factors (none wins both metrics), and the one-knob refit
diagnosis. The headline is the **per-steel-anchoring-vindicated** result — a validation increment,
not a wall-break.

Run headless (prints the tables, saves the figure):

    python -m steel.demo_cct_validation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import cct_validation as cv

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-cct-validation.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-cct-validation.png"


@dataclass(frozen=True)
class CctValidationDemo:
    """Validated arrays/values for the §20 figure (the plot layer only draws these, ADR 0002)."""

    names: list
    measured: np.ndarray                    # atlas bainite t50 @ 700 °F (s)
    cited_mask: np.ndarray                  # True for the two carefully-read anchors
    grades: dict                            # which -> FactorGrade (predicted + spearman + magnitude)
    wall: cv.CitedAnchorWall                # the bias-immune 1080↔4340 headline
    holdout: cv.RefitHoldout                # the one-knob refit, out-of-sample
    decomposition: dict                     # what carries the carbon-deleted ranking


def compute() -> CctValidationDemo:
    names = [s.name for s in cv.CROSSCHECK_STEELS]
    return CctValidationDemo(
        names=names,
        measured=np.array([s.t50_700F for s in cv.CROSSCHECK_STEELS]),
        cited_mask=np.array([s.cited for s in cv.CROSSCHECK_STEELS]),
        grades=cv.grade_factors(),
        wall=cv.cited_anchor_wall(),
        holdout=cv.carbon_rebalance_holdout(),
        decomposition=cv.refit_decomposition(),
    )


def print_summary(d: CctValidationDemo) -> None:
    print("\n§20 — cross-composition bainite validation vs the IT atlas\n")
    print(f"Source: {cv.ATLAS_SOURCE}\n")

    w = d.wall
    print("THE HEADLINE (bias-immune — two CITED anchors only, no factor-2 reads):")
    print(f"  atlas measures 4340 ×{w.measured_ratio:.1f} SLOWER than 1080;")
    print(f"  cited BC predicts it ×{1.0 / w.bc_ratio:.1f} FASTER → ratio missed ×{w.miss:.0f}, "
          f"sign-inverted = {w.sign_inverted}.")
    print(f"  (that ×{w.miss:.0f} reproduces austemper's independent 1080/4340 scale gap — the harness checks out)\n")

    print("EIGHT-STEEL GRADING (both metrics ANCHOR-INVARIANT; ~factor-2 reads → ranking + spread):")
    print(f"  {'factor':9}{'rank ρ':>9}{'mag spread':>12}{'inverts 1080':>14}")
    label = {"bainite": "BC (cited)", "pearlite": "PC (cited)", "ferrite": "FC (cited)"}
    for which in ("bainite", "ferrite", "pearlite"):
        g = d.grades[which]
        print(f"  {label[which]:9}{g.spearman:>9.2f}{'×' + format(10 ** g.log_resid_spread, '.1f'):>12}"
              f"{str(g.inverts_1080):>14}")
    print("  → RANK: PC (0.81) > FC (0.48) > BC (0.10, the wall — carbon-dominated, inverts 1080).")
    print("    SPREAD: FC (~×3) tightest, PC (~×7) widest; BC's is small only because it is nearly")
    print("    FLAT (no tracking, ρ≈0.1). None combines order + magnitude → no usable cross-steel")
    print("    law (per-steel ~×1.3) → PER-STEEL ANCHORING IS VINDICATED, not overturned.\n")

    h, dec = d.holdout, d.decomposition
    print("THE ONE-KNOB REFIT (minimal-DOF: fit carbon weight λ on TRAIN, predict disjoint TEST):")
    print(f"  λ = {h.lam:.2f} (carbon term driven to its floor) →")
    print(f"    TEST Spearman    BC {h.test_spearman_bc:+.2f} → refit {h.test_spearman_refit:+.2f} (anchor-invariant)")
    print(f"    TEST mag spread  BC ×{10 ** h.test_spread_bc:.1f} → refit ×{10 ** h.test_spread_refit:.1f}")
    print(f"  decomposition: alloy-only ρ={dec['alloy_only']:+.2f} ≫ Bs+grain-only "
          f"ρ={dec['Bs_and_grain_only']:+.2f}")
    print("  → the gain is carried by the residual CITED alloy coefficients, not the Bs/grain confounds:")
    print("    bainite retardation is ALLOY-driven, which BC's carbon-dominated factor corrupts.")
    print("  REPORTED AS A DIAGNOSIS, NOT A LAW — carbon/alloy under-identified (1080 the lone")
    print("    no-alloy steel), grafted into nothing (a real new law would need an ADR).\n")

    print("NAMED EDGES: isothermal atlas (NOT a measured-CCT benchmark); six new 50 %-line reads")
    print("  taken hypothesis-aware at ~factor-2 (4640 most marginal, not rested on); cited-anchor")
    print("  wall is the claim, the reads only size it; no engine/pipeline touched.")


def save_figure(d: CctValidationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import cct_validation_figure

    fig = cct_validation_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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
