"""Tempered-martensite embrittlement — the **irreversible** cementite-film consequence of low tempering.

Phosphorus' martensitic path closed with reversible temper embrittlement (:mod:`steel.temper_embrittlement`):
a *segregation* failure (P → prior-austenite grain boundaries on slow cooling through 375–575 °C), driven by
impurity, and **reversible** (reheat clears it; slow-cool re-embrittles). This module closes the *other*
embrittlement on the tempering axis — the one §11 (:doc:`steel-production`) named as the back-end
``toughness_index`` ceiling but never modelled: **tempered-martensite embrittlement (TME)**, a **microstructural**
failure, driven by **carbon**, and **irreversible**.

When as-quenched martensite is tempered in roughly **260–370 °C** (500–700 °F), the fine transition ε-carbide
is replaced by **cementite (Fe₃C) that precipitates as films** along the interlath and prior-austenite grain
boundaries — fed, in the modern (Horn–Ritchie 1978) picture, by the decomposition of **interlath retained-
austenite films** into M₃C. Those brittle boundary films are an easy crack path: impact toughness dips into a
trough. It is **not** segregation and **not** reversible. Temper *above* ~400 °C and the cementite spheroidizes,
toughness recovers — and, the load-bearing distinction, **the film cannot be restored** by dropping back into
the 260–370 °C band. The carbide morphology is set by the *peak* temper reached: one-way.

The reversible ↔ irreversible foil (the reason this slice completes the pair)
-----------------------------------------------------------------------------
The two are sharp opposites on every axis, and the cleanest test of each is the **temper-cycle toggle**:

============  ===========================================  ===========================================
              reversible temper embrittlement (the sibling)  tempered-martensite embrittlement (here)
============  ===========================================  ===========================================
window        375–575 °C (nose 490–550)                    260–370 °C
driver        **phosphorus** (Ni/Cr co-segregation)        **carbon** (cementite-film source)
mechanism     equilibrium GB *segregation*                 *microstructural* interlath cementite films
needs P?      yes — a clean heat escapes                   **no — a clean heat still embrittles**
reversible?   **yes** — reheat > 600 °C resets, and a       **no** — temper > ~400 °C recovers, and
              later slow-cool **re-embrittles** (toggles)   re-entering the trough **stays tough** (one-way)
cure          Mo (≈0.5 %), or a fast cool through window    temper above the trough (and stay above)
============  ===========================================  ===========================================

That a *clean* steel still embrittles is the headline distinction: TME is carbon/microstructure, not impurity.
Phosphorus is a cited secondary **aggravator** (it deepens and slightly widens the trough), named here, **not**
a verdict knob — modelling its magnitude is out of scope (symmetric with the reversible slice, whose P→DBTT
*slope* was likewise flagged representative). See :func:`steel.temper_embrittlement.temper_embrittlement_check`.

The honest posture — a NEW consumer with NO strict tooth (the gate was run and failed)
--------------------------------------------------------------------------------------
Like the sulfur / red-short slice (:mod:`steel.hot_work`) and the reversible-TE slice, this is **cited constants
+ a by-construction verdict**, *not* a tooth-bearing model. The tempting tooth — "the 260–370 °C toughness
trough *emerges* from the ε→cementite transition + interlath-RA-film decomposition kinetics, without tuning" —
was **gated on paper before any code**: the repo carries no stage-III tempering carbide thermodynamics (no
ε/Fe₃C free energies, no RA-decomposition kinetics), so the trough onset is **underdetermined here** exactly as
the reversible-TE segregation nose was. Pinning it faithfully needs carbide thermochemistry that is out of
scope, so we **do not** build a carbide model *to* land the trough. The parts:

* **By construction (NOT teeth):** the verdict rule (a hardened **martensitic** structure **and** enough
  **carbon** for cementite films **and** a **peak temper inside the trough**); the carbon threshold
  :data:`MIN_CARBON_FOR_TME` (the verified/game boundary, a labelled spec like
  :data:`steel.temper_embrittlement.J_SUSCEPTIBLE`); the peak-temper state model that makes it one-way.
* **Cited mechanism INPUTS (verification ≠ tooth):** the trough **260–370 °C**, the ~**400 °C** recovery /
  irreversibility threshold, the ε→cementite film mechanism, and the interlath-RA-film source. Pinning the
  right numbers guards transcription; none is a falsifiable prediction the model could miss.

**The faithful reuse (architecture, not a tooth):** the verdict *composes with hardenability*. The check runs
the **same frozen back-end quench** (:func:`steel.sweep.evaluate`) the spine's :func:`steel.heat_state.heat_treat`
uses, and gates on its **martensite fraction** — so a section that did not harden (a soft core) has no tempered
martensite to embrittle and TME falls out as immune, while a fully-hardened medium-carbon part tempered at
300 °C embrittles. Retained austenite is cited as the *mechanism* (the interlath-film source) but is **not** the
severity driver: *bulk* RA fraction ranks eutectoid (high-C **plate**-martensite) steels highest, where the
interlath-film mechanism does not apply — the "looks faithful, physically inverted" trap. Carbon drives the
gate; the demonstrator confirms low-carbon martensite (e.g. case-hardening 8620 at 0.20 %C) is immune even when
fully hardened. The carbon gate itself carries **no upper bound** — very-high-carbon *plate* martensite
(eutectoid 1080) tempered in the trough also embrittles, but by a *related* cementite-on-twin / prior-austenite-
boundary path, **not** the interlath-RA-film mechanism this slice narrates; so the demonstrator stays on the
lath-martensite (≲ 0.5 %C) grades the mechanism actually describes. **Named deferrals:** the absolute toughness-trough depth (no Charpy-J — the back-end
``toughness_index`` ceiling stands), the P-aggravation magnitude, and the explicit ε→Fe₃C carbide sequence.
Units: wt % for composition, °C for temperature.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import sweep
from .heat_state import Heat, ProcessStep, add_defect
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Cited inputs & the verified/spec boundary — pinned constants and labelled limits, NOT teeth
# --------------------------------------------------------------------------- #
# The TME trough: tempering as-quenched martensite here precipitates cementite as interlath / grain-boundary
# films and toughness dips. Cited 260-370 C (500-700 F). The peak temper landing in this band embrittles.
TME_WINDOW_C: tuple[float, float] = (260.0, 370.0)
# Temper above this and the cementite spheroidizes — toughness recovers, AND (the load-bearing irreversibility)
# the film cannot be restored by re-entering the trough. Cited "above ~400 C becomes tougher"; the one-way
# boundary the peak-temper state model turns on. (Sits just above the trough top, by construction distinct.)
TME_RECOVERY_C: float = 400.0

# The carbon floor for the cementite-film mechanism — the verified/game boundary (a labelled acceptance spec,
# editable per application, like temper_embrittlement.J_SUSCEPTIBLE). TME is a medium-/high-carbon martensite
# failure (classically 0.3-0.5 %C low-alloy, e.g. 4140 / 4340 / 300M); low-carbon lath martensite (~< 0.2 %C,
# case-hardening grades) carries too little carbon to form the embrittling interlath cementite films. We call a
# heat carbon-susceptible at or above this; it is a by-construction band boundary, NOT a pinned constant.
MIN_CARBON_FOR_TME: float = 0.25

# The structure must be martensite-LED for the consequence to apply: TME embrittles *tempered martensite*, so a
# soft / diffusional structure (a section that did not harden) has nothing to embrittle. Gate on the quench's
# martensite fraction. "Dominant" (>= half), matching design.MARTENSITE_TEMPER_MIN's martensite-led floor.
MARTENSITIC_MIN: float = 0.50

# The defect flag this stage raises (defined here, the module that raises it — as RED_SHORT is in hot_work and
# TEMPER_EMBRITTLED in temper_embrittlement). The OTHER tempering-axis embrittlement, the irreversible one.
TEMPERED_MARTENSITE_EMBRITTLED: str = "tempered-martensite-embrittled"


@dataclass(frozen=True)
class TemperedMartensiteEmbrittlement:
    """The tempered-martensite-embrittlement verdict for a hardened steel at a tempering exposure.

    ``martensite_fraction`` the as-quenched martensite (from the frozen back-end quench); ``martensitic``
    whether it clears :data:`MARTENSITIC_MIN` (a hardened structure to embrittle); ``carbon_sufficient``
    whether the carbon clears :data:`MIN_CARBON_FOR_TME` (enough to form the cementite films);
    ``peak_temper_C`` the **highest** temper the part has reached (the carbide morphology is set by the peak —
    the one-way state); ``in_trough`` whether that peak lands in the 260–370 °C band; ``recovered`` whether the
    peak went past :data:`TME_RECOVERY_C` (over-tempered → tough, and immune to re-entering the trough);
    ``embrittled`` the verdict — martensitic **and** carbon-sufficient **and** the peak in the trough.
    """

    peak_temper_C: float
    martensite_fraction: float
    martensitic: bool
    carbon_sufficient: bool
    in_trough: bool
    recovered: bool
    embrittled: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.embrittled:
            return "TEMPERED-MARTENSITE-EMBRITTLED (interlath cementite films from the 260–370 °C temper — irreversible)"
        if not self.martensitic:
            return "not a hardened martensitic structure — no tempered martensite to embrittle"
        if not self.carbon_sufficient:
            return "low-carbon martensite — too little carbon to form the embrittling cementite films"
        if self.recovered:
            return "over-tempered above the trough — tough, and immune to re-entering it (one-way)"
        if self.peak_temper_C > TME_WINDOW_C[1]:
            return "tempered just above the trough — recovering (tough)"
        return "tempered below the trough — no cementite films (yet)"


def tempered_martensite_embrittlement_assessment(
    comp: Steel, martensite_fraction: float, *, peak_temper_C: float,
) -> TemperedMartensiteEmbrittlement:
    """Whether a hardened ``comp`` is tempered-martensite-embrittled at a ``peak_temper_C`` (the physics-free verdict).

    Three conditions must all hold (the cited mechanism, as a rule): the structure is **martensitic**
    (``martensite_fraction`` ≥ :data:`MARTENSITIC_MIN`, so there is tempered martensite to embrittle), the steel
    has **enough carbon** (≥ :data:`MIN_CARBON_FOR_TME`, the cementite-film source), and its **peak temper lands
    in the trough** (260–370 °C). The peak — the *highest* temper the part has reached — is what carries the
    irreversibility: once it passes :data:`TME_RECOVERY_C` the cementite has spheroidized and re-entering the
    trough cannot reform the film, so ``in_trough`` (read off the peak) is false thereafter. ``martensite_fraction``
    comes from the as-quenched structure; pass the highest temper seen as ``peak_temper_C``.
    """
    mf = float(martensite_fraction)               # the quench may hand a numpy float; the verdict stays plain bool
    martensitic = mf >= MARTENSITIC_MIN
    carbon_sufficient = comp.C >= MIN_CARBON_FOR_TME
    in_trough = TME_WINDOW_C[0] <= peak_temper_C <= TME_WINDOW_C[1]
    recovered = peak_temper_C >= TME_RECOVERY_C
    embrittled = bool(martensitic and carbon_sufficient and in_trough)
    return TemperedMartensiteEmbrittlement(
        peak_temper_C=peak_temper_C,
        martensite_fraction=mf,
        martensitic=martensitic,
        carbon_sufficient=carbon_sufficient,
        in_trough=in_trough,
        recovered=recovered,
        embrittled=embrittled,
    )


def tempered_martensite_embrittlement_check(
    heat: Heat,
    *,
    temper_T_C: float = 300.0,
    prior_peak_temper_C: float | None = None,
    diameter: float = 0.010,
    medium: str | float = "oil",
    austenitize_T: float = 850.0,
    bath_T: float = 25.0,
) -> Heat:
    """Quench-and-temper the ``Heat`` and read whether the low temper embrittled it — the irreversible seam.

    The orchestrator that closes the **other** tempering-axis embrittlement (the counterpart to
    :func:`steel.temper_embrittlement.temper_embrittlement_check`, which closed the *reversible* one). It runs
    the **same frozen back-end quench** :func:`heat_treat` uses (:func:`steel.sweep.evaluate` →
    ``martensite_fraction``), so the verdict **composes with hardenability** (a soft-core section has no tempered
    martensite to embrittle), then applies the trough rule (:func:`tempered_martensite_embrittlement_assessment`).
    If a hardened, medium-/high-carbon part's **peak temper** lands in 260–370 °C it raises the
    **tempered-martensite-embrittled** flag and carries it forward — the mirror of :func:`heat_treat`'s soft-core
    seam. Returns a *new* ``Heat`` with one ``"tme-check"`` :class:`~steel.heat_state.ProcessStep` appended;
    composition is unchanged (carbide morphology moves no bulk composition).

    ``temper_T_C`` the temper applied in this step (default 300 °C, squarely in the trough); ``prior_peak_temper_C``
    the highest temper the part saw **before** this step (``None`` = none) — the effective peak is the max of the
    two, which is how the **irreversibility** threads: once a part has been over-tempered (a prior peak past
    :data:`TME_RECOVERY_C`), re-tempering in the trough leaves it tough. The quench parameters mirror
    :func:`heat_treat`.
    """
    steel = heat.as_steel()
    outcome = sweep.evaluate(steel, medium=medium, diameter=diameter,
                             austenitize_T=austenitize_T, bath_T=bath_T)
    fM = outcome.result.martensite
    peak = temper_T_C if prior_peak_temper_C is None else max(temper_T_C, prior_peak_temper_C)
    a = tempered_martensite_embrittlement_assessment(steel, fM, peak_temper_C=peak)

    defects = add_defect(heat.defects, TEMPERED_MARTENSITE_EMBRITTLED) if a.embrittled else heat.defects
    flags_added = (
        (TEMPERED_MARTENSITE_EMBRITTLED,)
        if (a.embrittled and not heat.has_defect(TEMPERED_MARTENSITE_EMBRITTLED)) else ()
    )
    peak_note = "" if prior_peak_temper_C is None else f" (peak {peak:.0f} °C)"
    summary = (
        f"quench → {fM:.0%} martensite, then temper {temper_T_C:.0f} °C{peak_note} "
        f"(trough {TME_WINDOW_C[0]:.0f}–{TME_WINDOW_C[1]:.0f} °C, C {steel.C:.2f} %) → {a.verdict}"
    )
    step = ProcessStep("tme-check", summary, in_spec=not a.embrittled, flags_added=flags_added)
    return heat.evolve(step, temperature_C=temper_T_C, defects=defects)
