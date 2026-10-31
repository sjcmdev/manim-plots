"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast

from manim import (
    Animation,
    Group,
    Mobject,
    VGroup,
    linear,
)

if TYPE_CHECKING:
    from manim_plots.mobjects.fields import ArrowVectorField, StreamLines


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
