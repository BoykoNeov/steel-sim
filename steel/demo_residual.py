"""The Phase-6f demo: residual stress & distortion on quench — the solid-mechanics axis (§11 Option-#2).

*Steel + section + quench in, the residual-stress profile out — and the quench-crack verdict that
follows.* This is the first piece to model **solid mechanics**: it marches the elastic–perfectly-plastic
mechanics of a planar plate on the frozen heat engine (:mod:`residual`), driven by two eigenstrains that
vary through the section — thermal contraction and the austenite→martensite **dilatation** — and reads
the stress locked in once the part has cooled to room temperature.

The headline figure (``plots.residual_stress_figure``) banks the *same* 4340 plate solved three ways:

* **thermal only (transformation OFF)** — the surface ends in **compression** (the hot core yields,
  then pulls the surface in as it equalises): benign, even beneficial;
* **with transformation (ON)** — the martensite dilatation **flips the surface to tension** (the surface
  transforms and hardens first, then the late-expanding core stretches it): the quench-crack-prone state;
* **martemper** — the near-uniform slow cool through ``Mₛ`` **removes** that surface tension: the
  stress-quantitative statement of §17's distortion proxy.

The text summary adds the falsifiable content: the surface-sign reversal (the headline tooth), the
self-equilibrium of the profile (``∫σ dx = 0``), the yield-order magnitude, and the direct-vs-martemper
surface-tension collapse.

Run headless (saves the figure, prints the summary):

    python -m steel.demo_residual
"""
from __future__ import annotations

from pathlib import Path

from . import cooling
from . import residual as res

AUSTENITIZE_T = 850.0            # °C — fully austenitic before the quench

# The headline case: 4340 (the deep-hardening, quench-crack-prone alloy) in a 50 mm plate
# (0.025 m half-thickness). Biot ≈ 1.25 under a still-water quench — severe enough that the hot core
# yields, which is what a thermal residual *requires* (a mild quench deforms nothing and leaves none).
DEMO_STEEL = "4340"
DEMO_HALF_THICKNESS = 0.025      # m  → a 50 mm plate
DEMO_H_QUENCH = cooling.H_WATER

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-residual-stress.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-residual-stress.png"


def compute(
    steel: str = DEMO_STEEL,
    half_thickness: float = DEMO_HALF_THICKNESS,
    h_quench: float = DEMO_H_QUENCH,
    n_t: int = 4000,
):
    """Run the three solves feeding the figure: direct ON, direct OFF (thermal-only), martemper.

    ``n_t = 4000`` (the slab solver's own default) is plenty for a clean figure and the teeth — the
    profile is resolution-robust (``test_residual.test_teeth_are_resolution_robust``); the library
    default is finer for standalone accuracy.
    """
    on = res.quench_residual_stress(
        steel, half_thickness, route="direct", transform=True,
        T0=AUSTENITIZE_T, h_quench=h_quench, n_t=n_t,
    )
    off = res.quench_residual_stress(
        steel, half_thickness, route="direct", transform=False,
        T0=AUSTENITIZE_T, h_quench=h_quench, n_t=n_t,
    )
    marte = res.quench_residual_stress(
        steel, half_thickness, route="martemper", transform=True,
        T0=AUSTENITIZE_T, h_quench=h_quench, n_t=n_t,
    )
    return on, off, marte


def print_summary(on, off, marte) -> None:
    """Print the sign reversal, the self-equilibrium, the magnitude, and the martemper benefit."""
    plate_mm = 2_000.0 * on.half_thickness
    print(f"\nResidual stress on quench — {on.steel}, {plate_mm:.0f} mm plate, "
          f"austenitized {AUSTENITIZE_T:.0f} °C, still-water quench (Mₛ = {on.Ms:.0f} °C)\n")

    # 1. The sign reversal — the headline tooth.
    print("Surface-sign reversal (the same steel & quench, transformation OFF vs ON):")
    print(f"  thermal only (OFF) : surface {off.surface_MPa:+7.1f} MPa   "
          f"→ {'compression — benign' if off.surface_stress < 0 else 'tension'}")
    print(f"  transformation (ON): surface {on.surface_MPa:+7.1f} MPa   "
          f"→ {'TENSION — quench-crack-prone' if on.surface_stress > 0 else 'compression'}")
    print(f"  the martensite dilatation ({100 * res.transformation_dilatation(0.42):.2f}% linear) "
          f"flips the surface from compression to tension.")

    # 2. Self-equilibrium + magnitude — conservation and order.
    print("\nProfile checks:")
    print(f"  self-equilibrium  : ∫σ dx ∝ mean = {on.mean_stress:.2e} Pa  (≈ 0, machine precision)")
    print(f"  peak |σ|          : {max(abs(on.peak_tension), abs(on.peak_compression)) / 1e6:.0f} MPa "
          f"(of order the {res.SIGMA_Y_REF_20C / 1e6:.0f} MPa yield base — a quench reaches yield-level "
          f"residuals)")
    print(f"  core (centreline) : {on.center_MPa:+7.1f} MPa  (compression — it balances the surface "
          f"tension)")

    # 3. The §17 tie-in, now in stress.
    print("\nMartempering — the distortion benefit, now quantitative in stress:")
    print(f"  direct quench  : surface {on.surface_MPa:+7.1f} MPa  (tension)")
    print(f"  martemper      : surface {marte.surface_MPa:+7.1f} MPa  "
          f"→ surface tension essentially removed (≈ 0 in this idealised model)")
    print("\nThe martemper figure is idealised (a thermally-thin, near-uniform slow cool, and no\n"
          "transformation plasticity) — a best case; real martempering retains a finite residual.")

    # 4. The named ceilings.
    print("\nNamed scope edges: no transformation plasticity (TRIP — the #1 deferred refinement);\n"
          "through-hardening (martensitic) only; one-way thermo-mechanical coupling; a single,\n"
          "non-phase-split yield; and an absolute magnitude that scales with the representative\n"
          "yield base (the teeth are the signs / equilibrium / route ratio, not the MPa).")


def save_figure(on, off, marte) -> Path:
    """Render and save the residual-stress artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import residual_stress_figure

    fig = residual_stress_figure(on, off, marte)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, subscripts, σ on legacy codepages

    on, off, marte = compute()
    print_summary(on, off, marte)
    try:
        saved = save_figure(on, off, marte)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
