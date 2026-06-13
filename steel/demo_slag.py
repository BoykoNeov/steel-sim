"""The F2 Slice-2 anchor demo: refine the tramps — phosphorus out in the converter, sulfur in the ladle.

*The two impurities the blast furnace leaves in, partitioned into slag — and the history that hinges on
them.* This is the demonstrable artifact for **F2 Slice 2** (``docs/plans/steel-making.md`` §7, the
"partition" of decarb/deox/**partition**/degas). Slice 1 set carbon and killed and degassed the heat; this
removes phosphorus and sulfur, and in doing so reproduces the most teachable stretch of steelmaking history:
the §14 purity-control ramp from acid Bessemer (couldn't remove P) through Thomas' basic lining (could) to
ladle desulfurization.

What it shows
-------------
1. **The route that works (blow → basic converter → kill → ladle).** Charge phosphorus- and sulfur-bearing
   hot metal, **blow** it to the grade's carbon (Slice 1 — oxygen rises to turndown), **dephosphorize**
   against a basic, oxidizing converter slag *there* (P drops two orders of magnitude — dephosphorization
   completes at low carbon, where the FeO-rich slag is consistent with the bath), **kill** it (Slice 1 —
   oxygen down), then **desulfurize** against a reducing ladle slag — which works *because* the heat is now
   deoxidized. Each step returns a new ``Heat`` with the impurity field lowered and one more entry on the
   trail.

2. **The opposite oxygen dependence — the headline tooth.** Dephosphorization is an oxidation: it needs the
   oxidizing converter (Healy's ``L_P`` carries a **+2.5·log %Fe_t** term). Desulfurization is a reduction:
   it needs the reducing ladle (the sulfide-capacity ``L_S`` carries a **−log a_O** term). Those two signs
   come from two independently sourced correlations, so their being opposite is *computed*, not tuned — and
   it is why the process order is what it is. The demo proves the coupling by reading the Heat's dissolved
   oxygen: the *same* ladle slag barely desulfurizes the heat **before** the kill (high oxygen) and strips it
   **after** (low oxygen).

3. **The two history-grounded failures (consequence deferred, honestly).** *Acid Bessemer:* the same charge
   dephosphorized against an acid (siliceous, lime-poor) slag keeps almost all its phosphorus — ``L_P ≈ 1`` —
   the **high-phosphorus** flag fires (cold-short rails). *Desulfurize too early:* skip the kill and the
   sulfur barely moves — **high-sulfur** flag (red-short). And **Mn:S → MnS**: with enough manganese the
   residual sulfur reports as benign MnS, not embrittling FeS — Mushet's fix that made Bessemer steel sound.

The honest posture (this is **not** Slice 1's validated propagation): phosphorus and sulfur have **no
validated back-end consumer** — the hardenability/hardness models read C/Si/Mn/Ni/Cr/Mo only — so this is
benchmarked **physics** (the F1-Ellingham / F4-casting class), not a spine-class propagation. The off-spec
heat would heat-treat *identically* to a clean one (the back end is P/S-blind); the embrittlement / hot-tear
consequence is deferred (``steel-making.md`` §6/§14). F2 Slice 2 sets the impurity state; it does not yet
close it. The teeth are the opposite-oxygen sign contrast, the order of magnitude vs measured plant ``L``,
and the acid/basic endpoint — never the last digit (the absolute constants are the source-sensitive tier).

Run headless (prints the tap chemistry + the history failures):

    python -m steel.demo_slag
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import refining as rf
from . import slag as sg
from .heat_state import Heat
from .sweep import STEELS

# The hero grade backbone (continuity with the spine / refining / ladle / casting demos), seeded with
# blast-furnace impurity levels (pig iron carries ~0.08 % P, ~0.045 % S — the furnace removes neither).
GRADE = "4140"
CHARGE_P = 0.10                     # phosphorus in the hot-metal charge (high-P bog/phosphoric ore territory)
CHARGE_S = 0.06                     # sulfur in the hot-metal charge (high-S coke, pre-desulfurization)
CHARGE_CARBON = 4.5                 # carbon-saturated hot metal
TARGET_C = 0.40                     # the grade's carbon (Slice 1 blow)
ALUMINIUM_PCT = 0.04                # the aluminium kill (Slice 1)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-slag.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-slag.png"


@dataclass(frozen=True)
class SlagDemo:
    """What the demo produced — the refined heats, the history failures, and the figure arrays.

    ``clean`` the heat through the working route (basic dephos → kill → ladle desulf); ``acid`` the
    acid-Bessemer counterfactual (phosphorus retained); ``early_desulf`` the desulfurize-before-kill
    counterfactual (sulfur retained). ``mns`` / ``mns_bad`` the Mn:S → MnS balance for the clean heat and a
    low-Mn high-S foil. The arrays draw the four panels: ``B_grid`` + ``Lp_vs_B`` the L_P–basicity curve with
    the acid / basic points; ``o_grid`` + ``Ls_vs_o`` the L_S–oxygen curve with the converter / ladle points;
    ``contrast_o`` + (``Lp_contrast``, ``Ls_contrast``) the shared-oxygen-axis opposite-dependence overlay;
    ``steps`` + (``p_trail``, ``s_trail``) the residual P/S through the working route, with the two
    counterfactual end-points (``acid_p``, ``early_s``).
    """

    clean: Heat
    acid: Heat
    early_desulf: Heat
    mns: sg.SulfideBalance
    mns_bad: sg.SulfideBalance
    # L_P vs basicity (panel A)
    B_grid: np.ndarray
    Lp_vs_B: np.ndarray
    acid_point: tuple[float, float]
    basic_point: tuple[float, float]
    bof_band: tuple[float, float]
    # L_S vs metal oxygen (panel B)
    o_grid: np.ndarray
    Ls_vs_o: np.ndarray
    converter_o_point: tuple[float, float]
    ladle_o_point: tuple[float, float]
    # opposite-oxygen contrast (panel C)
    contrast_o: np.ndarray
    Lp_contrast: np.ndarray
    Ls_contrast: np.ndarray
    # residual trail (panel D)
    steps: list[str]
    p_trail: list[float]
    s_trail: list[float]
    acid_p: float
    early_s: float


def _charge() -> Heat:
    """The hot-metal charge carrying the grade's alloy backbone plus blast-furnace P and S."""
    backbone = replace(STEELS[GRADE], P=CHARGE_P, S=CHARGE_S)
    return rf.from_hot_metal(backbone, charge_carbon=CHARGE_CARBON)


def _working_route(charge: Heat) -> tuple[Heat, list[str], list[float], list[float]]:
    """The route that works — blow → basic dephos (at turndown) → kill → ladle desulf. Heat + residual trail.

    The order is the textbook converter sequence, and it matters *physically*: dephosphorization completes at
    **low carbon / turndown**, where the FeO-rich oxidizing slag is consistent with the bath (a
    carbon-saturated melt would reduce that FeO — the carbon boil). So the blow comes first; it sets the high
    oxygen the basic slag pairs with and does not touch P/S. (Healy's L_P is carbon-independent, so the
    *number* would be the same in any order — but the slag/metal-oxygen states are only mutually consistent
    this way.)
    """
    steps = ["charge"]
    p_trail = [charge.composition.P]
    s_trail = [charge.composition.S]

    blown = rf.decarburize(charge, TARGET_C)                    # blow to grade carbon (oxygen rises, P/S inert)
    steps.append("blow"); p_trail.append(blown.composition.P); s_trail.append(blown.composition.S)

    dephos = sg.dephosphorize(blown, sg.BASIC_CONVERTER_SLAG)   # dephosphorize at the oxidizing turndown
    steps.append("dephos\n(basic)"); p_trail.append(dephos.composition.P); s_trail.append(dephos.composition.S)

    killed = rf.deoxidize(dephos, "Al", ALUMINIUM_PCT)          # kill (oxygen drops — the desulf precondition)
    steps.append("kill"); p_trail.append(killed.composition.P); s_trail.append(killed.composition.S)

    desulf = sg.desulfurize(killed, sg.LADLE_DESULF_SLAG)       # desulfurize in the reducing ladle (reads O)
    steps.append("desulf\n(ladle)"); p_trail.append(desulf.composition.P); s_trail.append(desulf.composition.S)
    return desulf, steps, p_trail, s_trail


def compute() -> SlagDemo:
    """Run the working route + the two history failures, then assemble the four-panel arrays."""
    charge = _charge()
    clean, steps, p_trail, s_trail = _working_route(charge)

    # Counterfactual 1 — acid Bessemer: dephosphorize the same turndown heat against a lime-poor acid slag
    # (phosphorus stays — Healy is carbon-independent, so it is the slag, not the carbon, that decides).
    blown = rf.decarburize(charge, TARGET_C)
    acid = sg.dephosphorize(blown, sg.ACID_BESSEMER_SLAG)

    # Counterfactual 2 — desulfurize before the kill: the ladle slag on the dephosphorized-but-still-oxidized
    # heat (the blow oxygen), which barely works (the deox-first lesson).
    pre_kill = sg.dephosphorize(blown, sg.BASIC_CONVERTER_SLAG)
    early_desulf = sg.desulfurize(pre_kill, sg.LADLE_DESULF_SLAG)

    # Mn:S → MnS on the clean heat (plenty of Mn), and a low-Mn high-S foil (free FeS → red-short).
    mns = sg.manganese_sulfide(clean.composition.Mn, clean.composition.S)
    mns_bad = sg.manganese_sulfide(0.30, 0.30)

    # Panel A — L_P vs basicity: sweep CaO on the basic converter base (FeO/SiO2/MgO/MnO fixed).
    base = sg.BASIC_CONVERTER_SLAG
    cao_grid = np.linspace(2.0, 55.0, 240)
    B_grid = cao_grid / base.SiO2
    Lp_vs_B = np.array([sg.phosphorus_partition(replace(base, CaO=float(c))) for c in cao_grid])
    acid_point = (sg.ACID_BESSEMER_SLAG.basicity, sg.phosphorus_partition(sg.ACID_BESSEMER_SLAG))
    basic_point = (base.basicity, sg.phosphorus_partition(base))
    bof_band = (50.0, 200.0)                                     # measured BOF L_P range (the benchmark)

    # Panel B — L_S vs metal dissolved oxygen (ladle slag fixed).
    o_grid = np.logspace(0.0, 2.9, 220)                         # 1 → ~800 ppm O
    Ls_vs_o = np.array([sg.sulfur_partition(sg.LADLE_DESULF_SLAG, float(o)) for o in o_grid])
    O_killed = clean.oxygen_ppm                                 # the deoxidized ladle oxygen (Slice 1)
    O_blown = blown.oxygen_ppm                                  # the un-killed converter oxygen
    ladle_o_point = (O_killed, sg.sulfur_partition(sg.LADLE_DESULF_SLAG, O_killed))
    converter_o_point = (O_blown, sg.sulfur_partition(sg.LADLE_DESULF_SLAG, O_blown))

    # Panel C — the opposite oxygen dependence on a shared metal-oxygen axis. L_P from sweeping the basic
    # slag's FeO (→ metal O via the Fe–FeO link), L_S from sweeping the metal oxygen on the ladle slag.
    feo_grid = np.linspace(2.0, 45.0, 220)
    basic_slags = [replace(base, FeO=float(f)) for f in feo_grid]
    contrast_o = np.array([sg.metal_oxygen_for_feo(s) for s in basic_slags])
    Lp_contrast = np.array([sg.phosphorus_partition(s) for s in basic_slags])
    Ls_contrast = np.array([sg.sulfur_partition(sg.LADLE_DESULF_SLAG, float(o)) for o in contrast_o])

    return SlagDemo(
        clean=clean, acid=acid, early_desulf=early_desulf, mns=mns, mns_bad=mns_bad,
        B_grid=B_grid, Lp_vs_B=Lp_vs_B, acid_point=acid_point, basic_point=basic_point, bof_band=bof_band,
        o_grid=o_grid, Ls_vs_o=Ls_vs_o, converter_o_point=converter_o_point, ladle_o_point=ladle_o_point,
        contrast_o=contrast_o, Lp_contrast=Lp_contrast, Ls_contrast=Ls_contrast,
        steps=steps, p_trail=p_trail, s_trail=s_trail,
        acid_p=acid.composition.P, early_s=early_desulf.composition.S,
    )


def print_summary(demo: SlagDemo) -> None:
    """Print the working route's trail, the opposite-oxygen coupling, and the two history failures."""
    print(f"\nF2 Slice 2 — refine the tramps in a {GRADE} heat: P out in the converter, S in the ladle\n")

    print("The route that works (blow → basic dephos at turndown → kill → ladle desulf), step by step:")
    for step in demo.clean.history:
        if step.name in ("decarburize", "deoxidize"):
            tag = "  (Slice 1)"
        else:
            tag = ""
        print(f"    • {step.name:<14} {step.summary}{tag}")
    print(f"    ⇒ clean heat: P {demo.clean.composition.P:.3f} %, S {demo.clean.composition.S:.3f} % "
          f"— both on spec ({'clean' if demo.clean.is_clean else demo.clean.defects})")

    print(f"\nThe opposite oxygen dependence (the headline) — dephos oxidizes, desulf reduces:")
    print(f"    dephosphorization wants the OXIDIZING converter (Healy L_P ∝ +%Fe_t): basic slag L_P "
          f"{demo.basic_point[1]:.0f}")
    print(f"    desulfurization wants the REDUCING ladle (L_S ∝ −a_O): same ladle slag gives")
    print(f"        L_S {demo.converter_o_point[1]:.0f} at the un-killed blow ({demo.converter_o_point[0]:.0f} "
          f"ppm O) → barely desulfurizes")
    print(f"        L_S {demo.ladle_o_point[1]:.0f} after the kill ({demo.ladle_o_point[0]:.0f} ppm O) → strips "
          f"the sulfur  ⇒ deoxidize FIRST")

    print(f"\nThe history failures (consequence deferred — P/S are inert in the back end):")
    print(f"    acid Bessemer (L_P {demo.acid_point[1]:.1f}): P {CHARGE_P:.3f} → {demo.acid_p:.3f} % "
          f"{'← HIGH P (cold-short rails)' if demo.acid.has_defect(sg.HIGH_PHOSPHORUS) else ''}")
    print(f"    desulfurize before the kill: S {CHARGE_S:.3f} → {demo.early_s:.3f} % "
          f"{'← HIGH S (red-short)' if demo.early_desulf.has_defect(sg.HIGH_SULFUR) else ''}")
    print(f"    Mn:S → MnS on the clean heat: ratio {demo.mns.ratio:.0f} ≥ 1.71 → "
          f"{'sulfur tied as benign MnS' if demo.mns.forms_mns else 'FeS risk'} "
          f"({demo.mns.mns_pct:.3f} % MnS); a low-Mn foil (Mn:S {demo.mns_bad.ratio:.1f}) leaves "
          f"{demo.mns_bad.free_sulfur_pct:.3f} % free S → red-short.")
    print(f"\n→ The chemistry is benchmarked (L_P ~ measured BOF 50–200; L_S ~ ladle 10²–10³; acid L_P ≈ 1); "
          f"the\n  embrittlement / hot-tear *consequence* is deferred — no validated back-end model reads "
          f"P or S yet.")


def save_figure(demo: SlagDemo) -> Path:
    """Render and bank the slag-partition artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import slag_figure

    fig = slag_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ₂, ≫, ∝ on legacy codepages

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
