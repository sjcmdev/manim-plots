"""Pictures of task 39's voxels and isosurfaces (`docs/acceptance/39-volumes.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp


def camera(scene: Scene) -> None:
    scene.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)  # type: ignore[attr-defined]


@pytest.mark.render
def test_voxel_sphere_coloured_by_height(visual):
    """A ball of voxels, each coloured by the height of its centre."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(0, 8, 2),
            y_range=(0, 8, 2),
            z_range=(0, 8, 2),
            x_length=5,
            y_length=5,
            z_length=3.5,
            frame="box",
        )
        i, j, k = np.indices((8, 8, 8)) + 0.5
        filled = (i - 4) ** 2 + (j - 4) ** 2 + (k - 4) ** 2 < 12
        scene.add(ax, ax.voxels(filled, c=k, colorscale="plasma"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_isosurface_of_a_torus(visual):
    """The level set of a torus function, shaded and coloured along z."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-1, 1, 0.5))
        surface = ax.plot_isosurface(
            lambda x, y, z: (np.sqrt(x**2 + y**2) - 1.2) ** 2 + z**2,
            0.16,
            resolution=28,
            colorscale="viridis",
        )
        scene.add(ax, surface)

    visual(construct, three_d=True)
