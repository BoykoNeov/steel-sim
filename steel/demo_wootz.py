"""Wootz / Damascus carbide banding: same ultra-high-carbon steel, the trace vanadium decides the pattern.

*Two crucible cakes of the same 1.5 %-carbon steel, forged through the same thermal cycles — one carries a
trace of vanadium from its ore and waters into a Damascus blade; the other is clean and comes out plain.* The
demonstrable artifact for the **signed good-impurity foil** (:mod:`steel.wootz`): the very "impurity" a modern
clean-steel spec rejects is the one the wootz smith requires — off-spec composition, signed either way
(``steel-making.md`` §14.5 / §15.4, the one genuine front-end physics gap).

What it shows
-------------
1. **The hero — same steel, same forging, the trace V decides.** One genuine wootz (1.5 %C, **V ≈ 60 ppm**) and
   one clean modern ultra-high-carbon steel (1.5 %C, **V < 10 ppm**), both cycled identically in the
   carbide-stable forging window. The vanadium-bearing heat develops the carbide banding; the clean one, forged
   *exactly* the same way, raises the **``wootz-pattern-failed``** flag — "the smith did everything right; the
   ore lacked the vanadium." Nothing but the trace chemistry moved.
2. **Three gates, all required.** Drop any one and the pattern fails: a plain medium-carbon bar (0.45 %C, no
   proeutectoid cementite to band) never patterns whatever its V; a genuine wootz forged **too hot** (above
   A_cm − 50 °C, where the cementite dissolves) loses its pattern too. The plain bar raises **no** flag — it
   never intended a pattern (the intent gate).
3. **The same Scheil engine, opposite sign (by construction).** The carbide-former enrichment that aligns the
   bands is the *same* interdendritic Scheil solid-segregation ratio (:func:`steel.casting.segregation_ratio`)
   that, applied at the centerline, makes segregation a hardenability **defect**. One engine, two signs.

The posture (carried from :mod:`wootz`): a thin consumer, **no claimable tooth** — the three gates are
Verhoeven & Pendray's cited threshold lines (V ≥ 40 ppm; Mn ≥ 200 ppm; the 50–100 °C-below-A_cm window), the
proeutectoid cementite is :mod:`steel.fe_c`'s lever rule, the enrichment is :mod:`steel.casting`'s Scheil. The
band spacing (30–70 µm) is a **cited observation**, not a computed prediction; the enrichment ratio is
**representative** (the pinned Mo former as the exemplar — ``k_V`` is not separately pinned).

Run headless:

    python -m steel.demo_wootz
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import casting, fe_c
from . import wootz as wz
from .heat_state import Heat
from .sweep import Steel

# A genuine wootz cake and a clean modern UHC twin — only the trace vanadium (and the carbon gate / forging
# gate cases) move. Bespoke ~1.5 %C compositions: the repo grades top out near eutectoid (1080 = 0.80 %C).
_WOOTZ = Steel(C=1.5, Mn=0.30, Si=0.10, name="wootz (V-bearing ore)")
_CLEAN = Steel(C=1.5, Mn=0.30, Si=0.10, name="clean modern UHC")
_PLAIN = Steel(C=0.45, Mn=0.75, Si=0.25, name="plain 1045")

_V_GENUINE = 60.0     # ppmw V — a genuine Damascus level (Verhoeven Table IV: <10–270 ppmw)
_V_CLEAN = 5.0        # ppmw V — modern clean stock, below the 40 ppm banding threshold

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-wootz.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-wootz.png"


@dataclass(frozen=True)
class WootzDemo:
    """What the demo produced — the trace-V hero, the three-gate cases, and the signed-Scheil curves."""

    v_threshold_ppm: float
    band_spacing_um: tuple[float, float]
    acm_C: float
    window: tuple[float, float]
    genuine_peak_C: float
    too_hot_peak_C: float
    # readings: (label, C, V ppm, effective former, patterned, pattern_failed, hyper, forged_as_wootz)
    readings: tuple[tuple[str, float, float, float, bool, bool, bool, bool], ...]
    # the signed Scheil curves over the solid-fraction grid
    fs_grid: np.ndarray
    former_enrichment_curve: np.ndarray   # carbide former (Mo k_γ=0.70) — the ASSET (interdendritic bands)
    centerline_defect_curve: np.ndarray   # the SAME ratio casting.py uses for the centerline DEFECT
    interdendritic_fs: float
    former_enrichment_at_band: float


def _read(comp: Steel, *, v_ppm: float, forge_peak_C, forge_cycles: int) -> tuple:
    """Run the orchestrator + assessment for one composition/forging case and pack the figure-row tuple."""
    heat = Heat(composition=comp)
    out = wz.wootz_pattern_check(heat, v_ppm=v_ppm, forge_peak_C=forge_peak_C, forge_cycles=forge_cycles)
    a = wz.wootz_assessment(comp.C, v_ppm=v_ppm, forge_peak_C=forge_peak_C, forge_cycles=forge_cycles)
    assert out.has_defect(wz.WOOTZ_PATTERN_FAILED) == a.pattern_failed
    return (comp.name, comp.C, v_ppm, a.effective_former_ppm, a.patterned, a.pattern_failed,
            a.hypereutectoid, a.forged_as_wootz)


def compute() -> WootzDemo:
    """Read the genuine and clean cakes (same forging), the carbon/forging gate cases, and the Scheil curves."""
    acm = fe_c.Acm(_WOOTZ.C)
    lo, hi = wz.forging_window(_WOOTZ.C)
    genuine_peak = round((lo + hi) / 2.0)          # mid-window cyclic forging peak
    too_hot_peak = round(acm + 20.0)               # above A_cm — cementite dissolves

    readings = (
        _read(_WOOTZ, v_ppm=_V_GENUINE, forge_peak_C=genuine_peak, forge_cycles=7),   # patterns
        _read(_CLEAN, v_ppm=_V_CLEAN, forge_peak_C=genuine_peak, forge_cycles=7),     # fails — clean ore (flag)
        _read(_PLAIN, v_ppm=_V_GENUINE, forge_peak_C=850.0, forge_cycles=7),          # carbon gate (no flag)
        _read(_WOOTZ, v_ppm=_V_GENUINE, forge_peak_C=too_hot_peak, forge_cycles=7),   # forging gate (no flag)
    )

    fs_grid = np.linspace(0.0, 0.97, 200)
    k_former = casting.partition_coefficient("Mo", "gamma")    # the pinned carbide former, γ (hypereutectoid)
    k_centerline = casting.partition_coefficient("Mn", "delta")  # the substitutional casting enriches at center
    former_curve = np.array([casting.segregation_ratio(k_former, fs) for fs in fs_grid])
    centerline_curve = np.array([casting.segregation_ratio(k_centerline, fs) for fs in fs_grid])

    return WootzDemo(
        v_threshold_ppm=wz.V_BANDING_MIN_PPM,
        band_spacing_um=(wz.BAND_SPACING_MIN_UM, wz.BAND_SPACING_MAX_UM),
        acm_C=acm,
        window=(lo, hi),
        genuine_peak_C=genuine_peak,
        too_hot_peak_C=too_hot_peak,
        readings=readings,
        fs_grid=fs_grid,
        former_enrichment_curve=former_curve,
        centerline_defect_curve=centerline_curve,
        interdendritic_fs=wz.FS_INTERDENDRITIC,
        former_enrichment_at_band=wz.former_interdendritic_enrichment(),
    )


def print_summary(demo: WootzDemo) -> None:
    """Print the signed-impurity story: the trace-V hero, the three gates, the same-engine-opposite-sign beat."""
    print("\nWootz / Damascus carbide banding — the signed GOOD-impurity foil\n")
    print(f"The Damascus pattern needs a trace carbide-former (V ≥ {demo.v_threshold_ppm:.0f} ppm) — the very "
          f"'impurity' a modern\n  clean-steel spec rejects. 'Bad steel' and 'good steel' are the same composition, "
          f"signed either way.\n")

    print(f"Three gates, all required (hypereutectoid C • V ≥ {demo.v_threshold_ppm:.0f} ppm • forged "
          f"{demo.window[0]:.0f}–{demo.window[1]:.0f} °C, ≥{wz.MIN_FORGING_CYCLES} cycles):")
    for name, C, v, eff, patterned, failed, hyper, intent in demo.readings:
        verdict = "PATTERNS" if patterned else ("FAILED (flag)" if failed else "no pattern")
        flag = "  → wootz-pattern-failed" if failed else ""
        print(f"    {name:24s} C {C:.2f} %  V {v:5.0f} ppm  former {eff:5.0f}  → {verdict}{flag}")
    print(f"  → the hero: the SAME 1.5 %C steel, the SAME forging — the V-bearing cake waters into Damascus, the "
          f"clean\n    cake (forged identically) comes out plain and raises the flag. The plain 1045 and the "
          f"too-hot heat raise\n    NO flag — neither was forged as wootz (the intent gate). Off-spec by *lacking* "
          f"a good impurity.")

    print(f"\nThe same Scheil engine, opposite sign (NO claimable tooth — by construction): the carbide former "
          f"enriches\n  ×{demo.former_enrichment_at_band:.1f} in the interdendritic bands (the ASSET) by the SAME "
          f"casting.segregation_ratio that\n  makes centerline segregation a hardenability DEFECT. One engine, two "
          f"signs. Wootz is hypereutectoid, so the\n  γ partition coefficient is the right one; the amplitude is "
          f"the pinned Mo former as the exemplar (representative).")
    print(f"\n→ Ceiling: a yes/no verdict, not a rendered etch or a band-sharpness curve. The band spacing "
          f"({demo.band_spacing_um[0]:.0f}–{demo.band_spacing_um[1]:.0f} µm)\n  is a CITED observation (it traces "
          f"the interdendritic spacing), NOT computed here — that would be a manufactured\n  coherence (the cake "
          f"modulus, Chvorinov B, and the SDAS law are all soft knobs aimed at a 2×-wide target).")


def save_figure(demo: WootzDemo) -> Path:
    """Render and bank the wootz artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")
    from .plots import wootz_figure

    fig = wootz_figure(demo)
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
