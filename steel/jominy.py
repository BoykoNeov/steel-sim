"""Jominy end-quench hardenability — the spatial thermal model (Steel Phase 2a).

Phase 2 is where the frozen heat solver (:mod:`engines.diffusion`) finally earns
its keep *spatially*. The standard Jominy end-quench test (ASTM A255): a 25.4 mm ×
100 mm bar, austenitized, then **one end** hit by a water jet while the rest cools
in air. The result is a gradient of cooling rates along the bar axis — fastest at
the quenched end, slower the further you go — and (Phase 2c) a hardness traverse
that reveals the steel's *hardenability*. This module builds and validates the
thermal half: ``T(x, t)`` and the cooling-rate-vs-distance curve. The
microstructure/hardness mapping (2b/2c) consumes the per-position ``(t, T)``
histories this module produces, via :mod:`pathint` — the same array seam the 0-D
demo used.

The model: the transient fin equation (and why lateral loss is essential)
-------------------------------------------------------------------------
The faithful 1-D reduction of the end-quench bar is **not** pure axial conduction.
A timescale check settles it: the axial diffusion length is ``√(αt)`` with
``α = k/(ρc_p) ≈ 6.4e-6 m²/s``, so heat from the quenched end reaches only ~8 mm
in 10 s and ~25 mm in 100 s. With *adiabatic sides* the far half of the bar would
take ~25 min to feel the quench — but a real Jominy bar's far end cools in
minutes. The missing sink is **lateral convection to air** off the cylindrical
surface. The right model is therefore the transient fin equation

    ρc_p ∂T/∂t = k ∂²T/∂x² − (h_lat·P/A)·(T − T_air)        x ∈ [0, L]

with a strong Robin (water) at the quenched end ``x = 0`` and an insulated tip
``x = L`` (the end area is negligible against the lateral area). For a cylinder
``P/A = (2πr)/(πr²) = 4/d``. Near the quenched end axial conduction to the cold
face dominates (fast cool); far away the slow lateral loss dominates (slow cool) —
exactly the Jominy gradient.

How the frozen solver is reused (operator splitting)
----------------------------------------------------
The frozen engine solves pure conduction ``∂T/∂t = ∂/∂x(α ∂T/∂x)`` with Robin /
Neumann boundaries; its ``source`` is ``S(x, t)``, which **cannot** express the
fin's lateral term because that term depends on the live solution ``T``. So the
lateral loss is composed *around* the engine by **Strang operator splitting**:
each step is a half-step of lateral loss, a full implicit conduction step (the
frozen solver, untouched), then another half-step of lateral loss. The lateral
sub-step is the *analytic* solution of the pointwise decay ODE,

    T ← T_air + (T − T_air)·exp(−Δt / τ_lat),     τ_lat = ρc_p·(d/4) / h_lat,

which is **exact** for the linear sink and unconditionally stable — so the
composition inherits the engine's unconditional stability, with a 2nd-order
splitting error in Δt. This is the array-in/array-out seam of ADR 0001 working as
designed: we extend the physics without modifying the sealed engine.

Note ``τ_lat = ρc_p·(d/4)/h_lat`` is exactly :func:`cooling.lumped_time_constant`
with ``L_c = d/4`` (a cylinder's ``V/A``). That is not a coincidence: in the
thermally-thin limit (Biot ``= h·(d/4)/k < 0.1``) axial conduction is negligible,
the field stays uniform, and every point follows the 0-D Newton cooling of
:mod:`cooling` — the **analytical-limit** validation leg (``test_jominy.py``), and
the honest continuation of the Biot hand-off :mod:`cooling` flagged.

The one subtle unit (engine ``h`` ≠ physical ``h``)
---------------------------------------------------
The engine solves the ``α`` form, so its Robin ``−α ∂T/∂n = h_eng(T − T_ext)``
relates to the physical convective law ``−k ∂T/∂n = h_phys(T − T_ext)`` by
``h_eng = h_phys / (ρc_p)`` (units m/s, not W/m²·K). Physical ``h`` (W/m²·K) is
stored on :class:`JominyBar`; the conversion happens only where the engine Robin
is built. The both-ends-slab lumped test pins this conversion.

Scope (Phase 2a)
----------------
This module banks the **thermal spine** and its two cleanly-analytic validation
legs (lumped limit + energy conservation). The *hardenability* alloy shift of the
C-curve and the microstructure→hardness map — the calibration-heavy pieces and the
1045/4140 benchmark leg — are Phase 2b/2c (``kinetics``/``properties``), kept
separate so each sub-model is anchored to its own published data rather than
co-fit to one curve.

Units: lengths m, temperatures °C, time s, ``h`` in W/(m²·K), ρ kg/m³, c_p
J/(kg·K), k W/(m·K). Cooling rate is reported in K/s (≡ °C/s).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engines.diffusion import Diffusion1D, uniform_grid, Robin, Neumann
from . import pathint
from .cooling import (
    RHO_STEEL, CP_STEEL, K_STEEL, H_AIR,
    characteristic_length, lumped_time_constant, biot_number,
)

# Standard ASTM A255 Jominy specimen.
STANDARD_LENGTH = 0.100          # m (the read-off region; the bar is ~101.6 mm)
STANDARD_DIAMETER = 0.0254       # m (1 inch)

# Representative quenched-end water-jet severity (W/m²·K). The Jominy jet holds the
# end face near the bath; a large h approximates that. This is the *one free
# thermal knob* (advisor): disciplined by the lumped-limit test and the standard
# Jominy distance↔cooling-rate equivalence, and the value Phase 2c calibrates the
# hardness benchmark around. Lateral cooling reuses still-air H_AIR.
H_QUENCH_WATER = 1.5e4

# Reference temperature for the Jominy cooling rate. The classic correlation reads
# the cooling rate at 700 °C (the diffusional-transformation region just below A₁),
# which is what the published Jominy-distance↔cooling-rate tables tabulate.
COOLING_RATE_REF_T = 700.0


@dataclass(frozen=True)
class JominyBar:
    """The end-quench bar: geometry, thermophysical properties, and quench severities.

    ``h_quench`` (water jet at ``x = 0``) and ``h_lateral`` (air off the sides) are
    **physical** coefficients in W/(m²·K); the engine-unit conversion
    ``h_eng = h_phys/(ρc_p)`` is applied internally. ``T_bath``/``T_air`` are the
    quench-bath and ambient temperatures (°C).
    """

    length: float = STANDARD_LENGTH
    diameter: float = STANDARD_DIAMETER
    h_quench: float = H_QUENCH_WATER
    h_lateral: float = H_AIR
    T_bath: float = 25.0
    T_air: float = 25.0
    rho: float = RHO_STEEL
    cp: float = CP_STEEL
    k: float = K_STEEL

    @property
    def alpha(self) -> float:
        """Thermal diffusivity ``α = k/(ρc_p)`` (m²/s) — the engine's ``D`` in heat mode."""
        return self.k / (self.rho * self.cp)

    @property
    def lateral_L_c(self) -> float:
        """Lateral characteristic length ``A/P = d/4`` (m) — a cylinder's ``V/A``."""
        return characteristic_length(self.diameter, "cylinder")

    @property
    def tau_lateral(self) -> float:
        """Lateral Newton-cooling time constant ``τ_lat = ρc_p·(d/4)/h_lat`` (s).

        Identical to :func:`cooling.lumped_time_constant` with ``L_c = d/4`` — the
        tie that makes the thermally-thin limit reduce to :mod:`cooling`'s 0-D model.
        ``h_lateral = 0`` (insulated sides — a pure axial-conduction experiment)
        gives ``inf`` (no lateral loss).
        """
        if self.h_lateral <= 0.0:
            return float("inf")
        return lumped_time_constant(self.h_lateral, self.lateral_L_c, self.rho, self.cp)

    @property
    def biot_lateral(self) -> float:
        """Lateral Biot number ``h_lat·(d/4)/k`` — lumped validity holds for ``< 0.1``."""
        return biot_number(self.h_lateral, self.lateral_L_c, self.k)

    def _h_engine(self, h_phys: float) -> float:
        """Convert a physical ``h`` (W/m²·K) to the engine's α-form ``h/(ρc_p)`` (m/s)."""
        return h_phys / (self.rho * self.cp)


@dataclass(frozen=True)
class ThermalField:
    """The end-quench thermal solution: ``T(x, t)`` plus its energy accounting.

    ``x`` are the cell-center distances from the quenched end (m); ``t`` the output
    times (s); ``T`` the field, shape ``(len(t), len(x))`` in °C. ``end_loss`` and
    ``lateral_loss`` are the cumulative heat removed through the quenched end and the
    sides respectively, in the engine's ``∫T dx`` units (K·m) — their sum equals the
    drop in ``∫T dx`` to machine precision (the conservation leg). The per-position
    ``(t, T)`` histories feed :mod:`pathint` in Phase 2b.
    """

    x: np.ndarray
    t: np.ndarray
    T: np.ndarray
    bar: JominyBar
    end_loss: float
    lateral_loss: float

    def history(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """The ``(t, T)`` cooling history at position index ``i`` — a :mod:`pathint` path."""
        return self.t, self.T[:, i]

    def cooling_rate(self, T_ref: float = COOLING_RATE_REF_T) -> np.ndarray:
        """Cooling rate ``|dT/dt|`` (K/s) as each position cools through ``T_ref`` (°C).

        The standard Jominy metric. The *instantaneous* rate at the crossing is taken,
        not a coarse bracket secant: the crossing time is interpolated from the
        (monotone) history, and the variable-spacing time-derivative ``dT/dt`` is
        evaluated there. Positions that never reach ``T_ref`` (e.g. ``T_ref`` above the
        austenitizing T) give ``nan``. Length ``len(x)``, indexed from the quenched end.
        """
        t = self.t
        rates = np.full(self.x.size, np.nan)
        for j in range(self.x.size):
            Tj = self.T[:, j]
            below = np.flatnonzero(Tj <= T_ref)
            if below.size == 0 or below[0] == 0:
                continue                      # never cooled through T_ref (or started below)
            # Interpolate the crossing time (Tj is decreasing → reverse to ascending),
            # then read dT/dt there (np.gradient honours the non-uniform time grid).
            t_cross = float(np.interp(T_ref, Tj[::-1], t[::-1]))
            rates[j] = abs(float(np.interp(t_cross, t, np.gradient(Tj, t))))
        return rates

    def cooling_rate_at(
        self, distances: np.ndarray, T_ref: float = COOLING_RATE_REF_T
    ) -> np.ndarray:
        """Cooling rate (K/s) sampled at ``distances`` (m) from the quenched end.

        Linear interpolation of :meth:`cooling_rate` onto arbitrary Jominy distances
        (e.g. :func:`jominy_distances`), for plotting/sampling against published tables.
        """
        return np.interp(np.asarray(distances, dtype=float), self.x, self.cooling_rate(T_ref))


def jominy_distances(n: int = 16, step: float = 1.5875e-3) -> np.ndarray:
    """Standard Jominy read-off distances (m): ``n`` points at 1/16-inch spacing.

    ASTM A255 reads hardness at 1/16 in (1.5875 mm) intervals from the quenched end.
    Returns ``[step, 2·step, …, n·step]`` (the quenched end itself, distance 0, is a
    separate measurement; here we sample the standard interior points).
    """
    return step * np.arange(1, n + 1, dtype=float)


def solve_thermal_field(
    bar: JominyBar | None = None,
    T0: float = 850.0,
    t_end: float | None = None,
    n_cells: int = 200,
    per_decade: int = 120,
    t_start: float = 1e-4,
) -> ThermalField:
    """March the fin-equation end-quench model to its ``T(x, t)`` field.

    Reuses the frozen :class:`~engines.diffusion.Diffusion1D` in heat mode
    (``D = α``, Robin water-jet at the quenched end, insulated tip) for the
    conduction operator, and composes the lateral air loss by Strang splitting (see
    the module docstring). Marches a logarithmic time grid (:func:`pathint.log_time_grid`)
    so the sub-second near-end cool and the minutes-long far-end cool are both
    resolved without millions of steps.

    Parameters
    ----------
    bar : JominyBar, optional
        Geometry + quench severities; defaults to the standard ASTM specimen.
    T0 : float
        Uniform austenitizing temperature (°C).
    t_end : float, optional
        End time (s); defaults to ``6·τ_lat`` (the far end cools to within ~0.25 %
        of ambient), enough to take every position through the transformation range.
    n_cells, per_decade, t_start : int, int, float
        Spatial resolution and the log-time-grid density / start (s).

    Returns
    -------
    ThermalField
        The field and its energy accounting.
    """
    if bar is None:
        bar = JominyBar()
    if t_end is None:
        # 6·τ_lat takes the far end to within ~0.25 % of ambient; with insulated
        # sides (τ_lat = inf) fall back to the axial conduction timescale L²/α.
        t_end = 6.0 * bar.tau_lateral if np.isfinite(bar.tau_lateral) else bar.length**2 / bar.alpha

    grid = uniform_grid(bar.length, n_cells)
    alpha = bar.alpha
    # Robin (water jet) at the quenched end; insulated tip (negligible end area). A
    # zero quench severity degenerates to an insulated end (the lumped-limit config).
    bc_left = (
        Robin(bar._h_engine(bar.h_quench), bar.T_bath)
        if bar.h_quench > 0.0
        else Neumann(0.0)
    )
    solver = Diffusion1D(grid, alpha, bc_left, Neumann(0.0))

    t_grid = pathint.log_time_grid(t_end, t_start=t_start, per_decade=per_decade)
    n_t = t_grid.size
    field = np.empty((n_t, n_cells))
    T = np.full(n_cells, float(T0))
    field[0] = T

    tau_lat = bar.tau_lateral
    T_air = bar.T_air
    end_loss = 0.0          # Σ heat out the quenched end, in ∫T dx units (via flux)
    lateral_loss = 0.0      # Σ heat out the sides, in ∫T dx units (via total snapshots)

    def lateral_half(state: np.ndarray, dt: float) -> np.ndarray:
        """Analytic half-step of the lateral Newton loss (exact for the linear sink)."""
        return T_air + (state - T_air) * np.exp(-0.5 * dt / tau_lat)

    for i in range(1, n_t):
        dt = float(t_grid[i] - t_grid[i - 1])

        before = solver.total(T)
        T = lateral_half(T, dt)
        lateral_loss += before - solver.total(T)

        u1 = solver.step(T, dt, t0=float(t_grid[i - 1]))
        # Frozen identity: total(u1) − total(T) = dt·(flux_left − flux_right). The
        # conduction drop (heat out the ends) is the negative of that, via flux().
        j_left = solver.flux(u1, "left", t=float(t_grid[i]))
        j_right = solver.flux(u1, "right", t=float(t_grid[i]))
        end_loss += -dt * (j_left - j_right)
        T = u1

        before = solver.total(T)
        T = lateral_half(T, dt)
        lateral_loss += before - solver.total(T)

        field[i] = T

    return ThermalField(
        x=grid.centers,
        t=t_grid,
        T=field,
        bar=bar,
        end_loss=end_loss,
        lateral_loss=lateral_loss,
    )
