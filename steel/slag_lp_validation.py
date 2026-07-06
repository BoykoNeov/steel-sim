"""Holdout validation of the cited Healy L_P model against an INDEPENDENT measured dataset (front-end B3, phosphorus leg).

*Does Healy's 1970 phosphorus-partition correlation predict L_P out-of-sample — or is
:mod:`steel.slag`'s "order-of-magnitude only" posture for dephosphorization forced?* This is the
**phosphorus twin of** :mod:`steel.slag_validation` (which did the sulfur/C_S leg): it grades a
cited correlation the engine already uses (:func:`steel.slag.phosphorus_partition`) against measured
L_P the correlation was **never fit to**, touches no engine, and lets the data set the verdict.
Nothing here feeds the frozen pipeline.

THE CIRCULARITY GATE (why this dataset). Healy (1970) is a **regression fit** to that era's
slag–metal heats; grading it against its own training data is the vacuous-benchmark trap the project
names ([[di-crosscheck-source]]). An honest holdout needs measured L_P from a source the fit could
not have seen. :data:`HOLDOUT` is Drain–Monaghan–Longbottom–Chapman–Zhang–Chew, *ISIJ International*
**58** (2018) 1965, Table 4 — the CaO–SiO₂–MgO–FetO–(MnO–Al₂O₃–TiO₂–P₂O₅) system, 33 of the authors'
**own measured equilibrium heats** (≥10 h, Ar). Independence here is in fact *cleaner* than the C_S
leg's:

1. **Temporal.** Measured 2018, **forty-eight years after** the 1970 correlation, in a different
   laboratory (Wollongong / BlueScope). It cannot be in Healy's fit.
2. **Parametric.** Healy's L_P reads **only** ``%CaO``, total slag iron ``%Fe_t`` and ``T`` — its four
   coefficients (``22350``, ``0.08``, ``2.5``, ``−16``) are fixed 1970 numbers, and there is **no
   optical basicity** in the formula (unlike Sosinsky–Sommerville), so there is not even a fitted-Λ
   input to worry about. The composite under test has **zero parameters fit to these data**.

The measured L_P is defined **exactly as Healy's** — the mass ratio ``(%P)_slag / [%P]_metal`` (Drain
Eq. 8; ``( )`` slag, ``[ ]`` metal), **not** a phosphate capacity ``C_PO₄`` and **not** a
distribution on ``(%P₂O₅)``. So the two numbers are directly comparable with no standard-state offset.
The experimental temperatures (1550–1700 °C) sit in the steelmaking range Healy addresses; the slag
**basicity** sweeps ``v = %CaO/%SiO₂`` from ≈ 1.8 to ≈ 5.6, i.e. from Healy's fit domain up into a
**high-lime extrapolation** — which is exactly where the model was already flagged to over-predict.

THE TRANSCRIPTION GUARDS (di-crosscheck, both baked into the suite — and their scope). Two
independent checks, because Table 4 has no repeat-reading column the way Nzotta's C_S table did:

* :func:`validate_lp_consistency` — Table 4 tabulates ``(%P₂O₅)`` in the slag, ``[%P]`` in the metal
  **and** the derived ``L_P`` in separate columns, so they must be mutually consistent:
  ``L_P ≈ (%P₂O₅ · M_P·2/M_P₂O₅) / [%P]``. Recomputing L_P from the other two columns (propagating the
  last-digit rounding of **both** ``%P₂O₅`` and ``[%P]``) must bracket the tabulated L_P. A
  fat-fingered digit in any of the three columns breaks the bracket. **Scope:** on the lowest-``[%P]``
  rows (``[%P] = 0.003``–``0.004``) the ±0.0005 rounding band is ±~15 %, so the guard is coarse there
  — it catches gross transcription errors, not a last-digit slip (a named limit, as the C_S guard was
  scoped to the C_S column only).
* :func:`reproducibility_crosscheck` — the seven R-series repeats (same nominal slag, 1650 °C) are
  summarised **in the paper's prose** as "mean L_P 190, standard deviation 7 (3.7 %)". Recomputing the
  mean and standard deviation of the seven transcribed R rows must reproduce that printed pair — an
  end-to-end cross-check of the L_P column against a statistic printed *outside* the table (the analog
  of the C_S leg's Table-6↔Table-9 overlap check). It also fixes the **measurement scatter floor**
  (~3.7 %, ≈ 0.016 in log₁₀) below which no model–data gap is meaningful.

The **composition columns** (CaO/SiO₂/FetO — Healy's actual inputs) carry **no internal-consistency
guard**: unlike the chemically-linked P₂O₅/[%P]/L_P triple, they are independent measured quantities
with nothing to recompute one from another. They were instead **cross-checked row-for-row against the
source PDF's text extraction** — all 33 rows of every composition column match exactly (verified at
build time). Named limit: that is a check against the *same* (deterministic, digital-PDF, non-OCR)
extraction the numbers were transcribed from, so it catches a hand-copy slip but not a shared
extraction artifact; there is no second-tool independent transcription of the composition columns.

THE VERDICT THE DATA GIVES — a *quantified bias map*, not a clean pass (computed, not asserted — see
:func:`summary`). Unlike the C_S leg (which the data *upgraded* to "holdout-validated"), Healy's L_P
comes out **honestly benchmarked with a measured, composition-dependent bias**:

  * **It carries at moderate basicity.** On the B2 series (``v ≈ 2``, ``%CaO ≈ 46`` — Healy's own fit
    domain) the model is **near-exact**: mean bias ≈ ×1.0. The pooled fit over all 33 points is a mild
    over-prediction (≈ ×1.5), well inside the factor-2–3 scatter such correlations carry.
  * **It over-predicts at high lime — the pre-registered flag, now measured.** The bias is **not
    uniform: it climbs monotonically with basicity** — B2 (``v≈2``) ≈ ×1.0 → B4 (``v≈4``) ≈ ×1.9 → B5
    (``v≈5``) ≈ ×2.0, and split by lime, ``%CaO < 50`` ≈ ×1.1 vs ``%CaO ≥ 55`` ≈ ×2.3. The mechanism is
    structural: Healy's ``+0.08·%CaO`` term is **linear and unbounded**, but the real L_P **saturates**
    with basicity (Drain, and others, report L_P levelling beyond ``v ≈ 2.5``). So extrapolating the
    linear-lime term above its fit domain inflates L_P — exactly the "known to over-predict at high
    lime" caveat :mod:`steel.slag` already carried, turned from a vague warning into a **quantified
    map** (≈ ×1.0 at ``v≈2`` rising to ≈ ×2 at ``v≈5``).
  * **The temperature direction is right.** The dedicated T-series (rows 8–10, 1550 → 1700 °C) has
    measured L_P **falling** with temperature, and Healy's ``+22350/T`` term reproduces that direction.
    It is **not** a cleanly isolated slope (the three points co-vary in composition — FetO 16 → 22 %),
    so the direction is confirmed but the magnitude is confounded — reported honestly, not as a second
    tooth.
  * **A named structural ceiling.** The dataset documents a **maximum L_P at ≈ 20 % FetO** for a given
    basicity (dephosphorization needs *both* oxygen potential and lime; too much FeO dilutes the lime).
    Healy's ``+2.5·log(%Fe_t)`` is **monotonic** in iron oxide, so it cannot represent that optimum —
    a structural limit of the bulk correlation, named, not a fitted defect.

CITED vs CALIBRATED. *Cited:* every measured number (Drain 2018 Table 4) and the Healy correlation +
its coefficients (from :mod:`steel.slag`, unchanged). *Calibrated:* **nothing** — this study fits no
parameter; it only scores the existing model. The decision it informs (keep Healy unchanged, replace
the vague "over-predicts at high lime" flag with the measured bias map, leave the L_P leg
order-of-magnitude / benchmarked — *not* upgraded to "validated") is recorded in ADR 0007.

Run headless (prints the grading + the holdout verdict):

    python -m steel.demo_slag_lp_validation
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from .kinetics import ABS_ZERO
from .slag import Slag, phosphorus_partition

# --------------------------------------------------------------------------- #
# 0. Provenance
# --------------------------------------------------------------------------- #
HOLDOUT_SOURCE = ("P. B. Drain, B. J. Monaghan, R. J. Longbottom, M. W. Chapman, G. Zhang, S. J. Chew, "
                  "'Phosphorus Partition and Phosphate Capacity of Basic Oxygen Steelmaking Slags', "
                  "ISIJ International 58 (2018), No. 11, 1965–1971 (open access, CC BY-NC-ND); "
                  "docs/sources/drain_2018_phosphorus_partition_bos.pdf")
MODEL_UNDER_TEST = ("Healy 1970: log L_P = 22350/T + 0.08·%CaO + 2.5·log₁₀(%Fe_t) − 16 (T in K), "
                    "L_P = (%P)_slag / [%P]_metal")

# The mass fraction of phosphorus in P₂O₅ — the (%P₂O₅) → (%P) conversion the transcription guard uses.
# 2·M_P / M_P₂O₅ with M_P = 30.974, M_P₂O₅ = 141.943.
P_IN_P2O5 = (2.0 * 30.974) / 141.943

# The paper's prose-stated reproducibility of the seven R-series repeats (1650 °C) — the cross-check
# target for :func:`reproducibility_crosscheck` and the measurement scatter floor (~3.7 %).
REPRO_MEAN_LP = 190.0
REPRO_STD_LP = 7.0

# Rounding half-widths for the per-row L_P consistency bracket (last printed digit of each column).
_P2O5_ROUND = 0.05
_PMETAL_ROUND = 0.0005


# --------------------------------------------------------------------------- #
# 1. The measured points (transcribed from the open-access PDF Table 4 — NOT a figure)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DrainPoint:
    """One measured phosphorus-partition datum from Drain 2018 Table 4.

    Composition is the tabulated **mass %** (the unit :class:`steel.slag.Slag` reads directly — no
    mole-fraction reconstruction needed). ``feto`` is total iron reported as FeO (Table-4 footnote),
    which is exactly what :attr:`steel.slag.Slag.FeO` expects (``pct_Fe_total`` converts it to %Fe_t).
    ``p2o5`` (slag) and ``p_metal`` (``[%P]``) are carried so :func:`validate_lp_consistency` can
    recompute ``lp`` from them; ``lp`` is the tabulated measured partition ratio. ``series`` is the
    experiment family (R reproducibility / T temperature / B2–B5 basicity), ``T_K`` the temperature.
    """

    label: str          # experiment number
    series: str         # R / T / B2 / B4 / B5
    T_K: float
    CaO: float
    SiO2: float
    MgO: float
    Al2O3: float
    FetO: float         # total iron as FeO (mass %)
    MnO: float
    p2o5: float         # (%P₂O₅) in slag, mass %
    p_metal: float      # [%P] in metal, mass %
    lp: float           # measured L_P = (%P)/[%P]

    @property
    def log_lp(self) -> float:
        return math.log10(self.lp)

    @property
    def v_ratio(self) -> float:
        return self.CaO / self.SiO2 if self.SiO2 > 0.0 else math.inf


def _pt(label, series, T_C, mgo, al2o3, sio2, p2o5, cao, mno, feto, p_metal, lp):
    """Build a point from a Table-4 row (temperature given in °C, as printed)."""
    return DrainPoint(label, series, T_C + ABS_ZERO, cao, sio2, mgo, al2o3, feto, mno, p2o5, p_metal, lp)


# --- HOLDOUT: Drain 2018 Table 4 — 33 measured equilibrium heats ---------------------------------- #
# Columns as transcribed: (No., series, T °C, MgO, Al2O3, SiO2, P2O5, CaO, MnO, FetO, [P], L_P).
# TiO2 (≤0.1 %) is dropped — Healy does not read it and Slag has no TiO2 field. FetO = total Fe as FeO.
HOLDOUT: tuple = (
    _pt("1",  "R",  1650,  9.8, 0.4, 17.0, 1.4, 47.2, 0.9, 23.3, 0.003, 201),
    _pt("2",  "R",  1650, 12.4, 0.4, 16.5, 1.3, 45.7, 0.8, 22.9, 0.003, 194),
    _pt("3",  "R",  1650, 17.3, 0.3, 15.2, 1.3, 43.0, 0.8, 22.1, 0.003, 185),
    _pt("4",  "R",  1650, 11.0, 0.5, 17.7, 4.0, 47.8, 1.0, 18.0, 0.009, 193),
    _pt("5",  "R",  1650, 11.3, 0.6, 16.4, 3.9, 45.0, 1.1, 21.6, 0.009, 189),
    _pt("6",  "R",  1650, 11.8, 0.4, 16.2, 3.7, 46.2, 1.1, 20.6, 0.009, 178),
    _pt("7",  "R",  1650,  9.6, 0.4, 18.0, 3.8, 49.4, 1.1, 17.7, 0.009, 186),
    _pt("8",  "T",  1550, 10.6, 0.5, 17.8, 3.8, 49.9, 1.2, 16.2, 0.004, 378),
    _pt("9",  "T",  1600, 12.3, 0.5, 19.2, 4.6, 48.7, 1.0, 13.8, 0.011, 187),
    _pt("10", "T",  1700, 11.1, 0.4, 16.2, 3.9, 44.7, 1.1, 22.5, 0.013, 137),
    _pt("11", "B2", 1650, 12.2, 0.5, 25.4, 3.5, 46.1, 1.1, 11.1, 0.037,  42),
    _pt("12", "B2", 1650, 10.7, 0.5, 24.6, 3.7, 48.2, 1.0, 11.4, 0.029,  56),
    _pt("13", "B2", 1650, 12.4, 0.4, 25.1, 3.7, 46.6, 1.0, 10.9, 0.037,  43),
    _pt("14", "B2", 1650, 14.2, 0.4, 24.1, 3.4, 45.5, 1.1, 11.4, 0.022,  67),
    _pt("15", "B2", 1650, 12.9, 0.2, 21.8, 4.0, 46.3, 0.9, 13.9, 0.023,  76),
    _pt("16", "B2", 1650, 13.4, 0.3, 17.2, 2.7, 34.3, 0.9, 31.2, 0.015,  79),
    _pt("17", "B2", 1650, 10.9, 0.3, 18.2, 2.8, 36.8, 0.9, 30.1, 0.017,  73),
    _pt("18", "B4", 1650, 10.2, 0.3, 13.5, 3.4, 55.5, 1.1, 16.0, 0.004, 374),
    _pt("19", "B4", 1650, 10.2, 0.5, 13.2, 3.8, 51.6, 1.2, 19.6, 0.004, 411),
    _pt("20", "B4", 1650,  7.5, 0.1, 15.1, 2.9, 67.0, 0.9,  6.5, 0.007, 178),
    _pt("21", "B4", 1650,  7.3, 0.1, 15.4, 2.8, 66.5, 0.7,  7.1, 0.007, 176),
    _pt("22", "B4", 1650,  9.1, 0.1, 17.0, 2.6, 65.1, 0.8,  5.3, 0.013,  89),
    _pt("23", "B4", 1650,  9.4, 0.1, 15.4, 2.8, 61.9, 1.2,  9.3, 0.006, 201),
    _pt("24", "B4", 1650, 10.1, 0.3, 14.5, 3.3, 56.9, 1.0, 14.0, 0.004, 356),
    _pt("25", "B4", 1650, 12.9, 0.3, 13.1, 2.7, 54.8, 1.1, 15.2, 0.004, 298),
    _pt("26", "B4", 1650, 16.0, 0.4, 11.1, 3.3, 48.5, 1.2, 19.5, 0.005, 288),
    _pt("27", "B5", 1650,  7.4, 0.2, 13.0, 3.5, 64.4, 1.2, 10.3, 0.004, 381),
    _pt("28", "B5", 1650, 11.5, 0.3, 10.6, 3.7, 48.4, 1.2, 24.3, 0.004, 418),
    _pt("29", "B5", 1650, 10.3, 0.1, 12.9, 3.5, 62.1, 1.2,  9.9, 0.005, 303),
    _pt("30", "B5", 1650,  9.5, 0.2, 12.0, 2.9, 63.5, 1.1, 10.7, 0.003, 426),
    _pt("31", "B5", 1650, 10.6, 0.2, 12.5, 3.0, 61.0, 1.1, 11.6, 0.003, 438),
    _pt("32", "B5", 1650, 10.0, 0.2, 11.3, 3.0, 63.0, 1.2, 11.2, 0.003, 442),
    _pt("33", "B5", 1650, 10.8, 0.2, 12.4, 3.0, 60.4, 1.1, 12.1, 0.003, 435),
)

# The reproducibility set = the seven R-series repeats at 1650 °C (Drain §3.1, "mean 190, std 7").
REPRO_SERIES = tuple(p for p in HOLDOUT if p.series == "R")


# --------------------------------------------------------------------------- #
# 2. The transcription guards (di-crosscheck, both run in the suite)
# --------------------------------------------------------------------------- #
def validate_lp_consistency(points: tuple = HOLDOUT) -> list:
    """Recompute L_P from each row's ``(%P₂O₅)`` and ``[%P]`` and bracket the tabulated ``L_P``.

    ``L_P = (%P)/[%P]`` with ``(%P) = %P₂O₅ · 2·M_P/M_P₂O₅``. Propagating the last-digit rounding of
    **both** ``%P₂O₅`` (±0.05) and ``[%P]`` (±0.0005) gives a bracket the tabulated ``L_P`` must fall
    inside — a transcription typo in any of the three columns breaks it. Returns the offending
    ``(label, tabulated_lp, lo, hi)`` (empty = every row's three P columns are mutually consistent).
    """
    bad = []
    for p in points:
        lo = (p.p2o5 - _P2O5_ROUND) * P_IN_P2O5 / (p.p_metal + _PMETAL_ROUND)
        hi = (p.p2o5 + _P2O5_ROUND) * P_IN_P2O5 / max(p.p_metal - _PMETAL_ROUND, 1.0e-9)
        if not (lo <= p.lp <= hi):
            bad.append((p.label, p.lp, lo, hi))
    return bad


def reproducibility_crosscheck(rel_tol: float = 0.05) -> tuple:
    """Recompute the R-series mean & std L_P and cross-check the paper's prose-stated "190 ± 7".

    The seven R-series repeats are summarised in Drain §3.1 *outside* Table 4 (mean L_P 190, standard
    deviation 7). Reproducing that pair from the transcribed R rows cross-checks the ``L_P`` column
    against an independently-printed statistic (the analog of the C_S leg's Table-6↔Table-9 overlap),
    and fixes the ~3.7 % measurement scatter floor. Returns ``(mean, std, ok)`` — ``ok`` is True when
    both reproduce the printed values to ``rel_tol``.
    """
    lps = [p.lp for p in REPRO_SERIES]
    mean = statistics.mean(lps)
    std = statistics.stdev(lps)     # sample std, as the paper quotes
    ok = (abs(mean - REPRO_MEAN_LP) <= rel_tol * REPRO_MEAN_LP
          and abs(std - REPRO_STD_LP) <= max(rel_tol * REPRO_STD_LP, 1.0))
    return mean, std, ok


# --------------------------------------------------------------------------- #
# 3. The model under test — reconstruct the Slag and read slag.phosphorus_partition
# --------------------------------------------------------------------------- #
def slag_from_point(p: DrainPoint) -> Slag:
    """Reconstruct a :class:`steel.slag.Slag` (wt %) from a point — Healy reads %CaO, %Fe_t (from FeO), T.

    Drain tabulates mass %, the unit ``Slag`` takes directly. FetO (total iron as FeO) maps onto the
    ``FeO`` field, from which :attr:`~steel.slag.Slag.pct_Fe_total` recovers the ``%Fe_t`` Healy needs.
    Al₂O₃/MgO/MnO are carried for completeness though Healy's L_P ignores them (it reads only CaO,
    Fe_t and T) — that blindness to the rest of the slag is part of what the residual measures.
    """
    return Slag(CaO=p.CaO, SiO2=p.SiO2, FeO=p.FetO, Al2O3=p.Al2O3, MgO=p.MgO, MnO=p.MnO)


def predicted_lp(p: DrainPoint) -> float:
    """Model-predicted ``L_P`` for a point: :func:`steel.slag.phosphorus_partition` at its temperature."""
    return phosphorus_partition(slag_from_point(p), T_celsius=p.T_K - ABS_ZERO)


def predicted_log_lp(p: DrainPoint) -> float:
    return math.log10(predicted_lp(p))


# --------------------------------------------------------------------------- #
# 4. Grading (log-residual = bias + scatter; the basicity-dependence; the T-direction)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Residual:
    """One point's prediction vs measurement, in log₁₀ L_P (the natural metric — L_P spans a decade+)."""

    label: str
    series: str
    T_K: float
    CaO: float
    v_ratio: float
    FetO: float
    predicted: float                # log10 L_P, model
    measured: float                 # log10 L_P, experiment
    resid: float                    # predicted − measured (>0 ⇒ model over-predicts)


def residuals(points: tuple = HOLDOUT) -> list:
    """The per-point :class:`Residual` list (basicity / lime / FetO carried for the edge analyses)."""
    out = []
    for p in points:
        pred = predicted_log_lp(p)
        out.append(Residual(p.label, p.series, p.T_K, p.CaO, p.v_ratio, p.FetO,
                            pred, p.log_lp, pred - p.log_lp))
    return out


@dataclass(frozen=True)
class BiasScatter:
    """Pooled magnitude verdict: mean log-residual (bias) and its std (scatter), both as ``×`` factors."""

    n: int
    mean_log: float                 # mean(predicted − measured); ×10**this = systematic bias factor
    std_log: float                  # std of the residual; ×10**this = scatter factor


def bias_scatter(points: tuple = HOLDOUT) -> BiasScatter:
    """Pooled bias + scatter over ``points`` (ordering-free — the 'how far off, on average' number)."""
    rs = [r.resid for r in residuals(points)]
    return BiasScatter(len(rs), statistics.mean(rs), statistics.pstdev(rs))


# The series in ascending basicity — the spine of the headline (bias climbs along this axis).
_SERIES_ORDER = ("B2", "R", "T", "B4", "B5")


def per_series_bias(points: tuple = HOLDOUT) -> list:
    """Mean log-residual and mean basicity per experiment series, ascending in basicity.

    The headline lives here: grouping by series shows the bias is **not uniform** — it climbs
    monotonically from B2 (``v≈2``, near-exact) to B5 (``v≈5``, ~×2). Returns
    ``[(series, mean_v, mean_resid, n), …]`` in :data:`_SERIES_ORDER`.
    """
    groups: dict = {}
    for r in residuals(points):
        groups.setdefault(r.series, []).append(r)
    out = []
    for s in _SERIES_ORDER:
        rs = groups.get(s)
        if rs:
            out.append((s, statistics.mean([r.v_ratio for r in rs]),
                        statistics.mean([r.resid for r in rs]), len(rs)))
    return out


def bias_by_lime(points: tuple = HOLDOUT, low: float = 50.0, high: float = 55.0) -> dict:
    """Pooled bias for the low-lime (``%CaO < low``) vs high-lime (``%CaO ≥ high``) rows.

    The same finding read on the raw lime axis rather than the series label: Healy is close at low
    lime and over-predicts ~×2 at high lime, because its ``+0.08·%CaO`` term is linear where the real
    L_P saturates. Returns ``{"low": (mean_resid, n), "high": (mean_resid, n)}``.
    """
    rs = residuals(points)
    lo = [r.resid for r in rs if r.CaO < low]
    hi = [r.resid for r in rs if r.CaO >= high]
    return {"low": (statistics.mean(lo), len(lo)) if lo else (float("nan"), 0),
            "high": (statistics.mean(hi), len(hi)) if hi else (float("nan"), 0)}


@dataclass(frozen=True)
class TemperatureDirection:
    """The T-series (rows 8–10): does measured *and* modelled L_P fall with temperature? (confounded)."""

    temps: tuple                    # the experimental temperatures (K), ascending
    measured_lp: tuple              # measured L_P at each
    predicted_lp: tuple             # Healy L_P at each
    measured_falls: bool            # measured L_P monotonically decreasing in T
    predicted_falls: bool           # Healy L_P monotonically decreasing in T


def temperature_direction(points: tuple = HOLDOUT) -> TemperatureDirection:
    """Grade Healy's ``+22350/T`` direction against the dedicated T-series (1550 → 1700 °C).

    Uses the ``T`` series — the one family varied deliberately in temperature. Both measured and
    Healy L_P should **fall** with T (dephosphorization favoured cool). It is a *direction* check, not
    an isolated slope: the three points also co-vary in composition (FetO 16 → 22 %), so the magnitude
    is confounded and is reported as such, never as a second independent axis.
    """
    ts = sorted((p for p in points if p.series == "T"), key=lambda p: p.T_K)
    temps = tuple(p.T_K for p in ts)
    meas = tuple(p.lp for p in ts)
    pred = tuple(predicted_lp(p) for p in ts)
    falls = lambda xs: all(a > b for a, b in zip(xs, xs[1:]))
    return TemperatureDirection(temps, meas, pred, falls(meas), falls(pred))


# --------------------------------------------------------------------------- #
# 5. The assembled verdict
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Verdict:
    """Everything the demo / figure / tests read — computed from the data, asserted nowhere."""

    pooled: BiasScatter                 # over all 33 points
    per_series: list                    # (series, mean_v, mean_resid, n) ascending in basicity
    by_lime: dict                       # low-lime vs high-lime pooled bias
    temperature: TemperatureDirection   # the T-direction check
    repro_mean: float                   # R-series mean L_P (cross-checks the printed 190)
    repro_std: float                    # R-series std L_P (cross-checks the printed 7)
    lp_consistency_clean: bool          # every row's (P₂O₅, [P], L_P) columns are mutually consistent
    repro_clean: bool                   # the R-series mean/std reproduce the paper's prose "190 ± 7"


def summary() -> Verdict:
    """Assemble the full verdict (the single entry point the demo and tests consume)."""
    mean, std, repro_ok = reproducibility_crosscheck()
    return Verdict(
        pooled=bias_scatter(HOLDOUT),
        per_series=per_series_bias(HOLDOUT),
        by_lime=bias_by_lime(HOLDOUT),
        temperature=temperature_direction(HOLDOUT),
        repro_mean=mean,
        repro_std=std,
        lp_consistency_clean=(len(validate_lp_consistency()) == 0),
        repro_clean=repro_ok,
    )
