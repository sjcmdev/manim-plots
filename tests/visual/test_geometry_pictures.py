"""Pictures of task 26's geometry and coordinates (`docs/acceptance/26-geometry.md`) in
a `ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, PI, Scene

import manim_plots as mp

# Small enough for the whole box to stay in the frame at the test camera.
SIZE: dict[str, Any] = {"x_length": 5, "y_length": 5, "z_length": 3.5}
BOX: dict[str, Any] = {
    "x_range": (-2, 2, 1),
    "y_range": (-2, 2, 1),
    "z_range": (-2, 2, 1),
    "frame": "box",
    **SIZE,
}


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


@pytest.mark.render
def test_plane_line_and_point(visual):
    """An oblique plane cut to the box, a line through it and their crossing."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        plane = ax.plane((0, 0, 0), (1, 1, 2))
        line = ax.axline((-1, -1, -2), direction=(1, 0.5, 2))
        scene.add(ax, plane, line, ax.intersection(plane, line))

    visual(construct, three_d=True)


@pytest.mark.render
def test_two_planes_meet(visual):
    """A wall at x = 0.5 and an oblique plane, with the line where they meet."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        wall, slope = ax.plane(x=0.5), ax.plane((0, 0, 0), (0, -1, 1))
        scene.add(ax, wall, slope, ax.intersection(wall, slope))

    visual(construct, three_d=True)


@pytest.mark.render
def test_plane_cuts_a_surface(visual):
    """A saddle cut by the plane x = 1: the cut is a line on the surface."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        surface = ax.plot_surface(lambda u, v: u * v / 2, colorscale="viridis")
        wall = ax.plane(x=1)
        cut = ax.intersection(wall, surface, stroke_width=6)
        scene.add(ax, surface, wall, cut)

    visual(construct, three_d=True)


@pytest.mark.render
def test_drop_lines_in_a_box(visual):
    """A point and its drop lines to the floor and the far walls."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        point = ax.scatter([1], [0.5], [1.5])
        scene.add(ax, point, ax.get_lines_to_point(ax.c2p(1, 0.5, 1.5)))

    visual(construct, three_d=True)


@pytest.mark.render
def test_spherical_surface(visual):
    """`r = 1.5 + 0.4 cos 3φ sin² θ`, checkerboard: a sphere with three lobes."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            **SIZE, x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-2, 2, 1)
        )
        scene.add(
            ax,
            ax.plot_surface(
                lambda th, ph: 1.5 + 0.4 * np.cos(3 * ph) * np.sin(th) ** 2,
                coords="spherical",
            ),
        )

    visual(construct, three_d=True)


@pytest.mark.render
def test_cylindrical_disc(visual):
    """`z = cos(rho)` on the disc of radius 2π, coloured by height."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-2 * PI, 2 * PI, PI),
            y_range=(-2 * PI, 2 * PI, PI),
            z_range=(-1, 1, 0.5),
            **SIZE,
        )
        scene.add(
            ax,
            ax.plot_surface(
                lambda rho, ph: np.cos(rho), coords="cylindrical", colorscale="coolwarm"
            ),
        )

    visual(construct, three_d=True)
