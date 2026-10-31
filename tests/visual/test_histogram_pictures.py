"""Pictures of task 32's histograms (`docs/acceptance/32-histograms.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene

import manim_plots as mp

RNG = np.random.default_rng(2)


def axes() -> mp.Axes:
    ax = mp.Axes(x_range=(-4, 4, 1), y_range=(0, 500, 100), x_length=9, y_length=5)
    ax.y.set_position("left")  # not through the bars at x = 0
    return ax


@pytest.mark.render
def test_spectrum_histogram(visual):
    """Three thousand normal samples, each bar coloured by its position (plasma)."""

    def construct(scene: Scene) -> None:
        ax = axes()
        h = ax.hist(
            RNG.normal(0, 1, 3000),
            bins=24,
            range=(-4, 4),
            color_by="x",
            colorscale="plasma",
        )
        scene.add(ax, h)

    visual(construct)


@pytest.mark.render
def test_histogram_by_count_with_colorbar(visual):
    """The same coloured by count, with its colorbar."""

    def construct(scene: Scene) -> None:
        ax = axes()
        h = ax.hist(RNG.normal(0, 1, 3000), bins=24, range=(-4, 4), color_by="count")
        scene.add(ax, h, ax.colorbar(h, label="count"))

    visual(construct)


@pytest.mark.render
def test_two_datasets_side_by_side_and_steps(visual):
    """Two samples side by side, a third as a step outline, with a legend."""

    def construct(scene: Scene) -> None:
        ax = axes()
        a, b, c = (
            RNG.normal(-1, 1, 1500),
            RNG.normal(1, 0.8, 1500),
            RNG.normal(0, 2, 3000),
        )
        pair = ax.hist([a, b], bins=16, range=(-4, 4), label=["left", "right"])
        wide = ax.hist(
            c, bins=16, range=(-4, 4), histtype="step", label="wide", stroke_width=3
        )
        scene.add(ax, pair, wide, ax.legend())

    visual(construct)


@pytest.mark.render
def test_stackplot(visual):
    """Three series stacked over twelve months."""

    def construct(scene: Scene) -> None:
        ax = mp.Axes(x_range=(1, 12, 1), y_range=(0, 15, 5), x_length=9, y_length=5)
        x = np.arange(1, 13)
        st = ax.stackplot(
            x, 2 + np.sin(x / 2), 3 + np.cos(x / 3), 1 + x / 4, labels=["a", "b", "c"]
        )
        scene.add(ax, st, ax.legend())

    visual(construct)
