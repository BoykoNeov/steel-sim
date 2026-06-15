---
name: sulfide-morphology-built
description: "MnS morphology (the signed sulfur foil — free-machining asset vs through-thickness toughness liability) BUILT 2026-06-15; closes the impurity build's tied-sulfide deferral"
metadata:
  node_type: memory
  type: project
---

**MnS inclusion morphology — the SIGNED SULFUR FOIL — BUILT ✓ 2026-06-15** (user picked "a smaller physics
build" → "MnS morphology consequences" from a what-next menu). Closes the two deferrals
[[impurity-consequence-built]] named together (MnS fracture-anisotropy / transverse-toughness debit + the
good-impurity free-machining use of S) as **one** module — stronger than two thin consumers (advisor).
`steel/sulfide_morphology.py` + demo + `plots.sulfide_morphology_figure` + tests (16 + 5 = **+21**, fast lane
**884 green**); standalone, **NO engine, NO ADR**; gallery card + root-README row + plan §14 banner.

**The module = the worked-product sibling of red-shortness ([[impurity-consequence-built]]/hot_work):** where
red-short reads the **free** sulfur Mn failed to tie, this reads the **tied** MnS that *did* form — because that
sulfide is itself **signed**. The SAME MnS (`slag.manganese_sulfide().mns_pct` → volume fraction by cited
density ratio ρ_MnS 4.0 / ρ_steel 7.87) is a deliberate **free-machining** asset (why 11xx exist — MnS breaks
the chip) AND a **through-thickness toughness** liability (hot working elongates plastic MnS into stringers
that gut the short-transverse direction). Lever = **sulfide shape control** (Ca/RE/Te → globular → keeps the
benefit, removes the debit). Hero = same sulfur, the SHAPE decides: 1144-type (S 0.24, MnS 1.27 vol%) as-rolled
= free-machining + anisotropic (S-T 43% < 50% spec); globular = free-machining + isotropic; plain 1045 (S 0.02)
= tough but not free-machining.

**THE LOAD-BEARING ADVISOR CATCH (pre-code): gate the anisotropy flag on MORPHOLOGY, never on a sulfur
threshold.** slag's flat `high-sulfur` (S > 0.040) **already fires on every free-machining grade by design**
(its own comment: "free-machining grades run higher"; 11xx run 0.08–0.33 %S) → gating on S would just
**re-derive red-short** and brand every free-cutting steel "defective" for being itself. So the build
**disambiguates** the already-firing flat flag into its good half (free-machining = positive readout, NO
`add_defect`) and bad half (`sulfide-anisotropy` defect, gated on shape). The fix is shape control, NOT
desulfurization.

**Honesty (the red-short/hot-tear landing): NO claimable tooth — and NO manufactured coherence note (advisor).**
MnS amount = cited stoichiometry, volume = cited density ratio, both verdicts by-construction `if` rules. "One
MnS, two opposite signs" is the **pedagogical** point — one number, two laws, opposite signs — **by
construction, NOT dressed as a coherence note** (that's the precise Mushet near-miss move, declined; red-short
landed with none too). **Machinability index = REPRESENTATIVE, ranking/OoM only, hardness/carbon + Pb/Ca/Te
confound NAMED out loud** (a higher-C resulfurized grade can machine *worse* than a lower-C plain one despite
more MnS) — the MnS contribution only, never the AISI rating (where I'd manufacture a tooth, per advisor).
Transverse debit = its **own directional axis** (pinned carbon-invariant in test), **NOT**
`properties.toughness_index` or DBTT — the repo polices now-false cross-refs, so the docstring says so.

**Structure mirrors hot_work/hot_tear:** Heat → ProcessStep → add_defect; split test that an anisotropic heat
heat-treats byte-identically (MnS morphology INERT in heat_treat). **Ceiling:** stringer aspect ratio (∝
rolling reduction) unmodelled — elongated/globular is a 2-state stand-in; through-thickness loading assumed;
MnS elongates because plastic (rigid oxides stay spherical) = narrative. Updated hot_work.py docstring (the
deferral text → points at the consumer). Sibling [[temper-embrittlement-built]]/[[tempered-martensite-embrittlement-built]];
amends [[impurity-consequence-built]]. **Next = `game/`** (all front-end chain + consequences + this signed
foil built) or another named deferral (Wootz V/Mo carbide banding = the one real physics gap; F2→F3 deox→recovery).
