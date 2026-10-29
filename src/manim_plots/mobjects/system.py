"""Cartesian coordinate systems, registration and frame synchronisation."""

from __future__ import annotations

import copy
import weakref
from collections.abc import Callable, Iterable, Sequence
from typing import Any, NoReturn, Self, Unpack

import numpy as np
from manim import Axes as NativeAxes
from manim import Mobject, VGroup, VMobject, config
from manim.constants import RendererType
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.nodes import AffineNode, Chain, SystemMap
from manim_plots.core.sources import Box
from manim_plots.mobjects.artists import FunctionPlot
from manim_plots.mobjects.axis import Axis, _range
from manim_plots.mobjects.context import playback_context
from manim_plots.mobjects.leaves import (
    FrameLeaf,
    _PlotOptions,
    _reported_updaters,
    _synchronise,
)


class CartesianAxes(VGroup):
    """Build two Cartesian axes whose frame carries separately registered plots.

    Parameters
    ----------
    x_range, y_range
        Endpoints and optional positive major tick spacing.
    x_length, y_length
        Positive axis lengths, defaulting to Manim's frame-based defaults.
    tips
        Whether to draw the native filled triangle tips.
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        *,
        tips: bool = True,
    ) -> None:
        if config.renderer == RendererType.OPENGL:
            raise ValueError("CartesianAxes requires the Cairo renderer")
        xr = (
            tuple(x_range)
            if x_range is not None
            else (-round(config.frame_x_radius), round(config.frame_x_radius), 1)
        )
        yr = (
            tuple(y_range)
            if y_range is not None
            else (-round(config.frame_y_radius), round(config.frame_y_radius), 1)
        )
        _range(xr, "x_range")
        _range(yr, "y_range")
        self.x_length = float(
            round(config.frame_width) - 2 if x_length is None else x_length
        )
        self.y_length = float(
            round(config.frame_height) - 2 if y_length is None else y_length
        )
        for name, value in (("x_length", self.x_length), ("y_length", self.y_length)):
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        self._artists: weakref.WeakSet[FunctionPlot] = weakref.WeakSet()
        self._actual_updaters: list[Callable[..., Any]] = []
        self._syncing = True
        self._data_version = 0
        self._poll_token: tuple[int, float | str, int] | None = None
        self._token = 0
        super().__init__()
        native = NativeAxes(xr, yr, self.x_length, self.y_length, tips=tips)
        lower = -np.array([self.x_length, self.y_length]) / 2
        self.bounds = Box(lower, -lower)
        self.frame = FrameLeaf(lower, -lower, self)
        self.x_axis = Axis(self, 0, xr, native.x_axis)
        self.y_axis = Axis(self, 1, yr, native.y_axis)
        self.x, self.y = self.x_axis, self.y_axis
        self.submobjects = [self.x_axis, self.y_axis, self.frame]
        self._compile()
        self._syncing = False
        self.add_updater(_synchronise)

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"CartesianAxes has no attribute {name!r}")

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Expose synchronisation only to plays that can change this system."""
        return _reported_updaters(self._actual_updaters, self)

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._actual_updaters = value

    @property
    def x_range(self) -> FloatArray:
        """Return the current immutable x endpoints."""
        return self.x_axis.range.value

    @property
    def y_range(self) -> FloatArray:
        """Return the current immutable y endpoints."""
        return self.y_axis.range.value

    def _compile(self) -> None:
        lower = np.array([self.x_range[0], self.y_range[0]])
        span = np.array([np.ptp(self.x_range), np.ptp(self.y_range)])
        factors = np.array([self.x_length, self.y_length]) / span
        # Signed spans preserve the meaning of reversed ranges.
        factors *= np.sign(
            [self.x_range[1] - self.x_range[0], self.y_range[1] - self.y_range[0]]
        )
        self._data = Chain(
            (
                AffineNode.from_parts(
                    np.diag(factors), self.bounds.lower - lower * factors
                ),
            )
        )
        self._data_version += 1

    def _sync_data(self) -> None:
        if self._syncing:
            return
        if (
            self.x_axis._range_seen == self.x_axis._range_parameter.version
            and self.y_axis._range_seen == self.y_axis._range_parameter.version
        ):
            return
        self._syncing = True
        try:
            self._compile()
            self.x_axis._configure()
            self.y_axis._configure()
        finally:
            self._syncing = False

    def _poll(self) -> None:
        if (
            self.x_axis._range_parameter.tracker is None
            and self.y_axis._range_parameter.tracker is None
        ):
            return
        token = playback_context()
        if token is not None and token == self._poll_token:
            return
        self._poll_token = token
        self._token += 1
        self.x_axis._range_parameter.poll(self._token)
        self.y_axis._range_parameter.poll(self._token)
        self._sync_data()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        if not hasattr(self, "frame"):
            return False
        if self.frame in moving:
            return True
        for axis in (self.x_axis, self.y_axis):
            tracker = axis.range.tracker
            if tracker is not None and (callable(tracker) or tracker in moving):
                return True
        return False

    def _mapping(self) -> SystemMap:
        self._sync_data()
        return SystemMap(self._data, self.frame.mapping)

    def c2p(self, *coords: ArrayLike) -> FloatArray:
        """Convert scalar coordinates, coordinate arrays or rows to scene points.

        Parameters
        ----------
        *coords
            Manim-style coordinate arguments.

        Returns
        -------
        FloatArray
            Shape (3,), (3, n), or (n, 3), following the input convention.
        """
        values = np.asarray(coords, dtype=float)
        if not np.isfinite(values).all():
            index = tuple(int(i) for i in np.argwhere(~np.isfinite(values))[0])
            raise ValueError(f"coords at index {index} must be finite")
        rows = values.ndim == 3
        if rows:
            values = values[0]
            if len(values) == 1:
                values = values[0]
        elif values.ndim == 2 and values.shape[0] == 1:
            values = values[0]
        scalar = values.ndim == 1
        data = np.atleast_2d(values) if scalar or rows else values.T
        if data.shape[1] == 1:
            data = np.column_stack((data, np.zeros(len(data))))
        data = data[:, :2]
        mapping = self._mapping()
        valid = mapping.valid(data)
        if not valid.all():
            sample_index = int(np.flatnonzero(~valid)[0])
            raise ValueError(
                f"coords at index {sample_index} must be inside the scale domain"
            )
        result = mapping.to_screen(data)
        if not np.isfinite(result).all():
            raise ValueError("coords map to a non-finite point")
        return result[0] if scalar else result if rows else result.T

    coords_to_point = c2p

    def p2c(self, point: ArrayLike) -> FloatArray:
        """Invert scene points, refusing singular frames and off-plane points.

        Parameters
        ----------
        point
            One scene point or rows of scene points.

        Returns
        -------
        FloatArray
            Coordinates of shape (2,) or (n, 2).
        """
        values = np.asarray(point, dtype=float)
        if values.ndim not in (1, 2) or values.shape[-1] != 3:
            raise ValueError("point must have shape (3,) or (n, 3)")
        if not np.isfinite(values).all():
            index = tuple(int(i) for i in np.argwhere(~np.isfinite(values))[0])
            raise ValueError(f"point at index {index} must be finite")
        self._sync_data()
        local = self.frame.mapping.inverse(np.atleast_2d(values))
        result = self._data.inverse(local[:, :2])
        if not np.isfinite(result).all():
            raise ValueError("point maps to non-finite coordinates")
        return result[0] if values.ndim == 1 else result

    point_to_coords = p2c

    def __matmul__(self, coords: ArrayLike) -> FloatArray:
        return self.c2p(coords)

    def set_x_range(self, x_range: Sequence[float]) -> Self:
        """Set x endpoints, retaining the existing locator.

        Parameters
        ----------
        x_range
            New endpoints and an optional ignored locator step.
        """
        self.x_axis.range = _range(x_range, "x_range")
        return self

    def set_y_range(self, y_range: Sequence[float]) -> Self:
        """Set y endpoints, retaining the existing locator.

        Parameters
        ----------
        y_range
            New endpoints and an optional ignored locator step.
        """
        self.y_axis.range = _range(y_range, "y_range")
        return self

    def plot(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        **kwargs: Unpack[_PlotOptions],
    ) -> FunctionPlot:
        """Create and register an analytic function plot.

        Parameters
        ----------
        function
            Scalar or vectorized analytic function.
        x_range
            Optional sampling interval and maximum spacing.
        use_vectorized
            Pass arrays to the callable when true.
        **kwargs
            Native VMobject styles and Manim's sampling/shape options.
        """
        artist = FunctionPlot(function, self, x_range, use_vectorized, **kwargs)
        self.add(artist)
        return artist

    def add(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Register artists without parenting them.

        Parameters
        ----------
        *artists
            Function plots with this system as their single owner.
        """
        for artist in artists:
            if not isinstance(artist, FunctionPlot):
                raise TypeError("artists must be FunctionPlot objects")
            if artist._system is not None and artist._system is not self:
                raise ValueError("artist is bound to another system")
            if artist._system is None:
                artist._dirty = True
                artist._frame_seen = -1
            artist._system = self
            self._artists.add(artist)
        return self

    def remove(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Unregister artists so that they may be bound to another system.

        Parameters
        ----------
        *artists
            Artists to unregister.
        """
        for artist in artists:
            if isinstance(artist, FunctionPlot) and artist in self._artists:
                self._artists.discard(artist)
                artist._system = None
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result._artists = weakref.WeakSet()
        for key, value in self.__dict__.items():
            if key in {"bounds", "_data"}:
                result.__dict__[key] = value
            elif key != "_artists":
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result


Axes = CartesianAxes
