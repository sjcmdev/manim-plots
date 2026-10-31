"""Local-space cubic geometry stages, independent of Manim."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from itertools import pairwise
from numbers import Real

import numpy as np
from numpy.typing import ArrayLike
from scipy.linalg.lapack import dpttrf, dpttrs  # type: ignore[import-untyped]

from manim_plots.core import FloatArray, IntArray
from manim_plots.core.payload import Payload
from manim_plots.core.sources import Bounds, Box, _Disk

Shape = Callable[[Payload, Bounds], Payload]


def marching_cubes(
    volume: ArrayLike,
    level: float,
    spacing: ArrayLike = (1, 1, 1),
    origin: ArrayLike = (0, 0, 0),
) -> tuple[FloatArray, IntArray]:
    """Extract a level surface with shared grid-edge vertices.

    Parameters
    ----------
    volume, level
        Finite three-dimensional samples and the level to extract.
    spacing, origin
        Grid steps and the data coordinates of the first sample.

    Returns
    -------
    vertices, triangles
        Data coordinates and triangle indices, wound towards increasing values.
    """
    values = np.asarray(volume, float)
    step, start = np.asarray(spacing, float), np.asarray(origin, float)
    if values.ndim != 3 or min(values.shape) < 2 or not np.isfinite(values).all():
        raise ValueError("volume must be finite with at least two samples per axis")
    if (
        step.shape != (3,)
        or start.shape != (3,)
        or not np.isfinite(step).all()
        or not np.isfinite(start).all()
        or np.any(step == 0)
        or not np.isfinite(level)
    ):
        raise ValueError("spacing, origin and level must be finite; spacing nonzero")
    offsets = np.array(
        [
            (0, 0, 0),
            (1, 0, 0),
            (1, 1, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 1),
            (1, 1, 1),
            (0, 1, 1),
        ]
    )
    edges = np.array(
        [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]
    )
    cubes = np.indices(tuple(n - 1 for n in values.shape)).reshape(3, -1).T
    nodes = cubes[:, None, :] + offsets
    samples = values[tuple(nodes.transpose(2, 0, 1))]
    cases = ((samples < level) * (1 << np.arange(8))).sum(axis=1)
    active = (cases != 0) & (cases != 255)
    nodes, samples, cases = nodes[active], samples[active], cases[active]
    crossed = (_MC_EDGES[cases, None] & (1 << np.arange(12))) != 0
    ci, ei = np.nonzero(crossed)
    endpoints = nodes[ci[:, None], edges[ei]]
    ids = np.ravel_multi_index(tuple(endpoints.transpose(2, 0, 1)), values.shape)
    unique, inverse = np.unique(np.sort(ids, axis=1), axis=0, return_inverse=True)
    grid = np.stack(np.unravel_index(unique, values.shape), axis=-1).astype(float)
    low, high = values.ravel()[unique].T
    fraction = (level - low) / (high - low)
    vertices = (
        grid[:, 0] + fraction[:, None] * (grid[:, 1] - grid[:, 0])
    ) * step + start
    edge_index = np.full((len(cases), 12), -1, dtype=np.intp)
    edge_index[ci, ei] = inverse
    faces = np.array(
        [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [3, 2, 6, 7],
            [0, 3, 7, 4],
            [1, 2, 6, 5],
        ]
    )
    face_edges = np.array(
        [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 9, 4, 8],
            [2, 10, 6, 11],
            [3, 11, 7, 8],
            [1, 10, 5, 9],
        ]
    )
    ambiguous = (crossed[:, face_edges].sum(axis=2) == 4).any(axis=1)
    table = _MC_TRIANGLES[cases[~ambiguous]]
    rows, columns = np.nonzero(table >= 0)
    triangles = edge_index[~ambiguous][rows, table[rows, columns]].reshape(-1, 3)
    # The classic table points into the below-level region.
    triangles = triangles[:, [0, 2, 1]] if np.prod(step) > 0 else triangles
    resolved: list[tuple[int, int, int]] = []
    for cube in np.flatnonzero(ambiguous):
        neighbours: dict[int, list[int]] = {}
        for corners, boundary in zip(faces, face_edges, strict=True):
            hits = boundary[crossed[cube, boundary]]
            if len(hits) == 4:
                # Both incident cubes see the same face-centre value and pairing.
                centre_below = samples[cube, corners].mean() < level
                hits = np.roll(
                    hits, -int(centre_below == (samples[cube, corners[0]] < level))
                )
            for a, b in hits.reshape(-1, 2):
                neighbours.setdefault(int(a), []).append(int(b))
                neighbours.setdefault(int(b), []).append(int(a))
        while neighbours:
            first = next(iter(neighbours))
            loop, current, previous = [first], neighbours[first][0], first
            while current != first:
                loop.append(current)
                following = next(n for n in neighbours[current] if n != previous)
                previous, current = current, following
            for edge in loop:
                del neighbours[edge]
            while len(loop) > 2:
                # Interior diagonals must not become extra contours on a shared face.
                ear = next(
                    (
                        j
                        for j in range(len(loop))
                        if len(loop) == 3
                        or not any(
                            loop[j - 1] in boundary
                            and loop[(j + 1) % len(loop)] in boundary
                            for boundary in face_edges
                        )
                    ),
                    0,
                )
                tri = tuple(
                    int(edge_index[cube, loop[j]])
                    for j in (ear - 1, ear, (ear + 1) % len(loop))
                )
                del loop[ear]
                points = vertices[list(tri)]
                uvw = (points.mean(axis=0) - start) / step - nodes[cube, 0]
                weights = np.where(offsets, uvw, 1 - uvw)
                gradient = np.array(
                    [
                        np.sum(
                            samples[cube]
                            * (2 * offsets[:, axis] - 1)
                            * np.prod(np.delete(weights, axis, axis=1), axis=1)
                        )
                        / step[axis]
                        for axis in range(3)
                    ]
                )
                if (
                    np.dot(
                        np.cross(points[1] - points[0], points[2] - points[0]), gradient
                    )
                    < 0
                ):
                    tri = (tri[0], tri[2], tri[1])
                resolved.append((tri[0], tri[1], tri[2]))
    if resolved:
        triangles = np.vstack((triangles, np.asarray(resolved, dtype=np.intp)))
    return vertices, triangles


def marching_squares(payload: Payload, bounds: Bounds) -> Payload:
    """Extract connected zero contours from a scalar region grid.

    Parameters
    ----------
    payload
        Region with scalar values and quad topology. Invalid cells are omitted.
    bounds
        Local viewport, unused during contour extraction.

    Returns
    -------
    Payload
        Data anchors in connected paths, with no region topology or values.
        Ambiguous saddle cells use the bilinear asymptotic decider.
    """
    if payload.kind != "region" or payload.values is None or payload.values.ndim != 1:
        raise ValueError("marching_squares requires a scalar region payload")
    topology = payload.topology
    if isinstance(topology, tuple):
        rows, cols = topology
        r, c = np.mgrid[: rows - 1, : cols - 1]
        a = (r * cols + c).ravel()
        cells = np.column_stack((a, a + 1, a + cols + 1, a + cols))
    else:
        assert topology is not None
        cells = topology
    if cells.shape[1] != 4:
        raise ValueError("marching_squares requires quad cells")
    values = payload.values
    if payload.valid is not None:
        cells = cells[payload.valid[cells].all(axis=1)]
    signs = values[cells] >= 0
    cells = cells[np.any(signs, axis=1) & ~np.all(signs, axis=1)]
    locations: dict[tuple[int, int], FloatArray] = {}
    neighbours: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for cell in cells:
        crossings = []
        for i, j in zip(cell, np.roll(cell, -1), strict=True):
            a, b = values[i], values[j]
            if (a >= 0) == (b >= 0):
                continue
            key = (
                (int(i), int(i))
                if a == 0
                else (
                    (int(j), int(j))
                    if b == 0
                    else (min(int(i), int(j)), max(int(i), int(j)))
                )
            )
            scale = max(abs(a), abs(b))
            fraction = (a / scale) / (a / scale - b / scale)
            locations[key] = payload.coords[i] + fraction * (
                payload.coords[j] - payload.coords[i]
            )
            crossings.append(key)
        if len(crossings) == 4:
            f = values[cell]
            f = f / np.max(np.abs(f))
            if f[0] * f[2] - f[1] * f[3] < 0:
                crossings = crossings[1:] + crossings[:1]
        for a_key, b_key in zip(crossings[::2], crossings[1::2], strict=True):
            if a_key != b_key:
                neighbours.setdefault(a_key, []).append(b_key)
                neighbours.setdefault(b_key, []).append(a_key)
    paths = []
    while neighbours:
        start = next(
            (k for k, v in neighbours.items() if len(v) == 1), next(iter(neighbours))
        )
        path = [locations[start]]
        current = start
        while current in neighbours:
            following = neighbours[current].pop()
            if not neighbours[current]:
                del neighbours[current]
            neighbours[following].remove(current)
            if not neighbours[following]:
                del neighbours[following]
            path.append(locations[following])
            current = following
            if current == start:
                break
        paths.append(np.array(path))
    return _assemble(paths, payload.coords.shape[1])


_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(8)
_NODES = (_NODES + 1) / 2
_WEIGHTS = _WEIGHTS / 2


def _path_only(payload: Payload) -> None:
    if payload.kind != "path":
        raise ValueError(f"kind {payload.kind!r} must be path")


def _curves(payload: Payload) -> FloatArray:
    _path_only(payload)
    if len(payload.coords) % 4 or np.any(np.diff(payload.segments, axis=1) % 4):
        raise ValueError("path segments must contain four points per cubic curve")
    if payload.valid is not None and not payload.valid.all():
        raise ValueError("curve path must have no invalid samples")
    return payload.coords.reshape(-1, 4, payload.coords.shape[1])


def _assemble(
    parts: list[FloatArray], dim: int, lengths: list[int] | None = None
) -> Payload:
    if not parts:
        return Payload.empty("path", dim)
    if len(parts) == 1:
        coords = parts[0]
        segments = np.array([[0, len(coords)]], dtype=np.intp)
    else:
        sizes = [len(part) for part in parts] if lengths is None else lengths
        edges = np.concatenate(([0], np.cumsum(sizes)))
        coords = np.concatenate(parts)
        segments = np.column_stack((edges[:-1], edges[1:]))
    # Finite anchors can still overflow while constructing handles.
    build = Payload._trusted if np.isfinite(coords).all() else Payload
    return build("path", coords, segments)


@lru_cache(maxsize=128)
def _spline_factor(n: int, closed: bool) -> tuple[FloatArray, FloatArray]:
    diagonal = np.full(n, 4.0)
    diagonal[0], diagonal[-1] = (3, 3) if closed else (2, 3.5)
    off_diagonal = np.ones(n - 1)
    diagonal, off_diagonal, info = dpttrf(
        diagonal, off_diagonal, overwrite_d=True, overwrite_e=True
    )
    # These fixed, strictly diagonally dominant matrices are positive definite.
    assert info == 0
    return np.asarray(diagonal), np.asarray(off_diagonal)


def _handles(anchors: FloatArray) -> tuple[FloatArray, FloatArray]:
    n, dim = len(anchors) - 1, anchors.shape[1]
    if n == 1:
        return (2 * anchors[:1] + anchors[1:]) / 3, (anchors[:1] + 2 * anchors[1:]) / 3
    # Exact closure takes precedence over Manim's signed endpoint tolerance.
    closed = bool(
        np.array_equal(anchors[0], anchors[-1])
        or np.all(np.abs(anchors[-1] - anchors[0]) <= 1e-8 + 1e-5 * anchors[0])
    )
    if closed:
        rhs = np.empty((n, dim + 1))
        rhs[:, :dim] = 4 * anchors[:-1] + 2 * anchors[1:]
        rhs[:, dim] = 0
        rhs[[0, -1], dim] = 1
    else:
        rhs = 4 * anchors[:-1] + 2 * anchors[1:]
        rhs[0], rhs[-1] = (
            anchors[0] + 2 * anchors[1],
            (8 * anchors[-2] + anchors[-1]) / 2,
        )
    # Halving the open spline's last equation makes the matrix symmetric.
    # Only its coefficients are cached; every solve uses the current anchors.
    solved, info = dpttrs(*_spline_factor(n, closed), rhs, overwrite_b=True)
    if info < 0:
        raise ValueError(f"illegal value in {-info}-th argument of internal dpttrs")
    solved = np.asarray(solved, dtype=np.float64)
    if closed:
        y, q = solved[:, :dim], solved[:, dim, None]
        first = y - q * (y[0] + y[-1]) / (1 + q[0] + q[-1])
        second = 2 * anchors[1:] - np.roll(first, -1, axis=0)
    else:
        first = solved
        second = np.empty_like(first)
        second[:-1] = 2 * anchors[1:-1] - first[1:]
        second[-1] = (anchors[-1] + first[-1]) / 2
    return first, second


def _from_anchors(payload: Payload, *, smoothing: bool) -> Payload:
    if not len(payload.coords):
        return Payload.empty(payload.kind, payload.coords.shape[1])
    _path_only(payload)
    dim = payload.coords.shape[1]
    parts: list[FloatArray] = []
    with np.errstate(all="ignore"):
        for start, stop in payload.segments:
            anchors = payload.coords[start:stop]
            if len(anchors) == 1:
                parts.append(np.repeat(anchors, 4, axis=0))
                continue
            curves = np.empty((len(anchors) - 1, 4, dim))
            curves[:, 0], curves[:, 3] = anchors[:-1], anchors[1:]
            if smoothing:
                curves[:, 1], curves[:, 2] = _handles(anchors)
            else:
                curves[:, 1] = (2 * anchors[:-1] + anchors[1:]) / 3
                curves[:, 2] = (anchors[:-1] + 2 * anchors[1:]) / 3
            parts.append(curves.reshape(-1, dim))
    return _assemble(parts, dim)


def corners(payload: Payload, bounds: Bounds) -> Payload:
    """Convert anchor segments to straight cubic Bézier curves.

    Parameters
    ----------
    payload
        Path anchors in local coordinates.
    bounds
        Local clip region, unused by this stage.

    Returns
    -------
    Payload
        Cubic path with four points per curve and no validity mask.
    """
    return _from_anchors(payload, smoothing=False)


def clip_region(
    upper: FloatArray,
    lower: FloatArray,
    bounds: Bounds,
    *,
    clip_x: bool = True,
    clip_y: bool = True,
) -> Payload:
    """Close paired boundary polylines, clipping without opening their fill.

    Parameters
    ----------
    upper, lower
        Boundary points with matching x coordinates, in traversal order.
    bounds
        Viewport in local coordinates.
    clip_x, clip_y
        Restrict x and clamp each boundary's y independently.

    Returns
    -------
    Payload
        Closed cubic paths, split at crossings and invisible stretches.
        Unlike Manim's area polygon, clipping preserves the filled interior.
    """
    dim = upper.shape[1]
    if len(upper) < 2:
        return Payload.empty("path", dim)
    parameter = np.arange(len(upper), dtype=float)
    events = [parameter]
    differences = [upper[:, 1] - lower[:, 1]]
    if clip_x:
        differences.extend(
            upper[:, 0] - edge for edge in (bounds.lower[0], bounds.upper[0])
        )
    if clip_y:
        differences.extend(
            boundary[:, 1] - edge
            for boundary in (upper, lower)
            for edge in (bounds.lower[1], bounds.upper[1])
        )
    for values in differences:
        crossing = ((values[:-1] < 0) & (values[1:] > 0)) | (
            (values[:-1] > 0) & (values[1:] < 0)
        )
        a, b = values[:-1][crossing], values[1:][crossing]
        scale = np.maximum(np.abs(a), np.abs(b))
        a, b = a / scale, b / scale
        events.append(parameter[:-1][crossing] + a / (a - b))
    grid = np.unique(np.concatenate(events))
    a, b = (
        np.column_stack([np.interp(grid, parameter, p[:, i]) for i in range(dim)])
        for p in (upper, lower)
    )
    middle_x = a[:-1, 0] / 2 + a[1:, 0] / 2
    keep = (
        (middle_x >= bounds.lower[0]) & (middle_x <= bounds.upper[0])
        if clip_x
        else np.ones(len(grid) - 1, dtype=bool)
    )
    if clip_x:
        a[:, 0] = np.clip(a[:, 0], bounds.lower[0], bounds.upper[0])
        b[:, 0] = a[:, 0]
    if clip_y:
        middle_a = a[:-1, 1] / 2 + a[1:, 1] / 2
        middle_b = b[:-1, 1] / 2 + b[1:, 1] / 2
        keep &= (np.maximum(middle_a, middle_b) >= bounds.lower[1]) & (
            np.minimum(middle_a, middle_b) <= bounds.upper[1]
        )
        a[:, 1] = np.clip(a[:, 1], bounds.lower[1], bounds.upper[1])
        b[:, 1] = np.clip(b[:, 1], bounds.lower[1], bounds.upper[1])
    # Each lobe has consistent winding; opposite lobes cannot cancel its fill.
    delta = a[:, 1] - b[:, 1]
    signs = np.sign(delta[:-1] + delta[1:])
    cuts = np.r_[
        0,
        np.flatnonzero((signs[1:] != signs[:-1]) | (keep[1:] != keep[:-1])) + 1,
        len(grid) - 1,
    ]
    parts = []
    for start, stop in pairwise(cuts):
        if not keep[start] or (signs[start] == 0 and np.any(signs[keep])):
            continue
        top, bottom = a[start : stop + 1], b[start : stop + 1]
        if signs[start] < 0:
            top, bottom = bottom, top
        parts.append(np.concatenate((top, bottom[::-1], top[:1])))
    return corners(_assemble(parts, dim), bounds)


def smooth(payload: Payload, bounds: Bounds) -> Payload:
    """Fit Manim's smooth open or closed cubic spline to each anchor segment.

    Parameters
    ----------
    payload
        Path anchors in local coordinates.
    bounds
        Local clip region, unused by this stage.

    Returns
    -------
    Payload
        Cubic path with four points per curve and no validity mask.
    """
    return _from_anchors(payload, smoothing=True)


def _split(curves: FloatArray, t: FloatArray) -> tuple[FloatArray, FloatArray]:
    alpha = t[:, None, None]
    first = (1 - alpha) * curves[:, :-1] + alpha * curves[:, 1:]
    second = (1 - alpha) * first[:, :-1] + alpha * first[:, 1:]
    point = (1 - alpha) * second[:, :1] + alpha * second[:, 1:]
    return (
        np.concatenate((curves[:, :1], first[:, :1], second[:, :1], point), axis=1),
        np.concatenate((point, second[:, 1:], first[:, 2:], curves[:, 3:]), axis=1),
    )


def _restrict(curves: FloatArray, lo: FloatArray, hi: FloatArray) -> FloatArray:
    left, _ = _split(curves, hi)
    fraction = np.divide(lo, hi, out=np.zeros_like(lo), where=hi != 0)
    _, result = _split(left, fraction)
    return result


def _crossings(curve: FloatArray, box: Box) -> tuple[FloatArray, FloatArray]:
    if isinstance(box, _Disk):
        p = curve[:, : len(box.lower)] / box.upper
        disk_coefficients = np.array(
            [
                p[0],
                3 * (p[1] - p[0]),
                3 * (p[2] - 2 * p[1] + p[0]),
                p[3] - 3 * p[2] + 3 * p[1] - p[0],
            ]
        )
        polynomial = np.polynomial.polynomial.polyadd(
            np.polynomial.polynomial.polymul(
                disk_coefficients[:, 0], disk_coefficients[:, 0]
            ),
            np.polynomial.polynomial.polymul(
                disk_coefficients[:, 1], disk_coefficients[:, 1]
            ),
        )
        polynomial[0] -= 1
        solutions = np.polynomial.polynomial.polyroots(
            np.polynomial.polynomial.polytrim(polynomial, tol=1e-14)
        )
        times = np.unique(
            [
                0.0,
                1.0,
                *(
                    float(r.real)
                    for r in solutions
                    if abs(r.imag) <= 1e-9 and 0 < r.real < 1
                ),
            ]
        )
        return times, np.full((len(times), len(box.lower)), np.nan)
    roots: list[float] = [0.0, 1.0]
    sides: list[tuple[int, float]] = [(-1, 0.0), (-1, 0.0)]
    scale = max(
        float(np.max(np.abs(curve[:, : len(box.lower)]))),
        float(np.max(np.abs(box.lower))),
        float(np.max(np.abs(box.upper))),
        1.0,
    )
    points = curve[:, : len(box.lower)] / scale
    for axis in range(len(box.lower)):
        p = points[:, axis]
        coefficients = [
            p[0],
            3 * (p[1] - p[0]),
            3 * (p[2] - 2 * p[1] + p[0]),
            p[3] - 3 * p[2] + 3 * p[1] - p[0],
        ]
        for bound in (box.lower[axis], box.upper[axis]):
            coefficients[0] = p[0] - bound / scale
            # Roundoff in a lower-degree curve must not scale the companion matrix.
            tolerance = 1e-14 * max(map(abs, coefficients))
            degree = 3
            while degree > 0 and abs(coefficients[degree]) <= tolerance:
                degree -= 1
            solutions = np.polynomial.polynomial.polyroots(coefficients[: degree + 1])
            for root in solutions:
                if abs(root.imag) <= 1e-10 and 0 < root.real < 1:
                    roots.append(float(root.real))
                    sides.append((axis, float(bound)))
    times, inverse = np.unique(roots, return_inverse=True)
    crossing = np.full((len(times), len(box.lower)), np.nan)
    for index, (axis, bound) in zip(inverse, sides, strict=True):
        if axis >= 0:
            crossing[index, axis] = bound
    return times, crossing


def _clip_curve(curve: FloatArray, box: Box) -> tuple[list[FloatArray], bool, bool]:
    dim = curve.shape[1]
    if box.contains(curve).all():
        return [curve], True, True
    xy = curve[:, : len(box.lower)]
    if ((xy < box.lower).all(axis=0) | (xy > box.upper).all(axis=0)).any():
        return [], False, False
    # Subdivision keeps roots well-conditioned even beside very large pole values.
    if np.max(np.ptp(xy, axis=0) / (box.upper - box.lower)) > 1e5:
        left, right = _split(curve[None], np.array([0.5]))
        lp, ls, le = _clip_curve(left[0], box)
        rp, rs, re = _clip_curve(right[0], box)
        if le and rs:
            lp[-1] = np.concatenate((lp[-1], rp[0]))
            rp = rp[1:]
        return lp + rp, ls, re
    times, crossing = _crossings(curve, box)
    a, b = times[:-1], times[1:]
    if len(times) == 3:
        left, right = _split(curve[None], times[1:2])
        pieces = np.concatenate((left, right))
    else:
        pieces = _restrict(np.repeat(curve[None], len(a), axis=0), a, b)
    pieces[:, 0, : len(box.lower)] = np.where(
        np.isfinite(crossing[:-1]), crossing[:-1], pieces[:, 0, : len(box.lower)]
    )
    pieces[:, 3, : len(box.lower)] = np.where(
        np.isfinite(crossing[1:]), crossing[1:], pieces[:, 3, : len(box.lower)]
    )
    mid = (pieces[:, 0] + 3 * pieces[:, 1] + 3 * pieces[:, 2] + pieces[:, 3]) / 8
    keep = box.contains(mid)
    changes = np.diff(np.concatenate(([False], keep, [False])).astype(np.intp))
    parts = [
        pieces[start:stop].reshape(-1, dim)
        for start, stop in zip(
            np.flatnonzero(changes == 1), np.flatnonzero(changes == -1), strict=True
        )
    ]
    return parts, bool(keep[0]), bool(keep[-1])


def _clip_path(payload: Payload, box: Box) -> Payload:
    curves = _curves(payload)
    dim = payload.coords.shape[1]
    inside = box.contains(payload.coords)
    if inside.all():
        return Payload._trusted("path", payload.coords, payload.segments)
    outside = payload.coords[~inside, : len(box.lower)]
    tolerance = 8 * np.spacing(np.maximum(np.abs(box.lower), np.abs(box.upper)))
    if (
        type(box) is Box
        and (
            (outside >= box.lower - tolerance) & (outside <= box.upper + tolerance)
        ).all()
    ):
        # An inverse/forward round trip at the viewport edge need not be bit-exact.
        coords = payload.coords.copy()
        coords[~inside, : len(box.lower)] = np.clip(outside, box.lower, box.upper)
        return Payload._trusted("path", coords, payload.segments)
    inside = inside.reshape(-1, 4).all(axis=1)
    parts: list[FloatArray] = []
    lengths: list[int] = []

    def append(points: FloatArray, *, join: bool) -> None:
        parts.append(points)
        if join and lengths:
            lengths[-1] += len(points)
        else:
            lengths.append(len(points))

    with np.errstate(all="ignore"):
        for start, stop in payload.segments // 4:
            cursor = int(start)
            connected = False
            for index in np.flatnonzero(~inside[start:stop]) + start:
                if cursor < index:
                    append(curves[cursor:index].reshape(-1, dim), join=connected)
                    connected = True
                pieces, reaches_start, reaches_end = _clip_curve(curves[index], box)
                for j, piece in enumerate(pieces):
                    append(piece, join=j == 0 and reaches_start and connected)
                connected = reaches_end
                cursor = int(index) + 1
            if cursor < stop:
                append(curves[cursor:stop].reshape(-1, dim), join=connected)
    return _assemble(parts, dim, lengths)


def _clip_with_parameters(payload: Payload, box: Box) -> tuple[Payload, FloatArray]:
    """Clip once, retaining each cubic's interval in the original traversal."""
    curves = _curves(payload)
    count = len(curves)
    inside = box.contains(payload.coords).reshape(-1, 4).all(axis=1)
    parts: list[FloatArray] = []
    intervals: list[tuple[float, float]] = []
    for i, curve in enumerate(curves):
        if inside[i]:
            parts.append(curve)
            intervals.append((float(i), float(i + 1)))
            continue
        xy = curve[:, : len(box.lower)]
        if ((xy < box.lower).all(axis=0) | (xy > box.upper).all(axis=0)).any():
            continue
        times, crossing = _crossings(curve, box)
        a, b = times[:-1], times[1:]
        pieces = _restrict(np.repeat(curve[None], len(a), axis=0), a, b)
        pieces[:, 0, : len(box.lower)] = np.where(
            np.isfinite(crossing[:-1]), crossing[:-1], pieces[:, 0, : len(box.lower)]
        )
        pieces[:, 3, : len(box.lower)] = np.where(
            np.isfinite(crossing[1:]), crossing[1:], pieces[:, 3, : len(box.lower)]
        )
        middle = (pieces[:, 0] + 3 * pieces[:, 1] + 3 * pieces[:, 2] + pieces[:, 3]) / 8
        for j in np.flatnonzero(box.contains(middle)):
            parts.append(pieces[j])
            intervals.append((i + float(a[j]), i + float(b[j])))
    return (
        _assemble(parts, payload.coords.shape[1]),
        np.asarray(intervals, dtype=float).reshape(-1, 2) / max(1, count),
    )


def clip(payload: Payload, bounds: Bounds) -> Payload:
    """Clip final cubic paths, points or whole region cells to a local box.

    Parameters
    ----------
    payload
        Cubic path, point set or region geometry.
    bounds
        Region whose bounding box supplies the clip rectangle.

    Returns
    -------
    Payload
        Clipped geometry; point and region coordinates retain their indices.
    """
    if not len(payload.coords):
        return Payload.empty(payload.kind, payload.coords.shape[1])
    box = bounds if isinstance(bounds, Box) else Box(bounds.lower, bounds.upper)
    if payload.kind == "path":
        return _clip_path(payload, box)
    valid = box.contains(payload.coords)
    if payload.valid is not None:
        valid &= payload.valid
    if payload.kind == "points":
        return Payload._trusted(
            "points",
            payload.coords,
            payload.segments,
            valid=valid,
            values=payload.values,
        )
    topology = payload.topology
    if isinstance(topology, tuple):
        rows, cols = topology
        r, c = np.meshgrid(np.arange(rows - 1), np.arange(cols - 1), indexing="ij")
        first = (r * cols + c).ravel()
        cells = np.column_stack((first, first + 1, first + cols + 1, first + cols))
    else:
        assert topology is not None
        cells = topology
    cells = cells[valid[cells].all(axis=1)]
    return Payload._trusted(
        "region", payload.coords, payload.segments, cells, payload.valid, payload.values
    )


def _lengths(curves: FloatArray, end: FloatArray | None = None) -> FloatArray:
    t = _NODES[None, :, None]
    if end is not None:
        t = t * end[:, None, None]
    delta = 3 * np.diff(curves, axis=1)
    derivative = (
        (1 - t) ** 2 * delta[:, :1]
        + 2 * (1 - t) * t * delta[:, 1:2]
        + t**2 * delta[:, 2:]
    )
    result = np.linalg.norm(derivative, axis=2) @ _WEIGHTS
    return result if end is None else result * end


def arc_length(payload: Payload) -> FloatArray:
    """Measure each cubic path segment with eight-point Gauss-Legendre quadrature.

    Parameters
    ----------
    payload
        A cubic path in local coordinates.

    Returns
    -------
    FloatArray
        One arc length per segment.
    """
    if not len(payload.coords):
        return np.empty(0)
    curves = _curves(payload)
    with np.errstate(all="ignore"):
        lengths = _lengths(curves)
        return np.array(
            [
                np.sum(lengths[start // 4 : stop // 4])
                for start, stop in payload.segments
            ]
        )


def _arc_parameters(
    curves: FloatArray, lengths: FloatArray, positions: FloatArray
) -> tuple[IntArray, FloatArray]:
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    indices = np.minimum(
        np.searchsorted(cumulative, positions, side="right") - 1, len(curves) - 1
    )
    indices = np.maximum(indices, 0)
    target = positions - cumulative[indices]
    lo, hi = np.zeros(len(positions)), np.ones(len(positions))
    selected = curves[indices]
    sizes = lengths[indices]
    endpoints = (target <= 0) | (target >= sizes - 1e-12 * np.maximum(sizes, 1.0))
    result = np.clip(np.divide(target, sizes, out=lo.copy(), where=sizes > 0), 0, 1)
    delta = 3 * np.diff(selected, axis=1)
    for _ in range(40):
        error = _lengths(selected, result) - target
        done = endpoints | (np.abs(error) <= 1e-12 * np.maximum(sizes, 1.0))
        if done.all():
            break
        lo = np.where(error < 0, result, lo)
        hi = np.where(error >= 0, result, hi)
        t = result[:, None]
        speed = np.linalg.norm(
            (1 - t) ** 2 * delta[:, 0]
            + 2 * (1 - t) * t * delta[:, 1]
            + t**2 * delta[:, 2],
            axis=1,
        )
        candidate = result - np.divide(
            error, speed, out=np.zeros_like(error), where=speed > 0
        )
        candidate = np.where(
            (candidate > lo) & (candidate < hi), candidate, (lo + hi) / 2
        )
        result = np.where(done, result, candidate)
    result[target <= 0] = 0
    result[target >= sizes - 1e-12 * np.maximum(sizes, 1.0)] = 1
    return indices, result


def dash(
    payload: Payload, bounds: Bounds, *, on: float, off: float, phase: float = 0.0
) -> Payload:
    """Split cubic paths into dashes measured by local arc length.

    Parameters
    ----------
    payload
        Cubic path geometry.
    bounds
        Local clip region, unused by this stage.
    on, off
        Finite dash and gap lengths; on is positive and off nonnegative.
    phase
        Finite distance into the pattern, restarted at every input segment.

    Returns
    -------
    Payload
        One segment per dash, preserving the cubic geometry.
    """
    for name, value in (("on", on), ("off", off), ("phase", phase)):
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError(f"{name} must be a real number")
    if not np.isfinite(on) or on <= 0:
        raise ValueError("on must be finite and positive")
    if not np.isfinite(off) or off < 0:
        raise ValueError("off must be finite and nonnegative")
    if not np.isfinite(phase):
        raise ValueError("phase must be finite")
    if not len(payload.coords):
        return Payload.empty(payload.kind, payload.coords.shape[1])
    curves = _curves(payload)
    if off == 0:
        return Payload._trusted("path", payload.coords, payload.segments)
    parts: list[FloatArray] = []
    dim = payload.coords.shape[1]
    with np.errstate(all="ignore"):
        chord = np.linalg.norm(curves[:, 3] - curves[:, 0], axis=1)
        polygon = np.linalg.norm(np.diff(curves, axis=1), axis=2).sum(axis=1)
        # These bound the true arc length; dense paths need no quadrature.
        lengths = (
            (chord + polygon) / 2
            if np.sum(polygon - chord) <= 1e-4
            else _lengths(curves)
        )
        period = on + off
        offset = phase % period
        for start, stop in payload.segments // 4:
            segment = curves[start:stop]
            sizes = lengths[start:stop]
            total = float(np.sum(sizes))
            if total == 0:
                if offset < on:
                    parts.append(segment.reshape(-1, dim).copy())
                continue
            count = int(np.ceil((total + offset) / period))
            begins = np.arange(count) * period - offset
            ends = begins + on
            keep = (begins < total) & (ends > 0)
            begins, ends = np.maximum(begins[keep], 0), np.minimum(ends[keep], total)
            # Quadrature roundoff must not turn an endpoint into another dash.
            keep = begins < total - 8 * np.finfo(np.float64).eps * total
            begins, ends = begins[keep], ends[keep]
            if not len(begins):
                continue
            indices, times = _arc_parameters(
                segment, sizes, np.column_stack((begins, ends)).ravel()
            )
            first, last = indices[::2], indices[1::2]
            counts = last - first + 1
            dash_ids = np.repeat(np.arange(len(first)), counts)
            offsets = np.r_[0, np.cumsum(counts)]
            curve_ids = (
                np.arange(offsets[-1])
                - np.repeat(offsets[:-1], counts)
                + first[dash_ids]
            )
            low, high = np.zeros(len(curve_ids)), np.ones(len(curve_ids))
            low[offsets[:-1]], high[offsets[1:] - 1] = times[::2], times[1::2]
            divided_curves = segment[curve_ids].copy()
            boundary = (low > 0) | (high < 1)
            divided_curves[boundary] = _restrict(
                divided_curves[boundary], low[boundary], high[boundary]
            )
            divided = divided_curves.reshape(-1, dim)
            parts.extend(np.split(divided, offsets[1:-1] * 4))
    return _assemble(parts, dim)


def densify(payload: Payload, bounds: Bounds, *, pieces: int) -> Payload:
    """Subdivide every cubic into equal parameter spans by de Casteljau.

    Parameters
    ----------
    payload
        Cubic path geometry.
    bounds
        Local clip region, unused by this stage.
    pieces
        Positive integer number of output curves per input curve.

    Returns
    -------
    Payload
        The same path geometry with a denser control lattice.
    """
    if not isinstance(pieces, int) or isinstance(pieces, bool):
        raise TypeError("pieces must be an int")
    if pieces < 1:
        raise ValueError("pieces must be at least 1")
    if not len(payload.coords):
        return Payload.empty(payload.kind, payload.coords.shape[1])
    curves = _curves(payload)
    with np.errstate(all="ignore"):
        lo = np.tile(np.arange(pieces) / pieces, len(curves))
        hi = np.tile(np.arange(1, pieces + 1) / pieces, len(curves))
        divided = _restrict(np.repeat(curves, pieces, axis=0), lo, hi)
    return Payload(
        "path", divided.reshape(-1, payload.coords.shape[1]), payload.segments * pieces
    )


def resample_pair(payload: Payload, target: Payload) -> tuple[Payload, Payload]:
    """Subdivide two paths at the union of their anchors' arc fractions.

    Parameters
    ----------
    payload
        Source cubic geometry, with nondegenerate continuous pieces.
    target
        Second cubic path with the same number of continuous pieces.

    Returns
    -------
    tuple of Payload
        Both paths with matching lattices, preserving their original geometry.

    Raises
    ------
    ValueError
        If piece counts differ or a curve is degenerate.
    """
    source_curves, target_curves = _curves(payload), _curves(target)
    if len(payload.segments) != len(target.segments) or not len(source_curves):
        raise ValueError("Morph paths must have the same nonzero number of pieces")
    source_parts, target_parts = [], []
    for (a, b), (c, d) in zip(payload.segments // 4, target.segments // 4, strict=True):
        curves, lattice = source_curves[a:b], target_curves[c:d]
        lengths, target_lengths = _lengths(curves), _lengths(lattice)
        if np.any(lengths <= 1e-12) or np.any(target_lengths <= 1e-12):
            raise ValueError("Morph cannot resample degenerate or repeated points")
        cumulative = np.r_[0.0, np.cumsum(lengths)]
        target_cumulative = np.r_[0.0, np.cumsum(target_lengths)]
        # Merge quadrature roundoff at shared anchors without tiny extra curves.
        fractions = np.unique(
            np.round(
                np.r_[
                    cumulative / cumulative[-1],
                    target_cumulative / target_cumulative[-1],
                ],
                9,
            )
        ).astype(np.float64)
        source_parts.append(_subdivide_at_fractions(curves, lengths, fractions))
        target_parts.append(_subdivide_at_fractions(lattice, target_lengths, fractions))
    return (
        _assemble(source_parts, payload.coords.shape[1]),
        _assemble(target_parts, target.coords.shape[1]),
    )


def _subdivide_at_fractions(
    curves: FloatArray, lengths: FloatArray, fractions: FloatArray
) -> FloatArray:
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    positions = fractions * cumulative[-1]
    # Keep original joins exact despite rounding the shared fractions.
    positions[np.searchsorted(fractions, np.round(cumulative / cumulative[-1], 9))] = (
        cumulative
    )
    indices, parameters = _arc_parameters(curves, lengths, positions)
    upper = np.where(indices[1:] == indices[:-1], parameters[1:], 1.0)
    return _restrict(curves[indices[:-1]], parameters[:-1], upper).reshape(
        -1, curves.shape[2]
    )


def _cut_polygon(points: FloatArray, axis: int, edge: float, above: bool) -> FloatArray:
    if not len(points):
        return points
    result = []
    for a, b in zip(points, np.roll(points, -1, axis=0), strict=True):
        inside_a = a[axis] >= edge if above else a[axis] <= edge
        inside_b = b[axis] >= edge if above else b[axis] <= edge
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a + (edge - a[axis]) / (b[axis] - a[axis]) * (b - a))
    return np.asarray(result, float).reshape(-1, points.shape[1])


def filled_marching_squares(
    X: FloatArray, Y: FloatArray, Z: FloatArray, lo: float, hi: float
) -> list[FloatArray]:
    """Cut grid quadrilaterals into a scalar band using edge interpolation.

    Parameters
    ----------
    X, Y, Z
        Matching two-dimensional coordinate and scalar grids.
    lo, hi
        Lower and upper band edges.

    Returns
    -------
    list of ndarray
        Closed data polygons, one per nonempty finite cell.
    """
    if X.ndim != 2 or X.shape != Y.shape or X.shape != Z.shape:
        raise ValueError("X, Y and Z must be matching two-dimensional grids")
    if not np.isfinite([lo, hi]).all() or hi <= lo:
        raise ValueError("band edges must be finite and increasing")
    grid = np.stack((X, Y, Z), axis=-1)
    cells = np.stack(
        (grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]), axis=-2
    ).reshape(-1, 4, 3)
    polygons = []
    for cell in cells:
        if (
            not np.isfinite(cell).all()
            or cell[:, 2].max() < lo
            or cell[:, 2].min() >= hi
        ):
            continue
        piece = _cut_polygon(_cut_polygon(cell, 2, lo, True), 2, hi, False)
        if len(piece) >= 3:
            polygons.append(np.vstack((piece[:, :2], piece[:1, :2])))
    return polygons


# Classic Lorensen-Cline cases (scikit-image lookup data, BSD-3-Clause).
# fmt: off
_MC_TRIANGLES = np.array([
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 8, 3, 9, 8, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, 1, 2, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 2, 10, 0, 2, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [2, 8, 3, 2, 10, 8, 10, 9, 8, -1, -1, -1, -1, -1, -1, -1],
    [3, 11, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 11, 2, 8, 11, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 9, 0, 2, 3, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 11, 2, 1, 9, 11, 9, 8, 11, -1, -1, -1, -1, -1, -1, -1],
    [3, 10, 1, 11, 10, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 10, 1, 0, 8, 10, 8, 11, 10, -1, -1, -1, -1, -1, -1, -1],
    [3, 9, 0, 3, 11, 9, 11, 10, 9, -1, -1, -1, -1, -1, -1, -1],
    [9, 8, 10, 10, 8, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 7, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 3, 0, 7, 3, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 1, 9, 8, 4, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 1, 9, 4, 7, 1, 7, 3, 1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, 8, 4, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 4, 7, 3, 0, 4, 1, 2, 10, -1, -1, -1, -1, -1, -1, -1],
    [9, 2, 10, 9, 0, 2, 8, 4, 7, -1, -1, -1, -1, -1, -1, -1],
    [2, 10, 9, 2, 9, 7, 2, 7, 3, 7, 9, 4, -1, -1, -1, -1],
    [8, 4, 7, 3, 11, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [11, 4, 7, 11, 2, 4, 2, 0, 4, -1, -1, -1, -1, -1, -1, -1],
    [9, 0, 1, 8, 4, 7, 2, 3, 11, -1, -1, -1, -1, -1, -1, -1],
    [4, 7, 11, 9, 4, 11, 9, 11, 2, 9, 2, 1, -1, -1, -1, -1],
    [3, 10, 1, 3, 11, 10, 7, 8, 4, -1, -1, -1, -1, -1, -1, -1],
    [1, 11, 10, 1, 4, 11, 1, 0, 4, 7, 11, 4, -1, -1, -1, -1],
    [4, 7, 8, 9, 0, 11, 9, 11, 10, 11, 0, 3, -1, -1, -1, -1],
    [4, 7, 11, 4, 11, 9, 9, 11, 10, -1, -1, -1, -1, -1, -1, -1],
    [9, 5, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 5, 4, 0, 8, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 5, 4, 1, 5, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [8, 5, 4, 8, 3, 5, 3, 1, 5, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, 9, 5, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 0, 8, 1, 2, 10, 4, 9, 5, -1, -1, -1, -1, -1, -1, -1],
    [5, 2, 10, 5, 4, 2, 4, 0, 2, -1, -1, -1, -1, -1, -1, -1],
    [2, 10, 5, 3, 2, 5, 3, 5, 4, 3, 4, 8, -1, -1, -1, -1],
    [9, 5, 4, 2, 3, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 11, 2, 0, 8, 11, 4, 9, 5, -1, -1, -1, -1, -1, -1, -1],
    [0, 5, 4, 0, 1, 5, 2, 3, 11, -1, -1, -1, -1, -1, -1, -1],
    [2, 1, 5, 2, 5, 8, 2, 8, 11, 4, 8, 5, -1, -1, -1, -1],
    [10, 3, 11, 10, 1, 3, 9, 5, 4, -1, -1, -1, -1, -1, -1, -1],
    [4, 9, 5, 0, 8, 1, 8, 10, 1, 8, 11, 10, -1, -1, -1, -1],
    [5, 4, 0, 5, 0, 11, 5, 11, 10, 11, 0, 3, -1, -1, -1, -1],
    [5, 4, 8, 5, 8, 10, 10, 8, 11, -1, -1, -1, -1, -1, -1, -1],
    [9, 7, 8, 5, 7, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 3, 0, 9, 5, 3, 5, 7, 3, -1, -1, -1, -1, -1, -1, -1],
    [0, 7, 8, 0, 1, 7, 1, 5, 7, -1, -1, -1, -1, -1, -1, -1],
    [1, 5, 3, 3, 5, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 7, 8, 9, 5, 7, 10, 1, 2, -1, -1, -1, -1, -1, -1, -1],
    [10, 1, 2, 9, 5, 0, 5, 3, 0, 5, 7, 3, -1, -1, -1, -1],
    [8, 0, 2, 8, 2, 5, 8, 5, 7, 10, 5, 2, -1, -1, -1, -1],
    [2, 10, 5, 2, 5, 3, 3, 5, 7, -1, -1, -1, -1, -1, -1, -1],
    [7, 9, 5, 7, 8, 9, 3, 11, 2, -1, -1, -1, -1, -1, -1, -1],
    [9, 5, 7, 9, 7, 2, 9, 2, 0, 2, 7, 11, -1, -1, -1, -1],
    [2, 3, 11, 0, 1, 8, 1, 7, 8, 1, 5, 7, -1, -1, -1, -1],
    [11, 2, 1, 11, 1, 7, 7, 1, 5, -1, -1, -1, -1, -1, -1, -1],
    [9, 5, 8, 8, 5, 7, 10, 1, 3, 10, 3, 11, -1, -1, -1, -1],
    [5, 7, 0, 5, 0, 9, 7, 11, 0, 1, 0, 10, 11, 10, 0, -1],
    [11, 10, 0, 11, 0, 3, 10, 5, 0, 8, 0, 7, 5, 7, 0, -1],
    [11, 10, 5, 7, 11, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [10, 6, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, 5, 10, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 0, 1, 5, 10, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 8, 3, 1, 9, 8, 5, 10, 6, -1, -1, -1, -1, -1, -1, -1],
    [1, 6, 5, 2, 6, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 6, 5, 1, 2, 6, 3, 0, 8, -1, -1, -1, -1, -1, -1, -1],
    [9, 6, 5, 9, 0, 6, 0, 2, 6, -1, -1, -1, -1, -1, -1, -1],
    [5, 9, 8, 5, 8, 2, 5, 2, 6, 3, 2, 8, -1, -1, -1, -1],
    [2, 3, 11, 10, 6, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [11, 0, 8, 11, 2, 0, 10, 6, 5, -1, -1, -1, -1, -1, -1, -1],
    [0, 1, 9, 2, 3, 11, 5, 10, 6, -1, -1, -1, -1, -1, -1, -1],
    [5, 10, 6, 1, 9, 2, 9, 11, 2, 9, 8, 11, -1, -1, -1, -1],
    [6, 3, 11, 6, 5, 3, 5, 1, 3, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 11, 0, 11, 5, 0, 5, 1, 5, 11, 6, -1, -1, -1, -1],
    [3, 11, 6, 0, 3, 6, 0, 6, 5, 0, 5, 9, -1, -1, -1, -1],
    [6, 5, 9, 6, 9, 11, 11, 9, 8, -1, -1, -1, -1, -1, -1, -1],
    [5, 10, 6, 4, 7, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 3, 0, 4, 7, 3, 6, 5, 10, -1, -1, -1, -1, -1, -1, -1],
    [1, 9, 0, 5, 10, 6, 8, 4, 7, -1, -1, -1, -1, -1, -1, -1],
    [10, 6, 5, 1, 9, 7, 1, 7, 3, 7, 9, 4, -1, -1, -1, -1],
    [6, 1, 2, 6, 5, 1, 4, 7, 8, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 5, 5, 2, 6, 3, 0, 4, 3, 4, 7, -1, -1, -1, -1],
    [8, 4, 7, 9, 0, 5, 0, 6, 5, 0, 2, 6, -1, -1, -1, -1],
    [7, 3, 9, 7, 9, 4, 3, 2, 9, 5, 9, 6, 2, 6, 9, -1],
    [3, 11, 2, 7, 8, 4, 10, 6, 5, -1, -1, -1, -1, -1, -1, -1],
    [5, 10, 6, 4, 7, 2, 4, 2, 0, 2, 7, 11, -1, -1, -1, -1],
    [0, 1, 9, 4, 7, 8, 2, 3, 11, 5, 10, 6, -1, -1, -1, -1],
    [9, 2, 1, 9, 11, 2, 9, 4, 11, 7, 11, 4, 5, 10, 6, -1],
    [8, 4, 7, 3, 11, 5, 3, 5, 1, 5, 11, 6, -1, -1, -1, -1],
    [5, 1, 11, 5, 11, 6, 1, 0, 11, 7, 11, 4, 0, 4, 11, -1],
    [0, 5, 9, 0, 6, 5, 0, 3, 6, 11, 6, 3, 8, 4, 7, -1],
    [6, 5, 9, 6, 9, 11, 4, 7, 9, 7, 11, 9, -1, -1, -1, -1],
    [10, 4, 9, 6, 4, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 10, 6, 4, 9, 10, 0, 8, 3, -1, -1, -1, -1, -1, -1, -1],
    [10, 0, 1, 10, 6, 0, 6, 4, 0, -1, -1, -1, -1, -1, -1, -1],
    [8, 3, 1, 8, 1, 6, 8, 6, 4, 6, 1, 10, -1, -1, -1, -1],
    [1, 4, 9, 1, 2, 4, 2, 6, 4, -1, -1, -1, -1, -1, -1, -1],
    [3, 0, 8, 1, 2, 9, 2, 4, 9, 2, 6, 4, -1, -1, -1, -1],
    [0, 2, 4, 4, 2, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [8, 3, 2, 8, 2, 4, 4, 2, 6, -1, -1, -1, -1, -1, -1, -1],
    [10, 4, 9, 10, 6, 4, 11, 2, 3, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 2, 2, 8, 11, 4, 9, 10, 4, 10, 6, -1, -1, -1, -1],
    [3, 11, 2, 0, 1, 6, 0, 6, 4, 6, 1, 10, -1, -1, -1, -1],
    [6, 4, 1, 6, 1, 10, 4, 8, 1, 2, 1, 11, 8, 11, 1, -1],
    [9, 6, 4, 9, 3, 6, 9, 1, 3, 11, 6, 3, -1, -1, -1, -1],
    [8, 11, 1, 8, 1, 0, 11, 6, 1, 9, 1, 4, 6, 4, 1, -1],
    [3, 11, 6, 3, 6, 0, 0, 6, 4, -1, -1, -1, -1, -1, -1, -1],
    [6, 4, 8, 11, 6, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [7, 10, 6, 7, 8, 10, 8, 9, 10, -1, -1, -1, -1, -1, -1, -1],
    [0, 7, 3, 0, 10, 7, 0, 9, 10, 6, 7, 10, -1, -1, -1, -1],
    [10, 6, 7, 1, 10, 7, 1, 7, 8, 1, 8, 0, -1, -1, -1, -1],
    [10, 6, 7, 10, 7, 1, 1, 7, 3, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 6, 1, 6, 8, 1, 8, 9, 8, 6, 7, -1, -1, -1, -1],
    [2, 6, 9, 2, 9, 1, 6, 7, 9, 0, 9, 3, 7, 3, 9, -1],
    [7, 8, 0, 7, 0, 6, 6, 0, 2, -1, -1, -1, -1, -1, -1, -1],
    [7, 3, 2, 6, 7, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [2, 3, 11, 10, 6, 8, 10, 8, 9, 8, 6, 7, -1, -1, -1, -1],
    [2, 0, 7, 2, 7, 11, 0, 9, 7, 6, 7, 10, 9, 10, 7, -1],
    [1, 8, 0, 1, 7, 8, 1, 10, 7, 6, 7, 10, 2, 3, 11, -1],
    [11, 2, 1, 11, 1, 7, 10, 6, 1, 6, 7, 1, -1, -1, -1, -1],
    [8, 9, 6, 8, 6, 7, 9, 1, 6, 11, 6, 3, 1, 3, 6, -1],
    [0, 9, 1, 11, 6, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [7, 8, 0, 7, 0, 6, 3, 11, 0, 11, 6, 0, -1, -1, -1, -1],
    [7, 11, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [7, 6, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 0, 8, 11, 7, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 1, 9, 11, 7, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [8, 1, 9, 8, 3, 1, 11, 7, 6, -1, -1, -1, -1, -1, -1, -1],
    [10, 1, 2, 6, 11, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, 3, 0, 8, 6, 11, 7, -1, -1, -1, -1, -1, -1, -1],
    [2, 9, 0, 2, 10, 9, 6, 11, 7, -1, -1, -1, -1, -1, -1, -1],
    [6, 11, 7, 2, 10, 3, 10, 8, 3, 10, 9, 8, -1, -1, -1, -1],
    [7, 2, 3, 6, 2, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [7, 0, 8, 7, 6, 0, 6, 2, 0, -1, -1, -1, -1, -1, -1, -1],
    [2, 7, 6, 2, 3, 7, 0, 1, 9, -1, -1, -1, -1, -1, -1, -1],
    [1, 6, 2, 1, 8, 6, 1, 9, 8, 8, 7, 6, -1, -1, -1, -1],
    [10, 7, 6, 10, 1, 7, 1, 3, 7, -1, -1, -1, -1, -1, -1, -1],
    [10, 7, 6, 1, 7, 10, 1, 8, 7, 1, 0, 8, -1, -1, -1, -1],
    [0, 3, 7, 0, 7, 10, 0, 10, 9, 6, 10, 7, -1, -1, -1, -1],
    [7, 6, 10, 7, 10, 8, 8, 10, 9, -1, -1, -1, -1, -1, -1, -1],
    [6, 8, 4, 11, 8, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 6, 11, 3, 0, 6, 0, 4, 6, -1, -1, -1, -1, -1, -1, -1],
    [8, 6, 11, 8, 4, 6, 9, 0, 1, -1, -1, -1, -1, -1, -1, -1],
    [9, 4, 6, 9, 6, 3, 9, 3, 1, 11, 3, 6, -1, -1, -1, -1],
    [6, 8, 4, 6, 11, 8, 2, 10, 1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, 3, 0, 11, 0, 6, 11, 0, 4, 6, -1, -1, -1, -1],
    [4, 11, 8, 4, 6, 11, 0, 2, 9, 2, 10, 9, -1, -1, -1, -1],
    [10, 9, 3, 10, 3, 2, 9, 4, 3, 11, 3, 6, 4, 6, 3, -1],
    [8, 2, 3, 8, 4, 2, 4, 6, 2, -1, -1, -1, -1, -1, -1, -1],
    [0, 4, 2, 4, 6, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 9, 0, 2, 3, 4, 2, 4, 6, 4, 3, 8, -1, -1, -1, -1],
    [1, 9, 4, 1, 4, 2, 2, 4, 6, -1, -1, -1, -1, -1, -1, -1],
    [8, 1, 3, 8, 6, 1, 8, 4, 6, 6, 10, 1, -1, -1, -1, -1],
    [10, 1, 0, 10, 0, 6, 6, 0, 4, -1, -1, -1, -1, -1, -1, -1],
    [4, 6, 3, 4, 3, 8, 6, 10, 3, 0, 3, 9, 10, 9, 3, -1],
    [10, 9, 4, 6, 10, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 9, 5, 7, 6, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, 4, 9, 5, 11, 7, 6, -1, -1, -1, -1, -1, -1, -1],
    [5, 0, 1, 5, 4, 0, 7, 6, 11, -1, -1, -1, -1, -1, -1, -1],
    [11, 7, 6, 8, 3, 4, 3, 5, 4, 3, 1, 5, -1, -1, -1, -1],
    [9, 5, 4, 10, 1, 2, 7, 6, 11, -1, -1, -1, -1, -1, -1, -1],
    [6, 11, 7, 1, 2, 10, 0, 8, 3, 4, 9, 5, -1, -1, -1, -1],
    [7, 6, 11, 5, 4, 10, 4, 2, 10, 4, 0, 2, -1, -1, -1, -1],
    [3, 4, 8, 3, 5, 4, 3, 2, 5, 10, 5, 2, 11, 7, 6, -1],
    [7, 2, 3, 7, 6, 2, 5, 4, 9, -1, -1, -1, -1, -1, -1, -1],
    [9, 5, 4, 0, 8, 6, 0, 6, 2, 6, 8, 7, -1, -1, -1, -1],
    [3, 6, 2, 3, 7, 6, 1, 5, 0, 5, 4, 0, -1, -1, -1, -1],
    [6, 2, 8, 6, 8, 7, 2, 1, 8, 4, 8, 5, 1, 5, 8, -1],
    [9, 5, 4, 10, 1, 6, 1, 7, 6, 1, 3, 7, -1, -1, -1, -1],
    [1, 6, 10, 1, 7, 6, 1, 0, 7, 8, 7, 0, 9, 5, 4, -1],
    [4, 0, 10, 4, 10, 5, 0, 3, 10, 6, 10, 7, 3, 7, 10, -1],
    [7, 6, 10, 7, 10, 8, 5, 4, 10, 4, 8, 10, -1, -1, -1, -1],
    [6, 9, 5, 6, 11, 9, 11, 8, 9, -1, -1, -1, -1, -1, -1, -1],
    [3, 6, 11, 0, 6, 3, 0, 5, 6, 0, 9, 5, -1, -1, -1, -1],
    [0, 11, 8, 0, 5, 11, 0, 1, 5, 5, 6, 11, -1, -1, -1, -1],
    [6, 11, 3, 6, 3, 5, 5, 3, 1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 10, 9, 5, 11, 9, 11, 8, 11, 5, 6, -1, -1, -1, -1],
    [0, 11, 3, 0, 6, 11, 0, 9, 6, 5, 6, 9, 1, 2, 10, -1],
    [11, 8, 5, 11, 5, 6, 8, 0, 5, 10, 5, 2, 0, 2, 5, -1],
    [6, 11, 3, 6, 3, 5, 2, 10, 3, 10, 5, 3, -1, -1, -1, -1],
    [5, 8, 9, 5, 2, 8, 5, 6, 2, 3, 8, 2, -1, -1, -1, -1],
    [9, 5, 6, 9, 6, 0, 0, 6, 2, -1, -1, -1, -1, -1, -1, -1],
    [1, 5, 8, 1, 8, 0, 5, 6, 8, 3, 8, 2, 6, 2, 8, -1],
    [1, 5, 6, 2, 1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 3, 6, 1, 6, 10, 3, 8, 6, 5, 6, 9, 8, 9, 6, -1],
    [10, 1, 0, 10, 0, 6, 9, 5, 0, 5, 6, 0, -1, -1, -1, -1],
    [0, 3, 8, 5, 6, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [10, 5, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [11, 5, 10, 7, 5, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [11, 5, 10, 11, 7, 5, 8, 3, 0, -1, -1, -1, -1, -1, -1, -1],
    [5, 11, 7, 5, 10, 11, 1, 9, 0, -1, -1, -1, -1, -1, -1, -1],
    [10, 7, 5, 10, 11, 7, 9, 8, 1, 8, 3, 1, -1, -1, -1, -1],
    [11, 1, 2, 11, 7, 1, 7, 5, 1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, 1, 2, 7, 1, 7, 5, 7, 2, 11, -1, -1, -1, -1],
    [9, 7, 5, 9, 2, 7, 9, 0, 2, 2, 11, 7, -1, -1, -1, -1],
    [7, 5, 2, 7, 2, 11, 5, 9, 2, 3, 2, 8, 9, 8, 2, -1],
    [2, 5, 10, 2, 3, 5, 3, 7, 5, -1, -1, -1, -1, -1, -1, -1],
    [8, 2, 0, 8, 5, 2, 8, 7, 5, 10, 2, 5, -1, -1, -1, -1],
    [9, 0, 1, 5, 10, 3, 5, 3, 7, 3, 10, 2, -1, -1, -1, -1],
    [9, 8, 2, 9, 2, 1, 8, 7, 2, 10, 2, 5, 7, 5, 2, -1],
    [1, 3, 5, 3, 7, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 7, 0, 7, 1, 1, 7, 5, -1, -1, -1, -1, -1, -1, -1],
    [9, 0, 3, 9, 3, 5, 5, 3, 7, -1, -1, -1, -1, -1, -1, -1],
    [9, 8, 7, 5, 9, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [5, 8, 4, 5, 10, 8, 10, 11, 8, -1, -1, -1, -1, -1, -1, -1],
    [5, 0, 4, 5, 11, 0, 5, 10, 11, 11, 3, 0, -1, -1, -1, -1],
    [0, 1, 9, 8, 4, 10, 8, 10, 11, 10, 4, 5, -1, -1, -1, -1],
    [10, 11, 4, 10, 4, 5, 11, 3, 4, 9, 4, 1, 3, 1, 4, -1],
    [2, 5, 1, 2, 8, 5, 2, 11, 8, 4, 5, 8, -1, -1, -1, -1],
    [0, 4, 11, 0, 11, 3, 4, 5, 11, 2, 11, 1, 5, 1, 11, -1],
    [0, 2, 5, 0, 5, 9, 2, 11, 5, 4, 5, 8, 11, 8, 5, -1],
    [9, 4, 5, 2, 11, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [2, 5, 10, 3, 5, 2, 3, 4, 5, 3, 8, 4, -1, -1, -1, -1],
    [5, 10, 2, 5, 2, 4, 4, 2, 0, -1, -1, -1, -1, -1, -1, -1],
    [3, 10, 2, 3, 5, 10, 3, 8, 5, 4, 5, 8, 0, 1, 9, -1],
    [5, 10, 2, 5, 2, 4, 1, 9, 2, 9, 4, 2, -1, -1, -1, -1],
    [8, 4, 5, 8, 5, 3, 3, 5, 1, -1, -1, -1, -1, -1, -1, -1],
    [0, 4, 5, 1, 0, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [8, 4, 5, 8, 5, 3, 9, 0, 5, 0, 3, 5, -1, -1, -1, -1],
    [9, 4, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 11, 7, 4, 9, 11, 9, 10, 11, -1, -1, -1, -1, -1, -1, -1],
    [0, 8, 3, 4, 9, 7, 9, 11, 7, 9, 10, 11, -1, -1, -1, -1],
    [1, 10, 11, 1, 11, 4, 1, 4, 0, 7, 4, 11, -1, -1, -1, -1],
    [3, 1, 4, 3, 4, 8, 1, 10, 4, 7, 4, 11, 10, 11, 4, -1],
    [4, 11, 7, 9, 11, 4, 9, 2, 11, 9, 1, 2, -1, -1, -1, -1],
    [9, 7, 4, 9, 11, 7, 9, 1, 11, 2, 11, 1, 0, 8, 3, -1],
    [11, 7, 4, 11, 4, 2, 2, 4, 0, -1, -1, -1, -1, -1, -1, -1],
    [11, 7, 4, 11, 4, 2, 8, 3, 4, 3, 2, 4, -1, -1, -1, -1],
    [2, 9, 10, 2, 7, 9, 2, 3, 7, 7, 4, 9, -1, -1, -1, -1],
    [9, 10, 7, 9, 7, 4, 10, 2, 7, 8, 7, 0, 2, 0, 7, -1],
    [3, 7, 10, 3, 10, 2, 7, 4, 10, 1, 10, 0, 4, 0, 10, -1],
    [1, 10, 2, 8, 7, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 9, 1, 4, 1, 7, 7, 1, 3, -1, -1, -1, -1, -1, -1, -1],
    [4, 9, 1, 4, 1, 7, 0, 8, 1, 8, 7, 1, -1, -1, -1, -1],
    [4, 0, 3, 7, 4, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [4, 8, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [9, 10, 8, 10, 11, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 0, 9, 3, 9, 11, 11, 9, 10, -1, -1, -1, -1, -1, -1, -1],
    [0, 1, 10, 0, 10, 8, 8, 10, 11, -1, -1, -1, -1, -1, -1, -1],
    [3, 1, 10, 11, 3, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 2, 11, 1, 11, 9, 9, 11, 8, -1, -1, -1, -1, -1, -1, -1],
    [3, 0, 9, 3, 9, 11, 1, 2, 9, 2, 11, 9, -1, -1, -1, -1],
    [0, 2, 11, 8, 0, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [3, 2, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [2, 3, 8, 2, 8, 10, 10, 8, 9, -1, -1, -1, -1, -1, -1, -1],
    [9, 10, 2, 0, 9, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [2, 3, 8, 2, 8, 10, 0, 1, 8, 1, 10, 8, -1, -1, -1, -1],
    [1, 10, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, 3, 8, 9, 1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 9, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 3, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
], dtype=np.intp)
_MC_EDGES = np.array([
    0, 265, 515, 778, 1030, 1295, 1541, 1804,
    2060, 2309, 2575, 2822, 3082, 3331, 3593, 3840,
    400, 153, 915, 666, 1430, 1183, 1941, 1692,
    2460, 2197, 2975, 2710, 3482, 3219, 3993, 3728,
    560, 825, 51, 314, 1590, 1855, 1077, 1340,
    2620, 2869, 2111, 2358, 3642, 3891, 3129, 3376,
    928, 681, 419, 170, 1958, 1711, 1445, 1196,
    2988, 2725, 2479, 2214, 4010, 3747, 3497, 3232,
    1120, 1385, 1635, 1898, 102, 367, 613, 876,
    3180, 3429, 3695, 3942, 2154, 2403, 2665, 2912,
    1520, 1273, 2035, 1786, 502, 255, 1013, 764,
    3580, 3317, 4095, 3830, 2554, 2291, 3065, 2800,
    1616, 1881, 1107, 1370, 598, 863, 85, 348,
    3676, 3925, 3167, 3414, 2650, 2899, 2137, 2384,
    1984, 1737, 1475, 1226, 966, 719, 453, 204,
    4044, 3781, 3535, 3270, 3018, 2755, 2505, 2240,
    2240, 2505, 2755, 3018, 3270, 3535, 3781, 4044,
    204, 453, 719, 966, 1226, 1475, 1737, 1984,
    2384, 2137, 2899, 2650, 3414, 3167, 3925, 3676,
    348, 85, 863, 598, 1370, 1107, 1881, 1616,
    2800, 3065, 2291, 2554, 3830, 4095, 3317, 3580,
    764, 1013, 255, 502, 1786, 2035, 1273, 1520,
    2912, 2665, 2403, 2154, 3942, 3695, 3429, 3180,
    876, 613, 367, 102, 1898, 1635, 1385, 1120,
    3232, 3497, 3747, 4010, 2214, 2479, 2725, 2988,
    1196, 1445, 1711, 1958, 170, 419, 681, 928,
    3376, 3129, 3891, 3642, 2358, 2111, 2869, 2620,
    1340, 1077, 1855, 1590, 314, 51, 825, 560,
    3728, 3993, 3219, 3482, 2710, 2975, 2197, 2460,
    1692, 1941, 1183, 1430, 666, 915, 153, 400,
    3840, 3593, 3331, 3082, 2822, 2575, 2309, 2060,
    1804, 1541, 1295, 1030, 778, 515, 265, 0,
], dtype=np.intp)
# fmt: on
