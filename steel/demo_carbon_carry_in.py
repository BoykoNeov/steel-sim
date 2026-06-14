"""Carbon carry-in: same trim, the ferroalloy *carbon grade* decides whether the heat lands on its carbon.

*Trim a 4140 up to grade with the cheap high-carbon ferroalloys and the carbon they carry drags the heat off
its own carbon band — a harder steel than the grade asks for; the same trim with refined low-carbon grades
lands clean.* The demonstrable artifact for the **carbon carry-in** consequence at the **ladle** stage
(:mod:`steel.ladle`) — a *second*, distinct ladle mistake beside the recovery shortfall of :mod:`steel.demo_ladle`.
Where that demo holds carbon on F2's blow (the Slice-1 clean axis) and lets a recovery shortfall miss the
**alloy** bands, this one turns on the carbon the ferroalloys carry: high-carbon (charge-grade) ferrochrome and
ferromanganese run 6–8 % C, so sizing the Cr/Mn trim drags the bath carbon **up** — off the grade's own carbon
window — and the *same* oil quench then lands a harder, off-grade martensite. The fix is the lever
:data:`~steel.ladle.LOW_CARBON_FERROALLOYS`: the same deliverers refined to ~0.5 % C, which carry the trim
without blowing the carbon. *This is why low-carbon ferroalloys exist.*

What it shows
-------------
1. **The hero — same charges, the carbon grade decides.** One alloy-lean 4140 tap, **one** set of ferroalloy
   charges sized to reach grade (identical for either alloy grade — same assay, same recovery). Mixed in with
   the **high-carbon** ferroalloys the bath carries ~+0.18 %C and lands at ~0.56 %C — **off-grade on carbon**
   (above 4140's 0.38–0.43 band), and a harder steel: the same Ø15 mm oil quench reads ~700 HV against the
   on-grade ~625 HV. Mixed with the **low-carbon** grades the carry-in is ~+0.01 %C, the heat stays at
   ~0.40 %C — **on grade**. Same trim, the carbon grade decides.
2. **The magnitude is the point (OoM coherence, not a benchmark).** The carry-in is ~0.16–0.18 %C — roughly
   **40 % of 4140's spec carbon** — computed from representative high-carbon assays. That order of magnitude
   *is* the reason a medium-carbon alloy steel cannot be trimmed with charge-grade ferroalloys; it is an
   order-of-magnitude coherence note (the assays are tier-2 representative), not a 2-significant-figure number.
3. **The verdict is the cited carbon window; the hardness is propagation colour.** Off-grade fires on the
   **carbon** band through the *same* window machinery the recovery-shortfall demo uses on the alloy bands — no
   new flag, no new physics. The hardness rise is the *validated back end* consuming the carry-in carbon (the
   over-carbon heat is metallurgically a harder steel), shown to say **why** the miss matters — not a second
   pass/fail line. F3 is spine-class: the carry-in arithmetic is mass-balance by construction, the propagation
   is the same validated link the soft core rides.

The posture: **no claimable tooth** (the carry-in is conservation arithmetic on cited ferroalloy carbon
assays; the consequence is OFF-GRADE-on-carbon plus the validated hardness propagation). Carbon recovery is
taken ~full (carbon does not oxidise off like the alloying element); the deox-state-dependent recovery and the
P/S residual bands stay named deferrals (no P/S state). The clean Slice-1 axis is still the module default —
this demo opts the carry-in *on*.

Run headless:

    python -m steel.demo_carbon_carry_in
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import heat_state as hs
from . import ladle as ld
from .heat_state import Heat
from .sweep import STEELS, evaluate

# The hero grade + set-points (continuity with the F3 ladle demo).
GRADE = "4140"
TREAT_MEDIUM = "oil"
TREAT_DIAMETER = 0.015                  # the section the recovery demo uses — on-grade through-hardens

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-carbon-carry-in.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-carbon-carry-in.png"


@dataclass(frozen=True)
class CarbonCarryInDemo:
    """What the demo produced — the same-charges HC-vs-LC contrast and the carbon→hardness propagation.

    ``tap`` the alloy-lean origin; ``hc`` / ``lc`` the trimmed, heat-treated Heats (high-carbon vs low-carbon
    ferroalloys, *same charges*). ``*_C`` the landed carbon, ``*_HV`` the back-end hardness behind the verdict,
    ``hc_off`` the elements HC drives off-grade (carbon). ``pickup_hc`` / ``pickup_lc`` the quantified carry-in
    magnitude (the OoM-coherence number), ``c_window`` the cited 4140 carbon band. ``carbon_grid`` /
    ``hv_curve`` the carbon→hardness propagation axis with the two operating points.
    """

    tap: Heat
    hc: Heat
    lc: Heat
    tap_C: float
    hc_C: float
    lc_C: float
    hc_HV: float
    lc_HV: float
    hc_off: tuple[str, ...]
    pickup_hc: float
    pickup_lc: float
    c_window: tuple[float, float]
    # figure arrays
    bar_labels: tuple[str, ...]
    bar_carbon: np.ndarray
    carbon_grid: np.ndarray
    hv_curve: np.ndarray


def _treated(ferroalloys: dict[str, ld.Ferroalloy]) -> Heat:
    """Trim a fresh tap to grade with ``ferroalloys`` (carry-in on), then heat-treat it — one trimmed Heat."""
    tap = ld.from_tap(GRADE)
    trimmed = ld.trim_to_grade(tap, GRADE, apply_carbon_pickup=True, ferroalloys=ferroalloys)
    return hs.heat_treat(trimmed, medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)


def compute() -> CarbonCarryInDemo:
    """Trim one tap two ways — high-carbon vs low-carbon ferroalloys — and read the carbon-band divergence."""
    tap = ld.from_tap(GRADE)
    charges = ld.additions_for_grade(tap.composition, STEELS[GRADE])   # same charges for either alloy grade

    hc = _treated(ld.FERROALLOYS)                  # charge-grade ferroalloys → carbon carries in
    lc = _treated(ld.LOW_CARBON_FERROALLOYS)       # refined low-carbon grades → carbon stays

    hc_o = evaluate(hc.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)
    lc_o = evaluate(lc.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)

    c_window = ld.GRADE_WINDOWS[GRADE].bands["C"]
    pickup_hc = ld.carbon_pickup_pct(charges)
    pickup_lc = ld.carbon_pickup_pct(charges, ferroalloys=ld.LOW_CARBON_FERROALLOYS)

    # Panel A — carbon bars: lean tap → LC trim (on band) → HC trim (over band), against the cited C window.
    bar_labels = ("lean tap", "LC trim\n(on grade)", "HC trim\n(off grade)")
    bar_carbon = np.array([tap.composition.C, lc.composition.C, hc.composition.C])

    # Panel B — the validated propagation: as-quenched hardness vs carbon (same Ø15 mm oil quench), the two
    # operating points riding the same curve — LC sits in the window, HC is dragged off it into a harder steel.
    base = STEELS[GRADE]
    carbon_grid = np.linspace(0.34, 0.62, 120)
    hv_curve = np.array([evaluate(replace(base, C=c), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER).HV
                         for c in carbon_grid])

    return CarbonCarryInDemo(
        tap=tap, hc=hc, lc=lc,
        tap_C=tap.composition.C, hc_C=hc.composition.C, lc_C=lc.composition.C,
        hc_HV=hc_o.HV, lc_HV=lc_o.HV, hc_off=tuple(ld.off_grade_elements(hc.composition, GRADE)),
        pickup_hc=pickup_hc, pickup_lc=pickup_lc, c_window=c_window,
        bar_labels=bar_labels, bar_carbon=bar_carbon,
        carbon_grid=carbon_grid, hv_curve=hv_curve,
    )


def print_summary(demo: CarbonCarryInDemo) -> None:
    """Print the same-charges HC-vs-LC divergence — off-grade-on-carbon and the hardness propagation."""
    lo, hi = demo.c_window
    print(f"\nCarbon carry-in — same trim, the ferroalloy carbon grade decides ({GRADE})\n")
    print(f"One alloy-lean tap (C {demo.tap_C:.2f} % on the F2 blow), ONE set of charges sized to reach grade "
          f"(same\n  assay and recovery either way). The only difference is the ferroalloy carbon grade:\n")

    for tag, heat, C, HV, note in [
        ("high-carbon ferroalloys", demo.hc, demo.hc_C, demo.hc_HV,
         f"OFF GRADE on {'/'.join(demo.hc_off)} (above the {hi:.2f} % ceiling)"),
        ("low-carbon ferroalloys ", demo.lc, demo.lc_C, demo.lc_HV, "on grade"),
    ]:
        flags = " + ".join(heat.defects).upper() if heat.defects else "clean"
        print(f"    {tag}: carbon → {C:.2f} %  →  {HV:.0f} HV  ({note})  [{flags}]")

    print(f"\n  The cited {GRADE} carbon window is {lo:.2f}–{hi:.2f} %. The high-carbon grades carry "
          f"~+{demo.pickup_hc:.2f} %C\n  into the heat (~{demo.pickup_hc / STEELS[GRADE].C:.0%} of the grade's "
          f"carbon); the low-carbon grades carry ~+{demo.pickup_lc:.2f} %C.\n  Same charges, the carbon grade "
          f"decides — and that ~0.16–0.18 %C magnitude is *why low-carbon ferroalloys exist*.")

    print(f"\n→ The verdict is OFF-GRADE on the CARBON band (the same window machinery the recovery-shortfall "
          f"demo\n  uses on the alloy bands — no new flag). The +{demo.hc_HV - demo.lc_HV:.0f} HV is the "
          f"validated back end consuming\n  the carry-in carbon (the over-carbon heat is a harder steel) — "
          f"propagation colour, not a second pass/fail\n  line. NO claimable tooth: the carry-in is mass-balance "
          f"on cited assays; carbon recovery taken ~full.\n  Named deferrals: deox-state-dependent recovery, "
          f"and P/S residual bands (no P/S state). F3 is spine-class.")


def save_figure(demo: CarbonCarryInDemo) -> Path:
    """Render and bank the carbon-carry-in artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import carbon_carry_in_figure

    fig = carbon_carry_in_figure(demo)
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
