"""Cartesian polar planes and coupled polar coordinate systems."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from typing import Any, NoReturn, Self, Unpack, cast

import numpy as np
from manim import (
    BLUE_D,
    DL,
    SMALL_BUFF,
    Circle,
    MathTex,
    NumberLine,
    VDict,
    VGroup,
    VMobject,
    config,
)
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.formatters import AngleFormatter, FormatStrFormatter
from manim_plots.core.nodes import Chain, CompiledMap, FunctionNode
from manim_plots.core.payload import Payload
from manim_plots.core.scales import LinearScale, LogScale, Scale
from manim_plots.core.sources import Bounds, ParametricSource, _Disk
from manim_plots.core.ticks import (
    FixedLocator,
    Level,
    Locator,
    MinorCountLocator,
    MultipleLocator,
    Tick,
    round_key,
)
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LinePlot,
    ParametricPlot,
    _parameterize,
)
from manim_plots.mobjects.axis import Axis, TickDirection, _range, _TickConfig
from manim_plots.mobjects.axis_labels import _Parts
from manim_plots.mobjects.leaves import (
    BoundLabel,
    GridLeaf,
    _ArtistOptions,
    _label,
    _NumberOptions,
    _VMStyle,
)
from manim_plots.mobjects.system import CartesianAxes, _scale
from manim_plots.mobjects.themes import Theme, _resolve_theme

_TAU = 2 * np.pi
_UNITS = {"PI radians": 20, "TAU radians": 20, "degrees": 36, "gradians": 40, None: 1}


def _azimuth(units: str | None, direction: str, step: float | None) -> float:
    if units not in _UNITS:
        raise ValueError(
            "azimuth_units must be PI radians, TAU radians, degrees, gradians or None"
        )
    if direction not in ("CW", "CCW"):
        raise ValueError("azimuth_direction must be CW or CCW")
    step = float(_UNITS[units] if step is None else step)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("azimuth_step must be finite and positive")
    return step


def _styles(
    background: dict[str, Any] | None, faded: dict[str, Any] | None, ratio: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(ratio, int) or isinstance(ratio, bool) or ratio < 0:
        raise ValueError("faded_line_ratio must be a nonnegative integer")
    major = {
        "stroke_color": BLUE_D,
        "stroke_width": 2,
        "stroke_opacity": 1,
        **(background or {}),
    }
    minor = (
        faded
        if faded is not None
        else {
            k: v * 0.5 if isinstance(v, (int, float)) else v for k, v in major.items()
        }
    )
    return major, minor


class _GridParts(_Parts[GridLeaf]):
    def at(self, value: float) -> GridLeaf:
        self._axis._system._sync_data()
        return self._parts[round_key(value)]


class _PeriodicParts[T: VMobject](_Parts[T]):
    def at(self, value: float) -> T:
        self._axis._system._sync_data()
        value = round_key(self._axis._part_value(value))
        if self._level is not None:
            return self._parts[value]
        for level in ("major", "minor"):
            if (level, value) in self._parts:
                return self._parts[(level, value)]
        raise KeyError(value)


def _grid(
    system: PolarPlane | PolarAxes,
    radial: Sequence[tuple[float, Level]],
    angular: Sequence[tuple[float, Level]],
) -> None:
    major: list[VMobject] = []
    minor: list[VMobject] = []
    mapping = system.frame.mapping
    for parts, values, circle in (
        (system.spokes, angular, False),
        (system.circles, radial, True),
    ):
        axis = parts._axis
        pool = axis._pool if circle or isinstance(system, PolarAxes) else None
        active = {(level, round_key(value)) for value, level in values}
        if pool is not None:
            values = [(item.value, item.level) for item in pool.items]
        tick_keys = {
            (item.level, round_key(item.value)): item.key for item in axis._items
        }
        current: dict[object, GridLeaf] = {}
        retained: dict[object, GridLeaf] = {}
        for value, level in values:
            if circle:
                if isinstance(system, PolarPlane) and value <= 0:
                    continue
                local = system._circle(value)
                if (
                    not len(local)
                    or np.max(np.linalg.norm(local[:, :2], axis=1)) < 1e-12
                ):
                    continue
            else:
                local = system._spoke(value)
            key = round_key(value)
            grid_key = (level, tick_keys.get((level, key), axis._part_key(value)))
            leaf = parts._parts.get(key)
            if leaf is None:
                leaf = axis._grid_leaves.get(grid_key)
            if leaf is None:
                leaf = GridLeaf(mapping.forward(local), system)
                leaf.set_style(
                    **(
                        system.background_line_style
                        if level == "major"
                        else system.faded_line_style
                    )
                )
                leaf.set_style(**axis._grid_styles.get(level, {}))
            else:
                leaf._cache = mapping.forward(local)
            leaf.level, leaf.value = level, value
            retained[grid_key] = leaf
            visible = (level, key) in active and axis._grid_visible.get(level, True)
            if pool is not None:
                pool._show(leaf, pool._opacity(grid_key) if visible else 0.0)
            elif not visible:
                leaf._cache = np.empty((0, 3))
            if visible:
                current[key] = leaf
            (major if level == "major" else minor).append(leaf)
        for old_key in axis._grid_leaves.keys() - retained.keys():
            axis._grid_leaves[old_key]._cache = np.empty((0, 3))
        axis._grid_leaves = retained
        parts._replace(current)
    system.background_lines.submobjects = major
    system.faded_lines.submobjects = minor


class _RadialFunction:
    def __init__(self, function: Callable[..., Any], system: CartesianAxes) -> None:
        self.function, self.system = function, system

    def __call__(self, theta: float | FloatArray) -> FloatArray:
        return self.system._polar_data(self.function(theta), theta)


class _CachedSource:
    def __init__(self, source: ParametricSource) -> None:
        self.source = source
        self.payload: Payload | None = None
        self.discontinuities = source.discontinuities

    def at(self, t: ArrayLike) -> FloatArray:
        return self.source.at(t)

    def sample(self, map: CompiledMap, bounds: Bounds) -> Payload:
        if self.payload is None:
            self.payload = self.source.sample(map, bounds)
        return self.payload


class _PolarPlot(ParametricPlot):
    set_parameters = FunctionPlot.set_parameters

    def __init__(
        self,
        function: Callable[..., Any],
        system: CartesianAxes,
        theta_range: Sequence[float] | None,
        **kwargs: object,
    ) -> None:
        original = function
        function, self.parameters = _parameterize(function, kwargs)
        use_vectorized = cast(bool, kwargs.pop("use_vectorized", False))
        limits = list(theta_range) if theta_range is not None else [0.0, _TAU]
        if len(limits) == 2:
            limits.append(_TAU / 1024)
        elif len(limits) == 3:
            limits[2] = min(limits[2], _TAU / 1024)
        self.underlying_function = original
        self._cache_angles = isinstance(system, PolarAxes)
        super().__init__(
            _RadialFunction(function, system),
            system,
            use_vectorized,
            t_range=limits,
            **cast(dict[str, Any], kwargs),
        )

    def _rebuild(self) -> None:
        if self._cache_angles and isinstance(self.source, ParametricSource):
            self.source = _CachedSource(self.source)
        if isinstance(self.source, _CachedSource) and (
            self._dirty or self._parameters_changed()
        ):
            self.source.payload = None
        super()._rebuild()

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = super().__deepcopy__(memo)
        result.parameters = {name: copy.copy(p) for name, p in self.parameters.items()}
        # Rebind parameter objects, while keeping the system binding of artist copies.
        source = (
            self.source.source
            if isinstance(self.source, _CachedSource)
            else self.source
        )
        if isinstance(source, ParametricSource) and isinstance(
            source.function, _RadialFunction
        ):
            function = copy.copy(source.function.function)
            if hasattr(function, "parameters"):
                function.parameters = result.parameters
            radial = _RadialFunction(function, source.function.system)
            rebuilt = ParametricSource(
                radial,
                source._range or (0, _TAU),
                use_vectorized=source.use_vectorized,
                discontinuities=source.discontinuities,
                dt=source.dt,
            )
            result.source = (
                _CachedSource(rebuilt)
                if isinstance(self.source, _CachedSource)
                else rebuilt
            )
        return result


class PolarPlane(CartesianAxes):
    """Draw Manim's Cartesian polar plane with a bound circular grid.

    Parameters
    ----------
    radius_max, size, radius_step
        Data radius, scene diameter and major radial spacing. An omitted size
        gives unit size one.
    azimuth_step, azimuth_units, azimuth_compact_fraction
        Divisions per turn and AngleFormatter options.
    azimuth_offset, azimuth_direction
        Zero angle in radians and orientation, CCW or CW.
    azimuth_label_buff, azimuth_label_font_size
        Distance outside the rim and label size.
    radius_config
        NumberLine options shared by the Cartesian axes.
    background_line_style, faded_line_style, faded_line_ratio
        Grid styles and subdivisions per major interval.
    make_smooth_after_applying_functions
        Native nonlinear transform smoothing option.
    theme, cycle
        Series and legend defaults, as on NumberPlane.
    **kwargs
        CartesianAxes options, including individual axis configurations.
    """

    def __init__(
        self,
        radius_max: float = config.frame_y_radius,
        size: float | None = None,
        radius_step: float = 1,
        azimuth_step: float | None = None,
        azimuth_units: str | None = "PI radians",
        azimuth_compact_fraction: bool = True,
        azimuth_offset: float = 0,
        azimuth_direction: str = "CCW",
        azimuth_label_buff: float = SMALL_BUFF,
        azimuth_label_font_size: float = 24,
        radius_config: dict[str, Any] | None = None,
        background_line_style: dict[str, Any] | None = None,
        faded_line_style: dict[str, Any] | None = None,
        faded_line_ratio: int = 1,
        make_smooth_after_applying_functions: bool = True,
        *,
        theme: str | Theme | Mapping[str, Any] | None = None,
        cycle: str | Sequence[ParsableManimColor] | None = None,
        **kwargs: object,
    ) -> None:
        self.azimuth_step = _azimuth(azimuth_units, azimuth_direction, azimuth_step)
        self.azimuth_units, self.azimuth_direction = azimuth_units, azimuth_direction
        self.azimuth_offset = azimuth_offset
        self.azimuth_compact_fraction = azimuth_compact_fraction
        self.azimuth_label_buff, self.azimuth_label_font_size = (
            azimuth_label_buff,
            azimuth_label_font_size,
        )
        self.background_line_style, self.faded_line_style = _styles(
            background_line_style, faded_line_style, faded_line_ratio
        )
        self.faded_line_ratio = faded_line_ratio
        self.background_lines, self.faded_lines = VGroup(), VGroup()
        self.radius_config = {
            "stroke_width": 2,
            "include_ticks": False,
            "include_tip": False,
            "line_to_number_buff": SMALL_BUFF,
            "label_direction": DL,
            "font_size": 24,
            **(radius_config or {}),
        }
        resolved = _resolve_theme(theme)
        diameter = 2 * radius_max if size is None else size
        super().__init__(
            (-radius_max, radius_max, radius_step),
            (-radius_max, radius_max, radius_step),
            diameter,
            diameter,
            axis_config=self.radius_config,
            theme=replace(
                resolved, box=False, grid=(), position="origin", minor_ticks=0
            ),
            cycle=cycle,
            make_smooth_after_applying_functions=make_smooth_after_applying_functions,
            **cast(dict[str, Any], kwargs),
        )
        self.theme = resolved
        self.circles, self.spokes = _GridParts(self.x), _GridParts(self.y)
        self.submobjects[:0] = [self.faded_lines, self.background_lines]
        self._configure_grid()

    def _polar_data(self, radius: ArrayLike, azimuth: ArrayLike) -> FloatArray:
        theta = self.azimuth_offset + (
            1 if self.azimuth_direction == "CCW" else -1
        ) * np.asarray(azimuth, dtype=float)
        return super()._polar_data(radius, theta)

    @property
    def x_range(self) -> FloatArray:
        """Return Cartesian x endpoints and the initial radius step."""
        return self.x_axis.x_range

    @property
    def y_range(self) -> FloatArray:
        """Return Cartesian y endpoints and the initial radius step."""
        return self.y_axis.x_range

    def point_to_polar(self, point: ArrayLike) -> tuple[float, float]:
        """Invert the plane's offset and orientation.

        Parameters
        ----------
        point
            Scene point.

        Returns
        -------
        tuple of float
            Radius and azimuth in ``(-pi, pi]``.
        """
        radius, phi = super().point_to_polar(point)
        theta = (phi - self.azimuth_offset) * (
            1 if self.azimuth_direction == "CCW" else -1
        )
        theta = (theta + np.pi) % _TAU - np.pi
        return radius, np.pi if theta == -np.pi else theta

    def _circle(self, radius: float) -> FloatArray:
        points = Circle(radius=radius).points[:, :2]
        return self._data.forward(points)

    def _spoke(self, theta: float) -> FloatArray:
        data = self._polar_data(np.linspace(0, self.x_range[1], 4), theta).T
        return self._data.forward(data)

    def _configure_grid(self) -> None:
        if not hasattr(self, "circles"):
            return
        ratio = max(1, self.faded_line_ratio)
        step = self.x._step / ratio
        radial = [
            (float(k * step), "major" if k % ratio == 0 else "minor")
            for k in range(1, int(np.floor(self.x.range.value[1] / step + 1e-10)) + 1)
        ]
        angular = [
            (
                float(k * _TAU / self.azimuth_step / ratio),
                "major" if k % ratio == 0 else "minor",
            )
            for k in range(int(np.ceil(self.azimuth_step * ratio)))
        ]
        _grid(
            self,
            cast(list[tuple[float, Level]], radial),
            cast(list[tuple[float, Level]], angular),
        )

    def get_radian_label(
        self, number: float, font_size: float = 24, **kwargs: object
    ) -> MathTex:
        """Create a radian label for a fraction of a turn.

        Parameters
        ----------
        number
            Fraction of a turn.
        font_size, **kwargs
            MathTex size and style options.

        Returns
        -------
        MathTex
            Manim-compatible radian label.
        """
        text = (
            AngleFormatter(self.azimuth_units, self.azimuth_compact_fraction)
            .format_ticks(np.array([number * _TAU]))
            .text[0]
        )
        return MathTex(text, font_size=font_size, **cast(dict[str, Any], kwargs))

    def get_coordinate_labels(
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
        **kwargs: Unpack[_NumberOptions],
    ) -> VDict:
        """Create radius numbers and azimuth labels bound to this plane.

        Parameters
        ----------
        r_values
            Radial positions; defaults to positive x tick values.
        a_values
            Fractions of a turn; defaults to the azimuth divisions.
        **kwargs
            Radius number options.

        Returns
        -------
        VDict
            Radius labels at key 0 and azimuth labels at key 1.
        """
        radii = (
            [v for v in self.x.get_tick_range() if v > 0]
            if r_values is None
            else list(r_values)
        )
        angles = (
            np.arange(0, 1, 1 / self.azimuth_step)
            if a_values is None
            else list(a_values)
        )
        radial = VGroup()
        for radius in radii:
            label = _label(self.x.get_number_mobject(radius, **kwargs))

            def anchor(radius: float = float(radius)) -> FloatArray:
                return np.append(self._data.forward(np.array([[radius, 0.0]]))[0], 0)

            radial.add(BoundLabel(label, self, anchor))
        angular = VGroup()
        formatter = AngleFormatter(self.azimuth_units, self.azimuth_compact_fraction)
        for turn in angles:
            theta = float(turn * _TAU)
            text = formatter.format_ticks(np.array([theta])).text[0]

            def rim(theta: float = theta) -> FloatArray:
                return np.append(
                    self._data.forward(
                        self._polar_data(self.x.range.value[1], theta).reshape(1, 2)
                    )[0],
                    0,
                )

            point = self.pr2pt(self.x.range.value[1], theta)
            direction = point - self.get_origin()
            native = MathTex(text, font_size=self.azimuth_label_font_size).next_to(
                point, direction, aligned_edge=direction, buff=self.azimuth_label_buff
            )
            angular.add(BoundLabel(_label(native), self, rim))
        result = VDict([(0, radial), (1, angular)])
        self.coordinate_labels = result  # type: ignore[assignment]
        return result

    def add_coordinates(  # type: ignore[override]
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
        **kwargs: Unpack[_NumberOptions],
    ) -> Self:
        """Add coordinate labels once and return this plane.

        Parameters
        ----------
        r_values, a_values, **kwargs
            Positions and number options for get_coordinate_labels.

        Returns
        -------
        Self
            This plane.
        """
        previous = getattr(self, "coordinate_labels", None)
        labels = self.get_coordinate_labels(r_values, a_values, **kwargs)
        if previous in self.submobjects:
            self.submobjects.remove(previous)
        self.submobjects.insert(-1, labels)
        return self


class _MappedAxis(Axis):
    def __init__(
        self,
        system: PolarAxes,
        index: int,
        config: dict[str, Any],
        scale: Scale,
        locator: Locator,
    ) -> None:
        self._polar_system = system
        self._periodic = index == 1
        limits = (
            [0.0, _TAU, _TAU / system.azimuth_step]
            if self._periodic
            else list(system.r_range)
        )
        native = NumberLine(
            x_range=(0, _TAU, 1)
            if self._periodic
            else scale.forward(limits[:2]).tolist(),
            length=system.x_length / 2,
            **{**config, "include_numbers": False, "numbers_to_include": None},
        )
        super().__init__(
            system, index, limits, native, scale, locator, axis_config=config
        )
        if self._periodic:
            self._ticks = _PeriodicParts(self)
            self._minor_ticks = _PeriodicParts(self, "minor")
            self._numbers = _PeriodicParts(self, None)
            self.submobjects = [
                self.line,
                self._ticks,
                self._minor_ticks,
                self._numbers,
            ]
        self._default_exclusion = False
        self._label_direction_custom = "label_direction" in config

    def _part_value(self, value: float) -> float:
        value = float(value % _TAU) if self._periodic else value
        return 0.0 if self._periodic and abs(value - _TAU) < 1e-10 else value

    def _part_key(self, value: float) -> object:
        return (
            round_key(self._part_value(value))
            if self._periodic
            else super()._part_key(value)
        )

    def _locate(self, config: _TickConfig, limits: FloatArray) -> tuple[Tick, ...]:
        if self._periodic:
            config = (
                cast(Locator, self._periodic_locator(config[0])),
                self._periodic_locator(config[1]),
                cast(FixedLocator | None, self._periodic_locator(config[2])),
                config[3],
            )
        items = super()._locate(config, limits)
        if not self._periodic:
            return items
        unique: dict[object, Tick] = {}
        for item in items:
            value = self._part_value(item.value)
            if abs(value - _TAU) < 1e-10 or abs(value) < 1e-10:
                value = 0.0
            key = round_key(value)
            unique.setdefault(
                (item.level, key), Tick(value, item.level, key, item.label)
            )
        return tuple(unique.values())

    def _periodic_locator(self, locator: Locator | None) -> Locator | None:
        if not isinstance(locator, FixedLocator):
            return locator
        entries: dict[float, Tick] = {}
        for item in locator.entries:
            value = round_key(self._part_value(item.value))
            previous = entries.get(value)
            if previous is None or previous.level == "minor":
                entries[value] = Tick(value, item.level, value, item.label)
        return FixedLocator(
            (item.value, item.label, item.level) for item in entries.values()
        )

    def _hides_zero(self) -> bool:
        return not self._periodic and self.range.value[0] == 0

    def _anchors(self, values: ArrayLike) -> FloatArray:
        system = self._polar_system
        values = np.atleast_1d(np.asarray(values, dtype=float))
        if self._periodic:
            phi = system.azimuth_offset + system._sign * values
            distance = np.full(len(values), system.x_length / 2)
        else:
            phi = np.full(len(values), system.r_axis_angle)
            distance = system._distance(values)
        return np.column_stack(
            (distance * np.cos(phi), distance * np.sin(phi), np.zeros(len(values)))
        )

    def _number_direction(self, value: float) -> FloatArray:
        if self._label_direction_custom:
            return super()._number_direction(value)
        return self._normal(value)

    def _normal(self, value: float) -> FloatArray:
        system = self._polar_system
        phi = (
            system.azimuth_offset + system._sign * value
            if self._periodic
            else system.r_axis_angle + np.pi / 2
        )
        return np.array([np.cos(phi), np.sin(phi), 0])

    def _label_basis(self, value: float) -> tuple[FloatArray, FloatArray]:
        normal = self._normal(value)
        return np.array([normal[1], -normal[0], 0]), normal

    def _tick_geometry(
        self, items: list[Tick], level: Level, length: float
    ) -> FloatArray:
        values = np.array([item.value for item in items])
        centers = self._anchors(values)
        normals = np.array([self._normal(float(v)) for v in values]).reshape(-1, 3)
        direction = self._tick_styles[level].get(
            "direction",
            self._tick_styles["major"].get(
                "direction", TickDirection.IN if self._periodic else TickDirection.BOTH
            ),
        )
        start, end = {
            TickDirection.BOTH: (-length / 2, length / 2),
            TickDirection.IN: (-length, 0.0),
            TickDirection.OUT: (0.0, length),
        }[direction]
        result: FloatArray = (
            centers[:, None]
            + np.linspace(start, end, 4)[None, :, None] * normals[:, None]
        )
        return result

    def _configure(self, *, only_crossing: bool = False) -> None:
        if (
            only_crossing
            and self._periodic
            and self._decoration_seen == self._versions()
            and (self._pool is None or self._pool.same)
        ):
            return
        system = self._polar_system
        local = (
            Circle(radius=system.x_length / 2).points
            if self._periodic
            else self._anchors(np.linspace(self.range.value[0], self.range.value[1], 4))
        )
        self.line._axis_local = local
        self.line._cache = system.frame.mapping.forward(local)
        self._items = (
            self._drawn_items()
            if self._pool is None
            else self._uncovered(self._pool._update(self), self.range.value)
        )
        for level in ("major", "minor"):
            self._configure_level(level)
        if self.include_numbers or self._number_values is not None:
            self._configure_numbers()
            for members in self._number_members.values():
                for glyph in members:
                    glyph._cache = glyph._cache.copy()
        if self._label_values:
            self._configure_labels()
        self._range_seen = self.range.version
        self._decoration_seen = self._versions()
        self._style_seen = self._decoration_seen[1:]
        if self._pool is not None:
            self._pool._apply(self)

    def _configure_grid(self) -> None:
        self._polar_system._configure_grid()

    def number_to_point(self, number: object) -> FloatArray:
        values = np.asarray(number, dtype=float)
        local = self._anchors(values.ravel())
        result = self._system.frame.mapping.forward(local)
        return result.reshape((*values.shape, 3))

    n2p = number_to_point

    def point_to_number(self, point: ArrayLike) -> float | FloatArray:
        """Invert scene points on a mapped axis.

        Parameters
        ----------
        point
            One scene point or rows of scene points.

        Returns
        -------
        float or FloatArray
            Radial values or periodic azimuths in radians.
        """
        system = self._polar_system
        values = np.asarray(point, dtype=float)
        local = system.frame.mapping.inverse(np.atleast_2d(values))
        if self._periodic:
            result = (
                (np.arctan2(local[:, 1], local[:, 0]) - system.azimuth_offset)
                * system._sign
            ) % _TAU
        else:
            distance = local[:, :2] @ np.array(
                [np.cos(system.r_axis_angle), np.sin(system.r_axis_angle)]
            )
            lo, hi = self._scale.forward(self.range.value)
            result = self._scale.inverse(
                lo + distance / (system.x_length / 2) * (hi - lo)
            )
        return float(result[0]) if values.ndim == 1 else result

    p2n = point_to_number

    def get_length(self) -> float:
        return (
            self._polar_system.x_length * np.pi
            if self._periodic
            else self._polar_system.x_length / 2
        )


class PolarAxes(CartesianAxes):
    """Map radius and radian azimuth through one coupled transform node.

    Parameters
    ----------
    r_range
        Increasing radial endpoints and optional tick step; defaults to (0, 4, 1).
    size
        Positive scene diameter; defaults to the frame height.
    r_scale
        Scale or linear, log or symlog.
    azimuth_step, azimuth_units, azimuth_compact_fraction
        Angular divisions and AngleFormatter options.
    azimuth_offset, azimuth_direction
        Scene zero angle and CCW or CW orientation.
    azimuth_label_buff, azimuth_label_font_size
        Distance outside the rim and angular number size, overridable per axis.
    r_axis_angle
        Radial decoration's scene angle, independent of the azimuth orientation.
    r_axis_config, azimuth_axis_config
        NumberLine style and number options for each decoration.
    background_line_style, faded_line_style, faded_line_ratio
        Grid styles and subdivisions per major interval.
    theme, cycle
        Theme, legend and series defaults.
    **kwargs
        Native VGroup style options.

    Notes
    -----
    Artists remain separate scene mobjects, as on CartesianAxes. Add them to the
    scene and retain references to them. A radial range edit reuses each curve's
    sampled angle grid. Cartesian calculus, regions and error bars are unavailable.
    """

    def __init__(
        self,
        r_range: Sequence[float] | None = None,
        size: float | None = None,
        *,
        r_scale: Scale | str = "linear",
        azimuth_step: float | None = None,
        azimuth_units: str | None = "PI radians",
        azimuth_compact_fraction: bool = True,
        azimuth_offset: float = 0,
        azimuth_direction: str = "CCW",
        azimuth_label_buff: float = SMALL_BUFF,
        azimuth_label_font_size: float = 24,
        r_axis_angle: float = np.pi / 8,
        r_axis_config: dict[str, Any] | None = None,
        azimuth_axis_config: dict[str, Any] | None = None,
        background_line_style: dict[str, Any] | None = None,
        faded_line_style: dict[str, Any] | None = None,
        faded_line_ratio: int = 1,
        theme: str | Theme | Mapping[str, Any] | None = None,
        cycle: str | Sequence[ParsableManimColor] | None = None,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        self._polar_ready = False
        self.azimuth_step = _azimuth(azimuth_units, azimuth_direction, azimuth_step)
        self.azimuth_units, self.azimuth_direction = azimuth_units, azimuth_direction
        self.azimuth_offset, self.r_axis_angle = azimuth_offset, r_axis_angle
        self._sign = 1 if azimuth_direction == "CCW" else -1
        self._r_scale = _scale(r_scale, "r_scale")
        limits = list(r_range) if r_range is not None else [0, config.frame_y_radius, 1]
        self._validate_r_range(limits)
        diameter = float(config.frame_height - 1 if size is None else size)
        if not np.isfinite(diameter) or diameter <= 0:
            raise ValueError("size must be finite and positive")
        self._initial_r_range = np.array(
            [*limits[:2], limits[2] if len(limits) == 3 else 1], dtype=float
        )
        resolved = _resolve_theme(theme)
        self.background_line_style, self.faded_line_style = _styles(
            {**resolved.grid_style, **(background_line_style or {})},
            faded_line_style,
            faded_line_ratio,
        )
        if faded_line_style is None and "minor" in resolved.grid:
            self.faded_line_style.update(resolved.minor_grid_style)
        self.faded_line_ratio = faded_line_ratio
        super().__init__(
            limits,
            (0, _TAU),
            diameter,
            diameter,
            axis_config={"include_ticks": False, "include_tip": False},
            x_scale=cast(Any, self._r_scale),
            theme=replace(
                resolved, box=False, grid=(), position="origin", minor_ticks=0
            ),
            cycle=cycle,
            **kwargs,
        )
        self.theme = resolved
        radial_config = {
            "include_tip": False,
            "include_ticks": False,
            "include_numbers": True,
            "numbers_to_exclude": [0] if limits[0] == 0 else [],
            "font_size": 24,
            "stroke_width": 2,
            "decimal_number_config": self.x.decimal_number_config,
            **(r_axis_config or {}),
        }
        angular_config = {
            "include_tip": False,
            "include_ticks": True,
            "include_numbers": True,
            "numbers_to_exclude": [],
            "font_size": azimuth_label_font_size,
            "line_to_number_buff": azimuth_label_buff,
            "stroke_width": 2,
            **(azimuth_axis_config or {}),
        }
        radial_locator = self.x.locator
        self.r_axis = _MappedAxis(self, 0, radial_config, self._r_scale, radial_locator)
        self.azimuth_axis = _MappedAxis(
            self,
            1,
            angular_config,
            LinearScale(),
            MultipleLocator(_TAU / self.azimuth_step),
        )
        self.x = self.x_axis = self.r_axis
        self.y = self.y_axis = self.azimuth_axis
        self._ranges = (self.r_axis, self.azimuth_axis)
        self.axes = VGroup(self.r_axis, self.azimuth_axis)
        if not isinstance(self._r_scale, LinearScale):
            self.r_axis.formatter = FormatStrFormatter("%g")
            self.r_axis._formatter_custom = True
        self.azimuth_axis.formatter = AngleFormatter(
            azimuth_units, azimuth_compact_fraction
        )
        self.azimuth_axis._formatter_custom = True
        if resolved.tick_direction is not None:
            for axis in (self.r_axis, self.azimuth_axis):
                axis._tick_styles["major"]["direction"] = resolved.tick_direction
        for axis in (self.r_axis, self.azimuth_axis):
            count = max(faded_line_ratio - 1, resolved.minor_ticks)
            if count:
                axis.minor_locator = MinorCountLocator(axis.locator, count)
        self.circles, self.spokes = (
            _GridParts(self.r_axis),
            _GridParts(self.azimuth_axis),
        )
        self.background_lines, self.faded_lines = VGroup(), VGroup()
        self.bounds = _Disk(self.bounds.lower, self.bounds.upper)
        self.submobjects = [
            self.faded_lines,
            self.background_lines,
            self.r_axis,
            self.azimuth_axis,
            self.frame,
        ]
        self._polar_ready = True
        self._syncing = True
        self._compile()
        for axis in (self.r_axis, self.azimuth_axis):
            axis._configure()
        self._configure_grid()
        self._syncing = False

    @property
    def r_range(self) -> FloatArray:
        """Return read-only radial endpoints and the initial locator step."""
        if not self._polar_ready:
            return self._initial_r_range
        result = np.array([*self.r_axis.range.value, self.r_axis._step])
        result.flags.writeable = False
        return result

    def _validate_r_range(self, value: Sequence[float]) -> None:
        limits = _range(value, "r_range")
        lower, upper = self._r_scale.domain
        valid = (limits >= lower if self._r_scale.closed[0] else limits > lower) & (
            limits <= upper if self._r_scale.closed[1] else limits < upper
        )
        if (
            limits[0] >= limits[1]
            or not valid.all()
            or not np.isfinite(self._r_scale.forward(limits)).all()
        ):
            raise ValueError(
                "r_range must be increasing and inside the radial scale domain"
            )

    def _distance(self, values: ArrayLike) -> FloatArray:
        limits = self._r_scale.forward(self.r_axis.range.value)
        result: FloatArray = (
            (self._r_scale.forward(values) - limits[0])
            / (limits[1] - limits[0])
            * self.x_length
            / 2
        )
        return result

    def _compile(self) -> None:
        if not self._polar_ready:
            super()._compile()
            return
        scale = self._r_scale
        rmin, rmax = self.r_axis.range.value
        lo, hi = scale.forward([rmin, rmax])
        factor = self.x_length / 2 / (hi - lo)
        offset, sign = self.azimuth_offset, self._sign

        def forward(points: FloatArray) -> FloatArray:
            distance = (scale.forward(points[:, 0]) - lo) * factor
            lower, upper = scale.domain
            radii = points[:, 0]
            valid = (radii >= lower if scale.closed[0] else radii > lower) & (
                radii <= upper if scale.closed[1] else radii < upper
            )
            if isinstance(scale, LogScale):
                distance = np.where(points[:, 0] < rmin, np.nan, distance)
            else:
                distance = np.maximum(distance, 0)
            distance = np.where(valid, distance, np.nan)
            phi = offset + sign * points[:, 1]
            return np.column_stack((distance * np.cos(phi), distance * np.sin(phi)))

        def inverse(points: FloatArray) -> FloatArray:
            distance = np.hypot(points[:, 0], points[:, 1])
            radius = scale.inverse(distance / factor + lo)
            theta = ((np.arctan2(points[:, 1], points[:, 0]) - offset) * sign) % _TAU
            theta[np.isclose(theta, _TAU, rtol=0, atol=1e-12)] = 0
            theta[distance == 0] = 0
            return np.column_stack((radius, theta))

        self._data = Chain((FunctionNode(forward, inverse, dim=2),))
        self._data_version += 1
        self._range_versions = (self.x.range.version, self.y.range.version)

    def _polar_data(self, radius: ArrayLike, azimuth: ArrayLike) -> FloatArray:
        return np.array(
            np.broadcast_arrays(
                np.asarray(radius, dtype=float), np.asarray(azimuth, dtype=float)
            )
        )

    def point_to_polar(self, point: ArrayLike) -> tuple[float, float]:
        """Invert a scene point into radius and azimuth.

        Parameters
        ----------
        point
            One scene point.

        Returns
        -------
        tuple of float
            Radius and angle in ``[0, tau)``.
        """
        radius, theta = self.p2c(point)
        return float(radius), float(theta)

    def get_origin(self) -> FloatArray:
        """Return the scene position of the polar centre, including on log scales."""
        result: FloatArray = self.frame.mapping.forward(np.zeros((1, 2)))[0]
        return result

    def set_r_range(self, r_range: Sequence[float]) -> Self:
        """Set radial endpoints, retaining keyed decoration styles.

        Parameters
        ----------
        r_range
            Increasing endpoints and optional positive locator step.

        Returns
        -------
        Self
            This system, also through native animate.
        """
        self._validate_r_range(r_range)
        self.r_axis.range = _range(r_range, "r_range")
        return self

    def plot(self, *args: object, **kwargs: object) -> ParametricPlot | LinePlot:  # type: ignore[override]
        """Draw radius as a function of angle, or join radial data pairs.

        Parameters
        ----------
        *args
            Radius function and optional theta range, or radius and angle arrays.
        **kwargs
            Function parameters, theta_range and ordinary plot options.

        Returns
        -------
        ParametricPlot or LinePlot
            Registered artist with radial data coordinates.
        """
        function = (
            args[0]
            if args
            else kwargs.pop("r_func", kwargs.pop("function", kwargs.pop("xs", None)))
        )
        if callable(function):
            if len(args) > 3:
                raise TypeError("plot accepts r_func, theta_range and use_vectorized")
            limits = (
                args[1]
                if len(args) > 1
                else kwargs.pop("theta_range", kwargs.pop("x_range", None))
            )
            if len(args) > 2:
                kwargs["use_vectorized"] = args[2]
            return self.plot_polar_graph(
                function, cast(Sequence[float] | None, limits), **kwargs
            )
        if len(args) > 2:
            raise TypeError("plot accepts radii and azimuths for an array line")
        ys = args[1] if len(args) > 1 else kwargs.pop("ys", None)
        return self.line(
            cast(ArrayLike, function),
            cast(ArrayLike | None, ys),
            **cast(_ArtistOptions, kwargs),
        )

    def _circle(self, radius: float) -> FloatArray:
        distance = float(self._distance(radius))
        return Circle(radius=distance).points if distance > 0 else np.empty((0, 3))

    def _spoke(self, theta: float) -> FloatArray:
        phi = self.azimuth_offset + self._sign * theta
        result: FloatArray = np.linspace(0, self.x_length / 2, 4)[:, None] * np.array(
            [np.cos(phi), np.sin(phi), 0]
        )
        return result

    def _configure_grid(self) -> None:
        if not self._polar_ready:
            return
        radial = [(tick.value, tick.level) for tick in self.r_axis._tick_items()]
        angular = [(tick.value, tick.level) for tick in self.azimuth_axis._tick_items()]
        _grid(self, radial, angular)


def _unsupported(name: str) -> Callable[..., NoReturn]:
    def refuse(self: PolarAxes, *args: object, **kwargs: object) -> NoReturn:
        raise NotImplementedError(f"{name} is not implemented on PolarAxes")

    refuse.__doc__ = f"""Refuse Cartesian {name} on PolarAxes.

    Parameters
    ----------
    *args, **kwargs
        Cartesian helper arguments.

    Raises
    ------
    NotImplementedError
        Polar helpers are not available for this method.
    """
    return refuse


for _name in (
    "get_line_from_axis_to_point",
    "get_vertical_line",
    "get_horizontal_line",
    "get_lines_to_point",
    "get_vertical_lines_to_graph",
    "axvline",
    "axhline",
    "get_T_label",
    "angle_of_tangent",
    "slope_of_tangent",
    "get_tangent_line",
    "get_tangent_vector",
    "get_secant_slope_group",
    "plot_derivative_graph",
    "plot_antiderivative_graph",
    "get_area",
    "fill_between",
    "get_riemann_rectangles",
    "errorbar",
):
    setattr(PolarAxes, _name, _unsupported(_name))
