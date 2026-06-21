---
name: game-slice1-built
description: "A1 game/ Slice 1 BUILT — the gauntlet (every stage a decision). Losability = the advisor's acceptance bar; 7 losable knobs probed empirically; casting honest no-loss; golden run preserved verbatim"
metadata:
  node_type: memory
  type: project
---

**A1 `game/` Slice 1 BUILT ✓ 2026-06-21 — the gauntlet.** Answers the user's Slice-0 critique
(*"nothing to get wrong in the other steps"*) by making **every stage a decision**. Scope was widened from
the plan's literal Slice 1 ("the deox kill knob") to the **full gauntlet (all 8 stages)** — the user's
explicit `AskUserQuestion` choice. Wraps [[game-slice0-built]]; amends [[next-directions-catalogue]];
sibling [[full-chain-capstone-built]] (the chain it plays).

**Spine.** A frozen `Recipe` carries **one knob per stage**, every field defaulting to the capstone
reference (single-sourced from `demo_capstone`). The canonical `Heat` is still built **only** from the
eight stage seams → `play_to_end(reference).heat == run_chain.part` holds **VERBATIM** (golden run
untouched — the existing test still passes as-is). `GameState.carbon_target` became a back-compat property.
New modules: **`choices.py`** (tested per-stage option tables — every *recommended* option provably equals
the `Recipe` field, so taking every recommendation IS the sound golden run) and **`postmortem.py`**.

**Post-mortem (the teeth).** `postmortem.post_mortem(part, recipe)` runs the **sealed consequence engines**
(`gas_porosity`, `hydrogen_flaking`, `hot_work` red-short, `hot_tear`, `heat_state.cold_short_check`) on the
**finished part** and reports which defect each latent flaw became + the stage that planted it — **WITHOUT
mutating the canonical spine** (that is what keeps the golden run exact; the alternative — appending
consequence steps — would force `run_chain` to grow them and reframe the test). Mirrors `app_consequences`'
stateless composition.

**LOSABILITY = the advisor's acceptance bar (the durable lesson).** The four Slice-0 structural tests
(firewall / golden-run / state-transition / label) **ALL pass on a gauntlet of purely cosmetic knobs** —
i.e. the exact state the user complained about, made invisible. So the real bar is **losability**: for each
claimed knob there must exist a wrong setting (others at reference) that flips the **finished-part** verdict
to a **distinct** defect, *end to end* — **one test per knob** (`test_game_losability.py`, 11 parametrized).
**7 knobs are losable**; casting is conceded.

**Both advisor masking predictions CONFIRMED by an empirical probe run BEFORE claiming any knob** (probe,
don't assume — then deleted):
- **desulf is masked.** Trim raises Mn to ~0.90 for 4140 → skip desulfurization (S≈0.050) → bulk Mn:S ≈ 17
  → **does NOT red-short or hot-tear** (the trim's Mn ties it as MnS). Made losable via the **cleanliness
  spec** instead (`S > slag.MAX_SULFUR_PCT = 0.040` → off-grade dirty). **The masking became the lesson**
  (the desulf why-card states it outright). Physics in [[sulfide-morphology-built]]/[[impurity-consequence-built]].
- **cast is non-losable.** Modulus only sets the Chvorinov time; segregation is `fs`-based and lands on the
  **centerline**, not the judged **nominal** part; there is **no validated casting spec** (Niyama/hot-tear
  in `casting.py` are "plausible, not validated", not surfaced as a flag). → casting is an **honest no-loss
  pass-through**, reported plainly + pinned by a test (`test_cast_modulus_is_an_honest_no_loss_pass_through`)
  so nobody later ships a fake slider. **Advisor: "don't ship a fake slider."**

**Two more probe-driven calls:**
- **deox: amount knob is non-losable** (aluminium is so strong it kills O below the porosity line even at
  0.005 %) → **reframed to the DEOXIDIZER-CHOICE knob** (Al ≫ Si > Mn, the F1 Ellingham hierarchy): a weak
  Si/Mn kill can't pull O below the C–O line (O pinned at 52.6 ppm) → **gas porosity** (S=1.02). Richer and
  more cited than a slider. Emergent bonus (not wired): weak kill → high O → **blocks desulfurization**
  (the engine reads `oxygen_ppm`) → also trips sulfur-over-spec = the real *kill-before-desulf* coupling.
- **cold-short is P-gated.** The §3 Pickering DBTT also climbs with carbon (pearlite), so a high-carbon
  over-blow reads brittle with **clean P** — that is the *carbon* mistake (already off-grade+soft-core), not
  the dephos knob. Gate the cold-short consequence on `part.P > MAX_PHOSPHORUS_PCT` so attribution is honest.

**Scope honesty (named, not faked):** quench-crack is **out of scope for 4140** (`quench_crack_check`
raises for non-atlas grades — §18 residual is keyed to 1080/4340; see [[fracture-coupling-built]]) → the
heat-treat failure is the **soft core**, not a crack. TME/temper-embrittlement left out (no temper stage).
**Field survival pinned**: the part faithfully carries every flaw at its lock value (trim at step 7 precedes
cast at 8; heat-treat at 9 is composition-inert) — a test asserts part fields == cast-snapshot fields, so
the post-mortem reads are physical, not drift. Consequence engines reused: [[gas-porosity-built]],
[[hydrogen-flaking-built]], [[hot-tear-built]].

**No engine touch** (Slice 0's `casting.cast_billet_onto` was already public). **60 game tests** (was 28),
**1046 fast-lane green**. Gallery *Game* blurb rewritten to Slice 1 (still 38 entries, `steel-game-blow.png`
unchanged — the τ-curve is still the headline continuous knob). **Deferred:** verified-vs-flavor labels as
styled UI chips + educational tier-2 physics-shape explainer; a Slice-1 "defect map" figure; Slice 2 (the
method/era tech tree).
