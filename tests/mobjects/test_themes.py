"""Task 20: themes and colour cycles.

Rows TH of `docs/acceptance/20-themes.md`. A theme only sets defaults, so each one is
checked by what it draws: where the axes sit, the box, the tips, the tick direction, the
minor ticks, the grid, the legend and the cycle.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import pytest
from manim import UP, ManimColor

import manim_plots as mp
from manim_plots.mobjects.axis import Axis

RANGES: dict[str, Any] = {
    "x_range": (0, 10, 2),
    "y_range": (0, 4, 1),
    "x_length": 8,
    "y_length": 4,
}

HEX = {
    "origin": "#515151 #F14040 #1A6FDF #37AD6B #B177DE #CC9900 #00CBCC #7D4E4E "
    "#8E8E00 #FB6501 #6699CC #6FB802",
    "fire": "#8B0800 #FF0000 #E51800 #FF3E1C #FF5B00 #FF9000 #F4A666 #FFC600 #FFFF7D",
    "colorblind": "#3F90DA #FFA90E #BD1F01 #94A4A2 #832DB6 #A96B59 #E76300 #B9AC70 "
    "#717581 #92DADD",
    "gray": "#FFFFFF #BBBBBB #888888 #555555",
}


def axes(**kwargs):
    return mp.Axes(**RANGES, **kwargs)


def hexes(colours) -> list[str]:
    return [ManimColor(c).to_hex().upper() for c in colours]


def leaves(ax) -> list[tuple[str, tuple[float, ...], str, float]]:
    """Every leaf with points: type, rounded points and stroke, in a stable order."""
    out = []
    for m in ax.get_family():
        if m is ax.frame or not m.has_points():
            continue
        points = tuple(np.round(np.asarray(m.points), 9).ravel().tolist())
        colour = m.get_stroke_color().to_hex().upper()
        out.append((type(m).__name__, points, colour, float(m.get_stroke_width())))
    return sorted(out)


def border(ax):
    lower, upper = ax.c2p(0, 0), ax.c2p(10, 4)
    return float(lower[0]), float(lower[1]), float(upper[0]), float(upper[1])


def line_y(axis) -> float:
    return float(np.asarray(axis.line.points)[:, 1].mean())


def line_x(axis) -> float:
    return float(np.asarray(axis.line.points)[:, 0].mean())


def lines(ax) -> list[tuple[float, float, float, float]]:
    """The bounding boxes of every axis line in the family, mirrors included."""
    out = []
    for m in ax.get_family():
        if isinstance(m, Axis):
            p = np.asarray(m.line.points)
            out.append((*p[:, :2].min(axis=0), *p[:, :2].max(axis=0)))
    return out


def tick_side(axis, level: str = "major") -> tuple[float, float]:
    """How far the first tick of a level reaches below and above (left and right of) its
    axis line."""
    tick = np.asarray((axis.ticks if level == "major" else axis.minor_ticks)[0].points)
    i = 1 - axis.index
    middle = float(np.asarray(axis.line.points)[:, i].mean())
    return middle - float(tick[:, i].min()), float(tick[:, i].max()) - middle


# --- TH-1 -----------------------------------------------------------------------------


def test_th1_the_manim_theme_changes_nothing():
    plain, themed = axes(), axes(theme="manim")
    assert leaves(plain) == leaves(themed)
    assert plain.theme == themed.theme == mp.THEMES["manim"]


# --- TH-2, TH-3 -----------------------------------------------------------------------


@pytest.mark.parametrize("name", ["origin", "base", "paper", "lab"])
def test_th3_border_themes_put_the_axes_on_a_box(name):
    ax = axes(theme=name)
    left, bottom, rightmost, topmost = border(ax)
    assert line_y(ax.x_axis) == pytest.approx(bottom, abs=1e-9)
    assert line_x(ax.y_axis) == pytest.approx(left, abs=1e-9)
    boxes = lines(ax)
    assert any(abs(b[1] - topmost) < 1e-9 and abs(b[3] - topmost) < 1e-9 for b in boxes)
    assert any(
        abs(b[0] - rightmost) < 1e-9 and abs(b[2] - rightmost) < 1e-9 for b in boxes
    )
    assert ax.x_axis.tip is None and ax.y_axis.tip is None


def test_th3_origin_ticks_point_in_with_one_minor_between_majors():
    ax = axes(theme="origin")
    for level in ("major", "minor"):
        below, above = tick_side(ax.x_axis, level)
        assert above > 0 and below == pytest.approx(0, abs=1e-9)
        left, right = tick_side(ax.y_axis, level)
        assert right > 0 and left == pytest.approx(0, abs=1e-9)
    assert len(ax.x_axis.minor_ticks) == len(ax.x_axis.ticks) - 1
    assert len(ax.x_axis.grid) == 0


def test_th3_base_adds_the_faint_major_grid():
    ax = axes(theme="base")
    assert len(ax.x_axis.grid) > 0
    line = ax.x_axis.grid[0]
    assert line.get_stroke_opacity() == pytest.approx(0.35)
    assert line.get_stroke_width() == pytest.approx(1)


def test_th3_paper_ticks_point_in_and_styles_cycle():
    ax = axes(theme="paper")
    below, above = tick_side(ax.x_axis)
    assert above > 0 and below == pytest.approx(0, abs=1e-9)
    plots = [ax.plot(lambda x, k=k: x / 4 + k) for k in range(4)]
    assert [p.line_style for p in plots] == [
        mp.LineStyle.SOLID,
        mp.LineStyle.DASHED,
        mp.LineStyle.DOTTED,
        mp.LineStyle.SOLID,
    ]
    assert hexes(p.get_color() for p in plots) == HEX["gray"].split()


def test_th3_lab_has_four_minor_ticks_and_both_grids():
    ax = axes(theme="lab")
    assert len(ax.x_axis.minor_ticks) == 4 * (len(ax.x_axis.ticks) - 1)
    assert len(ax.x_axis.grid) > len(ax.x_axis.ticks)
    assert hexes([ax.plot(np.sin).get_color()]) == HEX["colorblind"].split()[:1]


def test_th2_a_constructor_argument_wins():
    ax = axes(theme="origin", tips=True)
    assert ax.x_axis.tip is not None


def test_th2_a_later_call_wins():
    ax = axes(theme="origin")
    ax.x_axis.set_position("origin")
    assert line_y(ax.x_axis) == pytest.approx(float(ax.c2p(0, 0)[1]), abs=1e-9)
    ax.x_axis.set_tick_style(direction=mp.TickDirection.BOTH)
    below, above = tick_side(ax.x_axis)
    assert below > 0 and above > 0


# --- TH-4, TH-5 -----------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(HEX))
def test_th4_cycles_are_exact(name):
    assert hexes(mp.CYCLES[name]) == HEX[name].split()


def test_th4_the_manim_cycle_is_todays():
    assert hexes(mp.CYCLES["manim"]) == hexes(mp.COLOR_CYCLE)


def test_th5_a_cycle_by_name_or_as_colours():
    ax = axes(cycle="fire")
    assert hexes([ax.plot(np.sin).get_color()]) == ["#8B0800"]
    own = axes(cycle=["#123456", "#654321"])
    colours = [own.plot(np.sin).get_color() for _ in range(3)]
    assert hexes(colours) == ["#123456", "#654321", "#123456"]


def test_th5_the_cycle_wins_over_the_theme():
    ax = axes(theme="lab", cycle="fire")
    assert hexes([ax.plot(np.sin).get_color()]) == ["#8B0800"]


# --- TH-6, TH-7 -----------------------------------------------------------------------


def test_th6_a_derived_theme_and_a_dict():
    grid = dataclasses.replace(mp.THEMES["origin"], grid=("major",))
    assert len(axes(theme=grid).x_axis.grid) > 0
    ax = axes(theme={"name": "mine", "position": "border", "tips": False})
    assert ax.x_axis.tip is None
    assert ax.theme.name == "mine"


@pytest.mark.parametrize(
    ("kwargs", "name"),
    [
        ({"theme": "nope"}, "nope"),
        ({"cycle": "nope"}, "nope"),
        ({"theme": {"name": "x", "colour": 1}}, "colour"),
    ],
)
def test_th6_unknown_names_raise(kwargs, name):
    with pytest.raises(ValueError, match=name):
        axes(**kwargs)


def test_th7_a_module_default():
    try:
        mp.set_theme("origin")
        assert mp.get_theme() == mp.THEMES["origin"]
        assert axes().x_axis.tip is None
        assert axes(theme="manim").x_axis.tip is not None
        mp.set_theme(None)
        assert mp.get_theme() == mp.THEMES["manim"]
        assert axes().x_axis.tip is not None
    finally:
        mp.set_theme(None)


# --- TH-8 to TH-10 --------------------------------------------------------------------


def test_th8_a_twin_takes_its_parents_theme():
    ax = axes(theme="origin")
    twin = ax.twinx(y_range=(0, 1))
    assert twin.y_axis.tip is None
    first = ax.plot(np.sin)
    second = twin.plot(np.cos)
    assert hexes([first.get_color(), second.get_color()]) == HEX["origin"].split()[:2]


def test_th9_a_framed_legend_follows_its_axes():
    ax = axes()
    # The registry holds artists weakly (task 11b): keep them alive.
    curve = ax.plot(np.sin, label="sin")
    legend = ax.legend(frame=True)
    assert legend.frame is not None
    entry = legend.entries[0]
    assert entry.artist is curve
    assert legend.frame.get_left()[0] < entry.handle.get_left()[0]
    assert legend.frame.get_right()[0] > entry.label.get_right()[0]
    assert legend.frame.get_top()[1] > entry.label.get_top()[1]
    before = np.array(legend.frame.get_center(), copy=True)
    ax.shift(UP)
    np.testing.assert_allclose(legend.frame.get_center(), before + UP, atol=1e-9)
    plain = axes()
    kept = plain.plot(np.cos, label="cos")
    assert plain.legend().frame is None and kept in plain.artists


def test_th9_the_theme_places_and_frames_the_legend():
    ax = axes(theme="origin")
    curve = ax.plot(np.sin, label="sin")
    legend = ax.legend()
    assert legend.frame is not None and legend.entries[0].artist is curve
    assert legend.get_left()[0] < ax.get_center()[0]  # upper left


def test_th10_a_plane_takes_the_cycle_and_keeps_its_grid():
    plain, themed = mp.NumberPlane(), mp.NumberPlane(theme="base")
    assert len(themed.background_lines) == len(plain.background_lines)
    assert hexes([themed.plot(np.sin).get_color()]) == HEX["origin"].split()[:1]


# --- TH-11 ----------------------------------------------------------------------------


def inward(axis, side: str, level: str = "major") -> bool:
    """Whether the ticks of an axis on `side` reach only toward the data rectangle."""
    low, high = tick_side(axis, level)
    if side in ("bottom", "left"):
        return high > 0 and low == pytest.approx(0, abs=1e-9)
    return low > 0 and high == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize(
    ("name", "side"), [("x", "bottom"), ("x", "top"), ("y", "left"), ("y", "right")]
)
def test_th11_an_axis_placed_at_a_border_points_its_ticks_in(name, side):
    ax = axes()
    axis = getattr(ax, name)
    axis.set_position(side)
    assert inward(axis, side)


def test_th11_an_offset_axis_points_its_ticks_in():
    ax = axes()
    ax.y.set_position("left", offset=0.5)
    assert inward(ax.y, "left")


def test_th11_a_mirror_and_a_twin_point_their_ticks_in():
    ax = axes()
    ax.x.set_position("bottom")
    ax.y.set_position("left")
    top, right = ax.x.mirror(), ax.y.mirror()
    assert inward(top, "top") and inward(right, "right")
    first = ax.twinx(y_range=(0, 1, 0.25))
    second = ax.twinx(y_range=(0, 100, 25))
    assert inward(first.y_axis, "right") and inward(second.y_axis, "right")
    twin = ax.twiny(x_range=(0, 5, 1))
    assert inward(twin.x_axis, "top")


def test_th11_axes_through_the_data_keep_manims_ticks():
    for ax in (axes(), mp.Axes(x_range=(1, 5, 1), y_range=(2, 6, 1))):
        for axis in (ax.x, ax.y):
            low, high = tick_side(axis)
            assert low == pytest.approx(high, abs=1e-9) and low > 0
    ax = axes()
    ax.x.set_position(2.0)
    ax.y.set_position("origin", fraction=0.0)
    for axis in (ax.x, ax.y):
        low, high = tick_side(axis)
        assert low == pytest.approx(high, abs=1e-9)


def test_th11_a_set_direction_wins_also_over_a_later_position():
    ax = axes()
    ax.x.set_ticks_direction(mp.TickDirection.OUT)
    ax.x.set_position("bottom")
    below, above = tick_side(ax.x)
    assert below > 0 and above == pytest.approx(0, abs=1e-9)
    ax.y.set_position("left")
    ax.y.set_tick_style(direction=mp.TickDirection.BOTH)
    left, right = tick_side(ax.y)
    assert left == pytest.approx(right, abs=1e-9)


def test_th11_a_themes_direction_wins_and_none_is_the_rule():
    assert all(theme.tick_direction is None for theme in mp.THEMES.values())
    out = dataclasses.replace(mp.THEMES["origin"], tick_direction=mp.TickDirection.OUT)
    ax = axes(theme=out)
    below, above = tick_side(ax.x_axis)
    assert below > 0 and above == pytest.approx(0, abs=1e-9)


def test_th3_the_minor_grid_style_is_a_field():
    lab = mp.THEMES["lab"]
    assert lab.minor_grid_style == {"stroke_opacity": 0.15, "stroke_width": 0.5}
    ax = axes(theme=dataclasses.replace(lab, minor_grid_style={"stroke_opacity": 0.6}))
    minor = [line for line in ax.x_axis.grid if line.level == "minor"]
    assert minor and minor[0].get_stroke_opacity() == pytest.approx(0.6)
    assert minor[0].get_stroke_width() == pytest.approx(1)  # from grid_style
