"""Vectorized one-dimensional scales with explicit domains."""

from collections.abc import Callable
from dataclasses import dataclass
from numbers import Real
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike

from manim_plots.core import BoolArray, FloatArray

MINPOS_UNKNOWN = 1e-300


@runtime_checkable
class Scale(Protocol):
    """Describe a monotonic transform and its data-space domain."""

    @property
    def domain(self) -> tuple[float, float]:
        """Return the lower and upper data-space bounds."""
        ...

    @property
    def closed(self) -> tuple[bool, bool]:
        """Return whether each domain endpoint is included."""
        ...

    @property
    def increasing(self) -> bool:
        """Return the declared monotonic direction."""
        ...

    def forward(self, x: ArrayLike) -> FloatArray:
        """Transform data values, returning NaN for invalid values.

        Parameters
        ----------
        x
            Scalar or array-like data coordinates.

        Returns
        -------
        FloatArray
            Transformed values with the input shape.
        """
        ...

    def inverse(self, u: ArrayLike) -> FloatArray:
        """Recover data values, returning NaN for invalid values.

        Parameters
        ----------
        u
            Scalar or array-like transformed coordinates.

        Returns
        -------
        FloatArray
            Data values with the input shape.
        """
        ...

    def limit_range(self, lo: float, hi: float, minpos: float) -> tuple[float, float]:
        """Normalize range endpoints into the domain without reversing them.

        Parameters
        ----------
        lo, hi
            Finite range endpoints in either order.
        minpos
            Finite positive distance used at excluded endpoints.

        Returns
        -------
        tuple of float
            The normalized endpoints in their original order.
        """
        ...


def _inside(
    x: FloatArray, domain: tuple[float, float], closed: tuple[bool, bool]
) -> BoolArray:
    lo, hi = domain
    return (
        np.isfinite(x)
        & ((x >= lo) if closed[0] else (x > lo))
        & ((x <= hi) if closed[1] else (x < hi))
    )


def _real(value: float, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    return float(value)


def _evaluate(
    values: ArrayLike,
    function: Callable[[FloatArray], ArrayLike],
    domain: tuple[float, float],
    closed: tuple[bool, bool],
    *,
    inverse: bool = False,
) -> FloatArray:
    with np.errstate(all="ignore"):
        x = np.asarray(values, dtype=np.float64)
        mask = np.isfinite(x) if inverse else _inside(x, domain, closed)
        result = np.full(x.shape, np.nan, dtype=np.float64)
        if np.any(mask):
            output = np.asarray(function(x[mask]), dtype=np.float64)
            if output.shape != x[mask].shape:
                raise ValueError(
                    "function must return vectorized output with the input shape"
                )
            result[mask] = output
        good = np.isfinite(result)
        if inverse:
            good &= _inside(result, domain, closed)
        return np.where(good, result, np.nan)


class _ScaleBase:
    @property
    def domain(self) -> tuple[float, float]:
        """Return the open real line."""
        return (-np.inf, np.inf)

    @property
    def closed(self) -> tuple[bool, bool]:
        """Return the inclusion of the domain endpoints."""
        return (False, False)

    @property
    def increasing(self) -> bool:
        """Return whether the scale increases with its input."""
        return True

    def limit_range(self, lo: float, hi: float, minpos: float) -> tuple[float, float]:
        """Move excluded endpoints into the domain, retaining range order.

        Parameters
        ----------
        lo, hi
            Finite range endpoints, in either order.
        minpos
            Finite positive distance inside an open endpoint.

        Returns
        -------
        tuple of float
            Normalized Python floats.

        Raises
        ------
        ValueError
            If an endpoint is non-finite, minpos is invalid, or both endpoints
            are outside the domain on the same side.
        """
        lo = _real(lo, "lo")
        hi = _real(hi, "hi")
        minpos = _real(minpos, "minpos")
        if not np.isfinite(lo):
            raise ValueError("lo must be finite")
        if not np.isfinite(hi):
            raise ValueError("hi must be finite")
        if not np.isfinite(minpos) or minpos <= 0:
            raise ValueError("minpos must be finite and positive")
        lower, upper = self.domain
        values = np.array([lo, hi])
        below = values < lower if self.closed[0] else values <= lower
        above = values > upper if self.closed[1] else values >= upper
        if below.all() or above.all():
            raise ValueError("lo and hi are outside the domain on the same side")
        with np.errstate(all="ignore"):
            if np.any(below):
                values[below] = (
                    lower
                    if self.closed[0]
                    else max(lower + minpos, float(np.nextafter(lower, np.inf)))
                )
            if np.any(above):
                values[above] = (
                    upper
                    if self.closed[1]
                    else min(upper - minpos, float(np.nextafter(upper, -np.inf)))
                )
        return float(values[0]), float(values[1])


@dataclass(frozen=True)
class LinearScale(_ScaleBase):
    """Map finite data to itself over the open real line."""

    def forward(self, x: ArrayLike) -> FloatArray:
        """Return a new array containing finite inputs and NaN elsewhere.

        Parameters
        ----------
        x
            Scalar or array-like data.

        Returns
        -------
        FloatArray
            Identity transform with the input shape.
        """
        if type(self) is not LinearScale:
            return _evaluate(x, lambda values: values, self.domain, self.closed)
        with np.errstate(all="ignore"):
            values = np.asarray(x, dtype=np.float64)
            return np.where(np.isfinite(values), values, np.nan)

    def inverse(self, u: ArrayLike) -> FloatArray:
        """Return the identity inverse on finite input.

        Parameters
        ----------
        u
            Scalar or array-like transformed data.

        Returns
        -------
        FloatArray
            Data values with the input shape.
        """
        return self.forward(u)


@dataclass(frozen=True)
class LogScale(_ScaleBase):
    """Map positive values to logarithms of a real base.

    Parameters
    ----------
    base
        Finite positive logarithm base other than one.
    """

    base: float = 10.0

    def __post_init__(self) -> None:
        base = _real(self.base, "base")
        if not np.isfinite(base) or base <= 0 or base == 1:
            raise ValueError("base must be finite, positive and different from 1")
        object.__setattr__(self, "base", base)

    @property
    def domain(self) -> tuple[float, float]:
        """Return the open positive real line."""
        return (0.0, np.inf)

    @property
    def increasing(self) -> bool:
        """Return whether the base exceeds one."""
        return self.base > 1

    def forward(self, x: ArrayLike) -> FloatArray:
        """Take logarithms of finite positive data.

        Parameters
        ----------
        x
            Scalar or array-like data.

        Returns
        -------
        FloatArray
            Logarithms, with NaN for excluded values.
        """
        return _evaluate(
            x, lambda v: np.log(v) / np.log(self.base), self.domain, self.closed
        )

    def inverse(self, u: ArrayLike) -> FloatArray:
        """Raise the base to finite exponents.

        Parameters
        ----------
        u
            Scalar or array-like exponents.

        Returns
        -------
        FloatArray
            Positive data values, or NaN when the result is invalid.
        """
        return _evaluate(
            u, lambda v: np.power(self.base, v), self.domain, self.closed, inverse=True
        )


@dataclass(frozen=True)
class SymLogScale(_ScaleBase):
    """Use matplotlib's linear core and symmetric logarithmic wings.

    Parameters
    ----------
    base
        Finite logarithm base greater than one.
    linthresh
        Finite positive boundary of the linear core.
    linscale
        Finite positive extent of the linear core in logarithmic units.
    """

    base: float = 10.0
    linthresh: float = 1.0
    linscale: float = 1.0

    def __post_init__(self) -> None:
        for name in ("base", "linthresh", "linscale"):
            value = _real(getattr(self, name), name)
            minimum = 1 if name == "base" else 0
            if not np.isfinite(value) or value <= minimum:
                raise ValueError(f"{name} must be finite and greater than {minimum}")
            object.__setattr__(self, name, value)

    def _forward(self, x: FloatArray) -> FloatArray:
        a = self.linscale / (1 - 1 / self.base)
        inner = np.abs(x) <= self.linthresh
        result = np.empty_like(x)
        result[inner] = x[inner] * a
        outer = x[~inner]
        result[~inner] = (
            np.sign(outer)
            * self.linthresh
            * (a + (np.log(np.abs(outer)) - np.log(self.linthresh)) / np.log(self.base))
        )
        return result

    def _inverse(self, u: FloatArray) -> FloatArray:
        a = self.linscale / (1 - 1 / self.base)
        inner = np.abs(u) <= self.linthresh * a
        result = np.empty_like(u)
        result[inner] = u[inner] / a
        outer = u[~inner]
        result[~inner] = np.sign(outer) * np.exp(
            np.log(self.linthresh)
            + (np.abs(outer) / self.linthresh - a) * np.log(self.base)
        )
        return result

    def forward(self, x: ArrayLike) -> FloatArray:
        """Apply the linear core or a signed logarithmic wing.

        Parameters
        ----------
        x
            Scalar or array-like data.

        Returns
        -------
        FloatArray
            Transformed values with the input shape.
        """
        return _evaluate(x, self._forward, self.domain, self.closed)

    def inverse(self, u: ArrayLike) -> FloatArray:
        """Invert the linear core and signed logarithmic wings.

        Parameters
        ----------
        u
            Scalar or array-like transformed data.

        Returns
        -------
        FloatArray
            Data values with the input shape.
        """
        return _evaluate(u, self._inverse, self.domain, self.closed, inverse=True)


class FunctionScale(_ScaleBase):
    """Validate a user-supplied monotonic transform and inverse.

    Parameters
    ----------
    forward, inverse
        Callables accepting arrays and returning arrays with the same shape.
    domain
        Ordered pair of real bounds; infinite bounds are allowed when open.
    closed
        Inclusion flags for the lower and upper bounds.
    increasing
        Declared monotonic direction.

    Notes
    -----
    Construction attempts to falsify vectorization, finite output, monotonicity
    and round-trip inversion on fixed samples. This heuristic is blind to a
    reversal between samples.
    """

    def __init__(
        self,
        forward: Callable[[FloatArray], ArrayLike],
        inverse: Callable[[FloatArray], ArrayLike],
        domain: tuple[float, float],
        closed: tuple[bool, bool] = (False, False),
        increasing: bool = True,
    ) -> None:
        if not callable(forward):
            raise TypeError("forward must be callable")
        if not callable(inverse):
            raise TypeError("inverse must be callable")
        if (
            not isinstance(closed, (tuple, list))
            or len(closed) != 2
            or any(not isinstance(v, bool) for v in closed)
        ):
            raise TypeError("closed must be a pair of bool")
        if not isinstance(increasing, bool):
            raise TypeError("increasing must be a bool")
        if not isinstance(domain, (tuple, list)) or len(domain) != 2:
            raise TypeError("domain must be a pair of real numbers")
        lo, hi = _real(domain[0], "domain[0]"), _real(domain[1], "domain[1]")
        if np.isnan(lo) or np.isnan(hi) or lo >= hi:
            raise ValueError("domain must have ordered non-NaN bounds")
        for i, (bound, included) in enumerate(zip((lo, hi), closed, strict=True)):
            if not np.isfinite(bound) and included:
                raise ValueError(f"domain[{i}] is infinite but closed[{i}] is True")
        self._forward_function = forward
        self._inverse_function = inverse
        self._domain = (lo, hi)
        self._closed = (closed[0], closed[1])
        self._increasing = increasing
        self._falsify()

    @property
    def domain(self) -> tuple[float, float]:
        """Return the declared data-space bounds."""
        return self._domain

    @property
    def closed(self) -> tuple[bool, bool]:
        """Return the inclusion flags of the domain bounds."""
        return self._closed

    @property
    def increasing(self) -> bool:
        """Return the declared monotonic direction."""
        return self._increasing

    def _samples(self) -> FloatArray:
        lo, hi = self.domain
        with np.errstate(all="ignore"):
            if np.isfinite(lo) and np.isfinite(hi):
                weights = (np.arange(64) + 0.5) / 64
                samples = lo + (hi - lo) * (np.arange(64) + 0.5) / 64
                if not np.isfinite(samples).all():
                    samples = lo * (1 - weights) + hi * weights
            elif np.isfinite(lo):
                samples = lo + np.logspace(-6, 6, 64)
            elif np.isfinite(hi):
                samples = hi - np.logspace(-6, 6, 64)
            else:
                positive = np.logspace(-6, 6, 32)
                samples = np.concatenate((-positive, [0.0], positive))
        ends = [v for v, c in zip(self.domain, self.closed, strict=True) if c]
        return np.sort(np.concatenate((samples, ends)))

    @staticmethod
    def _vectorized(
        function: Callable[[FloatArray], ArrayLike], samples: FloatArray, name: str
    ) -> FloatArray:
        try:
            with np.errstate(all="ignore"):
                output = function(samples.copy())
                if not isinstance(output, np.ndarray) or output.shape != samples.shape:
                    raise ValueError("output shape does not match input")
                result = np.array(output, dtype=np.float64, copy=True)
        except Exception as exc:
            raise ValueError(
                f"{name} is not vectorized at sample 0 ({samples[0]!r})"
            ) from exc
        for i, sample in enumerate(samples):
            try:
                with np.errstate(all="ignore"):
                    single = np.asarray(function(np.array(sample)), dtype=np.float64)
                    agrees = single.shape == () and bool(
                        np.isclose(
                            result[i], single, rtol=1e-12, atol=0, equal_nan=True
                        )
                    )
            except Exception as exc:
                raise ValueError(
                    f"{name} is not vectorized at sample {i} ({sample!r})"
                ) from exc
            if not agrees:
                raise ValueError(f"{name} is not vectorized at sample {i} ({sample!r})")
        return result

    def _falsify(self) -> None:
        samples = self._samples()
        images = self._vectorized(self._forward_function, samples, "forward")
        restored = self._vectorized(self._inverse_function, images, "inverse")
        finite = np.isfinite(images)
        if not finite.all():
            i = int(np.flatnonzero(~finite)[0])
            raise ValueError(f"forward is not finite at sample {i} ({samples[i]!r})")
        ordered = (
            images[1:] > images[:-1] if self.increasing else images[1:] < images[:-1]
        )
        if not ordered.all():
            i = int(np.flatnonzero(~ordered)[0]) + 1
            raise ValueError(f"forward is not monotonic at sample {i} ({samples[i]!r})")
        with np.errstate(all="ignore"):
            good = np.abs(restored - samples) <= 1e-9 * np.abs(samples) + 1e-12
        if not good.all():
            i = int(np.flatnonzero(~good)[0])
            raise ValueError(
                f"inverse round trip failed at sample {i} ({samples[i]!r})"
            )

    def forward(self, x: ArrayLike) -> FloatArray:
        """Call the user's transform only on finite, in-domain input.

        Parameters
        ----------
        x
            Scalar or array-like data.

        Returns
        -------
        FloatArray
            Transformed values, with NaN for invalid input or output.
        """
        return _evaluate(x, self._forward_function, self.domain, self.closed)

    def inverse(self, u: ArrayLike) -> FloatArray:
        """Call the user's inverse only on finite input.

        Parameters
        ----------
        u
            Scalar or array-like transformed data.

        Returns
        -------
        FloatArray
            Data values, with NaN outside the domain or for non-finite values.
        """
        return _evaluate(
            u, self._inverse_function, self.domain, self.closed, inverse=True
        )
