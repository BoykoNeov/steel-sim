"""``app.py`` — the thin Streamlit what-if surface on the sweep harness (Steel plan §9, slice 2).

The *shareable* interactive twin of ``steel.ipynb``: the same validated chain
(:mod:`sweep` → :mod:`cooling`/:mod:`pathint`/:mod:`properties`) re-skinned as a slider
UI you can ``streamlit run`` and hand someone a link to. It adds **reach, not correctness**
(ADR 0002): every number it shows is produced by a function already sealed behind its own
validation triad, so this module introduces **no new physics, no new calibration, no new
constant** — exactly like :mod:`sweep`, of which it is a pure re-composition.

Three layers, by ADR-0002 discipline
------------------------------------
1. **Compute helpers** (this module's top half) — plain functions that call :mod:`sweep`
   directly and return plain data (``Outcome`` lists, column dicts, display strings). They
   import **neither** Streamlit **nor** matplotlib, so the module imports on a bare core
   install and the helpers are unit-tested *always-green* (``tests/test_app.py``), the same
   way ``test_sweep`` is — there is nothing optional about them.
2. **Figure builders** — thin wrappers over the existing :mod:`projects.steel.plots` figures
   (:func:`~projects.steel.plots.four_curves_figure`,
   :func:`~projects.steel.plots.sweep_comparison_figure`), importing matplotlib **lazily**
   inside the function so the module stays import-light. The tempering view uses Streamlit's
   native ``st.line_chart`` (there is no matplotlib temper figure to reuse, and inventing one
   here would be scope creep into a render layer a prior phase owns).
3. **:func:`main`** — the *only* place ``import streamlit`` lives, and the one surface neither
   the test nor a headless checkout can exercise. So it is kept paper-thin: every value it
   displays is computed/formatted by a tested helper above, and the only statements that can
   raise are literal ``st.*`` calls. If a line in :func:`main` could throw on its own, it
   belongs in a helper — that rule is the sole defence against an unrunnable deliverable.

The run-as-script import bootstrap (why the lines below ``__file__`` exist)
--------------------------------------------------------------------------
``streamlit run projects/steel/app.py`` executes this file as a **top-level script**
(``__name__ == "__main__"``, no package parent) with ``projects/steel/`` — *not* the repo
root — on ``sys.path``. In that context a relative ``from . import sweep`` raises "no known
parent package" and a bare ``from projects.steel import sweep`` raises ``ModuleNotFoundError``
(``projects`` is not on the path). The demos dodge this by running under ``python -m`` (which
supplies both); ``streamlit run`` supplies neither. So this module puts the repo root on
``sys.path`` first (the ``parents[2]`` idiom the demos already use for figure paths) and then
imports **absolutely**. Under pytest the root is already on the path, so the insert is a
no-op and the test imports the very same module object.

Run it
------
.. code-block:: powershell

    pip install -e .[viz,app]          # matplotlib (viz) + streamlit (app)
    streamlit run projects/steel/app.py

The ``[app]`` extra carries only Streamlit; matplotlib stays in ``[viz]`` (the figures), so
the runnable combo is ``.[viz,app]`` — mirroring the notebook's ``.[viz,notebook]``.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# --- run-as-script bootstrap: put the repo root on sys.path BEFORE the absolute
#     imports below, so `streamlit run app.py` (a top-level script, no package parent)
#     resolves `projects.steel.*`. A no-op under pytest, where the root is already there.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

from projects.steel import sweep
from projects.steel import properties as prop


# The dropdown vocabularies — the real-composition grades and the slow→fast media. Using the
# STEELS registry (not a raw %C / Mn=0 slider) keeps the surface off the documented
# "leaner hypothetical steel" trap: a plain-carbon grade still carries its ~0.7 % Mn, and the
# reference 1080 the kinetics were calibrated to *is* that Mn (sweep.STEELS docstring).
GRADES = list(sweep.STEELS)
MEDIA = list(sweep.DEFAULT_MEDIA)
DEFAULT_COMPARE = ["1045", "1080", "4140"]


# --------------------------------------------------------------------------- #
# 1. Compute helpers — pure sweep re-composition (no streamlit, no matplotlib)
# --------------------------------------------------------------------------- #
def single_steel_outcomes(grade: str, diameter: float = sweep.STANDARD_DIAMETER) -> list:
    """One grade down the cooling-rate axis (furnace→water) — the mechanism view's data.

    A :func:`sweep.cooling_rate_sweep` for the named grade: four :class:`~projects.steel.sweep.Outcome`
    objects sharing one austenite, differing only in quench severity. Their common
    ``ccurve`` (composition-determined, so identical across media) and their paths/results/
    hardness feed :func:`mechanism_figure`.
    """
    return sweep.cooling_rate_sweep(sweep.STEELS[grade], diameter=diameter)


def evaluate_one(grade: str, medium: str | float, diameter: float = sweep.STANDARD_DIAMETER):
    """The single what-if behind the hardness readout — one grade, one quench condition."""
    return sweep.evaluate(sweep.STEELS[grade], medium=medium, diameter=diameter)


def comparison_grid(grades, diameter: float = sweep.STANDARD_DIAMETER) -> list:
    """The composition × cooling-rate grid for the side-by-side panel (:func:`sweep.sweep_grid`)."""
    return sweep.sweep_grid(list(grades), diameter=diameter)


def temper_curve_data(grade: str, t_hours: float = 1.0) -> dict:
    """The quench-and-temper response as plain chart columns (martensite-only, by design).

    Wraps :func:`sweep.temper_sweep` (the validated *martensite-only* Q&T curve — pearlite
    barely tempers, so a mixed structure is a documented deferral) and flattens it to a dict
    of equal-length arrays ``st.line_chart`` can consume directly: ``temper_C`` (the x-axis),
    ``HV``/``HRC`` hardness, ``UTS_MPa`` strength, ``toughness`` the rough relative index, plus
    the scalar ``HV_as_quenched`` (the curve's left limit). The quantities live on very
    different scales (HV ~ hundreds, HRC ~ tens, UTS ~ thousands, toughness 0–1), so
    :func:`main` charts them **separately**, never on one shared axis.
    """
    tr = sweep.temper_sweep(sweep.STEELS[grade], t_hours=t_hours)
    return {
        "temper_C": np.asarray(tr.temper_C, dtype=float),
        "HV": np.asarray(tr.HV, dtype=float),
        "HRC": np.asarray(tr.HRC, dtype=float),
        "UTS_MPa": np.asarray(tr.UTS_MPa, dtype=float),
        "toughness": np.asarray(tr.toughness, dtype=float),
        "HV_as_quenched": float(tr.HV_as_quenched),
    }


def format_hrc(hrc: float) -> str:
    """HRC display string — the honest ``off HRC scale`` where Rockwell-C is undefined (<~20)."""
    return f"{hrc:.0f} HRC" if math.isfinite(hrc) else "off HRC scale (soft)"


def hardness_readout(outcome) -> dict:
    """Flatten one :class:`~projects.steel.sweep.Outcome` to display-ready strings for the readout.

    All the nan/HRC and formatting logic lives here (a tested helper), so :func:`main` only
    forwards strings to ``st.metric`` — never formats a possibly-``nan`` number itself.
    """
    return {
        "HV": f"{outcome.HV:.0f} HV",
        "HRC": format_hrc(outcome.HRC),
        "dominant": outcome.dominant().replace("_", " "),
        "Vr": f"{outcome.Vr:,.0f} °C/h" if math.isfinite(outcome.Vr) else "—",
        "fractions": {k: float(v) for k, v in outcome.fractions().items()},
        "lumped_valid": bool(outcome.lumped_valid),
        "biot": float(outcome.biot),
    }


# --------------------------------------------------------------------------- #
# 2. Figure builders — thin wrappers over plots.py (matplotlib imported lazily)
# --------------------------------------------------------------------------- #
def mechanism_figure(outcomes: list, grade: str):
    """The Phase-1 anchor figure for one grade: cooling paths on the TTT + microstructure bars.

    Reuses :func:`projects.steel.plots.four_curves_figure` (the plan names it explicitly for
    slice 2). The four outcomes share one ``ccurve`` (composition-determined), so the C-curve
    is taken from the first; each contributes its path, microstructure, and ``(HV, HRC)``.
    Raises ``ImportError`` if matplotlib (the ``[viz]`` extra) is absent — caught in :func:`main`.
    """
    from projects.steel.plots import four_curves_figure

    cc = outcomes[0].ccurve
    paths = [o.path for o in outcomes]
    results = [o.result for o in outcomes]
    hardness = [(o.HV, o.HRC) for o in outcomes]
    title = f"{grade}: one steel, four cooling rates — soft pearlite → hard martensite"
    return four_curves_figure(cc, paths, results, hardness=hardness, title=title)


def comparison_figure(grid: list):
    """The composition × cooling-rate side-by-side (:func:`projects.steel.plots.sweep_comparison_figure`).

    Hardenability curves (martensite vs cooling rate, one line per grade) beside the hardness
    grid. Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from projects.steel.plots import sweep_comparison_figure

    return sweep_comparison_figure(grid)


# --------------------------------------------------------------------------- #
# 3. main() — the Streamlit surface (the ONLY place streamlit is imported)
# --------------------------------------------------------------------------- #
def main() -> None:
    """Render the what-if app. Streamlit-only; not unit-tested (ADR 0002 — UI is reach).

    Kept paper-thin on purpose: every displayed value comes from a tested helper above, so the
    only statements here that can raise are ``st.*`` calls (and the figure builders, whose lone
    failure mode — matplotlib absent — is caught and turned into an ``st.info`` hint).
    """
    import streamlit as st

    st.set_page_config(page_title="Steel — cooling curve in, microstructure out",
                       layout="wide")
    st.title("Steel: cooling curve in, microstructure out")
    st.caption(
        "A thin what-if skin on the validated sweep harness (Steel plan §9). Every number is "
        "produced by a model sealed behind its own validation triad — this UI only turns the "
        "knobs (ADR 0002)."
    )

    # ---- sidebar: the knobs ------------------------------------------------ #
    st.sidebar.header("What-if controls")
    grade = st.sidebar.selectbox("Steel grade", GRADES,
                                 index=GRADES.index("1080") if "1080" in GRADES else 0)
    medium = st.sidebar.select_slider("Quench medium (slow → fast)", options=MEDIA, value="oil")
    diameter_mm = st.sidebar.slider("Section size — cylinder diameter (mm)", 5, 100,
                                    int(round(sweep.STANDARD_DIAMETER * 1000.0)))
    diameter = diameter_mm / 1000.0
    st.sidebar.markdown("---")
    compare = st.sidebar.multiselect("Compare these grades", GRADES, default=DEFAULT_COMPARE)
    temper_hours = st.sidebar.slider("Temper time (hours)", 0.25, 8.0, 1.0, 0.25)

    viz_hint = "Install the figures: `pip install -e .[viz,app]`"

    # ---- section 1: one grade, the mechanism + the hardness readout -------- #
    st.subheader(f"{grade}: same steel, four fates")
    one = evaluate_one(grade, medium, diameter)
    r = hardness_readout(one)
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Hardness in {medium}", r["HV"])
    c1.caption(r["HRC"])                              # HRC as a plain gray line — not a metric delta
    c2.metric("Dominant constituent", r["dominant"])
    c3.metric("Cooling rate at 700 °C", r["Vr"])
    if not r["lumped_valid"]:
        st.warning(
            f"This quench of a {diameter_mm:.0f} mm section exceeds the 0-D lumped-capacitance "
            f"range (Biot = {r['biot']:.2f} ≥ 0.1) — a severe quench of a thick part needs the "
            "Phase-2 spatial solve. The hardness shown is the 0-D estimate, flagged not trusted."
        )

    outcomes = single_steel_outcomes(grade, diameter)
    try:
        st.pyplot(mechanism_figure(outcomes, grade))
    except ImportError:
        st.info(viz_hint)

    # ---- section 2: the composition × cooling-rate comparison -------------- #
    st.subheader("Composition × cooling rate — the hardenability grid")
    st.caption(
        "In the 0-D model every steel sees the *same* cooling path at a given medium, so the "
        "grades share the martensitic fast end and the pearlitic slow end and **diverge only in "
        "the middle** — read the alloy-hardenability trend at an intermediate quench (oil)."
    )
    if compare:
        grid = comparison_grid(compare, diameter)
        try:
            st.pyplot(comparison_figure(grid))
        except ImportError:
            st.info(viz_hint)
    else:
        st.info("Pick one or more grades in the sidebar to compare.")

    # ---- section 3: the quench-and-temper response (martensite-only) ------- #
    st.subheader(f"{grade}: quench-and-temper response ({temper_hours:g} h temper)")
    st.caption(
        "A fully martensitic start tempered at each temperature: hardness falls and toughness "
        "rises — the strength/toughness trade-off. Martensite-only by design (pearlite barely "
        "tempers — a documented scope limit)."
    )
    td = temper_curve_data(grade, temper_hours)
    tcol1, tcol2 = st.columns(2)
    tcol1.markdown("**Hardness (HV) vs temper temperature**")
    tcol1.line_chart(td, x="temper_C", y="HV")
    tcol2.markdown("**Tensile strength (MPa) vs temper temperature**")
    tcol2.line_chart(td, x="temper_C", y="UTS_MPa")
    tcol3, tcol4 = st.columns(2)
    tcol3.markdown("**Hardness (HRC) vs temper temperature** (gaps = off-scale soft)")
    tcol3.line_chart(td, x="temper_C", y="HRC")
    tcol4.markdown("**Relative toughness vs temper temperature**")
    tcol4.line_chart(td, x="temper_C", y="toughness")
    st.caption(
        f"As-quenched start: {td['HV_as_quenched']:.0f} HV. An alloy steel resists tempering "
        "(starts harder, floors higher) — an emergent consequence of threading its composition "
        "through both ends of the master curve."
    )


if __name__ == "__main__":
    main()
