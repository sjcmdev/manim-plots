"""Task 22: polar, rows PH, PP, PX and ND of `docs/acceptance/22-polar.md`.

The oracles: Manim's own `PolarPlane` where `mp.PolarPlane` keeps its behaviour, and the
polar map written out by hand, ``centre + d (cos φ, sin φ)``, everywhere else.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest
from manim import (
    BLUE_D,
    DOWN,
    PI,
    RED,
    RIGHT,
    TAU,
    UP,
    Create,
    ManimColor,
    PolarPlane,
    Scene,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, dense, probe


def pts(mob) -> np.ndarray:
    return np.asarray(mob.points)


def radii(mob, centre) -> np.ndarray:
    """Distances from ``centre`` of points along the drawn curve."""
    return np.linalg.norm(dense(pts(mob))[:, :2] - np.asarray(centre)[:2], axis=1)


def angle(vector) -> float:
    return float(np.arctan2(vector[1], vector[0]))


def same_angle(a: float, b: float, atol: float = 1e-6) -> bool:
    return abs((a - b + PI) % TAU - PI) < atol


def at(r: float, phi: float) -> np.ndarray:
    return np.array([r * np.cos(phi), r * np.sin(phi), 0.0])


# --- PH -------------------------------------------------------------------------------


def axes(**kwargs):
    return mp.Axes(
        x_range=(-4, 4, 1), y_range=(-2, 2, 1), x_length=8, y_length=6, **kwargs
    )


def test_ph1_polar_to_point_is_c2p_of_the_cartesian_point():
    ax = axes()
    np.testing.assert_allclose(ax.polar_to_point(2, PI / 4), ax.c2p(2**0.5, 2**0.5))
    np.testing.assert_allclose(ax.pr2pt(2, PI / 4), ax.polar_to_point(2, PI / 4))
    np.testing.assert_allclose(ax.pr2pt(1, PI), ax.c2p(-1, 0), atol=1e-12)


def test_ph1_arrays_broadcast_as_c2p_does():
    ax = axes()
    np.testing.assert_allclose(
        ax.pr2pt(np.array([1.0, 2.0]), np.array([0.0, PI / 2])),
        ax.c2p(np.array([1.0, 0.0]), np.array([0.0, 2.0])),
        atol=1e-12,
    )


@pytest.mark.parametrize("theta", [-3.0, -PI / 2, 0.0, 0.5, PI / 2, 2.5, PI])
def test_ph2_point_to_polar_inverts_polar_to_point(theta):
    ax = axes()
    r, t = ax.pt2pr(ax.pr2pt(1.5, theta))
    assert r == pytest.approx(1.5, abs=1e-9)
    assert t == pytest.approx(theta, abs=1e-9)
    assert ax.point_to_polar(ax.c2p(0, -1)) == pytest.approx((1.0, -PI / 2))


def test_ph1_ph2_on_a_log_axis_and_a_twin():
    ax = mp.Axes(x_range=(0.1, 10), y_range=(0, 10, 1), x_scale="log")
    np.testing.assert_allclose(ax.pr2pt(2, 0), ax.c2p(2, 0), atol=1e-12)
    assert ax.pt2pr(ax.c2p(3, 4)) == pytest.approx((5.0, np.arctan2(4, 3)))
    right = ax.twinx(y_range=(0, 100, 10))
    np.testing.assert_allclose(right.pr2pt(5, 0), right.c2p(5, 0), atol=1e-9)


def test_ph3_plot_polar_graph_is_manims_parametric_curve():
    ax = axes()
    r_func = lambda t: 1 + 0.5 * np.cos(3 * t)  # noqa: E731
    graph = ax.plot_polar_graph(r_func, [0, TAU])
    assert isinstance(graph, mp.ParametricPlot)
    assert graph.underlying_function is r_func
    assert graph in ax.artists
    drawn = dense(pts(graph))
    for t in np.linspace(0, TAU, 50):
        target = ax.pr2pt(r_func(t), t)
        assert np.min(np.linalg.norm(drawn - target, axis=1)) < 1e-3


def test_ph3_follows_the_system_and_takes_the_cycle():
    ax = axes()
    first = ax.plot_polar_graph(lambda t: 1.0)
    second = ax.plot_polar_graph(lambda t: 1.5, color=RED)
    assert first.get_color() != second.get_color()
    ax.set_x_range((-2, 2))
    drawn = dense(pts(first))
    assert np.max(np.abs(drawn[:, 0] - ax.get_origin()[0])) == pytest.approx(
        2.0 * 1.0, abs=1e-3
    )


# --- PP -------------------------------------------------------------------------------


def unit(plane) -> float:
    return float(np.linalg.norm(plane.c2p(1, 0) - plane.c2p(0, 0)))


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"size": 6, "radius_max": 3},
        {"size": 6},
        {"radius_max": 2, "radius_step": 0.5},
    ],
)
def test_pp1_lengths_and_ranges_are_manims(kwargs):
    ours, theirs = mp.PolarPlane(**kwargs), PolarPlane(**kwargs)
    assert unit(ours) == pytest.approx(theirs.x_axis.get_unit_size())
    np.testing.assert_allclose(ours.x_range, theirs.x_range)
    np.testing.assert_allclose(ours.y_range, theirs.y_range)
    np.testing.assert_allclose(ours.c2p(1, 2), theirs.c2p(1, 2), atol=1e-9)


def test_pp1_radius_axes_as_manims():
    plane = mp.PolarPlane()
    assert len(plane.x_axis.ticks) == 0
    assert plane.x_axis.get_stroke_width() == 2


@pytest.mark.parametrize(
    "kwargs", [{"azimuth_units": "radians"}, {"azimuth_direction": "clockwise"}]
)
def test_pp1_bad_azimuth_keywords_raise(kwargs):
    with pytest.raises(ValueError):
        mp.PolarPlane(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "major", "faded"),
    [
        ({}, 24, 0),
        ({"faded_line_ratio": 2}, 24, 24),
        ({"azimuth_units": "degrees"}, 40, 0),
    ],
)
def test_pp2_line_counts_are_manims_without_the_zero_circle(kwargs, major, faded):
    ours, theirs = mp.PolarPlane(**kwargs), PolarPlane(**kwargs)
    assert len(ours.background_lines) == major == len(theirs.background_lines) - 1
    assert len(ours.faded_lines) == faded == len(theirs.faded_lines)


def test_pp2_spokes_and_circles_lie_where_manims_do():
    plane = mp.PolarPlane(azimuth_offset=PI / 7)
    centre = plane.get_origin()
    for k in range(20):
        spoke = plane.spokes.at(k * TAU / 20)
        np.testing.assert_allclose(pts(spoke)[0], centre, atol=1e-9)
        np.testing.assert_allclose(
            pts(spoke)[-1], centre + at(4, PI / 7 + k * TAU / 20), atol=1e-9
        )
    for r in (1, 2, 3, 4):
        assert radii(plane.circles.at(float(r)), centre) == pytest.approx(r, abs=5e-3)


def test_pp2_styles_are_manims():
    plane = mp.PolarPlane(faded_line_ratio=2)
    major, faded = plane.circles.at(1.0), plane.circles.at(0.5)
    assert major.get_stroke_color() == BLUE_D
    assert major.get_stroke_width() == 2
    assert faded.get_stroke_width() == 1
    assert faded.get_stroke_opacity() == 0.5


def test_pp3_grid_follows_a_changed_range_keeping_styles():
    plane = mp.PolarPlane()
    circle = plane.circles.at(1.0)
    circle.set_color(RED)
    plane.set_x_range((-2, 2, 1))
    plane.set_y_range((-2, 2, 1))
    assert plane.circles.at(1.0) is circle
    assert circle.get_color() == RED
    centre = plane.get_origin()
    assert radii(circle, centre) == pytest.approx(2.0, abs=5e-3)
    with pytest.raises(KeyError):
        plane.circles.at(3.0)
    spoke = plane.spokes.at(0.0)
    np.testing.assert_allclose(pts(spoke)[-1], centre + at(4, 0), atol=1e-9)


def test_pp3_grid_follows_an_animated_range():
    plane = mp.PolarPlane()
    circle = plane.circles.at(2.0)
    frames = probe(
        lambda s: (
            s.add(plane),
            s.play(plane.animate.set_x_range((-2, 2, 1)).set_y_range((-2, 2, 1))),
        ),
        lambda: float(radii(circle, plane.get_origin()).mean()),
    )
    assert frames[0] == pytest.approx(2.0, abs=1e-2)
    assert frames[-1] == pytest.approx(4.0, abs=1e-2)
    assert all(b >= a - 1e-9 for a, b in pairwise(frames))


def test_pp4_default_plane_maps_as_manims():
    ours, theirs = mp.PolarPlane(), PolarPlane()
    for r, t in [(2, PI / 4), (3, -2.0), (1, PI)]:
        np.testing.assert_allclose(ours.pr2pt(r, t), theirs.pr2pt(r, t), atol=1e-9)


def test_pp4_offset_and_direction_move_the_points_with_the_spokes():
    plane = mp.PolarPlane(azimuth_offset=PI / 2, azimuth_direction="CW")
    np.testing.assert_allclose(plane.pr2pt(1, 0), plane.c2p(0, 1), atol=1e-12)
    np.testing.assert_allclose(plane.pr2pt(1, PI / 2), plane.c2p(1, 0), atol=1e-12)
    np.testing.assert_allclose(
        plane.pr2pt(4, 3 * TAU / 20), pts(plane.spokes.at(3 * TAU / 20))[-1], atol=1e-9
    )
    r, t = plane.pt2pr(plane.pr2pt(2, 1.0))
    assert (r, t) == pytest.approx((2.0, 1.0))
    graph = plane.plot_polar_graph(lambda t: 1.0, [0, 0.01])
    np.testing.assert_allclose(pts(graph)[0], plane.c2p(0, 1), atol=1e-9)


def labels_of(plane, **kwargs):
    with tempconfig(RUN):
        return plane.get_coordinate_labels(**kwargs)


def test_pp5_azimuth_labels_ring_the_plane_centre():
    plane = mp.PolarPlane().shift(2 * RIGHT + DOWN)
    labels = labels_of(plane)
    centre = plane.get_origin()
    assert len(labels[1]) == 20
    for k, label in enumerate(labels[1]):
        offset = label.get_center() - centre
        assert same_angle(angle(offset), k * TAU / 20, atol=0.15)
        assert np.linalg.norm(offset) > 4


def test_pp5_radius_numbers_are_not_the_axis():
    plane = mp.PolarPlane()
    labels = labels_of(plane)
    assert labels[0] is not plane.x_axis
    assert len(labels[0]) == 4
    assert len(labels_of(plane, r_values=[1, 3])[0]) == 2


def test_pp5_add_coordinates_adds_once_and_the_labels_follow():
    plane = mp.PolarPlane(azimuth_units="degrees")
    with tempconfig(RUN):
        assert plane.add_coordinates() is plane
    label = plane.coordinate_labels[1][9]
    before = label.get_center()
    assert plane.x_axis not in plane.coordinate_labels.get_family()
    plane.shift(UP)
    np.testing.assert_allclose(label.get_center(), before + UP, atol=1e-9)
    assert same_angle(angle(label.get_center() - plane.get_origin()), PI / 2, atol=0.15)


def test_pp5_labels_follow_offset_and_direction():
    plane = mp.PolarPlane(azimuth_offset=PI / 2, azimuth_direction="CW")
    first = labels_of(plane)[1][1]
    expected = PI / 2 - TAU / 20
    assert same_angle(
        angle(first.get_center() - plane.get_origin()), expected, atol=0.15
    )


def test_pp6_radian_label_strings():
    with tempconfig(RUN):
        assert mp.PolarPlane().get_radian_label(0.375).tex_string == r"\tfrac{3\pi}{4}"
        loose = mp.PolarPlane(azimuth_compact_fraction=False)
        assert loose.get_radian_label(0.375).tex_string == r"\tfrac{3}{4}\pi"
        tau = mp.PolarPlane(azimuth_units="TAU radians")
        assert tau.get_radian_label(1).tex_string == r"\tau"
        assert mp.PolarPlane().get_radian_label(0).tex_string == "0"


# --- PX -------------------------------------------------------------------------------


def centre_of(ax) -> np.ndarray:
    return ax.c2p(ax.r_range[0], 0)


def test_px1_linear_map_by_hand():
    ax = mp.PolarAxes()  # r in (0, 4), diameter 8
    c = centre_of(ax)
    np.testing.assert_allclose(ax.c2p(0, 1.3), c, atol=1e-12)
    np.testing.assert_allclose(ax.c2p(4, 0), c + at(4, 0), atol=1e-9)
    np.testing.assert_allclose(ax.c2p(2, PI / 2), c + at(2, PI / 2), atol=1e-9)
    np.testing.assert_allclose(ax.pr2pt(2, PI / 2), ax.c2p(2, PI / 2))


def test_px1_size_offset_and_direction():
    ax = mp.PolarAxes(
        r_range=(0, 2), size=6, azimuth_offset=PI / 2, azimuth_direction="CW"
    )
    c = centre_of(ax)
    np.testing.assert_allclose(ax.c2p(1, 0), c + at(1.5, PI / 2), atol=1e-9)
    np.testing.assert_allclose(ax.c2p(2, PI / 2), c + at(3, 0), atol=1e-9)


def test_px1_log_radius():
    ax = mp.PolarAxes(r_range=(1, 100), r_scale="log")
    c = centre_of(ax)
    np.testing.assert_allclose(ax.c2p(1, 0.7), c, atol=1e-12)
    np.testing.assert_allclose(ax.c2p(10, 0), c + at(2, 0), atol=1e-9)
    np.testing.assert_allclose(ax.c2p(100, PI), c + at(4, PI), atol=1e-9)


@pytest.mark.parametrize("scale", ["linear", "log"])
def test_px1_inverse_returns_theta_in_a_full_turn(scale):
    ax = mp.PolarAxes(r_range=(1, 10), r_scale=scale).shift(RIGHT)
    for r, t in [(2, 0.0), (5, 3 * PI / 2), (9, 6.0), (3, PI)]:
        assert tuple(ax.p2c(ax.c2p(r, t))) == pytest.approx((r, t), abs=1e-9)
        assert tuple(ax.pt2pr(ax.pr2pt(r, t))) == pytest.approx((r, t), abs=1e-9)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"azimuth_units": "radians"}, "azimuth_units"),
        ({"azimuth_direction": "up"}, "azimuth_direction"),
        ({"r_range": (2, 1)}, "r_range"),
        ({"r_range": (0, 10), "r_scale": "log"}, "r_range"),
        ({"size": -1}, "size"),
    ],
)
def test_px2_validation(kwargs, match):
    with pytest.raises(ValueError, match=match):
        mp.PolarAxes(**kwargs)


def test_px3_cardioid_against_its_analytic_points():
    ax = mp.PolarAxes(r_range=(0, 2, 0.5))
    curve = ax.plot(lambda t: 1 + np.cos(t))
    drawn = dense(pts(curve), per_curve=32)
    c = centre_of(ax)
    for t in np.linspace(0, TAU, 400):
        target = c + at(2 * (1 + np.cos(t)), t)
        assert np.min(np.linalg.norm(drawn - target, axis=1)) < 1e-3


def test_px3_plot_polar_graph_is_plot_and_takes_the_cycle():
    ax = mp.PolarAxes(r_range=(0, 2))
    a = ax.plot(lambda t: 1.0)
    b = ax.plot_polar_graph(lambda t: 1.5, [0, PI])
    assert a.get_color() != b.get_color()
    assert a in ax.artists and b in ax.artists
    assert radii(b, centre_of(ax)) == pytest.approx(3.0, abs=1e-3)
    end = pts(b)[-1]
    assert same_angle(angle(end - centre_of(ax)), PI)


def test_px3_scatter_takes_r_and_theta():
    ax = mp.PolarAxes()
    dots = ax.scatter([1.0, 2.0], [0.0, PI / 2])
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(1, 0), atol=1e-9)
    np.testing.assert_allclose(dots[1].get_center(), ax.c2p(2, PI / 2), atol=1e-9)


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("get_area", (None,)),
        ("get_vertical_line", ((0, 0, 0),)),
        ("errorbar", ([1], [1])),
    ],
)
def test_px3_cartesian_helpers_refuse(method, args):
    ax = mp.PolarAxes()
    with pytest.raises(NotImplementedError, match="PolarAxes"):
        getattr(ax, method)(*args)


def test_px4_a_curve_beyond_the_rim_is_cut_at_the_rim():
    ax = mp.PolarAxes(r_range=(0, 2))  # rim at scene radius 4
    curve = ax.plot(lambda t: 1 + 2 * np.cos(t))
    distances = np.linalg.norm(dense(pts(curve))[:, :2] - centre_of(ax)[:2], axis=1)
    assert distances.max() == pytest.approx(4.0, abs=1e-6)
    loose = ax.plot(lambda t: 1 + 2 * np.cos(t), clip=False)
    assert np.linalg.norm(pts(loose)[:, :2] - centre_of(ax)[:2], axis=1).max() > 5.9


def test_px4_a_point_inside_r_min_is_invalid_on_a_log_scale():
    ax = mp.PolarAxes(r_range=(1, 100), r_scale="log")
    with pytest.warns(mp.ManimPlotsWarning):
        curve = ax.plot(lambda t: 0.5 + 0 * t)
    assert len(pts(curve)) == 0


def test_px5_the_rim_has_one_tick_and_number_per_division():
    ax = mp.PolarAxes()
    rim = ax.azimuth_axis
    assert len(rim.numbers) == 20
    assert len(rim.ticks) == 20
    rim.set_locator(mp.MultipleLocator(PI / 2))
    assert len(rim.numbers) == 4
    assert rim.numbers.at(0.0) is not None
    for value in (0.0, PI / 2, PI, 3 * PI / 2):
        offset = rim.numbers.at(value).get_center() - centre_of(ax)
        assert np.linalg.norm(offset) > 4
        assert same_angle(angle(offset), value, atol=0.2)


def test_px5_ticks_point_in_and_follow_the_formatter():
    ax = mp.PolarAxes(azimuth_units="degrees")
    rim = ax.azimuth_axis
    tick = rim.ticks.at(0.0)
    distances = np.linalg.norm(pts(tick)[:, :2] - centre_of(ax)[:2], axis=1)
    assert distances.max() == pytest.approx(4.0, abs=1e-6)
    assert distances.min() < 4.0 - 1e-3
    number = rim.numbers.at(PI)
    rim.set_formatter(mp.AngleFormatter("PI radians"))
    assert rim.numbers.at(PI) is number


def test_px6_radial_numbers_sit_beside_the_ray():
    ax = mp.PolarAxes()
    numbers = ax.r_axis.numbers
    assert len(numbers) == 4
    for r in (1.0, 2.0, 3.0, 4.0):
        offset = numbers.at(r).get_center() - centre_of(ax)
        phi = angle(offset)
        assert PI / 8 < phi < PI / 8 + 0.6
    assert len(ax.r_axis.ticks) == 0


def test_px6_grid_circles_and_spokes():
    ax = mp.PolarAxes(faded_line_ratio=2)
    c = centre_of(ax)
    for r in (1.0, 2.0, 3.0, 4.0, 0.5, 3.5):
        assert radii(ax.circles.at(r), c) == pytest.approx(r, abs=5e-3)
    assert ax.circles.at(0.5) in ax.faded_lines
    assert ax.circles.at(1.0) in ax.background_lines
    spoke = ax.spokes.at(PI / 10)
    np.testing.assert_allclose(pts(spoke)[0], c, atol=1e-9)
    np.testing.assert_allclose(pts(spoke)[-1], c + at(4, PI / 10), atol=1e-9)


def test_px6_log_grid():
    ax = mp.PolarAxes(r_range=(1, 100), r_scale="log")
    c = centre_of(ax)
    assert radii(ax.circles.at(10.0), c) == pytest.approx(2.0, abs=5e-3)
    assert ax.r_axis.numbers.at(10.0) is not None


def test_px7_set_r_range_moves_the_data_and_keeps_styles():
    ax = mp.PolarAxes()
    circle = ax.circles.at(2.0).set_color(RED)
    dots = ax.scatter([1.0], [PI / 2])
    rim_number = ax.azimuth_axis.numbers.at(PI / 2).get_center()
    ax.set_r_range((0, 2, 1))
    c = centre_of(ax)
    assert ax.circles.at(2.0) is circle and circle.get_color() == RED
    assert radii(circle, c) == pytest.approx(4.0, abs=5e-3)
    with pytest.raises(KeyError):
        ax.circles.at(3.0)
    np.testing.assert_allclose(dots[0].get_center(), c + at(2, PI / 2), atol=1e-9)
    np.testing.assert_allclose(
        ax.azimuth_axis.numbers.at(PI / 2).get_center(), rim_number
    )


def test_px7_animated_radial_range():
    ax = mp.PolarAxes()
    curve = ax.plot(lambda t: 1.0)
    circle = ax.circles.at(1.0)
    frames = probe(
        lambda s: (s.add(ax), s.play(ax.animate.set_r_range((0, 2, 1)))),
        lambda: (
            float(radii(curve, centre_of(ax)).mean()),
            float(radii(circle, centre_of(ax)).mean()),
        ),
    )
    assert frames[0] == pytest.approx((1.0, 1.0), abs=1e-2)
    assert frames[-1] == pytest.approx((2.0, 2.0), abs=1e-2)
    for curve_r, circle_r in frames:
        assert curve_r == pytest.approx(circle_r, abs=1e-2)


def test_px8_theme_and_cycle():
    ax = mp.PolarAxes(theme="origin")
    first = ax.plot(lambda t: 1.0)
    assert first.get_color().to_hex() == ManimColor(mp.CYCLES["origin"][0]).to_hex()


def test_px8_copy_add_legend_and_create():
    ax = mp.PolarAxes()
    curve = ax.plot(lambda t: 1.0, label="r = 1")
    twin = ax.copy()
    np.testing.assert_allclose(twin.c2p(1, 1), ax.c2p(1, 1))
    with tempconfig(RUN):
        assert ax.legend() is not None

    def construct(scene: Scene) -> None:
        scene.play(Create(ax))

    assert probe(construct, lambda: len(pts(curve)) > 0)[-1]


# --- ND -------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["Node", "AffineNode", "ScaleNode", "FunctionNode"])
def test_nd1_nodes_are_public(name):
    assert name in mp.__all__
    assert getattr(mp, name).__doc__


def test_nd1_function_node_round_trip():
    node = mp.FunctionNode(
        lambda x: np.column_stack(
            [x[:, 0] * np.cos(x[:, 1]), x[:, 0] * np.sin(x[:, 1])]
        ),
        lambda y: np.column_stack(
            [np.hypot(y[:, 0], y[:, 1]), np.arctan2(y[:, 1], y[:, 0])]
        ),
        dim=2,
    )
    x = np.array([[1.0, 0.5], [2.0, -1.0]])
    np.testing.assert_allclose(node.inverse(node.apply(x)), x)
    assert isinstance(node, mp.Node)
