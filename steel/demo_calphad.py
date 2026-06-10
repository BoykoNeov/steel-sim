"""The Phase-4 anchor demo: real thermodynamics vs the parametrised Fe-C diagram.

Phase 1b drew the Fe-C diagram as straight chords between pinned invariant points;
Phase 4 lets the boundaries *emerge* from a Gibbs-energy minimisation (pycalphad) and
**extends to multicomponent low-alloy steels**. This demo banks the two-panel artifact
(``docs/figures/steel-calphad.png``):

  * **Left** — the hypoeutectoid A₃ transus: ``fe_c``'s linear chord vs the CALPHAD
    curve, with their gap shaded. *What the parametrised version got wrong* — the chord
    over-predicts A₃ by tens of °C at mid-carbon.
  * **Right** — AISI 4140's equilibrium phase fractions vs temperature, showing the
    ferrite→austenite spread (A₁→A₃) **and a chromium carbide** — none of which ``fe_c``
    can represent. Andrews Ae1/Ae3 markers give the independent cross-check.

Needs the optional CALPHAD backend (see :mod:`calphad_backend`) and the ``viz`` extra.
The left panel uses the Fe-C database bundled with pycalphad; the right panel needs a
multicomponent steel TDB (``$BIGSIM_STEEL_TDB`` / ``data/tdb/`` — see
:func:`calphad_backend.download_mc_fe`) and is omitted if none is present.

Run headless (saves the figure, prints the comparison table):

    python -m steel.demo_calphad
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import calphad_backend as cb
from . import calphad_reference as ref
from . import fe_c

COMPOSITION_4140 = ref.COMPOSITION_4140

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-calphad.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-calphad.png"


def compute_binary(backend, n: int = 25) -> dict:
    """The hypoeutectoid A₃ comparison: ``fe_c`` linear chord vs CALPHAD curve."""
    carbon = np.linspace(0.10, 0.70, n)
    a3_calphad = np.array([backend.austenite_solvus(float(C)) for C in carbon])
    a3_linear = np.array([fe_c.A3(float(C)) for C in carbon])
    return {
        "carbon": carbon,
        "a3_linear": a3_linear,
        "a3_calphad": a3_calphad,
        "eutectoid": (fe_c.A1(), fe_c.C_EUTECTOID),
        "eutectoid_calphad": backend.eutectoid(),
        "gamma_max": (fe_c.T_GAMMA_MAX, fe_c.C_GAMMA_MAX),
        "gamma_max_calphad": backend.gamma_max(),
    }


def compute_alloy(steel_backend, T_range=(680.0, 820.0), n: int = 36) -> dict:
    """4140 equilibrium phase fractions vs temperature (the multicomponent showpiece)."""
    temps = np.linspace(T_range[0], T_range[1], n)
    fractions = {p: np.zeros(n) for p in ("ferrite", "austenite", "cementite", "carbide")}
    for i, T in enumerate(temps):
        point = steel_backend.equilibrium_point(COMPOSITION_4140, float(T))
        for phase, frac in point.mass_fractions.items():
            if phase in fractions:
                fractions[phase][i] = frac
    A1, A3 = steel_backend.alloy_transus(COMPOSITION_4140)
    return {
        "label": "AISI 4140",
        "T": temps,
        "fractions": fractions,
        "A1": A1,
        "A3": A3,
        "andrews": (ref.andrews_Ae1(COMPOSITION_4140), ref.andrews_Ae3(COMPOSITION_4140)),
    }


def compute():
    """Run the Phase-4 pipeline; return ``(binary, alloy_or_None)``."""
    cb._require_pycalphad()
    binary = compute_binary(cb.CalphadBackend())
    steel_path = cb.default_steel_database_path()
    alloy = compute_alloy(cb.CalphadBackend(steel_path)) if steel_path else None
    return binary, alloy


def print_summary(binary: dict, alloy: dict | None) -> None:
    """Print the diagram comparison — the demo's payoff in text."""
    Te, Ce = binary["eutectoid_calphad"]
    Tg, Cg = binary["gamma_max_calphad"]
    print("\nFe-C invariant points — parametrised (fe_c) vs CALPHAD-computed:")
    print(f"  eutectoid:  fe_c 727 °C / 0.76 %C   |   CALPHAD {Te:.1f} °C / {Ce:.3f} %C")
    print(f"  γ-max:      fe_c 1147 °C / 2.11 %C  |   CALPHAD {Tg:.1f} °C / {Cg:.3f} %C")
    print("\nA₃ transus — fe_c's linear chord over-predicts the curved boundary:")
    dev = binary["a3_linear"] - binary["a3_calphad"]
    i = int(np.argmax(dev))
    print(f"  {'C (wt%)':>9} {'fe_c (°C)':>10} {'CALPHAD (°C)':>13} {'chord high by':>14}")
    for C, lin, cal in zip(binary["carbon"][::4], binary["a3_linear"][::4], binary["a3_calphad"][::4]):
        print(f"  {C:9.2f} {lin:10.1f} {cal:13.1f} {lin - cal:+13.1f}")
    print(f"  → worst at {binary['carbon'][i]:.2f} %C: chord {dev[i]:.0f} °C too high "
          "(the parametrisation error this phase quantifies).")

    if alloy is not None:
        Ae1, Ae3 = alloy["andrews"]
        print(f"\n{alloy['label']} (Fe-C-Cr-Mn-Mo-Si) — beyond fe_c entirely:")
        print(f"  CALPHAD A₁ = {alloy['A1']:.1f} °C, A₃ = {alloy['A3']:.1f} °C   "
              f"(Andrews Ae₁/Ae₃ = {Ae1:.0f}/{Ae3:.0f} °C)")
        peak_carbide = max(alloy["fractions"]["carbide"])
        print(f"  stable chromium carbide up to {peak_carbide * 100:.1f} % mass — fe_c has no "
              "phase for it.")
    else:
        print("\n(no multicomponent steel TDB — right panel omitted. Enable it with: "
              "python -c \"from steel.calphad_backend import download_mc_fe; download_mc_fe()\")")


def save_figure(binary: dict, alloy: dict | None) -> Path:
    """Render and save the Phase-4 artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import calphad_figure

    fig = calphad_figure(binary, alloy)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, γ, subscripts on legacy codepages
    if not cb.available():
        print(cb._INSTALL_HINT)
        return

    binary, alloy = compute()
    print_summary(binary, alloy)
    try:
        saved = save_figure(binary, alloy)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
