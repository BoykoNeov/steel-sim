"""Metastable Fe–Fe₃C equilibrium: phase boundaries + the lever rule (Steel Phase 1b).

The thermodynamic *endpoint* of the steel simulator. Given a steel's carbon
content and a temperature, this module says which phases coexist and in what
proportion — the equilibrium the Phase-1c transformation kinetics drive *toward*,
and whose undercooling below the boundary temperatures *is* the driving force.

The diagram (what is modelled)
------------------------------
The **metastable** Fe–Fe₃C system (cementite, not graphite — the relevant one for
steels). Four phases appear in the solid range:

  * **austenite** (γ, FCC) — the high-temperature solvent, max **2.11 wt% C** at
    **1147 °C** (``C_GAMMA_MAX`` / ``T_GAMMA_MAX``).
  * **ferrite** (α, BCC) — low-temperature, nearly pure iron, max **0.022 wt% C**
    at **727 °C** (``C_ALPHA_MAX``).
  * **cementite** (Fe₃C) — the stoichiometric carbide, fixed at **6.70 wt% C**
    (``C_CEMENTITE``; the exact stoichiometric value 12.011/(3·55.845+12.011) =
    6.69 wt%, rounded to the diagram convention).
  * **pearlite** — not a phase but the lamellar α+Fe₃C *constituent* produced by
    the eutectoid reaction γ → α + Fe₃C at **727 °C / 0.76 wt% C** (``A1`` /
    ``C_EUTECTOID``).

The phase-boundary lines:

  * **A₁** — the eutectoid isotherm, a horizontal line at 727 °C.
  * **A₃** — the γ/(α+γ) transus on the *hypo*eutectoid side, falling from
    912 °C at 0 % C (pure-iron γ→α) to 727 °C at the eutectoid.
  * **A_cm** — the γ/(γ+Fe₃C) transus on the *hyper*eutectoid side, rising from
    727 °C at the eutectoid to 1147 °C at 2.11 % C.

Boundary approximation (the deliberate modelling choice)
--------------------------------------------------------
A₃ and A_cm are gently curved on the real diagram; here they are **linear between
their pinned invariant points** (Steel plan §3, §10). This makes the invariant
points — eutectoid (0.76 %/727 °C), γ-max (2.11 %/1147 °C), pure-iron A₃ (912 °C)
— **exact by construction**, which is exactly what the validation triad's
"lever-rule fractions exact at a chosen (T, %C)" leg requires. The ferrite solvus
is likewise linear from 0.022 % at 727 °C to 0 % at 912 °C on the α/(α+γ) side; on
the α/(α+Fe₃C) side below 727 °C it is **held at 0.022 %** (its further descent to
~0 at room temperature is a sub-percent correction to the lever rule and is
documented-but-omitted in v1). Phase 4 swaps these parametrized lines for
CALPHAD-computed equilibria; consumers see the same outputs.

The lever rule (what is computed)
---------------------------------
On a tie-line through a two-phase field at overall composition ``C0``, the
fraction of the phase at end ``C_far`` is the *opposite* lever arm over the whole
tie-line:  ``f = (C_other − C0) / (C_other − C_this)``. This is nothing but a
**carbon mass balance** — ``Σ fᵢ·Cᵢ = C0`` — so all fractions here are **mass
fractions** (not volume or mole), and that identity is the module's conservation
invariant. Learners routinely conflate mass with volume fractions; Phase-3
property models care about the distinction, so it is fixed here.

Two readings are exposed, and the difference between them is *the* subtlety of
this diagram:

  * :func:`phase_fractions` — the raw **phase** fractions (ferrite / austenite /
    cementite) at an arbitrary (C0, T) point. The plain inter-module currency
    (a dict; Steel plan §5).
  * :func:`equilibrium_constituents` — the slow-cooled **microstructural
    constituents**: *pro-eutectoid* ferrite or cementite (formed between the
    transus and A₁) plus *pearlite* (the eutectoid product), read just below A₁.
    This is the teaching payoff — dramatic on hypoeutectoid AISI 1045, near-
    degenerate on eutectoid-ish 1080 (Steel plan §1, §3).

Units & conventions
-------------------
* **Composition** ``C`` is **wt% carbon** (e.g. 0.45 for AISI 1045), not a
  fraction. All returned phase fractions are **mass fractions in [0, 1]**.
* **Temperature** ``T`` is **°C** — the universal convention for the Fe-C diagram
  and the Aₙ temperatures. The kinetics layer (Phase 1c) converts to kelvin at
  its Arrhenius/Andrews boundary; equilibrium needs no absolute zero.
* **The eutectoid isotherm.** ``T = 727 °C`` is genuinely ambiguous (γ above,
  α+Fe₃C below — the reaction is isothermal). By convention :func:`phase_fractions`
  treats ``T ≥ 727`` as the **austenite-bearing** side, where the boundary
  compositions are exactly (Cγ, Cα) = (0.76, 0.022); ``T < 727`` is α+Fe₃C. So the
  austenite fraction *at* 727 °C equals the pearlite fraction that austenite then
  becomes — the consistency :func:`equilibrium_constituents` relies on.
"""
from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Pinned invariant points of the metastable Fe–Fe₃C diagram (wt% C, °C).
# These are the *exact* values the linear boundaries interpolate between and the
# benchmark the validation triad reproduces (Steel plan §3 / §4 Phase-4 limit).
# --------------------------------------------------------------------------- #
C_EUTECTOID = 0.76      # eutectoid composition (γ → α + Fe₃C)
T_EUTECTOID = 727.0     # eutectoid temperature = A₁ (the eutectoid isotherm)
T_A3_PURE_IRON = 912.0  # A₃ at 0 % C: the pure-iron γ→α (α↔γ) transition
C_GAMMA_MAX = 2.11      # max C solubility in austenite (γ), at T_GAMMA_MAX
T_GAMMA_MAX = 1147.0    # temperature of γ-max (the eutectic isotherm)
C_ALPHA_MAX = 0.022     # max C solubility in ferrite (α), at the eutectoid T
C_CEMENTITE = 6.70      # Fe₃C carbon content (stoichiometric 6.69, diagram 6.70)

# The valid carbon window: 0 .. γ-max. Above 2.11 % C the solidification eutectic
# (ledeburite) appears and the simple solid-state lever rule no longer applies —
# cast irons are out of v1 scope (Steel plan §5 names the steel range).
_C_MIN, _C_MAX = 0.0, C_GAMMA_MAX


# --------------------------------------------------------------------------- #
# Phase boundaries (temperature as a function of composition)
# --------------------------------------------------------------------------- #
def A1() -> float:
    """The eutectoid temperature A₁ (°C) — the horizontal eutectoid isotherm."""
    return T_EUTECTOID


def A3(C: float) -> float:
    """A₃: the γ/(α+γ) transus (°C) for a hypoeutectoid composition ``C`` (wt%).

    Linear from 912 °C at 0 % C to 727 °C at the eutectoid (0.76 %). Valid for
    ``0 ≤ C ≤ C_EUTECTOID``; this is the temperature below which pro-eutectoid
    ferrite begins to form on cooling.
    """
    if not (_C_MIN <= C <= C_EUTECTOID):
        raise ValueError(f"A3 is defined for 0 ≤ C ≤ {C_EUTECTOID} wt%, got {C}")
    return T_A3_PURE_IRON + (T_EUTECTOID - T_A3_PURE_IRON) * (C / C_EUTECTOID)


def Acm(C: float) -> float:
    """A_cm: the γ/(γ+Fe₃C) transus (°C) for a hypereutectoid ``C`` (wt%).

    Linear from 727 °C at the eutectoid (0.76 %) to 1147 °C at γ-max (2.11 %).
    Valid for ``C_EUTECTOID ≤ C ≤ C_GAMMA_MAX``; below it pro-eutectoid cementite
    begins to form on cooling.
    """
    if not (C_EUTECTOID <= C <= C_GAMMA_MAX):
        raise ValueError(
            f"Acm is defined for {C_EUTECTOID} ≤ C ≤ {C_GAMMA_MAX} wt%, got {C}"
        )
    span = (T_GAMMA_MAX - T_EUTECTOID) / (C_GAMMA_MAX - C_EUTECTOID)
    return T_EUTECTOID + span * (C - C_EUTECTOID)


# --------------------------------------------------------------------------- #
# Phase boundaries (composition as a function of temperature) — the tie-line
# end-member compositions the lever rule reads off.
# --------------------------------------------------------------------------- #
def austenite_C_with_ferrite(T: float) -> float:
    """Cγ on the A₃ boundary (wt%): austenite composition in equilib. with α.

    The inverse of :func:`A3` — austenite carbon along the hypoeutectoid γ-side
    tie-line end. 0.76 % at 727 °C, falling to 0 % at 912 °C. Valid for
    ``727 ≤ T ≤ 912``.
    """
    if not (T_EUTECTOID <= T <= T_A3_PURE_IRON):
        raise ValueError(
            f"defined for {T_EUTECTOID} ≤ T ≤ {T_A3_PURE_IRON} °C, got {T}"
        )
    frac = (T_A3_PURE_IRON - T) / (T_A3_PURE_IRON - T_EUTECTOID)
    return C_EUTECTOID * frac


def austenite_C_with_cementite(T: float) -> float:
    """Cγ on the A_cm boundary (wt%): austenite composition in equilib. with Fe₃C.

    The inverse of :func:`Acm` — austenite carbon along the hypereutectoid γ-side
    tie-line end. 0.76 % at 727 °C, rising to 2.11 % at 1147 °C. Valid for
    ``727 ≤ T ≤ 1147``.
    """
    if not (T_EUTECTOID <= T <= T_GAMMA_MAX):
        raise ValueError(
            f"defined for {T_EUTECTOID} ≤ T ≤ {T_GAMMA_MAX} °C, got {T}"
        )
    span = (C_GAMMA_MAX - C_EUTECTOID) / (T_GAMMA_MAX - T_EUTECTOID)
    return C_EUTECTOID + span * (T - T_EUTECTOID)


def ferrite_C(T: float) -> float:
    """Cα on the ferrite solvus (wt%): carbon solubility in ferrite at ``T``.

    On the α/(α+γ) side (727–912 °C) it falls linearly from 0.022 % at 727 °C to
    0 % at 912 °C (mirroring :func:`austenite_C_with_ferrite`, so the α+γ field
    pinches shut at the pure-iron point). On the α/(α+Fe₃C) side (below 727 °C) it
    is **held at 0.022 %** — the documented v1 simplification (its real descent
    toward ~0 at room T is a sub-percent lever-rule correction). Valid for
    ``T ≤ 912``.
    """
    if T > T_A3_PURE_IRON:
        raise ValueError(f"ferrite solvus is defined for T ≤ {T_A3_PURE_IRON} °C, got {T}")
    if T <= T_EUTECTOID:
        return C_ALPHA_MAX
    frac = (T_A3_PURE_IRON - T) / (T_A3_PURE_IRON - T_EUTECTOID)
    return C_ALPHA_MAX * frac


# --------------------------------------------------------------------------- #
# The lever rule — equilibrium phase fractions at an arbitrary (C0, T)
# --------------------------------------------------------------------------- #
def _check_C0(C0: float) -> None:
    if not (_C_MIN <= C0 <= _C_MAX):
        raise ValueError(
            f"carbon content must be 0 ≤ C0 ≤ {_C_MAX} wt% (steel range); got {C0}. "
            "Cast irons (>2.11 %) involve the solidification eutectic — out of v1 scope."
        )


def _fractions(ferrite: float = 0.0, austenite: float = 0.0, cementite: float = 0.0) -> dict:
    """A phase-fraction dict with the stable, always-present key set.

    Absent phases are 0.0 (never missing), so consumers index without KeyError —
    this dict is the loose-coupling currency between steel modules (plan §5).
    """
    return {"ferrite": ferrite, "austenite": austenite, "cementite": cementite}


def phase_fractions(C0: float, T: float) -> dict:
    """Equilibrium **mass** fractions of the phases present at ``(C0, T)``.

    Parameters
    ----------
    C0 : float
        Overall carbon content, **wt%** (0 ≤ C0 ≤ 2.11; the steel range).
    T : float
        Temperature, **°C**.

    Returns
    -------
    dict
        ``{"ferrite": …, "austenite": …, "cementite": …}`` — mass fractions
        summing to 1, with 0.0 for any absent phase. Single-phase regions return
        a single 1.0 (the lever rule is not applied where the tie-line has no
        width). On the eutectoid isotherm ``T = 727`` the austenite-bearing side
        is returned by convention (see the module docstring).

    The result is the carbon mass balance made explicit: ``Σ fᵢ·Cᵢ = C0`` with
    ``C_ferrite = ferrite_C(T)``, ``C_austenite`` the relevant γ-side boundary,
    ``C_cementite = 6.70``.
    """
    _check_C0(C0)

    if T >= T_EUTECTOID:  # austenite-bearing side of the eutectoid isotherm
        if C0 <= C_EUTECTOID:  # hypoeutectoid: single-γ above A₃, else α + γ
            if T >= A3(C0):
                return _fractions(austenite=1.0)
            Cg = austenite_C_with_ferrite(T)
            Ca = ferrite_C(T)
            if C0 <= Ca:  # left of the ferrite solvus (low-C wedge) → single-phase α
                return _fractions(ferrite=1.0)
            f_ferrite = (Cg - C0) / (Cg - Ca)
            return _fractions(ferrite=f_ferrite, austenite=1.0 - f_ferrite)
        else:  # hypereutectoid: single-γ above A_cm, else γ + Fe₃C
            if T >= Acm(C0):
                return _fractions(austenite=1.0)
            Cg = austenite_C_with_cementite(T)
            f_cem = (C0 - Cg) / (C_CEMENTITE - Cg)
            return _fractions(austenite=1.0 - f_cem, cementite=f_cem)

    # Below the eutectoid isotherm: ferrite + cementite (or single-phase ferrite
    # at very low carbon, where C0 sits left of the ferrite solvus).
    Ca = ferrite_C(T)
    if C0 <= Ca:
        return _fractions(ferrite=1.0)
    f_cem = (C0 - Ca) / (C_CEMENTITE - Ca)
    return _fractions(ferrite=1.0 - f_cem, cementite=f_cem)


# --------------------------------------------------------------------------- #
# Slow-cooled microstructural constituents (the teaching payoff)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Constituents:
    """Slow-cooled equilibrium microstructure of a steel, read just below A₁.

    The same carbon, two complementary readings (all **mass fractions in [0,1]**):

    * **Constituent reading** — what you see under the microscope:
      ``proeutectoid`` (``"ferrite"`` | ``"cementite"`` | ``"none"``) at fraction
      ``f_proeutectoid``, the rest being lamellar ``f_pearlite``. The pro-eutectoid
      phase forms between the transus (A₃ or A_cm) and A₁; the remaining austenite,
      having reached the eutectoid composition, becomes pearlite at A₁.
    * **Phase reading** — the total ferrite / cementite once pearlite is itself
      resolved into its α+Fe₃C lamellae: ``f_ferrite_total`` + ``f_cementite_total``.

    The two readings are consistent by construction: the constituents re-summed by
    phase reproduce the totals, and both conserve carbon (``Σ fᵢCᵢ = C0``).
    """

    C0: float
    proeutectoid: str
    f_proeutectoid: float
    f_pearlite: float
    f_ferrite_total: float
    f_cementite_total: float


def equilibrium_constituents(C0: float) -> Constituents:
    """Slow-cool a steel of carbon ``C0`` (wt%) to just below A₁; report its phases.

    The Phase-1b headline. Returns a :class:`Constituents` with both the
    pro-eutectoid + pearlite *constituent* split and the total ferrite/cementite
    *phase* split, evaluated with the eutectoid-line boundary compositions
    (Cα = 0.022, Cγ = 0.76, C_Fe₃C = 6.70 — the conventional reference state).

    * **Hypoeutectoid** (C0 < 0.76): pro-eutectoid **ferrite** + pearlite.
      Showcased on AISI 1045 (0.45 %): ~42 % pro-eutectoid ferrite, ~58 % pearlite.
    * **Eutectoid** (C0 = 0.76): essentially all pearlite (pro-eutectoid → 0).
    * **Hypereutectoid** (C0 > 0.76): pro-eutectoid **cementite** + pearlite. AISI
      1080 (0.80 %) is *slightly* hypereutectoid — ~0.7 % pro-eutectoid cementite,
      the near-degenerate case the plan contrasts with 1045.
    * **C0 ≤ 0.022**: below the ferrite solubility — single-phase ferrite, no
      pearlite.
    """
    _check_C0(C0)

    # Total ferrite / cementite: the direct α/Fe₃C lever rule at 727⁻.
    f_ferrite_total = (C_CEMENTITE - C0) / (C_CEMENTITE - C_ALPHA_MAX)
    f_cementite_total = (C0 - C_ALPHA_MAX) / (C_CEMENTITE - C_ALPHA_MAX)

    if C0 <= C_ALPHA_MAX:  # left of the ferrite solvus → all ferrite, no pearlite
        return Constituents(
            C0=C0, proeutectoid="ferrite", f_proeutectoid=1.0, f_pearlite=0.0,
            f_ferrite_total=1.0, f_cementite_total=0.0,
        )

    if C0 < C_EUTECTOID:  # hypoeutectoid: pro-eutectoid ferrite + pearlite
        span = C_EUTECTOID - C_ALPHA_MAX
        f_pro = (C_EUTECTOID - C0) / span
        f_pearlite = (C0 - C_ALPHA_MAX) / span
        proeutectoid = "ferrite"
    elif C0 > C_EUTECTOID:  # hypereutectoid: pro-eutectoid cementite + pearlite
        span = C_CEMENTITE - C_EUTECTOID
        f_pro = (C0 - C_EUTECTOID) / span
        f_pearlite = (C_CEMENTITE - C0) / span
        proeutectoid = "cementite"
    else:  # exactly eutectoid: all pearlite
        f_pro, f_pearlite, proeutectoid = 0.0, 1.0, "none"

    return Constituents(
        C0=C0, proeutectoid=proeutectoid, f_proeutectoid=f_pro, f_pearlite=f_pearlite,
        f_ferrite_total=f_ferrite_total, f_cementite_total=f_cementite_total,
    )


# The cementite mass fraction *within* pearlite (eutectoid γ resolved into α+Fe₃C):
# (0.76 − 0.022)/(6.70 − 0.022) ≈ 0.1105. The classic "pearlite is ~11 % cementite,
# ~89 % ferrite" — the link that makes the constituent and phase readings consistent.
PEARLITE_CEMENTITE_FRACTION = (C_EUTECTOID - C_ALPHA_MAX) / (C_CEMENTITE - C_ALPHA_MAX)
