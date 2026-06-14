"""Peritectic surface cracking — the **carbon** consequence at the *casting* stage (δ→γ contraction).

The carbon-driven sibling of the sulfur-driven :mod:`steel.hot_tear`. Both are *solidification cracking*
read at the casting stage, but they are **different mechanisms on different chemistry**, and the contrast is
the point of building this one separately:

* :mod:`steel.hot_tear` — **sulfur**, in the **last liquid to freeze**: a Fe–FeS film between the dendrites
  that the casting tears across. It reads the **Scheil-enriched** interdendritic *liquid* (segregation is the
  whole story).
* this module — **carbon**, at the **primary solidification front**: the peritectic transformation
  ``L + δ → γ`` is a large **volume contraction** (δ-ferrite is BCC, austenite γ is the denser FCC), and when
  it happens fast and high in the mould it shrinks the thin solidifying **shell** away from the wall → an air
  gap → uneven heat extraction → a non-uniform shell with depressions and **longitudinal facial cracks**.
  Famously the **hypo-peritectic ``~0.10–0.16 wt% C`` grades** are the worst surface-crackers in continuous
  casting, and — counter-intuitively — both a *leaner* and a *richer* steel cast more soundly.

**The load-bearing distinction from** :mod:`steel.hot_tear` **— read NOMINAL (bulk) carbon, never the Scheil
last liquid.** This is the *reverse* of the hot-tear catch. The peritectic δ→γ contraction is a
**primary-solidification / shell** phenomenon governed by the **bulk grade chemistry** (the aim/ladle carbon),
not the segregated centerline; Wolf's ferrite potential is universally computed on ladle carbon. (And
:mod:`steel.casting` already defaults ``enrich_carbon=False`` because Scheil over-predicts interstitial C.) So:
**peritectic reads nominal; sulfur hot-tear reads the last liquid.** Enriching carbon here would model the
wrong place.

The model — a CITED empirical classifier (Wolf), a CITED lever-rule mechanism, NO claimable tooth
----------------------------------------------------------------------------------------------------
The same honest posture as the sibling consequences (hot-tear / gas-porosity / hydrogen-flaking): a thin,
standalone consumer — **no solver, no engine touch, no ADR** — whose verdict *is* cited inputs by
construction. The map:

* **The verdict — Wolf's ferrite potential band (CITED).** ``FP = 2.5·(0.5 − Cp)`` (M. M. Wolf), where ``Cp``
  is a **carbon equivalent** (carbon plus the austenite/ferrite-stabilizing alloy shift). ``FP`` measures how
  much peritectic reaction a grade undergoes: ``FP > 1.05`` solidifies essentially ferritic (a "sticker"
  grade), ``FP ≤ 0.8`` essentially austenitic, the peritectic reaction is **maximal at FP = 1.0**, and the
  **crack-susceptible "depression" band is ``0.8 < FP < 1.05``** (≈ ``Cp`` 0.10–0.18 wt% for plain carbon).
  These thresholds are cited (Wolf; reviewed in Azizi & Thomas, *Metall. Mater. Trans. B* 51:1875, 2020 and *ISIJ Int.*
  55:781, 2015) — so the verdict is a labelled classifier, not a benchmark it could "fail".
* **The carbon equivalent — REPRESENTATIVE (tier-2, the named ceiling).** ``Cp`` is what makes ``FP`` a *tool*
  rather than a carbon lookup: alloying shifts the effective carbon **into or out of** the band — austenite
  stabilizers (Mn, Ni, Cu, N) raise ``Cp``, ferrite stabilizers (Si, Cr, Mo, Al, P) lower it. But the
  **coefficient values genuinely spread across the literature** (Wolf 1991/1997; "various values are found",
  per the 2020 review), and the single-``Cp`` substitution is itself an approximation — the *ISIJ 2015*
  critique is that in multicomponent steel the peritectic boundary compositions each shift, so replacing only
  ``[%C]`` by ``[%C]e`` "would not suffice". So :data:`CE_COEFFS` is a **representative low-alloy
  weighting with the thermodynamically-correct stabilizer signs**, not a pinned Wolf set — exactly the
  honest tier-2 provenance :mod:`steel.casting` uses for its ISIJ partition coefficients. The plain-carbon
  hero needs **no** coefficients; the alloying lever is the representative, directional second story.
* **The mechanism — the Fe–C peritectic lever rule (CITED invariant points, by construction).** The textbook
  metastable Fe–C peritectic: ``L(0.53) + δ(0.09) → γ(0.17)`` at **1495 °C** (the same invariant points
  :data:`steel.casting.PERITECTIC_C` names; verified against standard Fe–C data). A simple lever rule on
  these points gives the δ-ferrite present at the front (:func:`delta_fraction_above_peritectic`) and the δ
  consumed by the rapid peritectic reaction (:func:`delta_consumed_by_peritectic`) — the source of the
  contraction. This is **pure carbon mass balance** (the same construction as :mod:`steel.fe_c`'s solid-state
  lever rule), so it cannot independently "fail"; it is the physical *why* behind the FP band, drawn in the
  figure.

**NO claimable tooth, one soft cross-source COHERENCE note.** Like its siblings this build manufactures no
benchmark: the verdict is a cited classifier and the mechanism is a by-construction lever rule. The one soft
note is a **coherence**, and it is named carefully (the two are **not** independent — both rest on the same
Fe–C peritectic structure): the thermodynamic lever rule and Wolf's *empirically*-fit ferrite potential place
the trouble at **the same ~0.1 wt% C window** — the mechanism *explains why* the empirical depression band
sits where it does. It is honestly **not** "two independent constructions agree". And it is **coherent, not
identical**: the empirical FP band's low edge (``FP = 1.05`` → ``Cp = 0.08``) reaches a sliver *below* the
binary δ-onset (``Cδ = 0.09``), so a ``0.08–0.09 %C`` heat is FP-flagged while the lever rule's peritectic
reaction has not yet started (:func:`delta_consumed_by_peritectic` ``= 0`` there) — the verdict names this
incipient strip rather than over-claiming the contraction. The two readings *conflict* by ~0.01 %C at that
edge, exactly as a fitted band and a sharp invariant point should.

**Named ceiling — equilibrium lever rule, not the exact worst-carbon.** The lever "δ consumed by the
peritectic reaction" peaks at the upper band edge ``C = Cγ = 0.17``, whereas the *empirically* worst grade is
nearer ``~0.10–0.13``; the offset is honest and **not patched** with a manufactured weighting. The exact
worst-carbon and the crack itself depend on δ→γ transformation **kinetics** and **shell mechanics** (cooling
rate, mould taper, the thin-shell stress state) that an equilibrium lever rule does not carry — the result is
**underdetermined, not wrong-placed** (the same landing as :mod:`steel.temper_embrittlement`). The δ→γ
contraction *magnitude* (:data:`DELTA_GAMMA_VOLUME_CONTRACTION`) is **illustrative only** — a representative
value near the peritectic; the verdict (the FP band) does **not** depend on it. Carbon-equivalent multicomponent
shifting (ISIJ 2015), and the strain-rate / feeding driver (RDG / Clyne–Davies, illustrative in
:mod:`steel.solidification`) are referenced, not rebuilt.

Units: wt % for composition, °C for temperature; ``FP`` and the lever fractions are dimensionless.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import casting
from .heat_state import Heat, ProcessStep, add_defect
from .sweep import Steel

# --------------------------------------------------------------------------- #
# 1. CITED — the Fe–C peritectic invariant points (wt% C, °C). Standard metastable Fe–Fe₃C data,
#    verified against multiple sources; C_LIQUID is the same value casting.PERITECTIC_C already pins.
# --------------------------------------------------------------------------- #
T_PERITECTIC: float = 1495.0          # peritectic isotherm (°C)
C_DELTA_PERITECTIC: float = 0.09      # δ-ferrite carbon at the peritectic
C_GAMMA_PERITECTIC: float = 0.17      # γ-austenite carbon formed by the peritectic
C_LIQUID_PERITECTIC: float = casting.PERITECTIC_C   # 0.53 — liquid carbon at the peritectic (shared)

# --------------------------------------------------------------------------- #
# 2. CITED — Wolf's ferrite potential thresholds. FP = 2.5(0.5 − Cp); the peritectic reaction is maximal at
#    FP = 1 and the crack-susceptible "depression" band is 0.8 < FP < 1.05 (Wolf; Azizi-Thomas MMTB 51:1875 2020 review;
#    ISIJ 55:781 2015). Above the band → ferritic ("sticker") grade; below → austenitic. NOT teeth: labelled
#    classifier thresholds, like heat_state.MIN_MARTENSITE_SPEC.
# --------------------------------------------------------------------------- #
FP_REFERENCE_C: float = 0.50          # the (0.5 − %C) reference carbon in Wolf's formula
FP_SLOPE: float = 2.5                 # the 2.5 prefactor
FP_PERITECTIC_MAX: float = 1.0        # FP at maximum peritectic reaction (Cp ≈ 0.10)
FP_CRACK_LOW: float = 0.80            # below this → austenitic solidification (sticker grade)
FP_CRACK_HIGH: float = 1.05           # above this → ferritic solidification (sticker grade)

# --------------------------------------------------------------------------- #
# 3. REPRESENTATIVE (tier-2, the named ceiling) — the carbon-equivalent stabilizer weighting. Austenite
#    stabilizers (Mn, Ni, Cu, N) RAISE Cp (push toward austenitic / lower FP); ferrite stabilizers
#    (Si, Cr, Mo, Al, P) LOWER Cp (push toward ferritic / higher FP). The SIGNS are thermodynamically
#    unambiguous; the magnitudes are a representative low-alloy set (Wolf-type), NOT pinned values — the
#    literature spreads, and single-Cp substitution is itself approximate (ISIJ 2015 multicomponent critique).
#    Same honest provenance tier as casting.py's ISIJ partition coefficients. Only the elements the back-end
#    Steel carries are listed; the plain-carbon verdict uses none of them.
# --------------------------------------------------------------------------- #
CE_COEFFS: dict[str, float] = {
    "Mn": +0.04,   # austenite stabilizer (mild)
    "Ni": +0.05,   # austenite stabilizer
    "Si": -0.14,   # ferrite stabilizer
    "Cr": -0.04,   # ferrite stabilizer
    "Mo": -0.04,   # ferrite stabilizer
    "P":  -0.05,   # ferrite stabilizer
}

# --------------------------------------------------------------------------- #
# 4. ILLUSTRATIVE ONLY — the δ→γ (BCC→FCC) transformation volume contraction near the peritectic. The
#    austenite molar volume is below both δ and liquid, so the transformation contracts. ~0.4 % volumetric is
#    representative near the peritectic (the room-temperature α→γ value is larger, ~1 % volumetric / ~0.3 %
#    linear); the magnitude is for the figure / narrative ONLY — the FP-band verdict does not use it.
# --------------------------------------------------------------------------- #
DELTA_GAMMA_VOLUME_CONTRACTION: float = 0.004   # volumetric strain per unit δ transformed (representative)

# The defect flag this stage raises — the carbon-driven solidification (surface) cracking consequence.
# Distinct from hot_tear's HOT_TEAR (the sulfur film). Single-tier and grade-intrinsic: there is no separate
# upstream chemistry RISK (unlike S > 0.040 % for hot-tear) — the aim carbon of the grade IS the driver.
PERITECTIC_CRACK: str = "peritectic-crack"


# --------------------------------------------------------------------------- #
# Wolf ferrite potential + the carbon equivalent (the verdict)
# --------------------------------------------------------------------------- #
def ferrite_potential(Cp: float) -> float:
    """Wolf's ferrite potential ``FP = 2.5·(0.5 − Cp)`` for carbon equivalent ``Cp`` (wt %).

    A measure of how ferritic the *primary* solidification is: ``FP > 1.05`` ferritic, ``FP ≤ 0.8``
    austenitic, peritectic reaction maximal at ``FP = 1`` (``Cp ≈ 0.10``). Cited (Wolf).
    """
    return FP_SLOPE * (FP_REFERENCE_C - Cp)


def carbon_equivalent(comp: Steel) -> float:
    """The peritectic **carbon equivalent** ``Cp`` (wt %) — carbon plus the alloy stabilizer shift.

    ``Cp = %C + Σ CE_COEFFS[el]·%el`` over the alloying elements the grade carries. Austenite stabilizers
    raise ``Cp``, ferrite stabilizers lower it, shifting the grade into/out of the crack band at a *fixed*
    carbon (the "same C, alloying decides" lever). The coefficients are **representative** (the named
    ceiling); the **signs** are unambiguous. For a plain-carbon steel ``Cp = %C``.
    """
    shift = 0.0
    for el, coeff in CE_COEFFS.items():
        shift += coeff * getattr(comp, el)
    return comp.C + shift


def is_crack_susceptible(fp: float) -> bool:
    """Whether a ferrite potential ``fp`` lands in Wolf's crack-susceptible band ``0.8 < FP < 1.05``."""
    return FP_CRACK_LOW < fp < FP_CRACK_HIGH


# --------------------------------------------------------------------------- #
# The Fe–C peritectic lever rule (the mechanism — by construction, the figure's "why")
# --------------------------------------------------------------------------- #
def delta_fraction_above_peritectic(C: float) -> float:
    """δ-ferrite mass fraction present **just above** the peritectic isotherm (the δ + L two-phase field).

    Lever rule between ``C_δ = 0.09`` and ``C_L = 0.53``: ``f_δ = (C_L − C)/(C_L − C_δ)`` for
    ``0.09 ≤ C ≤ 0.53``; ``1.0`` below (fully δ — sub-peritectic) and ``0.0`` above (fully γ —
    super-peritectic). This is the δ that the front carries into the transformation. By construction (carbon
    mass balance).
    """
    if C <= C_DELTA_PERITECTIC:
        return 1.0
    if C >= C_LIQUID_PERITECTIC:
        return 0.0
    return (C_LIQUID_PERITECTIC - C) / (C_LIQUID_PERITECTIC - C_DELTA_PERITECTIC)


def delta_fraction_below_peritectic(C: float) -> float:
    """δ-ferrite mass fraction remaining **just below** the peritectic isotherm (after ``L + δ → γ``).

    Hypo-peritectic (``0.09 < C < 0.17``): the reaction consumes all liquid, leaving ``γ + δ`` — lever
    between ``C_δ`` and ``C_γ``: ``f_δ = (C_γ − C)/(C_γ − C_δ)``. Hyper-peritectic (``C ≥ 0.17``): the
    reaction consumes all δ → ``0.0``. Below ``C_δ``: still ``1.0`` (no liquid reacted). By construction.
    """
    if C <= C_DELTA_PERITECTIC:
        return 1.0
    if C >= C_GAMMA_PERITECTIC:
        return 0.0
    return (C_GAMMA_PERITECTIC - C) / (C_GAMMA_PERITECTIC - C_DELTA_PERITECTIC)


def delta_consumed_by_peritectic(C: float) -> float:
    """δ-ferrite consumed **by the rapid peritectic reaction** at the isotherm — the contraction source.

    ``f_δ(above) − f_δ(below)``: zero outside ``0.09 < C < 0.53`` (no peritectic reaction), rising through
    the hypo-peritectic range and **peaking at ``C = Cγ = 0.17``** (the upper band edge), then falling to
    zero at ``C_L = 0.53``. This is the high-temperature, near-isothermal δ→γ that strains the thin shell —
    *not* the slower solid-state δ→γ of the remaining ferrite below the isotherm. By construction; its peak
    is honestly at the band edge, not the empirical worst-carbon (see the module ceiling).
    """
    return delta_fraction_above_peritectic(C) - delta_fraction_below_peritectic(C)


def peritectic_contraction_strain(C: float) -> float:
    """An **illustrative** volumetric contraction proxy: δ consumed × the δ→γ volume contraction.

    ``delta_consumed_by_peritectic(C) · DELTA_GAMMA_VOLUME_CONTRACTION`` — the order-of-magnitude strain the
    rapid peritectic δ→γ imposes on the shell. Illustrative only (the verdict is the FP band); the magnitude
    rides on the representative :data:`DELTA_GAMMA_VOLUME_CONTRACTION`.
    """
    return delta_consumed_by_peritectic(C) * DELTA_GAMMA_VOLUME_CONTRACTION


def peritectic_regime(C: float) -> str:
    """Name the solidification regime by carbon (the cited Fe–C lever points): ``"sub-peritectic"`` (fully δ,
    C ≤ 0.09), ``"hypo-peritectic"`` (0.09–0.17), ``"hyper-peritectic"`` (0.17–0.53), ``"super-peritectic"``
    (fully γ, C ≥ 0.53)."""
    if C <= C_DELTA_PERITECTIC:
        return "sub-peritectic"
    if C <= C_GAMMA_PERITECTIC:
        return "hypo-peritectic"
    if C <= C_LIQUID_PERITECTIC:
        return "hyper-peritectic"
    return "super-peritectic"


@dataclass(frozen=True)
class PeritecticAssessment:
    """Whether a grade is peritectic-crack susceptible, with the FP verdict and the lever-rule mechanism.

    ``C`` the **nominal** carbon (wt %, NOT Scheil-enriched); ``Cp`` the carbon equivalent; ``fp`` Wolf's
    ferrite potential; ``crack_susceptible`` whether ``fp`` is in the cited band (the verdict); ``regime`` the
    Fe–C solidification regime; ``delta_at_peritectic`` the δ the front carries; ``delta_consumed`` the δ the
    rapid peritectic reaction transforms; ``contraction_strain`` the illustrative shell-contraction proxy.
    """

    C: float
    Cp: float
    fp: float
    crack_susceptible: bool
    regime: str
    delta_at_peritectic: float
    delta_consumed: float
    contraction_strain: float

    @property
    def verdict(self) -> str:
        """A one-line human reading (for the demo and the process trail)."""
        if self.crack_susceptible:
            if self.delta_consumed > 0.0:
                return (f"PERITECTIC-CRACK risk (FP {self.fp:.2f} in the depression band "
                        f"{FP_CRACK_LOW:.2f}–{FP_CRACK_HIGH:.2f}; {self.regime}, the δ→γ contraction "
                        f"strains the thin shell → longitudinal facial cracks)")
            # The empirical FP band reaches a sliver below the binary δ-onset (Cδ = 0.09): FP-flagged but the
            # peritectic reaction has not yet started (the band is coherent with the lever rule, NOT identical).
            return (f"PERITECTIC-CRACK risk (FP {self.fp:.2f} in the depression band "
                    f"{FP_CRACK_LOW:.2f}–{FP_CRACK_HIGH:.2f}; {self.regime} — the empirical band reaches "
                    f"just below the δ-onset Cδ = {C_DELTA_PERITECTIC:.2f}, so the reaction is only incipient)")
        side = "ferritic 'sticker'" if self.fp >= FP_CRACK_HIGH else "austenitic"
        return (f"sound surface (FP {self.fp:.2f} outside the depression band → {side} solidification, "
                f"the δ→γ contraction is not concentrated at the front)")


def peritectic_assessment(comp: Steel) -> PeritecticAssessment:
    """Resolve whether a grade is peritectic-crack susceptible — Wolf's FP band on the **nominal** chemistry.

    Computes the carbon equivalent (:func:`carbon_equivalent`) and Wolf's ferrite potential
    (:func:`ferrite_potential`), flags the cited crack band as the verdict, and attaches the Fe–C lever-rule
    mechanism (δ at the front, δ consumed by the peritectic reaction, the illustrative contraction). Reads the
    **bulk** composition — the peritectic shell phenomenon is governed by aim chemistry, never the segregated
    last liquid (the contrast with :mod:`steel.hot_tear`).
    """
    Cp = carbon_equivalent(comp)
    fp = ferrite_potential(Cp)
    return PeritecticAssessment(
        C=comp.C,
        Cp=Cp,
        fp=fp,
        crack_susceptible=is_crack_susceptible(fp),
        regime=peritectic_regime(Cp),
        delta_at_peritectic=delta_fraction_above_peritectic(Cp),
        delta_consumed=delta_consumed_by_peritectic(Cp),
        contraction_strain=peritectic_contraction_strain(Cp),
    )


def peritectic_crack_check(heat: Heat) -> Heat:
    """Read whether a casting of this ``Heat`` is peritectic-crack susceptible — the carbon-consequence seam.

    The orchestrator for the **carbon-driven** casting-cracking consequence (the sibling of
    :func:`steel.hot_tear.hot_tear_check`, which is sulfur-driven). It reads the Heat's **nominal** carbon and
    alloy content (:func:`peritectic_assessment`), and if Wolf's ferrite potential lands in the cited
    depression band raises the **peritectic-crack** flag and carries it forward. Single-tier and
    grade-intrinsic: unlike hot-tear's ``S > 0.040 %`` upstream risk, the aim carbon of the grade *is* the
    driver — there is no separate upstream chemistry flag. Returns a *new* ``Heat`` with one
    ``"peritectic-crack-check"`` :class:`~steel.heat_state.ProcessStep` appended; composition is unchanged
    (the verdict reads state).
    """
    a = peritectic_assessment(heat.composition)
    crack = a.crack_susceptible
    defects = add_defect(heat.defects, PERITECTIC_CRACK) if crack else heat.defects
    flags_added = (PERITECTIC_CRACK,) if (crack and not heat.has_defect(PERITECTIC_CRACK)) else ()
    summary = (
        f"cast: C {a.C:.3f} % (Cp {a.Cp:.3f} %) → ferrite potential FP {a.fp:.2f} "
        f"[crack band {FP_CRACK_LOW:.2f}–{FP_CRACK_HIGH:.2f}], {a.regime} → {a.verdict}"
    )
    step = ProcessStep("peritectic-crack-check", summary, in_spec=not crack, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
