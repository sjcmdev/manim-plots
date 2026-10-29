"""Local-space cubic geometry stages, independent of Manim."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from itertools import pairwise
from numbers import Real

import numpy as np
from scipy.linalg.lapack import dpttrf, dpttrs  # type: ignore[import-untyped]

from manim_plots.core import FloatArray, IntArray
from manim_plots.core.payload import Payload
from manim_plots.core.sources import Bounds, Box

Shape = Callable[[Payload, Bounds], Payload]

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
    roots: list[float] = [0.0, 1.0]
    sides: list[tuple[int, float]] = [(-1, 0.0), (-1, 0.0)]
    scale = max(
        float(np.max(np.abs(curve[:, :2]))),
        float(np.max(np.abs(box.lower))),
        float(np.max(np.abs(box.upper))),
        1.0,
    )
    points = curve[:, :2] / scale
    for axis in range(2):
        p = points[:, axis]
        for bound in (box.lower[axis], box.upper[axis]):
            coefficients = np.array(
                [
                    p[0] - bound / scale,
                    3 * (p[1] - p[0]),
                    3 * (p[2] - 2 * p[1] + p[0]),
                    p[3] - 3 * p[2] + 3 * p[1] - p[0],
                ]
            )
            solutions = np.polynomial.polynomial.polyroots(coefficients)
            for root in solutions:
                if abs(root.imag) <= 1e-10 and 0 < root.real < 1:
                    roots.append(float(root.real))
                    sides.append((axis, float(bound)))
    times, inverse = np.unique(roots, return_inverse=True)
    crossing = np.full((len(times), 2), np.nan)
    for index, (axis, bound) in zip(inverse, sides, strict=True):
        if axis >= 0:
            crossing[index, axis] = bound
    return times, crossing


def _clip_curve(curve: FloatArray, box: Box) -> tuple[list[FloatArray], bool, bool]:
    dim = curve.shape[1]
    if box.contains(curve).all():
        return [curve], True, True
    xy = curve[:, :2]
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
    pieces[:, 0, :2] = np.where(
        np.isfinite(crossing[:-1]), crossing[:-1], pieces[:, 0, :2]
    )
    pieces[:, 3, :2] = np.where(
        np.isfinite(crossing[1:]), crossing[1:], pieces[:, 3, :2]
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
    outside = payload.coords[~inside, :2]
    tolerance = 8 * np.spacing(np.maximum(np.abs(box.lower), np.abs(box.upper)))
    if ((outside >= box.lower - tolerance) & (outside <= box.upper + tolerance)).all():
        # An inverse/forward round trip at the viewport edge need not be bit-exact.
        coords = payload.coords.copy()
        coords[~inside, :2] = np.clip(outside, box.lower, box.upper)
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
    box = bounds if type(bounds) is Box else Box(bounds.lower, bounds.upper)
    if payload.kind == "path":
        return _clip_path(payload, box)
    valid = box.contains(payload.coords)
    if payload.valid is not None:
        valid &= payload.valid
    if payload.kind == "points":
        return Payload._trusted("points", payload.coords, payload.segments, valid=valid)
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
        "region", payload.coords, payload.segments, cells, payload.valid
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
