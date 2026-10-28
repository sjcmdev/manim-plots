"""Plain Manim scenes: they check the harness, and catch a Manim version that renders
differently from the one the baselines were reviewed on."""

import numpy as np
import pytest
from manim import Axes, Circle, Create, Scene


@pytest.mark.render
def test_last_frame_of_plain_axes_with_a_graph(visual):
    def construct(scene: Scene) -> None:
        ax = Axes()
        scene.add(ax, ax.plot(np.sin))

    visual(construct)


@pytest.mark.render
def test_every_frame_of_create_circle(visual):
    def construct(scene: Scene) -> None:
        scene.play(Create(Circle()))

    visual(construct, frames="all")
