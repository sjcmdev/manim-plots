"""Box-cut data planes, lines and their bound intersections."""

from __future__ import annotations

from collections.abc import Callable
from itertools import product
from typing import Any, cast

import numpy as np
from manim import Mobject

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.payload import Payload
from manim_plots.core.scales import LinearScale
from manim_plots.core.shape import corners
from manim_plots.core.sources import ArraySource, ParametricSource
from manim_plots.mobjects.artists import (
    ParametricPlot,
    ScatterPlot,
    _CurvePlot,
    _MarkerLeaf,
)
from manim_plots.mobjects.helpers import HelperGroup, _Binding, _parameter
from manim_plots.mobjects.leaves import _ArtistOptions, _VMStyle


def _ensure_binding(binding: _Binding) -> None:
    # Lazy reads also work when the artist is not in the scene's update family.
    for parameter in binding.parameters.values():
        parameter.poll(parameter.version + 1)
    binding.ensure()


def _marker_point(
    system: mp.CartesianAxes, point: FloatArray
) -> tuple[FloatArray, bool]:
    visible = bool(np.isfinite(point).all()) and all(
        min(axis.range.value) <= point[i] <= max(axis.range.value)
        for i, axis in enumerate(system._ranges)
    )
    if visible:
        return point, True
    return np.array([np.mean(axis.range.value) for axis in system._ranges]), False


def _data_point(value: object, name: str) -> object:
    if isinstance(value, Mobject) or callable(value):
        return value
    try:
        entries = tuple(cast(Any, value))
    except TypeError as exc:
        raise TypeError(f"{name} must be a data triple, callable or Mobject") from exc
    if len(entries) != 3:
        raise ValueError(f"{name} must have three coordinates")
    return tuple(_parameter(entry, f"{name}[{i}]") for i, entry in enumerate(entries))


def _inputs(resolved: object, name: str, system: mp.ThreeDAxes) -> dict[str, object]:
    if isinstance(resolved, Mobject):
        return {name: lambda: system.p2c(resolved.get_center())}
    if callable(resolved):
        return {name: resolved}
    return {
        f"{name}{i}": p.tracker if p.tracker is not None else p.value
        for i, p in enumerate(cast(Any, resolved))
    }


def _read(binding: _Binding, name: str) -> FloatArray:
    if name in binding.parameters:
        value = np.asarray(binding.parameters[name].value, dtype=float)
    else:
        value = np.array([binding.number(f"{name}{i}") for i in range(3)])
    if value.shape != (3,) or not np.isfinite(value).all():
        raise ValueError(f"{name} must be a finite data triple")
    return value


def _polygon(system: mp.ThreeDAxes, p: FloatArray, n: FloatArray) -> FloatArray:
    lows, highs = np.array([a.range.value for a in system._ranges]).T
    found: list[FloatArray] = []
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for bits in product((0, 1), repeat=2):
            a = lows.copy()
            for i, bit in zip(others, bits, strict=True):
                a[i] = (lows, highs)[bit][i]
            b = a.copy()
            b[axis] = highs[axis]
            da, db = float(n @ (a - p)), float(n @ (b - p))
            candidates = [
                v for v, distance in ((a, da), (b, db)) if abs(distance) <= 1e-12
            ]
            if da * db < 0:
                candidates.append(a + da / (da - db) * (b - a))
            for q in candidates:
                if not any(np.linalg.norm(q - old) <= 1e-12 for old in found):
                    found.append(q)
    if len(found) < 3:
        return np.empty((0, 3))
    points = np.array(found)
    center = points.mean(axis=0)
    u = points[0] - center
    u /= np.linalg.norm(u)
    v = np.cross(n / np.linalg.norm(n), u)
    order = np.argsort(np.arctan2((points - center) @ v, (points - center) @ u))
    points = points[order]
    return np.vstack((points, points[0]))


class PlanePlot(_CurvePlot):
    """Draw the closed section of a data plane inside the current box.

    Parameters
    ----------
    system, point, normal
        Owning system, data point and normal, with bound input support.
    x, y, z
        Alternative axis-aligned section (exactly one).
    **style
        Artist style and legend label.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        point: object = None,
        normal: object = None,
        *,
        x: object = None,
        y: object = None,
        z: object = None,
        **style: object,
    ) -> None:
        aligned = [(i, value) for i, value in enumerate((x, y, z)) if value is not None]
        if (
            len(aligned) > 1
            or (aligned and (point is not None or normal is not None))
            or (not aligned and point is None and normal is None)
        ):
            raise ValueError("plane requires exactly one form")
        self._input_name = "point"
        if aligned:
            index, value = aligned[0]
            self._input_name = "xyz"[index]
            entries: list[object] = [0, 0, 0]
            entries[index] = value
            point = entries
            normal = np.eye(3)[index]
        else:
            if point is None:
                raise ValueError("point is required")
            if normal is None:
                raise ValueError("normal is required")
            if any(not isinstance(a._scale, LinearScale) for a in system._ranges):
                raise ValueError("normal requires linear axes")
        inputs = {
            **_inputs(_data_point(point, "point"), "point", system),
            **_inputs(_data_point(normal, "normal"), "normal", system),
        }
        self._point = np.zeros(3)
        self._normal = np.zeros(3)

        def derive(binding: _Binding) -> None:
            self._point, self._normal = (
                _read(binding, "point"),
                _read(binding, "normal"),
            )
            if np.linalg.norm(self._normal) == 0:
                if binding.version == 0:
                    raise ValueError("normal must be nonzero")
                binding.parts["polygon"] = np.empty((0, 3))
                return
            polygon = _polygon(system, self._point, self._normal)
            if not len(polygon) and binding.version == 0:
                raise ValueError(f"{self._input_name} plane misses the box")
            binding.parts["polygon"] = binding.local(polygon)

        self._binding = _Binding(system, derive, inputs)
        self._binding_seen = -1
        style.setdefault("fill_opacity", 0.25)
        style.setdefault("stroke_width", 1)
        super().__init__(
            ArraySource(np.empty((0, 3)), dim=3),
            system,
            use_smoothing=False,
            **cast(_ArtistOptions, style),
        )
        system.add(self)

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            _ensure_binding(self._binding)
            if self._binding_seen != self._binding.version:
                self._dirty = True
        super()._ensure()

    def _rebuild(self) -> None:
        self._binding.ensure()
        assert self._system is not None
        self._geometry_payload = corners(
            Payload.path(self._binding.parts["polygon"]), self._system.bounds
        )
        self._place(self._frame())
        self._binding_seen = self._binding.version
        self._data_seen = self._system._data_version
        self._dirty = False


def _slab(
    system: mp.ThreeDAxes, a: FloatArray, d: FloatArray, segment: bool
) -> tuple[float, float] | None:
    lower, upper = (0.0, 1.0) if segment else (-np.inf, np.inf)
    for i, axis in enumerate(system._ranges):
        lo, hi = sorted(axis.range.value)
        if abs(d[i]) < 1e-15:
            if not lo <= a[i] <= hi:
                return None
        else:
            t0, t1 = sorted(((lo - a[i]) / d[i], (hi - a[i]) / d[i]))
            lower, upper = max(lower, t0), min(upper, t1)
    return (
        (lower, upper) if lower <= upper and np.isfinite([lower, upper]).all() else None
    )


class AxLinePlot(ParametricPlot):
    """Draw a data line or segment cut to the current box.

    Parameters
    ----------
    system, xyz1, xyz2, direction
        Owning system and bound data points or direction.
    segment
        Restrict the line to the interval between the two points.
    **style
        Artist style and legend label.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        xyz1: object,
        xyz2: object = None,
        *,
        direction: object = None,
        segment: bool = False,
        _derive: Callable[[], tuple[FloatArray, FloatArray] | None] | None = None,
        **style: object,
    ) -> None:
        if (xyz2 is None) == (direction is None) and _derive is None:
            raise ValueError("direction requires exactly one second input")
        self._segment = segment
        self._a, self._d = np.zeros(3), np.zeros(3)
        self._interval: tuple[float, float] | None = None
        inputs = (
            {}
            if _derive
            else {
                **_inputs(_data_point(xyz1, "xyz1"), "xyz1", system),
                **_inputs(
                    _data_point(
                        direction if xyz2 is None else xyz2,
                        "direction" if xyz2 is None else "xyz2",
                    ),
                    "second",
                    system,
                ),
            }
        )
        if _derive:
            inputs["dependency"] = lambda: _derive()

        def derive(binding: _Binding) -> None:
            if _derive:
                result = binding.parameters["dependency"].value
                if result is None:
                    self._interval = None
                    return
                self._a, self._d = result
            else:
                self._a = _read(binding, "xyz1")
                second = _read(binding, "second")
                self._d = second if xyz2 is None else second - self._a
            if np.linalg.norm(self._d) == 0:
                if binding.version == 0:
                    raise ValueError(
                        "direction must be nonzero"
                        if xyz2 is None
                        else "xyz2 must differ"
                    )
                self._interval = None
            else:
                self._interval = _slab(system, self._a, self._d, segment)

        self._binding = _Binding(system, derive, inputs)
        self._binding_seen = -1
        self._binding.ensure()
        super().__init__(
            lambda t: self._a + t * self._d,
            system,
            use_smoothing=False,
            **cast(_ArtistOptions, style),
        )
        system.add(self)

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        if self._lifecycle.state is lc.State.ATTACHED and not self._alignment_locked:
            _ensure_binding(self._binding)
            if self._binding_seen != self._binding.version:
                self._dirty = True
        super()._ensure()

    def _rebuild(self) -> None:
        self._binding.ensure()
        assert self._system is not None
        if self._interval is None:
            self._geometry_payload = Payload.empty("path", 3)
            self._place(self._frame())
            self._dirty = False
            self._data_seen = self._system._data_version
        elif all(isinstance(a._scale, LinearScale) for a in self._system._ranges):
            points = np.array([self._a + t * self._d for t in self._interval])
            self._geometry_payload = corners(
                Payload.path(self._binding.local(points)), self._system.bounds
            )
            self._place(self._frame())
            self._dirty = False
            self._data_seen = self._system._data_version
        else:
            self.source = ParametricSource(
                lambda t: self._a + t * self._d, self._interval, dim=3
            )
            self._native_samples = None
            self._native_sample_key = None
            super()._rebuild()
        self._binding_seen = self._binding.version


def _drop_group(system: mp.ThreeDAxes, point: object, **options: object) -> HelperGroup:
    from manim_plots.mobjects.helpers import HelperLine, _line_options

    if isinstance(point, Mobject):
        point = point.get_center
    dynamic = callable(point)
    value = point if dynamic else system.p2c(cast(Any, point))
    inputs: dict[str, object] = {"point": value}
    if system.frame_style == "box":
        inputs["panes"] = lambda: system._pane_sides

    def derive(binding: _Binding) -> None:
        raw = binding.parameters["point"].value
        p = system.p2c(raw) if dynamic else np.asarray(raw, dtype=float)
        sides = system._pane_sides
        c = np.array(
            [
                axis.range.value[int(not sides[i])]
                if system.frame_style == "box" and sides
                else system._axis_cross_value(i)
                for i, axis in enumerate(system._ranges)
            ]
        )
        floor = p.copy()
        floor[2] = c[2]
        for i, name in enumerate(("x_line", "y_line", "z_line")):
            start = floor.copy()
            start[i] = c[i]
            end = p if i == 2 else floor
            binding.parts[name] = binding.local([start, end])
        binding.valid = all(
            min(a.range.value) <= p[i] <= max(a.range.value)
            for i, a in enumerate(system._ranges)
        )

    binding = _Binding(system, derive, inputs)
    group = HelperGroup()
    for name in ("x_line", "y_line", "z_line"):
        line = HelperLine(binding, name, **_line_options(**cast(Any, options)))
        setattr(group, name, line)
        group.add(line)
    return group


def _intersection(
    system: mp.ThreeDAxes, a: object, b: object, **style: object
) -> object:
    from manim_plots.mobjects.surfaces import ContourPlot, SurfacePlot, _ContourSource

    if not isinstance(a, PlanePlot) and isinstance(b, PlanePlot):
        a, b = b, a
    if (
        not isinstance(a, PlanePlot)
        or not isinstance(b, (PlanePlot, AxLinePlot, SurfacePlot))
        or a._system is not system
        or b._system is not system
    ):
        raise TypeError(
            f"intersection does not support {type(a).__name__} and {type(b).__name__}"
        )
    plane = a
    if isinstance(b, PlanePlot):
        other = b

        def common() -> tuple[FloatArray, FloatArray] | None:
            _ensure_binding(plane._binding)
            _ensure_binding(other._binding)
            d = np.cross(plane._normal, other._normal)
            if np.linalg.norm(d) < 1e-12:
                return None
            p = np.linalg.solve(
                np.array([plane._normal, other._normal, d]),
                [plane._normal @ plane._point, other._normal @ other._point, 0],
            )
            return p, d

        if common() is None:
            raise ValueError("intersection requires nonparallel planes")
        result_line = AxLinePlot(system, None, _derive=common, **cast(Any, style))
        if result_line._interval is None:
            raise ValueError("intersection misses the box")
        return result_line
    if isinstance(b, AxLinePlot):
        line = b

        def crossing() -> FloatArray:
            _ensure_binding(plane._binding)
            _ensure_binding(line._binding)
            denominator = float(plane._normal @ line._d)
            if abs(denominator) < 1e-12:
                return np.full(3, np.nan)
            t = float(plane._normal @ (plane._point - line._a) / denominator)
            if line._segment and not 0 <= t <= 1:
                return np.full(3, np.nan)
            return line._a + t * line._d

        plane._binding.ensure()
        line._binding.ensure()
        if abs(float(plane._normal @ line._d)) < 1e-12:
            raise ValueError("intersection requires a nonparallel line and plane")
        binding = _Binding(system, lambda binding: None, {"point": crossing})
        result = ScatterPlot(
            [_marker_point(system, crossing())[0]], system, **cast(Any, style)
        )
        result.submobjects = [
            _IntersectionMarker(result._marker_template, result.source, system, binding)
        ]
        system.add(result)
        return result
    surface = b

    def values(points: FloatArray) -> FloatArray:
        _ensure_binding(plane._binding)
        return (points - plane._point) @ plane._normal

    from manim_plots.mobjects.artists import _cycle_style

    _cycle_style(system, cast(_VMStyle, style))
    contour = ContourPlot(surface, [0.0], **cast(Any, style))
    cut = contour._lines[0.0]
    source = cast(_ContourSource, cut.source)
    source.value_function = values
    cut.parameters = {**cut.parameters, **plane._binding.parameters}
    cut._dirty = True
    cut._ensure()
    if not cut.has_points():
        raise ValueError("intersection plane misses surface")
    return contour


class _IntersectionMarker(_MarkerLeaf):
    _intersection_binding: _Binding
    _intersection_seen: int

    def __init__(
        self,
        native: Mobject,
        source: ArraySource,
        system: mp.ThreeDAxes,
        binding: _Binding,
    ) -> None:
        self._intersection_binding = binding
        self._intersection_seen = -1
        super().__init__(native, source, 0, system)

    def _poll(self) -> None:
        self._intersection_binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._intersection_binding.needs_sync(moving)

    def _ensure(self) -> None:
        if not hasattr(self, "_intersection_binding"):
            super()._ensure()
            return
        binding = self._intersection_binding
        _ensure_binding(binding)
        if self._intersection_seen != binding.version:
            point = np.asarray(binding.parameters["point"].value, dtype=float)
            point, binding.valid = _marker_point(binding.system, point)
            self.source = ArraySource([point], dim=3, kind="points")
            self._dirty = True
            self._intersection_seen = binding.version
        super()._ensure()

    def _rebuild(self) -> None:
        super()._rebuild()
        if not self._intersection_binding.valid and self._visible:
            self._opacities = (
                self.get_fill_opacity(),
                self.get_stroke_opacity(),
                self.get_stroke_opacity(background=True),
            )
            self.set_fill(opacity=0, family=False)
            self.set_stroke(opacity=0, family=False)
            self.set_stroke(opacity=0, background=True, family=False)
            self._visible = False
