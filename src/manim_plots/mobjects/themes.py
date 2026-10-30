"""Construction-time axis defaults and named series colour cycles.

``manim`` preserves axes through the origin, tips, straddling ticks, scale-default
minors, no grid, an unframed upper-right legend and the existing Manim cycle.
``origin`` supplies a bottom/left border box with unlabelled top/right mirrors,
no tips, inward ticks, one minor tick, no grid, an upper-left framed legend and
Origin colours. ``base`` adds a major grid (opacity 0.35, width 1) and moves that
legend upper right. ``paper`` keeps Origin's defaults with greys, solid/dashed/
dotted lines and circle/square/triangle/cross markers. ``lab`` keeps Origin's
defaults with four minors, base's major grid, a minor grid (opacity 0.15, width
0.5) and Petroff's ten colours. Every preset leaves direction to the border rule.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from typing import Any, Literal

from manim.utils.color import ManimColor, ParsableManimColor

from manim_plots.core.ticks import Level
from manim_plots.mobjects.artists import COLOR_CYCLE, LineStyle, Marker
from manim_plots.mobjects.axis import TickDirection

CYCLES: Mapping[str, tuple[ManimColor, ...]] = {
    "manim": COLOR_CYCLE,
    **{
        name: tuple(ManimColor(value) for value in colours.split())
        for name, colours in {
            "origin": "#515151 #F14040 #1A6FDF #37AD6B #B177DE #CC9900 #00CBCC "
            "#7D4E4E #8E8E00 #FB6501 #6699CC #6FB802",
            "fire": "#8B0800 #FF0000 #E51800 #FF3E1C #FF5B00 #FF9000 #F4A666 "
            "#FFC600 #FFFF7D",
            "colorblind": "#3F90DA #FFA90E #BD1F01 #94A4A2 #832DB6 #A96B59 "
            "#E76300 #B9AC70 #717581 #92DADD",
            "gray": "#FFFFFF #BBBBBB #888888 #555555",
        }.items()
    },
}
"""Exact Manim, Origin, Fire, Petroff 10 and grey colour sequences."""


def _resolve_cycle(
    cycle: str | Sequence[ParsableManimColor],
) -> tuple[ManimColor, ...]:
    if isinstance(cycle, str):
        if cycle not in CYCLES:
            raise ValueError(f"unknown cycle {cycle!r}")
        return CYCLES[cycle]
    colours = tuple(ManimColor(value) for value in cycle)
    if not colours:
        raise ValueError("cycle must contain at least one colour")
    return colours


@dataclass(frozen=True)
class Theme:
    """Describe defaults applied once when a system is constructed.

    Parameters
    ----------
    name
        Name used to identify this preset.
    position
        Axes through the origin or at the bottom and left borders.
    box
        Add unlabelled mirrors at the opposite borders, without tips.
    tips
        Default endpoint tips on the primary axes.
    tick_direction
        Explicit tick direction, or None for inward border ticks and straddling
        ticks through the data. Minor ticks inherit the major direction.
    minor_ticks
        Number of minor ticks between major ticks; zero keeps scale defaults.
    grid
        Grid levels to enable.
    grid_style
        Major grid's VMobject style; later set_grid calls can style either level.
    minor_grid_style
        Minor grid's style over grid_style, defaulting to opacity 0.15 and width
        0.5.
    legend_location, legend_frame
        Default legend corner and whether to draw its frame.
    cycle
        Named colour cycle or a nonempty tuple of Manim colours.
    line_styles, markers
        Optional sequences selected with the series colour index. An explicit
        artist style or marker takes precedence.

    Notes
    -----
    See this module's docstring for the contents of each named theme. Use
    dataclasses.replace to derive a preset without altering the original.
    NumberPlane uses only the series and legend defaults.
    """

    name: str
    position: Literal["origin", "border"] = "origin"
    box: bool = False
    tips: bool = True
    tick_direction: TickDirection | None = None
    minor_ticks: int = 0
    grid: tuple[Level, ...] = ()
    grid_style: Mapping[str, Any] = field(default_factory=dict)
    minor_grid_style: Mapping[str, Any] = field(
        default_factory=lambda: {"stroke_opacity": 0.15, "stroke_width": 0.5}
    )
    legend_location: str = "upper right"
    legend_frame: bool = False
    cycle: str | tuple[ParsableManimColor, ...] = "manim"
    line_styles: tuple[LineStyle, ...] = ()
    markers: tuple[Marker, ...] = ()

    def __post_init__(self) -> None:
        if self.position not in ("origin", "border"):
            raise ValueError(f"unknown position {self.position!r}")
        if not isinstance(self.minor_ticks, int) or self.minor_ticks < 0:
            raise ValueError("minor_ticks must be a nonnegative integer")
        if any(level not in ("major", "minor") for level in self.grid):
            raise ValueError(f"unknown grid level in {self.grid!r}")
        if self.tick_direction is not None and not isinstance(
            self.tick_direction, TickDirection
        ):
            raise ValueError(f"unknown tick_direction {self.tick_direction!r}")
        if any(not isinstance(style, LineStyle) for style in self.line_styles):
            raise ValueError(f"unknown line_styles {self.line_styles!r}")
        if any(not isinstance(marker, Marker) for marker in self.markers):
            raise ValueError(f"unknown markers {self.markers!r}")
        _resolve_cycle(self.cycle)


_origin = Theme(
    "origin",
    position="border",
    box=True,
    tips=False,
    minor_ticks=1,
    legend_location="upper left",
    legend_frame=True,
    cycle="origin",
)
_base = replace(
    _origin,
    name="base",
    grid=("major",),
    grid_style={"stroke_opacity": 0.35, "stroke_width": 1},
    legend_location="upper right",
)
THEMES: Mapping[str, Theme] = {
    "manim": Theme("manim"),
    "origin": _origin,
    "base": _base,
    "paper": replace(
        _origin,
        name="paper",
        cycle="gray",
        line_styles=(LineStyle.SOLID, LineStyle.DASHED, LineStyle.DOTTED),
        markers=(Marker.CIRCLE, Marker.SQUARE, Marker.TRIANGLE, Marker.CROSS),
    ),
    "lab": replace(
        _origin,
        name="lab",
        minor_ticks=4,
        grid=("major", "minor"),
        grid_style=_base.grid_style,
        cycle="colorblind",
    ),
}
"""Named presets; see the module docstring for each preset's defaults."""
_default_theme = THEMES["manim"]


def _resolve_theme(theme: str | Theme | Mapping[str, Any] | None) -> Theme:
    if theme is None:
        return get_theme()
    if isinstance(theme, str):
        if theme not in THEMES:
            raise ValueError(f"unknown theme {theme!r}")
        return THEMES[theme]
    if isinstance(theme, Mapping):
        names = {entry.name for entry in fields(Theme)}
        for name in theme:
            if name not in names:
                raise ValueError(f"unknown theme field {name!r}")
        return Theme(**theme)
    if not isinstance(theme, Theme):
        raise TypeError("theme must be a name, Theme, mapping or None")
    return theme


def set_theme(theme: str | Theme | Mapping[str, Any] | None) -> None:
    """Set the default theme for subsequently constructed systems.

    Parameters
    ----------
    theme
        Registered name, Theme or mapping of Theme fields. None restores manim.

    Raises
    ------
    ValueError
        A theme name, field or colour cycle is unknown.
    """
    global _default_theme
    _default_theme = THEMES["manim"] if theme is None else _resolve_theme(theme)


def get_theme() -> Theme:
    """Return the default theme for subsequently constructed systems.

    Returns
    -------
    Theme
        Current module default, initially the manim preset.
    """
    return _default_theme
