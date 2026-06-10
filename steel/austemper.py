"""Austempering: the isothermal bainite hold — the 6b reaction's valid home (Steel Phase 6d).

Phase 6b built the cited Li/KV :class:`~steel.kinetics.BainiteReaction` and then *proved*
it must stay out of the continuous-cooling race (:mod:`kinetics` §6 — at any 8620-safe scale a
competing bainite is inert, at any visible scale it is wrong). But the **isothermal hold** never
enters that race: quench *past* the pearlite nose, hold between ``Bs`` and ``Mₛ`` until the
austenite transforms to bainite, then cool. That is **austempering** — the industrially real use
of bainite (springs, clips, high-carbon strip; 1080 is *the* classic austempering steel) — and the
one configuration where the descoped 6b reaction becomes validly load-bearing. It completes the
simulator's process vocabulary: every existing recipe is a continuous-cooling route; this is the
missing hold-route.

The cited anchor — the US Steel atlas (the 2026-06-10 probe, banked)
--------------------------------------------------------------------
**Source (pinned, public domain):** US Steel, *Atlas of Isothermal Transformation Diagrams*
(1951); archive.org identifier ``atlas_of_isothermal_transformation_diagrams``. Steels: **1080**
p. 42 (C 0.79, Mn 0.76, ASTM grain size 6, austenitized 1650 °F) and **4340** p. 105 (C 0.42,
Mn 0.78, Ni 1.79, Cr 0.80, Mo 0.33, grain 7–8, 1550 °F). Atlas conventions (its front matter):
the *beginning* line ≈ **0.1 %** transformed; the dotted line = **50 %**. The machine read-offs
(printed 1-2-5 log-gridline fit, rms ≈ 1 px at ~173 px/decade) are pinned in
:data:`ATLAS_STEELS` — they are the contract the probe scripts (gitignored) reduced to.

**The probe's three-part verdict, which sets this module's whole shape:**

1. **Per-steel anchoring PASSES (~×1.3).** One scale fit at a single cited ``(T, t₅₀)`` point
   predicts that steel's austempering window: the ΔT¹·Arrhenius temperature *shape* of the Li/KV
   bainite rate is genuinely predictive (1080 50 %-line ×1.06 at the holdout temperatures — the
   Phase-6d teeth, :mod:`tests.test_austemper`).
2. **Cross-composition FAILS ×14–35, wrong-signed.** Cited ``BC`` says 4340 is ~7× *faster* than
   1080 (the carbon coefficient 10.18 dominates); the atlas measures 4340 ~4–5× *slower*. So
   **BC is never used for absolute cross-steel times** — each steel carries its own cited anchor,
   and the derived per-steel scales differ ×~40 (the documented negative, pinned by test).
3. **The 6b mechanism teeth survive, strengthened.** The atlas shows 4340's bainite retarded only
   ~4× while its pearlite is pushed ~10³× — the bay mechanism, measured. What fails is ``BC``'s
   carbon-vs-alloy *arithmetic* for absolute cross-steel times, not the Cr/Mo-weak-on-bainite story.

Cited vs calibrated (the discipline, and the named step down)
-------------------------------------------------------------
* **CITED** — the atlas read-off table (:data:`ATLAS_STEELS`), the ΔT¹ / Q = 27 500 cal/mol rate
  shape (Li 1998, already pinned by 6b), the Steven–Haynes ``Bs``, Andrews ``Mₛ``,
  Koistinen–Marburger.
* **CALIBRATED** — **one scale per steel**, each derived *at import* (:func:`anchored_reaction`)
  from a single cited ``(T_anchor, t₅₀)`` atlas point — never a stored magic number. This is a
  **named discipline step down** from 6a's one-global-knob: the model contributes the
  (holdout-proven) temperature *shape*; the absolute time base comes from the per-steel anchor —
  the same epistemic shape as Jominy's Grossmann calibration, narrowed to per-steel because the
  probe falsified any global scale (verdict 2).

Named scope edges (each is a measured probe fact, not a guess)
--------------------------------------------------------------
* **Claims stop at the 50 % line.** The model's begin→50 % spacing is ×39.5 where the atlas
  measures ×9.5–14 (the KV ``g(U)`` late-stage vs the atlas's begin-sensitivity ambiguity), and
  4340's hours-long completion-stasis tail makes full-completion times indefensible. The begin
  line is used only as a *shape* (ratio) check; the recipe's quantitative claim is the 50 % line.
* **Near-Mₛ acceleration is unmodeled** (1080 @ 260 °C runs ×2.9): holds close above ``Mₛ`` are
  qualitative.
* **The model nose sits ~28 °C high** (4340: 458 °C vs ~430 °C measured).
* **Bainite hardness is the carbon-only placeholder, now load-bearing** for the first time
  (:func:`~steel.properties.vickers_bainite`): fine for the plain-carbon 1080 headline
  recipe, under-ranks alloyed bainite (4340) — named, not fixed (Maynier's bainite terms still
  cannot graft, :mod:`properties`).
* **Steven–Haynes ``Bs`` is extrapolated beyond its 0.55 %C fit range for 1080** (it works:
  548 °C, consistent with the atlas's bainite band).
* **Upper/lower bainite morphology and the toughness benefit are narrated, not computed.**
* **Not in scope:** any :mod:`pathint`/CCT wiring (the 6b negative result is load-bearing and
  untouched — `pathint` stays byte-identical), martempering (the same hold machinery is the seam
  — noted, not built), Maynier bainite hardness terms.

The recipe's idealizations (named)
----------------------------------
The quench to the hold is **instantaneous** (a salt-bath quench outruns the pearlite nose by
construction; the path *to* the hold contributes nothing). The un-modeled **pearlite race** at
the hold is *policed*, not modeled: the existing single-curve fictitious time
(:meth:`~steel.kinetics.CCurve.fraction`) is integrated through the live part of the
hold and a warning raised when it is non-negligible — loud for high holds near ``Bs`` (where the
real ferrite/pearlite reactions compete), silent in the anchored austempering band. Bainite
carbon partitioning into the remaining austenite (which raises real retained γ) is not modeled;
KM runs at the steel's bulk-composition ``Mₛ``.

Units: °C, seconds, wt%, mass fractions in [0, 1] — matching :mod:`kinetics`/:mod:`pathint`.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, replace

import numpy as np

from .kinetics import (
    BainiteReaction, bainite_reaction_for_steel, ccurve_for_steel,
    andrews_Ms, koistinen_marburger, _kv_shape_integral,
)
from .properties import hardness_HV, vickers_to_rockwell_c

# --------------------------------------------------------------------------- #
# 1. The cited atlas anchor table (the probe's read-off contract)
# --------------------------------------------------------------------------- #
ATLAS_SOURCE = ("US Steel, Atlas of Isothermal Transformation Diagrams (1951); "
                "archive.org: atlas_of_isothermal_transformation_diagrams")

# Atlas line conventions (its own front matter): the "beginning" line is ≈ 0.1 % transformed,
# the dotted line is 50 %. These are the completion fractions U the model maps those lines to.
ATLAS_BEGIN_X = 0.001
ATLAS_T50_X = 0.5


@dataclass(frozen=True)
class AtlasSteel:
    """One austempering-anchored steel: the cited atlas facts + the machine read-offs.

    ``comp`` is the atlas's reported composition (wt%), ``G`` its ASTM grain size, ``page`` the
    atlas page and ``austenitize_F`` its austenitizing temperature (°F, as printed). The anchor
    is the single cited ``(T_anchor °C, t50_anchor s)`` 50 %-line point the per-steel scale is
    derived from; ``begin`` / ``t50`` are the full machine read-off tables (°C → s) — the probe's
    contract, kept here so the holdout tests consume cited data, not re-reads.
    """

    name: str
    comp: dict
    G: float
    page: int
    austenitize_F: float
    T_anchor: float
    t50_anchor: float
    begin: dict
    t50: dict


ATLAS_STEELS = {
    # 1080 — *the* classic austempering steel (atlas p. 42; C 0.79, Mn 0.76, grain 6, 1650 °F).
    "1080": AtlasSteel(
        name="1080",
        comp=dict(C=0.79, Mn=0.76),
        G=6.0,
        page=42,
        austenitize_F=1650.0,
        T_anchor=371.1, t50_anchor=70.6,
        begin={435.3: 1.66, 398.9: 3.74, 371.1: 7.44, 343.3: 18.7,
               315.6: 48.0, 287.8: 96.0, 260.0: 140.0},   # 315.6 °C read ~48 s (dash-segment region)
        t50={396.7: 38.0, 371.1: 70.6, 343.3: 151.0},
    ),
    # 4340 — the deep-hardening alloy steel (atlas p. 105; grain 7–8 → 7.5, 1550 °F).
    "4340": AtlasSteel(
        name="4340",
        comp=dict(C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33),
        G=7.5,
        page=105,
        austenitize_F=1550.0,
        T_anchor=371.1, t50_anchor=391.0,
        begin={482.2: 18.7, 454.4: 13.0, 426.7: 12.7, 398.9: 18.9, 371.1: 28.0, 343.3: 33.5},
        t50={398.9: 315.0, 371.1: 391.0},
    ),
}


# --------------------------------------------------------------------------- #
# 2. Per-steel anchoring — scales derived at import, BainiteReaction unchanged
# --------------------------------------------------------------------------- #
def _derive_scale(steel: AtlasSteel) -> float:
    """The per-steel kinetic scale that puts the model's 50 %-line through the cited anchor.

    For the separable site-saturation reaction ``dU/dt = K(T)·g(U)`` the isothermal time to
    fraction ``X`` is ``t = S(X)/K(T)`` with ``S`` the shape integral
    (:func:`~steel.kinetics._kv_shape_integral`), and ``K`` is linear in the scale — so
    the anchored scale is solved exactly: ``scale = S(0.5) / (K_{scale=1}(T_anchor) · t₅₀)``.
    Derived, never stored: the cited inputs are the atlas anchor point and the Li/KV rate form.
    """
    base = bainite_reaction_for_steel(**steel.comp, G=steel.G)
    K_unit = base.rate(steel.T_anchor) / base.scale          # the scale-1 rate at the anchor
    return _kv_shape_integral(ATLAS_T50_X) / (K_unit * steel.t50_anchor)


def anchored_reaction(steel: str) -> BainiteReaction:
    """The atlas-anchored :class:`BainiteReaction` for a named steel (``"1080"`` / ``"4340"``).

    The 6b reaction object, unchanged, with its ``scale`` replaced by the per-steel anchored
    value (:data:`ANCHORED_SCALES`). Everything else — ``Bs`` (Steven–Haynes from the atlas
    composition), ``BC``, the atlas grain size ``G`` — is cited. The 6b module-level
    ``BAINITE_KINETIC_SCALE`` demonstration default is untouched.
    """
    s = ATLAS_STEELS[steel]
    return replace(bainite_reaction_for_steel(**s.comp, G=s.G), scale=ANCHORED_SCALES[steel])


# Derived at import (the "no stored magic numbers" rule): 1080 ≈ 6.8e3, 4340 ≈ 1.7e2 — the ×~40
# scale gap IS the probe's cross-composition negative result, pinned by test, never bridged by BC.
ANCHORED_SCALES = {name: _derive_scale(s) for name, s in ATLAS_STEELS.items()}


def hold_time_to_fraction(steel: str, T_hold: float, X: float) -> float:
    """Isothermal time (s) for the anchored reaction to reach completion ``X`` at ``T_hold`` (°C).

    ``t = S(X)/K(T_hold)`` — the separable exact time, the same identity the anchoring inverts
    (so at ``(T_anchor, 0.5)`` it returns the cited ``t₅₀`` by construction). ``inf`` at/above
    ``Bs``. This is the model's TTT line for any fraction: ``X = ATLAS_T50_X`` is the validated
    50 % line, ``X = ATLAS_BEGIN_X`` the begin line (shape-only — see the module scope edges).
    """
    K = anchored_reaction(steel).rate(T_hold)
    return math.inf if K <= 0.0 else _kv_shape_integral(X) / K


# --------------------------------------------------------------------------- #
# 3. The austemper recipe — quench, hold, cool
# --------------------------------------------------------------------------- #
# Warn when the un-modeled diffusional competitor (the project single curve's fictitious time,
# integrated through the live part of the hold) exceeds this fraction — the pearlite-race police.
PEARLITE_SHADOW_WARN = 0.15
# The hold is "done" (the race window closes, the long-hold cap is reached) at this completion.
HOLD_COMPLETE_X = 0.99


@dataclass(frozen=True)
class AustemperResult:
    """The microstructure + hardness an austempering hold produces (fractions sum to 1).

    ``bainite`` is the anchored isothermal product ``U(t_hold)``; ``martensite`` /
    ``retained_austenite`` are the Koistinen–Marburger fate (at ``T_quench``) of the austenite
    the hold left untransformed. ``pearlite_shadow`` is the policing diagnostic — the existing
    single-curve fictitious-time fraction over the live race window (NOT subtracted from the
    products; the race is policed, not modeled) — with ``pearlite_race_flagged`` set when it
    crossed :data:`PEARLITE_SHADOW_WARN`. ``t``/``U`` are the hold history (s, completion) for
    the mechanism view. ``HV`` is the rule-of-mixtures hardness (bainite = the carbon-only
    placeholder, named); ``HRC`` is ``nan`` off the Rockwell-C scale.
    """

    steel: str
    T_hold: float
    t_hold: float
    Bs: float
    Ms: float
    bainite: float
    martensite: float
    retained_austenite: float
    HV: float
    HRC: float
    pearlite_shadow: float
    pearlite_race_flagged: bool
    T_quench: float
    t: np.ndarray
    U: np.ndarray

    def fractions(self) -> dict:
        """The product fractions as a dict — the same stable key set :mod:`pathint` emits.

        ``ferrite``/``pearlite`` are structurally 0 here (the quench is idealized instantaneous
        and the pearlite race is policed, not modeled), so property consumers index the familiar
        five keys without special-casing the hold route.
        """
        return {
            "ferrite": 0.0,
            "pearlite": 0.0,
            "bainite": self.bainite,
            "martensite": self.martensite,
            "retained_austenite": self.retained_austenite,
        }

    def dominant(self) -> str:
        """Name of the largest-fraction product — the headline microstructure."""
        return max(self.fractions().items(), key=lambda kv: kv[1])[0]


def austemper(
    steel: str, T_hold: float, t_hold: float,
    T_quench: float = 25.0, n_steps: int = 6000,
) -> AustemperResult:
    """Austemper a named steel: instant quench to ``T_hold`` (°C), hold ``t_hold`` (s), cool.

    The Phase-6d recipe, composed entirely of existing validated pieces:

    1. **Quench** — idealized instantaneous to the hold (named; a salt bath outruns the pearlite
       nose by construction, so the path down contributes nothing).
    2. **Hold** — the anchored :class:`~steel.kinetics.BainiteReaction` advances its
       completion ``U`` by the existing ``completion_step`` (the 6b stepper, unchanged) on a
       uniform grid; the final ``U`` is the bainite fraction. The **holdout-proven** content is
       the 50 %-line position across the austempering band (the Phase-6d teeth).
    3. **Cool** — the remaining austenite ``(1 − U)`` shears per Koistinen–Marburger at
       ``T_quench`` (Andrews ``Mₛ`` from the atlas composition), the rest staying retained γ —
       exactly :mod:`pathint`'s bookkeeping, so fractions sum to 1 by construction.
    4. **Hardness** — the existing rule-of-mixtures blend (:func:`~steel.properties
       .hardness_HV`) with the atlas composition's minor-alloy terms; **bainite is the
       carbon-only placeholder, now load-bearing** (named — fine for plain-carbon 1080,
       under-ranks alloyed bainite).

    **Guards:** ``T_hold`` must sit strictly inside the austempering window ``Mₛ < T_hold < Bs``
    — at/above ``Bs`` the bainite reaction is inert (that hold is an anneal, not austempering),
    at/below ``Mₛ`` martensite forms on the way in (martempering — the same hold machinery is
    the seam, deliberately not built). Both refuse with ``ValueError``. The un-modeled
    **pearlite race** is policed: the existing single-curve fictitious time is integrated
    through the live race window (the hold until bainite completion caps it — once the austenite
    is consumed there is no competitor left to race) and a ``UserWarning`` raised above
    :data:`PEARLITE_SHADOW_WARN` — loud near ``Bs``, silent in the anchored band.
    """
    if steel not in ATLAS_STEELS:
        raise ValueError(f"no atlas anchor for steel {steel!r} — anchored: {sorted(ATLAS_STEELS)}")
    if t_hold <= 0.0:
        raise ValueError(f"hold time must be > 0 s, got {t_hold}")
    s = ATLAS_STEELS[steel]
    br = anchored_reaction(steel)
    Ms = andrews_Ms(**s.comp)
    if T_hold >= br.Bs:
        raise ValueError(
            f"T_hold = {T_hold:.0f} °C is at/above Bs = {br.Bs:.0f} °C — the bainite reaction is "
            f"inert there (not an austempering hold)")
    if T_hold <= Ms:
        raise ValueError(
            f"T_hold = {T_hold:.0f} °C is at/below Ms = {Ms:.0f} °C — martensite forms on the way "
            f"in (martempering, not modeled)")

    # The hold: the 6b stepper, anchored. Uniform grid (a hold has no decades to span).
    t = np.linspace(0.0, t_hold, n_steps + 1)
    dt = t_hold / n_steps
    U = np.empty_like(t)
    U[0] = 0.0
    for i in range(1, t.size):
        U[i] = br.completion_step(U[i - 1], T_hold, dt)
    f_bainite = float(U[-1])

    # The pearlite-race police: the existing single-curve fictitious time at the hold (at a
    # constant T that is just the Avrami fraction), integrated over the LIVE race window — the
    # hold, capped at bainite completion (a competitor cannot race for austenite that is gone).
    # Recorded always, warned only when non-negligible. NOT subtracted: policed, not modeled.
    cc = ccurve_for_steel(**s.comp)
    t_race = min(t_hold, hold_time_to_fraction(steel, T_hold, HOLD_COMPLETE_X))
    pearlite_shadow = float(cc.fraction(T_hold, t_race))
    flagged = pearlite_shadow > PEARLITE_SHADOW_WARN
    if flagged:
        warnings.warn(
            f"high hold: the un-modeled diffusional competitor would reach "
            f"{pearlite_shadow:.0%} (project single-curve fictitious time) during the live hold "
            f"window at {T_hold:.0f} °C — the bainite-only claim is unreliable this close to Bs "
            f"= {br.Bs:.0f} °C", UserWarning, stacklevel=2)

    # The final cool: KM on the remainder at the quench-out temperature (pathint's bookkeeping).
    f_km = koistinen_marburger(T_quench, Ms)
    remainder = 1.0 - f_bainite
    martensite = remainder * f_km
    retained = remainder * (1.0 - f_km)

    fractions = {
        "ferrite": 0.0, "pearlite": 0.0, "bainite": f_bainite,
        "martensite": martensite, "retained_austenite": retained,
    }
    comp_minor = {el: wt for el, wt in s.comp.items() if el != "C"}
    HV = hardness_HV(fractions, s.comp["C"], comp=comp_minor)

    return AustemperResult(
        steel=steel, T_hold=T_hold, t_hold=t_hold,
        Bs=br.Bs, Ms=Ms,
        bainite=f_bainite, martensite=martensite, retained_austenite=retained,
        HV=HV, HRC=float(vickers_to_rockwell_c(HV)),
        pearlite_shadow=pearlite_shadow, pearlite_race_flagged=flagged,
        T_quench=T_quench, t=t, U=U,
    )


def minimum_full_hold(steel: str, T_hold: float, X: float = HOLD_COMPLETE_X) -> float:
    """The shortest hold (s) that fully transforms — ``t`` to completion ``X`` at ``T_hold``.

    The "find the minimum full-transform hold" readout (the notebook/app exercise): below it the
    leftover austenite shears to (brittle, untempered) martensite on the final cool; beyond it
    the hold buys nothing. Just :func:`hold_time_to_fraction` at the completion cap.
    """
    return hold_time_to_fraction(steel, T_hold, X)
