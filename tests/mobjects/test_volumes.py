"""Task 39: voxels and isosurfaces, rows VX and IS of `docs/acceptance/39-volumes.md`.

The oracles: face counts of voxel blocks counted by hand, matplotlib's shading rule
(BR-2), and the unit sphere's radius, area and volume.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import RED, ManimColor

import manim_plots as mp
from manim_plots.core import shape

LIGHT = np.array([-2, -2, 1]) / 3


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def drawn(plot: Any) -> list[Any]:
    return [f for f in plot.family_members_with_points() if not f.submobjects]


def axes() -> Any:
    return mp.ThreeDAxes(x_range=(0, 4, 1), y_range=(0, 4, 1), z_range=(0, 4, 1))


# --- VX -------------------------------------------------------------------------------


def test_vx1_only_outer_faces():
    ax = axes()
    block = ax.voxels(np.ones((3, 3, 3), bool))
    assert isinstance(cast(object, block), mp.VoxelPlot)
    assert len(drawn(block)) == 6 * 9
    assert len(block.at((1, 1, 1))) == 0
    pair = np.zeros((3, 3, 3), bool)
    pair[0, 0, 0] = pair[1, 0, 0] = True
    two = ax.voxels(pair)
    assert len(drawn(two)) == 10
    assert len(two.at((0, 0, 0))) == 5
    assert len(two.at((2, 2, 2))) == 0


def test_vx1_unit_boxes_and_corner_arrays():
    ax = axes()
    one = np.zeros((2, 2, 2), bool)
    one[1, 0, 1] = True
    cube = ax.voxels(one)
    pts = data(ax, np.concatenate([corners(f) for f in cube.at((1, 0, 1))]))
    np.testing.assert_allclose(pts.min(axis=0), (1, 0, 1), atol=1e-9)
    np.testing.assert_allclose(pts.max(axis=0), (2, 1, 2), atol=1e-9)
    x, y, z = np.meshgrid(*(np.arange(3) * 2.0,) * 3, indexing="ij")
    big = ax.voxels(x, y, z, one)
    pts = data(ax, np.concatenate([corners(f) for f in big.at((1, 0, 1))]))
    np.testing.assert_allclose(pts.min(axis=0), (2, 0, 2), atol=1e-9)
    np.testing.assert_allclose(pts.max(axis=0), (4, 2, 4), atol=1e-9)


def test_vx2_faces_keep_style_and_follow_ranges():
    ax = axes()
    one = np.ones((1, 1, 1), bool)
    cube = ax.voxels(one)
    face = cube.at((0, 0, 0))[0]
    face.set_stroke(RED, width=4)
    ax.set_x_range((0, 2, 1))
    assert cube.at((0, 0, 0))[0] is face
    assert face.get_stroke_width() == 4
    pts = data(ax, np.concatenate([corners(f) for f in cube.at((0, 0, 0))]))
    assert pts[:, 0].max() == pytest.approx(1, abs=1e-9)


def test_vx3_colours_by_value_and_shading():
    ax = axes()
    filled = np.zeros((2, 1, 1), bool)
    filled[:, 0, 0] = True
    values = np.array([[[0.0]], [[1.0]]])
    flat = ax.voxels(filled, c=values, shade=False)
    viridis = mp.colormaps["viridis"]
    for key, t in (((0, 0, 0), 0), ((1, 0, 0), 1)):
        rgb = ManimColor(flat.at(key)[0].get_fill_color()).to_rgb()
        np.testing.assert_allclose(rgb, viridis(t), atol=1.5 / 255)
    assert flat.color_mapping is not None
    lit = ax.voxels(np.ones((1, 1, 1), bool), facecolors=RED)
    base = np.asarray(ManimColor(RED).to_rgb())
    shades = sorted(
        float(ManimColor(f.get_fill_color()).to_rgb()[0]) for f in lit.at((0, 0, 0))
    )
    normals = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
    expected = sorted(
        float(base[0] * (0.3 + 0.35 * (1 + np.dot(n, LIGHT)))) for n in normals
    )
    np.testing.assert_allclose(shades, expected, atol=1.5 / 255)
    assert lit.at((0, 0, 0))[0].get_stroke_width() == 0


# --- IS -------------------------------------------------------------------------------


def sphere_grid(n: int = 24) -> tuple[np.ndarray, float, np.ndarray]:
    axis = np.linspace(-1.5, 1.5, n + 1)
    x, y, z = np.meshgrid(axis, axis, axis, indexing="ij")
    return x**2 + y**2 + z**2, 3 / n, np.array([-1.5, -1.5, -1.5])


def test_is1_marching_cubes_sphere_is_closed_and_outward():
    volume, h, origin = sphere_grid()
    vertices, triangles = shape.marching_cubes(volume, 1.0, (h, h, h), origin)
    r = np.linalg.norm(vertices, axis=1)
    assert np.max(np.abs(r - 1)) < 0.02
    edges = np.sort(
        np.concatenate(
            [triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]
        ),
        axis=1,
    )
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2)  # closed, one vertex per crossed edge
    a, b, c = (vertices[triangles[:, k]] for k in range(3))
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=1).sum()
    volume_enclosed = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6
    assert area == pytest.approx(4 * np.pi, rel=0.02)
    # normals towards increasing values: outward here, so the signed volume is positive
    assert volume_enclosed == pytest.approx(4 * np.pi / 3, rel=0.03)


def test_is2_plot_isosurface_from_a_function_or_samples():
    ax = mp.ThreeDAxes(x_range=(-1.5, 1.5, 0.5), y_range=(-1.5, 1.5, 0.5),
                       z_range=(-1.5, 1.5, 0.5))  # fmt: skip
    ball = ax.plot_isosurface(lambda x, y, z: x**2 + y**2 + z**2, 1.0, resolution=12)
    assert isinstance(cast(object, ball), mp.SurfacePlot)
    faces = drawn(ball)
    assert len(faces) > 100
    pts = data(ax, np.concatenate([corners(f) for f in faces]))
    assert np.max(np.abs(np.linalg.norm(pts, axis=1) - 1)) < 0.06
    volume, _, _ = sphere_grid(12)
    same = ax.plot_isosurface(volume, 1.0)
    assert len(drawn(same)) == len(faces)
    nothing = ax.plot_isosurface(volume, 100.0)
    assert len(drawn(nothing)) == 0
