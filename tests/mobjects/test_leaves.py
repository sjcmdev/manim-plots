"""Library leaves: the `points` property, the cache, the hidden frame (F-901, F-902,
F-102, F-705, F-706, F-914, F-1004).

Rows LF-1 to LF-6 of `docs/acceptance/09-leaves-context-frame.md`. Oracles: object
identity, the function itself mapped through `c2p`, and plain `VGroup`s of the visible
leaves.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from manim import BLUE, RED, VGroup, VMobject

import manim_plots as mp
from manim_plots.core import ManimPlotsWarning
from manim_plots.mobjects.leaves import Leaf

from .helpers import visible_leaves


def test_lf1_points_is_a_property_on_the_leaf_type():
    assert isinstance(Leaf.__dict__["points"], property)
    assert issubclass(Leaf, VMobject)


def test_lf2_a_clean_getter_returns_the_cache_itself():
    ax = mp.Axes()
    curve = ax.plot(np.sin)
    for leaf in [*visible_leaves(ax), curve]:
        assert leaf.points is leaf.points


def test_lf3_a_data_change_rebuilds_on_the_next_read_and_only_then():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(-2, 2, 1))
    curve = ax.plot(np.sin)
    first = curve.points
    assert curve.points is first
    ax.x.range = (0, 6)
    second = curve.points
    assert second is not first
    assert not np.array_equal(second, first)
    assert curve.points is second


def test_lf4_the_curve_lies_on_the_function_through_c2p():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
    curve = ax.plot(np.sin)
    anchors = curve.get_anchors()
    x = ax.p2c(anchors)[0]
    np.testing.assert_allclose(anchors, np.asarray(ax.c2p(x, np.sin(x))).T, atol=1e-9)
    start, end = ax.p2c(curve.get_start())[0], ax.p2c(curve.get_end())[0]
    assert math.isclose(start, -3, abs_tol=1e-9) and math.isclose(end, 3, abs_tol=1e-9)


def test_lf4_the_curve_never_leaves_the_axes_rectangle():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
    curve = ax.plot(lambda x: x**3)
    lo, hi = ax.c2p(-3, -2), ax.c2p(3, 2)
    points = curve.points
    assert (points[:, 0] >= lo[0] - 1e-9).all() and (points[:, 0] <= hi[0] + 1e-9).all()
    assert (points[:, 1] >= lo[1] - 1e-9).all() and (points[:, 1] <= hi[1] + 1e-9).all()


def test_lf4_a_pole_splits_the_curve_into_subpaths():
    ax = mp.Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
    with pytest.warns(ManimPlotsWarning, match="split"):
        curve = ax.plot(lambda x: 1 / (x - 4.5))
        paths = curve.get_subpaths()
    assert len(paths) == 2
    pole = ax.c2p(4.5, 0)[0]
    assert paths[0][:, 0].max() < pole < paths[1][:, 0].min()


STYLE_CALLS = {
    "set_color": lambda m: m.set_color(RED),
    "set_stroke": lambda m: m.set_stroke(BLUE, width=9, opacity=1),
    "set_fill": lambda m: m.set_fill(RED, opacity=1),
    "set_opacity": lambda m: m.set_opacity(1),
    "fade": lambda m: m.fade(0.2),
    "match_style": lambda m: m.match_style(
        VMobject().set_stroke(RED, 5).set_fill(RED, 1)
    ),
}


@pytest.mark.parametrize("name", list(STYLE_CALLS))
def test_lf5_the_frame_stays_invisible_under_every_style_call(name):
    ax = mp.Axes()
    STYLE_CALLS[name](ax)
    frame = ax.frame
    assert frame.get_stroke_opacity() == 0
    assert frame.get_fill_opacity() == 0
    assert frame.get_stroke_width() == 0 or frame.get_stroke_opacity() == 0


def test_lf5_the_frame_ignores_partial_drawing():
    ax = mp.Axes()
    before = np.array(ax.frame.points, copy=True)
    ax.frame.pointwise_become_partial(ax.frame.copy(), 0.0, 0.3)
    np.testing.assert_array_equal(ax.frame.points, before)


def test_lf5_the_frame_gives_no_boundary_anchors():
    ax = mp.Axes().shift(np.array([1.0, 0.5, 0.0])).rotate(0.3)
    others = VGroup(*[m for m in ax.submobjects if m is not ax.frame])
    np.testing.assert_allclose(ax.get_center(), others.get_center(), atol=1e-9)
    assert math.isclose(ax.width, others.width, abs_tol=1e-9)
    assert math.isclose(ax.height, others.height, abs_tol=1e-9)


def test_lf6_copies_keep_the_leaf_types():
    ax = mp.Axes()
    curve = ax.plot(np.sin)
    for original in [ax, curve]:
        copied = original.copy()
        assert [type(m) for m in copied.get_family()] == [
            type(m) for m in original.get_family()
        ]
