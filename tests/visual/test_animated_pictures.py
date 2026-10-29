"""Every frame of the data channel and of drawing a system, for review.

The pictures of `docs/acceptance/11b-data-channel.md`'s test list: visual baselines, a
change detector and not an oracle (ADR 0002). Each baseline tiles every frame of the
play, at 6 frames per second.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import BLUE, Axes, Create, Scene

import manim_plots as mp


@pytest.mark.render
def test_a_range_animated_with_its_plot(visual):
    """`ax.animate.set_x_range((0, 10))` with `plot(np.sin)`: the ticks, the y axis and
    the curve move together on every frame.
    """

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=10, y_length=5)
        scene.add(ax, ax.plot(np.sin, color=BLUE))
        scene.play(ax.animate.set_x_range((0, 10)), run_time=1)

    visual(construct, frames="all")


@pytest.mark.render
def test_create_axes_and_plot(visual):
    """`Create(ax)` and `Create(curve)` in one play, frame by frame."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
        scene.play(Create(ax), Create(ax.plot(np.sin, color=BLUE)), run_time=1)

    visual(construct, frames="all")


@pytest.mark.render
def test_create_axes_and_plot__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
        scene.play(Create(ax), Create(ax.plot(np.sin, color=BLUE)), run_time=1)

    visual(construct, frames="all")
