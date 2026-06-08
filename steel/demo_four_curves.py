"""The Phase-1 anchor demo: one steel, four cooling rates, soft pearlite → hard martensite.

*Cooling curve in, microstructure out* (Steel plan §1). Austenitize one eutectoid
steel (AISI 1080), cool it four ways — furnace, air, oil, water — and watch the
**same austenite** span a spectrum of materials, from soft pearlite to file-hard
martensite, purely because each cooling path falls on a different side of the TTT
C-curve nose. This is the banked Phase-1 artifact and simultaneously the
integration test of every 1c module: ``fe_c`` (the A₁ driving force) → ``kinetics``
(the C-curve) → ``cooling`` (the four paths) → ``pathint`` (path → fractions) →
``plots`` (the figure).

Honest scope: four cooling rates produce **three** distinct phase constitutions —
pearlite, bainite, martensite. Furnace and air both give pearlite, differing only
in *formation temperature* (and hence lamellar coarseness); the "four materials"
drama is the property span (~20 → ~63 HRC), not four distinct phases. Coarse/fine
pearlite resolution and the hardness numbers are Phase-3 (``properties.py``).

Run headless (saves the figure, prints the table):

    python -m projects.steel.demo_four_curves
"""
from __future__ import annotations

import warnings
from pathlib import Path

from . import fe_c
from .kinetics import CCurve, andrews_Ms
from .cooling import standard_media_paths
from .pathint import transform_along_path

STEEL_CARBON = 0.80          # AISI 1080, plain-carbon eutectoid
AUSTENITIZE_T = 850.0        # °C — fully austenitic, just above A₁
BATH_T = 25.0                # °C — room-temperature quench bath

# Banked artifact lives under docs/ (committed; .gitignore allows docs/**/*.png);
# a working copy goes to outputs/ (gitignored).
_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-four-curves.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-four-curves.png"


def compute():
    """Run the whole Phase-1c pipeline; return ``(ccurve, paths, results)``."""
    # The C-curve's equilibrium ceiling is fe_c's eutectoid A₁ (the driving force);
    # its martensite floor is Andrews Mₛ for this composition.
    ccurve = CCurve(T_eq=fe_c.A1(), Ms=andrews_Ms(STEEL_CARBON))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # Biot caveat reported in the table instead
        paths = standard_media_paths(T0=AUSTENITIZE_T, T_env=BATH_T)
    results = [transform_along_path(p.t, p.T, ccurve) for p in paths]
    return ccurve, paths, results


def print_summary(ccurve: CCurve, paths, results) -> None:
    """Print the results table — the demo's payoff in text form."""
    import math

    T_nose, t_nose = ccurve.nose(X=0.01)
    print(f"\nAISI 1080  (C = {STEEL_CARBON} wt%)   austenitized {AUSTENITIZE_T:.0f} °C → "
          f"bath {BATH_T:.0f} °C")
    print(f"  A₁ = {ccurve.T_eq:.0f} °C   Mₛ = {ccurve.Ms:.0f} °C   "
          f"C-curve nose ≈ {T_nose:.0f} °C / {t_nose:.1f} s\n")
    hdr = (f"{'medium':8s} {'τ_th (s)':>9s} {'Biot':>6s} {'P':>5s} {'B':>5s} {'M':>5s} "
           f"{'RA':>5s} {'formT':>6s}  {'microstructure':<14s}")
    print(hdr)
    print("-" * len(hdr))
    for p, r in zip(paths, results):
        f = r.fractions()
        flag = "" if p.lumped_valid else "  ⚠ Bi≥0.1 → Phase-2 spatial"
        form_t = f"{r.formation_T:6.0f}" if math.isfinite(r.formation_T) else "     —"
        print(f"{p.name:8s} {p.tau_thermal:9.1f} {p.biot:6.3f} "
              f"{f['pearlite']:5.2f} {f['bainite']:5.2f} {f['martensite']:5.2f} "
              f"{f['retained_austenite']:5.2f} {form_t}  {r.dominant().replace('_', ' '):<14s}{flag}")
    print("\n(P pearlite · B bainite · M martensite · RA retained austenite · "
          "formT = mean formation temp, °C)")
    print("Four cooling rates, three phase constitutions: furnace & air both give "
          "PEARLITE (differing\nonly in formation T → coarseness), oil a BAINITE-dominant "
          "*mixture* (1080 resists clean bainite\nin continuous cooling — austempering "
          "would be needed), water MARTENSITE. The drama is the\nproperty span (~20 → "
          "~63 HRC), set by which side of the C-curve nose each path falls.")


def save_figure(ccurve, paths, results) -> Path:
    """Render and save the anchor figure (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                        # headless
    from .plots import four_curves_figure

    fig = four_curves_figure(ccurve, paths, results)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    # The summary uses °C, subscripts, arrows etc.; make sure the console can take
    # them on a legacy-codepage terminal (Windows cp1252) without crashing.
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ccurve, paths, results = compute()
    print_summary(ccurve, paths, results)
    try:
        saved = save_figure(ccurve, paths, results)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
