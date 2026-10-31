"""Cartesian coordinate systems, registration and frame synchronisation."""

from __future__ import annotations

import copy
import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal, NoReturn, Self, Unpack, cast, overload

import numpy as np
from manim import (
    BLACK,
    BLUE,
    BLUE_D,
    DEFAULT_DOT_RADIUS,
    GREEN,
    MED_SMALL_BUFF,
    PURE_YELLOW,
    WHITE,
    DashedLine,
    Dot,
    Line,
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

import manim_plots as mp
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
    resolve_categories,
)
from manim_plots.mobjects.context import (
    _PlaybackToken,
    animation_context,
    data_interpolation,
    playback_context,
    writer_context,
)
from manim_plots.mobjects.errorbar import ErrorBars
from manim_plots.mobjects.fields import (
    ArrowVectorField,
    StreamLines,
    _get_vector,
    _implicit_curve,
)
from manim_plots.mobjects.helpers import (
    FilledRegion,
    HelperGroup,
    HelperLine,
    _annotate_2d,
    _area,
    _crosshair,
    _DerivedPlot,
    _drop,
    _DropOptions,
    _end_label,
    _fill_between,
    _graph,
    _HelperOptions,
    _number,
    _parameter,
    _reference,
    _riemann,
    _secant,
    _SlopeOptions,
    _span,
    _t_label,
    _tangent_helper,
    _TangentOptions,
    _verticals,
)
from manim_plots.mobjects.leaves import (
    BoundLabel,
    FrameLeaf,
    GridLeaf,
    Leaf,
    _ArtistOptions,
    _become_target,
    _ClipInput,
    _label,
    _NumberOptions,
    _ParametricOptions,
    _reported_updaters,
    _synchronise,
    _VMStyle,
)
from manim_plots.mobjects.legend import Legend, _handle
from manim_plots.mobjects.themes import Theme, _resolve_cycle, _resolve_theme

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
        self._clock = [0]
        self._refs: list[
            tuple[int, weakref.ReferenceType[_CurvePlot | ScatterPlot | ErrorBars]]
        ] = []

    def __iter__(self) -> Iterator[_CurvePlot | ScatterPlot | ErrorBars]:
        self._refs = [(order, ref) for order, ref in self._refs if ref() is not None]
        return iter(artist for _, ref in self._refs if (artist := ref()) is not None)

    def __contains__(self, artist: object) -> bool:
        return any(ref() is artist for _, ref in self._refs)

    def append(self, artist: _CurvePlot | ScatterPlot | ErrorBars) -> None:
        list(self)
        self._refs.append((self._clock[0], weakref.ref(artist)))
        self._clock[0] += 1

    def remove(self, artist: _CurvePlot | ScatterPlot | ErrorBars) -> None:
        self._refs = [(order, ref) for order, ref in self._refs if ref() is not artist]


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
    frame
        Origin axes or a box border; an explicit choice overrides the theme.
    theme
        Named preset, Theme or mapping of Theme fields. None uses the module
        default. Explicit constructor options and later decoration calls win.
    cycle
        Named colour cycle or nonempty colour sequence, overriding the theme.
    x_scale, y_scale
        Data scales or the names linear, log and symlog. Manim's scaling option
        retains its exponent-range convention for LogBase.
    aspect
        Optional ratio of a y unit's scene length to an x unit's scene length.
    adjustable
        Adapt an omitted length or widen a range to satisfy the aspect ratio.
    **kwargs
        Native VGroup style and mobject options.

    Attributes
    ----------
    parent
        Root system for a twin, or None for an independent system.
    twins
        Twins created from this root, in creation order.
    theme
        Preset applied at construction, without any per-frame theme work.

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
        tips: bool | None = None,
        *,
        frame: Literal["origin", "box"] | None = None,
        theme: str | Theme | Mapping[str, Any] | None = None,
        cycle: str | Sequence[ParsableManimColor] | None = None,
        x_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        y_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        aspect: float | None = None,
        adjustable: Literal["length", "range"] = "length",
        **kwargs: Unpack[_VMStyle],
    ) -> None:
        if config.renderer == RendererType.OPENGL:
            raise ValueError("CartesianAxes requires the Cairo renderer")
        self.theme = _resolve_theme(theme)
        if frame not in (None, "origin", "box"):
            raise ValueError("frame must be origin or box")
        self._frame_style = frame or (
            "box" if self.theme.position == "border" and self.theme.box else "origin"
        )
        if frame is not None:
            self.theme = replace(
                self.theme,
                position="border" if frame == "box" else "origin",
                box=frame == "box",
                tips=False if frame == "box" else self.theme.tips,
            )
        self._cycle = _resolve_cycle(self.theme.cycle if cycle is None else cycle)
        tips = self.theme.tips if tips is None else tips
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
        self.parent: CartesianAxes | None = None
        self._twins: list[CartesianAxes] = []
        self._twin_axis: int | None = None
        self._artists = _ArtistRegistry()
        self._field_steps = tuple(float(r[2]) if len(r) == 3 else 1.0 for r in ranges)
        self._data_animation = False
        self._channel_frame_moves = False
        self._pool_warned = False
        self._channel_roots: list[VMobject] = []
        self._has_mirrors = False
        self._has_secondary_axes = False
        self._channel_decorations: tuple[Axis, ...] = ()
        self._channel_decoration_versions: tuple[int, ...] = ()
        self._channel_decoration_leaves: tuple[Leaf, ...] = ()
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
        self._channel_frame = self.frame
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
            axis._label_direction_custom = any("label_direction" in c for c in given)
        self._ranges: tuple[Axis, ...] = (self.x_axis, self.y_axis)
        self.axes = VGroup(self.x_axis, self.y_axis)
        self.x, self.y = self.x_axis, self.y_axis
        self.submobjects = [self.x_axis, self.y_axis, self.frame]
        self._compile()
        for axis in self._ranges:
            if axis.include_numbers or axis.numbers_to_include is not None:
                axis.add_numbers(axis.numbers_to_include)
        for axis in self._ranges:
            axis._decoration_seen = axis._versions()
        self._syncing = False
        if any(not isinstance(scale, LinearScale) for scale in scales):
            self._syncing = True
            try:
                self.x_axis._configure()
                self.y_axis._configure()
            finally:
                self._syncing = False
        if not isinstance(self, NumberPlane):
            for axis in (self.x, self.y):
                if self.theme.position == "border":
                    axis.set_position("bottom" if axis.index == 0 else "left")
                if self.theme.tick_direction is not None:
                    axis.set_tick_style(direction=self.theme.tick_direction)
                if self.theme.minor_ticks:
                    axis.set_locator(
                        axis.locator,
                        minor=MinorCountLocator(axis.locator, self.theme.minor_ticks),
                    )
                if self.theme.box:
                    axis.mirror()
                for level in self.theme.grid:
                    style = dict(self.theme.grid_style)
                    if level == "minor":
                        style.update(self.theme.minor_grid_style)
                    axis.set_grid(level, **style)
        self.add_updater(_synchronise)

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"CartesianAxes has no attribute {name!r}")

    @property
    def frame_style(self) -> str:
        """Return the selected origin or box frame style."""
        return self._frame_style

    @property
    def twins(self) -> tuple[CartesianAxes, ...]:
        """Return this root system's twins in creation order."""
        return tuple(self._twins)

    def twinx(
        self,
        y_range: Sequence[float] | None = None,
        *,
        y_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        y_axis_config: dict[str, Any] | None = None,
        offset: float | None = None,
    ) -> CartesianAxes:
        """Add an independent y map on the shared frame and x axis.

        Parameters
        ----------
        y_range, y_scale, y_axis_config
            Constructor options for the new y axis; the range defaults to the root's.
        offset
            Outward spacing from the previous right axis, defaulting to 0.9.
            The first right axis sits on the rectangle's border.

        Returns
        -------
        CartesianAxes
            A system whose parent is the root and whose artists use the new map.
        """
        return self._twin(1, y_range, y_scale, y_axis_config, offset)

    def twiny(
        self,
        x_range: Sequence[float] | None = None,
        *,
        x_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        x_axis_config: dict[str, Any] | None = None,
        offset: float | None = None,
    ) -> CartesianAxes:
        """Add an independent x map on the shared frame and y axis.

        Parameters
        ----------
        x_range, x_scale, x_axis_config
            Constructor options for the new x axis; the range defaults to the root's.
        offset
            Outward spacing from the previous top axis, defaulting to 0.9.
            The first top axis sits on the rectangle's border.

        Returns
        -------
        CartesianAxes
            A system whose parent is the root and whose artists use the new map.
        """
        return self._twin(0, x_range, x_scale, x_axis_config, offset)

    def twin(
        self,
        x: Axis | CartesianAxes | None = None,
        y: Axis | CartesianAxes | None = None,
    ) -> CartesianAxes:
        """Return the unique system of two existing axes in this family.

        Parameters
        ----------
        x, y
            An existing x or y axis, or a system supplying that axis. None keeps
            the calling system's axis. Mirrors and secondary axes are decorations
            and cannot supply a map.

        Returns
        -------
        CartesianAxes
            The existing system of this pair, or a new twin drawing no axes.

        Raises
        ------
        ValueError
            If x or y is not a map axis of the requested direction in this family.
        TypeError
            If x or y is neither an axis, a system nor None.

        Examples
        --------
        The four corners share one frame and bind plots to any pair of axes:

        >>> right = ax.twinx(y_range=(0, 1))  # bottom x, right y
        >>> top = ax.twiny(x_range=(0, 50))  # top x, left y
        >>> corner = ax.twin(x=top, y=right)  # top x, right y
        >>> curve = corner.plot(lambda x: x / 50)
        """
        root = (
            self.parent
            if self._twin_axis is not None and self.parent is not None
            else self
        )
        axes = []
        for index, value in enumerate((x, y)):
            name = "x" if index == 0 else "y"
            if value is None:
                axis = self.get_axis(index)
            elif isinstance(value, CartesianAxes):
                axis = value.get_axis(index)
            elif isinstance(value, Axis):
                axis = value
            else:
                raise TypeError(f"{name} must be an Axis or CartesianAxes")
            if not any(axis is s.get_axis(index) for s in root._systems()):
                raise ValueError(f"{name} must be a map axis of this family")
            axes.append(axis)
        for system in root._systems():
            if system.x is axes[0] and system.y is axes[1]:
                return system
        pair = CartesianAxes(
            axes[0].range.value.tolist(),
            axes[1].range.value.tolist(),
            root.x_length,
            root.y_length,
            x_scale=axes[0]._scale,
            y_scale=axes[1]._scale,
            theme=replace(root.theme, box=False, grid=()),
            cycle=root._cycle,
        )
        pair.x = pair.x_axis = axes[0]
        pair.y = pair.y_axis = axes[1]
        pair._ranges = tuple(axes)
        pair.axes = VGroup(*axes)
        pair.submobjects = []
        root._attach_twin(pair, -1)
        return pair

    def secondary_xaxis(
        self,
        location: str = "top",
        functions: tuple[
            Callable[[FloatArray], ArrayLike], Callable[[FloatArray], ArrayLike]
        ]
        | None = None,
        *,
        offset: float | None = None,
        **axis_config: object,
    ) -> Axis:
        """Add an x decoration whose ticks use converted units.

        Parameters
        ----------
        location
            Top or bottom border.
        functions
            Vectorised forward and inverse conversions, or None for identity.
            They must be finite, strictly monotonic and inverse on the base range.
        offset
            Nonnegative outward distance in scene units.
        **axis_config
            NumberLine options for this axis alone; numbers default to enabled.

        Returns
        -------
        Axis
            A styleable decoration following this system's x range and scale.

        Raises
        ------
        ValueError
            If location, offset or the conversions on the base range are invalid.
            Invalid conversions also refuse later ranges before they are applied.
        """
        return self.x._secondary(location, functions, offset, axis_config)

    def secondary_yaxis(
        self,
        location: str = "right",
        functions: tuple[
            Callable[[FloatArray], ArrayLike], Callable[[FloatArray], ArrayLike]
        ]
        | None = None,
        *,
        offset: float | None = None,
        **axis_config: object,
    ) -> Axis:
        """Add a y decoration whose ticks use converted units.

        Parameters
        ----------
        location
            Left or right border.
        functions
            Vectorised forward and inverse conversions, or None for identity.
            They must be finite, strictly monotonic and inverse on the base range.
        offset
            Nonnegative outward distance in scene units.
        **axis_config
            NumberLine options for this axis alone; numbers default to enabled.

        Returns
        -------
        Axis
            A styleable decoration following this system's y range and scale.

        Raises
        ------
        ValueError
            If location, offset or the conversions on the base range are invalid.
            Invalid conversions also refuse later ranges before they are applied.
        """
        return self.y._secondary(location, functions, offset, axis_config)

    def _twin(
        self,
        index: int,
        limits: Sequence[float] | None,
        scale: Scale | Literal["linear", "log", "symlog"],
        options: dict[str, Any] | None,
        offset: float | None,
    ) -> CartesianAxes:
        root = (
            self.parent
            if self._twin_axis is not None and self.parent is not None
            else self
        )
        root._sync_data()
        distance = 0.9 if offset is None else float(offset)
        if not np.isfinite(distance) or distance < 0:
            raise ValueError("offset must be finite and nonnegative")
        ranges: list[Sequence[float]] = [
            (*axis.range.value, axis._step) for axis in (root.x, root.y)
        ]
        if limits is not None:
            ranges[index] = tuple(limits)
        scales = [root.x._scale, root.y._scale]
        scales[index] = _scale(scale, "x_scale" if index == 0 else "y_scale")
        configs: list[dict[str, Any]] = [{}, {}]
        configs[index] = {
            "include_tip": False,
            "label_direction": [0, 1, 0] if index == 0 else [1, 0, 0],
            **(options or {}),
        }
        twin = CartesianAxes(
            ranges[0],
            ranges[1],
            root.x_length,
            root.y_length,
            x_axis_config=configs[0],
            y_axis_config=configs[1],
            x_scale=scales[0],
            y_scale=scales[1],
            # The root already supplies the box and grid for the shared frame.
            theme=replace(root.theme, box=False, grid=()),
            cycle=root._cycle,
        )
        twin.theme = root.theme
        own = twin.get_axis(index)
        own._label_direction_custom = "label_direction" in (options or {})
        if index == 1:
            twin.x = twin.x_axis = self.x
        else:
            twin.y = twin.y_axis = self.y
        twin.axes = VGroup(twin.x, twin.y)
        twin.submobjects = [own]
        previous = [t.get_axis(index) for t in root.twins if t._twin_axis == index]
        outward = previous[-1]._position_offset + distance if previous else 0.0
        twin._ranges = (twin.x, twin.y)
        root._attach_twin(twin, index)
        own.set_position("top" if index == 0 else "right", offset=outward)
        return twin

    def _attach_twin(self, twin: CartesianAxes, index: int) -> None:
        root = self
        twin.theme = root.theme
        twin.parent, twin._twin_axis = root, index
        twin._artists._clock = root._artists._clock
        twin.frame = twin._channel_frame = root.frame
        twin.bounds = root.bounds
        twin._compile()
        root._twins.append(twin)
        root.submobjects.insert(root.submobjects.index(root.frame), twin)

    def _systems(self) -> tuple[CartesianAxes, ...]:
        return (self, *self._twins)

    def _owned_axes(self) -> tuple[Axis, ...]:
        if self._twin_axis == -1:
            return ()
        return (
            self._ranges
            if self._twin_axis is None
            else (self.get_axis(self._twin_axis),)
        )

    def _channel_axes(self) -> tuple[Axis, ...]:
        root = (
            self.parent
            if self._twin_axis is not None and self.parent is not None
            else self
        )
        if not root._has_secondary_axes:
            if self._twin_axis == -1:
                return self.x, self.y
            if not self._twins:
                return self._owned_axes()
            return tuple(
                axis for system in self._systems() for axis in system._owned_axes()
            )
        if self._twin_axis == -1:
            return tuple(
                a for base in (self.x, self.y) for a in (base, *base._secondaries)
            )
        return tuple(
            decoration
            for system in self._systems()
            for axis in system._owned_axes()
            for decoration in (axis, *axis._secondaries)
        )

    def _refresh_mirrors(self) -> None:
        root = (
            self.parent
            if self._twin_axis is not None and self.parent is not None
            else self
        )
        if not root._has_mirrors:
            return
        axes = [a for s in root._systems() for a in s._owned_axes()]
        for base in axes:
            for mirror in base._mirrors:
                hidden = root._mirror_occupied(mirror)
                if hidden != mirror._mirror_suppressed:
                    mirror._mirror_suppressed = hidden
                    mirror._regenerate()

    def _mirror_occupied(self, mirror: Axis) -> bool:
        root = (
            self.parent
            if self._twin_axis is not None and self.parent is not None
            else self
        )
        if not root._twins and not root._has_secondary_axes:
            return False
        occupants = [a for s in root.twins for a in s._owned_axes()]
        occupants.extend(
            a
            for s in root._systems()
            for base in s._owned_axes()
            for a in base._secondaries
        )
        other = mirror._system.get_axis(1 - mirror.index)
        side = (("bottom", "top") if mirror.index == 0 else ("left", "right"))[
            int(mirror._cross_value() == other.range.value[1])
        ]
        return any(
            a.index == mirror.index
            and a._position == side
            and a._position_fraction is None
            and a._position_offset == 0
            for a in occupants
        )

    def family_members_with_points(self) -> list[Mobject]:
        """Return members with points, using the flat animation channel directly."""
        if self.parent is not None and self._twin_axis is not None:
            writer = writer_context()
            if writer is not None and self.frame not in writer.family:
                raise ValueError("move the twin's parent to change its geometry")
        if self._data_animation and all(isinstance(m, Leaf) for m in self.submobjects):
            if data_interpolation():
                # The frame publishes all derived geometry at the same alpha.
                return [self._channel_frame]
            self._sync_data()
            if self._channel_decorations:
                self._sync_channel_decorations()
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
        assert isinstance(target, CartesianAxes)
        if len(self.twins) != len(target.twins) or [
            s._twin_axis for s in self._systems()
        ] != [s._twin_axis for s in target._systems()]:
            raise ValueError("become requires corresponding twins")
        parent = self.parent
        shared = {}
        if (
            self._twin_axis is not None
            and parent is not None
            and target.parent is not None
        ):
            source_axes = target.parent._channel_axes()
            for index, axis in enumerate((target.x, target.y)):
                if axis not in target._owned_axes():
                    shared[index] = parent._channel_axes()[source_axes.index(axis)]
        pairs = dict(zip(target._systems(), self._systems(), strict=True))
        for new, old in pairs.items():
            artists = old._artists
            old.__dict__.update(new.__dict__)
            old._artists = artists
            old._data_version += 1
        for old in pairs.values():
            if old.parent is not None:
                old.parent = pairs.get(old.parent, old.parent)
            old._twins = [pairs[twin] for twin in old._twins]
            old.submobjects = [
                pairs.get(member, member)
                if isinstance(member, CartesianAxes)
                else member
                for member in old.submobjects
            ]
        for member in self.get_family():
            if (
                isinstance(member, (Axis, Leaf, BoundLabel))
                and member._system is not None
            ):
                member._system = pairs.get(member._system, member._system)
        if parent is not None and self._twin_axis is not None:
            self.parent, self.frame = parent, parent.frame
            self._channel_frame = self.frame
            if 0 in shared:
                self.x = self.x_axis = shared[0]
            if 1 in shared:
                self.y = self.y_axis = shared[1]
            self._ranges = (self.x, self.y)
            self.axes = VGroup(self.x, self.y)
            self._compile()
            for axis in self._owned_axes():
                axis._configure()
        for system in self._systems():
            for artist in system._artists:
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
        if len(self.twins) != len(mobject.twins):
            raise ValueError("Transform requires the same number of twins")
        axes, targets = self._channel_axes(), mobject._channel_axes()
        if [t._twin_axis for t in self.twins] != [t._twin_axis for t in mobject.twins]:
            raise ValueError("Transform requires twins sharing the same dimensions")
        for axis, target in zip(axes, targets, strict=True):
            if type(axis._scale) is not type(target._scale):
                raise ValueError("a change of scale type requires FadeTransform")
        count = max(1, int(np.ceil(animation.run_time * config.frame_rate * 4)))
        alphas = np.array(
            [animation.rate_func(t) for t in np.linspace(0, 1, count + 1)]
        )
        pools = [
            _TickPool(axis, target, alphas)
            for axis, target in zip(axes, targets, strict=True)
        ]
        changed = any(
            not np.array_equal(axis.range.value, target.range.value) or not pool.same
            for axis, target, pool in zip(axes, targets, pools, strict=True)
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
            system._channel_frame = system.frame
            if system.parent is not None and system._twin_axis is not None:
                system._channel_frame = FrameLeaf(
                    system.bounds.lower, system.bounds.upper, system
                )
                system._channel_frame.points = system.frame._cache.copy()
            system._pool_warned = False
            system._pool_alpha = alpha
            system._syncing = True
            try:
                for axis, pool in zip(
                    system._channel_axes(),
                    target_pools if system is mobject else pools,
                    strict=True,
                ):
                    pool.alpha = alpha
                    axis._prepare_pool(pool)
                for axis in system._channel_axes():
                    axis._configure()
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
        self.submobjects = [*families[0], self._channel_frame]
        mobject.submobjects = [*families[1], mobject._channel_frame]
        for system in (self, mobject):
            root = (
                system.parent
                if system._twin_axis is not None and system.parent is not None
                else system
            )
            if not root._has_mirrors and not root._has_secondary_axes:
                continue
            system._channel_decorations = tuple(
                dict.fromkeys(
                    member
                    for axis in system._channel_axes()
                    for member in axis.get_family()
                    if isinstance(member, Axis)
                    and (
                        member._mirror_of is not None
                        or member._secondary_of is not None
                    )
                )
            )
            system._sync_channel_decorations()
        return self

    def _sync_channel_decorations(self) -> None:
        if not self._channel_decorations:
            return
        versions = tuple(axis._parts_version for axis in self._channel_decorations)
        if versions == self._channel_decoration_versions:
            return
        current = tuple(
            dict.fromkeys(
                leaf
                for axis in self._channel_decorations
                for leaf in axis.get_family()
                if isinstance(leaf, Leaf)
            )
        )
        previous = self._channel_decoration_leaves
        self._channel_decoration_versions = versions
        self._channel_decoration_leaves = current
        if not previous or current == previous:
            return
        old, new = set(previous), set(current)
        for leaf in old - new:
            # The renderer can still hold a reference captured at animation start.
            leaf._cache = np.empty((0, 3))
        members: list[VMobject] = []
        inserted = False
        for member in self.submobjects:
            if member in old:
                if not inserted:
                    members.extend(current)
                    inserted = True
            elif member not in new:
                members.append(member)
        if not inserted:
            members[-1:-1] = current
        self.submobjects = members

    def _channel_roles(self) -> dict[object, Leaf]:
        roles: dict[object, Leaf] = {}
        for axis_id, axis in enumerate(self._channel_axes()):
            for name in ("line", "tip", "tip_start"):
                leaf = getattr(axis, name)
                if leaf is not None:
                    roles[(axis_id, name)] = leaf
            for name, leaves in (
                ("major", axis._tick_leaves),
                ("minor", axis._minor_leaves),
            ):
                if axis.include_ticks:
                    for key, leaf in leaves.items():
                        roles[(axis_id, name, key)] = leaf
            for key, grid in axis._grid_leaves.items():
                roles[(axis_id, "grid", key)] = grid
            for key, label in axis._number_leaves.items():
                for i, leaf in enumerate(label.get_family()):
                    if isinstance(leaf, Leaf):
                        roles[(axis_id, "number", key, i)] = leaf
            if axis._pool is not None:
                for level, spares in axis._pool.spares.items():
                    for i, leaf in enumerate(spares):
                        roles[(axis_id, "spare", level, i)] = leaf
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
        for system, system_start, system_target in zip(
            self._systems(), start._systems(), target._systems(), strict=True
        ):
            system._field_steps = tuple(
                (1 - alpha) * x + alpha * y
                for x, y in zip(
                    system_start._field_steps, system_target._field_steps, strict=True
                )
            )
        self._syncing = True
        try:
            for axis, a, b in zip(
                self._channel_axes(),
                start._channel_axes(),
                target._channel_axes(),
                strict=True,
            ):
                assert axis._pool is not None
                limits = (
                    a.range.value
                    if axis._pool.fixed_range
                    else (1 - alpha) * a.range.value + alpha * b.range.value
                )
                if not isinstance(axis._scale, LinearScale):
                    limits = np.array(
                        axis._scale.limit_range(
                            float(limits[0]), float(limits[1]), MINPOS_UNKNOWN
                        )
                    )
                if not np.array_equal(limits, axis._range_parameter.value):
                    if axis._secondaries:
                        axis._validate_range(limits)
                    limits.flags.writeable = False
                    axis._range_parameter._value = limits
                    axis._range_parameter._version += 1
                axis._pool.alpha = alpha
            for system in self._systems():
                if (
                    system._twin_axis != -1
                    or system._range_versions
                    != tuple(axis.range.version for axis in system._ranges)
                    or (
                        system.parent is not None
                        and system.bounds is not system.parent.bounds
                    )
                ):
                    system._compile()
            for axis in self._channel_axes():
                if self.parent is not None and axis._system is not self:
                    axis._system._sync_data()
                axis._configure(only_crossing=axis._decoration_seen == axis._versions())
            for system in self._systems():
                system._configure_grid()
            if self._channel_decorations:
                self._sync_channel_decorations()
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
            self._channel_decorations = ()
            self._channel_decoration_versions = ()
            self._channel_decoration_leaves = ()
            self.submobjects = self._channel_roots
            del self._channel_roots
            self._channel_frame = self.frame
            for axis in self._channel_axes():
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
                for axis in self._channel_axes():
                    axis._configure()
                for system in self._systems():
                    system._configure_grid()
            finally:
                self._syncing = False
        if (
            animation is not None
            and getattr(animation, "replace_mobject_with_target_in_scene", False)
            and isinstance(
                target := getattr(animation, "target_mobject", None), CartesianAxes
            )
        ):
            pairs = dict(zip(self._systems(), target._systems(), strict=True))
            registered = sorted(
                (order, system, ref)
                for system in pairs
                for order, ref in system._artists._refs
            )
            for _, system, ref in registered:
                artist = ref()
                if artist is None:
                    continue
                paired = pairs[system]
                for leaf in artist.get_family():
                    if isinstance(leaf, Leaf):
                        leaf._event(lc.Rebind(paired))
                if isinstance(artist, (ScatterPlot, ErrorBars)):
                    system._artists.remove(artist)
                    paired._artists.append(artist)
                    artist._system = paired
                    if isinstance(artist, ErrorBars) and artist.markers is not None:
                        artist.markers._system = paired
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
        if self.parent is not None and self._twin_axis is not None:
            self.parent._sync_data()
            self.bounds = self.parent.bounds
            self.x_length, self.y_length = self.parent.x_length, self.parent.y_length
            for axis in self._owned_axes():
                axis._resize(self.x_length if axis.index == 0 else self.y_length)
        axes = self._ranges
        dim = len(axes)
        scaled = [axis._scale.forward(axis.range.value) for axis in axes]
        if self.aspect is not None:
            self._enforce_aspect(scaled)
        lower = np.array([limits[0] for limits in scaled])
        span = np.array([limits[1] - limits[0] for limits in scaled])
        factors = np.divide(
            [getattr(self, name + "_length") for name in "xyz"[:dim]],
            span,
            out=np.zeros(dim),
            where=span != 0,
        )
        self._data = Chain(
            (
                *(
                    ScaleNode(axis._scale, index, dim)
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
        self._range_versions = tuple(axis._range_parameter.version for axis in axes)

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
        if self._syncing:
            return False
        if (
            self.parent is not None
            and self._twin_axis is not None
            and self.bounds is not self.parent.bounds
        ):
            return True
        for index, axis in enumerate(self._ranges):
            if self._range_versions[index] != axis._range_parameter.version or (
                self._twin_axis in (None, index) and axis._style_changed()
            ):
                return True
        return False

    def _sync_data(self) -> None:
        if not self._data_dirty():
            return
        axes = self._owned_axes()
        range_changed = (
            self.parent is not None
            and self._twin_axis is not None
            and self.bounds is not self.parent.bounds
        ) or self._range_versions != tuple(
            axis._range_parameter.version for axis in self._ranges
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
        token = playback_context()
        if token is not None and token == self._poll_token:
            return
        parameters = tuple(p for axis in self._ranges for p in axis._parameters())
        self._poll_token = token
        self._token += 1
        for parameter in parameters:
            parameter.poll(self._token)
        for artist in self._artists:
            artist._poll()
        self._sync_data()
        for twin in self.twins:
            twin._poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        if self._moving_query is None or self._moving_query[0] is not moving:
            self._moving_query = (moving, self._sync_needed(moving))
        return self._moving_query[1]

    def _sync_needed(self, moving: frozenset[Mobject]) -> bool:
        if not hasattr(self, "frame"):
            return False
        if self.frame in moving:
            return True
        for axis in self._ranges:
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

    def _axis_cross_value(self, index: int) -> float:
        axis = self.get_axis(index)
        crossing = axis._cross_value()
        if axis._system is self and axis._position_offset == 0:
            return crossing
        self._sync_data()
        axis._system._sync_data()
        coords = np.full((1, 2), crossing)
        coords[0, index] = axis.range.value[0]
        local = axis._system._data.forward(coords)
        local[0, 1 - index] += axis._outward_offset()[1 - index]
        return float(self._data.inverse(local)[0, 1 - index])

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
        coords = (
            tuple(
                cast(ArrayLike, resolve_categories(axis, value))
                for axis, value in zip(self._ranges, coords, strict=False)
            )
            if any(np.asarray(value).dtype.kind in ("U", "S", "O") for value in coords)
            else coords
        )
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
        dim = len(self._ranges)
        if data.shape[1] < dim:
            padded = np.zeros((len(data), dim))
            padded[:, : data.shape[1]] = data
            data = padded
        else:
            data = data[:, :dim]
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
        result = self._data.inverse(local[:, : len(self._ranges)])
        if not np.isfinite(result).all():
            raise ValueError("point maps to non-finite coordinates")
        return result[0] if values.ndim == 1 else result

    point_to_coords = p2c

    def _polar_data(self, radius: ArrayLike, azimuth: ArrayLike) -> FloatArray:
        r, theta = np.broadcast_arrays(
            np.asarray(radius, dtype=float), np.asarray(azimuth, dtype=float)
        )
        return np.array([r * np.cos(theta), r * np.sin(theta)])

    def polar_to_point(self, radius: ArrayLike, azimuth: ArrayLike) -> FloatArray:
        """Convert polar coordinates through this system's data map.

        Parameters
        ----------
        radius, azimuth
            Broadcastable radii and radian angles.

        Returns
        -------
        FloatArray
            Scene points, in the same convention as c2p.
        """
        return self.c2p(*self._polar_data(radius, azimuth))

    def point_to_polar(self, point: ArrayLike) -> tuple[float, float]:
        """Recover a radius and signed azimuth from a scene point.

        Parameters
        ----------
        point
            One scene point.

        Returns
        -------
        tuple of float
            Radius and angle in ``(-pi, pi]`` for Cartesian systems.
        """
        x, y = self.p2c(point)
        theta = float(np.arctan2(y, x))
        return float(np.hypot(x, y)), np.pi if theta == -np.pi else theta

    def pr2pt(self, radius: ArrayLike, azimuth: ArrayLike) -> FloatArray:
        """Convert polar coordinates to scene points.

        Parameters
        ----------
        radius, azimuth
            Broadcastable radii and radian angles.

        Returns
        -------
        FloatArray
            Result of polar_to_point.
        """
        return self.polar_to_point(radius, azimuth)

    def pt2pr(self, point: ArrayLike) -> tuple[float, float]:
        """Convert a scene point to polar coordinates.

        Parameters
        ----------
        point
            One scene point.

        Returns
        -------
        tuple of float
            Result of point_to_polar.
        """
        return self.point_to_polar(point)

    def plot_polar_graph(
        self,
        r_func: Callable[..., Any],
        theta_range: Sequence[float] | None = None,
        **kwargs: object,
    ) -> ParametricPlot:
        """Draw a bound polar graph with angle as its parameter.

        Parameters
        ----------
        r_func
            Radius as a function of a radian angle and optional parameters.
        theta_range
            Endpoints and optional maximum spacing; defaults to a full turn.
        **kwargs
            Function parameters and ordinary plot keywords.

        Returns
        -------
        ParametricPlot
            Registered curve carrying r_func as underlying_function.
        """
        from manim_plots.mobjects.polar import _PolarPlot

        artist = _PolarPlot(r_func, self, theta_range, **kwargs)
        self.add(artist)
        return artist

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
        if len(x_range) == 3:
            self._field_steps = (float(x_range[2]), *self._field_steps[1:])
        return self

    def set_y_range(self, y_range: Sequence[float]) -> Self:
        """Set y endpoints, retaining the existing locator.

        Parameters
        ----------
        y_range
            New endpoints and an optional ignored locator step.
        """
        self.y_axis.range = _range(y_range, "y_range")
        if len(y_range) == 3:
            self._field_steps = (
                self._field_steps[0],
                float(y_range[2]),
                *self._field_steps[2:],
            )
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
        return self._ranges[index]

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
        edge: ArrayLike | None,
        direction: ArrayLike | None,
        buff: float,
    ) -> BoundLabel:
        axis = self.get_axis(index)
        outward = axis._outward_offset()
        if axis._position_outward:
            outward[1 - index] = -1 if axis._position in ("left", "bottom") else 1
        else:
            outward[1 - index] = 1
        if edge is None:
            edge = np.eye(3)[index] + outward
        if direction is None:
            direction = (0.5 if index == 1 else 1) * np.eye(3)[index] + outward
        result = _label(label)
        decoration: VMobject = axis
        if self.theme.box or self.theme.grid:
            # A theme's frame and grid must not move titles off the primary axis.
            decoration = VGroup(
                *(
                    m
                    for m in axis.submobjects
                    if m not in axis._mirrors and m is not axis.grid
                )
            )
        result.next_to(
            decoration.get_edge_center(np.asarray(edge, dtype=float)),
            direction=np.asarray(direction, dtype=float),
            buff=buff,
        )
        if not axis._position_outward:
            result.shift_onto_screen(buff=0.25)
        return BoundLabel(result, self)

    def get_x_axis_label(
        self,
        label: object,
        edge: ArrayLike | None = None,
        direction: ArrayLike | None = None,
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
        edge: ArrayLike | None = None,
        direction: ArrayLike | None = None,
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
        for axis in self._owned_axes():
            axis._configure_grid()
            if axis._mirrors or axis._secondaries:
                for decoration in (*axis._mirrors, *axis._secondaries):
                    decoration._configure_grid()

    def get_vector_field(
        self, func: Callable[..., Any], **kwargs: object
    ) -> ArrowVectorField:
        """Create a bound arrow field in data coordinates.

        Parameters
        ----------
        func
            Function of one point ``[x, y, 0]`` returning a vector.
        **kwargs
            ArrowVectorField options, styles and function parameter bindings.

        Returns
        -------
        ArrowVectorField
            Independently styleable arrows following this system.
        """
        return ArrowVectorField(func, self, **cast(dict[str, Any], kwargs))

    def get_stream_lines(
        self, func: Callable[..., Any], **kwargs: object
    ) -> StreamLines:
        """Create bound RK4 trajectories in data coordinates.

        Parameters
        ----------
        func
            Function of one point ``[x, y, 0]`` returning a vector.
        **kwargs
            StreamLines options, styles and function parameter bindings.

        Returns
        -------
        StreamLines
            Clipped trajectories following this system.
        """
        return StreamLines(func, self, **cast(dict[str, Any], kwargs))

    def get_vector(self, coords: Sequence[object], **kwargs: object) -> HelperGroup:
        """Draw a bound arrow from the data origin to coordinates.

        Parameters
        ----------
        coords
            Two data coordinates, each accepting a tracker or callable binding.
        **kwargs
            Native Arrow style and tip options.

        Returns
        -------
        HelperGroup
            Independently styleable ``line`` and ``tip`` parts.
        """
        return _get_vector(self, coords, **kwargs)

    def plot_implicit_curve(
        self,
        func: Callable[..., Any],
        min_depth: int = 5,
        max_quads: int = 1500,
        **kwargs: object,
    ) -> _CurvePlot:
        """Plot a bound zero contour by refined marching squares.

        Parameters
        ----------
        func
            Scalar function of x and y, followed by optional bound parameters.
        min_depth
            Number of subdivisions of cells containing a sign change.
        max_quads
            Approximate initial grid cell budget.
        **kwargs
            Artist style, clipping, and function parameter values or bindings.

        Returns
        -------
        VMobject
            One registered path artist following the system and parameters.
        """
        return _implicit_curve(self, func, min_depth, max_quads, **kwargs)

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
        default. ``clip`` accepts True, False, a finite numeric margin in scene
        units, or a two-entry tuple or list ``(cx, cy)`` for independent x and y
        policies. True clips at the viewport, False disables clipping, and
        positive margins expand the interval while negative margins narrow it.
        A single value applies to both axes. Uncoloured plots advance a cycle
        whose first colour is white; an explicit colour does not advance it.
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

    def plot_slice(
        self,
        surface: object,
        *,
        x: object = None,
        y: object = None,
        plane: object = None,
        **style: object,
    ) -> FunctionPlot:
        """Draw a bound height-surface profile on this two-dimensional system.

        Parameters
        ----------
        surface, x, y, plane, **style
            A plot_surface artist, exactly one bound coordinate and curve options.

        Returns
        -------
        FunctionPlot
            The profile over the surface's other parameter range.
        """
        from manim_plots.mobjects.surfaces import (
            SurfacePlot,
            _plane_profile,
            _slice_input,
            _SliceProfile,
        )

        if len(self._ranges) == 3:
            raise NotImplementedError("plot_slice is unavailable on ThreeDAxes")
        axis, value = _slice_input("plot_slice", (x, y, plane))
        if not isinstance(surface, SurfacePlot) or surface._kind != "height":
            raise TypeError("plot_slice requires a surface from plot_surface")
        artist = (
            _plane_profile(self, surface, value, **style)
            if axis == 2
            else _SliceProfile(self, surface, axis, value, **style)
        )
        self.add(artist)
        return artist

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
            Native VMobject styles and artist options, including ``clip`` as in
            ``plot``.
        """
        artist = LinePlot(xs, self, ys, **kwargs)
        self.add(artist)
        return artist

    def boxplot(
        self, x: object, positions: object = None, **kwargs: object
    ) -> mp.BoxPlot:
        """Create bound boxes from samples.

        Parameters
        ----------
        x, positions, **kwargs
            Samples, positions and statistics or styling options.
        """
        return mp.BoxPlot(self, x, positions, **cast(Any, kwargs))

    def violinplot(
        self, dataset: object, positions: object = None, **kwargs: object
    ) -> mp.ViolinPlot:
        """Create bound Gaussian density violins.

        Parameters
        ----------
        dataset, positions, **kwargs
            Samples, positions and density or styling options.
        """
        return mp.ViolinPlot(self, dataset, positions, **cast(Any, kwargs))

    def hist(self, x: object, bins: object = 10, **kwargs: object) -> mp.HistPlot:
        """Create a histogram from samples.

        Parameters
        ----------
        x, bins, **kwargs
            Samples, NumPy bins and histogram counting, geometry and style options.
        """
        return mp.HistPlot(self, x, bins, **cast(Any, kwargs))

    def step(
        self, x: object, y: object, *, where: str = "pre", **kwargs: object
    ) -> LinePlot:
        """Create a line stepping before, after or between samples.

        Parameters
        ----------
        x, y, where, **kwargs
            Coordinates, step placement and line options.
        """
        from manim_plots.mobjects.histograms import _step_vertices

        return self.line(_step_vertices(x, y, where), **cast(Any, kwargs))

    def stairs(
        self,
        values: object,
        edges: object = None,
        *,
        baseline: object = 0,
        fill: bool = False,
        orientation: str = "vertical",
        **style: object,
    ) -> LinePlot:
        """Create steps across explicit bin edges.

        Parameters
        ----------
        values, edges, baseline, fill, orientation, **style
            Bin heights, edges, baseline, fill, direction and line styles.
        """
        from manim_plots.mobjects.histograms import _stairs_vertices

        if fill:
            style = {"fill_opacity": 1, "stroke_width": 0, **style}
        return self.line(
            _stairs_vertices(values, edges, baseline, orientation, fill),
            **cast(Any, style),
        )

    def stackplot(
        self,
        x: object,
        *ys: object,
        labels: Sequence[str] = (),
        colors: object = None,
        baseline: str = "zero",
        **style: object,
    ) -> mp.StackPlot:
        """Fill cumulative series.

        Parameters
        ----------
        x, ys, labels, colors, baseline, **style
            Coordinates, series, labels, colours, baseline and fill styles.
        """
        return mp.StackPlot(
            self,
            x,
            ys,
            labels=labels,
            colors=colors,
            baseline=baseline,
            **cast(Any, style),
        )

    def bar(
        self,
        x: object,
        height: object,
        width: object = 0.8,
        bottom: object = 0,
        *,
        align: str = "center",
        color: object = None,
        c: object = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        label: str | None = None,
        **style: object,
    ) -> mp.BarPlot:
        """Create vertical bars.

        Parameters
        ----------
        x, height, width, bottom, align
            Positions, sizes, bases and alignment.
        color, c, colorscale, vmin, vmax, norm, label, **style
            Colours, value mapping, legend text and native styles.
        """
        return mp.BarPlot(
            self,
            x,
            height,
            width,
            bottom,
            align=align,
            color=color,
            c=c,
            colorscale=colorscale,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            label=label,
            **cast(Any, style),
        )

    def barh(
        self,
        y: object,
        width: object,
        height: object = 0.8,
        left: object = 0,
        *,
        align: str = "center",
        **style: object,
    ) -> mp.BarPlot:
        """Create horizontal bars.

        Parameters
        ----------
        y, width, height, left, align, **style
            Positions, lengths, thicknesses, bases, alignment and bar style.
        """
        return mp.BarPlot(
            self,
            y,
            width,
            height,
            left,
            align=align,
            horizontal=True,
            **cast(Any, style),
        )

    def grouped_bar(
        self,
        heights: object,
        positions: object = None,
        *,
        tick_labels: Sequence[str] | None = None,
        labels: Sequence[str] | None = None,
        group_spacing: float = 1.5,
        bar_spacing: float = 0,
        orientation: str = "vertical",
        colors: object = None,
        **style: object,
    ) -> mp.GroupedBarPlot:
        """Create evenly spaced datasets within each group.

        Parameters
        ----------
        heights, positions, tick_labels, labels
            Datasets, group coordinates, category names and legend labels.
        group_spacing, bar_spacing, orientation, colors, **style
            Relative gaps, direction, dataset colours and native style.
        """
        from manim_plots.mobjects.bars import _grouped_bar

        return _grouped_bar(
            self,
            heights,
            positions,
            tick_labels=tick_labels,
            labels=labels,
            group_spacing=group_spacing,
            bar_spacing=bar_spacing,
            orientation=orientation,
            colors=colors,
            **style,
        )

    def bar_label(
        self,
        container: mp.BarPlot,
        labels: Sequence[str] | None = None,
        *,
        fmt: str = "{:g}",
        label_type: str = "edge",
        padding: float = 0.1,
        **text_style: object,
    ) -> VGroup:
        """Create bound bar value labels.

        Parameters
        ----------
        container, labels, fmt, label_type, padding, **text_style
            Bars, optional text, format, placement, scene gap and Text styles.
        """
        from manim_plots.mobjects.bars import bar_label

        return bar_label(
            container,
            labels,
            fmt=fmt,
            label_type=label_type,
            padding=padding,
            **text_style,
        )

    def scatter(
        self,
        xs: ArrayLike,
        ys: ArrayLike | None = None,
        *,
        marker: Mobject | Marker | None = None,
        label: str | None = None,
        clip: _ClipInput = True,
        c: object = None,
        s: ArrayLike | None = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        **kwargs: Unpack[_VMStyle],
    ) -> ScatterPlot:
        """Create and register independent markers in input order.

        Parameters
        ----------
        c, s
            Per-point values or a single colour, and scene-unit marker radii.
        colorscale, vmin, vmax, norm
            Value colour mapping and normalisation.
        xs, ys
            Separate coordinates, or pairs in xs with ys omitted.
        marker
            Marker enum or native template, defaulting to Dot().
        label
            Legend entry text, or None to omit this artist.
        clip
            True clips marker centres at the viewport, False disables clipping,
            and a finite margin in scene units expands (positive) or narrows
            (negative) the interval. A single value applies to both axes; a
            two-entry tuple or list ``(cx, cy)`` sets each axis independently.
        **kwargs
            Native VMobject styles for the markers.
        """
        if ys is not None:
            xs, ys = (
                cast(ArrayLike, resolve_categories(self.x, xs)),
                cast(ArrayLike, resolve_categories(self.y, ys)),
            )
        artist = ScatterPlot(
            xs,
            self,
            ys,
            marker=marker,
            label=label,
            clip=clip,
            c=c,
            s=s,
            colorscale=colorscale,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            **kwargs,
        )
        self.add(artist)
        return artist

    def errorbar(
        self,
        x: ArrayLike,
        y: ArrayLike | None = None,
        yerr: ArrayLike | None = None,
        xerr: ArrayLike | None = None,
        *,
        marker: Mobject | Marker | None = Marker.DOT,
        line: bool = False,
        ecolor: ParsableManimColor | None = None,
        elinewidth: float | None = None,
        capsize: float = 0.1,
        capthick: float | None = None,
        barsabove: bool = False,
        errorevery: int | tuple[int, int] = 1,
        label: str | None = None,
        clip: _ClipInput = True,
        **style: Unpack[_VMStyle],
    ) -> ErrorBars:
        """Create and register error bars in x and y.

        Parameters
        ----------
        x, y
            Separate coordinate arrays, or pairs in x with y omitted.
        yerr, xerr
            Nonnegative scalar, n errors, or (2, n) lower and upper errors.
        marker
            Marker enum or native template; None omits markers.
        line
            Include a connecting line when true.
        ecolor, elinewidth, capthick
            Error colour, bar width (default 2), and cap width (default bar width).
        capsize
            Full cap length in scene units; zero omits caps.
        barsabove
            Draw bars after markers when true.
        errorevery
            Draw every kth error, or (start, k).
        label
            One legend entry for the entire artist.
        clip
            Boolean, scene-unit margin, or independent (x, y) policies.
        **style
            Native styles for markers and connecting line.

        Returns
        -------
        ErrorBars
            Registered artist with independently styleable named parts.
        """
        artist = ErrorBars(
            x,
            self,
            y,
            yerr,
            xerr,
            marker=marker,
            line=line,
            ecolor=ecolor,
            elinewidth=elinewidth,
            capsize=capsize,
            capthick=capthick,
            barsabove=barsabove,
            errorevery=errorevery,
            label=label,
            clip=clip,
            **style,
        )
        self.add(artist)
        return artist

    def imshow(
        self,
        Z: ArrayLike,
        *,
        extent: Sequence[float] | None = None,
        origin: str = "upper",
        colorscale: object = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        **style: object,
    ) -> mp.HeatmapPlot:
        """Draw an image as bound data cells.

        Parameters
        ----------
        Z, extent, origin, colorscale, vmin, vmax, norm, **style
            Values, data rectangle, row direction, colour mapping and cell style.
        """
        from manim_plots.mobjects.heatmaps import _imshow

        return _imshow(
            self,
            Z,
            extent=extent,
            origin=origin,
            colorscale=colorscale,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            **cast(dict[str, Any], style),
        )

    def pcolormesh(
        self,
        X: ArrayLike,
        Y: ArrayLike | None = None,
        C: ArrayLike | None = None,
        *,
        shading: str = "auto",
        colorscale: object = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        **style: object,
    ) -> mp.HeatmapPlot:
        """Draw scalar cells from corner grids or nearest centres.

        Parameters
        ----------
        X, Y, C, shading, colorscale, vmin, vmax, norm, **style
            Coordinates, values, grid interpretation, colour mapping and cell style.
        """
        from manim_plots.mobjects.heatmaps import _pcolormesh

        return _pcolormesh(
            self,
            X,
            Y,
            C,
            shading=shading,
            colorscale=colorscale,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            **cast(dict[str, Any], style),
        )

    def hist2d(
        self,
        x: ArrayLike,
        y: ArrayLike,
        bins: int | Sequence[ArrayLike] = 10,
        *,
        range: Sequence[Sequence[float]] | None = None,
        density: bool = False,
        weights: ArrayLike | None = None,
        cmin: float | None = None,
        cmax: float | None = None,
        colorscale: object = "viridis",
        **style: object,
    ) -> mp.HeatmapPlot:
        """Draw NumPy's two-dimensional histogram as scalar cells.

        Parameters
        ----------
        x, y, bins, range, density, weights, cmin, cmax, colorscale, **style
            Samples, histogram arguments, count limits, colormap and cell style.
        """
        from manim_plots.mobjects.heatmaps import _hist2d

        return _hist2d(
            self,
            x,
            y,
            bins,
            range=range,
            density=density,
            weights=weights,
            cmin=cmin,
            cmax=cmax,
            colorscale=colorscale,
            **cast(dict[str, Any], style),
        )

    def hexbin(
        self,
        x: ArrayLike,
        y: ArrayLike,
        C: ArrayLike | None = None,
        *,
        gridsize: int = 10,
        reduce_C_function: Callable[[FloatArray], float] = np.mean,
        mincnt: int | None = None,
        extent: Sequence[float] | None = None,
        colorscale: object = "viridis",
        **style: object,
    ) -> mp.HexbinPlot:
        """Bin samples into two interleaved hexagonal lattices.

        Parameters
        ----------
        x, y, C, gridsize, reduce_C_function, mincnt, extent, colorscale, **style
            Samples, lattice size, aggregation, limits, colormap and cell style.
        """
        from manim_plots.mobjects.heatmaps import HexbinPlot

        return HexbinPlot(
            self,
            x,
            y,
            C,
            gridsize=gridsize,
            reduce_C_function=reduce_C_function,
            mincnt=mincnt,
            extent=extent,
            colorscale=colorscale,
            **cast(dict[str, Any], style),
        )

    def contour(
        self,
        X: ArrayLike,
        Y: ArrayLike,
        Z: ArrayLike,
        levels: Sequence[float] | int | None = None,
        *,
        colorscale: object = None,
        **style: object,
    ) -> mp.ContourSetPlot:
        """Draw marching-squares level lines of a scalar grid.

        Parameters
        ----------
        X, Y, Z, levels, colorscale, **style
            Grid coordinates and values, levels, optional colormap and line style.
        """
        from manim_plots.mobjects.heatmaps import ContourSetPlot

        return ContourSetPlot(
            self, X, Y, Z, levels, colorscale=colorscale, **cast(dict[str, Any], style)
        )

    def contourf(
        self,
        X: ArrayLike,
        Y: ArrayLike,
        Z: ArrayLike,
        levels: Sequence[float] | int | None = None,
        *,
        colorscale: object = "viridis",
        **style: object,
    ) -> mp.ContourSetPlot:
        """Draw filled marching-squares bands of a scalar grid.

        Parameters
        ----------
        X, Y, Z, levels, colorscale, **style
            Grid coordinates and values, band edges, colormap and fill style.
        """
        from manim_plots.mobjects.heatmaps import ContourSetPlot

        return ContourSetPlot(
            self, X, Y, Z, levels, filled=True, colorscale=colorscale, **style
        )

    def colorbar(
        self,
        mappable: object = None,
        *,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        label: object = None,
        length: float | None = None,
        width: float = 0.25,
        buff: float = MED_SMALL_BUFF,
        **kwargs: object,
    ) -> mp.Colorbar:
        """Build a numbered colour strip beside this system.

        Parameters
        ----------
        mappable, colorscale, vmin, vmax, norm, label, length, width, buff, **kwargs
            Artist or explicit mapping, label, size and decoration options.

        Returns
        -------
        Colorbar
            The bound colour strip and value axis.
        """
        from manim_plots.mobjects.colorbar import Colorbar

        return Colorbar(
            self,
            mappable,
            colorscale=colorscale,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            label=label,
            length=length,
            width=width,
            buff=buff,
            **kwargs,
        )

    def plot_surface(
        self,
        function: Callable[..., Any],
        u_range: Sequence[float] | None = None,
        v_range: Sequence[float] | None = None,
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        resolution: int | tuple[int, int] = 32,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.SurfacePlot:
        """Draw a bound height surface.

        Parameters
        ----------
        function, u_range, v_range, colorscale, colorscale_axis
            Surface data, parameter ranges, colours and rendering options.
        resolution, vmin, vmax, norm, clip, **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("plot_surface needs ThreeDAxes")

    def plot_parametric_surface(
        self,
        function: Callable[..., Any],
        u_range: Sequence[float] | None,
        v_range: Sequence[float] | None,
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        resolution: int | tuple[int, int] = 32,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.SurfacePlot:
        """Draw a parametric surface in data coordinates.

        Parameters
        ----------
        function, u_range, v_range, colorscale, colorscale_axis
            Surface data, parameter ranges, colours and rendering options.
        resolution, vmin, vmax, norm, clip, **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("plot_parametric_surface needs ThreeDAxes")

    def plot_surface_of_revolution(
        self,
        function: Callable[..., Any],
        t_range: Sequence[float] | None = None,
        axis: str = "z",
        angle_range: Sequence[float] = (0, 2 * np.pi),
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        resolution: int | tuple[int, int] = 32,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.SurfacePlot:
        """Revolve a radius function about a data axis.

        Parameters
        ----------
        function, t_range, axis, angle_range, colorscale, colorscale_axis
            Surface data, parameter ranges, colours and rendering options.
        resolution, vmin, vmax, norm, clip, **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("plot_surface_of_revolution needs ThreeDAxes")

    def surface(
        self,
        X: ArrayLike,
        Y: ArrayLike,
        Z: ArrayLike,
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.SurfacePlot:
        """Draw quadrilateral cells from three matching coordinate grids.

        Parameters
        ----------
        X, Y, Z, colorscale, colorscale_axis, vmin, vmax, norm, clip
            Surface data, parameter ranges, colours and rendering options.
        **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("surface needs ThreeDAxes")

    def plot_trisurf(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        triangles: ArrayLike | None = None,
        colorscale: object = None,
        colorscale_axis: int | str | Callable[..., Any] = 2,
        *,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.SurfacePlot:
        """Draw explicit triangles or a Delaunay triangulation of scattered points.

        Parameters
        ----------
        x, y, z, triangles, colorscale, colorscale_axis, vmin, vmax, norm
            Surface data, parameter ranges, colours and rendering options.
        clip, **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("plot_trisurf needs ThreeDAxes")

    def plot_wireframe(
        self,
        function: Callable[..., Any],
        u_range: Sequence[float] | None = None,
        v_range: Sequence[float] | None = None,
        *,
        resolution: int | tuple[int, int] = 10,
        clip: _ClipInput = True,
        **kwargs: object,
    ) -> mp.WireframePlot:
        """Draw a grid of adaptive three-dimensional surface curves.

        Parameters
        ----------
        function, u_range, v_range, resolution, clip, **kwargs
            Surface data, parameter ranges, colours and rendering options.
        """
        raise NotImplementedError("plot_wireframe needs ThreeDAxes")

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
            t_range (default (0, 1)), sampling options, native styles and artist
            options, including ``clip`` as in ``plot``.
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
            Native styles and artist options for the line. ``clip`` also applies
            to the vertex dots and accepts the same scalar or ``(cx, cy)`` tuple
            or list as ``plot``.
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

    def get_line_from_axis_to_point(
        self,
        index: int,
        point: object,
        line_func: type[Line] = DashedLine,
        line_config: dict[str, Any] | None = None,
        color: ParsableManimColor | None = None,
        stroke_width: float = 2,
    ) -> HelperLine:
        """Draw a bound drop line from the axis where it is displayed.

        Parameters
        ----------
        index, point, line_func, line_config, color, stroke_width
            Manim's arguments; point also accepts a Mobject or scene-point callable.

        Returns
        -------
        HelperLine
            Registered plotting leaf, unlike Manim's Line or DashedLine. Static
            scene points are held in data coordinates; the helper follows edits.
        """
        return _drop(
            self,
            index,
            point,
            line_func=line_func,
            line_config=line_config,
            color=color,
            stroke_width=stroke_width,
        )

    def get_vertical_line(
        self, point: object, **kwargs: Unpack[_DropOptions]
    ) -> HelperLine:
        """Draw a bound drop line from the displayed x axis.

        Parameters
        ----------
        point, **kwargs
            Scene point or live point, and get_line_from_axis_to_point options.

        Returns
        -------
        HelperLine
            A registered leaf following data and placement, unlike Manim's line.
        """
        return self.get_line_from_axis_to_point(0, point, **kwargs)

    def get_horizontal_line(
        self, point: object, **kwargs: Unpack[_DropOptions]
    ) -> HelperLine:
        """Draw a bound drop line from the displayed y axis.

        Parameters
        ----------
        point, **kwargs
            Scene point or live point, and get_line_from_axis_to_point options.

        Returns
        -------
        HelperLine
            A registered leaf following data and placement, unlike Manim's line.
        """
        return self.get_line_from_axis_to_point(1, point, **kwargs)

    def get_lines_to_point(
        self, point: object, **kwargs: Unpack[_DropOptions]
    ) -> HelperGroup:
        """Return horizontal then vertical bound drop lines, as in Manim.

        Parameters
        ----------
        point, **kwargs
            Scene point or live point, and drop-line options.

        Returns
        -------
        HelperGroup
            Named horizontal_line and vertical_line, following the system unlike
            Manim's static group.
        """
        group = HelperGroup()
        group.horizontal_line = self.get_horizontal_line(point, **kwargs)
        group.vertical_line = self.get_vertical_line(point, **kwargs)
        group.add(group.horizontal_line, group.vertical_line)
        return group

    def get_vertical_lines_to_graph(
        self,
        graph: _CurvePlot,
        x_range: Sequence[object] | None = None,
        num_lines: int = 20,
        **kwargs: Unpack[_DropOptions],
    ) -> HelperGroup:
        """Draw equally spaced bound drops from the x axis to a graph.

        Parameters
        ----------
        graph, x_range, num_lines, **kwargs
            Manim's arguments; range endpoints also accept trackers or callables.

        Returns
        -------
        HelperGroup
            Registered lines that follow their graph and range, unlike Manim's.
        """
        return _verticals(self, graph, x_range, num_lines, **kwargs)

    def inset(
        self,
        bounds: Sequence[float],
        x_range: Sequence[float],
        y_range: Sequence[float],
        *,
        connectors: bool = True,
        mirror: Iterable[Mobject] = (),
        **axes_kwargs: object,
    ) -> mp.InsetAxes:
        """Create an inset in fractions of this axes' box.

        Parameters
        ----------
        bounds, x_range, y_range, connectors, mirror, **axes_kwargs
            Box fractions, inset ranges, connectors, artists and axes options.

        Returns
        -------
        InsetAxes
            Independent axes following this system's placement.
        """
        from manim_plots.mobjects.inset import InsetAxes

        return InsetAxes(
            self,
            bounds,
            x_range,
            y_range,
            connectors=connectors,
            mirror=mirror,
            **axes_kwargs,
        )

    def annotate(
        self,
        s: str | Mobject,
        xy: Sequence[object],
        xytext: Sequence[object] | None = None,
        *,
        arrow: bool = True,
        buff: float = 0.1,
        arrow_config: dict[str, Any] | None = None,
        **text_style: object,
    ) -> HelperGroup:
        """Attach text and an optional arrow to a data point.

        Parameters
        ----------
        s, xy, xytext, arrow, buff, arrow_config, **text_style
            Text, bound coordinates, arrow visibility, gap and native styles.

        Returns
        -------
        HelperGroup
            Independently addressable text and arrow.
        """
        return _annotate_2d(
            self,
            s,
            xy,
            xytext,
            arrow=arrow,
            buff=buff,
            arrow_config=arrow_config,
            **text_style,
        )

    def crosshair(
        self,
        x: object,
        y: object = None,
        *,
        graph: FunctionPlot | None = None,
        readout: bool = True,
        fmt: str = "({:.2f}, {:.2f})",
        **style: object,
    ) -> HelperGroup:
        """Follow coordinates with two lines, a dot and an optional readout.

        Parameters
        ----------
        x, y, graph, readout, fmt, **style
            Bound coordinates or graph, readout visibility and format, line style.

        Returns
        -------
        HelperGroup
            Addressable vline, hline, dot and readout.
        """
        return _crosshair(self, x, y, graph=graph, readout=readout, fmt=fmt, **style)

    def end_label(
        self,
        graph: _CurvePlot,
        label: str | Mobject | None = None,
        *,
        fmt: str = "{:.2f}",
        direction: ArrayLike = (1, 0, 0),
        buff: float = 0.15,
        **text_style: object,
    ) -> Mobject:
        """Label the last currently drawn point of a curve.

        Parameters
        ----------
        graph, label, fmt, direction, buff, **text_style
            Curve, optional fixed label, value format, placement and Text style.

        Returns
        -------
        Mobject
            Label following the drawn geometry, including partial creation.
        """
        return _end_label(
            self, graph, label, fmt=fmt, direction=direction, buff=buff, **text_style
        )

    def axvspan(
        self,
        xmin: object,
        xmax: object,
        ymin: object = 0,
        ymax: object = 1,
        **style: object,
    ) -> FilledRegion:
        """Fill a data interval across viewport height fractions.

        Parameters
        ----------
        xmin, xmax, ymin, ymax, **style
            Bound data limits, viewport fractions and region style.

        Returns
        -------
        FilledRegion
            Clipped, bound span.
        """
        return _span(self, 0, xmin, xmax, ymin, ymax, **style)

    def axhspan(
        self,
        ymin: object,
        ymax: object,
        xmin: object = 0,
        xmax: object = 1,
        **style: object,
    ) -> FilledRegion:
        """Fill a data interval across viewport width fractions.

        Parameters
        ----------
        ymin, ymax, xmin, xmax, **style
            Bound data limits, viewport fractions and region style.

        Returns
        -------
        FilledRegion
            Clipped, bound span.
        """
        return _span(self, 1, ymin, ymax, xmin, xmax, **style)

    def fill_betweenx(
        self,
        y: ArrayLike,
        x1: object,
        x2: object = 0,
        *,
        where: ArrayLike | None = None,
        interpolate: bool = False,
        **style: object,
    ) -> FilledRegion:
        """Fill between polylines sampled along y.

        Parameters
        ----------
        y, x1, x2, where, interpolate, **style
            Samples, boundaries, mask, crossing interpolation and region style.

        Returns
        -------
        FilledRegion
            Bound region with fill_between semantics and exchanged axes.
        """
        return _fill_between(
            self, y, x1, x2, where, interpolate, transpose=True, **style
        )

    def axvline(
        self,
        x: object,
        ymin: object = 0,
        ymax: object = 1,
        **style: Unpack[_HelperOptions],
    ) -> HelperLine:
        """Draw a vertical reference line with matplotlib's viewport fractions.

        Parameters
        ----------
        x, ymin, ymax, **style
            Data x, height fractions, and independently persistent artist style.
            Numbers also accept trackers or zero-argument callables.

        Returns
        -------
        HelperLine
            Solid bound artist; Manim has no corresponding helper.
        """
        return _reference(self, 0, x, ymin, ymax, **style)

    def axhline(
        self,
        y: object,
        xmin: object = 0,
        xmax: object = 1,
        **style: Unpack[_HelperOptions],
    ) -> HelperLine:
        """Draw a horizontal reference line with matplotlib's viewport fractions.

        Parameters
        ----------
        y, xmin, xmax, **style
            Data y, width fractions, and independently persistent artist style.
            Numbers also accept trackers or zero-argument callables.

        Returns
        -------
        HelperLine
            Solid bound artist; Manim has no corresponding helper.
        """
        return _reference(self, 1, y, xmin, xmax, **style)

    def get_T_label(
        self,
        x_val: object,
        graph: _CurvePlot,
        label: object = None,
        label_color: ParsableManimColor | None = None,
        triangle_size: float = MED_SMALL_BUFF,
        triangle_color: ParsableManimColor | None = WHITE,
        line_func: type[Line] = Line,
        line_color: ParsableManimColor = PURE_YELLOW,
        *,
        label_direction: ArrayLike = (0, -1, 0),
        label_buff: float = MED_SMALL_BUFF,
    ) -> HelperGroup:
        """Return a sliding T label anchored to the displayed x axis.

        Parameters
        ----------
        x_val, graph, label, label_color, triangle_size, triangle_color
            Manim's arguments; x_val may be bound, and label may be f(x_val).
        line_func, line_color, label_direction, label_buff
            Line type and colour, and the label's side and scene-unit separation.

        Returns
        -------
        HelperGroup
            Named label (when supplied), triangle and line in Manim's order.
            Unlike Manim, the triangle touches a relocated axis and all parts
            follow the graph and system without always_redraw.
        """
        return _t_label(
            self,
            x_val,
            graph,
            label,
            label_color,
            triangle_size,
            triangle_color,
            line_func,
            line_color,
            label_direction,
            label_buff,
        )

    def angle_of_tangent(
        self, x: object, graph: _CurvePlot, dx: object = 1e-8
    ) -> float:
        """Return the data-space chord angle, with Manim's meaning.

        Parameters
        ----------
        x, graph, dx
            Input, bound graph and forward difference; numbers accept bindings.

        Returns
        -------
        float
            Angle in radians. Unlike Manim's sampled graph queries, source
            queries are exact and independent of the displayed frame.
        """
        _graph(self, graph)
        value = _number(_parameter(x, "x").value, "x")
        delta = _number(_parameter(dx, "dx").value, "dx")
        if delta == 0:
            raise ValueError("dx must be nonzero")
        a, b = graph.source.at([value, value + delta])
        chord = b - a
        return float(np.arctan2(chord[1], chord[0]))

    def slope_of_tangent(
        self, x: object, graph: _CurvePlot, **kwargs: Unpack[_SlopeOptions]
    ) -> float:
        """Return the tangent of the data-space angle, as in Manim.

        Parameters
        ----------
        x, graph, **kwargs
            Input, bound graph and angle_of_tangent options.

        Returns
        -------
        float
            Source slope; unlike Manim it uses exact source queries.
        """
        return float(np.tan(self.angle_of_tangent(x, graph, **kwargs)))

    def get_tangent_line(
        self,
        x: object,
        graph: _CurvePlot,
        length: object = 1,
        **style: Unpack[_TangentOptions],
    ) -> HelperLine:
        """Draw a centred tangent of a given scene length on the mapped curve.

        Parameters
        ----------
        x, graph, length, **style
            Bound input, graph, scene length and artist style.

        Returns
        -------
        HelperLine
            A bound tangent queried by x, unlike Manim's TangentLine queried
            by path proportion. Central mapped differences handle log and warp.
        """
        return cast(HelperLine, _tangent_helper(self, x, graph, length, **style))

    def get_tangent_vector(
        self,
        x: object,
        graph: _CurvePlot,
        length: object = 1,
        **style: Unpack[_TangentOptions],
    ) -> HelperGroup:
        """Draw an arrow along the mapped tangent, starting on the graph.

        Parameters
        ----------
        x, graph, length, **style
            Bound input, graph, scene length or f(slope), and artist style.
            tip_length and tip_width default to Manim's 0.35 scene units.

        Returns
        -------
        HelperGroup
            Named line and tip. Manim has no graph-bound counterpart.
        """
        return cast(
            HelperGroup, _tangent_helper(self, x, graph, length, vector=True, **style)
        )

    def get_secant_slope_group(
        self,
        x: object,
        graph: _CurvePlot,
        dx: object = None,
        dx_line_color: ParsableManimColor = PURE_YELLOW,
        dy_line_color: ParsableManimColor | None = None,
        dx_label: object = None,
        dy_label: object = None,
        include_secant_line: bool = True,
        secant_line_color: ParsableManimColor = GREEN,
        secant_line_length: object = 10,
        *,
        dx_label_direction: ArrayLike | None = None,
        dy_label_direction: ArrayLike | None = None,
    ) -> HelperGroup:
        """Return bound secant legs, optional labels and an optional secant.

        Parameters
        ----------
        x, graph, dx, dx_line_color, dy_line_color, dx_label, dy_label
            Manim's inputs and part styles; x and dx accept bindings and labels
            accept f(dx). Omitted dx is a tenth of the span at the call.
        include_secant_line, secant_line_color, secant_line_length
            Manim's secant visibility, colour and scene length.
        dx_label_direction, dy_label_direction
            Optional overrides for the sign-dependent sides of the labels.

        Returns
        -------
        HelperGroup
            Manim's part names and order. Unlike Manim, legs follow the system's
            axes, inputs stay bound, and dx=0 gives the tangent limit.
        """
        return _secant(
            self,
            x,
            graph,
            dx,
            dx_line_color,
            dy_line_color,
            dx_label,
            dy_label,
            include_secant_line,
            secant_line_color,
            secant_line_length,
            dx_label_direction,
            dy_label_direction,
        )

    def plot_derivative_graph(
        self, graph: _CurvePlot, color: ParsableManimColor = GREEN, **kwargs: object
    ) -> FunctionPlot:
        """Plot the data derivative while following the parent graph.

        Parameters
        ----------
        graph, color, **kwargs
            Parent, Manim's default green, and ordinary plot options.

        Returns
        -------
        FunctionPlot
            Unlike Manim, uses central differences with step
            cbrt(eps)*max(1, abs(x)) and follows the parent's parameters/source.
        """
        result = _DerivedPlot(self, graph, False, 0, color=color, **kwargs)
        self.add(result)
        return result

    def plot_antiderivative_graph(
        self,
        graph: _CurvePlot,
        y_intercept: float = 0,
        samples: int = 50,
        use_vectorized: bool = False,
        **kwargs: object,
    ) -> FunctionPlot:
        """Plot a cached primitive following its parent graph.

        Parameters
        ----------
        graph, y_intercept, samples, use_vectorized, **kwargs
            Manim's arguments and plot options. samples is accepted but ignored;
            cached evaluation supports scalar and vector queries alike.

        Returns
        -------
        FunctionPlot
            y_intercept plus the integral from zero. Unlike Manim, integrates
            once per change; if zero is outside the parent's range/domain, the
            anchor is the start of that range instead.
        """
        result = _DerivedPlot(
            self,
            graph,
            True,
            _number(y_intercept, "y_intercept"),
            use_vectorized=use_vectorized,
            **kwargs,
        )
        self.add(result)
        return result

    def get_area(
        self,
        graph: _CurvePlot,
        x_range: Sequence[object] | None = None,
        color: ParsableManimColor | Iterable[ParsableManimColor] = (BLUE, GREEN),
        opacity: float = 0.3,
        bounded_graph: _CurvePlot | float | None = None,
        **kwargs: object,
    ) -> FilledRegion:
        """Fill between a graph and the drawn x axis or another boundary.

        Parameters
        ----------
        graph, x_range, color, opacity, bounded_graph, **kwargs
            Manim's inputs and VMobject style, plus artist clipping options.
            Range ends accept trackers or zero-argument callables. The default
            range follows the graph, intersected with a bounded graph's range.

        Returns
        -------
        FilledRegion
            Unlike Manim's Polygon, stays bound, clips closed fills and follows
            the sampled, smoothed curve. A numeric bounded_graph is constant;
            otherwise the baseline is the x axis wherever it is drawn.
        """
        return _area(self, graph, x_range, color, opacity, bounded_graph, **kwargs)

    def fill_between(
        self,
        x: ArrayLike,
        y1: object,
        y2: object = 0,
        *,
        where: ArrayLike | None = None,
        interpolate: bool = False,
        **style: object,
    ) -> FilledRegion:
        """Fill between two polylines with matplotlib's sampling semantics.

        Parameters
        ----------
        x, y1, y2
            One-dimensional x samples and scalar or matching y arrays. Graphs
            from this system and callables may also supply either boundary.
        where, interpolate
            Boolean sample mask; optionally extend kept stretches to crossings.
        **style
            VMobject style and artist clipping. Defaults are the next cycle
            colour, fill_opacity=0.3 and stroke_width=0.

        Returns
        -------
        FilledRegion
            Bound, clipped closed pieces. Manim has no fill_between verb.
        """
        return _fill_between(
            self, x, y1, y2, where, interpolate, transpose=False, **style
        )

    def get_riemann_rectangles(
        self,
        graph: _CurvePlot,
        x_range: Sequence[object] | None = None,
        dx: object = 0.1,
        input_sample_type: str | Callable[[float, float], float] = "left",
        stroke_width: float = 1,
        stroke_color: ParsableManimColor = BLACK,
        fill_opacity: float = 1,
        color: ParsableManimColor | Iterable[ParsableManimColor] = (BLUE, GREEN),
        show_signed_area: bool = True,
        bounded_graph: _CurvePlot | float | None = None,
        blend: bool = False,
        width_scale_factor: float = 1.001,
        **style: object,
    ) -> HelperGroup:
        """Return bound Riemann rectangles ordered and paired by index.

        Parameters
        ----------
        graph, x_range, dx, input_sample_type
            Manim's graph, interval, positive width and left/right/center sample.
            Width and range ends also accept trackers and callables.
            A sample callable f(left, right) supplies a custom input per bin.
        stroke_width, stroke_color, fill_opacity, color
            Manim's rectangle style and gradient defaults.
        show_signed_area, bounded_graph, blend, width_scale_factor
            Invert negative fills, choose the base, blend borders and scale width.
        **style
            Additional VMobject style and artist clipping options.

        Returns
        -------
        HelperGroup
            Individually styleable FilledRegion parts. Unlike Manim, counts
            tolerate endpoint roundoff, both graphs use the selected sample,
            and quadrilaterals follow the system's map, frame and inputs.
        """
        return _riemann(
            self,
            graph,
            x_range,
            dx,
            input_sample_type,
            stroke_width,
            stroke_color,
            fill_opacity,
            color,
            show_signed_area,
            bounded_graph,
            blend,
            width_scale_factor,
            **style,
        )

    def legend(
        self,
        location: str | None = None,
        *,
        font_size: float = 24,
        buff: float = 0.25,
        frame: bool | None = None,
        frame_style: Mapping[str, Any] | None = None,
    ) -> Legend:
        """Create a bound legend for labelled artists in registration order.

        Parameters
        ----------
        location
            One of upper right, upper left, lower left or lower right;
            None uses the theme's corner.
        font_size, buff
            Native text size and entry/corner spacing in scene units.
        frame
            Draw a rectangle around the entries; None uses the theme's default.
        frame_style
            Frame VMobject styles, defaulting to the x axis's line colour,
            stroke width one and no fill.

        Returns
        -------
        Legend
            The newly created legend, attached to this system's family.
        """
        location = self.theme.legend_location if location is None else location
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
        artists = self._legend_artists()
        if not artists:
            raise ValueError("legend requires an artist with a label")
        legend = Legend(
            *artists,
            font_size=font_size,
            buff=buff,
            frame=self.theme.legend_frame if frame is None else frame,
            frame_style={"color": self.x.line.get_color(), **(frame_style or {})},
        )
        corner = np.array([*locations[location], 0.0], dtype=float)
        local = np.where(
            corner[: len(self._ranges)] > 0, self.bounds.upper, self.bounds.lower
        )
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
        artists = self._legend_artists()
        return (
            [_handle(a) for a in artists],
            [cast(str, a.get_label()) for a in artists],
        )

    def _legend_artists(self) -> list[_CurvePlot | ScatterPlot | ErrorBars]:
        registered = sorted(
            (order, ref)
            for system in self._systems()
            for order, ref in system._artists._refs
        )
        return [
            artist
            for _, ref in registered
            if (artist := ref()) is not None and artist.get_label() is not None
        ]

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
            for system in self._systems():
                for artist in system._artists:
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
    def artists(self) -> tuple[_CurvePlot | ScatterPlot | ErrorBars, ...]:
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
            if not isinstance(artist, (_CurvePlot, ScatterPlot, ErrorBars)):
                raise TypeError("artists must be plotting artists")
            if artist._system is not None and artist._system is not self:
                raise ValueError("artist is bound to another system")
            if artist not in self._artists:
                if artist._system is None:
                    artist._system = self
                    for leaf in artist.get_family():
                        if isinstance(artist, ErrorBars) and isinstance(
                            leaf, ScatterPlot
                        ):
                            leaf._system = self
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
            assert isinstance(artist, (_CurvePlot, ScatterPlot, ErrorBars))
            for leaf in artist.get_family():
                if isinstance(artist, ErrorBars) and isinstance(leaf, ScatterPlot):
                    leaf._system = None
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
        result._artists._clock = copy.deepcopy(self._artists._clock, memo)
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
    theme, cycle
        Series and legend defaults, as on CartesianAxes. The axes and background
        grid retain NumberPlane's defaults and explicit constructor styles.
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
        *,
        theme: str | Theme | Mapping[str, Any] | None = None,
        cycle: str | Sequence[ParsableManimColor] | None = None,
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
            theme=theme,
            cycle=cycle,
            make_smooth_after_applying_functions=make_smooth_after_applying_functions,
            **options,
        )
        for axis in self._ranges:
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
