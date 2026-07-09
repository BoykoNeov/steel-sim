"""B3 phosphorus leg #2: the cited Healy L_P model against a SECOND slag system (Suito & Inoue 1984).

*Does Healy's 1970 phosphorus-partition correlation carry to a slag **system** beyond Drain's BOS?*
This runs :mod:`steel.slag_lp2_validation` and banks the verdict. An independent set (different lab,
different decade, **same converter temperature** so temperature is not a confound) says **yes with a
new edge**: on the 12 BaO slags (a minor 4 % flux) Healy over-predicts a consistent ~×1.6 with the
same high-lime pattern the Drain leg measured — the second-system generalization confirmed; but on the
11 Na₂O slags it **under-predicts**, because soda is a strong base Healy reads only ``%CaO`` and cannot
see. The CaO-isolated measure is the matched-CaO contrast — at ``%CaO ≈ 15–22`` the soda slags
dephosphorize ~×4–5 more than Healy expects — the *signed opposite* of leg #1's high-lime
over-prediction, and a scientific extension of the bias map (the engine carries no soda/baryta flux).

Run headless (prints the verdict, saves the figure):

    python -m steel.demo_slag_lp2_validation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import slag_lp2_validation as lv

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-slag-lp2-validation.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-slag-lp2-validation.png"


@dataclass(frozen=True)
class SlagLp2ValidationDemo:
    """Validated values/arrays for the B3 phosphorus leg-2 figure (the plot layer only draws these, ADR 0002)."""

    verdict: lv.Verdict
    residuals: list                         # residuals(HOLDOUT) — the residual-vs-CaO scatter, both fluxes


def compute() -> SlagLp2ValidationDemo:
    return SlagLp2ValidationDemo(verdict=lv.summary(), residuals=lv.residuals(lv.HOLDOUT))


def print_summary(d: SlagLp2ValidationDemo) -> None:
    v = d.verdict
    print("\nB3 (phosphorus leg #2) — a SECOND slag system for the cited Healy L_P model (Suito & Inoue 1984)\n")
    print(f"Model under test : {lv.MODEL_UNDER_TEST}")
    print(f"Holdout source   : {lv.HOLDOUT_SOURCE}\n")

    print("INDEPENDENCE (why this is a holdout, and a genuine SECOND system):")
    print("  • temporal — measured 1984, fourteen years after the 1970 correlation (Tohoku; also indep. of Drain 2018)")
    print("  • parametric — Healy reads only %CaO, %Fe_t, T with fixed 1970 coefficients; no optical basicity")
    print("  • system — the slag carries Na₂O (7–13 %) or BaO (~4 %), basic fluxes ABSENT from Drain's BOS")
    print("  • same conditions — 1550 °C (in Drain's 1550–1700 °C window) and LIQUID low-C iron ([%O] 0.09–0.19 %,")
    print("    oxidizing → not carbon-saturated), so this varies the SLAG, not the temperature or the metal")
    print(f"  • Eq.(3) k_P transcription guard passed: {v.kp_consistency_clean}   "
          f"oxide-sum guard passed: {v.oxide_sum_clean}\n")

    print("LEG A — BaO SLAGS: HEALY CARRIES, INDEPENDENTLY CONFIRMING THE DRAIN RESULT")
    print(f"  {v.bao.n} BaO slags (a minor 4 % flux): over-predicts ×{10 ** v.bao.mean_log:.2f}, scatter ×{10 ** v.bao.std_log:.2f}")
    print("  — the same mild over-prediction (high-basicity rows highest) the Drain leg measured (≈ ×1.48, ×2 high-lime),")
    print("  now reproduced by a different lab / decade / slag system at converter T. Healy's ~×1.5 posture GENERALIZES.\n")

    c = v.contrast
    pooled_gap = v.bao.mean_log - v.na2o.mean_log
    print("LEG B — Na₂O SLAGS: A NAMED NON-CaO-BASICITY EDGE (the signed opposite of the high-lime bias)")
    print(f"  {v.na2o.n} Na₂O slags: Healy UNDER-predicts ×{10 ** v.na2o.mean_log:.2f} (pooled, per-row) — blind to soda's basicity.")
    print("  The Na₂O residual sits ~0.5–0.7 below the BaO series across the whole lime range (robust, per-row):")
    print(f"    • pooled per-table difference (full range): BaO {v.bao.mean_log:+.2f} − Na₂O {v.na2o.mean_log:+.2f} = {pooled_gap:+.2f}")
    print(f"    • matched-CaO window (%CaO {c.cao_lo:.0f}–{c.cao_hi:.0f}): BaO ×{10 ** c.bao_mean:.2f} vs Na₂O ×{10 ** c.na2o_mean:.2f} → gap {c.gap:+.2f}")
    print(f"    → the soda under-predicts ~×{10 ** pooled_gap:.0f} relative to baryta, both reads agreeing (~0.7 log).")
    print(f"  corroboration (same paper, ORDER-of-magnitude): its 1.2×/0.9× CaO-equivalencies predict ≈ {v.equiv_expectation:+.2f}.")
    print("  CAVEATS: within Table 2 Na₂O/CaO are anti-correlated (so only the BETWEEN-table reads isolate soda); the small")
    print("    window is NOT Fe_t-matched (BaO ~40 % vs Na₂O ~33 %), so read ~×5 as order-of-magnitude, not a precise factor.\n")

    print("VERDICT: Healy's ~×1.5 L_P posture GENERALIZES to a second slag system (BaO leg confirms Drain),")
    print("  and the map gains a signed non-CaO-basicity edge (Na₂O under-predicted ~×4–5 at matched CaO). This is a")
    print("  SCIENTIFIC bias-map extension — the engine's slags carry no soda/baryta flux, so no behavior changes.")
    print("  No refit, no engine touched — this study only reads slag.phosphorus_partition (ADR 0008).")


def save_figure(d: SlagLp2ValidationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import slag_lp2_validation_figure

    fig = slag_lp2_validation_figure(d)
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
