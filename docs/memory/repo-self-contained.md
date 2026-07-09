---
name: repo-self-contained
description: "Standing constraint — steel-sim must be standalone; don't depend on the BigSim monorepo/archive existing"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 61386094-060e-433e-baa7-7bd5d6549384
---

User instruction (2026-06-11): **"don't count on monorepo future existence."**
steel-sim must be **standalone and self-contained** — nothing in the repo may
depend on the BigSim monorepo (or its GitHub archive) continuing to exist.

**Why:** the repo was extracted from the BigSim monorepo on 2026-06-10, but the
monorepo/archive may be deleted. Docs that point a *present reader* at
`ARCHITECTURE.md §N` / `PORTFOLIO.md`, or that present the BigSim archive link
as a go-to resource, break if it vanishes.

**How to apply:**
- Distinguish **directive vs record** (the discriminating test): a live doc that
  *tells a current reader to go look at* the monorepo → fix (restate the
  rationale locally). A *dated* plan/ADR that merely *records what the build was
  authored against* ("built to ARCHITECTURE.md's template") → leave it; it's
  history, like a commit message naming a since-removed file. Don't scrub the
  dated records — that falsifies history and over-churns.
- New docs: restate rationale locally (ADRs, plan, module docstrings); don't
  cite `ARCHITECTURE.md`/`PORTFOLIO.md` as if reachable.
- The root README **Provenance** section is the single self-contained
  explanation of what those program-level files were + that they aren't required
  here. It no longer presents the archive link as a resource.
- **Verified-safe, keep upstream:** `calphad_backend.download_mc_fe()`'s
  `MC_FE_URL` points at upstream `matcalc.at` (TU Wien), NOT the BigSim repo —
  so losing the monorepo does not break CALPHAD DB fetching. Keep it upstream;
  never repoint it at a BigSim mirror. See [[matcalc-mc-fe-database-source]].

Applied 2026-06-11: neutralized the dangling `ARCHITECTURE.md §N`/`PORTFOLIO.md`
citations in the live surfaces (root + engine + steel READMEs, CONTRACT,
`engines/__init__`, `plots.py`, `sweep.py` docstrings) + rewrote README
Provenance; plan/ADRs left as dated build-history.

**Extended 2026-07-06 — the sibling-project scrub (user: "remove references to
microchip and planet, this will have nothing to do with them anymore").** The
user chose scope **"scrub forward, trim history"** (over "purge everything" and
"live docs only"): removed ALL live/forward microchip/planet references from the
live/directive docs (engine CONTRACT/README "they depend on this"; ADR 0003's
"Successor after Microchip lands" section — its machinery `tools/gate.py` +
`projects/` was **never extracted** into this repo, so rewritten as a retired
program concern; ADR 0002/0004 + steel-production/steel-making reuse+roadmap
claims → generic "consumer" language; next-directions **§C removed**; README
Provenance reduced to a neutral line that no longer names the siblings). **KEPT
as history:** dated build-context mentions (given a standalone-repo banner in
steel-production.md) and the in-repo `docs/memory/*.md` build logs (left
untouched per the chosen scope — so a future grep still finds microchip/planet
there; that is by design, not an oversight). Commit `6c0733b`. So the rule is now
stronger than the 2026-06-11 directive: don't just avoid *citing* the monorepo —
don't present microchip/planet as a live/forward relationship at all.
