"""Immutable sources sampled in data space with screen-space error control."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any, Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike

from manim_plots.core import BoolArray, FloatArray, IntArray
from manim_plots.core.nodes import CompiledMap
from manim_plots.core.payload import Payload, split_segments

PIXEL = 8 / 1080
CHORD_TOLERANCE = 0.5 * PIXEL
INITIAL_SAMPLES = 33
MAX_DEPTH = 12
MAX_SAMPLES = 20_000


@runtime_checkable
class Bounds(Protocol):
    """Describe a local clipping region and its rectangular extent."""

    @property
    def lower(self) -> FloatArray:
        """Return the read-only lower corner of the bounding box."""
        ...

    @property
    def upper(self) -> FloatArray:
        """Return the read-only upper corner of the bounding box."""
        ...

    def contains(self, local: FloatArray) -> BoolArray:
        """Test membership in the region.

        Parameters
        ----------
        local
            Local points of shape ``(n, 2)`` or ``(n, 3)``.

        Returns
        -------
        BoolArray
            One membership flag per point.
        """
        ...


def _numeric(value: ArrayLike, name: str) -> FloatArray:
    try:
        with np.errstate(all="ignore"):
            return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise TypeError(f"{name} must be numeric") from error


@dataclass(frozen=True)
class Box:
    """Hold a closed rectangular clip region in local coordinates.

    Parameters
    ----------
    lower, upper
        Finite arrays of shape ``(2,)``, strictly ordered on each axis.
    """

    lower: FloatArray
    upper: FloatArray

    def __post_init__(self) -> None:
        for name in ("lower", "upper"):
            value = _numeric(getattr(self, name), name).copy()
            if value.shape != (2,):
                raise ValueError(f"{name} must have shape (2,)")
            bad = ~np.isfinite(value)
            if np.any(bad):
                raise ValueError(f"{name}[{np.flatnonzero(bad)[0]}] must be finite")
            value.flags.writeable = False
            object.__setattr__(self, name, value)
        bad = self.lower >= self.upper
        if np.any(bad):
            i = int(np.flatnonzero(bad)[0])
            raise ValueError(f"lower[{i}] must be less than upper[{i}]")

    def contains(self, local: FloatArray) -> BoolArray:
        """Test inclusive x/y membership, ignoring a finite z coordinate.

        Parameters
        ----------
        local
            Points of shape ``(n, 2)`` or ``(n, 3)``.

        Returns
        -------
        BoolArray
            False for every non-finite point.
        """
        points = _numeric(local, "local")
        if points.ndim != 2 or points.shape[1] not in (2, 3):
            raise ValueError("local must have shape (n, 2) or (n, 3)")
        x, y = points[:, 0], points[:, 1]
        inside: BoolArray = (
            (x >= self.lower[0])
            & (x <= self.upper[0])
            & (y >= self.lower[1])
            & (y <= self.upper[1])
        )
        if points.shape[1] == 3:
            inside &= np.isfinite(points[:, 2])
        return inside


@runtime_checkable
class Source(Protocol):
    """Supply data-space samples and exact or interpolated point queries."""

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        """Sample geometry for a map and local clip region.

        Parameters
        ----------
        map
            Read-only data, local and screen coordinate conversions.
        bounds
            Local clipping region.

        Returns
        -------
        Payload
            Data-space geometry.
        """
        ...

    def at(self, t: ArrayLike) -> FloatArray:
        """Evaluate data-space points at inputs.

        Parameters
        ----------
        t
            Scalar or one-dimensional inputs.

        Returns
        -------
        FloatArray
            Points of shape ``(m, 2)``.
        """
        ...


def _range(value: Sequence[float] | None, name: str) -> tuple[float, ...] | None:
    if value is None:
        return None
    numbers = _numeric(value, name)
    if numbers.ndim != 1 or len(numbers) not in (2, 3):
        raise ValueError(f"{name} must have length 2 or 3")
    bad = ~np.isfinite(numbers)
    if np.any(bad):
        raise ValueError(f"{name}[{np.flatnonzero(bad)[0]}] must be finite")
    if numbers[0] >= numbers[1]:
        raise ValueError(f"{name} must have lo < hi")
    if len(numbers) == 3 and numbers[2] <= 0:
        raise ValueError(f"{name} step must be positive")
    return tuple(float(x) for x in numbers)


def _options(
    function: Callable[..., Any],
    use_vectorized: bool,
    discontinuities: Iterable[float] | None,
    dt: float,
) -> tuple[float, ...]:
    if not callable(function):
        raise TypeError("function must be callable")
    if not isinstance(use_vectorized, bool):
        raise TypeError("use_vectorized must be a bool")
    if not isinstance(dt, Real) or isinstance(dt, bool):
        raise TypeError("dt must be a real number")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    try:
        ds = tuple(discontinuities) if discontinuities is not None else ()
    except TypeError as error:
        raise TypeError("discontinuities must be iterable") from error
    values = _numeric(ds, "discontinuities")
    if values.ndim != 1:
        raise ValueError("discontinuities must be one-dimensional")
    bad = ~np.isfinite(values)
    if np.any(bad):
        raise ValueError(f"discontinuities[{np.flatnonzero(bad)[0]}] must be finite")
    return tuple(float(x) for x in np.unique(values))


def _inputs(t: ArrayLike) -> FloatArray:
    values = _numeric(t, "t")
    if values.ndim > 1:
        raise ValueError("t must be a scalar or one-dimensional")
    return values.reshape(-1)


def _extent(map: CompiledMap, bounds: Bounds) -> tuple[float, float]:
    with np.errstate(all="ignore"):
        middle = bounds.lower / 2 + bounds.upper / 2
        edges = np.array([[bounds.lower[0], middle[1]], [bounds.upper[0], middle[1]]])
        xs = map.inverse(edges)[:, 0]
    return float(np.min(xs)), float(np.max(xs))


def _pieces(
    lo: float, hi: float, ds: tuple[float, ...], dt: float
) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    start = lo
    for d in ds:
        if lo < d < hi:
            left, right = max(lo, d - dt), min(hi, d + dt)
            if left >= start:
                intervals.append((start, left))
            start = max(start, right)
    if start <= hi:
        intervals.append((start, hi))
    return intervals


def _path(coords: FloatArray, labels: IntArray) -> Payload:
    finite = np.isfinite(coords)
    valid = None if finite.all() else finite.all(axis=1)
    cuts = np.flatnonzero(labels[1:] != labels[:-1]) + 1
    edges = np.concatenate(([0], cuts, [len(coords)]))
    segments = np.column_stack((edges[:-1], edges[1:]))
    segments = segments[segments[:, 0] < segments[:, 1]]
    return Payload._trusted(
        "path",
        coords,
        segments if valid is None else split_segments(segments, valid),
        valid=valid,
    )


def _sum_rows(values: FloatArray) -> FloatArray:
    # Three coordinate columns add in the same order without a strided reduction.
    if values.shape[1] == 2:
        return values[:, 0] + values[:, 1]
    if values.shape[1] == 3:
        return values[:, 0] + values[:, 1] + values[:, 2]
    return values.sum(axis=1)


@dataclass(frozen=True)
class _AnalyticSource:
    function: Callable[..., Any]
    _range: tuple[float, ...] | None
    use_vectorized: bool
    discontinuities: tuple[float, ...]
    dt: float
    _parametric: bool

    def _evaluate(self, t: FloatArray) -> FloatArray:
        if not len(t):
            return np.empty((0, 2))
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            if self.use_vectorized:
                raw = self.function(t.copy())
                values = _numeric(raw, "function output")
                if self._parametric:
                    if (
                        values.ndim != 2
                        or values.shape[0] not in (2, 3)
                        or values.shape[1] != len(t)
                    ):
                        raise TypeError(
                            "function must return two or three arrays of input length"
                        )
                    return values[:2].T.copy()
                if values.shape != t.shape:
                    raise TypeError("function must return an array of input length")
                return np.column_stack((t, values))
            result = np.empty((len(t), 2))
            for i, scalar in enumerate(t):
                raw = self.function(scalar)
                value = _numeric(raw, "function output")
                if self._parametric:
                    if value.shape not in ((2,), (3,)):
                        raise TypeError("function must return two or three coordinates")
                    result[i] = value[:2]
                else:
                    if value.ndim != 0:
                        raise TypeError("function must return a scalar")
                    result[i] = scalar, value.item()
            return result

    def at(self, t: ArrayLike) -> FloatArray:
        """Evaluate the function exactly, without restricting its range.

        Parameters
        ----------
        t
            Scalar or one-dimensional inputs.

        Returns
        -------
        FloatArray
            Data points of shape ``(m, 2)``.
        """
        return self._evaluate(_inputs(t))

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        """Adaptively sample using midpoint deviation in screen space.

        Parameters
        ----------
        map
            Coordinate conversions used for extent and screen error.
        bounds
            Local clipping region; restricts x only for a function graph.

        Returns
        -------
        Payload
            Ordered data anchors, retaining invalid samples and path splits.
        """
        if self._parametric:
            assert self._range is not None
            lo, hi = self._range[:2]
        else:
            lo, hi = _extent(map, bounds)
            if self._range is not None:
                lo, hi = max(lo, self._range[0]), min(hi, self._range[1])
        if not np.isfinite([lo, hi]).all() or lo > hi:
            return Payload.empty("path", 2)
        intervals = _pieces(lo, hi, self.discontinuities, self.dt)
        ts: list[FloatArray] = []
        ids: list[IntArray] = []
        remaining = MAX_SAMPLES
        with np.errstate(all="ignore"):
            for i, (interval_left, interval_right) in enumerate(intervals):
                count = INITIAL_SAMPLES if interval_left < interval_right else 1
                if self._range is not None and len(self._range) == 3:
                    ratio = (interval_right - interval_left) / self._range[2]
                    count = max(
                        count,
                        int(np.ceil(np.nextafter(min(ratio, MAX_SAMPLES), -np.inf)))
                        + 1,
                    )
                count = min(count, remaining)
                if not count:
                    break
                ts.append(np.linspace(interval_left, interval_right, count))
                ids.append(np.full(count, i, dtype=np.intp))
                remaining -= count
        if not ts:
            return Payload.empty("path", 2)
        t = ts[0] if len(ts) == 1 else np.concatenate(ts)
        labels = ids[0] if len(ids) == 1 else np.concatenate(ids)
        depth: IntArray | None = None
        active = labels[1:] == labels[:-1]
        probes = None
        if 1 < len(t) < MAX_SAMPLES:
            mid = t[:-1] / 2 + t[1:] / 2
            mid = mid if active.all() else mid[active]
            evaluated = self._evaluate(np.concatenate((t, mid)))
            mapped = map.to_screen(evaluated)
            coords, points = evaluated[: len(t)], evaluated[len(t) :]
            screen, images = mapped[: len(t)], mapped[len(t) :]
            probes = points, images
        else:
            coords = self._evaluate(t)
            screen = map.to_screen(coords)
        for _ in range(MAX_DEPTH):
            if len(t) < 2 or len(t) >= MAX_SAMPLES:
                break
            indices = None if active.all() else np.flatnonzero(active)
            if indices is not None and not len(indices):
                break
            with np.errstate(all="ignore"):
                if indices is None:
                    left_t, right_t = t[:-1], t[1:]
                    left, right = screen[:-1], screen[1:]
                else:
                    left_t, right_t = t[indices], t[indices + 1]
                    left, right = screen[indices], screen[indices + 1]
                mid = left_t / 2 + right_t / 2
                if probes is None:
                    points = self._evaluate(mid)
                    images = map.to_screen(points)
                else:
                    points, images = probes
                    probes = None
                # The chord midpoint is an admissible closest-point candidate.
                delta = images - left / 2 - right / 2
                if (_sum_rows(delta * delta) <= CHORD_TOLERANCE**2).all():
                    break
                chord = right - left
                norm = _sum_rows(chord * chord)
                delta = images - left
                fraction = np.divide(
                    _sum_rows(delta * chord),
                    norm,
                    out=np.zeros(len(mid)),
                    where=norm != 0,
                )
                np.clip(fraction, 0, 1, out=fraction)
                chord *= fraction[:, None]
                delta -= chord
                error = _sum_rows(delta * delta)
                if np.isfinite(screen).all() and np.isfinite(images).all():
                    refine = error > CHORD_TOLERANCE**2
                else:
                    lv = np.isfinite(left).all(axis=1)
                    rv = np.isfinite(right).all(axis=1)
                    mv = np.isfinite(images).all(axis=1)
                    refine = (lv != rv) | (
                        lv & rv & (~mv | (error > CHORD_TOLERANCE**2))
                    )
                refine &= (mid > left_t) & (mid < right_t)
            chosen = np.flatnonzero(refine)[: MAX_SAMPLES - len(t)]
            if not len(chosen):
                break
            edges = chosen if indices is None else indices[chosen]
            insert = np.zeros(len(t) - 1, dtype=np.bool_)
            insert[edges] = True
            positions = np.arange(len(t)) + np.concatenate(([0], np.cumsum(insert)))
            new_t = np.empty(len(t) + len(edges))
            new_coords = np.empty((len(new_t), 2))
            new_screen = np.empty((len(new_t), screen.shape[1]))
            new_labels = np.empty(len(new_t), dtype=np.intp)
            new_t[positions], new_coords[positions] = t, coords
            new_screen[positions], new_labels[positions] = screen, labels
            added = positions[edges] + 1
            new_t[added], new_coords[added] = mid[chosen], points[chosen]
            new_screen[added], new_labels[added] = images[chosen], labels[edges]
            if depth is None:
                depth = np.zeros(len(t) - 1, dtype=np.intp)
            depth = np.repeat(depth + insert, 1 + insert)
            active = np.repeat(insert, 1 + insert) & (depth < MAX_DEPTH)
            t, coords, screen, labels = new_t, new_coords, new_screen, new_labels
        return self._split_poles(t, coords, labels, map, bounds)

    def _split_poles(
        self,
        t: FloatArray,
        coords: FloatArray,
        labels: IntArray,
        map: CompiledMap,
        bounds: Bounds,
    ) -> Payload:
        with np.errstate(all="ignore"):
            candidates = np.signbit(coords[:-1]) != np.signbit(coords[1:])
            if not self._parametric:
                candidates[:, 0] = False
            indices = np.flatnonzero(
                candidates.any(axis=1) & (labels[:-1] == labels[1:])
            )
            if not len(indices):
                return _path(coords, labels)
            ends = np.concatenate((coords[indices], coords[indices + 1]))
            local = map.forward(ends)
            left_local, right_local = local[: len(indices)], local[len(indices) :]
            finite = np.isfinite(ends).all(axis=1)
            candidates = candidates[indices] & (
                ((left_local < bounds.lower) & (right_local > bounds.upper))
                | ((right_local < bounds.lower) & (left_local > bounds.upper))
            )
            candidates &= (finite[: len(indices)] & finite[len(indices) :])[:, None]
            keep = candidates.any(axis=1)
            indices, candidates = indices[keep], candidates[keep]
            if not len(indices):
                return _path(coords, labels)
            axis_ids = np.argmax(candidates, axis=1)
            rows = np.arange(len(indices))
            left, right = t[indices].copy(), t[indices + 1].copy()
            lc, rc = coords[indices].copy(), coords[indices + 1].copy()
            alive = np.ones(len(indices), dtype=np.bool_)
            probing = alive.copy()
            for _ in range(40):
                ids = np.flatnonzero(probing)
                if not len(ids):
                    break
                mid = left[ids] / 2 + right[ids] / 2
                mc = self._evaluate(mid)
                ml = map.forward(mc)
                a = axis_ids[ids]
                values = ml[np.arange(len(ids)), a]
                inside = (values >= bounds.lower[a]) & (values <= bounds.upper[a])
                alive[ids[inside]] = False
                good = np.isfinite(mc).all(axis=1) & ~inside
                probing[ids] = good & (mid > left[ids]) & (mid < right[ids])
                same = np.signbit(mc[np.arange(len(ids)), a]) == np.signbit(lc[ids, a])
                move_left, move_right = ids[good & same], ids[good & ~same]
                left[move_left], lc[move_left] = mid[good & same], mc[good & same]
                right[move_right], rc[move_right] = mid[good & ~same], mc[good & ~same]
            ll, rl = map.forward(lc)[rows, axis_ids], map.forward(rc)[rows, axis_ids]
            alive &= ((ll < bounds.lower[axis_ids]) & (rl > bounds.upper[axis_ids])) | (
                (rl < bounds.lower[axis_ids]) & (ll > bounds.upper[axis_ids])
            )
        confirmed = np.flatnonzero(alive)
        if not len(confirmed):
            return _path(coords, labels)
        ids = confirmed[: max(0, (MAX_SAMPLES - len(t)) // 2)]
        extra_t = np.column_stack((left[ids], right[ids])).ravel()
        extra_coords = np.stack((lc[ids], rc[ids]), axis=1).reshape(-1, 2)
        all_t = np.concatenate((t, extra_t))
        order = np.argsort(all_t, kind="stable")
        sorted_t = all_t[order]
        unique = np.concatenate(([True], sorted_t[1:] != sorted_t[:-1]))
        sorted_t = sorted_t[unique]
        coords = np.concatenate((coords, extra_coords))[order][unique]
        labels = np.concatenate((labels, np.repeat(labels[indices[ids]], 2)))[order][
            unique
        ]
        cuts = np.zeros(len(coords), dtype=np.intp)
        split_at = np.concatenate((right[ids], t[indices[confirmed[len(ids) :]] + 1]))
        cuts[np.searchsorted(sorted_t, split_at)] = 1
        # Preserve explicit discontinuities as well as newly located poles.
        cuts[1:] |= labels[1:] != labels[:-1]
        return _path(coords, np.cumsum(cuts))


@dataclass(frozen=True, init=False)
class FunctionSource(_AnalyticSource):
    """Sample an analytic graph with Manim's scalar/vectorized convention.

    Parameters
    ----------
    function
        Callable returning one y value per x.
    x_range
        Optional ascending endpoints and optional positive maximum spacing.
    use_vectorized
        Call once per pass with an array instead of once per scalar sample.
    discontinuities
        Inputs at which to force a gap.
    dt
        Positive half-width of each forced gap.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
    ) -> None:
        ds = _options(function, use_vectorized, discontinuities, dt)
        super().__init__(
            function, _range(x_range, "x_range"), use_vectorized, ds, dt, False
        )


@dataclass(frozen=True, init=False)
class ParametricSource(_AnalyticSource):
    """Sample a parameterized curve, dropping its optional z coordinate.

    Parameters
    ----------
    function
        Callable returning two or three coordinates, or coordinate arrays.
    t_range
        Ascending endpoints and optional positive maximum parameter spacing.
    use_vectorized
        Use Manim's sequence-of-coordinate-arrays calling convention.
    discontinuities
        Parameter values at which to force a gap.
    dt
        Positive half-width of each forced gap.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        t_range: Sequence[float] = (0.0, 1.0),
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
    ) -> None:
        ds = _options(function, use_vectorized, discontinuities, dt)
        checked = _range(t_range, "t_range")
        if checked is None:
            raise TypeError("t_range must be a sequence")
        super().__init__(function, checked, use_vectorized, ds, dt, True)


@dataclass(frozen=True, init=False)
class ArraySource:
    """Store immutable array geometry and retain edges bracketing the viewport.

    Parameters
    ----------
    xs
        One-dimensional x values, or an ``(n, 2)`` array of pairs.
    ys
        One-dimensional y values, absent when xs contains pairs.
    kind
        Path connectivity or independent points.
    """

    data: FloatArray
    kind: Literal["path", "points"]

    def __init__(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        kind: Literal["path", "points"] = "path",
    ) -> None:
        x = _numeric(xs, "xs")
        if ys is None:
            if x.ndim != 2 or x.shape[1] != 2:
                raise ValueError("pairs must have shape (n, 2)")
            data = x.copy()
        else:
            y = _numeric(ys, "ys")
            if x.ndim != 1 or y.ndim != 1:
                raise ValueError("xs and ys must be one-dimensional")
            if len(x) != len(y):
                raise ValueError(f"xs length {len(x)} differs from ys length {len(y)}")
            data = np.column_stack((x, y))
        if not isinstance(kind, str):
            raise TypeError("kind must be a str")
        if kind not in ("path", "points"):
            raise ValueError("kind must be path or points")
        data.flags.writeable = False
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "kind", kind)

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        """Filter by data x extent, preserving bracketing edges for paths.

        Parameters
        ----------
        map
            Supplies the inverse local-to-data mapping.
        bounds
            Local viewport.

        Returns
        -------
        Payload
            Ordered data with gaps wherever filtering removed samples.
        """
        lo, hi = _extent(map, bounds)
        x = self.data[:, 0]
        keep = (x >= lo) & (x <= hi)
        if self.kind == "path" and len(x) > 1:
            edges = (np.minimum(x[:-1], x[1:]) <= hi) & (
                np.maximum(x[:-1], x[1:]) >= lo
            )
            keep[:-1] |= edges
            keep[1:] |= edges
        indices = np.flatnonzero(keep)
        coords = self.data[indices]
        if self.kind == "points":
            valid = np.isfinite(coords).all(axis=1)
            return Payload.points(coords, None if valid.all() else valid)
        labels = np.cumsum(
            np.concatenate(([0], (np.diff(indices) != 1).astype(np.intp)))
        )
        return _path(coords, labels[: len(coords)])

    def at(self, t: ArrayLike) -> FloatArray:
        """Interpolate y linearly against strictly monotonic x samples.

        Parameters
        ----------
        t
            Scalar or one-dimensional x queries inside the data extent.

        Returns
        -------
        FloatArray
            Interpolated data points of shape ``(m, 2)``.

        Raises
        ------
        ValueError
            For non-monotonic x, an out-of-range input or an invalid neighbour.
        """
        values = _inputs(t)
        data = self.data
        if not len(data):
            if len(values):
                raise ValueError("t is outside the empty data x extent")
            return np.empty((0, 2))
        x = data[:, 0]
        with np.errstate(all="ignore"):
            diff = np.diff(x)
        increasing = len(x) < 2 or x[1] > x[0]
        bad = ~np.isfinite(x)
        if len(diff):
            bad[1:] |= (diff <= 0) if increasing else (diff >= 0)
        if np.any(bad):
            raise ValueError(
                f"x is not strictly monotonic at index {np.flatnonzero(bad)[0]}"
            )
        if not increasing:
            data, x = data[::-1], x[::-1]
        outside = ~np.isfinite(values) | (values < x[0]) | (values > x[-1])
        if np.any(outside):
            raise ValueError(
                f"t[{np.flatnonzero(outside)[0]}] is outside the data x extent"
            )
        right = np.clip(np.searchsorted(x, values, side="left"), 0, len(x) - 1)
        left = np.maximum(right - 1, 0)
        left = np.where(values == x[right], right, left)
        invalid = ~np.isfinite(data[left]).all(axis=1) | ~np.isfinite(data[right]).all(
            axis=1
        )
        if np.any(invalid):
            raise ValueError(
                f"t[{np.flatnonzero(invalid)[0]}] has a non-finite sample neighbourhood"
            )
        with np.errstate(all="ignore"):
            return np.column_stack((values, np.interp(values, x, data[:, 1])))
