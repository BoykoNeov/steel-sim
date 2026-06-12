"""The F4 anchor demo: cast a billet, and an upstream *segregation* propagates front-to-back.

*Composition in, a non-uniform section out.* This is the demonstrable artifact for **F4 Slice 1**
(``docs/plans/steel-making.md`` §7) and the moment the production chain **closes front-to-back inside
steel-sim**: a real front-end engine (:mod:`steel.casting`) produces the :class:`~steel.heat_state.Heat`
the already-validated back end consumes, and it produces it *non-uniformly*.

What it shows
-------------
1. **Scheil microsegregation + Chvorinov (the casting physics).** Freezing a 4140 casting rejects solute
   into the last liquid → the centerline is alloy-enriched. The Scheil profile shows the **severity
   ordering** (S, P, C the worst; Cr, Ni mild — *why* sulphur and phosphorus are the dangerous
   segregators), and Chvorinov gives the solidification time ``t = B·M²`` from the section modulus.

2. **The front-to-back proof (the headline).** The casting emits two real casting-produced Heats — the
   nominal section and the Scheil centerline — and **both** take the *same* oil quench through
   :func:`~steel.heat_state.heat_treat`. The enriched centerline is markedly **more hardenable**, so the
   *same* casting comes out **non-uniform**: here the bulk under-hardens (soft core) while the centerline
   over-hardens into a hard, crack-prone **band** ~90 HV harder — the §6 "centerline segregation → uneven
   hardenability" link, emergent from cited physics, end to end. The Heats carry a real **"cast"** origin
   on their trail (replacing :meth:`~steel.heat_state.Heat.from_grade`'s back-end stand-in).

The posture (carried from :mod:`casting`): Scheil is the **no-back-diffusion upper bound** (carbon, being
interstitial, is the worst over-prediction → the handoff leans on the substitutional alloys); the
δ/γ peritectic and the latent-heat solidification *map* are named/deferred (Slice 2). Tests are seam +
conservation correctness, plus the cited segregation ordering — not a new through-process benchmark.

Run headless (prints the casting + the front-to-back divergence):

    python -m steel.demo_casting
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import casting as cast
from . import heat_state as hs
from .heat_state import Heat
from .sweep import STEELS, evaluate

# The hero grade (continuity with the heat_state spine demo) and the section it's cast / treated at.
GRADE = "4140"
CAST_MODULUS = 0.025               # 25 mm casting modulus V/A — the section that froze
TREAT_MEDIUM = "oil"
TREAT_DIAMETER = 0.050             # the discriminating section: nominal under-hardens, centerline over-

# The solutes whose Scheil severity the profile panel draws (composition-independent ratio C_s/C₀).
PROFILE_SOLUTES = ("S", "P", "C", "Mo", "Mn", "Si", "Cr", "Ni")
FS_PROFILE_MAX = 0.97              # draw up to just below the f_s → 1 Scheil singularity

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-casting.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-casting.png"


@dataclass(frozen=True)
class CastingDemo:
    """What the demo produced — the cast section, the treated heats, and the figure arrays.

    ``section`` the :class:`~steel.casting.CastSection`; ``nominal_treated`` / ``centerline_treated`` the two
    Heats *after* :func:`~steel.heat_state.heat_treat` (the proof: the centerline diverges). The scalars
    (``nominal_HV`` / ``centerline_HV``, ``nominal_fM`` / ``centerline_fM``, the ``spec`` line) are the same
    back-end numbers the flags were set from. ``fs`` + ``liquid_ratio`` (per solute) draw the segregation
    profile — the **interdendritic liquid** enrichment ``C_L/C₀`` (rises steepest for the smallest ``k``: S,
    C, P — the dangerous segregators; the centerline *solid* inherits ``k×`` this). ``modulus_grid`` +
    ``time_grid`` the Chvorinov ``t ∝ M²`` curve.
    """

    section: cast.CastSection
    nominal_treated: Heat
    centerline_treated: Heat
    nominal_HV: float
    centerline_HV: float
    nominal_fM: float
    centerline_fM: float
    spec: float
    fs: np.ndarray
    liquid_ratio: dict[str, np.ndarray]
    modulus_grid: np.ndarray
    time_grid: np.ndarray


def compute() -> CastingDemo:
    """Cast the billet, heat-treat both heats, and assemble the figure arrays — the front-to-back check."""
    steel = STEELS[GRADE]
    section = cast.cast_billet(steel, modulus=CAST_MODULUS)

    nominal_treated = hs.heat_treat(section.nominal_heat, medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)
    centerline_treated = hs.heat_treat(section.centerline_heat, medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)

    # The same back-end evaluation, captured for the figure bars (identical constants ⇒ matches the flags).
    nom_o = evaluate(section.nominal_heat.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)
    ctr_o = evaluate(section.centerline_heat.as_steel(), medium=TREAT_MEDIUM, diameter=TREAT_DIAMETER)

    fs = np.linspace(0.0, FS_PROFILE_MAX, 240)
    # Interdendritic LIQUID enrichment C_L/C₀ = (1−f_s)^(k−1): the clean severity ordering (smallest k —
    # S, C, P — climbs steepest), and the last liquid the centerline solid inherits at k× its value.
    liquid_ratio = {el: np.array([cast.scheil_liquid_composition(1.0, cast.partition_coefficient(el, section.phase), f)
                                  for f in fs])
                    for el in PROFILE_SOLUTES}

    modulus_grid = np.linspace(0.005, 0.060, 120)         # 5–60 mm sections
    time_grid = np.array([cast.chvorinov_time(m) for m in modulus_grid])

    return CastingDemo(
        section=section, nominal_treated=nominal_treated, centerline_treated=centerline_treated,
        nominal_HV=nom_o.HV, centerline_HV=ctr_o.HV,
        nominal_fM=nom_o.result.martensite, centerline_fM=ctr_o.result.martensite,
        spec=hs.MIN_MARTENSITE_SPEC, fs=fs, liquid_ratio=liquid_ratio,
        modulus_grid=modulus_grid, time_grid=time_grid,
    )


def print_summary(demo: CastingDemo) -> None:
    """Print the casting, the segregation it produced, and the front-to-back hardness divergence."""
    s = demo.section
    print(f"\nF4 — cast a {GRADE} billet, and segregation propagates front-to-back\n")
    print(f"Casting: modulus M = {s.modulus * 1000:.0f} mm, liquidus {s.liquidus:.0f} °C, "
          f"Chvorinov solidification time t = B·M² ≈ {s.solidification_time:.0f} s "
          f"({s.solidification_time / 60:.1f} min).")

    ctr = s.centerline_heat.composition
    nom = s.steel
    print(f"\nScheil centerline enrichment (f_s* = {s.fs_centerline:.2f}, primary {s.phase}-ferrite), "
          f"the substitutional alloys:")
    for el in ("Mn", "Si", "Cr", "Mo"):
        n_, c_ = getattr(nom, el), getattr(ctr, el)
        if n_ > 0:
            print(f"    {el}: {n_:.2f} → {c_:.2f} wt%  (×{c_ / n_:.2f})")
    print("    C: left at nominal — Scheil over-predicts interstitial carbon (named ceiling).")

    print(f"\nSame {TREAT_MEDIUM} quench, Ø{TREAT_DIAMETER * 1000:.0f} mm section — composition decides:")
    print(f"    nominal section:      {demo.nominal_fM:.0%} martensite, {demo.nominal_HV:.0f} HV"
          f"  {'(soft core)' if demo.nominal_treated.has_defect(hs.SOFT_CORE) else ''}")
    print(f"    segregated centerline: {demo.centerline_fM:.0%} martensite, {demo.centerline_HV:.0f} HV"
          f"  {'(soft core)' if demo.centerline_treated.has_defect(hs.SOFT_CORE) else ''}")
    dHV = demo.centerline_HV - demo.nominal_HV
    print(f"\n→ The centerline is a {dHV:+.0f} HV harder BAND than the bulk — the same casting is "
          f"non-uniform (uneven hardenability), straight from Scheil segregation feeding the back end. "
          f"A real front-end origin ('cast') → a real back-end divergence: the chain runs front-to-back.")


def save_figure(demo: CastingDemo) -> Path:
    """Render and bank the cast-section artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import casting_figure

    fig = casting_figure(demo)
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
