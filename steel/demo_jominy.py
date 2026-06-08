"""The Phase-2 anchor demo: one Jominy bar, two steels — shallow 1045 vs deep 4140.

*Same end-quench, same carbon, opposite hardenability* (Steel plan §3, Phase 2). Run the
standard ASTM A255 Jominy bar once (the frozen thermal field of :mod:`jominy`), then read
the hardness traverse for two ≈ 0.4 %C steels: plain-carbon **1045** and low-alloy
**4140**. They **share the quenched-end hardness** — both are full martensite there, and
~0.4 %C martensite is ~57 HRC regardless of alloying (the property model, validated in
isolation) — and then **diverge with distance**: 4140 holds a deep-hardening plateau while
1045 falls steeply to a soft, off-HRC-scale ferrite-pearlite tail. That divergence is the
Phase-2b hardenability shift (validated as a martensite gradient) now read out as hardness.

This is the banked Phase-2 artifact and the integration test of the whole spatial chain:
``jominy`` (thermal field) → ``pathint`` (path → microstructure) → ``kinetics``
(``ccurve_for_steel``, the hardenability shift) → ``properties`` (microstructure →
hardness) → ``plots``.

Honest scope: the constituent hardnesses are carbon-only (Maynier's cooling-rate and
minor-alloy terms are Phase 3), so 4140's quenched end reads ~1 HRC below 1045's (its
0.05 % less carbon, with the Cr/Mn boost omitted) where published data has them ~equal —
within the as-quenched curve's own spread. And the 1045 *knee* sits a few mm deeper than a
lean published 1040: partly this 1045's 0.75 % Mn (genuinely more hardenable), partly the
documented Phase-2b kinetics simplification (``T_eq`` held at the eutectoid A₁, not A₃, for
hypoeutectoid steel). The robust, validated claims — the shared quenched end, the 4140
deep-hardening plateau, and the dramatic divergence — are what the figure is for.

Run headless (saves the figure, prints the table):

    python -m projects.steel.demo_jominy
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from .kinetics import ccurve_for_steel
from .jominy import JominyBar, solve_thermal_field, jominy_distances
from . import properties as prop

AUSTENITIZE_T = 850.0        # °C — fully austenitic before the quench

# The two benchmark steels (compositions as in the Phase-2b hardenability test), both
# ≈ 0.4 %C: a medium-carbon plain steel and a deep-hardening low-alloy one.
STEELS = {
    "1045": dict(C=0.45, Mn=0.75, Si=0.22),
    "4140": dict(C=0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25),
}

# Representative end-quench hardness, *after* Callister (*Materials Science & Eng.*, the
# 1040/4140 Jominy figure) and ASM Handbook Vol. 1 — illustrative reference points for
# visual comparison (an overlay, not a test assertion), not redistributed data.
# (distance mm, HRC). The model's 4140 tracks these closely; the 1045 knee sits a few mm
# deeper (the documented A₁/A₃ kinetics simplification — see the module docstring).
PUBLISHED = {
    "1045": [(1.6, 57.0), (6.4, 38.0), (12.7, 25.0), (25.4, 22.0)],
    "4140": [(1.6, 57.0), (6.4, 56.0), (12.7, 54.0), (19.0, 51.0), (25.4, 48.0)],
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-jominy-hardness.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-jominy-hardness.png"


def compute(n_cells: int = 200, per_decade: int = 120):
    """Run the whole Phase-2 spatial pipeline; return ``(field, curves)``.

    ``curves`` maps each steel label → its
    :class:`~projects.steel.properties.JominyHardness` traverse. One shared thermal field
    feeds both steels — the same bar, the same cooling, only the steel's C-curve differs.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")              # Biot caveat handled in jominy/cooling
        field = solve_thermal_field(JominyBar(), T0=AUSTENITIZE_T, n_cells=n_cells,
                                    per_decade=per_decade)
    d = jominy_distances(16)                         # 1.6 .. 25.4 mm, the standard read points
    curves = {
        label: prop.jominy_hardness(field, ccurve_for_steel(**comp), comp["C"], d)
        for label, comp in STEELS.items()
    }
    return field, curves


def print_summary(curves) -> None:
    """Print the hardness-vs-distance table — the demo's payoff in text form."""
    print(f"\nJominy end-quench (ASTM A255), austenitized {AUSTENITIZE_T:.0f} °C\n")
    hdr = f"{'dist (mm)':>9s} " + "".join(f"{lbl:>20s}" for lbl in curves)
    print(hdr)
    print(f"{'':9s} " + "".join(f"{'fM   HV   HRC':>20s}" for _ in curves))
    print("-" * len(hdr))
    d = next(iter(curves.values())).distance
    for i, dd in enumerate(d):
        row = f"{dd * 1000:9.1f} "
        for h in curves.values():
            hrc = f"{h.HRC[i]:4.1f}" if np.isfinite(h.HRC[i]) else "  — "
            row += f"{h.martensite[i]:6.2f} {h.HV[i]:4.0f} {hrc:>5s}"
        print(row)
    ends = {lbl: h.HRC[0] for lbl, h in curves.items()}
    print(f"\nShared quenched end: " + ", ".join(f"{lbl} = {v:.1f} HRC" for lbl, v in ends.items())
          + "  (both ~0.4 %C martensite → the hardness model, validated in isolation)")
    print("Then they diverge with distance — 4140 holds its deep-hardening plateau, 1045 falls\n"
          "to a soft off-HRC-scale ferrite-pearlite tail (the validated hardenability shift).")


def save_figure(curves) -> Path:
    """Render and save the Jominy hardness artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import jominy_hardness_figure

    references = {lbl: (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
                 for lbl, pts in PUBLISHED.items()}
    fig = jominy_hardness_figure(curves, references=references)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, subscripts on legacy codepages

    _, curves = compute()
    print_summary(curves)
    try:
        saved = save_figure(curves)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
