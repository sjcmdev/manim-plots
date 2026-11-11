"""Task 33: histograms and bars in 3D, rows H3 and B3 of
`docs/acceptance/33-histograms-3d.md`.

The oracles: `numpy.histogram2d`, the bar geometry written out, matplotlib's
`_shade_colors` rule (task 29, BR-2) and the colormap tables of task 25.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import DEGREES, RED, ManimColor, ThreeDScene, tempconfig

import manim_plots as mp

from .helpers import RUN

RNG = np.random.default_rng(4)
X, Y = RNG.normal(0, 1, 400), RNG.normal(0, 1, 400)
LIGHT = np.array([-2, -2, 1]) / 3
NORMALS = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def extent(ax: Any, group: Any) -> np.ndarray:
    pts = data(ax, np.concatenate([corners(f) for f in group if f.has_points()]))
    out: np.ndarray = np.array([pts.min(axis=0), pts.max(axis=0)])
    return out


def fill_rgb(mob: Any) -> np.ndarray:
    return np.asarray(ManimColor(mob.get_fill_color()).to_rgb())


def axes() -> Any:
    return mp.ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(0, 200, 50))


# --- H3 -------------------------------------------------------------------------------


def test_h3_1_counts_and_columns():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    assert isinstance(h, mp.Hist3DPlot)
    counts, xe, ye = np.histogram2d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    np.testing.assert_allclose(h.counts, counts)
    np.testing.assert_allclose(h.xedges, xe)
    i, j = np.unravel_index(np.argmax(counts), counts.shape)
    lo, hi = extent(ax, h.at((int(i), int(j))))
    cx, cy = (xe[i] + xe[i + 1]) / 2, (ye[j] + ye[j + 1]) / 2
    assert (lo[0], hi[0]) == pytest.approx((cx - 0.4, cx + 0.4), abs=1e-9)
    assert (lo[1], hi[1]) == pytest.approx((cy - 0.4, cy + 0.4), abs=1e-9)
    assert (lo[2], hi[2]) == pytest.approx((0, counts[i, j]), abs=1e-9)


def test_h3_1_empty_bins_draw_nothing():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    i, j = np.argwhere(h.counts == 0)[0]
    assert not any(f.has_points() for f in h.at((int(i), int(j))))


def test_h3_2_colour_by_count_then_shaded():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    drawn = h.counts[h.counts >= 1]
    lo, hi = drawn.min(), drawn.max()
    i, j = np.unravel_index(np.argmax(h.counts), h.counts.shape)
    base = mp.colormaps["viridis"]((h.counts[i, j] - lo) / (hi - lo))
    for face, n in zip(h.at((int(i), int(j))), NORMALS, strict=True):
        factor = 0.3 + 0.35 * (1 + np.dot(n, LIGHT))
        np.testing.assert_allclose(fill_rgb(face), base * factor, atol=1.5 / 255)
    assert tuple(ax.colorbar(h).y_range[:2]) == pytest.approx((lo, hi))
    flat = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)), shade=False)
    top = flat.at((int(i), int(j)))[1]
    np.testing.assert_allclose(fill_rgb(top), base, atol=1.5 / 255)


def test_h3_2_colour_by_position_or_one_colour():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)), color_by="x", shade=False)
    i, j = np.argwhere(h.counts >= 1)[0]
    centre = (h.xedges[i] + h.xedges[i + 1]) / 2
    expected = mp.colormaps["viridis"]((centre + 3) / 6)
    np.testing.assert_allclose(fill_rgb(h.at((int(i), int(j)))[1]), expected, atol=0.01)
    red = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)), color=RED, shade=False)
    assert red.color_mapping is None
    np.testing.assert_allclose(
        fill_rgb(red.at((int(i), int(j)))[1]), ManimColor(RED).to_rgb(), atol=1e-6
    )


def test_h3_3_set_data_in_place():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    i, j = np.unravel_index(np.argmax(h.counts), h.counts.shape)
    bar = h.at((int(i), int(j)))
    old = h.counts[i, j]
    more_x, more_y = np.concatenate([X, X]), np.concatenate([Y, Y])
    h.set_data(more_x, more_y)
    assert h.at((int(i), int(j))) is bar
    assert extent(ax, bar)[1][2] == pytest.approx(2 * old, abs=1e-9)
    np.testing.assert_allclose(
        h.counts, np.histogram2d(more_x, more_y, 6, ((-3, 3), (-3, 3)))[0]
    )


def test_h3_4_faces_drawn_far_to_near():
    ax = axes()
    h = ax.hist3d(X, Y, bins=6, range=((-3, 3), (-3, 3)))
    seen: list[np.ndarray] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)
            self.add(ax, h)
            self.wait(1 / 15)
            camera: Any = self.renderer.camera
            faces = {id(f) for f in h.family_members_with_points()}
            shown = camera.get_mobjects_to_display(self.mobjects)
            rot = camera.get_rotation_matrix()
            seen.append(
                np.array([(f.get_center() @ rot.T)[2] for f in shown if id(f) in faces])
            )

    with tempconfig(RUN):
        Shot().render()
    depths = seen[0]
    assert len(depths) == len(h.family_members_with_points())
    assert np.all(np.diff(depths) >= -1e-9)


# --- B3 -------------------------------------------------------------------------------


def test_b3_1_bar3d_by_height():
    ax = axes()
    bars = ax.bar3d([0, 1], [0, 0], [0, 0], 0.5, 0.5, [10, 30], c="height", shade=False)
    viridis = mp.colormaps["viridis"]
    np.testing.assert_allclose(fill_rgb(bars.bars[0][1]), viridis(0), atol=1.5 / 255)
    np.testing.assert_allclose(fill_rgb(bars.bars[1][1]), viridis(1), atol=1.5 / 255)
    assert bars.color_mapping is not None


def test_b3_2_two_d_bars_in_a_plane():
    ax = axes()
    bars = ax.bar([0, 1], [20, 40], zs=2, zdir="y", width=0.5)
    assert isinstance(bars, mp.BarPlot)
    pts = data(ax, corners(bars[1]))
    np.testing.assert_allclose(pts[:, 1], 2, atol=1e-9)
    assert (pts[:, 0].min(), pts[:, 0].max()) == pytest.approx((0.75, 1.25))
    assert (pts[:, 2].min(), pts[:, 2].max()) == pytest.approx((0, 40))


def test_b3_3_histograms_in_planes():
    ax = axes()
    h: Any = ax.hist(X, bins=6, range=(-3, 3), zs=-1, zdir="y", color_by="count")
    assert isinstance(cast(object, h), mp.HistPlot)
    pts = data(ax, corners(h.bars[2]))
    np.testing.assert_allclose(pts[:, 1], -1, atol=1e-9)
    assert pts[:, 2].max() == pytest.approx(h.counts[2])
    assert h.color_mapping is not None


def test_b3_4_planes_drawn_far_to_near():
    ax = axes()
    front = ax.hist(X, bins=6, range=(-3, 3), zs=-2, zdir="y")
    back = ax.hist(Y, bins=6, range=(-3, 3), zs=2, zdir="y")
    seen: list[np.ndarray] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)
            self.add(ax, front, back)
            self.wait(1 / 15)
            camera: Any = self.renderer.camera
            bars = {
                id(f)
                for plot in (front, back)
                for f in plot.family_members_with_points()
            }
            shown = camera.get_mobjects_to_display(self.mobjects)
            rot = camera.get_rotation_matrix()
            seen.append(
                np.array([(f.get_center() @ rot.T)[2] for f in shown if id(f) in bars])
            )

    with tempconfig(RUN):
        Shot().render()
    assert len(seen[0]) > 0
    assert np.all(np.diff(seen[0]) >= -1e-9)
