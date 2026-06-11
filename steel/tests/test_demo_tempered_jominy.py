"""Integration test for the tempered-Jominy demo (Steel plan §16 — the demo IS the integration test).

The tempered-Jominy demo wires the whole spatial chain together with a per-constituent temper
on top — ``jominy`` (one shared thermal field) → ``pathint`` (path → microstructure) →
``kinetics`` (``ccurve_for_steel``) → ``properties`` (mixture → **tempered** hardness). So its
compute pipeline is the end-to-end check that they compose, asserted on the *robust* qualitative
thesis (the differential temper: near end collapses, far end inert), bracketed by two already-
validated anchors — the exact tempered-Jominy numbers are pinned in ``test_properties.py``.

The figure itself is **not** in the correctness path (ADR 0002): rendering is checked only for
"builds without error", and skipped where the optional viz extra is absent.
"""
import numpy as np
import pytest

from steel.demo_tempered_jominy import compute, STEELS


def test_demo_pipeline_differential_temper():
    field, as_quenched, tempered = compute(n_cells=160, per_decade=80)
    assert set(as_quenched) == set(tempered) == set(STEELS) == {"1045", "4140"}

    aq45, t45 = as_quenched["1045"], tempered["1045"]
    aq41, t41 = as_quenched["4140"], tempered["4140"]

    # THE DIFFERENTIAL (1045: martensite near → pearlite far): the near end softens hard while
    # the far end (diffusional, temper-inert) does not move at all — the §16 teeth.
    drop_near = aq45.HV[0] - t45.HV[0]
    drop_far = aq45.HV[-1] - t45.HV[-1]
    assert drop_near > 100.0                              # near end (full martensite) collapses
    assert drop_far == 0.0                                # far end (ferrite-pearlite) is inert
    assert t45.martensite[-1] == 0.0                      # ...because there is no martensite there

    # BRACKET (near end, 4140): full martensite at the quenched end → reduces to 3b's validated
    # 4140 1 h temper response (~45 HRC at 400 °C; the 3b band 41–49).
    assert 41.0 <= t41.HRC[0] <= 49.0
    assert t41.HV[0] < aq41.HV[0]                         # tempering softened the quenched end


def test_demo_tempered_far_end_byte_identical_to_as_quenched():
    # The far-end bracket as a byte-exact claim: every position with no martensite is
    # temper-inert, so its tempered HV equals the as-quenched HV exactly (Seam B along the bar).
    _, as_quenched, tempered = compute(n_cells=160, per_decade=80)
    checked = 0
    for lbl in STEELS:
        aq, t = as_quenched[lbl], tempered[lbl]
        inert = t.martensite == 0.0
        assert np.array_equal(t.HV[inert], aq.HV[inert])
        checked += int(np.count_nonzero(inert))
    assert checked > 0          # 1045's pearlitic far end supplies inert positions (not a vacuous pass)


def test_tempered_jominy_figure_builds():
    # Viz smoke test only (never a correctness check): skip cleanly without the extra.
    plt = pytest.importorskip("matplotlib")
    plt.use("Agg")
    from steel.plots import tempered_jominy_figure

    _, as_quenched, tempered = compute(n_cells=120, per_decade=60)
    fig = tempered_jominy_figure(as_quenched, tempered)
    assert len(fig.axes) == 1
    plt.pyplot.close(fig)
