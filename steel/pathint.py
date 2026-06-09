"""Path integration: cooling curve → microstructure (Steel Phase 1c).

This is the steel-local **minimal path-integrator** (Steel plan §2 — kept here, not
promoted to ``engines/``, until a stabilized interface earns the rule-of-three).
It strings the isothermal laws of :mod:`kinetics` along a *continuous* cooling
curve ``T(t)`` and reports what the austenite becomes. Three pieces:

1. A **0-D lumped-capacitance cooler** — Newton cooling ``T(t)``, the analytic
   limit. (Phase 2 swaps in ``engines/diffusion`` heat mode for a *spatial*
   thermal field; this module's array-in/array-out boundary is where that slots.)
2. **Scheil additivity** ``∫dt/τ(T(t)) = 1`` — the rule that bridges the
   *isothermal* TTT curve to a *continuous-cooling* (CCT) transformation start.
3. The **fictitious-time additive integration** of the Avrami fraction along the
   path, then **Koistinen–Marburger** on whatever austenite survives to ``Mₛ``.

Why additivity works (and when it doesn't)
------------------------------------------
A continuously-cooled reaction is treated as a sum of infinitesimal isothermal
bites (Scheil 1935). Two equivalent uses appear here:

* **Start (incubation):** transformation begins when the *fractions of the local
  isothermal start-time consumed* add to one: ``∫₀ᵗ dt'/τ_X(T(t')) = 1`` with
  ``τ_X(T)`` the isothermal time to fraction ``X`` (:func:`additivity_start_time`).
  Held isothermally at ``T*`` the integral is just ``t/τ_X(T*)`` → it reaches 1 at
  ``t = τ_X(T*)``, recovering the isothermal curve. That reduction is the
  validation triad's consistency leg.
* **Amount:** the fraction itself is advanced by the **fictitious-time** method —
  at each step find the time ``t*`` that *would* have produced the current ``X`` at
  the current ``T`` (invert Avrami), advance ``t* + dt``, read the new ``X``
  (:func:`transform_along_path`).

Both are exact **only for an isokinetic reaction** (``Ẋ`` separable as
``f(X)·g(T)``), which is why :mod:`kinetics` holds the Avrami exponent ``n``
constant. A ``T``-dependent ``n`` would break additivity silently.

The martensite bookkeeping (why fractions sum to 1)
---------------------------------------------------
The diffusional path consumes a fraction ``X_diff`` of the austenite (split into
*pearlite* above ``Bs`` and *bainite* below it, by the temperature at which each
increment formed). Only the **retained** austenite ``(1 − X_diff)`` is then
available to shear to martensite, governed athermally by Koistinen–Marburger at
the **lowest temperature reached**. So

    pearlite + bainite + martensite + retained_austenite
      = X_diff + (1 − X_diff)·[f_KM + (1 − f_KM)]
      = X_diff + (1 − X_diff) = 1                       (exactly, by construction)

Applying KM to the *total* austenite instead would double-count and break this.

Units & I/O
-----------
Temperatures are **°C**, times **seconds**, fractions dimensionless ``[0,1]`` —
matching :mod:`kinetics`/:mod:`fe_c`. Cooling paths cross module boundaries as
**plain ``(t, T)`` arrays** (the array currency of ADR 0001 / Steel plan §5), not
live objects — the same seam a future spatial thermal history plugs into.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .kinetics import CCurve, koistinen_marburger


# --------------------------------------------------------------------------- #
# 1. The 0-D lumped-capacitance cooler (Newton cooling — the analytic limit)
# --------------------------------------------------------------------------- #
def newton_cooling(t: np.ndarray, T0: float, T_env: float, tau_thermal: float) -> np.ndarray:
    """Lumped-capacitance cooling history ``T(t) = T_env + (T0−T_env)·exp(−t/τ_th)``.

    Valid when the body is thermally "small" (Biot ``Bi = hL/k < 0.1``) so its
    interior is isothermal and a single time constant ``τ_th = ρc_pV/(hA)``
    governs — the regime :mod:`cooling` builds its presets in, and the exact limit
    Phase-2's spatial heat solver must reproduce. ``t`` (s) is an array; returns
    ``T`` (°C). ``T(0) = T0``, ``T(τ_th) = T_env + (T0−T_env)/e``, ``T(∞) = T_env``.
    """
    if tau_thermal <= 0.0:
        raise ValueError(f"thermal time constant τ_th must be > 0, got {tau_thermal}")
    t = np.asarray(t, dtype=float)
    return T_env + (T0 - T_env) * np.exp(-t / tau_thermal)


def log_time_grid(t_end: float, t_start: float = 1e-3, per_decade: int = 240) -> np.ndarray:
    """A logarithmic time grid ``[t_start, t_end]`` (s), dense across every decade.

    Cooling histories span decades — water quench in well under a second, furnace
    anneal over hours — so a fixed linear step is either ruinously fine or far too
    coarse. A geometric grid spends steps proportionally, keeping the additivity
    and fictitious-time integrals accurate at all timescales without millions of
    points. The grid is prepended with ``t = 0`` so paths start exactly at ``T0``.
    """
    if t_end <= t_start:
        raise ValueError(f"t_end ({t_end}) must exceed t_start ({t_start})")
    decades = math.log10(t_end / t_start)
    n = max(2, int(round(decades * per_decade)) + 1)
    grid = np.geomspace(t_start, t_end, n)
    return np.concatenate(([0.0], grid))


# --------------------------------------------------------------------------- #
# 2. Scheil additivity — the CCT transformation-start time
# --------------------------------------------------------------------------- #
def additivity_sum(t: np.ndarray, T: np.ndarray, ccurve: CCurve, X: float = 0.01) -> np.ndarray:
    """Cumulative Scheil sum ``S(t) = ∫₀ᵗ dt'/τ_X(T(t'))`` along a path (°C, s).

    ``τ_X(T)`` is the isothermal time to fraction ``X`` (:meth:`CCurve.time_to_fraction`);
    where it is infinite (``T ≥ T_eq``: no driving force) the integrand is zero.
    Trapezoidal cumulative integral — exact for an isothermal hold (constant
    integrand), so :func:`additivity_start_time` recovers ``τ_X(T*)`` there.
    Transformation has started wherever ``S ≥ 1``.
    """
    t = np.asarray(t, dtype=float)
    T = np.asarray(T, dtype=float)
    rate = np.empty_like(T)
    for i, Ti in enumerate(T):
        tau_X = ccurve.time_to_fraction(float(Ti), X)  # inf above T_eq
        rate[i] = 0.0 if math.isinf(tau_X) else 1.0 / tau_X
    dt = np.diff(t)
    increments = 0.5 * (rate[:-1] + rate[1:]) * dt      # trapezoid per interval
    return np.concatenate(([0.0], np.cumsum(increments)))


def additivity_start_time(
    t: np.ndarray, T: np.ndarray, ccurve: CCurve, X: float = 0.01
) -> float:
    """Time (s) at which the Scheil sum first reaches 1 — the CCT start, else ``inf``.

    Linear interpolation in the crossing interval. ``inf`` means the path outran
    the diffusional reaction entirely (a quench that misses the nose) — the
    austenite reaches ``Mₛ`` still untransformed.
    """
    S = additivity_sum(t, T, ccurve, X)
    idx = np.flatnonzero(S >= 1.0)
    if idx.size == 0:
        return math.inf
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    s0, s1 = S[i - 1], S[i]
    frac = (1.0 - s0) / (s1 - s0)               # s1 > s0 ≥ ... here
    return float(t[i - 1] + frac * (t[i] - t[i - 1]))


# --------------------------------------------------------------------------- #
# 3. Transform along a cooling path: diffusional (Avrami) + athermal (KM)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TransformResult:
    """The microstructure a cooling path produces — mass fractions summing to 1.

    ``ferrite`` is the **proeutectoid ferrite** (Phase 6a — the Li/KV reaction below A₃, ``0`` for
    a eutectoid/hypereutectoid steel or a bare :class:`~projects.steel.kinetics.CCurve` with no
    ferrite reaction); ``pearlite``/``bainite`` are the rest of the diffusional product (split by
    formation temperature at ``Bs``); ``martensite``/``retained_austenite`` are the athermal fate
    of the austenite that survived to ``Mₛ``. ``X_diffusional`` is the diffusional total
    (= ferrite + pearlite + bainite), ``T_min`` the lowest temperature reached (°C), and
    ``formation_T`` the fraction-weighted mean temperature at which the *pearlite/bainite* product
    formed (°C, ``nan`` if none; proeutectoid ferrite forms higher, near A₃, and is reported
    separately) — *where on the C-curve* the transformation happened, the kinetic quantity that
    distinguishes an otherwise-identical pearlite (high formation T = coarser lamellae) from a
    lower-temperature one. The ``t``/``T``/``X`` arrays are the path and its cumulative
    *pearlite/bainite* fraction — for the mechanism view (the cooling curve drawn across the
    C-curve) and the demo, not the validation scalars.
    """

    pearlite: float
    bainite: float
    martensite: float
    retained_austenite: float
    X_diffusional: float
    T_min: float
    formation_T: float
    t: np.ndarray
    T: np.ndarray
    X: np.ndarray
    ferrite: float = 0.0          # proeutectoid ferrite (Phase 6a); 0.0 = no ferrite reaction (byte-identical)

    def fractions(self) -> dict:
        """The product fractions as a dict (the inter-module currency, plan §5).

        Always carries the ``ferrite`` key (``0.0`` when there is no proeutectoid-ferrite
        reaction — the stable key set the ``fe_c`` idiom keeps), so consumers index without a
        ``KeyError`` and the rule of mixtures iterates it in lockstep with
        :data:`~projects.steel.properties.CONSTITUENT_HV`.
        """
        return {
            "ferrite": self.ferrite,
            "pearlite": self.pearlite,
            "bainite": self.bainite,
            "martensite": self.martensite,
            "retained_austenite": self.retained_austenite,
        }

    def dominant(self) -> str:
        """Name of the largest-fraction product — the headline microstructure."""
        return max(self.fractions().items(), key=lambda kv: kv[1])[0]


def transform_along_path(t: np.ndarray, T: np.ndarray, ccurve: CCurve) -> TransformResult:
    """Integrate a cooling path ``(t, T)`` to its microstructure (the Phase-1c core).

    Two diffusional reactions run, then the athermal one. **Proeutectoid ferrite** (Phase 6a,
    only if ``ccurve.ferrite`` is an active reaction) advances by the Li/KV site-saturation law
    over every interval where ``Mₛ < T < Ae3``, capped at the equilibrium proeutectoid-ferrite
    fraction. **Pearlite/bainite** advance by the **additive fictitious-time** method over every
    interval where ``Mₛ < T < T_eq`` (the existing curve, computed on the *full* austenite and
    labelled pearlite at ``T ≥ Bs`` else bainite). Proeutectoid ferrite forms first and at higher
    temperature, enriching the remaining austenite toward the eutectoid the pearlite curve is
    calibrated for, so it is treated **sequentially**: the pearlite/bainite/martensite products are
    scaled onto the ``(1 − f_ferrite)`` austenite the ferrite reaction left. The austenite still
    untransformed when the path bottoms out shears to **martensite** per Koistinen–Marburger at the
    lowest temperature reached, the remainder staying **retained austenite**. With no ferrite
    reaction (``ferrite=None``) or an inert one (``f_pro=0``: eutectoid/hypereutectoid, e.g. the
    four-curves 1080), ``f_ferrite = 0`` and the result is **byte-identical** to the pre-6a model.

    Parameters
    ----------
    t, T : np.ndarray
        The cooling path: times (s, increasing) and temperatures (°C). Build one
        with :func:`newton_cooling` on a :func:`log_time_grid`, or from
        :mod:`cooling`'s presets.
    ccurve : CCurve
        The steel's TTT C-curve (carries ``T_eq``, ``Mₛ``, ``Bs``, ``n``, and the optional
        Phase-6a ``ferrite`` reaction).
    """
    t = np.asarray(t, dtype=float)
    T = np.asarray(T, dtype=float)
    if t.shape != T.shape or t.ndim != 1:
        raise ValueError("t and T must be 1-D arrays of equal length")

    n = ccurve.n
    Ms, Bs, T_eq = ccurve.Ms, ccurve.Bs, ccurve.T_eq
    fr = ccurve.ferrite             # Phase-6a proeutectoid-ferrite reaction (may be None / inert)

    X = 0.0
    pearlite = 0.0
    bainite = 0.0
    U_ferrite = 0.0                 # KV proeutectoid-ferrite completion ∈ [0, 1]
    formation_T_weighted = 0.0      # Σ dX·T over the pearlite/bainite product (for the mean)
    X_hist = np.zeros_like(t)

    for i in range(1, t.size):
        dt = t[i] - t[i - 1]
        Ti = T[i]
        # Proeutectoid ferrite (Phase 6a): advances wherever Mₛ < T < Ae3 (rate is 0 above Ae3,
        # and the step is a no-op for an inert/None reaction).
        if fr is not None and Ti > Ms:
            U_ferrite = fr.completion_step(U_ferrite, float(Ti), dt)
        # Pearlite / bainite — the existing curve on the full austenite (unchanged).
        if Ms < Ti < T_eq and X < 1.0:
            tau_T = ccurve.tau(float(Ti))
            if not math.isinf(tau_T):
                # Fictitious time that reproduces the current X at this T, advanced dt.
                t_star = tau_T * (-math.log(1.0 - X)) ** (1.0 / n) if X > 0.0 else 0.0
                X_new = 1.0 - math.exp(-(((t_star + dt) / tau_T) ** n))
                dX = max(0.0, min(X_new, 1.0) - X)
                if Ti >= Bs:
                    pearlite += dX
                else:
                    bainite += dX
                formation_T_weighted += dX * Ti
                X += dX
        X_hist[i] = X

    X_diff = pearlite + bainite     # raw pearlite/bainite on the full austenite
    formation_T = formation_T_weighted / X_diff if X_diff > 0.0 else float("nan")
    T_min = float(np.min(T))
    f_km = koistinen_marburger(T_min, Ms)        # 0 if the path never reaches Mₛ

    # Sequential coupling: proeutectoid ferrite consumes f_ferrite of the austenite first; the
    # existing pearlite/martensite products take the (1 − f_ferrite) remainder. This is exact
    # (Σ = 1) and reduces to the pre-6a model when f_ferrite = 0.
    f_ferrite = U_ferrite * fr.f_pro if fr is not None else 0.0
    remainder = 1.0 - f_ferrite
    pearlite *= remainder
    bainite *= remainder
    retained = remainder * (1.0 - X_diff)
    martensite = retained * f_km
    retained_austenite = retained * (1.0 - f_km)

    return TransformResult(
        ferrite=f_ferrite,
        pearlite=pearlite,
        bainite=bainite,
        martensite=martensite,
        retained_austenite=retained_austenite,
        X_diffusional=f_ferrite + pearlite + bainite,
        T_min=T_min,
        formation_T=formation_T,
        t=t,
        T=T,
        X=X_hist,
    )
