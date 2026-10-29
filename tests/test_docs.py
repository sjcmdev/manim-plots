"""The user documentation: its pages, the differences from Manim, and runnable code
(F-1008, F-1009).

Rows DO-2 to DO-4 of `docs/acceptance/14-docs-release.md`. DO-1, the warning-free build,
is a step of `tools/check.py`.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest
from manim import Scene, tempconfig

import manim_plots as mp
from manim_plots.mobjects.leaves import Leaf

SITE = Path(__file__).parents[1] / "docs" / "site"
PAGES = ["index", "coming-from-manim", "differences", "gallery", "api"]
MEDIA = Path(__file__).parent / "visual" / "_out" / "media"


def page(name: str) -> str:
    return (SITE / f"{name}.rst").read_text(encoding="utf-8")


# --- DO-2 ----------------------------------------------------------------------------


@pytest.mark.parametrize("name", PAGES)
def test_do2_every_page_exists(name):
    assert page(name).strip()


def test_do2_the_api_page_documents_every_public_name():
    api = page("api")
    for name in [*mp.__all__, "Axes", "NumberPlane", "Axis"]:
        if name == "__version__":
            continue
        assert re.search(rf"\b{re.escape(name)}\b", api), name


def test_do2_the_gallery_shows_reviewed_pictures():
    gallery = page("gallery")
    images = re.findall(r"\.\. (?:image|figure):: (\S+)", gallery)
    assert len(images) >= 4
    for image in images:
        assert (SITE / image).resolve().exists() or image.startswith("_"), image


# --- DO-3 ----------------------------------------------------------------------------

# Each difference F-1008 lists, as words its section must contain.
DIFFERENCES = {
    "Create after Uncreate": ["Uncreate", "Create"],
    "permanent changes": ["permanent", "Rotate(ax, TAU)"],
    "the double move": ["twice"],
    "bound helper labels": ["get_graph_label"],
    "raising conversions": ["c2p", "p2c", "NaN"],
    "late binding": ["loop variable"],
    "simulation": ["callback"],
    "refresh": ["refresh()"],
    "non-affine frames": ["non-affine"],
    "PhaseFlow": ["PhaseFlow"],
    "tick placement": ["multiples of the step"],
    "the frame's lag slot": ["24/25"],
    "partial drawing": ["sample"],
    "Transform pairs ticks": ["Transform", "key"],
    "registration": ["ax.add"],
    "singular frame": ["singular"],
    "unknown axis_config key": ["axis_config"],
    "the defaults table's fixes": ["tip"],
}


@pytest.mark.parametrize("name", list(DIFFERENCES))
def test_do3_the_differences_page_states_each(name):
    text = page("differences")
    for word in DIFFERENCES[name]:
        assert word in text, (name, word)


WHERE_MET = {
    "FunctionPlot (Uncreate)": (mp.FunctionPlot, "Uncreate"),
    "CartesianAxes (permanent changes)": (mp.CartesianAxes, "permanent"),
    "Leaf.refresh": (Leaf.refresh, "point"),
    "CartesianAxes.c2p": (mp.CartesianAxes.c2p, "raise"),
    "CartesianAxes.plot (late binding)": (mp.CartesianAxes.plot, "loop"),
    "MultipleLocator (multiples)": (mp.MultipleLocator, "multiple"),
    "CartesianAxes (lag slot)": (mp.CartesianAxes, "Create"),
    "FunctionPlot (paced by sample)": (mp.FunctionPlot, "sample"),
}


@pytest.mark.parametrize("name", list(WHERE_MET))
def test_do3_each_difference_is_stated_where_users_meet_it(name):
    obj, word = WHERE_MET[name]
    assert word.lower() in (obj.__doc__ or "").lower(), name


# --- DO-4 ----------------------------------------------------------------------------

BLOCK = re.compile(
    r"^\.\. code-block:: python\n((?:\n|[ \t]+.*\n)+)", re.MULTILINE
)


def blocks() -> list[tuple[str, int, str]]:
    found = []
    for path in sorted(SITE.glob("*.rst")):
        text = path.read_text(encoding="utf-8")
        for k, match in enumerate(BLOCK.finditer(text)):
            found.append((path.stem, k, textwrap.dedent(match.group(1))))
    return found


BLOCKS = blocks()


def test_do4_the_site_has_code():
    assert len(BLOCKS) >= 5


@pytest.mark.parametrize(
    "where, index, code", BLOCKS, ids=[f"{w}-{i}" for w, i, _ in BLOCKS]
)
def test_do4_every_code_block_runs(where, index, code):
    config = {
        "dry_run": True,
        "disable_caching": True,
        "progress_bar": "none",
        "media_dir": str(MEDIA),
        "pixel_width": 320,
        "pixel_height": 180,
        "frame_rate": 6,
    }
    namespace: dict[str, object] = {"__name__": f"docs_{where}_{index}"}
    with tempconfig(config):
        exec(compile(code, f"{where}.rst block {index}", "exec"), namespace)
        for value in list(namespace.values()):
            # Only the scenes the block defines, not the ones a star import brings.
            if (
                isinstance(value, type)
                and issubclass(value, Scene)
                and value.__module__ == namespace["__name__"]
            ):
                value().render()
