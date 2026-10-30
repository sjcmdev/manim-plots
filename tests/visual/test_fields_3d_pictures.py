"""Pictures of task 27's fields in 3D (`docs/acceptance/27-fields-3d.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp

# Small enough for the whole box to stay in the frame at the test camera.
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


def swirl(p: np.ndarray) -> np.ndarray:
    return np.array([-p[1], p[0], 0.5])


@pytest.mark.render
def test_field_flat_arrows(visual):
    """A rising swirl, flat arrows facing the camera, coloured by length."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        scene.add(ax, ax.get_vector_field(swirl))

    visual(construct, three_d=True)


@pytest.mark.render
def test_field_three_d_arrows(visual):
    """The same swirl on a coarser grid with Manim's `Arrow3D`."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        scene.add(
            ax,
            ax.get_vector_field(
                swirl,
                arrow="3d",
                x_range=(-2, 2, 2),
                y_range=(-2, 2, 2),
                z_range=(-2, 2, 2),
            ),
        )

    visual(construct, three_d=True)


@pytest.mark.render
def test_stream_lines_3d(visual):
    """Stream lines of the swirl from one layer of start points."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        scene.add(
            ax,
            ax.get_stream_lines(
                swirl, three_dimensions=False, z_range=(-2, -2, 1), stroke_width=2
            ),
        )

    visual(construct, three_d=True)


@pytest.mark.render
def test_coulomb_field_in_spherical_coordinates(visual):
    """`(1 / r², 0, 0)` in spherical coordinates: arrows pointing out, shorter far
    away."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        field = ax.get_vector_field(
            lambda p: np.array([1 / max(p[0], 0.5) ** 2, 0.0, 0.0]),
            coords="spherical",
            length_func=lambda norm: 0.6 * np.tanh(norm),
        )
        scene.add(ax, field)

    visual(construct, three_d=True)
