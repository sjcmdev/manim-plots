"""The legend (F-801, F-802, F-901, defect 7).

Rows LG-1 to LG-7 of `docs/acceptance/12-legend-style-animations.md`. Manim has no
legend, so the oracles are the artists' own style and the axes' rectangle through
`c2p`.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import ORIGIN, RED, RIGHT, UP, ManimColor, Text

import manim_plots as mp
from manim_plots.mobjects.leaves import Leaf

X, Y = (-3, 3, 1), (-2, 2, 1)


def axes():
    return mp.Axes(x_range=X, y_range=Y, x_length=6, y_length=4)


def two_curves(ax):
    return ax.plot(np.sin, label="sin"), ax.plot(np.cos, label="cos")


# --- LG-1 ----------------------------------------------------------------------------


def test_lg1_a_label_from_the_keyword_or_the_setter():
    ax = axes()
    sin = ax.plot(np.sin, label="sin")
    assert sin.get_label() == "sin"
    cos = ax.plot(np.cos)
    assert cos.get_label() is None
    assert cos.set_label("cos") is cos
    assert cos.get_label() == "cos"


def test_lg1_every_artist_takes_a_label():
    ax = axes()
    assert ax.line([0, 1, 2], [0, 1, 0], label="line").get_label() == "line"
    assert ax.scatter([0, 1], [1, 0], label="dots").get_label() == "dots"
    curve = ax.plot_parametric_curve(
        lambda t: (np.cos(t), np.sin(t)), t_range=(0, 6), label="circle"
    )
    assert curve.get_label() == "circle"


def test_lg1_label_is_not_a_style_keyword():
    curve = axes().plot(np.sin, label="sin", color=RED)
    assert ManimColor(curve.get_stroke_color()) == ManimColor(RED)


# --- LG-2 ----------------------------------------------------------------------------


def test_lg2_the_legend_collects_labelled_artists_in_order():
    ax = axes()
    sin, cos = two_curves(ax)
    ax.plot(lambda x: x / 2)  # no label: left out
    legend = ax.legend()
    assert isinstance(legend, mp.Legend)
    assert [entry.artist for entry in legend.entries] == [sin, cos]
    assert ax.get_legend() is legend


def test_lg2_no_labelled_artist_raises():
    ax = axes()
    ax.plot(np.sin)
    with pytest.raises(ValueError, match="label"):
        ax.legend()
    assert ax.get_legend() is None


def test_lg2_handles_and_labels_without_a_legend():
    ax = axes()
    two_curves(ax)
    handles, labels = ax.get_legend_handles_labels()
    assert labels == ["sin", "cos"]
    assert len(handles) == 2
    assert ax.get_legend() is None


# --- LG-3 ----------------------------------------------------------------------------


def test_lg3_a_line_handle_carries_the_artists_style():
    ax = axes()
    curve = ax.plot(np.sin, label="sin", color=RED, stroke_width=6)
    (entry,) = ax.legend().entries
    handle = entry.handle
    assert np.ptp(handle.points[:, 0]) == pytest.approx(0.5, abs=1e-9)
    assert np.ptp(handle.points[:, 1]) == pytest.approx(0.0, abs=1e-9)
    assert ManimColor(handle.get_stroke_color()) == ManimColor(curve.get_stroke_color())
    assert handle.get_stroke_width() == curve.get_stroke_width()
    assert handle.get_stroke_opacity() == curve.get_stroke_opacity()


def test_lg3_a_scatter_handle_is_a_copy_of_its_marker():
    ax = axes()
    ax.scatter([0, 1], [1, 0], label="dots")
    (entry,) = ax.legend().entries
    marker = ax.artists[0].submobjects[0]
    assert entry.handle.width == pytest.approx(marker.width, abs=1e-9)
    assert ManimColor(entry.handle.get_fill_color()) == ManimColor(
        marker.get_fill_color()
    )


def test_lg3_entries_stack_with_labels_left_aligned():
    ax = axes()
    two_curves(ax)
    legend = ax.legend(buff=0.25)
    first, second = legend.entries
    assert first.label.get_left()[0] == pytest.approx(
        second.label.get_left()[0], abs=1e-6
    )
    gap = first.label.get_left()[0] - first.handle.get_right()[0]
    assert gap == pytest.approx(0.25, abs=1e-6)
    assert second.handle.get_center()[1] < first.handle.get_center()[1]
    text = Text("sin", font_size=24)
    assert first.label.width == pytest.approx(text.width, abs=1e-6)
    assert first.label.height == pytest.approx(text.height, abs=1e-6)


# --- LG-4 ----------------------------------------------------------------------------

CORNERS = {
    "upper right": ((X[1], Y[1]), np.array([1, 1, 0])),
    "upper left": ((X[0], Y[1]), np.array([-1, 1, 0])),
    "lower left": ((X[0], Y[0]), np.array([-1, -1, 0])),
    "lower right": ((X[1], Y[0]), np.array([1, -1, 0])),
}


@pytest.mark.parametrize("location", list(CORNERS))
def test_lg4_the_legend_sits_buff_inside_its_corner(location):
    ax = axes()
    two_curves(ax)
    legend = ax.legend(location=location, buff=0.25)
    (x, y), direction = CORNERS[location]
    corner = ax.c2p(x, y)
    np.testing.assert_allclose(
        legend.get_corner(direction), corner - 0.25 * direction, atol=1e-6
    )


def test_lg4_an_unknown_location_lists_the_four():
    ax = axes()
    two_curves(ax)
    with pytest.raises(ValueError, match="upper right"):
        ax.legend(location="best")


def test_lg4_the_legend_follows_its_axes_and_keeps_its_corner():
    ax = axes()
    two_curves(ax)
    legend = ax.legend()
    ax.shift(RIGHT + UP)
    np.testing.assert_allclose(
        legend.get_corner(np.array([1, 1, 0])),
        ax.c2p(X[1], Y[1]) - 0.25 * np.array([1, 1, 0]),
        atol=1e-6,
    )
    ax.x.range = (-5, 5)
    np.testing.assert_allclose(
        legend.get_corner(np.array([1, 1, 0])),
        ax.c2p(5, Y[1]) - 0.25 * np.array([1, 1, 0]),
        atol=1e-6,
    )


# --- LG-5 ----------------------------------------------------------------------------


def test_lg5_a_legend_spans_systems_and_is_not_bound():
    a, b = axes(), axes().shift(3 * RIGHT)
    sin = a.plot(np.sin, label="sin")
    cos = b.plot(np.cos, label="cos")
    legend = mp.Legend(sin, cos)
    assert [e.artist for e in legend.entries] == [sin, cos]
    np.testing.assert_allclose(legend.get_center(), ORIGIN, atol=1e-6)
    before = legend.get_center()
    a.shift(UP)
    np.testing.assert_allclose(legend.get_center(), before, atol=1e-9)


def test_lg5_an_unlabelled_artist_raises():
    curve = axes().plot(np.sin)
    with pytest.raises(ValueError, match="label"):
        mp.Legend(curve)


# --- LG-6 ----------------------------------------------------------------------------


def test_lg6_merge_and_split():
    ax = axes()
    sin, cos = two_curves(ax)
    tan = ax.plot(lambda x: x / 2, label="half")
    a, b = mp.Legend(sin, cos), mp.Legend(cos, tan)
    merged = a.merge(b)
    assert [e.artist for e in merged.entries] == [sin, cos, tan]
    assert [e.artist for e in a.entries] == [sin, cos]
    assert [e.artist for e in b.entries] == [cos, tan]
    parts = merged.split()
    assert [[e.artist for e in p.entries] for p in parts] == [[sin], [cos], [tan]]
    assert len(merged.entries) == 3


# --- LG-7 ----------------------------------------------------------------------------


def test_lg7_every_legend_leaf_is_a_library_leaf():
    ax = axes()
    two_curves(ax)
    ax.scatter([0, 1], [0, 1], label="dots")
    legend = ax.legend()
    leaves = legend.family_members_with_points()
    assert leaves
    assert all(isinstance(m, Leaf) for m in leaves), {type(m) for m in leaves}
