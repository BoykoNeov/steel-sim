"""Gas (CO) porosity — the dissolved-oxygen *consequence* (Steel-making, the casting stage after F2).

The consumer that **closes the oxygen consequence** F2 (:mod:`steel.refining`) deferred. Refining's
``deoxidize`` already *fills* the ``Heat``'s dissolved oxygen and raises a chemistry-state
**``porosity-risk``** flag when the killed-bath oxygen clears a single spec line
(:data:`steel.refining.MAX_DISSOLVED_OXYGEN_PPM` = 30 ppm). But whether a *casting* actually develops the
**CO blowholes** that pit an under-killed ingot is a different, deferred question — and a fundamentally
**carbon-aware** one. Dissolved oxygen blows holes only by reacting with dissolved **carbon**:
``[C] + [O] = CO(g)``. The very same carbon–oxygen product that governs the converter (F2 decarburization)
governs the casting: where ``[%C]·[%O]`` exceeds the CO equilibrium, gas evolves at the freezing front and
is trapped as porosity. So a single oxygen line cannot decide it — a high-carbon heat well *within* the
oxygen spec can still blow holes, and a low-carbon heat *over* it can stay sound. This module reads that
outcome — the two-tier pattern of cold-short (propagation) / red-short / hydrogen-flaking: refining sets the
*risk* (a carbon-blind oxygen line), this sets the *consequence* (does CO actually evolve, given the carbon).

The model — the carbon-aware CO criterion, and why it is standalone (no engine, no ADR)
---------------------------------------------------------------------------------------
The controlling physics is the **same C–O equilibrium F2 already pins**. CO gas evolves and is trapped when
the dissolved carbon–oxygen product crosses the equilibrium product at the freezing front (~1 atm, the
free-surface / top-of-section condition where blowholes nucleate):

    [%C]·[%O]  >  K_CO  =  p_CO / K   (the same ``refining.carbon_oxygen_product``)

So the porosity *verdict* is a **scalar from a closed form** — the supersaturation ratio
``S = [%C]·[%O] / K_CO`` (``S > 1`` ⇒ CO evolves ⇒ porous). No solver is needed (and the latent-heat
solidification field, :mod:`steel.solidification`, would buy no new content — the verdict is a bath/front
chemistry scalar, not a temperature map). Standalone, like :mod:`steel.hydrogen_flaking` and
:mod:`steel.reduction`: it reuses :func:`steel.refining.carbon_oxygen_product` (the CO equilibrium) and,
for the conservative secondary diagnostic only, :func:`steel.casting.scheil_liquid_composition`.

What is the load-bearing physics, what is conservative-secondary, and the honest tooth posture
----------------------------------------------------------------------------------------------
This is a **thin consumer** (the hydrogen-flaking / red-short class), not a benchmarked field model — named
so up front. The map:

* **The load-bearing verdict — the carbon-aware bath/front CO product (``S = [%C][%O]/K_CO``).** Oxygen is
  held at its **as-refined** value (it is *not* Scheil-enriched — see the next bullet for why that would be
  wrong, not merely approximate). The discrimination is robust at the bath, with **no cutoff dependence**:
  a well-killed heat (low O) sits far under the line at any carbon; an under-killed high-carbon heat sits
  over it. This is the carbon-aware *refinement* of refining's carbon-blind 30 ppm line, and the build's
  reason to exist (the demo shows the two flags **disagreeing** because of carbon). The high-carbon hero's
  modest ``S ≈ 1.05`` is **sign-robust, not marginal**: the C–O coupling self-limits a high-carbon heat's
  dissolved oxygen to ~its C–O equilibrium, so an under-killed high-C heat sits *on the tap C–O line* and its
  verdict reduces to the cooling-supersaturation ratio ``K_CO(tap)/K_CO(front) > 1`` — guaranteed by the
  front being colder than tap, the absolute-K_CO scatter cancelling in the ratio (see :data:`T_SOLIDIFICATION_C`).
* **NO claimable tooth — by construction + cited inputs (the reversible-TE / TME landing).** There is no
  tight benchmark here: the criterion *is* the cited C–O equilibrium evaluated against held composition, so
  it cannot independently "fail". The one soft, order-of-magnitude **coherence note** (not a tooth): the
  critical oxygen ``O_crit(C) = K_CO / [%C]`` falls as ``1/C`` with **no tuning** (``K_CO`` cited, the
  ``1/C`` shape is algebra), reproducing the metallurgical rule that *high-carbon steels must be killed and
  only low-carbon steels can be rimmed / semi-killed* — and exposing the carbon-blindness of a flat oxygen
  spec. Label it OoM-coherence; it is really by-construction. Nothing else is claimed.
* **Conservative secondary (decorative, NOT the verdict) — the solidification CO-margin.** As a section
  freezes, Scheil rejection enriches the interdendritic carbon, eroding the CO margin of a bath-sound heat;
  :func:`solidification_co_fraction` reports the solid fraction at which that enrichment would drive a
  bath-sound heat over the line. It is **conservative and cutoff-dominated, so it is not the verdict**: it
  leans on **carbon-Scheil enrichment, which** :mod:`steel.casting` **explicitly disowns** (``enrich_carbon
  =False``, "Scheil over-predicts interstitial C"), and the ``f_s → 1`` Scheil singularity means *any* held
  oxygen eventually crosses — so a crossing fraction below the :data:`FS_CO_CUTOFF` cutoff would false-flag
  even a sound high-carbon killed steel (1095, 52100 cast sound routinely). It is a "freezing shrinks the
  margin" indicator for the figure, never a pass/fail.
* **Cited INPUTS (verification ≠ tooth):** the C–O equilibrium ``ΔG° = −19840 − 40.65·T`` (Vidhyasagar
  2023 / standard; :data:`steel.refining.DG_CO_A`/``DG_CO_B``), evaluated at a representative solidification
  temperature (:data:`T_SOLIDIFICATION_C`); the Scheil carbon partition coefficient (Won & Thomas, via
  :mod:`steel.casting`) for the secondary diagnostic only; the 30 ppm risk line shared with
  :data:`steel.refining.MAX_DISSOLVED_OXYGEN_PPM`.

**Named ceiling:** the model is the CO-evolution *criterion* at the freezing front — *not* the bubble
nucleation/escape kinetics that set how much trapped porosity actually results. ``p_CO`` is pinned at 1 atm
(the free-surface condition); the **ferrostatic head** that suppresses CO deep in a tall section (real — the
bottom of a rimming ingot rims less) is a named over-conservatism, not modelled, as is the nucleation
overpressure ``2γ/r``. Oxygen is held at the as-refined value (reprecipitation of oxide as the melt cools
pins dissolved O in killed steel — which is *why* Scheil-enriching it would be wrong). Shrinkage / Niyama
porosity (a feeding problem, not a gas problem) stays the F4-Slice-2 deferral. Units: wt % for carbon, ppm
for dissolved oxygen (the field unit on ``Heat``), °C for temperature, atm for partial pressure.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import casting
from . import refining
from .heat_state import Heat, ProcessStep, add_defect

# --------------------------------------------------------------------------- #
# Pinned conditions & the verified/spec boundary — cited inputs, NOT teeth
# --------------------------------------------------------------------------- #
# A representative solidification (freezing-range) temperature for plain / low-alloy steel: the liquidus of
# the demonstrator grades sits near here, a little below the ~1600 °C tap. The CO equilibrium K_CO is
# evaluated here rather than at tap because the blowholes form at the *freezing front*. The pin is not
# load-bearing for the *sign* of the verdict: an undeoxidized / under-killed heat sits on the **tap C–O
# line** (``[%C]·[%O] = K_CO(tap)``), so its supersaturation reduces to the pure **cooling ratio**
# ``S = K_CO(tap)/K_CO(front)``, which is ``> 1`` for *any* front below tap (physically certain) and grows as
# the front cools toward the true freezing range — 1530 °C is if anything a high (conservative) estimate. The
# ~7 % absolute-K_CO scatter between 1600 and 1500 °C largely **cancels in that ratio** (the ΔG° slope is
# better constrained than the absolute level). The grade's own liquidus (steel.casting.liquidus_temperature)
# is the physically-exact T choice, omitted to avoid the coupling.
T_SOLIDIFICATION_C: float = 1530.0

# The partial pressure of CO at which gas evolves — pinned at 1 atm, the free-surface / top-of-section
# condition where blowholes nucleate. The ferrostatic head that raises p_CO (and suppresses CO) deep in a
# tall section is the named ceiling — a real, conservative-direction omission (the deep ingot rims less).
P_CO_FRONT: float = 1.0

# The risk/consequence boundary — refining's carbon-blind oxygen line, reused so the two-tier story is
# explicit (a labelled engineering spec, like heat_state.MIN_MARTENSITE_SPEC, not fitted physics).
POROSITY_RISK_O_PPM: float = refining.MAX_DISSOLVED_OXYGEN_PPM   # 30 ppm

# The last-to-freeze solid fraction characterising the interdendritic centerline — the cutoff for the
# *conservative secondary* solidification-margin diagnostic only (NOT the verdict). Reused from casting's
# centerline fraction so the two modules agree on "last liquid"; the Scheil f_s→1 singularity is why this
# diagnostic cannot be a pass/fail (see the module docstring).
FS_CO_CUTOFF: float = casting.FS_CENTERLINE                     # 0.95

# The defect flag this stage raises (the actual porosity consequence) — distinct from refining's
# porosity-RISK (the upstream carbon-blind oxygen flag). The two-tier pattern: risk → consequence.
GAS_POROSITY: str = "gas-porosity"   # dissolved C + O → trapped CO blowholes in the casting


def co_equilibrium_product(T_celsius: float = T_SOLIDIFICATION_C, p_CO: float = P_CO_FRONT) -> float:
    """The CO equilibrium product ``K_CO = [%C]·[%O]`` at the freezing front (wt %·wt %).

    A thin alias of :func:`steel.refining.carbon_oxygen_product` — the *same* cited C–O equilibrium the
    converter runs on (``ΔG° = −19840 − 40.65·T``), here evaluated at the solidification temperature and the
    free-surface ``p_CO``. Above this product CO evolves; the supersaturation against it is the verdict.
    """
    return refining.carbon_oxygen_product(T_celsius, p_CO)


def critical_oxygen(carbon_pct: float, T_celsius: float = T_SOLIDIFICATION_C, p_CO: float = P_CO_FRONT) -> float:
    """The dissolved oxygen (**ppm**) at which a ``carbon_pct`` heat is on the CO line: ``O_crit = K_CO/[%C]``.

    The carbon-aware porosity boundary — falls as ``1/C`` (the soft OoM-coherence note: high-carbon steels
    must be killed hard, low-carbon steels can be rimmed). The flat 30 ppm risk line crosses this curve near
    ``C ≈ K_CO/0.003 ≈ 0.67 %``: leaner than that the spec over-warns, richer it under-warns — the
    carbon-blindness the consequence corrects. Raises on non-positive carbon (the product diverges as C → 0).
    """
    if carbon_pct <= 0.0:
        raise ValueError(f"carbon must be positive (O_crit diverges as %C → 0), got {carbon_pct}")
    return co_equilibrium_product(T_celsius, p_CO) / carbon_pct * 1.0e4


def co_supersaturation(
    carbon_pct: float, oxygen_ppm: float, *, T_celsius: float = T_SOLIDIFICATION_C, p_CO: float = P_CO_FRONT
) -> float:
    """The CO supersaturation ratio ``S = [%C]·[%O] / K_CO`` (dimensionless) — the verdict driver.

    ``S > 1`` ⇒ the dissolved carbon–oxygen product is over the CO equilibrium ⇒ gas evolves at the freezing
    front ⇒ the casting is porous; ``S < 1`` ⇒ the heat is killed enough for that carbon ⇒ sound. Oxygen is
    the **as-refined** value (held, not Scheil-enriched — the module ceiling). Carbon-aware by construction:
    the same oxygen gives a larger ``S`` at a higher carbon, which is the whole point of the consequence.
    """
    product = carbon_pct * (oxygen_ppm * 1.0e-4)          # wt %·wt %
    return product / co_equilibrium_product(T_celsius, p_CO)


def solidification_co_fraction(
    carbon_pct: float,
    oxygen_ppm: float,
    *,
    T_celsius: float = T_SOLIDIFICATION_C,
    p_CO: float = P_CO_FRONT,
    phase: str = "delta",
) -> float:
    """**Conservative secondary diagnostic (NOT the verdict):** the solid fraction at which Scheil carbon
    enrichment would drive a *bath-sound* heat over the CO line.

    As freezing rejects carbon into the interdendritic liquid (``C_L = C₀·(1−f_s)^(k−1)``,
    :func:`steel.casting.scheil_liquid_composition`), the CO product climbs; this returns the ``f_s`` where
    ``C_L·[%O] = K_CO`` (oxygen still held). Solved in closed form
    ``f_s = 1 − [K_CO/([%C][%O])]^{1/(k−1)}``, clamped to ``0`` for a bath that is already over the line.

    **Why this is decorative, not a pass/fail:** it leans on carbon-Scheil enrichment, which
    :mod:`steel.casting` disowns as an over-prediction (``enrich_carbon=False``), so it is conservative; and
    because ``C_L → ∞`` as ``f_s → 1``, *any* held oxygen eventually crosses — a crossing below
    :data:`FS_CO_CUTOFF` would false-flag a sound high-carbon killed steel. So it is reported only as a
    "freezing erodes the CO margin" indicator (a larger value = more freezing margin); the verdict is the
    bath supersaturation :func:`co_supersaturation`.
    """
    product = carbon_pct * (oxygen_ppm * 1.0e-4)
    K_CO = co_equilibrium_product(T_celsius, p_CO)
    if product <= 0.0:
        return 1.0                                        # no oxygen (or no carbon) → never crosses
    if product >= K_CO:
        return 0.0                                        # already over the line at the bath (f_s = 0)
    k = casting.partition_coefficient("C", phase)
    one_minus_fs = (K_CO / product) ** (1.0 / (k - 1.0))  # k − 1 < 0 → in (0, 1) when product < K_CO
    return 1.0 - one_minus_fs


# --------------------------------------------------------------------------- #
# The porosity verdict — does the casting blow holes, given its carbon and oxygen?
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PorosityAssessment:
    """Whether a casting develops CO porosity, given its carbon and as-refined dissolved oxygen.

    ``carbon_pct`` the heat's carbon (wt %); ``oxygen_ppm`` the as-refined dissolved oxygen (held);
    ``co_product`` / ``K_CO`` the dissolved C–O product and the CO equilibrium product (wt %·wt %);
    ``supersaturation`` ``S = co_product/K_CO`` (the verdict driver, ``> 1`` ⇒ porous); ``critical_oxygen``
    the carbon-aware oxygen line ``K_CO/[%C]`` (ppm); ``risk_oxygen`` the carbon-blind 30 ppm refining line;
    ``solidification_co_fraction`` the conservative freezing-margin diagnostic (not the verdict);
    ``porous`` the verdict (``supersaturation > 1``).
    """

    carbon_pct: float
    oxygen_ppm: float
    co_product: float
    K_CO: float
    supersaturation: float
    critical_oxygen: float
    risk_oxygen: float
    solidification_co_fraction: float
    porous: bool

    @property
    def risk_flagged(self) -> bool:
        """Whether refining's carbon-blind oxygen line (30 ppm) would flag this heat (``porosity-risk``)."""
        return self.oxygen_ppm > self.risk_oxygen

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.porous:
            extra = (" — within the 30 ppm oxygen spec, but the carbon makes it blow holes"
                     if not self.risk_flagged else "")
            return (f"POROUS (dissolved C·O over the CO line, S = {self.supersaturation:.2f}{extra})")
        extra = (" — over the 30 ppm oxygen spec, but too lean in carbon to evolve CO"
                 if self.risk_flagged else "")
        return f"sound (killed enough for this carbon, S = {self.supersaturation:.2f}{extra})"


def porosity_assessment(
    carbon_pct: float,
    oxygen_ppm: float,
    *,
    T_celsius: float = T_SOLIDIFICATION_C,
    p_CO: float = P_CO_FRONT,
    phase: str = "delta",
) -> PorosityAssessment:
    """Resolve whether a casting develops CO porosity (the carbon-aware criterion): is ``[%C][%O] > K_CO``?

    The dissolved carbon–oxygen product (carbon from the composition, oxygen the as-refined value, **held**)
    against the CO equilibrium product at the freezing front. The casting is **porous** when the
    supersaturation ``S = [%C][%O]/K_CO`` exceeds 1 — CO evolves and is trapped. The freezing-margin
    diagnostic (:func:`solidification_co_fraction`) is computed and carried, but it is *not* the verdict
    (the module ceiling). Raises on a non-positive carbon (the CO product is undefined as ``%C → 0``).
    """
    if carbon_pct <= 0.0:
        raise ValueError(f"carbon must be positive (the CO product is undefined as %C → 0), got {carbon_pct}")
    K_CO = co_equilibrium_product(T_celsius, p_CO)
    product = carbon_pct * (oxygen_ppm * 1.0e-4)
    S = product / K_CO
    return PorosityAssessment(
        carbon_pct=carbon_pct,
        oxygen_ppm=oxygen_ppm,
        co_product=product,
        K_CO=K_CO,
        supersaturation=S,
        critical_oxygen=critical_oxygen(carbon_pct, T_celsius, p_CO),
        risk_oxygen=POROSITY_RISK_O_PPM,
        solidification_co_fraction=solidification_co_fraction(
            carbon_pct, oxygen_ppm, T_celsius=T_celsius, p_CO=p_CO, phase=phase),
        porous=S > 1.0,
    )


def gas_porosity_check(
    heat: Heat,
    *,
    T_celsius: float = T_SOLIDIFICATION_C,
    p_CO: float = P_CO_FRONT,
    phase: str = "delta",
) -> Heat:
    """Cast the ``Heat`` and read whether it blows CO holes — the oxygen-consequence seam.

    The orchestrator that **closes the oxygen consequence**: it reads the Heat's carbon (composition) and
    its as-refined dissolved oxygen (filled by :func:`steel.refining.deoxidize`) and, if the carbon–oxygen
    product is over the CO equilibrium at the freezing front, raises the **gas-porosity** flag and carries
    it forward — the mirror of :func:`steel.hydrogen_flaking.hydrogen_flaking_check` for dissolved oxygen
    rather than hydrogen. Distinct from refining's upstream carbon-blind ``porosity-risk``: this is the
    carbon-aware *consequence*. Returns a *new* ``Heat`` with one ``"gas-porosity-check"``
    :class:`~steel.heat_state.ProcessStep` appended; composition is unchanged (the verdict reads state, it
    does not alter the alloy). Raises if the Heat carries no dissolved-oxygen state yet (run
    :func:`steel.refining.deoxidize` first).
    """
    if heat.oxygen_ppm is None:
        raise ValueError("Heat has no dissolved-oxygen state — run refining.deoxidize first (F2 fills it)")
    a = porosity_assessment(heat.composition.C, heat.oxygen_ppm, T_celsius=T_celsius, p_CO=p_CO, phase=phase)
    defects = add_defect(heat.defects, GAS_POROSITY) if a.porous else heat.defects
    flags_added = (GAS_POROSITY,) if (a.porous and not heat.has_defect(GAS_POROSITY)) else ()
    summary = (
        f"cast at {heat.composition.C:.2f} %C, O {heat.oxygen_ppm:.0f} ppm "
        f"(O_crit {a.critical_oxygen:.0f} ppm for this carbon) → {a.verdict}"
    )
    step = ProcessStep("gas-porosity-check", summary, in_spec=not a.porous, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
