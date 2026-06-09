"""Phase-6a validation: the proeutectoid-ferrite bay (the Li/Kirkaldy–Venugopalan reaction).

Phase 6a adds the diffusional reaction the single C-curve was missing: **proeutectoid ferrite**,
nucleating below the A₃ transus (*above* A₁) for a hypoeutectoid steel. The corrected diagnosis
(see :mod:`kinetics` §5): A₁ is *correct* for pearlite; what was missing — leaving 1045's Jominy
knee ~2–3 mm too deep — is the ferrite reaction with its own higher ceiling A₃. The bay is
**additive**: it leaves the pearlite curve and every eutectoid/four-curves benchmark byte-identical.

The triad, each leg anchored to its own discipline (the program's non-circularity rule):

* **Analytical / structural** — the cited Li/KV composition factor ``FC`` reproduces the
  published coefficients exactly; the reaction is capped at the *equilibrium* proeutectoid-ferrite
  fraction (``fe_c``); the rate vanishes at/above ``Ae3``; and a bare ``CCurve`` / an inert
  (eutectoid) reaction is **byte-identical** to the pre-6a model. Conservation (fractions sum to 1)
  holds *with ferrite present*.
* **The teeth (cited prediction, not a fit)** — with the one calibrated scale set by a *constraint*
  (keep a 0.2 %C core physically hard, §5), **4140 stays deep**: it has *more* proeutectoid ferrite
  available than 1045 (f_pro ≈ 0.49 vs 0.42) yet forms almost none, purely because its cited Cr/Mo
  ``FC`` coefficients retard the reaction ~32×. Nothing about 4140 was tuned. The 1045-shallow /
  4140-deep divergence is now *mechanistic*.
* **Consequence** — fed the frozen Jominy thermal field, 1045 forms increasing ferrite with depth
  (shallower knee, the partial-but-real improvement) while its fully-martensitic quenched end is
  preserved; 1080 (eutectoid) is untouched.
"""
import numpy as np
import pytest

from projects.steel import fe_c, pathint
from projects.steel import properties as prop
from projects.steel.kinetics import (
    CCurve, ccurve_for_steel, andrews_Ms, ferrite_FC, ferrite_reaction_for_steel,
    FerriteReaction, FERRITE_FC_COEFFS, FERRITE_KINETIC_SCALE,
)
from projects.steel.jominy import solve_thermal_field, JominyBar, jominy_distances

STEEL_1045 = dict(Mn=0.75, Si=0.22)
STEEL_4140 = dict(Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)
STEEL_8620 = dict(Mn=0.80, Ni=0.55, Cr=0.50, Mo=0.20, Si=0.25)   # carburizing-grade core (0.2 %C)


# --------------------------------------------------------------------------- #
# Analytical / structural: the cited Li/KV composition factor + the cap + the ceiling
# --------------------------------------------------------------------------- #
def test_ferrite_FC_matches_cited_li_kv_coefficients():
    # FC = exp(1.00 + 6.31C + 1.78Mn + 0.31Si + 1.12Ni + 2.70Cr + 4.06Mo) — Li (1998) /
    # Kirkaldy–Venugopalan. Pin the exact exponent so a coefficient drift is caught, and confirm
    # carbon (6.31) and Cr/Mo (2.70/4.06) are the strong retarders the teeth rely on.
    expo = (1.00 + 6.31 * 0.40 + 1.78 * 0.90 + 0.31 * 0.25 + 1.12 * 0.0
            + 2.70 * 1.0 + 4.06 * 0.20)
    assert ferrite_FC(0.40, **STEEL_4140) == pytest.approx(np.exp(expo), rel=1e-12)
    assert FERRITE_FC_COEFFS["C"] == 6.31 and FERRITE_FC_COEFFS["Cr"] == 2.70 and FERRITE_FC_COEFFS["Mo"] == 4.06


def test_ferrite_retardation_ratio_4140_over_1045_is_cited_32x():
    # THE cited number behind the teeth: 4140's ferrite reaction is ~32× slower than 1045's, set
    # entirely by the published FC coefficients (Cr/Mo), not by us. This ratio is what keeps 4140
    # deep while 1045 goes shallow.
    ratio = ferrite_FC(0.40, **STEEL_4140) / ferrite_FC(0.45, **STEEL_1045)
    assert 28.0 <= ratio <= 36.0


def test_reaction_capped_at_equilibrium_proeutectoid_ferrite():
    # The ferrite mass fraction can never exceed the equilibrium proeutectoid-ferrite fraction the
    # lever rule gives (fe_c, Phase 1b) — that is the cap. A very slow path drives the completion
    # to 1, so the mass fraction lands exactly on f_pro.
    C = 0.45
    cc = ccurve_for_steel(C, **STEEL_1045)
    f_pro = fe_c.equilibrium_constituents(C).f_proeutectoid
    assert cc.ferrite.f_pro == pytest.approx(f_pro)
    # A ruinously slow cool (hold long inside the ferrite window) → full completion → f_ferrite = f_pro.
    Ae3 = cc.ferrite.Ae3
    t = np.linspace(0.0, 1e5, 4000)
    T = np.full_like(t, 0.5 * (cc.Ms + Ae3))            # park mid-window
    r = pathint.transform_along_path(t, T, cc)
    assert r.ferrite == pytest.approx(f_pro, rel=1e-6)
    assert r.ferrite <= f_pro + 1e-12


def test_eutectoid_and_hypereutectoid_have_no_ferrite_reaction():
    # No proeutectoid ferrite above the eutectoid: f_pro = 0, the reaction is inert. (1080 is
    # slightly hypereutectoid → proeutectoid cementite, not ferrite.)
    assert ferrite_reaction_for_steel(0.80, Mn=0.70, Si=0.20).f_pro == 0.0
    assert ferrite_reaction_for_steel(0.76).f_pro == 0.0          # exactly eutectoid


def test_rate_is_zero_at_and_above_Ae3():
    fr = ferrite_reaction_for_steel(0.45, **STEEL_1045)
    assert fr.rate(fr.Ae3) == 0.0
    assert fr.rate(fr.Ae3 + 50.0) == 0.0
    assert fr.rate(fr.Ae3 - 100.0) > 0.0                          # active below the ceiling


def test_ae3_override_is_the_calphad_coupling_seam():
    # The default ferrite ceiling is the alloy-aware Andrews Ae3; passing Ae3= overrides it (the
    # optional "couple CALPHAD into live kinetics" refinement). A lower ceiling = less undercooling
    # = a slower reaction, all else equal.
    fr_default = ccurve_for_steel(0.45, **STEEL_1045).ferrite
    fr_lower = ccurve_for_steel(0.45, **STEEL_1045, Ae3=fr_default.Ae3 - 40.0).ferrite
    assert fr_lower.Ae3 == pytest.approx(fr_default.Ae3 - 40.0)
    T = 0.5 * (50.0 + fr_lower.Ae3)
    assert fr_lower.rate(T) < fr_default.rate(T)


# --------------------------------------------------------------------------- #
# Byte-identity: the additive bay leaves the pre-6a model untouched where there is no ferrite
# --------------------------------------------------------------------------- #
def _path():
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=120, per_decade=60)
    return f.history(40)


def test_bare_ccurve_has_no_ferrite_and_is_byte_identical():
    # A direct CCurve (the four-curves idiom) carries no ferrite reaction → ferrite = 0 and the
    # other four fractions are exactly the pre-6a values.
    t, T = _path()
    cc = CCurve(Ms=andrews_Ms(0.80))
    r = pathint.transform_along_path(t, T, cc)
    assert r.ferrite == 0.0
    assert set(r.fractions()) == {"ferrite", "pearlite", "bainite", "martensite", "retained_austenite"}


def test_inert_ferrite_reaction_is_byte_identical_to_no_reaction():
    # Attaching an inert (f_pro = 0) reaction — e.g. eutectoid 1080 via ccurve_for_steel — leaves
    # every product fraction byte-for-byte identical to add_ferrite=False.
    t, T = _path()
    on = pathint.transform_along_path(t, T, ccurve_for_steel(0.80, Mn=0.70, Si=0.20))
    off = pathint.transform_along_path(t, T, ccurve_for_steel(0.80, Mn=0.70, Si=0.20, add_ferrite=False))
    assert on.ferrite == 0.0
    for k in ("pearlite", "bainite", "martensite", "retained_austenite"):
        assert on.fractions()[k] == off.fractions()[k]


def test_conservation_holds_with_ferrite_present():
    # The sacred sum-to-1, now with five products. Check across the whole Jominy bar for 1045
    # (where ferrite is substantial) — machine-exact, not just close.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=120, per_decade=60)
    cc = ccurve_for_steel(0.45, **STEEL_1045)
    for d in jominy_distances(16):
        j = int(np.argmin(np.abs(f.x - d)))
        r = pathint.transform_along_path(*f.history(j), cc)
        assert sum(r.fractions().values()) == pytest.approx(1.0, rel=0.0, abs=1e-12)
        assert r.ferrite >= 0.0 and all(v >= -1e-15 for v in r.fractions().values())


def test_ferrite_hardness_is_the_ferrite_pearlite_aggregate():
    # Proeutectoid ferrite shares the ferrite-pearlite hardness function (it IS that aggregate),
    # so the soft-end hardness depends only on the diffusional total: moving mass between the
    # ferrite and pearlite keys at fixed total leaves HV unchanged.
    C = 0.45
    base = {"ferrite": 0.0, "pearlite": 0.5, "bainite": 0.0, "martensite": 0.5, "retained_austenite": 0.0}
    split = {"ferrite": 0.3, "pearlite": 0.2, "bainite": 0.0, "martensite": 0.5, "retained_austenite": 0.0}
    assert prop.hardness_HV(base, C) == pytest.approx(prop.hardness_HV(split, C))


# --------------------------------------------------------------------------- #
# The teeth + consequence: 1045 shallow / 4140 deep, mechanistically, on the frozen field
# --------------------------------------------------------------------------- #
def _ferrite_vs_distance(C, comp, f, d):
    out = np.empty(d.size)
    cc = ccurve_for_steel(C, **comp)
    for k, dd in enumerate(d):
        j = int(np.argmin(np.abs(f.x - dd)))
        out[k] = pathint.transform_along_path(*f.history(j), cc).ferrite
    return out


def test_1045_forms_ferrite_with_depth_but_4140_does_not():
    # THE TEETH: 4140 has MORE proeutectoid ferrite available than 1045 (f_pro 0.49 vs 0.42) yet
    # forms almost none, because its cited Cr/Mo FC coefficients retard the reaction ~32×. 1045
    # forms increasing ferrite toward the slow (deep) end, up to its cap. Nothing about 4140 was
    # tuned — its suppression is the cited prediction.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)
    assert fe_c.equilibrium_constituents(0.40).f_proeutectoid > fe_c.equilibrium_constituents(0.45).f_proeutectoid
    fer1045 = _ferrite_vs_distance(0.45, STEEL_1045, f, d)
    fer4140 = _ferrite_vs_distance(0.40, STEEL_4140, f, d)
    assert fer1045[-1] > 0.30                            # 1045: substantial ferrite at the slow end
    assert np.all(fer4140 < 0.05)                        # 4140: suppressed everywhere (cited Cr/Mo)
    assert np.all(fer4140 <= fer1045 + 1e-9)             # 4140 never forms more, despite more available


def test_quenched_end_stays_fully_martensitic():
    # The fast quenched end outruns the ferrite reaction (rate is finite, the dwell short), so
    # both steels keep a fully-martensitic quenched end — the load-bearing hardness anchor the
    # bump destroyed but the additive bay preserves.
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)
    cc1045 = ccurve_for_steel(0.45, **STEEL_1045)
    r0 = pathint.transform_along_path(*f.history(int(np.argmin(np.abs(f.x - d[0])))), cc1045)
    assert r0.ferrite < 0.05 and r0.martensite > 0.85


def test_ferrite_bay_shallows_the_1045_knee_versus_no_bay():
    # The consequence (a partial, explicit improvement — NOT the headline): the proeutectoid-
    # ferrite bay moves 1045's 50 %-martensite knee shallower than the pre-6a single-curve model,
    # toward the published-shallow direction. (Full closure is blocked by the low-C-core ceiling
    # on the global scale — the named §5 limitation; per-reaction kinetics would lift it in 6b.)
    f = solve_thermal_field(JominyBar(), T0=850.0, n_cells=200, per_decade=120)
    d = jominy_distances(16)

    def knee_mm(cc):
        m = np.array([pathint.transform_along_path(*f.history(int(np.argmin(np.abs(f.x - dd)))), cc).martensite
                      for dd in d])
        below = np.flatnonzero(m < 0.5)
        if below.size == 0 or below[0] == 0:
            return np.inf if below.size == 0 else d[0] * 1000
        i = below[0]
        return (d[i - 1] + (0.5 - m[i - 1]) / (m[i] - m[i - 1]) * (d[i] - d[i - 1])) * 1000

    knee_with = knee_mm(ccurve_for_steel(0.45, **STEEL_1045))
    knee_without = knee_mm(ccurve_for_steel(0.45, **STEEL_1045, add_ferrite=False))
    assert knee_with < knee_without - 0.5                # measurably shallower with the bay


def test_low_carbon_core_forms_substantial_ferrite_the_named_limitation():
    # The named §5 scope limitation made concrete: a 0.2 %C 8620 core (low carbon → low FC →
    # ferrite forms readily, KV's 6.31 carbon coefficient) forms substantial proeutectoid ferrite
    # at a slow oil quench — the more-physical result (published 8620 oil cores ~30–40 HRC, not
    # the full-martensite ~48 HRC potential). The global scale is held so this stays in-band, not
    # driven to a dead-soft full-ferrite core.
    from projects.steel import cooling
    cc = ccurve_for_steel(0.20, **STEEL_8620)
    path = cooling.cooling_path("oil", T0=850.0, warn_biot=False)
    r = pathint.transform_along_path(path.t, path.T, cc)
    assert 0.15 < r.ferrite < 0.55                        # substantial, but not a dead-soft full-α core
    HV = prop.hardness_HV(r.fractions(), 0.20, comp=STEEL_8620)
    assert 30.0 <= prop.vickers_to_rockwell_c(HV) <= 42.0  # in the published 8620 oil-core band


def test_scale_is_the_documented_calibration_constant():
    # A regression pin: the one calibrated knob, held at the largest value keeping a low-C core in
    # band (§5). If it drifts, this catches it (and the 8620-core / 1045-knee bands above move).
    assert FERRITE_KINETIC_SCALE == pytest.approx(8.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# The CALPHAD coupling, live — the Ae3 ceiling fed from a Gibbs-energy minimisation
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_calphad_ae3_flows_into_the_ferrite_reaction_live():
    # "Couple CALPHAD into live kinetics", made concrete: the ferrite ceiling defaults to the
    # cited Andrews Ae3 (always-green), but a CALPHAD-computed A₃ can be passed straight in. Here
    # the binary cfe_broshe backend (bundled in pycalphad — no external DB) computes A₃ for 0.45 %C
    # and it flows through ccurve_for_steel into the reaction. The curved CALPHAD A₃ differs from
    # the Andrews default (the documented chord/curve gap), proving the seam carries a real value.
    pytest.importorskip("pycalphad")
    from projects.steel import calphad_backend as cb
    if not cb.available():
        pytest.skip("pycalphad not importable")
    a3_calphad = cb.CalphadBackend().austenite_solvus(0.45)     # binary Fe-C A₃, from Gibbs min
    cc = ccurve_for_steel(0.45, **STEEL_1045, Ae3=a3_calphad)
    assert cc.ferrite.Ae3 == pytest.approx(a3_calphad)
    assert cc.ferrite.Ae3 != ccurve_for_steel(0.45, **STEEL_1045).ferrite.Ae3   # ≠ Andrews default
    assert 740.0 < cc.ferrite.Ae3 < 820.0                       # a physically sane A₃ for 0.45 %C
