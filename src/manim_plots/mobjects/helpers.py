"""Bound line and calculus helpers, sharing the ordinary artist lifecycle."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Sequence
from numbers import Real
from typing import Any, TypedDict, Unpack, cast

import numpy as np
from manim import (
    DEFAULT_DASH_LENGTH,
    DOWN,
    RIGHT,
    UP,
    ArrowTriangleFilledTip,
    DashedLine,
    Line,
    Mobject,
    RegularPolygon,
    VGroup,
    VMobject,
)
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import FrameMap
from manim_plots.core.params import Parameter, _same
from manim_plots.core.payload import Payload
from manim_plots.core.shape import _assemble, arc_length, corners
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.shape import dash as dash_path
from manim_plots.core.sources import ArraySource, _CalculusSource
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LineStyle,
    _clip_axes,
    _clip_box,
    _CurvePlot,
    _dash_pattern,
    _unclipped_box,
)
from manim_plots.mobjects.leaves import (
    Leaf,
    _ArtistOptions,
    _label,
    _VMStyle,
)


class _DropOptions(TypedDict, total=False):
    line_func: type[Line]
    line_config: dict[str, Any] | None
    color: ParsableManimColor | None
    stroke_width: float


class _HelperOptions(_ArtistOptions, total=False):
    buff: float


class _TangentOptions(_HelperOptions, total=False):
    tip_length: float
    tip_width: float


class _SlopeOptions(TypedDict, total=False):
    dx: object


def _number(value: object, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number or a binding")
    if not np.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _parameter(value: object, name: str) -> Parameter[Any]:
    reader = getattr(value, "get_value", None)
    if callable(reader) or callable(value):
        parameter: Parameter[Any] = Parameter(None, name=name)
        parameter.bind(value)
        parameter.poll(0)
        return parameter
    return Parameter(value, name=name)


def _graph(system: mp.CartesianAxes, graph: _CurvePlot) -> None:
    if not isinstance(graph, _CurvePlot) or graph._system is not system:
        raise ValueError("graph must be bound to this system")


def _limits(system: mp.CartesianAxes, graph: _CurvePlot) -> tuple[float, float]:
    limits = getattr(graph.source, "_range", None)
    if isinstance(graph.source, ArraySource) and len(graph.source.data):
        xs = graph.source.data[:, 0]
        return float(np.nanmin(xs)), float(np.nanmax(xs))
    return cast(
        tuple[float, float], system.x.range.value if limits is None else limits[:2]
    )


def _valid_x(system: mp.CartesianAxes, graph: _CurvePlot | None, x: float) -> bool:
    lo, hi = sorted(system.x.range.value)
    if not lo <= x <= hi:
        return False
    if graph is not None:
        lo, hi = sorted(_limits(system, graph))
        if not lo <= x <= hi:
            return False
        with np.errstate(all="ignore"):
            try:
                coords = graph.source.at(x)
            except (ValueError, ZeroDivisionError, OverflowError):
                return False
        return bool(np.isfinite(coords).all() and system._data.valid(coords).all())
    return bool(np.isfinite(system.x._scale.forward([x])).all())


def _graph_local(system: mp.CartesianAxes, graph: _CurvePlot, x: float) -> FloatArray:
    local = system._data.forward(graph.source.at(x))
    if graph._own.nodes:
        local = graph._own.forward(np.column_stack((local, np.zeros(len(local)))))
    return cast(FloatArray, local[0])


def _graph_point(system: mp.CartesianAxes, graph: _CurvePlot, x: float) -> FloatArray:
    return cast(
        FloatArray,
        system.frame.mapping.forward(_graph_local(system, graph, x)[None, :])[0],
    )


def _tangent(system: mp.CartesianAxes, graph: _CurvePlot, x: float) -> FloatArray:
    h = np.cbrt(np.finfo(float).eps) * max(1, abs(x))
    lo, hi = sorted(_limits(system, graph))
    a, b = max(lo, x - h), min(hi, x + h)
    if a == b:
        a, b = x - h, x + h
    chord = _graph_point(system, graph, b) - _graph_point(system, graph, a)
    norm = np.linalg.norm(chord)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("x has no finite tangent")
    return chord / norm


class _Binding:
    def __init__(
        self,
        system: mp.CartesianAxes,
        derive: Callable[[_Binding], None],
        inputs: dict[str, object],
        graph: _CurvePlot | None = None,
    ) -> None:
        if graph is not None:
            _graph(system, graph)
        self.system, self.graph, self.derive = system, graph, derive
        self.parameters = {
            name: _parameter(value, name) for name, value in inputs.items()
        }
        self.parts: dict[str, FloatArray] = {}
        self.texts: dict[str, VGroup] = {}
        self.version = 0
        self.valid = True
        self._seen: object = None
        self._values: dict[str, object] = {}
        self._graph_values: dict[str, object] = {}
        self._poll_token = -1
        self._deriving = False

    def number(self, name: str) -> float:
        return _number(self.parameters[name].value, name)

    def check_x(self, name: str, x: float | None = None) -> bool:
        value = self.number(name) if x is None else x
        valid = _valid_x(self.system, self.graph, value)
        if not valid and self.version == 0:
            raise ValueError(f"{name} must be inside the graph domain and axis range")
        self.valid &= valid
        return valid

    def local(self, points: ArrayLike) -> FloatArray:
        return self.system._data.forward(np.asarray(points, dtype=float))

    def scene(self, points: ArrayLike) -> FloatArray:
        return self.system.frame.mapping.inverse(np.asarray(points, dtype=float))

    def scene_line(self, start: FloatArray, end: FloatArray) -> FloatArray:
        points = np.array([start, end])
        if not self.system.frame.mapping.is_affine:
            points = np.linspace(start, end, 65)
        return self.scene(points)

    def poll(self) -> None:
        token = self.system._token
        if self._poll_token != token:
            self._poll_token = token
            for parameter in self.parameters.values():
                parameter.poll(token)

    def needs_sync(self, moving: frozenset[Mobject]) -> bool:
        if self.graph is not None and (
            self.graph in moving or self.graph._needs_sync(moving)
        ):
            return True
        return any(
            p.tracker is not None and (callable(p.tracker) or p.tracker in moving)
            for p in self.parameters.values()
        )

    def ensure(self) -> None:
        if self._deriving:
            return
        system = self.system
        system._sync_data()
        graph = self.graph
        if isinstance(graph, _DerivedPlot):
            graph._binding.ensure()
        state = (
            system._data_version,
            system.frame.version,
            system.x_axis._position,
            system.x_axis._position_fraction,
            system.y_axis._position,
            system.y_axis._position_fraction,
            None if graph is None else id(graph.source),
            None if graph is None else id(graph._own),
            graph._binding.version if isinstance(graph, _DerivedPlot) else None,
        )
        if (
            self._seen == state
            and all(
                name in self._values and _same(value.value, self._values[name])
                for name, value in self.parameters.items()
            )
            and (
                graph is None
                or all(
                    name in self._graph_values
                    and _same(value.value, self._graph_values[name])
                    for name, value in graph.parameters.items()
                )
            )
        ):
            return
        self._deriving = True
        try:
            self.valid = True
            self.derive(self)
            self._seen = state
            self._values = {name: p.value for name, p in self.parameters.items()}
            self._graph_values = (
                {}
                if graph is None
                else {name: p.value for name, p in graph.parameters.items()}
            )
            self.version += 1
        finally:
            self._deriving = False

    def __deepcopy__(self, memo: dict[int, Any]) -> _Binding:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key in {"system", "graph"}:
                result.__dict__[key] = memo.get(id(value), value)
            elif key == "parameters":
                result.parameters = {name: copy.copy(p) for name, p in value.items()}
            else:
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result


class HelperLine(_CurvePlot):
    """Draw one registered, independently styled part of a bound helper.

    Parameters
    ----------
    binding, part
        Shared derivation and the name of this line's local endpoints.
    buff
        Scene distance trimmed from each end, as in Manim's Line.
    **style
        Ordinary artist style, dashing and per-axis clipping options.

    Notes
    -----
    Unlike Manim's Line and DashedLine this is a plotting leaf, bound to its
    system and inputs; it is not an instance of either native line class.
    Re-derivation replaces geometry and preserves the part's style.
    Lines clip at the viewport by default, where Manim's continue beyond it.
    They follow permanent system changes; temporary animations freeze their
    frame, as for plots. Create after Uncreate reattaches the current helper.
    """

    def __init__(
        self,
        binding: _Binding,
        part: str,
        *,
        buff: float = 0,
        **style: Unpack[_ArtistOptions],
    ) -> None:
        self._binding, self._part, self._buff = binding, part, _number(buff, "buff")
        self._binding_seen = -1
        style.setdefault("color", VMobject().get_color())
        super().__init__(
            ArraySource(np.empty((0, 2))), binding.system, use_smoothing=False, **style
        )
        self._dash_seen = (self.line_style, self.dash)
        binding.system.add(self)

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _adopt(self, other: Leaf) -> None:
        if isinstance(other, HelperLine):
            self._binding, self._part, self._buff = (
                other._binding,
                other._part,
                other._buff,
            )
            self._binding_seen = -1
        super()._adopt(other)
        self._dash_seen = (self.line_style, self.dash)

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            self._binding.ensure()
            if self._binding_seen != self._binding.version:
                self._dirty = True
            if (self.line_style, self.dash) != self._dash_seen:
                self._dash = _dash_pattern(self.line_style, self.dash)
                self._dash_seen = (self.line_style, self.dash)
                self._dirty = True
        super()._ensure()

    def _rebuild(self) -> None:
        binding = self._binding
        binding.ensure()
        system = self._system
        if system is None:
            return
        points = binding.parts.get(self._part, np.empty((0, 2)))
        if not binding.valid:
            points = np.empty((0, 2))
        frame = self._frame()
        if len(points) and self._buff > 0:
            placed = frame.forward(points)
            chord = placed[-1] - placed[0]
            length = np.linalg.norm(chord)
            if length >= 2 * self._buff:
                placed[0] += self._buff * chord / length
                placed[-1] -= self._buff * chord / length
                points = frame.inverse(placed)
        bounds = _clip_box(system, self._clip)
        payload = corners(Payload.path(points), bounds)
        axes = _clip_axes(self._clip)
        if any(axis is not False for axis in axes):
            if any(axis is False for axis in axes):
                bounds = _unclipped_box(bounds, axes, payload.coords)
            payload = clip_path(payload, bounds)
        self._geometry_payload = payload
        self._place(frame)
        self._binding_seen = binding.version
        self._data_seen = system._data_version
        self._dirty = False

    def _place(self, frame: FrameMap) -> None:
        pattern, self._dash = self._dash, None
        try:
            super()._place(frame)
        finally:
            self._dash = pattern
        if pattern is None or not len(self._cache):
            return
        assert self._system is not None
        ratio = pattern[0] / sum(pattern)
        pieces: list[FloatArray] = []
        for start, stop in self._render_segments:
            payload = Payload.path(self._cache[start:stop])
            length = float(arc_length(payload)[0])
            if length == 0:
                pieces.append(payload.coords)
                continue
            count = max(2, int(np.ceil(length / sum(pattern) * ratio)))
            dashed = dash_path(
                payload,
                self._system.bounds,
                on=length * ratio / count,
                off=length * (1 - ratio) / (count - 1),
            )
            pieces.extend(dashed.coords[a:b] for a, b in dashed.segments)
        result = _assemble(pieces, 3)
        self._cache = result.coords.copy()
        self._render_segments = result.segments


class HelperGroup(VGroup):
    """Group bound helper parts with independently persistent styles.

    Parameters
    ----------
    *parts
        Parts in Manim's order, also exposed by their documented names.

    Notes
    -----
    Unlike Manim's helper groups, each part follows its graph and system without
    always_redraw; line-like parts are registered HelperLine artists.
    """

    horizontal_line: HelperLine
    vertical_line: HelperLine
    line: HelperLine
    triangle: VMobject
    tip: VMobject
    label: VGroup
    dx_line: HelperLine
    df_line: HelperLine
    dx_label: VGroup
    df_label: VGroup
    secant_line: HelperLine


class _HelperShape(HelperLine):
    def __init__(self, binding: _Binding, part: str, template: VMobject) -> None:
        super().__init__(binding, part, clip=False)
        self.match_style(template, family=False)

    def _ensure(self) -> None:
        owner = self.__dict__.get("_label_owner")
        if owner is not None:
            owner._ensure()
        super()._ensure()

    def _rebuild(self) -> None:
        binding = self._binding
        binding.ensure()
        local = binding.parts.get(self._part, np.empty((0, 3)))
        if not binding.valid:
            local = np.empty((0, 3))
        segments = (
            np.array([[0, len(local)]], dtype=np.intp)
            if len(local)
            else np.empty((0, 2), dtype=np.intp)
        )
        self._geometry_payload = Payload._trusted("path", local, segments)
        axes = _clip_axes(self._clip)
        if len(local) and any(axis is not False for axis in axes):
            bounds = _clip_box(binding.system, self._clip)
            if any(axis is False for axis in axes):
                bounds = _unclipped_box(bounds, axes, local)
            self._geometry_payload = clip_path(self._geometry_payload, bounds)
        self._place(self._frame())
        self._binding_seen = binding.version
        self._data_seen = binding.system._data_version
        self._dirty = False


class _HelperText(VGroup):
    def __init__(self, binding: _Binding, part: str) -> None:
        self._binding, self._part = binding, part
        self._binding_seen = -1
        self._placing = False
        self._text_ready = False
        self._cache = np.empty((0, 3))
        super().__init__()
        self._text_ready = True
        self._ensure()

    @property
    def points(self) -> FloatArray:
        """Keep changing glyph counts current before Manim walks the family."""
        if self._text_ready:
            self._ensure()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)

    def _ensure(self) -> None:
        if self._placing:
            return
        self._placing = True
        try:
            binding = self._binding
            binding.ensure()
            if self._binding_seen == binding.version:
                return
            native = binding.texts[self._part]
            for index, glyph in enumerate(native.submobjects):
                binding.parts[f"{self._part}/{index}"] = glyph.points
            if len(self.submobjects) != len(native.submobjects):
                style = self.get_style() if self.submobjects else None
                self.submobjects = [
                    _HelperShape(binding, f"{self._part}/{index}", glyph)
                    for index, glyph in enumerate(native.submobjects)
                ]
                if style is not None:
                    self.set_style(**style)
                else:
                    self.match_style(native, family=False)
            for leaf in self.submobjects:
                assert isinstance(leaf, _HelperShape)
                leaf.__dict__["_label_owner"] = self
            self._binding_seen = binding.version
        finally:
            self._placing = False


class _Text:
    def __init__(self, label: object, color: ParsableManimColor | None = None) -> None:
        self.label, self.color = label, color
        self._value: object = None
        self._template: VGroup | None = None

    def at(self, value: float) -> VGroup:
        if self._template is None or (callable(self.label) and self._value != value):
            rendered = self.label(value) if callable(self.label) else self.label
            self._template = _label(rendered)
            if self.color is not None:
                self._template.set_color(self.color)
            self._value = value
        return self._template.copy()


def _line_options(
    line_func: type[Line] = DashedLine,
    line_config: dict[str, Any] | None = None,
    color: ParsableManimColor | None = None,
    stroke_width: float = 2,
) -> _HelperOptions:
    if line_func not in (Line, DashedLine):
        raise TypeError("line_func must be Line or DashedLine")
    options = dict(line_config or {})
    for key in options:
        if key not in {
            *_VMStyle.__annotations__,
            "buff",
            "dash_length",
            "dashed_ratio",
        }:
            raise TypeError(f"unknown line_config key {key!r}")
    dash_length = _number(
        options.pop("dash_length", DEFAULT_DASH_LENGTH), "dash_length"
    )
    ratio = _number(options.pop("dashed_ratio", 0.5), "dashed_ratio")
    if dash_length <= 0 or not 0 < ratio <= 1:
        raise ValueError("dash_length must be positive and dashed_ratio in (0, 1]")
    options["color"] = VMobject().get_color() if color is None else color
    options["stroke_width"] = stroke_width
    options["line_style"] = (
        LineStyle.DASHED if line_func is DashedLine else LineStyle.SOLID
    )
    if line_func is DashedLine:
        options["dash"] = (dash_length * ratio, dash_length * (1 - ratio))
    return cast(_HelperOptions, options)


def _drop(
    system: mp.CartesianAxes, index: int, point: object, **options: Unpack[_DropOptions]
) -> HelperLine:
    if not isinstance(index, int) or isinstance(index, bool):
        raise TypeError("index must be 0 or 1")
    if index not in (0, 1):
        raise ValueError("index must be 0 or 1")
    if isinstance(point, Mobject):
        point = point.get_center
    dynamic = callable(point)
    data = point if dynamic else system.p2c(cast(ArrayLike, point))

    def derive(binding: _Binding) -> None:
        raw = binding.parameters["point"].value
        coords = system.p2c(raw) if dynamic else np.asarray(raw, dtype=float)
        start = coords.copy()
        start[1 - index] = system.get_axis(index)._cross_value()
        binding.parts["line"] = binding.local([start, coords])

    binding = _Binding(system, derive, {"point": data})
    return HelperLine(binding, "line", **_line_options(**options))


def _verticals(
    system: mp.CartesianAxes,
    graph: _CurvePlot,
    x_range: Sequence[object] | None,
    num_lines: int,
    **options: Unpack[_DropOptions],
) -> HelperGroup:
    _graph(system, graph)
    if not isinstance(num_lines, int) or isinstance(num_lines, bool):
        raise TypeError("num_lines must be an integer")
    if num_lines < 1:
        raise ValueError("num_lines must be at least 1")
    if x_range is not None and len(x_range) not in (2, 3):
        raise ValueError("x_range must have length 2 or 3")
    inputs = (
        {} if x_range is None else {"x_range[0]": x_range[0], "x_range[1]": x_range[1]}
    )

    def derive(binding: _Binding) -> None:
        limits = (
            system.x.range.value
            if x_range is None
            else (binding.number("x_range[0]"), binding.number("x_range[1]"))
        )
        for i, x in enumerate(np.linspace(limits[0], limits[1], num_lines)):
            if _valid_x(system, graph, float(x)):
                local = _graph_local(system, graph, float(x))
                bottom = binding.local([[x, system.x_axis._cross_value()]])[0]
                if len(local) != len(bottom):
                    bottom = np.append(bottom, 0)
                binding.parts[str(i)] = np.array([bottom, local])
            else:
                if binding.version == 0:
                    raise ValueError(
                        "x_range must be inside the graph domain and axis range"
                    )
                binding.parts[str(i)] = np.empty((0, 2))

    binding = _Binding(system, derive, inputs, graph)
    style = _line_options(**options)
    return HelperGroup(
        *(HelperLine(binding, str(i), **style) for i in range(num_lines))
    )


def _reference(
    system: mp.CartesianAxes,
    index: int,
    value: object,
    minimum: object,
    maximum: object,
    **style: Unpack[_HelperOptions],
) -> HelperLine:
    name = "x" if index == 0 else "y"

    def derive(binding: _Binding) -> None:
        v = binding.number(name)
        lo, hi = sorted(system.get_axis(index).range.value)
        if not lo <= v <= hi:
            if binding.version == 0:
                raise ValueError(f"{name} must be inside the axis range")
            binding.valid = False
            return
        other = system.get_axis(1 - index)
        ends = other._scale.forward(other.range.value)
        fractions = np.array([binding.number("minimum"), binding.number("maximum")])
        extents = other._scale.inverse(ends[0] + fractions * (ends[1] - ends[0]))
        coords = np.full((2, 2), v)
        coords[:, 1 - index] = extents
        binding.parts["line"] = binding.local(coords)

    binding = _Binding(
        system, derive, {name: value, "minimum": minimum, "maximum": maximum}
    )
    style.setdefault("stroke_width", 2)
    return HelperLine(binding, "line", **style)


def _t_label(
    system: mp.CartesianAxes,
    x_val: object,
    graph: _CurvePlot,
    label: object,
    label_color: ParsableManimColor | None,
    triangle_size: float,
    triangle_color: ParsableManimColor | None,
    line_func: type[Line],
    line_color: ParsableManimColor,
    label_direction: ArrayLike,
    label_buff: float,
) -> HelperGroup:
    size = _number(triangle_size, "triangle_size")
    if size <= 0:
        raise ValueError("triangle_size must be positive")
    triangle = RegularPolygon(n=3, start_angle=np.pi / 2, stroke_width=0)
    triangle.set_fill(color=triangle_color, opacity=1)
    triangle.height = size
    text = _Text(label, label_color)

    def derive(binding: _Binding) -> None:
        x = binding.number("x_val")
        if not binding.check_x("x_val"):
            return
        start = [x, system.x_axis._cross_value()]
        bottom = binding.local([start])[0]
        top = _graph_local(system, graph, x)
        if len(top) != len(bottom):
            bottom = np.append(bottom, 0)
        binding.parts["line"] = np.array([bottom, top])
        anchor = np.zeros(3)
        anchor[: len(bottom)] = bottom
        marker = triangle.copy().move_to(anchor, UP)
        binding.parts["triangle"] = marker.points
        if label is not None:
            binding.texts["label"] = text.at(x).next_to(
                marker, np.asarray(label_direction, dtype=float), buff=label_buff
            )

    binding = _Binding(system, derive, {"x_val": x_val}, graph)
    binding.ensure()
    group = HelperGroup()
    if label is not None:
        group.label = _HelperText(binding, "label")
        group.add(group.label)
    group.triangle = _HelperShape(binding, "triangle", triangle)
    group.line = HelperLine(
        binding, "line", **_line_options(line_func, None, line_color)
    )
    group.add(group.triangle, group.line)
    return group


class _DerivedPlot(FunctionPlot):
    def __init__(
        self,
        system: mp.CartesianAxes,
        graph: _CurvePlot,
        integral: bool,
        y_intercept: float,
        /,
        **kwargs: object,
    ) -> None:
        self._binding = _Binding(system, lambda binding: None, {}, graph)
        self._binding_seen = -1
        source = _CalculusSource(
            lambda: graph.source,
            lambda: _limits(system, graph),
            self._revision,
            integral=integral,
            y_intercept=y_intercept,
            x_range=cast(Sequence[float] | None, kwargs.pop("x_range", None)),
            discontinuities=cast(Iterable[float] | None, kwargs.get("discontinuities")),
            dt=cast(float, kwargs.get("dt", 1e-8)),
        )
        kwargs.pop("use_vectorized", None)
        super().__init__(lambda x: x, system, **cast(dict[str, Any], kwargs))
        self.source = source
        self._dirty = True
        self._ensure()

    def _revision(self) -> int:
        self._binding.ensure()
        return self._binding.version

    def _ensure(self) -> None:
        if (
            self._lifecycle.state is lc.State.ATTACHED
            and self._binding_seen != self._revision()
        ):
            self._dirty = True
        super()._ensure()
        self._binding_seen = self._binding.version

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _adopt(self, other: Leaf) -> None:
        if isinstance(other, _DerivedPlot):
            self._binding = other._binding
            self._binding_seen = -1
        super()._adopt(other)


def _tangent_helper(
    system: mp.CartesianAxes,
    x: object,
    graph: _CurvePlot,
    length: object,
    *,
    vector: bool = False,
    **style: Unpack[_TangentOptions],
) -> HelperLine | HelperGroup:
    tip_length = _number(style.pop("tip_length", 0.35), "tip_length")
    tip_width = _number(style.pop("tip_width", tip_length), "tip_width")
    if tip_length <= 0 or tip_width <= 0:
        raise ValueError("tip_length and tip_width must be positive")
    tip = ArrowTriangleFilledTip(length=tip_length, width=tip_width)
    tip.set_color(style.get("color", VMobject().get_color()))
    slope_length = vector and callable(length)

    def derive(binding: _Binding) -> None:
        value = binding.number("x")
        if not binding.check_x("x"):
            return
        size = (
            _number(length(system.slope_of_tangent(value, graph)), "length")
            if slope_length and callable(length)
            else binding.number("length")
        )
        if size < 0:
            raise ValueError("length must be nonnegative")
        point = _graph_point(system, graph, value)
        direction = _tangent(system, graph, value)
        if vector:
            end = point + size * direction
            marker = tip.copy()
            if size < tip_length:
                marker.scale(size / tip_length)
            marker.rotate(np.arctan2(direction[1], direction[0]) - marker.tip_angle)
            marker.shift(end - marker.tip_point)
            binding.parts["tip"] = binding.scene(marker.points)
            binding.parts["line"] = binding.scene_line(point, marker.base)
        else:
            delta = size / 2 * direction
            binding.parts["line"] = binding.scene_line(point - delta, point + delta)

    inputs = {"x": x} if slope_length else {"x": x, "length": length}
    binding = _Binding(system, derive, inputs, graph)
    line = HelperLine(binding, "line", **cast(_HelperOptions, style))
    if not vector:
        return line
    group = HelperGroup(line)
    group.line = line
    group.tip = _HelperShape(binding, "tip", tip)
    group.add(group.tip)
    return group


def _secant(
    system: mp.CartesianAxes,
    x: object,
    graph: _CurvePlot,
    dx: object,
    dx_line_color: ParsableManimColor,
    dy_line_color: ParsableManimColor | None,
    dx_label: object,
    dy_label: object,
    include_secant_line: bool,
    secant_line_color: ParsableManimColor,
    secant_line_length: object,
    dx_label_direction: ArrayLike | None,
    dy_label_direction: ArrayLike | None,
) -> HelperGroup:
    _graph(system, graph)
    if dx is None:
        dx = float(system.x.range.value[1] - system.x.range.value[0]) / 10
    if dy_line_color is None:
        dy_line_color = graph.get_color()
    dx_text, df_text = _Text(dx_label, dx_line_color), _Text(dy_label, dy_line_color)

    def derive(binding: _Binding) -> None:
        value, delta = binding.number("x"), binding.number("dx")
        if not binding.check_x("x") or not binding.check_x("dx", value + delta):
            return
        p1, p2 = graph.source.at([value, value + delta])
        corner = np.array([p2[0], p1[1]])
        locals = binding.local([p1, corner, p2])
        if graph._own.nodes:
            locals = graph._own.forward(np.column_stack((locals, np.zeros(3))))
        binding.parts["dx_line"], binding.parts["df_line"] = locals[:2], locals[1:]
        points = system.frame.mapping.forward(locals)
        if include_secant_line:
            size = binding.number("secant_line_length")
            if size < 0:
                raise ValueError("secant_line_length must be nonnegative")
            chord = points[-1] - points[0]
            direction = (
                _tangent(system, graph, value)
                if delta == 0
                else chord / np.linalg.norm(chord)
            )
            middle = (points[0] + points[-1]) / 2
            binding.parts["secant_line"] = binding.scene_line(
                middle - size / 2 * direction, middle + size / 2 * direction
            )
        labels = VGroup()
        if dx_label is not None:
            binding.texts["dx_label"] = dx_text.at(delta)
            labels.add(binding.texts["dx_label"])
        if dy_label is not None:
            binding.texts["df_label"] = df_text.at(delta)
            labels.add(binding.texts["df_label"])
        dx_leg, df_leg = Line(*points[:2]), Line(*points[1:])
        if len(labels):
            max_width, max_height = 0.8 * dx_leg.width, 0.8 * df_leg.height
            if labels.width > max_width:
                labels.width = max_width
            if labels.height > max_height:
                labels.height = max_height
        sign = np.sign(delta) if delta else 1
        for name, leg, side in (
            (
                "dx_label",
                dx_leg,
                sign * DOWN if dx_label_direction is None else dx_label_direction,
            ),
            (
                "df_label",
                df_leg,
                sign * RIGHT if dy_label_direction is None else dy_label_direction,
            ),
        ):
            if name in binding.texts:
                text = binding.texts[name]
                text.next_to(leg, np.asarray(side, dtype=float), buff=text.height / 2)
                for glyph in text.submobjects:
                    glyph.points = binding.scene(glyph.points)

    binding = _Binding(
        system,
        derive,
        {"x": x, "dx": dx, "secant_line_length": secant_line_length},
        graph,
    )
    group = HelperGroup()
    group.dx_line = HelperLine(binding, "dx_line", color=dx_line_color)
    group.df_line = HelperLine(binding, "df_line", color=dy_line_color)
    group.add(group.dx_line, group.df_line)
    if dx_label is not None:
        group.dx_label = _HelperText(binding, "dx_label")
        group.add(group.dx_label)
    if dy_label is not None:
        group.df_label = _HelperText(binding, "df_label")
        group.add(group.df_label)
    if include_secant_line:
        group.secant_line = HelperLine(binding, "secant_line", color=secant_line_color)
        group.add(group.secant_line)
    return group
