"""Tests for the Jominy spatial thermal model (Steel Phase 2a).

The two cleanly-analytic legs of the Phase-2 validation triad — the *analytical
limit* and the *conservation law*. (The third leg, the 1045/4140 hardness
benchmark, lands with the hardenability/hardness models in Phase 2b/2c; it needs
those calibrated sub-models, kept separate so each is anchored to its own
published data rather than co-fit to one curve.)

* **Analytical limit — the lumped-capacitance reduction.** In the thermally-thin
  regime (Biot ``< 0.1``) the spatial solve must collapse to the 0-D Newton
  cooling of :mod:`cooling`/:mod:`pathint`. Two configs pin it: (a) lateral-only
  cooling through :func:`solve_thermal_field` reproduces ``newton_cooling`` with
  ``τ_lat = ρc_p(d/4)/h`` *exactly* (the lateral half-step is the analytic
  exponential); (b) a both-ends Robin slab pins the engine's ``h_eng = h_phys/(ρc_p)``
  unit conversion against ``τ = ρc_p(L/2)/h_phys``.
* **Conservation — energy balance with two sinks.** The frozen flux identity covers
  only the conduction half-step; with the split-in lateral loss the bar has *two*
  sinks (the quenched end and the sides), so the test is
  ``Δ∫T dx = end-flux integral + lateral-loss integral`` to machine precision.

Plus qualitative checks that the cooling-rate-vs-distance curve is a recognizable
Jominy profile (monotone, fast end / slow far end, right order of magnitude vs the
standard distance↔cooling-rate equivalence).
"""
import numpy as np
import pytest

from engines.diffusion import Diffusion1D, uniform_grid, Robin
from steel import pathint
from steel.jominy import JominyBar, solve_thermal_field, jominy_distances
from steel.cooling import (
    RHO_STEEL, CP_STEEL, K_STEEL,
    lumped_time_constant, characteristic_length,
)


# --------------------------------------------------------------------------- #
# Analytical limit (1): lateral-only cooling reduces to cooling.py's 0-D model
# --------------------------------------------------------------------------- #
def test_lateral_only_lumped_matches_newton_cooling_exactly():
    # No end quench (insulated ends) + uniform lateral loss on a thin section
    # (Bi << 0.1): conduction is identity on the uniform field, and the analytic
    # lateral half-steps compose to the exact exponential -> every cell follows
    # newton_cooling with tau = rho cp (d/4) / h, *to machine precision*.
    bar = JominyBar(h_quench=0.0, h_lateral=20.0, diameter=0.006)
    assert bar.biot_lateral < 0.01
    f = solve_thermal_field(bar, T0=820.0, n_cells=40, per_decade=60)

    T_ref = pathint.newton_cooling(f.t, 820.0, bar.T_air, bar.tau_lateral)
    assert np.max(np.abs(f.T[:, 0] - T_ref)) < 1e-9          # matches the 0-D limit
    assert np.max(np.abs(f.T - f.T[:, :1])) < 1e-9           # field stays uniform in x


def test_tau_lateral_uses_cooling_module_Lc_convention():
    # The tie to cooling.py: tau_lateral == lumped_time_constant(h, L_c=d/4).
    bar = JominyBar(h_lateral=30.0, diameter=0.012)
    L_c = characteristic_length(bar.diameter, "cylinder")
    assert bar.tau_lateral == pytest.approx(lumped_time_constant(30.0, L_c))
    assert L_c == pytest.approx(bar.diameter / 4.0)


def test_insulated_sides_give_no_lateral_loss():
    # h_lateral = 0 -> tau_lateral = inf -> a pure axial-conduction experiment.
    bar = JominyBar(h_lateral=0.0)
    assert not np.isfinite(bar.tau_lateral)
    f = solve_thermal_field(bar, T0=850.0, n_cells=60, t_end=400.0, per_decade=60)
    assert f.lateral_loss == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------- #
# Analytical limit (2): the engine-Robin h = h_phys/(rho c_p) conversion
# --------------------------------------------------------------------------- #
def test_engine_robin_h_conversion_reproduces_lumped_slab():
    # A thermally-thin slab cooled by Robin on BOTH faces follows 0-D Newton
    # cooling with tau = rho cp (L/2)/h_phys -- but only if the physical h is
    # converted to the engine's alpha-form h/(rho cp). With a fine uniform dt (so
    # backward-Euler time error is negligible) and tiny Bi, the match is tight and
    # the residual is the genuine O(Bi) lumped-approximation error (it scales with
    # Bi). Using the *unconverted* h would put tau off by a factor rho cp ~ 5e6.
    rho_cp = RHO_STEEL * CP_STEEL
    alpha = K_STEEL / rho_cp
    L, h_phys, T0, T_ext = 0.02, 2.5, 800.0, 30.0
    Bi = h_phys * (L / 2.0) / K_STEEL
    assert Bi < 1e-3
    tau = rho_cp * (L / 2.0) / h_phys

    g = uniform_grid(L, 20)
    solver = Diffusion1D(g, alpha, Robin(h_phys / rho_cp, T_ext), Robin(h_phys / rho_cp, T_ext))
    dt = tau / 2000.0
    T = np.full(20, T0)
    t = 0.0
    for _ in range(4000):                 # marches to ~2 tau
        T = solver.step(T, dt)
        t += dt
    assert abs(float(T.mean()) - pathint.newton_cooling(t, T0, T_ext, tau)) < 0.5  # << 0.1% of span
    assert float(T.max() - T.min()) < 1.0          # nearly uniform (O(Bi))


# --------------------------------------------------------------------------- #
# Conservation: energy balance over the bar (two sinks: end + sides)
# --------------------------------------------------------------------------- #
def test_energy_balance_end_plus_lateral_equals_total_drop():
    # The frozen flux identity covers conduction; the lateral loss is accounted
    # separately. Their sum must equal the drop in the conserved integral int T dx,
    # to machine precision -- the Phase-2 conservation leg with the fin's two sinks.
    bar = JominyBar()
    f = solve_thermal_field(bar, T0=850.0, n_cells=120, per_decade=60)

    g = uniform_grid(bar.length, 120)
    total = lambda u: float(np.sum(u * g.widths))
    drop = total(f.T[0]) - total(f.T[-1])
    assert drop > 0.0                                  # the bar cooled
    assert f.end_loss > 0.0 and f.lateral_loss > 0.0   # both sinks active
    assert drop == pytest.approx(f.end_loss + f.lateral_loss, rel=1e-8, abs=1e-9)


def test_both_sinks_present_and_ordered():
    # The quenched end is the dominant near-field sink; both contribute. (A pure
    # check that the split bookkeeping attributes heat to each path.)
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=100, per_decade=50)
    assert f.end_loss > f.lateral_loss > 0.0


# --------------------------------------------------------------------------- #
# Qualitative: a recognizable Jominy cooling-rate-vs-distance profile
# --------------------------------------------------------------------------- #
def test_cooling_rate_monotone_decreasing_with_distance():
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=160, per_decade=80)
    cr = f.cooling_rate(700.0)
    assert np.all(np.isfinite(cr))
    # Monotone non-increasing across the standard Jominy read region (~first 50 mm,
    # the 1/16-inch sample points). The reported quantity is clean here; the raw
    # per-cell rate carries sub-0.5 % log-grid bracketing noise only in the very
    # slow far tail near the insulated tip (x > ~80 mm), which is not read.
    read = f.x <= 0.050
    assert np.all(np.diff(cr[read]) <= 1e-6)
    crd = f.cooling_rate_at(jominy_distances(32), 700.0)   # 1.6 .. ~50 mm
    assert np.all(np.diff(crd) <= 1e-9)


def test_cooling_rate_matches_published_jominy_equivalence():
    # The THERMAL benchmark (no hardness yet): the mid-range cooling-rate-vs-distance
    # must track the published Jominy distance<->rate equivalence at 700 C. Freezing
    # this *before* the Phase-2b hardenability calibration is what stops the τ-shift
    # from silently absorbing a thermal error -- the mid-range knee (~5..25 mm) is the
    # region the τ-shift and the thermal curve both act on. Representative ASM/Krauss-
    # band values; the published equivalence varies ~±25 % between sources, so the
    # tolerance is honest, not slack. The near-quenched-end rate is *not* benchmarked
    # here: it is the h_quench-driven region (Phase-2c knob) and is martensite-
    # saturated, so it does not affect hardness.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    published = [                                     # (distance mm, K/s at 700 C)
        (3.2, 170.0), (4.8, 100.0), (7.9, 50.0), (9.5, 38.0),
        (12.7, 23.0), (15.9, 16.5), (19.0, 11.0), (25.4, 7.0),
    ]
    dist = np.array([p[0] for p in published]) / 1000.0
    pub_rate = np.array([p[1] for p in published])
    ratio = f.cooling_rate_at(dist, 700.0) / pub_rate
    assert np.all(ratio > 0.70) and np.all(ratio < 1.30)     # each mid point within ~25 %
    assert 0.80 < float(np.mean(ratio)) < 1.20               # unbiased across the range


def test_cooling_rate_curve_is_resolution_converged():
    # The cooling-rate curve is a physical result, not a discretization artifact:
    # doubling both the spatial cells and the time-grid density moves the read-region
    # curve < 3 %. (Rules out the sub-cell near-end boundary layer / coarse-bracket
    # extraction as the source of the curve's shape -- it is the fin physics.)
    d = jominy_distances(20)                          # 1.6 .. ~32 mm
    base = solve_thermal_field(JominyBar(), n_cells=200, per_decade=120).cooling_rate_at(d, 700.0)
    fine = solve_thermal_field(JominyBar(), n_cells=400, per_decade=240).cooling_rate_at(d, 700.0)
    assert np.max(np.abs(fine - base) / np.maximum(base, 1e-9)) < 0.03


def test_cooling_rate_strong_gradient_end_to_far():
    # The quenched end cools far faster than the bar interior -- the gradient that
    # makes hardenability legible. (Near-end magnitude is the uncalibrated knob, so
    # only a sanity floor is asserted here; the shape is pinned by the benchmark.)
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    cr = f.cooling_rate_at(jominy_distances(16), 700.0)
    assert cr[0] > 150.0                              # ~1.6 mm: very fast (martensitic)
    assert cr[0] > 20.0 * cr[-1]                       # strong end-to-far gradient


def test_near_end_cools_below_far_end():
    # Direction of the spatial gradient: at an intermediate time the quenched end
    # is colder than the far end.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=120, per_decade=60)
    # pick a time where the near end has dropped well below the far end
    i_mid = f.t.size // 2
    assert f.T[i_mid, 0] < f.T[i_mid, -1]
    # and every position cools monotonically in time
    assert np.all(np.diff(f.T, axis=0) <= 1e-9)
