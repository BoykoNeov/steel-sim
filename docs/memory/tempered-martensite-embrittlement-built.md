---
name: tempered-martensite-embrittlement-built
description: "tempered-martensite embrittlement (irreversible, carbon-driven, 260-370 C cementite films) BUILT 2026-06-14 — closes temper-embrittlement's named deferral; the foil that completes the tempering-axis pair"
metadata: 
  node_type: memory
  type: project
  originSessionId: 648a8383-b19c-4ff7-bc42-19b56c632ce5
---

**Tempered-martensite embrittlement (TME) BUILT ✓ 2026-06-14** — closes the named deferral from
[[temper-embrittlement-built]]: the **irreversible** sibling on the SAME tempering axis. Reversible TE closed
phosphorus' *segregation* path; TME closes the *microstructural* one — the trough `steel-production.md` §11
named as the back-end `properties.toughness_index` ceiling but never modelled. New `tempered_martensite_embrittlement.py`
→ the **`tempered-martensite-embrittled`** flag (mirrors `heat_treat`/`hot_work`/`temper_embrittlement`).
Tempering as-quenched martensite in **260–370 °C** precipitates cementite as **films** on interlath /
prior-austenite boundaries (Horn–Ritchie 1978: fed by interlath retained-austenite decomposition) → toughness
trough. Suite **741 green / 2 skipped** (+19), NO engine touch, NO ADR. Demo+figure+gallery card+README row.

**The slice = the FOIL that completes the pair — opposite on every axis:** TME is **carbon-driven** (not
impurity — a *clean* medium-carbon steel still embrittles, the headline distinction from reversible TE which
needs P), **microstructural** (not equilibrium segregation), **irreversible** (not reversible). Modelled as a
**one-way verdict keyed on the *peak* temper reached**: temper 300 → embrittled, temper 450 → recovered,
re-enter 300 (peak still 450) → *stays tough* — the direct foil to reversible TE's re-embrittling cycle.

**NO claimable tooth — the paper-gate run BEFORE coding, FAILED (the discipline, symmetric with reversible TE
and red-short).** The tempting tooth — "the 260–370 °C trough *emerges* from ε→cementite / interlath-RA
kinetics without tuning" — fails the same way reversible TE's segregation nose did: the repo carries no
stage-III carbide thermodynamics, so the trough onset is **underdetermined here** → did NOT build a carbide
model to manufacture one. **By construction:** carbon gate `MIN_CARBON_FOR_TME=0.25`, martensitic gate, peak-temper
rule. **Cited inputs (verification ≠ tooth):** trough 260–370, ~400 °C recovery, cementite-film mechanism.
**The faithful part is ARCHITECTURE not a tooth:** the check runs the **same frozen `sweep.evaluate` quench**
the spine uses and gates on its **martensite fraction** → composes with hardenability (a soft-core section is
immune — no tempered martensite to embrittle; un-hardened 1045 at oil-10mm M=0.21 confirms).

**TWO ADVISOR CATCHES, both durable (called advisor BEFORE writing the verdict logic):**
1. **Irreversibility stated BACKWARDS in my first plan.** I had the >600 °C reheat *failing* to clear TME and
   re-austenitization *clearing* it — the **reverse**: the reheat is above the ~400 °C recovery so it *relieves*
   TME (same reset that fixes reversible TE), and re-austenitizing *restores* susceptibility (fresh RA films).
   The genuine reversible/irreversible distinction is the **cycling toggle** (reversible re-embrittles; TME
   stays tough), NOT a failed reset. → keyed the verdict on **peak temper**.
2. **RA-as-severity-driver = the inverted "looks-faithful" trap (Mushet-class).** My first design drove TME off
   *computed bulk retained austenite* (mechanistically the interlath-film source). But bulk RA ranks eutectoid
   **1080 (~0.18 RA, plate martensite)** as the worst victim — where the interlath-film mechanism does NOT apply
   — vs the textbook medium-C low-alloy (4140/4340/300M). → RA cited as **mechanism only**, **CARBON drives the
   gate**. Discriminating check run before committing: flags 4140 (0.40C), 1080 (0.80C); **8620 (0.20 %C) immune
   even fully hardened** (M=0.98) — the low-carbon lath-martensite exemption.

Registry has no 4340 → used **4140** (0.40C Cr-Mo) as the registry-grounded classic victim. Deferrals: absolute
trough depth (no Charpy-J — back-end ceiling stands), P-aggravation magnitude, explicit ε→Fe₃C carbide sequence.
Amends [[temper-embrittlement-built]] (its TME deferral now closed) / [[impurity-consequence-built]]; sibling of
[[hydrogen-flaking-built]]. **The whole impurity/embrittlement consequence arc is now closed** (P cold-short +
P temper-embrittle + P TME, S red-short, H flaking). **Next = `game/`** (full chain + all consequences built)
or another named physics deferral (wootz V/Mo carbide banding = the only one buying genuinely new physics).
