"""Phase-6d validation: austempering — the atlas-anchored isothermal bainite hold.

The probe (2026-06-10, banked in the plan §13) burned the phase's risk down before the build:
per-steel anchoring of the 6b :class:`BainiteReaction` against the US Steel 1951 atlas PASSES
(~×1.3 — the ΔT¹·Arrhenius temperature shape is genuinely predictive in the austempering band),
cross-composition FAILS ×14–35 wrong-signed (cited ``BC`` says 4340 faster than 1080; the atlas
measures it slower). This suite pins all three verdict legs as the triad:

* **Analytical / structural** — the anchored scale is *derived* from the single cited
  ``(T, t₅₀)`` atlas point (recompute it by hand from the cited rate form); the anchored model
  recovers the anchor exactly; the recipe's stepper agrees with the separable analytic time.
* **THE HOLDOUT TEETH** — anchored at 371.1 °C *only*, the model predicts the 1080 50 %-line at
  the two un-anchored atlas temperatures within ±25 %, and the 4340 begin-line *shape* within
  ×1.35 across 427→371 °C. These are measured numbers the model was never fit to.
* **The documented negative** (the 6b 540-split-test pattern) — the two per-steel anchored scales
  differ ×>10 and the unanchored cross-steel ordering is wrong-signed: there is NO global scale,
  and ``BC`` is never used for absolute cross-steel times.

Plus the recipe invariants: the ``Mₛ < T_hold < Bs`` window guards, short hold → pure KM on the
remainder, long hold → the full-bainite cap (the carbon-only placeholder hardness, named and now
load-bearing), fractions sum to 1 on :mod:`pathint`'s stable key set, the pearlite-race police
(loud near ``Bs``, silent in the anchored band), and everything existing byte-identical (the 6b
demonstration scale and the 540-split untouched — the 6b negative result stays load-bearing).
"""
import math
import warnings

import numpy as np
import pytest

from projects.steel import austemper as au
from projects.steel.kinetics import (
    BAINITE_KINETIC_SCALE, BS_DEFAULT, ABS_ZERO, KV_Q, R_CAL,
    bainite_reaction_for_steel, bainite_BC, steven_haynes_Bs, andrews_Ms,
    koistinen_marburger, ccurve_for_steel, _kv_shape_integral,
)
from projects.steel.properties import vickers_bainite


# --------------------------------------------------------------------------- #
# Analytical / structural: scales derived (not stored), the anchor recovered exactly
# --------------------------------------------------------------------------- #
def test_anchored_model_recovers_the_cited_anchor_exactly():
    # The "recover the constant" leg: the per-steel scale is solved from t50 = S(0.5)/K(T_anchor),
    # so the anchored model's 50 % time at the anchor temperature IS the cited atlas value.
    for name, s in au.ATLAS_STEELS.items():
        t50 = au.hold_time_to_fraction(name, s.T_anchor, au.ATLAS_T50_X)
        assert t50 == pytest.approx(s.t50_anchor, rel=1e-9)


def test_anchored_scales_are_derived_from_the_cited_pieces():
    # Recompute each scale by hand from nothing but cited inputs — the Li/KV rate form
    # K = scale·2^(0.41G)·(Bs−T)·exp(−Q/RT)/BC, the Steven–Haynes Bs, the atlas anchor point —
    # and confirm the import-time derivation matches. No stored magic numbers.
    for name, s in au.ATLAS_STEELS.items():
        comp = dict(s.comp)
        Bs = steven_haynes_Bs(**{el: comp.get(el, 0.0) for el in ("C", "Mn", "Ni", "Cr", "Mo")})
        BC = bainite_BC(**{el: comp.get(el, 0.0) for el in ("C", "Mn", "Ni", "Cr", "Mo")})
        T_K = s.T_anchor + ABS_ZERO
        K_unit = 2.0 ** (0.41 * s.G) * (Bs - s.T_anchor) * math.exp(-KV_Q / (R_CAL * T_K)) / BC
        expected = _kv_shape_integral(au.ATLAS_T50_X) / (K_unit * s.t50_anchor)
        assert au.ANCHORED_SCALES[name] == pytest.approx(expected, rel=1e-12)
    # The probe's derived magnitudes (1080 ≈ 6.8e3, 4340 ≈ 165 on the literature base = 1),
    # quantifying 6b's "absolute times named, not validated" — the KV base is ~10²–10⁴ slow.
    assert au.ANCHORED_SCALES["1080"] == pytest.approx(6.8e3, rel=0.05)
    assert au.ANCHORED_SCALES["4340"] == pytest.approx(165.0, rel=0.05)


def test_atlas_anchor_table_pins_the_cited_facts():
    # The read-off contract: the anchor is an entry of its own 50 %-line table, the atlas line
    # conventions are pinned (begin ≈ 0.1 % transformed, dotted = 50 %), and the compositions/
    # grain sizes are the atlas's (1080 p.42 grain 6; 4340 p.105 grain 7–8 → 7.5).
    assert au.ATLAS_BEGIN_X == 0.001 and au.ATLAS_T50_X == 0.5
    for s in au.ATLAS_STEELS.values():
        assert s.t50[s.T_anchor] == s.t50_anchor
    assert au.ATLAS_STEELS["1080"].comp == dict(C=0.79, Mn=0.76)
    assert au.ATLAS_STEELS["1080"].G == 6.0 and au.ATLAS_STEELS["4340"].G == 7.5
    assert au.ATLAS_STEELS["4340"].comp == dict(C=0.42, Mn=0.78, Ni=1.79, Cr=0.80, Mo=0.33)


def test_recipe_stepper_agrees_with_the_separable_time():
    # The recipe advances U with the existing 6b completion_step; held for exactly the anchored
    # t50 it must sit at U ≈ 0.5 (the same identity the anchoring inverted, now integrated).
    s = au.ATLAS_STEELS["4340"]
    r = au.austemper("4340", s.T_anchor, s.t50_anchor)
    assert r.bainite == pytest.approx(0.5, abs=0.02)


# --------------------------------------------------------------------------- #
# THE HOLDOUT TEETH: anchored at one point, predict the measured rest
# --------------------------------------------------------------------------- #
def test_1080_t50_holdout_within_25_percent():
    # Anchored at 371.1 °C ONLY, predict the 50 %-line at the two other measured temperatures:
    # 343.3 °C → 151 s (lands ×1.06) and 396.7 °C → 38 s (×0.96). The temperature SHAPE
    # (ΔT¹·Arrhenius) is the model's contribution; these numbers were never fit.
    s = au.ATLAS_STEELS["1080"]
    for T, measured in s.t50.items():
        if T == s.T_anchor:
            continue
        predicted = au.hold_time_to_fraction("1080", T, au.ATLAS_T50_X)
        assert predicted == pytest.approx(measured, rel=0.25)


def test_4340_begin_shape_holdout_within_1p35x_over_427_to_371():
    # The begin line is claimed as SHAPE only (time-ratios within the line — the begin→50 %
    # spacing is a named edge, so absolute begin times are not claimed). Anchor the shape at the
    # mid-window 398.9 °C begin point; the predictions at 426.7 and 371.1 °C land within ×1.35.
    s = au.ATLAS_STEELS["4340"]
    T_ref = 398.9
    t_ref = au.hold_time_to_fraction("4340", T_ref, au.ATLAS_BEGIN_X)
    for T in (426.7, 371.1):
        shape_pred = au.hold_time_to_fraction("4340", T, au.ATLAS_BEGIN_X) / t_ref
        shape_meas = s.begin[T] / s.begin[T_ref]
        miss = shape_pred / shape_meas
        assert 1.0 / 1.35 < miss < 1.35
    # The named edges, documented not claimed: toward Bs the shape drifts to ~×0.7 (still the
    # right order), and by 343.3 °C the unmodeled near-Ms acceleration grows the miss to ~×2.3 —
    # exactly why the claim window stops at 427→371 °C.
    for T, lo, hi in ((482.2, 0.5, 1.0), (454.4, 0.5, 1.0), (343.3, 1.5, 3.0)):
        shape_pred = au.hold_time_to_fraction("4340", T, au.ATLAS_BEGIN_X) / t_ref
        shape_meas = s.begin[T] / s.begin[T_ref]
        assert lo < shape_pred / shape_meas < hi


# --------------------------------------------------------------------------- #
# The documented negative: no global scale, BC never cross-steel (the 6b 540-split pattern)
# --------------------------------------------------------------------------- #
def test_per_steel_scales_differ_x40_no_global_scale_exists():
    # The two anchored scales differ ×~41. A single global scale CANNOT serve both steels — the
    # per-steel anchor table is forced, the named discipline step down from 6a's one global knob.
    ratio = au.ANCHORED_SCALES["1080"] / au.ANCHORED_SCALES["4340"]
    assert ratio > 10.0


def test_cited_BC_is_wrong_signed_across_compositions():
    # WHY no global scale exists: at any common scale the cited BC arithmetic says 4340's bainite
    # is FASTER than 1080's (carbon 10.18 dominates BC), while the atlas measures 4340 ~5× SLOWER
    # (t50 391 s vs 70.6 s at 371.1 °C). Wrong-signed ⇒ BC is never used for absolute cross-steel
    # times. (The 6b mechanism teeth — Cr/Mo retard bainite far less than ferrite — survive; what
    # fails is BC's carbon-vs-alloy arithmetic for absolute times.)
    s1080, s4340 = au.ATLAS_STEELS["1080"], au.ATLAS_STEELS["4340"]
    br_1080 = bainite_reaction_for_steel(**s1080.comp, G=s1080.G)   # common demonstration scale
    br_4340 = bainite_reaction_for_steel(**s4340.comp, G=s4340.G)
    T = 371.1
    assert br_4340.rate(T) > br_1080.rate(T)                        # model (any global scale): 4340 faster
    assert s4340.t50[T] > s1080.t50[T]                              # atlas: 4340 slower — wrong-signed


# --------------------------------------------------------------------------- #
# Recipe invariants: the window guards, the KM/cap limits, the stable currency
# --------------------------------------------------------------------------- #
def test_hold_window_guards_refuse_outside_Ms_Bs():
    s = au.ATLAS_STEELS["1080"]
    Bs = steven_haynes_Bs(**s.comp)
    Ms = andrews_Ms(**s.comp)
    with pytest.raises(ValueError, match="Bs"):
        au.austemper("1080", Bs, 100.0)                  # at the ceiling: inert, refused
    with pytest.raises(ValueError, match="Bs"):
        au.austemper("1080", Bs + 40.0, 100.0)
    with pytest.raises(ValueError, match="Ms"):
        au.austemper("1080", Ms, 100.0)                  # at the floor: martempering, refused
    with pytest.raises(ValueError, match="Ms"):
        au.austemper("1080", Ms - 40.0, 100.0)
    with pytest.raises(ValueError, match="anchor"):
        au.austemper("1018", 350.0, 100.0)               # no atlas anchor for this steel
    with pytest.raises(ValueError, match="hold time"):
        au.austemper("1080", 350.0, 0.0)


def test_short_hold_reduces_to_KM_on_the_full_austenite():
    # A vanishing hold transforms nothing (incubation): the final cool is exactly the existing
    # Koistinen–Marburger bookkeeping on the FULL austenite — the recipe adds nothing of its own.
    s = au.ATLAS_STEELS["1080"]
    r = au.austemper("1080", 343.3, 1e-6)
    f_km = koistinen_marburger(r.T_quench, andrews_Ms(**s.comp))
    assert r.bainite < 1e-9
    assert r.martensite == pytest.approx(f_km, abs=1e-9)
    assert r.retained_austenite == pytest.approx(1.0 - f_km, abs=1e-9)


def test_long_hold_caps_at_full_bainite_and_the_placeholder_hardness():
    # The cap: a hold far past completion saturates at U = 1 — fully bainitic, nothing left for
    # KM — and the hardness IS the carbon-only bainite placeholder (now load-bearing, named: fine
    # for plain-carbon 1080, under-ranks alloyed 4340).
    for steel in ("1080", "4340"):
        r = au.austemper(steel, 343.3, 1e5)
        assert r.bainite == pytest.approx(1.0, abs=1e-12)
        assert r.martensite == 0.0 and r.retained_austenite == 0.0
        assert r.HV == pytest.approx(vickers_bainite(au.ATLAS_STEELS[steel].comp["C"]), rel=1e-12)


def test_fractions_sum_to_one_on_the_stable_key_set():
    # The inter-module currency: the same five keys pathint emits (ferrite/pearlite structurally
    # zero on the hold route), summing to 1 by construction at any hold length.
    for t_hold in (5.0, 80.0, 600.0):
        r = au.austemper("4340", 371.1, t_hold)
        f = r.fractions()
        assert set(f) == {"ferrite", "pearlite", "bainite", "martensite", "retained_austenite"}
        assert f["ferrite"] == 0.0 and f["pearlite"] == 0.0
        assert sum(f.values()) == pytest.approx(1.0, abs=1e-12)
        assert 0.0 <= r.bainite <= 1.0


def test_pearlite_race_police_loud_near_Bs_silent_in_the_anchored_band():
    # The un-modeled diffusional competitor is POLICED, not modeled: a high hold (near Bs, where
    # the real ferrite/pearlite reactions are fastest) must warn; the classic anchored-band
    # austempering hold must not. The shadow is recorded either way (transparency).
    with pytest.warns(UserWarning, match="high hold"):
        r_high = au.austemper("1080", 480.0, 100.0)
    assert r_high.pearlite_race_flagged
    assert r_high.pearlite_shadow > au.PEARLITE_SHADOW_WARN
    with warnings.catch_warnings():
        warnings.simplefilter("error")                   # any warning here is a failure
        r_band = au.austemper("1080", 343.3, 600.0)
    assert not r_band.pearlite_race_flagged
    assert 0.0 <= r_band.pearlite_shadow <= au.PEARLITE_SHADOW_WARN


def test_everything_existing_is_byte_identical():
    # The 6b negative result stays load-bearing: anchoring uses dataclasses.replace, so the
    # module-level demonstration scale, the 540-split, and the CCurve are untouched — pathint
    # never sees the anchored reaction (the rest of the suite staying green is the broader guard).
    assert BAINITE_KINETIC_SCALE == 10.0
    assert bainite_reaction_for_steel(0.40, Mn=0.90, Cr=1.0, Mo=0.20).scale == 10.0
    assert BS_DEFAULT == 540.0
    cc = ccurve_for_steel(0.45, Mn=0.75, Si=0.22)
    assert cc.Bs == 540.0
    assert not hasattr(cc, "bainite")
