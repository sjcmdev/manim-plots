"""Task 37: heatmaps, rows HM, HX, CT2 of `docs/acceptance/37-heatmaps.md`.

The oracles: cell geometry from matplotlib's documented conventions,
`numpy.histogram2d`,
the colormap tables of task 25, and areas computed by the shoelace formula.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import RED, ManimColor, ValueTracker

import manim_plots as mp

from .helpers import probe


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def centre(ax: Any, mob: Any) -> np.ndarray:
    out: np.ndarray = data(ax, corners(mob))[:, :2].mean(axis=0)
    return out


def fill_rgb(mob: Any) -> np.ndarray:
    return np.asarray(ManimColor(mob.get_fill_color()).to_rgb())


def area(polygon: np.ndarray) -> float:
    x, y = polygon[:, 0], polygon[:, 1]
    return float(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def path_area(ax: Any, mob: Any) -> float:
    """Total signed area of a VMobject's closed subpaths, in data units."""
    total = 0.0
    for sub in mob.get_subpaths():
        poly = data(ax, np.asarray(sub)[::4])[:, :2]
        total += abs(area(poly))
    return total


def axes(**kwargs: Any) -> Any:
    return mp.Axes(
        x_range=(-1, 6, 1), y_range=(-1, 6, 1), x_length=7, y_length=7, **kwargs
    )


Z = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]])


# --- HM -------------------------------------------------------------------------------


def test_hm1_imshow_cells_upper_and_lower():
    ax = axes()
    img = ax.imshow(Z)
    assert isinstance(img, mp.HeatmapPlot)
    assert len(img.cells) == 6
    np.testing.assert_allclose(centre(ax, img.cells.at((0, 0))), (0, 1), atol=1e-9)
    np.testing.assert_allclose(centre(ax, img.cells.at((1, 2))), (2, 0), atol=1e-9)
    low = ax.imshow(Z, origin="lower")
    np.testing.assert_allclose(centre(ax, low.cells.at((0, 0))), (0, 0), atol=1e-9)
    d = data(ax, corners(img.cells.at((0, 0))))
    assert np.ptp(d[:, 0]) == pytest.approx(1) and np.ptp(d[:, 1]) == pytest.approx(1)
    assert tuple(ax.x_range[:2]) == pytest.approx((-1, 6))  # ranges untouched


def test_hm1_extent():
    ax = axes()
    img = ax.imshow(Z, extent=(0, 6, 0, 4))
    np.testing.assert_allclose(centre(ax, img.cells.at((0, 0))), (1, 3), atol=1e-9)
    np.testing.assert_allclose(centre(ax, img.cells.at((1, 2))), (5, 1), atol=1e-9)


def test_hm2_pcolormesh_corner_grids_and_nearest():
    ax = axes()
    x, y = np.array([0, 1, 3, 4]), np.array([0, 2, 5])
    mesh = ax.pcolormesh(x, y, Z)
    d = data(ax, corners(mesh.cells.at((1, 1))))
    assert (
        d[:, 0].min(),
        d[:, 0].max(),
        d[:, 1].min(),
        d[:, 1].max(),
    ) == pytest.approx((1, 3, 2, 5))
    xs, ys = np.meshgrid([0.0, 1.0, 2.0], [0.0, 2.0])
    near = ax.pcolormesh(xs, ys, Z, shading="nearest")
    np.testing.assert_allclose(centre(ax, near.cells.at((1, 2))), (2, 2), atol=1e-9)


def test_hm3_colours_mapping_and_nan():
    ax = axes()
    img = ax.imshow(Z)
    viridis = mp.colormaps["viridis"]
    np.testing.assert_allclose(
        fill_rgb(img.cells.at((0, 0))), viridis(0), atol=1.5 / 255
    )
    np.testing.assert_allclose(
        fill_rgb(img.cells.at((1, 2))), viridis(1), atol=1.5 / 255
    )
    assert img.cells.at((0, 0)).get_stroke_width() == 0
    assert (img.color_mapping.vmin, img.color_mapping.vmax) == pytest.approx((0, 5))
    assert tuple(ax.colorbar(img).y_range[:2]) == pytest.approx((0, 5))
    holes = ax.imshow(np.array([[1.0, np.nan], [2.0, 3.0]]), colorscale="plasma")
    assert not holes.cells.at((0, 1)).has_points()
    assert len(holes.cells) == 4


def test_hm4_cells_keep_their_style_and_take_new_data():
    ax = axes()
    img = ax.imshow(Z)
    cell = img.cells.at((0, 1))
    cell.set_stroke(RED, width=3)
    img.set_data(Z[::-1])
    assert img.cells.at((0, 1)) is cell
    assert cell.get_stroke_width() == 3
    viridis = mp.colormaps["viridis"]
    np.testing.assert_allclose(
        fill_rgb(img.cells.at((0, 0))), viridis(3 / 5), atol=1.5 / 255
    )


def test_hm4_set_data_from_a_tracker_every_frame():
    ax = axes()
    t = ValueTracker(0)
    img = ax.imshow(Z, vmin=0, vmax=10)
    img.add_updater(lambda m: m.set_data(Z + t.get_value()))

    def worst() -> float:
        expected = mp.colormaps["viridis"]((Z[0, 0] + t.get_value()) / 10)
        return float(np.max(np.abs(fill_rgb(img.cells.at((0, 0))) - expected)))

    def construct(scene: Any) -> None:
        scene.add(ax, img)
        scene.play(t.animate.set_value(5))

    assert max(probe(construct, worst)) < 2 / 255


def test_hm5_cells_follow_a_range_and_are_cut():
    ax = axes()
    img = ax.imshow(Z)
    ax.set_x_range((-1, 1.25, 1))
    d = data(ax, corners(img.cells.at((0, 1))))
    assert d[:, 0].max() == pytest.approx(1.25, abs=1e-9)
    assert not img.cells.at((0, 2)).has_points()


def test_hm6_cell_labels_with_contrast():
    ax = axes()
    img = ax.imshow(Z)
    labels = img.label_cells(fmt="{:.0f}")
    assert len(labels) == 6
    texts = [str(getattr(m, "text", "")) for m in labels]
    assert texts == ["0", "1", "2", "3", "4", "5"]
    np.testing.assert_allclose(labels[4].get_center(), ax.c2p(1, 0), atol=1e-6)
    dark, light = labels[0], labels[5]  # viridis(0) is dark purple, viridis(1) yellow
    assert ManimColor(dark.get_color()).to_hex() == ManimColor("white").to_hex()
    assert ManimColor(light.get_color()).to_hex() == ManimColor("black").to_hex()


# --- HX -------------------------------------------------------------------------------


def test_hx1_hist2d_is_numpys():
    rng = np.random.default_rng(3)
    x, y = rng.normal(2, 1, 400), rng.normal(2, 1, 400)
    ax = axes()
    h = ax.hist2d(x, y, bins=5, range=((0, 4), (0, 4)))
    counts, xe, ye = np.histogram2d(x, y, bins=5, range=((0, 4), (0, 4)))
    np.testing.assert_allclose(h.counts, counts)
    np.testing.assert_allclose(h.xedges, xe)
    d = data(ax, corners(h.cells.at((1, 3))))  # y bin 1, x bin 3
    assert (d[:, 0].min(), d[:, 1].min()) == pytest.approx((xe[3], ye[1]))
    sparse = ax.hist2d(x, y, bins=5, range=((0, 4), (0, 4)), cmin=5)
    i, j = np.argwhere(counts.T < 5)[0]
    assert not sparse.cells.at((int(i), int(j))).has_points()


def test_hx2_every_point_in_one_containing_hexagon():
    rng = np.random.default_rng(5)
    x, y = rng.uniform(0, 5, 300), rng.uniform(0, 5, 300)
    ax = axes()
    hx = ax.hexbin(x, y, gridsize=6, extent=(0, 5, 0, 5))
    assert isinstance(hx, mp.HexbinPlot)
    assert hx.values.sum() == pytest.approx(300)
    polygons = [data(ax, corners(c))[:, :2] for c in hx.cells if c.has_points()]
    assert all(len(p) == 6 for p in polygons)

    def inside(poly: np.ndarray, p: np.ndarray) -> bool:
        edges = np.roll(poly, -1, axis=0) - poly
        cross = edges[:, 0] * (p[1] - poly[:, 1]) - edges[:, 1] * (p[0] - poly[:, 0])
        return bool(np.all(cross >= -1e-9) or np.all(cross <= 1e-9))

    for p in np.column_stack([x, y])[:40]:
        assert sum(inside(poly, p) for poly in polygons) >= 1
    some = ax.hexbin(x, y, C=x, gridsize=6, extent=(0, 5, 0, 5), mincnt=3)
    assert np.all(np.isfinite(some.values))


# --- CT2 ------------------------------------------------------------------------------


def grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs, ys = np.meshgrid(np.linspace(0, 4, 41), np.linspace(0, 4, 41))
    return xs, ys, (xs - 2) ** 2 + (ys - 2) ** 2


def test_ct2_1_level_lines_on_the_circles():
    ax = axes()
    xs, ys, zs = grid()
    cs = ax.contour(xs, ys, zs, levels=[1, 2])
    assert isinstance(cs, mp.ContourSetPlot)
    pts = data(ax, corners(cs.at(1.0)))
    np.testing.assert_allclose(np.hypot(pts[:, 0] - 2, pts[:, 1] - 2), 1, atol=1e-2)


def test_ct2_2_bands_tile_the_grid():
    ax = axes()
    xs, ys, zs = grid()
    levels = [0, 1, 2, 4, 8]
    cf = ax.contourf(xs, ys, zs, levels=levels)
    areas = [path_area(ax, cf.at(k)) for k in range(len(levels) - 1)]
    assert sum(areas) == pytest.approx(
        16, abs=1e-6
    )  # the 4 by 4 grid, z < 8 everywhere
    assert areas[0] == pytest.approx(np.pi, abs=0.05)  # the disc of radius 1
    assert cf.color_mapping is not None


def test_ct2_3_bound_to_ranges():
    ax = axes()
    xs, ys, zs = grid()
    cs = ax.contour(xs, ys, zs, levels=[1])
    ax.set_x_range((-2, 8, 1))
    pts = data(ax, corners(cs.at(1.0)))
    np.testing.assert_allclose(np.hypot(pts[:, 0] - 2, pts[:, 1] - 2), 1, atol=1e-2)
