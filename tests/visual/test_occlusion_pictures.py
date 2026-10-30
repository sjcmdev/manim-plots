"""Pictures of task 30's occlusion (`docs/acceptance/30-occlusion.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp

SIZE: dict[str, Any] = {
    "x_range": (-2, 2, 1),
    "y_range": (-2, 2, 1),
    "z_range": (-2, 2, 1),
    "x_length": 5,
    "y_length": 5,
    "z_length": 3.5,
}


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


def helix(t: float) -> np.ndarray:
    return np.array([1.2 * np.cos(t), 1.2 * np.sin(t), t / 5])


@pytest.mark.render
def test_helix_through_a_surface(visual):
    """A helix passing through an opaque saddle: the turns below it are hidden where
    the saddle covers them."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**SIZE)
        surface = ax.plot_surface(
            lambda u, v: (u * u - v * v) / 4, colorscale="viridis"
        )
        curve = ax.plot_parametric_curve(helix, t_range=(-9, 9), stroke_width=6)
        scene.add(ax, surface, curve)

    visual(construct, three_d=True)


@pytest.mark.render
def test_helix_through_a_surface_without_occlusion(visual):
    """The same scene with `occlusion=False`: Manim's picture, the helix drawn whole on
    top or below by the camera's sort."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(occlusion=False, **SIZE)
        surface = ax.plot_surface(
            lambda u, v: (u * u - v * v) / 4, colorscale="viridis"
        )
        curve = ax.plot_parametric_curve(helix, t_range=(-9, 9), stroke_width=6)
        scene.add(ax, surface, curve)

    visual(construct, three_d=True)
