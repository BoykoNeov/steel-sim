"""Phase-2b validation: the alloy hardenability shift of the TTT C-curve (Steel plan §3).

Phase 2b adds *hardenability* to the kinetics: Mn/Cr/Mo slide the whole C-curve to
longer times (right), so martensite survives deeper into a quenched section. The
model is a single multiplicative time-shift ``M`` (:func:`hardenability_factor`,
:func:`ccurve_for_steel`). The triad, kept separate so each leg anchors to its own
published data rather than co-fitting one curve (the discipline plan §3 calls for):

* **Analytical / structural** — ``M = 1`` *exactly* at the reference composition (so a
  bare ``CCurve`` and the four-curves demo stay byte-identical); the shift is a clean
  multiplicative scaling of ``τ`` that preserves the C-curve *shape* and nose
  *temperature* (only the time axis moves); ``M`` rises with each of Mn/Cr/Mo and ranks
  their potencies the Grossmann way (Cr, Mo ≫ Ni per wt%).
* **Benchmark / calibration** — the *magnitude* is calibrated to a defensible ≈ 8×
  shift for **4140**, consistent with its deep-hardening TTT band (nose shifted ~an
  order of magnitude). That absolute factor is a calibrated estimate, range-checked —
  *not* a fit to one cited diagram (Phase 2c's published Jominy curve pins it). Under
  that one scale, **1045** falls out ≈ identity (shallow-hardening) — a genuine
  *non-circular prediction*, not a second fit.
* **Consequence (integration through the frozen thermal field)** — fed the same Jominy
  bar's cooling histories (:mod:`jominy`), 4140 stays martensitic *much deeper* than
  1045, while both harden identically at the quenched end. This is the plan's "share
  the quenched-end hardness, diverge with distance" — the divergence validates the
  hardenability shift in isolation (the quenched-end hardness model is Phase 2c).
"""
import numpy as np
import pytest

from projects.steel import fe_c, pathint
from projects.steel.kinetics import (
    CCurve, andrews_Ms,
    hardenability_factor, ccurve_for_steel,
    REFERENCE_COMPOSITION, HARDENABILITY_SCALE,
)
from projects.steel.jominy import solve_thermal_field, JominyBar, jominy_distances

EXACT = dict(rel=0.0, abs=1e-12)

# The two benchmark steels (same compositions as the Andrews Mₛ benchmark, + Si): a
# medium-carbon plain steel and a low-alloy deep-hardening one, both ≈ 0.4 % C.
STEEL_1045 = dict(Mn=0.75, Si=0.22)
STEEL_4140 = dict(Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)


# --------------------------------------------------------------------------- #
# Analytical / structural: identity at the reference, and a clean shape-preserving shift
# --------------------------------------------------------------------------- #
def test_reference_composition_is_exact_identity():
    # M = 1 *exactly* at the calibrated reference steel (1080, ~0.7 % Mn). This is the
    # byte-identity guarantee: ccurve_for_steel at the reference, and every existing
    # bare CCurve (tau_factor defaults to 1.0), are unchanged from the Phase-1 model.
    assert hardenability_factor(**REFERENCE_COMPOSITION) == 1.0
    assert hardenability_factor(Mn=0.70, Si=0.20) == 1.0


def test_tau_factor_scales_tau_and_default_is_identity():
    # The shift is exactly a multiplier on τ(T): a CCurve with tau_factor = M returns
    # M × the reference curve's τ at every temperature. tau_factor defaults to 1.0
    # (×1.0 is exact in IEEE-754), so a bare CCurve is byte-identical to Phase 1.
    base = CCurve(Ms=300.0)
    shifted = CCurve(Ms=300.0, tau_factor=8.0)
    assert CCurve(Ms=300.0).tau_factor == 1.0
    for T in (650.0, 560.0, 500.0, 400.0):
        assert shifted.tau(T) == pytest.approx(8.0 * base.tau(T), rel=1e-12)


def test_shift_preserves_nose_temperature_and_scales_nose_time():
    # A constant multiplier can't move argmin τ(T): with Mₛ (hence the scan window)
    # held fixed, the shifted nose sits at the *same temperature* and its time is
    # scaled by exactly the factor — the C-curve slides right without changing shape.
    base = CCurve(Ms=300.0)
    shifted = CCurve(Ms=300.0, tau_factor=8.0)
    T_base, t_base = base.nose(X=0.01)
    T_shift, t_shift = shifted.nose(X=0.01)
    assert T_shift == T_base                          # identical scan grid → exact
    assert t_shift == pytest.approx(8.0 * t_base, rel=1e-12)


def test_factor_rises_with_alloying_and_ranks_potencies():
    # Above the reference, every hardenability element pushes M up; below it (leaner
    # Mn, no Si) M < 1 (a left shift — shallower hardening). And the Grossmann ranking:
    # Cr and Mo are far more potent per wt% than Ni (the *relative* potencies, which is
    # all Grossmann is trusted for here).
    ref = hardenability_factor(Mn=0.70, Si=0.20)      # == 1.0
    assert hardenability_factor(Mn=0.70, Si=0.20, Cr=0.5) > ref
    assert hardenability_factor(Mn=0.70, Si=0.20, Mo=0.5) > ref
    assert hardenability_factor(Mn=1.20, Si=0.20) > ref
    assert hardenability_factor(Mn=0.30) < ref         # leaner than reference → left
    m_cr = hardenability_factor(Mn=0.70, Si=0.20, Cr=1.0)
    m_mo = hardenability_factor(Mn=0.70, Si=0.20, Mo=1.0)
    m_ni = hardenability_factor(Mn=0.70, Si=0.20, Ni=1.0)
    assert m_cr > m_ni and m_mo > m_ni                 # Cr, Mo ≫ Ni per wt%


def test_ccurve_for_steel_bundles_Teq_Ms_and_shift():
    # The factory wires the three composition-dependent pieces together: A₁ ceiling,
    # Andrews Mₛ, and the hardenability shift M.
    cc = ccurve_for_steel(0.40, **STEEL_4140)
    assert cc.T_eq == fe_c.A1()
    assert cc.Ms == pytest.approx(andrews_Ms(0.40, Mn=0.90, Cr=1.0, Mo=0.20))
    assert cc.tau_factor == pytest.approx(hardenability_factor(**STEEL_4140))


# --------------------------------------------------------------------------- #
# Benchmark: 4140 lands in its published TTT band; 1045 ≈ identity (a check, not a fit)
# --------------------------------------------------------------------------- #
def test_benchmark_4140_nose_in_published_band_and_1045_near_identity():
    # 4140 is a deep-hardening low-alloy steel, its pearlite nose ~an order of magnitude
    # later than plain-carbon 1080 (its published TTT band). The scale is *calibrated* to
    # a defensible ~8× there (range-checked, not fit to one diagram); 1045 (shallow-
    # hardening, ~0.75 % Mn only) is then a non-circular prediction — it must come out
    # near identity on its own, which is the real check this leg makes.
    m1045 = hardenability_factor(**STEEL_1045)
    m4140 = hardenability_factor(**STEEL_4140)
    assert 0.9 <= m1045 <= 1.4                         # ≈ identity (predicted, not fit)
    assert 4.0 <= m4140 <= 16.0                        # the calibrated deep-hardening band

    base = CCurve(Ms=andrews_Ms(0.80))                 # plain-carbon 1080 reference
    cc4140 = ccurve_for_steel(0.40, **STEEL_4140)
    T_base, t_base = base.nose(X=0.01)
    T_4140, t_4140 = cc4140.nose(X=0.01)
    assert 3.0 <= t_4140 <= 30.0                       # published 4140 pearlite-nose band (s)
    assert 4.0 <= t_4140 / t_base <= 16.0              # rightward shift vs plain carbon
    assert abs(T_4140 - T_base) < 5.0                  # nose T ~unchanged (shape-preserving)


def test_scale_constant_is_the_single_calibration_knob():
    # A regression pin documenting that the magnitude is one number (not three co-fit
    # knobs): the 4140 factor is the Grossmann ratio raised to HARDENABILITY_SCALE.
    # If the scale or the Grossmann coefficients drift, this catches it.
    assert HARDENABILITY_SCALE == pytest.approx(1.13, **EXACT)
    assert hardenability_factor(**STEEL_4140) == pytest.approx(7.94, abs=0.1)


# --------------------------------------------------------------------------- #
# Consequence: the 4140-vs-1045 Jominy divergence through the frozen thermal field
# --------------------------------------------------------------------------- #
def _martensite_vs_distance(ccurve, field, distances):
    """Martensite fraction at each Jominy distance — that cell's (t,T) history → pathint."""
    out = np.empty(distances.size)
    for k, dd in enumerate(distances):
        j = int(np.argmin(np.abs(field.x - dd)))       # nearest cell (0.5 mm grid)
        t, T = field.history(j)
        out[k] = pathint.transform_along_path(t, T, ccurve).martensite
    return out


def test_4140_hardens_deeper_than_1045_along_the_jominy_bar():
    cc1045 = ccurve_for_steel(0.45, **STEEL_1045)
    cc4140 = ccurve_for_steel(0.40, **STEEL_4140)
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)                            # 1.6 .. 25.4 mm
    m1045 = _martensite_vs_distance(cc1045, f, d)
    m4140 = _martensite_vs_distance(cc4140, f, d)

    # (1) Shared quenched end: both fully harden where the quench is fierce (≤ 3 mm) —
    # the common anchor the Phase-2c quenched-end hardness model will validate.
    near = d <= 0.0032
    assert np.all(m1045[near] > 0.85) and np.all(m4140[near] > 0.85)

    # (2) The alloy steel is at least as hardenable at *every* depth (M ≥ 1 ⇒ the
    # right-shifted curve is never easier to transform diffusionally).
    assert np.all(m4140 >= m1045 - 1e-9)

    # (3) The divergence: by mid-bar the plain steel has lost to pearlite while the
    # alloy steel is still essentially martensitic — the hardenability gap, in isolation.
    mid = int(np.argmin(np.abs(d - 0.0127)))            # ~12.7 mm (½ inch)
    assert m1045[mid] < 0.2
    assert m4140[mid] > 0.6

    # (4) Deep hardening: 4140 still substantially martensitic at the far read point,
    # where 1045 is gone entirely.
    assert m4140[-1] > 0.4 and m1045[-1] < 0.05
