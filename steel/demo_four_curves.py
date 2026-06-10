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
drama is the property span, not four distinct phases.

**Phase 3 (this rewire):** the hardness numbers are now the **real**, validated
:mod:`properties` model (rule of mixtures over the constituents), not the retired
``INDICATIVE_HARDNESS`` placeholder strings — furnace/air pearlite ≈ 29–30 HRC, oil's
bainite-mixture ≈ 52 HRC, water martensite ≈ 61 HRC (a ~30 HRC span). Each path's
hardness uses its **cooling rate at 700 °C** (Maynier's ``Vr``) for the ferrite-pearlite
term. Honest finding: for *plain carbon* that cooling-rate term is small — furnace and air
pearlite differ by only ~5 HV — so the coarse/fine distinction is mainly the kinetic
``formation_T`` (lamellar spacing), not a large hardness gap. The 1080 here is the
idealized **carbon-only** steel (no minor-alloy term — that face of the model is exercised
by the 1045/4140 Jominy benchmark, ``test_properties``).

Run headless (saves the figure, prints the table):

    python -m steel.demo_four_curves
"""
from __future__ import annotations

import math
import warnings
from pathlib import Path

from . import fe_c
from . import properties as prop
from .kinetics import CCurve, andrews_Ms
from .cooling import standard_media_paths
from .pathint import transform_along_path

STEEL_CARBON = 0.80          # AISI 1080, plain-carbon eutectoid
AUSTENITIZE_T = 850.0        # °C — fully austenitic, just above A₁
BATH_T = 25.0                # °C — room-temperature quench bath

# Banked artifact lives under docs/ (committed; .gitignore allows docs/**/*.png);
# a working copy goes to outputs/ (gitignored).
_REPO_ROOT = Path(__file__).resolve().parents[1]
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


def compute_hardness(paths, results):
    """Real per-path hardness ``[(HV, HRC), …]`` from the validated :mod:`properties` model.

    The Phase-3 rewire: each path's microstructure (the rule-of-mixtures over its
    constituent fractions) is evaluated at the demo steel's carbon, using that path's
    **cooling rate at 700 °C** (``Vr``, the Maynier ferrite-pearlite term). Carbon-only —
    the idealized 1080 carries no minor-alloy term. Returns Vickers + Rockwell-C (``HRC``
    is ``nan`` for a structure softer than the ~20 HRC scale floor).
    """
    readings = []
    for p, r in zip(paths, results):
        rate_Ks = p.cooling_rate()                      # |dT/dt| at 700 °C (K/s); nan if never reached
        Vr = rate_Ks * prop.SECONDS_PER_HOUR if math.isfinite(rate_Ks) else None
        HV = prop.hardness_HV(r.fractions(), STEEL_CARBON, Vr=Vr)
        readings.append((HV, prop.vickers_to_rockwell_c(HV)))
    return readings


def print_summary(ccurve: CCurve, paths, results, hardness) -> None:
    """Print the results table — the demo's payoff in text form (now with real hardness)."""
    T_nose, t_nose = ccurve.nose(X=0.01)
    print(f"\nAISI 1080  (C = {STEEL_CARBON} wt%)   austenitized {AUSTENITIZE_T:.0f} °C → "
          f"bath {BATH_T:.0f} °C")
    print(f"  A₁ = {ccurve.T_eq:.0f} °C   Mₛ = {ccurve.Ms:.0f} °C   "
          f"C-curve nose ≈ {T_nose:.0f} °C / {t_nose:.1f} s\n")
    hdr = (f"{'medium':8s} {'Vr(°C/h)':>9s} {'P':>5s} {'B':>5s} {'M':>5s} {'RA':>5s} "
           f"{'formT':>6s} {'HV':>5s} {'HRC':>5s}  {'microstructure':<14s}")
    print(hdr)
    print("-" * len(hdr))
    for p, r, (HV, HRC) in zip(paths, results, hardness):
        f = r.fractions()
        flag = "" if p.lumped_valid else "  ⚠ Bi≥0.1 → Phase-2 spatial"
        form_t = f"{r.formation_T:6.0f}" if math.isfinite(r.formation_T) else "     —"
        rate_Ks = p.cooling_rate()
        Vr = f"{rate_Ks * prop.SECONDS_PER_HOUR:9.0f}" if math.isfinite(rate_Ks) else "        —"
        hrc = f"{HRC:5.1f}" if math.isfinite(HRC) else "  off"
        print(f"{p.name:8s} {Vr} "
              f"{f['pearlite']:5.2f} {f['bainite']:5.2f} {f['martensite']:5.2f} "
              f"{f['retained_austenite']:5.2f} {form_t} {HV:5.0f} {hrc}  "
              f"{r.dominant().replace('_', ' '):<14s}{flag}")
    print("\n(P pearlite · B bainite · M martensite · RA retained austenite · "
          "formT = mean formation temp, °C · Vr = cooling rate at 700 °C · HV/HRC from properties.py)")
    span_lo = min(h[1] for h in hardness if math.isfinite(h[1]))
    span_hi = max(h[1] for h in hardness if math.isfinite(h[1]))
    print("Four cooling rates, three phase constitutions: furnace & air both give "
          "PEARLITE (differing\nonly in formation T → coarseness — only ~5 HV apart, "
          "the honest size of the cooling-rate term\nfor plain carbon), oil a BAINITE-dominant "
          "*mixture*, water MARTENSITE. The drama is the\n"
          f"real property span ({span_lo:.0f} → {span_hi:.0f} HRC), set by which side of the "
          "C-curve nose each path falls.")


def save_figure(ccurve, paths, results, hardness) -> Path:
    """Render and save the anchor figure (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                        # headless
    from .plots import four_curves_figure

    fig = four_curves_figure(ccurve, paths, results, hardness=hardness)
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
    hardness = compute_hardness(paths, results)
    print_summary(ccurve, paths, results, hardness)
    try:
        saved = save_figure(ccurve, paths, results, hardness)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
