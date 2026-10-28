"""Plain Manim, measured the way F-1001 measures the library: the reference for its
1.5x check, and a check of the harness."""

import numpy as np
import pytest
from manim import PI, UP, Axes, Rotate, Scene, Square


@pytest.mark.benchmark
def test_plain_manim_static_plots_under_an_unrelated_animation(measure_frames):
    def construct(scene: Scene) -> None:
        ax = Axes()
        graphs = [
            ax.plot(np.sin, x_range=[-7, 7, 0.007]).shift(0.5 * k * UP)
            for k in range(4)
        ]
        scene.add(ax, *graphs)
        scene.play(Rotate(Square(), PI), run_time=1)

    stats = measure_frames(construct)
    assert stats.frames == 60
