"""Transformation kinetics: Avrami/TTT, Koistinen–Marburger, Andrews Mₛ (Steel Phase 1c).

Where :mod:`fe_c` says *what equilibrium a steel is heading toward*, this module
says *how fast it gets there, and what it becomes if it never arrives*. It is the
kinetic counterpart to the thermodynamic endpoint: the undercooling below
``fe_c``'s ``A1``/``A3`` is the **driving force** this module consumes.

Three laws live here; the path integration that strings them along a cooling
curve is :mod:`pathint`, and the cooling-medium presets are :mod:`cooling`.

1. Isothermal JMAK/Avrami kinetics
----------------------------------
At a fixed temperature a diffusional transformation (austenite → pearlite /
bainite) follows the Johnson–Mehl–Avrami–Kolmogorov sigmoid

    X(t) = 1 − exp(−(t/τ)ⁿ)            (equivalently 1 − exp(−k·tⁿ), k = τ⁻ⁿ)

``X`` is the fraction transformed, ``n`` the **Avrami exponent** (nucleation +
growth geometry, ~1–4), and ``τ`` the **characteristic time** — the time to
``X = 1 − e⁻¹ ≈ 0.632``. The ``τ`` form is used throughout because ``τ`` carries
units of time and is the natural quantity the TTT diagram plots. Crucially ``n``
is held **constant** in ``T``: that is what makes the reaction *isokinetic*
(``Ẋ`` separable as ``f(X)·g(T)``) and therefore *additive* — the property
:mod:`pathint`'s fictitious-time CCT integration relies on. A ``T``-dependent
``n`` would silently break additivity.

2. The TTT C-curve — the nose from driving force × mobility
-----------------------------------------------------------
The characteristic time ``τ(T)`` is **not** monotone: it has a minimum (the
**nose**) at an intermediate temperature, which is the whole reason a fast quench
can dodge the diffusional reaction entirely. The nose is the product of two
competing temperature dependences (Christian; Porter & Easterling):

  * **Nucleation driving force.** Classical nucleation makes the barrier
    ``ΔG* ∝ σ³/ΔG_v²`` with chemical driving force ``ΔG_v ∝ ΔT`` (linear in
    undercooling near equilibrium), so the nucleation rate carries
    ``exp(−ΔG*/kT) → exp(−K_N/(T·ΔT²))``. As ``ΔT = T_eq − T → 0`` this term
    kills the rate (no transformation *at* equilibrium): ``τ → ∞``.
  * **Diffusional mobility.** Atoms must diffuse for the new phase to grow:
    Arrhenius ``exp(−Q/RT)``. As ``T → 0`` this term kills the rate: ``τ → ∞``.

Their product gives a *minimum* ``τ`` at the nose:

    τ(T) = τ₀ · exp(Q/(R·T)) · exp(K_N/(T·ΔT²))          (T in **kelvin**)

The TTT "start"/"finish" lines (``X = 0.01``/``0.99``) are this same curve scaled
by ``(−ln(1−X))^{1/n}`` — parallel C-curves, the standard result.

3. Athermal martensite — Koistinen–Marburger + Andrews Mₛ
---------------------------------------------------------
If austenite is cooled past the **martensite-start** temperature ``Mₛ`` before
the diffusional reaction consumes it, the remainder shears to martensite
*athermally* — the fraction depends on how far below ``Mₛ`` you are, **not** on
time (Koistinen–Marburger):

    f = 1 − exp(−α·(Mₛ − T))           α ≈ 0.011 K⁻¹

``Mₛ`` itself is set by composition via the empirical **Andrews (1965)** linear
equation. Note KM is applied by :mod:`pathint` to the *retained* austenite left
after the diffusional path ``(1 − X_diff)``, never to the total — that is what
makes the product fractions sum to 1 by construction.

Units & conventions
-------------------
* **Temperature** is **°C** at every public boundary (matching :mod:`fe_c`); the
  Arrhenius/nucleation exponentials convert to **kelvin** internally via
  :data:`ABS_ZERO`. The undercooling ``ΔT`` is a *difference* (°C ≡ K), but the
  *absolute* ``T`` multiplying it inside the exponentials must be kelvin — the
  one easy unit slip here.
* **Composition** is **wt%** (as in :mod:`fe_c`); Andrews coefficients are
  per-wt%.
* **Fractions** are dimensionless in ``[0, 1]``.

The TTT C-curve constants ``(Q, K_N, τ₀)`` are a **calibrated semi-empirical**
fit (plain-carbon eutectoid: nose ≈ 550 °C / ≈ 1 s), not first-principles values
— this is a teaching model. Alloying shifts the real curves right (hardenability,
Phase 2); v1 holds the shape fixed and moves only ``T_eq`` (from ``fe_c``) and
``Mₛ`` (from Andrews) with composition.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import fe_c

# Physical constants.
R_GAS = 8.314462618          # universal gas constant, J/(mol·K)
ABS_ZERO = 273.15            # 0 °C in kelvin

# Koistinen–Marburger rate constant (K⁻¹). The classic value: gives ~0.90
# martensite at 100 K below Mₛ and ~0.96 at 150 K below — i.e. for a steel with
# Mₛ ≈ 200 °C, quenching to room temperature leaves a few percent retained γ.
KM_ALPHA = 0.011


# --------------------------------------------------------------------------- #
# 1. Isothermal JMAK / Avrami kinetics
# --------------------------------------------------------------------------- #
def avrami_fraction(t: float | np.ndarray, tau: float, n: float) -> float | np.ndarray:
    """Fraction transformed ``X(t) = 1 − exp(−(t/τ)ⁿ)`` at isothermal time ``t``.

    ``tau`` is the characteristic time (time to ``X = 0.632``); ``n`` the Avrami
    exponent. ``t`` may be a scalar or array. ``X(0) = 0``, ``X(τ) = 1 − e⁻¹``,
    ``X → 1`` as ``t → ∞``; monotonically increasing in ``t``.
    """
    if tau <= 0.0:
        raise ValueError(f"characteristic time τ must be > 0, got {tau}")
    if n <= 0.0:
        raise ValueError(f"Avrami exponent n must be > 0, got {n}")
    t = np.asarray(t, dtype=float)
    out = 1.0 - np.exp(-np.power(t / tau, n))
    return float(out) if out.ndim == 0 else out


def avrami_time_for_fraction(X: float, tau: float, n: float) -> float:
    """Invert :func:`avrami_fraction`: the time ``t`` to reach fraction ``X``.

    ``t = τ·(−ln(1−X))^{1/n}``. This is the map that turns the characteristic
    curve ``τ(T)`` into the TTT line for any fraction ``X`` (the start/finish
    lines are just ``X = 0.01``/``0.99``).
    """
    if not (0.0 < X < 1.0):
        raise ValueError(f"fraction X must be in the open interval (0, 1), got {X}")
    if tau <= 0.0:
        raise ValueError(f"characteristic time τ must be > 0, got {tau}")
    return tau * (-math.log(1.0 - X)) ** (1.0 / n)


def fit_avrami(t: np.ndarray, X: np.ndarray) -> tuple[float, float]:
    """Recover ``(n, τ)`` from an isothermal ``(t, X)`` series — the round-trip.

    Linearizes the Avrami law: ``ln(−ln(1−X)) = n·ln t − n·ln τ``, so a straight
    line through ``(ln t, ln(−ln(1−X)))`` has slope ``n`` and recovers
    ``τ = exp(−intercept/n)``. Points with ``X ∉ (0, 1)`` are dropped (the
    double-log is undefined there). This is the validation triad's analytical
    "recover the constant" leg.
    """
    t = np.asarray(t, dtype=float)
    X = np.asarray(X, dtype=float)
    mask = (X > 0.0) & (X < 1.0) & (t > 0.0)
    if mask.sum() < 2:
        raise ValueError("need at least two points with 0 < X < 1 and t > 0 to fit")
    x = np.log(t[mask])
    y = np.log(-np.log(1.0 - X[mask]))
    n, intercept = np.polyfit(x, y, 1)
    tau = math.exp(-intercept / n)
    return float(n), float(tau)


# --------------------------------------------------------------------------- #
# 2. The TTT C-curve — characteristic time τ(T) with a nose
# --------------------------------------------------------------------------- #
# Calibrated plain-carbon-eutectoid kinetic constants (semi-empirical; see the
# module docstring). Chosen so the diffusional nose lands at ≈ 550 °C / ≈ 1 s and
# the start/finish lines straddle the quench rates the four-curves demo uses.
Q_DIFFUSION = 140_000.0      # effective diffusion activation energy, J/mol (C/Fe scale)
K_NUCLEATION = 6.36e7        # nucleation-barrier parameter, K³ (sets the nose temperature)
TAU0 = 7.0e-10               # Avrami time prefactor, s (sets the nose time)
AVRAMI_N = 2.5               # Avrami exponent (constant in T — keeps the reaction additive)

# Bainite-start temperature: the diffusional product that forms above BS is
# pearlitic, below it (down to Mₛ) bainitic. A fixed v1 value for plain-carbon
# eutectoid (the morphology label, not a separate C-curve — see pathint).
BS_DEFAULT = 540.0           # °C


@dataclass(frozen=True)
class CCurve:
    """An isothermal TTT C-curve: characteristic time ``τ(T)`` and its readings.

    Bundles the kinetic law (``τ(T)`` from driving force × mobility) with the
    thermodynamic ceiling ``T_eq`` (above which there is no driving force) and the
    martensite floor ``Ms`` (below which athermal martensite, not this curve,
    governs). The defaults are the calibrated plain-carbon-eutectoid set; pass
    ``T_eq``/``Ms`` from :func:`~projects.steel.fe_c.A1` and :func:`andrews_Ms`
    for a specific steel.
    """

    T_eq: float = field(default_factory=fe_c.A1)   # °C; driving force vanishes here (A₁/A₃)
    Ms: float = 200.0                              # °C; martensite-start floor
    n: float = AVRAMI_N
    Q: float = Q_DIFFUSION
    K_N: float = K_NUCLEATION
    tau0: float = TAU0
    Bs: float = BS_DEFAULT

    def tau(self, T: float) -> float:
        """Characteristic time ``τ(T)`` (s) — time to ``X = 0.632`` at ``T`` (°C).

        ``τ = τ₀·exp(Q/RT)·exp(K_N/(T·ΔT²))`` with ``T`` in kelvin and
        ``ΔT = T_eq − T``. Returns ``inf`` at/above ``T_eq`` (zero driving force)
        — the guard that also avoids the ``ΔT → 0`` overflow.
        """
        if T >= self.T_eq:
            return math.inf
        T_K = T + ABS_ZERO
        dT = self.T_eq - T                          # undercooling (°C ≡ K, a difference)
        mobility_exp = self.Q / (R_GAS * T_K)        # Arrhenius: grows as T falls
        nucleation_exp = self.K_N / (T_K * dT * dT)  # barrier: grows as ΔT → 0
        try:
            return self.tau0 * math.exp(mobility_exp + nucleation_exp)
        except OverflowError:
            # Either edge of the window (ΔT → 0 near T_eq, or mobility → 0 at low
            # T) sends τ → ∞ — physically "no transformation here", numerically inf.
            return math.inf

    def time_to_fraction(self, T: float, X: float) -> float:
        """TTT time to reach fraction ``X`` at temperature ``T`` (°C).

        ``τ(T)·(−ln(1−X))^{1/n}`` — the C-curve for any fraction. ``X = 0.01`` is
        the conventional "start" line, ``X = 0.99`` the "finish".
        """
        return avrami_time_for_fraction(X, self.tau(T), self.n)

    def fraction(self, T: float, t: float) -> float:
        """Isothermal fraction transformed after holding time ``t`` (s) at ``T`` (°C)."""
        return avrami_fraction(t, self.tau(T), self.n)

    def nose(self, X: float = 0.01, n_scan: int = 4000) -> tuple[float, float]:
        """The nose of the ``X``-fraction C-curve: ``(T_nose °C, t_nose s)``.

        Found by scanning ``τ(T)`` over the active window ``(Ms, T_eq)`` for its
        minimum (argmin, per the advisor — robust where an analytic ``dτ/dT = 0``
        is messy), then scaling to the requested fraction. The nose is the
        shortest time to transformation and the temperature a quench must outrun.
        """
        temps = np.linspace(self.Ms + 1.0, self.T_eq - 1.0, n_scan)
        taus = np.array([self.tau(float(T)) for T in temps])
        i = int(np.argmin(taus))
        T_nose = float(temps[i])
        t_nose = avrami_time_for_fraction(X, float(taus[i]), self.n)
        return T_nose, t_nose


# --------------------------------------------------------------------------- #
# 3. Athermal martensite — Andrews Mₛ + Koistinen–Marburger
# --------------------------------------------------------------------------- #
# Andrews (1965) linear martensite-start equation, JISI 203:721. Mₛ in °C from
# wt% alloying; the canonical coefficients. (Andrews also gives a product form;
# the linear one is the textbook standard and what is implemented here.)
ANDREWS_BASE = 539.0
ANDREWS_COEFFS = {  # °C per wt%
    "C": -423.0, "Mn": -30.4, "Ni": -17.7, "Cr": -12.1, "Mo": -7.5,
}


def andrews_Ms(
    C: float, Mn: float = 0.0, Ni: float = 0.0, Cr: float = 0.0, Mo: float = 0.0
) -> float:
    """Martensite-start temperature ``Mₛ`` (°C) from composition (wt%), Andrews 1965.

    ``Mₛ = 539 − 423·C − 30.4·Mn − 17.7·Ni − 12.1·Cr − 7.5·Mo``. Carbon dominates;
    every alloying addition lowers ``Mₛ`` (and widens the martensite range that
    must be quenched through). Plain eutectoid (0.8 % C) → ≈ 200 °C; 4140
    (0.4C-0.9Mn-1.0Cr-0.2Mo) → ≈ 330 °C — both matching published values.
    """
    comp = {"C": C, "Mn": Mn, "Ni": Ni, "Cr": Cr, "Mo": Mo}
    return ANDREWS_BASE + sum(ANDREWS_COEFFS[el] * comp[el] for el in ANDREWS_COEFFS)


def koistinen_marburger(T: float, Ms: float, alpha: float = KM_ALPHA) -> float:
    """Athermal martensite fraction ``f = 1 − exp(−α·(Mₛ − T))`` at ``T`` (°C).

    Depends only on the undercooling below ``Mₛ`` (athermal — *not* on time): the
    fraction is fixed the instant a temperature is reached. ``f = 0`` at and above
    ``Mₛ`` (clamped), rising toward 1 as ``T`` falls. This is the fraction of the
    *austenite present at Mₛ*; :mod:`pathint` multiplies it by the retained
    ``(1 − X_diff)`` so the total never exceeds 1.
    """
    if T >= Ms:
        return 0.0
    return 1.0 - math.exp(-alpha * (Ms - T))
