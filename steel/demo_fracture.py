"""Quench cracking: same quench, the *cleanliness* decides — the inclusion as crack initiator (B1).

*A tensile surface is only a risk; an inclusion is only a defect; a quench crack is what happens when the
two meet.* The demonstrable artifact for the **fracture-side coupling** (:mod:`steel.fracture`): the §18
residual-stress field already raises a flat **``quench-crack-risk``** whenever the surface ends in tension —
this **couples** that field to the heat's inclusion population through a linear-elastic fracture-mechanics
gate, so the *same* tensile surface reads as a survivable risk for a clean heat and a **realized
``quench-crack``** for a dirty one. The two-tier split (cf. ``hydrogen-flaking-RISK`` → ``hydrogen-flaking``).

What it shows
-------------
1. **The hero — same residual field, the flaw decides.** One thick 4340 section, one direct water quench,
   one surface tension (the phase-split residual solve). A **clean** heat (largest surface flaw √area ≈
   30 µm) sits below the critical flaw size — tensile surface, **no crack**. A **dirty** heat (√area ≈
   400 µm) in the *identical* field exceeds it — **quench crack**. Cleanliness is load-bearing; the flat
   tension flag cannot see it.
2. **The crack window opens with section size.** Critical flaw size √area_c falls as the section thickens
   (thicker → steeper gradient → higher surface tension → smaller tolerable flaw). The dirty heat crosses
   into cracking past a section thickness; the clean heat stays safe across the range — quench cracking is a
   heavy-section problem.
3. **The route lever — martempering saves the dirty part.** The same dirty heat, martempered, equalises
   through ``Mₛ`` and collapses the surface tension (→ compression), so √area_c → ∞ and the crack clears —
   the §17/§18 distortion benefit carried into fracture. (And the thermal-only reference leaves the surface
   in *compression* — never cracks, whatever the flaw.)

The posture: **no claimable tooth.** The surface-sign reversal and the martemper benefit are *consumed* from
:mod:`steel.residual` (downstream of its formula sign), not new teeth. The LEFM relation and Murakami's √area
factor are **cited**; the as-quenched ``K_Ic`` magnitude, the hard-martensite yield base and the clean/dirty
``√area`` populations are **representative** — the absolute crack threshold is property-sensitive (``√area_c
∝ K_Ic²``), so the constants are chosen so the gate *discriminates* clean from dirty, a named scope edge. The
checks are structural: the two-factor straddle, the martemper-raises-√area_c monotonicity, tension-required.

Run headless:

    python -m steel.demo_fracture
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import fracture as fr
from .heat_state import Heat, QUENCH_CRACK
from .sweep import STEELS

# The hero: a thick 4340 section (half-thickness 50 mm → 100 mm plate), the heavy-section quench-crack case.
# 4340 is an atlas anchor (residual.ATLAS_STEELS), not a back-end grade (sweep.STEELS) — build its composition
# from the 4140 backbone so the Heat carries an honest 4340 wt-% vector for the seam demonstration.
HERO_STEEL = "4340"
HERO_HALF_THICKNESS = 0.05
_HERO_COMP = replace(STEELS["4140"], C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33, name="4340")

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-fracture.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-fracture.png"


@dataclass(frozen=True)
class FractureDemo:
    """What the demo produced — the cleanliness-decides hero, the section window, and the route lever."""

    steel: str
    half_thickness: float
    K_Ic_MPa: float
    clean_um: float
    dirty_um: float
    # the hero pair (same field): the clean and dirty assessments at the hero section
    clean: fr.QuenchCrackAssessment
    dirty: fr.QuenchCrackAssessment
    # whether the clean heat raised the realized quench-crack flag, and the dirty heat
    clean_flag: bool
    dirty_flag: bool
    # section-size sweep: half-thickness grid (m), surface tension (MPa), critical flaw √area_c (µm)
    ht_grid: np.ndarray
    surface_curve: np.ndarray
    critical_curve: np.ndarray
    # the route lever: dirty heat, direct vs martemper
    dirty_direct: fr.QuenchCrackAssessment
    dirty_martemper: fr.QuenchCrackAssessment
    # the LEFM gate plane at the hero stress: √area grid (µm) and K (MPa√m)
    sqrt_area_grid: np.ndarray
    K_curve: np.ndarray


def _flag(sqrt_area_um: float, **kw) -> bool:
    """Run the Heat seam for the hero grade + a flaw and report whether the realized quench-crack flag rose."""
    heat = Heat(composition=_HERO_COMP)
    out = fr.fracture_check(heat, HERO_HALF_THICKNESS, sqrt_area_um, grade=HERO_STEEL, **kw)
    return out.has_defect(QUENCH_CRACK)


def compute() -> FractureDemo:
    """Read the clean and dirty heats in one residual field, sweep section size, and pull the route lever."""
    clean = fr.quench_crack_fracture(HERO_STEEL, HERO_HALF_THICKNESS, fr.SQRT_AREA_CLEAN_UM)
    dirty = fr.quench_crack_fracture(HERO_STEEL, HERO_HALF_THICKNESS, fr.SQRT_AREA_DIRTY_UM)

    # Section-size sweep — the crack window opening with thickness (surface tension and √area_c).
    ht_grid = np.linspace(0.015, 0.06, 16)
    surface, critical = [], []
    for ht in ht_grid:
        a = fr.quench_crack_fracture(HERO_STEEL, float(ht), fr.SQRT_AREA_DIRTY_UM)
        surface.append(a.surface_stress_MPa)
        critical.append(a.critical_flaw_um)

    # The route lever — the dirty heat, direct vs martemper.
    dirty_direct = dirty
    dirty_martemper = fr.quench_crack_fracture(
        HERO_STEEL, HERO_HALF_THICKNESS, fr.SQRT_AREA_DIRTY_UM, route="martemper",
    )

    # The LEFM gate plane at the hero surface stress — K rising with √area against K_Ic.
    sqrt_area_grid = np.linspace(0.0, 600.0, 200)
    K_curve = np.array([fr.murakami_stress_intensity(dirty.surface_stress_MPa, s) for s in sqrt_area_grid])

    return FractureDemo(
        steel=HERO_STEEL, half_thickness=HERO_HALF_THICKNESS, K_Ic_MPa=fr.K_IC_AS_QUENCHED_MPA,
        clean_um=fr.SQRT_AREA_CLEAN_UM, dirty_um=fr.SQRT_AREA_DIRTY_UM,
        clean=clean, dirty=dirty,
        clean_flag=_flag(fr.SQRT_AREA_CLEAN_UM),
        dirty_flag=_flag(fr.SQRT_AREA_DIRTY_UM),
        ht_grid=ht_grid, surface_curve=np.array(surface), critical_curve=np.array(critical),
        dirty_direct=dirty_direct, dirty_martemper=dirty_martemper,
        sqrt_area_grid=sqrt_area_grid, K_curve=K_curve,
    )


def print_summary(demo: FractureDemo) -> None:
    """Print the two-tier story: a flat tension risk, then the cleanliness-resolved realized crack."""
    print("\nQuench cracking — same quench, the cleanliness decides (the inclusion as crack initiator)\n")
    print(f"The §18 residual field raises a flat 'quench-crack-risk' on surface tension alone. This couples it\n"
          f"  to the heat's inclusion flaw through an LEFM gate (Murakami √area, K_Ic of the as-quenched\n"
          f"  martensite): a crack runs only when the surface is in tension AND the flaw exceeds √area_c.\n")

    c, d = demo.clean, demo.dirty
    print(f"Hero — one {demo.steel}, 2t = {2 * demo.half_thickness * 1000:g} mm, one direct water quench "
          f"(phase-split residual):")
    print(f"  surface residual = {d.surface_stress_MPa:+.0f} MPa (tension) → 'quench-crack-risk' raised either way")
    print(f"  critical flaw √area_c at this stress = {d.critical_flaw_um:.0f} µm  (K_Ic = {demo.K_Ic_MPa:.0f} MPa√m)")
    print(f"    clean heat  √area {demo.clean_um:5.0f} µm  → K {c.K_applied_MPa:4.1f} MPa√m  "
          f"({c.margin:.1f}× below √area_c) → {'QUENCH CRACK' if c.cracks else 'no crack'}  "
          f"[flag: {demo.clean_flag}]")
    print(f"    dirty heat  √area {demo.dirty_um:5.0f} µm  → K {d.K_applied_MPa:4.1f} MPa√m  "
          f"({d.margin:.2f}× of √area_c) → {'QUENCH CRACK' if d.cracks else 'no crack'}  "
          f"[flag: {demo.dirty_flag}]")
    print("  → SAME residual field; the clean heat survives, the dirty heat cracks. Cleanliness is "
          "load-bearing,\n    not a relabel of the tension flag.")

    dd, dm = demo.dirty_direct, demo.dirty_martemper
    print(f"\nThe route lever — the dirty heat, direct vs martemper:")
    print(f"    direct    surface {dd.surface_stress_MPa:+6.0f} MPa → "
          f"{'QUENCH CRACK' if dd.cracks else 'no crack'}")
    print(f"    martemper surface {dm.surface_stress_MPa:+6.0f} MPa → "
          f"{'QUENCH CRACK' if dm.cracks else 'no crack'} (√area_c → "
          f"{'∞' if dm.critical_flaw_um == float('inf') else f'{dm.critical_flaw_um:.0f} µm'})")
    print("  → martempering collapses the surface tension, so √area_c blows up and the same dirty heat clears "
          "— the\n    §17/§18 distortion benefit, now in fracture.")

    print("\nNO claimable tooth — the sign reversal and the martemper benefit are consumed from residual.py; "
          "the LEFM\n  relation and Murakami's √area factor are cited; the as-quenched K_Ic, the martensite "
          "yield base and the\n  clean/dirty √area are representative (the absolute crack threshold ∝ K_Ic² — a "
          "named scope edge).\n  Ceilings: surface-initiated only, atlas-steel only, one flaw per heat (not an "
          "extreme-value distribution).")


def save_figure(demo: FractureDemo) -> Path:
    """Render and bank the fracture-coupling artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import fracture_figure

    fig = fracture_figure(demo)
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
