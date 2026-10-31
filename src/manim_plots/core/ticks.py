"""Generate keyed ticks, merge explicit entries and plan reusable tick leaves."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from math import ceil, floor, isfinite, log, log10
from numbers import Real
from typing import Literal, Protocol, runtime_checkable

import numpy as np

from manim_plots.core import BoolArray, FloatArray, IntArray
from manim_plots.core.scales import Scale

KEY_DIGITS = 12
MAX_GENERATED = 10_000
SPARES = 8
MULTIPLE_RTOL = 1e-9
DECADE_ATOL = 1e-9

Level = Literal["major", "minor"]


def _finite(value: float, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: int, name: str, minimum: int = 0) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _range(lo: float, hi: float, max_ticks: int) -> tuple[float, float]:
    lo, hi = _finite(lo, "lo"), _finite(hi, "hi")
    _integer(max_ticks, "max_ticks")
    return min(lo, hi), max(lo, hi)


def _count(count: int, name: str) -> None:
    if count > MAX_GENERATED:
        raise ValueError(f"{name} would generate more than MAX_GENERATED ticks")


def round_key(value: float) -> float:
    """Round a finite value to twelve significant digits for tick identity.

    Parameters
    ----------
    value
        Finite tick position.

    Returns
    -------
    float
        Canonical value, with signed zeros identified.
    """
    value = _finite(value, "value")
    return float(f"{value:.{KEY_DIGITS - 1}e}") if value else 0.0


@runtime_checkable
class Locator(Protocol):
    """Describe tick positions, stable identities and density-aware membership."""

    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        """Return finite, in-domain ticks in axis order.

        Parameters
        ----------
        lo, hi
            Finite axis endpoints, in either order.
        scale
            Scale used to reject out-of-domain candidates.
        max_ticks
            Nonnegative estimate of available label space.

        Returns
        -------
        FloatArray
            New one-dimensional array of data positions.
        """
        ...

    def key(self, value: float) -> Hashable:
        """Return a range-independent identity for a finite value.

        Parameters
        ----------
        value
            Tick position.

        Returns
        -------
        Hashable
            Tick identity under this locator's configuration.
        """
        ...

    def contains(
        self, value: float, lo: float, hi: float, scale: Scale, max_ticks: int
    ) -> bool:
        """Check membership at the given range and density.

        Parameters
        ----------
        value
            Position to query.
        lo, hi
            Axis endpoints.
        scale
            Axis scale.
        max_ticks
            Available label count.

        Returns
        -------
        bool
            Whether the locator emits the queried identity.
        """
        ...


def _filter(
    values: FloatArray, lo: float, hi: float, scale: Scale, tolerance: float = 0.0
) -> FloatArray:
    with np.errstate(all="ignore"):
        inside = (
            np.isfinite(values)
            & (values >= lo - tolerance)
            & (values <= hi + tolerance)
        )
        result = values[inside]
        return result[np.isfinite(scale.forward(result))]


def _unique(values: FloatArray, name: str, *, rounded: bool = True) -> None:
    # Match round_key's decimal rounding without a Python loop over the ticks.
    keys = (
        np.char.mod(f"%.{KEY_DIGITS - 1}e", values).astype(np.float64)
        if rounded
        else values
    )
    if len(np.unique(keys)) != len(values):
        raise ValueError(f"{name} locator emitted duplicate keys")


class _LocatorBase:
    _tolerance = 0.0
    _rounded_keys = True

    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        """Return filtered tick positions in axis order.

        Parameters
        ----------
        lo, hi
            Finite endpoints in either order.
        scale
            Scale defining valid tick positions.
        max_ticks
            Nonnegative label-space estimate.

        Returns
        -------
        FloatArray
            New array, empty for coincident endpoints.
        """
        lower, upper = _range(lo, hi, max_ticks)
        if lower == upper:
            return np.empty(0, dtype=np.float64)
        endpoints = (upper, lower) if lo > hi else (lower, upper)
        result = self._values(*endpoints, scale, max_ticks)
        result = np.sort(_filter(result, lower, upper, scale, self._tolerance))
        _unique(result, type(self).__name__, rounded=self._rounded_keys)
        return result[::-1].copy() if lo > hi else result

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        raise NotImplementedError

    def key(self, value: float) -> Hashable:
        """Return the position rounded to twelve significant digits.

        Parameters
        ----------
        value
            Finite data position.

        Returns
        -------
        Hashable
            Canonical tick identity.
        """
        return round_key(value)

    def contains(
        self, value: float, lo: float, hi: float, scale: Scale, max_ticks: int
    ) -> bool:
        """Check whether the current tick list includes the queried key.

        Parameters
        ----------
        value
            Tick position to query.
        lo, hi
            Finite axis endpoints.
        scale
            Axis scale.
        max_ticks
            Nonnegative label-space estimate.

        Returns
        -------
        bool
            Membership at the given range and density.
        """
        key = self.key(value)
        return any(
            self.key(float(v)) == key for v in self.values(lo, hi, scale, max_ticks)
        )


def _bounds(lo: float, hi: float, step: float, tolerance: float = 0) -> tuple[int, int]:
    lower, upper = lo / step, hi / step
    if not isfinite(lower) or not isfinite(upper):
        raise ValueError("step produces unrepresentable multiple indices")
    return ceil(lower - tolerance), floor(upper + tolerance)


def _multiples(start: int, stop: int, step: float, name: str) -> FloatArray:
    count = max(0, stop - start + 1)
    _count(count, name)
    with np.errstate(all="ignore"):
        return (np.arange(count, dtype=np.float64) + start) * step


class MultipleLocator(_LocatorBase):
    """Place ticks at integer multiples of a positive step.

    Parameters
    ----------
    step
        Finite positive spacing, independent of the range and label budget.

    Notes
    -----
    Every tick is computed as an integer multiple k * step, without accumulated
    floating-point addition. Manim anchors at x_min when a range excludes zero:
    for (0.001, 6, 1), Manim places ticks at 0.001, 1.001, ...; this locator places
    them at 1, 2, ..., 6. Keys are the integer indices and stay stable through an
    animated range. Axis decoration may omit the endpoint tick under an arrow tip.
    """

    _rounded_keys = False

    def __init__(self, step: float = 1.0) -> None:
        self.step = _finite(step, "step")
        if self.step <= 0:
            raise ValueError("step must be positive")
        self._tolerance = MULTIPLE_RTOL * self.step

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        lo, hi = min(lo, hi), max(lo, hi)
        start, stop = _bounds(lo, hi, self.step, MULTIPLE_RTOL)
        return _multiples(start, stop, self.step, "step")

    def key(self, value: float) -> int:
        """Return the nearest integer multiple of the configured step.

        Parameters
        ----------
        value
            Finite data position.

        Returns
        -------
        int
            Nearest multiple index.
        """
        value = _finite(value, "value")
        index = value / self.step
        if not isfinite(index):
            raise ValueError("value / step must be finite")
        return round(index)

    def contains(
        self, value: float, lo: float, hi: float, scale: Scale, max_ticks: int
    ) -> bool:
        """Check grid proximity and membership in the current tick list.

        Parameters
        ----------
        value
            Position within ``1e-9 * step`` of an emitted multiple.
        lo, hi
            Axis endpoints.
        scale
            Axis scale.
        max_ticks
            Validated but otherwise ignored label budget.

        Returns
        -------
        bool
            Whether the queried position belongs to this grid and range.
        """
        index = self.key(value)
        values = self.values(lo, hi, scale, max_ticks)
        lower, upper = min(lo, hi), max(lo, hi)
        return (
            abs(value - index * self.step) <= self._tolerance
            and lower - self._tolerance <= value <= upper + self._tolerance
            and bool(np.any(values == index * self.step))
        )


class MaxNLocator(_LocatorBase):
    """Choose the smallest nice step fitting a tick-count budget.

    Parameters
    ----------
    n
        Optional positive upper bound on the number of ticks.
    steps
        Strictly increasing mantissas between one and ten inclusive.
    """

    def __init__(
        self, n: int | None = None, steps: Sequence[float] = (1, 2, 2.5, 5, 10)
    ) -> None:
        if n is not None:
            _integer(n, "n", 1)
        self.n = n
        self.steps = _sequence(steps, "steps", 1, 10, closed_upper=True)

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        lo, hi = min(lo, hi), max(lo, hi)
        budget = max_ticks if self.n is None else min(self.n, max_ticks)
        if budget == 0:
            return np.empty(0, dtype=np.float64)
        magnitude = max(abs(lo), abs(hi))
        span_log = log10(magnitude) + log10(hi / magnitude - lo / magnitude)
        exponent = floor(span_log - log10(budget + 1)) - 1
        while True:
            for mantissa in self.steps:
                step = float(f"{mantissa}e{exponent}")
                if step == 0:
                    continue
                if not isfinite(step):
                    raise ValueError("steps cannot represent a finite tick spacing")
                start, stop = _bounds(lo, hi, step)
                if stop - start + 1 <= budget:
                    values = _multiples(start, stop, step, "n / max_ticks / steps")
                    return values
            exponent += 1


def _sequence(
    values: Sequence[float],
    name: str,
    lower: float,
    upper: float,
    *,
    closed_upper: bool,
) -> tuple[float, ...]:
    try:
        iterator = iter(values)
    except TypeError as exc:
        raise TypeError(f"{name} must be a sequence of real numbers") from exc
    result = tuple(_finite(v, f"{name}[{i}]") for i, v in enumerate(iterator))
    if not result:
        raise ValueError(f"{name} must not be empty")
    for i, value in enumerate(result):
        if value < lower or (value > upper if closed_upper else value >= upper):
            raise ValueError(f"{name}[{i}] is outside the permitted interval")
        if i and value <= result[i - 1]:
            raise ValueError(f"{name}[{i}] must be strictly increasing")
    return result


def _exponent(value: float, base: float) -> int:
    exponent = log(value) / log(base)
    nearest = round(exponent)
    return nearest if abs(exponent - nearest) <= DECADE_ATOL else floor(exponent)


def _thin(
    values: FloatArray, decades: IntArray, max_ticks: int, *, zero: bool = False
) -> FloatArray:
    if max_ticks == 0:
        return np.empty(0, dtype=np.float64)
    if len(values) + zero <= max_ticks:
        return values
    if np.count_nonzero(decades == 0) + zero > max_ticks:
        kept: FloatArray = values[decades == 0]  # max_ticks is only an estimate
        return kept
    stride = 2
    while True:
        keep: BoolArray = decades % stride == 0
        if np.count_nonzero(keep) + zero <= max_ticks:
            return values[keep]
        stride += 1


class LogLocator(_LocatorBase):
    """Place logarithmic ticks at configured subdivisions of each decade.

    Parameters
    ----------
    base
        Finite logarithm base greater than one.
    subs
        Strictly increasing multipliers in ``[1, base)``.
    """

    _rounded_keys = False

    def __init__(self, base: float = 10.0, subs: Sequence[float] = (1.0,)) -> None:
        self.base = _finite(base, "base")
        if self.base <= 1:
            raise ValueError("base must be greater than 1")
        self.subs = _sequence(subs, "subs", 1, self.base, closed_upper=False)

    def _grid(self, lo: float, hi: float) -> tuple[FloatArray, IntArray]:
        if hi <= 0:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.intp)
        lower = max(lo, float.fromhex("0x0.0000000000001p-1022"))
        start, stop = _exponent(lower, self.base) - 1, _exponent(hi, self.base) + 1
        _count((stop - start + 1) * len(self.subs), "base / subs")
        decades = np.arange(start, stop + 1, dtype=np.intp)
        with np.errstate(all="ignore"):
            values = (
                np.power(self.base, decades.astype(np.float64))[:, None] * self.subs
            ).ravel()
        return values, np.repeat(decades, len(self.subs))

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        lo, hi = min(lo, hi), max(lo, hi)
        if max_ticks == 0:
            return np.empty(0, dtype=np.float64)
        values, decades = self._grid(lo, hi)
        with np.errstate(all="ignore"):
            keep = (
                np.isfinite(values)
                & (values > 0)
                & (values >= lo)
                & (values <= hi)
                & np.isfinite(scale.forward(values))
            )
        return _thin(values[keep], decades[keep], max_ticks)

    def _grid_key(self, value: float) -> tuple[int, int] | None:
        decade = _exponent(value, self.base)
        decades = (decade, decade - 1, decade + 1)
        with np.errstate(all="ignore"):
            candidates = (
                np.power(self.base, np.array(decades, dtype=np.float64))[:, None]
                * self.subs
            )
            exact = np.argwhere(candidates == value)
            if len(exact):
                row, index = exact[0]
                return decades[int(row)], int(index)
            distance = np.abs(candidates - value)
            row, index = np.unravel_index(np.argmin(distance), distance.shape)
            if distance[row, index] <= DECADE_ATOL * value:
                return decades[int(row)], int(index)
        return None

    def key(self, value: float) -> Hashable:
        """Return the decade and subdivision index, or an off-grid identity.

        Parameters
        ----------
        value
            Finite positive data position.

        Returns
        -------
        Hashable
            ``(decade, subdivision)`` or ``("off", round_key(value))``.
        """
        value = _finite(value, "value")
        if value <= 0:
            raise ValueError("value must be positive")
        key = self._grid_key(value)
        return key if key is not None else ("off", round_key(value))


class SymLogLocator(LogLocator):
    """Place zero and symmetric logarithmic ticks outside a linear core.

    Parameters
    ----------
    base
        Finite logarithm base greater than one.
    linthresh
        Finite positive minimum decade magnitude.
    subs
        Strictly increasing multipliers in ``[1, base)``.
    """

    def __init__(
        self,
        base: float = 10.0,
        linthresh: float = 1.0,
        subs: Sequence[float] = (1.0,),
    ) -> None:
        super().__init__(base, subs)
        self.linthresh = _finite(linthresh, "linthresh")
        if self.linthresh <= 0:
            raise ValueError("linthresh must be positive")

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        lo, hi = min(lo, hi), max(lo, hi)
        if max_ticks == 0:
            return np.empty(0, dtype=np.float64)
        values, decades = self._grid(self.linthresh, max(abs(lo), abs(hi)))
        with np.errstate(all="ignore"):
            outside = np.power(self.base, decades.astype(np.float64)) >= self.linthresh
        values, decades = values[outside], decades[outside]
        values = np.concatenate((-values, values))
        decades = np.tile(decades, 2)
        with np.errstate(all="ignore"):
            keep = (
                np.isfinite(values)
                & (values != 0)
                & (values >= lo)
                & (values <= hi)
                & np.isfinite(scale.forward(values))
            )
        zero = lo <= 0 <= hi and bool(np.isfinite(scale.forward([0.0]))[0])
        _count(int(np.count_nonzero(keep)) + zero, "base / subs")
        values = _thin(values[keep], decades[keep], max_ticks, zero=zero)
        return np.append(values, 0.0) if zero and max_ticks else values

    def key(self, value: float) -> Hashable:
        """Return zero, a signed grid identity, or an off-grid identity.

        Parameters
        ----------
        value
            Finite signed data position.

        Returns
        -------
        Hashable
            ``(0,)``, ``(sign, decade, subdivision)`` or an off-grid key.
        """
        value = _finite(value, "value")
        if value == 0:
            return (0,)
        key = self._grid_key(abs(value))
        if key is not None:
            with np.errstate(all="ignore"):
                outside = np.power(self.base, float(key[0])) >= self.linthresh
            if outside:
                return (-1 if value < 0 else 1, *key)
        return ("off", round_key(value))


@dataclass(frozen=True)
class Tick:
    """Hold a tick's data position, level, identity and optional label.

    Parameters
    ----------
    value
        Data position.
    level
        Major or minor tick level.
    key
        Stable locator identity.
    label
        Explicit label, or None for automatic formatting.
    """

    value: float
    level: Level
    key: Hashable
    label: str | None = None


class FixedLocator(_LocatorBase):
    """Store explicit positions, optional labels and major or minor levels.

    Parameters
    ----------
    entries
        Values or tuples of one to three items: value, label and level.
    """

    def __init__(self, entries: Iterable[float | tuple[object, ...]]) -> None:
        ticks: list[Tick] = []
        seen: dict[Hashable, int] = {}
        try:
            iterator = iter(entries)
        except TypeError as exc:
            raise TypeError("entries must be iterable") from exc
        for i, entry in enumerate(iterator):
            _count(i + 1, "entries")
            parts = entry if isinstance(entry, tuple) else (entry,)
            if not 1 <= len(parts) <= 3:
                raise ValueError(f"entries[{i}] must contain one to three items")
            raw = parts[0]
            if not isinstance(raw, Real) or isinstance(raw, bool):
                raise TypeError(f"entries[{i}] value must be a real number")
            value = _finite(float(raw), f"entries[{i}] value")
            label = parts[1] if len(parts) > 1 else None
            if label is not None and not isinstance(label, str):
                raise TypeError(f"entries[{i}] label must be str or None")
            level = parts[2] if len(parts) > 2 else "major"
            if not isinstance(level, str):
                raise TypeError(f"entries[{i}] level must be str")
            if level not in {"major", "minor"}:
                raise ValueError(f"entries[{i}] level must be 'major' or 'minor'")
            key = round_key(value)
            if key in seen:
                previous = seen[key]
                raise ValueError(
                    f"entries[{previous}] ({ticks[previous].value!r}) and "
                    f"entries[{i}] ({value!r}) have duplicate keys"
                )
            seen[key] = i
            tick_level: Level = "major" if level == "major" else "minor"
            ticks.append(Tick(value, tick_level, key, label))
        self.entries = tuple(ticks)
        self._labels = {tick.key: tick.label for tick in ticks}
        self._major = np.array(
            [tick.value for tick in ticks if tick.level == "major"], dtype=np.float64
        )
        self._major.flags.writeable = False

    @property
    def minor(self) -> FixedLocator:
        """Return the minor entries as a locator emitting their positions."""
        return FixedLocator(
            (tick.value, tick.label) for tick in self.entries if tick.level == "minor"
        )

    def label(self, value: float) -> str | None:
        """Return a fixed label by canonical position, or None.

        Parameters
        ----------
        value
            Finite data position.

        Returns
        -------
        str or None
            Stored label if present.
        """
        return self._labels.get(round_key(value))

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        return self._major.copy()


class NullLocator(_LocatorBase):
    """Emit no tick positions."""

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        return np.empty(0, dtype=np.float64)


class MinorCountLocator(_LocatorBase):
    """Subdivide major intervals and extend their edge spacings to the range ends.

    Parameters
    ----------
    major
        Locator providing the interval boundaries.
    n
        Positive number of minor ticks between consecutive majors.
    """

    def __init__(self, major: Locator, n: int = 4) -> None:
        _integer(n, "n", 1)
        self.major, self.n = as_locator(major), n

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        majors = np.sort(self.major.values(lo, hi, scale, max_ticks))
        lo, hi = min(lo, hi), max(lo, hi)
        if len(majors) < 2:
            return np.empty(0, dtype=np.float64)
        _count((len(majors) - 1) * self.n, "n")
        with np.errstate(all="ignore"):
            spacing = np.diff(majors) / (self.n + 1)
            fractions = np.arange(1, self.n + 1, dtype=np.float64)
            middle = (majors[:-1, None] + spacing[:, None] * fractions).ravel()
        if np.any(spacing <= 0) or not np.isfinite(spacing).all():
            raise ValueError("major locator must provide increasing, finite intervals")
        before = floor((float(majors[0]) - lo) / float(spacing[0]))
        after = floor((hi - float(majors[-1])) / float(spacing[-1]))
        _count(len(middle) + before + after, "n")
        with np.errstate(all="ignore"):
            values = np.concatenate(
                (
                    majors[0] - np.arange(1, before + 1) * spacing[0],
                    middle,
                    majors[-1] + np.arange(1, after + 1) * spacing[-1],
                )
            )
        values = _filter(values, lo, hi, scale)
        return values


class FunctionLocator(_LocatorBase):
    """Wrap a callable yielding tick positions for two endpoints.

    Parameters
    ----------
    function
        Callable accepting lo and hi and returning an iterable of positions.
    """

    def __init__(self, function: Callable[[float, float], Iterable[float]]) -> None:
        if not callable(function):
            raise TypeError("function must be callable")
        self.function = function

    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        """Call the function with the original endpoints and filter its output.

        Parameters
        ----------
        lo, hi
            Finite endpoints, passed to the callable in their original order.
        scale
            Scale defining valid positions.
        max_ticks
            Validated label-space estimate; the callable controls the count.

        Returns
        -------
        FloatArray
            Unique positions sorted along the axis.
        """
        lower, upper = _range(lo, hi, max_ticks)
        if lower == upper:
            return np.empty(0, dtype=np.float64)
        entries: list[float] = []
        try:
            iterator = iter(self.function(lo, hi))
        except TypeError as exc:
            raise TypeError("function must return an iterable of real numbers") from exc
        for i, value in enumerate(iterator):
            _count(i + 1, "function")
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"function[{i}] must be a real number")
            entries.append(float(value))
        values = np.sort(
            _filter(np.array(entries, dtype=np.float64), lower, upper, scale)
        )
        _unique(values, "FunctionLocator function")
        return values[::-1].copy() if lo > hi else values


def as_locator(obj: object) -> Locator:
    """Accept a locator protocol object or wrap a plain callable.

    Parameters
    ----------
    obj
        Locator or two-endpoint callable.

    Returns
    -------
    Locator
        Original locator or a FunctionLocator wrapper.
    """
    if isinstance(obj, Locator):
        return obj
    if callable(obj):
        return FunctionLocator(obj)
    raise TypeError("obj must be a locator or callable")


def _generated(
    locator: Locator, level: Level, lo: float, hi: float, scale: Scale, max_ticks: int
) -> list[Tick]:
    values = np.asarray(locator.values(lo, hi, scale, max_ticks), dtype=np.float64)
    name = f"{level} locator {type(locator).__name__}"
    if values.ndim != 1:
        raise ValueError(f"{name} values must be one-dimensional")
    values = _filter(
        values,
        min(lo, hi),
        max(lo, hi),
        scale,
        locator._tolerance if isinstance(locator, MultipleLocator) else 0,
    )
    ticks = [Tick(float(value), level, locator.key(float(value))) for value in values]
    if len({tick.key for tick in ticks}) != len(ticks):
        raise ValueError(f"{name} emitted duplicate keys")
    with np.errstate(all="ignore"):
        images = scale.forward(values)
        increasing = scale.increasing == (lo < hi)
        ordered = images[1:] > images[:-1] if increasing else images[1:] < images[:-1]
    if not ordered.all():
        raise ValueError(f"{name} values must be strictly monotonic under scale")
    return ticks


def axis_ticks(
    major: Locator,
    minor: Locator | None,
    lo: float,
    hi: float,
    scale: Scale,
    max_ticks: int,
    *,
    explicit: FixedLocator | None = None,
    mode: Literal["add", "replace"] = "add",
) -> tuple[Tick, ...]:
    """Merge generated and explicit ticks, preserving identities and axis order.

    Parameters
    ----------
    major, minor
        Locators for the two levels; None disables generated minors.
    lo, hi
        Finite endpoints in axis order.
    scale
        Scale used for domain and monotonicity checks.
    max_ticks
        Available label count passed to the locators.
    explicit
        Optional fixed entries with labels and levels.
    mode
        Add explicit entries or replace the generated ticks altogether.

    Returns
    -------
    tuple of Tick
        Interleaved ticks sorted along the axis.
    """
    lower, upper = _range(lo, hi, max_ticks)
    if mode not in {"add", "replace"}:
        raise ValueError("mode must be 'add' or 'replace'")
    if lower == upper:
        return ()
    ticks: dict[tuple[Level, Hashable], Tick] = {}
    if mode == "add":
        for tick in _generated(major, "major", lo, hi, scale, max_ticks):
            ticks[(tick.level, tick.key)] = tick
        if minor is not None:
            for tick in _generated(minor, "minor", lo, hi, scale, max_ticks):
                if not major.contains(tick.value, lo, hi, scale, max_ticks):
                    ticks[(tick.level, tick.key)] = tick
    if explicit is not None:
        for tick in explicit.entries:
            if not lower <= tick.value <= upper:
                continue
            with np.errstate(all="ignore"):
                if not np.isfinite(scale.forward([tick.value]))[0]:
                    continue
            locator = major if tick.level == "major" else minor
            if (
                mode == "add"
                and locator is not None
                and locator.contains(tick.value, lo, hi, scale, max_ticks)
            ):
                key = locator.key(tick.value)
            else:
                key = ("fixed", round_key(tick.value)) if mode == "add" else tick.key
            ticks[(tick.level, key)] = Tick(tick.value, tick.level, key, tick.label)
    return tuple(sorted(ticks.values(), key=lambda tick: tick.value, reverse=lo > hi))


@dataclass(frozen=True)
class Pool:
    """Describe reusable tick identities and spare hidden leaves.

    Parameters
    ----------
    keys
        Level and identity pairs in first-appearance order.
    spares
        Number of spare leaves reserved for unanticipated ticks.
    """

    keys: tuple[tuple[Level, Hashable], ...]
    spares: int


def plan_pool(
    ticks_at: Callable[[float], Sequence[Tick]],
    alphas: Iterable[float],
    spares: int = SPARES,
) -> Pool:
    """Collect tick identities along a sampled animation path.

    Parameters
    ----------
    ticks_at
        Callable returning the ticks at one animation parameter.
    alphas
        Parameters to sample, in the caller's chosen order.
    spares
        Nonnegative number of hidden spare leaves.

    Returns
    -------
    Pool
        Union of level and key pairs in order of first appearance.
    """
    _integer(spares, "spares")
    keys = dict.fromkeys(
        (tick.level, tick.key) for alpha in alphas for tick in ticks_at(alpha)
    )
    return Pool(tuple(keys), spares)


class LogitLocator(_LocatorBase):
    """Locate probability decades, their complements, and one half."""

    _rounded_keys = False

    def key(self, value: float) -> float:
        """Keep distinct probability ticks near one distinct.

        Parameters
        ----------
        value
            Finite probability tick position.

        Returns
        -------
        float
            Exact, range-independent probability identity.
        """
        return _finite(value, "value")

    def _values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        lower, upper = sorted((lo, hi))
        if lower <= 0 or upper >= 1:
            raise ValueError("logit range must be inside (0, 1)")
        if max_ticks == 0:
            return np.empty(0, dtype=float)
        count = min(323, ceil(-log10(min(lower, 1 - upper))))
        decades = 10.0 ** -np.arange(1, count + 1, dtype=float)
        stride = 1
        while True:
            selected = decades[::stride]
            values: FloatArray = np.unique(np.r_[selected, 0.5, 1 - selected])
            values = values[(values >= lower) & (values <= upper)]
            if len(values) <= max_ticks:
                return values
            if stride >= count:
                kept: FloatArray = values[values == 0.5]
                return kept
            stride *= 2
