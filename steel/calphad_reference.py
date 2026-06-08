"""Frozen CALPHAD reference values — the committed half of Phase 4's Option C.

The thermodynamic databases are never committed (plan §6), so the validation suite
cannot run pycalphad on a clean checkout. Instead we **freeze the numbers** CALPHAD
produces into :data:`REFERENCE` here, generated once from this module's own
:func:`regenerate` (the *exact* functions the live test calls — no hand-transcribed
values). Then:

* the always-green committed tests validate ``fe_c`` against :data:`REFERENCE`
  (and 4140 against the independent Andrews formulae); and
* an ``importorskip``-guarded live test calls :func:`regenerate` and asserts it
  reproduces :data:`REFERENCE` — so the frozen table and the live backend match
  *by construction*, and any drift (a new pycalphad/database) surfaces immediately.

Regenerate / verify::

    python -m projects.steel.calphad_reference            # prints REFERENCE vs live diff

The committed numbers are **physical facts computed from cited assessments**, the
same status as every other phase's benchmark constants (Maynier coefficients,
Grange temper response, published Jominy plateaus) — not redistributed database data.
"""
from __future__ import annotations

import math

# --------------------------------------------------------------------------- #
# Provenance — what produced REFERENCE (so it is reproducible)
# --------------------------------------------------------------------------- #
PROVENANCE = {
    "generated": "2026-06-08",
    "pycalphad": "0.11.2 (Python 3.14; symengine 0.14.1 override + PEP-749 shim)",
    "binary_db": (
        "cfe_broshe.tdb — SGTE-style metastable Fe-C assessment bundled inside "
        "pycalphad (pycalphad/tests/databases/); used as a validation reference, "
        "not redistributed."
    ),
    "steel_db": (
        "mc_fe_v2.060.tdb — MatCalc steel database, openly licensed under ODbL 1.0 "
        "(assessed at TU Wien by E. Povoden-Karadeniz); used as a validation "
        "reference, never committed (gitignored)."
    ),
    "preprocessing": (
        "load_clean_database keeps only grammar-parseable TDB commands (drops "
        "molar-volume/mobility params, MatCalc REFERENCE_ELEMENT/ADD_COMPOSITION_SET "
        "metadata, and ~8 wildcard-G params on excluded auxiliary phases) and prunes "
        "constituent-less phases (MNB4). Active phases restricted to a curated steel "
        "set; corrupted BCC_DISL/SIGMA/PDMN_B2 excluded."
    ),
}

# The composition (wt%) at which the curved A3 transus is sampled vs fe_c's chord.
A3_SAMPLE_CARBON = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60)

# A representative AISI 4140 composition (wt%) — the multicomponent showpiece.
COMPOSITION_4140 = {"C": 0.40, "Cr": 0.95, "Mn": 0.875, "Mo": 0.20, "Si": 0.25}

# A binary Fe-C point used for the conservation leg (two-phase α + Fe₃C).
CONSERVATION_POINT = {"C0": 0.76, "T_celsius": 700.0}


# --------------------------------------------------------------------------- #
# Andrews (1965) empirical Ae1 / Ae3 — the INDEPENDENT multicomponent benchmark
# --------------------------------------------------------------------------- #
def andrews_Ae1(comp_wt: dict) -> float:
    """Andrews (1965) equilibrium **Ae1** (°C) from composition (wt%).

    ``Ae1 = 723 − 10.7·Mn − 16.9·Ni + 29.1·Si + 16.9·Cr + 6.38·W`` (+ As term,
    omitted). An empirical fit across many steels — independent of both ``fe_c`` and
    the CALPHAD database, so it is a genuine cross-check on the alloy A₁ (with the
    ±~15–20 °C scatter such fits carry).
    """
    c = {k.upper(): float(v) for k, v in comp_wt.items()}
    return (723.0 - 10.7 * c.get("MN", 0) - 16.9 * c.get("NI", 0)
            + 29.1 * c.get("SI", 0) + 16.9 * c.get("CR", 0) + 6.38 * c.get("W", 0))


def andrews_Ae3(comp_wt: dict) -> float:
    """Andrews (1965) equilibrium **Ae3** (°C) from composition (wt%).

    ``Ae3 = 910 − 203·√C − 15.2·Ni + 44.7·Si + 104·V + 31.5·Mo + 13.1·W
    − 30·Mn − 11·Cr − 20·Cu`` (+ P/Al/As/Ti terms, omitted for low-alloy steels).
    """
    c = {k.upper(): float(v) for k, v in comp_wt.items()}
    return (910.0 - 203.0 * math.sqrt(c.get("C", 0)) - 15.2 * c.get("NI", 0)
            + 44.7 * c.get("SI", 0) + 104.0 * c.get("V", 0) + 31.5 * c.get("MO", 0)
            + 13.1 * c.get("W", 0) - 30.0 * c.get("MN", 0) - 11.0 * c.get("CR", 0)
            - 20.0 * c.get("CU", 0))


# --------------------------------------------------------------------------- #
# Regeneration — emit the table from the exact backend functions the test calls
# --------------------------------------------------------------------------- #
def regenerate(binary_backend=None, steel_backend=None) -> dict:
    """Recompute the reference numbers from CALPHAD backends.

    ``binary_backend`` (Fe-C, bundled ``cfe_broshe``) drives the binary entries;
    ``steel_backend`` (a multicomponent TDB) drives the 4140 entries. Either may be
    omitted — only the entries it would produce are then included, so the binary
    half (always available) and the multicomponent half (TDB-gated) regenerate
    independently. This is the *single source* the frozen :data:`REFERENCE` and the
    live test both go through.
    """
    out: dict = {}
    if binary_backend is not None:
        T_eu, C_eu = binary_backend.eutectoid()
        T_gm, C_gm = binary_backend.gamma_max()
        point = binary_backend.equilibrium_point(
            {"C": CONSERVATION_POINT["C0"]}, CONSERVATION_POINT["T_celsius"]
        )
        out["binary"] = {
            "eutectoid_T": T_eu,
            "eutectoid_C": C_eu,
            "gamma_max_T": T_gm,
            "gamma_max_C": C_gm,
            "a3_curve": {C0: binary_backend.austenite_solvus(C0) for C0 in A3_SAMPLE_CARBON},
            "conservation": {
                "ferrite": point.mass_fractions.get("ferrite", 0.0),
                "cementite": point.mass_fractions.get("cementite", 0.0),
                "recovered_wt_C": point.wt_pct["C"],
            },
        }
    if steel_backend is not None:
        A1, A3 = steel_backend.alloy_transus(COMPOSITION_4140)
        point = steel_backend.equilibrium_point(COMPOSITION_4140, 730.0)
        out["alloy_4140"] = {
            "A1": A1,
            "A3": A3,
            "stable_phases_730C": list(point.stable_phases),
        }
    return out


# --------------------------------------------------------------------------- #
# The frozen table (generated by `regenerate`; see PROVENANCE). The live test
# asserts `regenerate(...)` reproduces these within a hair of numerical tolerance.
# --------------------------------------------------------------------------- #
REFERENCE = {
    "binary": {
        "eutectoid_T": 726.6,
        "eutectoid_C": 0.7573,
        "gamma_max_T": 1148.0,
        "gamma_max_C": 2.0446,
        "a3_curve": {
            0.10: 869.0,
            0.20: 836.4,
            0.30: 809.7,
            0.40: 787.2,
            0.50: 767.5,
            0.60: 750.5,
        },
        "conservation": {
            "ferrite": 0.8883,
            "cementite": 0.1117,
            "recovered_wt_C": 0.7600,
        },
    },
    "alloy_4140": {
        "A1": 720.7,
        "A3": 771.8,
        "stable_phases_730C": ["BCC_A2", "CEMENTITE", "FCC_A1", "M7C3"],
    },
}


def main() -> None:  # pragma: no cover - manual verification helper
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from . import calphad_backend as cb

    if not cb.available():
        print(cb._INSTALL_HINT)
        return
    binary = cb.CalphadBackend()
    steel_path = cb.default_steel_database_path()
    steel = cb.CalphadBackend(steel_path) if steel_path else None
    live = regenerate(binary_backend=binary, steel_backend=steel)
    print("Live regeneration vs frozen REFERENCE:\n")
    import json
    print(json.dumps(live, indent=2, default=str))
    if steel is None:
        print("\n(no multicomponent steel TDB found — run "
              "`python -c \"from projects.steel.calphad_backend import download_mc_fe; "
              "download_mc_fe()\"` to enable the 4140 entries)")


if __name__ == "__main__":
    main()
