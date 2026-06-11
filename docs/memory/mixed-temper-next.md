---
name: mixed-temper-next
description: "Next planned steel-sim work = mixed-structure (per-constituent) tempering, plan §16; steps 1-3 next session, 4+ later"
metadata: 
  node_type: memory
  type: project
  originSessionId: de815651-624e-4ad4-a0ce-d4922d12fd67
---

**Next planned work for steel-sim** (chosen 2026-06-11, user-directed; recorded as plan
**§16**, not yet built): **mixed-structure tempering** — temper a phase *mixture*
per-constituent, the named 3b deferral. All planned phases (1–7 + §15 D(C)) are already
built/committed; this is the §11 "smaller deferral" the user picked over residual-stress and
the KV-pearlite rebuild.

**The split the user set:** **steps 1–3 = the next session** (the validated core, no hazard);
**steps 4+ = a future session.**

- **Steps 1–3 (next):** new opt-in `properties.tempered_hardness_HV(fractions, …)` = rule of
  mixtures where martensite → `tempered_martensite_HV` and ferrite/pearlite/bainite/RA are
  **temper-inert, *delegating* to `CONSTITUENT_HV[name](C, comp, Vr)`** (carry comp/Vr or the
  no-op seam breaks); **three exact seams** (mart=1→`tempered_martensite_HV`; mart=0→`hardness_HV`
  no-op; sub-onset g=1→as-quenched — all *exactly*); `tempered_jominy_hardness` + banked figure =
  **the teeth** (near-end full-martensite softens hard, far-end pearlite flat — the differential
  shape; bracketed by 3b's validated 4140 temper response + 2c's as-quenched soft end, NO extracted
  numbers — the [[di-crosscheck-source]] table-trap).
- **Steps 4+ (later):** `design.py` guarded unlock (relax `_is_fully_martensitic`, invert the mixed
  curve — still monotone in T) **gated on a retained-austenite guard** (RA→bainite/fresh-martensite
  on temper is non-monotone, can *raise* hardness; design *recommends* so an unguarded relax is
  dishonest — keep martensite-dominant/RA-capped) + **consciously re-derive §14** (1045-infeasible /
  45 HRC→4140-oil headline can flip); surfaces; close-out + [[commit-push-end-of-batch]].

**Posture (advisor-confirmed):** NOT pure re-composition like sweep/design — *"diffusional products
are temper-inert"* is a new claim (cited for pearlite, **named-not-validated for bainite & RA**).
Keep `tempered_martensite_HV`/`hardness_HV`/2c/3a/3b/Jominy/four-curves byte-identical (new function
is opt-in).
