"""Fracture-side coupling — the inclusion as the **quench-crack initiator** (Steel B1, the one new-physics thread).

Every consequence module so far read one axis. This one **couples two**: the **residual-stress field**
(:mod:`steel.residual`, §18) — consumed directly as code — and a **cleanliness** axis, represented here as a
worst-case surface-flaw size ``√area``. On its own, a tensile residual surface is only a *risk*; on its own,
a non-metallic inclusion is only a defect. A **quench crack** is what happens when the two meet: a flaw large
enough, in a surface tensile enough, that linear-elastic fracture mechanics says a crack will run.

**Scope of the cleanliness axis (read this — it is the honest bound of the coupling).** ``√area`` is a
**representative input**, not derived from the repo's inclusion engines. Two named cleanliness classes
(:data:`SQRT_AREA_CLEAN_UM` / :data:`SQRT_AREA_DIRTY_UM`) stand in for "the largest surface flaw a clean vs a
dirty heat carries". Wiring the *actual* inclusion models (:func:`steel.slag.manganese_sulfide`'s MnS volume,
:mod:`steel.sulfide_morphology`, :attr:`steel.heat_state.Heat.inclusion_volume_fraction`) into ``√area`` is a
**named deferral** — and deliberately *not* faked: a **bulk volume fraction is not a largest-flaw size**, and
the scales do not line up (single micro-inclusions are ~10–50 µm, whereas the ``√area`` that actually
discriminates here is *hundreds* of µm — inclusion *clusters* / exogenous reoxidation defects / segregated
stringer colonies). A vol%→``√area`` bridge would therefore be a *tuned* number, not a physical one, so it is
left as an explicit extension rather than manufactured. The coupling this module *does* make is **residual
stress × a representative flaw**; the flaw's provenance is honest about being a knob.

The gate (linear-elastic fracture mechanics)
--------------------------------------------
A pre-existing flaw of effective size ``√area`` under a tensile stress ``σ`` carries a **stress intensity**.
For a *small* defect Murakami's form (the standard small-defect / inclusion model) is

    K = Y · σ · √(π · √area),     Y = 0.65 (surface defect), 0.50 (interior),

and a crack runs when ``K ≥ K_Ic`` — the **fracture toughness** of the surface martensite. Equivalently
there is a **critical flaw size**

    √area_c = (1/π) · (K_Ic / (Y·σ))²,

below which any flaw is sub-critical (no crack) and above which it propagates. The quench-crack verdict is
therefore a **two-factor AND**: the surface must be in **tension** (σ > 0, from the residual solve) **and**
the largest flaw must exceed ``√area_c`` (from the cleanliness class). Either alone is not enough.

Why this is not a relabel of ``residual.crack_risk`` (the load-bearing design call)
-----------------------------------------------------------------------------------
:attr:`steel.residual.ResidualStressField.crack_risk` (and :func:`steel.heat_state.quench_crack_check` →
``quench-crack-risk``) already return *surface in tension*. This module earns its keep only if the
**inclusion is load-bearing** — i.e. the *same* residual field gives a crack for a dirty heat and no crack
for a clean one. So it follows the repo's **two-tier idiom** (cf. ``hydrogen-flaking-RISK`` →
``hydrogen-flaking``):

* ``quench-crack-risk`` (existing, :mod:`steel.residual`) = surface tension — the **necessary** condition;
* ``quench-crack`` (new, here) = tension **AND** largest flaw > ``√area_c`` — the **realized** crack.

The hero (:func:`steel.demo_fracture`): thick 4340, one direct water quench, *one* residual field — a clean
heat (``√area ≈ 30 µm``) survives while a dirty heat (``√area ≈ 400 µm``) cracks. **Cleanliness decides**,
at the same section and hardness. Martempering the dirty part collapses the surface tension
(``√area_c → ∞``) and saves it — the §17/§18 route benefit carried into fracture.

The stress that drives it — why ``phase_split_yield`` is required
----------------------------------------------------------------
Residual stress is bounded by the yield strength, so at the residual engine's **default** single-yield cap
(``σ_Y,20 ≈ 400 MPa``) the surface tension is ≲ 400 MPa and ``√area_c`` is **millimetres** — far above any
inclusion, so single inclusions would *never* be critical and the gate would collapse to "never cracks".
That cap is :mod:`steel.residual`'s own **named scope edge** ("yield not phase-split → surface tension
capped at σ_Y,20"). The fracture coupling consumes the **phase-split** residual path
(:func:`steel.residual.quench_residual_stress` with ``phase_split_yield=True``): a hard as-quenched
martensite surface *holds* far higher tension (the soft hot core still yields to generate the mismatch), so
thick 4340 reaches ~900–1045 MPa and ``√area_c`` falls to ~150–370 µm — straddling realistic clean vs
dirty inclusions. (A *uniform* yield raise was tried and falsified — it stiffens the hot core, kills the
mismatch generator, and the residual relaxes to ~0; the *split* is the physical fix, standard in real
quench-residual FEM.)

Cited vs representative vs NO tooth (the honesty discipline)
------------------------------------------------------------
* **CITED (the load-bearing form).** ``K = Y·σ·√(πa)`` (Anderson, *Fracture Mechanics*); Murakami's √area
  small-defect model and the surface/interior geometry factors ``Y = 0.65 / 0.50`` (Murakami, *Metal
  Fatigue: Effects of Small Defects and Nonmetallic Inclusions*, 2002); the **form** "K_Ic falls as
  hardness/strength rises" for high-strength martensitic steel.
* **REPRESENTATIVE (named scope edges, NOT benchmarked).** The as-quenched-martensite ``K_Ic`` magnitude
  (notoriously scattered — temper, prior-austenite grain size, impurities all move it); the hard-martensite
  yield base (1.5 GPa, the residual edge); the clean / dirty ``√area`` populations. The **absolute**
  crack/no-crack threshold is doubly property-sensitive (σ capped at the representative martensite yield;
  ``√area_c ∝ K_Ic²``) — **not** benchmarkable, and the representative constants are chosen so ``√area_c``
  lands *between* the clean and dirty inclusion sizes. That is what makes the coupling *discriminate*; it is
  named here, not hidden.
* **NO claimable tooth.** The surface-sign reversal and the martemper benefit are **consumed** from
  :mod:`steel.residual`, downstream of its formula sign — they are *not* new teeth, and dressing them as
  such would be the manufactured-coherence trap. The one *candidate* real tooth — the emergent **carbon
  ranking** (more carbon → lower K_Ic [worse] *and* lower transformation dilatation → less σ [better]) — is
  **not isolable**: only two atlas steels exist (1080 / 4340) and they differ in alloying and section, so
  the two legs cannot be separated. Default **no tooth**, like the :mod:`steel.sulfide_morphology` /
  :mod:`steel.wootz` siblings. The checks are **structural / discriminating**: the two-factor straddle, the
  martemper-raises-``√area_c`` monotonicity, tension-required, and the ``K``↔``√area_c`` self-consistency.

Named ceilings (each a real limit, not hidden)
----------------------------------------------
* **Surface-initiated only.** The gate reads the *surface* tension against a *surface* geometry factor
  (Y = 0.65). Interior bursting / core-tension flaws (the thermal-only and martemper cases put the tension
  at the **core**, not the surface) are a separate problem — not modelled.
* **Atlas-steel-only.** Inherits :func:`steel.residual.quench_residual_stress`'s name-keyed guard
  (1080 / 4340). An arbitrary off-spec composition → crack chain stays deferred (the same bound as
  :func:`steel.heat_state.quench_crack_check`).
* **One representative flaw per heat, not an extreme-value distribution.** ``√area`` is a single
  representative "largest surface inclusion" for the cleanliness class, not a Murakami statistics-of-extremes
  fit over a control volume.
* **The cleanliness axis is not wired to the inclusion engines (named deferral).** ``√area`` is a passed
  representative input, not computed from :func:`steel.slag.manganese_sulfide` /
  :mod:`steel.sulfide_morphology` / :attr:`steel.heat_state.Heat.inclusion_volume_fraction`. A bulk volume
  fraction is not a largest-flaw size and the scales do not line up (see the scope note above), so the bridge
  is left explicit rather than tuned. The coupling is residual-stress × a representative flaw.
* **Static LEFM** — a one-shot initiation criterion, no R-curve, no short-crack correction, no
  residual-field redistribution once a crack starts.

Units: stress MPa (matching :mod:`steel.residual`'s ``*_MPa`` reporting), flaw size ``√area`` in **µm** at
the API (SI metres internally), fracture toughness ``K_Ic`` in **MPa·√m**, compositions wt %.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import residual
from .austemper import ATLAS_STEELS
from .heat_state import QUENCH_CRACK, Heat, ProcessStep, add_defect

# --------------------------------------------------------------------------- #
# 1. Cited geometry factors + representative material / cleanliness constants
# --------------------------------------------------------------------------- #
# Murakami small-defect geometry factor Y in K = Y·σ·√(π·√area): 0.65 for a *surface* defect, 0.50 for an
# interior one (Murakami 2002). This gate reads the SURFACE residual against a SURFACE flaw → 0.65.
MURAKAMI_Y_SURFACE: float = 0.65
MURAKAMI_Y_INTERIOR: float = 0.50

# Representative fracture toughness of *as-quenched* (untempered) martensite, MPa·√m. Genuinely low (brittle,
# untempered) — published values for high-strength martensitic steel scatter ~15–25 MPa·√m and FALL with
# hardness/carbon. REPRESENTATIVE (the same property-sensitive status as residual's σ_Y bases); the absolute
# crack threshold scales with K_Ic² (a named scope edge), so this is a ranking knob, never a benchmark.
K_IC_AS_QUENCHED_MPA: float = 18.0

# Representative "largest surface inclusion" √area for two cleanliness classes, µm. A clean, Ca-treated /
# vacuum-degassed heat keeps its largest surface inclusion small; a dirty / reoxidized / large-cast-section
# heat carries coarse oxide clusters. REPRESENTATIVE populations (a single flaw per class, not an
# extreme-value distribution — a named ceiling), chosen to straddle √area_c at thick-section stresses.
SQRT_AREA_CLEAN_UM: float = 30.0
SQRT_AREA_DIRTY_UM: float = 400.0


# --------------------------------------------------------------------------- #
# 2. The LEFM primitives (closed form — cited relations, no fit)
# --------------------------------------------------------------------------- #
def murakami_stress_intensity(
    surface_stress_MPa: float, sqrt_area_um: float, *, surface: bool = True
) -> float:
    """Stress intensity ``K`` (MPa·√m) of a ``√area`` flaw under a surface stress — Murakami's small-defect form.

    ``K = Y · σ · √(π · √area)`` with ``Y = 0.65`` for a surface defect (:data:`MURAKAMI_Y_SURFACE`), the
    cited inclusion-fracture relation. ``surface_stress_MPa`` is the residual surface stress (tensile +);
    a compressive (≤ 0) surface returns ``K = 0`` (a closed crack carries no opening-mode intensity).
    ``sqrt_area_um`` is the flaw's ``√area`` in µm. Returned in MPa·√m for comparison with ``K_Ic``.
    """
    if surface_stress_MPa <= 0.0:
        return 0.0
    Y = MURAKAMI_Y_SURFACE if surface else MURAKAMI_Y_INTERIOR
    sqrt_area_m = sqrt_area_um * 1.0e-6
    return Y * surface_stress_MPa * math.sqrt(math.pi * sqrt_area_m)


def critical_flaw_size_um(
    surface_stress_MPa: float, K_Ic_MPa: float = K_IC_AS_QUENCHED_MPA, *, surface: bool = True
) -> float:
    """Critical flaw size ``√area_c`` (µm) at which ``K`` reaches ``K_Ic`` for this surface stress.

    Inverts Murakami's form: ``√area_c = (1/π)·(K_Ic/(Y·σ))²``. A flaw smaller than this is sub-critical
    (no crack); a larger one propagates. A compressive / zero surface (``σ ≤ 0``) returns ``inf`` — no flaw
    can crack a surface that is not in tension (the necessary-condition half of the gate). ``K_Ic`` in
    MPa·√m; returned in µm.
    """
    if surface_stress_MPa <= 0.0:
        return math.inf
    Y = MURAKAMI_Y_SURFACE if surface else MURAKAMI_Y_INTERIOR
    sqrt_area_c_m = (K_Ic_MPa / (Y * surface_stress_MPa)) ** 2 / math.pi
    return sqrt_area_c_m * 1.0e6


# --------------------------------------------------------------------------- #
# 3. The coupled assessment — residual field × cleanliness → quench-crack verdict
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class QuenchCrackAssessment:
    """The two-factor quench-crack verdict — a residual-stress surface crossed with an inclusion flaw.

    ``steel`` / ``half_thickness`` / ``route`` the quench (the residual field's inputs); ``surface_stress_MPa``
    its surface residual (tensile +, from the **phase-split** residual solve); ``surface_tension`` whether it
    is tensile (the necessary condition). ``sqrt_area_um`` the heat's representative largest surface flaw;
    ``K_Ic_MPa`` the surface fracture toughness used; ``critical_flaw_um`` the ``√area_c`` at this stress;
    ``K_applied_MPa`` the flaw's stress intensity. ``cracks`` the verdict — surface in tension **and** the
    flaw exceeds ``√area_c`` (equivalently ``K_applied ≥ K_Ic``). ``margin`` the ratio ``√area_c / √area``
    (> 1 safe, < 1 cracked) — how far the heat is from the gate.
    """

    steel: str
    half_thickness: float
    route: str
    surface_stress_MPa: float
    surface_tension: bool
    sqrt_area_um: float
    K_Ic_MPa: float
    critical_flaw_um: float
    K_applied_MPa: float
    cracks: bool
    margin: float

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if not self.surface_tension:
            return (f"surface {self.surface_stress_MPa:+.0f} MPa (compression) → no quench crack "
                    f"(flaw {self.sqrt_area_um:.0f} µm irrelevant — surface not in tension)")
        if self.cracks:
            return (f"surface {self.surface_stress_MPa:+.0f} MPa tension, flaw {self.sqrt_area_um:.0f} µm "
                    f"> √area_c {self.critical_flaw_um:.0f} µm (K {self.K_applied_MPa:.1f} ≥ "
                    f"{self.K_Ic_MPa:.0f} MPa√m) → QUENCH CRACK")
        return (f"surface {self.surface_stress_MPa:+.0f} MPa tension, but flaw {self.sqrt_area_um:.0f} µm "
                f"< √area_c {self.critical_flaw_um:.0f} µm (K {self.K_applied_MPa:.1f} < "
                f"{self.K_Ic_MPa:.0f} MPa√m) → no crack (sub-critical flaw)")


def quench_crack_fracture(
    steel: str,
    half_thickness: float,
    sqrt_area_um: float,
    *,
    route: str = "direct",
    K_Ic_MPa: float = K_IC_AS_QUENCHED_MPA,
    transform: bool = True,
) -> QuenchCrackAssessment:
    """Couple the §18 residual field to an inclusion flaw → the LEFM quench-crack verdict (the physics).

    Runs :func:`steel.residual.quench_residual_stress` with ``phase_split_yield=True`` (the
    martensite-bounded surface tension the gate needs — see the module docstring), reads the **surface**
    residual, and applies the Murakami surface-flaw gate: the heat cracks when the surface is in **tension**
    **and** its ``sqrt_area_um`` flaw exceeds the critical size :func:`critical_flaw_size_um`. ``steel`` must
    be an anchored atlas steel (the residual engine's guard); ``route`` ``"direct"`` / ``"martemper"``;
    ``transform`` toggles the transformation dilatation (``False`` = thermal-only, surface in compression →
    never cracks, the reference). The cleanliness (``sqrt_area_um``) and the toughness (``K_Ic_MPa``) are the
    representative knobs.
    """
    if steel not in ATLAS_STEELS:
        raise ValueError(
            f"quench_crack_fracture inherits the atlas-steel guard — anchored grades {sorted(ATLAS_STEELS)}, "
            f"got {steel!r}. An off-spec-composition → crack chain is deferred (needs a composition-keyed "
            f"residual path)."
        )
    field_ = residual.quench_residual_stress(
        steel, half_thickness, route=route, transform=transform, phase_split_yield=True,
    )
    sigma = field_.surface_MPa
    tension = sigma > 0.0
    a_c = critical_flaw_size_um(sigma, K_Ic_MPa)
    K = murakami_stress_intensity(sigma, sqrt_area_um)
    cracks = tension and (sqrt_area_um > a_c)
    margin = a_c / sqrt_area_um if sqrt_area_um > 0.0 else math.inf
    return QuenchCrackAssessment(
        steel=steel, half_thickness=half_thickness, route=route,
        surface_stress_MPa=sigma, surface_tension=tension,
        sqrt_area_um=sqrt_area_um, K_Ic_MPa=K_Ic_MPa,
        critical_flaw_um=a_c, K_applied_MPa=K, cracks=cracks, margin=margin,
    )


# --------------------------------------------------------------------------- #
# 4. The Heat seam — repack the coupled verdict, raise the realized quench-crack flag
# --------------------------------------------------------------------------- #
def fracture_check(
    heat: Heat,
    half_thickness: float,
    sqrt_area_um: float,
    *,
    grade: str | None = None,
    route: str = "direct",
    K_Ic_MPa: float = K_IC_AS_QUENCHED_MPA,
    transform: bool = True,
) -> Heat:
    """Read whether this ``Heat`` actually **quench-cracks** — the realized (two-tier) fracture seam.

    The fracture-mechanics counterpart to :func:`steel.heat_state.quench_crack_check`: where that raises the
    ``quench-crack-risk`` flag on surface *tension* alone (the necessary condition), this couples the same
    residual field to the heat's inclusion flaw (:func:`quench_crack_fracture`) and raises the **realized**
    ``quench-crack`` flag only when tension **and** a critical flaw coincide. So a clean heat carrying a
    tensile surface stays ``quench-crack-risk`` but **not** ``quench-crack``; a dirty heat in the same field
    crosses into the realized crack. ``grade`` selects the atlas anchor (default: the ``Heat``'s composition
    name); ``sqrt_area_um`` is the heat's representative largest surface flaw (the cleanliness input — e.g.
    :data:`SQRT_AREA_CLEAN_UM` / :data:`SQRT_AREA_DIRTY_UM`). Returns a *new* ``Heat`` with one
    ``"fracture-check"`` :class:`~steel.heat_state.ProcessStep` appended; composition is unchanged.

    Note: like :func:`steel.heat_state.quench_crack_check`, this writes ``residual_stress_MPa`` — but from the
    **phase-split** solve (martensite-bounded, ~1045 MPa for the hero), where ``quench_crack_check`` writes
    the **single-yield** value (~388 MPa). Running both on one ``Heat`` is last-writer-wins on that field; the
    trail records which step set it.
    """
    grade = grade or heat.composition.name
    a = quench_crack_fracture(
        grade, half_thickness, sqrt_area_um, route=route, K_Ic_MPa=K_Ic_MPa, transform=transform,
    )
    defects = add_defect(heat.defects, QUENCH_CRACK) if a.cracks else heat.defects
    flags_added = (QUENCH_CRACK,) if (a.cracks and not heat.has_defect(QUENCH_CRACK)) else ()
    summary = (
        f"{grade} {route} quench, 2t={2 * half_thickness * 1000:g} mm, flaw √area {sqrt_area_um:.0f} µm: "
        f"{a.verdict}"
    )
    step = ProcessStep("fracture-check", summary, in_spec=not a.cracks, flags_added=flags_added)
    return heat.evolve(step, residual_stress_MPa=a.surface_stress_MPa, defects=defects)
