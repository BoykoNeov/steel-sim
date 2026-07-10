"""B3 sulfur metal-partition leg: the cited C_S→L_S conversion PROBED against measured L_S (Mohassab 2013).

*Does the capacity→metal-partition conversion — the ``−log a_O`` step that turns a validated ``C_S`` into
the ``L_S`` :func:`steel.slag.desulfurize` uses — carry out-of-sample?* This runs
:mod:`steel.slag_ls_validation` and banks the verdict. Against controlled-atmosphere gas–slag–metal
heats (a_O fixed by the gas, the clean-provenance gate) the answer is **order-of-magnitude, not an
upgrade**: on the clean waterless CO/CO₂ subset the whole chain under-predicts L_S by a factor of
several (both a_O methods agreeing on the direction), and three structural confounds — the FeO-laden C_S
baseline being itself unvalidated, the ``−log a_O`` slope being inseparable from FeO basicity, and a
standard-state offset in a_O — mean the *magnitude* is not resolvable. Two clean side-findings survive:
the measured atmosphere ladder (water raises L_S ~×5, engine blind) and the ~×2-low FeO oxygen anchor.

Run headless (prints the verdict, saves the figure):

    python -m steel.demo_slag_ls_validation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import slag_ls_validation as lv

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-slag-ls-validation.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-slag-ls-validation.png"


@dataclass(frozen=True)
class SlagLsValidationDemo:
    """Validated values/arrays for the B3 sulfur-partition figure (the plot layer only draws these, ADR 0002)."""

    verdict: lv.Verdict
    co_residuals: list                      # residuals(HOLDOUT_CO) — the clean waterless grade
    h2o_residuals: list                     # residuals(HOLDOUT_H2O) — the oxidizing supplement


def compute() -> SlagLsValidationDemo:
    return SlagLsValidationDemo(
        verdict=lv.summary(),
        co_residuals=lv.residuals(lv.HOLDOUT_CO),
        h2o_residuals=lv.residuals(lv.HOLDOUT_H2O),
    )


def print_summary(d: SlagLsValidationDemo) -> None:
    v = d.verdict
    print("\nB3 (sulfur metal-partition leg) — PROBING the cited C_S→L_S conversion (Mohassab 2013)\n")
    print(f"Model under test : {lv.MODEL_UNDER_TEST}")
    print(f"Holdout source   : {lv.HOLDOUT_SOURCE}\n")

    print("THE a_O-PROVENANCE GATE (why this dataset):")
    print("  • a_O set INDEPENDENTLY by the gas phase (H2/H2O/CO/CO2 pO2), NOT back-derived from a deox")
    print("    equilibrium — the only clean way to test the −log a_O term (deferring Al/Si-killed L_S data)")
    print("  • liquid LOW-carbon iron, 1550–1650 °C; measured 2012–13 (Utah), decades after the fits")
    print(f"  • Log(Ls) three-column guard passed: {v.logls_consistency_clean} (S8 excluded — source-inconsistent, "
          f"{lv.SOURCE_INCONSISTENT_ROW})   oxide-sum guard passed: {v.oxide_sum_clean}\n")

    print("THE CLEAN GRADE — WATERLESS CO/CO2 (dilute metal S ⇒ f_S ≈ 1), gas-fixed a_O")
    print(f"  {v.co_gas.n} heats: under-predicts ×{10 ** v.co_gas.mean_log:.2f} (gas-a_O), "
          f"×{10 ** v.co_feo.mean_log:.2f} (FeO-anchor a_O) — BOTH low; scatter ×{10 ** v.co_gas.std_log:.2f}.")
    print("  → the direction is robust across the a_O method; the FACTOR is not (see confounds).")
    print(f"  Oxidizing supplement (36→{v.h2o_gas.n} H2/H2O, [S]=5–12 wt% ⇒ f_S BROKEN): "
          f"×{10 ** v.h2o_gas.mean_log:.2f} gas / ×{10 ** v.h2o_feo.mean_log:.2f} FeO — straddles, shown not headlined.\n")

    print("WHY A PROBE, NOT A VALIDATION — three confounds the data cannot separate:")
    print("  1. the conversion is inseparable from the C_S baseline, itself UNVALIDATED here (10–53 % FeO,")
    print("     whose Λ=1.00 is the fitted value the FeO-free Nzotta C_S leg excluded)")
    print("  2. the −log a_O slope is inseparable from FeO basicity (gas sets FeO; no matched-comp pairs)")
    print("     — the desulfurization analog of the L_P single-temperature confound (both B3 gaps, one wall)")
    print("  3. part of the absolute offset is an a_O standard-state artifact (gas-a_O vs FeO-anchor differ ×2)\n")

    lad = {r.atmosphere: r for r in v.ladder}
    co, mix, h2 = lad["CO/CO2"], lad["mix"], lad["H2/H2O"]
    print("SIGNED EDGE #1 — the MEASURED atmosphere ladder (the paper's own result, engine-independent):")
    print(f"  mean measured L_S: CO/CO2 {10 ** co.mean_log_ls:.2f} → mix {10 ** mix.mean_log_ls:.2f} → "
          f"H2/H2O {10 ** h2.mean_log_ls:.2f}  (water raises L_S ~×{10 ** (h2.mean_log_ls - co.mean_log_ls):.0f})")
    print("  water lowers f_S²⁻ (Mohassab Figs 4-8/9); the engine has NO atmosphere term → this is WHY the")
    print("  clean grade uses the waterless CO/CO2 subset (a ladle is not under a controlled H2/H2O atmosphere).\n")

    print("SIGNED EDGE #2 — the shared-axis oxygen anchor:")
    print(f"  metal_oxygen_for_feo (Raoultian a_FeO≈X_FeO) reads ×{10 ** v.anchor.mean_log_ratio:.2f} BELOW the")
    print("  gas-equilibrium a_O — FeO's positive activity deviation in basic slags, a located anchor bias.\n")

    print("VERDICT: a PROBE that CONFIRMS slag.py's 'order-of-magnitude only' L_S posture across a NEW")
    print("  (BF-slag) regime and does NOT upgrade it (unlike C_S). No refit, no engine touched — this study")
    print("  only reads slag.sulfur_partition (ADR 0009). Both B3 residual gaps hit the same structural wall.")


def save_figure(d: SlagLsValidationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import slag_ls_validation_figure

    fig = slag_ls_validation_figure(d)
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
