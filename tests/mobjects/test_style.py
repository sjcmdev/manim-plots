"""The colour cycle, line styles, markers and stroke under scaling (F-803-F-807).

Rows CY-1 to CY-3 and ST-1 to ST-4 of `docs/acceptance/12-legend-style-animations.md`.
The oracles are Manim's colours and shapes, and arc length measured here on the drawn
cubic curves.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from manim import (
    BLUE,
    DEFAULT_DOT_RADIUS,
    GREEN,
    ORANGE,
    PINK,
    PURE_YELLOW,
    PURPLE,
    RED,
    TAU,
    TEAL,
    WHITE,
    YELLOW,
    Circle,
    Cross,
    Dot,
    ManimColor,
    Square,
    Star,
    Triangle,
)

import manim_plots as mp

from .helpers import along


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)


def color(c) -> str:
    return ManimColor(c).to_hex().upper()


# --- CY ------------------------------------------------------------------------------


def test_cy1_the_cycle_is_manims_colours_from_white():
    expected = (WHITE, BLUE, YELLOW, GREEN, RED, PURPLE, ORANGE, TEAL)
    assert [color(c) for c in mp.COLOR_CYCLE] == [color(c) for c in expected]


def test_cy2_each_uncoloured_artist_takes_the_next_colour():
    ax = axes()
    first = ax.plot(np.sin)
    explicit = ax.plot(np.cos, color=PINK)
    second = ax.plot(lambda x: x / 3)
    third = ax.line([0, 1, 2], [0, 1, 0])
    stroked = ax.plot(np.sin, stroke_color=RED)
    fourth = ax.scatter([0, 1], [1, 0])
    graph = ax.plot_line_graph([0, 1, 2], [1, 0, 1])
    fifth = ax.plot(lambda x: x / 4)
    assert color(first.get_stroke_color()) == color(WHITE)
    assert color(explicit.get_stroke_color()) == color(PINK)
    assert color(second.get_stroke_color()) == color(BLUE)
    assert color(third.get_stroke_color()) == color(YELLOW)
    assert color(stroked.get_stroke_color()) == color(RED)
    assert color(fourth.submobjects[0].get_fill_color()) == color(GREEN)
    assert color(graph["line_graph"].get_stroke_color()) == color(PURE_YELLOW)
    assert color(fifth.get_stroke_color()) == color(RED)


def test_cy2_the_count_is_per_system():
    a, b = axes(), axes()
    a.plot(np.sin)
    assert color(b.plot(np.sin).get_stroke_color()) == color(WHITE)
    assert color(a.plot(np.cos).get_stroke_color()) == color(BLUE)


def test_cy3_a_custom_marker_keeps_its_style_and_takes_no_colour():
    ax = axes()
    custom = ax.scatter([0, 1], [0, 1], marker=Square(side_length=0.2, color=PINK))
    assert color(custom.submobjects[0].get_stroke_color()) == color(PINK)
    assert color(ax.plot(np.sin).get_stroke_color()) == color(WHITE)


# --- ST-1, ST-2: dashes -------------------------------------------------------------


def lengths(path: np.ndarray) -> float:
    pts = along(path, 64)
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def pieces(mob) -> list[np.ndarray]:
    return [np.asarray(p) for p in mob.get_subpaths() if len(p)]


def flat(**kwargs):
    return axes().plot(lambda x: 0.5 + 0 * x, **kwargs)


@pytest.mark.parametrize(
    "style, on, off",
    [(mp.LineStyle.DASHED, 0.2, 0.1), (mp.LineStyle.DOTTED, 0.03, 0.07)],
)
def test_st1_line_styles_dash_by_arc_length(style, on, off):
    dashes = pieces(flat(line_style=style))
    assert len(dashes) == int(np.ceil(6 / (on + off) - 1e-9))
    for dash in dashes[:-1]:
        assert lengths(dash) == pytest.approx(on, abs=1e-3)
    for a, b in itertools.pairwise(dashes):
        assert np.linalg.norm(b[0] - a[-1]) == pytest.approx(off, abs=1e-3)


def test_st1_a_custom_pattern_wins_over_the_style():
    dashes = pieces(flat(line_style=mp.LineStyle.DOTTED, dash=(0.5, 0.25)))
    assert lengths(dashes[0]) == pytest.approx(0.5, abs=1e-3)


def test_st1_a_solid_line_is_one_piece():
    assert len(pieces(flat(line_style=mp.LineStyle.SOLID))) == 1


def test_st1_a_shorthand_string_raises():
    with pytest.raises(TypeError, match="LineStyle"):
        flat(line_style="--")


def test_st2_dashes_follow_the_arc_on_a_curve():
    curve = axes().plot(np.sin, line_style=mp.LineStyle.DASHED)
    for dash in pieces(curve)[:-1]:
        assert lengths(dash) == pytest.approx(0.2, abs=1e-3)


def test_st2_finer_sampling_keeps_the_dashes_in_place():
    coarse = axes().plot(np.sin, line_style=mp.LineStyle.DASHED)
    fine = axes().plot(np.sin, x_range=(-3, 3, 0.01), line_style=mp.LineStyle.DASHED)
    a, b = pieces(coarse), pieces(fine)
    assert len(a) == len(b)
    starts = np.array([p[0] for p in a]) - np.array([p[0] for p in b])
    assert np.abs(starts).max() < 1e-2


def test_st2_the_pattern_restarts_on_each_piece():
    ax = axes()
    xs = np.linspace(-3, 3, 13)
    ys = np.where(np.isclose(xs, 0), np.nan, 0.5)
    with pytest.warns(mp.ManimPlotsWarning):
        line = ax.line(xs, ys, line_style=mp.LineStyle.DASHED)
    starts = [p[0] for p in pieces(line)]
    second_piece = ax.c2p(0.5, 0.5)
    assert any(np.linalg.norm(s - second_piece) < 1e-9 for s in starts)


# --- ST-3: markers -------------------------------------------------------------------

WIDTH = 2 * DEFAULT_DOT_RADIUS
SHAPES = {
    "DOT": lambda: Dot(),
    "CIRCLE": lambda: Circle().set(width=WIDTH),
    "SQUARE": lambda: Square().set(width=WIDTH),
    "TRIANGLE": lambda: Triangle().set(width=WIDTH),
    "CROSS": lambda: Cross(Square().set(width=WIDTH)),
    "STAR": lambda: Star().set(width=WIDTH),
}


@pytest.mark.parametrize("name", list(SHAPES))
def test_st3_a_named_marker_is_manims_shape(name):
    ax = axes()
    scatter = ax.scatter([1.0], [0.5], marker=getattr(mp.Marker, name))
    marker = scatter.submobjects[0]
    target = ax.c2p(1.0, 0.5)
    assert marker.width == pytest.approx(WIDTH, abs=1e-6)
    np.testing.assert_allclose(marker.get_center(), target, atol=1e-6)
    shape = SHAPES[name]().move_to(target)
    ours = [m.points for m in marker.family_members_with_points()]
    theirs = [m.points for m in shape.family_members_with_points()]
    assert len(ours) == len(theirs)
    for a, b in zip(ours, theirs, strict=True):
        np.testing.assert_allclose(a, b, atol=1e-6)


@pytest.mark.parametrize("name", ["SQUARE", "TRIANGLE", "STAR", "DOT"])
def test_st3_filled_markers_take_the_cycle_colour_as_fill(name):
    marker = (
        axes().scatter([0.0], [0.0], marker=getattr(mp.Marker, name)).submobjects[0]
    )
    assert marker.get_fill_opacity() == 1
    assert color(marker.get_fill_color()) == color(WHITE)


def test_st3_an_outline_marker_is_not_filled():
    marker = axes().scatter([0.0], [0.0], marker=mp.Marker.CIRCLE).submobjects[0]
    assert marker.get_fill_opacity() == 0


def test_st3_a_string_marker_raises():
    with pytest.raises(TypeError, match="Marker"):
        axes().scatter([0.0], [0.0], marker="o")


# --- ST-4 ----------------------------------------------------------------------------


def widths(ax, curve) -> list[float]:
    leaves = [m for m in ax.family_members_with_points() if m is not ax.frame]
    return [float(m.get_stroke_width()) for m in [*leaves, curve]]


def test_st4_scale_leaves_stroke_widths_as_manim_does():
    ax = axes()
    curve = ax.plot(np.sin)
    before = widths(ax, curve)
    ax.scale(2)
    assert widths(ax, curve) == before


def test_st4_scale_stroke_opts_in():
    ax = axes()
    curve = ax.plot(np.sin)
    before = widths(ax, curve)
    ax.scale(2, scale_stroke=True)
    assert widths(ax, curve) == pytest.approx([2 * w for w in before])


# --- CL: clipping -------------------------------------------------------------------

RECT_X, RECT_Y = (-3.0, 3.0), (-2.0, 2.0)  # the rectangle of `axes()` in scene units


def extent(mob) -> tuple[float, float]:
    """The largest |y| an artist's points reach, and the largest |x|."""
    points = np.asarray(mob.points)
    return float(np.abs(points[:, 1]).max()), float(np.abs(points[:, 0]).max())


def tall():
    """A curve that leaves the axes a little: 2.3 sin x on y in (-2, 2)."""
    return lambda x: 2.3 * np.sin(x)


def test_cl1_clipping_is_on_by_default_at_the_rectangle():
    curve = axes().plot(tall())
    assert extent(curve)[0] == pytest.approx(2.0, abs=1e-9)
    assert len(pieces(curve)) == 3


def test_cl1_clip_false_draws_the_whole_curve_as_manim_does():
    ax = axes()
    curve = ax.plot(tall(), clip=False)
    peak = ax.c2p(0, 2.3)[1] - ax.c2p(0, 0)[1]
    assert extent(curve)[0] == pytest.approx(peak, abs=5e-3)  # a spline's overshoot
    assert len(pieces(curve)) == 1


@pytest.mark.parametrize("margin", [0.2, 0.5])
def test_cl1_a_positive_margin_widens_the_rectangle(margin):
    curve = axes().plot(tall(), clip=margin)
    top = extent(curve)[0]
    assert top <= 2.0 + margin + 1e-9
    assert top > 2.0 + min(margin, 0.3) - 1e-3  # reaches past the rectangle


def test_cl1_a_margin_wide_enough_keeps_the_curve_whole():
    curve = axes().plot(tall(), clip=0.5)
    assert len(pieces(curve)) == 1


def test_cl1_a_negative_margin_narrows_the_rectangle():
    curve = axes().plot(np.sin, clip=-0.5)
    top, side = extent(curve)
    assert top <= 1.5 + 1e-9 and side <= 2.5 + 1e-9


def test_cl1_a_margin_that_leaves_nothing_raises():
    with pytest.raises(ValueError, match="clip"):
        axes().plot(np.sin, clip=-2.5)


@pytest.mark.parametrize(
    "make",
    [
        lambda ax, clip: ax.line([-4, 0, 4], [0, 2.2, 0], clip=clip),
        lambda ax, clip: ax.plot_parametric_curve(
            lambda t: (2.2 * np.cos(t), 2.2 * np.sin(t)), t_range=(0, 6.28), clip=clip
        ),
    ],
    ids=["line", "parametric"],
)
def test_cl1_every_line_like_artist_takes_clip(make):
    clipped, free = make(axes(), True), make(axes(), False)
    assert extent(clipped)[0] <= 2.0 + 1e-9
    assert extent(free)[0] > 2.1


def test_cl1_a_scatter_shows_points_within_the_margin():
    ax = axes()
    xs, ys = [0.0, 0.0, 0.0], [1.0, 2.2, 3.0]  # inside, within 0.3 above, beyond
    shown = [m.get_fill_opacity() > 0 for m in ax.scatter(xs, ys, clip=0.3)]
    assert shown == [True, True, False]
    assert [m.get_fill_opacity() > 0 for m in axes().scatter(xs, ys, clip=False)] == [
        True
    ] * 3
    assert [m.get_fill_opacity() > 0 for m in axes().scatter(xs, ys)] == [
        True,
        False,
        False,
    ]


def test_cl1_a_pole_splits_whatever_clip_is():
    ax = mp.Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
    with pytest.warns(mp.ManimPlotsWarning):
        curve = ax.plot(lambda x: 1 / (x - 4.5), clip=0.5)
    assert len(pieces(curve)) == 2


def test_cl2_set_clip_rebuilds_and_reads_back():
    curve = axes().plot(tall())
    assert curve.get_clip() is True
    assert curve.set_clip(False) is curve
    assert curve.get_clip() is False
    assert len(pieces(curve)) == 1
    curve.set_clip(0.2)
    assert curve.get_clip() == 0.2
    assert extent(curve)[0] <= 2.2 + 1e-9


# --- CP: clipping per axis (task 15) -------------------------------------------------


def wide(clip):
    """2.3 sin x over x in (-2 pi, 2 pi): it leaves the rectangle on both axes and
    ends on y = 0, inside the y interval."""
    return axes().plot(tall(), x_range=(-TAU, TAU), clip=clip)


def test_cp1_y_unclipped_reaches_past_the_top_and_stays_within_the_sides():
    top, side = extent(wide((True, False)))
    assert top == pytest.approx(2.3, abs=5e-3)  # a spline's overshoot
    assert side <= 3.0 + 1e-9


def test_cp1_x_unclipped_reaches_past_the_sides_and_stays_within_the_top():
    top, side = extent(wide((False, True)))
    assert side == pytest.approx(TAU, abs=1e-6)
    assert top <= 2.0 + 1e-9


def test_cp1_a_margin_on_one_axis_only():
    top, side = extent(wide((0.2, False)))
    assert 3.1 < side <= 3.2 + 1e-9
    assert top == pytest.approx(2.3, abs=5e-3)
    top, side = extent(wide((False, 0.2)))
    assert side == pytest.approx(TAU, abs=1e-6)
    assert 2.1 < top <= 2.2 + 1e-9


@pytest.mark.parametrize("value", [True, False, 0.2, -0.5])
def test_cp1_a_single_value_equals_its_pair(value):
    np.testing.assert_array_equal(wide(value).points, wide((value, value)).points)


def test_cp1_a_list_is_a_pair():
    np.testing.assert_array_equal(
        wide([True, False]).points, wide((True, False)).points
    )


@pytest.mark.parametrize(
    "make",
    [
        lambda ax, clip: ax.line([-5, 0, 5], [0, 2.2, 0], clip=clip),
        lambda ax, clip: ax.plot_parametric_curve(
            lambda t: (4 * np.cos(t), 2.2 * np.sin(t)), t_range=(0, 6.28), clip=clip
        ),
        lambda ax, clip: ax.plot_line_graph([-5, 0, 5], [0, 2.2, 0], clip=clip)[
            "line_graph"
        ],
    ],
    ids=["line", "parametric", "line_graph"],
)
def test_cp2_every_line_like_artist_clips_per_axis(make):
    top, side = extent(make(axes(), (True, False)))
    assert side <= 3.0 + 1e-9 and top > 2.1
    top, side = extent(make(axes(), (False, True)))
    assert side > 3.9 and top <= 2.0 + 1e-9


SCATTER = ([0.0, 4.0, 0.0, 4.0], [0.0, 0.0, 3.0, 3.0])  # in, x out, y out, both out


@pytest.mark.parametrize(
    ("clip", "shown"),
    [
        (True, [True, False, False, False]),
        ((False, True), [True, True, False, False]),
        ((True, False), [True, False, True, False]),
        ((False, False), [True, True, True, True]),
        ((1.5, True), [True, True, False, False]),
        ((True, 1.5), [True, False, True, False]),
    ],
)
def test_cp3_a_scatter_hides_points_outside_a_clipped_axis_only(clip, shown):
    markers = axes().scatter(*SCATTER, clip=clip)
    assert [m.get_fill_opacity() > 0 for m in markers] == shown


def test_cp4_a_pole_splits_with_y_unclipped():
    with pytest.warns(mp.ManimPlotsWarning):
        curve = axes().plot(lambda x: 1 / (x - 0.5), clip=(True, False))
    assert len(pieces(curve)) == 2
    top, side = extent(curve)
    assert top > 2.0 and side <= 3.0 + 1e-9


@pytest.mark.parametrize(
    ("clip", "error"),
    [
        ((True,), ValueError),
        ((True, True, True), ValueError),
        ((True, "x"), TypeError),
        ((None, True), TypeError),
        ((True, np.inf), ValueError),
        ((np.nan, True), ValueError),
        ((-3.5, True), ValueError),  # x narrowed to nothing
        ((True, -2.5), ValueError),  # y narrowed to nothing
        ((False, -2.5), ValueError),
    ],
)
def test_cp5_a_bad_pair_raises_naming_clip(clip, error):
    with pytest.raises(error, match="clip"):
        axes().plot(np.sin, clip=clip)
    curve = axes().plot(np.sin)
    before = np.array(curve.points)
    with pytest.raises(error, match="clip"):
        curve.set_clip(clip)
    assert curve.get_clip() is True
    np.testing.assert_array_equal(curve.points, before)


@pytest.mark.parametrize("clip", [(-2.5, True), (-2.5, False), (True, -1.5)])
def test_cp5_a_margin_that_leaves_something_on_each_clipped_axis_is_accepted(clip):
    axes().plot(np.sin, clip=clip)


def test_cp6_set_clip_takes_a_pair_and_reads_it_back_as_a_tuple():
    curve = wide(True)
    assert curve.set_clip([False, True]) is curve
    assert curve.get_clip() == (False, True)
    assert isinstance(curve.get_clip(), tuple)
    np.testing.assert_array_equal(curve.points, wide((False, True)).points)


def test_cp6_become_takes_a_pair_over():
    ax = axes()
    curve = ax.plot(tall())
    curve.become(ax.plot(tall(), clip=(True, False)))
    assert curve.get_clip() == (True, False)
    assert extent(curve)[0] == pytest.approx(2.3, abs=5e-3)
