"""The experimentation surface: parameter sweeps over the validated chain (Steel plan §9).

*Cooling curve in, microstructure out* (plan §1) made **sweepable**. ARCHITECTURE.md §1
names experimentation a core target and ties parameter sweeps to "the cheapest
verification"; this module is the headless harness that delivers it — the foundation
the interactive surfaces (``app.py`` Streamlit, ``steel.ipynb`` notebook) import.

What this is — and what it is *not*
-----------------------------------
It is **pure re-composition** of modules that are already individually validated:

    ccurve_for_steel (kinetics/2b)  →  cooling.cooling_path (1c)  →
    pathint.transform_along_path (1c)  →  properties.hardness_HV (2c/3a)

No new physics, no new calibration, no new constant lives here — every number a
sweep reports is produced by a function sealed behind its own triad. So this module
has **no validation triad of its own**; what its tests check is *harness* correctness
(see ``tests/test_sweep.py``):

  * **Cross-consistency** — the single most load-bearing property. A steel's minor-alloy
    composition threads into **both** the kinetics (``ccurve_for_steel`` → the
    hardenability ``τ``-shift) **and** the hardness (``hardness_HV(comp=…)`` → the Maynier
    minor-alloy delta) from *one* :meth:`Steel.minor` dict — the same "one dict serves both
    consumers" wiring :data:`carburize.CARBURIZING_STEEL_8620` documents. Exercising both
    faces from one input is what a sweep adds over a single demo call.
  * **Monotone trends** — the experimentation payoff, asserted *qualitatively* (robust,
    not brittle exact fractions, like ``test_demo_four_curves``): faster cooling → harder;
    more carbon → harder martensite and lower Mₛ; more alloy → martensite survives a slower
    quench (deeper hardenability); more tempering → softer.
  * **Conservation passthrough** — the four product fractions still sum to 1 at every node
    (inherited from :mod:`pathint`, re-asserted at the harness boundary).

The 0-D model and its one honest subtlety (read before sweeping)
----------------------------------------------------------------
Cooling histories come from the **0-D lumped-capacitance** cooler (:mod:`cooling`) — the
same engine the four-curves demo uses. A consequence worth internalizing, because it
shapes what the sweeps can and cannot show: in the lumped model the cooling path ``T(t)``
depends on the quench ``h``, the section size, and steel thermophysical constants — **not
on composition**. So a :func:`composition_sweep` at a fixed medium feeds *every* steel the
**same** ``(t, T)`` path; the alloy effect enters purely through the C-curve shift (exactly
the Phase-2b "same Jominy histories, different hardenability" setup). The project's recurring
lesson follows: steels **share the fully-martensitic fast end** (water) and the
**fully-pearlitic slow end** (furnace) and **diverge only in the middle**. Read an
alloy-hardenability trend at an *intermediate* medium (oil), never at the saturated ends —
where every steel is identical and the trend is silent. (A *spatial* alloy gradient is the
Jominy artifact, ``demo_jominy``; this surface is the 0-D what-if.)

Two more honest edges, both surfaced not hidden:

  * **Biot validity.** A severe quench (water) of a thick section exceeds the lumped-validity
    ``Bi < 0.1`` (:mod:`cooling`). Every :class:`Outcome` carries its ``biot`` /
    :attr:`Outcome.lumped_valid` so a sweep that wanders into stretched territory is *flagged*,
    not silently trusted — the cue for the Phase-2 spatial solve. (The harness sets
    ``warn_biot=False`` so a multi-node sweep does not emit one warning per call; it reports
    Biot in the data instead, the ``demo_four_curves`` pattern.)
  * **Report in HV, compare in HV.** Hardness is mixed in Vickers (defined for soft material);
    HRC (:func:`properties.vickers_to_rockwell_c`) is ``nan`` below ~20 HRC — exactly the
    soft slow-cooled end of a lean steel, the steel that makes the composition axis
    interesting. ``Outcome`` carries both; trends are meaningful in ``HV`` everywhere, in
    ``HRC`` only on-scale.

Tempering is kept honest and separate
--------------------------------------
:func:`tempered_martensite_HV` is **martensite-only** by design (pearlite barely tempers;
the mixed-structure per-constituent temper is a documented Phase-3b deferral). So tempering
is **not** folded into the as-quenched cooling/composition sweeps (that would temper mixed
microstructures the model does not cover). It gets its own :func:`temper_sweep`, the
quench-and-temper response of a *fully martensitic* start — the practically relevant Q&T
curve, within the validated scope.

Units & conventions (inherited from the consumed modules)
--------------------------------------------------------
Temperatures **°C**, times **s** (tempering **hours**, per Hollomon–Jaffe), composition
**wt %**, fractions dimensionless ``[0, 1]``, hardness **HV** internally / **HRC** at the
boundary, cooling rate ``Vr`` in **°C/h at 700 °C** (the Maynier metric).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from . import cooling, pathint
from . import properties as prop
from .kinetics import CCurve, ccurve_for_steel
from .cooling import STANDARD_DIAMETER


# --------------------------------------------------------------------------- #
# 1. A named steel composition — the one input that threads everywhere
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Steel:
    """A named steel composition (wt %) — the sweep's unit of "a material".

    Carbon plus the minor-alloy elements the downstream models read. The crucial
    property is that **one** composition object feeds *both* faces of the model: its
    :meth:`minor` dict goes into :func:`~steel.kinetics.ccurve_for_steel`
    (the hardenability ``τ``-shift) *and* into :func:`~steel.properties.hardness_HV`
    (the Maynier minor-alloy hardness delta) — the same self-consistent wiring the
    carburizing 8620 dict documents. Defaults are zero so a bare ``Steel(0.80)`` is a
    plain-carbon steel (but see :data:`STEELS` for *real* compositions — a plain-carbon
    grade still carries ~0.7 % Mn, and the reference 1080 the kinetics were calibrated to
    *is* that Mn; ``Steel(0.80)`` with ``Mn = 0`` is a leaner hypothetical steel, the trap
    :func:`ccurve_for_steel` warns about).
    """

    C: float
    Mn: float = 0.0
    Si: float = 0.0
    Ni: float = 0.0
    Cr: float = 0.0
    Mo: float = 0.0
    name: str = ""

    def minor(self) -> dict:
        """The minor-alloy ``{element: wt%}`` dict the property/kinetics models consume.

        Only the non-carbon elements (``properties`` reads Si/Mn/Ni/Cr; ``ccurve_for_steel``
        reads Mn/Ni/Cr/Mo/Si — each picks the keys it knows). Zeros are kept so the dict is a
        stable shape; the models treat a missing or zero element identically.
        """
        return {"Mn": self.Mn, "Si": self.Si, "Ni": self.Ni, "Cr": self.Cr, "Mo": self.Mo}

    def label(self) -> str:
        """A display label — the steel's ``name`` if given, else its carbon content."""
        return self.name or f"{self.C:.2f}%C"


# A small registry of **real** compositions (wt %), matching the grades exercised
# elsewhere in the project so the experimentation surface defaults to honest chemistry
# (not the Mn=0 "leaner hypothetical" trap). 1080 is the kinetics' reference steel
# (≈ 0.7 % Mn → hardenability M = 1); 4140 is the deep-hardening alloy benchmark; 8620 is
# the carburizing-grade core (same dict as carburize.CARBURIZING_STEEL_8620, C = core).
STEELS = {
    "1045": Steel(C=0.45, Mn=0.75, Si=0.22, name="1045"),
    "1080": Steel(C=0.80, Mn=0.70, Si=0.20, name="1080"),
    "4140": Steel(C=0.40, Mn=0.90, Si=0.25, Cr=1.00, Mo=0.20, name="4140"),
    "8620": Steel(C=0.20, Mn=0.80, Si=0.25, Ni=0.55, Cr=0.50, Mo=0.20, name="8620"),
}

# The four standard quench media, slow → fast (the cooling-rate axis). A sweep may also
# pass a raw ``h`` (W/m²·K) for a continuous cooling-rate sweep — see :func:`cooling.cooling_path`.
DEFAULT_MEDIA = ("furnace", "air", "oil", "water")

# The discriminating intermediate medium for reading an alloy-hardenability trend: at the
# saturated ends (furnace/water) every steel shares the same outcome, so the composition
# axis only speaks in the middle (the "diverge with distance" lesson, in 0-D form).
DISCRIMINATING_MEDIUM = "oil"


# --------------------------------------------------------------------------- #
# 2. The single what-if: one steel + one cooling condition → one outcome
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Outcome:
    """Everything one (steel, cooling condition) produces — the unit a sweep is a grid of.

    Echoes the inputs (``steel``, ``medium``, ``diameter``) and carries the whole chain's
    output: the cooling ``path``, the ``ccurve`` it was integrated under (whose
    ``tau_factor`` is the alloy hardenability shift — exposed so the mechanism view can draw
    the path across the C-curve and tests can confirm the comp threaded into the kinetics),
    the microstructure ``result`` (the four fractions), the cooling rate ``Vr`` (°C/h at
    700 °C), and the hardness in both ``HV`` (defined everywhere — compare here) and ``HRC``
    (``nan`` below ~20 HRC — report only). ``biot`` / :attr:`lumped_valid` flag where the
    0-D model is stretched.
    """

    steel: Steel
    medium: str | float
    diameter: float
    path: cooling.CoolingPath
    ccurve: CCurve
    result: pathint.TransformResult
    Vr: float
    HV: float
    HRC: float
    biot: float

    @property
    def lumped_valid(self) -> bool:
        """Whether the 0-D lumped-capacitance model holds here (``Bi < 0.1``)."""
        return self.biot < 0.1

    def fractions(self) -> dict:
        """The microstructure as the plan-§5 constituent dict (summing to 1)."""
        return self.result.fractions()

    def dominant(self) -> str:
        """The headline (largest-fraction) constituent."""
        return self.result.dominant()


def evaluate(
    steel: Steel,
    medium: str | float = DISCRIMINATING_MEDIUM,
    diameter: float = STANDARD_DIAMETER,
    austenitize_T: float = 850.0,
    bath_T: float = 25.0,
) -> Outcome:
    """Run the full chain for one steel cooled one way — the single what-if.

    Builds the steel's TTT curve (:func:`~steel.kinetics.ccurve_for_steel`: A₁
    ceiling + Andrews Mₛ + the alloy hardenability shift, all from ``steel``'s composition),
    cools a specimen of ``diameter`` in ``medium`` (a preset name or a raw ``h``) with the
    0-D lumped cooler, integrates that history to a microstructure
    (:func:`~steel.pathint.transform_along_path`), and maps the fractions to
    hardness with the rule of mixtures — threading the **same** composition into the Maynier
    minor-alloy term and this path's cooling rate ``Vr`` into the cooling-rate term. The one
    place ``steel.minor()`` reaches both the kinetics and the hardness, self-consistently.

    ``warn_biot=False``: a severe-quench/thick-section node still records its ``biot`` in the
    returned :class:`Outcome` (``lumped_valid``), but a multi-node sweep stays quiet.
    """
    minor = steel.minor()
    ccurve = ccurve_for_steel(
        steel.C, Mn=steel.Mn, Ni=steel.Ni, Cr=steel.Cr, Mo=steel.Mo, Si=steel.Si
    )
    path = cooling.cooling_path(
        medium, T0=austenitize_T, T_env=bath_T, diameter=diameter, warn_biot=False
    )
    result = pathint.transform_along_path(path.t, path.T, ccurve)

    rate_Ks = path.cooling_rate()                       # |dT/dt| at 700 °C, K/s (nan if never reached)
    Vr = rate_Ks * prop.SECONDS_PER_HOUR                # → °C/h (Maynier's metric); nan propagates
    Vr_arg = float(Vr) if np.isfinite(Vr) else None     # the model takes None, not nan, for "no rate"
    HV = prop.hardness_HV(result.fractions(), steel.C, comp=minor, Vr=Vr_arg)
    HRC = prop.vickers_to_rockwell_c(HV)

    return Outcome(
        steel=steel, medium=medium, diameter=diameter, path=path, ccurve=ccurve,
        result=result, Vr=float(Vr), HV=float(HV), HRC=float(HRC), biot=path.biot,
    )


# --------------------------------------------------------------------------- #
# 3. The sweeps: cooling-rate axis, composition axis, and their grid
# --------------------------------------------------------------------------- #
def cooling_rate_sweep(
    steel: Steel, media=DEFAULT_MEDIA, diameter: float = STANDARD_DIAMETER, **evaluate_kwargs
) -> list[Outcome]:
    """One steel down the cooling-rate axis — :func:`evaluate` for each medium (slow → fast).

    The four-curves demo generalized to any *real* steel: same austenite, a spectrum of
    quench severities, soft pearlite → hard martensite. ``media`` may mix preset names and
    raw ``h`` values (a continuous cooling-rate sweep). Returns one :class:`Outcome` per
    medium, in the given order.
    """
    return [evaluate(steel, medium=m, diameter=diameter, **evaluate_kwargs) for m in media]


def composition_sweep(
    steels, medium: str | float = DISCRIMINATING_MEDIUM,
    diameter: float = STANDARD_DIAMETER, **evaluate_kwargs
) -> list[Outcome]:
    """Several steels down the composition axis at one cooling condition — :func:`evaluate` each.

    ``steels`` is an iterable of :class:`Steel` (or :data:`STEELS` keys). **Read the alloy
    trend at an intermediate medium** (the default :data:`DISCRIMINATING_MEDIUM` = oil): in
    the 0-D model every steel sees the *same* cooling path at a fixed medium (composition does
    not change the lumped ``T(t)``), so the hardenability difference only shows in the middle
    of the severity range — at water every steel is martensitic, at furnace every steel is
    pearlitic, and the composition axis says nothing there. Returns one :class:`Outcome` per
    steel, in order.
    """
    resolved = [STEELS[s] if isinstance(s, str) else s for s in steels]
    return [evaluate(s, medium=medium, diameter=diameter, **evaluate_kwargs) for s in resolved]


def sweep_grid(
    steels, media=DEFAULT_MEDIA, diameter: float = STANDARD_DIAMETER, **evaluate_kwargs
) -> list[list[Outcome]]:
    """The composition × cooling-rate grid — the side-by-side comparison (plan §9).

    Rows are steels, columns are media: ``grid[i][j]`` is steel ``i`` cooled in medium ``j``.
    This is the one genuinely-new view over the four-curves demo — it adds the **composition
    axis** the single-steel demo cannot show — and the data behind
    :func:`~steel.plots.sweep_comparison_figure`. ``steels`` may be :class:`Steel`
    objects or :data:`STEELS` keys.
    """
    resolved = [STEELS[s] if isinstance(s, str) else s for s in steels]
    return [cooling_rate_sweep(s, media=media, diameter=diameter, **evaluate_kwargs)
            for s in resolved]


# --------------------------------------------------------------------------- #
# 4. The tempering sweep — martensite-only quench-and-temper (kept separate, honest)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TemperResponse:
    """A quench-and-temper response curve: properties vs tempering temperature.

    For a steel **quenched to full martensite** then tempered ``t_hours`` h at each
    temperature in ``temper_C``. All arrays share ``temper_C``'s length: ``P`` the
    Hollomon–Jaffe parameter, ``HV``/``HRC`` the tempered hardness (HRC ``nan`` once soft),
    ``UTS_MPa`` the ISO-18265 tensile strength (``nan`` outside ~150–550 HV), ``toughness``
    the rough relative [0, 1] index (rises as the steel softens). ``HV_as_quenched`` is the
    untempered start (the curve's left limit).
    """

    steel: Steel
    t_hours: float
    temper_C: np.ndarray
    P: np.ndarray
    HV: np.ndarray
    HRC: np.ndarray
    UTS_MPa: np.ndarray
    toughness: np.ndarray
    HV_as_quenched: float


def temper_sweep(
    steel: Steel, temper_C=None, t_hours: float = 1.0
) -> TemperResponse:
    """Sweep tempering temperature for a quench-hardened steel — the Q&T property curve.

    Tempers a **fully martensitic** as-quenched structure (the practically relevant
    quench-and-temper case, and the validated scope of
    :func:`~steel.properties.tempered_martensite_HV` — pearlite barely tempers, so a
    *mixed* structure would have to be tempered per-constituent, a documented deferral). This
    is why tempering is its own sweep and not folded into the as-quenched cooling/composition
    sweeps. The steel's minor-alloy ``comp`` threads through both master-curve endpoints, so an
    alloy steel **resists tempering** (starts harder, floors higher) as an emergent consequence.

    ``temper_C`` defaults to 100 → 700 °C (the practical tempering range, onset to spheroidite
    floor). ``t_hours`` is the hold time. Hardness moves down the Hollomon–Jaffe master curve;
    strength and toughness follow it (toughness *up* as hardness *down* — the trade-off).
    """
    if temper_C is None:
        temper_C = np.linspace(100.0, 700.0, 25)
    temper_C = np.asarray(temper_C, dtype=float)
    minor = steel.minor()

    HV = np.array([prop.tempered_martensite_HV(steel.C, float(T), t_hours, comp=minor)
                   for T in temper_C])
    P = np.array([prop.hollomon_jaffe_parameter(float(T), t_hours) for T in temper_C])
    HRC = prop.vickers_to_rockwell_c(HV)
    UTS = prop.tensile_strength_MPa(HV)
    tough = prop.toughness_index(HV)
    HV_aq = prop.vickers_martensite(steel.C, comp=minor)

    return TemperResponse(
        steel=steel, t_hours=t_hours, temper_C=temper_C, P=P, HV=HV, HRC=np.asarray(HRC),
        UTS_MPa=np.asarray(UTS), toughness=np.asarray(tough), HV_as_quenched=float(HV_aq),
    )
