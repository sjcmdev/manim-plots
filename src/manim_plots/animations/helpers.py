"""Transitions between nested Riemann partitions."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, cast

import numpy as np

from manim_plots.core.params import Parameter
from manim_plots.mobjects.helpers import (
    FilledRegion,
    _Binding,
    _RegionBinding,
    _RiemannGroup,
)

from ._base import Presentation, window


class RefineRiemann(Presentation):
    """Change a Riemann partition through its nested parent intervals.

    Parameters
    ----------
    rectangles, dx, lag_ratio, order, **kwargs
        Bound rectangles, target step, parent stagger, interval key and Manim options.
    """

    def __init__(
        self,
        rectangles: _RiemannGroup,
        dx: float,
        *,
        lag_ratio: float = 0,
        order: str | Callable[[tuple[float, float]], Any] = "data",
        **kwargs: object,
    ) -> None:
        if not isinstance(rectangles, _RiemannGroup):
            raise TypeError("rectangles must be bound Riemann rectangles")
        if not np.isfinite(dx) or dx <= 0:
            raise ValueError("dx must be finite and positive")
        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        if order != "data" and not callable(order):
            raise ValueError("order must be data or an interval key")
        self.rectangles, self.dx, self.order = rectangles, dx, order
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(
            rectangles, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs)
        )

    def begin(self) -> None:
        """Resolve the current partition and acquire its derivation."""
        group = self.rectangles
        binding = group._binding
        binding.poll()
        binding.ensure()
        self._old_dx = binding.number("dx")
        ratio = max(self.dx, self._old_dx) / min(self.dx, self._old_dx)
        if not np.isclose(ratio, round(ratio)):
            raise ValueError("Riemann partitions must be nested")
        if "_topology_writer" in binding.__dict__:
            raise ValueError("concurrent Riemann writers conflict")
        self._binding = binding
        self._derive = binding.derive
        self._parameter = binding.parameters["dx"]
        self._styles = [r.get_style() for r in group]
        self._progress = 0.0
        binding.__dict__["_topology_writer"] = self
        binding.derive = self._transition
        super().begin()

    def _partition(self, dx: float) -> dict[str, Any]:
        binding = self._binding
        parameter = binding.parameters["dx"]
        binding.parameters["dx"] = Parameter(dx, name="dx")
        try:
            self._derive(binding)
            return copy.deepcopy(binding.boundaries)
        finally:
            binding.parameters["dx"] = parameter

    def _transition(self, base: _Binding) -> None:
        binding = cast(_RegionBinding, base)
        coarse = max(self.dx, self._old_dx)
        fine = min(self.dx, self._old_dx)
        parents = self._partition(coarse)
        children = self._partition(fine)
        count = len(parents)
        key = self.order
        # Interval order is semantic even when widths are drawn with an overlap.
        intervals = [(i * coarse, (i + 1) * coarse) for i in range(count)]
        if parents:
            start = float(binding.system._data.inverse(parents["0"][0][0])[0, 0])
            intervals = [(a + start, b + start) for a, b in intervals]
        order = (
            sorted(range(count), key=lambda i: key(intervals[i]))
            if callable(key)
            else list(range(count))
        )
        ranks = {parent: rank for rank, parent in enumerate(order)}
        factor = round(coarse / fine)
        for j, pieces in enumerate(children.values()):
            parent = min(j // factor, count - 1)
            p = self.rate_func(
                window(self._progress, ranks[parent], count, self.lag_ratio)
            )
            if self.dx > self._old_dx:
                p = 1 - p
            top, bottom = pieces[0]
            old_top, old_bottom = parents[str(parent)][0]
            top[:, 1] = (1 - p) * old_top[0, 1] + p * top[:, 1]
            bottom[:, 1] = (1 - p) * old_bottom[0, 1] + p * bottom[:, 1]
        binding.boundaries = children

    def interpolate_mobject(self, alpha: float) -> None:
        """Derive child heights from the absolute parent progress."""
        self._progress = alpha
        binding = self._binding
        binding._seen = None
        binding.ensure()
        self.rectangles._ensure_regions()
        factor = round(max(self.dx, self._old_dx) / min(self.dx, self._old_dx))
        for i, member in enumerate(self.rectangles):
            rect = cast(FilledRegion, member)
            source = i // factor if self.dx < self._old_dx else i
            rect.set_style(**self._styles[min(source, len(self._styles) - 1)])
            rect._binding_seen = -1
            rect.refresh()

    def restore(self) -> None:
        """Commit the target step while retaining an existing tracker input."""
        binding = self._binding
        if binding.__dict__.get("_topology_writer") is not self:
            return
        binding.derive = self._derive
        binding.__dict__.pop("_topology_writer")
        self.rectangles._follow_dx = True
        tracker = self._parameter.tracker
        setter = getattr(tracker, "set_value", None)
        if callable(setter):
            setter(self.dx)
            self._parameter.poll()
        else:
            self._parameter.value = self.dx
        binding._seen = None
        binding.ensure()
        self.rectangles._ensure_regions()
        for rect in self.rectangles:
            rect.refresh()
