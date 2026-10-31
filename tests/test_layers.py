"""The layer rules of ADR 0001 §1, checked on the parsed source.

Rows L-1, L-2 and C-3 of `docs/acceptance/06-core-contracts.md`. The check is static
because a runtime one cannot work: importing any submodule first runs
`manim_plots/__init__.py`, which imports the Manim layer.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "manim_plots"
CORE = PACKAGE / "core"
CONTEXT = PACKAGE / "mobjects" / "context.py"
FRAME_NAMES = {"_getframe", "currentframe", "f_code", "f_locals", "f_back"}


def modules(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def forbidden_imports(path: Path) -> list[str]:
    """Imports of Manim or of the Manim layer in one core module."""
    found = []
    for node in ast.walk(tree(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top == "manim" or alias.name.startswith(
                    ("manim_plots.mobjects", "manim_plots.animations")
                ):
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0:
                if module.split(".")[0] == "manim" or module.startswith(
                    ("manim_plots.mobjects", "manim_plots.animations")
                ):
                    found.append(module)
            elif node.level >= 2:
                # Both packages belong to the Manim layer (ADR 0008 §1).
                names = {alias.name for alias in node.names}
                if module.split(".")[0] in {"mobjects", "animations"} or (
                    not module and names & {"mobjects", "animations"}
                ):
                    found.append("." * node.level + module)
    return found


def test_the_core_exists():
    assert len(modules(CORE)) >= 4


@pytest.mark.parametrize("path", modules(CORE), ids=lambda p: p.name)
def test_l1_the_core_imports_no_manim(path):
    assert forbidden_imports(path) == []


def frame_names(path: Path) -> set[str]:
    used = set()
    for node in ast.walk(tree(path)):
        if isinstance(node, ast.Attribute) and node.attr in FRAME_NAMES:
            used.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in FRAME_NAMES:
            used.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            used |= {a.name for a in node.names} & FRAME_NAMES
    return used


@pytest.mark.parametrize(
    "path",
    [p for p in modules(PACKAGE) if p != CONTEXT],
    ids=lambda p: str(p.relative_to(PACKAGE)),
)
def test_l2_only_context_reads_the_call_stack(path):
    assert frame_names(path) == set()


def test_l2_the_check_would_see_a_frame_read():
    sample = "import sys\nframe = sys._getframe(1)\ncode = frame.f_code\n"
    found = set()
    for node in ast.walk(ast.parse(sample)):
        if isinstance(node, ast.Attribute) and node.attr in FRAME_NAMES:
            found.add(node.attr)
    assert found == {"_getframe", "f_code"}


def test_c3_the_core_package_imports_none_of_its_submodules():
    init = tree(CORE / "__init__.py")
    for node in ast.walk(init):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"core/__init__.py imports .{node.module}"
            assert not (node.module or "").startswith("manim_plots")
        elif isinstance(node, ast.Import):
            assert all(not a.name.startswith("manim_plots") for a in node.names)
