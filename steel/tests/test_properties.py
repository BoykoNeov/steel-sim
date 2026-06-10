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
import math

import numpy as np
import pytest

from steel import properties as prop
from steel.kinetics import ccurve_for_steel, ABS_ZERO
from steel.jominy import solve_thermal_field, JominyBar, jominy_distances

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


# =========================================================================== #
# Phase 3a — Maynier minor-alloy + cooling-rate graft on the 2c carbon baselines.
#
# The graft keeps 2c's independently-anchored carbon baselines and bolts on only
# Maynier's *non-carbon* deltas, reference-zeroed. The discipline these tests pin:
#   (1) the seam — defaults reproduce the 2c carbon-only value byte-for-byte, so the
#       frozen 2c benchmark above is unchanged (it stays carbon-only by signature);
#   (2) the deltas match Maynier's published coefficients (anchored, not invented);
#   (3) the new terms are the *improvements* 2c flagged as Phase-3 work — the
#       minor-alloy term closes the 4140≈1045 quenched-end gap; the cooling-rate term
#       is honestly small for plain carbon; the constituent ordering is preserved.
# =========================================================================== #
# 1045's / 4140's minor-alloy comp dicts (carbon excluded — it rides the baseline).
COMP_1045 = {"Mn": 0.75, "Si": 0.22}
COMP_4140 = {"Mn": 0.90, "Cr": 1.0, "Mo": 0.20, "Si": 0.25}


def test_defaults_reproduce_2c_carbon_only_byte_for_byte():
    # THE SEAM (advisor): the optional comp/Vr default to the exact 2c value, so every
    # frozen 2c call above is unchanged. Assert the constituent functions and the rule of
    # mixtures are identical with the args omitted vs explicitly None.
    for C in (0.20, 0.45, 0.80):
        # math.sqrt (not C**0.5) to match the source exactly — pow isn't correctly-rounded,
        # so == against C**0.5 could flake 1 ULP for reasons unrelated to the graft.
        assert prop.vickers_martensite(C) == prop.MART_HV_BASE + prop.MART_HV_SLOPE * math.sqrt(C)
        assert prop.vickers_martensite(C, comp=None, Vr=None) == prop.vickers_martensite(C)
        assert prop.vickers_ferrite_pearlite(C) == prop.FP_HV_BASE + prop.FP_HV_SLOPE * C
        assert prop.vickers_ferrite_pearlite(C, comp=None, Vr=None) == prop.vickers_ferrite_pearlite(C)
    frac = {"martensite": 0.5, "pearlite": 0.3, "bainite": 0.15, "retained_austenite": 0.05}
    assert prop.hardness_HV(frac, 0.45, comp=None, Vr=None) == prop.hardness_HV(frac, 0.45)


def test_martensite_alloy_delta_matches_maynier_coefficients():
    # Anchored, not invented: the martensite minor-alloy delta IS Maynier's non-carbon
    # martensite coefficients 27Si + 11Mn + 8Ni + 16Cr (HV per wt%).
    delta = prop.vickers_martensite(0.40, comp=COMP_4140) - prop.vickers_martensite(0.40)
    expected = 27.0 * 0.25 + 11.0 * 0.90 + 16.0 * 1.0          # Si, Mn, Cr (Ni=Mo=0 here)
    assert delta == pytest.approx(expected, abs=1e-9)


def test_minor_alloy_term_closes_4140_1045_quenched_end_gap():
    # The headline Phase-3 improvement, on the constituent directly (decoupled from the
    # kinetics): at the fully-martensitic quenched end, carbon-only the leaner-carbon 4140
    # (0.40 %C) reads BELOW 1045 (0.45 %C) by >1 HRC — the gap 2c flagged. The Maynier
    # minor-alloy term (4140's Cr/Mn) closes it to ~equal, matching published data.
    hrc = prop.vickers_to_rockwell_c
    gap_carbon = hrc(prop.vickers_martensite(0.45)) - hrc(prop.vickers_martensite(0.40))
    gap_alloy = (hrc(prop.vickers_martensite(0.45, comp=COMP_1045))
                 - hrc(prop.vickers_martensite(0.40, comp=COMP_4140)))
    assert gap_carbon > 1.0                                   # 2c: 1045 ~1.4 HRC above 4140
    assert abs(gap_alloy) < 1.0                               # Phase 3: ~equal (gap closed)
    assert gap_alloy < gap_carbon                             # the term moved them together


def test_ferrite_pearlite_alloy_delta_matches_maynier_coefficients():
    # The FP minor-alloy delta IS Maynier's non-carbon FP coefficients
    # 53Si + 30Mn + 12.6Ni + 7Cr + 19Mo (with Vr omitted, so no cooling-rate term).
    delta = prop.vickers_ferrite_pearlite(0.45, comp=COMP_4140) - prop.vickers_ferrite_pearlite(0.45)
    expected = 53.0 * 0.25 + 30.0 * 0.90 + 7.0 * 1.0 + 19.0 * 0.20
    assert delta == pytest.approx(expected, abs=1e-9)


def test_ferrite_pearlite_cooling_rate_term_direction_and_honest_magnitude():
    # The cooling-rate term: faster cooling → finer → harder pearlite, and it vanishes at
    # the reference rate (recovering the 2c baseline). HONEST magnitude (advisor #3): for
    # PLAIN CARBON the slope is only ~10 HV/decade, so a furnace→air step (~0.5 decade) is
    # only ~5 HV — a few HV, not a dramatic gap. We assert that smallness, not inflate it.
    base = prop.vickers_ferrite_pearlite(0.80)
    assert prop.vickers_ferrite_pearlite(0.80, Vr=prop.MAYNIER_VR_REF) == pytest.approx(base, abs=1e-9)
    fast = prop.vickers_ferrite_pearlite(0.80, Vr=10.0 * prop.MAYNIER_VR_REF)
    slow = prop.vickers_ferrite_pearlite(0.80, Vr=0.1 * prop.MAYNIER_VR_REF)
    assert fast > base > slow                                 # monotone in cooling rate
    assert fast - base == pytest.approx(10.0, abs=1e-9)       # plain-carbon slope ~10 HV/decade
    assert (fast - slow) < 25.0                               # ~2 decades → ~20 HV: a small effect


def test_bainite_alloy_and_cooling_rate_are_deferred():
    # Bainite stays carbon-only: its Maynier coefficients are too large to graft onto the
    # placeholder baseline (would exceed martensite), so comp/Vr are accepted but ignored.
    for C in (0.2, 0.45, 0.8):
        assert prop.vickers_bainite(C, comp=COMP_4140, Vr=1e6) == prop.vickers_bainite(C)


def test_constituent_ordering_preserved_with_alloy_terms():
    # Adding the minor-alloy deltas must not break the physical ordering martensite >
    # bainite > ferrite-pearlite (the bound the rule of mixtures relies on). FP gets a
    # delta and bainite does not, so this is the case that could invert — check it holds.
    for C in (0.2, 0.4, 0.6, 0.8):
        m = prop.vickers_martensite(C, comp=COMP_4140)
        b = prop.vickers_bainite(C, comp=COMP_4140)
        fp = prop.vickers_ferrite_pearlite(C, comp=COMP_4140, Vr=prop.MAYNIER_VR_REF)
        assert m > b > fp


def test_jominy_hardness_alloy_term_closes_gap_and_lifts_1045_tail():
    # The threaded path the new terms actually fire through (advisor #2). With the full
    # composition, jominy_hardness closes the quenched-end gap AND lifts the 1045 soft tail
    # from off-HRC-scale (the 2c result) onto ~20 HRC — matching the published ~22 HRC tail.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)
    # carbon-only (byte-identical to 2c): 1045 tail is off-scale (nan).
    h45_c = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_1045), STEEL_1045["C"], d)
    assert np.isnan(h45_c.HRC[-1])
    # with minor-alloy comp: gap closes and the 1045 tail lands on the HRC scale.
    h45 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_1045), STEEL_1045["C"], d,
                               comp=COMP_1045, use_cooling_rate=True)
    h41 = prop.jominy_hardness(f, ccurve_for_steel(**STEEL_4140), STEEL_4140["C"], d,
                               comp=COMP_4140, use_cooling_rate=True)
    assert abs(h45.HRC[0] - h41.HRC[0]) < 1.0                 # quenched-end gap closed
    assert 18.0 <= h45.HRC[-1] <= 24.0                        # tail lifted onto scale (~published 22)
    assert h41.HV[-1] - h45.HV[-1] > 200.0                    # still the dramatic divergence


# =========================================================================== #
# Phase 3b — tempering (Hollomon–Jaffe) + the strength/toughness trade-off.
#
# The non-circularity discipline (advisor), mirroring 2c/2b: VALIDATE the parameter's
# *form* (the time–temperature equivalence — convention-independent; the monotone
# softening; the bound between two INDEPENDENTLY-anchored endpoints) tightly, and treat
# the value of C_hj (a cited constant) and the softening MAGNITUDE (the two P breakpoints)
# as CALIBRATED — asserted only with loose sanity bands, not dressed as a validation.
# =========================================================================== #
def _equal_hollomon_jaffe_pair(T1=540.0, t1=1.0, T2=480.0, C_hj=prop.HJ_CONSTANT):
    """Two tempers ``(T °C, t h)`` constructed to share the *same* Hollomon–Jaffe P exactly."""
    P1 = prop.hollomon_jaffe_parameter(T1, t1, C_hj=C_hj)
    t2 = 10.0 ** (P1 / (T2 + ABS_ZERO) - C_hj)               # invert P = T_K·(C_hj + log10 t)
    return (T1, t1), (T2, t2), P1


def test_hollomon_jaffe_parameter_form():
    # The parameter's FORM (the validated part): P = T_K·(C_hj + log10 t), exact at a point,
    # and rising with BOTH temperature and time (more of either → more tempering).
    T, t = 500.0, 2.0
    assert prop.hollomon_jaffe_parameter(T, t) == pytest.approx((T + ABS_ZERO) * (prop.HJ_CONSTANT + math.log10(t)))
    assert prop.hollomon_jaffe_parameter(600.0, 1.0) > prop.hollomon_jaffe_parameter(400.0, 1.0)  # ↑ with T
    assert prop.hollomon_jaffe_parameter(500.0, 10.0) > prop.hollomon_jaffe_parameter(500.0, 1.0)  # ↑ with t
    with pytest.raises(ValueError):
        prop.hollomon_jaffe_parameter(500.0, 0.0)            # t must be > 0 (log10)


def test_tempering_time_temperature_equivalence():
    # THE HEADLINE analytical leg (the whole point of the parameter): two (T, t) on the same
    # Hollomon–Jaffe P soften to the SAME tempered hardness — a low-T/long-t temper trades for
    # a high-T/short-t one. It is CONVENTION-INDEPENDENT: holds for any carbon and any C_hj
    # (the function depends on (T, t) only through P), so vary both and it must still hold.
    for C in (0.30, 0.45, 0.80):
        for C_hj in (18.0, prop.HJ_CONSTANT, 22.0):
            (T1, t1), (T2, t2), P1 = _equal_hollomon_jaffe_pair(C_hj=C_hj)
            assert prop.hollomon_jaffe_parameter(T2, t2, C_hj=C_hj) == pytest.approx(P1)
            h1 = prop.tempered_martensite_HV(C, T1, t1, C_hj=C_hj)
            h2 = prop.tempered_martensite_HV(C, T2, t2, C_hj=C_hj)
            assert h1 == pytest.approx(h2, abs=1e-6)


def test_tempered_hardness_monotone_in_temperature_and_time():
    # Tempered hardness only ever FALLS with more tempering — strictly decreasing in both T
    # (fixed t) and t (fixed T) across the active window. (Ranges chosen so g is unclamped.)
    C = 0.45
    by_T = [prop.tempered_martensite_HV(C, T, 1.0) for T in np.linspace(200.0, 650.0, 12)]
    by_t = [prop.tempered_martensite_HV(C, 400.0, t) for t in np.linspace(0.1, 100.0, 12)]
    assert np.all(np.diff(by_T) < 0)
    assert np.all(np.diff(by_t) < 0)


def test_tempered_hardness_bounded_by_independent_endpoints():
    # The bound that keeps the model non-circular: tempered hardness lives BETWEEN two
    # INDEPENDENTLY-anchored endpoints — the Phase-3a as-quenched martensite (ceiling) and
    # the ferrite-pearlite/spheroidite floor — recovering each in its limit. A negligible
    # temper (P below onset) returns the as-quenched value EXACTLY (the seam); a heavy
    # over-temper (P above the breakpoint) returns the floor exactly.
    for C in (0.20, 0.45, 0.80):
        aq = prop.vickers_martensite(C)
        floor = prop.vickers_ferrite_pearlite(C)
        # the seam: a sub-onset temper (100 °C/1 h) is byte-for-byte the as-quenched model.
        assert prop.tempered_martensite_HV(C, 100.0, 1.0) == aq
        # a deep over-temper (750 °C/10 h) bottoms out exactly on the floor.
        assert prop.tempered_martensite_HV(C, 750.0, 10.0) == pytest.approx(floor, abs=1e-9)
        # everything in between is bounded by the two anchors.
        for T in (250.0, 400.0, 550.0, 650.0):
            hv = prop.tempered_martensite_HV(C, T, 1.0)
            assert floor - 1e-9 <= hv <= aq + 1e-9


def test_alloy_steel_resists_tempering_softening():
    # EMERGENT (not a fitted term): threading comp through BOTH endpoints makes an alloy
    # steel start harder AND keep a higher floor — so it stays harder than a plain steel of
    # the same carbon at every temper. The real alloy temper-resistance, for free.
    for T in (300.0, 450.0, 600.0):
        plain = prop.tempered_martensite_HV(0.40, T, 1.0)
        alloy = prop.tempered_martensite_HV(0.40, T, 1.0, comp=COMP_4140)
        assert alloy > plain


def test_tempered_hardness_plain_carbon_self_consistency():
    # SELF-CONSISTENCY (not the benchmark leg): the two P breakpoints were CALIBRATED to this
    # plain-carbon 0.4 %C 1 h response (Grange/ASM tempering charts) — high-50s HRC as-quenched,
    # low-40s at 400 °C, ~25 HRC band by 600 °C — so asserting it back is a regression guard on
    # the calibration, not an independent validation (the 4140 test below is the genuine leg).
    # Held loosely the way the 1045 knee position was; in HV to dodge the nan-at-HRC-floor edge.
    assert 555.0 <= prop.tempered_martensite_HV(0.40, 200.0, 1.0) <= 605.0   # ~579 HV (~54 HRC)
    assert 400.0 <= prop.tempered_martensite_HV(0.40, 400.0, 1.0) <= 455.0   # ~425 HV (~43 HRC)
    assert 250.0 <= prop.tempered_martensite_HV(0.40, 600.0, 1.0) <= 300.0   # ~272 HV (~25 HRC)


def test_benchmark_4140_tempering_response_is_a_prediction():
    # THE BENCHMARK LEG (advisor): 4140's tempering response is NON-CIRCULAR — the P breakpoints
    # were calibrated only to *plain-carbon* data, and 4140's curve falls out of the plain-carbon
    # master curve + the *independently anchored* (Maynier, Phase-3a) comp deltas threaded through
    # BOTH endpoints. Nothing here was fit to 4140 tempering data, so matching its published 1 h
    # response (ASM/Bhadeshia tempering charts: ~57 HRC as-quenched → ~55 @200 °C → ~45 @400 °C →
    # ~33 @600 °C) is a genuine prediction — the inverse of Phase-2b's "calibrate 4140, 1045 falls
    # out". Loose ±~4 HRC bands (the benchmark's own inter-source spread + the recall caveat).
    hrc = lambda T: prop.vickers_to_rockwell_c(prop.tempered_martensite_HV(0.40, T, 1.0, comp=COMP_4140))
    assert 50.0 <= hrc(200.0) <= 58.0                        # low-temp temper, barely softened
    assert 41.0 <= hrc(400.0) <= 49.0                        # mid temper (~published 45 HRC)
    assert 28.0 <= hrc(600.0) <= 37.0                        # high temper (~published 33 HRC)
    assert hrc(200.0) > hrc(400.0) > hrc(600.0)              # and monotone, as published


def test_tensile_strength_matches_iso18265_table():
    # Strength via the ISO 18265 / ASTM A370 steel hardness→UTS conversion, pinned to table
    # points (~3.3·HV across the band) — accuracy, not just monotonicity.
    for HV, MPa in [(300.0, 950.0), (400.0, 1290.0), (500.0, 1660.0)]:
        assert prop.tensile_strength_MPa(HV) == pytest.approx(MPa, abs=1.0)
    assert 3.0 <= prop.tensile_strength_MPa(400.0) / 400.0 <= 3.5      # the ≈3.3·HV rule of thumb
    HV = np.linspace(prop.RELIABLE_UTS_HV_MIN, prop.RELIABLE_UTS_HV_MAX, 50)
    assert np.all(np.diff(prop.tensile_strength_MPa(HV)) > 0)          # monotone in the band


def test_tensile_strength_nan_outside_validity_band():
    # The correlation degrades above ~550 HV — untempered martensite is exactly where it is
    # least valid — so the table returns nan there (and below ~150 HV), the honest "out of
    # range", not a clamp. A fully-martensitic 0.4 %C quenched end (~616 HV) is off-band.
    assert np.isnan(prop.tensile_strength_MPa(100.0))                 # too soft for the table
    assert np.isnan(prop.tensile_strength_MPa(700.0))                 # untempered-martensite range
    assert np.isnan(prop.tensile_strength_MPa(prop.vickers_martensite(0.40)))  # ~616 HV → off-band
    arr = prop.tensile_strength_MPa(np.array([100.0, 400.0, 700.0]))
    assert np.isnan(arr[0]) and np.isfinite(arr[1]) and np.isnan(arr[2])


def test_strength_toughness_trade_off():
    # The Phase-3b payoff: strength and toughness move in OPPOSITE directions as a steel is
    # tempered. toughness_index is monotone-decreasing in hardness (a relative direction,
    # not a Charpy J); over a tempering sweep, hardness and strength fall while toughness
    # rises — the trade-off tempering exploits.
    assert prop.toughness_index(200.0) == pytest.approx(1.0)          # soft → fully tough
    assert prop.toughness_index(600.0) == pytest.approx(0.0)          # hard → brittle
    assert prop.toughness_index(400.0) == pytest.approx(0.5)          # linear between, clamped
    tough = prop.toughness_index(np.linspace(200.0, 600.0, 20))
    assert np.all(np.diff(tough) < 0)                                 # ↓ with hardness
    # A real tempering sweep (T over a range where UTS is in-band): hardness ↓, so strength ↓
    # and toughness ↑ — the anti-correlation, the headline trade-off.
    HV = np.array([prop.tempered_martensite_HV(0.45, T, 1.0) for T in np.linspace(300.0, 650.0, 10)])
    strength = prop.tensile_strength_MPa(HV)
    toughness = prop.toughness_index(HV)
    assert np.all(np.diff(HV) < 0)                                    # tempering softens
    assert np.all(np.diff(strength) < 0)                             # strength falls
    assert np.all(np.diff(toughness) > 0)                            # toughness rises (opposite)
