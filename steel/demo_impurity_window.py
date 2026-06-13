"""Closing the impurity consequences: phosphorus (cold-short) and sulfur (red-short) bracket the workable window.

*The same high-phosphorus, sulfurous pig iron, made into cracking steel by the acid Bessemer process and into
sound steel by the basic process + Mushet's manganese + ladle desulfurization — and the two failure
mechanisms that close the workable temperature window from both ends.* This is the demonstrable artifact for
the **impurity-consequence** slices (``docs/plans/steel-making.md`` §14): the consumers that finally **close**
what F2 Slice 2 (:mod:`steel.slag`) only set as inert state.

The two consequences — two impurities, two mechanisms, two classes
------------------------------------------------------------------
* **Phosphorus → cold-shortness (a PROPAGATION).** P threads the *existing* Pickering ferrite-pearlite laws
  in :mod:`steel.grain` (:func:`steel.heat_state.cold_short_check`): it raises the yield strength *and* the
  ductile-brittle transition temperature (DBTT). When the DBTT climbs above the service temperature the steel
  is brittle in the hand — *cold-short*. The strengthening term is **pinned** (Thiele–Hošek +237 MPa/at% P,
  cross-checked against Total Materia) — the slice's teeth; the DBTT *slope* is flagged representative.
* **Sulfur → red-shortness (a NEW consumer).** S has no existing back-end consumer, so it closes through the
  **new** :mod:`steel.hot_work` verdict: free sulfur (that manganese did not tie up as MnS) forms a Fe–FeS
  grain-boundary film above the ~988 °C eutectic, so the steel tears when hot-worked. This slice carries **no
  strict tooth** — it is cited constants + by-construction, the same shape slag.py labels "by construction
  (NOT teeth)". Mushet's Mn:S ≥ 1.71 threshold (manganese makes sulfurous steel forgeable) is the
  historical-coherence *anchor* (1.71 = M_Mn/M_S, arithmetic — it cannot come out wrong); the cited eutectic
  is a di-crosschecked *input*; the temperature ordering is mechanism narrative.

The signed-impurity foil (the §5b pedagogy)
-------------------------------------------
Phosphorus is the clean inverse of grain refinement. Refinement is the *lone* lever that raises strength AND
improves toughness (lowers DBTT) — one variable, both benefits. Phosphorus raises strength AND *raises* DBTT:
it strengthens while it embrittles. The acid heat is the proof — **stronger** than the clean heat (P in solid
solution) yet **brittle**. That contrast is *why* refinement is special.

The workable window
-------------------
The off-spec heat is squeezed from both ends: brittle below its (high) DBTT at the cold/service end, red-short
above the 988 °C eutectic at the hot-working end. The clean heat is ductile far below room temperature and
sound to the forging heat — a wide-open window. (The DBTT is a *service / toughness* limit and red-shortness a
*hot-working* limit — two different ends of the temperature axis, not one cold-working scale.)

Run headless (prints the historical arc + both verdicts):

    python -m steel.demo_impurity_window
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import grain as g
from . import refining as rf
from . import slag as sg
from . import hot_work as hw
from .heat_state import COLD_SHORT, Heat, cold_short_check
from .hot_work import RED_SHORT, hot_work, red_short_assessment
from .slag import MN_PER_S
from .sweep import STEELS

# The high-phosphorus, sulfurous charge — Continental "minette"-class ore (the reason the basic/Thomas process
# and ladle desulfurization had to be invented; acid Bessemer could remove neither P nor S). Pig iron carries
# the impurities the blast furnace leaves in.
CHARGE_P = 0.35                     # phosphorus in the hot metal (high-P ore territory)
CHARGE_S = 0.05                     # sulfur in the hot metal (high-S coke)
CHARGE_CARBON = 4.0                 # carbon-saturated hot metal
TARGET_C = 0.12                     # a low-carbon structural steel (the ferritic, cold-short-prone regime)
BASE_SI = 0.15                      # silicon backbone (common to both heats)
MUSHET_MN = 0.80                    # manganese added (the basic + Mushet route): ties sulfur as MnS
NO_MN = 0.05                        # pre-Mushet acid Bessemer: essentially no manganese
ALUMINIUM_PCT = 0.04                # the aluminium kill (Slice 1 — the desulfurization precondition)

NORMALIZE_T = 900.0                 # austenitizing temperature for the normalize (→ ferrite-pearlite)
NORMALIZE_T_HOURS = 0.5
FORGE_TEMP_C = 1150.0               # the assumed hot-working temperature (above the 988 °C eutectic)
SERVICE_T = g.ROOM_TEMPERATURE_C    # the temperature the DBTT is read against (20 °C, brittle in the hand)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-impurity-window.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-impurity-window.png"


@dataclass(frozen=True)
class HeatConsequence:
    """One heat carried through to its impurity verdicts — the per-heat row of the comparison."""

    label: str
    heat: Heat               # post-refining (P/S set), before the consequence checks
    P: float
    Mn: float
    S: float
    dbtt_C: float            # normalized ferrite-pearlite DBTT (P-aware Pickering)
    yield_MPa: float         # the same structure's yield (the P-strengthening foil)
    free_S: float            # sulfur not tied as MnS (the red-short precursor)
    cold_short: bool         # DBTT above service temperature
    red_short: bool          # free S worked above the Fe–FeS eutectic
    after_checks: Heat       # the Heat after cold_short_check + hot_work (defects populated)


@dataclass(frozen=True)
class ImpurityDemo:
    """What the demo produced — the two heats' consequences and the four-panel figure arrays."""

    acid: HeatConsequence
    basic: HeatConsequence
    # Panel A — P → DBTT (and yield) sweep; both heats share the baseline, differing only in P
    P_grid: np.ndarray
    dbtt_vs_P: np.ndarray
    yield_vs_P: np.ndarray
    P_star: float            # the P where DBTT crosses the service temperature (cold-short onset)
    # Panel B — free sulfur vs Mn:S ratio at the charge sulfur (the Mushet threshold)
    ratio_grid: np.ndarray
    freeS_vs_ratio: np.ndarray
    # Panel C — the signed foil: arrows on the yield–DBTT plane from a shared baseline
    foil_baseline: tuple[float, float]    # (yield, DBTT) of a mid-P reference
    foil_P_arrow: tuple[float, float]     # Δ(yield, DBTT) from adding phosphorus
    foil_grain_arrow: tuple[float, float] # Δ(yield, DBTT) from refining the grain
    # Reference scalars (so the plots layer only draws — ADR 0002)
    service_T: float
    forge_temp_C: float
    eutectic_C: float
    mushet_ratio: float


def _refine_acid() -> Heat:
    """Heat A — 1856 acid Bessemer, no manganese: blow, then dephosphorize against an acid (lime-poor) slag."""
    backbone = replace(STEELS["1045"], C=CHARGE_CARBON, Mn=NO_MN, Si=BASE_SI,
                       P=CHARGE_P, S=CHARGE_S, name="acid Bessemer")
    charge = rf.from_hot_metal(backbone, charge_carbon=CHARGE_CARBON)
    blown = rf.decarburize(charge, TARGET_C)                    # blow to grade carbon (P/S inert here)
    return sg.dephosphorize(blown, sg.ACID_BESSEMER_SLAG)       # acid slag can't fix P → retained, S untouched


def _refine_basic() -> Heat:
    """Heat B — basic converter + Mushet manganese + ladle desulfurization: the route that makes sound steel."""
    backbone = replace(STEELS["1045"], C=CHARGE_CARBON, Mn=MUSHET_MN, Si=BASE_SI,
                       P=CHARGE_P, S=CHARGE_S, name="basic + Mushet")
    charge = rf.from_hot_metal(backbone, charge_carbon=CHARGE_CARBON)
    blown = rf.decarburize(charge, TARGET_C)
    dephos = sg.dephosphorize(blown, sg.BASIC_CONVERTER_SLAG)   # basic slag pulls P down two orders of magnitude
    killed = rf.deoxidize(dephos, "Al", ALUMINIUM_PCT)          # kill (the desulfurization precondition)
    return sg.desulfurize(killed, sg.LADLE_DESULF_SLAG)         # reducing ladle strips the sulfur


def _consequence(label: str, heat: Heat) -> HeatConsequence:
    """Carry one refined heat through both consequence checks and record the verdicts."""
    gp = g.coupled_grain_properties(
        NORMALIZE_T, NORMALIZE_T_HOURS, heat.composition.C,
        comp=heat.composition.minor(), P_pct=heat.composition.P,
    )
    a = red_short_assessment(heat.composition.Mn, heat.composition.S, FORGE_TEMP_C)
    after = hot_work(cold_short_check(heat, service_T=SERVICE_T), FORGE_TEMP_C)
    return HeatConsequence(
        label=label, heat=heat, P=heat.composition.P, Mn=heat.composition.Mn, S=heat.composition.S,
        dbtt_C=gp.dbtt_C, yield_MPa=gp.yield_MPa, free_S=a.free_sulfur_pct,
        cold_short=after.has_defect(COLD_SHORT), red_short=after.has_defect(RED_SHORT), after_checks=after,
    )


def compute() -> ImpurityDemo:
    """Refine both heats through the real chain, read both consequences, and assemble the figure arrays."""
    acid = _consequence("acid Bessemer, no Mn", _refine_acid())
    basic = _consequence("basic + Mushet + desulf", _refine_basic())

    # Panel A — the DBTT (and yield) vs phosphorus curve. Both heats share the normalize condition and Si/C/N,
    # so their DBTT differs ONLY in P: they lie on one curve. (Mn shifts yield, not DBTT, so the yield curve is
    # drawn at a representative Mn; the two heats' yields are reported in the summary.)
    base_minor = {"Mn": 0.5, "Si": BASE_SI}
    P_grid = np.linspace(0.0, 0.45, 240)
    dbtt_vs_P = np.array([
        g.coupled_grain_properties(NORMALIZE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=float(p)).dbtt_C
        for p in P_grid
    ])
    yield_vs_P = np.array([
        g.coupled_grain_properties(NORMALIZE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=float(p)).yield_MPa
        for p in P_grid
    ])
    # P* where the DBTT crosses the service temperature (linear in P, so solve from the slope directly)
    dbtt0 = g.coupled_grain_properties(NORMALIZE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=0.0).dbtt_C
    P_star = (SERVICE_T - dbtt0) / g.ITT_K_P

    # Panel B — free sulfur vs Mn:S ratio at the charge sulfur. Free S vanishes at the stoichiometric 1.71
    # (Mushet's threshold — the historical-coherence anchor, by construction), via free_S = S·(1 − ratio/1.71)₊.
    ratio_grid = np.linspace(0.0, 4.0, 240)
    freeS_vs_ratio = np.array([
        red_short_assessment(float(r) * CHARGE_S, CHARGE_S, FORGE_TEMP_C).free_sulfur_pct for r in ratio_grid
    ])

    # Panel C — the signed foil. From a coarse-grained, mid-phosphorus baseline (an over-austenitized
    # heat), one arrow adds phosphorus (yield ↑, DBTT ↑: strengthens AND embrittles) and one refines the
    # grain back to the normalize (yield ↑, DBTT ↓: the lone co-improver). The coarse baseline makes the
    # refinement lever visible — grain growth is slow below ~1000 °C, so a small austenitizing change moves
    # little; the contrast is over-austenitized vs normalized.
    P_ref = 0.15
    COARSE_T = 1150.0
    base = g.coupled_grain_properties(COARSE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=P_ref)
    add_P = g.coupled_grain_properties(COARSE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=P_ref + 0.15)
    finer = g.coupled_grain_properties(NORMALIZE_T, NORMALIZE_T_HOURS, TARGET_C, comp=base_minor, P_pct=P_ref)
    foil_baseline = (base.yield_MPa, base.dbtt_C)
    foil_P_arrow = (add_P.yield_MPa - base.yield_MPa, add_P.dbtt_C - base.dbtt_C)
    foil_grain_arrow = (finer.yield_MPa - base.yield_MPa, finer.dbtt_C - base.dbtt_C)

    return ImpurityDemo(
        acid=acid, basic=basic,
        P_grid=P_grid, dbtt_vs_P=dbtt_vs_P, yield_vs_P=yield_vs_P, P_star=P_star,
        ratio_grid=ratio_grid, freeS_vs_ratio=freeS_vs_ratio,
        foil_baseline=foil_baseline, foil_P_arrow=foil_P_arrow, foil_grain_arrow=foil_grain_arrow,
        service_T=SERVICE_T, forge_temp_C=FORGE_TEMP_C,
        eutectic_C=hw.FE_FES_EUTECTIC_C, mushet_ratio=MN_PER_S,
    )


def print_summary(demo: ImpurityDemo) -> None:
    """Print the historical arc, the two consequence verdicts, and the signed-impurity foil."""
    print(f"\nClosing the impurity consequences — the same {CHARGE_P:.2f} %P / {CHARGE_S:.2f} %S pig iron, "
          f"two processes\n")

    for c in (demo.acid, demo.basic):
        flags = ", ".join(c.after_checks.defects) if c.after_checks.defects else "clean — workable"
        print(f"  {c.label}:")
        print(f"      P {c.P:.3f} %, Mn {c.Mn:.2f} %, S {c.S:.3f} % (free S {c.free_S:.3f} %)")
        print(f"      normalized DBTT {c.dbtt_C:+.0f} °C vs {SERVICE_T:+.0f} °C service "
              f"→ {'COLD-SHORT (brittle)' if c.cold_short else 'ductile'};  "
              f"forge {FORGE_TEMP_C:.0f} °C → {'RED-SHORT (cracks)' if c.red_short else 'sound'}")
        print(f"      yield {c.yield_MPa:.0f} MPa   ⇒ {flags}")

    print(f"\n  The signed-impurity foil — the acid heat is STRONGER yet BRITTLE:")
    print(f"      yield {demo.acid.yield_MPa:.0f} MPa (acid, +P) vs {demo.basic.yield_MPa:.0f} MPa (clean) "
          f"— phosphorus strengthens (+{demo.acid.yield_MPa - demo.basic.yield_MPa:.0f} MPa) while it embrittles.")
    print(f"      Phosphorus raises yield AND DBTT; grain refinement raises yield but LOWERS DBTT — the lone "
          f"co-improver (§5b).")

    print(f"\n  Where the consequences close (the two classes):")
    print(f"      P → cold-short: a PROPAGATION through the existing Pickering DBTT law (DBTT crosses "
          f"{SERVICE_T:.0f} °C at P ≈ {demo.P_star:.3f} %).")
    print(f"      S → red-short: a NEW hot-work consumer (no strict tooth — cited constants + "
          f"by-construction); free sulfur vanishes at Mushet's Mn:S = {MN_PER_S:.2f} (historical anchor).")
    print(f"      Both still INERT in heat_treat (hardenability / hardness / martensite read C/Si/Mn/Ni/Cr/Mo "
          f"only) — P/S now propagate on exactly one path each.")


def save_figure(demo: ImpurityDemo) -> Path:
    """Render and bank the impurity-window artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import impurity_window_figure

    fig = impurity_window_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ⇒ on legacy codepages

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
