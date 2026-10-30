"""Pictures of task 28's slices and projections (`docs/acceptance/28-slices.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp

BOX: dict[str, Any] = {
    "x_range": (-2, 2, 1),
    "y_range": (-2, 2, 1),
    "z_range": (-2, 2, 1),
    "x_length": 5,
    "y_length": 5,
    "z_length": 3.5,
    "frame": "box",
}


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


@pytest.mark.render
def test_slices_of_a_surface(visual):
    """A translucent saddle with its slices at x = 1 and y = -1 drawn on it."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        surface = ax.plot_surface(
            lambda u, v: u * v / 2, colorscale="viridis", fill_opacity=0.5
        )
        scene.add(ax, surface, surface.slice(x=1), surface.slice(y=-1))

    visual(construct, three_d=True)


@pytest.mark.render
def test_shadows_on_the_panes(visual):
    """A helix and its three shadows on the far panes."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        helix = ax.plot_parametric_curve(
            lambda t: np.array([np.cos(t), np.sin(t), t / 4]), t_range=(-7, 7)
        )
        scene.add(ax, helix, *(ax.shadow(helix, zdir=d) for d in "xyz"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_zdir_curves_on_the_walls(visual):
    """matplotlib's `zdir`: a sine laid on the wall y = 2 and a cosine on x = -2."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        scene.add(
            ax,
            ax.plot(np.sin, x_range=(-2, 2), zs=2, zdir="y"),
            ax.plot(np.cos, x_range=(-2, 2), zs=-2, zdir="x"),
        )

    visual(construct, three_d=True)
