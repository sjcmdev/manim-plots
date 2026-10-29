"""Cartesian coordinate systems, registration and frame synchronisation."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Sequence
from typing import Any, NoReturn, Self, Unpack, cast, overload

import numpy as np
from manim import (
    DEFAULT_DOT_RADIUS,
    PURE_YELLOW,
    Dot,
    Mobject,
    VDict,
    VGroup,
    VMobject,
    config,
)
from manim import Axes as NativeAxes
from manim.constants import RendererType
from manim.typing import Point3DLike, Vector3DLike
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.nodes import AffineNode, Chain, SystemMap
from manim_plots.core.sources import Box
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LinePlot,
    Marker,
    ParametricPlot,
    ScatterPlot,
    _CurvePlot,
    _parameterize,
)
from manim_plots.mobjects.axis import Axis, _range
from manim_plots.mobjects.context import playback_context
from manim_plots.mobjects.leaves import (
    FrameLeaf,
    _ArtistOptions,
    _ParametricOptions,
    _reported_updaters,
    _synchronise,
    _VMStyle,
)
from manim_plots.mobjects.legend import Legend, _handle


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

    _color_index: int = 0

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
        self._artists: list[_CurvePlot | ScatterPlot] = []
        self._moving_query: tuple[frozenset[Mobject], bool] | None = None
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
        token = playback_context()
        if token is not None and token == self._poll_token:
            return
        self._poll_token = token
        self._token += 1
        self.x_axis._range_parameter.poll(self._token)
        self.y_axis._range_parameter.poll(self._token)
        for artist in self._artists:
            if isinstance(artist, _CurvePlot):
                artist._poll()
        self._sync_data()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        if self._moving_query is None or self._moving_query[0] is not moving:
            self._moving_query = (moving, self._sync_needed(moving))
        return self._moving_query[1]

    def _sync_needed(self, moving: frozenset[Mobject]) -> bool:
        if not hasattr(self, "frame"):
            return False
        if self.frame in moving:
            return True
        for axis in (self.x_axis, self.y_axis):
            tracker = axis.range.tracker
            if tracker is not None and (callable(tracker) or tracker in moving):
                return True
        for artist in self._artists:
            if isinstance(artist, _CurvePlot) and artist._needs_sync(moving):
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

    @overload
    def plot(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        **kwargs: object,
    ) -> FunctionPlot: ...

    @overload
    def plot(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> LinePlot: ...

    def plot(
        self,
        *args: object,
        **kwargs: object,
    ) -> FunctionPlot | LinePlot:
        """Create and register a function plot or an array line.

        Parameters
        ----------
        *args
            Function, optional x_range and use_vectorized; or array xs and ys.
        **kwargs
            Named inputs, function parameters, native styles and sampling options.
        """
        if args:
            function = args[0]
        elif "function" in kwargs:
            function = kwargs.pop("function")
        else:
            function = kwargs.pop("xs", None)
        if callable(function):
            if len(args) > 3:
                raise TypeError("plot accepts function, x_range and use_vectorized")
            function, _ = _parameterize(function, kwargs)
            x_range = args[1] if len(args) > 1 else kwargs.pop("x_range", None)
            use_vectorized = (
                args[2] if len(args) > 2 else kwargs.pop("use_vectorized", False)
            )
            artist = FunctionPlot(
                function,
                self,
                cast(Sequence[float] | None, x_range),
                cast(bool, use_vectorized),
                **cast(dict[str, Any], kwargs),
            )
            self.add(artist)
            return artist
        if len(args) > 2:
            raise TypeError("plot accepts xs and ys for an array line")
        ys = args[1] if len(args) > 1 else kwargs.pop("ys", None)
        return self.line(
            cast(ArrayLike, function),
            cast(ArrayLike | None, ys),
            **cast(_ArtistOptions, kwargs),
        )

    def line(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> LinePlot:
        """Create and register a straight array line.

        Parameters
        ----------
        xs, ys
            Separate coordinates, or pairs in xs with ys omitted.
        **kwargs
            Native VMobject styles.
        """
        artist = LinePlot(xs, self, ys, **kwargs)
        self.add(artist)
        return artist

    def scatter(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        marker: Mobject | Marker | None = None,
        label: str | None = None,
        clip: bool | float = True,
        **kwargs: Unpack[_VMStyle],
    ) -> ScatterPlot:
        """Create and register independent markers in input order.

        Parameters
        ----------
        xs, ys
            Separate coordinates, or pairs in xs with ys omitted.
        marker
            Marker enum or native template, defaulting to Dot().
        label
            Legend entry text, or None to omit this artist.
        clip
            True, False, or a clipping margin in scene units.
        **kwargs
            Native VMobject styles for the markers.
        """
        artist = ScatterPlot(
            xs, self, ys, marker=marker, label=label, clip=clip, **kwargs
        )
        self.add(artist)
        return artist

    def plot_parametric_curve(
        self,
        function: Callable[..., Any],
        use_vectorized: bool = False,
        **kwargs: Unpack[_ParametricOptions],
    ) -> ParametricPlot:
        """Create and register a parameterized curve.

        Parameters
        ----------
        function
            Callable returning coordinates or coordinate arrays.
        use_vectorized
            Evaluate arrays instead of scalars when true.
        **kwargs
            t_range (default (0, 1)), sampling options and native styles.
        """
        artist = ParametricPlot(function, self, use_vectorized, **kwargs)
        self.add(artist)
        return artist

    def plot_line_graph(
        self,
        x_values: ArrayLike,
        y_values: ArrayLike,
        z_values: ArrayLike | None = None,
        line_color: ParsableManimColor = PURE_YELLOW,
        add_vertex_dots: bool = True,
        vertex_dot_radius: float = DEFAULT_DOT_RADIUS,
        vertex_dot_style: _VMStyle | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> VDict:
        """Return Manim's named line and optional vertex-dot groups.

        Parameters
        ----------
        x_values, y_values, z_values
            Vertex coordinates; the optional z coordinate is ignored in 2D.
        line_color
            Line stroke color, defaulting to PURE_YELLOW.
        add_vertex_dots
            Include a ScatterPlot under vertex_dots when true.
        vertex_dot_radius, vertex_dot_style
            Native Dot radius and style options.
        **kwargs
            Native styles for the line.
        """
        options = kwargs.copy()
        options["color"] = line_color
        line = self.line(x_values, y_values, **options)
        result = VDict([("line_graph", line)])
        if add_vertex_dots:
            marker = Dot(radius=vertex_dot_radius, **(vertex_dot_style or {}))
            result.add(
                [
                    (
                        "vertex_dots",
                        self.scatter(
                            x_values,
                            y_values,
                            marker=marker,
                            clip=kwargs.get("clip", True),
                        ),
                    )
                ]
            )
        return result

    def i2gc(self, x: float, graph: _CurvePlot) -> tuple[float, float]:
        """Evaluate a bound graph's source exactly or by linear interpolation.

        Parameters
        ----------
        x
            Source input, independent of the sampled anchors.
        graph
            Function, array line or parametric artist bound to this system.

        Returns
        -------
        tuple of float
            The two data coordinates.
        """
        if not isinstance(graph, _CurvePlot) or graph._system is not self:
            raise ValueError("graph must be bound to this system")
        coords = graph.source.at(x)[0]
        return float(coords[0]), float(coords[1])

    input_to_graph_coords = i2gc

    def i2gp(self, x: float, graph: _CurvePlot) -> FloatArray:
        """Map an exact source query to a scene point.

        Parameters
        ----------
        x
            Source input.
        graph
            Artist bound to this system.

        Returns
        -------
        FloatArray
            Scene point of shape (3,).
        """
        return self.c2p(*self.i2gc(x, graph))

    input_to_graph_point = i2gp

    def legend(
        self,
        location: str = "upper right",
        *,
        font_size: float = 24,
        buff: float = 0.25,
    ) -> Legend:
        """Create a bound legend for labelled artists in registration order.

        Parameters
        ----------
        location
            One of upper right, upper left, lower left or lower right.
        font_size, buff
            Native text size and entry/corner spacing in scene units.

        Returns
        -------
        Legend
            The newly created legend, attached to this system's family.
        """
        locations = {
            "upper right": (1, 1),
            "upper left": (-1, 1),
            "lower left": (-1, -1),
            "lower right": (1, -1),
        }
        if location not in locations:
            raise ValueError(
                "location must be upper right, upper left, lower left or lower right"
            )
        artists = [a for a in self._artists if a.get_label() is not None]
        if not artists:
            raise ValueError("legend requires an artist with a label")
        legend = Legend(*artists, font_size=font_size, buff=buff)
        corner = np.array([*locations[location], 0.0], dtype=float)
        local = np.where(corner[:2] > 0, self.bounds.upper, self.bounds.lower)
        legend.shift(
            self.frame.mapping.forward(local[None])[0]
            - corner * buff
            - legend.get_corner(corner)
        )
        previous = self.get_legend()
        if previous is not None:
            self.submobjects.remove(previous)
        self.submobjects.append(legend)
        self._legend = legend
        return legend

    def get_legend(self) -> Legend | None:
        """Return the last legend created by this system, or None."""
        return getattr(self, "_legend", None)

    def get_legend_handles_labels(self) -> tuple[list[Mobject], list[str]]:
        """Return independent handles and labels in registration order."""
        artists = [a for a in self._artists if a.get_label() is not None]
        return (
            [_handle(a) for a in artists],
            [cast(str, a.get_label()) for a in artists],
        )

    def scale(
        self,
        scale_factor: float,
        scale_stroke: bool = False,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Scale the frame and optionally all registered artists' strokes.

        Parameters
        ----------
        scale_factor, scale_stroke, about_point, about_edge
            Native VMobject scaling options.
        """
        super().scale(
            scale_factor,
            scale_stroke=scale_stroke,
            about_point=about_point,
            about_edge=about_edge,
        )
        if scale_stroke:
            for artist in self._artists:
                for leaf in artist.get_family():
                    if isinstance(leaf, VMobject):
                        leaf.set_stroke(
                            width=abs(scale_factor) * leaf.get_stroke_width(),
                            family=False,
                        )
                        leaf.set_stroke(
                            width=abs(scale_factor)
                            * leaf.get_stroke_width(background=True),
                            background=True,
                            family=False,
                        )
        return self

    @property
    def artists(self) -> tuple[_CurvePlot | ScatterPlot, ...]:
        """Return registered artists in registration order, excluding copies."""
        return tuple(self._artists)

    def add(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Register artists without parenting them.

        Parameters
        ----------
        *artists
            Artists with this system as their single owner.
        """
        for artist in artists:
            if not isinstance(artist, (_CurvePlot, ScatterPlot)):
                raise TypeError("artists must be plotting artists")
            if artist._system is not None and artist._system is not self:
                raise ValueError("artist is bound to another system")
            if artist not in self._artists:
                if artist._system is None:
                    artist._system = self
                    for leaf in artist.get_family():
                        if isinstance(leaf, _CurvePlot):
                            leaf._system = self
                            leaf._frozen_frame = None
                            leaf._parameter_token = -1
                            leaf._frame_seen = -1
                            leaf.refresh()
                self._artists.append(artist)
        return self

    def remove(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Unregister artists so that they may be bound to another system.

        Parameters
        ----------
        *artists
            Artists to unregister.
        """
        for artist in artists:
            if artist not in self._artists:
                raise ValueError("artist is not registered with this system")
            assert isinstance(artist, (_CurvePlot, ScatterPlot))
            for leaf in artist.get_family():
                if isinstance(leaf, _CurvePlot):
                    leaf._ensure()
                    leaf._system = None
            self._artists.remove(artist)
            artist._system = None
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result._artists = []
        for key, value in self.__dict__.items():
            if key in {"bounds", "_data"}:
                result.__dict__[key] = value
            elif key == "_moving_query":
                result.__dict__[key] = None
            elif key != "_artists":
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result


Axes = CartesianAxes
