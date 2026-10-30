"""Task 29: more plot types, rows VS, SM, WT, FB3, BR, EB3, TX, PJ, GM of
`docs/acceptance/29-plot-types.md`.

The oracles: the data by hand, matplotlib's colormap tables (task 25) and its
`_shade_colors` rule written out, the projection of `ThreeDCamera` for PJ-1.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import (
    BLUE,
    DEFAULT_DOT_RADIUS,
    DEGREES,
    RED,
    Create,
    ManimColor,
    Square,
    ThreeDScene,
    Transform,
    interpolate_color,
    linear,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, probe


def anchors(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def vertices(mob: Any) -> np.ndarray:
    """A polyline's corners: every curve's start and the last curve's end."""
    points = np.asarray(mob.points)
    return np.vstack([points[::4], points[-1:]])


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def ends(mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    return np.array([points[0], points[-1]])


def same_set(a: Any, b: Any, atol: float = 1e-9) -> None:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert len(a) == len(b)
    for p in a:
        assert np.min(np.linalg.norm(b - p, axis=1)) < atol


def rgb(color: Any) -> np.ndarray:
    return np.asarray(ManimColor(color).to_rgb())


def fill_rgb(mob: Any) -> np.ndarray:
    return rgb(mob.get_fill_color())


# --- VS -------------------------------------------------------------------------------


def test_vs1_colour_by_value_in_2d():
    ax = mp.Axes()
    dots = ax.scatter([0, 1, 2], [0, 1, 2], c=[0.0, 5.0, 10.0])
    viridis = mp.colormaps["viridis"]
    for dot, t in zip(dots, (0.0, 0.5, 1.0), strict=True):
        np.testing.assert_allclose(fill_rgb(dot), viridis(t), atol=1.5 / 255)
    mapping = dots.color_mapping
    assert mapping is not None
    assert (mapping.vmin, mapping.vmax) == pytest.approx((0, 10))
    bar = ax.colorbar(dots)
    assert tuple(bar.y_range[:2]) == pytest.approx((0, 10))


def test_vs1_colour_by_value_in_3d():
    ax = mp.ThreeDAxes()
    dots = ax.scatter(
        [0, 1], [0, 1], [0, 1], c=[0.25, 1.0], colorscale=[BLUE, RED], vmin=0, vmax=1
    )
    expected = interpolate_color(ManimColor(BLUE), ManimColor(RED), 0.25)
    np.testing.assert_allclose(fill_rgb(dots[0]), rgb(expected), atol=1.5 / 255)
    np.testing.assert_allclose(fill_rgb(dots[1]), rgb(RED), atol=1.5 / 255)


def test_vs1_one_colour_and_a_wrong_length():
    ax = mp.Axes()
    dots = ax.scatter([0, 1], [0, 1], c=RED)
    assert all(np.allclose(fill_rgb(d), rgb(RED)) for d in dots)
    with pytest.raises(ValueError, match="c"):
        ax.scatter([0, 1], [0, 1], c=[1.0, 2.0, 3.0])


def test_vs2_sizes():
    ax = mp.Axes()
    dots = ax.scatter([0, 1], [0, 1], s=0.2)
    assert all(d.width == pytest.approx(0.4) for d in dots)
    sized = ax.scatter([0, 1], [0, 1], s=[0.1, 0.3])
    assert sized[0].width == pytest.approx(0.2)
    assert sized[1].width == pytest.approx(0.6)
    assert ax.scatter([0], [0])[0].width == pytest.approx(2 * DEFAULT_DOT_RADIUS)
    with pytest.raises(ValueError, match="s"):
        ax.scatter([0, 1], [0, 1], s=[0.1])


# --- SM -------------------------------------------------------------------------------


def test_sm1_stems_markers_and_baseline():
    ax = mp.ThreeDAxes()
    st = ax.stem([0, 1], [1, 2], [2, 3])
    assert isinstance(st, mp.StemPlot)
    np.testing.assert_allclose(
        data(ax, ends(st.stemlines[0])), [(0, 1, 0), (0, 1, 2)], atol=1e-9
    )
    np.testing.assert_allclose(
        data(ax, ends(st.stemlines[1])), [(1, 2, 0), (1, 2, 3)], atol=1e-9
    )
    np.testing.assert_allclose(st.markers[1].get_center(), ax.c2p(1, 2, 3), atol=1e-9)
    np.testing.assert_allclose(
        data(ax, ends(st.baseline)), [(0, 1, 0), (1, 2, 0)], atol=1e-9
    )


def test_sm1_bottom_and_orientation():
    ax = mp.ThreeDAxes()
    st = ax.stem([3], [1], [2], bottom=-1, orientation="x")
    np.testing.assert_allclose(
        data(ax, ends(st.stemlines[0])), [(-1, 1, 2), (3, 1, 2)], atol=1e-9
    )


def test_sm2_colours():
    ax = mp.ThreeDAxes()
    st = ax.stem([0, 1], [1, 2], [2, 3])
    assert st.stemlines[0].get_color() == st.markers[0].get_color()
    assert st.baseline.get_stroke_width() == pytest.approx(1)


# --- WT -------------------------------------------------------------------------------


def test_wt1_curves_laid_in_their_planes():
    ax = mp.ThreeDAxes()
    wf = ax.waterfall([0, 1, 2], [[0, 1, 0], [1, 2, 1]])
    assert isinstance(wf, mp.WaterfallPlot)
    same_set(data(ax, vertices(wf.lines[1])), [(0, 1, 1), (1, 1, 2), (2, 1, 1)])
    fill = data(ax, anchors(wf.fills[0]))
    np.testing.assert_allclose(fill[:, 1], 0, atol=1e-9)
    assert fill[:, 2].min() == pytest.approx(-4)  # down to the floor
    assert wf.lines[0].get_color() != wf.lines[1].get_color()
    first = wf.fills[0]
    assert first is not None
    assert first.get_fill_opacity() == pytest.approx(0.5)


def test_wt1_positions_direction_and_no_fill():
    ax = mp.ThreeDAxes()
    wf = ax.waterfall([0, 1], [[1, 2]], positions=[3], zdir="x", fill=False)
    same_set(data(ax, vertices(wf.lines[0])), [(3, 0, 1), (3, 1, 2)])
    assert wf.fills[0] is None


# --- FB3 ------------------------------------------------------------------------------


def test_fb3_the_band_is_a_two_row_surface():
    ax = mp.ThreeDAxes()
    band = ax.fill_between(
        [0, 1, 2], [0, 0, 0], [0, 1, 0], [0, 1, 2], [1, 1, 1], [1, 2, 1]
    )
    assert isinstance(band, mp.SurfacePlot)
    assert len(band.faces) == 2
    same_set(
        data(ax, anchors(band.faces.at((0, 0)))),
        [(0, 0, 0), (1, 0, 1), (1, 1, 2), (0, 1, 1)],
    )
    assert band.faces.at((0, 0)).get_fill_opacity() == pytest.approx(0.5)
    with pytest.raises(ValueError, match="x2"):
        ax.fill_between([0, 1], [0, 0], [0, 0], [0], [1], [1])


# --- BR -------------------------------------------------------------------------------


def test_br1_six_faces_in_matplotlibs_order():
    ax = mp.ThreeDAxes()
    bars = ax.bar3d([0], [0], [0], 1, 2, 3)
    assert isinstance(bars, mp.BarPlot3D)
    faces = list(bars.bars[0])
    assert len(faces) == 6
    expected = [
        [(0, 0, 0), (1, 0, 0), (1, 2, 0), (0, 2, 0)],
        [(0, 0, 3), (1, 0, 3), (1, 2, 3), (0, 2, 3)],
        [(0, 0, 0), (1, 0, 0), (1, 0, 3), (0, 0, 3)],
        [(0, 2, 0), (1, 2, 0), (1, 2, 3), (0, 2, 3)],
        [(0, 0, 0), (0, 2, 0), (0, 2, 3), (0, 0, 3)],
        [(1, 0, 0), (1, 2, 0), (1, 2, 3), (1, 0, 3)],
    ]
    for face, corners in zip(faces, expected, strict=True):
        same_set(data(ax, anchors(face)), corners)


def test_br2_matplotlibs_shading():
    ax = mp.ThreeDAxes()
    faces = list(ax.bar3d([0], [0], [0], 1, 1, 1, color=RED).bars[0])
    light = np.array([-2, -2, 1]) / 3
    normals = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
    for face, n in zip(faces, normals, strict=True):
        factor = 0.3 + 0.35 * (1 + np.dot(n, light))
        np.testing.assert_allclose(fill_rgb(face), rgb(RED) * factor, atol=1.5 / 255)
        assert not face.shade_in_3d
    flat = list(ax.bar3d([0], [0], [0], 1, 1, 1, color=RED, shade=False).bars[0])
    assert all(np.allclose(fill_rgb(f), rgb(RED), atol=1.5 / 255) for f in flat)


def test_br3_bars_follow_a_range_change():
    ax = mp.ThreeDAxes()
    top = ax.bar3d([0], [0], [0], 1, 1, 3).bars[0][1]
    ax.set_z_range((-2, 6, 1))
    same_set(data(ax, anchors(top)), [(0, 0, 3), (1, 0, 3), (1, 1, 3), (0, 1, 3)])


# --- EB3 ------------------------------------------------------------------------------


def test_eb3_bars_on_three_axes():
    ax = mp.ThreeDAxes()
    eb = ax.errorbar([1], [2], [3], zerr=0.5, xerr=[[0.1], [0.2]])
    assert isinstance(eb, mp.ErrorBars)
    np.testing.assert_allclose(
        data(ax, ends(eb.zbars)), [(1, 2, 2.5), (1, 2, 3.5)], atol=1e-9
    )
    np.testing.assert_allclose(
        data(ax, ends(eb.xbars)), [(0.9, 2, 3), (1.2, 2, 3)], atol=1e-9
    )
    assert eb.ybars is None
    assert eb.markers is not None
    np.testing.assert_allclose(eb.markers[0].get_center(), ax.c2p(1, 2, 3), atol=1e-9)


def test_eb3_caps_face_the_default_view():
    ax = mp.ThreeDAxes()
    eb = ax.errorbar([1], [2], [3], xerr=0.5)
    assert eb.xcaps is not None
    caps = np.asarray(eb.xcaps.get_all_points())
    assert np.ptp(caps[:, 1]) == pytest.approx(0.1, abs=1e-6)  # across the bar
    assert np.ptp(caps[:, 2]) == pytest.approx(0, abs=1e-9)  # in the facing plane


# --- TX -------------------------------------------------------------------------------


def test_tx1_text_at_a_point_follows_the_axes():
    ax = mp.ThreeDAxes()
    label = ax.text(1, 2, 3, "abcdef")
    np.testing.assert_allclose(label.get_center(), ax.c2p(1, 2, 3), atol=1e-6)
    ax.set_z_range((-2, 6, 1))
    np.testing.assert_allclose(label.get_center(), ax.c2p(1, 2, 3), atol=1e-6)
    assert label.width > label.height  # upright on the default view
    square = Square(0.2)
    assert ax.text(0, 0, 0, square) is square


def test_tx1_zdir_turns_the_baseline():
    ax = mp.ThreeDAxes()
    label = ax.text(0, 0, 0, "abcdef", zdir="y")
    points = np.asarray(label.get_all_points())
    assert np.ptp(points[:, 1]) > np.ptp(points[:, 0])


def test_tx2_an_annotation_points_at_its_point():
    ax = mp.ThreeDAxes()
    note: Any = ax.annotate("P", (1, 2, 3), (2, 2, 3))
    assert mp.HelperGroup in type(note).__mro__
    np.testing.assert_allclose(note.text.get_center(), ax.c2p(2, 2, 3), atol=1e-6)
    tip = np.asarray(note.arrow.get_all_points())
    assert np.min(np.linalg.norm(tip - ax.c2p(1, 2, 3), axis=1)) < 1e-6
    plain: Any = ax.annotate("Q", (0, 0, 0), arrow=False)
    np.testing.assert_allclose(
        plain.text.get_center(), ax.c2p(0, 0, 0) + np.array([0.6, 0.6, 0]), atol=1e-6
    )
    assert plain.arrow is None


def test_tx2_in_a_three_d_scene_the_text_stays_at_its_point():
    ax = mp.ThreeDAxes()
    note: Any = ax.annotate("peak", (2, 2, 2), (3.5, 0.5, 3.5))
    label = ax.text(0.5, 3.5, 4, "top")
    seen: list[np.ndarray] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
            self.add(ax, note, label)
            self.wait(1 / 6)
            seen.extend([note.text.get_center(), label.get_center()])
            tip = np.asarray(note.arrow.get_all_points())
            seen.append(np.min(np.linalg.norm(tip - ax.c2p(2, 2, 2), axis=1)))

    with tempconfig(RUN):
        Shot().render()
    # a turned text's bounding box centre is within a few hundredths of its anchor
    np.testing.assert_allclose(seen[0], ax.c2p(3.5, 0.5, 3.5), atol=0.05)
    np.testing.assert_allclose(seen[1], ax.c2p(0.5, 3.5, 4), atol=0.05)
    assert seen[2] < 1e-6


# --- PJ -------------------------------------------------------------------------------


def test_pj1_view_keywords():
    ax = mp.ThreeDAxes()
    assert ax.view(30, -60, proj_type="ortho")["focal_distance"] == 1e6
    assert "focal_distance" not in ax.view(30, -60)
    with pytest.raises(ValueError, match="proj_type"):
        ax.view(30, -60, proj_type="fisheye")


@pytest.mark.parametrize(("proj", "parallel"), [("ortho", True), ("persp", False)])
def test_pj1_parallel_edges_stay_parallel(proj, parallel):
    ax = mp.ThreeDAxes()
    edges = np.array(
        [ax.c2p(-5, -4, -3), ax.c2p(5, -4, -3), ax.c2p(-5, 4, 3), ax.c2p(5, 4, 3)]
    )
    seen: list[np.ndarray] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(**ax.view(30, -60, proj_type=proj))  # type: ignore[arg-type]
            self.add(ax)
            self.wait(1 / 6)
            seen.append(self.camera.project_points(edges)[:, :2])

    with tempconfig(RUN):
        Shot().render()
    p = seen[0]
    a, b = p[1] - p[0], p[3] - p[2]
    cross = abs(a[0] * b[1] - a[1] * b[0]) / (np.linalg.norm(a) * np.linalg.norm(b))
    assert (cross < 1e-4) == parallel


# --- GM -------------------------------------------------------------------------------


def corners(surface: Any) -> np.ndarray:
    return np.concatenate([anchors(f) for f in surface.faces])


def test_gm1_create_ends_where_it_started():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(lambda u, v: u * v / 4, (-2, 2), (-2, 2), resolution=4)
    before = corners(surface).copy()
    probe(lambda s: s.play(Create(surface)), lambda: None)
    np.testing.assert_allclose(corners(surface), before, atol=1e-9)


def test_gm2_a_surface_grows_from_the_floor():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(
        lambda u, v: u * v / 2 + 1, (-2, 2), (-2, 2), resolution=4
    )
    final = data(ax, corners(surface))
    spread: list[float] = []

    def record() -> None:
        now = data(ax, corners(surface))
        np.testing.assert_allclose(now[:, :2], final[:, :2], atol=1e-9)
        alpha = (now[:, 2] + 4) / (final[:, 2] + 4)
        spread.append(float(np.ptp(alpha)))

    updaters = len(surface.get_updaters())
    probe(lambda s: s.play(mp.GrowSurface(surface, rate_func=linear)), record)
    assert max(spread) < 1e-9  # one alpha for every point of a frame
    np.testing.assert_allclose(data(ax, corners(surface)), final, atol=1e-9)
    assert len(surface.get_updaters()) == updaters
    ax.set_z_range((-2, 6, 1))
    np.testing.assert_allclose(data(ax, corners(surface)), final, atol=1e-9)


def test_gm3_a_transform_adopts_its_target():
    ax = mp.ThreeDAxes()
    a = ax.plot_surface(lambda u, v: u * v / 4, (-2, 2), (-2, 2), resolution=4)
    b = ax.plot_surface(
        lambda u, v: 1 - (u**2 + v**2) / 8, (-2, 2), (-2, 2), resolution=4
    )
    probe(lambda s: s.play(Transform(a, b)), lambda: None)
    np.testing.assert_allclose(corners(a), corners(b), atol=1e-9)
    ax.set_z_range((-2, 6, 1))
    np.testing.assert_allclose(data(ax, corners(a)), data(ax, corners(b)), atol=1e-9)


def test_gm_in_a_three_d_scene():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(lambda u, v: u * v / 4, (-2, 2), (-2, 2), resolution=4)

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)
            self.play(mp.GrowSurface(surface, run_time=1 / 3))

    with tempconfig(RUN):
        Shot().render()
