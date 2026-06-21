"""The game's headless golden run — play the Slice-0 heat twice and bank the blow-curve figure.

The runnable face of the ``game/`` package (the gallery card's ``python -m game.demo_game``): it plays the
playable chain headless at two blow endpoints — the **reference** (on-aim) and an **over-blow** — and
prints the contrast the interactive app lets you reach by hand. It is the same golden run the
``test_game_golden_run`` tooth pins: stepping the game chain reproduces ``demo_capstone.run_chain``'s
sealed verdict exactly, so the reference lands a sound part and the over-blow soft-cores — **no physics
here, only orchestration** (``game.md`` §2). It also banks the blow-endpoint τ-curve figure (the value
selection surface) for the gallery's *Game* card.

Run it::

    python -m game.demo_game                  # prints the contrast, banks the figure (needs .[viz] for the PNG)
    streamlit run game/app_game.py            # the interactive version (needs .[viz,app])
"""
from __future__ import annotations

from pathlib import Path

from . import knobs as kn
from . import state as gs
from steel.demo_capstone import FOIL_CARBON, REF_CARBON

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _play(carbon_target: float) -> dict:
    """Play one heat to the finished part and return its verdict readout (the tested helper)."""
    return gs.final_readout(gs.play_to_end(carbon_target))


def print_summary() -> None:
    """Print the two-endpoint contrast — the same single-knob story the app surfaces, played headless."""
    lo, hi = kn.grade_carbon_window()
    print("\nThe playable chain (Slice 0) — one heat of 4140, you set the F2 decarb blow endpoint.\n")
    print(f"The grade carbon window is {lo:.2f}–{hi:.2f} % (aim {kn.grade_carbon_aim():.2f} %); the only "
          "knob is where you stop the blow. Two heats, the identical chain otherwise:\n")

    for label, carbon in (("Reference — on aim", REF_CARBON), ("Over-blow — too far", FOIL_CARBON)):
        r = _play(carbon)
        pos = kn.endpoint_position(carbon)
        print(f"{label} ({carbon:.2f} %C, {pos.oxygen_ppm:.0f} ppm O at the blow):")
        for step in r["trail"]:
            print(f"    {step['mark']} {step['name']}: {step['summary']}")
        print(f"    → {r['verdict']}\n")

    print("Same chain, one knob: stop in the window and the part through-hardens; over-blow and the carbon "
          "shortfall soft-cores it two stages later — the back-end physics, reached through play.")


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ✓/✗ on legacy codepages

    print_summary()
    try:
        from .figures import save_figure
        saved = save_figure(REF_CARBON)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
