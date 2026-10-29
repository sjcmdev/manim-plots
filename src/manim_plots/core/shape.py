"""Local-space cubic geometry stages, independent of Manim."""

from __future__ import annotations

from collections.abc import Callable
from numbers import Real

import numpy as np
from scipy.linalg import solve_banded  # type: ignore[import-untyped]

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


def _handles(anchors: FloatArray) -> tuple[FloatArray, FloatArray]:
    n, dim = len(anchors) - 1, anchors.shape[1]
    if n == 1:
        return (2 * anchors[:1] + anchors[1:]) / 3, (anchors[:1] + 2 * anchors[1:]) / 3
    band = np.ones((3, n))
    band[1] = 4
    # Exact closure takes precedence over Manim's signed endpoint tolerance.
    closed = bool(
        np.array_equal(anchors[0], anchors[-1])
        or np.all(np.abs(anchors[-1] - anchors[0]) <= 1e-8 + 1e-5 * anchors[0])
    )
    if closed:
        band[1, [0, -1]] = 3
        rhs = np.empty((n, dim + 1))
        rhs[:, :dim] = 4 * anchors[:-1] + 2 * anchors[1:]
        rhs[:, dim] = 0
        rhs[[0, -1], dim] = 1
        solved = np.asarray(
            solve_banded((1, 1), band, rhs, check_finite=False), dtype=np.float64
        )
        y, q = solved[:, :dim], solved[:, dim, None]
        first = y - q * (y[0] + y[-1]) / (1 + q[0] + q[-1])
        second = 2 * anchors[1:] - np.roll(first, -1, axis=0)
    else:
        band[1, 0], band[1, -1] = 2, 7
        band[2, -2] = 2
        rhs = 4 * anchors[:-1] + 2 * anchors[1:]
        rhs[0], rhs[-1] = anchors[0] + 2 * anchors[1], 8 * anchors[-2] + anchors[-1]
        first = np.asarray(
            solve_banded((1, 1), band, rhs, check_finite=False), dtype=np.float64
        )
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
    for _ in range(48):
        mid = (lo + hi) / 2
        below = _lengths(selected, mid) < target
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    result = (lo + hi) / 2
    result[target <= 0] = 0
    result[target >= lengths[indices]] = 1
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
        lengths = _lengths(curves)
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
            indices, times = _arc_parameters(
                segment, sizes, np.column_stack((begins, ends)).ravel()
            )
            for (first, last), (a, b) in zip(
                indices.reshape(-1, 2), times.reshape(-1, 2), strict=True
            ):
                selected = segment[first : last + 1].copy()
                low, high = np.zeros(len(selected)), np.ones(len(selected))
                low[0], high[-1] = a, b
                parts.append(_restrict(selected, low, high).reshape(-1, dim))
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
