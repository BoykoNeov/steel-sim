"""Integration test for the CALPHAD demo (Steel Phase 4 — the demo IS the integration test).

The Phase-4 demo wires the backend, the parametrised ``fe_c`` diagram, and the Andrews
reference together into the banked two-panel artifact. Its compute pipeline is the
end-to-end check that they compose; the *quantitative* validation lives in
``test_calphad.py`` (against the frozen reference table), so here we assert the robust
thesis only — and skip cleanly without pycalphad / a steel TDB / matplotlib.

Compute is done once (module-scoped fixtures, small grids) and shared — a full-resolution
recompute per test would make this optional file dominate the suite's wall-clock.
"""
import numpy as np
import pytest

pytest.importorskip("pycalphad")
from steel import calphad_backend as cb       # noqa: E402
from steel import demo_calphad as demo        # noqa: E402

# Every test here drives a live pycalphad solve through the module-scoped fixtures
# below (`binary_data`/`alloy_data`) — including the figure smoke-test, which shares
# `binary_data`. So the whole file is `slow` (ADR 0003): a per-test mark would leak the
# 15-80 s fixture setup into the fast inner loop. Deselected by `pytest -m "not slow"`,
# always run in the full commit gate.
#
# xdist_group("calphad") (shared with test_calphad.py) pins these to ONE worker under
# `-n auto --dist loadgroup` (pyproject addopts): the module-scoped fixtures build once and
# no two live solves run concurrently. See test_calphad.py's live-section note.
pytestmark = [pytest.mark.slow, pytest.mark.xdist_group("calphad")]


@pytest.fixture(scope="module")
def binary_data():
    return demo.compute_binary(cb.CalphadBackend(), n=6)   # coarse grid: a smoke test, not the figure


@pytest.fixture(scope="module")
def alloy_data():
    path = cb.default_steel_database_path()
    if path is None:
        pytest.skip("no multicomponent steel TDB (set $BIGSIM_STEEL_TDB or download_mc_fe())")
    return demo.compute_alloy(cb.CalphadBackend(path), n=8)


def test_demo_binary_panel_quantifies_the_chord_error(binary_data):
    # The left panel's thesis: fe_c's linear A₃ chord sits *above* the CALPHAD curve
    # across the whole hypoeutectoid range, by a meaty-but-bounded amount at mid-carbon.
    deviation = binary_data["a3_linear"] - binary_data["a3_calphad"]
    assert np.all(deviation > 0.0)                         # chord systematically too high
    assert 20.0 <= deviation.max() <= 40.0                 # the quantified parametrisation error
    # The emergent eutectoid lands next to fe_c's pinned value (the wiring smoke-test).
    Te, Ce = binary_data["eutectoid_calphad"]
    assert Te == pytest.approx(727.0, abs=3.0)
    assert Ce == pytest.approx(0.76, abs=0.02)


def test_demo_alloy_panel_shows_multicomponent_richness(alloy_data):
    # A ferrite+austenite region (A₁ < A₃), a stable chromium carbide, and the
    # composition closing on austenite (fraction → 1) above A₃ — all beyond fe_c.
    assert alloy_data["A1"] < alloy_data["A3"]
    assert alloy_data["fractions"]["carbide"].max() > 0.0
    assert alloy_data["fractions"]["austenite"].max() == pytest.approx(1.0, abs=1e-3)
    Ae1, Ae3 = alloy_data["andrews"]
    assert abs(alloy_data["A1"] - Ae1) < 20.0              # within Andrews' scatter (loose)
    assert abs(alloy_data["A3"] - Ae3) < 20.0


def test_calphad_figure_builds(binary_data):
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    # Reuses the already-computed binary data; the binary-only panel is enough to
    # exercise the renderer (the alloy panel is covered by its own data test above).
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import calphad_figure

    fig = calphad_figure(binary_data, None)
    assert len(fig.axes) == 1
    plt.pyplot.close(fig)
