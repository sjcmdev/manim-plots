"""The coordinate system, minimal (task 09): construction, parity with Manim's `Axes`,
conversions, ranges, registration.

Rows AX-1 to AX-10 of `docs/acceptance/09-leaves-context-frame.md`. The oracle for
geometry, style and conversions is Manim's own `Axes`, built with the same arguments in
the same test.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from manim import RIGHT, Axes, Scene, config, tempconfig

import manim_plots as mp
from manim_plots.mobjects.artists import FunctionPlot
from manim_plots.mobjects.leaves import Leaf

MEDIA = Path(__file__).parents[1] / "visual" / "_out" / "media"
RUN = {"dry_run": True, "disable_caching": True, "media_dir": str(MEDIA)}

CASES = [
    {},
    {"x_range": (0, 10, 1), "y_range": (-2, 2, 0.5)},
    {"x_range": (-3, 5), "x_length": 8, "tips": False},
]


def ids(case: dict[str, object]) -> str:
    return ",".join(f"{k}={v}" for k, v in case.items()) or "default"


# --- AX-1, AX-2 -----------------------------------------------------------------------


def test_ax1_defaults_are_manims():
    ax = mp.Axes()
    np.testing.assert_array_equal(ax.x.range.value, [-7, 7])
    np.testing.assert_array_equal(ax.y.range.value, [-4, 4])
    manim = Axes()
    for ours, theirs in ((ax.x_axis, manim.x_axis), (ax.y_axis, manim.y_axis)):
        np.testing.assert_allclose(
            np.ptp(ours.line.points, axis=0), np.ptp(theirs.points, axis=0)
        )
    assert ax.x_axis.tip is not None and ax.y_axis.tip is not None


def test_ax1_the_manim_name_is_an_alias_outside_the_star_export():
    assert mp.Axes is mp.CartesianAxes
    assert "CartesianAxes" in mp.__all__
    assert "Axes" not in mp.__all__


@pytest.mark.parametrize(
    "kwargs, word",
    [
        ({"x_range": (0, math.inf)}, "x_range"),
        ({"x_range": (1, 1)}, "x_range"),
        ({"y_range": (0,)}, "y_range"),
        ({"x_range": (0, 10, 0)}, "step"),
        ({"y_range": (0, 10, -1)}, "step"),
        ({"x_length": 0}, "x_length"),
        ({"y_length": math.nan}, "y_length"),
    ],
    ids=str,
)
def test_ax2_malformed_arguments_raise_naming_them(kwargs, word):
    with pytest.raises(ValueError, match=word):
        mp.Axes(**kwargs)


def test_ax2_the_opengl_renderer_is_refused():
    # Not `tempconfig`: it restores the renderer without its setter, so Manim's classes
    # would keep their OpenGL bases for the rest of the session.
    config.renderer = "opengl"
    try:
        with pytest.raises(ValueError, match="Cairo"):
            mp.Axes()
    finally:
        config.renderer = "cairo"


# --- AX-3: structure ---------------------------------------------------------------


def test_ax3_the_frame_is_the_last_member():
    ax = mp.Axes()
    assert ax.submobjects == [ax.x_axis, ax.y_axis, ax.frame]
    for axis in (ax.x_axis, ax.y_axis):
        assert {id(axis.line), id(axis.ticks), id(axis.tip)} <= {
            id(m) for m in axis.submobjects
        }


def test_ax3_every_leaf_is_a_library_type():
    ax = mp.Axes()
    leaves = [m for m in ax.get_family() if m.has_points()]
    assert leaves
    assert all(isinstance(m, Leaf) for m in leaves)
    curve = ax.plot(np.sin)
    assert isinstance(curve, Leaf)
    assert curve not in ax.get_family()


# --- AX-4: parity with Manim's Axes ---------------------------------------------------


def same_points(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and np.allclose(a, b, rtol=0, atol=1e-9)


@pytest.mark.parametrize("case", CASES, ids=ids)
def test_ax4_lines_and_tips_are_manims(case):
    ours, theirs = mp.Axes(**case), Axes(**case)
    for mine, manim_axis in (
        (ours.x_axis, theirs.x_axis),
        (ours.y_axis, theirs.y_axis),
    ):
        np.testing.assert_allclose(
            mine.line.points, manim_axis.points, rtol=0, atol=1e-9
        )
        assert mine.line.get_stroke_width() == manim_axis.get_stroke_width()
        assert mine.line.get_stroke_color() == manim_axis.get_stroke_color()
        assert mine.line.get_stroke_opacity() == manim_axis.get_stroke_opacity()
        if case.get("tips", True):
            assert mine.tip is not None
            np.testing.assert_allclose(
                mine.tip.points, manim_axis.tip.points, rtol=0, atol=1e-9
            )
            assert mine.tip.get_fill_color() == manim_axis.tip.get_fill_color()
            assert mine.tip.get_fill_opacity() == manim_axis.tip.get_fill_opacity()
            assert mine.tip.get_stroke_width() == manim_axis.tip.get_stroke_width()
        else:
            assert mine.tip is None


@pytest.mark.parametrize("case", CASES, ids=ids)
def test_ax4_every_manim_tick_is_there_plus_the_one_under_the_tip(case):
    ours, theirs = mp.Axes(**case), Axes(**case)
    for mine, manim_axis in (
        (ours.x_axis, theirs.x_axis),
        (ours.y_axis, theirs.y_axis),
    ):
        our_ticks = [t.points for t in mine.ticks]
        for tick in manim_axis.ticks:
            assert any(same_points(tick.points, p) for p in our_ticks)
            style = next(t for t in mine.ticks if same_points(tick.points, t.points))
            assert style.get_stroke_width() == tick.get_stroke_width()
            assert style.get_stroke_color() == tick.get_stroke_color()
        extra = len(our_ticks) - len(manim_axis.ticks)
        assert extra == (1 if case.get("tips", True) else 0)


# --- AX-5 to AX-7: conversions -------------------------------------------------------


@pytest.mark.parametrize("case", CASES[:2], ids=ids)
def test_ax5_c2p_follows_manims_convention_and_values(case):
    ours, theirs = mp.Axes(**case), Axes(**case)
    np.testing.assert_allclose(ours.c2p(1, 1), theirs.c2p(1, 1), atol=1e-12)
    assert ours.c2p(1, 1).shape == (3,)
    many = ours.c2p([1, 2], [0.5, -1])
    assert many.shape == (3, 2)
    np.testing.assert_allclose(many, theirs.c2p([1, 2], [0.5, -1]), atol=1e-12)
    rows = np.array([[1.0, 1.0], [2.0, -0.5]])
    np.testing.assert_allclose(ours.c2p(rows), theirs.c2p(rows), atol=1e-12)
    assert ours.c2p(rows).shape == (2, 3)
    np.testing.assert_allclose(ours @ (1, 1), theirs.c2p(1, 1), atol=1e-12)


@pytest.mark.parametrize("case", CASES[:2], ids=ids)
def test_ax5_p2c_follows_manims_convention_and_values(case):
    ours, theirs = mp.Axes(**case), Axes(**case)
    point = theirs.c2p(1.5, 0.5)
    np.testing.assert_allclose(ours.p2c(point), theirs.p2c(point), atol=1e-12)
    assert ours.p2c(point).shape == (2,)
    points = np.array([theirs.c2p(1, 1), theirs.c2p(2, -1), theirs.c2p(-1, 0)])
    np.testing.assert_allclose(ours.p2c(points), theirs.p2c(points), atol=1e-12)
    assert ours.p2c(points).shape == (3, 2)


@pytest.mark.parametrize("bad", [(math.nan, 0.0), (0.0, math.inf)])
def test_ax6_c2p_raises_and_never_returns_nan(bad):
    with pytest.raises(ValueError):
        mp.Axes().c2p(*bad)


def test_ax6_p2c_raises_on_a_non_finite_or_off_plane_point():
    ax = mp.Axes()
    with pytest.raises(ValueError):
        ax.p2c(np.array([np.nan, 0.0, 0.0]))
    with pytest.raises(ValueError):
        ax.p2c(np.array([1.0, 1.0, 5.0]))
    np.testing.assert_allclose(
        ax.p2c(np.array([0.0, 0.0, 1e-9])), [0.0, 0.0], atol=1e-6
    )


OPERATIONS = {
    "shift": lambda ax: ax.shift(2 * RIGHT),
    "rotate": lambda ax: ax.rotate(0.7),
    "scale": lambda ax: ax.scale(0.4),
    "stretch": lambda ax: ax.stretch(2.5, 1),
    "flip": lambda ax: ax.flip(),
    "apply_matrix": lambda ax: ax.apply_matrix([[1, 0.4], [0.1, 0.9]]),
    "defect 14": lambda ax: ax.scale(2).rotate(0.3).shift(RIGHT).stretch(0.5, 0),
}


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_ax7_round_trip_survives_geometric_operations(name):
    ax = mp.Axes(x_range=(-3, 9, 1), y_range=(-2, 2, 0.5))
    OPERATIONS[name](ax)
    xs = np.linspace(-3, 9, 13)
    ys = np.linspace(-2, 2, 13)
    back = ax.p2c(np.asarray(ax.c2p(xs, ys)).T)
    np.testing.assert_allclose(back[0], xs, rtol=0, atol=1e-9 * 12)
    np.testing.assert_allclose(back[1], ys, rtol=0, atol=1e-9 * 4)


# --- AX-8: ranges --------------------------------------------------------------------


def test_ax8_the_short_and_the_manim_name_are_one_axis():
    ax = mp.Axes()
    assert ax.x is ax.x_axis and ax.y is ax.y_axis


def test_ax8_a_range_is_a_read_only_parameter():
    ax = mp.Axes()
    value = ax.x.range.value
    assert not value.flags.writeable
    ax.x.range = (0, 20)
    np.testing.assert_array_equal(ax.x.range.value, [0, 20])
    ax.set_y_range((-1, 1))
    np.testing.assert_array_equal(ax.y.range.value, [-1, 1])


def test_ax8_a_range_change_regenerates_ticks_and_moves_the_curve():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(-2, 2, 1))
    curve = ax.plot(np.sin)
    before = curve.points.copy()
    count = len(ax.x_axis.ticks)
    ax.set_x_range((0, 5))
    assert len(ax.x_axis.ticks) < count
    assert not np.array_equal(curve.points, before)
    # The locator is untouched: ticks are still at whole numbers.
    for tick in ax.x_axis.ticks:
        x = ax.p2c(tick.get_center())[0]
        assert math.isclose(x, round(x), abs_tol=1e-9)


def test_ax8_a_range_can_be_bound_to_a_callable():
    ax = mp.Axes(x_range=(0, 10, 1))
    ax.x.range.bind(lambda: (0, 4))
    assert ax.x.range.tracker is not None


# --- AX-9, AX-10: plotting and registration ------------------------------------------


def test_ax9_plot_returns_a_registered_plot_with_manims_default_stroke():
    ax = mp.Axes()
    curve = ax.plot(np.sin)
    assert isinstance(curve, FunctionPlot)
    assert curve.get_stroke_color() == Axes().plot(np.sin).get_stroke_color()
    assert curve.get_stroke_width() == Axes().plot(np.sin).get_stroke_width()


def test_ax9_style_keywords_are_passed_on():
    curve = mp.Axes().plot(np.sin, color="#FF0000", stroke_width=7)
    assert str(curve.get_stroke_color()).upper() == "#FF0000"
    assert curve.get_stroke_width() == 7


def test_ax10_add_registers_and_a_second_system_is_refused():
    ax, other = mp.Axes(), mp.Axes()
    curve = ax.plot(np.sin)
    with pytest.raises(ValueError):
        other.add(curve)
    assert ax.add(curve) is ax


def test_ax10_adding_the_system_to_a_scene_does_not_add_its_artists():
    with tempconfig(RUN | {"progress_bar": "none"}):
        scene = Scene()
        ax = mp.Axes()
        curve = ax.plot(np.sin)
        scene.add(ax)
        assert curve not in scene.mobjects
        scene.add(curve)
        assert curve in scene.mobjects
