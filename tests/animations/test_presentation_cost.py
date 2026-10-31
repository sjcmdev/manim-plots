"""ADR 0008 §4: a presentation is applied once per frame, not once per read.

Row LC-12 of `docs/acceptance/40-animation-package.md`. The camera reads a leaf's
points many times per frame (the 3D camera once per gradient and per colour); each
read must not re-run the whole animation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, Scene, ThreeDScene, tempconfig

import manim_plots as mp

FRAMES = {"frame_rate": 10, "pixel_height": 90, "pixel_width": 160}


def surface(scene: Any) -> tuple[Any, Any]:
    ax = mp.ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-2, 3, 1))
    scene.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)
    s = ax.plot_surface(
        lambda u, v: np.sin(u) * np.cos(v), (-3, 3), (-3, 3), resolution=8
    )
    return ax, mp.SweepSurface(s)


def region(scene: Any) -> tuple[Any, Any]:
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 6, 1))
    top = ax.plot(lambda x: 3 + np.sin(x))
    return ax, mp.GrowRegion(ax.get_area(top, x_range=(0, 4)))


def stack(scene: Any) -> tuple[Any, Any]:
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 9, 3))
    x = np.linspace(0, 4, 20)
    return ax, mp.GrowStack(ax.stackplot(x, 1 + 0 * x, 2 + np.sin(x)))


@pytest.mark.parametrize(
    "build,base", [(surface, ThreeDScene), (region, Scene), (stack, Scene)]
)
def test_lc12_presentation_runs_a_bounded_number_of_times_per_frame(build, base):
    calls: list[float] = []
    frames: list[float] = []

    class Shot(base):  # type: ignore[misc,valid-type]
        def update_to_time(self, t: float) -> None:
            super().update_to_time(t)
            frames.append(t)

        def construct(self) -> None:
            ax, animation = build(self)
            run = animation.interpolate_mobject

            def counted(alpha: float) -> None:
                calls.append(alpha)
                run(alpha)

            animation.interpolate_mobject = counted
            self.add(ax)
            self.play(animation, run_time=0.5)

    with tempconfig({"dry_run": True, "disable_caching": True, **FRAMES}):
        Shot().render()
    assert frames
    # One application per frame, plus the finish and a re-derivation or two.
    assert len(calls) <= 3 * len(frames) + 3
