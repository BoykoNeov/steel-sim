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
2. **Figure builders** — thin wrappers over the existing :mod:`steel.plots` figures
   (:func:`~steel.plots.four_curves_figure`,
   :func:`~steel.plots.sweep_comparison_figure`), importing matplotlib **lazily**
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
``streamlit run steel/app.py`` executes this file as a **top-level script**
(``__name__ == "__main__"``, no package parent) with ``steel/`` — *not* the repo
root — on ``sys.path``. In that context a relative ``from . import sweep`` raises "no known
parent package" and a bare ``from steel import sweep`` raises ``ModuleNotFoundError``
(``projects`` is not on the path). The demos dodge this by running under ``python -m`` (which
supplies both); ``streamlit run`` supplies neither. So this module puts the repo root on
``sys.path`` first (``parents[1]`` = the repo root, the parent of the ``steel`` package — the
same idiom the demos use for figure paths) and then imports **absolutely**. Under pytest the root
is already on the path, so the insert is a no-op and the test imports the very same module object.

Run it
------
.. code-block:: powershell

    pip install -e .[viz,app]          # matplotlib (viz) + streamlit (app)
    streamlit run steel/app.py

The ``[app]`` extra carries only Streamlit; matplotlib stays in ``[viz]`` (the figures), so
the runnable combo is ``.[viz,app]`` — mirroring the notebook's ``.[viz,notebook]``.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# --- run-as-script bootstrap: put the repo root on sys.path BEFORE the absolute
#     imports below, so `streamlit run app.py` (a top-level script, no package parent)
#     resolves `steel.*`. A no-op under pytest, where the root is already there.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

from steel import austemper as aus
from steel import sweep
from steel import grain
from steel import design
from steel import properties as prop
from steel import unified_kv as ukv
from steel import pathint
from steel import cooling
from steel import jominy
from steel import martemper as mt
from steel import carburize as cb


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

# The austempering (Phase 6d) section's vocabulary — only the atlas-anchored steels are offered
# (per-steel anchoring is the validated content; BC is probe-falsified for cross-steel times, so
# a free-composition austemper slider would be dressing an invalid extrapolation as a knob). The
# hold-temperature slider is clamped inside the Mₛ/Bs window with this margin, so the recipe's
# refuse-guards are programmatically unreachable from the UI (the composition_warnings pattern).
AUSTEMPER_STEELS = list(aus.ATLAS_STEELS)
AUSTEMPER_T_MARGIN = 10.0     # °C inside the (Ms, Bs) window
# Log-ish hold options for the select_slider: the "find the minimum full-transform hold"
# exercise needs fine steps where the action is (minutes), coarse ones in the long tail.
AUSTEMPER_HOLD_OPTIONS = [1, 2, 5, 10, 20, 30, 60, 90, 120, 180, 240, 300, 360, 450, 600,
                          900, 1200, 1800, 2700, 3600]

# §19 unified-KV competing-reaction demonstrator — the two atlas-anchored steels ONLY
# (``unified_system`` raises on anything else: the BC / 8620 cross-composition wall, §6b).
UNIFIED_STEELS = list(aus.ATLAS_STEELS)        # ["1080", "4340"]
# Cooling-rate presets (Newton time constant τ_th, s) spanning the ladder fast → slow, labelled by
# the section/medium they evoke. A select_slider so a drag can't land on a pathological τ; the
# 4340 bay shows up as bainite-dominant at the intermediate steps, 1080 never reaches it.
UNIFIED_COOLING = {
    "very fast — thin water quench": 12.0,
    "fast — oil quench":             150.0,
    "intermediate — air cool":       1200.0,
    "slow — heavy section air cool": 8000.0,
    "very slow — furnace anneal":    60000.0,
}

# The grain / Phase-5 section's carbon cap. Phase 5's Pickering laws describe a ferrite-pearlite
# structure; above the eutectoid (~0.8 %C) a pro-eutectoid cementite network appears and that
# framing breaks, so the carbon slider stops there (cf. the §1 endpoint, which goes hyper-eutectoid
# on purpose). The grain section is the **normalized / slow-cool** regime — its own austenitizing
# and composition knobs, deliberately *not* wired to the sidebar's quench medium (those quench
# toward martensite, which the ferrite-pearlite laws return nan for), the same isolation §3 uses.
GRAIN_C_MAX = 0.80

# The Jominy end-quench (Phase 2) — the two ≈0.4 %C benchmark steels (shallow 1045 vs deep 4140)
# and their published overlays live in :mod:`steel.demo_jominy` (reused, not re-listed). The
# read-depth select_slider walks the standard ASTM-A255 read distances (so a drag lands exactly on
# a sampled point — no interpolation), shared by every steel's traverse.
JOMINY_READ_MM = [round(d * 1000.0, 1) for d in jominy.jominy_distances(16)]

# Martempering (Phase 6e) — the atlas-anchored pair ONLY (the same per-steel wall austempering
# rides; a free-composition martemper slider would dress the probe-falsified cross-steel kinetics
# as a knob). T0 matches demo_martemper's austenitizing temperature.
MARTEMPER_STEELS = list(aus.ATLAS_STEELS)        # ["1080", "4340"]
MARTEMPER_T0 = 850.0

# Residual stress (Phase 6f) — same anchored pair; section size + quench medium are the knobs. The
# three-solve mechanics is the app's ONE expensive compute (~3 s at RESIDUAL_N_T), so main()
# memoizes it in st.session_state keyed on its inputs (recomputing only when they change, not on
# every unrelated rerun). The teeth — the surface-sign reversal and ∫σ=0 — are resolution-robust,
# so the coarser n_t trades figure-smoothness for responsiveness without moving the verdict.
RESIDUAL_STEELS = list(aus.ATLAS_STEELS)
RESIDUAL_MEDIA = ["water", "oil"]                # severe enough to yield the hot core (Biot ≳ 1)
RESIDUAL_N_T = 2000

# Carburizing (Phase 3c) — the mass-diffusion face (an ≈8620, 0.2 %C-core gear; the cb defaults).
# The cycle knobs feed the same transform + property chain as Jominy; constant-D erfc (the
# validated analytic limit). The quench is the standard case-hardening oil/water.
CARBURIZE_MEDIA = ["oil", "water"]


# --------------------------------------------------------------------------- #
# 1. Compute helpers — pure sweep re-composition (no streamlit, no matplotlib)
# --------------------------------------------------------------------------- #
def single_steel_outcomes(grade: str, diameter: float = sweep.STANDARD_DIAMETER) -> list:
    """One grade down the cooling-rate axis (furnace→water) — the mechanism view's data.

    A :func:`sweep.cooling_rate_sweep` for the named grade: four :class:`~steel.sweep.Outcome`
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
    :func:`~steel.properties.tensile_strength_MPa` returns ``nan`` (a glass-hard
    as-quenched martensite has no meaningful tensile number — it fractures first). Say so,
    rather than print a ``nan`` MPa.
    """
    return f"{uts:,.0f} MPa" if math.isfinite(uts) else "off-scale (as-quenched)"


def hardness_readout(outcome) -> dict:
    """Flatten one :class:`~steel.sweep.Outcome` to display-ready strings for the readout.

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
    :func:`sweep.evaluate` of a :class:`~steel.sweep.Steel` assembled from free
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


def grain_outcome(T_austenitize: float, t_hours: float, C: float, Mn: float, Si: float):
    """The grain what-if: an austenitizing hold + composition → the coupled Phase-5 result.

    One :func:`grain.coupled_grain_properties` — austenitize (T, t) → prior-austenite grain (5a) →
    ferrite grain (the calibrated coupling) → Hall–Petch yield + Cottrell–Petch DBTT (5b), with the
    equilibrium pearlite from carbon (1b). This is the **normalized / slow-cool** ferrite-pearlite
    regime those laws describe, isolated at a fixed cooling rate (named) — *not* the quench product
    of the sections above. Mn/Si are the minor-alloy elements Pickering's laws read. Adds no
    physics — a pure re-composition of the validated grain chain, exactly like the other helpers.
    """
    return grain.coupled_grain_properties(
        float(T_austenitize), float(t_hours), float(C), comp={"Mn": float(Mn), "Si": float(Si)},
    )


def grain_readout(gp) -> dict:
    """Display strings for the grain panel — the austenitize → grain → yield + DBTT chain.

    Surfaces the genuinely-new Phase-5 quantities: the prior-austenite and ferrite grain sizes
    (µm + their ASTM E112 numbers), the **yield strength** and **DBTT** the hardness chain
    deliberately withholds, and the one reading that makes DBTT concrete — ductile or brittle at
    room temperature (:data:`grain.ROOM_TEMPERATURE_C`). All formatting lives here, so
    :func:`main` only forwards strings (and reads the ``brittle`` flag for its warning).
    """
    brittle = gp.dbtt_C > grain.ROOM_TEMPERATURE_C
    return {
        "pags": f"{gp.pags_um:.0f} µm  (ASTM G {grain.astm_grain_size_number(gp.pags_um):.1f})",
        "ferrite": f"{gp.ferrite_um:.0f} µm  (ASTM G {grain.astm_grain_size_number(gp.ferrite_um):.1f})",
        "yield": f"{gp.yield_MPa:.0f} MPa",
        "dbtt": f"{gp.dbtt_C:.0f} °C",
        "at_room": "brittle at room temperature" if brittle else "ductile at room temperature",
        "brittle": brittle,
        "f_pearlite": f"{gp.f_pearlite:.0%}",
    }


def austemper_window(steel: str) -> tuple[float, float]:
    """The austempering window ``(Mₛ, Bs)`` (°C) for an anchored steel — the slider bounds.

    ``main()`` clamps the hold-temperature slider :data:`AUSTEMPER_T_MARGIN` inside this window,
    so the recipe's refuse-guards (at/above ``Bs`` the reaction is inert; at/below ``Mₛ`` it is
    martempering) are programmatically unreachable from a drag — the MN_FLOOR pattern.
    """
    r = aus.anchored_reaction(steel)
    s = aus.ATLAS_STEELS[steel]
    return aus.andrews_Ms(**s.comp), r.Bs


def austemper_outcome(steel: str, T_hold: float, t_hold: float) -> aus.AustemperResult:
    """The austempering what-if: an anchored steel + a hold → the Phase-6d recipe result.

    One :func:`austemper.austemper` — instant quench (named), the atlas-anchored bainite hold,
    KM on the remainder, the rule-of-mixtures hardness. Adds no physics — a pure re-composition
    of the validated 6d chain, exactly like the other helpers. The pearlite-race ``UserWarning``
    is suppressed here because the same fact arrives structurally as ``pearlite_race_flagged``
    (surfaced as an ``st.warning`` in :func:`main`) — a console warning per slider drag would be
    noise on top of the structured flag, not information.
    """
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.filterwarnings("ignore", message="high hold", category=UserWarning)
        return aus.austemper(steel, float(T_hold), float(t_hold))


def austemper_readout(r: aus.AustemperResult) -> dict:
    """Display strings for the austempering panel — the hold's products, hardness, and pacing.

    Surfaces the two times the exercise turns on — the model's 50 % time at this hold and the
    **minimum full-transform hold** (shorter holds leave austenite that shears to brittle
    untempered martensite on the cool) — plus the race flag :func:`main` turns into a warning.
    All nan/format logic lives here, so :func:`main` only forwards strings.
    """
    return {
        "bainite": f"{r.bainite:.0%}",
        "martensite": f"{r.martensite:.0%}",
        "retained": f"{r.retained_austenite:.0%}",
        "HV": f"{r.HV:.0f} HV",
        "HRC": format_hrc(r.HRC),
        "dominant": r.dominant().replace("_", " "),
        "t50": f"{aus.hold_time_to_fraction(r.steel, r.T_hold, aus.ATLAS_T50_X):,.0f} s",
        "min_full_hold": f"{aus.minimum_full_hold(r.steel, r.T_hold):,.0f} s",
        "window": f"Mₛ {r.Ms:.0f} °C < hold < Bₛ {r.Bs:.0f} °C",
        "race_flagged": bool(r.pearlite_race_flagged),
        "race_shadow": f"{r.pearlite_shadow:.0%}",
    }


def unified_outcome(steel: str, tau_thermal: float) -> ukv.UnifiedResult:
    """Race the three competing KV reactions down a Newton cool of time-constant ``τ`` (§19).

    One :func:`unified_kv.transform_competing` over a single Newton-cooling path — light (one path
    integration, the [[notebook-kernel-wedge-rootcause]]/advisor discipline: no rate-sweep in a
    live surface). ``steel`` is one of :data:`UNIFIED_STEELS` (the atlas-anchored pair); anything
    else raises in :func:`unified_kv.unified_system` (the cross-steel wall), which the selectbox
    makes unreachable.
    """
    t = pathint.log_time_grid(14.0 * tau_thermal)
    T = pathint.newton_cooling(t, 850.0, 25.0, tau_thermal)
    return ukv.transform_competing(t, T, ukv.unified_system(steel))


def unified_readout(result: ukv.UnifiedResult) -> dict:
    """Display strings for the unified-KV panel — the products, the dominant, the enriched Mₛ."""
    f = result.fractions()
    return {
        "dominant": result.dominant().replace("_", " "),
        "ferrite": f"{f['ferrite']:.0%}",
        "pearlite": f"{f['pearlite']:.0%}",
        "bainite": f"{f['bainite']:.0%}",
        "martensite": f"{f['martensite']:.0%}",
        "retained": f"{f['retained_austenite']:.0%}",
        "C_gamma": f"{result.C_gamma:.2f} %C",
        "Ms_eff": f"{result.Ms_effective:.0f} °C",
        "bay_hit": result.dominant() == "bainite",
    }


def design_outcome(target_HRC: float, tol_HRC: float, diameter_mm: float, t_hours: float = 1.0):
    """The inverse-design what-if: a hardness spec + section size → the feasible recipe set (Phase 7).

    One :func:`design.find_recipes_for_HRC` — search every grade × quench × temper for recipes
    hitting ``target_HRC ± tol_HRC`` in a ``diameter_mm`` section. Adds no physics — a pure
    inversion of the validated forward chain (every recipe is re-checked against the band), exactly
    like the other helpers. Section size is taken in **mm** here (the slider unit) and converted to
    the metres :mod:`design`/:mod:`cooling` use. Imports neither Streamlit nor matplotlib.
    """
    return design.find_recipes_for_HRC(
        float(target_HRC), tol_HRC=float(tol_HRC),
        diameter=float(diameter_mm) / 1000.0, t_hours=float(t_hours))


def design_readout(result, target_HRC: float, tol_HRC: float) -> dict:
    """Display strings for the inverse-design panel — the recommendation + the ranked recipe table.

    Surfaces the spec (in both HRC and the internal HV band), whether it is feasible at all, the
    cheapest recommended recipe with its 0-D-validity honesty flag, and the full feasible set as
    table ``rows`` (label / HV / HRC / cost / 0-D model). All nan/format logic lives here, so
    :func:`main` only forwards strings (and reads the ``feasible``/``recommended_valid`` flags).
    """
    lo, hi = result.target_band
    rec = result.recommended
    rows = [{
        "recipe": r.label(),
        "HV": f"{r.HV:.0f}",
        "HRC": format_hrc(r.HRC),
        "rel. cost": f"{r.cost:.2f}",
        "0-D model": "valid" if r.lumped_valid else "⚠ stretched",
    } for r in result.recipes]
    return {
        "target": f"{target_HRC:.0f} ± {tol_HRC:.0f} HRC",
        "band_HV": f"{lo:.0f}–{hi:.0f} HV",
        "feasible": result.feasible,
        "n": len(result.recipes),
        "recommended": rec.label() if rec is not None else None,
        "recommended_hardness": f"{rec.HV:.0f} HV / {format_hrc(rec.HRC)}" if rec is not None else None,
        "recommended_valid": bool(rec.lumped_valid) if rec is not None else None,
        "rows": rows,
    }


def jominy_traverses(n_cells: int = 200, per_decade: int = 120) -> dict:
    """The benchmark Jominy hardness traverses — shallow 1045 vs deep 4140 (Phase 2).

    A pure re-composition of :func:`steel.demo_jominy.compute` (one shared ASTM-A255 thermal field
    → :func:`steel.properties.jominy_hardness` per steel): returns the demo's ``curves`` dict
    (label → :class:`~steel.properties.JominyHardness`). Imports neither Streamlit nor matplotlib;
    the field solve is light (~0.1 s), so it runs every rerun without the residual section's
    memoizing.
    """
    from steel.demo_jominy import compute

    _, curves = compute(n_cells=n_cells, per_decade=per_decade)
    return curves


def jominy_readout_at(curves: dict, distance_mm: float) -> dict:
    """The hardness each benchmark steel holds at a chosen Jominy depth — the divergence, read out.

    At the quenched end both steels are full ≈0.4 %C martensite (the same HRC — the property model
    in isolation); with distance 4140 holds its deep-hardening plateau while 1045 falls to a soft,
    off-scale ferrite-pearlite tail (the validated hardenability shift). Reads both traverses at the
    standard read point nearest ``distance_mm`` and flattens to display strings (all nan/HRC logic
    here, so :func:`main` only forwards strings).
    """
    rows: dict[str, dict] = {}
    d_read = distance_mm
    for label, h in curves.items():
        i = int(np.argmin(np.abs(h.distance - distance_mm / 1000.0)))
        d_read = h.distance[i] * 1000.0
        rows[label] = {
            "HV": f"{h.HV[i]:.0f} HV",
            "HRC": format_hrc(h.HRC[i]),
            "martensite": f"{h.martensite[i]:.0%}",
        }
    ends = {label: format_hrc(h.HRC[0]) for label, h in curves.items()}
    return {"distance_mm": f"{d_read:.1f} mm", "steels": rows, "quenched_end": ends}


def martemper_outcome(steel: str, diameter_mm: float):
    """The martempering what-if: an anchored steel + plate thickness → the distortion comparison.

    One :func:`steel.martemper.distortion_comparison` (the same slab solved direct-quench vs
    martemper on the frozen heat engine — Phase 6e). ``diameter_mm`` is the full plate thickness
    (the slider unit); the model takes the half-thickness it halves to. Adds no physics — a
    re-composition of the validated 6e chain. Imports neither Streamlit nor matplotlib.
    """
    return mt.distortion_comparison(steel, float(diameter_mm) / 2000.0, T0=MARTEMPER_T0)


def martemper_readout(steel: str, dc) -> dict:
    """Display strings for the martempering panel — the equivalence, the distortion cut, feasibility.

    Surfaces the three falsifiable pieces the demo prints: the **equivalence** (martemper HV = the
    ideal nose-missing quench's HV, exact by construction), the **distortion reduction** (the
    surface−centre ΔT at the Mₛ crossing, cut by ``dc.reduction``×), and the **feasibility** verdict
    (can the section equalise before bainite nucleates — the section-size / hardenability limit).
    All nan/format logic here, so :func:`main` only forwards strings (+ reads ``feasible``).
    """
    iq = mt.ideal_quench(steel)
    r = mt.martemper(steel, T_bath=iq.Ms + 20.0, t_hold=30.0)
    feas = mt.feasibility(steel, dc.half_thickness)
    return {
        "HV": f"{r.HV:.0f} HV",
        "HRC": format_hrc(r.HRC),
        "quench_HV": f"{r.quench_HV:.0f} HV",
        "quench_HRC": format_hrc(r.quench_HRC),
        "gradient_direct": f"{abs(dc.gradient_direct):.0f} °C",
        "gradient_martemper": f"{abs(dc.gradient_martemper):.0f} °C",
        "reduction": f"{dc.reduction:.0f}×",
        "feasible": bool(feas.feasible),
        "margin": "∞" if feas.margin == float("inf") else f"{feas.margin:.1f}×",
        "biot": f"{feas.biot:.2f}",
        "Ms": f"{dc.Ms:.0f} °C",
    }


def residual_solves(steel: str, diameter_mm: float, medium: str, n_t: int = RESIDUAL_N_T):
    """The residual-stress what-if: a steel + plate thickness + quench → the three solved fields.

    A pure re-composition of :func:`steel.demo_residual.compute` (the same plate solved three ways
    on the frozen heat engine — thermal-only OFF, transformation ON, and martemper — Phase 6f),
    returning ``(on, off, marte)``. ``diameter_mm`` is the full plate thickness; ``medium`` indexes
    :data:`steel.cooling.MEDIA` for the quench coefficient. This is the app's one expensive compute
    (three slab + plasticity solves), so :func:`main` memoizes it on its inputs. Imports neither
    Streamlit nor matplotlib.
    """
    from steel.demo_residual import compute

    return compute(steel=steel, half_thickness=float(diameter_mm) / 2000.0,
                   h_quench=cooling.MEDIA[medium], n_t=n_t)


def residual_readout(on, off, marte) -> dict:
    """Display strings for the residual-stress panel — the sign reversal, equilibrium, the route cut.

    Surfaces the headline tooth: the surface goes from **compression** (thermal-only, benign) to
    **tension** (with the martensite dilatation, quench-crack-prone), and martempering **removes**
    that tension; plus the self-equilibrium check (∫σ ∝ mean ≈ 0) and the peak magnitude. All
    sign/format logic here, so :func:`main` only forwards strings (+ reads ``surface_tension``).
    """
    peak = max(abs(on.peak_tension), abs(on.peak_compression)) / 1e6
    return {
        "surface_off": f"{off.surface_MPa:+.0f} MPa",
        "surface_off_kind": "compression — benign" if off.surface_stress < 0 else "tension",
        "surface_on": f"{on.surface_MPa:+.0f} MPa",
        "surface_on_kind": "tension — crack-prone" if on.surface_stress > 0 else "compression",
        "surface_marte": f"{marte.surface_MPa:+.0f} MPa",
        "center_on": f"{on.center_MPa:+.0f} MPa",
        "peak": f"{peak:.0f} MPa",
        "equilibrium": f"{on.mean_stress:.1e} Pa",
        "Ms": f"{on.Ms:.0f} °C",
        "surface_tension": bool(on.surface_stress > 0),
    }


def carburize_outcome(C_surface: float, t_hours: float, T_carburize: float, medium: str):
    """The carburizing what-if: an atmosphere + cycle → the carbon profile and the case traverse.

    Two steps of the Phase-3c mass-mode chain: :func:`steel.carburize.solve_carburize` (the erfc
    carbon profile from the frozen diffusion engine, constant-D analytic limit) →
    :func:`steel.carburize.carburized_traverse` (per-depth transform + property). Returns
    ``(profile, traverse)``; the 0.2 %C ≈8620 core is the library default. Imports neither Streamlit
    nor matplotlib (~0.3 s, so no memoizing needed).
    """
    profile = cb.solve_carburize(C_surface=float(C_surface), C_core=cb.DEFAULT_CORE_CARBON,
                                 T_carburize=float(T_carburize), t_hours=float(t_hours))
    traverse = cb.carburized_traverse(profile, medium=medium)
    return profile, traverse


def carburize_readout(profile, traverse) -> dict:
    """Display strings for the carburizing panel — the case depth, the surface/core split, retained γ.

    Surfaces the case depth two honest ways (to 0.4 %C carbon and to the 50-HRC hardness line), the
    hard-case-over-tough-core hardness split, and the surface retained austenite (the real heavy-case
    effect — reported, not asserted; the surface HRC is read off the martensite *potential*, the case
    as designed). All nan/format logic here, so :func:`main` only forwards strings.
    """
    return {
        "case_depth_C": f"{profile.case_depth(0.4) * 1000.0:.2f} mm",
        "case_depth_HRC": f"{traverse.case_depth_50HRC() * 1000.0:.2f} mm",
        "surface_HRC": format_hrc(traverse.HRC[0]),
        "surface_HV": f"{traverse.HV[0]:.0f} HV",
        "core_HRC": format_hrc(traverse.HRC[-1]),
        "core_HV": f"{traverse.HV[-1]:.0f} HV",
        "retained_surface": f"{traverse.retained_austenite[0]:.0%}",
        "D": f"{profile.D:.2e} m²/s",
    }


# --------------------------------------------------------------------------- #
# 2. Figure builders — thin wrappers over plots.py (matplotlib imported lazily)
# --------------------------------------------------------------------------- #
def mechanism_figure(outcomes: list, grade: str):
    """The Phase-1 anchor figure for one grade: cooling paths on the TTT + microstructure bars.

    Reuses :func:`steel.plots.four_curves_figure` (the plan names it explicitly for
    slice 2). The four outcomes share one ``ccurve`` (composition-determined), so the C-curve
    is taken from the first; each contributes its path, microstructure, and ``(HV, HRC)``.
    Raises ``ImportError`` if matplotlib (the ``[viz]`` extra) is absent — caught in :func:`main`.
    """
    from steel.plots import four_curves_figure

    cc = outcomes[0].ccurve
    paths = [o.path for o in outcomes]
    results = [o.result for o in outcomes]
    hardness = [(o.HV, o.HRC) for o in outcomes]
    title = f"{grade}: one steel, four cooling rates — soft pearlite → hard martensite"
    return four_curves_figure(cc, paths, results, hardness=hardness, title=title)


def comparison_figure(grid: list):
    """The composition × cooling-rate side-by-side (:func:`steel.plots.sweep_comparison_figure`).

    Hardenability curves (martensite vs cooling rate, one line per grade) beside the hardness
    grid. Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import sweep_comparison_figure

    return sweep_comparison_figure(grid)


def custom_figure(outcome):
    """The build-your-own two-panel view: the cooling path across the (alloy-shifted) TTT +
    a schematic microstructure swatch.

    A thin wrapper over :func:`steel.plots.single_steel_figure` — the render layer owns
    the composition, exactly as :func:`mechanism_figure` wraps ``four_curves_figure`` (the app
    invents no figure of its own). The title carries the two hardenability knobs the composition
    moved (Mₛ and the ``tau_factor`` shift). Raises ``ImportError`` without matplotlib — caught
    in :func:`main`.
    """
    from steel.plots import single_steel_figure

    cc = outcome.ccurve
    ttt_title = (f"your steel — the TTT slides right with alloy  "
                 f"(Mₛ {cc.Ms:.0f} °C · hardenability M {cc.tau_factor:.1f}×)")
    return single_steel_figure(cc, outcome.path, outcome.result, ttt_title=ttt_title,
                               schematic_title="microstructure at an oil quench")


def grain_overview_figure(gp, C: float, comp: dict, *, name: str = "", t_hours: float = 1.0):
    """The grain section's two-panel interactive figure — grain growth + the property payoff.

    A thin wrapper over :func:`steel.plots.grain_interactive_figure` (the render layer
    owns the figure; the app invents none of its own — the same discipline as :func:`custom_figure`
    and :func:`mechanism_figure`). Left panel: the grain coarsening with austenitizing T (the new
    length scale + ASTM G); right panel: yield ↑ / DBTT ↓ with the room-temperature service line,
    the current hold marked on both. Raises ``ImportError`` without matplotlib — caught in
    :func:`main`.
    """
    from steel.plots import grain_interactive_figure

    return grain_interactive_figure(gp, C, comp, name=name, t_hours=t_hours)


# The grain swatch uses a FIXED field of view, sized to the coarsest grain the §5 austenitize
# sliders can reach (1250 °C / 8 h — the slider maxima), so dragging the sliders coarsens the
# *picture* (fewer, larger grains), not just a relabelled scale bar — the size-accurate point.
GRAIN_SWATCH_AUST_T_MAX = 1250.0
GRAIN_SWATCH_HOLD_MAX = 8.0


def grain_morphology_overview_figure(gp, *, name: str = "", window_um: float | None = None):
    """The grain section's size-accurate Voronoi swatch — the current ferrite grain, drawn to scale.

    A thin wrapper over :func:`steel.plots.grain_swatch_figure` (the render layer owns the figure;
    the app invents none). The field of view is **fixed** across the austenitize sliders (sized
    from the coarsest grain they can reach, :data:`GRAIN_SWATCH_AUST_T_MAX` / :data:`GRAIN_SWATCH_HOLD_MAX`)
    so refining the grain shows as *more, smaller* grains in the same area — the size-accurate
    point — rather than an identical picture with a different scale bar. Reach, not evidence
    (ADR 0002); complements the §4 phase-fraction schematic, replaces nothing. Raises
    ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import grain_swatch_figure, grain_swatch_window_um

    if window_um is None:
        coarsest = grain.ferrite_grain_size(
            grain.austenite_grain_size(GRAIN_SWATCH_AUST_T_MAX, GRAIN_SWATCH_HOLD_MAX))
        window_um = grain_swatch_window_um(coarsest, target_coarse_cells=7.0)
    return grain_swatch_figure(gp.ferrite_um, window_um=window_um, name=name)


def austemper_overview_figure(steel: str, T_hold: float, t_hold: float):
    """The austempering three-panel view — the Phase-6d demo's own figure, re-aimed at the knobs.

    A thin wrapper over :func:`steel.demo_austemper.compute` +
    :func:`steel.plots.austemper_figure` (the demo's compute pipeline *is* the validated
    arrays; the render layer owns the drawing — the app invents no figure of its own): the
    anchored isothermal diagram with the atlas measurements on it, the hold's completion U(t),
    and hardness vs hold time with the minimum full-transform hold marked. The pearlite-race
    warning is suppressed exactly as in :func:`austemper_outcome` (the flag carries the fact).
    Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.demo_austemper import compute
    from steel.plots import austemper_figure

    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.filterwarnings("ignore", message="high hold", category=UserWarning)
        return austemper_figure(compute(steel, float(T_hold), float(t_hold)))


def unified_overview_figure():
    """The §19 two-panel bay figure — the banked artifact (4340 bay vs 1080 no-bay).

    A thin wrapper over :func:`steel.demo_unified_kv.compute` + :func:`steel.plots.unified_kv_figure`
    (the demo's compute pipeline *is* the validated arrays; the render layer owns the drawing — the
    app invents no figure of its own). Static context for the slider readout: the three competing
    C-curves with the bay open for 4340 and merged for 1080. Raises ``ImportError`` without
    matplotlib — caught in :func:`main`.
    """
    from steel.demo_unified_kv import compute
    from steel.plots import unified_kv_figure

    return unified_kv_figure(compute())


def design_overview_figure(result):
    """The inverse-design two-panel view — the feasibility map + the cost-ranked recipes.

    A thin wrapper over :func:`steel.plots.design_figure` (the render layer owns the figure; the
    app invents none of its own). Rebuilds the as-quenched landscape grid from ``result.diameter``
    over the same grades × media the search used, so the map matches the result it annotates.
    Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import design_figure

    grid = sweep.sweep_grid(list(sweep.STEELS), media=sweep.DEFAULT_MEDIA, diameter=result.diameter)
    return design_figure(result, grid)


def jominy_overview_figure(curves: dict):
    """The Jominy benchmark figure — the model traverses with the published Callister/ASM overlays.

    A thin wrapper over :func:`steel.plots.jominy_hardness_figure` with the published reference
    points from :mod:`steel.demo_jominy` (the render layer owns the drawing; the app invents none).
    Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.demo_jominy import PUBLISHED
    from steel.plots import jominy_hardness_figure

    references = {lbl: (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
                 for lbl, pts in PUBLISHED.items()}
    return jominy_hardness_figure(curves, references=references)


def martemper_overview_figure(dc):
    """The martempering distortion figure — the same slab quenched direct vs martemper (Phase 6e).

    A thin wrapper over :func:`steel.plots.martemper_distortion_figure` (the render layer owns the
    drawing; the app invents none). Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import martemper_distortion_figure

    return martemper_distortion_figure(dc)


def residual_overview_figure(on, off, marte):
    """The residual-stress figure — the plate solved thermal-only / with-transform / martemper (6f).

    A thin wrapper over :func:`steel.plots.residual_stress_figure` (the render layer owns the
    drawing; the app invents none). Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import residual_stress_figure

    return residual_stress_figure(on, off, marte)


def carburize_overview_figure(profile, traverse):
    """The carburized-gradient figure — carbon, microstructure, and hardness vs depth (Phase 3c).

    A thin wrapper over :func:`steel.plots.carburize_figure` (the render layer owns the drawing; the
    app invents none). Raises ``ImportError`` without matplotlib — caught in :func:`main`.
    """
    from steel.plots import carburize_figure

    return carburize_figure(profile, traverse)


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

    with st.expander("⌬ Going deeper — the crystal structures behind the story"):
        st.markdown(
            "Everything above is really a story about **how iron atoms pack** and **where the "
            "carbon goes**. Iron is *allotropic* — it changes crystal structure with temperature:\n\n"
            "| Phase | Structure | Carbon it dissolves | Why |\n"
            "|---|---|---|---|\n"
            "| **Austenite (γ)** | **FCC** — face-centred cubic | up to **2.1 %** | close-packed, but its octahedral holes are *large* — carbon fits |\n"
            "| **Ferrite (α)** | **BCC** — body-centred cubic | only **0.02 %** | looser packing, yet tiny distorted interstices — carbon barely fits |\n"
            "| **Martensite (α′)** | **BCT** — body-centred *tetragonal* | all of it, **trapped** | BCC stretched along one axis by carbon it had no time to reject |\n\n"
            "**This table is the whole hardness story.** You austenitize to reach FCC, which "
            "*dissolves* the carbon. On cooling, iron wants to become BCC ferrite — which **can't "
            "hold that carbon** — so it has to go somewhere, and *how fast you cool decides where*:\n\n"
            "- **Slow** → carbon diffuses out into **cementite (Fe₃C)**; ferrite + cementite "
            "lamellae = **pearlite** (soft).\n"
            "- **Fast** → no time to diffuse; the FCC→BCC shear happens anyway but the carbon stays "
            "**trapped**, stretching the lattice into **BCT martensite**. That trapped carbon + "
            "lattice strain + a high dislocation density is *why martensite is hard*.\n\n"
            "So \"miss the nose → martensite\" is really \"cool too fast for the carbon to "
            "diffuse.\" The TTT C-curve is a **diffusion clock**."
        )

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
        "the middle). The swatch's **areas are the computed phase fractions**; the grain *shapes* "
        "are illustrative. For real grain-*size* physics — yield, DBTT, and the strength-toughness "
        "lever — see the **Grain size** section below."
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

    with st.expander("⚗ Going deeper — what each alloying element actually does"):
        st.markdown(
            "The sliders give you C, Mn, Cr, Mo, Ni — but real steels are designed element by "
            "element. Two families, by *how the atom sits in the iron lattice*:\n\n"
            "- **Interstitial** (small atoms — **C, N**): squeeze into the gaps between iron "
            "atoms. A little goes a long way — large localized lattice strain → strong hardening "
            "per atom. Free **nitrogen** also strengthens but **embrittles** (the `N_free` DBTT "
            "term in the Grain section).\n"
            "- **Substitutional** (Fe-sized — **Mn, Si, Cr, Mo, Ni, V**): *replace* iron atoms. "
            "Milder per atom, but they set **phase stability** and **hardenability**.\n\n"
            "| Element | What it buys you |\n"
            "|---|---|\n"
            "| **C** | the potential hardness (interstitial); austenite stabilizer |\n"
            "| **Mn** | hardenability + deoxidizer; ties up sulfur as MnS; austenite stabilizer |\n"
            "| **Cr** | hardenability + hard carbides (wear); **corrosion resistance** (stainless ≳ 11 %) |\n"
            "| **Mo** | hardenability + **suppresses temper embrittlement** + high-temperature strength |\n"
            "| **Ni** | hardenability + **toughness** (it *lowers* DBTT — opposite of Si); austenite stabilizer |\n"
            "| **Si** | deoxidizer + solid-solution strength, but **raises DBTT** (the Grain-section Si term) |\n"
            "| **V, Nb, Ti** | **grain refinement** + precipitation strengthening (microalloyed HSLA) |\n\n"
            "**Austenite stabilizers** (Ni, Mn, C, N) widen the γ field — push enough (≈ 8 % Ni + "
            "18 % Cr) and you get *austenitic stainless*, FCC even at room temperature. **Ferrite "
            "stabilizers** (Cr, Si, Mo, V, Ti) do the opposite. Note the toughness fork: **Ni "
            "lowers DBTT, Si raises it** — same \"add a substitutional solute\" move, opposite "
            "outcome. The one lever that helps *both* strength and toughness is **grain "
            "refinement** (the Grain section) — exactly what the V/Nb/Ti row buys."
        )

    # ---- section 3b: the Jominy end-quench — hardenability as hardness vs depth (Phase 2) ---- #
    st.subheader("Jominy end-quench — hardness vs depth, shallow 1045 vs deep 4140")
    st.caption(
        "Hardenability made visible the standard way: one ASTM-A255 bar quenched from a single end, "
        "hardness read along its length. Two ≈0.4 %C steels **share the quenched-end hardness** "
        "(both are full martensite there, and ~0.4 %C martensite is ~57 HRC whatever the alloy) and "
        "then **diverge with depth** — deep-hardening **4140** holds a plateau while plain-carbon "
        "**1045** falls to a soft, off-scale ferrite-pearlite tail. Drag the read depth to watch the "
        "gap open. The figure carries published Callister/ASM overlays; the 1045 knee sits a few mm "
        "deep — the documented A₁/A₃ kinetics simplification."
    )
    j_curves = jominy_traverses()
    j_mm = st.select_slider("Read depth from the quenched end (mm)", options=JOMINY_READ_MM,
                            value=JOMINY_READ_MM[min(4, len(JOMINY_READ_MM) - 1)], key="jominy_mm")
    jr = jominy_readout_at(j_curves, j_mm)
    jcols = st.columns(len(jr["steels"]) + 1)
    jcols[0].metric("Read depth", jr["distance_mm"])
    jcols[0].caption("quenched end: "
                     + " · ".join(f"{k} {v}" for k, v in jr["quenched_end"].items()))
    for col, (label, vals) in zip(jcols[1:], jr["steels"].items()):
        col.metric(label, vals["HRC"])
        col.caption(f"{vals['HV']} · {vals['martensite']} martensite")
    try:
        st.pyplot(jominy_overview_figure(j_curves))
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

    # ---- section 5: grain size — the strength-AND-toughness lever (Phase 5) ----- #
    st.subheader("Grain size — the strength-and-toughness lever (Phase 5)")
    st.caption(
        "The one structural length scale the hardness story above never carried. The "
        "**austenitizing hold** (how hot and how long you soak before cooling) grows the austenite "
        "grain; a finer grain seeds a finer **ferrite** grain, which raises **yield strength** "
        "*and* lowers the **ductile-brittle transition temperature (DBTT)** — the lone lever that "
        "improves strength and toughness at once. This is the **normalized / slow-cooled** "
        "ferrite-pearlite regime, with its own knobs below — *not* the quenched parts of the "
        "sections above (those form martensite, which these laws don't describe)."
    )
    gc = st.columns(5)
    aust_T = gc[0].slider("Austenitize (°C)", 850, 1250, 1000, 25)
    aust_t = gc[1].slider("Hold time (h)", 0.25, 8.0, 1.0, 0.25, key="grain_hold")
    gC = gc[2].slider("C %", 0.05, GRAIN_C_MAX, 0.20, 0.05, key="grain_C")
    gMn = gc[3].slider("Mn %", 0.0, 2.0, 0.75, 0.05, key="grain_Mn")
    gSi = gc[4].slider("Si %", 0.0, 1.0, 0.20, 0.05, key="grain_Si")
    gp = grain_outcome(aust_T, aust_t, gC, gMn, gSi)
    gr = grain_readout(gp)
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Ferrite grain size", gr["ferrite"])
    g2.metric("Yield strength σy", gr["yield"])
    g3.metric("DBTT", gr["dbtt"])
    g3.caption(gr["at_room"])
    g4.metric("Prior-austenite grain", gr["pags"])
    if gr["brittle"]:
        st.warning(
            f"At this austenitizing hold the DBTT ({gr['dbtt']}) is **above** room temperature "
            f"({grain.ROOM_TEMPERATURE_C:.0f} °C) — the steel would be brittle in service. Soak "
            "cooler or shorter for a finer grain and a lower DBTT (the over-austenitizing penalty)."
        )
    st.caption(
        f"Equilibrium pearlite {gr['f_pearlite']} from {gC:.2f} %C. The co-benefit and "
        "over-austenitizing **directions** follow by construction from the two cited Pickering "
        "signs — a demonstration, not evidence; Phase 5's only falsifiable teeth are the 5a "
        "grain-growth holdout (ADR 0002: a figure is reach, never proof)."
    )
    try:
        st.pyplot(grain_overview_figure(gp, gC, {"Mn": gMn, "Si": gSi},
                                        name="your steel", t_hours=aust_t))
    except ImportError:
        st.info(viz_hint)
    st.caption(
        "And the current ferrite grain **drawn to scale** — a size-accurate Voronoi swatch. The "
        "field of view is fixed, so a hotter or longer soak shows as *fewer, larger* grains (the "
        "over-austenitizing penalty), not just a relabelled scale bar. Grains-per-area tracks the "
        "ASTM Nₐ(d); the cell shapes are illustrative — it complements the phase-fraction swatch in "
        "§4 above and is not a micrograph."
    )
    swatch_col, _swatch_spacer = st.columns([3, 2])
    try:
        with swatch_col:
            st.pyplot(grain_morphology_overview_figure(gp, name="your steel"))
    except ImportError:
        st.info(viz_hint)

    with st.expander("🔬 Going deeper — why grain refinement uniquely improves both"):
        st.markdown(
            "The headline above — refinement raises strength *and* toughness — comes from grain "
            "boundaries playing **two roles at once**:\n\n"
            "1. **They block dislocations** (the carriers of plastic flow): a dislocation gliding "
            "through a grain piles up at the boundary, and the next grain's misoriented planes "
            "resist it. More boundary area (finer grain) → **higher yield**. That's Hall–Petch, "
            "`σ_y = σ₀ + k·d^(−½)` — the *positive* grain term.\n"
            "2. **They deflect and arrest cleavage cracks** (the carriers of brittle fracture): a "
            "running crack must change direction at every misoriented boundary, which costs "
            "energy. Finer grain → harder to propagate a brittle crack → **lower DBTT** — the "
            "*negative* grain term.\n\n"
            "The *same* feature — grain-boundary area — helps both, which is why grain refinement "
            "escapes the usual strength↔toughness trade-off. Every *other* strengthening lever "
            "(more carbon, more pearlite, solid solution) adds obstacles *inside* the grain — "
            "raising strength but giving cleavage an easier path, so toughness falls.\n\n"
            "**In practice:** keep the austenitizing temperature low (the slider above) and add "
            "**microalloying** — tiny amounts of **V, Nb, Ti** form carbonitride particles that "
            "*pin* the austenite grain boundaries and stop them coarsening during the soak. That "
            "is the design idea behind modern HSLA (high-strength low-alloy) steels — and the "
            "S960MC grade whose grain-growth data calibrates this section's kinetics."
        )

    # ---- section 6: austempering — the isothermal hold route (Phase 6d) ---- #
    st.subheader("Austempering — quench past the nose, hold, and grow bainite (Phase 6d)")
    st.caption(
        "Every recipe above cools *through* the diagram; this one **stops inside it**: quench "
        "into a salt bath between Mₛ and Bₛ, hold until the austenite transforms to **bainite**, "
        "then cool — no brittle as-quenched martensite, no separate temper (springs and clips "
        "are made this way; 1080 is *the* classic austempering steel). The kinetics are the 6b "
        "bainite reaction **anchored per steel to one cited point** of the US Steel 1951 atlas — "
        "the model then predicts that steel's whole 50 %-line (the holdout teeth). Only the two "
        "anchored steels are offered: the probe proved the cited cross-composition arithmetic "
        "wrong-signed, so there is deliberately no build-your-own here. **The exercise:** find "
        "the shortest hold that still fully transforms — every second past it buys nothing, and "
        "every second short of it leaves austenite that shears to brittle martensite on the cool."
    )
    ac = st.columns(3)
    a_steel = ac[0].selectbox("Anchored steel", AUSTEMPER_STEELS, index=0)
    a_Ms, a_Bs = austemper_window(a_steel)
    a_T = ac[1].slider("Hold temperature (°C)",
                       int(math.ceil(a_Ms + AUSTEMPER_T_MARGIN)),
                       int(math.floor(a_Bs - AUSTEMPER_T_MARGIN)),
                       min(343, int(math.floor(a_Bs - AUSTEMPER_T_MARGIN))), 1,
                       key="austemper_T")
    a_t = ac[2].select_slider("Hold time (s)", options=AUSTEMPER_HOLD_OPTIONS, value=600,
                              key="austemper_t")
    a_out = austemper_outcome(a_steel, a_T, a_t)
    ar = austemper_readout(a_out)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Bainite", ar["bainite"])
    a1.caption(f"martensite {ar['martensite']} · retained γ {ar['retained']}")
    a2.metric("Hardness", ar["HV"])
    a2.caption(ar["HRC"])
    a3.metric("50 % transformed at", ar["t50"])
    a4.metric("Minimum full-transform hold", ar["min_full_hold"])
    if ar["race_flagged"]:
        st.warning(
            f"High hold: this close to Bₛ the un-modeled ferrite/pearlite reactions would reach "
            f"~{ar['race_shadow']} during the hold (the single-curve fictitious-time police) — "
            "the bainite-only claim is unreliable here. Hold lower, in the anchored band."
        )
    st.caption(
        f"{ar['window']} · the quench to the hold is idealized instantaneous (named) · claims "
        "stop at the atlas 50 % line; bainite hardness is the carbon-only placeholder, now "
        "load-bearing (under-ranks alloyed bainite — named)."
    )
    try:
        st.pyplot(austemper_overview_figure(a_steel, a_T, a_t))
    except ImportError:
        st.info(viz_hint)

    # ---- section 6b: the unified-KV bay — the competing reactions in CCT (§19) ---- #
    st.subheader("The bainite bay — three competing reactions, opened in continuous cooling (§19)")
    st.caption(
        "Every section above models the diffusional transformation as **one** C-curve (pearlite "
        "above Bₛ, bainite below — the *taught, validated* pipeline that carries the four-curves and "
        "Jominy benchmarks, and works for any composition). This view does something different: it "
        "races **three separate** cited Kirkaldy–Venugopalan reactions — ferrite, pearlite and "
        "bainite — for one austenite pool, so the real **bainite bay** can open. Alloying pushes "
        "the reconstructive ferrite/pearlite noses ~10³× to the right (cited FC/PC factors — the "
        "teeth) while the displacive bainite nose barely moves, leaving a gap an intermediate cool "
        "threads into bainite. **Why it's a separate view, not a replacement:** it is a *per-steel "
        "demonstrator* anchored to the two US-Steel-atlas steels only — the cited cross-composition "
        "bainite arithmetic is wrong-signed (the 8620 wall), it bridges the *isothermal* atlas to "
        "continuous cooling by Scheil additivity with **no measured-CCT validation**, and bainite "
        "hardness is the carbon-only placeholder. Mechanism lens, not a workhorse."
    )
    uc = st.columns(2)
    u_steel = uc[0].selectbox("Atlas-anchored steel", UNIFIED_STEELS,
                              index=UNIFIED_STEELS.index("4340") if "4340" in UNIFIED_STEELS else 0,
                              key="unified_steel")
    u_label = uc[1].select_slider("Cooling rate", options=list(UNIFIED_COOLING),
                                  value="intermediate — air cool", key="unified_cool")
    u_out = unified_outcome(u_steel, UNIFIED_COOLING[u_label])
    ur = unified_readout(u_out)
    u1, u2, u3 = st.columns(3)
    u1.metric("Dominant product", ur["dominant"].title())
    u1.caption(f"ferrite {ur['ferrite']} · pearlite {ur['pearlite']} · bainite {ur['bainite']}")
    u2.metric("Bainite", ur["bainite"])
    u2.caption(f"martensite {ur['martensite']} · retained γ {ur['retained']}")
    u3.metric("Austenite at Mₛ", ur["C_gamma"])
    u3.caption(f"enriched by ferrite → Mₛ {ur['Ms_eff']}")
    if ur["bay_hit"]:
        st.success(
            f"**The bay.** At this cooling rate {u_steel} threads between the pushed-right "
            "ferrite/pearlite noses and the martensite floor → **bainite-dominant** — the "
            "microstructure the single-curve pipeline cannot produce."
        )
    elif u_steel == "1080":
        st.info(
            "1080 (eutectoid, plain carbon) opens **no** bay: its pearlite and bainite noses nearly "
            "coincide, so no continuous cool reaches bainite-dominant. The only route to bulk bainite "
            "here is an isothermal **hold** — which is exactly why austempering (above) exists."
        )
    try:
        st.pyplot(unified_overview_figure())
    except ImportError:
        st.info(viz_hint)
    st.caption(
        "Bainite time base = the per-steel **atlas anchor** (cited absolute time); ferrite/pearlite "
        "separation = the **cited differential** (the teeth); the bay *opening in CCT* is a "
        "demonstration bridged from the isothermal atlas (named). Carbon enrichment from ferrite "
        "lowers the effective Mₛ shown above."
    )

    # ---- section 6c: martempering — same hardness, far less distortion (Phase 6e) ---- #
    st.subheader("Martempering — the same hardness as a direct quench, far less distortion")
    st.caption(
        "Austempering's short-hold sibling: quench into a bath just **above** Mₛ, hold only long "
        "enough to **equalise** the section (well under the bainite clock), then slow-cool through Mₛ "
        "near-uniformly. The microstructure and hardness match a direct quench **point-for-point** "
        "(exact by construction — not a claim that a shallow steel through-hardens a thick part); "
        "what changes is the *spatial* picture at the moment of transformation. The catch is "
        "feasibility: the section must equalise **before** bainite nucleates (τ_eq < t_crit), which "
        "thin / hardenable sections clear and thick ones do not — the textbook section-size limit."
    )
    mc = st.columns(2)
    m_steel = mc[0].selectbox("Anchored steel", MARTEMPER_STEELS, index=0, key="martemper_steel")
    m_mm = mc[1].slider("Plate thickness (mm)", 5, 60, 20, 5, key="martemper_mm")
    m_dc = martemper_outcome(m_steel, m_mm)
    mr = martemper_readout(m_steel, m_dc)
    mm1, mm2, mm3 = st.columns(3)
    mm1.metric("Martemper hardness", mr["HV"])
    mm1.caption(f"{mr['HRC']} · = direct quench {mr['quench_HV']} / {mr['quench_HRC']} (equivalence)")
    mm2.metric("Distortion driver cut", mr["reduction"])
    mm2.caption(f"surface−centre ΔT at Mₛ: direct {mr['gradient_direct']} → "
                f"martemper {mr['gradient_martemper']}")
    mm3.metric("Feasible here?", "yes" if mr["feasible"] else "no — bainite first")
    mm3.caption(f"τ_eq vs t_crit margin {mr['margin']} · Biot {mr['biot']}")
    if not mr["feasible"]:
        st.warning(
            f"At {m_mm} mm, {m_steel} cannot equalise before bainite nucleates — the section is too "
            "thick (or not hardenable enough) to martemper. This is the real limit, not a model "
            "edge: try a thinner section, or the more hardenable steel."
        )
    try:
        st.pyplot(martemper_overview_figure(m_dc))
    except ImportError:
        st.info(viz_hint)
    st.caption(
        "The martemper figure is idealised (a near-uniform slow cool, no transformation plasticity) "
        f"— a best case; t_crit near Mₛ {mr['Ms']} is optimistic, so the feasibility margin is a best "
        "case too. The hardness equivalence itself is exact by construction (a 0-D microstructure "
        "claim), independent of the section size."
    )

    # ---- section 6d: residual stress & distortion on quench — solid mechanics (Phase 6f) ---- #
    st.subheader("Residual stress on quench — why a through-hardened part can crack")
    st.caption(
        "The first **solid-mechanics** view: a plate quenched while it transforms locks in a "
        "self-balancing stress field, read once it has cooled to room temperature. The headline is a "
        "**sign reversal**. With transformation *off* (thermal contraction only) the hot core yields "
        "and pulls the surface into **compression** — benign, even beneficial. Turn transformation "
        "*on* and the austenite→martensite **dilatation** flips the surface to **tension** — the "
        "quench-crack-prone state. **Martempering removes** that surface tension (§6c's distortion "
        "benefit, now in stress). It needs a quench severe enough to yield the hot core (Biot ≳ 1); a "
        "mild quench deforms nothing and leaves nothing."
    )
    rc = st.columns(3)
    r_steel = rc[0].selectbox("Anchored steel", RESIDUAL_STEELS,
                              index=RESIDUAL_STEELS.index("4340") if "4340" in RESIDUAL_STEELS else 0,
                              key="residual_steel")
    r_mm = rc[1].slider("Plate thickness (mm)", 10, 80, 50, 5, key="residual_mm")
    r_medium = rc[2].selectbox("Quench medium", RESIDUAL_MEDIA, index=0, key="residual_medium")
    # The app's one expensive compute (three slab + plasticity solves, ~3 s). Memoize on its own
    # inputs in session_state so it recomputes only when these change — not on every unrelated rerun.
    r_key = (r_steel, r_mm, r_medium)
    if st.session_state.get("_residual_key") != r_key:
        with st.spinner("Solving the quench mechanics (three slab + plasticity solves)…"):
            st.session_state["_residual_val"] = residual_solves(r_steel, r_mm, r_medium)
        st.session_state["_residual_key"] = r_key
    r_on, r_off, r_marte = st.session_state["_residual_val"]
    rr = residual_readout(r_on, r_off, r_marte)
    rm1, rm2, rm3 = st.columns(3)
    rm1.metric("Surface — thermal only", rr["surface_off"])
    rm1.caption(rr["surface_off_kind"])
    rm2.metric("Surface — with transform", rr["surface_on"])
    rm2.caption(rr["surface_on_kind"])
    rm3.metric("Surface — martemper", rr["surface_marte"])
    rm3.caption("tension essentially removed")
    if rr["surface_tension"]:
        st.warning(
            f"Direct quench here leaves the surface in **tension** ({rr['surface_on']}) over a "
            f"compressive core ({rr['center_on']}) — the quench-crack-prone state. Peak |σ| ≈ "
            f"{rr['peak']} (of order the yield base). Martempering removes the surface tension."
        )
    else:
        st.info(
            "This combination does not end with the surface in tension — the quench is too mild (or "
            "the section too thin) to build the transformation stress that drives quench cracking. "
            "Try water, or a thicker section."
        )
    try:
        st.pyplot(residual_overview_figure(r_on, r_off, r_marte))
    except ImportError:
        st.info(viz_hint)
    st.caption(
        f"Self-equilibrium check: ∫σ dx ∝ mean = {rr['equilibrium']} (≈ 0). The teeth are the "
        "**signs**, the equilibrium, and the route ratio — not the absolute MPa (no transformation "
        "plasticity / TRIP; through-hardening only; a single representative yield base)."
    )

    # ---- section 6e: carburizing — case hardening, the mass-diffusion face (Phase 3c) ---- #
    st.subheader("Carburizing — a hard case over a tough core, set by a carbon gradient")
    st.caption(
        "The other face of the same engine: the frozen diffusion solver that cooled the Jominy bar "
        "in *heat* mode now runs in *mass* mode, diffusing carbon **into** the surface of a "
        "low-carbon (≈8620, 0.2 %C) gear held in a carburizing atmosphere, then quenching. The "
        "hardness gradient is set by the **carbon** gradient (one quench throughout, not a "
        "cooling-rate gradient): a hard ~60–65 HRC martensite case over a softer, tougher core. "
        "Surface hardness is read off the martensite **potential** (the case as designed); the "
        "retained austenite the heavy case really carries is reported, not asserted."
    )
    cc = st.columns(4)
    c_pot = cc[0].slider("Carbon potential (%C)", 0.6, 1.1, 0.8, 0.05, key="carb_pot")
    c_hrs = cc[1].slider("Carburize time (h)", 2, 16, 8, 1, key="carb_hrs")
    c_T = cc[2].slider("Temperature (°C)", 880, 960, 925, 5, key="carb_T")
    c_medium = cc[3].selectbox("Quench", CARBURIZE_MEDIA, index=0, key="carb_medium")
    c_profile, c_traverse = carburize_outcome(c_pot, c_hrs, c_T, c_medium)
    cbr = carburize_readout(c_profile, c_traverse)
    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.metric("Case depth (to 50 HRC)", cbr["case_depth_HRC"])
    cm1.caption(f"to 0.4 %C: {cbr['case_depth_C']}")
    cm2.metric("Surface hardness", cbr["surface_HRC"])
    cm2.caption(f"{cbr['surface_HV']} (martensite potential)")
    cm3.metric("Core hardness", cbr["core_HRC"])
    cm3.caption(f"{cbr['core_HV']} — softer, tougher")
    cm4.metric("Surface retained γ", cbr["retained_surface"])
    cm4.caption("the real heavy-case effect")
    try:
        st.pyplot(carburize_overview_figure(c_profile, c_traverse))
    except ImportError:
        st.info(viz_hint)
    st.caption(
        f"Carbon diffusivity D = {cbr['D']} at this temperature; case depth scales with √(D·t) — "
        "double the time for ~1.4× the depth. Constant-D erfc (the validated analytic limit); the "
        "opt-in concentration-dependent D(C) deepens the case toward the published ~1 mm (see the demo)."
    )

    # ---- section 7: inverse design — name a hardness, get a recipe (Phase 7) ---- #
    st.subheader("Inverse design — name a hardness, get the recipe (Phase 7)")
    st.caption(
        "The whole simulator, run **backwards**. Every section above runs the model *forwards* "
        "(steel + quench + temper → hardness); here you name the **target hardness** and **section "
        "size**, and it searches every grade × quench × temper for the recipes that hit it, then "
        "names the cheapest. It adds **no physics** — it just inverts the validated forward chain, "
        "so a recipe is reported only if re-running the forward model lands it back in your band. "
        "An impossible target honestly returns *nothing* — not a near miss."
    )
    dc = st.columns(3)
    d_hrc = dc[0].slider("Target hardness (HRC)", 25, 60, 45, 1, key="design_hrc")
    d_tol = dc[1].slider("Tolerance (± HRC)", 1, 4, 2, 1, key="design_tol")
    d_mm = dc[2].slider("Section size (mm)", 5, 60, 10, 5, key="design_mm")
    d_res = design_outcome(d_hrc, d_tol, d_mm, t_hours=1.0)
    dr = design_readout(d_res, d_hrc, d_tol)
    if not dr["feasible"]:
        st.warning(
            f"No recipe in the {' / '.join(sweep.STEELS)} × quench × temper space reaches "
            f"**{dr['target']}** ({dr['band_HV']}) in a {d_mm} mm section — the target is outside the "
            "achievable envelope. Try a softer target, a smaller section, or a wider tolerance."
        )
    else:
        d1, d2 = st.columns([2, 1])
        d1.metric("Recommended recipe", dr["recommended"])
        d1.caption(dr["recommended_hardness"] + " · " + (
            "0-D model valid" if dr["recommended_valid"]
            else "⚠ 0-D lumped model stretched here (Biot > 0.1) — see the Jominy spatial view"))
        d2.metric("Feasible recipes", f"{dr['n']}")
        st.dataframe(dr["rows"], hide_index=True, width="stretch")
    st.caption(
        "Cost ordering is a transparent convenience (leaner alloy + milder quench + no extra temper "
        "step ⇒ lower) — **not** a validated cost model. A ⚠ recipe needs a quench severe enough "
        "that the 0-D lumped model is stretched at this section size; the bulk hardness is the "
        "0-D section value, *not* a radial profile (that is the Jominy / critical-diameter view)."
    )
    try:
        st.pyplot(design_overview_figure(d_res))
    except ImportError:
        st.info(viz_hint)


if __name__ == "__main__":
    main()
