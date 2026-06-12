"""Unified-KV competing reactions: the bainite bay, *opened* in continuous cooling (Steel §19).

This is the "6b deepening" — the one item the plan left ``[available]`` in the §11 menu.
The validated pipeline (:mod:`pathint`) models the diffusional transformation as **one**
TTT C-curve (:meth:`~steel.kinetics.CCurve.tau`, Grossmann-shifted ``M``) and labels its
product *pearlite* above ``Bs`` / *bainite* below it (the "540-split"). Phase 6b *proved*
the real **bainite bay** — the temperature window where alloying pushes ferrite/pearlite far
to the right while barely moving bainite, so a cooling path threads between them into
bainite — **cannot** be wired into that single curve (the Jominy-pinned ``M`` ≈ 8× vs the
~100× a bay needs; the carbon-flat 550 °C nose; the 8620 carbon-spread ceiling). The bay was
therefore *absent* from the continuous-cooling microstructure.

This module opens it, by racing **three separate Li/Kirkaldy–Venugopalan reactions** —
proeutectoid **ferrite** (:class:`~steel.kinetics.FerriteReaction`, ``FC``, ΔT³, ceiling
Ae3), **pearlite** (:class:`~steel.kinetics.PearliteReaction`, ``PC``, ΔT³, ceiling Ae1) and
**bainite** (:class:`~steel.kinetics.BainiteReaction`, ``BC``, ΔT¹, ceiling Bs) — as one
**competing-reaction system** sharing a single austenite pool along a cooling path, with
ferrite **carbon enrichment** feeding back into the martensite split. It is **opt-in and
parallel** to the validated single-curve pipeline, which stays **byte-identical**: nothing
here touches :meth:`CCurve.tau` / :mod:`pathint` / the four-curves / Jominy benchmarks.

Why this is a *demonstrator*, not a *predictor* (the load-bearing scope decision)
--------------------------------------------------------------------------------
The 2026-06-10 bainite-anchoring probe (banked in :mod:`austemper`) settled the epistemics,
and the cited coefficients confirm them arithmetically:

* **Ferrite/pearlite differentials are cited-and-RIGHT** → they open the bay, and they are
  the **teeth**. Scale-free cited ratios: ``PC(4340)/PC(1080) ≈ 1.4e3`` (≈ the atlas-measured
  ~10³× pearlite retardation) and ``FC(4340)/FC(1045) ≈ 2.1e2``. Both *predict* the bay
  separation from the published coefficients, with no fitting.
* **Bainite's differential is cited-and-WRONG** → ``BC(4340)/BC(1080) ≈ 0.146`` says 4340
  bainite is ~7× *faster* than 1080; the atlas measures it ~4–5× *slower*. ``BC``'s carbon
  coefficient (10.18) is **directionally** wrong — no global scale fixes a wrong-direction
  prediction. So bainite carries a **per-steel atlas-anchored scale** (reused verbatim from
  :func:`~steel.austemper.anchored_reaction`); ``BC`` is never used for absolute cross-steel
  times.

Hence this is a **per-steel-anchored CCT demonstrator** scoped to the two atlas steels
(**1080**, **4340**). Cross-steel bainite prediction is *not* attempted: the **8620
carbon-spread ceiling** (Phase 6b) returns the instant cross-steel is claimed, and is named
as the wall. (For *any* composition, the validated single-curve :mod:`pathint` remains the
workhorse — this view is the mechanism-deepening lens, not its replacement.)

The per-steel time-base assembly (the honest scale split)
---------------------------------------------------------
* **Ferrite** — Phase 6a's one **global** ``FERRITE_KINETIC_SCALE = 8.0`` (validated, keeps a
  0.2 %C 8620 core in band; ``FC`` is right-direction). Reused, not re-tuned.
* **Pearlite** — one **global** scale :data:`PEARLITE_SCALE`, *derived at import* so the 1080
  pearlite-reaction nose reproduces the frozen single-curve ~550 °C / ~1 s nose (consistency
  with the four-curves anchor → not a free knob). 4340's deep pearlite nose is then
  **predicted** from the cited ``PC`` ratio with no 4340 tuning — the teeth.
* **Bainite** — the **per-steel atlas-anchored** scale (:data:`~steel.austemper.ANCHORED_SCALES`,
  1080 ≈ 6.8e3 / 4340 ≈ 165; the ×~40 gap *is* the cross-composition wall). The absolute
  bainite time is by-construction-anchored (the wall), not teeth.

Named scope edges (each a real limit, several inherited from austemper)
-----------------------------------------------------------------------
* **CCT-source gap.** The US Steel atlas is *isothermal*. "Realised in CCT" means **emergent
  from the per-steel-anchored IT curves bridged by the frozen Scheil additivity** (the
  fictitious-time competition below), **not** validated against a measured CCT diagram (we do
  not have one). No CCT benchmark is implied — the bay opening is a *demonstration*.
* **Carbon enrichment is first-order.** Proeutectoid ferrite rejects carbon into the
  remaining austenite (lever rule), enriching it toward the eutectoid — captured in the
  **final martensite split** (``Mₛ`` from the enriched austenite carbon, the physically right
  direction: more ferrite ⇒ lower ``Mₛ`` ⇒ more retained γ). The **diffusional reaction
  kinetics** (``FC``/``PC``/``BC`` factors, the ``Bs`` ceiling) keep the **bulk-composition**
  cited values — re-deriving them at the live austenite carbon every step has no atlas/citation
  support, and enrichment is small in the bay regime (a path fast enough to land bainite forms
  little ferrite). Named, not hidden.
* **Bainite hardness** stays the carbon-only placeholder (:func:`~steel.properties.vickers_bainite`),
  load-bearing here as in :mod:`austemper` — under-ranks alloyed bainite. Microstructure, not
  hardness, is the headline.
* Inherited austemper edges: claims at the 50 % line; near-Mₛ acceleration unmodeled; the model
  nose runs a little high.

Units: °C, seconds, wt%, mass fractions in [0, 1] — matching :mod:`kinetics`/:mod:`pathint`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import austemper, fe_c
from .kinetics import (
    CCurve, FerriteReaction, PearliteReaction, BainiteReaction,
    ferrite_reaction_for_steel, pearlite_reaction_for_steel,
    andrews_Ms, koistinen_marburger,
)

# --------------------------------------------------------------------------- #
# 1. The pearlite global scale — derived at import against the frozen 1080 nose
# --------------------------------------------------------------------------- #
# The fraction the pearlite/ferrite *start* line is read at (the consistency target is the
# frozen single-curve START nose ≈ 550 °C / 1 s, the four-curves anchor).
NOSE_X = 0.01
# Representative ferrite carbon (max α solubility ≈ 0.022 wt%); the carbon ferrite rejects.
FERRITE_CARBON = 0.02


def _derive_pearlite_scale() -> float:
    """The global pearlite scale that puts the 1080 pearlite-reaction nose on the frozen nose.

    The frozen single-curve reference is :class:`~steel.kinetics.CCurve` (the carbon-only
    eutectoid that bakes in 1080's ~0.7 % Mn — the four-curves demo default), nose ≈ 550 °C /
    ~1 s at :data:`NOSE_X`. The pearlite reaction's nose time scales as ``1/scale``, so the
    anchored scale is the exact ratio ``t_nose(scale=1) / t_target``. Derived, never stored
    (the :mod:`austemper` "no magic number" discipline) — the cited inputs are the frozen nose
    and the Li/KV pearlite rate form, both already in the codebase.
    """
    _, t_target = CCurve().nose(X=NOSE_X)
    comp_1080 = austemper.ATLAS_STEELS["1080"].comp
    _, t_unit = pearlite_reaction_for_steel(**comp_1080, scale=1.0).nose(X=NOSE_X)
    return t_unit / t_target


# Derived at import: ≈ 0.50. The single calibrated global knob (PC's right-direction alloy
# dependence makes one global scale honest, cf. 6a's ferrite — unlike bainite's wrong-signed BC).
PEARLITE_SCALE = _derive_pearlite_scale()


# --------------------------------------------------------------------------- #
# 2. The per-steel competing-reaction system (ferrite + pearlite + bainite)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class UnifiedSystem:
    """The three atlas-anchored Li/KV reactions for one steel + the shared-pool bookkeeping caps.

    Built by :func:`unified_system` for a named atlas steel (``"1080"`` / ``"4340"``). Carries
    the three reaction objects (each with its honest per-steel time-base: ferrite global,
    pearlite global-derived, bainite atlas-anchored), the equilibrium proeutectoid-ferrite cap
    ``f_pro`` (from :func:`~steel.fe_c.equilibrium_constituents`, 0 for eutectoid 1080 → ferrite
    inert), the bulk martensite-start ``Ms`` and the composition ``comp``. :func:`transform_competing`
    races them along a cooling path.
    """

    steel: str
    comp: dict
    ferrite: FerriteReaction
    pearlite: PearliteReaction
    bainite: BainiteReaction
    f_pro: float
    Ms: float

    @property
    def Bs(self) -> float:
        """The (bulk-composition) bainite-start ceiling — Steven–Haynes via the anchored reaction."""
        return self.bainite.Bs

    @property
    def Ae3(self) -> float:
        """The proeutectoid-ferrite ceiling (alloy-aware Andrews Ae3) via the ferrite reaction."""
        return self.ferrite.Ae3


def unified_system(steel: str) -> UnifiedSystem:
    """Assemble the :class:`UnifiedSystem` for a named atlas-anchored steel (``"1080"``/``"4340"``).

    * **ferrite** — :func:`~steel.kinetics.ferrite_reaction_for_steel` (global 6a scale 8.0).
    * **pearlite** — :func:`~steel.kinetics.pearlite_reaction_for_steel` at :data:`PEARLITE_SCALE`
      (the 1080-nose-derived global scale).
    * **bainite** — :func:`~steel.austemper.anchored_reaction` (the per-steel atlas anchor — the
      cited absolute time-base; the cross-steel wall lives in its ×~40 scale gap).

    Refuses an unanchored steel with ``ValueError`` (only the atlas steels have the cited bainite
    anchor — the named scope, the 8620/cross-comp wall).
    """
    if steel not in austemper.ATLAS_STEELS:
        raise ValueError(
            f"no atlas anchor for steel {steel!r} — unified-KV is a per-steel demonstrator, "
            f"anchored: {sorted(austemper.ATLAS_STEELS)} (cross-steel is the 8620 wall, §6b)")
    comp = dict(austemper.ATLAS_STEELS[steel].comp)
    G = austemper.ATLAS_STEELS[steel].G
    cons = fe_c.equilibrium_constituents(comp["C"])
    f_pro = cons.f_proeutectoid if cons.proeutectoid == "ferrite" else 0.0
    return UnifiedSystem(
        steel=steel,
        comp=comp,
        ferrite=ferrite_reaction_for_steel(**comp, G=G),
        pearlite=pearlite_reaction_for_steel(**comp, G=G, scale=PEARLITE_SCALE),
        bainite=austemper.anchored_reaction(steel),
        f_pro=f_pro,
        Ms=andrews_Ms(**comp),
    )


# --------------------------------------------------------------------------- #
# 3. The competing integrator — three reactions, one austenite pool, along a path
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class UnifiedResult:
    """The microstructure the competing-reaction system produces (mass fractions summing to 1).

    The same stable five-key product set :mod:`pathint`/:mod:`austemper` emit (so
    :func:`~steel.properties.hardness_HV` consumes it unchanged): ``ferrite`` (proeutectoid α,
    capped at ``f_pro``), ``pearlite`` and ``bainite`` (the two diffusional competitors that
    shared the austenite pool), ``martensite``/``retained_austenite`` (the athermal fate of the
    austenite that survived to ``Mₛ``, with ``Mₛ`` from the **carbon-enriched** austenite). ``X_diffusional``
    is the diffusional total; ``T_min`` the lowest temperature reached; ``C_gamma`` the final
    austenite carbon (enriched above ``C0`` by the ferrite that formed). ``t``/``T`` are the path
    and ``m_*`` the cumulative mass histories — for the mechanism view / demo, not validation scalars.
    """

    steel: str
    ferrite: float
    pearlite: float
    bainite: float
    martensite: float
    retained_austenite: float
    X_diffusional: float
    T_min: float
    C_gamma: float
    Ms_effective: float
    t: np.ndarray
    T: np.ndarray
    m_ferrite: np.ndarray
    m_pearlite: np.ndarray
    m_bainite: np.ndarray

    def fractions(self) -> dict:
        """The product fractions as a dict — the stable five-key currency (:mod:`pathint` idiom)."""
        return {
            "ferrite": self.ferrite,
            "pearlite": self.pearlite,
            "bainite": self.bainite,
            "martensite": self.martensite,
            "retained_austenite": self.retained_austenite,
        }

    def dominant(self) -> str:
        """Name of the largest-fraction product — the headline microstructure."""
        return max(self.fractions().items(), key=lambda kv: kv[1])[0]


def transform_competing(t: np.ndarray, T: np.ndarray, system: UnifiedSystem) -> UnifiedResult:
    """Race the three KV reactions along a cooling path ``(t, T)`` — the unified-KV core (§19).

    At each step ``(T, dt)`` the active reactions (ceiling-permitting, above ``Mₛ``) advance their
    own site-saturation completion ``U_r ← U_r + K_r(T)·g(U_r)·dt`` and convert a slice of the
    **shared remaining austenite** ``γ = 1 − m_f − m_p − m_b``:

    * **Ferrite** (``T < Ae3`` and ``m_f < f_pro``): ``dm_f = ΔU_f · f_pro`` (capped at the
      equilibrium proeutectoid fraction and the pool). It forms *first and hottest*, rejecting
      carbon into the austenite (lever-rule enrichment toward the eutectoid — captured in the
      final ``Mₛ``).
    * **Pearlite** (``T < Ae1``) and **bainite** (``T < Bs``): each proposes ``dm_r = ΔU_r · γ``
      from the **current** pool; if together they exceed ``γ`` they are scaled to fit (so the pool
      never goes negative). The faster reaction at this ``T`` wins the larger slice — *that* is the
      competition, and where alloying's ``PC ≫ BC`` retardation opens the bay (pearlite starved in
      the bay, bainite fed).

    The austenite still untransformed when the path bottoms out shears to **martensite** per
    Koistinen–Marburger at ``T_min``, using ``Mₛ`` from the **enriched** austenite carbon (more
    ferrite ⇒ lower ``Mₛ`` ⇒ more retained γ); the rest stays retained. Product fractions sum to 1
    by construction.
    """
    t = np.asarray(t, dtype=float)
    T = np.asarray(T, dtype=float)
    if t.shape != T.shape or t.ndim != 1:
        raise ValueError("t and T must be 1-D arrays of equal length")

    fr, pr, br = system.ferrite, system.pearlite, system.bainite
    f_pro, Ms_bulk = system.f_pro, system.Ms
    Ae3, Ae1, Bs = fr.Ae3, pr.Ae1, br.Bs
    C0 = system.comp["C"]

    U_f = U_p = U_b = 0.0
    m_f = m_p = m_b = 0.0
    m_ferrite = np.zeros_like(t)
    m_pearlite = np.zeros_like(t)
    m_bainite = np.zeros_like(t)

    for i in range(1, t.size):
        dt = t[i] - t[i - 1]
        Ti = float(T[i])
        if Ti > Ms_bulk:                       # diffusional window (below Mₛ the athermal shear governs)
            # Ferrite — forms first/hottest, capped at the equilibrium proeutectoid fraction.
            gamma = 1.0 - m_f - m_p - m_b
            if Ti < Ae3 and m_f < f_pro and gamma > 0.0:
                U_f_new = fr.completion_step(U_f, Ti, dt)
                dm_f = min((U_f_new - U_f) * f_pro, f_pro - m_f, gamma)
                m_f += max(0.0, dm_f)
                U_f = U_f_new
            # Pearlite vs bainite — compete for the *current* remaining austenite pool.
            gamma = 1.0 - m_f - m_p - m_b
            if gamma > 0.0:
                U_p_new = pr.completion_step(U_p, Ti, dt) if Ti < Ae1 else U_p
                U_b_new = br.completion_step(U_b, Ti, dt) if Ti < Bs else U_b
                dm_p = max(0.0, U_p_new - U_p) * gamma
                dm_b = max(0.0, U_b_new - U_b) * gamma
                total = dm_p + dm_b
                if total > gamma and total > 0.0:     # clip both to the shared pool
                    scale = gamma / total
                    dm_p *= scale
                    dm_b *= scale
                m_p += dm_p
                m_b += dm_b
                U_p, U_b = U_p_new, U_b_new
        m_ferrite[i] = m_f
        m_pearlite[i] = m_p
        m_bainite[i] = m_b

    # Carbon enrichment (lever rule): the austenite the ferrite left is enriched toward the
    # eutectoid; its Mₛ governs the final athermal split. (Bulk minors unchanged.)
    C_gamma = (C0 - m_f * FERRITE_CARBON) / (1.0 - m_f) if m_f < 1.0 else C0
    minors = {el: wt for el, wt in system.comp.items() if el != "C"}
    Ms_eff = andrews_Ms(C=C_gamma, **minors)

    T_min = float(np.min(T))
    f_km = koistinen_marburger(T_min, Ms_eff)        # 0 if the path never reaches the (enriched) Mₛ
    remainder = 1.0 - m_f - m_p - m_b
    martensite = remainder * f_km
    retained = remainder * (1.0 - f_km)

    return UnifiedResult(
        steel=system.steel,
        ferrite=m_f, pearlite=m_p, bainite=m_b,
        martensite=martensite, retained_austenite=retained,
        X_diffusional=m_f + m_p + m_b,
        T_min=T_min, C_gamma=C_gamma, Ms_effective=Ms_eff,
        t=t, T=T,
        m_ferrite=m_ferrite, m_pearlite=m_pearlite, m_bainite=m_bainite,
    )


def competing_microstructure(steel: str, t: np.ndarray, T: np.ndarray) -> UnifiedResult:
    """Convenience: assemble the system for ``steel`` and race a cooling path ``(t, T)``.

    ``transform_competing(t, T, unified_system(steel))`` in one call — the entry point the demo
    and the notebook/app sections use for a named atlas steel (``"1080"`` / ``"4340"``).
    """
    return transform_competing(t, T, unified_system(steel))
