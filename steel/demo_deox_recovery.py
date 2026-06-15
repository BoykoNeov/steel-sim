"""The F2→F3 seam: the bath's dissolved oxygen taxes the *oxidizable* trim alloys' recovery.

*Kill the bath before you trim it. Drop Mn and Si into a hot, under-killed heat and the dissolved oxygen eats
some of them — they land short; the noble Cr/Mo/Ni do not care.* This is the demonstrable artifact for the
**deox→recovery coupling** — the seam that closes the named deferral the F3 ladle module carried: where
:mod:`steel.demo_ladle` **hand-set** the recovery shortfall (Cr/Mo recovery halved) and
:mod:`steel.demo_carbon_carry_in` turned on the ferroalloy carbon, this one turns on F2's *deox state*. The
dissolved oxygen :func:`steel.refining.deoxidize` leaves on the ``Heat`` (high if the kill is skipped or
weak — the porosity-risk regime) ties up a stoichiometric mass of the oxidizable additions as oxide, so their
**recovery** falls below nominal (:func:`steel.ladle.recovery_after_deox`).

What it shows
-------------
1. **The hero — same charges, the deox state decides the Mn/Si recovery.** One alloy-lean tap, **one** set of
   ferroalloy charges sized for the nominal recovery. Trim it into a *well-killed* bath (Al-killed, O ~4 ppm)
   and Mn/Si recover essentially in full; trim the *same* charges into an *under-killed* bath (a weak,
   insufficient Si kill — O at the C–O equilibrium, ~53 ppm, **porosity-risk**) and the oxygen taxes Mn/Si.
   The noble Cr/Mo/Ni land identically either way. **Selectivity is the point** — the oxygen tax falls only on
   the alloys that deoxidize.

2. **The magnitude is modest — and that is itself the result (why the gross hero is hand-set).** Even a fully
   under-killed bath taxes Mn by only ~2 % at 4140's carbon (~4 % at 8620's lower carbon, which sits at higher
   dissolved O). The landed Mn dips but stays **inside the window** — the dissolved-O coupling alone cannot
   drive a heat off grade, which is *quantitatively why* :mod:`steel.demo_ladle`'s gross under-trim (Cr/Mo
   recovery ~halved) must be **hand-set**. The gross industrial loss is slag-FeO reoxidation — a metal→slag
   alloy distribution this repo does not build (the named ceiling).

3. **The carbon→oxygen→tax coherence (F2 straight into F3).** Lower-carbon heats sit at *higher* dissolved
   oxygen (the C–O inverse coupling F2 computes), so they are **more** vulnerable to the recovery tax — 8620
   (0.20 %C) loses more Mn than 4140 (0.40 %C) under the same skipped kill. The kill-before-you-trim
   discipline matters most exactly where the carbon is lowest.

The posture: **no claimable tooth.** The tax is conservation arithmetic (the same mass balance
:func:`steel.refining.generated_oxide` uses) on cited oxide stoichiometry; the oxidizable-vs-noble selectivity
is exact by construction (which trim elements carry a deox reaction), the Si-over-Mn split is a stated
simplification, and the result is a **readout** (recovery / landed composition), not a new flag. The under-
killed heat's only defect is F2's own ``porosity-risk`` — one root cause (the skipped kill), one flag plus one
readout. The gross slag-reoxidation distribution stays a named deferral.

Run headless:

    python -m steel.demo_deox_recovery
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import ladle as ld
from . import refining as rf
from .heat_state import Heat
from .sweep import STEELS

# The hero grade + the second grade that carries the carbon→oxygen coherence.
GRADE = "4140"
LEAN_GRADE = "8620"                     # lower carbon → higher dissolved O → bigger tax
KILL_DEOX, KILL_LEVEL = "Al", 0.04      # the proper kill: aluminium to a few ppm
WEAK_DEOX, WEAK_LEVEL = "Si", 0.05      # the insufficient kill: a little silicon, O stays high (porosity-risk)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-deox-recovery.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-deox-recovery.png"


@dataclass(frozen=True)
class DeoxRecoveryDemo:
    """What the demo produced — the same-charges well-vs-under contrast and the recovery/landed sweeps.

    ``tap`` the alloy-lean origin; ``well`` / ``under`` the trimmed Heats (well-killed vs under-killed, *same
    charges*, carry-in off). ``well_O`` / ``under_O`` the bath dissolved oxygen behind them; ``mn_loss_pct`` the
    Mn recovery loss in the under-killed bath. ``well_Mn`` / ``under_Mn`` the landed manganese, ``mn_floor`` the
    cited window floor. ``oxygen_grid`` with ``rec_curves`` (per-element recovery vs O — panel A) and the
    per-grade ``landed_mn`` curves with operating points (panel B), ``lean_under_O`` / ``lean_mn_loss_pct`` the
    lower-carbon grade's bigger tax.
    """

    tap: Heat
    well: Heat
    under: Heat
    well_O: float
    under_O: float
    mn_loss_pct: float
    well_Mn: float
    under_Mn: float
    mn_floor: float
    # the lower-carbon coherence
    lean_under_O: float
    lean_mn_loss_pct: float
    # panel A — recovery vs dissolved oxygen, per trim element
    elements: tuple[str, ...]
    oxygen_grid: np.ndarray
    rec_curves: dict[str, np.ndarray]
    well_point_O: float
    under_point_O: float
    # panel B — landed Mn vs dissolved oxygen, per grade (with window floors + operating points)
    grades: tuple[str, ...]
    landed_mn: dict[str, np.ndarray]
    mn_floors: dict[str, float]
    operating: dict[str, tuple[float, float]]   # grade → (operating O, landed Mn)


def _trimmed(grade: str, deox: str, level: float) -> Heat:
    """Deoxidize a fresh ``grade`` tap with ``deox`` at ``level``, then trim it to grade with the seam on."""
    tap = ld.from_tap(grade)
    killed = rf.deoxidize(tap, deox, level)                       # sets oxygen_ppm (+ porosity-risk if weak)
    return ld.trim_to_grade(killed, grade, couple_deox_recovery=True)


def compute() -> DeoxRecoveryDemo:
    """Trim one tap two ways — well-killed vs under-killed — and assemble the recovery / landed sweeps."""
    tap = ld.from_tap(GRADE)
    charges = ld.additions_for_grade(tap.composition, STEELS[GRADE])   # nominal-sized, same either way

    well = _trimmed(GRADE, KILL_DEOX, KILL_LEVEL)
    under = _trimmed(GRADE, WEAK_DEOX, WEAK_LEVEL)
    well_O = rf.deoxidize(tap, KILL_DEOX, KILL_LEVEL).oxygen_ppm
    under_O = rf.deoxidize(tap, WEAK_DEOX, WEAK_LEVEL).oxygen_ppm

    mn_loss = ld.oxidation_recovery_loss(charges, under_O).get("Mn", 0.0)
    mn_loss_pct = 100.0 * mn_loss / ld.FERROALLOYS["Mn"].recovery
    mn_floor = ld.GRADE_WINDOWS[GRADE].bands["Mn"][0]

    # the lower-carbon coherence: 8620 sits at higher dissolved O → a bigger Mn tax
    lean_tap = ld.from_tap(LEAN_GRADE)
    lean_charges = ld.additions_for_grade(lean_tap.composition, STEELS[LEAN_GRADE])
    lean_under_O = rf.deoxidize(lean_tap, WEAK_DEOX, WEAK_LEVEL).oxygen_ppm
    lean_mn_loss = ld.oxidation_recovery_loss(lean_charges, lean_under_O).get("Mn", 0.0)
    lean_mn_loss_pct = 100.0 * lean_mn_loss / ld.FERROALLOYS["Mn"].recovery

    # Panel A — recovery vs dissolved oxygen, per trim element (the selectivity).
    elements = ld.TRIM_ELEMENTS                                  # (Mn, Si, Ni, Cr, Mo)
    oxygen_grid = np.linspace(0.0, 120.0, 121)
    rec_curves = {
        e: np.array([ld.recovery_after_deox(charges, O).get(e, ld.FERROALLOYS[e].recovery) for O in oxygen_grid])
        for e in elements
    }

    # Panel B — landed Mn vs dissolved oxygen, per grade (sized at nominal, delivered at the taxed recovery).
    def landed_mn_curve(g_tap: Heat, g_charges: dict[str, float]) -> np.ndarray:
        out = np.empty_like(oxygen_grid)
        for i, O in enumerate(oxygen_grid):
            trimmed, _ = ld.mix(g_tap.composition, g_charges, recovery=ld.recovery_after_deox(g_charges, O))
            out[i] = trimmed.Mn
        return out

    grades = (GRADE, LEAN_GRADE)
    taps = {GRADE: tap, LEAN_GRADE: lean_tap}
    chgs = {GRADE: charges, LEAN_GRADE: lean_charges}
    landed_mn = {g: landed_mn_curve(taps[g], chgs[g]) for g in grades}
    mn_floors = {g: ld.GRADE_WINDOWS[g].bands["Mn"][0] for g in grades}
    operating = {GRADE: (under_O, under.composition.Mn),
                 LEAN_GRADE: (lean_under_O, float(np.interp(lean_under_O, oxygen_grid, landed_mn[LEAN_GRADE])))}

    return DeoxRecoveryDemo(
        tap=tap, well=well, under=under, well_O=well_O, under_O=under_O,
        mn_loss_pct=mn_loss_pct, well_Mn=well.composition.Mn, under_Mn=under.composition.Mn, mn_floor=mn_floor,
        lean_under_O=lean_under_O, lean_mn_loss_pct=lean_mn_loss_pct,
        elements=elements, oxygen_grid=oxygen_grid, rec_curves=rec_curves,
        well_point_O=well_O, under_point_O=under_O,
        grades=grades, landed_mn=landed_mn, mn_floors=mn_floors, operating=operating,
    )


def print_summary(demo: DeoxRecoveryDemo) -> None:
    """Print the same-charges well-vs-under divergence — the selectivity, the modest magnitude, the coherence."""
    print(f"\nF2→F3 seam — the bath's dissolved oxygen taxes the oxidizable trim ({GRADE})\n")
    print("One alloy-lean tap, ONE set of charges sized for the nominal recovery. The only difference is the")
    print("bath's deox state when the alloys go in (kill first, or trim into a hot bath):\n")

    for tag, heat, O in [("well-killed (Al)   ", demo.well, demo.well_O),
                         ("under-killed (weak)", demo.under, demo.under_O)]:
        rec = ld.recovery_after_deox(
            ld.additions_for_grade(demo.tap.composition, STEELS[GRADE]), O)
        flags = " + ".join(heat.defects).upper() if heat.defects else "clean"
        print(f"    {tag}: O {O:5.1f} ppm → η(Mn) {rec['Mn']:.3f}, η(Si) {rec['Si']:.3f} | "
              f"η(Cr) {rec['Cr']:.3f}, η(Mo) {rec['Mo']:.3f}")
        print(f"                          → landed Mn {heat.composition.Mn:.3f}, Si {heat.composition.Si:.3f} "
              f"| Cr {heat.composition.Cr:.3f}, Mo {heat.composition.Mo:.3f}  [{flags}]")

    print(f"\n  Selectivity: the oxygen tax falls only on the deoxidizing alloys (Mn, Si); the noble Cr/Mo/Ni "
          f"land\n  identically. In the under-killed bath Mn recovery drops ~{demo.mn_loss_pct:.1f} % — landed "
          f"Mn {demo.well_Mn:.3f} → {demo.under_Mn:.3f}, still\n  above the {demo.mn_floor:.2f} % window floor. "
          f"The tax is *sub-window*: it cannot trip off-grade — which is\n  quantitatively why the gross "
          f"under-trim hero (Cr/Mo recovery halved) in demo_ladle must be hand-set.")

    print(f"\n  Carbon→oxygen→tax coherence: the leaner {LEAN_GRADE} (0.20 %C) sits at {demo.lean_under_O:.0f} ppm "
          f"vs {GRADE}'s {demo.under_O:.0f} ppm\n  (the C–O inverse coupling), so the same skipped kill taxes "
          f"its Mn ~{demo.lean_mn_loss_pct:.1f} % — kill-before-you-trim\n  matters most where the carbon is "
          f"lowest. NO tooth: conservation arithmetic on cited oxide stoichiometry;\n  the gross slag-FeO "
          f"reoxidation distribution stays the named ceiling. The only flag is F2's porosity-risk.")


def save_figure(demo: DeoxRecoveryDemo) -> Path:
    """Render and bank the deox→recovery artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import deox_recovery_figure

    fig = deox_recovery_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ≥ on legacy codepages

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
