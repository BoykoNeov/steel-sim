"""Hydrogen flaking: same ladle hydrogen, two sections — one sound, one cracks (the geometric consequence).

*Whether dissolved hydrogen flakes a part is set by the section size and the dehydrogenation bake, not the
ladle number alone.* The demonstrable artifact for the hydrogen consequence F2 (:mod:`steel.refining`)
deferred: refining fills the dissolved hydrogen and flags the chemistry-state **risk**; this reads whether a
*part* actually **flakes**, which is an out-diffusion (geometric) question. Two-tier, like cold-short
(propagation) / red-short (a new consumer): risk → consequence.

What it shows
-------------
1. **The hero — same heat, two outcomes.** A 4140 heat is vacuum-degassed in the ladle to ~3–4 ppm hydrogen
   (above the 2 ppm limit → it already carries refining's ``hydrogen-flaking-risk``). Cast into **two
   sections** and given the *same* dehydrogenation bake: the **thin** section degasses below the limit and is
   **sound**; the **thick** section cannot degas in time and **flakes** (adds the ``hydrogen-flaking`` flag).
   Same hydrogen, geometry decides — the analog of "same quench, two compositions → soft core".
2. **The bake lever.** That same thick section *can* be saved — by a long enough hold (its dehydrogenation
   time scales as section², so a heavy forging needs days).
3. **The coherence tooth.** The bake time this model predicts from an **independently pinned** lattice
   diffusivity reproduces cited practice without tuning: ~1 h per inch, ~days for a heavy forging.

The posture (carried from :mod:`hydrogen_flaking`): a thin consumer (the red-short class), not a benchmarked
field model. The one genuine tooth is the **OoM cross-source coherence** (D_H pinned to the room-T α-Fe
lattice value reproduces bake-vs-section practice); the ``τ ∝ L²`` scaling and the verdict are
by-construction; the model is out-diffusion only (not the γ→α supersaturation / H₂ void-pressure
thermodynamics — the named ceiling).

Run headless:

    python -m steel.demo_hydrogen_flaking
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import hydrogen_flaking as hf
from . import refining
from .heat_state import Heat
from .sweep import STEELS

GRADE = "4140"
LADLE_VACUUM_ATM = 0.02            # a weak ladle vacuum → ~3–4 ppm H (above the 2 ppm limit: risk flag set)
THIN_MM = 50                       # thin section — degasses fast
THICK_MM = 500                     # heavy-forging section — traps hydrogen
PRACTICAL_BAKE_H = 48.0            # a practical dehydrogenation hold (the hero schedule)
LONG_BAKE_H = 400.0                # the long hold that saves the thick section (the bake lever)
BAKE_T = hf.DEFAULT_BAKE_TEMP_C    # ~650 °C ferritic hold

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-hydrogen-flaking.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-hydrogen-flaking.png"


@dataclass(frozen=True)
class HydrogenFlakingDemo:
    """What the demo produced — the hero contrast, the bake lever, and the coherence/desorption curves."""

    ladle_H_ppm: float
    critical_ppm: float
    risk_flag: bool
    # hero: same H, two sections, same bake
    thin_residual_ppm: float
    thick_residual_ppm: float
    thin_flakes: bool
    thick_flakes: bool
    # the bake lever: thick saved by a long hold
    thick_long_residual_ppm: float
    thick_long_flakes: bool
    # panel — bake time vs section (the coherence tooth)
    section_mm: np.ndarray
    bake_time_h: np.ndarray
    # panel — residual H vs bake time, thin vs thick
    time_grid_h: np.ndarray
    thin_curve_ppm: np.ndarray
    thick_curve_ppm: np.ndarray
    # panel — D_H Arrhenius
    arrhenius_T: np.ndarray
    arrhenius_D: np.ndarray


def _residual(H0: float, half_thickness: float, hold_h: float) -> float:
    return hf.flaking_assessment(H0, half_thickness, hold_time_s=hold_h * 3600.0).residual_centre_ppm


def compute() -> HydrogenFlakingDemo:
    """Degas a heat, cast it into two sections, and read the flaking contrast + the coherence curves."""
    heat = refining.degas(Heat(composition=STEELS[GRADE]), p_H2=LADLE_VACUUM_ATM)
    H0 = heat.hydrogen_ppm
    thin_L, thick_L = THIN_MM / 2e3, THICK_MM / 2e3

    thin = hf.hydrogen_flaking_check(heat, half_thickness=thin_L, hold_time_s=PRACTICAL_BAKE_H * 3600.0)
    thick = hf.hydrogen_flaking_check(heat, half_thickness=thick_L, hold_time_s=PRACTICAL_BAKE_H * 3600.0)
    thick_long = hf.hydrogen_flaking_check(heat, half_thickness=thick_L, hold_time_s=LONG_BAKE_H * 3600.0)

    section_mm = np.array([12.5, 25, 50, 100, 250, 500, 1000])
    bake_time_h = np.array([hf.dehydrogenation_time(mm / 2e3) / 3600.0 for mm in section_mm])

    time_grid_h = np.linspace(0.0, LONG_BAKE_H, 200)
    D = hf.hydrogen_diffusivity(BAKE_T)
    thin_curve = np.array([H0 * hf.centre_residual_fraction(D, t * 3600.0, thin_L) for t in time_grid_h])
    thick_curve = np.array([H0 * hf.centre_residual_fraction(D, t * 3600.0, thick_L) for t in time_grid_h])

    arrhenius_T = np.linspace(20.0, 720.0, 120)
    arrhenius_D = np.array([hf.hydrogen_diffusivity(T) for T in arrhenius_T])

    return HydrogenFlakingDemo(
        ladle_H_ppm=H0, critical_ppm=hf.CRITICAL_FLAKING_H_PPM,
        risk_flag=heat.has_defect(refining.HYDROGEN_FLAKING_RISK),
        thin_residual_ppm=_residual(H0, thin_L, PRACTICAL_BAKE_H),
        thick_residual_ppm=_residual(H0, thick_L, PRACTICAL_BAKE_H),
        thin_flakes=thin.has_defect(hf.HYDROGEN_FLAKING),
        thick_flakes=thick.has_defect(hf.HYDROGEN_FLAKING),
        thick_long_residual_ppm=_residual(H0, thick_L, LONG_BAKE_H),
        thick_long_flakes=thick_long.has_defect(hf.HYDROGEN_FLAKING),
        section_mm=section_mm, bake_time_h=bake_time_h,
        time_grid_h=time_grid_h, thin_curve_ppm=thin_curve, thick_curve_ppm=thick_curve,
        arrhenius_T=arrhenius_T, arrhenius_D=arrhenius_D,
    )


def print_summary(demo: HydrogenFlakingDemo) -> None:
    """Print the two-tier story: ladle risk, then the section-decided flaking consequence."""
    print(f"\nHydrogen flaking — same ladle hydrogen, the section decides (4140)\n")
    print(f"Ladle: vacuum-degassed to {demo.ladle_H_ppm:.1f} ppm H "
          f"(> {demo.critical_ppm:.0f} ppm limit → refining's hydrogen-flaking-RISK set: {demo.risk_flag}).")

    print(f"\nSame heat, same {PRACTICAL_BAKE_H:.0f} h bake at {BAKE_T:.0f} °C, two sections:")
    print(f"    thin  {THIN_MM:>4d} mm: residual {demo.thin_residual_ppm:5.2f} ppm → "
          f"{'FLAKES' if demo.thin_flakes else 'sound'}")
    print(f"    thick {THICK_MM:>4d} mm: residual {demo.thick_residual_ppm:5.2f} ppm → "
          f"{'FLAKES' if demo.thick_flakes else 'sound'}")
    print(f"\nThe bake lever — the thick section saved by a longer hold:")
    print(f"    thick {THICK_MM:>4d} mm + {LONG_BAKE_H:.0f} h: residual {demo.thick_long_residual_ppm:5.2f} "
          f"ppm → {'FLAKES' if demo.thick_long_flakes else 'sound'}")

    print(f"\nCoherence tooth — bake time vs section (D_H pinned to the room-T lattice value, no tuning):")
    for mm, h in zip(demo.section_mm, demo.bake_time_h):
        anchor = "  (≈1 h/inch)" if abs(mm - 25) < 1 else ("  (heavy forging → days)" if mm >= 500 else "")
        print(f"    {mm:6.1f} mm → {h:7.1f} h{anchor}")
    print("\n→ same hydrogen, geometry + bake decide. One genuine tooth (OoM coherence with cited practice); "
          "the\n  L² scaling and verdict are by-construction; out-diffusion only (the named ceiling).")


def save_figure(demo: HydrogenFlakingDemo) -> Path:
    """Render and bank the hydrogen-flaking artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import hydrogen_flaking_figure

    fig = hydrogen_flaking_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    demo = compute()
    print_summary(demo)
    try:
        saved = save_figure(demo)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
