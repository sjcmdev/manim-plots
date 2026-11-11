"""Visual baselines: rendered frames compared with reviewed PNGs (ADR 0002).

A test marked ``render`` takes the ``visual`` fixture and hands it a ``construct``
function. The fixture renders it with Cairo and compares the result with
``baselines/<module>/<test>.png``: the last frame, or every frame tiled into one grid.
Each frame is held to Manim's tolerance on its own. On a mismatch the fixture writes the
render and a diff under ``_out/<module>/`` for review. ``--update-baselines`` writes a
missing or changed baseline instead of failing, and the maintainer reviews it in the
commit.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pytest
from manim import Scene, ThreeDScene, tempconfig
from manim.camera.three_d_camera import ThreeDCamera
from manim.renderer.cairo_renderer import CairoRenderer
from numpy.typing import NDArray
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
OUT = HERE / "_out"

# Manim's own tolerances (manim/utils/testing/_frames_testers.py), applied per frame as
# Manim does: a value may be off by one, and fewer than 0.001 % of a frame's values may
# differ by more, for Cairo builds that round differently.
ATOL = 1
MISMATCH_RATIO = 1e-5
# Manim's graphical-test configurations (manim/utils/testing/*.cfg).
LAST_FRAME = {"pixel_width": 854, "pixel_height": 480, "frame_rate": 6}
ALL_FRAMES = {"pixel_width": 427, "pixel_height": 240, "frame_rate": 6}
# TeX and text caches go under the ignored _out/, not the working directory.
RUN = {
    "dry_run": True,
    "disable_caching": True,
    "progress_bar": "none",
    "media_dir": str(OUT / "media"),
}
BORDER = (64, 64, 64, 255)

Construct = Callable[[Scene], None]
Frames = Literal["last", "all"]
Pixels = NDArray[np.uint8]

# Baseline paths claimed in this session, lower-cased: Windows would give two test ids
# that differ only in case one PNG.
_CLAIMED: dict[str, str] = {}


class _Capture(CairoRenderer):
    """Keep every frame the renderer adds, a frozen frame once per frame it lasts. The
    hook is ``add_frame``, because Manim 0.22 replaced the ``SceneFileWriter`` interface
    that 0.21 has."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.frames: list[Pixels] = []

    def add_frame(self, frame: Any, num_frames: int = 1) -> None:
        if not self.skip_animations:
            self.frames.extend([np.array(frame, dtype=np.uint8)] * num_frames)
        super().add_frame(frame, num_frames)


def render(
    construct: Construct, frames: Frames, three_d: bool = False
) -> tuple[Pixels, tuple[int, int]]:
    """Render ``construct``; return its last frame or every frame in one grid, and the
    frame size. ``three_d`` renders in a `ThreeDScene` with its camera."""
    last = frames == "last"
    size = LAST_FRAME if last else ALL_FRAMES

    base: type[Scene] = ThreeDScene if three_d else Scene

    class VisualScene(base):  # type: ignore[valid-type,misc]
        def construct(self) -> None:
            construct(self)

    with tempconfig({**size, **RUN}):
        renderer = (
            _Capture(skip_animations=last, camera_class=ThreeDCamera)
            if three_d
            else _Capture(skip_animations=last)
        )
        scene = VisualScene(renderer=renderer)
        scene.render()
        # A play leaves its end state undrawn until the next play; draw it. A frozen
        # wait leaves its background cached, and drawing over it would draw twice.
        renderer.static_image = None
        renderer.update_frame(scene)
        end = np.asarray(renderer.get_frame(), dtype=np.uint8)
    tile = (size["pixel_height"], size["pixel_width"])
    return (end if last else _grid([*renderer.frames, end])), tile


def _grid(frames: list[Pixels]) -> Pixels:
    """Tile the frames row by row, each in a grey border, into one image."""
    h, w, _ = frames[0].shape
    cols = math.ceil(math.sqrt(len(frames)))
    rows = math.ceil(len(frames) / cols)
    sheet = np.full((rows * (h + 2) + 2, cols * (w + 2) + 2, 4), BORDER, np.uint8)
    for (y, x), frame in zip(_origins(sheet.shape, (h, w)), frames, strict=False):
        sheet[y : y + h, x : x + w] = frame
    return sheet


def _origins(shape: tuple[int, ...], tile: tuple[int, int]) -> list[tuple[int, int]]:
    """Top-left corner of every tile: one for a single frame, else the grid's cells."""
    h, w = tile
    if shape[:2] == tile:
        return [(0, 0)]
    rows, cols = (shape[0] - 2) // (h + 2), (shape[1] - 2) // (w + 2)
    return [
        (2 + r * (h + 2), 2 + c * (w + 2)) for r in range(rows) for c in range(cols)
    ]


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
    owner = _CLAIMED.setdefault(str(baseline).lower(), request.node.nodeid)
    if owner != request.node.nodeid:
        pytest.fail(
            f"{_rel(baseline)} is already the baseline of {owner}", pytrace=False
        )
    actual = OUT / module / f"{name}.actual.png"
    diff = actual.with_name(f"{name}.diff.png")

    def check(
        construct: Construct, frames: Frames = "last", three_d: bool = False
    ) -> None:
        image, tile = render(construct, frames, three_d)
        expected = _load(baseline)
        differs, failing = None, 0
        if expected is not None and expected.shape == image.shape:
            differs = np.abs(image.astype(np.int16) - expected) > ATOL
            h, w = tile
            origins = _origins(image.shape, tile)
            failing = sum(
                bool(differs[y : y + h, x : x + w].mean() >= MISMATCH_RATIO)
                for y, x in origins
            )
            if not failing:
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
                f"render {image.shape[1]}x{image.shape[0]} (a different frame count?); "
                f"review {_rel(actual)}, then {accept}",
                pytrace=False,
            )
        Image.fromarray(_diff(image, differs)).save(diff)
        pytest.fail(
            f"{failing} of {len(_origins(image.shape, tile))} frames differ from "
            f"{_rel(baseline)} ({int(differs.sum())} values); review {_rel(actual)} "
            f"and {_rel(diff)}, then {accept}",
            pytrace=False,
        )

    return check
