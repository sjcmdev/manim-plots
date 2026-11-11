"""Pictures of the bound helpers of task 16, each beside the same scene in plain Manim
(`docs/acceptance/16-helpers-lines.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import (
    BLUE,
    BLUE_B,
    DARK_BLUE,
    GREEN,
    ORANGE,
    TEAL,
    YELLOW,
    Axes,
    Line,
    Scene,
)

import manim_plots as mp


def quarter(x):
    return x**2 / 4


@pytest.mark.render
def test_drop_lines_and_t_label(visual):
    """Lines to a point, five dashed lines to the graph, and a T label at x = 3."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes()
        graph = ax.plot(quarter, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.get_lines_to_point(ax.c2p(2, 1)),
            ax.get_vertical_lines_to_graph(
                graph, x_range=(-3, -1), num_lines=5, color=GREEN
            ),
            ax.get_T_label(3, graph, label="x_0"),
        )

    visual(construct)


@pytest.mark.render
def test_drop_lines_and_t_label__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes()
        graph = ax.plot(quarter, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.get_lines_to_point(ax.c2p(2, 1)),
            ax.get_vertical_lines_to_graph(
                graph, x_range=(-3, -1), num_lines=5, color=GREEN
            ),
            ax.get_T_label(3, graph, label="x_0"),
        )

    visual(construct)


@pytest.mark.render
def test_secant_and_tangent(visual):
    """A secant slope group at x = 1 with dx = 1.5, and an orange tangent at x = -2."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes()
        graph = ax.plot(quarter, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.get_secant_slope_group(
                1, graph, dx=1.5, dx_label="dx", dy_label="dy", secant_line_length=6
            ),
            ax.get_tangent_line(-2, graph, length=3, color=ORANGE),
        )

    visual(construct)


@pytest.mark.render
def test_secant_and_tangent__manim(visual):
    """Plain Manim, same scene; Manim has no tangent line for an x value, so the
    tangent is a `Line` along the exact derivative."""

    def construct(scene: Scene) -> None:
        ax = Axes()
        graph = ax.plot(quarter, color=BLUE)
        point = ax.c2p(-2, quarter(-2))
        step = ax.c2p(-1, quarter(-2) - 1) - ax.c2p(-2, quarter(-2))
        step = 1.5 * step / np.linalg.norm(step)
        scene.add(
            ax,
            graph,
            ax.get_secant_slope_group(
                1, graph, dx=1.5, dx_label="dx", dy_label="dy", secant_line_length=6
            ),
            Line(point - step, point + step, color=ORANGE),
        )

    visual(construct)


@pytest.mark.render
def test_derivative_and_antiderivative(visual):
    """x**2 / 4 - 1 in blue, its derivative in green, its antiderivative in yellow."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes()
        graph = ax.plot(lambda x: quarter(x) - 1, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.plot_derivative_graph(graph),
            ax.plot_antiderivative_graph(graph, color=YELLOW),
        )

    visual(construct)


@pytest.mark.render
def test_derivative_and_antiderivative__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes()
        graph = ax.plot(lambda x: quarter(x) - 1, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.plot_derivative_graph(graph),
            ax.plot_antiderivative_graph(graph, color=YELLOW),
        )

    visual(construct)


def parabola(x):
    return 0.5 * x**2 - 0.5


@pytest.mark.render
def test_area_and_riemann_rectangles(visual):
    """Manim's Riemann example: right samples on (-4, -3), a yellow signed sum on
    (-1.5, 1.5) whose middle dips below the axis, and an area under the parabola from
    2 to 3 (task 17)."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(y_range=(-2, 10, 1))
        graph = ax.plot(parabola, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.get_riemann_rectangles(
                graph,
                x_range=(-4, -3),
                dx=0.25,
                color=(TEAL, BLUE_B, DARK_BLUE),
                input_sample_type="right",
            ),
            ax.get_riemann_rectangles(
                graph, x_range=(-1.5, 1.5), dx=0.15, color=YELLOW
            ),
            ax.get_area(graph, x_range=(2, 3)),
        )

    visual(construct)


@pytest.mark.render
def test_area_and_riemann_rectangles__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        ax = Axes(y_range=[-2, 10])
        graph = ax.plot(parabola, color=BLUE)
        scene.add(
            ax,
            graph,
            ax.get_riemann_rectangles(
                graph,
                x_range=[-4, -3],
                dx=0.25,
                color=(TEAL, BLUE_B, DARK_BLUE),
                input_sample_type="right",
            ),
            ax.get_riemann_rectangles(
                graph, x_range=[-1.5, 1.5], dx=0.15, color=YELLOW
            ),
            ax.get_area(graph, x_range=(2, 3)),
        )

    visual(construct)


@pytest.mark.render
def test_fill_between_where(visual):
    """`fill_between` of sin x and 0.3 where sin x is above, with `interpolate`; no
    Manim twin: Manim has no `fill_between`."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(-7, 7, 1), y_range=(-2, 2, 1))
        xs = np.linspace(-7, 7, 141)
        ys = np.sin(xs)
        scene.add(
            ax,
            ax.plot(np.sin, color=BLUE),
            ax.fill_between(xs, ys, 0.3, where=ys > 0.3, interpolate=True, color=GREEN),
        )

    visual(construct)
