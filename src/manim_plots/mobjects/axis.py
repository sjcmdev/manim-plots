"""Axis containers and versioned ranges, with library-owned decoration leaves."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Sequence
from functools import partial
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Self, Unpack, cast

import numpy as np
from manim import Line, LinearBase, LogBase, MathTex, NumberLine, Tex, VGroup, VMobject
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.formatters import DecimalFormatter, decimal_places
from manim_plots.core.params import Param, Parameter
from manim_plots.core.scales import MINPOS_UNKNOWN, LinearScale, Scale
from manim_plots.core.ticks import Locator, LogLocator, MultipleLocator, axis_ticks
from manim_plots.mobjects.leaves import (
    AxisLine,
    GridLeaf,
    Leaf,
    NumberLabel,
    TickLeaf,
    TipLeaf,
    _DecimalOptions,
    _label,
    _NumberOptions,
    _NumberPlacement,
    _RotateOptions,
    _VMStyle,
)

if TYPE_CHECKING:
    from manim_plots.mobjects.system import CartesianAxes


def _range(value: ArrayLike, name: str = "range") -> FloatArray:
    result = np.asarray(value, dtype=float)
    if result.ndim != 1 or len(result) not in (2, 3):
        raise ValueError(f"{name} must have length 2 or 3")
    bad = np.flatnonzero(~np.isfinite(result))
    if len(bad):
        raise ValueError(f"{name}[{bad[0]}] must be finite")
    if result[0] == result[1]:
        raise ValueError(f"{name} endpoints must differ")
    if len(result) == 3 and result[2] <= 0:
        raise ValueError(f"{name} step must be positive")
    return result[:2].copy()


def _scale_range(scale: Scale, value: ArrayLike) -> FloatArray:
    limits = _range(value)
    return np.array(
        scale.limit_range(float(limits[0]), float(limits[1]), MINPOS_UNKNOWN)
    )


class _LogExponentLocator(LogLocator):
    def __init__(self, base: float, step: float) -> None:
        super().__init__(base=base if base > 1 else 1 / base)
        self._step = step

    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        """Return decades at multiples of the exponent step.

        Parameters
        ----------
        lo, hi, scale, max_ticks
            Data limits, logarithmic scale and label-space estimate.
        """
        limits = scale.forward([lo, hi])
        exponents = MultipleLocator(self._step).values(
            float(limits[0]), float(limits[1]), LinearScale(), max_ticks
        )
        return scale.inverse(exponents)


class Axis(VGroup):
    """Group an axis line, keyed ticks, numbers, labels and a grid.

    Parameters
    ----------
    system
        Owning system.
    index
        Coordinate index, zero for x and one for y.
    limits
        Endpoints and optional initial locator spacing.
    native
        Native NumberLine furnishing the initial geometry and style.
    scale
        Numeric data scale, defaulting to linear.
    locator, minor_locator
        Major and optional minor tick generators.
    axis_config
        Merged NumberLine configuration, including label options.
    """

    range: Param[FloatArray] = Param((-1.0, 1.0), validate=_range)

    def __init__(
        self,
        system: CartesianAxes,
        index: int,
        limits: Sequence[float],
        native: NumberLine,
        scale: Scale | None = None,
        locator: Locator | None = None,
        minor_locator: Locator | None = None,
        axis_config: dict[str, Any] | None = None,
    ) -> None:
        self._system = system
        self.index = index
        self.range = limits
        self._range_parameter = self.range
        self._step = limits[2] if len(limits) == 3 else 1
        self.locator = locator or MultipleLocator(self._step)
        self.minor_locator = minor_locator
        self._scale = scale or LinearScale()
        self._range_parameter._validate = partial(_scale_range, self._scale)
        self._config = axis_config or {}
        self.scaling = native.scaling
        self.include_ticks = native.include_ticks
        self.include_tip = native.include_tip
        self.exclude_origin_tick = native.exclude_origin_tick
        self.tick_size = native.tick_size
        self.font_size = native.font_size
        self.label_direction = np.asarray(native.label_direction, dtype=float)
        self.line_to_number_buff = native.line_to_number_buff
        self.numbers_to_exclude = tuple(native.numbers_to_exclude)
        self.numbers_to_include = self._config.get("numbers_to_include")
        self.include_numbers = self._config.get("include_numbers", False)
        self.decimal_number_config = self._config.get(
            "decimal_number_config", {"num_decimal_places": decimal_places(self._step)}
        )
        self.formatter = DecimalFormatter(
            self.decimal_number_config.get("num_decimal_places", 0)
        )
        self._number_values: tuple[float, ...] | None = None
        self._number_options: dict[str, Any] = {}
        self._number_leaves: dict[object, NumberLabel] = {}
        self._number_offsets: dict[object, list[FloatArray]] = {}
        self._label_values: dict[float, object] = {}
        self._label_options: dict[str, Any] = {}
        self._minor_leaves: dict[object, TickLeaf] = {}
        self._grid_styles: dict[str, dict[str, Any]] = {}
        self._grid_visible: dict[str, bool] = {}
        self._range_seen = self.range.version
        self._native = native
        self._line_reference = native.points.copy()
        self._reference_length = native.get_length()
        cross_value = float(np.clip(0, native.x_min, native.x_max))
        self._crossing_reference = native.number_to_point(cross_value).copy()
        tick = native.get_tick(cross_value, native.tick_size)
        self._tick_reference = tick.points - self._crossing_reference
        self._tip_reference = native.tip.points.copy() if native.has_tip() else None
        self._tick_leaves: dict[object, TickLeaf] = {}
        self.line = AxisLine(native.points, system)
        self.line.match_style(native, family=False)
        self.ticks = VGroup()
        self.minor_ticks = VGroup()
        self.numbers = VGroup()
        self.labels = VGroup()
        self.grid = VGroup()
        self.tip: TipLeaf | None = None
        if native.has_tip():
            self.tip = TipLeaf(native.tip.points, system)
            self.tip.match_style(native.tip)
        super().__init__(
            self.line, self.ticks, *(() if self.tip is None else (self.tip,))
        )
        self.match_style(native, family=False)
        if self.include_ticks:
            self._configure_ticks(native)
        if self.minor_locator is not None:
            self.add(self.minor_ticks)

    @property
    def ticks(self) -> VGroup:
        """Return the current major tick family, updating a changed range lazily."""
        self._system._sync_data()
        return self._ticks

    @ticks.setter
    def ticks(self, value: VGroup) -> None:
        self._ticks = value

    @property
    def numbers(self) -> VGroup:
        """Return the current numbers family."""
        self._system._sync_data()
        return self._numbers

    @numbers.setter
    def numbers(self, value: VGroup) -> None:
        self._numbers = value

    @property
    def minor_ticks(self) -> VGroup:
        """Return the current minor ticks family."""
        self._system._sync_data()
        return self._minor_ticks

    @minor_ticks.setter
    def minor_ticks(self, value: VGroup) -> None:
        self._minor_ticks = value

    @property
    def grid(self) -> VGroup:
        """Return the current grid family."""
        self._system._sync_data()
        return self._grid

    @grid.setter
    def grid(self, value: VGroup) -> None:
        self._grid = value

    @property
    def labels(self) -> VGroup:
        """Return the current labels family."""
        self._system._sync_data()
        return self._labels

    @labels.setter
    def labels(self, value: VGroup) -> None:
        self._labels = value

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"Axis has no attribute {name!r}")

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if isinstance(value, Parameter):
                # Immutable values and foreign bindings remain shared, as sources do.
                if id(value) not in memo:
                    memo[id(value)] = copy.copy(value)
                result.__dict__[key] = memo[id(value)]
            else:
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result

    def _configure_ticks(self, native: NumberLine) -> None:
        lo, hi = self.range.value
        values = axis_ticks(
            self.locator, None, float(lo), float(hi), self._scale, 10000
        )
        previous = self._tick_leaves
        current: dict[object, TickLeaf] = {}
        for item in values:
            value = item.value
            if value == 0 and self.exclude_origin_tick:
                continue
            key = self.locator.key(float(value))
            size = native.tick_size
            if np.any(np.isclose(value, tuple(native.numbers_with_elongated_ticks))):
                size *= native.longer_tick_multiple
            template = native.get_tick(float(value), size)
            leaf = previous.get(key)
            if leaf is None:
                leaf = TickLeaf(template.points, self._system)
                leaf.match_style(template)
            else:
                leaf._cache = template.points.copy()
            current[key] = leaf
        self._tick_leaves = current
        self.ticks.submobjects = list(current.values())

    def _resize(self, length: float) -> None:
        delta = length - self._reference_length
        if abs(delta) <= 1e-12 * max(length, self._reference_length):
            return
        positions = self._line_reference[:, self.index]
        fractions = (positions - positions[0]) / (positions[-1] - positions[0])
        self._line_reference[:, self.index] += delta * (fractions - 0.5)
        if self._tip_reference is not None:
            self._tip_reference[:, self.index] += delta / 2
        self._reference_length = length

    def _configure(self) -> None:
        system = self._system
        limits = self.range.value
        other = system.y_axis if self.index == 0 else system.x_axis
        cross = float(np.clip(0, min(other.range.value), max(other.range.value)))
        coords = np.array(
            [[system.x_axis.range.value[0], system.y_axis.range.value[0]]]
        )
        coords[0, 1 - self.index] = cross
        origin = np.column_stack((system._data.forward(coords), np.zeros(1)))[0]
        offset = origin - self._crossing_reference
        # Range changes move the crossing, but preserve line and tip dimensions.
        offset[self.index] = 0
        mapping = system.frame.mapping
        self.line._cache = mapping.forward(self._line_reference + offset)
        if self.tip is not None and self._tip_reference is not None:
            self.tip._cache = mapping.forward(self._tip_reference + offset)
        previous, current = self._tick_leaves, {}
        items = tuple(
            item
            for item in axis_ticks(
                self.locator,
                None,
                float(limits[0]),
                float(limits[1]),
                self._scale,
                10000,
            )
            if item.value != 0 or not self.exclude_origin_tick
        )
        positions = np.full((len(items), 2), cross)
        positions[:, self.index] = [item.value for item in items]
        centers = system._data.forward(positions)
        local = np.tile(self._tick_reference, (len(items), 1, 1))
        elongated = self._native.numbers_with_elongated_ticks
        if tuple(elongated):
            factors = np.array(
                [
                    self._native.longer_tick_multiple
                    if np.any(np.isclose(item.value, tuple(elongated)))
                    else 1
                    for item in items
                ]
            )
            local *= factors[:, None, None]
        local[:, :, :2] += centers[:, None, :]
        placed = mapping.forward(local.reshape(-1, 3)).reshape(local.shape)
        for item, points in zip(items, placed, strict=True):
            leaf = previous.get(item.key)
            if leaf is None:
                leaf = TickLeaf(points, system)
                leaf.match_style(self.line)
            else:
                leaf._cache = points
            current[item.key] = leaf
        # Cairo keeps dropped leaves in the play's initial moving family.
        for key in previous.keys() - current.keys():
            previous[key]._cache = np.empty((0, 3))
        self._tick_leaves = current
        self.ticks.submobjects = list(current.values()) if self.include_ticks else []
        self._range_seen = self.range.version
        if self.minor_locator is not None:
            self._configure_minor()
        if self._number_values is not None or self.include_numbers:
            self._configure_numbers()
        if self._label_values:
            self._configure_labels()

    def set_grid(
        self,
        level: Literal["major", "minor"] = "major",
        visible: bool = True,
        **style: Unpack[_VMStyle],
    ) -> Self:
        """Configure grid lines across the other axis's range.

        Parameters
        ----------
        level
            Major or minor tick level.
        visible
            Whether to display this grid level.
        **style
            Native VMobject style options for the selected level.
        """
        if level not in ("major", "minor"):
            raise ValueError("level must be major or minor")
        self._grid_visible[level] = visible
        self._grid_styles.setdefault(level, {}).update(style)
        self._system._sync_data()
        self._system._configure_grid()
        return self

    def _configure_grid(self) -> None:
        if not self._grid_visible:
            return
        system = self._system
        other = system.get_axis(1 - self.index)
        lo, hi = self.range.value
        crossing = float(np.clip(0, min(lo, hi), max(lo, hi)))
        items = axis_ticks(
            self.locator, self.minor_locator, float(lo), float(hi), self._scale, 10000
        )
        lines: list[VMobject] = []
        for item in items:
            if not self._grid_visible.get(item.level, False) or np.isclose(
                item.value, crossing, rtol=0, atol=1e-12
            ):
                continue
            endpoints = np.zeros((2, 2))
            endpoints[:, self.index] = item.value
            endpoints[:, 1 - self.index] = other.range.value
            local = system._data.forward(endpoints)
            template = Line(np.append(local[0], 0), np.append(local[1], 0))
            line = GridLeaf(system.frame.mapping.forward(template.points), system)
            line.level, line.value = item.level, item.value
            line.set_style(**self._grid_styles.get(item.level, {}))
            lines.append(line)
        self.grid.submobjects = lines
        if self.grid not in self.submobjects:
            self.add(self.grid)

    def _configure_minor(self) -> None:
        assert self.minor_locator is not None
        lo, hi = self.range.value
        items = axis_ticks(
            self.locator, self.minor_locator, float(lo), float(hi), self._scale, 10000
        )
        current: dict[object, TickLeaf] = {}
        for item in items:
            if item.level != "minor":
                continue
            tick = self.get_tick(item.value, self.tick_size / 2)
            leaf = self._minor_leaves.get(item.key)
            if leaf is None:
                leaf = tick
            else:
                leaf._cache = tick.points
            current[item.key] = leaf
        self._minor_leaves = current
        self.minor_ticks.submobjects = list(current.values())

    @property
    def x_range(self) -> FloatArray:
        """Return NumberLine's range, including its original locator step."""
        limits = self.range.value
        if isinstance(self.scaling, LogBase):
            limits = self._scale.forward(limits)
        elif isinstance(self.scaling, LinearBase):
            limits = limits / self.scaling.scale_factor
        return np.array([*limits, self._step])

    def get_start(self) -> FloatArray:
        """Return the first endpoint of the axis."""
        return self.line.get_start()

    def get_end(self) -> FloatArray:
        """Return the endpoint, including the tip when present."""
        return self.line.get_end() if self.tip is None else self.tip.get_start()

    def get_length(self) -> float:
        """Return the distance between axis endpoints."""
        return float(np.linalg.norm(self.get_end() - self.get_start()))

    def get_angle(self) -> float:
        """Return the axis direction in the scene's xy plane."""
        vector = self.get_end() - self.get_start()
        return float(np.arctan2(vector[1], vector[0]))

    def number_to_point(self, number: ArrayLike) -> FloatArray:
        """Map values to scene points.

        Parameters
        ----------
        number
            Scalar or array of values in the scale domain.
        """
        self._system._sync_data()
        values = np.asarray(number, dtype=float)
        scaled = self._scale.forward(values)
        if not np.isfinite(scaled).all():
            raise ValueError("number must be finite and inside the scale domain")
        limits = self._scale.forward(self.range.value)
        alphas = (scaled - limits[0]) / (limits[1] - limits[0])
        result: FloatArray = self.get_start() + alphas[..., None] * (
            self.get_end() - self.get_start()
        )
        return result

    n2p = number_to_point

    def point_to_number(self, point: ArrayLike) -> float | FloatArray:
        """Invert scene points on the axis.

        Parameters
        ----------
        point
            One point or rows of points.
        """
        values = np.asarray(point, dtype=float)
        if (
            values.ndim not in (1, 2)
            or values.shape[-1] != 3
            or not np.isfinite(values).all()
        ):
            raise ValueError("point must contain finite rows of three coordinates")
        start = self.get_start()
        delta = self.get_end() - start
        squared = float(delta @ delta)
        if squared <= 1e-24:
            raise ValueError("axis is singular")
        proportion = (values - start) @ delta / squared
        limits = self._scale.forward(self.range.value)
        result = self._scale.inverse(limits[0] + proportion * (limits[1] - limits[0]))
        if not np.isfinite(result).all():
            raise ValueError("point maps to a non-finite number")
        return float(result) if result.ndim == 0 else result

    p2n = point_to_number

    def get_unit_size(self) -> float:
        """Return scene length per transformed coordinate unit."""
        span = float(np.diff(self._scale.forward(self.range.value))[0])
        if isinstance(self.scaling, LinearBase):
            span /= self.scaling.scale_factor
        return self.get_length() / abs(span)

    def get_unit_vector(self) -> FloatArray:
        """Return the axis direction multiplied by its unit size."""
        return (
            (self.get_end() - self.get_start())
            / self.get_length()
            * self.get_unit_size()
        )

    def rotate_about_number(
        self,
        number: float,
        angle: float,
        axis: ArrayLike = (0, 0, 1),
        **kwargs: Unpack[_RotateOptions],
    ) -> Self:
        """Rotate around a value.

        Parameters
        ----------
        number, angle, axis, **kwargs
            Native pivot, rotation and geometric options.
        """
        return self.rotate(
            angle, np.asarray(axis, dtype=float), about_point=self.n2p(number), **kwargs
        )

    def rotate_about_zero(
        self,
        angle: float,
        axis: ArrayLike = (0, 0, 1),
        **kwargs: Unpack[_RotateOptions],
    ) -> Self:
        """Rotate around zero.

        Parameters
        ----------
        angle, axis, **kwargs
            Native rotation options.
        """
        return self.rotate_about_number(0, angle, axis, **kwargs)

    def get_tick_range(self) -> FloatArray:
        """Return locator values, retaining the tick beneath a tip."""
        self._system._sync_data()
        lo, hi = self.range.value
        values = self.locator.values(float(lo), float(hi), self._scale, 10000)
        return values[values != 0] if self.exclude_origin_tick else values

    def get_tick(self, x: float, size: float | None = None) -> TickLeaf:
        """Return a positioned tick.

        Parameters
        ----------
        x, size
            Tick value and half length in scene units.
        """
        length = self.tick_size if size is None else size
        template = Line((0, -length, 0), (0, length, 0))
        template.rotate(self.get_angle()).move_to(self.n2p(x))
        leaf = TickLeaf(template.points, self._system)
        leaf.match_style(self.line)
        return leaf

    def get_tick_marks(self) -> VGroup:
        """Return the major tick family."""
        return self.ticks

    def add_ticks(self) -> Self:
        """Regenerate the major ticks using the current locator."""
        self.include_ticks = True
        self._configure()
        return self

    def get_number_mobject(
        self,
        x: float,
        direction: ArrayLike | None = None,
        buff: float | None = None,
        font_size: float | None = None,
        label_constructor: object = None,
        **number_config: Unpack[_DecimalOptions],
    ) -> NumberLabel:
        """Return a positioned cached-glyph number.

        Parameters
        ----------
        x, direction, buff, font_size, label_constructor, **number_config
            Native NumberLine label placement and formatting options.
        """
        options = {**self.decimal_number_config, **number_config}
        number = NumberLabel(
            x,
            font_size=self.font_size if font_size is None else font_size,
            label_constructor=label_constructor,
            **options,
        )
        number.next_to(
            self.n2p(x),
            direction=self.label_direction
            if direction is None
            else np.asarray(direction, dtype=float),
            buff=self.line_to_number_buff if buff is None else buff,
        )
        if x < 0 and self.label_direction[0] == 0:
            number.shift(np.array([-number[0].width / 2, 0, 0]))
        return number

    def get_number_mobjects(
        self, *numbers: float, **kwargs: Unpack[_NumberOptions]
    ) -> VGroup:
        """Return numbers at explicit or default tick values.

        Parameters
        ----------
        *numbers, **kwargs
            Positions and native number options.
        """
        values = numbers or tuple(self.get_tick_range())
        return VGroup(*(self.get_number_mobject(float(x), **kwargs) for x in values))

    def get_labels(self) -> VGroup:
        """Return number labels at the default tick values."""
        return self.get_number_mobjects()

    def add_numbers(
        self,
        x_values: Iterable[float] | None = None,
        excluding: Iterable[float] | None = None,
        font_size: float | None = None,
        label_constructor: object = None,
        **kwargs: Unpack[_NumberPlacement],
    ) -> Self:
        """Attach cached-glyph numbers.

        Parameters
        ----------
        x_values, excluding, font_size, label_constructor, **kwargs
            Native NumberLine positions, exclusions and formatting options.
        """
        self._number_values = None if x_values is None else tuple(map(float, x_values))
        self.include_numbers = True
        if excluding is not None:
            self.numbers_to_exclude = tuple(excluding)
        self._number_options = dict(kwargs)
        if font_size is not None:
            self._number_options["font_size"] = font_size
        self._number_leaves = {}
        self._number_offsets = {}
        self._configure_numbers()
        if self.numbers not in self.submobjects:
            self.add(self.numbers)
        return self

    def _configure_numbers(self) -> None:
        candidates = (
            self.get_tick_range()
            if self._number_values is None
            else self._number_values
        )
        lo, hi = sorted(self.range.value)
        values = [
            float(x)
            for x in candidates
            if x not in self.numbers_to_exclude and lo <= x <= hi
        ]
        system = self._system
        other = system.y_axis if self.index == 0 else system.x_axis
        cross = float(np.clip(0, min(other.range.value), max(other.range.value)))
        positions = np.full((len(values), 2), cross)
        positions[:, self.index] = values
        # One data and frame evaluation per family, including the affine inverse.
        anchors = system._data.forward(positions)
        anchors = np.column_stack((anchors, np.zeros(len(anchors))))
        mapping = system.frame.mapping
        points = mapping.forward(anchors)
        current: dict[object, NumberLabel] = {}
        glyphs: list[Leaf] = []
        local_points: list[FloatArray] = []
        for x, anchor, point in zip(values, anchors, points, strict=True):
            key = self.locator.key(x)
            label = self._number_leaves.get(key)
            if label is None:
                if isinstance(self.scaling, LogBase) and self.scaling.custom_labels:
                    exponent = float(self._scale.forward(x))
                    places = self.decimal_number_config.get("num_decimal_places", 0)
                    label = NumberLabel(
                        self.scaling.base,
                        font_size=48,
                        num_decimal_places=0,
                        unit="^{" + f"{exponent:.{places}f}" + "}",
                    )
                    label.font_size = self.font_size
                    label.next_to(
                        point,
                        direction=self.label_direction,
                        buff=self.line_to_number_buff,
                    )
                else:
                    label = self.get_number_mobject(x, **self._number_options)
                members = [
                    cast(Leaf, member) for member in label.family_members_with_points()
                ]
                counts = [len(member._cache) for member in members]
                local = (
                    mapping.inverse(
                        np.concatenate([member._cache for member in members])
                    )
                    - anchor
                )
                breaks = np.cumsum([0, *counts])
                self._number_offsets[key] = [
                    local[start:stop] for start, stop in pairwise(breaks)
                ]
            for glyph, offset in zip(
                label.family_members_with_points(),
                self._number_offsets[key],
                strict=True,
            ):
                leaf = cast(Leaf, glyph)
                leaf._system = system
                glyphs.append(leaf)
                local_points.append(offset + anchor)
            current[key] = label
        if local_points:
            placed = mapping.forward(np.concatenate(local_points))
            offset_index = 0
            for glyph, local in zip(glyphs, local_points, strict=True):
                glyph._cache = placed[offset_index : offset_index + len(local)]
                offset_index += len(local)
        for key in self._number_leaves.keys() - current.keys():
            for glyph in self._number_leaves[key].family_members_with_points():
                cast(Leaf, glyph)._cache = np.empty((0, 3))
        self._number_leaves = current
        self._number_offsets = {key: self._number_offsets[key] for key in current}
        self.numbers.submobjects = list(current.values())
        if isinstance(self.scaling, LogBase) and self.scaling.custom_labels:
            self.labels = self.numbers

    def add_labels(
        self,
        dict_values: dict[float, object],
        direction: ArrayLike | None = None,
        buff: float | None = None,
        font_size: float | None = None,
        label_constructor: object = None,
    ) -> Self:
        """Attach explicit labels, interpreting strings in text mode.

        Parameters
        ----------
        dict_values, direction, buff, font_size, label_constructor
            Native NumberLine labels and placement options.
        """
        self._label_values = dict(dict_values)
        self._label_options = {
            "direction": self.label_direction if direction is None else direction,
            "buff": self.line_to_number_buff if buff is None else buff,
            "font_size": self.font_size if font_size is None else font_size,
            "label_constructor": label_constructor,
        }
        self._configure_labels()
        if self.labels not in self.submobjects:
            self.add(self.labels)
        return self

    def _configure_labels(self) -> None:
        labels: list[VMobject] = []
        for x, value in self._label_values.items():
            size = self._label_options["font_size"]
            constructor = self._label_options["label_constructor"]
            if constructor is not None and not isinstance(value, VMobject):
                if constructor is MathTex and isinstance(value, str):
                    constructor = Tex
                if not callable(constructor):
                    raise TypeError("label_constructor must be callable")
                value = constructor(str(value))
            if isinstance(value, VMobject):
                if not hasattr(value, "font_size"):
                    raise AttributeError("label is not compatible with add_labels")
                cast(Any, value).font_size = size
            label = _label(value, text_mode=isinstance(value, str), font_size=size)
            label.next_to(
                self.n2p(x),
                direction=self._label_options["direction"],
                buff=self._label_options["buff"],
            )
            for member in label.family_members_with_points():
                cast(Leaf, member)._system = self._system
            labels.append(label)
        self.labels.submobjects = labels
