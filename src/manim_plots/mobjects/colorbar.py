"""A scale-aware colour strip with a numbered Cartesian value axis."""

from __future__ import annotations

from functools import partial
from typing import Any, Protocol, cast

import numpy as np
from manim import (
    MED_SMALL_BUFF,
    ManimColor,
    Mobject,
    Rectangle,
    VGroup,
    config,
)

from manim_plots.core.scales import LinearScale, Scale
from manim_plots.core.ticks import MaxNLocator
from manim_plots.mobjects.axis import Axis, _scale_range
from manim_plots.mobjects.colormaps import ColorMapping, resolve_colorscale
from manim_plots.mobjects.placement import _place_beside
from manim_plots.mobjects.system import CartesianAxes


class _Mappable(Protocol):
    @property
    def color_mapping(self) -> ColorMapping | None: ...


class Colorbar(CartesianAxes):
    """Show a mapping beside axes, or fixed in a three-dimensional camera frame.

    Parameters
    ----------
    parent_axes
        Axes supplying default length and placement.
    mappable
        Artist exposing a color_mapping, or None for an explicit mapping.
    colorscale, vmin, vmax, norm
        Explicit mapping, mutually exclusive with mappable.
    label, length, width, buff
        Axis label, strip dimensions and gap from the parent axes.
    **kwargs
        CartesianAxes decoration options.
    """

    def __init__(
        self,
        parent_axes: CartesianAxes,
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
    ) -> None:
        if (mappable is None) == (colorscale is None):
            raise ValueError("provide either mappable or colorscale")
        mapping = (
            cast(_Mappable, mappable).color_mapping
            if mappable is not None
            else resolve_colorscale(colorscale, vmin=vmin, vmax=vmax, norm=norm)
        )
        if not isinstance(mapping, ColorMapping):
            raise ValueError("mappable must have a color_mapping")
        self._parent_axes = parent_axes
        self._mappable = cast(_Mappable | None, mappable)
        self._last_mapping = mapping
        self._bar_width, self._bar_buff = width, buff
        self._fixed = False
        self._parent_box: Any = None
        if length is None:
            length = float(getattr(parent_axes, "z_length", parent_axes.y_length))
        super().__init__(
            x_range=(0, 1),
            y_range=(mapping.vmin, mapping.vmax),
            x_length=width,
            y_length=length,
            y_scale=mapping.scale,
            tips=False,
            **cast(dict[str, Any], kwargs),
        )
        self.submobjects.remove(self.x_axis)
        self.y.exclude_origin_tick = False
        if isinstance(mapping.scale, LinearScale):
            self.y.locator = MaxNLocator()
        self.y.set_position("right")
        self.y.add_numbers(excluding=())
        self.axis: Axis = self.y
        self.strip = VGroup(
            *(Rectangle(stroke_width=0, fill_opacity=1) for _ in range(64))
        )
        self.submobjects.insert(0, self.strip)
        self._paint_strip(mapping)
        if label is not None:
            self.submobjects.append(self.get_y_axis_label(label))
        self._follow_parent()
        self.add_updater(_colorbar_update)
        _colorbar_update(self, 0)

    def _paint_strip(self, mapping: ColorMapping) -> None:
        lo, hi = mapping.scale.forward(np.array([mapping.vmin, mapping.vmax]))
        edges = mapping.scale.inverse(np.linspace(lo, hi, 65))
        centres = mapping.scale.inverse(lo + (hi - lo) * (np.arange(64) + 0.5) / 64)
        colors = mapping(centres)
        for k, cell in enumerate(self.strip):
            corners = self.c2p(
                np.array(
                    [
                        [0, edges[k]],
                        [1, edges[k]],
                        [1, edges[k + 1]],
                        [0, edges[k + 1]],
                        [0, edges[k]],
                    ]
                )
            )
            cell.set_points_as_corners(corners)
            cell.set_fill(ManimColor.from_rgb(colors[k]), opacity=1)

    def _follow_parent(self) -> None:
        _place_beside(
            self,
            self._parent_axes,
            "right",
            self._bar_buff,
            anchor=self.strip,
            frame_offset=config.frame_width / 2 - 1,
        )
        self._fixed = self.__dict__.get("_beside_fixed", False)


def _colorbar_update(mobject: Mobject, dt: float) -> None:
    bar = cast(Colorbar, mobject)
    if bar._mappable is not None:
        mapping = bar._mappable.color_mapping
        if mapping is not None and mapping != bar._last_mapping:
            bar.axis._scale = mapping.scale
            bar.axis._range_parameter._validate = partial(_scale_range, mapping.scale)
            bar.set_y_range((mapping.vmin, mapping.vmax))
            bar._paint_strip(mapping)
            bar._last_mapping = mapping
    bar._follow_parent()
