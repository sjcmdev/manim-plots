"""Defects found while rendering the release's example scenes (task 23).

RF-1: a number never rounds the tick it labels. RF-2: a line's end label can fade in
while the line is created.
Each test names the example in `examples/` that showed the defect.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from manim import DOWN, YELLOW, Create, FadeIn

import manim_plots as mp
from tests.mobjects.helpers import probe


def places(axis: Any) -> dict[float, int]:
    return {float(n.get_value()): int(n.num_decimal_places) for n in axis.numbers}


# --- RF-1 ----------------------------------------------------------------------------


def test_rf1_a_finer_locator_step_gets_the_places_it_needs():
    """`examples/01_first_plot.py`: `MaxNLocator` after a range change picks a step of
    2.5, and the numbers read -8 for -7.5 with the configured step's 0 places."""
    ax = mp.Axes(
        x_range=(-4, 4, 1), y_range=(-2, 2, 1), axis_config={"include_numbers": True}
    )
    ax.x.set_locator(mp.MaxNLocator(8))
    ax.set_x_range((-8, 8))
    shown = places(ax.x_axis)
    assert -7.5 in shown, shown
    for value, p in shown.items():
        assert round(value, p) == value, (value, p)
    # On a linear axis the numbers share one precision, as in Manim and matplotlib.
    assert len(set(shown.values())) == 1, shown


def test_rf1_a_log_axis_never_labels_a_tenth_zero():
    """`examples/08_log_scale.py`: the bottom tick at 0.1 read "0"."""
    ax = mp.Axes(
        x_range=(1, 100),
        y_range=(0.1, 1e4),
        x_scale="log",
        y_scale="log",
        axis_config={"include_numbers": True},
    )
    shown = places(ax.y_axis)
    assert 0.1 in shown, shown
    for value, p in shown.items():
        assert round(value, p) == value, (value, p)


def test_rf1_explicit_places_are_kept():
    """A precision the user set is the user's: no rounding check overrides it."""
    ax = mp.Axes(
        x_range=(-8, 8, 2.5),
        y_range=(-2, 2, 1),
        axis_config={
            "include_numbers": True,
            "decimal_number_config": {"num_decimal_places": 0},
        },
    )
    assert set(places(ax.x_axis).values()) == {0}


# --- RF-2 ----------------------------------------------------------------------------


def test_rf2_an_end_label_fades_in_while_its_line_is_created():
    """`examples/18_live_data.py`: `self.play(Create(ax), Create(line), FadeIn(label))`
    raised `ValueError: zip() argument 2 is longer than argument 1` in Manim's
    `Transform`, because the label had no glyphs on a frame where the line had no
    drawn end."""
    held: dict[str, Any] = {}

    def construct(scene: Any) -> None:
        ax = mp.Axes(
            x_range=(0, 2, 1),
            y_range=(0, 2, 1),
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        ).shift(0.3 * DOWN)
        xs = np.arange(0, 41) / 4
        ys = 1 + xs / 3 + np.sin(xs)
        line = ax.line(xs[:3], ys[:3], color=YELLOW)
        label = ax.end_label(line)
        held.update(line=line, label=label)
        scene.play(Create(ax), Create(line), FadeIn(label))
        held["glyphs"] = len(label.family_members_with_points())

    probe(construct, lambda: None, frame_rate=15)
    assert held["glyphs"] > 0
