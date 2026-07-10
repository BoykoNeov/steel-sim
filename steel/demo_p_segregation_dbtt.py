"""A2-B: why the bulk P→DBTT slope can't be pinned — the grain-boundary-coverage mechanism.

Runs :mod:`steel.p_segregation_dbtt` and banks the verdict. Phosphorus' bulk contribution to the
Cottrell–Petch DBTT (:data:`steel.grain.ITT_K_P`) has always been a **flagged bracket** — ≈ 40–78 °C
per 0.1 wt% P — never a teeth-bearing coefficient. This demo shows *why*, mechanistically: the clean
measured form of P embrittlement is **GB coverage → DBTT**, and it is separated from the engine's
bulk-wt% term by two independently non-universal gaps —

  1. **bulk P → GB coverage** (a Langmuir–McLean isotherm whose enrichment depends on the segregation
     temperature / thermal history — the FLAGGED, underdetermined leg), and
  2. **GB coverage → DBTT** (measured, linear, but **per steel**: 3.12 °C/at% in ferritic IF steel up
     to 13.31 in tempered-martensite SA508-4N — a 4.3× cross-*domain* span, plus a 2× grain-size span).

Composing them, the bulk slope becomes a **product of two non-universal factors** whose range
(~5–120 °C/0.1 wt%) *contains* the documented 40–78 bracket, with the engine's flagged 50 mid-range.
The mechanism reproduces the bracket's magnitude and **explains its width** — but pins nothing. There
is **no independent in-domain holdout** (the only ferritic/transgranular steel is the fitted IF one),
so — like the temper-embrittlement gate and the B3 legs — this carries **no claimable tooth**, and it
touches no engine (ADR 0010). It is the mechanistic close of the A2 sourcing gate's conclusion.

Run headless (prints the verdict, saves the figure):

    python -m steel.demo_p_segregation_dbtt
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import p_segregation_dbtt as ps

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-p-segregation-dbtt.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-p-segregation-dbtt.png"

# The T_seg grid the figure sweeps for the composed-slope panel (segregation/ageing window, °C).
T_SEG_GRID_C: tuple[float, ...] = (350.0, 375.0, 400.0, 425.0, 450.0, 475.0, 500.0, 525.0, 550.0)


@dataclass(frozen=True)
class PSegregationDemo:
    """Validated values/arrays for the A2-B figure (the plot layer only draws these, ADR 0002)."""

    summary: ps.PSegregationSummary
    relations: tuple[ps.CoverageDBTT, ...]
    t_seg_grid: tuple[float, ...]


def compute() -> PSegregationDemo:
    return PSegregationDemo(
        summary=ps.summary(), relations=ps.COVERAGE_DBTT_RELATIONS, t_seg_grid=T_SEG_GRID_C,
    )


def print_summary(d: PSegregationDemo) -> None:
    s = d.summary
    print("\nA2-B — the grain-boundary-coverage mechanism behind grain.ITT_K_P's flag "
          "(NO claimable tooth)\n")
    print("THE QUESTION: why is P's bulk contribution to the DBTT (grain.ITT_K_P) a FLAGGED bracket")
    print("  (≈ 40–78 °C/0.1 wt% P), not a pinned coefficient? Answer: it is a reduced form of a")
    print("  two-gap mechanism, each gap independently non-universal.\n")

    print("GAP 2 — GB coverage → DBTT is CITED but PER-STEEL (the '8620 wall' of the front end):")
    for r in d.relations:
        note = " (ferritic MATRIX, but no solute C → still intergranular; the FITTED steel)" \
            if r is ps.IF_STEEL else ""
        dom = f"{r.matrix} / {r.fracture}  — ≠ engine's transgranular law{note}"
        extra = f", PAGS {r.pags_um:.0f} µm" if r.pags_um else (
            f", {r.hardness_HV:.0f} HV" if r.hardness_HV else "")
        print(f"  {r.slope_C_per_at:5.2f} °C/at%   {r.name}{extra}")
        print(f"                {dom}")
    print(f"\n  cross-steel slope span      = ×{s.slope_span:.2f}   (3.12 IF → 13.31 SA508)")
    print(f"  within-SA508 grain-size span= ×{s.grain_size_span:.2f}   (13.13 @34µm vs 6.69 @112µm)")
    print(f"  naive IF→SA508 transfer bias= ×{ps.naive_transfer_bias(ps.IF_STEEL, ps.SA508_FIXED_H):.2f}"
          "  (the cost of assuming universality)\n")

    print("GAP 1 — bulk P → GB coverage is the FLAGGED, underdetermined leg (McLean isotherm):")
    print("  coverage depends on the segregation temperature (thermal history), so one bulk P maps to")
    print("  a RANGE of coverages — e.g. 0.03 wt% P →")
    for T in (350.0, 450.0, 550.0):
        print(f"      T_seg={T:.0f} °C → {ps.mclean_gb_coverage(0.03, T) * 100:.2f} at% GB P")
    print("  (absolute coverage under-predicted by the single-solute isotherm — used for SENSITIVITY")
    print("   only, never as a coverage benchmark; the bracket rests on the slope composition.)\n")

    print("THE SYNTHESIS — compose the two gaps → the bulk slope (order-of-magnitude, rides McLean):")
    print(f"  composed bulk-slope range      = {s.composed_min:.1f}–{s.composed_max:.1f} °C/0.1 wt% "
          f"(a ×{s.composed_max / s.composed_min:.0f} span)")
    print(f"  contains documented 40–78 band = {s.bracket_contained}")
    print(f"  contains engine flag (50)      = {s.engine_value_inside}")
    print("  → NOT a derivation of the specific 40–78 band; the point is that TWO non-universal factors")
    print("    (per-steel slope × thermal-history enrichment) make the bulk slope irreducibly steel-/")
    print("    path-dependent → a flagged BRACKET is the only honest form. The mechanism pins nothing.\n")

    print("THE TEETH VERDICT (structural — the honest posture from line one):")
    print(f"  in-domain (transgranular) holdout? = {s.has_independent_in_domain_holdout}")
    print("  EVERY coverage→DBTT relation is the intergranular GB-segregation axis — a different fracture")
    print("  mode from the engine's transgranular-cleavage law. IF is ferritic in matrix but intergranular")
    print("  too (interstitial-free → no solute C at the boundaries), and is additionally the fitted steel.")
    print("  So no relation is in the engine's domain: there is no in-domain holdout at all → NO TOOTH.")
    print("  grain.ITT_K_P stays flagged and UNCHANGED (500 °C/wt%), now with a mechanistic justification")
    print("  for the flag rather than a bare bracket. No engine touch, no refit (ADR 0010).")


def save_figure(d: PSegregationDemo) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import p_segregation_dbtt_figure

    fig = p_segregation_dbtt_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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
