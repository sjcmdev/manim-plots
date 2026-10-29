"""Pictures of the artists, for review (ADR 0002), with a ``__manim`` twin where Manim
draws the same scene."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import BLUE, RED, YELLOW, Axes, Scene, Star

import manim_plots as mp

RANGES: dict[str, Any] = {"x_range": (-3, 3, 1), "y_range": (-2, 2, 1)}


@pytest.mark.render
@pytest.mark.filterwarnings("ignore::manim_plots.ManimPlotsWarning")  # the split, F-705
def test_a_line_with_a_gap(visual):
    """`ax.line` through data with a `NaN`: the line breaks there (F-705)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        xs = np.linspace(-3, 3, 13)
        ys = np.sin(xs)
        ys[6] = np.nan
        scene.add(ax, ax.line(xs, ys, color=BLUE))

    visual(construct)


@pytest.mark.render
def test_a_scatter_with_stars(visual):
    """`ax.scatter` with a custom marker (F-805); the point outside the axes is not
    drawn."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        marker = Star(outer_radius=0.12, color=YELLOW, fill_opacity=1)
        scene.add(
            ax,
            ax.scatter([-2, -1, 0, 1, 2, 5], [1, -1, 0.5, 1.5, -0.5, 0], marker=marker),
        )

    visual(construct)


@pytest.mark.render
def test_a_clipped_spiral(visual):
    """`plot_parametric_curve` of a spiral that leaves the axes: clipped at their sides
    (F-706)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        spiral = ax.plot_parametric_curve(
            lambda t: (0.25 * t * np.cos(t), 0.25 * t * np.sin(t)),
            t_range=(0, 14),
            color=RED,
        )
        scene.add(ax, spiral)

    visual(construct)


LINE_GRAPH = ([-2, -1, 0, 1, 2], [0, 1, 0.5, -1, 0])


@pytest.mark.render
def test_plot_line_graph(visual):
    """`plot_line_graph`: a yellow polyline with vertex dots."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        scene.add(ax, ax.plot_line_graph(*LINE_GRAPH))

    visual(construct)


@pytest.mark.render
def test_plot_line_graph__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(**RANGES)
        scene.add(ax, ax.plot_line_graph(*LINE_GRAPH))

    visual(construct)
