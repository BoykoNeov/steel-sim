# 0010 — The bulk P→DBTT slope stays flagged; the grain-boundary-coverage mechanism explains the flag but earns no tooth

Status: Accepted — 2026-07-10
Scope: `steel/grain.py`'s phosphorus term in the Cottrell–Petch DBTT law (`ITT_K_P`, P's bulk
contribution to the ductile-brittle transition) and the new mechanistic module
`steel/p_segregation_dbtt.py`. **No engine or frozen pipeline is touched** — `grain.ITT_K_P` is
byte-identical (500 °C/wt%). This ADR records the decision to *keep it flagged and unchanged*, now with
a **mechanistic** justification for the flag rather than a bare bracket. It resolves the "B-escalation"
that next-directions §A2 deferred as new physics ("model the McLean coverage pathway so the bulk
scatter becomes an output").

## Context

A2 (2026-06-22, ADR-less, Outcome A) made `grain.ITT_K_P` **traceable** — anchored to a documented
engineering bracket ≈ 40–78 °C per 0.1 wt% P — but left it a *flagged* bulk coefficient, because the
A2 sourcing gate concluded the bulk-wt% slope **cannot earn teeth**: it is a path-dependent reduced
form of grain-boundary *coverage* physics. The B-escalation was to build the coverage pathway
explicitly and see whether, expressed in GB coverage, the slope becomes teeth-bearing. This is that
build — and the answer is **no, for a structural reason worth recording**.

**The teeth question is decided by one gate: does an independent *in-domain* holdout exist?** Composing
two cited relations (a McLean isotherm for bulk P → GB coverage, and a coverage → DBTT law) is a
by-construction wiring check — *not* a tooth — unless the composite is graded against measured data
neither relation was fit to, in the fracture-mode domain the engine's law describes. The engine's
`cottrell_petch_dbtt_C` is the Pickering **ferrite-pearlite, transgranular-cleavage** DBTT (it returns
`nan` on martensite).

**The clean coverage→DBTT data is real, multi-steel, and cross-*domain*.** Four cited linear relations
`DBTT[°C] = slope·Cp[at%] + intercept` (Cp = AES grain-boundary P), transcribed from the papers' own
abstracts (verified via the DOAJ API, not search snippets):

| Steel | slope °C/at% | matrix / fracture | source |
|---|---|---|---|
| Ti-stabilized IF | **3.12** | ferritic / **intergranular** | Chen & Song, *Mater. Sci. Eng. A* **528** (2011); doi:10.1016/j.msea.2011.08.002 |
| SA508-4N (fixed ~260 HV) | **13.31** | tempered martensite / intergranular | Zhao & Song, *J. Mater. Res. Technol.* **11** (2021) 1908; doi:10.1016/j.jmrt.2021.11.092 |
| SA508-4N (PAGS 34 µm) | **13.13** | tempered martensite / intergranular | Zhao & Song, *JMRT* **18** (2022) 3585; doi:10.1016/j.jmrt.2022.03.122 |
| SA508-4N (PAGS 112 µm) | **6.69** | tempered martensite / intergranular | Zhao & Song, *JMRT* **18** (2022) 3585 |

The slope spans **4.3×** across steels and **2×** within one steel by prior-austenite grain size. But
**every one of these relations is the intergranular grain-boundary-segregation axis** — a
DBTT-vs-AES-GB-coverage fit measures intergranular embrittlement (`temper_embrittlement.py`'s fracture
mode), *not* Pickering's transgranular cleavage. That includes IF: it is ferritic in *matrix*, but
being interstitial-free it has no solute carbon to compete with P at the ferrite boundaries, so it too
embrittles **intergranularly** (the phosphorus IF cold-work-embrittlement literature is explicit on
this) — and it is additionally the very steel whose 3.12 slope was fit to it. **So no cited relation is
in the engine's transgranular domain at all: there is no in-domain holdout, the cross-steel spread is
cross-*domain*, and composing it onto the engine's transgranular law would be a category graft.** (The
initially-tempting reading — that
the slope scales as Hall–Petch √d, which `grain.py` already carries — was rejected as confirmation
bias: two grain sizes fit an exponent −0.57 not −0.50, the authors' own mechanism invokes GB area per
volume (d⁻¹), and the ratio is hardness-confounded.)

**The computed payoff (`p_segregation_dbtt.summary`, compute-before-framing, not asserted).** Compose
the two gaps — McLean coverage (with the repo's already-cited `ΔG_seg = −34469 + 22.9·T` J/mol,
Yang–Chen / Erhart–Grabke) and a per-steel coverage→DBTT slope — and the bulk slope `dDBTT/d(0.1 wt% P)`
becomes a **product of two independently non-universal factors**: the per-steel coverage slope (4.3×
span) × the thermal-history-dependent McLean enrichment (~5× over T_seg 350–550 °C). Their product spans
**~5–116 °C/0.1 wt%** — a ~20× range that is order-of-magnitude consistent with the documented 40–78
bracket and *contains* it, with the engine's flagged 50 landing mid-range. This is **not** a derivation
of the specific 40–78 band (it rides the flagged McLean leg): the point is that two multiplicatively
non-universal factors make the bulk slope irreducibly steel-/path-dependent, so a flagged band is the
only honest form — the mechanism explains *why the slope must be a bracket*, and pins nothing. The
McLean leg is itself flagged: the single-solute isotherm *under-predicts*
absolute AES coverage (it omits C co-segregation), so it is used for **sensitivity only** — the
bracket explanation rests on the slope composition (order of magnitude), never on reproduced coverages.

## Decision

**Keep `grain.ITT_K_P` flagged and unchanged (500 °C/wt%); build the coverage mechanism as a separate,
engine-untouching module that explains *why* the flag is the only honest form; claim no tooth.** The
module `steel/p_segregation_dbtt.py` is wired into nothing — `grain.py` is byte-identical, the frozen
pipeline is untouched.

This is a **mechanistic overlay that confirms Outcome A's flag, not an upgrade** (deliberately the same
class as the temper-embrittlement gate and the B3 legs), because the composite is non-teeth-bearing for
a structural reason:

1. **No in-domain holdout at all.** No cited coverage→DBTT relation sits in the engine's
   transgranular-cleavage domain — every one is the intergranular GB-segregation axis (IF included:
   ferritic matrix, but intergranular for lack of solute carbon, and additionally the fitted steel).
   With nothing in the engine's fracture mode, the cross-steel spread is cross-domain, so it cannot
   falsify — or validate — the engine's transgranular P term.
2. **The "clean form" is itself non-universal.** Even granting the domain, the coverage→DBTT slope is
   per-steel (4.3×) and grain-size-dependent (2×) — there is no single slope to pin.
3. **The bulk→coverage link is underdetermined.** One bulk P maps to a range of coverage via a
   thermal-history-dependent isotherm the bulk content does not fix — the same wall the repo's earlier
   McLean gate hit (temper embrittlement: "underdetermined, not wrong-placed"). **This is the same
   structural finding as the B3 residual gaps (ADR 0009): the term under test co-varies with
   composition / microstructure / thermal history in all clean data.**

No parameter is fitted or grafted — a refit would manufacture a coefficient the physics says cannot
exist as a single number.

## Consequences

- `+` The A2 B-escalation is **resolved on the honest terms the physics supports**: the bulk P→DBTT
  slope's flag is now *mechanistically* justified (a product of two non-universal factors reproducing
  the bracket's width), not merely bracketed — the deferred "make the scatter an output" is delivered as
  an *explanation of the scatter*, which is what the data allows.
- `+` **Zero blast radius.** New module + demo + figure + gallery/README rows + tests; `grain.py` and
  every engine module untouched and byte-identical. The coverage relations are read, never applied to
  the pipeline.
- `+` The **compute-before-framing discipline held**: the numeric check *confirmed* the bracket falls
  out of the mechanism as a span (unlike a false-tooth), and the √d-scaling temptation was caught and
  rejected before any code.
- `+` The **domain-boundary discipline is on the record**: intergranular (prior-austenite-boundary) P
  embrittlement is a different fracture mode from Pickering transgranular cleavage — the coverage
  literature belongs conceptually next to `temper_embrittlement.py`, not grafted onto `grain.py`.
- `−` `grain.ITT_K_P` is **not upgraded** to teeth — it stays a flagged, representative bulk coefficient.
  The mechanism explains the flag; it does not remove it.
- `−` The McLean bridge is a **sensitivity overlay, not a coverage model** — the single-solute isotherm
  under-predicts absolute AES coverage, so it must not be read as predicting measured segregation
  levels; only the *direction and relative* movement with T_seg is used.

## Alternatives considered

- **Compose the McLean bridge onto `grain.cottrell_petch_dbtt_C` and call it a validated coverage-based
  P→DBTT law** — rejected: a category graft (intergranular coverage data onto a transgranular-cleavage
  law) and a by-construction wiring check with no independent in-domain holdout.
- **Build a √d-scaled slope law** (coverage→DBTT slope ∝ Hall–Petch d^−½, reusing grain.py's length
  scale) — rejected as confirmation bias: two SA508 grain sizes fit an exponent −0.57 (not −0.50), the
  authors attribute the slope to GB area per volume (d⁻¹), and the ratio is hardness-confounded.
- **Re-centre `ITT_K_P` on a per-steel measured value (e.g. SA508's 13.31 slope back-mapped)** —
  rejected: the value is arbitrary within the flagged band (A2's finding), and the mechanism shows the
  bulk slope is irreducibly steel-/path-dependent, so any single re-centred digit over-claims.
- **Grade against Auger coverage↔ΔFATT temper-embrittlement data in `temper_embrittlement.py`'s domain**
  — set aside: that is the *intergranular* axis and would test a different (unbuilt) law; the honest
  scope here is why the *engine's existing* transgranular bulk term stays flagged. A coverage-based
  intergranular DBTT model is a named future deferral with its own triad.
