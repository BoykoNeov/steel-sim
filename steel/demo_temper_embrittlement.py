"""Temper embrittlement: the Ni-Cr forging that cracked, and the four ways to stop it.

*The reversible, alloy-driven phosphorus embrittlement of quench-and-tempered steel — and why molybdenum,
a fast cool, a clean heat, or a reheat each defeat it.* The demonstrable artifact for the **martensitic-P**
consequence (``docs/plans/steel-making.md`` §14): the consumer that closes the *second* half of phosphorus'
story. :func:`steel.heat_state.cold_short_check` closed the ferritic/normalized path (DBTT); this closes the
quench-and-tempered path, where phosphorus segregates to prior-austenite grain boundaries on slow cooling
through ~375–575 °C and turns the fracture intergranular.

What it shows (the four levers, on one susceptible heat)
-------------------------------------------------------
A dirty **3.3 %Ni–1.6 %Cr** steel with residual phosphorus and **no molybdenum** — the classic temper-
embrittlement victim (a turbine rotor / pressure-vessel forging) — slow-cooled through the danger window
**embrittles**. The same heat is saved by any one of:

1. **A fast cool** through the window (the part never dwells where phosphorus segregates).
2. **Molybdenum** (≈0.5 %) — it scavenges phosphorus; the classic cure (and why Ni–Cr forging steels get a
   molybdenum addition).
3. **A clean heat** (low phosphorus → low J-factor → not susceptible at all).
4. **A reheat above 600 °C + fast cool** — the *reversibility* that names the phenomenon: the segregation
   disperses and the steel is tough again (until it is slow-cooled once more).

The honest posture (no strict tooth — the gate was run and failed)
------------------------------------------------------------------
Like the sulfur / red-short slice, this is **cited constants + a by-construction verdict**, not a tooth.
The tempting tooth — "the embrittlement C-curve nose emerges at the observed ~490–550 °C from cited
segregation thermodynamics + diffusion kinetics, without tuning" — was *tested on paper before coding and
could not be pinned*: a tractable Langmuir–McLean model fed the cited ΔG_seg(P) and D_P(α-Fe) runs ~100×
faster than the source's own kinetic anchor (450 °C → ~10 h) and gives no time-stable nose. Correcting for
the missing slowness (the omitted Fe₃P-cluster step) pushes the peak *up* from ~410 °C toward the observed
window — the model is **underdetermined, not wrong-placed** — and pinning it faithfully is out of scope. So
**no claimable tooth**, and we did not build the segregation model *to* land the nose. The **J-factor**
susceptibility index ``(Mn+Si)(P+Sn)·10⁴`` (Watanabe) is a regression-fit ranking (by-construction); the
danger window, the ≥600 °C reversibility, and the ≈0.5 % Mo cure are cited mechanism inputs. In the registry
only the dirty Ni–Cr victim (J ≈ 225) is susceptible; 4140/8620 are safe by **low J** (≈ 126–138 < 150), not
by their sub-threshold Mo — a coherence note, not a benchmark.

Run headless (prints the susceptibility ranking + the four levers + the reversibility cycle):

    python -m steel.demo_temper_embrittlement
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from . import temper_embrittlement as te
from .heat_state import Heat
from .sweep import STEELS, Steel

# The classic victim: a dirty Ni-Cr forging steel (turbine-rotor / pressure-vessel class) with residual
# phosphorus and NO molybdenum. Nickel + chromium promote the segregation; manganese + silicon co-segregate.
VICTIM = Steel(C=0.40, Mn=0.60, Si=0.30, Ni=3.30, Cr=1.60, Mo=0.0, P=0.025, name="3.3Ni–1.6Cr (dirty, no Mo)")
CURED = replace(VICTIM, Mo=0.55, name="3.3Ni–1.6Cr + 0.5Mo")
CLEAN = replace(VICTIM, P=0.005, name="3.3Ni–1.6Cr (clean P)")
RESIDUAL_P = 0.012                      # a typical residual phosphorus for the registry grades
REGISTRY = ("1045", "1080", "8620", "4140")

TEMPER_T = 620.0                        # a high temper ABOVE the window — embrittlement is set by the cool
REHEAT_T = 650.0                        # above the ~600 °C de-embrittlement threshold (the reset reheat)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-temper-embrittlement.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-temper-embrittlement.png"


@dataclass(frozen=True)
class TemperEmbrittleDemo:
    """What the demo produced — the susceptibility ranking, the four levers, the reversibility cycle."""

    # Panel A — J-factor susceptibility ranking
    ranking: list[tuple[str, float, bool]]      # (label, J, mo_protected) sorted ascending
    j_threshold: float
    # Panel B/C — the danger window and the four levers
    window: tuple[float, float]
    nose: tuple[float, float]
    de_embrittle_T: float
    levers: list[tuple[str, bool]]              # (lever label, embrittled?) for the victim
    # Panel D — the reversibility cycle (state label, embrittled?)
    cycle: list[tuple[str, bool]]
    victim_J: float


def _embrittled(comp: Steel, *, exposure_T_C: float, slow_cool: bool) -> bool:
    return te.temper_embrittlement_check(
        Heat(composition=comp), exposure_T_C=exposure_T_C, slow_cool=slow_cool
    ).has_defect(te.TEMPER_EMBRITTLED)


def compute() -> TemperEmbrittleDemo:
    """Rank susceptibility, run the four levers on the victim, and trace the reversibility cycle."""
    # Panel A — J-factor for the registry (with residual P) plus the victim and its Mo-cured twin.
    rows: list[tuple[str, float, bool]] = []
    for name in REGISTRY:
        s = replace(STEELS[name], P=RESIDUAL_P)
        rows.append((name, te.j_factor(s), s.Mo >= te.MO_SUPPRESSION_PCT))
    for s in (VICTIM, CURED):
        rows.append((s.name, te.j_factor(s), s.Mo >= te.MO_SUPPRESSION_PCT))
    rows.sort(key=lambda r: r[1])

    # Panel C — the four levers, each defeating embrittlement of the susceptible victim. All temper ABOVE the
    # window (so the cool rate THROUGH it is the variable): slow cool dwells and embrittles, the others escape.
    levers = [
        ("slow-cool through window\n(the failure)", _embrittled(VICTIM, exposure_T_C=TEMPER_T, slow_cool=True)),
        ("fast cool through window", _embrittled(VICTIM, exposure_T_C=TEMPER_T, slow_cool=False)),
        ("+0.5 % Mo (the cure)", _embrittled(CURED, exposure_T_C=TEMPER_T, slow_cool=True)),
        ("clean heat (low P)", _embrittled(CLEAN, exposure_T_C=TEMPER_T, slow_cool=True)),
    ]

    # Panel D — reversibility: embrittle → reheat>600 + fast cool (reset) → slow-cool again (re-embrittle).
    cycle = [
        ("temper + slow cool", _embrittled(VICTIM, exposure_T_C=TEMPER_T, slow_cool=True)),
        (f"reheat {REHEAT_T:.0f} °C\n+ fast cool", _embrittled(VICTIM, exposure_T_C=REHEAT_T, slow_cool=False)),
        ("slow-cool again", _embrittled(VICTIM, exposure_T_C=TEMPER_T, slow_cool=True)),
    ]

    return TemperEmbrittleDemo(
        ranking=rows, j_threshold=te.J_SUSCEPTIBLE,
        window=te.TE_WINDOW_C, nose=te.TE_NOSE_C, de_embrittle_T=te.DE_EMBRITTLEMENT_C,
        levers=levers, cycle=cycle, victim_J=te.j_factor(VICTIM),
    )


def print_summary(demo: TemperEmbrittleDemo) -> None:
    """Print the susceptibility ranking, the four levers, and the reversibility cycle."""
    print("\nTemper embrittlement — the reversible, alloy-driven phosphorus consequence (martensitic P)\n")

    print("J-factor susceptibility ranking  (Watanabe (Mn+Si)(P+Sn)·10⁴; susceptible above "
          f"{demo.j_threshold:.0f}):")
    for name, J, mo in demo.ranking:
        cue = "susceptible" if J >= demo.j_threshold else "clean"
        mocue = "  [Mo-protected]" if mo else ""
        print(f"    {name:<26} J = {J:6.0f}   {cue}{mocue}")

    print(f"\nThe victim (J = {demo.victim_J:.0f}) is saved by ANY one lever:")
    for label, emb in demo.levers:
        print(f"    {label.replace(chr(10),' '):<34} → {'EMBRITTLED' if emb else 'tough'}")

    print(f"\nReversibility (the danger window {demo.window[0]:.0f}–{demo.window[1]:.0f} °C, "
          f"reset above {demo.de_embrittle_T:.0f} °C):")
    for label, emb in demo.cycle:
        print(f"    {label.replace(chr(10),' '):<26} → {'EMBRITTLED' if emb else 'tough'}")

    print("\n→ J-factor + danger window + Mo cure are cited / by-construction — no strict tooth (the "
          "segregation-nose\n  gate was run and failed). This closes phosphorus' martensitic path; "
          "cold_short_check closed the ferritic one.")


def save_figure(demo: TemperEmbrittleDemo) -> Path:
    """Render and bank the temper-embrittlement artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import temper_embrittlement_figure

    fig = temper_embrittlement_figure(demo)
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
