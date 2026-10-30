"""Artists derived from the numeric Source, Map and Shape pipeline."""

from __future__ import annotations

import copy
import inspect
import warnings
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from math import isfinite
from numbers import Real
from typing import Any, Self, Unpack, cast

import numpy as np
from manim import (
    BLUE,
    DEFAULT_DOT_RADIUS,
    GREEN,
    ORANGE,
    PURPLE,
    RED,
    TEAL,
    WHITE,
    YELLOW,
    Circle,
    Cross,
    Dot,
    Mobject,
    Square,
    Star,
    Triangle,
    VGroup,
    VMobject,
)
from manim.animation.transform import _MethodAnimation
from manim.typing import PathFuncType, Point3DLike, Vector3DLike
from manim.utils.color import ManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray, ManimPlotsWarning
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import (
    AffineNode,
    Chain,
    FrameMap,
    FunctionNode,
    Node,
    SystemMap,
)
from manim_plots.core.params import Parameter
from manim_plots.core.payload import Payload, split_segments
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.shape import corners, densify, smooth
from manim_plots.core.shape import dash as dash_path
from manim_plots.core.sources import (
    ArraySource,
    Box,
    FunctionSource,
    ParametricSource,
    Source,
)
from manim_plots.mobjects.context import (
    WriterContext,
    affine_context,
    animation_context,
    buffer_write,
    playback_context,
    writer_context,
)
from manim_plots.mobjects.leaves import (
    _STRAIGHT,
    Leaf,
    _ArtistOptions,
    _ClipInput,
    _ClipPair,
    _ClipValue,
    _synchronise,
    _VMStyle,
)

COLOR_CYCLE: tuple[ManimColor, ...] = (
    WHITE,
    BLUE,
    YELLOW,
    GREEN,
    RED,
    PURPLE,
    ORANGE,
    TEAL,
)


class LineStyle(Enum):
    """Select a solid, dashed or dotted stroke in scene units."""

    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class Marker(Enum):
    """Select a native Manim marker with the default dot's width."""

    DOT = "dot"
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    CROSS = "cross"
    STAR = "star"


def _cycle_style(
    system: mp.CartesianAxes, style: _VMStyle, *, scatter: bool = False
) -> int:
    system = system.parent if system.parent is not None else system
    index = system._color_index
    keys = (
        ("color", "stroke_color", "fill_color")
        if scatter
        else ("color", "stroke_color")
    )
    if not any(key in style for key in keys):
        style["color"] = system._cycle[index % len(system._cycle)]
        system._color_index = index + 1
    return index


def _validate_label(label: str | None) -> None:
    if label is not None and not isinstance(label, str):
        raise TypeError("label must be a string or None")


def _validate_clip(value: object) -> _ClipValue:
    if isinstance(value, (tuple, list)) and len(value) != 2:
        raise ValueError("clip must contain two axis entries")
    entries = value if isinstance(value, (tuple, list)) else (value,)
    for index, entry in enumerate(entries):
        if not isinstance(entry, (bool, Real)):
            raise TypeError(f"clip[{index}] must be bool or a real margin")
        if not isfinite(entry):
            raise ValueError(f"clip[{index}] must be finite")
    return cast(_ClipValue, tuple(value) if isinstance(value, list) else value)


def _clip_axes(value: _ClipValue) -> _ClipPair:
    return value if isinstance(value, tuple) else (value, value)


def _clip_has_margin(value: _ClipValue) -> bool:
    return any(not isinstance(axis, bool) for axis in _clip_axes(value))


def _clip_box(system: mp.CartesianAxes, value: _ClipValue) -> Box:
    if not _clip_has_margin(value):
        return system.bounds
    bounds = system.bounds
    origin = np.zeros((3, 2))
    origin[1:] = np.eye(2)
    placed = system.frame.mapping.forward(origin)
    units = np.linalg.norm(placed[1:] - placed[0], axis=1)
    margin = (
        np.array(
            [0.0 if isinstance(axis, bool) else axis for axis in _clip_axes(value)],
            dtype=float,
        )
        / units
    )
    span = bounds.upper - bounds.lower
    # A fitted frame can leave roundoff-sized remnants of a collapsed interval.
    if np.any(span + 2 * margin <= 8 * np.finfo(float).eps * span):
        raise ValueError("clip margin narrows the rectangle to nothing")
    return type(bounds)(bounds.lower - margin, bounds.upper + margin)


def _unclipped_box(bounds: Box, axes: _ClipPair, coords: FloatArray) -> Box:
    lower, upper = bounds.lower.copy(), bounds.upper.copy()
    for index, axis in enumerate(axes):
        if axis is False:
            values = coords[:, index]
            finite = values[np.isfinite(values)]
            if len(finite):
                lower[index] = min(lower[index], float(np.min(finite)))
                upper[index] = max(upper[index], float(np.max(finite)))
    return Box(lower, upper)


def _dash_pattern(
    line_style: LineStyle, dash: tuple[float, float] | None
) -> tuple[float, float] | None:
    if not isinstance(line_style, LineStyle):
        raise TypeError("line_style must be a LineStyle")
    if dash is not None:
        if not isinstance(dash, tuple):
            raise TypeError("dash must be an (on, off) tuple")
        if len(dash) != 2:
            raise ValueError("dash must contain on and off")
        on, off = dash
        if any(not isinstance(v, Real) or isinstance(v, bool) for v in dash):
            raise TypeError("dash lengths must be real numbers")
        if not np.isfinite(dash).all() or on <= 0 or off < 0:
            raise ValueError("dash requires finite on > 0 and off >= 0")
        return dash
    return {
        LineStyle.SOLID: None,
        LineStyle.DASHED: (0.2, 0.1),
        LineStyle.DOTTED: (0.03, 0.07),
    }[line_style]


class _SampleWarnings:
    def __init__(self) -> None:
        self._seen: object | None = None
        self._warned: object | None = None

    def warn(
        self,
        system: mp.CartesianAxes,
        source: Source,
        message: str,
        versions: tuple[int, ...] = (),
    ) -> None:
        seen = (id(system), id(source), system._data_version, versions)
        if self._seen == seen:
            return
        self._seen = seen
        token = playback_context()
        change = seen if token is None else (token[0], token[2], id(system), id(source))
        if self._warned != change:
            self._warned = change
            warnings.warn(message, ManimPlotsWarning, stacklevel=4)


class _CurvePlot(Leaf):
    def __init__(
        self,
        source: Source,
        system: mp.CartesianAxes,
        *,
        use_smoothing: bool = True,
        label: str | None = None,
        line_style: LineStyle | None = None,
        dash: tuple[float, float] | None = None,
        clip: _ClipInput = True,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        _validate_label(label)
        clip_value = _validate_clip(clip)
        _clip_box(system, clip_value)
        self._label = label
        self._clip = clip_value
        self._clip_has_margin = _clip_has_margin(clip_value)
        root = system.parent if system.parent is not None else system
        if line_style is None:
            styles = system.theme.line_styles
            line_style = (
                styles[root._color_index % len(styles)] if styles else LineStyle.SOLID
            )
        self.line_style = line_style
        self.dash = dash
        self._dash = _dash_pattern(line_style, dash)
        _cycle_style(system, kwargs)
        self.source = source
        if not hasattr(self, "parameters"):
            self.parameters: dict[str, Parameter[Any]] = {}
        self._parameter_versions: dict[str, int] = {}
        self._parameter_token = -1
        self.use_smoothing = use_smoothing
        self._data_seen = -1
        self._local = np.empty((0, 3))
        self._geometry_payload = Payload.empty("path", 2)
        self._render_segments = self._geometry_payload.segments
        self._reversed = False
        self._dense = False
        if not hasattr(self, "_sample_warnings"):
            self._sample_warnings = _SampleWarnings()
        self._source_invalid = (
            isinstance(source, ArraySource) and not np.isfinite(source.data).all()
        )
        self._parameter_animation = False
        super().__init__(system=system, **kwargs)
        self.add_updater(_synchronise)
        self._rebuild()

    def set_label(self, label: str | None) -> Self:
        """Set the legend label.

        Parameters
        ----------
        label
            Entry text, or None to omit this artist.
        """
        _validate_label(label)
        self._label = label
        return self

    def get_label(self) -> str | None:
        """Return the legend label, or None when unset."""
        return self._label

    def set_clip(self, value: _ClipInput) -> Self:
        """Set clipping and rebuild the artist.

        Parameters
        ----------
        value
            True clips at the viewport, False disables clipping, and a finite
            margin in scene units expands or narrows it. A tuple or list
            ``(cx, cy)`` applies these policies independently to x and y.

        Returns
        -------
        Self
            This artist after rebuilding.
        """
        clip = _validate_clip(value)
        if self._system is not None:
            _clip_box(self._system, clip)
        self._clip = clip
        self._clip_has_margin = _clip_has_margin(clip)
        self._dirty = True
        self._ensure()
        return self

    def get_clip(self) -> _ClipValue:
        """Return the clipping policy or margin in scene units.

        Returns
        -------
        bool or float or tuple
            The supplied policy; per-axis entries are returned as ``(cx, cy)``,
            including when set from a list.
        """
        return self._clip

    def _poll(self) -> None:
        system = self._system
        if system is None or self._parameter_token == system._token:
            return
        self._parameter_token = system._token
        for parameter in self.parameters.values():
            parameter.poll(system._token)

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        for parameter in self.parameters.values():
            tracker = parameter.tracker
            if tracker is not None and (callable(tracker) or tracker in moving):
                return True
        return False

    def _parameters_changed(self) -> bool:
        for name, parameter in self.parameters.items():
            if self._parameter_versions.get(name) != parameter.version:
                return True
        return False

    def _frame(self) -> FrameMap:
        assert self._system is not None
        for _, frozen, excluded in self._system.frame._suspensions:
            if frozen is not None and self not in excluded:
                return frozen
        return (
            self._frozen_frame
            if self._frozen_frame is not None
            else self._system.frame.mapping
        )

    def _ensure(self) -> None:
        if self._alignment_locked:
            return
        system = self._system
        state = self._lifecycle.state
        if system is None or state is lc.State.TRANSIENT or state is lc.State.REMOVED:
            return
        if self._lifecycle.state is lc.State.SHAPED:
            if self._shape is not None and self._frame_seen != system.frame.version:
                self._cache = self._frame().forward(self._shape)
                self._frame_seen = system.frame.version
            return
        system._sync_data()
        if (
            self._dirty
            or self._data_seen != system._data_version
            or (self.parameters and self._parameters_changed())
        ):
            self._rebuild()
        elif self._frame_seen != system.frame.version:
            frame = self._frame()
            if self._clip_has_margin:
                self._rebuild()
            elif self._dash is not None or self._dense == frame.is_affine:
                self._place(frame)
            else:
                self._cache = frame.forward(self._local)
                self._frame_seen = system.frame.version

    def _rebuild(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        frame = self._frame()
        collapsed = [
            i
            for i, axis in enumerate((system.x, system.y))
            if axis.range.value[0] == axis.range.value[1]
        ]
        if collapsed:
            local = self._geometry_payload.coords.copy()
            local[:, collapsed] = 0
            self._geometry_payload = Payload._trusted(
                "path", local, self._geometry_payload.segments
            )
            self._place(frame)
            self._data_seen = system._data_version
            self._dirty = False
            return
        mapping = SystemMap(system._data, frame)
        bounds = _clip_box(system, self._clip)
        clip_axes = _clip_axes(self._clip)
        unclipped = any(axis is False for axis in clip_axes)
        clipped = any(axis is not False for axis in clip_axes)
        sampling_bounds = bounds
        if clip_axes[0] is False:
            extent = None
            if isinstance(self.source, ArraySource):
                finite = self.source.data[np.isfinite(self.source.data).all(axis=1)]
                if len(finite):
                    extent = system._data.forward(finite)[:, 0]
            elif isinstance(self.source, FunctionSource) and self.source._range:
                extent = system._data.forward(
                    np.column_stack((self.source._range[:2], np.zeros(2)))
                )[:, 0]
            if extent is not None:
                lower, upper = bounds.lower.copy(), bounds.upper.copy()
                lower[0] = min(lower[0], float(np.min(extent)))
                upper[0] = max(upper[0], float(np.max(extent)))
                sampling_bounds = Box(lower, upper)
        payload = self.source.sample(mapping, sampling_bounds)
        if isinstance(self.source, ArraySource):
            invalid = self._source_invalid or not len(self.source.data)
        else:
            invalid = (
                not len(payload.coords)
                or (payload.valid is not None and not payload.valid.all())
                or len(payload.segments)
                > len(getattr(self.source, "discontinuities", ())) + 1
            )
        payload = system._data.apply_payload(payload)
        if invalid or (payload.valid is not None and not payload.valid.all()):
            self._sample_warnings.warn(
                system,
                self.source,
                "source is empty or contains invalid samples or a pole; "
                "the path is split",
                tuple(p.version for p in self.parameters.values()),
            )
        if clipped and self.use_smoothing and len(payload.segments) > 1:
            # Keep visible samples and their brackets; remote pole tails ring globally.
            trim_bounds = (
                _unclipped_box(bounds, clip_axes, payload.coords)
                if unclipped
                else bounds
            )
            inside = trim_bounds.contains(payload.coords)
            keep = inside.copy()
            keep[:-1] |= inside[1:]
            keep[1:] |= inside[:-1]
            if payload.valid is not None:
                keep &= payload.valid
            if inside.any():
                payload = Payload(
                    "path",
                    payload.coords,
                    split_segments(payload.segments, keep),
                    valid=keep,
                )
        payload = (smooth if self.use_smoothing else corners)(payload, bounds)
        if clipped:
            if unclipped:
                bounds = _unclipped_box(bounds, clip_axes, payload.coords)
            payload = clip_path(payload, bounds)
        self._geometry_payload = payload
        self._place(frame)
        self._data_seen = system._data_version
        self._parameter_versions = {
            name: parameter.version for name, parameter in self.parameters.items()
        }
        self._dirty = False

    def _restore(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        if (
            self._dirty
            or self._data_seen != system._data_version
            or (self.parameters and self._parameters_changed())
            or (self._clip_has_margin and self._frame_seen != system.frame.version)
        ):
            self._rebuild()
        else:
            self._place(self._frame())

    def _place(self, frame: FrameMap) -> None:
        system = self._system
        assert system is not None
        payload = self._geometry_payload
        self._dense = not frame.is_affine
        count = len(payload.coords) // 4
        if self._dense and 0 < count < 64:
            payload = densify(payload, system.bounds, pieces=(64 + count - 1) // count)
        if self._own.nodes:
            local = payload.coords
            if local.shape[1] == 2:
                local = np.column_stack((local, np.zeros(len(local))))
            self._local = self._own.forward(local)
        else:
            self._local = payload.coords
        self._cache = frame.forward(self._local)
        self._render_segments = payload.segments
        if self._dash is not None:
            placed = Payload._trusted("path", self._cache, payload.segments)
            dashed = dash_path(
                placed, system.bounds, on=self._dash[0], off=self._dash[1]
            )
            self._cache = dashed.coords.copy()
            self._render_segments = dashed.segments
        if self._reversed:
            self._local = self._local[::-1].copy()
            self._cache = self._cache[::-1].copy()
            self._render_segments = len(self._cache) - self._render_segments[::-1, ::-1]
        self._frame_seen = system.frame.version

    def reverse_points(self) -> Self:
        """Reverse traversal, retaining the direction across attached rebuilds."""
        self._ensure()
        if self._lifecycle.state is lc.State.ATTACHED:
            self._reversed = not self._reversed
            self._local = self._local[::-1].copy()
            self._render_segments = len(self._cache) - self._render_segments[::-1, ::-1]
        elif self._lifecycle.state is lc.State.SHAPED and self._shape is not None:
            self._shape = self._shape[::-1].copy()
        return super().reverse_points()

    @property
    def points(self) -> FloatArray:
        """Return the current derived or animation-owned buffer itself."""
        if (
            self._ready
            and not self._alignment_locked
            and self._lifecycle.state not in (lc.State.TRANSIENT, lc.State.REMOVED)
            and not buffer_write()
        ):
            self._ensure()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        if not self._ready:
            self._cache = np.asarray(value, dtype=float)
            return
        context = writer_context()
        if context is None or self._lifecycle.state in {
            lc.State.TRANSIENT,
            lc.State.REMOVED,
        }:
            self._cache = np.asarray(value, dtype=float)
            return
        if self._write_start is None:
            self._write_start = self._cache.copy()
            if context.pivot is not None:
                # Manim subtracts the pivot in place before this first assignment.
                self._write_start += context.pivot
        self._cache = np.asarray(value, dtype=float)
        if not context.last:
            return
        start, self._write_start = self._write_start, None
        system = self._system
        if system is None:
            return
        writer = lc.Writer.FRAME if system.frame in context.family else lc.Writer.OTHER
        self._lifecycle, actions = lc.transition(self._lifecycle, lc.Write(writer))
        if actions[0].kind is lc.Kind.IGNORE:
            self._frame_seen = -1
            return
        self._cache = start
        self._capture(context)

    def _capture(self, context: WriterContext) -> None:
        if context.vector is not None:
            vector = context.vector
            self._geometry(lambda p: p + vector, np.eye(3), vector)
        elif context.application is not None:
            container, application = context.application
            factor = container.pre_function_handle_to_anchor_scale_factor
            smoothing = container.make_smooth_after_applying_functions

            def apply(points: FloatArray) -> FloatArray:
                native = VMobject().set_points(points.copy())
                native.pre_function_handle_to_anchor_scale_factor = factor
                native.make_smooth_after_applying_functions = smoothing
                return native.apply_function(application).points

            self._geometry(apply)
        else:
            function, pivot = context.function, context.pivot
            assert function is not None and pivot is not None
            matrix = context.matrix
            offset = None if matrix is None else pivot - pivot @ matrix
            self._geometry(lambda p: function(p - pivot) + pivot, matrix, offset)

    def _geometry(
        self,
        function: Callable[[FloatArray], FloatArray],
        matrix: FloatArray | None = None,
        offset: FloatArray | None = None,
    ) -> Self:
        if self._system is None or self._lifecycle.state in {
            lc.State.TRANSIENT,
            lc.State.REMOVED,
        }:
            self._cache = function(self._cache)
            return self
        self._ensure()
        frame = self._frame()
        if frame.is_singular:
            raise ValueError("system frame is singular; artist transform refused")
        if self._lifecycle.state is lc.State.SHAPED:
            transformed = function(self.points)
            local = frame.inverse(transformed)
            self._shape, self._cache = local, transformed
            return self
        if frame.is_affine and matrix is not None:
            basis_points = frame.forward(np.vstack((np.zeros(3), np.eye(3))))
            origin = basis_points[0]
            basis = basis_points[1:] - origin
            inverse = np.linalg.inv(basis)
            shift = np.zeros(3) if offset is None else offset
            linear = basis @ matrix @ inverse
            translation = (origin @ matrix + shift - origin) @ inverse
            node: Node = AffineNode.from_parts(linear.T, translation)
        else:
            node = FunctionNode(
                lambda p: frame.inverse(function(frame.forward(p))), dim=3
            )
        self._own = Chain((*self._own.nodes, node))
        local = self._local
        if local.shape[1] == 2:
            local = np.column_stack((local, np.zeros(len(local))))
        self._local = node.apply(local)
        self._cache = function(self._cache)
        if self._dash is not None:
            self._place(frame)
        return self

    def shift(self, *vectors: Vector3DLike) -> Self:
        """Record a native translation in the system's local space.

        Parameters
        ----------
        *vectors
            Native scene-space vectors, summed before application.
        """
        vector = np.sum(np.asarray(vectors, dtype=float), axis=0)
        return self._geometry(lambda p: p + vector, np.eye(3), vector)

    def apply_points_function_about_point(
        self,
        func: Callable[[FloatArray], FloatArray],
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Record the exact native matrix or a non-affine placement node.

        Parameters
        ----------
        func, about_point, about_edge
            Native points function and pivot conventions.
        """
        if about_point is None:
            about_point = self.get_critical_point(
                np.zeros(3) if about_edge is None else about_edge
            )
        pivot = np.array(about_point, dtype=float, copy=True)
        matrix = affine_context()
        offset = None if matrix is None else pivot - pivot @ matrix
        return self._geometry(lambda p: func(p - pivot) + pivot, matrix, offset)

    def apply_function(
        self,
        function: Callable[..., Any],
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Apply Manim's handle preparation as a permanent local operation.

        Parameters
        ----------
        function, about_point, about_edge
            Native mapping and pivot options.
        """
        factor = self.pre_function_handle_to_anchor_scale_factor
        smoothing = self.make_smooth_after_applying_functions

        def apply(points: FloatArray) -> FloatArray:
            native = VMobject().set_points(points.copy())
            native.pre_function_handle_to_anchor_scale_factor = factor
            native.make_smooth_after_applying_functions = smoothing
            return native.apply_function(
                function, about_point=about_point, about_edge=about_edge
            ).points

        return self._geometry(apply)

    def _adopt(self, other: Leaf) -> None:
        if isinstance(other, _CurvePlot):
            old, new = self._system, other._system
            registered = old is not None and self in old._artists
            if old is not new:
                if registered:
                    assert old is not None
                    old._artists.remove(self)
                self._system = new
                if registered and new is not None:
                    new._artists.append(self)
            other = other.copy()
            self.source = other.source
            self.parameters = other.parameters
            self._source_invalid = other._source_invalid
            self._reversed = other._reversed
            self.use_smoothing = other.use_smoothing
            self._clip = other._clip
            self._clip_has_margin = other._clip_has_margin
            self.line_style, self.dash, self._dash = (
                other.line_style,
                other.dash,
                other._dash,
            )
            self._geometry_payload = other._geometry_payload
            self._local = other._local
            self._render_segments = other._render_segments
            self._data_seen = other._data_seen
            self._frame_seen = other._frame_seen
            self._parameter_versions = {
                name: parameter.version for name, parameter in self.parameters.items()
            }
            self._parameter_token = -1
            self._frozen_frame = None
        super()._adopt(other)
        self._dirty = False
        self._parameter_animation = False

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Align native artist buffers and detect animated function parameters.

        Parameters
        ----------
        mobject, skip_point_alignment
            Native target and alignment option.
        """
        animation = animation_context(transform_only=True)
        self._parameter_animation = (
            isinstance(animation, _MethodAnimation)
            and isinstance(mobject, _CurvePlot)
            and self.parameters.keys() == mobject.parameters.keys()
            and any(
                not np.array_equal(p.value, mobject.parameters[name].value)
                for name, p in self.parameters.items()
            )
        )
        return super().align_data(mobject, skip_point_alignment)

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType = _STRAIGHT,
    ) -> Self:
        """Interpolate data parameters for native method animations.

        Parameters
        ----------
        mobject1, mobject2, alpha, path_func
            Native endpoints, progress and geometric interpolation path.
        """
        if self._parameter_animation:
            assert isinstance(mobject1, _CurvePlot)
            assert isinstance(mobject2, _CurvePlot)
            for name, parameter in self.parameters.items():
                parameter.value = (1 - alpha) * mobject1.parameters[
                    name
                ].value + alpha * mobject2.parameters[name].value
            self._rebuild()
            self.interpolate_color(mobject1, mobject2, alpha)
            return self
        return super().interpolate(mobject1, mobject2, alpha, path_func)


class _ParameterizedFunction:
    def __init__(
        self,
        function: Callable[..., Any],
        signature: inspect.Signature,
        parameters: dict[str, Parameter[Any]],
    ) -> None:
        self.function, self.signature, self.parameters = function, signature, parameters

    def __call__(self, x: float | FloatArray) -> ArrayLike:
        args = [x]
        kwargs = {}
        for item in list(self.signature.parameters.values())[1:]:
            if item.kind is inspect.Parameter.POSITIONAL_ONLY:
                args.append(self.parameters[item.name].value)
            elif item.name in self.parameters:
                parameter = self.parameters[item.name]
                if parameter.version or parameter.value is not item.default:
                    kwargs[item.name] = parameter.value
        return cast(ArrayLike, self.function(*args, **kwargs))


def _parameterize(
    function: Callable[..., Any], kwargs: dict[str, object]
) -> tuple[Callable[..., Any], dict[str, Parameter[Any]]]:
    if isinstance(function, _ParameterizedFunction):
        return function, function.parameters
    parameters: dict[str, Parameter[Any]] = {}
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return function, parameters
    for item in list(signature.parameters.values())[1:]:
        if item.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        if item.name in _ArtistOptions.__annotations__:
            raise ValueError(f"parameter {item.name!r} is a reserved artist keyword")
        value = kwargs.pop(item.name, item.default)
        if value is inspect.Parameter.empty:
            raise TypeError(f"missing function parameter {item.name!r}")
        bound = callable(value) or callable(getattr(value, "get_value", None))
        parameter: Parameter[Any] = Parameter(None if bound else value, name=item.name)
        if bound:
            parameter.bind(value)
            parameter.poll(0)
        parameters[item.name] = parameter
    if parameters:
        function = _ParameterizedFunction(function, signature, parameters)
    return function, parameters


class FunctionPlot(_CurvePlot):
    """Draw an analytic function with versioned parameters through a system.

    Parameters
    ----------
    function
        Scalar or vectorized function; arguments after the first are parameters.
    system
        Coordinate system supplying ranges, bounds and placement.
    x_range
        Optional sampling interval and maximum sample spacing.
    use_vectorized
        Evaluate arrays instead of individual scalars.
    use_smoothing
        Fit native cubic splines instead of straight cubic segments.
    discontinuities, dt
        Explicit gaps and their half-width, with Manim's meaning.
    **kwargs
        Function parameter values or bindings, native VMobject styles, and label,
        line_style, dash and clip. Clipping defaults to True; False disables it,
        and a number gives a margin in scene units. A tuple or list ``(cx, cy)``
        sets each axis independently. Uncoloured plots take the next colour in
        the system's cycle, starting with white.

    Notes
    -----
    Samples are refined adaptively, independently of the tick step. Invalid
    samples and poles split the path; the result is clipped to the viewport.
    Native Create paces partial drawing by sample count, not by x, so dense bends
    take longer to reveal. Use TraceCurve with a linear rate function for steady
    progress in data x.

    Uncreate detaches the curve: later data changes leave its removed buffer
    alone. Unlike plain Manim, a subsequent Create reattaches it and draws the
    current data. Calling refresh also reattaches it. A bare edit of points lasts
    only until the next rebuild; refresh replaces that edit with derived geometry.

    A curve's own geometric transform persists through resampling and moves with
    its axes. PhaseFlow-like callbacks append to that transform each frame, so a
    long animation can grow its transform chain. Prefer one affine operation when
    it describes the intended movement.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        system: mp.CartesianAxes,
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        *,
        use_smoothing: bool = True,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        **kwargs: object,
    ) -> None:
        function, self.parameters = _parameterize(function, kwargs)
        super().__init__(
            FunctionSource(
                function,
                x_range,
                use_vectorized=use_vectorized,
                discontinuities=discontinuities,
                dt=dt,
            ),
            system,
            use_smoothing=use_smoothing,
            **cast(_ArtistOptions, kwargs),
        )

    def set_parameters(self, **values: object) -> Self:
        """Set named function parameters, including through native ``animate``.

        Parameters
        ----------
        **values
            Values of arguments declared after the function's input coordinate.

        Raises
        ------
        ValueError
            If a name is not a declared function parameter.
        """
        for name in values:
            if name not in self.parameters:
                raise ValueError(f"unknown function parameter {name!r}")
        for name, value in values.items():
            self.parameters[name].value = value
        self._ensure()
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = super().__deepcopy__(memo)
        result.parameters = {
            name: copy.copy(parameter) for name, parameter in self.parameters.items()
        }
        source = self.source
        if isinstance(source, FunctionSource) and isinstance(
            source.function, _ParameterizedFunction
        ):
            result.source = FunctionSource(
                _ParameterizedFunction(
                    source.function.function,
                    source.function.signature,
                    result.parameters,
                ),
                source._range,
                use_vectorized=source.use_vectorized,
                discontinuities=source.discontinuities,
                dt=source.dt,
            )
        return result


class LinePlot(_CurvePlot):
    """Draw immutable array data, clipping straight segments to the viewport.

    Parameters
    ----------
    xs, ys
        Separate coordinate sequences, or pairs in xs with ys omitted.
    system
        Coordinate system supplying bounds and placement.
    **kwargs
        Native VMobject styles and artist options. ``clip`` accepts True, False,
        a finite scene-unit margin, or a tuple or list ``(cx, cy)`` of these
        policies for x and y independently.
    """

    def __init__(
        self,
        xs: ArrayLike,
        system: mp.CartesianAxes,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> None:
        super().__init__(ArraySource(xs, ys), system, use_smoothing=False, **kwargs)


class ParametricPlot(_CurvePlot):
    """Draw a parameterized curve through a Cartesian system.

    Parameters
    ----------
    function
        Callable returning two or three coordinates per input.
    system
        Coordinate system supplying bounds and placement.
    use_vectorized
        Return a sequence of coordinate arrays when true.
    t_range
        Parameter endpoints and optional maximum spacing.
    use_smoothing
        Fit native cubic splines when true.
    discontinuities, dt
        Explicit gaps and their half-width.
    **kwargs
        Native VMobject styles and artist options. ``clip`` accepts True, False,
        a finite scene-unit margin, or a tuple or list ``(cx, cy)`` of these
        policies for x and y independently.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        system: mp.CartesianAxes,
        use_vectorized: bool = False,
        *,
        t_range: Sequence[float] = (0.0, 1.0),
        use_smoothing: bool = True,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        **kwargs: Unpack[_ArtistOptions],
    ) -> None:
        super().__init__(
            ParametricSource(
                function,
                t_range,
                use_vectorized=use_vectorized,
                discontinuities=discontinuities,
                dt=dt,
            ),
            system,
            use_smoothing=use_smoothing,
            **kwargs,
        )


class _MarkerLeaf(_CurvePlot):
    def __init__(
        self,
        native: Mobject,
        source: ArraySource,
        index: int,
        system: mp.CartesianAxes,
        clip: _ClipInput = True,
        sample_warnings: _SampleWarnings | None = None,
    ) -> None:
        self._sample_warnings = sample_warnings or _SampleWarnings()
        self._outline = native.points.copy()
        self._index = index
        self._visible = True
        self._opacities = (1.0, 1.0, 1.0)
        super().__init__(
            source, system, use_smoothing=False, clip=clip, color=native.get_color()
        )
        if isinstance(native, VMobject):
            self.match_style(native, family=False)
        else:
            self.set_color(native.get_color())
        self._visible = True
        self._dirty = True
        self._ensure()

    def _rebuild(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        assert isinstance(self.source, ArraySource)
        data = self.source.data[self._index : self._index + 1]
        payload = system._data.apply_payload(
            Payload.points(data, np.isfinite(data).all(axis=1))
        )
        if payload.valid is not None and not payload.valid.all():
            self._sample_warnings.warn(
                system,
                self.source,
                "source contains invalid samples; points are hidden",
            )
        axes = _clip_axes(self._clip)
        visible = payload.valid is None or bool(payload.valid[0])
        if visible and any(axis is not False for axis in axes):
            bounds = _clip_box(system, self._clip)
            if any(axis is False for axis in axes):
                bounds = _unclipped_box(bounds, axes, payload.coords)
            visible = bool(bounds.contains(payload.coords)[0])
        if visible != self._visible:
            if visible:
                fill, stroke, background = self._opacities
            else:
                self._opacities = (
                    self.get_fill_opacity(),
                    self.get_stroke_opacity(),
                    self.get_stroke_opacity(background=True),
                )
                fill = stroke = background = 0.0
            self.set_fill(opacity=fill, family=False)
            self.set_stroke(opacity=stroke, family=False)
            self.set_stroke(opacity=background, background=True, family=False)
            self._visible = visible
        center = np.zeros(3)
        if np.isfinite(payload.coords).all():
            center[:2] = payload.coords[0]
        points = self._outline + center
        # Marker outlines already are native control points, including local depth.
        self._geometry_payload = Payload._trusted(
            "path", points, np.array([[0, len(points)]], dtype=np.intp)
        )
        self._place(self._frame())
        self._data_seen = system._data_version
        self._dirty = False

    def _place(self, frame: FrameMap) -> None:
        if len(self._outline) % 4:
            # Point-based native mobjects need no cubic subdivision.
            self._dense = not frame.is_affine
            self._local = self._own.forward(self._geometry_payload.coords)
            if self._reversed:
                self._local = self._local[::-1].copy()
            self._cache = frame.forward(self._local)
            assert self._system is not None
            self._frame_seen = self._system.frame.version
        else:
            super()._place(frame)


class ScatterPlot(VGroup):
    """Draw one independent marker per input row, retaining hidden rows in order.

    Parameters
    ----------
    xs, ys
        Separate coordinates, or pairs in xs with ys omitted.
    system
        Coordinate system supplying bounds and placement.
    marker
        Marker enum or native template, defaulting to Dot().
    label
        Legend entry text, or None when unset.
    clip
        True clips marker centres at the viewport, False disables clipping,
        and a finite scene-unit margin expands or narrows it. A tuple or list
        ``(cx, cy)`` applies these policies independently to x and y.
    **kwargs
        Native VMobject styles applied to the marker template.
    """

    def __init__(
        self,
        xs: ArrayLike,
        system: mp.CartesianAxes,
        ys: ArrayLike | None = None,
        *,
        marker: Mobject | Marker | None = None,
        label: str | None = None,
        clip: _ClipInput = True,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        _validate_label(label)
        clip_value = _validate_clip(clip)
        _clip_box(system, clip_value)
        self._label, self._clip = label, clip_value
        self.source = ArraySource(xs, ys, kind="points")
        if marker is not None and not isinstance(marker, (Mobject, Marker)):
            raise TypeError("marker must be a Marker, Mobject or None")
        if marker is None or isinstance(marker, Marker):
            index = _cycle_style(system, kwargs, scatter=True)
            if marker is None and system.theme.markers:
                marker = system.theme.markers[index % len(system.theme.markers)]
            shape = Marker.DOT if marker is None else marker
            template: Mobject = {
                Marker.DOT: Dot,
                Marker.CIRCLE: Circle,
                Marker.SQUARE: Square,
                Marker.TRIANGLE: Triangle,
                Marker.CROSS: Cross,
                Marker.STAR: Star,
            }[shape]()
            template.width = 2 * DEFAULT_DOT_RADIUS
            if shape in {Marker.SQUARE, Marker.TRIANGLE, Marker.STAR}:
                cast(VMobject, template).set_fill(opacity=1)
        else:
            template = marker.copy()
        if kwargs:
            for member in template.get_family():
                if isinstance(member, VMobject):
                    if "color" in kwargs:
                        member.set_color(kwargs["color"], family=False)
                    style = member.get_style()
                    for name, value in kwargs.items():
                        if name in style:
                            style[name] = value
                        elif name != "color":
                            setattr(member, name, value)
                    member.set_style(**style, family=False)
        template.shift(-template.get_center())
        self._marker_template = template.copy()
        self._system: mp.CartesianAxes | None = system
        self._sample_warnings = _SampleWarnings()
        self._validity_seen = -1
        self._ready = False
        self._cache = np.empty((0, 3))
        super().__init__()
        self._ready = True
        self._poll()
        if isinstance(template, VMobject):
            self.match_style(template, family=False)

        def convert(native: Mobject, index: int) -> VMobject:
            children = [convert(child, index) for child in native.submobjects]
            if len(native.points):
                leaf = _MarkerLeaf(
                    native,
                    self.source,
                    index,
                    system,
                    clip_value,
                    self._sample_warnings,
                )
                leaf.submobjects = children
                return leaf
            group = VGroup(*children)
            if isinstance(native, VMobject):
                group.match_style(native, family=False)
            return group

        self.submobjects = [convert(template, i) for i in range(len(self.source.data))]
        self.add_updater(_synchronise)

    @property
    def points(self) -> FloatArray:
        """Return the group buffer, checking invalid or empty data once per change."""
        if self._ready:
            self._poll()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)

    def _poll(self) -> None:
        system = self._system
        if system is None:
            return
        system._sync_data()
        if self._validity_seen == system._data_version:
            return
        self._validity_seen = system._data_version
        data = self.source.data
        if not len(data) or not system._data.valid(data).all():
            self._sample_warnings.warn(
                system,
                self.source,
                "source is empty or contains invalid samples; points are hidden",
            )

    def set_label(self, label: str | None) -> Self:
        """Set the legend label.

        Parameters
        ----------
        label
            Entry text, or None to omit this scatter.
        """
        _validate_label(label)
        self._label = label
        return self

    def get_label(self) -> str | None:
        """Return the legend label, or None when unset."""
        return self._label

    def set_clip(self, value: _ClipInput) -> Self:
        """Set the marker-centre clipping policy.

        Parameters
        ----------
        value
            True clips at the viewport, False disables clipping, and a finite
            margin in scene units expands or narrows it. A tuple or list
            ``(cx, cy)`` applies these policies independently to x and y.

        Returns
        -------
        Self
            This scatter after rebuilding its markers.
        """
        clip = _validate_clip(value)
        if self._system is not None:
            _clip_box(self._system, clip)
        self._clip = clip
        for leaf in self.get_family():
            if isinstance(leaf, _MarkerLeaf):
                leaf.set_clip(clip)
        return self

    def get_clip(self) -> _ClipValue:
        """Return the marker-centre clipping policy.

        Returns
        -------
        bool or float or tuple
            The supplied policy; per-axis entries are returned as ``(cx, cy)``,
            including when set from a list.
        """
        return self._clip

    def become(
        self,
        mobject: Mobject,
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """Adopt native target geometry and another scatter's clipping policy.

        Parameters
        ----------
        mobject, match_height, match_width, match_depth, match_center, stretch
            Native target and size/placement preparation options.
        """
        super().become(
            mobject, match_height, match_width, match_depth, match_center, stretch
        )
        if isinstance(mobject, ScatterPlot):
            self._clip = mobject._clip
            for leaf in self.get_family():
                if isinstance(leaf, _MarkerLeaf):
                    leaf._clip = self._clip
                    leaf._clip_has_margin = _clip_has_margin(self._clip)
        return self

    def shift(self, *vectors: Vector3DLike) -> Self:
        """Translate markers, recording the operation in their local transforms.

        Parameters
        ----------
        *vectors
            Native scene-space vectors, summed before application.
        """
        return super().shift(np.sum(np.asarray(vectors, dtype=float), axis=0))

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Report synchronisation when this scatter's system can move."""
        from manim_plots.mobjects.leaves import _reported_updaters

        return _reported_updaters(self._actual_updaters, self._system)

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._actual_updaters = value

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key == "_system":
                result.__dict__[key] = memo.get(id(value), value)
            elif key == "source":
                result.__dict__[key] = value
            else:
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result
