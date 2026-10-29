"""Pictures of the legend, the colour cycle, line styles, markers and the library's
animations, for review.

The pictures of `docs/acceptance/12-legend-style-animations.md`'s test list: visual
baselines, a change detector and not an oracle (ADR 0002). Manim has none of these, so
there are no `__manim` twins.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene, linear

import manim_plots as mp


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=10, y_length=5)


@pytest.mark.render
def test_cycle_and_legend(visual):
    """Two curves and a scatter without colour keywords take the cycle's first three
    colours; `ax.legend()` lists them in the upper right corner.
    """

    def construct(scene: Scene) -> None:
        ax = axes()
        sin = ax.plot(np.sin, label="sin x")
        cos = ax.plot(np.cos, label="cos x")
        dots = ax.scatter(
            [-2, -1, 0, 1, 2], [1.5, -1.5, 1.5, -1.5, 1.5], label="points"
        )
        scene.add(ax, sin, cos, dots, ax.legend())

    visual(construct)


@pytest.mark.render
def test_line_styles(visual):
    """`SOLID`, `DASHED`, `DOTTED` and a custom `dash=(0.4, 0.1)`, top to bottom."""

    def construct(scene: Scene) -> None:
        ax = axes()
        scene.add(ax)
        for k, style in enumerate(
            [mp.LineStyle.SOLID, mp.LineStyle.DASHED, mp.LineStyle.DOTTED]
        ):
            scene.add(
                ax.plot(lambda x, k=k: 1.5 - k + 0.3 * np.sin(2 * x), line_style=style)
            )
        scene.add(ax.plot(lambda x: -1.5 + 0.3 * np.sin(2 * x), dash=(0.4, 0.1)))

    visual(construct)


@pytest.mark.render
def test_markers(visual):
    """Every named marker, left to right: `DOT`, `CIRCLE`, `SQUARE`, `TRIANGLE`,
    `CROSS`, `STAR`, three of each.
    """

    def construct(scene: Scene) -> None:
        ax = axes()
        scene.add(ax)
        for k, marker in enumerate(mp.Marker):
            x = -2.5 + k
            scene.add(ax.scatter([x, x, x], [1, 0, -1], marker=marker))

    visual(construct)


@pytest.mark.render
def test_trace_curve_frames(visual):
    """`TraceCurve` of `tanh(8x)`, linear in time: the drawn end moves at a constant
    speed in x although the samples crowd near 0.
    """

    def construct(scene: Scene) -> None:
        ax = axes()
        curve = ax.plot(lambda x: np.tanh(8 * x))
        scene.add(ax)
        scene.play(mp.TraceCurve(curve, rate_func=linear), run_time=1)

    visual(construct, frames="all")


@pytest.mark.render
def test_morph_frames(visual):
    """`Morph` of a five-point zigzag into fifty samples of a sine, frame by frame."""

    def construct(scene: Scene) -> None:
        ax = axes()
        zigzag = ax.line([-3, -1, 0, 1, 3], [0, 1, -1, 1, 0])
        xs = np.linspace(-3, 3, 50)
        sine = ax.line(xs, np.sin(xs))
        scene.add(ax, zigzag)
        scene.play(mp.Morph(zigzag, sine), run_time=1)

    visual(construct, frames="all")
