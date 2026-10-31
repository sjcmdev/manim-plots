"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, cast

import numpy as np
from manim import (
    Animation,
    Group,
    Mobject,
    VGroup,
    linear,
)

from manim_plots.core import FloatArray

from ._spatial import _Spatial


class Flow(Animation):
    """Advect mobjects through a field without leaving an updater behind.

    Parameters
    ----------
    field
        ArrowVectorField or StreamLines supplying the data-space velocity.
    *mobjects
        Mobjects to advect for ``speed * run_time`` of field time; a plain
        VGroup or Group moves member by member, each along its own path.
    speed, pointwise
        Signed field time per second and pointwise movement mode.
    **kwargs
        Native Animation options; the default rate function is linear.
    """

    def __init__(
        self,
        field: ArrowVectorField | StreamLines,
        *mobjects: Mobject,
        speed: float = 1,
        pointwise: bool = False,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.helpers import _number

        self.field, self.targets = field, mobjects
        self.speed, self.pointwise = _number(speed, "speed"), pointwise
        self._last_time = 0.0
        kwargs.setdefault("rate_func", linear)
        super().__init__(Mobject().add(*mobjects), **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Start a fresh advection interval using Manim's animation lifecycle."""
        self._last_time = 0.0
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Advance targets by this frame's elapsed field time.

        Parameters
        ----------
        alpha
            Animation progress supplied by Manim.
        """
        current = self.rate_func(alpha) * self.run_time
        dt = (current - self._last_time) * self.speed
        self._last_time = current
        for mob in self.targets:
            for part in [mob] if self.pointwise else _members(mob):
                self.field.nudge(
                    part,
                    dt,
                    substeps=max(1, math.ceil(abs(dt) / 0.02)),
                    pointwise=self.pointwise,
                )


def _members(mob: Mobject) -> list[Mobject]:
    # A plain group is a collection: each member follows its own trajectory.
    if type(mob) in (VGroup, Group) and mob.submobjects:
        return [part for sub in mob.submobjects for part in _members(sub)]
    return [mob]


class GrowField(_Spatial):
    """Grow arrows about their canonical tails in a stable order.

    Parameters
    ----------
    field, order, lag_ratio, reverse, remover, **kwargs
        Bound field, sorting key, stagger, playback flags and native options.
    """

    def __init__(
        self,
        field: ArrowVectorField,
        *,
        order: str | Callable[[FloatArray, FloatArray], object] = "data",
        lag_ratio: float = 0.02,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not callable(order) and order not in ("data", "x", "y", "z", "value"):
            raise ValueError("unknown field order")
        self.field, self.order = field, order
        super().__init__(
            field, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def begin(self) -> None:
        """Resolve sorting from the current vector samples."""
        field = self.field
        field._binding.ensure()
        payload = field._grid()
        assert payload.values is not None
        coords, vectors = payload.coords[field._order], payload.values[field._order]
        self._arrows = field.arrows
        self._ordered = list(range(len(self._arrows)))
        if self.order != "data":

            def key(i: int) -> object:
                if callable(self.order):
                    return self.order(coords[i], vectors[i])
                if self.order == "value":
                    return float(np.linalg.norm(vectors[i]))
                dim = "xyz".index(self.order)
                return coords[i, dim] if dim < coords.shape[1] else 0

            self._ordered.sort(key=cast(Any, key))
        self._solid = (
            {
                leaf: leaf.points.copy()
                for arrow in self._arrows
                for leaf in arrow.get_family()
            }
            if field._arrow_kind == "3d"
            else {}
        )
        super().begin()

    def _draw(self) -> None:
        from manim_plots.mobjects.fields import _FieldPart

        field = self.field
        for leaf, points in self._solid.items():
            leaf.points = points.copy()
        field._binding.ensure()
        if self._solid:
            self._solid = {
                leaf: leaf.points.copy()
                for arrow in self._arrows
                for leaf in arrow.get_family()
            }
        for index, i in enumerate(self._ordered):
            arrow = self._arrows[i]
            progress = self._progress(index, len(self._ordered))
            if self._solid:
                tail = arrow.get_start().copy()
                for leaf in arrow.get_family():
                    leaf.points = tail + progress * (self._solid[leaf] - tail)
            else:
                parts = cast(list[_FieldPart], [arrow, *arrow.submobjects])
                local = field._binding.parts[str(i)]
                if not len(local):
                    continue
                tail = field.system.frame.mapping.forward(local[:1])[0]
                for part in parts:
                    points = field.system.frame.mapping.forward(
                        field._binding.parts[part._part]
                    )
                    part.points = tail + progress * (points - tail)

    def restore(self) -> None:
        """Restore all arrows without changing sources or bindings."""
        super().restore()
        for leaf, points in self._solid.items():
            leaf.points = points.copy()
        for part in self.field._parts:
            part.refresh()
        for part in self.field._tips:
            part.refresh()


# Import after the classes: the artist module re-exports Flow.
from manim_plots.mobjects.fields import ArrowVectorField, StreamLines  # noqa: E402
