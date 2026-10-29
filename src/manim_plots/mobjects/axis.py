"""Axis containers and versioned ranges, with library-owned decoration leaves."""

from __future__ import annotations

import copy
import warnings
from collections.abc import Iterable, Sequence
from enum import Enum
from functools import partial
from math import floor
from numbers import Real
from typing import Any, Literal, NoReturn, Self, Unpack

import numpy as np
from manim import Line, LinearBase, LogBase, NumberLine, VGroup
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray, ManimPlotsWarning
from manim_plots.core.formatters import (
    DecimalFormatter,
    Formatter,
    as_formatter,
    decimal_places,
)
from manim_plots.core.params import Param, Parameter
from manim_plots.core.scales import MINPOS_UNKNOWN, LinearScale, Scale
from manim_plots.core.ticks import (
    FixedLocator,
    Level,
    Locator,
    LogLocator,
    MaxNLocator,
    MultipleLocator,
    Tick,
    as_locator,
    axis_ticks,
    plan_pool,
)
from manim_plots.mobjects import leaves as leaf_state
from manim_plots.mobjects.axis_labels import (
    _configure_labels,
    _configure_numbers,
    _layout_overlap,
    _Parts,
    _restore_overlap,
)
from manim_plots.mobjects.leaves import (
    AxisLine,
    GridLeaf,
    Leaf,
    NumberLabel,
    TickLeaf,
    TipLeaf,
    _DecimalOptions,
    _glyph,
    _NumberOptions,
    _NumberPlacement,
    _RotateOptions,
    _VMStyle,
)


class TickDirection(Enum):
    """Choose whether ticks straddle the axis or face its interior or exterior."""

    IN = "in"
    OUT = "out"
    BOTH = "both"


def _finite(value: object, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _offset(value: ArrayLike) -> FloatArray:
    result = np.asarray(value, dtype=float)
    if result.shape != (2,) or not np.isfinite(result).all():
        raise ValueError("offset must contain two finite scene distances")
    return result


def _choice(value: str, name: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return value


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


type _TickConfig = tuple[
    Locator, Locator | None, FixedLocator | None, Literal["add", "replace"]
]


class _TickPool:
    def __init__(self, axis: Axis, target: Axis, alphas: FloatArray) -> None:
        self.start: _TickConfig = (
            axis.locator,
            axis.minor_locator,
            axis._explicit,
            axis._tick_mode,
        )
        self.target: _TickConfig = (
            target.locator,
            target.minor_locator,
            target._explicit,
            target._tick_mode,
        )
        self.same = all(
            type(a) is type(b)
            and repr(vars(a) if hasattr(a, "__dict__") else a)
            == repr(vars(b) if hasattr(b, "__dict__") else b)
            for a, b in zip(self.start, self.target, strict=True)
        )
        self.building = True
        self.alpha = 0.0
        self.fade = 4 / max(1, len(alphas) - 1)
        self.active: dict[object, float] = {}
        self.absent: dict[object, FloatArray] = {}
        self.styles: dict[Leaf, tuple[FloatArray, FloatArray]] = {}
        self.spares: dict[Level, list[TickLeaf]] = {"major": [], "minor": []}
        start, end = axis.range.value, target.range.value
        schedule: list[tuple[float, dict[object, Tick]]] = []

        def ticks_at(alpha: float) -> tuple[Tick, ...]:
            limits = (1 - alpha) * start + alpha * end
            ticks = axis._uncovered(self._items(axis, limits, alpha), limits)
            schedule.append((alpha, {(t.level, t.key): t for t in ticks}))
            return ticks

        plan = plan_pool(ticks_at, [0.0, 1.0, *alphas])
        by_key = {key: tick for _, items in schedule for key, tick in items.items()}
        self.items = tuple(by_key[key] for key in plan.keys)
        for key in plan.keys:
            self.absent[key] = np.array(
                [a for a, items in schedule if key not in items]
            )
        self.count = plan.spares

    def _items(self, axis: Axis, limits: FloatArray, alpha: float) -> tuple[Tick, ...]:
        def generate(
            config: _TickConfig,
        ) -> tuple[Tick, ...]:
            major, minor, explicit, mode = config
            return axis_ticks(
                major,
                minor,
                float(limits[0]),
                float(limits[1]),
                axis._scale,
                axis.max_ticks,
                explicit=explicit,
                mode=mode,
            )

        ticks = generate(self.start)
        if self.same:
            return ticks
        left = {(t.level, t.key): t for t in ticks}
        right = {(t.level, t.key): t for t in generate(self.target)}
        result = []
        for key in dict.fromkeys((*left, *right)):
            a, b = left.get(key), right.get(key)
            if a is not None and b is not None:
                tick = Tick(
                    (1 - alpha) * a.value + alpha * b.value, a.level, a.key, b.label
                )
            else:
                remaining = a if b is None else b
                assert remaining is not None
                tick = remaining
            result.append(tick)
        return tuple(result)

    def _opacity(self, key: object) -> float:
        if not self.same:
            return self.active.get(key, 0.0)
        absent = self.absent.get(key)
        if absent is None:
            self.absent[key] = np.array([self.alpha])
            return 1e-6
        return (
            max(1e-6, min(1.0, float(np.min(abs(absent - self.alpha))) / self.fade))
            if len(absent)
            else 1.0
        )

    def _update(self, axis: Axis) -> tuple[Tick, ...]:
        ticks = self._items(axis, axis.range.value, self.alpha)
        if self.same:
            self.active = {(t.level, t.key): 1.0 for t in ticks}
        else:
            lo, hi = axis.range.value
            left = axis_ticks(
                self.start[0],
                self.start[1],
                float(lo),
                float(hi),
                axis._scale,
                axis.max_ticks,
                explicit=self.start[2],
                mode=self.start[3],
            )
            right = axis_ticks(
                self.target[0],
                self.target[1],
                float(lo),
                float(hi),
                axis._scale,
                axis.max_ticks,
                explicit=self.target[2],
                mode=self.target[3],
            )
            self.active = {(t.level, t.key): 1 - self.alpha for t in left}
            for t in right:
                key = (t.level, t.key)
                self.active[key] = min(1.0, self.active.get(key, 0.0) + self.alpha)
        return ticks

    def _take(self, axis: Axis, level: Level) -> TickLeaf | None:
        if self.spares[level]:
            return self.spares[level].pop()
        if not axis._system._pool_warned and not leaf_state._SIMULATING:
            axis._system._pool_warned = True
            warnings.warn(
                "tick pool exhausted its spare leaves during this play",
                ManimPlotsWarning,
                stacklevel=3,
            )
        return None

    def _show(self, leaf: Leaf, opacity: float) -> None:
        if leaf not in self.styles:
            self.styles[leaf] = (
                leaf.stroke_rgbas[:, 3].copy(),
                leaf.fill_rgbas[:, 3].copy(),
            )
        stroke, fill = self.styles[leaf]
        leaf.stroke_rgbas[:, 3] = stroke * opacity
        leaf.fill_rgbas[:, 3] = fill * opacity
        leaf._pool_visible = opacity > 0

    def _apply(self, axis: Axis) -> None:
        for level, leaves in (
            ("major", axis._tick_leaves),
            ("minor", axis._minor_leaves),
        ):
            for key, leaf in leaves.items():
                pair = (level, key)
                self._show(
                    leaf,
                    self._opacity(pair)
                    if axis.include_ticks and pair in self.active
                    else 0.0,
                )
        for key in axis._number_leaves:
            opacity = self._opacity(key) if key in self.active else 0.0
            for glyph in axis._number_members[key]:
                self._show(glyph, opacity)
        for spares in self.spares.values():
            for leaf in spares:
                self._show(leaf, 0.0)


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


class _LogMinorLocator(LogLocator):
    def values(self, lo: float, hi: float, scale: Scale, max_ticks: int) -> FloatArray:
        """Budget minor subdivisions by the space available for major decades.

        Parameters
        ----------
        lo, hi, scale, max_ticks
            Data limits, logarithmic scale and major label-space estimate.
        """
        return super().values(lo, hi, scale, max_ticks * len(self.subs))


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
    rotation: Param[float] = Param(0.0, validate=partial(_finite, name="rotation"))
    offset: Param[FloatArray] = Param((0.0, 0.0), validate=_offset)
    justify: Param[str] = Param(
        "center",
        validate=partial(_choice, name="justify", choices=("center", "left", "right")),
    )
    overlap: Param[str] = Param(
        "hide",
        validate=partial(_choice, name="overlap", choices=("hide", "drop", "rotate")),
    )

    def __init__(
        self,
        system: mp.CartesianAxes,
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
        self.tick_under_tip = False
        self.exclude_origin_tick = native.exclude_origin_tick
        self.tick_size = native.tick_size
        self.font_size = native.font_size
        self.label_direction = np.asarray(native.label_direction, dtype=float)
        self.line_to_number_buff = native.line_to_number_buff
        self.numbers_to_exclude = tuple(native.numbers_to_exclude)
        # Manim's default exclusion of 0, which follows the crossing (_hides_zero).
        self._default_exclusion = True
        self.numbers_to_include = self._config.get("numbers_to_include")
        self.include_numbers = self._config.get("include_numbers", False)
        self.decimal_number_config = self._config.get(
            "decimal_number_config", {"num_decimal_places": decimal_places(self._step)}
        )
        self.formatter: Formatter = DecimalFormatter(
            self.decimal_number_config.get("num_decimal_places", 0)
        )
        self._formatter_custom = False
        self._explicit: FixedLocator | None = None
        self._tick_mode: Literal["add", "replace"] = "add"
        self._items: tuple[Tick, ...] = ()
        self._pool: _TickPool | None = None
        self._tick_styles: dict[Level, dict[str, Any]] = {"major": {}, "minor": {}}
        self._position: str | float = "origin"
        self._position_fraction: float | None = None
        self._mirrors: list[Axis] = []
        self._mirror_of: Axis | None = None
        self._decoration_seen: tuple[int, ...] = ()
        self._number_content: dict[object, tuple[str, bool]] = {}
        self._number_members: dict[object, list[Leaf]] = {}
        self._label_style_seen: tuple[int, ...] | None = None
        self._label_offsets: dict[object, list[FloatArray]] = {}
        self._label_content: dict[object, object] = {}
        self._custom_style_seen: tuple[int, ...] | None = None
        self._grid_leaves: dict[object, GridLeaf] = {}
        self._number_values: tuple[float, ...] | None = None
        self._number_options: dict[str, Any] = {}
        self._number_leaves: dict[object, NumberLabel] = {}
        self._number_offsets: dict[object, list[FloatArray]] = {}
        self._label_values: dict[float, object] = {}
        self._label_options: dict[str, Any] = {}
        self._minor_leaves: dict[object, TickLeaf] = {}
        self._grid_styles: dict[str, dict[str, Any]] = {}
        self._grid_visible: dict[str, bool] = {}
        self._digit_height: float | None = None
        self._digit_font: float | None = None
        self._rotation_parameter = self.rotation
        self._offset_parameter = self.offset
        self._justify_parameter = self.justify
        self._overlap_parameter = self.overlap
        self._style_seen: tuple[int, ...] = (0, 0, 0, 0)
        self._range_seen = self.range.version
        self._crossing_frame = -1
        self._crossing_origin = np.zeros(3)
        self._crossing_leaves: list[Leaf] = []
        self._crossing_local = np.empty((0, 3))
        self._crossing_edges = np.zeros(1, dtype=np.intp)
        self._crossing_ticks: tuple[object, ...] | None = None
        self._crossing_density = -1
        self._native = native
        self._line_reference = native.points.copy()
        self._start_reference = native.get_start().copy()
        self._end_reference = native.get_end().copy()
        self._tip_start_reference: FloatArray | None = None
        self._reference_length = native.get_length()
        cross_value = float(np.clip(0, native.x_min, native.x_max))
        self._crossing_reference = native.number_to_point(cross_value).copy()
        tick = native.get_tick(cross_value, 1.0)
        self._tick_reference = tick.points - self._crossing_reference
        self._tip_reference = native.tip.points.copy() if native.has_tip() else None
        self._tick_leaves: dict[object, TickLeaf] = {}
        self.line = AxisLine(native.points, system)
        self.line.match_style(native, family=False)
        self.ticks = _Parts[TickLeaf](self)
        self.minor_ticks = _Parts[TickLeaf](self, "minor")
        self.numbers = _Parts[NumberLabel](self, None)
        self.labels = _Parts[VGroup](self)
        self.grid = _Parts[GridLeaf](self, None)
        self.tip: TipLeaf | None = None
        self.tip_start: TipLeaf | None = None
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
    def ticks(self) -> _Parts[TickLeaf]:
        """Return the current major tick family, updating a changed range lazily."""
        self._system._sync_data()
        return self._ticks

    @ticks.setter
    def ticks(self, value: _Parts[TickLeaf]) -> None:
        self._ticks = value

    @property
    def numbers(self) -> _Parts[NumberLabel]:
        """Return the current numbers family."""
        self._system._sync_data()
        return self._numbers

    @numbers.setter
    def numbers(self, value: _Parts[NumberLabel]) -> None:
        self._numbers = value

    @property
    def minor_ticks(self) -> _Parts[TickLeaf]:
        """Return the current minor ticks family."""
        self._system._sync_data()
        return self._minor_ticks

    @minor_ticks.setter
    def minor_ticks(self, value: _Parts[TickLeaf]) -> None:
        self._minor_ticks = value

    @property
    def grid(self) -> _Parts[GridLeaf]:
        """Return the current grid family."""
        self._system._sync_data()
        return self._grid

    @grid.setter
    def grid(self, value: _Parts[GridLeaf]) -> None:
        self._grid = value

    @property
    def labels(self) -> _Parts[Any]:
        """Return the current labels family."""
        self._system._sync_data()
        return self._labels

    @labels.setter
    def labels(self, value: _Parts[Any]) -> None:
        self._labels = value

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"Axis has no attribute {name!r}")

    def get_scale(self) -> Scale:
        """Return the numeric scale without shadowing Manim's geometric scale."""
        return self._scale

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
        self._items = self._drawn_items()
        values = (item for item in self._items if item.level == "major")
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
        self._ticks._replace(current)

    def _resize(self, length: float) -> None:
        delta = length - self._reference_length
        if abs(delta) <= 1e-12 * max(length, self._reference_length):
            return
        positions = self._line_reference[:, self.index]
        fractions = (positions - positions[0]) / (positions[-1] - positions[0])
        self._line_reference[:, self.index] += delta * (fractions - 0.5)
        if self._tip_reference is not None:
            self._tip_reference[:, self.index] += delta / 2
        self._start_reference[self.index] -= delta / 2
        self._end_reference[self.index] += delta / 2
        if self._tip_start_reference is not None:
            self._tip_start_reference[:, self.index] -= delta / 2
        self._reference_length = length

    def _parameters(self) -> tuple[Parameter[Any], ...]:
        return (self.range, self.rotation, self.offset, self.justify, self.overlap)

    def _style_changed(self) -> bool:
        seen = self._style_seen
        return (
            self._rotation_parameter.version != seen[0]
            or self._offset_parameter.version != seen[1]
            or self._justify_parameter.version != seen[2]
            or self._overlap_parameter.version != seen[3]
        )

    def _versions(self) -> tuple[int, ...]:
        return tuple(parameter.version for parameter in self._parameters())

    def _hides_zero(self) -> bool:
        """Whether the tick and number at 0 are left out, as Manim leaves them out.

        Manim's axes cross at the origin; once the other axis moves to a border or a
        value, nothing crosses this axis at 0 and its tick and number come back.
        """
        other = self._system.get_axis(1 - self.index)
        crossing = other._position == "origin" and other._position_fraction is None
        return self.exclude_origin_tick and crossing

    def _cross_value(self) -> float:
        other = self._system.get_axis(1 - self.index)
        lo, hi = other.range.value
        fraction = self._position_fraction
        where = self._position
        if self._mirror_of is not None:
            original = self._mirror_of
            transformed = other._scale.forward([lo, hi, original._cross_value()])
            position = (transformed[2] - transformed[0]) / (
                transformed[1] - transformed[0]
            )
            fraction = 0.0 if position > 0.5 else 1.0
        if fraction is not None:
            limits = other._scale.forward([lo, hi])
            return float(
                other._scale.inverse(limits[0] + fraction * (limits[1] - limits[0]))
            )
        if where == "origin":
            return float(np.clip(0, min(lo, hi), max(lo, hi)))
        if where in ("bottom", "left"):
            return float(lo)
        if where in ("top", "right"):
            return float(hi)
        return float(where)

    def _tick_items(self) -> tuple[Tick, ...]:
        lo, hi = self.range.value
        return axis_ticks(
            self.locator,
            self.minor_locator,
            float(lo),
            float(hi),
            self._scale,
            self.max_ticks,
            explicit=self._explicit,
            mode=self._tick_mode,
        )

    def _drawn_items(self) -> tuple[Tick, ...]:
        """Return the tick items without those at an end under a tip, as Manim's."""
        return self._uncovered(self._tick_items(), self.range.value)

    def _uncovered(
        self, items: tuple[Tick, ...], limits: FloatArray
    ) -> tuple[Tick, ...]:
        """Leave out the items at an end of ``limits`` that carries a tip."""
        source = self._mirror_of or self
        tips = (self.tip_start, self.tip)
        ends = [v for v, tip in zip(limits, tips, strict=True) if tip]
        if source.tick_under_tip or not ends or not items:
            return items
        lo, hi, *covered = self._scale.forward([*limits, *ends])
        values = self._scale.forward([item.value for item in items])
        near = np.abs(values[:, None] - np.array(covered)[None, :])
        keep = ~np.any(near <= 1e-9 * abs(hi - lo), axis=1)
        return tuple(item for item, kept in zip(items, keep, strict=True) if kept)

    @property
    def max_ticks(self) -> int:
        """Return the label-space estimate passed to both locators."""
        if self._digit_height is None or self._digit_font != self.font_size:
            self._digit_height = _glyph("0", self.font_size).height
            self._digit_font = self.font_size
        height = self._digit_height
        factor = 3 if self.index == 0 else 2
        return max(0, floor(self.get_length() / (factor * height))) if height else 0

    def _configure(self, *, only_crossing: bool = False) -> None:
        system = self._system
        coords = np.array([[self.range.value[0], self.range.value[0]]])
        coords[0, 1 - self.index] = self._cross_value()
        origin = np.append(system._data.forward(coords)[0], 0)
        offset = origin - self._crossing_reference
        offset[self.index] = 0
        mapping = system.frame.mapping
        locator = self.locator
        tick_config: tuple[object, ...] | None = None
        if self.minor_locator is None and self._explicit is None:
            if type(locator) is MaxNLocator:
                tick_config = (
                    MaxNLocator,
                    locator.n,
                    locator.steps,
                    self.include_ticks,
                )
            elif type(locator) is MultipleLocator:
                tick_config = (MultipleLocator, locator.step, self.include_ticks)
        if (
            only_crossing
            and tick_config is not None
            and tick_config == self._crossing_ticks
            and self._decoration_seen == self._versions()
            and self._crossing_frame == system.frame.version
            and not self._mirrors
            and (self._pool is None or self._pool.same)
        ):
            # The other range moves this decoration only across its own direction.
            delta = origin - self._crossing_origin
            delta[self.index] = 0
            placed = mapping.forward(self._crossing_local + delta)
            for leaf, start, stop in zip(
                self._crossing_leaves,
                self._crossing_edges[:-1],
                self._crossing_edges[1:],
                strict=True,
            ):
                leaf._cache = placed[start:stop]
            if self.max_ticks == self._crossing_density:
                if not mapping.is_affine:
                    for group in (self._numbers, self._labels):
                        group._replace(group._parts)
                        _layout_overlap(self, group)
                if self._pool is not None:
                    self._pool._apply(self)
                return
        self.line._axis_local = self._line_reference + offset
        self.line._cache = mapping.forward(self.line._axis_local)
        if self.tip is not None and self._tip_reference is not None:
            self.tip._axis_local = self._tip_reference + offset
            self.tip._cache = mapping.forward(self.tip._axis_local)
        if self.tip_start is not None and self._tip_start_reference is not None:
            self.tip_start._axis_local = self._tip_start_reference + offset
            self.tip_start._cache = mapping.forward(self.tip_start._axis_local)
        self._items = (
            self._drawn_items()
            if self._pool is None
            else self._uncovered(self._pool._update(self), self.range.value)
        )
        for level in ("major", "minor"):
            self._configure_level(level)
        self._range_seen = self.range.version
        self._decoration_seen = self._versions()
        self._style_seen = self._decoration_seen[1:]
        if self._mirror_of is None:
            if (
                self._number_values is not None
                or self.include_numbers
                or any(item.label is not None for item in self._items)
            ):
                self._configure_numbers()
            if self._label_values:
                self._configure_labels()
        for mirror in self._mirrors:
            mirror.locator, mirror.minor_locator = self.locator, self.minor_locator
            mirror._explicit, mirror._tick_mode = self._explicit, self._tick_mode
            mirror._tick_styles = self._tick_styles
            mirror._line_reference = self._line_reference
            mirror._start_reference = self._start_reference
            mirror._end_reference = self._end_reference
            mirror._reference_length = self._reference_length
            mirror._tip_reference = self._tip_reference
            mirror._tip_start_reference = self._tip_start_reference
            for attr in ("tip", "tip_start"):
                source = getattr(self, attr)
                target = getattr(mirror, attr)
                if source is None and target is not None:
                    mirror.remove(target)
                    setattr(mirror, attr, None)
                elif source is not None and target is None:
                    target = TipLeaf(source._cache, system)
                    target.match_style(source)
                    setattr(mirror, attr, target)
                    mirror.add(target)
            mirror._configure()
        if self._pool is not None:
            self._pool._apply(self)
        if tick_config is None or self._mirrors or self._mirror_of is not None:
            self._crossing_frame = -1
            return
        self._crossing_leaves = [
            leaf
            for leaf in self.get_family()
            if isinstance(leaf, Leaf) and leaf._axis_local is not None
        ]
        local = [
            leaf._axis_local
            for leaf in self._crossing_leaves
            if leaf._axis_local is not None
        ]
        self._crossing_local = np.concatenate(local)
        self._crossing_edges = np.r_[0, np.cumsum([len(points) for points in local])]
        self._crossing_origin = origin
        self._crossing_frame = system.frame.version
        self._crossing_ticks = tick_config
        self._crossing_density = self.max_ticks

    def _prepare_pool(self, pool: _TickPool) -> None:
        self._pool = pool
        self._items = pool.items
        for level in ("major", "minor"):
            self._configure_level(level)
            if level == "minor" and pool.start[1] is None and pool.target[1] is None:
                continue
            for _ in range(pool.count):
                leaf = TickLeaf(np.zeros((4, 3)), self._system)
                leaf.match_style(self.line)
                style = self._tick_styles[level]
                leaf.set_stroke(
                    color=style.get("color", leaf.get_color()), width=style.get("width")
                )
                pool.spares[level].append(leaf)
        if self.include_numbers or self._number_values is not None:
            self._configure_numbers()
            for label in self._number_leaves.values():
                _restore_overlap(label)
        self._configure_grid()
        pool.building = False

    def _finish_pool(self) -> None:
        pool, self._pool = self._pool, None
        if pool is not None:
            for leaf, (stroke, fill) in pool.styles.items():
                leaf.stroke_rgbas[:, 3] = stroke
                leaf.fill_rgbas[:, 3] = fill
                leaf._pool_visible = True

    def _configure_level(self, level: Level) -> None:
        system = self._system
        items = [
            item
            for item in self._items
            if item.level == level and (item.value != 0 or not self._hides_zero())
        ]
        style = self._tick_styles[level]
        major_length = self._tick_styles["major"].get("length", 2 * self.tick_size)
        length = style.get(
            "length", major_length / 2 if level == "minor" else major_length
        )
        local = np.tile(self._tick_reference, (len(items), 1, 1))
        local *= length / 2
        if level == "major":
            elongated = tuple(self._native.numbers_with_elongated_ticks)
            if elongated:
                factors = np.array(
                    [
                        self._native.longer_tick_multiple
                        if np.any(np.isclose(item.value, elongated))
                        else 1
                        for item in items
                    ]
                )
                local *= factors[:, None, None]
        major = self._tick_styles["major"]
        direction = style.get("direction", major.get("direction", TickDirection.BOTH))
        if direction is not TickDirection.BOTH:
            other = system.get_axis(1 - self.index)
            limits = other._scale.forward(other.range.value)
            cross = float(other._scale.forward(self._cross_value()))
            outward = -1 if (cross - limits[0]) / (limits[1] - limits[0]) <= 0.5 else 1
            if direction is TickDirection.IN:
                outward *= -1
            local[:, :, 1 - self.index] += (
                outward * np.ptp(local[:, :, 1 - self.index], axis=1)[:, None] / 2
            )
        positions = np.full((len(items), 2), self._cross_value())
        positions[:, self.index] = [item.value for item in items]
        centers = system._data.forward(positions)
        local[:, :, :2] += centers[:, None, :]
        placed = system.frame.mapping.forward(local.reshape(-1, 3)).reshape(local.shape)
        previous = self._tick_leaves if level == "major" else self._minor_leaves
        current: dict[object, TickLeaf] = {}
        for item, outline, points in zip(items, local, placed, strict=True):
            leaf = previous.get(item.key)
            if leaf is None:
                if self._pool is not None and not self._pool.building:
                    leaf = self._pool._take(self, level)
                    if leaf is None:
                        continue
                    leaf._cache = points
                    previous[item.key] = leaf
                else:
                    leaf = TickLeaf(points, system)
                    leaf.match_style(self.line)
                    leaf.set_stroke(
                        color=style.get("color", leaf.get_color()),
                        width=style.get("width", self._default_width(level)),
                    )
            else:
                leaf._cache = points
            leaf._axis_local = outline
            current[item.key] = leaf
        if self._pool is None:
            for key in previous.keys() - current.keys():
                previous[key]._cache = np.empty((0, 3))
            retained = current
        else:
            retained = {**previous, **current}
        if level == "major":
            self._tick_leaves = retained
            self._ticks._replace(current if self.include_ticks else {})
        else:
            self._minor_leaves = retained
            self._minor_ticks._replace(current if self.include_ticks else {})
            if current and self._minor_ticks not in self.submobjects:
                self.add(self._minor_ticks)

    def _regenerate(self) -> None:
        system = self._system
        system._sync_data()
        system._syncing = True
        try:
            self._configure()
            system._configure_grid()
        finally:
            system._syncing = False

    def set_locator(self, locator: object, minor: object = None) -> Self:
        """Replace the tick generators and regenerate keyed decorations.

        Parameters
        ----------
        locator, minor
            Locator protocol objects or two-endpoint callables; None disables minors.
        """
        major = as_locator(locator)
        minor_locator = None if minor is None else as_locator(minor)
        self.locator, self.minor_locator = major, minor_locator
        self._explicit, self._tick_mode = None, "add"
        self._regenerate()
        return self

    def set_formatter(self, formatter: object) -> Self:
        """Relabel existing number objects using a formatter or callable.

        Parameters
        ----------
        formatter
            Whole-list formatter or a per-value callable.
        """
        self.formatter = as_formatter(formatter)
        self._formatter_custom = True
        self._system._sync_data()
        self._configure_numbers()
        return self

    def set_ticks(
        self,
        entries: Iterable[float | tuple[object, ...]],
        mode: Literal["replace", "add"] = "replace",
    ) -> Self:
        """Replace or supplement generated ticks with fixed entries.

        Parameters
        ----------
        entries
            Values or tuples of value, label and optional tick level.
        mode
            Replace generated ticks or add entries, overriding matching keys.
        """
        if mode not in ("replace", "add"):
            raise ValueError("mode must be replace or add")
        fixed = FixedLocator(entries)
        if mode == "replace":
            self.locator = fixed
            self.minor_locator = (
                fixed.minor
                if any(item.level == "minor" for item in fixed.entries)
                else None
            )
        self._explicit, self._tick_mode = fixed, mode
        self._regenerate()
        return self

    def set_tick_style(
        self,
        level: Level = "major",
        *,
        direction: TickDirection | None = None,
        length: float | None = None,
        width: float | None = None,
        color: ParsableManimColor | None = None,
    ) -> Self:
        """Style one tick level, measuring length as its full scene length.

        A minor level takes the major level's direction until its own is set, half its
        length and three quarters of its width.

        Parameters
        ----------
        level
            Major or minor ticks.
        direction
            Both sides of the line, toward the interior, or toward the exterior.
        length, width, color
            Total tick length, native stroke width and native colour.
        """
        if level not in ("major", "minor"):
            raise ValueError("level must be major or minor")
        if direction is not None and not isinstance(direction, TickDirection):
            raise TypeError("direction must be a TickDirection")
        options: dict[str, Any] = {}
        for name, value in (("length", length), ("width", width)):
            if value is not None:
                checked = _finite(value, name)
                if checked < 0:
                    raise ValueError(f"{name} must be nonnegative")
                options[name] = checked
        if direction is not None:
            options["direction"] = direction
        if color is not None:
            options["color"] = color
        self._tick_styles[level].update(options)
        leaves = self._tick_leaves if level == "major" else self._minor_leaves
        for leaf in leaves.values():
            leaf.set_stroke(
                color=leaf.get_color() if color is None else color, width=width
            )
        if level == "major" and "width" not in self._tick_styles["minor"]:
            for leaf in self._minor_leaves.values():
                leaf.set_stroke(width=self._default_width("minor"))
        self._regenerate()
        return self

    def _default_width(self, level: Level) -> float | None:
        """Return an unset width: the line's for major, 3/4 of major's for minor."""
        if level == "major":
            return None
        major = self._tick_styles["major"].get("width", self.line.get_stroke_width())
        return 0.75 * float(major)

    def set_position(
        self, where: str | float = "origin", *, fraction: float | None = None
    ) -> Self:
        """Move only this axis's decoration across the other coordinate range.

        Parameters
        ----------
        where
            Origin, an appropriate border name, or a data value of the other axis.
        fraction
            Optional fraction of the other axis's transformed range, from zero to one.
        """
        if isinstance(where, str):
            sides = ("bottom", "top") if self.index == 0 else ("left", "right")
            _choice(where, "where", ("origin", *sides))
        else:
            where = _finite(where, "where")
            other = self._system.get_axis(1 - self.index)
            if not np.isfinite(other._scale.forward(where)).all():
                raise ValueError("where must be inside the other scale's domain")
        if fraction is not None:
            fraction = _finite(fraction, "fraction")
            if not 0 <= fraction <= 1:
                raise ValueError("fraction must be between zero and one")
        self._position, self._position_fraction = where, fraction
        self._regenerate()
        self._system.get_axis(1 - self.index)._regenerate()
        return self

    def set_tips(
        self, start: bool = False, end: bool = True, *, tick_under_tip: bool = False
    ) -> Self:
        """Show tips at either endpoint without changing the data mapping.

        As in Manim, the tick and the number at an end with a tip are left out.

        Parameters
        ----------
        start, end
            Whether each endpoint carries an arrow tip.
        tick_under_tip
            Keep the tick and the number at an end with a tip.
        """
        if not all(isinstance(flag, bool) for flag in (start, end, tick_under_tip)):
            raise TypeError("start, end and tick_under_tip must be bool")
        self.tick_under_tip = tick_under_tip
        if self._tip_reference is None:
            template = NumberLine(
                (0, self._reference_length, 1),
                length=self._reference_length,
                include_ticks=False,
                include_tip=True,
                tip_shape=self._config.get("tip_shape"),
                tip_width=self._native.tip_width,
                tip_height=self._native.tip_height,
            )
            template.rotate(self.index * np.pi / 2)
            template.shift((self._start_reference + self._end_reference) / 2)
            self._tip_reference = template.tip.points.copy()
        center = (self._start_reference + self._end_reference) / 2
        self._tip_start_reference = 2 * center - self._tip_reference
        # Arrow tips start at their point; the base is the farthest axial inset.
        unit = (self._end_reference - self._start_reference) / self._reference_length
        inset = float(np.max((self._end_reference - self._tip_reference) @ unit))
        endpoints = np.array(
            [
                self._start_reference + (inset * unit if start else 0),
                self._end_reference - (inset * unit if end else 0),
            ]
        )
        self._line_reference = endpoints[0] + np.linspace(0, 1, 4)[:, None] * (
            endpoints[1] - endpoints[0]
        )
        for attr, visible, reference in (
            ("tip", end, self._tip_reference),
            ("tip_start", start, self._tip_start_reference),
        ):
            leaf = getattr(self, attr)
            if visible and leaf is None:
                leaf = TipLeaf(reference, self._system)
                leaf.set_fill(self.line.get_color(), opacity=1).set_stroke(
                    self.line.get_color(), width=self.line.get_stroke_width()
                )
                setattr(self, attr, leaf)
                self.add(leaf)
            elif not visible and leaf is not None:
                self.remove(leaf)
                setattr(self, attr, None)
        self.include_tip = end
        self._regenerate()
        return self

    def mirror(self) -> Axis:
        """Return an unlabelled, opposite-side axis sharing this axis's data."""
        system = self._system
        system._sync_data()
        mirror = Axis(
            system,
            self.index,
            self.range.value.tolist(),
            self._native,
            self._scale,
            self.locator,
            self.minor_locator,
            self._config,
        )
        mirror.__dict__["__manim_plots_parameter_range"] = self.range
        mirror._range_parameter = self.range
        mirror._mirror_of = self
        mirror._line_reference = self._line_reference.copy()
        mirror._tip_reference = (
            None if self._tip_reference is None else self._tip_reference.copy()
        )
        mirror.include_numbers = False
        mirror.line.match_style(self.line)
        self._mirrors.append(mirror)
        self.add(mirror)
        self._regenerate()
        return mirror

    def set_grid(
        self, level: Level = "major", visible: bool = True, **style: Unpack[_VMStyle]
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
        normalized: dict[str, Any] = dict(style)
        color = normalized.pop("color", None)
        if color is not None:
            normalized.setdefault("stroke_color", color)
            normalized.setdefault("fill_color", color)
        self._grid_styles.setdefault(level, {}).update(normalized)
        for leaf in self._grid_leaves.values():
            if leaf.level == level:
                leaf.set_style(**self._grid_styles[level])
        self._system._sync_data()
        self._system._configure_grid()
        return self

    def _configure_grid(self) -> None:
        if not self._grid_visible:
            return
        system = self._system
        other = system.get_axis(1 - self.index)
        crossing = other._cross_value()
        items = [
            item
            for item in (self._tick_items() if self._pool is None else self._items)
            if self._grid_visible.get(item.level, False)
            and not np.isclose(item.value, crossing, rtol=1e-12, atol=0)
        ]
        endpoints = np.zeros((len(items), 2, 2))
        endpoints[:, :, self.index] = np.array([item.value for item in items])[:, None]
        endpoints[:, :, 1 - self.index] = other.range.value
        local = system._data.forward(endpoints.reshape(-1, 2)).reshape(-1, 2, 2)
        points = local[:, :1] + np.linspace(0, 1, 4)[None, :, None] * (
            local[:, 1:] - local[:, :1]
        )
        placed = system.frame.mapping.forward(points.reshape(-1, 2)).reshape(-1, 4, 3)
        current: dict[object, GridLeaf] = {}
        for item, outline in zip(items, placed, strict=True):
            key = (item.level, item.key)
            leaf = self._grid_leaves.get(key)
            if leaf is None:
                leaf = GridLeaf(outline, system)
                leaf.set_style(**self._grid_styles.get(item.level, {}))
            else:
                leaf._cache = outline
            leaf.level, leaf.value = item.level, item.value
            current[key] = leaf
        if self._pool is None:
            for old_key in self._grid_leaves.keys() - current.keys():
                self._grid_leaves[old_key]._cache = np.empty((0, 3))
            self._grid_leaves = current
        else:
            self._grid_leaves.update(current)
            for grid_key, leaf in self._grid_leaves.items():
                self._pool._show(
                    leaf, self._pool._opacity(grid_key) if grid_key in current else 0.0
                )
        self._grid._replace(current)
        if self._grid not in self.submobjects:
            self.add(self._grid)

    def set_label_style(
        self,
        *,
        rotation: float = 0.0,
        offset: ArrayLike = (0, 0),
        justify: str = "center",
        overlap: str = "hide",
    ) -> Self:
        """Set label rotation, local scene offsets, justification and overlap.

        Parameters
        ----------
        rotation
            Angle in radians relative to the axis's initial label orientation.
        offset
            Scene distances along and across the axis.
        justify
            Center, left or right edge of the label at its anchor.
        overlap
            Hide later overlaps, drop alternating labels, or rotate by 45 degrees.
        """
        checked_rotation = _finite(rotation, "rotation")
        checked_offset = _offset(offset)
        checked_justify = _choice(justify, "justify", ("center", "left", "right"))
        checked_overlap = _choice(overlap, "overlap", ("hide", "drop", "rotate"))
        self.rotation, self.offset = checked_rotation, checked_offset
        self.justify, self.overlap = checked_justify, checked_overlap
        self._regenerate()
        return self

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
        return (
            self.line.get_start()
            if self.tip_start is None
            else self.tip_start.get_start()
        )

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
        """Return the major tick values, without the one under a tip."""
        self._system._sync_data()
        return np.array(
            [
                item.value
                for item in self._drawn_items()
                if item.level == "major" and (item.value != 0 or not self._hides_zero())
            ]
        )

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
            self._default_exclusion = False
        self._number_options = dict(kwargs)
        if font_size is not None:
            self._number_options["font_size"] = font_size
        self._configure_numbers()
        if self.numbers not in self.submobjects:
            self.add(self.numbers)
        return self

    def _configure_numbers(self) -> None:
        _configure_numbers(self)

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
        _configure_labels(self)
