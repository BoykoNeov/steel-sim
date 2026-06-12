"""Residual stress & distortion on quench — the solid-mechanics axis (Steel Phase 6f / §11 Option-#2).

Every phase up to here answered *what the steel becomes* (microstructure, hardness, yield, DBTT).
This module answers a different question — *what the quench does to the part*: the **residual stress**
locked into a section by a quench, and the quench-crack / distortion risk that follows. It is the one
genuinely new modelling axis left on the §11 menu, the first to introduce **solid mechanics**, and the
piece that makes the §17 martempering distortion story *quantitative in stress* instead of a thermal proxy.

Why a quench leaves stress behind (the mechanism)
-------------------------------------------------
A quench drives two stress-free ("eigen") strains that vary through the section because temperature and
phase vary through the section:

1. **Thermal contraction** ``ε_th = α·(T − T_ref)`` — the surface cools (contracts) before the core.
2. **Transformation dilatation** ``ε_tr·f_M`` — austenite (FCC, dense) shearing to martensite (BCT)
   *expands* ~1 % linear; the surface reaches ``Mₛ`` and expands while the core is still austenite.

Neither strain alone leaves residual stress: if the part ends uniform in temperature and phase the
eigenstrain is uniform and a purely elastic body relaxes to zero. **Residual stress is path-dependent** —
it is locked in by *plastic yielding while the steel is hot and soft*. That is why this is genuinely
solid mechanics and not an elastic misfit calculation: the model must march the quench incrementally and
let fibres yield (temperature-dependent yield strength), so the order in which regions contract and
transform is permanently recorded.

The two competing residual-stress signs (the headline teeth)
------------------------------------------------------------
* **Thermal alone** (or transformation suppressed): the surface contracts first and is stretched by the
  hot core, the hot core yields in compression, then on final equalisation the plastically-shortened core
  pulls the surface into **compression** (core tension). Surface compression — *benign*, even beneficial.
* **With transformation** (a through-hardening quench): the surface transforms (expands) first and is
  locked in compression, then the **core transforms last** and its late expansion stretches the now-hard
  martensitic surface into **tension** (core compression). Surface tension — the **quench-crack-prone**
  state. The transformation dilatation *flips the sign*.

So the same steel and quench give opposite surface signs depending on whether transformation is active —
the cleanest demonstration of the mechanism (and the way to show *both* signs, since both anchored atlas
steels are through-hardeners: see :func:`quench_residual_stress` with ``transform=True``/``False``).

The mechanical model (1-D plate, equibiaxial, perfectly plastic)
----------------------------------------------------------------
A planar slab of full thickness ``2·half_thickness`` cooled symmetrically on both faces — exactly the
geometry :func:`steel.martemper.slab_thermal_history` already marches on the **frozen heat engine**
(:mod:`engines.diffusion`). For an infinite plate with traction-free faces the through-thickness stress
is zero and the in-plane stress is **equibiaxial** ``σ(x) = σ_yy = σ_zz``; by compatibility every fibre
shares one membrane strain ``ε*`` (the plate stays flat, symmetric ⇒ no bending), and equilibrium is the
single condition **∫σ dx = 0** (zero net in-plane force). The elastic law for the equibiaxial state is

    σ(x) = E(T)/(1 − ν) · ε_el(x),     ε_el = ε* − ε_free − ε_pl,

and von Mises yield for equibiaxial stress is simply ``|σ| ≤ σ_Y(T)``. Each time step is a standard
return-map: form the elastic-trial stress, clip it to ``±σ_Y`` (the excess becoming plastic strain),
and solve ``∫σ dx = 0`` for ``ε*`` (the clipped stress is monotone in ``ε*`` ⇒ a bisection). The residual
field is the stress at the final uniform-temperature state — non-zero because the **plastic strain** left
behind is non-uniform, and self-equilibrated (``∫σ dx = 0``) by construction (the free conservation leg).

Cited vs representative (the discipline — no number fitted to a stress measurement)
-----------------------------------------------------------------------------------
* **CITED** — the martensite/austenite **lattice parameters** that set the transformation dilatation
  (Roberts / Kurdjumov–Lyssak relations, :func:`transformation_dilatation`); the **Eurocode 3** elevated-
  temperature reduction factors for steel modulus ``E(T)`` and yield ``σ_Y(T)`` (the standard cited
  elevated-T property curves, :func:`youngs_modulus` / :func:`yield_strength`); Andrews ``Mₛ`` and
  Koistinen–Marburger (inherited); the frozen conduction solver and ``ρ, c_p, k`` (inherited).
* **REPRESENTATIVE** — ``ν = 0.30``, the room-temperature base modulus ``E₂₀ = 210 GPa``, the
  representative yield base ``σ_Y,20`` and the mean thermal-expansion ``α`` (same status as ``ρ, c_p, k``).
* **NOT FITTED** — nothing here is calibrated to a residual-stress dataset. The **absolute** stress
  magnitude scales with the representative yield base and ``α`` (a named scope edge); the **teeth are
  structural** — the surface-sign reversal (transformation ON vs OFF), self-equilibrium to machine
  precision, peak ``|σ|`` of order the yield, and martemper < direct-quench surface tension — none of
  which depend on the exact property values. This is the same "read the shape, not the absolute number"
  stance as §14/§16/§17.

Named scope edges (each a real limit, not hidden)
-------------------------------------------------
* **No transformation plasticity (TRIP / Greenwood–Johnson).** The dominant *secondary* mechanism —
  enhanced plastic flow under stress *during* transformation (Leblond) — is a whole second model and is
  **not** included. It would raise the locked-in stresses; the signs and rankings are unaffected. The
  #1 deferred refinement.
* **Through-hardening (martensitic) only.** Every cell is taken to martensite by Koistinen–Marburger on
  its own thermal history — i.e. a *through-hardening* section (the anchored 1080-thin / 4340 case). The
  hardenability-limited case (a slow core forming pearlite/bainite with a *different*, smaller dilatation)
  is **not** modelled — the diffusional-product misfit is a deferred edge. (This is why the route
  comparison is honest: both routes through-harden, so the difference is the *timing*, not the product.)
* **One-way coupling, no latent-heat feedback.** Mechanical dissipation does not reheat the part, and the
  transformation latent heat is not fed back into the frozen thermal solve (it would slightly slow the
  near-``Mₛ`` cooling). Standard one-way thermo-mechanical staggering.
* **Elastic–perfectly-plastic, single σ_Y(T).** No strain hardening, no creep, and yield is *not* phase-
  split (the much harder martensite is not given a separate high yield) — so the surface-tension peak is
  capped at the representative ``σ_Y,20`` rather than the martensite strength. A representative magnitude.
* **Absolute magnitude is property-sensitive.** Scales with ``σ_Y,20``, ``α`` and the cited dilatation;
  the model targets signs / rankings / orders, not a specific published stress profile (geometry- and
  heat-transfer-specific — the named fitting trap, avoided).

Units: lengths m, temperatures °C, time s, stress Pa (reported MPa via the ``*_MPa`` helpers), strains
dimensionless. Compositions wt%, fractions in [0, 1] — matching :mod:`kinetics` / :mod:`martemper`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from engines.diffusion import uniform_grid

from . import cooling
from .austemper import ATLAS_STEELS
from .kinetics import KM_ALPHA, andrews_Ms
from .martemper import SlabHistory, slab_thermal_history

# --------------------------------------------------------------------------- #
# 1. Representative mechanical / thermal constants (cited where it matters)
# --------------------------------------------------------------------------- #
POISSON = 0.30                  # Poisson's ratio ν (standard for steel; constant)
E_REF_20C = 210.0e9             # room-temperature Young's modulus E₂₀ (Pa) — standard
SIGMA_Y_REF_20C = 400.0e6       # representative room-temperature yield base σ_Y,20 (Pa)
ALPHA_THERMAL = 1.5e-5          # representative mean linear thermal-expansion coefficient (1/K)
T_REF_STRAIN = 25.0             # reference T for thermal strain (°C) — immaterial to σ (absorbed by ε*)

# Eurocode 3 Part 1-2 elevated-temperature reduction factors for carbon steel (Table 3.1): the
# standard *cited* temperature dependence of the Young's modulus (k_E) and effective yield (k_y).
# Used as the multiplicative T-shape on the representative room-T bases above — so the *temperature
# dependence* is cited, not invented, and only the room-T magnitudes are representative.
_EC3_T = np.array([20.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0,
                   700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0])
_EC3_KE = np.array([1.000, 1.000, 0.900, 0.800, 0.700, 0.600, 0.310,
                    0.130, 0.090, 0.0675, 0.0450, 0.0225, 0.000])
_EC3_KY = np.array([1.000, 1.000, 1.000, 1.000, 1.000, 0.780, 0.470,
                    0.230, 0.110, 0.060, 0.040, 0.020, 0.000])


def youngs_modulus(T: float | np.ndarray) -> float | np.ndarray:
    """Young's modulus ``E(T)`` (Pa) — ``E₂₀`` scaled by the cited Eurocode-3 reduction factor ``k_E(T)``.

    Monotonically decreasing in ``T`` (steel softens when hot): ``E₂₀ = 210 GPa`` at room temperature,
    falling to ~30 % near 600 °C and a small residual at the austenitizing temperature. ``T`` in °C may
    be a scalar or array; values outside the tabulated 20–1200 °C range are clamped to the end factors.
    """
    k = np.interp(np.asarray(T, dtype=float), _EC3_T, _EC3_KE)
    out = E_REF_20C * k
    return float(out) if out.ndim == 0 else out


def yield_strength(T: float | np.ndarray) -> float | np.ndarray:
    """Yield strength ``σ_Y(T)`` (Pa) — ``σ_Y,20`` scaled by the cited Eurocode-3 factor ``k_y(T)``.

    The temperature-dependent flow stress that governs how much the section yields *while hot* (the
    plastic lock-in that creates residual stress). Full ``σ_Y,20`` up to ~400 °C, then dropping steeply
    (hot austenite is soft). ``T`` in °C, scalar or array; clamped outside 20–1200 °C. **Single yield
    for all phases** — the harder martensite is not given a separate value (a named scope edge), so the
    locked surface tension is capped at the representative ``σ_Y,20``.
    """
    k = np.interp(np.asarray(T, dtype=float), _EC3_T, _EC3_KY)
    out = SIGMA_Y_REF_20C * k
    return float(out) if out.ndim == 0 else out


# --------------------------------------------------------------------------- #
# 2. Transformation dilatation from cited lattice parameters
# --------------------------------------------------------------------------- #
# Lattice-parameter relations (Å, wt% C). Austenite FCC (4 atoms/cell): a_γ = 3.548 + 0.044·C
# (Roberts 1953 / the standard γ-Fe(C) relation). Martensite BCT (2 atoms/cell), Kurdjumov–Lyssak:
# a = 2.8664 − 0.0028·C, c = 2.8664 + 0.0116·C. The γ→α′ *volume* change is V_α′/V_γ − 1 with
# V_γ = a_γ³/4, V_α′ = a²c/2; the **linear** transformation strain is ⅓ of that. These are the cited
# textbook relations (Honeycombe & Bhadeshia, *Steels*); the absolute dilatation is source-sensitive
# (a named edge) but the carbon trend and ~1 % magnitude are robust.
_A_GAMMA_0 = 3.548
_A_GAMMA_C = 0.044
_A_MART_0 = 2.8664
_A_MART_C = -0.0028
_C_MART_0 = 2.8664
_C_MART_C = 0.0116


def volume_change_gamma_to_martensite(C: float) -> float:
    """Relative **volume** change ``ΔV/V`` for austenite → martensite at carbon ``C`` (wt%).

    From the cited lattice parameters: ``V_γ = a_γ³/4`` (FCC) and ``V_α′ = a²c/2`` (BCT). Positive (the
    transformation expands); decreases with carbon (austenite expands with C faster than martensite),
    ~5 % at low carbon to ~2–3 % near eutectoid — the standard dilatometric figures.
    """
    a_g = _A_GAMMA_0 + _A_GAMMA_C * C
    a_m = _A_MART_0 + _A_MART_C * C
    c_m = _C_MART_0 + _C_MART_C * C
    V_gamma = a_g**3 / 4.0
    V_mart = a_m**2 * c_m / 2.0
    return V_mart / V_gamma - 1.0


def transformation_dilatation(C: float) -> float:
    """**Linear** transformation strain ``ε_tr = ⅓·ΔV/V`` for γ → martensite at carbon ``C`` (wt%).

    The isotropic linear eigenstrain a fully-martensitic cell carries relative to austenite — the
    quantity multiplied by the local Koistinen–Marburger martensite fraction in the eigenstrain field.
    ~0.9–1.3 % for the anchored steels; the source of the surface-tension sign flip.
    """
    return volume_change_gamma_to_martensite(C) / 3.0


# --------------------------------------------------------------------------- #
# 3. The incremental elastic–perfectly-plastic membrane solve
# --------------------------------------------------------------------------- #
def _solve_membrane_strain(
    M: np.ndarray, a: np.ndarray, sigma_Y: np.ndarray, n_iter: int = 80
) -> tuple[np.ndarray, float]:
    """Find the membrane strain ``ε*`` enforcing ``mean(σ) = 0`` for clipped trial stress, and return ``σ``.

    Per cell the elastic-trial stress is ``σ_trial = M·(ε* − a)`` with ``a = ε_free + ε_pl`` (the part of
    the total strain already spent on eigenstrain + accumulated plastic strain), and the actual stress is
    the von-Mises clip ``σ = clip(σ_trial, ±σ_Y)``. ``mean(σ)`` is monotone non-decreasing in ``ε*`` and
    spans ``[−mean(σ_Y), +mean(σ_Y)]``, so the equilibrium root is found by bisection. Uniform cells make
    ``∫σ dx = 0`` equivalent to ``mean(σ) = 0``. Returns ``(σ, ε*)``.
    """
    # Bracket: the all-compressive and all-tensile extremes plus a margin guarantee a sign change.
    span = float(np.max(sigma_Y) / np.min(M)) if np.min(M) > 0 else 1.0
    lo = float(np.min(a)) - span - 1.0
    hi = float(np.max(a)) + span + 1.0
    for _ in range(n_iter):
        mid = 0.5 * (lo + hi)
        sigma = np.clip(M * (mid - a), -sigma_Y, sigma_Y)
        if sigma.mean() > 0.0:
            hi = mid
        else:
            lo = mid
    eps_star = 0.5 * (lo + hi)
    sigma = np.clip(M * (eps_star - a), -sigma_Y, sigma_Y)
    return sigma, eps_star


@dataclass(frozen=True)
class ResidualStressField:
    """The residual-stress solution for a quenched plate — the room-temperature locked-in profile.

    ``x`` are cell-centre depths from the centreline (m, ``0`` = core, ``half_thickness`` = surface);
    ``sigma`` is the final in-plane residual stress profile (Pa, tensile +); ``sigma_history`` the full
    ``(n_t, n_cells)`` stress field through the quench (for the figure/animation). ``surface_stress`` /
    ``center_stress`` are the surface and core residuals (Pa); ``peak_tension`` / ``peak_compression`` the
    profile extremes. ``mean_stress`` is the self-equilibrium residual (``∫σ dx`` ÷ thickness — ``≈ 0`` to
    machine precision, the conservation leg). ``transform`` records whether the transformation dilatation
    was active (the ON/OFF toggle); ``route`` the quench path; ``slab`` the underlying thermal history.
    """

    steel: str
    route: str
    transform: bool
    half_thickness: float
    Ms: float
    x: np.ndarray
    sigma: np.ndarray
    sigma_history: np.ndarray
    surface_stress: float
    center_stress: float
    peak_tension: float
    peak_compression: float
    mean_stress: float
    slab: SlabHistory

    @property
    def surface_MPa(self) -> float:
        """Surface residual stress in MPa (tensile +) — the quench-crack-risk number."""
        return self.surface_stress / 1.0e6

    @property
    def center_MPa(self) -> float:
        """Core (centreline) residual stress in MPa (tensile +)."""
        return self.center_stress / 1.0e6

    @property
    def crack_risk(self) -> bool:
        """Whether the surface ends in **tension** — the quench-crack-prone state (transformation sign)."""
        return self.surface_stress > 0.0

    def sigma_MPa(self) -> np.ndarray:
        """The residual profile in MPa (tensile +)."""
        return self.sigma / 1.0e6


def quench_residual_stress(
    steel: str,
    half_thickness: float,
    route: str = "direct",
    transform: bool = True,
    T0: float = 850.0,
    T_bath: float | None = None,
    t_hold: float | None = None,
    h_quench: float = cooling.H_WATER,
    h_slow: float = cooling.H_AIR,
    T_env: float = 25.0,
    n_cells: int = 120,
    n_t: int = 8000,
) -> ResidualStressField:
    """Residual stress locked into a quenched plate of a named atlas steel — the solid-mechanics solve.

    Marches :func:`steel.martemper.slab_thermal_history` for the through-thickness temperature field
    ``T(x, t)`` (``route="direct"`` = single-stage water quench; ``route="martemper"`` = quench into a
    bath ``Mₛ + 20`` °C, hold, slow-cool), then advances the incremental elastic–perfectly-plastic
    equibiaxial-plate mechanics on it: at each step the eigenstrain (thermal contraction + the
    Koistinen–Marburger martensite dilatation, the latter only if ``transform=True``) drives a
    return-mapped membrane solve enforcing ``∫σ dx = 0``. The returned ``sigma`` is the residual at the
    final uniform-temperature state.

    Set ``transform=False`` for the **thermal-only** reference (no transformation dilatation) — paired
    with the default ``transform=True`` it exhibits the surface-sign reversal (compression → tension)
    that is the model's headline tooth. ``steel`` must be an anchored atlas steel
    (:data:`~steel.austemper.ATLAS_STEELS`); ``route`` one of ``"direct"`` / ``"martemper"``.
    """
    if steel not in ATLAS_STEELS:
        raise ValueError(f"no atlas anchor for steel {steel!r} — anchored: {sorted(ATLAS_STEELS)}")
    if route not in ("direct", "martemper"):
        raise ValueError(f"route must be 'direct' or 'martemper', got {route!r}")

    s = ATLAS_STEELS[steel]
    C = s.comp["C"]
    Ms = andrews_Ms(**s.comp)
    eps_tr = transformation_dilatation(C)

    if T_bath is None:
        T_bath = Ms + 20.0
    if route == "martemper" and t_hold is None:
        # A generous equalisation hold (several conduction times) — the §17 default.
        alpha = cooling.K_STEEL / (cooling.RHO_STEEL * cooling.CP_STEEL)
        t_hold = 6.0 * half_thickness**2 / alpha

    slab = slab_thermal_history(
        half_thickness, T0, h_quench, T_bath,
        t_hold=(t_hold if route == "martemper" else None),
        h_slow=h_slow, T_env=T_env, n_cells=n_cells, n_t=n_t,
    )

    T = slab.T                                  # (n_t+1, n_cells), col 0 = centre, col -1 = surface
    n_steps = T.shape[0]

    # Koistinen–Marburger martensite fraction is athermal & irreversible → set by the *deepest*
    # undercooling reached so far: f_M(x, t) = KM(running-min T(x, ·≤t), Ms). Vectorised over the field.
    T_min = np.minimum.accumulate(T, axis=0)
    if transform:
        under = np.clip(Ms - T_min, 0.0, None)
        f_M = 1.0 - np.exp(-KM_ALPHA * under)    # vectorised kinetics.koistinen_marburger over the field
    else:
        f_M = np.zeros_like(T)

    eps_free = ALPHA_THERMAL * (T - T_REF_STRAIN) + eps_tr * f_M

    eps_pl = np.zeros(T.shape[1])
    sigma_history = np.empty_like(T)
    sigma_history[0] = 0.0                       # uniform T0, no transformation, no plastic strain → σ=0
    for i in range(1, n_steps):
        Ti = T[i]
        M = youngs_modulus(Ti) / (1.0 - POISSON)         # equibiaxial stiffness E/(1−ν)
        sigma_Y = yield_strength(Ti)
        a = eps_free[i] + eps_pl                          # strain already spent (eigen + plastic)
        # Return-map: solve ε* for equilibrium with the clipped (yield-capped) stress, then read the
        # plastic increment as the clipped overflow. On elastic cells σ_trial = σ ⇒ no plastic increment;
        # on yielded cells the excess (σ_trial − ±σ_Y)/M is absorbed into ε_pl.
        sigma, eps_star = _solve_membrane_strain(M, a, sigma_Y)
        sigma_trial = M * (eps_star - a)
        eps_pl = eps_pl + (sigma_trial - sigma) / M
        sigma_history[i] = sigma

    sigma_final = sigma_history[-1]
    return ResidualStressField(
        steel=steel, route=route, transform=transform,
        half_thickness=half_thickness, Ms=Ms,
        x=uniform_grid(half_thickness, n_cells).centers,  # cell-centre depths (0 = core)
        sigma=sigma_final,
        sigma_history=sigma_history,
        surface_stress=float(sigma_final[-1]),
        center_stress=float(sigma_final[0]),
        peak_tension=float(sigma_final.max()),
        peak_compression=float(sigma_final.min()),
        mean_stress=float(sigma_final.mean()),
        slab=slab,
    )


# --------------------------------------------------------------------------- #
# 4. The route comparison — making the §17 distortion story quantitative in stress
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ResidualComparison:
    """Direct-quench vs martemper residual stress for one slab — the §17 payoff, now in stress.

    ``surface_direct`` / ``surface_martemper`` are the surface residual stresses (Pa, tensile +) of the
    two routes; ``reduction`` the factor by which martempering shrinks the surface tension's magnitude
    (the quantitative quench-crack benefit). The §17 ``DistortionComparison`` read a surface−centre
    *temperature* gradient as a distortion *proxy*; this reads the actual residual *stress* the gradient
    produces. The two :class:`ResidualStressField` objects carry the full profiles for the figure.
    """

    steel: str
    half_thickness: float
    Ms: float
    surface_direct: float
    surface_martemper: float
    reduction: float
    direct: ResidualStressField
    martemper: ResidualStressField

    @property
    def surface_direct_MPa(self) -> float:
        """Direct-quench surface residual stress (MPa, tensile +)."""
        return self.surface_direct / 1.0e6

    @property
    def surface_martemper_MPa(self) -> float:
        """Martemper surface residual stress (MPa, tensile +)."""
        return self.surface_martemper / 1.0e6


def residual_comparison(
    steel: str,
    half_thickness: float,
    T0: float = 850.0,
    h_quench: float = cooling.H_WATER,
    h_slow: float = cooling.H_AIR,
    T_env: float = 25.0,
    n_cells: int = 120,
    n_t: int = 8000,
) -> ResidualComparison:
    """Compare the residual stress of a direct quench and a martemper of the same atlas-steel slab.

    Runs :func:`quench_residual_stress` twice (``route="direct"`` and ``route="martemper"``, both with
    transformation active) and reads the surface residual of each. Martempering equalises the section
    below the nose and takes it through ``Mₛ`` slowly and near-uniformly, so the surface transforms
    almost in step with the core — far less of the late-core-expansion that stretches a direct-quenched
    surface into tension. The ``reduction`` factor is the quantitative, stress-based statement of the
    §17 distortion benefit (which measured only the thermal gradient proxy).
    """
    direct = quench_residual_stress(
        steel, half_thickness, route="direct", transform=True,
        T0=T0, h_quench=h_quench, h_slow=h_slow, T_env=T_env, n_cells=n_cells, n_t=n_t,
    )
    marte = quench_residual_stress(
        steel, half_thickness, route="martemper", transform=True,
        T0=T0, h_quench=h_quench, h_slow=h_slow, T_env=T_env, n_cells=n_cells, n_t=n_t,
    )
    s_d = direct.surface_stress
    s_m = marte.surface_stress
    reduction = abs(s_d) / abs(s_m) if s_m != 0.0 else float("inf")
    return ResidualComparison(
        steel=steel, half_thickness=half_thickness, Ms=direct.Ms,
        surface_direct=s_d, surface_martemper=s_m, reduction=reduction,
        direct=direct, martemper=marte,
    )
