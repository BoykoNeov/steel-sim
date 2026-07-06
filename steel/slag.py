"""Slag-partition refining — dephosphorization / desulfurization (Steel-making **F2**, Slice 2).

The second half of primary refining (``docs/plans/steel-making.md`` §7, the "partition" of F2's
decarb/deox/**partition**/degas). Slice 1 (:mod:`steel.refining`) blew the carbon and killed and degassed
the heat; this module removes the two **tramp impurities the blast furnace leaves in** — phosphorus and
sulfur — by partitioning them into the slag. It is the engine behind the most teachable stretch of
metallurgical history: *why acid Bessemer made rails that cracked, why Thomas' basic lining beat it, and
why sulfur comes out in the ladle and not the converter* (the §14 purity-control ramp). To carry that
state it required the one extension Slice 1 deferred — :class:`~steel.sweep.Steel` now carries ``P`` / ``S``
(the residual-impurity fields), filled here for the first time.

Where the proof rides — the honest posture (this is **not** Slice 1)
--------------------------------------------------------------------
Slice 1's carbon axis was a *validated end-to-end propagation*: the back end **consumes** carbon, so an
over-blow reached a benchmarked soft core. **Phosphorus and sulfur have no such consumer.** The
hardenability and hardness models read C / Si / Mn / Ni / Cr / Mo only (:meth:`~steel.sweep.Steel.minor`);
nothing in the *quench* path reads P or S. So this slice is **benchmarked-physics, the F1-Ellingham /
F4-casting class — not a spine-class propagation.** Its proof is the *physics itself* checked against
published facts. Its downstream consequence (P → grain-boundary embrittlement / raised DBTT; S →
red-shortness) is **closed by dedicated consumers built 2026-06-13** — :func:`steel.heat_state.cold_short_check`
(phosphorus, a propagation through the Pickering DBTT law) and :func:`steel.hot_work.hot_work` (sulfur, a
new hot-working verdict; ``steel-making.md`` §14). F2 Slice 2 *sets the impurity state*; those consumers
*close* it. (The P→DBTT slope they use is flagged representative — the §14 unpinned number; the strength
axis carries the teeth.)

The teeth — and the trap they avoid
------------------------------------
"L rises with basicity" is baked into any correlation that has a basicity term: asserting it proves
nothing (the vacuous-benchmark trap this project has hit before). The teeth that *could* have come out
wrong are:

1. **The opposite oxygen dependence of P and S — the headline, and it falls out of independent sources.**
   Dephosphorization is an **oxidation** (``2[P] + 5[O] + 3(CaO) = (3CaO·P₂O₅)``): it wants *oxidizing*
   conditions, and Healy's correlation carries a **+2.5·log(%Fe_t)** term — more slag iron oxide, more P
   removed. Desulfurization is the **reduction** ``[S] + (O²⁻) = (S²⁻) + [O]``: it wants *reducing*
   conditions, and the sulfide-capacity route carries a **−log a_O** term — more dissolved oxygen, *less* S
   removed. These two signs come from two **independently sourced** correlations (Healy 1970 for P, the
   Sosinsky–Sommerville sulfide capacity + its metal-partition conversion for S), so their being opposite
   is *computed*, not tuned. It cross-coheres with Slice 1 exactly as the Al ≫ Si > Mn deox hierarchy
   cohered with F1's Ellingham order: :func:`desulfurize` **reads the Heat's dissolved oxygen** (set by
   Slice 1's blow + kill), so the *same* slag desulfurizes a deoxidized ladle heat well and a raw converter
   heat barely — the physics dictates the process sequence *dephos (oxidizing) → deox → desulf (reducing)*.
2. **Order-of-magnitude vs an independent measured plant value.** Computed L_P at basic-converter
   conditions lands in the **50–200** BOF range (measured, not from the correlation); computed L_S at
   deoxidized-ladle conditions lands in the **10²–10³** range good ladle slags reach. The *absolute*
   constants are the source-sensitive tier (see below) so these are order-of-magnitude anchors, the same
   posture as Slice 1's deox K.
3. **The acid/basic endpoint — why Bessemer rails cracked.** An *acid* (siliceous, low-CaO) slag has
   ``L_P`` of order **1** even though it is oxidizing: it lacks the basic oxides to fix P₂O₅ as a stable
   phosphate, so phosphorus stays in the steel. Drop in lime (basic Thomas lining) and ``L_P`` jumps by
   orders of magnitude. That qualitative jump is not a coefficient — it is the 0.08·(%CaO) term sweeping
   across the lime range.

By construction (NOT teeth): the metal↔slag **mass-balance partition** (you write the balance, it
conserves), and the **Mn:S → MnS stoichiometry** (the §14 theme-B clearer, *conservation-clean by
definition* — Mushet's manganese that made Bessemer steel sound). They guard transcription; they cannot
fail informatively, and are labelled as such.

What is CITED vs the named ceiling — the two-tier provenance (as in reduction / refining / casting)
---------------------------------------------------------------------------------------------------
* **Robust-anchor teeth.** The *sign* of each oxygen dependence (Healy's +2.5·log %Fe_t; the −log a_O of
  the sulfide-capacity partition) and the *direction* of the basicity dependence; the measured plant
  ranges used as the order-of-magnitude benchmark; the acid-slag L_P ≈ O(1) endpoint.
* **Source-sensitive tier (ranking + order of magnitude only).** The absolute coefficients — Healy 1970
  (``log L_P = 22350/T + 0.08·%CaO + 2.5·log %Fe_t − 16``; known to *over*-predict at high lime),
  Sosinsky–Sommerville (``log C_S = (22690 − 54640·Λ)/T + 43.6·Λ − 25.2``), the C_S→L_S conversion
  (``log L_S = log C_S − log a_O − 770/T + 1.30``), the Duffy–Ingram component optical basicities (FeO/MnO
  are themselves *optimized* from sulfide-capacity data), and the Fe–FeO oxygen anchor (``[%O] = 0.213·a_FeO``
  at 1600 °C) used only to link slag FeO to metal oxygen on a shared axis. P/S equilibria scatter by a
  factor of several between studies — the read is the ranking and the order of magnitude.

  **C_S is now holdout-validated (B3, ADR 0006 — see** :mod:`steel.slag_validation` **).** Graded
  against an *independent* measured dataset (Nzotta–Sichen–Seetharaman, ISIJ Int. 38 (1998) 1170,
  Table 6 — measured after the 1986 fit, MnO/FeO-free so no fitted Λ is in the loop), the
  Sosinsky–Sommerville correlation **carries** for basic Al₂O₃–CaO–MgO–SiO₂ slags: a consistent
  ~×1.4 overprediction with ×1.2 scatter, *exact* composition ranking within temperature, and the
  temperature slope reproduced. So C_S earns "holdout-validated within the basic domain (Λ ≳ 0.65)"
  rather than "order-of-magnitude only" there. Two **named edges** remain source-sensitive and were
  *quantified*, not removed: the **acidic** side (Λ ≲ 0.6) under-predicts ~×4, and **MnO**-rich slags
  over-predict ~×5 (the optical-basicity scale's weak spots).

  **Healy's L_P is now holdout-graded too (B3 phosphorus leg, ADR 0007 — see** :mod:`steel.slag_lp_validation`
  **).** Graded against an *independent* measured dataset (Drain et al., ISIJ Int. 58 (2018) 1965,
  Table 4 — 33 equilibrium heats, measured 48 years after Healy's 1970 fit, L_P defined exactly as the
  ``(%P)/[%P]`` mass ratio), the correlation comes out **honestly benchmarked with a measured,
  basicity-dependent bias**: near-exact in Healy's own fit domain (B2, ``v≈2``: ≈ ×1.0) but
  **over-predicting ≈ ×2 at high lime** (B5, ``v≈5``; ``%CaO ≥ 55`` ≈ ×2.3). The mechanism is the
  ``+0.08·%CaO`` term being *linear and unbounded* where the real L_P *saturates* beyond ``v ≈ 2.5``.
  So the flagged "over-predicts at high lime" caveat below is now a **quantified map** (≈ ×1.0 at
  ``v≈2`` rising to ≈ ×2 at ``v≈5``) — but L_P stays **benchmarked / order-of-magnitude**, *not*
  upgraded to "validated" like C_S (the high-lime bias is real). The metal-partition conversions
  (C_S→L_S) are still uncovered by any holdout — they stay order-of-magnitude.
* **The named ceiling.** Equilibrium partition endpoints, never the *rate* (slag–metal mass-transfer /
  emulsion kinetics — the front-end tar pit, §4); a single lumped slag of fixed mass ratio (no slag
  evolution through the heat); dilute 1-wt% Henrian metal (``a_O ≈ [%O]``, ``f_X ≈ 1``); the optical
  basicity is the *theoretical* (composition-weighted) one; ``a_FeO ≈ X_FeO`` (Raoultian) where the link to
  metal oxygen is drawn. The partition is also **carbon-blind** — Healy's L_P carries no carbon term — so it
  is the caller's job to pair an oxidizing (FeO-rich) slag with a bath that can hold it: dephosphorization
  completes at **low carbon / turndown** (a carbon-saturated melt would reduce that FeO — the carbon boil),
  which is why the demo blows *before* it dephosphorizes, and that carbon–FeO coupling is the unmodelled
  *rate*. P/S **carried but inert** downstream (no validated consumer); the P/S that high-impurity
  ferroalloys would *add back* in the ladle trim is, like F3's carbon carry-in, a named deferral, not
  modelled here.

Units: wt % for composition and slag oxides, **ppm** for dissolved metal oxygen (the field unit on
``Heat``), °C for temperature (converted to K internally).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .heat_state import Heat, ProcessStep, add_defect
from .kinetics import ABS_ZERO
from .refining import T_TAP_C, equilibrium_oxygen
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Spec thresholds & flags — the verified/game boundary (labelled spec, NOT physics)
# --------------------------------------------------------------------------- #
# Where a residual *field* becomes a *defect*. Design requirements (like heat_state.MIN_MARTENSITE_SPEC and
# refining.MAX_DISSOLVED_OXYGEN_PPM), editable per grade — representative quality-steel limits, NOT fitted
# constants. The physics that computes the residual P/S is what is benchmarked; these lines are where we
# decide the result is unacceptable. The *consequence* of crossing them (cold-shortness, red-shortness) is
# now closed by dedicated consumers (heat_state.cold_short_check for P, hot_work.hot_work for S, built
# 2026-06-13); these flags set the residual state those consumers read.
MAX_PHOSPHORUS_PCT: float = 0.035       # cold-short / temper-embrittlement limit (standard SAE 4140-class)
MAX_SULFUR_PCT: float = 0.040           # red-short / hot-tear / MnS limit (free-machining grades run higher)

HIGH_PHOSPHORUS: str = "high-phosphorus"   # under-dephosphorized: residual P → cold-short / GB embrittlement
HIGH_SULFUR: str = "high-sulfur"           # under-desulfurized: residual S → red-short / MnS / hot-tear

# Representative slag-to-metal mass ratios (slag mass / steel mass) — the partition lever. A converter runs a
# large, FeO-rich oxidizing slag; the ladle a smaller, reducing one. Order-of-magnitude (process-specific).
SLAG_RATIO_CONVERTER: float = 0.10      # ~10 % of the metal mass (the big oxidizing dephos slag)
SLAG_RATIO_LADLE: float = 0.02          # ~2 % (the smaller reducing desulf slag)


# --------------------------------------------------------------------------- #
# 1. The slag — composition, the two basicities, and its oxygen lever
# --------------------------------------------------------------------------- #
# Duffy–Ingram component optical basicities Λ_i (the source-sensitive tier — FeO/MnO are *optimized* from
# sulfide-capacity data, not measured optically). With the number of oxygens per formula they give the
# theoretical (composition-weighted) optical basicity of a slag.
_OPTICAL_BASICITY: dict[str, float] = {
    "CaO": 1.00, "SiO2": 0.48, "Al2O3": 0.605, "MgO": 0.78, "FeO": 1.00, "MnO": 1.00,
}
_OXYGENS: dict[str, int] = {"CaO": 1, "SiO2": 2, "Al2O3": 3, "MgO": 1, "FeO": 1, "MnO": 1}
_MOLAR_MASS: dict[str, float] = {
    "CaO": 56.08, "SiO2": 60.08, "Al2O3": 101.96, "MgO": 40.30, "FeO": 71.85, "MnO": 70.94,
}
_FE_IN_FEO: float = 55.85 / 71.85       # mass fraction of iron in FeO (for %Fe_t from %FeO)

# Fe–FeO oxygen anchor: dissolved [%O] in equilibrium with pure liquid FeO at 1600 °C (Fe + [O] = (FeO)),
# k_Fe ≈ 0.213 — the cited link from slag iron oxide to metal oxygen. Used only to put L_P and L_S on a
# shared "oxidizing power" axis (with a_FeO ≈ X_FeO, Raoultian — the named simplification).
K_FE_FEO: float = 0.213


@dataclass(frozen=True)
class Slag:
    """A refining slag (oxide wt %) — the phase the impurities partition *into*.

    The oxides the partition correlations read: ``CaO`` / ``SiO2`` set the basicity that fixes phosphate and
    sulfide; ``FeO`` is the **oxygen lever** (high in the oxidizing converter, near zero in the reducing
    ladle); ``Al2O3`` / ``MgO`` / ``MnO`` round out a real slag and feed the optical basicity. The numbers
    need not sum to 100 (minor oxides, P₂O₅, CaF₂ are not tracked) — the correlations use the listed
    contents directly.
    """

    CaO: float
    SiO2: float
    FeO: float = 0.0
    Al2O3: float = 0.0
    MgO: float = 0.0
    MnO: float = 0.0
    name: str = ""

    @property
    def basicity(self) -> float:
        """Binary basicity ``B = %CaO / %SiO₂`` — the operator's lever (``> 1`` basic, ``< 1`` acid)."""
        return self.CaO / self.SiO2 if self.SiO2 > 0.0 else math.inf

    @property
    def pct_Fe_total(self) -> float:
        """Total iron in the slag (wt %), from its FeO content — the ``%Fe_t`` Healy's L_P reads."""
        return self.FeO * _FE_IN_FEO

    @property
    def optical_basicity(self) -> float:
        """Theoretical optical basicity ``Λ = Σ(nᵢxᵢΛᵢ)/Σ(nᵢxᵢ)`` (equivalent-oxygen-weighted component Λ).

        The composition-weighted electron-donor power the sulfide-capacity model reads; ``x_i`` is the oxide
        mole fraction, ``n_i`` its oxygens, ``Λ_i`` the Duffy–Ingram component value. A pure-lime slag → 1.0,
        a siliceous one → ~0.5.
        """
        oxides = {"CaO": self.CaO, "SiO2": self.SiO2, "Al2O3": self.Al2O3,
                  "MgO": self.MgO, "FeO": self.FeO, "MnO": self.MnO}
        num = den = 0.0
        for ox, wt in oxides.items():
            if wt <= 0.0:
                continue
            moles = wt / _MOLAR_MASS[ox]
            equiv_o = moles * _OXYGENS[ox]          # oxygen equivalents this oxide contributes
            num += equiv_o * _OPTICAL_BASICITY[ox]
            den += equiv_o
        return num / den if den > 0.0 else 0.0

    def label(self) -> str:
        return self.name or f"B={self.basicity:.1f} slag"


# Three reference slags spanning the history (the §14 purity ramp / §15 method map). The acid Bessemer slag
# is oxidizing but lime-poor — it *can't* dephosphorize; the basic converter (Thomas/BOF-class) slag is
# oxidizing AND basic — it does; the ladle slag is basic and FeO-lean — the reducing desulfurizer.
ACID_BESSEMER_SLAG = Slag(CaO=4.0, SiO2=48.0, FeO=38.0, MnO=8.0, name="acid Bessemer")
BASIC_CONVERTER_SLAG = Slag(CaO=45.0, SiO2=12.0, FeO=22.0, MgO=8.0, MnO=5.0, name="basic converter (Thomas/BOF)")
LADLE_DESULF_SLAG = Slag(CaO=52.0, SiO2=8.0, Al2O3=33.0, MgO=7.0, FeO=0.5, name="ladle (CaO–Al₂O₃)")


# --------------------------------------------------------------------------- #
# 2. Dephosphorization — Healy's L_P (the oxidizing partition)
# --------------------------------------------------------------------------- #
# Healy 1970: log[(%P)/[%P]] = 22350/T + 0.08·(%CaO) + 2.5·log₁₀(%Fe_t) − 16  (T in K). The
# source-sensitive tier (one of several published models — Suito–Inoue, Turkdogan — and known to OVER-predict
# at high lime; the holdout in slag_lp_validation quantifies that: ≈ ×1.0 at v≈2 rising to ≈ ×2 at v≈5). The
# robust reads: the +2.5·log %Fe_t **oxidizing** dependence (the sign), the basicity jump from acid to basic,
# and the order of magnitude vs measured BOF L_P ≈ 50–200.
HEALY_T: float = 22350.0
HEALY_CAO: float = 0.08
HEALY_FE: float = 2.5
HEALY_CONST: float = -16.0


def phosphorus_partition(slag: Slag, T_celsius: float = T_TAP_C) -> float:
    """Phosphorus partition ratio ``L_P = (%P)_slag / [%P]_metal`` for ``slag`` at ``T_celsius`` (Healy 1970).

    Large ``L_P`` ⇒ phosphorus pulled into the slag. The two levers that make it large are **basicity**
    (the +0.08·%CaO term — lime to fix the phosphate) and **oxidation** (the +2.5·log %Fe_t term — slag iron
    oxide). An acid slag, lime-poor however oxidizing, lands near ``L_P ≈ 1`` (phosphorus stays in the steel
    — *why acid Bessemer couldn't make rails that survived*); a basic converter slag lands in the hundreds.
    Lower temperature also helps (the 22350/T term) — dephosphorization is favoured cool.
    """
    T_K = T_celsius + ABS_ZERO
    Fe_t = max(slag.pct_Fe_total, 1.0e-6)
    log_Lp = HEALY_T / T_K + HEALY_CAO * slag.CaO + HEALY_FE * math.log10(Fe_t) + HEALY_CONST
    return 10.0 ** log_Lp


# --------------------------------------------------------------------------- #
# 3. Desulfurization — the sulfide capacity and its metal partition (the reducing partition)
# --------------------------------------------------------------------------- #
# Sosinsky–Sommerville: log₁₀ C_S = (22690 − 54640·Λ)/T + 43.6·Λ − 25.2  (T in K, 1400–1700 °C). The
# combined slag-composition + temperature dependence of the *sulfide capacity* C_S, from optical basicity Λ.
CS_A: float = 22690.0
CS_B: float = 54640.0
CS_C: float = 43.6
CS_D: float = -25.2

# The capacity→metal-partition conversion (the metal side of the reaction [S] + (O²⁻) = (S²⁻) + [O]):
# log₁₀ L_S = log₁₀ C_S − log₁₀ a_O − 770/T + 1.30. The **−log a_O** is the reducing dependence — the mirror
# image of Healy's +2.5·log %Fe_t, and the term :func:`desulfurize` reads from the Heat's dissolved oxygen.
LS_T: float = -770.0
LS_CONST: float = 1.30


def sulfide_capacity(slag: Slag, T_celsius: float = T_TAP_C) -> float:
    """Sulfide capacity ``C_S`` of ``slag`` at ``T_celsius`` (Sosinsky–Sommerville, from optical basicity).

    The slag's intrinsic ability to dissolve sulfur as sulfide — composition only (no metal oxygen yet). It
    climbs steeply with optical basicity: a lime-rich ladle slag carries orders of magnitude more sulfur than
    a siliceous one. Feeds :func:`sulfur_partition`, which adds the metal's oxygen dependence.
    """
    T_K = T_celsius + ABS_ZERO
    Lam = slag.optical_basicity
    log_Cs = (CS_A - CS_B * Lam) / T_K + CS_C * Lam + CS_D
    return 10.0 ** log_Cs


def sulfur_partition(slag: Slag, oxygen_ppm: float, T_celsius: float = T_TAP_C) -> float:
    """Sulfur partition ratio ``L_S = (%S)_slag / [%S]_metal`` for ``slag`` at dissolved ``oxygen_ppm``.

    ``log L_S = log C_S − log a_O − 770/T + 1.30`` with the metal oxygen activity ``a_O ≈ [%O]`` (dilute
    Henrian, the same standard state Slice 1 uses; ``a_O = oxygen_ppm / 10⁴``). The **−log a_O** is the whole
    coupling: a deoxidized ladle heat (a few ppm O) desulfurizes well, the *same* slag on a raw converter heat
    (tens–hundreds of ppm O) barely moves the sulfur — the reason desulfurization is a reducing **ladle** step,
    after the kill, not a converter one. Raises on non-positive oxygen (``a_O`` undefined as ``[%O] → 0``).
    """
    if oxygen_ppm <= 0.0:
        raise ValueError(f"dissolved oxygen must be positive (a_O undefined as [%O] → 0), got {oxygen_ppm}")
    T_K = T_celsius + ABS_ZERO
    a_O = oxygen_ppm / 1.0e4
    log_Ls = math.log10(sulfide_capacity(slag, T_celsius)) - math.log10(a_O) + LS_T / T_K + LS_CONST
    return 10.0 ** log_Ls


def metal_oxygen_for_feo(slag: Slag, T_celsius: float = T_TAP_C) -> float:
    """Metal dissolved oxygen (**ppm**) in Fe–FeO equilibrium with ``slag`` — the shared-axis link.

    ``[%O] = k_Fe · a_FeO`` (``k_Fe = 0.213`` at 1600 °C; ``a_FeO ≈ X_FeO`` Raoultian — the named
    simplification). The bridge that lets dephosphorization's slag-FeO lever and desulfurization's metal-O
    lever sit on one *oxidizing-power* axis: a high-FeO converter slag implies a high metal oxygen (consistent
    with Slice 1's blown-heat number), a near-zero-FeO ladle slag a low one. Order-of-magnitude only.
    """
    oxides = {"CaO": slag.CaO, "SiO2": slag.SiO2, "Al2O3": slag.Al2O3,
              "MgO": slag.MgO, "FeO": slag.FeO, "MnO": slag.MnO}
    total_moles = sum(wt / _MOLAR_MASS[ox] for ox, wt in oxides.items() if wt > 0.0)
    if total_moles <= 0.0:
        return 0.0
    x_FeO = (slag.FeO / _MOLAR_MASS["FeO"]) / total_moles
    return K_FE_FEO * x_FeO * 1.0e4                  # wt % → ppm


# --------------------------------------------------------------------------- #
# 4. Conservation — the mass-balance partition and Mn:S → MnS (by construction, NOT teeth)
# --------------------------------------------------------------------------- #
def partition_remaining(initial_pct: float, L: float, slag_ratio: float) -> float:
    """Residual metal content (wt %) after partitioning at ratio ``L`` into a slag of mass ``slag_ratio``.

    The metal↔slag mass balance: with ``(%X)_slag = L·[%X]_metal`` and a slag-to-metal mass ratio ``R``,
    conserving the element (``[%X]₀·m_metal = [%X]·m_metal + L·[%X]·m_slag``) gives ``[%X] = [%X]₀ / (1 +
    L·R)``. **By construction** — it is the balance solved, so the element is conserved across the two phases
    exactly; the test that ``metal + slag = initial`` guards transcription, it cannot fail informatively.
    """
    if initial_pct < 0.0 or L < 0.0 or slag_ratio < 0.0:
        raise ValueError(f"inputs must be non-negative, got {initial_pct}, {L}, {slag_ratio}")
    return initial_pct / (1.0 + L * slag_ratio)


# Mn + S → MnS: a 1:1 atomic reaction. The weight ratio for exact stoichiometry is M_Mn/M_S = 54.94/32.06
# ≈ 1.71; the historical rule of thumb is Mn:S ≳ 2–3 (excess manganese) so sulfur reports as benign
# higher-melting MnS, not grain-boundary FeS (≈ 988 °C, red-short). This is Mushet's manganese — what made
# Bessemer steel sound. The stoichiometry is conservation-clean by construction (§14 theme B), NOT a tooth.
M_MN: float = 54.94
M_S: float = 32.06
M_MNS: float = 87.00
MN_PER_S: float = M_MN / M_S            # ≈ 1.71 wt Mn per wt S, fully tied as MnS


@dataclass(frozen=True)
class SulfideBalance:
    """The Mn:S → MnS outcome — what ties up, what is free, and whether the steel is sulfide-safe."""

    ratio: float            # Mn:S by weight
    forms_mns: bool         # enough Mn to bind all the sulfur as MnS (ratio ≥ 1.71)
    mns_pct: float          # MnS formed (wt %), = bound S × M_MnS/M_S
    free_sulfur_pct: float  # sulfur left unbound (→ FeS, the red-short risk) if Mn is short


def manganese_sulfide(Mn_pct: float, S_pct: float) -> SulfideBalance:
    """Resolve ``Mn`` + ``S`` → MnS for the given contents (the §14 theme-B conservation clearer).

    Sulfur is bound 1:1 (atomic) by manganese; with ``Mn:S ≥ 1.71`` (weight) all of it reports as MnS and
    none is left as embrittling FeS. Returns the ratio, the MnS formed, and any free sulfur. The mass balance
    (``Mn consumed = bound S × 1.71``; MnS = bound S × 2.71) closes by construction — Mushet's fix, stated as
    arithmetic, not benchmarked.
    """
    ratio = Mn_pct / S_pct if S_pct > 0.0 else math.inf
    bound_S = min(S_pct, Mn_pct / MN_PER_S)          # sulfur the available Mn can tie up
    return SulfideBalance(
        ratio=ratio,
        forms_mns=ratio >= MN_PER_S,
        mns_pct=bound_S * (M_MNS / M_S),
        free_sulfur_pct=max(0.0, S_pct - bound_S),
    )


# --------------------------------------------------------------------------- #
# 5. The orchestrator seam — partition P / S out of a Heat into a slag
# --------------------------------------------------------------------------- #
def dephosphorize(
    heat: Heat, slag: Slag = BASIC_CONVERTER_SLAG, *,
    slag_ratio: float = SLAG_RATIO_CONVERTER, T_celsius: float = T_TAP_C,
) -> Heat:
    """Partition phosphorus from the ``Heat`` into ``slag`` — the **oxidizing converter** step.

    Computes :func:`phosphorus_partition` for the slag, drops the composition's ``P`` by the mass balance
    (:func:`partition_remaining`), and repacks a new ``Heat`` with a ``"dephosphorize"`` step. A **basic**
    converter slag (high lime, high FeO) pulls phosphorus down by orders of magnitude; an **acid** slag
    leaves it almost untouched — and if the residual stays above :data:`MAX_PHOSPHORUS_PCT` the
    **high-phosphorus** flag is raised (its cold-short consequence closed downstream by
    :func:`steel.heat_state.cold_short_check`).
    """
    Lp = phosphorus_partition(slag, T_celsius)
    P0 = heat.composition.P
    P1 = partition_remaining(P0, Lp, slag_ratio)
    comp = replace(heat.composition, P=P1)

    high = P1 > MAX_PHOSPHORUS_PCT
    defects = add_defect(heat.defects, HIGH_PHOSPHORUS) if high else heat.defects
    flags_added = (HIGH_PHOSPHORUS,) if (high and not heat.has_defect(HIGH_PHOSPHORUS)) else ()
    summary = (
        f"{slag.label()} (B={slag.basicity:.1f}, %Fe_t {slag.pct_Fe_total:.0f}) → L_P {Lp:.0f}, "
        f"P {P0:.3f} → {P1:.3f} %"
        + ("" if not high else f" → HIGH P (> {MAX_PHOSPHORUS_PCT:.3f} % spec)")
    )
    step = ProcessStep("dephosphorize", summary, in_spec=not high, flags_added=flags_added)
    return heat.evolve(step, composition=comp, defects=defects)


def desulfurize(
    heat: Heat, slag: Slag = LADLE_DESULF_SLAG, *,
    slag_ratio: float = SLAG_RATIO_LADLE, T_celsius: float = T_TAP_C,
) -> Heat:
    """Partition sulfur from the ``Heat`` into ``slag`` — the **reducing ladle** step (reads dissolved O).

    The coupling that defines the slice: it **reads the Heat's** ``oxygen_ppm`` (set by Slice 1's blow and
    kill) as the metal oxygen activity for :func:`sulfur_partition`. A deoxidized heat (a few ppm O) gives a
    large ``L_S`` and the sulfur drops; the *same* slag on a heat that has **not** been deoxidized (the high
    oxygen of the blow) barely moves it — the physics reason desulfurization waits for the ladle. When
    ``oxygen_ppm`` is ``None`` (no kill recorded) the undeoxidized C–O-equilibrium oxygen at the heat's carbon
    is used (so an out-of-order desulf honestly under-performs). Residual above :data:`MAX_SULFUR_PCT` raises
    the **high-sulfur** flag (its red-short consequence closed downstream by :func:`steel.hot_work.hot_work`,
    once manganese fails to tie the sulfur as MnS).
    """
    O = heat.oxygen_ppm if heat.oxygen_ppm is not None else equilibrium_oxygen(heat.composition.C, T_celsius)
    Ls = sulfur_partition(slag, O, T_celsius)
    S0 = heat.composition.S
    S1 = partition_remaining(S0, Ls, slag_ratio)
    comp = replace(heat.composition, S=S1)

    high = S1 > MAX_SULFUR_PCT
    defects = add_defect(heat.defects, HIGH_SULFUR) if high else heat.defects
    flags_added = (HIGH_SULFUR,) if (high and not heat.has_defect(HIGH_SULFUR)) else ()
    killed = heat.oxygen_ppm is not None
    summary = (
        f"{slag.label()} (Λ={slag.optical_basicity:.2f}, a_O from {O:.0f} ppm O"
        f"{'' if killed else ' — UNKILLED'}) → L_S {Ls:.0f}, S {S0:.3f} → {S1:.3f} %"
        + ("" if not high else f" → HIGH S (> {MAX_SULFUR_PCT:.3f} % spec)")
    )
    step = ProcessStep("desulfurize", summary, in_spec=not high, flags_added=flags_added)
    return heat.evolve(step, composition=comp, defects=defects)
