"""Pictures of the bound helpers of task 16, each beside the same scene in plain Manim
(`docs/acceptance/16-helpers-lines.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import BLUE, GREEN, ORANGE, YELLOW, Axes, Line, Scene

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
