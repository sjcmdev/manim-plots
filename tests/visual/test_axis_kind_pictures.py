"""Pictures of task 36's axis kinds (`docs/acceptance/36-axis-kinds.md`)."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest
from manim import Scene

import manim_plots as mp


@pytest.mark.render
def test_a_year_of_daily_values(visual):
    """A date axis over 2024 with concise month labels."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(y_range=(-2, 2, 1), x_length=10, y_length=4)
        start = datetime(2024, 1, 1)
        when = [start + timedelta(days=k) for k in range(366)]
        values = np.sin(np.arange(366) / 29) + 0.3 * np.sin(np.arange(366) / 3)
        line = ax.line(when, values)
        scene.add(ax, line)

    visual(construct)


@pytest.mark.render
def test_percent_and_logit(visual):
    """A share in percent against a logit axis of probabilities."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(
            x_range=(0, 1, 0.25),
            y_range=(0.001, 0.999),
            y_scale="logit",
            x_length=8,
            y_length=5,
        )
        ax.x.set_formatter(mp.PercentFormatter(xmax=1))
        ax.x.add_numbers()
        ax.y.add_numbers()
        xs = np.linspace(0.01, 0.99, 99)
        curve = ax.line(xs, 1 / (1 + np.exp(-12 * (xs - 0.5))))
        scene.add(ax, curve)

    visual(construct)


@pytest.mark.render
def test_broken_axis(visual):
    """Two clusters of values far apart, the empty stretch between them cut out."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 100, 10), x_length=8, y_length=5)
        ax.y.set_breaks([(20, 80)])
        ax.y.add_numbers()
        low = ax.scatter(np.arange(1, 10), [5, 8, 12, 9, 15, 11, 7, 14, 10])
        high = ax.scatter(np.arange(1, 10), [85, 90, 88, 95, 87, 92, 89, 91, 86])
        scene.add(ax, low, high)

    visual(construct)
