"""Bound rectangles, grouped bars and Manim-compatible bar charts."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from numbers import Real
from typing import Any, Self, Unpack, cast

import numpy as np
from manim import (
    DOWN,
    MED_SMALL_BUFF,
    RIGHT,
    UP,
    ManimColor,
    Mobject,
    Tex,
    Text,
    VGroup,
    VMobject,
    config,
)

import manim_plots as mp
from manim_plots.core.payload import Payload
from manim_plots.core.shape import corners
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.artists import _CurvePlot, _cycle_style
from manim_plots.mobjects.axis import resolve_categories
from manim_plots.mobjects.colormaps import resolve_colorscale
from manim_plots.mobjects.helpers import _parameter
from manim_plots.mobjects.leaves import Leaf, _ArtistOptions, _label, _VMStyle
from manim_plots.mobjects.system import CartesianAxes


def _entries(value: object) -> np.ndarray[Any, np.dtype[np.object_]]:
    entries = (
        (value,)
        if isinstance(value, (Real, str))
        or callable(value)
        or hasattr(value, "get_value")
        else cast(Iterable[object], value)
    )
    return np.fromiter(entries, dtype=object)


class _Bar(_CurvePlot):
    def __init__(
        self,
        system: CartesianAxes,
        values: Sequence[object],
        horizontal: bool,
        **style: Unpack[_ArtistOptions],
    ) -> None:
        self.horizontal = horizontal
        self._label_bindings: list[_LabelBinding] = []
        self.parameters = {
            name: _parameter(value, name)
            for name, value in zip(
                ("x", "height", "width", "bottom"), values, strict=True
            )
        }
        super().__init__(
            ArraySource(np.empty((0, 2))), system, use_smoothing=False, **style
        )

    def _rebuild(self) -> None:
        system = self._system
        assert system is not None
        system._sync_data()
        x, height, width, bottom = (
            float(self.parameters[name].value)
            for name in ("x", "height", "width", "bottom")
        )
        if not np.isfinite([x, height, width, bottom]).all():
            raise ValueError("bar coordinates must be finite")
        a, b = (
            np.array([x - width / 2, bottom]),
            np.array([x + width / 2, bottom + height]),
        )
        if self.horizontal:
            a, b = a[::-1], b[::-1]
        for i, axis in enumerate(system._ranges):
            low = min(axis.range.value)
            if not np.isfinite(axis._scale.forward([a[i]])).all():
                a[i] = low
            if not np.isfinite(axis._scale.forward([b[i]])).all():
                b[i] = low
        native = system._data.forward(np.array([a, b]))
        low = np.maximum(native.min(axis=0), system.bounds.lower)
        high = np.minimum(native.max(axis=0), system.bounds.upper)
        polygon = (
            np.empty((0, 2))
            if np.any(low > high)
            else np.array([high, [low[0], high[1]], low, [high[0], low[1]], high])
        )
        self._geometry_payload = corners(Payload.path(polygon), system.bounds)
        self._place(self._frame())
        self._data_seen = system._data_version
        self._parameter_versions = {
            name: p.version for name, p in self.parameters.items()
        }
        self._dirty = False


class _LabelBinding:
    def __init__(
        self,
        text: VMobject,
        bar: _Bar,
        place: Callable[[Mobject], None],
        factory: Callable[[], VMobject] | None = None,
    ) -> None:
        self.text, self.bar, self.place = text, bar, place
        self.factory = factory
        self.value = bar.parameters["height"].value
        self.seen: object = None
        self.busy = False
        self._glyphs(text)
        text.add_updater(lambda _: self._ensure())
        bar._label_bindings.append(self)

    def _glyphs(self, text: VMobject) -> None:
        glyphs = _label(text)
        self.text.submobjects = glyphs.submobjects
        for leaf in self.text.get_family():
            if isinstance(leaf, Leaf):
                cast(Any, leaf)._label_owner = self

    def _ensure(self) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            self.bar._poll()
            self.bar._ensure()
            value = self.bar.parameters["height"].value
            if value != self.value and self.factory is not None:
                fresh = self.factory()
                fresh.match_style(self.text)
                self._glyphs(fresh)
                if isinstance(self.text, Text) and isinstance(fresh, Text):
                    self.text.text = fresh.text
                self.value = value
                self.seen = None
            if self.seen is not self.bar._cache:
                self.place(self.text)
                self.seen = self.bar._cache
        finally:
            self.busy = False


class BarPlot(VGroup):
    """Draw independent bound bars.

    Parameters
    ----------
    system, x, height, width, bottom
        Owning axes and broadcastable data coordinates.
    align, horizontal
        Edge or centre alignment and orientation.
    color, c, colorscale, vmin, vmax, norm, label, **style
        Native style, value colour mapping and legend label.
    """

    def __init__(
        self,
        system: CartesianAxes,
        x: object,
        height: object,
        width: object = 0.8,
        bottom: object = 0,
        *,
        align: str = "center",
        horizontal: bool = False,
        color: object = None,
        c: object = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        label: str | None = None,
        **style: object,
    ) -> None:
        if align not in ("center", "edge"):
            raise ValueError("align must be center or edge")
        self._system, self.horizontal, self.align = system, horizontal, align
        self._keys = list(np.atleast_1d(np.asarray(x)))
        axis = system.y if horizontal else system.x
        positions = resolve_categories(axis, x)
        arrays = np.broadcast_arrays(
            np.atleast_1d(np.asarray(positions)),
            _entries(height),
            np.asarray(width),
            np.asarray(bottom),
        )
        if arrays[0].ndim != 1:
            raise ValueError("bar data must be one dimensional")
        self._keys = list(np.broadcast_to(np.asarray(x), arrays[0].shape))
        self._color_mapping: mp.ColorMapping | None = None
        colors: Any = None
        if c is not None:
            values = (
                np.array(
                    [_parameter(v, "height").value for v in arrays[1]], dtype=float
                )
                if isinstance(c, str) and c == "height"
                else np.asarray(c, dtype=float)
            )
            if values.shape != arrays[0].shape or not np.isfinite(values).all():
                raise ValueError("c must contain one finite value per bar")
            lo, hi = (
                (float(values.min()), float(values.max()))
                if len(values)
                else (0.0, 1.0)
            )
            self._color_mapping = resolve_colorscale(
                "viridis" if colorscale is None else colorscale,
                vmin=vmin,
                vmax=vmax,
                norm=cast(Any, norm),
                default_range=(lo, hi if hi > lo else lo + 1),
            )
            colors = self._color_mapping(values)
        elif color is not None:
            if isinstance(color, (list, tuple, np.ndarray)) and not (
                len(color) in (3, 4)
                and all(isinstance(channel, Real) for channel in color)
            ):
                colors = color
            else:
                style["color"] = color
        if colors is not None and len(colors) != len(arrays[0]):
            raise ValueError("color must contain one colour per bar")
        if colors is None:
            _cycle_style(system, cast(_VMStyle, style))
        style.setdefault("fill_opacity", 1)
        style.setdefault("stroke_width", 0)
        super().__init__()
        for i, row in enumerate(zip(*arrays, strict=True)):
            bar_values = list(row)
            if align == "edge":
                bar_values[0] += bar_values[2] / 2
            own = dict(style)
            if colors is not None:
                own["color"] = colors[i]
            own["label"] = label if i == 0 else None
            bar = _Bar(
                system,
                bar_values,
                horizontal,
                **cast(_ArtistOptions, own),
            )
            self.add(bar)
            system.add(bar)

    @property
    def color_mapping(self) -> mp.ColorMapping | None:
        """Return the value colour mapping, when supplied."""
        return self._color_mapping

    def at(self, key: object) -> _Bar:
        """Return the bar at a category or data position.

        Parameters
        ----------
        key
            Original category name or numeric coordinate.
        """
        return cast(_Bar, self.submobjects[self._keys.index(key)])

    def set_data(
        self,
        *,
        x: object = None,
        height: object = None,
        width: object = None,
        bottom: object = None,
        c: object = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
    ) -> Self:
        """Rewrite existing bars while retaining their styles and identities.

        Parameters
        ----------
        x, height, width, bottom
            Replacement coordinates; omitted coordinates retain their values.
        c, colorscale, vmin, vmax, norm
            Optional replacement colour values and mapping.
        """
        if c is not None:
            values = np.asarray(c, dtype=float)
            if values.shape != (len(self),) or not np.isfinite(values).all():
                raise ValueError("c must contain one finite value per bar")
            lo, hi = (
                (float(values.min()), float(values.max()))
                if len(values)
                else (0.0, 1.0)
            )
            self._color_mapping = resolve_colorscale(
                "viridis" if colorscale is None else colorscale,
                vmin=vmin,
                vmax=vmax,
                norm=cast(Any, norm),
                default_range=(lo, hi if hi > lo else lo + 1),
            )
            for mob, color in zip(
                self.submobjects, self._color_mapping(values), strict=True
            ):
                mob.set_color(ManimColor(color.tolist()))
        updates = dict(x=x, height=height, width=width, bottom=bottom)
        if x is not None:
            self._keys = list(np.broadcast_to(np.asarray(x), (len(self),)))
            updates["x"] = resolve_categories(
                self._system.y if self.horizontal else self._system.x, x
            )
        resolved = {
            name: np.broadcast_to(_entries(value), (len(self),))
            for name, value in updates.items()
            if value is not None
        }
        for i, mob in enumerate(self.submobjects):
            bar = cast(_Bar, mob)
            if self.align == "edge" and "width" in resolved and "x" not in resolved:
                bar.parameters["x"].value += (
                    resolved["width"][i] - bar.parameters["width"].value
                ) / 2
            for name, values in resolved.items():
                value = values[i]
                if name == "x" and self.align == "edge":
                    value += (
                        resolved["width"][i]
                        if "width" in resolved
                        else bar.parameters["width"].value
                    ) / 2
                bar.parameters[name] = _parameter(value, name)
            bar._dirty = True
            bar._ensure()
            for binding in bar._label_bindings:
                binding._ensure()
        return self


class GroupedBarPlot(VGroup):
    """Keep the bar plots of each dataset together.

    Parameters
    ----------
    bar_plots
        One bar plot per dataset.
    """

    def __init__(self, bar_plots: Sequence[BarPlot]) -> None:
        self.bar_plots = tuple(bar_plots)
        super().__init__(*bar_plots)


def bar_label(
    container: BarPlot,
    labels: Sequence[str] | None = None,
    *,
    fmt: str = "{:g}",
    label_type: str = "edge",
    padding: float = 0.1,
    **text_style: object,
) -> VGroup:
    """Build labels which follow the bars.

    Parameters
    ----------
    container, labels, fmt, label_type, padding, **text_style
        Bars, optional text, value format, placement, scene gap and Text style.
    """
    if label_type not in ("edge", "center"):
        raise ValueError("label_type must be edge or center")
    if labels is not None and len(labels) != len(container):
        raise ValueError("labels must contain one string per bar")
    result = VGroup()
    for i, mob in enumerate(container.submobjects):
        bar = cast(_Bar, mob)
        value = float(bar.parameters["height"].value)
        text = Text(
            fmt.format(value) if labels is None else labels[i],
            **cast(Any, {"font_size": 24, **text_style}),
        )

        def place(m: Mobject, bar: _Bar = bar) -> None:
            value = float(bar.parameters["height"].value)
            direction = (RIGHT if container.horizontal else UP) * (
                1 if value >= 0 else -1
            )
            if label_type == "center":
                m.move_to(bar.get_center())
            else:
                m.next_to(bar, direction, buff=padding)

        place(text)

        def factory(bar: _Bar = bar, i: int = i) -> VMobject:
            return Text(
                fmt.format(float(bar.parameters["height"].value))
                if labels is None
                else labels[i],
                **cast(Any, {"font_size": 24, **text_style}),
            )

        _LabelBinding(text, bar, place, factory)
        result.add(text)
    container.add_updater(lambda _: result.update())
    return result


class BarChart(CartesianAxes):
    """Create a chart using Manim's bar-chart defaults.

    Parameters
    ----------
    values, bar_names, y_range, x_length, y_length
        Bar values, names and axes dimensions.
    bar_colors, bar_width, bar_fill_opacity, bar_stroke_width, **kwargs
        Gradient, bar geometry, native styles and axes options.
    """

    def __init__(
        self,
        values: Sequence[float],
        bar_names: Sequence[str] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        bar_colors: Sequence[str] = (
            "#003f5c",
            "#58508d",
            "#bc5090",
            "#ff6361",
            "#ffa600",
        ),
        bar_width: float = 0.6,
        bar_fill_opacity: float = 0.7,
        bar_stroke_width: float = 3,
        **kwargs: object,
    ) -> None:
        options = cast(dict[str, Any], kwargs)
        self.values = list(values)
        self.bar_names, self.bar_colors = bar_names, bar_colors
        self.bar_width = bar_width
        self.bar_fill_opacity, self.bar_stroke_width = (
            bar_fill_opacity,
            bar_stroke_width,
        )
        y_length = y_length if y_length is not None else config.frame_height - 4
        if y_range is None:
            y_range = [
                min(0, min(values)),
                max(0, max(values)),
                round(max(values) / y_length, 2),
            ]
        elif len(y_range) == 2:
            y_range = [*y_range, round(max(values) / y_length, 2)]
        x_length = (
            x_length
            if x_length is not None
            else min(len(values), config.frame_width - 2)
        )
        x_config: dict[str, Any] = {"font_size": 24, **options.pop("x_axis_config", {})}
        constructor = x_config.pop("label_constructor", Tex)
        super().__init__(
            x_range=[0, len(values), 1],
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            x_axis_config=x_config,
            tips=options.pop("tips", False),
            **options,
        )
        self.bars = self.bar(
            np.arange(len(values)) + 0.5,
            values,
            width=bar_width,
            fill_opacity=bar_fill_opacity,
            stroke_width=bar_stroke_width,
        )
        self.bars.set_color_by_gradient(*bar_colors)
        self.submobjects.insert(0, self.bars)
        self.x_labels: VGroup | None = None
        self.bar_labels: VGroup | None = None
        if bar_names is not None:
            self.bars._keys = list(bar_names)
            self.x_labels = VGroup()
            for i, name in enumerate(bar_names):
                text = constructor(name)
                text.font_size = self.x.font_size
                text.next_to(
                    self.x.number_to_point(i + 0.5),
                    UP if values[i] < 0 else DOWN,
                    buff=self.x.line_to_number_buff,
                )
                self.x_labels.add(text)

                def place_name(m: Mobject, i: int = i) -> None:
                    bar = cast(_Bar, self.bars[i])
                    m.next_to(
                        self.x.number_to_point(i + 0.5),
                        UP if float(bar.parameters["height"].value) < 0 else DOWN,
                        buff=self.x.line_to_number_buff,
                    )

                _LabelBinding(text, cast(_Bar, self.bars[i]), place_name)
            self.submobjects.append(self.x_labels)
        self.y.add_numbers()

    def get_bar_labels(
        self,
        color: object = None,
        font_size: float = 24,
        buff: float = MED_SMALL_BUFF,
        label_constructor: Callable[[str], VMobject] = Tex,
    ) -> VGroup:
        """Create native labels bound to the bars.

        Parameters
        ----------
        color, font_size, buff, label_constructor
            Optional colour, size, scene gap and native text constructor.
        """
        result = VGroup()
        for mob, value in zip(self.bars, self.values, strict=True):
            bar = cast(_Bar, mob)
            text = label_constructor(str(value))
            cast(Any, text).font_size = font_size
            text.set_color(bar.get_fill_color() if color is None else cast(Any, color))

            def place(m: Mobject, bar: _Bar = bar) -> None:
                m.next_to(
                    bar,
                    UP if float(bar.parameters["height"].value) >= 0 else DOWN,
                    buff=buff,
                )

            place(text)

            def factory(bar: _Bar = bar) -> VMobject:
                label = label_constructor(str(bar.parameters["height"].value))
                cast(Any, label).font_size = font_size
                return label

            _LabelBinding(text, bar, place, factory)
            result.add(text)
        self.bars.add_updater(lambda _: result.update())
        self.bar_labels = result
        return result

    def change_bar_values(
        self, values: Sequence[float], update_colors: bool = True
    ) -> None:
        """Rewrite the chart's values, including bars previously at zero.

        Parameters
        ----------
        values, update_colors
            Replacement values and Manim-compatible colour update flag.
        """
        self.bars.set_data(height=values)
        self.values = list(values)


def _grouped_bar(
    self: CartesianAxes,
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
    """Assemble grouped bars using the documented spacing formula."""
    if isinstance(heights, Mapping):
        labels = list(heights) if labels is None else labels
        heights = list(heights.values())
    values = np.asarray(heights, dtype=float)
    if values.ndim != 2 or not values.size or not np.isfinite(values).all():
        raise ValueError("heights must be a nonempty rectangular array")
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation must be vertical or horizontal")
    m, n = values.shape
    positions = (
        np.arange(n, dtype=float)
        if positions is None
        else np.asarray(positions, dtype=float)
    )
    if positions.shape != (n,) or not np.isfinite(positions).all():
        raise ValueError("positions must contain one finite value per group")
    d = float(np.min(np.diff(positions))) if n > 1 else 1.0
    if (
        d <= 0
        or not np.isfinite([group_spacing, bar_spacing]).all()
        or group_spacing < 0
        or bar_spacing < 0
    ):
        raise ValueError("positions must increase and spacing must be nonnegative")
    if labels is not None and len(labels) != m:
        raise ValueError("labels must contain one string per dataset")
    if colors is not None and len(cast(Sequence[object], colors)) != m:
        raise ValueError("colors must contain one colour per dataset")
    w = d / (m + (m - 1) * bar_spacing + group_spacing)
    total = m * w + (m - 1) * bar_spacing * w
    axis = self.y if orientation == "horizontal" else self.x
    if tick_labels is not None:
        if len(tick_labels) != n:
            raise ValueError("tick_labels must match the groups")
        if len(set(tick_labels)) != n or any(
            not isinstance(name, str) for name in tick_labels
        ):
            raise ValueError("tick_labels must be unique strings")
        axis._set_categories(tick_labels, list(positions))
        axis.set_locator(mp.FixedLocator(positions))
        axis.set_formatter(
            mp.FixedFormatter(dict(zip(positions, tick_labels, strict=True)))
        )
    plots = []
    for j, dataset in enumerate(values):
        centres = positions - total / 2 + w / 2 + j * w * (1 + bar_spacing)
        method = self.barh if orientation == "horizontal" else self.bar
        plot = method(
            centres,
            dataset,
            w,
            color=None if colors is None else cast(Sequence[object], colors)[j],
            label=None if labels is None else labels[j],
            **cast(Any, style),
        )
        plots.append(plot)
    return mp.GroupedBarPlot(plots)
