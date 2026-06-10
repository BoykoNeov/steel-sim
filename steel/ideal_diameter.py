"""The ideal-critical-diameter (D_I) cross-check — the measured-Jominy validation leg (Steel Phase 6c).

Phases 2a–2c built the Jominy chain (thermal fin → alloy C-curve shift → microstructure → hardness)
and 6a added the proeutectoid-ferrite reaction. Every calibration in that chain was anchored to its
*own* data: the thermal curve to the published distance↔cooling-rate equivalence (2a), the alloy
shift's **magnitude** to 4140's TTT nose (2b ``HARDENABILITY_SCALE``), each constituent hardness to
an independent dataset (2c). What was never directly checked is whether the *combination* predicts
the right **absolute depth of hardening** — and that is exactly what the **critical diameter**
measures: the diameter of a round bar that is 50 % martensite at its centre. (The **ideal** critical
diameter ``D_I`` is the infinitely-severe-quench, ``H → ∞``, limit; this module reports the
directly-tabulated **water-quench centre-equivalent** ``D_c`` — a defensible lower bound on ``D_I``,
see §1's "what this reports" note.) This module computes ``D_c`` *from the finished model* and
compares it to **independently measured** hardenability data — the "available, not required" triad
leg the 2c/3c docstrings flagged, now built.

Why this is a genuine (non-circular) cross-check — the teeth caveat (advisor)
----------------------------------------------------------------------------
The model's hardenability rides the **Grossmann alloy multiplying factors** — but only their
*relative* element potencies, raised to a magnitude calibrated against a **TTT nose**, never against
``D_I`` (:mod:`kinetics` §4 is explicit: "Grossmann's own magnitude lives in ideal-critical-*diameter*
space, which already convolves the thermal physics the fin solver models directly; using it for
*scale* would double-count"). So a **Grossmann-computed** ``D_I`` (base ``D_I`` × multiplying factors)
would be a tautology. The benchmark here is therefore **measured** Jominy hardenability — real
end-quench heats — *not* a Grossmann calculation. The model never saw these numbers.

The standard method, used both ways with the *same* conversion (so its error cancels)
-------------------------------------------------------------------------------------
``D_c`` is obtained from an end-quench curve the textbook way: find the Jominy distance ``J50`` at
which the steel is **50 % martensite**, then read the diameter off the empirical end-quench↔round-bar
equal-hardness equivalence (**EMJ Reference Book p.29**, centre-of-round, water quench). Applying that
one conversion *identically* to the model curve and the measured band means **the chart's absolute
accuracy is irrelevant** — its error cancels in the comparison; the discrimination lives in where
``J50`` falls (advisor). The two sides locate ``J50`` by the two valid readings of "50 % martensite":

* **Model side** — directly from the predicted **martensite fraction** ``fM = 0.5`` (:mod:`pathint`/
  :func:`properties.jominy_hardness`). This isolates *hardenability* (the depth of martensite) from
  the 2c hardness map — the cleaner headline, and the quantity 6c actually tests.
* **Measured side** — from hardness, because hardness is all an end-quench band reports: the Jominy
  distance where the band crosses the **cited 50 %-martensite hardness** for that carbon
  (:func:`fifty_percent_martensite_HRC`, SAE J406 Table A5 / Hodge–Orehoski). Using a *cited* criterion
  — not the model's own rule-of-mixtures 50/50 blend — keeps the benchmark independent (the model must
  not grade its own benchmark).

What the comparison shows (the honest result — read the *shape*, not "within X %")
---------------------------------------------------------------------------------
Run against four grades whose roles are deliberate (the circularity audit):

* **4140 = the calibration anchor** — ``HARDENABILITY_SCALE`` was set to its nose, so a match here is
  **by construction, not teeth**. It lands inside the (wide) measured 4140H band.
* **4340 + 8620 = the clean teeth** — neither touched the calibration; they bracket the deep
  (Ni-Cr-Mo, ~0.4 %C) and shallow (carburizing core, 0.2 %C) ends.
* **1045 = the documented edge** — its model knee runs ~2–3 mm deep (the 2b/6a A₁/ferrite story),
  so it rides high; reported, never tuned.

Three findings, in order of strength:

1. **The hardenability *ranking* is correct** — model ``D_c``: 1045 < 8620 < 4140 < 4340. That a
   0.2 %C carburizing steel out-hardens a 0.45 %C plain one (alloy beats carbon) emerges from the
   cited potencies. This is the headline (an H-band is a wide composition-spread envelope, so merely
   landing "in band" is weak teeth).
2. **4340 is under-predicted** — the model puts it at/below the *lower* edge of the measured 4340H
   band, whose upper edge runs **off the standard bar** (``D_c`` beyond EMJ p.29's J32 ≈ 142 mm). The
   scale was calibrated on Cr-Mo (4140); 4340's **nickel** potency is under-captured. This is the
   strongest non-circular result.
3. **A directional bias** — shallow grades (1045, 8620) ride at/above the band through the knee
   (knee + low-carbon hardness-map, *not* pure hardenability), the deep grade under-predicts.

Named scope edges
-----------------
* **We report ``D_c`` (water-quench centre-equivalent), not the *ideal* ``D_I``** — the latter is the
  ``H → ∞`` upper bound. A first AI-extracted ideal-``D_I`` table was dropped because *the extraction*
  was unreliable (self-contradictory, and falling on the oil column below water — see §1), not because
  the cited source is wrong. ``D_c`` is directly read (EMJ p.29) and used only as the cancelling
  conversion (applied identically both sides — the comparison lives in ``J50``). It tops out at J32
  (D_c ≈ 5.6 in / 142 mm); a ``J50`` beyond that is reported **off-scale**, not extrapolated.
* **The measured bands are cited anchor points**, partly read off published band *charts* (EMJ
  Reference Book) and partly exact tabulated values (SAE J1268 1045H); they carry the H-band's own
  ±2 HRC tolerance. Claims are **loose, directional bands**, ~2 sig figs — never a precise mm match.
* **No new physics, no new geometry.** The frozen Cartesian engine cannot simulate a round bar's
  radial centreline; none is needed — the end-quench↔diameter equivalence *is* how section-size
  hardenability is obtained from a Jominy curve industrially. This module is pure re-composition of
  the validated Jominy chain plus two cited lookup tables.

Units: ``D_c`` and distances in **mm** at the module boundary (the engineering unit for section size);
Jominy distance also carried in **1/16 in** (the J-number, the conversion's argument); hardness HRC; wt% C.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .jominy import JominyBar, solve_thermal_field, ThermalField
from .kinetics import ccurve_for_steel
from . import properties as prop

# --------------------------------------------------------------------------- #
# 1. The cited conversion — EMJ p.29 (Jominy distance -> critical diameter, 50 % martensite)
# --------------------------------------------------------------------------- #
# The empirical equal-hardness equivalence between a Jominy position and the round-bar diameter
# whose CENTRE reaches the same as-quenched hardness (so 50 % martensite at the same J). Read DIRECTLY
# (not AI-extracted) from the EMJ Reference Book p.29 table "Correlation between end-quench
# hardenability test and round bars", the "at centre" columns, for a mild WATER quench (the deeper
# reference EMJ tabulates) and a mild OIL quench (the shallower bracket).
#
# WHAT THIS REPORTS, AND WHY IT IS NOT THE *IDEAL* D_I (the advisor catch — a durable finding):
# the true ideal critical diameter D_I is the H -> infinity (infinitely severe quench) limit, which
# is an UPPER BOUND on the finite-quench centre-equivalent diameter (D_I >= D_water >= D_oil at a
# given J — a more severe quench through-hardens a *larger* bar to the same centre cooling rate). A
# first conversion was an AI-extracted "SAE J406 Table A7 ideal-D_I" and was DROPPED — NOT because
# J406's real table is wrong (it was never actually seen: the fetch failed and the text-extraction was
# unreliable, self-contradicting across attempts — J8 -> 2.97 then J8 -> 1.75), but because the
# extraction was untrustworthy and its values fell on the EMJ OIL column (below water), impossible for
# an ideal D_I. The physics check D_I >= D_water flagged the bad *extraction* (the durable lesson:
# verify an AI-extracted table against an independent direct read before trusting it). So this module
# reports the directly-read **water-quench centre-equivalent critical diameter D_c** (a defensible
# lower bound on the ideal D_I), used only as the scalar conversion applied IDENTICALLY to the model
# curve and the measured band — so its absolute accuracy cancels in the comparison; the discrimination
# lives in J50 (advisor).
DC_SOURCE = ("EMJ Reference Book (Earle M. Jorgensen) p.29, end-quench↔round-bar correlation, "
             "centre-of-round, mild water quench (the ideal D_I is the H→∞ upper bound)")
EMJ_J_SIXTEENTHS = np.array(
    [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0])
EMJ_DC_WATER_INCH = np.array(
    [0.3, 0.6, 1.0, 1.3, 1.6, 1.8, 2.0, 2.3, 2.8, 3.2, 3.6, 3.9, 4.5, 5.0, 5.4, 5.6])   # centre, water
EMJ_DC_OIL_INCH = np.array(
    [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.9, 2.3, 2.5, 2.9, 3.4, 3.9, 4.3, 4.5])    # centre, oil (bracket)

INCH_MM = 25.4
JOMINY_STEP_MM = 1.5875                      # 1/16 in, the J-number unit (ASTM A255)
DC_MAX_J = float(EMJ_J_SIXTEENTHS[-1])       # J32 — beyond this D_c is reported off-scale (off the bar)
DC_MAX_MM = float(EMJ_DC_WATER_INCH[-1] * INCH_MM)    # ~142 mm

# --------------------------------------------------------------------------- #
# 2. The cited 50 %-martensite hardness criterion (the measured side's J50 locator)
# --------------------------------------------------------------------------- #
# Hardness corresponding to a 50 %-martensite microstructure, vs carbon (the standard hardenability
# criterion). SAE J406 Table A5 / the classic Hodge-Orehoski 50 %-martensite curve. Cited, NOT the
# model's own rule-of-mixtures blend — so the benchmark stays independent of the model under test.
H50_SOURCE = "SAE J406 Table A5 / Hodge-Orehoski 50 %-martensite hardness curve"
H50_C = np.array([0.20, 0.30, 0.40, 0.45, 0.50, 0.60])
H50_HRC = np.array([30.0, 37.0, 43.0, 45.0, 47.0, 50.0])


def fifty_percent_martensite_HRC(C: float) -> float:
    """Cited 50 %-martensite hardness (HRC) at carbon ``C`` (wt %) — the measured side's J50 threshold.

    Linear interpolation of the cited Table A5 / Hodge-Orehoski curve. This is the hardness an
    end-quench *band* is read at to locate its 50 %-martensite Jominy distance.
    """
    return float(np.interp(C, H50_C, H50_HRC))


def jominy_to_critical_diameter(j_sixteenths: float) -> float:
    """Critical diameter ``D_c`` (mm, water-quench centre-equivalent) for a 50 %-martensite Jominy
    distance (1/16 in), via the cited EMJ p.29 table (a lower bound on the ideal ``D_I``).

    Returns ``inf`` for ``j_sixteenths`` beyond the table's range (J32 ≈ 142 mm) — the honest "off the
    standard bar", not an extrapolation. ``nan`` in -> ``nan`` out (no 50 %-martensite point).
    """
    if not np.isfinite(j_sixteenths):
        return float("nan") if np.isnan(j_sixteenths) else float("inf")
    if j_sixteenths > DC_MAX_J:
        return float("inf")
    return float(np.interp(j_sixteenths, EMJ_J_SIXTEENTHS, EMJ_DC_WATER_INCH) * INCH_MM)


# --------------------------------------------------------------------------- #
# 3. The benchmark steels — composition + MEASURED Jominy band + circularity role
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BenchmarkSteel:
    """One grade: composition, its cited *measured* Jominy band, and its circularity role.

    ``comp`` is the composition (wt%, including ``C``). ``band`` is a cited set of
    ``(J_sixteenths, HRC_min, HRC_max)`` anchor points of the measured end-quench hardenability band.
    ``role`` is one of "anchor" (calibration grade — a match is by construction), "teeth" (never
    touched the calibration — the real cross-check) or "edge" (documented bias, reported not tuned).
    ``source`` cites where the band came from.
    """

    name: str
    comp: dict
    role: str
    source: str
    band: tuple                       # ((J, HRC_min, HRC_max), ...)

    @property
    def carbon(self) -> float:
        return float(self.comp["C"])

    @property
    def minor(self) -> dict:
        """Composition without carbon — the minor-alloy dict for the Maynier hardness term."""
        return {k: v for k, v in self.comp.items() if k != "C"}

    def _band_arrays(self):
        b = np.asarray(self.band, dtype=float)
        return b[:, 0], b[:, 1], b[:, 2]      # J, HRC_min, HRC_max


# Compositions: the project's STEELS (1045/4140/8620) + 4340 added BENCHMARK-LOCAL (not surfaced in
# sweep.STEELS / the app — a validation-only grade, advisor). Measured bands are cited anchor points;
# the 1045H values are exact (SAE J1268 tabulated), the alloy bands are read off published band charts
# (EMJ Reference Book) anchored by SAE J1268 callout points — loose, ~2 sig figs, the H-band's own
# ±2 HRC tolerance. Each carries its source.
J1268 = "SAE J1268 (Hardenability Bands for Carbon and Alloy H Steels)"
EMJ = "EMJ Reference Book (Earle M. Jorgensen), Mechanical Properties & Hardenability, end-quench bands"

BENCHMARK_STEELS = {
    # Shallow, medium-carbon plain steel. EXACT band (SAE J1268 1045H, Fig. 4). The documented edge:
    # the model knee runs ~2-3 mm deep (2b/6a), so it rides above the measured band — reported.
    "1045": BenchmarkSteel(
        name="1045", role="edge",
        comp=dict(C=0.45, Mn=0.75, Si=0.22),
        source=f"{J1268} 1045H (Fig. 4, tabulated)",
        band=((1, 55, 62), (2, 42, 59), (3, 31, 52), (4, 28, 38),
              (6, 25, 32), (8, 24, 30), (12, 21, 28), (16, 20, 26)),
    ),
    # Deep-hardening Cr-Mo. THE CALIBRATION ANCHOR (HARDENABILITY_SCALE set to its nose) -> a match is
    # by construction. Band: SAE J1268 4140H (J8 = 42-54, the confirmed callout) + EMJ 4142 shape.
    "4140": BenchmarkSteel(
        name="4140", role="anchor",
        comp=dict(C=0.40, Mn=0.90, Si=0.25, Cr=1.00, Mo=0.20),
        source=f"{J1268} 4140H (J8 = 42-54 callout) + {EMJ} 4142",
        band=((2, 53, 58), (4, 49, 57), (8, 42, 54), (12, 40, 52),
              (16, 37, 50), (24, 35, 49), (32, 34, 48)),
    ),
    # Shallow carburizing-core composition (0.2 %C, lean Ni-Cr-Mo). TEETH. Band: SAE J1268 8620H
    # (J4 = 27-41, the confirmed callout) + EMJ 8620 shape. Leans on the 6a ferrite reaction (0.2 %C).
    "8620": BenchmarkSteel(
        name="8620", role="teeth",
        comp=dict(C=0.20, Mn=0.80, Si=0.25, Ni=0.55, Cr=0.50, Mo=0.20),
        source=f"{J1268} 8620H (J4 = 27-41 callout) + {EMJ} 8620",
        band=((2, 40, 47), (4, 27, 41), (6, 20, 34), (8, 20, 28), (10, 20, 24)),
    ),
    # Very deep-hardening Ni-Cr-Mo. TEETH, the deep end. Band read off EMJ 4340 chart. Benchmark-local
    # composition (not in sweep.STEELS). Its Ni potency was never in the (Cr-Mo) calibration.
    "4340": BenchmarkSteel(
        name="4340", role="teeth",
        comp=dict(C=0.40, Mn=0.70, Si=0.25, Ni=1.80, Cr=0.80, Mo=0.25),
        source=f"{EMJ} 4340 (band chart read-off)",
        band=((2, 51, 58), (8, 50, 57), (16, 48, 55), (24, 44, 53), (32, 40, 50)),
    ),
}


# --------------------------------------------------------------------------- #
# 4. The measured side — locate J50 where the band crosses the cited 50 %-martensite hardness
# --------------------------------------------------------------------------- #
def _cross_decreasing(j: np.ndarray, hrc: np.ndarray, level: float) -> float:
    """First Jominy distance (1/16 in) where a (mostly decreasing) band curve drops through ``level``.

    Linear interpolation between the bracketing anchor points. Returns ``-inf`` if the curve starts
    already below ``level`` (50 %-martensite reached at/before the quenched end -> a tiny D_I) and
    ``+inf`` if it never drops to ``level`` within the tabulated band (off the standard bar).
    """
    if hrc[0] <= level:
        return float("-inf")
    below = np.flatnonzero(hrc <= level)
    if below.size == 0:
        return float("inf")
    i = below[0]
    h0, h1 = hrc[i - 1], hrc[i]
    j0, j1 = j[i - 1], j[i]
    return float(j0 + (level - h0) * (j1 - j0) / (h1 - h0))


@dataclass(frozen=True)
class MeasuredDI:
    """The measured ideal-diameter band for a grade: ``(D_I_min, D_I_max)`` mm + their J50s."""

    grade: str
    h50_HRC: float
    j50_min: float            # 1/16 in (lower-hardenability band edge -> shallower)
    j50_max: float            # 1/16 in (upper-hardenability band edge -> deeper)
    Dc_min_mm: float
    Dc_max_mm: float
    upper_off_scale: bool     # max-band 50 %-martensite point runs past the EMJ J32 limit (off the bar)


def measured_ideal_diameter(steel: BenchmarkSteel) -> MeasuredDI:
    """Measured ``D_I`` band (mm) for ``steel`` — the cited Jominy band read at the cited 50 %M hardness."""
    j, hrc_min, hrc_max = steel._band_arrays()
    h50 = fifty_percent_martensite_HRC(steel.carbon)
    # The MIN band edge (lower hardenability) crosses h50 at a SMALLER J -> the shallower D_I, and the
    # MAX edge at a LARGER J -> the deeper D_I. A negative cross (already below at J1) clamps to J1.
    j50_lo = _cross_decreasing(j, hrc_min, h50)
    j50_hi = _cross_decreasing(j, hrc_max, h50)
    j50_lo_c = max(j50_lo, float(j[0])) if np.isfinite(j50_lo) else j50_lo
    j50_hi_c = max(j50_hi, float(j[0])) if np.isfinite(j50_hi) else j50_hi
    return MeasuredDI(
        grade=steel.name,
        h50_HRC=h50,
        j50_min=j50_lo_c,
        j50_max=j50_hi_c,
        Dc_min_mm=jominy_to_critical_diameter(j50_lo_c),
        Dc_max_mm=jominy_to_critical_diameter(j50_hi_c),
        upper_off_scale=(not np.isfinite(j50_hi)) or (j50_hi > DC_MAX_J),
    )


# --------------------------------------------------------------------------- #
# 5. The model side — D_I from the finished model via fM = 0.5
# --------------------------------------------------------------------------- #
# A fine Jominy distance grid out to the full bar (the J-number axis); deep grades need the reach.
_DEFAULT_DISTANCES_MM = np.linspace(1.0, 90.0, 240)


@dataclass(frozen=True)
class ModelDI:
    """The model's ideal diameter for a grade: ``D_I`` (mm) at ``fM = 0.5``, plus the curve behind it."""

    grade: str
    j50_sixteenths: float
    Dc_mm: float
    off_scale: bool           # fM never reached 0.5 within the bar, or J50 past the EMJ J32 limit
    jominy: prop.JominyHardness


def _solve_default_field(n_cells: int = 240) -> ThermalField:
    """The standard ASTM Jominy thermal field (reused across grades — solve once)."""
    return solve_thermal_field(JominyBar(), T0=850.0, n_cells=n_cells, per_decade=120)


def model_ideal_diameter(
    steel: BenchmarkSteel, field: ThermalField | None = None,
    distances_mm: np.ndarray | None = None,
) -> ModelDI:
    """Compute ``D_c`` (mm) for ``steel`` *from the model*: its Jominy ``fM = 0.5`` distance via EMJ p.29.

    Reuses the validated Jominy chain (:func:`properties.jominy_hardness`): the steel's
    hardenability-shifted C-curve, integrated through the frozen thermal ``field`` at every distance,
    gives the martensite fraction ``fM(J)``; ``J50`` is where ``fM`` crosses 0.5 (interpolated). The
    model side uses ``fM`` directly (not hardness) to isolate hardenability from the 2c hardness map.
    """
    if field is None:
        field = _solve_default_field()
    if distances_mm is None:
        distances_mm = _DEFAULT_DISTANCES_MM
    distances_m = np.asarray(distances_mm, dtype=float) * 1e-3
    cc = ccurve_for_steel(**steel.comp)
    jh = prop.jominy_hardness(field, cc, steel.carbon, distances_m, comp=steel.minor)

    fM = jh.martensite
    j16 = distances_m / (JOMINY_STEP_MM * 1e-3)
    below = np.flatnonzero(fM <= 0.5)
    if below.size == 0 or below[0] == 0:
        # never crossed 0.5 within the bar (fully martensitic throughout, or never martensitic) ->
        # off-scale: the model puts D_I beyond the sampled bar.
        return ModelDI(steel.name, float("inf"), float("inf"), off_scale=True, jominy=jh)
    i = below[0]
    f0, f1 = fM[i - 1], fM[i]
    j50 = float(j16[i - 1] + (0.5 - f0) * (j16[i] - j16[i - 1]) / (f1 - f0))
    DI = jominy_to_critical_diameter(j50)
    return ModelDI(steel.name, j50, DI, off_scale=(not np.isfinite(DI)), jominy=jh)


# --------------------------------------------------------------------------- #
# 6. The cross-check — model vs measured, with the circularity role
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CrossCheck:
    """One grade's D_I cross-check: model vs the measured band, tagged with its circularity role."""

    grade: str
    role: str
    model: ModelDI
    measured: MeasuredDI

    @property
    def in_band(self) -> bool:
        """Does the model D_I fall within the measured band (treating an off-scale upper edge as +inf)?"""
        lo = self.measured.Dc_min_mm
        hi = float("inf") if self.measured.upper_off_scale else self.measured.Dc_max_mm
        m = self.model.Dc_mm
        return bool(lo <= m <= hi) if np.isfinite(m) else (hi == float("inf"))

    @property
    def verdict(self) -> str:
        """A short directional read: 'in band' / 'rides high (shallow bias)' / 'under-predicts (deep)'."""
        m = self.model.Dc_mm
        if self.in_band:
            return "in band"
        if np.isfinite(m) and m < self.measured.Dc_min_mm:
            return "under-predicts (below measured band)"
        return "rides high (above measured band)"


def crosscheck(steel: BenchmarkSteel, field: ThermalField | None = None) -> CrossCheck:
    """Full D_I cross-check for one benchmark steel (model fM=0.5 vs the measured-band D_I)."""
    return CrossCheck(
        grade=steel.name, role=steel.role,
        model=model_ideal_diameter(steel, field=field),
        measured=measured_ideal_diameter(steel),
    )


def crosscheck_all(field: ThermalField | None = None) -> dict:
    """Cross-check every benchmark steel against one shared thermal field (solve once)."""
    if field is None:
        field = _solve_default_field()
    return {name: crosscheck(s, field=field) for name, s in BENCHMARK_STEELS.items()}
