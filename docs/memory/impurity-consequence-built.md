---
name: impurity-consequence-built
description: "impurity consequences (P cold-short + S red-short) BUILT 2026-06-13 — closes F2 Slice 2's deferral; ONE genuine tooth (P-strength), S is by-construction symmetric with slag.py; two distinct classes (P propagation, S new consumer)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1b04496f-fae3-4c1e-ac0d-98666df46497
---

**The impurity CONSEQUENCES are closed ✓ 2026-06-13** — what F2 Slice 2 ([[slag-f2-slice2-built]]) set as
inert P/S state now produces a downstream verdict. Built per **user's explicit "plan for s also, we are not
in a hurry"** (I'd scoped S as deferred; user pulled it in). Two slices, **two distinct classes** (the
load-bearing honesty the advisor enforced):

- **P → cold-shortness = a PROPAGATION.** `grain.py` §3 gained a `P_pct` term in BOTH Pickering laws
  (default 0 → suite byte-identical); `heat_state.cold_short_check` normalizes a `Heat` and flags
  **`cold-short`** when the P-aware DBTT > service temp. P threads the **existing** toughness law.
- **S → red-shortness = a NEW consumer.** New module `hot_work.py` (`red_short_assessment` + `hot_work`
  orchestrator → **`red-short`** flag): free S (reuses `slag.manganese_sulfide`) forms a Fe–FeS GB film
  above the eutectic when forged; Mn ties it as MnS to prevent it.

**THE LOAD-BEARING ADVISOR CATCH (pre-commit, two rounds): the whole build adds EXACTLY ONE genuine tooth —
the P-strength cross-source coherence — and I'd manufactured a second.** I labelled the **Mushet Mn:S ≥ 1.71
threshold "THE HEADLINE TOOTH"**, but `slag.py` *already* labels the **same** `manganese_sulfide`
stoichiometry **"by construction (NOT teeth)"** (1.71 = M_Mn/M_S, arithmetic, cannot come out wrong) →
direct internal contradiction. The tell was in my own tests: `test_mushet_threshold` (claimed tooth) and
`test_free_sulfur_reuses_the_slag_balance` (by-construction) test the *same* arithmetic crossing zero. And
"analog of slag's acid/basic L_P endpoint" is a **disanalogy** — L_P emerges from a nontrivial Healy
correlation that *could* have failed history; 1.71 cannot. **Fixed: framing only, no code, tests stayed
green.** The honest map:
- **THE ONE TOOTH = P-strength, by CROSS-SOURCE coherence** (grain.py, the propagation side): Thiele–Hošek
  **+237 MPa/at% P PDF-verified** (eq ΔR_p0.2 = G·ε·X_c/100, G=83000, ε=0.286 from Fe/P radii) → **≈427
  MPa/wt%** (×1.803 at%→wt%, the registered unit trap) sits inside Total Materia's independent **365–620
  MPa/wt%**; hardness increment **119.8 vs lit 123–125 vs theoretical 127 HV/wt% within ~6%** (the tightest
  leg). Could have missed (a unit-basis slip → ~237/wt%, below bracket).
- **EVERYTHING ELSE = cited / flagged / by-construction, NO tooth:** P→DBTT slope **FLAGGED representative**
  (`grain.ITT_K_P` — built here ≈500, **re-pinned 2026-06-22 to ≈600 °C/wt% by A2** = centre of a documented
  ≈40–78 °C/0.1wt% bracket, IDOT PRR-174 7–7.8 °C/0.01%P anchor; the A2 gate CONFIRMED the bulk slope can't
  earn teeth — a reduced form of GB *coverage* physics, clean form GB at%→DBTT Song 2011 via McLean = the
  deferred B-escalation; see [[next-directions-catalogue]] A2); the cold-short verdict + the **demo's +96 °C =
  ILLUSTRATIVE** (ride the flagged slope);
  the S slice = cited constants + by-construction, **symmetric with slag.py** (a thin honest consumer, which
  is FINE — just don't dress it as a tooth). Mushet 1.71 = the **historical-coherence ANCHOR (a result,
  by-construction)**.
- **Cited di-crosschecked INPUTS (verification ≠ tooth):** Fe–FeS **eutectic 988 °C** — confirmed the
  *eutectic* (GB-film onset), **distinct from FeS melting ~1192 °C** (the advisor's exact trap; IspatGuru +
  Wiley troilite); **MnS 1610 °C** (Total Materia). Temperature *ordering* = mechanism narrative, never a
  tooth (the vacuous-benchmark trap, dodged on the temps, nearly hit one step over on Mushet). di-crosscheck
  applied — [[di-crosscheck-source]].

**The SPLIT** (`test_phosphorus_sulfur_inert_in_the_hardenability_back_end`, renamed from `..._in_back_end`):
P/S now propagate on **exactly ONE path each** — consumed in `cold_short_check` / `hot_work`, still **inert
in `heat_treat`** (hardenability/hardness/martensite read C/Si/Mn/Ni/Cr/Mo only; `minor()` still excludes
P/S, takes them by explicit keyword). The old "consequence deferred" framing in `slag.py`/`sweep.py`
docstrings was now-false live text → rewritten to point at the consumers (repo-self-contained discipline).

**Demo = `demo_impurity_window`** (the unifying artifact, ONE demo / ONE gallery card / 4-panel figure):
the SAME high-P (0.35) sulfurous pig iron, made **cold-short + red-short by acid Bessemer / no manganese**
(P retained 0.32, DBTT +96 °C, free S 0.021, σy 457 — STRONGER, the signed foil) and **sound by basic +
Mushet Mn + ladle desulf** (P 0.008, DBTT −61, S as MnS, σy 347). Routed through the REAL chain
(`from_hot_metal`→`decarburize`→`dephosphorize` acid/basic→kill→`desulfurize`) — consequence **produced, not
hand-set**. Panels: P→DBTT (+ yield twin axis = the foil); free-S vs Mn:S (Mushet 1.71); the signed foil on
the yield–DBTT plane (P up-right = stronger+brittle; grain refine down-right = the §5b lone co-improver);
the closing **workable window** (P caps the cold/service end, S the hot/forging end ≥988 °C — DBTT framed as
a *service/toughness* limit NOT a cold-working scale, per advisor). The §5b foil is the real pedagogical
payoff.

Suite **668 passed / 2 skipped** (+28 tests), **no engine touch, no ADR** (additive `P_pct` + two
orchestrators ≠ a semantics change). **Named deferrals:** temper embrittlement (martensitic P → PAG-boundary
segregation — the martensitic P path), MnS inclusion **fracture-anisotropy** / transverse-toughness debit,
the **good-impurity** free-machining S (resulfurized 11xx — MnS breaks the chip), the kinetic hot-ductility
**trough shape**. Closes [[slag-f2-slice2-built]]'s P/S consequence deferral and [[historical-impurity-pedagogy]]
§14 themes A+B (now BUILT, §14.0 banner); builds on [[steel-making-frontend-plan]]. **Next = `game/`** (the
full front-end chain + all consequences now built) or a named deferral.
