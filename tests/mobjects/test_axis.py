"""The library's own axis capabilities (F-406, F-408, F-412, F-413, F-505-F-508,
F-603-F-608).

Rows LB-1 to LB-6, DP-1 to DP-5, LL-1 and LL-2 of
`docs/acceptance/10-axis-decoration.md`. Manim has none of these, so the oracles are
geometry computed here from `c2p` and the axis line, and object identity.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
from manim import RED, tempconfig

import manim_plots as mp
from manim_plots import FixedLocator, MaxNLocator, MultipleLocator
from manim_plots.mobjects.axis import TickDirection

from .helpers import RUN


def axes(**kwargs):
    with tempconfig(RUN):
        return mp.Axes(
            x_range=(0, 10, 1), y_range=(-2, 2, 1), x_length=10, y_length=4, **kwargs
        )


def tick_values(ax, axis="x", level="ticks"):
    group = getattr(getattr(ax, f"{axis}_axis"), level)
    index = 0 if axis == "x" else 1
    return sorted(round(float(ax.p2c(t.get_center())[index]), 9) for t in group)


# --- LB -------------------------------------------------------------------------------


def test_lb1_a_locator_regenerates_the_ticks():
    ax = axes()
    ax.x.set_locator(MultipleLocator(2.5))
    assert tick_values(ax) == [2.5, 5.0, 7.5]  # 10 is under the tip, as in Manim


def test_lb1_a_plain_callable_is_a_locator():
    ax = axes()
    ax.x.set_locator(lambda lo, hi: [1.0, 4.0])
    assert tick_values(ax) == [1.0, 4.0]


def test_lb1_set_ticks_replaces_or_adds():
    ax = axes()
    ax.x.set_ticks([(2.5, "a"), 7.0])
    assert tick_values(ax) == [2.5, 7.0]
    ax2 = axes()
    ax2.x.set_ticks([(2.5, "a")], mode="add")
    assert 2.5 in tick_values(ax2) and 3.0 in tick_values(ax2)


def test_lb1_a_minor_locator():
    ax = axes()
    ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))
    assert tick_values(ax, level="minor_ticks") == [1.0, 3.0, 5.0, 7.0, 9.0]


def test_lb1_only_the_affected_parts_change():
    ax = axes()
    y_ticks = list(ax.y_axis.ticks)
    ax.x.set_locator(MultipleLocator(5))
    assert list(ax.y_axis.ticks) == y_ticks


def test_lb2_parts_are_addressable_by_value():
    ax = axes(axis_config={"include_numbers": True})
    tick = ax.x_axis.ticks.at(3.0)
    assert math.isclose(ax.p2c(tick.get_center())[0], 3.0, abs_tol=1e-9)
    number = ax.x_axis.numbers.at(3.0)
    assert abs(number.get_center()[0] - tick.get_center()[0]) < 1e-6
    with pytest.raises(KeyError):
        ax.x_axis.ticks.at(3.5)


def test_lb3_a_part_keeps_its_object_while_its_key_stays_in_range():
    ax = axes(axis_config={"include_numbers": True})
    number = ax.x.numbers.at(2.0)
    number.set_color(RED)
    ax.x.range = (0, 6)
    assert ax.x.numbers.at(2.0) is number
    assert number.get_color() == RED


def test_lb4_a_new_formatter_relabels_the_same_objects():
    ax = axes(axis_config={"include_numbers": True})
    number = ax.x.numbers.at(2.0)
    ax.x.set_formatter(lambda v: f"{v:g} m")
    assert ax.x.numbers.at(2.0) is number


def test_lb5_label_space_bounds_a_density_aware_locator():
    with tempconfig(RUN):
        narrow = mp.Axes(x_range=(0, 100, 10), x_length=2)
        wide = mp.Axes(x_range=(0, 100, 10), x_length=12)
    narrow.x.set_locator(MaxNLocator())
    wide.x.set_locator(MaxNLocator())
    assert len(narrow.x_axis.ticks) < len(wide.x_axis.ticks)


def test_lb6_no_label_outside_the_range():
    ax = axes(axis_config={"include_numbers": True})
    ax.x.set_ticks([(-1.0, "out"), (5.0, "in"), (11.0, "out")])
    assert len(ax.x_axis.numbers) == 1


# --- DP -------------------------------------------------------------------------------


def tick_extent(ax, value):
    tick = ax.x_axis.ticks.at(value)
    line_y = ax.x_axis.line.get_center()[1]
    ys = tick.points[:, 1]
    return ys.min() - line_y, ys.max() - line_y


def test_dp1_both_out_and_in():
    ax = axes()
    lo, hi = tick_extent(ax, 3.0)
    assert math.isclose(lo, -hi, abs_tol=1e-9)
    ax.x.set_position("bottom")
    ax.x.set_tick_style(direction=TickDirection.OUT, length=0.3)
    lo, hi = tick_extent(ax, 3.0)
    assert math.isclose(hi, 0, abs_tol=1e-9) and math.isclose(lo, -0.3, abs_tol=1e-9)
    ax.x.set_tick_style(direction=TickDirection.IN)
    lo, hi = tick_extent(ax, 3.0)
    assert math.isclose(lo, 0, abs_tol=1e-9) and hi > 0


def test_dp1_style_per_level():
    ax = axes()
    ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))
    ax.x.set_tick_style("minor", width=1, color=RED)
    minor = ax.x_axis.minor_ticks.at(1.0)
    assert minor.get_stroke_width() == 1
    assert ax.x_axis.ticks.at(2.0).get_stroke_width() != 1
    major_length = np.ptp(ax.x_axis.ticks.at(2.0).points[:, 1])
    assert math.isclose(np.ptp(minor.points[:, 1]), major_length / 2, rel_tol=1e-9)


@pytest.mark.parametrize(
    "where, expected",
    [("origin", 0.0), ("bottom", -2.0), ("top", 2.0), (1.5, 1.5)],
    ids=str,
)
def test_dp2_axis_position(where, expected):
    ax = axes()
    before = ax.c2p(3, 1).copy()
    ax.x.set_position(where)
    assert math.isclose(
        ax.x_axis.line.get_center()[1], ax.c2p(0, expected)[1], abs_tol=1e-9
    )
    np.testing.assert_allclose(ax.c2p(3, 1), before)


def test_dp2_a_fractional_position():
    ax = axes()
    ax.x.set_position(fraction=0.25)
    assert math.isclose(ax.x_axis.line.get_center()[1], ax.c2p(0, -1)[1], abs_tol=1e-9)


def test_dp2_an_axis_whose_range_excludes_zero_sits_at_the_edge():
    with tempconfig(RUN):
        ax = mp.Axes(x_range=(2, 8, 1), y_range=(1, 5, 1))
    assert math.isclose(ax.y_axis.line.get_center()[0], ax.c2p(2, 3)[0], abs_tol=1e-9)
    assert math.isclose(ax.x_axis.line.get_center()[1], ax.c2p(5, 1)[1], abs_tol=1e-9)


def test_dp3_tips_at_either_end_change_no_mapping():
    ax = axes()
    before = ax.c2p(7, 1).copy()
    ticks = tick_values(ax)
    ax.x.set_tips(start=True, end=True)
    assert ax.x_axis.tip is not None and ax.x_axis.tip_start is not None
    np.testing.assert_allclose(ax.c2p(7, 1), before)
    assert tick_values(ax) == ticks


def test_dp3_the_tick_under_a_tip_is_left_out_unless_asked_for():
    # As in Manim: an end with a tip has no tick and no number; without a tip it has.
    ax = axes(axis_config={"include_numbers": True})
    assert tick_values(ax)[-1] == 9
    assert max(ax.p2c(n.get_center())[0] for n in ax.x_axis.numbers) < 9.5
    ax.x.set_tips(end=True, tick_under_tip=True)
    assert tick_values(ax)[-1] == 10
    assert max(ax.p2c(n.get_center())[0] for n in ax.x_axis.numbers) > 9.5
    ax.x.set_tips(end=True)
    assert tick_values(ax)[-1] == 9
    assert tick_values(axes(tips=False))[-1] == 10
    with pytest.raises(TypeError):
        ax.x.set_tips(tick_under_tip=1)


def test_dp4_a_mirrored_axis_is_unlabelled_on_the_other_side():
    ax = axes(axis_config={"include_numbers": True})
    ax.x.set_position("bottom")
    top = ax.x.mirror()
    assert math.isclose(top.line.get_center()[1], ax.c2p(0, 2)[1], abs_tol=1e-9)
    assert len(top.numbers) == 0
    assert len(top.ticks) == len(ax.x_axis.ticks)
    ax.x.range = (0, 5)
    assert len(top.ticks) == len(ax.x_axis.ticks)


def test_dp5_grid_per_level():
    ax = axes()
    assert len(ax.x_axis.grid) == 0
    ax.x.set_locator(MultipleLocator(2), minor=MultipleLocator(1))
    ax.x.set_grid("major", stroke_width=1)
    ax.x.set_grid("minor", stroke_opacity=0.3)
    majors = [m for m in ax.x_axis.grid if m.level == "major"]
    minors = [m for m in ax.x_axis.grid if m.level == "minor"]
    assert len(majors) == 5 and len(minors) == 5
    line = majors[0]
    ys = line.points[:, 1]
    assert math.isclose(ys.min(), ax.c2p(0, -2)[1], abs_tol=1e-9)
    assert math.isclose(ys.max(), ax.c2p(0, 2)[1], abs_tol=1e-9)


# --- LL -------------------------------------------------------------------------------


def boxes(numbers):
    return [
        (n.get_left()[0], n.get_right()[0]) for n in numbers if n.get_fill_opacity() > 0
    ]


def overlapping(intervals) -> bool:
    intervals = sorted(intervals)
    return any(b[0] < a[1] for a, b in itertools.pairwise(intervals))


def dense_axes():
    with tempconfig(RUN):
        return mp.Axes(
            x_range=(0, 1000, 50), x_length=6, axis_config={"include_numbers": True}
        )


def test_ll1_hide_is_the_default_and_leaves_no_overlap():
    ax = dense_axes()
    visible = boxes(ax.x_axis.numbers)
    assert not overlapping(visible)
    assert len(visible) < len(ax.x_axis.numbers)


def test_ll1_drop_removes_labels_until_none_overlap():
    ax = dense_axes()
    ax.x.set_label_style(overlap="drop")
    assert not overlapping(boxes(ax.x_axis.numbers))


def test_ll1_rotate_turns_the_labels_and_shows_at_least_as_many():
    hidden = len(boxes(dense_axes().x_axis.numbers))
    ax = dense_axes()
    ax.x.set_label_style(overlap="rotate")
    assert not overlapping(boxes(ax.x_axis.numbers))
    assert len(boxes(ax.x_axis.numbers)) >= hidden


def test_ll2_rotation_offset_and_justification():
    ax = axes(axis_config={"include_numbers": True})
    tick = ax.x_axis.ticks.at(3.0).get_center()
    ax.x.set_label_style(justify="left")
    assert math.isclose(ax.x.numbers.at(3.0).get_left()[0], tick[0], abs_tol=1e-6)
    ax.x.set_label_style(justify="center", offset=(0.5, 0.0))
    assert math.isclose(
        ax.x.numbers.at(3.0).get_center()[0], tick[0] + 0.5, abs_tol=1e-6
    )
    width = ax.x.numbers.at(3.0).width
    ax.x.set_label_style(rotation=math.pi / 2)
    assert math.isclose(ax.x.numbers.at(3.0).height, width, rel_tol=1e-6)


def test_fixed_entries_carry_their_labels():
    ax = axes(axis_config={"include_numbers": True})
    ax.x.set_locator(FixedLocator([(2.0, r"\alpha"), (5.0, None)]))
    assert len(ax.x_axis.numbers) == 2
