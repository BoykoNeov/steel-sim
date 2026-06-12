---
name: gallery-page
description: docs/index.html is a generated clickable front-door gallery; how it stays current
metadata: 
  node_type: memory
  type: project
  originSessionId: 37eb057b-35b2-4ad0-9dcb-628063bece5a
---

**The clickable front door = `docs/index.html`**, a generated visual gallery of every demo
(figure + run command + notebook/app links). Built 2026-06-12 in answer to "make a webpage that
takes you to the visualizations/demos/experiments/notebooks and keeps it up to date".

- **Single source of truth:** the `CATALOG` tuple in `steel/gallery.py`. The HTML is *rendered*
  from it (`render_html()`, deterministic — no timestamps), written by `python -m steel.gallery`.
  Pure stdlib, no third-party imports.
- **Keep-it-current contract (the point):** `steel/tests/test_gallery.py` (fast/unmarked, gates
  in the `not slow` lane) fails the build if — catalog ≠ `demo_*.py` set on disk, a figure is
  unbanked, a demo isn't named in `README.md`, or the committed page ≠ a fresh render
  (LF-normalized byte-compare). **So: after adding a demo or editing a blurb, run
  `python -m steel.gallery` and commit `docs/index.html`, or CI goes red.**
- Figures are referenced by relative path (`figures/...`) → a re-banked PNG shows up
  automatically; source/notebook/README out-links are absolute GitHub URLs (Pages serves only
  `/docs`). Page works both on GitHub Pages-from-`/docs` and via local `file://`.
- **Pages not enabled** (a repo-settings action, left to the user): enabling Pages on `/docs`
  serves it at `https://boykoneov.github.io/steel-sim/`.
- The root README "guided tour" table is the same map in Markdown (sibling, not generated from
  the catalog — only the demo *names* are cross-guarded; blurb wording may differ).
- Local HTML preview on this Windows box: headless Edge at
  `C:\Program Files (x86)\Microsoft\EdgeCore\<ver>\msedge.exe --headless=new --screenshot=...`
  (Edge isn't on PATH; not under the usual `Program Files\Microsoft\Edge` dir either).
