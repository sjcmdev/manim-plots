"""Task 25: surfaces, colour by value, clipping, wireframes and contours, rows SF, CS,
SK, WF, CT of `docs/acceptance/25-surfaces.md`.

The oracles: Manim's own `ThreeDAxes.plot_surface` where the library keeps its points,
the surface's equation everywhere else, and `interpolate_color` by hand for colours.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import numpy as np
import pytest
from manim import (
    BLUE,
    BLUE_D,
    BLUE_E,
    DEGREES,
    GREEN,
    LIGHT_GREY,
    RED,
    RIGHT,
    WHITE,
    YELLOW,
    ManimColor,
    ThreeDAxes,
    ThreeDScene,
    interpolate_color,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, dense, probe

SQUARE: dict[str, Any] = {"u_range": (0, 2), "v_range": (0, 2), "resolution": 2}


def corners(face: Any) -> np.ndarray:
    """The start of every cubic curve of a face: its corners, in order."""
    return np.asarray(face.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def fill(mob: Any) -> str:
    return ManimColor(mob.get_fill_color()).to_hex()


def stroke(mob: Any) -> str:
    return ManimColor(mob.get_stroke_color()).to_hex()


def mix(a: Any, b: Any, t: float) -> str:
    return interpolate_color(ManimColor(a), ManimColor(b), t).to_hex()


def close(hex_a: str, hex_b: str, tol: float = 3 / 255) -> bool:
    a, b = ManimColor(hex_a).to_rgb(), ManimColor(hex_b).to_rgb()
    return bool(np.max(np.abs(np.asarray(a) - np.asarray(b))) <= tol)


# --- SF -------------------------------------------------------------------------------


def test_sf1_faces_equal_manims_point_for_point():
    def f(u, v):
        return 0.5 * u * v

    ours = mp.ThreeDAxes().plot_surface(f, (-2, 2), (-2, 2), resolution=4)
    # Manim types the function as Callable[[float], float]; it takes (u, v)
    manims = ThreeDAxes().plot_surface
    theirs = manims(f, (-2, 2), (-2, 2), resolution=4)  # type: ignore[arg-type]
    assert len(ours.faces) == 16
    for i in range(4):
        for j in range(4):
            np.testing.assert_allclose(
                ours.faces.at((i, j)).points,
                theirs.submobjects[4 * i + j].points,
                rtol=0,
                atol=1e-9,
            )


def test_sf1_a_resolution_pair():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: 0 * u, (0, 1), (0, 1), resolution=(3, 2)
    )
    assert len(s.faces) == 6
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(lambda u, v: 0 * u, (0, 3), (0, 2), resolution=(3, 2))
    np.testing.assert_allclose(
        corners(s.faces.at((2, 1))),
        [ax.c2p(2, 1, 0), ax.c2p(3, 1, 0), ax.c2p(3, 2, 0), ax.c2p(2, 2, 0)],
        atol=1e-9,
    )


def test_sf2_manims_defaults():
    s = mp.ThreeDAxes().plot_surface(lambda u, v: 0 * u, (0, 1), (0, 1))
    assert len(s.faces) == 32 * 32
    first, second = s.faces.at((0, 0)), s.faces.at((0, 1))
    assert fill(first) == ManimColor(BLUE_D).to_hex()
    assert fill(second) == ManimColor(BLUE_E).to_hex()
    assert fill(s.faces.at((1, 1))) == ManimColor(BLUE_D).to_hex()
    assert first.get_fill_opacity() == pytest.approx(1)
    assert stroke(first) == ManimColor(LIGHT_GREY).to_hex()
    assert first.get_stroke_width() == pytest.approx(0.5)
    assert s.color_mapping is None


def test_sf2_surface_keywords_keep_their_meaning():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: 0 * u,
        (0, 1),
        (0, 1),
        resolution=2,
        checkerboard_colors=False,
        fill_color=RED,
        fill_opacity=0.5,
        stroke_width=2,
    )
    face = s.faces.at((0, 1))
    assert fill(face) == ManimColor(RED).to_hex()
    assert face.get_fill_opacity() == pytest.approx(0.5)
    assert face.get_stroke_width() == pytest.approx(2)


def test_sf2_default_ranges_are_the_axes_and_follow_them():
    ax = mp.ThreeDAxes(x_range=(-2, 2, 1), y_range=(-1, 1, 1))
    s = ax.plot_surface(lambda u, v: 0 * u, resolution=2)
    np.testing.assert_allclose(corners(s.faces.at((0, 0)))[0], ax.c2p(-2, -1, 0))
    np.testing.assert_allclose(corners(s.faces.at((1, 1)))[2], ax.c2p(2, 1, 0))
    ax.set_x_range((-1, 1, 1))
    np.testing.assert_allclose(
        corners(s.faces.at((0, 0)))[0], ax.c2p(-1, -1, 0), atol=1e-9
    )


def test_sf2_an_explicit_range_stays():
    ax = mp.ThreeDAxes(x_range=(-2, 2, 1), y_range=(-1, 1, 1))
    s = ax.plot_surface(lambda u, v: 0 * u, (-2, 2), (-1, 1), resolution=2, clip=False)
    ax.set_x_range((-1, 1, 1))
    np.testing.assert_allclose(
        corners(s.faces.at((0, 0)))[0], ax.c2p(-2, -1, 0), atol=1e-9
    )


def sphere(u, v):
    return np.array([np.cos(u) * np.cos(v), np.cos(u) * np.sin(v), np.sin(u)])


def test_sf3_a_parametric_surface():
    ax = mp.ThreeDAxes()
    s = ax.plot_parametric_surface(sphere, (-np.pi / 2, np.pi / 2), (0, 2 * np.pi))
    anchors = np.concatenate([corners(f) for f in s.faces if f.has_points()])
    np.testing.assert_allclose(
        np.linalg.norm(data(ax, anchors), axis=1), 1, rtol=0, atol=1e-9
    )


@pytest.mark.parametrize("missing", ["u_range", "v_range"])
def test_sf3_both_ranges_are_required(missing):
    ranges: dict[str, Any] = {"u_range": (0, 1), "v_range": (0, 1)}
    ranges[missing] = None
    with pytest.raises(ValueError, match=missing):
        mp.ThreeDAxes().plot_parametric_surface(sphere, **ranges)


@pytest.mark.parametrize(
    ("axis", "along", "across"),
    [("z", 2, (0, 1)), ("x", 0, (1, 2)), ("y", 1, (2, 0))],
)
def test_sf4_a_surface_of_revolution(axis, along, across):
    ax = mp.ThreeDAxes()
    s = ax.plot_surface_of_revolution(
        lambda t: 1 + 0.5 * t, (0, 2), axis=axis, resolution=8
    )
    points = data(ax, np.concatenate([corners(f) for f in s.faces]))
    radius = np.hypot(points[:, across[0]], points[:, across[1]])
    np.testing.assert_allclose(radius, 1 + 0.5 * points[:, along], atol=1e-9)
    assert points[:, along].min() == pytest.approx(0, abs=1e-9)
    assert points[:, along].max() == pytest.approx(2, abs=1e-9)


def test_sf4_the_angle_runs_from_x_about_z():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface_of_revolution(lambda t: 1 + 0 * t, (0, 1), resolution=4)
    np.testing.assert_allclose(corners(s.faces.at((0, 0)))[0], ax.c2p(1, 0, 0))
    np.testing.assert_allclose(
        corners(s.faces.at((0, 1)))[0], ax.c2p(0, 1, 0), atol=1e-9
    )


def test_sf4_t_range_defaults_to_the_axis():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface_of_revolution(lambda t: 2 + 0 * t, resolution=4)
    z = data(ax, np.concatenate([corners(f) for f in s.faces]))[:, 2]
    assert z.min() == pytest.approx(-4)
    assert z.max() == pytest.approx(4)


def test_sf5_a_surface_from_grids():
    ax = mp.ThreeDAxes()
    X, Y = np.meshgrid(np.linspace(0, 2, 3), np.linspace(0, 1, 4))
    Z = X * Y
    s = ax.surface(X, Y, Z)
    assert len(s.faces) == 6
    expected = [
        ax.c2p(X[i, j], Y[i, j], Z[i, j]) for i, j in [(1, 0), (2, 0), (2, 1), (1, 1)]
    ]
    np.testing.assert_allclose(corners(s.faces.at((1, 0))), expected, atol=1e-9)


def test_sf5_grids_of_different_shapes_are_refused():
    with pytest.raises(ValueError, match="Z"):
        mp.ThreeDAxes().surface(np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 2)))


def test_sf6_trisurf_by_delaunay():
    ax = mp.ThreeDAxes()
    x = np.array([0, 1, 1, 0, 0.5])
    y = np.array([0, 0, 1, 1, 0.5])
    s = ax.plot_trisurf(x, y, np.zeros(5))
    assert len(s.faces) == 4
    for face in s.faces:
        assert len(corners(face)) == 3
        assert fill(face) == ManimColor(BLUE_D).to_hex()


def test_sf6_trisurf_with_given_triangles():
    ax = mp.ThreeDAxes()
    x, y, z = np.array([0, 1, 1, 0]), np.array([0, 0, 1, 1]), np.array([0, 1, 2, 3])
    s = ax.plot_trisurf(x, y, z, triangles=np.array([[0, 1, 2], [0, 2, 3]]))
    assert len(s.faces) == 2
    np.testing.assert_allclose(
        corners(s.faces.at(1)),
        [ax.c2p(0, 0, 0), ax.c2p(1, 1, 2), ax.c2p(0, 1, 3)],
        atol=1e-9,
    )


def test_sf7_non_finite_corners_make_holes():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: np.where(u + v > 1, np.nan, 0 * u), (0, 1), (0, 1), resolution=4
    )
    assert len(s.faces) == 16
    for i in range(4):
        for j in range(4):
            assert s.faces.at((i, j)).has_points() == (i + j <= 2)


def test_sf8_surfaces_need_three_dimensions():
    ax = mp.Axes()
    with pytest.raises(NotImplementedError, match="ThreeDAxes"):
        ax.plot_surface(lambda u, v: u * v, (0, 1), (0, 1))
    with pytest.raises(NotImplementedError, match="ThreeDAxes"):
        ax.plot_trisurf([0, 1, 0], [0, 0, 1], [0, 0, 0])


# --- CS -------------------------------------------------------------------------------


def plane(u, v):
    return u + v


def test_cs2_a_face_takes_its_centres_value():
    s = mp.ThreeDAxes().plot_surface(plane, colorscale=[BLUE, RED], **SQUARE)
    # z range (-4, 4): the centre of face (0, 0) is at 1, of face (1, 1) at 3
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 5 / 8), 1 / 255)
    assert close(fill(s.faces.at((1, 1))), mix(BLUE, RED, 7 / 8), 1 / 255)
    assert close(stroke(s.faces.at((0, 0))), mix(BLUE, RED, 5 / 8), 1 / 255)


def test_cs1_three_colours_are_evenly_spaced():
    s = mp.ThreeDAxes().plot_surface(plane, colorscale=[BLUE, GREEN, RED], **SQUARE)
    assert close(fill(s.faces.at((0, 0))), mix(GREEN, RED, 0.25), 1 / 255)


def test_cs1_pivots():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: 0 * u + 0.25,
        colorscale=[(RED, -0.5), (YELLOW, 0), (GREEN, 0.5)],
        **SQUARE,
    )
    assert close(fill(s.faces.at((0, 0))), mix(YELLOW, GREEN, 0.5), 1 / 255)
    assert s.color_mapping is not None
    assert s.color_mapping.vmin == pytest.approx(-0.5)
    assert s.color_mapping.vmax == pytest.approx(0.5)


def test_cs3_vmin_with_pivots_is_refused():
    with pytest.raises(ValueError, match="vmin"):
        mp.ThreeDAxes().plot_surface(
            plane, colorscale=[(RED, -0.5), (GREEN, 0.5)], vmin=0, **SQUARE
        )


def test_cs1_a_named_colormap():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: 0 * u + (-4 + 8 * 0.3), colorscale="viridis", **SQUARE
    )
    assert close(fill(s.faces.at((0, 0))), "#355f8d")


def test_cs1_any_callable_colormap():
    s = mp.ThreeDAxes().plot_surface(
        lambda u, v: 0 * u, colorscale=lambda t: (t, 0.0, 1 - t, 1.0), **SQUARE
    )
    assert close(fill(s.faces.at((0, 0))), "#800080", 1 / 255)


def test_cs2_a_callable_axis_spans_its_values():
    s = mp.ThreeDAxes().plot_surface(
        plane, colorscale=[BLUE, RED], colorscale_axis=lambda x, y, z: x * y, **SQUARE
    )
    # centres (0.5, 0.5) -> 0.25, (0.5, 1.5) -> 0.75, (1.5, 1.5) -> 2.25
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 0), 1 / 255)
    assert close(fill(s.faces.at((1, 1))), mix(BLUE, RED, 1), 1 / 255)
    assert close(fill(s.faces.at((0, 1))), mix(BLUE, RED, 0.25), 1 / 255)


@pytest.mark.parametrize("axis", [0, "x"])
def test_cs2_an_axis_by_number_or_name(axis):
    s = mp.ThreeDAxes().plot_surface(
        plane, colorscale=[BLUE, RED], colorscale_axis=axis, **SQUARE
    )
    # x range (-6, 6): the centre of face (1, 0) has x = 1.5
    assert close(fill(s.faces.at((1, 0))), mix(BLUE, RED, 7.5 / 12), 1 / 255)


def test_cs3_explicit_vmin_and_vmax():
    s = mp.ThreeDAxes().plot_surface(
        plane, colorscale=[BLUE, RED], vmin=0, vmax=4, **SQUARE
    )
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 0.25), 1 / 255)
    assert close(fill(s.faces.at((1, 1))), mix(BLUE, RED, 0.75), 1 / 255)


def test_cs3_a_log_axis_colours_on_its_scale():
    ax = mp.ThreeDAxes(z_range=(1, 1000), z_scale="log")
    s = ax.plot_surface(lambda u, v: 0 * u + 10, colorscale=[BLUE, RED], **SQUARE)
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 1 / 3), 1 / 255)
    s = ax.plot_surface(
        lambda u, v: 0 * u + 10, colorscale=[BLUE, RED], norm="linear", **SQUARE
    )
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 9 / 999), 1 / 255)


def test_cs4_an_explicit_stroke_is_kept():
    s = mp.ThreeDAxes().plot_surface(
        plane, colorscale=[BLUE, RED], stroke_color=WHITE, **SQUARE
    )
    assert stroke(s.faces.at((0, 0))) == ManimColor(WHITE).to_hex()
    mapping = s.color_mapping
    assert isinstance(mapping, mp.ColorMapping)
    assert (mapping.vmin, mapping.vmax) == pytest.approx((-4, 4))


def test_cs5_colours_follow_a_range_and_a_styled_face_is_kept():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(plane, colorscale=[BLUE, RED], **SQUARE)
    s.faces.at((0, 0)).set_fill(GREEN)
    ax.set_z_range((-8, 8, 1))
    assert fill(s.faces.at((0, 0))) == ManimColor(GREEN).to_hex()
    assert close(fill(s.faces.at((1, 1))), mix(BLUE, RED, 11 / 16), 1 / 255)
    s.set_colorscale([BLUE, RED])
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 9 / 16), 1 / 255)


def test_cs5_manims_colour_methods_replace_the_rule():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(plane, colorscale=[BLUE, RED], **SQUARE)
    s.set_fill_by_checkerboard(RED, GREEN)
    assert fill(s.faces.at((0, 0))) == ManimColor(RED).to_hex()
    assert fill(s.faces.at((0, 1))) == ManimColor(GREEN).to_hex()
    assert s.color_mapping is None
    ax.set_z_range((-8, 8, 1))
    assert fill(s.faces.at((0, 0))) == ManimColor(RED).to_hex()
    s.set_fill_by_value(ax, colorscale=[BLUE, RED], axis=2)
    assert close(fill(s.faces.at((0, 0))), mix(BLUE, RED, 9 / 16), 1 / 255)


def test_cs6_colormaps():
    gray = mp.Colormap(["#000000", "#ffffff"])
    np.testing.assert_allclose(gray(0.5), [0.5, 0.5, 0.5], atol=1e-9)
    assert np.asarray(gray(np.array([0.0, 0.5, 1.0]))).shape == (3, 3)
    stepped = mp.Colormap(["#000000", "#ffffff", "#ff0000"], positions=(0, 0.8, 1))
    np.testing.assert_allclose(stepped(0.4), [0.5, 0.5, 0.5], atol=1e-9)
    names = {"viridis", "plasma", "inferno", "magma", "cividis", "coolwarm", "RdBu_r"}
    assert names | {"gray"} <= set(mp.colormaps)
    assert {f"{n}_r" for n in names} <= set(mp.colormaps)
    np.testing.assert_allclose(
        mp.colormaps["viridis_r"](0), mp.colormaps["viridis"](1), atol=1e-12
    )
    hexed = ManimColor.from_rgb(mp.colormaps["coolwarm"](0.7)).to_hex()
    assert close(hexed, "#f7ac8e")


# --- SK -------------------------------------------------------------------------------


def test_sk1_faces_are_cut_on_the_box():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(lambda u, v: 3 * u, (-2, 2), (-1, 1), resolution=8)
    points = data(ax, np.concatenate([f.points for f in s.faces if f.has_points()]))
    assert points[:, 2].max() == pytest.approx(4, abs=1e-9)
    assert points[:, 2].min() == pytest.approx(-4, abs=1e-9)
    whole = ax.plot_surface(
        lambda u, v: 3 * u, (-2, 2), (-1, 1), resolution=8, clip=False
    )
    assert data(ax, whole.faces.at((7, 0)).points)[:, 2].max() > 5.9


def test_sk1_a_face_outside_keeps_its_place():
    s = mp.ThreeDAxes().plot_surface(lambda u, v: 0 * u + 9, (0, 1), (0, 1))
    assert len(s.faces) == 32 * 32
    assert not any(f.has_points() for f in s.faces)


def test_sk1_per_axis_clip():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(
        lambda u, v: 3 * u, (-2, 2), (-1, 1), resolution=8, clip=(True, True, False)
    )
    assert data(ax, s.faces.at((7, 0)).points)[:, 2].max() > 5.9


def test_sk2_faces_are_stable():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(plane, **SQUARE)
    face = s.faces.at((0, 0))
    ax.set_z_range((-2, 2, 1))
    assert s.faces.at((0, 0)) is face
    assert len(s.faces) == 4


def test_sk3_a_surface_follows_an_animated_range():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(lambda u, v: 0 * u + 1, (0, 1), (0, 1), resolution=1)
    heights = probe(
        lambda scene: scene.play(ax.animate.set_z_range((-2, 2, 1))),
        lambda: float(s.faces.at((0, 0)).get_center()[2]),
    )
    assert heights[0] == pytest.approx(0.8125, abs=1e-6)
    assert all(b >= a - 1e-9 for a, b in pairwise(heights))
    assert s.faces.at((0, 0)).get_center()[2] == pytest.approx(1.625)


def test_sk3_a_surface_follows_a_move():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(plane, **SQUARE)
    before = np.array(s.faces.at((1, 0)).points)
    ax.shift(RIGHT)
    np.testing.assert_allclose(s.faces.at((1, 0)).points, before + RIGHT, atol=1e-9)


def test_sk4_every_face_is_its_own_leaf():
    s = mp.ThreeDAxes().plot_surface(plane, **SQUARE)
    leaves = s.family_members_with_points()
    assert len(leaves) == 4
    assert {id(m) for m in leaves} == {id(f) for f in s.faces}


# --- WF -------------------------------------------------------------------------------


def saddle(u, v):
    return 0.25 * u * v**2


def test_wf1_wireframe_lines_lie_on_the_surface():
    ax = mp.ThreeDAxes()
    w = ax.plot_wireframe(saddle, (-2, 2), (-2, 2), resolution=4)
    assert len(w.u_lines) == 5
    assert len(w.v_lines) == 5
    line = data(ax, dense(w.u_lines.at(-1.0).points))
    np.testing.assert_allclose(line[:, 0], -1, atol=1e-9)
    np.testing.assert_allclose(line[:, 2], saddle(line[:, 0], line[:, 1]), atol=1e-3)
    line = data(ax, dense(w.v_lines.at(1.0).points))
    np.testing.assert_allclose(line[:, 1], 1, atol=1e-9)


def test_wf1_wireframe_takes_the_cycle():
    w = mp.ThreeDAxes().plot_wireframe(saddle, (-2, 2), (-2, 2))
    assert len(w.u_lines) == 11
    expected = ManimColor(mp.COLOR_CYCLE[0]).to_hex()
    assert ManimColor(w.u_lines[0].get_stroke_color()).to_hex() == expected


# --- CT -------------------------------------------------------------------------------


def paraboloid(u, v):
    return u**2 + v**2


def bowl(ax: Any) -> Any:
    return ax.plot_surface(paraboloid, (-2, 2), (-2, 2))


def test_ct1_level_lines_lie_on_the_surface():
    ax = mp.ThreeDAxes(z_range=(0, 8, 1))
    c = bowl(ax).contour([1, 2])
    assert c.levels == (1.0, 2.0)
    for level in (1.0, 2.0):
        line = data(ax, dense(c.at(level).points))
        np.testing.assert_allclose(line[:, 2], level, atol=1e-2)
        np.testing.assert_allclose(line[:, 0] ** 2 + line[:, 1] ** 2, level, atol=1e-2)


def test_ct1_another_coordinate():
    ax = mp.ThreeDAxes(z_range=(0, 8, 1))
    c = bowl(ax).contour([0.5], zdir="x")
    line = data(ax, dense(c.at(0.5).points))
    np.testing.assert_allclose(line[:, 0], 0.5, atol=1e-9)
    np.testing.assert_allclose(line[:, 2], 0.25 + line[:, 1] ** 2, atol=1e-2)


def test_ct2_levels_by_count_and_by_the_axis():
    ax = mp.ThreeDAxes(z_range=(0, 8, 1))
    assert bowl(ax).contour(3).levels == pytest.approx((2, 4, 6))
    ax = mp.ThreeDAxes()
    assert bowl(ax).contour().levels == pytest.approx((1, 2, 3, 4))


def test_ct3_an_offset_projects_the_lines():
    ax = mp.ThreeDAxes(z_range=(-4, 8, 1))
    c = bowl(ax).contour([1], offset=-4)
    line = data(ax, dense(c.at(1.0).points))
    np.testing.assert_allclose(line[:, 2], -4, atol=1e-9)
    np.testing.assert_allclose(line[:, 0] ** 2 + line[:, 1] ** 2, 1, atol=1e-2)


def shown(ax: Any, *mobs: Any, phi: float, theta: float) -> None:
    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=phi, theta=theta)
            self.add(ax, *mobs)
            self.wait(1 / 6)

    with tempconfig(RUN):
        Shot().render()


@pytest.mark.parametrize(("phi", "height"), [(65, 0.0), (110, 8.0)])
def test_ct3_contours_on_the_pane(phi, height):
    ax = mp.ThreeDAxes(
        x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(0, 8, 2), frame="box"
    )
    c = bowl(ax).contour([1], offset="pane")
    shown(ax, c, phi=phi * DEGREES, theta=-45 * DEGREES)
    line = data(ax, dense(c.at(1.0).points))
    np.testing.assert_allclose(line[:, 2], height, atol=1e-9)


def test_ct3_a_pane_needs_the_box():
    with pytest.raises(ValueError, match="offset"):
        bowl(mp.ThreeDAxes()).contour([1], offset="pane")


def test_ct4_colours():
    ax = mp.ThreeDAxes()
    s = ax.plot_surface(paraboloid, (-2, 2), (-2, 2), colorscale=[BLUE, RED])
    assert stroke(s.contour([1], color=YELLOW).at(1.0)) == ManimColor(YELLOW).to_hex()
    assert close(stroke(s.contour([2]).at(2.0)), mix(BLUE, RED, 6 / 8), 1 / 255)
    plain = bowl(ax).contour([1])
    assert stroke(plain.at(1.0)) == ManimColor(WHITE).to_hex()


def test_ct5_contours_follow_the_axes():
    ax = mp.ThreeDAxes(z_range=(0, 8, 1))
    c = bowl(ax).contour([1])
    ax.set_z_range((0, 4, 1))
    line = data(ax, dense(c.at(1.0).points))
    np.testing.assert_allclose(line[:, 2], 1, atol=1e-2)
