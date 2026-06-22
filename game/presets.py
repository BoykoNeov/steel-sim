"""``game.presets`` — the method/era tech tree (``game.md`` §6 Slice 2; the §15.2 method→engine map).

Slice 1 made the modern 4140 route a gauntlet — every stage a decision on **one** technology. Slice 2 turns
the **§15.2 method→engine map** into a played progression: a small table of historical/modern steelmaking
**methods**, each a *constrained walk* through the same validated F1–F4 engines, and a small table of
**ores** (the feedstock's tramp load). The choice of method + ore is the new decision, and the **purity-control
ramp** (``steel-making.md`` §14 theme C / §15.2) is the difficulty curve: each era conquers one more tramp
element, so a dirty ore that an old process cannot clean walks you up the tech tree.

What is era-gated here — and what deliberately is **not** (the honesty posture, ``game.md`` §2)
------------------------------------------------------------------------------------------------
The two tramp elements the front-end engines actually **carry on the charge and remove by benchmarked
slag partition** are **phosphorus and sulfur** — and those are exactly the two the era ramp gates:

* **Phosphorus — the acid/basic slag lever (verified).** Every converter method *runs* a dephosphorization
  stage, but with its era's slag. An **acid** Bessemer slag (lime-poor, however oxidizing) has
  ``L_P ≈ 1`` — phosphorus stays in the steel (*why Bessemer rails cracked*); the **basic** Thomas/BOF slag
  has ``L_P`` in the hundreds — phosphorus conquered. This is :func:`steel.slag.phosphorus_partition` (Healy
  1970) reading :data:`steel.slag.ACID_BESSEMER_SLAG` vs :data:`steel.slag.BASIC_CONVERTER_SLAG` — the era
  difference is *which slag the stage runs*, not a skipped step. (More honest: you watch the acid slag try
  and fail.)
* **Sulfur — the ladle desulfurization unlock (verified).** Desulfurization is a **reducing ladle** step
  (:func:`steel.slag.desulfurize`, reading the killed bath's low oxygen): pre-ladle eras simply have no such
  stage, so tramp sulfur rides through (off-grade dirty, or red-short if the manganese cannot tie it as
  MnS). Only the modern secondary-metallurgy era unlocks it. This is the §15.2 "sulfur comes out in the
  ladle, not the converter."

What is **not** honestly era-gateable (so it is not claimed):

* **Hydrogen.** The model introduces *no charge hydrogen* — :func:`steel.refining.degas` only *sets* H to a
  Sieverts equilibrium, it does not strip a pre-existing charge load. So "no vacuum" cannot mean "leaves the
  charge hydrogen in" (there is none): pre-modern eras simply make **no flaking claim** (``hydrogen_ppm``
  stays ``None``, unchecked). The flaking decision lives in the modern gauntlet's degas knob, where it
  belongs. (N is reported-not-flagged by design — :mod:`steel.refining`.)
* **The kill and the deoxidizer.** Every era is given a *proper* aluminium kill so the deoxidizer choice
  does not confound the P/S ramp — its losability is the Slice-1 gauntlet's lesson, not the era ramp's.
  Aluminium specifically (cheap only from ~1890s) and vacuum degassing (1950s+) are **anachronistic** in the
  old eras: that period detail, like the process *speed*, *scale*, and the BOF's *low nitrogen*, is **flavor**
  — labelled "plausible, not validated" (the §15 doctrine: a method's *chemistry* is a walk through built
  engines; its *process feel* is the §4 transport tar-pit, game-layer by design).

The named ceiling — the different-product methods are out of scope
-----------------------------------------------------------------
This is the **converter-era purity ramp judged as 4140** (every method makes the same grade; they differ in
*which tramp they can clean*). The §15.2 methods that make a **different product on a different walk** —
the **bloomery** (low-carbon, slag-laden wrought iron, hard-capped *below* the F1 C/CO crossover so it cannot
make hardenable alloy steel at all), **cementation** (``carburize.py``), **crucible** (homogenization), and
**wootz** (``wootz.py`` carbide banding) — each need their own win-condition and judge, and are a **named
deferral** (a later slice). The bloomery is surfaced here only as the era-0 *floor* (:data:`BLOOMERY_NOTE`),
not a playable 4140 walk.

Pure data + thin helpers — no streamlit, no matplotlib (the ``app.py`` three-layer firewall). Every physics
number a method implies is read live from the sealed engine at play time; this module only names the recipe.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from steel import demo_capstone as dc
from steel import slag as sl
from steel.slag import Slag
from steel.sweep import Steel


# --------------------------------------------------------------------------- #
# 1. The ore — the feedstock's tramp load (the new lever that makes the gates bite)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Ore:
    """A charge feedstock — the alloy-lean backbone plus the **tramp phosphorus and sulfur** it carries.

    The era ramp only bites when the ore is dirty enough to need cleaning: a phosphoric ore demands a basic
    slag (Thomas, not acid Bessemer) for its phosphorus and a ladle for its sulfur, while a clean ore makes
    sound steel even in the oldest process. ``backbone`` is single-sourced from :data:`steel.demo_capstone`'s
    lean backbone (so the alloy content matches the capstone exactly); only ``P`` / ``S`` distinguish the
    ores — an apples-to-apples tramp comparison.
    """

    name: str
    backbone: Steel
    note: str

    @property
    def P(self) -> float:
        """Tramp phosphorus on the charge (wt %)."""
        return self.backbone.P

    @property
    def S(self) -> float:
        """Tramp sulfur on the charge (wt %)."""
        return self.backbone.S


#: The phosphoric ore — the capstone's seeded backbone (P 0.090, S 0.050, both over spec): the "hard mode"
#: that needs the full modern chain to clean. Single-sourced from the capstone so the modern route reproduces
#: the golden run exactly.
PHOSPHORIC_ORE = Ore(
    "Phosphoric ore", dc.LEAN_BACKBONE,
    "high tramp phosphorus and sulfur (the pig iron most of the world had) — needs a basic process for the "
    "phosphorus and a ladle for the sulfur.",
)

#: The clean ore — low phosphorus AND low sulfur (both under the cleanliness spec), the non-phosphoric
#: "Swedish/charcoal" iron acid Bessemer needed. Differs from the phosphoric ore ONLY in its tramp load.
CLEAN_ORE = Ore(
    "Clean ore (Swedish/charcoal)", replace(dc.LEAN_BACKBONE, P=0.012, S=0.018),
    "low tramp phosphorus and sulfur (the scarce non-phosphoric ore) — clean enough that even acid Bessemer "
    "makes sound steel, which is exactly why early Bessemer steelmakers fought over it.",
)

#: The ores, in the order the UI offers them (clean is the "easy" feedstock).
ORES: tuple[Ore, ...] = (PHOSPHORIC_ORE, CLEAN_ORE)


# --------------------------------------------------------------------------- #
# 2. The method — a constrained walk through the F1–F4 engines (the era's technology)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Method:
    """A steelmaking method/era — the **technology** (what refining is possible), distinct from the recipe.

    The method fixes the era's refining *chemistry*: which slag the dephosphorization stage runs
    (``dephos_slag`` — acid vs basic, the phosphorus lever), and whether the era has the secondary-metallurgy
    stages (``can_desulfurize`` — the reducing ladle; ``can_degas`` — vacuum degassing). The player's per-heat
    choices (the Slice-1 gauntlet knobs) are the *recipe*; the method is what the era *allows*. The
    ``conquers`` line names the tramp this era newly masters (the purity ramp), and ``flavor`` lists the
    distinguishing claims that are game-feel, not engine-backed (so the label-correctness test can pin the
    verified/flavor split).
    """

    name: str
    year: int
    era: str                     # short era tag for the UI (e.g. "basic converter")
    dephos_slag: Slag            # the slag the dephosphorization stage runs (acid → L_P≈1, basic → hundreds)
    can_desulfurize: bool        # the era has a reducing ladle desulfurization stage (the sulfur unlock)
    can_degas: bool              # the era has vacuum degassing (modern only)
    blurb: str                   # one-line "what this era is"
    conquers: str                # the tramp this era newly masters ("—" when it conquers nothing new)
    flavor: tuple[str, ...]      # the distinguishing claims that are flavor (period detail / speed / N / scale)

    @property
    def is_modern(self) -> bool:
        """The modern secondary-metallurgy era — the only one with the full gauntlet (desulf + degas)."""
        return self.can_desulfurize and self.can_degas

    @property
    def removes_phosphorus(self) -> bool:
        """Whether this era's dephosphorization slag is basic enough to actually pull phosphorus down.

        Read live from the sealed engine (:func:`steel.slag.phosphorus_partition`) — not a hardcoded flag:
        an acid slag lands ``L_P`` of order 1 (phosphorus stays), a basic one in the hundreds. The threshold
        ``L_P > 10`` cleanly separates the two regimes (the acid/basic jump spans orders of magnitude).
        """
        return sl.phosphorus_partition(self.dephos_slag) > 10.0


# The era ladder — the §15.2 purity-control ramp. Three chemically-distinct tiers (acid converter →
# basic converter → modern ladle); the basic open hearth and BOF share Thomas' chemistry in this model
# (they conquered phosphorus the same way) and differ only in flavor (scale, speed, nitrogen) — stated, and
# pinned by the label test. Ordered by year = the order the tech tree unlocks.
ACID_BESSEMER = Method(
    "Acid Bessemer", 1856, "acid converter",
    dephos_slag=sl.ACID_BESSEMER_SLAG, can_desulfurize=False, can_degas=False,
    blurb="The first cheap bulk steel (Henry Bessemer, 1856): air blown through the melt. Its acid "
          "(siliceous) lining cannot carry a basic slag, so it cannot remove phosphorus — it needs a clean, "
          "non-phosphoric ore.",
    conquers="—",
    flavor=("the air blow is fast and spectacular (the 'flame drop')", "no vacuum, no ladle refining",
            "the aluminium kill is anachronistic here (Al was dear before ~1890) — a modelling abstraction"),
)
THOMAS = Method(
    "Thomas (basic Bessemer)", 1879, "basic converter",
    dephos_slag=sl.BASIC_CONVERTER_SLAG, can_desulfurize=False, can_degas=False,
    blurb="Thomas & Gilchrist's basic (dolomite) lining, 1879: a lime-rich slag fixes the phosphorus as a "
          "stable phosphate. It unlocked the vast phosphoric ore fields of Europe — the single most "
          "consequential metallurgical fix of the century.",
    conquers="phosphorus (basic slag, L_P in the hundreds)",
    flavor=("the basic slag becomes phosphate-rich fertilizer ('Thomas meal')", "no ladle desulfurization yet",
            "the aluminium kill is still anachronistic — a modelling abstraction"),
)
OPEN_HEARTH = Method(
    "Basic open hearth", 1885, "basic open hearth",
    dephos_slag=sl.BASIC_CONVERTER_SLAG, can_desulfurize=False, can_degas=False,
    blurb="Siemens–Martin regenerative furnace with a basic lining (~1880s): same phosphorus chemistry as "
          "Thomas, but slow and large-scale, melting scrap as well as hot metal — it dominated quality "
          "steel for ~70 years.",
    conquers="— (same phosphorus chemistry as Thomas)",
    flavor=("hours per heat, not minutes — a slow, controllable process", "huge heats; melts cold scrap",
            "by this model's chemistry it makes the same heat as Thomas — the difference is scale and "
            "control (flavor)"),
)
BOF = Method(
    "Basic oxygen (BOF)", 1952, "oxygen converter",
    dephos_slag=sl.BASIC_CONVERTER_SLAG, can_desulfurize=False, can_degas=False,
    blurb="The basic oxygen furnace (Linz–Donawitz, 1952): pure oxygen blown onto a basic-slagged bath. As "
          "fast as Bessemer, as clean as open hearth, and — blowing oxygen, not air — it picks up little "
          "nitrogen. The modern workhorse for primary steel.",
    conquers="— (same phosphorus chemistry as Thomas; nitrogen is flavor here)",
    flavor=("~40 minutes for ~300 tonnes", "oxygen (not air) → low dissolved nitrogen — reported, not "
            "spec-flagged in this model", "still needs a ladle to take the sulfur out"),
)
EAF_LADLE = Method(
    "EAF + ladle metallurgy", 1970, "ladle / secondary metallurgy",
    dephos_slag=sl.BASIC_CONVERTER_SLAG, can_desulfurize=True, can_degas=True,
    blurb="Modern secondary metallurgy: after the primary melt (electric arc or BOF) the ladle does the fine "
          "work — a reducing slag pulls the sulfur out on the killed bath, and a vacuum strips hydrogen. "
          "This is the full chain — every tramp under control.",
    conquers="sulfur (reducing ladle slag) + hydrogen (vacuum degassing)",
    flavor=("'secondary metallurgy' — the converter sets carbon, the ladle does the cleanliness",
            "the only era with the full Slice-1 gauntlet"),
)

#: The methods, oldest → newest = the tech-tree unlock order. ``EAF_LADLE`` is the modern default (its
#: reference run reproduces the capstone golden run exactly).
METHODS: tuple[Method, ...] = (ACID_BESSEMER, THOMAS, OPEN_HEARTH, BOF, EAF_LADLE)

#: The default method — the modern full chain (Slice 0/1's route). New games default here so the golden run
#: (modern method + phosphoric ore + reference recipe) is unchanged.
MODERN = EAF_LADLE


#: The bloomery — named as the era-0 floor, NOT a playable 4140 walk (the named ceiling above). Surfaced as
#: prose so the tech tree shows where the ramp starts, without faking a hardenable-steel verdict it cannot
#: reach (the bloomery stays *below* the F1 carbon/CO crossover — direct solid-state reduction to low-carbon,
#: slag-laden wrought iron — so it cannot make hardenable alloy steel at all).
BLOOMERY_NOTE: str = (
    "Before the converters: the **bloomery** (ancient–medieval) reduced ore in the solid state, below the "
    "F1 carbon/CO crossover, to a low-carbon, slag-laden wrought iron. It is the floor of the purity ramp — "
    "but it cannot make hardenable alloy steel at all, so it is not a playable 4140 route here (a different "
    "product on a different walk — a named deferral)."
)
