"""Grain size & Hall–Petch — the grain-size strengthening axis (Steel Phase 5).

Steel's first **post-v1** phase. Phases 1–4 mapped a cooling path to a microstructure
and that microstructure to **hardness** (`properties.py`). Phase 5 adds the one structural
*length scale* none of that carried — the **grain size** — and through it the two
engineering quantities the hardness chain deliberately withholds: **yield strength**
(Hall–Petch) and the **ductile-brittle transition temperature** (Cottrell–Petch). This
module is *orthogonal* to the hardness model: it touches neither the frozen
`engines/diffusion` nor any frozen benchmark.

This file currently implements **Phase 5a** — austenite grain *growth* during the
austenitizing hold, and the ASTM E112 grain-size-number bookkeeping. The Hall–Petch yield
and the Cottrell–Petch DBTT (5b) and their coupling/figure (5c) land on top of it; see
`docs/plans/steel-production.md` §12.

5a — austenite grain growth `Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t`
-------------------------------------------------------
A part held at the austenitizing temperature grows its austenite grains by curvature-driven
(normal) coarsening. The prior-austenite grain size (PAGS) it inherits is the input the
property laws of 5b act on — and the reason *over*-austenitizing (hotter / longer) costs you
both strength and toughness.

What is **cited** vs **calibrated** — the non-circularity discipline (as in 2b/3b/4):
  * **CITED: Q = 329.95 kJ/mol** — the activation energy of a published S960MC grain-growth
    study (open access, NCBI PMC9737238). This is what carries the benchmark's *teeth*: the
    Arrhenius **temperature** scaling across 900–1200 °C.
  * **CALIBRATED** (with Q held at the cited value) to that study's *isothermal* grain-size
    table: the exponent ``m ≈ 4.22``, the initial size ``D₀ ≈ 14.46 µm``, and ``K₀``. Named
    caveat: the paper's *headline* ``m = 3.03`` comes from a different (continuous-heating)
    fit; its own isothermal table prefers ``m ≈ 4.2``, and the literature spread is large
    (``n ≈ 2.6–6.5``, ``Q ≈ 256–572 kJ/mol``). The time-exponent is method-/steel-specific,
    so it is calibrated, not asserted.

The **teeth** (the only genuinely falsifiable leg of Phase 5 — see the 5c demo's
by-construction caveat) is a **holdout**: fit the kinetic constants on the 900 & 1200 °C
rows only and *predict* the held-out 1000 & 1100 °C rows (→ within ~16 %). That is a real
cross-temperature prediction; it could have missed. The full-table reproduction is asserted
only *loosely* (grain-growth fits are inherently scattered, and ``Q`` is weakly determined
by this data).

Units (the registered trap — cf. chip's CGS/SI, oxidation's µm)
---------------------------------------------------------------
Internal grain size is **µm** (the cross-module currency), hold time **hours**, temperature
input **°C** (converted to **K** for the Arrhenius factor), ``Q`` in **J/mol**. The 5b
Hall–Petch / Pickering laws cite coefficients with grain size in **mm** — that conversion
lives at *their* boundary, registry-tested, not here.
"""
from __future__ import annotations

import math

import numpy as np

from .kinetics import R_GAS, ABS_ZERO

# --------------------------------------------------------------------------- #
# 1. Austenite grain growth — Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t  (S960MC, PMC9737238)
# --------------------------------------------------------------------------- #
# CITED: the activation energy (the Arrhenius temperature scaling — the teeth).
GROWTH_Q = 329.95e3          # J/mol — activation energy for austenite grain growth (cited)

# CALIBRATED to the cited study's ISOTHERMAL grain-size table, with GROWTH_Q held fixed.
# (The paper's headline m = 3.03 is a continuous-heating fit; its isothermal data prefer
# m ≈ 4.2. Time-exponent is method-/steel-specific — calibrated, not cited. See module doc.)
GROWTH_M = 4.2225            # grain-growth exponent (dimensionless)
GROWTH_D0 = 14.4598          # µm — initial (pre-growth) austenite grain size
GROWTH_K0 = 1.891137e19      # µm^m / hour — pre-exponential (internal units µm, hours)

# The published S960MC isothermal grain-size table — the benchmark data (NOT used by the
# model itself; the holdout test in test_grain.py refits on a subset and predicts the rest).
# Frozen reference, like properties.py's E140 points: published facts, interpolated/compared,
# never redistributed wholesale.
S960MC_TEMP_C = np.array([900.0, 1000.0, 1100.0, 1200.0])         # austenitizing temperature
S960MC_TIME_H = np.array([0.5, 1.0, 2.0, 4.0, 6.0, 8.0])          # soaking time, hours
S960MC_GRAIN_UM = np.array([                                       # mean grain diameter, µm
    [13.1, 15.4, 16.0, 16.8, 20.4, 24.7],
    [25.3, 26.0, 29.4, 30.8, 32.8, 39.2],
    [38.5, 39.2, 45.5, 48.8, 54.1, 58.8],
    [60.1, 64.5, 71.4, 80.0, 95.2, 111.1],
])


def austenite_grain_size(
    T_celsius: float, t_hours: float, d0: float = GROWTH_D0,
    *, Q: float = GROWTH_Q, m: float = GROWTH_M, K0: float = GROWTH_K0,
) -> float:
    """Prior-austenite grain size (µm) after holding ``t_hours`` at ``T_celsius``.

    Integrates the normal-grain-growth law ``Dᵐ = D₀ᵐ + K₀·exp(−Q/RT)·t`` (the closed-form
    isothermal solution). ``d0`` is the grain size entering the hold (µm); at ``t = 0`` the
    result is ``d0`` exactly (the seam). Hotter or longer → larger grain, monotonically.

    The kinetic constants default to the cited/calibrated S960MC values (module docstring);
    they are exposed as keyword overrides so the holdout benchmark can refit them. ``T`` is
    °C (converted to kelvin for the Arrhenius factor); ``t`` is hours; the result is µm.
    """
    if t_hours < 0.0:
        raise ValueError(f"hold time must be ≥ 0 hours, got {t_hours}")
    if d0 <= 0.0:
        raise ValueError(f"initial grain size must be > 0 µm, got {d0}")
    T_K = T_celsius + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"temperature must be above absolute zero, got {T_celsius} °C")
    if t_hours == 0.0:
        return float(d0)                      # the seam: no hold ⇒ d0 exactly (no float round-trip)
    grown = d0 ** m + K0 * math.exp(-Q / (R_GAS * T_K)) * t_hours
    return grown ** (1.0 / m)


def grain_growth_rate(
    T_celsius: float, t_hours: float, d0: float = GROWTH_D0,
    *, Q: float = GROWTH_Q, m: float = GROWTH_M, K0: float = GROWTH_K0,
) -> float:
    """Instantaneous growth rate ``dD/dt`` (µm/hour) at hold time ``t_hours``.

    The analytic derivative of :func:`austenite_grain_size`: ``dD/dt = K₀·exp(−Q/RT)/(m·Dᵐ⁻¹)``.
    Always ``≥ 0`` (growth is one-way) and **decreasing** in ``t`` as ``D`` grows — the
    coarsening driving force (grain-boundary curvature) falls as grains enlarge. Used by the
    dissipative-direction invariant test; rises steeply with ``T`` (the Arrhenius factor).
    """
    D = austenite_grain_size(T_celsius, t_hours, d0, Q=Q, m=m, K0=K0)
    T_K = T_celsius + ABS_ZERO
    return K0 * math.exp(-Q / (R_GAS * T_K)) / (m * D ** (m - 1.0))


# --------------------------------------------------------------------------- #
# 2. ASTM E112 grain-size number  G ↔ mean diameter d  (exact by construction)
# --------------------------------------------------------------------------- #
# n = grains per in² at 100× = 2^(G−1). One image-in² at 100× is (1/100 in)² = 645.16/100²
# = 0.064516 mm² of real specimen, so real grains/mm²  N_A = ASTM_NA_PER_G1 · 2^(G−1) with
# ASTM_NA_PER_G1 = 100²/645.16 = 15.500 (grains/mm² at G = 1). Mean diameter d = 1/√N_A.
# Anchors (textbook): G1 → 254 µm, G8 → 22.5 µm.
ASTM_NA_PER_G1 = 100.0 ** 2 / 645.16      # grains per mm² at G = 1 (i.e. 1 grain/in² @100×)


def astm_grain_size_number(d_um: float) -> float:
    """ASTM E112 grain-size number ``G`` for a mean grain diameter ``d_um`` (µm).

    Inverse of :func:`grain_diameter_um`; the pair round-trips exactly. Larger ``G`` ⇒ finer
    grain (each +1 in ``G`` doubles grains/area → divides ``d`` by √2). ``G`` is not clamped
    to integers — a real grain size lands between numbers.
    """
    if d_um <= 0.0:
        raise ValueError(f"grain diameter must be > 0 µm, got {d_um}")
    d_mm = d_um / 1000.0
    N_A = 1.0 / d_mm ** 2                          # grains per mm²
    return 1.0 + math.log2(N_A / ASTM_NA_PER_G1)


def grain_diameter_um(G: float) -> float:
    """Mean grain diameter (µm) for ASTM E112 grain-size number ``G``.

    ``d = 1000 / √(15.500 · 2^(G−1))`` µm — the exact inverse of
    :func:`astm_grain_size_number`. G1 → 254 µm, G8 → 22.5 µm (the textbook anchors).
    """
    N_A = ASTM_NA_PER_G1 * 2.0 ** (G - 1.0)        # grains per mm²
    d_mm = 1.0 / math.sqrt(N_A)
    return d_mm * 1000.0
