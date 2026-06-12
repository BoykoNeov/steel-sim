"""Reduction thermodynamics — the Ellingham diagram: ore → iron (Steel-making **F1**).

The **first slice of the front end** (``docs/plans/steel-making.md`` §7). Where the back
half of the project takes a composition *as given* and follows it through cooling to a
microstructure, the front half asks the upstream question: *how do you get iron — and a given
alloy element — out of its oxide in the first place?* The answer is the classic teaching
artifact of extractive metallurgy, the **Ellingham diagram**: the standard Gibbs free energy of
oxide formation ΔG°(T), plotted per mole of O₂ so every oxide's line is directly comparable, and
read to decide **which reductant pulls the oxygen off which oxide above which temperature.**

This module is deliberately standalone — it touches neither the frozen ``engines/diffusion``
spine nor any back-end module. It is pure equilibrium thermodynamics built up from per-species
standard data, exactly the "tractable, citable, triad-clearing" tier the front-end scope ceiling
admits (``steel-making.md`` §4); the transport-resolved *rate* of reduction is the named tar pit
and lives nowhere in this repo.

The straight-line model
-----------------------
For an oxidation reaction written **per mole of O₂** (``(2x/y)·M + O₂ → (2/y)·MₓO_y``),

    ΔG°(T) = ΔH° − T·ΔS°                       (the Ellingham straight line)

with ΔH°, ΔS° taken **temperature-independent** (the ``ΔCp ≈ 0`` approximation) and computed
from per-species standard enthalpies of formation and absolute entropies at 298 K:
``ΔH° = Σν·ΔHf,298``, ``ΔS° = Σν·S°298`` (ν signed: + products, − reactants). The slope of each
line is **−ΔS°**. Because forming a metal oxide *consumes* gaseous O₂ (entropy falls, ΔS° < 0),
metal-oxide lines slope **up**. The one reaction that *makes* gas — ``2C + O₂ → 2CO`` (1 mol gas
→ 2 mol gas, ΔS° > 0) — slopes **down**, so the carbon→CO line eventually dives below every
metal-oxide line: that sign opposition is *why carbon can reduce any oxide given enough
temperature*, and the carbon/iron-oxide crossover (~700–750 °C) is where ironmaking begins.

What is CITED vs the named scope ceiling — the non-circularity discipline (as in grain/kinetics)
-----------------------------------------------------------------------------------------------
* **CITED (the teeth):** the per-species ΔHf,298 and S°298 are **standard thermochemical data**
  (NIST-JANAF / CODATA / CRC-class), verified against NIST for the crossover-driving species
  (CO, CO₂, Fe₂O₃, Fe₃O₄, FeO entropy) before pinning — see ``test_reduction.py``. They are
  implemented *into the equations*, never redistributed as a dataset (terms of use,
  ``steel-making.md`` §11). The **benchmark** the data must clear without tuning: the carbon /
  wüstite crossover lands in the textbook ~650–800 °C window and the
  Fe₂O₃ → Fe₃O₄ → FeO → Fe reduction sequence stacks in the right order.
* **NOTHING is calibrated.** There is no fitted constant in this module; every number is a
  sourced physical constant. The conservation leg (element + oxygen balance on every reaction)
  and the ΔG°(298 K) ≡ ΔH° − 298·ΔS° identity are **by construction**, not benchmarks — they
  guard typos and arithmetic, they cannot fail informatively.
* **The named scope ceiling — the omitted kinks.** Real Ellingham lines change slope at the
  melting / boiling points of the metal and oxide (ΔS° jumps when a phase appears or vanishes);
  this straight-line model omits those kinks deliberately — the front-end analogue of the
  back-end's "endpoints, not the transport field" ceiling. A related casualty: below ≈ 570 °C
  wüstite (FeO) is itself unstable and disproportionates (Fe + Fe₃O₄), so the literal
  Fe₂O₃ → Fe₃O₄ → FeO → Fe sequence is a *high-temperature* one; the linear lines do not encode
  that eutectoid. And **wüstite is non-stoichiometric** (Fe₁₋ₓO): its tabulated ΔHf ranges
  ≈ −266 to −272 kJ/mol, which slides the carbon crossover across ~710–746 °C — all inside the
  benchmark window, which is why the window is set generously rather than pinned tight.

Units (the registered trap)
---------------------------
Every reaction is normalized to **per mole O₂** (the Ellingham convention — the *only* way the
lines are comparable). Internally ΔHf and ΔG are **J/mol O₂**, S° and ΔS° **J/(mol O₂·K)**,
temperature input **°C** (converted to **K** for the ``−T·ΔS°`` term and for ``RT``). The figure
and the demo report ΔG in **kJ/mol O₂** (the conventional y-axis) — that J→kJ scaling lives at
the surface, not here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .kinetics import R_GAS, ABS_ZERO

# --------------------------------------------------------------------------- #
# 1. Per-species standard thermochemical data (NIST-JANAF / CODATA / CRC class)
# --------------------------------------------------------------------------- #
# ΔHf,298 in J/mol, S°298 in J/(mol·K). Elements in their reference state have ΔHf = 0 by
# definition; their S°298 is still a real (absolute, third-law) entropy and enters every ΔS°.
# Verified against NIST/CODATA for the crossover-driving species (CO, CO₂, Fe₂O₃, Fe₃O₄, and
# the FeO entropy) — see test_reduction.py's benchmark notes. Implemented as equation inputs,
# not redistributed as a table (terms of use). NO value here is fitted.
@dataclass(frozen=True)
class Species:
    """A chemical species' standard formation enthalpy, absolute entropy, and element makeup.

    ``dHf298`` J/mol (0 for an element in its reference state), ``S298`` J/(mol·K) (always a
    real third-law entropy), ``elements`` the atom count per formula unit (``{"Fe": 1, "O": 1}``
    for FeO) — the latter is what makes the conservation leg a real check, not a comment.
    """

    name: str
    dHf298: float                       # J/mol — standard enthalpy of formation at 298.15 K
    S298: float                         # J/(mol·K) — standard absolute (third-law) entropy
    elements: dict[str, int] = field(default_factory=dict)


# Reference-state elements: ΔHf = 0; carbon is GRAPHITE (the reference allotrope), not diamond.
SPECIES: dict[str, Species] = {
    "O2":    Species("O2",         0.0,    205.152, {"O": 2}),     # CODATA
    "C":     Species("C(gr)",      0.0,      5.74,  {"C": 1}),     # graphite, CODATA
    "H2":    Species("H2",         0.0,    130.680, {"H": 2}),     # CODATA
    "Fe":    Species("Fe",         0.0,     27.28,  {"Fe": 1}),    # α-iron, CODATA
    "Al":    Species("Al",         0.0,     28.30,  {"Al": 1}),
    "Si":    Species("Si",         0.0,     18.81,  {"Si": 1}),
    "Mn":    Species("Mn",         0.0,     32.01,  {"Mn": 1}),
    "Cr":    Species("Cr",         0.0,     23.77,  {"Cr": 1}),
    "Ca":    Species("Ca",         0.0,     41.59,  {"Ca": 1}),
    # Gaseous oxides (the reductant products)
    "CO":    Species("CO",     -110.53e3,  197.66,  {"C": 1, "O": 1}),   # NIST/CODATA
    "CO2":   Species("CO2",    -393.51e3,  213.79,  {"C": 1, "O": 2}),   # NIST/CODATA
    "H2O":   Species("H2O(g)", -241.83e3,  188.84,  {"H": 2, "O": 1}),   # water VAPOUR, CODATA
    # Iron oxides (the ore the front end reduces) — the stepwise reduction chain
    "FeO":   Species("FeO",    -272.0e3,    60.75,  {"Fe": 1, "O": 1}),  # wüstite (see ceiling note)
    "Fe3O4": Species("Fe3O4", -1118.4e3,  146.4,    {"Fe": 3, "O": 4}),  # magnetite, NIST
    "Fe2O3": Species("Fe2O3",  -824.2e3,   87.4,    {"Fe": 2, "O": 3}),  # hematite, NIST
    # Reference alloy / slag oxides — the Ellingham hierarchy (why Al reduces everything, why
    # Si/Mn/Cr matter to F3 ferroalloy trim, why CaO anchors F2 basic slag). Ordering-tested.
    "Al2O3": Species("Al2O3", -1675.7e3,   50.92,  {"Al": 2, "O": 3}),   # corundum
    "SiO2":  Species("SiO2",   -910.7e3,   41.46,  {"Si": 1, "O": 2}),   # α-quartz
    "MnO":   Species("MnO",    -385.2e3,   59.71,  {"Mn": 1, "O": 1}),
    "Cr2O3": Species("Cr2O3", -1139.7e3,   81.2,   {"Cr": 2, "O": 3}),
    "CaO":   Species("CaO",    -634.9e3,   38.10,  {"Ca": 1, "O": 1}),
}


# --------------------------------------------------------------------------- #
# 2. Oxidation reactions, normalized per mole O₂ (the Ellingham convention)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Reaction:
    """An oxidation reaction normalized to **one mole of O₂** (so its ΔG° line is comparable).

    ``reactants`` / ``products`` map a species key (into :data:`SPECIES`) to its stoichiometric
    coefficient; the reactant side always carries exactly ``1.0`` mol ``O2``. Fractional
    coefficients (e.g. ``4/3`` Al) are expected and fine — the per-O₂ normalization is the whole
    point. ``label`` is the human-readable equation for tables and the figure legend.
    """

    key: str
    label: str
    reactants: dict[str, float]
    products: dict[str, float]


def _rxn(key: str, label: str, reactants: dict[str, float], products: dict[str, float]) -> Reaction:
    return Reaction(key, label, reactants, products)


REACTIONS: dict[str, Reaction] = {
    # --- the reductant lines (the carbon system + hydrogen) -------------------------------
    # 2C + O₂ → 2CO is the special one: gas moles rise (ΔS° > 0) so it slopes DOWN and dives
    # below the metal-oxide lines — the engine of carbothermic reduction.
    "C->CO":     _rxn("C->CO",     "2 C + O₂ → 2 CO",        {"C": 2.0, "O2": 1.0},  {"CO": 2.0}),
    "C->CO2":    _rxn("C->CO2",    "C + O₂ → CO₂",           {"C": 1.0, "O2": 1.0},  {"CO2": 1.0}),
    "CO->CO2":   _rxn("CO->CO2",   "2 CO + O₂ → 2 CO₂",      {"CO": 2.0, "O2": 1.0}, {"CO2": 2.0}),
    "H2->H2O":   _rxn("H2->H2O",   "2 H₂ + O₂ → 2 H₂O",      {"H2": 2.0, "O2": 1.0}, {"H2O": 2.0}),
    # --- iron oxides: the stepwise oxidation chain (read in reverse = the reduction sequence) -
    "Fe->FeO":      _rxn("Fe->FeO",      "2 Fe + O₂ → 2 FeO",          {"Fe": 2.0, "O2": 1.0},   {"FeO": 2.0}),
    "FeO->Fe3O4":   _rxn("FeO->Fe3O4",   "6 FeO + O₂ → 2 Fe₃O₄",       {"FeO": 6.0, "O2": 1.0},  {"Fe3O4": 2.0}),
    "Fe3O4->Fe2O3": _rxn("Fe3O4->Fe2O3", "4 Fe₃O₄ + O₂ → 6 Fe₂O₃",     {"Fe3O4": 4.0, "O2": 1.0}, {"Fe2O3": 6.0}),
    # --- the reference hierarchy (alloy + slag oxides) ------------------------------------
    "Al->Al2O3": _rxn("Al->Al2O3", "4/3 Al + O₂ → 2/3 Al₂O₃", {"Al": 4.0 / 3.0, "O2": 1.0}, {"Al2O3": 2.0 / 3.0}),
    "Si->SiO2":  _rxn("Si->SiO2",  "Si + O₂ → SiO₂",          {"Si": 1.0, "O2": 1.0},       {"SiO2": 1.0}),
    "Mn->MnO":   _rxn("Mn->MnO",   "2 Mn + O₂ → 2 MnO",       {"Mn": 2.0, "O2": 1.0},       {"MnO": 2.0}),
    "Cr->Cr2O3": _rxn("Cr->Cr2O3", "4/3 Cr + O₂ → 2/3 Cr₂O₃", {"Cr": 4.0 / 3.0, "O2": 1.0}, {"Cr2O3": 2.0 / 3.0}),
    "Ca->CaO":   _rxn("Ca->CaO",   "2 Ca + O₂ → 2 CaO",       {"Ca": 2.0, "O2": 1.0},       {"CaO": 2.0}),
}

# The carbon reductant lines and the iron-oxide chain — named groups the demo/figure read.
REDUCTANT_KEYS: tuple[str, ...] = ("C->CO", "C->CO2", "CO->CO2", "H2->H2O")
# Iron oxidation, MOST-reduced first. Read top-to-bottom it is the OXIDATION ladder
# Fe → FeO → Fe₃O₄ → Fe₂O₃; reversed, the REDUCTION sequence Fe₂O₃ → Fe₃O₄ → FeO → Fe.
IRON_OXIDATION_CHAIN: tuple[str, ...] = ("Fe->FeO", "FeO->Fe3O4", "Fe3O4->Fe2O3")
HIERARCHY_KEYS: tuple[str, ...] = ("Ca->CaO", "Al->Al2O3", "Si->SiO2", "Mn->MnO", "Cr->Cr2O3")


# --------------------------------------------------------------------------- #
# 3. Conservation leg — element + oxygen balance (by construction; a typo guard)
# --------------------------------------------------------------------------- #
def element_balance(rxn: Reaction) -> dict[str, float]:
    """Net atoms of each element (products − reactants) for ``rxn`` — all ~0 when balanced.

    The conservation leg of F1's triad, applied per reaction: a balanced equation conserves every
    element *and* oxygen by construction, so this returns ≈ 0 for each. It is a **typo guard**,
    not a benchmark with teeth (a balanced reaction cannot fail it informatively) — but it is the
    cheapest possible check that the per-O₂ stoichiometry was entered correctly.
    """
    bal: dict[str, float] = defaultdict(float)
    for s, c in rxn.reactants.items():
        for el, n in SPECIES[s].elements.items():
            bal[el] -= c * n
    for s, c in rxn.products.items():
        for el, n in SPECIES[s].elements.items():
            bal[el] += c * n
    return dict(bal)


def is_balanced(rxn: Reaction, *, tol: float = 1e-9) -> bool:
    """``True`` when every element (oxygen included) balances to within ``tol`` (see
    :func:`element_balance`)."""
    return all(abs(v) <= tol for v in element_balance(rxn).values())


# --------------------------------------------------------------------------- #
# 4. The Ellingham line — ΔH°, ΔS° (slope), ΔG°(T)
# --------------------------------------------------------------------------- #
def reaction_enthalpy(rxn: Reaction) -> float:
    """Standard reaction enthalpy ΔH° (J/mol O₂), ``Σν·ΔHf,298`` — temperature-independent here."""
    return (
        sum(c * SPECIES[s].dHf298 for s, c in rxn.products.items())
        - sum(c * SPECIES[s].dHf298 for s, c in rxn.reactants.items())
    )


def reaction_entropy(rxn: Reaction) -> float:
    """Standard reaction entropy ΔS° (J/(mol O₂·K)), ``Σν·S°298``.

    The **slope** of the Ellingham line is ``−ΔS°``: metal oxides consume O₂ gas (ΔS° < 0 → line
    slopes up); ``2C + O₂ → 2CO`` makes gas (ΔS° > 0 → line slopes down). That sign is the whole
    story of why carbon is the universal high-temperature reductant.
    """
    return (
        sum(c * SPECIES[s].S298 for s, c in rxn.products.items())
        - sum(c * SPECIES[s].S298 for s, c in rxn.reactants.items())
    )


def standard_free_energy(rxn: Reaction, T_celsius: float) -> float:
    """Ellingham ΔG°(T) for ``rxn`` (J/mol O₂): the straight line ``ΔH° − T·ΔS°``.

    ``T`` is °C (converted to kelvin for the entropy term). This is the height of the reaction's
    line on the Ellingham diagram at temperature ``T`` — the lower (more negative) the line, the
    more stable the oxide and the harder it is to reduce. Exactly linear in ``T`` by construction
    (the ``ΔCp ≈ 0`` model — see the module's named ceiling on the omitted phase-change kinks).
    """
    T_K = T_celsius + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"temperature must be above absolute zero, got {T_celsius} °C")
    return reaction_enthalpy(rxn) - T_K * reaction_entropy(rxn)


# --------------------------------------------------------------------------- #
# 5. Crossovers, reduction, and the equilibrium oxygen potential
# --------------------------------------------------------------------------- #
def crossover_temperature(rxn_a: Reaction, rxn_b: Reaction) -> float | None:
    """Temperature (°C) where the two Ellingham lines intersect, or ``None`` if parallel.

    Set ``ΔGa = ΔGb`` → ``ΔHa − T·ΔSa = ΔHb − T·ΔSb`` → ``T = (ΔHa − ΔHb)/(ΔSa − ΔSb)`` — a
    closed-form linear intersection (the analytic leg). Returns ``None`` when the slopes are equal
    (no crossover). The carbon→CO / iron-oxide crossover this computes is F1's headline benchmark.
    """
    dHa, dSa = reaction_enthalpy(rxn_a), reaction_entropy(rxn_a)
    dHb, dSb = reaction_enthalpy(rxn_b), reaction_entropy(rxn_b)
    denom = dSa - dSb
    if abs(denom) < 1e-12:
        return None
    return (dHa - dHb) / denom - ABS_ZERO


def reduces(reductant: Reaction, oxide: Reaction, T_celsius: float) -> bool:
    """``True`` if ``reductant`` can strip the oxygen from ``oxide`` at ``T_celsius``.

    The coupled reduction ``MₓO_y + reductant → M + (reductant oxide)`` has
    ``ΔG = ΔG(reductant oxidation) − ΔG(oxide formation)`` (both per mole O₂); it is spontaneous
    when the reductant's line sits **below** the oxide's line. So the test is simply: is the
    reductant's ΔG° more negative than the oxide's at this temperature?
    """
    return standard_free_energy(reductant, T_celsius) < standard_free_energy(oxide, T_celsius)


def reduction_onset_temperature(reductant: Reaction, oxide: Reaction) -> float | None:
    """Lowest temperature (°C) above which ``reductant`` reduces ``oxide``, or ``None``.

    For the carbon→CO reductant (line sloping down past the rising oxide line) this is the
    crossover, and ``reduces`` is ``True`` above it / ``False`` below — the "carbon reduces
    wüstite above ~700 °C" fact. Returns ``None`` when there is no such low→high transition (the
    lines are parallel, or the reductant is already below the oxide at every temperature, e.g. a
    far stronger reductant). The boolean :func:`reduces` is the robust primitive; this is the
    convenience that names the onset.
    """
    T_cross = crossover_temperature(reductant, oxide)
    if T_cross is None:
        return None
    # A genuine non-reducing→reducing transition with rising T: not reducing just below, reducing
    # just above. (Guards the "already below everywhere" and "drops out above" cases.)
    if not reduces(reductant, oxide, T_cross - 1.0) and reduces(reductant, oxide, T_cross + 1.0):
        return T_cross
    return None


def equilibrium_oxygen_pressure(rxn: Reaction, T_celsius: float) -> float:
    """Equilibrium oxygen partial pressure (bar) over a metal/oxide couple at ``T_celsius``.

    For a condensed-phase oxidation ``M + O₂ → MO₂`` (activities of the solid metal and oxide ≈ 1)
    the equilibrium constant is ``K = (p_O₂/p°)⁻¹``, so ``ΔG° = R·T·ln(p_O₂/p°)`` and

        p_O₂,eq = exp(ΔG°/(R·T))          (in bar, with p° = 1 bar)

    is the **oxygen potential**: the O₂ pressure at which metal and oxide coexist. A more stable
    oxide (lower ΔG° line) demands a *lower* equilibrium p_O₂ — it clings to its oxygen harder, so
    it is reduced only in a more strongly reducing (lower-p_O₂) atmosphere. Meaningful for the
    condensed metal/oxide couples; the gas-product reductant lines (C→CO, etc.) set their oxygen
    potential through the CO/CO₂ (or H₂/H₂O) ratio instead and are out of this function's scope.
    """
    T_K = T_celsius + ABS_ZERO
    if T_K <= 0.0:
        raise ValueError(f"temperature must be above absolute zero, got {T_celsius} °C")
    return math.exp(standard_free_energy(rxn, T_celsius) / (R_GAS * T_K))


# --------------------------------------------------------------------------- #
# 6. The stepwise iron reduction sequence + the hierarchy (demo/figure helpers)
# --------------------------------------------------------------------------- #
def stability_order(keys: tuple[str, ...], T_celsius: float) -> list[tuple[str, float]]:
    """``(key, ΔG°)`` for each reaction in ``keys``, sorted most-stable (most negative ΔG°) first.

    The bottom of an Ellingham diagram is the most stable oxide. Applied to
    :data:`IRON_OXIDATION_CHAIN` it returns the stepwise stack whose reverse is the
    Fe₂O₃ → Fe₃O₄ → FeO → Fe reduction sequence; applied to :data:`HIERARCHY_KEYS` it returns the
    alloy/slag-oxide pecking order (CaO/Al₂O₃ at the bottom, why Al deoxidizes everything).
    """
    return sorted(
        ((k, standard_free_energy(REACTIONS[k], T_celsius)) for k in keys),
        key=lambda kv: kv[1],
    )


def iron_reduction_sequence(T_celsius: float) -> list[str]:
    """The iron-oxide reduction order at ``T_celsius`` — least stable (reduced first) → iron.

    Reduction removes oxygen, so it proceeds from the *highest* (least negative ΔG°) line down:
    the reaction keys returned read as ``Fe₂O₃ → Fe₃O₄`` first, then ``Fe₃O₄ → FeO``, then
    ``FeO → Fe`` — i.e. hematite → magnetite → wüstite → iron, the textbook blast-furnace stack
    (above the ~570 °C wüstite floor named in the module ceiling).
    """
    return [k for k, _ in reversed(stability_order(IRON_OXIDATION_CHAIN, T_celsius))]
