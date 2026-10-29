"""Pictures of the artists, for review (ADR 0002), with a ``__manim`` twin where Manim
draws the same scene."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import (
    BLUE,
    DOWN,
    LEFT,
    RED,
    RIGHT,
    UP,
    YELLOW,
    Axes,
    Dot,
    Line,
    Scene,
    Star,
    VGroup,
)

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


@pytest.mark.render
def test_clip_per_axis(visual):
    """`clip=(True, False)`: a blue curve over x in (-5, 5) cut at the axes' sides but
    not at their top and bottom, beside a red one clipped on both axes (F-706,
    ADR 0004)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        free_y = ax.plot(
            lambda x: 2.3 * np.sin(x), x_range=(-5, 5), clip=(True, False), color=BLUE
        )
        both = ax.plot(lambda x: 2.3 * np.cos(x), x_range=(-5, 5), color=RED)
        scene.add(ax, free_y, both)

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


ERR_X = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
ERR_Y = np.array([0.5, 1.2, 0.8, -0.4, 0.3])
YERR = np.array([[0.2, 0.3, 0.2, 0.4, 0.3], [0.4, 0.3, 0.5, 0.2, 0.3]])
XERR = 0.25


@pytest.mark.render
def test_errorbars_in_x_and_y(visual):
    """`ax.errorbar` with asymmetric y errors and symmetric x errors, caps 0.1 long,
    in yellow (task 18)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(**RANGES)
        scene.add(ax, ax.errorbar(ERR_X, ERR_Y, yerr=YERR, xerr=XERR, color=YELLOW))

    visual(construct)


@pytest.mark.render
def test_errorbars_in_x_and_y__manim(visual):
    """Plain Manim, the same bars built by hand from `Line`s and `Dot`s."""

    def construct(scene: Scene) -> None:
        ax = Axes(**RANGES)
        parts = []
        for i, (x, y) in enumerate(zip(ERR_X, ERR_Y, strict=True)):
            lo, hi = YERR[0, i], YERR[1, i]
            parts.append(Line(ax.c2p(x, y - lo), ax.c2p(x, y + hi), stroke_width=2))
            parts.append(Line(ax.c2p(x - XERR, y), ax.c2p(x + XERR, y), stroke_width=2))
            for end in (ax.c2p(x, y - lo), ax.c2p(x, y + hi)):
                parts.append(
                    Line(end + 0.05 * LEFT, end + 0.05 * RIGHT, stroke_width=2)
                )
            for end in (ax.c2p(x - XERR, y), ax.c2p(x + XERR, y)):
                parts.append(Line(end + 0.05 * DOWN, end + 0.05 * UP, stroke_width=2))
            parts.append(Dot(ax.c2p(x, y)))
        scene.add(ax, VGroup(*parts).set_color(YELLOW))

    visual(construct)


@pytest.mark.render
def test_errorbars_on_a_log_axis(visual):
    """Error bars on a log y axis: the second point's lower end leaves the domain, so
    its bar runs to the bottom and has no cap there (EB-3)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 5, 1), y_range=(1, 100, 1), y_scale="log")
        xs = np.array([1.0, 2.0, 3.0, 4.0])
        ys = np.array([5.0, 2.0, 30.0, 60.0])
        scene.add(ax, ax.errorbar(xs, ys, yerr=[2.0, 5.0, 10.0, 30.0], color=BLUE))

    visual(construct)
