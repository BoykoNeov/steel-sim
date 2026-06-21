"""Golden-run determinism (``game.md`` §2/§8) — the game's strongest structural tooth.

Stepping the game chain to completion reproduces the **sealed** capstone's output *exactly*: the finished
``Heat`` from :func:`game.state.play_to_end` equals ``demo_capstone.run_chain(...).part``, field for field
(composition, filled gas/inclusion fields, defects, and the whole provenance trail). That equality **is**
the proof the game adds no physics — it only orchestrates the same seams in the same order, so it cannot
diverge from the validated engines. The reference blow endpoint lands a sound part; the over-blow
soft-cores — the same verdicts the sealed engines already produce (the game adds no scripted "you failed").
"""
from game import state as gs
from steel import heat_state as hs
from steel import ladle as ld
from steel.demo_capstone import REF_CARBON, FOIL_CARBON, run_chain


def test_stepping_reproduces_run_chain_exactly():
    # The whole point: the game IS the sealed chain, stepped. Frozen-dataclass equality compares every
    # field including the history tuple — a deep equality, the tightest possible "adds no physics" proof.
    for carbon in (REF_CARBON, FOIL_CARBON):
        finished = gs.play_to_end(carbon).heat
        sealed = run_chain(carbon).part
        assert finished == sealed, f"the game diverged from the sealed run_chain at C={carbon}"


def test_reference_endpoint_is_a_sound_part():
    # The reference blow endpoint → a clean, on-grade, through-hardened part (the back-end physics verdict,
    # reached through play — not a scripted success branch).
    state = gs.play_to_end(REF_CARBON)
    r = gs.final_readout(state)
    assert r["sound"] and not r["soft_core"] and not r["off_grade"]
    assert r["martensite"] >= r["spec"]
    assert state.heat.is_clean


def test_over_blow_endpoint_soft_cores():
    # The over-blow endpoint → off-grade at the trim AND a soft core at the quench: the emergent failure,
    # the martensite fraction crossing the spec line, carried on the same Heat.
    state = gs.play_to_end(FOIL_CARBON)
    r = gs.final_readout(state)
    assert r["soft_core"] and r["off_grade"]
    assert r["martensite"] < r["spec"]
    assert state.heat.has_defect(hs.SOFT_CORE) and state.heat.has_defect(ld.OFF_GRADE)


def test_finished_trail_is_the_whole_chain_in_order():
    # One continuous, un-rewritten trail: the charge origin through the heat-treat verdict, nine stages.
    expected = (
        "hot-metal charge", "decarburize", "dephosphorize", "deoxidize", "degas",
        "desulfurize", "trim", "cast", "heat-treat",
    )
    finished = gs.play_to_end(REF_CARBON).heat
    assert tuple(s.name for s in finished.history) == expected
