"""``app_consequences.py`` — the thin Streamlit what-if surface on the **defect consequences**.

The third panel of the triptych. :mod:`app` is the back-end *"cooling curve in, microstructure out"*;
:mod:`app_making` is the front-end *"ore → billet"*; this surface is *"...and here is everything that
goes wrong"* — the consequences the upstream chemistry (P, S, O, H, carbon) comes back to inflict on a
downstream part. It is a **separate** app on purpose (``docs/plans/steel-making.md`` §7, the Slice-1
"separate, not appended" discipline): five of the six defects manifest *downstream of the billet*
(cold-short, red-short, hydrogen flaking, temper embrittlement, tempered-martensite embrittlement), so
they belong to neither the making story nor the heat-treatment story — they are the catalog the gallery
already files under "Impurity consequences (front-end)."

Like :mod:`app` and :mod:`app_making`, it adds **reach, not correctness** (ADR 0002): every verdict it
shows is produced by a model already sealed behind its own validation triad (:mod:`grain`,
:mod:`hot_work`, :mod:`temper_embrittlement`, :mod:`tempered_martensite_embrittlement`,
:mod:`hydrogen_flaking`, :mod:`gas_porosity`, :mod:`hot_tear`), so this module introduces **no new
physics, no new calibration, no new constant**.

Three layers, by the same ADR-0002 discipline :mod:`app` / :mod:`app_making` follow
----------------------------------------------------------------------------------
1. **Compute helpers** (top half) — plain functions that call the consequence modules directly and return
   plain data (readout dicts of display strings + the raw scalars/flags the UI branches and the tests
   assert on). They import **neither** Streamlit **nor** matplotlib, so the module imports on a bare core
   install and the helpers are unit-tested *always-green* (``tests/test_app_consequences.py``).
2. **Figure builders** — thin wrappers over the banked ``demo_*.compute()`` pipelines + the existing
   :mod:`steel.plots` consequence figures, importing matplotlib **lazily**. The app invents **no figure
   of its own** — it reuses the validated demo arrays and the render layer that owns the drawing.
3. **:func:`main`** — the *only* place ``import streamlit`` lives. Kept paper-thin: every value it
   displays is computed/formatted by a tested helper above.

The recurring shape of every panel is the **two-tier** story these consequences share: an upstream stage
sets a flat, single-number **risk** (O > 30 ppm, S > 0.040 %, H > 2 ppm, a J-factor); whether a *part*
actually fails is the **consequence** — carbon-aware, geometry-aware, or segregation-aware — and the two
routinely disagree. Same impurity, the *other* variable decides.

Run it
------
.. code-block:: powershell

    pip install -e .[viz,app]                  # matplotlib (viz) + streamlit (app)
    streamlit run steel/app_consequences.py    # the third app, beside app.py and app_making.py
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

# --- run-as-script bootstrap: repo root on sys.path BEFORE the absolute imports (the app.py idiom).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from steel import gas_porosity as gp
from steel import grain as g
from steel import hot_tear as ht
from steel import hot_work as hw
from steel import hydrogen_flaking as hf
from steel import refining as ref
from steel import slag as sl
from steel import temper_embrittlement as te
from steel import tempered_martensite_embrittlement as tme
from steel.heat_state import COLD_SHORT, Heat, cold_short_check
from steel.hot_work import RED_SHORT, hot_work, red_short_assessment
from steel.sweep import STEELS, Steel, evaluate


# --------------------------------------------------------------------------- #
# 0. The vocabularies — knob bounds and the anchored scenarios each panel rides
# --------------------------------------------------------------------------- #
# Impurity window (cold-short P + red-short S). A low-carbon ferritic-pearlitic structural backbone; the
# knobs are the two tramp impurities P/S and the manganese that ties sulfur as benign MnS (the Mushet lever).
IMPURITY_BACKBONE = replace(STEELS["1045"], C=0.12, Mn=0.50, Si=0.15, P=0.0, S=0.0, name="structural")
NORMALIZE_T, NORMALIZE_HOURS = 900.0, 0.5          # the normalize that sets the ferrite-pearlite structure
SERVICE_T = g.ROOM_TEMPERATURE_C                   # the DBTT is read against room temperature (in the hand)
FORGE_TEMP_C = 1150.0                              # the hot-working temperature (above the 988 °C eutectic)
IMP_P_MIN, IMP_P_MAX = 0.0, 0.45
IMP_MN_MIN, IMP_MN_MAX = 0.05, 1.50
IMP_S_MIN, IMP_S_MAX = 0.0, 0.08

# Temper embrittlement (reversible, alloy-driven P). The classic victim: a dirty 3.3Ni–1.6Cr forging with
# no molybdenum; the knobs are residual P, the Mo cure, the cool rate through the window, and the temper.
TE_BASE = Steel(C=0.40, Mn=0.60, Si=0.30, Ni=3.30, Cr=1.60, Mo=0.0, P=0.012, name="3.3Ni–1.6Cr forging")
TE_P_MIN, TE_P_MAX = 0.002, 0.030
TE_MO_MIN, TE_MO_MAX = 0.0, 0.80
TE_EXPOSURE_MIN, TE_EXPOSURE_MAX = 300.0, 700.0

# Tempered-martensite embrittlement (irreversible, carbon-driven). The knobs: the grade (its carbon) and
# the peak temper temperature; the quench is fixed (oil, 10 mm — 4140 deep-hardens, 8620 stays low-carbon).
# Kept to the lath-martensite (≤ ~0.5 %C) grades the interlath-cementite-film mechanism describes — the
# demo's discriminator set (4140 embrittles, 8620 carbon-gated, 1045 martensitic-gate miss). High-carbon
# *plate*-martensite (1080) also embrittles in the trough but by a related cementite-on-twin-boundary path,
# so it is deliberately excluded: this panel would otherwise attribute the film mechanism to a structure it
# does not describe (the same exclusion demo_tempered_martensite_embrittlement makes).
TME_GRADES = ("4140", "8620", "1045")
TME_MEDIUM, TME_DIAMETER = "oil", 0.010
TME_AUSTENITIZE_T, TME_BATH_T = 850.0, 25.0
TME_TEMPER_MIN, TME_TEMPER_MAX = 150.0, 650.0

# Hydrogen flaking (geometric consequence of dissolved H). A 4140 weakly vacuum-degassed in the ladle to
# ~3–4 ppm (already over the 2 ppm risk limit); the knobs are the section size and the dehydrogenation bake.
HF_GRADE = "4140"
HF_LADLE_VACUUM_ATM = 0.02
HF_BAKE_T = hf.DEFAULT_BAKE_TEMP_C
HF_SECTION_MIN_MM, HF_SECTION_MAX_MM = 12, 1000
HF_BAKE_MIN_H, HF_BAKE_MAX_H = 0.0, 500.0

# Gas (CO) porosity (carbon-aware consequence of dissolved O). The knobs: the grade (its carbon) and the
# aluminium kill level — the deox lever that drops oxygen under the carbon-aware CO line that saves a heat.
GP_GRADES = ("1080", "1045", "8620", "4140")
GP_AL_MIN, GP_AL_MAX = 0.0005, 0.05

# Hot-tearing (segregation-amplified S at the casting stage). A low-carbon cast structural backbone; the
# knobs are sulfur and the manganese whose Mn:S — amplified by Scheil enrichment of the last liquid — decides.
HT_BACKBONE = replace(STEELS["1045"], C=0.18, Mn=0.0, Si=0.30, P=0.0, S=0.0, name="cast structural")
HT_MN_MIN, HT_MN_MAX = 0.05, 2.00
HT_S_MIN, HT_S_MAX = 0.005, 0.10


# --------------------------------------------------------------------------- #
# 1. Compute helpers — pure consequence re-composition (no streamlit, no matplotlib)
# --------------------------------------------------------------------------- #
def impurity_readout(P_pct: float, Mn_pct: float, S_pct: float) -> dict:
    """Cold-short (P) + red-short (S): normalize one heat, read both ends of the workable window.

    Builds a low-carbon structural heat with the chosen phosphorus, manganese and sulfur, then reads the
    two consequences that bracket the temperature window from opposite ends: at the **cold** end, phosphorus
    threads the existing Pickering DBTT law (:mod:`grain`) — when the ductile-brittle transition climbs above
    the service temperature the steel is **cold-short** (brittle in the hand); at the **hot** end, the free
    sulfur manganese did not tie up as MnS forms a Fe–FeS grain-boundary film above the ~988 °C eutectic, so
    the steel is **red-short** when forged. Yield is surfaced as the signed-impurity foil (P strengthens
    *and* embrittles). All formatting here, so :func:`main` only forwards strings (+ reads the two flags).
    """
    comp = replace(IMPURITY_BACKBONE, P=float(P_pct), Mn=float(Mn_pct), S=float(S_pct))
    heat = Heat(composition=comp)
    props = g.coupled_grain_properties(
        NORMALIZE_T, NORMALIZE_HOURS, comp.C, comp=comp.minor(), P_pct=float(P_pct)
    )
    a = red_short_assessment(float(Mn_pct), float(S_pct), FORGE_TEMP_C)
    after = hot_work(cold_short_check(heat, service_T=SERVICE_T), FORGE_TEMP_C)
    cold = after.has_defect(COLD_SHORT)
    red = after.has_defect(RED_SHORT)
    return {
        "dbtt_C": float(props.dbtt_C),
        "yield_MPa": float(props.yield_MPa),
        "free_S": float(a.free_sulfur_pct),
        "mn_s": float(Mn_pct / S_pct) if S_pct > 0 else float("inf"),
        "cold_short": cold,
        "red_short": red,
        "service_T": float(SERVICE_T),
        "eutectic_C": float(hw.FE_FES_EUTECTIC_C),
        "dbtt_str": f"DBTT {props.dbtt_C:+.0f} °C vs {SERVICE_T:+.0f} °C service",
        "free_S_str": f"free S {a.free_sulfur_pct:.3f} % (Mn:S {Mn_pct / S_pct:.1f})" if S_pct > 0
        else "free S 0.000 % (no sulfur)",
        "yield_str": f"{props.yield_MPa:.0f} MPa",
        "cold_verdict": (
            f"COLD-SHORT — brittle in the hand (DBTT {props.dbtt_C:+.0f} °C is above the "
            f"{SERVICE_T:+.0f} °C service temperature)"
            if cold else
            f"ductile at service — DBTT {props.dbtt_C:+.0f} °C sits below {SERVICE_T:+.0f} °C"
        ),
        "red_verdict": (
            f"RED-SHORT — tears when forged ({a.free_sulfur_pct:.3f} % free sulfur films the grain "
            f"boundaries above the {hw.FE_FES_EUTECTIC_C:.0f} °C eutectic)"
            if red else
            "sound when forged — manganese ties the sulfur up as benign MnS (Mushet)"
        ),
    }


def temper_embrittlement_readout(
    P_pct: float, Mo_pct: float, slow_cool: bool, exposure_T_C: float
) -> dict:
    """Reversible temper embrittlement: the J-factor susceptibility and whether this cool embrittles.

    Doses the dirty Ni-Cr forging base (:data:`TE_BASE`) with the chosen residual phosphorus and molybdenum,
    computes the Watanabe **J-factor** (the susceptibility index ``(Mn+Si)(P+Sn)·10⁴``), and runs
    :func:`~steel.temper_embrittlement.temper_embrittlement_check` for the chosen exposure temperature and
    cool rate. The phosphorus drives susceptibility; molybdenum scavenges it (the classic cure); a fast cool
    through the danger window escapes it; a reheat above ~600 °C resets it (the reversibility). All
    formatting here, so :func:`main` only forwards strings (+ reads the flag).
    """
    comp = replace(TE_BASE, P=float(P_pct), Mo=float(Mo_pct))
    J = te.j_factor(comp)
    emb = te.temper_embrittlement_check(
        Heat(composition=comp), exposure_T_C=float(exposure_T_C), slow_cool=bool(slow_cool)
    ).has_defect(te.TEMPER_EMBRITTLED)
    susceptible = J >= te.J_SUSCEPTIBLE
    mo_protected = Mo_pct >= te.MO_SUPPRESSION_PCT
    lo, hi = te.TE_WINDOW_C
    return {
        "J": float(J),
        "j_threshold": float(te.J_SUSCEPTIBLE),
        "susceptible": susceptible,
        "mo_protected": mo_protected,
        "embrittled": emb,
        "window": (float(lo), float(hi)),
        "de_embrittle_T": float(te.DE_EMBRITTLEMENT_C),
        "J_str": f"J = {J:.0f} (susceptible above {te.J_SUSCEPTIBLE:.0f})",
        "window_str": f"{lo:.0f}–{hi:.0f} °C danger window; reheat above {te.DE_EMBRITTLEMENT_C:.0f} °C resets it",
        "verdict": (
            "TEMPER-EMBRITTLED — phosphorus segregated to the prior-austenite boundaries; "
            "the fracture turns intergranular"
            if emb else
            "tough — no embrittling phosphorus segregation on this schedule"
        ),
        "why": (
            "Mo scavenges the phosphorus (the cure)" if mo_protected and not emb else
            "a fast cool skips the danger window" if not slow_cool and not emb and susceptible else
            "low J-factor — not susceptible" if not susceptible else
            "slow cool through the window on a susceptible, Mo-free heat"
        ),
    }


def tme_readout(grade: str, peak_temper_C: float) -> dict:
    """Tempered-martensite embrittlement: harden the grade once, then read the carbon-driven trough.

    Runs the *same frozen back-end quench* the spine uses (:func:`~steel.sweep.evaluate`, fixed oil/10 mm)
    to get the martensite fraction the consequence acts on, then reads
    :func:`~steel.tempered_martensite_embrittlement.tempered_martensite_embrittlement_assessment` at the
    chosen peak temper. The verdict has two gates: enough **carbon** to form the cementite films (8620's
    0.20 %C is exempt even fully hardened) AND a **hardened martensitic** structure (a mild quench that
    never hardened has no tempered martensite). It is **irreversible** — keyed on the peak temper. All
    formatting here, so :func:`main` only forwards strings (+ reads the flag).
    """
    steel = STEELS[grade]
    o = evaluate(steel, medium=TME_MEDIUM, diameter=TME_DIAMETER,
                 austenitize_T=TME_AUSTENITIZE_T, bath_T=TME_BATH_T)
    fM = o.result.martensite
    a = tme.tempered_martensite_embrittlement_assessment(steel, fM, peak_temper_C=float(peak_temper_C))
    lo, hi = tme.TME_WINDOW_C
    return {
        "carbon": float(steel.C),
        "martensite": float(fM),
        "embrittled": bool(a.embrittled),
        "window": (float(lo), float(hi)),
        "recovery_T": float(tme.TME_RECOVERY_C),
        "martensite_str": f"{steel.C:.2f} %C, {fM:.0%} martensite (oil, 10 mm)",
        "window_str": f"the {lo:.0f}–{hi:.0f} °C trough; recovers (one-way) above {tme.TME_RECOVERY_C:.0f} °C",
        "verdict": (
            f"TEMPERED-MARTENSITE EMBRITTLED — cementite films at {peak_temper_C:.0f} °C "
            f"(inside the {lo:.0f}–{hi:.0f} °C trough)"
            if a.embrittled else
            f"tough at a {peak_temper_C:.0f} °C peak temper"
        ),
        "why": (
            f"too little carbon ({steel.C:.2f} %C) for the cementite films" if steel.C < 0.30 and not a.embrittled
            else "no hardened martensite to embrittle" if fM < 0.50 and not a.embrittled
            else f"temper {peak_temper_C:.0f} °C is above the trough — recovered (one-way)"
            if peak_temper_C > hi and not a.embrittled
            else f"temper {peak_temper_C:.0f} °C is below the trough" if peak_temper_C < lo and not a.embrittled
            else "carbon + hardened martensite + a peak temper inside the trough"
        ),
    }


def hydrogen_flaking_readout(section_mm: float, bake_h: float) -> dict:
    """Hydrogen flaking: same ladle hydrogen, the section + bake decide whether a part flakes.

    Vacuum-degasses a 4140 to ~3–4 ppm in the ladle (already carrying refining's ``hydrogen-flaking-risk``),
    casts it into the chosen section, and reads :func:`~steel.hydrogen_flaking.hydrogen_flaking_check` after
    the chosen dehydrogenation bake at ~650 °C. Whether it flakes is an out-diffusion (geometric) question:
    the residual centre hydrogen after a Crank slab desorption, with the dehydrogenation time scaling as
    section². All formatting here, so :func:`main` only forwards strings (+ reads the flag).
    """
    heat = ref.degas(Heat(composition=STEELS[HF_GRADE]), p_H2=HF_LADLE_VACUUM_ATM)
    H0 = heat.hydrogen_ppm
    half_thickness = float(section_mm) / 2e3
    hold_s = float(bake_h) * 3600.0
    out = hf.hydrogen_flaking_check(heat, half_thickness=half_thickness, hold_time_s=hold_s)
    residual = hf.flaking_assessment(H0, half_thickness, hold_time_s=hold_s).residual_centre_ppm
    needed_h = hf.dehydrogenation_time(half_thickness) / 3600.0
    flakes = out.has_defect(hf.HYDROGEN_FLAKING)
    return {
        "ladle_H_ppm": float(H0),
        "critical_ppm": float(hf.CRITICAL_FLAKING_H_PPM),
        "residual_ppm": float(residual),
        "needed_bake_h": float(needed_h),
        "flakes": flakes,
        "ladle_str": f"{H0:.1f} ppm H from the ladle (limit {hf.CRITICAL_FLAKING_H_PPM:.0f} ppm)",
        "residual_str": f"{residual:.2f} ppm at the centre after a {bake_h:.0f} h bake",
        "needed_str": f"this section needs ~{needed_h:.0f} h to degas below the limit",
        "verdict": (
            f"FLAKES — the {section_mm:.0f} mm section traps hydrogen ({residual:.2f} ppm > "
            f"{hf.CRITICAL_FLAKING_H_PPM:.0f} ppm limit); internal hairline cracks"
            if flakes else
            f"sound — the {section_mm:.0f} mm section degassed to {residual:.2f} ppm, under the limit"
        ),
    }


def gas_porosity_readout(grade: str, al_pct: float) -> dict:
    """Gas (CO) porosity: same oxygen spec, the carbon decides whether a casting blows holes.

    Refines a heat honestly (charge → blow to grade carbon → (under-)kill with ``al_pct`` aluminium),
    reads :func:`~steel.gas_porosity.gas_porosity_check`, and surfaces the supersaturation ``S`` against the
    CO equilibrium and the carbon-aware critical oxygen ``O_crit = K_CO/[%C]``. The contrast: a high-carbon
    heat can sit on the CO line and blow holes while carrying *less* oxygen than a sound low-carbon one — the
    carbon, not the oxygen, decides, and refining's flat 30 ppm risk line cannot see it. The aluminium kill
    is the deox lever that saves a high-carbon heat. All formatting here, so :func:`main` only forwards strings.
    """
    h = ref.from_hot_metal(STEELS[grade])
    h = ref.decarburize(h, STEELS[grade].C)
    h = ref.deoxidize(h, "Al", float(al_pct))
    out = gp.gas_porosity_check(h)
    a = gp.porosity_assessment(h.composition.C, h.oxygen_ppm)
    porous = out.has_defect(gp.GAS_POROSITY)
    risk = h.has_defect(ref.POROSITY_RISK)
    return {
        "carbon": float(h.composition.C),
        "oxygen_ppm": float(h.oxygen_ppm),
        "critical_oxygen": float(a.critical_oxygen),
        "supersaturation": float(a.supersaturation),
        "risk_spec_ppm": float(gp.POROSITY_RISK_O_PPM),
        "risk": risk,
        "porous": porous,
        "oxygen_str": f"{h.oxygen_ppm:.0f} ppm O at {h.composition.C:.2f} %C "
                      f"(carbon-aware limit O_crit ≈ {a.critical_oxygen:.0f} ppm)",
        "risk_str": f"refining's flat risk line: O {'>' if risk else '≤'} "
                    f"{gp.POROSITY_RISK_O_PPM:.0f} ppm → {'flagged' if risk else 'cleared'}",
        "verdict": (
            f"POROUS — CO evolves (supersaturation S = {a.supersaturation:.2f} > 1); the casting blows holes"
            if porous else
            f"sound — under the carbon-aware CO line (S = {a.supersaturation:.2f} ≤ 1)"
        ),
    }


def hot_tear_readout(Mn_pct: float, S_pct: float) -> dict:
    """Hot-tearing: same sulfur, the Mn:S in the *last liquid to freeze* decides (segregation-amplified).

    Casts a low-carbon structural heat with the chosen manganese and sulfur and reads
    :func:`~steel.hot_tear.hot_tear_check`. Whether it tears is set by the Mn:S in the **interdendritic
    last liquid** — Scheil enrichment piles sulfur up faster than manganese, so the film Mn:S is far poorer
    than the bath's; a Fe–FeS film forms and tears when the bulk Mn:S falls below the segregation-amplified
    threshold (the stoichiometric 1.71 lifted into the *tens*). The Mushet manganese is the lever, only the
    threshold is much higher than at the forge. All formatting here, so :func:`main` only forwards strings.
    """
    heat = Heat(composition=replace(HT_BACKBONE, Mn=float(Mn_pct), S=float(S_pct)))
    out = ht.hot_tear_check(heat)
    a = ht.hot_tear_assessment(float(Mn_pct), float(S_pct))
    tear = out.has_defect(ht.HOT_TEAR)
    risk = S_pct > sl.MAX_SULFUR_PCT
    critical = ht.critical_bulk_mn_s()
    return {
        "bulk_mn_s": float(a.bulk_mn_s),
        "film_mn_s": float(a.last_liquid_mn_s),
        "stoich": float(ht.MN_S_STOICH),
        "critical_bulk": float(critical),
        "s_spec_pct": float(sl.MAX_SULFUR_PCT),
        "risk": risk,
        "hot_tear": tear,
        "bulk_str": f"bulk Mn:S {a.bulk_mn_s:.1f} → segregated film Mn:S {a.last_liquid_mn_s:.2f}",
        "risk_str": f"slag's flat risk line: S {'>' if risk else '≤'} {sl.MAX_SULFUR_PCT:.3f} % "
                    f"→ {'flagged' if risk else 'cleared'}",
        "verdict": (
            f"HOT-TEARS — the interdendritic film Mn:S {a.last_liquid_mn_s:.2f} falls below "
            f"stoichiometry ({ht.MN_S_STOICH:.2f}); a Fe–FeS film forms in the last liquid"
            if tear else
            f"sound — the film keeps Mn:S {a.last_liquid_mn_s:.2f} above {ht.MN_S_STOICH:.2f} "
            f"(bulk Mn:S clears the segregation-amplified ≈{critical:.0f} threshold)"
        ),
    }


# --------------------------------------------------------------------------- #
# 2. Figure builders — wrap the banked demo pipelines + plots.* (matplotlib lazy)
# --------------------------------------------------------------------------- #
def impurity_window_overview_figure():
    """The cold-short/red-short figure — the banked impurity-window demo through the render layer."""
    from steel.demo_impurity_window import compute
    from steel.plots import impurity_window_figure
    return impurity_window_figure(compute())


def temper_embrittlement_overview_figure():
    """The reversible temper-embrittlement figure — the banked four-levers / reversibility demo."""
    from steel.demo_temper_embrittlement import compute
    from steel.plots import temper_embrittlement_figure
    return temper_embrittlement_figure(compute())


def tme_overview_figure():
    """The tempered-martensite-embrittlement figure — the banked trough / two-gates / irreversibility demo."""
    from steel.demo_tempered_martensite_embrittlement import compute
    from steel.plots import tempered_martensite_embrittlement_figure
    return tempered_martensite_embrittlement_figure(compute())


def hydrogen_flaking_overview_figure():
    """The hydrogen-flaking figure — the banked section/bake desorption demo arrays."""
    from steel.demo_hydrogen_flaking import compute
    from steel.plots import hydrogen_flaking_figure
    return hydrogen_flaking_figure(compute())


def gas_porosity_overview_figure():
    """The gas-porosity figure — the banked carbon-decides demo arrays."""
    from steel.demo_gas_porosity import compute
    from steel.plots import gas_porosity_figure
    return gas_porosity_figure(compute())


def hot_tear_overview_figure():
    """The hot-tear figure — the banked segregation-amplified Mn:S demo arrays."""
    from steel.demo_hot_tear import compute
    from steel.plots import hot_tear_figure
    return hot_tear_figure(compute())


# --------------------------------------------------------------------------- #
# 3. main() — the Streamlit surface (the ONLY place streamlit is imported)
# --------------------------------------------------------------------------- #
def main() -> None:
    """Render the consequences what-if app. Streamlit-only; not unit-tested (ADR 0002 — UI is reach).

    Paper-thin on purpose: every displayed value comes from a tested helper above, so the only statements
    here that can raise are ``st.*`` calls and the figure builders (matplotlib-absent → an ``st.info`` hint).
    """
    import streamlit as st

    st.set_page_config(page_title="Steel defects — what goes wrong", layout="wide")
    st.title("Steel defects: what the chemistry comes back to inflict")
    st.caption(
        "A thin what-if skin on the validated **defect consequences** (Steel plan §14) — the third app, "
        "beside the back-end heat-treatment app and the front-end *ore → billet* app. Every verdict is "
        "produced by a model sealed behind its own validation triad; this UI only turns the knobs (ADR 0002)."
    )

    with st.expander("The two-tier shape every panel shares — the 30-second mental model", expanded=True):
        st.markdown(
            "The making app shows production; the back-end app shows heat-treatment. **This app is "
            "everything that goes wrong** — and every defect here has the same shape:\n\n"
            "1. An **upstream stage sets a flat, single-number risk** — oxygen over 30 ppm, sulfur over "
            "0.040 %, hydrogen over 2 ppm, a J-factor over threshold.\n"
            "2. Whether a *part* actually **fails is the consequence** — and it is *carbon*-aware, "
            "*geometry*-aware, or *segregation*-aware, so it sees what the flat risk line cannot.\n\n"
            "The recurring punchline: **same impurity, the *other* variable decides.** Same oxygen, the "
            "carbon decides porosity. Same hydrogen, the section decides flaking. Same sulfur, the manganese "
            "decides hot-tearing. The risk line and the consequence routinely disagree."
        )

    viz_hint = "Install the figures: `pip install -e .[viz,app]`"

    # ---- Cold-short + red-short (the impurity window) ---------------------- #
    st.subheader("Phosphorus & sulfur — the impurity window (cold-short ↔ red-short)")
    i1, i2, i3 = st.columns(3)
    P = i1.slider("Phosphorus (%)", IMP_P_MIN, IMP_P_MAX, 0.30, 0.01)
    Mn = i2.slider("Manganese (%)", IMP_MN_MIN, IMP_MN_MAX, 0.05, 0.05)
    S = i3.slider("Sulfur (%)", IMP_S_MIN, IMP_S_MAX, 0.05, 0.005)
    ir = impurity_readout(P, Mn, S)
    m1, m2, m3 = st.columns(3)
    m1.metric("Cold end (DBTT)", ir["dbtt_str"])
    m2.metric("Hot end (free sulfur)", ir["free_S_str"])
    m3.metric("Yield (the foil)", ir["yield_str"])
    (st.error if ir["cold_short"] else st.success)(ir["cold_verdict"])
    (st.error if ir["red_short"] else st.success)(ir["red_verdict"])
    st.caption(
        "Phosphorus is the signed-impurity foil: it strengthens the steel **and** embrittles it (raises both "
        "yield and the DBTT), where grain refinement is the lone lever that raises strength while lowering the "
        "DBTT. The two consequences bracket the workable temperature window — brittle below the DBTT at the "
        "cold/service end, red-short above the eutectic at the forge."
    )
    try:
        st.pyplot(impurity_window_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- Temper embrittlement (reversible) -------------------------------- #
    st.subheader("Temper embrittlement — the reversible Ni-Cr phosphorus trap")
    t1, t2 = st.columns(2)
    te_P = t1.slider("Residual phosphorus (%)", TE_P_MIN, TE_P_MAX, 0.020, 0.001)
    te_Mo = t2.slider("Molybdenum (% — the cure)", TE_MO_MIN, TE_MO_MAX, 0.0, 0.05)
    e1, e2 = st.columns(2)
    cool = e1.radio("Cool through the window", ["slow cool (the failure)", "fast cool"], index=0)
    exposure = e2.slider("Exposure / temper temperature (°C)", TE_EXPOSURE_MIN, TE_EXPOSURE_MAX, 500.0, 10.0)
    er = temper_embrittlement_readout(te_P, te_Mo, cool.startswith("slow"), exposure)
    e3, e4 = st.columns(2)
    e3.metric("Susceptibility", er["J_str"])
    e4.metric("Verdict basis", er["why"])
    (st.error if er["embrittled"] else st.success)(er["verdict"])
    st.caption(
        f"The Watanabe J-factor (Mn+Si)(P+Sn)·10⁴ ranks susceptibility; the {er['window_str']}. "
        "Four independent cures: a fast cool, ≈0.5 % molybdenum (it scavenges the phosphorus — why Ni-Cr "
        "forgings get a Mo addition), a clean heat (low J), or a reheat above 600 °C (the reversibility that "
        "names it). No strict tooth — the segregation-nose gate was run on paper and could not be pinned."
    )
    try:
        st.pyplot(temper_embrittlement_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- Tempered-martensite embrittlement (irreversible) ----------------- #
    st.subheader("Tempered-martensite embrittlement — the other trough, carbon-driven & one-way")
    v1, v2 = st.columns(2)
    tme_grade = v1.selectbox("Grade (its carbon)", TME_GRADES, index=0)
    peak = v2.slider("Peak temper temperature (°C)", TME_TEMPER_MIN, TME_TEMPER_MAX, 300.0, 10.0)
    vr = tme_readout(tme_grade, peak)
    w1, w2 = st.columns(2)
    w1.metric("Hardened state", vr["martensite_str"])
    w2.metric("Verdict basis", vr["why"])
    (st.error if vr["embrittled"] else st.success)(vr["verdict"])
    st.caption(
        f"The same frozen quench the spine uses (oil, 10 mm), then a temper into {vr['window_str']}. Two "
        "gates: enough **carbon** for the cementite films (8620's 0.20 %C is exempt even fully hardened) AND "
        "a hardened martensitic structure. It is **carbon-driven** — a *clean* medium-carbon steel still "
        "embrittles, the foil to the reversible (phosphorus) trap — and **irreversible**: the carbide "
        "morphology is set by the *peak* temper, so dropping back into the trough cannot restore the film."
    )
    try:
        st.pyplot(tme_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- Hydrogen flaking (geometric) ------------------------------------- #
    st.subheader("Hydrogen flaking — same ladle hydrogen, the section decides")
    h1, h2 = st.columns(2)
    section = h1.slider("Section size (mm)", HF_SECTION_MIN_MM, HF_SECTION_MAX_MM, 500, 10)
    bake = h2.slider("Dehydrogenation bake (h)", HF_BAKE_MIN_H, HF_BAKE_MAX_H, 48.0, 4.0)
    hr = hydrogen_flaking_readout(section, bake)
    hm1, hm2 = st.columns(2)
    hm1.metric("Ladle hydrogen", hr["ladle_str"])
    hm2.metric("Centre residual", hr["residual_str"])
    (st.error if hr["flakes"] else st.success)(hr["verdict"])
    st.caption(
        f"Whether a part flakes is a *geometric* question, not a number: {hr['needed_str']} — the "
        "dehydrogenation time scales as section², so a thin section degasses in hours while a heavy forging "
        "needs days. The bake is the lever. One genuine tooth: the bake time from an independently-pinned "
        "lattice diffusivity reproduces cited practice (a 500 mm forging → ~10 days) without tuning."
    )
    try:
        st.pyplot(hydrogen_flaking_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- Gas (CO) porosity (carbon-aware) --------------------------------- #
    st.subheader("Gas (CO) porosity — same oxygen spec, the carbon decides")
    p1, p2 = st.columns(2)
    gp_grade = p1.selectbox("Grade (its carbon)", GP_GRADES, index=0)
    al = p2.slider("Aluminium kill (% — the deox lever)", GP_AL_MIN, GP_AL_MAX, 0.0015, 0.0005, format="%.4f")
    pr = gas_porosity_readout(gp_grade, al)
    pm1, pm2 = st.columns(2)
    pm1.metric("Dissolved oxygen", pr["oxygen_str"])
    pm2.metric("Refining's risk line", pr["risk_str"])
    (st.error if pr["porous"] else st.success)(pr["verdict"])
    st.caption(
        "Refining's risk line is carbon-blind (O > 30 ppm). Whether a casting blows CO holes is set by the "
        "carbon the oxygen reacts with: gas evolves where [%C]·[%O] crosses the CO equilibrium. A high-carbon "
        "heat can sit on the line and blow holes while carrying *less* oxygen than a sound low-carbon one — "
        "the carbon decides. A full aluminium kill (the deox lever) drops the oxygen under the line and saves it."
    )
    try:
        st.pyplot(gas_porosity_overview_figure())
    except ImportError:
        st.info(viz_hint)

    # ---- Hot-tearing (segregation-amplified) ------------------------------ #
    st.subheader("Hot-tearing — same sulfur, the Mn:S in the last liquid decides")
    o1, o2 = st.columns(2)
    ht_Mn = o1.slider("Manganese (%)", HT_MN_MIN, HT_MN_MAX, 0.30, 0.05)
    ht_S = o2.slider("Sulfur (%)", HT_S_MIN, HT_S_MAX, 0.030, 0.005)
    or_ = hot_tear_readout(ht_Mn, ht_S)
    n1, n2 = st.columns(2)
    n1.metric("Mn:S, bulk → film", or_["bulk_str"])
    n2.metric("Slag's risk line", or_["risk_str"])
    (st.error if or_["hot_tear"] else st.success)(or_["verdict"])
    st.caption(
        "Slag's risk line is flat and Mn-blind (S > 0.040 %). Whether a casting tears is set by the Mn:S in "
        "the **last liquid to freeze** — Scheil enrichment piles sulfur up faster than manganese, so the "
        "interdendritic film is far poorer than the bath. The Mushet manganese is the lever, only the "
        f"threshold is in the *tens* (bulk Mn:S ≈ {or_['critical_bulk']:.0f}), not 1.71, reproducing the "
        "empirical 'castings need Mn:S ≳ 20' rule."
    )
    try:
        st.pyplot(hot_tear_overview_figure())
    except ImportError:
        st.info(viz_hint)

    st.markdown("---")
    st.caption(
        "Where the numbers come from: cold/red-short (`grain`, `hot_work`), temper embrittlement "
        "(`temper_embrittlement`), tempered-martensite embrittlement "
        "(`tempered_martensite_embrittlement`), hydrogen flaking (`hydrogen_flaking`), gas porosity "
        "(`gas_porosity`), hot-tearing (`hot_tear`). Each is sealed behind its own validation triad; this "
        "surface adds reach, not physics (ADR 0002). Production lives in the *ore → billet* app; "
        "heat-treatment in the back-end app — this is the third panel of the triptych."
    )


if __name__ == "__main__":
    main()
