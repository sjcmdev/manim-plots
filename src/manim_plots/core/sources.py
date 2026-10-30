"""Immutable sources sampled in data space with screen-space error control."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any, Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike
from scipy.interpolate import CubicSpline  # type: ignore[import-untyped]

from manim_plots.core import BoolArray, FloatArray, IntArray
from manim_plots.core.nodes import CompiledMap, SystemMap
from manim_plots.core.payload import Payload, split_segments

PIXEL = 8 / 1080
CHORD_TOLERANCE = 0.5 * PIXEL
INITIAL_SAMPLES = 33
MAX_DEPTH = 12
MAX_SAMPLES = 20_000


def rk4_step(
    func: Callable[[FloatArray], FloatArray], points: FloatArray, dt: float
) -> FloatArray:
    """Advance data points by one classical fourth-order Runge-Kutta step.

    Parameters
    ----------
    func
        Vectorized velocity on arrays of shape ``(n, d)``, with d equal to 2 or 3.
    points
        Initial data coordinates of shape ``(n, d)``, with d equal to 2 or 3.
    dt
        Finite signed field time.

    Returns
    -------
    FloatArray
        Advanced coordinates. A non-finite stage leaves that point stationary.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] not in (2, 3):
        raise ValueError("points must have shape (n, 2) or (n, 3)")
    if not np.isfinite(dt):
        raise ValueError("dt must be finite")
    with np.errstate(all="ignore"):
        k1 = np.asarray(func(points.copy()), dtype=float)
        k2 = np.asarray(func(points + dt / 2 * k1), dtype=float)
        k3 = np.asarray(func(points + dt / 2 * k2), dtype=float)
        k4 = np.asarray(func(points + dt * k3), dtype=float)
        if any(k.shape != points.shape for k in (k1, k2, k3, k4)):
            raise ValueError("func must return the same shape as points")
        result = points + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    good = np.isfinite(result).all(axis=1)
    return np.where(good[:, None], result, points)


@dataclass(frozen=True, init=False)
class FieldSource:
    """Sample a scalar or vector field on an inclusive rectangular data grid.

    Parameters
    ----------
    func
        Function accepting one data point ``[x, y, 0]`` and returning a scalar
        or a two- or three-component vector. Without z_range the third
        component is ignored. With z_range all three components are retained.
    x_range, y_range, z_range
        Optional finite bounds and positive step; omitted bounds use the map's
        viewport and omitted steps use one. Field artists supply tick steps.
    use_vectorized
        Pass an ``(n, 3)`` array and expect ``(n,)``, ``(n, 2)`` or ``(n, 3)``.
    """

    func: Callable[..., Any]
    x_range: tuple[float, ...] | None
    y_range: tuple[float, ...] | None
    z_range: tuple[float, ...] | None
    use_vectorized: bool

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        z_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
    ) -> None:
        if not callable(func):
            raise TypeError("func must be callable")
        if not isinstance(use_vectorized, bool):
            raise TypeError("use_vectorized must be a bool")
        object.__setattr__(self, "func", func)
        object.__setattr__(
            self, "x_range", _range(x_range, "x_range", allow_equal=z_range is not None)
        )
        object.__setattr__(
            self, "y_range", _range(y_range, "y_range", allow_equal=z_range is not None)
        )
        object.__setattr__(
            self, "z_range", _range(z_range, "z_range", allow_equal=True)
        )
        object.__setattr__(self, "use_vectorized", use_vectorized)

    def at(self, points: ArrayLike) -> FloatArray:
        """Evaluate arbitrary data points without restricting them to the grid.

        Parameters
        ----------
        points
            Array of shape ``(n, 2)`` or ``(n, 3)``.

        Returns
        -------
        FloatArray
            Scalars ``(n,)`` or vectors ``(n, d)`` in the grid dimension.
        """
        data = _numeric(points, "points")
        if data.ndim != 2 or data.shape[1] not in (2, 3):
            raise ValueError("points must have shape (n, 2) or (n, 3)")
        inputs = (
            data.copy()
            if self.z_range is not None and data.shape[1] == 3
            else np.column_stack((data[:, :2], np.zeros(len(data))))
        )
        with np.errstate(all="ignore"):
            if self.use_vectorized:
                values = _numeric(self.func(inputs), "func output")
            else:
                outputs = []
                for point in inputs:
                    try:
                        outputs.append(self.func(point))
                    except (ZeroDivisionError, OverflowError):
                        outputs.append(np.nan)
                # Scalar failures in an otherwise vector field invalidate the row.
                shape = next((np.shape(v) for v in outputs if np.ndim(v)), ())
                values = _numeric(
                    [
                        np.full(shape, v) if np.ndim(v) == 0 and shape else v
                        for v in outputs
                    ],
                    "func output",
                )
        if values.shape == (len(data),):
            return values
        if values.shape in ((len(data), 2), (len(data), 3)):
            return values[:, : 3 if self.z_range is not None else 2].copy()
        raise ValueError("func output must have shape (n,), (n, 2) or (n, 3)")

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        """Sample a region in C order, with x outermost on a 3D grid.

        Parameters
        ----------
        map, bounds
            Coordinate conversion and local viewport.

        Returns
        -------
        Payload
            Region with grid topology, immutable values and sample validity.
        """
        dimension = 3 if self.z_range is not None else 2
        edges = map.inverse(np.array([bounds.lower, bounds.upper]))[:, :dimension]
        axes = []
        for i, explicit in enumerate(
            (self.x_range, self.y_range, self.z_range)[:dimension]
        ):
            lo, hi = sorted(edges[:, i]) if explicit is None else explicit[:2]
            step = explicit[2] if explicit is not None and len(explicit) == 3 else 1
            count = int(np.floor((hi - lo) / step + 1e-12))
            grid = lo + np.arange(count + 1) * step
            # Include the upper end even when the final cell is shorter.
            if not np.isclose(grid[-1], hi, rtol=0, atol=step * 1e-12):
                grid = np.append(grid, hi)
            else:
                grid[-1] = hi
            axes.append(grid)
        grids = np.meshgrid(*axes, indexing="ij" if dimension == 3 else "xy")
        coords = np.column_stack([grid.ravel() for grid in grids])
        values = self.at(coords)
        valid = np.isfinite(values)
        if values.ndim == 2:
            valid = valid.all(axis=1)
        return Payload(
            "region",
            coords,
            np.array([[0, len(coords)]]),
            tuple(len(axis) for axis in axes)
            if dimension == 3
            else (len(axes[1]), len(axes[0])),
            None if valid.all() else valid,
            values,
        )


class _CalculusSource:
    """Cache calculus queries against a versioned, replaceable parent source."""

    def __init__(
        self,
        parent: Callable[[], Source],
        limits: Callable[[], tuple[float, float]],
        revision: Callable[[], object],
        *,
        integral: bool = False,
        y_intercept: float = 0,
        x_range: Sequence[float] | None = None,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
    ) -> None:
        self._parent, self._limits, self._revision = parent, limits, revision
        self._integral, self._intercept = integral, y_intercept
        self._explicit_range = _range(x_range, "x_range")
        self._extra_gaps = _options(self._values, True, discontinuities, dt)
        self.dt = dt
        self._seen: object = None
        self._primitive: Any = None
        self._anchor = 0.0
        self.use_vectorized = True
        self.discontinuities: tuple[float, ...] = ()

    @property
    def _range(self) -> tuple[float, ...]:
        return (
            tuple(sorted(self._limits()))
            if self._explicit_range is None
            else self._explicit_range
        )

    def _sync(self) -> None:
        seen = self._revision()
        if seen == self._seen:
            return
        parent = self._parent()
        self.discontinuities = tuple(
            sorted(set((*getattr(parent, "discontinuities", ()), *self._extra_gaps)))
        )
        if self._integral:
            lo, hi = sorted(self._limits())
            # Integrate one cubic interpolant over the entire grid, including the
            # anchor exactly. Queries then cost one polynomial evaluation.
            anchor = 0.0 if lo <= 0 <= hi else self._limits()[0]
            if anchor == 0:
                with np.errstate(all="ignore"):
                    try:
                        valid_zero = bool(np.isfinite(parent.at(0)).all())
                    except (ValueError, ZeroDivisionError, OverflowError):
                        valid_zero = False
                if not valid_zero:
                    anchor = self._limits()[0]
            grid = np.unique(np.append(np.linspace(lo, hi, 4097), anchor))
            values = parent.at(grid)[:, 1]
            self._primitive = CubicSpline(grid, values).antiderivative()
            self._anchor = float(self._primitive(anchor))
        self._seen = seen

    def _values(self, x: FloatArray) -> FloatArray:
        self._sync()
        if self._integral:
            return np.asarray(
                self._primitive(x) - self._anchor + self._intercept, dtype=float
            )
        h = np.cbrt(np.finfo(float).eps) * np.maximum(1, np.abs(x))
        parent = self._parent()
        return np.asarray(
            (parent.at(x + h)[:, 1] - parent.at(x - h)[:, 1]) / (2 * h), dtype=float
        )

    def at(self, t: ArrayLike) -> FloatArray:
        """Return exact derivative queries or queries of the cached primitive.

        Parameters
        ----------
        t
            Scalar or one-dimensional data inputs.

        Returns
        -------
        FloatArray
            Input and derived value in each row.
        """
        x = _inputs(t)
        return np.column_stack((x, self._values(x)))

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        """Sample the derived function with the ordinary adaptive sampler.

        Parameters
        ----------
        map, bounds
            Coordinate conversions and local sampling bounds.

        Returns
        -------
        Payload
            Data-space path, as for FunctionSource.
        """
        self._sync()
        return FunctionSource(
            self._values,
            self._range,
            use_vectorized=True,
            discontinuities=self.discontinuities,
            dt=self.dt,
        ).sample(map, bounds)


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
            if value.shape not in ((2,), (3,)):
                raise ValueError(f"{name} must have shape (2,)")
            bad = ~np.isfinite(value)
            if np.any(bad):
                raise ValueError(f"{name}[{np.flatnonzero(bad)[0]}] must be finite")
            value.flags.writeable = False
            object.__setattr__(self, name, value)
        if self.lower.shape != self.upper.shape:
            raise ValueError("lower and upper must have the same shape")
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
        for axis in range(2, len(self.lower)):
            inside &= (points[:, axis] >= self.lower[axis]) & (
                points[:, axis] <= self.upper[axis]
            )
        return inside


class _Disk(Box):
    def contains(self, local: FloatArray) -> BoolArray:
        points = np.asarray(local, dtype=float)
        result: BoolArray = np.isfinite(points).all(axis=1) & (
            np.hypot(points[:, 0] / self.upper[0], points[:, 1] / self.upper[1])
            <= 1 + 8 * np.finfo(float).eps
        )
        return result


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


def _range(
    value: Sequence[float] | None, name: str, *, allow_equal: bool = False
) -> tuple[float, ...] | None:
    if value is None:
        return None
    numbers = _numeric(value, name)
    if numbers.ndim != 1 or len(numbers) not in (2, 3):
        raise ValueError(f"{name} must have length 2 or 3")
    bad = ~np.isfinite(numbers)
    if np.any(bad):
        raise ValueError(f"{name}[{np.flatnonzero(bad)[0]}] must be finite")
    if numbers[0] > numbers[1] or (numbers[0] == numbers[1] and not allow_equal):
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
        edges = np.tile(middle, (2, 1))
        edges[:, 0] = [bounds.lower[0], bounds.upper[0]]
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
    dim: int = 2

    def _evaluate(self, t: FloatArray) -> FloatArray:
        if not len(t):
            return np.empty((0, self.dim))
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
                    if len(values) >= self.dim:
                        return values[: self.dim].T.copy()
                    return np.pad(values.T, ((0, 0), (0, self.dim - len(values))))
                if values.shape != t.shape:
                    raise TypeError("function must return an array of input length")
                coordinates = np.column_stack((t, values))
                return (
                    coordinates
                    if self.dim == 2
                    else np.pad(coordinates, ((0, 0), (0, self.dim - 2)))
                )
            result = np.zeros((len(t), self.dim))
            for i, scalar in enumerate(t):
                raw = self.function(scalar)
                value = _numeric(raw, "function output")
                if self._parametric:
                    if value.shape not in ((2,), (3,)):
                        raise TypeError("function must return two or three coordinates")
                    result[i, : min(self.dim, len(value))] = value[: self.dim]
                else:
                    if value.ndim != 0:
                        raise TypeError("function must return a scalar")
                    result[i, :2] = scalar, value.item()
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
        tolerance = CHORD_TOLERANCE / (self.dim - 1) ** 4
        if self._parametric:
            assert self._range is not None
            lo, hi = self._range[:2]
        else:
            lo, hi = _extent(map, bounds)
            if self._range is not None:
                lo, hi = max(lo, self._range[0]), min(hi, self._range[1])
        if not np.isfinite([lo, hi]).all() or lo > hi:
            return Payload.empty("path", self.dim)
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
            return Payload.empty("path", self.dim)
        t = ts[0] if len(ts) == 1 else np.concatenate(ts)
        labels = ids[0] if len(ids) == 1 else np.concatenate(ids)
        depth: IntArray | None = None
        active = labels[1:] == labels[:-1]
        probes = None
        if 1 < len(t) < MAX_SAMPLES:
            mid = t[:-1] / 2 + t[1:] / 2
            mid = mid if active.all() else mid[active]
            evaluated = self._evaluate(np.concatenate((t, mid)))
            if active.all() and type(map) is SystemMap:
                certified, contained = map._straight_enough(
                    evaluated,
                    len(t),
                    tolerance,
                    bounds.lower,
                    bounds.upper,
                    parametric=self._parametric,
                )
                if certified:
                    if contained:
                        return Payload._trusted(
                            "path",
                            evaluated[: len(t)],
                            np.array([[0, len(t)]], dtype=np.intp),
                        )
                    return self._split_poles(
                        t, evaluated[: len(t)], labels, map, bounds
                    )
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
                if (_sum_rows(delta * delta) <= tolerance**2).all():
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
                    refine = error > tolerance**2
                else:
                    lv = np.isfinite(left).all(axis=1)
                    rv = np.isfinite(right).all(axis=1)
                    mv = np.isfinite(images).all(axis=1)
                    refine = (lv != rv) | (lv & rv & (~mv | (error > tolerance**2)))
                refine &= (mid > left_t) & (mid < right_t)
            chosen = np.flatnonzero(refine)[: MAX_SAMPLES - len(t)]
            if not len(chosen):
                break
            edges = chosen if indices is None else indices[chosen]
            insert = np.zeros(len(t) - 1, dtype=np.bool_)
            insert[edges] = True
            positions = np.arange(len(t)) + np.concatenate(([0], np.cumsum(insert)))
            new_t = np.empty(len(t) + len(edges))
            new_coords = np.empty((len(new_t), self.dim))
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
        extra_coords = np.stack((lc[ids], rc[ids]), axis=1).reshape(-1, self.dim)
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
    dim
        Data dimension; missing coordinates are zero and excess ones are dropped.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        dim: int = 2,
    ) -> None:
        ds = _options(function, use_vectorized, discontinuities, dt)
        super().__init__(
            function, _range(x_range, "x_range"), use_vectorized, ds, dt, False, dim
        )


@dataclass(frozen=True, init=False)
class ParametricSource(_AnalyticSource):
    """Sample a parameterized curve in the requested data dimension.

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
    dim
        Data dimension; missing coordinates are zero and excess ones are dropped.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        t_range: Sequence[float] = (0.0, 1.0),
        *,
        use_vectorized: bool = False,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        dim: int = 2,
    ) -> None:
        ds = _options(function, use_vectorized, discontinuities, dt)
        checked = _range(t_range, "t_range")
        if checked is None:
            raise TypeError("t_range must be a sequence")
        super().__init__(function, checked, use_vectorized, ds, dt, True, dim)


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
    dim
        Number of coordinate columns, defaulting to two.
    """

    data: FloatArray
    kind: Literal["path", "points"]

    def __init__(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        kind: Literal["path", "points"] = "path",
        dim: int = 2,
    ) -> None:
        x = _numeric(xs, "xs")
        if ys is None:
            if x.ndim != 2 or x.shape[1] != dim:
                raise ValueError(f"pairs must have shape (n, {dim})")
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
