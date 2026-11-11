"""Every Manim symbol the design documents cite must still exist.

The design documents cite Manim source by ``module.py::Symbol``, sometimes with its
directory in front, and give a line number only as a hint. Symbols survive a version
bump, line numbers do not — so this test imports each cited symbol and fails by name
when upstream renames or removes one. It is the acceptance criterion in
`docs/plan.md`, not a behavioural test.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

DOCS = (
    Path(__file__).parents[1] / "docs/plan.md",
    Path(__file__).parents[1] / "docs" / "scope.md",
    Path(__file__).parents[1] / "docs" / "grill-log.md",
    *sorted((Path(__file__).parents[1] / "docs" / "adr").glob("*.md")),
    # The acceptance tables and the parity survey cite Manim too (row SY-1, task 13).
    *sorted((Path(__file__).parents[1] / "docs" / "acceptance").glob("*.md")),
    Path(__file__).parents[1] / "docs" / "parity-survey.md",
)

# The Manim module each cited file name lives in. A citation names the file, because
# that is what a reader greps for; the import needs the package path.
MODULE_OF_FILE = {
    "animation.py": "manim.animation.animation",
    "cairo_renderer.py": "manim.renderer.cairo_renderer",
    "coordinate_systems.py": "manim.mobject.graphing.coordinate_systems",
    "creation.py": "manim.animation.creation",
    "fading.py": "manim.animation.fading",
    "family_ops.py": "manim.utils.family_ops",
    "functions.py": "manim.mobject.graphing.functions",
    "indication.py": "manim.animation.indication",
    "logger_utils.py": "manim._config.logger_utils",
    "mobject.py": "manim.mobject.mobject",
    "number_line.py": "manim.mobject.graphing.number_line",
    "scale.py": "manim.mobject.graphing.scale",
    "scene.py": "manim.scene.scene",
    "transform.py": "manim.animation.transform",
    "vectorized_mobject.py": "manim.mobject.types.vectorized_mobject",
}

CITATION = re.compile(r"`(?:[a-z_]+/)*([a-z_]+\.py)::([A-Za-z_][A-Za-z0-9_.]*)`")

# Prose describing the citation format itself, not a citation.
PLACEHOLDERS = {("file.py", "Symbol"), ("module.py", "Symbol")}


def citations() -> set[tuple[str, str]]:
    """Every ``file.py::Symbol.attr`` citation across the design documents."""
    found: set[tuple[str, str]] = set()
    for doc in DOCS:
        found |= set(CITATION.findall(doc.read_text(encoding="utf-8")))
    return found - PLACEHOLDERS


def test_the_documents_actually_cite_something() -> None:
    assert len(citations()) >= 15


@pytest.mark.parametrize("file_name,dotted", sorted(citations()))
def test_cited_symbol_exists(file_name: str, dotted: str) -> None:
    module_name = MODULE_OF_FILE.get(file_name)
    assert module_name is not None, f"no module known for the cited file {file_name}"

    obj: object = importlib.import_module(module_name)
    walked = module_name
    for part in dotted.split("."):
        assert hasattr(obj, part), (
            f"{walked} has no {part} (cited as {file_name}::{dotted})"
        )
        obj = getattr(obj, part)
        walked = f"{walked}.{part}"
