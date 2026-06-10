"""The Phase-6d demo: austempering — the isothermal bainite hold, atlas-anchored.

*Steel + hold in, bainitic microstructure + hardness out — with the anchoring shown.* Phase 6b's
cited :class:`~projects.steel.kinetics.BainiteReaction` was proven invalid in the continuous-
cooling race; the **isothermal hold** is where it becomes validly load-bearing (:mod:`austemper`).
The headline recipe is the classic one: **1080** (atlas p. 42) quenched to a salt-bath hold in the
austempering band, held to full bainite, cooled — springs-and-clips territory.

The figure (``plots.austemper_figure``) banks the story in three panels:

1. **The anchored isothermal diagram, with the atlas measurements on it.** The model's 50 %-line
   (anchored at ONE cited point, marked) runs through the *other* measured 50 % points — the
   holdout teeth, visible. The begin line is drawn too, honestly: anchored at t₅₀ its spacing
   runs wide (model ×39.5 vs measured ×9.5–14 — claims stop at the 50 % line). The hold path is
   the step over the diagram.
2. **The hold itself** — completion ``U(t)``, with the measured 50 % time at this temperature
   overlaid (151 s measured vs ~161 s predicted at 343.3 °C).
3. **Hardness vs hold time** — the austempering trade: too short a hold leaves austenite that
   shears to brittle untempered martensite on the cool; the **minimum full-transform hold** is
   marked, beyond which the structure is fully bainitic (~500 HV / ~49 HRC for 1080 — the
   carbon-only bainite placeholder, named).

Run headless (saves the figure, prints the summary):

    python -m projects.steel.demo_austemper
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import austemper as au

# The headline recipe: the classic austempering steel at a classic salt-bath hold (650 °F),
# held past full transformation. 343.3 °C is also a HOLDOUT temperature (not the anchor).
DEMO_STEEL = "1080"
DEMO_T_HOLD = 343.3          # °C
DEMO_T_HOLD_F = 650.0        # the same hold in °F (how a heat-treat shop would quote it)
DEMO_HOLD_S = 600.0          # s — comfortably past the minimum full-transform hold

# The hardness-vs-hold-time sweep (panel 3): seconds, log-spaced through the whole window.
SWEEP_HOLDS = np.geomspace(1.0, 1.0e4, 41)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-austemper.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-austemper.png"


@dataclass(frozen=True)
class AustemperDemo:
    """Validated arrays for the Phase-6d figure (the plot layer only draws these)."""

    steel: str
    T_hold: float
    Bs: float
    Ms: float
    # Panel 1 — the anchored isothermal diagram + the atlas read-offs.
    temps: np.ndarray                       # °C, the diagram's temperature axis
    t50_line: np.ndarray                    # s, the anchored model 50 %-line (validated)
    begin_line: np.ndarray                  # s, the model begin line (shape-only, named)
    atlas_t50_T: np.ndarray                 # the measured 50 % points (°C, s)
    atlas_t50_t: np.ndarray
    atlas_begin_T: np.ndarray               # the measured begin points (°C, s)
    atlas_begin_t: np.ndarray
    anchor_T: float                         # the ONE cited anchor point the scale came from
    anchor_t50: float
    # Panel 2 — the hold: completion U(t) + the measured 50 % time at this temperature.
    hold: au.AustemperResult
    measured_t50_here: float                # s (nan if the atlas has no 50 % read at T_hold)
    predicted_t50_here: float               # s
    # Panel 3 — hardness vs hold time + the minimum full-transform hold.
    sweep_t: np.ndarray
    sweep_HV: np.ndarray
    sweep_bainite: np.ndarray
    min_full_hold: float                    # s


def compute(steel: str = DEMO_STEEL, T_hold: float = DEMO_T_HOLD,
            t_hold: float = DEMO_HOLD_S) -> AustemperDemo:
    """Build the validated arrays for the figure — diagram, hold history, hardness sweep."""
    s = au.ATLAS_STEELS[steel]
    hold = au.austemper(steel, T_hold, t_hold)

    # Panel 1 — the anchored model lines across the austempering window, atlas points beside them.
    temps = np.linspace(hold.Ms + 2.0, hold.Bs - 2.0, 300)
    t50_line = np.array([au.hold_time_to_fraction(steel, float(T), au.ATLAS_T50_X) for T in temps])
    begin_line = np.array([au.hold_time_to_fraction(steel, float(T), au.ATLAS_BEGIN_X) for T in temps])

    # Panel 3 — the hardness-vs-hold sweep at the same hold temperature.
    sweep_HV = np.empty(SWEEP_HOLDS.size)
    sweep_bainite = np.empty(SWEEP_HOLDS.size)
    for i, th in enumerate(SWEEP_HOLDS):
        r = au.austemper(steel, T_hold, float(th), n_steps=2000)
        sweep_HV[i] = r.HV
        sweep_bainite[i] = r.bainite

    return AustemperDemo(
        steel=steel, T_hold=T_hold, Bs=hold.Bs, Ms=hold.Ms,
        temps=temps, t50_line=t50_line, begin_line=begin_line,
        atlas_t50_T=np.array(sorted(s.t50)), atlas_t50_t=np.array([s.t50[T] for T in sorted(s.t50)]),
        atlas_begin_T=np.array(sorted(s.begin)), atlas_begin_t=np.array([s.begin[T] for T in sorted(s.begin)]),
        anchor_T=s.T_anchor, anchor_t50=s.t50_anchor,
        hold=hold,
        measured_t50_here=s.t50.get(T_hold, float("nan")),
        predicted_t50_here=au.hold_time_to_fraction(steel, T_hold, au.ATLAS_T50_X),
        sweep_t=SWEEP_HOLDS, sweep_HV=sweep_HV, sweep_bainite=sweep_bainite,
        min_full_hold=au.minimum_full_hold(steel, T_hold),
    )


def print_summary(d: AustemperDemo) -> None:
    """Print the anchor table, the holdout verdict, the recipe result, and the named edges."""
    print("\nPhase 6d — austempering: the isothermal bainite hold (atlas-anchored)\n")
    print(f"Anchors ({au.ATLAS_SOURCE}):")
    for name, s in au.ATLAS_STEELS.items():
        print(f"  {name}  p.{s.page:<4} anchor {s.T_anchor:.1f} °C / {s.t50_anchor:.0f} s "
              f"→ derived scale {au.ANCHORED_SCALES[name]:8.3g}")
    gap = au.ANCHORED_SCALES["1080"] / au.ANCHORED_SCALES["4340"]
    print(f"  scale gap ×{gap:.0f} — THE DOCUMENTED NEGATIVE: no global scale exists; the cited BC")
    print(f"  arithmetic is wrong-signed across compositions (atlas: 4340 ~5× SLOWER than 1080;")
    print(f"  BC says ~7× faster) — BC is never used for absolute cross-steel times.\n")

    s = au.ATLAS_STEELS[d.steel]
    print(f"THE HOLDOUT TEETH ({d.steel}, anchored at {s.T_anchor:.1f} °C only):")
    for T in sorted(s.t50):
        if T == s.T_anchor:
            continue
        pred = au.hold_time_to_fraction(d.steel, T, au.ATLAS_T50_X)
        print(f"  t50 @ {T:5.1f} °C: predicted {pred:6.1f} s vs measured {s.t50[T]:6.1f} s "
              f"(×{pred / s.t50[T]:.2f})")

    h = d.hold
    print(f"\nTHE RECIPE — {d.steel} austempered {h.t_hold:.0f} s @ {h.T_hold:.1f} °C "
          f"({DEMO_T_HOLD_F:.0f} °F salt bath), window Ms {h.Ms:.0f} < T < Bs {h.Bs:.0f} °C:")
    for name, f in h.fractions().items():
        if f > 0.0:
            print(f"  {name:<20} {f:6.1%}")
    hrc = f"{h.HRC:.0f} HRC" if np.isfinite(h.HRC) else "(off HRC)"
    print(f"  hardness             {h.HV:.0f} HV ≈ {hrc}")
    print(f"  minimum full-transform hold ≈ {d.min_full_hold:.0f} s "
          f"(shorter holds leave austenite → brittle untempered martensite on the cool)")
    print(f"  pearlite-race shadow {h.pearlite_shadow:.1%} (policed, not modeled — "
          f"{'FLAGGED' if h.pearlite_race_flagged else 'silent in the anchored band'})")
    print("\nNAMED EDGES: claims stop at the 50 % line (begin→50 % spacing runs ×39.5 vs ×9.5–14")
    print("  measured); near-Ms acceleration unmodeled; bainite hardness = the carbon-only")
    print("  placeholder, now load-bearing (under-ranks alloyed bainite); pathint byte-identical.")


def save_figure(d: AustemperDemo) -> Path:
    """Render and save the Phase-6d artifact (needs the optional ``viz`` extra)."""
    import matplotlib
    matplotlib.use("Agg")                            # headless
    from .plots import austemper_figure

    fig = austemper_figure(d)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    return DOCS_FIGURE


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # °C, × on legacy codepages

    d = compute()
    print_summary(d)
    try:
        saved = save_figure(d)
        print(f"\nFigure saved → {saved.relative_to(_REPO_ROOT)}")
    except ImportError:
        print("\n(matplotlib not installed — install the viz extra to render the figure: "
              "pip install -e .[viz])")


if __name__ == "__main__":
    main()
