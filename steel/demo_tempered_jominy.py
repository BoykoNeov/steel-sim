"""The §16 artifact: a *tempered* Jominy traverse — per-constituent temper of a mixture.

*Same end-quench, then temper — the martensite softens, the pearlite does not* (Steel plan
§16). Run the standard ASTM A255 Jominy bar once (the frozen thermal field of :mod:`jominy`),
read the **as-quenched** hardness traverse for two ≈ 0.4 %C steels (plain-carbon **1045**,
low-alloy **4140**), then read the **tempered** traverse for the same bars — each position
tempered ``t_hours`` h at ``T_temper`` °C **per-constituent** (:func:`properties.tempered_jominy_hardness`).

The thesis (the phase's teeth): the temper acts on the microstructure constituent-by-constituent,
so the result is a **differential** across the bar —

* the **near end** (full martensite) softens *hard* (down the validated 3b Hollomon–Jaffe curve);
* the **far end** (diffusional ferrite-pearlite) is **temper-inert** — it does not move at all.

A shallow-hardening steel (1045: martensite near → pearlite far) shows the whole differential
within one bar; a deep-hardening one (4140: martensite throughout) softens more uniformly and
its quenched end reproduces 3b's already-validated 4140 1 h temper response — the **bracket**.

Validation posture — **bracketing, not extraction** (plan §16): no tempered-Jominy atlas is
baked (tempered-Jominy data exists only in Hollomon–Jaffe modelling papers — the
"verify the AI-extracted table" trap). The near end is anchored to 3b's validated 4140 temper
response, the far end to 2c's validated as-quenched soft end, and the *differential shape*
between them is asserted qualitatively (``test_properties``). The figure is drawn in **HV** (not
HRC) because the "far end barely moves" story lives in the soft-pearlite region Rockwell-C cannot
display.

This is the banked §16 artifact and the integration test of the tempered chain: ``jominy``
(thermal field) → ``pathint`` (path → microstructure) → ``kinetics`` (``ccurve_for_steel``) →
``properties`` (mixture → **tempered** hardness) → ``plots``.

Run headless (saves the figure, prints the table):

    python -m steel.demo_tempered_jominy
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from .kinetics import ccurve_for_steel
from .jominy import JominyBar, solve_thermal_field, jominy_distances
from . import properties as prop

AUSTENITIZE_T = 850.0        # °C — fully austenitic before the quench
TEMPER_T = 400.0             # °C — a representative mid temper (the 3b 4140 benchmark point)
TEMPER_T_HOURS = 1.0         # h  — the standard 1 h temper

# The two benchmark steels (compositions as in the Phase-2b/2c/3a tests), both ≈ 0.4 %C: a
# medium-carbon plain steel and a deep-hardening low-alloy one. Their minor-alloy comp dicts
# (carbon excluded — it rides the constituent baselines) thread the Phase-3 Maynier terms.
STEELS = {
    "1045": dict(C=0.45, Mn=0.75, Si=0.22),
    "4140": dict(C=0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25),
}
COMP = {
    "1045": {"Mn": 0.75, "Si": 0.22},
    "4140": {"Mn": 0.90, "Cr": 1.0, "Mo": 0.20, "Si": 0.25},
}

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-tempered-jominy.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-tempered-jominy.png"


def compute(n_cells: int = 200, per_decade: int = 120,
            T_temper: float = TEMPER_T, t_hours: float = TEMPER_T_HOURS):
    """Run the tempered Jominy pipeline; return ``(field, as_quenched, tempered)``.

    ``as_quenched`` and ``tempered`` each map a steel label → its
    :class:`~steel.properties.JominyHardness` traverse on the *same* distances — the same bar,
    the same cooling, read before and after a per-constituent temper. The minor-alloy ``comp``
    is threaded into both (the Phase-3 Maynier term), so the far-end inert ferrite-pearlite
    matches between the two by construction.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")              # Biot caveat handled in jominy/cooling
        field = solve_thermal_field(JominyBar(), T0=AUSTENITIZE_T, n_cells=n_cells,
                                    per_decade=per_decade)
    d = jominy_distances(16)                         # 1.6 .. 25.4 mm, the standard read points
    as_quenched, tempered = {}, {}
    for label, comp_full in STEELS.items():
        cc = ccurve_for_steel(**comp_full)
        as_quenched[label] = prop.jominy_hardness(field, cc, comp_full["C"], d, comp=COMP[label])
        tempered[label] = prop.tempered_jominy_hardness(
            field, cc, comp_full["C"], T_temper, t_hours, distances=d, comp=COMP[label])
    return field, as_quenched, tempered


def print_summary(as_quenched, tempered, T_temper: float = TEMPER_T,
                  t_hours: float = TEMPER_T_HOURS) -> None:
    """Print the as-quenched → tempered hardness table — the demo's payoff in text form."""
    print(f"\nJominy end-quench (ASTM A255), austenitized {AUSTENITIZE_T:.0f} °C, "
          f"then tempered {t_hours:.0f} h @ {T_temper:.0f} °C\n")
    d = next(iter(as_quenched.values())).distance
    hdr = f"{'dist (mm)':>9s} " + "".join(f"{lbl:>22s}" for lbl in as_quenched)
    print(hdr)
    print(f"{'':9s} " + "".join(f"{'fM   HV_aq  HV_temp':>22s}" for _ in as_quenched))
    print("-" * len(hdr))
    for i, dd in enumerate(d):
        row = f"{dd * 1000:9.1f} "
        for lbl in as_quenched:
            aq, t = as_quenched[lbl], tempered[lbl]
            row += f"{aq.martensite[i]:6.2f} {aq.HV[i]:6.0f} {t.HV[i]:6.0f}  "
        print(row)
    print("\nThe differential temper (read the SHAPE):")
    for lbl in as_quenched:
        aq, t = as_quenched[lbl], tempered[lbl]
        print(f"  {lbl}: near-end softening {aq.HV[0] - t.HV[0]:5.0f} HV  |  "
              f"far-end softening {aq.HV[-1] - t.HV[-1]:5.0f} HV")
    print("→ the near end (full martensite) collapses; the far end (ferrite-pearlite) is "
          "temper-inert.\n  1045 shows the whole differential within one bar; 4140 (martensite "
          "throughout) softens deeper,\n  its quenched end reproducing 3b's validated 4140 1 h "
          "temper response (the bracket).")


def save_figure(as_quenched, tempered, T_temper: float = TEMPER_T,
                t_hours: float = TEMPER_T_HOURS) -> Path:
    """Render and save the tempered-Jominy artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import tempered_jominy_figure

    label = f"tempered {t_hours:.0f} h @ {T_temper:.0f} °C"
    fig = tempered_jominy_figure(as_quenched, tempered, temper_label=label)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, subscripts on legacy codepages

    _, as_quenched, tempered = compute()
    print_summary(as_quenched, tempered)
    try:
        saved = save_figure(as_quenched, tempered)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
