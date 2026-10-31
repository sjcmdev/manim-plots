"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from typing import Any, cast

import numpy as np
from manim import (
    YELLOW,
    Animation,
    AnimationGroup,
    Arc,
    Create,
    FadeIn,
    FadeOut,
    Group,
    Indicate,
    Mobject,
    Scene,
    VGroup,
    VMobject,
)
from manim.utils.color import ParsableManimColor

import manim_plots as mp
from manim_plots.mobjects.axis import Axis
from manim_plots.mobjects.leaves import FrameLeaf
from manim_plots.mobjects.system import CartesianAxes

from ._base import flags
from ._spatial import _Spatial


class SweepPolar(_Spatial):
    """Reveal polar decorations over a directed source-angle interval.

    Parameters
    ----------
    ax, start_angle, angle, lag_ratio, reverse, remover, **kwargs
        Polar system, angular interval, ring stagger, playback flags and native options.
    """

    def __init__(
        self,
        ax: mp.PolarPlane | mp.PolarAxes,
        *,
        start_angle: float = 0,
        angle: float = 2 * np.pi,
        lag_ratio: float = 0,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.polar import PolarAxes, PolarPlane

        if not isinstance(ax, (PolarAxes, PolarPlane)):
            raise TypeError("ax must be PolarPlane or PolarAxes")
        if not np.isfinite([start_angle, angle]).all():
            raise ValueError("angular options must be finite")
        self.ax, self.start_angle, self.angle = ax, start_angle, angle
        self._involved_system = ax
        parts = VGroup(*(part for part in ax.submobjects if part is not ax.frame))
        super().__init__(
            parts, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def _setup_scene(self, scene: Scene) -> None:
        if self.is_introducer():
            scene.add(self.ax)

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Restore decorations and remove only the system root when requested.

        Parameters
        ----------
        scene
            Scene containing the system and independently added plots.
        """
        remove = self.remover
        self.remover = False
        try:
            super().clean_up_from_scene(scene)
        finally:
            self.remover = remove
        if remove:
            scene.remove(self.ax)
        else:
            scene.add(self.ax)

    def _reached(self, theta: float, progress: float) -> bool:
        delta = ((theta - self.start_angle) * (1 if self.angle >= 0 else -1)) % (
            2 * np.pi
        )
        return bool(progress > 0 and delta <= abs(self.angle) * progress + 1e-10)

    def _draw(self) -> None:
        ax = cast(Any, self.ax)
        ax._sync_data()
        rings = sorted(ax.circles, key=lambda ring: ring.value)
        origin = ax.get_origin()
        for i, ring in enumerate(rings):
            p = self._progress(i, len(rings))
            arc = Arc(start_angle=self.start_angle, angle=p * self.angle)
            x = ax.polar_to_point(ring.value, 0) - origin
            y = ax.polar_to_point(ring.value, np.pi / 2) - origin
            ring.points = origin + arc.points[:, :1] * x + arc.points[:, 1:2] * y
            self._visibility(ring, float(p > 0))
        p = self._progress(len(rings) - 1, len(rings)) if rings else self._progress()
        for spoke in ax.spokes:
            spoke.points = ax.frame.mapping.forward(ax._spoke(spoke.value))
            self._visibility(spoke, float(self._reached(spoke.value, p)))
        labels = ax.__dict__.get("coordinate_labels")
        if labels is not None:
            for index, group in enumerate((labels[0], labels[1])):
                for label in group:
                    value = label._anchor.__defaults__[0]
                    if index == 1:
                        shown = self._reached(value, p)
                    else:
                        rank = next(
                            (i for i, ring in enumerate(rings) if ring.value >= value),
                            0,
                        )
                        shown = self._progress(rank, len(rings)) > 0
                    self._visibility(label, float(shown))

    def restore(self) -> None:
        """Restore the complete bound decorations and independent plots."""
        super().restore()
        self.ax._configure_grid()


class _FadeInParts(FadeIn):
    def get_all_families_zipped(self) -> Iterable[tuple[Mobject, ...]]:
        # NumberLabel parents carry observable style despite having no points.
        return zip(
            *(
                m.get_family()
                for m in (self.mobject, self.starting_mobject, self.target_copy)
            ),
            strict=True,
        )


class BuildAxes(AnimationGroup):
    """Build axis lines, ticks, numbers, then labels and grid in stages.

    Parameters
    ----------
    ax, lag_ratio, **kwargs
        Coordinate system, stage stagger and native group options.
    """

    def __init__(
        self,
        ax: CartesianAxes,
        lag_ratio: float = 0.5,
        *,
        stages: Iterable[str] | None = None,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        known = {
            "lines",
            "tips",
            "ticks",
            "minor_ticks",
            "numbers",
            "labels",
            "grid",
            "panes",
            "breaks",
        }
        if stages is not None and any(stage not in known for stage in stages):
            raise ValueError("unknown stages")
        self.ax = ax
        flags(reverse, remover, kwargs)
        lines = VGroup(
            *(
                part
                for axis in ax._ranges
                for part in (axis.line, axis.tip)
                if part is not None
            )
        )
        ticks = VGroup(*(axis.ticks for axis in ax._ranges))
        numbers = VGroup(*(axis.numbers for axis in ax._ranges))
        labels = VGroup(
            *(part for axis in ax._ranges for part in (axis.labels, axis.grid))
        )
        children = (
            [
                FadeOut(labels),
                FadeOut(numbers),
                Create(ticks, reverse_rate_function=True, introducer=False),
                Create(lines, reverse_rate_function=True, introducer=False),
            ]
            if reverse
            else [Create(lines), Create(ticks), _FadeInParts(numbers), FadeIn(labels)]
        )
        super().__init__(
            *children,
            group=ax,
            lag_ratio=lag_ratio,
            **cast(dict[str, Any], kwargs),
        )

    def _setup_scene(self, scene: Scene) -> None:
        if self.introducer:
            scene.add(self.ax)

    def begin(self) -> None:
        """Capture exact decoration styles and geometry at playback."""
        self._canonical = [
            (m, m.copy()) for m in self.ax.get_family() if isinstance(m, VMobject)
        ]
        super().begin()

    def _restore(self) -> None:
        for leaf, original in self._canonical:
            leaf.set_points(original.points.copy())
            leaf.match_style(original, family=False)
            if hasattr(type(leaf), "refresh"):
                leaf.refresh()

    def finish(self) -> None:
        """Return all decorations to canonical bound state."""
        super().finish()
        self._restore()

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Remove the axes container rather than temporary stage groups.

        Parameters
        ----------
        scene
            Scene playing this construction.
        """
        Animation.clean_up_from_scene(self, scene)
        self._restore()


class HighlightTick(Indicate):
    """Indicate a keyed tick and its number together.

    Parameters
    ----------
    axis, value, color, scale_factor, **kwargs
        Axis, tick value, highlight colour, size factor and native options.
    """

    def __init__(
        self,
        axis: Axis,
        value: float,
        color: ParsableManimColor = YELLOW,
        scale_factor: float = 1.5,
        **kwargs: object,
    ) -> None:
        tick = axis.ticks.at(value)
        parts: list[Mobject] = [tick]
        with suppress(KeyError):
            parts.append(axis.numbers.at(value))
        super().__init__(
            Group(*parts),
            color=color,
            scale_factor=scale_factor,
            **cast(dict[str, Any], kwargs),
        )


class DrawAxes(Create):
    """Create visible axis leaves with Manim's native family timing.

    Parameters
    ----------
    ax
        Coordinate system; registered artists are left untouched.
    **kwargs
        Native Create animation options.
    """

    def __init__(
        self,
        ax: CartesianAxes,
        *,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(ax, CartesianAxes):
            raise TypeError("ax must be a CartesianAxes")
        self.ax = ax
        flags(reverse, remover, kwargs)
        kwargs["reverse_rate_function"] = reverse
        super().__init__(ax, **cast(dict[str, Any], kwargs))

    def _setup_scene(self, scene: Scene) -> None:
        if self.introducer:
            scene.add(self.ax)

    def begin(self) -> None:
        """Capture canonical decorations before native partial creation."""
        self._canonical = [
            (m, m.copy()) for m in self.ax.get_family() if isinstance(m, VMobject)
        ]
        super().begin()

    def finish(self) -> None:
        """Restore the original bound decorations."""
        super().finish()
        for leaf, original in self._canonical:
            leaf.set_points(original.points.copy())
            leaf.match_style(original, family=False)
            if hasattr(type(leaf), "refresh"):
                leaf.refresh()

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Remove the original axes container when requested.

        Parameters
        ----------
        scene
            Scene playing this construction.
        """
        if self.remover:
            scene.remove(self.ax)

    def get_all_families_zipped(self) -> Iterable[tuple[Mobject, ...]]:
        """Use native creation timing over the visible decoration leaves."""
        return zip(
            *(
                [
                    leaf
                    for leaf in mob.family_members_with_points()
                    if isinstance(leaf, VMobject) and not isinstance(leaf, FrameLeaf)
                ]
                for mob in (self.mobject, self.starting_mobject)
            ),
            strict=True,
        )
