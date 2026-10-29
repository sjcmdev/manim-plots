"""Artists derived from the numeric Source, Map and Shape pipeline."""

from __future__ import annotations

import copy
import inspect
import warnings
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Self, Unpack, cast

import numpy as np
from manim import Dot, Mobject, VGroup, VMobject
from manim.typing import Point3DLike, Vector3DLike
from numpy.typing import ArrayLike

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
from manim_plots.core.shape import clip, corners, densify, smooth
from manim_plots.core.sources import (
    ArraySource,
    FunctionSource,
    ParametricSource,
    Source,
)
from manim_plots.mobjects.context import (
    WriterContext,
    affine_context,
    buffer_write,
    playback_context,
    writer_context,
)
from manim_plots.mobjects.leaves import Leaf, _synchronise, _VMStyle

if TYPE_CHECKING:
    from manim_plots.mobjects.system import CartesianAxes


class _CurvePlot(Leaf):
    def __init__(
        self,
        source: Source,
        system: CartesianAxes,
        *,
        use_smoothing: bool = True,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        self.source = source
        if not hasattr(self, "parameters"):
            self.parameters: dict[str, Parameter[Any]] = {}
        self._parameter_versions: dict[str, int] = {}
        self._parameter_token = -1
        self.use_smoothing = use_smoothing
        self._data_seen = -1
        self._local = np.empty((0, 3))
        self._geometry_payload = Payload.empty("path", 2)
        self._dense = False
        self._warned_change: object | None = None
        self._source_invalid = (
            isinstance(source, ArraySource) and not np.isfinite(source.data).all()
        )
        super().__init__(system=system, **kwargs)
        self.add_updater(_synchronise)
        self._rebuild()

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
            if self._dense == frame.is_affine:
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
        mapping = SystemMap(system._data, frame)
        payload = self.source.sample(mapping, system.bounds)
        if isinstance(self.source, ArraySource):
            invalid = self._source_invalid or not len(self.source.data)
        else:
            invalid = (
                not len(payload.coords)
                or (payload.valid is not None and not payload.valid.all())
                or len(payload.segments)
                > len(getattr(self.source, "discontinuities", ())) + 1
            )
        if invalid:
            token = playback_context()
            change = (
                (
                    None,
                    system._data_version,
                    tuple(p.version for p in self.parameters.values()),
                )
                if token is None
                else (token[0], token[2])
            )
            if self._warned_change != change:
                self._warned_change = change
                warnings.warn(
                    "source is empty or contains invalid samples or a pole; "
                    "the path is split",
                    ManimPlotsWarning,
                    stacklevel=3,
                )
        payload = system._data.apply_payload(payload)
        if self.use_smoothing and len(payload.segments) > 1:
            # Keep visible samples and their brackets; remote pole tails ring globally.
            inside = system.bounds.contains(payload.coords)
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
        payload = (smooth if self.use_smoothing else corners)(payload, system.bounds)
        self._geometry_payload = clip(payload, system.bounds)
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
        self._frame_seen = system.frame.version

    @property
    def points(self) -> FloatArray:
        """Return the current derived or animation-owned buffer itself."""
        if self._ready and not buffer_write():
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
            self.source = other.source
            self.use_smoothing = other.use_smoothing
        super()._adopt(other)
        self._rebuild()


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
        if item.name in _VMStyle.__annotations__:
            raise ValueError(f"parameter {item.name!r} is a VMobject style keyword")
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
        Function parameter values or bindings, and native VMobject styles.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        system: CartesianAxes,
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
            **cast(_VMStyle, kwargs),
        )

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
        Native VMobject styles.
    """

    def __init__(
        self,
        xs: ArrayLike,
        system: CartesianAxes,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_VMStyle],
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
        Native VMobject styles.
    """

    def __init__(
        self,
        function: Callable[..., Any],
        system: CartesianAxes,
        use_vectorized: bool = False,
        *,
        t_range: Sequence[float] = (0.0, 1.0),
        use_smoothing: bool = True,
        discontinuities: Iterable[float] | None = None,
        dt: float = 1e-8,
        **kwargs: Unpack[_VMStyle],
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
        self, native: Mobject, source: ArraySource, index: int, system: CartesianAxes
    ) -> None:
        self._outline = native.points.copy()
        self._index = index
        self._visible = True
        self._opacities = (1.0, 1.0, 1.0)
        super().__init__(source, system, use_smoothing=False)
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
        visible = bool(
            (payload.valid is None or payload.valid[0])
            and system.bounds.contains(payload.coords)[0]
        )
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
        Native marker template, defaulting to Dot().
    **kwargs
        Native VMobject styles applied to the marker template.
    """

    def __init__(
        self,
        xs: ArrayLike,
        system: CartesianAxes,
        ys: ArrayLike | None = None,
        *,
        marker: Mobject | None = None,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        self.source = ArraySource(xs, ys, kind="points")
        if marker is not None and not isinstance(marker, Mobject):
            raise TypeError("marker must be a Mobject or None")
        template = Dot(**kwargs) if marker is None else marker.copy()
        if marker is not None and kwargs:
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
        self._system: CartesianAxes | None = system
        super().__init__()

        def convert(native: Mobject, index: int) -> VMobject:
            children = [convert(child, index) for child in native.submobjects]
            if len(native.points):
                leaf = _MarkerLeaf(native, self.source, index, system)
                leaf.submobjects = children
                return leaf
            return VGroup(*children)

        self.submobjects = [convert(template, i) for i in range(len(self.source.data))]
        self.add_updater(_synchronise)

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
