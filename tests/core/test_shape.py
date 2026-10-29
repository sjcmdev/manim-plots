"""`Shape` stages and the pipeline's order (F-106, F-107, F-705, F-706, F-806, F-914).

Rows SH-1 to SH-12 of `docs/acceptance/07-sources-shape-params.md`, and the three cases
ADR 0003 §1 names: a segment from outside to outside across the viewport, a single
point, a pole gap. Oracles: Manim's own smoothing
(`get_smooth_cubic_bezier_handle_points`), Bézier curves evaluated here, SciPy's
adaptive quadrature for arc length, hand-built geometry.
"""

from __future__ import annotations

import functools
import math
from typing import Any

import numpy as np
import pytest
from manim.utils.bezier import get_smooth_cubic_bezier_handle_points
from scipy.integrate import quad  # type: ignore[import-untyped]

from manim_plots.core import shape
from manim_plots.core.nodes import AffineNode, Chain, FrameMap, ScaleNode, SystemMap
from manim_plots.core.payload import Payload
from manim_plots.core.scales import LinearScale
from manim_plots.core.shape import arc_length, clip, corners, dash, densify, smooth
from manim_plots.core.sources import ArraySource, Box, FunctionSource

BOX = Box(np.array([-3.0, -2.0]), np.array([3.0, 2.0]))
BIG = Box(np.array([-100.0, -100.0]), np.array([100.0, 100.0]))
SIZE = math.hypot(6.0, 4.0)


def path(*anchors) -> Payload:
    return Payload.path(np.array(anchors, dtype=float))


def curves_of(payload: Payload) -> list[np.ndarray]:
    """Each segment's curves, as an ``(k, 4, d)`` array."""
    return [
        payload.coords[a:b].reshape(-1, 4, payload.coords.shape[1])
        for a, b in payload.segments
    ]


def bezier(curve: np.ndarray, t: Any) -> Any:
    t = np.asarray(t, dtype=float)[:, None]
    p0, p1, p2, p3 = curve
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


def length_of(curve: np.ndarray) -> float:
    def speed(t: float) -> float:
        p0, p1, p2, p3 = curve
        d = (
            3 * (1 - t) ** 2 * (p1 - p0)
            + 6 * (1 - t) * t * (p2 - p1)
            + 3 * t**2 * (p3 - p2)
        )
        return float(np.linalg.norm(d))

    return float(quad(speed, 0.0, 1.0, epsabs=1e-14, epsrel=1e-13)[0])


def sampled(fn, lo: float, hi: float, n: int) -> Payload:
    x = np.linspace(lo, hi, n)
    return Payload.path(np.c_[x, fn(x)])


# --- SH-1 to SH-3: from anchors to curves -----------------------------------------


def test_sh1_shape_is_the_stage_type():
    assert shape.Shape is not None
    stage: shape.Shape = clip
    assert callable(stage)


def test_sh2_corners_are_straight_curves_with_handles_at_thirds():
    out = corners(path((0, 0), (3, 0), (3, 3)), BOX)
    np.testing.assert_allclose(
        out.coords,
        [[0, 0], [1, 0], [2, 0], [3, 0], [3, 0], [3, 1], [3, 2], [3, 3]],
    )
    np.testing.assert_array_equal(out.segments, [[0, 8]])
    assert out.valid is None


def test_sh2_a_lone_anchor_is_one_degenerate_curve():
    out = corners(path((1.0, 2.0)), BOX)
    np.testing.assert_array_equal(out.coords, [[1.0, 2.0]] * 4)


def test_sh2_invalid_samples_are_dropped():
    coords = np.array([[0, 0], [1, 1], [np.nan, np.nan], [3, 3], [4, 4]], dtype=float)
    out = corners(Payload.path(coords, np.array([True, True, False, True, True])), BOX)
    assert out.valid is None
    assert np.isfinite(out.coords).all()
    assert [b - a for a, b in out.segments] == [4, 4]


@pytest.mark.parametrize("n", [2, 3, 7, 40])
def test_sh3_smooth_matches_manims_handles(n):
    rng = np.random.default_rng(n)
    anchors = np.cumsum(rng.normal(size=(n, 2)), axis=0)
    out = smooth(Payload.path(anchors), BOX)
    h1, h2 = (
        np.reshape(h, (-1, 2)) for h in get_smooth_cubic_bezier_handle_points(anchors)
    )
    expected = np.stack([anchors[:-1], h1, h2, anchors[1:]], axis=1).reshape(-1, 2)
    np.testing.assert_allclose(out.coords, expected, rtol=1e-12, atol=1e-12)


def test_sh3_a_closed_run_uses_the_closed_handles():
    t = np.linspace(0, math.tau, 13)
    anchors = np.c_[np.cos(t), np.sin(t)]
    anchors[-1] = anchors[0]
    out = smooth(Payload.path(anchors), BOX)
    # Manim's closed solver indexes a third coordinate: give it z = 0.
    flat = np.c_[anchors, np.zeros(len(anchors))]
    h1, h2 = get_smooth_cubic_bezier_handle_points(flat)
    expected = np.stack([flat[:-1], h1, h2, flat[1:]], axis=1).reshape(-1, 3)[:, :2]
    np.testing.assert_allclose(out.coords, expected, rtol=1e-12, atol=1e-12)


def test_sh3_each_segment_is_smoothed_on_its_own():
    coords = np.array(
        [[0, 0], [1, 1], [2, 0], [np.nan, 0], [4, 0], [5, 1], [6, 0]], float
    )
    valid = np.isfinite(coords).all(axis=1)
    out = smooth(Payload.path(coords, valid), BIG)
    first = smooth(Payload.path(coords[:3]), BIG)
    second = smooth(Payload.path(coords[4:]), BIG)
    np.testing.assert_allclose(out.coords, np.r_[first.coords, second.coords])
    np.testing.assert_array_equal(out.segments, [[0, 8], [8, 16]])


# --- SH-4 to SH-6: clipping ----------------------------------------------------------


def test_sh4_a_line_crossing_the_box_is_cut_at_its_sides():
    out = clip(corners(path((-5, 0), (5, 0)), BOX), BOX)
    (curves,) = curves_of(out)
    assert curves.shape == (1, 4, 2)
    np.testing.assert_allclose(curves[0, 0], [-3, 0], atol=1e-9 * SIZE)
    np.testing.assert_allclose(curves[0, -1], [3, 0], atol=1e-9 * SIZE)


SECANT_BOX = Box(np.array([-4.5, -2.5]), np.array([4.5, 2.5]))
# Straight cubics from the secant demo, whose cubic and quadratic terms are rounding
# noise: the root solve found the crossing at t = 0.5, or not at all, and the line
# flickered past the axes for a frame.
STRAIGHT = [
    [
        [-4.524473674849413, -2.131309409174665],
        [-2.284308747445003, -1.478541806982563],
        [-0.04414382004059281, -0.8257742047904609],
        [2.1960211073638174, -0.17300660259835876],
    ],
    [
        [-4.6682007011651185, -2.109755851343566],
        [-2.416311273696219, -1.4986597452373147],
        [-0.16442184622731926, -0.8875636391310634],
        [2.0874675812415804, -0.2764675330248121],
    ],
]


@pytest.mark.parametrize("curve", STRAIGHT, ids=["crossing-at-half", "no-crossing"])
def test_sh4_a_straight_cubic_is_cut_where_it_crosses(curve):
    points = np.array(curve)
    p0, p3 = points[0], points[-1]
    crossing = p0 + (-4.5 - p0[0]) / (p3[0] - p0[0]) * (p3 - p0)
    for given in (
        Payload(kind="path", coords=points, segments=np.array([[0, 4]])),
        corners(path(p0, p3), SECANT_BOX),
    ):
        (curves,) = curves_of(clip(given, SECANT_BOX))
        assert curves.shape == (1, 4, 2)
        np.testing.assert_allclose(curves[0, 0], crossing, atol=1e-9)
        np.testing.assert_allclose(curves[0, -1], p3, atol=1e-12)


def test_sh4_a_curve_inside_is_kept_whole():
    inside = smooth(path((-1, 0), (0, 1), (1, 0)), BOX)
    out = clip(inside, BOX)
    np.testing.assert_array_equal(out.coords, inside.coords)
    np.testing.assert_array_equal(out.segments, inside.segments)


def test_sh4_a_path_wholly_outside_vanishes():
    out = clip(corners(path((5, 5), (8, 9)), BOX), BOX)
    assert out.segments.shape == (0, 2)


def test_sh4_leaving_and_returning_makes_two_pieces():
    out = clip(corners(path((-2, 0), (0, 5), (2, 0)), BOX), BOX)
    assert len(out.segments) == 2
    first, second = curves_of(out)
    np.testing.assert_allclose(first[-1, -1, 1], 2.0, atol=1e-9 * SIZE)
    np.testing.assert_allclose(second[0, 0, 1], 2.0, atol=1e-9 * SIZE)


def test_sh4_every_kept_curve_stays_in_the_box():
    out = clip(smooth(sampled(lambda x: 3 * np.sin(2 * x), -4, 4, 60), BOX), BOX)
    t = np.linspace(0, 1, 33)
    for curves in curves_of(out):
        for curve in curves:
            p = bezier(curve, t)
            assert (p >= BOX.lower - 1e-9 * SIZE).all()
            assert (p <= BOX.upper + 1e-9 * SIZE).all()


def test_sh4_clipping_keeps_the_geometry_inside():
    original = smooth(sampled(lambda x: 3 * np.sin(2 * x), -4, 4, 60), BOX)
    out = clip(original, BOX)
    # A point of a kept curve lies on the original path.
    t = np.linspace(0, 1, 9)
    dense = np.concatenate(
        [bezier(c, np.linspace(0, 1, 400)) for c in curves_of(original)[0]]
    )
    for curves in curves_of(out):
        for curve in curves:
            for p in bezier(curve, t):
                assert np.min(np.linalg.norm(dense - p, axis=1)) < 1e-2


def test_sh5_clipping_points_marks_those_outside_invalid():
    points = Payload.points(np.array([[0, 0], [5, 0], [3, 2], [-3.1, 0]], dtype=float))
    out = clip(points, BOX)
    np.testing.assert_array_equal(out.valid, [True, False, True, False])
    np.testing.assert_array_equal(out.coords, points.coords)
    np.testing.assert_array_equal(out.segments, [[0, 4]])


def test_sh6_clipping_a_region_drops_whole_cells():
    coords = np.array([[c, r] for r in (0.0, 1.0) for c in (0.0, 1.0, 5.0)])
    region = Payload(
        "region", coords, np.array([[0, 6]], dtype=np.intp), topology=(2, 3)
    )
    out = clip(region, BOX)
    assert out.kind == "region"
    np.testing.assert_array_equal(out.topology, [[0, 1, 4, 3]])


def test_sh6_a_cell_with_an_invalid_corner_is_dropped():
    coords = np.array([[c, r] for r in (0.0, 1.0) for c in (0.0, 1.0, 2.0)])
    valid = np.array([True, True, True, True, True, False])
    coords[5] = np.nan
    region = Payload(
        "region",
        coords,
        np.array([[0, 6]], dtype=np.intp),
        topology=(2, 3),
        valid=valid,
    )
    np.testing.assert_array_equal(clip(region, BOX).topology, [[0, 1, 4, 3]])


# --- SH-7 to SH-9: dashes and arc length -----------------------------------------


def dash_ends(payload: Payload) -> list[tuple[float, float]]:
    return [
        (payload.coords[a, 0], payload.coords[b - 1, 0]) for a, b in payload.segments
    ]


def test_sh7_a_line_in_dashes_of_one_and_gaps_of_one():
    out = dash(corners(path((0, 0), (10, 0)), BIG), BIG, on=1.0, off=1.0)
    np.testing.assert_allclose(
        dash_ends(out), [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)], atol=1e-9 * 10
    )


def test_sh7_the_phase_starts_inside_the_pattern():
    out = dash(corners(path((0, 0), (10, 0)), BIG), BIG, on=1.0, off=1.0, phase=0.5)
    np.testing.assert_allclose(dash_ends(out)[:2], [(0, 0.5), (1.5, 2.5)], atol=1e-8)


def test_sh7_every_piece_restarts_the_phase():
    coords = np.array([[0, 0], [3, 0], [np.nan, 0], [10, 0], [13, 0]], dtype=float)
    pieces = Payload.path(coords, np.isfinite(coords).all(axis=1))
    out = dash(corners(pieces, BIG), BIG, on=1.0, off=1.0)
    starts = [a for a, _ in dash_ends(out)]
    assert 0.0 in starts and 10.0 in starts
    np.testing.assert_allclose(sorted(starts), [0, 2, 10, 12], atol=1e-9)


def test_sh7_no_gap_returns_the_path():
    line = corners(path((0, 0), (10, 0)), BIG)
    out = dash(line, BIG, on=1.0, off=0.0)
    np.testing.assert_array_equal(out.coords, line.coords)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"on": 0.0, "off": 1.0},
        {"on": 1.0, "off": -1.0},
        {"on": 1.0, "off": 1.0, "phase": np.nan},
    ],
)
def test_sh7_an_impossible_pattern_raises(kwargs):
    with pytest.raises(ValueError):
        dash(corners(path((0, 0), (10, 0)), BIG), BIG, **kwargs)


def test_sh7_dashes_are_shapes_through_partial():
    stage = functools.partial(dash, on=2.0, off=1.0)
    out = stage(corners(path((0, 0), (10, 0)), BIG), BIG)
    assert len(out.segments) == 4


def test_sh8_dashes_do_not_move_when_the_line_is_resampled():
    coarse = corners(path((0, 0), (10, 0)), BIG)
    fine = corners(Payload.path(np.c_[np.linspace(0, 10, 23), np.zeros(23)]), BIG)
    a = dash(coarse, BIG, on=0.7, off=0.4, phase=0.2)
    b = dash(fine, BIG, on=0.7, off=0.4, phase=0.2)
    np.testing.assert_allclose(dash_ends(a), dash_ends(b), rtol=1e-9, atol=1e-9)


def test_sh8_dash_lengths_are_measured_along_the_curve():
    curve = smooth(sampled(np.sin, 0, 2 * math.pi, 50), BIG)
    out = dash(curve, BIG, on=0.5, off=0.25)
    lengths = arc_length(out)
    np.testing.assert_allclose(lengths[:-1], 0.5, rtol=1e-6)


def test_sh9_arc_length_of_a_line_and_of_a_cubic():
    np.testing.assert_allclose(arc_length(corners(path((0, 0), (3, 4)), BIG)), [5.0])
    # SH-9's claim covers the curves `smooth` makes of a sampled smooth function.
    payload = smooth(sampled(np.sin, 0, 2 * math.pi, 50), BIG)
    expected = sum(length_of(c) for c in payload.coords.reshape(-1, 4, 2))
    np.testing.assert_allclose(arc_length(payload), [expected], rtol=1e-9)


def test_sh9_arc_length_per_segment():
    coords = np.array([[0, 0], [3, 4], [np.nan, 0], [0, 0], [0, 2]], dtype=float)
    pieces = corners(Payload.path(coords, np.isfinite(coords).all(axis=1)), BIG)
    np.testing.assert_allclose(arc_length(pieces), [5.0, 2.0])


# --- SH-10 to SH-12 ----------------------------------------------------------------


def test_sh10_densify_splits_each_curve_without_moving_it():
    original = smooth(path((0, 0), (1, 2), (3, 1)), BIG)
    out = densify(original, BIG, pieces=3)
    assert len(out.coords) == 3 * len(original.coords)
    t = np.linspace(0, 1, 7)
    for k, curve in enumerate(curves_of(original)[0]):
        pieces = curves_of(out)[0][3 * k : 3 * k + 3]
        for j, piece in enumerate(pieces):
            np.testing.assert_allclose(
                bezier(piece, t), bezier(curve, (j + t) / 3), atol=1e-12
            )


def test_sh10_densify_needs_a_piece():
    with pytest.raises(ValueError):
        densify(corners(path((0, 0), (1, 1)), BIG), BIG, pieces=0)


@pytest.mark.parametrize(
    "stage",
    [
        corners,
        smooth,
        functools.partial(dash, on=1, off=1),
        functools.partial(densify, pieces=2),
    ],
)
def test_sh11_path_stages_refuse_points(stage):
    with pytest.raises(ValueError, match="points"):
        stage(Payload.points(np.zeros((3, 2))), BOX)


@pytest.mark.parametrize(
    "stage",
    [
        corners,
        smooth,
        clip,
        functools.partial(dash, on=1, off=1),
        functools.partial(densify, pieces=2),
    ],
)
def test_sh12_empty_in_empty_out(stage):
    out = stage(Payload.empty("path", 2), BOX)
    assert out.kind == "path"
    assert out.coords.shape[0] == 0
    assert out.segments.shape == (0, 2)


@pytest.mark.parametrize("stage", [corners, smooth, clip])
def test_every_stage_leaves_its_input_alone(stage):
    payload = sampled(np.sin, -5, 5, 20)
    before = payload.coords.copy()
    out = stage(payload, BOX)
    assert out is not payload
    np.testing.assert_array_equal(payload.coords, before)


# --- ADR 0003 §1: the pipeline's order ---------------------------------------------


def local_system():
    """Data ``(-6, 6) x (-4, 4)`` onto the local box at half scale."""
    lower, upper = np.array([-3.0, -2.0]), np.array([3.0, 2.0])
    data = Chain(
        [
            ScaleNode(LinearScale(), 0, 2),
            AffineNode.from_parts(np.diag([0.5, 0.5]), np.zeros(2)),
        ]
    )
    frame = FrameMap(lower, upper, FrameMap.lattice(lower, upper, 9))
    return SystemMap(data, frame), data, Box(lower, upper)


def pipeline(source, *, smoothing=True):
    """Source, Map, then smooth or corners, then clip: ADR 0003 §1's order."""
    map_, data, bounds = local_system()
    payload = data.apply_payload(source.sample(map_, bounds))
    payload = (smooth if smoothing else corners)(payload, bounds)
    return clip(payload, bounds)


def test_pipeline_a_segment_from_outside_to_outside_crosses_the_viewport():
    out = pipeline(ArraySource([-10, 10], [1, 1]), smoothing=False)
    (curves,) = curves_of(out)
    np.testing.assert_allclose(curves[0, 0], [-3.0, 0.5], atol=1e-9)
    np.testing.assert_allclose(curves[-1, -1], [3.0, 0.5], atol=1e-9)


def test_pipeline_a_single_point_survives():
    map_, data, bounds = local_system()
    payload = ArraySource([1.0], [1.0], kind="points").sample(map_, bounds)
    out = clip(data.apply_payload(payload), bounds)
    np.testing.assert_allclose(out.coords, [[0.5, 0.5]])
    assert out.valid is None or out.valid.all()


def test_pipeline_a_pole_leaves_a_gap_and_nothing_leaves_the_viewport():
    out = pipeline(FunctionSource(lambda x: 1 / (x - 0.1)))
    pole = 0.05  # 0.1 in data is 0.05 in local x
    t = np.linspace(0, 1, 17)
    for curves in curves_of(out):
        xs = np.concatenate([bezier(c, t)[:, 0] for c in curves])
        assert (xs < pole).all() or (xs > pole).all()
        ys = np.concatenate([bezier(c, t)[:, 1] for c in curves])
        assert (np.abs(ys) <= 2 + 1e-9).all()
    assert len(out.segments) >= 2
