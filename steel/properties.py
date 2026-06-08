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

Known v1 simplifications (scope, not bugs — the Phase-3 extensions)
-------------------------------------------------------------------
Maynier's full equations also carry a **cooling-rate** term (finer pearlite/lower
bainite at faster cooling → harder) and **minor-alloy** terms (Si/Mn/Cr/Mo raise each
constituent a little). Both are dropped in v1: the constituent hardnesses are the
moderate-cooling-rate, carbon-only limit. Consequences, flagged honestly:

  * The two benchmark steels are **both ≈ 0.4 % C**, so neither exercises the *slope*
    of HVᵢ(C); the slope is tested separately at 0.8 % C (1080 → ~65 HRC martensite).
  * Dropping the minor-alloy terms makes 4140's quenched end come out ~1 HRC *below*
    1045's (it has 0.05 % less C and the Cr/Mn boost is omitted), where published data
    has them ~equal — within the as-quenched curve's own ±2 HRC spread, and exactly the
    Phase-3 refinement.
  * Coarse vs fine pearlite (the furnace-vs-air distinction :mod:`pathint` carries as
    ``formation_T``) maps to *one* ferrite-pearlite hardness here — the cooling-rate
    term is what would separate them. Phase 3.

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
from .kinetics import CCurve

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


def vickers_martensite(C: float) -> float:
    """As-quenched martensite hardness ``HV = 92 + 828·√C`` (Vickers), carbon ``C`` (wt%).

    The benchmark-critical constituent: at a Jominy quenched end the structure is fully
    martensitic, so the hardness there *is* this value. A ``√C`` fit to the canonical
    as-quenched-martensite-vs-carbon data (Hodge–Orehoski / Krauss) — an independent
    dataset, so hitting the published Jominy J1 hardness is genuine cross-source
    agreement, not a refit. Saturating: ~56 HRC at 0.4 % C, ~65 HRC by 0.8 % C.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return MART_HV_BASE + MART_HV_SLOPE * math.sqrt(C)


def vickers_ferrite_pearlite(C: float) -> float:
    """Ferrite-pearlite (diffusional product) hardness ``HV = 90 + 260·C``, ``C`` wt%.

    A linear-in-carbon fit to **normalized plain-carbon steel** hardness (independent of
    the Jominy data). :mod:`pathint` lumps the whole diffusional product as "pearlite";
    for a hypoeutectoid steel that aggregate is ferrite + pearlite, which is what this
    normalized hardness measures. The soft end of the Jominy bar — typically < 20 HRC,
    where HRC is undefined and the result is reported off-scale.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return FP_HV_BASE + FP_HV_SLOPE * C


def vickers_bainite(C: float) -> float:
    """Bainite hardness ``HV = 200 + 380·C`` (Vickers), carbon ``C`` (wt%).

    Intermediate between ferrite-pearlite and martensite. The least-anchored
    constituent (barely exercised by the continuous-cooled 1045/4140 benchmark, which
    go essentially martensite-or-pearlite); a defensible placeholder refined in Phase 3.
    """
    if C < 0.0:
        raise ValueError(f"carbon content must be ≥ 0, got {C}")
    return BAIN_HV_BASE + BAIN_HV_SLOPE * C


# Registry: constituent name → hardness HV(C). Keys match pathint's fractions dict, so
# the rule of mixtures iterates them in lockstep (a missing/extra key is a real error).
CONSTITUENT_HV = {
    "pearlite": vickers_ferrite_pearlite,
    "bainite": vickers_bainite,
    "martensite": vickers_martensite,
    "retained_austenite": lambda C: HV_RETAINED_AUSTENITE,
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
def hardness_HV(fractions: dict, C: float) -> float:
    """Rule-of-mixtures hardness ``HV = Σ fᵢ·HVᵢ(C)`` (Vickers) — the Maynier method.

    ``fractions`` is the constituent dict (:meth:`pathint.TransformResult.fractions`):
    pearlite / bainite / martensite / retained_austenite, summing to 1. Each constituent
    contributes its carbon-dependent Vickers hardness weighted by its fraction. Computed
    in HV (linear, additive, soft-defined); convert with :func:`vickers_to_rockwell_c`
    or use :func:`hardness_HRC`. Unknown constituent keys raise (a fractions/registry
    mismatch is a real error, not a silent zero).
    """
    HV = 0.0
    for name, f in fractions.items():
        if name not in CONSTITUENT_HV:
            raise KeyError(f"no hardness model for constituent {name!r}")
        HV += f * CONSTITUENT_HV[name](C)
    return HV


def hardness_HRC(fractions: dict, C: float) -> float:
    """Rule-of-mixtures hardness in **HRC** — :func:`hardness_HV` then ASTM E140.

    ``nan`` when the mixture is softer than ~20 HRC (a pearlitic Jominy tail) — HRC is
    undefined there; read :func:`hardness_HV` for the soft end.
    """
    return vickers_to_rockwell_c(hardness_HV(fractions, C))


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


def jominy_hardness(field, ccurve: CCurve, C: float, distances: np.ndarray | None = None) -> JominyHardness:
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
    """
    x = np.asarray(field.x, dtype=float)
    if distances is None:
        distances = x
    distances = np.asarray(distances, dtype=float)

    HV = np.empty(distances.size)
    mart = np.empty(distances.size)
    for k, d in enumerate(distances):
        j = int(np.argmin(np.abs(x - d)))          # nearest cell (the array seam)
        t, T = field.history(j)
        result = pathint.transform_along_path(t, T, ccurve)
        HV[k] = hardness_HV(result.fractions(), C)
        mart[k] = result.martensite
    return JominyHardness(
        distance=distances,
        HV=HV,
        HRC=vickers_to_rockwell_c(HV),
        martensite=mart,
        carbon=C,
    )
