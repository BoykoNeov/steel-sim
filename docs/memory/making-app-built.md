---
name: making-app-built
description: "Front-end making-chain Streamlit app (notebook/app backfill, Slice 1) BUILT — the ore→billet twin of app.py, per-stage panels, separate not appended"
metadata: 
  node_type: memory
  type: project
  originSessionId: aa60f82e-3f1c-45b1-bad7-94ae7af0c924
---

**Notebook/app backfill — Slice 1 (the making-chain app) BUILT ✓ 2026-06-14** (picked from a "what's
next" menu: small-deferrals → notebook/app backfill). The front-end interactive surface F1/spine/F4 each
deferred. `steel/app_making.py` + `steel/tests/test_app_making.py`; **798 green / 2 skipped (+15)**;
standalone, **NO engine, NO ADR, no constant**. README (root + package) + gallery Experiments card wired
(drift-guard regenerated). Closes the §7 "Notebook & app deferred" note as Slice 1.

**The app = the *"ore → billet"* twin of `app.py`'s *"cooling curve in, microstructure out"*.** Covers the
making chain: F1 reduction → the `Heat` spine → F2 refining + slag partition → F3 ladle trim → F4 casting +
solidification. Reuses the *validated* modules ([[f1-ellingham-built]] [[refining-f2-built]]
[[slag-f2-slice2-built]] [[ladle-f3-built]] [[f4-casting-built]] [[f4-slice2-solidification-built]]
[[heat-state-spine-built]]) — **reach, not physics** (ADR 0002), same as `app.py`.

**FOUR advisor steers, all load-bearing (pre-write):** (1) **Slice it — app before notebook**: app compute
helpers are headless always-green; the notebook carries the [[notebook-kernel-wedge-rootcause]] flakiness.
(2) **Separate `app_making.py`, NOT appended** to `app.py`/`steel.ipynb`: test isolation (don't add cells
to the wedge-mitigated notebook test), file focus (`app.py` already ~1400 lines), and narrative (the title
*is* the back-end thesis). (3) **Per-stage panels (option A), NOT "follow one heat" (option B)** — B is
more compelling but bumps the **unwired `from_hot_metal`/`from_tap` seam** ("composed by type, not chained
in one run") → pursuing it turns the backfill into the **integration capstone**, out of scope. (4) **Verify
the demos follow the compute/render split before wiring figure builders** — confirmed: every front-end
`demo_*` has `compute()` + a reusable `plots.*_figure(d)`, so builders wrap them (no figure invented).

**Three-layer ADR-0002 discipline, mirrored from `app.py`:** (1) headless **compute helpers** (one per
stage — `reduction_readout`/`spine_readout`/`refining_deox_readout`/`slag_partition_readout`/
`ladle_trim_readout`/`casting_readout`; import neither Streamlit nor matplotlib; tested against each stage's
*validated demo behaviour*, so they can't drift). (2) **figure builders** wrapping `demo_*.compute()` +
`plots.*` (matplotlib lazy). (3) **`main()`** = the lone `import streamlit`, paper-thin. The one heavy
compute (the latent-heat solidification field) is **memoized in `main()`** via `st.session_state` (the
`app.py`-residual pattern). Run-as-script bootstrap verified (`python steel/app_making.py` dies only at
`import streamlit` inside `main()`; runs end-to-end clean in bare mode, exit 0, 0 tracebacks).

**Each panel's knob over the validated model:** furnace T → the 746 °C C/FeO crossover + oxide ladder;
Cr/Mo dose → the **emergent** soft core (martensite crossing the spec, not scripted); deox element/level →
the Al–O **minimum** (~0.074 %); the three reference slags → the **acid≈1 vs basic≈hundreds L_P** gap;
recovery shortfall → the **off-grade + soft-core double flag**; casting modulus → the enriched centerline
**hard band**.

**Advisor catch at the COMMIT GATE (the durable lesson):** my self-checks dropped **layer 3** — `app.py`'s
`test_app.py` *build-smoke-tests the figures under `[viz]`*, but I'd only smoke-tested the figure builders
in a **one-off bash command that won't re-run**. A future `plots.*` signature change would break the app's
`st.pyplot` calls while `test_app_making.py` stayed silently green. Fix: added **7 viz-gated figure-build
smoke tests** (`pytest.importorskip("matplotlib")` → `len(fig.axes) >= 1`; solidification computes the
heavy demo ONCE). Also: I'd **baked an inferred "791" into the plan banner** (xdist `-q` hid the summary;
exit 0 confirms *pass* not the *number*) — **measured it** (`-n0` → 798/2) and corrected to +15 → 798.
Lesson = *a manual check outside the suite isn't a test; measure counts you write down durably.*

**Slice 2 deferred (named):** the **defect-consequence panels** (porosity / flaking / hot-tear /
cold-short / red-short / temper-embrittlement / TME) and the **front-end teaching notebook**. The
**end-to-end integration capstone** (one `Heat` chained hot-metal→…→quench, resolving the seam) remains the
separate larger item. Amends [[steel-making-frontend-plan]]; companion to [[gallery-page]].
