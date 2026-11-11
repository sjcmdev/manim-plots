"""Invalid input at use, surface by surface (F-1006, `docs/scope.md`'s *at use* table).

Rows IV-1 to IV-5 of `docs/acceptance/13-hardening.md`: one test per cell of the table
that applies to a surface. Where an earlier task tests a cell, the docstring names that
test; the case here is the one it lacked or the whole cell in one place.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np
import pytest
from manim import RED

import manim_plots as mp
from manim_plots.core import ManimPlotsWarning


@contextmanager
def counted() -> Iterator[list[warnings.WarningMessage]]:
    """Record every library warning, so a test can count them."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ManimPlotsWarning)
        yield caught


def library(caught: list[warnings.WarningMessage]) -> int:
    return sum(issubclass(w.category, ManimPlotsWarning) for w in caught)


def axes(**kwargs):
    kwargs.setdefault("x_range", (-3, 3, 1))
    kwargs.setdefault("y_range", (-2, 2, 1))
    return mp.Axes(x_length=6, y_length=4, **kwargs)


# --- IV-1: path sampling --------------------------------------------------------------

BAD_PATHS: dict[str, Callable[[], tuple[Any, Callable[[Any], Any]]]] = {
    "NaN": lambda: (axes(), lambda ax: ax.plot(lambda x: np.sqrt(x))),
    "infinity": lambda: (
        axes(),
        lambda ax: ax.plot(lambda x: np.inf if abs(x) < 0.5 else x / 3),
    ),
    "outside the domain": lambda: (
        axes(y_range=(0.1, 10), y_scale="log"),
        lambda ax: ax.plot(lambda x: x),
    ),
}


@pytest.mark.parametrize("case", list(BAD_PATHS))
def test_iv1_a_bad_sample_splits_and_warns_once_per_data_change(case):
    """Earlier: `test_leaves.py::test_lf4_a_pole_splits_the_curve_into_subpaths` (the
    split); here the count, across a data change and a style change."""
    ax, make = BAD_PATHS[case]()
    with counted() as caught:
        curve = make(ax)
    assert library(caught) == 1
    assert curve.has_points()
    with counted() as caught:
        ax.x.range = (-2.5, 2.5)
        _ = curve.points
    assert library(caught) == 1
    with counted() as caught:
        curve.set_color(RED)
        _ = curve.points
    assert library(caught) == 0


def test_iv1_a_range_partly_outside_the_scale_is_normalised_without_a_warning():
    with counted() as caught:
        ax = mp.Axes(x_range=(-1, 100), x_scale="log", y_range=(-1, 5, 1))
        curve = ax.plot(np.log10)
        xs = ax.p2c(curve.get_anchors())[:, 0]
    assert library(caught) == 0
    assert (xs > 0).all()


def test_iv1_an_empty_source_draws_nothing_and_warns_once():
    with counted() as caught:
        line = axes().line(np.array([]), np.array([]))
    assert library(caught) == 1
    assert not line.has_points()


# --- IV-2: tick generation ------------------------------------------------------------


def test_iv2_a_nan_candidate_is_dropped_silently():
    with counted() as caught:
        ax = axes()
        # A locator's candidate, not a fixed entry: a NaN entry raises (scope).
        ax.x_axis.set_locator(lambda lo, hi: [1.0, np.nan, 2.0])
        values = sorted(
            round(float(ax.p2c(t.get_center())[0]), 9) for t in ax.x_axis.ticks
        )
    assert library(caught) == 0
    assert values == [1.0, 2.0]


def test_iv2_a_candidate_outside_the_domain_is_dropped_silently():
    with counted() as caught:
        ax = mp.Axes(x_range=(0.1, 100), x_scale="log", y_range=(-1, 1, 1))
        ax.x_axis.set_locator(mp.FixedLocator([-1.0, 1.0, 10.0]))
        values = sorted(
            round(float(ax.p2c(t.get_center())[0]), 9) for t in ax.x_axis.ticks
        )
    assert library(caught) == 0
    assert values == [1.0, 10.0]


def test_iv2_ticks_come_from_the_normalised_range_only():
    ax = mp.Axes(x_range=(-1, 100), x_scale="log", y_range=(-1, 1, 1))
    values = [ax.p2c(t.get_center())[0] for t in ax.x_axis.ticks]
    assert values and min(values) > 0


@pytest.mark.parametrize("step", [0, -1])
def test_iv2_a_zero_or_negative_step_raises_naming_it(step):
    """Earlier: `test_system.py::test_ax2_*` (the constructor)."""
    with pytest.raises(ValueError, match="step"):
        axes(x_range=(0, 5, step))


# --- IV-3: c2p and p2c ----------------------------------------------------------------


@pytest.mark.parametrize("bad", [(np.nan, 0.0), (0.0, np.inf)])
def test_iv3_c2p_raises_on_nan_and_infinity(bad):
    """Earlier: `test_system.py::test_ax6_*`."""
    with pytest.raises(ValueError):
        axes().c2p(*bad)


def test_iv3_c2p_raises_outside_the_domain():
    ax = mp.Axes(x_range=(0.1, 100), x_scale="log", y_range=(-1, 1, 1))
    with pytest.raises(ValueError):
        ax.c2p(-1.0, 0.0)


def test_iv3_p2c_raises_on_a_singular_frame():
    """Earlier: `test_context.py::test_wr7_*`."""
    ax = axes()
    ax.scale(0)
    with pytest.raises(ValueError, match="singular"):
        ax.p2c(np.zeros(3))


# --- IV-4: formatting -----------------------------------------------------------------


def test_iv4_a_dropped_tick_never_reaches_the_formatter():
    seen: list[float] = []

    def label(value: float) -> str:
        assert np.isfinite(value), value
        seen.append(value)
        return f"{value:g}"

    ax = axes(axis_config={"include_numbers": True})
    ax.x_axis.set_locator(lambda lo, hi: [1.0, np.nan, 2.0])
    ax.x_axis.set_formatter(label)
    _ = [n.points for n in ax.x_axis.numbers]
    assert seen and set(seen) <= {1.0, 2.0}


def test_iv4_an_empty_tick_list_formats_to_no_labels():
    for formatter in (
        mp.DecimalFormatter(),
        mp.ScientificFormatter(),
        mp.NullFormatter(),
    ):
        assert list(formatter.format_ticks(np.array([])).text) == []


# --- IV-5: point drawing --------------------------------------------------------------


def test_iv5_an_invalid_point_is_hidden_and_warns_once_per_data_change():
    with counted() as caught:
        ax = axes()
        scatter = ax.scatter([0.0, 1.0, 2.0], [0.0, np.nan, 1.0])
    assert library(caught) == 1
    assert scatter[1].get_fill_opacity() == 0
    assert scatter[0].get_fill_opacity() > 0
    with counted() as caught:
        ax.x.range = (-2, 2)
        _ = [m.points for m in scatter]
    assert library(caught) == 1


def test_iv5_a_point_outside_the_viewport_is_hidden_without_a_warning():
    with counted() as caught:
        scatter = axes().scatter([0.0, 10.0], [0.0, 0.0])
    assert library(caught) == 0
    assert scatter[1].get_fill_opacity() == 0


def test_iv5_an_empty_scatter_draws_nothing_and_warns_once():
    with counted() as caught:
        scatter = axes().scatter(np.array([]), np.array([]))
    assert library(caught) == 1
    assert len(scatter) == 0 or not any(m.has_points() for m in scatter.get_family())
