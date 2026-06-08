"""Phase-2c validation: the microstructure→hardness map + the Jominy benchmark (Steel plan §3).

Phase 2c seeds the property model (:mod:`properties`) and with it banks the **third
leg of the Phase-2 validation triad** — the published Jominy hardness benchmark (the
analytical-limit and conservation legs were banked thermally in 2a). The discipline the
plan §3 demands is that each sub-model anchors to its *own* published data, so the
end-quench curve is a genuine cross-check rather than a refit. That shapes this file:

* **The hardness map in isolation — anchored to independent data.** The constituent
  hardnesses are fit to datasets that are *not* the Jominy curve: martensite to the
  as-quenched-martensite-vs-%C curve (Hodge–Orehoski/Krauss), ferrite-pearlite to
  normalized plain-carbon hardness (ASM). So reproducing the Jominy quenched end is real
  agreement. Both benchmark steels are ~0.4 %C, so the martensite-curve *slope* is tested
  separately at 0.6/0.8 %C — otherwise the benchmark exercises a single point.
* **The HV→HRC conversion** is pinned to ASTM E140 reference pairs (not just a round-trip)
  and bounded to ~20–65 HRC — below that HRC is undefined and the model says so (``nan``).
* **The rule of mixtures** is checked structurally (exact at a pure phase, bounded by the
  constituents, monotone in martensite fraction) — the analytical-limit leg *of the map*.
* **The benchmark / consequence.** 1045 and 4140 (both ~0.4 %C) **share the quenched-end
  hardness** — which validates the *hardness model alone*, since the 2b hardenability
  shift is silent where everything is martensite — and then **diverge with distance**:
  4140 stays hard deep (its published deep-hardening plateau), 1045 falls steeply to a
  soft, off-HRC-scale pearlitic tail. Published 1040/4140 end-quench curves (Callister;
  ASM Handbook Vol. 1) are used as *reference facts* with an honest band tolerance. The
  1045 knee sits ~2–3 mm deeper than published — an inherited, documented Phase-2b
  kinetics simplification (``T_eq`` held at A₁, not A₃, for hypoeutectoid steel), **not**
  a hardness-map error — so the well-anchored claims (quenched-end, the 4140 plateau, the
  divergence) are asserted tightly and the 1045 knee *position* loosely.
"""
import numpy as np
import pytest

from projects.steel import properties as prop
from projects.steel.kinetics import ccurve_for_steel
from projects.steel.jominy import solve_thermal_field, JominyBar, jominy_distances

# The two benchmark steels (as in the Phase-2b hardenability test): a medium-carbon
# plain steel and a deep-hardening low-alloy one, both ≈ 0.4 %C.
STEEL_1045 = dict(C=0.45, Mn=0.75, Si=0.22)
STEEL_4140 = dict(C=0.40, Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)


# --------------------------------------------------------------------------- #
# The HV → HRC conversion: ASTM E140 accuracy + bounded validity (advisor #3)
# --------------------------------------------------------------------------- #
def test_vickers_to_rockwell_c_matches_E140_pairs():
    # Pin known ASTM E140 (steel) pairs in the band the benchmark lives in — accuracy,
    # not just invertibility. ~±1 HRC is the table's own granularity.
    for HV, HRC in [(300.0, 30.0), (392.0, 40.0), (513.0, 50.0), (595.0, 55.0), (697.0, 60.0)]:
        assert prop.vickers_to_rockwell_c(HV) == pytest.approx(HRC, abs=1.0)


def test_vickers_to_rockwell_c_is_monotone_and_bounded():
    HV = np.linspace(240.0, 900.0, 200)
    HRC = prop.vickers_to_rockwell_c(HV)
    assert np.all(np.diff(HRC) > 0)                       # strictly increasing
    assert np.all((HRC >= prop.RELIABLE_HRC_MIN - 1e-9) & (HRC <= prop.RELIABLE_HRC_MAX + 1e-9))


def test_vickers_to_rockwell_c_nan_off_scale():
    # Below ~240 HV (~20 HRC) Rockwell-C is undefined — the honest output is nan, not a
    # clamped number (soft ferrite-pearlite is quoted in HRB/HB). Likewise above the table.
    assert np.isnan(prop.vickers_to_rockwell_c(200.0))    # soft pearlite → off-scale
    assert np.isnan(prop.vickers_to_rockwell_c(1000.0))
    arr = prop.vickers_to_rockwell_c(np.array([200.0, 500.0, 1000.0]))
    assert np.isnan(arr[0]) and np.isfinite(arr[1]) and np.isnan(arr[2])


# --------------------------------------------------------------------------- #
# Constituent hardnesses: independent anchors + the carbon slope (advisor #1)
# --------------------------------------------------------------------------- #
def test_martensite_matches_as_quenched_curve_across_carbon():
    # The INDEPENDENT anchor: the as-quenched (99.9 %) martensite hardness-vs-%C curve.
    # Both benchmark steels are 0.4 %C, so the *slope* is what makes this more than one
    # point — check 0.2/0.4/0.6/0.8 %C against the canonical curve (rising, saturating
    # toward ~65 HRC). Bands reflect the curve's own ±2 HRC inter-source spread.
    hrc = lambda C: prop.vickers_to_rockwell_c(prop.vickers_martensite(C))
    assert 44.0 <= hrc(0.20) <= 50.0
    assert 54.0 <= hrc(0.40) <= 58.0
    assert 59.0 <= hrc(0.60) <= 64.0
    assert 63.0 <= hrc(0.80) <= 66.0                      # the saturating plateau
    # Monotone increasing and concave (saturating) — the √C signature, not a straight line.
    # (Uniform carbon spacing so the second difference reads concavity directly.)
    hv = np.array([prop.vickers_martensite(C) for C in np.linspace(0.1, 1.0, 10)])
    assert np.all(np.diff(hv) > 0)                        # rises with carbon
    assert np.all(np.diff(hv, 2) < 0)                     # concave (saturating), not linear


def test_ferrite_pearlite_matches_normalized_plain_carbon_hardness():
    # Independent anchor: normalized plain-carbon steel hardness (ASM ranges). ~200–220 HV
    # at 0.45 %C (1045), ~290–310 HV at 0.8 %C (1080). This is what makes the 1045 far-end
    # Jominy hardness a prediction, not a fit.
    assert 195.0 <= prop.vickers_ferrite_pearlite(0.45) <= 225.0
    assert 285.0 <= prop.vickers_ferrite_pearlite(0.80) <= 315.0
    assert prop.vickers_ferrite_pearlite(0.80) > prop.vickers_ferrite_pearlite(0.20)


def test_constituent_hardness_ordering():
    # Physical ordering of the carbon-dependent constituents at every carbon: martensite
    # (hardest) > bainite > ferrite-pearlite. Retained austenite is a soft constant — much
    # softer than martensite — but not the absolute floor (at low carbon, ferrite-pearlite
    # is softer still); only its hardness *relative to martensite* is load-bearing.
    for C in (0.2, 0.4, 0.6, 0.8):
        assert (prop.vickers_martensite(C) > prop.vickers_bainite(C)
                > prop.vickers_ferrite_pearlite(C))
        assert prop.vickers_martensite(C) > prop.HV_RETAINED_AUSTENITE  # retained γ is soft


# --------------------------------------------------------------------------- #
# The rule of mixtures: structural / analytical-limit checks (the map itself)
# --------------------------------------------------------------------------- #
def test_pure_phase_recovers_its_constituent_hardness_exactly():
    # A 100 % martensite structure is exactly as hard as the martensite constituent —
    # the analytic limit the benchmark's quenched end relies on. Likewise pure pearlite.
    C = 0.45
    assert prop.hardness_HV({"martensite": 1.0}, C) == pytest.approx(prop.vickers_martensite(C))
    assert prop.hardness_HV({"pearlite": 1.0}, C) == pytest.approx(prop.vickers_ferrite_pearlite(C))


def test_rule_of_mixtures_is_bounded_by_constituents():
    # Any partition's hardness lies between the softest and hardest constituent present —
    # the convex-combination property (a "conservation"-style bound on the weighted mean).
    C = 0.5
    constituents = [prop.vickers_ferrite_pearlite(C), prop.vickers_bainite(C),
                    prop.vickers_martensite(C), prop.HV_RETAINED_AUSTENITE]
    softest, hardest = min(constituents), max(constituents)
    rng = np.random.default_rng(0)
    for _ in range(50):
        w = rng.random(4)
        w /= w.sum()
        frac = dict(zip(("pearlite", "bainite", "martensite", "retained_austenite"), w))
        HV = prop.hardness_HV(frac, C)
        assert softest - 1e-9 <= HV <= hardest + 1e-9


def test_hardness_monotone_in_martensite_fraction():
    # Trading pearlite for martensite only ever raises hardness — the whole point of a
    # quench, and what makes hardness a faithful readout of the martensite gradient.
    C = 0.5
    HVs = [prop.hardness_HV({"martensite": m, "pearlite": 1.0 - m}, C)
           for m in np.linspace(0.0, 1.0, 11)]
    assert np.all(np.diff(HVs) > 0)


def test_50pct_martensite_matches_hodge_orehoski_criterion():
    # The MIXTURE anchor — independent of both endpoint datasets (as-quenched martensite,
    # normalized pearlite). The classic 50 %-martensite hardness criterion (Hodge & Orehoski
    # 1946; the basis of the D_I framework) measures the hardness of a 50/50 martensite-
    # pearlite structure vs carbon: ~43 HRC at 0.40 %C, rising to ~50 HRC at 0.60 %C. That
    # the rule-of-mixtures *output* (not just its pure-phase endpoints) lands on this third,
    # independent curve is what closes the non-circularity story — and it is read at fM = 0.5
    # regardless of *where* that occurs on a bar, so it validates the hardness map in the
    # transition decoupled from the kinetics' knee position. The model sits ~1–2 HRC below the
    # measured curve (the linear rule slightly underpredicts the real 50 %-M hardness).
    hrc50 = lambda C: prop.vickers_to_rockwell_c(prop.hardness_HV({"martensite": 0.5, "pearlite": 0.5}, C))
    assert 40.0 <= hrc50(0.40) <= 46.0                   # canonical ~43 HRC
    assert 42.0 <= hrc50(0.50) <= 48.0                   # canonical ~46 HRC
    assert 45.0 <= hrc50(0.60) <= 52.0                   # canonical ~50 HRC
    assert hrc50(0.40) < hrc50(0.50) < hrc50(0.60)       # rises with carbon


def test_unknown_constituent_raises():
    # A fractions/registry mismatch is a real error, not a silent zero contribution.
    with pytest.raises(KeyError):
        prop.hardness_HV({"graphite": 1.0}, 0.4)


# --------------------------------------------------------------------------- #
# Shared quenched-end hardness — validates the hardness model in ISOLATION (advisor #2)
# --------------------------------------------------------------------------- #
def test_1045_and_4140_share_quenched_end_hardness():
    # At the quenched end both steels are full martensite, so the 2b hardenability shift
    # is silent and only the martensite hardness model speaks. Both ~0.4 %C → both land at
    # ~55–58 HRC (the as-quenched-martensite anchor), within a couple HRC of each other.
    # This is the clean isolation of the hardness sub-model the plan calls for.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)
    h1045 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_1045), STEEL_1045["C"], d)
    h4140 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_4140), STEEL_4140["C"], d)

    assert 54.0 <= h1045.HRC[0] <= 60.0
    assert 54.0 <= h4140.HRC[0] <= 60.0
    assert abs(h1045.HRC[0] - h4140.HRC[0]) < 3.0         # shared, set by ~0.4 %C martensite


# --------------------------------------------------------------------------- #
# The Jominy hardness benchmark — the third Phase-2 triad leg (advisor #5)
# --------------------------------------------------------------------------- #
def _hardness_curves():
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)                              # 1.6 .. 25.4 mm
    h1045 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_1045), STEEL_1045["C"], d)
    h4140 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_4140), STEEL_4140["C"], d)
    return d, h1045, h4140


def test_benchmark_4140_deep_hardening_plateau():
    # 4140 is the deep-hardening steel: its published end-quench curve stays high right
    # across the read region — ~52–57 HRC through ½ inch (12.7 mm), still ~45–50 HRC at
    # 1 inch (25.4 mm). The model's strongest quantitative benchmark match.
    d, _, h4140 = _hardness_curves()
    j8 = int(np.argmin(np.abs(d - 0.0127)))               # ½ inch
    assert h4140.HRC[j8] > 50.0                           # still hard at mid-bar
    assert 44.0 <= h4140.HRC[-1] <= 53.0                  # 1 inch: deep-hardening plateau
    assert np.all(h4140.HRC > 44.0)                       # never falls out of the hard band


def test_benchmark_1045_shallow_hardening():
    # 1045 is the shallow-hardening steel: martensitic at the quenched end, then a steep
    # fall to a soft, *off-HRC-scale* pearlitic tail (published 1040 tails to ~20 HRC).
    d, h1045, _ = _hardness_curves()
    assert h1045.HRC[0] > 54.0                            # quenched end: martensitic
    j8 = int(np.argmin(np.abs(d - 0.0127)))
    assert h1045.HRC[j8] < 38.0                           # already soft by ½ inch
    assert np.isnan(h1045.HRC[-1])                        # far end: off the HRC scale (soft)
    assert h1045.HV[-1] < 240.0                           # ...softer than ~20 HRC, in HV
    assert h1045.HV[0] - h1045.HV[-1] > 350.0             # a large drop across the bar


def test_benchmark_hardness_diverges_with_distance():
    # The headline: same quenched-end hardness, dramatically different at depth. At ½ inch
    # the alloy steel is still hard while the plain steel has gone soft — the hardenability
    # gap, now read in hardness (the 2b martensite divergence translated through the map).
    d, h1045, h4140 = _hardness_curves()
    j8 = int(np.argmin(np.abs(d - 0.0127)))
    assert h4140.HRC[j8] - h1045.HRC[j8] > 15.0           # model gap ≈ 23 HRC
    assert h4140.HV[-1] - h1045.HV[-1] > 250.0            # and far deeper still (HV, both defined)


def test_hardness_decreases_monotonically_with_distance():
    # Hardenability curves never rise with distance (cooling rate, hence martensite, only
    # falls). Asserted in HV (defined everywhere, including the soft 1045 tail).
    _, h1045, h4140 = _hardness_curves()
    assert np.all(np.diff(h1045.HV) <= 1e-9)
    assert np.all(np.diff(h4140.HV) <= 1e-9)


# --------------------------------------------------------------------------- #
# Integration: jominy_hardness composes thermal → kinetics → property consistently
# --------------------------------------------------------------------------- #
def test_jominy_hardness_arrays_consistent():
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=120, per_decade=60)
    d = jominy_distances(16)
    h = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_4140), STEEL_4140["C"], d)
    assert h.distance.shape == h.HV.shape == h.HRC.shape == h.martensite.shape == d.shape
    assert np.all((h.martensite >= 0.0) & (h.martensite <= 1.0))
    # HRC is exactly the E140 image of HV (the reporting boundary), nan where off-scale.
    expected = prop.vickers_to_rockwell_c(h.HV)
    finite = np.isfinite(expected)
    assert np.array_equal(np.isnan(h.HRC), ~finite)
    assert np.allclose(h.HRC[finite], expected[finite])
    assert h.carbon == STEEL_4140["C"]
