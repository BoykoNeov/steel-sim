"""Hydrogen flaking — the dissolved-hydrogen *consequence* (Steel-making, the cooling stage after F2).

The consumer that **closes the hydrogen consequence** F2 (:mod:`steel.refining`) deferred. Refining's
``degas`` already *fills* the ``Heat``'s dissolved hydrogen and raises a chemistry-state
**``hydrogen-flaking-risk``** flag when the ladle hydrogen clears its spec (the Sieverts √p limit vs the
2 ppm engineering line). But whether a *part* actually **flakes** — develops the internal hairline cracks
("flakes" / shatter cracks / "fisheyes") that ruin heavy forgings — is a different, deferred question, and a
fundamentally **geometric** one: flaking is governed by whether dissolved hydrogen can **diffuse out** of a
section before it is cooled into the brittle range, where it precipitates as molecular H₂ at internal
interfaces and cracks. Thick sections trap it; a slow cool or a **dehydrogenation bake** (~650 °C hold) lets
it escape. This module reads that outcome — the two-tier pattern of cold-short (propagation) / red-short (a
new consumer): refining sets the *risk* (chemistry), this sets the *consequence* (does the section crack).

The model — analytic out-diffusion, and why it is standalone (no engine, no ADR)
-------------------------------------------------------------------------------
Hydrogen escaping a plate held with its surfaces swept clean is the **textbook slab-desorption** problem,
which has a closed form (Crank, *The Mathematics of Diffusion*): for a plate of half-thickness ``L`` with
uniform initial content and zero surface concentration, the **centre** content (the last to degas — the
crack-prone core) decays as ``C_c(t)/C₀ = Σ 4(−1)ⁿ/((2n+1)π) · exp(−(2n+1)²π²Dt/4L²)`` and the **mean**
content as ``Σ 8/((2n+1)²π²)·exp(…)``. So the flaking *verdict* — residual peak hydrogen after a cool/bake
schedule — is a **scalar from a closed form**; no solver is needed (the project's sealed diffusion engine is
already validated against exactly this analytic solution, ``engines/diffusion/tests/test_erfc.py`` — running
it here would only re-exercise that seal, adding machinery, not content). Standalone, like
:mod:`steel.reduction` and casting Slice 1.

What is a TOOTH here, and what is honestly by-construction
----------------------------------------------------------
This is a **thin consumer** (the red-short class), not a benchmarked field model — named so up front. The map:

* **The one genuine (soft, OoM/ranking-grade) tooth — cross-source coherence.** The dehydrogenation time
  this model predicts from an *independently pinned* hydrogen diffusivity reproduces cited industrial
  bake-vs-section practice **without tuning**: with ``D_H`` set to reproduce the accepted room-temperature
  α-Fe **lattice** value (~8×10⁻⁹ m²/s), a 1-inch section clears in ~0.6 h (the "~1 h per inch" rule) and a
  500 mm heavy forging takes ~10 days (heavy forgings need days). The diffusivity is pinned to the *room-T
  lattice* number, the practice anchors are *bake times* — two independent sources, so the agreement is a
  real check, not arithmetic. It is **OoM-grade**: real steel traps hydrogen (carbides, dislocations,
  grain boundaries) 10–100× below the trap-free lattice value, so the lattice model is a **conservative
  lower bound** on the bake time (real bakes are at least this long) — the named scatter.
* **By construction (NOT teeth):** the ``τ ∝ L²`` section-size scaling (it falls straight out of the
  diffusion equation — Chvorinov-``M²`` class) and the verdict rule (peak residual hydrogen above the
  critical line ⇒ flakes).
* **Cited INPUTS (verification ≠ tooth):** the α-Fe lattice Arrhenius ``D_H`` (Kiuchi–McLellan 1983
  experimental reanalysis; cross-checked by DFT/MD, Jiang–Carter / Hasan 2020), the ~650 °C ferritic bake
  (below A₁ = 727 °C, where hydrogen diffuses fastest), and the ~2 ppm engineering flaking limit (shared with
  :data:`steel.refining.MAX_HYDROGEN_PPM`).

**Named ceiling:** the model is hydrogen **out-diffusion** during a cool/bake — *not* the thermodynamics that
drive flaking (the γ→α solubility collapse on transformation that supersaturates the lattice, the H₂
recombination pressure built at internal voids). It answers "can the hydrogen escape this section in time?",
which is the controlling, geometric question; it does not compute the crack itself. The susceptible
temperature range (flakes form on cooling below ~200 °C, once hydrogen is immobile and supersaturated) is the
reason the bake is done *before* the final cool — modelled here only as "degas above the critical content
before cooling". Units: ppm for hydrogen, metres for section, seconds for time, °C for temperature.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .heat_state import Heat, ProcessStep, add_defect
from .refining import MAX_HYDROGEN_PPM

# --------------------------------------------------------------------------- #
# Cited inputs & the verified/spec boundary — pinned constants, NOT teeth
# --------------------------------------------------------------------------- #
R_GAS: float = 8.314                      # J/(mol·K)

# Lattice diffusivity of hydrogen in α-Fe (bcc ferrite), D = D0·exp(−Q/RT). Representative trap-free values
# pinned to reproduce the accepted room-temperature lattice coefficient ~8×10⁻⁹ m²/s (Kiuchi & McLellan 1983
# experimental reanalysis of 62 datasets; cross-checked by DFT/MD — Jiang & Carter, Hasan et al. 2020:
# D0 ≈ 1–1.5×10⁻⁷ m²/s, Ea ≈ 0.04–0.06 eV). Pinned INDEPENDENTLY of bake practice (the coherence tooth).
# Real steel traps hydrogen 10–100× below this lattice value → the lattice model is a conservative LOWER
# bound on the bake time (the named scatter).
D0_HYDROGEN_FERRITE: float = 1.0e-7       # m²/s
Q_HYDROGEN_FERRITE: float = 6000.0        # J/mol (~0.062 eV) → D(25 °C) ≈ 8.9×10⁻⁹ m²/s

# A ferritic dehydrogenation-hold temperature: ~650 °C is below A₁ (727 °C), so the steel is bcc ferrite
# where hydrogen diffuses fastest — why the classic anti-flaking soak is done here (isothermal ~600–650 °C).
DEFAULT_BAKE_TEMP_C: float = 650.0

# The flaking limit — the verified/spec boundary (a labelled engineering acceptance line, like
# heat_state.MIN_MARTENSITE_SPEC). Shared with refining.MAX_HYDROGEN_PPM (the ladle risk spec): a section
# whose peak residual hydrogen stays above this after its cool/bake is taken to flake.
CRITICAL_FLAKING_H_PPM: float = MAX_HYDROGEN_PPM   # 2.0 ppm

# The defect flag this stage raises (the actual cracking consequence) — distinct from refining's
# hydrogen-flaking-RISK (the upstream chemistry-state flag). The two-tier pattern: risk → consequence.
HYDROGEN_FLAKING: str = "hydrogen-flaking"   # trapped dissolved H → internal hairline cracks (flakes)


def hydrogen_diffusivity(T_celsius: float) -> float:
    """Lattice diffusivity of hydrogen in α-Fe ``D = D0·exp(−Q/RT)`` (m²/s), ``T`` in **°C**.

    The cited α-Fe lattice Arrhenius (:data:`D0_HYDROGEN_FERRITE`, :data:`Q_HYDROGEN_FERRITE`), reproducing
    the accepted room-temperature value ~8.9×10⁻⁹ m²/s. Hydrogen is the fastest-diffusing solute in steel;
    this is the trap-free lattice value (real, trapped steel diffuses slower — the named scatter).
    """
    return D0_HYDROGEN_FERRITE * math.exp(-Q_HYDROGEN_FERRITE / (R_GAS * (T_celsius + 273.15)))


# --------------------------------------------------------------------------- #
# 1. Analytic slab desorption (Crank) — the closed forms the verdict reads
# --------------------------------------------------------------------------- #
def centre_residual_fraction(D: float, t: float, half_thickness: float, n_terms: int = 200) -> float:
    """Centre hydrogen content as a fraction of the initial, after time ``t`` (Crank slab desorption).

    ``C_centre(t)/C₀ = Σ 4(−1)ⁿ/((2n+1)π)·exp(−(2n+1)²π²Dt/4L²)`` for a plate of half-thickness ``L`` with
    surfaces held at zero (hydrogen recombines and leaves at the free surface). The **centre** is the last to
    degas — the crack-prone core, so this is the peak residual the flaking verdict reads. Clamped to ≥ 0.
    """
    if t <= 0.0:
        return 1.0
    L = half_thickness
    s = 0.0
    for n in range(n_terms):
        m = 2 * n + 1
        s += 4.0 * (-1) ** n / (m * math.pi) * math.exp(-(m * math.pi) ** 2 * D * t / (4.0 * L * L))
    return max(s, 0.0)


def mean_residual_fraction(D: float, t: float, half_thickness: float, n_terms: int = 200) -> float:
    """Section-mean hydrogen content as a fraction of the initial (the total hydrogen still in the part).

    ``M(t)/M₀ = Σ 8/((2n+1)²π²)·exp(−(2n+1)²π²Dt/4L²)`` — the classic fractional-residual-gas series. Lower
    than the centre fraction (the surface clears first); used for the desorption curve, not the verdict.
    """
    if t <= 0.0:
        return 1.0
    L = half_thickness
    s = 0.0
    for n in range(n_terms):
        m = 2 * n + 1
        s += 8.0 / (m * math.pi) ** 2 * math.exp(-(m * math.pi) ** 2 * D * t / (4.0 * L * L))
    return max(min(s, 1.0), 0.0)


def dehydrogenation_time(
    half_thickness: float,
    *,
    T_celsius: float = DEFAULT_BAKE_TEMP_C,
    target_fraction: float = 0.25,
) -> float:
    """Time (s) for the section **centre** to fall to ``target_fraction`` of its initial hydrogen at ``T``.

    The bake time the section needs — the quantity compared to cited practice (~1 h/inch; heavy forgings
    days). Scales as ``L²`` (the by-construction section-size law). Found by bisection on
    :func:`centre_residual_fraction`.
    """
    D = hydrogen_diffusivity(T_celsius)
    lo, hi = 1.0, 1.0e10
    for _ in range(100):
        mid = math.sqrt(lo * hi)
        if centre_residual_fraction(D, mid, half_thickness) > target_fraction:
            lo = mid
        else:
            hi = mid
    return mid


# --------------------------------------------------------------------------- #
# 2. The flaking verdict — does the section crack, given its size and cool/bake?
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FlakingAssessment:
    """Whether a section flakes, given its initial hydrogen, thickness, and cool/bake schedule.

    ``initial_H_ppm`` the dissolved hydrogen handed in (from F2 :func:`steel.refining.degas`);
    ``half_thickness`` the section's V/A-like half-dimension (m); ``residual_centre_ppm`` the peak (centre)
    hydrogen left after the schedule; ``critical_ppm`` the flaking limit; ``flakes`` the verdict —
    ``residual_centre_ppm`` still above ``critical_ppm`` when the part is cooled into the brittle range.
    """

    initial_H_ppm: float
    half_thickness: float
    bake_temp_C: float
    hold_time_s: float
    residual_centre_ppm: float
    critical_ppm: float
    flakes: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.flakes:
            return ("FLAKES (trapped hydrogen → internal hairline cracks — the section is too thick to degas "
                    "in time)")
        if self.initial_H_ppm <= self.critical_ppm:
            return "sound (hydrogen was already below the flaking limit — a clean, well-degassed heat)"
        return "sound (the bake degassed the section below the flaking limit before it cooled)"


def flaking_assessment(
    initial_H_ppm: float,
    half_thickness: float,
    *,
    bake_temp_C: float = DEFAULT_BAKE_TEMP_C,
    hold_time_s: float = 0.0,
    critical_ppm: float = CRITICAL_FLAKING_H_PPM,
) -> FlakingAssessment:
    """Resolve whether a section flakes (the physics): out-diffuse its hydrogen over the hold, then judge.

    The peak (centre) hydrogen after a ``hold_time_s`` dehydrogenation hold at ``bake_temp_C`` is the initial
    content times :func:`centre_residual_fraction`; the section **flakes** if that residual is still above
    ``critical_ppm`` when it is finally cooled into the brittle range. ``hold_time_s = 0`` is the no-bake
    case — a thick section then keeps essentially all its hydrogen and flakes, a thin one may already be safe.
    The section-size and bake levers both enter through the ``L²``/``Dt`` group.
    """
    D = hydrogen_diffusivity(bake_temp_C)
    residual = initial_H_ppm * centre_residual_fraction(D, hold_time_s, half_thickness)
    return FlakingAssessment(
        initial_H_ppm=initial_H_ppm,
        half_thickness=half_thickness,
        bake_temp_C=bake_temp_C,
        hold_time_s=hold_time_s,
        residual_centre_ppm=residual,
        critical_ppm=critical_ppm,
        flakes=residual > critical_ppm,
    )


def hydrogen_flaking_check(
    heat: Heat,
    *,
    half_thickness: float,
    bake_temp_C: float = DEFAULT_BAKE_TEMP_C,
    hold_time_s: float = 0.0,
    critical_ppm: float = CRITICAL_FLAKING_H_PPM,
) -> Heat:
    """Cool / bake the ``Heat`` in a section of ``half_thickness`` and read whether it flakes — the H seam.

    The orchestrator that **closes the hydrogen consequence**: it reads the Heat's dissolved hydrogen
    (filled by :func:`steel.refining.degas`) and, if a section that thick cannot degas below the flaking
    limit in the given hold, raises the **hydrogen-flaking** flag and carries it forward — the mirror of
    :func:`steel.hot_work.hot_work`'s red-short seam, but for cooling rather than forging. Distinct from
    refining's upstream ``hydrogen-flaking-risk`` (the chemistry-state flag): this is the *consequence*.
    Returns a *new* ``Heat`` with one ``"hydrogen-flaking-check"`` :class:`~steel.heat_state.ProcessStep`
    appended; composition is unchanged (out-diffusion removes trace hydrogen, not bulk alloy). Raises if the
    Heat carries no dissolved-hydrogen state yet (run :func:`steel.refining.degas` first).
    """
    if heat.hydrogen_ppm is None:
        raise ValueError("Heat has no dissolved-hydrogen state — run refining.degas first (F2 fills it)")
    a = flaking_assessment(heat.hydrogen_ppm, half_thickness, bake_temp_C=bake_temp_C,
                           hold_time_s=hold_time_s, critical_ppm=critical_ppm)
    defects = add_defect(heat.defects, HYDROGEN_FLAKING) if a.flakes else heat.defects
    flags_added = (HYDROGEN_FLAKING,) if (a.flakes and not heat.has_defect(HYDROGEN_FLAKING)) else ()
    bake = "no bake" if hold_time_s <= 0.0 else f"bake {hold_time_s / 3600:.0f} h @ {bake_temp_C:.0f} °C"
    summary = (
        f"section {half_thickness * 2e3:.0f} mm, H {heat.hydrogen_ppm:.1f} ppm, {bake} → "
        f"residual {a.residual_centre_ppm:.1f} ppm (limit {critical_ppm:.0f}) → {a.verdict}"
    )
    step = ProcessStep("hydrogen-flaking-check", summary, in_spec=not a.flakes, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
