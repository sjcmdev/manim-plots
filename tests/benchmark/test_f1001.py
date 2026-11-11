"""F-1001, the performance gate (rows PF-1 and PF-2 of
`docs/acceptance/13-hardening.md`).

Four plots of 2 000 samples on one system with `MaxNLocator` ticks and numbers on both
axes, from a warm glyph cache; the x range animated for one second at 1080p60, once
bound to a tracker and once through `ax.animate.set_x_range`; on the affine frame and on
the bilinear one after a smooth warp. Each reading's `update` p95 must be at most 4 ms.
Run alone on a quiet machine: `uv run pytest -m benchmark`.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene, ValueTracker

import manim_plots as mp

BUDGET_MS = 4.0


def warp(p):
    return p + np.array([0.05 * np.sin(p[1]), 0.05 * np.cos(p[0]), 0.0])


def decorated_axes() -> mp.Axes:
    ax = mp.Axes(
        x_range=(-7, 7, 1), y_range=(-4, 4, 1), axis_config={"include_numbers": True}
    )
    ax.x_axis.set_locator(mp.MaxNLocator())
    ax.y_axis.set_locator(mp.MaxNLocator())
    return ax


@pytest.fixture(scope="module", autouse=True)
def warm_glyph_cache():
    decorated_axes()


@pytest.mark.benchmark
@pytest.mark.parametrize("frame", ["affine", "bilinear"])
@pytest.mark.parametrize("animated", ["tracker", "animate"])
def test_f1001_four_plots_under_an_animated_range(measure_frames, frame, animated):
    def construct(scene: Scene) -> None:
        ax = decorated_axes()
        if frame == "bilinear":
            ax.apply_function(warp)
        plots = [
            ax.plot(
                lambda x, k=k: np.sin(x + k),
                x_range=(-7, 7, 14 / 1999),
                use_vectorized=True,
            )
            for k in range(4)
        ]
        scene.add(ax, *plots)
        if animated == "tracker":
            right = ValueTracker(7.0)
            ax.x.range.bind(lambda: (-7.0, right.get_value()))
            scene.play(right.animate.set_value(5.0), run_time=1)
        else:
            scene.play(ax.animate.set_x_range((-7, 5)), run_time=1)

    stats = measure_frames(construct)
    assert stats.frames == 60
    assert stats.update.p95 <= BUDGET_MS, stats
