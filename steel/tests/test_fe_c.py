"""Phase-1b validation triad for the metastable Fe–Fe₃C lever rule (Steel plan §3).

Three legs, kept deliberately separate (an "exact" leg must not inherit textbook
round-off):

* **Analytical limit** — (a) the pinned invariant points are reproduced *exactly*
  (eutectoid 0.76 %/727 °C, γ-max 2.11 %/1147 °C, pure-iron A₃ 912 °C), and
  (b) lever-rule fractions are exact at chosen (T, %C) points, derived from the
  module's *own* constants and asserted to ~1e-14.
* **Conservation** — the lever rule is a carbon mass balance, so ``Σ fᵢ·Cᵢ = C0``
  to machine precision; phase fractions sum to 1 and stay in [0, 1] across the
  diagram; and the constituent reading re-sums to the phase reading.
* **Benchmark** — a *separate, looser* comparison to published textbook facts
  (AISI 1045 ~42 % pro-eutectoid ferrite; pearlite ~11 % cementite; the near-
  degenerate 1080), where conventions vary at the ~1 % level.

Also pins the documented 727 °C eutectoid-isotherm convention and the input
guards.
"""
import numpy as np
import pytest

from steel.fe_c import (
    A1, A3, Acm,
    austenite_C_with_ferrite, austenite_C_with_cementite, ferrite_C,
    phase_fractions, equilibrium_constituents, Constituents,
    PEARLITE_CEMENTITE_FRACTION,
    C_EUTECTOID, T_EUTECTOID, T_A3_PURE_IRON,
    C_GAMMA_MAX, T_GAMMA_MAX, C_ALPHA_MAX, C_CEMENTITE,
)

EXACT = dict(rel=0.0, abs=1e-14)  # the analytical-limit tolerance


# --------------------------------------------------------------------------- #
# Analytical limit (a): pinned invariant points reproduced exactly
# --------------------------------------------------------------------------- #
def test_invariant_points_exact():
    assert A1() == 727.0
    # A₃ pins: 912 °C at 0 % C (pure iron) → 727 °C at the eutectoid.
    assert A3(0.0) == pytest.approx(T_A3_PURE_IRON, **EXACT)
    assert A3(C_EUTECTOID) == pytest.approx(T_EUTECTOID, **EXACT)
    # A_cm pins: 727 °C at the eutectoid → 1147 °C at γ-max (2.11 %).
    assert Acm(C_EUTECTOID) == pytest.approx(T_EUTECTOID, **EXACT)
    assert Acm(C_GAMMA_MAX) == pytest.approx(T_GAMMA_MAX, **EXACT)


def test_boundary_composition_inverses_exact():
    # γ-side composition lines (the tie-line ends) hit the same invariant points.
    assert austenite_C_with_ferrite(T_EUTECTOID) == pytest.approx(C_EUTECTOID, **EXACT)
    assert austenite_C_with_ferrite(T_A3_PURE_IRON) == pytest.approx(0.0, **EXACT)
    assert austenite_C_with_cementite(T_EUTECTOID) == pytest.approx(C_EUTECTOID, **EXACT)
    assert austenite_C_with_cementite(T_GAMMA_MAX) == pytest.approx(C_GAMMA_MAX, **EXACT)
    # Ferrite solvus: 0.022 % at the eutectoid, pinching to 0 % at pure-iron A₃.
    assert ferrite_C(T_EUTECTOID) == pytest.approx(C_ALPHA_MAX, **EXACT)
    assert ferrite_C(T_A3_PURE_IRON) == pytest.approx(0.0, **EXACT)
    # the α+γ field closes to a point at 912 °C: both ends → 0 there.
    assert austenite_C_with_ferrite(T_A3_PURE_IRON) == ferrite_C(T_A3_PURE_IRON)


def test_gamma_max_invariant_point_is_single_phase():
    # (2.11 %, 1147 °C) is the tip of the austenite field — fully γ.
    f = phase_fractions(C_GAMMA_MAX, T_GAMMA_MAX)
    assert f == {"ferrite": 0.0, "austenite": 1.0, "cementite": 0.0}


# --------------------------------------------------------------------------- #
# Analytical limit (b): exact lever-rule fractions at chosen (T, %C)
# --------------------------------------------------------------------------- #
def test_lever_rule_exact_hypoeutectoid_at_eutectoid_line():
    # AISI 1045 just above A₁: α (0.022 %) + γ (0.76 %). The eutectoid-line split,
    # exact because T = 727 selects the pinned boundary compositions by convention.
    C0 = 0.45
    f = phase_fractions(C0, T_EUTECTOID)
    expect_ferrite = (C_EUTECTOID - C0) / (C_EUTECTOID - C_ALPHA_MAX)
    assert f["ferrite"] == pytest.approx(expect_ferrite, **EXACT)
    assert f["austenite"] == pytest.approx(1.0 - expect_ferrite, **EXACT)
    assert f["cementite"] == 0.0


def test_lever_rule_exact_hypereutectoid_at_eutectoid_line():
    # A 1.0 % C steel just above A₁: γ (0.76 %) + Fe₃C (6.70 %).
    C0 = 1.0
    f = phase_fractions(C0, T_EUTECTOID)
    expect_cem = (C0 - C_EUTECTOID) / (C_CEMENTITE - C_EUTECTOID)
    assert f["cementite"] == pytest.approx(expect_cem, **EXACT)
    assert f["austenite"] == pytest.approx(1.0 - expect_cem, **EXACT)
    assert f["ferrite"] == 0.0


def test_lever_rule_exact_subcritical_ferrite_cementite():
    # Below A₁: α (held at 0.022 %) + Fe₃C (6.70 %); fixed end-members, so exact.
    C0, T = 0.50, 600.0
    f = phase_fractions(C0, T)
    expect_cem = (C0 - C_ALPHA_MAX) / (C_CEMENTITE - C_ALPHA_MAX)
    assert f["cementite"] == pytest.approx(expect_cem, **EXACT)
    assert f["ferrite"] == pytest.approx(1.0 - expect_cem, **EXACT)
    assert f["austenite"] == 0.0


# --------------------------------------------------------------------------- #
# Single-phase guards (no lever rule where the tie-line has no width)
# --------------------------------------------------------------------------- #
def test_single_phase_austenite_above_transus():
    # 0.45 % C at 900 °C is above A₃(0.45)=802.5 °C → fully austenite.
    assert phase_fractions(0.45, 900.0) == {"ferrite": 0.0, "austenite": 1.0, "cementite": 0.0}


def test_single_phase_ferrite_below_solvus():
    # 0.01 % C (< 0.022 %) at 600 °C sits left of the ferrite solvus → all ferrite.
    assert phase_fractions(0.01, 600.0) == {"ferrite": 1.0, "austenite": 0.0, "cementite": 0.0}


def test_single_phase_ferrite_in_low_carbon_wedge_above_727():
    # The α+γ-side wedge (0 ≤ C0 < ferrite solvus, 727 < T < 912): pure iron and a
    # trace-carbon steel at 800 °C are single-phase ferrite — NOT a lever-rule point
    # (a missing guard here yields an unphysical negative austenite fraction).
    pure = {"ferrite": 1.0, "austenite": 0.0, "cementite": 0.0}
    assert phase_fractions(0.0, 800.0) == pure
    assert phase_fractions(0.01, 800.0) == pure  # C0 < ferrite_C(800) ≈ 0.0133


def test_eutectoid_point_is_single_phase_austenite():
    # The eutectoid point itself is the bottom tip of the γ field (convention: the
    # austenite-bearing side of the isotherm).
    assert phase_fractions(C_EUTECTOID, T_EUTECTOID) == {
        "ferrite": 0.0, "austenite": 1.0, "cementite": 0.0
    }


# --------------------------------------------------------------------------- #
# The 727 °C eutectoid-isotherm convention (the documented discontinuity)
# --------------------------------------------------------------------------- #
def test_eutectoid_isotherm_convention():
    C0 = 0.45
    above = phase_fractions(C0, T_EUTECTOID)       # T == 727 → austenite-bearing
    below = phase_fractions(C0, T_EUTECTOID - 1.0)  # 726 → α + Fe₃C
    assert above["austenite"] > 0.0 and above["cementite"] == 0.0
    assert below["austenite"] == 0.0 and below["cementite"] > 0.0
    # Crossing A₁ destroys austenite (the eutectoid reaction): a real jump.
    assert above["ferrite"] < below["ferrite"]


# --------------------------------------------------------------------------- #
# Conservation: Σ fᵢCᵢ = C0, fractions sum to 1 and stay in [0, 1]
# --------------------------------------------------------------------------- #
def _austenite_carbon(C0: float, T: float) -> float:
    """The γ-side tie-line composition for the field that (C0, T) lands in."""
    return austenite_C_with_ferrite(T) if C0 <= C_EUTECTOID else austenite_C_with_cementite(T)


@pytest.mark.parametrize(
    "C0, T",
    [
        (0.30, 760.0),  # hypoeutectoid α + γ
        (1.20, 850.0),  # hypereutectoid γ + Fe₃C
        (0.50, 650.0),  # subcritical α + Fe₃C
        (0.05, 727.0),  # near-pure-iron α + γ at the isotherm
    ],
)
def test_carbon_conservation_two_phase(C0, T):
    f = phase_fractions(C0, T)
    carbon = f["ferrite"] * ferrite_C(min(T, T_A3_PURE_IRON)) + f["cementite"] * C_CEMENTITE
    if f["austenite"] > 0.0:  # the γ-side boundary is only defined where γ exists
        carbon += f["austenite"] * _austenite_carbon(C0, T)
    assert carbon == pytest.approx(C0, rel=0.0, abs=1e-13)


def test_phase_fractions_sum_to_one_and_bounded_across_diagram():
    # C0=0.0 (pure iron) probes the low-carbon ferrite wedge above 727 °C, where a
    # missing single-phase guard would surface as a negative austenite fraction.
    for C0 in [0.0, 0.05, 0.20, 0.45, 0.76, 1.00, 1.50, 2.00, 2.11]:
        for T in [500.0, 650.0, 727.0, 760.0, 850.0, 950.0, 1100.0]:
            f = phase_fractions(C0, T)
            total = f["ferrite"] + f["austenite"] + f["cementite"]
            assert total == pytest.approx(1.0, rel=0.0, abs=1e-12), (C0, T)
            assert min(f.values()) >= -1e-15, (C0, T)  # no negative (wrong field) fractions
            assert max(f.values()) <= 1.0 + 1e-12, (C0, T)


# --------------------------------------------------------------------------- #
# Constituents: conservation + the constituent ↔ phase consistency
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("C0", [0.20, 0.45, 0.76, 0.80, 1.20, 2.00])
def test_constituents_fractions_sum_to_one(C0):
    c = equilibrium_constituents(C0)
    assert c.f_proeutectoid + c.f_pearlite == pytest.approx(1.0, **EXACT)
    assert c.f_ferrite_total + c.f_cementite_total == pytest.approx(1.0, **EXACT)


@pytest.mark.parametrize("C0", [0.20, 0.45, 0.76, 0.80, 1.20, 2.00])
def test_constituents_conserve_carbon(C0):
    c = equilibrium_constituents(C0)
    # phase reading: total ferrite/cementite at their fixed compositions
    by_phase = c.f_ferrite_total * C_ALPHA_MAX + c.f_cementite_total * C_CEMENTITE
    assert by_phase == pytest.approx(C0, rel=0.0, abs=1e-13)
    # constituent reading: pro-eutectoid phase + pearlite (at the eutectoid comp)
    c_pro = C_ALPHA_MAX if c.proeutectoid == "ferrite" else C_CEMENTITE
    by_constituent = c.f_proeutectoid * c_pro + c.f_pearlite * C_EUTECTOID
    if c.proeutectoid != "none":
        assert by_constituent == pytest.approx(C0, rel=0.0, abs=1e-13)


@pytest.mark.parametrize("C0", [0.20, 0.45])
def test_constituents_resum_to_phase_reading_hypoeutectoid(C0):
    # Resolving pearlite into its α+Fe₃C lamellae must reproduce the total phases.
    c = equilibrium_constituents(C0)
    cem_from_pearlite = c.f_pearlite * PEARLITE_CEMENTITE_FRACTION
    fer_from_pearlite = c.f_pearlite * (1.0 - PEARLITE_CEMENTITE_FRACTION)
    assert c.f_cementite_total == pytest.approx(cem_from_pearlite, **EXACT)
    assert c.f_ferrite_total == pytest.approx(c.f_proeutectoid + fer_from_pearlite, **EXACT)


@pytest.mark.parametrize("C0", [0.20, 0.45, 0.80, 1.20])
def test_pearlite_equals_austenite_at_eutectoid_line(C0):
    # The pearlite fraction IS the austenite present just above A₁ that transforms.
    c = equilibrium_constituents(C0)
    assert c.f_pearlite == pytest.approx(phase_fractions(C0, T_EUTECTOID)["austenite"], **EXACT)


# --------------------------------------------------------------------------- #
# Benchmark (separate, looser — published textbook facts; conventions vary ~1 %)
# --------------------------------------------------------------------------- #
def test_benchmark_aisi_1045_proeutectoid_split():
    # AISI 1045 (0.45 % C) — the plan's showcase of the dramatic hypoeutectoid
    # split (Callister-convention constants): ~42 % pro-eutectoid ferrite / 58 %
    # pearlite.
    c = equilibrium_constituents(0.45)
    assert c.proeutectoid == "ferrite"
    assert c.f_proeutectoid == pytest.approx(0.42, abs=5e-3)
    assert c.f_pearlite == pytest.approx(0.58, abs=5e-3)


def test_benchmark_aisi_1080_is_near_degenerate_cementite():
    # AISI 1080 (0.80 % C) is *slightly* hypereutectoid — the plan's degenerate
    # contrast: a thin pro-eutectoid CEMENTITE network, ~0.7 %, not ferrite, not 0.
    c = equilibrium_constituents(0.80)
    assert c.proeutectoid == "cementite"
    assert c.f_proeutectoid < 0.01
    assert c.f_pearlite > 0.99


def test_benchmark_pearlite_is_about_eleven_percent_cementite():
    # The classic value: pearlite (0.76 % C) is ~11 % cementite, ~89 % ferrite.
    assert 0.10 < PEARLITE_CEMENTITE_FRACTION < 0.12


# --------------------------------------------------------------------------- #
# Input guards
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad_C0", [-0.1, 3.0, 6.70])
def test_phase_fractions_rejects_out_of_range_carbon(bad_C0):
    with pytest.raises(ValueError):
        phase_fractions(bad_C0, 800.0)


@pytest.mark.parametrize("bad_C0", [-0.1, 2.5])
def test_equilibrium_constituents_rejects_out_of_range_carbon(bad_C0):
    with pytest.raises(ValueError):
        equilibrium_constituents(bad_C0)


def test_boundary_functions_reject_wrong_side():
    with pytest.raises(ValueError):
        A3(1.0)   # hypereutectoid — not on the A₃ branch
    with pytest.raises(ValueError):
        Acm(0.5)  # hypoeutectoid — not on the A_cm branch
    with pytest.raises(ValueError):
        ferrite_C(1000.0)  # above pure-iron A₃
