"""The methods/era tech tree, headless — the purity-control ramp played across the §15.2 method map.

The runnable face of Slice 2 (the gallery card's ``python -m game.demo_game_methods``): it plays the **same**
4140 chain through each historical/modern method (:mod:`game.presets`) on each ore, and prints the verdict
matrix — the **purity-control ramp** (``steel-making.md`` §14 theme C / §15.2) as a played progression. A
phosphoric ore is cold-short in acid Bessemer (acid slag, L_P≈1), phosphorus-fixed-but-still-dirty in Thomas
(basic slag, no ladle desulf), and sound only in the modern ladle era; a clean (non-phosphoric) ore is sound
even in acid Bessemer — *exactly* why the early Bessemer steelmakers fought over clean ore. Every verdict is
the sealed engines' own, read off one ``Heat`` per run — **no physics here, only orchestration** (``game.md``
§2): the game threads the same seams the capstone does, with the era fixing which dephosphorization slag runs
and whether the era has a reducing ladle.

Run it::

    python -m game.demo_game_methods           # prints the verdict matrix, banks the figure (needs .[viz])
    streamlit run game/app_game.py             # the interactive version (pick a method + ore; needs .[viz,app])
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from steel import slag as sl

from . import presets as pr
from . import state as gs

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-game-methods.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-game-methods.png"


@dataclass(frozen=True)
class EraOutcome:
    """One played run — a (method, ore) pair's finished-part verdict, read off the sealed engines.

    ``P`` / ``S`` are the finished part's residual phosphorus / sulfur (wt %), the purity-ramp axes;
    ``martensite`` the back-end hardenability read; ``consequences`` the post-mortem headlines (empty = sound).
    """

    method: pr.Method
    ore: pr.Ore
    sound: bool
    P: float
    S: float
    martensite: float
    consequences: tuple[str, ...]


@dataclass(frozen=True)
class MethodsDemo:
    """The whole tech-tree matrix plus the specs the ramp is judged against."""

    outcomes: tuple[EraOutcome, ...]
    p_spec: float
    s_spec: float

    def for_ore(self, ore: pr.Ore) -> list[EraOutcome]:
        """The era ladder (oldest → newest) for one ore — the purity ramp the figure draws."""
        return [o for o in self.outcomes if o.ore is ore]


def _play(method: pr.Method, ore: pr.Ore) -> EraOutcome:
    """Play one heat through ``method`` on ``ore`` and read the finished-part verdict (the tested helper)."""
    state = gs.play_to_end(method=method, ore=ore)
    r = gs.final_readout(state)
    part = state.heat
    return EraOutcome(
        method=method, ore=ore, sound=r["sound"],
        P=float(part.composition.P), S=float(part.composition.S),
        martensite=float(r["martensite"]),
        consequences=tuple(c["headline"] for c in r["consequences"]),
    )


def compute() -> MethodsDemo:
    """Play every (method, ore) pair — the whole purity-ramp matrix the figure and the demo read."""
    outcomes = tuple(_play(m, ore) for ore in pr.ORES for m in pr.METHODS)
    return MethodsDemo(outcomes=outcomes, p_spec=sl.MAX_PHOSPHORUS_PCT, s_spec=sl.MAX_SULFUR_PCT)


# --------------------------------------------------------------------------- #
# The figure — bank the purity-ramp artifact (needs the optional viz extra)
# --------------------------------------------------------------------------- #
def save_figure(demo: MethodsDemo | None = None) -> Path:
    """Render and bank the purity-ramp artifact (needs the optional ``viz`` extra). Returns the docs path."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .figures import methods_figure

    demo = demo if demo is not None else compute()
    fig = methods_figure(demo)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return DOCS_FIGURE


# --------------------------------------------------------------------------- #
# The narrated run — the tech-tree story
# --------------------------------------------------------------------------- #
def print_summary(demo: MethodsDemo | None = None) -> None:
    """Print the verdict matrix — the purity-control ramp played across the §15.2 method map."""
    demo = demo if demo is not None else compute()

    print("\nThe tech tree (Slice 2) — one grade (4140), the §15.2 method map, the purity-control ramp.\n")
    print("Each era is the SAME validated chain with the era's refining chemistry: acid vs basic "
          "dephosphorization slag, and whether the era has a reducing ladle. The history is the difficulty "
          "curve — a dirty ore walks you up the tree.\n")

    for ore in pr.ORES:
        print(f"{ore.name} — P {ore.P:.3f} %, S {ore.S:.3f} % on the charge:")
        for o in demo.for_ore(ore):
            verdict = "SOUND  " if o.sound else "SPOILED"
            flaws = "" if o.sound else "  ← " + ", ".join(o.consequences)
            print(f"    {o.method.year}  {o.method.name:24s}  P {o.P:.3f}  S {o.S:.3f}  {verdict}{flaws}")
        print()

    print("Read the phosphoric-ore column top to bottom: phosphorus falls below spec only at Thomas (the "
          "basic slag), sulfur only at the modern ladle. Each era conquers one more tramp — the §14 "
          "purity-control ramp, played. The clean ore is sound even in acid Bessemer: the non-phosphoric "
          "ore the early Bessemer trade was built on.")
    print(f"\n{pr.BLOOMERY_NOTE}")


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, →, ✓/✗ on legacy codepages

    demo = compute()
    print_summary(demo)
    try:
        saved = save_figure(demo)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
