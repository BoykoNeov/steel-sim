"""Solidification & casting defects: the latent-heat thermal field, validated against Stefan (F4 Slice 2).

*A section freezing against a chill — the iconic solidification map, the latent-heat arrest, and where the
casting's defects concentrate.* The demonstrable artifact for **F4 Slice 2** (``docs/plans/steel-making.md``
§7): the part Slice 1 (:mod:`steel.casting`) deferred. Slice 1 needed no solver (Scheil + Chvorinov are
closed forms); this reuses the **sealed 1-D heat engine** (no engine touch, no ADR) to solve the latent-heat
temperature field of a chill-cooled section and read two defect criteria off it.

What it shows (four panels)
---------------------------
1. **The solidification map.** Temperature ``T(x, t)`` of a 4140 section freezing against a fixed chill, with
   the solidus front sweeping from the chill toward the insulated thermal centre — the iconic picture.
2. **The latent-heat arrest.** The centre's temperature history with latent heat on vs off: freezing
   *stalls* the cool-down in the mushy range (the recalescence plateau), emergent from the enthalpy method
   — a directional sanity check (~order ``L/c_pΔT``; shape-dependent, not a precise tooth).
3. **The Stefan benchmark — the headline tooth.** The numerical freezing front vs the analytic one-phase
   Stefan/Neumann closed form ``X(t) = 2λ√(αt)``: an untuned, cited benchmark the solver **converges to**
   under grid refinement (a broken latent-heat coupling misses by tens of percent). Conservation is exact.
4. **Where the defects are (by construction).** Local solidification time: the insulated centre freezes
   *last* — the shrinkage hot spot, and the *same* centre Slice 1 showed is alloy-enriched (segregation and
   porosity concentrate in one place, two independent reasons). The cited **Niyama** ``Ny = G/√Ṫ`` criterion
   collapses toward that centre (``G → 0``); illustrative, named by-construction, not a tooth.

Posture (carried from :mod:`solidification`): the enthalpy method (state = specific enthalpy) makes latent
heat ride the engine's nonlinear ``D(u)`` path with exact conservation; smoothing the solid fraction is a
**numerical regularization** (the Stefan front is insensitive to its shape, which is why it does not game the
tooth); the BC is a **fixed-temperature chill** (convective cooling is the named scope edge). Niyama/hot-tear
are illustrative — the headline tooth is the Stefan match.

Run headless (prints the Stefan match, conservation, the latent arrest, and the hot-spot):

    python -m steel.demo_solidification
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import solidification as sol
from .solidification import FreezingPath
from .sweep import STEELS

# The hero grade (continuity with the casting Slice-1 demo) and the chill section it solidifies.
GRADE = "4140"
HALF_THICKNESS = 0.05              # 50 mm half-section (chill at 0, insulated thermal centre at 50 mm)
CHILL_T = 100.0                    # fixed chill / water-cooled mold surface temperature (°C)
FREEZING_RANGE_C = sol.DEFAULT_FREEZING_RANGE_C

# Resolution / window for the solidification field (map + defects); the centre fully freezes well within
# FIELD_TEND, so there is no need to march to the full conduction time — modest, in the resolved regime.
N_CELLS = 140
N_T = 2600
FIELD_TEND = 320.0

# Stefan-benchmark grids — the convergence pair (the headline tooth: ratio climbs toward 1 as Δx halves).
# Kept in the Picard-robust regime (Δx ≲ 1.3 mm, dt ≲ 0.25 s — the cold chill makes the enthalpy gradient
# steep, so the regularized capacity spike needs resolution there). Domain > the front reach so the far
# boundary stays a semi-infinite proxy.
STEFAN_DOMAIN = 0.18
STEFAN_CHILL_T = 25.0
STEFAN_GRIDS = ((144, 2000), (216, 3500))
STEFAN_TEND = 500.0

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-solidification.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-solidification.png"


@dataclass(frozen=True)
class SolidificationDemo:
    """What the demo produced — the field, the latent arrest, the Stefan validation, and the defect reads."""

    path: FreezingPath
    field: sol.SolidificationField
    # panel 1 — the map (front line over the field)
    solidus_front: np.ndarray
    # panel 2 — the latent arrest at the centre (L on vs off)
    centre_t: np.ndarray
    centre_T_on: np.ndarray
    centre_T_off: np.ndarray
    centre_freeze_on: float
    centre_freeze_off: float
    # panel 3 — the Stefan benchmark (the tooth), at two resolutions
    stefan: tuple[sol.StefanValidation, ...]
    conservation_resid: float
    # panel 4 — defect localization (by construction)
    x: np.ndarray
    solidification_time: np.ndarray
    niyama_x: np.ndarray
    niyama: np.ndarray


def _centre_freeze_time(field: sol.SolidificationField) -> float:
    """The solidus-crossing time of the insulated thermal centre (the last-to-freeze location), s."""
    _, tsol = sol.local_solidification_time(field)
    finite = tsol[np.isfinite(tsol)]
    return float(finite[-1]) if finite.size else float("nan")


def compute() -> SolidificationDemo:
    """Solve the chill-slab field, the latent toggle, the Stefan benchmark, and the defect reads."""
    steel = STEELS[GRADE]
    path = sol.freezing_path_for(steel, freezing_range_C=FREEZING_RANGE_C)

    field = sol.solidify_chill_slab(path, half_thickness=HALF_THICKNESS, chill_T=CHILL_T,
                                    n_cells=N_CELLS, n_t=N_T, t_end=FIELD_TEND)
    conservation_resid = abs(field.enthalpy_drift - field.boundary_flux) / max(abs(field.boundary_flux), 1e-30)

    # latent ON/OFF toggle at the centre (the ON case reuses the field above; OFF sets L = 0, same sensible props)
    path_off = FreezingPath(T_sol=path.T_sol, T_liq=path.T_liq, L=0.0)
    field_off = sol.solidify_chill_slab(path_off, half_thickness=HALF_THICKNESS, chill_T=CHILL_T,
                                        n_cells=N_CELLS, n_t=N_T, t_end=FIELD_TEND)
    centre_t, centre_T_on, freeze_on = field.t, field.T[:, -1], _centre_freeze_time(field)
    centre_T_off, freeze_off = field_off.T[:, -1], _centre_freeze_time(field_off)

    # the Stefan benchmark at two resolutions (the tooth: converges toward 1 under refinement)
    stefan = tuple(
        sol.one_phase_stefan_validation(path, chill_T=STEFAN_CHILL_T, domain=STEFAN_DOMAIN,
                                        n_cells=nc, n_t=nt, t_end=STEFAN_TEND, n_samples=6)
        for nc, nt in STEFAN_GRIDS
    )

    # defect localization (by construction)
    x, t_sol = sol.local_solidification_time(field)
    nx, ny = sol.niyama_field(field)

    return SolidificationDemo(
        path=path, field=field, solidus_front=field.solidus_front,
        centre_t=centre_t, centre_T_on=centre_T_on, centre_T_off=centre_T_off,
        centre_freeze_on=freeze_on, centre_freeze_off=freeze_off,
        stefan=stefan, conservation_resid=conservation_resid,
        x=x, solidification_time=t_sol, niyama_x=nx, niyama=ny,
    )


def print_summary(demo: SolidificationDemo) -> None:
    """Print the Stefan match, conservation, the latent arrest, and the last-to-freeze hot spot."""
    p = demo.path
    print(f"\nF4 Slice 2 — a {GRADE} section solidifying against a chill (latent-heat thermal field)\n")
    print(f"Freezing range: liquidus {p.T_liq:.0f} °C → solidus {p.T_sol:.0f} °C  (α = {p.alpha:.2e} m²/s); "
          f"chill held at {CHILL_T:.0f} °C, {HALF_THICKNESS*1e3:.0f} mm to the insulated centre.")

    print("\nStefan benchmark — numerical front vs analytic 2λ√(αt) (the headline tooth):")
    for v in demo.stefan:
        print(f"    n = {v.n_cells:4d} cells:  mean front ratio = {v.ratio.mean():.4f}  "
              f"(St = {v.St:.2f}, λ = {v.lam:.4f})")
    better = abs(demo.stefan[-1].ratio.mean() - 1) < abs(demo.stefan[0].ratio.mean() - 1)
    print(f"    → converges toward 1 as the grid refines: {better}.  "
          f"Enthalpy conservation residual = {demo.conservation_resid:.1e} (machine precision).")

    print(f"\nLatent-heat arrest at the centre (the recalescence plateau):")
    print(f"    freeze-through time   latent ON = {demo.centre_freeze_on:.0f} s   "
          f"OFF = {demo.centre_freeze_off:.0f} s   (×{demo.centre_freeze_on/demo.centre_freeze_off:.1f} — "
          "latent heat stalls the cool-down).")

    finite = demo.solidification_time[np.isfinite(demo.solidification_time)]
    print(f"\nWhere the defects concentrate (by construction):")
    print(f"    the insulated centre freezes LAST ({finite[-1]:.0f} s) — the shrinkage hot spot, and the "
          "same centerline Slice 1 showed is alloy-enriched. Niyama collapses there (G → 0): porosity-prone.")
    print("\n→ Stefan match = the validated tooth; the latent arrest is directional; Niyama/hot-spot are "
          "illustrative (by-construction). No engine touch, no ADR — the sealed heat engine as a library.")


def save_figure(demo: SolidificationDemo) -> Path:
    """Render and bank the solidification artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import solidification_figure

    fig = solidification_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, × on legacy codepages

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
