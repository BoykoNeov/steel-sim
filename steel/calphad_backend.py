"""CALPHAD-backed equilibrium via pycalphad — the bounded deep end (Steel Phase 4).

Phase 1b's :mod:`fe_c` draws the metastable Fe–Fe₃C diagram as **linear chords**
between pinned invariant points. That makes the invariant points exact *by
construction* — and everything in between an approximation. Phase 4 swaps those
chords for a real **Gibbs-energy minimisation** (pycalphad) over an assessed
thermodynamic database, so the phase boundaries *emerge* from the free energies
rather than being drawn, and the model **extends to multicomponent low-alloy
steels** (Fe-C-Cr-Mn-Mo-…) that ``fe_c`` cannot represent at all.

This is consumed as an **optional backend** (plan §2/§6: *CALPHAD is consumed, not
reimplemented*). pycalphad is an optional dependency (the ``[calphad]`` extra); the
thermodynamic databases are **never committed** (plan §6 / ``.gitignore``). The
always-green committed validation rests on a frozen reference table generated from
this module (:mod:`calphad_reference`); a live test re-derives it when pycalphad and
a database are present.

What the validation triad rests on (see ``tests/test_calphad.py``)
-----------------------------------------------------------------
* **Analytical limit** — the Fe-C **invariant points** *emerge*: eutectoid
  ≈ 727 °C / 0.76 %C and γ-max ≈ 2.11 %C / 1147 °C, computed from the free
  energies, not input. (This is a *wiring* check — those values are pinned by
  construction in ``fe_c``, so agreeing there is necessary but not probative.)
* **Conservation** — the lever rule is a mass balance: from CALPHAD's phase
  amounts and per-phase compositions, ``Σ fᵢ·Cᵢ = C0`` closes to machine
  precision (a free correctness check on the equilibrium output).
* **Benchmark — the leg with teeth** — CALPHAD's *curved* A₃ transus vs ``fe_c``'s
  *linear chord* quantifies "what the parametrised version got wrong" (the chord
  over-predicts A₃ by tens of °C at mid-carbon); and a **4140** low-alloy steel's
  A₁/A₃ — which ``fe_c`` cannot touch — agrees with the independent **Andrews**
  Ae1/Ae3 empirical formulae within their scatter (loose bands; an alloy steel's
  A₁ with stable Cr-carbides is not a sharp eutectoid point).

Databases used (validation references — never redistributed, never committed)
----------------------------------------------------------------------------
* **Fe-C (binary):** ``cfe_broshe.tdb``, *bundled inside the installed pycalphad
  package* (``pycalphad/tests/databases/``). Present on any ``pip install``ed
  pycalphad → the binary live tests run with no external file.
* **Multicomponent steel:** ``mc_fe_v2.060.tdb``, the **openly-licensed (ODbL 1.0)**
  MatCalc steel database (assessed at TU Wien by E. Povoden-Karadeniz). Downloaded
  by the user to ``data/tdb/`` (gitignored) or pointed to by ``$BIGSIM_STEEL_TDB``;
  the multicomponent live tests skip if it is absent. See ``download_mc_fe`` below.

Two environment workarounds (documented, validated by the physical results)
--------------------------------------------------------------------------
This runs on Python 3.14, where pycalphad 0.11.2 needs two nudges; both are honest
compatibility shims, not changes to the thermodynamics, and the invariant-point and
Andrews benchmarks are what prove they are harmless:

1. **symengine pin** — pycalphad 0.11.2 pins ``symengine<0.14`` but only
   ``symengine==0.14.1`` ships a 3.14 wheel. Install with the cap overridden
   (``pip install symengine==0.14.1`` then ``pip install pycalphad --no-deps`` +
   its other deps); the reproduced eutectoid confirms 0.14 is fine. *Install-time
   only — nothing here depends on it at run time.*
2. **PEP-749 annotations** — pycalphad's ``Workspace.__init__`` reads
   ``self.__annotations__`` on an *instance*, which Python 3.14 no longer resolves
   to the class annotations. :func:`_ensure_workspace_annotation_shim` rewrites that
   one access to ``type(self).__annotations__`` — idempotent, and applied only when
   the bug is actually present (a future fixed pycalphad is left untouched).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------- #
# Optional dependency: the whole module degrades gracefully without pycalphad.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - import guard
    import pycalphad  # noqa: F401  (presence check; submodules imported lazily)

    _HAVE_PYCALPHAD = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    _HAVE_PYCALPHAD = False
    _IMPORT_ERROR = exc


_INSTALL_HINT = (
    "Phase 4 needs the optional CALPHAD backend. Install it with:\n"
    "  pip install symengine==0.14.1\n"
    "  pip install 'pycalphad>=0.11' --no-deps\n"
    "  pip install xarray pint tinydb runtype pandas\n"
    "(the two-step install overrides pycalphad's conservative symengine<0.14 pin, "
    "which has no Python-3.14 wheel; see the module docstring)."
)


def available() -> bool:
    """True iff pycalphad imported — callers can skip/branch without a try/except."""
    return _HAVE_PYCALPHAD


def _require_pycalphad() -> None:
    if not _HAVE_PYCALPHAD:
        raise ImportError(_INSTALL_HINT) from _IMPORT_ERROR


# --------------------------------------------------------------------------- #
# Compatibility shim: PEP-749 broke `self.__annotations__` on instances (Py3.14).
# --------------------------------------------------------------------------- #
_SHIM_APPLIED = False


def _ensure_workspace_annotation_shim() -> None:
    """Patch pycalphad's ``Workspace.__init__`` for Python 3.14, only if needed.

    The method uses ``self.__annotations__`` purely to list the typed attribute
    names; under PEP 749 that access fails on an instance. We rewrite *that one
    token* to ``type(self).__annotations__`` (which resolves correctly) by
    recompiling the method's own source in its module namespace — no behaviour
    change. Idempotent; a no-op if the access is already absent (future fix).
    """
    global _SHIM_APPLIED
    if _SHIM_APPLIED:
        return
    import inspect
    import textwrap

    import pycalphad.core.workspace as ws

    src = inspect.getsource(ws.Workspace.__init__)
    if "self.__annotations__" not in src:
        _SHIM_APPLIED = True  # already fixed upstream — nothing to do
        return
    patched = textwrap.dedent(src).replace(
        "self.__annotations__", "type(self).__annotations__"
    )
    namespace = dict(vars(ws))
    exec(compile(patched, ws.__file__, "exec"), namespace)  # noqa: S102 (trusted source)
    ws.Workspace.__init__ = namespace["__init__"]
    _SHIM_APPLIED = True


# --------------------------------------------------------------------------- #
# Phase bookkeeping
# --------------------------------------------------------------------------- #
# The curated steel phase set we ever let CALPHAD choose among. Restricting the
# candidate phases is *required*, not cosmetic: the messy MatCalc database carries
# ~120 phases (oxides, borides, intermetallics) irrelevant to a clean steel, and a
# few (BCC_DISL, SIGMA, PDMN_B2) lost a Gibbs-energy term during preprocessing
# (their parameters used wildcards pycalphad cannot parse) — they are *corrupted,
# not absent*, so they could be spuriously (un)stable. They are deliberately
# excluded here and must never enter a calculation. (Phases with *no* constituents,
# e.g. MNB4, are pruned outright in :func:`load_clean_database`.)
_CANDIDATE_STEEL_PHASES = (
    "LIQUID",
    "FCC_A1",            # austenite (γ)
    "BCC_A2",            # ferrite (α) / δ
    "CEMENTITE",         # Fe₃C  (mc_fe spelling)
    "CEMENTITE_D011",    # Fe₃C  (cfe_broshe spelling)
    "M23C6", "M7C3", "M3C2", "M6C",   # alloy (Cr/Mo) carbides — multicomponent only
)
_EXCLUDED_CORRUPTED_PHASES = frozenset({"BCC_DISL", "SIGMA", "PDMN_B2"})

# Map CALPHAD phase names onto the fe_c inter-module currency (ferrite/austenite/
# cementite). Alloy carbides have no fe_c analogue — they are why the multicomponent
# output is *richer* than the binary currency, so they are reported under "carbide".
_FERRITE_PHASES = frozenset({"BCC_A2"})
_AUSTENITE_PHASES = frozenset({"FCC_A1"})
_CEMENTITE_PHASES = frozenset({"CEMENTITE", "CEMENTITE_D011"})
_CARBIDE_PHASES = frozenset({"M23C6", "M7C3", "M3C2", "M6C"})

# Molar masses (g/mol) for the elements steel equilibria touch — used to turn
# CALPHAD's *mole*-based phase amounts into the **mass** fractions fe_c speaks.
_MOLAR_MASS = {
    "C": 12.011, "FE": 55.845, "CR": 51.996, "MN": 54.938,
    "MO": 95.95, "NI": 58.693, "SI": 28.085, "V": 50.942,
}


def fe_c_phase_label(phase_name: str) -> str:
    """Map a CALPHAD phase name to ``ferrite``/``austenite``/``cementite``/``carbide``."""
    if phase_name in _FERRITE_PHASES:
        return "ferrite"
    if phase_name in _AUSTENITE_PHASES:
        return "austenite"
    if phase_name in _CEMENTITE_PHASES:
        return "cementite"
    if phase_name in _CARBIDE_PHASES:
        return "carbide"
    if phase_name == "LIQUID":
        return "liquid"
    return phase_name.lower()


# --------------------------------------------------------------------------- #
# Database loading: a minimal, scoped preprocessor for messy TDB files
# --------------------------------------------------------------------------- #
_DB_CACHE: dict = {}


def load_clean_database(path):
    """Load a TDB, keeping only the commands pycalphad's own grammar can parse.

    The openly-licensed MatCalc steel database carries TDB commands pycalphad does
    not model (molar-volume ``V``/``HMVA`` parameters, mobility data, MatCalc-only
    ``REFERENCE_ELEMENT``/``ADD_COMPOSITION_SET`` metadata, and a handful of
    Gibbs-energy parameters written with ``*`` wildcards). Rather than guess a
    keyword blocklist, we keep exactly the commands that **parse** — by construction
    that drops only what pycalphad cannot represent (volume/mobility at 1 atm don't
    affect phase equilibria; the dropped wildcard-``G`` params hit only the
    deliberately-excluded auxiliary phases). Phases left with no constituents (their
    sole ``CONSTITUENT`` line was malformed) are then pruned so they can't crash
    pycalphad's phase filter.

    Scoped to the two databases this project loads — *not* a general TDB-repair
    library. Cleanly-written databases (e.g. the bundled ``cfe_broshe.tdb``) pass
    through with nothing dropped.
    """
    _require_pycalphad()
    # Cache by (path, mtime): the MatCalc database is ~460 KB / 4400 commands, and
    # re-parsing it per backend construction dominated the test time. The result is
    # treated as read-only by callers (pruning happens here, before it is returned).
    resolved = Path(path).resolve()
    key = (str(resolved), resolved.stat().st_mtime)
    if key in _DB_CACHE:
        return _DB_CACHE[key]

    import pycalphad.io.tdb as tdb_io
    from pycalphad import Database
    from pyparsing.exceptions import ParseBaseException

    raw = Path(path).read_text(encoding="utf-8", errors="replace")

    # Mirror read_tdb's own splitting: upper-case, drop `$` comments, split on `!`.
    upper = raw.upper().replace("\t", " ")
    stripped = [line.split("$", 1)[0] for line in upper.split("\n")]
    stripped = [
        seg.split("!")[0] + ("!" if "!" in seg else "") for seg in stripped
    ]
    commands = " ".join(stripped).split("!")

    grammar = tdb_io._tdb_grammar()
    kept: list[str] = []
    for command in commands:
        text = command.strip()
        if not text:
            continue
        try:
            grammar.parse_string(command)
        except ParseBaseException:
            continue
        kept.append(text)

    dbf = Database.from_string(" !\n".join(kept) + " !\n", fmt="tdb")

    # Prune phases whose constituents failed to load (would crash filter_phases).
    for phase in [p for p in list(dbf.phases) if not getattr(dbf.phases[p], "constituents", None)]:
        del dbf.phases[phase]
    _DB_CACHE[key] = dbf
    return dbf


def bundled_fe_c_database_path() -> Path:
    """Path to the Fe-C ``cfe_broshe.tdb`` bundled inside the installed pycalphad."""
    _require_pycalphad()
    import pycalphad

    return Path(pycalphad.__file__).parent / "tests" / "databases" / "cfe_broshe.tdb"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_steel_database_path() -> Path | None:
    """Locate a multicomponent steel TDB: ``$BIGSIM_STEEL_TDB`` or ``data/tdb/``.

    Returns ``None`` if none is present (the multicomponent live tests then skip).
    """
    env = os.environ.get("BIGSIM_STEEL_TDB")
    if env and Path(env).is_file():
        return Path(env)
    candidate = _repo_root() / "data" / "tdb" / "mc_fe_v2.060.tdb"
    return candidate if candidate.is_file() else None


# --------------------------------------------------------------------------- #
# Composition helpers (the diagram speaks wt%; CALPHAD speaks mole fraction)
# --------------------------------------------------------------------------- #
def wt_to_mole_fractions(comp_wt: dict) -> dict:
    """Convert a ``{element: wt%}`` solute dict (Fe = balance) to mole fractions.

    Keys are upper-cased element symbols (``"C"``, ``"CR"`` …). The balance is iron,
    so ``comp_wt`` lists only the solutes; their wt% must sum to < 100.
    """
    solutes = {k.upper(): float(v) for k, v in comp_wt.items()}
    fe_wt = 100.0 - sum(solutes.values())
    if fe_wt <= 0:
        raise ValueError(f"solute wt% must sum to < 100 (Fe is the balance); got {solutes}")
    moles = {el: w / _MOLAR_MASS[el] for el, w in solutes.items()}
    moles["FE"] = fe_wt / _MOLAR_MASS["FE"]
    total = sum(moles.values())
    return {el: n / total for el, n in moles.items()}


def carbon_wt_to_mole_fraction(C0: float) -> float:
    """Mole fraction of carbon for a binary Fe-``C0``-wt% steel."""
    return wt_to_mole_fractions({"C": C0})["C"]


# --------------------------------------------------------------------------- #
# The backend
# --------------------------------------------------------------------------- #
@dataclass
class EquilibriumPoint:
    """One equilibrium state: mass fractions + the carbon balance that proves it.

    ``mass_fractions`` is keyed by the **fe_c label** (ferrite/austenite/cementite/
    carbide/liquid), summing to 1. ``wt_pct`` is the overall composition recovered
    *from the phases* (Σ phase-mass·phase-composition) — its carbon entry equalling
    the input ``C0`` to machine precision is the conservation triad leg.
    """

    T_celsius: float
    mass_fractions: dict
    wt_pct: dict
    stable_phases: tuple


class CalphadBackend:
    """A thin pycalphad wrapper exposing fe_c-shaped equilibrium readings.

    Construct with no argument for the bundled binary **Fe-C** database (the
    drop-in replacement for :func:`fe_c.phase_fractions`), or pass a multicomponent
    steel TDB path for low-alloy steels::

        be = CalphadBackend()                                   # Fe-C (bundled)
        be.phase_fractions(0.76, 740.0)                         # → austenite-bearing
        be.eutectoid()                                          # → (~727 °C, ~0.76 %C)

        steel = CalphadBackend(default_steel_database_path())   # mc_fe (if present)
        steel.alloy_transus({"C":0.40,"Cr":0.95,"Mn":0.875,"Mo":0.20,"Si":0.25})  # 4140 A1/A3
    """

    def __init__(self, tdb_path=None):
        _require_pycalphad()
        _ensure_workspace_annotation_shim()
        self.tdb_path = Path(tdb_path) if tdb_path is not None else bundled_fe_c_database_path()
        self.db = load_clean_database(self.tdb_path)
        self.active_phases = [
            p for p in _CANDIDATE_STEEL_PHASES
            if p in self.db.phases and p not in _EXCLUDED_CORRUPTED_PHASES
        ]

    # -- low-level equilibrium ------------------------------------------------ #
    def _components(self, solute_elements) -> list:
        comps = ["FE", "C", "VA"]
        for el in solute_elements:
            if el not in comps:
                comps.append(el)
        return comps

    def _equilibrium(self, x_conditions: dict, T):
        """Run pycalphad ``equilibrium`` at the given mole-fraction conditions.

        ``x_conditions`` maps element symbol → mole fraction (carbon required;
        Fe is the dependent balance and is *not* listed). ``T`` is kelvin and may
        be a scalar or a ``(start, stop, step)`` range for a vectorised scan.
        """
        from pycalphad import equilibrium, variables as v

        solutes = [el for el in x_conditions if el != "FE"]
        conditions = {v.T: T, v.P: 101325, v.N: 1}
        for el in solutes:
            conditions[v.X(el)] = x_conditions[el]
        comps = self._components(solutes)
        return equilibrium(self.db, comps, self.active_phases, conditions)

    @staticmethod
    def _stable_sets(eq) -> list:
        """Stable-phase ``frozenset`` per grid point of a (possibly scanned) result."""
        phase = eq.Phase.squeeze()
        amount = eq.NP.squeeze()
        if phase.ndim == 1:  # single point: dims = (vertex,)
            names = {
                str(p) for p, n in zip(phase.values, amount.values)
                if str(p) and n > 1e-6
            }
            return [frozenset(names)]
        # scanned: leading axis is the scan variable, last axis is vertex
        out = []
        pv, nv = phase.values, amount.values
        for i in range(pv.shape[0]):
            names = {str(p) for p, n in zip(pv[i], nv[i]) if str(p) and n > 1e-6}
            out.append(frozenset(names))
        return out

    # -- mass-fraction extraction (the conservation leg) ---------------------- #
    def equilibrium_point(self, comp_wt: dict, T_celsius: float) -> EquilibriumPoint:
        """Full equilibrium at one (composition, T): mass fractions + carbon balance.

        ``comp_wt`` is ``{element: wt%}`` (Fe balance; ``"C"`` required). Phases are
        merged by fe_c label (e.g. ferrite + δ-ferrite both ``BCC_A2`` → "ferrite").
        """
        x = wt_to_mole_fractions(comp_wt)
        eq = self._equilibrium(x, T_celsius + 273.15)
        phase = eq.Phase.squeeze()
        amount = eq.NP.squeeze()
        comp_X = eq.X.squeeze()
        elements = [str(c) for c in eq.component.values]

        mass_by_label: dict = {}
        element_mass: dict = {el: 0.0 for el in elements}
        total_mass = 0.0
        stable = []
        for iv in range(phase.sizes["vertex"]):
            name = str(phase.isel(vertex=iv).values)
            moles = float(amount.isel(vertex=iv).values)
            if not name or not np.isfinite(moles) or moles <= 1e-10:
                continue
            xvec = {
                el: float(comp_X.isel(vertex=iv).sel(component=el).values)
                for el in elements
            }
            molar_mass = sum(xvec[el] * _MOLAR_MASS[el] for el in elements)
            phase_mass = moles * molar_mass
            label = fe_c_phase_label(name)
            mass_by_label[label] = mass_by_label.get(label, 0.0) + phase_mass
            for el in elements:
                element_mass[el] += moles * xvec[el] * _MOLAR_MASS[el]
            total_mass += phase_mass
            stable.append(name)

        mass_fractions = {k: m / total_mass for k, m in mass_by_label.items()}
        wt_pct = {el: 100.0 * element_mass[el] / total_mass for el in elements}
        return EquilibriumPoint(
            T_celsius=T_celsius,
            mass_fractions=mass_fractions,
            wt_pct=wt_pct,
            stable_phases=tuple(sorted(stable)),
        )

    def phase_fractions(self, C0: float, T_celsius: float) -> dict:
        """Fe-C drop-in for :func:`fe_c.phase_fractions` — mass fractions at (C0, T).

        Returns ``{"ferrite", "austenite", "cementite"}`` (always all three keys,
        0.0 for absent phases), summing to 1 — the same currency and shape ``fe_c``
        returns, now from real thermodynamics. Intended for **binary Fe-C**; for an
        alloy steel use :meth:`equilibrium_point` (alloy carbides have no fe_c key).
        """
        point = self.equilibrium_point({"C": C0}, T_celsius)
        out = {"ferrite": 0.0, "austenite": 0.0, "cementite": 0.0}
        for label, frac in point.mass_fractions.items():
            if label in out:
                out[label] += frac
            else:  # an alloy carbide / liquid slipped in — fold into cementite, flagged by sum
                out["cementite"] += frac
        return out

    # -- boundary finders ----------------------------------------------------- #
    def _bisect_phase_boundary(self, x: dict, T_lo: float, T_hi: float,
                               present: str, want_present_below: bool,
                               tol: float = 0.25) -> float:
        """Bisect (kelvin) for the temperature where ``present`` appears/vanishes.

        ``want_present_below=True`` means the phase is stable below the boundary and
        gone above it (e.g. ferrite vanishing at A₃). Returns °C.
        """
        def has(TK):
            return present in self._stable_sets(self._equilibrium(x, TK))[0]

        while (T_hi - T_lo) > tol:
            mid = 0.5 * (T_lo + T_hi)
            present_here = has(mid)
            # boundary is between a "present" point and an "absent" point
            if present_here == want_present_below:
                T_lo = mid  # still on the "below" side
            else:
                T_hi = mid
        return 0.5 * (T_lo + T_hi) - 273.15

    def austenite_solvus(self, C0: float, T_window=(727.0, 1000.0)) -> float:
        """A₃ (°C): the temperature at which the last ferrite dissolves for Fe-``C0``.

        The CALPHAD-computed γ/(α+γ) transus — the **curved** boundary whose
        deviation from ``fe_c``'s linear chord is the Phase-4 benchmark with teeth.
        Defined for hypoeutectoid carbon (``C0`` below the eutectoid).
        """
        x = {"C": carbon_wt_to_mole_fraction(C0)}
        lo, hi = T_window[0] + 273.15, T_window[1] + 273.15
        return self._bisect_phase_boundary(x, lo, hi, "BCC_A2", want_present_below=True)

    def eutectoid(self, T_scan=(700.0, 760.0)) -> tuple:
        """The eutectoid invariant ``(T °C, C wt%)``, found from the free energies.

        T: the A₁ at which austenite first appears (taken at a hypoeutectoid probe
        composition, where A₁ is the eutectoid isotherm). C: the carbon of the
        single-γ window just above A₁, which pinches to the eutectoid composition.
        """
        from pycalphad import variables as v

        # T_eutectoid: austenite onset at a hypoeutectoid probe (0.5 %C).
        x_probe = {"C": carbon_wt_to_mole_fraction(0.50)}
        T_eu = self._bisect_phase_boundary(
            x_probe, T_scan[0] + 273.15, T_scan[1] + 273.15,
            "FCC_A1", want_present_below=False,
        )
        # C_eutectoid: scan composition just above A₁; centre of the single-γ window.
        TK = T_eu + 273.15 + 2.0
        xlo = carbon_wt_to_mole_fraction(0.40)
        xhi = carbon_wt_to_mole_fraction(1.10)
        eq = self._equilibrium({"C": (xlo, xhi, (xhi - xlo) / 120.0)}, TK)
        sets = self._stable_sets(eq)
        xs = eq.X_C.values.ravel() if hasattr(eq, "X_C") else eq.coords["X_C"].values
        single_g = [xs[i] for i, s in enumerate(sets) if s == frozenset({"FCC_A1"})]
        x_eu = 0.5 * (min(single_g) + max(single_g))
        C_eu = _mole_fraction_C_to_wt(x_eu)
        return (T_eu, C_eu)

    def gamma_max(self, T_scan=(1080.0, 1160.0)) -> tuple:
        """γ-max ``(T °C, C wt%)``: the peak carbon solubility in austenite.

        The top of the A_cm transus, at the eutectic isotherm — the second Fe-C
        invariant. Found as the maximum carbon for which austenite is single-phase,
        scanning composition across temperatures near the eutectic.
        """
        best = (float("nan"), 0.0)
        xlo = carbon_wt_to_mole_fraction(1.6)
        xhi = carbon_wt_to_mole_fraction(2.4)
        for T_c in np.arange(T_scan[0], T_scan[1] + 0.1, 4.0):
            eq = self._equilibrium({"C": (xlo, xhi, (xhi - xlo) / 80.0)}, T_c + 273.15)
            sets = self._stable_sets(eq)
            xs = eq.X_C.values.ravel() if hasattr(eq, "X_C") else eq.coords["X_C"].values
            single_g = [xs[i] for i, s in enumerate(sets) if s == frozenset({"FCC_A1"})]
            if single_g:
                c_here = _mole_fraction_C_to_wt(max(single_g))
                if c_here > best[1]:
                    best = (T_c, c_here)
        return best

    def alloy_transus(self, comp_wt: dict, T_scan=(680.0, 860.0)) -> tuple:
        """``(A1 °C, A3 °C)`` for a multicomponent steel: austenite onset and ferrite end.

        A₁ = the lowest T at which austenite (FCC_A1) is stable; A₃ = the lowest T at
        which ferrite (BCC_A2) is *gone* (fully austenitic). For an alloy steel these
        bracket a ferrite+austenite(+carbide) region, not a sharp eutectoid.
        """
        x = wt_to_mole_fractions(comp_wt)
        A1 = self._bisect_phase_boundary(
            x, T_scan[0] + 273.15, T_scan[1] + 273.15, "FCC_A1", want_present_below=False,
        )
        A3 = self._bisect_phase_boundary(
            x, T_scan[0] + 273.15, T_scan[1] + 273.15, "BCC_A2", want_present_below=True,
        )
        return (A1, A3)


def _mole_fraction_C_to_wt(x_C: float) -> float:
    """Invert a binary Fe-C mole fraction to wt% carbon."""
    # x_C = (m_C/M_C) / (m_C/M_C + m_Fe/M_Fe); solve for wt% with m_C + m_Fe = 100.
    mc, mfe = _MOLAR_MASS["C"], _MOLAR_MASS["FE"]
    # x_C / (1 - x_C) = (w/mc) / ((100-w)/mfe)  →  solve linear in w
    r = x_C / (1.0 - x_C)
    # r = (w/mc)*(mfe/(100-w))  →  r*(100-w)*mc = w*mfe
    # 100*r*mc - r*mc*w = w*mfe  →  w = 100*r*mc / (mfe + r*mc)
    return 100.0 * r * mc / (mfe + r * mc)


# --------------------------------------------------------------------------- #
# Convenience: fetch the openly-licensed MatCalc database (never auto-committed)
# --------------------------------------------------------------------------- #
MC_FE_URL = "https://www.matcalc.at/images/stories/Download/Database/mc_fe_v2.060.tdb"


def download_mc_fe(dest: Path | None = None) -> Path:
    """Download the ODbL-licensed MatCalc steel database to ``data/tdb/`` (gitignored).

    A user convenience for enabling the multicomponent live tests / the 4140 figure.
    The file is **never committed** (``.gitignore`` covers ``*.tdb`` and ``data/``);
    we ship only numbers computed *from* it (:mod:`calphad_reference`), per plan §6.
    """
    import shutil
    import urllib.request

    dest = dest or (_repo_root() / "data" / "tdb" / "mc_fe_v2.060.tdb")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # matcalc.at (a Joomla host) 403s the default ``Python-urllib`` User-Agent, so send a
    # browser one — verified empirically (default UA → 403, browser UA → 200). Without this
    # the bare ``urlretrieve`` below fails on any fresh fetch (CI and a user alike).
    req = urllib.request.Request(MC_FE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:  # noqa: S310 (known ODbL source)
        shutil.copyfileobj(resp, fh)
    return dest
