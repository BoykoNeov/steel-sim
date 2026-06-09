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
by rule-of-three (ARCHITECTURE.md §6), like :mod:`pathint`.

Requires the optional ``viz`` extra (``pip install -e .[viz]``).
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from . import grain
from .kinetics import CCurve
from .pathint import TransformResult
from .cooling import CoolingPath
from .grain import GrainProperties
from .properties import JominyHardness, RELIABLE_HRC_MIN
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
    ``fractions`` (the validated :meth:`~projects.steel.pathint.TransformResult.fractions`
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

    ``curves`` maps a steel label → its :class:`~projects.steel.properties.JominyHardness`
    traverse (from :func:`~projects.steel.properties.jominy_hardness`). Optional
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

    ``grid`` is the :func:`~projects.steel.sweep.sweep_grid` output — ``grid[i][j]`` is steel
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
    app's :func:`~projects.steel.app.custom_figure` wraps this (the app's discipline forbids
    inventing a figure in ``main()``), and ``steel.ipynb`` §3 draws the same left/right pair.
    Takes the chain **primitives** — ``ccurve`` (the alloy-shifted C-curve), the single
    cooling ``path`` and its ``result`` — *not* a :class:`~projects.steel.sweep.Outcome`, so
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
    vs a hot austenitize) as :class:`~projects.steel.grain.GrainProperties`; ``C`` / ``comp`` the
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
    :class:`~projects.steel.grain.GrainProperties` for the **current** austenitizing (T, t) — is
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
