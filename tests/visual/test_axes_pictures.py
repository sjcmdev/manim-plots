"""Pictures of the axes, each beside plain Manim's where Manim has the same scene.

Row VP-1 of `docs/acceptance/10-axis-decoration.md`: visual baselines for review, a
change detector and not an oracle (ADR 0002). A ``__manim`` twin draws the same scene
with Manim's `Axes` or `NumberPlane`; the library-only scenes show what Manim lacks.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import BLUE, GREEN, RED, YELLOW, Axes, LogBase, NumberPlane, Scene

import manim_plots as mp
from manim_plots import MultipleLocator
from manim_plots.mobjects.axis import TickDirection

NUMBERS: dict[str, Any] = {"include_numbers": True}


@pytest.mark.render
def test_numbers_on_default_axes(visual):
    """`mp.Axes(axis_config={"include_numbers": True})`: Manim's numbers, plus the
    tick under each tip."""
    visual(lambda scene: scene.add(mp.Axes(axis_config=NUMBERS)))


@pytest.mark.render
def test_numbers_on_default_axes__manim(visual):
    """Plain Manim's `Axes(axis_config={"include_numbers": True})`."""
    visual(lambda scene: scene.add(Axes(axis_config=NUMBERS)))


CUSTOM: dict[str, Any] = {
    "x_range": (0, 10, 2),
    "y_range": (-1, 1, 0.25),
    "axis_config": NUMBERS,
}


@pytest.mark.render
def test_even_steps_and_quarters(visual):
    """`x_range=(0, 10, 2)`, `y_range=(-1, 1, 0.25)` with numbers and a cosine."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**CUSTOM)
        scene.add(ax, ax.plot(lambda x: np.cos(x / 2)))

    visual(construct)


@pytest.mark.render
def test_even_steps_and_quarters__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(**CUSTOM)
        scene.add(ax, ax.plot(lambda x: np.cos(x / 2)))

    visual(construct)


LOG: dict[str, Any] = {
    "x_range": (-2, 4, 1),
    "axis_config": {"scaling": LogBase(), "include_numbers": True},
}


@pytest.mark.render
def test_logbase_axis(visual):
    """Manim's `LogBase` in `axis_config`, on both axes: exponent ranges, `10^k` labels,
    and `sqrt(x)` through `c2p`, a straight line on log-log axes."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**LOG)
        scene.add(ax, ax.plot(np.sqrt))

    visual(construct)


@pytest.mark.render
def test_logbase_axis__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(**LOG)
        scene.add(ax, ax.plot(np.sqrt))

    visual(construct)


@pytest.mark.render
def test_number_plane(visual):
    """`mp.NumberPlane()` with a sine."""

    def construct(scene: Scene) -> None:
        plane = mp.NumberPlane()
        scene.add(plane, plane.plot(np.sin))

    visual(construct)


@pytest.mark.render
def test_number_plane__manim(visual):
    """Plain Manim's `NumberPlane()` with a sine."""

    def construct(scene: Scene) -> None:
        plane = NumberPlane()
        scene.add(plane, plane.plot(np.sin))

    visual(construct)


@pytest.mark.render
def test_log_scale_with_minor_ticks(visual):
    """`x_scale="log"` over data 0.1 to 1000: decades and the minor ticks between them
    (defect 9); `log10` is a straight line on a log x axis."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0.1, 1000), y_range=(0, 3, 1), x_scale="log")
        scene.add(ax, ax.plot(np.log10, x_range=(0.1, 1000)))

    visual(construct)


@pytest.mark.render
def test_ticks_out_axes_at_the_border(visual):
    """Axes at the bottom and left, ticks pointing out, a mirrored x axis on top, major
    and minor grid."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 10, 2), y_range=(0, 5, 1), axis_config=NUMBERS)
        ax.x.set_position("bottom")
        ax.y.set_position("left")
        ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))
        for axis in (ax.x, ax.y):
            axis.set_tick_style(direction=TickDirection.OUT)
            axis.set_grid("major", stroke_opacity=0.5)
        ax.x.set_grid("minor", stroke_opacity=0.2)
        top = ax.x.mirror()
        scene.add(ax, top, ax.plot(lambda x: 2.5 + 2 * np.sin(x), color=RED))

    visual(construct)


@pytest.mark.render
def test_rotated_labels_on_a_dense_axis(visual):
    """Twenty labels on six units: `overlap="rotate"` turns them, the rest stay
    hidden."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 1000, 50), x_length=6, axis_config=NUMBERS)
        ax.x.set_label_style(overlap="rotate")
        scene.add(ax)

    visual(construct)


@pytest.mark.render
def test_an_aspect_lock(visual):
    """`aspect=1`: the upper half of a circle of radius 2 is round."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), x_length=10, aspect=1.0)
        scene.add(ax, ax.plot(lambda x: np.sqrt(np.maximum(4 - x**2, 0))))

    visual(construct)


@pytest.mark.render
def test_top_axis_twiny(visual):
    """A framed plot with an independent top axis from `twiny`, taking the place of the
    top mirror: time below, distance above (task 19b)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 10, 2), y_range=(0, 5, 1), axis_config=NUMBERS)
        ax.x.set_position("bottom")
        ax.y.set_position("left")
        ax.x.mirror()
        ax.y.mirror()
        distance = ax.twiny(x_range=(0, 50, 10), x_axis_config=NUMBERS)
        scene.add(
            ax,
            ax.plot(lambda t: 2.5 + 2 * np.sin(t), color=RED),
            distance.plot(lambda d: d / 12, color=BLUE),
        )

    visual(construct)


@pytest.mark.render
def test_secondary_axis(visual):
    """A spectrum in nanometres with electronvolts on a secondary top axis, decreasing
    from left to right (task 19b)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(400, 800, 100), y_range=(0, 1, 0.25), axis_config=NUMBERS)
        ax.x.set_position("bottom")
        ax.y.set_position("left")
        energy = ax.secondary_xaxis(
            "top", functions=(lambda nm: 1239.84198 / nm, lambda ev: 1239.84198 / ev)
        )
        energy.set_locator(MultipleLocator(0.25))
        line = ax.plot(lambda nm: np.exp(-(((nm - 550) / 60) ** 2)), color=GREEN)
        scene.add(ax, line)

    visual(construct)


@pytest.mark.render
def test_four_corners(visual):
    """One curve on each pair of a bottom and a top x axis and a left and a right y
    axis, each pair one call (task 19b)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 10, 2), y_range=(0, 100, 20), axis_config=NUMBERS)
        ax.x.set_position("bottom")
        ax.y.set_position("left")
        right = ax.twinx(y_range=(0, 1, 0.2), y_axis_config=NUMBERS)
        top = ax.twiny(x_range=(0, 50, 10), x_axis_config=NUMBERS)
        corner = ax.twin(x=top, y=right)
        scene.add(
            ax,
            ax.plot(lambda x: 10 * x, color=RED),
            right.plot(lambda x: 1 - x / 10, color=BLUE),
            top.plot(lambda d: 50 + 40 * np.sin(d / 8), color=GREEN),
            corner.plot(lambda d: 0.5 + 0.4 * np.cos(d / 8), color=YELLOW),
        )

    visual(construct)
