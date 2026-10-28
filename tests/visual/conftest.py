"""Visual baselines: rendered frames compared with reviewed PNGs (ADR 0002).

A test marked ``render`` takes the ``visual`` fixture and hands it a ``construct``
function. The fixture renders it with Cairo and compares the result with
``baselines/<module>/<test>.png``: the last frame, or every frame tiled into one grid.
On a mismatch it writes the render and a diff under ``_out/`` for review.
``--update-baselines`` writes a missing or changed baseline instead of failing, and the
maintainer reviews it in the commit.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pytest
from manim import Scene, tempconfig
from manim.renderer.cairo_renderer import CairoRenderer
from numpy.typing import NDArray
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[1]

# Manim's own tolerances (manim/utils/testing/_frames_testers.py): a value may be off
# by one, and fewer than 0.001 % of values may differ by more, for Cairo builds that
# round differently.
ATOL = 1
MISMATCH_RATIO = 1e-5
# Manim's graphical-test configurations (manim/utils/testing/*.cfg).
LAST_FRAME = {"pixel_width": 854, "pixel_height": 480, "frame_rate": 6}
ALL_FRAMES = {"pixel_width": 427, "pixel_height": 240, "frame_rate": 6}
RUN = {"dry_run": True, "disable_caching": True, "progress_bar": "none"}
BORDER = (64, 64, 64, 255)

Construct = Callable[[Scene], None]
Frames = Literal["last", "all"]
Pixels = NDArray[np.uint8]


class _Capture(CairoRenderer):
    """Keep every frame the renderer adds. The hook is ``add_frame``, because Manim
    0.22 replaced the ``SceneFileWriter`` interface that 0.21 has."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.frames: list[Pixels] = []

    def add_frame(self, frame: Any, num_frames: int = 1) -> None:
        if not self.skip_animations:
            self.frames.append(np.array(frame, dtype=np.uint8))
        super().add_frame(frame, num_frames)


def render(construct: Construct, frames: Frames) -> Pixels:
    """Render ``construct`` and return its last frame, or every frame in one grid."""
    last = frames == "last"

    class VisualScene(Scene):
        def construct(self) -> None:
            construct(self)

    with tempconfig({**(LAST_FRAME if last else ALL_FRAMES), **RUN}):
        renderer = _Capture(skip_animations=last)
        scene = VisualScene(renderer=renderer)
        scene.render()
        # A play leaves its end state undrawn until the next play; draw it.
        renderer.update_frame(scene)
        end = np.asarray(renderer.get_frame(), dtype=np.uint8)
    return end if last else _grid([*renderer.frames, end])


def _grid(frames: list[Pixels]) -> Pixels:
    """Tile the frames row by row, each in a grey border, into one image."""
    h, w, _ = frames[0].shape
    cols = math.ceil(math.sqrt(len(frames)))
    rows = math.ceil(len(frames) / cols)
    sheet = np.full((rows * (h + 2) + 2, cols * (w + 2) + 2, 4), BORDER, np.uint8)
    for i, frame in enumerate(frames):
        r, c = divmod(i, cols)
        y, x = 2 + r * (h + 2), 2 + c * (w + 2)
        sheet[y : y + h, x : x + w] = frame
    return sheet


def _load(path: Path) -> Pixels | None:
    if not path.is_file():
        return None
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA"))


def _diff(image: Pixels, differs: NDArray[np.bool_]) -> Pixels:
    """The render dimmed to a third, with every differing pixel in red."""
    out = image // 3
    out[..., 3] = 255
    out[differs.any(axis=-1)] = (255, 0, 0, 255)
    return out


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@pytest.fixture
def visual(request: pytest.FixtureRequest, report: list[str]) -> Callable[..., None]:
    """Compare a rendered scene with its baseline; see the module docstring."""
    if request.node.get_closest_marker("render") is None:
        pytest.fail("a visual test needs @pytest.mark.render", pytrace=False)
    name = re.sub(r"[^\w.-]+", "_", request.node.name)
    module = request.node.path.stem
    baseline = HERE / "baselines" / module / f"{name}.png"
    actual = HERE / "_out" / module / f"{name}.actual.png"
    diff = actual.with_name(f"{name}.diff.png")

    def check(construct: Construct, frames: Frames = "last") -> None:
        image = render(construct, frames)
        expected = _load(baseline)
        differs = None
        if expected is not None and expected.shape == image.shape:
            differs = np.abs(image.astype(np.int16) - expected) > ATOL
            if differs.mean() < MISMATCH_RATIO:
                actual.unlink(missing_ok=True)
                diff.unlink(missing_ok=True)
                return
        if request.config.getoption("--update-baselines"):
            baseline.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(image).save(baseline)
            actual.unlink(missing_ok=True)
            diff.unlink(missing_ok=True)
            verb = "new" if expected is None else "updated"
            report.append(f"{verb} baseline: {_rel(baseline)}")
            return
        actual.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(image).save(actual)
        accept = "accept it with --update-baselines"
        if expected is None:
            pytest.fail(
                f"no baseline {_rel(baseline)}; review {_rel(actual)}, then {accept}",
                pytrace=False,
            )
        if differs is None:
            pytest.fail(
                f"{_rel(baseline)} is {expected.shape[1]}x{expected.shape[0]}, the "
                f"render {image.shape[1]}x{image.shape[0]}; review {_rel(actual)}, "
                f"then {accept}",
                pytrace=False,
            )
        Image.fromarray(_diff(image, differs)).save(diff)
        pytest.fail(
            f"{int(differs.sum())} of {differs.size} values differ from "
            f"{_rel(baseline)}; review {_rel(actual)} and {_rel(diff)}, then {accept}",
            pytrace=False,
        )

    return check
