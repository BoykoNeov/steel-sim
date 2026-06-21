"""``game.choices`` — the per-stage decisions the gauntlet offers (Slice 1's selectable knobs).

Slice 1 turns every stage (bar casting) into a decision. This module is the **tested source of truth** for
what the UI offers at each stage: the named options, their underlying :class:`~game.state.Recipe` values,
and which one is the clean-heat **recommendation**. Keeping the option *values* here (not inline in the
untested Streamlit layer) lets a test pin the load-bearing property: **every recommended option reproduces
the capstone reference** — so "take every recommendation" is exactly the sound golden run, and any other
pick is a deliberate, losable departure (the losability suite pins that each departure actually fails).

No streamlit, no matplotlib (the ``app.py`` three-layer firewall) — pure data the UI renders and the tests
check. The carbon blow endpoint is the one *continuous* knob (a slider over the C–O τ-curve, :mod:`game.knobs`);
every other knob is a small set of named choices defined here.
"""
from __future__ import annotations

from dataclasses import dataclass

from steel import demo_capstone as dc

# Vacuum depths for the degassing decision (atm H₂): the reference deep vacuum + two shallow traps that
# leave hydrogen above the flaking limit (probed losable).
DEGAS_DEEP: float = dc.DEGAS_P_H2          # the reference — drops H below the 2 ppm flaking limit
DEGAS_SHALLOW: float = 0.1                 # leaves hydrogen → flaking
DEGAS_NONE: float = 1.0                    # no vacuum → flaking


@dataclass(frozen=True)
class Option:
    """One selectable choice for a stage: its UI ``label``, the ``Recipe`` ``value`` it sets, and a hint."""

    label: str
    value: object
    note: str
    recommended: bool = False


@dataclass(frozen=True)
class Decision:
    """A stage's decision — the knob it sets and the named options, exactly one of them recommended."""

    knob: str
    prompt: str
    options: tuple[Option, ...]

    def recommended(self) -> Option:
        """The clean-heat option (the one that keeps the heat on the capstone's sound reference run)."""
        return next(o for o in self.options if o.recommended)

    def default_index(self) -> int:
        """The index of the recommended option (the UI's default selection)."""
        return next(i for i, o in enumerate(self.options) if o.recommended)


#: The named-choice decisions, keyed by ``Recipe`` field. (Carbon is the slider, handled in the UI.)
DECISIONS: dict[str, Decision] = {
    "dephosphorize": Decision("dephosphorize", "Dephosphorization", (
        Option("Basic converter slag — pull the tramp phosphorus out", True,
               "the clean-heat choice (oxidizing, while the oxygen is high)", recommended=True),
        Option("Skip it — save a slag", False, "tramp phosphorus stays → cold-short (brittle)"),
    )),
    "deoxidizer": Decision("deoxidizer", "Kill the bath with", (
        Option("Aluminium — a strong deoxidizer", "Al",
               "drops dissolved oxygen far below the C–O line (Al ≫ Si > Mn)", recommended=True),
        Option("Silicon — a weak deoxidizer", "Si", "can't pull O below the C–O line → gas porosity"),
        Option("Manganese — a weak deoxidizer", "Mn", "can't pull O below the C–O line → gas porosity"),
    )),
    "degas_p_H2": Decision("degas_p_H2", "Vacuum degassing", (
        Option("Deep vacuum — strip hydrogen below the flaking limit", DEGAS_DEEP,
               "the clean-heat choice", recommended=True),
        Option("Shallow vacuum", DEGAS_SHALLOW, "leaves dissolved hydrogen → flaking on cooling"),
        Option("No vacuum — skip it", DEGAS_NONE, "leaves dissolved hydrogen → flaking on cooling"),
    )),
    "desulfurize": Decision("desulfurize", "Desulfurization", (
        Option("Reducing ladle slag — pull the tramp sulfur out", True,
               "the clean-heat choice (reads the now-low oxygen the kill left)", recommended=True),
        Option("Skip it — save a slag", False,
               "tramp sulfur stays over the cleanliness spec (the trim's Mn ties it as MnS — no red-short, "
               "but off-grade dirty)"),
    )),
    "carbon_pickup": Decision("carbon_pickup", "Ferroalloys for the trim", (
        Option("Low-carbon ferroalloys — clean", False,
               "hit the alloy window without carrying carbon in", recommended=True),
        Option("High-carbon ferroalloys — cheaper", True,
               "carry carbon into the bath → over the grade carbon ceiling (off-grade)"),
    )),
    "quench_medium": Decision("quench_medium", "Quench medium", (
        Option("Oil — the grade's quench", "oil", "through-hardens this section", recommended=True),
        Option("Water — more severe", "water", "harder still — this section through-hardens either way "
               "(distortion / quench-crack risk is real in practice but not modelled for this grade)"),
        Option("Air — mild", "air", "cools too slowly → no martensite → soft core"),
    )),
    "part_diameter": Decision("part_diameter", "Section to quench", (
        Option("20 mm bar", dc.PART_DIAMETER, "the reference section — through-hardens in oil", recommended=True),
        Option("50 mm bar", 0.050, "too thick for this hardenability → soft core"),
        Option("100 mm bar", 0.100, "far too thick → soft core"),
    )),
}


#: What each stage asks the player. The carbon slider is named here but rendered specially (the τ-curve);
#: casting asks nothing (an honest pass-through); heat-treat asks two (medium + section).
STAGE_DECISIONS: dict[str, tuple[str, ...]] = {
    "decarburize": ("carbon",),
    "dephosphorize": ("dephosphorize",),
    "deoxidize": ("deoxidizer",),
    "degas": ("degas_p_H2",),
    "desulfurize": ("desulfurize",),
    "trim": ("carbon_pickup",),
    "cast": (),
    "heat-treat": ("quench_medium", "part_diameter"),
}
