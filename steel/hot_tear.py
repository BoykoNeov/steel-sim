"""Hot-tearing (solidification cracking) — the **sulfur** consequence at the *casting* stage.

The casting-stage sibling of forging-stage red-shortness (:mod:`steel.hot_work`). Both close the sulfur
consequence F2 Slice 2 (:mod:`steel.slag`) set up: slag partition *removed* sulfur and raised the
chemistry-state **``high-sulfur``** risk flag; the *consequences* of the residual ``S`` are read downstream.
Red-short reads it at the **forging reheat** (a Fe–FeS grain-boundary film in the homogenized solid). This
module reads it one stage earlier — **during solidification**, where the same sulfur does its damage as a
liquid film between the freezing dendrites, and the casting **tears** because the solidification-shrinkage /
thermal-contraction strain cannot be fed across that film. This is the §6 failure-propagation row
"under-desulfurization → hot-tear susceptibility", and the two-tier pattern of cold-short (propagation) /
red-short / hydrogen-flaking / gas-porosity: the upstream stage sets a single-axis **risk**, this sets the
mechanism-aware **consequence**.

What makes this NOT just red-short again — segregation, and the load-bearing phase + time distinction
---------------------------------------------------------------------------------------------------------
Red-short gates on the **bulk** Mn:S. Hot-tearing happens in the **last liquid to freeze**, which is
**Scheil-enriched**: solidification rejects the low-partition-coefficient solutes into the shrinking
interdendritic liquid. Sulfur (``k ≈ 0.035–0.05``) piles up there ~10–20×, while manganese (``k ≈ 0.78``)
barely concentrates (~2×) — so the **local Mn:S in the interdendritic film is roughly 10× *poorer* than the
bath**. A heat that comfortably clears the bulk MnS stoichiometry can therefore still grow a Fe–FeS film in
its last liquid and tear while casting. The lever and the fix are the same *Mushet's manganese* (more Mn →
the film stays high-melting MnS), but the **threshold is segregation-amplified**.

This is the honest, load-bearing distinction from :mod:`steel.hot_work` — **phase + time, not
homogenization**. Hot-tear reads the *transient interdendritic liquid* during freezing; red-short reads the
*bulk solid* at the later forging heat. Different phase, different time → a heat can legitimately **fail one
gate and pass the other**: castability is not forgeability. (There is no "bulk" liquid to read during
freezing — segregation is intrinsic to the mechanism, not a refinement of it.) The model uses the **liquid**
Scheil composition (:func:`steel.casting.scheil_liquid_composition`) for *both* Mn and S — never
:func:`steel.casting.centerline_enriched_composition`, which returns the depleted *solid* and would drop S
entirely.

The honest posture — a new consumer, NO strict tooth, one soft OoM-coherence note
---------------------------------------------------------------------------------
Like its siblings (hydrogen-flaking, gas-porosity, red-short), this is a **thin consumer**, named so up
front — standalone, no solver, **no engine touch, no ADR**. The map:

* **The load-bearing verdict — the segregation-amplified film Mn:S.** The interdendritic liquid Mn:S
  (Scheil, both solutes) fed to the *same* :func:`steel.slag.manganese_sulfide` balance red-short uses: free
  sulfur in the film (film Mn:S below the stoichiometric ``1.71``) ⇒ a Fe–FeS liquid film ⇒ hot-tear. The
  build's reason to exist is that this **disagrees** with the bulk reading because of segregation — a
  bulk-clear heat tears at the centerline (the demo hero), and the same centerline a casting enriches and
  over-hardens (:mod:`steel.casting`) and freezes last (:mod:`steel.solidification`) is where it tears: one
  place, now three reasons.
* **NO claimable tooth — by construction + cited inputs (the red-short / gas-porosity landing).** The verdict
  *is* the cited Scheil partition (Won & Thomas ``k``) feeding the cited MnS stoichiometry — it cannot
  independently "fail". The one soft, order-of-magnitude **coherence note** (not a tooth): the **bulk** Mn:S a
  casting needs so the *amplified* film still clears stoichiometry, :func:`critical_bulk_mn_s`, lands in the
  **tens** (≈10 at ``f_s = 0.90``, ≈15 at 0.95, ≈50 at 0.99) — reproducing, from the stoichiometric ``1.71``
  with **no tuning** (cited ``k`` only), the empirical metallurgical rule that **sound castings need Mn:S in
  the tens** (Toledo 1993: below ~20, carbon steels show intergranular embrittlement in continuous casting;
  the literature band runs ~6–36, sulfur-dependent). The **order** is robust and cutoff-insensitive; the
  *specific* value is **cutoff-tuned** (``f_s*`` is a free knob, the :data:`FS_LAST_LIQUID` default). Label it
  OoM-coherence; it is really by-construction.
* **By construction (NOT teeth):** the free-sulfur balance is :func:`steel.slag.manganese_sulfide` reused
  wholesale on the film composition (``1.71 = M_Mn/M_S``, pure stoichiometry — cannot fail); the Scheil liquid
  enrichment is :mod:`steel.casting`'s; the verdict rule itself ("free S in the last liquid ⇒ hot-tear").

**Named ceiling — this is the S-film *sub-mechanism* of hot-tearing, segregation-aware, not "the" model.**
The feeding / strain-rate driver (the RDG / Clyne–Davies cracking-susceptibility index, the freezing-range /
vulnerable mushy-span *magnitude*) is **not** rebuilt here — its illustrative form already lives in
:mod:`steel.solidification` (the late-freezing span / hot-spot read); reference it, do not duplicate it. The
**carbon-peritectic** contribution (the δ→γ contraction that makes ~0.1 %C grades the worst surface-cracking
steels in continuous casting) is a different mechanism needing δ/γ volumetric thermodynamics the repo does
not carry — a named deferral. And the stoichiometric ``1.71`` is applied to the **final** liquid ratio,
ignoring **progressive MnS precipitation** during freezing (a solubility-product calculation that would
deplete the liquid sulfur as it concentrates) — the same by-construction simplification :mod:`steel.slag`
makes, now on the segregated liquid. Units: wt % for composition.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import casting
from . import slag
from .heat_state import Heat, ProcessStep, add_defect

# --------------------------------------------------------------------------- #
# Pinned conventions & the reused thresholds — cited / by-construction inputs, NOT teeth
# --------------------------------------------------------------------------- #
# The last-to-freeze solid fraction at which the interdendritic film composition is read — reused from
# casting's centerline fraction so the two modules agree on "the last liquid". This is the cutoff f_s* below
# the Scheil f_s → 1 singularity; it is a FREE KNOB (the soft OoM note's specific value rides on it, the
# ORDER does not — see critical_bulk_mn_s). Named, not a tooth.
FS_LAST_LIQUID: float = casting.FS_CENTERLINE          # 0.95

# The stoichiometric MnS weight ratio (M_Mn/M_S ≈ 1.71) — reused wholesale from slag.py. Pure stoichiometry
# (Mushet's number); cannot come out wrong, so it is by-construction, not a tooth.
MN_S_STOICH: float = slag.MN_PER_S                     # ≈ 1.71

# Primary solidification phase whose partition coefficients drive the segregation (δ-ferrite for the low-C
# casting grades, as in casting.py). γ gives a very similar amplification (~16 vs ~14 at f_s = 0.95).
DEFAULT_PHASE: str = "delta"

# A cited reference Mn:S for the OoM-coherence note / figure ONLY — the value below which carbon steels show
# intergranular embrittlement (poor hot ductility) in continuous casting (Toledo et al., Steel Research 1993).
# The literature band is ~6–36 (sulfur-dependent); ~20 is the commonly-cited line. NOT a threshold the model
# uses — the verdict is the film Mn:S vs 1.71; this is the external anchor the amplification is checked against.
EMPIRICAL_MN_S_CASTING: float = 20.0

# The defect flag this stage raises — the solidification-cracking consequence. Distinct from slag's upstream
# high-sulfur RISK (a flat, Mn-blind / segregation-blind S line) and from hot_work's RED_SHORT (the forging
# sibling). The two-tier pattern: risk → consequence.
HOT_TEAR: str = "hot-tear"   # free S in the segregation-enriched last liquid → Fe–FeS film → casting tears


def segregation_factor(fs: float = FS_LAST_LIQUID, phase: str = DEFAULT_PHASE) -> float:
    """The factor (< 1) by which interdendritic segregation **suppresses** the last-liquid Mn:S vs the bath.

    ``(1 − f_s)^(k_Mn − k_S)`` — the ratio of the two Scheil liquid enrichments
    (``C_L/C₀ = (1 − f_s)^(k − 1)``). Because sulfur's partition coefficient is far smaller than manganese's,
    sulfur enriches in the residual liquid much faster, so the film's Mn:S is ~10× *poorer* than the bath's
    (≈0.12 at ``f_s = 0.95`` — i.e. a bulk Mn:S of 14 becomes a film Mn:S of ~1.7). By construction from the
    cited :mod:`steel.casting` partition coefficients.
    """
    k_Mn = casting.partition_coefficient("Mn", phase)
    k_S = casting.partition_coefficient("S", phase)
    return (1.0 - fs) ** (k_Mn - k_S)


def last_liquid_mn_s(
    Mn_pct: float, S_pct: float, fs: float = FS_LAST_LIQUID, phase: str = DEFAULT_PHASE
) -> tuple[float, float]:
    """The (Mn, S) of the interdendritic **liquid** film at solid fraction ``fs`` (wt %) — both Scheil-enriched.

    Uses :func:`steel.casting.scheil_liquid_composition` for *both* solutes — the film is a **liquid**
    phenomenon (sulfur piles up in the residual liquid, not the depleted solid). Returns ``(Mn_L, S_L)``;
    their ratio is the segregation-amplified film Mn:S the verdict reads.
    """
    k_Mn = casting.partition_coefficient("Mn", phase)
    k_S = casting.partition_coefficient("S", phase)
    Mn_L = casting.scheil_liquid_composition(Mn_pct, k_Mn, fs) if Mn_pct > 0.0 else 0.0
    S_L = casting.scheil_liquid_composition(S_pct, k_S, fs) if S_pct > 0.0 else 0.0
    return Mn_L, S_L


def critical_bulk_mn_s(fs: float = FS_LAST_LIQUID, phase: str = DEFAULT_PHASE) -> float:
    """The **bulk** Mn:S a casting needs so the segregation-amplified *film* Mn:S still clears stoichiometry.

    ``MN_S_STOICH / segregation_factor`` — the soft OoM-coherence note. Segregation amplifies the
    stoichiometric ``1.71`` into the **tens** (≈10 at ``f_s = 0.90``, ≈15 at 0.95, ≈50 at 0.99), reproducing
    with no tuning the empirical "sound castings need Mn:S in the tens" rule (:data:`EMPIRICAL_MN_S_CASTING`).
    The **order** is cutoff-robust; the specific value is cutoff-tuned (``f_s`` is the free knob). Really
    by-construction.
    """
    return MN_S_STOICH / segregation_factor(fs, phase)


@dataclass(frozen=True)
class HotTearAssessment:
    """Whether a casting hot-tears, given its bulk Mn/S and the segregation of the last liquid to freeze.

    ``bulk_mn_s`` the nominal Mn:S (what red-short reads; ``inf`` for a sulfur-free heat); ``bulk_forms_mns``
    whether the bath clears stoichiometry; ``last_liquid_mn`` / ``last_liquid_s`` the Scheil-enriched film
    composition (wt %); ``last_liquid_mn_s`` the segregation-amplified **film** Mn:S (the verdict driver);
    ``film_forms_mns`` whether the film clears stoichiometry; ``free_sulfur_film_pct`` the free sulfur in the
    film (in the *residual-liquid* concentration scale — a positive value is the FeS precursor, the verdict);
    ``critical_bulk_mn_s`` the bulk Mn:S needed to keep the film MnS; ``fs`` the last-liquid cutoff; ``hot_tear``
    the verdict.
    """

    bulk_mn_s: float
    bulk_forms_mns: bool
    last_liquid_mn: float
    last_liquid_s: float
    last_liquid_mn_s: float
    film_forms_mns: bool
    free_sulfur_film_pct: float
    critical_bulk_mn_s: float
    fs: float
    hot_tear: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.hot_tear:
            extra = (" — the bath clears Mn:S stoichiometry, but segregation tips the interdendritic film below it"
                     if self.bulk_forms_mns else "")
            return (f"HOT-TEAR (Fe–FeS film in the last liquid: film Mn:S {self.last_liquid_mn_s:.2f} "
                    f"< {MN_S_STOICH:.2f}{extra})")
        return (f"sound casting (the last liquid keeps Mn:S {self.last_liquid_mn_s:.2f} ≥ {MN_S_STOICH:.2f} — "
                f"sulfur stays high-melting MnS)")


def hot_tear_assessment(
    Mn_pct: float, S_pct: float, *, fs: float = FS_LAST_LIQUID, phase: str = DEFAULT_PHASE
) -> HotTearAssessment:
    """Resolve whether a casting of this ``Mn``/``S`` hot-tears — the segregation-amplified film criterion.

    Enriches the bath Mn and S into the last-to-freeze interdendritic liquid (:func:`last_liquid_mn_s`,
    Scheil), then applies the *same* :func:`steel.slag.manganese_sulfide` balance red-short uses, but **to the
    film**: free sulfur in the film (film Mn:S below the stoichiometric ``1.71``) ⇒ a Fe–FeS liquid film
    between the dendrites ⇒ hot-tear. The **bulk** balance is computed too (so the demo can show the two
    readings disagree). The temperature gate red-short carries is implicit here — the film *is* liquid (it is
    the last metal to freeze), so there is no separate "above the eutectic" condition.
    """
    bulk = slag.manganese_sulfide(Mn_pct, S_pct)
    Mn_L, S_L = last_liquid_mn_s(Mn_pct, S_pct, fs, phase)
    film = slag.manganese_sulfide(Mn_L, S_L)
    return HotTearAssessment(
        bulk_mn_s=bulk.ratio,
        bulk_forms_mns=bulk.forms_mns,
        last_liquid_mn=Mn_L,
        last_liquid_s=S_L,
        last_liquid_mn_s=film.ratio,
        film_forms_mns=film.forms_mns,
        free_sulfur_film_pct=film.free_sulfur_pct,
        critical_bulk_mn_s=critical_bulk_mn_s(fs, phase),
        fs=fs,
        hot_tear=film.free_sulfur_pct > 0.0,
    )


def hot_tear_check(heat: Heat, *, fs: float = FS_LAST_LIQUID, phase: str = DEFAULT_PHASE) -> Heat:
    """Cast the ``Heat`` and read whether it hot-tears — the casting-stage sulfur-consequence seam.

    The orchestrator that **closes the sulfur consequence at the casting stage**: it reads the Heat's bulk
    ``Mn`` and ``S`` (:func:`hot_tear_assessment`), enriches them into the last-to-freeze liquid by Scheil
    segregation, and if the film's Mn:S falls below stoichiometry (a Fe–FeS interdendritic film) raises the
    **hot-tear** flag and carries it forward — the mirror of :func:`steel.hot_work.hot_work`'s red-short seam,
    but during solidification rather than forging (the segregation-amplified, phase-and-time-distinct
    sibling). Returns a *new* ``Heat`` with one ``"hot-tear-check"`` :class:`~steel.heat_state.ProcessStep`
    appended; composition is unchanged (the verdict reads state, it does not move sulfur).
    """
    a = hot_tear_assessment(heat.composition.Mn, heat.composition.S, fs=fs, phase=phase)
    defects = add_defect(heat.defects, HOT_TEAR) if a.hot_tear else heat.defects
    flags_added = (HOT_TEAR,) if (a.hot_tear and not heat.has_defect(HOT_TEAR)) else ()
    summary = (
        f"cast: bulk Mn:S {a.bulk_mn_s:.1f}, segregation → film Mn:S {a.last_liquid_mn_s:.2f} "
        f"(a sound casting needs bulk Mn:S ≳ {a.critical_bulk_mn_s:.0f}) → {a.verdict}"
    )
    step = ProcessStep("hot-tear-check", summary, in_spec=not a.hot_tear, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
