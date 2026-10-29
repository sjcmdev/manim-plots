"""Library-owned point buffers and the Manim side of the leaf lifecycle."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, NoReturn, Self, TypedDict, Unpack, cast

import numpy as np
from manim import Animation, MathTex, Mobject, Scene, Tex, VGroup, VMobject, config
from manim.constants import CapStyleType, LineJointType, RendererType
from manim.typing import PathFuncType, Vector3DLike
from manim.utils.color import ParsableManimColor
from manim.utils.paths import straight_path
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
    from manim_plots.mobjects.artists import FunctionPlot, LineStyle
    from manim_plots.mobjects.system import CartesianAxes

_SIMULATING = False
_STRAIGHT = straight_path()


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


class _ArtistOptions(_VMStyle, total=False):
    label: str | None
    clip: bool | float
    line_style: LineStyle
    dash: tuple[float, float] | None


class _PlotOptions(_ArtistOptions, total=False):
    use_smoothing: bool
    discontinuities: Iterable[float] | None
    dt: float


class _DecimalOptions(_VMStyle, total=False):
    num_decimal_places: int
    include_sign: bool
    group_with_commas: bool
    digit_buff_per_font_unit: float
    show_ellipsis: bool
    unit: str | None
    unit_buff_per_font_unit: float
    include_background_rectangle: bool
    edge_to_fix: Vector3DLike


class _NumberPlacement(_DecimalOptions, total=False):
    direction: ArrayLike | None
    buff: float | None


class _NumberOptions(_NumberPlacement, total=False):
    font_size: float | None
    label_constructor: object


class _RotateOptions(TypedDict, total=False):
    about_edge: Vector3DLike | None


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


def _become_target(
    subject: Mobject,
    target: Mobject,
    match_height: bool,
    match_width: bool,
    match_depth: bool,
    match_center: bool,
    stretch: bool,
) -> Mobject:
    if stretch or match_height or match_width or match_depth or match_center:
        target = target.copy()
        if stretch:
            target.stretch_to_fit_height(subject.height)
            target.stretch_to_fit_width(subject.width)
            target.stretch_to_fit_depth(subject.depth)
        else:
            if match_height:
                target.match_height(subject)
            if match_width:
                target.match_width(subject)
            if match_depth:
                target.match_depth(subject)
        if match_center:
            target.move_to(subject.get_center())
    return target


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

    _label_owner: BoundLabel | None = None
    _pool_visible = True

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
        self._alignment_locked = False
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
        if (
            self._ready
            and not self._alignment_locked
            and self._lifecycle.state not in (lc.State.TRANSIENT, lc.State.REMOVED)
            and not buffer_write()
        ):
            self._ensure()
        return self._cache

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._cache = np.asarray(value, dtype=float)

    def _ensure(self) -> None:
        if self._alignment_locked or self._lifecycle.state in (
            lc.State.TRANSIENT,
            lc.State.REMOVED,
        ):
            return
        owner = self.__dict__.get("_label_owner")
        if owner is not None:
            owner._ensure()
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
            elif kind is lc.Kind.REBIND:
                old, new = self._system, action.ref
                assert old is not None
                from manim_plots.mobjects.system import CartesianAxes

                assert isinstance(new, CartesianAxes)
                if self in old._artists:
                    old._artists.remove(self)  # type: ignore[arg-type]
                    new._artists.append(self)  # type: ignore[arg-type]
                self._system = new
                self._frozen_frame = None
                self._frame_seen = -1
                self._dirty = True

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
            self._alignment_locked = True
            if isinstance(mobject, Leaf):
                mobject._ensure()
                mobject._alignment_locked = True
        super().align_data(mobject, skip_point_alignment)
        if isinstance(mobject, VMobject):
            self._candidate = mobject.copy()
        return self

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType = _STRAIGHT,
    ) -> Self:
        """Keep keyed decorations derived while Manim interpolates ordinary leaves.

        Parameters
        ----------
        mobject1, mobject2, alpha, path_func
            Native interpolation endpoints, progress and geometry path.
        """
        if self._system is None or not self._system._data_animation:
            super().interpolate(mobject1, mobject2, alpha, path_func)
        return self

    def get_anchors(self) -> list[FloatArray]:
        """Exclude inactive pool members from visible boundaries."""
        return super().get_anchors() if self._pool_visible else self._empty_anchors

    def reduce_across_dimension(
        self, reduce_func: Callable[[Iterable[float]], float], dim: int
    ) -> float | None:
        """Measure active geometry, excluding hidden pool slots.

        Parameters
        ----------
        reduce_func, dim
            Native boundary reduction and coordinate index.
        """
        if not self._pool_visible:
            return None
        return super().reduce_across_dimension(reduce_func, dim)

    def become(
        self,
        mobject: Mobject,
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """Adopt an artist's data or retain the local shape of a plain target.

        Parameters
        ----------
        mobject, match_height, match_width, match_depth, match_center, stretch
            Native target and size/placement preparation options.
        """
        target = _become_target(
            self, mobject, match_height, match_width, match_depth, match_center, stretch
        )
        super().become(target)
        self._event(lc.Become(target, isinstance(target, Leaf)))
        self._candidate = None
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
            self._alignment_locked = False
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
        aligned_copy = self._alignment_locked and animation_context(transform_only=True)
        result._alignment_locked = bool(aligned_copy)
        if rebuilding and not aligned_copy:
            result._restore()
        return result


class AxisLine(Leaf):
    """Carry the control points of one axis line."""


class TickLeaf(Leaf):
    """Carry one major tick's cubic path."""


class TipLeaf(Leaf):
    """Carry a filled native arrow tip's cubic path."""


class GlyphLeaf(Leaf):
    """Carry one cached glyph's colour-independent outline."""


class GridLeaf(Leaf):
    """Carry one major or minor grid line."""

    level: str = "major"
    value: float = 0


_GLYPHS: dict[tuple[str, float, object], FloatArray] = {}
_SCRIPTS: dict[tuple[str, float], tuple[FloatArray, float]] = {}


def _glyph(text: str, font_size: float, label_constructor: object = None) -> GlyphLeaf:
    constructor = MathTex if label_constructor is None else label_constructor
    if not callable(constructor):
        raise TypeError("label_constructor must be callable")
    key = (text, font_size, constructor)
    if key not in _GLYPHS:
        native = constructor(text)
        if not isinstance(native, VMobject) or not hasattr(native, "font_size"):
            raise TypeError("label_constructor must produce a font_size-aware VMobject")
        cast(Any, native).font_size = font_size
        outline = native.get_all_points().copy()
        outline.flags.writeable = False
        _GLYPHS[key] = outline
    return GlyphLeaf(_GLYPHS[key], stroke_width=0, fill_opacity=1)


def _superscript(text: str, font_size: float) -> VGroup:
    result = VGroup()
    position = 0.0
    for char in text:
        key = (char, font_size)
        if key not in _SCRIPTS:
            # The two zeros retain TeX's glyph bearings, baseline and advance.
            native = MathTex("^{0" + char + "0}", font_size=font_size)
            glyphs = native.family_members_with_points()
            first, middle, last = glyphs
            advance_zero = _script_zero_advance(font_size)
            outline = middle.points - first.get_left() - [advance_zero, 0, 0]
            advance = float(last.get_left()[0] - first.get_left()[0]) - advance_zero
            outline.flags.writeable = False
            _SCRIPTS[key] = outline, advance
        outline, advance = _SCRIPTS[key]
        result.add(
            GlyphLeaf(
                outline + np.array([position, 0, 0]), stroke_width=0, fill_opacity=1
            )
        )
        position += advance
    result.center()
    return result


def _script_zero_advance(font_size: float) -> float:
    key = ("0", font_size)
    if key not in _SCRIPTS:
        native = MathTex("^{000}", font_size=font_size)
        first, middle, last = native.family_members_with_points()
        advance = float(last.get_left()[0] - first.get_left()[0]) / 2
        outline = middle.points - first.get_left() - [advance, 0, 0]
        outline.flags.writeable = False
        _SCRIPTS[key] = outline, advance
    return _SCRIPTS[key][1]


def _formatted_glyphs(
    text: str, font_size: float, *, text_mode: bool = False
) -> VGroup:
    # Tokenize commands and scripts, so a new label never compiles a whole string.
    result = VGroup()
    tokens = re.findall(r"\\[a-zA-Z]+|\\.|.", text)
    i = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if token in ("{", "}", "$", r"\left", r"\right"):
            continue
        if token in ("^", "_") and not text_mode:
            script: list[str] = []
            if i < len(tokens) and tokens[i] == "{":
                i += 1
                depth = 1
                while i < len(tokens) and depth:
                    part = tokens[i]
                    i += 1
                    depth += (part == "{") - (part == "}")
                    if depth:
                        script.append(part)
            elif i < len(tokens):
                script.append(tokens[i])
                i += 1
            small = _formatted_glyphs("".join(script), font_size * 0.7)
            small.next_to(result, direction=(1, 0, 0), buff=0.02)
            small.shift((0, (0.35 if token == "^" else -0.2) * font_size / 48, 0))
            result.add(*small.submobjects)
            continue
        if (
            token in (r"\text", r"\mathrm", r"\operatorname")
            and i < len(tokens)
            and tokens[i] == "{"
        ):
            i += 1
            run: list[str] = []
            while i < len(tokens) and tokens[i] != "}":
                run.append(tokens[i])
                i += 1
            i += 1
            for char in "".join(run):
                glyph = _glyph(char, font_size, Tex)
                if result.submobjects:
                    glyph.next_to(
                        result,
                        direction=(1, 0, 0),
                        buff=0.001 * font_size,
                        aligned_edge=(0, -1, 0),
                    )
                result.add(glyph)
            continue
        if token.isspace() or token in (r"\,", r"\;", r"\!"):
            continue
        glyph = _glyph(token, font_size, Tex if text_mode else None)
        if result.submobjects:
            glyph.next_to(
                result,
                direction=(1, 0, 0),
                buff=0.001 * font_size,
                aligned_edge=(0, -1, 0),
            )
        result.add(glyph)
    result.center()
    if text.startswith("-") and len(result) > 1:
        result[0].align_to(result[1], (0, 1, 0)).shift(
            result[1].height * np.array([0, -0.5, 0])
        )
    return result


class NumberLabel(VGroup):
    """Lay out cached glyphs using DecimalNumber's spacing and alignment.

    Parameters
    ----------
    number
        Finite numeric value.
    font_size
        Size of the cached math glyphs.
    label_constructor
        Optional native glyph constructor, defaulting to MathTex.
    **kwargs
        DecimalNumber formatting and VMobject style options.
    """

    def __init__(
        self,
        number: float,
        font_size: float = 36,
        label_constructor: object = None,
        **kwargs: Unpack[_DecimalOptions],
    ) -> None:
        options: dict[str, Any] = dict(kwargs)
        places = options.pop("num_decimal_places", 2)
        sign = options.pop("include_sign", False)
        commas = options.pop("group_with_commas", True)
        spacing = options.pop("digit_buff_per_font_unit", 0.001) * font_size
        ellipsis = options.pop("show_ellipsis", False)
        unit = options.pop("unit", None)
        unit_buff = options.pop("unit_buff_per_font_unit", 0) * font_size
        background = options.pop("include_background_rectangle", False)
        options.pop("edge_to_fix", None)
        self.number = number
        self._font_size = font_size
        self.num_decimal_places = places
        text = format(number, f"{'+' if sign else ''}{',' if commas else ''}.{places}f")
        if text.startswith("-") and np.round(number, places) == 0:
            text = ("+" if sign else "") + text[1:]
        self.text = text
        super().__init__(*(_glyph(c, font_size, label_constructor) for c in text))
        if ellipsis:
            self.add(_glyph(r"\dots", font_size))
        self.arrange(buff=spacing, aligned_edge=np.array([0.0, -1.0, 0.0]))
        if unit is not None:
            # Units are annotations; numeric digits always use the glyph cache.
            unit_mob = (
                _superscript(unit[2:-1], font_size)
                if unit.startswith("^{") and unit.endswith("}")
                else _label(unit, font_size=font_size)
            )
            unit_mob.next_to(self, buff=unit_buff + spacing, aligned_edge=(0, -1, 0))
            self.add(unit_mob)
        self.move_to(np.zeros(3))
        for i, char in enumerate(text):
            if char == "-" and i + 1 < len(text):
                self[i].align_to(self[i + 1], (0, 1, 0))
                self[i].shift(self[i + 1].height * np.array([0, -0.5, 0]))
            elif char == ",":
                self[i].shift(self[i].height * np.array([0, -0.5, 0]))
        if unit is not None and unit.startswith("^"):
            unit_mob.align_to(self, (0, 1, 0))
        if unit is not None:
            self.submobjects = [*self.submobjects[:-1], *unit_mob.submobjects]
        self.initial_height = self.height
        style = {"stroke_width": 0, "fill_opacity": 1, **options}
        color = style.pop("color", None)
        if color is not None:
            style.setdefault("stroke_color", color)
            style.setdefault("fill_color", color)
        self.set_style(**style)
        if background:
            # Convert even the optional background to a library-owned leaf.
            self.add_to_back(_label(self.copy().add_background_rectangle()[0]))

    def _set_text(self, text: str, *, text_mode: bool = False) -> None:
        style = self.get_style()
        glyphs = _formatted_glyphs(text, self._font_size, text_mode=text_mode)
        self.submobjects = glyphs.submobjects
        self.text = text
        self.initial_height = self.height or 1.0
        self.set_style(**style)

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"NumberLabel has no attribute {name!r}")

    @property
    def font_size(self) -> float:
        """Return the current size using DecimalNumber's height convention."""
        return self._font_size * self.height / self.initial_height

    @font_size.setter
    def font_size(self, value: float) -> None:
        if value <= 0:
            raise ValueError("font_size must be positive")
        self.scale(value / self.font_size)

    def get_value(self) -> float:
        """Return the represented numeric value."""
        return self.number


def _label(value: object, *, text_mode: bool = False, font_size: float = 48) -> VGroup:
    if isinstance(value, NumberLabel):
        return value
    if not isinstance(value, VMobject):
        value = (Tex if text_mode else MathTex)(str(value), font_size=font_size)
    result = VGroup()
    result.match_style(value, family=False)
    for member in value.family_members_with_points():
        leaf = GlyphLeaf(member.points)
        leaf.match_style(cast(VMobject, member), family=False)
        result.add(leaf)
    return result


class BoundLabel(VGroup):
    """Bind label outlines to a system's frame and optional data anchor.

    Parameters
    ----------
    label
        Positioned library glyphs.
    system
        Owning coordinate system.
    anchor
        Optional callable returning a local anchor after a range edit.
    graph
        Optional source of a graph-bound anchor.
    """

    dot: VMobject

    def __init__(
        self,
        label: VGroup,
        system: CartesianAxes,
        anchor: Callable[[], FloatArray] | None = None,
        graph: FunctionPlot | None = None,
    ) -> None:
        self._system = system
        self._actual_updaters: list[Callable[..., Any]] = []
        self._graph = graph
        self._source_seen = None if graph is None else graph.source
        self._own_seen = None if graph is None else graph._own
        super().__init__(*label.submobjects)
        self.match_style(label, family=False)
        self._anchor = anchor
        self._data_seen = system._data_version
        self._frame_seen = system.frame.version
        self._placing = False
        leaves = [m for m in self.get_family() if isinstance(m, Leaf)]
        self._leaves = leaves
        self._local = [system.frame.mapping.inverse(m.points) for m in leaves]
        self._anchor_seen = None if anchor is None else anchor()
        for leaf in leaves:
            leaf._label_owner = self
        self.add_updater(_synchronise)

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"BoundLabel has no attribute {name!r}")

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Report synchronisation to plays that move the system or graph."""
        moving = moving_context()
        if moving is not None and self._graph is not None and self._graph in moving:
            return self._actual_updaters
        return _reported_updaters(self._actual_updaters, self._system)

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._actual_updaters = value

    def _poll(self) -> None:
        self._system._poll()
        self._ensure()

    def _ensure(self) -> None:
        if self._placing:
            return
        self._placing = True
        try:
            system = self._system
            system._sync_data()
            graph = self._graph
            changed = self._data_seen != system._data_version
            if graph is not None:
                changed |= (
                    graph.source is not self._source_seen
                    or graph._own is not self._own_seen
                )
            if changed and self._anchor is not None and self._anchor_seen is not None:
                anchor = self._anchor()
                delta = anchor - self._anchor_seen
                self._local = [points + delta for points in self._local]
                self._anchor_seen = anchor
            if changed or self._frame_seen != system.frame.version:
                mapping = system.frame.mapping
                for leaf, local in zip(self._leaves, self._local, strict=True):
                    leaf._cache = mapping.forward(local)
                self._frame_seen = system.frame.version
                self._data_seen = system._data_version
                if graph is not None:
                    self._source_seen = graph.source
                    self._own_seen = graph._own
        finally:
            self._placing = False


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

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType = _STRAIGHT,
    ) -> Self:
        """Interpolate native placement, then publish the current data ranges.

        Parameters
        ----------
        mobject1, mobject2, alpha, path_func
            Native frame endpoints, progress and geometric interpolation path.
        """
        system = self._system
        if system is None or not system._data_animation or system._channel_frame_moves:
            VMobject.interpolate(self, mobject1, mobject2, alpha, path_func)
        if system is not None and system._data_animation:
            assert isinstance(mobject1, FrameLeaf) and mobject1._system is not None
            assert isinstance(mobject2, FrameLeaf) and mobject2._system is not None
            system._interpolate_data(mobject1._system, mobject2._system, alpha)
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
