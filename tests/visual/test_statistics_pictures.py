"""Pictures of task 38's statistics (`docs/acceptance/38-statistics.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene

import manim_plots as mp


@pytest.mark.render
def test_pie(visual):
    """Four shares, one exploded, with labels outside and percentages inside."""

    def construct(scene: Scene) -> None:
        pie = mp.PieChart(
            [35, 25, 25, 15],
            explode=[0.08, 0, 0, 0],
            labels=["frogs", "hogs", "dogs", "logs"],
            autopct="%1.0f%%",
            startangle=90,
            radius=2.5,
        )
        scene.add(pie)

    visual(construct)


@pytest.mark.render
def test_boxes_and_violins(visual):
    """Three samples as box plots on the left half and violins on the right."""

    def construct(scene: Scene) -> None:
        rng = np.random.default_rng(7)
        samples = [
            rng.normal(0, 1, 300),
            rng.standard_t(3, 300),
            np.concatenate([rng.normal(-1.5, 0.5, 150), rng.normal(1.5, 0.5, 150)]),
        ]
        ax = mp.Axes(x_range=(0, 8, 1), y_range=(-5, 5, 1), x_length=10, y_length=6)
        boxes = ax.boxplot(samples, positions=[1, 2, 3])
        violins = ax.violinplot(samples, positions=[5, 6, 7], showmedians=True)
        scene.add(ax, boxes, violins)

    visual(construct)
