"""Tempered-martensite embrittlement: the OTHER tempering trough — carbon-driven, microstructural, irreversible.

*The second embrittlement on the tempering axis, and the foil to its reversible sibling.*
:func:`steel.temper_embrittlement.temper_embrittlement_check` closed the **reversible** one — phosphorus
segregating to grain boundaries on slow cooling through 375–575 °C, cleared by a reheat. This closes the
**irreversible** one (``steel-production.md`` §11's back-end ``toughness_index`` ceiling, now addressed as a
front-end consumer): tempering as-quenched martensite in **260–370 °C** precipitates **cementite films** along
the interlath / prior-austenite boundaries (fed by interlath retained-austenite decomposition), and toughness
drops into a trough. Temper above ~400 °C and it recovers — but the film **cannot be restored** by dropping back
into the band. One-way.

What it shows (four panels)
---------------------------
1. **The trough on the temper axis.** For a hardened **4140** (medium-carbon Cr-Mo, the classic victim), the
   verdict across temper temperature: tough below 260 °C, **embrittled 260–370 °C**, tough again above. The
   *reversible*-TE window (375–575 °C) is marked alongside for orientation — a different trough, a different
   mechanism.
2. **The two gates (carbon + hardenability).** At a 300 °C temper: 4140 and 1080 embrittle; **8620 (0.20 %C)
   stays tough even fully hardened** — too little carbon for the cementite films; and a plain-carbon section
   that *did not harden* (1045, mild quench → 21 % martensite) is immune — no tempered martensite to embrittle.
   The verdict composes with the same frozen quench the spine uses.
3. **Irreversibility (the headline).** Temper 300 °C → embrittled; temper 450 °C → recovered; **temper 300 °C
   again → stays tough.** The carbide morphology is set by the *peak* temper — one-way.
4. **Reversible ↔ irreversible.** The direct foil: reversible TE *re-embrittles* when you cycle it; TME does
   not. Same axis, opposite character.

The honest posture (no strict tooth — the gate was run and failed)
------------------------------------------------------------------
Like the reversible-TE and sulfur / red-short slices, this is **cited constants + a by-construction verdict**.
The tempting tooth — "the 260–370 °C trough *emerges* from ε→cementite + interlath-RA-film kinetics without
tuning" — was gated on paper: the repo carries no stage-III carbide thermodynamics, so the trough onset is
underdetermined here (just as the reversible-TE segregation nose was), and we did not build a carbide model *to*
land it. The trough window, the ~400 °C recovery, and the cementite-film mechanism are **cited inputs**; the
carbon gate and the verdict rule are **by construction**. The faithful part is architecture, not a tooth: the
check runs the **same frozen back-end quench** and gates on its martensite fraction, so hardenability composes
in. Retained austenite is the cited *mechanism* (interlath-film source) but **not** the severity driver — bulk
RA would rank high-carbon *plate*-martensite steels worst, where the mechanism does not apply (the inverted
trap); carbon drives the gate, and 8620 confirms the low-carbon exemption.

Run headless (prints the trough map, the two gates, and the irreversibility cycle):

    python -m steel.demo_tempered_martensite_embrittlement
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import tempered_martensite_embrittlement as tme
from .sweep import STEELS, Steel, evaluate

# The classic victim: 4140, a medium-carbon Cr-Mo quench-and-temper steel (4340 / 300M are the textbook icons).
VICTIM = STEELS["4140"]
HERO_MEDIUM, HERO_DIAMETER = "oil", 0.010      # 4140 deep-hardens here → ~96 % martensite (a hardened part)
TROUGH_TEMPER = 300.0                          # squarely in the 260–370 °C trough — the failure
RECOVERY_TEMPER = 450.0                        # above the ~400 °C recovery — over-temper (and stay) to be tough
REVERSIBLE_WINDOW_C = (375.0, 575.0)           # the SIBLING trough (reversible TE) — marked for orientation only

# Panel-2 discriminator: (label, steel, quench medium, diameter) — the two gates, each on a real quench.
# Kept to the lath-martensite (≤ ~0.5 %C) grades the interlath-film mechanism describes: 4140 is the embrittled
# hero, 8620 the carbon-gate miss, 1045-mild the martensitic-gate miss. High-carbon *plate*-martensite (1080)
# also embrittles in the trough but by a related cementite-on-twin-boundary path — deliberately not shown, so
# the panel does not attribute the interlath-film mechanism to a structure it does not describe.
DISCRIMINATOR_CASES: tuple[tuple[str, Steel, str, float], ...] = (
    ("4140 hardened\n(0.40 %C)", STEELS["4140"], "oil", 0.010),
    ("8620 hardened\n(0.20 %C — low C)", STEELS["8620"], "water", 0.005),
    ("1045 mild quench\n(un-hardened)", STEELS["1045"], "oil", 0.010),
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-tempered-martensite-embrittlement.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-tempered-martensite-embrittlement.png"


@dataclass(frozen=True)
class TMEDemo:
    """What the demo produced — the trough map, the two gates, the irreversibility cycle, the foil."""

    # Panel 1 — the verdict across temper temperature for the hardened victim
    axis_map: list[tuple[float, bool]]          # (temper °C, embrittled?)
    window: tuple[float, float]                 # the TME trough 260–370
    recovery_T: float                           # the ~400 °C recovery / irreversibility boundary
    reversible_window: tuple[float, float]      # the sibling reversible-TE trough (orientation)
    victim_name: str
    victim_C: float
    victim_martensite: float
    # Panel 2 — the two gates (carbon + hardenability)
    discriminator: list[tuple[str, float, float, bool]]   # (label, C, martensite_fraction, embrittled?)
    # Panel 3 — the irreversibility cycle
    cycle: list[tuple[str, bool]]               # (state label, embrittled?)
    # Panel 4 — the reversible ↔ irreversible foil
    contrast: list[tuple[str, str, str]]        # (aspect, reversible TE, tempered-martensite)


def compute() -> TMEDemo:
    """Quench the victim once, sweep the temper axis, run the two gates, and trace the irreversibility cycle."""
    # The hardened victim — one quench gives the martensite fraction TME acts on (composes with hardenability).
    vq = evaluate(VICTIM, medium=HERO_MEDIUM, diameter=HERO_DIAMETER, austenitize_T=850.0, bath_T=25.0)
    fM = vq.result.martensite

    # Panel 1 — verdict vs peak temper for the hardened victim (the trough on the axis).
    temps = [150.0 + 10.0 * i for i in range(0, 51)]      # 150 → 650 °C
    axis_map = [
        (T, tme.tempered_martensite_embrittlement_assessment(VICTIM, fM, peak_temper_C=T).embrittled)
        for T in temps
    ]

    # Panel 2 — the two gates: each case quenched for real, then tempered at 300 °C.
    discriminator: list[tuple[str, float, float, bool]] = []
    for label, steel, medium, d in DISCRIMINATOR_CASES:
        o = evaluate(steel, medium=medium, diameter=d, austenitize_T=850.0, bath_T=25.0)
        a = tme.tempered_martensite_embrittlement_assessment(steel, o.result.martensite, peak_temper_C=TROUGH_TEMPER)
        discriminator.append((label, steel.C, o.result.martensite, a.embrittled))

    # Panel 3 — irreversibility: temper in trough → over-temper → re-enter trough, threading the PEAK.
    def emb(peak: float) -> bool:
        return tme.tempered_martensite_embrittlement_assessment(VICTIM, fM, peak_temper_C=peak).embrittled

    cycle = [
        (f"temper {TROUGH_TEMPER:.0f} °C", emb(TROUGH_TEMPER)),
        (f"temper {RECOVERY_TEMPER:.0f} °C\n(over the trough)", emb(RECOVERY_TEMPER)),
        (f"re-enter {TROUGH_TEMPER:.0f} °C\n(peak still {RECOVERY_TEMPER:.0f})", emb(max(RECOVERY_TEMPER, TROUGH_TEMPER))),
    ]

    # Panel 4 — the reversible ↔ irreversible foil (cited mechanism contrast, not computed numbers).
    contrast = [
        ("trough", "375–575 °C", "260–370 °C"),
        ("driver", "phosphorus (Ni/Cr)", "carbon (cementite films)"),
        ("mechanism", "GB segregation", "interlath cementite films"),
        ("clean heat?", "escapes (needs P)", "still embrittles"),
        ("reversible?", "YES — cycles back", "NO — one-way"),
        ("cure", "Mo / fast cool", "temper above the trough"),
    ]

    return TMEDemo(
        axis_map=axis_map, window=tme.TME_WINDOW_C, recovery_T=tme.TME_RECOVERY_C,
        reversible_window=REVERSIBLE_WINDOW_C,
        victim_name=VICTIM.name, victim_C=VICTIM.C, victim_martensite=fM,
        discriminator=discriminator, cycle=cycle, contrast=contrast,
    )


def print_summary(demo: TMEDemo) -> None:
    """Print the trough map, the two gates, and the irreversibility cycle."""
    print("\nTempered-martensite embrittlement — the irreversible, carbon-driven tempering trough\n")

    lo, hi = demo.window
    embrittled_temps = [T for T, e in demo.axis_map if e]
    print(f"Hardened {demo.victim_name} ({demo.victim_C:.2f} %C, {demo.victim_martensite:.0%} martensite) — "
          f"verdict across temper temperature:")
    print(f"    embrittled for tempers in {min(embrittled_temps):.0f}–{max(embrittled_temps):.0f} °C "
          f"(the {lo:.0f}–{hi:.0f} °C trough); tough below, tough (recovered) above {demo.recovery_T:.0f} °C")

    print("\nThe two gates (at a 300 °C temper) — carbon AND a hardened martensitic structure:")
    for label, C, M, e in demo.discriminator:
        one = label.replace(chr(10), " ")
        print(f"    {one:<34} C = {C:.2f} %, {M:>4.0%} martensite  → {'EMBRITTLED' if e else 'tough'}")

    print("\nIrreversibility — the carbide morphology is set by the PEAK temper (one-way):")
    for label, e in demo.cycle:
        print(f"    {label.replace(chr(10),' '):<40} → {'EMBRITTLED' if e else 'tough'}")

    print("\n→ The trough window, the ~400 °C recovery, and the cementite-film mechanism are cited; the carbon "
          "gate\n  and verdict rule are by-construction — no strict tooth (the carbide-kinetics trough gate was "
          "run and failed).\n  This closes the OTHER tempering-axis embrittlement; temper_embrittlement_check "
          "closed the reversible one.")


def save_figure(demo: TMEDemo) -> Path:
    """Render and bank the tempered-martensite-embrittlement artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import tempered_martensite_embrittlement_figure

    fig = tempered_martensite_embrittlement_figure(demo)
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
