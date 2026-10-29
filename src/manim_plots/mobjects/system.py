"""Cartesian coordinate systems, registration and frame synchronisation."""

from __future__ import annotations

import copy
import weakref
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any, Literal, NoReturn, Self, Unpack, cast, overload

import numpy as np
from manim import (
    BLUE_D,
    DEFAULT_DOT_RADIUS,
    PURE_YELLOW,
    Dot,
    LinearBase,
    LogBase,
    Mobject,
    VDict,
    VGroup,
    VMobject,
    config,
)
from manim import Axes as NativeAxes
from manim.constants import RendererType
from manim.typing import Point3DLike, Vector3DLike
from manim.utils.color import ParsableManimColor
from manim.utils.config_ops import merge_dicts_recursively
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core import lifecycle as lc
from manim_plots.core.nodes import (
    FRAME_NODES,
    AffineNode,
    Chain,
    FrameMap,
    ScaleNode,
    SystemMap,
)
from manim_plots.core.scales import (
    MINPOS_UNKNOWN,
    LinearScale,
    LogScale,
    Scale,
    SymLogScale,
)
from manim_plots.core.sources import Box
from manim_plots.core.ticks import (
    Locator,
    LogLocator,
    MinorCountLocator,
    MultipleLocator,
    SymLogLocator,
)
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LinePlot,
    Marker,
    ParametricPlot,
    ScatterPlot,
    _CurvePlot,
    _parameterize,
)
from manim_plots.mobjects.axis import (
    Axis,
    _LogExponentLocator,
    _LogMinorLocator,
    _range,
    _TickPool,
)
from manim_plots.mobjects.context import (
    _PlaybackToken,
    animation_context,
    data_interpolation,
    playback_context,
)
from manim_plots.mobjects.leaves import (
    BoundLabel,
    FrameLeaf,
    GridLeaf,
    Leaf,
    _ArtistOptions,
    _become_target,
    _label,
    _NumberOptions,
    _ParametricOptions,
    _reported_updaters,
    _synchronise,
    _VMStyle,
)
from manim_plots.mobjects.legend import Legend, _handle

_DEFAULT_LENGTHS = (round(config.frame_width) - 2, round(config.frame_height) - 2)
_AXIS_KEYS = frozenset(
    [
        "include_numbers",
        "numbers_to_include",
        "numbers_to_exclude",
        "decimal_number_config",
        "font_size",
        "include_ticks",
        "tick_size",
        "longer_tick_multiple",
        "numbers_with_elongated_ticks",
        "exclude_origin_tick",
        "include_tip",
        "tip_shape",
        "tip_width",
        "tip_height",
        "label_direction",
        "line_to_number_buff",
        "unit_size",
        "scaling",
        "stroke_width",
        "color",
    ]
)


class _ArtistRegistry:
    def __init__(self) -> None:
        self._refs: list[weakref.ReferenceType[_CurvePlot | ScatterPlot]] = []

    def __iter__(self) -> Iterator[_CurvePlot | ScatterPlot]:
        live = [artist for ref in self._refs if (artist := ref()) is not None]
        self._refs = [weakref.ref(artist) for artist in live]
        return iter(live)

    def __contains__(self, artist: object) -> bool:
        return any(ref() is artist for ref in self._refs)

    def append(self, artist: _CurvePlot | ScatterPlot) -> None:
        list(self)
        self._refs.append(weakref.ref(artist))

    def remove(self, artist: _CurvePlot | ScatterPlot) -> None:
        self._refs = [ref for ref in self._refs if ref() is not artist]


def _scale(value: Scale | str, name: str) -> Scale:
    if isinstance(value, str):
        if value == "linear":
            return LinearScale()
        if value == "log":
            return LogScale()
        if value == "symlog":
            return SymLogScale()
        raise ValueError(f"{name} must be linear, log or symlog")
    if not isinstance(value, Scale):
        raise TypeError(f"{name} must be a Scale or scale name")
    return value


class CartesianAxes(VGroup):
    """Build two Cartesian axes whose frame carries separately registered plots.

    Parameters
    ----------
    x_range, y_range
        Endpoints and optional positive major tick spacing.
    x_length, y_length
        Positive axis lengths, defaulting to Manim's frame-based defaults.
    axis_config, x_axis_config, y_axis_config
        Recursively merged NumberLine options; per-axis values take precedence.
        An unknown key raises ValueError naming the key. A unit_size without an
        explicit axis length sets the length; supplying both raises ValueError.
    tips
        Default for each axis's include_tip option.
    x_scale, y_scale
        Data scales or the names linear, log and symlog. Manim's scaling option
        retains its exponent-range convention for LogBase.
    aspect
        Optional ratio of a y unit's scene length to an x unit's scene length.
    adjustable
        Adapt an omitted length or widen a range to satisfy the aspect ratio.
    **kwargs
        Native VGroup style and mobject options.

    Notes
    -----
    Registered curves follow permanent changes of this system, including shifts,
    scales and rotations. They stay still throughout animations that return the
    frame to its start, including Indicate, Wiggle and ``Rotate(ax, TAU)``.
    Animating both the axes and a curve's shift moves the curve twice. A geometric
    operation on a VGroup containing both moves it once.

    To determine whether a change is permanent, an animation runs on a copy first.
    Its callbacks therefore run once more than in plain Manim; avoid relying on
    callback side effects. After a non-affine deformation, the frame is a bilinear
    approximation, exact at its lattice nodes. A singular frame refuses p2c and
    operations on a curve that need the frame's inverse.

    The invisible frame is the last family member. With Manim's default lag ratio,
    ``Create(ax)`` finishes its visible leaves at 24/25 of the run. Use DrawAxes to
    draw without that lag slot. Transform pairs ticks by locator key rather than
    family position; unmatched ticks fade out or in. Changing scale type requires
    FadeTransform.

    Curves are clipped by default, plots use a colour cycle starting with white,
    and overlapping number labels hide the later label. Tick locations are integer
    multiples of the step, and scientific-notation steps count their exponent when
    choosing decimal places. See plot and the Axis decoration methods for controls.
    """

    _color_index: int = 0

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        axis_config: dict[str, Any] | None = None,
        x_axis_config: dict[str, Any] | None = None,
        y_axis_config: dict[str, Any] | None = None,
        tips: bool = True,
        *,
        x_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        y_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        aspect: float | None = None,
        adjustable: Literal["length", "range"] = "length",
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        if config.renderer == RendererType.OPENGL:
            raise ValueError("CartesianAxes requires the Cairo renderer")
        for options in (axis_config, x_axis_config, y_axis_config):
            if options is not None:
                if not isinstance(options, dict):
                    raise TypeError("axis_config must be a dict")
                for key in options:
                    if key not in _AXIS_KEYS:
                        raise ValueError(f"unknown axis_config key {key!r}")
        self.axis_config = merge_dicts_recursively(
            {"include_tip": tips, "numbers_to_exclude": [0]}, axis_config or {}
        )
        self.x_axis_config = merge_dicts_recursively(
            self.axis_config, x_axis_config or {}
        )
        self.y_axis_config = merge_dicts_recursively(
            self.axis_config, {"label_direction": [-1, 0, 0]}, y_axis_config or {}
        )
        configs = (self.x_axis_config, self.y_axis_config)
        ranges: list[list[float]] = [
            list(x_range)
            if x_range is not None
            else [-round(config.frame_x_radius), round(config.frame_x_radius), 1],
            list(y_range)
            if y_range is not None
            else [-round(config.frame_y_radius), round(config.frame_y_radius), 1],
        ]
        scales = [_scale(x_scale, "x_scale"), _scale(y_scale, "y_scale")]
        native_ranges = []
        locators: list[Locator | None] = [None, None]
        minors: list[Locator | None] = [None, None]
        for i, options in enumerate(configs):
            name = "x_range" if i == 0 else "y_range"
            _range(ranges[i], name)
            if len(ranges[i]) == 2:
                ranges[i].append(1)
            scaling = options.get("scaling")
            if isinstance(scaling, LogBase):
                if not isinstance(scales[i], LinearScale):
                    raise ValueError(
                        "scaling and x_scale/y_scale cannot both specify a scale"
                    )
                scales[i] = LogScale(base=scaling.base)
                native_ranges.append(list(ranges[i]))
                ranges[i][:2] = scales[i].inverse(ranges[i][:2]).tolist()
                locators[i] = _LogExponentLocator(scaling.base, ranges[i][2])
            elif isinstance(scaling, LinearBase) and scaling.scale_factor != 1:
                factor = float(scaling.scale_factor)
                if not np.isfinite(factor) or factor == 0:
                    raise ValueError("scaling scale_factor must be finite and nonzero")
                native_ranges.append(list(ranges[i]))
                ranges[i][:2] = [value * factor for value in ranges[i][:2]]
                locators[i] = MultipleLocator(abs(factor) * ranges[i][2])
            else:
                scale = scales[i]
                lo, hi = scale.limit_range(
                    float(ranges[i][0]), float(ranges[i][1]), MINPOS_UNKNOWN
                )
                ranges[i][:2] = [lo, hi]
                if isinstance(scale, LogScale):
                    tick_base = scale.base if scale.base > 1 else 1 / scale.base
                    locators[i] = LogLocator(base=tick_base)
                    subs = tuple(value for value in range(2, 10) if value < tick_base)
                    if subs:
                        minors[i] = _LogMinorLocator(base=tick_base, subs=subs)
                elif isinstance(scale, SymLogScale):
                    locators[i] = SymLogLocator(
                        base=scale.base, linthresh=scale.linthresh
                    )
                displayed = scales[i].forward(ranges[i][:2]).tolist()
                if not isinstance(scale, LinearScale):
                    displayed.sort()
                native_ranges.append([*displayed, ranges[i][2]])
            if options.get("scaling") is None or isinstance(
                options.get("scaling"), LinearBase
            ):
                options["exclude_origin_tick"] = True
            else:
                options["exclude_origin_tick"] = False
        lengths = [x_length, y_length]
        for i, options in enumerate(configs):
            if "unit_size" in options:
                if lengths[i] is not None:
                    raise ValueError(
                        f"{'x_length' if i == 0 else 'y_length'} and "
                        "unit_size cannot both be given"
                    )
                lengths[i] = (
                    abs(float(native_ranges[i][1] - native_ranges[i][0]))
                    * options["unit_size"]
                )
        resolved = [
            float(_DEFAULT_LENGTHS[i] if length is None else length)
            for i, length in enumerate(lengths)
        ]
        if adjustable not in ("length", "range"):
            raise ValueError("adjustable must be length or range")
        if aspect is not None:
            if not np.isfinite(aspect) or aspect <= 0:
                raise ValueError("aspect must be positive and finite")
            spans = [
                abs(float(np.diff(scale.forward(limits[:2]))[0]))
                for scale, limits in zip(scales, ranges, strict=True)
            ]
            if adjustable == "length":
                if lengths[0] is not None and lengths[1] is not None:
                    raise ValueError(
                        "aspect with adjustable=length cannot fix both lengths"
                    )
                if lengths[1] is not None:
                    resolved[0] = resolved[1] * spans[0] / (aspect * spans[1])
                else:
                    resolved[1] = aspect * resolved[0] * spans[1] / spans[0]
            else:
                ratio = (resolved[1] / spans[1]) / (resolved[0] / spans[0])
                index = 1 if ratio > aspect else 0
                factor = ratio / aspect if index == 1 else aspect / ratio
                transformed = scales[index].forward(ranges[index][:2])
                midpoint = float(np.mean(transformed))
                ranges[index][:2] = (
                    scales[index]
                    .inverse(midpoint + (transformed - midpoint) * factor)
                    .tolist()
                )
                native_ranges[index][:2] = (
                    scales[index].forward(ranges[index][:2]).tolist()
                )
        self.x_length, self.y_length = resolved
        self.aspect, self.adjustable = aspect, adjustable
        self._aspect_axis = 0 if lengths[1] is not None else 1
        for name, value in (("x_length", self.x_length), ("y_length", self.y_length)):
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        self._artists = _ArtistRegistry()
        self._data_animation = False
        self._channel_frame_moves = False
        self._pool_warned = False
        self._channel_roots: list[VMobject] = []
        self._moving_query: tuple[frozenset[Mobject], bool] | None = None
        self._actual_updaters: list[Callable[..., Any]] = []
        self._syncing = True
        self._data_version = 0
        self._poll_token: _PlaybackToken | None = None
        self._token = 0
        super().__init__(**kwargs)
        # Native geometry is constructed without labels; all labels use our cache.
        native_configs = [
            {**options, "include_numbers": False, "numbers_to_include": None}
            for options in configs
        ]
        native = NativeAxes(
            native_ranges[0],
            native_ranges[1],
            self.x_length,
            self.y_length,
            x_axis_config=native_configs[0],
            y_axis_config=native_configs[1],
            tips=tips,
        )
        lower = -np.array([self.x_length, self.y_length]) / 2
        self.bounds = Box(lower, -lower)
        self.frame = FrameLeaf(lower, -lower, self)
        self.x_axis = Axis(
            self,
            0,
            ranges[0],
            native.x_axis,
            scales[0],
            locators[0],
            minors[0],
            configs[0],
        )
        self.y_axis = Axis(
            self,
            1,
            ranges[1],
            native.y_axis,
            scales[1],
            locators[1],
            minors[1],
            configs[1],
        )
        for axis, own in ((self.x_axis, x_axis_config), (self.y_axis, y_axis_config)):
            given = (axis_config or {}, own or {})
            axis._default_exclusion = not any("numbers_to_exclude" in c for c in given)
        self.axes = VGroup(self.x_axis, self.y_axis)
        self.x, self.y = self.x_axis, self.y_axis
        self.submobjects = [self.x_axis, self.y_axis, self.frame]
        self._compile()
        for axis in (self.x_axis, self.y_axis):
            if axis.include_numbers or axis.numbers_to_include is not None:
                axis.add_numbers(axis.numbers_to_include)
        for axis in (self.x_axis, self.y_axis):
            axis._decoration_seen = axis._versions()
        self._syncing = False
        if any(not isinstance(scale, LinearScale) for scale in scales):
            self._syncing = True
            try:
                self.x_axis._configure()
                self.y_axis._configure()
            finally:
                self._syncing = False
        self.add_updater(_synchronise)

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"CartesianAxes has no attribute {name!r}")

    def family_members_with_points(self) -> list[Mobject]:
        """Return members with points, using the flat animation channel directly."""
        if self._data_animation and all(isinstance(m, Leaf) for m in self.submobjects):
            if data_interpolation():
                # The frame publishes all derived geometry at the same alpha.
                return [self.frame]
            self._sync_data()
            members: list[Mobject] = []
            for leaf in cast(list[Leaf], self.submobjects):
                if leaf._label_owner is not None:
                    leaf._ensure()
                if len(leaf._cache):
                    members.append(leaf)
            return members
        return super().family_members_with_points()

    def update(self, dt: float = 0, recursive: bool = True) -> Self:
        """Update active channel leaves without traversing updater-free decorations.

        Parameters
        ----------
        dt, recursive
            Native updater elapsed time and family traversal flag.
        """
        if not self._data_animation:
            return super().update(dt, recursive)
        if self.updating_suspended:
            return self
        super().update(dt, recursive=False)
        if recursive:
            for member in self.submobjects:
                if member.submobjects or member.updaters:
                    member.update(dt, recursive=True)
        return self

    def become(
        self,
        mobject: Mobject,
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """Adopt another system's parameters and frame, retaining bound artists.

        Parameters
        ----------
        mobject, match_height, match_width, match_depth, match_center, stretch
            Native target and size/placement preparation options.
        """
        if not isinstance(mobject, CartesianAxes):
            super().become(
                mobject, match_height, match_width, match_depth, match_center, stretch
            )
            return self
        target = _become_target(
            self,
            mobject.copy(),
            match_height,
            match_width,
            match_depth,
            match_center,
            stretch,
        )
        artists = self._artists
        self.__dict__.update(target.__dict__)
        self._artists = artists
        for member in self.get_family():
            if isinstance(member, (Axis, Leaf, BoundLabel)):
                member._system = self
        self._data_version += 1
        for artist in artists:
            for leaf in artist.get_family():
                if isinstance(leaf, Leaf):
                    leaf._frame_seen = -1
                    leaf._event(lc.DataChange())
        return self

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Align a system Transform by decoration role and locator identity.

        Parameters
        ----------
        mobject, skip_point_alignment
            Native target and alignment option.

        Raises
        ------
        ValueError
            If the target changes a scale type; use FadeTransform instead.
        """
        animation = animation_context(transform_only=True)
        if animation is None or not isinstance(mobject, CartesianAxes):
            super().align_data(mobject, skip_point_alignment)
            return self
        self._sync_data()
        mobject._sync_data()
        for axis, target in zip(self.axes, mobject.axes, strict=True):
            if type(axis._scale) is not type(target._scale):
                raise ValueError("a change of scale type requires FadeTransform")
        count = max(1, int(np.ceil(animation.run_time * config.frame_rate * 4)))
        alphas = np.array(
            [animation.rate_func(t) for t in np.linspace(0, 1, count + 1)]
        )
        pools = [
            _TickPool(axis, target, alphas)
            for axis, target in zip(
                (self.x, self.y), (mobject.x, mobject.y), strict=True
            )
        ]
        changed = any(
            not np.array_equal(axis.range.value, target.range.value) or not pool.same
            for axis, target, pool in zip(
                (self.x, self.y), (mobject.x, mobject.y), pools, strict=True
            )
        )
        if not changed:
            super().align_data(mobject, skip_point_alignment)
            return self
        target_pools = [copy.deepcopy(pool) for pool in pools]
        frame_moves = not np.array_equal(self.frame._cache, mobject.frame._cache)
        for system, alpha in ((self, 0.0), (mobject, 1.0)):
            system._channel_roots = system.submobjects[:]
            system._data_animation = True
            system._channel_frame_moves = frame_moves
            system._pool_warned = False
            system._pool_alpha = alpha
            system._syncing = True
            try:
                for axis, pool in zip(
                    (system.x, system.y),
                    target_pools if system is mobject else pools,
                    strict=True,
                ):
                    pool.alpha = alpha
                    axis._prepare_pool(pool)
                system.x._configure()
                system.y._configure()
            finally:
                system._syncing = False
        left, right = self._channel_roles(), mobject._channel_roles()
        roles = dict.fromkeys((*left, *right))
        families: list[list[VMobject]] = [[], []]
        for role in roles:
            a, b = left.get(role), right.get(role)
            if a is None:
                assert b is not None
                a = Leaf(np.zeros_like(b._cache), self)
                a.match_style(b)
                a.set_opacity(0)
            if b is None:
                b = Leaf(np.zeros_like(a._cache), mobject)
                b.match_style(a)
                b.set_opacity(0)
            # Native point alignment is safe here: derived interpolation bypasses it.
            VMobject.align_data(a, b)
            families[0].append(a)
            families[1].append(b)
        self.submobjects = [*families[0], self.frame]
        mobject.submobjects = [*families[1], mobject.frame]
        return self

    def _channel_roles(self) -> dict[object, Leaf]:
        roles: dict[object, Leaf] = {}
        for axis in (self.x, self.y):
            for name in ("line", "tip", "tip_start"):
                leaf = getattr(axis, name)
                if leaf is not None:
                    roles[(axis.index, name)] = leaf
            for name, leaves in (
                ("major", axis._tick_leaves),
                ("minor", axis._minor_leaves),
            ):
                if axis.include_ticks:
                    for key, leaf in leaves.items():
                        roles[(axis.index, name, key)] = leaf
            for key, grid in axis._grid_leaves.items():
                roles[(axis.index, "grid", key)] = grid
            for key, label in axis._number_leaves.items():
                for i, leaf in enumerate(label.get_family()):
                    if isinstance(leaf, Leaf):
                        roles[(axis.index, "number", key, i)] = leaf
            if axis._pool is not None:
                for level, spares in axis._pool.spares.items():
                    for i, leaf in enumerate(spares):
                        roles[(axis.index, "spare", level, i)] = leaf
        included = set(roles.values())
        for i, member in enumerate(self.get_family()):
            if (
                isinstance(member, Leaf)
                and member is not self.frame
                and member not in included
            ):
                roles[("extra", i)] = member
        return roles

    def _interpolate_data(
        self, start: CartesianAxes, target: CartesianAxes, alpha: float
    ) -> None:
        self._pool_alpha = alpha
        self._syncing = True
        try:
            for axis, a, b in zip(
                (self.x, self.y), (start.x, start.y), (target.x, target.y), strict=True
            ):
                limits = (1 - alpha) * a.range.value + alpha * b.range.value
                if not isinstance(axis._scale, LinearScale):
                    limits = np.array(
                        axis._scale.limit_range(
                            float(limits[0]), float(limits[1]), MINPOS_UNKNOWN
                        )
                    )
                if not np.array_equal(limits, axis._range_parameter.value):
                    limits.flags.writeable = False
                    axis._range_parameter._value = limits
                    axis._range_parameter._version += 1
                assert axis._pool is not None
                axis._pool.alpha = alpha
            self._compile()
            for axis in (self.x, self.y):
                axis._configure(only_crossing=axis._decoration_seen == axis._versions())
            self._configure_grid()
        finally:
            self._syncing = False

    def resume_updating(self, recursive: bool = True) -> Self:
        """Close a prepared pool and transfer bindings after a replacement.

        Parameters
        ----------
        recursive
            Resume native family updaters when true.
        """
        animation = animation_context(finishing=True)
        super().resume_updating(recursive)
        if self._data_animation:
            self._data_animation = False
            self.submobjects = self._channel_roots
            del self._channel_roots
            for axis in (self.x, self.y):
                pool = axis._pool
                if pool is not None:
                    config = pool.target if self._pool_alpha == 1 else pool.start
                    (
                        axis.locator,
                        axis.minor_locator,
                        axis._explicit,
                        axis._tick_mode,
                    ) = config
                axis._finish_pool()
            self._syncing = True
            try:
                self.x._configure()
                self.y._configure()
                self._configure_grid()
            finally:
                self._syncing = False
        if (
            animation is not None
            and getattr(animation, "replace_mobject_with_target_in_scene", False)
            and isinstance(
                target := getattr(animation, "target_mobject", None), CartesianAxes
            )
        ):
            for artist in tuple(self._artists):
                for leaf in artist.get_family():
                    if isinstance(leaf, Leaf):
                        leaf._event(lc.Rebind(target))
                if isinstance(artist, ScatterPlot):
                    self._artists.remove(artist)
                    target._artists.append(artist)
                    artist._system = target
        return self

    @property
    def updaters(self) -> list[Callable[..., Any]]:
        """Expose synchronisation only to plays that can change this system."""
        return _reported_updaters(self._actual_updaters, self)

    @updaters.setter
    def updaters(self, value: list[Callable[..., Any]]) -> None:
        self._actual_updaters = value

    @property
    def x_range(self) -> FloatArray:
        """Return the current immutable x endpoints."""
        return self.x_axis.range.value

    @property
    def y_range(self) -> FloatArray:
        """Return the current immutable y endpoints."""
        return self.y_axis.range.value

    def _compile(self) -> None:
        axes = (self.x_axis, self.y_axis)
        scaled = [axis._scale.forward(axis.range.value) for axis in axes]
        if self.aspect is not None:
            self._enforce_aspect(scaled)
        lower = np.array([limits[0] for limits in scaled])
        span = np.array([limits[1] - limits[0] for limits in scaled])
        factors = np.divide(
            [self.x_length, self.y_length], span, out=np.zeros(2), where=span != 0
        )
        self._data = Chain(
            (
                *(
                    ScaleNode(axis._scale, index, 2)
                    for index, axis in enumerate(axes)
                    if not isinstance(axis._scale, LinearScale)
                ),
                AffineNode.from_parts(
                    np.diag(factors),
                    np.where(span == 0, 0, self.bounds.lower - lower * factors),
                ),
            )
        )
        self._data_version += 1

    def _enforce_aspect(self, scaled: list[FloatArray]) -> None:
        assert self.aspect is not None
        spans = [abs(float(limits[1] - limits[0])) for limits in scaled]
        lengths = np.array([self.x_length, self.y_length])
        if self.adjustable == "range":
            ratio = (lengths[1] / spans[1]) / (lengths[0] / spans[0])
            if np.isclose(ratio, self.aspect, rtol=1e-12, atol=0):
                return
            index = 1 if ratio > self.aspect else 0
            factor = ratio / self.aspect if index == 1 else self.aspect / ratio
            limits = scaled[index]
            midpoint = float(np.mean(limits))
            limits = midpoint + (limits - midpoint) * factor
            axis = self.get_axis(index)
            normalized = axis._scale.inverse(limits)
            normalized.flags.writeable = False
            # Preserve a range tracker's binding while storing its constrained value.
            axis._range_parameter._value = normalized
            axis._range_parameter._version += 1
            scaled[index] = limits
            return
        index = self._aspect_axis
        if index == 0:
            lengths[0] = lengths[1] * spans[0] / (self.aspect * spans[1])
        else:
            lengths[1] = self.aspect * lengths[0] * spans[1] / spans[0]
        if np.allclose(lengths, [self.x_length, self.y_length], rtol=1e-12, atol=0):
            return
        mapping = self.frame.mapping
        lower = -lengths / 2
        upper = -lower
        nodes = FrameMap.lattice(lower, upper, FRAME_NODES)
        placed = mapping.forward(nodes)
        self.frame.lower, self.frame.upper = lower.copy(), upper.copy()
        self.frame.points = np.repeat(placed, 4, axis=0)
        self.bounds = Box(lower, upper)
        self.x_length, self.y_length = map(float, lengths)
        self.x_axis._resize(self.x_length)
        self.y_axis._resize(self.y_length)

    def _data_dirty(self) -> bool:
        return not self._syncing and (
            self.x_axis._range_seen != self.x_axis._range_parameter.version
            or self.y_axis._range_seen != self.y_axis._range_parameter.version
            or self.x_axis._style_changed()
            or self.y_axis._style_changed()
        )

    def _sync_data(self) -> None:
        if not self._data_dirty():
            return
        axes = (self.x_axis, self.y_axis)
        range_changed = any(
            axis._range_seen != axis._range_parameter.version for axis in axes
        )
        changed = [axis for axis in axes if axis._decoration_seen != axis._versions()]
        if not range_changed and not changed:
            return
        self._syncing = True
        try:
            if range_changed:
                self._compile()
            for axis in axes if range_changed else changed:
                axis._configure(only_crossing=axis not in changed)
            self._configure_grid()
        finally:
            self._syncing = False

    def _poll(self) -> None:
        parameters = (*self.x_axis._parameters(), *self.y_axis._parameters())
        token = playback_context()
        if token is not None and token == self._poll_token:
            return
        self._poll_token = token
        self._token += 1
        for parameter in parameters:
            parameter.poll(self._token)
        for artist in self._artists:
            artist._poll()
        self._sync_data()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        if self._moving_query is None or self._moving_query[0] is not moving:
            self._moving_query = (moving, self._sync_needed(moving))
        return self._moving_query[1]

    def _sync_needed(self, moving: frozenset[Mobject]) -> bool:
        if not hasattr(self, "frame"):
            return False
        if self.frame in moving:
            return True
        for axis in (self.x_axis, self.y_axis):
            for parameter in axis._parameters():
                tracker = parameter.tracker
                if tracker is not None and (callable(tracker) or tracker in moving):
                    return True
        for artist in self._artists:
            if isinstance(artist, _CurvePlot) and artist._needs_sync(moving):
                return True
        return False

    def _mapping(self) -> SystemMap:
        self._sync_data()
        return SystemMap(self._data, self.frame.mapping)

    def c2p(self, *coords: ArrayLike) -> FloatArray:
        """Convert scalar coordinates, coordinate arrays or rows to scene points.

        Parameters
        ----------
        *coords
            Manim-style coordinate arguments.

        Returns
        -------
        FloatArray
            Shape (3,), (3, n), or (n, 3), following the input convention.

        Raises
        ------
        ValueError
            If a coordinate is non-finite or outside its scale's domain, or the
            configured data range is collapsed. Conversions raise instead of
            returning NaN and never clamp a value into the domain.
        """
        values = np.asarray(coords, dtype=float)
        if not np.isfinite(values).all():
            index = tuple(int(i) for i in np.argwhere(~np.isfinite(values))[0])
            raise ValueError(f"coords at index {index} must be finite")
        rows = values.ndim == 3
        if rows:
            values = values[0]
            if len(values) == 1:
                values = values[0]
        elif values.ndim == 2 and values.shape[0] == 1:
            values = values[0]
        scalar = values.ndim == 1
        data = np.atleast_2d(values) if scalar or rows else values.T
        if data.shape[1] == 1:
            data = np.column_stack((data, np.zeros(len(data))))
        data = data[:, :2]
        mapping = self._mapping()
        if mapping.frame.is_singular:
            raise ValueError("frame is singular")
        valid = mapping.valid(data)
        if not valid.all():
            sample_index = int(np.flatnonzero(~valid)[0])
            raise ValueError(
                f"coords at index {sample_index} must be inside the scale domain"
            )
        result = mapping.to_screen(data)
        if not np.isfinite(result).all():
            raise ValueError("coords map to a non-finite point")
        return result[0] if scalar else result if rows else result.T

    coords_to_point = c2p

    def p2c(self, point: ArrayLike) -> FloatArray:
        """Invert scene points, refusing singular frames and off-plane points.

        Parameters
        ----------
        point
            One scene point or rows of scene points.

        Returns
        -------
        FloatArray
            Coordinates of shape (2,) or (n, 2).

        Raises
        ------
        ValueError
            If a point is non-finite, outside the frame's plane tolerance, or has
            no valid inverse, including a singular frame or collapsed data range.
            Invalid conversions raise rather than returning NaN or clamping.

        Notes
        -----
        A point within 1e-6 times the frame size of the fitted plane is projected
        onto it. For a non-affine frame, inversion returns the branch reached by
        Newton iteration from the affine fit's guess; failure to converge raises.
        """
        values = np.asarray(point, dtype=float)
        if values.ndim not in (1, 2) or values.shape[-1] != 3:
            raise ValueError("point must have shape (3,) or (n, 3)")
        if not np.isfinite(values).all():
            index = tuple(int(i) for i in np.argwhere(~np.isfinite(values))[0])
            raise ValueError(f"point at index {index} must be finite")
        self._sync_data()
        local = self.frame.mapping.inverse(np.atleast_2d(values))
        result = self._data.inverse(local[:, :2])
        if not np.isfinite(result).all():
            raise ValueError("point maps to non-finite coordinates")
        return result[0] if values.ndim == 1 else result

    point_to_coords = p2c

    def __matmul__(self, coords: ArrayLike) -> FloatArray:
        return self.c2p(coords)

    def set_x_range(self, x_range: Sequence[float]) -> Self:
        """Set x endpoints, retaining the existing locator.

        Parameters
        ----------
        x_range
            New endpoints and an optional ignored locator step.
        """
        self.x_axis.range = _range(x_range, "x_range")
        return self

    def set_y_range(self, y_range: Sequence[float]) -> Self:
        """Set y endpoints, retaining the existing locator.

        Parameters
        ----------
        y_range
            New endpoints and an optional ignored locator step.
        """
        self.y_axis.range = _range(y_range, "y_range")
        return self

    def get_origin(self) -> FloatArray:
        """Return the mapped data origin, without an additional range clamp."""
        return self.c2p(0, 0)

    def get_axes(self) -> VGroup:
        """Return both axis decorations."""
        return self.axes

    def get_axis(self, index: int) -> Axis:
        """Return an axis by index.

        Parameters
        ----------
        index
            Zero for x, one for y.
        """
        return (self.x_axis, self.y_axis)[index]

    def get_x_axis(self) -> Axis:
        """Return the x decoration."""
        return self.x_axis

    def get_y_axis(self) -> Axis:
        """Return the y decoration."""
        return self.y_axis

    def get_x_unit_size(self) -> float:
        """Return the x axis's unit size."""
        return self.x_axis.get_unit_size()

    def get_y_unit_size(self) -> float:
        """Return the y axis's unit size."""
        return self.y_axis.get_unit_size()

    def add_coordinates(
        self,
        *axes_numbers: Iterable[float] | dict[float, object] | None,
        **kwargs: Unpack[_NumberOptions],
    ) -> Self:
        """Attach numbers or explicit labels to each selected axis.

        Parameters
        ----------
        *axes_numbers, **kwargs
            Native per-axis positions or dictionaries and label options.
        """
        self.coordinate_labels = VGroup()
        for axis, values in zip(
            (self.x_axis, self.y_axis), axes_numbers or (None, None), strict=False
        ):
            if isinstance(values, dict):
                axis.add_labels(values, **cast(dict[str, Any], kwargs))
                labels = axis.labels
            else:
                axis.add_numbers(values, **kwargs)
                labels = axis.numbers
            self.coordinate_labels.add(labels)
        return self

    def _axis_label(
        self,
        label: object,
        index: int,
        edge: ArrayLike,
        direction: ArrayLike,
        buff: float,
    ) -> BoundLabel:
        result = _label(label)
        result.next_to(
            self.get_axis(index).get_edge_center(np.asarray(edge, dtype=float)),
            direction=np.asarray(direction, dtype=float),
            buff=buff,
        )
        result.shift_onto_screen(buff=0.25)
        return BoundLabel(result, self)

    def get_x_axis_label(
        self,
        label: object,
        edge: ArrayLike = (1, 1, 0),
        direction: ArrayLike = (1, 1, 0),
        buff: float = 0.1,
        **kwargs: Unpack[_VMStyle],
    ) -> BoundLabel:
        """Return a bound x-axis title.

        Parameters
        ----------
        label, edge, direction, buff, **kwargs
            Native label and placement options.
        """
        return self._axis_label(
            label, 0, edge, direction, buff, **cast(dict[str, Any], kwargs)
        )

    def get_y_axis_label(
        self,
        label: object,
        edge: ArrayLike = (1, 1, 0),
        direction: ArrayLike = (1, 0.5, 0),
        buff: float = 0.1,
        **kwargs: Unpack[_VMStyle],
    ) -> BoundLabel:
        """Return a bound y-axis title.

        Parameters
        ----------
        label, edge, direction, buff, **kwargs
            Native label and placement options.
        """
        return self._axis_label(
            label, 1, edge, direction, buff, **cast(dict[str, Any], kwargs)
        )

    def get_axis_labels(self, x_label: object = "x", y_label: object = "y") -> VGroup:
        """Return bound titles for both axes.

        Parameters
        ----------
        x_label, y_label
            Math strings or native label mobjects.
        """
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label), self.get_y_axis_label(y_label)
        )
        return self.axis_labels

    def get_graph_label(
        self,
        graph: FunctionPlot,
        label: object = "f(x)",
        x_val: float | None = None,
        direction: ArrayLike = (1, 0, 0),
        buff: float = 0.25,
        color: ParsableManimColor | None = None,
        dot: bool = False,
        dot_config: dict[str, Any] | None = None,
    ) -> BoundLabel:
        """Return a graph label bound to its system and source.

        Parameters
        ----------
        graph, label, x_val, direction, buff, color, dot, dot_config
            Native graph-label arguments.
        """

        def anchor() -> FloatArray:
            # Since task 11 a plot's source is typed as the base Source.
            source_range = getattr(graph.source, "_range", None)
            if x_val is None:
                limits = (
                    self.x_axis.range.value if source_range is None else source_range
                )
                for value in np.linspace(limits[1], limits[0], 100):
                    point = self.c2p(graph.source.at(float(value))[0])
                    if point[1] < config.frame_y_radius:
                        break
            else:
                point = self.c2p(graph.source.at(x_val)[0])
            local = self.frame.mapping.inverse(point[None, :])
            if graph._own.nodes:
                local = graph._own.forward(local)
            return cast(FloatArray, local[0])

        point = self.frame.mapping.forward(anchor()[None, :])[0]
        result = _label(label).set_color(graph.get_color() if color is None else color)
        result.next_to(
            point, np.asarray(direction, dtype=float), buff=buff
        ).shift_onto_screen()
        if dot:
            result.add(_label(Dot(point=point, **(dot_config or {}))))
        bound = BoundLabel(result, self, anchor, graph)
        if dot:
            bound.dot = bound[-1]
        return bound

    def _configure_grid(self) -> None:
        self.x_axis._configure_grid()
        self.y_axis._configure_grid()

    @overload
    def plot(
        self,
        function: Callable[..., Any],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        **kwargs: object,
    ) -> FunctionPlot: ...

    @overload
    def plot(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> LinePlot: ...

    def plot(
        self,
        *args: object,
        **kwargs: object,
    ) -> FunctionPlot | LinePlot:
        """Create and register a function plot or an array line.

        Parameters
        ----------
        *args
            Function, optional x_range and use_vectorized; or array xs and ys.
        **kwargs
            Named inputs, function parameters, native styles and sampling options.

        Notes
        -----
        A callable creates a FunctionPlot; array inputs create a LinePlot. Callable
        arguments after the input coordinate become versioned plot parameters,
        with values or bindings supplied by keyword. A parameter whose name is a
        native style keyword raises ValueError.

        The function runs again on resampling. A lambda closing over a loop
        variable sees its last value then: bind it with ``lambda x, k=k: k * x``
        to preserve each iteration's value. The default also exposes k as a plot
        parameter, which can be changed with ``curve.set_parameters(k=2)``.

        Manim's x_range, use_vectorized, use_smoothing, discontinuities and dt keep
        their meaning. A range step caps sample spacing independently of ticks.
        Curves split at invalid samples and poles, and clip to the viewport by
        default. Use ``clip=False`` to disable clipping or a numeric margin in
        scene units to expand or narrow it. Uncoloured plots advance a cycle whose
        first colour is white; an explicit colour does not advance it.
        """
        if args:
            function = args[0]
        elif "function" in kwargs:
            function = kwargs.pop("function")
        else:
            function = kwargs.pop("xs", None)
        if callable(function):
            if len(args) > 3:
                raise TypeError("plot accepts function, x_range and use_vectorized")
            function, _ = _parameterize(function, kwargs)
            x_range = args[1] if len(args) > 1 else kwargs.pop("x_range", None)
            use_vectorized = (
                args[2] if len(args) > 2 else kwargs.pop("use_vectorized", False)
            )
            artist = FunctionPlot(
                function,
                self,
                cast(Sequence[float] | None, x_range),
                cast(bool, use_vectorized),
                **cast(dict[str, Any], kwargs),
            )
            self.add(artist)
            return artist
        if len(args) > 2:
            raise TypeError("plot accepts xs and ys for an array line")
        ys = args[1] if len(args) > 1 else kwargs.pop("ys", None)
        return self.line(
            cast(ArrayLike, function),
            cast(ArrayLike | None, ys),
            **cast(_ArtistOptions, kwargs),
        )

    def line(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> LinePlot:
        """Create and register a straight array line.

        Parameters
        ----------
        xs, ys
            Separate coordinates, or pairs in xs with ys omitted.
        **kwargs
            Native VMobject styles.
        """
        artist = LinePlot(xs, self, ys, **kwargs)
        self.add(artist)
        return artist

    def scatter(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        marker: Mobject | Marker | None = None,
        label: str | None = None,
        clip: bool | float = True,
        **kwargs: Unpack[_VMStyle],
    ) -> ScatterPlot:
        """Create and register independent markers in input order.

        Parameters
        ----------
        xs, ys
            Separate coordinates, or pairs in xs with ys omitted.
        marker
            Marker enum or native template, defaulting to Dot().
        label
            Legend entry text, or None to omit this artist.
        clip
            True, False, or a clipping margin in scene units.
        **kwargs
            Native VMobject styles for the markers.
        """
        artist = ScatterPlot(
            xs, self, ys, marker=marker, label=label, clip=clip, **kwargs
        )
        self.add(artist)
        return artist

    def plot_parametric_curve(
        self,
        function: Callable[..., Any],
        use_vectorized: bool = False,
        **kwargs: Unpack[_ParametricOptions],
    ) -> ParametricPlot:
        """Create and register a parameterized curve.

        Parameters
        ----------
        function
            Callable returning coordinates or coordinate arrays.
        use_vectorized
            Evaluate arrays instead of scalars when true.
        **kwargs
            t_range (default (0, 1)), sampling options and native styles.
        """
        artist = ParametricPlot(function, self, use_vectorized, **kwargs)
        self.add(artist)
        return artist

    def plot_line_graph(
        self,
        x_values: ArrayLike,
        y_values: ArrayLike,
        z_values: ArrayLike | None = None,
        line_color: ParsableManimColor = PURE_YELLOW,
        add_vertex_dots: bool = True,
        vertex_dot_radius: float = DEFAULT_DOT_RADIUS,
        vertex_dot_style: _VMStyle | None = None,
        **kwargs: Unpack[_ArtistOptions],
    ) -> VDict:
        """Return Manim's named line and optional vertex-dot groups.

        Parameters
        ----------
        x_values, y_values, z_values
            Vertex coordinates; the optional z coordinate is ignored in 2D.
        line_color
            Line stroke color, defaulting to PURE_YELLOW.
        add_vertex_dots
            Include a ScatterPlot under vertex_dots when true.
        vertex_dot_radius, vertex_dot_style
            Native Dot radius and style options.
        **kwargs
            Native styles for the line.
        """
        options = kwargs.copy()
        options["color"] = line_color
        line = self.line(x_values, y_values, **options)
        result = VDict([("line_graph", line)])
        if add_vertex_dots:
            marker = Dot(radius=vertex_dot_radius, **(vertex_dot_style or {}))
            result.add(
                [
                    (
                        "vertex_dots",
                        self.scatter(
                            x_values,
                            y_values,
                            marker=marker,
                            clip=kwargs.get("clip", True),
                        ),
                    )
                ]
            )
        return result

    def i2gc(self, x: float, graph: _CurvePlot) -> tuple[float, float]:
        """Evaluate a bound graph's source exactly or by linear interpolation.

        Parameters
        ----------
        x
            Source input, independent of the sampled anchors.
        graph
            Function, array line or parametric artist bound to this system.

        Returns
        -------
        tuple of float
            The two data coordinates.
        """
        if not isinstance(graph, _CurvePlot) or graph._system is not self:
            raise ValueError("graph must be bound to this system")
        coords = graph.source.at(x)[0]
        return float(coords[0]), float(coords[1])

    input_to_graph_coords = i2gc

    def i2gp(self, x: float, graph: _CurvePlot) -> FloatArray:
        """Map an exact source query to a scene point.

        Parameters
        ----------
        x
            Source input.
        graph
            Artist bound to this system.

        Returns
        -------
        FloatArray
            Scene point of shape (3,).
        """
        return self.c2p(*self.i2gc(x, graph))

    input_to_graph_point = i2gp

    def legend(
        self,
        location: str = "upper right",
        *,
        font_size: float = 24,
        buff: float = 0.25,
    ) -> Legend:
        """Create a bound legend for labelled artists in registration order.

        Parameters
        ----------
        location
            One of upper right, upper left, lower left or lower right.
        font_size, buff
            Native text size and entry/corner spacing in scene units.

        Returns
        -------
        Legend
            The newly created legend, attached to this system's family.
        """
        locations = {
            "upper right": (1, 1),
            "upper left": (-1, 1),
            "lower left": (-1, -1),
            "lower right": (1, -1),
        }
        if location not in locations:
            raise ValueError(
                "location must be upper right, upper left, lower left or lower right"
            )
        artists = [a for a in self._artists if a.get_label() is not None]
        if not artists:
            raise ValueError("legend requires an artist with a label")
        legend = Legend(*artists, font_size=font_size, buff=buff)
        corner = np.array([*locations[location], 0.0], dtype=float)
        local = np.where(corner[:2] > 0, self.bounds.upper, self.bounds.lower)
        legend.shift(
            self.frame.mapping.forward(local[None])[0]
            - corner * buff
            - legend.get_corner(corner)
        )
        previous = self.get_legend()
        if previous is not None:
            self.submobjects.remove(previous)
        self.submobjects.append(legend)
        self._legend = legend
        return legend

    def get_legend(self) -> Legend | None:
        """Return the last legend created by this system, or None."""
        return getattr(self, "_legend", None)

    def get_legend_handles_labels(self) -> tuple[list[Mobject], list[str]]:
        """Return independent handles and labels in registration order."""
        artists = [a for a in self._artists if a.get_label() is not None]
        return (
            [_handle(a) for a in artists],
            [cast(str, a.get_label()) for a in artists],
        )

    def scale(
        self,
        scale_factor: float,
        scale_stroke: bool = False,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Scale the frame and optionally all registered artists' strokes.

        Parameters
        ----------
        scale_factor, scale_stroke, about_point, about_edge
            Native VMobject scaling options.
        """
        super().scale(
            scale_factor,
            scale_stroke=scale_stroke,
            about_point=about_point,
            about_edge=about_edge,
        )
        if scale_stroke:
            for artist in self._artists:
                for leaf in artist.get_family():
                    if isinstance(leaf, VMobject):
                        leaf.set_stroke(
                            width=abs(scale_factor) * leaf.get_stroke_width(),
                            family=False,
                        )
                        leaf.set_stroke(
                            width=abs(scale_factor)
                            * leaf.get_stroke_width(background=True),
                            background=True,
                            family=False,
                        )
        return self

    @property
    def artists(self) -> tuple[_CurvePlot | ScatterPlot, ...]:
        """Return registered artists in registration order, excluding copies."""
        return tuple(self._artists)

    def add(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Register artists without parenting them.

        Parameters
        ----------
        *artists
            Artists with this system as their single owner.

        Notes
        -----
        ``ax.add(curve)`` registers the curve without making it a submobject,
        unlike Manim's add. Add both axes and curves to the Scene explicitly.
        Registration makes the curve follow the system's placement and data.
        Adding it again is harmless; binding it to another system raises until
        it is unregistered with remove.
        """
        for artist in artists:
            if not isinstance(artist, (_CurvePlot, ScatterPlot)):
                raise TypeError("artists must be plotting artists")
            if artist._system is not None and artist._system is not self:
                raise ValueError("artist is bound to another system")
            if artist not in self._artists:
                if artist._system is None:
                    artist._system = self
                    for leaf in artist.get_family():
                        if isinstance(leaf, _CurvePlot):
                            leaf._system = self
                            leaf._frozen_frame = None
                            leaf._parameter_token = -1
                            leaf._frame_seen = -1
                            leaf.refresh()
                self._artists.append(artist)
        return self

    def remove(self, *artists: Mobject | Iterable[VMobject]) -> Self:
        """Unregister artists so that they may be bound to another system.

        Parameters
        ----------
        *artists
            Artists to unregister.
        """
        for artist in artists:
            if artist not in self._artists:
                raise ValueError("artist is not registered with this system")
            assert isinstance(artist, (_CurvePlot, ScatterPlot))
            for leaf in artist.get_family():
                if isinstance(leaf, _CurvePlot):
                    leaf._ensure()
                    leaf._system = None
            self._artists.remove(artist)
            artist._system = None
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result._artists = _ArtistRegistry()
        for key, value in self.__dict__.items():
            if key in {"bounds", "_data"}:
                result.__dict__[key] = value
            elif key == "_moving_query":
                result.__dict__[key] = None
            elif key != "_artists":
                result.__dict__[key] = copy.deepcopy(value, memo)
        return result


class NumberPlane(CartesianAxes):
    """Draw Cartesian axes with Manim's major and faded background lines.

    Parameters
    ----------
    x_range, y_range
        Endpoints and major spacing, defaulting to the frame radii.
    x_length, y_length
        Axis lengths; omitted lengths use unit size one.
    background_line_style, faded_line_style
        Native grid style dictionaries.
    faded_line_ratio
        Number of subdivisions of each major interval.
    make_smooth_after_applying_functions
        Native VMobject nonlinear-transform smoothing option.
    **kwargs
        CartesianAxes constructor options.
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        background_line_style: dict[str, Any] | None = None,
        faded_line_style: dict[str, Any] | None = None,
        faded_line_ratio: int = 1,
        make_smooth_after_applying_functions: bool = True,
        **kwargs: object,
    ) -> None:
        options: dict[str, Any] = dict(kwargs)
        if not isinstance(faded_line_ratio, int):
            raise TypeError("faded_line_ratio must be an int")
        if faded_line_ratio < 0:
            raise ValueError("faded_line_ratio must be nonnegative")
        xr = (
            list(x_range)
            if x_range is not None
            else [-config.frame_x_radius, config.frame_x_radius, 1]
        )
        yr = (
            list(y_range)
            if y_range is not None
            else [-config.frame_y_radius, config.frame_y_radius, 1]
        )
        common = merge_dicts_recursively(
            {
                "stroke_width": 2,
                "include_ticks": False,
                "include_tip": False,
                "line_to_number_buff": 0.1,
                "label_direction": [1, -1, 0],
                "font_size": 24,
            },
            options.pop("axis_config", {}),
        )
        y_options = merge_dicts_recursively(
            {"label_direction": [1, -1, 0]}, options.pop("y_axis_config", {})
        )
        if (
            x_length is None
            and "unit_size" not in common
            and "unit_size" not in options.get("x_axis_config", {})
        ):
            x_length = abs(xr[1] - xr[0])
        if (
            y_length is None
            and "unit_size" not in common
            and "unit_size" not in y_options
        ):
            y_length = abs(yr[1] - yr[0])
        self.background_line_style = {
            "stroke_color": BLUE_D,
            "stroke_width": 2,
            "stroke_opacity": 1,
            **(background_line_style or {}),
        }
        self.faded_line_style = faded_line_style
        if self.faded_line_style is None:
            self.faded_line_style = {
                key: value * 0.5 if isinstance(value, (int, float)) else value
                for key, value in self.background_line_style.items()
            }
        self.faded_line_ratio = faded_line_ratio
        self.background_lines = VGroup()
        self.faded_lines = VGroup()
        super().__init__(
            xr,
            yr,
            x_length,
            y_length,
            axis_config=common,
            y_axis_config=y_options,
            make_smooth_after_applying_functions=make_smooth_after_applying_functions,
            **options,
        )
        for axis in (self.x_axis, self.y_axis):
            axis.minor_locator = (
                MinorCountLocator(axis.locator, faded_line_ratio - 1)
                if faded_line_ratio > 1
                else None
            )
        self.submobjects[:0] = [self.faded_lines, self.background_lines]
        self._configure_grid()

    @property
    def background_lines(self) -> VGroup:
        """Return the current background lines family."""
        if hasattr(self, "_syncing"):
            self._sync_data()
        return self._background_lines

    @background_lines.setter
    def background_lines(self, value: VGroup) -> None:
        self._background_lines = value

    @property
    def faded_lines(self) -> VGroup:
        """Return the current faded lines family."""
        if hasattr(self, "_syncing"):
            self._sync_data()
        return self._faded_lines

    @faded_lines.setter
    def faded_lines(self, value: VGroup) -> None:
        self._faded_lines = value

    def _configure_grid(self) -> None:
        if not hasattr(self, "x_axis") or not hasattr(self, "y_axis"):
            return
        ratio = max(1, self.faded_line_ratio)
        major: list[VMobject] = []
        minor: list[VMobject] = []
        mapping = self.frame.mapping
        for index in (1, 0):
            perpendicular = self.get_axis(index)
            parallel = self.get_axis(1 - index)
            step = perpendicular._step / ratio
            lo, hi = perpendicular.range.value
            cross = float(np.clip(0, min(lo, hi), max(lo, hi)))
            positive_stop, negative_stop = min(hi - lo, hi), max(lo - hi, lo)
            positive = [
                k * step for k in range(1, max(1, int(np.ceil(positive_stop / step))))
            ]
            negative = [
                -k * step for k in range(1, max(1, int(np.ceil(-negative_stop / step))))
            ]
            grid: dict[object, GridLeaf] = {}
            axis_major = []
            for values in ([0.0], positive, negative):
                for k, value in enumerate(values):
                    level = "major" if (k + 1) % ratio == 0 else "minor"
                    endpoints = np.zeros((2, 2))
                    endpoints[:, index] = cross + value
                    endpoints[:, 1 - index] = parallel.range.value
                    points = self._data.forward(endpoints)
                    local = points[0] + np.linspace(0, 1, 4)[:, None] * (
                        points[1] - points[0]
                    )
                    locator = (
                        perpendicular.minor_locator
                        if level == "minor"
                        else perpendicular.locator
                    )
                    key = (
                        level,
                        (locator or perpendicular.locator).key(float(cross + value)),
                    )
                    leaf = perpendicular._grid_leaves.get(key)
                    if leaf is None:
                        leaf = GridLeaf(mapping.forward(local), self)
                        leaf.set_style(
                            **(
                                self.background_line_style
                                if level == "major"
                                else (self.faded_line_style or {})
                            )
                        )
                        leaf.set_style(**perpendicular._grid_styles.get(level, {}))
                    else:
                        leaf._cache = mapping.forward(local)
                    leaf.level = level
                    leaf.value = cross + value
                    if not perpendicular._grid_visible.get(level, True):
                        continue
                    (major if level == "major" else minor).append(leaf)
                    grid[key] = leaf
                    if level == "major":
                        axis_major.append(leaf)
            perpendicular._grid_leaves = grid
            perpendicular._grid._replace(grid)
            if index == 1:
                self.x_lines = VGroup(*axis_major)
            else:
                self.y_lines = VGroup(*axis_major)
        self.background_lines.submobjects = major
        self.faded_lines.submobjects = minor
        self.background_lines.set_style(**self.background_line_style, family=False)
        self.faded_lines.set_style(**(self.faded_line_style or {}), family=False)


Axes = CartesianAxes
