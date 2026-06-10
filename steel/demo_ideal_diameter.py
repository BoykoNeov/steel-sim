"""The Phase-6c demo: the ideal-critical-diameter (D_I) / measured-Jominy cross-check.

*The finished model's hardenability depth, vs measured end-quench data it never saw.* This is the
"available, not required" triad leg (the 2c/3c docstrings flagged it): compute the **critical
diameter** ``D_c`` — the round-bar diameter that is 50 % martensite at its centre (reported as the
water-quench centre-equivalent, EMJ p.29; a lower bound on the *ideal* ``D_I``) — *from* the model,
and lay it beside **measured** hardenability bands. The benchmark is measured, not Grossmann-
calculated, so it is a genuine cross-check (:mod:`ideal_diameter`).

The figure (``plots.ideal_diameter_figure``) banks the story in two panels:

1. **D_c: model vs measured, per grade.** Each grade's measured ``D_c`` band is a bar (arrow where
   the deepest heats run off the standard bar); the model's ``D_c`` (from ``fM = 0.5``) is a marker.
   The read, in order of strength: the **ranking is correct** (1045 < 8620 < 4140 < 4340 — alloy
   beats carbon); **4340 is under-predicted** (marker at/below the band's low edge, band off-scale
   above — the Cr-Mo-calibrated scale under-captures Ni); shallow grades **ride high** through the
   knee. 4140 (the calibration anchor) sits in its wide band *by construction* — not teeth.
2. **The Jominy curves behind it.** Model HRC(J) for each grade over the measured band envelopes,
   with the cited 50 %-martensite hardness (where ``D_c`` is read) marked — the threshold/conversion-
   free corroboration, the near-end hardness-map fold visible on the alloy steels.

Run headless (saves the figure, prints the summary):

    python -m projects.steel.demo_ideal_diameter
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import ideal_diameter as idd

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-ideal-diameter.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-ideal-diameter.png"

# Plot grades cool→warm by hardenability (the ranking the headline panel makes visible).
PLOT_ORDER = ("1045", "8620", "4140", "4340")


@dataclass(frozen=True)
class IdealDiameterDemo:
    """Already-validated arrays for the two-panel D_I cross-check artifact (the render layer only draws)."""

    order: tuple
    checks: dict                      # grade -> CrossCheck


def compute() -> IdealDiameterDemo:
    """Run the cross-check for every benchmark grade against one shared thermal field."""
    return IdealDiameterDemo(order=PLOT_ORDER, checks=idd.crosscheck_all())


def print_summary(d: IdealDiameterDemo) -> None:
    print("Critical-diameter (D_c, water-quench centre-equiv) cross-check — model (fM=0.5) vs MEASURED bands")
    print("=" * 86)
    print(f"{'grade':>6} {'role':>7} {'C':>5} {'50%M':>5} | "
          f"{'model D_c':>10} | {'measured D_c band':>20} | read")
    for name in d.order:
        cc = d.checks[name]
        m, me = cc.model, cc.measured
        mdi = "off-scale" if not np.isfinite(m.DI_mm) else f"{m.DI_mm:5.0f} mm"
        hi = ">bar" if me.upper_off_scale else f"{me.DI_max_mm:.0f}"
        band = f"{me.DI_min_mm:5.0f} – {hi:>5} mm"
        print(f"{name:>6} {cc.role:>7} {cc.model.jominy.carbon:5.2f} {me.h50_HRC:4.0f}  | "
              f"{mdi:>10} | {band:>20} | {cc.verdict}")
    di = {n: d.checks[n].model.DI_mm for n in d.order}
    ranked = " < ".join(sorted(di, key=lambda n: di[n]))
    print("-" * 86)
    print(f"HEADLINE — hardenability ranking (model D_c): {ranked}")
    print("  4140 = the calibration anchor (a match is by construction, NOT teeth).")
    print("  4340 + 8620 = the clean teeth: 4340 UNDER-predicted (Ni potency under-captured; the")
    print("    Cr-Mo-calibrated scale), 8620 lands in band. 1045 = the documented knee edge (rides high).")
    print("NAMED EDGES: D_c = water-quench centre-equivalent (EMJ p.29, directly read; the ideal D_I is")
    print("  its H→∞ upper bound — an AI-extracted ideal-D_I table was dropped, it coincided with oil).")
    print("  The conversion is applied identically both sides so its error cancels; measured bands are")
    print("  cited anchor points (~2 sig figs, ±2 HRC); no new physics — re-composition of the Jominy chain.")


def save_figure(d: IdealDiameterDemo) -> Path:
    """Render and save the Phase-6c artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import ideal_diameter_figure

    fig = ideal_diameter_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, ≈ on legacy codepages

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
