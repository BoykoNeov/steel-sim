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


# The dropdown vocabularies — the real-composition grades and the slow→fast media. The preset
# registry drives the main what-ifs (sections 1–2): a plain-carbon grade still carries its
# ~0.7 % Mn and the reference 1080 the kinetics were calibrated to *is* that Mn (sweep.STEELS
# docstring), so the dropdown cannot wander into the documented "leaner hypothetical steel" trap.
# The *build-your-own* section (4) deliberately reopens a free C/Mn/Cr/Mo/Ni slider — the
# experimentation payoff the notebook also exposes — and pays for that reach honestly: the Mn
# slider floors at MN_FLOOR and composition_warnings() flags alloy content past the 1080/4140
# calibration envelope. So free composition here is a *guarded* reach, not an oversight.
GRADES = list(sweep.STEELS)
MEDIA = list(sweep.DEFAULT_MEDIA)
DEFAULT_COMPARE = ["1045", "1080", "4140"]

# The build-your-own composition envelope — the honest companion to allowing a free slider at
# all. The kinetics are calibrated to 1080 (Mn≈0.7, hardenability M = 1) and 4140 (Cr1.0/Mo0.2);
# beyond that the C-curve shift extrapolates. MN_FLOOR doubles as the Mn slider's lower bound in
# main(), so composition_warnings()'s Mn branch is a tested *programmatic* guard (a drag can't
# reach it); the alloy-envelope branch is the live, UI-reachable warning.
MN_FLOOR = 0.30
ALLOY_ENVELOPE = {"Cr": 1.5, "Mo": 0.40, "Ni": 1.5}


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


def format_uts(uts: float) -> str:
    """UTS display string — honest ``off-scale`` where ISO-18265 leaves HV (as-quenched HV > ~550).

    The ISO-18265 HV→UTS correlation is defined on a finite hardness band; outside it
    :func:`~projects.steel.properties.tensile_strength_MPa` returns ``nan`` (a glass-hard
    as-quenched martensite has no meaningful tensile number — it fractures first). Say so,
    rather than print a ``nan`` MPa.
    """
    return f"{uts:,.0f} MPa" if math.isfinite(uts) else "off-scale (as-quenched)"


def hardness_readout(outcome) -> dict:
    """Flatten one :class:`~projects.steel.sweep.Outcome` to display-ready strings for the readout.

    All the nan/HRC and formatting logic lives here (a tested helper), so :func:`main` only
    forwards strings to ``st.metric`` — never formats a possibly-``nan`` number itself. ``UTS``
    (ISO-18265 tensile strength) and ``toughness`` (the rough relative [0, 1] index) are derived
    from the same validated ``HV`` and carried here too, so the single what-if surfaces the
    strength/toughness consequence, not just hardness.
    """
    return {
        "HV": f"{outcome.HV:.0f} HV",
        "HRC": format_hrc(outcome.HRC),
        "UTS": format_uts(prop.tensile_strength_MPa(outcome.HV)),
        "toughness": f"{prop.toughness_index(outcome.HV):.2f}",
        "dominant": outcome.dominant().replace("_", " "),
        "Vr": f"{outcome.Vr:,.0f} °C/h" if math.isfinite(outcome.Vr) else "—",
        "fractions": {k: float(v) for k, v in outcome.fractions().items()},
        "lumped_valid": bool(outcome.lumped_valid),
        "biot": float(outcome.biot),
    }


def custom_steel_outcome(
    C: float, Mn: float, Cr: float, Mo: float, Ni: float,
    medium: str | float = sweep.DISCRIMINATING_MEDIUM,
    diameter: float = sweep.STANDARD_DIAMETER,
):
    """The build-your-own what-if: a *free* composition → the full validated chain.

    The notebook's §3 "build your own steel" as a headless helper — one
    :func:`sweep.evaluate` of a :class:`~projects.steel.sweep.Steel` assembled from free
    C/Mn/Cr/Mo/Ni, at the **discriminating** oil quench (the composition axis is silent at the
    saturated water/furnace ends — see :data:`sweep.DISCRIMINATING_MEDIUM`). The *same* harness
    the preset dropdown uses, driven by sliders instead of a registry key — so it adds no
    physics, only reach. The fixed oil medium / standard section isolate the composition effect
    (the sidebar's grade/medium/diameter knobs intentionally do **not** reach this section).
    """
    steel = sweep.Steel(C=float(C), Mn=float(Mn), Cr=float(Cr), Mo=float(Mo),
                        Ni=float(Ni), name="your steel")
    return sweep.evaluate(steel, medium=medium, diameter=diameter)


def custom_readout(outcome) -> dict:
    """Display strings for the build-your-own panel — the knobs the composition moved + the result.

    Surfaces what alloying *did*: ``Ms`` (the martensite-start the composition lowered) and
    ``hardenability`` (the ``tau_factor`` C-curve shift — the deeper-hardening payoff), then the
    resulting structure (``martensite`` fraction) and properties (``HV``/``HRC``/``UTS``/
    ``toughness``). All nan/format logic here, so :func:`main` only forwards strings.
    """
    return {
        "Ms": f"{outcome.ccurve.Ms:.0f} °C",
        "hardenability": f"{outcome.ccurve.tau_factor:.1f}×",
        "martensite": f"{outcome.result.martensite:.0%}",
        "HV": f"{outcome.HV:.0f} HV",
        "HRC": format_hrc(outcome.HRC),
        "UTS": format_uts(prop.tensile_strength_MPa(outcome.HV)),
        "toughness": f"{prop.toughness_index(outcome.HV):.2f}",
    }


def composition_warnings(C: float, Mn: float, Cr: float, Mo: float, Ni: float) -> list[str]:
    """Honest envelope cautions for a free composition — the build-your-own guardrails.

    The preset dropdown cannot leave the validated chemistry; a free slider can, so it must
    *say so*. Returns human-readable cautions (an empty list means inside the envelope): a
    sub-:data:`MN_FLOOR` Mn "leaner hypothetical" the kinetics warn about, and alloy contents
    past the 1080/4140 calibration grades (:data:`ALLOY_ENVELOPE`) where the hardenability shift
    extrapolates. These are *reach* flags, not hard limits — the number still computes; the
    warning is the honesty (ADR 0002). The Mn branch is a programmatic guard: ``main()`` floors
    the Mn slider at :data:`MN_FLOOR`, so a drag cannot trigger it (but a direct call can).
    """
    warns: list[str] = []
    if Mn < MN_FLOOR:
        warns.append(
            f"Mn = {Mn:.2f} % is below ~{MN_FLOOR:.2f} % — a real plain-carbon steel still "
            "carries ~0.7 % Mn, so this is a leaner hypothetical the kinetics flag (the reference "
            "1080 they were calibrated to *is* that Mn).")
    high = [f"{el} {val:.2f} %" for el, val in (("Cr", Cr), ("Mo", Mo), ("Ni", Ni))
            if val > ALLOY_ENVELOPE[el]]
    if high:
        warns.append(
            "Alloy content beyond the calibration grades (1080, 4140): " + ", ".join(high)
            + " — the hardenability shift extrapolates past the validated envelope here.")
    return warns


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


def custom_figure(outcome):
    """The build-your-own two-panel view: the cooling path across the (alloy-shifted) TTT +
    a schematic microstructure swatch.

    A thin wrapper over :func:`projects.steel.plots.single_steel_figure` — the render layer owns
    the composition, exactly as :func:`mechanism_figure` wraps ``four_curves_figure`` (the app
    invents no figure of its own). The title carries the two hardenability knobs the composition
    moved (Mₛ and the ``tau_factor`` shift). Raises ``ImportError`` without matplotlib — caught
    in :func:`main`.
    """
    from projects.steel.plots import single_steel_figure

    cc = outcome.ccurve
    ttt_title = (f"your steel — the TTT slides right with alloy  "
                 f"(Mₛ {cc.Ms:.0f} °C · hardenability M {cc.tau_factor:.1f}×)")
    return single_steel_figure(cc, outcome.path, outcome.result, ttt_title=ttt_title,
                               schematic_title="microstructure at an oil quench")


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

    # The entry-level on-ramp — open by default so a newcomer meets it, collapsible for the expert.
    with st.expander("New to heat treatment? Start here — the 30-second mental model", expanded=True):
        st.markdown(
            "**Steel is iron with a little carbon.** Heat it red-hot (~850 °C) and it becomes "
            "**austenite**, which dissolves the carbon. What happens in the seconds *after* you "
            "start cooling decides whether you get a soft, machinable part or a glass-hard one.\n\n"
            "- **How much carbon** sets the *potential* hardness.\n"
            "- **What alloy** (Mn, Cr, Mo, Ni) sets how *deep* the hardness reaches — *hardenability*.\n"
            "- **How fast you cool** sets *which* microstructure actually forms.\n"
            "- **Tempering** (reheating afterward) trades hardness back for toughness.\n\n"
            "The one rule of thumb everything below makes concrete: **slow cooling → soft pearlite; "
            "fast quench → hard martensite; alloying lets martensite form even when you cool more "
            "slowly.** Glossary: *pearlite* = soft layered ferrite + cementite (slow cooling); "
            "*bainite* = an intermediate product; *martensite* = hard, carbon trapped (fast quench)."
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Hardness in {medium}", r["HV"])
    c1.caption(r["HRC"])                              # HRC as a plain gray line — not a metric delta
    c2.metric("Tensile strength (UTS)", r["UTS"])
    c3.metric("Dominant constituent", r["dominant"])
    c4.metric("Cooling rate at 700 °C", r["Vr"])
    st.caption(
        f"Relative toughness index ≈ {r['toughness']} (a rough [0, 1] proxy that rises as the steel "
        "softens) · UTS via the ISO-18265 hardness correlation, off-scale for as-quenched martensite."
    )
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

    # ---- section 3: build your own steel — the free-composition what-if ---- #
    st.subheader("Build your own steel — move the C-curve with composition")
    st.caption(
        "Mix your own chemistry and watch the TTT slide right with alloy (that *is* hardenability) "
        "and the microstructure respond. Read at an **oil** quench — the discriminating medium "
        "(water → all martensite, furnace → all pearlite, so the composition axis only speaks in "
        "the middle). The swatch is a **schematic**: areas = the computed phase fractions, grain "
        "shapes are illustrative (not a grain simulation)."
    )
    bc = st.columns(5)
    C = bc[0].slider("C %", 0.10, 1.00, 0.45, 0.05)
    Mn = bc[1].slider("Mn %", MN_FLOOR, 2.00, 0.75, 0.05)
    Cr = bc[2].slider("Cr %", 0.00, 2.00, 0.00, 0.05)
    Mo = bc[3].slider("Mo %", 0.00, 0.60, 0.00, 0.05)
    Ni = bc[4].slider("Ni %", 0.00, 2.00, 0.00, 0.05)
    for w in composition_warnings(C, Mn, Cr, Mo, Ni):
        st.warning(w)
    custom = custom_steel_outcome(C, Mn, Cr, Mo, Ni)
    cr = custom_readout(custom)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mₛ (martensite start)", cr["Ms"])
    m2.metric("Hardenability M", cr["hardenability"])
    m3.metric("Hardness (oil quench)", cr["HV"])
    m3.caption(cr["HRC"])
    m4.metric("Tensile strength (UTS)", cr["UTS"])
    st.caption(
        f"Oil quench → {cr['martensite']} martensite · relative toughness ≈ {cr['toughness']}. "
        "Reproduce the presets: 1045 ≈ C0.45/Mn0.75 · 4140 ≈ C0.40/Mn0.90/Cr1.0/Mo0.20 · "
        "8620 ≈ C0.20/Mn0.80/Ni0.55/Cr0.50/Mo0.20."
    )
    try:
        st.pyplot(custom_figure(custom))
    except ImportError:
        st.info(viz_hint)

    # ---- section 4: the quench-and-temper response (martensite-only) ------- #
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
