"""Plain Manim, measured the way F-1001 measures the library: the reference for its
1.5x check (row PF-3 of `docs/acceptance/13-hardening.md`), and a check of the
harness."""

from __future__ import annotations

import numpy as np
import pytest
from manim import PI, UP, Axes, Rotate, Scene, Square

import manim_plots as mp

RATIO = 1.5


def static_plots(make_axes):
    def construct(scene: Scene) -> None:
        ax = make_axes()
        graphs = [
            ax.plot(np.sin, x_range=[-7, 7, 0.007]).shift(0.5 * k * UP)
            for k in range(4)
        ]
        scene.add(ax, *graphs)
        scene.play(Rotate(Square(), PI), run_time=1)

    return construct


@pytest.mark.benchmark
def test_plain_manim_static_plots_under_an_unrelated_animation(measure_frames):
    stats = measure_frames(static_plots(Axes))
    assert stats.frames == 60


@pytest.mark.benchmark
def test_pf3_static_library_plots_cost_at_most_one_and_a_half_plain_manims(
    measure_frames,
):
    plain = measure_frames(static_plots(Axes))
    ours = measure_frames(static_plots(mp.Axes))
    assert ours.frame.p95 <= RATIO * plain.frame.p95, (ours.frame, plain.frame)
