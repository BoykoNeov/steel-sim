"""MnS inclusion morphology — the **signed sulfur foil**: the same manganese sulfide, good *and* bad.

The worked-product (rolled / forged bar / plate) sibling of forging-stage red-shortness
(:mod:`steel.hot_work`). Both read the residual sulfur after a working operation; red-short reads the
**free** sulfur Mn failed to tie up (the embrittling Fe–FeS film). This module reads the **tied** sulfur —
the MnS that *did* form — because that benign-looking sulfide is itself **signed**: the same MnS is a
deliberate asset and an unintended liability, and which one you get is set by **how much** there is and
**what shape** it takes.

* **The good — free-machining (the "good impurity").** Soft MnS inclusions break the chip and lubricate the
  tool, so a steel with enough of them machines far faster. This is *why* the resulfurized **11xx** grades
  exist: sulfur is added **on purpose** (S ≈ 0.08–0.33 %, far over the structural 0.040 % line) to make a
  free-cutting steel. The benefit rises with the **MnS volume fraction**.
* **The bad — through-thickness toughness anisotropy.** Hot working **elongates** the (plastic) MnS into
  ribbons / stringers aligned with the rolling direction. A crack loaded **across** those ribbons (the
  short-transverse / through-thickness direction) runs along the weak inclusion–matrix interfaces, so
  **short-transverse toughness and ductility drop** while the longitudinal values barely move. The debit
  rises with the **same MnS volume fraction** — but only when the sulfides are **elongated**.

The lever that separates the two is **sulfide shape control**: a small calcium (or rare-earth / tellurium)
treatment makes the MnS **globular** instead of plastic, so it does *not* stringer out on rolling. Globular
MnS keeps the machining benefit (the volume is still there) while removing the directional debit — the
classic "Ca-treat the free-machining plate" fix. Low sulfur is the other end of the trade: superb toughness,
but no MnS to break the chip.

The two-tier seam — disambiguating an already-firing risk, NOT echoing it (the load-bearing design call)
-------------------------------------------------------------------------------------------------------
Slag (:mod:`steel.slag`) raises a single, flat **``high-sulfur``** risk at ``S > 0.040 %`` — and its own
comment notes "free-machining grades run higher", so **that risk fires on every 11xx grade by design.** This
module therefore must **not** gate its consequence on a sulfur threshold: doing so would just re-derive
red-shortness and brand every free-cutting steel "defective" for being what it is. Instead the **anisotropy**
consequence is gated on **morphology** (elongated, not shape-controlled) — so the *same* high-sulfur state
reads as the intended free-machining asset when the MnS is globular and as a through-thickness liability only
when it is left elongated. The build's whole reason to exist is to **split** the flat ``high-sulfur`` flag
into its good and bad halves, not to repeat it.

The honest posture — a thin consumer, NO claimable tooth (the red-short / hot-tear landing)
-------------------------------------------------------------------------------------------
Like its siblings, this is a **thin consumer**, standalone — no solver, **no engine touch, no ADR**. The map:

* **By construction (NOT teeth).** The MnS amount is :func:`steel.slag.manganese_sulfide`'s ``mns_pct`` reused
  wholesale (Mushet stoichiometry, cannot fail); its conversion to a **volume fraction** is the cited
  density ratio (ρ_MnS ≈ 4.0 vs ρ_steel ≈ 7.87 g/cm³) — arithmetic. The verdict rules (free-machining when
  the MnS volume clears a labelled floor; anisotropic when elongated MnS pulls the short-transverse toughness
  below a labelled acceptance line) are by-construction ``if`` rules, like ``MIN_MARTENSITE_SPEC``.
* **The pedagogical point is by construction, NOT a coherence note.** "One MnS, two opposite-signed
  consequences" is the teaching beat — but it is simply one number (the MnS volume fraction) fed to two laws
  with opposite signs. It is **not** two independent constructions agreeing on anything; it cannot "come out
  wrong", so it is not dressed as a tooth or a coherence note.
* **The machinability index is REPRESENTATIVE, ranking / order-of-magnitude only — and confounded.** Real
  machinability rating (AISI %, B1112 = 100) is a multi-factor index: it also falls with **hardness / carbon**
  (a higher-carbon resulfurized grade can machine *worse* than a lower-carbon plain one despite carrying more
  MnS) and rises with **other** free-machining additions (Pb, Bi, Te, Ca). This index models the **MnS
  contribution only**; it is a relative, monotone stand-in, **not** the AISI rating, and "more MnS volume →
  more free-machining" is the only claim — a representative direction, never a benchmarked curve.
* **The transverse-toughness debit is its OWN axis.** It is **not** :func:`steel.properties.toughness_index`
  (a hardness-based strength/toughness-trade-off proxy) nor :mod:`steel.grain`'s DBTT — it is a *third*,
  directional (short-transverse vs longitudinal) toughness reduction from inclusion stringers, computed here
  and used nowhere else. It does not move the other two.

**Named ceiling.** The stringer **aspect ratio** scales with the rolling reduction (more reduction → longer
ribbons → a steeper debit) — not modelled; the elongated/globular toggle is a **two-state stand-in** for that
continuous shape-control spectrum. The debit assumes **through-thickness / short-transverse loading** (the
direction the stringers weaken); longitudinal properties are taken unaffected. MnS is singled out because it
is **plastic** at rolling temperature and so elongates, where rigid oxides (alumina) stay roughly spherical —
that distinction is narrative, not resolved. And the MnS amount is the final tied sulfide (slag's
by-construction simplification), ignoring precipitation sequence. The manganese tied up as MnS is **not**
subtracted from the hardenability manganese — the back end still hardens on the *total* ``Mn`` (the same
total-composition convention :mod:`steel.hot_work` / :mod:`steel.hot_tear` keep); a free-machining heat's bound
Mn is a real but unmodelled debit to its hardenability. Units: wt % for composition, vol % for the inclusion
fraction.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import slag
from .heat_state import Heat, ProcessStep, add_defect

# --------------------------------------------------------------------------- #
# Cited densities (by-construction INPUTS, not teeth) — wt % MnS → volume fraction
# --------------------------------------------------------------------------- #
# MnS (alabandite) ≈ 4.0 g/cm³; steel ≈ 7.87 g/cm³. The lighter sulfide occupies a *larger* volume fraction
# than its weight fraction — the relevant quantity for "how much of the section is inclusion". Pure arithmetic.
RHO_MNS: float = 4.0
RHO_STEEL: float = 7.87

# --------------------------------------------------------------------------- #
# Labelled thresholds & representative slopes (NOT teeth — named so)
# --------------------------------------------------------------------------- #
# The MnS volume fraction (vol %) above which the sulfide is a useful chip-breaker — the free-machining floor.
# A labelled line (like MIN_MARTENSITE_SPEC), not a benchmark: plain steels (S ≈ 0.02 %) sit ~0.1 vol % and do
# not free-machine; resulfurized 11xx grades (S ≈ 0.1–0.3 %) clear ~0.5–1.5 vol % and do.
FREE_MACHINING_MIN_VOLPCT: float = 0.30
# Relative machinability gain per vol % MnS — REPRESENTATIVE (the MnS contribution only; hardness/carbon/Pb
# confound the real AISI rating, see the module docstring). Index = 1 (no MnS) + this × vol %.
MACHINING_GAIN_PER_VOLPCT: float = 0.55
# Short-transverse toughness lost per vol % of *elongated* MnS — REPRESENTATIVE debit slope. The directional
# anisotropy: globular MnS (shape-controlled) carries no elongation, so no debit.
ANISOTROPY_SLOPE_PER_VOLPCT: float = 0.45
# The labelled short-transverse / through-thickness toughness acceptance line: below this fraction of the
# longitudinal toughness, a through-thickness-loaded product is off-spec. A labelled spec, not a benchmark.
MIN_TRANSVERSE_RATIO_SPEC: float = 0.50
# The smallest transverse ratio the representative debit is allowed to report (a severe stringer field does
# not reach zero toughness). A clamp, named.
MIN_TRANSVERSE_RATIO: float = 0.05

# The elongation multiplier set by sulfide shape: 1.0 as-rolled (plastic MnS stringers), 0.0 shape-controlled
# (globular MnS — Ca / rare-earth / Te treatment). The two-state stand-in for the continuous shape spectrum.
ELONGATED: float = 1.0
GLOBULAR: float = 0.0

# The defect flag this stage raises — the through-thickness (short-transverse) toughness debit from elongated
# MnS stringers. Distinct from slag's flat high-sulfur RISK and from hot_work's RED_SHORT (free-sulfur film).
# Free-machining is a *benefit*, not a defect, so it raises no flag — only the anisotropy does.
SULFIDE_ANISOTROPY: str = "sulfide-anisotropy"   # elongated MnS stringers → short-transverse toughness debit


def mns_volume_fraction(mns_pct: float) -> float:
    """Convert MnS **weight** percent (slag's ``mns_pct``) to a **volume** percent (the inclusion fraction).

    ``f_v = (w/ρ_MnS) / (w/ρ_MnS + (1−w)/ρ_steel)`` with ``w = mns_pct/100`` — the lighter sulfide takes up a
    larger volume than weight fraction. Returned in **vol %**. By construction (cited densities); not a tooth.
    """
    w = max(0.0, mns_pct) / 100.0
    if w <= 0.0:
        return 0.0
    v_mns = w / RHO_MNS
    v_steel = (1.0 - w) / RHO_STEEL
    return 100.0 * v_mns / (v_mns + v_steel)


def _machinability_from_volpct(f_v_pct: float) -> float:
    """Relative machinability index from the MnS volume fraction — REPRESENTATIVE (MnS contribution only)."""
    return 1.0 + MACHINING_GAIN_PER_VOLPCT * max(0.0, f_v_pct)


def _transverse_ratio_from_volpct(f_v_pct: float, elongation: float) -> float:
    """Short-transverse / longitudinal toughness ratio from MnS volume fraction × elongation — representative."""
    ratio = 1.0 - ANISOTROPY_SLOPE_PER_VOLPCT * max(0.0, f_v_pct) * elongation
    return max(MIN_TRANSVERSE_RATIO, min(1.0, ratio))


def machinability_index(Mn_pct: float, S_pct: float) -> float:
    """Relative machinability index of this ``Mn``/``S`` steel — the free-machining (good-impurity) reading.

    Reuses :func:`steel.slag.manganese_sulfide` for the MnS that forms, converts it to a volume fraction
    (:func:`mns_volume_fraction`), and scales a **representative** monotone index off it (1.0 = no MnS). This
    is the **MnS contribution only** — the real AISI rating is confounded by hardness/carbon and by other
    free-machining additions (see the module docstring). Ranking / order-of-magnitude, not a benchmark.
    """
    f_v = mns_volume_fraction(slag.manganese_sulfide(Mn_pct, S_pct).mns_pct)
    return _machinability_from_volpct(f_v)


def transverse_toughness_ratio(Mn_pct: float, S_pct: float, *, shape_controlled: bool = False) -> float:
    """Short-transverse toughness as a fraction of the longitudinal — the anisotropy (bad-impurity) reading.

    The *third*, directional toughness axis (NOT :func:`steel.properties.toughness_index`, NOT a DBTT): MnS
    stringers, elongated by rolling, weaken the through-thickness direction. ``1.0`` (isotropic) when there is
    no MnS **or** the sulfides are **globular** (``shape_controlled=True``); it falls with the MnS volume
    fraction when the MnS is left **elongated**. Representative debit slope, clamped.
    """
    f_v = mns_volume_fraction(slag.manganese_sulfide(Mn_pct, S_pct).mns_pct)
    elongation = GLOBULAR if shape_controlled else ELONGATED
    return _transverse_ratio_from_volpct(f_v, elongation)


@dataclass(frozen=True)
class SulfideMorphology:
    """The signed-sulfur verdict — the same MnS read as a machining asset and a through-thickness liability.

    ``mns_pct`` the MnS formed (wt %, from :func:`slag.manganese_sulfide`); ``mns_volume_fraction`` its volume
    fraction (vol %); ``shape_controlled`` whether the MnS was globularized (Ca / RE / Te); ``machinability_index``
    the representative free-machining index (1.0 = no MnS); ``free_machining`` whether the MnS volume clears the
    chip-breaker floor (the good half); ``transverse_ratio`` short-transverse / longitudinal toughness;
    ``anisotropic`` the verdict — elongated MnS pulled the short-transverse toughness below the acceptance line
    (the bad half, the defect).
    """

    mns_pct: float
    mns_volume_fraction: float
    shape_controlled: bool
    machinability_index: float
    free_machining: bool
    transverse_ratio: float
    anisotropic: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        good = (f"free-machining (MnS {self.mns_volume_fraction:.2f} vol %, "
                f"machinability ×{self.machinability_index:.2f})" if self.free_machining
                else f"not free-machining (only {self.mns_volume_fraction:.2f} vol % MnS — too little to break the chip)")
        if self.anisotropic:
            return (f"{good}, but ANISOTROPIC (elongated MnS → short-transverse toughness "
                    f"{self.transverse_ratio:.0%} of longitudinal, below the {MIN_TRANSVERSE_RATIO_SPEC:.0%} line)")
        if self.shape_controlled and self.free_machining:
            return f"{good}, and isotropic (shape-controlled — globular MnS keeps the benefit without the debit)"
        return f"{good}, isotropic (short-transverse toughness {self.transverse_ratio:.0%} of longitudinal)"


def sulfide_morphology_assessment(
    Mn_pct: float, S_pct: float, *, shape_controlled: bool = False
) -> SulfideMorphology:
    """Resolve the signed-sulfur reading for this ``Mn``/``S`` and sulfide shape (the physics).

    Reuses :func:`slag.manganese_sulfide` for the MnS that forms, converts it to a volume fraction, and reads
    both halves off that **one** quantity: the free-machining benefit (volume above the chip-breaker floor) and
    the through-thickness anisotropy (elongated MnS pulling the short-transverse toughness below the acceptance
    line). ``shape_controlled=True`` (globular MnS) keeps the benefit but removes the elongation, so the
    anisotropy clears — the sulfide-shape-control lever.
    """
    balance = slag.manganese_sulfide(Mn_pct, S_pct)
    f_v = mns_volume_fraction(balance.mns_pct)
    elongation = GLOBULAR if shape_controlled else ELONGATED
    transverse = _transverse_ratio_from_volpct(f_v, elongation)
    return SulfideMorphology(
        mns_pct=balance.mns_pct,
        mns_volume_fraction=f_v,
        shape_controlled=shape_controlled,
        machinability_index=_machinability_from_volpct(f_v),
        free_machining=f_v >= FREE_MACHINING_MIN_VOLPCT,
        transverse_ratio=transverse,
        anisotropic=(not shape_controlled) and transverse < MIN_TRANSVERSE_RATIO_SPEC,
    )


def sulfide_morphology_check(heat: Heat, *, shape_controlled: bool = False) -> Heat:
    """Work the ``Heat`` to product form and read its MnS morphology — the signed-sulfur seam.

    The orchestrator (the mirror of :func:`steel.hot_work.hot_work`, but for the *tied* sulfide rather than the
    free): it reads the Heat's ``Mn`` and ``S`` (:func:`sulfide_morphology_assessment`), reports the
    free-machining benefit, and — if the MnS is left **elongated** and its stringers pull the short-transverse
    toughness below the acceptance line — raises the **sulfide-anisotropy** defect flag and carries it forward.
    Free-machining is a *benefit*, so it raises **no** flag; only the anisotropy does, and it is gated on
    **morphology**, never on the sulfur level (which slag already flags). Returns a *new* ``Heat`` with one
    ``"sulfide-morphology"`` :class:`~steel.heat_state.ProcessStep` appended; composition is unchanged (the
    verdict reads state, it does not move sulfur).
    """
    a = sulfide_morphology_assessment(heat.composition.Mn, heat.composition.S, shape_controlled=shape_controlled)
    defects = add_defect(heat.defects, SULFIDE_ANISOTROPY) if a.anisotropic else heat.defects
    flags_added = (SULFIDE_ANISOTROPY,) if (a.anisotropic and not heat.has_defect(SULFIDE_ANISOTROPY)) else ()
    shape = "globular (shape-controlled)" if shape_controlled else "elongated (as-rolled)"
    summary = f"work to product, MnS {shape}: {a.verdict}"
    step = ProcessStep("sulfide-morphology", summary, in_spec=not a.anisotropic, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
