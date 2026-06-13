"""Hot-working / red-shortness — the **sulfur** consequence (Steel-making **F5**, the forging stage).

The consumer that **closes the sulfur consequence** F2 Slice 2 (:mod:`steel.slag`) deferred. The slag
partition *removed* sulfur and set the residual ``S`` state; this module is what finally *reads* it. At
the forging / rolling heat, sulfur that manganese did not tie up as MnS forms **FeS**, whose low-melting
**Fe–FeS eutectic (~988 °C)** wets the austenite grain boundaries as a liquid film — so the piece tears
when it is worked: **red-shortness** (hot-shortness). Manganese is the fix — it outcompetes iron for the
sulfur to form **MnS (m.p. ~1610 °C)**, solid and plastic at the forging heat, which simply rolls out.
This is *Mushet's manganese*, the 1850s addition that made Bessemer steel sound.

The honest posture — a NEW consumer with NO strict tooth of its own
-------------------------------------------------------------------
The phosphorus consequence closes by **propagation** — P threads the *existing* Pickering DBTT law in
:mod:`steel.grain` (see :func:`steel.heat_state.cold_short_check`) — and the **one genuine tooth of the whole
impurity-consequence build lives there**: the P solid-solution strengthening rate, by cross-source coherence
(Thiele ≈427 MPa/wt% inside Total Materia's 365–620, hardness 119.8 vs 123–125 vs 127 HV/wt%). Sulfur has no
existing consumer, so it closes through this **new** verdict — but, the load-bearing honesty, **this slice
carries no strict tooth.** It is cited constants + a by-construction verdict over a reused balance: nothing
here *could come out wrong* and falsify a benchmark — exactly as slag.py labels its own Mn:S → MnS
stoichiometry "**by construction (NOT teeth)**". That is a fine thing to be (a thin, honest consumer); it
just must not be dressed as a tooth. The parts:

* **Cited constants (di-crosschecked INPUTS, not teeth — verification ≠ a tooth):** the Fe–FeS **eutectic
  ~988 °C** — and crucially the *eutectic* (the grain-boundary liquid-film onset), **distinct from FeS
  melting ~1192 °C** — and **MnS ~1610 °C**. Pinning the right number guards a transcription slip; it is not
  a falsifiable prediction.
* **By construction (NOT teeth):** the free-sulfur balance, *reused wholesale* from
  :func:`steel.slag.manganese_sulfide` (Mn:S → MnS, ``1.71 = M_Mn/M_S`` — pure stoichiometry, cannot fail);
  and the verdict rule itself (free sulfur **and** worked at/above the eutectic ⇒ red-short).
* **The historical-coherence ANCHOR (a RESULT, still by-construction):** that the Mn:S ≥ 1.71 threshold
  reproduces *Mushet's manganese* (the 1850s fix that made sulfurous Bessemer steel forgeable) — the reason
  the slice is worth building. It is **not** the analog of slag.py's acid/basic ``L_P`` endpoint: *that*
  endpoint emerges from a nontrivial Healy correlation that could have failed to reproduce history, whereas
  1.71 is arithmetic that cannot.
* **Mechanism narrative (NOT a tooth):** the temperature *ordering* (eutectic 988 < forging heat < MnS 1610).
  Three looked-up numbers on a line; "free S above the eutectic cracks hot" is this module's ``if`` — a test
  asserting the ordering would confirm our own rule (the vacuous-benchmark trap this project polices).

**Named ceiling:** this is a *forgeability verdict* at an assumed working temperature, **not** a kinetic
hot-ductility curve — no strain rate, no
reduction-of-area trough, no window *shape* (the red-short ductility trough hot-tensile tests map between
~900–1200 °C is the unmodelled refinement). MnS inclusion **fracture anisotropy** / transverse-toughness
debit, and the *good*-impurity **free-machining** use of sulfur (resulfurized 11xx grades — MnS breaks the
chip), are named deferrals. Units: wt % for composition, °C for temperature.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import slag
from .heat_state import Heat, ProcessStep, add_defect

# --------------------------------------------------------------------------- #
# Cited transition temperatures (di-crosschecked, 1 atm) — pinned constants, NOT teeth
# --------------------------------------------------------------------------- #
# The Fe–FeS EUTECTIC, not FeS melting: a sulfur-rich liquid wets the austenite grain boundaries the moment
# the working temperature passes this point, and the boundary loses cohesion. The eutectic (~988 °C) sits
# well below FeS's own melting (~1192 °C) — citing the eutectic, the lower onset, is the load-bearing choice.
FE_FES_EUTECTIC_C: float = 988.0
# MnS melts ~1610 °C — far above any forging heat, so MnS stays a solid, plastic inclusion that rolls out
# instead of a grain-boundary film. The ~620 °C gap between the two is *why* manganese works (mechanism).
MNS_MELTING_C: float = 1610.0
# A representative hot-working (forge / hot-roll) temperature — the labelled default the verdict is read
# "at". Steel is worked roughly 1100–1250 °C; the verdict only needs this to be a realistic value above the
# eutectic. Override per call (e.g. drop below 988 °C to show the same free-sulfur heat is workable cold).
DEFAULT_FORGE_TEMP_C: float = 1150.0

# The defect flag this stage raises — defined here (the module that raises it), as SOFT_CORE is in
# heat_state and HIGH_SULFUR in slag. The consequence the F2-Slice-2 deferral left open, now propagating.
RED_SHORT: str = "red-short"   # free S → Fe–FeS grain-boundary film above the eutectic → hot cracking


@dataclass(frozen=True)
class HotWorkability:
    """The red-shortness verdict at a forging temperature — what sulfur is free, and whether it cracks hot.

    ``mn_s_ratio`` Mn:S by weight (``inf`` for a sulfur-free heat); ``free_sulfur_pct`` the sulfur the
    available manganese could *not* tie up as MnS (the FeS precursor), from :func:`slag.manganese_sulfide`;
    ``forms_mns`` whether Mn:S ≥ 1.71 (all sulfur benign); ``above_eutectic`` whether the working
    temperature is at or above the Fe–FeS eutectic; ``red_short`` the verdict — free sulfur present **and**
    worked above the eutectic.
    """

    forge_temp_C: float
    mn_s_ratio: float
    free_sulfur_pct: float
    forms_mns: bool
    above_eutectic: bool
    red_short: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading of the outcome (used by the demo and the process trail)."""
        if self.red_short:
            return "RED-SHORT (free sulfur → Fe–FeS grain-boundary film — cracks on forging)"
        if not self.forms_mns:
            return f"free sulfur present, but worked below the {FE_FES_EUTECTIC_C:.0f} °C eutectic (no liquid film)"
        return "sound (manganese ties the sulfur as high-melting MnS)"


def red_short_assessment(
    Mn_pct: float, S_pct: float, temp_C: float = DEFAULT_FORGE_TEMP_C,
) -> HotWorkability:
    """Resolve whether a steel of this ``Mn``/``S`` is red-short when worked at ``temp_C`` (the physics).

    Reuses :func:`slag.manganese_sulfide` for the conservation-clean free-sulfur balance, then applies the
    verdict rule: red-shortness needs **both** free sulfur (Mn:S below the 1.71 stoichiometric threshold —
    Mushet's headline) **and** a working temperature at or above the Fe–FeS eutectic (so the FeS forms a
    liquid grain-boundary film). Mushet's manganese closes the first condition; working cold closes the
    second. The temperature comparison is the module's *rule* (mechanism), not a benchmark.
    """
    balance = slag.manganese_sulfide(Mn_pct, S_pct)
    above = temp_C >= FE_FES_EUTECTIC_C
    red = balance.free_sulfur_pct > 0.0 and above
    return HotWorkability(
        forge_temp_C=temp_C,
        mn_s_ratio=balance.ratio,
        free_sulfur_pct=balance.free_sulfur_pct,
        forms_mns=balance.forms_mns,
        above_eutectic=above,
        red_short=red,
    )


def hot_work(heat: Heat, temp_C: float = DEFAULT_FORGE_TEMP_C) -> Heat:
    """Forge / hot-roll the ``Heat`` at ``temp_C`` and read whether it is red-short — the S-consequence seam.

    The orchestrator that **closes the sulfur consequence**: it reads the Heat's ``Mn`` and ``S``
    (:func:`red_short_assessment`) and, if the free sulfur would form a Fe–FeS grain-boundary film at the
    working heat, raises the **red-short** flag and carries it forward. Returns a *new* ``Heat`` with one
    ``"hot-work"`` :class:`~steel.heat_state.ProcessStep` appended — the mirror of :func:`heat_treat`'s
    soft-core seam, but for hot-working rather than quench. Composition is unchanged (forging does not move
    sulfur); only the body temperature set-point and the defect state evolve.
    """
    a = red_short_assessment(heat.composition.Mn, heat.composition.S, temp_C)
    defects = add_defect(heat.defects, RED_SHORT) if a.red_short else heat.defects
    flags_added = (RED_SHORT,) if (a.red_short and not heat.has_defect(RED_SHORT)) else ()
    summary = (
        f"forge at {temp_C:.0f} °C (eutectic {FE_FES_EUTECTIC_C:.0f} °C), Mn:S {a.mn_s_ratio:.1f}, "
        f"free S {a.free_sulfur_pct:.3f} % → {a.verdict}"
    )
    step = ProcessStep("hot-work", summary, in_spec=not a.red_short, flags_added=flags_added)
    return heat.evolve(step, temperature_C=temp_C, defects=defects)
