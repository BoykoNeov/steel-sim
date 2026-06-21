"""Casting & solidification — Scheil microsegregation + Chvorinov time (Steel-making **F4**, Slice 1).

The link that **closes the chain front-to-back** (``docs/plans/steel-making.md`` §7 / build-order item 3).
Where F1 reduced ore to iron and the F-spine (``heat_state``) threaded a *given* composition through the
back end, F4 produces the **cast billet** the back end consumes — and produces it *non-uniformly*. That
non-uniformity is the whole point: solidification **rejects solute** into the last liquid to freeze, so a
casting's **centerline** is alloy-enriched → locally **more hardenable** → it over-hardens into a hard,
crack-prone **band** while the rest of the section is on spec. That is the §6 failure-propagation link
"centerline segregation → uneven hardenability", and it is the first link whose *upstream* end is a real
front-end engine and whose *downstream* end is the already-validated back end — the front-to-back proof.

Slice 1 — what this module is (and what it defers)
--------------------------------------------------
This is **Slice 1**: the part that feeds the proof. It is pure solidification *thermodynamics* and needs
**no solver** (standalone, like :mod:`steel.reduction`):

* **Scheil microsegregation** — the closed form ``C_s = k·C₀·(1−f_s)^(k−1)`` for the solute redistributed
  during freezing, and the **centerline-enriched composition** it implies, handed to the back end as a
  real casting-produced :class:`~steel.heat_state.Heat` (replacing ``Heat.from_grade``'s stand-in origin).
* **Chvorinov's rule** — solidification time ``t = B·M²`` in the casting *modulus* ``M = V/A`` (the foundry
  rule of thumb), for the "how long does it take, and which section freezes last" axis.

**Deferred to Slice 2** (named, not built here): the latent-heat solidification *temperature field* on the
diffusion solver (the iconic "solidification map" — an apparent-heat-capacity / enthalpy formulation, *not*
a trivial source term, because the solver's PDE carries no capacity coefficient on the LHS), and the defect
criteria (Niyama shrinkage-porosity, hot-tear) which are mostly game-layer "plausible, not validated". The
T-field is iconic but does **not** feed the composition handoff the proof rides on — so it is not gating.

What is CITED vs the named ceiling — the non-circularity discipline (as in reduction/grain)
-----------------------------------------------------------------------------------------
* **CITED (the inputs), in two honestly-distinct provenance tiers.** The equilibrium partition coefficients
  ``k`` (= C_solid/C_liquid at the interface) and liquidus slopes ``m`` are standard solidification data:
  **(1)** C, Si, Mn, P, S from **Won & Thomas 2001** (Metall. Mater. Trans. A 32:1755, Table I), in *both*
  the δ-ferrite and γ-austenite phases — **read from the paper's table (primary-source verified)**; the
  teeth (conservation + severity ordering) rest on these. **(2)** Cr, Ni, Mo from an **ISIJ in-situ
  measurement** (Fe–Cr–Ni–Mo–Cu, ISIJ Int. 60(2):2020 — Cr 0.96, Ni 0.97 ≈ constant, Mo 0.70 → 0.60),
  **verified against that paper but γ-mode-measured and used as a single representative value** (a
  δ-specific substitutional coefficient is not separately pinned; the demonstration is ranking-grade and
  was checked robust across the δ/γ spread, so it does *not* rest on these). Implemented into the
  equations, never redistributed as a dataset (terms of use, §11).
* **The benchmark the data must clear** (the teeth, un-tuned): the **segregation severity ordering** —
  S, P (tiny ``k``) segregate far more than the substitutionals Mn/Si/Cr/Ni/Mo (``k`` near 1) — reproduces
  *why* sulphur and phosphorus are the dangerous segregators; and the centerline-enrichment magnitude lands
  in the published interdendritic range (Mn ≈ ×1.3–1.6). The **conservation leg has real teeth here**: the
  mean solid solute over a full freeze, ``∫₀¹ C_s df_s``, returns ``C₀`` exactly (solute is *rejected*, not
  *created*) — that is a genuine check, not the tautological "the closed form reproduces itself".
* **The named ceiling — Scheil is the no-back-diffusion UPPER bound.** Scheil assumes **zero** solid-state
  back-diffusion, so it *over*-predicts segregation (the real answer lies between Scheil and the lever rule;
  Brody–Flemings/Clyne–Kurz interpolate — not modelled). **Carbon is the worst case**: C is interstitial and
  diffuses fast in the solid, so Scheil grossly over-states C segregation — hence the centerline handoff
  leans on the **substitutional** alloys (Mn/Cr/Mo/Ni/Si, which also drive the hardenability the back end
  reads) and treats C's enrichment as an over-estimate (``enrich_carbon=False`` by default). Also omitted:
  the **δ/γ peritectic** switch for ``C > 0.53 wt%`` (the demonstrator grades are below it, so primary δ is
  right), dendrite coarsening, and the ``f_s → 1`` Scheil singularity (``C_L → ∞``; characterised at a named
  cutoff ``f_s*`` < 1, the last-to-freeze fraction). The mold constant ``B`` in Chvorinov is process-specific
  (mold, superheat) — ranking/rule-of-thumb grade, not a pinned magnitude.

Units: wt % for composition, °C for temperature, metres for the casting modulus, seconds for time.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .heat_state import Heat, ProcessStep
from .sweep import Steel

# --------------------------------------------------------------------------- #
# 1. Cited solidification data — equilibrium partition coefficients & liquidus slopes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Solute:
    """A solute's equilibrium partition coefficients and liquidus slope — the cited inputs.

    ``k_delta`` / ``k_gamma`` are the equilibrium partition coefficients ``k = C_solid/C_liquid`` for
    primary **δ-ferrite** and **γ-austenite** solidification (a solute with ``k < 1`` is rejected into the
    liquid → segregates; the smaller ``k``, the worse). ``m_liquidus`` is the liquidus-line slope
    (°C per wt %), used to depress the iron melting point into the alloy liquidus (Won & Thomas Eq. 13).
    ``None`` where a source does not pin it (the alloy slopes are minor and omitted).
    """

    name: str
    k_delta: float
    k_gamma: float
    m_liquidus: float | None = None


# Two provenance tiers, honestly distinct:
#  * C, Si, Mn, P, S — Won & Thomas 2001 Table I, both phases + liquidus slope: read directly from the
#    paper's table (primary-source verified). The teeth (conservation + severity ordering) rest on these.
#  * Cr, Ni, Mo — ISIJ in-situ measurement (Fe–Cr–Ni–Mo–Cu, ISIJ Int. 60(2):2020), verified against the
#    paper: Cr 0.96, Ni 0.97 "almost constant" through solidification, Mo "gradually 0.70 → 0.60". These
#    are **austenitic-mode (γ) measurements used as a single representative value for both phase slots** —
#    a δ-specific coefficient for the substitutionals is NOT separately pinned (literature spread); the
#    demonstration is ranking-grade and was verified robust across the δ/γ spread, so it does not rest here.
SOLUTES: dict[str, Solute] = {
    "C":  Solute("C",  0.19,  0.34,  78.0),    # interstitial — Scheil OVER-predicts (fast back-diffusion)
    "Si": Solute("Si", 0.77,  0.52,   7.6),
    "Mn": Solute("Mn", 0.76,  0.78,   4.9),
    "P":  Solute("P",  0.23,  0.13,  34.4),    # strong segregator (the embrittling impurity)
    "S":  Solute("S",  0.05,  0.035, 38.0),    # extreme segregator (red-shortness / MnS)
    "Cr": Solute("Cr", 0.96,  0.96,  None),    # ISIJ in-situ (≈ constant); representative, not δ/γ-resolved
    "Ni": Solute("Ni", 0.97,  0.97,  None),    # ISIJ in-situ (≈ constant); representative
    "Mo": Solute("Mo", 0.70,  0.70,  None),    # ISIJ in-situ (drifts to ~0.60 late — severe end-seg, named)
}

# Melting point of pure iron (°C), Won & Thomas Eq. 13 anchor for the liquidus.
T_PURE_FE: float = 1536.0
# δ→γ peritectic carbon (wt %): above it primary solidification switches to γ (Won & Thomas §C). The
# demonstrator grades sit below it, so primary δ is correct — this is the named phase ceiling.
PERITECTIC_C: float = 0.53
# Latent heat of fusion of steel (J/kg) — cited context for the (deferred) latent-heat map / Chvorinov.
LATENT_HEAT_FUSION: float = 272.0e3

# The substitutional alloys the centerline handoff leans on (they segregate AND drive hardenability);
# carbon is excluded by default (Scheil over-predicts it — see the module ceiling).
SUBSTITUTIONAL_ALLOYS: tuple[str, ...] = ("Si", "Mn", "Ni", "Cr", "Mo")

# Default last-to-freeze solid fraction characterising the centerline (the f_s* cutoff below the f_s→1
# Scheil singularity — the interdendritic last-liquid enrichment, the standard ~0.9–0.95 choice).
FS_CENTERLINE: float = 0.95

# A representative Chvorinov mold constant for steel in a greensand mold (s/m²) — ≈ 2 min/cm², the
# textbook foundry figure. Process-specific (mold, superheat): ranking/rule-of-thumb grade, not pinned.
B_STEEL_SAND: float = 1.2e6


def partition_coefficient(solute: str, phase: str = "delta") -> float:
    """Equilibrium partition coefficient ``k`` of ``solute`` for ``phase`` (``"delta"`` / ``"gamma"``)."""
    s = SOLUTES[solute]
    if phase == "delta":
        return s.k_delta
    if phase == "gamma":
        return s.k_gamma
    raise ValueError(f"phase must be 'delta' or 'gamma', got {phase!r}")


# --------------------------------------------------------------------------- #
# 2. Scheil microsegregation — the closed form and its conservation/benchmark teeth
# --------------------------------------------------------------------------- #
def scheil_solid_composition(C0: float, k: float, fs: float) -> float:
    """Scheil solid composition at the interface when a fraction ``fs`` has frozen (wt %).

    ``C_s(f_s) = k·C₀·(1 − f_s)^(k − 1)`` — the **non-equilibrium lever rule**: no back-diffusion in the
    solid, complete mixing in the liquid (Scheil 1942; Won & Thomas Eq. 2). For ``k < 1`` the solid that
    freezes gets progressively richer as ``f_s → 1`` (the rejected solute piles up in the shrinking
    liquid), diverging at ``f_s = 1`` — the named singularity that motivates a cutoff ``f_s* < 1``.
    """
    if not 0.0 <= fs < 1.0:
        raise ValueError(f"solid fraction must be in [0, 1), got {fs}")
    return k * C0 * (1.0 - fs) ** (k - 1.0)


def scheil_liquid_composition(C0: float, k: float, fs: float) -> float:
    """Enriched **liquid** composition when a fraction ``fs`` has frozen: ``C_L = C₀·(1 − f_s)^(k − 1)``.

    The interdendritic liquid that pools at and feeds the last-to-freeze centerline; the solid frozen from
    it is ``k·C_L`` = :func:`scheil_solid_composition`.
    """
    if not 0.0 <= fs < 1.0:
        raise ValueError(f"solid fraction must be in [0, 1), got {fs}")
    return C0 * (1.0 - fs) ** (k - 1.0)


def segregation_ratio(k: float, fs: float) -> float:
    """Solid segregation ratio ``C_s/C₀ = k·(1 − f_s)^(k − 1)`` at solid fraction ``fs`` (composition-free).

    The dimensionless severity of segregation — > 1 where the solute is enriched. The *ordering* of this
    across solutes at a fixed ``fs`` (S, P highest; Mn/Cr/Ni near 1) is the un-tuned benchmark tooth.
    """
    return scheil_solid_composition(1.0, k, fs)


def solute_in_liquid(C0: float, k: float, fs: float) -> float:
    """Solute mass still in the liquid at solid fraction ``fs`` (per unit total): ``(1 − f_s)·C_L``.

    The lever arm: the residual-liquid mass ``(1 − f_s)`` times its enriched concentration
    :func:`scheil_liquid_composition`, which simplifies to ``C₀·(1 − f_s)^k`` — an exact closed form.
    """
    return (1.0 - fs) * scheil_liquid_composition(C0, k, fs)


def solute_in_solid(C0: float, k: float, fs: float, n: int = 4000) -> float:
    """Solute mass frozen into the solid by fraction ``fs`` (per unit total): ``∫₀^{fs} C_s(f_s') df_s'``.

    Evaluated by midpoint quadrature of the Scheil solid composition — an **independent** computation of the
    frozen solute (it knows nothing of the answer), accurate while ``fs`` stays off the ``f_s = 1``
    singularity. It exists to be summed with :func:`solute_in_liquid` for the conservation check, and to be
    cross-checked against its own closed form ``C₀·(1 − (1 − f_s)^k)``.
    """
    if not 0.0 <= fs < 1.0:
        raise ValueError(f"solid fraction must be in [0, 1), got {fs}")
    total = 0.0
    dx = fs / n
    for i in range(n):
        total += scheil_solid_composition(C0, k, (i + 0.5) * dx) * dx
    return total


def scheil_mass_balance(C0: float, k: float, fs: float) -> float:
    """Total solute accounted for at fraction ``fs``: solute in solid + solute in liquid — returns ``C₀``.

    The conservation leg with **real teeth**: Scheil *rejects* solute forward, it does not create it, so at
    every solid fraction the solute already frozen into the solid (:func:`solute_in_solid`, a numeric
    integral of ``C_s``) plus the solute still dissolved in the shrinking liquid (:func:`solute_in_liquid`,
    the analytic lever) must sum to the nominal ``C₀``. Two **independently written** closed forms reached by
    different routes (a quadrature vs a lever) — they reconcile to ``C₀`` only if both are correct, so this
    is a genuine mass-balance check, not the tautological "the closed form integrates to its own known value".
    """
    return solute_in_solid(C0, k, fs) + solute_in_liquid(C0, k, fs)


def liquidus_temperature(comp: dict[str, float]) -> float:
    """Alloy liquidus (°C): ``T_liq = T_pure(Fe) − Σ mᵢ·Cᵢ`` (Won & Thomas Eq. 13).

    The temperature at which freezing begins. Sums only the solutes with a pinned liquidus slope ``m``
    (C/Si/Mn/P/S — which dominate the depression; the alloy slopes are minor and omitted, the named gap).
    """
    drop = 0.0
    for el, wt in comp.items():
        s = SOLUTES.get(el)
        if s is not None and s.m_liquidus is not None:
            drop += s.m_liquidus * wt
    return T_PURE_FE - drop


# --------------------------------------------------------------------------- #
# 3. Chvorinov's rule — solidification time from the casting modulus
# --------------------------------------------------------------------------- #
def casting_modulus(volume: float, surface_area: float) -> float:
    """The casting modulus ``M = V/A`` (m) — volume per cooling surface area, the heat-extraction length."""
    if surface_area <= 0.0:
        raise ValueError("surface area must be positive")
    return volume / surface_area


def chvorinov_time(modulus: float, B: float = B_STEEL_SAND) -> float:
    """Chvorinov solidification time ``t = B·M²`` (s) for a section of modulus ``M`` (m).

    The foundry rule of thumb: solidification time scales with the **square** of the modulus (a chunkier
    section, more volume per cooling face, freezes far slower) — the ``t ∝ M²`` law is the robust teaching
    content; the mold constant ``B`` (default :data:`B_STEEL_SAND`, steel in greensand) is process-specific,
    so the *magnitude* is rule-of-thumb grade, the *ranking* of sections is the reliable read.
    """
    return B * modulus * modulus


# --------------------------------------------------------------------------- #
# 4. The handoff — a cast section emits a nominal + a centerline-enriched Heat
# --------------------------------------------------------------------------- #
def centerline_enriched_composition(
    steel: Steel,
    fs: float = FS_CENTERLINE,
    phase: str = "delta",
    *,
    enrich_carbon: bool = False,
) -> Steel:
    """The Scheil-enriched **centerline** composition of a casting of ``steel`` (a new :class:`Steel`).

    Each solute the back end reads is multiplied by its Scheil solid segregation ratio
    :func:`segregation_ratio` at the last-to-freeze fraction ``fs`` — the interdendritic enrichment locked
    into the last metal to solidify at the centerline. Leans on the **substitutional** alloys
    (:data:`SUBSTITUTIONAL_ALLOYS` — they segregate *and* raise hardenability); **carbon is left at nominal
    by default** (``enrich_carbon=False``) because Scheil over-predicts interstitial C (the module ceiling).
    ``phase`` selects δ (primary for ``C < 0.53 wt%`` grades) or γ partition coefficients.
    """
    def enriched(el: str, wt: float) -> float:
        if wt == 0.0 or el not in SOLUTES:
            return wt
        if el == "C" and not enrich_carbon:
            return wt
        if el != "C" and el not in SUBSTITUTIONAL_ALLOYS:
            return wt
        return wt * segregation_ratio(partition_coefficient(el, phase), fs)

    return Steel(
        C=enriched("C", steel.C),
        Mn=enriched("Mn", steel.Mn),
        Si=enriched("Si", steel.Si),
        Ni=enriched("Ni", steel.Ni),
        Cr=enriched("Cr", steel.Cr),
        Mo=enriched("Mo", steel.Mo),
        name=f"{steel.label()} centerline",
    )


@dataclass(frozen=True)
class CastSection:
    """A cast section: the nominal billet and its segregated centerline, as back-end-ready Heats.

    ``steel`` the nominal (ladle) composition that was cast; ``fs_centerline`` / ``phase`` the Scheil
    parameters; ``modulus`` (m) and ``solidification_time`` (s) the Chvorinov read; ``liquidus`` (°C) where
    freezing began. ``nominal_heat`` and ``centerline_heat`` are two **real casting-produced**
    :class:`~steel.heat_state.Heat` records (each with a "cast" provenance origin) — the same composition
    everywhere on spec, vs the alloy-enriched centerline. Threading *both* through
    :func:`~steel.heat_state.heat_treat` is the front-to-back proof: the centerline over-hardens into a band.
    """

    steel: Steel
    fs_centerline: float
    phase: str
    modulus: float
    solidification_time: float
    liquidus: float
    nominal_heat: Heat
    centerline_heat: Heat


def cast_billet(
    steel: Steel,
    *,
    modulus: float = 0.025,
    fs_centerline: float = FS_CENTERLINE,
    phase: str = "delta",
    B: float = B_STEEL_SAND,
) -> CastSection:
    """Cast a section of ``steel`` → a :class:`CastSection` carrying its nominal and centerline Heats.

    Computes the liquidus and Chvorinov solidification time, then emits the two casting-produced Heats: the
    nominal composition (on spec) and the Scheil centerline-enriched composition
    (:func:`centerline_enriched_composition`). Each Heat starts its provenance trail with a **"cast"** origin
    step (a real front-end origin, replacing :meth:`~steel.heat_state.Heat.from_grade`'s back-end stand-in),
    at the solidus-cooled state. ``modulus`` is the section ``V/A`` (m); ``phase`` defaults to primary δ.
    """
    T_liq = liquidus_temperature({
        "C": steel.C, "Mn": steel.Mn, "Si": steel.Si, "Ni": steel.Ni, "Cr": steel.Cr, "Mo": steel.Mo,
    })
    t_solid = chvorinov_time(modulus, B)
    centerline = centerline_enriched_composition(steel, fs_centerline, phase)

    def cast_heat(comp: Steel, where: str) -> Heat:
        origin = ProcessStep(
            "cast",
            f"{where} of a {steel.label()} casting (modulus {modulus * 1000:g} mm, "
            f"liquidus {T_liq:.0f} °C, solidified in {t_solid:.0f} s)",
            in_spec=(where == "nominal section"),
        )
        return Heat(composition=comp, temperature_C=25.0, history=(origin,))

    return CastSection(
        steel=steel, fs_centerline=fs_centerline, phase=phase,
        modulus=modulus, solidification_time=t_solid, liquidus=T_liq,
        nominal_heat=cast_heat(steel, "nominal section"),
        centerline_heat=cast_heat(centerline, "segregated centerline"),
    )


def cast_billet_onto(
    parent: Heat,
    *,
    modulus: float = 0.025,
    fs_centerline: float = FS_CENTERLINE,
    phase: str = "delta",
    B: float = B_STEEL_SAND,
) -> CastSection:
    """Cast ``parent``'s steel, **re-basing** the nominal billet onto ``parent``'s provenance trail.

    The ``Heat``-consuming twin of :func:`cast_billet`. Where :func:`cast_billet` takes a
    :class:`~steel.sweep.Steel` and emits two **fresh-trail** Heats (a real front-end *origin*, the
    ``"cast"`` step starting a new history), this takes a live ``Heat`` already carrying its upstream
    history and threads it *through* casting: the returned :class:`CastSection`'s ``nominal_heat`` inherits
    ``parent``'s whole trail with the ``"cast"`` step appended — **one** continuous ``Heat`` across F4 — so a
    full-chain run never has to start a fresh trail at the casting seam. The ``centerline_heat`` (and every
    other field) is exactly :func:`cast_billet`'s: the segregation read is a property of the *casting*, not
    of the upstream trail.

    Pure repack — **no new physics, no triad** (the same structural class as
    :meth:`~steel.heat_state.Heat.evolve`). The nominal composition *equals* ``parent``'s, because
    :func:`cast_billet` Scheil-enriches only the *centerline* (the nominal section carries the input
    composition through), so the re-base appends the cast step and the solidus-cooled temperature and
    changes nothing else. This **promotes** ``demo_capstone``'s demo-local ``_cast_onto`` (next-directions
    B2, Option A) to a public seam — the move that demo's docstring named as the promotion trigger, now that
    a second surface (the ``game/`` spine) needs the same glue and the trigger says *promote, don't
    duplicate*.
    """
    section = cast_billet(parent.as_steel(), modulus=modulus, fs_centerline=fs_centerline, phase=phase, B=B)
    cast_step = section.nominal_heat.history[-1]                   # the "cast" origin step cast_billet made
    nominal_onto_parent = parent.evolve(
        cast_step,
        composition=section.nominal_heat.composition,
        temperature_C=section.nominal_heat.temperature_C,
    )
    return replace(section, nominal_heat=nominal_onto_parent)
