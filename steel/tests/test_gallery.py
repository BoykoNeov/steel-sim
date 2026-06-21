"""The drift guard for the clickable gallery page (docs/index.html).

The whole point of generating the page (rather than hand-writing it) is that it cannot silently
rot. These checks are the enforcement loop the user asked for — "keep it up to date":

  * the catalog and the demos on disk are the *same set* (add a demo → must catalog it);
  * every catalogued figure is actually banked under docs/figures/;
  * every demo is named somewhere in the root README (a format-independent "did you wire up the
    other surfaces?" nudge — it does not couple to the README's table layout);
  * the committed docs/index.html is byte-identical to what gallery.render_html() produces now
    (so editing the catalog without regenerating fails the build — run `python -m steel.gallery`).

All fast/unmarked so they gate in the `-m "not slow"` lane and in CI. No viz/optional deps.
"""
from pathlib import Path

import pytest

from steel import gallery
from steel.gallery import CATALOG

_REPO_ROOT = Path(gallery.__file__).resolve().parent.parent
_FIGURES = _REPO_ROOT / "docs" / "figures"
_INDEX = _REPO_ROOT / "docs" / "index.html"
_README = _REPO_ROOT / "README.md"

# The packages a gallery demo can live in (the library + the playable spinoff). Each entry's `package`
# field says which; the coverage check resolves the demo file under that package's directory.
_PACKAGES = ("steel", "game")


def _disk_demo_modules() -> set[tuple[str, str]]:
    """`(package, module)` for every `demo_*.py` on disk across the catalogued packages."""
    return {(pkg, p.stem) for pkg in _PACKAGES for p in (_REPO_ROOT / pkg).glob("demo_*.py")}


def test_catalog_covers_exactly_the_demos_on_disk():
    catalogued = {(e.package, e.module) for e in CATALOG}
    on_disk = _disk_demo_modules()
    missing = on_disk - catalogued
    extra = catalogued - on_disk
    assert not missing, f"demos on disk but absent from gallery CATALOG: {sorted(missing)}"
    assert not extra, f"CATALOG names a demo with no demo_*.py file: {sorted(extra)}"


def test_catalog_has_no_duplicate_modules_or_figures():
    modules = [e.module for e in CATALOG]
    figures = [e.figure for e in CATALOG]
    assert len(modules) == len(set(modules)), "duplicate module in CATALOG"
    assert len(figures) == len(set(figures)), "two entries point at the same figure"


def test_every_catalogued_figure_is_banked():
    for e in CATALOG:
        assert (_FIGURES / e.figure).is_file(), (
            f"{e.module} → docs/figures/{e.figure} is missing "
            "(re-run the demo to bank it, or fix the catalog filename)"
        )


def test_each_demo_is_named_in_root_readme():
    # Format-independent: the demo's module string must appear *somewhere* in the README, so a
    # newly added demo can't be cataloged on the page yet forgotten on the repo's front door.
    text = _README.read_text(encoding="utf-8")
    for e in CATALOG:
        assert e.module in text, f"{e.module} is on the gallery page but not mentioned in README.md"


def test_committed_index_html_is_in_sync():
    assert _INDEX.is_file(), "docs/index.html is missing — run `python -m steel.gallery`"
    committed = _INDEX.read_text(encoding="utf-8").replace("\r\n", "\n")
    fresh = gallery.render_html().replace("\r\n", "\n")
    assert committed == fresh, (
        "docs/index.html is stale — regenerate it with `python -m steel.gallery` and commit."
    )
