"""The ``Heat`` physical-state record + the thin orchestrator seam (Steel-making **F-spine**).

The **spine of the front end** (``docs/plans/steel-making.md`` §5, build-order item 2). Where each
F-phase (Ellingham, refining, ladle, casting) is one *step* with its own physics, this module is the
**carrier that flows between steps** and the **pattern by which a step composes** — the thing that
lets an upstream mistake *propagate* into a downstream consequence instead of being a disconnected
calculation. It is architecture, not a new physics phase: it reimplements nothing.

What it is — two pieces
-----------------------
1. **:class:`Heat` — the physical-state record.** A lightweight, **immutable** snapshot of a body of
   steel as it moves down the chain: its composition (wt %), dissolved gas, inclusions, temperature,
   grain size, residual stress, **defect flags**, and a **provenance trail** of the steps it has been
   through. It is **physics only** — cost, score, RNG, UI, and other game-layer state stay *out* of
   ``Heat`` (``steel-making.md`` §5), so it remains a candidate steel-sim datatype even if the game is
   later split out. Fields a not-yet-built phase would populate (dissolved O/N/H from F2, inclusions
   from F3, a cast residual field from F4) default to **``None`` = "no engine has produced this yet"** —
   the honest "unmeasured", distinct from a real zero.

2. **The thin orchestrator seam.** Functions like :func:`heat_treat` that **unpack** a ``Heat`` into
   the plain inputs an engine consumes, **call** the (frozen, untouched) engine, and **repack** the
   result back into a fresh ``Heat`` — appending one :class:`ProcessStep` to the trail and raising a
   defect flag when a state field crosses a spec threshold. The engines are never handed the ``Heat``
   and never mutate it; that loose-coupling boundary is the same one the back end keeps between
   ``engines/`` and ``steel/`` (``steel-production.md`` §5), and it is what keeps the frozen diffusion
   core reusable. The seam unpacks ``Heat`` → :class:`~steel.sweep.Steel` and calls the **public**
   composition function (:func:`~steel.sweep.evaluate`), which itself wraps the frozen array engine one
   level down — the orchestrator does *not* reach past it into the diffusion core.

Failure propagation — the point of the spine
--------------------------------------------
The hero chain (``steel-making.md`` §1/§6): *mis-set the alloy upstream → the part won't harden
downstream.* :func:`heat_treat` runs it for **any** composition: under-dose Cr/Mo in the ``Heat``'s
composition and the same oil quench lands a soft, ferrite-dominant core → the **soft-core** defect
flag is raised on the returned ``Heat`` and carried forward, with the step that caused it recorded in
the trail. No scripted "you failed" branch — the flag falls out of the back-end physics crossing a
spec line (``demo_heat_state.py`` shows a properly-dosed and an under-dosed 4140 diverging this way).

What is real here vs what is scaffolding — the honesty discipline
-----------------------------------------------------------------
* **No new physics, no cited constant, no triad.** This module computes no material behaviour; it
  threads state through engines that are *already* benchmarked. So its checks are **structural**, not a
  new benchmark (the same posture ``design.py`` takes for inverse design): the round-trip
  ``Steel → Heat → Steel`` preserves composition exactly, the record is immutable (every step returns a
  *new* ``Heat``), and a spec miss propagates to a flag deterministically. Those are the "teeth" — they
  catch a broken seam, not a wrong number.
* **The spec thresholds sit on the verified/game boundary.** :data:`MIN_MARTENSITE_SPEC` is a *design
  requirement* ("a part is through-hardened if ≥ 90 % of its core is martensite"), not a fitted physical
  constant — it is where "soft core" *begins*, editable per application, labelled as spec. The
  quench-crack criterion, by contrast, reuses the §18 engine's own physics-grounded
  :attr:`~steel.residual.ResidualStressField.crack_risk` (surface ends in tension) — no new threshold.
* **The residual / quench-crack link is a *fixed atlas-steel illustration*, not the off-spec chain.**
  The §18 residual engine is **name-keyed and guarded to the anchored atlas steels**
  (``residual.quench_residual_stress`` raises outside :data:`~steel.austemper.ATLAS_STEELS` = {1080,
  4340}); it takes a grade *name*, not a composition. So an *arbitrary off-spec composition →
  quench-crack* chain **cannot run today** — it is **deferred** until a composition-keyed residual path
  exists. :func:`quench_crack_check` demonstrates the *same repack pattern* for a fixed atlas grade, so
  the spine is shown composing across two different engines, honestly bounded. The general
  failure-propagation proof runs through :func:`heat_treat` (any composition).

Scope (build-order item 2): the carrier + the orchestrator pattern + a minimal propagation proof. The
§6 defect catalogue fills in **as engines land** (``steel-making.md`` §6) — it is not built here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import sweep
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Spec thresholds — the verified/game boundary (labelled spec, NOT fitted physics)
# --------------------------------------------------------------------------- #
# A *design requirement*, not a calibrated constant: "a part is through-hardened to spec when at least
# this fraction of its core shears to martensite." It sets where the **soft-core** failure begins and is
# editable per application — the back-end physics that computes the martensite fraction is what is
# benchmarked; this line is where we decide the result is unacceptable. (steel-making.md §6: failure =
# a state field crossing a spec threshold.)
MIN_MARTENSITE_SPEC: float = 0.90

# Defect-flag names — the failure carriers that ride in Heat.defects (steel-making.md §5/§6).
SOFT_CORE: str = "soft-core"                 # insufficient through-hardening (heat_treat, any composition)
QUENCH_CRACK_RISK: str = "quench-crack-risk"  # surface locked in tension (atlas-steel illustration)


# --------------------------------------------------------------------------- #
# 1. The provenance trail — one entry per step the Heat has been through
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProcessStep:
    """One entry in a :class:`Heat`'s process history — *what happened, and did it meet spec*.

    ``name`` the step ("heat-treat", "quench-crack-check", an origin "charge"); ``summary`` a
    human one-liner of the inputs and the physical outcome; ``in_spec`` whether the step's spec check
    passed (``None`` when the step does not spec-check anything); ``flags_added`` the defect flags this
    step raised (``()`` for a clean step). The trail is what makes failure propagation *visible*: it
    names the step where an off-spec state entered the ``Heat``.
    """

    name: str
    summary: str
    in_spec: bool | None = None
    flags_added: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# 2. The Heat physical-state record — the carrier (physics only; immutable)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Heat:
    """A body of steel as it flows through the production chain — the carrier of failure propagation.

    **Physics only** (``steel-making.md`` §5): composition and physical state, never game-layer cost /
    score / RNG / UI. **Immutable**: an orchestrator step never mutates a ``Heat``, it returns a *new*
    one (:meth:`evolve`) with one more :class:`ProcessStep` on the trail — so the history is a faithful,
    un-rewritable record.

    Fields
    ------
    ``composition`` — the wt-% vector, **the existing back-end** :class:`~steel.sweep.Steel` (not a
    parallel type): this *is* the seam to the back end, the object :func:`~steel.sweep.evaluate`
    consumes, so :meth:`as_steel` is a no-op unpack. ``temperature_C`` the body's current temperature
    (the *field* ``T(x)`` is an engine-internal array, never stored at rest — only its set point lives
    here). ``grain_size_um`` prior-austenite grain size (PAGS). ``oxygen_ppm`` / ``nitrogen_ppm`` /
    ``hydrogen_ppm`` dissolved gas (F2). ``inclusion_volume_fraction`` / ``inclusion_type`` (F3).
    ``residual_stress_MPa`` the locked-in surface residual (tensile +; §18 / F4). Each of these defaults
    to **``None`` = no engine has produced it yet** — the honest "unmeasured", which a phase that lands
    later will fill. ``defects`` the raised failure flags; ``history`` the provenance trail.
    """

    composition: Steel
    temperature_C: float | None = None
    grain_size_um: float | None = None
    oxygen_ppm: float | None = None
    nitrogen_ppm: float | None = None
    hydrogen_ppm: float | None = None
    inclusion_volume_fraction: float | None = None
    inclusion_type: str | None = None
    residual_stress_MPa: float | None = None
    defects: tuple[str, ...] = ()
    history: tuple[ProcessStep, ...] = field(default_factory=tuple)

    # -- the unpack to the back end (a no-op: composition already IS a Steel) --
    def as_steel(self) -> Steel:
        """The composition as the :class:`~steel.sweep.Steel` the back end consumes — the unpack seam.

        Identity, by construction: ``Heat(composition=s).as_steel() is s``. Because ``Heat`` *composes*
        the existing back-end carrier rather than duplicating its fields, the round trip
        ``Steel → Heat → Steel`` is exact — the structural tooth that the seam is non-lossy.
        """
        return self.composition

    # -- the immutable-update primitive: every step returns a fresh Heat ----------
    def evolve(self, step: ProcessStep, **changes) -> "Heat":
        """Return a **new** ``Heat`` with field ``changes`` applied and ``step`` appended to the trail.

        The single state-evolution primitive. Frozen, so the receiver is untouched; ``changes`` are the
        physical fields the step updated (any ``defects`` passed must be the already-merged tuple — use
        :func:`add_defect` to merge). This is how the orchestrator repacks an engine result.
        """
        return replace(self, history=self.history + (step,), **changes)

    @property
    def is_clean(self) -> bool:
        """``True`` when no defect flag has been raised on this ``Heat``."""
        return not self.defects

    def has_defect(self, name: str) -> bool:
        """Whether the named defect flag has been raised on this ``Heat``."""
        return name in self.defects

    def label(self) -> str:
        """A one-line description — the grade, plus any defect flags (the failure-state cue)."""
        base = self.composition.label()
        if self.defects:
            return f"{base} [{', '.join(self.defects)}]"
        return base

    @classmethod
    def from_grade(cls, grade: str, *, temperature_C: float | None = None) -> "Heat":
        """A ``Heat`` of a named back-end grade (:data:`~steel.sweep.STEELS`) — a stand-in chain origin.

        Until F2/F3/F4 (which would *produce* an on-spec composition by refining and trimming) are
        built, this seeds the chain as if the front end had already delivered the grade — with an origin
        :class:`ProcessStep` on the trail so provenance starts somewhere honest. Raises ``KeyError`` for
        an unknown grade.
        """
        if grade not in sweep.STEELS:
            raise KeyError(f"unknown grade {grade!r} — known: {sorted(sweep.STEELS)}")
        origin = ProcessStep("charge", f"charge grade {grade} (front-end-supplied stand-in)", in_spec=True)
        return cls(composition=sweep.STEELS[grade], temperature_C=temperature_C, history=(origin,))


def add_defect(defects: tuple[str, ...], name: str) -> tuple[str, ...]:
    """``defects`` with ``name`` appended if absent (no duplicates) — the flag-merge helper."""
    return defects if name in defects else defects + (name,)


# --------------------------------------------------------------------------- #
# 3. The orchestrator seam — unpack Heat → call frozen engine → repack into Heat
# --------------------------------------------------------------------------- #
def heat_treat(
    heat: Heat,
    *,
    medium: str | float = "oil",
    diameter: float = 0.010,
    austenitize_T: float = 850.0,
    bath_T: float = 25.0,
    min_martensite: float = MIN_MARTENSITE_SPEC,
) -> Heat:
    """Quench the ``Heat`` and read whether it through-hardened — the spine's failure-propagation seam.

    The thin orchestrator in one function: **unpack** ``heat`` → its :class:`~steel.sweep.Steel`,
    **call** the public back-end chain :func:`~steel.sweep.evaluate` (which builds the steel's C-curve
    from its composition, cools a ``diameter`` section in ``medium``, and integrates to a microstructure
    — wrapping the frozen array engine one level down), then **repack**: the body ends at ``bath_T``, and
    if the martensite fraction misses ``min_martensite`` the **soft-core** flag is raised and carried
    forward. The result is a *new* ``Heat`` with one :class:`ProcessStep` appended.

    This is the general path — it runs for **any** composition, which is why the propagation proof rides
    here: under-dose Cr/Mo upstream and this same call lands a soft core (``demo_heat_state.py``). The
    returned ``Heat`` records the cooling outcome in its trail; callers wanting the full
    :class:`~steel.sweep.Outcome` call :func:`~steel.sweep.evaluate` directly (the seam threads *state*,
    it does not replace the engine).
    """
    steel = heat.as_steel()
    outcome = sweep.evaluate(steel, medium=medium, diameter=diameter,
                             austenitize_T=austenitize_T, bath_T=bath_T)
    fM = outcome.result.martensite
    soft = fM < min_martensite

    defects = add_defect(heat.defects, SOFT_CORE) if soft else heat.defects
    flags_added = (SOFT_CORE,) if (soft and not heat.has_defect(SOFT_CORE)) else ()
    medium_label = medium if isinstance(medium, str) else f"h={medium:g}"
    summary = (
        f"{medium_label} quench Ø{diameter * 1000:g} mm → {fM:.0%} martensite, {outcome.HV:.0f} HV, "
        f"{outcome.dominant()}-dominant"
        + ("" if not soft else f" → SOFT CORE (spec ≥ {min_martensite:.0%} martensite)")
    )
    step = ProcessStep("heat-treat", summary, in_spec=not soft, flags_added=flags_added)
    return heat.evolve(step, temperature_C=bath_T, defects=defects)


def quench_crack_check(
    heat: Heat,
    half_thickness: float,
    *,
    grade: str | None = None,
    transform: bool = True,
) -> Heat:
    """Repack the §18 residual-stress solve into the ``Heat`` — the **fixed atlas-steel** illustration.

    Demonstrates the *same* unpack → engine → repack pattern for a second engine (the residual-stress
    solid mechanics), so the spine is shown composing across more than one step. The surface residual is
    repacked into ``residual_stress_MPa`` and, when the surface ends in **tension**
    (:attr:`~steel.residual.ResidualStressField.crack_risk`), the **quench-crack-risk** flag is raised.

    **Honest bound (``steel-making.md`` §6 deferral).** The §18 engine is name-keyed and guarded to the
    anchored atlas steels (:data:`~steel.austemper.ATLAS_STEELS` = {1080, 4340}) — it takes a *grade*,
    not a composition — so this is **not** the off-spec-composition → crack chain (that is deferred until
    a composition-keyed residual path exists). ``grade`` selects the atlas anchor (default: the ``Heat``'s
    composition name if it is an atlas grade); a non-atlas ``Heat`` raises ``ValueError``.
    """
    from .residual import quench_residual_stress  # local: pulls the §18 mechanics only when used
    from .austemper import ATLAS_STEELS

    grade = grade or heat.composition.name
    if grade not in ATLAS_STEELS:
        raise ValueError(
            f"quench_crack_check is the fixed atlas-steel illustration — needs an anchored grade "
            f"({sorted(ATLAS_STEELS)}), got {grade!r}. The off-spec-composition → crack chain is "
            f"deferred (steel-making.md §6); use heat_treat for the general propagation proof."
        )

    field_ = quench_residual_stress(grade, half_thickness, transform=transform)
    crack = field_.crack_risk
    defects = add_defect(heat.defects, QUENCH_CRACK_RISK) if crack else heat.defects
    flags_added = (QUENCH_CRACK_RISK,) if (crack and not heat.has_defect(QUENCH_CRACK_RISK)) else ()
    state = "TENSION → crack-risk" if crack else "compression (safe)"
    summary = (
        f"{grade} water quench, 2t={2 * half_thickness * 1000:g} mm → surface "
        f"{field_.surface_MPa:+.0f} MPa ({state})"
    )
    step = ProcessStep("quench-crack-check", summary, in_spec=not crack, flags_added=flags_added)
    return heat.evolve(step, residual_stress_MPa=field_.surface_MPa, defects=defects)
