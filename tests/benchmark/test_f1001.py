"""F-1001 end to end, without labels: the first reading of the real gate (row BM-1 of
task 09's acceptance table).

Four plots of 2 000 samples on one system whose x range follows a tracker through a
one-second play at 1080p60, on the affine frame and on the bilinear one. Recorded, not
gated; the gate itself is task 13's, with labels from a warm glyph cache.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene, ValueTracker

import manim_plots as mp


def warp(p):
    return p + np.array([0.05 * np.sin(p[1]), 0.05 * np.cos(p[0]), 0.0])


@pytest.mark.benchmark
@pytest.mark.parametrize("frame", ["affine", "bilinear"])
def test_f1001_four_plots_under_an_animated_range(measure_frames, frame):
    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-7, 7, 1), y_range=(-4, 4, 1))
        if frame == "bilinear":
            ax.apply_function(warp)
        right = ValueTracker(7.0)
        ax.x.range.bind(lambda: (-7.0, right.get_value()))
        plots = [
            ax.plot(
                lambda x, k=k: np.sin(x + k),
                x_range=(-7, 7, 14 / 1999),
                use_vectorized=True,
            )
            for k in range(4)
        ]
        scene.add(ax, *plots)
        scene.play(right.animate.set_value(5.0), run_time=1)

    stats = measure_frames(construct)
    assert stats.frames == 60
