"""Martempering (marquenching): austempering's short-hold sibling (Steel Phase 6e).

Phase 6d (:mod:`austemper`) built the **isothermal hold route** — quench past the pearlite
nose into a bath between ``Bs`` and ``Mₛ`` and hold *long enough* to fully transform to bainite.
Its docstring named the seam this module fills: *"at/below Mₛ martensite forms on the way in —
martempering, the same hold machinery is the seam, deliberately not built."* That phrasing was
slightly off in one detail this module corrects: martempering holds in the **same window**
``Mₛ < T_bath < Bs`` as austempering — it differs only in **hold time**.

The one axis: hold time
-----------------------
Austempering and martempering are the *same two-stage path* (instant quench into a hot bath above
``Mₛ``, hold, cool) read at opposite ends of one continuous **hold-time axis**:

* **Austemper** holds *past* the bainite reaction's completion → the product is **bainite**.
* **Martemper** holds *short* — only long enough for the section to **thermally equalise** at the
  bath, well before bainite nucleates — then slow-cools through ``Mₛ→Mf`` to **martensite**.

The boundary between them is a single critical hold time
:func:`critical_hold_time` ``t_crit(steel, T_bath)`` = the bath-temperature bainite-onset time
(the anchored 6d kinetics). Below ``t_crit`` the hold forms negligible bainite, so the austenite
that survives shears to martensite on the final cool exactly as a *direct quench* would — the
martemper microstructure is the direct-quench microstructure. Above ``t_crit`` bainite appears and
the route drifts into austempering. So martempering adds **no new physics and no new constant**:
its kinetics, hardness, and bookkeeping are 6d's, re-read for the martensite outcome — the same
"composed process over validated pieces, not new modelling" stance as Phase 7 inverse design.

What martempering is *for* — the distortion payoff (the reason to build it)
--------------------------------------------------------------------------
If martempering gave the same hardness as a quench and nothing else, it would be a relabelling.
Its industrial reason is **distortion and quench-crack reduction**: in a direct quench the surface
reaches ``Mₛ`` and transforms while the core is still tens of degrees hotter and untransformed, so
the section transforms *non-uniformly in space* — differential transformation strain → distortion,
residual stress, cracking. Martempering shrinks that by **two steps that are both essential**: the
bath hold equalises the section *below the nose*, and the **slow final cool** then takes the whole
(now near-isothermal) section through ``Mₛ`` *slowly and near-uniformly* — so the through-section
gradient *at the moment of transformation* is small (the Mₛ crossing happens deep in the slow cool,
not during the hold). That gradient is inherently spatial, so
this module computes it on the **frozen heat engine** (:mod:`engines.diffusion`) for a planar slab:
:func:`slab_thermal_history` marches a two-stage Robin surface (bath, then air) with a symmetry
centreline, and :func:`distortion_metric` reads the surface−centre temperature difference at the
``Mₛ`` crossing — small for martemper, large for a direct quench. **No solid mechanics** is modelled
(true residual stress is the deferred Option-#2 axis); the gradient is the standard thermal *proxy*
for distortion risk, computed without inventing a stress model.

Cited vs calibrated (the discipline) — all inherited
----------------------------------------------------
Nothing here is newly fitted. The bainite kinetics (atlas-anchored per-steel, 6d), Andrews ``Mₛ``,
Steven–Haynes ``Bs``, Koistinen–Marburger, the rule-of-mixtures hardness, the thermophysical
``ρ, c_p, k`` and the frozen conduction solver are all cited/validated upstream. Martempering
**composes** them.

Named scope edges (each a real limit, not hidden)
-------------------------------------------------
* **Per-steel only.** Bainite kinetics are atlas-anchored, so martempering is defined for the
  anchored steels (``"1080"``, ``"4340"`` — :data:`~steel.austemper.ATLAS_STEELS`). No cross-steel
  bainite-time comparison (the documented 6d ``BC`` cross-composition failure).
* **``t_crit`` near ``Mₛ`` is optimistic.** Holds sit just above ``Mₛ``, in the regime where the
  atlas shows a near-``Mₛ`` bainite *acceleration* the Li/KV rate does not model (6d edge), so the
  modelled onset time over-estimates the real safe-hold budget — the feasibility margins are a
  best case, named.
* **Onset is the atlas "begin-line" (shape-only) regime.** ``t_crit`` reads a small completion
  fraction; the 6d module validates the **50 % line**, treating the begin line as shape only. So
  ``t_crit`` is a *ranking/feasibility* quantity, not a tightly-validated absolute time.
* **The slow final cool's microstructure effect is 0-D-immaterial *near* ``Mₛ`` only.** For a bath
  just above ``Mₛ`` (the default) the only lumped effect of the cool is Koistinen–Marburger at the
  temperature reached (room) — slow vs instant changes nothing in the fractions, because the short
  descent from just-above-``Mₛ`` spends little time in the bainite-active range. **At a higher bath**
  (nearer ``Bs``) the slow cool would traverse the bainite range slowly and form bainite that the
  delegated instant-Koistinen–Marburger idealisation **misses** — so the lumped outcome is faithful
  near ``Mₛ``, not for a high bath. Where the slow cool *always* matters is the **spatial gradient**
  — which is exactly the payoff, and is computed spatially.
* **Equivalence reference is the *ideal* nose-missing quench** (full austenite → KM), what martemper
  converges to by construction. A real water quench in this model may clip a little nose (e.g. 1080
  picks up ~5 % bainite), so martemper can read marginally *harder* than real water — reported,
  not hidden.

Units: °C, seconds, wt%, mass fractions in [0, 1] — matching :mod:`kinetics`/:mod:`austemper`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from engines.diffusion import Diffusion1D, Neumann, Robin, uniform_grid

from . import cooling
from .austemper import (
    ATLAS_STEELS, anchored_reaction, austemper, hold_time_to_fraction,
)
from .kinetics import andrews_Ms, koistinen_marburger
from .properties import hardness_HV, vickers_to_rockwell_c

# A hold that forms less bainite than this is treated as a "true" martemper — the austenite that
# survives shears to martensite, indistinguishable (in hardness) from a direct quench. It is the
# completion fraction :func:`critical_hold_time` solves for: the martemper↔austemper boundary.
BAINITE_CONTAMINATION_TOL = 0.01


# --------------------------------------------------------------------------- #
# 1. The hold-time boundary and the ideal-quench reference (0-D, pure reuse)
# --------------------------------------------------------------------------- #
def critical_hold_time(
    steel: str, T_bath: float, X: float = BAINITE_CONTAMINATION_TOL
) -> float:
    """The longest hold (s) at ``T_bath`` (°C) that stays a martemper — the austemper boundary.

    ``t_crit`` is the bath-temperature time for the anchored 6d bainite reaction to reach the small
    contamination fraction ``X`` (:func:`~steel.austemper.hold_time_to_fraction`): below it the hold
    forms < ``X`` bainite and the route is hardness-identical to a direct quench; above it bainite
    accumulates and the route becomes austempering. This single number *is* the unified
    martemper/austemper hold-time axis. ``inf`` at/above ``Bs`` (no bainite reaction → any hold is
    safe kinetically). **Named caveat:** near ``Mₛ`` this is an optimistic over-estimate (the
    unmodelled near-``Mₛ`` acceleration) and it reads the atlas begin-line (shape-only) regime — a
    feasibility/ranking quantity, not a tightly-validated absolute time.
    """
    return hold_time_to_fraction(steel, T_bath, X)


@dataclass(frozen=True)
class IdealQuench:
    """The microstructure/hardness of an *ideal* (nose-missing) direct quench to ``T_quench``.

    Full austenite shears to martensite per Koistinen–Marburger at ``T_quench``, the rest staying
    retained γ; no diffusional product. This is what a martemper with a sub-``t_crit`` hold converges
    to by construction — the equivalence reference the hold preserves.
    """

    steel: str
    T_quench: float
    Ms: float
    martensite: float
    retained_austenite: float
    HV: float
    HRC: float

    def fractions(self) -> dict:
        """Product fractions (the stable five-key set :mod:`pathint`/:mod:`austemper` emit)."""
        return {
            "ferrite": 0.0, "pearlite": 0.0, "bainite": 0.0,
            "martensite": self.martensite, "retained_austenite": self.retained_austenite,
        }


def ideal_quench(steel: str, T_quench: float = 25.0) -> IdealQuench:
    """The ideal nose-missing direct quench of a named atlas steel to ``T_quench`` (°C).

    Full austenite → Koistinen–Marburger at ``T_quench`` (Andrews ``Mₛ`` from the atlas
    composition) → martensite + retained γ, hardness by the rule of mixtures. The reference a
    martemper hold (kept under :func:`critical_hold_time`) reproduces — so the equivalence is
    **exact by construction, conditional on nose-avoidance**, not an independent benchmark.
    """
    if steel not in ATLAS_STEELS:
        raise ValueError(f"no atlas anchor for steel {steel!r} — anchored: {sorted(ATLAS_STEELS)}")
    s = ATLAS_STEELS[steel]
    Ms = andrews_Ms(**s.comp)
    f_km = koistinen_marburger(T_quench, Ms)
    fractions = {
        "ferrite": 0.0, "pearlite": 0.0, "bainite": 0.0,
        "martensite": f_km, "retained_austenite": 1.0 - f_km,
    }
    comp_minor = {el: wt for el, wt in s.comp.items() if el != "C"}
    HV = hardness_HV(fractions, s.comp["C"], comp=comp_minor)
    return IdealQuench(
        steel=steel, T_quench=T_quench, Ms=Ms,
        martensite=f_km, retained_austenite=1.0 - f_km,
        HV=HV, HRC=float(vickers_to_rockwell_c(HV)),
    )


@dataclass(frozen=True)
class MartemperResult:
    """The outcome of a martempering hold — the austemper microstructure read for martensite.

    ``bainite`` is the *unwanted contaminant* the short hold forms (≈ 0 for a true martemper);
    ``martensite``/``retained_austenite`` are the Koistinen–Marburger fate of the surviving
    austenite; ``HV``/``HRC`` the rule-of-mixtures hardness. ``t_crit`` is the
    :func:`critical_hold_time` boundary and ``bainite_safe`` flags ``t_hold ≤ t_crit`` (the
    contamination stayed under :data:`BAINITE_CONTAMINATION_TOL`). ``quench_HV``/``quench_HRC`` are
    the :func:`ideal_quench` equivalence reference. ``t``/``U`` are the hold's bainite-completion
    history (for the mechanism view).
    """

    steel: str
    T_bath: float
    t_hold: float
    Bs: float
    Ms: float
    bainite: float
    martensite: float
    retained_austenite: float
    HV: float
    HRC: float
    t_crit: float
    bainite_safe: bool
    quench_HV: float
    quench_HRC: float
    t: np.ndarray
    U: np.ndarray

    def fractions(self) -> dict:
        """Product fractions — the stable five-key set property consumers index."""
        return {
            "ferrite": 0.0, "pearlite": 0.0, "bainite": self.bainite,
            "martensite": self.martensite, "retained_austenite": self.retained_austenite,
        }

    def dominant(self) -> str:
        """Name of the largest-fraction product — the headline microstructure."""
        return max(self.fractions().items(), key=lambda kv: kv[1])[0]


def martemper(
    steel: str, T_bath: float, t_hold: float,
    T_quench: float = 25.0, n_steps: int = 6000,
) -> MartemperResult:
    """Martemper a named atlas steel: quench to ``T_bath`` (°C), hold ``t_hold`` (s), slow-cool.

    The hold + final-cool microstructure is computed by :func:`~steel.austemper.austemper` — the
    *same* atlas-anchored bainite kinetics and Koistinen–Marburger bookkeeping (martempering adds no
    new physics) — and re-read here for the **martensite** outcome. The martemper-specific analysis
    is layered on: the :func:`critical_hold_time` boundary, the ``bainite_safe`` flag (did the hold
    stay a true martemper?), and the :func:`ideal_quench` equivalence reference.

    ``T_bath`` must sit strictly inside ``Mₛ < T_bath < Bs`` (austemper's guard, raised as
    ``ValueError`` outside it). A ``t_hold`` beyond :func:`critical_hold_time` is **not** an error —
    it is a martemper that has drifted into austempering, reported with ``bainite_safe = False``
    (the two routes are one hold-time axis). The slow final cool is idealised the same way austemper
    idealises its quench-out (instantaneous to ``T_quench``); in the lumped microstructure that is
    immaterial — the slow cool's payoff is spatial (:func:`slab_thermal_history`), not in the
    fractions.
    """
    a = austemper(steel, T_bath, t_hold, T_quench=T_quench, n_steps=n_steps)
    t_crit = critical_hold_time(steel, T_bath)
    iq = ideal_quench(steel, T_quench)
    return MartemperResult(
        steel=steel, T_bath=T_bath, t_hold=t_hold,
        Bs=a.Bs, Ms=a.Ms,
        bainite=a.bainite, martensite=a.martensite, retained_austenite=a.retained_austenite,
        HV=a.HV, HRC=a.HRC,
        t_crit=t_crit, bainite_safe=(a.bainite <= BAINITE_CONTAMINATION_TOL),
        quench_HV=iq.HV, quench_HRC=iq.HRC,
        t=a.t, U=a.U,
    )


# --------------------------------------------------------------------------- #
# 2. The spatial payoff: a planar slab on the frozen heat engine
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SlabHistory:
    """Through-thickness thermal history of a quenched planar slab (the distortion solve).

    A plate of full thickness ``2·half_thickness`` cooled on both faces, modelled by symmetry on
    ``[0, half_thickness]`` with an insulated centreline (``x = 0``) and a convective surface
    (``x = half_thickness``). ``t`` is the time grid (s); ``surface``/``center`` are the two face
    histories (°C); ``T`` is the full field ``T[i, j]`` (time × cell). ``t_hold`` is ``None`` for a
    single-stage direct quench, else the bath-hold duration before the second (slow-cool) stage.
    """

    t: np.ndarray
    surface: np.ndarray
    center: np.ndarray
    T: np.ndarray
    half_thickness: float
    t_hold: float | None

    def crossing_time(self, face: str, T_cross: float) -> float:
        """Time (s) at which ``face`` (``"surface"``/``"center"``) cools through ``T_cross`` (°C).

        Interpolated from the monotone-cooling history; ``inf`` if the face never reaches it.
        """
        T_face = self.surface if face == "surface" else self.center
        below = np.flatnonzero(T_face <= T_cross)
        if below.size == 0 or below[0] == 0:
            return math.inf
        return float(np.interp(T_cross, T_face[::-1], self.t[::-1]))

    def gradient_at_surface_crossing(self, T_cross: float) -> float:
        """Surface−centre temperature difference (°C) when the surface first reaches ``T_cross``.

        Negative (centre hotter than surface) during a quench; its magnitude is the through-section
        gradient *at the onset of transformation* — the distortion proxy. ``nan`` if the surface
        never reaches ``T_cross``.
        """
        t_cross = self.crossing_time("surface", T_cross)
        if not math.isfinite(t_cross):
            return float("nan")
        T_center_then = float(np.interp(t_cross, self.t, self.center))
        return T_cross - T_center_then


def slab_thermal_history(
    half_thickness: float,
    T0: float,
    h_quench: float,
    T_bath: float,
    t_hold: float | None = None,
    h_slow: float = cooling.H_AIR,
    T_env: float = 25.0,
    n_cells: int = 120,
    n_t: int = 4000,
    t_end: float | None = None,
) -> SlabHistory:
    """March a planar slab's two-stage quench on the frozen :class:`~engines.diffusion.Diffusion1D`.

    Heat mode (``D = α = k/ρc_p``), symmetry centreline (``Neumann(0)``), convective surface
    (``Robin``). **Single stage** (``t_hold=None``): a direct quench — ``Robin(h_quench, T_env)``
    throughout. **Two stage** (``t_hold`` set, the martemper): ``Robin(h_quench, T_bath)`` for the
    bath quench+hold, then the surface BC is swapped to ``Robin(h_slow, T_env)`` for the slow cool —
    re-instantiating the solver mid-march, the Jominy stepping pattern, the only "new" mechanism and
    one the frozen engine fully covers (no Strang splitting: a uniformly surface-cooled section has
    no lateral sink). The engine Robin coefficient is ``h_phys/(ρc_p)`` (the :mod:`jominy`
    convention). ``t_end`` defaults to enough time for the (slow) final cool to take the centre
    below ``T_env`` comfortably.
    """
    alpha = cooling.K_STEEL / (cooling.RHO_STEEL * cooling.CP_STEEL)

    def h_eng(h_phys: float) -> float:
        return h_phys / (cooling.RHO_STEEL * cooling.CP_STEEL)

    if t_end is None:
        tau_cond = half_thickness**2 / alpha
        if t_hold is None:
            t_end = max(8.0 * tau_cond, 30.0 * cooling.lumped_time_constant(h_quench, half_thickness))
        else:
            tau_slow = cooling.lumped_time_constant(h_slow, half_thickness)
            t_end = t_hold + max(8.0 * tau_cond, 8.0 * tau_slow)

    grid = uniform_grid(half_thickness, n_cells)
    t = np.linspace(0.0, float(t_end), n_t + 1)
    field = np.empty((t.size, n_cells))
    T = np.full(n_cells, float(T0))
    field[0] = T

    bath_target = T_bath if t_hold is not None else T_env
    solver = Diffusion1D(grid, alpha, Neumann(0.0), Robin(h_eng(h_quench), bath_target))
    swapped = t_hold is None  # single stage: nothing to swap to
    for i in range(1, t.size):
        dt = float(t[i] - t[i - 1])
        if (not swapped) and t[i] > t_hold:
            solver = Diffusion1D(grid, alpha, Neumann(0.0), Robin(h_eng(h_slow), T_env))
            swapped = True
        T = solver.step(T, dt)
        field[i] = T

    return SlabHistory(
        t=t, surface=field[:, -1].copy(), center=field[:, 0].copy(), T=field,
        half_thickness=half_thickness, t_hold=t_hold,
    )


@dataclass(frozen=True)
class DistortionComparison:
    """Direct-quench vs martemper through-section gradient at ``Mₛ`` — the distortion payoff.

    ``gradient_*`` are the surface−centre temperature differences (°C, signed: centre hotter ⇒
    negative) at the instant the surface reaches ``Mₛ``; ``reduction`` is the factor by which
    martempering shrinks that gradient's magnitude. The two :class:`SlabHistory` objects carry the
    full curves for the figure. The hardness comparison this rides alongside is "**the same as a
    direct quench would give, point-for-point**" (:func:`ideal_quench`), *not* a claim that the
    section fully through-hardens — a shallow steel in a thick section under-hardens at the centre in
    *both* routes; martempering removes the distortion, not the hardenability limit.
    """

    steel: str
    Ms: float
    T_bath: float
    half_thickness: float
    gradient_direct: float
    gradient_martemper: float
    reduction: float
    direct: SlabHistory
    martemper: SlabHistory


def distortion_comparison(
    steel: str,
    half_thickness: float,
    T_bath: float | None = None,
    t_hold: float | None = None,
    T0: float = 850.0,
    h_quench: float = cooling.H_WATER,
    h_slow: float = cooling.H_AIR,
    T_env: float = 25.0,
) -> DistortionComparison:
    """Compare a direct quench and a martemper of the same slab — the surface−centre gradient at ``Mₛ``.

    Runs :func:`slab_thermal_history` twice (single-stage water quench; two-stage bath hold + slow
    cool) for a named atlas steel and reads :meth:`SlabHistory.gradient_at_surface_crossing` at the
    steel's Andrews ``Mₛ`` for each. ``T_bath`` defaults to ``Mₛ + 20`` °C (just inside the
    martempering window) and ``t_hold`` to a generous equalisation hold (several conduction times,
    well under 1080's huge ``t_crit``). The martemper gradient should be far smaller — that ratio is
    the quantitative reason martempering exists.
    """
    s = ATLAS_STEELS[steel]
    Ms = andrews_Ms(**s.comp)
    if T_bath is None:
        T_bath = Ms + 20.0
    if t_hold is None:
        # A generous equalisation hold: several conduction times so the section reaches the bath.
        t_hold = 6.0 * half_thickness**2 / (cooling.K_STEEL / (cooling.RHO_STEEL * cooling.CP_STEEL))

    direct = slab_thermal_history(
        half_thickness, T0, h_quench, T_bath, t_hold=None, T_env=T_env,
    )
    marte = slab_thermal_history(
        half_thickness, T0, h_quench, T_bath, t_hold=t_hold, h_slow=h_slow, T_env=T_env,
    )
    g_direct = direct.gradient_at_surface_crossing(Ms)
    g_marte = marte.gradient_at_surface_crossing(Ms)
    if not (math.isfinite(g_direct) and math.isfinite(g_marte)):
        reduction = float("nan")
    elif g_marte == 0.0:
        reduction = float("inf")
    else:
        reduction = abs(g_direct) / abs(g_marte)
    return DistortionComparison(
        steel=steel, Ms=Ms, T_bath=T_bath, half_thickness=half_thickness,
        gradient_direct=g_direct, gradient_martemper=g_marte, reduction=reduction,
        direct=direct, martemper=marte,
    )


# --------------------------------------------------------------------------- #
# 3. Feasibility: can the section equalise before bainite forms?
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Feasibility:
    """Whether a section can be martempered at ``T_bath`` — equalisation vs the bainite clock.

    ``tau_equalize`` is the time (s) for the slab centre to come within ``tol`` of the bath under
    the quench; ``t_crit`` the bainite-onset hold (:func:`critical_hold_time`). The condition
    ``tau_equalize < t_crit`` is a **conservative proxy**: it asks whether even the hold needed to
    *fully* equalise the section to the bath fits inside the bath's bainite budget. ``margin =
    t_crit / tau_equalize`` is the safety factor; ``biot`` flags the thermal regime (``> 0.1`` ⇒ a
    real through-section gradient — the distortion regime martempering targets). **Two named caveats:**
    (1) ``t_crit`` near ``Mₛ`` is optimistic (the unmodelled near-``Mₛ`` acceleration), so a thin
    margin should be read conservatively; (2) the *dominant* real martempering constraint —
    outrunning the pearlite/upper-bainite nose during the descent *to* the bath — is idealised away
    here (the quench-in is instantaneous, as in :mod:`austemper`), so this is the *hold*-side limit,
    not the whole story. The verdicts are robust: the contrast (thin feasible, deep-alloy thick
    infeasible) survives a fuller hold-plus-slow-cool-dwell accounting.
    """

    steel: str
    T_bath: float
    half_thickness: float
    tau_equalize: float
    t_crit: float
    margin: float
    biot: float
    feasible: bool


def feasibility(
    steel: str,
    half_thickness: float,
    T_bath: float | None = None,
    h_quench: float = cooling.H_WATER,
    T0: float = 850.0,
    tol_frac: float = 0.02,
) -> Feasibility:
    """Can a slab of ``half_thickness`` (m) be martempered at ``T_bath`` (°C)? — the equalise/bainite race.

    Computes the centre's equalisation time from the *actual* spatial solve
    (:func:`slab_thermal_history`, bath stage only) — the time for the centre to fall within
    ``tol_frac`` of the initial (T0→bath) gap above the bath — and compares it to
    :func:`critical_hold_time`. Tying feasibility to the engine's own thermal field (rather than a
    lumped formula) keeps it honest in the thick-section regime where the gradient — and so the
    distortion martempering fixes — actually lives.
    """
    s = ATLAS_STEELS[steel]
    Ms = andrews_Ms(**s.comp)
    if T_bath is None:
        T_bath = Ms + 20.0
    t_crit = critical_hold_time(steel, T_bath)

    # Bath stage only, long enough to equalise: hold the surface BC at the bath the whole march.
    alpha = cooling.K_STEEL / (cooling.RHO_STEEL * cooling.CP_STEEL)
    t_end = max(10.0 * half_thickness**2 / alpha,
                30.0 * cooling.lumped_time_constant(h_quench, half_thickness))
    hist = slab_thermal_history(
        half_thickness, T0, h_quench, T_bath, t_hold=None, T_env=T_bath, t_end=t_end,
    )
    equalize_T = T_bath + tol_frac * (T0 - T_bath)
    tau_equalize = hist.crossing_time("center", equalize_T)

    L_c = half_thickness
    biot = cooling.biot_number(h_quench, L_c)
    margin = t_crit / tau_equalize if math.isfinite(tau_equalize) and tau_equalize > 0.0 else float("inf")
    return Feasibility(
        steel=steel, T_bath=T_bath, half_thickness=half_thickness,
        tau_equalize=tau_equalize, t_crit=t_crit, margin=margin, biot=biot,
        feasible=(math.isfinite(tau_equalize) and tau_equalize < t_crit),
    )
