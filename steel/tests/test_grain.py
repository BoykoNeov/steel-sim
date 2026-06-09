"""Phase-5a validation: austenite grain growth + ASTM E112 bookkeeping.

5a is the foundation of Phase 5 (grain size & Hall–Petch — steel-production.md §12). Its
triad, in the project's three-leg shape:

* **Analytic limit ("recover the constant").** The growth law ``Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t``
  is *linear in t* by construction, so ``(Dᵐ − D₀ᵐ)/t`` is constant (the exact structure),
  the power-law asymptote ``D ∝ t^(1/m)`` holds for ``D ≫ D₀``, and the input ``Q`` is
  recovered from two temperatures (the grain-growth analogue of 1c's Avrami round-trip). The
  ASTM E112 ``G ↔ d`` pair round-trips exactly.
* **Dissipative-direction invariant (the rigor leg — grain growth has no mass-conservation
  analogue).** Growth is monotone (``D`` non-decreasing in t *and* T), the rate ``dD/dt`` is
  ``≥ 0`` and *decreasing* in t (the curvature driving force falls as grains coarsen) — a
  one-way direction, the dissipative cousin of an energy balance.
* **Benchmark — the teeth are a HOLDOUT.** Fit the kinetic constants on the 900 & 1200 °C
  rows of the cited S960MC table (with ``Q`` held at its cited value) and *predict* the
  held-out 1000 & 1100 °C rows → within ~16 %. A genuine cross-temperature prediction that
  could have missed. The full-table reproduction with the locked module constants is asserted
  only *loosely* (grain-growth fits are inherently scattered, and ``Q`` is weakly determined
  by this data — see grain-growth-source). This is the *only* genuinely falsifiable leg of
  Phase 5; 5c's sign-opposition is a by-construction demonstration, not teeth.
"""
import math

import numpy as np
import pytest
from scipy.optimize import least_squares

from projects.steel import grain
from projects.steel.kinetics import R_GAS, ABS_ZERO


# --------------------------------------------------------------------------- #
# Analytic limit — recover the constant
# --------------------------------------------------------------------------- #
def test_zero_hold_returns_initial_size_exactly():
    # The seam: no hold ⇒ the grain size entering the hold, byte-for-byte.
    assert grain.austenite_grain_size(1000.0, 0.0, d0=12.0) == pytest.approx(12.0, abs=0.0)


def test_growth_law_is_exactly_linear_in_time():
    # Dᵐ − D₀ᵐ = K₀·exp(−Q/RT)·t  ⇒  (Dᵐ − D₀ᵐ)/t is constant in t (the conserved structure).
    d0, m = grain.GROWTH_D0, grain.GROWTH_M
    slopes = []
    for t in (0.5, 1.0, 2.0, 4.0, 8.0):
        D = grain.austenite_grain_size(1100.0, t, d0=d0)
        slopes.append((D ** m - d0 ** m) / t)
    assert np.allclose(slopes, slopes[0], rtol=1e-12)


def test_power_law_asymptote_d_proportional_t_to_1_over_m():
    # For D ≫ D₀ the initial size drops out and D ∝ t^(1/m): doubling t multiplies D by 2^(1/m).
    d0 = 0.01  # tiny seed so Dᵐ ≫ D₀ᵐ across the window
    t1, t2 = 100.0, 200.0
    D1 = grain.austenite_grain_size(1100.0, t1, d0=d0)
    D2 = grain.austenite_grain_size(1100.0, t2, d0=d0)
    assert D2 / D1 == pytest.approx(2.0 ** (1.0 / grain.GROWTH_M), rel=1e-6)


def test_arrhenius_Q_recovered_from_two_temperatures():
    # ln[(Dᵐ−D₀ᵐ) ratio] / (1/T1 − 1/T2) = −Q/R  → recover the input Q (the round-trip leg).
    d0, m = grain.GROWTH_D0, grain.GROWTH_M
    T1, T2, t = 950.0, 1150.0, 2.0
    g1 = grain.austenite_grain_size(T1, t, d0=d0) ** m - d0 ** m
    g2 = grain.austenite_grain_size(T2, t, d0=d0) ** m - d0 ** m
    inv = 1.0 / (T1 + ABS_ZERO) - 1.0 / (T2 + ABS_ZERO)
    Q_recovered = -R_GAS * math.log(g1 / g2) / inv
    assert Q_recovered == pytest.approx(grain.GROWTH_Q, rel=1e-9)


def test_astm_grain_size_number_round_trips_exactly():
    for G in (1.0, 4.5, 8.0, 10.0, 12.0):
        d = grain.grain_diameter_um(G)
        assert grain.astm_grain_size_number(d) == pytest.approx(G, abs=1e-12)


def test_astm_anchors_match_textbook():
    # The two universally-tabulated ASTM E112 anchors.
    assert grain.grain_diameter_um(1.0) == pytest.approx(254.0, rel=2e-3)
    assert grain.grain_diameter_um(8.0) == pytest.approx(22.5, rel=5e-3)


# --------------------------------------------------------------------------- #
# Dissipative-direction invariant — growth is one-way, the rate decays
# --------------------------------------------------------------------------- #
def test_grain_size_monotone_in_time_and_temperature():
    times = np.linspace(0.0, 10.0, 40)
    sizes = [grain.austenite_grain_size(1050.0, t) for t in times]
    assert np.all(np.diff(sizes) >= -1e-12)                       # never shrinks with time
    temps = np.linspace(850.0, 1250.0, 40)
    sizes_T = [grain.austenite_grain_size(T, 1.0) for T in temps]
    assert np.all(np.diff(sizes_T) >= -1e-12)                     # never shrinks with temperature


def test_growth_rate_nonnegative_and_decelerating():
    rates = [grain.grain_growth_rate(1100.0, t) for t in (0.5, 1.0, 2.0, 4.0, 8.0)]
    assert all(r >= 0.0 for r in rates)                          # one-way (dD/dt ≥ 0)
    assert np.all(np.diff(rates) < 0.0)                          # decelerates as grains coarsen


def test_growth_rate_rises_with_temperature():
    # The Arrhenius driving force, read at the SAME grain size (t = 0 ⇒ D = D₀ for both), so the
    # comparison is the rate *constant*, not confounded by the hotter sample's already-coarser
    # grain at a later instant. ~69× over 1000 → 1200 °C.
    assert grain.grain_growth_rate(1200.0, 0.0) > 10.0 * grain.grain_growth_rate(1000.0, 0.0)


# --------------------------------------------------------------------------- #
# Benchmark — the teeth: a cross-temperature HOLDOUT of the cited S960MC data
# --------------------------------------------------------------------------- #
def _fit_constants(temp_C, time_h, grain_um, Q=grain.GROWTH_Q):
    """Refit (log10 K0, D0, m) to a grain-size table with Q held at its cited value."""
    Tg, tg = np.meshgrid(temp_C + ABS_ZERO, time_h, indexing="ij")
    Tf, tf, Df = Tg.ravel(), tg.ravel(), grain_um.ravel()

    def resid(p):
        logK0, D0, m = p
        return (D0 ** m + 10.0 ** logK0 * np.exp(-Q / (R_GAS * Tf)) * tf) ** (1.0 / m) - Df

    sol = least_squares(resid, [19.0, 14.0, 4.2])
    logK0, D0, m = sol.x
    return 10.0 ** logK0, D0, m


def test_holdout_predicts_unseen_temperatures():
    # Fit on the EXTREME temperatures (900 & 1200 °C), predict the held-out middle rows.
    fit_idx, hold_idx = [0, 3], [1, 2]
    K0, D0, m = _fit_constants(
        grain.S960MC_TEMP_C[fit_idx], grain.S960MC_TIME_H, grain.S960MC_GRAIN_UM[fit_idx],
    )
    err_pct = []
    for i in hold_idx:
        T = grain.S960MC_TEMP_C[i]
        for j, t in enumerate(grain.S960MC_TIME_H):
            pred = grain.austenite_grain_size(T, t, d0=D0, m=m, K0=K0)
            measured = grain.S960MC_GRAIN_UM[i, j]
            err_pct.append(abs(pred - measured) / measured)
    err_pct = np.array(err_pct)
    # A genuine prediction of unseen temperatures — could have missed; lands within ~16 %.
    assert err_pct.max() < 0.20
    assert err_pct.mean() < 0.10


def test_locked_constants_reproduce_full_table_loosely():
    # The shipped module constants vs the whole cited table — asserted LOOSELY (scattered data).
    abs_err, pct_err = [], []
    for i, T in enumerate(grain.S960MC_TEMP_C):
        for j, t in enumerate(grain.S960MC_TIME_H):
            pred = grain.austenite_grain_size(T, t)
            measured = grain.S960MC_GRAIN_UM[i, j]
            abs_err.append(abs(pred - measured))
            pct_err.append(abs(pred - measured) / measured)
    assert np.mean(abs_err) < 4.0          # mean abs error a few µm on 13–111 µm grains
    assert np.max(pct_err) < 0.22          # worst case on the smallest (900 °C) grains


def test_overheating_coarsens_grain_the_teaching_point():
    # The §12 payoff in 5a terms: a hotter austenitize gives a markedly coarser PAGS.
    fine = grain.austenite_grain_size(900.0, 1.0)
    coarse = grain.austenite_grain_size(1200.0, 1.0)
    assert coarse > 3.0 * fine
    # ...and a coarser grain is a smaller ASTM number (G falls as d rises).
    assert grain.astm_grain_size_number(coarse) < grain.astm_grain_size_number(fine)


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        grain.austenite_grain_size(1000.0, -1.0)
    with pytest.raises(ValueError):
        grain.austenite_grain_size(1000.0, 1.0, d0=0.0)
    with pytest.raises(ValueError):
        grain.austenite_grain_size(-300.0, 1.0)          # below absolute zero
    with pytest.raises(ValueError):
        grain.astm_grain_size_number(0.0)


# =========================================================================== #
# Phase 5b — the Pickering pair: Hall–Petch yield + Cottrell–Petch DBTT
# =========================================================================== #
# Two laws of the same Hall–Petch form, OPPOSITE grain-size signs (steel-production.md §12).
# Per the plan's non-circularity split, almost everything here is *by construction* or
# *calibrated*, NOT a benchmark with teeth (those live in 5a's grain-growth holdout):
#   * the d^(−½) linearity of both laws is exact by construction;
#   * the mm↔µm and N(wt%) unit conversions are registry checks (the registered trap);
#   * the sign-opposition / lever comparison is a DEMONSTRATION that passes by construction
#     (both Pickering equations are cited — no holdout could falsify it);
#   * a real plain-carbon steel landing in its published (σ_y, DBTT) band is a *loose,
#     in-distribution* sanity check (Pickering is a general correlation across such steels).
# The one web-confirmed external anchor is the textbook "10→1 µm lowers DBTT by ~250 K".

# A representative clean mild steel for the in-distribution anchors (≈ a 1010/1018 ferrite).
_MILD = {"Mn": 0.45, "Si": 0.20}


# --------------------------------------------------------------------------- #
# Exact-by-construction: both laws are affine in d^(−½) with the cited slopes
# --------------------------------------------------------------------------- #
def test_yield_is_exactly_linear_in_d_to_the_minus_half():
    # σ_y(d1) − σ_y(d2) = k_y·(d1^(−½) − d2^(−½)) with k_y = YIELD_KY_MM (mm units), holding
    # composition/pearlite/N fixed — the Hall–Petch structure, exact.
    kw = dict(comp=_MILD, f_pearlite=0.3, N_free_pct=0.004)
    for d1, d2 in [(5.0, 50.0), (10.0, 20.0), (8.0, 200.0)]:
        dy = grain.hall_petch_yield_MPa(d1, **kw) - grain.hall_petch_yield_MPa(d2, **kw)
        expected = grain.YIELD_KY_MM * ((d1 / 1000.0) ** -0.5 - (d2 / 1000.0) ** -0.5)
        assert dy == pytest.approx(expected, rel=1e-12)


def test_dbtt_is_exactly_linear_in_d_to_the_minus_half_opposite_sign():
    # DBTT(d1) − DBTT(d2) = −k_T·(d1^(−½) − d2^(−½)): same form, OPPOSITE sign to yield.
    kw = dict(comp=_MILD, f_pearlite=0.3, N_free_pct=0.004)
    for d1, d2 in [(5.0, 50.0), (10.0, 20.0), (8.0, 200.0)]:
        dT = grain.cottrell_petch_dbtt_C(d1, **kw) - grain.cottrell_petch_dbtt_C(d2, **kw)
        expected = -grain.ITT_KT_MM * ((d1 / 1000.0) ** -0.5 - (d2 / 1000.0) ** -0.5)
        assert dT == pytest.approx(expected, rel=1e-12)


def test_bare_form_is_the_two_constant_ferrite_hall_petch_limit():
    # comp=None, no pearlite, no free N ⇒ σ_y = σ₀ + k_y·d^(−½) exactly (the teaching limit).
    d = 12.0
    expected = grain.YIELD_SIGMA0 + grain.YIELD_KY_MM * (d / 1000.0) ** -0.5
    got = grain.hall_petch_yield_MPa(d, comp=None, f_pearlite=0.0, N_free_pct=0.0)
    assert got == pytest.approx(expected, rel=1e-12)


# --------------------------------------------------------------------------- #
# Registry — the unit traps (µm↔mm grain size, and N_free in wt%)
# --------------------------------------------------------------------------- #
def test_grain_coefficient_unit_conversion_mm_to_m():
    # The cited k_y = 17.4 MPa·mm^(−½) is the plan's ≈0.6 MPa·√m once put in SI (d in metres):
    # 17.4 / √1000 ≈ 0.55 MPa·m^(−½). The registered mm-vs-m trap.
    assert grain.YIELD_KY_MM / math.sqrt(1000.0) == pytest.approx(0.55, abs=0.01)


def test_pure_ferrite_grain_term_at_10um_is_174_MPa():
    # Bare ferrite at d = 10 µm = 0.01 mm: σ_y = 53.9 + 17.402·(0.01)^(−½) = 53.9 + 174.0.
    got = grain.hall_petch_yield_MPa(10.0, comp=None, f_pearlite=0.0, N_free_pct=0.0)
    assert got == pytest.approx(grain.YIELD_SIGMA0 + 174.02, abs=0.1)


def test_grain_refinement_10_to_1_um_lowers_dbtt_by_about_250K():
    # The one WEB-CONFIRMED external anchor (textbook): refining 10 µm → 1 µm drops the DBTT
    # by ~250 K. −11.5·[(0.001)^(−½) − (0.01)^(−½)] = −11.5·(31.62 − 10) = −248.7 °C. Holding
    # composition fixed, only the grain term moves, so this is the −11.5 coefficient itself.
    kw = dict(comp=_MILD, f_pearlite=0.2)
    drop = grain.cottrell_petch_dbtt_C(1.0, **kw) - grain.cottrell_petch_dbtt_C(10.0, **kw)
    assert drop == pytest.approx(-248.7, abs=1.0)


def test_free_nitrogen_is_wt_percent_under_a_square_root():
    # N_free enters both laws as √(wt%): a wt%/ppm mix-up is a ~√1000 error. At 0.005 wt% the
    # yield bump is 354.2·√0.005 ≈ 25 MPa and the DBTT bump is 700·√0.005 ≈ 49.5 °C.
    base_y = grain.hall_petch_yield_MPa(15.0, comp=_MILD, N_free_pct=0.0)
    bump_y = grain.hall_petch_yield_MPa(15.0, comp=_MILD, N_free_pct=0.005) - base_y
    assert bump_y == pytest.approx(354.2 * math.sqrt(0.005), rel=1e-9)
    base_T = grain.cottrell_petch_dbtt_C(15.0, comp=_MILD, N_free_pct=0.0)
    bump_T = grain.cottrell_petch_dbtt_C(15.0, comp=_MILD, N_free_pct=0.005) - base_T
    assert bump_T == pytest.approx(700.0 * math.sqrt(0.005), rel=1e-9)


def test_pearlite_fraction_not_percent_at_the_interface():
    # f_pearlite is a MASS FRACTION [0,1] (fe_c convention), converted to percent internally:
    # a full 100 % pearlite raises yield by 2.0·100 and DBTT by 2.2·100, not by 2.0·1.
    dy = grain.hall_petch_yield_MPa(15.0, f_pearlite=1.0) - grain.hall_petch_yield_MPa(15.0, f_pearlite=0.0)
    assert dy == pytest.approx(grain.YIELD_K_PEARLITE * 100.0, rel=1e-9)
    dT = grain.cottrell_petch_dbtt_C(15.0, f_pearlite=1.0) - grain.cottrell_petch_dbtt_C(15.0, f_pearlite=0.0)
    assert dT == pytest.approx(grain.ITT_K_PEARLITE * 100.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# In-distribution sanity (loose) — a real plain-carbon steel lands in band
# --------------------------------------------------------------------------- #
def test_mild_steel_yield_at_10um_in_published_band():
    # A real fine-grained (10 µm) mild steel sits near ~260–290 MPa yield — the plan's
    # "≈260 MPa at 10 µm" in-distribution band (bare ferrite alone is 228; Mn/Si/N lift it).
    sigma_y = grain.hall_petch_yield_MPa(10.0, comp=_MILD, f_pearlite=0.0)
    assert 250.0 < sigma_y < 310.0


def test_fine_mild_steel_is_tough_coarse_pearlitic_is_brittle():
    # Loose direction: a fine-grained low-pearlite mild steel is ductile well below 0 °C; a
    # coarse-grained, pearlite-rich steel transitions above room temperature.
    tough = grain.cottrell_petch_dbtt_C(8.0, comp=_MILD, f_pearlite=0.1)
    brittle = grain.cottrell_petch_dbtt_C(60.0, comp=_MILD, f_pearlite=0.6)
    assert tough < 0.0 < brittle


# --------------------------------------------------------------------------- #
# The sign-opposition DEMONSTRATION (a consistency check that passes BY CONSTRUCTION —
# NOT the benchmark's teeth; both Pickering equations are cited, so nothing here can fail).
# --------------------------------------------------------------------------- #
def test_grain_refinement_is_the_lone_co_improving_lever():
    # Refine the grain (coarse → fine): yield RISES and DBTT FALLS together — the famous
    # exception to the strength↔toughness trade-off, the headline of option (b).
    coarse_d, fine_d = 60.0, 8.0
    kw = dict(comp=_MILD, f_pearlite=0.3)
    assert grain.hall_petch_yield_MPa(fine_d, **kw) > grain.hall_petch_yield_MPa(coarse_d, **kw)
    assert grain.cottrell_petch_dbtt_C(fine_d, **kw) < grain.cottrell_petch_dbtt_C(coarse_d, **kw)


def test_silicon_and_pearlite_raise_both_yield_and_dbtt():
    # The OTHER levers move yield and DBTT the SAME way (both up = embrittle while strengthen)
    # — so only the grain term's sign flip makes refinement special.
    d = 20.0
    y0 = grain.hall_petch_yield_MPa(d, comp={"Si": 0.2}, f_pearlite=0.2)
    T0 = grain.cottrell_petch_dbtt_C(d, comp={"Si": 0.2}, f_pearlite=0.2)
    # +Si
    assert grain.hall_petch_yield_MPa(d, comp={"Si": 0.6}, f_pearlite=0.2) > y0
    assert grain.cottrell_petch_dbtt_C(d, comp={"Si": 0.6}, f_pearlite=0.2) > T0
    # +pearlite
    assert grain.hall_petch_yield_MPa(d, comp={"Si": 0.2}, f_pearlite=0.5) > y0
    assert grain.cottrell_petch_dbtt_C(d, comp={"Si": 0.2}, f_pearlite=0.5) > T0


def test_yield_monotone_down_and_dbtt_monotone_up_as_grain_coarsens():
    diams = np.linspace(5.0, 120.0, 40)
    ys = [grain.hall_petch_yield_MPa(d, comp=_MILD, f_pearlite=0.3) for d in diams]
    Ts = [grain.cottrell_petch_dbtt_C(d, comp=_MILD, f_pearlite=0.3) for d in diams]
    assert np.all(np.diff(ys) < 0.0)        # coarser ⇒ weaker
    assert np.all(np.diff(Ts) > 0.0)        # coarser ⇒ more brittle (higher DBTT)


# --------------------------------------------------------------------------- #
# nan for a martensitic structure — the FP laws do not apply (HRC-nan idiom)
# --------------------------------------------------------------------------- #
def test_martensitic_structure_returns_nan_for_both():
    assert math.isnan(grain.hall_petch_yield_MPa(15.0, comp=_MILD, f_martensite=0.8))
    assert math.isnan(grain.cottrell_petch_dbtt_C(15.0, comp=_MILD, f_martensite=0.8))


def test_below_martensite_limit_is_finite():
    # A mostly-diffusional structure with a little martensite still evaluates (the threshold).
    assert math.isfinite(grain.hall_petch_yield_MPa(15.0, comp=_MILD, f_martensite=0.3))
    assert math.isfinite(grain.cottrell_petch_dbtt_C(15.0, comp=_MILD, f_martensite=0.3))


def test_pickering_invalid_inputs_raise():
    with pytest.raises(ValueError):
        grain.hall_petch_yield_MPa(0.0)                  # non-positive grain size
    with pytest.raises(ValueError):
        grain.cottrell_petch_dbtt_C(-5.0)
    with pytest.raises(ValueError):
        grain.hall_petch_yield_MPa(15.0, N_free_pct=-0.001)   # negative free N
