"""The game's headless golden run — play the gauntlet sound, then rough, and bank the blow-curve figure.

The runnable face of the ``game/`` package (the gallery card's ``python -m game.demo_game``): it plays the
chain headless two ways — the **reference** (take every recommendation → a sound part, reproducing
``demo_capstone.run_chain`` exactly) and a **rough heat** (several wrong calls → a part the post-mortem
condemns) — and prints the contrast the interactive app lets you reach by hand. The sound run is the same
golden run the ``test_game_golden_run`` tooth pins (the recipe never drifts off the reference), and every
losing defect is the sealed engines' own verdict on the one ``Heat`` — **no physics here, only orchestration**
(``game.md`` §2). It also banks the blow-endpoint τ-curve figure for the gallery's *Game* card.

Run it::

    python -m game.demo_game                  # prints the contrast, banks the figure (needs .[viz] for the PNG)
    streamlit run game/app_game.py            # the interactive version (needs .[viz,app])
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from steel.demo_capstone import REF_CARBON

from . import choices as ch
from . import state as gs

_REPO_ROOT = Path(__file__).resolve().parents[1]

# A rough heat — a handful of deliberate wrong calls, each planting a different latent flaw the sealed
# post-mortem engines surface on the finished part (skipped dephos → cold-short; a weak Mn kill → gas
# porosity; a shallow vacuum → flaking; skipped desulf → sulfur over the cleanliness spec).
ROUGH = dataclasses.replace(
    gs.REFERENCE, dephosphorize=False, deoxidizer="Mn", degas_p_H2=ch.DEGAS_SHALLOW, desulfurize=False,
)


def _play(recipe: gs.Recipe) -> dict:
    """Play one heat to the finished part and return its verdict readout (the tested helper)."""
    return gs.final_readout(gs.play_to_end(recipe=recipe))


def _print_heat(title: str, recipe: gs.Recipe) -> None:
    r = _play(recipe)
    print(f"{title}:")
    for step in r["trail"]:
        print(f"    {step['mark']} {step['name']}: {step['summary']}")
    print(f"    → {r['verdict']}")
    if r["consequences"]:
        print("    post-mortem — what each wrong call became:")
        for c in r["consequences"]:
            print(f"        ✗ {c['headline']} (planted at {c['planted_by']}): {c['detail']}")
    print()


def print_summary() -> None:
    """Print the gauntlet contrast — the same chain, played safe then rough, judged by the sealed engines."""
    print("\nThe gauntlet (Slice 1) — one heat of 4140, every stage a decision.\n")
    print("Take every recommendation and the heat comes out sound — and reproduces the capstone reference "
          "exactly. Get a stage wrong and you plant a flaw the finished part is judged on:\n")

    _print_heat(f"Reference — every recommendation (blow {REF_CARBON:.2f} %C)", gs.REFERENCE)
    _print_heat("Rough heat — skip the dephos, a weak Mn kill, a shallow vacuum, skip the desulf", ROUGH)

    print("Same chain, same sealed engines: the recommendations land a sound part; the wrong calls each "
          "leave a latent flaw — over-oxidized, gassy, dirty — that surfaces only when the part is judged.")


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ✓/✗ on legacy codepages

    print_summary()
    try:
        from .figures import save_figure
        saved = save_figure(REF_CARBON)
        print(f"Figure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
