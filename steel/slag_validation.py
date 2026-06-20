"""Holdout validation of the cited C_S model against an INDEPENDENT measured dataset (front-end B3).

*Does the Sosinsky–Sommerville optical-basicity sulfide-capacity correlation predict C_S
out-of-sample — or is :mod:`steel.slag`'s "order-of-magnitude only" posture forced?* This module
is the **front-end twin of** :mod:`steel.cct_validation`: it grades a cited correlation the engine
already uses against measured data the correlation was **never fit to**, touches no engine, and
lets the data set the verdict. It reads :func:`steel.slag.sulfide_capacity`; nothing here feeds the
frozen pipeline.

THE CIRCULARITY GATE (why this dataset, and not any other). Sosinsky–Sommerville (1986) is a
**regression fit** — grading it against its own training data is the vacuous-benchmark trap the
project names ([[di-crosscheck-source]]). An honest holdout needs measured C_S from a source the
fit could not have seen. Two independence facts make :data:`HOLDOUT` clean:

1. **Temporal.** The points are Nzotta–Sichen–Seetharaman, *ISIJ International* **38 (1998)** 1170,
   Table 6 — measured **twelve years after** the 1986 correlation, by gas–slag equilibration in a
   different laboratory (KTH). They could not be in the 1986 fit.
2. **Parametric.** Table 6 is the **Al₂O₃–CaO–MgO–SiO₂** system: it contains **no MnO and no FeO**.
   :mod:`steel.slag`'s optical basicities for those two oxides are *themselves optimized from C_S
   data* (the named source-sensitive tier), so a MnO/FeO slag would test a fitted input. The four
   components here (CaO 1.00, SiO₂ 0.48, Al₂O₃ 0.605, MgO 0.78) carry **spectroscopic** Duffy–Ingram
   values fit to nothing in this chain. So the composite under test — Λ(spectroscopic) → S–S(1986) —
   has **zero parameters fit to these data**. A real holdout, not a benchmark.

The temperature range (1773–1923 K = 1500–1650 °C) sits **inside** S–S's stated validity
(1400–1700 °C), so any edge found is compositional, not an out-of-range temperature artifact.

THE TRANSCRIPTION GUARD (di-crosscheck, baked into the suite — and its scope). Every measured point
carries its raw repeat readings (:attr:`NzottaPoint.cs_repeats`); :func:`validate_transcription`
asserts the tabulated **C_S** average reproduces the mean of those repeats — a fat-fingered C_S digit
cannot silently corrupt the verdict. It guards the **C_S column only**. The composition and
temperature columns (which drive Λ and the prediction) are cross-checked separately and *partially*:
the **four** slags that appear in *both* Table 6 and the Table-9 literature comparison must agree on
composition **and** C_S (:func:`overlap_crosscheck`), confirming 4 of the 10 holdout rows end-to-end.
A composition typo outside those four (e.g. a mis-read MgO in the non-headline MnO tier) is **not**
caught — a named limit of the automated guard.

THE VERDICT THE DATA GIVES (computed, not asserted — see :func:`summary`):
  * **It CARRIES.** Table 6 is **four distinct basic compositions** (Q2/Q3/Q4/Q5, Λ ≳ 0.65), each
    measured at up to three temperatures (ten points). On those nine basic points the model is a
    **consistent ~×1.4 overprediction** (mean log-residual +0.16, std 0.07 → ×1.18) — and the
    consistency holds on *both* axes: each of the four compositions carries the *same* ~×1.4 bias
    (Q2 ≈ +0.20, Q3 ≈ +0.13, Q4 ≈ +0.14, Q5 ≈ +0.15), well inside the factor-2–3 inter-laboratory
    scatter the same paper documents (Abraham–Richardson run high, Kärsrud/Nzotta low). The
    **genuinely independent corroboration is the temperature slope**: a constant log-bias leaves the
    slope untouched, so the S–S ``(22690 − 54640·Λ)/T`` term is tested *on its own* when the repeated
    compositions (Q2, Q3 at three temperatures) reproduce the measured C_S(T) movement — ≈ +0.44
    predicted vs +0.47 measured per +100 K. (Within-temperature composition ranking is also exact,
    ρ = 1 at 1773 and 1873 K, but over only 3–4 closely-spaced slags with S–S monotonic in Λ — a
    supporting footnote, not the headline.) A *positive* out-of-sample result — it upgrades
    :mod:`steel.slag`'s C_S posture from "order-of-magnitude only" to "holdout-validated to ~×1.4
    with ×1.2 scatter, within the basic domain."
  * **Two named edges, flagged honestly.** (1) **The acidic edge — a single-point flag, not an
    established trend.** The one most-acidic slag tested (Q1, Λ ≈ 0.60 — high SiO₂, low CaO) flips
    sign and under-predicts **~×4**. The literature's lowest-Λ point (:data:`LITERATURE_1773`) also
    misses badly, *but* a near-identical-Λ neighbour (Λ ≈ 0.635) fits fine and the two differ ~7× in
    measured C_S at the *same* basicity — that is the dataset's internal scatter at low Λ, **not** a
    reproduced acidic trend. So the acidic edge rests on **Q1 alone**; it is reported as a flag to be
    confirmed (candidate causes: amphoteric Al₂O₃, whose Λ = 0.605 is genuinely uncertain, and/or
    S–S used at the high-alumina composition extreme), not as a law. (2) **The MnO edge.**
    :data:`MNO_DIAGNOSTIC` (Table 5, with MnO) over-predicts **~×5** — but it tests the model's
    *fitted* MnO Λ = 1.00 in the steep high-Λ regime, so it is a **weaker-independence** tier and is
    reported as a located weak link, not part of the headline.

CITED vs CALIBRATED. *Cited:* every measured number (Nzotta 1998 Tables 5/6/9; the literature it
compiles — Abraham–Richardson 1960, Kärsrud 1983/84, Kalyanram 1960) and the S–S correlation +
Duffy–Ingram Λ (both from :mod:`steel.slag`, unchanged). *Calibrated:* **nothing** — this study
fits no parameter; it only scores the existing model. The decision it informs (keep the model,
upgrade its documented posture, name the two edges) is recorded in ADR 0006.

Run headless (prints the grading + the holdout verdict):

    python -m steel.demo_slag_validation
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from .slag import Slag, _MOLAR_MASS, sulfide_capacity

# --------------------------------------------------------------------------- #
# 0. Provenance
# --------------------------------------------------------------------------- #
HOLDOUT_SOURCE = ("M. M. Nzotta, Du Sichen, S. Seetharaman, 'Sulphide Capacities in Some Multi "
                  "Component Slag Systems', ISIJ International 38 (1998), No. 11, 1170–1179 "
                  "(open access, CC BY-NC-ND); docs/sources/nzotta_1998_sulphide_capacities.pdf")
MODEL_UNDER_TEST = ("Sosinsky & Sommerville, Metall. Trans. B 17 (1986) 331: "
                    "log C_S = (22690 − 54640·Λ)/T + 43.6·Λ − 25.2, valid 1400–1700 °C")

# Internal-consistency tolerance for the transcription guard: the tabulated average must match the
# mean of the listed repeat readings to within this *relative* tolerance (rounding of the last digit
# in the printed averages — not a physics tolerance).
_AVG_REL_TOL = 0.02


# --------------------------------------------------------------------------- #
# 1. The measured points (transcribed from the open-access PDF tables — NOT the figures)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NzottaPoint:
    """One measured sulfide-capacity datum: composition (mole fractions), temperature, measured C_S.

    ``x`` is the slag composition as **mole fractions** of the oxides (the unit Nzotta tabulates;
    ``SiO2`` is filled to make the listed cations + SiO₂ sum to 1 where the table omits it).
    ``cs`` is the tabulated **average** sulfide capacity; ``cs_repeats`` are the individual repeat
    readings behind that average — the transcription guard (:func:`validate_transcription`) checks
    that ``cs`` reproduces their mean. ``T_K`` is the experimental temperature (K), ``label`` the
    sample id, ``source`` the originating study (for the literature-comparison set).
    """

    label: str
    T_K: float
    x: dict
    cs: float
    cs_repeats: tuple = ()
    source: str = "Nzotta 1998 (present work)"

    @property
    def log_cs(self) -> float:
        return math.log10(self.cs)


def _pt(label, T_K, xAl, xCa, xMg, cs, repeats=(), xMn=None, source="Nzotta 1998 (present work)"):
    """Build a point; SiO₂ mole fraction is the remainder after the listed cations (+ MnO if given)."""
    x = {"Al2O3": xAl, "CaO": xCa, "MgO": xMg}
    if xMn is not None:
        x["MnO"] = xMn
    x["SiO2"] = 1.0 - sum(x.values())
    return NzottaPoint(label, T_K, x, cs, tuple(repeats), source)


# --- HOLDOUT: Table 6, Al₂O₃–CaO–MgO–SiO₂, present work — the clean independent test ------- #
# No MnO / no FeO (dodges the model's fitted Λ); measured 1998 (post-dates the 1986 fit). 10 points.
HOLDOUT: tuple = (
    _pt("Q1", 1923, 0.118, 0.178, 0.224, 2.125e-4, (2.109e-4, 2.140e-4)),
    _pt("Q2", 1873, 0.096, 0.433, 0.151, 4.024e-4, (4.099e-4, 3.948e-4)),
    _pt("Q3", 1873, 0.049, 0.378, 0.145, 1.251e-4, (1.344e-4, 1.157e-4)),
    _pt("Q4", 1873, 0.068, 0.359, 0.214, 2.576e-4, (2.768e-4, 2.383e-4)),
    _pt("Q2", 1823, 0.096, 0.433, 0.151, 2.038e-4, (1.977e-4, 2.098e-4)),
    _pt("Q3", 1823, 0.049, 0.378, 0.145, 1.280e-4, (1.280e-4,)),
    _pt("Q5", 1773, 0.085, 0.404, 0.216, 1.819e-4, (1.757e-4, 1.882e-4)),
    _pt("Q2", 1773, 0.096, 0.433, 0.151, 1.357e-4, (1.357e-4,)),
    _pt("Q3", 1773, 0.049, 0.378, 0.145, 4.831e-5, (5.149e-5, 4.512e-5)),
    _pt("Q4", 1773, 0.068, 0.359, 0.214, 8.185e-5, (8.185e-5,)),
)

# --- LITERATURE_1773: Table 9, same system at 1773 K — CORROBORATION ONLY ------------------ #
# Same Al₂O₃–CaO–MgO–SiO₂ system, three other laboratories, all at 1773 K. Weaker independence: these
# are PRE-1986 and may sit inside the S–S training set, so they corroborate the trend (and the acidic
# edge), they are NOT a second holdout. Nzotta notes Abraham–Richardson run high vs the others.
LITERATURE_1773: tuple = (
    _pt("AR-1", 1773, 0.086, 0.448, 0.174, 5.43e-4, source="Abraham & Richardson 1960"),
    _pt("AR-2", 1773, 0.116, 0.457, 0.177, 6.85e-4, source="Abraham & Richardson 1960"),
    _pt("AR-3", 1773, 0.151, 0.492, 0.152, 6.92e-4, source="Abraham & Richardson 1960"),
    _pt("AR-4", 1773, 0.188, 0.637, 0.079, 3.97e-3, source="Abraham & Richardson 1960"),
    _pt("Ka-1", 1773, 0.071, 0.458, 0.074, 1.29e-4, source="Kärsrud 1983/84"),
    _pt("Ka-2", 1773, 0.068, 0.337, 0.213, 1.05e-4, source="Kärsrud 1983/84"),
    _pt("Ka-3", 1773, 0.069, 0.396, 0.145, 1.15e-4, source="Kärsrud 1983/84"),
    _pt("Ky-1", 1773, 0.077, 0.332, 0.150, 3.86e-5, source="Kalyanram et al. 1960"),
    _pt("Ky-2", 1773, 0.074, 0.390, 0.146, 1.68e-4, source="Kalyanram et al. 1960"),
    _pt("Ky-3", 1773, 0.071, 0.309, 0.214, 5.86e-5, source="Kalyanram et al. 1960"),
    _pt("Ky-4", 1773, 0.105, 0.318, 0.148, 2.70e-4, source="Kalyanram et al. 1960"),
)

# --- MNO_DIAGNOSTIC: Table 5, Al₂O₃–CaO–MgO–MnO, present work — WEAK-INDEPENDENCE tier ----- #
# Post-1986, but contains MnO, whose Λ = 1.00 in slag.py is fit-to-C_S. So this does NOT test purely
# independent inputs; it probes the model's MnO handling (its weakest link) in the steep high-Λ regime.
MNO_DIAGNOSTIC: tuple = (
    _pt("C1", 1923, 0.289, 0.556, 0.086, 3.867e-3, (3.570e-3, 4.164e-3), xMn=0.069),
    _pt("C2", 1923, 0.305, 0.557, 0.087, 2.382e-3, (2.739e-3, 2.025e-3), xMn=0.051),
    _pt("C3", 1923, 0.299, 0.538, 0.121, 2.983e-3, (2.952e-3, 3.013e-3), xMn=0.042),
    _pt("C4", 1923, 0.301, 0.550, 0.121, 2.196e-3, (2.280e-3, 2.111e-3), xMn=0.028),
    _pt("C1", 1873, 0.289, 0.556, 0.086, 2.853e-3, (2.950e-3, 2.756e-3), xMn=0.069),
    _pt("C2", 1873, 0.305, 0.557, 0.087, 2.469e-3, (2.499e-3, 2.438e-3), xMn=0.051),
    _pt("C3", 1873, 0.299, 0.538, 0.121, 2.232e-3, (2.306e-3, 2.157e-3), xMn=0.042),
    _pt("C4", 1873, 0.301, 0.550, 0.087, 1.912e-3, (1.948e-3, 1.875e-3), xMn=0.062),
)


# --------------------------------------------------------------------------- #
# 2. The transcription guard (di-crosscheck, runs in the suite)
# --------------------------------------------------------------------------- #
def validate_transcription(points=None) -> list:
    """Check the tabulated average C_S against the mean of the listed repeats for every point.

    The "verify an AI-extracted table against a direct read" guard ([[di-crosscheck-source]]): a
    transcription typo in a digit shifts the average away from the mean of the repeats it summarizes.
    Returns the list of offending ``(label, T_K, tabulated, mean_of_repeats)`` (empty = all clean);
    points with a single reading (no repeat to cross-check) are skipped.
    """
    points = HOLDOUT + MNO_DIAGNOSTIC if points is None else points
    bad = []
    for p in points:
        if len(p.cs_repeats) < 2:
            continue
        mean = statistics.mean(p.cs_repeats)
        if abs(mean - p.cs) > _AVG_REL_TOL * p.cs:
            bad.append((p.label, p.T_K, p.cs, mean))
    return bad


# The four present-work rows the source reproduces in BOTH Table 6 and the Table-9 literature
# comparison (at 1773 K) — an end-to-end transcription cross-check of composition AND C_S, the part
# the C_S-only :func:`validate_transcription` cannot reach. (X_Al2O3, X_CaO, X_MgO, C_S) as printed
# in Table 9; they must match the corresponding 1773 K HOLDOUT points to rounding.
_TABLE9_PRESENT_WORK = (
    (0.085, 0.404, 0.216, 1.82e-4),     # = Q5 / 1773
    (0.096, 0.433, 0.151, 1.36e-4),     # = Q2 / 1773
    (0.049, 0.378, 0.145, 4.83e-5),     # = Q3 / 1773
    (0.068, 0.359, 0.214, 8.19e-5),     # = Q4 / 1773
)


def overlap_crosscheck(rel_tol: float = 0.01) -> list:
    """Cross-check the 4 rows printed in both Table 6 and Table 9 — composition AND C_S agree.

    The guard :func:`validate_transcription` cannot see the composition columns; this closes part of
    that gap. For each Table-9 present-work row, find the 1773 K HOLDOUT point with the same
    (Al₂O₃, CaO, MgO) mole fractions and assert its tabulated C_S matches (to ``rel_tol``, the
    Table-9 rounding). Returns the list of mismatches (empty = the 4 overlap rows transcribe
    consistently across two independent printings).
    """
    bad = []
    h1773 = {(round(p.x["Al2O3"], 3), round(p.x["CaO"], 3), round(p.x["MgO"], 3)): p
             for p in HOLDOUT if p.T_K == 1773}
    for xAl, xCa, xMg, cs in _TABLE9_PRESENT_WORK:
        p = h1773.get((round(xAl, 3), round(xCa, 3), round(xMg, 3)))
        if p is None or abs(p.cs - cs) > rel_tol * cs:
            bad.append((xAl, xCa, xMg, cs, None if p is None else p.cs))
    return bad


def per_composition_bias(points: tuple = HOLDOUT) -> dict:
    """Mean log-residual for each distinct composition (the honest 'consistent on both axes' check).

    Groups the points by their (rounded) mole-fraction vector — so a composition measured at several
    temperatures is one group — and reports the mean over-prediction per composition. The basic
    Table-6 set resolves to four compositions (Q2/Q3/Q4/Q5), each carrying the same ~×1.4 bias; that
    per-composition consistency, not the raw point count, is what 'it carries' rests on.
    """
    groups: dict = {}
    for p in points:
        key = (p.label, round(p.x["Al2O3"], 3), round(p.x["CaO"], 3), round(p.x["MgO"], 3))
        groups.setdefault(key, []).append(predicted_log_cs(p) - p.log_cs)
    return {key[0]: statistics.mean(rs) for key, rs in groups.items()}


# --------------------------------------------------------------------------- #
# 3. The model under test — reconstruct the Slag and read slag.sulfide_capacity
# --------------------------------------------------------------------------- #
def slag_from_point(p: NzottaPoint) -> Slag:
    """Reconstruct a :class:`steel.slag.Slag` (wt %) from a point's mole fractions.

    :class:`~steel.slag.Slag` reads **wt %** and converts back to moles via the same molar masses
    used here (imported from :mod:`steel.slag` so the round-trip is exact). ``wt_i ∝ x_i · M_i``;
    the absolute normalization is irrelevant — both the optical basicity and the S–S correlation
    depend only on the *ratios*. So feeding the reconstructed wt % recovers exactly the mole-fraction
    composition Nzotta tabulated.
    """
    wt = {ox: x * _MOLAR_MASS[ox] for ox, x in p.x.items()}
    total = sum(wt.values())
    pct = {ox: 100.0 * w / total for ox, w in wt.items()}
    return Slag(CaO=pct.get("CaO", 0.0), SiO2=pct.get("SiO2", 0.0), Al2O3=pct.get("Al2O3", 0.0),
                MgO=pct.get("MgO", 0.0), MnO=pct.get("MnO", 0.0))


def predicted_log_cs(p: NzottaPoint) -> float:
    """Model-predicted ``log₁₀ C_S`` for a point: :func:`steel.slag.sulfide_capacity` at its temperature.

    The whole composite under test in one line — Duffy–Ingram Λ (in the ``Slag``) fed to the S–S
    correlation, evaluated at the measured temperature (K → °C for slag.py's interface).
    """
    return math.log10(sulfide_capacity(slag_from_point(p), T_celsius=p.T_K - 273.15))


# --------------------------------------------------------------------------- #
# 4. Grading (log-residual = bias + scatter; ranking within temperature; T-slope)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Residual:
    """One point's prediction vs measurement, in log₁₀ C_S (the natural metric — C_S spans decades)."""

    label: str
    T_K: float
    Lambda: float
    predicted: float                # log10 C_S, model
    measured: float                 # log10 C_S, experiment
    resid: float                    # predicted − measured (>0 ⇒ model over-predicts)


def residuals(points: tuple) -> list:
    """The per-point :class:`Residual` list for ``points`` (optical basicity carried for the edge analysis)."""
    out = []
    for p in points:
        pred = predicted_log_cs(p)
        out.append(Residual(p.label, p.T_K, slag_from_point(p).optical_basicity,
                            pred, p.log_cs, pred - p.log_cs))
    return out


@dataclass(frozen=True)
class BiasScatter:
    """Pooled magnitude verdict: mean log-residual (bias) and its std (scatter) over a point set.

    Both are reported as ``×`` factors (``10**value``). Ordering-free — this is the honest "does it
    carry" claim, the analog of :class:`steel.cct_validation.FactorGrade`'s ``log_resid_spread``,
    calibrated against the factor-2–3 inter-laboratory scatter the source itself documents.
    """

    n: int
    mean_log: float                 # mean(predicted − measured); ×10**this = systematic bias factor
    std_log: float                  # std of the residual; ×10**this = scatter factor
    excluded: tuple = ()            # labels held out of the pool (named edges), if any


def bias_scatter(points: tuple, exclude: tuple = ()) -> BiasScatter:
    """Pooled bias + scatter over ``points``, optionally excluding named labels (the acidic edge).

    Excluding a point is only honest when it is *named and explained* (here Q1, the acidic edge) —
    both the pooled-all and the pooled-minus-edge numbers are reported so nothing hides behind the
    exclusion, exactly as :mod:`steel.cct_validation` separates the bias-immune claim from the
    hypothesis-aware reads.
    """
    rs = [r.resid for r in residuals(points) if r.label not in exclude]
    return BiasScatter(len(rs), statistics.mean(rs), statistics.pstdev(rs), tuple(exclude))


def _spearman(xs: list, ys: list) -> float:
    """Spearman rank correlation ρ — Pearson on the ranks (no scipy needed for one number)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for rank, i in enumerate(order):
            r[i] = float(rank)
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def within_temperature_ranking(points: tuple = HOLDOUT) -> dict:
    """Spearman ρ of predicted vs measured log C_S **within each temperature** (composition skill).

    Pooling all temperatures into one ρ would inflate apparent skill via the temperature ordering
    (and "C_S rises with Λ" is baked into S–S — the vacuous claim). Ranking *within* a fixed
    temperature isolates the genuine cross-composition question, the faithful analog of
    :mod:`steel.cct_validation`'s fixed-700 °F cut. Returns ``{T_K: (rho, n)}`` for the temperatures
    with at least two points.
    """
    by_T: dict = {}
    for r in residuals(points):
        by_T.setdefault(r.T_K, []).append(r)
    out = {}
    for T, rs in sorted(by_T.items()):
        if len(rs) >= 2:
            out[T] = (_spearman([r.predicted for r in rs], [r.measured for r in rs]), len(rs))
    return out


@dataclass(frozen=True)
class TemperatureSlope:
    """A repeated composition's measured vs predicted temperature dependence of log C_S (per +100 K)."""

    label: str
    temps: tuple
    measured_slope: float           # Δ(log10 C_S)/Δ(100 K), least-squares over the repeats
    predicted_slope: float


def temperature_slopes(points: tuple = HOLDOUT) -> list:
    """For each composition measured at ≥ 2 temperatures, the measured vs model log-C_S slope (per 100 K).

    The independent *second* axis of the validation: the S–S temperature term (22690 − 54640·Λ)/T
    is graded against how the same slag's measured C_S actually moves with temperature — using the
    repeated compositions (Q2, Q3 each at three temperatures; Q4 at two). A composition is keyed by
    its rounded mole-fraction vector, not its sample id, so identical compositions group correctly.
    """
    groups: dict = {}
    for p in points:
        key = (round(p.x["Al2O3"], 3), round(p.x["CaO"], 3), round(p.x["MgO"], 3))
        groups.setdefault(key, []).append(p)

    def slope(temps, vals):
        # least-squares slope of vals vs T, expressed per +100 K
        n = len(temps)
        mt, mv = statistics.mean(temps), statistics.mean(vals)
        den = sum((t - mt) ** 2 for t in temps)
        return 100.0 * sum((t - mt) * (v - mv) for t, v in zip(temps, vals)) / den if den else float("nan")

    out = []
    for pts in groups.values():
        if len({p.T_K for p in pts}) < 2:
            continue
        pts = sorted(pts, key=lambda p: p.T_K)
        temps = [p.T_K for p in pts]
        out.append(TemperatureSlope(
            pts[0].label, tuple(temps),
            slope(temps, [p.log_cs for p in pts]),
            slope(temps, [predicted_log_cs(p) for p in pts]),
        ))
    return out


def acidic_edge(points: tuple = HOLDOUT) -> Residual:
    """The lowest-optical-basicity point and its residual — the named acidic edge (S–S used acid-side)."""
    return min(residuals(points), key=lambda r: r.Lambda)


# --------------------------------------------------------------------------- #
# 5. The assembled verdict
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Verdict:
    """Everything the demo / figure / tests read — computed from the data, asserted nowhere."""

    holdout_all: BiasScatter            # pooled over all 10 Table-6 points
    holdout_basic: BiasScatter          # pooled excluding the named acidic edge (Q1)
    edge: Residual                      # the acidic edge point (lowest Λ)
    ranking: dict                       # within-temperature Spearman {T: (rho, n)}
    slopes: list                        # repeated-composition temperature slopes
    literature: BiasScatter             # corroboration set (weaker independence)
    mno: BiasScatter                    # MnO weak-link tier (weakest independence)
    per_composition: dict               # mean bias per distinct basic composition (consistency on both axes)
    transcription_clean: bool           # the C_S-column di-crosscheck guard passed
    overlap_clean: bool                 # the 4 Table-6↔Table-9 composition+C_S overlap rows agree


def summary() -> Verdict:
    """Assemble the full verdict (the single entry point the demo and tests consume)."""
    edge = acidic_edge(HOLDOUT)
    return Verdict(
        holdout_all=bias_scatter(HOLDOUT),
        holdout_basic=bias_scatter(HOLDOUT, exclude=(edge.label,)),
        edge=edge,
        ranking=within_temperature_ranking(HOLDOUT),
        slopes=temperature_slopes(HOLDOUT),
        literature=bias_scatter(LITERATURE_1773),
        mno=bias_scatter(MNO_DIAGNOSTIC),
        per_composition=per_composition_bias(HOLDOUT),
        transcription_clean=(len(validate_transcription()) == 0),
        overlap_clean=(len(overlap_crosscheck()) == 0),
    )
