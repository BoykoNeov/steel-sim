---
name: consequences-app-built
description: "Defect-consequences Streamlit app (notebook/app backfill Slice 2a) BUILT — the third app of the triptych; 6 defect panels, no engine/ADR"
metadata: 
  node_type: memory
  type: project
  originSessionId: a648e1b5-36ca-4eb1-9d47-d2ae9dbb66f9
---

**Notebook/app backfill — Slice 2a (the defect-consequences app) BUILT ✓ 2026-06-14** (the user
confirmed "notebook Slice 2 is the cleanest next"). `steel/app_consequences.py` + `tests/test_app_consequences.py`
(8 always-green helper tests + 6 viz-gated figure build-smoke tests = **+14**); fast lane **829 passed / 9
deselected** (serial `-n0`, measured not inferred). Standalone, **NO engine, NO ADR, no constant** — same
ADR-0002 "reach not physics" posture as [[making-app-built]]. Closes the named Slice-2 *panels* half;
the front-end teaching **notebook is 2b** (separate batch, gets its own retry-on-wedge harness).

**The triptych — advisor's architecture call (separate surface, NOT appended to `app_making`).**
`app.py` = heat-treat (cooling curve → microstructure); `app_making.py` = *ore → billet*; this =
**"…and here is what goes wrong"**. Discriminating test the advisor posed: *does an "ore → billet" app
want a tempering-embrittlement panel?* **Five of the six defects manifest downstream of the billet**
(cold/red-short, flaking, temper-embrittlement, TME) — only porosity + hot-tear are casting-stage. The
gallery had already made the call: all of them file under one category, **"Impurity consequences
(front-end)"** — neither making nor heat-treatment. So a third app, name matching that vocabulary.

**Six panels = 6 figure builders, not 7** — `demo_impurity_window` is ONE demo/figure covering BOTH
cold-short (P) and red-short (S). Every panel wraps an already-banked `demo_*.compute()` + `plots.*_figure`
(pure reuse, no figure invented), and each `*_readout` helper re-composes the sealed model with the
panel's knob: impurity (P/Mn/S → cold-short DBTT + red-short free-S, the workable window); temper-embrit
(J-factor + Mo + cool rate + temper); TME (grade-carbon + peak temper on the same frozen oil/10 mm quench);
H-flaking (section + bake, fixed 4140 ladle H); gas-porosity (grade + Al kill); hot-tear (Mn/S). Each
panel carries the **two-tier** punchline — flat upstream RISK line vs the carbon-/geometry-/segregation-aware
CONSEQUENCE — the same "same impurity, the *other* variable decides" thread.

**DURABLE LESSON — advisor commit-gate catch: an app panel must not surface an input the underlying
model DELIBERATELY EXCLUDES.** My `TME_GRADES` had offered **1080**. The TME demo's own source drops 1080
on purpose: high-carbon **plate-martensite** embrittles in the trough by a *cementite-on-twin-boundary*
path, NOT the **interlath cementite-film** mechanism the panel's caption describes. `tme_readout("1080")`
returned `embrittled=True` — **accidentally right for the wrong reason**, attributing the film mechanism to
a structure it doesn't cover (the exact misattribution the demo author engineered around). Fix = restrict
to the demo's discriminator set **(4140 / 8620 / 1045)** = embrittles / carbon-gated / martensitic-gate
miss. The other 5 panels are clean (advisor scanned): HF fixed to 4140, GP's [%C][%O] is grade-general,
impurity/hot-tear are backbone+knobs, TE runs only the Ni-Cr victim.

**The Slice-1 commit-gate lessons were pre-empted, not re-learned:** figure build-smoke tests were in from
the first write (not a one-off manual check), and the count was **measured with `-n0`** — refused to
back-compute a delta vs the 798 (different lane). Non-blocking polish also taken: impurity panel default
Mn dropped to 0.05 so it OPENS on the cold-short+red-short double-flag (the "both ends of the window" hero).

Gallery intro + both READMEs surface the third app (`streamlit run steel/app_consequences.py`); drift-guard
regenerated/green. Amends [[making-app-built]]; companion to [[gallery-page]]; the integration capstone
(one Heat chained through the whole run) is still the separate larger item.
