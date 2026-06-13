---
name: ladle-f3-built
description: "front-end F3 (ladle trim — alloy to grade, Slice 1) BUILT 2026-06-13; the seam where the grade composition is finalized; spine-class; the hero off-spec input PRODUCED by a recovery shortfall, not hand-set"
metadata:
  node_type: memory
  type: project
---

**front-end F3 (ladle trim, Slice 1) BUILT ✓ 2026-06-13** — the **seam to the back end** where the grade
composition is finalized: `ladle.py` + `demo_ladle.py` + `plots.ladle_figure` + 21 tests (`test_ladle.py`
14 + `test_demo_ladle.py` 7); fast lane **590→611**, full suite **618 passed / 2 skipped**; **no solver, no
engine/back-end touch, no ADR** (plan §7 is the record). Where the spine and F2 *held the alloy fixed* to
isolate carbon, **F3 is where the Cr/Mo/Mn/Si actually go in** — so its failure output is the **hero-demo
off-spec input the plan kept pointing at**, now **produced by a modeled ladle op, not hand-set**.

**Advisor pre-code reframe = the crux (two load-bearing calls, both shaped the build):**
1. **Grade-band miss ≠ soft-core → PROBE THE BACK END FIRST (the one blocking item).** My instinct
   ("recovery scatter → off-grade → soft core") would have **failed empirically**: the SAE window is a wide
   commercial tolerance, a marginal recovery miss lands *inside* it (Cr recovery 0.95→0.80 ≈ 0.86 %Cr, still
   in 4140's 0.80–1.10) and nowhere near soft. Probed 4140 oil Ø15mm: nominal 94%M; **band bottom corner
   still ~89–92%M (through-hardens)**; soft-core only below ~70% of nominal Cr/Mo (Cr 0.70/Mo 0.14 = 90%M
   knife-edge); spine's dramatic 40%M ≈ Cr 0.20 (20%). So the hero is a **GROSS under-trim (~half
   recovery)** so BOTH flags fire; the "in-band-but-soft-at-bigger-section" subtlety is **deferred**.
2. **F3 is SPINE-CLASS, not a physics phase — don't manufacture teeth.** No new thermo: mass-balance
   arithmetic + cited recovery + cited windows. So like [[heat-state-spine-built]] its checks are
   **structural** (round-trip identity, conservation, dilution, immutability) *labelled by-construction*,
   and the **grade window is a labelled spec** (SAE J404, like `MIN_MARTENSITE_SPEC`), NOT a benchmark.
   Advisor killed my "naive-vs-recovery-corrected contrast" as **near-vacuous** (`recovery×deficit<deficit`
   because recovery<1 *by definition* — the F2 K-independence trap in a new costume). The genuinely
   **validated** content is the back-end propagation (under-trim Cr/Mo → soft core) = **same class as the
   spine's hand-set under-dose**; F3's new value = the under-dose is **produced** — additions sized for an
   *assumed* recovery the bath didn't deliver. **The tier-2 scatter in the recovery factor IS the failure
   mechanism** (turns the weak cited input into the point); it's the front-end consequence of F2's deox
   state (an under-killed bath eats the Cr/Mn).

**Seam:** `from_tap(grade)` (alloy-lean post-refining origin, on F2's carbon, Cr/Mo ~0) → `trim_to_grade`
sizes ferroalloy charges with a **dilution-exact closed-form inverse** (`additions_for_grade`: W' closed
form, no matrix) and mixes them at the *actual* recovery (`mix`, forward exact incl. dilution). **Op point
4140 oil Ø15mm:** correct trim (recovery holds) → Cr 1.00/Mo 0.20, 94%M/620HV, **in-band, through-hardens**;
under-recovered (Cr/Mo recovery ×0.5) → Cr 0.53/Mo 0.10, 81%M/570HV → **`off-grade-composition` flag (F3) +
`soft-core` flag (back end)** = **one mistake, two flags**, and **at THIS section (oil Ø15mm) off-grade
fires BEFORE soft-core** (band floor Cr 0.80 above the hardenability crossing ~0.70 → window = *conservative
early warning*, ordering tooth in the demo test). **The ordering is SECTION-DEPENDENT** (advisor done-review
catch): at a thicker section an *on-grade* heat soft-cores, at a thinner one a low-Cr heat through-hardens —
the chemistry-spec ≠ H-band point (the deferred subtlety); test only pins Ø15mm, so all prose qualified "at
this section". Dilution is real: 3.3 t of additions on 100 t
dilute C 0.40→0.388 (exact). **Bug caught by my own smoke test:** forgot `defects=defects` in `evolve` →
flag computed but not applied (fixed before tests).

**Cited tiers (di-crosscheck, two like F2/F4):** robust = **SAE J404 grade windows** (4140 C0.38–0.43/
Mn0.75–1.00/Si0.15–0.35/Cr0.80–1.10/Mo0.15–0.25, 8620 likewise) — but used as a **labelled spec**, not
teeth. Source-sensitive = **recovery factors** (Mn/Si≈0.90, Cr≈0.95, Mo/Ni≈0.97 — scatter with deox
state/timing → ranking only) + ferroalloy assays (FeMn 78%, FeSi75, FeCr 68%, FeMo 62%).

**Named deferrals (the honesty bound):** **carbon carry-in** — HC ferrochrome/ferromanganese carry ~6–8% C,
so the 4140 Cr/Mn trim *would* add **+0.18 %C (~45% of the grade's carbon!)** — `carbon_pickup_pct`
quantifies it (= **why low-carbon ferroalloys exist**); held off F2's carbon axis (`mix` only dilutes C,
never raises it). **P/S residual bands + desulf/dephos OUT of the window** — the `Steel`/`Heat` vector
carries no P/S (same state gap as F2 Slice 2). Deox-state-dependent recovery (F2→F3 coupling) named.
**Ceiling:** equilibrium/steady-state additions, never dissolution/flotation *kinetics* (the F2 transport
wall).

**Surfacing:** banked figure `docs/figures/steel-ladle.png` (2×2: trim-vs-window bars, recovery→landed-Cr,
martensite-vs-Cr propagation, two-flag verdict); gallery **"Ladle trim (front-end)"** card inserted BEFORE
Casting (chain-forward) via [[gallery-page]] generator (regenerated, drift-guard forced it); both READMEs +
plan §7/§13 as-built. **Notebook & app deferred** (heat-treatment-framed, as F1/spine/F2/F4).

**The full front-end chain is now BUILT inside steel-sim:** ore→iron (F1) → spine → refine (F2) → trim (F3)
→ cast (F4) — each link **composes by `Heat` type** (produces the Heat the next consumes; under-spec output
reaches the validated back end), but **NOT piped in one run** (F2 `from_hot_metal` takes a fully-alloyed
backbone, F3 `from_tap` starts alloy-lean — composed by type, not chained; advisor done-review catch).
**Next = `game/`** (on the proven spine)
or a **Slice 2** (F2 slag partition / S/P state extension, F4 latent-heat map + defects). NB the green count
is **optional-extra-dependent** (this env had no calphad → 590/611; F2 memory's "614" was with extras).
Amends [[f4-casting-built]] / [[refining-f2-built]] / [[heat-state-spine-built]]; builds on
[[steel-making-frontend-plan]]; di-crosscheck per [[di-crosscheck-source]].
