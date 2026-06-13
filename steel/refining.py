"""Primary refining — decarburize / deoxidize / degas (Steel-making **F2**, Slice 1).

The **middle of the chain** (``docs/plans/steel-making.md`` §7, build-order item 4). F1 reduced ore to
iron; F4 cast the finished billet; this module is the converter/ladle step *between* them — the BOF/EAF
**refining** that takes carbon-saturated hot metal and blows, kills, and degasses it into a steel that is
on its carbon target and clean enough to cast. It is the phase that finally **fills the dissolved-gas and
inclusion fields the** :class:`~steel.heat_state.Heat` **record has carried as ``None``** since the spine
was built: dissolved O from the carbon–oxygen equilibrium, retained oxide inclusions from deoxidation,
dissolved H/N from Sieverts' law.

The two coupled stories — one validated end-to-end, one honestly bounded
----------------------------------------------------------------------
Refining is one move with two outputs, and they sit on opposite sides of the verified/plausible line:

1. **Carbon — the *validated* propagation (the proof rides here).** The blow sets the steel's carbon, and
   carbon is the one refining output the **already-benchmarked back end consumes**. Aim for the grade's
   carbon and the part through-hardens; **over-blow** (carbon below target) and the *same* quench misses —
   the existing :func:`~steel.heat_state.heat_treat` raises its **soft-core** flag, not because F2 scripted
   a failure but because the back-end martensite fraction crossed a spec line. That is the same class as the
   spine's Cr/Mo under-dose propagation (``heat_state``) — a chosen composition/control error reaching the
   *already-benchmarked* back end. (It is *not* F4's centerline band, where Scheil **computes** the
   enrichment from new cited physics; here the new physics — §2 below — sits on the *deferred*-consequence
   side, while the validated link rides a control input the back end already responds to.)

2. **Oxygen / gas — the *new state*, consequences deferred.** The same decarburization that sets carbon
   **raises dissolved oxygen** (they are inversely coupled by the C–O product, below), which deoxidation
   then removes — generating oxide inclusions — and degassing strips H/N. These fields are now *filled* on
   the ``Heat``, and an under-killed or under-degassed heat raises a **porosity** / **flaking** flag when a
   field crosses spec. But their *downstream* consequence — gas porosity, hydrogen flaking, hot-tearing in
   the casting — lives in F4 Slice 2 / the game layer (the ``steel-making.md`` §6 links marked "F2 new +
   F4 new", both ends unbuilt). So F2 *sets up* that propagation honestly; it does not yet close it.

The physics — equilibrium endpoints, never the transport rate (the named scope ceiling)
---------------------------------------------------------------------------------------
Every relation here is an **equilibrium**: the carbon–oxygen product, the deoxidation equilibria, the
Sieverts solubilities. The *rate* at which the blow removes carbon, the *flotation* that clears the oxide,
the *kinetics* of gas pick-up — that is the mass-transfer / transport wall, the front-end tar pit the plan
excludes (``steel-making.md`` §4), the exact analogue of the back end computing phase *fractions* and never
the dendrite *field*. So the dissolved-gas numbers here are **solubility limits / equilibrium endpoints**:
real heats sit below the equilibrium N (kinetically limited pick-up) and the retained inclusion content
sits below the *generated* alumina (most floats out). Those gaps are named, not hidden.

* **Decarburization** — ``[C] + [O] = CO(g)``, the carbon–oxygen product ``[%C]·[%O] = p_CO / K_CO``. At
  1600 °C and 1 atm CO this is ≈ **0.0022** (``[%C]·[ppm O] ≈ 22``): blow carbon *down* and equilibrium
  oxygen climbs (charge ~4.5 %C / ~5 ppm O → 0.4 %C / ~55 ppm O → over-blown 0.2 %C / ~110 ppm O).
* **Deoxidation** — ``m[M] + n[O] = MₘOₙ``: add Al / Si / Mn and the dissolved oxygen drops to the
  equilibrium the deoxidizer's affinity allows. **Aluminium is far stronger than silicon than manganese**
  — the same oxide-stability ordering F1's Ellingham diagram draws (Al₂O₃ below SiO₂ below MnO), here
  reached from *independently sourced* dissolved-state equilibria (Q below). The Al–O curve has a **minimum**
  (``[O]`` falls, bottoms near ``[Al] ≈ 0.07 %``, then *rises*): a real feature, captured by the one
  first-order interaction coefficient ``e_O^Al`` (Sigworth & Elliott) — drop it and the curve is a cartoon.
* **Degassing** — Sieverts' law ``[%X] = K_X·√p_X``: a *diatomic* gas dissolves as atoms, so solubility
  goes as the **square root** of partial pressure. Halving dissolved hydrogen needs *quartering* the
  pressure — why ladle vacuum degassing works, and how deep a vacuum the 2 ppm flaking limit demands.

What is CITED vs the named ceiling — the non-circularity / two-tier discipline (as in casting/reduction)
------------------------------------------------------------------------------------------------------
* **CITED (the teeth), the robust-anchor tier.** The carbon–oxygen product ``[%C][%O] ≈ 0.0022`` at
  1600 °C (ΔG° = −19840 − 40.65·T, J/mol; Vidhyasagar et al. 2023 / standard, and benchmarked against
  measured BOP 27±3, EAF 26±2 ppm·%C — higher than equilibrium from slag FeO); the Sieverts solubilities
  **H ≈ 26 ppm** (log K = −1900/T + 2.423) and **N ≈ 450 ppm** (ΔG° = 3598 + 23.89·T; Pehlke–Elliott) in
  pure liquid iron at 1 atm, 1600 °C; the interaction coefficient ``e_O^Al = −3.9`` (Sigworth & Elliott
  1974) that makes the Al–O minimum. These were **read from the sources and pinned**; the teeth (the √p
  law, the C–O coupling, the deox hierarchy, the minimum's *existence*) rest on them.
* **CITED, the source-sensitive tier.** The *absolute* deoxidation constants ``K_M`` (Al/Si/Mn formation
  ΔG°, Turkdogan-class) — the Al–O equilibrium famously scatters by a factor of several between studies, so
  the **ranking and order of magnitude** are the read, not the last digit. Crucially the **minimum
  *location*** ``[Al] = −m/(n·ln10·e_O^Al) ≈ 0.07 %`` is independent of ``K_Al`` (only ``e_O^Al`` sets it),
  so the headline tooth does not ride the scattered constant — same two-tier honesty as casting's ``k``.
* **The named ceiling.** Equilibrium endpoints only (no blow/flotation/pick-up *rate*); 1-wt% Henrian
  dilute standard state with a **single dominant** deoxidizer and ``f_M ≈ 1`` (the O-side ``e_O^M``
  interaction is what bends the curve); the deox constants are pinned at the 1600 °C reference (their
  T-extrapolation is not the claim); dissolved gas is the **solubility limit** (real pick-up is
  kinetically below it); inclusion content is **generated** oxide (flotation removal not modelled). Slag
  partition (L_S, L_P vs basicity — desulfurization / dephosphorization) is **Slice 2**: it needs S/P state
  the ``Heat``/``Steel`` does not carry, so pulling it in would mean a state extension that is its own call.

Units: wt % for composition, **ppm** for dissolved gas/oxygen (the field unit on ``Heat``), °C for
temperature (converted to K internally), atm for partial pressure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .heat_state import Heat, ProcessStep, add_defect
from .kinetics import R_GAS, ABS_ZERO
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Reference temperatures & the spec thresholds (the verified/game boundary)
# --------------------------------------------------------------------------- #
# Steelmaking happens hot. Tap is ~1600 °C; blast-furnace hot metal a little cooler. Constants are
# pinned at the 1600 °C reference (their T-extrapolation is named, not claimed).
T_TAP_C: float = 1600.0                     # reference tap / refining temperature
T_HOT_METAL_C: float = 1450.0               # blast-furnace hot-metal charge temperature

# Spec thresholds — design requirements, NOT fitted physics (the same posture as
# heat_state.MIN_MARTENSITE_SPEC). They mark where a *field* becomes a *defect*; the physics that computes
# the field is what is benchmarked, these lines are where we decide the result is unacceptable.
MAX_DISSOLVED_OXYGEN_PPM: float = 30.0      # above this the heat is under-killed → CO/shrinkage porosity risk
MAX_HYDROGEN_PPM: float = 2.0               # the classic flaking / hairline-crack limit in heavy sections

# Nitrogen is **reported, not spec-flagged** (the honest asymmetry). The Sieverts value is the *solubility
# limit* at the bath's nitrogen partial pressure; real dissolved N sits well below it (pick-up is
# kinetically limited), and vacuum strips N only slowly (the tar pit). A hard N spec would flag every heat
# defective on a number that is an upper bound, not the live content — so N fills its field as a limit, with
# no defect attached. Oxygen and hydrogen equilibrate fast enough that their specs are honest.

# Defect-flag names — the failure carriers that ride in Heat.defects (steel-making.md §5/§6). The carbon
# over-blow consequence is NOT a new flag: it surfaces as heat_state.SOFT_CORE when the refined heat is
# heat-treated (the validated propagation rides the existing seam, F2 adds nothing there).
POROSITY_RISK: str = "porosity-risk"               # under-deoxidized: residual O → gas/shrinkage porosity
HYDROGEN_FLAKING_RISK: str = "hydrogen-flaking-risk"  # under-degassed: dissolved H → flaking on cooling


# --------------------------------------------------------------------------- #
# 1. Decarburization — the carbon–oxygen equilibrium ([C] + [O] = CO)
# --------------------------------------------------------------------------- #
# [C]_1wt% + [O]_1wt% = CO(g), ΔG° = A + B·T (J/mol). Vidhyasagar et al., AISTech 2023 (and standard
# steelmaking data); benchmarked there against measured tap [%C]·[ppm O]: BOP 27±3, EAF 26±2, EOF 29±4 —
# all above the ~22 equilibrium because slag FeO pushes the bath off the p_CO = 1 atm line. Dilute (Henrian
# activity coefficients ≈ 1): exact for the low-carbon refined regime the proof lives in.
DG_CO_A: float = -19840.0
DG_CO_B: float = -40.65


def carbon_oxygen_product(T_celsius: float = T_TAP_C, p_CO: float = 1.0) -> float:
    """The carbon–oxygen product ``[%C]·[%O] = p_CO / K_CO`` (wt %·wt %) at ``T_celsius``.

    The equilibrium of the carbon boil: ``K_CO = p_CO / ([%C][%O])`` with ``K_CO = exp(−ΔG°/RT)``. At
    1600 °C, 1 atm CO this is ≈ **0.0022** — the famous "``[%C]·[ppm O] ≈ 22``" of the converter. The
    product is the whole coupling: at a fixed ``p_CO`` it is constant, so driving carbon *down* drives
    equilibrium oxygen *up* (:func:`equilibrium_oxygen`). Lowering ``p_CO`` (vacuum decarburization, the
    RH/VOD route) shifts the product down — decarburize *without* the oxygen penalty.
    """
    T_K = T_celsius + ABS_ZERO
    K = math.exp(-(DG_CO_A + DG_CO_B * T_K) / (R_GAS * T_K))
    return p_CO / K


def equilibrium_oxygen(carbon_pct: float, T_celsius: float = T_TAP_C, p_CO: float = 1.0) -> float:
    """Dissolved oxygen (**ppm**) in C–O equilibrium with ``carbon_pct`` wt % carbon at ``T_celsius``.

    ``[%O] = ([%C][%O]) / [%C]`` → ppm. The inverse coupling in one line: carbon-saturated hot metal
    (~4.5 %C) sits at only a few ppm O; blow to the grade's 0.4 %C and O is ~55 ppm; over-blow to 0.2 %C
    and O doubles to ~110 ppm — which is *why* a low-carbon heat needs heavier deoxidation. Raises on a
    non-positive carbon (the product is undefined as ``[%C] → 0``, the converter's over-oxidation limit).
    """
    if carbon_pct <= 0.0:
        raise ValueError(f"carbon must be positive (the C–O product diverges as %C → 0), got {carbon_pct}")
    return carbon_oxygen_product(T_celsius, p_CO) / carbon_pct * 1.0e4


# --------------------------------------------------------------------------- #
# 2. Deoxidation — m[M] + n[O] = MₘOₙ, with the Al–O minimum from e_O^Al
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Deoxidizer:
    """A deoxidizer's formation equilibrium and the data to bookkeep the oxide it makes — cited inputs.

    The reaction ``m[M] + n[O] = MₘOₙ(s)`` with standard free energy ``ΔG° = dG_A + dG_B·T`` (J/mol,
    1-wt% Henrian standard state). ``e_O`` is the first-order interaction coefficient ``e_O^M`` (Sigworth &
    Elliott 1974, 1873 K) — the effect of dissolved ``M`` on the **oxygen** activity coefficient; for
    aluminium it is strongly negative (−3.9), which is what bends the Al–O curve through a minimum.
    ``oxide_O_mass_frac`` and ``oxide_density`` (kg/m³) convert removed oxygen into generated-oxide mass and
    volume (the inclusion bookkeeping). ``dG_A/dG_B`` are the source-sensitive tier (the Al–O equilibrium
    scatters between studies) — the **ranking** and order of magnitude are the read.
    """

    name: str
    metal: str                  # the dissolved-metal element symbol
    m: int                      # moles of metal in the formation reaction
    n: int                      # moles of oxygen
    oxide: str                  # the oxide formula (the inclusion type)
    dG_A: float                 # ΔG° = dG_A + dG_B·T  (J/mol)
    dG_B: float
    e_O: float                  # first-order interaction coefficient e_O^metal (1873 K)
    oxide_O_mass_frac: float    # mass fraction of oxygen in the oxide
    oxide_density: float        # kg/m³ — for the generated-oxide volume fraction


# Three single-element deoxidizers, strongest → weakest. ΔG° are Turkdogan-class standard formation
# energies (source-sensitive tier); e_O are the Sigworth & Elliott 1974 first-order coefficients verified
# in the AISTech-2023 interaction-parameter table (e_O^Al = −3.9, e_O^Si = −0.131, e_O^Mn = −0.021).
DEOXIDIZERS: dict[str, Deoxidizer] = {
    # 2[Al] + 3[O] = Al₂O₃(s): the strong deoxidizer (Al₂O₃ inclusions). e_O^Al = −3.9 makes the minimum.
    "Al": Deoxidizer("aluminium", "Al", 2, 3, "Al2O3", -1_202_000.0, 386.3, -3.9, 48.0 / 101.96, 3950.0),
    # [Si] + 2[O] = SiO₂(s): the workhorse (silica / silicate inclusions). Weaker than Al.
    "Si": Deoxidizer("silicon",   "Si", 1, 2, "SiO2",   -594_100.0, 230.0, -0.131, 32.0 / 60.08, 2200.0),
    # [Mn] + [O] = MnO(s): the weak deoxidizer — usually a partner to Si, not a finisher.
    "Mn": Deoxidizer("manganese", "Mn", 1, 1, "MnO",    -288_000.0, 128.3, -0.021, 16.0 / 70.94, 5400.0),
}

RHO_STEEL: float = 7000.0       # kg/m³ — liquid steel, for the oxide volume-fraction bookkeeping


def deoxidation_constant(deox: Deoxidizer, T_celsius: float = T_TAP_C) -> float:
    """The formation equilibrium constant ``K = exp(−ΔG°/RT)`` of ``deox`` at ``T_celsius`` (large = strong).

    ``K = aₒₓᵢ𝒹ₑ / (a_M^m · a_O^n) = 1 / ([%M]^m [%O]^n f_M^m f_O^n)`` (oxide activity ≈ 1). A larger ``K``
    pulls the equilibrium dissolved oxygen lower — the quantitative form of "stronger deoxidizer".
    """
    T_K = T_celsius + ABS_ZERO
    return math.exp(-(deox.dG_A + deox.dG_B * T_K) / (R_GAS * T_K))


def equilibrium_oxygen_after_deox(
    deox: Deoxidizer, level_pct: float, T_celsius: float = T_TAP_C, *, with_interaction: bool = True
) -> float:
    """Dissolved oxygen (**ppm**) in equilibrium with ``level_pct`` wt % of ``deox``'s metal at ``T_celsius``.

    Solves ``([%M]·f_M)^m · ([%O]·f_O)^n = 1/K`` for ``[%O]``. With ``f_M ≈ 1`` (dilute metal, the named
    simplification) the oxygen **activity** is ``a_O = (1/(K·[%M]^m))^{1/n}`` and the **concentration** is
    ``[%O] = a_O / f_O`` with ``log₁₀ f_O = e_O^M·[%M]`` (the dominant O-side interaction; the negligible
    ``e_O^O·[%O]`` self term is dropped). For aluminium that interaction is what produces the **minimum**:
    as ``[Al]`` rises the ``(1/[%M]^m)`` factor drives oxygen down, but ``f_O`` collapses (``e_O^Al < 0``),
    so concentration eventually climbs again. ``with_interaction=False`` returns the dilute cartoon (a
    monotonic fall — useful only to *show* what the coefficient adds).
    """
    if level_pct <= 0.0:
        raise ValueError(f"deoxidizer level must be positive, got {level_pct}")
    K = deoxidation_constant(deox, T_celsius)
    a_O = (1.0 / (K * level_pct ** deox.m)) ** (1.0 / deox.n)        # oxygen activity (wt %)
    f_O = 10.0 ** (deox.e_O * level_pct) if with_interaction else 1.0
    return a_O / f_O * 1.0e4                                          # → ppm


def aluminium_oxygen_minimum(T_celsius: float = T_TAP_C) -> tuple[float, float]:
    """The Al–O curve's minimum: ``([Al]_min wt %, [O]_min ppm)`` at ``T_celsius``.

    The location is the closed form ``[M]_min = −m/(n·ln10·e_O^M)`` (set ``d log[O]/d[Al] = 0``) — for
    aluminium ``−2/(3·ln10·(−3.9)) ≈ 0.074 %``. Note the location depends **only on** ``e_O^Al``, *not* on
    the scattered ``K_Al`` — so this headline tooth is robust to the source-sensitive constant; only the
    minimum's *depth* (the ppm) moves with ``K_Al``.
    """
    d = DEOXIDIZERS["Al"]
    Al_min = -d.m / (d.n * math.log(10.0) * d.e_O)
    return Al_min, equilibrium_oxygen_after_deox(d, Al_min, T_celsius)


def deoxidizing_power(level_pct: float = 0.05, T_celsius: float = T_TAP_C) -> list[tuple[str, float]]:
    """``(symbol, equilibrium [O] ppm)`` for each deoxidizer at a common ``level_pct``, strongest first.

    The hierarchy read: at equal addition, aluminium leaves the *least* dissolved oxygen, then silicon,
    then manganese — the Al ≫ Si > Mn ordering, which is the **same** oxide-stability ordering F1's
    Ellingham diagram draws (Al₂O₃ < SiO₂ < MnO), reached here from independently-sourced dissolved-state
    equilibria. ``test_refining`` *computes* that ordering from the pinned constants rather than asserting it.
    """
    pairs = [(sym, equilibrium_oxygen_after_deox(d, level_pct, T_celsius)) for sym, d in DEOXIDIZERS.items()]
    return sorted(pairs, key=lambda kv: kv[1])


def generated_oxide(oxygen_removed_ppm: float, deox: Deoxidizer) -> tuple[float, float]:
    """``(oxide mass fraction, oxide volume fraction)`` made by removing ``oxygen_removed_ppm`` of oxygen.

    Conservation, the deoxidation mass balance: the oxygen pulled out of the melt does not vanish, it ends
    up bound in oxide. ``mass_oxide = mass_O_removed / (mass fraction O in the oxide)``; the volume fraction
    scales by the steel/oxide density ratio. This is the **generated** oxide — most of it floats out
    (flotation is the kinetic tar pit, not modelled), so the retained inclusion content is *below* this;
    the figure returned is the honest upper bound that lands in ``Heat.inclusion_volume_fraction``.
    """
    if oxygen_removed_ppm <= 0.0:
        return 0.0, 0.0
    mass_oxide = (oxygen_removed_ppm * 1.0e-6) / deox.oxide_O_mass_frac
    vol_oxide = mass_oxide * (RHO_STEEL / deox.oxide_density)
    return mass_oxide, vol_oxide


# --------------------------------------------------------------------------- #
# 3. Degassing — Sieverts' law, [%X] = K_X·√p (the diatomic square root)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DissolvedGas:
    """A dissolved diatomic gas' Sieverts constant — ``log₁₀([ppm X]/√p) = A/T + B`` (T in K, p in atm).

    The √p (not linear-p) dependence is Sieverts' law: a diatomic molecule dissolves as two atoms
    (``½X₂ = [X]``), so the equilibrium constant carries the half-power. ``A``/``B`` reproduce the cited
    solubility of ``X`` in pure liquid iron at 1 atm, 1600 °C.
    """

    name: str
    A: float
    B: float


# Hydrogen: log([ppm H]/√p) = −1900/T + 2.423 → ~26 ppm at 1 atm, 1600 °C (and ~25 ppm from the 27.7
#   cc/100 g measurement). Nitrogen: ΔG°(½N₂=[N]) = 3598 + 23.89·T (Pehlke–Elliott) → log([%N]/√p) =
#   −188/T − 1.248 → in ppm, B = −1.248 + 4 = 2.752 → ~450 ppm at 1 atm (cross-check: 3000 ppm at 50 atm
#   × √(1/50) = 424 ppm). Both are pure-iron solubility LIMITS (real pick-up is kinetically below them).
GASES: dict[str, DissolvedGas] = {
    "H": DissolvedGas("hydrogen", -1900.0, 2.423),
    "N": DissolvedGas("nitrogen", -188.0, 2.752),
}


def sieverts_solubility(gas: str, p_atm: float, T_celsius: float = T_TAP_C) -> float:
    """Sieverts equilibrium solubility of ``gas`` (**ppm**) at partial pressure ``p_atm`` and ``T_celsius``.

    ``[ppm X] = K_X·√p`` with ``log₁₀ K_X = A/T + B``. The **square root** is the law's whole content: it is
    why halving dissolved hydrogen takes *quartering* the pressure (a vacuum, not a fan), and why
    ladle degassing is so effective. Returns the equilibrium *limit*; a real bath sits at or below it.
    """
    if p_atm < 0.0:
        raise ValueError(f"partial pressure must be non-negative, got {p_atm}")
    g = GASES[gas]
    K = 10.0 ** (g.A / (T_celsius + ABS_ZERO) + g.B)
    return K * math.sqrt(p_atm)


def vacuum_for_gas_target(gas: str, target_ppm: float, T_celsius: float = T_TAP_C) -> float:
    """The partial pressure (**atm**) whose Sieverts equilibrium is ``target_ppm`` — the vacuum to pull.

    Inverting ``[ppm] = K√p`` gives ``p = (target/K)²``. The quantitative degassing answer: e.g. the
    pressure at which equilibrium hydrogen falls to the 2 ppm flaking limit (a few mbar) — below it the
    heat is safe, above it it flakes.
    """
    if target_ppm <= 0.0:
        raise ValueError(f"target must be positive, got {target_ppm}")
    g = GASES[gas]
    K = 10.0 ** (g.A / (T_celsius + ABS_ZERO) + g.B)
    return (target_ppm / K) ** 2


# --------------------------------------------------------------------------- #
# 4. The orchestrator seam — refine a Heat: charge → decarburize → deoxidize → degas
# --------------------------------------------------------------------------- #
def from_hot_metal(
    backbone: Steel, *, charge_carbon: float = 4.5, T_celsius: float = T_HOT_METAL_C, p_CO: float = 1.0
) -> Heat:
    """A blast-furnace **hot-metal charge** ``Heat``: high carbon, *low* dissolved oxygen — the chain origin.

    Carbon-saturated hot metal is the converter's feed: ~4.5 %C and, because the C–O product is inverse,
    only a few ppm dissolved oxygen. ``backbone`` carries the **alloy** content (the grade's Mn/Si/Cr/Mo)
    that the refining steps hold fixed — in reality the alloy trim is F3's job, but holding it fixed here is
    what lets the *same* downstream heat-treat read the **carbon** axis alone (the proof). The returned
    ``Heat`` starts its trail with a real ``"hot-metal charge"`` origin and its ``oxygen_ppm`` filled.
    """
    comp = replace(backbone, C=charge_carbon, name=f"{backbone.label()} hot metal")
    O = equilibrium_oxygen(charge_carbon, T_celsius, p_CO)
    origin = ProcessStep(
        "hot-metal charge",
        f"charge {charge_carbon:.1f} %C hot metal of a {backbone.label()} heat "
        f"(C–O equilibrium O {O:.1f} ppm — carbon-saturated, low oxygen)",
        in_spec=True,
    )
    return Heat(composition=comp, temperature_C=T_celsius, oxygen_ppm=O, history=(origin,))


def decarburize(
    heat: Heat, target_carbon: float, *, T_celsius: float = T_TAP_C, p_CO: float = 1.0
) -> Heat:
    """Blow the ``Heat`` to ``target_carbon`` wt % — sets carbon, **raises** dissolved oxygen (C–O coupled).

    The refining step that carries the validated proof. It updates the composition's carbon and repacks the
    C–O-equilibrium oxygen (:func:`equilibrium_oxygen`) — so an **over-blow** (``target_carbon`` below the
    grade) both lowers carbon *and* lifts oxygen. No flag is raised here on the carbon axis: its consequence
    is the *downstream* :func:`~steel.heat_state.heat_treat` soft-core (the validated propagation rides the
    existing seam, not a scripted branch). High oxygen after the blow is **expected** — deoxidation is the
    next step — so it is not yet a defect either.
    """
    comp = replace(heat.composition, C=target_carbon)
    O = equilibrium_oxygen(target_carbon, T_celsius, p_CO)
    summary = (
        f"blow C {heat.composition.C:.2f} → {target_carbon:.2f} %, dissolved O → {O:.0f} ppm "
        f"(C–O equilibrium, p_CO = {p_CO:g} atm)"
    )
    step = ProcessStep("decarburize", summary, in_spec=None)
    return heat.evolve(step, composition=comp, oxygen_ppm=O, temperature_C=T_celsius)


def deoxidize(
    heat: Heat, deoxidizer: str = "Al", level_pct: float = 0.04, *, T_celsius: float = T_TAP_C
) -> Heat:
    """Kill the ``Heat`` with ``level_pct`` of ``deoxidizer`` — drop dissolved O, fill the inclusion fields.

    Pulls dissolved oxygen down to the deoxidizer's equilibrium (:func:`equilibrium_oxygen_after_deox`) —
    never *up* (deoxidation only removes oxygen, so the result is clamped at the incoming level) — and books
    the oxide it generates into ``inclusion_volume_fraction`` / ``inclusion_type`` (the mass balance,
    :func:`generated_oxide`). An **under-killed** result (oxygen still above
    :data:`MAX_DISSOLVED_OXYGEN_PPM`) raises the **porosity-risk** flag. Note the Al–O minimum:
    over-shooting the deoxidizer past ~0.07 % Al *raises* equilibrium oxygen again (and makes more alumina)
    — more is not better.
    """
    d = DEOXIDIZERS[deoxidizer]
    O_before = heat.oxygen_ppm if heat.oxygen_ppm is not None else equilibrium_oxygen(heat.composition.C, T_celsius)
    O_eq = equilibrium_oxygen_after_deox(d, level_pct, T_celsius)
    O_after = min(O_before, O_eq)                       # deoxidation removes oxygen, never adds it
    _, vol_oxide = generated_oxide(max(0.0, O_before - O_after), d)

    porosity = O_after > MAX_DISSOLVED_OXYGEN_PPM
    defects = add_defect(heat.defects, POROSITY_RISK) if porosity else heat.defects
    flags_added = (POROSITY_RISK,) if (porosity and not heat.has_defect(POROSITY_RISK)) else ()
    summary = (
        f"add {level_pct:.3f} % {d.name} → dissolved O {O_before:.0f} → {O_after:.1f} ppm, "
        f"{d.oxide} inclusions {vol_oxide * 1e4:.1f}×10⁻⁴ vol-frac (generated)"
        + ("" if not porosity else f" → POROSITY RISK (O > {MAX_DISSOLVED_OXYGEN_PPM:.0f} ppm spec)")
    )
    step = ProcessStep("deoxidize", summary, in_spec=not porosity, flags_added=flags_added)
    return heat.evolve(
        step, oxygen_ppm=O_after, inclusion_volume_fraction=vol_oxide, inclusion_type=d.oxide, defects=defects,
    )


def degas(
    heat: Heat, *, p_H2: float = 1.0, p_N2: float = 0.79, T_celsius: float = T_TAP_C
) -> Heat:
    """Vacuum-degas the ``Heat`` to the Sieverts equilibrium at ``p_H2`` / ``p_N2`` — fill H and N.

    Sets dissolved hydrogen and nitrogen to their Sieverts solubility (:func:`sieverts_solubility`) at the
    given partial pressures — the equilibrium a vacuum of that depth drives toward. A deep vacuum (low
    ``p_H2``) drops **hydrogen** below the **2 ppm flaking limit**; an insufficient vacuum leaves it above
    and raises the **hydrogen-flaking-risk** flag. **Nitrogen** is filled as a reported field but *not*
    spec-flagged — its Sieverts value is the solubility *limit* (real content sits below it, and vacuum
    strips N only slowly), so a hard N spec would be dishonest. The √p law makes the leverage explicit: the
    *square* of the pressure ratio is the gas-content ratio.
    """
    H = sieverts_solubility("H", p_H2, T_celsius)
    N = sieverts_solubility("N", p_N2, T_celsius)

    flaking = H > MAX_HYDROGEN_PPM
    defects = add_defect(heat.defects, HYDROGEN_FLAKING_RISK) if flaking else heat.defects
    flags_added = (HYDROGEN_FLAKING_RISK,) if (flaking and not heat.has_defect(HYDROGEN_FLAKING_RISK)) else ()
    summary = (
        f"vacuum-degas (p_H₂ {p_H2:g} atm, p_N₂ {p_N2:g} atm) → H {H:.1f} ppm, N {N:.0f} ppm (limit)"
        + ("" if not flaking else f" → FLAKING RISK (H > {MAX_HYDROGEN_PPM:.0f} ppm spec)")
    )
    step = ProcessStep("degas", summary, in_spec=not flaking, flags_added=flags_added)
    return heat.evolve(step, hydrogen_ppm=H, nitrogen_ppm=N, defects=defects)
