"""Firewall guard (``game.md`` §2/§4) — ``game/`` orchestrates engines, it never reimplements physics.

The structural discipline that replaces a physics validation triad for this package. These checks are
concrete and discriminating (per the advisor): the logic layers are pure (no streamlit/matplotlib), the
only ``import streamlit`` is the lazy one in :mod:`game.app_game`, and ``game`` reaches past the public
engine surface for **no** private internal. (That ``game`` defines no *physics constant* is review
discipline, not directly testable — the test name does not imply coverage it lacks.)
"""
import importlib
import re
from pathlib import Path

import game

GAME_DIR = Path(game.__file__).resolve().parent
LOGIC_MODULES = ("state", "knobs", "teach", "choices", "postmortem")   # pure logic (no streamlit/matplotlib)


def _source(stem: str) -> str:
    return (GAME_DIR / f"{stem}.py").read_text(encoding="utf-8")


def _imports(src: str, module: str) -> list[str]:
    """Real import STATEMENTS of ``module`` (``import m`` / ``from m import …``) — prose mentions excluded.

    The discipline is about what the code *imports*, not what its docstrings *mention* — so this matches an
    import statement at line start (after any indentation), never a backtick'd reference in prose.
    """
    pat = rf"(?m)^[ \t]*(?:import {module}\b|from {module}[.\w]* import\b)"
    return re.findall(pat, src)


def test_logic_layers_are_pure_and_import_clean():
    # The three logic modules must not IMPORT streamlit or matplotlib at all (the app.py three-layer rule),
    # and must import cleanly on the bare core (this very import would fail if they pulled a UI/viz dep).
    for stem in LOGIC_MODULES:
        importlib.import_module(f"game.{stem}")
        src = _source(stem)
        assert not _imports(src, "streamlit"), f"game.{stem} is a logic layer — it must not import streamlit"
        assert not _imports(src, "matplotlib"), f"game.{stem} is a logic layer — it must not import matplotlib"


def test_streamlit_is_confined_to_app_game_and_lazy():
    # The firewall deliverable: streamlit is IMPORTED only in the paper-thin UI module, and even there
    # lazily (inside main, so indented), so importing the package never drags streamlit in.
    offenders = [
        p.name for p in GAME_DIR.glob("*.py")
        if _imports(p.read_text(encoding="utf-8"), "streamlit") and p.name != "app_game.py"
    ]
    assert offenders == [], f"streamlit imported outside app_game.py: {offenders}"

    app_src = _source("app_game")
    assert _imports(app_src, "streamlit"), "app_game must own the (one) streamlit import"
    assert not re.search(r"(?m)^import streamlit", app_src), "streamlit must be imported lazily inside main()"


def test_figures_layer_holds_no_streamlit_and_imports_matplotlib_lazily():
    # The figure layer wraps the render stack but is not the UI: no streamlit, and matplotlib only inside
    # functions (so `import game.figures` works on a core install — the package stays import-light).
    src = _source("figures")
    assert not _imports(src, "streamlit")
    assert not re.search(r"(?m)^import matplotlib", src), "matplotlib must be imported lazily in figures.py"
    importlib.import_module("game.figures")           # imports without matplotlib present-or-not


def test_no_private_engine_imports():
    # game reaches only the PUBLIC engine surface: it imports no underscore-prefixed steel internal
    # (a private import would be reaching past the firewall into engine guts).
    bad: list[tuple[str, str]] = []
    for p in GAME_DIR.glob("*.py"):
        for m in re.finditer(r"from steel[.\w]* import (.+)", p.read_text(encoding="utf-8")):
            names = [n.strip().split(" as ")[0] for n in m.group(1).split(",")]
            bad += [(p.name, n) for n in names if n.startswith("_")]
    assert bad == [], f"private steel imports reach past the firewall: {bad}"
