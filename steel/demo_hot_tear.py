"""Hot-tearing: same sulfur, two manganese levels — one casting tears, one is sound (segregation-aware).

*Whether sulfur tears a casting is set by the Mn:S in the **last liquid to freeze**, not the bulk Mn:S.*
The demonstrable artifact for the sulfur consequence at the **casting** stage (the segregation-amplified
sibling of forging-stage red-shortness, :mod:`steel.hot_work`): slag partition (:mod:`steel.slag`) leaves the
residual sulfur and flags a single, flat **risk** (S > 0.040 %, Mn-blind *and* segregation-blind); this reads
whether a *casting* actually grows a Fe–FeS interdendritic film and **hot-tears** — which is a Mn:S question,
amplified by the Scheil enrichment of the last liquid. Two-tier, like cold-short / red-short / flaking /
gas-porosity: the upstream stage sets the risk, this the consequence.

What it shows
-------------
1. **The hero — same sulfur, the manganese decides.** Two heats with the *same* sulfur (both **within** the
   0.040 % spec → both risk-cleared) and **both clearing the bulk MnS stoichiometry** (Mn:S ≥ 1.71, so
   neither is red-short at the forge). Yet the lower-Mn heat (Mn:S 10) hot-tears: segregation drives its
   **interdendritic film** Mn:S down to ~1.2, below stoichiometry, so a Fe–FeS film forms in the last liquid.
   The higher-Mn heat (Mn:S 22) keeps its film above 1.71 and is sound. Same sulfur, the manganese decides —
   and the flat sulfur line cannot see it.
2. **The Mushet lever.** That lower-Mn heat *is* saved — by adding manganese (the higher-Mn heat is the same
   sulfur, Mn:S lifted past the segregation-amplified threshold). The casting-stage fix is the same
   manganese that fixes red-shortness, only the threshold is in the **tens**, not 1.71.
3. **The two-direction disagreement with the flat risk line.** A third heat carries sulfur **over** the
   0.040 % spec (risk-flagged) but enough manganese (Mn:S 25) to keep even its segregated film MnS — sound.
   So the flat line both **under-warns** (the in-spec low-Mn heat tears) and **over-warns** (the over-spec
   high-Mn heat is sound). The Mn:S-and-segregation-aware consequence corrects both.

The posture (carried from :mod:`hot_tear`): a thin consumer (the red-short / gas-porosity class), **no
claimable tooth** — the verdict *is* the cited Scheil partition feeding the cited MnS stoichiometry. The one
soft OoM-coherence note is that segregation amplifies the stoichiometric **1.71** into the **tens** (the bulk
Mn:S a casting needs, :func:`~steel.hot_tear.critical_bulk_mn_s`), reproducing the empirical "sound castings
need Mn:S ≳ 20" rule (Toledo 1993) with no tuning — the *order* is robust, the *value* is cutoff-tuned
(``f_s`` is a free knob). The freezing-range / strain-rate (RDG / Clyne–Davies) driver and the
carbon-peritectic contribution are named deferrals; the late-freezing span lives illustratively in
:mod:`steel.solidification`.

Run headless:

    python -m steel.demo_hot_tear
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import hot_tear as ht
from . import slag
from .heat_state import Heat
from .sweep import STEELS

# A representative low-carbon cast structural backbone; the heats differ only in Mn and S (the control axis).
_BACKBONE = replace(STEELS["1045"], C=0.18, Mn=0.0, Si=0.30, P=0.0, S=0.0, name="cast structural")

S_IN_SPEC = 0.030      # within slag's 0.040 % sulfur spec (so the high-sulfur risk is NOT raised)
S_OVER_SPEC = 0.060    # over the spec (risk-flagged) — the over-warning direction
MN_LOW = 0.30          # Mn:S 10  — clears bulk stoichiometry, but the film tears
MN_FIX = 0.66          # Mn:S 22  — the Mushet-lifted same-sulfur heat (sound)
MN_HIGH = 1.50         # Mn:S 25 at the higher sulfur — over the spec yet sound

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-hot-tear.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-hot-tear.png"


@dataclass(frozen=True)
class HotTearDemo:
    """What the demo produced — the manganese-decides hero, the Mushet lever, and the segregation amplification."""

    s_spec_pct: float
    mn_s_stoich: float
    seg_factor: float
    critical_bulk: float
    empirical_mn_s: float
    fs: float
    # the three heats: (label, S, bulk Mn:S, film Mn:S, hot_tear, risk_flagged)
    heats: tuple[tuple[str, float, float, float, bool, bool], ...]
    # panel — the segregation map: bulk Mn:S grid → film Mn:S (no-segregation 1:1 vs actual)
    bulk_grid: np.ndarray
    film_curve: np.ndarray
    # panel — the cutoff-dependence of the critical bulk Mn:S (the OoM-coherence robustness)
    fs_grid: np.ndarray
    critical_curve: np.ndarray
    empirical_band: tuple[float, float]


def _heat(Mn: float, S: float) -> Heat:
    """A cast heat at the structural backbone with the given Mn and S (the only axis that moves)."""
    return Heat(composition=replace(_BACKBONE, Mn=Mn, S=S))


def compute() -> HotTearDemo:
    """Cast three heats — same-S low/high Mn and an over-spec high-Mn — and read the hot-tear contrast."""
    specs = [
        ("Mn:S 10\n(in spec)", MN_LOW, S_IN_SPEC),
        ("Mn:S 22\n(more Mn)", MN_FIX, S_IN_SPEC),
        ("Mn:S 25\n(S>spec)", MN_HIGH, S_OVER_SPEC),
    ]
    heats = []
    for label, Mn, S in specs:
        out = ht.hot_tear_check(_heat(Mn, S))
        a = ht.hot_tear_assessment(Mn, S)
        heats.append((label, S, a.bulk_mn_s, a.last_liquid_mn_s,
                      out.has_defect(ht.HOT_TEAR), S > slag.MAX_SULFUR_PCT))

    bulk_grid = np.linspace(0.0, 40.0, 200)
    film_curve = bulk_grid * ht.segregation_factor()

    fs_grid = np.linspace(0.85, 0.99, 120)
    critical_curve = np.array([ht.critical_bulk_mn_s(fs) for fs in fs_grid])

    return HotTearDemo(
        s_spec_pct=slag.MAX_SULFUR_PCT,
        mn_s_stoich=ht.MN_S_STOICH,
        seg_factor=ht.segregation_factor(),
        critical_bulk=ht.critical_bulk_mn_s(),
        empirical_mn_s=ht.EMPIRICAL_MN_S_CASTING,
        fs=ht.FS_LAST_LIQUID,
        heats=tuple(heats),
        bulk_grid=bulk_grid, film_curve=film_curve,
        fs_grid=fs_grid, critical_curve=critical_curve,
        empirical_band=(6.0, 36.0),
    )


def print_summary(demo: HotTearDemo) -> None:
    """Print the two-tier story: a flat sulfur risk line, then the segregation-aware hot-tear consequence."""
    print("\nHot-tearing — same sulfur, the manganese decides (segregation-amplified)\n")
    print(f"Slag's risk line is flat and Mn-blind: S > {demo.s_spec_pct:.3f} %. The consequence is the Mn:S "
          f"in the\n  LAST LIQUID to freeze — segregation enriches sulfur ~{1/demo.seg_factor:.0f}× more than "
          f"manganese, so the\n  interdendritic film Mn:S is ~{demo.seg_factor:.2f}× the bath's "
          f"(f_s = {demo.fs:.2f}).\n")

    print(f"Three castings (stoichiometric MnS needs Mn:S ≥ {demo.mn_s_stoich:.2f}; the SEGREGATED film needs "
          f"bulk Mn:S ≳ {demo.critical_bulk:.0f}):")
    for label, S, bulk, film, tear, risk in demo.heats:
        tag = "HOT-TEAR" if tear else "sound"
        print(f"    {label.replace(chr(10), ' '):18s} S {S:.3f} % (risk: {risk})  bulk Mn:S {bulk:5.1f}  "
              f"→ film Mn:S {film:.2f}  → {tag}")
    print("  → the in-spec low-Mn heat tears though the bath clears stoichiometry (segregation); the same "
          "sulfur\n    with more Mn is sound (the Mushet lever); the over-spec heat is sound because its Mn:S "
          "is high.")

    print(f"\nThe soft OoM-coherence note (NO claimable tooth): segregation amplifies the stoichiometric "
          f"{demo.mn_s_stoich:.2f}\n  into the TENS — a casting needs bulk Mn:S ≈ {demo.critical_bulk:.0f} "
          f"(at f_s = {demo.fs:.2f}; ≈9 at 0.90, ≈45 at 0.99),\n  reproducing the empirical 'sound castings "
          f"need Mn:S ≳ {demo.empirical_mn_s:.0f}' rule (Toledo 1993) with no tuning.")
    print("  The ORDER is cutoff-robust; the specific value is cutoff-tuned (f_s is a free knob). Really "
          "by-construction.")
    print("\n→ Ceiling: the S-film sub-mechanism only — the RDG / Clyne–Davies feeding-strain driver and the "
          "carbon-\n  peritectic contribution are deferred; the freezing-range span lives in steel.solidification.")


def save_figure(demo: HotTearDemo) -> Path:
    """Render and bank the hot-tear artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import hot_tear_figure

    fig = hot_tear_figure(demo)
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
