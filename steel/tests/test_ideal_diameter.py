"""Phase-6c validation: the ideal-critical-diameter (D_I) / measured-Jominy cross-check.

6c closes the Jominy chain's one un-checked leg: every 2a–2c/6a calibration was anchored to its own
data (thermal curve, TTT nose, constituent hardnesses), but the *absolute depth of hardening* the
combination predicts was never directly validated. The critical diameter (the round-bar diameter
that is 50 % martensite at its centre — reported as ``D_c``, the water-quench centre-equivalent, a
lower bound on the ideal ``D_I``) measures exactly that, and the benchmark is **measured** end-quench
hardenability — NOT a Grossmann calculation (which would be circular, since the model's hardenability
rides Grossmann *relative potencies*; :mod:`ideal_diameter` docstring).

The triad, with the circularity roles deliberate (the model must not be graded on a grade it was
calibrated to):

* **Analytical / structural** — the two cited lookup tables behave: the EMJ p.29 J→D_c conversion is
  monotone, reproduces its anchors, stays above the oil bracket (the physics check that caught a bad
  AI-extracted "ideal-D_I" table), and goes off-scale past J32; the cited 50 %-martensite hardness
  rises with carbon; the measured-band crossing logic orders min below max.
* **THE CROSS-CHECK (teeth)** — read the *shape*, not "within X %". (1) the model hardenability
  **ranking is correct** (1045 < 8620 < 4140 < 4340 — alloy beats carbon); (2) **4340 is
  under-predicted** (model at/below the measured band's lower edge, whose upper edge runs off the
  standard bar) — the Cr-Mo-calibrated scale under-captures 4340's Ni potency, the strongest
  non-circular result; (3) the **directional bias** — shallow grades ride high through the knee, the
  deep grade under-predicts. 4140 (the calibration anchor) lands in its wide band *by construction*.
* **Corroborating** — the direct model HRC(J) curve (threshold/conversion-free) tracks the measured
  4140H band over the hardenability range, with the near-end hardness-map fold named.
"""
import numpy as np
import pytest

from projects.steel import ideal_diameter as idd
from projects.steel import sweep


@pytest.fixture(scope="module")
def field():
    """One shared ASTM Jominy thermal field — solved once, reused across grades (fast)."""
    return idd._solve_default_field()


@pytest.fixture(scope="module")
def checks(field):
    """The full cross-check for every benchmark steel against the shared field."""
    return idd.crosscheck_all(field)


# --------------------------------------------------------------------------- #
# Analytical / structural: the two cited tables and the crossing logic
# --------------------------------------------------------------------------- #
def test_critical_diameter_conversion_is_monotone_and_anchored():
    # The EMJ p.29 water-quench conversion reproduces its own anchor points (J→inch×25.4 mm) and rises.
    assert idd.jominy_to_critical_diameter(2.0) == pytest.approx(0.6 * 25.4, rel=1e-9)
    assert idd.jominy_to_critical_diameter(16.0) == pytest.approx(3.9 * 25.4, rel=1e-9)
    js = np.linspace(1.0, 32.0, 32)
    di = [idd.jominy_to_critical_diameter(j) for j in js]
    assert np.all(np.diff(di) > 0)                       # strictly increasing
    # The reported D_c (water) must NOT exceed the ideal-D_I upper bound — but it MUST exceed the oil
    # bracket at every J (D_oil < D_water; the physics check that caught the bad AI-extracted table).
    water = np.interp(js, idd.EMJ_J_SIXTEENTHS, idd.EMJ_DC_WATER_INCH)
    oil = np.interp(js, idd.EMJ_J_SIXTEENTHS, idd.EMJ_DC_OIL_INCH)
    assert np.all(water >= oil)
    # Beyond J32 is OFF-SCALE (the honest "off the standard bar"), not an extrapolation; nan→nan.
    assert idd.jominy_to_critical_diameter(40.0) == float("inf")
    assert np.isnan(idd.jominy_to_critical_diameter(float("nan")))


def test_fifty_percent_martensite_hardness_is_cited_and_rises_with_carbon():
    # The cited (SAE J406 / Hodge-Orehoski) 50 %-martensite hardness — independent of the model.
    assert idd.fifty_percent_martensite_HRC(0.20) == pytest.approx(30.0)
    assert idd.fifty_percent_martensite_HRC(0.40) == pytest.approx(43.0)
    assert idd.fifty_percent_martensite_HRC(0.45) == pytest.approx(45.0)
    cs = np.linspace(0.20, 0.60, 21)
    h = [idd.fifty_percent_martensite_HRC(c) for c in cs]
    assert np.all(np.diff(h) > 0)                        # rises with carbon


def test_measured_band_crossing_edge_cases():
    j = np.array([2.0, 4.0, 8.0])
    # starts already below the level → 50 % martensite at/before the quenched end (tiny D_I).
    assert idd._cross_decreasing(j, np.array([40.0, 30.0, 20.0]), 50.0) == float("-inf")
    # never drops to the level within the band → off the standard bar.
    assert idd._cross_decreasing(j, np.array([60.0, 58.0, 55.0]), 50.0) == float("inf")
    # a clean interior crossing is interpolated.
    assert idd._cross_decreasing(j, np.array([60.0, 50.0, 40.0]), 45.0) == pytest.approx(6.0)


def test_measured_di_band_orders_min_below_max_for_every_grade(checks):
    for cc in checks.values():
        me = cc.measured
        hi = float("inf") if me.upper_off_scale else me.DI_max_mm
        assert me.DI_min_mm <= hi                         # lower-hardenability edge ≤ deeper edge
        assert me.j50_min <= (np.inf if not np.isfinite(me.j50_max) else me.j50_max)


# --------------------------------------------------------------------------- #
# THE CROSS-CHECK (teeth) — lead with the ranking, feature the 4340 under-prediction
# --------------------------------------------------------------------------- #
def test_model_hardenability_ranking_is_correct(checks):
    # THE HEADLINE. The model's D_I orders the grades by true hardenability: a 0.2 %C carburizing
    # steel (8620) out-hardens a 0.45 %C plain one (1045) — alloy beats carbon — and the alloy
    # steels rank 4140 < 4340. This emerges from the cited potencies; nothing here is fit to D_I.
    di = {n: cc.model.DI_mm for n, cc in checks.items()}
    assert di["1045"] < di["8620"] < di["4140"] < di["4340"]


def test_anchor_4140_lands_in_its_measured_band_by_construction(checks):
    # 4140 is THE CALIBRATION ANCHOR (HARDENABILITY_SCALE was set to its nose), so this is a
    # consistency check, NOT teeth: it must land inside the (wide) measured 4140H band.
    cc = checks["4140"]
    assert cc.role == "anchor"
    assert cc.in_band
    assert 75.0 < cc.model.DI_mm < 135.0                  # deep, mid of the wide 4140H band


def test_teeth_8620_shallow_end_lands_in_band(checks):
    # 8620 (0.2 %C carburizing core) — TEETH, never in the calibration. Read at the CITED 30-HRC
    # 50 %-martensite hardness (not the model's blend), its model D_I lands in the measured band.
    cc = checks["8620"]
    assert cc.role == "teeth"
    assert cc.in_band
    assert 35.0 < cc.model.DI_mm < 70.0


def test_teeth_4340_deep_end_is_under_predicted(checks):
    # THE STRONGEST NON-CIRCULAR RESULT. 4340 — TEETH, the deep end. The scale was calibrated on
    # Cr-Mo (4140); 4340's NICKEL potency is under-captured, so the model sits at/below the measured
    # band's lower edge, while the band's upper edge runs OFF the standard bar (D_c past EMJ J32).
    cc = checks["4340"]
    assert cc.role == "teeth"
    assert cc.measured.upper_off_scale                    # deepest heats run off the 50 mm bar
    assert cc.model.DI_mm < cc.measured.DI_min_mm         # model below even the shallow-heat edge
    assert cc.model.DI_mm > 95.0                          # still firmly in the deep-hardening regime
    assert cc.verdict.startswith("under-predicts")


def test_edge_1045_rides_high_through_the_knee(checks):
    # 1045 — the DOCUMENTED EDGE: its model knee runs ~2-3 mm deep (the 2b/6a A₁/ferrite story), so
    # it rides above the (exact, SAE J1268) measured band. Reported, never tuned.
    cc = checks["1045"]
    assert cc.role == "edge"
    assert cc.model.DI_mm > cc.measured.DI_max_mm         # above the measured band
    assert cc.model.DI_mm < 50.0                          # still a shallow-hardening steel


def test_directional_bias_shallow_high_deep_low(checks):
    # The honest SHAPE (not "within X %"): shallow grades ride at/above the measured band (knee +
    # low-carbon hardness-map), the deep grade under-predicts (Ni potency). 8620 lands at the top
    # edge (in band) — the shallow-bias direction without crossing out.
    assert checks["1045"].verdict.startswith("rides high")
    assert checks["4340"].verdict.startswith("under-predicts")
    # 1045's overshoot is modest, not wild (a few mm above a ~20 mm band).
    assert checks["1045"].model.DI_mm - checks["1045"].measured.DI_max_mm < 12.0


# --------------------------------------------------------------------------- #
# Corroborating — the direct HRC(J) curve tracks the measured 4140H band
# --------------------------------------------------------------------------- #
def test_corroborating_4140_hrc_curve_tracks_measured_band(checks):
    # The threshold/conversion-free layer: the model's hardness traverse for the anchor 4140 falls
    # within its measured band over the hardenability range — with the NEAR-END hardness-map fold
    # named (the model's as-quenched martensite runs a touch hard, so allow +3 HRC near the end).
    cc = checks["4140"]
    jh = cc.model.jominy
    dist_mm = jh.distance * 1e3
    band = {2: (53, 58), 8: (42, 54), 16: (37, 50), 24: (35, 49)}   # SAE J1268 4140H anchors
    for j16, (lo, hi) in band.items():
        hrc = float(np.interp(j16 * idd.JOMINY_STEP_MM, dist_mm, jh.HRC))
        assert lo - 3.0 <= hrc <= hi + 3.0, f"4140 J{j16}: {hrc:.1f} not within [{lo},{hi}]±3"


# --------------------------------------------------------------------------- #
# Hygiene — roles/sources present; 4340 stays benchmark-local (no surface expansion)
# --------------------------------------------------------------------------- #
def test_every_benchmark_steel_carries_a_role_and_source(checks):
    for cc in checks.values():
        steel = idd.BENCHMARK_STEELS[cc.grade]
        assert steel.role in {"anchor", "teeth", "edge"}
        assert steel.source                               # a citation string
        j, _, _ = steel._band_arrays()
        assert np.all(np.diff(j) > 0)                     # band anchors ordered by distance


def test_4340_is_benchmark_local_not_surfaced_in_sweep():
    # Advisor: 4340 is added as a validation-only grade — it must NOT leak into the interactive
    # surface (sweep.STEELS / the app), which deliberately ships 1045/1080/4140/8620.
    assert "4340" in idd.BENCHMARK_STEELS
    assert "4340" not in sweep.STEELS
