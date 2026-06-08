"""Microstructure → hardness: the structure-property map (Steel Phase 2c, minimal seed).

Where :mod:`pathint` ends — *a cooling path produces this mixture of constituents* —
this module begins: *that mixture is this hard*. It closes the thermal→kinetic→property
chain for the Jominy artifact, and is the **minimal seed** of the property model that
Phase 3 extends (interlamellar-spacing pearlite, tempering, strength/toughness). v1
maps phase fractions → **hardness only**.

The model: a rule of mixtures over the constituents (the Maynier method)
-----------------------------------------------------------------------
Hardness is taken as the **fraction-weighted mean of the constituent hardnesses**,

    HV = Σ fᵢ · HVᵢ(C)        (i ∈ pearlite, bainite, martensite, retained γ)

This is not an ad-hoc average: it is exactly the structure of the **Maynier (1978)
Jominy-hardness-prediction method** (Maynier, Dollet & Bastien; reproduced in
Bhadeshia & Honeycombe, *Steels*), which predicts a measured Jominy hardness as the
phase-weighted sum of constituent Vickers hardnesses. Naming the structure matters:
the *form* is a published method, not a curve we invented, so what is left to anchor
is only the constituent hardnesses HVᵢ(C) — and those are anchored to **independent**
datasets (below), which is what makes the Jominy benchmark a genuine cross-check
rather than a refit.

Why Vickers (HV) is the internal currency, Rockwell-C only at the boundary
--------------------------------------------------------------------------
The mixing is done in **HV**, then converted to **HRC** for the standard Jominy plot.
Two reasons, both load-bearing:

  * HV is (near-)**linear and additive** across the whole hardness range and is
    *defined for soft material* — a fraction-weighted mean is meaningful in HV. HRC
    is a nonlinear cone-indentation scale that **saturates and is undefined below
    ~20 HRC**, so averaging in HRC would be physically wrong at the soft (pearlitic)
    end of a Jominy bar.
  * The conversion HV→HRC (:func:`vickers_to_rockwell_c`) is a tabulated **ASTM E140**
    standard, accurate only over ~20–65 HRC; below 20 HRC it returns ``nan`` because
    *there is no defined HRC* — which is itself the honest output for soft ferrite-
    pearlite (you quote those in HRB/HB, not HRC). The Jominy benchmark is therefore
    asserted tightly over the hardenability-bearing range (≳ 20 HRC) and the soft far
    tail is reported as "off the HRC scale", not tuned.

Constituent hardnesses — anchored to *independent* published data
-----------------------------------------------------------------
Each HVᵢ(C) is carbon-dominated (carbon is the first-order hardness variable in
steel) and anchored to a dataset that is **not** the Jominy curve this module is
validated against:

  * **Martensite** :func:`vickers_martensite` — a ``√C`` fit to the canonical
    **as-quenched (99.9 %) martensite hardness vs % C** curve (Hodge & Orehoski 1946;
    reproduced in Krauss, *Steels*). A *different experiment* (small fully-martensitic
    specimens, carbon varied) from an end-quench bar, so reproducing the Jominy J1
    hardness is real cross-source agreement. The ``√C`` form captures the curve's
    saturation (rising steeply then flattening toward ~65 HRC by 0.8 % C). This is the
    benchmark-critical sub-model: at the quenched end every steel is full martensite,
    so the hardness there is HVᵢ(C) and nothing else.
  * **Ferrite-pearlite** :func:`vickers_ferrite_pearlite` — a linear-in-C fit to
    **normalized plain-carbon steel hardness vs % C** (ASM handbook ranges: ~140 HV at
    0.2 % C → ~300 HV at 0.8 % C). Again independent of the Jominy data, so the 1045
    far-end hardness the model predicts is a genuine prediction. (:mod:`pathint` labels
    the whole diffusional product "pearlite"; for a hypoeutectoid steel that aggregate
    *is* ferrite + pearlite, which is exactly what this normalized hardness measures.)
  * **Bainite** :func:`vickers_bainite` — an intermediate carbon-dependent value
    (between pearlite and martensite). The **least-anchored** constituent and barely
    exercised by the 1045/4140 benchmark (continuous-cooled, those go essentially
    martensite-or-pearlite); it matters mainly for the four-curves demo's oil path. A
    reasonable placeholder, refined in Phase 3.
  * **Retained austenite** :data:`HV_RETAINED_AUSTENITE` — soft, a small constant; it
    is a minor fraction in these steels and carbon-insensitive at this fidelity.

The Phase-3 extension: Maynier's minor-alloy + cooling-rate terms (a graft)
---------------------------------------------------------------------------
2c's constituent hardnesses were the **moderate-cooling-rate, carbon-only** limit.
Maynier's full equations also carry a **minor-alloy** term (Si/Mn/Ni/Cr/Mo raise each
constituent) and a **cooling-rate** term (faster cooling → finer product → harder).
Phase 3 adds them — but as an honest **graft**, not a wholesale switch to Maynier
(see :func:`vickers_martensite` and the :data:`MAYNIER_ALLOY` block): we keep 2c's
independently-anchored carbon baselines (the load-bearing martensite anchor especially)
and bolt on only Maynier's *non-carbon* deltas, the cooling-rate one **reference-zeroed**
so the 2c value is recovered exactly when no cooling rate is supplied. The new ``comp``
and ``Vr`` arguments are **optional and default to the 2c carbon-only value byte-for-byte**
— so every Phase-2c call (and its frozen benchmark) is unchanged; the new terms fire only
where a caller passes composition / cooling rate (the demos, the case-hardening gradient).
What this buys, flagged honestly:

  * The **minor-alloy term on martensite** closes the gap 2c flagged: 4140's quenched
    end came out ~1 HRC *below* 1045's (0.05 % less C, Cr/Mn boost omitted) where
    published data has them ~equal. With Si/Mn/Cr added it lands ~equal — a concrete
    benchmark *improvement*, not a refit (the carbon anchor is untouched).
  * The **cooling-rate term on ferrite-pearlite** separates furnace- from air-pearlite
    — but for *plain carbon* its slope is only ~10 HV/decade, so the effect is a few HV
    (measured, reported honestly; the coarseness itself is the kinetic ``formation_T``
    distinction, not a large hardness one). It matters more for the soft alloy tails.
  * **Martensite is kept cooling-rate-independent** (its small Maynier ``21·log Vr`` term
    dropped): as-quenched hardness is carbon-set above the critical rate, and this is
    exactly what protects the validated Jominy quenched-end anchor.
  * **Bainite's** alloy/Vr terms are **deferred**: Maynier's bainite coefficients are
    large and fit against his own ``−323+185C`` base, so grafting them onto 2c's
    placeholder baseline gives unphysical (> martensite) hardness. Bainite stays
    carbon-only — still the least-anchored constituent.

**Domain limit of the alloyed model (the bainite-deferral consequence).** Because
ferrite-pearlite gets a minor-alloy boost but bainite does not, the physical ordering
``martensite > bainite > ferrite-pearlite`` (the convex bound the rule of mixtures relies
on) is only guaranteed for **low-to-medium-alloy continuous-cooling steels**. For a heavily
alloyed steel — e.g. a ~2 % Si spring steel, whose FP alloy delta reaches ~130 HV — the
boosted ferrite-pearlite can overtake the un-boosted bainite, under-ranking bainite. This
cannot bite the four-curves demo (carbon-only 1080 → no FP boost) or the 1045/4140 benchmark
(bainite-poor), which is why it is invisible in the green suite; it is the honest edge of the
graft and is resolved only when bainite's own Maynier terms are added (a later phase).

Phase 3b: tempering (Hollomon–Jaffe) + the strength/toughness trade-off
-----------------------------------------------------------------------
Everything above is the **as-quenched** property model. Phase 3b adds the next step every
real quench-hardened part takes — **tempering** — and closes the loop to engineering
properties (section 5 of the code below). The **Hollomon–Jaffe** parameter
``P = T·(C_hj + log10 t)`` (T in kelvin, t in hours) collapses tempering temperature and
time into one number; tempered-martensite hardness is a decreasing master curve ``HV(P)``
running between two **independently-anchored** endpoints — the Phase-3a as-quenched
martensite and the ferrite-pearlite/spheroidite floor — so only the *transition* is
calibrated (the two ``P`` breakpoints, the Phase-3b analogue of Phase-2b's calibrated
``HARDENABILITY_SCALE``). The **validated** content is the parameter's *form*: the
time–temperature **equivalence** (same ``P`` → same hardness, convention-independent), the
monotone softening, and the endpoint bound; the value of ``C_hj`` and the softening
magnitude are *cited / calibrated*, flagged as such (not dressed as a validation). Threading
``comp`` through both endpoints makes an alloy steel resist tempering softening as an
*emergent* consequence (it starts harder and floors higher). Strength is read from the
published **ISO 18265** hardness→tensile-strength conversion (a table, like the E140 one, with
a validity band — it breaks down above ~550 HV, i.e. untempered martensite); toughness is a
deliberately **rough, relative** direction opposite to hardness (no Charpy-J is invented — real
toughness is non-monotone through the tempered-martensite/temper-embrittlement troughs, the
named scope ceiling). Tempering is **martensite-only** here (pearlite barely tempers; a mixed
traverse would temper per-constituent — deferred).

Units & conventions
-------------------
* **Hardness** internally **HV** (Vickers, kgf/mm²); reported **HRC** (Rockwell-C)
  over ~20–65 HRC, ``nan`` outside (HRC undefined there).
* **Carbon** **wt %** (as :mod:`fe_c`/:mod:`kinetics`); **fractions** dimensionless
  ``[0, 1]`` (the :meth:`pathint.TransformResult.fractions` dict — the plan-§5 currency).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import pathint
from .kinetics import CCurve, ABS_ZERO

# --------------------------------------------------------------------------- #
# 1. Constituent hardnesses HVᵢ(C) — each anchored to an independent dataset
# --------------------------------------------------------------------------- #
# Martensite: √C fit to the canonical as-quenched (99.9 %) martensite hardness-vs-%C
# curve (Hodge & Orehoski 1946; Krauss, *Steels*). Anchors: 0.40 % C → ~615 HV (~56 HRC),
# 0.80 % C → ~832 HV (~65 HRC, the saturating plateau). √C captures the sub-linear
# saturation; the coefficients are a two-point fit to that *independent* curve, NOT to
# the Jominy quenched end (which is what makes reproducing J1 a real cross-check).
MART_HV_BASE = 92.0          # HV at C→0 (extrapolated; no real martensite hardening there)
MART_HV_SLOPE = 828.0        # HV per √(wt%) — sets the as-quenched curve's rise

# Ferrite-pearlite: linear-in-C fit to normalized plain-carbon steel hardness vs %C
# (ASM ranges ~140 HV @ 0.2 %C → ~300 HV @ 0.8 %C). Independent of the Jominy data.
FP_HV_BASE = 90.0            # HV at C→0 (soft ferrite)
FP_HV_SLOPE = 260.0          # HV per wt% C (more carbon → more pearlite → harder)

# Bainite: intermediate, carbon-dependent. The least-anchored constituent (barely
# enters the 1045/4140 continuous-cooling benchmark); a reasonable placeholder between
# pearlite and martensite, refined in Phase 3.
BAIN_HV_BASE = 200.0
BAIN_HV_SLOPE = 380.0

# Retained austenite: soft, a small minor fraction; carbon-insensitive at this fidelity.
HV_RETAINED_AUSTENITE = 250.0

# --------------------------------------------------------------------------- #
# 1b. Maynier (1978) minor-alloy + cooling-rate terms — the Phase-3 graft
# --------------------------------------------------------------------------- #
# The canonical Maynier (1978) Vickers equations (Vr = cooling rate at 700 °C in
# °C/h; reproduced e.g. in Scand. J. Metallurgy 33:98, 2004):
#
#   HV_M   = 127 + 949C + 27Si + 11Mn + 8Ni + 16Cr + 21·log10(Vr)
#   HV_B   = -323 + 185C + 330Si + 153Mn + 65Ni + 144Cr + 191Mo
#                 + (89 + 53C - 55Si - 22Mn - 10Ni - 20Cr - 33Mo)·log10(Vr)
#   HV_F+P = 42 + 223C + 53Si + 30Mn + 12.6Ni + 7Cr + 19Mo
#                 + (10 - 19Si + 4Ni + 8Cr + 130V)·log10(Vr)
#
# THE GRAFT (honest scope — *not* "pure Maynier"): we keep 2c's INDEPENDENTLY-anchored
# carbon baselines above (Hodge-Orehoski √C martensite; normalized-plain-carbon linear
# ferrite-pearlite) and bolt on ONLY Maynier's *non-carbon* deltas — the minor-alloy
# contribution and the cooling-rate slope. Maynier fit his alloy/Vr coefficients jointly
# with his own (linear-in-C) carbon terms, so these deltas are borrowed, not derived: a
# defensible teaching graft, not a self-consistent refit. The dicts below hold only the
# non-carbon coefficients; the carbon coefficient is *not* used (our √C / linear baseline
# is). Deliberate omissions (see the module docstring): martensite carries no Vr term
# (cooling-rate-independent — protects the quenched-end anchor), and bainite carries
# neither (its Maynier coefficients are too large to graft onto the placeholder baseline).
MAYNIER_ALLOY = {            # non-carbon composition coefficients (HV per wt%)
    "martensite":       {"Si": 27.0, "Mn": 11.0, "Ni": 8.0, "Cr": 16.0},
    "ferrite_pearlite": {"Si": 53.0, "Mn": 30.0, "Ni": 12.6, "Cr": 7.0, "Mo": 19.0},
}
MAYNIER_VR_SLOPE = {         # cooling-rate slope (HV per decade of Vr); composition-dependent
    "ferrite_pearlite": {"const": 10.0, "Si": -19.0, "Ni": 4.0, "Cr": 8.0, "V": 130.0},
}

# The reference cooling rate (°C/h at 700 °C) the carbon baselines correspond to — a
# representative **normalizing** (air-cool) rate, since the ferrite-pearlite baseline is
# the *normalized* plain-carbon hardness. The Vr term is reference-zeroed about this, so
# Vr = MAYNIER_VR_REF (or Vr = None) recovers the 2c baseline exactly. For plain carbon
# the FP slope is only ~10 HV/decade, so an order-of-magnitude choice here shifts the soft
# pearlite end by just a few HV — it does not manufacture drama.
MAYNIER_VR_REF = 5000.0      # °C/h
SECONDS_PER_HOUR = 3600.0    # K/s → °C/h for callers that measure dT/dt in K/s


def _alloy_delta(constituent: str, comp: dict | None) -> float:
    """Maynier minor-alloy hardness delta (HV) for ``constituent`` given a comp dict.

    ``comp`` maps element symbol → wt% (Si/Mn/Ni/Cr/Mo). ``None`` or empty → 0.0 (the
    2c carbon-only value). Only the elements with a coefficient for this constituent
    contribute; missing elements are zero.
    """
    if not comp:
        return 0.0
    coeffs = MAYNIER_ALLOY.get(constituent, {})
    return sum(coeffs.get(el, 0.0) * comp.get(el, 0.0) for el in coeffs)


def _vr_delta(constituent: str, comp: dict | None, Vr: float | None) -> float:
    """Maynier reference-zeroed cooling-rate delta (HV): ``slope·(log10 Vr − log10 Vr_ref)``.

    ``Vr`` is the cooling rate at 700 °C in **°C/h**; ``None`` → 0.0 (no correction → the
    2c baseline exactly). The slope is composition-dependent for ferrite-pearlite. A
    constituent with no Vr slope (martensite, bainite — deliberately) → 0.0.
    """
    if Vr is None:
        return 0.0
    slope_coeffs = MAYNIER_VR_SLOPE.get(constituent)
    if slope_coeffs is None:
        return 0.0
    comp = comp or {}
    slope = slope_coeffs["const"] + sum(
        c * comp.get(el, 0.0) for el, c in slope_coeffs.items() if el != "const"
    )
    return slope * (math.log10(Vr) - math.log10(MAYNIER_VR_REF))


def vickers_martensite(C: float, comp: dict | None = None, Vr: float | None = None) -> float:
    """As-quenched martensite hardness ``HV = 92 + 828·√C (+ Maynier alloy delta)`` (Vickers).

    The benchmark-critical constituent: at a Jominy quenched end the structure is fully
    martensitic, so the hardness there *is* this value. The carbon term is a ``√C`` fit to
    the canonical as-quenched-martensite-vs-carbon data (Hodge–Orehoski / Krauss) — an
    independent dataset, so hitting the published Jominy J1 hardness is genuine cross-source
    agreement, not a refit. Saturating: ~56 HRC at 0.4 % C, ~65 HRC by 0.8 % C.

    Phase 3 adds the optional **minor-alloy** delta (``comp`` → ``27Si + 11Mn + 8Ni + 16Cr``;
    Maynier's non-carbon martensite coefficients) — this closes the documented 4140≈1045
    quenched-end gap. ``Vr`` is **accepted but ignored**: as-quenched martensite hardness is
    carbon-set above the critical cooling rate, and keeping it cooling-rate-independent is
    what protects the validated quenched-end anchor. With ``comp=None`` the result is the 2c
    carbon-only value exactly.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return MART_HV_BASE + MART_HV_SLOPE * math.sqrt(C) + _alloy_delta("martensite", comp)


def vickers_ferrite_pearlite(C: float, comp: dict | None = None, Vr: float | None = None) -> float:
    """Ferrite-pearlite hardness ``HV = 90 + 260·C (+ Maynier alloy + cooling-rate deltas)``.

    The carbon term is a linear-in-carbon fit to **normalized plain-carbon steel** hardness
    (independent of the Jominy data). :mod:`pathint` lumps the whole diffusional product as
    "pearlite"; for a hypoeutectoid steel that aggregate is ferrite + pearlite, which is what
    this normalized hardness measures.

    Phase 3 adds two optional Maynier deltas: the **minor-alloy** term (``comp`` →
    ``53Si + 30Mn + 12.6Ni + 7Cr + 19Mo``) and the **cooling-rate** term (``Vr`` in °C/h →
    ``(10 − 19Si + 4Ni + 8Cr + 130V)·log10(Vr/Vr_ref)``, reference-zeroed about a normalizing
    rate). For plain carbon the cooling-rate slope is only ~10 HV/decade. With ``comp=None``
    and ``Vr=None`` the result is the 2c carbon-only value exactly — the soft end of the Jominy
    bar, often < 20 HRC where HRC is undefined and the result reported off-scale.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return (FP_HV_BASE + FP_HV_SLOPE * C
            + _alloy_delta("ferrite_pearlite", comp)
            + _vr_delta("ferrite_pearlite", comp, Vr))


def vickers_bainite(C: float, comp: dict | None = None, Vr: float | None = None) -> float:
    """Bainite hardness ``HV = 200 + 380·C`` (Vickers), carbon ``C`` (wt%) — carbon-only.

    Intermediate between ferrite-pearlite and martensite. The least-anchored constituent
    (barely exercised by the continuous-cooled 1045/4140 benchmark, which go essentially
    martensite-or-pearlite). ``comp`` and ``Vr`` are **accepted but ignored**: Maynier's
    bainite alloy/Vr coefficients are large and fit against his own ``−323+185C`` base, so
    grafting them onto this placeholder baseline gives unphysical (> martensite) hardness —
    so the bainite refinement is deliberately deferred (module docstring), and this stays the
    carbon-only placeholder.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return BAIN_HV_BASE + BAIN_HV_SLOPE * C


# Registry: constituent name → hardness HV(C, comp, Vr). Keys match pathint's fractions
# dict, so the rule of mixtures iterates them in lockstep (a missing/extra key is a real
# error). All take the same (C, comp, Vr) signature so the rule of mixtures threads the
# Phase-3 terms uniformly; retained austenite ignores them (a soft constant).
CONSTITUENT_HV = {
    "pearlite": vickers_ferrite_pearlite,
    "bainite": vickers_bainite,
    "martensite": vickers_martensite,
    "retained_austenite": lambda C, comp=None, Vr=None: HV_RETAINED_AUSTENITE,
}


# --------------------------------------------------------------------------- #
# 2. The HV → HRC conversion (ASTM E140), valid ~20–65 HRC
# --------------------------------------------------------------------------- #
# Tabulated ASTM E140 (hardened-steel) Vickers↔Rockwell-C anchor points — used as
# published *reference facts* (not redistributed data), interpolated. Rockwell C is
# undefined below ~20 HRC, so the table stops there; HV outside the range → nan.
_E140_HV = np.array([240.0, 300.0, 392.0, 446.0, 513.0, 595.0, 697.0, 800.0, 900.0])
_E140_HRC = np.array([20.0, 30.0, 40.0, 45.0, 50.0, 55.0, 60.0, 64.0, 67.0])

# Below this HRC the Rockwell-C scale is unreliable/undefined (the memory note, and the
# bottom of the E140 table): a soft ferrite-pearlite Jominy tail is reported off-scale.
RELIABLE_HRC_MIN = 20.0
RELIABLE_HRC_MAX = 67.0


def vickers_to_rockwell_c(HV: float | np.ndarray) -> float | np.ndarray:
    """Convert Vickers ``HV`` → Rockwell-C ``HRC`` via the ASTM E140 table (steel).

    Linear interpolation over the standard E140 hardened-steel conversion points,
    accurate to ~±1 HRC across the ~20–65 HRC band where the benchmark lives. Returns
    ``nan`` where ``HV`` falls outside the table — **deliberately**: below ~240 HV
    (~20 HRC) the Rockwell-C scale is undefined (soft material is quoted in HRB/HB), so a
    ``nan`` is the honest "off the HRC scale", not a failure. Scalar or array in/out.
    """
    HV_arr = np.asarray(HV, dtype=float)
    out = np.interp(HV_arr, _E140_HV, _E140_HRC, left=np.nan, right=np.nan)
    return float(out) if out.ndim == 0 else out


# --------------------------------------------------------------------------- #
# 3. The rule of mixtures: phase fractions (+ carbon) → hardness
# --------------------------------------------------------------------------- #
def hardness_HV(fractions: dict, C: float, comp: dict | None = None, Vr: float | None = None) -> float:
    """Rule-of-mixtures hardness ``HV = Σ fᵢ·HVᵢ(C, comp, Vr)`` (Vickers) — the Maynier method.

    ``fractions`` is the constituent dict (:meth:`pathint.TransformResult.fractions`):
    pearlite / bainite / martensite / retained_austenite, summing to 1. Each constituent
    contributes its Vickers hardness weighted by its fraction. Computed in HV (linear,
    additive, soft-defined); convert with :func:`vickers_to_rockwell_c` or use
    :func:`hardness_HRC`. Unknown constituent keys raise (a fractions/registry mismatch is
    a real error, not a silent zero).

    The optional Phase-3 ``comp`` (minor-alloy wt% dict: Si/Mn/Ni/Cr/Mo/V) and ``Vr``
    (cooling rate at 700 °C, °C/h) thread through to each constituent's Maynier deltas.
    Both default to the **carbon-only** value — so a 2c-style ``hardness_HV(fractions, C)``
    call is byte-identical to before.
    """
    HV = 0.0
    for name, f in fractions.items():
        if name not in CONSTITUENT_HV:
            raise KeyError(f"no hardness model for constituent {name!r}")
        HV += f * CONSTITUENT_HV[name](C, comp, Vr)
    return HV


def hardness_HRC(fractions: dict, C: float, comp: dict | None = None, Vr: float | None = None) -> float:
    """Rule-of-mixtures hardness in **HRC** — :func:`hardness_HV` then ASTM E140.

    ``nan`` when the mixture is softer than ~20 HRC (a pearlitic Jominy tail) — HRC is
    undefined there; read :func:`hardness_HV` for the soft end. ``comp``/``Vr`` are the
    optional Phase-3 minor-alloy / cooling-rate terms (see :func:`hardness_HV`).
    """
    return vickers_to_rockwell_c(hardness_HV(fractions, C, comp, Vr))


# --------------------------------------------------------------------------- #
# 4. The Jominy hardness traverse (the banked Phase-2 artifact's data)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class JominyHardness:
    """A steel's Jominy hardness traverse: hardness vs distance from the quenched end.

    ``distance`` (m, from the quenched end), ``HV`` (Vickers — defined everywhere),
    ``HRC`` (Rockwell-C — ``nan`` where the structure is softer than ~20 HRC), and
    ``martensite`` (the martensite fraction at each point, the hardenability cue that
    explains the curve's shape). All arrays share ``distance``'s length.
    """

    distance: np.ndarray
    HV: np.ndarray
    HRC: np.ndarray
    martensite: np.ndarray
    carbon: float


def jominy_hardness(
    field, ccurve: CCurve, C: float, distances: np.ndarray | None = None,
    comp: dict | None = None, use_cooling_rate: bool = False, T_ref_rate: float = 700.0,
) -> JominyHardness:
    """Hardness vs distance along a Jominy bar — compose thermal → kinetics → property.

    For each sampled distance, take that position's cooling history ``(t, T)`` from the
    thermal ``field`` (any object exposing ``.x`` cell centres and ``.history(i)`` —
    a :class:`~projects.steel.jominy.ThermalField`), integrate it to a microstructure
    with :func:`pathint.transform_along_path` under the steel's ``ccurve`` (which carries
    its hardenability shift), and map the resulting fractions to hardness with the rule
    of mixtures. This is the full Phase-2 chain in one call — the data behind the banked
    hardness-vs-distance artifact and the 1045/4140 benchmark.

    Parameters
    ----------
    field
        The solved thermal field (:func:`~projects.steel.jominy.solve_thermal_field`).
    ccurve
        The steel's TTT curve (:func:`~projects.steel.kinetics.ccurve_for_steel`) — its
        ``tau_factor`` is the validated hardenability shift that makes 4140 harden deeper.
    C
        Carbon content (wt %), the property model's dominant variable.
    distances
        Sample points (m) from the quenched end; defaults to the field's own cell
        centres. Nearest-cell histories are used (no thermal re-interpolation).
    comp
        Optional **Phase-3** minor-alloy composition (wt% dict: Si/Mn/Ni/Cr/Mo/V) for the
        Maynier alloy term. ``None`` → the 2c carbon-only result, byte-identical.
    use_cooling_rate
        Optional **Phase-3** flag: thread each position's cooling rate at ``T_ref_rate``
        (from ``field.cooling_rate``, K/s → °C/h) into the Maynier cooling-rate term.
        ``False`` → no cooling-rate term (the 2c carbon-only result).
    """
    x = np.asarray(field.x, dtype=float)
    if distances is None:
        distances = x
    distances = np.asarray(distances, dtype=float)

    rates_Cph = None
    if use_cooling_rate:
        # Same dT/dt-at-T_ref metric as the 0-D paths (cooling.cooling_rate_through);
        # K/s → °C/h for Maynier's Vr. nan where a position never cools through T_ref.
        rates_Cph = field.cooling_rate(T_ref_rate) * SECONDS_PER_HOUR

    HV = np.empty(distances.size)
    mart = np.empty(distances.size)
    for k, d in enumerate(distances):
        j = int(np.argmin(np.abs(x - d)))          # nearest cell (the array seam)
        t, T = field.history(j)
        result = pathint.transform_along_path(t, T, ccurve)
        Vr = float(rates_Cph[j]) if (rates_Cph is not None and np.isfinite(rates_Cph[j])) else None
        HV[k] = hardness_HV(result.fractions(), C, comp=comp, Vr=Vr)
        mart[k] = result.martensite
    return JominyHardness(
        distance=distances,
        HV=HV,
        HRC=vickers_to_rockwell_c(HV),
        martensite=mart,
        carbon=C,
    )


# --------------------------------------------------------------------------- #
# 5. Tempering (Hollomon–Jaffe) + the strength/toughness trade-off (Phase 3b)
# --------------------------------------------------------------------------- #
# As-quenched martensite is hard but brittle; almost every quench-hardened part is
# then **tempered** — reheated to a moderate temperature for a hold time — to trade
# hardness back for toughness. The **Hollomon–Jaffe (1945)** tempering parameter
# collapses the (temperature, time) trade-off into a SINGLE number:
#
#     P = T·(C_hj + log10 t)            T in KELVIN, t in HOURS
#
# so that any two (T, t) on the same P soften the steel to the *same* hardness — the
# **time–temperature equivalence** that is the whole point of the parameter (a low-T/
# long-t temper substitutes for a high-T/short-t one). Tempered hardness is then a
# master curve HV(P), monotonically **decreasing** in P.
#
# WHAT IS VALIDATED vs WHAT IS CALIBRATED (the non-circularity discipline, as in 2c/2b):
#   * VALIDATED — the parameter's *form*: the equivalence (same P → same hardness), which
#     is **convention-independent** (holds for any carbon and any C_hj); the monotone
#     decrease in both T and t; and the bound between two **independently-anchored
#     endpoints** — as-quenched = the Phase-3a martensite model, the over-tempered floor =
#     the ferrite-pearlite/spheroidite baseline. Only the *transition between* them is
#     calibrated, exactly as the rule of mixtures had anchored endpoints + an independent
#     50 %-martensite criterion for its transition.
#   * CALIBRATED — the value of C_hj (a *cited* literature constant ≈ 20 for low-alloy
#     steel, T in K / t in h — defaulted, not fitted; Hollomon & Jaffe 1945) and the
#     softening *magnitude* (the two P breakpoints below). These are the Phase-3b analogue
#     of Phase-2b's HARDENABILITY_SCALE: a calibrated knob, NOT a fit dressed as a
#     validation. The breakpoints are set so the curve reproduces the well-known 1 h
#     tempering response of ~0.4 %C martensite (Grange/ASM tempering charts: high-50s HRC
#     as-quenched → low-40s at 400 °C → ~30 at 600 °C) — asserted only with *loose* sanity
#     bands, the calibrated claim held loosely the way the 1045 knee position was.
#
# Strength & toughness close the property loop (plan §3, "a rough strength/toughness
# trade-off"): tensile strength is read from the published hardness↔strength conversion;
# toughness is the *opposite* of hardness — a deliberately ROUGH, relative direction (no
# Charpy-J number is invented — real toughness is steel/heat-specific and non-monotone,
# see :func:`toughness_index`).

# The Hollomon–Jaffe constant C_hj (T in K, t in hours). ≈ 20 for low-alloy steels — a
# CITED literature value (Hollomon & Jaffe 1945), defaulted not fitted. It is mildly
# carbon-dependent in the original work; that is left to the caller as an optional C_hj
# override rather than baked in with unverifiable coefficients (only the parameter's
# *form* is validated here, not the value of the constant).
HJ_CONSTANT = 20.0

# The two CALIBRATED breakpoints of the fractional-softening master curve g(P). Below
# onset the structure is essentially as-quenched (g = 1); above the over-tempered point
# it has softened to the spheroidized floor (g = 0). Chosen (~150 °C and ~700 °C at 1 h)
# so the curve matches the well-known ~0.4 %C tempering response — a calibrated magnitude,
# the Phase-3b analogue of HARDENABILITY_SCALE, NOT a benchmark fit.
P_TEMPER_ONSET = 8500.0       # ≈ 150 °C / 1 h — softening begins
P_OVERTEMPERED = 19500.0      # ≈ 700 °C / 1 h — fully over-tempered (spheroidite floor)


def hollomon_jaffe_parameter(T_temper: float, t_hours: float, C_hj: float = HJ_CONSTANT) -> float:
    """Hollomon–Jaffe tempering parameter ``P = T·(C_hj + log10 t)`` (``T`` in **kelvin**).

    ``T_temper`` is the tempering temperature in **°C** (converted to kelvin internally —
    the Arrhenius-like form needs absolute ``T``); ``t_hours`` the hold time in **hours**;
    ``C_hj`` the Hollomon–Jaffe constant (≈ 20 for low-alloy steel — a cited value,
    defaulted not fitted). The load-bearing property is the **time–temperature
    equivalence**: two (T, t) with equal ``P`` give equal tempered hardness, so a
    high-T/short-t temper trades for a low-T/long-t one. ``P`` rises with both ``T`` and
    ``t``; larger ``P`` ⇒ more tempering ⇒ softer.
    """
    if t_hours <= 0.0:
        raise ValueError(f"tempering time must be > 0 hours, got {t_hours}")
    T_K = T_temper + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"tempering temperature must be above absolute zero, got {T_temper} °C")
    return T_K * (C_hj + math.log10(t_hours))


def _temper_softening(P: float) -> float:
    """Fractional retained hardening ``g(P) ∈ [0, 1]`` — the master curve (1 = as-quenched, 0 = floor).

    Linear in ``P`` between the calibrated onset / over-tempered breakpoints, clamped. The
    *shape* (linear) is a teaching approximation; the validated content is the
    **equivalence** — that ``g`` depends on ``(T, t)`` only through ``P`` — not this curve's
    exact form.
    """
    g = (P_OVERTEMPERED - P) / (P_OVERTEMPERED - P_TEMPER_ONSET)
    return min(1.0, max(0.0, g))


def tempered_martensite_HV(
    C: float, T_temper: float, t_hours: float, comp: dict | None = None,
    C_hj: float = HJ_CONSTANT,
) -> float:
    """Tempered-martensite hardness (HV) after tempering ``t_hours`` h at ``T_temper`` °C.

    Tempers a **fully martensitic** as-quenched structure (the practically relevant case:
    quench to martensite, then temper). The hardness moves down the master curve between
    two **independently-anchored** endpoints:

        HV(P) = HV_floor + (HV_aq − HV_floor)·g(P)

      * ``HV_aq``   — as-quenched martensite (:func:`vickers_martensite`, the Phase-3a model),
      * ``HV_floor`` — the over-tempered / spheroidized floor, taken as the ferrite-pearlite
        baseline (:func:`vickers_ferrite_pearlite`); spheroidite is in fact a little softer,
        so this is a slightly **conservative** (won't over-soften) floor,
      * ``g(P)``    — the calibrated fractional-softening master curve (:func:`_temper_softening`),
        with ``P`` the Hollomon–Jaffe parameter (:func:`hollomon_jaffe_parameter`).

    Both endpoints carry the optional ``comp`` minor-alloy term, so an alloy steel both
    **starts harder and keeps a higher floor** — it resists tempering softening, the real
    alloy temper-resistance, as an *emergent consequence* of the two anchored endpoints (not
    a separate fitted term). With ``comp=None`` it is the plain-carbon response.

    **Scope (deliberate):** martensite-only. Pearlite/ferrite are near-equilibrium and barely
    temper, so a *mixed* Jominy traverse would have to be tempered **per-constituent** (soften
    the martensite, leave the pearlite) — that integration is deferred. This models the
    quench-and-temper part, not 'tempered pearlite'.
    """
    HV_aq = vickers_martensite(C, comp=comp)
    HV_floor = vickers_ferrite_pearlite(C, comp=comp)
    P = hollomon_jaffe_parameter(T_temper, t_hours, C_hj=C_hj)
    g = _temper_softening(P)
    # Return the anchored endpoints *exactly* in the clamped regions (g is exactly 1.0 below
    # onset / 0.0 above the over-tempered breakpoint) — so the seam "a negligible temper is
    # byte-for-byte the as-quenched model" is exact by construction, not float round-trip luck.
    if g >= 1.0:
        return HV_aq
    if g <= 0.0:
        return HV_floor
    return HV_floor + (HV_aq - HV_floor) * g


# --------------------------------------------------------------------------- #
# 5b. Strength: the published hardness → tensile-strength conversion (ISO 18265)
# --------------------------------------------------------------------------- #
# ISO 18265 / ASTM A370 hardness↔tensile-strength conversion for steel (HV → UTS MPa),
# interpolated exactly like the E140 hardness table above. The standard correlation
# ``UTS[MPa] ≈ 3.3·HV`` holds across the soft-to-medium range but **degrades above
# ~550 HV** — as-quenched, untempered martensite is precisely where the linear hardness–
# strength relation is least valid — so the table stops there and returns ``nan`` outside
# its band (the honest "out of the correlation's range", mirroring
# :func:`vickers_to_rockwell_c`). Published reference facts, interpolated, not redistributed.
_UTS_HV = np.array([150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0])
_UTS_MPA = np.array([480.0, 640.0, 800.0, 950.0, 1115.0, 1290.0, 1465.0, 1660.0, 1845.0])

RELIABLE_UTS_HV_MIN = 150.0
RELIABLE_UTS_HV_MAX = 550.0


def tensile_strength_MPa(HV: float | np.ndarray) -> float | np.ndarray:
    """Ultimate tensile strength (MPa) from Vickers ``HV`` via the ISO 18265 steel table.

    Linear interpolation over the standard steel hardness↔strength conversion (≈ ``3.3·HV``
    across the band). Returns ``nan`` below ~150 HV and above ~550 HV — outside the
    correlation's validity: above ~550 HV (untempered martensite) the linear relation breaks
    down, so a ``nan`` there is the honest "this conversion does not apply", not a clamp.
    Scalar or array in/out.

    Yield strength is **not** returned: it is a rough ~0.6–0.9·UTS for tempered steels and is
    not a clean function of hardness (Tabor's ``H ≈ 3σ`` relates hardness to *flow stress*,
    not yield) — reporting it as a function would over-claim.
    """
    HV_arr = np.asarray(HV, dtype=float)
    out = np.interp(HV_arr, _UTS_HV, _UTS_MPA, left=np.nan, right=np.nan)
    return float(out) if out.ndim == 0 else out


# --------------------------------------------------------------------------- #
# 5c. Toughness: the rough strength/toughness trade-off (a relative direction)
# --------------------------------------------------------------------------- #
# Toughness rises as hardness/strength falls — the strength/toughness trade-off tempering
# exploits. This maps HV onto a dimensionless, RELATIVE index in [0, 1] (1 = soft & tough,
# 0 = fully hard & brittle), linearly between two reference hardnesses. It is deliberately a
# *direction*, not an absolute Charpy energy: a real impact-toughness curve is steel/heat-
# specific AND **non-monotone** — tempered-martensite embrittlement (~260–370 °C) and
# temper embrittlement (~375–575 °C, alloy steels) cut toughness troughs this monotone proxy
# does not model. That non-monotonicity is the named scope ceiling of the trade-off here.
TOUGH_HV_TOUGH = 200.0        # ≲ this HV: soft, fully tough (index → 1)
TOUGH_HV_BRITTLE = 600.0      # ≳ this HV: fully hard, brittle (index → 0)


def toughness_index(HV: float | np.ndarray) -> float | np.ndarray:
    """Relative toughness — dimensionless ``[0, 1]``, **high when soft, low when hard**.

    The strength/toughness trade-off as a *direction*: ``1`` at/below ~200 HV (soft,
    tough), ``0`` at/above ~600 HV (fully hard, brittle), linear between (clamped). This is
    **not** a Charpy energy — no absolute J value is invented, because real impact toughness
    is steel/heat-specific and, crucially, **non-monotone** (the embrittlement troughs named
    above). Use it for the *trade-off* (it must move opposite to :func:`tensile_strength_MPa`
    as a steel is tempered), not as a quantitative toughness. Scalar or array in/out.
    """
    HV_arr = np.asarray(HV, dtype=float)
    idx = (TOUGH_HV_BRITTLE - HV_arr) / (TOUGH_HV_BRITTLE - TOUGH_HV_TOUGH)
    out = np.clip(idx, 0.0, 1.0)
    return float(out) if out.ndim == 0 else out
