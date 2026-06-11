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

from steel import carburize as cb
from steel import properties as prop


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


def test_as_quenched_hardness_dips_below_the_martensite_potential():
    # The "potential" curve (tr.HV) is the *as-designed* full-martensite hypothetical; the
    # as-quenched curve (tr.HV_as_quenched) is the real mixture, which dips below it for TWO
    # distinct reasons at the two ends:
    #   * surface — heavy RETAINED AUSTENITE (high-C austenite, low Ms) drags it down hard;
    #   * core    — PROEUTECTOID FERRITE (Phase 6a): a 0.2 %C core forms ~⅓ α at the slow oil
    #     quench (KV's large carbon coefficient → low-C austenite transforms readily), the more
    #     physical result the module docstring anticipated (published 8620 cores run ~30–40 HRC,
    #     NOT the full-martensite ~48 HRC potential). Pre-6a the core sat at the potential
    #     (spuriously full martensite); now it dips by the ferrite it really forms.
    # Assert both dips are real and the case-harder-than-core ordering holds; do NOT assert the
    # core coincides with the full-martensite potential (it no longer does — and shouldn't).
    p = cb.solve_carburize(t_hours=8.0)
    tr = cb.carburized_traverse(p)
    assert tr.HV_as_quenched[0] < tr.HV[0] - 50.0          # surface dip: retained austenite
    assert tr.HV_as_quenched[-1] < tr.HV[-1] - 30.0        # core dip: proeutectoid ferrite (6a)
    assert tr.HV_as_quenched[0] > tr.HV_as_quenched[-1]    # case still harder than core
    # The as-quenched core lands in the published 8620 oil-core band (~30–40 HRC), not the
    # full-martensite potential — the ferrite bay corrects it toward the real value.
    assert 30.0 <= prop.vickers_to_rockwell_c(tr.HV_as_quenched[-1]) <= 42.0


def test_solve_rejects_inverted_carbon_gradient():
    # Carbon must flow inward: a surface potential at/below the core is a configuration error.
    with pytest.raises(ValueError):
        cb.solve_carburize(C_surface=0.2, C_core=0.4)


# --------------------------------------------------------------------------- #
# Concentration-dependent diffusivity D(C): the opt-in Tibbetts path + its triad
# --------------------------------------------------------------------------- #
# The constant-D erfc above is the validated *analytical limit* and stays the default.
# D(C) (Tibbetts 1980) is the opt-in concentration-dependent diffusivity, wired to the
# (now unfrozen) engine's native nonlinear ``D_of_u`` — ADR 0004. It turns the named
# "constant-D under-predicts the absolute case depth" scope edge into a quantified, cited
# result, with its own triad: the Boltzmann self-similar reference (analytical), the exact
# conservation identity (the engine's cached-field guarantee), and a deeper case in the
# published band (benchmark). Tibbetts D is independent diffusion data — not fit to case
# depth — so the case-depth benchmark stays a genuine cross-check.
def test_tibbetts_diffusivity_rises_with_carbon_and_matches_cited_value():
    D02 = float(cb.carbon_diffusivity_tibbetts(0.2, 925.0))
    D04 = float(cb.carbon_diffusivity_tibbetts(0.4, 925.0))
    D08 = float(cb.carbon_diffusivity_tibbetts(0.8, 925.0))
    # Rises with carbon (the −6600·C activation lowering beats the −1.6·C prefactor decay) —
    # the physical basis for the fuller-than-erfc profile.
    assert D08 > D04 > D02
    # Pin the cited closed form at a reference (0.4 %C, 925 °C):
    # 0.47·e^(−0.64)·e^(−34360/(1.987·1198.15)) cm²/s = 1.337e-7 cm²/s = 1.337e-11 m²/s.
    assert D04 == pytest.approx(1.337e-11, rel=0.02)
    # …and it sits ABOVE the constant Callister D (8.1e-12) across the active band — the
    # "constant-D under-predicts" direction the constant-D scope note names.
    assert D02 > cb.carbon_diffusivity(925.0)
    # Arrhenius in temperature, at fixed carbon.
    assert float(cb.carbon_diffusivity_tibbetts(0.4, 950.0)) > D04
    # Vectorized over a carbon array → an elementwise, increasing D array.
    Darr = cb.carbon_diffusivity_tibbetts(np.array([0.2, 0.4, 0.8]), 925.0)
    assert Darr.shape == (3,)
    assert np.all(np.diff(Darr) > 0)


def test_dofC_is_opt_in_constant_path_byte_identical():
    # The additive-default discipline (mirrors 3a's byte-for-byte comp/Vr defaults): passing
    # D_of_C=None reproduces the constant-D erfc solve exactly — the validated analytical
    # limit is untouched. The D(C) path carries its diagnostics; the constant path does not.
    base = cb.solve_carburize()
    same = cb.solve_carburize(D_of_C=None)
    assert np.array_equal(base.C, same.C)
    assert base.D_array is None and base.concentration_dependent is False
    dc = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts)
    assert dc.concentration_dependent is True
    assert dc.D_array is not None and dc.D_array.shape == base.C.shape


def test_dofC_profile_matches_boltzmann_similarity():
    # The D(C) analytical leg: the numeric concentration-dependent solve (the engine's native
    # nonlinear Picard step) matches the self-similar Boltzmann BVP reference in the interior
    # — two independent numerics (finite-volume marching vs a similarity BVP) agreeing is the
    # real check that the D(C) solve is correct, not merely self-consistent.
    p = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts, n_cells=400, n_steps=800)
    ref = p.boltzmann_profile()
    active = (ref - p.C_core) > 1e-3 * (p.C_surface - p.C_core)
    active[0] = False                                   # drop the Dirichlet surface half-cell
    rel = np.abs(p.C[active] - ref[active]) / (p.C_surface - p.C_core)
    assert np.max(rel) < 2e-3                            # two independent solvers agree tightly


def test_dofC_case_depth_still_scales_as_sqrt_t():
    # The tight scaling leg SURVIVES the loss of erfc: with D(C) the profile is self-similar
    # in η = x/√t, so x_case/√t is still constant. (Conservation of the scaling is the leg
    # with content here; the absolute depth is the benchmark below.)
    ratios = []
    for th in (2.0, 4.0, 8.0):
        p = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts,
                               t_hours=th, length=8e-3, n_cells=400, n_steps=800)
        ratios.append(p.case_depth(0.4) / math.sqrt(th))
    ratios = np.array(ratios)
    assert np.all(np.isfinite(ratios))
    assert (ratios.std() / ratios.mean()) < 0.02


def test_dofC_resolution_converged_under_refinement():
    # The fuller profile must be PHYSICS, not a time-discretization artifact: the D(C) case
    # depth is converged under time refinement (mirrors jominy's <1.2 % check). The engine's
    # per-step Picard converges to tol, so this isolates the backward-Euler time accuracy.
    coarse = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts,
                                length=8e-3, n_cells=400, n_steps=400)
    fine = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts,
                              length=8e-3, n_cells=400, n_steps=1600)
    assert abs(coarse.case_depth(0.4) - fine.case_depth(0.4)) / fine.case_depth(0.4) < 0.01


def test_dofC_conservation_is_machine_precise():
    # Conservation is STRUCTURAL and exact on the D(C) path too: the engine caches the
    # accepted-assembly D-field, so the backward-Euler flux identity holds per step and
    # telescopes — the carbon absorbed = the integrated surface flux to machine precision,
    # exactly as on the constant-D path (the cached-field guarantee, CONTRACT.md / ADR 0004).
    p = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts)
    assert p.mass_uptake > 0.0
    assert abs(p.mass_uptake - p.surface_flux_uptake) < 1e-12


def test_dofC_gives_a_deeper_case_than_constant_D():
    # The teeth: turning the named "constant-D under-predicts" edge into a quantified, cited
    # result. At the same cycle the Tibbetts D(C) case (0.4 %C) is DEEPER than constant-D —
    # and lands in the published rule-of-thumb band for a 925 °C / 8 h gas-carburize, a
    # genuine cross-check (Tibbetts D is independent diffusion data, not fit to case depth).
    const = cb.solve_carburize(length=8e-3, n_cells=400, n_steps=800)
    dc = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts,
                            length=8e-3, n_cells=400, n_steps=800)
    ecd_const = const.case_depth(0.4)
    ecd_dc = dc.case_depth(0.4)
    assert ecd_dc > ecd_const * 1.10                    # meaningfully deeper, not a wash
    assert 0.7e-3 < ecd_dc < 1.2e-3                     # in the published ~1 mm band (was ~0.66 mm)
    # The self-similar Boltzmann case depth agrees with the numeric one (cross-check of the
    # two D(C) numerics at the benchmark point).
    assert cb.boltzmann_case_depth(dc.t) == pytest.approx(ecd_dc, rel=0.05)


def test_dofC_traverse_runs_and_keeps_the_case_gradient():
    # The downstream microstructure→hardness chain is agnostic to how C(x) was produced, so
    # the D(C) profile flows through carburized_traverse unchanged: still a hard case over a
    # softer core, with mass-conservation intact. (The hardness model itself is Phase 2c/3a;
    # here we only confirm the deeper D(C) profile composes cleanly.)
    p = cb.solve_carburize(D_of_C=cb.carbon_diffusivity_tibbetts)
    tr = cb.carburized_traverse(p)
    assert tr.HV[0] > tr.HV[-1]                          # case still harder than core
    assert 62.0 <= tr.HRC[0] <= 67.0                     # hard martensite case (carbon-set)
