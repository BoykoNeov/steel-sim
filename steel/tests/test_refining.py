"""Tests for F2 primary refining (Slice 1): decarburization, deoxidation, Sieverts degassing + the seam.

The non-circularity split (as in ``test_casting.py`` / ``test_reduction.py``):

* **Teeth (could-have-missed):** the carbon–oxygen product lands on its cited ≈ 0.0022 anchor; the
  deoxidizer hierarchy Al ≫ Si > Mn is **computed** from the pinned constants *and* matches the F1
  Ellingham oxide-stability order (the cross-module coherence the plan claims, verified not asserted); the
  Sieverts √p law is exact and the H/N solubilities hit their cited liquid-iron anchors; the Al–O curve has
  a real **minimum** the dilute cartoon misses, at the cited ~0.07 % location; the C–O coupling is inverse
  (less carbon → more oxygen); and the deoxidation mass balance closes (oxygen removed = oxygen bound in
  the generated oxide).
* **By construction (NOT teeth):** ``equilibrium_oxygen = product/carbon``, ``vacuum_for_gas_target``
  inverts ``sieverts_solubility``, ``deoxidation_constant = exp(−ΔG°/RT)``. They guard transcription, they
  cannot fail informatively.

The seam tests pin that the orchestrator fills the right ``Heat`` fields and raises the right flags; the
end-to-end carbon-axis propagation (over-blow → a back-end soft core) is exercised in ``test_demo_refining``.
"""
import math
from dataclasses import replace

import numpy as np
import pytest

from steel import refining as rf
from steel import reduction as red
from steel.refining import (
    DEOXIDIZERS, GASES, carbon_oxygen_product, equilibrium_oxygen, deoxidation_constant,
    equilibrium_oxygen_after_deox, aluminium_oxygen_minimum, deoxidizing_power, generated_oxide,
    sieverts_solubility, vacuum_for_gas_target, from_hot_metal, decarburize, deoxidize, degas,
    MAX_DISSOLVED_OXYGEN_PPM, MAX_HYDROGEN_PPM, POROSITY_RISK, HYDROGEN_FLAKING_RISK,
)
from steel.heat_state import Heat, SOFT_CORE
from steel.sweep import Steel, STEELS


# --------------------------------------------------------------------------- #
# Decarburization — the carbon–oxygen product (teeth) + the inverse coupling
# --------------------------------------------------------------------------- #
def test_carbon_oxygen_product_hits_the_cited_anchor():
    # The famous converter number: [%C][%O] ≈ 0.0022 at 1600 °C, 1 atm CO (≈ 22 ppm·%C). Un-tuned — it
    # falls out of the cited ΔG° = −19840 − 40.65·T, so landing in the window is a real tooth.
    p = carbon_oxygen_product(1600.0, p_CO=1.0)
    assert 0.0018 < p < 0.0026, f"C–O product {p} off the ~0.0022 anchor"


def test_oxygen_climbs_as_carbon_is_blown_down():
    # The inverse coupling that makes the whole story: carbon-saturated charge is low-oxygen, the blow
    # lifts oxygen as it drops carbon. Strictly monotone decreasing in carbon.
    o = [equilibrium_oxygen(c) for c in (4.5, 0.80, 0.40, 0.20, 0.05)]
    assert o == sorted(o)                                   # rises as carbon falls
    assert o[0] < 10.0 and o[-1] > 300.0                   # ~5 ppm at the charge, ~400 ppm at 0.05 %C


def test_lower_p_CO_decarburizes_without_the_oxygen_penalty():
    # Vacuum decarburization (the RH/VOD lever): dropping p_CO lowers the product, so the same carbon sits
    # at lower oxygen — the reason vacuum routes exist.
    assert equilibrium_oxygen(0.05, p_CO=0.1) < equilibrium_oxygen(0.05, p_CO=1.0)


def test_equilibrium_oxygen_rejects_zero_carbon():
    with pytest.raises(ValueError):
        equilibrium_oxygen(0.0)                            # the product diverges as %C → 0


# --------------------------------------------------------------------------- #
# Deoxidation — the hierarchy (computed, + F1 coherence), the minimum, the balance
# --------------------------------------------------------------------------- #
def test_deoxidizer_hierarchy_is_aluminium_strongest():
    # Computed from the pinned constants, not asserted: at equal addition aluminium leaves the least
    # dissolved oxygen, then silicon, then manganese.
    order = [sym for sym, _ in deoxidizing_power(0.05)]
    assert order == ["Al", "Si", "Mn"]


def test_deox_hierarchy_matches_the_f1_ellingham_order():
    # The cross-module coherence the plan claims (steel-making.md §7 / F1's p_O₂ ladder): F2's
    # dissolved-state deoxidizing power must rank the SAME way as F1's pure-oxide Ellingham stability
    # (Al₂O₃ < SiO₂ < MnO). The two are INDEPENDENTLY sourced (Henrian deox constants vs Raoultian ΔG°f),
    # so their agreement is an observation worth verifying — computed from both sides, not assumed.
    f2_order = [sym for sym, _ in deoxidizing_power(0.05)]
    f1_keys = {"Al": "Al->Al2O3", "Si": "Si->SiO2", "Mn": "Mn->MnO"}
    # F1 stability_order returns most-stable (most negative ΔG°) first = strongest oxygen affinity first.
    f1_order = [k for k, _ in red.stability_order(tuple(f1_keys.values()), 1600.0)]
    f1_symbols = [s for k in f1_order for s, kk in f1_keys.items() if kk == k]
    assert f2_order == f1_symbols == ["Al", "Si", "Mn"]


def test_aluminium_oxygen_curve_has_a_minimum_the_cartoon_misses():
    d = DEOXIDIZERS["Al"]
    al = [0.005, 0.02, 0.074, 0.2, 0.5]
    with_int = [equilibrium_oxygen_after_deox(d, a) for a in al]
    dilute = [equilibrium_oxygen_after_deox(d, a, with_interaction=False) for a in al]
    # The real (interaction) curve is NOT monotone — it dips then rises (the minimum); the dilute cartoon
    # falls monotonically (it silently drops the diagram's most famous feature).
    assert with_int != sorted(with_int, reverse=True)      # has an interior minimum
    assert dilute == sorted(dilute, reverse=True)          # monotone fall (no minimum)


def test_aluminium_minimum_location_is_cited_and_K_independent():
    al_min, o_min = aluminium_oxygen_minimum(1600.0)
    assert 0.05 < al_min < 0.10                            # the cited ~0.07 % location
    assert 2.0 < o_min < 8.0                               # a few ppm — clean killed-steel oxygen
    # K-invariance, tested on the CURVE not the formula: find the argmin numerically for the real K and a
    # shifted K — the minimum sits at the same [Al] (it depends on e_O^Al alone). This can fail if the
    # location did move, unlike asserting the closed form equals itself.
    d = DEOXIDIZERS["Al"]
    shifted = replace(d, dG_A=d.dG_A - 20000.0)            # a different (scaled) K_Al
    al = np.linspace(0.01, 0.30, 3000)
    loc_real = al[int(np.argmin([equilibrium_oxygen_after_deox(d, float(a)) for a in al]))]
    loc_shift = al[int(np.argmin([equilibrium_oxygen_after_deox(shifted, float(a)) for a in al]))]
    assert loc_real == pytest.approx(loc_shift, abs=2e-3)
    assert loc_real == pytest.approx(al_min, abs=2e-3)     # and the numeric argmin matches the closed form


def test_deoxidation_mass_balance_oxygen_removed_equals_oxygen_in_oxide():
    # Conservation tooth: the oxygen pulled from the melt is exactly the oxygen bound in the generated
    # oxide (mass_oxide × O-mass-fraction = mass of O removed). Not a tautology — it crosses the
    # stoichiometric oxide composition.
    for sym in ("Al", "Si", "Mn"):
        d = DEOXIDIZERS[sym]
        O_removed_ppm = 50.0
        mass_oxide, vol_oxide = generated_oxide(O_removed_ppm, d)
        assert mass_oxide * d.oxide_O_mass_frac == pytest.approx(O_removed_ppm * 1e-6, rel=1e-9)
        assert vol_oxide > 0.0
    assert generated_oxide(0.0, DEOXIDIZERS["Al"]) == (0.0, 0.0)


def test_deoxidation_constant_is_definitional():
    # By construction (NOT teeth): K = exp(−ΔG°/RT).
    d = DEOXIDIZERS["Al"]
    T = 1600.0 + 273.15
    assert deoxidation_constant(d, 1600.0) == pytest.approx(math.exp(-(d.dG_A + d.dG_B * T) / (8.314462618 * T)))


# --------------------------------------------------------------------------- #
# Degassing — Sieverts √p (exact) + the cited solubility anchors
# --------------------------------------------------------------------------- #
def test_sieverts_is_exactly_square_root_in_pressure():
    # The law's whole content: a diatomic gas dissolves as atoms, so solubility ∝ √p. Quadrupling the
    # pressure exactly doubles the dissolved gas — for both H and N.
    for gas in ("H", "N"):
        assert sieverts_solubility(gas, 4.0) == pytest.approx(2.0 * sieverts_solubility(gas, 1.0))
        assert sieverts_solubility(gas, 0.0) == 0.0


def test_sieverts_solubilities_hit_their_liquid_iron_anchors():
    # Cited pure-iron solubility at 1 atm, 1600 °C: H ≈ 25–27 ppm, N ≈ 440–460 ppm. Un-tuned (the A/B
    # reproduce the cited ΔG°/log-K), so hitting the windows is the tooth.
    assert 24.0 < sieverts_solubility("H", 1.0, 1600.0) < 28.0
    assert 430.0 < sieverts_solubility("N", 1.0, 1600.0) < 465.0


def test_vacuum_for_target_inverts_solubility():
    # By construction (NOT teeth): p = (target/K)² is the inverse of [ppm] = K√p (round-trips).
    p = vacuum_for_gas_target("H", 2.0, 1600.0)
    assert sieverts_solubility("H", p, 1600.0) == pytest.approx(2.0)
    assert 0.003 < p < 0.010                               # the 2 ppm flaking limit ≈ a few mbar


# --------------------------------------------------------------------------- #
# The orchestrator seam — fills the right fields, raises the right flags
# --------------------------------------------------------------------------- #
def test_from_hot_metal_is_high_carbon_low_oxygen():
    charge = from_hot_metal(STEELS["4140"], charge_carbon=4.5)
    assert charge.composition.C == 4.5
    assert charge.oxygen_ppm is not None and charge.oxygen_ppm < 10.0   # carbon-saturated → low O
    assert charge.history[0].name == "hot-metal charge"
    # The alloy backbone is carried (held fixed for the carbon-axis proof; F3 trims it for real).
    assert charge.composition.Cr == STEELS["4140"].Cr


def test_decarburize_sets_carbon_and_raises_oxygen_no_flag():
    charge = from_hot_metal(STEELS["4140"], charge_carbon=4.5)
    blown = decarburize(charge, 0.40)
    over = decarburize(charge, 0.20)
    assert blown.composition.C == 0.40 and over.composition.C == 0.20
    assert over.oxygen_ppm > blown.oxygen_ppm > charge.oxygen_ppm       # over-blow → lower C, higher O
    assert blown.is_clean and over.is_clean                            # no flag here (consequence is downstream)
    assert blown.history[-1].name == "decarburize"


def test_deoxidize_drops_oxygen_and_fills_inclusion_fields():
    blown = decarburize(from_hot_metal(STEELS["4140"]), 0.40)
    killed = deoxidize(blown, "Al", 0.04)
    assert killed.oxygen_ppm < blown.oxygen_ppm                        # oxygen pulled down
    assert killed.inclusion_type == "Al2O3"
    assert killed.inclusion_volume_fraction is not None and killed.inclusion_volume_fraction > 0.0
    assert killed.is_clean                                            # well-killed → no porosity flag


def test_deoxidize_never_adds_oxygen():
    # A late, tiny addition cannot RAISE dissolved oxygen above what was already there (deox only removes).
    blown = decarburize(from_hot_metal(STEELS["4140"]), 0.40)
    killed = deoxidize(blown, "Al", 0.0001)                            # barely any aluminium
    assert killed.oxygen_ppm <= blown.oxygen_ppm + 1e-9


def test_under_deoxidation_raises_the_porosity_flag():
    blown = decarburize(from_hot_metal(STEELS["4140"]), 0.40)
    under = deoxidize(blown, "Al", 0.001)                             # far too little aluminium
    assert under.oxygen_ppm > MAX_DISSOLVED_OXYGEN_PPM
    assert under.has_defect(POROSITY_RISK)


def test_degas_fills_gases_and_flags_only_hydrogen():
    blown = decarburize(from_hot_metal(STEELS["4140"]), 0.40)
    deep = degas(blown, p_H2=0.003)
    weak = degas(blown, p_H2=0.05)
    assert deep.hydrogen_ppm is not None and deep.nitrogen_ppm is not None
    assert deep.hydrogen_ppm < MAX_HYDROGEN_PPM and deep.is_clean     # deep vacuum → safe
    assert weak.hydrogen_ppm > MAX_HYDROGEN_PPM and weak.has_defect(HYDROGEN_FLAKING_RISK)
    # Nitrogen is a reported solubility-limit field, NOT a spec'd defect (the honest asymmetry): a heat
    # with high N (the limit) is not flagged on it.
    assert "nitrogen" not in " ".join(weak.defects)


def test_full_refining_sequence_fills_every_none_gas_inclusion_field():
    # The user-facing point of F2: the Heat fields that sat None since the spine are now FILLED.
    charge = from_hot_metal(STEELS["4140"])
    refined = degas(deoxidize(decarburize(charge, 0.40), "Al", 0.04), p_H2=0.003)
    for field in ("oxygen_ppm", "hydrogen_ppm", "nitrogen_ppm",
                  "inclusion_volume_fraction", "inclusion_type"):
        assert getattr(refined, field) is not None, f"{field} still None after refining"
    # Immutability carried from the spine: the charge was not mutated.
    assert charge.oxygen_ppm is not None and charge.inclusion_type is None
