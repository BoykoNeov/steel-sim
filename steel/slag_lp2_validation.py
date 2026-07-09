"""Second-slag-system holdout of the cited Healy L_P model (front-end B3, phosphorus leg #2).

*Does Healy's 1970 phosphorus-partition correlation carry to a slag **system** beyond Drain's BOS —
and what does it miss?* This is the **second independent slag system** left open by
:mod:`steel.slag_lp_validation` (the Drain leg / ADR 0007, whose one weakness was resting on a single
CaO–SiO₂–MgO–FetO BOS family). It grades the same cited correlation
(:func:`steel.slag.phosphorus_partition`) against a *different laboratory, different decade,
genuinely different oxide system*, at the **same converter temperature** so temperature is not a
confound. It touches no engine and fits nothing; nothing here feeds the frozen pipeline.

WHY A NEW SYSTEM AT CONVERTER T (the trap this leg was built to avoid). The obvious "different
systems" with open, tabulated L_P data are **hot-metal dephosphorization** sets (e.g. Zhou 2017, Im
1996) measured at ~1573 K against **carbon-saturated** iron. Those were assessed and **rejected**:
at 1300 °C — ~300 K below the converter fit — Healy's unbounded ``22350/T`` term alone over-predicts
by ×200–500, so they measure a temperature extrapolation, not slag-system generalization (and the
C-saturated metal is a second confound). A clean second-system test must hold temperature and metal
chemistry fixed and vary only the **slag**.

THE HOLDOUT. :data:`HOLDOUT` is Suito & Inoue, *Transactions ISIJ* **24** (1984) 47, Tables 1 & 2 —
23 measured equilibrium heats of **liquid low-carbon iron** against **CaO–MgO_sat–FeO_x–SiO₂ slags
carrying a foreign basic flux**: 12 with **BaO ≈ 4 %** (Table 1) and 11 with **Na₂O 7–13 %**
(Table 2), all at **1550 °C = 1823 K** (open access CC BY-NC-ND →
``docs/sources/suito_inoue_1984_naba_phosphorus_partition.pdf``). Independence is on three axes:

1. **Temporal** — measured 1984, fourteen years after the 1970 correlation, a different laboratory
   (Tohoku). It cannot be in Healy's fit. (And independent of the Drain leg's 2018 data.)
2. **Parametric** — Healy reads only ``%CaO``, total slag iron ``%Fe_t`` and ``T`` with fixed 1970
   coefficients and **no optical basicity**, so no fitted input is in the loop.
3. **System** — the slag carries **Na₂O / BaO**, basic fluxes **absent from Drain's BOS system** (and
   from Healy's fit). Since Healy's basicity term is ``%CaO`` **alone**, these slags test whether that
   single-oxide basicity generalizes when *another* basic oxide does part of the dephosphorization.

The metal is **liquid and low-carbon, not hot metal**: the source tabulates dissolved ``[%O] ≈
0.085–0.19 %`` (850–1900 ppm) alongside ``[%P]``, an oxidizing FeO_x system that precludes carbon
saturation — the exact confound the rejected hot-metal sets had. The temperature (1823 K) sits in
Drain's own 1550–1700 °C window, so this is genuinely a *same-conditions, different-slag* test.

THE TRANSCRIPTION GUARDS (di-crosscheck; the table is a printed image transcribed from the rendered
PDF, so guards are load-bearing — the Nzotta / Im pattern). Suito & Inoue tabulate **no** L_P or k_P
column (unlike Drain's three-column P redundancy), so the guard is built against the paper's *own*
published fit:

* :func:`validate_kp_consistency` — the paper's Eq. (3) is a fit for the equilibrium quotient
  ``log k_P = log[(%P₂O₅)/([%P]²(%Fe_tO)⁵)] = 0.145·[(%CaO)+0.3(%MgO)−0.5(%P₂O₅)+c·(%flux)] +
  22810/T − 20.506`` (``c`` = 1.2 for Na₂O, 0.9 for BaO — the CaO-equivalencies the paper derives).
  Recomputing ``log k_P`` from the transcribed FeO/Fe₂O₃/P₂O₅/[%P] columns and checking it against
  Eq. (3) from the CaO/MgO/flux columns is a **multi-column** cross-check (a fat-fingered digit in any
  of seven columns breaks it), with the paper's Fig. 1 scatter as the tolerance. The ``(%Fe_tO)⁵``
  leverage makes it very sensitive to [%P] (squared) and P₂O₅ typos. **Named limit:** at the
  extreme-composition edge (near-zero-CaO / FeO-saturated rows 809/810, max-Na₂O row 712) the paper's
  *own* linear-basicity fit deviates ~0.6–1.0 (visible in Fig. 1), so the guard is coarse there — it
  catches gross transcription errors, not last-digit slips at the fit edge.
* :func:`validate_oxide_sum` — every row's seven oxide columns sum to 100 ± 2 mass % (the slags are
  MgO-saturated with minor un-tabulated components), a blunt catch for a dropped/duplicated column.

THE VERDICT THE DATA GIVES — an independent confirmation **plus** a signed new edge (computed, not
asserted — see :func:`summary`):

  * **BaO leg — Healy carries, independently confirming the Drain result.** On the 12 BaO slags (a
    minor 4 % flux) Healy over-predicts a **consistent ≈ ×1.56** (scatter ×1.6), and its high-basicity
    rows run highest (805, ``v≈2`` → ×2) — the *same* mild high-lime over-prediction the Drain leg
    measured (≈ ×1.48 pooled, ×2 high-lime), now reproduced by a **different lab, different decade,
    different slag system, at converter temperature**. That is the second-system generalization
    result: Healy's ~×1.5 posture is not an artifact of Drain's one BOS family.
  * **Na₂O leg — a named non-CaO-basicity edge, the signed opposite of the high-lime bias.** On the 11
    Na₂O slags Healy **under-predicts**, because soda is a strong base Healy is blind to. The robust,
    per-row read (each point's own CaO *and* Fe_t are inside its Healy prediction) is the **pooled
    under-prediction, ≈ ×0.30**, and the **Na₂O residual sitting ~0.5–0.7 below the BaO series across
    the whole lime range** (the figure's right panel). The two tables' pooled residuals differ by
    ≈ 0.72 (BaO +0.19 vs Na₂O −0.53), and the matched-CaO window (``%CaO ≈ 15–22``,
    :func:`matched_cao_contrast`) gives a consistent gap ≈ 0.69 — so the soda under-prediction relative
    to baryta is **~×5**, robust across both reads. (Within Table 2, Na₂O and CaO are anti-correlated —
    the flux replaces lime — so the *within-table* gradient is CaO-confounded and is **not** used; the
    between-table reads isolate the flux.) This is **order-consistent** with the paper's own 1.2×/0.9×
    CaO-equivalencies for Na₂O/BaO (≈ 0.7 log units on Healy's 0.08 term,
    :func:`na2o_equivalency_expectation`) — but reported as *same-paper, order-of-magnitude*
    corroboration, **not** a precise match: the small matched-CaO window is **not also Fe_t-matched**
    (BaO ~40 % vs Na₂O ~33 % Fe_t ≈ 0.17 log of Healy's Fe_t term), so the exact factor is uncertain and
    the 0.69 ≈ 0.67 coincidence should not be over-read.

CITED vs CALIBRATED. *Cited:* every measured number (Suito & Inoue 1984 Tables 1 & 2), the Healy
correlation + coefficients (from :mod:`steel.slag`, unchanged), and the paper's Eq. (3) used only as a
transcription cross-check. *Calibrated:* **nothing** — this study fits no parameter; it scores the
existing model. The decision it informs (keep Healy unchanged; record that the Drain ~×1.5 posture
generalizes to a second system, and add the non-CaO-basicity edge to the bias map — a *scientific*
extension, since the engine's slags carry no soda/baryta flux) is recorded in ADR 0008.

NOTE — this is the paper's *data*, not its model. ADR 0007 rejected grading Healy against Suito &
Inoue's *correlation* (Eq. 3 is a fit, so that would compare models). Here their **measured heats** are
the holdout, exactly as Drain's measured heats were; Eq. (3) is used only as a transcription guard.

Run headless (prints the grading + the verdict):

    python -m steel.demo_slag_lp2_validation
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
HOLDOUT_SOURCE = ("H. Suito, R. Inoue, 'Effects of Na2O and BaO Additions on Phosphorus Distribution "
                  "between CaO-MgO-FetO-SiO2 Slags and Liquid Iron', Transactions ISIJ 24 (1984), No. 1, "
                  "47-53 (open access, CC BY-NC-ND); docs/sources/suito_inoue_1984_naba_phosphorus_partition.pdf")
MODEL_UNDER_TEST = ("Healy 1970: log L_P = 22350/T + 0.08·%CaO + 2.5·log₁₀(%Fe_t) − 16 (T in K), "
                    "L_P = (%P)_slag / [%P]_metal — reads %CaO alone for basicity (blind to Na2O/BaO/MgO)")

# The mass fraction of phosphorus in P₂O₅ — the (%P₂O₅) → (%P) conversion for the measured L_P.
# 2·M_P / M_P₂O₅ with M_P = 30.974, M_P₂O₅ = 141.943.
P_IN_P2O5 = (2.0 * 30.974) / 141.943

# Fe₂O₃ (mass %) → FeO-equivalent (mass %): 1 mol Fe₂O₃ = 2 mol FeO. 2·M_FeO / M_Fe₂O₃.
FEO_PER_FE2O3 = (2.0 * 71.844) / 159.688      # ≈ 0.900

# Suito & Inoue Eq. (3): log k_P = 0.145·[(%CaO)+0.3(%MgO)−0.5(%P₂O₅)+c·%flux] + 22810/T − 20.506,
# k_P = (%P₂O₅)/([%P]²(%Fe_tO)⁵). The CaO-equivalency c: Na₂O 1.2, BaO 0.9 (Fig. 1 / the paper's text).
KP_BASE = 0.145
KP_T = 22810.0
KP_CONST = -20.506
FLUX_EQUIV = {"Na2O": 1.2, "BaO": 0.9}

# Tolerances (transcription, NOT physics): the Eq. (3) cross-check passes at the paper's Fig. 1 scatter
# (a gross-error catcher — see the module docstring's named coarseness at the fit edge), and each row's
# oxide columns sum to 100 within the minor-component budget.
_KP_TOL = 1.05
_SUM_TOL = 2.0


# --------------------------------------------------------------------------- #
# 1. The measured points (transcribed from the rendered open-access PDF, Tables 1 & 2 — NOT figures)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SuitoPoint:
    """One measured phosphorus-partition datum from Suito & Inoue 1984 Table 1 (BaO) or 2 (Na₂O).

    Composition is the tabulated **mass %**. ``FeO`` / ``Fe2O3`` are carried separately (both the
    ``%Fe_t`` Healy needs and the ``%Fe_tO`` the k_P guard needs are derived from them). ``flux`` names
    the foreign basic oxide (``"BaO"`` / ``"Na2O"``) and ``flux_pct`` its content. ``p_metal`` (``[%P]``)
    and ``o_metal`` (``[%O]``) are the metal analyses; ``p2o5`` the slag phosphate. The measured L_P is
    **computed** ((%P)/[%P] from ``p2o5``/``p_metal``) — the source tabulates no L_P column, so the k_P
    guard cross-checks the columns against the paper's Eq. (3) instead.
    """

    label: int
    flux: str
    T_K: float
    FeO: float
    Fe2O3: float
    CaO: float
    MgO: float
    SiO2: float
    p2o5: float
    flux_pct: float
    p_metal: float      # [%P] in metal, mass %
    o_metal: float      # [%O] in metal, mass % (evidence of the oxidizing, low-C metal — not read by Healy)

    @property
    def feto_total(self) -> float:
        """Total iron as FeO (mass %) = FeO + 0.9·Fe₂O₃ — feeds Slag.FeO (Healy's %Fe_t) and k_P."""
        return self.FeO + FEO_PER_FE2O3 * self.Fe2O3

    @property
    def lp(self) -> float:
        """Measured L_P = (%P)_slag / [%P]_metal, with (%P) = %P₂O₅ · 2·M_P/M_P₂O₅ (Healy's definition)."""
        return (self.p2o5 * P_IN_P2O5) / self.p_metal

    @property
    def log_lp(self) -> float:
        return math.log10(self.lp)

    @property
    def v_ratio(self) -> float:
        return self.CaO / self.SiO2 if self.SiO2 > 0.0 else math.inf


def _pt(label, flux, FeO, Fe2O3, CaO, MgO, SiO2, p2o5, flux_pct, p_metal, o_metal, T_C=1550.0):
    """Build a point from a Table 1/2 row (temperature 1550 °C for the whole dataset)."""
    return SuitoPoint(label, flux, T_C + ABS_ZERO, FeO, Fe2O3, CaO, MgO, SiO2, p2o5, flux_pct, p_metal, o_metal)


# --- Table 1: CaO–MgO_sat–FeO_x–SiO₂–BaO (BaO ≈ 4 %), 1550 °C -------------------------------------- #
# Columns as transcribed: (No., [P], [O], FeO, Fe2O3, CaO, MgO, SiO2, P2O5, BaO).
HOLDOUT_BAO: tuple = (
    _pt(801, "BaO", 21.68, 2.20, 27.12, 14.20, 29.42, 0.726, 3.98, 0.0084, 0.0996),
    _pt(802, "BaO", 33.14, 2.79, 19.02, 14.84, 24.77, 0.707, 4.19, 0.0109, 0.1130),
    _pt(803, "BaO", 28.95, 4.69, 30.05, 9.30, 21.96, 0.858, 4.12, 0.0036, 0.1121),
    _pt(804, "BaO", 41.99, 4.89, 20.30, 9.83, 17.42, 0.783, 4.16, 0.0067, 0.1153),
    _pt(805, "BaO", 38.22, 6.98, 29.21, 6.23, 14.14, 0.803, 4.14, 0.0026, 0.1201),
    _pt(806, "BaO", 44.64, 10.44, 24.61, 5.80, 9.29, 0.817, 4.06, 0.0032, 0.1250),
    _pt(807, "BaO", 58.06, 7.29, 12.78, 7.06, 9.32, 0.758, 4.26, 0.0128, 0.1404),
    _pt(808, "BaO", 60.65, 12.18, 16.26, 5.10, 0.50, 0.854, 3.72, 0.0067, 0.1260),
    _pt(809, "BaO", 80.14, 8.38, 0.19, 6.02, 0.59, 0.309, 3.40, 0.103, 0.1876),
    _pt(810, "BaO", 68.95, 5.72, 0.19, 12.15, 8.24, 0.409, 3.57, 0.0858, 0.1690),
    _pt(811, "BaO", 58.25, 4.39, 0.29, 17.81, 15.11, 0.422, 3.83, 0.0687, 0.1463),
    _pt(812, "BaO", 45.92, 5.82, 18.99, 8.85, 15.18, 0.801, 3.99, 0.0074, 0.1259),
)

# --- Table 2: CaO–MgO_sat–FeO_x–SiO₂–Na₂O (Na₂O 7–13 %), 1550 °C ----------------------------------- #
HOLDOUT_NA2O: tuple = (
    _pt(701, "Na2O", 23.56, 4.23, 25.61, 10.05, 28.10, 0.764, 8.82, 0.0039, 0.0851),
    _pt(702, "Na2O", 29.08, 4.46, 18.38, 10.30, 26.60, 1.27, 11.2, 0.0063, 0.0934),
    _pt(703, "Na2O", 26.21, 5.53, 29.86, 6.93, 22.15, 1.40, 8.37, 0.0040, 0.0900),
    _pt(705, "Na2O", 38.93, 8.56, 26.93, 5.07, 13.02, 0.800, 7.24, 0.0016, 0.1025),
    _pt(706, "Na2O", 35.16, 6.73, 17.28, 8.50, 21.67, 0.963, 10.5, 0.0037, 0.1116),
    _pt(707, "Na2O", 42.26, 5.92, 9.61, 9.45, 21.38, 1.01, 11.5, 0.0063, 0.1252),
    _pt(709, "Na2O", 32.23, 7.23, 28.30, 6.26, 17.82, 0.856, 7.99, 0.0016, 0.1043),
    _pt(710, "Na2O", 37.65, 7.42, 20.83, 6.69, 17.05, 1.15, 9.48, 0.0031, 0.1190),
    _pt(711, "Na2O", 43.83, 8.21, 13.03, 6.66, 16.23, 0.761, 10.9, 0.0026, 0.1214),
    _pt(712, "Na2O", 49.88, 8.05, 6.65, 6.38, 15.11, 0.753, 12.8, 0.0033, 0.1289),
    _pt(713, "Na2O", 45.36, 8.99, 16.52, 5.28, 12.47, 0.764, 11.0, 0.0016, 0.1242),
)

HOLDOUT: tuple = HOLDOUT_BAO + HOLDOUT_NA2O


# --------------------------------------------------------------------------- #
# 2. The transcription guards (di-crosscheck, both run in the suite)
# --------------------------------------------------------------------------- #
def _observed_log_kp(p: SuitoPoint) -> float:
    """Observed log₁₀ k_P = log₁₀[(%P₂O₅)/([%P]²(%Fe_tO)⁵)] from the transcribed columns."""
    return math.log10(p.p2o5 / (p.p_metal ** 2 * p.feto_total ** 5))


def _eq3_log_kp(p: SuitoPoint) -> float:
    """Suito & Inoue Eq. (3) prediction of log₁₀ k_P from the CaO/MgO/P₂O₅/flux columns + T."""
    B = p.CaO + 0.3 * p.MgO - 0.5 * p.p2o5 + FLUX_EQUIV[p.flux] * p.flux_pct
    return KP_BASE * B + KP_T / p.T_K + KP_CONST


def validate_kp_consistency(points: tuple = HOLDOUT, tol: float = _KP_TOL) -> list:
    """Cross-check each row's observed log k_P against the paper's Eq. (3) (a multi-column guard).

    ``log k_P = log[(%P₂O₅)/([%P]²(%Fe_tO)⁵)]`` recomputed from FeO/Fe₂O₃/P₂O₅/[%P] must match Eq. (3)
    computed from CaO/MgO/P₂O₅/flux to within ``tol`` (the paper's Fig. 1 fit scatter). Ties seven
    columns together; the ``(%Fe_tO)⁵`` leverage makes it sharp on [%P]/P₂O₅ typos. Returns the
    offending ``(label, observed, eq3, diff)`` (empty = all rows mutually consistent). Coarse at the
    extreme-composition fit edge (809/810/712), a named limit — a gross-error catcher, not last-digit.
    """
    bad = []
    for p in points:
        obs, eq3 = _observed_log_kp(p), _eq3_log_kp(p)
        if abs(obs - eq3) > tol:
            bad.append((p.label, obs, eq3, obs - eq3))
    return bad


def validate_oxide_sum(points: tuple = HOLDOUT, tol: float = _SUM_TOL) -> list:
    """Check every row's seven oxide columns sum to 100 ± ``tol`` mass % (a dropped-column catch).

    The slags are MgO-saturated with minor un-tabulated components, so the sum sits at 100 ± ~1.3.
    Returns the offending ``(label, sum)`` (empty = all rows within budget).
    """
    bad = []
    for p in points:
        s = p.FeO + p.Fe2O3 + p.CaO + p.MgO + p.SiO2 + p.p2o5 + p.flux_pct
        if abs(s - 100.0) > tol:
            bad.append((p.label, s))
    return bad


# --------------------------------------------------------------------------- #
# 3. The model under test — reconstruct the Slag and read slag.phosphorus_partition
# --------------------------------------------------------------------------- #
def slag_from_point(p: SuitoPoint) -> Slag:
    """Reconstruct a :class:`steel.slag.Slag` (wt %) — Healy reads %CaO, %Fe_t (from FeO), T.

    ``feto_total`` (total iron as FeO) maps onto ``Slag.FeO`` so ``pct_Fe_total`` recovers Healy's
    ``%Fe_t``. CaO/SiO₂/MgO are carried; Na₂O and BaO have **no Slag field** — Healy cannot read them,
    and that blindness is exactly what this leg measures.
    """
    return Slag(CaO=p.CaO, SiO2=p.SiO2, FeO=p.feto_total, MgO=p.MgO)


def predicted_lp(p: SuitoPoint) -> float:
    """Model-predicted L_P: :func:`steel.slag.phosphorus_partition` of the reconstructed slag at its T."""
    return phosphorus_partition(slag_from_point(p), T_celsius=p.T_K - ABS_ZERO)


def predicted_log_lp(p: SuitoPoint) -> float:
    return math.log10(predicted_lp(p))


# --------------------------------------------------------------------------- #
# 4. Grading (log-residual = bias + scatter; per-flux; the matched-CaO Na₂O contrast)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Residual:
    """One point's prediction vs measurement in log₁₀ L_P (the natural metric — L_P spans a decade+)."""

    label: int
    flux: str
    T_K: float
    CaO: float
    v_ratio: float
    flux_pct: float
    predicted: float                # log10 L_P, model
    measured: float                 # log10 L_P, experiment
    resid: float                    # predicted − measured (>0 ⇒ model over-predicts)


def residuals(points: tuple = HOLDOUT) -> list:
    """The per-point :class:`Residual` list (flux / CaO carried for the per-flux + contrast analyses)."""
    out = []
    for p in points:
        pred = predicted_log_lp(p)
        out.append(Residual(p.label, p.flux, p.T_K, p.CaO, p.v_ratio, p.flux_pct,
                            pred, p.log_lp, pred - p.log_lp))
    return out


@dataclass(frozen=True)
class BiasScatter:
    """Pooled magnitude verdict: mean log-residual (bias) and its std (scatter), both as ``×`` factors."""

    n: int
    mean_log: float                 # mean(predicted − measured); ×10**this = systematic bias factor
    std_log: float                  # std of the residual; ×10**this = scatter factor


def bias_scatter(points: tuple) -> BiasScatter:
    """Pooled bias + scatter over ``points`` (the 'how far off, on average' number)."""
    rs = [r.resid for r in residuals(points)]
    return BiasScatter(len(rs), statistics.mean(rs), statistics.pstdev(rs))


# The CaO window that both tables populate — where the Na₂O effect is read at matched lime.
_CONTRAST_CAO_LO = 15.0
_CONTRAST_CAO_HI = 22.0


@dataclass(frozen=True)
class MatchedCaOContrast:
    """The CaO-isolated Na₂O tooth: BaO vs Na₂O mean bias in a fixed ``%CaO`` window, and their gap.

    Within Table 2, Na₂O and CaO are anti-correlated (flux replaces lime), so the within-table gradient
    is CaO-confounded. Comparing the two tables **at matched CaO** differences Healy's ``0.08·%CaO`` term
    out — Healy predicts the same L_P for both at a given CaO (it reads neither flux) — so the gap is the
    extra dephosphorization the soda gives over baryta, which Healy cannot see. **Caveat:** the small
    window is matched on CaO but **not on Fe_t** (the BaO rows average ~40 % vs the Na₂O rows ~33 %, a
    ~0.17 log difference in Healy's Fe_t term), so read the gap as ~×5 order-of-magnitude, not a precise
    factor — the full-range pooled per-table difference (≈ 0.72) is the robustness cross-check.
    """

    cao_lo: float
    cao_hi: float
    bao_mean: float                 # mean log-residual, BaO rows in the window
    na2o_mean: float                # mean log-residual, Na₂O rows in the window
    n_bao: int
    n_na2o: int

    @property
    def gap(self) -> float:
        """BaO − Na₂O mean log-residual: >0 ⇒ Na₂O dephosphorizes more than Healy expects at that CaO."""
        return self.bao_mean - self.na2o_mean


def matched_cao_contrast(cao_lo: float = _CONTRAST_CAO_LO, cao_hi: float = _CONTRAST_CAO_HI) -> MatchedCaOContrast:
    """The matched-CaO BaO-vs-Na₂O contrast (the CaO-isolated non-CaO-basicity tooth)."""
    bao = [r.resid for r in residuals(HOLDOUT_BAO) if cao_lo <= r.CaO <= cao_hi]
    na = [r.resid for r in residuals(HOLDOUT_NA2O) if cao_lo <= r.CaO <= cao_hi]
    return MatchedCaOContrast(cao_lo, cao_hi, statistics.mean(bao), statistics.mean(na),
                              len(bao), len(na))


def na2o_equivalency_expectation() -> float:
    """The gap the paper's own 1.2×/0.9× CaO-equivalency predicts (same-paper corroboration, log units).

    Mean Na₂O rows carry ≈ 1.2·%Na₂O CaO-equivalent extra basicity Healy ignores; mean BaO rows carry
    ≈ 0.9·%BaO. The difference × Healy's 0.08 %CaO slope is what the matched-CaO gap should be if soda
    behaved like the lime Healy can see (≈ 0.7 log). Reported as *order-of-magnitude, same-paper*
    corroboration of the ~×5 soda under-prediction — **not** a precise match (the measured gap is not
    Fe_t-matched; see :func:`matched_cao_contrast`), and never fit.
    """
    na_equiv = statistics.mean(FLUX_EQUIV["Na2O"] * p.flux_pct for p in HOLDOUT_NA2O)
    bao_equiv = statistics.mean(FLUX_EQUIV["BaO"] * p.flux_pct for p in HOLDOUT_BAO)
    return 0.08 * (na_equiv - bao_equiv)


# --------------------------------------------------------------------------- #
# 5. The assembled verdict
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Verdict:
    """Everything the demo / figure / tests read — computed from the data, asserted nowhere."""

    bao: BiasScatter                    # the 12 BaO slags — the "Healy carries / confirms Drain" leg
    na2o: BiasScatter                   # the 11 Na₂O slags — under-predicts (Healy blind to soda)
    contrast: MatchedCaOContrast        # the CaO-isolated Na₂O tooth
    equiv_expectation: float            # same-paper CaO-equivalency corroboration of the gap
    kp_consistency_clean: bool          # the Eq. (3) multi-column transcription guard passed
    oxide_sum_clean: bool               # every row's oxides sum to 100 ± 2


def summary() -> Verdict:
    """Assemble the full verdict (the single entry point the demo and tests consume)."""
    return Verdict(
        bao=bias_scatter(HOLDOUT_BAO),
        na2o=bias_scatter(HOLDOUT_NA2O),
        contrast=matched_cao_contrast(),
        equiv_expectation=na2o_equivalency_expectation(),
        kp_consistency_clean=(len(validate_kp_consistency()) == 0),
        oxide_sum_clean=(len(validate_oxide_sum()) == 0),
    )
