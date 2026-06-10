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
  :func:`~steel.properties.tempered_martensite_HV` is strictly monotone-decreasing in temper ``T``
  (through the Hollomon–Jaffe parameter), with achievable range ``[HV_floor, HV_aq]``, so "what
  temper ``T`` hits the target?" has a **unique** solution — found by **bisection over the public
  forward function** (so this module stays decoupled from the master-curve's internal shape: it
  inverts whatever ``tempered_martensite_HV`` is). The temper branch fires **only** for a fully-
  martensitic as-quenched candidate — the validated martensite-only temper scope.

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

Scope ceiling (named)
---------------------
**Hardness-only target in v1.** Yield is incoherent as a co-target — :func:`grain.coupled_grain_properties`
returns ``nan`` yield for the martensitic structures an inverse-hardness search returns — so a
yield target lives in a *different* (slow-cool FP) regime and cannot share a recipe. Yield-target
inversion and case-depth inversion (carburising — a different process axis) are named as separate
future inversions, not v1 knobs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import sweep
from . import properties as prop
from .cooling import STANDARD_DIAMETER


# --------------------------------------------------------------------------- #
# Tunables — all *convenience*, none load-bearing (no physics lives here)
# --------------------------------------------------------------------------- #
# Default half-width of the target band, in HV. A spec is a band, not a point (the brittleness-
# dodging idiom the demos use): a recipe is feasible iff its predicted hardness lands inside it.
DEFAULT_TOL_HV = 25.0

# A structure must be essentially fully martensitic for the martensite-only temper model to apply
# (:func:`~steel.properties.tempered_martensite_HV` tempers a *fully* martensitic start). Below this
# the candidate is judged as-quenched only — a mixed structure would have to be tempered
# per-constituent (the documented Phase-3b deferral).
MARTENSITE_TEMPER_MIN = 0.95

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
    ``biot`` flags where the 0-D lumped model is stretched (``lumped_valid``). ``cost`` is the
    convenience-sort key — lower is "cheaper/simpler" (see :data:`MEDIUM_SEVERITY`).
    """

    steel: sweep.Steel
    medium: str
    diameter: float
    temper_C: float | None
    t_hours: float
    HV: float
    HRC: float
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
        """A one-line human description — grade, quench, and the temper (or 'as-quenched')."""
        treat = f"temper {self.temper_C:.0f} °C/{self.t_hours:g} h" if self.tempered else "as-quenched"
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
        """The cheapest/simplest feasible recipe (lowest :attr:`Recipe.cost`), or ``None``."""
        return self.recipes[0] if self.recipes else None

    @property
    def target_band(self) -> tuple[float, float]:
        """The feasible hardness band ``(low, high)`` in HV."""
        return self.target_HV - self.tol_HV, self.target_HV + self.tol_HV


# --------------------------------------------------------------------------- #
# 2. The inner root-find: invert the (monotone) temper curve by bisection
# --------------------------------------------------------------------------- #
def _temper_to_target(
    C: float, target_HV: float, t_hours: float, comp: dict | None,
    tol_HV: float = 0.05, max_iter: int = 80,
) -> float | None:
    """Find the temper ``T`` (°C, at fixed ``t_hours``) giving ``target_HV`` — or ``None`` if unreachable.

    :func:`~steel.properties.tempered_martensite_HV` is strictly monotone-decreasing in ``T``
    between the as-quenched hardness ``HV_aq`` (low ``T``) and the over-tempered floor ``HV_floor``
    (high ``T``), so the target has a unique solution iff ``HV_floor ≤ target ≤ HV_aq``. We bisect
    the **public** forward function (keeping this module decoupled from the master-curve's internal
    shape). Returns ``None`` when the target is above as-quenched (can't temper *up*) or below the
    spheroidite floor (can't soften further) — the honest infeasible (a *bracketing failure*),
    never a silent nearest-miss.
    """
    HV_aq = prop.vickers_martensite(C, comp=comp)
    HV_floor = prop.vickers_ferrite_pearlite(C, comp=comp)
    # Outside the achievable [floor, as-quenched] band ⇒ no temper reaches it. (A small slack lets a
    # target sitting exactly on an endpoint resolve to that clamped end rather than read infeasible.)
    if not (HV_floor - tol_HV <= target_HV <= HV_aq + tol_HV):
        return None

    def f(T: float) -> float:
        return prop.tempered_martensite_HV(C, T, t_hours, comp=comp)

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
    alloy = sum(ALLOY_COST_WEIGHT[el] * steel.minor()[el] for el in ALLOY_COST_WEIGHT)
    temper = TEMPER_STEP_COST if temper_C is not None else 0.0
    return quench + alloy + temper


def _is_fully_martensitic(outcome: sweep.Outcome) -> bool:
    """Whether the as-quenched structure is martensitic enough for the martensite-only temper model."""
    return outcome.fractions()["martensite"] >= MARTENSITE_TEMPER_MIN


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
    * as-quenched **above** band and **fully martensitic** → bisect a temper ``T`` that brings it
      into band (the inner root-find), a feasible **tempered** recipe;
    * otherwise infeasible at this (grade, medium) — below band can't be hardened by tempering, a
      non-martensitic above-band structure is out of the temper model's scope.

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

            # Branch 1 — as-quenched already meets the spec (no temper needed).
            if lo <= outcome.HV <= hi:
                recipes.append(_build_recipe(steel, medium, diameter, None, t_hours,
                                             outcome.HV, outcome.biot))
                continue

            # Branch 2 — as-quenched too hard, but a fully martensitic structure can be tempered
            # down into band. (Below band is unreachable by tempering; a more severe quench / more
            # hardenable grade — other cells of the grid — is the answer, not this one.)
            if outcome.HV > hi and _is_fully_martensitic(outcome):
                T = _temper_to_target(steel.C, target_HV, t_hours, steel.minor())
                if T is not None:
                    HV_t = prop.tempered_martensite_HV(steel.C, T, t_hours, comp=steel.minor())
                    if lo <= HV_t <= hi:            # re-validate through the forward model
                        recipes.append(_build_recipe(steel, medium, diameter, T, t_hours,
                                                      HV_t, outcome.biot))

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
    t_hours: float, HV: float, biot: float,
) -> Recipe:
    """Assemble a :class:`Recipe` — attach the HRC reading and the convenience cost."""
    return Recipe(
        steel=steel, medium=medium, diameter=diameter, temper_C=temper_C, t_hours=t_hours,
        HV=float(HV), HRC=float(prop.vickers_to_rockwell_c(HV)), biot=float(biot),
        cost=_recipe_cost(steel, medium, temper_C),
    )
