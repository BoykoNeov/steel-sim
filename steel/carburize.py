"""Carburizing case-hardening: the mass-diffusion face of the spine (Steel Phase 3c).

Phase 2 reused the frozen :mod:`engines.diffusion` in **heat mode** (the Jominy
bar). Phase 3c reunites the other face: the *same* sealed engine in **mass mode**,
computing the surface-enriched carbon profile of a **carburized** part, then feeding
position-dependent ``%C`` through the transformation + property model already built
in 1c/2c/3a → a **case-hardened hardness gradient** (a hard, wear-resistant martensite
case over a tougher, lower-carbon core). This is the carbon-diffusion code the whole
program was scaffolded around (CONTRACT.md "mass mode"); here it finally pays off.

The process, and the textbook solution
--------------------------------------
A low-carbon steel (core ``C0 ≈ 0.2 %``, an 8620/9310-grade chosen for core
toughness) is held at an austenitizing temperature ``T_carb ≈ 900–930 °C`` in a
carbon-rich atmosphere. Carbon dissolves at the surface up to the atmosphere's
**carbon potential** ``Cs`` (held fixed → a Dirichlet boundary) and diffuses inward.
For a constant surface concentration into a semi-infinite solid with constant ``D``,
Fick's second law has the **error-function** solution

    (C(x, t) − C0) / (Cs − C0) = erfc( x / (2·√(D·t)) )                    (the erfc law)

— the program's headline analytical limit, now in its native carbon-into-austenite
instantiation. The **case depth** (depth to a chosen carbon level — conventionally
the *effective case depth* to ``0.4 % C``) is the level set of the self-similar
variable ``x / 2√(Dt)``, so it scales as

    x_case(t) = 2·erfc⁻¹( (C_th − C0)/(Cs − C0) ) · √(D·t)   ∝ √(D·t)      (exact)

— the "case depth ∝ √(Dt)" of the plan's Phase-3 triad, exact for isothermal
carburizing. After carburizing the part is quenched: the high-carbon case shears to
hard martensite, the low-carbon core stays softer (and tough). The hardness *traverse*
falls from ~63–65 HRC at the surface to a softer core — set by the **carbon gradient**,
not a cooling-rate gradient (see "What 3c isolates").

How the frozen solver is reused (mass mode)
-------------------------------------------
The engine solves ``∂u/∂t = ∂/∂x(D ∂u/∂x)`` directly with ``u = %C`` and ``D =``
:func:`carbon_diffusivity` ``(T_carb)`` — a **constant scalar** at a fixed carburizing
temperature, which is exactly the case the erfc solution is exact for. The boundaries
are the two the contract ships:

  * **surface** ``x = 0`` → :class:`~engines.diffusion.Dirichlet` at the carbon
    potential ``Cs`` (the fixed-surface-concentration erfc condition), and
  * **core / centreline** ``x = L`` → :class:`~engines.diffusion.Neumann` ``(0)``
    (no-flux): both the symmetry plane of a tooth *and* the semi-infinite far field,
    provided ``L`` is deep enough that the carbon never reaches it.

No operator splitting, no source term — unlike the Jominy fin, carburizing is *pure*
diffusion, so the engine is used unadorned. The carbon-uptake bookkeeping rides the
engine's **frozen flux identity**: with backward Euler, ``total(stepped) − total(state)
= dt·(flux(left) − flux(right))`` *exactly*, and the right end is no-flux, so the
accumulated surface-flux integral ``Σ dt·flux(left)`` equals the rise in ``∫C dx`` to
machine precision — the conservation leg ("carbon mass uptake = surface flux integrated
over time"). This is the engine's own guarantee re-instantiated, needing **no new
calibration** — the cleanest validation legs in the project.

The one physics input — carbon diffusivity (cited, not fitted)
--------------------------------------------------------------
The only new physical constant is the Arrhenius diffusivity of carbon in austenite
(:data:`D0_CARBON_AUSTENITE`, :data:`Q_CARBON_AUSTENITE`) — the **cited** Callister/
Shewmon value for C in FCC γ-iron, the same ``D₀ ≈ 2.3e-5 m²/s, Q ≈ 148 kJ/mol`` the
CONTRACT names as the mass-mode example. Crucially it is anchored to *diffusion* data,
**not** fit to case-depth tables — so the case-depth benchmark (below) is a genuine
cross-check, exactly as the martensite hardness (anchored to Hodge–Orehoski, not to
carburizing) makes the surface-hardness benchmark a cross-check.

What 3c isolates — the **composition** gradient (not the cooling-rate one)
--------------------------------------------------------------------------
The four-curves (1c) and Jominy (2) artifacts produced hardness gradients from a
**cooling-rate** gradient (one steel, position-varying thermal history). Carburizing
produces one from a **carbon** gradient (position-varying *composition*, one quench).
To isolate that cleanly, :func:`carburized_traverse` applies a **single** cooling path
at every depth and varies only ``C(x)`` (hence ``Ms(C)``, the C-curve, the hardness).
This is faithful, not a shortcut: across the thin (~1 mm) case the quench equilibrates
thermally in well under the transformation time (``√(αt) ≈ 2.5 mm at 1 s``, the same
timescale argument :mod:`jominy` uses), so the case's hardness gradient really is
carbon-driven. The cooling-rate gradient is the prior phases' subject; the carbon
gradient is this one's.

The benchmark fork — surface hardness vs the retained-austenite the kinetics predict
------------------------------------------------------------------------------------
Running the full transformation model (:func:`pathint.transform_along_path`) at the
high-carbon surface exposes a real, well-documented effect: a 0.8–1.0 %C austenite has
a low ``Ms`` (Andrews: ``Ms ≈ 160 °C`` at 0.8 %C, ``~75 °C`` at 1.0 %C for this alloy),
so a room-temperature quench leaves **substantial retained austenite** (Koistinen–
Marburger: ~22 % RA at Cs = 0.8, ~58 % at Cs = 1.0). Retained austenite is soft, and a
rule-of-mixtures hardness that includes it reads *below* the 62–65 HRC a real hardened
case shows. This is genuine physics (RA in heavy cases is real, and is why production
practice minimizes it with sub-zero treatment / tempering / alloy control), **but it is
also where the kinetics chain is being pushed past its anchored carbon range** (Andrews
``Ms``, Koistinen–Marburger, and the √C martensite curve were all anchored ~0.4–0.8 %C;
the surface sits at the top of, or just past, that range). So, following the same
non-circularity discipline as the 1045 knee and the bainite deferral:

  * The **surface-hardness benchmark** is anchored to the martensite **potential**
    ``HV = `` :func:`~steel.properties.vickers_martensite` ``(C_surface, comp)``
    — the hardness of the case *as designed* (martensite by intent), which is what a
    published surface-hardness spec represents. This is the clean cross-check to the
    independently-anchored as-quenched-martensite curve. It is :attr:`CarburizedTraverse.HV`.
  * The **microstructure gradient** is the full ``transform_along_path`` per depth,
    which *does* show retained austenite rising toward the surface — reported as the real
    phase gradient (:attr:`CarburizedTraverse.retained_austenite`) and an honest
    as-quenched hardness (:attr:`CarburizedTraverse.HV_as_quenched`, with the RA drag),
    but **not** asserted against the published surface band.

So the two hardness curves coincide through the core (full martensite there, ~0.96 fM
for this alloy) and separate only near the high-carbon surface — the visible signature
of the RA the heavy case carries.

What is validated vs what is calibrated (the project's standing split)
----------------------------------------------------------------------
  * **VALIDATED (tight, no calibration):** the erfc profile (constant ``D`` + Dirichlet
    — the frozen engine's analytical limit, re-confirmed in carbon mass mode); the case
    depth ∝ √(Dt) scaling (exact, from the self-similar variable); and carbon-mass
    conservation = surface-flux integral (the engine's exact backward-Euler identity).
  * **ANCHORED (independent data, so the benchmarks are cross-checks):** the carbon
    diffusivity ``D0, Q`` (cited diffusion data); the surface/core hardness (the 2c/3a
    martensite model, anchored to Hodge–Orehoski).
  * **CALIBRATED / LOOSE:** the *absolute* case-depth value vs published tables — banded,
    not pinned, because the carbon potential and the case-depth *definition* vary widely
    across sources (so the scaling law is asserted tightly, the absolute number loosely,
    like the 1045 knee position).

Deliberate scope (named, not hidden)
------------------------------------
  * **Constant ``D`` (concentration-independent) is the default.** Real carbon diffusivity
    in austenite rises with carbon content (Tibbetts), so a real profile is a little fuller
    than erfc. Constant ``D`` is the standard textbook reduction and is *what makes erfc
    exact* — the validated analytical limit, kept as the default. The concentration-dependent
    ``D(C)`` is now **built** as the opt-in :func:`carbon_diffusivity_tibbetts` →
    :func:`solve_carburize` ``D_of_C``: it deepens the case toward the published band and is
    validated against the Boltzmann self-similar reference. It is wired to the diffusion
    engine's **native nonlinear ``D_of_u``** — the v1.1 surface for which the spine was
    unfrozen and re-sealed (CONTRACT.md / ADR 0004), not composed around the engine.
  * **Dirichlet (constant carbon potential).** A finite surface reaction rate (a Robin /
    mass-transfer boundary, and boost-diffuse cycles that ramp ``Cs``) is deferred — the
    constant-potential erfc case is the canonical one.
  * **Uniform quench across the case** (above) — the carbon gradient is the subject.
  * **High-carbon extrapolation** of Andrews ``Ms`` / KM / the martensite curve past
    their ~0.8 %C anchor — the root of the surface-RA overprediction, handled by the
    benchmark fork above.
  * The **D_I cross-check** (critical diameter from the finished model) is now **built**
    (Phase 6c — :mod:`ideal_diameter`): the critical diameter ``D_c`` read from the model's
    ``fM=0.5`` Jominy distance vs **measured** H-bands (the benchmark is measured, not
    Grossmann-computed — non-circular).

Units & conventions
-------------------
* **Carbon** wt % (as :mod:`fe_c`/:mod:`kinetics`/:mod:`properties`); **length** m;
  **time** s at the API (hours accepted at the carburize entry point — the process unit);
  **temperature** °C; **diffusivity** m²/s; **hardness** internally HV, reported HRC
  (``nan`` below ~20 HRC / above ~67 HRC, the E140 band).
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_bvp
from scipy.special import erfc, erfcinv

from engines.diffusion import Diffusion1D, uniform_grid, Dirichlet, Neumann
from . import pathint, cooling
from . import properties as prop
from .kinetics import ccurve_for_steel

# --------------------------------------------------------------------------- #
# 1. Carbon diffusivity in austenite — the one new physics constant (cited)
# --------------------------------------------------------------------------- #
# Arrhenius diffusivity of carbon in FCC γ-iron, D = D0·exp(−Q/RT). The cited
# Callister/Shewmon value (Callister, *Materials Science & Engineering*, diffusion
# appendix — the same D0 ≈ 2.3e-5 m²/s, Q ≈ 148 kJ/mol the CONTRACT names as the
# mass-mode example). Anchored to *diffusion* data, NOT fit to case-depth tables, so
# the case-depth benchmark below is a genuine cross-check. (Real D rises with carbon
# content — Tibbetts — but the constant-D form is the textbook erfc case; see the
# module docstring's scope note.)
R_GAS = 8.314462618          # universal gas constant, J/(mol·K)
ABS_ZERO = 273.15            # 0 °C in kelvin
D0_CARBON_AUSTENITE = 2.3e-5     # m²/s
Q_CARBON_AUSTENITE = 148_000.0   # J/mol

# Process defaults: a representative gas-carburizing cycle and an 8620-grade steel.
DEFAULT_T_CARBURIZE = 925.0      # °C — austenitic, brisk carbon diffusion
DEFAULT_CARBON_POTENTIAL = 0.80  # wt% — the atmosphere's carbon potential (Cs); 0.8 %
#   is the representative target: it keeps the surface at the top of the Andrews/KM
#   anchored range (mild extrapolation) and holds retained austenite modest (~22 %),
#   so both the martensite-potential surface hardness *and* the as-quenched traverse
#   stay on the HRC scale. Higher potentials (→ 1.0 %) invite heavy RA and carbides.
DEFAULT_CORE_CARBON = 0.20       # wt% — a low-carbon carburizing-grade core
CASE_DEPTH_CARBON = 0.40         # wt% — the conventional *effective case depth* level

# A representative carburizing-grade steel (≈ AISI 8620), the alloy that carries both
# the hardenability (so the core hardens under an oil quench) and the Maynier minor-alloy
# hardness delta. One dict serves both consumers: ccurve_for_steel reads Mn/Ni/Cr/Mo/Si,
# the properties model reads Si/Mn/Ni/Cr (martensite) — each picks the keys it knows.
CARBURIZING_STEEL_8620 = {"Mn": 0.80, "Ni": 0.55, "Cr": 0.50, "Mo": 0.20, "Si": 0.25}


def carbon_diffusivity(T_celsius: float) -> float:
    """Diffusivity of carbon in austenite ``D = D0·exp(−Q/RT)`` (m²/s), ``T`` in **°C**.

    The cited Callister value for C in FCC γ-iron (``D0 = 2.3e-5 m²/s``,
    ``Q = 148 kJ/mol``). Converts to kelvin internally (Arrhenius needs absolute ``T``).
    At 925 °C ≈ 8.1e-12 m²/s, giving ``√(Dt) ≈ 0.48 mm`` over an 8 h cycle — the right
    case-depth scale. Constant in ``x`` (concentration-independent — the erfc reduction).
    """
    T_K = T_celsius + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"temperature must be above absolute zero, got {T_celsius} °C")
    return D0_CARBON_AUSTENITE * math.exp(-Q_CARBON_AUSTENITE / (R_GAS * T_K))


# --------------------------------------------------------------------------- #
# 1b. Concentration-dependent carbon diffusivity — Tibbetts (1980): the opt-in D(C)
# --------------------------------------------------------------------------- #
# Real carbon diffusivity in austenite RISES with carbon content. The constant-D erfc
# (above) is the textbook reduction the *validated analytical limit* needs, but it
# UNDER-predicts the absolute case depth (the named scope edge). Tibbetts (1980,
# J. Appl. Phys. 51(9):4813, "Diffusivity of carbon in iron and steels at high
# temperatures") measured D for C in austenite by the steady-state method (975–1075 °C,
# up to 1.3 %C) and fit the empirical concentration- and temperature-dependent form
#
#     D = 0.47 · exp(−1.6·C) · exp[ −(37000 − 6600·C) / (R_cal·T) ]   cm²/s
#
# with C in wt%, energies in cal/mol (R_cal = 1.987 cal/mol·K), T in kelvin. Like the
# Callister constant-D it is anchored to *diffusion* measurements, NOT fit to case-depth
# tables — so the D(C) case-depth benchmark stays a genuine cross-check, not a tautology.
# Net effect: the activation-energy lowering (−6600·C) outweighs the prefactor decay
# (−1.6·C), so D increases with C → a fuller-than-erfc profile and a deeper case. (The
# default carburizing T = 925 °C sits ~50 °C below Tibbetts' measured floor — a mild,
# named extrapolation; the relation is the standard one used in carburizing simulation at
# 900–950 °C.) Fed to the (now unfrozen) engine's native nonlinear ``D_of_u`` — ADR 0004.
R_GAS_CAL = 1.987                # cal/(mol·K) — gas constant in Tibbetts' calorie units
TIBBETTS_D0 = 0.47               # cm²/s — prefactor
TIBBETTS_C_PREFACTOR = 1.6       # 1/wt% — concentration coefficient of the prefactor
TIBBETTS_Q0 = 37_000.0           # cal/mol — activation energy extrapolated to C → 0
TIBBETTS_Q_PER_C = 6_600.0       # cal/(mol·wt%) — activation lowering per wt% carbon


def carbon_diffusivity_tibbetts(C, T_celsius: float = DEFAULT_T_CARBURIZE):
    """Concentration-dependent diffusivity of carbon in austenite ``D(C, T)`` (m²/s).

    The cited Tibbetts (1980) form ``D = 0.47·exp(−1.6 C)·exp[−(37000−6600 C)/(R_cal T)]``
    cm²/s (``C`` in wt%, ``T`` in **°C** → kelvin internally), returned in **m²/s**.
    Vectorized over ``C`` — accepts a scalar or the per-cell carbon array the D(C) solve
    feeds it. Rises with carbon: at 925 °C, ``D ≈ 1.05e-11`` (0.2 %C) → ``1.34e-11``
    (0.4 %C) → ``2.13e-11`` m²/s (0.8 %C), all above the constant ``8.1e-12`` — the
    deeper-case effect the constant-``D`` erfc misses. Pass to :func:`solve_carburize`'s
    ``D_of_C`` (it is wired to the engine's native nonlinear ``D_of_u`` — ADR 0004).
    """
    C = np.asarray(C, dtype=float)
    T_K = T_celsius + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"temperature must be above absolute zero, got {T_celsius} °C")
    Q = TIBBETTS_Q0 - TIBBETTS_Q_PER_C * C            # cal/mol — falls with carbon
    D_cm2 = TIBBETTS_D0 * np.exp(-TIBBETTS_C_PREFACTOR * C) * np.exp(-Q / (R_GAS_CAL * T_K))
    return D_cm2 * 1.0e-4                              # cm²/s → m²/s


# --------------------------------------------------------------------------- #
# 2. The analytic erfc solution + case depth (the analytical-limit leg)
# --------------------------------------------------------------------------- #
def analytic_erfc_carbon(
    x: np.ndarray, t: float, D: float, C_surface: float, C_core: float
) -> np.ndarray:
    """The erfc carbon profile ``C(x) = C0 + (Cs − C0)·erfc(x / 2√(Dt))`` (wt%).

    The exact solution for a constant surface concentration ``Cs`` diffusing into a
    semi-infinite solid of uniform ``C0`` with constant ``D`` — the analytical limit the
    numeric :func:`solve_carburize` is validated against. ``x`` (m, from the surface),
    ``t`` (s), ``D`` (m²/s).
    """
    x = np.asarray(x, dtype=float)
    if t <= 0.0:
        raise ValueError(f"time must be > 0, got {t}")
    return C_core + (C_surface - C_core) * erfc(x / (2.0 * math.sqrt(D * t)))


def analytic_case_depth(
    t: float, D: float, C_surface: float, C_core: float,
    C_threshold: float = CASE_DEPTH_CARBON,
) -> float:
    """Case depth (m) to carbon level ``C_threshold`` — ``2·erfc⁻¹(r)·√(Dt)``, ``∝ √(Dt)``.

    With ``r = (C_threshold − C0)/(Cs − C0)`` the level set of the erfc profile, so the
    depth scales **exactly** as ``√(Dt)`` (the analytical leg of the Phase-3 triad). The
    default ``C_threshold = 0.4 %`` is the conventional *effective case depth*. ``r`` must
    lie in ``(0, 1)`` (threshold strictly between core and surface carbon), else ``nan``.
    """
    denom = C_surface - C_core
    if denom <= 0.0:
        raise ValueError("C_surface must exceed C_core (carbon flows inward)")
    r = (C_threshold - C_core) / denom
    if not (0.0 < r < 1.0):
        return float("nan")            # threshold outside (C_core, C_surface)
    return 2.0 * float(erfcinv(r)) * math.sqrt(D * t)


# --------------------------------------------------------------------------- #
# 2c. The case-depth INVERSION (Phase 7 v2) — target a case depth, get a schedule
# --------------------------------------------------------------------------- #
# The forward :func:`analytic_case_depth` gives a depth from a (time, temperature) cycle; this
# inverts it — the engineer's actual question, *"what cycle gives me 0.5 mm of effective case?"*.
# Because the constant-D erfc case depth is **exactly** ``x = 2·erfc⁻¹(r)·√(Dt)`` (the level set of
# the erfc profile), the inverse is **closed form** — no root-find, recovering the input to machine
# precision. Two natural unknowns:
#   * solve the **time** at a chosen temperature  (t = (x / k)² / D,                  k = 2·erfc⁻¹(r))
#   * solve the **temperature** at a chosen time  (D = (x / k)² / t, then invert Arrhenius for T).
#
# Scope — what is and is NOT inverted (named, mirroring the forward split):
#   * **The constant-D erfc leg only** — the *validated analytical limit*. The concentration-
#     dependent D(C) (Tibbetts / the Boltzmann self-similar profile) is **not closed-form invertible**
#     (D depends on the carbon field being solved for); inverting it would need a numeric outer loop
#     over :func:`boltzmann_case_depth`, named as a ceiling, not built here. The erfc inverse slightly
#     UNDER-predicts the depth a real D(C) cycle reaches — the same direction the forward erfc leg is
#     conservative, carried forward honestly.
#   * **The carbon-level case depth** (:data:`CASE_DEPTH_CARBON`, 0.40 wt%, the conventional
#     *effective case depth*) — a *hardness*-based effective case (e.g. depth to 50 HRC) would couple
#     back into the quench/martensite-potential model (a different regime), named as an extension.

def carburize_time_for_case_depth(
    target_case_m: float,
    T_celsius: float = DEFAULT_T_CARBURIZE,
    C_surface: float = DEFAULT_CARBON_POTENTIAL,
    C_core: float = DEFAULT_CORE_CARBON,
    C_threshold: float = CASE_DEPTH_CARBON,
) -> float:
    """Carburizing **time** (s) to reach ``target_case_m`` at ``T_celsius`` — the exact inverse of ``2·erfc⁻¹(r)·√(Dt)``.

    Closed form ``t = (x / k)² / D`` with ``k = 2·erfc⁻¹(r)``, ``r = (C_th − C0)/(Cs − C0)`` the erfc
    level set and ``D = D(T)`` the constant Callister diffusivity — so a round trip through
    :func:`analytic_case_depth` recovers ``target_case_m`` to machine precision. Returns **nan** when
    ``r ∉ (0, 1)`` (threshold outside the core/surface carbon span — no depth reaches it, the honest
    infeasible). ``target_case_m`` and the returned time are SI (m, s); higher ``T`` cuts the time
    (Arrhenius ``D``). The D(C)/hardness-based ceilings in the section note above apply.
    """
    if target_case_m <= 0.0:
        raise ValueError(f"target case depth must be > 0 m, got {target_case_m}")
    denom = C_surface - C_core
    if denom <= 0.0:
        raise ValueError("C_surface must exceed C_core (carbon flows inward)")
    r = (C_threshold - C_core) / denom
    if not (0.0 < r < 1.0):
        return float("nan")            # threshold outside (C_core, C_surface) — unreachable
    D = carbon_diffusivity(T_celsius)
    k = 2.0 * float(erfcinv(r))
    return (target_case_m / k) ** 2 / D


def carburize_temperature_for_case_depth(
    target_case_m: float,
    t_seconds: float,
    C_surface: float = DEFAULT_CARBON_POTENTIAL,
    C_core: float = DEFAULT_CORE_CARBON,
    C_threshold: float = CASE_DEPTH_CARBON,
) -> float:
    """Carburizing **temperature** (°C) reaching ``target_case_m`` in ``t_seconds`` — inverts the Arrhenius ``D``.

    From the same closed form: the depth fixes the required diffusivity ``D = (x / k)² / t``
    (``k = 2·erfc⁻¹(r)``), then the Callister Arrhenius ``D = D₀·exp(−Q/RT)`` inverts to
    ``T = −Q / (R·ln(D/D₀))`` (kelvin → °C). A round trip through :func:`carbon_diffusivity` +
    :func:`analytic_case_depth` recovers ``target_case_m`` to machine precision. Returns **nan** when
    ``r ∉ (0, 1)`` (threshold unreachable). The **practical carburizing window is ~815–1050 °C**
    (austenitic, below grain-coarsening); a returned temperature outside it means the target is not
    achievable in that time by a sane cycle — surfaced to the caller (this function returns the exact
    analytic value rather than masking it), not silently clamped. The D(C)/hardness ceilings apply.
    """
    if t_seconds <= 0.0:
        raise ValueError(f"time must be > 0 s, got {t_seconds}")
    if target_case_m <= 0.0:
        raise ValueError(f"target case depth must be > 0 m, got {target_case_m}")
    denom = C_surface - C_core
    if denom <= 0.0:
        raise ValueError("C_surface must exceed C_core (carbon flows inward)")
    r = (C_threshold - C_core) / denom
    if not (0.0 < r < 1.0):
        return float("nan")            # threshold outside (C_core, C_surface) — unreachable
    k = 2.0 * float(erfcinv(r))
    D_required = (target_case_m / k) ** 2 / t_seconds
    if D_required <= 0.0:
        return float("nan")
    T_K = -Q_CARBON_AUSTENITE / (R_GAS * math.log(D_required / D0_CARBON_AUSTENITE))
    return T_K - ABS_ZERO


# --------------------------------------------------------------------------- #
# 2b. The Boltzmann self-similar reference for D(C) — the D(C) analytical leg
# --------------------------------------------------------------------------- #
def boltzmann_carbon_profile(
    x: np.ndarray,
    t: float,
    T_carburize: float = DEFAULT_T_CARBURIZE,
    C_surface: float = DEFAULT_CARBON_POTENTIAL,
    C_core: float = DEFAULT_CORE_CARBON,
    D_of_C: Callable = carbon_diffusivity_tibbetts,
) -> np.ndarray:
    """The self-similar carbon profile for concentration-dependent ``D`` (wt%).

    With ``D = D(C)`` the profile is no longer erfc — but the constant-surface
    semi-infinite problem is still **Boltzmann self-similar**: the variable ``η = x/√t``
    collapses Fick's second law to the ODE

        d/dη( D(C) dC/dη ) + (η/2) dC/dη = 0,    C(0) = Cs,  C(∞) = C0

    solved here as a boundary-value problem (:func:`scipy.integrate.solve_bvp`). This is
    the reference the numeric D(C) :func:`solve_carburize` is validated against (the D(C)
    analogue of :func:`analytic_erfc_carbon`), and an *independent* numeric from the
    engine's own re-seal (``engines/diffusion/tests/test_nonlinear_d.py``) — a cross-check
    at two layers. Because the solution depends on ``x`` and ``t`` only through ``η``, the
    case depth still scales **exactly** as ``√t`` — the tight scaling leg of the Phase-3
    triad survives the loss of erfc. ``x`` (m, from the surface), ``t`` (s); ``D_of_C(C, T)``
    returns m²/s (defaults to the cited Tibbetts D(C)).
    """
    x = np.asarray(x, dtype=float)
    if t <= 0.0:
        raise ValueError(f"time must be > 0, got {t}")
    # η reaches the core near ~6·√D (erfc argument ≈ 3); integrate out to a generous
    # multiple so C(η_max) ≈ C0. Use the surface (largest) D — the deepest penetration.
    D_hi = float(np.asarray(D_of_C(C_surface, T_carburize)))
    eta_max = 12.0 * math.sqrt(D_hi)
    eta = np.linspace(0.0, eta_max, 400)

    def odes(e, y):
        C = y[0]
        w = y[1]                                       # w = D(C)·dC/dη (the flux variable)
        dC = w / D_of_C(C, T_carburize)
        return np.vstack((dC, -0.5 * e * dC))

    def bc(ya, yb):
        return np.array([ya[0] - C_surface, yb[0] - C_core])

    # Initial guess: a linear ramp Cs→C0, with w from its finite-difference slope.
    C_guess = C_core + (C_surface - C_core) * (1.0 - eta / eta_max)
    w_guess = D_of_C(C_guess, T_carburize) * np.gradient(C_guess, eta)
    sol = solve_bvp(odes, bc, eta, np.vstack((C_guess, w_guess)), tol=1e-8, max_nodes=20000)
    if not sol.success:
        raise RuntimeError(f"Boltzmann similarity BVP did not converge: {sol.message}")
    return sol.sol(np.clip(x / math.sqrt(t), 0.0, eta_max))[0]


def boltzmann_case_depth(
    t: float,
    T_carburize: float = DEFAULT_T_CARBURIZE,
    C_surface: float = DEFAULT_CARBON_POTENTIAL,
    C_core: float = DEFAULT_CORE_CARBON,
    C_threshold: float = CASE_DEPTH_CARBON,
    D_of_C: Callable = carbon_diffusivity_tibbetts,
) -> float:
    """Case depth (m) to ``C_threshold`` for the concentration-dependent D(C) profile.

    The D(C) analogue of :func:`analytic_case_depth`. Evaluates the self-similar
    :func:`boltzmann_carbon_profile` on a dense grid and interpolates the threshold
    crossing; ``∝ √t`` by self-similarity. ``nan`` if the threshold lies outside
    ``(C_core, C_surface)`` or beyond the resolved profile.
    """
    denom = C_surface - C_core
    if denom <= 0.0:
        raise ValueError("C_surface must exceed C_core (carbon flows inward)")
    r = (C_threshold - C_core) / denom
    if not (0.0 < r < 1.0):
        return float("nan")
    D_hi = float(np.asarray(D_of_C(C_surface, T_carburize)))
    x_grid = np.linspace(0.0, 12.0 * math.sqrt(D_hi * t), 800)
    C = boltzmann_carbon_profile(x_grid, t, T_carburize, C_surface, C_core, D_of_C)
    if C_threshold >= C[0] or C_threshold <= C[-1]:
        return float("nan")
    return float(np.interp(C_threshold, C[::-1], x_grid[::-1]))


# --------------------------------------------------------------------------- #
# 3. The numeric carburizing solve (diffusion engine, mass mode) → CarburizedProfile
#    Constant ``D`` (erfc) by default, or the opt-in nonlinear ``D(C)`` (Tibbetts) wired
#    to the unfrozen engine's native ``D_of_u`` (ADR 0004).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CarburizedProfile:
    """A carburized carbon profile ``C(x)`` plus its mass-conservation accounting.

    ``x`` are cell-centre depths from the surface (m); ``C`` the carbon profile (wt%);
    ``t``/``T_carburize``/``D`` the cycle (s, °C, m²/s); ``C_surface``/``C_core`` the
    boundary and initial carbon. ``mass_uptake`` is the numeric rise in ``∫C dx`` (the
    carbon absorbed, in wt%·m); ``surface_flux_uptake`` is the independent integral
    ``Σ dt·flux(left)`` of the surface flux — the two are equal to machine precision for
    the backward-Euler default (the engine's frozen identity; the core end is no-flux),
    which is the conservation leg. The ``(x, C)`` array is the seam :func:`carburized_traverse`
    consumes — the same plain-array currency every module here exchanges.
    """

    x: np.ndarray
    C: np.ndarray
    t: float
    T_carburize: float
    D: float
    C_surface: float
    C_core: float
    length: float
    mass_uptake: float
    surface_flux_uptake: float
    method: str
    concentration_dependent: bool = False    # True when solved with the opt-in D(C) (Tibbetts)
    D_array: np.ndarray | None = None         # the final per-cell D(x) of a D(C) solve (else None)

    def erfc_profile(self) -> np.ndarray:
        """The analytic erfc carbon profile at this solve's ``x``, ``t``, ``D`` (wt%).

        Uses the constant reference ``D``; on a D(C) solve
        (:attr:`concentration_dependent`) this is the *under-predicting* constant-``D``
        baseline to overlay against — the exact reference there is
        :meth:`boltzmann_profile`, not erfc.
        """
        return analytic_erfc_carbon(self.x, self.t, self.D, self.C_surface, self.C_core)

    def boltzmann_profile(self, D_of_C: Callable = carbon_diffusivity_tibbetts) -> np.ndarray:
        """The Boltzmann self-similar reference profile (wt%) — the D(C) analogue of erfc.

        Defaults to the cited Tibbetts D(C); pass a matching ``D_of_C`` if the solve used a
        custom diffusivity. See :func:`boltzmann_carbon_profile`.
        """
        return boltzmann_carbon_profile(
            self.x, self.t, self.T_carburize, self.C_surface, self.C_core, D_of_C
        )

    def case_depth(self, C_threshold: float = CASE_DEPTH_CARBON) -> float:
        """Numeric case depth (m): the depth where ``C(x)`` falls through ``C_threshold``.

        Interpolated from the (monotone-decreasing) profile. ``nan`` if the threshold is
        outside the profile's range (above the surface carbon, or deeper than the domain
        reaches — i.e. the case is not resolved). Compare with :meth:`analytic_case_depth`.
        """
        C, x = self.C, self.x
        if C_threshold >= C[0] or C_threshold <= C[-1]:
            return float("nan")
        # C decreases in x → reverse to an ascending xp for np.interp.
        return float(np.interp(C_threshold, C[::-1], x[::-1]))

    def analytic_case_depth(self, C_threshold: float = CASE_DEPTH_CARBON) -> float:
        """The closed-form case depth ``2·erfc⁻¹(r)·√(Dt)`` for this cycle (m)."""
        return analytic_case_depth(self.t, self.D, self.C_surface, self.C_core, C_threshold)


def solve_carburize(
    C_surface: float = DEFAULT_CARBON_POTENTIAL,
    C_core: float = DEFAULT_CORE_CARBON,
    T_carburize: float = DEFAULT_T_CARBURIZE,
    t_hours: float = 8.0,
    length: float = 6.0e-3,
    n_cells: int = 300,
    n_steps: int = 600,
    method: str = "backward_euler",
    D_of_C: Callable | None = None,
) -> CarburizedProfile:
    """Diffuse carbon into the surface — the diffusion engine in **mass mode** → ``C(x)``.

    Solves ``∂C/∂t = ∂ₓ(D ∂ₓC)`` with a Dirichlet surface at the carbon potential
    ``C_surface`` and a no-flux core/centreline, from a uniform core ``C_core``. Marches a
    uniform time grid (``n_steps`` of ``t_hours·3600/n_steps``), accumulating the
    surface-flux integral so the conservation leg can compare it to the change in ``∫C dx``.

    By default ``D`` is the **constant** Callister value at ``T_carburize`` (the textbook
    erfc case — the validated analytical limit). Pass ``D_of_C`` (e.g.
    :func:`carbon_diffusivity_tibbetts`) for the **concentration-dependent** diffusivity:
    it is wired straight into the engine's native nonlinear ``D_of_u`` (the unfrozen v1.1
    path — CONTRACT.md / ADR 0004), which Picard-solves the nonlinear step and caches the
    accepted D-field so the conservation identity stays machine-exact.

    Parameters
    ----------
    C_surface, C_core : float
        Carbon potential (Dirichlet surface, wt%) and uniform initial core carbon (wt%).
    T_carburize : float
        Carburizing temperature (°C) → the constant diffusivity :func:`carbon_diffusivity`.
    t_hours : float
        Cycle time (hours — the process unit).
    length : float
        Domain depth (m). Keep ``length ≳ 3·√(Dt)`` so the far end stays semi-infinite
        (the erfc holds); the no-flux core conserves mass regardless.
    n_cells, n_steps : int
        Spatial / temporal resolution. ``backward_euler`` is unconditionally stable, so
        these set accuracy, not stability.
    method : {"backward_euler", "crank_nicolson"}
        Time scheme. **Backward Euler (default)** is the one whose flux identity is
        *exact*, so the conservation bookkeeping is machine-precise; Crank–Nicolson is
        more accurate in the interior profile but only approximately closes the flux
        identity (so ``surface_flux_uptake`` carries a small splitting residual there).
        The ``D_of_C`` (nonlinear) path requires backward Euler (the engine enforces it).
    D_of_C : callable, optional
        Opt-in **concentration-dependent** diffusivity ``D_of_C(C, T_celsius) → m²/s``
        (e.g. :func:`carbon_diffusivity_tibbetts`). ``None`` (default) keeps the
        **constant-``D`` erfc** solve byte-identical. When supplied it is passed to the
        engine's native nonlinear ``D_of_u``; the result carries
        :attr:`CarburizedProfile.concentration_dependent` and the final ``D_array``, and is
        validated against :func:`boltzmann_carbon_profile`, not erfc.
    """
    if C_surface <= C_core:
        raise ValueError("C_surface must exceed C_core for carbon to diffuse inward")
    D = carbon_diffusivity(T_carburize)        # the constant reference (the erfc baseline's D)
    t_end = t_hours * 3600.0
    dt = t_end / n_steps
    grid = uniform_grid(length, n_cells)

    if D_of_C is None:
        solver = Diffusion1D(grid, D, Dirichlet(C_surface), Neumann(0.0), method=method)
    else:
        # The unfrozen engine handles the nonlinear D(C) natively (Picard inside step,
        # caching the accepted D-field — CONTRACT.md / ADR 0004): hand it the diffusivity
        # as a function of the live carbon. No per-step reassembly or operator splitting.
        solver = Diffusion1D(
            grid, None, Dirichlet(C_surface), Neumann(0.0), method=method,
            D_of_u=lambda u: np.asarray(D_of_C(u, T_carburize), dtype=float),
        )

    C = np.full(n_cells, float(C_core))
    total0 = solver.total(C)
    surface_flux_uptake = 0.0       # Σ dt·flux(left): carbon entering the surface
    t = 0.0
    for _ in range(n_steps):
        C = solver.step(C, dt, t0=t)
        t += dt
        # Discrete identity (backward Euler): Δtotal = dt·(flux_left − flux_right). The core
        # (right) is no-flux, so the surface (left) flux integral is the carbon uptake. On the
        # D(C) path the engine caches the accepted-assembly D-field, so this stays exact.
        surface_flux_uptake += dt * solver.flux(C, "left", t=t)

    total1 = solver.total(C)
    D_array = None if D_of_C is None else np.asarray(D_of_C(C, T_carburize), dtype=float)
    return CarburizedProfile(
        x=grid.centers,
        C=C,
        t=t_end,
        T_carburize=T_carburize,
        D=D,
        C_surface=C_surface,
        C_core=C_core,
        length=length,
        mass_uptake=total1 - total0,
        surface_flux_uptake=surface_flux_uptake,
        method=method,
        concentration_dependent=D_of_C is not None,
        D_array=D_array,
    )


# --------------------------------------------------------------------------- #
# 4. The case-hardened gradient: C(x) → microstructure + hardness (the artifact)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CarburizedTraverse:
    """The case-hardened gradient: depth → microstructure → hardness (the gear-tooth data).

    ``depth`` (m from the surface) and ``C`` (wt% at each depth, from the profile). The
    per-depth phase fractions ``pearlite``/``bainite``/``martensite``/``retained_austenite``
    are the full transformation model's output (a single quench, only ``C(x)`` varying) —
    the **microstructure gradient**, in which retained austenite rises toward the
    high-carbon surface (real heavy-case physics; see the module docstring's fork).

    Two hardness curves, deliberately:

      * ``HV`` / ``HRC`` — the martensite **potential** (the case as designed: full
        martensite at the local carbon). This is the **benchmark-bearing** case-hardness
        traverse, cross-checked against published surface/case hardness.
      * ``HV_as_quenched`` — the full rule-of-mixtures hardness *including* the predicted
        retained austenite. It coincides with ``HV`` through the core and dips below it
        near the surface (the RA drag) — reported as the honest as-quenched value, **not**
        asserted against the published surface band.
    """

    depth: np.ndarray
    C: np.ndarray
    pearlite: np.ndarray
    bainite: np.ndarray
    martensite: np.ndarray
    retained_austenite: np.ndarray
    HV: np.ndarray
    HRC: np.ndarray
    HV_as_quenched: np.ndarray
    medium: str
    ferrite: np.ndarray = None      # proeutectoid ferrite per depth (Phase 6a; ~0 in the high-C case, rises in the low-C core)

    def case_depth_50HRC(self) -> float:
        """Case depth (m) to **50 HRC** on the potential traverse — the hardness-based ECD.

        The other conventional effective-case-depth definition (depth to 50 HRC), read off
        the martensite-potential ``HRC`` curve by interpolation. ``nan`` if the surface is
        already below 50 HRC or the whole resolved case stays above it. Complements the
        carbon-based :meth:`CarburizedProfile.case_depth` (depth to 0.4 %C).
        """
        hrc, x = self.HRC, self.depth
        finite = np.isfinite(hrc)
        if finite.sum() < 2 or hrc[0] < 50.0 or np.nanmin(hrc[finite]) > 50.0:
            return float("nan")
        # HRC decreases with depth; reverse to ascending for np.interp.
        h = hrc[finite][::-1]
        xx = x[finite][::-1]
        return float(np.interp(50.0, h, xx))


def carburized_traverse(
    profile: CarburizedProfile,
    comp: dict | None = None,
    medium: str | float = "oil",
    T0: float = 850.0,
) -> CarburizedTraverse:
    """Map a carbon profile to a hardness traverse — the case-hardened gear-tooth gradient.

    For each depth's carbon ``C(x)``, build the steel's TTT curve (``ccurve_for_steel`` —
    so the local ``Ms``, hardenability shift, and ceiling all follow the carbon), integrate
    the **same** cooling path through it (:func:`pathint.transform_along_path`) to a
    microstructure, and read two hardnesses: the martensite *potential* (``HV``/``HRC`` —
    the benchmark-bearing case hardness) and the full as-quenched rule of mixtures
    (``HV_as_quenched``, RA included). One quench is applied at every depth on purpose: the
    case's gradient is carbon-driven, not cooling-rate-driven (module docstring).

    Parameters
    ----------
    profile : CarburizedProfile
        The carbon profile from :func:`solve_carburize`.
    comp : dict, optional
        Minor-alloy composition (wt%: Mn/Ni/Cr/Mo/Si). Defaults to an 8620-grade steel
        (:data:`CARBURIZING_STEEL_8620`) — alloyed for core hardenability + the Maynier delta.
    medium : str | float
        Quench medium (:data:`cooling.MEDIA` key, or a raw ``h``). Default ``"oil"`` — the
        standard case-hardening quench (water risks distortion/cracking of a carburized part).
    T0 : float
        The austenitize/quench start temperature (°C).

    Note
    ----
    The **surface / case** hardness is the benchmark-bearing cross-check (carbon-set martensite
    potential). The **core** hardness *number*, by contrast, is **model/quench-dependent, not an
    anchored benchmark**: it is fixed by the held-constant cooling-rate axis (one 0-D quench on
    :mod:`cooling`'s default 10 mm cylinder → ~97 % martensite at 0.2 %C → ~48 HRC). A real gear
    section cools more slowly and forms more bainite/ferrite in the core (published 8620 cores run
    ~30–40 HRC), so the core hardness is a *sanity* value, not a validated one — 3c's subject is
    the **carbon** gradient, and the cooling-rate gradient that sets the absolute core hardness is
    the prior phases' (1c/2). Pass a milder ``medium`` / larger section to soften the core.
    """
    comp = dict(CARBURIZING_STEEL_8620 if comp is None else comp)
    path = cooling.cooling_path(medium, T0=T0, warn_biot=False)

    Cx = np.asarray(profile.C, dtype=float)
    n = Cx.size
    fer = np.empty(n); pear = np.empty(n); bain = np.empty(n); mart = np.empty(n); ra = np.empty(n)
    HV = np.empty(n); HV_aq = np.empty(n)

    for k, C in enumerate(Cx):
        cc = ccurve_for_steel(
            C, Mn=comp.get("Mn", 0.0), Ni=comp.get("Ni", 0.0),
            Cr=comp.get("Cr", 0.0), Mo=comp.get("Mo", 0.0), Si=comp.get("Si", 0.0),
        )
        r = pathint.transform_along_path(path.t, path.T, cc)
        f = r.fractions()
        # Phase 6a: proeutectoid ferrite is ~0 in the high-carbon case but rises in the low-carbon
        # core (KV's large carbon coefficient → low-C austenite forms ferrite readily) — track it
        # so the microstructure gradient sums to 1 and the soft core is shown honestly.
        fer[k] = f["ferrite"]
        pear[k], bain[k] = f["pearlite"], f["bainite"]
        mart[k], ra[k] = f["martensite"], f["retained_austenite"]
        # The full as-quenched rule of mixtures (RA + proeutectoid ferrite dragging the curve down)…
        HV_aq[k] = prop.hardness_HV(f, float(C), comp=comp)
        # …vs the martensite *potential*: the case as designed (the benchmark anchor).
        HV[k] = prop.vickers_martensite(float(C), comp=comp)

    return CarburizedTraverse(
        depth=profile.x,
        C=Cx,
        ferrite=fer,
        pearlite=pear,
        bainite=bain,
        martensite=mart,
        retained_austenite=ra,
        HV=HV,
        HRC=prop.vickers_to_rockwell_c(HV),
        HV_as_quenched=HV_aq,
        medium=path.name,
    )
