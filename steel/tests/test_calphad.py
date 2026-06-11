"""Phase-4 validation: CALPHAD-backed equilibrium (the bounded deep end).

Two tiers, mirroring Option C (steel-production.md §3 Phase 4):

* **Committed / always green** — validate the parametrised :mod:`fe_c` against the
  frozen :data:`calphad_reference.REFERENCE` table (and 4140 against the independent
  Andrews formulae). These need *no* pycalphad and *no* database — they run on a
  clean checkout, the way every prior phase's triad does.
* **Live / ``importorskip``** — call :func:`calphad_reference.regenerate` through the
  real pycalphad backend and assert it reproduces the frozen table *by construction*.
  The binary half uses the Fe-C database bundled inside pycalphad (so it runs
  whenever pycalphad is installed); the multicomponent half skips unless a steel TDB
  is present (``$BIGSIM_STEEL_TDB`` or ``data/tdb/``).

The non-circularity split (advisor; the same discipline as 2b/2c/3b):
  - the **invariant points** (eutectoid, γ-max) are pinned *by construction* in
    ``fe_c``, so CALPHAD agreeing there only checks the *wiring* — asserted loosely;
  - the leg with **teeth** is CALPHAD's *curved* A₃ vs ``fe_c``'s *linear chord*
    (a quantified, non-trivial deviation), and the **multicomponent** A₁/A₃ that
    ``fe_c`` cannot produce at all, cross-checked against Andrews (loose bands — an
    alloy steel's A₁ amid stable Cr-carbides is not a sharp eutectoid, and CALPHAD
    and Andrews straddle the plain-carbon 727 °C, so no directional claim is made).
"""
import math

import pytest

from steel import fe_c
from steel import calphad_reference as ref
from steel import calphad_backend as cb  # imports cleanly even without pycalphad

REF = ref.REFERENCE

# The committed tests below need neither pycalphad nor a database (Option C: they
# validate fe_c against the frozen table on any checkout). Only the *live* tests are
# gated — per test, so a missing pycalphad never skips the committed half.
requires_pycalphad = pytest.mark.skipif(
    not cb.available(), reason="optional CALPHAD backend (pycalphad) not installed"
)


# =========================================================================== #
# Committed / always-green — fe_c vs the frozen CALPHAD reference
# =========================================================================== #

# --- Analytical limit: the invariant points emerge (a loose *wiring* check) -- #
def test_fe_c_eutectoid_matches_calphad_reference_loosely():
    # fe_c pins the eutectoid to 727 °C / 0.76 %C *by construction*; CALPHAD computes
    # it from the free energies (~726.6 / ~0.757). Agreement here is necessary but not
    # probative (it cannot fail unless the CALPHAD wiring is broken) — assert loosely.
    assert fe_c.A1() == pytest.approx(REF["binary"]["eutectoid_T"], abs=2.0)
    assert fe_c.C_EUTECTOID == pytest.approx(REF["binary"]["eutectoid_C"], abs=0.02)


def test_fe_c_gamma_max_matches_calphad_reference_loosely():
    # The second named Fe-C invariant: γ-max ≈ 2.11 %C / 1147 °C in fe_c vs the
    # assessed ~2.04 / ~1148. Loose — assessments differ a few % in max C solubility.
    assert fe_c.T_GAMMA_MAX == pytest.approx(REF["binary"]["gamma_max_T"], abs=3.0)
    assert fe_c.C_GAMMA_MAX == pytest.approx(REF["binary"]["gamma_max_C"], abs=0.12)


# --- Benchmark with teeth: the curved transus vs the linear chord ----------- #
def test_fe_c_linear_A3_overpredicts_the_calphad_curve():
    # THE Phase-4 benchmark: fe_c draws A₃ as a straight chord from 912 °C (0 %C) to
    # 727 °C (eutectoid); the real γ/(α+γ) transus is concave, sitting *below* that
    # chord. The deviation is "what the parametrised version got wrong" — it must be
    # systematically positive (chord too high), meaningful at mid-carbon, yet bounded
    # (fe_c is a fair first approximation, not nonsense).
    deviations = {}
    for C0 in ref.A3_SAMPLE_CARBON:
        chord = fe_c.A3(C0)
        curved = REF["binary"]["a3_curve"][C0]
        deviations[C0] = chord - curved

    # Systematically over-predicting across the whole hypoeutectoid range.
    assert all(d > 5.0 for d in deviations.values()), deviations
    # A meaty, teaching-worthy gap at mid-carbon — but bounded (still a fair approx).
    assert 20.0 <= max(deviations.values()) <= 40.0, deviations
    # At the benchmark-steel carbon (~0.4 %C) the chord is ~27 °C high.
    assert deviations[0.40] == pytest.approx(27.0, abs=6.0)


# --- Conservation: the lever rule is a mass balance ------------------------- #
def test_calphad_conservation_carbon_balance_closes():
    # CALPHAD returns phase amounts + per-phase compositions; recombining them must
    # recover the input carbon (Σ fᵢ·Cᵢ = C0). The frozen record closes to 4 figures;
    # the live test below confirms machine precision.
    cons = REF["binary"]["conservation"]
    assert cons["ferrite"] + cons["cementite"] == pytest.approx(1.0, abs=1e-3)
    assert cons["recovered_wt_C"] == pytest.approx(ref.CONSERVATION_POINT["C0"], abs=1e-3)
    # The split is the α/Fe₃C lever rule — cementite ≈ 11 % at the eutectoid, matching
    # fe_c's own PEARLITE_CEMENTITE_FRACTION (a cross-check between the two backends).
    assert cons["cementite"] == pytest.approx(fe_c.PEARLITE_CEMENTITE_FRACTION, abs=0.01)


# --- Benchmark: the multicomponent extension fe_c cannot reach -------------- #
def test_4140_transus_brackets_andrews_within_scatter():
    # 4140 is Fe-C-Cr-Mn-Mo-Si — outside fe_c entirely. CALPHAD's A₁/A₃ are checked
    # against the independent Andrews Ae1/Ae3 empirical formulae. LOOSE bands (±20 °C):
    # both models carry ~15–20 °C scatter and they straddle the plain-carbon 727 °C
    # (CALPHAD A₁ ≈ 721 below, Andrews Ae1 ≈ 737 above), so no directional claim — only
    # "the same neighbourhood, an alloy A₁ that is not a sharp eutectoid point".
    A1 = REF["alloy_4140"]["A1"]
    A3 = REF["alloy_4140"]["A3"]
    Ae1 = ref.andrews_Ae1(ref.COMPOSITION_4140)
    Ae3 = ref.andrews_Ae3(ref.COMPOSITION_4140)
    assert abs(A1 - Ae1) < 20.0, (A1, Ae1)
    assert abs(A3 - Ae3) < 20.0, (A3, Ae3)
    assert A1 < A3              # a ferrite+austenite(+carbide) region, in order


def test_4140_shows_chromium_carbide_beyond_fe_c_currency():
    # The qualitative payoff of going multicomponent: a chromium carbide (M7C3) is a
    # stable equilibrium phase in 4140 — something fe_c's three-phase Fe-Fe₃C currency
    # (ferrite/austenite/cementite) has no way to represent. And fe_c's eutectoid is a
    # single composition-independent isotherm (A₁ = 727 for any steel), whereas the
    # alloy A₁ here differs — the parametrised diagram is genuinely blind to alloying.
    phases = REF["alloy_4140"]["stable_phases_730C"]
    assert any(p in {"M7C3", "M23C6", "M3C2", "M6C"} for p in phases), phases
    assert fe_c.A1() != pytest.approx(REF["alloy_4140"]["A1"], abs=3.0)


# =========================================================================== #
# Live / pycalphad — the real backend reproduces the frozen table (per-test gated)
#
# These drive a *live external solver*, so each carries @pytest.mark.slow as well as
# the pycalphad gate (ADR 0003): they are deselected from the fast inner loop
# (`pytest -m "not slow"`) but always run in the full commit gate. The committed
# fe_c-vs-frozen tests above are pure/fast and stay in the inner loop.
#
# Under `-n auto` (pytest-xdist) each also carries @pytest.mark.xdist_group("calphad")
# — shared with test_demo_calphad.py — so every live solve lands on ONE worker
# (`--dist loadgroup`, set in pyproject addopts). That makes the module-scoped backends
# below build once per module and stops two heavyweight live solves running concurrently
# (oversubscription / the known multicomponent flake). The fast committed tests above are
# deliberately left ungrouped so they parallelise freely.
# =========================================================================== #
@pytest.fixture(scope="module")
def binary_backend():
    return cb.CalphadBackend()  # bundled Fe-C — present whenever pycalphad is


@pytest.fixture(scope="module")
def steel_backend():
    path = cb.default_steel_database_path()
    if path is None:
        pytest.skip("no multicomponent steel TDB (set $BIGSIM_STEEL_TDB or download_mc_fe())")
    return cb.CalphadBackend(path)


@pytest.mark.slow
@pytest.mark.xdist_group("calphad")
@requires_pycalphad
def test_live_binary_reproduces_frozen_reference(binary_backend):
    # Match-by-construction: the frozen table *is* what this backend produces.
    live = ref.regenerate(binary_backend=binary_backend)["binary"]
    frozen = REF["binary"]
    assert live["eutectoid_T"] == pytest.approx(frozen["eutectoid_T"], abs=0.5)
    assert live["eutectoid_C"] == pytest.approx(frozen["eutectoid_C"], abs=0.005)
    assert live["gamma_max_T"] == pytest.approx(frozen["gamma_max_T"], abs=0.5)
    assert live["gamma_max_C"] == pytest.approx(frozen["gamma_max_C"], abs=0.01)
    for C0 in ref.A3_SAMPLE_CARBON:
        assert live["a3_curve"][C0] == pytest.approx(frozen["a3_curve"][C0], abs=1.0)


@pytest.mark.slow
@pytest.mark.xdist_group("calphad")
@requires_pycalphad
def test_live_conservation_closes_to_machine_precision(binary_backend):
    # The real conservation leg: recombine CALPHAD's phases at a two-phase α+Fe₃C
    # point and recover the input carbon to ~machine precision (a free correctness
    # check the finite-volume engine guaranteed in mass mode; here it is the
    # equilibrium solver's own mass balance).
    point = binary_backend.equilibrium_point(
        {"C": ref.CONSERVATION_POINT["C0"]}, ref.CONSERVATION_POINT["T_celsius"]
    )
    assert set(point.stable_phases) == {"BCC_A2", "CEMENTITE_D011"}
    assert point.wt_pct["C"] == pytest.approx(ref.CONSERVATION_POINT["C0"], abs=1e-6)
    assert sum(point.mass_fractions.values()) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.slow
@pytest.mark.xdist_group("calphad")
@requires_pycalphad
def test_live_phase_fractions_is_fe_c_drop_in(binary_backend):
    # The consumer-facing currency: same keys, same shape as fe_c.phase_fractions,
    # summing to 1 — a genuine swappable backend.
    out = binary_backend.phase_fractions(0.40, 760.0)
    assert set(out) == {"ferrite", "austenite", "cementite"}
    assert sum(out.values()) == pytest.approx(1.0, abs=1e-6)
    # 0.40 %C just below A₃ (~787 °C): mostly austenite with some pro-eutectoid ferrite.
    assert out["austenite"] > out["ferrite"] > 0.0
    assert out["cementite"] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.slow
@pytest.mark.xdist_group("calphad")
@requires_pycalphad
def test_live_multicomponent_reproduces_frozen_reference(steel_backend):
    live = ref.regenerate(steel_backend=steel_backend)["alloy_4140"]
    frozen = REF["alloy_4140"]
    assert live["A1"] == pytest.approx(frozen["A1"], abs=1.0)
    assert live["A3"] == pytest.approx(frozen["A3"], abs=1.0)
    assert set(live["stable_phases_730C"]) == set(frozen["stable_phases_730C"])
