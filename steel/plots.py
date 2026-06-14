"""Steel-local plot helpers — the render layer (Steel Phase 1c; ADR 0002).

The **viz floor**: static matplotlib figures that *consume* the plain arrays the
compute modules produce. Per ADR 0002 this layer is strictly downstream of
correctness — a figure draws already-validated numbers, it is never evidence of
validity (the triad tests do that). It is also the only place in steel that
imports a plotting library; :mod:`kinetics`/:mod:`pathint`/:mod:`cooling` stay
headless, so the test suite never needs matplotlib.

The headline view is the **mechanism** one ADR 0002 §5 calls for: the four cooling
paths drawn *across* the TTT C-curve, so a learner sees *why* a fast quench misses
the nose and lands in martensite while a slow cool runs into pearlite. These
helpers start project-local; a primitive earns promotion to a shared ``viz/`` only
by rule-of-three, like :mod:`pathint`.

Requires the optional ``viz`` extra (``pip install -e .[viz]``).
"""
from __future__ import annotations

import math

import numpy as np
import matplotlib.pyplot as plt

from . import grain
from .kinetics import CCurve
from .pathint import TransformResult
from .cooling import CoolingPath
from .grain import GrainProperties
from .properties import JominyHardness, RELIABLE_HRC_MIN, rockwell_c_to_vickers
from .carburize import CarburizedProfile, CarburizedTraverse

# Stable colours so the legend reads the same across every figure.
PHASE_COLORS = {
    "ferrite": "#f2d7a8",             # pale — soft proeutectoid α (the diffusional high-T product, Phase 6a)
    "pearlite": "#e8833a",            # warm — diffusional, slow, soft
    "bainite": "#4a9b5e",
    "martensite": "#3b6db5",          # cool — athermal, fast, hard
    "retained_austenite": "#9aa0a6",
}
PHASE_LABELS = {
    "ferrite": "proeutectoid ferrite",
    "pearlite": "pearlite",
    "bainite": "bainite",
    "martensite": "martensite",
    "retained_austenite": "retained γ",
}
MEDIUM_COLORS = {
    "furnace": "#b03a2e",
    "air": "#e67e22",
    "oil": "#1e8449",
    "water": "#2471a3",
}


def _hardness_label(HV: float, HRC: float) -> str:
    """Bar annotation: real Vickers + Rockwell-C (``off HRC`` where HRC is undefined)."""
    if np.isfinite(HRC):
        return f"{HV:.0f} HV\n{HRC:.0f} HRC"
    return f"{HV:.0f} HV\n(off HRC)"


def plot_ttt(
    ax: "plt.Axes", ccurve: CCurve, n_pts: int = 400,
    t_lim: tuple[float, float] = (0.1, 1e6), T_top: float = 880.0,
) -> "plt.Axes":
    """Draw the TTT C-curve (start + finish) with the A₁ ceiling, Mₛ floor, and nose.

    ``T`` on the vertical axis, **log time** on the horizontal — the standard TTT
    layout. The C opens rightward because ``τ(T)`` is shortest at the nose. Active
    window only (``Mₛ < T < A₁``); above A₁ there is no driving force, below Mₛ
    martensite governs. The axes are bounded explicitly: near A₁ the start time
    diverges to ~1e18 s (vanishing driving force), which would otherwise hand the
    log locator a pathological range.
    """
    temps = np.linspace(ccurve.Ms + 2.0, ccurve.T_eq - 2.0, n_pts)
    t_start = np.array([ccurve.time_to_fraction(float(T), 0.01) for T in temps])
    t_finish = np.array([ccurve.time_to_fraction(float(T), 0.99) for T in temps])
    # Keep only points that fall within the plotted window (drops the near-A₁ blow-up).
    keep = np.isfinite(t_start) & np.isfinite(t_finish) & (t_finish < t_lim[1])

    ax.plot(t_start[keep], temps[keep], "k-", lw=2.0, label="start (1 %)")
    ax.plot(t_finish[keep], temps[keep], "k--", lw=1.6, label="finish (99 %)")
    ax.fill_betweenx(temps[keep], t_start[keep], t_finish[keep],
                     color="0.85", alpha=0.6, zorder=0)

    ax.set_xscale("log")
    ax.set_xlim(*t_lim)
    ax.set_ylim(0.0, T_top)

    ax.axhline(ccurve.T_eq, color="0.4", ls=":", lw=1.2)
    ax.axhline(ccurve.Ms, color="#3b6db5", ls=":", lw=1.2)
    ax.text(t_lim[0] * 1.3, ccurve.T_eq + 6, "A₁", va="bottom", ha="left",
            color="0.3", fontsize=9)
    ax.text(t_lim[0] * 1.3, ccurve.Ms + 6, "Mₛ", va="bottom", ha="left",
            color="#3b6db5", fontsize=9)

    T_nose, t_nose = ccurve.nose(X=0.01)
    ax.plot([t_nose], [T_nose], "ko", ms=5)
    ax.annotate(f"nose\n{T_nose:.0f} °C, {t_nose:.1f} s", (t_nose, T_nose),
                textcoords="offset points", xytext=(8, -26), fontsize=8, color="0.2")

    ax.set_xlabel("time  (s)")
    ax.set_ylabel("temperature  (°C)")
    return ax


def plot_cooling_paths(
    ax: "plt.Axes", paths: list[CoolingPath], results: list[TransformResult] | None = None
) -> "plt.Axes":
    """Overlay cooling histories ``T(t)`` on a TTT axis (call after :func:`plot_ttt`).

    Each path is a coloured curve falling left→right across the C-curve; the legend
    labels it with its medium and (if ``results`` given) the dominant product, so
    the figure reads as *medium → where it crosses → what it becomes*.
    """
    for i, p in enumerate(paths):
        m = p.t > 0.0                              # drop t=0 for the log axis
        label = p.name
        if results is not None:
            r = results[i]
            dom = r.dominant()
            label = f"{p.name} → {dom.replace('_', ' ')}"
            # For a diffusional product, show *where on the C-curve* it formed — the
            # kinetic cue that separates furnace- from air-pearlite (higher = coarser).
            if dom in ("pearlite", "bainite") and np.isfinite(r.formation_T):
                label += f"  (~{r.formation_T:.0f} °C)"
        ax.plot(p.t[m], p.T[m], color=MEDIUM_COLORS.get(p.name, f"C{i}"),
                lw=2.0, label=label)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    return ax


def plot_microstructure_bars(
    ax: "plt.Axes", paths: list[CoolingPath], results: list[TransformResult],
    hardness: list[tuple[float, float]] | None = None,
) -> "plt.Axes":
    """Stacked phase-fraction bars per medium — the four resulting microstructures.

    One stacked bar per cooling path (pearlite/bainite/martensite/retained γ). If
    ``hardness`` is supplied (a list of ``(HV, HRC)`` per path, from the validated
    :mod:`properties` model — Phase 3), each bar is annotated with its **real** hardness;
    otherwise the bars carry no hardness label (the figure still builds). Hardness is
    computed upstream (ADR 0002: viz consumes validated numbers, never derives them).
    """
    order = ["ferrite", "pearlite", "bainite", "martensite", "retained_austenite"]
    names = [p.name for p in paths]
    x = np.arange(len(names))
    bottom = np.zeros(len(names))
    for phase in order:
        vals = np.array([r.fractions()[phase] for r in results])
        ax.bar(x, vals, bottom=bottom, color=PHASE_COLORS[phase],
               label=PHASE_LABELS[phase], width=0.7, edgecolor="white", linewidth=0.5)
        bottom += vals

    if hardness is not None:
        for xi, (HV, HRC) in zip(x, hardness):
            ax.text(xi, 1.02, _hardness_label(HV, HRC), ha="center", va="bottom",
                    fontsize=7.5, color="0.2", rotation=0, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.18)
    ax.set_ylabel("mass fraction")
    ax.set_xlabel("quench medium")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=4, fontsize=8,
              frameon=False)
    return ax


def microstructure_schematic(
    ax: "plt.Axes", fractions: dict, *, n: int = 16, seed: int = 0,
    title: str | None = None, legend: bool = True,
) -> "plt.Axes":
    """A **schematic** microstructure swatch whose cell areas track the phase fractions.

    Tiles an ``n × n`` field and allocates cells to each constituent in proportion to
    ``fractions`` (the validated :meth:`~steel.pathint.TransformResult.fractions`
    dict — pearlite/bainite/martensite/retained_austenite), coloured by
    :data:`PHASE_COLORS` with a light morphology hatch (pearlite lamellae ``---``,
    martensite laths ``///``, bainite ``xx``). The allocation is **deterministic** (a fixed
    ``seed``), so the same fractions always draw the same swatch — a committed/re-run notebook
    stays stable, and dragging a slider morphs the field smoothly as the fractions change.

    **This is an illustration, not a simulation** (ADR 0002 — the render layer is *reach, not
    evidence*). Only the cell **areas** carry validated information (they are the phase
    fractions); the grain *shapes, sizes and placement are decorative* — there is no
    grain-size or morphology model behind them (that is the deferred grain-physics phase). The
    axis label says so, so the figure cannot be mistaken for a micrograph.
    """
    from matplotlib.patches import Rectangle, Patch

    order = ["ferrite", "pearlite", "bainite", "martensite", "retained_austenite"]
    hatches = {"ferrite": "", "pearlite": "---", "bainite": "xx", "martensite": "///",
               "retained_austenite": ""}
    total = n * n
    # Cell counts ∝ fractions, summing *exactly* to total (the largest phase absorbs the
    # rounding remainder, so areas stay faithful and the grid is always full).
    counts = {p: int(round(float(fractions.get(p, 0.0)) * total)) for p in order}
    drift = total - sum(counts.values())
    if drift != 0:
        biggest = max(order, key=lambda p: float(fractions.get(p, 0.0)))
        counts[biggest] = max(0, counts[biggest] + drift)
    cells: list[str] = []
    for p in order:
        cells.extend([p] * counts[p])
    cells = cells[:total] + ["retained_austenite"] * max(0, total - len(cells))
    np.random.default_rng(seed).shuffle(cells)   # deterministic "mixed" placement

    ax.set_xlim(0, n); ax.set_ylim(0, n); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for idx, p in enumerate(cells):
        r, c = divmod(idx, n)
        ax.add_patch(Rectangle((c, r), 1, 1, facecolor=PHASE_COLORS[p],
                               edgecolor="white", linewidth=0.4, hatch=hatches[p]))
    if title:
        ax.set_title(title, fontsize=10.5)
    if legend:
        present = [p for p in order if counts[p] > 0]
        ax.legend(handles=[Patch(facecolor=PHASE_COLORS[p], label=PHASE_LABELS[p])
                           for p in present],
                  loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=4,
                  fontsize=7.5, frameon=False)
    ax.text(0.5, -0.16, "schematic — areas ∝ phase fractions; shapes illustrative (not a grain simulation)",
            transform=ax.transAxes, ha="center", va="top", fontsize=6.8, color="0.45")
    return ax


# Stable per-steel colours for the Jominy artifact (plain-carbon warm, alloy cool).
STEEL_COLORS = {
    "1045": "#c0392b",
    "4140": "#2471a3",
}


def jominy_hardness_figure(
    curves: dict[str, JominyHardness],
    references: dict[str, tuple] | None = None,
    title: str = "Jominy hardenability: a plain-carbon (1045) vs an alloy steel (4140)",
) -> "plt.Figure":
    """The banked **Phase-2 artifact**: hardness vs distance from the quenched end.

    ``curves`` maps a steel label → its :class:`~steel.properties.JominyHardness`
    traverse (from :func:`~steel.properties.jominy_hardness`). Optional
    ``references`` maps a label → ``(distance_mm, HRC)`` of *published* end-quench points
    (reference facts, supplied by the demo) drawn as markers for comparison.

    The thesis the figure makes visible: both steels **share the quenched-end hardness**
    (set by ~0.4 %C martensite — the validated-in-isolation hardness model) and then
    **diverge with distance** — 4140 holds its deep-hardening plateau while 1045 falls to
    a soft, *off-HRC-scale* ferrite-pearlite tail (the validated Phase-2b hardenability
    shift, read out in hardness). Points below ~20 HRC are not plotted on the HRC axis
    (Rockwell-C is undefined there); the 1045 tail is annotated instead.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    for label, h in curves.items():
        color = STEEL_COLORS.get(label, None)
        dist_mm = h.distance * 1000.0
        finite = np.isfinite(h.HRC)
        ax.plot(dist_mm[finite], h.HRC[finite], "-o", color=color, ms=4, lw=2.2, label=label)
        # If the curve runs off the bottom of the HRC scale (soft tail), mark where.
        if not np.all(finite) and np.any(finite):
            last = dist_mm[finite][-1]
            ax.annotate(f"{label} → soft ferrite-pearlite\n(off HRC scale, < {RELIABLE_HRC_MIN:.0f} HRC)",
                        (last, h.HRC[finite][-1]), textcoords="offset points",
                        xytext=(6, -28), fontsize=8, color=color,
                        arrowprops=dict(arrowstyle="->", color=color, lw=1.0))

    if references:
        for label, (dist_mm, hrc) in references.items():
            ax.plot(dist_mm, hrc, "s", color=STEEL_COLORS.get(label, "0.4"),
                    mfc="none", ms=8, mew=1.6,
                    label=f"{label} (published)")

    ax.axhline(RELIABLE_HRC_MIN, color="0.7", ls=":", lw=1.0)
    ax.text(ax.get_xlim()[1], RELIABLE_HRC_MIN + 0.4, "HRC scale floor (~20)",
            va="bottom", ha="right", fontsize=8, color="0.5")

    ax.set_xlabel("distance from quenched end  (mm)")
    ax.set_ylabel("hardness  (HRC)")
    ax.set_ylim(RELIABLE_HRC_MIN - 2.0, 66.0)
    ax.set_xlim(left=0.0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig


def tempered_jominy_figure(
    as_quenched: dict[str, JominyHardness],
    tempered: dict[str, JominyHardness],
    temper_label: str = "tempered 1 h @ 400 °C",
    title: str = "Mixed-structure tempering: per-constituent temper across a Jominy bar",
) -> "plt.Figure":
    """The banked **§16 artifact**: an as-quenched vs **tempered** Jominy traverse overlay.

    ``as_quenched`` and ``tempered`` each map a steel label → its
    :class:`~steel.properties.JominyHardness` traverse on the *same* distances (from
    :func:`~steel.properties.jominy_hardness` and :func:`~steel.properties.tempered_jominy_hardness`).
    Each steel is drawn as-quenched (**solid**) and tempered (**dashed**) in the same colour.

    The thesis the figure makes visible — the **differential** temper (plan §16): the temper
    acts **per-constituent**, so the **near end** (full martensite) softens *hard* while the
    **far end** (diffusional ferrite-pearlite, temper-INERT) does not move at all — the dashed
    and solid curves *coincide* there. A shallow-hardening steel (1045: martensite near →
    pearlite far) shows the differential within one bar; a deep-hardening one (4140: martensite
    throughout) softens more uniformly. Drawn in **HV**, not HRC, on purpose: the "far end
    barely moves" story lives in the soft-pearlite region that Rockwell-C cannot display
    (``nan`` below ~20 HRC) — the deliberate departure from :func:`jominy_hardness_figure`.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    for label, h_aq in as_quenched.items():
        color = STEEL_COLORS.get(label, None)
        dist_mm = h_aq.distance * 1000.0
        ax.plot(dist_mm, h_aq.HV, "-", color=color, lw=2.2, label=f"{label} as-quenched")
        h_t = tempered[label]
        ax.plot(h_t.distance * 1000.0, h_t.HV, "--", color=color, lw=2.2,
                label=f"{label} {temper_label}")
        # Shade the near-end softening gap (the martensite that tempered away) for emphasis.
        ax.fill_between(dist_mm, h_t.HV, h_aq.HV, color=color, alpha=0.08)

    # The two ends, annotated as the differential: near collapses, far is inert.
    any_label = next(iter(as_quenched))
    d_mm = as_quenched[any_label].distance * 1000.0
    ax.annotate("near end (full martensite):\ntempers hard ↓",
                (d_mm[0], tempered[any_label].HV[0]),
                xytext=(d_mm[0] + 2.0, 300.0), fontsize=8.5, color="0.25",
                arrowprops=dict(arrowstyle="->", color="0.4", lw=1.0))
    ax.annotate("far end (ferrite-pearlite):\ntemper-inert — curves coincide",
                (d_mm[-1], as_quenched[any_label].HV[-1]),
                xytext=(d_mm[-1] - 9.0, as_quenched[any_label].HV[-1] + 130.0),
                fontsize=8.5, color="0.25", ha="left",
                arrowprops=dict(arrowstyle="->", color="0.4", lw=1.0))

    # A faint HRC reference: the E140 scale floor in HV (below it, HRC is undefined).
    floor_HV = rockwell_c_to_vickers(RELIABLE_HRC_MIN)
    ax.axhline(floor_HV, color="0.7", ls=":", lw=1.0)
    ax.text(ax.get_xlim()[1], floor_HV + 4.0, f"~{RELIABLE_HRC_MIN:.0f} HRC (E140 floor)",
            va="bottom", ha="right", fontsize=8, color="0.5")

    ax.set_xlabel("distance from quenched end  (mm)")
    ax.set_ylabel("hardness  (HV)")
    ax.set_xlim(left=0.0)
    ax.set_ylim(bottom=0.0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig


def carburize_figure(
    profile: CarburizedProfile,
    traverse: CarburizedTraverse,
    surface_hardness_band: tuple[float, float] = (62.0, 65.0),
    title: str = "Carburized case-hardened gradient (8620, 925 °C → oil quench)",
) -> "plt.Figure":
    """The banked **Phase-3c artifact**: a carburized cross-section, surface → core.

    Three stacked panels sharing the depth axis — *carbon profile → microstructure →
    hardness*, all from the **same** frozen solver in mass mode:

      1. **Carbon profile** ``C(x)`` (the numeric solve) with the analytic **erfc** overlay
         and the effective-case-depth (0.4 %C) marker — the analytical-limit leg made visible.
      2. **Microstructure gradient** — phase fractions vs depth (stacked). Retained austenite
         rises toward the high-carbon surface (the documented heavy-case effect).
      3. **Hardness traverse** — the martensite **potential** (the case as designed, the
         benchmark-bearing curve) over the full as-quenched rule of mixtures (dashed; it dips
         below the potential near the surface — the retained-austenite drag). A shaded band
         marks the published carburized-surface hardness for comparison.

    All numbers are computed upstream (ADR 0002: viz consumes validated arrays, never derives).
    """
    depth_mm = traverse.depth * 1000.0
    fig, (ax_c, ax_phase, ax_h) = plt.subplots(
        3, 1, figsize=(9, 10), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 1.1]},
    )

    # -- panel 1: carbon profile + erfc overlay + case-depth marker -------------- #
    pdepth_mm = profile.x * 1000.0
    ax_c.plot(pdepth_mm, profile.C, "-", color="#3b6db5", lw=2.2, label="numeric  C(x)")
    ax_c.plot(pdepth_mm, profile.erfc_profile(), "k--", lw=1.4, label="analytic  erfc")
    ax_c.axhline(profile.C_core, color="0.6", ls=":", lw=1.0)
    ecd = profile.case_depth() * 1000.0
    if np.isfinite(ecd):
        ax_c.axvline(ecd, color="#b03a2e", ls="-.", lw=1.3)
        ax_c.annotate(f"effective case depth\n(0.4 %C)  {ecd:.2f} mm", (ecd, 0.5),
                      textcoords="offset points", xytext=(8, 0), fontsize=8, color="#b03a2e",
                      va="center")
    ax_c.set_ylabel("carbon  (wt %)")
    ax_c.set_ylim(0.0, profile.C_surface * 1.12)
    ax_c.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    ax_c.set_title("carbon diffuses in (erfc) → microstructure → hardness, all from one solver",
                   fontsize=10.5)

    # -- panel 2: microstructure gradient (stacked phase fractions) -------------- #
    order = ["martensite", "bainite", "pearlite", "ferrite", "retained_austenite"]
    bands = {
        "martensite": traverse.martensite, "bainite": traverse.bainite,
        "pearlite": traverse.pearlite,
        "ferrite": (traverse.ferrite if traverse.ferrite is not None else np.zeros_like(traverse.martensite)),
        "retained_austenite": traverse.retained_austenite,
    }
    ax_phase.stackplot(
        depth_mm, *[bands[p] for p in order],
        colors=[PHASE_COLORS[p] for p in order],
        labels=[PHASE_LABELS[p] for p in order],
    )
    ax_phase.set_ylabel("mass fraction")
    ax_phase.set_ylim(0.0, 1.0)
    ax_phase.legend(loc="lower right", fontsize=8, ncol=2, framealpha=0.9)

    # -- panel 3: hardness traverse (potential vs as-quenched) + published band -- #
    pot_hrc = traverse.HRC
    aq_hrc = vickers_to_rockwell_c_safe(traverse.HV_as_quenched)
    fp, fa = np.isfinite(pot_hrc), np.isfinite(aq_hrc)
    ax_h.plot(depth_mm[fp], pot_hrc[fp], "-o", color="#b03a2e", ms=3.5, lw=2.2,
              label="martensite potential (case as designed)")
    ax_h.plot(depth_mm[fa], aq_hrc[fa], "--", color="#7d3c98", lw=1.8,
              label="as-quenched (incl. retained γ)")
    lo, hi = surface_hardness_band
    ax_h.axhspan(lo, hi, color="0.7", alpha=0.35)
    ax_h.text(depth_mm[-1], 0.5 * (lo + hi), "published\nsurface band", ha="right",
              va="center", fontsize=7.5, color="0.35")
    ax_h.set_ylabel("hardness  (HRC)")
    ax_h.set_xlabel("depth from surface  (mm)")
    ax_h.set_ylim(RELIABLE_HRC_MIN, 68.0)
    ax_h.set_xlim(left=0.0)
    ax_h.grid(True, alpha=0.25)
    ax_h.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

    fig.suptitle(title, fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def vickers_to_rockwell_c_safe(HV: np.ndarray) -> np.ndarray:
    """HV→HRC for an array, returning ``nan`` off-scale (a thin wrapper over the E140 table)."""
    from .properties import vickers_to_rockwell_c
    return np.asarray(vickers_to_rockwell_c(np.asarray(HV, dtype=float)), dtype=float)


# Equilibrium-phase colours for the CALPHAD figure (distinct from the kinetic
# product palette above — these are equilibrium constituents, not transformation products).
EQ_PHASE_COLORS = {
    "ferrite": "#5b8bbf",        # α (BCC) — soft, low-C
    "austenite": "#e0a458",      # γ (FCC) — the high-T solvent
    "cementite": "#7d3c98",      # Fe₃C
    "carbide": "#2e8b57",        # alloy (Cr/Mo) carbides — what fe_c cannot represent
}
EQ_PHASE_LABELS = {
    "ferrite": "ferrite (α)", "austenite": "austenite (γ)",
    "cementite": "cementite (Fe₃C)", "carbide": "alloy carbide (M₇C₃/M₂₃C₆)",
}


def calphad_figure(binary: dict, alloy: dict | None = None) -> "plt.Figure":
    """The banked **Phase-4 artifact**: real thermodynamics vs the parametrised diagram.

    Two panels, both consuming plain arrays the demo computed upstream (ADR 0002):

      * **Left — "what the linear chord got wrong".** The hypoeutectoid A₃ transus:
        ``fe_c``'s straight chord (912 °C → eutectoid) vs the CALPHAD-computed *curved*
        boundary, with their gap shaded. The chord systematically over-predicts A₃ by
        tens of °C at mid-carbon — the quantified cost of the parametrisation.
      * **Right — the multicomponent reach (optional).** Equilibrium phase fractions vs
        temperature for a low-alloy steel (4140) — ferrite/austenite/cementite **plus a
        chromium carbide**, across a ferrite+austenite region spanning A₁→A₃. ``fe_c``
        has no representation for any of this; it is the "extend to low-alloy steels"
        payoff. Drawn only if ``alloy`` data is supplied (needs the steel database).

    ``binary`` keys: ``carbon`` (wt% array), ``a3_linear`` / ``a3_calphad`` (°C arrays),
    ``eutectoid``/``gamma_max`` (``(T, C)`` tuples — fe_c-pinned), ``eutectoid_calphad``/
    ``gamma_max_calphad`` (CALPHAD ``(T, C)``). ``alloy`` keys: ``label``, ``T`` (°C
    array), ``fractions`` (``{phase: array}``), ``A1``/``A3`` (°C), ``andrews`` (``(Ae1,
    Ae3)``).
    """
    ncols = 2 if alloy is not None else 1
    fig, axes = plt.subplots(1, ncols, figsize=(13 if alloy else 7, 6),
                             squeeze=False)
    ax_d = axes[0][0]

    # -- left panel: linear chord vs curved CALPHAD A₃ --------------------------- #
    carbon = np.asarray(binary["carbon"])
    a3_lin = np.asarray(binary["a3_linear"])
    a3_cal = np.asarray(binary["a3_calphad"])
    ax_d.fill_between(carbon, a3_cal, a3_lin, color="#d98880", alpha=0.35,
                      label="parametrisation error")
    ax_d.plot(carbon, a3_lin, "--", color="#b03a2e", lw=2.0,
              label="fe_c A₃ (linear chord)")
    ax_d.plot(carbon, a3_cal, "-", color="#1f4e79", lw=2.4,
              label="CALPHAD A₃ (computed)")
    # invariant points (fe_c-pinned filled, CALPHAD open) — the wiring smoke-test
    T_eu, C_eu = binary["eutectoid"]
    ax_d.plot([C_eu], [T_eu], "ks", ms=7, label="eutectoid (fe_c)")
    if "eutectoid_calphad" in binary:
        Tc, Cc = binary["eutectoid_calphad"]
        ax_d.plot([Cc], [Tc], "o", mfc="none", mec="k", mew=1.6, ms=9,
                  label="eutectoid (CALPHAD)")
    imax = int(np.argmax(a3_lin - a3_cal))
    ax_d.annotate(f"chord high by {a3_lin[imax] - a3_cal[imax]:.0f} °C",
                  (carbon[imax], 0.5 * (a3_lin[imax] + a3_cal[imax])),
                  textcoords="offset points", xytext=(12, 0), fontsize=9,
                  color="#7b241c", va="center")
    ax_d.set_xlabel("carbon  (wt %)")
    ax_d.set_ylabel("temperature  (°C)")
    ax_d.set_xlim(left=0.0)
    ax_d.grid(True, alpha=0.25)
    ax_d.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    ax_d.set_title("Fe-C A₃ transus: linear chord vs CALPHAD", fontsize=11)

    # -- right panel: 4140 equilibrium phase fractions vs T ---------------------- #
    if alloy is not None:
        ax_a = axes[0][1]
        T = np.asarray(alloy["T"])
        order = [p for p in ("ferrite", "austenite", "cementite", "carbide")
                 if p in alloy["fractions"]]
        ax_a.stackplot(T, *[np.asarray(alloy["fractions"][p]) for p in order],
                       colors=[EQ_PHASE_COLORS[p] for p in order],
                       labels=[EQ_PHASE_LABELS[p] for p in order])
        for boundary, name, col in ((alloy["A1"], "A₁", "#444"), (alloy["A3"], "A₃", "#444")):
            ax_a.axvline(boundary, color=col, ls=":", lw=1.2)
            ax_a.text(boundary, 1.02, f"{name}\n{boundary:.0f} °C", ha="center",
                      va="bottom", fontsize=8, color=col)
        Ae1, Ae3 = alloy["andrews"]
        ax_a.plot([Ae1, Ae3], [0.5, 0.5], "kv", ms=7,
                  label=f"Andrews Ae₁/Ae₃ ({Ae1:.0f}/{Ae3:.0f} °C)")
        ax_a.set_xlabel("temperature  (°C)")
        ax_a.set_ylabel("mass fraction")
        ax_a.set_ylim(0.0, 1.12)
        ax_a.set_xlim(T.min(), T.max())
        ax_a.legend(loc="center left", fontsize=8, framealpha=0.9)
        ax_a.set_title(f"{alloy['label']} equilibrium phases (CALPHAD) — fe_c cannot reach this",
                       fontsize=11)

    fig.suptitle("Phase 4: CALPHAD thermodynamics vs the parametrised Fe-C diagram",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def sweep_comparison_figure(
    grid: list[list],
    title: str = "Experimentation surface: composition × cooling rate (hardenability, side by side)",
) -> "plt.Figure":
    """The banked **experimentation-surface artifact**: the composition × cooling-rate grid.

    ``grid`` is the :func:`~steel.sweep.sweep_grid` output — ``grid[i][j]`` is steel
    ``i`` cooled in medium ``j`` (rows = steels, cols = media). This is the one genuinely-new
    view over the four-curves demo: it adds the **composition axis** a single-steel demo
    cannot show. Two panels (mechanism | consequence), like the four-curves figure:

      * **Left — hardenability as a curve.** Martensite fraction vs cooling rate ``Vr``
        (°C/h at 700 °C, log axis), one line per steel. In the 0-D model every steel sees the
        *same* cooling path at a given medium, so the lines share their x-values and stack by
        **hardenability**: the deep-hardening alloy keeps martensite down to far lower cooling
        rates (its curve sits high and to the left), while the lean steel needs a fast quench.
        The steels **converge at the fast end** (all martensitic) and **at the slow end** (all
        pearlitic) and **diverge in the middle** — the project's recurring lesson, here on the
        cooling-rate axis.
      * **Right — the property grid.** A hardness heat-map (HRC) over the same steels × media;
        cells off the HRC scale (soft ferrite-pearlite, < ~20 HRC) are marked "soft". The
        side-by-side comparison the plan (§9) asks for — read off "what material do I get".

    All numbers are computed upstream by :mod:`sweep` (ADR 0002: viz consumes validated
    arrays, never derives them). Outcomes carrying ``lumped_valid = False`` (a severe quench
    of a thick section, beyond the 0-D Biot range) are marked with a hollow ring on the left
    panel — the honest "this node is stretched; use the Phase-2 spatial solve" flag.
    """
    steels = [row[0].steel for row in grid]
    media = [o.medium for o in grid[0]]
    n_steel, n_media = len(steels), len(media)

    fig, (ax_curve, ax_heat) = plt.subplots(
        1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.3, 1.0]})

    # -- left: martensite fraction vs cooling rate, one line per steel -------------- #
    palette = ["#c0392b", "#7d3c98", "#2471a3", "#1e8449", "#e67e22"]
    for i, row in enumerate(grid):
        color = STEEL_COLORS.get(steels[i].label(), palette[i % len(palette)])
        Vr = np.array([o.Vr for o in row])
        fM = np.array([o.result.martensite for o in row])
        order = np.argsort(Vr)                              # draw slow → fast left → right
        ax_curve.plot(Vr[order], fM[order], "-o", color=color, lw=2.2, ms=6,
                      label=steels[i].label())
        # ring the nodes where the 0-D lumped model is stretched (Bi ≥ 0.1).
        for o in row:
            if not o.lumped_valid and np.isfinite(o.Vr):
                ax_curve.plot([o.Vr], [o.result.martensite], "o", mfc="none",
                              mec="0.25", mew=1.6, ms=12, zorder=5)
    ax_curve.set_xscale("log")
    ax_curve.set_xlabel("cooling rate at 700 °C   Vr  (°C/h)")
    ax_curve.set_ylabel("martensite fraction")
    ax_curve.set_ylim(-0.03, 1.05)
    ax_curve.grid(True, alpha=0.25, which="both")
    ax_curve.legend(loc="upper left", fontsize=9, framealpha=0.9, title="steel")
    ax_curve.set_title("hardenability: martensite vs cooling rate (○ = beyond 0-D Biot range)",
                       fontsize=10.5)

    # -- right: hardness grid (HRC heat-map, annotated; soft cells flagged) --------- #
    HRC = np.array([[o.HRC for o in row] for row in grid])
    HV = np.array([[o.HV for o in row] for row in grid])
    masked = np.ma.masked_invalid(HRC)
    cmap = plt.get_cmap("inferno").copy()
    cmap.set_bad("0.85")                                    # off-scale (soft) → light grey
    im = ax_heat.imshow(masked, cmap=cmap, aspect="auto", vmin=20.0, vmax=66.0,
                        origin="upper")
    for i in range(n_steel):
        for j in range(n_media):
            if np.isfinite(HRC[i, j]):
                txt, tcol = f"{HRC[i, j]:.0f}\nHRC", ("white" if HRC[i, j] < 48 else "black")
            else:
                txt, tcol = f"soft\n{HV[i, j]:.0f}HV", "0.25"
            ax_heat.text(j, i, txt, ha="center", va="center", fontsize=8.5,
                         color=tcol, fontweight="bold")
    ax_heat.set_xticks(range(n_media))
    ax_heat.set_xticklabels([str(m) for m in media])
    ax_heat.set_yticks(range(n_steel))
    ax_heat.set_yticklabels([s.label() for s in steels])
    ax_heat.set_xlabel("quench medium  (slow → fast)")
    ax_heat.set_ylabel("steel")
    fig.colorbar(im, ax=ax_heat, label="hardness (HRC)", fraction=0.046, pad=0.04)
    ax_heat.set_title("resulting hardness — the side-by-side comparison", fontsize=10.5)

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return fig


def design_figure(result, grid, title=None) -> "plt.Figure":
    """The banked **inverse-design artifact**: target a hardness, see the recipes that meet it.

    Two panels — the *landscape* and the *answer*:

      * **Left — the as-quenched feasibility map.** A hardness heat-map (HRC; soft cells <~20 HRC
        greyed) over grades (rows) × quench media (cols), the same grid the forward surface draws —
        but here each cell is judged against the **target band**. A cell already in band as-quenched
        gets a **solid** border; a martensitic cell that reaches the band only **after tempering**
        gets a **dashed** border with its tempered hardness noted; the **recommended** (cheapest)
        recipe is starred. Cells with no border are infeasible — the honest "this grade/quench can't
        be made to hit the spec."
      * **Right — the feasible recipes, cheapest first.** A cost-ranked bar (the recommendation at
        top), each annotated with its treatment and achieved hardness, coloured by whether the 0-D
        lumped model holds (a severe quench of a thick section is flagged ⚠, not hidden). The
        **cost ordering is a transparent convenience** (leaner alloy + milder quench + no extra
        temper step) — *not* a validated cost model (see :mod:`~steel.design`).

    ``result`` is a :class:`~steel.design.DesignResult`; ``grid`` is the matching
    :func:`~steel.sweep.sweep_grid` (rows = the same grades, cols = the same media, same diameter) —
    the as-quenched landscape the map colours. All numbers are computed upstream (ADR 0002: this
    layer draws validated arrays, never derives them).
    """
    lo, hi = result.target_band
    band_HRC = (_safe_hrc(lo), _safe_hrc(hi))               # the target band, on the HRC colorbar
    steels = [row[0].steel for row in grid]
    media = [o.medium for o in grid[0]]
    n_steel, n_media = len(steels), len(media)

    # Lookup: which (grade, medium) cells are feasible, and the recipe sitting on each.
    recipe_at = {(r.steel.label(), r.medium): r for r in result.recipes}
    rec = result.recommended

    fig, (ax_map, ax_rank) = plt.subplots(
        1, 2, figsize=(13.5, 6.0), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # -- left: the as-quenched hardness map, cells judged against the target band ---- #
    HRC = np.array([[o.HRC for o in row] for row in grid])
    HV = np.array([[o.HV for o in row] for row in grid])
    cmap = plt.get_cmap("inferno").copy()
    cmap.set_bad("0.85")
    im = ax_map.imshow(np.ma.masked_invalid(HRC), cmap=cmap, aspect="auto",
                       vmin=20.0, vmax=66.0, origin="upper")
    for i in range(n_steel):
        for j in range(n_media):
            key = (steels[i].label(), media[j])
            r = recipe_at.get(key)
            if np.isfinite(HRC[i, j]):
                base = f"{HRC[i, j]:.0f} HRC"
                tcol = "white" if HRC[i, j] < 48 else "black"
            else:
                base, tcol = f"soft\n{HV[i, j]:.0f}HV", "0.25"
            # Annotate feasible cells with how they get there (as-quenched vs +temper).
            if r is not None and r.tempered:
                base += f"\n→{r.HRC:.0f} (+temper)"
            ax_map.text(j, i, base, ha="center", va="center", fontsize=8.2,
                        color=tcol, fontweight="bold")
            if r is not None:
                # solid border = as-quenched-in-band; dashed = reaches band only via tempering.
                ls = "--" if r.tempered else "-"
                ax_map.add_patch(plt.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#1e8449",
                    lw=2.4, ls=ls, zorder=4))
    if rec is not None:
        ri = steels.index(next(s for s in steels if s.label() == rec.steel.label()))
        rj = media.index(rec.medium)
        # Park the star in the cell's top-left corner so it never collides with the annotation.
        ax_map.plot(rj - 0.34, ri - 0.32, marker="*", ms=18, mfc="#f1c40f", mec="black",
                    mew=1.2, zorder=6, clip_on=False)
    ax_map.set_xticks(range(n_media)); ax_map.set_xticklabels([str(m) for m in media])
    ax_map.set_yticks(range(n_steel)); ax_map.set_yticklabels([s.label() for s in steels])
    ax_map.set_xlabel("quench medium  (slow → fast)")
    ax_map.set_ylabel("steel")
    cb = fig.colorbar(im, ax=ax_map, label="as-quenched hardness (HRC)", fraction=0.046, pad=0.04)
    cb.ax.axhspan(band_HRC[0], band_HRC[1], color="#1e8449", alpha=0.35)   # the target band
    ax_map.set_title("feasibility map  (□ feasible, ┄ via temper, ★ recommended)", fontsize=10.5)

    # -- right: the feasible recipes, cost-ranked (the recommendation) -------------- #
    if not result.recipes:
        ax_rank.text(0.5, 0.5, "No feasible recipe in this design space\n"
                     "— target outside the achievable envelope.", ha="center", va="center",
                     fontsize=12, color="#b03a2e", transform=ax_rank.transAxes)
        ax_rank.axis("off")
    else:
        recipes = list(result.recipes)                       # already cost-sorted (cheapest first)
        y = np.arange(len(recipes))[::-1]                    # recommended at the TOP
        costs = [r.cost for r in recipes]
        colors = ["#1e8449" if r.lumped_valid else "#e67e22" for r in recipes]
        ax_rank.barh(y, costs, color=colors, edgecolor="0.2", height=0.62)
        for yi, r in zip(y, recipes):
            flag = "" if r.lumped_valid else "  ⚠ 0-D stretched"
            tag = "★ " if r is rec else ""
            ax_rank.text(0.02, yi, f"{tag}{r.label()}", va="center", ha="left", fontsize=8.6,
                         fontweight="bold" if r is rec else "normal")
            ax_rank.text(r.cost, yi, f"  {r.HRC:.0f} HRC{flag}", va="center", ha="left", fontsize=8.2)
        ax_rank.set_yticks([])
        ax_rank.set_xlim(0, max(costs) * 1.45)
        ax_rank.set_xlabel("relative cost  (leaner alloy + milder quench ⇒ lower — convenience, not validated)")
        ax_rank.set_title("feasible recipes, cheapest first  (green = 0-D valid, orange = stretched)",
                          fontsize=10.5)

    head = title or (f"Inverse design: reach {result.target_HV:.0f} ± {result.tol_HV:.0f} HV "
                     f"in a {result.diameter * 1000:.0f} mm section")
    if rec is not None:
        head += f"   →   recommend: {rec.label()}  ({rec.HRC:.0f} HRC)"
    fig.suptitle(head, fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def _safe_hrc(HV: float) -> float:
    """HV→HRC for the colorbar band marker — clamped to the scale floor so the band still draws."""
    from .properties import vickers_to_rockwell_c
    hrc = float(vickers_to_rockwell_c(HV))
    return hrc if np.isfinite(hrc) else RELIABLE_HRC_MIN


def four_curves_figure(
    ccurve: CCurve, paths: list[CoolingPath], results: list[TransformResult],
    hardness: list[tuple[float, float]] | None = None,
    title: str = "One steel (AISI 1080), four cooling rates: soft pearlite → very-hard martensite",
) -> "plt.Figure":
    """Assemble the Phase-1 **anchor artifact**: paths-on-TTT + microstructure bars.

    Left, the mechanism (cooling paths crossing the C-curve); right, the consequence
    (the microstructures and — Phase 3 — their **real** computed hardness, if ``hardness``
    is supplied as ``(HV, HRC)`` per path from :mod:`properties`). The two panels are the
    demo's whole thesis — same austenite, a spectrum of fates from soft pearlite to
    file-hard martensite, set by which side of the nose the cooling path falls. (Four
    cooling rates yield three distinct phase constitutions — furnace and air both give
    pearlite, differing only in formation temperature/coarseness; the title names the
    property span, which is the honest dramatic claim.)
    """
    fig, (ax_ttt, ax_bars) = plt.subplots(1, 2, figsize=(13, 6),
                                          gridspec_kw={"width_ratios": [1.6, 1.0]})
    plot_ttt(ax_ttt, ccurve)
    plot_cooling_paths(ax_ttt, paths, results)
    ax_ttt.set_title("cooling paths across the TTT C-curve", fontsize=11)

    plot_microstructure_bars(ax_bars, paths, results, hardness=hardness)
    ax_bars.set_title("resulting microstructure & hardness", fontsize=11)

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return fig


def single_steel_figure(
    ccurve: CCurve, path: CoolingPath, result: TransformResult, *,
    ttt_title: str | None = None, schematic_title: str | None = None, seed: int = 0,
) -> "plt.Figure":
    """One steel, one quench: the cooling path across the TTT (left) + a schematic
    microstructure swatch (right) — the **build-your-own composition** view's figure.

    Packaged here (the render layer) so the *free-composition* surfaces compose the same
    two-panel view from validated arrays rather than each hand-rolling it: the Streamlit
    app's :func:`~steel.app.custom_figure` wraps this (the app's discipline forbids
    inventing a figure in ``main()``), and ``steel.ipynb`` §3 draws the same left/right pair.
    Takes the chain **primitives** — ``ccurve`` (the alloy-shifted C-curve), the single
    cooling ``path`` and its ``result`` — *not* a :class:`~steel.sweep.Outcome`, so
    this module keeps its no-:mod:`sweep`-import boundary (it already depends only on
    kinetics/pathint/cooling/properties). ADR 0002: a figure is reach, never evidence.
    """
    fig, (ax_ttt, ax_micro) = plt.subplots(
        1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1.55, 1.0]})
    plot_ttt(ax_ttt, ccurve)
    plot_cooling_paths(ax_ttt, [path], [result])
    if ttt_title:
        ax_ttt.set_title(ttt_title, fontsize=10.5)
    microstructure_schematic(ax_micro, result.fractions(),
                             title=schematic_title or "microstructure at this quench", seed=seed)
    fig.subplots_adjust(left=0.06, right=0.97, bottom=0.20, wspace=0.22)
    return fig


# Stable colours for the two coupled grain-size properties (Phase 5c). Yield = strength axis,
# DBTT = toughness axis — opposite directions under grain refinement (the co-benefit).
YIELD_COLOR = "#1f4e79"          # deep blue — yield strength (rises as grain refines)
DBTT_COLOR = "#c0392b"           # red — DBTT (falls as grain refines; the co-benefit)


def grain_figure(
    fine: GrainProperties, coarse: GrainProperties, C: float, comp: dict, *,
    name: str = "", d_um_range: tuple[float, float] = (3.0, 120.0),
    T_range: tuple[float, float] = (850.0, 1250.0), t_hours: float = 1.0, n: int = 200,
) -> "plt.Figure":
    """The banked **Phase-5c artifact**: grain refinement, the lone strength-AND-toughness lever.

    Three panels telling the option-(b) story — yield and DBTT moving *opposite* ways under
    grain refinement (the famous exception to the strength↔toughness trade-off), made a model
    output rather than narrated. ``fine`` / ``coarse`` are the demo's two operating points (a cool
    vs a hot austenitize) as :class:`~steel.grain.GrainProperties`; ``C`` / ``comp`` the
    steel the smooth curves are sampled for.

      * **Left — the co-benefit, vs ``d^(−½)``.** Yield (left axis, ``↑``) and DBTT (right axis,
        ``↓``) sampled across ferrite grain size, plotted against ``d^(−½)`` (the Hall–Petch
        abscissa; finer grain → right). Both *improve* toward the right — the co-improvement, the
        whole point of option (b). The two operating points are marked.
      * **Middle — the lever comparison, in the (yield, DBTT) plane.** From the coarse-grain
        baseline, three ways to reach the *same* higher yield: **refine the grain** (down-right —
        yield up, DBTT *down*), or **add pearlite / add Si** (up-right — yield up, DBTT *up*). The
        grain arrow breaks the conventional strength–toughness front the solute/pearlite arrows
        trace; "the same strength two ways", with opposite toughness outcomes — the sign-opposition
        of the two Pickering laws, drawn.
      * **Right — the overheating penalty, vs austenitizing T.** The coupled yield (``↓``) and DBTT
        (``↑``) as the austenitizing temperature rises: a hotter hold coarsens the PAGS → coarsens
        the ferrite → costs *both* strength and toughness. The cautionary companion to the
        co-benefit.

    All curves are evaluations of the **validated** 5b/5c laws over plotting ranges (the
    ``plot_ttt`` idiom — the render layer samples a validated function, it does not invent
    physics; ADR 0002). The co-benefit / lever direction is **by construction** from the two
    cited Pickering signs — a demonstration, not a benchmark with teeth (those are 5a's holdout).
    """
    fp = fine.f_pearlite                                       # same steel ⇒ same equilibrium pearlite
    fig, (ax_co, ax_lever, ax_over) = plt.subplots(1, 3, figsize=(17, 5.4))

    # -- panel A: the co-benefit — yield ↑ & DBTT ↓ vs d^(−½) --------------------- #
    d = np.linspace(d_um_range[1], d_um_range[0], n)          # coarse → fine (left → right)
    inv_sqrt = (d / 1000.0) ** -0.5                            # mm^(−½), the Hall–Petch abscissa
    yld = np.array([grain.hall_petch_yield_MPa(di, comp=comp, f_pearlite=fp) for di in d])
    dbt = np.array([grain.cottrell_petch_dbtt_C(di, comp=comp, f_pearlite=fp) for di in d])

    ax_co.plot(inv_sqrt, yld, color=YIELD_COLOR, lw=2.4)
    ax_co.set_xlabel("ferrite grain size  d$^{-1/2}$  (mm$^{-1/2}$)   →  finer grain")
    ax_co.set_ylabel("yield strength  σ$_y$  (MPa)", color=YIELD_COLOR)
    ax_co.tick_params(axis="y", labelcolor=YIELD_COLOR)
    ax_T = ax_co.twinx()
    ax_T.plot(inv_sqrt, dbt, color=DBTT_COLOR, lw=2.4, ls="--")
    ax_T.set_ylabel("DBTT  (°C)", color=DBTT_COLOR)
    ax_T.tick_params(axis="y", labelcolor=DBTT_COLOR)
    ax_T.axhline(0.0, color="0.7", ls=":", lw=1.0)
    # the two operating points
    for g, tag in ((coarse, "coarse"), (fine, "fine")):
        xi = (g.ferrite_um / 1000.0) ** -0.5
        ax_co.plot([xi], [g.yield_MPa], "o", color=YIELD_COLOR, ms=7, zorder=5)
        ax_T.plot([xi], [g.dbtt_C], "s", color=DBTT_COLOR, ms=7, zorder=5)
        ax_co.annotate(f"{tag}\n{g.ferrite_um:.0f} µm", (xi, g.yield_MPa),
                       textcoords="offset points", xytext=(0, 9), ha="center",
                       fontsize=8, color="0.25")
    ax_co.set_title("grain refinement raises σ$_y$ AND lowers DBTT (the co-benefit)", fontsize=10.5)

    # -- panel B: the lever comparison in the (yield, DBTT) plane ----------------- #
    # From the coarse baseline, raise yield by Δσ three ways and read where DBTT lands. Yield is
    # linear in f_pearlite and in Si, so the matching increments are closed-form (grain constants).
    d_sigma = fine.yield_MPa - coarse.yield_MPa
    y0, T0 = coarse.yield_MPa, coarse.dbtt_C
    # endpoints, all at yield = fine.yield_MPa:
    grain_pt = (fine.yield_MPa, fine.dbtt_C)                                    # refine grain
    pearl_dT = (grain.ITT_K_PEARLITE / grain.YIELD_K_PEARLITE) * d_sigma        # add pearlite
    si_dT = (grain.ITT_K_SI / grain.YIELD_K_SI) * d_sigma                       # add Si
    pearl_pt = (fine.yield_MPa, T0 + pearl_dT)
    si_pt = (fine.yield_MPa, T0 + si_dT)

    ax_lever.plot([y0], [T0], "ko", ms=8, zorder=6)
    ax_lever.annotate("coarse-grain\nbaseline", (y0, T0), textcoords="offset points",
                      xytext=(-10, 8), ha="right", fontsize=8.5, color="0.2")
    arrows = [
        (grain_pt, DBTT_COLOR, "refine grain", "tougher (DBTT ↓)"),
        (pearl_pt, "#e67e22", "add pearlite", "brittle (DBTT ↑)"),
        (si_pt, "#8e44ad", "add Si", "brittle (DBTT ↑)"),
    ]
    for (yp, Tp), col, lab, sub in arrows:
        ax_lever.annotate("", xy=(yp, Tp), xytext=(y0, T0),
                          arrowprops=dict(arrowstyle="-|>", color=col, lw=2.2))
        ax_lever.plot([yp], [Tp], "o", color=col, ms=7, zorder=6)
        ax_lever.annotate(f"{lab}\n{sub}", (yp, Tp), textcoords="offset points",
                          xytext=(8, 0), va="center", fontsize=8.2, color=col)
    # Headroom so the right-hand arrow labels (at the target yield) are not clipped.
    span = max(fine.yield_MPa - y0, 1.0)
    ax_lever.set_xlim(y0 - 0.10 * span, fine.yield_MPa + 0.65 * span)
    ax_lever.axvline(fine.yield_MPa, color="0.8", ls=":", lw=1.2)
    ax_lever.text(fine.yield_MPa, ax_lever.get_ylim()[1], "same yield,\nthree ways",
                  ha="center", va="top", fontsize=8, color="0.45")
    ax_lever.axhline(0.0, color="0.7", ls=":", lw=1.0)
    ax_lever.set_xlabel("yield strength  σ$_y$  (MPa)")
    ax_lever.set_ylabel("DBTT  (°C)")
    ax_lever.set_title("same strength, three levers — only grain refinement also toughens",
                       fontsize=10.5)
    ax_lever.grid(True, alpha=0.2)

    # -- panel C: the overheating penalty — both worse as austenitizing T rises --- #
    Ts = np.linspace(T_range[0], T_range[1], n)
    gps = [grain.coupled_grain_properties(float(t), t_hours, C, comp=comp) for t in Ts]
    yld_o = np.array([g.yield_MPa for g in gps])
    dbt_o = np.array([g.dbtt_C for g in gps])

    ax_over.plot(Ts, yld_o, color=YIELD_COLOR, lw=2.4)
    ax_over.set_xlabel(f"austenitizing temperature  (°C, {t_hours:.0f} h hold)   →  hotter")
    ax_over.set_ylabel("yield strength  σ$_y$  (MPa)", color=YIELD_COLOR)
    ax_over.tick_params(axis="y", labelcolor=YIELD_COLOR)
    ax_o2 = ax_over.twinx()
    ax_o2.plot(Ts, dbt_o, color=DBTT_COLOR, lw=2.4, ls="--")
    ax_o2.set_ylabel("DBTT  (°C)", color=DBTT_COLOR)
    ax_o2.tick_params(axis="y", labelcolor=DBTT_COLOR)
    ax_o2.axhline(0.0, color="0.7", ls=":", lw=1.0)
    for g, tag in ((fine, "cool"), (coarse, "hot / over-austenitized")):
        ax_over.plot([g.austenitizing_T], [g.yield_MPa], "o", color=YIELD_COLOR, ms=7, zorder=5)
        ax_o2.plot([g.austenitizing_T], [g.dbtt_C], "s", color=DBTT_COLOR, ms=7, zorder=5)
    ax_over.set_title("over-austenitizing coarsens the grain → σ$_y$ ↓ and DBTT ↑ (both worse)",
                      fontsize=10.5)

    label = f"{name}  " if name else ""
    fig.suptitle(
        f"Phase 5c — {label}grain refinement: the lone strength-AND-toughness lever "
        f"(σ$_y$ ↑ with DBTT ↓)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# Colours for the two grain sizes in the kinetics panel — austenite parent vs ferrite product.
PAGS_COLOR = "#c79a3a"           # amber — prior-austenite grain (the coarser parent)
FERRITE_COLOR = "#3a7d5d"        # green — ferrite grain (the product the 5b laws act on)


def grain_interactive_figure(
    gp: GrainProperties, C: float, comp: dict, *,
    name: str = "", t_hours: float = 1.0, T_range: tuple[float, float] = (850.0, 1250.0),
    room_T: float = grain.ROOM_TEMPERATURE_C, n: int = 160,
) -> "plt.Figure":
    """The **interactive single-state** Phase-5 view — one austenitizing hold, the whole chain.

    The slider-driven companion to the banked :func:`grain_figure` (which contrasts a fixed
    fine/coarse pair). Here a *single* operating point — ``gp``, the
    :class:`~steel.grain.GrainProperties` for the **current** austenitizing (T, t) — is
    marked on two curves swept over austenitizing temperature, so dragging the temperature slides
    the marker and tells the **over-austenitizing** story live: a hotter hold coarsens the grain,
    which lowers yield *and* raises DBTT (both worse). The two panels show *different* quantities:

      * **Left — the grain grows (Phase 5a kinetics).** Prior-austenite grain (PAGS) and the
        seeded ferrite grain vs austenitizing T (for the current hold ``t_hours``) — the genuinely
        new length scale the hardness chain never carried, annotated with the ferrite ASTM E112
        grain-size number ``G`` at the current hold.
      * **Right — the property payoff (Phase 5b/5c).** Yield (``↑``, left axis) and DBTT (``↓``,
        right axis) vs austenitizing T, with the **room-temperature** service reference drawn:
        where the DBTT curve crosses it is the ductile→brittle line. The current hold is marked
        on both axes.

    All curves evaluate the **validated** 5a/5b/5c laws over a plotting range (the ``plot_ttt``
    sample-a-validated-function idiom; ADR 0002 — a figure is reach, never evidence). The
    over-austenitizing direction, like the co-benefit, follows **by construction** from the two
    cited Pickering signs — a demonstration; Phase 5's only falsifiable teeth are 5a's
    grain-growth holdout. ``C`` / ``comp`` are the steel the curves are sampled for; ``gp`` must
    be the coupled result for that same steel and hold.
    """
    Ts = np.linspace(T_range[0], T_range[1], n)
    gps = [grain.coupled_grain_properties(float(t), t_hours, C, comp=comp) for t in Ts]
    pags = np.array([g.pags_um for g in gps])
    ferr = np.array([g.ferrite_um for g in gps])
    yld = np.array([g.yield_MPa for g in gps])
    dbt = np.array([g.dbtt_C for g in gps])
    T_now = gp.austenitizing_T

    fig, (ax_grain, ax_prop) = plt.subplots(1, 2, figsize=(14, 5.4))

    # -- left: grain growth (5a kinetics) — the new length scale ------------------ #
    ax_grain.plot(Ts, pags, color=PAGS_COLOR, lw=2.4, label="prior-austenite grain (PAGS)")
    ax_grain.plot(Ts, ferr, color=FERRITE_COLOR, lw=2.4,
                  label="ferrite grain  d$_\\alpha$  (the 5b input)")
    ax_grain.axvline(T_now, color="0.6", ls=":", lw=1.2)
    ax_grain.plot([T_now], [gp.pags_um], "o", color=PAGS_COLOR, ms=8, zorder=5)
    ax_grain.plot([T_now], [gp.ferrite_um], "o", color=FERRITE_COLOR, ms=8, zorder=5)
    G_ferrite = grain.astm_grain_size_number(gp.ferrite_um)
    ax_grain.annotate(f"{gp.ferrite_um:.0f} µm\nASTM G {G_ferrite:.1f}", (T_now, gp.ferrite_um),
                      textcoords="offset points", xytext=(9, -3), fontsize=9, color=FERRITE_COLOR)
    ax_grain.set_xlabel(f"austenitizing temperature  (°C, {t_hours:g} h hold)   →  hotter")
    ax_grain.set_ylabel("grain size  (µm)")
    ax_grain.set_title("the hold grows the grain (5a) — hotter ⇒ coarser", fontsize=10.5)
    ax_grain.legend(loc="upper left", fontsize=9, frameon=False)
    ax_grain.grid(True, alpha=0.2)

    # -- right: yield ↑ / DBTT ↓ vs T, with the room-temperature service line ------ #
    ax_prop.plot(Ts, yld, color=YIELD_COLOR, lw=2.4)
    ax_prop.axvline(T_now, color="0.6", ls=":", lw=1.2)
    ax_prop.plot([T_now], [gp.yield_MPa], "o", color=YIELD_COLOR, ms=8, zorder=5)
    ax_prop.set_xlabel(f"austenitizing temperature  (°C, {t_hours:g} h hold)   →  hotter")
    ax_prop.set_ylabel("yield strength  σ$_y$  (MPa)", color=YIELD_COLOR)
    ax_prop.tick_params(axis="y", labelcolor=YIELD_COLOR)
    ax_T = ax_prop.twinx()
    ax_T.plot(Ts, dbt, color=DBTT_COLOR, lw=2.4, ls="--")
    ax_T.plot([T_now], [gp.dbtt_C], "s", color=DBTT_COLOR, ms=8, zorder=5)
    ax_T.set_ylabel("DBTT  (°C)", color=DBTT_COLOR)
    ax_T.tick_params(axis="y", labelcolor=DBTT_COLOR)
    ax_T.axhline(room_T, color="0.45", ls="-.", lw=1.2)
    ax_T.annotate("room temperature", (Ts[0], room_T), textcoords="offset points",
                  xytext=(4, 4), fontsize=8.5, color="0.35")
    verdict = "BRITTLE at room T" if gp.dbtt_C > room_T else "ductile at room T"
    ax_T.annotate(f"{gp.dbtt_C:.0f} °C\n{verdict}", (T_now, gp.dbtt_C),
                  textcoords="offset points", xytext=(9, -3), fontsize=9, color=DBTT_COLOR)
    ax_prop.set_title("over-austenitizing: σ$_y$ ↓ and DBTT ↑ (both worse)", fontsize=10.5)

    label = f"{name}  " if name else ""
    fig.suptitle(
        f"Phase 5 — {label}grain refinement is the lone strength-AND-toughness lever "
        f"(refine ⇒ σ$_y$ ↑ and DBTT ↓)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# --------------------------------------------------------------------------- #
# 4b. Grain morphology — the size-accurate Voronoi swatch (the deferred grain viz)
# --------------------------------------------------------------------------- #
# A spatial *illustration* of grain.py's scalar grain size d (µm). It is reach, not physics
# (ADR 0002): the ONE faithful quantity is the grain NUMBER DENSITY. grain.py defines
# N_A = 1/d² grains per area (astm_grain_size_number), so a square field of side W holds
# N = (W/d)² grains, and a Voronoi tessellation of N random seeds has mean cell area W²/N = d².
# Finer grain (smaller d) ⇒ more cells in the SAME field of view — the size-accurate story.
# Everything else (the individual cell shapes, the absence of a size distribution / annealing
# twins / crystallographic texture) is decorative. This sits exactly where the
# microstructure_schematic cartoon sits (areas faithful, shapes illustrative) — it does NOT
# replace that swatch (which shows phase fractions); it adds the grain-size length scale the
# schematic explicitly disclaims.
GRAIN_SWATCH_FILL = FERRITE_COLOR        # ferrite grains — the structure the 5b laws act on
_GRAIN_SWATCH_MAX_CELLS = 1500           # safety cap (never hit across grain.py's size range)


def _nice_round(x: float) -> float:
    """Round ``x`` to a 1/2/5 × 10ⁿ "nice" number — for a legible scale-bar length."""
    if x <= 0.0:
        return 1.0
    exp = math.floor(math.log10(x))
    base = x / 10.0 ** exp
    nice = 1.0 if base < 1.5 else 2.0 if base < 3.5 else 5.0 if base < 7.5 else 10.0
    return nice * 10.0 ** exp


def grain_swatch_window_um(d_coarsest_um: float, *, target_coarse_cells: float = 9.0) -> float:
    """Side (µm) of a square field showing ``target_coarse_cells`` grains at ``d_coarsest_um``.

    From the number-density identity ``N = (W/d)²`` (grain.py's ``N_A = 1/d²``): to show ``N``
    grains at the *coarsest* grain a caller will draw, the window side is ``W = √N · d_coarsest``.
    Sizing the window from the **coarsest** grain (then reusing it for finer ones, which simply
    pack in more cells) is what makes a fine/coarse pair — or a slider — read as the *same field
    of view*, so refinement shows up as more grains rather than a relabelled scale bar. ~6–9
    coarse cells keeps the coarse swatch legible.
    """
    if d_coarsest_um <= 0.0:
        raise ValueError(f"grain size must be > 0 µm, got {d_coarsest_um}")
    if target_coarse_cells <= 0.0:
        raise ValueError(f"target cell count must be > 0, got {target_coarse_cells}")
    return math.sqrt(target_coarse_cells) * d_coarsest_um


def grain_cell_count(d_um: float, window_um: float) -> int:
    """Number of grains in a ``window_um``-side field at mean grain size ``d_um`` — ``(W/d)²``.

    The size-accurate count (grain.py's ``N_A = 1/d²`` × field area ``W²``), clamped to
    ``[1, _GRAIN_SWATCH_MAX_CELLS]`` so a pathologically fine grain cannot ask for an unbounded
    tessellation. Pure arithmetic (no draw), so the size-accuracy claim is testable headlessly.
    """
    if d_um <= 0.0:
        raise ValueError(f"grain size must be > 0 µm, got {d_um}")
    if window_um <= 0.0:
        raise ValueError(f"window must be > 0 µm, got {window_um}")
    return int(min(_GRAIN_SWATCH_MAX_CELLS, max(1, round((window_um / d_um) ** 2))))


def _bounded_voronoi_cells(points: np.ndarray, window_um: float) -> list:
    """Voronoi polygons for ``points`` in ``[0, W]²``, each clipped finite by mirror padding.

    The standard trick: reflect the seed set across all four edges and four corners (8 images),
    so every *original* seed is fully surrounded and its Voronoi cell is finite and lies inside
    the window. Returns one ``(k, 2)`` vertex array per original seed whose cell is bounded (any
    degenerate cell is skipped). scipy.spatial is a core dependency — the engine's
    ``solve_banded`` lives in scipy too.
    """
    from scipy.spatial import Voronoi

    pts = np.asarray(points, dtype=float)
    n = len(pts)
    images = [pts]
    for mx in (0.0, window_um, None):                 # reflect across x=0, x=W, or not at all
        for my in (0.0, window_um, None):             # …and y=0, y=W, or not at all
            if mx is None and my is None:
                continue                              # the identity copy is already in `images`
            rx = pts[:, 0] if mx is None else 2.0 * mx - pts[:, 0]
            ry = pts[:, 1] if my is None else 2.0 * my - pts[:, 1]
            images.append(np.column_stack([rx, ry]))
    vor = Voronoi(np.vstack(images))
    cells = []
    for i in range(n):
        region = vor.regions[vor.point_region[i]]
        if region and -1 not in region:
            cells.append(vor.vertices[region])
    return cells


def grain_voronoi_swatch(
    ax: "plt.Axes", d_um: float, *, window_um: float | None = None, seed: int = 0,
    fill: str = GRAIN_SWATCH_FILL, title: str | None = None,
    scale_bar: bool = True, caption: bool = True,
) -> "plt.Axes":
    """A size-accurate **Voronoi grain swatch** for the scalar grain size ``d_um`` (µm).

    Draws ``(window/d)²`` equiaxed Voronoi cells in a ``window_um``-side field — so a finer grain
    packs visibly more grains into the same field of view. The one faithful quantity is the
    **number density** (grain.py's ``N_A = 1/d²`` — :func:`grain_cell_count`); the cell shapes and
    the absence of a size distribution / annealing twins / crystallographic texture are decorative.
    When ``window_um`` is ``None`` the field auto-sizes to ~36 grains (a stand-alone snapshot whose
    absolute size is carried by the scale bar); pass an explicit ``window_um`` (e.g. from
    :func:`grain_swatch_window_um`) to compare several grain sizes in **one** common field — the
    size-accurate use. Deterministic for a given ``seed``. This is the deferred grain-*morphology*
    view; it complements, and does not replace, :func:`microstructure_schematic` (which shows phase
    *fractions*, not grain size). ADR 0002: reach, never evidence.
    """
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Rectangle

    if d_um <= 0.0:
        raise ValueError(f"grain size must be > 0 µm, got {d_um}")
    if window_um is None:
        window_um = grain_swatch_window_um(d_um, target_coarse_cells=36.0)
    n = grain_cell_count(d_um, window_um)
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0.0, window_um, size=(n, 2))
    cells = _bounded_voronoi_cells(pts, window_um)

    # Pale, lightly-varied fills + thin dark boundaries — the etched-micrograph look.
    pale = 0.45 * np.array(to_rgb(fill)) + 0.55
    shades = rng.uniform(0.86, 1.0, size=(len(cells), 1))
    facecolors = np.clip(pale[None, :] * shades, 0.0, 1.0)
    ax.add_collection(PolyCollection(cells, facecolors=facecolors,
                                     edgecolors="#2b2b2b", linewidths=0.6))

    ax.set_xlim(0, window_um); ax.set_ylim(0, window_um); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])

    if scale_bar:
        L = _nice_round(window_um / 4.0)
        x0, y0 = window_um * 0.06, window_um * 0.05
        pad = window_um * 0.02
        ax.add_patch(Rectangle((x0 - pad, y0 - pad), L + 2 * pad, window_um * 0.115,
                               facecolor="white", alpha=0.78, edgecolor="none", zorder=5))
        ax.plot([x0, x0 + L], [y0 + window_um * 0.012, y0 + window_um * 0.012],
                color="black", lw=3.0, solid_capstyle="butt", zorder=6)
        ax.text(x0 + L / 2.0, y0 + window_um * 0.038, f"{L:g} µm",
                ha="center", va="bottom", fontsize=8, zorder=6)

    G = grain.astm_grain_size_number(d_um)
    readout = f"d = {d_um:.0f} µm   ·   ASTM G {G:.1f}   ·   {n} grains"
    ax.set_title(f"{title}\n{readout}" if title else readout, fontsize=10.5)
    if caption:
        ax.text(0.5, -0.06,
                "idealized equiaxed Voronoi — grains/area ∝ ASTM Nₐ(d); shapes & size-spread "
                "decorative (not a micrograph)",
                transform=ax.transAxes, ha="center", va="top", fontsize=6.8, color="0.45")
    return ax


def grain_swatch_figure(
    d_um: float, *, window_um: float | None = None, name: str = "", seed: int = 0,
    title: str | None = None,
) -> "plt.Figure":
    """A single-axes Voronoi grain swatch *figure* — the app's grain-section view.

    Wraps :func:`grain_voronoi_swatch` with its own figure so the app (and any single-state caller)
    gets a ready figure — the render layer owns the figure (ADR 0002). Pass a fixed ``window_um``
    so a sequence of grain sizes (e.g. an austenitize slider) shares one field of view and
    refinement reads as *more grains*, not a relabelled scale bar.
    """
    fig, ax = plt.subplots(figsize=(5.8, 6.2))
    head = title if title is not None else (
        f"{name} — ferrite grain at this hold" if name else "ferrite grain at this hold")
    grain_voronoi_swatch(ax, d_um, window_um=window_um, seed=seed, title=head)
    fig.tight_layout()
    return fig


def grain_morphology_figure(
    fine: GrainProperties, coarse: GrainProperties, *, name: str = "", seed: int = 0,
    window_um: float | None = None,
) -> "plt.Figure":
    """The banked grain-**morphology** artifact: two grain sizes in ONE common field of view.

    The size-accurate companion to :func:`grain_figure` (which plots the yield/DBTT payoff): a fine
    vs a coarse ferrite grain (a cool vs a hot austenitize — the demo's two operating points) drawn
    as Voronoi swatches at a **shared** window, so the over-austenitized grain reads as a handful of
    large grains while the normalized one is a fine mosaic in the *same* area. The window is sized
    from the coarse grain (:func:`grain_swatch_window_um`, ~9 coarse cells); the fine swatch then
    shows ``(d_coarse/d_fine)²`` times as many. Reach, not evidence (ADR 0002) — the faithful
    quantity is the grain count per area; see :func:`grain_voronoi_swatch`.
    """
    if window_um is None:
        window_um = grain_swatch_window_um(coarse.ferrite_um, target_coarse_cells=9.0)
    fig, (ax_f, ax_c) = plt.subplots(1, 2, figsize=(12.4, 6.4))
    grain_voronoi_swatch(ax_f, fine.ferrite_um, window_um=window_um, seed=seed,
                         title=f"fine grain — {fine.austenitizing_T:.0f} °C austenitize")
    grain_voronoi_swatch(ax_c, coarse.ferrite_um, window_um=window_um, seed=seed + 1,
                         title=f"coarse grain — {coarse.austenitizing_T:.0f} °C (over-austenitized)")
    label = f"{name}  " if name else ""
    fig.suptitle(
        f"{label}grain morphology — same {window_um:.0f} µm field: over-austenitizing "
        f"coarsens the grain (fewer, larger grains)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    return fig


def ideal_diameter_figure(d):
    """The Phase-6c artifact: the critical-diameter (D_c) / measured-Jominy cross-check.

    ``d`` is a :class:`~steel.demo_ideal_diameter.IdealDiameterDemo` (already-validated
    arrays — this layer only draws them, ADR 0002). ``D_c`` is the water-quench centre-equivalent
    critical diameter (a lower bound on the ideal ``D_I``). Two panels:

    * **left — D_c, model vs measured, per grade:** each grade's measured ``D_c`` band is a bar
      (open arrow where the deepest heats run off the standard bar); the model's ``D_c`` (from
      ``fM = 0.5``) is a diamond. The read, in order: the **ranking is correct** (grades sorted by
      hardenability); **4340 under-predicted** (diamond at/below the band's low edge, band off-scale
      above); shallow grades **ride high**. 4140 (the calibration anchor) sits in its wide band *by
      construction* — coloured apart, not teeth.
    * **right — the Jominy curves behind it:** model HRC(J) over the measured band envelopes, with
      the cited 50 %-martensite hardness (where ``D_c`` is read) dashed per grade — the threshold/
      conversion-free corroboration; the near-end hardness-map fold shows on the alloy steels.
    """
    import matplotlib.pyplot as plt
    from .ideal_diameter import BENCHMARK_STEELS, JOMINY_STEP_MM, DC_MAX_MM

    # Role palette: the anchor (calibration) set apart from the teeth and the documented edge.
    ROLE_COLOR = {"anchor": "#9aa0a6", "teeth": PHASE_COLORS["bainite"], "edge": PHASE_COLORS["pearlite"]}
    GRADE_COLOR = {"1045": PHASE_COLORS["pearlite"], "8620": "#2e8b57",
                   "4140": PHASE_COLORS["martensite"], "4340": "#6c3fb5"}

    fig, (ax_di, ax_j) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    order = d.order

    # --- left: D_I bars (measured band) + model markers, by hardenability ---------- #
    x_right = DC_MAX_MM * 1.12                        # plot edge a touch past the standard-bar limit
    for i, name in enumerate(order):
        cc = d.checks[name]
        me, m = cc.measured, cc.model
        lo = me.Dc_min_mm
        hi = x_right if me.upper_off_scale else me.Dc_max_mm
        color = ROLE_COLOR[cc.role]
        ax_di.barh(i, hi - lo, left=lo, height=0.46, color=color, alpha=0.30,
                   edgecolor=color, linewidth=1.3)
        if me.upper_off_scale:                        # arrow: deepest heats run off the standard bar
            ax_di.annotate("", (x_right, i), (hi - 6, i),
                           arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6))
        mdi = x_right if not np.isfinite(m.Dc_mm) else m.Dc_mm
        ax_di.plot(mdi, i, "D", ms=11, color=color, mec="0.15", mew=1.0, zorder=5)
        ax_di.annotate(f"  model {m.Dc_mm:.0f} mm — {cc.verdict}" if np.isfinite(m.Dc_mm)
                       else "  model off-scale", (mdi, i), textcoords="offset points",
                       xytext=(6, 9), fontsize=8.0, color="0.2")
    ax_di.axvline(DC_MAX_MM, color="0.5", ls=":", lw=1.2)
    ax_di.annotate("standard bar limit\n(EMJ p.29 J32 ≈ 142 mm)", (DC_MAX_MM, len(order) - 0.5),
                   textcoords="offset points", xytext=(-6, -2), ha="right", va="top",
                   fontsize=7.6, color="0.4")
    ax_di.set_yticks(range(len(order)))
    ax_di.set_yticklabels([f"{n}\n({d.checks[n].role})" for n in order])
    ax_di.set_ylim(-0.6, len(order) - 0.4)
    ax_di.set_xlim(0, x_right)
    ax_di.set_xlabel("critical diameter  D_c  (mm, water-quench centre-equivalent; ≤ ideal D_I)")
    ax_di.set_title("D_c: model (fM=0.5) vs measured band — ranking correct, 4340 under-predicted",
                    fontsize=10.0)

    # --- right: the model Jominy HRC(J) curves over the measured band envelopes ----- #
    for name in order:
        cc = d.checks[name]
        steel = BENCHMARK_STEELS[name]
        col = GRADE_COLOR[name]
        jb, hmin, hmax = steel._band_arrays()
        ax_j.fill_between(jb, hmin, hmax, color=col, alpha=0.14, lw=0)         # measured band
        jh = cc.model.jominy
        j16 = jh.distance / (JOMINY_STEP_MM * 1e-3)
        good = np.isfinite(jh.HRC)
        ax_j.plot(j16[good], jh.HRC[good], color=col, lw=2.0, label=f"{name} model")
        ax_j.axhline(cc.measured.h50_HRC, color=col, ls=":", lw=1.0, alpha=0.6)
    ax_j.set_xlim(0, 32)
    ax_j.set_ylim(18, 62)
    ax_j.set_xlabel("Jominy distance from quenched end  (1/16 in)")
    ax_j.set_ylabel("hardness  (HRC)")
    ax_j.set_title("model HRC(J) over measured bands; dotted = cited 50 %-martensite hardness",
                   fontsize=10.0)
    ax_j.legend(loc="upper right", fontsize=8.0, framealpha=0.9)

    fig.suptitle(
        "Phase 6c — the critical-diameter (D_c) / measured-Jominy cross-check: absolute hardenability "
        "depth, vs data the model never saw (benchmark MEASURED, not Grossmann-computed)",
        fontsize=12.0, fontweight="bold",
    )
    fig.subplots_adjust(left=0.075, right=0.985, top=0.88, bottom=0.11, wspace=0.20)
    return fig


def bainite_figure(d):
    """The Phase-6b artifact: the bainite bay's **mechanism** (the teeth) and the cited C-curve.

    ``d`` is a :class:`~steel.demo_bainite.BainiteDemo` (already-validated arrays — this
    layer only draws them, ADR 0002). Two panels:

    * **left — the coefficient bay (scale-free, cited):** as Cr is added, the reconstructive ferrite
      reaction (``FC``) is retarded steeply while the displacive bainite reaction (``BC``) is retarded
      gently. The gap between the two curves *is* the bay's cause — purely the published Li/KV
      coefficients, the §4 fix at the mechanism level.
    * **right — the 4140 pearlite + bainite TTT start curves:** the bainite reaction is real and has
      its own nose below ``Bs``, but the two noses sit close in absolute time (no bay gap a continuous
      cool could exploit). The time axis is **unanchored** (a demonstration scale — named, not
      validated); the validated content is the coefficient ratio on the left, not the nose position.
    """
    import matplotlib.pyplot as plt

    fig, (ax_c, ax_ttt) = plt.subplots(1, 2, figsize=(12.5, 5.4))

    # --- left: the coefficient bay (the teeth) ------------------------------- #
    # A darker tan than the pale ferrite *phase* swatch — a thin line needs the contrast.
    ax_c.plot(d.cr, d.ferrite_retardation, color="#c8941f", lw=2.6,
              label="ferrite  FC  (reconstructive)")
    ax_c.plot(d.cr, d.bainite_retardation, color=PHASE_COLORS["bainite"], lw=2.6,
              label="bainite  BC  (displacive)")
    ax_c.fill_between(d.cr, d.bainite_retardation, d.ferrite_retardation,
                      color="0.85", alpha=0.6, zorder=0)
    ax_c.set_yscale("log")
    ax_c.set_xlim(d.cr[0], d.cr[-1])
    ax_c.set_xlabel("chromium added  (wt %)")
    ax_c.set_ylabel("reaction slowed  (× vs plain 0.40 %C)")
    ax_c.set_title("the bay's cause: alloy retards bainite far less than ferrite", fontsize=10.5)
    ax_c.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax_c.annotate("the gap IS the bay\n(cited coefficients,\nno calibration)",
                  (d.cr[-1], np.sqrt(d.bainite_retardation[-1] * d.ferrite_retardation[-1])),
                  textcoords="offset points", xytext=(-12, -6), ha="right", fontsize=8.5, color="0.3")

    # --- right: the 4140 pearlite + bainite TTT start curves ----------------- #
    keep_p = np.isfinite(d.pearlite_tau) & (d.pearlite_tau < 1e8)
    keep_b = np.isfinite(d.bainite_tau)
    ax_ttt.plot(d.pearlite_tau[keep_p], d.temps[keep_p], color=PHASE_COLORS["pearlite"], lw=2.4,
                label="pearlite start (project curve)")
    ax_ttt.plot(d.bainite_tau[keep_b], d.temps[keep_b], color=PHASE_COLORS["bainite"], lw=2.4,
                label="bainite start (cited Li/KV)")
    for nose, col in ((d.pearlite_nose, PHASE_COLORS["pearlite"]), (d.bainite_nose, PHASE_COLORS["bainite"])):
        ax_ttt.plot([nose[1]], [nose[0]], "o", color=col, ms=6, mec="0.2")
    ax_ttt.axhline(d.bs_4140, color=PHASE_COLORS["bainite"], ls=":", lw=1.3)
    ax_ttt.text(ax_ttt.get_xlim()[0], d.bs_4140 + 5, "  Bₛ (Steven–Haynes)", va="bottom", ha="left",
                color=PHASE_COLORS["bainite"], fontsize=8.5)
    ax_ttt.set_xscale("log")
    ax_ttt.set_xlabel("time  (s)")
    ax_ttt.set_ylabel("temperature  (°C)")
    ax_ttt.set_title("4140: the bainite reaction is real, but its nose sits near pearlite's", fontsize=10.5)
    ax_ttt.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax_ttt.annotate("absolute time scale unanchored\n(a demonstration parameter — §6)",
                    (0.5, 0.02), xycoords="axes fraction", ha="center", va="bottom",
                    fontsize=8, color="0.4", style="italic")

    fig.suptitle(
        "Phase 6b — the cited bainite reaction & the bay's mechanism "
        "(the bay itself is not realised in continuous cooling — see §6)",
        fontsize=12.5, fontweight="bold",
    )
    # Explicit margins (not tight_layout): the two log panels + long y-label otherwise trip
    # matplotlib's auto-layout into a spurious "axes too small" warning.
    fig.subplots_adjust(left=0.075, right=0.975, top=0.88, bottom=0.12, wspace=0.22)
    return fig


def _draw_competing_ccurves(ax, view, *, show_ferrite=True, t_lim=(0.1, 1e7)):
    """Draw one steel's three competing KV C-curves (ferrite/pearlite/bainite) on a TTT axis.

    Shared by both panels of :func:`unified_kv_figure`. ``view`` is a
    :class:`~steel.demo_unified_kv.SteelView`. Plots each reaction's start line ``t(T)`` (nan-masked
    above its ceiling), the ``Bs``/``Ms`` markers, and a nose dot per curve.
    """
    temps = view.temps
    if show_ferrite and view.has_ferrite:
        keep = np.isfinite(view.ferrite_tau) & (view.ferrite_tau < t_lim[1])
        ax.plot(view.ferrite_tau[keep], temps[keep], color="#c8941f", lw=2.4,
                label="ferrite start  (FC, ΔT³)")
    keep = np.isfinite(view.pearlite_tau) & (view.pearlite_tau < t_lim[1])
    ax.plot(view.pearlite_tau[keep], temps[keep], color=PHASE_COLORS["pearlite"], lw=2.4,
            label="pearlite start  (PC, ΔT³)")
    keep = np.isfinite(view.bainite_tau) & (view.bainite_tau < t_lim[1])
    ax.plot(view.bainite_tau[keep], temps[keep], color=PHASE_COLORS["bainite"], lw=2.4,
            label="bainite start  (BC, ΔT¹, atlas-anchored)")

    noses = [(view.pearlite_nose, PHASE_COLORS["pearlite"]), (view.bainite_nose, PHASE_COLORS["bainite"])]
    if show_ferrite and view.has_ferrite and view.ferrite_nose is not None:
        noses.append((view.ferrite_nose, "#c8941f"))
    for (Tn, tn), col in noses:
        if np.isfinite(tn):
            ax.plot([tn], [Tn], "o", color=col, ms=6, mec="0.2", zorder=5)

    ax.axhline(view.Bs, color=PHASE_COLORS["bainite"], ls=":", lw=1.2)
    ax.axhline(view.Ms, color=PHASE_COLORS["martensite"], ls=":", lw=1.2)
    ax.text(t_lim[0] * 1.4, view.Bs + 6, "Bₛ", va="bottom", ha="left",
            color=PHASE_COLORS["bainite"], fontsize=8.5)
    ax.text(t_lim[0] * 1.4, view.Ms + 6, "Mₛ", va="bottom", ha="left",
            color=PHASE_COLORS["martensite"], fontsize=8.5)
    ax.set_xscale("log")
    ax.set_xlim(*t_lim)
    ax.set_ylim(0.0, view.Ae3 + 30.0)
    ax.set_xlabel("time  (s)")
    ax.set_ylabel("temperature  (°C)")
    return ax


def unified_kv_figure(d):
    """The §19 artifact: the bainite bay **opened** in continuous cooling (the 6b deepening).

    ``d`` is a :class:`~steel.demo_unified_kv.UnifiedDemo` (already-validated arrays — this layer
    only draws them, ADR 0002). Two panels:

    * **left — 4340: the bay opens.** The three competing Li/KV C-curves (ferrite/pearlite/bainite);
      alloying pushes the reconstructive ferrite/pearlite noses ~10³× right (cited ``FC``/``PC``)
      while the displacive bainite nose barely moves (per-steel atlas-anchored ``BC``). Three cooling
      paths thread it: fast → **martensite**, intermediate → **bainite** (the bay), slow →
      **ferrite + pearlite**.
    * **right — 1080: no bay.** Eutectoid plain carbon: no proeutectoid ferrite, and the pearlite and
      bainite noses nearly coincide (a merged C-curve) — the consistency contrast.

    The bainite time base is the **per-steel atlas anchor** (cited, the validated absolute time); the
    ferrite/pearlite separation is the **cited differential** (the teeth). The bay *opening in CCT*
    is bridged from the isothermal atlas by Scheil additivity (no measured-CCT validation) — a
    **demonstration**, named on the figure.
    """
    import matplotlib.pyplot as plt

    fig, (ax_bay, ax_nb) = plt.subplots(1, 2, figsize=(13.0, 5.6))

    # --- left: 4340, the bay opens, with three cooling paths threading it ----- #
    _draw_competing_ccurves(ax_bay, d.bay)
    for p in d.paths:
        m = p.t > 0.0
        dom = p.dominant.replace("_", " ")
        ax_bay.plot(p.t[m], p.T[m], color=PHASE_COLORS.get(p.dominant, "0.3"),
                    lw=1.8, ls="--", alpha=0.9, label=f"{p.label} → {dom}")
    # Annotate the bay: the temperature gap between the bainite nose and the pearlite nose.
    t_mid = float(np.sqrt(d.bay.bainite_nose[1] * d.bay.pearlite_nose[1]))
    ax_bay.annotate("the BAY\n(cool through here\n→ bainite)", (t_mid, d.bay.Bs - 70),
                    ha="center", va="top", fontsize=8.5, color="0.25",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#eef6f0", ec=PHASE_COLORS["bainite"], lw=1.0))
    ax_bay.set_title("4340: the bay opens — ferrite/pearlite pushed ~10³× right, bainite stays put",
                     fontsize=10.0)
    ax_bay.legend(loc="upper right", fontsize=7.6, framealpha=0.92)

    # --- right: 1080, no bay (the consistency contrast) ---------------------- #
    _draw_competing_ccurves(ax_nb, d.nobay, show_ferrite=False)
    ax_nb.set_title("1080: no bay — pearlite & bainite noses coincide (eutectoid, no ferrite)",
                    fontsize=10.0)
    ax_nb.legend(loc="upper right", fontsize=8, framealpha=0.92)
    ax_nb.annotate("the merged C-curve a fast quench\nmust outrun (the four-curves ladder)",
                   (0.5, 0.02), xycoords="axes fraction", ha="center", va="bottom",
                   fontsize=8, color="0.4", style="italic")

    fig.suptitle(
        "§19 — the bainite bay, opened in continuous cooling (per-steel-anchored demonstrator; "
        "the validated single-curve pipeline is untouched)",
        fontsize=12.0, fontweight="bold",
    )
    fig.subplots_adjust(left=0.065, right=0.98, top=0.89, bottom=0.11, wspace=0.2)
    return fig


def austemper_figure(d):
    """The Phase-6d artifact: the atlas-anchored austempering hold, in three panels.

    ``d`` is a :class:`~steel.demo_austemper.AustemperDemo` (already-validated arrays —
    this layer only draws them, ADR 0002).

    * **left — the anchored isothermal diagram, atlas measurements on it:** the model 50 %-line
      (anchored at ONE cited point, ringed) runs through the *other* measured 50 % points — the
      holdout teeth, visible. The begin line is drawn honestly as shape-only (anchored at t₅₀ its
      begin→50 % spacing runs wide — claims stop at the 50 % line). The hold path steps across.
    * **middle — the hold itself:** completion ``U(t)`` with the predicted vs measured 50 % time
      at this hold temperature.
    * **right — hardness vs hold time:** too short a hold leaves austenite that shears to brittle
      untempered martensite on the cool; past the marked minimum full-transform hold the structure
      is fully bainitic (the carbon-only bainite placeholder hardness, named).
    """
    import matplotlib.pyplot as plt

    fig, (ax_ttt, ax_u, ax_hv) = plt.subplots(1, 3, figsize=(16.0, 5.2))
    h = d.hold

    # --- left: the anchored isothermal diagram + atlas points + the hold path --- #
    keep = np.isfinite(d.t50_line) & (d.t50_line < 1e7)
    ax_ttt.plot(d.t50_line[keep], d.temps[keep], color=PHASE_COLORS["bainite"], lw=2.4,
                label="model 50 % (anchored, validated)")
    keep_b = np.isfinite(d.begin_line) & (d.begin_line < 1e7)
    ax_ttt.plot(d.begin_line[keep_b], d.temps[keep_b], color=PHASE_COLORS["bainite"], lw=1.4,
                ls="--", alpha=0.7, label="model begin (shape-only — named)")
    ax_ttt.plot(d.atlas_t50_t, d.atlas_t50_T, "o", color="0.15", ms=6.5, zorder=5,
                label="atlas 50 % (measured)")
    ax_ttt.plot(d.atlas_begin_t, d.atlas_begin_T, "o", mfc="none", mec="0.15", ms=6.5, zorder=5,
                label="atlas begin (measured)")
    ax_ttt.plot([d.anchor_t50], [d.anchor_T], "o", mfc="none", mec="#c0392b", ms=13, mew=2.2,
                zorder=6, label="THE anchor (one cited point)")
    # The hold path: instant quench in, hold at T_hold, quench out (drawn at the left edge).
    t_lo = max(min(d.atlas_begin_t.min(), d.begin_line[keep_b].min()) * 0.2, 1e-2)
    ax_ttt.plot([t_lo, h.t_hold], [h.T_hold, h.T_hold], color=PHASE_COLORS["martensite"],
                lw=2.0, zorder=4)
    ax_ttt.plot([h.t_hold, h.t_hold], [h.T_hold, d.Ms - 60.0], color=PHASE_COLORS["martensite"],
                lw=2.0, zorder=4)
    ax_ttt.annotate("hold", (math.sqrt(t_lo * h.t_hold), h.T_hold), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=8.5, color=PHASE_COLORS["martensite"])
    for T_line, name in ((d.Bs, "Bₛ (Steven–Haynes)"), (d.Ms, "Mₛ (Andrews)")):
        ax_ttt.axhline(T_line, color="0.45", ls=":", lw=1.2)
        ax_ttt.annotate(f"  {name}", (1.0, T_line), xycoords=("axes fraction", "data"),
                        ha="right", va="bottom", fontsize=8.5, color="0.35")
    ax_ttt.set_xscale("log")
    ax_ttt.set_xlabel("time  (s)")
    ax_ttt.set_ylabel("temperature  (°C)")
    ax_ttt.set_ylim(d.Ms - 70.0, d.Bs + 35.0)
    ax_ttt.set_title(f"{d.steel}: one anchor point → the whole 50 % line (holdout)", fontsize=10.5)
    ax_ttt.legend(loc="lower right", fontsize=7.8, framealpha=0.9)

    # --- middle: the hold's completion U(t) ----------------------------------- #
    ax_u.plot(h.t, h.U, color=PHASE_COLORS["bainite"], lw=2.4)
    ax_u.axhline(0.5, color="0.6", ls=":", lw=1.0)
    ax_u.axvline(d.predicted_t50_here, color=PHASE_COLORS["bainite"], ls="--", lw=1.4)
    ax_u.annotate(f"predicted t₅₀ ≈ {d.predicted_t50_here:.0f} s",
                  (d.predicted_t50_here, 0.52), textcoords="offset points", xytext=(6, 0),
                  fontsize=8.5, color=PHASE_COLORS["bainite"])
    if np.isfinite(d.measured_t50_here):
        ax_u.plot([d.measured_t50_here], [0.5], "o", color="0.15", ms=7, zorder=5)
        ax_u.annotate(f"atlas: {d.measured_t50_here:.0f} s", (d.measured_t50_here, 0.5),
                      textcoords="offset points", xytext=(8, -14), fontsize=8.5, color="0.15")
    ax_u.set_xlabel("hold time  (s)")
    ax_u.set_ylabel("bainite completion  U")
    ax_u.set_ylim(-0.02, 1.05)
    ax_u.set_xlim(0.0, h.t_hold)
    # Only an atlas-measured, non-anchor temperature earns the "holdout" tag (the app drives
    # arbitrary holds through this same figure).
    holdout = " — a holdout temperature" if (np.isfinite(d.measured_t50_here)
                                             and d.T_hold != d.anchor_T) else ""
    ax_u.set_title(f"the hold at {h.T_hold:.0f} °C{holdout}", fontsize=10.5)

    # --- right: hardness vs hold time + the minimum full-transform hold ------- #
    ax_hv.plot(d.sweep_t, d.sweep_HV, color="0.2", lw=2.4)
    ax_hv.axvline(d.min_full_hold, color=PHASE_COLORS["bainite"], ls="--", lw=1.4)
    ax_hv.annotate(f"minimum full-transform\nhold ≈ {d.min_full_hold:.0f} s",
                   (d.min_full_hold, float(np.max(d.sweep_HV))), textcoords="offset points",
                   xytext=(8, -16), fontsize=8.5, color=PHASE_COLORS["bainite"])
    ax_hv.annotate("short hold → leftover austenite\nshears to brittle untempered\nmartensite on the cool",
                   (0.03, 0.69), xycoords="axes fraction", fontsize=8, color=PHASE_COLORS["martensite"])
    HV_full = float(d.sweep_HV[-1])
    HRC_full = vickers_to_rockwell_c_safe(np.array([HV_full]))[0]
    tag = f"fully bainitic ≈ {HV_full:.0f} HV / {HRC_full:.0f} HRC" if np.isfinite(HRC_full) \
        else f"fully bainitic ≈ {HV_full:.0f} HV"
    ax_hv.annotate(tag + "\n(carbon-only placeholder — named)",
                   (0.97, 0.05), xycoords="axes fraction", ha="right", fontsize=8,
                   color=PHASE_COLORS["bainite"])
    ax_hv.set_xscale("log")
    ax_hv.set_xlabel("hold time  (s)")
    ax_hv.set_ylabel("hardness  (HV)")
    ax_hv.set_title("the austempering trade: hold long enough", fontsize=10.5)

    fig.suptitle(
        f"Phase 6d — austempering {d.steel}: the 6b bainite reaction in its valid home "
        f"(per-steel atlas anchor; claims stop at the 50 % line)",
        fontsize=12.5, fontweight="bold",
    )
    fig.subplots_adjust(left=0.055, right=0.985, top=0.87, bottom=0.12, wspace=0.24)
    return fig


def martemper_distortion_figure(dc):
    """The Phase-6e artifact: why martempering exists — the through-section gradient at ``Mₛ``.

    ``dc`` is a :class:`~steel.martemper.DistortionComparison` (already-computed slab histories on
    the frozen heat engine — this layer only draws them, ADR 0002). Two panels, the *same* slab
    quenched two ways, each showing the **surface** (solid) and **centre** (dashed) temperature
    histories with the steel's ``Mₛ`` marked:

    * **left — direct quench:** the surface dives through ``Mₛ`` while the centre is still tens of
      degrees hotter and untransformed. The shaded bar at the surface-``Mₛ`` instant is the
      through-section temperature gradient *at the onset of transformation* — the driver of
      differential transformation strain, distortion and quench cracking.
    * **right — martemper:** the bath hold (the plateau just above ``Mₛ``) lets the section
      **equalise**; the slow final cool then takes surface and centre through ``Mₛ`` almost
      together, so the gradient at transformation nearly vanishes.

    The headline is the **reduction factor** — *the same hardness a direct quench would give*
    (point-for-point; the equivalence is exact by construction — not a claim the thick section fully
    through-hardens), at a fraction of the transformation gradient. The gradient is a *thermal proxy*
    for distortion risk; no stress is modelled (solid mechanics is the deferred residual-stress axis).
    """
    import matplotlib.pyplot as plt

    fig, (ax_d, ax_m) = plt.subplots(1, 2, figsize=(14.5, 5.4), sharey=True)
    surf_c = MEDIUM_COLORS["water"]
    cent_c = PHASE_COLORS["pearlite"]

    def _crossing(hist, T):
        below = np.flatnonzero(hist.surface <= T)
        if below.size == 0 or below[0] == 0:
            return float("nan")
        return float(np.interp(T, hist.surface[::-1], hist.t[::-1]))

    def _panel(ax, hist, gradient, title):
        ax.plot(hist.t, hist.surface, "-", color=surf_c, lw=2.2, label="surface")
        ax.plot(hist.t, hist.center, "--", color=cent_c, lw=2.2, label="centre")
        ax.axhline(dc.Ms, color="0.45", ls=":", lw=1.2)
        ax.annotate(f"  Mₛ = {dc.Ms:.0f} °C", (1.0, dc.Ms), xycoords=("axes fraction", "data"),
                    ha="right", va="bottom", fontsize=8.5, color="0.35")
        t_s = _crossing(hist, dc.Ms)
        if np.isfinite(t_s):
            T_c = float(np.interp(t_s, hist.t, hist.center))
            # The gradient bar: surface (at Mₛ) up to the still-hotter centre, at the crossing instant.
            ax.plot([t_s, t_s], [dc.Ms, T_c], color="0.2", lw=3.0, solid_capstyle="butt", zorder=5)
            ax.plot([t_s], [dc.Ms], "o", color=surf_c, ms=6, zorder=6)
            ax.plot([t_s], [T_c], "o", color=cent_c, ms=6, zorder=6)
            ax.annotate(f"ΔT = {abs(gradient):.0f} °C\nat surface-Mₛ",
                        (t_s, 0.5 * (dc.Ms + T_c)), textcoords="offset points", xytext=(10, 0),
                        va="center", fontsize=9, color="0.2",
                        fontweight="bold" if abs(gradient) > 5 else "normal")
            ax.set_xlim(0.0, min(hist.t[-1], 1.7 * t_s))
        ax.set_xlabel("time  (s)")
        ax.set_title(title, fontsize=10.5)
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

    ax_d.set_ylabel("temperature  (°C)")
    _panel(ax_d, dc.direct, dc.gradient_direct, "direct quench: surface transforms first")
    _panel(ax_m, dc.martemper, dc.gradient_martemper,
           f"martemper: hold at {dc.T_bath:.0f} °C → equalise → slow cool")
    ax_d.set_ylim(dc.Ms - 60.0, None)

    plate_mm = 2_000.0 * dc.half_thickness
    fig.suptitle(
        f"Phase 6e — martempering {dc.steel} ({plate_mm:.0f} mm plate): direct-quench hardness, "
        f"{dc.reduction:.0f}× smaller transformation gradient (proxy, not stress)",
        fontsize=11.0, fontweight="bold",
    )
    fig.subplots_adjust(left=0.06, right=0.985, top=0.88, bottom=0.12, wspace=0.06)
    return fig


# Residual-stress sign palette: tension (crack-prone) warm, compression (benign) cool.
TENSION_COLOR = "#c0392b"        # red — surface tension (the quench-crack driver)
COMPRESSION_COLOR = "#2471a3"    # blue — surface compression (benign / beneficial)


def residual_stress_figure(on, off, marte):
    """The Phase-6f artifact: the residual-stress profile a quench locks into a plate.

    Three already-computed :class:`~steel.residual.ResidualStressField` solves on the *same* slab
    (this layer only draws them, ADR 0002): ``on`` = direct quench with the transformation active,
    ``off`` = the same quench with transformation suppressed (thermal-only), ``marte`` = the martemper
    route. The depth axis runs **centre → surface** (0 to the half-thickness); the residual stress is
    plotted signed (tension +, compression −) with the zero line marked.

    * **left — the sign reversal (the headline tooth).** Thermal contraction alone leaves the surface
      in **compression** (the hot core yields, then the equalising part pulls the surface in); the
      martensite **dilatation flips it to tension** — the surface transforms first and is then stretched
      by the late-expanding core. The same steel and quench, opposite surface signs: the mechanism that
      makes a through-hardening quench crack-prone, and why a pure-elastic model (which gives *zero*
      residual on a through-hardened part) was rejected.
    * **right — the martemper benefit (the §17 tie-in, now in stress).** The direct quench's surface
      tension vs the martemper's: the near-uniform slow cool through ``Mₛ`` collapses it — the
      stress-quantitative statement of §17's distortion proxy. The reduction is near-complete in this
      idealised (thermally-thin slow cool, no transformation plasticity) model — a best case.

    The magnitude is property-sensitive (it scales with the representative yield base); the **teeth are
    the signs, the self-equilibrium, and the route ratio**, not the absolute MPa (ADR 0002 — the render
    layer draws validated numbers; the triad tests carry the validity).
    """
    import matplotlib.pyplot as plt

    fig, (ax_sign, ax_route) = plt.subplots(1, 2, figsize=(14.5, 5.6), sharey=True)
    depth_mm = on.x * 1000.0

    def _profile(ax, field, color, label, ls="-"):
        ax.plot(depth_mm, field.sigma_MPa(), ls, color=color, lw=2.4, label=label)
        ax.plot([depth_mm[-1]], [field.surface_MPa], "o", color=color, ms=7, zorder=6)

    for ax in (ax_sign, ax_route):
        ax.axhline(0.0, color="0.45", ls=":", lw=1.2)
        ax.set_xlabel("depth from centreline  (mm)   →  surface")

    # -- left: the sign reversal (transformation ON vs OFF) ----------------------- #
    _profile(ax_sign, off, COMPRESSION_COLOR, "thermal only (transformation OFF)", ls="--")
    _profile(ax_sign, on, TENSION_COLOR, "with transformation (ON)")
    ax_sign.set_ylabel("residual stress  (MPa)     tension +  /  compression −")
    ax_sign.annotate(f"surface TENSION\n{on.surface_MPa:+.0f} MPa  (crack-prone)",
                     (depth_mm[-1], on.surface_MPa), textcoords="offset points",
                     xytext=(-8, -4), ha="right", va="top", fontsize=8.6,
                     color=TENSION_COLOR, fontweight="bold")
    ax_sign.annotate(f"surface compression\n{off.surface_MPa:+.0f} MPa  (benign)",
                     (depth_mm[-1], off.surface_MPa), textcoords="offset points",
                     xytext=(-8, 6), ha="right", va="bottom", fontsize=8.6,
                     color=COMPRESSION_COLOR)
    ax_sign.set_title("the transformation flips the surface sign: compression → tension",
                      fontsize=10.5)
    ax_sign.legend(loc="upper left", fontsize=8.5, framealpha=0.9)

    # -- right: direct quench vs martemper (the stress benefit) ------------------- #
    _profile(ax_route, on, TENSION_COLOR, "direct quench")
    _profile(ax_route, marte, MEDIUM_COLORS["oil"], "martemper", ls="-.")
    ax_route.annotate(f"direct: {on.surface_MPa:+.0f} MPa",
                      (depth_mm[-1], on.surface_MPa), textcoords="offset points",
                      xytext=(-8, -4), ha="right", va="top", fontsize=8.6,
                      color=TENSION_COLOR, fontweight="bold")
    ax_route.annotate(f"martemper: {marte.surface_MPa:+.0f} MPa",
                      (depth_mm[-1], marte.surface_MPa), textcoords="offset points",
                      xytext=(-8, 10), ha="right", va="bottom", fontsize=8.6,
                      color=MEDIUM_COLORS["oil"])
    ax_route.set_title("martempering collapses the surface tension (the distortion benefit, in stress)",
                       fontsize=10.5)
    ax_route.legend(loc="upper left", fontsize=8.5, framealpha=0.9)

    plate_mm = 2_000.0 * on.half_thickness
    fig.suptitle(
        f"Phase 6f — residual stress on quench, {on.steel} ({plate_mm:.0f} mm plate): "
        f"transformation → surface tension; martempering removes it",
        fontsize=11.0, fontweight="bold",
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.88, bottom=0.12, wspace=0.06)
    return fig


def cct_validation_figure(d):
    """The §20 artifact: cross-composition bainite validation vs the IT atlas, in two panels.

    ``d`` is a :class:`~steel.demo_cct_validation.CctValidationDemo` (validated arrays only — this
    layer draws, ADR 0002). Each cited factor is drawn in **its own reaction's colour** (bainite
    green ``BC``, ferrite tan ``FC``, pearlite orange ``PC``) — the mnemonic that the alloy-weighted
    diffusional factors order bainite better than bainite's own carbon-dominated one.

    * **left — predicted vs measured 50 %-time (log-log):** the magnitude story. ``FC`` hugs the
      ±factor-2 band (the read uncertainty); the carbon-dominated ``BC`` sits low (predicts too fast)
      and inverts 1080; ``PC`` ranks but sits high. The dashed 1:1 line + shaded band is the target.
    * **right — the scorecard + verdict:** Spearman rank skill per factor (``BC`` ≈ 0, the wall), the
      out-of-sample refit lift (arrow), and the bias-immune cited-anchor headline — none wins both,
      so per-steel anchoring stands.
    """
    import matplotlib.pyplot as plt

    fig, (ax_sc, ax_bar) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    factor_color = {"bainite": PHASE_COLORS["bainite"], "ferrite": "#c79a4a",
                    "pearlite": PHASE_COLORS["pearlite"]}
    factor_label = {"bainite": "BC  (bainite, cited)", "ferrite": "FC  (ferrite, cited)",
                    "pearlite": "PC  (pearlite, cited)"}

    # --- left: predicted vs measured t50 @ 700 °F (log-log) ------------------- #
    lo, hi = 30.0, 3e5
    ax_sc.fill_between([lo, hi], [lo / 2, hi / 2], [lo * 2, hi * 2], color="0.85", alpha=0.6,
                       zorder=0, label="±factor-2 (read uncertainty)")
    ax_sc.plot([lo, hi], [lo, hi], color="0.4", ls="--", lw=1.2, zorder=1, label="perfect (1:1)")
    for which in ("ferrite", "pearlite", "bainite"):
        g = d.grades[which]
        pred = np.array([g.predicted[n] for n in d.names])
        inrange = (pred >= lo) & (pred <= hi)
        ax_sc.scatter(d.measured[inrange], pred[inrange], s=46, color=factor_color[which],
                      edgecolor="0.2", lw=0.5, zorder=3,
                      label=f"{factor_label[which]}  (ρ={g.spearman:.2f})")
        # points below the frame (BC predicts ×10–40 too fast) — mark at the floor as ▽
        below = pred < lo
        if below.any():
            ax_sc.scatter(d.measured[below], np.full(below.sum(), lo * 1.03), s=44,
                          marker="v", color=factor_color[which], edgecolor="0.2", lw=0.5, zorder=3)
    # name the two cited anchors (the bias-immune pair)
    for i, n in enumerate(d.names):
        if d.cited_mask[i]:
            ax_sc.annotate(n, (d.measured[i], d.grades["ferrite"].predicted[n]),
                           textcoords="offset points", xytext=(6, -10), fontsize=8.5, color="0.2")
    ax_sc.set_xscale("log"); ax_sc.set_yscale("log")
    ax_sc.set_xlim(lo, hi); ax_sc.set_ylim(lo, hi)
    ax_sc.set_xlabel("measured bainite t₅₀ @ 700 °F  (s, atlas)")
    ax_sc.set_ylabel("predicted t₅₀  (s, anchored on 1080)")
    ax_sc.set_title("anchored on 1080: FC tracks the band, BC predicts too fast (inverts 1080)",
                    fontsize=10.0)
    ax_sc.legend(loc="upper left", fontsize=7.8, framealpha=0.92)

    # --- right: Spearman scorecard + refit lift + cited-anchor headline -------- #
    order = ["bainite", "ferrite", "pearlite"]
    xs = np.arange(len(order))
    rhos = [d.grades[w].spearman for w in order]
    ax_bar.bar(xs, rhos, color=[factor_color[w] for w in order], edgecolor="0.2", width=0.6, zorder=3)
    ax_bar.axhline(0.0, color="0.3", lw=1.0)
    for x, w in zip(xs, order):
        g = d.grades[w]
        ax_bar.annotate(f"×{10 ** g.log_resid_spread:.1f}\nspread", (x, max(g.spearman, 0) + 0.03),
                        ha="center", va="bottom", fontsize=8, color="0.3")
    # the out-of-sample refit lift on BC (bainite bar)
    h = d.holdout
    ax_bar.annotate("", xy=(0.0, h.test_spearman_refit), xytext=(0.0, h.test_spearman_bc),
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.8), zorder=5)
    ax_bar.annotate(f"1-knob refit\n(λ→0): TEST\nρ {h.test_spearman_bc:.1f}→{h.test_spearman_refit:.1f}",
                    (0.0, h.test_spearman_refit), textcoords="offset points", xytext=(10, -2),
                    fontsize=7.6, color="#c0392b", va="center")
    ax_bar.set_xticks(xs)
    ax_bar.set_xticklabels(["BC\n(bainite)", "FC\n(ferrite)", "PC\n(pearlite)"], fontsize=9)
    ax_bar.set_ylabel("cross-steel rank skill  (Spearman ρ)")
    ax_bar.set_ylim(-0.15, 1.05)
    ax_bar.set_title("none wins both → per-steel anchoring vindicated", fontsize=10.5)
    w = d.wall
    ax_bar.annotate(
        f"headline (2 cited anchors only):\ncited BC inverts 1080↔4340 by ×{w.miss:.0f}\n"
        f"(reproduces austemper's scale gap)",
        (0.97, 0.04), xycoords="axes fraction", ha="right", va="bottom", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fbeee6", ec="#c0392b", alpha=0.9))

    fig.suptitle("§20 — cross-composition bainite kinetics vs the US Steel IT atlas: "
                 "the wall measured on 8 steels, per-steel anchoring strengthened",
                 fontsize=11.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.9, bottom=0.12, wspace=0.2)
    return fig


# Colour families for the Ellingham diagram (F1). Reductants warm/bold, iron-oxide chain a brown
# ladder, reference alloy/slag oxides muted grey-blues.
ELLINGHAM_COLORS = {
    "C->CO":        "#c0392b",   # the reductant star — bold red, the down-sloping line
    "H2->H2O":      "#2471a3",   # hydrogen reductant
    "CO->CO2":      "#7f8c8d",   # the CO/CO₂ line
    "Fe->FeO":      "#7a4a1e",   # iron-oxide chain, darkest = most reduced
    "FeO->Fe3O4":   "#a9712f",
    "Fe3O4->Fe2O3": "#cda06a",
    "Ca->CaO":      "#34495e",   # the hierarchy (muted)
    "Al->Al2O3":    "#566573",
    "Si->SiO2":     "#707b7c",
    "Mn->MnO":      "#85929e",
    "Cr->Cr2O3":    "#99a3a4",
}


def ellingham_figure(d):
    """The F1 artifact: the Ellingham diagram + the equilibrium oxygen-potential ladder.

    ``d`` is a :class:`~steel.demo_reduction.EllinghamDemo` (already-validated arrays — this layer
    only draws them, ADR 0002). Two panels:

    * **left — the Ellingham diagram.** ΔG° of oxide formation per mole O₂ vs temperature. The
      metal-oxide lines slope *up* (forming an oxide consumes O₂ gas, ΔS° < 0); the lone
      **2C + O₂ → 2CO** line slopes *down* (it makes gas) and dives under them. Where it crosses the
      Fe → FeO line (~746 °C, marked) carbon begins to reduce wüstite — the shaded **reduction
      window** to its right is where ironmaking happens. The iron-oxide chain (Fe → FeO → Fe₃O₄ →
      Fe₂O₃) is the brown ladder; the muted lines are the alloy/slag-oxide hierarchy (CaO/Al₂O₃ at
      the bottom — the strong deoxidizers).
    * **right — the oxygen potential.** The same numbers as equilibrium p_O₂(T): the O₂ pressure at
      which each metal and its oxide coexist. Al₂O₃/CaO survive down to 10⁻³⁵–10⁻⁴² bar — *why* Al
      and Ca deoxidize a bath that Fe, Mn, Si cannot (the bridge to F2).

    Straight lines with the melting/boiling kinks omitted (ΔCp ≈ 0) — the named module ceiling.
    """
    import matplotlib.pyplot as plt

    fig, (ax_ell, ax_po2) = plt.subplots(1, 2, figsize=(14.5, 6.2))
    T = np.array(d.temps_C)
    Tmax = float(T[-1])

    def _draw(ax, keys, *, lw, ls="-", alpha=1.0, label_right=True, label_fs=8.0):
        for k in keys:
            y = np.array(d.lines[k])
            color = ELLINGHAM_COLORS.get(k, "0.4")
            ax.plot(T, y, color=color, lw=lw, ls=ls, alpha=alpha)
            if label_right:
                ax.annotate(f" {_ellingham_label(k)}", (Tmax, y[-1]), va="center", ha="left",
                            fontsize=label_fs, color=color)

    # --- left: the Ellingham diagram ----------------------------------------- #
    iron_keys = ("Fe->FeO", "FeO->Fe3O4", "Fe3O4->Fe2O3")
    muted_keys = tuple(k for k in d.lines if k not in iron_keys and k != "C->CO")
    _draw(ax_ell, muted_keys, lw=1.3, alpha=0.85)         # hierarchy + H2/CO lines (muted)
    _draw(ax_ell, iron_keys, lw=2.0, alpha=0.95)          # the iron-oxide chain (the ore)
    _draw(ax_ell, ("C->CO",), lw=2.8)                     # the reductant star

    # The headline crossover: carbon reduces wüstite above it. Mark the point + shade the window.
    Tc = d.carbon_wustite_crossover_C
    g_at = float(np.interp(Tc, T, np.array(d.lines["Fe->FeO"])))
    ax_ell.plot([Tc], [g_at], "o", mfc="none", mec="#c0392b", ms=14, mew=2.2, zorder=6)
    ax_ell.axvspan(Tc, Tmax, color="#fdecea", alpha=0.55, zorder=0)
    ax_ell.annotate(f"carbon reduces FeO →\n(above ~{Tc:.0f} °C)", (Tc, g_at),
                    textcoords="offset points", xytext=(12, 26), fontsize=8.6, color="#c0392b",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#c0392b", lw=1.0))
    ax_ell.set_xlim(float(T[0]), Tmax + (Tmax - T[0]) * 0.22)   # room for right-edge labels
    ax_ell.set_xlabel("temperature  (°C)")
    ax_ell.set_ylabel("ΔG° of oxidation  (kJ per mole O₂)")
    ax_ell.set_title("Ellingham diagram — the C→CO line dives under the oxides; "
                     "where it crosses Fe→FeO, ironmaking begins", fontsize=9.8)
    ax_ell.grid(True, alpha=0.25)

    # --- right: the equilibrium oxygen-potential ladder ----------------------- #
    for k in d.pO2:
        y = np.array(d.pO2[k])
        color = ELLINGHAM_COLORS.get(k, "0.4")
        ax_po2.plot(T, y, color=color, lw=2.0)
        ax_po2.annotate(f" {_ellingham_label(k)}", (Tmax, y[-1]), va="center", ha="left",
                        fontsize=8.0, color=color)
    ax_po2.set_xlim(float(T[0]), Tmax + (Tmax - T[0]) * 0.20)
    ax_po2.set_xlabel("temperature  (°C)")
    ax_po2.set_ylabel("equilibrium oxygen potential  log₁₀(p_O₂ / bar)")
    ax_po2.set_title("oxygen potential — Al/Ca oxides survive to 10⁻³⁵–10⁻⁴² bar "
                     "(why they deoxidize)", fontsize=9.8)
    ax_po2.grid(True, alpha=0.25)
    # Honesty caveat (the named ΔCp=0 ceiling): absolute values past a metal's melting/boiling
    # point carry the omitted-kink error — the ladder's *ordering* is the robust read, not the
    # last-digit pressure (e.g. Ca boils at 1484 °C, inside this range).
    ax_po2.annotate("straight-line ΔCp=0 model: absolute p_O₂ past each metal's melting/boiling\n"
                    "point carries the omitted-kink error — read the ladder's order, not last digits",
                    (0.5, 0.015), xycoords="axes fraction", ha="center", va="bottom",
                    fontsize=7.2, color="0.45", style="italic")

    fig.suptitle("F1 — reduction thermodynamics: which reductant reduces which oxide, "
                 "above which temperature  (ore → iron)",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.06, right=0.97, top=0.9, bottom=0.1, wspace=0.22)
    return fig


def _ellingham_label(key: str) -> str:
    """Short legend tag for an Ellingham line — the product oxide (or reductant) name."""
    tags = {
        "C->CO": "2C→2CO", "H2->H2O": "H₂→H₂O", "CO->CO2": "2CO→2CO₂",
        "Fe->FeO": "FeO", "FeO->Fe3O4": "Fe₃O₄", "Fe3O4->Fe2O3": "Fe₂O₃",
        "Ca->CaO": "CaO", "Al->Al2O3": "Al₂O₃", "Si->SiO2": "SiO₂",
        "Mn->MnO": "MnO", "Cr->Cr2O3": "Cr₂O₃",
    }
    return tags.get(key, key)


def heat_state_figure(d):
    """The F-spine artifact: an upstream alloy mistake *propagates* to a downstream defect.

    ``d`` is a :class:`~steel.demo_heat_state.HeatStateDemo` (already-computed scalars — this layer
    only draws them, ADR 0002). The spine adds no physics; the figure draws the *propagation*, which
    is the spine's whole point. Two panels, deliberately separated:

    * **left — the general propagation proof (any composition).** Two 4140 heats take the *same* oil
      quench through :func:`~steel.heat_state.heat_treat`; only the composition differs (Cr/Mo
      under-dosed upstream). The core-martensite bars straddle the
      :data:`~steel.heat_state.MIN_MARTENSITE_SPEC` line: the well-dosed heat clears it (martensitic,
      hard); the under-dosed heat falls under it → the **soft-core** flag. The failure is not scripted
      — it is the back-end martensite fraction crossing a spec line, carried on the ``Heat``.
    * **right — the fixed atlas-steel illustration (a *different* engine, honestly bounded).** The §18
      residual solve repacked onto an atlas 4340 heat: the surface locks into **tension** → the
      **quench-crack-risk** flag. Drawn in its own panel and labelled as the fixed-grade stand-in,
      because the §18 engine is atlas-anchored — the off-spec-composition → crack chain is **deferred**
      (``steel-making.md`` §6), and this figure must not imply it runs.
    """
    import matplotlib.pyplot as plt

    fig, (ax_bars, ax_res) = plt.subplots(1, 2, figsize=(13.0, 5.4),
                                          gridspec_kw={"width_ratios": [1.5, 1.0]})

    # --- left: same quench, composition decides — the soft-core spec line ----- #
    fracs = [d.well_martensite, d.under_martensite]
    hvs = [d.well_HV, d.under_HV]
    labels = ["properly dosed\n(4140: Cr 1.0, Mo 0.2)", "under-dosed\n(Cr 0.1, Mo 0)"]
    # Pass = martensite blue; fail = the warning red used for the atlas crossover elsewhere.
    colors = [PHASE_COLORS["martensite"], "#c0392b"]
    x = np.arange(2)
    ax_bars.bar(x, fracs, width=0.58, color=colors, edgecolor="0.25", zorder=3)
    ax_bars.axhline(d.spec, color="0.35", ls="--", lw=1.6, zorder=2)
    ax_bars.annotate(f"soft-core spec  (≥ {d.spec:.0%} martensite)", (1.0, d.spec),
                     xycoords=("axes fraction", "data"), ha="right", va="bottom",
                     fontsize=8.6, color="0.3")
    for xi, frac, hv in zip(x, fracs, hvs):
        ax_bars.annotate(f"{frac:.0%}\n{hv:.0f} HV", (xi, frac), textcoords="offset points",
                         xytext=(0, 5), ha="center", va="bottom", fontsize=10, fontweight="bold",
                         color="0.15")
    ax_bars.annotate("SOFT CORE\n(ferrite-dominant)", (1, d.under_martensite),
                     textcoords="offset points", xytext=(0, 34), ha="center", fontsize=9,
                     color="#c0392b", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#c0392b", lw=1.0))
    ax_bars.set_xticks(x)
    ax_bars.set_xticklabels(labels, fontsize=9)
    ax_bars.set_ylabel("core martensite fraction")
    ax_bars.set_ylim(0.0, 1.12)
    ax_bars.set_title("Same oil quench, Ø10 mm — the composition decides\n"
                      "(under-dose Cr/Mo upstream → soft core downstream)", fontsize=10.2)
    ax_bars.grid(True, axis="y", alpha=0.25)

    # --- right: the atlas residual illustration (a separate engine, bounded) -- #
    sigma = d.atlas_surface_MPa
    crack = d.cracked.has_defect("quench-crack-risk")
    ax_res.bar([0], [sigma], width=0.5, color=("#c0392b" if sigma > 0 else PHASE_COLORS["martensite"]),
               edgecolor="0.25", zorder=3)
    ax_res.axhline(0.0, color="0.4", lw=1.2, zorder=2)
    state = "TENSION → quench-crack-risk" if crack else "compression (safe)"
    ax_res.annotate(f"{sigma:+.0f} MPa\n{state}", (0, sigma), textcoords="offset points",
                    xytext=(0, 8 if sigma > 0 else -28), ha="center",
                    va="bottom" if sigma > 0 else "top", fontsize=9.5, fontweight="bold",
                    color=("#c0392b" if sigma > 0 else PHASE_COLORS["martensite"]))
    ax_res.set_xticks([0])
    ax_res.set_xticklabels(["4340, 50 mm,\nwater quench"], fontsize=9)
    ax_res.set_ylabel("surface residual stress  (MPa, tensile +)")
    ax_res.set_xlim(-0.7, 0.7)
    # Headroom above the bar so the annotation clears the panel title (works either sign).
    lo, hi = min(0.0, sigma * 1.3), max(0.0, sigma * 1.5)
    if hi - lo < 80.0:
        hi = lo + 80.0
    ax_res.set_ylim(lo, hi)
    ax_res.set_title("Fixed atlas-steel illustration (§18)\n— the same seam, a second engine",
                     fontsize=10.2)
    ax_res.grid(True, axis="y", alpha=0.25)
    ax_res.annotate("atlas-anchored to a *grade*, not a composition:\n"
                    "the off-spec → crack chain is deferred (§6)",
                    (0.5, 0.02), xycoords="axes fraction", ha="center", va="bottom",
                    fontsize=7.4, color="0.45", style="italic")

    fig.suptitle("Front-end spine — the Heat carries an upstream mistake into a downstream defect",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.13, wspace=0.26)
    return fig


# Solute line colours for the Scheil profile — impurities (S, P) hot/dark (the dangerous segregators),
# carbon warm (over-predicted), the substitutional alloys cool.
_SOLUTE_COLORS = {
    "S": "#7b1fa2", "P": "#c0392b", "C": "#e8833a", "Mo": "#1e8449",
    "Mn": "#2471a3", "Si": "#16a085", "Cr": "#8e7cc3", "Ni": "#95a5a6",
}


def casting_figure(d):
    """The F4 artifact: Scheil microsegregation, Chvorinov time, and the centerline band it propagates.

    ``d`` is a :class:`~steel.demo_casting.CastingDemo` (already-computed arrays/scalars — this layer only
    draws them, ADR 0002). Three panels:

    * **left — Scheil microsegregation.** The interdendritic **liquid** enrichment ``C_L/C₀`` vs solid
      fraction for each solute; the **severity ordering** is the un-tuned tooth (smallest ``k`` — S, C, P —
      climbs steepest, the dangerous segregators that enrich the last liquid; Cr, Ni stay near 1). The
      dashed line is the last-to-freeze ``f_s*`` whose liquid the centerline solid inherits at ``k×``; past
      it Scheil diverges (the named ceiling).
    * **middle — Chvorinov's rule.** Solidification time ``t = B·M²`` vs casting modulus — the ``∝ M²``
      foundry law (the cast section marked); the magnitude is rule-of-thumb grade, the ranking reliable.
    * **right — the propagation.** The *same* oil quench on the nominal section vs the Scheil centerline:
      the enriched centerline over-hardens into a band the bulk never reaches (martensite bars vs the
      soft-core spec line, ΔHV annotated) — the §6 uneven-hardenability link, front-to-back.
    """
    import matplotlib.pyplot as plt

    fig, (ax_seg, ax_chv, ax_band) = plt.subplots(1, 3, figsize=(16.0, 5.2))
    s = d.section

    # --- left: the Scheil segregation profile (interdendritic liquid enrichment) --- #
    for el in d.liquid_ratio:
        ax_seg.plot(d.fs, d.liquid_ratio[el], color=_SOLUTE_COLORS.get(el, "0.4"), lw=2.0)
        ax_seg.annotate(f" {el}", (d.fs[-1], d.liquid_ratio[el][-1]), va="center", ha="left",
                        fontsize=8.5, color=_SOLUTE_COLORS.get(el, "0.4"), fontweight="bold")
    ax_seg.axhline(1.0, color="0.6", ls=":", lw=1.0)
    ax_seg.axvline(s.fs_centerline, color="0.35", ls="--", lw=1.4)
    ax_seg.annotate(f"centerline f_s* = {s.fs_centerline:.2f}", (s.fs_centerline, 1.0),
                    textcoords="offset points", xytext=(-5, 2), ha="right", va="bottom",
                    fontsize=8.0, color="0.35", rotation=90)
    ax_seg.set_yscale("log")
    ax_seg.set_xlabel("solid fraction  f_s")
    ax_seg.set_ylabel("interdendritic liquid enrichment  C_L / C₀")
    ax_seg.set_xlim(0.0, 1.0)
    ax_seg.set_title(f"Scheil microsegregation (primary {s.phase}-ferrite)\n"
                     "smallest k — S, C, P — enrich the last liquid most; Cr, Ni mild", fontsize=10.2)
    ax_seg.grid(True, which="both", alpha=0.22)

    # --- middle: Chvorinov t = B·M² ------------------------------------------- #
    ax_chv.plot(d.modulus_grid * 1000.0, d.time_grid / 60.0, color="0.2", lw=2.4)
    ax_chv.plot([s.modulus * 1000.0], [s.solidification_time / 60.0], "o", color="#c0392b", ms=9, zorder=5)
    ax_chv.annotate(f"this cast section\nM = {s.modulus * 1000:.0f} mm → {s.solidification_time / 60:.1f} min",
                    (s.modulus * 1000.0, s.solidification_time / 60.0), textcoords="offset points",
                    xytext=(-10, 10), ha="right", fontsize=8.6, color="#c0392b")
    ax_chv.set_xlabel("casting modulus  M = V/A  (mm)")
    ax_chv.set_ylabel("solidification time  t = B·M²  (min)")
    ax_chv.set_title("Chvorinov's rule — time ∝ modulus²\n(B for steel in greensand; rank-grade)",
                     fontsize=10.2)
    ax_chv.grid(True, alpha=0.25)

    # --- right: the centerline band (the propagation) ------------------------- #
    fracs = [d.nominal_fM, d.centerline_fM]
    hvs = [d.nominal_HV, d.centerline_HV]
    labels = ["nominal\nsection", "segregated\ncenterline"]
    colors = ["#9aa3b2", "#c0392b"]                  # nominal grey, centerline the hot band
    x = np.arange(2)
    ax_band.bar(x, fracs, width=0.58, color=colors, edgecolor="0.25", zorder=3)
    ax_band.axhline(d.spec, color="0.35", ls="--", lw=1.6, zorder=2)
    ax_band.annotate(f"soft-core spec (≥ {d.spec:.0%})", (1.0, d.spec),
                     xycoords=("axes fraction", "data"), ha="right", va="bottom",
                     fontsize=8.4, color="0.3")
    for xi, frac, hv in zip(x, fracs, hvs):
        ax_band.annotate(f"{frac:.0%}\n{hv:.0f} HV", (xi, frac), textcoords="offset points",
                         xytext=(0, 5), ha="center", va="bottom", fontsize=10, fontweight="bold",
                         color="0.15")
    dHV = d.centerline_HV - d.nominal_HV
    ax_band.annotate(f"hard centerline BAND\nΔ{dHV:+.0f} HV", (1, d.centerline_fM),
                     textcoords="offset points", xytext=(0, 34), ha="center", fontsize=9,
                     color="#c0392b", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#c0392b", lw=1.0))
    ax_band.set_xticks(x)
    ax_band.set_xticklabels(labels, fontsize=9)
    ax_band.set_ylabel("core martensite fraction")
    ax_band.set_ylim(0.0, 1.30)               # headroom so the BAND callout clears the panel title
    ax_band.set_title(f"Same {d.section.steel.label()} casting, same oil quench →\n"
                      "the centerline over-hardens (uneven hardenability)", fontsize=10.2)
    ax_band.grid(True, axis="y", alpha=0.25)

    fig.suptitle("F4 — casting & solidification: segregation propagates front-to-back into a hard band",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.06, right=0.97, top=0.86, bottom=0.12, wspace=0.28)
    return fig


def solidification_figure(d):
    """The F4 Slice-2 artifact: the latent-heat solidification map, the arrest, the Stefan tooth, the hot spot.

    ``d`` is a :class:`~steel.demo_solidification.SolidificationDemo` (already-computed arrays — this layer
    only draws them, ADR 0002). Four panels:

    * **top-left — the solidification map.** ``T(x, t)`` of the section freezing against the chill; the solid
      front (solidus isotherm) sweeps from the chill toward the insulated thermal centre — the iconic picture.
    * **top-right — the latent-heat arrest.** The centre's temperature history, latent heat on vs off: with
      latent heat the cool-down *stalls* in the freezing band (the plateau) — directional, not a precise tooth.
    * **bottom-left — the Stefan benchmark (the tooth).** The numerical freezing front vs the analytic
      one-phase ``2λ√(αt)``, at two grid resolutions: the match converges toward the closed form as Δx halves.
    * **bottom-right — where the defects are.** Local solidification time rises to the insulated centre (the
      last-to-freeze hot spot, the same centerline Slice 1 enriches); the cited Niyama number collapses there
      (G → 0) — porosity-prone. Illustrative / by-construction.
    """
    import matplotlib.pyplot as plt

    fig, ((ax_map, ax_arr), (ax_stef, ax_def)) = plt.subplots(2, 2, figsize=(13.8, 9.8))
    p = d.path
    warn, good, amber = "#c0392b", "#1f6f3c", "#d68910"

    # --- top-left: the solidification map T(x, t) (cropped to the freezing window) --- #
    t_cap = min(d.field.t[-1], 1.7 * max(d.centre_freeze_on, 1.0))
    keep = d.field.t <= t_cap
    step = max(1, int(keep.sum()) // 320)            # subsample time rows for a clean mesh
    ti = d.field.t[keep][::step]
    Tmesh = d.field.T[keep][::step]
    xm = d.field.x * 1e3
    pcm = ax_map.pcolormesh(xm, ti, Tmesh, cmap="inferno", shading="auto",
                            vmin=p.T_sol - 250.0, vmax=p.T_liq)
    ax_map.plot(d.solidus_front[keep][::step] * 1e3, ti, color="cyan", lw=1.8, label="solidus front")
    cb = fig.colorbar(pcm, ax=ax_map, pad=0.02)
    cb.set_label("temperature (°C)")
    ax_map.set_xlabel("distance from chill  x  (mm)")
    ax_map.set_ylabel("time  t  (s)")
    ax_map.set_title(f"Solidification map — {p.T_liq:.0f}→{p.T_sol:.0f} °C front sweeps from the chill",
                     fontsize=10.2)
    ax_map.legend(loc="lower right", fontsize=8.4, framealpha=0.85)

    # --- top-right: the latent-heat arrest at the centre ----------------------- #
    ax_arr.axhspan(p.T_sol, p.T_liq, color=amber, alpha=0.16, zorder=0)
    ax_arr.annotate("freezing band", (0.98, 0.5 * (p.T_sol + p.T_liq)), xycoords=("axes fraction", "data"),
                    ha="right", va="center", fontsize=8.2, color=amber)
    t_lim = min(d.centre_t[-1], 2.2 * max(d.centre_freeze_on, 1.0))
    ax_arr.plot(d.centre_t, d.centre_T_on, color=warn, lw=2.4, label="latent heat ON (the plateau)")
    ax_arr.plot(d.centre_t, d.centre_T_off, color="0.45", lw=1.8, ls="--", label="latent heat OFF")
    ax_arr.set_xlim(0.0, t_lim)
    ax_arr.set_xlabel("time  t  (s)")
    ax_arr.set_ylabel("centre temperature (°C)")
    ax_arr.set_title(f"Latent-heat arrest at the thermal centre\nfreeze-through ×{d.centre_freeze_on/d.centre_freeze_off:.1f} vs no latent heat",
                     fontsize=10.2)
    ax_arr.legend(loc="upper right", fontsize=8.4)
    ax_arr.grid(True, alpha=0.25)

    # --- bottom-left: the Stefan benchmark (the headline tooth) ---------------- #
    v_fine = d.stefan[-1]
    tline = np.linspace(0.0, v_fine.t[-1], 200)
    from .solidification import stefan_front
    ax_stef.plot(tline, stefan_front(tline, p.alpha, v_fine.lam) * 1e3, color="0.2", lw=2.2,
                 label=f"analytic Stefan 2λ√(αt)  (λ={v_fine.lam:.3f})")
    markers = ["o", "s"]
    for v, mk in zip(d.stefan, markers):
        ax_stef.plot(v.t, v.x_numerical * 1e3, mk, ms=6.5, mfc="none",
                     color=warn if mk == "o" else good,
                     label=f"numerical, n={v.n_cells} (ratio {v.ratio.mean():.3f})")
    ax_stef.set_xlabel("time  t  (s)")
    ax_stef.set_ylabel("freezing front  X  (mm)")
    ax_stef.set_title("Stefan benchmark — the front converges to the\nclosed form as the grid refines (the tooth)",
                      fontsize=10.2)
    ax_stef.legend(loc="upper left", fontsize=8.2)
    ax_stef.grid(True, alpha=0.25)

    # --- bottom-right: defect localization (by construction) ------------------- #
    fin = np.isfinite(d.solidification_time)
    ax_def.plot(d.x[fin] * 1e3, d.solidification_time[fin], color="0.2", lw=2.4)
    ax_def.set_xlabel("distance from chill  x  (mm)")
    ax_def.set_ylabel("local solidification time  (s)", color="0.2")
    ax_def.set_title("Where the defects concentrate (by construction):\nthe centre freezes last — Slice 1's enriched centerline",
                     fontsize=10.2)
    ax_def.grid(True, alpha=0.22)
    xc = d.x[fin][-1] * 1e3
    ax_def.axvline(xc, color=warn, ls=":", lw=1.4)
    ax_def.annotate("hot spot\n(last to freeze)", (xc, d.solidification_time[fin][-1]),
                    textcoords="offset points", xytext=(-8, -4), ha="right", va="top",
                    fontsize=8.6, color=warn, fontweight="bold")
    ax_ny = ax_def.twinx()
    # mask the immediate chill-shock band (initial liquid-against-cold-wall transient) — the cited
    # criterion is meaningful in the directionally-solidified interior, where it declines toward the centre.
    nfin = np.isfinite(d.niyama) & (d.niyama_x > 0.04 * d.x[-1])
    ax_ny.plot(d.niyama_x[nfin] * 1e3, d.niyama[nfin], color="#2471a3", lw=1.8, alpha=0.85)
    ax_ny.set_ylabel("Niyama  Ny = G/√Ṫ  (cited; illustrative)", color="#2471a3")
    ax_ny.set_yscale("log")
    ax_ny.tick_params(axis="y", labelcolor="#2471a3")

    fig.suptitle("F4 Slice 2 — latent-heat solidification: the map, the arrest, the Stefan tooth, the hot spot",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.93, top=0.90, bottom=0.08, wspace=0.32, hspace=0.32)
    return fig


def hydrogen_flaking_figure(d):
    """The hydrogen-flaking artifact: same ladle H, the section decides — out-diffusion, the bake, the tooth.

    ``d`` is a :class:`~steel.demo_hydrogen_flaking.HydrogenFlakingDemo` (precomputed arrays — this layer only
    draws, ADR 0002). Four panels:

    * **top-left — the hero verdict.** Peak residual hydrogen after the same bake, thin vs thick section vs
      thick+long-bake, against the flaking limit: same heat, geometry + schedule decide.
    * **top-right — out-diffusion dynamics.** Centre hydrogen vs bake time for the two sections; the thin
      drops below the limit in under an hour, the thick lingers for days (the ``L²`` trap).
    * **bottom-left — the coherence tooth.** Dehydrogenation time vs section (log-log, slope-2 ``∝L²``); the
      load-bearing anchor is the heavy forging → days (500 mm ≈ 10 d), reproduced from an independently pinned
      D_H — the 1 h/inch thin-section mark is OoM sanity only.
    * **bottom-right — the cited input.** The α-Fe lattice diffusivity Arrhenius, the ferritic bake point
      marked; the room-temperature value is the anchor D_H was pinned to (independent of bake practice).
    """
    import matplotlib.pyplot as plt

    fig, ((ax_bar, ax_dyn), (ax_tooth, ax_arr)) = plt.subplots(2, 2, figsize=(13.6, 9.6))
    warn, good, blue = "#c0392b", "#1f6f3c", "#2471a3"

    # --- top-left: the hero verdict bars -------------------------------------- #
    labels = [f"thin\n{int(d.section_mm[2])} mm", f"thick\n{int(d.section_mm[5])} mm", "thick\n+ long bake"]
    vals = [d.thin_residual_ppm, d.thick_residual_ppm, d.thick_long_residual_ppm]
    flakes = [d.thin_flakes, d.thick_flakes, d.thick_long_flakes]
    colors = [warn if f else good for f in flakes]
    x = np.arange(3)
    ax_bar.bar(x, vals, width=0.6, color=colors, edgecolor="0.25", zorder=3)
    ax_bar.axhline(d.critical_ppm, color="0.3", ls="--", lw=1.6, zorder=2)
    ax_bar.annotate(f"flaking limit ({d.critical_ppm:.0f} ppm)", (1.0, d.critical_ppm),
                    xycoords=("axes fraction", "data"), ha="right", va="bottom", fontsize=8.4, color="0.3")
    ax_bar.axhline(d.ladle_H_ppm, color=blue, ls=":", lw=1.4, zorder=2)
    ax_bar.annotate(f"ladle H ({d.ladle_H_ppm:.1f} ppm)", (0.02, d.ladle_H_ppm),
                    xycoords=("axes fraction", "data"), ha="left", va="bottom", fontsize=8.0, color=blue)
    for xi, v, f in zip(x, vals, flakes):
        ax_bar.annotate(f"{v:.1f}\n{'FLAKES' if f else 'sound'}", (xi, v), textcoords="offset points",
                        xytext=(0, 4), ha="center", va="bottom", fontsize=9, fontweight="bold",
                        color=warn if f else good)
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(labels, fontsize=9)
    ax_bar.set_ylabel("peak (centre) residual hydrogen (ppm)")
    ax_bar.set_ylim(0.0, max(vals + [d.ladle_H_ppm]) * 1.25)
    ax_bar.set_title("Same ladle hydrogen — the section decides\n(same bake; geometry + schedule, not the number alone)",
                     fontsize=10.2)
    ax_bar.grid(True, axis="y", alpha=0.25)

    # --- top-right: out-diffusion dynamics (residual H vs bake time) ----------- #
    ax_dyn.plot(d.time_grid_h, d.thin_curve_ppm, color=good, lw=2.4, label=f"thin {int(d.section_mm[2])} mm")
    ax_dyn.plot(d.time_grid_h, d.thick_curve_ppm, color=warn, lw=2.4, label=f"thick {int(d.section_mm[5])} mm")
    ax_dyn.axhline(d.critical_ppm, color="0.3", ls="--", lw=1.5)
    ax_dyn.set_xlabel("dehydrogenation bake time (h)")
    ax_dyn.set_ylabel("centre hydrogen (ppm)")
    ax_dyn.set_title("Out-diffusion: the thin section clears fast,\nthe thick one lingers for days (the L² trap)",
                     fontsize=10.2)
    ax_dyn.legend(fontsize=8.6)
    ax_dyn.grid(True, alpha=0.25)

    # --- bottom-left: the coherence tooth (bake time vs section, ∝ L²) --------- #
    ax_tooth.loglog(d.section_mm, d.bake_time_h, "o-", color="0.2", lw=2.2, ms=6)
    ax_tooth.plot([25], [np.interp(25, d.section_mm, d.bake_time_h)], "o", color=blue, ms=11, mfc="none", mew=2.2)
    ax_tooth.annotate("1 inch ≈ 1 h\n(OoM sanity)", (25, np.interp(25, d.section_mm, d.bake_time_h)),
                      textcoords="offset points", xytext=(8, -6), fontsize=8.2, color=blue)
    ax_tooth.annotate("500 mm → ~10 days\n(load-bearing anchor)", (500, np.interp(500, d.section_mm, d.bake_time_h)),
                      textcoords="offset points", xytext=(-6, 8), ha="right", fontsize=8.2, color=warn)
    ax_tooth.set_xlabel("section thickness (mm)")
    ax_tooth.set_ylabel("dehydrogenation time (h)")
    ax_tooth.set_title("Coherence tooth — bake time ∝ section²\nreproduces cited practice (pinned D_H, no tuning)",
                       fontsize=10.2)
    ax_tooth.grid(True, which="both", alpha=0.25)

    # --- bottom-right: the cited input — D_H Arrhenius ------------------------- #
    from .hydrogen_flaking import DEFAULT_BAKE_TEMP_C as hf_bake
    ax_arr.semilogy(d.arrhenius_T, d.arrhenius_D, color=blue, lw=2.4)
    D_bake = float(np.interp(hf_bake, d.arrhenius_T, d.arrhenius_D))
    ax_arr.plot([hf_bake], [D_bake], "o", color=warn, ms=10, zorder=5)
    ax_arr.annotate(f"ferritic bake\n{hf_bake:.0f} °C", (hf_bake, D_bake), textcoords="offset points",
                    xytext=(-10, -2), ha="right", fontsize=8.4, color=warn)
    D_room = float(np.interp(25.0, d.arrhenius_T, d.arrhenius_D))
    ax_arr.plot([25.0], [D_room], "o", color="0.3", ms=8, zorder=5)
    ax_arr.annotate(f"room-T anchor\n~{D_room:.1e} m²/s", (25.0, D_room), textcoords="offset points",
                    xytext=(10, 6), fontsize=8.0, color="0.3")
    ax_arr.set_xlabel("temperature (°C)")
    ax_arr.set_ylabel("hydrogen diffusivity in α-Fe (m²/s)")
    ax_arr.set_title("The cited input: lattice D_H (α-Fe)\npinned to the room-T value — independent of bake practice",
                     fontsize=10.2)
    ax_arr.grid(True, which="both", alpha=0.25)

    fig.suptitle("Hydrogen flaking — the dissolved-H consequence: same ladle H, the section decides",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.90, bottom=0.08, wspace=0.24, hspace=0.34)
    return fig


def refining_figure(d):
    """The F2 artifact: the tap-chemistry panel — deoxidation curve, C–O coupling, degassing, propagation.

    ``d`` is a :class:`~steel.demo_refining.RefiningDemo` (already-computed arrays/scalars — this layer only
    draws them, ADR 0002). Four panels, the refining story top-left → bottom-right:

    * **top-left — the deoxidation curve (the banked artifact).** Equilibrium dissolved oxygen vs aluminium
      added. The solid line is the real curve with its **minimum** (~0.07 % Al); the dashed line is the
      dilute *cartoon* that monotonically falls — the gap is exactly what the one cited interaction
      coefficient ``e_O^Al`` adds. Silicon sits an order of magnitude above aluminium (the hierarchy).
    * **top-right — the C–O coupling.** Dissolved oxygen vs carbon, the inverse product ``[%C][%O] ≈
      0.0022``: carbon-saturated charge is low-oxygen, the blow lifts oxygen as it drops carbon, the
      over-blow lifts it further (the three process points marked).
    * **bottom-left — vacuum degassing (Sieverts √p).** Hydrogen and nitrogen solubility vs partial
      pressure: the square-root law means the 2 ppm hydrogen flaking limit needs a few-mbar vacuum (marked).
    * **bottom-right — the validated propagation.** Core martensite fraction vs the carbon turndown: aim
      for the grade's carbon and the part clears the soft-core spec; over-blow and the *same* quench falls
      under it. The one refining output the benchmarked back end consumes — a real mistake, a real
      consequence.
    """
    import matplotlib.pyplot as plt

    fig, ((ax_deox, ax_co), (ax_gas, ax_prop)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn = "#c0392b"
    al_color, si_color = "#2471a3", "#16a085"

    # --- top-left: the deoxidation curve with the minimum --------------------- #
    ax_deox.plot(d.al_grid, d.o_vs_al, color=al_color, lw=2.6, label="aluminium (with e_O$^{Al}$)")
    ax_deox.plot(d.al_grid, d.o_vs_al_dilute, color=al_color, lw=1.6, ls="--",
                 label="aluminium (dilute cartoon — no minimum)")
    ax_deox.plot(d.al_grid, d.o_vs_al_si, color=si_color, lw=2.2, label="silicon")
    ax_deox.plot([d.al_min], [d.o_min], "o", mfc="white", mec=warn, ms=11, mew=2.2, zorder=6)
    ax_deox.annotate(f"minimum\n[Al] ≈ {d.al_min:.3f} % → {d.o_min:.1f} ppm\n(over-kill RAISES O)",
                     (d.al_min, d.o_min), textcoords="offset points", xytext=(26, 6), fontsize=8.4,
                     color=warn, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=warn, lw=1.0))
    ax_deox.set_yscale("log")
    ax_deox.set_xlabel("aluminium added  (wt %)")
    ax_deox.set_ylabel("equilibrium dissolved oxygen  (ppm)")
    ax_deox.set_title("Deoxidation curve — [O] vs Al, and the minimum the cartoon misses", fontsize=10.4)
    ax_deox.grid(True, which="both", alpha=0.22)
    ax_deox.legend(fontsize=8.0, loc="upper right")

    # --- top-right: the C–O coupling ------------------------------------------ #
    ax_co.plot(d.carbon_grid, d.o_vs_carbon, color="0.25", lw=2.4)
    pts = [("hot-metal\ncharge", d.charge_point, "0.45"),
           ("on-spec\nblow", d.target_point, PHASE_COLORS["martensite"]),
           ("over-blow", d.overblow_point, warn)]
    for label, (c, o), color in pts:
        ax_co.plot([c], [o], "o", color=color, ms=10, zorder=5)
        ax_co.annotate(f"{label}\n{c:g} %C → {o:.0f} ppm", (c, o), textcoords="offset points",
                       xytext=(8, -2 if label.startswith('hot') else 10), fontsize=8.0, color=color,
                       ha="left", va="top" if label.startswith('hot') else "bottom")
    ax_co.set_xscale("log")
    ax_co.set_yscale("log")
    ax_co.set_xlabel("carbon  (wt %)")
    ax_co.set_ylabel("equilibrium dissolved oxygen  (ppm)")
    ax_co.set_title("C–O coupling — [%C]·[%O] ≈ 0.0022: blow carbon down, oxygen climbs", fontsize=10.4)
    ax_co.grid(True, which="both", alpha=0.22)

    # --- bottom-left: Sieverts √p degassing ----------------------------------- #
    p_mbar = d.pressure_grid * 1000.0
    ax_gas.plot(p_mbar, d.h_vs_p, color="#8e44ad", lw=2.6, label="hydrogen")
    ax_gas.plot(p_mbar, d.n_vs_p, color="#d68910", lw=2.2, label="nitrogen (solubility limit)")
    ax_gas.axhline(2.0, color=warn, ls="--", lw=1.5)                 # MAX_HYDROGEN_PPM, the flaking spec
    ax_gas.annotate("2 ppm H flaking limit", (p_mbar[-1], 2.0), ha="right", va="bottom",
                    fontsize=8.2, color=warn)
    vac = d.vacuum_for_2ppm * 1000.0
    ax_gas.axvline(vac, color="0.4", ls=":", lw=1.4)
    ax_gas.annotate(f"vacuum to beat flaking\n≈ {vac:.1f} mbar", (vac, d.h_vs_p[0]),
                    textcoords="offset points", xytext=(8, -4), fontsize=8.2, color="0.3", ha="left")
    ax_gas.set_xscale("log")
    ax_gas.set_yscale("log")
    ax_gas.set_xlabel("gas partial pressure  (mbar)")
    ax_gas.set_ylabel("Sieverts solubility  (ppm)")
    ax_gas.set_title("Vacuum degassing — [X] = K·√p: halve H, quarter the pressure", fontsize=10.4)
    ax_gas.grid(True, which="both", alpha=0.22)
    ax_gas.legend(fontsize=8.4, loc="lower right")

    # --- bottom-right: the validated carbon-axis propagation ------------------ #
    ax_prop.plot(d.carbon_axis, d.fM_vs_carbon, color="0.25", lw=2.4, zorder=3)
    ax_prop.axhline(d.spec, color="0.35", ls="--", lw=1.6, zorder=2)
    ax_prop.axhspan(0.0, d.spec, color="#fdecea", alpha=0.6, zorder=0)
    ax_prop.annotate(f"soft-core spec (≥ {d.spec:.0%} martensite)", (0.5, d.spec),
                     xycoords=("axes fraction", "data"), ha="center", va="bottom", fontsize=8.4, color="0.3")
    for label, c, fM, color in [("on-spec\n0.40 %C", 0.40, d.on_spec_fM, PHASE_COLORS["martensite"]),
                                ("over-blown\n0.20 %C", 0.20, d.over_fM, warn)]:
        ax_prop.plot([c], [fM], "o", color=color, ms=11, zorder=5)
        ax_prop.annotate(label, (c, fM), textcoords="offset points", xytext=(0, 12 if color != warn else -30),
                         ha="center", fontsize=8.6, color=color, fontweight="bold")
    ax_prop.set_xlabel("carbon after the blow  (wt %)")
    ax_prop.set_ylabel("core martensite fraction")
    ax_prop.set_ylim(0.0, 1.05)
    ax_prop.set_title("Validated axis — over-blow carbon → soft core (same oil quench)", fontsize=10.4)
    ax_prop.grid(True, alpha=0.25)

    fig.suptitle("F2 — primary refining: the blow sets carbon (validated), and the gas / inclusion fields fill",
                 fontsize=12.4, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.07, hspace=0.28, wspace=0.22)
    return fig


def slag_figure(d):
    """The F2 Slice-2 artifact: slag partition — P out in the converter, S in the ladle, opposite oxygen.

    ``d`` is a :class:`~steel.demo_slag.SlagDemo` (already-computed arrays/scalars — this layer only draws
    them, ADR 0002). Four panels, the partition story top-left → bottom-right:

    * **top-left — dephosphorization, L_P vs basicity (the acid/basic history).** Phosphorus partition (log)
      against slag basicity B = %CaO/%SiO₂. The acid-Bessemer slag sits near ``L_P ≈ 1`` (phosphorus stays —
      the rails that cracked); the basic converter slag lands in the hundreds. The measured BOF band (50–200)
      is the order-of-magnitude benchmark — Healy over-predicts at high lime, named.
    * **top-right — desulfurization, L_S vs metal dissolved oxygen (the deox-first rule).** Sulfur partition
      (log) against the dissolved oxygen the *same* ladle slag sees. At the un-killed blow oxygen L_S is
      single-digit (sulfur barely moves); after the kill it is in the hundreds — *deoxidize before you
      desulfurize*.
    * **bottom-left — the opposite oxygen dependence (the headline tooth).** On one oxidizing-power axis
      (metal dissolved oxygen): L_P **rises** with oxygen (Healy's +2.5·log %Fe_t — dephos oxidizes) while
      L_S **falls** (the −log a_O of the sulfide-capacity partition — desulf reduces). Two independently
      sourced correlations, opposite signs — which is *why* P comes out in the converter and S in the ladle.
    * **bottom-right — the heat through the working route.** Residual phosphorus and sulfur down the chain
      (charge → basic dephos → blow + kill → ladle desulf), with the spec lines — and the two history
      failures' end-points: acid-Bessemer phosphorus retained, and sulfur retained when desulfurized before
      the kill.
    """
    import matplotlib.pyplot as plt

    fig, ((ax_p, ax_s), (ax_x, ax_trail)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn = "#c0392b"
    p_color, s_color = "#b9770e", "#6c3483"

    # --- top-left: L_P vs basicity ------------------------------------------- #
    ax_p.plot(d.B_grid, d.Lp_vs_B, color=p_color, lw=2.6)
    ax_p.axhspan(d.bof_band[0], d.bof_band[1], color="#eaf2f8", alpha=0.9, zorder=0)
    ax_p.annotate("measured BOF\nL_P 50–200", (d.B_grid[-1], d.bof_band[1]), ha="right", va="bottom",
                  fontsize=8.0, color="#2471a3")
    ax_p.axvline(1.0, color="0.6", ls=":", lw=1.3)
    ax_p.annotate("acid ↔ basic", (1.0, d.Lp_vs_B.min()), textcoords="offset points", xytext=(4, 2),
                  fontsize=8.0, color="0.4", ha="left")
    for label, (B, Lp), color in [("acid Bessemer\n(P stays)", d.acid_point, warn),
                                   ("basic converter\n(P out)", d.basic_point, PHASE_COLORS["martensite"])]:
        ax_p.plot([B], [Lp], "o", color=color, ms=11, zorder=5)
        ax_p.annotate(label, (B, Lp), textcoords="offset points",
                      xytext=(8, -2 if color == warn else 8), fontsize=8.2, color=color,
                      ha="left", va="top" if color == warn else "bottom", fontweight="bold")
    ax_p.set_yscale("log")
    ax_p.set_xlabel("slag basicity  B = %CaO / %SiO₂")
    ax_p.set_ylabel("phosphorus partition  L_P = (%P)$_{slag}$ / [%P]")
    ax_p.set_title("Dephosphorization — L_P vs basicity: acid can't, basic can", fontsize=10.4)
    ax_p.grid(True, which="both", alpha=0.22)

    # --- top-right: L_S vs metal dissolved oxygen ----------------------------- #
    ax_s.plot(d.o_grid, d.Ls_vs_o, color=s_color, lw=2.6)
    for label, (O, Ls), color in [("after kill\n(ladle)", d.ladle_o_point, PHASE_COLORS["martensite"]),
                                   ("un-killed blow\n(converter)", d.converter_o_point, warn)]:
        ax_s.plot([O], [Ls], "o", color=color, ms=11, zorder=5)
        ax_s.annotate(label, (O, Ls), textcoords="offset points",
                      xytext=(8, 8 if color != warn else -4), fontsize=8.2, color=color,
                      ha="left", va="bottom" if color != warn else "top", fontweight="bold")
    ax_s.set_xscale("log")
    ax_s.set_yscale("log")
    ax_s.set_xlabel("metal dissolved oxygen  [ppm O]  (the kill state)")
    ax_s.set_ylabel("sulfur partition  L_S = (%S)$_{slag}$ / [%S]")
    ax_s.set_title("Desulfurization — L_S vs oxygen: deoxidize FIRST", fontsize=10.4)
    ax_s.grid(True, which="both", alpha=0.22)

    # --- bottom-left: the opposite oxygen dependence (shared oxygen axis) ------ #
    ax_x.plot(d.contrast_o, d.Lp_contrast, color=p_color, lw=2.8, label="L_P (dephos) — rises ⇒ oxidizing")
    ax_x.plot(d.contrast_o, d.Ls_contrast, color=s_color, lw=2.8, label="L_S (desulf) — falls ⇒ reducing")
    ax_x.annotate("more oxidizing →", (0.5, 0.03), xycoords="axes fraction", ha="center", fontsize=8.4,
                  color="0.4")
    ax_x.set_xscale("log")
    ax_x.set_yscale("log")
    ax_x.set_xlabel("oxidizing power  —  metal dissolved oxygen [ppm]  (slag FeO ⟷ [O], Fe–FeO)")
    ax_x.set_ylabel("partition ratio  L")
    ax_x.set_title("Opposite oxygen dependence — why P goes in the converter, S in the ladle", fontsize=10.0)
    ax_x.grid(True, which="both", alpha=0.22)
    ax_x.legend(fontsize=8.4, loc="center left")

    # --- bottom-right: residual P / S through the working route ---------------- #
    x = np.arange(len(d.steps))
    w = 0.38
    ax_trail.bar(x - w / 2, d.p_trail, w, color=p_color, label="phosphorus")
    ax_trail.bar(x + w / 2, d.s_trail, w, color=s_color, label="sulfur")
    ax_trail.axhline(sg_max_p(), color=p_color, ls="--", lw=1.3, alpha=0.7)
    ax_trail.axhline(sg_max_s(), color=s_color, ls="--", lw=1.3, alpha=0.7)
    ax_trail.annotate(f"P spec {sg_max_p():.3f}", (len(d.steps) - 1, sg_max_p()), ha="right", va="bottom",
                      fontsize=7.6, color=p_color)
    # The history failures' retained levels, as ghosted end-bars beyond the route.
    ax_trail.plot([len(d.steps) - 1 + 0.0], [d.acid_p], "v", color=warn, ms=11, zorder=6)
    ax_trail.annotate(f"acid Bessemer\nP {d.acid_p:.3f} (retained)", (len(d.steps) - 1, d.acid_p),
                      textcoords="offset points", xytext=(-6, 6), fontsize=8.0, color=warn, ha="right")
    ax_trail.plot([len(d.steps) - 1], [d.early_s], "^", color="#7d3c98", ms=11, zorder=6)
    ax_trail.annotate(f"desulf-before-kill\nS {d.early_s:.3f} (retained)", (len(d.steps) - 1, d.early_s),
                      textcoords="offset points", xytext=(-6, -22), fontsize=8.0, color="#7d3c98", ha="right")
    ax_trail.set_xticks(x)
    ax_trail.set_xticklabels(d.steps, fontsize=8.2)
    ax_trail.set_yscale("log")
    ax_trail.set_ylabel("residual content  (wt %)")
    ax_trail.set_title("The heat through the route — P and S driven below spec", fontsize=10.4)
    ax_trail.grid(True, which="both", axis="y", alpha=0.22)
    ax_trail.legend(fontsize=8.4, loc="upper right")

    fig.suptitle("F2 Slice 2 — slag partition: phosphorus out in the converter, sulfur in the ladle "
                 "(opposite oxygen)", fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.08, hspace=0.30, wspace=0.22)
    return fig


def sg_max_p():
    from .slag import MAX_PHOSPHORUS_PCT
    return MAX_PHOSPHORUS_PCT


def sg_max_s():
    from .slag import MAX_SULFUR_PCT
    return MAX_SULFUR_PCT


def impurity_window_figure(d):
    """The impurity-consequence artifact: P (cold-short) + S (red-short) bracket the workable window.

    ``d`` is a :class:`~steel.demo_impurity_window.ImpurityDemo` (precomputed — this layer only draws,
    ADR 0002). Four panels, the same high-P/high-S pig iron made cracking (acid) vs sound (basic + Mushet):

    * **top-left — phosphorus → cold-shortness (the PROPAGATION).** DBTT vs phosphorus along the shared
      normalize baseline, crossing the service temperature at ``P*``; yield (twin axis) climbs with P — the
      signed foil's "stronger" half. The acid heat sits brittle and strong to the right, the basic heat
      ductile to the left.
    * **top-right — sulfur → red-shortness (the NEW consumer).** Free sulfur vs Mn:S, vanishing at Mushet's
      stoichiometric 1.71 (the historical-coherence anchor — by construction, not a tooth). Right of the line
      the steel is sound at the forge; left, free FeS tears the grain boundaries.
    * **bottom-left — the signed-impurity foil.** On the yield–DBTT plane, adding phosphorus pushes up-AND-right
      (stronger *and* more brittle); refining the grain pushes up-AND-left (the lone co-improver, §5b).
    * **bottom-right — the workable temperature window.** Each heat on a temperature axis: brittle below its
      DBTT (the service/toughness end), red-short above the 988 °C Fe–FeS eutectic when sulfur is free (the
      hot-working end). The off-spec heat is squeezed from both ends; the clean heat is wide open.
    """
    import matplotlib.pyplot as plt

    fig, ((ax_p, ax_s), (ax_foil, ax_win)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn = "#c0392b"
    good = PHASE_COLORS["martensite"]
    p_color, s_color = "#b9770e", "#6c3483"
    y_color = "#1f6f8b"

    # --- top-left: P → DBTT (cold-short), with yield on a twin axis (the foil) ----------------- #
    ax_p.axhspan(d.service_T, d.dbtt_vs_P.max() + 20.0, color="#fdEDEC", alpha=0.8, zorder=0)
    ax_p.plot(d.P_grid, d.dbtt_vs_P, color=p_color, lw=2.8, label="DBTT (P-aware Pickering)")
    ax_p.axhline(d.service_T, color="0.5", ls=":", lw=1.4)
    ax_p.annotate(f"service {d.service_T:+.0f} °C — above ⇒ brittle", (d.P_grid[-1], d.service_T),
                  ha="right", va="bottom", fontsize=8.0, color="0.4")
    ax_p.axvline(d.P_star, color=p_color, ls="--", lw=1.2, alpha=0.7)
    ax_p.annotate(f"cold-short\nonset P*≈{d.P_star:.3f}", (d.P_star, d.dbtt_vs_P.min()),
                  textcoords="offset points", xytext=(6, 4), fontsize=8.0, color=p_color, ha="left")
    for c, color, va in [(d.acid, warn, "top"), (d.basic, good, "bottom")]:
        ax_p.plot([c.P], [c.dbtt_C], "o", color=color, ms=11, zorder=6)
        ax_p.annotate(f"{c.label.split(',')[0]}\nDBTT {c.dbtt_C:+.0f} °C", (c.P, c.dbtt_C),
                      textcoords="offset points", xytext=(8, -2 if va == "top" else 8),
                      fontsize=8.2, color=color, ha="left", va=va, fontweight="bold")
    ax_yld = ax_p.twinx()
    ax_yld.plot(d.P_grid, d.yield_vs_P, color=y_color, lw=2.0, ls="-.", alpha=0.85)
    ax_yld.set_ylabel("yield strength  σ_y  (MPa)", color=y_color, fontsize=9.0)
    ax_yld.tick_params(axis="y", labelcolor=y_color)
    ax_yld.annotate("yield ↑ with P\n(strengthens)", (d.P_grid[-1], d.yield_vs_P[-1]),
                    textcoords="offset points", xytext=(-6, -28), fontsize=7.8, color=y_color, ha="right")
    ax_p.set_xlabel("phosphorus  (wt %)")
    ax_p.set_ylabel("DBTT  (°C)", color=p_color)
    ax_p.set_title("Phosphorus → cold-shortness (propagation through Pickering DBTT)", fontsize=10.0)
    ax_p.grid(True, alpha=0.22)

    # --- top-right: free S vs Mn:S (red-short), the Mushet threshold ---------------------------- #
    ax_s.axvspan(0.0, d.mushet_ratio, color="#fdEDEC", alpha=0.7, zorder=0)
    ax_s.plot(d.ratio_grid, d.freeS_vs_ratio, color=s_color, lw=2.8)
    ax_s.axvline(d.mushet_ratio, color=s_color, ls="--", lw=1.5)
    ax_s.annotate(f"Mushet Mn:S = {d.mushet_ratio:.2f}\n(all S → MnS)", (d.mushet_ratio, d.freeS_vs_ratio.max()),
                  textcoords="offset points", xytext=(8, -6), fontsize=8.2, color=s_color, ha="left", va="top",
                  fontweight="bold")
    ax_s.annotate("free FeS\n→ red-short", (d.mushet_ratio * 0.45, d.freeS_vs_ratio.max() * 0.6),
                  fontsize=8.4, color=warn, ha="center")
    for c, color in [(d.acid, warn), (d.basic, good)]:
        ratio = c.Mn / c.S if c.S > 0 else 4.0
        ax_s.plot([min(ratio, d.ratio_grid[-1])], [c.free_S], "o", color=color, ms=11, zorder=6)
        ax_s.annotate(f"{c.label.split(',')[0]}\nMn:S {ratio:.1f}", (min(ratio, d.ratio_grid[-1]), c.free_S),
                      textcoords="offset points", xytext=(-6 if color == good else 8, 10),
                      fontsize=8.2, color=color, ha="right" if color == good else "left", fontweight="bold")
    ax_s.set_xlabel("manganese-to-sulfur ratio  Mn:S  (by weight)")
    ax_s.set_ylabel("free sulfur  (wt %)  → FeS")
    ax_s.set_title("Sulfur → red-shortness (new hot-work consumer; Mushet threshold)", fontsize=10.0)
    ax_s.grid(True, alpha=0.22)

    # --- bottom-left: the signed-impurity foil on the yield–DBTT plane -------------------------- #
    y0, t0 = d.foil_baseline
    dyP, dtP = d.foil_P_arrow
    dyG, dtG = d.foil_grain_arrow
    ax_foil.annotate("", xy=(y0 + dyP, t0 + dtP), xytext=(y0, t0),
                     arrowprops=dict(arrowstyle="-|>", color=p_color, lw=2.6))
    ax_foil.annotate("", xy=(y0 + dyG, t0 + dtG), xytext=(y0, t0),
                     arrowprops=dict(arrowstyle="-|>", color=good, lw=2.6))
    ax_foil.plot([y0], [t0], "o", color="0.3", ms=9, zorder=6)
    ax_foil.annotate("+phosphorus\nstronger AND brittler", (y0 + dyP, t0 + dtP), textcoords="offset points",
                     xytext=(6, 4), fontsize=8.6, color=p_color, ha="left", fontweight="bold")
    ax_foil.annotate("refine grain\nstronger AND tougher\n(the lone co-improver)", (y0 + dyG, t0 + dtG),
                     textcoords="offset points", xytext=(6, -6), fontsize=8.6, color=good, ha="left",
                     va="top", fontweight="bold")
    ax_foil.axhline(d.service_T, color="0.6", ls=":", lw=1.2)
    # annotate() arrows do not drive autoscale — set limits to frame the baseline and both arrow tips.
    xs = [y0, y0 + dyP, y0 + dyG]
    ys = [t0, t0 + dtP, t0 + dtG]
    xpad = max(8.0, 0.18 * (max(xs) - min(xs)))
    ypad = max(8.0, 0.22 * (max(ys) - min(ys)))
    ax_foil.set_xlim(min(xs) - xpad, max(xs) + xpad * 2.2)
    ax_foil.set_ylim(min(ys) - ypad * 1.5, max(ys) + ypad)
    ax_foil.set_xlabel("yield strength  σ_y  (MPa)")
    ax_foil.set_ylabel("DBTT  (°C)   ↑ = more brittle")
    ax_foil.set_title("The signed-impurity foil — P embrittles while it strengthens", fontsize=10.0)
    ax_foil.grid(True, alpha=0.22)

    # --- bottom-right: the workable temperature window ------------------------------------------ #
    T_lo, T_hi = -120.0, 1320.0
    rows = [(d.basic, 1, good), (d.acid, 0, warn)]
    for c, y, _ in rows:
        # brittle (below DBTT) — the service/toughness end
        ax_win.broken_barh([(T_lo, c.dbtt_C - T_lo)], (y - 0.32, 0.64), facecolors="#f1948a", edgecolor="none")
        # red-short (above the eutectic) when sulfur is free — the hot-working end
        if c.red_short:
            ax_win.broken_barh([(d.eutectic_C, T_hi - d.eutectic_C)], (y - 0.32, 0.64),
                               facecolors="#f5b041", edgecolor="none")
            workable_hi = d.eutectic_C
        else:
            workable_hi = T_hi
        # the workable window between
        ax_win.broken_barh([(c.dbtt_C, workable_hi - c.dbtt_C)], (y - 0.32, 0.64),
                           facecolors="#abebc6", edgecolor="none")
        ax_win.annotate(c.label.split(",")[0], (T_lo + 20, y), va="center", ha="left", fontsize=8.6,
                        fontweight="bold")
    ax_win.axvline(d.service_T, color="0.25", ls=":", lw=1.6)
    ax_win.annotate("room T", (d.service_T, 1.5), rotation=90, fontsize=7.8, color="0.25", va="top", ha="right")
    ax_win.axvline(d.eutectic_C, color=warn, ls="--", lw=1.4)
    ax_win.annotate(f"Fe–FeS eutectic {d.eutectic_C:.0f} °C", (d.eutectic_C, -0.5), rotation=90, fontsize=7.8,
                    color=warn, va="bottom", ha="right")
    ax_win.axvline(d.forge_temp_C, color="0.25", ls=":", lw=1.2)
    ax_win.annotate("forge", (d.forge_temp_C, 1.5), rotation=90, fontsize=7.8, color="0.25", va="top", ha="left")
    # legend swatches
    from matplotlib.patches import Patch
    ax_win.legend(handles=[Patch(facecolor="#f1948a", label="brittle (below DBTT)"),
                           Patch(facecolor="#abebc6", label="workable"),
                           Patch(facecolor="#f5b041", label="red-short (free S, hot)")],
                  fontsize=7.8, loc="lower right", framealpha=0.9)
    ax_win.set_ylim(-0.7, 1.7)
    ax_win.set_yticks([])
    ax_win.set_xlim(T_lo, T_hi)
    ax_win.set_xlabel("temperature  (°C)")
    ax_win.set_title("The workable window — P caps the cold end, S the hot end", fontsize=10.0)
    ax_win.grid(True, axis="x", alpha=0.22)

    fig.suptitle("Closing the impurity consequences — phosphorus (cold-short) and sulfur (red-short)",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.93, top=0.92, bottom=0.08, hspace=0.30, wspace=0.26)
    return fig


def temper_embrittlement_figure(d):
    """The temper-embrittlement artifact: the martensitic-P consequence and the four levers that defeat it.

    ``d`` is a :class:`~steel.demo_temper_embrittlement.TemperEmbrittleDemo` (precomputed — this layer only
    draws, ADR 0002). Four panels:

    * **top-left — J-factor susceptibility ranking.** Watanabe `(Mn+Si)(P+Sn)·10⁴` for the registry plus the
      dirty Ni-Cr victim; the threshold line separates susceptible from clean. Mo-bearing bars are marked —
      composition susceptibility, with the cure flagged.
    * **top-right — the danger window and the cooling-rate control.** Temperature vs time: the embrittling
      window (375–575 °C, nose 490–550) and the ≥600 °C reset band shaded; a slow cool dwells in the window
      (embrittles) while a fast cool passes through (safe).
    * **bottom-left — the four levers.** One susceptible heat, four independent saves: fast cool, molybdenum,
      a clean heat, or a reheat — each turns the verdict from embrittled (red) to tough (green).
    * **bottom-right — reversibility.** The cycle that names the phenomenon: slow-cool → embrittled, reheat
      >600 °C + fast cool → tough, slow-cool again → embrittled.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch

    fig, ((ax_j, ax_win), (ax_lev, ax_rev)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn = "#c0392b"
    good = PHASE_COLORS["martensite"]
    amber = "#d68910"

    # --- top-left: J-factor susceptibility ranking ------------------------------------------- #
    labels = [r[0] for r in d.ranking]
    Js = [r[1] for r in d.ranking]
    mos = [r[2] for r in d.ranking]
    ypos = np.arange(len(labels))
    colors = [(amber if mo else warn) if J >= d.j_threshold else good for J, mo in zip(Js, mos)]
    ax_j.barh(ypos, Js, color=colors, edgecolor="0.3", zorder=3)
    ax_j.axvline(d.j_threshold, color="0.3", ls="--", lw=1.5, zorder=4)
    ax_j.annotate(f"susceptible →\nJ > {d.j_threshold:.0f}", (d.j_threshold, 0.4),
                  textcoords="offset points", xytext=(6, 0), fontsize=8.0, color="0.3", va="center")
    for y, (J, mo) in enumerate(zip(Js, mos)):
        if mo:
            ax_j.annotate("Mo cure", (J, y), textcoords="offset points", xytext=(-6, 0), ha="right",
                          va="center", fontsize=7.4, color="white", fontweight="bold")
    ax_j.set_yticks(ypos)
    ax_j.set_yticklabels(labels, fontsize=8.4)
    ax_j.set_xlabel("J-factor  (Mn+Si)(P+Sn)·10⁴")
    ax_j.set_title("Susceptibility ranking — dirty Ni-Cr (no Mo) is the victim", fontsize=10.2)
    ax_j.grid(True, axis="x", alpha=0.22)

    # --- top-right: the danger window + slow/fast cooling paths ------------------------------- #
    t = np.linspace(0.0, 10.0, 200)
    T0, Tenv = 680.0, 250.0
    slow = Tenv + (T0 - Tenv) * np.exp(-t / 6.0)        # gentle cool — dwells in the window
    fast = Tenv + (T0 - Tenv) * np.exp(-t / 0.7)        # steep quench — passes through
    ax_win.axhspan(d.window[0], d.window[1], color="#fadbd8", zorder=0)
    ax_win.axhspan(d.nose[0], d.nose[1], color="#f1948a", zorder=0)
    ax_win.axhspan(d.de_embrittle_T, 720.0, color="#d5f5e3", zorder=0)
    ax_win.annotate(f"danger window\n{d.window[0]:.0f}–{d.window[1]:.0f} °C", (9.8, sum(d.window) / 2),
                    ha="right", va="center", fontsize=8.0, color=warn)
    ax_win.annotate(f"reset > {d.de_embrittle_T:.0f} °C", (5.5, 655.0), ha="center", va="center",
                    fontsize=8.0, color=good)
    ax_win.plot(t, slow, color=warn, lw=2.8, label="slow cool — dwells → embrittles")
    ax_win.plot(t, fast, color=good, lw=2.8, label="fast cool — passes → safe")
    ax_win.set_xlabel("time (arb.)")
    ax_win.set_ylabel("temperature (°C)")
    ax_win.set_ylim(220.0, 720.0)
    ax_win.set_title("The cooling-rate control — cool fast through the window", fontsize=10.2)
    ax_win.legend(fontsize=8.0, loc="upper right")
    ax_win.grid(True, alpha=0.18)

    # --- bottom-left: the four levers ---------------------------------------------------------- #
    lev_labels = [l for l, _ in d.levers]
    lev_emb = [e for _, e in d.levers]
    ly = np.arange(len(lev_labels))[::-1]               # first lever on top
    for y, (lab, emb) in zip(ly, d.levers):
        ax_lev.barh(y, 1.0, color=warn if emb else good, edgecolor="0.3", zorder=3)
        ax_lev.annotate("EMBRITTLED" if emb else "tough", (0.5, y), ha="center", va="center",
                        fontsize=9.0, color="white", fontweight="bold")
    ax_lev.set_yticks(ly)
    ax_lev.set_yticklabels(lev_labels, fontsize=8.2)
    ax_lev.set_xlim(0.0, 1.0)
    ax_lev.set_xticks([])
    ax_lev.set_title("Four levers on ONE susceptible heat — any one saves it", fontsize=10.2)

    # --- bottom-right: the reversibility cycle ------------------------------------------------- #
    ax_rev.set_xlim(0.0, 1.0)
    ax_rev.set_ylim(0.0, 1.0)
    ax_rev.axis("off")
    ax_rev.set_title("Reversible — reheat resets it", fontsize=10.2)
    xs = [0.18, 0.5, 0.82]
    ys = [0.78, 0.30, 0.78]
    for (lab, emb), x, y in zip(d.cycle, xs, ys):
        ax_rev.annotate(("EMBRITTLED\n" if emb else "TOUGH\n") + lab, (x, y), ha="center", va="center",
                        fontsize=8.2, color="white", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.4", fc=warn if emb else good, ec="0.3"))
    for (x0, y0), (x1, y1) in (((xs[0], ys[0]), (xs[1], ys[1])), ((xs[1], ys[1]), (xs[2], ys[2]))):
        ax_rev.add_patch(FancyArrowPatch((x0, y0 - 0.12), (x1, y1 + 0.12), arrowstyle="-|>",
                                         mutation_scale=16, color="0.4", lw=1.8,
                                         connectionstyle="arc3,rad=-0.2"))
    ax_rev.annotate("reheat > 600 °C\n+ fast cool", (0.34, 0.50), fontsize=7.8, color=good, ha="center")
    ax_rev.annotate("slow-cool again", (0.66, 0.50), fontsize=7.8, color=warn, ha="center")

    fig.suptitle("Temper embrittlement — the reversible, alloy-driven phosphorus consequence (martensitic P)",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.16, right=0.97, top=0.92, bottom=0.08, hspace=0.32, wspace=0.28)
    return fig


def tempered_martensite_embrittlement_figure(d):
    """The tempered-martensite-embrittlement artifact: the OTHER tempering trough — carbon-driven, irreversible.

    ``d`` is a :class:`~steel.demo_tempered_martensite_embrittlement.TMEDemo` (precomputed — this layer only
    draws, ADR 0002). Four panels:

    * **top-left — the trough on the temper axis.** The hardened victim's verdict across temper temperature: the
      cited TME trough (260–370 °C) shaded red, the > ~400 °C recovery green, and the *sibling* reversible-TE
      window (375–575 °C) marked amber for orientation. The verdict step fills exactly the trough — the model
      tracks the cited window (by construction, not a tooth).
    * **top-right — the two gates.** At a 300 °C temper: 4140 / 1080 embrittle; 8620 (0.20 %C) stays tough even
      fully hardened (carbon gate); a plain-carbon section that did not harden is immune (martensitic gate).
    * **bottom-left — irreversibility.** Temper 300 → embrittled, temper 450 → recovered, re-enter 300 → stays
      tough. One-way: the carbide morphology is set by the peak temper.
    * **bottom-right — reversible ↔ irreversible.** The contrast table: the sibling re-embrittles on cycling,
      this does not — same axis, opposite character.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch

    fig, ((ax_axis, ax_disc), (ax_cyc, ax_con)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn = "#c0392b"
    good = PHASE_COLORS["martensite"]
    amber = "#d68910"

    # --- top-left: the trough on the temper axis ------------------------------------------------ #
    Ts = [T for T, _ in d.axis_map]
    emb = [1.0 if e else 0.0 for _, e in d.axis_map]
    ax_axis.axvspan(d.window[0], d.window[1], color="#fadbd8", zorder=0)
    ax_axis.axvspan(d.recovery_T, Ts[-1], color="#d5f5e3", zorder=0)
    ax_axis.axvspan(d.reversible_window[0], d.reversible_window[1], facecolor="#fdebd0", zorder=0, hatch="//",
                    edgecolor="#e8c39e")
    ax_axis.fill_between(Ts, emb, step="mid", color=warn, alpha=0.85, zorder=3, label="TME — embrittled")
    ax_axis.step(Ts, emb, where="mid", color=warn, lw=1.6, zorder=4)
    ax_axis.annotate(f"TME trough\n{d.window[0]:.0f}–{d.window[1]:.0f} °C\n(irreversible)",
                     (sum(d.window) / 2, 0.55), ha="center", va="center", fontsize=8.2, color=warn,
                     fontweight="bold")
    ax_axis.annotate(f"recovered\n> {d.recovery_T:.0f} °C", ((d.recovery_T + Ts[-1]) / 2, 0.22), ha="center",
                     va="center", fontsize=8.0, color=good)
    ax_axis.annotate("reversible-TE\nwindow (sibling —\ndifferent mechanism)", (sum(d.reversible_window) / 2, 0.80),
                     ha="center", va="center", fontsize=7.2, color="#9c640c")
    ax_axis.set_xlim(Ts[0], Ts[-1])
    ax_axis.set_ylim(0.0, 1.15)
    ax_axis.set_yticks([0.0, 1.0])
    ax_axis.set_yticklabels(["tough", "embrittled"], fontsize=8.4)
    ax_axis.set_xlabel("temper temperature (°C)")
    ax_axis.set_title(f"Hardened {d.victim_name} ({d.victim_C:.2f} %C) — the trough on the temper axis",
                      fontsize=10.0)
    ax_axis.grid(True, axis="x", alpha=0.2)

    # --- top-right: the two gates (carbon + hardenability) -------------------------------------- #
    dl = d.discriminator
    dy = np.arange(len(dl))[::-1]                       # first case on top
    for y, (lab, C, M, e) in zip(dy, dl):
        ax_disc.barh(y, 1.0, color=warn if e else good, edgecolor="0.3", zorder=3)
        ax_disc.annotate(("EMBRITTLED" if e else "tough") + f"\n{M:.0%} M", (0.5, y), ha="center", va="center",
                         fontsize=8.4, color="white", fontweight="bold")
    ax_disc.set_yticks(dy)
    ax_disc.set_yticklabels([lab for lab, *_ in dl], fontsize=8.0)
    ax_disc.set_xlim(0.0, 1.0)
    ax_disc.set_xticks([])
    ax_disc.set_title("Two gates at a 300 °C temper — carbon AND a hardened structure", fontsize=10.0)

    # --- bottom-left: the irreversibility cycle ------------------------------------------------- #
    ax_cyc.set_xlim(0.0, 1.0)
    ax_cyc.set_ylim(0.0, 1.0)
    ax_cyc.axis("off")
    ax_cyc.set_title("Irreversible — the peak temper sets it (one-way)", fontsize=10.0)
    xs = [0.18, 0.5, 0.82]
    ys = [0.74, 0.30, 0.74]
    for (lab, e), x, y in zip(d.cycle, xs, ys):
        ax_cyc.annotate(("EMBRITTLED\n" if e else "TOUGH\n") + lab, (x, y), ha="center", va="center",
                        fontsize=8.0, color="white", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.4", fc=warn if e else good, ec="0.3"))
    for (x0, y0), (x1, y1) in (((xs[0], ys[0]), (xs[1], ys[1])), ((xs[1], ys[1]), (xs[2], ys[2]))):
        ax_cyc.add_patch(FancyArrowPatch((x0, y0 - 0.12), (x1, y1 + 0.12), arrowstyle="-|>",
                                         mutation_scale=16, color="0.4", lw=1.8,
                                         connectionstyle="arc3,rad=-0.2"))
    ax_cyc.annotate("over-temper\n> 400 °C", (0.34, 0.50), fontsize=7.8, color=good, ha="center")
    ax_cyc.annotate("re-enter trough\n→ stays tough", (0.66, 0.50), fontsize=7.8, color=good, ha="center")

    # --- bottom-right: reversible ↔ irreversible contrast --------------------------------------- #
    ax_con.set_xlim(0.0, 1.0)
    ax_con.set_ylim(0.0, 1.0)
    ax_con.axis("off")
    ax_con.set_title("Reversible (sibling)  vs  tempered-martensite (here)", fontsize=10.0)
    x_aspect, x_rev, x_tme = 0.02, 0.40, 0.74
    y0, dyrow = 0.86, 0.135
    ax_con.text(x_rev, y0 + 0.07, "reversible TE", fontsize=8.4, fontweight="bold", color="#9c640c", ha="left")
    ax_con.text(x_tme, y0 + 0.07, "TME", fontsize=8.4, fontweight="bold", color=warn, ha="left")
    for i, (aspect, rev, tme_) in enumerate(d.contrast):
        y = y0 - i * dyrow
        ax_con.text(x_aspect, y, aspect, fontsize=7.8, color="0.25", ha="left", fontweight="bold")
        ax_con.text(x_rev, y, rev, fontsize=7.6, color="0.2", ha="left")
        ax_con.text(x_tme, y, tme_, fontsize=7.6, color="0.2", ha="left")
        if i:
            ax_con.axhline(y + 0.5 * dyrow, xmin=0.0, xmax=1.0, color="0.85", lw=0.7)

    fig.suptitle("Tempered-martensite embrittlement — the irreversible, carbon-driven tempering trough",
                 fontsize=12.0, fontweight="bold")
    fig.subplots_adjust(left=0.17, right=0.975, top=0.92, bottom=0.08, hspace=0.32, wspace=0.30)
    return fig


def ladle_figure(d):
    """The F3 artifact: alloy to grade — the trim, the recovery shortfall, and the front-to-back verdict.

    ``d`` is a :class:`~steel.demo_ladle.LadleDemo` (already-computed arrays/scalars — this layer only draws
    them, ADR 0002). Four panels, the ladle story top-left → bottom-right:

    * **top-left — alloy to grade (the banked artifact).** Per-element bars (Cr, Mo, Mn, Si) for the lean
      tap, the on-grade trim, and the under-recovered heat, each against the **cited 4140 window band**
      (shaded). The on-grade bars land in the bands; the under-recovered Cr/Mo bars fall *below* the floor.
    * **top-right — the recovery shortfall (the failure mechanism).** Landed chromium vs the bath's actual
      Cr/Mo recovery (as a fraction of the assumed): the additions were sized for full recovery, so a bath
      that under-delivers lands short — below the window floor (shaded off-grade region), the two operating
      points marked.
    * **bottom-left — the validated propagation.** Core martensite fraction vs the *landed* chromium: the
      same oil quench clears the soft-core spec on grade and falls under it when Cr is short. The window
      floor (vertical) sits *above* the soft-core crossing — off-grade is the conservative early warning.
    * **bottom-right — the verdict.** Martensite and hardness for the on-grade vs under-trimmed heat, with
      the flags each carries: one ladle mistake → off-grade (F3) **and** soft-core (back end).
    """
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ((ax_bars, ax_rec), (ax_prop, ax_verdict)) = plt.subplots(2, 2, figsize=(13.5, 9.6))
    warn, good_c = "#c0392b", PHASE_COLORS["martensite"]
    band_c = "#d5e8d4"

    # --- top-left: the trim bars vs the cited window bands -------------------- #
    x = np.arange(len(d.bar_elements))
    w = 0.26
    for i in range(len(d.bar_elements)):                                  # the window band behind each group
        ax_bars.add_patch(plt.Rectangle((x[i] - 0.42, d.window_lo[i]), 0.84, d.window_hi[i] - d.window_lo[i],
                                        facecolor=band_c, edgecolor="#82b366", lw=1.0, zorder=0))
    ax_bars.bar(x - w, d.bars_tap, w, label="lean tap", color="0.7", zorder=3)
    ax_bars.bar(x, d.bars_good, w, label="on-grade trim", color=good_c, zorder=3)
    ax_bars.bar(x + w, d.bars_bad, w, label="under-recovered", color=warn, zorder=3)
    ax_bars.set_xticks(x)
    ax_bars.set_xticklabels(d.bar_elements)
    ax_bars.set_ylabel("content  (wt %)")
    ax_bars.set_title("Alloy to grade — trim the lean tap into the 4140 window", fontsize=10.4)
    ax_bars.legend(fontsize=8.4, loc="upper right")
    ax_bars.grid(True, axis="y", alpha=0.22)
    ax_bars.annotate("4140 window\n(SAE J404)", (x[0] - 0.42, d.window_hi[0]), textcoords="offset points",
                     xytext=(2, 4), fontsize=7.6, color="#5a8a3c")

    # --- top-right: landed Cr vs the actual recovery ------------------------- #
    rr = d.recovery_ratio * 100.0
    ax_rec.axhspan(0.0, d.cr_floor, color="#fdecea", alpha=0.7, zorder=0)
    ax_rec.plot(rr, d.cr_vs_recovery, color="0.25", lw=2.4, zorder=3)
    ax_rec.axhline(d.cr_floor, color=warn, ls="--", lw=1.5, zorder=2)
    ax_rec.annotate(f"4140 Cr floor ({d.cr_floor:.2f} %) — below ⇒ off grade", (rr[-1], d.cr_floor),
                    ha="right", va="bottom", fontsize=8.2, color=warn)
    for label, (ratio, cr, _fM), color in [("on-grade", d.good_point, good_c),
                                            ("under-recovered", d.bad_point, warn)]:
        ax_rec.plot([ratio * 100.0], [cr], "o", color=color, ms=11, zorder=5)
        ax_rec.annotate(f"{label}\nCr {cr:.2f} %", (ratio * 100.0, cr), textcoords="offset points",
                        xytext=(6, -2 if color == warn else 8), fontsize=8.2, color=color,
                        ha="left", va="top" if color == warn else "bottom")
    ax_rec.set_xlabel("actual Cr/Mo recovery  (% of the assumed yield the trim was sized for)")
    ax_rec.set_ylabel("landed chromium  (wt %)")
    ax_rec.set_title("Recovery shortfall — size for one yield, deliver another → short", fontsize=10.4)
    ax_rec.grid(True, alpha=0.22)

    # --- bottom-left: martensite vs the landed Cr (the validated propagation) - #
    ax_prop.axhline(d.spec, color="0.35", ls="--", lw=1.6, zorder=2)
    ax_prop.axhspan(0.0, d.spec, color="#fdecea", alpha=0.55, zorder=0)
    ax_prop.annotate(f"soft-core spec (≥ {d.spec:.0%} M)", (0.5, d.spec), xycoords=("axes fraction", "data"),
                     ha="center", va="bottom", fontsize=8.4, color="0.3")
    ax_prop.axvline(d.cr_floor, color=warn, ls=":", lw=1.6, zorder=2)
    ax_prop.annotate("4140 Cr floor", (d.cr_floor, 0.05), textcoords="offset points", xytext=(5, 0),
                     fontsize=8.0, color=warn, ha="left")
    ax_prop.plot(d.cr_vs_recovery, d.fM_vs_recovery, color="0.25", lw=2.4, zorder=3)
    for label, (_r, cr, fM), color in [("on-grade", d.good_point, good_c),
                                       ("under-recovered", d.bad_point, warn)]:
        ax_prop.plot([cr], [fM], "o", color=color, ms=11, zorder=5)
        ax_prop.annotate(label, (cr, fM), textcoords="offset points", xytext=(0, 12 if color == good_c else -28),
                         ha="center", fontsize=8.6, color=color, fontweight="bold")
    ax_prop.set_xlabel("landed chromium  (wt %)")
    ax_prop.set_ylabel("core martensite fraction")
    ax_prop.set_ylim(0.0, 1.05)
    ax_prop.set_title("Validated axis — under-trim Cr → soft core (same oil quench)", fontsize=10.4)
    ax_prop.grid(True, alpha=0.25)

    # --- bottom-right: the two-flag verdict --------------------------------- #
    groups = ["on-grade", "under-recovered"]
    xv = np.arange(len(groups))
    fM = [d.good_fM, d.bad_fM]
    colors = [good_c, warn]
    bars = ax_verdict.bar(xv, fM, 0.5, color=colors, zorder=3)
    ax_verdict.axhline(d.spec, color="0.35", ls="--", lw=1.6, zorder=2)
    ax_verdict.annotate(f"≥ {d.spec:.0%} martensite spec", (1.0, d.spec), xycoords=("axes fraction", "data"),
                        ha="right", va="bottom", fontsize=8.2, color="0.3")
    flag_text = ["through-hardens\non grade ✓", f"off-grade + soft-core\n{d.bad_HV:.0f} HV vs {d.good_HV:.0f}"]
    for bar, val, txt, color in zip(bars, fM, flag_text, colors):
        ax_verdict.annotate(f"{val:.0%} M\n{txt}", (bar.get_x() + bar.get_width() / 2, val),
                            textcoords="offset points", xytext=(0, 6), ha="center", va="bottom",
                            fontsize=8.4, color=color, fontweight="bold")
    ax_verdict.set_xticks(xv)
    ax_verdict.set_xticklabels(groups)
    ax_verdict.set_ylim(0.0, 1.15)
    ax_verdict.set_ylabel("core martensite fraction")
    ax_verdict.set_title("One mistake, two flags — F3 off-grade + back-end soft core", fontsize=10.4)
    ax_verdict.grid(True, axis="y", alpha=0.22)

    fig.suptitle("F3 — ladle trim: the alloy goes in, and recovery decides whether the heat lands on grade",
                 fontsize=12.4, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.07, hspace=0.30, wspace=0.22)
    return fig
