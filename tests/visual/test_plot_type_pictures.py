"""Pictures of task 29's plot types (`docs/acceptance/29-plot-types.md`) in a
`ThreeDScene` with the camera at phi = 65°, theta = -45°."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DEGREES, Scene

import manim_plots as mp

BOX: dict[str, Any] = {
    "x_range": (0, 4, 1),
    "y_range": (0, 4, 1),
    "z_range": (0, 4, 1),
    "x_length": 5,
    "y_length": 5,
    "z_length": 3.5,
    "frame": "box",
}


def camera(scene: Scene) -> None:
    turn = scene.set_camera_orientation  # type: ignore[attr-defined]
    turn(phi=65 * DEGREES, theta=-45 * DEGREES)


@pytest.mark.render
def test_scatter_by_value(visual):
    """200 points of a spiral, coloured by height with plasma and sized by radius,
    with a colorbar."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        t = np.linspace(0, 4, 200)
        r = 0.4 + 0.35 * t
        dots = ax.scatter(
            2 + r * np.cos(3 * t),
            2 + r * np.sin(3 * t),
            t,
            c=t,
            s=0.02 + 0.02 * t,
            colorscale="plasma",
        )
        scene.add(ax, dots, ax.colorbar(dots, label="z"))

    visual(construct, three_d=True)


@pytest.mark.render
def test_bars(visual):
    """A 4 by 4 grid of shaded bars, heights from a bump."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        x, y = np.meshgrid(np.arange(4), np.arange(4))
        x, y = x.ravel(), y.ravel()
        heights = 4 * np.exp(-((x - 1.5) ** 2 + (y - 1.5) ** 2) / 3)
        scene.add(ax, ax.bar3d(x + 0.1, y + 0.1, 0 * x, 0.8, 0.8, heights))

    visual(construct, three_d=True)


@pytest.mark.render
def test_stems_and_waterfall(visual):
    """Stems of a sampled sine and a three-curve waterfall behind them."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        x = np.linspace(0, 4, 9)
        stems = ax.stem(x, 0.5 + 0 * x, 2 + np.sin(2 * x))
        curves = [1 + np.cos(x * k) for k in (1, 1.5, 2)]
        scene.add(ax, ax.waterfall(x, curves, positions=[2, 3, 4]), stems)

    visual(construct, three_d=True)


@pytest.mark.render
def test_text_and_annotation(visual):
    """A point labelled by an annotation and a title at the top of the box."""

    def construct(scene: Scene) -> None:
        camera(scene)
        ax = mp.ThreeDAxes(**BOX)
        scene.add(
            ax,
            ax.scatter([2], [2], [3]),
            ax.annotate("peak", (2, 2, 3), (3, 1, 4)),
            ax.text(2, 2, 4, "top"),
        )

    visual(construct, three_d=True)
