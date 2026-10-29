"""Axis containers and versioned ranges, with library-owned decoration leaves."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NoReturn, Self

import numpy as np
from manim import NumberLine, VGroup
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.params import Param, Parameter
from manim_plots.core.scales import LinearScale
from manim_plots.core.ticks import MultipleLocator, axis_ticks
from manim_plots.mobjects.leaves import AxisLine, TickLeaf, TipLeaf

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


class Axis(VGroup):
    """Group a line, major ticks and an optional tip around a range parameter.

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
    """

    range: Param[FloatArray] = Param((-1.0, 1.0), validate=_range)

    def __init__(
        self,
        system: CartesianAxes,
        index: int,
        limits: Sequence[float],
        native: NumberLine,
    ) -> None:
        self._system = system
        self.index = index
        self.range = limits
        self._range_parameter = self.range
        self.locator = MultipleLocator(float(limits[2]) if len(limits) == 3 else 1.0)
        self._scale = LinearScale()
        self._range_seen = self.range.version
        self._native = native
        self._line_reference = native.points.copy()
        self._crossing_reference = native.number_to_point(0).copy()
        tick = native.get_tick(0, native.tick_size)
        self._tick_reference = tick.points - self._crossing_reference
        self._tip_reference = native.tip.points.copy() if native.has_tip() else None
        self._tick_leaves: dict[object, TickLeaf] = {}
        self.line = AxisLine(native.points, system)
        self.line.match_style(native, family=False)
        self.ticks = VGroup()
        self.tip: TipLeaf | None = None
        if native.has_tip():
            self.tip = TipLeaf(native.tip.points, system)
            self.tip.match_style(native.tip)
        super().__init__(
            self.line, self.ticks, *(() if self.tip is None else (self.tip,))
        )
        self._configure_ticks(native)

    @property
    def ticks(self) -> VGroup:
        """Return the current major tick family, updating a changed range lazily."""
        self._system._sync_data()
        return self._ticks

    @ticks.setter
    def ticks(self, value: VGroup) -> None:
        self._ticks = value

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
            if value == 0:
                continue
            key = self.locator.key(float(value))
            template = native.get_tick(float(value), native.tick_size)
            leaf = previous.get(key)
            if leaf is None:
                leaf = TickLeaf(template.points, self._system)
                leaf.match_style(template)
            else:
                leaf._cache = template.points.copy()
            current[key] = leaf
        self._tick_leaves = current
        self.ticks.submobjects = list(current.values())

    def _configure(self) -> None:
        system = self._system
        limits = self.range.value
        other = system.y_axis if self.index == 0 else system.x_axis
        cross = float(np.clip(0, min(other.range.value), max(other.range.value)))
        coords = np.zeros((1, 2))
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
            if item.value != 0
        )
        positions = np.full((len(items), 2), cross)
        positions[:, self.index] = [item.value for item in items]
        centers = system._data.forward(positions)
        local = np.tile(self._tick_reference, (len(items), 1, 1))
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
        self._tick_leaves = current
        self.ticks.submobjects = list(current.values())
        self._range_seen = self.range.version
