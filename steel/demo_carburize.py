"""The Phase-3c anchor demo: a carburized gear tooth — carbon in, case hardness out.

*One solver, both faces of the spine.* The frozen :mod:`engines.diffusion` that cooled the
Jominy bar in **heat mode** (Phase 2) now runs in **mass mode** to diffuse carbon into the
surface of a low-carbon gear (≈ AISI 8620, 0.2 %C core), held at 925 °C in a 0.8 %C-potential
atmosphere. The erfc carbon profile feeds the *same* transformation + property model the rest
of the steel project built → a **case-hardened gradient**: a hard (~65 HRC) martensite case
over a tough, softer (~48 HRC) core, the hardness set by the **carbon** gradient (not a
cooling-rate gradient — one quench is applied throughout; see :mod:`carburize`).

This is the banked Phase-3c artifact and the integration test of the mass-mode chain:
``carburize.solve_carburize`` (the erfc profile from the frozen engine) → ``carburize.carburized_traverse``
(per-depth ``ccurve_for_steel`` → ``pathint`` → ``properties``) → ``plots``.

Honest framing (and why two hardness curves). Running the full kinetics to room temperature at
the high-carbon surface predicts substantial **retained austenite** (the surface ``Ms`` is low) —
real heavy-case physics, but it drags a rule-of-mixtures hardness below the 62–65 HRC a hardened
case shows, *and* it is where Andrews ``Ms`` / KM are pushed past their ~0.8 %C anchor. So the
**surface-hardness benchmark** is read off the martensite **potential** (the case as designed —
what a published surface spec represents), while the retained austenite is shown as the
microstructure gradient and an honest as-quenched curve, not asserted against the published band.

Published comparison points (reference facts, not redistributed data): a 925 °C / ~8 h gas-carburize
of an 8620-grade steel gives an effective case depth of order ~1 mm (50-HRC definition) and a
surface hardness ~60–64 HRC after quench (ASM Handbook Vol. 4 *Heat Treating*; Krauss, *Steels*).

Run headless (saves the figure, prints the table):

    python -m steel.demo_carburize
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import carburize as cb

# The carburizing cycle and steel (an 8620-grade case-hardening steel).
T_CARBURIZE = cb.DEFAULT_T_CARBURIZE       # 925 °C
CARBON_POTENTIAL = cb.DEFAULT_CARBON_POTENTIAL   # 0.8 %C atmosphere
CORE_CARBON = cb.DEFAULT_CORE_CARBON       # 0.2 %C core
T_HOURS = 8.0
QUENCH = "oil"                             # standard case-hardening quench

# Published surface-hardness band for a quenched carburized case (reference facts — ASM
# Heat Treating; Krauss). Drawn as a comparison band, not a test assertion.
PUBLISHED_SURFACE_HRC = (62.0, 65.0)

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-carburize-gradient.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-carburize-gradient.png"


def compute(t_hours: float = T_HOURS):
    """Run the whole Phase-3c mass-mode pipeline; return ``(profile, traverse)``."""
    profile = cb.solve_carburize(
        C_surface=CARBON_POTENTIAL, C_core=CORE_CARBON,
        T_carburize=T_CARBURIZE, t_hours=t_hours,
    )
    traverse = cb.carburized_traverse(profile, medium=QUENCH)
    return profile, traverse


def print_summary(profile, traverse) -> None:
    """Print the carbon → microstructure → hardness traverse — the demo's payoff in text."""
    ecd_c = profile.case_depth(0.4) * 1000.0
    ecd_h = traverse.case_depth_50HRC() * 1000.0
    print(f"\nCarburized {T_CARBURIZE:.0f} °C, {T_HOURS:.0f} h, {CARBON_POTENTIAL:.1f} %C potential, "
          f"{QUENCH} quench  (D = {profile.D:.2e} m²/s)\n")
    print(f"  effective case depth: {ecd_c:.2f} mm to 0.4 %C   |   {ecd_h:.2f} mm to 50 HRC")
    print(f"  carbon mass conserved: Δ∫C dx = {profile.mass_uptake:.4e}, "
          f"surface-flux integral = {profile.surface_flux_uptake:.4e} "
          f"(resid {abs(profile.mass_uptake - profile.surface_flux_uptake):.1e})\n")
    hdr = f"{'depth':>7} {'C':>6} {'fM':>5} {'ret.γ':>6} {'HVpot':>6} {'HRC':>5} {'HVaq':>6}"
    print(hdr)
    print(f"{'(mm)':>7} {'(%)':>6}")
    print("-" * len(hdr))
    depth = traverse.depth
    # Sample ~12 points from the surface through the active case into the core.
    idx = np.linspace(0, depth.size - 1, 12).astype(int)
    for i in idx:
        hrc = traverse.HRC[i]
        hrcs = f"{hrc:5.1f}" if np.isfinite(hrc) else "  — "
        print(f"{depth[i] * 1000:7.2f} {traverse.C[i]:6.3f} {traverse.martensite[i]:5.2f} "
              f"{traverse.retained_austenite[i]:6.2f} {traverse.HV[i]:6.0f} {hrcs:>5s} "
              f"{traverse.HV_as_quenched[i]:6.0f}")
    print(f"\nSurface (potential): {traverse.HRC[0]:.1f} HRC  — hard martensite case, the design intent.")
    print(f"Core: {traverse.HRC[-1]:.1f} HRC — softer & tougher. The {traverse.retained_austenite[0]*100:.0f} % "
          f"retained austenite at the surface (HVpot {traverse.HV[0]:.0f} vs as-quenched "
          f"{traverse.HV_as_quenched[0]:.0f}) is the real heavy-case effect — reported, not asserted.")


def print_dofC_comparison(t_hours: float = T_HOURS) -> None:
    """Contrast the constant-``D`` erfc case with the concentration-dependent Tibbetts ``D(C)``.

    The constant-``D`` erfc is the validated *analytical limit* but under-predicts the absolute
    case depth (real carbon diffusivity rises with carbon content — Tibbetts 1980). The opt-in
    ``D(C)``, solved by the (unfrozen) engine's **native nonlinear** path (CONTRACT.md / ADR
    0004), deepens the case toward the published ~1 mm rule of thumb — the named scope edge
    turned into a cited, validated result.
    """
    const = cb.solve_carburize(C_surface=CARBON_POTENTIAL, C_core=CORE_CARBON,
                               T_carburize=T_CARBURIZE, t_hours=t_hours)
    dc = cb.solve_carburize(C_surface=CARBON_POTENTIAL, C_core=CORE_CARBON,
                            T_carburize=T_CARBURIZE, t_hours=t_hours,
                            D_of_C=cb.carbon_diffusivity_tibbetts)
    ecd_c = const.case_depth(0.4) * 1000.0
    ecd_d = dc.case_depth(0.4) * 1000.0
    resid = abs(dc.mass_uptake - dc.surface_flux_uptake)
    print("\nConstant-D (erfc)  vs  concentration-dependent D(C) (Tibbetts 1980, native engine D(u))")
    print(f"  effective case depth (0.4 %C):  constant-D {ecd_c:.2f} mm  →  D(C) {ecd_d:.2f} mm "
          f"(+{(ecd_d / ecd_c - 1) * 100:.0f} %, toward the published ~1 mm)")
    print(f"  carbon conserved on the D(C) path:  |Δ∫C dx − Σ dt·flux| = {resid:.1e} "
          f"(the engine's cached-field identity — machine-exact)")
    print("  D(C) profile validated against the Boltzmann self-similar reference (not erfc); "
          "the √(t) case-depth scaling survives.")


def print_case_depth_inversion(target_case_mm: float = 0.5) -> None:
    """The v2 case-depth INVERSION — *target a case depth, get a schedule* — and its exact round trip.

    The forward demo above gives a case depth from a (time, temperature) cycle; this inverts it
    closed-form (no root-find): solve the **time** at the standard 925 °C, and the **temperature**
    at the standard 8 h. Re-running :func:`~steel.carburize.analytic_case_depth` on each recovers the
    target to machine precision — the strongest harness check the project has.
    """
    x = target_case_mm / 1000.0
    t_at_T = cb.carburize_time_for_case_depth(x, T_celsius=T_CARBURIZE)
    T_at_t = cb.carburize_temperature_for_case_depth(x, T_HOURS * 3600.0)
    # Round-trip both back through the forward case depth.
    x_from_t = cb.analytic_case_depth(t_at_T, cb.carbon_diffusivity(T_CARBURIZE),
                                      CARBON_POTENTIAL, CORE_CARBON) * 1000.0
    x_from_T = cb.analytic_case_depth(T_HOURS * 3600.0, cb.carbon_diffusivity(T_at_t),
                                      CARBON_POTENTIAL, CORE_CARBON) * 1000.0
    print(f"\nCase-depth inversion (v2) — target {target_case_mm:.2f} mm effective case (0.4 %C)")
    print(f"  solve time @ {T_CARBURIZE:.0f} °C:   {t_at_T / 3600.0:6.2f} h   "
          f"(forward re-eval → {x_from_t:.4f} mm)")
    print(f"  solve temperature @ {T_HOURS:.0f} h:  {T_at_t:6.1f} °C  "
          f"(forward re-eval → {x_from_T:.4f} mm)")
    practical = "in the practical 815–1050 °C window" if 815.0 <= T_at_t <= 1050.0 else \
                "OUTSIDE the practical 815–1050 °C window — not achievable in this time by a sane cycle"
    print(f"  closed-form inverse of x = 2·erfc⁻¹(r)·√(Dt) — recovers the target exactly; "
          f"the temperature is {practical}.")


def save_figure(profile, traverse) -> Path:
    """Render and save the carburized-gradient artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import carburize_figure

    fig = carburize_figure(profile, traverse, surface_hardness_band=PUBLISHED_SURFACE_HRC)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, γ, subscripts on legacy codepages

    profile, traverse = compute()
    print_summary(profile, traverse)
    print_dofC_comparison()
    print_case_depth_inversion()                      # the v2 case-depth inversion + round trip
    try:
        saved = save_figure(profile, traverse)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
