"""Pictures of task 33's 3D histograms (`docs/acceptance/33-histograms-3d.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp

RNG = np.random.default_rng(8)


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


@pytest.mark.render
def test_hist3d_coloured_by_count(visual):
    """Matplotlib's 3D histogram example in one call: counts as shaded columns coloured
    by viridis, with a colorbar."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(0, 120, 40),
            x_length=5,
            y_length=5,
            z_length=3.5,
            frame="box",
        )
        x, y = RNG.normal(0, 1, 2000), RNG.normal(0, 1, 2000)
        h = ax.hist3d(x, y, bins=8, range=((-3, 3), (-3, 3)))
        scene.add(ax, h, ax.colorbar(h, label="count"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_histograms_in_planes(visual):
    """Four histograms laid in the planes y = 0 … 3, each coloured by position."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(
            x_range=(-4, 4, 2),
            y_range=(0, 3, 1),
            z_range=(0, 300, 100),
            x_length=5,
            y_length=5,
            z_length=3.5,
            frame="box",
        )
        parts = []
        for k in range(4):
            sample = RNG.normal(k - 1.5, 0.6 + 0.2 * k, 1000)
            parts.append(
                ax.hist(
                    sample,
                    bins=16,
                    range=(-4, 4),
                    zs=k,
                    zdir="y",
                    color_by="x",
                    colorscale="plasma",
                )
            )
        scene.add(ax, *parts)

    visual(construct, three_d=True)
