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
