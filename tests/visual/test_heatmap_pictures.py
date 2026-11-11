"""Pictures of task 37's heatmaps (`docs/acceptance/37-heatmaps.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene

import manim_plots as mp


def axes() -> mp.Axes:
    return mp.Axes(x_range=(0, 6, 1), y_range=(0, 6, 1), x_length=6, y_length=6)


@pytest.mark.render
def test_annotated_heatmap(visual):
    """A 6 by 6 table of values with each cell labelled, dark text on light cells."""

    def construct(scene: Scene) -> None:
        ax = axes()
        z = np.add.outer(np.arange(6), np.arange(6)) % 7 / 6
        img = ax.imshow(z, extent=(0, 6, 0, 6))
        scene.add(ax, img, img.label_cells(fmt="{:.1f}", font_size=18))

    visual(construct)


@pytest.mark.render
def test_hist2d_with_colorbar(visual):
    """Two thousand normal points binned 12 by 12, with a colorbar."""

    def construct(scene: Scene) -> None:
        ax = axes()
        rng = np.random.default_rng(1)
        x, y = rng.normal(3, 1, 2000), rng.normal(3, 0.7, 2000)
        h = ax.hist2d(x, y, bins=12, range=((0, 6), (0, 6)), colorscale="magma")
        scene.add(ax, h, ax.colorbar(h, label="count"))

    visual(construct)


@pytest.mark.render
def test_hexbin(visual):
    """The same points in hexagons."""

    def construct(scene: Scene) -> None:
        ax = axes()
        rng = np.random.default_rng(1)
        x, y = rng.normal(3, 1, 2000), rng.normal(3, 0.7, 2000)
        scene.add(ax, ax.hexbin(x, y, gridsize=12, extent=(0, 6, 0, 6)))

    visual(construct)


@pytest.mark.render
def test_contourf_and_contour(visual):
    """Filled bands of two Gaussian bumps with their level lines on top."""

    def construct(scene: Scene) -> None:
        ax = axes()
        xs, ys = np.meshgrid(np.linspace(0, 6, 61), np.linspace(0, 6, 61))
        zs = np.exp(-((xs - 2) ** 2 + (ys - 2) ** 2)) + np.exp(
            -((xs - 4) ** 2 + (ys - 4) ** 2) / 2
        )
        scene.add(
            ax,
            ax.contourf(xs, ys, zs, levels=8, colorscale="coolwarm"),
            ax.contour(xs, ys, zs, levels=8, color="#ffffff", stroke_width=1),
        )

    visual(construct)
