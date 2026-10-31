"""Pictures of task 31's bars (`docs/acceptance/31-bars.md`), beside Manim's where Manim
draws the same scene."""

from __future__ import annotations

import numpy as np
import pytest
from manim import BarChart, Scene

import manim_plots as mp

VALUES = [3.0, -1.0, 2.0, 4.5, 1.0]
NAMES = ["one", "two", "three", "four", "five"]


@pytest.mark.render
def test_bar_chart(visual):
    """Manim's `BarChart` on the library, with its bar labels."""

    def construct(scene: Scene) -> None:
        chart = mp.BarChart(VALUES, bar_names=NAMES, y_range=(-2, 5, 1))
        scene.add(chart, chart.get_bar_labels(font_size=24))

    visual(construct)


@pytest.mark.render
def test_bar_chart__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        chart = BarChart(VALUES, bar_names=NAMES, y_range=[-2, 5, 1])
        scene.add(chart, chart.get_bar_labels(font_size=24))

    visual(construct)


@pytest.mark.render
def test_bars_coloured_by_height(visual):
    """Twelve monthly values coloured by height with viridis, and their colorbar."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 13, 1), y_range=(0, 10, 2), x_length=9, y_length=5)
        months = np.arange(1, 13)
        heights = 5 + 4 * np.sin(months / 2)
        bars = ax.bar(months, heights, c="height")
        scene.add(ax, bars, ax.colorbar(bars, label="value"))

    visual(construct)


@pytest.mark.render
def test_grouped_and_stacked(visual):
    """Three datasets grouped on categories, with a legend."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(y_range=(0, 6, 1), x_length=9, y_length=5)
        group = ax.grouped_bar(  # held: the axes keep their artists weakly
            {"2024": [3, 4, 2], "2025": [4, 5, 3], "2026": [5, 3, 4]},
            tick_labels=["north", "south", "east"],
        )
        scene.add(ax, group, ax.legend())

    visual(construct)


@pytest.mark.render
def test_horizontal_bars_with_labels(visual):
    """Categories on the y axis, stacked horizontal bars and their value labels."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 10, 2), x_length=8, y_length=4)
        low = ax.barh(["tea", "coffee", "water"], [2, 4, 3], label="morning")
        high = ax.barh(
            ["tea", "coffee", "water"], [3, 2, 4], left=[2, 4, 3], label="day"
        )
        scene.add(ax, low, high, ax.bar_label(high, label_type="center"), ax.legend())

    visual(construct)
