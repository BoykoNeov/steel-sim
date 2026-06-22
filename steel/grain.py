"""Grain size & Hall–Petch — the grain-size strengthening axis (Steel Phase 5).

Steel's first **post-v1** phase. Phases 1–4 mapped a cooling path to a microstructure
and that microstructure to **hardness** (`properties.py`). Phase 5 adds the one structural
*length scale* none of that carried — the **grain size** — and through it the two
engineering quantities the hardness chain deliberately withholds: **yield strength**
(Hall–Petch) and the **ductile-brittle transition temperature** (Cottrell–Petch). This
module is *orthogonal* to the hardness model: it touches neither the frozen
`engines/diffusion` nor any frozen benchmark.

This file implements **Phase 5a** — austenite grain *growth* during the austenitizing hold
and the ASTM E112 grain-size-number bookkeeping — **Phase 5b** — the two grain-size
*property* laws (Hall–Petch yield + Cottrell–Petch DBTT, the cited Pickering ferrite-pearlite
pair) — and **Phase 5c** — the coupling (austenitizing hold → PAGS → ferrite grain → *both*
yield and DBTT) and the ``yield ≤ UTS`` consistency cross-check. The banked co-benefit figure
sits in :mod:`plots` (``grain_figure``); see `docs/plans/steel-production.md` §12.

5b — the Pickering pair: yield ↑ and DBTT ↓ with grain refinement
----------------------------------------------------------------
Two laws of the *same* Hall–Petch form with **opposite grain-size signs** — the headline
metallurgical fact that grain refinement is the **only** lever that raises strength *and*
improves toughness at once:

    σ_y  = f_σ(Mn, Si, N_free, %pearlite) + k_y·d^(−½)     grain term POSITIVE  (refine → stronger)
    DBTT = g_T(Si, N_free, %pearlite)     − k_T·d^(−½)     grain term NEGATIVE  (refine → tougher)

Si / free-N / pearlite raise **both** (strength↑ *and* DBTT↑ = embrittle); only the grain
term flips sign, so grain refinement is the lone co-improving lever. Coefficients are the
**cited Pickering ferrite-pearlite correlation** (Pickering, *Physical Metallurgy and the
Design of Steels*, 1978) — see [[pickering-strength-dbtt-source]]. This sign-opposition is a
**by-construction demonstration**, not a benchmark with teeth: both equations are cited, so
no held-out quantity could falsify it (the Phase-4 "wiring check" status). Phase 5's
falsifiable weight lives entirely in 5a's grain-growth holdout.

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
Hall–Petch / Pickering laws cite their coefficients with grain size in **mm** (so
``k_y ≈ 17.4 MPa·mm^(−½) ≡ 0.55 MPa·m^(−½) ≈ 0.6 MPa·√m``) — that µm→mm conversion lives at
*their* boundary (``_d_mm``), registry-tested. Free nitrogen ``N_free`` is in **wt %** (it
enters both laws under a √, so a wt%/ppm mix-up is a ~√1000 error) — also registry-tested.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import fe_c
from . import properties as prop
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


# --------------------------------------------------------------------------- #
# 3. The Pickering pair — Hall–Petch yield + Cottrell–Petch DBTT (Phase 5b)
# --------------------------------------------------------------------------- #
# Two laws of the SAME Hall–Petch form with OPPOSITE grain-size signs (module docstring).
# Coefficients are the cited Pickering ferrite-pearlite correlation — see
# [[pickering-strength-dbtt-source]]. Grain size enters in MILLIMETRES in both cited forms;
# we convert µm→mm at this boundary (_d_mm), registry-tested.
#
# --- Lower yield stress, ferrite-pearlite (MPa; d in mm) ----------------------
# σ_y = 53.9 + 32.34·Mn + 83.16·Si + 354.2·√N_free + (pearlite) + 17.4·d^(−½)
# The Mn/Si/N/grain coefficients are CITED (web-confirmed). With comp=None and no pearlite
# this reduces to the bare two-constant ferrite Hall–Petch teaching limit σ₀ + k_y·d^(−½).
YIELD_SIGMA0 = 53.9          # MPa — friction/base stress (composition- & grain-independent)
YIELD_K_MN = 32.34           # MPa per wt% Mn  (substitutional solid solution)
YIELD_K_SI = 83.16           # MPa per wt% Si  (substitutional solid solution)
YIELD_K_NF = 354.2           # MPa per (wt% free N)^(1/2)  (interstitial solid solution, √c)
YIELD_KY_MM = 17.402         # MPa·mm^(1/2) — Hall–Petch grain coefficient (d in mm)

# The pearlite contribution to YIELD is the ONE CALIBRATED coefficient (Pickering's cited
# yield equation is ferrite-matrix-controlled and carries no pearlite term). Grounded in a
# rule of mixtures: eutectoid pearlite lower-yield ≈ 400–450 MPa vs ferrite matrix ≈
# 200–250 MPa ⇒ (425 − 225)/100 ≈ 2 MPa per percent pearlite. Flagged calibrated; NOT tuned
# to the 5c figure (the sign-opposition is by-construction regardless — tuning buys nothing).
YIELD_K_PEARLITE = 2.0       # MPa per % pearlite  (rule-of-mixtures slope; calibrated, flagged)

# --- Impact transition temperature, ferrite-pearlite (°C; d in mm) ------------
# DBTT = −19 + 44·Si + 700·√N_free + 2.2·%pearlite − 11.5·d^(−½)
# The grain coefficient (−11.5) and the Si coefficient (+44) are web-confirmed; the −19 base,
# the 700·√N and the 2.2·%pearlite are recalled-canonical Pickering, cross-checked
# structurally (see source memory). The grain term carries the OPPOSITE sign to the yield law
# — the whole point of option (b).
ITT_BASE = -19.0             # °C — base transition temperature
ITT_K_SI = 44.0              # °C per wt% Si        (embrittles — raises DBTT)
ITT_K_NF = 700.0             # °C per (wt% free N)^(1/2)  (embrittles — raises DBTT)
ITT_K_PEARLITE = 2.2         # °C per % pearlite    (embrittles — raises DBTT)
ITT_KT_MM = 11.5             # °C·mm^(1/2) — grain coefficient, applied with a NEGATIVE sign

# --- Phosphorus: the signed-impurity foil (the §14 cold-shortness consequence) ----------------
# P is the lone *substitutional* element that raises strength AND DBTT through the same linear
# concentration term — the clean inverse of grain refinement (the only lever that improves both).
# It is the tramp impurity :mod:`steel.slag` partitions out; this is the **consumer that closes
# its consequence** — the F2-Slice-2 deferral (an off-spec-P heat threading the chain inert). It
# reads ``P_pct`` *explicitly* (a dedicated keyword), NOT through ``comp``/``Steel.minor()``, which
# deliberately withhold P so it is never fed silently to an unbenchmarked model.
#
# YIELD term — PINNABLE, the teeth. Thiele–Hošek's solid-solution model gives **+237 MPa per
# 1 at% P** (ΔR_p0.2 = G·ε·X_c/100, with G = 83000 MPa and ε = (140−100)/140 = 0.286 from the Fe/P
# atomic radii — PDF-verified, [[historical-impurity-pedagogy]]). The teeth are CROSS-SOURCE
# coherence, not the lone number: converting at%→wt% (×M_Fe/M_P below) gives ~427 MPa/wt% P, inside
# Total Materia's independent 365–620 MPa/wt% bracket; and Thiele's hardness increment 119.8 HV/wt%
# sits within ~6 % of the literature's 123–125 and the theoretical 127. We pin the cited at%-basis
# number and convert at the boundary — the registered unit trap: **strength is per at% P, DBTT per
# wt% P** (a ~1.8× basis difference; mixing them is the documented mistake).
YIELD_K_P_PER_AT = 237.0     # MPa per at% P  (Thiele–Hošek solid-solution model; PDF-verified)
M_FE = 55.845                # g/mol — iron, for the dilute wt%→at% conversion of phosphorus
M_P = 30.974                 # g/mol — phosphorus
AT_PCT_PER_WT_PCT_P = M_FE / M_P     # ≈ 1.803 (1 wt% P ≈ 1.803 at% P; so 1 at% P ≈ 0.555 wt%)

# DBTT term — NOT teeth, FLAGGED representative (the FERRITE_PAGS_RATIO posture). The P→DBTT slope
# is the one number §14 flagged as *not cleanly pinnable*, and a 2026-06-22 sourcing pass
# (next-directions A2) CONFIRMED it cannot earn teeth: the bulk-wt% slope is a path-dependent
# **reduced form** of grain-boundary segregation physics. The clean modern relations express
# embrittlement vs GB **coverage** — e.g. Song et al., *Mater. Sci. Eng. A* 528 (2011) for a
# Ti-stabilized IF steel, DBTT = 3.12·C_P − 118.87 with C_P in at% AT THE BOUNDARY — and bulk P maps
# onto that coverage through a Langmuir–McLean isotherm (ΔG_seg(P) ≈ 45 kJ/mol) whose enrichment
# depends on grain size, thermal history and C co-segregation. So this stays a flagged bulk
# coefficient — but now a *traceable* one, pinned to the centre of a documented engineering bracket
# rather than a bare mid-band guess:
#   * UPPER anchor (the most-cited reduced-form figure): P raises the impact transition temperature by
#     ~7–7.8 °C per 0.01 wt% P ("based on several investigations" — IDOT structural-steels report
#     PRR-174) ⇒ ~70–78 °C per 0.1 wt%.
#   * LOWER anchor: other reduced-form readings give ~40 °C per 0.1 wt% (the §14.1 spread).
# Documented bracket ≈ 40–78 °C per 0.1 wt% P (≈ 400–780 °C/wt%); we pin its centre. That 40–78 spread
# is NOT cross-source coherence — it is consensus that the bulk number is processing-dependent — so this
# carries *direction and rough magnitude*, never a benchmark; the strength term (YIELD_K_P_PER_AT) holds
# the teeth. Override per call. (Modelling the McLean coverage pathway, so the bulk scatter becomes an
# *output*, is the named B-escalation deferred as new physics with its own triad.)
ITT_K_P = 600.0             # °C per wt% P  (≈ 60 °C/0.1 wt%, centre of the documented 40–78 band; FLAGGED — not teeth)

# Free nitrogen is not in the STEELS registry → a flagged default (a typical small value, wt%).
# It enters BOTH laws under a √ (raises strength AND DBTT — an embrittler), so it does NOT
# affect the grain-term sign-opposition; the grain / Si / pearlite terms carry the story.
# Override per call. 0.005 wt% ≈ 50 ppm free N (semi-killed steel); a clean Al-killed steel
# is lower (~0.002).
DEFAULT_N_FREE_PCT = 0.005

# Above this martensite fraction the diffusional ferrite-pearlite laws do not apply → nan
# (the HRC-nan-on-a-soft-tail idiom; martensite strength is carbon/lath-dominated and its
# packet/block Hall–Petch is deferred). NAMED limit: bainite is *also* strictly outside the
# ferrite-pearlite domain (the bainite-deferral idiom), but — per plan — only martensite
# triggers the nan; a bainitic structure is loosely-out-of-domain, not guarded.
MARTENSITE_NAN_LIMIT = 0.5

# Room temperature (°C) — the reference service temperature a DBTT is read *against*: a steel
# whose DBTT sits above it is brittle in the hand, below it ductile. This is a display /
# interpretation reference for the readouts and the interactive figure (``plots`` and the
# notebook/app surfaces), NOT used by any physics function here — DBTT is returned as an absolute
# temperature, and where it lands relative to service temperature is the engineering question the
# surfaces frame. Exposed here (the matplotlib-free physics module) so every consumer shares one
# value. 20 °C is the conventional "room temperature"; the demo steel's DBTT crosses it across the
# austenitizing range (the ductile→brittle story, test_grain.py).
ROOM_TEMPERATURE_C = 20.0


def _d_mm(d_um: float) -> float:
    """µm → mm at the cited-equation boundary (the registered unit trap). d must be > 0."""
    if d_um <= 0.0:
        raise ValueError(f"grain diameter must be > 0 µm, got {d_um}")
    return d_um / 1000.0


def _solute_strengthening(comp: dict | None, N_free_pct: float, P_pct: float = 0.0) -> float:
    """Pickering substitutional (Mn, Si, **P**) + interstitial (√N_free) yield contribution (MPa).

    Phosphorus enters as a substitutional solid-solution term **linear in its atomic fraction**
    (Thiele–Hošek): the cited ``YIELD_K_P_PER_AT`` is per **at%**, so the wt% ``P_pct`` is
    converted at this boundary (``× AT_PCT_PER_WT_PCT_P``) — the registered at%/wt% unit trap.
    ``P_pct`` is threaded explicitly (never via ``comp`` / ``Steel.minor()``), so it stays zero
    unless a caller opts in — P is never fed silently to the law.
    """
    comp = comp or {}
    if N_free_pct < 0.0:
        raise ValueError(f"free nitrogen must be ≥ 0 wt%, got {N_free_pct}")
    if P_pct < 0.0:
        raise ValueError(f"phosphorus must be ≥ 0 wt%, got {P_pct}")
    return (
        YIELD_K_MN * comp.get("Mn", 0.0)
        + YIELD_K_SI * comp.get("Si", 0.0)
        + YIELD_K_NF * math.sqrt(N_free_pct)
        + YIELD_K_P_PER_AT * (P_pct * AT_PCT_PER_WT_PCT_P)
    )


def hall_petch_yield_MPa(
    d_um: float, *, comp: dict | None = None, f_pearlite: float = 0.0,
    N_free_pct: float = DEFAULT_N_FREE_PCT, f_martensite: float = 0.0, P_pct: float = 0.0,
) -> float:
    """Lower yield strength (MPa) of a ferrite-pearlite steel — Pickering + Hall–Petch.

    ``σ_y = σ₀ + k_Mn·Mn + k_Si·Si + k_N·√N_free + k_pearl·%pearlite + k_P·at%P + k_y·d^(−½)``

    The grain-size term is **positive**: refine the grain (smaller ``d``) and yield *rises*.
    ``P_pct`` (wt%, default 0) adds Thiele–Hošek's phosphorus solid-solution term — P is the
    signed-impurity foil: it *raises* yield here AND *raises* DBTT in :func:`cottrell_petch_dbtt_C`
    (the cold-shortness consequence :mod:`steel.slag` leaves to this consumer to close).
    ``comp`` is the minor-alloy ``{element: wt%}`` dict (``Steel.minor()`` — only Mn, Si are
    read by Pickering's yield form). ``f_pearlite`` is the **mass fraction** in ``[0, 1]``
    (e.g. ``fe_c.equilibrium_constituents(C0).f_pearlite`` — the *equilibrium* slow-cool
    pearlite from carbon, **not** the actual cooling product), converted to percent for
    Pickering's per-percent coefficient internally. With ``comp=None``, ``f_pearlite=0`` *and*
    ``N_free_pct=0`` this is the bare two-constant ferrite Hall–Petch teaching limit
    ``σ₀ + k_y·d^(−½)`` (the default ``N_free`` adds its ~25 MPa interstitial term).

    Returns **nan** when ``f_martensite`` exceeds :data:`MARTENSITE_NAN_LIMIT` — the
    ferrite-pearlite laws do not describe a martensitic structure (carbon/lath-dominated;
    its packet Hall–Petch is deferred), the HRC-``nan``-on-a-soft-tail idiom. ``d`` is µm.
    """
    if f_martensite > MARTENSITE_NAN_LIMIT:
        return float("nan")
    grain = YIELD_KY_MM * _d_mm(d_um) ** -0.5
    return (
        YIELD_SIGMA0
        + _solute_strengthening(comp, N_free_pct, P_pct)
        + YIELD_K_PEARLITE * 100.0 * f_pearlite
        + grain
    )


def cottrell_petch_dbtt_C(
    d_um: float, *, comp: dict | None = None, f_pearlite: float = 0.0,
    N_free_pct: float = DEFAULT_N_FREE_PCT, f_martensite: float = 0.0, P_pct: float = 0.0,
) -> float:
    """Ductile-brittle transition temperature (°C) — Cottrell–Petch / Pickering ITT.

    ``DBTT = −19 + 44·Si + 700·√N_free + 2.2·%pearlite + k_P·%P − 11.5·d^(−½)``

    The grain-size term is **negative** — the *opposite* sign to :func:`hall_petch_yield_MPa`
    — so refining the grain *lowers* DBTT (tougher) while it *raises* yield (stronger): the
    lone co-improving lever, the headline of option (b). Si / free-N / pearlite raise DBTT
    (embrittle), the same direction they raise yield. ``f_pearlite`` is the **mass fraction**
    in ``[0, 1]`` (the equilibrium value from carbon, as in the yield law).

    ``P_pct`` (wt%, default 0) adds phosphorus embrittlement — P raises DBTT *and* yield, the
    signed foil that makes grain refinement special. **This slope is FLAGGED representative**
    (:data:`ITT_K_P`), not a benchmark: it is the centre of a documented engineering bracket
    (≈ 40–78 °C per 0.1 wt% P) and carries the *direction and rough magnitude* of cold-shortness,
    the one number §14 could not cleanly pin — the bulk slope is a reduced form of grain-boundary
    *coverage* physics, not a falsifiable bulk law. The strength term carries this slice's teeth.

    This is a transition **temperature**, *not* a Charpy energy: no shelf energies, no
    absolute J, no tempering-axis non-monotonicity — those stay Phase 3b's named ceiling
    (``properties.toughness_index`` is untouched). Returns **nan** for a martensitic
    structure (``f_martensite`` past :data:`MARTENSITE_NAN_LIMIT`), as the yield law does.
    ``d`` is µm.
    """
    if f_martensite > MARTENSITE_NAN_LIMIT:
        return float("nan")
    comp = comp or {}
    if N_free_pct < 0.0:
        raise ValueError(f"free nitrogen must be ≥ 0 wt%, got {N_free_pct}")
    if P_pct < 0.0:
        raise ValueError(f"phosphorus must be ≥ 0 wt%, got {P_pct}")
    grain = ITT_KT_MM * _d_mm(d_um) ** -0.5
    return (
        ITT_BASE
        + ITT_K_SI * comp.get("Si", 0.0)
        + ITT_K_NF * math.sqrt(N_free_pct)
        + ITT_K_PEARLITE * 100.0 * f_pearlite
        + ITT_K_P * P_pct
        - grain
    )


# --------------------------------------------------------------------------- #
# 4. Coupling (Phase 5c) — austenitizing hold → PAGS → ferrite grain → yield + DBTT
# --------------------------------------------------------------------------- #
# 5a gives the prior-austenite grain size (PAGS) a part inherits from its austenitizing
# hold; 5b's two laws act on the *ferrite* grain size. 5c bridges them: austenite grain
# boundaries are the nucleation sites for pro-eutectoid ferrite, so a finer austenite grain
# seeds a finer ferrite grain — the metallurgical reason over-austenitizing (hotter / longer)
# costs *both* strength and toughness, and the reason grain refinement is the lone lever that
# improves both at once.
#
# ISOLATED AT A FIXED COOLING RATE (named, deliberate — the 3c single-quench analogue). The
# ferrite grain size depends on the cooling rate too — often *more* than on the PAGS (faster
# cooling undercools further → more nucleation → finer ferrite). 5c reads the PAGS effect at
# *one* cooling rate, folding that rate's influence into the calibrated proportionality below,
# exactly as 3c read the carbon gradient at one quench. A cooling-rate axis on ferrite grain
# size is a later refinement, not this coupling.
#
# FERRITE_PAGS_RATIO is the ONE CALIBRATED constant of 5c (flagged, like 5a's m/D₀/K₀ and 5b's
# pearlite-in-yield slope). d_α = ratio · d_PAGS with ratio < 1 (several ferrite grains nucleate
# per austenite grain → ferrite is finer than the austenite it forms from). ~0.5 is a
# representative normalized-/air-cool value; the precise number does not change the co-benefit
# *direction* (that is by-construction from the two Pickering signs — see the module doc), only
# the absolute grain sizes, so it is documented once and not agonized over. NOT a benchmark.
FERRITE_PAGS_RATIO = 0.5


def ferrite_grain_size(pags_um: float, *, ratio: float = FERRITE_PAGS_RATIO) -> float:
    """Ferrite grain size (µm) seeded by a prior-austenite grain size ``pags_um`` (µm).

    ``d_α = ratio · d_PAGS`` — austenite grain boundaries nucleate pro-eutectoid ferrite, so a
    finer austenite grain gives a finer ferrite grain (``ratio < 1``: several ferrite grains per
    austenite grain). ``ratio`` is the **calibrated** :data:`FERRITE_PAGS_RATIO` at a fixed
    cooling rate (the named single-variable isolation); override per call. Linear and monotone:
    the coupling carries the *direction* (coarser PAGS → coarser ferrite), not a benchmarked
    absolute.
    """
    if pags_um <= 0.0:
        raise ValueError(f"PAGS must be > 0 µm, got {pags_um}")
    if ratio <= 0.0:
        raise ValueError(f"ferrite/PAGS ratio must be > 0, got {ratio}")
    return ratio * pags_um


@dataclass(frozen=True)
class GrainProperties:
    """The coupled Phase-5c result: an austenitizing hold → grain size → yield + DBTT.

    All grain sizes **µm**, ``yield_MPa`` / ``uts_MPa`` **MPa**, ``dbtt_C`` **°C**,
    ``f_pearlite`` a mass fraction ``[0, 1]``. ``uts_MPa`` is the hardness-derived ultimate
    tensile strength of the *same* ferrite-pearlite structure (``properties`` model), carried
    only for the :attr:`yield_below_uts` consistency cross-check (see
    :func:`coupled_grain_properties`).
    """

    austenitizing_T: float       # °C
    austenitizing_t: float       # hours
    pags_um: float               # prior-austenite grain size (5a)
    ferrite_um: float            # coupled ferrite grain size (5c)
    f_pearlite: float            # equilibrium pearlite fraction from carbon (fe_c, 1b)
    yield_MPa: float             # Hall–Petch / Pickering lower yield (5b)
    dbtt_C: float                # Cottrell–Petch / Pickering DBTT (5b)
    uts_MPa: float               # hardness-derived UTS of the FP structure (properties)

    @property
    def yield_below_uts(self) -> bool:
        """``True`` when the Pickering yield does not exceed the hardness-derived UTS.

        The Phase-5c **consistency / scope-boundary** cross-check (NOT a benchmark with teeth —
        the only teeth in Phase 5 are 5a's grain-growth holdout). In the realistic
        ferrite-pearlite window ``yield ≈ 0.4–0.6·UTS``, so this never bites; it would fail only
        at **sub-micron ferrite** (~1 µm), which the austenitizing route never reaches — the
        scope boundary made explicit. A ``nan`` UTS (carbon outside the ISO-18265 table's
        ~150–550 HV band) is treated as "no violation detectable", not a failure.
        """
        return not (self.yield_MPa > self.uts_MPa)   # nan UTS ⇒ comparison False ⇒ True


def coupled_grain_properties(
    T_austenitize: float, t_hours: float, C: float, *,
    comp: dict | None = None, d0: float = GROWTH_D0,
    ferrite_ratio: float = FERRITE_PAGS_RATIO, N_free_pct: float = DEFAULT_N_FREE_PCT,
    P_pct: float = 0.0,
) -> GrainProperties:
    """Couple an austenitizing hold to the ferrite-pearlite yield **and** DBTT (Phase 5c).

    The whole 5c chain in one call, all *reuse* of validated pieces — no new physics:

        austenitize (T, t) → PAGS (:func:`austenite_grain_size`, 5a)
          → ferrite grain (:func:`ferrite_grain_size`, the calibrated coupling)
          → yield (:func:`hall_petch_yield_MPa`) + DBTT (:func:`cottrell_petch_dbtt_C`) (5b)

    ``%pearlite`` is the **equilibrium** slow-cool value from carbon
    (:func:`fe_c.equilibrium_constituents`, Phase 1b) — the structure these ferrite-pearlite
    laws describe, read at the fixed cooling rate the coupling assumes. The PAGS kinetics are the
    S960MC-calibrated grain-growth model (one calibrated model, reused for any steel, exactly as
    5a treats it); the ``comp`` minor-alloy dict (``Steel.minor()`` — Mn/Si read by Pickering)
    feeds the yield/DBTT laws.

    ``uts_MPa`` is computed from the same structure's ferrite-pearlite hardness
    (:func:`properties.vickers_ferrite_pearlite` → :func:`properties.tensile_strength_MPa`) for
    the :attr:`GrainProperties.yield_below_uts` cross-check; it is *not* part of the grain
    physics. ``P_pct`` (wt%, default 0) threads phosphorus into *both* laws — the one piece here
    that is **not** pure reuse: it adds Thiele's P solid-solution strengthening (pinnable) and the
    flagged P→DBTT embrittlement, the consumer that closes :mod:`steel.slag`'s cold-shortness
    deferral on a normalized heat. ``T`` is °C, ``t`` hours, ``C`` wt%; grain sizes returned in µm.
    """
    pags = austenite_grain_size(T_austenitize, t_hours, d0=d0)
    d_ferrite = ferrite_grain_size(pags, ratio=ferrite_ratio)
    f_pearlite = fe_c.equilibrium_constituents(C).f_pearlite
    sigma_y = hall_petch_yield_MPa(
        d_ferrite, comp=comp, f_pearlite=f_pearlite, N_free_pct=N_free_pct, P_pct=P_pct,
    )
    dbtt = cottrell_petch_dbtt_C(
        d_ferrite, comp=comp, f_pearlite=f_pearlite, N_free_pct=N_free_pct, P_pct=P_pct,
    )
    uts = float(prop.tensile_strength_MPa(prop.vickers_ferrite_pearlite(C, comp=comp)))
    return GrainProperties(
        austenitizing_T=T_austenitize, austenitizing_t=t_hours,
        pags_um=pags, ferrite_um=d_ferrite, f_pearlite=f_pearlite,
        yield_MPa=sigma_y, dbtt_C=dbtt, uts_MPa=uts,
    )
