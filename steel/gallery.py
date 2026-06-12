"""The gallery generator: one catalog, one clickable page, kept honest by a test.

`python -m steel.gallery` renders **docs/index.html** — a self-contained, clickable
front door to every surface of the simulator: the banked **visualizations**, the runnable
**demos**, the **experiments** (the composition x cooling sweep and the what-if app), and
the teaching **notebook**.

Why a generator and not a hand-written page? So it cannot rot. `CATALOG` below is the *single*
source of truth (topic, demo module, banked figure, where the same idea lives in the notebook
and the app, and a one-line blurb). The HTML is derived from it, the figures are referenced by
path so a re-banked PNG shows up automatically, and `steel/tests/test_gallery.py` fails the build
if a demo is added without a catalog entry, a figure goes missing, or the committed page drifts
from what this module would regenerate. To refresh after editing the catalog (or adding a demo):

    python -m steel.gallery        # rewrites docs/index.html in place

The page is **GitHub-Pages-ready** (serve from the `/docs` folder): figure `src`s are relative
(`figures/...`) so they render both on Pages and when the file is opened locally; links out to
source, the notebook, and the READMEs are absolute GitHub URLs (Pages only serves `/docs`).
This module has no third-party imports — it is pure stdlib so it runs in any checkout.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

# --- repo geography -----------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCS = _REPO_ROOT / "docs"
_FIGURES = _DOCS / "figures"
_INDEX = _DOCS / "index.html"

# Absolute GitHub base for out-links (Pages serves only /docs, so these can't be relative).
GH = "https://github.com/BoykoNeov/steel-sim/blob/main"
NOTEBOOK_URL = f"{GH}/steel/steel.ipynb"
ROOT_README_URL = f"{GH}/README.md"
STEEL_README_URL = f"{GH}/steel/README.md"


@dataclass(frozen=True)
class Entry:
    """One runnable surface. `module` is the `demo_*` stem under steel/ (so the run command is
    `python -m steel.<module>` and the source link is steel/<module>.py); `figure` is the banked
    PNG filename under docs/figures/; `notebook`/`app` name where the same idea lives interactively
    (None when that surface doesn't cover it)."""

    topic: str
    module: str
    figure: str
    title: str
    blurb: str
    notebook: str | None = None  # e.g. "§1-2" — links to the notebook on GitHub
    app: str | None = None  # e.g. "four fates" — text cue only (the app runs locally)


# The single source of truth. Order = the suggested learning path (it also drives the README
# "guided tour" table — keep the two consistent, but only the demo *names* are guarded by the
# test; blurb wording may differ between surfaces). Topics are emitted as section headers in order.
CATALOG: tuple[Entry, ...] = (
    Entry(
        "Core", "demo_four_curves", "steel-four-curves.png",
        "Four fates of one steel",
        "One 1080 steel, four quench rates → pearlite → bainite → martensite "
        "— the C-curve mechanism beside the microstructure it produces.",
        notebook="§1-2", app="four fates",
    ),
    Entry(
        "Core", "demo_sweep", "steel-sweep.png",
        "Composition × cooling sweep  —  the experiment surface",
        "Every composition against every cooling rate, side by side — the hardenability "
        "axis the four-curves view can't show. This is the experimentation surface; the app makes "
        "it interactive.",
        notebook="§3", app="grid / build-your-own",
    ),
    Entry(
        "Hardenability", "demo_jominy", "steel-jominy-hardness.png",
        "Jominy end-quench",
        "One end-quench bar: shallow-hardening 1045 against deep-hardening 4140, hardness versus "
        "depth from the quenched end.",
        notebook="§3", app="Jominy",
    ),
    Entry(
        "Hardenability", "demo_ideal_diameter", "steel-ideal-diameter.png",
        "Ideal critical diameter",
        "Critical diameter read *from* the model against measured H-band data — does it rank "
        "the steels' hardenability in the right order?",
        notebook="§3",
    ),
    Entry(
        "Tempering", "demo_tempered_jominy", "steel-tempered-jominy.png",
        "Tempered Jominy traverse",
        "A *tempered* Jominy traverse — per-constituent temper of a mixed structure, not a "
        "single hardness knocked down by one number.",
        notebook="§4", app="quench-and-temper",
    ),
    Entry(
        "Grain size", "demo_grain", "steel-grain.png",
        "Grain refinement",
        "Grain refinement — the lone lever that raises strength *and* toughness at once "
        "(same Hall–Petch form, opposite grain-size signs).",
        notebook="§5", app="§5",
    ),
    Entry(
        "Grain size", "demo_grain_morphology", "steel-grain-morphology.png",
        "Grain morphology swatch",
        "Those two grains drawn to scale — a size-accurate microstructure swatch beside the "
        "schematic.",
        notebook="§5", app="§5",
    ),
    Entry(
        "Process routes", "demo_austemper", "steel-austemper.png",
        "Austempering",
        "Quench past the nose, hold isothermally inside the diagram, grow bainite — the "
        "atlas-anchored isothermal hold.",
        notebook="§6", app="§6",
    ),
    Entry(
        "Process routes", "demo_martemper", "steel-martemper-distortion.png",
        "Martempering",
        "The same hardness as a direct quench, far less distortion — the surface−centre "
        "temperature gap closed before the martensite forms.",
        notebook="§6d", app="martempering",
    ),
    Entry(
        "Process routes", "demo_unified_kv", "steel-unified-kv-bay.png",
        "Bainite bay, opened in continuous cooling",
        "The bainite bay *opened* in continuous cooling — three competing reactions "
        "(ferrite / pearlite / bainite) raced on one shared austenite pool.",
        notebook="§6b", app="§6b",
    ),
    Entry(
        "Process routes", "demo_bainite", "steel-bainite.png",
        "Bainite reaction (the negative result)",
        "The cited bainite reaction on its own, and why its bay *can't* form in a plain continuous "
        "cool — the negative-result companion to the unified model.",
    ),
    Entry(
        "Validation", "demo_cct_validation", "steel-cct-validation.png",
        "Cross-composition bainite wall, measured",
        "Does any cited composition factor predict bainite kinetics *across* steels? Eight atlas "
        "steels say no — the per-steel-only wall, measured and quantified (not just asserted), and "
        "the alloy-vs-carbon diagnosis behind it.",
        notebook="§6c",
    ),
    Entry(
        "Stress", "demo_residual", "steel-residual-stress.png",
        "Residual stress & distortion",
        "The residual stress and distortion a quench locks into a section — the "
        "solid-mechanics axis (incremental elastic–perfectly-plastic, transform dilatation "
        "and all).",
        notebook="§6e", app="residual stress",
    ),
    Entry(
        "Case hardening", "demo_carburize", "steel-carburize-gradient.png",
        "Carburizing",
        "A carburized gear tooth: carbon diffused in at the surface, case hardness profiled out "
        "— the same sealed engine as Jominy, a mass-diffusion face.",
        notebook="§8", app="carburizing",
    ),
    Entry(
        "Inverse design", "demo_design", "steel-design.png",
        "Inverse design",
        "Run the simulator backwards: name a target hardness, get a feasible recipe — grade, "
        "quench medium, and temper.",
        notebook="§7", app="§7",
    ),
    Entry(
        "Equilibrium", "demo_calphad", "steel-calphad.png",
        "CALPHAD equilibrium",
        "Real CALPHAD thermodynamics against the parametrised Fe-C diagram the rest of the sim "
        "uses (needs the optional `.[calphad]` extra).",
    ),
)


# --- rendering ----------------------------------------------------------------------------
_CSS = """\
:root {
  --bg: #0f1115; --panel: #171a21; --panel2: #1d2129; --ink: #e7e9ee; --muted: #9aa3b2;
  --line: #2a2f3a; --accent: #ff8a3d; --accent2: #5ab0ff; --code: #0b0d11;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent2); text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 32px 20px 64px; }
header h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: -0.01em; }
header .tag { color: var(--muted); margin: 0 0 22px; font-size: 16px; }
.ways { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;
        margin: 0 0 14px; }
.way { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.way h3 { margin: 0 0 4px; font-size: 15px; }
.way p { margin: 0; color: var(--muted); font-size: 13.5px; }
code, .cmd { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.cmd { display: block; background: var(--code); border: 1px solid var(--line); border-radius: 8px;
       padding: 7px 10px; font-size: 13px; color: #cfe3ff; overflow-x: auto; }
.note { color: var(--muted); font-size: 13.5px; margin: 6px 0 26px; }
h2.section { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent);
             border-bottom: 1px solid var(--line); padding-bottom: 6px; margin: 34px 0 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 18px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
        display: flex; flex-direction: column; transition: border-color .15s, transform .15s; }
.card:hover { border-color: #3a4150; transform: translateY(-2px); }
.card .shot { display: block; background: var(--panel2); border-bottom: 1px solid var(--line); }
.card .shot img { display: block; width: 100%; height: 188px; object-fit: contain; background: #fff; }
.card .body { padding: 13px 15px 15px; display: flex; flex-direction: column; gap: 9px; flex: 1; }
.card h3 { margin: 0; font-size: 17px; }
.card .blurb { margin: 0; color: var(--muted); font-size: 13.5px; flex: 1; }
.card .links { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 13px; padding-top: 2px;
               border-top: 1px solid var(--line); margin-top: 2px; }
.card .links .sep { color: var(--line); }
.chip { display: inline-block; font-size: 11px; color: var(--muted); border: 1px solid var(--line);
        border-radius: 999px; padding: 1px 8px; }
footer { color: var(--muted); font-size: 13px; margin-top: 44px; border-top: 1px solid var(--line);
         padding-top: 18px; }
em { color: #c8cee0; font-style: italic; }
"""


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _card_html(e: Entry) -> str:
    fig_rel = f"figures/{e.figure}"
    src = f"{GH}/steel/{e.module}.py"
    links = [
        f'<a href="{fig_rel}" target="_blank" rel="noopener">figure ↗</a>',
        f'<a href="{src}" target="_blank" rel="noopener">source ↗</a>',
    ]
    if e.notebook:
        links.append(
            f'<a href="{NOTEBOOK_URL}" target="_blank" rel="noopener">notebook {_esc(e.notebook)} ↗</a>'
        )
    if e.app:
        links.append(f'<span class="chip">app: {_esc(e.app)}</span>')
    links_html = '<span class="sep">|</span>'.join(links)
    return (
        '    <article class="card">\n'
        f'      <a class="shot" href="{fig_rel}" target="_blank" rel="noopener">'
        f'<img src="{fig_rel}" alt="{_esc(e.title)}" loading="lazy"></a>\n'
        '      <div class="body">\n'
        f'        <h3>{_esc(e.title)}</h3>\n'
        f'        <p class="blurb">{_esc(e.blurb)}</p>\n'
        f'        <code class="cmd">python -m steel.{e.module}</code>\n'
        f'        <div class="links">{links_html}</div>\n'
        '      </div>\n'
        '    </article>'
    )


def _sections_html() -> str:
    out: list[str] = []
    current: str | None = None
    for e in CATALOG:
        if e.topic != current:
            if current is not None:
                out.append("  </div>")  # close previous grid
            out.append(f'  <h2 class="section">{_esc(e.topic)}</h2>')
            out.append('  <div class="grid">')
            current = e.topic
        out.append(_card_html(e))
    if current is not None:
        out.append("  </div>")
    return "\n".join(out)


def render_html() -> str:
    """Render the full index page as a string. Deterministic (no timestamps) so the drift test
    can byte-compare it against the committed file."""
    ways = (
        '  <div class="ways">\n'
        '    <div class="way"><h3>▶ Demos &amp; visualizations</h3>'
        '<p>Each card runs one <code>python -m steel.&lt;name&gt;</code> demo, prints its validation '
        'table, and banks the figure shown. Needs only <code>.[viz]</code>.</p></div>\n'
        f'    <div class="way"><h3>\U0001f9ea Experiments</h3>'
        '<p>The <strong>composition × cooling sweep</strong> below, and the interactive '
        '<strong>what-if app</strong> (<code>streamlit run steel/app.py</code>) — pick a grade, '
        'quench, and section size and watch the microstructure move.</p></div>\n'
        f'    <div class="way"><h3>\U0001f4d3 Notebook</h3>'
        f'<p>The narrative teaching path with sliders. New here? Open the '
        f'<a href="{NOTEBOOK_URL}" target="_blank" rel="noopener">notebook</a> and read '
        '"Start here — the 30-second mental model", then go top to bottom.</p></div>\n'
        '  </div>'
    )
    body = (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <title>steel-sim — visual gallery &amp; guided tour</title>\n'
        f'  <style>\n{_CSS}  </style>\n'
        '</head>\n'
        '<body>\n'
        '  <div class="wrap">\n'
        '  <header>\n'
        '    <h1>steel-sim — visual gallery &amp; guided tour</h1>\n'
        '    <p class="tag">Composition + cooling in, microstructure and properties out. '
        'Click any card to open its figure full-size, or copy its run command. '
        'Every surface of the simulator — visualizations, demos, experiments, and the '
        'notebook — in one place.</p>\n'
        '  </header>\n'
        f'{ways}\n'
        '  <p class="note">Suggested first pass: '
        '<code>demo_four_curves</code> → <code>demo_jominy</code> → '
        '<code>demo_sweep</code> → <code>demo_tempered_jominy</code>, then branch by interest. '
        'Install &amp; launch commands are in the '
        f'<a href="{ROOT_README_URL}" target="_blank" rel="noopener">README</a>; the physics and '
        f'validation behind each demo are in '
        f'<a href="{STEEL_README_URL}" target="_blank" rel="noopener">steel/README.md</a>.</p>\n'
        f'{_sections_html()}\n'
        '  <footer>\n'
        '    This page is generated by <code>python -m steel.gallery</code> from a single catalog '
        'in <code>steel/gallery.py</code>, and a test (<code>test_gallery.py</code>) fails the build '
        'if it drifts — add a demo and its figure, regenerate, and it appears here automatically. '
        f'&nbsp;·&nbsp; <a href="{ROOT_README_URL}" target="_blank" rel="noopener">README</a> '
        f'&nbsp;·&nbsp; <a href="{NOTEBOOK_URL}" target="_blank" rel="noopener">notebook</a> '
        f'&nbsp;·&nbsp; <a href="https://github.com/BoykoNeov/steel-sim" target="_blank" '
        'rel="noopener">repository</a>\n'
        '  </footer>\n'
        '  </div>\n'
        '</body>\n'
        '</html>\n'
    )
    return body


def write_index(path: Path = _INDEX) -> Path:
    """Write the rendered page to `path` with LF newlines (so the byte-compare test is stable on
    Windows + autocrlf). Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(), encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    written = write_index()
    print(f"wrote {written.relative_to(_REPO_ROOT)}  ({len(CATALOG)} entries)")
