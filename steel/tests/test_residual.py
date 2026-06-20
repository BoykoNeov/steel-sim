"""Phase-6f validation: residual stress & distortion on quench (§11 Option-#2, solid mechanics).

The first phase to add solid mechanics. Like §14/§16/§17 it introduces **no number fitted to a
residual-stress measurement** — the material curves (``E(T)``, ``σ_Y(T)``) are cited Eurocode-3
reductions on representative bases, the dilatation is from cited lattice parameters — so the triad is
**structural teeth + conservation + consistency**, read for shape not absolute value:

* **The sign-reversal tooth (headline).** A quench leaves *surface compression* when only thermal
  contraction acts (transformation OFF) but *surface tension* when the martensite dilatation is active
  (transformation ON) — the same steel and quench, opposite surface signs. This is the mechanism that
  makes a through-hardening quench crack-prone, and the reason pure-elastic (which gives zero residual
  on a through-hardened part) was rejected. Shown with the ON/OFF toggle because both anchored atlas
  steels are through-hardeners (no steel here gives surface compression *with* transformation).
* **Self-equilibrium (conservation).** ``∫σ dx = 0`` to machine precision — the free conservation leg,
  the residual-stress analogue of Jominy's energy balance.
* **Magnitude order.** Peak ``|σ|`` is of order the yield strength (a quench reaches yield-level
  residuals), not 10× or 0.01× — the only magnitude claim the model makes.
* **Martemper < direct quench.** Martempering's near-uniform slow cool through ``Mₛ`` collapses the
  surface tension — the stress-quantitative statement of the §17 distortion benefit (which read only a
  thermal-gradient proxy).

Plus the cited-property monotonicities, the dilatation carbon trend, and the input guards. The demo
case is 4340 (the deep-hardening, quench-crack-prone alloy) in a 50 mm plate (Biot ≈ 1.25 — severe
enough that the hot core yields, which is what a thermal residual *requires*); a coarse grid is used
for speed (the teeth are resolution-robust, pinned by :func:`test_teeth_are_resolution_robust`).
"""
import numpy as np
import pytest

from steel import residual as res
from steel import cooling

# Demo regime: 4340, 2L = 50 mm plate, still-water quench (Biot ≈ 1.25). Coarse grid for speed.
STEEL = "4340"
HALF_THICKNESS = 0.025
H_QUENCH = cooling.H_WATER
N_CELLS = 60
N_T = 2000
SIGMA_Y_20 = res.SIGMA_Y_REF_20C


@pytest.fixture(scope="module")
def direct_on():
    """Direct water quench, transformation active — the crack-prone through-hardening case."""
    return res.quench_residual_stress(
        STEEL, HALF_THICKNESS, route="direct", transform=True,
        h_quench=H_QUENCH, n_cells=N_CELLS, n_t=N_T,
    )


@pytest.fixture(scope="module")
def direct_off():
    """Direct water quench, transformation suppressed — the thermal-only reference."""
    return res.quench_residual_stress(
        STEEL, HALF_THICKNESS, route="direct", transform=False,
        h_quench=H_QUENCH, n_cells=N_CELLS, n_t=N_T,
    )


@pytest.fixture(scope="module")
def comparison():
    """Direct-vs-martemper residual comparison at the demo geometry."""
    return res.residual_comparison(
        STEEL, HALF_THICKNESS, h_quench=H_QUENCH, n_cells=N_CELLS, n_t=N_T,
    )


# --------------------------------------------------------------------------- #
# The headline tooth: the surface-sign reversal (thermal vs transformation)
# --------------------------------------------------------------------------- #
def test_thermal_only_leaves_surface_compression(direct_off):
    """Transformation OFF (thermal contraction alone) → the surface ends in **compression**."""
    assert direct_off.surface_stress < 0.0
    assert direct_off.crack_risk is False


def test_transformation_flips_surface_to_tension(direct_on):
    """Transformation ON (martensite dilatation) → the surface ends in **tension** (crack-prone)."""
    assert direct_on.surface_stress > 0.0
    assert direct_on.crack_risk is True


def test_sign_reversal_is_the_transformation(direct_on, direct_off):
    """The *only* difference is the dilatation, yet the surface sign flips — the mechanism, isolated."""
    assert direct_off.surface_stress < 0.0 < direct_on.surface_stress
    # And the transformation case puts the core into compression (it balances the surface tension).
    assert direct_on.center_stress < 0.0


# --------------------------------------------------------------------------- #
# Conservation: self-equilibrium (∫σ dx = 0 to machine precision)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("transform", [True, False])
def test_residual_field_is_self_equilibrated(transform):
    """The residual profile carries zero net in-plane force (``mean σ = 0``) to machine precision."""
    f = res.quench_residual_stress(
        STEEL, HALF_THICKNESS, route="direct", transform=transform,
        h_quench=H_QUENCH, n_cells=N_CELLS, n_t=N_T,
    )
    peak = max(abs(f.peak_tension), abs(f.peak_compression), 1.0)
    assert abs(f.mean_stress) < 1e-6 * peak          # ~1e-8 Pa in practice


# --------------------------------------------------------------------------- #
# Magnitude order: residuals reach (but do not absurdly exceed) the yield
# --------------------------------------------------------------------------- #
def test_peak_residual_is_of_order_yield(direct_on):
    """A severe quench leaves yield-order residuals — peak ``|σ|`` within a band around ``σ_Y``."""
    peak = max(abs(direct_on.peak_tension), abs(direct_on.peak_compression))
    assert 0.2 * SIGMA_Y_20 < peak < 1.5 * SIGMA_Y_20


def test_perfectly_plastic_cap_is_respected(direct_on):
    """No cell exceeds the (perfectly-plastic) room-temperature yield — the return-map cap holds."""
    assert np.max(np.abs(direct_on.sigma)) <= SIGMA_Y_20 * (1.0 + 1e-6)


# --------------------------------------------------------------------------- #
# The §17 tie-in: martempering collapses the surface tension (now in stress)
# --------------------------------------------------------------------------- #
def test_martemper_reduces_surface_tension(comparison):
    """Martempering's near-uniform slow cool shrinks the direct-quench surface tension far down."""
    assert comparison.surface_direct > 0.0                       # direct quench is crack-prone
    assert abs(comparison.surface_martemper) < 0.1 * abs(comparison.surface_direct)
    assert comparison.reduction > 5.0


def test_martemper_is_not_crack_prone(comparison):
    """The martempered surface is not in significant tension — the distortion/crack benefit."""
    assert comparison.martemper.surface_stress < 0.1 * comparison.direct.surface_stress


# --------------------------------------------------------------------------- #
# Cited-property monotonicities and the dilatation carbon trend
# --------------------------------------------------------------------------- #
def test_modulus_and_yield_soften_with_temperature():
    """``E(T)`` and ``σ_Y(T)`` both decrease monotonically with temperature (steel softens hot)."""
    T = np.linspace(20.0, 1200.0, 25)
    E = res.youngs_modulus(T)
    sY = res.yield_strength(T)
    assert np.all(np.diff(E) <= 1e-6)
    assert np.all(np.diff(sY) <= 1e-6)
    assert res.youngs_modulus(20.0) == pytest.approx(res.E_REF_20C)
    assert res.yield_strength(20.0) == pytest.approx(res.SIGMA_Y_REF_20C)


def test_transformation_dilatation_is_positive_and_falls_with_carbon():
    """γ→martensite expands (``ε_tr > 0``) and the dilatation decreases with carbon — ~1 % linear."""
    e0, e4, e8 = (res.transformation_dilatation(c) for c in (0.0, 0.4, 0.8))
    assert e0 > e4 > e8 > 0.0
    assert 0.005 < e4 < 0.02                          # ~1.3 % for 4340-carbon
    # Linear strain is one third of the volume change, by construction.
    assert res.transformation_dilatation(0.4) == pytest.approx(
        res.volume_change_gamma_to_martensite(0.4) / 3.0
    )


# --------------------------------------------------------------------------- #
# Resolution robustness of the teeth, and input guards
# --------------------------------------------------------------------------- #
def test_teeth_are_resolution_robust():
    """The signs and the surface-tension magnitude hold under grid refinement (not a coarse artifact)."""
    coarse = res.quench_residual_stress(
        STEEL, HALF_THICKNESS, route="direct", transform=True,
        h_quench=H_QUENCH, n_cells=60, n_t=2000,
    )
    fine = res.quench_residual_stress(
        STEEL, HALF_THICKNESS, route="direct", transform=True,
        h_quench=H_QUENCH, n_cells=120, n_t=4000,
    )
    assert coarse.surface_stress > 0.0 and fine.surface_stress > 0.0
    assert fine.surface_MPa == pytest.approx(coarse.surface_MPa, rel=0.1)


def test_martemper_near_zero_is_resolution_converged():
    """The martemper ≈ 0 residual is physical, not an under-resolved early-transient artifact.

    The martemper run marches a ~10-hour air cool, so a coarse linspace grid could *starve* the early
    bath-quench transient and report a spuriously-zero residual. Refining the grid 4× (the bath quench
    is then resolved by hundreds of steps) leaves the surface residual still negligible — so the
    near-elimination is the physics (the deep-cooling-under-gradient phase that builds the *direct*
    quench's thermal residual is replaced by a uniform slow cool), not a grid artifact. Checked with
    transformation off too (the bath-quench thermal residual is itself negligible at this severity).
    """
    for transform in (True, False):
        coarse = res.quench_residual_stress(
            STEEL, HALF_THICKNESS, route="martemper", transform=transform,
            h_quench=H_QUENCH, n_cells=60, n_t=3000,
        )
        fine = res.quench_residual_stress(
            STEEL, HALF_THICKNESS, route="martemper", transform=transform,
            h_quench=H_QUENCH, n_cells=60, n_t=12000,
        )
        assert abs(coarse.surface_MPa) < 5.0 and abs(fine.surface_MPa) < 5.0


def test_unknown_steel_refused():
    """Only the anchored atlas steels have a defined composition/``Mₛ`` for the dilatation."""
    with pytest.raises(ValueError, match="atlas anchor"):
        res.quench_residual_stress("1045", HALF_THICKNESS)


def test_unknown_route_refused():
    """``route`` must be 'direct' or 'martemper'."""
    with pytest.raises(ValueError, match="route"):
        res.quench_residual_stress(STEEL, HALF_THICKNESS, route="furnace")


def test_field_shape_and_geometry(direct_on):
    """The field is one stress per cell, centre→surface, on the requested grid."""
    assert direct_on.sigma.shape == (N_CELLS,)
    assert direct_on.sigma_history.shape[1] == N_CELLS
    assert direct_on.x[0] < direct_on.x[-1]                       # 0 = core, half_thickness = surface
    assert direct_on.x[-1] == pytest.approx(HALF_THICKNESS, rel=0.05)
    assert direct_on.center_stress == pytest.approx(direct_on.sigma[0])
    assert direct_on.surface_stress == pytest.approx(direct_on.sigma[-1])


# --------------------------------------------------------------------------- #
# The optional phase-split yield path (the mechanics the fracture coupling consumes)
# --------------------------------------------------------------------------- #
def test_default_is_single_yield_and_phase_split_records_the_flag():
    """``phase_split_yield`` defaults off (unchanged behaviour) and is recorded on the field."""
    default = res.quench_residual_stress(STEEL, HALF_THICKNESS, n_cells=N_CELLS, n_t=N_T)
    assert default.phase_split is False
    split = res.quench_residual_stress(
        STEEL, HALF_THICKNESS, phase_split_yield=True, n_cells=N_CELLS, n_t=N_T)
    assert split.phase_split is True


def test_phase_split_lifts_surface_tension_above_the_single_yield_cap():
    """A hard martensite surface holds tension the single-yield solve caps at σ_Y,20 — the mechanism.

    The default solve clips the surface near ``SIGMA_Y_REF_20C`` (the named scope edge); the phase-split
    solve lets the transformed surface carry far higher tension (the soft hot core still yields to generate
    the mismatch). A thick section makes the gradient steep enough to show it clearly.
    """
    ht = 0.04                                                     # thick enough to be cap-limited
    single = res.quench_residual_stress(STEEL, ht, n_cells=N_CELLS, n_t=N_T)
    split = res.quench_residual_stress(STEEL, ht, phase_split_yield=True, n_cells=N_CELLS, n_t=N_T)
    assert single.surface_stress == pytest.approx(SIGMA_Y_20, rel=0.1)   # single-yield is at the cap
    assert split.surface_stress > 1.5 * single.surface_stress           # split lifts it well above
    assert split.surface_stress < res.SIGMA_Y_MARTENSITE_20C            # but bounded by the martensite yield


def test_phase_split_field_is_still_self_equilibrated():
    """Lifting the yield cap must not break the conservation leg: ``∫σ dx = 0`` still holds."""
    split = res.quench_residual_stress(STEEL, 0.04, phase_split_yield=True, n_cells=N_CELLS, n_t=N_T)
    assert split.mean_stress == pytest.approx(0.0, abs=1e-6 * SIGMA_Y_20)
