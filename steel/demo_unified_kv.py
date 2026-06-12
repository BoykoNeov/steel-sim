"""The §19 demo: the bainite bay, *opened* in continuous cooling (the 6b deepening).

*Composition in, the bay out.* Phase 6b proved the bainite bay cannot be wired into the single
Grossmann-shifted curve; this demo races the three cited Li/Kirkaldy–Venugopalan reactions
(ferrite/pearlite/bainite) on one shared austenite pool (:mod:`unified_kv`) and shows the bay
**emerge** for an alloy steel (4340) — while a plain-carbon eutectoid (1080) opens **no** bay.

Two panels (``plots.unified_kv_figure``):

1. **left — 4340: the bay opens.** The three competing C-curves: alloying pushes the reconstructive
   **ferrite** and **pearlite** noses ~10³× to the right (cited ``FC``/``PC``) while the displacive
   **bainite** nose barely moves (weak, wrong-signed ``BC`` → per-steel atlas-anchored). The gap is a
   real **bay** — and three cooling paths show the consequence: a fast quench → **martensite**, an
   intermediate cool threads the bay → **bainite**, a slow cool → **ferrite + pearlite**.
2. **right — 1080: no bay.** Eutectoid plain carbon: no proeutectoid ferrite, and the pearlite and
   bainite noses sit almost on top of each other (a merged C-curve) — so no cooling path can dodge
   pearlite into a bainite plateau. The consistency contrast that makes the 4340 bay meaningful.

The two-model honesty (why both this and the single-curve pipeline exist)
-------------------------------------------------------------------------
* **The single-curve pipeline** (:mod:`pathint`) stays the **validated workhorse**: one C-curve +
  Grossmann ``M``, it carries the four-curves and 1045/4140 Jominy benchmarks and works for *any*
  composition. It is byte-identical — nothing here touches it.
* **This unified-KV view** is a **per-steel-anchored demonstrator** (the two atlas steels 1080/4340
  only): it opens the bay from cited differentials, but cannot predict cross-steel bainite (the BC
  wall, the 8620 carbon-spread ceiling), bridges the *isothermal* atlas to CCT by Scheil additivity
  with **no measured-CCT validation**, and uses the carbon-only bainite hardness. It is the
  mechanism-deepening lens, **not** a replacement for the workhorse.

Run headless (saves the figure, prints the summary):

    python -m steel.demo_unified_kv
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import unified_kv as ukv
from . import cooling
from .kinetics import _kv_shape_integral

# The start fraction the C-curves are read at (matches plots.plot_ttt and the pearlite calibration).
START_X = 0.01

# The 4340 demonstrator ladder: (label, medium, diameter m) → martensite / bainite / ferrite+pearlite.
DEMO_PATHS = [
    ("fast quench",   "water",   0.012),
    ("intermediate",  "air",     0.050),
    ("slow cool",     "furnace", 0.500),
]

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-unified-kv-bay.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-unified-kv-bay.png"


@dataclass(frozen=True)
class SteelView:
    """The three competing C-curves + ceilings for one steel (the plot layer draws these)."""

    steel: str
    temps: np.ndarray                       # °C, shared temperature axis (Ms → Ae1)
    ferrite_tau: np.ndarray                 # s, ferrite start time (nan where inert / above Ae3)
    pearlite_tau: np.ndarray                # s, pearlite start time (nan above Ae1)
    bainite_tau: np.ndarray                 # s, bainite start time (nan above Bs)
    Ae3: float
    Ae1: float
    Bs: float
    Ms: float
    has_ferrite: bool                       # False for eutectoid 1080 (f_pro = 0 → ferrite inert)
    ferrite_nose: tuple | None              # (T °C, t s) or None
    pearlite_nose: tuple                    # (T °C, t s)
    bainite_nose: tuple                     # (T °C, t s)


@dataclass(frozen=True)
class PathOutcome:
    """One demonstrator cooling path and the microstructure the competition produced."""

    label: str
    t: np.ndarray
    T: np.ndarray
    fractions: dict
    dominant: str
    Vr: float


@dataclass(frozen=True)
class UnifiedDemo:
    """Validated arrays for the §19 figure: the 4340 bay, the 1080 no-bay, and the 4340 ladder."""

    bay: SteelView                          # 4340 — the bay opens
    nobay: SteelView                        # 1080 — the consistency contrast
    paths: list                             # the 4340 demonstrator ladder (PathOutcome)


def _start_curve(reaction, ceiling: float, temps: np.ndarray, X: float = START_X) -> np.ndarray:
    """The reaction's TTT start line ``t(T) = S(X)/K(T)`` (s), ``nan`` at/above its ceiling.

    For a site-saturation reaction ``dU/dt = K(T)·g(U)`` the isothermal time to fraction ``X`` is
    ``S(X)/K(T)`` (separable) — the same identity :mod:`austemper`/:meth:`BainiteReaction.nose` use.
    """
    if reaction is None:
        return np.full_like(temps, np.nan)
    S = _kv_shape_integral(X)
    out = np.full_like(temps, np.nan)
    for i, T in enumerate(temps):
        K = reaction.rate(float(T))
        if T < ceiling and K > 0.0:
            out[i] = S / K
    return out


def _react_nose(reaction, ceiling: float, X: float = START_X, T_low: float = 100.0,
                n_scan: int = 4000) -> tuple:
    """The reaction's nose ``(T °C, t s)`` — the fastest start time over ``(T_low, ceiling)``."""
    temps = np.linspace(T_low, ceiling - 1.0, n_scan)
    rates = np.array([reaction.rate(float(T)) for T in temps])
    i = int(np.argmax(rates))
    K_max = float(rates[i])
    t = np.inf if K_max <= 0.0 else _kv_shape_integral(X) / K_max
    return float(temps[i]), t


def _steel_view(steel: str) -> SteelView:
    """Build the three-C-curve view for a named atlas steel (``"1080"`` / ``"4340"``)."""
    sysm = ukv.unified_system(steel)
    fr, pr, br = sysm.ferrite, sysm.pearlite, sysm.bainite
    has_ferrite = sysm.f_pro > 0.0
    temps = np.linspace(sysm.Ms + 2.0, sysm.Ae3 - 2.0, 500)
    return SteelView(
        steel=steel,
        temps=temps,
        ferrite_tau=_start_curve(fr if has_ferrite else None, sysm.Ae3, temps),
        pearlite_tau=_start_curve(pr, pr.Ae1, temps),
        bainite_tau=_start_curve(br, br.Bs, temps),
        Ae3=sysm.Ae3, Ae1=pr.Ae1, Bs=sysm.Bs, Ms=sysm.Ms,
        has_ferrite=has_ferrite,
        ferrite_nose=_react_nose(fr, sysm.Ae3) if has_ferrite else None,
        pearlite_nose=_react_nose(pr, pr.Ae1),
        bainite_nose=_react_nose(br, br.Bs),
    )


def compute() -> UnifiedDemo:
    """Build the validated arrays: the 4340 bay, the 1080 no-bay, and the 4340 demonstrator ladder."""
    sys4340 = ukv.unified_system("4340")
    paths = []
    for label, medium, diameter in DEMO_PATHS:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")               # biot — the demo is a 0-D kinetic study
            cp = cooling.cooling_path(medium, T0=850.0, diameter=diameter, warn_biot=False)
        res = ukv.transform_competing(cp.t, cp.T, sys4340)
        paths.append(PathOutcome(
            label=label, t=cp.t, T=cp.T,
            fractions=res.fractions(), dominant=res.dominant(), Vr=cp.cooling_rate(),
        ))
    return UnifiedDemo(bay=_steel_view("4340"), nobay=_steel_view("1080"), paths=paths)


def print_summary(d: UnifiedDemo) -> None:
    """Print the bay separation, the 4340 ladder, and the two-model honesty."""
    b = d.bay
    print("\n§19 — the bainite bay, opened in continuous cooling (the 6b deepening)\n")
    print("4340: the three competing C-curve noses (cited Li/KV, per-steel-anchored time base):")
    print(f"  ferrite  nose  {b.ferrite_nose[0]:5.0f} °C / {b.ferrite_nose[1]:10.4g} s   (FC, ΔT³, ceiling Ae3 = {b.Ae3:.0f})")
    print(f"  pearlite nose  {b.pearlite_nose[0]:5.0f} °C / {b.pearlite_nose[1]:10.4g} s   (PC, ΔT³, ceiling Ae1 = {b.Ae1:.0f})")
    print(f"  bainite  nose  {b.bainite_nose[0]:5.0f} °C / {b.bainite_nose[1]:10.4g} s   (BC, ΔT¹, ceiling Bs = {b.Bs:.0f})")
    sep = b.pearlite_nose[1] / b.bainite_nose[1]
    print(f"  → pearlite nose sits ×{sep:.0f} later than bainite's: THE BAY (cited PC≫BC differential).\n")
    print("the 4340 ladder — one steel, three cooling rates, three microstructures:")
    for p in d.paths:
        frac = " ".join(f"{k.replace('_',' ')[:8]}={v:.2f}" for k, v in p.fractions.items())
        print(f"  {p.label:13s} (Vr={p.Vr:7.2f} K/s) → {p.dominant.upper():11s}  {frac}")
    nb = d.nobay
    print(f"\n1080 (consistency): no proeutectoid ferrite ({'has' if nb.has_ferrite else 'no'} ferrite reaction); "
          f"pearlite nose {nb.pearlite_nose[1]:.2g} s vs bainite {nb.bainite_nose[1]:.2g} s")
    print("  → the two noses nearly coincide: NO bay (a merged C-curve, the four-curves ladder).\n")
    print("the two-model honesty:")
    print("  • the single-curve pipeline (pathint) stays the VALIDATED workhorse — any composition,")
    print("    carries the four-curves + 1045/4140 Jominy benchmarks (byte-identical, untouched here);")
    print("  • this unified-KV view is a per-steel DEMONSTRATOR (1080/4340 only): it opens the bay from")
    print("    cited differentials, but cannot predict cross-steel bainite (the BC / 8620 wall), bridges")
    print("    the isothermal atlas to CCT by Scheil additivity (no measured-CCT validation), and uses")
    print("    the carbon-only bainite hardness. The mechanism lens, not a replacement.")


def save_figure(d: UnifiedDemo) -> Path:
    """Render and save the §19 artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                                # headless
    from .plots import unified_kv_figure

    fig = unified_kv_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")         # °C, × on legacy codepages

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
