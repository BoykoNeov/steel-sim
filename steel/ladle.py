"""Ladle metallurgy — alloy trim to a target grade (Steel-making **F3**, Slice 1).

The **seam to the back end** (``docs/plans/steel-making.md`` §7, build-order item 5). F1 reduced ore to
iron, F2 blew and killed the bath to its carbon, F4 casts the finished billet — and *this* module is the
ladle step where the heat is **trimmed to a grade** by ferroalloy additions. It is the phase that finally
**finalizes the composition vector the back end consumes**: where the spine and F2 *held the alloy fixed*
to isolate the carbon axis, F3 is where the Mn / Si / Cr / Mo / Ni actually go *in*. So its failure output
— a heat that misses the grade — is **the hero-demo input** the plan kept pointing at.

Two outputs on opposite sides of the verified/plausible line (as in F2)
----------------------------------------------------------------------
1. **The trim arithmetic — *structural*, not a physics benchmark.** There is no new thermodynamics here:
   sizing an addition is mass balance, ``addition = deficit / (alloy fraction × recovery)``, and mixing it
   in is more mass balance with a little dilution from the added mass. So — exactly like the
   :mod:`~steel.heat_state` spine — F3's own checks are **structural** (the inverse/forward round-trip is an
   identity, the element mass balance closes, the ``Heat`` is immutable), *labelled* as by-construction, not
   dressed up as teeth. The grade window itself is a **labelled spec** (like
   :data:`~steel.heat_state.MIN_MARTENSITE_SPEC` or F2's porosity line), a commercial chemistry tolerance —
   not a benchmark the model could fail.

2. **The off-grade → soft-core propagation — the *validated* link (the proof rides here).** The one piece
   that is genuinely validated is the same one the spine and F2 lean on: a composition error reaching the
   **already-benchmarked back end**. Under-trim the hardenability alloys (Cr/Mo) and the *same* oil quench
   that through-hardens a proper 4140 lands a soft, ferrite-leaning core — :func:`~steel.heat_state.heat_treat`
   raises **soft-core**, not because F3 scripted it but because the back-end martensite fraction crossed a
   spec line. F3's *new* contribution over the spine's hand-set under-dose: the under-dose is now **produced
   by a modeled ladle operation** — the additions were sized for an *assumed* recovery the bath did not
   deliver (the recovery shortfall *is* the failure mechanism, below).

The failure mechanism — recovery is the cited input *and* the thing that bites
------------------------------------------------------------------------------
Not all of a ferroalloy ends up in the steel. Some of the added element oxidizes into the slag or fumes off;
the fraction that reports to the bath is the **recovery** (yield) ``η``. Recovery is **practice-dependent**
— add silicon or manganese to an under-deoxidized bath and the dissolved oxygen (F2's residual!) eats them,
so ``η`` falls; add them to a well-killed bath and ``η`` is high. That is the whole point: the additions are
sized assuming a recovery, and a heat where the *actual* recovery comes in well below the assumed one lands
**short of the grade** — below the window, and (for Cr/Mo) into a back-end soft core. The tier-2 scatter in
the cited recovery factor is not a weakness to hide; it is the modeled mechanism by which a real ladle
misses spec. (This is the front-end consequence of F2's deox state — named here, the coupling deferred.)

What is CITED vs the named ceiling — the two-tier discipline (as in casting/refining)
------------------------------------------------------------------------------------
* **CITED, the robust tier — the grade windows.** The per-element composition bands (:data:`GRADE_WINDOWS`)
  are the standard SAE/AISI grade limits (SAE J404): 4140 C 0.38–0.43 / Mn 0.75–1.00 / Si 0.15–0.35 /
  Cr 0.80–1.10 / Mo 0.15–0.25, 8620 likewise. These are hard published facts. But they are used as a
  **labelled spec** (the window the trim must land in), not as teeth — a model that aims at the window and
  accounts for recovery lands inside it *by construction*.
* **CITED, the source-sensitive tier — the recovery factors and ferroalloy assays.** The recoveries ``η``
  (:data:`FERROALLOYS`) are **representative** practice values (Mn/Si ≈ 0.90, Cr ≈ 0.95, Mo/Ni ≈ 0.97);
  they scatter widely with deox state, timing, and bath temperature, so only the **ranking and the order**
  ("noble Mo/Ni recover near-fully, oxidizable Mn/Si less") are the read, never the last digit. The
  ferroalloy element fractions (FeMn ≈ 78 % Mn, FeSi75, FeCr ≈ 68 % Cr, FeMo ≈ 62 % Mo) are standard product
  assays.
* **The named ceiling.** Equilibrium / steady-state additions, never the *kinetics* of dissolution or
  flotation (the same transport wall F2 names). **Carbon is held on the F2-set axis**: the additions trim
  only the substitutional alloys, and on the **Slice-1 default** the only thing that touches carbon here is
  **dilution** by the added mass (computed exactly). (a) **Carbon carry-in is now built as an opt-in
  consequence** — high-carbon ferrochrome/ferromanganese carry ~6–8 % C, so a full 4140 trim with the
  high-carbon grades would add **~0.16 %C** (~40 % of 4140's carbon — :func:`carbon_pickup_pct` quantifies
  it; it is *why* low-carbon ferroalloys exist). ``mix(apply_carbon_pickup=True)`` applies it and
  :data:`LOW_CARBON_FERROALLOYS` is the lever; the carbon then crosses the grade's C band and the existing
  window machinery raises **off-grade on carbon** (the demonstrated propagation: the over-carbon heat is a
  harder steel — see :mod:`steel.demo_carbon_carry_in`). The Slice-1 clean axis is still the **default** (the
  trim only dilutes carbon). (b) The **deox-state-dependent recovery** above stays named, not built.
  **Phosphorus and sulphur are not in the window check** — the
  :class:`~steel.sweep.Steel` vector carries no P/S, so the residual-element bands (and desulf/dephos, which
  is also F2 Slice 2) are deferred until that state exists.

Units: wt % for composition, kg for ferroalloy charges and heat mass.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .heat_state import Heat, ProcessStep, add_defect
from .sweep import Steel, STEELS

# --------------------------------------------------------------------------- #
# Reference heat mass + the defect flag (the verified/game boundary)
# --------------------------------------------------------------------------- #
# A representative converter/ladle heat mass. Only the ratio of charge to heat mass matters for the
# resulting wt %, so this is a scale that makes the charges come out in readable kilograms (a ~3 t total
# trim on a 100 t heat) — not a pinned physical magnitude.
HEAT_MASS_KG: float = 100_000.0

# The off-grade flag — F3's labelled-spec failure carrier (rides Heat.defects, steel-making.md §5/§6). It is
# raised when the trimmed composition falls outside the cited grade window. Distinct from the *downstream*
# heat_state.SOFT_CORE the same under-trim triggers when the heat is later quenched: OFF_GRADE is F3's own
# front-end spec catch (an early warning), SOFT_CORE is the validated back-end consequence.
OFF_GRADE: str = "off-grade-composition"

# The substitutional alloys F3 trims (carbon is held on F2's axis; it only dilutes). The order is the
# strongest-hardenability-first reading order used in summaries.
TRIM_ELEMENTS: tuple[str, ...] = ("Mn", "Si", "Ni", "Cr", "Mo")


# --------------------------------------------------------------------------- #
# 1. The cited inputs — ferroalloys (assay + recovery) and the grade windows
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Ferroalloy:
    """A ferroalloy addition: its assay, its recovery, and the carbon it carries — cited inputs.

    ``element`` the alloying element it delivers; ``element_fraction`` the standard product assay (mass
    fraction of that element in the alloy — robust); ``recovery`` the **representative** fraction that
    reports to the steel (the source-sensitive tier — it scatters with deox state/timing); ``carbon_fraction``
    the carbon carried in (high-carbon FeMn/FeCr ≈ 6–8 % C) — *named, not applied* on the Slice-1 clean
    carbon axis (see :func:`carbon_pickup_pct`).
    """

    name: str
    element: str
    element_fraction: float
    recovery: float
    carbon_fraction: float = 0.0


# One ferroalloy per trimmed element (the simple Slice-1 case: distinct deliverers, no shared element).
# element_fraction = standard product assay; recovery = representative practice yield (tier-2: ranking, not
# the last digit); carbon_fraction = the HC carbon carry-in that the clean axis defers.
FERROALLOYS: dict[str, Ferroalloy] = {
    "Mn": Ferroalloy("high-carbon ferromanganese", "Mn", 0.78, 0.90, carbon_fraction=0.065),
    "Si": Ferroalloy("ferrosilicon (FeSi75)",      "Si", 0.75, 0.90, carbon_fraction=0.0),
    "Cr": Ferroalloy("high-carbon ferrochrome",    "Cr", 0.68, 0.95, carbon_fraction=0.070),
    "Mo": Ferroalloy("ferromolybdenum",            "Mo", 0.62, 0.97, carbon_fraction=0.0),
    "Ni": Ferroalloy("nickel",                     "Ni", 0.99, 0.97, carbon_fraction=0.0),
}

# The **low-carbon** ferroalloy set — *the same deliverers* (identical assay and recovery, so they size the
# trim identically), but **refined to low carbon**: low-carbon ferrochrome ≈ 0.5 % C and low-carbon /
# electrolytic ferromanganese ≈ 0.5 % C, versus the high-carbon (charge-chrome) grades' 6–8 % C above. They
# cost more — affining the carbon out of the alloy is the extra step — which is *why a heat that can tolerate
# the carry-in uses the cheap high-carbon grades and one that cannot must pay for these*. This set is the
# **lever** :func:`carbon_pickup_pct` and ``mix(apply_carbon_pickup=True)`` turn: with high-carbon alloys the
# trim drags carbon up off-grade; with these it does not. (FeSi / FeMo / Ni carry ~no carbon either way.)
LOW_CARBON_FERROALLOYS: dict[str, Ferroalloy] = {
    "Mn": replace(FERROALLOYS["Mn"], name="low-carbon ferromanganese", carbon_fraction=0.005),
    "Si": FERROALLOYS["Si"],
    "Cr": replace(FERROALLOYS["Cr"], name="low-carbon ferrochrome",    carbon_fraction=0.005),
    "Mo": FERROALLOYS["Mo"],
    "Ni": FERROALLOYS["Ni"],
}


@dataclass(frozen=True)
class GradeWindow:
    """A grade's per-element composition window (wt %) — the cited SAE/AISI spec bands.

    ``bands`` maps each element the :class:`~steel.sweep.Steel` vector carries to its ``(min, max)`` limit.
    Phosphorus and sulphur (max-only residual limits) are **omitted** — the vector carries no P/S (named
    deferral). The window is a **labelled spec**, the commercial chemistry tolerance, not a model benchmark.
    """

    name: str
    bands: dict[str, tuple[float, float]]


# Standard SAE J404 composition limits for the two demonstrator grades (C/Mn/Si/Ni/Cr/Mo only — P/S deferred).
GRADE_WINDOWS: dict[str, GradeWindow] = {
    "4140": GradeWindow("4140", {
        "C": (0.38, 0.43), "Mn": (0.75, 1.00), "Si": (0.15, 0.35), "Cr": (0.80, 1.10), "Mo": (0.15, 0.25),
    }),
    "8620": GradeWindow("8620", {
        "C": (0.18, 0.23), "Mn": (0.70, 0.90), "Si": (0.15, 0.35),
        "Ni": (0.40, 0.70), "Cr": (0.40, 0.60), "Mo": (0.15, 0.25),
    }),
}


# --------------------------------------------------------------------------- #
# 2. The mixing arithmetic — forward (exact, with dilution) and the inverse
# --------------------------------------------------------------------------- #
def mix(
    base: Steel, charges: dict[str, float], *, heat_mass: float = HEAT_MASS_KG,
    recovery: dict[str, float] | None = None,
    apply_carbon_pickup: bool = False, ferroalloys: dict[str, Ferroalloy] | None = None,
) -> tuple[Steel, float]:
    """Mix ``charges`` (kg of each ferroalloy by element) into ``base`` — the **exact** forward mass balance.

    Returns ``(new composition, new bath mass kg)``. For each addition the recovered element
    (``charge × assay × η``) enters the steel and the bath mass grows by the retained mass (the recovered
    element plus the iron carrier *and the carbon it carries*; only the *un*-recovered element is lost to
    slag). Every element's new wt % is ``100 × element mass / bath mass`` — so the added mass **dilutes** the
    untrimmed elements (carbon drops a touch), which is the "mixing/dilution exact" leg, captured rather than
    ignored. ``recovery`` overrides the ferroalloys' nominal ``η`` per element (this is how a heat that
    *under*-recovers is mixed: size the charges for the assumed ``η``, mix them at the actual ``η``).

    ``apply_carbon_pickup`` turns on the **carbon carry-in** consequence: with it set, the carbon the
    ferroalloys carry (``Σ charge × carbon_fraction``, recovered ~fully — carbon does not oxidize off like the
    alloying element does) is added to the bath's carbon, so a high-carbon trim drags carbon **up** (net of
    dilution). It defaults **off** — the Slice-1 clean axis where carbon is held on F2's blow and the trim
    only dilutes it. ``ferroalloys`` selects the set whose ``carbon_fraction`` (and assay/recovery) is read —
    :data:`FERROALLOYS` (high-carbon) by default, :data:`LOW_CARBON_FERROALLOYS` for the refined grades that
    carry the trim without blowing the carbon. The carbon mass is *already* in ``bath`` (it rode in as part of
    the non-recovered alloy mass); ``apply_carbon_pickup`` only re-attributes it from inert carrier to carbon.
    """
    fas = ferroalloys or FERROALLOYS
    rec = {**{e: fa.recovery for e, fa in fas.items()}, **(recovery or {})}
    bath = heat_mass
    for e, a in charges.items():
        fa = fas[e]
        bath += a * (1.0 - fa.element_fraction * (1.0 - rec[e]))   # retained = recovered element + Fe carrier

    def new_pct(el: str, pct: float) -> float:
        mass = heat_mass * pct / 100.0
        if el in charges:
            fa = fas[el]
            mass += charges[el] * fa.element_fraction * rec[el]
        if el == "C" and apply_carbon_pickup:
            mass += sum(a * fas[e].carbon_fraction for e, a in charges.items())
        return 100.0 * mass / bath

    trimmed = replace(
        base,
        C=new_pct("C", base.C), Mn=new_pct("Mn", base.Mn), Si=new_pct("Si", base.Si),
        Ni=new_pct("Ni", base.Ni), Cr=new_pct("Cr", base.Cr), Mo=new_pct("Mo", base.Mo),
    )
    return trimmed, bath


def additions_for_grade(
    base: Steel, aim: Steel, *, heat_mass: float = HEAT_MASS_KG, recovery: dict[str, float] | None = None,
) -> dict[str, float]:
    """Charges (kg per element) that bring ``base`` up to ``aim`` for each trimmed element — the **inverse**.

    The dilution-aware closed form: each element's balance is ``aim·W' = base·W + a·assay·η`` and the bath
    mass ``W' = W + Σ aᵢ·(retainedᵢ)`` — substituting gives ``W'`` in closed form, then each charge. Only
    elements where ``aim > base`` (and that have a ferroalloy) are trimmed; carbon is never trimmed (it is
    held on F2's axis). By construction :func:`mix` of this result reproduces ``aim`` for the trimmed
    elements — that round-trip is a **structural identity**, not a benchmark (forward and inverse are the
    same mass balance read two ways; see the test module's honesty note).
    """
    rec = {**{e: fa.recovery for e, fa in FERROALLOYS.items()}, **(recovery or {})}
    base_d = {"Mn": base.Mn, "Si": base.Si, "Ni": base.Ni, "Cr": base.Cr, "Mo": base.Mo}
    aim_d = {"Mn": aim.Mn, "Si": aim.Si, "Ni": aim.Ni, "Cr": aim.Cr, "Mo": aim.Mo}
    trimmed = [e for e in TRIM_ELEMENTS if aim_d[e] - base_d[e] > 1e-9 and e in FERROALLOYS]

    num, den = 1.0, 1.0
    for e in trimmed:
        fa = FERROALLOYS[e]
        delta = fa.element_fraction * rec[e]                       # element delivered per kg charge
        rho = 1.0 - fa.element_fraction * (1.0 - rec[e])           # bath mass added per kg charge
        num -= rho * base_d[e] / (100.0 * delta)
        den -= rho * aim_d[e] / (100.0 * delta)
    bath = heat_mass * num / den

    charges: dict[str, float] = {}
    for e in trimmed:
        fa = FERROALLOYS[e]
        delta = fa.element_fraction * rec[e]
        charges[e] = (aim_d[e] * bath - base_d[e] * heat_mass) / (100.0 * delta)
    return charges


def slag_loss(charges: dict[str, float], *, recovery: dict[str, float] | None = None) -> dict[str, float]:
    """The mass (kg) of each element lost to slag/fume during ``charges`` — the un-recovered fraction.

    ``loss = charge × assay × (1 − η)``: the part of the added element that did not report to the steel.
    Used by the conservation check (added element = recovered into steel + lost to slag).
    """
    rec = {**{e: fa.recovery for e, fa in FERROALLOYS.items()}, **(recovery or {})}
    return {e: charges[e] * FERROALLOYS[e].element_fraction * (1.0 - rec[e]) for e in charges}


def carbon_pickup_pct(
    charges: dict[str, float], *, heat_mass: float = HEAT_MASS_KG,
    ferroalloys: dict[str, Ferroalloy] | None = None,
) -> float:
    """The carbon (wt %) the ferroalloys in ``charges`` carry into the heat — ``Σ charge × carbon_fraction``.

    Over the heat mass. With the default high-carbon set (:data:`FERROALLOYS`) a full 4140 trim carries
    **~0.16 %C** — roughly 40 % of the grade's carbon, and exactly why low-carbon ferroalloys exist; with
    :data:`LOW_CARBON_FERROALLOYS` it is an order of magnitude less. This is the **magnitude** behind the
    carry-in consequence — an order-of-magnitude coherence number from representative assays, not a 2-sig-fig
    benchmark. :func:`mix` applies it only when ``apply_carbon_pickup=True`` (the Slice-1 default holds carbon
    on F2's axis); this function quantifies it either way.
    """
    fas = ferroalloys or FERROALLOYS
    return sum(a * fas[e].carbon_fraction for e, a in charges.items()) / heat_mass * 100.0


# --------------------------------------------------------------------------- #
# 3. The grade window — membership (the labelled spec)
# --------------------------------------------------------------------------- #
def in_window(comp: Steel, grade: str) -> dict[str, bool]:
    """Per-element ``{element: within its band}`` for ``comp`` against ``grade``'s window (the spec check)."""
    window = GRADE_WINDOWS[grade]
    values = {"C": comp.C, "Mn": comp.Mn, "Si": comp.Si, "Ni": comp.Ni, "Cr": comp.Cr, "Mo": comp.Mo}
    return {el: lo <= values[el] <= hi for el, (lo, hi) in window.bands.items()}


def off_grade_elements(comp: Steel, grade: str) -> list[str]:
    """The elements of ``comp`` that fall **outside** ``grade``'s window (empty ⇒ on grade)."""
    return [el for el, ok in in_window(comp, grade).items() if not ok]


def is_on_grade(comp: Steel, grade: str) -> bool:
    """Whether ``comp`` lands inside *every* band of ``grade``'s window."""
    return not off_grade_elements(comp, grade)


# --------------------------------------------------------------------------- #
# 4. The orchestrator seam — a lean tap, trimmed to grade (with the recovery failure)
# --------------------------------------------------------------------------- #
def from_tap(
    grade: str, *, carbon: float | None = None,
    Mn: float = 0.15, Si: float = 0.05, Cr: float = 0.05, Mo: float = 0.0, Ni: float = 0.0,
) -> Heat:
    """An **alloy-lean tap** ``Heat`` of ``grade`` — the post-refining chain origin F3 trims up to grade.

    Where the spine's :meth:`~steel.heat_state.Heat.from_grade` seeded the chain with the *finished* grade as
    a stand-in, this is a real F3 origin: a BOF/EAF tap that is **on carbon** (set by F2's blow — defaults to
    the grade's nominal) but **lean in the alloys** (residual Mn/Si, ~no Cr/Mo/Ni) — the heat as it arrives
    at the ladle, waiting to be trimmed. The composition keeps the grade's ``name`` so the window check knows
    the target; the trail starts with a ``"tap"`` step.
    """
    aim = STEELS[grade]
    C = aim.C if carbon is None else carbon
    comp = Steel(C=C, Mn=Mn, Si=Si, Ni=Ni, Cr=Cr, Mo=Mo, name=grade)
    origin = ProcessStep(
        "tap",
        f"alloy-lean {grade} tap (C {C:.2f} % on the F2 blow; Mn {Mn:.2f}, Si {Si:.2f}, "
        f"Cr {Cr:.2f} — to be trimmed to grade)",
        in_spec=True,
    )
    return Heat(composition=comp, temperature_C=1600.0, history=(origin,))


def trim_to_grade(
    heat: Heat, grade: str, *, heat_mass: float = HEAT_MASS_KG,
    recovery: dict[str, float] | None = None, actual_recovery: dict[str, float] | None = None,
    apply_carbon_pickup: bool = False, ferroalloys: dict[str, Ferroalloy] | None = None,
) -> Heat:
    """Trim ``heat`` to ``grade`` by ferroalloy additions — sized for ``recovery``, delivered at ``actual``.

    The ladle operation as one seam: size the charges to reach the grade's nominal alloy content assuming
    ``recovery`` (:func:`additions_for_grade`), then mix them in at ``actual_recovery``
    (:func:`mix`) and repack the trimmed composition into a new ``Heat`` with a ``"trim"`` step.
    When the additions are sized and delivered at the same recovery (``actual_recovery=None``) the heat lands
    **on grade**; when the bath delivers *less* than assumed (an under-killed bath eats the Cr/Mn — the F2
    deox-state coupling), the heat lands **short**, outside the window, and the **off-grade** flag is raised.

    The off-grade flag is F3's own labelled-spec catch (the cited grade window). The *downstream* consequence
    of an under-trim — a soft core when the heat is quenched — is **not** flagged here: it rides the existing
    :func:`~steel.heat_state.heat_treat` seam (the validated propagation), the same way F2's over-blow carbon
    does. So an under-trimmed Cr/Mo heat carries **two** flags by the time it is treated: off-grade (F3) and
    soft-core (back end) — the front-end early warning and the validated consequence of one mistake.

    ``apply_carbon_pickup`` / ``ferroalloys`` route the **carbon carry-in** consequence (:func:`mix`): with
    high-carbon ferroalloys (default set) and the pickup on, the trim drags carbon up off the grade's C band —
    a *different* ladle mistake than the recovery shortfall, fixed by paying for :data:`LOW_CARBON_FERROALLOYS`.
    The off-grade flag then fires on **carbon** through the same window machinery; see :mod:`steel.demo_carbon_carry_in`.
    """
    aim = STEELS[grade]
    charges = additions_for_grade(heat.composition, aim, heat_mass=heat_mass, recovery=recovery)
    trimmed, _ = mix(heat.composition, charges, heat_mass=heat_mass, recovery=actual_recovery or recovery,
                     apply_carbon_pickup=apply_carbon_pickup, ferroalloys=ferroalloys)
    trimmed = replace(trimmed, name=grade)

    off = off_grade_elements(trimmed, grade)
    defects = add_defect(heat.defects, OFF_GRADE) if off else heat.defects
    flags_added = (OFF_GRADE,) if (off and not heat.has_defect(OFF_GRADE)) else ()
    charge_str = ", ".join(f"{e} {charges[e] / 1000.0:.2f} t" for e in TRIM_ELEMENTS if e in charges)
    summary = (
        f"trim to {grade}: add {charge_str} → Cr {trimmed.Cr:.2f}, Mo {trimmed.Mo:.2f}, Mn {trimmed.Mn:.2f} %"
        + ("" if not off else f" → OFF GRADE ({', '.join(off)} outside the {grade} window)")
    )
    step = ProcessStep("trim", summary, in_spec=not off, flags_added=flags_added)
    return heat.evolve(step, composition=trimmed, defects=defects)
