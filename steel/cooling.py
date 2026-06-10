"""Cooling-medium presets: quench severity → a 0-D cooling path (Steel Phase 1c).

The third Phase-1c piece. :mod:`kinetics` holds the laws and :mod:`pathint` the
integration; this module supplies the *inputs* — the ``T(t)`` cooling histories for
the four quench media that drive the anchor demo (furnace / air / oil / water).

The model: lumped capacitance
-----------------------------
A quench is parametrized by a convective heat-transfer coefficient ``h``
(W/m²·K) — higher ``h`` = more severe quench. For a thermally **thin** body the
interior stays uniform and Newton cooling applies with a single time constant

    τ_th = ρ·c_p·L_c / h            L_c = V/A  (the characteristic length)

so :mod:`pathint`'s 0-D cooler turns ``h`` + specimen size into ``T(t)``. The four
presets span the severity range; with the standard specimen they straddle the
1080 C-curve nose, which is what makes one steel become four materials.

The validity caveat (honest, not hidden)
----------------------------------------
Lumped capacitance holds only for **Biot number** ``Bi = h·L_c/k < 0.1`` — the
surface-to-interior temperature lag must be negligible. A severe quench (water)
of a thick section violates this: the surface and core cool at different rates and
a *spatial* solve is required. That is precisely the Phase-2 step
(``engines/diffusion`` in heat mode, the Jominy bar). Every :class:`CoolingPath`
here therefore carries its :attr:`~CoolingPath.biot` number, and
:func:`cooling_path` warns when it exceeds 0.1 — the 0-D demo is honest about
where it is being stretched and where Phase 2 takes over.

The ``h`` values are **representative** quench severities (still/unagitated end of
the usual ranges), not fitted to a specific bath. They and the standard specimen
are chosen so the four kinetic outcomes are distinct and dramatic for plain-carbon
1080; alloying and section size (hardenability) are Phase-2 territory.

Units: ``h`` in W/(m²·K), lengths in m, ρ in kg/m³, c_p in J/(kg·K), k in
W/(m·K), temperatures in °C, time in s.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from . import pathint

# Steel thermophysical properties (austenitic range, representative).
RHO_STEEL = 7850.0      # density, kg/m³
CP_STEEL = 600.0        # specific heat, J/(kg·K)
K_STEEL = 30.0          # thermal conductivity, W/(m·K)

# Representative convective heat-transfer coefficients, W/(m²·K). Spanning the
# severity ladder: a near-still furnace, still air, an unagitated oil bath, an
# agitated water quench. Real baths vary with agitation; these are illustrative.
H_FURNACE = 8.0
H_AIR = 25.0
H_OIL = 400.0
H_WATER = 1500.0

MEDIA = {"furnace": H_FURNACE, "air": H_AIR, "oil": H_OIL, "water": H_WATER}

# Standard demo specimen: a 10 mm-diameter cylinder. Small enough that the slower
# three media stay within lumped validity (Bi < 0.1); the water quench mildly
# exceeds it (Bi ≈ 0.13) — flagged, and the cue for the Phase-2 spatial solve.
STANDARD_DIAMETER = 0.010   # m

# Lumped-capacitance shape factor L_c = V/A by geometry.
_SHAPE_FACTOR = {
    "cylinder": 4.0,        # long cylinder: V/A = d/4
    "sphere": 6.0,          # sphere:        V/A = d/6
    "plate": 2.0,           # plate cooled both faces: V/A = thickness/2
}


def characteristic_length(size: float, geometry: str = "cylinder") -> float:
    """Lumped characteristic length ``L_c = V/A`` (m) for a ``size`` (diameter/thickness)."""
    if geometry not in _SHAPE_FACTOR:
        raise ValueError(f"geometry must be one of {sorted(_SHAPE_FACTOR)}, got {geometry!r}")
    if size <= 0.0:
        raise ValueError(f"size must be > 0, got {size}")
    return size / _SHAPE_FACTOR[geometry]


def biot_number(h: float, L_c: float, k: float = K_STEEL) -> float:
    """Biot number ``Bi = h·L_c/k`` — lumped capacitance is valid only for ``Bi < 0.1``."""
    return h * L_c / k


def lumped_time_constant(
    h: float, L_c: float, rho: float = RHO_STEEL, cp: float = CP_STEEL
) -> float:
    """Newton cooling time constant ``τ_th = ρ·c_p·L_c / h`` (s) — bigger ``L_c``/smaller ``h`` ⇒ slower."""
    if h <= 0.0:
        raise ValueError(f"heat-transfer coefficient h must be > 0, got {h}")
    return rho * cp * L_c / h


# Reference temperature for the cooling-rate metric (°C). 700 °C is the classic
# read-off for the Jominy distance↔rate equivalence and Maynier's ``Vr`` (the
# diffusional-transformation region just below A₁) — the same temperature
# :meth:`jominy.ThermalField.cooling_rate` uses, so the 0-D and spatial models share
# one cooling-rate definition (the Phase-3 property model's :math:`V_r`).
COOLING_RATE_REF_T = 700.0


def cooling_rate_through(t: np.ndarray, T: np.ndarray, T_ref: float = COOLING_RATE_REF_T) -> float:
    """Cooling rate ``|dT/dt|`` (K/s) as a history ``(t, T)`` cools through ``T_ref`` (°C).

    The crossing time is interpolated from the (monotone-cooling) history and the
    variable-spacing derivative ``dT/dt`` read there — **the identical definition**
    :meth:`steel.jominy.ThermalField.cooling_rate` applies per spatial
    position, so the 0-D demo paths and the Jominy bar report cooling rate the same
    way (the single-metric discipline the Phase-3 property model needs). Returns
    ``nan`` if the path never cools through ``T_ref`` (e.g. it started below it).
    """
    t = np.asarray(t, dtype=float)
    T = np.asarray(T, dtype=float)
    below = np.flatnonzero(T <= T_ref)
    if below.size == 0 or below[0] == 0:
        return float("nan")                  # never cooled through T_ref (or started below)
    t_cross = float(np.interp(T_ref, T[::-1], t[::-1]))   # reverse to ascending for interp
    return abs(float(np.interp(t_cross, t, np.gradient(T, t))))


@dataclass(frozen=True)
class CoolingPath:
    """A named cooling history: the ``(t, T)`` arrays plus the parameters behind them.

    ``t``/``T`` are the plain arrays :mod:`pathint` consumes (the inter-module
    currency); ``tau_thermal`` is the Newton time constant and ``biot`` the
    lumped-validity flag (``> 0.1`` ⇒ the 0-D model is being stretched, see module
    docstring). ``name`` is the medium label for plots/legends.
    """

    name: str
    t: np.ndarray
    T: np.ndarray
    tau_thermal: float
    biot: float

    @property
    def lumped_valid(self) -> bool:
        """Whether the lumped-capacitance assumption holds (``Bi < 0.1``)."""
        return self.biot < 0.1

    def cooling_rate(self, T_ref: float = COOLING_RATE_REF_T) -> float:
        """Cooling rate ``|dT/dt|`` (K/s) as this path cools through ``T_ref`` (°C).

        The Maynier/Jominy ``Vr`` metric (:func:`cooling_rate_through`), read off this
        path's ``(t, T)`` history — what the Phase-3 property model consumes to apply
        the cooling-rate hardness term. ``nan`` if the path never reaches ``T_ref``.
        """
        return cooling_rate_through(self.t, self.T, T_ref)


def cooling_path(
    medium: str | float,
    T0: float = 850.0,
    T_env: float = 25.0,
    diameter: float = STANDARD_DIAMETER,
    geometry: str = "cylinder",
    t_end: float | None = None,
    warn_biot: bool = True,
) -> CoolingPath:
    """Build the 0-D ``T(t)`` cooling path for a quench ``medium`` (or a raw ``h``).

    ``medium`` is a key of :data:`MEDIA` (``"furnace"``/``"air"``/``"oil"``/``"water"``)
    or a numeric ``h`` (W/m²·K). The specimen austenitizes at ``T0`` (°C) and cools
    toward the bath ``T_env`` with time constant ``τ_th`` set by ``h`` and size.
    ``t_end`` defaults to ``≈ 14·τ_th`` (cooled to within ~1e-6 of the bath). Emits
    a warning when ``Bi ≥ 0.1`` (lumped model stretched — use the Phase-2 spatial
    solve for a faithful thick-section result).
    """
    h = MEDIA[medium] if isinstance(medium, str) else float(medium)
    name = medium if isinstance(medium, str) else f"h={h:g}"

    L_c = characteristic_length(diameter, geometry)
    tau_th = lumped_time_constant(h, L_c)
    Bi = biot_number(h, L_c)
    if warn_biot and Bi >= 0.1:
        warnings.warn(
            f"cooling_path({name!r}): Biot number Bi={Bi:.2f} ≥ 0.1 — the 0-D "
            "lumped model is stretched (surface/core lag); a faithful thick-section "
            "result needs the Phase-2 spatial heat solve.",
            stacklevel=2,
        )

    if t_end is None:
        t_end = 14.0 * tau_th       # exp(-14) ≈ 8e-7: cooled essentially to the bath
    t = pathint.log_time_grid(t_end)
    T = pathint.newton_cooling(t, T0, T_env, tau_th)
    return CoolingPath(name=name, t=t, T=T, tau_thermal=tau_th, biot=Bi)


def standard_media_paths(
    T0: float = 850.0, T_env: float = 25.0, diameter: float = STANDARD_DIAMETER
) -> list[CoolingPath]:
    """The four anchor-demo cooling paths (furnace → air → oil → water), slow → fast.

    One austenitized 1080 specimen, four quench severities — the inputs that, fed
    through :func:`~steel.pathint.transform_along_path`, become the four
    microstructures of the demo. Ordered by decreasing ``τ_th`` (increasing severity).
    """
    return [
        cooling_path(m, T0=T0, T_env=T_env, diameter=diameter)
        for m in ("furnace", "air", "oil", "water")
    ]
