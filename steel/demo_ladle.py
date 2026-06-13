"""The F3 anchor demo: trim a heat to grade — recovery decides whether it lands or misses.

*An alloy-lean tap in, a finished grade out — or a heat that missed the window and won't harden.* This is
the demonstrable artifact for **F3 Slice 1** (``docs/plans/steel-making.md`` §7) and the **seam to the back
end**: the ladle step where the composition the back end consumes is finally finalized. Where the spine and
F2 *held the alloy fixed* to isolate carbon, F3 is where the Cr / Mo / Mn / Si actually go in — so this is
where the hero-demo's off-spec input is *produced*, not hand-set.

What it shows
-------------
1. **Alloy to grade (the trim physics).** Start from an alloy-lean :func:`~steel.ladle.from_tap` heat, size
   ferroalloy additions for the assumed recovery (:func:`~steel.ladle.additions_for_grade`), and mix them in
   (:func:`~steel.ladle.mix`, dilution exact). A heat that recovers as planned lands **inside the cited 4140
   window**; the carbon dilutes a touch under the ~3 t of additions (named, second-order).

2. **The recovery shortfall is the failure mechanism (the headline).** The additions were sized for an
   assumed recovery. A bath that under-delivers — Cr/Mo recovery roughly *halved* (an under-killed bath eats
   the additions, the F2 deox-state coupling) — lands **below the window** (Cr under its 0.80 floor), so F3
   raises **off-grade** immediately. Then the *same* oil quench that through-hardens the on-grade heat lands
   a soft core on the under-trimmed one: :func:`~steel.heat_state.heat_treat` raises **soft-core**, the
   validated back-end consequence. One mistake, two flags — the front-end early warning and the back-end
   verdict — and the soft core is **emergent** (the martensite fraction crossing a spec line), the same
   class as the spine's hand-set under-dose, now produced by a modeled ladle operation.

3. **Honestly bounded.** Off-grade fires *before* soft-core (the band floor sits above the hardenability
   threshold at this section — the window is the conservative early warning). Carbon is held on F2's axis;
   the carbon **carry-in** that high-carbon ferrochrome/ferromanganese *would* add (~0.18 %C here — nearly
   half the grade's carbon) is quantified and **deferred** (:func:`~steel.ladle.carbon_pickup_pct`), the
   reason low-carbon ferroalloys exist. Recovery factors are the source-sensitive tier (ranking, not the
   last digit); P/S residual bands are out of the window (no P/S state). The trim arithmetic itself is
   structural (round-trip / conservation), not a benchmark — F3 is spine-class.

Run headless (prints the trim trail + the front-to-back divergence):

    python -m steel.demo_ladle
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import heat_state as hs
from . import ladle as ld
from .heat_state import Heat
from .sweep import STEELS, evaluate

# The hero grade + set-points (continuity with the spine / F2 / F4 demos).
GRADE = "4140"
TREAT_MEDIUM = "oil"
TREAT_DIAMETER = 0.015                  # the discriminating section: on-grade through-hardens, under-trim soft-cores
BAD_RECOVERY_FACTOR = 0.5               # the bad heat's actual Cr/Mo recovery, as a fraction of the assumed
TRIM_ELS = ("Cr", "Mo", "Mn", "Si")    # the elements drawn in the trim-bar panel (hardenability-first)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-ladle.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-ladle.png"


@dataclass(frozen=True)
class LadleDemo:
    """What the demo produced — the trimmed heats, the propagation, and the figure arrays.

    ``tap`` the alloy-lean origin; ``good`` / ``bad`` the trimmed Heats *after* heat-treat (the proof: only
    the under-recovered heat carries both off-grade and soft-core). ``good_fM`` / ``bad_fM`` / ``good_HV`` /
    ``bad_HV`` the back-end numbers behind the flags, ``spec`` the soft-core line. ``window`` the cited 4140
    bands and ``bars_*`` the per-element trim levels (panel A). ``recovery_ratio`` + (``cr_vs_recovery``,
    ``fM_vs_recovery``) the recovery-shortfall sweep (panels B/C), with ``cr_floor`` the band floor and the
    two operating points. ``carbon_carry_in`` the deferred HC-ferroalloy carbon (named).
    """

    tap: Heat
    good: Heat
    bad: Heat
    good_fM: float
    bad_fM: float
    good_HV: float
    bad_HV: float
    spec: float
    cr_floor: float
    carbon_carry_in: float
    # panel A — the trim bars
    bar_elements: tuple[str, ...]
    bars_tap: np.ndarray
    bars_good: np.ndarray
    bars_bad: np.ndarray
    window_lo: np.ndarray
    window_hi: np.ndarray
    # panels B/C — the recovery-shortfall sweep
    recovery_ratio: np.ndarray
    cr_vs_recovery: np.ndarray
    fM_vs_recovery: np.ndarray
    good_point: tuple[float, float, float]   # (recovery_ratio, landed Cr, martensite)
    bad_point: tuple[float, float, float]


def _assumed_recovery() -> dict[str, float]:
    """The recovery the additions are sized for — the ferroalloys' nominal yields."""
    return {e: ld.FERROALLOYS[e].recovery for e in ("Mn", "Si", "Cr", "Mo")}


def _treated(actual_recovery: dict[str, float] | None) -> Heat:
    """Trim a fresh tap to grade at ``actual_recovery`` and heat-treat it — one trimmed, treated Heat."""
    tap = ld.from_tap(GRADE)
    trimmed = ld.trim_to_grade(tap, GRADE, actual_recovery=actual_recovery)
    return hs.heat_treat(trimmed, medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)


def compute() -> LadleDemo:
    """Trim an on-grade and an under-recovered heat, then assemble the trim / sweep arrays."""
    assumed = _assumed_recovery()
    bad_actual = {**assumed, "Cr": assumed["Cr"] * BAD_RECOVERY_FACTOR, "Mo": assumed["Mo"] * BAD_RECOVERY_FACTOR}

    tap = ld.from_tap(GRADE)
    good = _treated(None)               # delivered = assumed → on grade
    bad = _treated(bad_actual)          # Cr/Mo recovery halved → off grade + soft core

    good_o = evaluate(good.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)
    bad_o = evaluate(bad.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)

    window = ld.GRADE_WINDOWS[GRADE]
    cr_floor = window.bands["Cr"][0]
    charges = ld.additions_for_grade(tap.composition, STEELS[GRADE])
    carbon_carry_in = ld.carbon_pickup_pct(charges)

    # Panel A — the trim bars: tap (lean) → good (on grade) → bad (short), against each element's window band.
    def comp_of(h: Heat) -> dict[str, float]:
        c = h.composition
        return {"Cr": c.Cr, "Mo": c.Mo, "Mn": c.Mn, "Si": c.Si}
    bars_tap = np.array([comp_of(tap)[e] for e in TRIM_ELS])
    bars_good = np.array([comp_of(good)[e] for e in TRIM_ELS])
    bars_bad = np.array([comp_of(bad)[e] for e in TRIM_ELS])
    window_lo = np.array([window.bands[e][0] for e in TRIM_ELS])
    window_hi = np.array([window.bands[e][1] for e in TRIM_ELS])

    # Panels B/C — the recovery-shortfall sweep: drop the actual Cr/Mo recovery from the assumed, read the
    # landed Cr and the resulting core martensite (the failure mechanism → the validated consequence).
    recovery_ratio = np.linspace(0.30, 1.05, 120)
    cr_vs_recovery = np.empty_like(recovery_ratio)
    fM_vs_recovery = np.empty_like(recovery_ratio)
    tap_steel = tap.composition
    for i, r in enumerate(recovery_ratio):
        actual = {**assumed, "Cr": assumed["Cr"] * r, "Mo": assumed["Mo"] * r}
        trimmed, _ = ld.mix(tap_steel, charges, recovery=actual)
        cr_vs_recovery[i] = trimmed.Cr
        fM_vs_recovery[i] = evaluate(replace(trimmed, name=GRADE), medium=TREAT_MEDIUM,
                                     diameter=TREAT_DIAMETER).result.martensite

    good_point = (1.0, good.composition.Cr, good_o.result.martensite)
    bad_point = (BAD_RECOVERY_FACTOR, bad.composition.Cr, bad_o.result.martensite)

    return LadleDemo(
        tap=tap, good=good, bad=bad,
        good_fM=good_o.result.martensite, bad_fM=bad_o.result.martensite,
        good_HV=good_o.HV, bad_HV=bad_o.HV, spec=hs.MIN_MARTENSITE_SPEC, cr_floor=cr_floor,
        carbon_carry_in=carbon_carry_in,
        bar_elements=TRIM_ELS, bars_tap=bars_tap, bars_good=bars_good, bars_bad=bars_bad,
        window_lo=window_lo, window_hi=window_hi,
        recovery_ratio=recovery_ratio, cr_vs_recovery=cr_vs_recovery, fM_vs_recovery=fM_vs_recovery,
        good_point=good_point, bad_point=bad_point,
    )


def print_summary(demo: LadleDemo) -> None:
    """Print the trim trail, the cited window, and the front-to-back divergence (the two flags)."""
    print(f"\nF3 — trim a {GRADE} heat to grade: recovery decides whether it lands or misses\n")

    print("Trim sequence (the on-grade heat), step by step:")
    for step in demo.good.history:
        if step.name == "heat-treat":
            continue
        print(f"    • {step.name:<6} {step.summary}")

    print(f"\nThe under-recovered heat (Cr/Mo recovery ~{BAD_RECOVERY_FACTOR:.0%} of assumed — an under-killed "
          f"bath eats the additions):")
    for step in demo.bad.history:
        if step.name == "heat-treat":
            continue
        print(f"    • {step.name:<6} {step.summary}")

    print(f"\nSame {TREAT_MEDIUM} quench, Ø{TREAT_DIAMETER * 1000:.0f} mm — the trim decides:")
    print(f"    on-grade : Cr {demo.good.composition.Cr:.2f}, Mo {demo.good.composition.Mo:.2f} → "
          f"{demo.good_fM:.0%} martensite, {demo.good_HV:.0f} HV  "
          f"{'(soft core)' if demo.good.has_defect(hs.SOFT_CORE) else '— through-hardens, on grade'}")
    flags = " + ".join(demo.bad.defects) if demo.bad.defects else "clean"
    print(f"    under-trim: Cr {demo.bad.composition.Cr:.2f}, Mo {demo.bad.composition.Mo:.2f} → "
          f"{demo.bad_fM:.0%} martensite, {demo.bad_HV:.0f} HV  ← {flags.upper()}")

    print(f"\n→ One ladle mistake (a recovery shortfall) carries TWO flags: off-grade at the trim (Cr below the "
          f"{demo.cr_floor:.2f} %\n  floor of the cited {GRADE} window — F3's early warning) and a validated "
          f"back-end soft core at the\n  quench (martensite under the {demo.spec:.0%} spec). At this section "
          f"the off-grade flag fires first — the\n  chemistry window is the conservative front-end catch; at a "
          f"thicker section an *on-grade* heat could\n  still soft-core (the chemistry-spec ≠ H-band point, "
          f"deferred — the ordering is section-dependent).")
    print(f"\n  Deferred (named): high-carbon ferrochrome/ferromanganese would carry +{demo.carbon_carry_in:.2f} "
          f"%C into the heat\n  (~{demo.carbon_carry_in / 0.40:.0%} of {GRADE}'s carbon) — held off F2's axis "
          f"here; it is why low-carbon ferroalloys exist.")


def save_figure(demo: LadleDemo) -> Path:
    """Render and bank the alloy-to-grade artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import ladle_figure

    fig = ladle_figure(demo)
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
