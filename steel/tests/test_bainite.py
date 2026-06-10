"""Phase-6b validation: the cited bainite reaction, and the proven negative result.

Phase 6b set out to give bainite its **own** competing C-curve so the *bainite bay* would open in
the continuous-cooling microstructure (the named §4 simplification: one factor shifts pearlite and
bainite together). A four-round empirical investigation (see :mod:`kinetics` §6) proved the bay
**cannot be realised in this model** — and the corrected understanding is itself the Phase-6b
content (the same "design-fork" lesson as 6a). So 6b delivers the *cited* bainite reaction as a
**standalone** kinetic object, NOT wired into :mod:`pathint` (the crude 540-split is left untouched,
because at any scale keeping the 8620 core in its hardness band a competing bainite forms negligibly
in the benchmark and would only *regress* the morphology-correct split).

The triad, each leg anchored to its own discipline:

* **Analytical / structural** — the cited Li/KV ``BC`` and Steven–Haynes ``Bs`` reproduce the
  published coefficients exactly; the undercooling exponent is ``ΔT¹`` (Li 1998 for bainite, NOT the
  ``ΔT³`` of ferrite/pearlite); the rate vanishes at/above ``Bs``; the isothermal time-to-fraction
  matches the shape integral ``S(X)/K`` (the "recover the constant" leg).
* **The teeth (cited, scale-free)** — alloy retards the displacive bainite reaction *far less* than
  the reconstructive ferrite/pearlite reaction (``BC`` Cr/Mo ≪ ``FC`` Cr/Mo): the **mechanism** of
  the bay, purely the published coefficients, independent of any calibration.
* **The negative result (durable)** — the ``BC`` carbon coefficient (10.18) makes low-carbon bainite
  explode, so the 0.20 %C 8620 core has the fastest bainite of any benchmark steel; this is the
  carbon-spread that forces the 8620 hardness-band ceiling and the decision to leave :mod:`pathint`
  byte-identical (the 540-split untouched).
"""
import math

import numpy as np
import pytest

from steel import kinetics as k
from steel.kinetics import (
    BainiteReaction, bainite_reaction_for_steel, bainite_BC, steven_haynes_Bs, ferrite_FC,
    BAINITE_BC_COEFFS, BAINITE_UNDERCOOLING_EXP, STEVEN_HAYNES_BS_COEFFS, BS_DEFAULT,
    FERRITE_FC_COEFFS, ccurve_for_steel, KV_Q, R_CAL, ABS_ZERO, FERRITE_ASTM_GRAIN,
)

STEEL_1045 = dict(Mn=0.75, Si=0.22)
STEEL_4140 = dict(Mn=0.90, Cr=1.0, Mo=0.20, Si=0.25)
STEEL_8620 = dict(Mn=0.80, Ni=0.55, Cr=0.50, Mo=0.20, Si=0.25)   # 0.20 %C carburising core


# --------------------------------------------------------------------------- #
# Analytical / structural: the cited coefficients, the ΔT¹ form, the ceiling
# --------------------------------------------------------------------------- #
def test_bainite_BC_matches_cited_li_kv_coefficients():
    # BC = exp(-10.23 + 10.18C + 0.85Mn + 0.55Ni + 0.90Cr + 0.36Mo) — Li (1998) / Kirkaldy–
    # Venugopalan. Pin the exact exponent so a coefficient drift is caught, and confirm the WEAK
    # Cr (0.90) / Mo (0.36) retarders the teeth rely on.
    expo = (-10.23 + 10.18 * 0.40 + 0.85 * 0.90 + 0.55 * 0.0 + 0.90 * 1.0 + 0.36 * 0.20)
    assert bainite_BC(0.40, **{key: STEEL_4140[key] for key in ("Mn", "Cr", "Mo")}) == pytest.approx(np.exp(expo), rel=1e-12)
    assert BAINITE_BC_COEFFS["C"] == 10.18 and BAINITE_BC_COEFFS["Cr"] == 0.90 and BAINITE_BC_COEFFS["Mo"] == 0.36


def test_steven_haynes_Bs_matches_cited_coefficients():
    # Bs = 830 - 270C - 90Mn - 37Ni - 70Cr - 83Mo (Steven & Haynes 1956). Pin the coefficients and a
    # known value: 4140 ≈ 554 °C, plain-carbon eutectoid ≈ 551 °C.
    assert STEVEN_HAYNES_BS_COEFFS == {"C": -270.0, "Mn": -90.0, "Ni": -37.0, "Cr": -70.0, "Mo": -83.0}
    assert steven_haynes_Bs(0.40, Mn=0.90, Cr=1.0, Mo=0.20) == pytest.approx(554.4, abs=0.1)
    assert steven_haynes_Bs(0.80, Mn=0.70) == pytest.approx(551.0, abs=0.1)
    # Every alloying addition lowers Bs (narrows the bainite window).
    assert steven_haynes_Bs(0.40, Mn=0.90, Cr=1.0, Mo=0.20) < steven_haynes_Bs(0.40)


def test_undercooling_exponent_is_one_not_three_and_rate_form_is_cited():
    # Bainite uses ΔT¹ (Li 1998), NOT the ΔT³ of ferrite/pearlite — the one easy place to slip.
    assert BAINITE_UNDERCOOLING_EXP == 1.0
    br = bainite_reaction_for_steel(0.40, **STEEL_4140)
    # Recompute K(T) by hand to pin the whole cited rate form: scale·2^(0.41G)·(Bs-T)¹·exp(-Q/RT)/BC.
    T = 480.0
    expected = (br.scale * 2.0 ** (0.41 * FERRITE_ASTM_GRAIN) * (br.Bs - T)
                * math.exp(-KV_Q / (R_CAL * (T + ABS_ZERO))) / br.BC)
    assert br.rate(T) == pytest.approx(expected, rel=1e-12)
    # ΔT¹ (linear): at a fixed temperature the rate is exactly proportional to the ceiling undercooling.
    hot = BainiteReaction(Bs=br.Bs + 100.0, BC=br.BC)       # +100 °C more undercooling at the same T
    assert hot.rate(T) / br.rate(T) == pytest.approx((hot.Bs - T) / (br.Bs - T), rel=1e-12)


def test_rate_is_zero_at_and_above_Bs():
    br = bainite_reaction_for_steel(0.45, **STEEL_1045)
    assert br.rate(br.Bs) == 0.0
    assert br.rate(br.Bs + 50.0) == 0.0
    assert br.rate(br.Bs - 100.0) > 0.0                     # active below the ceiling


def test_isothermal_time_to_fraction_matches_shape_integral():
    # The "recover the constant" leg: for a site-saturation reaction dU/dt = K(T)·g(U), the isothermal
    # time to fraction X is t = S(X)/K(T) (separable). Step the completion at a fixed T and confirm the
    # time to reach X agrees with S(X)/K to integration accuracy.
    br = bainite_reaction_for_steel(0.45, **STEEL_1045)
    T = 0.5 * (200.0 + br.Bs)
    X = 0.5
    K = br.rate(T)
    dt = (k._kv_shape_integral(X) / K) / 50000.0            # fine, fixed step
    U = 0.0
    t = 0.0
    while U < X and t < 1e9:
        U = br.completion_step(U, T, dt)
        t += dt
    assert t == pytest.approx(k._kv_shape_integral(X) / K, rel=2e-3)


# --------------------------------------------------------------------------- #
# The teeth: alloy retards bainite far less than ferrite — the bay MECHANISM (scale-free)
# --------------------------------------------------------------------------- #
def test_alloy_retards_bainite_far_less_than_ferrite_the_bay_mechanism():
    # THE TEETH (the §4 fix at the mechanism level, independent of any calibration): the displacive
    # bainite reaction is retarded WEAKLY by Cr/Mo while the reconstructive ferrite reaction is
    # retarded STRONGLY. For 4140's alloy additions the bainite slows ~5.7× but ferrite ~166× — the
    # bay's cause, set entirely by the published BC/FC coefficients.
    add = dict(Mn=0.90, Cr=1.0, Mo=0.20)
    bain_ret = bainite_BC(0.40, **add) / bainite_BC(0.40)   # how much alloy retards bainite
    ferr_ret = ferrite_FC(0.40, **add) / ferrite_FC(0.40)   # how much alloy retards ferrite
    assert bain_ret < ferr_ret
    assert ferr_ret / bain_ret > 10.0                       # a wide, cited margin (the bay opens here in TTT-space)
    # The Cr/Mo coefficients themselves are the source — bainite's are far the smaller.
    assert BAINITE_BC_COEFFS["Cr"] < FERRITE_FC_COEFFS["Cr"]
    assert BAINITE_BC_COEFFS["Mo"] < FERRITE_FC_COEFFS["Mo"]


# --------------------------------------------------------------------------- #
# The isothermal demonstration: the reaction is real and has its own nose
# --------------------------------------------------------------------------- #
def test_isothermal_hold_transforms_below_Bs_and_is_inert_above():
    # Where the reaction genuinely lives: held below Bs the completion U rises monotonically toward 1;
    # held at/above Bs it never ignites (rate 0).
    br = bainite_reaction_for_steel(0.40, **STEEL_4140)
    T = 0.5 * (250.0 + br.Bs)
    U, prev, dt = 0.0, -1.0, 1.0
    for _ in range(4000):
        U = br.completion_step(U, T, dt)
        assert U >= prev                                    # monotone
        prev = U
    assert U > 0.99                                         # essentially complete after a long hold
    # Above the ceiling: inert.
    U_above = 0.0
    for _ in range(4000):
        U_above = br.completion_step(U_above, br.Bs + 20.0, dt)
    assert U_above == 0.0


def test_bainite_nose_is_the_fastest_time_and_below_Bs():
    # The bainite C-curve has its own nose (the fastest time to a fraction): below the ceiling, and a
    # genuine minimum — the time at the nose is shorter than at temperatures above and below it.
    br = bainite_reaction_for_steel(0.45, **STEEL_1045)
    T_nose, t_nose = br.nose(X=0.01)
    assert 100.0 < T_nose < br.Bs
    assert math.isfinite(t_nose) and t_nose > 0.0
    S = k._kv_shape_integral(0.01)
    for dT in (-80.0, 80.0):
        T = T_nose + dT
        if 100.0 < T < br.Bs:
            assert S / br.rate(T) > t_nose                  # the nose is the minimum


# --------------------------------------------------------------------------- #
# The negative result (durable): the carbon spread, and pathint left byte-identical
# --------------------------------------------------------------------------- #
def test_low_carbon_bainite_explodes_the_8620_ceiling():
    # THE NEGATIVE RESULT, made concrete (why the reaction is NOT wired into the benchmark): BC's large
    # carbon coefficient (10.18) makes low-carbon bainite explode. The 0.20 %C 8620 core has the
    # FASTEST bainite of any benchmark steel — far faster than 0.45 %C 1045 — so any competing scale
    # large enough to put bainite into 1045/4140 drives the 8620 oil core out of its 30–40 HRC band.
    # Smaller BC ⇒ faster reaction, so this asserts the carbon spread directly.
    bc_8620 = bainite_BC(0.20, **{key: STEEL_8620[key] for key in ("Mn", "Ni", "Cr", "Mo")})
    bc_1045 = bainite_BC(0.45, Mn=0.75)
    assert bc_8620 < bc_1045                                # 8620 bainite is faster (smaller BC)
    assert bc_1045 / bc_8620 > 5.0                          # by a wide, carbon-driven margin


def test_bainite_reaction_is_standalone_pathint_540_split_untouched():
    # The design decision the negative result forces: the bainite reaction is standalone — NOT attached
    # to a CCurve, NOT integrated into pathint. The continuous-cooling pearlite/bainite morphology
    # split is still the fixed BS_DEFAULT (540 °C), unchanged by 6b. (Wiring a competing bainite would
    # regress this morphology-correct split at every 8620-safe scale — see the module §6.)
    assert BS_DEFAULT == 540.0
    cc = ccurve_for_steel(0.45, **STEEL_1045)
    assert cc.Bs == 540.0                                   # the split is untouched, not the Steven–Haynes Bs
    assert not hasattr(cc, "bainite")                       # no bainite reaction is carried on the curve
