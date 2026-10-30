"""Pictures of task 24's 3D system (`docs/acceptance/24-three-d.md`) in a `ThreeDScene`
with the camera at phi = 65°, theta = -45°, each beside Manim's `ThreeDAxes` where Manim
draws the same scene."""

from __future__ import annotations

import numpy as np
import pytest
from manim import DEGREES, YELLOW, Scene, ThreeDAxes

import manim_plots as mp


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


def helix(t):
    return np.array([np.cos(t), np.sin(t), t])


@pytest.mark.render
def test_three_d_axes(visual):
    """Manim's default `ThreeDAxes` with its axis labels and a sine in the z = 0 plane."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes()
        scene.add(ax, ax.get_axis_labels(), ax.plot(np.sin))

    visual(construct, three_d=True)


@pytest.mark.render
def test_three_d_axes__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = ThreeDAxes()
        scene.add(ax, ax.get_axis_labels(), ax.plot(np.sin))

    visual(construct, three_d=True)


@pytest.mark.render
def test_three_d_helix_clipped(visual):
    """A helix of height 10 on the default axes, cut at z = ±4; Manim's runs past the
    box."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes()
        scene.add(ax, ax.plot_parametric_curve(helix, t_range=(-5, 5), color=YELLOW))

    visual(construct, three_d=True)


@pytest.mark.render
def test_three_d_helix_clipped__manim(visual):
    """Plain Manim, same helix, unclipped."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = ThreeDAxes()
        scene.add(ax, ax.plot_parametric_curve(helix, t_range=(-5, 5), color=YELLOW))

    visual(construct, three_d=True)


@pytest.mark.render
def test_three_d_log_z(visual):
    """A log z axis from 1 to 1000 with numbers, and points at the decades above a
    circle of radius 3."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            z_range=(1, 1000), z_scale="log", z_axis_config={"include_numbers": True}
        )
        t = np.linspace(0, 2 * np.pi, 12, endpoint=False)
        scene.add(
            ax,
            ax.scatter(3 * np.cos(t), 3 * np.sin(t), 10 ** (3 * t / (2 * np.pi))),
            ax.plot_parametric_curve(
                lambda s: np.array([3 * np.cos(s), 3 * np.sin(s), 10 ** (3 * s / 6.3)]),
                t_range=(0, 6.3),
            ),
        )

    visual(construct, three_d=True)
