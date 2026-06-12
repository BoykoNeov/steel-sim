"""Cross-composition validation of the cited bainite kinetics against the IT atlas (§20).

*Does a cited composition factor predict bainite kinetics ACROSS steels — or is the project's
"per-steel only" honesty forced?* This module is the **validation study** that answers it with
data, not assertion. It widens the austempering probe's **two**-steel cross-composition negative
([[bainite-anchoring-probe]], :mod:`austemper`) to **eight** atlas steels and tests three *cited*
Li/KV composition factors — bainite ``BC``, pearlite ``PC``, ferrite ``FC`` — as cross-steel
predictors of the measured bainite 50 %-line. No engine is touched; nothing here feeds the frozen
pipeline. It **reads** the cited factors out of :mod:`kinetics` and grades them against the atlas.

THE OBSERVABLE. Each steel's **bainite 50 %-transformation time at 371.1 °C (700 °F)** — the same
austempering-window point the two existing anchors use (1080 = 70.6 s, 4340 = 391 s, both cited in
:mod:`austemper`). 371.1 °C sits strictly inside ``Mₛ < T < Bs`` for all eight (verified), so the
50 %-line there is genuinely bainitic, not martensite/pearlite. The six new times were read off the
1951 atlas's faint dotted 50 %-line at native scan resolution; they carry **~factor-2** uncertainty
(:data:`READ_UNCERTAINTY`). That is coarse for *magnitudes* but the cross-steel spread is ~30×, so
**ranking is robust** — the register every claim here is stated in (Spearman ρ + order-of-magnitude),
never number-matching ([[di-crosscheck-source]] "read the SHAPE").

THE MODEL-FAITHFUL PREDICTION. For the separable site-saturation reaction ``dU/dt = K(T)·g(U)`` the
isothermal time to 50 % is ``t = S(0.5)/K(T)``; ``K`` is linear in the global scale, so a prediction
anchored on ONE steel is ``t̂(s) = t_atlas(anchor)·K(anchor)/K(s)``. Crucially ``K`` carries the
**per-steel grain size** ``2^(0.41·G)`` (atlas G spans 6→10 ≈ 3× rate) and **per-steel ceiling**
``(Bs − T)`` (Steven–Haynes) — both real cross-steel confounds, both folded in here, not waved away.
Only the **composition factor** is swapped to test a hypothesis: :func:`predicted_t50` runs the
*same* :class:`~steel.kinetics.BainiteReaction` rate with its ``BC`` field replaced by ``PC`` or
``FC`` (a controlled experiment — identical undercooling shape, different composition weighting).

THE HEADLINE IS BIAS-IMMUNE — it rests on the **two cited anchors only** (:func:`cited_anchor_wall`).
1080 and 4340 carry the carefully-read austemper anchor times (70.6 s, 391 s — *not* this study's
reads). Anchor the cited ``BC`` rate on 1080 and predict 4340: ``BC`` says 4340 transforms ~9 s
(**faster** than 1080's 70.6 s); the atlas measures 391 s (**5.5× slower**). So ``BC`` inverts the
cited 1080↔4340 ordering and misses the ratio by **~×40, wrong-signed** — and that ×40 *reproduces*
:mod:`austemper`'s independently-derived 1080/4340 scale gap (≈ 6.8e3 / 1.7e2), which both confirms
the harness and means **no new reads are needed for the wall to be real**.

THE EIGHT-STEEL READS CORROBORATE, THEY DON'T CARRY (see :func:`grade_factors`):
  * **The wall, quantified.** Across all eight, cited ``BC`` ranks the measured 50 %-line at Spearman
    ρ ≈ 0.1 (no cross-steel order skill) — because ``BC``'s carbon coefficient (10.18) dwarfs its
    alloy coefficients (Cr 0.90, Mo 0.36, Ni 0.55), so it orders steels by *carbon* and calls
    plain-carbon 1080 (the **fastest** measured) the most retarded. **Caveat (named, load-bearing):**
    the six non-anchor times were read off the faint dotted 50 %-line *with this hypothesis already
    in hand* (~factor-2, confirmation-bias exposure — :data:`READ_UNCERTAINTY`); 4640 is the most
    marginal (only ~50 °C above ``Mₛ``) and is **not** rested on. The bias-immune cited-anchor result
    above is the claim; these reads only put a number on its size.
  * **No single cited factor combines ranking with magnitude (both metrics anchor-invariant).** On
    *rank skill* (Spearman, the cross-steel-order metric that matters): ``PC`` 0.81 > ``FC`` 0.48 >
    ``BC`` 0.10 — the alloy-weighted diffusional factors order bainite, bainite's own carbon-dominated
    factor does not. On *magnitude spread* (std of log-residual, ×10**std): ``FC`` ~×3.1 is tightest,
    ``BC`` ~×4.6, ``PC`` ~×6.7 widest — but ``BC``'s is small only because it is nearly **flat** (it
    barely varies across steels — the no-skill failure mode, consistent with ρ ≈ 0.1), not because it
    tracks. So ``PC`` ranks best but scatters widest, ``FC`` is the most balanced (yet still ρ ≈ 0.48 /
    ~×3), and *none* is a usable cross-steel law — the mechanistic reading is that bainite retardation
    is **alloy-driven**, which ``BC`` under-weights relative to carbon. (Spotlighting ``PC`` as "the
    winner" on rank alone would be a metric cherry-pick — hence both metrics, both anchor-invariant.)
  * **A one-knob refit is a diagnosis, not a new law.** :func:`carbon_rebalance_holdout` fits a SINGLE
    parameter (the carbon-coefficient weight λ) on a train split and predicts a disjoint split — the
    minimal-DOF bound (a 5-coefficient fit on 8 factor-2 points would memorise noise). λ drives to its
    floor (carbon-term removed) and improves the bainite ranking out-of-sample (TEST ρ 0.4 → 0.8).
    :func:`refit_decomposition` shows the gain is carried by the **residual cited alloy coefficients**
    (alloy-only ρ ≈ 0.67 ≫ Bs+grain-only ρ ≈ 0.26), not by the ``Bs``/grain confounds — so the
    diagnosis is "alloy drives it, carbon corrupts it," not a re-tuned coefficient. The carbon/alloy
    axis is **under-identified** here (1080 is the lone no-alloy steel; the low-carbon grades that
    would decorrelate it sit above ``Mₛ`` at 700 °F and were excluded), and ``Bs`` itself absorbs some
    carbon dependence — so the refit is reported as a diagnosis only and grafted into nothing.

CITED vs CALIBRATED. *Cited:* the atlas read-offs (:data:`CROSSCHECK_STEELS`), and the three Li/KV
factors + Steven–Haynes ``Bs`` (all from :mod:`kinetics`, unchanged). *Calibrated:* nothing in the
factors — the only fitted number is the diagnostic λ, which lives in this study and touches no
production path. The verdict **strengthens** the per-steel anchoring of :mod:`austemper` /
:mod:`unified_kv`: it is principled, not a shortcut — no cited single composition law predicts
cross-steel bainite times on this evidence, and the closest one (``PC``) is borrowed, not bainite's.

Run headless (prints the grading table + the holdout):

    python -m steel.demo_cct_validation
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from . import kinetics as kin

# --------------------------------------------------------------------------- #
# 1. The cited atlas read-off table (the cross-composition contract)
# --------------------------------------------------------------------------- #
ATLAS_SOURCE = ("US Steel, Atlas of Isothermal Transformation Diagrams (1951); "
                "archive.org: atlas_of_isothermal_transformation_diagrams")

CROSSCHECK_T = 371.1        # °C = 700 °F — the common austempering-window observable temperature
READ_UNCERTAINTY = 2.0      # the six new 50 %-line reads carry ~factor-2 uncertainty (named)


@dataclass(frozen=True)
class CrossCheckSteel:
    """One atlas steel's cross-composition datum: cited composition + the bainite 50 %-time.

    ``comp`` is the atlas's printed composition (wt%; the keys the Li/KV factors read). ``G`` is the
    atlas ASTM grain size, ``page`` the atlas page. ``Ms_C`` is the read martensite-start (°C, for
    the in-window check). ``t50_700F`` is the measured bainite 50 %-transformation time at
    :data:`CROSSCHECK_T` (s); ``cited`` is ``True`` for the two pre-existing carefully-read anchors
    (1080, 4340 — identical to :data:`steel.austemper.ATLAS_STEELS`) and ``False`` for the six new
    ~factor-2 reads.
    """

    name: str
    comp: dict
    G: float
    page: int
    Ms_C: float
    t50_700F: float
    cited: bool
    note: str = ""


# Eight steels spanning carbon 0.36→0.79 and alloy plain→Ni1.8 — chosen because each shows a
# bainite bay separable at 700 °F (Mₛ < 371.1 °C < Bs, all verified). The 86xx/41xx low-carbon
# grades (8620/8630/4130/4140) are NOT here: their Mₛ ≳ 700 °F, so 371.1 °C is below Mₛ (a
# martensite confound) — they appear in the pearlite-nose discussion (the docstring), not this
# bainite table. The two cited anchors carry the austemper read-offs verbatim.
CROSSCHECK_STEELS: tuple[CrossCheckSteel, ...] = (
    CrossCheckSteel("1080", dict(C=0.79, Mn=0.76), G=6.0, page=42,
                    Ms_C=232.0, t50_700F=70.6, cited=True,
                    note="eutectoid plain carbon — atlas anchor; the FASTEST bainite measured"),
    CrossCheckSteel("4340", dict(C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33), G=7.5, page=105,
                    Ms_C=285.0, t50_700F=391.0, cited=True,
                    note="deep-hardening Ni-Cr-Mo — atlas anchor"),
    CrossCheckSteel("4360", dict(C=0.62, Mn=0.64, Si=0.67, Ni=1.79, Cr=0.60, Mo=0.32), G=7.5, page=106,
                    Ms_C=204.0, t50_700F=2000.0, cited=False,
                    note="high-C high-alloy — slowest (carbon AND alloy agree)"),
    CrossCheckSteel("8660", dict(C=0.59, Mn=0.89, Ni=0.53, Cr=0.64, Mo=0.22), G=8.0, page=115,
                    Ms_C=221.0, t50_700F=700.0, cited=False,
                    note="Ni-Cr-Mo 0.59 C"),
    CrossCheckSteel("4150", dict(C=0.55, Mn=0.60, Ni=0.36, Cr=1.03, Mo=0.19), G=7.5, page=103,
                    Ms_C=249.0, t50_700F=400.0, cited=False,
                    note="4150 Modified — Cr-Mo 0.55 C"),
    CrossCheckSteel("4640", dict(C=0.36, Mn=0.63, Ni=1.84, Mo=0.23), G=7.5, page=108,
                    Ms_C=321.0, t50_700F=500.0, cited=False,
                    note="Ni-Mo 0.36 C — BC calls it FASTEST (low C); atlas measures it SLOW"),
    CrossCheckSteel("6150", dict(C=0.53, Mn=0.67, Cr=0.93), G=9.0, page=112,
                    Ms_C=290.0, t50_700F=150.0, cited=False,
                    note="Cr-V (V absent from all three cited factors)"),
    CrossCheckSteel("6145", dict(C=0.43, Mn=0.74, Cr=0.92), G=8.0, page=111,
                    Ms_C=290.0, t50_700F=100.0, cited=False,
                    note="Cr-V 0.43 C"),
)

CROSSCHECK_BY_NAME = {s.name: s for s in CROSSCHECK_STEELS}
ANCHOR = "1080"             # the single steel every cross-composition prediction is anchored on


# --------------------------------------------------------------------------- #
# 2. The three cited composition factors, and the model-faithful prediction
# --------------------------------------------------------------------------- #
def _factor_value(comp: dict, which: str, carbon_weight: float = 1.0) -> float:
    """The cited Li/KV composition factor for ``which`` ∈ {bainite, pearlite, ferrite} (larger ⇒ slower).

    Reads the *unchanged* :mod:`kinetics` factors. ``carbon_weight`` ≠ 1 only for the refit
    diagnostic (:func:`carbon_rebalance_holdout`): it rescales the **bainite** carbon coefficient,
    leaving the alloy coefficients cited (the minimal-DOF carbon-vs-alloy rebalance).
    """
    C = comp.get("C", 0.0)
    args = {k: comp.get(k, 0.0) for k in ("Mn", "Ni", "Cr", "Mo")}
    if which == "bainite":
        if carbon_weight == 1.0:
            return kin.bainite_BC(C, **args)
        cf = kin.BAINITE_BC_COEFFS
        expo = (cf["const"] + carbon_weight * cf["C"] * C
                + cf["Mn"] * args["Mn"] + cf["Ni"] * args["Ni"]
                + cf["Cr"] * args["Cr"] + cf["Mo"] * args["Mo"])
        return math.exp(expo)
    if which == "pearlite":
        return kin.pearlite_PC(C, Si=comp.get("Si", 0.0), **args)
    if which == "ferrite":
        return kin.ferrite_FC(C, Si=comp.get("Si", 0.0), **args)
    raise ValueError(f"unknown factor {which!r}")


def _bainite_rate_at_obs(steel: CrossCheckSteel, which: str, carbon_weight: float = 1.0) -> float:
    """The Li/KV bainite *rate* ``K`` at :data:`CROSSCHECK_T` with the composition factor swapped to ``which``.

    Reuses the real :meth:`~steel.kinetics.BainiteReaction.rate` (so the per-steel grain size
    ``2^(0.41·G)`` and ceiling ``(Bs − T)¹`` are carried exactly) and replaces only the ``BC`` field
    with the ``which`` factor value — the controlled experiment: same undercooling shape, different
    composition weighting. The global ``scale`` cancels in :func:`predicted_t50`.
    """
    base = kin.bainite_reaction_for_steel(**steel.comp, G=steel.G)   # cited BC + Steven–Haynes Bs
    rxn = base if which == "bainite" and carbon_weight == 1.0 else replace(
        base, BC=_factor_value(steel.comp, which, carbon_weight))
    return rxn.rate(CROSSCHECK_T)


def predicted_t50(steel: CrossCheckSteel, which: str = "bainite",
                  anchor: str = ANCHOR, carbon_weight: float = 1.0) -> float:
    """Predicted bainite 50 %-time (s) at 700 °F, anchored on one steel, via composition factor ``which``.

    ``t̂(steel) = t_atlas(anchor) · K(anchor)/K(steel)`` — the separable-reaction identity. Everything
    cross-steel except the composition factor (``G``, ``Bs``, undercooling) is the real cited rate;
    only ``which`` is the hypothesis under test. By construction ``t̂(anchor) = t_atlas(anchor)``.
    """
    a = CROSSCHECK_BY_NAME[anchor]
    Ks = _bainite_rate_at_obs(steel, which, carbon_weight)
    Ka = _bainite_rate_at_obs(a, which, carbon_weight)
    if Ks <= 0.0:
        return math.inf
    return a.t50_700F * Ka / Ks


# --------------------------------------------------------------------------- #
# 3. Grading: rank the measured 50 %-line against each cited factor
# --------------------------------------------------------------------------- #
def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation ρ — Pearson on the ranks (no scipy needed for one number)."""
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    denom = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    return float((rx * ry).sum() / denom) if denom else float("nan")


@dataclass(frozen=True)
class FactorGrade:
    """How one cited factor ranks/predicts the measured bainite 50 %-line across the eight steels.

    The two metrics are deliberately **both anchor-invariant** (a hostile-reviewer requirement):
    a single global anchor only shifts every log-residual by the same constant, so it cannot change
    the *order* (``spearman``) nor the *spread* (``log_resid_spread``). The earlier anchor-referenced
    "median miss" was dropped precisely because it flipped which factor looked best when re-anchored.
    """

    which: str
    spearman: float                 # rank correlation of predicted vs measured t50 (1 = perfect order); anchor-invariant
    log_resid_spread: float         # std of log10(t̂/t_atlas) over the 8 steels (×10**this); anchor-invariant
    predicted: dict                 # name -> predicted t50 (s), anchored on ANCHOR (the per-steel scatter IS anchored)
    inverts_1080: bool              # True if this factor predicts 1080 (the fastest measured) in the slow half — anchor-invariant


def grade_factor(which: str, anchor: str = ANCHOR, carbon_weight: float = 1.0) -> FactorGrade:
    """Grade composition factor ``which`` as a cross-steel predictor of the measured 50 %-line.

    ``spearman`` and ``log_resid_spread`` are anchor-invariant (the anchor cancels in both rank and
    spread); only the ``predicted`` dict (the per-steel scatter) depends on ``anchor``.
    """
    names = [s.name for s in CROSSCHECK_STEELS]
    measured = np.array([s.t50_700F for s in CROSSCHECK_STEELS])
    pred = {s.name: predicted_t50(s, which, anchor, carbon_weight) for s in CROSSCHECK_STEELS}
    pred_arr = np.array([pred[n] for n in names])

    rho = _spearman(pred_arr, measured)
    log_res = [math.log10(pred[n] / m) for n, m in zip(names, measured)
               if math.isfinite(pred[n]) and pred[n] > 0.0]
    spread = float(np.std(log_res)) if log_res else float("nan")

    # The "wall tell": 1080 is the fastest measured; a carbon-dominated factor predicts it slow.
    # (Predicted order = order of 1/K, anchor-invariant — so this flag is anchor-invariant too.)
    rank_1080 = sorted(names, key=lambda n: pred[n]).index("1080")       # 0 = fastest predicted
    inverts = rank_1080 > len(names) // 2
    return FactorGrade(which, rho, spread, pred, inverts)


def grade_factors(anchor: str = ANCHOR) -> dict:
    """Grade all three cited factors on BOTH metrics — none wins both (``FC`` magnitude, ``PC`` rank)."""
    return {which: grade_factor(which, anchor) for which in ("bainite", "pearlite", "ferrite")}


@dataclass(frozen=True)
class CitedAnchorWall:
    """The bias-immune headline: cited ``BC`` inverts the cited 1080↔4340 ordering (no study reads)."""

    measured_ratio: float           # t50(4340)/t50(1080) measured — > 1 means 4340 SLOWER (atlas: ~5.5)
    bc_ratio: float                 # BC-model t50(4340)/t50(1080) anchored — < 1 means predicted FASTER
    miss: float                     # |log-symmetric| ratio error = measured_ratio / bc_ratio (the ×40)
    sign_inverted: bool             # True if model and atlas disagree on which steel is slower


def cited_anchor_wall() -> CitedAnchorWall:
    """The wall from the two **cited** anchors alone — 1080 & 4340, no factor-2 study reads involved.

    Anchors the cited ``BC`` rate on 1080 and predicts 4340's 50 %-time; compares the predicted
    4340/1080 ratio to the measured one. The atlas measures 4340 *slower* than 1080 (ratio > 1);
    ``BC`` predicts it *faster* (ratio < 1) — a sign inversion whose magnitude (~×40) reproduces
    :mod:`austemper`'s independently-derived 1080/4340 scale gap. This is the claim the headline rests
    on; :func:`grade_factors` only quantifies its spread across the wider (read) set.
    """
    s1080, s4340 = CROSSCHECK_BY_NAME["1080"], CROSSCHECK_BY_NAME["4340"]
    measured_ratio = s4340.t50_700F / s1080.t50_700F
    bc_ratio = predicted_t50(s4340, "bainite", "1080") / s1080.t50_700F
    miss = measured_ratio / bc_ratio
    return CitedAnchorWall(measured_ratio, bc_ratio, miss, sign_inverted=(measured_ratio > 1.0 > bc_ratio))


# --------------------------------------------------------------------------- #
# 4. The minimal-DOF refit attempt (one knob: the carbon-coefficient weight λ)
# --------------------------------------------------------------------------- #
# Composition-balanced train/test split: each half carries plain-carbon, Cr-Mo/Cr-V and Ni-bearing
# steels, so a λ fit on TRAIN is judged on chemistry it did not see. (8 factor-2 points cannot
# support more than one fitted parameter without memorising noise — the advisor's bound.)
REFIT_TRAIN = ("1080", "4340", "8660", "6150")
REFIT_TEST = ("4360", "4150", "4640", "6145")


def _fit_carbon_weight(train: tuple, anchor: str = ANCHOR) -> float:
    """Least-squares-in-log carbon weight λ that best aligns predicted vs measured 50 %-time on ``train``.

    A 1-D scan (the single degree of freedom): for each λ, the median log-residual on the train
    steels; pick the λ minimising the sum of squared log-residuals. λ = 1 is cited ``BC``; λ < 1
    down-weights carbon (the diagnosed bug).
    """
    lams = np.linspace(0.0, 1.5, 151)
    best, best_cost = 1.0, math.inf
    train_steels = [CROSSCHECK_BY_NAME[n] for n in train if n != anchor]
    for lam in lams:
        cost = 0.0
        for s in train_steels:
            p = predicted_t50(s, "bainite", anchor, float(lam))
            if not (math.isfinite(p) and p > 0.0):
                cost = math.inf
                break
            cost += math.log10(p / s.t50_700F) ** 2
        if cost < best_cost:
            best, best_cost = float(lam), cost
    return best


@dataclass(frozen=True)
class RefitHoldout:
    """Out-of-sample result of the one-knob carbon rebalance — does the diagnosis generalise?

    Both scores are anchor-invariant (Spearman rank; std of log-residual), so the BC-vs-refit
    comparison cannot be an artifact of the anchor choice.
    """

    lam: float                      # the fitted carbon weight (1 = cited BC; < 1 = carbon down-weighted)
    test_spearman_bc: float         # cited-BC Spearman on the TEST split (anchor-invariant)
    test_spearman_refit: float      # refit Spearman on the TEST split
    test_spread_bc: float           # cited-BC std of log10-residual on TEST (×10**this; anchor-invariant)
    test_spread_refit: float        # refit std of log10-residual on TEST


def carbon_rebalance_holdout(train: tuple = REFIT_TRAIN, test: tuple = REFIT_TEST,
                             anchor: str = ANCHOR) -> RefitHoldout:
    """Fit λ on ``train``, score cited-``BC`` vs the refit on the disjoint ``test`` split.

    The honest minimal-DOF attempt the user escalated for: one parameter, fit-on-subset /
    predict-disjoint-subset. Reports whether down-weighting carbon improves the bainite ranking
    *out of sample* (both metrics anchor-invariant). A clear improvement locates the bug (carbon
    over-domination); it does **not** license grafting a new law into the engine on eight factor-2
    points (that needs an ADR).
    """
    lam = _fit_carbon_weight(train, anchor)
    test_steels = [CROSSCHECK_BY_NAME[n] for n in test]
    measured = np.array([s.t50_700F for s in test_steels])

    def score(carbon_weight: float):
        pred = np.array([predicted_t50(s, "bainite", anchor, carbon_weight) for s in test_steels])
        rho = _spearman(pred, measured)
        spread = float(np.std([math.log10(p / s.t50_700F)
                               for p, s in zip(pred, test_steels) if math.isfinite(p) and p > 0]))
        return rho, spread

    rho_bc, spread_bc = score(1.0)
    rho_re, spread_re = score(lam)
    return RefitHoldout(lam, rho_bc, rho_re, spread_bc, spread_re)


def refit_decomposition(anchor: str = ANCHOR) -> dict:
    """What carries the carbon-deleted (λ→0) ranking — the residual alloy factor, or the ``Bs``/grain confounds?

    At λ = 0 the bainite rate is ``2^(0.41·G)·(Bs − T)·exp(−Q/RT)/BC_alloy`` with ``BC_alloy`` the
    carbon-free residual (cited Mn/Ni/Cr/Mo coefficients). To attribute the ranking, predict the
    measured 50 %-line with each varying piece *in isolation* (the rest pinned to the anchor's value)
    and report Spearman ρ. The honest verdict turns on whether ``alloy-only`` ≫ ``Bs+grain-only``:
    if so, the alloy composition dependence — not the confounds — carries the cross-steel order, so
    "bainite retardation is alloy-driven, carbon corrupts it" is the right reading.
    """
    a = CROSSCHECK_BY_NAME[anchor]
    Bs_a = kin.steven_haynes_Bs(**{k: a.comp.get(k, 0.0) for k in ("C", "Mn", "Ni", "Cr", "Mo")})
    grain_a = 2.0 ** (0.41 * a.G)
    alloy_a = _factor_value(a.comp, "bainite", carbon_weight=0.0)
    measured = np.array([s.t50_700F for s in CROSSCHECK_STEELS])

    def piece(use_alloy: bool, use_Bs: bool, use_G: bool) -> float:
        times = []                              # predicted 50 %-time ∝ 1/K (the anchor scaling cancels in ρ)
        for s in CROSSCHECK_STEELS:
            Bs = kin.steven_haynes_Bs(**{k: s.comp.get(k, 0.0) for k in ("C", "Mn", "Ni", "Cr", "Mo")})
            grain = 2.0 ** (0.41 * s.G)
            alloy = _factor_value(s.comp, "bainite", carbon_weight=0.0)
            K = ((grain if use_G else grain_a) * ((Bs if use_Bs else Bs_a) - CROSSCHECK_T)
                 / (alloy if use_alloy else alloy_a))
            times.append(1.0 / K)
        return _spearman(np.array(times), measured)

    return {
        "alloy_only": piece(True, False, False),
        "Bs_and_grain_only": piece(False, True, True),
        "Bs_only": piece(False, True, False),
        "grain_only": piece(False, False, True),
    }


# --------------------------------------------------------------------------- #
# 5. In-window self-check (guards the observable: 700 °F must be bainitic for every steel)
# --------------------------------------------------------------------------- #
def in_window(steel: CrossCheckSteel) -> bool:
    """Whether 700 °F sits strictly inside this steel's austempering window ``Mₛ < 371.1 °C < Bs``."""
    Bs = kin.steven_haynes_Bs(**{k: steel.comp.get(k, 0.0) for k in ("C", "Mn", "Ni", "Cr", "Mo")})
    return steel.Ms_C < CROSSCHECK_T < Bs
