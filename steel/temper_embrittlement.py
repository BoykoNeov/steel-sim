"""Temper embrittlement — the **martensitic** phosphorus consequence (reversible, alloy-driven).

The third and last impurity consequence, and the second half of phosphorus' story. :func:`cold_short_check`
(:mod:`steel.heat_state`) closed the **ferritic / normalized** P path through the Pickering DBTT law; this
module closes the **quench-and-tempered (martensitic)** path. Reversible temper embrittlement is the famous
failure of large alloy forgings and pressure-vessel steels: phosphorus (with Sn/Sb/As) **co-segregates with
nickel and chromium to prior-austenite grain boundaries** during slow cooling through — or holding in —
roughly **375–575 °C** (fastest ~490–550 °C). The grain boundaries lose cohesion, the fracture turns
intergranular, and the ductile–brittle transition climbs by tens to >100 °C. It is **reversible**: reheat
above ~600 °C and cool *fast* and the segregation disperses. **Molybdenum (≈0.5 %) is the classic cure** — it
scavenges phosphorus and suppresses the segregation; it is the reason Ni–Cr forging steels carry a Mo
addition.

The honest posture — a NEW consumer with NO strict tooth (the gate was run and failed)
--------------------------------------------------------------------------------------
Like the sulfur / red-short slice (:mod:`steel.hot_work`), this is **cited constants + a by-construction
verdict**, *not* a benchmarked propagation and *not* a tooth-bearing model. The tempting tooth — "the
embrittlement C-curve nose emerges at the observed ~490–550 °C from cited segregation thermodynamics +
diffusion kinetics, without tuning" — was **tested on paper before any code was written** (the discipline
that saved the deox-curve minimum and the Fe–FeS eutectic) and **could not be pinned**. Fed the cited
ΔG_seg(P) = −34469 + 22.9·T J/mol (Yang–Chen / Erhart–Grabke) and the cited D_P(α-Fe) Arrhenius, a tractable
Langmuir–McLean equilibrium × diffusion-kinetics model runs ~**100× faster** than the paper's own kinetic
anchor (450 °C → ~10 h) and yields no single, time-stable nose. The 100× is the tell, not the verdict: the
real kinetics add an Fe₃P-cluster step the simple model omits, and *correcting* for the missing slowness (a
slower effective D) pushes the peak **up** from ~410 °C **toward** the observed 490–550 °C — so the model is
**underdetermined, not wrong-placed**. Pinning the nose faithfully needs the cluster kinetics, which is out
of scope. The honest conclusion is therefore "**no claimable tooth**," not "the physics lands the nose
elsewhere" — and building the segregation model *to* land the nose would be manufacturing a tooth. We don't.
The parts:

* **By construction (NOT teeth):** the **J-factor** susceptibility index `J = (Mn + Si)(P + Sn)·10⁴`
  (Watanabe) — a regression-fit empirical ranking, so "high J ⇒ susceptible" cannot come out wrong; and the
  verdict rule (susceptible **and** exposed in the danger window **and** unprotected by Mo).
* **Cited mechanism INPUTS (verification ≠ tooth):** the danger window **375–575 °C** (fastest ~490–550 °C),
  the **≥600 °C** de-embrittlement / reversibility threshold, the **≈0.5 % Mo** suppression level, and the
  Ni/Cr co-segregation promotion. Pinning the right numbers guards transcription; none is a falsifiable
  prediction the model could miss.

**The teaching beat (a coherence note, not a tooth):** in the registry only the dirty Ni–Cr victim (J ≈ 225)
clears `J_SUSCEPTIBLE`; the lean carbon/alloy grades 1080/1045/8620/4140 sit at J ≈ 108–138 and come out safe
**by low J** (a little residual P in a lean matrix), *not* by the Mo rule — 4140 and 8620 carry only ~0.2 % Mo,
below the 0.5 % suppression level, so the model never marks them Mo-protected. Molybdenum is the cited cure,
and the demo proves it on the genuinely-susceptible J ≈ 225 victim — it just isn't what makes the registry
grades safe here. The classic *victims* are clean-looking Ni–Cr steels merely slow-cooled with a little
residual phosphorus. **Named deferrals:** the absolute ΔFATT magnitude (scattered, calibration-heavy);
the full Guttmann co-segregation kinetics / the Fe₃P-cluster C-curve. The *irreversible* sibling on the
tempering axis — tempered-martensite embrittlement (260–370 °C cementite films, a different mechanism) — is now
its own consumer (:mod:`steel.tempered_martensite_embrittlement`). Units: wt % for composition, °C for
temperature.
"""
from __future__ import annotations

from dataclasses import dataclass

from .heat_state import Heat, ProcessStep, add_defect
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Cited inputs & the verified/spec boundary — pinned constants and a labelled limit, NOT teeth
# --------------------------------------------------------------------------- #
# The reversible-temper-embrittlement danger window: phosphorus co-segregates to prior-austenite grain
# boundaries fastest here. Broad band 375-575 C; most rapid 490-550 C in Ni-Cr steels. Cited inputs.
TE_WINDOW_C: tuple[float, float] = (375.0, 575.0)     # the embrittling exposure band
TE_NOSE_C: tuple[float, float] = (490.0, 550.0)       # fastest embrittlement (the C-curve nose region)
# Reheat above this and cool FAST and the segregation disperses — the reversibility that names the phenomenon.
DE_EMBRITTLEMENT_C: float = 600.0
# Molybdenum scavenges phosphorus; ~0.5 % "greatly reduces" susceptibility (the classic cure). Cited level.
MO_SUPPRESSION_PCT: float = 0.5

# J-factor susceptibility limit — the verified/game boundary (a labelled acceptance spec, editable per
# application, like heat_state.MIN_MARTENSITE_SPEC). Clean pressure-vessel practice targets J < ~100-180; we
# call a heat susceptible above this. The J-factor *value* is the cited Watanabe formula; this line is where
# we decide the result is unacceptable.
J_SUSCEPTIBLE: float = 150.0

# The defect flag this stage raises (defined here, the module that raises it — as RED_SHORT is in hot_work).
TEMPER_EMBRITTLED: str = "temper-embrittled"   # reversible P grain-boundary segregation, intergranular fracture


def j_factor(comp: Steel, *, Sn_pct: float = 0.0) -> float:
    """Watanabe's temper-embrittlement susceptibility index ``J = (Mn + Si)(P + Sn)·10⁴`` (wt %).

    The standard empirical susceptibility ranking for low-alloy (Ni-Cr-Mo-V) steels: manganese and silicon
    promote the phosphorus (and tin) grain-boundary segregation, so their product scales the susceptibility.
    **By construction** — it is a regression-fit index, so a large ``J`` cannot fail to read "susceptible";
    it ranks heats, it is not a benchmark. Tin is in the formula but absent from the registry, so it defaults
    to zero (pass ``Sn_pct`` to include it). Nickel and chromium are *not* in ``J`` (it presumes a low-alloy
    matrix) but promote the segregation — the reason Ni-Cr steels are the classic victims.
    """
    return (comp.Mn + comp.Si) * (comp.P + Sn_pct) * 1.0e4


@dataclass(frozen=True)
class TemperEmbrittlement:
    """The reversible-temper-embrittlement verdict for a steel at a tempering / service exposure.

    ``j`` the Watanabe susceptibility index; ``susceptible`` whether it clears :data:`J_SUSCEPTIBLE`;
    ``mo_protected`` whether molybdenum (≥ :data:`MO_SUPPRESSION_PCT`) suppresses it; ``exposed`` whether the
    thermal history put the part in the danger window long enough to segregate (held in 375–575 °C, or slow-
    cooled through it); ``embrittled`` the verdict — susceptible **and** exposed **and** not Mo-protected.
    """

    j: float
    susceptible: bool
    mo_protected: bool
    exposed: bool
    embrittled: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.embrittled:
            return "TEMPER-EMBRITTLED (P → prior-austenite grain boundaries — intergranular fracture)"
        if self.susceptible and self.mo_protected:
            return "susceptible by composition, but molybdenum suppresses the segregation"
        if self.susceptible and not self.exposed:
            return "susceptible by composition, but the thermal path avoided the danger window"
        return "not susceptible (clean / low-J) — tough"


def temper_embrittlement_assessment(
    comp: Steel,
    *,
    exposure_T_C: float,
    slow_cool: bool = True,
    Sn_pct: float = 0.0,
) -> TemperEmbrittlement:
    """Whether ``comp`` is reversibly temper-embrittled by an exposure at ``exposure_T_C`` (the physics-free verdict).

    Three conditions must all hold (the cited mechanism, as a rule): the steel is **susceptible** (J-factor
    above :data:`J_SUSCEPTIBLE`), it is **exposed** (held in the 375–575 °C danger window, or — the usual
    culprit — *slow-cooled through it*, so it spent time segregating), and it is **not Mo-protected**
    (< :data:`MO_SUPPRESSION_PCT`). Reheating above :data:`DE_EMBRITTLEMENT_C` and cooling *fast*
    (``slow_cool=False`` from an exposure above the window) clears it — the reversibility. ``exposure_T_C`` is
    the tempering or holding temperature; ``slow_cool`` whether the part then cooled slowly through the window
    (large forgings do; a fast quench from temper does not).
    """
    j = j_factor(comp, Sn_pct=Sn_pct)
    susceptible = j >= J_SUSCEPTIBLE
    mo_protected = comp.Mo >= MO_SUPPRESSION_PCT
    held_in_window = TE_WINDOW_C[0] <= exposure_T_C <= TE_WINDOW_C[1]
    exposed = held_in_window or slow_cool        # time in the window: tempered there, or slow-cooled through it
    embrittled = susceptible and exposed and not mo_protected
    return TemperEmbrittlement(
        j=j, susceptible=susceptible, mo_protected=mo_protected, exposed=exposed, embrittled=embrittled,
    )


def temper_embrittlement_check(
    heat: Heat,
    *,
    exposure_T_C: float = 540.0,
    slow_cool: bool = True,
    Sn_pct: float = 0.0,
) -> Heat:
    """Read whether tempering / slow-cooling the ``Heat`` reversibly embrittles it — the martensitic-P seam.

    The orchestrator that closes the **martensitic** half of phosphorus' consequence (the counterpart to
    :func:`steel.heat_state.cold_short_check`, which closed the ferritic half). It reads composition and the
    thermal exposure (:func:`temper_embrittlement_assessment`) and, if a susceptible heat segregated in the
    danger window without Mo protection, raises the **temper-embrittled** flag and carries it forward — the
    mirror of :func:`heat_treat`'s soft-core seam. Returns a *new* ``Heat`` with one ``"temper-embrittle-check"``
    :class:`~steel.heat_state.ProcessStep` appended; composition is unchanged (segregation moves no bulk
    composition). Default exposure 540 °C, slow-cooled — squarely in the danger window.
    """
    a = temper_embrittlement_assessment(
        heat.composition, exposure_T_C=exposure_T_C, slow_cool=slow_cool, Sn_pct=Sn_pct,
    )
    defects = add_defect(heat.defects, TEMPER_EMBRITTLED) if a.embrittled else heat.defects
    flags_added = (TEMPER_EMBRITTLED,) if (a.embrittled and not heat.has_defect(TEMPER_EMBRITTLED)) else ()
    cool = "slow-cooled" if slow_cool else "fast-cooled"
    summary = (
        f"temper/expose {exposure_T_C:.0f} °C ({cool}), J-factor {a.j:.0f} "
        f"(susceptible > {J_SUSCEPTIBLE:.0f}), Mo {heat.composition.Mo:.2f} % → {a.verdict}"
    )
    step = ProcessStep("temper-embrittle-check", summary, in_spec=not a.embrittled, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
