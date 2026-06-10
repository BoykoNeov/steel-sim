"""The Phase-6b demo: the cited bainite reaction, and why its bay can't be realised here.

*Composition in, the bay's **mechanism** out — and the honest reason it stays a mechanism.*
Phase 6b set out to give bainite its own competing C-curve so the **bainite bay** would open in
the continuous-cooling microstructure (the §4 simplification: one Grossmann factor shifts pearlite
and bainite together). A four-round empirical investigation (:mod:`kinetics` §6) proved the bay
**cannot be realised in this model** — the project pearlite curve is deliberately under-shifted
(Jominy-pinned ``M`` ≈ 8× where a real bay needs ~100×), its nose is carbon-flat at 550 °C (inside
the bainite band for lean steels), and ``BC``'s large carbon coefficient makes the 0.20 %C 8620 core
explode into bainite at any scale that would put bainite into 1045/4140. So 6b delivers the **cited
reaction** and the bay's **mechanism**, not the bay itself.

This demo banks that honestly in two panels (``plots.bainite_figure``):

1. **The coefficient bay (the teeth, scale-free).** As Cr is added, the *reconstructive* ferrite
   reaction (``FC``) is retarded **steeply** while the *displacive* bainite reaction (``BC``) is
   retarded **gently** — the published Li/KV coefficients alone, no calibration. This is the §4 fix
   at the mechanism level: the cause of the bay.
2. **The bainite C-curve, beside pearlite (4140).** The reaction is real and has its own nose below
   ``Bs`` — but in *this* model the bainite and pearlite noses sit close in absolute time, so a
   continuous cool can't dodge pearlite into a bay. The absolute times are **unanchored** (the same
   modest-``M`` time-base compression, named not validated); the validated content is the coefficient
   ratio, not the nose position.

Run headless (saves the figure, prints the summary):

    python -m steel.demo_bainite
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import kinetics as kin

# The two benchmark steels — 4140 (the alloy steel that *should* show a bay) and 1045 (lean).
STEEL_4140 = dict(C=0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)
STEEL_1045 = dict(C=0.45, Mn=0.75, Si=0.22)

# The Cr sweep for the coefficient-bay panel: a fixed 0.40 %C base, Cr 0 → 1.5 wt%.
CR_SWEEP = np.linspace(0.0, 1.5, 61)
SWEEP_BASE_C = 0.40

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-bainite.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-bainite.png"


@dataclass(frozen=True)
class BainiteDemo:
    """Validated arrays for the Phase-6b figure (the plot layer only draws these)."""

    # Panel 1 — the coefficient bay (retardation vs Cr, relative to plain 0.40 %C).
    cr: np.ndarray
    bainite_retardation: np.ndarray         # BC(Cr)/BC(0) — gentle (the displacive reaction)
    ferrite_retardation: np.ndarray         # FC(Cr)/FC(0) — steep (the reconstructive reaction)
    # Panel 2 — the 4140 pearlite + bainite TTT start curves.
    temps: np.ndarray                       # °C, the shared temperature axis (Ms_4140 → A1)
    pearlite_tau: np.ndarray                # s, pearlite start time τ_0.01(T) (the project curve)
    bainite_tau: np.ndarray                 # s, bainite start time S(0.01)/K(T) (nan above Bs)
    pearlite_nose: tuple                    # (T °C, t s)
    bainite_nose: tuple                     # (T °C, t s)
    bs_4140: float                          # the bainite ceiling (Steven–Haynes), °C
    # The teeth scalar (scale-free): 4140 alloy retardation of ferrite vs bainite.
    alloy_ferrite_retardation: float
    alloy_bainite_retardation: float


def compute() -> BainiteDemo:
    """Build the validated arrays for the figure — the coefficient sweep and the 4140 TTT curves."""
    # Panel 1 — relative retardation of each reaction as Cr is added (the bay's mechanism).
    bc0 = kin.bainite_BC(SWEEP_BASE_C)
    fc0 = kin.ferrite_FC(SWEEP_BASE_C)
    bain_ret = np.array([kin.bainite_BC(SWEEP_BASE_C, Cr=cr) / bc0 for cr in CR_SWEEP])
    ferr_ret = np.array([kin.ferrite_FC(SWEEP_BASE_C, Cr=cr) / fc0 for cr in CR_SWEEP])

    # Panel 2 — the 4140 pearlite + bainite start curves on a shared T axis.
    cc = kin.ccurve_for_steel(**STEEL_4140)
    br = kin.bainite_reaction_for_steel(**STEEL_4140)
    temps = np.linspace(cc.Ms + 2.0, cc.T_eq - 2.0, 400)
    pearlite_tau = np.array([cc.time_to_fraction(float(T), 0.01) for T in temps])
    S = kin._kv_shape_integral(0.01)
    bainite_tau = np.array([
        (S / br.rate(float(T))) if (T < br.Bs and br.rate(float(T)) > 0.0) else np.nan
        for T in temps
    ])

    # The scale-free teeth scalar: how much 4140's full alloy load retards each reaction.
    alloy = dict(Mn=0.90, Cr=1.0, Mo=0.20)
    return BainiteDemo(
        cr=CR_SWEEP,
        bainite_retardation=bain_ret,
        ferrite_retardation=ferr_ret,
        temps=temps,
        pearlite_tau=pearlite_tau,
        bainite_tau=bainite_tau,
        pearlite_nose=cc.nose(0.01),
        bainite_nose=br.nose(0.01),
        bs_4140=br.Bs,
        alloy_ferrite_retardation=kin.ferrite_FC(0.40, **alloy) / kin.ferrite_FC(0.40),
        alloy_bainite_retardation=kin.bainite_BC(0.40, **alloy) / kin.bainite_BC(0.40),
    )


def print_summary(d: BainiteDemo) -> None:
    """Print the teeth, the noses, and the named negative result."""
    print("\nPhase 6b — the bainite reaction (cited) and the bay's mechanism\n")
    print(f"THE TEETH (scale-free, cited Li/KV coefficients): 4140's alloy load retards")
    print(f"  the reconstructive FERRITE reaction  ×{d.alloy_ferrite_retardation:6.1f}  (FC: Cr 2.70, Mo 4.06)")
    print(f"  the displacive    BAINITE reaction   ×{d.alloy_bainite_retardation:6.1f}  (BC: Cr 0.90, Mo 0.36)")
    print(f"  → alloy retards bainite ~{d.alloy_ferrite_retardation / d.alloy_bainite_retardation:.0f}× LESS"
          f" than ferrite — the cause of the bay (the §4 fix, at the mechanism level).\n")
    print(f"4140 TTT noses (scale = {kin.BAINITE_KINETIC_SCALE:.0f}, a DEMONSTRATION parameter — absolute times unanchored):")
    print(f"  pearlite nose  {d.pearlite_nose[0]:5.0f} °C / {d.pearlite_nose[1]:8.2g} s")
    print(f"  bainite  nose  {d.bainite_nose[0]:5.0f} °C / {d.bainite_nose[1]:8.2g} s   (ceiling Bs = {d.bs_4140:.0f} °C)")
    print("\nWHY THE BAY ISN'T REALISED (the proven negative result — pathint left byte-identical):")
    print("  the pearlite curve is Jominy-pinned to a modest ~8× alloy shift (a real bay needs ~100×),")
    print("  its nose is carbon-flat at 550 °C, and BC's carbon coefficient makes the 0.20 %C 8620 core")
    print("  explode into bainite at any scale that would put bainite into 1045/4140. The crude 540 °C")
    print("  morphology split is left untouched — it is the better bainite stand-in at any safe scale.")


def save_figure(d: BainiteDemo) -> Path:
    """Render and save the Phase-6b artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import bainite_figure

    fig = bainite_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, × on legacy codepages

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
