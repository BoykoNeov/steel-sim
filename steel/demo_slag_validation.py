"""The B3 demo: holdout validation of the cited C_S model against measured Nzotta 1998 data.

*Does Sosinsky–Sommerville's optical-basicity sulfide capacity predict C_S out-of-sample?* This runs
the :mod:`steel.slag_validation` study and banks the verdict: an **independent temporal holdout**
(Nzotta 1998, measured after the 1986 fit, MnO/FeO-free so no fitted Λ is in the loop) says the
model **carries** for basic high-alumina slags — consistent ~×1.4 overprediction, ×1.2 scatter,
perfect within-temperature ranking, temperature slope reproduced — with two named edges (the acidic
slag under-predicts ~×4; the MnO tier over-predicts ~×5). A *positive* validation increment, the
front-end twin of :mod:`steel.demo_cct_validation`.

Run headless (prints the verdict, saves the figure):

    python -m steel.demo_slag_validation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import slag_validation as sv

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-slag-validation.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-slag-validation.png"


@dataclass(frozen=True)
class SlagValidationDemo:
    """Validated values/arrays for the B3 figure (the plot layer only draws these, ADR 0002)."""

    verdict: sv.Verdict
    holdout: list                           # residuals(HOLDOUT) — the headline scatter
    literature: list                        # residuals(LITERATURE_1773) — corroboration
    mno: list                               # residuals(MNO_DIAGNOSTIC) — weak-link tier


def compute() -> SlagValidationDemo:
    return SlagValidationDemo(
        verdict=sv.summary(),
        holdout=sv.residuals(sv.HOLDOUT),
        literature=sv.residuals(sv.LITERATURE_1773),
        mno=sv.residuals(sv.MNO_DIAGNOSTIC),
    )


def print_summary(d: SlagValidationDemo) -> None:
    v = d.verdict
    print("\nB3 — front-end validation: cited C_S model vs an INDEPENDENT measured dataset\n")
    print(f"Model under test : {sv.MODEL_UNDER_TEST}")
    print(f"Holdout source   : {sv.HOLDOUT_SOURCE}\n")

    print("INDEPENDENCE (why this is a holdout, not a benchmark):")
    print("  • temporal — measured 1998, twelve years after the 1986 correlation (different lab, KTH)")
    print("  • parametric — Al₂O₃–CaO–MgO–SiO₂: no MnO/FeO, so no slag.py Λ that is itself fit to C_S")
    print("  • in-domain — 1773–1923 K sits inside S–S's 1400–1700 °C validity (edges are compositional)")
    print(f"  • C_S transcription guard passed: {v.transcription_clean} (every avg = mean of its repeats);")
    print(f"    composition+C_S cross-checked on the 4 Table-6↔Table-9 overlap rows: {v.overlap_clean}")
    print(f"    (the guard sees the C_S column only — composition is checked via the overlap, not exhaustively)\n")

    ba, bb = v.holdout_all, v.holdout_basic
    print("THE HEADLINE — DOES IT CARRY? (pooled bias + scatter, ordering-free):")
    print(f"  10 points = 4 basic compositions × up to 3 temperatures (Q2/Q3/Q4/Q5):")
    print(f"    pooled basic (9 pts) : bias ×{10 ** bb.mean_log:.2f}, scatter ×{10 ** bb.std_log:.2f}"
          f"   (all 10 incl. the acidic edge: ×{10 ** ba.mean_log:.2f} / ×{10 ** ba.std_log:.2f})")
    print(f"    per composition      : "
          + ", ".join(f"{lab} ×{10 ** b:.2f}" for lab, b in sorted(v.per_composition.items()) if lab != v.edge.label))
    print(f"  → the SAME ~×1.4 bias on every basic composition AND across temperatures → it CARRIES")
    print(f"    (inside the factor-2–3 inter-laboratory scatter the source itself documents)\n")

    print("TEMPERATURE SLOPE on the repeated compositions — the GENUINELY independent axis (per +100 K):")
    print("  (a constant log-bias leaves the slope untouched, so this tests the (…−54640·Λ)/T term alone)")
    for s in v.slopes:
        print(f"    {s.label} {s.temps}: measured {s.measured_slope:+.2f}  vs  model {s.predicted_slope:+.2f}")
    print("  → the S–S temperature term reproduces how C_S actually moves with temperature.")
    ranks = ", ".join(f"{T:.0f} K ρ={rho:+.0f}" for T, (rho, n) in v.ranking.items())
    print(f"  (footnote — within-T composition ranking is exact: {ranks}; thin, n=3–4 close slags, S–S monotonic in Λ)\n")

    e = v.edge
    print("NAMED EDGE 1 — the acidic side: a SINGLE-POINT flag, not an established trend:")
    print(f"    {e.label} (Λ = {e.Lambda:.2f}, the one most-acidic slag tested): under-predicts "
          f"×{10 ** abs(e.resid):.1f} (resid {e.resid:+.2f}, sign-flipped)")
    print(f"  the literature's lowest-Λ point also misses — but a near-identical-Λ neighbour fits fine")
    print(f"  (~7× spread in measured C_S at the SAME Λ = internal scatter, not a reproduced acidic trend).")
    print(f"  candidate causes: amphoteric Al₂O₃ (Λ=0.605 uncertain) and/or S–S at the high-alumina extreme.\n")

    print("NAMED EDGE 2 — MnO (weak-independence tier: slag.py's MnO Λ=1.00 is itself fit-to-C_S):")
    print(f"    Table-5 MnO slags: model over-predicts ×{10 ** v.mno.mean_log:.1f} "
          f"(scatter ×{10 ** v.mno.std_log:.2f}) — the located weak link, NOT part of the headline.\n")

    print(f"CORROBORATION — literature (Abraham–Richardson / Kärsrud / Kalyanram, pre-1986, same system):")
    print(f"    bias ×{10 ** v.literature.mean_log:.2f}, scatter ×{10 ** v.literature.std_log:.2f} "
          f"(n={v.literature.n}) — model sits inside the inter-lab band (these labs run high vs Nzotta).\n")

    print("VERDICT: the cited C_S model is HOLDOUT-VALIDATED for basic Al₂O₃–CaO–MgO–SiO₂ slags —")
    print("  ~×1.4 with ×1.2 scatter and perfect ranking. slag.py's 'order-of-magnitude only' posture")
    print("  is upgraded to 'holdout-validated within the basic domain'; the acidic and MnO edges are")
    print("  named (ADR 0006). No engine touched — this study only reads slag.sulfide_capacity.")


def save_figure(d: SlagValidationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import slag_validation_figure

    fig = slag_validation_figure(d)
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
