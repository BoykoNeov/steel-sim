"""``game.postmortem`` — judge the finished part with the sealed consequence engines (Slice 1's teeth).

The gauntlet's losing move is a **latent flaw** a wrong choice plants in the live ``Heat``: dissolved
oxygen the kill left high, hydrogen a shallow vacuum left in, tramp sulfur a skipped slag left, tramp
phosphorus a skipped converter left. None of these are visible in the running chain — they ride on the
``Heat``'s state fields and surface only when the part is put to use. This module is the **post-mortem**:
it runs the repo's already-benchmarked consequence engines on the finished part and reports which defect
each latent flaw became, and which stage planted it.

Two disciplines, both load-bearing (``game.md`` §3, §5.3):

* **It reads, it never mutates.** Every check here runs on the *finished* part and inspects the result; the
  canonical chain ``Heat`` is untouched. That is what keeps the golden-run equality
  (``play_to_end(reference) == run_chain``) **exact** — the post-mortem is a separate read, not a ninth
  stage. (Mirrors the stateless what-if posture of :mod:`steel.app_consequences`, which composes these same
  engines without threading them into a spine.)
* **No new physics.** Each verdict is a sealed engine's own: :func:`steel.gas_porosity.gas_porosity_check`
  (CO blowholes from ``[%C][%O]``), :func:`steel.hydrogen_flaking.hydrogen_flaking_check` (Crank slab
  desorption), :func:`steel.hot_work.hot_work` (red-short Fe–FeS film), :func:`steel.hot_tear.hot_tear_check`
  (segregation-amplified film), :func:`steel.heat_state.cold_short_check` (phosphorus → DBTT). The game only
  *composes* them and attributes each to the stage whose knob controls the flaw.

**Field survival (the correctness caveat, ``game.md`` §3).** A consequence is only physical if the field it
reads still carries the value its stage locked. In this chain that holds: phosphorus / oxygen / hydrogen /
sulfur are set by their refining stage and only *diluted* by the later trim mass-balance (never re-raised),
and trim precedes casting and the composition-inert heat-treat — so the finished part faithfully carries
every flaw at its physical value. The losability tests pin this empirically (a wrong knob flips the verdict
end-to-end, not just at its own step). Quench-crack is **out of scope for this grade** — its §18 residual
engine is keyed to the anchored atlas steels (1080/4340), not 4140 — so the heat-treat stage's failure is
the soft core (the back-end martensite spec), not a crack.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from steel import gas_porosity as gp
from steel import hot_tear as ht
from steel import hot_work as hw
from steel import hydrogen_flaking as hf
from steel import slag as sl
from steel.heat_state import COLD_SHORT, Heat, cold_short_check

#: A residual-sulfur reading over this cleanliness spec is off-grade dirty even when manganese ties it as
#: MnS (so it does not red-short) — the honest losability lever for a skipped desulfurization.
HIGH_SULFUR_SPEC: str = "high-sulfur-spec"

if TYPE_CHECKING:                                    # avoid an import cycle (state imports us lazily)
    from .state import Recipe


@dataclass(frozen=True)
class Consequence:
    """One manifested defect — what a latent flaw became, and which stage planted it.

    ``flag`` the engine's defect constant (e.g. ``"gas-porosity"``); ``headline`` a short human name;
    ``planted_by`` the stage whose knob controls the flaw; ``detail`` the engine's own summary line, carrying
    the **live numbers** (the carbon/oxygen product, the residual hydrogen, the film Mn:S) — never a canned
    string. ``knob`` the :class:`~game.state.Recipe` field the player set wrong.
    """

    flag: str
    headline: str
    planted_by: str
    knob: str
    detail: str

    def as_dict(self) -> dict:
        return {
            "flag": self.flag,
            "headline": self.headline,
            "planted_by": self.planted_by,
            "knob": self.knob,
            "detail": self.detail,
        }


def _last_summary(heat: Heat) -> str:
    """The summary of the consequence engine's appended step — its live-number verdict line."""
    return heat.history[-1].summary


def post_mortem(part: Heat, *, recipe: "Recipe") -> list[Consequence]:
    """Run the sealed consequence engines on the finished part; return the defects that fired.

    A separate read — the part ``Heat`` is never mutated (golden-run stays exact). Each engine is run only
    when the part carries the state it needs (a refining stage may have been skipped, but it still fills the
    field; the dissolved-O / dissolved-H guards are belt-and-braces). The order is the chain's own:
    phosphorus → oxygen → hydrogen → sulfur (forging, then casting).
    """
    out: list[Consequence] = []

    # Phosphorus → cold-short. Gated on the part actually carrying tramp phosphorus over spec: the §3 DBTT
    # law also climbs with carbon (more pearlite), so a high-carbon over-blow can read brittle with clean P —
    # that is the *carbon* mistake (already off-grade + soft-core), not the dephosphorization knob's. The
    # gate attributes cold-short to dephosphorization only when phosphorus is genuinely the driver.
    if part.composition.P > sl.MAX_PHOSPHORUS_PCT:
        cs = cold_short_check(part)
        if cs.has_defect(COLD_SHORT):
            out.append(Consequence(COLD_SHORT, "cold-short (phosphorus)", "dephosphorize",
                                   "dephosphorize", _last_summary(cs)))

    # Oxygen → gas porosity (a weak kill — Si/Mn, not Al — can't drop O below the C–O line; CO blows holes).
    if part.oxygen_ppm is not None:
        por = gp.gas_porosity_check(part)
        if por.has_defect(gp.GAS_POROSITY):
            out.append(Consequence(gp.GAS_POROSITY, "gas porosity (oxygen)", "deoxidize",
                                   "deoxidizer", _last_summary(por)))

    # Hydrogen → flaking (a shallow vacuum leaves dissolved H above the flaking limit in this section).
    if part.hydrogen_ppm is not None:
        fl = hf.hydrogen_flaking_check(part, half_thickness=recipe.part_diameter / 2.0)
        if fl.has_defect(hf.HYDROGEN_FLAKING):
            out.append(Consequence(hf.HYDROGEN_FLAKING, "hydrogen flaking", "degas",
                                   "degas_p_H2", _last_summary(fl)))

    # Sulfur → red-short on forging (free S forms a Fe–FeS film above the eutectic).
    rs = hw.hot_work(part)
    red_short = rs.has_defect(hw.RED_SHORT)
    if red_short:
        out.append(Consequence(hw.RED_SHORT, "red-short (sulfur)", "desulfurize",
                               "desulfurize", _last_summary(rs)))

    # Sulfur → hot-tear on casting (segregation amplifies the film Mn:S below stoichiometry).
    tear = ht.hot_tear_check(part)
    hot_tear = tear.has_defect(ht.HOT_TEAR)
    if hot_tear:
        out.append(Consequence(ht.HOT_TEAR, "hot-tear (sulfur)", "desulfurize",
                              "desulfurize", _last_summary(tear)))

    # Sulfur → off-spec cleanliness. The honest losability lever for a skipped desulfurization: at this seed
    # the trim's manganese ties the sulfur as high-melting MnS (no red-short, no hot-tear above) — yet the
    # residual sulfur is still over the cleanliness spec, so the heat is off-grade dirty. Only surfaced when
    # no sulfur *mechanism* fired (those are the louder defect, and carry the same root cause).
    if not red_short and not hot_tear and part.composition.S > sl.MAX_SULFUR_PCT:
        detail = (f"residual S {part.composition.S:.3f} % over the {sl.MAX_SULFUR_PCT:.3f} % spec "
                  f"(Mn {part.composition.Mn:.2f} % ties it as MnS — no red-short, but off-grade dirty)")
        out.append(Consequence(HIGH_SULFUR_SPEC, "sulfur over spec", "desulfurize", "desulfurize", detail))

    return out
