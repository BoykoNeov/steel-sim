"""Gas porosity: same oxygen spec, two carbons — one casting blows holes, one is sound (carbon-aware).

*Whether dissolved oxygen blows CO holes is set by the carbon it has to react with, not the oxygen number
alone.* The demonstrable artifact for the oxygen consequence F2 (:mod:`steel.refining`) deferred: refining
fills the dissolved oxygen and flags a single, **carbon-blind** chemistry-state **risk** (O > 30 ppm); this
reads whether a *casting* actually develops **CO porosity**, which is a carbon-aware question
(``[%C]·[%O] > K_CO``). Two-tier, like hydrogen-flaking (risk → consequence) — but where flaking's second
lever was geometric, this one is the **carbon** the oxygen has to find.

What it shows
-------------
1. **The hero — same deoxidizer treatment, the carbon decides.** A high-carbon heat (1080) and a low-carbon
   heat (8620) are given the *same* light (under-)kill, leaving **both within refining's 30 ppm oxygen spec
   → both risk-cleared**. Yet the 1080 sits right on the CO line (its carbon-aware oxygen limit is only
   ~25 ppm) and **blows holes**; the 8620 has an order of magnitude of carbon-margin (limit ~100 ppm) and is
   **sound**. The 1080 even carries *less* dissolved oxygen than the 8620 — and is still the one that
   cracks. Same oxygen, the carbon decides: refining's flat oxygen line cannot see it.
2. **The deox lever.** That same 1080 *is* saved — by killing it harder (a full aluminium kill drops its
   oxygen well under the carbon-aware line). The fix is upstream deoxidation, the mirror of flaking's bake.
3. **The carbon-blindness, drawn.** The carbon-aware limit ``O_crit(C) = K_CO/[%C]`` falls as ``1/C`` and
   crosses refining's flat 30 ppm line near C ≈ 0.67 %: leaner, the spec over-warns (flags sound heats);
   richer, it under-warns (clears heats that blow holes). The consequence corrects both.

The posture (carried from :mod:`gas_porosity`): a thin consumer (the hydrogen-flaking class), **no claimable
tooth** — the criterion *is* the cited C–O equilibrium against held composition. The one soft OoM-coherence
note is "high-carbon must be killed, low-carbon can be rimmed" falling out of ``O_crit = K_CO/C`` with no
tuning. The solidification CO-margin panel is a **conservative secondary** (Scheil over-predicts carbon), not
the verdict; the model is the CO-evolution *criterion*, not the bubble-escape kinetics (the named ceiling).

Run headless:

    python -m steel.demo_gas_porosity
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import gas_porosity as gp
from . import refining
from .heat_state import Heat
from .sweep import STEELS

GRADE_HIGH_C = "1080"             # 0.80 %C — sits right on the CO line even barely killed
GRADE_LOW_C = "8620"             # 0.20 %C — an order of magnitude of carbon-margin
UNDERKILL_AL = 0.0015            # a token aluminium addition — far short of a full kill (under-killed)
FULL_KILL_AL = 0.04             # a proper aluminium kill — the deox lever that saves the high-carbon heat

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-gas-porosity.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-gas-porosity.png"


@dataclass(frozen=True)
class GasPorosityDemo:
    """What the demo produced — the carbon-decides hero, the deox lever, and the carbon-blindness curve."""

    risk_spec_ppm: float
    K_CO: float
    crossover_C: float
    # hero: same kill, two carbons (both under the 30 ppm spec)
    high_C: float
    low_C: float
    high_O_ppm: float
    low_O_ppm: float
    high_Ocrit: float
    low_Ocrit: float
    high_S: float
    low_S: float
    high_risk: bool
    low_risk: bool
    high_porous: bool
    low_porous: bool
    # the deox lever: the high-carbon heat saved by a full kill
    killed_O_ppm: float
    killed_S: float
    killed_porous: bool
    # panel — the O_crit(C) carbon-aware line vs the flat refining spec
    carbon_grid: np.ndarray
    Ocrit_curve_ppm: np.ndarray
    # panel — supersaturation S of the three heats
    bar_labels: tuple[str, ...]
    bar_S: np.ndarray
    # panel — the conservative secondary solidification CO-margin vs carbon (NOT the verdict)
    margin_carbon: np.ndarray
    margin_fs: np.ndarray


def _heat(grade: str, al_pct: float) -> Heat:
    """Refine a heat honestly: charge → blow to the grade carbon → (under-)kill with ``al_pct`` aluminium."""
    h = refining.from_hot_metal(STEELS[grade])
    h = refining.decarburize(h, STEELS[grade].C)
    return refining.deoxidize(h, "Al", al_pct)


def compute() -> GasPorosityDemo:
    """Refine high- and low-carbon heats to the same light kill, then read the CO-porosity contrast."""
    high = _heat(GRADE_HIGH_C, UNDERKILL_AL)
    low = _heat(GRADE_LOW_C, UNDERKILL_AL)
    killed = _heat(GRADE_HIGH_C, FULL_KILL_AL)

    high_out = gp.gas_porosity_check(high)
    low_out = gp.gas_porosity_check(low)
    killed_out = gp.gas_porosity_check(killed)

    a_high = gp.porosity_assessment(high.composition.C, high.oxygen_ppm)
    a_low = gp.porosity_assessment(low.composition.C, low.oxygen_ppm)
    a_killed = gp.porosity_assessment(killed.composition.C, killed.oxygen_ppm)

    carbon_grid = np.linspace(0.05, 1.10, 120)
    Ocrit_curve = np.array([gp.critical_oxygen(c) for c in carbon_grid])

    bar_labels = (f"{GRADE_HIGH_C}\nunder-killed", f"{GRADE_LOW_C}\nunder-killed", f"{GRADE_HIGH_C}\nkilled")
    bar_S = np.array([a_high.supersaturation, a_low.supersaturation, a_killed.supersaturation])

    margin_carbon = np.linspace(0.05, 1.10, 120)
    margin_fs = np.array([gp.solidification_co_fraction(c, 10.0) for c in margin_carbon])  # at a fixed 10 ppm

    return GasPorosityDemo(
        risk_spec_ppm=gp.POROSITY_RISK_O_PPM, K_CO=a_high.K_CO,
        crossover_C=gp.co_equilibrium_product() / (gp.POROSITY_RISK_O_PPM * 1e-4),
        high_C=high.composition.C, low_C=low.composition.C,
        high_O_ppm=high.oxygen_ppm, low_O_ppm=low.oxygen_ppm,
        high_Ocrit=a_high.critical_oxygen, low_Ocrit=a_low.critical_oxygen,
        high_S=a_high.supersaturation, low_S=a_low.supersaturation,
        high_risk=high.has_defect(refining.POROSITY_RISK), low_risk=low.has_defect(refining.POROSITY_RISK),
        high_porous=high_out.has_defect(gp.GAS_POROSITY), low_porous=low_out.has_defect(gp.GAS_POROSITY),
        killed_O_ppm=killed.oxygen_ppm, killed_S=a_killed.supersaturation,
        killed_porous=killed_out.has_defect(gp.GAS_POROSITY),
        carbon_grid=carbon_grid, Ocrit_curve_ppm=Ocrit_curve,
        bar_labels=bar_labels, bar_S=bar_S,
        margin_carbon=margin_carbon, margin_fs=margin_fs,
    )


def print_summary(demo: GasPorosityDemo) -> None:
    """Print the two-tier story: a carbon-blind oxygen risk, then the carbon-aware porosity consequence."""
    print(f"\nGas (CO) porosity — same oxygen spec, the carbon decides\n")
    print(f"Refining's risk line is carbon-blind: O > {demo.risk_spec_ppm:.0f} ppm. The consequence is "
          f"carbon-aware:\n  CO evolves where [%C]·[%O] > K_CO = {demo.K_CO:.4f} wt%² "
          f"(O_crit = K_CO/[%C]).\n")

    print(f"Same light aluminium kill, two carbons — BOTH within the {demo.risk_spec_ppm:.0f} ppm spec "
          f"(both risk-cleared):")
    print(f"    {GRADE_HIGH_C} {demo.high_C:.2f} %C: O {demo.high_O_ppm:4.1f} ppm "
          f"(O_crit {demo.high_Ocrit:3.0f}), S = {demo.high_S:.2f} → "
          f"{'POROUS' if demo.high_porous else 'sound'}   (refining risk: {demo.high_risk})")
    print(f"    {GRADE_LOW_C} {demo.low_C:.2f} %C: O {demo.low_O_ppm:4.1f} ppm "
          f"(O_crit {demo.low_Ocrit:3.0f}), S = {demo.low_S:.2f} → "
          f"{'POROUS' if demo.low_porous else 'sound'}   (refining risk: {demo.low_risk})")
    print(f"  → the {GRADE_HIGH_C} carries {'less' if demo.high_O_ppm < demo.low_O_ppm else 'more'} oxygen "
          f"than the {GRADE_LOW_C}, yet it is the one that blows holes — the carbon, not the oxygen, decides.")

    print(f"\nThe deox lever — the high-carbon heat saved by a full kill:")
    print(f"    {GRADE_HIGH_C} {demo.high_C:.2f} %C + full Al kill: O {demo.killed_O_ppm:.1f} ppm, "
          f"S = {demo.killed_S:.2f} → {'POROUS' if demo.killed_porous else 'sound'}")

    print(f"\nThe carbon-blindness: O_crit = K_CO/[%C] crosses the flat {demo.risk_spec_ppm:.0f} ppm spec at "
          f"C ≈ {demo.crossover_C:.2f} %.")
    print("  Leaner → the spec over-warns (flags sound heats); richer → it under-warns (clears heats that "
          "blow holes).")
    print("\n→ No claimable tooth (the criterion is the cited C–O equilibrium vs held composition); the soft "
          "OoM note is\n  'high-C must be killed, low-C can be rimmed' from O_crit ∝ 1/C. The solidification "
          "margin is a\n  conservative secondary (Scheil over-predicts C), not the verdict.")


def save_figure(demo: GasPorosityDemo) -> Path:
    """Render and bank the gas-porosity artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import gas_porosity_figure

    fig = gas_porosity_figure(demo)
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
