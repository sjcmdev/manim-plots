"""Library-owned point buffers and the Manim side of the leaf lifecycle."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, NoReturn, Self, TypedDict, Unpack, cast

import numpy as np
from manim import Animation, Mobject, Scene, VMobject, config
from manim.constants import CapStyleType, LineJointType, RendererType
from manim.typing import Vector3DLike
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike
from PIL.Image import Image

from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import FRAME_NODES, Chain, FrameMap
from manim_plots.mobjects.context import (
    animation_context,
    buffer_write,
    moving_context,
)

if TYPE_CHECKING:
    from manim_plots.mobjects.system import CartesianAxes

_SIMULATING = False


class _VMStyle(TypedDict, total=False):
    color: ParsableManimColor
    fill_color: ParsableManimColor | None
    fill_opacity: float
    stroke_color: ParsableManimColor | None
    stroke_opacity: float
    stroke_width: float
    background_stroke_color: ParsableManimColor | None
    background_stroke_opacity: float
    background_stroke_width: float
    sheen_factor: float
    sheen_direction: Vector3DLike
    joint_type: LineJointType | None
    cap_style: CapStyleType
    close_new_points: bool
    pre_function_handle_to_anchor_scale_factor: float
    make_smooth_after_applying_functions: bool
    background_image: Image | str | None
    shade_in_3d: bool
    tolerance_for_point_equality: float
    n_points_per_cubic_curve: int
    name: str | None
    dim: int
    z_index: float


class _PlotOptions(_VMStyle, total=False):
    use_smoothing: bool
    discontinuities: Iterable[float] | None
    dt: float


class _ParametricOptions(_PlotOptions, total=False):
    t_range: Sequence[float]


def _reported_updaters(
    actual: list[Callable[..., Any]],
    system: CartesianAxes | None,
    leaf: Leaf | None = None,
) -> list[Callable[..., Any]]:
    if not actual or _synchronise not in actual:
        return actual
    moving = moving_context()
    if moving is not None and (
        system is None
        or not (
            system._needs_sync(moving)
            or (leaf is not None and leaf._needs_sync(moving))
        )
    ):
        return [u for u in actual if u is not _synchronise]
    return actual


def _synchronise(mobject: Mobject) -> None:
    system = cast("CartesianAxes | None", getattr(mobject, "_system", mobject))
    if system is not None:
        system._poll()
        if isinstance(mobject, Leaf):
            mobject._poll()


class Leaf(VMobject):
    """Expose a stable, writable cache to Manim.

    Parameters
    ----------
    points
        Initial cubic control points, if any.
    system
        Coordinate system that owns the leaf's mapping.
    **kwargs
        Native VMobject style options.

    Notes
    -----
    Animation ownership and detachment are reduced by core.lifecycle. Reads of a
    clean buffer take a fast path without allocating a lifecycle event.
    """

    def __init__(
        self,
        points: ArrayLike | None = None,
        system: CartesianAxes | None = None,
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        if config.renderer == RendererType.OPENGL:
            raise ValueError("Leaf requires the Cairo renderer")
        self._ready = False
        self._cache = np.empty((0, 3))
        self._system = system
        self._lifecycle = lc.Leaf()
        self._candidate: VMobject | None = None
        self._dirty = True
        self._own = Chain(())
        self._shape: FloatArray | None = None
        self._frozen_frame: FrameMap | None = None
        self._frame_seen = -1
        self._write_start: FloatArray | None = None
        self._empty_anchors: list[FloatArray] = []
        self._actual_updaters: list[Callable[..., Any]] = []
        super().__init__(**kwargs)
        if points is not None:
            self._cache = np.array(points, dtype=float, copy=True)
        self._ready = True

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Report the synchronisation updater to either Cairo query version."""
        return _reported_updaters(self._actual_updaters, self._system, self)

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._actual_updaters = value

    @property
    def points(self) -> FloatArray:
        """Return the cache itself, rebuilding derived geometry only when dirty."""
        if self._ready and not buffer_write():
            self._ensure()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)

    def _ensure(self) -> None:
        if self._system is not None and self._lifecycle.state is lc.State.ATTACHED:
            self._system._sync_data()

    def _poll(self) -> None:
        pass

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return False

    def _event(self, event: lc.Event) -> None:
        self._lifecycle, actions = lc.transition(self._lifecycle, event)
        for action in actions:
            kind = action.kind
            if kind is lc.Kind.MARK_DIRTY:
                self._dirty = True
            elif kind is lc.Kind.REBUILD:
                self._shape = None
                self._restore()
            elif kind is lc.Kind.REATTACH:
                self._shape = None
                self._dirty = True
                self._rebuild()
            elif kind in {lc.Kind.SHAPE_FROM_TARGET, lc.Kind.SHAPE_FROM_BUFFER}:
                target = action.ref
                points = target.points if isinstance(target, VMobject) else self._cache
                self._save_shape(points)
            elif kind is lc.Kind.ADOPT and isinstance(action.ref, Leaf):
                self._adopt(action.ref)

    def _rebuild(self) -> None:
        self._dirty = False

    def _restore(self) -> None:
        self._rebuild()

    def _save_shape(self, points: FloatArray) -> None:
        if self._system is None:
            self._cache = points.copy()
        else:
            self._shape = self._system.frame.mapping.inverse(points)
            self._cache = points.copy()
            self._frame_seen = self._system.frame.version

    def _adopt(self, other: Leaf) -> None:
        self._own = other._own
        self._shape = other._shape
        self.match_style(other)
        self._dirty = True

    def refresh(self) -> Self:
        """Reattach and regenerate this leaf from its current data."""
        self._dirty = True
        self._event(lc.Refresh())
        return self

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Open a Transform's transient section before native point alignment.

        Parameters
        ----------
        mobject
            Native alignment target.
        skip_point_alignment
            Forwarded to Manim's alignment implementation.
        """
        animation = animation_context(transform_only=True)
        if animation is not None:
            if animation.is_introducer() and self._lifecycle.state is lc.State.REMOVED:
                self.refresh()
            self._begin(animation)
        super().align_data(mobject, skip_point_alignment)
        if isinstance(mobject, VMobject):
            self._candidate = mobject.copy()
        return self

    def _begin(self, animation: Animation) -> None:
        if animation in self._lifecycle.owners:
            return
        self._ensure()
        self._event(lc.Begin(animation, animation.is_introducer()))

    def suspend_updating(self, recursive: bool = True) -> Self:
        """Give the animation ownership of the writable buffer.

        Parameters
        ----------
        recursive
            Suspend the whole family when true.
        """
        animation = animation_context()
        if animation is not None:
            reattach = animation.is_introducer() and self._lifecycle.state in {
                lc.State.REMOVED,
                lc.State.SHAPED,
            }
            self._begin(animation)
            if reattach:
                # Manim annotates this Cairo attribute as an OpenGL-only mobject.
                cast(
                    Any, animation
                ).starting_mobject = animation.create_starting_mobject()
                if hasattr(animation, "get_outline"):
                    cast(Any, animation).outline = animation.get_outline()
        else:
            self._event(lc.SuspendUpdating())
        super().suspend_updating(recursive)
        return self

    def resume_updating(self, recursive: bool = True) -> Self:
        """Finish ownership, adopting a target or retaining Manim's buffer.

        Parameters
        ----------
        recursive
            Resume the whole family when true.
        """
        animation = animation_context(finishing=True)
        if animation is not None and animation in self._lifecycle.owners:
            ending, target = lc.Ending.START, None
            candidate = self._candidate
            if candidate is not None and self._same_points(candidate):
                ending = (
                    lc.Ending.ARTIST if isinstance(candidate, Leaf) else lc.Ending.PLAIN
                )
                target = candidate
            else:
                family = cast(
                    Mobject, animation.starting_mobject
                ).family_members_with_points()
                live = cast(Mobject, animation.mobject).family_members_with_points()
                start = next(
                    (s for s, m in zip(family, live, strict=False) if m is self), None
                )
                if start is not None and not self._same_points(start):
                    ending = lc.Ending.ELSEWHERE
            self._event(lc.Finish(animation, ending, target, animation.is_remover()))
            self._candidate = None
        super().resume_updating(recursive)
        return self

    def _same_points(self, other: Mobject) -> bool:
        return bool(
            self._cache.shape == other.points.shape
            and np.allclose(self._cache, other.points, atol=1e-9, rtol=0)
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        _, actions = lc.transition(self._lifecycle, lc.Copy())
        rebuilding = actions[0].kind is lc.Kind.COPY_REBUILT
        for key, value in self.__dict__.items():
            if key == "_system":
                result.__dict__[key] = memo.get(id(value), value)
            elif key in {
                "source",
                "_geometry_payload",
                "_own",
                "_mapping",
            }:
                result.__dict__[key] = value
            elif key in {"_candidate", "_frozen_frame"}:
                result.__dict__[key] = None
            elif key == "_lifecycle":
                result.__dict__[key] = lc.Leaf() if rebuilding else lc.Leaf(value.state)
            elif key == "_suspensions":
                result.__dict__[key] = []
            elif key == "parameters":
                result.__dict__[key] = {
                    name: copy.copy(parameter) for name, parameter in value.items()
                }
            else:
                result.__dict__[key] = copy.deepcopy(value, memo)
        if rebuilding:
            result._restore()
        return result


class AxisLine(Leaf):
    """Carry the control points of one axis line."""


class TickLeaf(Leaf):
    """Carry one major tick's cubic path."""


class TipLeaf(Leaf):
    """Carry a filled native arrow tip's cubic path."""


class FrameLeaf(Leaf):
    """Carry an invisible lattice whose positions define the system map.

    Parameters
    ----------
    lower, upper
        Local viewport corners.
    system
        Owning coordinate system.
    """

    def __init__(
        self, lower: FloatArray, upper: FloatArray, system: CartesianAxes
    ) -> None:
        self.lower, self.upper = lower.copy(), upper.copy()
        self.version = 0
        self._map_version = -1
        self._mapping: FrameMap | None = None
        self._suspensions: list[
            tuple[Animation, FrameMap | None, frozenset[Mobject]]
        ] = []
        nodes = FrameMap.lattice(lower, upper, FRAME_NODES)
        super().__init__(np.repeat(nodes, 4, axis=0), system, stroke_width=0)
        self.set_fill(opacity=0)
        self.set_stroke(opacity=0)

    @property
    def points(self) -> FloatArray:
        """Return the native lattice buffer without deriving geometry."""
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)
        self.version += 1

    @property
    def mapping(self) -> FrameMap:
        """Return the cached core map for the current lattice."""
        if self._map_version != self.version or self._mapping is None:
            self._mapping = FrameMap(self.lower, self.upper, self._cache[::4])
            self._map_version = self.version
        return self._mapping

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Align native lattice buffers without opening derived-leaf ownership.

        Parameters
        ----------
        mobject
            Native alignment target.
        skip_point_alignment
            Forwarded to Manim.
        """
        VMobject.align_data(self, mobject, skip_point_alignment)
        return self

    def set_fill(
        self,
        color: ParsableManimColor | None = None,
        opacity: float | None = None,
        family: bool = True,
    ) -> Self:
        """Keep the hidden lattice's fill transparent.

        Parameters
        ----------
        color, opacity, family
            Native style arguments; opacity is always zero.
        """
        super().set_fill(color, 0, family)
        return self

    def set_stroke(
        self,
        color: ParsableManimColor | None = None,
        width: float | None = None,
        opacity: float | None = None,
        background: bool = False,
        family: bool = True,
    ) -> Self:
        """Keep both hidden strokes transparent.

        Parameters
        ----------
        color, width, opacity, background, family
            Native style arguments; width and opacity are always zero.
        """
        super().set_stroke(cast(ParsableManimColor, color), 0, 0, background, family)
        return self

    def interpolate_color(
        self, mobject1: Mobject, mobject2: Mobject, alpha: float
    ) -> Self:
        """Interpolate style while preserving invisibility.

        Parameters
        ----------
        mobject1, mobject2, alpha
            Native interpolation endpoints and fraction.
        """
        super().interpolate_color(
            cast(VMobject, mobject1), cast(VMobject, mobject2), alpha
        )
        self.set_fill(opacity=0)
        self.set_stroke(opacity=0)
        self.set_stroke(opacity=0, background=True)
        return self

    def pointwise_become_partial(self, vmobject: VMobject, a: float, b: float) -> Self:
        """Ignore partial drawing of the hidden frame.

        Parameters
        ----------
        vmobject, a, b
            Native source and interval, intentionally unused.
        """
        return self

    def get_anchors(self) -> list[FloatArray]:
        """Exclude hidden lattice nodes from visible boundary queries."""
        return self._empty_anchors

    def reduce_across_dimension(
        self, reduce_func: Callable[[Iterable[float]], float], dim: int
    ) -> None:
        """Exclude the lattice from family width, height and depth measurements.

        Parameters
        ----------
        reduce_func, dim
            Native boundary reduction arguments, intentionally unused.
        """
        return None

    def suspend_updating(self, recursive: bool = True) -> Self:
        """Freeze external artists if the animation returns the frame to its start.

        Parameters
        ----------
        recursive
            Forwarded to Manim.
        """
        animation = animation_context()
        if animation is not None and not _SIMULATING and self._system is not None:
            frozen = None if self._permanent(animation) else self.mapping
            self._suspensions.append(
                (
                    animation,
                    frozen,
                    frozenset(cast(Mobject, animation.mobject).get_family()),
                )
            )
            self._freeze_artists()
        VMobject.suspend_updating(self, recursive)
        return self

    def resume_updating(self, recursive: bool = True) -> Self:
        """Release an animation's frozen frame.

        Parameters
        ----------
        recursive
            Forwarded to Manim.
        """
        animation = animation_context(finishing=True)
        self._suspensions = [s for s in self._suspensions if s[0] is not animation]
        self._freeze_artists()
        VMobject.resume_updating(self, recursive)
        return self

    def _freeze_artists(self) -> None:
        if self._system is not None:
            for artist in self._system._artists:
                for leaf in artist.get_family():
                    if isinstance(leaf, Leaf):
                        leaf._frozen_frame = None
                        for _, frozen, excluded in self._suspensions:
                            if leaf not in excluded:
                                leaf._frozen_frame = frozen
                        leaf._frame_seen = -1

    def _permanent(self, animation: Animation) -> bool:
        global _SIMULATING
        memo: dict[int, Any] = {}
        _SIMULATING = True
        try:
            clone = copy.deepcopy(animation, memo)
            frame = memo.get(id(self))
            if frame is None:
                return False
            initial = frame.points.copy()
            clone._setup_scene(cast(Scene, _SimulationScene()))
            clone.begin()
            clone.finish()
            clone.clean_up_from_scene(cast(Scene, _SimulationScene()))
            return not np.allclose(initial, frame.points, atol=1e-9, rtol=0)
        finally:
            _SIMULATING = False


class _SimulationScene:
    def __init__(self) -> None:
        self.mobjects: list[Mobject] = []

    def add(self, *mobjects: Mobject) -> None:
        self.mobjects.extend(mobjects)

    def remove(self, *mobjects: Mobject) -> None:
        self.mobjects = [m for m in self.mobjects if m not in mobjects]

    def replace(self, old: Mobject, new: Mobject) -> None:
        self.remove(old)
        self.add(new)

    def get_mobject_family_members(self) -> list[Mobject]:
        return [m for root in self.mobjects for m in root.get_family()]
