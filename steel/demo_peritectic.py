"""Peritectic surface cracking: carbon decides, non-monotonically — the ~0.1 %C continuous-casting window.

*Whether a casting surface-cracks is set by where the carbon sits relative to the peritectic, not by "more
carbon is worse".* The demonstrable artifact for the **carbon-driven** casting-cracking consequence (the
sibling of the sulfur-driven :mod:`steel.hot_tear`): the peritectic transformation ``L + δ → γ`` is a volume
contraction (BCC δ → denser FCC γ) that, concentrated high in the mould, shrinks the thin shell off the wall
and tears it into longitudinal facial cracks. The hypo-peritectic ``~0.10–0.16 wt% C`` grades are the worst
— and, counter-intuitively, a *leaner* OR a *richer* steel casts more soundly.

What it shows
-------------
1. **The hero — carbon decides, non-monotonically.** Three plain-carbon heats differing only in carbon: a
   lean 0.05 %C (sub-peritectic, solidifies fully δ → sound), a peritectic 0.11 %C (Wolf FP in the depression
   band → cracks), and a rich 0.45 %C (1045-like, solidifies austenitic → sound). A 0.11 %C steel cracks
   where both a leaner and a richer one are sound — **more carbon can be safer**, the signature of the
   peritectic. (Mirrors gas-porosity's "same O, carbon decides", here on carbon alone.)
2. **The mechanism — the Fe–C peritectic lever rule.** The δ-ferrite the front carries and the δ the rapid
   peritectic reaction transforms (the contraction source), from the cited invariant points
   ``L(0.53) + δ(0.09) → γ(0.17)`` at 1495 °C. The δ→γ contraction is concentrated only where the peritectic
   reaction runs (0.09–0.53 %C) — leaner grades transform slowly in the solid state, richer ones solidify
   austenitic.
3. **The alloying lever — same carbon, the stabilizers decide.** Two heats at the *same* 0.20 %C — one plain
   (austenitic, sound) and one with ferrite stabilizers (Si + Cr) that pull the **carbon equivalent** down
   into the crack band (crack). Alloying shifts the effective carbon, so a grade that looks safe on carbon
   alone can be peritectic — the reason Wolf's ferrite potential uses a carbon equivalent, not raw carbon.

The posture (carried from :mod:`peritectic`): a thin consumer, **no claimable tooth** — the verdict *is*
Wolf's cited ferrite-potential band on a (representative) carbon equivalent, and the mechanism *is* the Fe–C
lever rule (carbon mass balance). The one soft note is a **coherence** (carefully named: the two are not
independent — both rest on the Fe–C peritectic): the thermodynamic lever rule and Wolf's *empirical* FP place
the trouble at the same ~0.1 %C window — the mechanism explains *why* the depression band sits there. The
δ→γ contraction *magnitude* and the carbon-equivalent coefficients are representative (illustrative); the
exact worst-carbon needs δ→γ kinetics + shell mechanics — underdetermined, not wrong-placed.

Run headless:

    python -m steel.demo_peritectic
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import peritectic as pk
from .heat_state import Heat
from .sweep import STEELS

# A plain-carbon cast backbone; the hero heats differ only in carbon (the control axis). Lean of alloy so the
# plain-carbon FP = %C story is clean (the alloying lever adds Si/Cr deliberately, below).
_BACKBONE = replace(STEELS["1045"], C=0.11, Mn=0.0, Si=0.0, Cr=0.0, Mo=0.0, Ni=0.0, P=0.0, S=0.0,
                    name="cast structural")

C_LEAN = 0.05      # sub-peritectic: solidifies fully δ → sound
C_PERITECTIC = 0.11  # hypo-peritectic: Wolf FP in the depression band → cracks
C_RICH = 0.45      # hyper-peritectic (1045-like): solidifies austenitic → sound

# The alloying lever — same carbon, ferrite stabilizers pull Cp into the band.
C_ALLOY = 0.20     # plain: FP just austenitic (sound) ...
ALLOY_SI, ALLOY_CR = 0.50, 1.00   # ... + ferrite stabilizers → Cp into the crack band (crack)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-peritectic.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-peritectic.png"


@dataclass(frozen=True)
class PeritecticDemo:
    """What the demo produced — the non-monotonic carbon hero, the lever-rule mechanism, the alloying lever."""

    fp_low: float
    fp_high: float
    fp_max: float
    # crack-band carbon edges for plain carbon (Cp = %C)
    c_band_low: float
    c_band_high: float
    # cited peritectic invariant points
    c_delta: float
    c_gamma: float
    c_liquid: float
    t_peritectic: float
    # the three hero heats: (label, C, Cp, FP, crack, regime, flagged)
    heroes: tuple[tuple[str, float, float, float, bool, str, bool], ...]
    # the alloying lever pair: (label, C, Cp, FP, crack)
    alloy_pair: tuple[tuple[str, float, float, float, bool], ...]
    # panel — Wolf FP vs carbon (the verdict)
    c_grid: np.ndarray
    fp_curve: np.ndarray
    # panel — the lever-rule mechanism vs carbon
    delta_above_curve: np.ndarray
    delta_consumed_curve: np.ndarray


def _hero(label: str, C: float) -> tuple[str, float, float, float, bool, str, bool]:
    comp = replace(_BACKBONE, C=C)
    a = pk.peritectic_assessment(comp)
    out = pk.peritectic_crack_check(Heat(composition=comp))
    return label, a.C, a.Cp, a.fp, a.crack_susceptible, a.regime, out.has_defect(pk.PERITECTIC_CRACK)


def compute() -> PeritecticDemo:
    """Assess the non-monotonic carbon hero, the lever-rule mechanism, and the alloying lever."""
    heroes = (
        _hero(f"{C_LEAN:.2f} %C\n(lean)", C_LEAN),
        _hero(f"{C_PERITECTIC:.2f} %C\n(peritectic)", C_PERITECTIC),
        _hero(f"{C_RICH:.2f} %C\n(rich)", C_RICH),
    )

    plain = replace(_BACKBONE, C=C_ALLOY)
    alloyed = replace(_BACKBONE, C=C_ALLOY, Si=ALLOY_SI, Cr=ALLOY_CR)
    alloy_pair = tuple(
        (label, a.C, a.Cp, a.fp, a.crack_susceptible)
        for label, a in (
            (f"{C_ALLOY:.2f} %C\nplain", pk.peritectic_assessment(plain)),
            (f"{C_ALLOY:.2f} %C\n+Si+Cr", pk.peritectic_assessment(alloyed)),
        )
    )

    c_grid = np.linspace(0.0, 0.60, 300)
    fp_curve = np.array([pk.ferrite_potential(c) for c in c_grid])
    delta_above_curve = np.array([pk.delta_fraction_above_peritectic(c) for c in c_grid])
    delta_consumed_curve = np.array([pk.delta_consumed_by_peritectic(c) for c in c_grid])

    return PeritecticDemo(
        fp_low=pk.FP_CRACK_LOW, fp_high=pk.FP_CRACK_HIGH, fp_max=pk.FP_PERITECTIC_MAX,
        c_band_low=pk.FP_REFERENCE_C - pk.FP_CRACK_HIGH / pk.FP_SLOPE,
        c_band_high=pk.FP_REFERENCE_C - pk.FP_CRACK_LOW / pk.FP_SLOPE,
        c_delta=pk.C_DELTA_PERITECTIC, c_gamma=pk.C_GAMMA_PERITECTIC, c_liquid=pk.C_LIQUID_PERITECTIC,
        t_peritectic=pk.T_PERITECTIC,
        heroes=heroes, alloy_pair=alloy_pair,
        c_grid=c_grid, fp_curve=fp_curve,
        delta_above_curve=delta_above_curve, delta_consumed_curve=delta_consumed_curve,
    )


def print_summary(demo: PeritecticDemo) -> None:
    """Print the carbon-decides story: the non-monotonic hero, the lever mechanism, the alloying lever."""
    print("\nPeritectic surface cracking — carbon decides, non-monotonically (δ→γ contraction)\n")
    print(f"Wolf's ferrite potential FP = 2.5·(0.5 − Cp): the peritectic reaction is maximal at FP = "
          f"{demo.fp_max:.1f}, and the\n  crack-susceptible 'depression' band is "
          f"{demo.fp_low:.2f} < FP < {demo.fp_high:.2f} (Cp ≈ {demo.c_band_low:.2f}–{demo.c_band_high:.2f} %C "
          f"for plain carbon).\n  Mechanism: L({demo.c_liquid:.2f}) + δ({demo.c_delta:.2f}) → "
          f"γ({demo.c_gamma:.2f}) at {demo.t_peritectic:.0f} °C — a BCC→FCC volume contraction.\n")

    print("Hero — three plain-carbon heats, carbon the only axis:")
    for label, C, Cp, fp, crack, regime, flagged in demo.heroes:
        tag = "PERITECTIC-CRACK" if crack else "sound"
        print(f"    {label.replace(chr(10), ' '):22s} C {C:.3f} %  FP {fp:5.2f}  {regime:16s} → {tag}")
    print("  → the 0.11 %C heat cracks though BOTH the leaner and the richer heat are sound — more carbon is "
          "safer.\n    The flat 'more carbon = worse' intuition cannot see the peritectic window.")

    print("\nThe alloying lever — same carbon, the stabilizers decide:")
    for label, C, Cp, fp, crack in demo.alloy_pair:
        tag = "PERITECTIC-CRACK" if crack else "sound"
        print(f"    {label.replace(chr(10), ' '):22s} C {C:.3f} %  Cp {Cp:.3f} %  FP {fp:5.2f}  → {tag}")
    print("  → identical carbon: ferrite stabilizers (Si + Cr) pull the carbon EQUIVALENT into the band — a "
          "grade\n    safe on carbon alone is peritectic. (Representative coefficients — the directional "
          "second story.)")

    print(f"\nThe soft coherence note (NO claimable tooth): the Fe–C lever rule and Wolf's empirical FP — NOT "
          f"independent\n  (both rest on the Fe–C peritectic) — place the trouble at the same ~0.1 %C window; "
          f"the mechanism explains\n  WHY the depression band sits there. The δ→γ contraction peaks at the "
          f"band EDGE (Cγ = {demo.c_gamma:.2f}), not the\n  empirical worst (~0.11) — the exact worst-carbon "
          f"needs δ→γ kinetics + shell mechanics (underdetermined).")
    print("\n→ Ceiling: equilibrium lever rule + a representative carbon equivalent (ISIJ-2015 multicomponent "
          "shifting,\n  and the strain-rate / feeding driver in steel.solidification, are referenced not "
          "rebuilt). No engine, no ADR.")


def save_figure(demo: PeritecticDemo) -> Path:
    """Render and bank the peritectic artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import peritectic_figure

    fig = peritectic_figure(demo)
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
