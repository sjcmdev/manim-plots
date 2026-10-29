"""The four artists and `plot`'s calling convention (F-701-F-707, F-805, F-1004).

Rows AR-1 to AR-9 and AR-12 of `docs/acceptance/11a-artists.md`. Oracles: the data and
the functions themselves mapped through `c2p`, and Manim's own `plot_line_graph` on
Manim's `Axes`.
"""

from __future__ import annotations

import math
import typing

import numpy as np
import pytest
from manim import DEFAULT_DOT_RADIUS, Axes, Dot, Square, ValueTracker, VDict, tempconfig

import manim_plots as mp
from manim_plots import FunctionPlot, LinePlot, ParametricPlot, ScatterPlot
from manim_plots.core import ManimPlotsWarning
from manim_plots.mobjects.leaves import Leaf

from .helpers import RUN


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)


def anchors_xy(ax, artist) -> np.ndarray:
    """The data coordinates of an artist's anchors, one row per anchor."""
    return np.asarray(ax.p2c(artist.get_anchors()))


def path_anchors(mob) -> np.ndarray:
    """A single path's anchors, each once (Manim's `get_anchors` repeats the inner
    ones)."""
    points = np.asarray(mob.points)
    return np.vstack([points[::4], points[-1:]])


def test_ar1_the_artists_are_star_exported():
    for name in ("FunctionPlot", "LinePlot", "ScatterPlot", "ParametricPlot"):
        assert name in mp.__all__


def test_ar2_plot_dispatches_on_its_first_argument():
    ax = axes()
    assert isinstance(ax.plot(np.sin), FunctionPlot)
    assert isinstance(ax.plot([0, 1, 2], [0, 1, 0]), LinePlot)
    assert isinstance(ax.plot([(0, 0), (1, 1)]), LinePlot)
    assert len(typing.get_overloads(mp.CartesianAxes.plot)) >= 2


def test_ar3_function_parameters_come_from_the_signature():
    ax = axes()
    curve = ax.plot(lambda x, a=1.0, b=0.0: a * np.sin(x) + b, a=1.5)
    assert set(curve.parameters) == {"a", "b"}
    assert curve.parameters["a"].value == 1.5
    assert curve.parameters["b"].value == 0.0
    xy = anchors_xy(ax, curve)
    np.testing.assert_allclose(xy[:, 1], 1.5 * np.sin(xy[:, 0]), atol=1e-9)
    curve.parameters["b"].value = 0.5
    xy = anchors_xy(ax, curve)
    # Anchors where the viewport cuts the curve lie on its spline, not on f.
    inside = np.abs(1.5 * np.sin(xy[:, 0]) + 0.5) < 2 - 1e-3
    np.testing.assert_allclose(
        xy[inside, 1], 1.5 * np.sin(xy[inside, 0]) + 0.5, atol=1e-9
    )


def test_ar3_other_keywords_are_style():
    curve = axes().plot(lambda x, a=1.0: a * x, a=0.5, stroke_width=9, color="#00FF00")
    assert curve.get_stroke_width() == 9
    assert curve.parameters["a"].value == 0.5


@pytest.mark.parametrize("name", ["color", "stroke_width", "fill_opacity"])
def test_ar3_a_parameter_named_like_a_style_keyword_raises(name):
    namespace: dict[str, object] = {}
    exec(f"def f(x, {name}=1.0):\n    return x", namespace)
    with pytest.raises(ValueError, match=name):
        axes().plot(namespace["f"])


def test_ar3_a_tracker_binds_a_parameter():
    tracker = ValueTracker(2.0)
    ax = axes()
    curve = ax.plot(lambda x, a=1.0: a * x / 4, a=tracker)
    assert curve.parameters["a"].tracker is tracker


def test_ar4_use_smoothing_false_draws_straight_segments():
    curve = axes().plot(np.sin, use_smoothing=False)
    curves = curve.points.reshape(-1, 4, 3)
    thirds = curves[:, 0] + (curves[:, 3] - curves[:, 0]) / 3
    np.testing.assert_allclose(curves[:, 1], thirds, atol=1e-12)


def test_ar4_discontinuities_and_dt_are_manims():
    ax = axes()
    curve = ax.plot(lambda x: math.floor(x), discontinuities=[0.0, 1.0], dt=1e-3)
    assert len(curve.get_subpaths()) >= 3


def test_ar5_a_line_goes_through_the_data():
    ax = axes()
    xs, ys = np.array([-2.0, -1.0, 0.5, 2.0]), np.array([1.0, -1.0, 0.0, 1.5])
    line = ax.line(xs, ys)
    np.testing.assert_allclose(
        path_anchors(line), np.asarray(ax.c2p(xs, ys)).T, atol=1e-9
    )
    same = ax.line(np.c_[xs, ys])
    np.testing.assert_allclose(same.points, line.points)


def test_ar5_nan_splits_and_the_data_stays():
    ax = axes()
    xs = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    ys = np.array([0.0, 1.0, np.nan, 1.0, 0.0])
    keep = ys.copy()
    with pytest.warns(ManimPlotsWarning, match="split"):
        line = ax.line(xs, ys)
    assert len(line.get_subpaths()) == 2
    np.testing.assert_array_equal(ys, keep)


def test_ar5_a_range_change_filters_and_does_not_resample():
    ax = axes()
    line = ax.line(np.linspace(-3, 3, 7), np.zeros(7))
    ax.x.range = (-1, 1)
    xs = ax.p2c(line.get_anchors())[0]
    assert set(np.round(xs, 9)) <= {-1.0, 0.0, 1.0}


def test_ar6_one_marker_per_point_at_c2p():
    ax = axes()
    xs, ys = np.array([-1.0, 0.0, 1.0]), np.array([1.0, 0.5, -1.0])
    scatter = ax.scatter(xs, ys)
    assert len(scatter) == 3
    for marker, x, y in zip(scatter, xs, ys, strict=True):
        np.testing.assert_allclose(marker.get_center(), ax.c2p(x, y), atol=1e-9)
        assert math.isclose(marker.width, 2 * DEFAULT_DOT_RADIUS, rel_tol=1e-6)
        assert marker.get_fill_color() == Dot().get_fill_color()


def test_ar6_a_custom_marker_becomes_library_leaves():
    ax = axes()
    scatter = ax.scatter([0.0, 1.0], [0.0, 1.0], marker=Square(side_length=0.2))
    for marker, point in zip(scatter, ax.c2p([0.0, 1.0], [0.0, 1.0]).T, strict=True):
        np.testing.assert_allclose(marker.get_center(), point, atol=1e-9)
        assert math.isclose(marker.width, 0.2, rel_tol=1e-6)
        assert all(isinstance(m, Leaf) for m in marker.get_family() if m.has_points())


def test_ar6_a_point_outside_is_not_drawn_and_keeps_its_place():
    ax = axes()
    scatter = ax.scatter([0.0, 10.0, 1.0], [0.0, 0.0, np.nan])
    assert len(scatter) == 3
    assert scatter[0].get_fill_opacity() > 0
    assert scatter[1].get_fill_opacity() == 0
    assert scatter[2].get_fill_opacity() == 0


def test_ar7_a_parametric_curve_follows_its_function():
    ax = axes()
    spiral = ax.plot_parametric_curve(
        lambda t: (0.3 * t * np.cos(t), 0.3 * t * np.sin(t)), t_range=(0, 6)
    )
    assert isinstance(spiral, ParametricPlot)
    xy = anchors_xy(ax, spiral)
    radius = np.hypot(xy[:, 0], xy[:, 1])
    angle = np.unwrap(np.arctan2(xy[:, 1], xy[:, 0]))
    np.testing.assert_allclose(
        radius, 0.3 * (angle - angle[0] + 0.0) + radius[0], atol=1e-6
    )


def test_ar8_plot_line_graph_is_manims():
    xs, ys = [-2, -1, 0, 1, 2], [0, 1, 0.5, -1, 0]
    with tempconfig(RUN):
        ours, theirs = (
            axes(),
            Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4),
        )
        mine, manims = ours.plot_line_graph(xs, ys), theirs.plot_line_graph(xs, ys)
    assert isinstance(mine, VDict)
    assert isinstance(mine["line_graph"], LinePlot)
    assert isinstance(mine["vertex_dots"], ScatterPlot)
    np.testing.assert_allclose(
        mine["line_graph"].get_anchors(), manims["line_graph"].get_anchors(), atol=1e-9
    )
    assert (
        mine["line_graph"].get_stroke_color() == manims["line_graph"].get_stroke_color()
    )
    for a, b in zip(mine["vertex_dots"], manims["vertex_dots"], strict=True):
        np.testing.assert_allclose(a.get_center(), b.get_center(), atol=1e-9)


def test_ar9_i2gp_is_exact_between_samples():
    ax = axes()
    curve = ax.plot(np.sin)
    for x in (0.123456, -2.71, 1.0):
        np.testing.assert_allclose(ax.i2gp(x, curve), ax.c2p(x, np.sin(x)), atol=1e-12)
        np.testing.assert_allclose(
            ax.input_to_graph_point(x, curve), ax.c2p(x, np.sin(x))
        )
        assert ax.i2gc(x, curve) == pytest.approx((x, np.sin(x)))
    ax.x.range = (-1, 1)
    np.testing.assert_allclose(
        ax.i2gp(0.5, curve), ax.c2p(0.5, np.sin(0.5)), atol=1e-12
    )


def test_ar9_i2gp_on_a_line_interpolates_and_refuses_non_monotone_x():
    ax = axes()
    line = ax.line([0, 1, 2], [0, 1, 0])
    np.testing.assert_allclose(ax.i2gp(0.5, line), ax.c2p(0.5, 0.5), atol=1e-12)
    loop = ax.line([0, 1, 0.5], [0, 1, 0])
    with pytest.raises(ValueError):
        ax.i2gp(0.25, loop)


def test_ar9_a_graph_of_another_system_raises():
    ax, other = axes(), axes()
    curve = other.plot(np.sin)
    with pytest.raises(ValueError):
        ax.i2gp(0.0, curve)


def test_ar12_every_leaf_of_every_artist_is_a_library_leaf():
    ax = axes()
    artists = [
        ax.plot(np.sin),
        ax.line([0, 1], [0, 1]),
        ax.scatter([0, 1], [0, 1]),
        ax.plot_parametric_curve(lambda t: (t, t), t_range=(0, 1)),
    ]
    for artist in artists:
        assert all(isinstance(m, Leaf) for m in artist.get_family() if m.has_points())
