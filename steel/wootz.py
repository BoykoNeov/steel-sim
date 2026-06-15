"""Wootz / Damascus carbide banding — the **signed good-impurity foil**: the trace element that *makes* the steel.

The mirror image of every other impurity story in the chain. Phosphorus (cold-short), sulfur (red-short),
the elongated MnS stringer (:mod:`steel.sulfide_morphology`) are all **bad** impurities — a clean-steel spec
wants them *gone*. Wootz is the inverse: the watered Damascus pattern needs a **trace carbide-forming
"impurity"** — chiefly **vanadium** — that a modern clean-steel spec would reject as off-spec pickup, yet the
wootz smith *requires*. So "bad steel" and "good steel" are the same statement read with opposite signs:
**off-spec composition, signed either way** (``steel-making.md`` §14.5 / §15.4 — the one genuine front-end
physics gap, now filled).

The physics — three gates, all required (Verhoeven & Pendray 1998)
-----------------------------------------------------------------
The Damascus surface pattern is **carbide banding**: alternating sheets of clustered proeutectoid cementite
(Fe₃C) and near-carbide-free steel, ~30–70 µm apart. It develops only when **all three** of the following hold;
remove any one and the bar comes out plain:

1. **Hypereutectoid carbon** — wootz is an ultra-high-carbon steel (1.0–1.8 wt %, typically ~1.5 %), well above
   the eutectoid (:data:`steel.fe_c.C_EUTECTOID` = 0.76 %). Only then is there a **proeutectoid cementite
   network** to organise into bands (reused from :func:`steel.fe_c.equilibrium_constituents`). A plain
   medium-carbon bar has no excess carbide and cannot pattern, whatever its trace chemistry.
2. **A trace carbide-former above threshold** — **V ≥ ~40 ppmw** (0.004 wt %; ~100 ppmw acts as the nucleation
   agent), or the less-potent **Mn ≥ ~200 ppmw**; **Mo** is, with V, the *most effective* of the formers
   (V, Mo, Cr, Mn, Nb). These segregate to the interdendritic regions on freezing and, on reheating, either
   nucleate cementite or stop it dissolving — so the carbide preferentially sits in the solute-rich bands.
   Below threshold the carbide stays dispersed: a modern *clean* ultra-high-carbon steel, forged identically,
   shows **no pattern**.
3. **Cyclic forging in the carbide-stable window** — repeated thermal cycling to a peak **50–100 °C below
   A_cm** (the cementite solvus, :func:`steel.fe_c.Acm`), ~6–8 cycles, to develop and sharpen the bands.
   Forge too hot (above A_cm the proeutectoid cementite dissolves and the segregation memory is erased) or
   skip the cycling, and the pattern never forms.

The mechanism is **microsegregation** — and that is where this build reuses, with the opposite sign, the very
engine that makes segregation a *defect* elsewhere in the chain.

The reuse beat — the same Scheil engine, opposite sign (by construction, NOT a coherence note)
---------------------------------------------------------------------------------------------
:mod:`steel.casting` rejects solute into the last liquid to freeze (Scheil) and hands the **centerline-enriched**
composition to the back end, where it over-hardens into a crack-prone band — segregation as a **defect**. This
module reads the *same* Scheil solid-segregation ratio (:func:`steel.casting.segregation_ratio`) for the
carbide-former, at the same interdendritic last-to-freeze fraction — and that enrichment is the **asset**: it is
what aligns the cementite into the Damascus bands. One engine, read two ways. Because wootz is hypereutectoid
(C ≫ the 0.53 % peritectic carbon), its primary solidification is **γ-austenite**, so the γ partition
coefficients are the right ones (the named ceiling :mod:`steel.casting` flags for its own δ-mode demonstrators).
This is **one number fed to the mechanism, by construction** — like "one MnS, two opposite signs" — not two
independent constructions agreeing, so it is **not** dressed as a coherence note or a tooth.

The honest posture — a thin consumer, NO claimable tooth
-------------------------------------------------------
Standalone, **no engine touch, no ADR** — like :mod:`steel.sulfide_morphology`. The map:

* **By construction (NOT teeth).** The three gates are cited threshold lines (like ``MIN_MARTENSITE_SPEC``): the
  V/Mn ppm thresholds and the 50–100 °C-below-A_cm forging window are **Verhoeven & Pendray's measured
  numbers**, used as given; the proeutectoid-cementite fraction is :mod:`steel.fe_c`'s lever rule; the
  interdendritic enrichment is :mod:`steel.casting`'s Scheil. The relative effectiveness of the formers is
  taken **directly from the two cited thresholds** (40 ppm V ≈ 200 ppm Mn ⇒ Mn counts at ~0.2× V; Mo counts
  with V as a most-effective former) — it is **not** derived from segregation coefficients (effectiveness is
  carbide-forming thermodynamics, not how strongly an element microsegregates; Mn's ``k`` is unremarkable).
* **The band spacing is a cited observation, NOT a prediction.** The measured Damascus band spacing (30–70 µm)
  and the fact that it traces the interdendritic (secondary-dendrite-arm) spacing are **two consistent cited
  facts** — Verhoeven's metallography plus the independent fact that SDAS in a slow-cooled crucible cake is
  tens of µm. This module **does not compute** a spacing from a solidification time and call the match a
  prediction: the cake modulus, the Chvorinov constant, and the SDAS correlation are all soft knobs aimed at a
  2×-wide target, which would be a manufactured coherence. The range is reported as a label, nothing more.
* **The interdendritic-enrichment ratio is REPRESENTATIVE.** It is shown via the repo's already-pinned former
  (**Mo**, ``k_γ`` = 0.70 from :mod:`steel.casting`) as the segregation exemplar; V behaves the same way
  (``k`` < 1) but the repo does not separately pin ``k_V``, so the *amplitude* is the Mo stand-in, ranking /
  order-of-magnitude only — never a benchmarked band-to-matrix contrast.

The flag — off-spec by *lacking* a good impurity (gated on INTENT, never re-deriving another flag)
-------------------------------------------------------------------------------------------------
The signed-foil consequence: a heat **forged as wootz** (hypereutectoid *and* cycled correctly in the A_cm
window) that comes out **plain** because its trace former was below threshold raises **``wootz-pattern-failed``**
— "the smith did everything right; the ore lacked the vanadium." A plain bar forged normally never intended a
pattern and reads **clean** (the intent gate — the model of :mod:`steel.sulfide_morphology`'s plain heat). The
gate is the **trace-former threshold**, which is genuinely novel physics here (it collapses into no other flag
in the chain), so gating on it is correct — unlike the sulfur case, where gating on an S-threshold would have
re-derived red-shortness.

**Inert in the back end.** Trace V/Mo at 40–270 ppmw are invisible to the hardenability / hardness models
(they are not even in the :class:`~steel.sweep.Steel` vector — they are passed as keyword inputs here), so a
patterned heat heat-treats byte-identically to a plain one: the pattern reads state, it moves no composition.

**Named ceiling.** The pattern is a **yes/no** verdict on whether the bands develop, not a rendered etch
figure or a quantitative band *sharpness* / contrast curve (the cycle-count → sharpness evolution, "clear after
6–8 cycles", is a threshold, not a kinetic model). The forging window is the cited 50–100 °C-below-A_cm band,
not a carbide-dissolution kinetics calculation. Carbon is read **nominal** (Scheil over-predicts interstitial C
— :mod:`steel.casting`'s ceiling); the segregation is the **substitutional** former's. Units: wt % for carbon,
**ppmw** for the trace formers, °C for temperature, µm for band spacing.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import casting, fe_c
from .heat_state import Heat, ProcessStep, add_defect
from .sweep import Steel

# --------------------------------------------------------------------------- #
# Cited thresholds (Verhoeven & Pendray 1998, JOM 50(9):58) — by-construction lines, NOT teeth
# --------------------------------------------------------------------------- #
# Vanadium is THE key carbide-former for Damascus banding. ≥ 40 ppmw is "quite effective" at producing the
# bands of clustered Fe₃C; ~100 ppmw acts as the nucleation agent. Genuine blades ran <10–270 ppmw V (Table IV).
V_BANDING_MIN_PPM: float = 40.0
V_NUCLEATION_PPM: float = 100.0
# Manganese is a *weaker* former: banding is induced only at ~200 ppmw — 5× the V threshold. This 40-vs-200
# ratio is Verhoeven's cited relative effectiveness, used directly (NOT derived from partition coefficients).
MN_BANDING_MIN_PPM: float = 200.0

# Wootz is ultra-high-carbon. Below the eutectoid there is no proeutectoid cementite to band — so the carbon
# gate is simply "hypereutectoid", reusing fe_c's eutectoid composition.
HYPEREUTECTOID_MIN_C: float = fe_c.C_EUTECTOID   # 0.76 wt %

# The cyclic-forging window: a peak temperature 50–100 °C BELOW A_cm (the cementite solvus). Hotter than
# A_cm − 50 risks dissolving the proeutectoid cementite (erasing the segregation memory); the band is the
# carbide-stable forging range Verhoeven cycled through. Cited offsets, °C below A_cm.
FORGE_BELOW_ACM_MIN_C: float = 50.0
FORGE_BELOW_ACM_MAX_C: float = 100.0
# The bands "begin to develop after a few cycles and become clear after 6–8 cycles" — the cited cycle floor.
MIN_FORGING_CYCLES: int = 6

# The measured Damascus band spacing (µm) — a CITED metallographic observation (Zschokke swords 42/46/50 µm),
# reported as a label. It traces the interdendritic / secondary-dendrite-arm spacing; it is NOT computed here.
BAND_SPACING_MIN_UM: float = 30.0
BAND_SPACING_MAX_UM: float = 70.0

# The interdendritic last-to-freeze solid fraction at which the carbide-former enrichment is read — the same
# centerline fraction casting.py uses for its (opposite-signed) segregation defect.
FS_INTERDENDRITIC: float = casting.FS_CENTERLINE   # 0.95

# The defect flag this stage raises — a wootz-intent heat that came out PLAIN because its trace carbide-former
# was below threshold. The signed-impurity miss: off-spec by *lacking* a good impurity. Distinct from every
# other (bad-impurity) flag in the chain.
WOOTZ_PATTERN_FAILED: str = "wootz-pattern-failed"


def effective_carbide_former_ppm(v_ppm: float = 0.0, mo_ppm: float = 0.0, mn_ppm: float = 0.0) -> float:
    """The **V-equivalent** effective carbide-former level (ppmw) for banding — a cited-threshold weighting.

    Verhoeven & Pendray: vanadium and molybdenum are the *most effective* formers, manganese a weaker one
    (banding needs ~200 ppmw Mn vs ~40 ppmw V). So V and Mo count at full weight and Mn at the cited
    ``V_BANDING_MIN_PPM / MN_BANDING_MIN_PPM`` ≈ 0.2× — the relative effectiveness read **straight off the two
    cited thresholds**, never derived from segregation coefficients. By construction; not a tooth.

    **Assumption (named, not cited):** the contributions are taken **additive** (a sub-threshold V plus a
    sub-threshold Mn can together clear the line). The *weights* are cited; that they *add* is a modeling
    choice Verhoeven does not speak to — fine for a by-construction gate, but flagged so it is not mistaken for
    cited. The genuine-wootz hero is V-only, so nothing rides on the additivity today.
    """
    mn_weight = V_BANDING_MIN_PPM / MN_BANDING_MIN_PPM
    return max(0.0, v_ppm) + max(0.0, mo_ppm) + max(0.0, mn_ppm) * mn_weight


def former_sufficient_for_banding(v_ppm: float = 0.0, mo_ppm: float = 0.0, mn_ppm: float = 0.0) -> bool:
    """Whether the trace carbide-former clears the cited V banding threshold (the second gate)."""
    return effective_carbide_former_ppm(v_ppm, mo_ppm, mn_ppm) >= V_BANDING_MIN_PPM


def proeutectoid_cementite_pct(C: float) -> float:
    """Proeutectoid cementite fraction (%) available to band — :mod:`steel.fe_c`'s lever rule (by construction).

    Zero below the eutectoid (no excess carbide); for hypereutectoid wootz it is the carbide network the bands
    organise. Reused from :func:`steel.fe_c.equilibrium_constituents` — not re-derived here.
    """
    if C <= HYPEREUTECTOID_MIN_C:
        return 0.0
    return 100.0 * fe_c.equilibrium_constituents(C).f_proeutectoid


def former_interdendritic_enrichment(fs: float = FS_INTERDENDRITIC) -> float:
    """Interdendritic carbide-former enrichment ratio (C_band / C_nominal) — the segregation MECHANISM display.

    The same Scheil solid-segregation ratio :func:`steel.casting.segregation_ratio` that makes centerline
    segregation a *defect*, read for the carbide-former at the interdendritic last-to-freeze fraction — here it
    is the *asset* that aligns the cementite into bands (one engine, opposite sign). Shown via the repo's
    already-pinned former (**Mo**, ``k_γ`` = 0.70) as the exemplar, in the **γ** phase (wootz is hypereutectoid,
    so primary solidification is austenitic). REPRESENTATIVE / order-of-magnitude — V segregates the same way
    (``k`` < 1) but ``k_V`` is not separately pinned; this is not a benchmarked contrast.
    """
    k_mo_gamma = casting.partition_coefficient("Mo", "gamma")
    return casting.segregation_ratio(k_mo_gamma, fs)


def forging_window(C: float) -> tuple[float, float]:
    """The cyclic-forging temperature window (°C) for a hypereutectoid carbon ``C`` — 50–100 °C below A_cm.

    ``(A_cm − 100, A_cm − 50)`` with A_cm the cementite solvus (:func:`steel.fe_c.Acm`). Raises ``ValueError``
    for a non-hypereutectoid carbon (A_cm is undefined below the eutectoid — there is no wootz window).
    """
    if C <= HYPEREUTECTOID_MIN_C:
        raise ValueError(f"forging window is defined only for hypereutectoid C > {HYPEREUTECTOID_MIN_C} wt%, got {C}")
    acm = fe_c.Acm(C)
    return acm - FORGE_BELOW_ACM_MAX_C, acm - FORGE_BELOW_ACM_MIN_C


@dataclass(frozen=True)
class WootzPattern:
    """The carbide-banding verdict — did the Damascus pattern develop, and if not, why.

    ``carbon_pct`` the bulk carbon; ``hypereutectoid`` whether it clears the eutectoid (gate 1) and
    ``proeutectoid_cementite_pct`` the carbide network available to band; ``v_ppm`` / ``mo_ppm`` / ``mn_ppm``
    the trace formers, ``effective_former_ppm`` their V-equivalent sum and ``former_sufficient`` whether it
    clears the V banding threshold (gate 2); ``former_enrichment`` the interdendritic enrichment ratio (the
    Scheil mechanism display); ``acm_C`` the cementite solvus and ``forge_peak_C`` / ``forge_cycles`` the
    forging, ``forged_in_window`` whether the cycling met the window-and-cycle-count condition (gate 3);
    ``forged_as_wootz`` whether the *intent* was a pattern (hypereutectoid + correctly forged);
    ``patterned`` the verdict (all three gates); ``band_spacing_um`` the cited (NOT computed) spacing range;
    ``pattern_failed`` the flag condition — forged as wootz but the trace former fell short.
    """

    carbon_pct: float
    hypereutectoid: bool
    proeutectoid_cementite_pct: float
    v_ppm: float
    mo_ppm: float
    mn_ppm: float
    effective_former_ppm: float
    former_sufficient: bool
    former_enrichment: float
    acm_C: float | None
    forge_peak_C: float | None
    forge_cycles: int
    forged_in_window: bool
    forged_as_wootz: bool
    patterned: bool
    band_spacing_um: tuple[float, float]
    pattern_failed: bool

    @property
    def verdict(self) -> str:
        """A one-line human reading (used by the demo and the process trail)."""
        if self.patterned:
            return (f"Damascus pattern develops — {self.proeutectoid_cementite_pct:.0f} % proeutectoid cementite "
                    f"banded by {self.effective_former_ppm:.0f} ppm carbide-former (×{self.former_enrichment:.1f} "
                    f"interdendritic), bands ~{self.band_spacing_um[0]:.0f}–{self.band_spacing_um[1]:.0f} µm")
        if self.pattern_failed:
            return (f"NO pattern — forged as wootz but only {self.effective_former_ppm:.0f} ppm carbide-former "
                    f"(< {V_BANDING_MIN_PPM:.0f} ppm V threshold): clean ore, the cementite stays dispersed")
        if not self.hypereutectoid:
            return (f"no pattern — {self.carbon_pct:.2f} %C is not hypereutectoid (< {HYPEREUTECTOID_MIN_C:.2f} %): "
                    f"no proeutectoid cementite to band")
        return ("no pattern — not forged as wootz (hypereutectoid steel, but not cycled in the "
                f"{self._window_str()} window)")

    def _window_str(self) -> str:
        if self.acm_C is None:
            return "A_cm"
        lo, hi = self.acm_C - FORGE_BELOW_ACM_MAX_C, self.acm_C - FORGE_BELOW_ACM_MIN_C
        return f"{lo:.0f}–{hi:.0f} °C"


def wootz_assessment(
    C: float,
    *,
    v_ppm: float = 0.0,
    mo_ppm: float = 0.0,
    mn_ppm: float = 0.0,
    forge_peak_C: float | None = None,
    forge_cycles: int = 0,
) -> WootzPattern:
    """Resolve the carbide-banding verdict for a carbon level, trace chemistry, and forging schedule (the physics).

    The three gates: (1) **hypereutectoid carbon** → a proeutectoid cementite network (``fe_c`` lever rule);
    (2) the **trace carbide-former** clears the cited V banding threshold (:func:`former_sufficient_for_banding`);
    (3) **cyclic forging** with ``forge_cycles`` ≥ :data:`MIN_FORGING_CYCLES` and ``forge_peak_C`` inside the
    50–100 °C-below-A_cm window (:func:`forging_window`). The pattern develops only if all three hold. The
    interdendritic enrichment (the Scheil mechanism display) is reported either way. ``forge_peak_C=None`` (the
    default) means "not forged as wootz" — no pattern intent, so a plain bar reads clean.
    """
    hyper = C > HYPEREUTECTOID_MIN_C
    cementite_pct = proeutectoid_cementite_pct(C)
    eff = effective_carbide_former_ppm(v_ppm, mo_ppm, mn_ppm)
    sufficient = eff >= V_BANDING_MIN_PPM
    enrichment = former_interdendritic_enrichment()

    acm = fe_c.Acm(C) if hyper else None
    if hyper and forge_peak_C is not None:
        lo, hi = forging_window(C)
        forged_in_window = (lo <= forge_peak_C <= hi) and (forge_cycles >= MIN_FORGING_CYCLES)
    else:
        forged_in_window = False

    forged_as_wootz = hyper and forged_in_window
    patterned = forged_as_wootz and sufficient
    pattern_failed = forged_as_wootz and not sufficient

    return WootzPattern(
        carbon_pct=C,
        hypereutectoid=hyper,
        proeutectoid_cementite_pct=cementite_pct,
        v_ppm=v_ppm,
        mo_ppm=mo_ppm,
        mn_ppm=mn_ppm,
        effective_former_ppm=eff,
        former_sufficient=sufficient,
        former_enrichment=enrichment,
        acm_C=acm,
        forge_peak_C=forge_peak_C,
        forge_cycles=forge_cycles,
        forged_in_window=forged_in_window,
        forged_as_wootz=forged_as_wootz,
        patterned=patterned,
        band_spacing_um=(BAND_SPACING_MIN_UM, BAND_SPACING_MAX_UM),
        pattern_failed=pattern_failed,
    )


def wootz_pattern_check(
    heat: Heat,
    *,
    v_ppm: float = 0.0,
    mo_ppm: float = 0.0,
    mn_ppm: float = 0.0,
    forge_peak_C: float | None = None,
    forge_cycles: int = 0,
) -> Heat:
    """Forge the ``Heat`` as wootz and read whether the Damascus pattern develops — the signed good-impurity seam.

    The orchestrator (mirror of :func:`steel.sulfide_morphology.sulfide_morphology_check`): it reads the Heat's
    carbon, takes the trace carbide-former and forging schedule as keyword inputs (V/Mo/Mn are *not* in the
    :class:`~steel.sweep.Steel` vector — they are below the back end's resolution), and reports whether the
    pattern formed (:func:`wootz_assessment`). It raises the **wootz-pattern-failed** flag **only** when the heat
    was *forged as wootz* (hypereutectoid and correctly cycled) but the trace former fell short — the signed
    miss, off-spec by lacking a good impurity. A patterned heat, or a plain bar never forged as wootz, raises
    **no** flag. Returns a *new* ``Heat`` with one ``"wootz"`` :class:`~steel.heat_state.ProcessStep` appended;
    composition is unchanged (the pattern reads state, it moves no composition).
    """
    a = wootz_assessment(
        heat.composition.C, v_ppm=v_ppm, mo_ppm=mo_ppm, mn_ppm=mn_ppm,
        forge_peak_C=forge_peak_C, forge_cycles=forge_cycles,
    )
    defects = add_defect(heat.defects, WOOTZ_PATTERN_FAILED) if a.pattern_failed else heat.defects
    flags_added = (WOOTZ_PATTERN_FAILED,) if (a.pattern_failed and not heat.has_defect(WOOTZ_PATTERN_FAILED)) else ()
    summary = f"forge as wootz (V {v_ppm:g} ppm, Mo {mo_ppm:g} ppm, Mn {mn_ppm:g} ppm): {a.verdict}"
    # in_spec: a forged-as-wootz heat passes when the pattern develops; a heat not forged as wootz spec-checks
    # nothing (None) — it never intended a pattern.
    in_spec = a.patterned if a.forged_as_wootz else None
    step = ProcessStep("wootz", summary, in_spec=in_spec, flags_added=flags_added)
    return heat.evolve(step, defects=defects)
