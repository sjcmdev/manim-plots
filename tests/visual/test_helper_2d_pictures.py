"""Pictures of task 35's 2D helpers (`docs/acceptance/35-helpers-2d.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import Scene

import manim_plots as mp


def axes() -> mp.Axes:
    return mp.Axes(x_range=(0, 10, 1), y_range=(-2, 2, 1), x_length=9, y_length=5)


@pytest.mark.render
def test_annotation_spans_and_fill_betweenx(visual):
    """A damped wave, a shaded interval, a band, and the peak annotated."""

    def construct(scene: Scene) -> None:
        ax = axes()
        wave = ax.plot(lambda x: 1.8 * np.exp(-x / 5) * np.sin(2 * x))
        span = ax.axvspan(3, 5)
        band = ax.axhspan(-0.5, 0.5)
        side = ax.fill_betweenx(np.linspace(-2, 2, 41), 9.5, 10)
        note = ax.annotate("first peak", (0.73, 1.55), (3, 1.7))
        scene.add(ax, span, band, side, wave, note)

    visual(construct)


@pytest.mark.render
def test_crosshair_and_end_label(visual):
    """A crosshair with its readout on a curve, and the curve's end labelled."""

    def construct(scene: Scene) -> None:
        ax = axes()
        wave = ax.plot(lambda x: np.sin(x), x_range=(0, 8))
        scene.add(ax, wave, ax.crosshair(2.5, graph=wave), ax.end_label(wave))

    visual(construct)


@pytest.mark.render
def test_inset_zoom(visual):
    """A noisy signal with an inset zooming one stretch, joined by two connectors."""

    def construct(scene: Scene) -> None:
        ax = axes()
        xs = np.linspace(0, 10, 400)
        ys = np.sin(xs) + 0.15 * np.sin(23 * xs)
        line = ax.line(xs, ys)
        ins = ax.inset(
            (0.55, 0.05, 0.4, 0.35), (1, 2, 0.5), (0.6, 1.3, 0.25), mirror=[line]
        )
        scene.add(ax, line, ins, *ins.mirrored)

    visual(construct)
