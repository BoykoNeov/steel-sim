"""``game.knobs`` — the player knob as **value-selection on the C–O τ-curve** (Slice 0's one knob).

The plan's honest reframing of the iconic Bessemer "flame-drop, stop NOW" (``game.md`` §3.3): Streamlit
reruns do reflex timing badly, so the decarb blow is a **value-selection**, not a reaction test. The
player sets the blow *endpoint* (a carbon target); this module turns that choice into the two curves the
UI draws and the position readout it shows — built entirely from the **validated** F2 refining engine.

What is validated vs what is feel (the verified-vs-flavor contract, ``game.md`` §5.3):

* **Validated (the physics).** The dissolved-oxygen reading at any carbon endpoint is the C–O coupling
  :func:`steel.refining.equilibrium_oxygen` (``[%C]·[%O] = p_CO / K_CO``): drive carbon down and
  equilibrium oxygen climbs. The grade **carbon window** is the cited
  :data:`steel.ladle.GRADE_WINDOWS` band, and the **aim** is the grade's nominal carbon. These are the
  ``optimum`` the blow targets — *physics, not feel*.
* **Flavor (game feel, labelled).** The *trajectory shape* — carbon falling first-order with blow time
  toward the chosen endpoint — is a Tier-3 kinetic cartoon (``steel-making.md`` §16): a plausible
  relaxation, **not** a validated rate. Only the shape is feel; both endpoints it runs between are
  validated.

No streamlit, no matplotlib here (the ``app.py`` three-layer discipline) — this is pure logic the figure
builder and the why-cards read, and the always-green tests pin.
"""
from __future__ import annotations

from dataclasses import dataclass

from steel import demo_capstone as dc
from steel import ladle as ld
from steel import refining as ref
from steel.sweep import STEELS

# The grade the Slice-0 method makes (the capstone's 4140 route — single-sourced from the demo).
GRADE: str = dc.GRADE

# The blow-endpoint slider span (wt % carbon): wide enough to straddle the under-blow side (carbon too
# high → off-grade high), the grade window, and the over-blow side (carbon too low → off-grade low + the
# bath over-oxidized). The reference (0.40) and the capstone foil (0.25) both sit inside it.
BLOW_C_MIN: float = 0.18
BLOW_C_MAX: float = 0.55

# The carbon-saturated charge the blow starts from (single-sourced from the capstone recipe) — the top of
# the flavor trajectory.
CHARGE_CARBON: float = dc.CHARGE_CARBON

# The flavor blow-trajectory time constant (Tier-3 kinetics, NOT validated): the fraction of the blow over
# which carbon relaxes toward the endpoint. Labelled "plausible" everywhere it surfaces.
BLOW_TAU: float = 0.30


# --------------------------------------------------------------------------- #
# 1. The validated reads — straight off the F2 refining engine
# --------------------------------------------------------------------------- #
def grade_carbon_window() -> tuple[float, float]:
    """The cited 4140 carbon window ``(lo, hi)`` wt % — the validated grade aim band (``ladle``)."""
    lo, hi = ld.GRADE_WINDOWS[GRADE].bands["C"]
    return float(lo), float(hi)


def grade_carbon_aim() -> float:
    """The grade's nominal carbon (wt %) — the blow's target, the Type-B optimum (``sweep.STEELS``)."""
    return float(STEELS[GRADE].C)


def dissolved_oxygen(carbon_pct: float) -> float:
    """Equilibrium dissolved oxygen (**ppm**) at a carbon endpoint — the validated C–O coupling.

    A pass-through to :func:`steel.refining.equilibrium_oxygen` (no game arithmetic on top): driving
    carbon down drives oxygen up. This is the number the over-blow readout and the why-cards quote *live*.
    """
    return float(ref.equilibrium_oxygen(carbon_pct))


def carbon_oxygen_product() -> float:
    """The validated C–O product ``[%C]·[%O]`` at tap temperature (``refining``) — the curve's constant."""
    return float(ref.carbon_oxygen_product())


def oxygen_curve(n: int = 60) -> tuple[list[float], list[float]]:
    """``(carbons, oxygens)`` across the blow-endpoint span — the validated C–O curve the figure draws.

    ``carbons`` is a uniform sweep over ``[BLOW_C_MIN, BLOW_C_MAX]``; ``oxygens`` is
    :func:`dissolved_oxygen` at each. Monotone decreasing in carbon (the C–O coupling), and *exactly* the
    refining engine's values — the endpoint-consistency test pins both.
    """
    step = (BLOW_C_MAX - BLOW_C_MIN) / (n - 1)
    carbons = [BLOW_C_MIN + i * step for i in range(n)]
    oxygens = [dissolved_oxygen(c) for c in carbons]
    return carbons, oxygens


# --------------------------------------------------------------------------- #
# 2. The flavor trajectory — game feel, labelled plausible (Tier-3 kinetics)
# --------------------------------------------------------------------------- #
def blow_trajectory(carbon_target: float, n: int = 60) -> tuple[list[float], list[float]]:
    """``(progress, carbons)`` for the blow trajectory — **flavor**, a first-order relaxation cartoon.

    ``progress`` runs 0→1 (fraction of the blow); ``carbons`` falls from :data:`CHARGE_CARBON` to
    ``carbon_target`` with the first-order *shape* ``e^(−p/τ)``, **normalized** so the curve starts exactly
    at the charge carbon and **lands exactly on the player's endpoint** at ``p = 1`` (the value they
    selected). This is the Type-B "feel" of the blow — fast at first, slowing as the endpoint nears —
    **not a validated rate** (the decarb kinetics are the transport tar-pit the project keeps as flavor).
    Only the shape is feel; both ends it runs between are honest.
    """
    import math

    step = 1.0 / (n - 1)
    progress = [i * step for i in range(n)]
    d1 = math.exp(-1.0 / BLOW_TAU)                       # decay at p=1, factored out so C(1) == target exactly
    span = CHARGE_CARBON - carbon_target
    carbons = [carbon_target + span * (math.exp(-p / BLOW_TAU) - d1) / (1.0 - d1) for p in progress]
    return progress, carbons


# --------------------------------------------------------------------------- #
# 3. The position readout — where the chosen endpoint sits (the "flame-drop" as a position)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EndpointPosition:
    """Where a blow endpoint lands relative to the validated grade window — the value-selection readout.

    ``zone`` is ``"under-blow"`` (carbon above the window — didn't blow enough, off-grade high),
    ``"on-aim"`` (inside the window), or ``"over-blow"`` (below the window — over-oxidized + off-grade
    low). ``oxygen_ppm`` is the validated dissolved oxygen there; ``window``/``aim`` the cited targets.
    """

    carbon: float
    oxygen_ppm: float
    zone: str
    window: tuple[float, float]
    aim: float


def endpoint_position(carbon_target: float) -> EndpointPosition:
    """Classify a blow endpoint against the validated grade window and read the dissolved oxygen there.

    The "flame-drop, stop NOW" reframed as a **position** (``game.md`` §3.3): not a clock, but where the
    chosen endpoint sits on the validated curve. Inside the window → on aim; below it → over-blow (the
    bath over-oxidized, the heat off-grade low → a soft core at the quench); above it → under-blow.
    """
    lo, hi = grade_carbon_window()
    if carbon_target > hi:
        zone = "under-blow"
    elif carbon_target < lo:
        zone = "over-blow"
    else:
        zone = "on-aim"
    return EndpointPosition(
        carbon=float(carbon_target),
        oxygen_ppm=dissolved_oxygen(carbon_target),
        zone=zone,
        window=(lo, hi),
        aim=grade_carbon_aim(),
    )
