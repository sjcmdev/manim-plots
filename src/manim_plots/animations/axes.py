"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from typing import Any, cast

from manim import (
    YELLOW,
    Animation,
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    Group,
    Indicate,
    Mobject,
    Scene,
    Uncreate,
    VGroup,
    VMobject,
    linear,
)
from manim.utils.color import ParsableManimColor

from manim_plots.mobjects.axis import Axis
from manim_plots.mobjects.leaves import FrameLeaf
from manim_plots.mobjects.system import CartesianAxes

from ._base import flags


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
    stages
        Ordered stage names or tuples of simultaneous names; None keeps the
        existing lines/tips, ticks, numbers, labels/grid schedule.
    stage_animations
        Native animation factories keyed by stage name.
    reverse, remover
        Playback direction and independent scene removal.
    """

    def __init__(
        self,
        ax: CartesianAxes,
        lag_ratio: float = 0.5,
        *,
        stages: Iterable[str | tuple[str, ...]] | None = None,
        stage_animations: Mapping[str, Callable[[VGroup], Animation]] | None = None,
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
        selected = (
            list(stages)
            if stages is not None
            else [("lines", "tips"), "ticks", "numbers", ("labels", "grid")]
        )
        factories = dict(stage_animations or {})
        if any(
            name not in known
            for stage in selected
            for name in ((stage,) if isinstance(stage, str) else stage)
        ) or any(name not in known for name in factories):
            raise ValueError("unknown stage")
        self.ax = ax
        self._involved_system = ax
        flags(reverse, remover, kwargs)
        attributes = {"lines": "line", "tips": "tip", "breaks": "break_marks"}
        parts = {}
        for name in known:
            if name == "panes":
                pane = getattr(ax, "panes", None)
                parts[name] = VGroup() if pane is None else VGroup(pane)
            else:
                parts[name] = VGroup(
                    *(
                        part
                        for axis in ax._ranges
                        if (part := getattr(axis, attributes.get(name, name), None))
                        is not None
                    )
                )
        children: list[Animation] = []
        rate = cast(Callable[[float], float], kwargs.get("rate_func", linear))
        for stage in selected:
            animations = []
            for name in (stage,) if isinstance(stage, str) else stage:
                group = parts[name]
                if name in factories:
                    animation = factories[name](group)
                elif name in {"lines", "tips", "ticks", "minor_ticks", "breaks"}:
                    animation = (Uncreate if reverse else Create)(group, rate_func=rate)
                elif reverse:
                    animation = FadeOut(group, rate_func=rate)
                else:
                    animation = (_FadeInParts if name == "numbers" else FadeIn)(
                        group, rate_func=rate
                    )
                animations.append(animation)
            children.append(AnimationGroup(*animations, run_time=1))
        if stages is None and not factories:
            # Preserve the original native family order and timing for existing callers.
            lines = VGroup(
                *(
                    part
                    for axis in ax._ranges
                    for part in (axis.line, axis.tip)
                    if part is not None
                )
            )
            labels = VGroup(
                *(part for axis in ax._ranges for part in (axis.labels, axis.grid))
            )
            children = [
                (Uncreate if reverse else Create)(lines),
                (Uncreate if reverse else Create)(parts["ticks"]),
                FadeOut(parts["numbers"])
                if reverse
                else _FadeInParts(parts["numbers"]),
                FadeOut(labels) if reverse else FadeIn(labels),
            ]
        else:
            kwargs.pop("rate_func", None)
        if reverse:
            children.reverse()
        if not children:
            children = [Animation(ax)]
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
