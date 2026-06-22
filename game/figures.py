"""``game.figures`` — the figure layer (matplotlib imported lazily; the ``app.py`` three-layer idiom).

The **blow τ-curve** figure (``game.md`` §6, Slice 0): the value-selection surface for the one knob,
drawn over the validated F2 refining engine (:mod:`game.knobs`) — *not* a figure that invents physics.
Two stacked panels make the verified/flavor split visible:

* **Top (flavor, labelled).** The blow *trajectory* — carbon falling first-order with blow progress
  toward the chosen endpoint. The *shape* is game feel (Tier-3 kinetics, not a validated rate); both ends
  it runs between are real.
* **Bottom (validated).** Dissolved oxygen vs carbon endpoint — the C–O coupling
  (:func:`steel.refining.equilibrium_oxygen`), monotone-climbing as carbon falls. The cited grade window
  is shaded (the aim), the over-blow region flagged, and the player's endpoint marked: the "flame-drop"
  as a **position** on the curve, not a clock (``game.md`` §3.3).

This module imports matplotlib **only inside** its functions, so the package imports on a bare core
install and the logic layers stay headless. It invents no validated physics — every datum is a
:mod:`game.knobs` read (which is a pass-through to the sealed engine).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from . import knobs as kn
from steel.demo_capstone import REF_CARBON

if TYPE_CHECKING:
    from .demo_game_methods import MethodsDemo

_REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_FIGURE = _REPO_ROOT / "docs" / "figures" / "steel-game-blow.png"
OUTPUT_FIGURE = _REPO_ROOT / "outputs" / "steel-game-blow.png"

# Zone → endpoint marker colour (on-aim good, off the window bad) — display only, not physics.
_ZONE_COLOR = {"on-aim": "#2e9e5b", "over-blow": "#d2483a", "under-blow": "#d98a29"}


def blow_curve_figure(carbon_target: float = REF_CARBON):
    """Build the blow τ-curve figure for a chosen endpoint — flavor trajectory + validated C–O readout.

    Returns a matplotlib ``Figure`` (caller renders or saves). The endpoint marker is coloured by zone
    (on-aim / over-blow / under-blow) and the validated dissolved-oxygen value at the endpoint is
    annotated — all read live from :mod:`game.knobs`.
    """
    import matplotlib.pyplot as plt

    pos = kn.endpoint_position(carbon_target)
    lo, hi = pos.window
    color = _ZONE_COLOR.get(pos.zone, "#888888")

    fig, (ax_t, ax_o) = plt.subplots(2, 1, figsize=(7.5, 7.0), height_ratios=[1.0, 1.4])

    # --- top: the flavor trajectory (carbon vs blow progress) ----------------------------------------- #
    progress, carbons = kn.blow_trajectory(carbon_target)
    ax_t.plot([p * 100 for p in progress], carbons, color="#5ab0ff", lw=2.2)
    ax_t.axhline(carbon_target, color=color, ls="--", lw=1.4)
    ax_t.axhspan(lo, hi, color="#2e9e5b", alpha=0.12)
    ax_t.set_xlabel("blow progress (%)  —  shape is game feel, not a validated rate")
    ax_t.set_ylabel("carbon (wt %)")
    ax_t.set_title("The blow trajectory  ·  flavor (plausible, not validated)", fontsize=11)
    ax_t.annotate(f"endpoint {carbon_target:.2f} %C", xy=(100, carbon_target),
                  xytext=(-6, 6), textcoords="offset points", ha="right", color=color, fontsize=9)

    # --- bottom: the validated C–O readout (dissolved O vs carbon endpoint) ---------------------------- #
    cs, os_ = kn.oxygen_curve()
    ax_o.plot(cs, os_, color="#1f2a44", lw=2.4, zorder=3)
    ax_o.axvspan(lo, hi, color="#2e9e5b", alpha=0.16, label=f"grade window {lo:.2f}–{hi:.2f} %C (aim)")
    ax_o.axvspan(kn.BLOW_C_MIN, lo, color="#d2483a", alpha=0.10, label="over-blow (off-grade + O climbing)")
    ax_o.axvline(carbon_target, color=color, ls="--", lw=1.6, zorder=4)
    ax_o.scatter([carbon_target], [pos.oxygen_ppm], color=color, s=60, zorder=5, edgecolor="k", linewidth=0.5)
    ax_o.annotate(f"{pos.oxygen_ppm:.0f} ppm O", xy=(carbon_target, pos.oxygen_ppm),
                  xytext=(8, 8), textcoords="offset points", color=color, fontsize=9.5, fontweight="bold")
    ax_o.invert_xaxis()                                   # blow runs left→right as carbon falls
    ax_o.set_xlabel("blow endpoint — carbon (wt %)   ◀ more blow")
    ax_o.set_ylabel("dissolved oxygen (ppm)")
    ax_o.set_title(
        f"Dissolved oxygen climbs as you over-blow  ·  validated (C–O product ≈ {kn.carbon_oxygen_product():.4f})",
        fontsize=11,
    )
    ax_o.legend(loc="upper left", fontsize=8.5, framealpha=0.3)

    fig.suptitle(f"Set the blow endpoint  —  {pos.zone.replace('-', ' ')}", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def methods_figure(demo: "MethodsDemo"):
    """Build the purity-ramp figure (``game.md`` §6 Slice 2) — residual P and S down the era tech tree.

    Two stacked panels for the **phosphoric** ore (the "hard mode" that needs the full chain): residual
    phosphorus (top) and sulfur (bottom) after each era, with the cleanliness spec lines drawn. Each era's
    point is coloured by whether that run came out sound, so the eye reads the ramp directly — phosphorus
    drops below spec at Thomas (the basic slag), sulfur only at the modern ladle. Every datum is a played run
    (:func:`game.demo_game_methods.compute`), i.e. the sealed engines' own output — the figure invents nothing.
    """
    import matplotlib.pyplot as plt

    # The phosphoric ore is the informative column (the clean ore is sound everywhere — nothing to ramp).
    ore = next((o for o in demo.outcomes if o.P > 0.05), demo.outcomes[0]).ore
    row = [o for o in demo.outcomes if o.ore is ore]
    labels = [f"{o.method.year}\n{o.method.name}" for o in row]
    x = list(range(len(row)))
    good, bad = "#2e9e5b", "#d2483a"
    # Colour each panel by THAT tramp's own spec status (not the whole run's verdict): so the phosphorus
    # panel goes green exactly when phosphorus is conquered (Thomas), the sulfur panel when sulfur is (ladle).
    p_colors = [good if o.P <= demo.p_spec else bad for o in row]
    s_colors = [good if o.S <= demo.s_spec else bad for o in row]

    fig, (ax_p, ax_s) = plt.subplots(2, 1, figsize=(8.5, 7.4), sharex=True)

    ax_p.plot(x, [o.P * 100 for o in row], color="#1f2a44", lw=1.6, zorder=2)
    ax_p.scatter(x, [o.P * 100 for o in row], c=p_colors, s=80, zorder=3, edgecolor="k", linewidth=0.5)
    ax_p.axhline(demo.p_spec * 100, color=bad, ls="--", lw=1.3,
                 label=f"cold-short spec ≤ {demo.p_spec * 100:.3f} %P")
    ax_p.set_ylabel("residual phosphorus (·10⁻² wt %)")
    ax_p.set_title("Phosphorus — conquered at Thomas (the basic slag)  ·  validated (Healy L_P)", fontsize=11)
    ax_p.legend(loc="upper right", fontsize=8.5, framealpha=0.3)

    ax_s.plot(x, [o.S * 100 for o in row], color="#1f2a44", lw=1.6, zorder=2)
    ax_s.scatter(x, [o.S * 100 for o in row], c=s_colors, s=80, zorder=3, edgecolor="k", linewidth=0.5)
    ax_s.axhline(demo.s_spec * 100, color=bad, ls="--", lw=1.3,
                 label=f"cleanliness spec ≤ {demo.s_spec * 100:.3f} %S")
    ax_s.set_ylabel("residual sulfur (·10⁻² wt %)")
    ax_s.set_title("Sulfur — conquered only at the modern ladle  ·  validated (sulfide capacity L_S)", fontsize=11)
    ax_s.set_xticks(x)
    ax_s.set_xticklabels(labels, fontsize=8.5)
    ax_s.legend(loc="lower left", fontsize=8.5, framealpha=0.3)

    fig.suptitle(f"The purity-control ramp  —  {ore.name} up the §15.2 tech tree", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def save_figure(carbon_target: float = REF_CARBON) -> Path:
    """Render and bank the blow τ-curve artifact (needs the optional ``viz`` extra). Returns the docs path."""
    import matplotlib
    matplotlib.use("Agg")                                # headless

    fig = blow_curve_figure(carbon_target)
    for target in (DOCS_FIGURE, OUTPUT_FIGURE):
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=130)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return DOCS_FIGURE


if __name__ == "__main__":
    saved = save_figure()
    print(f"wrote {saved.relative_to(_REPO_ROOT)}")
