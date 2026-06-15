"""Inverse design / recipe selection — *target a property, get a recipe* (Steel plan §11.4 → Phase 7).

Every other surface runs the forward model (*composition × quench × temper → hardness*); this one
**inverts** it. Given a hardness spec for a section of a given size, it searches the real-grade ×
quench × temper space for recipes that meet it — the engineer's actual question ("what steel and
heat treatment gives me 45 HRC at this size, and which is cheapest?").

What this is — and what it is *not* (the :mod:`sweep` posture, inherited)
------------------------------------------------------------------------
Like :mod:`sweep`, this is **pure re-composition of already-validated modules** — it invents **no
physics and no calibrated constant**. So, exactly as ``sweep.py``, it carries **no validation triad
of its own**; its tests (``tests/test_design.py``) check *harness/solver correctness*, not metallurgy.
The forward model is the ground truth; the inverse's only job is to invert it faithfully and to
**say "infeasible" honestly** when a target is outside the achievable envelope.

The shape of the inverse: outer enumeration × inner root-find
-------------------------------------------------------------
* **Outer (discrete, enumerated):** grade ∈ :data:`~steel.sweep.STEELS` × quench medium, at a
  **given** section ``diameter`` (the part geometry is a *constraint*, not a swept axis). Staying on
  the registry of **real** grades is the non-circularity win, not a limitation: a continuous-
  composition optimiser would wander into the ``Mn = 0`` "leaner-hypothetical" steels
  :func:`~steel.kinetics.ccurve_for_steel` warns about and no benchmark covers. This is **recipe
  selection / what-if inversion**, not "optimisation over composition space".
* **Inner (continuous, root-found):** the temper axis is the *one genuinely invertible core*.
  :func:`~steel.properties.tempered_hardness_HV` tempers a phase *mixture* per-constituent — only the
  martensite leg softens (down the Hollomon–Jaffe curve), the diffusional legs are inert — so it stays
  strictly monotone-decreasing in temper ``T`` with achievable range ``[floor, as-quenched]``, and
  "what temper ``T`` hits the target?" has a **unique** solution, found by **bisection over the public
  forward function** (so this module stays decoupled from the master-curve's internal shape, inverting
  whatever the mixture is). The temper branch fires for a **martensite-dominant, retained-austenite-
  capped** candidate (:func:`_is_temperable`) — §16's mixed-structure unlock of Phase-7's original
  *fully*-martensitic-only scope, fenced by the load-bearing RA guard (a high-RA structure can
  *harden* on tempering, and this surface **recommends**).

Honest edges (named, the project signature)
-------------------------------------------
* **``diameter`` is the 0-D *bulk* hardness of a section** — section size enters only through the
  lumped cooling rate, **not** as a radial profile. The centre-of-a-round-bar story is Phase-6c's
  ``D_c`` (:mod:`ideal_diameter`); these are not the same thing.
* **Biot validity propagates** — a recipe needing a severe quench of a thick section carries its
  ``lumped_valid`` flag (the 0-D model stretched), surfaced not hidden.
* **HV is the internal currency** (defined everywhere); HRC is the boundary unit (``nan`` below
  ~20 HRC). The core API targets **HV**; :func:`find_recipes_for_HRC` accepts an HRC spec via
  :func:`~steel.properties.rockwell_c_to_vickers`.
* **The feasible *set* is the deliverable.** Every returned recipe is re-checked against the target
  band. The cost-sorted "recommended" recipe is **labelled convenience, not a claim**: a transparent
  "leaner alloy + milder quench + no extra temper step" sort, *not* a validated cost model.

Scope ceiling (named) — and the v2 inversions that close it
-----------------------------------------------------------
**The hardness inversion above is martensitic-quench-regime only.** Yield is incoherent as a
*co-target* of it — :func:`grain.coupled_grain_properties` returns ``nan`` yield for the martensitic
structures an inverse-hardness search returns — so a yield target lives in a *different* (slow-cool
ferrite-pearlite) regime and **cannot share a recipe**. Phase-7 v2 (2026-06-15) builds the two
inversions the v1 record named as future, each over its own process axis, **still inventing no
physics** (they invert already-validated forward models, same posture):

* **Yield-target inversion — :func:`find_yield_recipes`, here.** It fits this module's
  outer-enumerate × inner-bisect shape, but in the **FP slow-cool regime where yield is defined**:
  enumerate grade, bisect the *austenitizing temperature* (monotone — hotter → coarser PAGS →
  coarser ferrite → lower yield) over :func:`~steel.grain.coupled_grain_properties`. A
  :class:`YieldRecipe` is *grade + austenitize T/t under a normalized cool* — **no quench medium,
  no temper, no Biot** (a separate recipe space, by design). The cooling rate is **baked into**
  :data:`~steel.grain.FERRITE_PAGS_RATIO` (calibrated at one rate), so it is *not* a free knob —
  fewer knobs, honest.
* **Case-depth inversion — :func:`steel.carburize.carburize_time_for_case_depth` /
  :func:`~steel.carburize.carburize_temperature_for_case_depth`.** A different process axis
  (carburising), so it lives in :mod:`steel.carburize` next to its forward
  :func:`~steel.carburize.analytic_case_depth` — a **closed-form** inverse of ``x = 2·erfc⁻¹(r)·√(Dt)``
  (no grade enumeration, none of this module's machinery), *not* forced into the shape here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import sweep
from . import grain
from . import properties as prop
from .cooling import STANDARD_DIAMETER


# --------------------------------------------------------------------------- #
# Tunables — all *convenience*, none load-bearing (no physics lives here)
# --------------------------------------------------------------------------- #
# Default half-width of the target band, in HV. A spec is a band, not a point (the brittleness-
# dodging idiom the demos use): a recipe is feasible iff its predicted hardness lands inside it.
DEFAULT_TOL_HV = 25.0

# Temper-scope gate (§16 mixed-structure unlock). A candidate is in scope for the per-constituent
# temper model (:func:`~steel.properties.tempered_hardness_HV`) when it is martensite-DOMINANT *and*
# retained-austenite-CAPPED (see :func:`_is_temperable`). Phase-7 v1 required a *fully* martensitic
# start (≥ 0.95) because it tempered the pure-martensite curve only; §16 relaxed that to a *mixture*
# temper — the martensite leg softens, the diffusional legs are inert — so the floor drops to
# "dominant" (majority martensite; the inert rest is a minority correction the rule of mixtures
# carries honestly). Below this floor the structure is not martensite-led and is judged as-quenched.
MARTENSITE_TEMPER_MIN = 0.50

# The retained-austenite cap — the LOAD-BEARING guard (§16 step 4). RA is modelled temper-INERT
# (:data:`~steel.properties.TEMPER_ACTIVE`), which is exactly wrong for a *high*-RA structure: RA
# decomposes to bainite / fresh martensite on tempering — non-monotone, and it can *raise* hardness.
# Since this surface RECOMMENDS (unlike a Jominy traverse, which only reports), a high-RA candidate
# is held OUT rather than handed back a confidently-wrong recipe. The cap sits well below the
# registry's hazard (a hard-quenched 1080 is ~0.18 RA); the temperable martensitic grades sit at
# RA ≤ ~0.035, so 0.05 separates them conservatively. Above the cap the candidate is as-quenched only.
RA_TEMPER_MAX = 0.05

# Above this martensite fraction a tempered recipe reads as an ordinary (essentially full)
# quench-and-temper; below it the recipe is a *partial-martensite* mixed temper — materially
# different — so :meth:`Recipe.label` flags the fraction (the §16 honesty cue).
MARTENSITE_NEARLY_FULL = 0.95

# The bisection bracket (°C). Wide enough that at any practical hold time the low end sits below the
# Hollomon–Jaffe softening onset (~150 °C/1 h → f = HV_aq) and the high end above the over-tempered
# breakpoint (~700 °C/1 h → f = HV_floor), so the endpoints clamp to the achievable range exactly.
_TEMPER_T_LO = 20.0
_TEMPER_T_HI = 760.0

# The cost heuristic (a transparent convenience sort, NOT a validated cost model — see module
# docstring). Lower is preferred. Quench severity: a milder quench is cheaper and lower-distortion;
# alloy weights are a rough relative-cost ordering (Ni/Mo dear, Mn/Si/Cr cheap); an extra temper
# step carries a small fixed cost. The weights are deliberately round and editable — nothing
# validated rides on them.
MEDIUM_SEVERITY = {"furnace": 0.0, "air": 1.0, "oil": 2.0, "water": 3.0}
QUENCH_COST_WEIGHT = 0.4
ALLOY_COST_WEIGHT = {"Mn": 0.3, "Si": 0.2, "Ni": 1.0, "Cr": 0.5, "Mo": 1.5}
TEMPER_STEP_COST = 0.5


# --------------------------------------------------------------------------- #
# 1. The data: a recipe (a point in the design space) and the search result
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Recipe:
    """One heat-treatment recipe that meets the spec — a feasible point in the design space.

    The steel grade, the quench ``medium`` and section ``diameter`` it was evaluated at, and the
    tempering step (``temper_C`` is ``None`` for an as-quenched recipe; otherwise the tempering
    temperature in °C for ``t_hours`` h). ``HV``/``HRC`` is the **predicted** hardness this recipe
    delivers (the value re-checked against the target band; ``HRC`` is ``nan`` below ~20 HRC).
    ``martensite`` is the as-quenched martensite fraction the temper acted on — a tempered recipe
    below :data:`MARTENSITE_NEARLY_FULL` is a *partial-martensite* mixed temper (§16), materially
    not a full quench-and-temper, which :meth:`label` flags. ``biot`` flags where the 0-D lumped
    model is stretched (``lumped_valid``). ``cost`` is the convenience-sort key — lower is
    "cheaper/simpler" (see :data:`MEDIUM_SEVERITY`).
    """

    steel: sweep.Steel
    medium: str
    diameter: float
    temper_C: float | None
    t_hours: float
    HV: float
    HRC: float
    martensite: float
    biot: float
    cost: float

    @property
    def lumped_valid(self) -> bool:
        """Whether the 0-D lumped-capacitance model holds for this quench (``Bi < 0.1``)."""
        return self.biot < 0.1

    @property
    def tempered(self) -> bool:
        """Whether this recipe includes a tempering step."""
        return self.temper_C is not None

    def label(self) -> str:
        """A one-line human description — grade, quench, and the temper (or 'as-quenched').

        A *partial-martensite* mixed temper (tempered, below :data:`MARTENSITE_NEARLY_FULL`) appends
        its martensite fraction — the §16 honesty cue that the temper softened only part of the
        structure, not a fully martensitic quench-and-temper.
        """
        if not self.tempered:
            treat = "as-quenched"
        elif self.martensite < MARTENSITE_NEARLY_FULL:
            treat = f"temper {self.temper_C:.0f} °C/{self.t_hours:g} h ({self.martensite:.0%} martensite)"
        else:
            treat = f"temper {self.temper_C:.0f} °C/{self.t_hours:g} h"
        return f"{self.steel.label()}, {self.medium} quench, {treat}"


@dataclass(frozen=True)
class DesignResult:
    """The outcome of a recipe search: the feasible set (cost-sorted) for one (target, section).

    ``recipes`` is **every** recipe whose predicted hardness lands in the target band, sorted by
    :attr:`Recipe.cost` (cheapest/simplest first) — possibly **empty** when the target is outside
    the achievable envelope (the honest "infeasible", :attr:`feasible` ``False``). ``target_HV`` ±
    ``tol_HV`` is the band every recipe satisfies; ``diameter`` (m) the section it was solved for;
    ``t_hours`` the tempering hold used for the temper branch.
    """

    target_HV: float
    tol_HV: float
    diameter: float
    t_hours: float
    recipes: tuple[Recipe, ...]

    @property
    def feasible(self) -> bool:
        """Whether any recipe meets the spec (``False`` ⇒ target outside the achievable envelope)."""
        return len(self.recipes) > 0

    @property
    def recommended(self) -> Recipe | None:
        """The recommended recipe: the cheapest feasible recipe whose 0-D model holds, or ``None``.

        ``recipes`` is cost-sorted (cheapest first), so the recommendation is the first one that is
        :attr:`~Recipe.lumped_valid` — a recipe the simulator itself flags as outside its 0-D
        validity (``Bi ≥ 0.1``) is never headlined as the answer. (The §16 mixed-structure unlock
        admits leaner *partial-martensite* recipes that may be cheaper but Biot-stretched: they stay
        in :attr:`recipes`, surfaced with their flag, yet do not become the recommendation — so the
        headline stays the cheapest *lumped-valid* recipe, the §14 intent.) Falls back to the
        outright cheapest when **no** feasible recipe is lumped-valid (a thick-section spec reachable
        only by a severe quench still returns its best honest option, flagged), and ``None`` when the
        feasible set is empty.
        """
        if not self.recipes:
            return None
        for r in self.recipes:                 # cost-sorted ⇒ the first valid one is the cheapest valid
            if r.lumped_valid:
                return r
        return self.recipes[0]                 # none valid ⇒ the outright cheapest, carrying its ⚠ flag

    @property
    def target_band(self) -> tuple[float, float]:
        """The feasible hardness band ``(low, high)`` in HV."""
        return self.target_HV - self.tol_HV, self.target_HV + self.tol_HV


# --------------------------------------------------------------------------- #
# 2. The inner root-find: invert the (monotone) temper curve by bisection
# --------------------------------------------------------------------------- #
def _temper_to_target(
    fractions: dict, C: float, target_HV: float, t_hours: float, comp: dict | None,
    Vr: float | None = None, tol_HV: float = 0.05, max_iter: int = 80,
) -> float | None:
    """Find the temper ``T`` (°C, at fixed ``t_hours``) tempering ``fractions`` to ``target_HV`` — or ``None``.

    :func:`~steel.properties.tempered_hardness_HV` tempers a phase *mixture* per-constituent: only the
    martensite leg softens (down the Hollomon–Jaffe curve), the diffusional legs are inert, so the
    mixture hardness is strictly monotone-decreasing in ``T`` between the as-quenched mixture
    ``HV_aq`` (low ``T``, sub-onset) and the over-tempered floor ``HV_floor`` (high ``T``, martensite
    floored). The target has a unique solution iff ``HV_floor ≤ target ≤ HV_aq`` — found by bisecting
    the **public** forward function (keeping this module decoupled from the master-curve's internal
    shape, and *inverting whatever the mixture is*: ``{"martensite": 1.0}`` recovers the pure-
    martensite curve exactly). Returns ``None`` when the target is above the as-quenched mixture
    (can't temper *up*) or below its floor (can't soften further) — the honest infeasible (a
    *bracketing failure*), never a silent nearest-miss. ``Vr`` (the cooling-rate Maynier term) threads
    to the inert legs so the bracket matches the structure's as-quenched hardness exactly (the
    consistency the inverse relies on — the same ``Vr`` :func:`~steel.sweep.evaluate` read).
    """
    def f(T: float) -> float:
        return prop.tempered_hardness_HV(fractions, C, T, t_hours, comp=comp, Vr=Vr)

    # Bracket the achievable range from the function itself: sub-onset temper ⇒ the as-quenched
    # mixture (ceiling), over-tempered ⇒ martensite floored under the held inert legs (floor).
    HV_aq = f(_TEMPER_T_LO)
    HV_floor = f(_TEMPER_T_HI)
    # Outside the achievable [floor, as-quenched] band ⇒ no temper reaches it. (A small slack lets a
    # target sitting exactly on an endpoint resolve to that clamped end rather than read infeasible.)
    if not (HV_floor - tol_HV <= target_HV <= HV_aq + tol_HV):
        return None

    lo, hi = _TEMPER_T_LO, _TEMPER_T_HI
    # f decreasing: f(lo) ≈ HV_aq ≥ target ≥ HV_floor ≈ f(hi). Bisect on the sign of (f(mid) − target).
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if f(mid) > target_HV:        # still too hard → temper more → raise T
            lo = mid
        else:                          # too soft → temper less → lower T
            hi = mid
        if hi - lo < 1e-3:
            break
    T = 0.5 * (lo + hi)
    # Defensive re-check: the solved temper really does land on the target (it always should for an
    # interior target; this guards a degenerate bracket rather than returning a wrong recipe).
    return T if abs(f(T) - target_HV) <= max(tol_HV, 1.0) else None


# --------------------------------------------------------------------------- #
# 3. The cost heuristic (convenience sort key — labelled, not load-bearing)
# --------------------------------------------------------------------------- #
def _recipe_cost(steel: sweep.Steel, medium: str, temper_C: float | None) -> float:
    """A transparent "cheaper/simpler is lower" sort key — **convenience, not a validated model**.

    Sums a quench-severity penalty (milder = cheaper, lower-distortion), a rough alloy-cost penalty
    (:data:`ALLOY_COST_WEIGHT`), and a small fixed cost for an extra tempering step. Only orders the
    feasible set; every recipe it ranks already meets the spec.
    """
    quench = QUENCH_COST_WEIGHT * MEDIUM_SEVERITY.get(medium, 1.0)
    temper = TEMPER_STEP_COST if temper_C is not None else 0.0
    return quench + _alloy_cost(steel) + temper


def _alloy_cost(steel: sweep.Steel) -> float:
    """The rough relative alloy-cost penalty (:data:`ALLOY_COST_WEIGHT`) — shared by both inversions' sorts."""
    return sum(ALLOY_COST_WEIGHT[el] * steel.minor()[el] for el in ALLOY_COST_WEIGHT)


def _is_temperable(outcome: sweep.Outcome) -> bool:
    """Whether the as-quenched structure is in scope for the per-constituent temper model.

    Two conditions, both from the as-quenched fractions: **martensite-dominant** (≥
    :data:`MARTENSITE_TEMPER_MIN`, so the mixture is martensite-led and the temper-inert diffusional
    legs are a minority correction) **and retained-austenite-capped** (≤ :data:`RA_TEMPER_MAX`, the
    load-bearing guard — RA is modelled temper-inert, which is wrong for a high-RA structure that can
    *harden* on tempering, and this surface recommends). Phase-7 v1 required a *fully* martensitic
    start; this is the §16 mixed-structure unlock, fenced so a hard-quenched high-RA grade is held
    out rather than offered a confidently-wrong temper.
    """
    f = outcome.fractions()
    return f["martensite"] >= MARTENSITE_TEMPER_MIN and f["retained_austenite"] <= RA_TEMPER_MAX


# --------------------------------------------------------------------------- #
# 4. The search: enumerate grade × medium, solve the temper inner problem
# --------------------------------------------------------------------------- #
def find_recipes(
    target_HV: float,
    tol_HV: float = DEFAULT_TOL_HV,
    diameter: float = STANDARD_DIAMETER,
    grades=None,
    media=sweep.DEFAULT_MEDIA,
    t_hours: float = 1.0,
    austenitize_T: float = 850.0,
) -> DesignResult:
    """Search the grade × quench × temper space for recipes hitting ``target_HV ± tol_HV`` at ``diameter``.

    For each registry grade and quench ``medium`` (the outer enumeration), run the **validated**
    forward chain (:func:`~steel.sweep.evaluate`):

    * as-quenched hardness already in band → a feasible **as-quenched** recipe;
    * as-quenched **above** band and **temperable** (martensite-dominant & RA-capped,
      :func:`_is_temperable`) → bisect a temper ``T`` that brings the *mixture* into band (the inner
      root-find over :func:`~steel.properties.tempered_hardness_HV`), a feasible **tempered** recipe;
    * otherwise infeasible at this (grade, medium) — below band can't be hardened by tempering, an
      above-band structure that is not martensite-dominant (or is high-RA) is out of temper scope.

    Returns the feasible set cost-sorted (cheapest/simplest first), **empty if none** — the honest
    "no recipe in this space meets the spec". ``grades`` defaults to all of
    :data:`~steel.sweep.STEELS` (accepts :class:`~steel.sweep.Steel` objects or registry keys);
    ``media`` to the four standard quenches. ``diameter`` is the section size (m) the bulk hardness
    is read at (a *constraint*, not swept); ``t_hours`` the tempering hold.
    """
    resolved = (list(sweep.STEELS.values()) if grades is None
                else [sweep.STEELS[g] if isinstance(g, str) else g for g in grades])
    lo, hi = target_HV - tol_HV, target_HV + tol_HV

    recipes: list[Recipe] = []
    for steel in resolved:
        for medium in media:
            outcome = sweep.evaluate(steel, medium=medium, diameter=diameter,
                                     austenitize_T=austenitize_T)

            fracs = outcome.fractions()
            # Match sweep.evaluate's Vr handling: it passes a finite °C/h rate or None (never nan),
            # so the tempered mixture's inert legs read the *same* cooling-rate term as the
            # as-quenched hardness this outcome was scored with — the Seam-C consistency the inverse
            # leans on (a sub-onset temper recovers outcome.HV exactly).
            Vr = outcome.Vr if np.isfinite(outcome.Vr) else None

            # Branch 1 — as-quenched already meets the spec (no temper needed).
            if lo <= outcome.HV <= hi:
                recipes.append(_build_recipe(steel, medium, diameter, None, t_hours,
                                             outcome.HV, fracs["martensite"], outcome.biot))
                continue

            # Branch 2 — as-quenched too hard, but a temperable (martensite-dominant, RA-capped)
            # structure can be tempered down into band, softening its martensite leg per-constituent.
            # (Below band is unreachable by tempering; a more severe quench / more hardenable grade —
            # other cells of the grid — is the answer, not this one.)
            if outcome.HV > hi and _is_temperable(outcome):
                T = _temper_to_target(fracs, steel.C, target_HV, t_hours, steel.minor(), Vr)
                if T is not None:
                    HV_t = prop.tempered_hardness_HV(fracs, steel.C, T, t_hours,
                                                     comp=steel.minor(), Vr=Vr)
                    if lo <= HV_t <= hi:            # re-validate through the forward model
                        recipes.append(_build_recipe(steel, medium, diameter, T, t_hours,
                                                      HV_t, fracs["martensite"], outcome.biot))

    recipes.sort(key=lambda r: r.cost)
    return DesignResult(target_HV, tol_HV, diameter, t_hours, tuple(recipes))


def find_recipes_for_HRC(
    target_HRC: float, tol_HRC: float = 2.0, **kwargs
) -> DesignResult:
    """:func:`find_recipes` for a target given in **HRC** (the engineering spec unit).

    Converts the band edges ``target_HRC ± tol_HRC`` to HV through the ASTM E140 table
    (:func:`~steel.properties.rockwell_c_to_vickers`) — converting the **edges** (not a centre plus
    an HV tolerance) honours the non-linear HV↔HRC mapping — then delegates to :func:`find_recipes`.
    Raises :class:`ValueError` if the band falls outside the ~20–67 HRC convertible range (where
    Rockwell-C is undefined). All other keyword arguments pass straight through.
    """
    hv_hi = prop.rockwell_c_to_vickers(target_HRC + tol_HRC)   # harder edge → larger HV
    hv_lo = prop.rockwell_c_to_vickers(target_HRC - tol_HRC)
    if not (np.isfinite(hv_lo) and np.isfinite(hv_hi)):
        raise ValueError(
            f"target {target_HRC} ± {tol_HRC} HRC falls outside the ~20–67 HRC band ASTM E140 "
            "converts — give the target in HV (the internal currency) for soft material instead.")
    target_HV = 0.5 * (hv_lo + hv_hi)
    tol_HV = 0.5 * (hv_hi - hv_lo)
    return find_recipes(target_HV, tol_HV=tol_HV, **kwargs)


def _build_recipe(
    steel: sweep.Steel, medium: str, diameter: float, temper_C: float | None,
    t_hours: float, HV: float, martensite: float, biot: float,
) -> Recipe:
    """Assemble a :class:`Recipe` — attach the HRC reading, the martensite fraction, and the cost."""
    return Recipe(
        steel=steel, medium=medium, diameter=diameter, temper_C=temper_C, t_hours=t_hours,
        HV=float(HV), HRC=float(prop.vickers_to_rockwell_c(HV)), martensite=float(martensite),
        biot=float(biot), cost=_recipe_cost(steel, medium, temper_C),
    )


# =========================================================================== #
# Phase 7 v2 — the yield-target inversion (the ferrite-pearlite slow-cool regime)
# =========================================================================== #
# The hardness inversion above is the martensitic quench-and-temper regime; this is its
# slow-cool sibling. Yield strength is the property the hardness chain deliberately refuses to give
# (properties.py returns UTS from hardness, not yield — Tabor's H≈3σ is flow stress), and Phase 5
# supplies it for the FERRITE-PEARLITE structure only: austenitize (T, t) → PAGS → ferrite grain →
# Hall–Petch/Pickering yield. That law returns nan for a martensitic structure, so a yield target
# CANNOT live in the quench regime the hardness search returns — it is a separate recipe space, and
# this is why yield was named a *separate* future inversion, not a v1 co-target.
#
# The knob is the AUSTENITIZING TEMPERATURE. Within a grade, %pearlite and the minor-alloy solutes
# are fixed (equilibrium from carbon), so yield varies only through ferrite grain size: hotter
# austenitize → coarser PAGS → coarser ferrite → LOWER yield (the d^(−½) Hall–Petch term). So
# yield(T) is strictly monotone-decreasing across the practical austenitizing window — the same
# clean "bisect the public forward function" inner problem the temper inversion uses. The cooling
# rate is NOT a knob: grain.FERRITE_PAGS_RATIO is calibrated at one (normalized) rate, so a yield
# recipe is grade + austenitize (T, t) under a normalized cool — fewer knobs, honestly fewer.

# The practical austenitizing window the inner bisection brackets (°C). The floor sits above the
# Ac3 of these registry grades (full austenitization; representative, not a per-grade computed Ac3);
# the ceiling is a grain-coarsening / over-austenitizing limit. Named as a stated constraint — a
# yield target outside [yield(T_hi), yield(T_lo)] for every grade is the honest "infeasible".
_AUSTENITIZE_T_LO = 850.0
_AUSTENITIZE_T_HI = 1100.0

# Default half-width of the yield target band (MPa) — a spec is a band, not a point, as with HV.
DEFAULT_YIELD_TOL_MPA = 15.0

# The yield-recipe convenience cost (same posture as _recipe_cost — labelled, not validated): the
# alloy-cost penalty (no quench/temper here) plus a small austenitizing-energy term so that, at
# equal alloy, the cheaper/cooler austenitize (which also gives the finer grain) sorts first. Round
# and editable; nothing validated rides on it.
AUSTENITIZE_COST_WEIGHT = 0.002   # per °C above the window floor


@dataclass(frozen=True)
class YieldRecipe:
    """One normalized-and-austenitized recipe that meets a **yield** spec — the FP-regime analogue of :class:`Recipe`.

    A yield recipe is *grade + austenitizing schedule under a normalized (slow) cool* — there is
    deliberately **no quench medium, no temper, and no Biot flag** (those are the martensitic
    :class:`Recipe`'s; mixing them here would conflate the two regimes). ``yield_MPa`` is the
    **predicted** lower yield this recipe delivers (re-checked against the target band);
    ``dbtt_C`` is the co-property the same Phase-5 call returns — carried because grain refinement
    is the lone lever that improves *both* (yield ↑, DBTT ↓), the §5b foil, so a yield recipe can
    show its toughness cost for free. ``pags_um`` / ``ferrite_um`` are the grain sizes the schedule
    produces; ``cost`` is the convenience-sort key (lower = leaner alloy / cooler austenitize).
    """

    steel: sweep.Steel
    austenitize_T: float     # °C
    austenitize_t: float     # h
    yield_MPa: float
    dbtt_C: float
    pags_um: float
    ferrite_um: float
    cost: float

    def label(self) -> str:
        """A one-line human description — grade, the normalized cool, and the austenitizing schedule."""
        return (f"{self.steel.label()}, normalized — austenitize "
                f"{self.austenitize_T:.0f} °C/{self.austenitize_t:g} h")


@dataclass(frozen=True)
class YieldDesignResult:
    """The outcome of a yield-recipe search: the feasible set (cost-sorted) for one yield target.

    ``recipes`` is **every** grade whose austenitizing window can hit ``target_MPa ± tol_MPa``,
    sorted by :attr:`YieldRecipe.cost` (leaner/cooler first) — possibly **empty** when the target is
    outside every grade's achievable yield band (the honest "infeasible"). ``t_hours`` is the
    austenitizing hold the inner bisection held fixed while solving for temperature.
    """

    target_MPa: float
    tol_MPa: float
    t_hours: float
    recipes: tuple[YieldRecipe, ...]

    @property
    def feasible(self) -> bool:
        """Whether any recipe meets the spec (``False`` ⇒ target outside every grade's envelope)."""
        return len(self.recipes) > 0

    @property
    def recommended(self) -> YieldRecipe | None:
        """The recommended recipe: the cheapest feasible one (leanest alloy / coolest austenitize), or ``None``.

        Unlike the hardness :class:`DesignResult`, there is no Biot validity to weigh — every recipe
        here is a normalized cool the lumped grain-growth model is posed for — so the recommendation
        is simply the cost-sorted head of the feasible set.
        """
        return self.recipes[0] if self.recipes else None

    @property
    def target_band(self) -> tuple[float, float]:
        """The feasible yield band ``(low, high)`` in MPa."""
        return self.target_MPa - self.tol_MPa, self.target_MPa + self.tol_MPa


def _yield_at(
    steel: sweep.Steel, T_austenitize: float, t_hours: float, N_free_pct: float, P_pct: float,
) -> grain.GrainProperties:
    """The Phase-5c coupled result for one grade at one austenitizing schedule (the forward call)."""
    return grain.coupled_grain_properties(
        T_austenitize, t_hours, steel.C, comp=steel.minor(),
        N_free_pct=N_free_pct, P_pct=P_pct,
    )


def _austenitize_to_yield(
    steel: sweep.Steel, target_MPa: float, t_hours: float, N_free_pct: float, P_pct: float,
    tol_MPa: float = 0.05, max_iter: int = 80,
) -> float | None:
    """Find the austenitizing ``T`` (°C, at fixed ``t_hours``) giving ``target_MPa`` yield for ``steel`` — or ``None``.

    Within a grade the yield depends on the austenitizing temperature **only** through the ferrite
    grain size (``%pearlite`` and the solutes are carbon-/composition-fixed), and grain size grows
    monotonically with ``T`` while the Hall–Petch term *falls* with grain size, so ``yield(T)`` is
    **strictly monotone-decreasing** between the finest-grain ceiling ``Y_hi`` (at the cool window
    floor :data:`_AUSTENITIZE_T_LO`) and the coarsest-grain floor ``Y_lo`` (at the hot ceiling
    :data:`_AUSTENITIZE_T_HI`). The target has a unique solution iff ``Y_lo ≤ target ≤ Y_hi`` —
    found by bisecting the **public** forward function (decoupled from Phase-5's internal shape, as
    the temper inversion is from the master curve). Returns ``None`` when the target is above the
    finest-grain ceiling (can't strengthen further inside the window) or below the coarsest-grain
    floor (can't soften further) — the honest infeasible, never a silent nearest-miss.
    """
    def f(T: float) -> float:
        return _yield_at(steel, T, t_hours, N_free_pct, P_pct).yield_MPa

    Y_hi = f(_AUSTENITIZE_T_LO)   # finest grain (coolest austenitize) ⇒ highest yield (ceiling)
    Y_lo = f(_AUSTENITIZE_T_HI)   # coarsest grain (hottest austenitize) ⇒ lowest yield (floor)
    if not (np.isfinite(Y_hi) and np.isfinite(Y_lo)):
        return None               # martensitic / out-of-table grade — not an FP yield candidate
    if not (Y_lo - tol_MPa <= target_MPa <= Y_hi + tol_MPa):
        return None

    lo, hi = _AUSTENITIZE_T_LO, _AUSTENITIZE_T_HI
    # f decreasing: f(lo) ≈ Y_hi ≥ target ≥ Y_lo ≈ f(hi). Bisect on the sign of (f(mid) − target).
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if f(mid) > target_MPa:    # yield still too high → coarser grain → hotter → raise T
            lo = mid
        else:                       # too low → finer grain → cooler → lower T
            hi = mid
        if hi - lo < 1e-3:
            break
    T = 0.5 * (lo + hi)
    return T if abs(f(T) - target_MPa) <= max(tol_MPa, 1.0) else None


def find_yield_recipes(
    target_MPa: float,
    tol_MPa: float = DEFAULT_YIELD_TOL_MPA,
    t_hours: float = 1.0,
    grades=None,
    N_free_pct: float = grain.DEFAULT_N_FREE_PCT,
    P_pct: float = 0.0,
) -> YieldDesignResult:
    """Search the grade × austenitizing space for normalized recipes hitting ``target_MPa ± tol_MPa`` yield.

    The slow-cool (ferrite-pearlite) sibling of :func:`find_recipes`. For each registry grade (the
    outer enumeration) bisect the austenitizing temperature that brings the **Phase-5c coupled
    yield** (:func:`~steel.grain.coupled_grain_properties`) into band — a feasible grade is one whose
    practical austenitizing window :data:`_AUSTENITIZE_T_LO`–:data:`_AUSTENITIZE_T_HI` brackets the
    target. Returns the feasible set cost-sorted (leaner alloy / cooler austenitize first),
    **empty if none** — the honest "no grade reaches this yield by normalizing in the window".

    No quench, no temper: the recipe is a normalized cool, and the cooling rate is folded into the
    calibrated :data:`~steel.grain.FERRITE_PAGS_RATIO`, so the only knobs are grade and the
    austenitizing schedule. ``grades`` defaults to all of :data:`~steel.sweep.STEELS` (accepts
    :class:`~steel.sweep.Steel` objects or registry keys); ``t_hours`` is the austenitizing hold;
    ``N_free_pct`` / ``P_pct`` thread the free-nitrogen and phosphorus terms into the yield/DBTT laws
    (``P_pct`` is the signed-impurity foil — it raises yield *and* DBTT).

    **No new physics, no validation triad** (the :mod:`sweep`/:func:`find_recipes` posture): this
    inverts the validated Phase-5 forward model faithfully and says "infeasible" honestly.
    """
    resolved = (list(sweep.STEELS.values()) if grades is None
                else [sweep.STEELS[g] if isinstance(g, str) else g for g in grades])
    lo, hi = target_MPa - tol_MPa, target_MPa + tol_MPa

    recipes: list[YieldRecipe] = []
    for steel in resolved:
        T = _austenitize_to_yield(steel, target_MPa, t_hours, N_free_pct, P_pct)
        if T is None:
            continue
        gp = _yield_at(steel, T, t_hours, N_free_pct, P_pct)
        if lo <= gp.yield_MPa <= hi:            # re-validate through the forward model
            cost = (_alloy_cost(steel)
                    + AUSTENITIZE_COST_WEIGHT * (T - _AUSTENITIZE_T_LO))
            recipes.append(YieldRecipe(
                steel=steel, austenitize_T=float(T), austenitize_t=t_hours,
                yield_MPa=float(gp.yield_MPa), dbtt_C=float(gp.dbtt_C),
                pags_um=float(gp.pags_um), ferrite_um=float(gp.ferrite_um), cost=float(cost),
            ))

    recipes.sort(key=lambda r: r.cost)
    return YieldDesignResult(target_MPa, tol_MPa, t_hours, tuple(recipes))
