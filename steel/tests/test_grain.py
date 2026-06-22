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

from steel import grain
from steel import fe_c
from steel.kinetics import R_GAS, ABS_ZERO


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


# =========================================================================== #
# Phase 5c — coupling: austenitizing hold → PAGS → ferrite grain → yield + DBTT
# =========================================================================== #
# 5c is pure *reuse* — 5a's grain growth, the calibrated PAGS→ferrite ratio, fe_c's
# equilibrium pearlite, and 5b's two laws, composed. No new physics, no new teeth (those
# stay 5a's holdout). What its tests check (the plan's split):
#   * the coupling wiring (the chain composes the pieces it claims to);
#   * the co-benefit / overheating *directions* — by construction from the two Pickering signs;
#   * the yield ≤ UTS CONSISTENCY / scope-boundary cross-check (NOT a benchmark — it never
#     bites in the realistic FP window; it would only at sub-micron ferrite).
_DEMO_C = 0.18
_DEMO_COMP = {"Mn": 0.75, "Si": 0.20}     # ≈ AISI 1018, the demo steel (in-distribution)


def test_ferrite_grain_finer_than_pags_and_proportional():
    # d_α = ratio · d_PAGS, ratio < 1 (several ferrite grains nucleate per austenite grain).
    assert grain.ferrite_grain_size(40.0) == pytest.approx(40.0 * grain.FERRITE_PAGS_RATIO)
    assert grain.ferrite_grain_size(40.0) < 40.0
    assert grain.ferrite_grain_size(80.0) == pytest.approx(2.0 * grain.ferrite_grain_size(40.0))


def test_ferrite_grain_invalid_inputs_raise():
    with pytest.raises(ValueError):
        grain.ferrite_grain_size(0.0)
    with pytest.raises(ValueError):
        grain.ferrite_grain_size(40.0, ratio=0.0)


def test_coupled_chain_matches_its_pieces():
    # The wiring check: coupled_grain_properties is exactly 5a → ratio → fe_c → 5b composed.
    g = grain.coupled_grain_properties(1000.0, 1.0, _DEMO_C, comp=_DEMO_COMP)
    pags = grain.austenite_grain_size(1000.0, 1.0)
    d_ferrite = grain.ferrite_grain_size(pags)
    fp = fe_c.equilibrium_constituents(_DEMO_C).f_pearlite
    assert g.pags_um == pytest.approx(pags)
    assert g.ferrite_um == pytest.approx(d_ferrite)
    assert g.f_pearlite == pytest.approx(fp)
    assert g.yield_MPa == pytest.approx(
        grain.hall_petch_yield_MPa(d_ferrite, comp=_DEMO_COMP, f_pearlite=fp))
    assert g.dbtt_C == pytest.approx(
        grain.cottrell_petch_dbtt_C(d_ferrite, comp=_DEMO_COMP, f_pearlite=fp))


def test_coupling_co_benefit_and_overheating_penalty():
    # A cool austenitize (fine grain) vs a hot one (coarse grain): the co-benefit and its
    # converse, the overheating penalty — a by-construction demonstration.
    cool = grain.coupled_grain_properties(900.0, 1.0, _DEMO_C, comp=_DEMO_COMP)
    hot = grain.coupled_grain_properties(1200.0, 1.0, _DEMO_C, comp=_DEMO_COMP)
    assert hot.pags_um > cool.pags_um and hot.ferrite_um > cool.ferrite_um   # hotter ⇒ coarser
    # Overheating costs BOTH: weaker AND more brittle (the cautionary direction).
    assert hot.yield_MPa < cool.yield_MPa
    assert hot.dbtt_C > cool.dbtt_C
    # Equivalently, refining (cool) is the lone co-improver: stronger AND tougher.
    assert cool.yield_MPa > hot.yield_MPa and cool.dbtt_C < hot.dbtt_C


def test_demo_steel_dbtt_crosses_room_temperature():
    # The reason 1018 is the demo steel (not 1045): its coupled DBTT spans the ductile→brittle
    # crossover across the austenitizing range — tough when normalized, brittle when overheated.
    cool = grain.coupled_grain_properties(900.0, 1.0, _DEMO_C, comp=_DEMO_COMP)
    hot = grain.coupled_grain_properties(1200.0, 1.0, _DEMO_C, comp=_DEMO_COMP)
    assert cool.dbtt_C < 0.0 < hot.dbtt_C


def test_yield_below_uts_across_austenitizing_range():
    # The CONSISTENCY / scope-boundary cross-check: Pickering yield stays below the
    # hardness-derived UTS for a realistic steel across the whole austenitizing window (it
    # never bites here — yield ≈ 0.4–0.7·UTS; it would only at sub-micron ferrite).
    for T in np.linspace(850.0, 1250.0, 9):
        g = grain.coupled_grain_properties(float(T), 1.0, _DEMO_C, comp=_DEMO_COMP)
        assert g.yield_below_uts
        assert g.yield_MPa < g.uts_MPa


def test_yield_below_uts_property_logic():
    base = dict(austenitizing_T=900.0, austenitizing_t=1.0, pags_um=15.0,
                ferrite_um=7.5, f_pearlite=0.2, dbtt_C=0.0)
    assert grain.GrainProperties(yield_MPa=400.0, uts_MPa=700.0, **base).yield_below_uts is True
    assert grain.GrainProperties(yield_MPa=900.0, uts_MPa=500.0, **base).yield_below_uts is False
    # A nan UTS (carbon outside the ISO-18265 table band) ⇒ "no violation detectable", not a fail.
    assert grain.GrainProperties(yield_MPa=400.0, uts_MPa=float("nan"), **base).yield_below_uts is True


# =========================================================================== #
# Phosphorus — the signed-impurity foil (the §14 cold-shortness consequence)
# =========================================================================== #
# P closes the F2-Slice-2 deferral by threading the EXISTING Pickering laws (a propagation, consumed via
# heat_state.cold_short_check). What carries teeth vs what is flagged:
#   * TEETH — the YIELD strengthening rate, by CROSS-SOURCE coherence: Thiele–Hošek's +237 MPa/at% P,
#     converted to a wt% basis, lands inside Total Materia's independent 365–620 MPa/wt% bracket. (The
#     hardness increment 119.8 vs lit 123–125 vs theoretical 127 HV/wt% coheres within ~6%; that is the
#     tightest leg of the coherence, documented in the module — grain.py does not compute hardness from P.)
#   * FLAGGED (NOT teeth) — the DBTT slope (ITT_K_P): representative, carrying the direction/magnitude of
#     cold-shortness, the one number §14 could not cleanly pin (clean relations use GB-segregation at%).
#   * BY CONSTRUCTION — P is the signed foil: it raises BOTH yield and DBTT, the inverse of refinement.
def test_phosphorus_default_zero_is_byte_identical():
    # P_pct defaults to 0 and adds nothing — the existing suite/behaviour is untouched (the additive proof).
    for d in (8.0, 20.0, 60.0):
        assert grain.hall_petch_yield_MPa(d, comp=_MILD, f_pearlite=0.3) == \
               grain.hall_petch_yield_MPa(d, comp=_MILD, f_pearlite=0.3, P_pct=0.0)
        assert grain.cottrell_petch_dbtt_C(d, comp=_MILD, f_pearlite=0.3) == \
               grain.cottrell_petch_dbtt_C(d, comp=_MILD, f_pearlite=0.3, P_pct=0.0)


def test_phosphorus_yield_rate_in_cross_source_bracket():
    # THE TEETH (cross-source coherence). The pinned at%-basis rate, converted to a wt% basis, must land in
    # the INDEPENDENT Total Materia bracket (~365–620 MPa per wt% P). This could have missed: a wrong unit
    # basis (forgetting the ×1.803 at%→wt%) would give ~237 MPa/wt%, well below the bracket.
    eff_slope_per_wt = grain.YIELD_K_P_PER_AT * grain.AT_PCT_PER_WT_PCT_P
    assert 365.0 <= eff_slope_per_wt <= 620.0
    # the unit conversion itself: 1 wt% P ≈ 1.803 at% P (the M_Fe/M_P dilute factor — the registered trap).
    assert grain.AT_PCT_PER_WT_PCT_P == pytest.approx(1.8030, rel=1e-3)


def test_phosphorus_yield_term_linear_in_atomic_fraction():
    # The increment is YIELD_K_P_PER_AT per at% P (≈ 42.7 MPa at 0.10 wt%: 237 × 0.10 × 1.803), linear in P.
    d = 15.0
    base = grain.hall_petch_yield_MPa(d, comp=_MILD)
    bump = grain.hall_petch_yield_MPa(d, comp=_MILD, P_pct=0.10) - base
    assert bump == pytest.approx(grain.YIELD_K_P_PER_AT * 0.10 * grain.AT_PCT_PER_WT_PCT_P, rel=1e-9)
    assert grain.hall_petch_yield_MPa(d, comp=_MILD, P_pct=0.20) - base == pytest.approx(2.0 * bump, rel=1e-9)


def test_phosphorus_dbtt_slope_is_flagged_representative():
    # NOT teeth — guard only the wiring (P raises DBTT, linearly) and that the flagged slope sits inside the
    # DOCUMENTED engineering bracket ~40–78 °C per 0.1 wt% P (upper anchor 7–7.8 °C/0.01 % P, IDOT PRR-174;
    # lower ~40). The A2 sourcing gate (2026-06-22) confirmed the bulk slope is a reduced form of GB-coverage
    # physics and cannot carry teeth — the strength term (YIELD_K_P_PER_AT) does. See grain.ITT_K_P.
    d = 15.0
    base = grain.cottrell_petch_dbtt_C(d, comp=_MILD)
    bump = grain.cottrell_petch_dbtt_C(d, comp=_MILD, P_pct=0.10) - base
    assert bump == pytest.approx(grain.ITT_K_P * 0.10, rel=1e-9)
    assert 40.0 <= grain.ITT_K_P * 0.10 <= 78.0       # documented bracket, per 0.1 wt% P


def test_phosphorus_is_the_signed_foil_raises_both():
    # BY CONSTRUCTION: P raises BOTH yield AND DBTT (strengthens AND embrittles) — like Si/pearlite, the
    # OPPOSITE of the grain term. This is the §5b foil: the reason grain refinement is the lone co-improver.
    d = 20.0
    y0 = grain.hall_petch_yield_MPa(d, comp=_MILD, f_pearlite=0.2)
    T0 = grain.cottrell_petch_dbtt_C(d, comp=_MILD, f_pearlite=0.2)
    assert grain.hall_petch_yield_MPa(d, comp=_MILD, f_pearlite=0.2, P_pct=0.3) > y0
    assert grain.cottrell_petch_dbtt_C(d, comp=_MILD, f_pearlite=0.2, P_pct=0.3) > T0
    # contrast — refining the grain raises yield but LOWERS DBTT (the lone co-improver)
    assert grain.hall_petch_yield_MPa(8.0, comp=_MILD, f_pearlite=0.2) > y0
    assert grain.cottrell_petch_dbtt_C(8.0, comp=_MILD, f_pearlite=0.2) < T0


def test_coupled_grain_properties_threads_phosphorus():
    # P_pct flows through the coupling into BOTH laws; P=0 is identical to omitting it (the additive proof).
    kw = dict(comp=_DEMO_COMP)
    g0 = grain.coupled_grain_properties(950.0, 1.0, _DEMO_C, **kw)
    gP = grain.coupled_grain_properties(950.0, 1.0, _DEMO_C, P_pct=0.25, **kw)
    assert grain.coupled_grain_properties(950.0, 1.0, _DEMO_C, P_pct=0.0, **kw).dbtt_C == g0.dbtt_C
    assert gP.yield_MPa > g0.yield_MPa and gP.dbtt_C > g0.dbtt_C
    assert gP.dbtt_C == pytest.approx(
        grain.cottrell_petch_dbtt_C(gP.ferrite_um, comp=_DEMO_COMP, f_pearlite=gP.f_pearlite, P_pct=0.25))


def test_phosphorus_negative_raises():
    with pytest.raises(ValueError):
        grain.hall_petch_yield_MPa(15.0, P_pct=-0.01)
    with pytest.raises(ValueError):
        grain.cottrell_petch_dbtt_C(15.0, P_pct=-0.01)
