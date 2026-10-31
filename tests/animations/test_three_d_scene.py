"""Row SC-7 of `docs/acceptance/43-spatial-animations.md`: animations in a ThreeDScene.

A 3D system reads the scene's camera; a later animation copies the artist (Manim's
starting mobject) and must not try to copy the camera with it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from manim import ThreeDScene, tempconfig

import manim_plots as mp


def test_sc7_two_plays_on_a_surface_in_a_three_d_scene():
    held: dict[str, Any] = {}

    class Shot(ThreeDScene):
        def construct(self) -> None:
            ax = mp.ThreeDAxes(
                x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-2, 3, 1)
            )
            surface = ax.plot_surface(
                lambda u, v: np.sin(u) * np.cos(v), (-3, 3), (-3, 3), resolution=4
            )
            held["ax"], held["surface"] = ax, surface
            self.add(ax)
            self.play(mp.SweepSurface(surface), run_time=0.2)
            self.play(mp.SweepSurface(surface, reverse=True), run_time=0.2)

    with tempconfig(
        {"dry_run": True, "frame_rate": 10, "pixel_height": 90, "pixel_width": 160}
    ):
        Shot().render()
    # The play finished: the reverse sweep removed the surface, data intact.
    assert len(held["surface"].faces) > 0
