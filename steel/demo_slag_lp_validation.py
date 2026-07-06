"""The B3 phosphorus leg: holdout validation of the cited Healy L_P model against measured Drain 2018 data.

*Does Healy's 1970 phosphorus-partition correlation predict L_P out-of-sample?* This runs the
:mod:`steel.slag_lp_validation` study and banks the verdict: an **independent temporal holdout**
(Drain et al. 2018, measured 48 years after the 1970 fit, L_P defined exactly as Healy's) says the
model is **honestly benchmarked with a measured, basicity-dependent bias** — near-exact at moderate
basicity (B2, ``v≈2``: ×1.0) and over-predicting ~×2 at high lime (B5, ``v≈5``), because Healy's
linear ``+0.08·%CaO`` term does not saturate where the real L_P does. The temperature direction is
reproduced (confounded magnitude), and the ~20 % FetO maximum is a structural ceiling of the
monotonic ``+2.5·log(%Fe_t)`` term. The phosphorus twin of :mod:`steel.demo_slag_validation` — but a
*quantified bias map*, not a "validated" upgrade.

Run headless (prints the verdict, saves the figure):

    python -m steel.demo_slag_lp_validation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import slag_lp_validation as lv

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-slag-lp-validation.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-slag-lp-validation.png"


@dataclass(frozen=True)
class SlagLpValidationDemo:
    """Validated values/arrays for the B3 phosphorus figure (the plot layer only draws these, ADR 0002)."""

    verdict: lv.Verdict
    holdout: list                           # residuals(HOLDOUT) — the headline scatter


def compute() -> SlagLpValidationDemo:
    return SlagLpValidationDemo(verdict=lv.summary(), holdout=lv.residuals(lv.HOLDOUT))


def print_summary(d: SlagLpValidationDemo) -> None:
    v = d.verdict
    print("\nB3 (phosphorus leg) — front-end validation: cited Healy L_P model vs an INDEPENDENT measured dataset\n")
    print(f"Model under test : {lv.MODEL_UNDER_TEST}")
    print(f"Holdout source   : {lv.HOLDOUT_SOURCE}\n")

    print("INDEPENDENCE (why this is a holdout, not a benchmark):")
    print("  • temporal — measured 2018, forty-eight years after the 1970 correlation (Wollongong/BlueScope)")
    print("  • parametric — Healy reads only %CaO, %Fe_t, T with fixed 1970 coefficients; NO optical basicity,")
    print("    so (unlike the C_S leg) not even a fitted-Λ input is in the loop — zero parameters fit to these data")
    print("  • same definition — measured L_P = (%P)/[%P] mass ratio, exactly Healy's (not a phosphate capacity)")
    print(f"  • L_P-consistency guard passed: {v.lp_consistency_clean} (each row's %P₂O₅, [%P], L_P columns agree)")
    print(f"  • reproducibility cross-check passed: {v.repro_clean} — 7 R-series repeats give mean L_P "
          f"{v.repro_mean:.0f}, std {v.repro_std:.0f}")
    print(f"    (reproduces the paper's prose-stated 190 ± 7, i.e. a ~3.7 % measurement scatter floor)\n")

    b = v.pooled
    print("THE HEADLINE — A QUANTIFIED, BASICITY-DEPENDENT BIAS (not a uniform pass):")
    print(f"  pooled over all 33 points: over-predicts ×{10 ** b.mean_log:.2f}, scatter ×{10 ** b.std_log:.2f}")
    print("  but the bias is NOT uniform — it climbs monotonically with slag basicity:")
    for s, mean_v, mean_r, n in v.per_series:
        print(f"    {s:<3} v≈{mean_v:.1f}: ×{10 ** mean_r:.2f}   (n={n})")
    lo, hi = v.by_lime["low"], v.by_lime["high"]
    print(f"  on the raw lime axis: %CaO < 50 → ×{10 ** lo[0]:.2f} (n={lo[1]})   "
          f"vs   %CaO ≥ 55 → ×{10 ** hi[0]:.2f} (n={hi[1]})")
    print("  → near-exact in Healy's fit domain (moderate basicity); ~×2 high at the high-lime extrapolation.")
    print("    Mechanism: the +0.08·%CaO term is LINEAR and unbounded, but real L_P SATURATES beyond v≈2.5.\n")

    t = v.temperature
    print("TEMPERATURE DIRECTION — the +22350/T term (dedicated T-series, 1550 → 1700 °C):")
    print(f"    measured L_P {tuple(round(x) for x in t.measured_lp)}  falls with T: {t.measured_falls}")
    print(f"    Healy    L_P {tuple(round(x) for x in t.predicted_lp)}  falls with T: {t.predicted_falls}")
    print("  → direction reproduced, but the 3 points co-vary in composition (FetO 16→22 %) — magnitude")
    print("    confounded, so this is a direction check, NOT a second independent axis (reported honestly).\n")

    print("NAMED STRUCTURAL CEILING — the ~20 % FetO maximum:")
    print("  the data (and others) show L_P peaking at ≈ 20 % FetO for a given basicity; Healy's monotonic")
    print("  +2.5·log(%Fe_t) cannot represent that optimum — a structural limit of the bulk correlation.\n")

    print("VERDICT: Healy's L_P is HONESTLY BENCHMARKED with a MEASURED bias map — trustworthy to ~×1.1 at")
    print("  moderate basicity, over-predicting to ~×2 at high lime. slag.py's vague 'over-predicts at high")
    print("  lime' caveat is replaced by this quantified map; the L_P leg stays order-of-magnitude/benchmarked")
    print("  (NOT upgraded to 'validated' like the C_S leg — the high-lime bias is real). No refit, no engine")
    print("  touched — this study only reads slag.phosphorus_partition (ADR 0007).")


def save_figure(d: SlagLpValidationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import slag_lp_validation_figure

    fig = slag_lp_validation_figure(d)
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
