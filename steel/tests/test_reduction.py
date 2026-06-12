"""F1 validation: reduction thermodynamics — the Ellingham diagram (steel-making.md §7).

F1's triad, in the project's three-leg shape (mirrors test_grain.py's split of teeth vs
by-construction):

* **Analytic limit ("recover the constant").** ΔG°(T) = ΔH° − T·ΔS° is *exactly linear in T* by
  construction, so its slope recovers −ΔS° and a two-point read returns ΔH°/ΔS°. The carbon→CO
  line has a slope of the **opposite sign** to every metal-oxide line (it makes gas, they consume
  it) — the structural fact that lets carbon reduce any oxide. The crossover temperature is a
  closed-form linear intersection. Hess/path-independence (the carbon system composes) is automatic
  from per-species state-function data.
* **Conservation.** Every reaction balances each element *and* oxygen (a typo guard — balanced
  equations conserve by construction; this leg cannot fail informatively, by design).
* **Benchmark — the teeth.** From the **un-tuned, NIST/CODATA-sourced** per-species data (verified
  against NIST for the crossover-driving species before pinning), three things must land that
  *could have missed*: (1) the carbon / wüstite crossover sits in the textbook ~650–800 °C window;
  (2) the iron-oxide lines stack so the reduction sequence is Fe₂O₃ → Fe₃O₄ → FeO → Fe; (3) the
  alloy/slag-oxide hierarchy orders Ca < Al < Si < Mn < Cr < Fe (most stable → least). A fourth,
  the **honesty bound**: the linear ΔCp=0 model reproduces the famous JANAF ΔfG°(CO, 1000 K) ≈
  −200 kJ/mol anchor to within a few kJ — so the omitted-kink error is small over the working
  range. NO constant in :mod:`reduction` is fitted, so none of this is circular.
"""
import math

import pytest

from steel import reduction as red
from steel.reduction import REACTIONS as RX
from steel.kinetics import ABS_ZERO, R_GAS


# --------------------------------------------------------------------------- #
# Conservation leg — element + oxygen balance (by construction; a typo guard)
# --------------------------------------------------------------------------- #
def test_every_reaction_conserves_each_element_and_oxygen():
    for key, rxn in RX.items():
        bal = red.element_balance(rxn)
        assert red.is_balanced(rxn), f"{key} does not balance: {bal}"
        assert "O" in bal, f"{key} has no oxygen — every Ellingham reaction is an oxidation"


def test_each_reaction_carries_exactly_one_mole_O2():
    # The per-O₂ normalization is the whole reason the lines are comparable.
    for key, rxn in RX.items():
        assert rxn.reactants.get("O2") == pytest.approx(1.0), f"{key} is not normalized per mole O₂"


# --------------------------------------------------------------------------- #
# Analytic leg — linearity, slope = −ΔS, the sign opposition, the crossover
# --------------------------------------------------------------------------- #
def test_free_energy_is_exactly_linear_in_temperature():
    # ΔG(T) = ΔH − T·ΔS ⇒ the secant slope is constant and equals −ΔS (kelvin basis).
    rxn = RX["Fe->FeO"]
    slopes = []
    for Tc in (0.0, 200.0, 600.0, 1200.0):
        dT = 50.0
        g1 = red.standard_free_energy(rxn, Tc)
        g2 = red.standard_free_energy(rxn, Tc + dT)
        slopes.append((g2 - g1) / dT)
    assert all(s == pytest.approx(slopes[0], rel=1e-12) for s in slopes)
    assert slopes[0] == pytest.approx(-red.reaction_entropy(rxn), rel=1e-12)


def test_dG298_is_the_dH_minus_298_dS_identity():
    # By construction (ΔG° ≡ ΔH° − T·ΔS° at the data's reference T) — not a benchmark.
    for rxn in RX.values():
        lhs = red.standard_free_energy(rxn, 25.0)
        rhs = red.reaction_enthalpy(rxn) - (25.0 + ABS_ZERO) * red.reaction_entropy(rxn)
        assert lhs == pytest.approx(rhs, rel=1e-12)


def test_carbon_to_CO_line_slopes_down_while_oxides_slope_up():
    # The headline structural fact: 2C+O₂→2CO makes gas (ΔS>0 → line slopes DOWN); metal oxides
    # consume gas (ΔS<0 → lines slope UP). That opposite slope is *why* carbon is the universal
    # high-T reductant — its line eventually dives below every oxide line.
    assert red.reaction_entropy(RX["C->CO"]) > 0.0
    for key in red.IRON_OXIDATION_CHAIN + red.HIERARCHY_KEYS:
        assert red.reaction_entropy(RX[key]) < 0.0, f"{key} should consume O₂ gas (ΔS<0)"


def test_crossover_is_the_closed_form_intersection():
    a, b = RX["C->CO"], RX["Fe->FeO"]
    Tc = red.crossover_temperature(a, b)
    # At the crossover the two lines are equal (that is the definition).
    assert red.standard_free_energy(a, Tc) == pytest.approx(red.standard_free_energy(b, Tc), abs=1e-6)
    # Parallel lines (a reaction with itself) have no crossover.
    assert red.crossover_temperature(a, a) is None


def test_hess_path_independence_of_the_carbon_system():
    # C+O₂→CO₂ must equal (C+½O₂→CO) + (CO+½O₂→CO₂): i.e. ΔG(C->CO2) = ½[ΔG(C->CO)+ΔG(CO->CO2)],
    # an automatic consequence of building everything from per-species state functions.
    for Tc in (25.0, 500.0, 1000.0, 1500.0):
        direct = red.standard_free_energy(RX["C->CO2"], Tc)
        stepwise = 0.5 * (
            red.standard_free_energy(RX["C->CO"], Tc) + red.standard_free_energy(RX["CO->CO2"], Tc)
        )
        assert direct == pytest.approx(stepwise, rel=1e-12)


# --------------------------------------------------------------------------- #
# Benchmark — THE TEETH: crossover window, reduction sequence, hierarchy
# --------------------------------------------------------------------------- #
def test_carbon_reduces_wustite_in_the_textbook_window():
    # The classic ironmaking number: the 2C+O₂→2CO line crosses the 2Fe+O₂→2FeO line where carbon
    # begins to reduce wüstite. From un-tuned NIST data this lands ~746 °C (and ~710 °C with the
    # lower wüstite enthalpy) — both inside the generous textbook window. The window is wide ON
    # PURPOSE: the crossover is a ratio of differences of large numbers and wüstite is
    # non-stoichiometric (module ceiling), so a tight pin would be false precision, not rigor.
    Tc = red.crossover_temperature(RX["C->CO"], RX["Fe->FeO"])
    assert 650.0 < Tc < 800.0


def test_carbon_reduces_wustite_above_the_crossover_not_below():
    onset = red.reduction_onset_temperature(RX["C->CO"], RX["Fe->FeO"])
    assert onset is not None
    assert not red.reduces(RX["C->CO"], RX["Fe->FeO"], onset - 50.0)   # below: cannot
    assert red.reduces(RX["C->CO"], RX["Fe->FeO"], onset + 50.0)       # above: can
    # The onset is exactly the crossover.
    assert onset == pytest.approx(red.crossover_temperature(RX["C->CO"], RX["Fe->FeO"]))


def test_iron_oxide_lines_stack_into_the_reduction_sequence():
    # The stepwise inter-oxide reactions (6FeO+O₂→2Fe₃O₄, 4Fe₃O₄+O₂→6Fe₂O₃) must stack so that,
    # at ironmaking temperature, Fe→FeO is the most stable (bottom) and Fe₃O₄→Fe₂O₃ the least
    # (top). Reduction removes oxygen and so runs top-down: Fe₂O₃ → Fe₃O₄ → FeO → Fe.
    for Tc in (700.0, 1000.0, 1300.0):
        ordered = red.stability_order(red.IRON_OXIDATION_CHAIN, Tc)
        keys = [k for k, _ in ordered]
        assert keys == ["Fe->FeO", "FeO->Fe3O4", "Fe3O4->Fe2O3"]
        assert red.iron_reduction_sequence(Tc) == ["Fe3O4->Fe2O3", "FeO->Fe3O4", "Fe->FeO"]


def test_ellingham_hierarchy_orders_the_alloy_and_slag_oxides():
    # The classic stacked Ellingham order (most stable / most negative ΔG per O₂ first):
    # CaO < Al₂O₃ < SiO₂ < MnO < Cr₂O₃ < FeO. This is *why* Al deoxidizes everything in F2, why
    # Si/Mn are easier-lost ferroalloys in F3, and why CaO anchors a basic slag. From un-tuned data.
    keys = [k for k, _ in red.stability_order(red.HIERARCHY_KEYS + ("Fe->FeO",), 1200.0)]
    assert keys == ["Ca->CaO", "Al->Al2O3", "Si->SiO2", "Mn->MnO", "Cr->Cr2O3", "Fe->FeO"]


def test_aluminium_reduces_the_weaker_oxides_a_deoxidation_fact():
    # Aluminium's line sits below Si/Mn/Cr/Fe oxides at steelmaking temperature → Al reduces them
    # (aluminothermic / deoxidation). The coupled-reduction primitive, read the metallurgist's way.
    for weaker in ("Si->SiO2", "Mn->MnO", "Cr->Cr2O3", "Fe->FeO"):
        assert red.reduces(RX["Al->Al2O3"], RX[weaker], 1600.0)


def test_linear_model_matches_the_famous_CO_ellingham_anchor_at_1000K():
    # The honesty bound on the omitted-kink (ΔCp=0) error: the most famous point on any Ellingham
    # diagram is the CO line passing ~−200 kJ per mole CO at 1000 K (JANAF ΔfG°(CO,1000K) ≈
    # −200.2). Our straight line from 298 K data gives −199.9 — within a few kJ over 700 K of
    # extrapolation, so the linear approximation is good across the working range. (RX["C->CO"] is
    # per mole O₂ = per 2 CO, so halve it.) Generous window — bounding the error, not pinning it.
    dG_per_CO = red.standard_free_energy(RX["C->CO"], 1000.0 - ABS_ZERO) / 2.0 / 1000.0  # kJ/mol CO
    assert -205.0 < dG_per_CO < -195.0
    # CO₂ likewise sits near its near-flat ~−396 kJ/mol at 1000 K.
    dG_CO2 = red.standard_free_energy(RX["C->CO2"], 1000.0 - ABS_ZERO) / 1000.0          # kJ/mol CO₂
    assert -400.0 < dG_CO2 < -392.0


# --------------------------------------------------------------------------- #
# Equilibrium oxygen potential — the pO₂ consistency checks
# --------------------------------------------------------------------------- #
def test_equilibrium_pO2_is_lower_for_the_more_stable_oxide():
    # A more stable oxide (lower ΔG line) clings to its oxygen harder → needs a *lower* equilibrium
    # p_O₂ to coexist with its metal. So at fixed T, p_O₂ rises Ca→Al→Si→Mn→Cr→Fe (stability falls).
    order = ["Ca->CaO", "Al->Al2O3", "Si->SiO2", "Mn->MnO", "Cr->Cr2O3", "Fe->FeO"]
    pO2 = [red.equilibrium_oxygen_pressure(RX[k], 1000.0) for k in order]
    assert all(pO2[i] < pO2[i + 1] for i in range(len(pO2) - 1))
    assert all(p > 0.0 for p in pO2)             # a pressure, always positive


def test_equilibrium_pO2_rises_with_temperature():
    # Oxides get less stable as they heat (ΔG climbs toward 0) → the equilibrium p_O₂ rises.
    rxn = RX["Fe->FeO"]
    pressures = [red.equilibrium_oxygen_pressure(rxn, Tc) for Tc in (600.0, 900.0, 1200.0, 1500.0)]
    assert all(pressures[i] < pressures[i + 1] for i in range(len(pressures) - 1))


def test_equilibrium_pO2_recovers_dG_through_RTlnK():
    # Round-trip: ΔG° = R·T·ln(p_O₂,eq). The definition, checked numerically.
    rxn = RX["Cr->Cr2O3"]
    Tc = 1100.0
    pO2 = red.equilibrium_oxygen_pressure(rxn, Tc)
    assert R_GAS * (Tc + ABS_ZERO) * math.log(pO2) == pytest.approx(
        red.standard_free_energy(rxn, Tc), rel=1e-9
    )


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_below_absolute_zero_raises():
    with pytest.raises(ValueError):
        red.standard_free_energy(RX["Fe->FeO"], -300.0)
    with pytest.raises(ValueError):
        red.equilibrium_oxygen_pressure(RX["Fe->FeO"], -300.0)
