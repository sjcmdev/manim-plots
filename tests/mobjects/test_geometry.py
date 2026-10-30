"""Task 26: planes, lines, drop lines, intersections and spherical and cylindrical
coordinates, rows PL, LN, DP, IX, CO of `docs/acceptance/26-geometry.md`.

The oracles: the box's corners and the plane's equation by brute force, Manim's
own `ThreeDAxes.get_line_from_axis_to_point` for DP-1, the coordinate formulas of ISO
80000-2 written out here.
"""

from __future__ import annotations

from itertools import product
from typing import Any

import numpy as np
import pytest
from manim import (
    BLUE,
    DEGREES,
    PI,
    RED,
    RIGHT,
    TAU,
    WHITE,
    Dot,
    Line,
    ManimColor,
    ThreeDAxes,
    ThreeDScene,
    ValueTracker,
    interpolate_color,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, dense, probe

RANGES = {"x": (-6.0, 6.0), "y": (-5.0, 5.0), "z": (-4.0, 4.0)}  # ThreeDAxes defaults


def anchors(mob: Any) -> np.ndarray:
    """The start of every cubic curve: a polygon's corners, a curve's samples."""
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def ends(mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    return np.array([points[0], points[-1]])


def same_set(a: np.ndarray, b: np.ndarray, atol: float = 1e-9) -> None:
    """Two point sets equal up to order."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert len(a) == len(b)
    for p in a:
        assert np.min(np.linalg.norm(b - p, axis=1)) < atol


def box_crossings(point: Any, normal: Any) -> np.ndarray:
    """The plane's crossings with the twelve edges of the default box."""
    p0, n = np.asarray(point, dtype=float), np.asarray(normal, dtype=float)
    lows = np.array([RANGES[k][0] for k in "xyz"])
    highs = np.array([RANGES[k][1] for k in "xyz"])
    found: list[np.ndarray] = []
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for a, b in product((0, 1), repeat=2):
            start = lows.copy()
            start[others[0]] = (lows, highs)[a][others[0]]
            start[others[1]] = (lows, highs)[b][others[1]]
            end = start.copy()
            end[axis] = highs[axis]
            da, db = n @ (start - p0), n @ (end - p0)
            if da * db <= 0 and da != db:
                q = start + da / (da - db) * (end - start)
                if not any(np.allclose(q, f) for f in found):
                    found.append(q)
    return np.array(found)


def mix(a: Any, b: Any, t: float) -> str:
    return interpolate_color(ManimColor(a), ManimColor(b), t).to_hex()


def fill(mob: Any) -> str:
    return ManimColor(mob.get_fill_color()).to_hex()


# --- PL -------------------------------------------------------------------------------


def test_pl1_an_axis_aligned_plane_is_the_box_section():
    ax = mp.ThreeDAxes()
    wall = ax.plane(x=1)
    assert isinstance(wall, mp.PlanePlot)
    corners = data(ax, anchors(wall))
    same_set(corners, [(1, -5, -4), (1, 5, -4), (1, 5, 4), (1, -5, 4)])
    np.testing.assert_allclose(wall.points[-1], wall.points[0], atol=1e-9)


def test_pl1_flat_on_a_log_axis():
    ax = mp.ThreeDAxes(z_range=(1, 100), z_scale="log")
    floor = ax.plane(z=10)
    corners = data(ax, anchors(floor))
    same_set(corners, [(-6, -5, 10), (6, -5, 10), (6, 5, 10), (-6, 5, 10)])


@pytest.mark.parametrize(
    ("point", "normal", "count"),
    [((0, 0, 0), (1, 1, 1), 6), ((5, 4, 3), (1, 1, 1), 3), ((0, 0, 1), (0, 1, 2), 4)],
)
def test_pl2_an_oblique_plane_is_cut_to_the_box(point, normal, count):
    ax = mp.ThreeDAxes()
    cut = ax.plane(point, normal)
    corners = data(ax, anchors(cut))
    assert len(corners) == count
    same_set(corners, box_crossings(point, normal))
    n = np.asarray(normal, dtype=float)
    np.testing.assert_allclose((corners - point) @ n, 0, atol=1e-9)
    # ordered around the normal: every turn of the polygon has the same sense
    edges = np.roll(corners, -1, axis=0) - corners
    turns = np.cross(edges, np.roll(edges, -1, axis=0)) @ n
    assert np.all(turns > 0) or np.all(turns < 0)


def test_pl3_exactly_one_form():
    ax = mp.ThreeDAxes()
    for call in (
        lambda: ax.plane(),
        lambda: ax.plane(x=1, y=1),
        lambda: ax.plane((0, 0, 0), (1, 0, 0), x=1),
    ):
        with pytest.raises(ValueError, match="plane"):
            call()
    with pytest.raises(ValueError, match="normal"):
        ax.plane((0, 0, 0))
    with pytest.raises(ValueError, match="point"):
        ax.plane(normal=(0, 0, 1))
    with pytest.raises(ValueError, match="normal"):
        ax.plane((0, 0, 0), (0, 0, 0))
    log = mp.ThreeDAxes(z_range=(1, 100), z_scale="log")
    with pytest.raises(ValueError, match="normal"):
        log.plane((1, 1, 10), (1, 1, 1))


def test_pl4_a_plane_that_misses_the_box():
    ax = mp.ThreeDAxes()
    with pytest.raises(ValueError, match="x"):
        ax.plane(x=9)
    with pytest.raises(ValueError, match="point"):
        ax.plane((0, 0, 100), (0, 0, 1))
    t = ValueTracker(0)
    wall = ax.plane(x=t)

    def construct(scene: Any) -> None:
        scene.add(ax)
        scene.play(t.animate.set_value(9))
        scene.play(t.animate.set_value(0))

    shown = probe(construct, wall.has_points)
    assert shown[0] and shown[-1]
    assert not all(shown)


def test_pl5_a_plane_follows_its_tracker():
    ax = mp.ThreeDAxes()
    t = ValueTracker(-3)
    wall = ax.plane(x=t)
    gaps = probe(
        lambda s: s.play(t.animate.set_value(3)),
        lambda: float(np.max(np.abs(data(ax, anchors(wall))[:, 0] - t.get_value()))),
    )
    assert max(gaps) < 1e-9


def test_pl5_a_plane_follows_ranges_and_moves():
    ax = mp.ThreeDAxes()
    wall = ax.plane(x=1)
    ax.set_z_range((-2, 2, 1))
    same_set(data(ax, anchors(wall)), [(1, -5, -2), (1, 5, -2), (1, 5, 2), (1, -5, 2)])
    ax.shift(RIGHT).rotate(PI / 5, axis=RIGHT)
    same_set(
        anchors(wall),
        [ax.c2p(*p) for p in [(1, -5, -2), (1, 5, -2), (1, 5, 2), (1, -5, 2)]],
        atol=1e-6,
    )


def test_pl6_style_and_customisation():
    ax = mp.ThreeDAxes()
    a, b = ax.plane(x=1), ax.plane(y=1, label="wall")
    assert fill(a) != fill(b)
    assert a.get_fill_opacity() == pytest.approx(0.25)
    assert a.get_stroke_width() == pytest.approx(1)
    assert ManimColor(a.get_stroke_color()).to_hex() == fill(a)
    assert a in ax.artists and b in ax.artists
    a.set_fill(RED, opacity=0.6)
    ax.set_z_range((-2, 2, 1))
    assert fill(a) == ManimColor(RED).to_hex()
    assert a.get_fill_opacity() == pytest.approx(0.6)


# --- LN -------------------------------------------------------------------------------


def test_ln1_axline_through_two_points_spans_the_box():
    ax = mp.ThreeDAxes()
    line = ax.axline((0, 0, 0), (1, 1, 1))
    assert isinstance(line, mp.AxLinePlot)
    drawn = data(ax, anchors(line))
    np.testing.assert_allclose(drawn - drawn[:, :1], 0, atol=1e-9)  # x = y = z
    same_set(data(ax, ends(line)), [(-4, -4, -4), (4, 4, 4)])


def test_ln1_axline_by_direction():
    ax = mp.ThreeDAxes()
    line = ax.axline((0, 1, 2), direction=(1, 0, 0))
    same_set(data(ax, ends(line)), [(-6, 1, 2), (6, 1, 2)])


def test_ln2_one_second_input():
    ax = mp.ThreeDAxes()
    with pytest.raises(ValueError, match="direction"):
        ax.axline((0, 0, 0))
    with pytest.raises(ValueError, match="direction"):
        ax.axline((0, 0, 0), (1, 1, 1), direction=(1, 0, 0))
    with pytest.raises(ValueError, match="xyz2"):
        ax.axline((1, 1, 1), (1, 1, 1))
    with pytest.raises(ValueError, match="direction"):
        ax.axline((1, 1, 1), direction=(0, 0, 0))


def test_ln3_a_segment_is_clipped_to_the_box():
    ax = mp.ThreeDAxes()
    s = ax.segment((0, 0, 0), (0, 0, 10))
    same_set(data(ax, ends(s)), [(0, 0, 0), (0, 0, 4)])


def test_ln3_a_segment_is_straight_in_data_on_a_log_axis():
    ax = mp.ThreeDAxes(z_range=(1, 100), z_scale="log")
    a, b = np.array([0.0, 0.0, 1.0]), np.array([2.0, 2.0, 100.0])
    s = ax.segment(a, b)
    drawn = data(ax, anchors(s))
    t = (drawn - a) @ (b - a) / ((b - a) @ (b - a))
    np.testing.assert_allclose(a + t[:, None] * (b - a), drawn, atol=1e-6)
    scene = anchors(s)
    chord = scene[-1] - scene[0]
    off = np.linalg.norm(np.cross(scene - scene[0], chord), axis=1)
    assert off.max() / np.linalg.norm(chord) > 0.01  # curved on screen


def test_ln4_lines_parallel_to_the_axes():
    ax = mp.ThreeDAxes()
    x = ax.xline(1, 2)
    same_set(data(ax, ends(x)), [(-6, 1, 2), (6, 1, 2)])
    part = ax.xline(1, 2, xmin=0.25, xmax=0.75)
    same_set(data(ax, ends(part)), [(-3, 1, 2), (3, 1, 2)])
    same_set(data(ax, ends(ax.yline(1, 2))), [(1, -5, 2), (1, 5, 2)])
    same_set(data(ax, ends(ax.zline(1, 2))), [(1, 2, -4), (1, 2, 4)])
    assert x.get_stroke_width() == pytest.approx(2)
    assert ManimColor(x.get_color()).to_hex() == ManimColor(WHITE).to_hex()


def test_ln5_lines_take_the_cycle_and_are_bound():
    ax = mp.ThreeDAxes()
    a, b = ax.axline((0, 0, 0), (1, 1, 1)), ax.segment((0, 0, 0), (1, 0, 0))
    assert a.get_color() != b.get_color()
    t = ValueTracker(1)
    s = ax.segment((0, 0, 0), (t, 0, 0))
    gaps = probe(
        lambda scene: scene.play(t.animate.set_value(3)),
        lambda: float(abs(ax.p2c(ends(s)[1])[0] - t.get_value())),
    )
    assert max(gaps) < 1e-9


def test_ln5_a_mobject_end_is_read_every_frame():
    ax = mp.ThreeDAxes()
    dot = Dot(ax.c2p(1, 1, 1))
    s = ax.segment((0, 0, 0), dot)

    def construct(scene: Any) -> None:
        scene.add(ax, dot)
        scene.play(dot.animate.move_to(ax.c2p(2, 2, 2)))

    gaps = probe(
        construct, lambda: float(np.linalg.norm(ends(s)[1] - dot.get_center()))
    )
    assert max(gaps) < 1e-9


# --- DP -------------------------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 1, 2])
def test_dp1_a_line_from_an_axis_matches_manims(index):
    ours, theirs = mp.ThreeDAxes(), ThreeDAxes()
    a = ours.get_line_from_axis_to_point(index, ours.c2p(1, 2, 3), line_func=Line)
    b = theirs.get_line_from_axis_to_point(index, theirs.c2p(1, 2, 3), line_func=Line)
    np.testing.assert_allclose(ends(a), [b.get_start(), b.get_end()], atol=1e-9)
    assert a.get_stroke_width() == 2


def test_dp1_three_axes_only():
    ax = mp.ThreeDAxes()
    with pytest.raises(ValueError, match="index"):
        ax.get_line_from_axis_to_point(3, ax.c2p(1, 1, 1))


def test_dp2_drop_lines_in_the_origin_frame():
    ax = mp.ThreeDAxes()
    g = ax.get_lines_to_point(ax.c2p(1, 2, 3), line_func=Line)
    assert isinstance(g, mp.HelperGroup)
    assert list(g) == [g.x_line, g.y_line, g.z_line]
    np.testing.assert_allclose(
        data(ax, ends(g.x_line)), [(0, 2, 0), (1, 2, 0)], atol=1e-9
    )
    np.testing.assert_allclose(
        data(ax, ends(g.y_line)), [(1, 0, 0), (1, 2, 0)], atol=1e-9
    )
    np.testing.assert_allclose(
        data(ax, ends(g.z_line)), [(1, 2, 0), (1, 2, 3)], atol=1e-9
    )


def test_dp2_drop_lines_go_to_the_far_panes_and_follow_the_camera():
    ax = mp.ThreeDAxes(frame="box")
    g = ax.get_lines_to_point(ax.c2p(1, 2, 3), line_func=Line)
    seen: list[np.ndarray] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
            self.add(ax, g)
            self.wait(1 / 3)
            seen.append(np.array([data(ax, ends(m)) for m in g]))
            self.move_camera(theta=135 * DEGREES, run_time=1 / 3)
            self.wait(1 / 3)
            seen.append(np.array([data(ax, ends(m)) for m in g]))

    with tempconfig(RUN):
        Shot().render()
    # theta = -45: far x side -6, far y side 5, floor -4
    np.testing.assert_allclose(
        seen[0],
        [[(-6, 2, -4), (1, 2, -4)], [(1, 5, -4), (1, 2, -4)], [(1, 2, -4), (1, 2, 3)]],
        atol=1e-9,
    )
    # theta = 135: far x side 6, far y side -5
    np.testing.assert_allclose(
        seen[1],
        [[(6, 2, -4), (1, 2, -4)], [(1, -5, -4), (1, 2, -4)], [(1, 2, -4), (1, 2, 3)]],
        atol=1e-9,
    )


# --- IX -------------------------------------------------------------------------------


def test_ix1_two_axis_planes_meet_in_a_line():
    ax = mp.ThreeDAxes()
    line = ax.intersection(ax.plane(x=1), ax.plane(y=2))
    assert isinstance(line, mp.AxLinePlot)
    same_set(data(ax, ends(line)), [(1, 2, -4), (1, 2, 4)])


def test_ix1_two_oblique_planes():
    ax = mp.ThreeDAxes()
    line = ax.intersection(
        ax.plane((0, 0, 0), (1, 0, 0)), ax.plane((0, 0, 0), (0, 1, 1))
    )
    drawn = data(ax, anchors(line))
    np.testing.assert_allclose(drawn[:, 0], 0, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 1], -drawn[:, 2], atol=1e-9)
    same_set(data(ax, ends(line)), [(0, -4, 4), (0, 4, -4)])


def test_ix2_a_line_meets_a_plane_in_a_point():
    ax = mp.ThreeDAxes()
    line, floor = ax.axline((0, 0, 0), direction=(1, 1, 1)), ax.plane(z=2)
    for a, b in ((line, floor), (floor, line)):
        point = ax.intersection(a, b)
        assert isinstance(point, mp.ScatterPlot)
        np.testing.assert_allclose(point[0].get_center(), ax.c2p(2, 2, 2), atol=1e-9)
        assert point[0].get_fill_opacity() > 0


def test_ix2_a_crossing_outside_the_segment_is_hidden():
    ax = mp.ThreeDAxes()
    point = ax.intersection(ax.segment((0, 0, 0), (1, 1, 1)), ax.plane(z=2))
    assert point[0].get_fill_opacity() == 0


def test_ix3_a_plane_cuts_a_surface():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(lambda u, v: u * v, (-2, 2), (-2, 2), resolution=16)
    cut = ax.intersection(ax.plane(x=0.9), surface)  # off the grid lines
    assert isinstance(cut, mp.ContourPlot)
    drawn = data(ax, anchors(cut.at(0.0)))
    assert len(drawn) > 4
    np.testing.assert_allclose(drawn[:, 0], 0.9, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 2], 0.9 * drawn[:, 1], atol=1e-9)


def test_ix4_other_pairs_and_no_meeting_are_refused():
    ax = mp.ThreeDAxes()
    line = ax.axline((0, 0, 0), (1, 1, 1))
    surface = ax.plot_surface(lambda u, v: u * v, (-1, 1), (-1, 1), resolution=4)
    with pytest.raises(TypeError, match="AxLinePlot"):
        ax.intersection(line, ax.axline((0, 0, 0), (1, 0, 0)))
    with pytest.raises(TypeError, match="SurfacePlot"):
        ax.intersection(surface, surface)
    with pytest.raises(TypeError, match="int"):
        ax.intersection(ax.plane(x=1), 3)
    with pytest.raises(ValueError, match="intersection"):
        ax.intersection(ax.plane(x=1), ax.plane(x=2))
    with pytest.raises(ValueError, match="intersection"):
        ax.intersection(ax.axline((0, 0, 1), direction=(1, 0, 0)), ax.plane(z=2))


def test_ix5_an_intersection_follows_its_inputs():
    ax = mp.ThreeDAxes()
    t = ValueTracker(0)
    point = ax.intersection(ax.axline((0, 0, 0), direction=(1, 1, 1)), ax.plane(z=t))
    gaps = probe(
        lambda s: s.play(t.animate.set_value(3)),
        lambda: float(
            np.linalg.norm(point[0].get_center() - ax.c2p(*[t.get_value()] * 3))
        ),
    )
    assert max(gaps) < 1e-9


# --- CO -------------------------------------------------------------------------------


def test_co1_spherical_to_point_is_iso():
    ax = mp.ThreeDAxes()
    np.testing.assert_allclose(ax.sp2pt(1, 0, 0), ax.c2p(0, 0, 1), atol=1e-12)
    np.testing.assert_allclose(
        ax.spherical_to_point(2, PI / 2, PI / 2), ax.c2p(0, 2, 0), atol=1e-12
    )
    r, theta, phi = 3, 0.7, -2.1
    np.testing.assert_allclose(
        ax.sp2pt(r, theta, phi),
        ax.c2p(
            r * np.sin(theta) * np.cos(phi),
            r * np.sin(theta) * np.sin(phi),
            r * np.cos(theta),
        ),
        atol=1e-12,
    )
    many = ax.sp2pt(np.array([1.0, 2.0]), np.array([PI / 2] * 2), np.array([0.0, PI]))
    assert np.shape(many) == (3, 2)
    np.testing.assert_allclose(many[:, 1], ax.c2p(-2, 0, 0), atol=1e-12)
    assert type(ax).sp2pt is type(ax).spherical_to_point


def test_co2_point_to_spherical_inverts_it():
    ax = mp.ThreeDAxes()
    for r, theta, phi in [(1, 0.3, 0.2), (2.5, 2.9, -3.0), (3, PI / 2, PI)]:
        np.testing.assert_allclose(
            ax.pt2sp(ax.sp2pt(r, theta, phi)), (r, theta, phi), atol=1e-9
        )
    np.testing.assert_allclose(
        ax.point_to_spherical(ax.c2p(0, 0, 0)), (0, 0, 0), atol=1e-12
    )
    many = ax.pt2sp(np.array([ax.c2p(0, 0, 2), ax.c2p(0, -1, 0)]))
    np.testing.assert_allclose(many, [(2, 0, 0), (1, PI / 2, -PI / 2)], atol=1e-9)
    assert type(ax).pt2sp is type(ax).point_to_spherical


def test_co3_cylindrical():
    ax = mp.ThreeDAxes()
    np.testing.assert_allclose(ax.cy2pt(2, PI / 2, 3), ax.c2p(0, 2, 3), atol=1e-12)
    np.testing.assert_allclose(
        ax.pt2cy(ax.cylindrical_to_point(1.5, -2.0, -1)), (1.5, -2.0, -1), atol=1e-9
    )
    np.testing.assert_allclose(
        ax.point_to_cylindrical(ax.c2p(0, 2, 1)), (2, PI / 2, 1), atol=1e-12
    )
    assert type(ax).cy2pt is type(ax).cylindrical_to_point
    assert type(ax).pt2cy is type(ax).point_to_cylindrical


def test_co4_only_three_d_systems():
    ax = mp.Axes()
    for name in ("sp2pt", "pt2sp", "cy2pt", "pt2cy", "spherical_to_point"):
        assert not hasattr(ax, name)


def test_co5_a_sphere_in_spherical_coordinates():
    ax = mp.ThreeDAxes()
    sphere = ax.plot_surface(
        lambda th, ph: 2 + 0 * th, coords="spherical", resolution=8
    )
    corners = data(ax, np.concatenate([anchors(face) for face in sphere.faces]))
    np.testing.assert_allclose(np.linalg.norm(corners, axis=1), 2, atol=1e-9)
    assert corners[:, 2].max() == pytest.approx(2)
    assert corners[:, 2].min() == pytest.approx(-2)
    assert np.unique(np.round(np.arctan2(corners[:, 1], corners[:, 0]), 9)).size >= 8


def test_co5_colour_by_the_cartesian_z():
    ax = mp.ThreeDAxes()
    sphere = ax.plot_surface(
        lambda th, ph: 2 + 0 * th,
        coords="spherical",
        resolution=8,
        colorscale=[BLUE, RED],
        vmin=-2,
        vmax=2,
    )
    theta = PI / 16  # the first row's centre
    expected = mix(BLUE, RED, (2 * np.cos(theta) + 2) / 4)
    np.testing.assert_allclose(
        ManimColor(fill(sphere.faces.at((0, 0)))).to_rgb(),
        ManimColor(expected).to_rgb(),
        atol=1.5 / 255,
    )


def test_co5_a_disc_in_cylindrical_coordinates():
    ax = mp.ThreeDAxes(z_range=(0, 30, 5))
    bowl = ax.plot_surface(lambda rho, ph: rho**2, coords="cylindrical", resolution=8)
    corners = data(ax, np.concatenate([anchors(face) for face in bowl.faces]))
    np.testing.assert_allclose(corners[:, 2], corners[:, 0] ** 2 + corners[:, 1] ** 2)
    assert np.hypot(corners[:, 0], corners[:, 1]).max() == pytest.approx(5)
    off = mp.ThreeDAxes(x_range=(1, 5, 1))
    with pytest.raises(ValueError, match="u_range"):
        off.plot_surface(lambda rho, ph: rho, coords="cylindrical")


def test_co6_parametric_forms():
    ax = mp.ThreeDAxes()
    ball = ax.plot_parametric_surface(
        lambda u, v: (1 + 0 * u, u, v),
        (0, PI),
        (0, TAU),
        coords="spherical",
        resolution=6,
    )
    corners = data(ax, np.concatenate([anchors(face) for face in ball.faces]))
    np.testing.assert_allclose(np.linalg.norm(corners, axis=1), 1, atol=1e-9)
    ring = ax.plot_parametric_curve(
        lambda t: (1, PI / 2, t), t_range=(0, TAU), coords="spherical"
    )
    drawn = data(ax, anchors(ring))
    np.testing.assert_allclose(np.hypot(drawn[:, 0], drawn[:, 1]), 1, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 2], 0, atol=1e-9)
    helix = ax.plot_parametric_curve(
        lambda t: (1, t, t), t_range=(-3, 3), coords="cylindrical"
    )
    points = dense(np.asarray(helix.points), per_curve=32)
    for t in np.linspace(-3, 3, 50):
        target = ax.c2p(np.cos(t), np.sin(t), t)
        assert np.min(np.linalg.norm(points - target, axis=1)) < 1e-3


def test_co7_unknown_coordinates():
    ax = mp.ThreeDAxes()
    with pytest.raises(ValueError, match="coords"):
        ax.plot_surface(lambda u, v: u, coords="polar")
    with pytest.raises(ValueError, match="coords"):
        ax.plot_parametric_curve(lambda t: (t, t, t), t_range=(0, 1), coords="polar")
