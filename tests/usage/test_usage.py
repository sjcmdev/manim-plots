"""Typical calls with the types their annotations promise (F-1002, row TY-2 of
`docs/acceptance/13-hardening.md`).

mypy checks each `assert_type` in the gate, on both Manim versions; pytest runs the
calls, so a promise the code does not keep fails here too.
"""

from __future__ import annotations

from typing import assert_type

import numpy as np

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.mobjects.leaves import TickLeaf


def square(x: float) -> float:
    return x * x


def test_typical_calls_have_their_annotated_types() -> None:
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
    curve = assert_type(ax.plot(square, label="square"), mp.FunctionPlot)
    assert isinstance(curve, mp.FunctionPlot)
    line = assert_type(ax.plot([0.0, 1.0, 2.0], [1.0, 0.0, 1.0]), mp.LinePlot)
    assert isinstance(line, mp.LinePlot)
    assert isinstance(
        assert_type(ax.line([0.0, 1.0], [0.0, 1.0]), mp.LinePlot), mp.LinePlot
    )
    dots = assert_type(ax.scatter([0.0, 1.0], [1.0, 0.0]), mp.ScatterPlot)
    assert isinstance(dots, mp.ScatterPlot)
    value = assert_type(ax.x.range.value, FloatArray)
    assert isinstance(value, np.ndarray)
    tick = assert_type(ax.x_axis.ticks.at(1.0), TickLeaf)
    assert isinstance(tick, TickLeaf)
    legend = assert_type(ax.legend(), mp.Legend)
    assert isinstance(legend, mp.Legend)
    point = assert_type(ax.c2p(1.0, 1.0), FloatArray)
    assert point.shape == (3,)
