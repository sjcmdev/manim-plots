"""Bound line, calculus and region helpers with the ordinary artist lifecycle."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Sequence
from numbers import Real
from typing import Any, Self, TypedDict, Unpack, cast

import numpy as np
from manim import (
    DEFAULT_DASH_LENGTH,
    DOWN,
    RIGHT,
    UP,
    Arrow,
    ArrowTriangleFilledTip,
    DashedLine,
    Dot,
    Line,
    Mobject,
    RegularPolygon,
    Text,
    VGroup,
    VMobject,
)
from manim.utils.color import (
    ManimColor,
    ParsableManimColor,
    color_gradient,
    invert_color,
)
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import FrameMap, SystemMap
from manim_plots.core.params import Parameter, _same
from manim_plots.core.payload import Payload
from manim_plots.core.shape import _assemble, arc_length, clip_region, corners, smooth
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.shape import dash as dash_path
from manim_plots.core.sources import ArraySource, Box, _CalculusSource
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LineStyle,
    _clip_axes,
    _clip_box,
    _CurvePlot,
    _cycle_style,
    _dash_pattern,
    _unclipped_box,
)
from manim_plots.mobjects.leaves import (
    Leaf,
    _ArtistOptions,
    _label,
    _replace_glyphs,
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
        if system.parent is not None:
            system.parent._sync_data()
        system._sync_data()
        graph = self.graph
        if isinstance(graph, _DerivedPlot):
            graph._binding.ensure()
        state = (
            system._data_version,
            system.frame.version,
            system.x_axis._position,
            system.x_axis._position_fraction,
            system.x_axis._position_offset,
            system.y_axis._position,
            system.y_axis._position_fraction,
            system.y_axis._position_offset,
            None if system.parent is None else system.parent._data_version,
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

    x_line: HelperLine
    y_line: HelperLine
    z_line: HelperLine
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


class _RegionBinding(_Binding):
    def __init__(
        self,
        system: mp.CartesianAxes,
        derive: Callable[[_Binding], None],
        inputs: dict[str, object],
        graphs: Sequence[_CurvePlot],
    ) -> None:
        super().__init__(system, derive, inputs, graphs[0] if graphs else None)
        self._others = [_Binding(system, lambda b: None, {}, g) for g in graphs[1:]]
        self._other_seen: tuple[int, ...] = ()
        self.boundaries: dict[str, list[tuple[FloatArray, FloatArray]]] = {}
        self.colors: list[ManimColor] = []
        self.rectangle_style: dict[str, object] = {}
        self.rectangle_blend = False
        self.transpose = False

    def local(self, points: ArrayLike) -> FloatArray:
        coords = np.asarray(points, dtype=float)
        # An excluded scale-domain tail still fills up to the viewport edge.
        for index, axis in enumerate((self.system.x_axis, self.system.y_axis)):
            invalid = np.isfinite(coords[:, index]) & ~np.isfinite(
                axis._scale.forward(coords[:, index])
            )
            if invalid.any():
                coords = coords.copy()
                lo, hi = sorted(axis.range.value)
                coords[invalid, index] = np.clip(coords[invalid, index], lo, hi)
        return super().local(coords)

    def poll(self) -> None:
        super().poll()
        for other in self._others:
            other.poll()

    def needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return super().needs_sync(moving) or any(
            other.needs_sync(moving) for other in self._others
        )

    def ensure(self) -> None:
        for other in self._others:
            other.ensure()
        seen = tuple(other.version for other in self._others)
        if seen != self._other_seen:
            self._seen = None
            self._other_seen = seen
        super().ensure()


class FilledRegion(_CurvePlot):
    """Draw a registered filled region with persistent, independent style.

    Parameters
    ----------
    binding, part
        Shared boundary derivation and its part name.
    **style
        VMobject style and ordinary artist clipping options. Colour sequences
        produce Manim's gradient.

    Notes
    -----
    Unlike Manim's Polygon, this leaf follows graphs and bound inputs. It uses
    sampled, smoothed boundaries, splits crossing lobes and clips closed fills.
    Re-derivation only replaces geometry, preserving later style changes.
    """

    def __init__(self, binding: _RegionBinding, part: str, **style: object) -> None:
        self._binding, self._part = binding, part
        self._binding_seen = -1
        self._region_styling = True
        self._fill_color_set = self._stroke_color_set = False
        super().__init__(
            ArraySource(np.empty((0, 2))),
            binding.system,
            use_smoothing=False,
            **cast(dict[str, Any], style),
        )
        color = style.get("color")
        if isinstance(color, (tuple, list)):
            self.set_color(cast(ParsableManimColor, color))
            if style.get("fill_color") is not None:
                self.set_fill(cast(ParsableManimColor, style["fill_color"]))
            if style.get("stroke_color") is not None:
                self.set_stroke(cast(ParsableManimColor, style["stroke_color"]))
        self._region_styling = False
        binding.system.add(self)

    def set_fill(
        self,
        color: ParsableManimColor | None = None,
        opacity: float | None = None,
        family: bool = True,
    ) -> Self:
        """Set fill style, preserving an explicit colour across derivations.

        Parameters
        ----------
        color, opacity, family
            Manim's colour, opacity and family propagation options.

        Notes
        -----
        Matches Manim's styling; an explicit colour overrides future Riemann
        gradient defaults while an opacity change leaves those defaults active.
        """
        if color is not None and not self._region_styling:
            self._fill_color_set = True
        return super().set_fill(color, opacity, family)

    def set_stroke(
        self,
        color: ParsableManimColor | None = None,
        width: float | None = None,
        opacity: float | None = None,
        background: bool = False,
        family: bool = True,
    ) -> Self:
        """Set stroke style, preserving an explicit colour across derivations.

        Parameters
        ----------
        color, width, opacity, background, family
            Manim's stroke style and propagation options.

        Notes
        -----
        Matches Manim's styling; an explicit foreground colour also overrides
        future Riemann blend defaults, independently of width and opacity.
        """
        if color is not None and not background and not self._region_styling:
            self._stroke_color_set = True
        return super().set_stroke(
            cast(ParsableManimColor, color), width, opacity, background, family
        )

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            self._binding.ensure()
            if self._binding_seen != self._binding.version:
                self._dirty = True
        super()._ensure()

    def _adopt(self, other: Leaf) -> None:
        if isinstance(other, FilledRegion):
            self._binding, self._part = other._binding, other._part
            self._binding_seen = -1
        self._region_styling = True
        try:
            super()._adopt(other)
        finally:
            self._region_styling = False
        if isinstance(other, FilledRegion):
            self._fill_color_set = other._fill_color_set
            self._stroke_color_set = other._stroke_color_set

    def _rebuild(self) -> None:
        binding = self._binding
        binding.ensure()
        system = self._system
        if system is None:
            return
        bounds = _clip_box(system, self._clip)
        axes = _clip_axes(self._clip)
        parts: list[FloatArray] = []
        if binding.valid:
            for upper, lower in binding.boundaries.get(self._part, []):
                order = [1, 0] if binding.transpose else [0, 1]
                region_bounds = Box(bounds.lower[order], bounds.upper[order])
                payload = clip_region(
                    upper[:, order],
                    lower[:, order],
                    region_bounds,
                    clip_x=axes[order[0]] is not False,
                    clip_y=axes[order[1]] is not False,
                )
                if binding.transpose:
                    payload = Payload._trusted(
                        "path", payload.coords[:, order], payload.segments
                    )
                parts.extend(payload.coords[a:b] for a, b in payload.segments)
        self._geometry_payload = _assemble(parts, 2)
        self._place(self._frame())
        self._binding_seen = binding.version
        self._data_seen = system._data_version
        self._dirty = False


def _graph_boundary(system: mp.CartesianAxes, graph: _CurvePlot) -> list[FloatArray]:
    limits = _limits(system, graph)
    ends = system._data.forward(
        np.column_stack((limits, np.full(2, system._axis_cross_value(0))))
    )[:, 0]
    lower, upper = system.bounds.lower.copy(), system.bounds.upper.copy()
    lower[0], upper[0] = min(lower[0], min(ends)), max(upper[0], max(ends))
    bounds = Box(lower, upper)
    payload = system._data.apply_payload(
        graph.source.sample(SystemMap(system._data, system.frame.mapping), bounds)
    )
    payload = (smooth if graph.use_smoothing else corners)(payload, bounds)
    parts = []
    t = np.linspace(0, 1, 17)[:, None]
    weights = np.column_stack(
        ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3)
    )
    for start, stop in payload.segments:
        curves = payload.coords[start:stop].reshape(-1, 4, 2)
        points = np.einsum("tk,nkd->ntd", weights, curves).reshape(-1, 2)
        if graph._own.nodes:
            points = graph._own.forward(
                np.column_stack((points, np.zeros(len(points))))
            )[:, :2]
        points = points[np.argsort(points[:, 0], kind="stable")]
        parts.append(points[np.r_[True, np.diff(points[:, 0]) > 0]])
    return parts


def _paired_boundaries(
    upper: list[FloatArray], lower: list[FloatArray], limits: FloatArray
) -> list[tuple[FloatArray, FloatArray]]:
    result = []
    for a in upper:
        for b in lower:
            if len(a) < 2 or len(b) < 2:
                continue
            lo, hi = (
                max(limits[0], a[0, 0], b[0, 0]),
                min(limits[1], a[-1, 0], b[-1, 0]),
            )
            if lo >= hi:
                continue
            x = np.unique(np.r_[lo, a[:, 0], b[:, 0], hi])
            x = x[(x >= lo) & (x <= hi)]
            result.append(
                (
                    np.column_stack((x, np.interp(x, a[:, 0], a[:, 1]))),
                    np.column_stack((x, np.interp(x, b[:, 0], b[:, 1]))),
                )
            )
    return result


def _region_range(
    binding: _Binding, graph: _CurvePlot, bounded_graph: object, explicit: bool
) -> tuple[float, float]:
    system = binding.system
    a, b = (
        (
            _number(binding.parameters["x_range[0]"].value, "x_range[0]"),
            _number(binding.parameters["x_range[1]"].value, "x_range[1]"),
        )
        if explicit
        else _limits(system, graph)
    )
    if isinstance(bounded_graph, _CurvePlot):
        lo, hi = _limits(system, bounded_graph)
        if lo > b:
            if binding.version:
                binding.valid = False
                return a, a
            raise ValueError(f"Ranges not matching: {lo} < {b}")
        if hi < a:
            if binding.version:
                binding.valid = False
                return a, a
            raise ValueError(f"Ranges not matching: {hi} > {a}")
        a, b = max(a, lo), min(b, hi)
    if explicit:
        lo, hi = sorted(_limits(system, graph))
        for name in ("x_range[0]", "x_range[1]"):
            parameter = binding.parameters[name]
            value = binding.number(name)
            valid = lo <= value <= hi
            if parameter.tracker is not None:
                axis_lo, axis_hi = sorted(system.x.range.value)
                valid &= axis_lo <= value <= axis_hi
            if not valid:
                if not binding.version:
                    raise ValueError(
                        f"{name} must be inside the graph domain and axis range"
                    )
                binding.valid = False
    return a, b


def _range_inputs(x_range: Sequence[object] | None) -> dict[str, object]:
    if x_range is None:
        return {}
    if len(x_range) not in (2, 3):
        raise ValueError("x_range must have length 2 or 3")
    return {"x_range[0]": x_range[0], "x_range[1]": x_range[1]}


def _area(
    system: mp.CartesianAxes,
    graph: _CurvePlot,
    x_range: Sequence[object] | None,
    color: object,
    opacity: float,
    bounded_graph: _CurvePlot | float | None,
    **style: object,
) -> FilledRegion:
    _graph(system, graph)
    graphs = [graph]
    if isinstance(bounded_graph, _CurvePlot):
        _graph(system, bounded_graph)
        graphs.append(bounded_graph)
    elif bounded_graph is not None:
        _number(bounded_graph, "bounded_graph")

    def derive(base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        a, b = _region_range(binding, graph, bounded_graph, x_range is not None)
        ends = binding.local(
            [[a, system._axis_cross_value(0)], [b, system._axis_cross_value(0)]]
        )
        limits = np.sort(ends[:, 0])
        top = _graph_boundary(system, graph)
        if isinstance(bounded_graph, _CurvePlot):
            bottom = _graph_boundary(system, bounded_graph)
        else:
            baseline = (
                system._axis_cross_value(0) if bounded_graph is None else bounded_graph
            )
            bottom = [binding.local([[a, baseline], [b, baseline]])]
            bottom[0] = bottom[0][np.argsort(bottom[0][:, 0])]
        binding.boundaries["area"] = _paired_boundaries(top, bottom, limits)

    binding = _RegionBinding(system, derive, _range_inputs(x_range), graphs)
    style.setdefault("color", color)
    style.setdefault("fill_opacity", opacity)
    style.setdefault("stroke_opacity", opacity)
    return FilledRegion(binding, "area", **style)


def _fill_between(
    system: mp.CartesianAxes,
    x: ArrayLike,
    y1: object,
    y2: object,
    where: ArrayLike | None,
    interpolate: bool,
    *,
    transpose: bool = False,
    **style: object,
) -> FilledRegion:
    xs = np.array(x, dtype=float, copy=True)
    if xs.ndim != 1:
        raise ValueError("x must be one-dimensional")
    invalid = np.flatnonzero(~np.isfinite(xs))
    if len(invalid):
        raise ValueError(f"x[{invalid[0]}] must be finite")
    mask = (
        np.ones(len(xs), dtype=bool)
        if where is None
        else np.array(where, dtype=bool, copy=True)
    )
    if mask.shape != xs.shape:
        raise ValueError("where must have the same length as x")
    xs.flags.writeable = mask.flags.writeable = False
    fixed: dict[str, FloatArray] = {}
    for name, boundary in (("y1", y1), ("y2", y2)):
        if not isinstance(boundary, _CurvePlot) and not callable(boundary):
            fixed[name] = np.array(boundary, dtype=float, copy=True)
            fixed[name].flags.writeable = False
    graphs = [y for y in (y1, y2) if isinstance(y, _CurvePlot)]
    for graph in graphs:
        _graph(system, graph)

    def values(y: object, name: str) -> FloatArray:
        if isinstance(y, _CurvePlot):
            result = y.source.at(xs)[:, 1]
        elif callable(y):
            result = np.array([y(float(v)) for v in xs], dtype=float)
        else:
            result = fixed[name]
        if result.ndim == 0:
            result = np.full(len(xs), result)
        if result.shape != xs.shape:
            raise ValueError(f"{name} must be scalar or have the same length as x")
        return result

    def derive(base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        a, b = values(y1, "y1"), values(y2, "y2")
        valid = mask & np.isfinite(a) & np.isfinite(b)
        edges = np.diff(np.r_[False, valid, False].astype(int))
        pairs = []
        for start, stop in zip(
            map(int, np.flatnonzero(edges == 1)),
            map(int, np.flatnonzero(edges == -1)),
            strict=True,
        ):
            grid, top, bottom = xs[start:stop], a[start:stop], b[start:stop]
            if interpolate:
                for left, right, prepend in (
                    (max(0, start - 1), start, True),
                    (stop - 1, min(len(xs) - 1, stop), False),
                ):
                    d0, d1 = a[left] - b[left], a[right] - b[right]
                    if left != right and d0 * d1 <= 0 and d0 != d1:
                        t = d0 / (d0 - d1)
                        cross_x = xs[left] + t * (xs[right] - xs[left])
                        cross_y = a[left] + t * (a[right] - a[left])
                        grid = np.r_[cross_x, grid] if prepend else np.r_[grid, cross_x]
                        top = np.r_[cross_y, top] if prepend else np.r_[top, cross_y]
                        bottom = (
                            np.r_[cross_y, bottom]
                            if prepend
                            else np.r_[bottom, cross_y]
                        )
            if len(grid) < 2:
                continue
            columns = [1, 0] if transpose else [0, 1]
            upper = binding.local(np.column_stack((grid, top))[:, columns])
            lower = binding.local(np.column_stack((grid, bottom))[:, columns])
            if transpose:
                pairs.append((upper, lower))
                continue
            for boundary, source in ((upper, y1), (lower, y2)):
                if isinstance(source, _CurvePlot) and source._own.nodes:
                    boundary[:] = source._own.forward(
                        np.column_stack((boundary, np.zeros(len(boundary))))
                    )[:, :2]
            order = np.argsort(upper[:, 0], kind="stable")
            if np.array_equal(upper[:, 0], lower[:, 0]):
                pairs.append((upper, lower))
            else:
                limits = binding.local(
                    [
                        [min(grid), system._axis_cross_value(0)],
                        [max(grid), system._axis_cross_value(0)],
                    ]
                )[:, 0]
                pairs.extend(
                    _paired_boundaries(
                        [upper[order]],
                        [lower[np.argsort(lower[:, 0], kind="stable")]],
                        np.sort(limits),
                    )
                )
        binding.boundaries["area"] = pairs

    binding = _RegionBinding(system, derive, {}, graphs)
    binding.transpose = transpose
    _cycle_style(system, cast(_VMStyle, style), scatter=True)
    style.setdefault("fill_opacity", 0.3)
    style.setdefault("stroke_width", 0)
    return FilledRegion(binding, "area", **style)


def _update_riemann(group: Mobject) -> None:
    assert isinstance(group, _RiemannGroup)
    group._binding.poll()
    group._ensure_regions()


class _RiemannGroup(HelperGroup):
    def __init__(
        self, binding: _RegionBinding, blend: bool, style: dict[str, object]
    ) -> None:
        self._binding, self._blend, self._region_style = binding, blend, style
        binding.rectangle_style, binding.rectangle_blend = style, blend
        self._region_ready = False
        self._binding_seen = -1
        self._cache = np.empty((0, 3))
        super().__init__()
        self._region_ready = True
        self._ensure_regions()
        self.add_updater(_update_riemann)

    @property
    def points(self) -> FloatArray:
        if self._region_ready:
            self._ensure_regions()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)

    def __len__(self) -> int:
        self._ensure_regions()
        return len(self.submobjects)

    def _ensure_regions(self) -> None:
        if not self._region_ready or self.updating_suspended:
            return
        if self.submobjects:
            first = self.submobjects[0]
            if (
                isinstance(first, FilledRegion)
                and first._binding.derive is not self._binding.derive
                and all(
                    isinstance(rect, FilledRegion)
                    and rect._binding.derive is first._binding.derive
                    for rect in self.submobjects
                )
            ):
                # Transform adopts leaves separately; restore their shared derivation.
                self._binding = first._binding
                self._region_style = self._binding.rectangle_style
                self._blend = self._binding.rectangle_blend
                self._binding_seen = -1
                for i, member in enumerate(self.submobjects):
                    rect = cast(FilledRegion, member)
                    rect._binding, rect._part = self._binding, str(i)
                    rect._binding_seen = -1
        binding = self._binding
        binding.ensure()
        if self._binding_seen == binding.version:
            return
        self._binding_seen = binding.version
        count = len(binding.colors)
        for removed in self.submobjects[count:]:
            if removed in binding.system.artists:
                binding.system.remove(removed)
        del self.submobjects[count:]
        for i, color in enumerate(binding.colors):
            if i == len(self.submobjects):
                style = {"color": color, "fill_color": color, **self._region_style}
                if self._blend:
                    style["stroke_color"] = style["fill_color"]
                rect = FilledRegion(binding, str(i), **style)
                self.submobjects.append(rect)
            else:
                rect = cast(FilledRegion, self.submobjects[i])
                rect._region_styling = True
                try:
                    if (
                        "fill_color" not in self._region_style
                        and not rect._fill_color_set
                    ):
                        rect.set_fill(color)
                    if self._blend and not rect._stroke_color_set:
                        rect.set_stroke(rect.get_fill_color())
                finally:
                    rect._region_styling = False


def _riemann(
    system: mp.CartesianAxes,
    graph: _CurvePlot,
    x_range: Sequence[object] | None,
    dx: object,
    input_sample_type: str | Callable[[float, float], float],
    stroke_width: float,
    stroke_color: object,
    fill_opacity: float,
    color: object,
    show_signed_area: bool,
    bounded_graph: _CurvePlot | float | None,
    blend: bool,
    width_scale_factor: float,
    **style: object,
) -> HelperGroup:
    _graph(system, graph)
    if not callable(input_sample_type) and input_sample_type not in (
        "left",
        "right",
        "center",
    ):
        raise ValueError("Invalid input sample type")
    graphs = [graph]
    if isinstance(bounded_graph, _CurvePlot):
        _graph(system, bounded_graph)
        graphs.append(bounded_graph)
    elif bounded_graph is not None:
        _number(bounded_graph, "bounded_graph")
    palette = color if isinstance(color, (list, tuple)) else [color]

    def derive(base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        step = binding.number("dx")
        if step <= 0:
            raise ValueError("dx must be finite and positive")
        a, b = _region_range(binding, graph, bounded_graph, x_range is not None)
        count = max(0, int(np.ceil((b - a) / step - 1e-9)))
        xs = a + np.arange(count) * step
        if callable(input_sample_type):
            samples = np.array(
                [
                    _number(
                        input_sample_type(float(x), float(x + step)),
                        "input_sample_type",
                    )
                    for x in xs
                ]
            )
        else:
            fraction = {"left": 0, "right": 1, "center": 0.5}[input_sample_type]
            samples = xs + fraction * step
        tops = graph.source.at(samples)
        local_top = binding.local(tops)
        if graph._own.nodes:
            local_top = graph._own.forward(
                np.column_stack((local_top, np.zeros(count)))
            )[:, :2]
        if isinstance(bounded_graph, _CurvePlot):
            bottoms = binding.local(bounded_graph.source.at(samples))
            if bounded_graph._own.nodes:
                bottoms = bounded_graph._own.forward(
                    np.column_stack((bottoms, np.zeros(count)))
                )[:, :2]
        else:
            baseline = (
                system._axis_cross_value(0) if bounded_graph is None else bounded_graph
            )
            bottoms = binding.local(
                np.column_stack((samples, np.full(count, baseline)))
            )
        ends = binding.local(
            np.column_stack(
                (
                    np.r_[xs, xs + width_scale_factor * step],
                    np.full(2 * count, system._axis_cross_value(0)),
                )
            )
        )[:, 0]
        binding.boundaries = {}
        binding.colors = color_gradient(cast(list[ParsableManimColor], palette), count)
        for i in range(count):
            x = np.sort(ends[[i, i + count]])
            top, bottom = local_top[i, 1], bottoms[i, 1]
            if np.isfinite([*x, top, bottom]).all():
                binding.boundaries[str(i)] = [
                    (
                        np.column_stack((x, [top, top])),
                        np.column_stack((x, [bottom, bottom])),
                    )
                ]
            if top < bottom and show_signed_area:
                binding.colors[i] = invert_color(binding.colors[i])

    binding = _RegionBinding(
        system, derive, {**_range_inputs(x_range), "dx": dx}, graphs
    )
    style = {
        "stroke_width": stroke_width,
        "stroke_color": stroke_color,
        "fill_opacity": fill_opacity,
        **style,
    }
    return _RiemannGroup(binding, blend, style)


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
    dim = len(system._ranges)
    if not isinstance(index, int) or isinstance(index, bool):
        raise TypeError("index must identify an axis")
    if index not in range(dim):
        raise ValueError("index must identify an axis")
    if isinstance(point, Mobject):
        point = point.get_center
    dynamic = callable(point)
    data = point if dynamic else system.p2c(cast(ArrayLike, point))

    def derive(binding: _Binding) -> None:
        raw = binding.parameters["point"].value
        coords = system.p2c(raw) if dynamic else np.asarray(raw, dtype=float)
        if dim == 3:
            binding.valid = all(
                min(axis.range.value) <= coords[i] <= max(axis.range.value)
                for i, axis in enumerate(system._ranges)
            )
        start = coords.copy()
        if dim == 2:
            start[1 - index] = system._axis_cross_value(index)
        else:
            for i in range(dim):
                if i != index:
                    start[i] = system._axis_cross_value(i)
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
                bottom = binding.local([[x, system._axis_cross_value(0)]])[0]
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
    from manim_plots.mobjects.axis import resolve_categories

    value = resolve_categories(system.get_axis(index), value, data=False)
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
        start = [x, system._axis_cross_value(0)]
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


def _span(
    system: mp.CartesianAxes,
    index: int,
    minimum: object,
    maximum: object,
    fraction_min: object,
    fraction_max: object,
    **style: object,
) -> FilledRegion:
    def derive(base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        other = system.get_axis(1 - index)
        ends = other._scale.forward(other.range.value)
        fractions = np.array([binding.number("fmin"), binding.number("fmax")])
        extents = other._scale.inverse(ends[0] + fractions * (ends[1] - ends[0]))
        limits = [binding.number("minimum"), binding.number("maximum")]
        upper = np.column_stack((limits, np.full(2, extents[1])))
        lower = np.column_stack((limits, np.full(2, extents[0])))
        order = [0, 1] if index == 0 else [1, 0]
        binding.boundaries["area"] = [
            (binding.local(upper[:, order]), binding.local(lower[:, order]))
        ]

    binding = _RegionBinding(
        system,
        derive,
        dict(minimum=minimum, maximum=maximum, fmin=fraction_min, fmax=fraction_max),
        [],
    )
    binding.transpose = index == 1
    _cycle_style(system, cast(_VMStyle, style), scatter=True)
    style.setdefault("fill_opacity", 0.25)
    style.setdefault("stroke_width", 0)
    return FilledRegion(binding, "area", **style)


class _NativeBinding:
    def __init__(self, mob: Mobject, place: Callable[[], None]) -> None:
        self.mob, self.place = mob, place
        self.busy = False
        if isinstance(mob, _LivePoints):
            mob.__dict__["_helper_driver"] = self
        mob.add_updater(lambda _: self._ensure())

    def glyphs(self, native: Mobject) -> None:
        if isinstance(native, VMobject):
            glyphs = list(_label(native).submobjects)
            _replace_glyphs(self.mob, glyphs)
            for leaf in self.mob.get_family():
                if isinstance(leaf, Leaf):
                    cast(Any, leaf)._label_owner = self

    def _ensure(self) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            self.place()
        finally:
            self.busy = False


class _LivePoints:
    @property
    def points(self) -> FloatArray:
        driver = self.__dict__.get("_helper_driver")
        if driver is not None:
            driver._ensure()
        return cast(FloatArray, self.__dict__.get("_helper_points", np.empty((0, 3))))

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._helper_points = np.asarray(value, dtype=float)


class _LiveArrow(_LivePoints, Arrow):
    def get_end(self) -> FloatArray:
        driver = self.__dict__.get("_helper_driver")
        if driver is not None:
            driver._ensure()
        return super().get_end()


class _LiveDot(_LivePoints, Dot):
    pass


class _LiveLine(_LivePoints, Line):
    pass


class _LiveShape(_LivePoints, VMobject):
    pass


class _LiveText(_LivePoints, Text):
    pass


def _annotate_2d(
    system: mp.CartesianAxes,
    s: str | Mobject,
    xy: Sequence[object],
    xytext: Sequence[object] | None = None,
    *,
    arrow: bool = True,
    buff: float = 0.1,
    arrow_config: dict[str, Any] | None = None,
    **text_style: object,
) -> HelperGroup:
    if len(xy) != 2 or (xytext is not None and len(xytext) != 2):
        raise ValueError("xy and xytext must have two coordinates")
    buff = _number(buff, "buff")
    text = (
        s
        if isinstance(s, Mobject)
        else _LiveText(s, **cast(Any, {"font_size": 24, **text_style}))
    )
    inputs = {f"p{i}": v for i, v in enumerate(xy)}
    if xytext is not None:
        inputs.update({f"t{i}": v for i, v in enumerate(xytext)})
    binding = _Binding(system, lambda _: None, inputs)
    shaft = _LiveArrow(**{**(arrow_config or {}), "buff": 0}) if arrow else None
    seen = -1

    def place() -> None:
        nonlocal seen
        binding.poll()
        binding.ensure()
        if seen == binding.version:
            return
        end = system.c2p(binding.number("p0"), binding.number("p1"))
        center = (
            end + np.array([0.6, 0.6, 0])
            if xytext is None
            else system.c2p(binding.number("t0"), binding.number("t1"))
        )
        text.move_to(center)
        if shaft is not None:
            delta = end - center
            length = float(np.linalg.norm(delta))
            ratios = [
                size / 2 / abs(d)
                for size, d in zip((text.width, text.height), delta[:2], strict=True)
                if d != 0
            ]
            t = min(ratios, default=0)
            start = center + t * delta + buff * delta / max(length, 1e-12)
            fresh = Arrow(start, end, **{**(arrow_config or {}), "buff": 0})
            shaft.become(fresh)
        seen = binding.version

    driver = _NativeBinding(text, place)
    driver.glyphs(text)
    if shaft is not None:
        shaft.__dict__["_helper_driver"] = driver
        for leaf in shaft.get_family():
            if leaf is not shaft and isinstance(leaf, VMobject):
                # Arrow tips must also trigger derivation before their points are read.
                leaf.add_updater(lambda _: driver._ensure())
    group = HelperGroup(cast(VMobject, text))
    cast(Any, group).text, cast(Any, group).arrow = text, shaft
    if shaft is not None:
        group.add(shaft)
    group.add_updater(lambda _: driver._ensure())
    driver._ensure()
    return group


def _crosshair(
    system: mp.CartesianAxes,
    x: object,
    y: object = None,
    *,
    graph: FunctionPlot | None = None,
    readout: bool = True,
    fmt: str = "({:.2f}, {:.2f})",
    **style: object,
) -> HelperGroup:
    if y is None and graph is None:
        raise ValueError("supply y or graph")
    if graph is not None:
        _graph(system, graph)
    binding = _Binding(
        system, lambda _: None, {"x": x, **({"y": y} if y is not None else {})}, graph
    )

    def values() -> tuple[float, float]:
        binding.poll()
        binding.ensure()
        xx = binding.number("x")
        yy = (
            binding.number("y")
            if y is not None
            else float(cast(FunctionPlot, graph).source.at(xx)[0, 1])
        )
        return xx, yy

    line_style = {
        "color": system.x_axis.get_color(),
        "stroke_width": 2,
        "stroke_opacity": 0.6,
        **style,
    }
    vline = system.axvline(lambda: values()[0], **cast(Any, line_style))
    hline = system.axhline(lambda: values()[1], **cast(Any, line_style))
    dot = _LiveDot(color=cast(Any, line_style["color"]))
    text = _LiveText(fmt.format(*values()), font_size=24) if readout else None
    current = fmt.format(*values())
    group = HelperGroup(vline, hline, dot)
    cast(Any, group).vline, cast(Any, group).hline = vline, hline
    cast(Any, group).dot, cast(Any, group).readout = dot, text

    def place() -> None:
        nonlocal current
        xx, yy = values()
        dot.move_to(system.c2p(xx, yy))
        if text is None:
            return
        formatted = fmt.format(xx, yy)
        if formatted != current:
            fresh = Text(formatted, font_size=24)
            fresh.match_style(text)
            driver.glyphs(fresh)
            text.text, current = formatted, formatted
        direction = np.array([1.0, 1.0, 0.0])
        text.next_to(dot, direction, buff=0.1)
        box = system.c2p(
            np.array(
                [
                    [system.x_range[0], system.y_range[0]],
                    [system.x_range[1], system.y_range[1]],
                ]
            )
        )
        if text.get_right()[0] > box[:, 0].max():
            direction[0] = -1
        if text.get_top()[1] > box[:, 1].max():
            direction[1] = -1
        text.next_to(dot, direction, buff=0.1)

    driver = _NativeBinding(dot if text is None else text, place)
    dot.__dict__["_helper_driver"] = driver
    if text is not None:
        driver.glyphs(text)
        group.add(text)
    group.add_updater(lambda _: driver._ensure())
    driver._ensure()
    return group


def _end_label(
    system: mp.CartesianAxes,
    graph: _CurvePlot,
    label: str | Mobject | None = None,
    *,
    fmt: str = "{:.2f}",
    direction: ArrayLike = RIGHT,
    buff: float = 0.15,
    **text_style: object,
) -> Mobject:
    _graph(system, graph)
    text_style.setdefault("color", graph.get_stroke_color())
    text = (
        label
        if isinstance(label, Mobject)
        else _LiveText(label or "", **cast(Any, {"font_size": 24, **text_style}))
    )
    if not isinstance(label, Mobject):
        # Empty Text has no glyphs to carry its colour into match_style.
        text.set_color(cast(ParsableManimColor, text_style["color"]))
    current: str | None = None
    template = text.copy()
    hidden = False

    def place() -> None:
        nonlocal current, hidden
        points = graph.points
        if not len(points):
            for leaf in text.family_members_with_points():
                leaf.clear_points()
            hidden = True
            return
        end = points[-1]
        formatted = fmt.format(system.p2c(end)[1]) if label is None else label
        if formatted != current or hidden:
            fresh = (
                Text(formatted, **cast(Any, {"font_size": 24, **text_style}))
                if isinstance(formatted, str)
                else template.copy()
            )
            fresh.match_style(text)
            driver.glyphs(fresh)
            if isinstance(text, Text) and isinstance(fresh, Text):
                text.text = fresh.text
            current = cast(str | None, formatted)
            hidden = False
        text.next_to(end, np.asarray(direction), buff=buff)

    driver = _NativeBinding(text, place)
    driver._ensure()
    return text
