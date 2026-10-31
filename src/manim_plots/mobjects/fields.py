"""Data-space fields, bound field artists and Runge-Kutta advection."""

from __future__ import annotations

import copy
import inspect
import warnings
from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import Any, Self, cast

import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    Arrow,
    Arrow3D,
    Create,
    Line3D,
    Mobject,
    Scene,
    ShowPassingFlash,
    Transform,
    Vector,
    VGroup,
    VMobject,
    linear,
)
from manim.mobject.vector_field import DEFAULT_SCALAR_FIELD_COLORS
from manim.utils.color import ManimColor, ParsableManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray, ManimPlotsWarning
from manim_plots.core import lifecycle as lc
from manim_plots.core.coordinates import (
    cartesian_to_cylindrical,
    cartesian_to_spherical,
)
from manim_plots.core.nodes import CompiledMap
from manim_plots.core.params import Parameter
from manim_plots.core.payload import Payload
from manim_plots.core.shape import (
    _clip_with_parameters,
    corners,
    marching_squares,
    smooth,
)
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.sources import Bounds, FieldSource, rk4_step
from manim_plots.mobjects.artists import (
    _clip_axes,
    _clip_box,
    _CurvePlot,
    _parameterize,
    _ParameterizedFunction,
    _unclipped_box,
    _validate_clip,
)
from manim_plots.mobjects.helpers import (
    HelperGroup,
    _Binding,
    _HelperShape,
    _number,
)
from manim_plots.mobjects.leaves import (
    _ClipInput,
    _reported_updaters,
    _synchronise,
)


def _positive(value: float, name: str, *, zero: bool = False) -> float:
    value = _number(value, name)
    if value < 0 or (value == 0 and not zero):
        raise ValueError(f"{name} must be {'nonnegative' if zero else 'positive'}")
    return value


def _count(value: int, name: str, *, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _facing_basis(
    system: mp.CartesianAxes, unit: FloatArray, previous: FloatArray | None
) -> tuple[FloatArray, FloatArray]:
    angles = cast(Any, system)._camera_angles
    phi, theta = angles[:2] if angles else (0.0, -np.pi / 2)
    view = np.array(
        [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
    )
    normal = view - (unit @ view)[:, None] * unit
    size = np.linalg.norm(normal, axis=1)
    if previous is None or previous.shape != normal.shape:
        fallback = np.eye(3)[np.argmin(np.abs(unit), axis=1)]
        previous = fallback - np.sum(fallback * unit, axis=1)[:, None] * unit
        previous /= np.maximum(np.linalg.norm(previous, axis=1)[:, None], 1e-12)
    normal = np.divide(
        normal, size[:, None], out=previous.copy(), where=size[:, None] >= 1e-9
    )
    return np.cross(normal, unit), normal


class _FieldBinding(_Binding):
    _steps_seen: tuple[float, ...] = ()

    def ensure(self) -> None:
        steps = self.system._field_steps
        if steps != self._steps_seen:
            self._seen = None
            self._steps_seen = steps
        super().ensure()


class _FieldPart(_HelperShape):
    tip: VMobject

    def __init__(self, binding: _Binding, part: str, template: VMobject) -> None:
        self._styling = True
        self._style_version = 0
        self._explicit_fill = self._explicit_stroke = self._explicit_width = False
        self._default: VMobject | None = template
        self._start: FloatArray | None = None
        super().__init__(binding, part, template)
        self.remove_updater(_synchronise)
        self._styling = False
        self._explicit_fill = self._explicit_stroke = self._explicit_width = False
        self._style_version = 0

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        # A line's animation snapshot must not copy its entire field owner.
        memo.setdefault(id(self._binding), self._binding)
        return super().__deepcopy__(memo)

    def set_clip(self, value: _ClipInput) -> Self:
        """Set clipping for this part and its arrow tip.

        Parameters
        ----------
        value
            Viewport policy or per-axis scene margins, as for other artists.
        """
        super().set_clip(value)
        tip = self.__dict__.get("tip")
        if isinstance(tip, _FieldPart):
            tip.set_clip(value)
        return self

    def set_fill(
        self,
        color: ParsableManimColor | None = None,
        opacity: float | None = None,
        family: bool = True,
    ) -> Self:
        """Set persistent fill style.

        Parameters
        ----------
        color, opacity, family
            Manim fill and propagation options.
        """
        if not self._styling:
            self._style_version += 1
            self._explicit_fill |= color is not None
        return super().set_fill(color, opacity, family)

    def set_stroke(
        self,
        color: ParsableManimColor | None = None,
        width: float | None = None,
        opacity: float | None = None,
        background: bool = False,
        family: bool = True,
    ) -> Self:
        """Set persistent stroke style.

        Parameters
        ----------
        color, width, opacity, background, family
            Manim stroke and propagation options.
        """
        if not self._styling:
            self._style_version += 1
        if not self._styling and not background:
            self._explicit_stroke |= color is not None
            self._explicit_width |= width is not None
        return super().set_stroke(
            cast(ParsableManimColor, color), width, opacity, background, family
        )

    def _rebuild(self) -> None:
        binding = self._binding
        binding.ensure()
        local = binding.parts.get(self._part, np.empty((0, 3)))
        bounds = _clip_box(binding.system, self._clip)
        axes = _clip_axes(self._clip, len(binding.system._ranges))
        if self._start is not None:
            inside = all(
                axis is False
                or bounds.lower[i] - 1e-12 <= self._start[i] <= bounds.upper[i] + 1e-12
                for i, axis in enumerate(axes)
            )
            if not inside:
                local = np.empty((0, 3))
        payload = Payload.path(local)
        if self._start is None and len(local) and any(a is not False for a in axes):
            if any(a is False for a in axes):
                bounds = _unclipped_box(bounds, axes, local)
            payload = clip_path(payload, bounds)
        self._geometry_payload = payload
        self._place(self._frame())
        self._data_seen = binding.system._data_version
        self._binding_seen = binding.version
        self._dirty = False
        default = self._default
        if default is not None:
            self._styling = True
            try:
                if not self._explicit_fill:
                    self.set_fill(default.get_fill_color(), family=False)
                if not self._explicit_stroke:
                    self.set_stroke(default.get_stroke_color(), family=False)
                if not self._explicit_width:
                    self.set_stroke(width=default.get_stroke_width(), family=False)
            finally:
                self._styling = False


class _Field(VGroup):
    def __init__(
        self,
        func: Callable[..., Any],
        system: mp.CartesianAxes,
        color: ParsableManimColor | None,
        color_scheme: Callable[[FloatArray], float] | None,
        min_color_scheme_value: float,
        max_color_scheme_value: float,
        colors: Sequence[ParsableManimColor],
        x_range: Sequence[float] | None,
        y_range: Sequence[float] | None,
        use_vectorized: bool,
        kwargs: dict[str, object],
    ) -> None:
        func, parameters = _parameterize(func, kwargs)
        self._dimension: int = len(system._ranges)
        self._coords = kwargs.pop("coords", None)
        if self._coords not in (None, "spherical", "cylindrical"):
            raise ValueError("coords must be spherical or cylindrical")
        z_range = kwargs.pop("z_range", None)
        self._three_dimensions = kwargs.pop("three_dimensions", True)
        if self._dimension == 3 and not self._three_dimensions:
            z_range = (0, 0, 1)
        self.func, self.system = func, system
        self._system = system
        self._vectorized = use_vectorized
        self.source = FieldSource(
            func,
            x_range=x_range,
            y_range=y_range,
            z_range=(
                cast(Sequence[float], z_range)
                if z_range is not None
                else (*system.get_axis(2).range.value, 1)
            )
            if self._dimension == 3
            else None,
            use_vectorized=use_vectorized,
        )
        self._ranges: tuple[tuple[float, ...] | None, ...] = (
            self.source.x_range,
            self.source.y_range,
        )
        if self._dimension == 3:
            self._ranges += (None if z_range is None else self.source.z_range,)
        self._binding = _FieldBinding(system, self._derive, {})
        self._binding.parameters = parameters
        self.parameters = parameters
        self._single_color = None if color is None else ManimColor(color)
        self._norm_scheme = color_scheme is None
        self._scheme = color_scheme or (lambda v: float(np.linalg.norm(v)))
        self._minimum = _number(min_color_scheme_value, "min_color_scheme_value")
        self._maximum = _number(max_color_scheme_value, "max_color_scheme_value")
        if self._maximum <= self._minimum:
            raise ValueError(
                "max_color_scheme_value must exceed min_color_scheme_value"
            )
        if not colors:
            raise ValueError("colors must not be empty")
        self._colors = [ManimColor(c).to_rgb() for c in colors]
        self._parts: list[_FieldPart] = []
        self._movement: Callable[[Mobject, float], None] | None = None
        self._clip = _validate_clip(kwargs.pop("clip", True))
        _clip_box(system, self._clip)
        self._warned = False
        super().__init__(**cast(dict[str, Any], kwargs))
        self.add_updater(_synchronise)

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Report synchronization only when the system or bound parameters move."""
        return _reported_updaters(self._updaters, getattr(self, "system", None))

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._updaters = value

    @property
    def color_mapping(self) -> mp.ColorMapping:
        """Return the field's linear magnitude-to-colour mapping."""
        from manim_plots.core.scales import LinearScale
        from manim_plots.mobjects.colormaps import Colormap, ColorMapping

        cached = self.__dict__.get("_field_color_mapping")
        if not isinstance(cached, ColorMapping):
            cached = ColorMapping(
                Colormap(self._colors), self._minimum, self._maximum, LinearScale()
            )
            self._field_color_mapping = cached
        return cached

    def _color(self, vector: FloatArray) -> ManimColor:
        if self._single_color is not None:
            return self._single_color
        vector3 = np.append(vector, 0) if self._dimension == 2 else vector
        value = self._scheme(vector3)
        alpha = float(
            np.clip((value - self._minimum) / (self._maximum - self._minimum), 0, 1)
        )
        scaled = alpha * (len(self._colors) - 1)
        index = int(scaled)
        fraction = scaled - index
        rgb = (1 - fraction) * self._colors[index] + fraction * self._colors[
            min(index + 1, len(self._colors) - 1)
        ]
        return ManimColor(rgb)

    def _grid(self) -> Payload:
        ranges = []
        for explicit, axis in zip(
            self._ranges,
            tuple(self.system.get_axis(i) for i in range(self._dimension)),
            strict=True,
        ):
            lo, hi = sorted(axis.range.value) if explicit is None else explicit[:2]
            step = (
                explicit[2]
                if explicit is not None and len(explicit) == 3
                # Half the system's step: Manim's 0.5 on its default plane.
                else self.system._field_steps[axis.index]
                * (2 if self._dimension == 3 else 0.5)
            )
            ranges.append((float(lo), float(hi), float(step)))
        self.source = FieldSource(
            self._coordinate_velocity if self._coords else self.func,
            x_range=ranges[0],
            y_range=ranges[1],
            z_range=ranges[2] if self._dimension == 3 else None,
            use_vectorized=self._vectorized,
        )
        payload = self.source.sample(self.system._mapping(), self.system.bounds)
        assert isinstance(payload.topology, tuple)
        rows, cols = payload.topology[:2]
        self._steps = np.array([r[2] for r in ranges])
        # Payloads are row-major; Manim's public part order is x outer, y inner.
        self._order = np.arange(len(payload.coords))
        if self._dimension == 2:
            self._order = self._order.reshape(rows, cols).T.ravel()
        if payload.valid is not None and not self._warned:
            warnings.warn(
                "field contains invalid samples; they are not drawn",
                ManimPlotsWarning,
                stacklevel=4,
            )
            self._warned = True
        return payload

    def _derive(self, binding: _Binding) -> None:
        raise NotImplementedError

    def _resize(self, templates: Sequence[VMobject]) -> None:
        binding = self._binding
        for index, template in enumerate(templates):
            if index >= len(self._parts):
                part = _FieldPart(binding, str(index), template)
                part.set_clip(cast(Any, self._clip))
                self._parts.append(part)
                self.add(part)
            self._parts[index]._default = template
        # Keep retired leaves empty for a renderer that captured the old family.
        for index in range(len(templates), len(self._parts)):
            binding.parts[str(index)] = np.empty((0, 3))
        self._active_count = len(templates)

    def update(self, dt: float = 0, recursive: bool = True) -> Self:
        """Synchronize changed data before updating field children.

        Parameters
        ----------
        dt, recursive
            Manim's elapsed time and child-update switch.
        """
        if self.updating_suspended:
            return self
        self.system._poll()
        self._binding.poll()
        self._binding.ensure()
        return super().update(dt, recursive)

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result.system = memo.get(id(self.system), self.system)
        result._system = result.system
        result._binding = copy.deepcopy(self._binding, memo)
        result.parameters = result._binding.parameters
        function = self.func
        result.func = (
            _ParameterizedFunction(
                function.function, function.signature, result.parameters
            )
            if isinstance(function, _ParameterizedFunction)
            else function
        )
        result.source = FieldSource(
            result.func,
            x_range=self.source.x_range,
            y_range=self.source.y_range,
            z_range=self.source.z_range,
            use_vectorized=self._vectorized,
        )
        for key, value in self.__dict__.items():
            if key not in {
                "system",
                "_system",
                "_binding",
                "parameters",
                "func",
                "source",
            }:
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result

    def set_parameters(self, **values: object) -> Self:
        """Set named field-function parameters.

        Parameters
        ----------
        **values
            Values for declared arguments after the point argument.
        """
        for name in values:
            if name not in self.parameters:
                raise ValueError(f"unknown function parameter {name!r}")
        for name, value in values.items():
            self.parameters[name].value = value
        self._binding.ensure()
        return self

    def _coordinate_velocity(self, points: FloatArray) -> FloatArray:
        points = np.atleast_2d(points)
        spherical = self._coords == "spherical"
        converted = (cartesian_to_spherical if spherical else cartesian_to_cylindrical)(
            points
        )
        converted[(points[:, :2] == 0).all(axis=1), 2 if spherical else 1] = 0
        values = np.asarray(
            self.func(converted) if self._vectorized else self.func(converted[0]),
            dtype=float,
        )
        if not self._vectorized:
            values = values[None, :]
        if values.shape != converted.shape:
            raise ValueError("func must return three components for coords")
        phi = converted[:, 2 if spherical else 1]
        c, t = np.cos(phi), np.sin(phi)
        radial = np.column_stack((c, t, np.zeros(len(points))))
        azimuth = np.column_stack((-t, c, np.zeros(len(points))))
        vertical = np.tile([0.0, 0.0, 1.0], (len(points), 1))
        if spherical:
            theta = converted[:, 1]
            first = np.sin(theta)[:, None] * radial + np.cos(theta)[:, None] * vertical
            second = np.cos(theta)[:, None] * radial - np.sin(theta)[:, None] * vertical
            basis = np.stack((first, second, azimuth), axis=1)
        else:
            basis = np.stack((radial, azimuth, vertical), axis=1)
        result = np.einsum("ni,nij->nj", values, basis)
        return cast(FloatArray, result if self._vectorized else result[0])

    def _velocity(self, points: FloatArray) -> FloatArray:
        values = self.source.at(points)
        if values.ndim == 1 and not np.isfinite(values).any():
            return np.full_like(points, np.nan)
        if values.shape != points.shape:
            raise ValueError("func must return vectors for a vector field")
        return values

    def nudge(
        self, mob: Mobject, dt: float = 1, substeps: int = 1, pointwise: bool = False
    ) -> Self:
        """Advect a mobject by RK4 in data coordinates.

        Parameters
        ----------
        mob
            Mobject to move, including all its children in pointwise mode.
        dt, substeps
            Finite signed field time and positive number of RK4 steps.
        pointwise
            Move every control point instead of translating the centre.

        Returns
        -------
        Self
            This field.
        """
        dt = _number(dt, "dt")
        _count(substeps, "substeps")
        system = self.system
        system._poll()
        self._binding.poll()

        def move(scene: FloatArray) -> FloatArray:
            data = system.p2c(scene)[:, : self._dimension]
            for _ in range(substeps):
                data = rk4_step(self._velocity, data, dt / substeps)
            valid = system._data.valid(data)
            result = scene.copy()
            if valid.any():
                result[valid] = system.c2p(data[valid])
            return result

        if pointwise:
            mob.apply_points_function_about_point(move, about_point=np.zeros(3))
        else:
            centre = np.asarray(mob.get_center())[None, :]
            mob.shift(move(centre)[0] - centre[0])
        return self

    def nudge_submobjects(
        self, dt: float = 1, substeps: int = 1, pointwise: bool = False
    ) -> Self:
        """Advect each direct submobject along this field.

        Parameters
        ----------
        dt, substeps, pointwise
            Field time, RK4 step count and pointwise mode, as in ``nudge``.
        """
        for mob in self.submobjects:
            self.nudge(mob, dt, substeps, pointwise)
        return self

    def get_nudge_updater(
        self, speed: float = 1, pointwise: bool = False
    ) -> Callable[[Mobject, float], Mobject]:
        """Return a time-based advection updater.

        Parameters
        ----------
        speed, pointwise
            Field time per second and pointwise movement mode.

        Returns
        -------
        Callable
            Updater accepting a mobject and elapsed seconds.
        """
        speed = _number(speed, "speed")

        def updater(mob: Mobject, dt: float) -> Mobject:
            self.nudge(mob, dt * speed, pointwise=pointwise)
            return mob

        return updater

    def start_submobject_movement(
        self, speed: float = 1, pointwise: bool = False
    ) -> Self:
        """Continuously advect direct children, replacing any previous updater.

        Parameters
        ----------
        speed, pointwise
            Field time per second and pointwise movement mode.
        """
        self.stop_submobject_movement()
        speed = _number(speed, "speed")

        def updater(mob: Mobject, dt: float) -> None:
            self.nudge_submobjects(dt * speed, pointwise=pointwise)

        self._movement = updater
        self.add_updater(updater)
        return self

    def stop_submobject_movement(self) -> Self:
        """Remove the updater installed by ``start_submobject_movement``.

        Returns
        -------
        Self
            This field.
        """
        if self._movement is not None:
            self.remove_updater(self._movement)
            self._movement = None
        return self


def _arrow_length(norm: float) -> float:
    return float(0.45 / (1 + np.exp(-norm)))


class ArrowVectorField(_Field):
    """Draw individually styleable arrows of a data-coordinate vector field.

    Parameters
    ----------
    func, system
        Manim-convention point function and owning coordinate system.
    color, color_scheme
        Uniform colour, or a vector-to-scalar colour rule (default: data norm).
    min_color_scheme_value, max_color_scheme_value, colors
        Clamped scalar interval and interpolated palette, as in Manim.
    x_range, y_range
        Inclusive bounds and steps; defaults follow system ranges and tick steps.
    length_func
        Scene length as a function of data norm; default ``0.45 * sigmoid(norm)``.
    opacity, vector_config
        Arrow opacity and native Vector keywords. ``center=True`` centres arrows.
    use_vectorized
        Evaluate ``func`` over an ``(n, 3)`` batch.
    **kwargs
        VGroup style, function parameters or bindings, and per-axis ``clip``.
        On 3D systems, ``z_range`` sets the third grid range,
        ``three_dimensions=False`` samples z=0, ``arrow="3d"`` uses Arrow3D,
        and ``coords`` selects spherical or cylindrical local components.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        system: mp.CartesianAxes,
        color: ParsableManimColor | None = None,
        color_scheme: Callable[[FloatArray], float] | None = None,
        min_color_scheme_value: float = 0,
        max_color_scheme_value: float = 2,
        colors: Sequence[ParsableManimColor] = DEFAULT_SCALAR_FIELD_COLORS,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        length_func: Callable[[float], float] = _arrow_length,
        opacity: float = 1.0,
        vector_config: dict[str, Any] | None = None,
        use_vectorized: bool = False,
        **kwargs: object,
    ) -> None:
        self._arrow_kind = kwargs.pop("arrow", "flat")
        if self._arrow_kind not in ("flat", "3d"):
            raise ValueError("arrow must be flat or 3d")
        self._solid_arrows: list[VMobject] = []
        self._solid_colors: list[ManimColor] = []
        self._normals: FloatArray | None = None
        self._flat_geometry: tuple[FloatArray, FloatArray, FloatArray] | None = None
        self.length_func, self.opacity = length_func, opacity
        self.vector_config = dict(vector_config or {})
        self._centred = self.vector_config.pop("center", False)
        self._tips: list[_FieldPart] = []
        super().__init__(
            func,
            system,
            color,
            color_scheme,
            min_color_scheme_value,
            max_color_scheme_value,
            colors,
            x_range,
            y_range,
            use_vectorized,
            kwargs,
        )
        if self._arrow_kind == "3d":
            self._binding.ensure()
            return
        self._arrow_template = Vector(
            (1.0, 0.0, 0.0), **(self.vector_config | {"buff": 0})
        )
        self._arrow_template.set_opacity(opacity)
        nominal = min(
            self._arrow_template.tip_length,
            self._arrow_template.max_tip_length_to_length_ratio,
        )
        endpoint = self._arrow_template.tip.tip_point
        self._tip_unit = (
            (self._arrow_template.tip.points - endpoint) / nominal
            if nominal
            else np.zeros_like(self._arrow_template.tip.points)
        )
        self._shaft_inset = (
            (endpoint - self._arrow_template.points[-1]) / nominal
            if nominal
            else np.zeros(3)
        )
        self._binding.ensure()
        if self._dimension == 3 and self._arrow_kind == "flat":
            cast(Any, system)._register_field_view(self)

    def _turn(self) -> None:
        if self._arrow_kind != "flat":
            return
        binding = self._binding
        version = binding.version
        binding.ensure()
        if binding.version != version or self._flat_geometry is None:
            return
        origins, unit, coordinates = self._flat_geometry
        width, self._normals = _facing_basis(self.system, unit, self._normals)
        basis = np.stack((unit, width, np.cross(unit, width)), axis=1)
        scene = origins[:, None] + np.einsum("npj,njk->npk", coordinates, basis)
        local = self.system.frame.mapping.inverse(scene.reshape(-1, 3)).reshape(
            scene.shape
        )
        for i in range(self._active_count):
            for part, points, placed in (
                (self._parts[i], local[i, :4], scene[i, :4]),
                (self._tips[i], local[i, 4:], scene[i, 4:]),
            ):
                visible = len(binding.parts[part._part]) > 0
                self._publish_arrow(
                    part,
                    points if visible else np.empty((0, 3)),
                    placed if visible else np.empty((0, 3)),
                )
        binding.version += 1

    @property
    def arrows(self) -> list[VMobject]:
        """Return current arrows in grid order, x outer and y inner."""
        self._binding.ensure()
        if self._arrow_kind == "3d":
            return self._solid_arrows[: self._active_count]
        return list(self._parts[: self._active_count])

    def _derive(self, binding: _Binding) -> None:
        payload = self._grid()
        assert payload.values is not None
        if payload.values.ndim != 2:
            raise ValueError("func must return vectors for ArrowVectorField")
        coords, vectors = payload.coords[self._order], payload.values[self._order]
        system = self.system
        mapping, frame = system._data, system.frame.mapping
        starts = mapping.forward(coords)
        scene_starts = frame.forward(starts)
        delta = 1e-6 * vectors if self._dimension == 3 else vectors
        directions = frame.forward(mapping.forward(coords + delta)) - scene_starts
        norms = np.linalg.norm(vectors, axis=1)
        valid = (
            mapping.valid(coords)
            & np.isfinite(directions).all(axis=1)
            & np.isfinite(norms)
        )
        safe_norms = np.where(valid, norms, 0)
        lengths = (
            0.45 / (1 + np.exp(-safe_norms))
            if self.length_func is _arrow_length
            else np.array(
                [
                    _positive(
                        self.length_func(float(n)), "length_func output", zero=True
                    )
                    for n in safe_norms
                ]
            )
        )
        magnitude = np.linalg.norm(directions, axis=1)
        unit = np.divide(
            directions,
            magnitude[:, None],
            out=np.zeros_like(directions),
            where=(valid & (magnitude > 0))[:, None],
        )
        lengths = np.where(magnitude > 0, lengths, 0)
        if self._arrow_kind == "3d":
            visible = []
            for i, (point, direction, length, vector) in enumerate(
                zip(scene_starts, unit, lengths, vectors, strict=True)
            ):
                end = point + length * direction
                if i == len(self._solid_arrows):
                    arrow: VMobject = self._solid_arrow(point, end, float(length))
                    arrow.set_color(self._color(vector)).set_opacity(self.opacity)
                    self._solid_arrows.append(arrow)
                    self._solid_colors.append(self._color(vector))
                else:
                    arrow = self._solid_arrows[i]
                    color = self._color(vector)
                    if arrow.get_color() == self._solid_colors[i]:
                        arrow.set_color(color)
                    self._solid_colors[i] = color
                    if not np.array_equal(
                        arrow.get_start(), point
                    ) or not np.array_equal(arrow.get_end(), end):
                        replacement = self._solid_arrow(
                            point, end, float(length)
                        ).match_style(arrow)
                        arrow.become(replacement)
                        cast(Arrow3D, arrow).start = point.copy()
                bounds = _clip_box(system, self._clip)
                if (
                    valid[i]
                    and length > 0
                    and all(
                        axis is False
                        or bounds.lower[j] - 1e-12
                        <= starts[i, j]
                        <= bounds.upper[j] + 1e-12
                        for j, axis in enumerate(
                            _clip_axes(self._clip, self._dimension)
                        )
                    )
                ):
                    visible.append(arrow)
            self.submobjects = visible
            self._active_count = len(coords)
            return
        transverse = np.column_stack((-unit[:, 1], unit[:, 0], np.zeros(len(unit))))
        xy_length = np.linalg.norm(transverse, axis=1)
        transverse = np.divide(
            transverse,
            xy_length[:, None],
            out=np.tile([0.0, -1.0, 0.0], (len(unit), 1)),
            where=xy_length[:, None] > 0,
        )
        if self._dimension == 3:
            transverse, self._normals = _facing_basis(system, unit, self._normals)
        normal = np.cross(unit, transverse)
        basis = np.stack((unit, transverse, normal), axis=1)
        buff = max(0.0, float(self.vector_config.get("buff", 0)))
        trim = np.where(lengths >= 2 * buff, buff, 0)
        span = lengths - 2 * trim
        template = self._arrow_template
        tip_lengths = np.minimum(
            template.tip_length, template.max_tip_length_to_length_ratio * span
        )
        origin = scene_starts - (lengths[:, None] * unit / 2 if self._centred else 0)
        first = origin + trim[:, None] * unit
        ends = origin + (lengths - trim)[:, None] * unit
        tip_points = ends[:, None] + tip_lengths[:, None, None] * np.einsum(
            "pj,njk->npk", self._tip_unit, basis
        )
        shaft_ends = ends - tip_lengths[:, None] * np.einsum(
            "j,njk->nk", self._shaft_inset, basis
        )
        shafts = (
            first[:, None]
            + np.linspace(0, 1, 4)[None, :, None] * (shaft_ends - first)[:, None]
        )
        scene = np.concatenate((shafts, tip_points), axis=1)
        if not valid.all():
            scene[~valid] = frame.forward(np.zeros((1, self._dimension)))[0]
        if self._dimension == 3:
            self._flat_geometry = (
                scene_starts,
                unit,
                np.einsum("npk,njk->npj", scene - scene_starts[:, None], basis),
            )
        local = frame.inverse(scene.reshape(-1, 3)).reshape(scene.shape)
        if self._single_color is not None:
            colors = np.tile(self._single_color.to_rgb(), (len(coords), 1))
        else:
            values = (
                safe_norms
                if self._norm_scheme
                else np.array(
                    [
                        self._scheme(np.append(v, 0) if self._dimension == 2 else v)
                        for v in np.where(valid[:, None], vectors, 0)
                    ]
                )
            )
            scaled = np.clip(
                (values - self._minimum) / (self._maximum - self._minimum), 0, 1
            ) * (len(self._colors) - 1)
            indices = scaled.astype(int)
            palette = np.asarray(self._colors)
            fraction = (scaled - indices)[:, None]
            colors = (1 - fraction) * palette[indices] + fraction * palette[
                np.minimum(indices + 1, len(palette) - 1)
            ]
        widths = np.minimum(
            template.initial_stroke_width,
            template.max_stroke_width_to_length_ratio * span,
        )
        for i in range(len(coords)):
            if i == len(self._parts):
                part = _FieldPart(binding, str(i), template)
                tip = _FieldPart(binding, f"tip/{i}", template.tip)
                self._parts.append(part)
                self._tips.append(tip)
                part.tip = tip
                part.add(tip)
                self.add(part)
                part._clip = tip._clip = cast(Any, self._clip)
            for part, points, placed in (
                (self._parts[i], local[i, :4], scene[i, :4]),
                (self._tips[i], local[i, 4:], scene[i, 4:]),
            ):
                part._default = None
                part._start = starts[i]
                bounds = _clip_box(system, part._clip)
                inside = valid[i] and all(
                    axis is False
                    or bounds.lower[j] - 1e-12
                    <= starts[i, j]
                    <= bounds.upper[j] + 1e-12
                    for j, axis in enumerate(_clip_axes(part._clip, self._dimension))
                )
                self._publish_arrow(
                    part,
                    points if inside else np.empty((0, 3)),
                    placed if inside else np.empty((0, 3)),
                )
                if not part._explicit_fill:
                    part.fill_rgbas[:, :3] = colors[i]
                if not part._explicit_stroke:
                    part.stroke_rgbas[:, :3] = colors[i]
                if part is self._parts[i] and not part._explicit_width:
                    part.stroke_width = float(widths[i])
        for i in range(len(coords), len(self._parts)):
            for part in (self._parts[i], self._tips[i]):
                self._publish_arrow(part, np.empty((0, 3)), np.empty((0, 3)))
        self._active_count = len(coords)

    def _solid_arrow(
        self, start: FloatArray, end: FloatArray, length: float
    ) -> Arrow3D:
        config = self.vector_config.copy()
        height = config.get("height", 0.3)
        if length < 2 * height:
            config["height"] = length / 2
            config["base_radius"] = (
                config.get("base_radius", 0.08) * length / (2 * height)
            )
        return Arrow3D(start, end, **config)

    def _publish_arrow(
        self, part: _FieldPart, local: FloatArray, scene: FloatArray
    ) -> None:
        binding = self._binding
        binding.parts[part._part] = local
        if part._lifecycle.state is not lc.State.ATTACHED or part._alignment_locked:
            return
        segments = (
            np.array([[0, len(local)]], dtype=np.intp)
            if len(local)
            else np.empty((0, 2), dtype=np.intp)
        )
        part._geometry_payload = Payload._trusted("path", local, segments)
        frame = part._frame()
        if (
            not frame.is_affine
            or part._own.nodes
            or part._reversed
            or part._frozen_frame is not None
        ):
            part._place(frame)
        else:
            part._local = local
            if part._cache.shape == scene.shape:
                part._cache[:] = scene
            else:
                part._cache = scene.copy()
            part._render_segments = segments
            part._frame_seen = self.system.frame.version
        part._binding_seen = binding.version + 1
        part._data_seen = self.system._data_version
        part._dirty = False


class _FlashWindow:
    def __init__(self, intervals: FloatArray, times: FloatArray) -> None:
        self.intervals = intervals
        self.times = times
        self.parameters = np.linspace(0, 1, len(times))
        self.clip: object = None
        self.own = 0
        self.style_version = -1

    def parameter(self, value: float) -> float:
        intervals = self.intervals
        count = len(intervals)
        if not count:
            return 0.0
        i = int(np.searchsorted(intervals[:, 1], value, side="right"))
        if i == count:
            return 1.0
        start, stop = intervals[i]
        fraction = min(1.0, max(0.0, (value - start) / (stop - start)))
        return float((i + fraction) / count)


class StreamLines(_Field):
    """Draw clipped, smoothed RK4 trajectories from a seeded data grid.

    Parameters
    ----------
    func, system
        Manim-convention vector function and owning coordinate system.
    color, color_scheme
        Uniform colour, or vector-to-scalar stroke-gradient rule (default: norm).
    min_color_scheme_value, max_color_scheme_value, colors
        Clamped scalar colour interval and palette.
    x_range, y_range
        Inclusive seed ranges and steps; omitted ranges follow the system.
    noise_factor
        Seed perturbation width; None uses half the y step, as in Manim.
    n_repeats
        Number of copies of the seed grid.
    dt, virtual_time
        Positive RK4 step and nonnegative total field time.
    max_anchors_per_line
        Maximum number of smoothed anchors on each trajectory.
    padding
        Number of data steps beyond every viewport side before stopping.
    stroke_width, opacity
        Initial line stroke style.
    use_vectorized
        Evaluate ``func`` over batches of points.
    seed
        Random seed for seed offsets, creation order and flash phases.
    **kwargs
        VGroup style, function parameters or bindings, and per-axis ``clip``.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        system: mp.CartesianAxes,
        color: ParsableManimColor | None = None,
        color_scheme: Callable[[FloatArray], float] | None = None,
        min_color_scheme_value: float = 0,
        max_color_scheme_value: float = 2,
        colors: Sequence[ParsableManimColor] = DEFAULT_SCALAR_FIELD_COLORS,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        noise_factor: float | None = None,
        n_repeats: int = 1,
        dt: float = 0.05,
        virtual_time: float = 3,
        max_anchors_per_line: int = 100,
        padding: float = 3,
        stroke_width: float = 1,
        opacity: float = 1,
        use_vectorized: bool = False,
        *,
        seed: int = 0,
        **kwargs: object,
    ) -> None:
        self._line_kind = kwargs.pop("line", "flat")
        if self._line_kind not in ("flat", "3d"):
            raise ValueError("line must be flat or 3d")
        self._solid_lines: list[VMobject] = []
        self._solid_line_colors: list[tuple[FloatArray, FloatArray]] = []
        self.seed = _count(seed, "seed", minimum=0)
        self.noise_factor = noise_factor
        if noise_factor is not None:
            _positive(noise_factor, "noise_factor", zero=True)
        self.n_repeats = _count(n_repeats, "n_repeats")
        self.dt = _positive(dt, "dt")
        self.virtual_time = _positive(virtual_time, "virtual_time", zero=True)
        self.max_anchors_per_line = _count(
            max_anchors_per_line, "max_anchors_per_line", minimum=2
        )
        self.padding = _positive(padding, "padding", zero=True)
        self.stroke_width, self.opacity = stroke_width, opacity
        self._seeds: FloatArray | None = None
        self._traces: list[FloatArray] = []
        self._times: list[FloatArray] = []
        self._durations: list[float] = []
        self._anchor_times: list[FloatArray] = []
        self.flow_animation: Callable[[Mobject, float], None] | None = None
        self._flashes: list[ShowPassingFlash] = []
        super().__init__(
            func,
            system,
            color,
            color_scheme,
            min_color_scheme_value,
            max_color_scheme_value,
            colors,
            x_range,
            y_range,
            use_vectorized,
            kwargs,
        )
        self._binding.ensure()

    @property
    def stream_lines(self) -> list[VMobject]:
        """Return independently styleable lines in seed order."""
        self._binding.ensure()
        if self._line_kind == "3d":
            return self._solid_lines[: self._active_count]
        return list(self._parts[: self._active_count])

    def _derive(self, binding: _Binding) -> None:
        payload = self._grid()
        if self._seeds is None:
            seeds = np.tile(payload.coords[self._order], (self.n_repeats, 1))
            noise = (
                self._steps[1] / 2 if self.noise_factor is None else self.noise_factor
            )
            self._seeds = seeds + noise * (
                np.random.default_rng(self.seed).random(seeds.shape) - 0.5
            )
        seeds = self._seeds
        system = self.system
        lower = (
            np.array(
                [min(system.get_axis(i).range.value) for i in range(self._dimension)]
            )
            - self.padding * self._steps
        )
        upper = (
            np.array(
                [max(system.get_axis(i).range.value) for i in range(self._dimension)]
            )
            + self.padding * self._steps
        )
        traces = [[seed.copy()] for seed in seeds]
        times = [[0.0] for _ in seeds]
        positions = seeds.copy()
        active = np.isfinite(self._velocity(positions)).all(axis=1)
        elapsed = 0.0
        while elapsed < self.virtual_time - 1e-12 and active.any():
            step = min(self.dt, self.virtual_time - elapsed)
            indices = np.flatnonzero(active)
            following = rk4_step(self._velocity, positions[indices], step)
            finite = np.isfinite(self._velocity(following)).all(axis=1)
            inside = ((following >= lower) & (following <= upper)).all(axis=1)
            moving = np.any(following != positions[indices], axis=1)
            keep = finite & inside & moving
            active[indices[~keep]] = False
            elapsed += step
            positions[indices[keep]] = following[keep]
            for index in indices[keep]:
                traces[index].append(positions[index].copy())
                times[index].append(elapsed)
        self._traces = [np.array(trace) for trace in traces]
        self._times = [np.array(t) for t in times]
        self._durations = [t[-1] for t in times]
        self._anchor_times = []
        templates = []
        for i, trace in enumerate(self._traces):
            indices = np.unique(
                np.linspace(
                    0, len(trace) - 1, min(len(trace), self.max_anchors_per_line)
                ).astype(int)
            )
            anchors = trace[indices]
            self._anchor_times.append(self._times[i][indices])
            local = system._data.apply_payload(Payload.path(anchors))
            if self._line_kind == "3d":
                clipped = (
                    clip_path(
                        corners(local, system.bounds), _clip_box(system, self._clip)
                    )
                    if self._clip is not False
                    else local
                )
                group = VGroup()
                for begin, stop in clipped.segments:
                    points = clipped.coords[begin:stop]
                    pairs = (
                        ((curve[0], curve[-1]) for curve in points.reshape(-1, 4, 3))
                        if self._clip is not False
                        else pairwise(points)
                    )
                    for first, last in pairs:
                        if np.linalg.norm(last - first) < 1e-12:
                            continue
                        endpoints = system.frame.mapping.forward(
                            np.array([first, last])
                        )
                        segment = Line3D(*endpoints)
                        midpoint = system._data.inverse(((first + last) / 2)[None, :])
                        segment.set_color(
                            self._color(self._velocity(midpoint)[0])
                        ).set_opacity(self.opacity)
                        group.add(segment)
                if i == len(self._solid_lines):
                    self._solid_lines.append(group)
                    self._solid_line_colors.append(
                        (group.fill_rgbas.copy(), group.stroke_rgbas.copy())
                    )
                    self.add(group)
                else:
                    old = self._solid_lines[i]
                    fill, stroke = self._solid_line_colors[i]
                    self._solid_line_colors[i] = (
                        group.fill_rgbas.copy(),
                        group.stroke_rgbas.copy(),
                    )
                    if not np.array_equal(old.fill_rgbas, fill) or not np.array_equal(
                        old.stroke_rgbas, stroke
                    ):
                        group.match_style(old)
                    old.submobjects = group.submobjects
                continue
            curves = smooth(local, system.bounds)
            binding.parts[str(i)] = curves.coords
            template = VMobject(
                stroke_width=self.stroke_width, stroke_opacity=self.opacity
            )
            if self._single_color is not None:
                template.set_color(self._single_color)
            else:
                template.set_stroke(
                    cast(
                        ParsableManimColor,
                        [self._color(v) for v in self._velocity(anchors)],
                    )
                )
            templates.append(template)
        if self._line_kind == "3d":
            self._active_count = len(self._traces)
            self.submobjects = self._solid_lines[: self._active_count]
            return
        self._resize(templates)
        for part, template in zip(self._parts, templates, strict=False):
            if not part._explicit_stroke:
                part._styling = True
                part.stroke_rgbas = template.stroke_rgbas.copy()
                part._style_version += 1
                part._styling = False
                # Keep the full along-line gradient when rebuilding geometry.
                part._default = None

    def create(
        self,
        lag_ratio: float | None = None,
        run_time: float | None = None,
        **kwargs: object,
    ) -> AnimationGroup:
        """Create trajectories in deterministic shuffled order.

        Parameters
        ----------
        lag_ratio, run_time
            Per-line lag and duration; defaults are Manim's virtual-time rule.
        **kwargs
            Native Create options.

        Returns
        -------
        AnimationGroup
            Creation animations for every line.
        """
        duration = self.virtual_time if run_time is None else run_time
        lines = self.stream_lines
        lag = duration / 2 / max(1, len(lines)) if lag_ratio is None else lag_ratio
        order = np.random.default_rng(self.seed).permutation(len(lines))
        return _CreateLines(
            self,
            *(
                Create(lines[i], run_time=duration, **cast(dict[str, Any], kwargs))
                for i in order
            ),
            lag_ratio=lag,
        )

    def start_animation(
        self,
        warm_up: bool = True,
        flow_speed: float = 1,
        time_width: float = 0.3,
        rate_func: Callable[[float], float] = linear,
        line_animation_class: type[ShowPassingFlash] = ShowPassingFlash,
        **kwargs: object,
    ) -> Self:
        """Continuously flash lines at their integrated field-time speed.

        Parameters
        ----------
        warm_up
            Stagger initially invisible flashes when True.
        flow_speed, time_width
            Positive field-time speed and visible fraction of each line.
        rate_func, line_animation_class
            Native flash timing and animation class.
        **kwargs
            Additional native flash options.

        Returns
        -------
        Self
            This field with its animation updater installed.
        """
        if self._line_kind == "3d":
            raise NotImplementedError("start_animation is not defined for line=3d")
        if self.flow_animation is not None:
            self.remove_updater(self.flow_animation)
        speed = _positive(flow_speed, "flow_speed")
        self.flow_speed, self.time_width = speed, time_width
        self._flashes = []
        phases = np.random.default_rng(self.seed).random(len(self.stream_lines))
        self._phases = phases * (-self.virtual_time if warm_up else self.virtual_time)
        windows: dict[ShowPassingFlash, _FlashWindow] = {}

        def get_bounds(flash: ShowPassingFlash, alpha: float) -> tuple[float, float]:
            lower, upper = line_animation_class._get_bounds(flash, alpha)
            window = windows[flash]
            return window.parameter(lower), window.parameter(upper)

        # Subclass the selected animation; its other hooks and timing stay native.
        animation_class = cast(
            type[ShowPassingFlash],
            type(
                "FieldPassingFlash",
                (line_animation_class,),
                {"_get_bounds": get_bounds},
            ),
        )

        def prepare(i: int, flash: ShowPassingFlash, *, begin: bool = False) -> None:
            line = self._parts[i]
            line._ensure()
            local = self._binding.parts[str(i)]
            if local.shape[1] == 2:
                local = np.column_stack((local, np.zeros(len(local))))
            payload = Payload.path(local)
            bounds = _clip_box(self.system, line._clip)
            axes = _clip_axes(line._clip, self._dimension)
            if any(a is not False for a in axes) and len(local):
                if any(a is False for a in axes):
                    bounds = _unclipped_box(bounds, axes, local)
                payload, intervals = _clip_with_parameters(payload, bounds)
            else:
                n = len(local) // 4
                intervals = np.column_stack((np.arange(n), np.arange(1, n + 1))) / max(
                    1, n
                )
            points = payload.coords
            if line._own.nodes:
                points = line._own.forward(points)
            placed = line._frame().forward(points)
            window = _FlashWindow(intervals, self._anchor_times[i])
            window.clip, window.own = line._clip, id(line._own)
            window.style_version = line._style_version
            windows[flash] = window
            display = cast(VMobject, flash.mobject)
            display.match_style(line)
            if begin:
                display.set_points(placed)
                flash.begin()
            else:
                cast(VMobject, flash.starting_mobject).set_points(placed)

        for i in range(len(self.stream_lines)):
            flash = animation_class(
                VMobject(),
                run_time=max(self.virtual_time / speed, 1e-9),
                time_width=time_width,
                rate_func=rate_func,
                **kwargs,
            )
            prepare(i, flash, begin=True)
            self._flashes.append(flash)
        self.submobjects = [cast(VMobject, flash.mobject) for flash in self._flashes]
        self._flash_version = self._binding.version
        durations = np.asarray(self._durations)

        def updater(mob: Mobject, dt: float) -> None:
            nonlocal durations
            changed = self._flash_version != self._binding.version
            if changed:
                durations = np.asarray(self._durations)
                self._flash_version = self._binding.version
            self._phases += dt * speed
            np.remainder(
                self._phases,
                durations,
                out=self._phases,
                where=(durations > 0) & (self._phases >= durations),
            )
            for i, flash in enumerate(self._flashes):
                line, window = self._parts[i], windows[flash]
                if changed or window.clip != line._clip or window.own != id(line._own):
                    prepare(i, flash)
                    window = windows[flash]
                elif window.style_version != line._style_version:
                    cast(VMobject, flash.mobject).match_style(line)
                    window.style_version = line._style_version
                phase = self._phases[i]
                progress = float(
                    np.interp(max(0.0, phase), window.times, window.parameters)
                )
                alpha = (
                    (progress + time_width / 2) / (1 + time_width)
                    if phase >= 0
                    else 0.0
                )
                flash.interpolate(alpha)

        self.flow_animation = updater
        self.add_updater(updater)
        updater(self, 0)
        return self

    def end_animation(self) -> AnimationGroup:
        """Finish running flashes and smoothly restore complete trajectories.

        Returns
        -------
        AnimationGroup
            Native creation animations returning the full lines.

        Raises
        ------
        ValueError
            If no flow animation is running.
        """
        if self.flow_animation is None:
            raise ValueError("start_animation must be called before end_animation")
        self.remove_updater(self.flow_animation)
        self.flow_animation = None
        return _EndFlow(self)


class _CreateLines(AnimationGroup):
    def __init__(
        self, field: StreamLines, *animations: Animation, lag_ratio: float
    ) -> None:
        self.field = field
        super().__init__(*animations, lag_ratio=lag_ratio)

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Leave the field itself in the scene, so a later flow animation shows.

        Parameters
        ----------
        scene
            Scene the lines were created in; adding the field takes its lines out.
        """
        super().clean_up_from_scene(scene)
        scene.add(self.field)


class _EndFlow(AnimationGroup):
    def __init__(self, field: StreamLines) -> None:
        self.field = field
        super().__init__(
            *(
                Transform(
                    cast(Mobject, flash.mobject),
                    line,
                    run_time=max(field.virtual_time / field.flow_speed, 1e-9),
                )
                for flash, line in zip(field._flashes, field.stream_lines, strict=True)
            )
        )

    def finish(self) -> None:
        """Restore bound lines after the visible flashes have filled out."""
        super().finish()
        self.field.submobjects = list(self.field._parts)
        self.field._flashes = []


class _VectorGroup(_HelperShape, HelperGroup):
    """Keep the shaft on the group itself, as on a native Arrow."""

    def _ensure(self) -> None:
        if (
            len(self._binding.system._ranges) == 3
            and self._lifecycle.state is lc.State.ATTACHED
            and not self._alignment_locked
        ):
            from manim_plots.mobjects.geometry import _ensure_binding

            _ensure_binding(self._binding)
        super()._ensure()

    def _turn(self) -> None:
        self._binding._seen = None
        self._binding.ensure()


def _get_vector(
    system: mp.CartesianAxes, coords: Sequence[object], **kwargs: object
) -> HelperGroup:
    if len(coords) not in (2, 3):
        raise ValueError("coords must have length 2 or 3")
    if len(system._ranges) == 3 and len(coords) != 3:
        raise ValueError("coords must have length 3")
    template: Arrow | None = None
    previous: FloatArray | None = None

    def derive(binding: _Binding) -> None:
        nonlocal template, previous
        values = [binding.number(name) for name in "xyz"[: len(system._ranges)]]
        origin = system.c2p(*([0.0] * len(system._ranges)))
        endpoint = system.c2p(*values)
        template = Arrow(origin, endpoint, buff=0, **cast(dict[str, Any], kwargs))
        if len(system._ranges) == 3:
            delta = endpoint - origin
            length = np.linalg.norm(delta)
            direction = (delta / length if length else np.array([1.0, 0.0, 0.0]))[
                None, :
            ]
            width, previous = _facing_basis(system, direction, previous)
            flat = Arrow(
                np.zeros(3),
                np.array([length, 0.0, 0.0]),
                buff=0,
                **cast(dict[str, Any], kwargs),
            )
            basis = np.stack((direction[0], width[0], previous[0]))
            template.set_points(origin + flat.points @ basis)
            template.tip.set_points(origin + flat.tip.points @ basis)
        binding.parts["line"] = binding.scene(template.points)
        binding.parts["tip"] = binding.scene(template.tip.points)

    binding = _Binding(
        system, derive, dict(zip("xyz"[: len(system._ranges)], coords, strict=False))
    )
    binding.ensure()
    assert template is not None
    group = _VectorGroup(binding, "line", template)
    group.line = group
    group.tip = _HelperShape(binding, "tip", template.tip)
    group.add(group.tip)
    if len(system._ranges) == 3:
        cast(Any, system)._register_field_view(group)
    return group


class _ImplicitSource:
    def __init__(
        self, func: Callable[..., Any], min_depth: int, max_quads: int
    ) -> None:
        self.field = FieldSource(func)
        self.min_depth, self.max_quads = min_depth, max_quads

    def at(self, t: ArrayLike) -> FloatArray:
        return self.field.at(t)

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        edges = map.inverse(np.array([bounds.lower, bounds.upper]))[:, :2]
        lo, hi = edges.min(axis=0), edges.max(axis=0)
        ratio = (hi[0] - lo[0]) / (hi[1] - lo[1])
        nx = min(self.max_quads, max(1, int(np.sqrt(self.max_quads * ratio))))
        ny = max(1, self.max_quads // nx)
        source = FieldSource(
            self.field.func,
            x_range=(lo[0], hi[0], (hi[0] - lo[0]) / nx),
            y_range=(lo[1], hi[1], (hi[1] - lo[1]) / ny),
        )
        payload = source.sample(map, bounds)
        rows, cols = cast(tuple[int, int], payload.topology)
        r, c = np.mgrid[: rows - 1, : cols - 1]
        a = (r * cols + c).ravel()
        cells = np.column_stack((a, a + 1, a + cols + 1, a + cols))
        for _ in range(self.min_depth):
            assert payload.values is not None
            values = payload.values[cells]
            centres = source.at(payload.coords[cells].mean(axis=1))
            keep = (np.minimum(values.min(axis=1), centres) <= 0) & (
                np.maximum(values.max(axis=1), centres) >= 0
            )
            if payload.valid is not None:
                keep &= payload.valid[cells].all(axis=1)
            quads = payload.coords[cells[keep]]
            if not len(quads):
                return Payload.empty("path", 2)
            a0, b, c0, d = (quads[:, i] for i in range(4))
            ab, bc, cd, da = (a0 + b) / 2, (b + c0) / 2, (c0 + d) / 2, (d + a0) / 2
            centre = (a0 + c0) / 2
            refined = np.array(
                [
                    [a0, ab, centre, da],
                    [ab, b, bc, centre],
                    [centre, bc, c0, cd],
                    [da, centre, cd, d],
                ]
            )
            flat = np.moveaxis(refined, 2, 1).reshape(-1, 2)
            normalized = np.round((flat - lo) / (hi - lo), 13)
            coords, inverse = np.unique(normalized, axis=0, return_inverse=True)
            coords = lo + coords * (hi - lo)
            cells = inverse.reshape(-1, 4)
            values = source.at(coords)
            valid = np.isfinite(values)
            payload = Payload(
                "region",
                coords,
                np.array([[0, len(coords)]]),
                cells,
                None if valid.all() else valid,
                values,
            )
        return marching_squares(payload, bounds)


class _ImplicitPlot(_CurvePlot):
    def __init__(
        self,
        source: _ImplicitSource,
        system: mp.CartesianAxes,
        parameters: dict[str, Parameter[Any]],
        **kwargs: object,
    ) -> None:
        self.parameters = parameters
        super().__init__(source, system, **cast(dict[str, Any], kwargs))

    def set_parameters(self, **values: object) -> Self:
        """Set named implicit-function parameters, also through ``animate``.

        Parameters
        ----------
        **values
            Values of arguments declared after x and y.
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
        source = self.source
        assert isinstance(source, _ImplicitSource)
        function = source.field.func
        if isinstance(function, _ParameterizedFunction):
            result.source = _ImplicitSource(
                _ParameterizedFunction(
                    function.function, function.signature, result.parameters
                ),
                source.min_depth,
                source.max_quads,
            )
        return result


def _implicit_curve(
    system: mp.CartesianAxes,
    func: Callable[..., Any],
    min_depth: int,
    max_quads: int,
    **kwargs: object,
) -> _CurvePlot:
    _count(min_depth, "min_depth", minimum=0)
    _count(max_quads, "max_quads")

    def point_function(point: FloatArray, *args: object, **values: object) -> object:
        return cast(object, func(point[0], point[1], *args, **values))

    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if len(parameters) < 2:
        raise TypeError("func must accept x and y")
    point_function.__dict__["__signature__"] = signature.replace(
        parameters=[parameters[0].replace(name="point"), *parameters[2:]]
    )
    function, bound = _parameterize(point_function, kwargs)
    source = _ImplicitSource(function, min_depth, max_quads)
    curve = _ImplicitPlot(source, system, bound, **kwargs)
    system.add(curve)
    return curve


from manim_plots.animations.fields import Flow as Flow  # noqa: E402
