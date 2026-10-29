"""The first pictures of the library, each beside the same scene in plain Manim.

Rows RT-1 to RT-3 of `docs/acceptance/09-leaves-context-frame.md`. RT-1 and RT-2 are
correctness oracles — a render compared with another render, F-914 and F-915. RT-3 is a
visual baseline pair for the maintainer's review: the library's picture and its
``__manim`` twin. They differ where the defaults table says the library fixes Manim: the
tick under a tip is kept (F-411), the curve is clipped to the axes (F-706), and a pole
splits the curve (F-705).
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import BLUE, RED, RIGHT, Axes, Scene, ValueTracker, VGroup

import manim_plots as mp

from .conftest import ATOL, MISMATCH_RATIO, _origins, render


def same_picture(a: np.ndarray, b: np.ndarray, tile: tuple[int, int]) -> bool:
    if a.shape != b.shape:
        return False
    differs = np.abs(a.astype(np.int16) - b) > ATOL
    h, w = tile
    return all(
        differs[y : y + h, x : x + w].mean() < MISMATCH_RATIO
        for y, x in _origins(a.shape, tile)
    )


STYLE = {
    "none": lambda ax: ax,
    "set_color": lambda ax: ax.set_color(RED),
    "set_stroke": lambda ax: ax.set_stroke(width=8),
    "set_fill": lambda ax: ax.set_fill(BLUE, opacity=1),
    "rotate": lambda ax: ax.rotate(0.3),
}


@pytest.mark.render
@pytest.mark.parametrize("style", list(STYLE))
def test_rt1_the_frame_draws_nothing(style):
    """F-914: the scene with the system and with its leaves but the frame look alike."""

    def build(with_frame: bool):
        def construct(scene: Scene) -> None:
            ax = mp.Axes()
            curve = ax.plot(np.sin)
            STYLE[style](ax)
            shown = ax if with_frame else VGroup(ax.x_axis, ax.y_axis)
            scene.add(shown, curve)

        return construct

    with_frame, tile = render(build(True), "last")
    without, _ = render(build(False), "last")
    assert same_picture(with_frame, without, tile)


@pytest.mark.render
@pytest.mark.parametrize(
    "curve_first", [True, False], ids=["curve first", "axes first"]
)
def test_rt2_a_bound_curve_does_not_freeze_in_the_background(curve_first):
    """F-915: the middle frame of a shift equals a still frame of the half shift."""

    def moving(scene: Scene) -> None:
        ax = mp.Axes()
        curve = ax.plot(np.sin)
        scene.add(*([curve, ax] if curve_first else [ax, curve]))
        scene.play(ax.animate.shift(2 * RIGHT), run_time=1)

    def still(scene: Scene) -> None:
        ax = mp.Axes()
        curve = ax.plot(np.sin)
        ax.shift(RIGHT)
        scene.add(curve, ax)

    sheet, tile = render(moving, "all")
    tiles = [
        sheet[y : y + tile[0], x : x + tile[1]] for y, x in _origins(sheet.shape, tile)
    ]
    middle = tiles[3]  # t = 0.5 at 6 fps, where smooth(0.5) = 0.5
    single, _ = render(still, "all")
    ((y, x),) = _origins(single.shape, tile)[:1]
    assert same_picture(middle, single[y : y + tile[0], x : x + tile[1]], tile)


@pytest.mark.render
def test_rt4_a_tick_dropped_during_a_play_is_not_drawn():
    """A pan of a bound range: the middle frame equals a still of the range there, so
    the ticks that left the range are not drawn at the axis end."""

    def moving(scene: Scene) -> None:
        t = ValueTracker(0.0)
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
        ax.x.range.bind(lambda: (t.get_value() - 3, t.get_value() + 3))
        scene.add(ax, ax.plot(np.sin))
        scene.play(t.animate.set_value(2.5), run_time=1)

    def still(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-1.75, 4.25, 1), y_range=(-2, 2, 1))
        scene.add(ax, ax.plot(np.sin))

    sheet, tile = render(moving, "all")
    tiles = [
        sheet[y : y + tile[0], x : x + tile[1]] for y, x in _origins(sheet.shape, tile)
    ]
    single, _ = render(still, "all")
    ((y, x),) = _origins(single.shape, tile)[:1]
    assert same_picture(tiles[3], single[y : y + tile[0], x : x + tile[1]], tile)


@pytest.mark.render
def test_rt3_sine_on_default_axes(visual):
    """`mp.Axes()` with `plot(np.sin)`: Manim's picture, with the tick under each tip
    kept and the curve clipped to the axes."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes()
        scene.add(ax, ax.plot(np.sin))

    visual(construct)


@pytest.mark.render
def test_rt3_sine_on_default_axes__manim(visual):
    """Plain Manim's `Axes()` with `plot(np.sin)`, for comparison."""

    def construct(scene: Scene) -> None:
        ax = Axes()
        scene.add(ax, ax.plot(np.sin))

    visual(construct)


@pytest.mark.render
@pytest.mark.filterwarnings("ignore::manim_plots.ManimPlotsWarning")  # the split, F-705
def test_rt3_a_pole_on_offset_axes(visual):
    """`1 / (x - 4.5)` on axes whose x range excludes 0: the curve splits at the pole
    and stays inside the axes; the y axis sits at the left edge, as in Manim."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
        scene.add(ax, ax.plot(lambda x: 1 / (x - 4.5)))

    visual(construct)


@pytest.mark.render
def test_rt3_a_pole_on_offset_axes__manim(visual):
    """Plain Manim, same scene: the samples beside the pole reach about 1e15 scene
    units, and Cairo draws nothing of the curve (defects 3 and 15a)."""

    def construct(scene: Scene) -> None:
        ax = Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
        scene.add(ax, ax.plot(lambda x: 1 / (x - 4.5)))

    visual(construct)
