---
name: matcalc-mc-fe-database-source
description: Source/license for the MatCalc mc_fe steel TDB + the bundled cfe_broshe Fe-C DB that Phase 4 CALPHAD uses
metadata: 
  node_type: memory
  type: reference
  originSessionId: 05bc7ecd-f71f-40fa-9d85-d359a9d7e9d4
---

The thermodynamic databases Steel Phase 4 ([[bigsim-program]]) validates against —
**never committed** (plan §6 / `.gitignore` covers `*.tdb`, `data/`):

- **Multicomponent steel:** `mc_fe_v2.060.tdb`, the **MatCalc steel database**,
  assessed at TU Wien by **Erwin Povoden-Karadeniz**. **Openly licensed under
  ODbL 1.0** (Open Database License, https://opendatacommons.org/licenses/odbl/1-0/) +
  the DbCL contents license — free to use. Download:
  `https://www.matcalc.at/images/stories/Download/Database/mc_fe_v2.060.tdb`
  (open-databases page: https://www.matcalc.at/index.php/databases/open-databases).
  `calphad_backend.download_mc_fe()` fetches it to gitignored `data/tdb/`.
  **GOTCHA (found 2026-06-09 building full-gate CI):** matcalc.at (a Joomla host) 403s
  the default `Python-urllib/x.y` User-Agent — any *other* UA (even `python-requests`)
  gets 200. The original `download_mc_fe()` used a bare `urlretrieve` (default UA) → it
  would 403 on any fresh fetch (CI *and* a user; the local file predated the filter).
  Fixed to send `User-Agent: Mozilla/5.0`. Relevant to CI: the workflow caches `data/tdb`
  (key `mc-fe-v2.060`), so this download only fires on cache miss (first run / ~7-day
  eviction) — if matcalc.at is down then, the multicomponent live test 403s the run.
  Covers
  Fe-C-Cr-Mn-Mo-Ni-Si-V-… → 4140. **pycalphad cannot parse the raw file** (it has
  `REFERENCE_ELEMENT`/`ADD_COMPOSITION_SET` metadata, molar-volume/mobility params,
  and ~8 wildcard-`G` params) → `load_clean_database` keeps only grammar-parseable
  commands + prunes constituent-less phases. The pycalphad-*bundled* `mc_fecocrnbti.tdb`
  is a **stripped subset** ("only Fe-Co-Cr-Nb-Ti retained") — **unusable for carbon
  steel** (gives all-ferrite, no austenite); the full download is required.

- **Binary Fe-C:** `cfe_broshe.tdb`, an SGTE-style (91Din/10Hal functions)
  metastable Fe-C assessment **bundled inside the installed pycalphad package**
  (`pycalphad/tests/databases/`). Present on any pip-installed pycalphad → the
  binary Phase-4 live tests need no external file. Used as a validation reference,
  not redistributed (`bundled_fe_c_database_path()`).

Both are used as **validation references only** (plan §6 explicitly permits even a
commercial/research DB validation-only, never redistributed); Phase 4 commits only the
*numbers computed from them* (`calphad_reference.REFERENCE`), the same status as the
other cited benchmark constants ([[maynier-hardness-source]], [[hollomon-jaffe-tempering-source]], [[carburize-diffusivity-source]]).
