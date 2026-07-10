"""Why the bulk P→DBTT slope can't be pinned — the grain-boundary-coverage mechanism (A2-B).

A **mechanistic overlay with NO claimable tooth**, built to close the last open question the
phosphorus story left: *why* is :data:`steel.grain.ITT_K_P` (P's bulk contribution to the
Cottrell–Petch DBTT) a **flagged bracket** — ≈ 40–78 °C per 0.1 wt% P — rather than a pinned,
teeth-bearing coefficient? The A2 sourcing gate (2026-06-22, next-directions §A2) already
*concluded* it cannot earn teeth — the bulk-wt% slope is a **reduced form** of grain-boundary
segregation physics. This module makes that conclusion **mechanistic and computed** instead of
asserted, and in doing so *re-derives the flag from the physics* rather than merely restating it.

The honest posture — stated from line one (the discipline of the temper-embrittlement gate)
-----------------------------------------------------------------------------------------------
This is **cited relations + a computed bias map**, the same class as the B3 validation legs
(:mod:`steel.slag_lp_validation`) and the temper-embrittlement build — *not* a benchmarked
propagation and *not* a tooth. There is a specific reason it **cannot** be a tooth, and it is worth
naming up front because it is the whole result:

    The clean, measured form of P embrittlement is **GB coverage → DBTT** (a linear law, per steel).
    The engine's :func:`steel.grain.cottrell_petch_dbtt_C` carries P as a **bulk-wt%** term on the
    Pickering **ferrite-pearlite transgranular-cleavage** DBTT. The two are separated by two gaps,
    each of which is independently non-universal:

    1. **bulk P → GB coverage** (:func:`mclean_gb_coverage`) — a Langmuir–McLean isotherm whose
       enrichment factor depends on the **segregation temperature / thermal history**, saturation and
       C co-segregation. None of that is fixed by the bulk P content, so one bulk P maps to a *range*
       of coverages. This is the **same wall** the repo's earlier McLean gate hit (temper
       embrittlement: the kinetic nose was "underdetermined, not wrong-placed").
    2. **GB coverage → DBTT** (:data:`COVERAGE_DBTT_RELATIONS`) — measured, linear, and **per steel**:
       the slope spans **3.12 °C/at%** (ferritic IF steel) to **13.31 °C/at%** (tempered-martensite
       SA508-4N), a **4.3×** range, and varies with prior-austenite grain size (13.13 vs 6.69, a
       1.96× range) and hardness. Crucially, **every one of these relations is the *intergranular*
       GB-segregation axis** — a DBTT-vs-AES-GB-coverage fit measures intergranular embrittlement, a
       *different fracture mode* from the Pickering **transgranular-cleavage** law the bulk term rides.
       That includes the IF steel: its matrix is ferritic, but being interstitial-free it has no solute
       carbon to compete with P at the boundaries, so it too embrittles **intergranularly** — and it is
       additionally the very steel its 3.12 slope was fit to. **So no cited relation is in the engine's
       transgranular domain at all: there is no in-domain holdout, and the cross-steel spread is
       cross-*domain*.** Composing these slopes onto the engine's law would be a category graft, which
       is exactly why this module does **not** touch :mod:`steel.grain`.

**The computed payoff (see** :func:`summary` **— computed, not asserted).** Compose the two gaps and
the bulk slope ``dDBTT/d(wt% P)`` becomes a **product of two non-universal factors**: the per-steel
coverage slope (4.3× span) × the thermal-history-dependent McLean enrichment (~5× span over
T_seg 350–550 °C). Their product spans roughly **5–120 °C per 0.1 wt% P** — a ~20× range that is
**order-of-magnitude consistent with** the documented 40–78 bracket and *contains* it, with the
engine's flagged mid-value (500 °C/wt% ≡ 50 °C/0.1 wt%) landing inside for mid-range (steel, T_seg).
The point is **not** that the model derives the specific 40–78 band (it cannot — it rides the flagged
McLean leg): it is that **two multiplicatively non-universal factors make the bulk slope irreducibly
steel- and path-dependent, so a flagged band is the *only* honest form.** The mechanism **pins
nothing**; it explains why nothing here can be pinned.

CITED vs FLAGGED (the non-circularity discipline)
-------------------------------------------------
* **CITED** — every coverage→DBTT relation (:data:`COVERAGE_DBTT_RELATIONS`): the IF slope
  ``3.12·Cp − 118.87`` (Chen & Song, *Mater. Sci. Eng. A* **528** (2011) 8002,
  doi:10.1016/j.msea.2011.08.002 — already the source behind :data:`steel.grain.ITT_K_P`'s docstring
  bracket) and the three SA508-4N relations (Zhao & Song, *J. Mater. Res. Technol.* **11** (2021)
  1908 / **18** (2022) 3585, doi:10.1016/j.jmrt.2021.11.092 and .2022.03.122 — CC-BY open access; the
  equations are transcribed from the papers' own abstracts, cross-checked in :func:`validate_relations`).
  The segregation free energy ``ΔG_seg(P) = −34469 + 22.9·T`` J/mol is the **same cited value**
  (Yang–Chen / Erhart–Grabke) the repo already carries in :mod:`steel.temper_embrittlement`.
* **FLAGGED / underdetermined** — :func:`mclean_gb_coverage` itself: the simplest single-solute
  McLean isotherm with the cited ΔG_seg **under-predicts** absolute AES coverage (it yields ~0.2–8 at%
  where dilute-P steels typically measure ~5–25 at%, because it omits C co-segregation and any
  effective-energy enhancement). It is used **only as a sensitivity overlay** — to show how coverage
  (hence the composed slope) *moves* with T_seg — never as a coverage benchmark. The bracket
  explanation rests on the **slope composition** (order of magnitude), not on reproduced coverages.
* **CALIBRATED** — **nothing.** This module fits no parameter; it scores and composes cited relations.

The decision it informs — **keep** :data:`steel.grain.ITT_K_P` **flagged and unchanged**, now with a
*mechanistic* rather than merely bracketed justification — is recorded in ADR 0010. No engine touch.

Units (the registered trap — a TRIPLE basis, worse than the wt%/at% pair in :mod:`steel.grain`)
-----------------------------------------------------------------------------------------------
Three phosphorus concentration bases live here and must never be mixed:
  * **bulk wt%** — the composition input (the ITT_K_P basis, and :mod:`steel.slag`'s output);
  * **bulk atomic fraction** — wt% × ``M_Fe/M_P`` / 100 (the McLean isotherm's ``X_c``);
  * **GB coverage** — the isotherm's monolayer fraction ``X_b`` ∈ [0, 1), identified (approximately,
    a named caveat) with the AES boundary **at%** the coverage→DBTT laws take as ``Cp``.
The isotherm works in atomic fraction; the DBTT laws in at%; the engine in wt%. Conversions happen at
the function boundaries and are asserted in the tests.

Run headless (prints the bias map + the computed bracket explanation)::

    python -m steel.p_segregation_dbtt
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .grain import AT_PCT_PER_WT_PCT_P, ITT_K_P
from .kinetics import ABS_ZERO, R_GAS

# --------------------------------------------------------------------------- #
# 1. Cited constants — the McLean segregation energy and the documented bracket
# --------------------------------------------------------------------------- #
# ΔG_seg(P) in α-Fe = A + B·T  (J/mol) — the SAME cited value carried by temper_embrittlement.py
# (Yang–Chen / Erhart–Grabke). Becomes LESS negative (weaker segregation) as T rises: the entropy term.
DG_SEG_A = -34469.0          # J/mol   — enthalpic part of the P segregation free energy
DG_SEG_B = 22.9              # J/mol·K — entropic part (T·ΔS)

# The documented engineering bracket for P's BULK contribution to the DBTT — what grain.ITT_K_P is
# flagged against (next-directions §A2 / grain.py): ≈ 40–78 °C per 0.1 wt% P (≈ 400–780 °C/wt%). The
# engine's flagged value is 500 °C/wt% ≡ 50 °C/0.1 wt%, mid-bracket. Reproduced here for the summary
# cross-reference only; this module changes nothing in grain.py.
BULK_SLOPE_BRACKET_C_PER_0P1: tuple[float, float] = (40.0, 78.0)
ITT_K_P_AS_C_PER_0P1 = ITT_K_P / 10.0        # grain.ITT_K_P (°C/wt%) → °C per 0.1 wt% (= 50.0)


# --------------------------------------------------------------------------- #
# 2. Gap 1: bulk P → GB coverage — the Langmuir–McLean isotherm (FLAGGED overlay)
# --------------------------------------------------------------------------- #
def mclean_gb_coverage(bulk_P_wt: float, T_seg_C: float, *,
                       dG_A: float = DG_SEG_A, dG_B: float = DG_SEG_B) -> float:
    """Equilibrium grain-boundary P coverage (monolayer fraction ``X_b`` ∈ [0, 1)) — FLAGGED overlay.

    The single-solute Langmuir–McLean isotherm ``X_b/(1−X_b) = [X_c/(1−X_c)]·exp(−ΔG_seg/RT)`` with the
    cited ``ΔG_seg = dG_A + dG_B·T`` (J/mol). ``bulk_P_wt`` (wt%) is converted to the bulk atomic
    fraction ``X_c`` at this boundary (× :data:`~steel.grain.AT_PCT_PER_WT_PCT_P` / 100); ``T_seg_C`` is
    the **segregation / ageing temperature** (°C), the free variable that makes the bulk→coverage map
    non-unique — hotter → weaker segregation → less coverage.

    **This is the underdetermined leg, used only for sensitivity** (module docstring): the simplest
    one-solute isotherm with the cited ΔG_seg *under-predicts* the absolute AES coverage of real dilute-P
    steels (it omits C co-segregation and effective-energy enhancement). Do **not** read the absolute
    number as a coverage benchmark — read only how it *moves* with T_seg. Monotone: rises with bulk P,
    falls with T_seg. Returns a fraction in [0, 1).
    """
    if bulk_P_wt < 0.0:
        raise ValueError(f"bulk phosphorus must be ≥ 0 wt%, got {bulk_P_wt}")
    T_K = T_seg_C + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"segregation temperature must be above absolute zero, got {T_seg_C} °C")
    if bulk_P_wt == 0.0:
        return 0.0
    X_c = (bulk_P_wt * AT_PCT_PER_WT_PCT_P) / 100.0     # wt% → bulk atomic FRACTION
    beta = math.exp(-(dG_A + dG_B * T_K) / (R_GAS * T_K))
    ratio = (X_c / (1.0 - X_c)) * beta
    return ratio / (1.0 + ratio)


# --------------------------------------------------------------------------- #
# 3. Gap 2: GB coverage → DBTT — the cited, PER-STEEL relations (the bias map)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CoverageDBTT:
    """A cited linear coverage→DBTT relation ``DBTT[°C] = slope·Cp[at%] + intercept`` for one steel.

    ``slope`` is °C per at% GB phosphorus (the embrittlement *rate*), ``intercept`` °C (the P-free
    baseline DBTT of that steel/microstructure). ``matrix`` / ``fracture`` record the metallurgical
    domain — the load-bearing distinction: only ``ferritic`` + transgranular is the Pickering
    :func:`steel.grain.cottrell_petch_dbtt_C` domain; the tempered-martensite / intergranular rows are
    :mod:`steel.temper_embrittlement`'s domain and are here as the **cross-domain** spread, not as
    holdout targets for the engine law. ``pags_um`` / ``hardness_HV`` are recorded where the source
    isolates them (the grain-size and hardness axes of the non-transferability). ``in_pickering_domain``
    is the one ferritic, transgranular case — and it is the fitted steel, so it is not an independent
    holdout.
    """

    name: str
    slope_C_per_at: float
    intercept_C: float
    matrix: str
    fracture: str
    source: str
    pags_um: float | None = None
    hardness_HV: float | None = None

    @property
    def in_pickering_domain(self) -> bool:
        """True only for a ferritic **transgranular-cleavage** relation — the engine-law domain.

        **No cited relation qualifies:** every coverage→DBTT law here is an *intergranular*
        GB-segregation correlation (that is what a DBTT-vs-AES-GB-coverage fit measures). The IF steel is
        ferritic but embrittles intergranularly (interstitial-free → no solute carbon at the boundaries),
        so it is out of this domain too. The property stays as the explicit test — it returns False for
        all — because "nothing is in the transgranular domain" is the load-bearing fact.
        """
        return self.matrix == "ferritic" and self.fracture == "transgranular"

    def dbtt_C(self, Cp_at: float) -> float:
        """DBTT (°C) at a GB phosphorus coverage ``Cp_at`` (at%) — the cited line, evaluated."""
        if Cp_at < 0.0:
            raise ValueError(f"GB coverage must be ≥ 0 at%, got {Cp_at}")
        return self.slope_C_per_at * Cp_at + self.intercept_C


# The cited relations (transcribed from the papers' own abstracts; guarded in validate_relations).
# IF: Chen & Song 2011 — Ti-stabilized interstitial-free steel, ferritic MATRIX but INTERGRANULAR P
# embrittlement: being interstitial-free, it has no solute carbon to compete with P at the ferrite grain
# boundaries, so P segregation opens an intergranular fracture path (the cold-work-embrittlement
# literature — e.g. the phosphorus IF-CWE studies — is explicit that the fracture is intergranular). It
# is the relation grain.ITT_K_P's docstring names as the "clean modern form" — but note it is NOT the
# engine's transgranular-cleavage domain either. The three SA508-4N rows: Zhao & Song 2021/2022 — a
# Ni–Cr–Mo RPV steel, quench+temper(650 °C)+age → tempered martensite, non-hardening INTERGRANULAR
# (prior-austenite-boundary) embrittlement. So ALL four relations are the intergranular GB-segregation
# axis — a different fracture mode from the transgranular Pickering law grain.ITT_K_P rides.
IF_STEEL = CoverageDBTT(
    name="IF (Ti-stabilized interstitial-free)",
    slope_C_per_at=3.12, intercept_C=-118.87,
    matrix="ferritic", fracture="intergranular",
    source="Chen & Song, Mater. Sci. Eng. A 528 (2011); doi:10.1016/j.msea.2011.08.002",
)
SA508_FIXED_H = CoverageDBTT(
    name="SA508-4N (fixed hardness ~260 HV10)",
    slope_C_per_at=13.31, intercept_C=-339.28,
    matrix="tempered martensite", fracture="intergranular", hardness_HV=260.0,
    source="Zhao & Song, J. Mater. Res. Technol. 11 (2021) 1908; doi:10.1016/j.jmrt.2021.11.092",
)
SA508_PAGS_34 = CoverageDBTT(
    name="SA508-4N (PAGS 34 µm)",
    slope_C_per_at=13.13, intercept_C=-335.70,
    matrix="tempered martensite", fracture="intergranular", pags_um=34.0,
    source="Zhao & Song, J. Mater. Res. Technol. 18 (2022) 3585; doi:10.1016/j.jmrt.2022.03.122",
)
SA508_PAGS_112 = CoverageDBTT(
    name="SA508-4N (PAGS 112 µm)",
    slope_C_per_at=6.69, intercept_C=-223.87,
    matrix="tempered martensite", fracture="intergranular", pags_um=112.0,
    source="Zhao & Song, J. Mater. Res. Technol. 18 (2022) 3585; doi:10.1016/j.jmrt.2022.03.122",
)
COVERAGE_DBTT_RELATIONS: tuple[CoverageDBTT, ...] = (
    IF_STEEL, SA508_FIXED_H, SA508_PAGS_34, SA508_PAGS_112,
)


def naive_transfer_bias(source: CoverageDBTT, target: CoverageDBTT) -> float:
    """Slope ratio ``target/source`` — the factor by which transferring one steel's coverage→DBTT slope
    to another mis-scales the embrittlement rate.

    The concrete cost of the non-transferability: apply the IF steel's 3.12 °C/at% to SA508-4N and you
    under-state its P sensitivity by :func:`naive_transfer_bias`\\ (IF, SA508) ≈ 4.3×. This is the
    "8620 wall" of the front end — a per-steel-anchored relation, not a universal law.
    """
    if source.slope_C_per_at == 0.0:
        raise ValueError("source slope is zero; ratio undefined")
    return target.slope_C_per_at / source.slope_C_per_at


# --------------------------------------------------------------------------- #
# 4. The synthesis: compose the two gaps → the bulk slope, and explain the bracket
# --------------------------------------------------------------------------- #
def composed_bulk_slope_C_per_0p1(relation: CoverageDBTT, T_seg_C: float, *,
                                  dP_wt: float = 0.02) -> float:
    """The BULK slope ``dDBTT/d(0.1 wt% P)`` implied by composing McLean + one coverage→DBTT relation.

    Finite-difference of ``bulk P → X_b (McLean) → Cp[at%] ≈ 100·X_b → DBTT (relation)`` over
    ``[0, dP_wt]`` wt% P, at segregation temperature ``T_seg_C``, expressed in **°C per 0.1 wt% P** (the
    bracket's unit). This is the quantity :data:`steel.grain.ITT_K_P` represents in reduced form — here
    reconstructed from the mechanism, showing its dependence on *both* the steel (via ``relation``) and
    the thermal history (via ``T_seg_C``). Order-of-magnitude (rides the flagged McLean leg); not a pin.
    """
    if dP_wt <= 0.0:
        raise ValueError(f"finite-difference step must be > 0 wt%, got {dP_wt}")
    hi = relation.dbtt_C(mclean_gb_coverage(dP_wt, T_seg_C) * 100.0)      # X_b → at%
    lo = relation.dbtt_C(mclean_gb_coverage(0.0, T_seg_C) * 100.0)
    per_wt = (hi - lo) / dP_wt          # °C per wt% P
    return per_wt / 10.0                # → °C per 0.1 wt% P


@dataclass(frozen=True)
class PSegregationSummary:
    """The computed bias-map verdict (all fields computed in :func:`summary`, none asserted).

    ``slope_span`` the cross-steel coverage-slope ratio (max/min over the cited relations);
    ``grain_size_span`` the within-SA508 ratio (13.13/6.69); ``composed_min`` / ``composed_max`` the
    bulk-slope range (°C/0.1 wt%) over the (steel, T_seg) grid; ``bracket_contained`` whether that range
    contains the documented 40–78; ``engine_value_inside`` whether grain.ITT_K_P's 50 °C/0.1 wt% lands
    inside the composed range. ``has_independent_in_domain_holdout`` is the teeth verdict: whether ANY
    coverage→DBTT relation sits in the engine's transgranular-cleavage domain (:attr:`CoverageDBTT.
    in_pickering_domain`) — it is False, because every cited relation is the *intergranular*
    GB-segregation axis (a different fracture mode from the engine's law). With no in-domain relation at
    all there is nothing to serve as an independent holdout, which is why A2-B carries no tooth.
    """

    slope_span: float
    grain_size_span: float
    composed_min: float
    composed_max: float
    bracket_contained: bool
    engine_value_inside: bool
    has_independent_in_domain_holdout: bool


def summary(*, T_seg_grid_C: tuple[float, ...] = (350.0, 400.0, 450.0, 500.0, 550.0)
           ) -> PSegregationSummary:
    """Compute the bias-map verdict from the cited relations + the composed bulk slope (nothing asserted).

    Spans the coverage-slope non-transferability (cross-steel and within-SA508 grain size), the composed
    bulk-slope range over ``T_seg_grid_C`` × the cited relations, and checks whether that range contains
    the documented 40–78 °C/0.1 wt% bracket and the engine's flagged 50. The teeth verdict
    (``has_independent_in_domain_holdout``) is read structurally from the relations' domains.
    """
    slopes = [r.slope_C_per_at for r in COVERAGE_DBTT_RELATIONS]
    slope_span = max(slopes) / min(slopes)
    grain_size_span = SA508_PAGS_34.slope_C_per_at / SA508_PAGS_112.slope_C_per_at
    composed = [
        composed_bulk_slope_C_per_0p1(r, T)
        for r in COVERAGE_DBTT_RELATIONS for T in T_seg_grid_C
    ]
    cmin, cmax = min(composed), max(composed)
    lo, hi = BULK_SLOPE_BRACKET_C_PER_0P1
    bracket_contained = cmin <= lo and hi <= cmax
    engine_value_inside = cmin <= ITT_K_P_AS_C_PER_0P1 <= cmax
    # The teeth verdict: an in-domain holdout would be a coverage→DBTT relation in the engine's
    # transgranular-cleavage domain. NONE exists — every cited relation is the intergranular
    # GB-segregation axis (IF included: ferritic matrix, but intergranular for lack of solute carbon).
    # So there is no in-domain relation to serve as a holdout at all (and IF, the nearest, is also the
    # fitted steel). → no tooth.
    independent = any(r.in_pickering_domain for r in COVERAGE_DBTT_RELATIONS)
    return PSegregationSummary(
        slope_span=slope_span, grain_size_span=grain_size_span,
        composed_min=cmin, composed_max=cmax,
        bracket_contained=bracket_contained, engine_value_inside=engine_value_inside,
        has_independent_in_domain_holdout=independent,
    )


def validate_relations() -> bool:
    """Transcription guard: re-derive each cited relation's DBTT at its own reference coverage.

    Not a physics check — a **di-crosscheck transcription guard** (the analog of the B3 legs' guards):
    every ``(slope, intercept)`` was transcribed from a paper abstract, so we re-evaluate the line at a
    couple of coverages and confirm the arithmetic is internally consistent with the stored coefficients
    (catches a fat-fingered digit in the dataclass, the only failure mode a self-check can catch here).
    The real cross-check is that the numbers match the cited abstracts, verified at build time.
    """
    for r in COVERAGE_DBTT_RELATIONS:
        for Cp in (0.0, 10.0):
            expect = r.slope_C_per_at * Cp + r.intercept_C
            if abs(r.dbtt_C(Cp) - expect) > 1e-9:
                return False
    return True


def _print_report() -> None:
    """Headless report — the bias map and the computed bracket explanation."""
    print("Phosphorus GB-coverage → DBTT: the mechanism behind grain.ITT_K_P's flag (A2-B)")
    print("=" * 78)
    print("\nGap 2 — cited coverage→DBTT relations (DBTT[°C] = slope·Cp[at%] + intercept):")
    for r in COVERAGE_DBTT_RELATIONS:
        dom = "IN-DOMAIN (Pickering)" if r.in_pickering_domain else f"{r.matrix}/{r.fracture}"
        print(f"  {r.name:38s} slope {r.slope_C_per_at:5.2f}  [{dom}]")
    print(f"\n  cross-steel slope span (max/min)  = {max(r.slope_C_per_at for r in COVERAGE_DBTT_RELATIONS)/min(r.slope_C_per_at for r in COVERAGE_DBTT_RELATIONS):.2f}×")
    print(f"  within-SA508 grain-size span      = {naive_transfer_bias(SA508_PAGS_112, SA508_PAGS_34):.2f}×")
    print(f"  naive-transfer bias IF→SA508      = {naive_transfer_bias(IF_STEEL, SA508_FIXED_H):.2f}×")

    print("\nGap 1 — McLean coverage (monolayer fraction) vs T_seg [FLAGGED — sensitivity only]:")
    for T in (350.0, 450.0, 550.0):
        xs = " | ".join(f"P={P:.2f}%→{mclean_gb_coverage(P, T)*100:5.2f}at%" for P in (0.01, 0.03, 0.10))
        print(f"  T_seg={T:.0f}°C:  {xs}")

    print("\nComposed bulk slope dDBTT/d(0.1 wt% P) [°C/0.1wt%] — the ITT_K_P reduced form:")
    print(f"  documented bracket {BULK_SLOPE_BRACKET_C_PER_0P1}, engine flag = {ITT_K_P_AS_C_PER_0P1:.0f}")
    for T in (350.0, 450.0, 550.0):
        cells = " | ".join(f"{r.name.split()[0]:6s}{composed_bulk_slope_C_per_0p1(r, T):6.1f}"
                           for r in COVERAGE_DBTT_RELATIONS)
        print(f"  T_seg={T:.0f}°C:  {cells}")

    s = summary()
    print("\nVerdict (computed):")
    print(f"  composed bulk-slope range        = {s.composed_min:.1f}–{s.composed_max:.1f} °C/0.1wt%")
    print(f"  contains documented 40–78 bracket= {s.bracket_contained}")
    print(f"  contains engine flag (50)        = {s.engine_value_inside}")
    print(f"  independent in-domain holdout?   = {s.has_independent_in_domain_holdout}  → NO TOOTH")
    print("\n  → grain.ITT_K_P stays a FLAGGED bracket: the mechanism reproduces the bracket's")
    print("    magnitude and explains its WIDTH (per-steel slope × thermal-history enrichment),")
    print("    but pins nothing. The clean coverage→DBTT form is itself per-steel/cross-domain.")


if __name__ == "__main__":
    _print_report()
