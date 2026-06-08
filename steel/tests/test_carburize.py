"""Phase-3c validation: carburizing case-hardening — the mass-diffusion face of the spine.

3c carries the plan's **named Phase-3 triad** (steel-production.md §3), and it is the
cleanest triad in the project because its two headline legs are the *frozen engine's own
guarantees* re-instantiated in carbon mass mode — no new calibration:

* **Analytical limit — the erfc law and case depth ∝ √(Dt).** The numeric carbon profile
  (constant ``D`` + Dirichlet surface) matches the error-function solution in the interior,
  and the case depth scales **exactly** as ``√(Dt)`` (the self-similar variable ``x/2√(Dt)``).
  The scaling is asserted *tightly*; the *absolute* case depth is asserted *loosely* — the
  carbon potential and the case-depth definition vary widely across sources, and the cited
  constant-``D`` (vs the concentration-enhanced Tibbetts ``D(C)``) under-predicts the absolute
  depth, a *named* scope limitation. (Same split as the 1045 knee: anchored claim tight,
  simplification-driven number loose.)
* **Conservation — carbon uptake = surface-flux integral.** ``Δ∫C dx`` equals the accumulated
  surface flux ``Σ dt·flux(left)`` to machine precision — the engine's *exact* backward-Euler
  flux identity, with the core a no-flux boundary. Confirmed here for the **Dirichlet** surface
  specifically (not inherited from jominy's Robin result), plus the semi-infinite tie ``Δ∫C dx =
  2(Cs−C0)√(Dt/π)``.
* **Benchmark — case depth + surface hardness vs published.** The 50-HRC effective case depth
  (~1.4 mm at 925 °C/8 h) lands in the published rule-of-thumb band, and the **surface hardness**
  cross-checks the independently-anchored martensite curve (~65 HRC for ~0.8 %C — the case as
  designed). Both are genuine cross-checks: ``D0, Q`` are cited diffusion data (not fit to case
  depth) and the martensite hardness is anchored to Hodge–Orehoski (not to carburizing).

The benchmark fork (advisor): running the full kinetics to room temperature at the
high-carbon surface predicts substantial **retained austenite** (low ``Ms`` there) — real
heavy-case physics, but also where Andrews ``Ms`` / KM / the √C martensite curve are pushed
past their ~0.8 %C anchor. So the surface-hardness benchmark is anchored to the martensite
**potential** (``HV`` — the case as designed), and the RA is reported as the microstructure
gradient (``retained_austenite`` / ``HV_as_quenched``) but **not** asserted against the band.
"""
import math

import numpy as np
import pytest

from projects.steel import carburize as cb


# --------------------------------------------------------------------------- #
# The one new physics constant: cited carbon diffusivity in austenite
# --------------------------------------------------------------------------- #
def test_carbon_diffusivity_matches_cited_arrhenius():
    # Pin the cited Callister C-in-γ-Fe value (D0 = 2.3e-5, Q = 148 kJ/mol). At 925 °C
    # ≈ 8.1e-12 m²/s — the diffusivity that sets the ~0.5 mm/√(8 h) case-depth scale.
    assert cb.carbon_diffusivity(925.0) == pytest.approx(8.12e-12, rel=0.02)
    # Arrhenius: rises with temperature (a hotter cycle diffuses faster → deeper case).
    assert cb.carbon_diffusivity(950.0) > cb.carbon_diffusivity(925.0) > cb.carbon_diffusivity(900.0)


# --------------------------------------------------------------------------- #
# Analytical limit: the erfc profile + case depth ∝ √(Dt)
# --------------------------------------------------------------------------- #
def test_numeric_profile_matches_erfc_in_the_interior():
    # The frozen engine (mass mode, constant D + Dirichlet surface) reproduces the
    # error-function solution. Compare the *interior* (the surface cell carries the
    # Dirichlet half-cell's local first-order error; the active region is where erfc
    # rises meaningfully above the core).
    p = cb.solve_carburize(t_hours=8.0, n_cells=300, n_steps=600)
    ana = p.erfc_profile()
    active = (ana - p.C_core) > 1e-3 * (p.C_surface - p.C_core)
    active[0] = False                                       # drop the Dirichlet surface cell
    rel_err = np.abs(p.C[active] - ana[active]) / (p.C_surface - p.C_core)
    assert np.max(rel_err) < 2e-3                           # tight interior agreement


def test_profile_is_monotone_surface_to_core_and_semi_infinite():
    p = cb.solve_carburize(t_hours=8.0)
    # Carbon decreases monotonically from the enriched surface to the untouched core.
    assert np.all(np.diff(p.C) <= 1e-12)
    assert p.C[0] == pytest.approx(p.C_surface, abs=0.02)   # surface ≈ carbon potential
    assert p.C[-1] == pytest.approx(p.C_core, abs=1e-4)     # far field untouched (semi-infinite)


def test_case_depth_scales_as_sqrt_Dt():
    # The headline analytical leg: x_case = 2·erfc⁻¹(r)·√(Dt) ∝ √(Dt). Solve several
    # cycle times and confirm x_case/√t is constant (the self-similar variable). TIGHT.
    times = [2.0, 4.0, 8.0]
    ratios = []
    for th in times:
        p = cb.solve_carburize(t_hours=th, length=8e-3, n_cells=400, n_steps=800)
        ratios.append(p.case_depth(0.4) / math.sqrt(th))
    ratios = np.array(ratios)
    assert np.all(np.isfinite(ratios))
    assert (ratios.std() / ratios.mean()) < 0.02           # constant ratio → ∝ √t


def test_numeric_case_depth_matches_closed_form():
    # The numeric threshold-crossing reproduces the closed-form 2·erfc⁻¹(r)·√(Dt).
    p = cb.solve_carburize(t_hours=8.0, length=8e-3, n_cells=400, n_steps=800)
    assert p.case_depth(0.4) == pytest.approx(p.analytic_case_depth(0.4), rel=0.03)


def test_analytic_case_depth_form():
    # Closed form: ∝ √(Dt), and nan when the threshold falls outside (C_core, C_surface).
    D = cb.carbon_diffusivity(925.0)
    d1 = cb.analytic_case_depth(3600.0, D, 0.8, 0.2, 0.4)
    d4 = cb.analytic_case_depth(4 * 3600.0, D, 0.8, 0.2, 0.4)
    assert d4 == pytest.approx(2.0 * d1, rel=1e-9)          # 4× time → 2× depth
    assert math.isnan(cb.analytic_case_depth(3600.0, D, 0.8, 0.2, 0.9))   # above surface
    assert math.isnan(cb.analytic_case_depth(3600.0, D, 0.8, 0.2, 0.1))   # below core


# --------------------------------------------------------------------------- #
# Conservation: carbon uptake = surface-flux integral (the frozen identity)
# --------------------------------------------------------------------------- #
def test_carbon_uptake_equals_surface_flux_integral():
    # The engine's EXACT backward-Euler identity, re-confirmed for the Dirichlet surface:
    # Δ∫C dx = Σ dt·(flux_left − flux_right); the core is no-flux, so the carbon absorbed
    # equals the integrated surface flux to machine precision. The conservation leg.
    p = cb.solve_carburize(t_hours=8.0)
    assert p.mass_uptake > 0.0                              # carbon was absorbed
    assert abs(p.mass_uptake - p.surface_flux_uptake) < 1e-12


def test_mass_uptake_matches_semi_infinite_analytic():
    # The semi-infinite tie that links the erfc and conservation legs: the absorbed carbon
    # ∫(C−C0) dx = 2(Cs−C0)√(Dt/π) exactly for the erfc profile.
    p = cb.solve_carburize(t_hours=8.0)
    analytic = 2.0 * (p.C_surface - p.C_core) * math.sqrt(p.D * p.t / math.pi)
    assert p.mass_uptake == pytest.approx(analytic, rel=0.01)


def test_conservation_holds_even_when_not_semi_infinite():
    # Conservation is structural (no-flux core), independent of the erfc holding: run a
    # shallow domain so carbon reaches the core boundary — the erfc breaks, but the mass
    # balance does NOT (the carbon piles up, reflected, still accounted).
    p = cb.solve_carburize(t_hours=8.0, length=0.8e-3, n_cells=120)
    assert p.C[-1] > p.C_core + 1e-3                        # far end is NOT untouched here
    assert abs(p.mass_uptake - p.surface_flux_uptake) < 1e-12


# --------------------------------------------------------------------------- #
# Benchmark: case depth + surface hardness vs published (genuine cross-checks)
# --------------------------------------------------------------------------- #
def test_effective_case_depth_in_published_band():
    # ABSOLUTE case depth, asserted LOOSELY (the carbon potential + the case-depth
    # definition vary across sources; constant-D under-predicts vs Tibbetts D(C)). The
    # carbon-based ECD (0.4 %C) is sub-mm and order-1 mm at a multi-hour cycle…
    p = cb.solve_carburize(t_hours=8.0)
    ecd_carbon = p.case_depth(0.4)
    assert 0.3e-3 < ecd_carbon < 1.2e-3
    # …and the hardness-based ECD (depth to 50 HRC), the most-tabulated definition, lands
    # in the published rule-of-thumb band (~1.4 mm at 925 °C / 8 h) — an *integrated*
    # cross-check (cited D for the depth × the anchored hardness model for the contour).
    tr = cb.carburized_traverse(p)
    ecd_hardness = tr.case_depth_50HRC()
    assert 1.0e-3 < ecd_hardness < 1.8e-3


def test_surface_hardness_cross_checks_martensite_curve():
    # The surface-hardness benchmark is anchored to the martensite POTENTIAL (the case as
    # designed). ~0.8 %C full martensite ≈ 65 HRC on the independently-anchored
    # as-quenched curve — a real cross-check (the curve was fit to Hodge–Orehoski, not to
    # carburizing data). Band the high-60s carburized-surface ceiling (E140 tops at 67).
    p = cb.solve_carburize(t_hours=8.0)
    tr = cb.carburized_traverse(p)
    assert 62.0 <= tr.HRC[0] <= 67.0                        # hard martensite case


def test_hardness_falls_from_hard_case_to_softer_core():
    # The case-hardened gradient: a hard surface over a softer, tougher core, monotone
    # in between (the carbon gradient read out as hardness — the whole point of 3c). The
    # tight, anchored claims are the *direction* (case harder than core) and monotonicity.
    p = cb.solve_carburize(t_hours=8.0)
    tr = cb.carburized_traverse(p)
    assert tr.HV[0] > tr.HV[-1]                             # case harder than core
    assert np.all(np.diff(tr.HV) <= 1e-9)                  # monotone decreasing with depth
    # The core hardness NUMBER is a *model/quench-dependent sanity band*, NOT a published
    # cross-check (unlike the surface hardness). It is set by the cooling-rate physics 3c
    # deliberately holds fixed — the default 0-D `oil` path on cooling.py's 10 mm cylinder
    # gives ~97 % martensite at 0.2 %C, so the core reads ~48 HRC. A real gear section cools
    # slower and forms more bainite/ferrite in the core (published 8620 core ~30–40 HRC), so
    # this band is asserted *loosely*, the way the 1045-knee position is — not as a benchmark.
    assert 40.0 <= tr.HRC[-1] <= 52.0


# --------------------------------------------------------------------------- #
# The retained-austenite fork: real physics, reported but NOT asserted vs the band
# --------------------------------------------------------------------------- #
def test_retained_austenite_rises_toward_the_high_carbon_surface():
    # Emergent (not a fitted term): the high-carbon surface has a low Ms (Andrews), so KM
    # to room temperature leaves substantial retained austenite there, while the low-carbon
    # core goes essentially full martensite. Assert the DIRECTION (qualitative, loose) —
    # this is the documented heavy-case effect, and the reason the surface benchmark uses
    # the martensite potential, not this RA-laden mixture.
    p = cb.solve_carburize(t_hours=8.0)
    tr = cb.carburized_traverse(p)
    assert tr.retained_austenite[0] > 0.10                  # meaningful RA at the surface
    assert tr.retained_austenite[0] > tr.retained_austenite[-1]   # rises toward the surface
    assert tr.retained_austenite[-1] < 0.05                 # core is essentially martensite


def test_as_quenched_hardness_dips_below_potential_only_near_the_surface():
    # The two hardness curves coincide through the core (full martensite there) and the
    # as-quenched curve dips below the potential only near the surface — the visible RA
    # signature. Assert the direction; do NOT assert the RA-laden surface value vs published.
    p = cb.solve_carburize(t_hours=8.0)
    tr = cb.carburized_traverse(p)
    assert tr.HV_as_quenched[0] < tr.HV[0] - 50.0           # RA drags the surface down
    assert tr.HV_as_quenched[-1] == pytest.approx(tr.HV[-1], rel=0.05)  # core: curves coincide


def test_solve_rejects_inverted_carbon_gradient():
    # Carbon must flow inward: a surface potential at/below the core is a configuration error.
    with pytest.raises(ValueError):
        cb.solve_carburize(C_surface=0.2, C_core=0.4)
