"""Pictures of the axes, each beside plain Manim's where Manim has the same scene.

Row VP-1 of `docs/acceptance/10-axis-decoration.md`: visual baselines for review, a
change detector and not an oracle (ADR 0002). A ``__manim`` twin draws the same scene
with Manim's `Axes` or `NumberPlane`; the library-only scenes show what Manim lacks.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import RED, Axes, LogBase, NumberPlane, Scene

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
    """Manim's `LogBase` in `axis_config`: exponent ranges, `10^k` labels, and a curve
    through `c2p`."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**LOG)
        scene.add(ax, ax.plot(lambda x: np.log10(x) / 2))

    visual(construct)


@pytest.mark.render
def test_logbase_axis__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(**LOG)
        scene.add(ax, ax.plot(lambda x: np.log10(x) / 2))

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
