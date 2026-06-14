"""``app_making.py`` — the thin Streamlit what-if surface on the **steel-making** front end.

The shareable interactive twin of the front-end chain, the way :mod:`app` is the twin of the
back-end heat-treatment story. Where :mod:`app` is *"cooling curve in, microstructure out"*
(``sweep`` → microstructure), this surface is *"ore → billet"*: the validated front-end stages
the plan builds — reduction (F1), the ``Heat`` spine, primary refining + slag partition (F2),
ladle trim to grade (F3), casting + solidification (F4). It is a **separate** app on purpose
(``docs/plans/steel-making.md`` §7): the two narratives, the two test surfaces, and the two
paper-thin ``main()`` bodies stay focused instead of one 3000-line file straddling both.

Like :mod:`app`, it adds **reach, not correctness** (ADR 0002): every number it shows is produced
by a function already sealed behind its own validation triad (:mod:`reduction`, :mod:`refining`,
:mod:`slag`, :mod:`ladle`, :mod:`casting`, :mod:`solidification`, :mod:`heat_state`), so this
module introduces **no new physics, no new calibration, no new constant**.

Three layers, by the same ADR-0002 discipline :mod:`app` follows
----------------------------------------------------------------
1. **Compute helpers** (top half) — plain functions that call the front-end modules directly and
   return plain data (readout dicts of display strings + the raw scalars/flags the UI branches and
   the tests assert on). They import **neither** Streamlit **nor** matplotlib, so the module imports
   on a bare core install and the helpers are unit-tested *always-green* (``tests/test_app_making.py``).
2. **Figure builders** — thin wrappers over the banked ``demo_*.compute()`` pipelines + the existing
   :mod:`steel.plots` front-end figures, importing matplotlib **lazily** inside the function (via the
   ``plots`` import) so the module stays import-light. The app invents **no figure of its own** — it
   reuses the validated demo arrays and the render layer that owns the drawing.
3. **:func:`main`** — the *only* place ``import streamlit`` lives. Kept paper-thin: every value it
   displays is computed/formatted by a tested helper above, so the only statements that can raise are
   literal ``st.*`` calls and the figure builders (whose lone failure mode — matplotlib absent — is
   caught and turned into an ``st.info`` hint).

The run-as-script import bootstrap is the same idiom :mod:`app` documents: ``streamlit run`` executes
this file as a top-level script with no package parent, so we put the repo root on ``sys.path`` first
and import absolutely (a no-op under pytest, where the root is already there).

Run it
------
.. code-block:: powershell

    pip install -e .[viz,app]                # matplotlib (viz) + streamlit (app)
    streamlit run steel/app_making.py        # the front-end twin of `streamlit run steel/app.py`
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# --- run-as-script bootstrap: repo root on sys.path BEFORE the absolute imports (the app.py idiom).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from steel import casting as cast
from steel import heat_state as hs
from steel import ladle as ld
from steel import reduction as red
from steel import refining as ref
from steel import slag as sl
from steel.heat_state import Heat
from steel.sweep import STEELS, Steel, evaluate


# --------------------------------------------------------------------------- #
# 0. The vocabularies — knob bounds and the anchored scenarios each stage rides
# --------------------------------------------------------------------------- #
# F1 — reduction (Ellingham). The temperature axis the C→CO / FeO crossover sits on (the headline
# benchmark ~746 °C), and the deoxidizer-oxide stability ladder, read at the chosen temperature.
RED_T_MIN, RED_T_MAX = 400.0, 1600.0
CARBON_KEY, WUSTITE_KEY = "C->CO", "Fe->FeO"
HIERARCHY_KEYS = red.HIERARCHY_KEYS + (WUSTITE_KEY,)        # Ca, Al, Si, Mn, Cr oxides + wüstite

# The spine — the failure-propagation lever: an under-dosed 4140 (Mn kept on spec, so only the
# deep-hardening Cr/Mo move). The same oil quench both heats see, so the divergence is the chemistry.
SPINE_BASE = dict(C=0.40, Mn=0.90, Si=0.25)
SPINE_CR_NOMINAL, SPINE_MO_NOMINAL = 1.0, 0.20
SPINE_MEDIUM, SPINE_DIAMETER = "oil", 0.010

# F2 — refining. The single-element deoxidizers (Al ≫ Si > Mn) and the addition-level axis the
# Al–O minimum sits on; the C–O product is the static converter benchmark.
DEOX_SYMBOLS = list(ref.DEOXIDIZERS)                        # ["Al", "Si", "Mn"]
DEOX_LEVEL_MIN, DEOX_LEVEL_MAX = 0.01, 0.30

# F2 — slag partition. The three reference slags spanning the history (acid Bessemer can't dephos,
# basic converter can, the ladle slag desulfurizes once the heat is killed). The dissolved-oxygen
# axis is the −log a_O coupling desulfurization rides (converter ~hundreds ppm, killed ladle ~few).
SLAGS = {
    sl.ACID_BESSEMER_SLAG.name: sl.ACID_BESSEMER_SLAG,
    sl.BASIC_CONVERTER_SLAG.name: sl.BASIC_CONVERTER_SLAG,
    sl.LADLE_DESULF_SLAG.name: sl.LADLE_DESULF_SLAG,
}
SLAG_O_MIN, SLAG_O_MAX = 2.0, 600.0

# F3 — ladle trim. The hero grade and the recovery-shortfall axis (additions sized for the assumed
# recovery; a bath that under-delivers lands short → off-grade → a soft core at the quench).
LADLE_GRADE = "4140"
LADLE_RECOVERY_MIN, LADLE_RECOVERY_MAX = 0.30, 1.05
LADLE_MEDIUM, LADLE_DIAMETER = "oil", 0.015

# F4 — casting. The hero grade, the casting-modulus axis (Chvorinov t ∝ M²), and the discriminating
# treat section where the segregated centerline over-hardens into a band the nominal bulk misses.
CAST_GRADE = "4140"
CAST_MODULUS_MIN_MM, CAST_MODULUS_MAX_MM = 5.0, 60.0
CAST_MEDIUM, CAST_DIAMETER = "oil", 0.050


# --------------------------------------------------------------------------- #
# 1. Compute helpers — pure front-end re-composition (no streamlit, no matplotlib)
# --------------------------------------------------------------------------- #
def _fmt_g(g_kJ: float) -> str:
    return f"{g_kJ:+,.0f} kJ/mol O₂"


def reduction_readout(T_celsius: float) -> dict:
    """F1 at a chosen temperature: can carbon reduce wüstite yet, and the oxide-stability ladder.

    Reads the Ellingham model (:mod:`reduction`) at ``T_celsius``: the carbon→CO and iron→FeO free
    energies, whether carbon's line has dropped below wüstite's (the spontaneous-reduction test), the
    fixed crossover temperature where it does, and the deoxidizer/oxide stability order at this
    temperature (most stable first — the Ca < Al < Si < Mn < Cr < Fe ladder the kill chemistry reads).
    All formatting here, so :func:`main` only forwards strings (+ reads ``carbon_reduces_wustite``).
    """
    carbon, wustite = red.REACTIONS[CARBON_KEY], red.REACTIONS[WUSTITE_KEY]
    g_carbon = red.standard_free_energy(carbon, T_celsius) / 1000.0
    g_wustite = red.standard_free_energy(wustite, T_celsius) / 1000.0
    reduces = red.reduces(carbon, wustite, T_celsius)
    crossover = red.crossover_temperature(carbon, wustite)
    order = [(k, g / 1000.0) for k, g in red.stability_order(HIERARCHY_KEYS, T_celsius)]
    return {
        "T_C": T_celsius,
        "crossover_C": float(crossover) if crossover is not None else float("nan"),
        "carbon_reduces_wustite": reduces,
        "g_carbon": _fmt_g(g_carbon),
        "g_wustite": _fmt_g(g_wustite),
        "verdict": (
            "carbon (→CO) reduces wüstite — ironmaking is spontaneous here"
            if reduces else
            "carbon cannot pull the last oxygen off iron yet — below the crossover"
        ),
        "hierarchy_order": [k for k, _ in order],
        "hierarchy_rows": [{"oxide": k, "dG": _fmt_g(g)} for k, g in order],
    }


def spine_readout(Cr: float, Mo: float) -> dict:
    """The spine lever: dose Cr/Mo on a 4140, run the *same* oil quench, and read the propagation.

    Builds a :class:`~steel.heat_state.Heat` from the fixed 4140 backbone with the chosen Cr/Mo, threads
    it through :func:`~steel.heat_state.heat_treat` (the validated back end), and reads the core
    martensite, hardness, and whether the soft-core flag fell out of the physics — the failure that is
    *emergent* (the martensite fraction crossing :data:`~steel.heat_state.MIN_MARTENSITE_SPEC`), not
    scripted. The provenance trail is surfaced so the UI can show where the heat is judged.
    """
    comp = Steel(**SPINE_BASE, Cr=float(Cr), Mo=float(Mo), name=f"4140 (Cr {Cr:.2f}, Mo {Mo:.2f})")
    heat = hs.heat_treat(Heat(composition=comp), medium=SPINE_MEDIUM, diameter=SPINE_DIAMETER)
    o = evaluate(comp, medium=SPINE_MEDIUM, diameter=SPINE_DIAMETER)
    soft = heat.has_defect(hs.SOFT_CORE)
    return {
        "martensite": float(o.result.martensite),
        "HV": float(o.HV),
        "soft_core": soft,
        "spec": float(hs.MIN_MARTENSITE_SPEC),
        "martensite_str": f"{o.result.martensite:.0%}",
        "HV_str": f"{o.HV:.0f} HV",
        "spec_str": f"{hs.MIN_MARTENSITE_SPEC:.0%} martensite",
        "verdict": (
            f"soft core — only {o.result.martensite:.0%} martensite, under the "
            f"{hs.MIN_MARTENSITE_SPEC:.0%} spec (the under-dose propagated to a defect)"
            if soft else
            f"through-hardens — {o.result.martensite:.0%} martensite, clears the "
            f"{hs.MIN_MARTENSITE_SPEC:.0%} spec"
        ),
        "trail": [f"{s.name}: {s.summary}" for s in heat.history],
    }


def refining_deox_readout(deox_symbol: str, level_pct: float) -> dict:
    """F2 deoxidation: the dissolved oxygen a given addition of one deoxidizer leaves, and the ladder.

    Reads :mod:`refining`: the equilibrium dissolved oxygen after ``level_pct`` of the chosen
    deoxidizer (with the Sigworth–Elliott interaction that bends aluminium through a **minimum**, and
    the dilute cartoon without it — the contrast that *is* the minimum), the strongest-first hierarchy
    at this addition (the Al ≫ Si > Mn ordering that cross-coheres with F1's Ellingham order), the
    closed-form Al–O minimum location (~0.074 %, robust to the scattered K), and the C–O product
    benchmark. All formatting here, so :func:`main` only forwards strings.
    """
    deox = ref.DEOXIDIZERS[deox_symbol]
    o_real = ref.equilibrium_oxygen_after_deox(deox, level_pct, with_interaction=True)
    o_cartoon = ref.equilibrium_oxygen_after_deox(deox, level_pct, with_interaction=False)
    hierarchy = ref.deoxidizing_power(level_pct)                     # (sym, ppm) strongest first
    al_min_pct, al_min_ppm = ref.aluminium_oxygen_minimum()
    return {
        "deox_name": deox.name,
        "oxide": deox.oxide,
        "oxygen_ppm": float(o_real),
        "oxygen_ppm_cartoon": float(o_cartoon),
        "hierarchy": [(sym, float(ppm)) for sym, ppm in hierarchy],
        "al_min_pct": float(al_min_pct),
        "al_min_ppm": float(al_min_ppm),
        "co_product": float(ref.carbon_oxygen_product()),
        "oxygen_str": f"{o_real:,.0f} ppm O",
        "oxygen_cartoon_str": f"{o_cartoon:,.0f} ppm O",
        "hierarchy_rows": [{"deoxidizer": sym, "[O] ppm": f"{ppm:,.0f}"} for sym, ppm in hierarchy],
        "al_min_str": f"[Al] ≈ {al_min_pct:.3f} % → {al_min_ppm:,.0f} ppm O (the curve's floor)",
    }


def slag_partition_readout(slag_name: str, oxygen_ppm: float) -> dict:
    """F2 slag partition: the phosphorus and sulfur partition ratios for one slag at a dissolved-O level.

    Reads :mod:`slag`: the Healy phosphorus partition ``L_P`` (oxidizing — large for a basic, iron-rich
    converter slag, near 1 for an acid one: *why acid Bessemer couldn't make sound rails*) and the
    Sosinsky–Sommerville sulfur partition ``L_S`` at the chosen dissolved oxygen (reducing — the
    ``−log a_O`` coupling, so the *same* slag desulfurizes a killed ladle heat far better than a raw
    converter one). The opposite oxygen dependence of P vs S is the headline. All formatting here.
    """
    slag = SLAGS[slag_name]
    L_P = sl.phosphorus_partition(slag)
    L_S = sl.sulfur_partition(slag, oxygen_ppm)
    return {
        "slag_label": slag.label(),
        "basicity": float(slag.basicity),
        "optical_basicity": float(slag.optical_basicity),
        "L_P": float(L_P),
        "L_S": float(L_S),
        "basicity_str": f"B = %CaO/%SiO₂ = {slag.basicity:.1f}  ({'basic' if slag.basicity > 1 else 'acid'})",
        "L_P_str": f"L_P = {L_P:,.1f}",
        "L_S_str": f"L_S = {L_S:,.1f}  (at {oxygen_ppm:,.0f} ppm O)",
        "dephos_verdict": (
            "dephosphorizes — phosphorus pulled into the slag"
            if L_P > 10 else
            "barely dephosphorizes — phosphorus stays in the steel"
        ),
    }


def _assumed_recovery() -> dict[str, float]:
    """The ferroalloy nominal yields the trim additions are sized for (the demo's assumed recovery)."""
    return {e: ld.FERROALLOYS[e].recovery for e in ("Mn", "Si", "Cr", "Mo")}


def ladle_trim_readout(recovery_ratio: float) -> dict:
    """F3 trim: size a 4140 to grade, deliver Cr/Mo at ``recovery_ratio`` of assumed, read the two flags.

    Mirrors :mod:`demo_ladle`'s mechanism: a fresh alloy-lean tap, additions sized for the assumed
    recovery, then delivered at ``recovery_ratio``× on Cr/Mo (an under-killed bath eats the additions).
    A short heat lands **off-grade** (Cr below the cited window floor — F3's labelled-spec catch) and
    then **soft-cores** at the same oil quench (the validated back-end consequence): one mistake, two
    flags. All formatting here, so :func:`main` only forwards strings (+ reads the two flags).
    """
    assumed = _assumed_recovery()
    actual = {**assumed, "Cr": assumed["Cr"] * recovery_ratio, "Mo": assumed["Mo"] * recovery_ratio}
    trimmed = ld.trim_to_grade(ld.from_tap(LADLE_GRADE), LADLE_GRADE, actual_recovery=actual)
    treated = hs.heat_treat(trimmed, medium=LADLE_MEDIUM, diameter=LADLE_DIAMETER)
    o = evaluate(trimmed.as_steel(), medium=LADLE_MEDIUM, diameter=LADLE_DIAMETER)
    off = ld.off_grade_elements(trimmed.composition, LADLE_GRADE)
    cr_floor = ld.GRADE_WINDOWS[LADLE_GRADE].bands["Cr"][0]
    return {
        "landed_Cr": float(trimmed.composition.Cr),
        "landed_Mo": float(trimmed.composition.Mo),
        "on_grade": not off,
        "off_grade": treated.has_defect(ld.OFF_GRADE),
        "off_elements": off,
        "soft_core": treated.has_defect(hs.SOFT_CORE),
        "martensite": float(o.result.martensite),
        "HV": float(o.HV),
        "cr_floor": float(cr_floor),
        "landed_str": f"Cr {trimmed.composition.Cr:.2f} %, Mo {trimmed.composition.Mo:.2f} %",
        "martensite_str": f"{o.result.martensite:.0%} martensite, {o.HV:.0f} HV",
        "grade_verdict": (
            f"on grade — Cr clears the {cr_floor:.2f} % floor of the {LADLE_GRADE} window"
            if not off else
            f"OFF GRADE — {', '.join(off)} outside the {LADLE_GRADE} window (Cr floor {cr_floor:.2f} %)"
        ),
    }


def casting_readout(grade: str, modulus_mm: float) -> dict:
    """F4 casting: cast a billet, read the Scheil centerline enrichment and the front-to-back divergence.

    Casts ``grade`` at the chosen modulus (:func:`~steel.casting.cast_billet` — Chvorinov ``t ∝ M²`` and
    the substitutional-alloy centerline enrichment), then threads *both* the nominal and the segregated
    centerline Heats through :func:`~steel.heat_state.heat_treat`. The centerline inherits an enriched
    composition, so the same casting hardens **non-uniformly** — a harder centerline band the bulk
    misses (uneven hardenability), straight from segregation feeding the back end. All formatting here.
    """
    steel = STEELS[grade]
    section = cast.cast_billet(steel, modulus=modulus_mm / 1000.0)
    nominal_treated = hs.heat_treat(section.nominal_heat, medium=CAST_MEDIUM, diameter=CAST_DIAMETER)
    centerline_treated = hs.heat_treat(section.centerline_heat, medium=CAST_MEDIUM, diameter=CAST_DIAMETER)
    nom_o = evaluate(section.nominal_heat.as_steel(), medium=CAST_MEDIUM, diameter=CAST_DIAMETER)
    ctr_o = evaluate(section.centerline_heat.as_steel(), medium=CAST_MEDIUM, diameter=CAST_DIAMETER)
    ctr = section.centerline_heat.composition
    ratios = {el: getattr(ctr, el) / getattr(steel, el)
              for el in ("Mn", "Si", "Cr", "Mo") if getattr(steel, el) > 0.0}
    return {
        "centerline_ratios": ratios,
        "nominal_HV": float(nom_o.HV),
        "centerline_HV": float(ctr_o.HV),
        "nominal_martensite": float(nom_o.result.martensite),
        "centerline_martensite": float(ctr_o.result.martensite),
        "nominal_soft_core": nominal_treated.has_defect(hs.SOFT_CORE),
        "centerline_soft_core": centerline_treated.has_defect(hs.SOFT_CORE),
        "chvorinov_s": float(section.solidification_time),
        "liquidus_C": float(section.liquidus),
        "band_HV": float(ctr_o.HV - nom_o.HV),
        "ratio_rows": [{"element": el, "centerline ×": f"×{r:.2f}"} for el, r in ratios.items()],
        "chvorinov_str": f"{section.solidification_time:,.0f} s ({section.solidification_time / 60:.1f} min)",
        "band_str": f"{ctr_o.HV - nom_o.HV:+.0f} HV harder centerline band",
        "nominal_str": f"{nom_o.result.martensite:.0%} M, {nom_o.HV:.0f} HV",
        "centerline_str": f"{ctr_o.result.martensite:.0%} M, {ctr_o.HV:.0f} HV",
    }


# --------------------------------------------------------------------------- #
# 2. Figure builders — wrap the banked demo pipelines + plots.* (matplotlib lazy)
# --------------------------------------------------------------------------- #
def reduction_overview_figure():
    """The F1 Ellingham figure — the banked demo arrays through the render layer (matplotlib lazy)."""
    from steel.demo_reduction import compute
    from steel.plots import ellingham_figure
    return ellingham_figure(compute())


def spine_overview_figure():
    """The spine propagation figure — the banked heat-state demo (well vs under-dosed)."""
    from steel.demo_heat_state import compute
    from steel.plots import heat_state_figure
    return heat_state_figure(compute())


def refining_overview_figure():
    """The F2 refining figure — the banked decarb/deox/degas demo arrays."""
    from steel.demo_refining import compute
    from steel.plots import refining_figure
    return refining_figure(compute())


def slag_overview_figure():
    """The F2 slag-partition figure — the banked dephos/desulf demo arrays."""
    from steel.demo_slag import compute
    from steel.plots import slag_figure
    return slag_figure(compute())


def ladle_overview_figure():
    """The F3 trim figure — the banked alloy-to-grade / recovery-shortfall demo arrays."""
    from steel.demo_ladle import compute
    from steel.plots import ladle_figure
    return ladle_figure(compute())


def casting_overview_figure():
    """The F4 casting figure — the banked Scheil-segregation / front-to-back demo arrays."""
    from steel.demo_casting import compute
    from steel.plots import casting_figure
    return casting_figure(compute())


def solidification_compute():
    """The F4 solidification demo object (the app's one heavy compute — memoized by :func:`main`)."""
    from steel.demo_solidification import compute
    return compute()


def solidification_overview_figure(demo):
    """The F4 latent-heat solidification figure — the precomputed demo through the render layer.

    Takes the (memoized) demo so the heavy chill-slab solve runs once per session, not per rerun —
    the one place this app departs from the cheap "compute inside the builder" pattern, the same way
    :mod:`app`'s residual section memoizes its expensive three-solve compute.
    """
    from steel.plots import solidification_figure
    return solidification_figure(demo)


# --------------------------------------------------------------------------- #
# 3. main() — the Streamlit surface (the ONLY place streamlit is imported)
# --------------------------------------------------------------------------- #
def main() -> None:
    """Render the front-end what-if app. Streamlit-only; not unit-tested (ADR 0002 — UI is reach).

    Paper-thin on purpose: every displayed value comes from a tested helper above, so the only
    statements here that can raise are ``st.*`` calls and the figure builders (matplotlib-absent →
    an ``st.info`` hint).
    """
    import streamlit as st

    st.set_page_config(page_title="Steel-making — ore to billet", layout="wide")
    st.title("Steel-making: ore → billet")
    st.caption(
        "A thin what-if skin on the validated **front-end** chain (Steel plan §7) — the twin of the "
        "back-end heat-treatment app. Every number is produced by a model sealed behind its own "
        "validation triad; this UI only turns the knobs (ADR 0002)."
    )

    with st.expander("What is the front end? — the 30-second mental model", expanded=True):
        st.markdown(
            "The back-end app starts from a *finished grade* and asks how to heat-treat it. **This app "
            "is everything that happens first** — how the grade gets made:\n\n"
            "1. **Reduction (F1)** — pull the oxygen off iron ore with carbon (the blast furnace).\n"
            "2. **Refining (F2)** — burn out the carbon, kill the dissolved oxygen, and partition "
            "phosphorus/sulfur into a slag.\n"
            "3. **Ladle trim (F3)** — add the ferroalloys that turn plain iron into the target grade.\n"
            "4. **Casting (F4)** — freeze it into a billet, where segregation is locked in.\n\n"
            "The thread tying them together is one rule: **an upstream mistake propagates** — under-dose "
            "the alloy or miss the trim, and the *same* downstream quench lands a soft core. The back end "
            "is the judge; the front end is where the verdict is decided."
        )

    st.sidebar.header("Front-end stages")
    st.sidebar.markdown(
        "Each section below is an independent stage with its own knobs — there is no single spine knob "
        "(the stages compose by the `Heat` they hand on, not by a shared slider)."
    )
    viz_hint = "Install the figures: `pip install -e .[viz,app]`"

    # ---- F1 — reduction ---------------------------------------------------- #
    st.subheader("F1 · Reduction — can carbon pull the oxygen off iron?")
    T_red = st.slider("Furnace temperature (°C)", int(RED_T_MIN), int(RED_T_MAX), 1200, 25)
    rr = reduction_readout(float(T_red))
    c1, c2, c3 = st.columns(3)
    c1.metric("C→CO free energy", rr["g_carbon"])
    c2.metric("Fe→FeO free energy", rr["g_wustite"])
    c3.metric("Crossover", f"{rr['crossover_C']:.0f} °C")
    (st.success if rr["carbon_reduces_wustite"] else st.warning)(rr["verdict"])
    st.caption(
        f"Oxide stability at {T_red} °C, most stable first (the deoxidizer ladder): "
        + " < ".join(rr["hierarchy_order"])
        + " — the same order F1's Ellingham diagram draws, the order the ladle kill chemistry reads."
    )
    try:
        st.pyplot(reduction_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- the spine --------------------------------------------------------- #
    st.subheader("The spine — an upstream alloy mistake propagates to a downstream defect")
    s1, s2 = st.columns(2)
    Cr = s1.slider("Cr dose on a 4140 (%)", 0.0, 1.20, SPINE_CR_NOMINAL, 0.05)
    Mo = s2.slider("Mo dose on a 4140 (%)", 0.0, 0.30, SPINE_MO_NOMINAL, 0.01)
    sr = spine_readout(Cr, Mo)
    m1, m2 = st.columns(2)
    m1.metric("Core martensite (oil quench)", sr["martensite_str"])
    m2.metric("Core hardness", sr["HV_str"])
    (st.error if sr["soft_core"] else st.success)(sr["verdict"])
    st.caption(
        "Same oil quench, same section — only Cr/Mo differ. The soft-core flag is **not** scripted: it "
        f"is the martensite fraction crossing the {sr['spec_str']} spec, carried on the Heat downstream."
    )
    try:
        st.pyplot(spine_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- F2 — refining (deoxidation) -------------------------------------- #
    st.subheader("F2 · Deoxidation — kill the dissolved oxygen (and why aluminium has a sweet spot)")
    d1, d2 = st.columns(2)
    deox = d1.selectbox("Deoxidizer", DEOX_SYMBOLS, index=0)
    level = d2.slider("Addition level (%)", DEOX_LEVEL_MIN, DEOX_LEVEL_MAX, 0.05, 0.01)
    fr = refining_deox_readout(deox, level)
    o1, o2 = st.columns(2)
    o1.metric(f"Dissolved O after {fr['deox_name']}", fr["oxygen_str"])
    o2.metric("Same, ignoring the interaction", fr["oxygen_cartoon_str"])
    st.caption(
        f"The two differ because the Sigworth–Elliott interaction bends the Al–O curve through a "
        f"**minimum** — {fr['al_min_str']}. Below it, more aluminium re-raises oxygen. "
        f"The C–O product benchmark: [%C][%O] ≈ {fr['co_product']:.4f} (cf. measured BOF/EAF)."
    )
    st.table(fr["hierarchy_rows"])
    try:
        st.pyplot(refining_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- F2 — slag partition ---------------------------------------------- #
    st.subheader("F2 · Slag partition — dephosphorize (oxidizing) and desulfurize (reducing)")
    g1, g2 = st.columns(2)
    slag_name = g1.selectbox("Refining slag", list(SLAGS), index=1)
    o_ppm = g2.slider("Dissolved oxygen for L_S (ppm)", SLAG_O_MIN, SLAG_O_MAX, 30.0, 1.0)
    gr = slag_partition_readout(slag_name, float(o_ppm))
    p1, p2 = st.columns(2)
    p1.metric("Phosphorus partition", gr["L_P_str"])
    p2.metric("Sulfur partition", gr["L_S_str"])
    st.caption(
        f"{gr['basicity_str']} · optical basicity Λ = {gr['optical_basicity']:.2f}. "
        f"{gr['dephos_verdict']}. P removal is *oxidizing* (needs slag FeO), S removal is *reducing* "
        "(needs a killed, low-oxygen bath) — opposite oxygen dependence from independent sources."
    )
    try:
        st.pyplot(slag_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- F3 — ladle trim --------------------------------------------------- #
    st.subheader("F3 · Ladle trim — add the alloys, and recovery decides whether it lands")
    recovery = st.slider("Cr/Mo recovery (fraction of the assumed yield)",
                         LADLE_RECOVERY_MIN, LADLE_RECOVERY_MAX, 1.0, 0.05)
    lr = ladle_trim_readout(float(recovery))
    l1, l2 = st.columns(2)
    l1.metric("Landed alloy", lr["landed_str"])
    l2.metric("At the oil quench", lr["martensite_str"])
    (st.error if lr["off_grade"] else st.success)(lr["grade_verdict"])
    if lr["soft_core"]:
        st.error("…and it soft-cores at the quench — one mistake, two flags (off-grade + soft-core).")
    st.caption(
        "Additions are sized for the assumed recovery; an under-killed bath that under-delivers lands the "
        "heat short. Off-grade is F3's front-end early warning; the soft core is the validated back-end "
        "consequence of the same shortfall."
    )
    try:
        st.pyplot(ladle_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- F4 — casting ------------------------------------------------------ #
    st.subheader("F4 · Casting — freeze the billet, and segregation locks in a hard band")
    modulus_mm = st.slider("Casting modulus V/A (mm)", CAST_MODULUS_MIN_MM, CAST_MODULUS_MAX_MM, 25.0, 1.0)
    cr2 = casting_readout(CAST_GRADE, float(modulus_mm))
    k1, k2, k3 = st.columns(3)
    k1.metric("Solidification time (Chvorinov)", cr2["chvorinov_str"])
    k2.metric("Nominal section", cr2["nominal_str"])
    k3.metric("Segregated centerline", cr2["centerline_str"])
    st.success(
        f"The centerline is a {cr2['band_str']} than the bulk — the same casting hardens non-uniformly, "
        "straight from Scheil segregation feeding the back end."
    )
    st.caption("Scheil centerline enrichment of the substitutional alloys (carbon held at nominal — "
               "Scheil over-predicts interstitial C):")
    st.table(cr2["ratio_rows"])
    try:
        st.pyplot(casting_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- F4 — solidification (the heavy, memoized one) --------------------- #
    st.subheader("F4 · Solidification — the latent-heat field, validated against the Stefan solution")
    if "solidification_demo" not in st.session_state:
        with st.spinner("Solving the chill-slab solidification field…"):
            st.session_state["solidification_demo"] = solidification_compute()
    demo = st.session_state["solidification_demo"]
    f1, f2 = st.columns(2)
    f1.metric("Centre freezes last (with transform)", f"{demo.centre_freeze_on:,.0f} s")
    f2.metric("Conservation residual", f"{demo.conservation_resid:.1e}")
    st.caption(
        "The insulated centre is the last to freeze — the same centerline the casting panel enriches and "
        "the hot spot porosity/hot-tear nucleate in. The moving front is validated against the analytic "
        "one-phase Stefan solution (the figure's overlay); enthalpy is conserved to the residual above."
    )
    try:
        st.pyplot(solidification_overview_figure(demo))
    except ImportError:
        st.info(viz_hint)

    st.markdown("---")
    st.caption(
        "Where the numbers come from: F1 Ellingham (`reduction`), the `Heat` spine (`heat_state`), F2 "
        "refining + slag (`refining`, `slag`), F3 trim (`ladle`), F4 casting + solidification "
        "(`casting`, `solidification`). Each is sealed behind its own validation triad; this surface "
        "adds reach, not physics (ADR 0002). Defect consequences (porosity, flaking, hot-tear, "
        "cold/red-short, temper embrittlement) are a separate slice."
    )


if __name__ == "__main__":
    main()
