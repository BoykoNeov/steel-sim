"""Tests for the cooling-medium presets (Steel Phase 1c).

cooling.py is *parameter plumbing* (turn a quench severity ``h`` + specimen size
into a Newton ``T(t)``), so these check the lumped-capacitance formulas, the Biot
validity bookkeeping, and the path mechanics — not transformation outcomes (those
are :mod:`test_pathint`). The one physics-content check is that the four standard
media come out ordered slow → fast and that the lumped-validity flag fires exactly
where the 0-D model is stretched (the honest Phase-2 hand-off).
"""
import math

import numpy as np
import pytest

from steel import cooling
from steel.cooling import (
    characteristic_length, biot_number, lumped_time_constant,
    cooling_path, standard_media_paths, CoolingPath,
    RHO_STEEL, CP_STEEL, K_STEEL, MEDIA,
)


# --------------------------------------------------------------------------- #
# Lumped-capacitance formulas (the analytic definitions)
# --------------------------------------------------------------------------- #
def test_characteristic_length_by_geometry():
    d = 0.012
    assert characteristic_length(d, "cylinder") == pytest.approx(d / 4.0)
    assert characteristic_length(d, "sphere") == pytest.approx(d / 6.0)
    assert characteristic_length(d, "plate") == pytest.approx(d / 2.0)


def test_characteristic_length_guards():
    with pytest.raises(ValueError):
        characteristic_length(0.01, "octahedron")
    with pytest.raises(ValueError):
        characteristic_length(-1.0, "cylinder")


def test_biot_and_time_constant_formulas():
    h, L_c = 500.0, 0.0025
    assert biot_number(h, L_c, k=30.0) == pytest.approx(h * L_c / 30.0)
    assert lumped_time_constant(h, L_c, rho=RHO_STEEL, cp=CP_STEEL) == pytest.approx(
        RHO_STEEL * CP_STEEL * L_c / h
    )


def test_time_constant_rejects_bad_h():
    with pytest.raises(ValueError):
        lumped_time_constant(0.0, 0.0025)


# --------------------------------------------------------------------------- #
# cooling_path: the Newton history and its bookkeeping
# --------------------------------------------------------------------------- #
def test_cooling_path_endpoints_and_monotone():
    p = cooling_path("oil", T0=850.0, T_env=25.0)
    assert isinstance(p, CoolingPath)
    assert p.T[0] == pytest.approx(850.0, abs=1e-9)          # starts austenitized
    assert np.all(np.diff(p.T) <= 0.0)                       # monotone cooling
    assert p.T[-1] == pytest.approx(25.0, abs=1.0)           # ~reaches the bath
    # τ_th and Bi match the lumped formulas for the standard specimen.
    L_c = characteristic_length(cooling.STANDARD_DIAMETER, "cylinder")
    assert p.tau_thermal == pytest.approx(lumped_time_constant(MEDIA["oil"], L_c))
    assert p.biot == pytest.approx(biot_number(MEDIA["oil"], L_c))


def test_cooling_path_accepts_raw_h():
    p = cooling_path(1000.0, warn_biot=False)
    L_c = characteristic_length(cooling.STANDARD_DIAMETER, "cylinder")
    assert p.tau_thermal == pytest.approx(lumped_time_constant(1000.0, L_c))


def test_temperature_at_one_time_constant():
    # The defining Newton property, surfaced through the preset machinery.
    p = cooling_path("air", T0=900.0, T_env=20.0)
    T_at_tau = 20.0 + (900.0 - 20.0) / math.e
    # interpolate the path at t = τ_th
    T_interp = float(np.interp(p.tau_thermal, p.t, p.T))
    assert T_interp == pytest.approx(T_at_tau, rel=1e-3)


# --------------------------------------------------------------------------- #
# Biot validity: the honest Phase-2 hand-off
# --------------------------------------------------------------------------- #
@pytest.mark.filterwarnings("ignore:cooling_path")
def test_furnace_air_oil_are_lumped_valid_water_is_flagged():
    # The standard specimen is sized so the three slower media satisfy Bi < 0.1;
    # the severe water quench exceeds it — the documented stretch that motivates
    # the Phase-2 spatial solve.
    paths = {p.name: p for p in standard_media_paths()}
    assert paths["furnace"].lumped_valid
    assert paths["air"].lumped_valid
    assert paths["oil"].lumped_valid
    assert not paths["water"].lumped_valid


def test_severe_quench_emits_biot_warning():
    with pytest.warns(UserWarning, match="Biot"):
        cooling_path("water")            # Bi ≈ 0.13 on the standard specimen


def test_no_warning_when_lumped_valid():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")   # any warning becomes an error
        cooling_path("furnace")          # comfortably Bi < 0.1


# --------------------------------------------------------------------------- #
# The four standard media (the demo inputs)
# --------------------------------------------------------------------------- #
@pytest.mark.filterwarnings("ignore:cooling_path")
def test_standard_media_ordered_slow_to_fast():
    paths = standard_media_paths()
    assert [p.name for p in paths] == ["furnace", "air", "oil", "water"]
    taus = [p.tau_thermal for p in paths]
    assert taus == sorted(taus, reverse=True)               # decreasing τ_th = increasing severity


def test_bigger_section_cools_slower():
    # Same medium, thicker bar ⇒ larger L_c ⇒ longer time constant (and larger Bi).
    thin = cooling_path("oil", diameter=0.006)
    thick = cooling_path("oil", diameter=0.020)
    assert thick.tau_thermal > thin.tau_thermal
    assert thick.biot > thin.biot
