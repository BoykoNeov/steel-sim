"""Solidification & casting defects — the latent-heat thermal field (Steel-making **F4**, Slice 2).

The deferred half of F4 (``docs/plans/steel-making.md`` §7). Slice 1 (:mod:`steel.casting`) needed **no
solver**: Scheil microsegregation and Chvorinov's rule are closed forms, and the front-to-back proof rode
the *composition* handoff (the enriched centerline over-hardens). This slice builds the iconic part Slice 1
deferred — the **latent-heat solidification temperature field** of a section freezing against a chill — and
reads two casting **defect** criteria off it (Niyama shrinkage-porosity and a hot-tear susceptibility).

It is the project's second solver-bearing front-end physics (after the back end's Jominy / carburize), and
it reuses the **sealed 1-D diffusion/heat engine** (:class:`engines.diffusion.Diffusion1D`) — *no engine
touch, no new ADR*: latent heat rides the engine's already-unfrozen nonlinear ``D(u)`` path (ADR 0004).

The formulation — the enthalpy method on a unit-capacity engine (why, and the one trap avoided)
-----------------------------------------------------------------------------------------------
The engine solves ``∂u/∂t = ∂ₓ(D ∂ₓu)`` with **unit capacity on the LHS** and a source that is a function of
time only. Latent heat is therefore *not* a simple source term, and the tempting shortcut — fold an
apparent heat capacity into a temperature-mode diffusivity ``D(T) = k/(ρ c_app(T))`` — is **physically
wrong**: ``ρ c_app ∂T/∂t = ∂ₓ(k ∂ₓT)`` does not reduce to ``∂T/∂t = ∂ₓ((k/ρc_app) ∂ₓT)`` when ``c_app``
varies in space (a spurious ``k ∂ₓT · ∂ₓ(1/ρc_app)`` term appears across the mushy front), and the engine
would then conserve ``∫T dx``, which is not enthalpy.

The conservation-correct route is the **enthalpy method**: take the state variable to be **specific
enthalpy** ``u = h`` (the engine's heat-mode conserved quantity is exactly ``∫h dx`` — total enthalpy), and
recast ``ρ ∂h/∂t = ∂ₓ(k ∂ₓT)`` with ``T = T(h)`` as ``∂h/∂t = ∂ₓ( D(h) ∂ₓh )`` where ``D(h) = (k/ρ)·dT/dh``.
In the mushy range ``dT/dh`` is small (latent heat → the enthalpy rises with little temperature change), so
``D(h)`` drops and the freezing front slows — the recalescence/plateau, emergent and conserved exactly (the
engine caches the accepted ``D``-field, so the conservation identity stays machine-precision on the
nonlinear path). This maps onto the engine's native ``D_of_u`` argument with **no engine change**.

* **Smoothing the solid fraction is a numerical *regularization*, not a physics claim.** A lever-rule
  top-hat (``f_s`` linear in ``T``) makes ``dT/dh`` a step function — ``D(h)`` jumps ~9× at the mushy
  boundaries and the engine's Picard iteration *oscillates and fails to converge*. A smooth ``f_s(T)``
  (here a ``sin²`` ramp) makes ``D(h)`` continuous and Picard converges. The legitimacy of doing this is
  *proven* by the headline tooth below: the Stefan front position depends on the latent-heat **content** and
  ``α``, not the mushy-zone profile shape (``∫ df_l = 1`` for *any* shape), so the validated result is
  **insensitive** to the ``sin²`` choice. We do not claim ``sin²`` is the real ``f_s`` (it is Scheil/lever in
  reality) — only that the regularization does not move the benchmark.
* **The boundary condition is a fixed-temperature chill** (``Dirichlet``). With ``u = h`` the engine's
  convective ``Robin`` would act on *enthalpy*, not temperature — wrong for Newton cooling — so the
  enthalpy method is restricted to ``Dirichlet``/``Neumann``. A fixed chill surface (chill mold, die, or a
  water-cooled continuous-casting mold) is exactly ``Dirichlet`` and exact (``T(h)`` is monotonic, so a
  fixed surface temperature *is* a fixed surface enthalpy). Convective surface cooling is the named scope
  edge (it is the idiom :mod:`steel.martemper` / :mod:`steel.residual` use, on ``u = T``).

What is a TOOTH here, and what is honestly by-construction
----------------------------------------------------------
* **HEADLINE TOOTH (validated, untuned).** The numerical solidification front **converges to the analytic
  one-phase Stefan/Neumann closed form** ``X(t) = 2λ√(αt)`` (``λ`` from the transcendental Stefan-number
  equation) under grid refinement: at a physical freezing range the solidus front matches to within a few
  percent and the ratio climbs toward 1 as ``Δx`` halves. This is a cited, tuning-free benchmark — a broken
  latent-heat coupling misses it by tens of percent. (Plus the **enthalpy-conservation identity**, exact to
  machine precision.) The residual at finite freezing range is the solidus-isotherm offset below the Stefan
  interface temperature — a definitional offset of a mushy model vs the sharp-interface idealization, named,
  not hidden; and the ``ΔT → 0`` sharp limit *under-resolves* on a fixed grid (a razor-thin capacity spike),
  the named numerical limit.
* **Directional sanity (NOT a precise tooth).** Toggling latent heat off vs on slows the freeze-through by
  ~order ``L/(c_p·ΔT_freeze)`` — the right sign and order of magnitude, but the exact multiplier is
  profile-shape-dependent (the regularization), so it is a sanity check, not a falsifiable magnitude.
* **By construction / illustrative (NOT teeth).** **Niyama** ``Ny = G/√Ṫ`` (cited criterion *form*; Niyama
  1982 / Carlson–Beckermann) flags shrinkage porosity where the gradient is shallow and cooling slow — the
  thermal centre. That the centre is the worst (lowest ``Ny``) is by-construction from ``G`` and ``Ṫ``, and
  the absolute threshold is representative/rank-grade. The hot-tear readout (late-freezing mushy span) is
  likewise illustrative. This is the same discipline as Slice 1's "Scheil severity ordering is the tooth,
  the singularity is named": we name the defect criteria illustrative up front and do not manufacture a
  benchmark from them. **Chvorinov comparison stays scaling-only** — Chvorinov's ``t ∝ M²`` is
  *mold-diffusion-controlled*; a metal-conduction chill slab is a different heat-extraction regime, so the
  magnitude ``B`` is not reproduced (only the ``∝ length²`` scaling is shared).

Units: °C for temperature (SI K internally only where a rate/gradient needs it), metres for length, seconds
for time, J/kg for specific enthalpy and latent heat.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.special import erf

from engines.diffusion import Diffusion1D, Dirichlet, Neumann, uniform_grid

from .casting import LATENT_HEAT_FUSION, liquidus_temperature
from .cooling import CP_STEEL, K_STEEL, RHO_STEEL
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Cited / representative inputs — reused thermophysics + the freezing-range & chill conventions
# --------------------------------------------------------------------------- #
# Solidus depression below the liquidus (°C). The freezing range over which latent heat is released; a
# representative low-alloy-steel value (Won & Thomas give liquidus and solidus slopes — casting.py pins the
# liquidus; the range here is rank-grade, like Chvorinov's mold constant). Named, not a tooth.
DEFAULT_FREEZING_RANGE_C: float = 60.0

# A fixed chill / water-cooled-mold surface temperature (°C) — the Dirichlet BC the enthalpy method needs.
CHILL_MOLD_TEMP_C: float = 100.0

# Niyama critical value (cited criterion; Niyama 1982 / Carlson–Beckermann 2009). Below this, feeding fails
# and shrinkage micro-porosity forms. Expressed in SI (K^½·s^½·m⁻¹); ≈ 0.775 (K·s)^½·mm⁻¹ → ×10³ to m⁻¹.
# Representative / rank-grade — used illustratively (the centre-worst RANKING is the content, not the line).
NIYAMA_CRITICAL_SI: float = 0.775e3

# Latent heat re-exported under a local name (cited; from casting.py — Won & Thomas context).
LATENT_HEAT: float = LATENT_HEAT_FUSION


# --------------------------------------------------------------------------- #
# 1. The regularized enthalpy constitutive path  T ↔ h,  and  D(h)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FreezingPath:
    """The enthalpy ↔ temperature constitutive relation for a steel with a finite freezing range.

    Specific enthalpy ``h(T) = c_p·T + L·f_l(T)`` (reference ``h = 0`` at ``T = 0``), with the **liquid
    fraction** ``f_l`` ramped **smoothly** from 0 at the solidus to 1 at the liquidus by a ``sin²`` profile —
    a numerical regularization (continuous ``dT/dh`` ⇒ the engine's Picard step converges), not a physical
    ``f_l`` claim (see the module docstring). ``temperature``/``specific_enthalpy`` are inverse maps;
    ``diffusivity_of_h`` is ``D(h) = (k/ρ)·dT/dh`` — the nonlinear diffusivity handed to the sealed engine.

    ``T_sol`` / ``T_liq`` solidus / liquidus (°C); ``L`` latent heat (J/kg); ``cp`` / ``k`` / ``rho`` the
    thermophysical constants (defaults: the representative steel values shared with :mod:`steel.cooling`).
    """

    T_sol: float
    T_liq: float
    L: float = LATENT_HEAT
    cp: float = CP_STEEL
    k: float = K_STEEL
    rho: float = RHO_STEEL

    @property
    def freezing_range(self) -> float:
        return self.T_liq - self.T_sol

    @property
    def alpha(self) -> float:
        """Single-phase thermal diffusivity ``α = k/(ρ c_p)`` (m²/s) — outside the freezing range."""
        return self.k / (self.rho * self.cp)

    def liquid_fraction(self, T):
        """Smooth liquid fraction ``f_l(T)`` — 0 below the solidus, 1 above the liquidus, ``sin²`` between."""
        xi = np.clip((np.asarray(T, dtype=float) - self.T_sol) / self.freezing_range, 0.0, 1.0)
        return np.sin(0.5 * np.pi * xi) ** 2

    def solid_fraction(self, T):
        """Solid fraction ``f_s = 1 − f_l`` (1 below the solidus, 0 above the liquidus)."""
        return 1.0 - self.liquid_fraction(T)

    def specific_enthalpy(self, T):
        """Specific enthalpy ``h(T) = c_p·T + L·f_l(T)`` (J/kg) — monotonic in ``T``."""
        T = np.asarray(T, dtype=float)
        return self.cp * T + self.L * self.liquid_fraction(T)

    def apparent_capacity(self, T):
        """Apparent heat capacity ``c_app(T) = dh/dT = c_p + L·df_l/dT`` (J/kg·K).

        ``df_l/dT = (π / 2ΔT)·sin(π (T−T_sol)/ΔT)`` inside the freezing range (zero at both ends, so
        ``c_app`` ramps continuously to ``c_p`` outside — the regularization that makes ``D(h)`` continuous).
        """
        T = np.asarray(T, dtype=float)
        dT = self.freezing_range
        inside = (T >= self.T_sol) & (T <= self.T_liq)
        dfl_dT = np.where(inside, (np.pi / (2.0 * dT)) * np.sin(np.pi * (T - self.T_sol) / dT), 0.0)
        return self.cp + self.L * dfl_dT

    def _table(self, n: int = 200001):
        """Dense (T, h) table for inverting ``h → T`` (built once, cached on first use).

        Spans well below any chill temperature (down to −50 °C) up to a superheat above the liquidus, so the
        ``h → T`` interpolation never clamps over the physical field (the cold chill side included).
        """
        cached = self.__dict__.get("_Th_table")
        if cached is None:
            Tg = np.linspace(-50.0, self.T_liq + 400.0, n)
            Hg = self.specific_enthalpy(Tg)
            object.__setattr__(self, "_Th_table", (Tg, Hg))
            cached = (Tg, Hg)
        return cached

    def temperature(self, h):
        """Temperature ``T(h)`` (°C) — the inverse of :meth:`specific_enthalpy`, by interpolation."""
        Tg, Hg = self._table()
        return np.interp(np.asarray(h, dtype=float), Hg, Tg)

    def diffusivity_of_h(self, h):
        """Nonlinear diffusivity ``D(h) = (k/ρ)·dT/dh = (k/ρ)/c_app(T(h))`` (m²/s) — the engine's ``D_of_u``."""
        T = self.temperature(h)
        return (self.k / self.rho) / self.apparent_capacity(T)


def freezing_path_for(steel: Steel, *, freezing_range_C: float = DEFAULT_FREEZING_RANGE_C) -> FreezingPath:
    """The :class:`FreezingPath` of ``steel``: liquidus from Won & Thomas (:mod:`steel.casting`), solidus
    a representative ``freezing_range_C`` below it."""
    comp = {"C": steel.C, "Mn": steel.Mn, "Si": steel.Si, "Ni": steel.Ni, "Cr": steel.Cr, "Mo": steel.Mo}
    T_liq = liquidus_temperature(comp)
    return FreezingPath(T_sol=T_liq - freezing_range_C, T_liq=T_liq)


# --------------------------------------------------------------------------- #
# 2. The solidification solve — an enthalpy field on the sealed engine, chill BC
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SolidificationField:
    """The solved temperature field ``T(x, t)`` of a chill-cooled section, plus the derived defect reads.

    ``x`` cell-centre positions (m, 0 = chill surface … ``half_thickness`` = insulated thermal centre);
    ``t`` the sample times (s); ``T`` the field, shape ``(len(t), len(x))`` (°C). ``path`` the
    :class:`FreezingPath`; ``chill_T`` / ``T_init`` the BCs (°C). ``enthalpy_drift`` / ``boundary_flux`` the
    two sides of the conservation identity (should match to machine precision). ``solidus_front`` the
    interpolated position of the ``T_sol`` isotherm at each sample time (m) — the freezing front.
    """

    x: np.ndarray
    t: np.ndarray
    T: np.ndarray
    path: FreezingPath
    chill_T: float
    T_init: float
    enthalpy_drift: float
    boundary_flux: float
    solidus_front: np.ndarray


def solidify_chill_slab(
    path: FreezingPath,
    *,
    half_thickness: float = 0.05,
    chill_T: float = CHILL_MOLD_TEMP_C,
    T_init: float | None = None,
    n_cells: int = 200,
    t_end: float | None = None,
    n_t: int = 4000,
) -> SolidificationField:
    """Solidify a planar section against a fixed chill on the sealed :class:`~engines.diffusion.Diffusion1D`.

    Enthalpy mode (``u = h``, ``D = D(h)`` from ``path``): a fixed-temperature chill surface
    (``Dirichlet`` at ``x = 0``) and an insulated thermal centre (``Neumann(0)`` at ``x = half_thickness``,
    the symmetry plane). The state is specific enthalpy; the field is mapped back to temperature for output.
    Conservation is tracked (the chill-end boundary flux vs the enthalpy drift). ``T_init`` defaults to the
    liquidus (a just-poured section at the start of freezing); ``t_end`` defaults to several conduction times.
    """
    if T_init is None:
        T_init = path.T_liq
    if t_end is None:
        t_end = 6.0 * half_thickness ** 2 / path.alpha

    grid = uniform_grid(half_thickness, n_cells)
    H = np.full(n_cells, float(path.specific_enthalpy(T_init)))
    H_chill = float(path.specific_enthalpy(chill_T))
    solver = Diffusion1D(
        grid, D=None, bc_left=Dirichlet(H_chill), bc_right=Neumann(0.0),
        D_of_u=path.diffusivity_of_h, picard_max_iters=400,
    )

    t = np.linspace(0.0, float(t_end), n_t + 1)
    T_field = np.empty((t.size, n_cells))
    T_field[0] = path.temperature(H)
    H0 = solver.total(H)
    flux_acc = 0.0
    for i in range(1, t.size):
        dt = float(t[i] - t[i - 1])
        H = solver.step(H, dt)
        flux_acc += dt * solver.flux(H, "left", t=t[i])     # J in +x at the chill face (heat leaving)
        T_field[i] = path.temperature(H)

    fronts = np.array([_isotherm_position(grid.centers, T_field[i], path.T_sol) for i in range(t.size)])
    return SolidificationField(
        x=grid.centers, t=t, T=T_field, path=path, chill_T=chill_T, T_init=T_init,
        enthalpy_drift=solver.total(H) - H0, boundary_flux=flux_acc, solidus_front=fronts,
    )


def _isotherm_position(centers: np.ndarray, T: np.ndarray, level: float) -> float:
    """Interpolated position (m) where the (chill→centre increasing) field ``T`` first rises through ``level``.

    The temperature rises from the cold chill (``x = 0``) to the hot centre, so the front is the lowest ``x``
    at which ``T`` crosses ``level`` from below. Returns 0 if the whole section is below ``level`` (fully past
    that isotherm) and the centre position if none of it has reached ``level`` yet.
    """
    for j in range(1, len(T)):
        if T[j - 1] < level <= T[j]:
            f = (level - T[j - 1]) / (T[j] - T[j - 1])
            return float(centers[j - 1] + f * (centers[j] - centers[j - 1]))
    return 0.0 if T[-1] < level else float(centers[-1])


# --------------------------------------------------------------------------- #
# 3. The analytic one-phase Stefan / Neumann benchmark — the headline tooth
# --------------------------------------------------------------------------- #
def stefan_number(path: FreezingPath, chill_T: float, *, T_freeze: float | None = None) -> float:
    """One-phase Stefan number ``St = c_p (T_freeze − T_chill) / L`` (dimensionless).

    The ratio of sensible to latent heat driving solidification; ``T_freeze`` defaults to the liquidus (the
    freezing point in the sharp-interface limit the analytic solution describes).
    """
    if T_freeze is None:
        T_freeze = path.T_liq
    return path.cp * (T_freeze - chill_T) / path.L


def stefan_lambda(St: float) -> float:
    """Solve the one-phase Stefan transcendental ``λ·e^{λ²}·erf(λ) = St/√π`` for the front coefficient ``λ``.

    The classic Neumann similarity solution: a semi-infinite melt at the freezing point, surface dropped to a
    fixed temperature, the solid front advances as ``X(t) = 2λ√(αt)`` (:func:`stefan_front`). Closed form,
    no tuning — the analytic answer the numerical field is validated against.
    """
    if St <= 0.0:
        raise ValueError("Stefan number must be positive (chill below the freezing point)")
    # λ grows slowly with St; the bracket [≈0, 6] covers St up to ~10⁴ while keeping exp(λ²) finite.
    return float(brentq(lambda l: l * np.exp(l * l) * erf(l) - St / np.sqrt(np.pi), 1e-9, 6.0))


def stefan_front(t, alpha: float, lam: float):
    """Analytic one-phase Stefan front position ``X(t) = 2λ√(αt)`` (m)."""
    return 2.0 * lam * np.sqrt(alpha * np.asarray(t, dtype=float))


@dataclass(frozen=True)
class StefanValidation:
    """The numerical front vs the analytic one-phase Stefan solution — the headline-tooth comparison.

    ``t`` sample times (s); ``x_numerical`` the ``f_s = 0.5`` isotherm position from the enthalpy solve (m);
    ``x_analytic`` the closed-form ``2λ√(αt)`` (m); ``ratio`` their quotient (→ 1 is the goal). ``lam`` /
    ``St`` the Stefan coefficient & number; ``n_cells`` the grid (refining it pushes ``ratio`` toward 1).
    The isotherm tracked (``f_s = 0.5``, i.e. ``T_mid``) is **consistent** with the Stefan interface
    temperature ``T_freeze = T_mid`` — so the residual is grid resolution, not a definitional offset.
    """

    t: np.ndarray
    x_numerical: np.ndarray
    x_analytic: np.ndarray
    ratio: np.ndarray
    lam: float
    St: float
    n_cells: int


def one_phase_stefan_validation(
    path: FreezingPath,
    *,
    chill_T: float = 25.0,
    domain: float = 0.40,
    n_cells: int = 800,
    n_t: int = 20000,
    t_end: float = 2500.0,
    n_samples: int = 8,
) -> StefanValidation:
    """Validate the enthalpy solver against the analytic one-phase Stefan front (the headline tooth).

    Sets up the Neumann similarity problem the closed form describes — a section initially **fully liquid at
    the freezing point** (the liquidus), a fixed cold chill, and a far end the cooling wave does not reach
    within ``t_end`` (a semi-infinite proxy: insulated, still at the liquidus) — solves it with the same
    enthalpy method as :func:`solidify_chill_slab`, and compares the numerical ``f_s = 0.5`` isotherm to
    ``2λ√(αt)`` with ``λ`` from :func:`stefan_lambda` at ``St = St(T_freeze = T_mid)``. The match is a few
    percent and improves toward 1 as ``n_cells`` grows — a cited, tuning-free benchmark. (The ``ΔT → 0``
    sharp limit *under-resolves* on a fixed grid — a named numerical limit, not a model property.)
    """
    T_mid = 0.5 * (path.T_sol + path.T_liq)
    St = stefan_number(path, chill_T, T_freeze=T_mid)
    lam = stefan_lambda(St)

    grid = uniform_grid(domain, n_cells)
    H = np.full(n_cells, float(path.specific_enthalpy(path.T_liq)))     # fully liquid at the liquidus
    H_chill = float(path.specific_enthalpy(chill_T))
    solver = Diffusion1D(
        grid, D=None, bc_left=Dirichlet(H_chill), bc_right=Neumann(0.0),
        D_of_u=path.diffusivity_of_h, picard_max_iters=400,
    )

    t = np.linspace(0.0, float(t_end), n_t + 1)
    sample_idx = np.unique(np.linspace(n_t // n_samples, n_t, n_samples, dtype=int))
    ts, xs = [], []
    for i in range(1, t.size):
        dt = float(t[i] - t[i - 1])
        H = solver.step(H, dt)
        if i in sample_idx:
            ts.append(t[i])
            xs.append(_isotherm_position(grid.centers, path.temperature(H), T_mid))
    ts = np.asarray(ts)
    x_num = np.asarray(xs)
    x_ana = np.asarray(stefan_front(ts, path.alpha, lam))
    return StefanValidation(
        t=ts, x_numerical=x_num, x_analytic=x_ana, ratio=x_num / x_ana, lam=lam, St=St, n_cells=n_cells,
    )


def isotherm_front(field: "SolidificationField", level: float) -> np.ndarray:
    """The position (m) of the ``level``-°C isotherm at each sample time of ``field`` (for plotting the map)."""
    return np.array([_isotherm_position(field.x, field.T[i], level) for i in range(field.t.size)])


# --------------------------------------------------------------------------- #
# 4. Casting defect criteria — Niyama porosity & hot-tear susceptibility (illustrative, by-construction)
# --------------------------------------------------------------------------- #
def niyama(gradient_K_per_m, cooling_rate_K_per_s):
    """Niyama criterion ``Ny = G / √Ṫ`` (SI: ``(K/m)/√(K/s)``) — shrinkage-porosity indicator.

    Cited criterion *form* (Niyama 1982; Carlson–Beckermann 2009): porosity forms where the thermal gradient
    ``G`` is shallow and the cooling rate ``Ṫ`` slow (feeding cannot keep up). Low ``Ny`` ⇒ porosity-prone.
    The criterion is applied at the **solidus crossing**. **Illustrative / by-construction** — the centre's
    being worst follows directly from its small ``G`` and ``Ṫ``; :data:`NIYAMA_CRITICAL_SI` is rank-grade.
    """
    G = np.asarray(gradient_K_per_m, dtype=float)
    Rdot = np.asarray(cooling_rate_K_per_s, dtype=float)
    return G / np.sqrt(np.maximum(Rdot, 1e-30))


def _crossing_time(t: np.ndarray, col: np.ndarray, level: float) -> float:
    """Interpolated time at which a (cooling) temperature history ``col`` first drops through ``level`` (s).

    Returns ``nan`` if it never crosses or starts already below (a chill-pinned cell)."""
    crossed = np.where(col <= level)[0]
    if crossed.size == 0 or crossed[0] == 0:
        return float("nan")
    i = crossed[0]
    f = (col[i - 1] - level) / (col[i - 1] - col[i])
    return float(t[i - 1] + f * (t[i] - t[i - 1]))


def local_solidification_time(field: SolidificationField):
    """``(x, t_sol)``: the time each location takes to cool through the solidus (s) — the hot-spot map.

    The cleanest, monotone defect-localization read (**by construction**): the insulated thermal centre is
    the **last to freeze**, so it is the shrinkage hot spot — and it is the *same* centre Slice 1
    (:mod:`steel.casting`) showed is alloy-enriched, so shrinkage porosity and macro-segregation concentrate
    in one place for two independent reasons. Chill-pinned cells (already solid) are ``nan``.
    """
    Tsol = field.path.T_sol
    return field.x, np.array([_crossing_time(field.t, field.T[:, j], Tsol) for j in range(field.x.size)])


def niyama_field(field: SolidificationField):
    """``(x, Ny)``: the Niyama number across the section, the cited shrinkage-porosity criterion (illustrative).

    Evaluated at the solidus crossing with a **freezing-range traverse** cooling rate ``Ṫ = ΔT_freeze /
    (t_solidus − t_liquidus)`` (less initial-transient-sensitive than a single-step difference) and a centred
    spatial gradient ``G``. **By construction, not a tooth** (see :func:`niyama`): ``Ny`` is ~constant across
    the directionally-solidified region — *the* textbook signature that a chill produces sound, directional
    structure — and collapses toward the insulated centre where ``G → 0``, the porosity-prone core. The chill
    cell (pinned) and any location that does not fully solidify are ``nan``.
    """
    x, t, T = field.x, field.t, field.T
    Tsol, Tliq = field.path.T_sol, field.path.T_liq
    ny = np.full(x.size, np.nan)
    for j in range(x.size):
        col = T[:, j]
        t_sol, t_liq = _crossing_time(t, col, Tsol), _crossing_time(t, col, Tliq)
        if not (np.isfinite(t_sol) and np.isfinite(t_liq)) or t_sol <= t_liq:
            continue
        Rdot = field.path.freezing_range / (t_sol - t_liq)         # traverse cooling rate (K/s)
        i = int(np.searchsorted(t, t_sol))
        if i >= t.size:
            i = t.size - 1
        jl, jr = max(j - 1, 0), min(j + 1, x.size - 1)
        G = abs(T[i, jr] - T[i, jl]) / (x[jr] - x[jl])             # centred spatial gradient (K/m)
        ny[j] = niyama(G, Rdot)
    return x, ny


def porosity_prone_fraction(field: SolidificationField) -> float:
    """Fraction of the (solidified) section whose Niyama number is below :data:`NIYAMA_CRITICAL_SI` (illustrative)."""
    _, ny = niyama_field(field)
    valid = ny[~np.isnan(ny)]
    if valid.size == 0:
        return 0.0
    return float(np.mean(valid < NIYAMA_CRITICAL_SI))
