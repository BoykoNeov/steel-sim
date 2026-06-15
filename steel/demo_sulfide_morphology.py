"""MnS morphology: same sulfur, the *shape* decides — the free-machining asset and the toughness liability.

*The same manganese sulfide that makes a steel free-cutting also robs its through-thickness toughness — and
which one dominates is set by how the MnS is shaped, not by how much sulfur there is.* The demonstrable
artifact for the **signed sulfur foil** (:mod:`steel.sulfide_morphology`): slag (:mod:`steel.slag`) raises a
single, flat **``high-sulfur``** risk (S > 0.040 %) that fires on every free-machining grade by design; this
**disambiguates** that flag into its good half (free-machining) and its bad half (short-transverse toughness
anisotropy), and shows the lever — sulfide shape control — that keeps the one without the other.

What it shows
-------------
1. **The hero — same sulfur, the morphology decides.** One resulfurized 1144-type heat (S ≈ 0.24 %, well
   over the 0.040 % line, so ``high-sulfur`` is already raised) read two ways. **As-rolled** the MnS stringers
   out: free-machining **and** anisotropic (short-transverse toughness below the acceptance line — the
   ``sulfide-anisotropy`` defect). **Shape-controlled** (a calcium treatment globularizes the MnS): still
   free-machining, now isotropic. Same sulfur, same MnS *volume* — only the shape changed, and the flat
   sulfur line cannot see it.
2. **One MnS, two opposite signs (by construction).** The free-machining benefit and the anisotropy debit are
   read off the *same* MnS volume fraction with opposite signs — the machinability index rises with it, the
   short-transverse toughness ratio falls with it. The teaching beat, stated as what it is: one number, two
   laws, not a coincidence.
3. **The other end of the trade — you cannot machine freely without the MnS.** A plain 1045 (S ≈ 0.020 %,
   within spec) carries too little MnS to break the chip: tough and isotropic, but **not** free-machining.
   Low sulfur buys toughness at the cost of machinability; shape control is what buys both.

The posture (carried from :mod:`sulfide_morphology`): a thin consumer, **no claimable tooth** — the verdict is
slag's by-construction MnS amount (Mushet stoichiometry) converted to a volume fraction (cited densities) fed
to two representative laws. The machinability index is the **MnS contribution only** (the real rating is
confounded by hardness/carbon and by Pb/Ca/Te); the transverse-toughness debit is its **own** directional
axis, not the hardness-based toughness proxy or the DBTT. The stringer aspect ratio (∝ rolling reduction) is
a named ceiling; the elongated/globular toggle is a two-state stand-in.

Run headless:

    python -m steel.demo_sulfide_morphology
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import slag
from . import sulfide_morphology as sm
from .heat_state import Heat
from .sweep import STEELS

# A free-machining 1144-type backbone and a plain 1045 — the only axes that move are Mn, S, and the shape.
_FREE_MACHINING = replace(STEELS["1045"], C=0.45, Mn=1.40, Si=0.25, P=0.0, S=0.24, name="1144 (resulfurized)")
_PLAIN = replace(STEELS["1045"], C=0.45, Mn=0.75, Si=0.25, P=0.0, S=0.020, name="1045 (plain)")

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-sulfide-morphology.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-sulfide-morphology.png"


@dataclass(frozen=True)
class SulfideMorphologyDemo:
    """What the demo produced — the shape-decides hero, the signed trade-off curves, and the plain foil."""

    s_spec_pct: float
    free_machining_floor_volpct: float
    transverse_spec: float
    # the three readings: (label, S, MnS vol%, machinability, free_machining, transverse_ratio, anisotropic, risk)
    readings: tuple[tuple[str, float, float, float, bool, float, bool, bool], ...]
    # signed-trade-off curves over a MnS volume-fraction grid
    volpct_grid: np.ndarray
    machinability_curve: np.ndarray
    transverse_elongated_curve: np.ndarray
    transverse_globular_curve: np.ndarray


def _read(comp, *, shape_controlled: bool) -> tuple[str, float, float, float, bool, float, bool, bool]:
    """Run the orchestrator + assessment for one composition/shape and pack the figure-row tuple."""
    heat = Heat(composition=comp)
    out = sm.sulfide_morphology_check(heat, shape_controlled=shape_controlled)
    a = sm.sulfide_morphology_assessment(comp.Mn, comp.S, shape_controlled=shape_controlled)
    shape_tag = "globular" if shape_controlled else "as-rolled"
    label = f"{comp.name}\n{shape_tag}"
    return (
        label, comp.S, a.mns_volume_fraction, a.machinability_index, a.free_machining,
        a.transverse_ratio, out.has_defect(sm.SULFIDE_ANISOTROPY), comp.S > slag.MAX_SULFUR_PCT,
    )


def compute() -> SulfideMorphologyDemo:
    """Read the resulfurized heat as-rolled and shape-controlled, and the plain heat — the signed contrast."""
    readings = (
        _read(_FREE_MACHINING, shape_controlled=False),   # free-machining + anisotropic
        _read(_FREE_MACHINING, shape_controlled=True),    # free-machining + isotropic (the lever)
        _read(_PLAIN, shape_controlled=False),            # not free-machining + isotropic
    )

    volpct_grid = np.linspace(0.0, 1.6, 200)
    machinability_curve = np.array([sm._machinability_from_volpct(v) for v in volpct_grid])
    transverse_elongated_curve = np.array([sm._transverse_ratio_from_volpct(v, sm.ELONGATED) for v in volpct_grid])
    transverse_globular_curve = np.array([sm._transverse_ratio_from_volpct(v, sm.GLOBULAR) for v in volpct_grid])

    return SulfideMorphologyDemo(
        s_spec_pct=slag.MAX_SULFUR_PCT,
        free_machining_floor_volpct=sm.FREE_MACHINING_MIN_VOLPCT,
        transverse_spec=sm.MIN_TRANSVERSE_RATIO_SPEC,
        readings=readings,
        volpct_grid=volpct_grid,
        machinability_curve=machinability_curve,
        transverse_elongated_curve=transverse_elongated_curve,
        transverse_globular_curve=transverse_globular_curve,
    )


def print_summary(demo: SulfideMorphologyDemo) -> None:
    """Print the two-tier story: a flat sulfur risk line, then the signed morphology consequence."""
    print("\nMnS morphology — same sulfur, the shape decides (the signed sulfur foil)\n")
    print(f"Slag's risk line is flat and shape-blind: S > {demo.s_spec_pct:.3f} % → 'high-sulfur'. But that "
          f"sulfur is\n  added ON PURPOSE in free-machining grades. The MnS it forms is signed: a chip-breaking "
          f"asset by\n  volume, a through-thickness toughness liability by shape. This splits the flat flag.\n")

    print(f"Free-machining needs MnS ≳ {demo.free_machining_floor_volpct:.2f} vol %; through-thickness toughness "
          f"is off-spec below {demo.transverse_spec:.0%} of longitudinal:")
    for label, S, volpct, mach, free, transverse, aniso, risk in demo.readings:
        good = "free-machining" if free else "NOT free-machining"
        bad = "ANISOTROPIC" if aniso else "isotropic"
        print(f"    {label.replace(chr(10), ' '):28s} S {S:.3f} % (risk: {risk})  MnS {volpct:.2f} vol %  "
              f"mach ×{mach:.2f}  → {good}, {bad} (S-T {transverse:.0%})")
    print("  → the SAME resulfurized heat is free-machining either way; as-rolled it is anisotropic, "
          "shape-controlled\n    (globular MnS) it is not — the lever is the shape, not the sulfur. The plain "
          "heat is tough but cannot\n    free-machine: low sulfur buys toughness at the cost of the chip-breaker.")

    print("\nOne MnS, two opposite signs (NO claimable tooth — by construction): the machinability index rises "
          "with the\n  MnS volume fraction and the short-transverse toughness ratio falls with it — one number, "
          "two laws.\n  The machinability index is the MnS contribution only (hardness/carbon and Pb/Ca/Te "
          "confound the real\n  AISI rating); the transverse debit is its own directional axis, not the hardness "
          "toughness proxy or DBTT.")
    print("\n→ Ceiling: the stringer aspect ratio (∝ rolling reduction) is not modelled — the elongated/globular "
          "toggle is\n  a two-state stand-in; the debit assumes through-thickness loading; MnS elongates because "
          "it is plastic\n  (rigid oxides stay spherical) — narrative, not resolved.")


def save_figure(demo: SulfideMorphologyDemo) -> Path:
    """Render and bank the sulfide-morphology artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import sulfide_morphology_figure

    fig = sulfide_morphology_figure(demo)
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
