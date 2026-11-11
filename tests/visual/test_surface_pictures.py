"""Pictures of task 25's surfaces and colour (`docs/acceptance/25-surfaces.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°, beside Manim's where Manim
draws the same scene."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import (
    BLUE,
    DEGREES,
    GREEN,
    ORANGE,
    RED,
    YELLOW,
    Scene,
    ThreeDAxes,
)

import manim_plots as mp

SCALE = [BLUE, GREEN, YELLOW, ORANGE, RED]
# Small enough for the whole box to stay in the frame at the test camera.
SIZE: dict[str, Any] = {"x_length": 5, "y_length": 5, "z_length": 3.5}


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


def saddle(u, v):
    return 2 * np.sin(u) * np.cos(v)


@pytest.mark.render
def test_surface_saddle(visual):
    """Manim's `PlotSurfaceExample` on the library: colour by height, each face by its
    centre."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-5, 5, 1))
        surface = ax.plot_surface(
            saddle, (-3, 3), (-3, 3), resolution=16, colorscale=SCALE
        )
        scene.add(ax, surface)

    visual(construct, three_d=True)


@pytest.mark.render
def test_surface_saddle__manim(visual):
    """Plain Manim, same scene: each face coloured by its far corner."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-5, 5, 1))
        surface = ax.plot_surface(
            saddle,  # type: ignore[arg-type]  # Manim types it Callable[[float], float]
            (-3, 3),
            (-3, 3),
            resolution=16,
            colorscale=SCALE,
        )
        scene.add(ax, surface)

    visual(construct, three_d=True)


@pytest.mark.render
def test_surface_viridis_colorbar(visual):
    """A Gaussian bump coloured by viridis in a box frame, with its colorbar fixed at
    the right of the frame."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-2, 2, 1),
            y_range=(-2, 2, 1),
            z_range=(0, 1, 0.25),
            frame="box",
            **SIZE,
        )
        surface = ax.plot_surface(
            lambda u, v: np.exp(-(u**2 + v**2)), resolution=24, colorscale="viridis"
        )
        scene.add(ax, surface, ax.colorbar(surface, label="z"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_surface_clipped(visual):
    """A steep sine cut at z = ±2 on the box; Manim would draw it past the box."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-2, 2, 1), **SIZE
        )
        surface = ax.plot_surface(
            lambda u, v: 3 * np.sin(u + v), resolution=24, colorscale=SCALE
        )
        scene.add(ax, surface)

    visual(construct, three_d=True)


@pytest.mark.render
def test_trisurf(visual):
    """`plot_trisurf` of 60 scattered points on a cone, by Delaunay, coloured by
    height."""

    def construct(scene: Scene) -> None:
        camera(scene)
        rng = np.random.default_rng(7)
        x, y = rng.uniform(-2, 2, 60), rng.uniform(-2, 2, 60)
        ax = mp.ThreeDAxes(
            x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(0, 3, 1), **SIZE
        )
        scene.add(ax, ax.plot_trisurf(x, y, np.hypot(x, y), colorscale="plasma"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_wireframe(visual):
    """A wireframe of `sin(r) / r`, 10 by 10 lines in the cycle's first colour."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-6, 6, 2), y_range=(-6, 6, 2), z_range=(-1, 1, 0.5), **SIZE
        )
        scene.add(ax, ax.plot_wireframe(lambda u, v: np.sinc(np.hypot(u, v) / np.pi)))

    visual(construct, three_d=True)


@pytest.mark.render
def test_surface_of_revolution(visual):
    """`1 + sin(t) / 2` turned about the z axis: a vase, checkerboard."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(0, 6, 1), **SIZE
        )
        scene.add(
            ax, ax.plot_surface_of_revolution(lambda t: 1 + np.sin(t) / 2, (0, 6))
        )

    visual(construct, three_d=True)


@pytest.mark.render
def test_contours_on_the_pane(visual):
    """A paraboloid in a box frame with its level lines on the surface and projected
    on the floor pane, coloured by the surface's coolwarm."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-2, 2, 1),
            y_range=(-2, 2, 1),
            z_range=(0, 8, 2),
            frame="box",
            **SIZE,
        )
        surface = ax.plot_surface(
            lambda u, v: u**2 + v**2, colorscale="coolwarm", fill_opacity=0.7
        )
        scene.add(ax, surface, surface.contour(), surface.contour(offset="pane"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_colorbar_2d(visual):
    """A 2D rotation field coloured by magnitude with its colorbar on the right."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=8, y_length=5)
        field = ax.get_vector_field(lambda p: np.array([-p[1], p[0], 0.0]) / 2)
        scene.add(ax, field, ax.colorbar(field, label="|v|"))

    visual(construct)
