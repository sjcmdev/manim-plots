"""`mp.Axes(...)` against Manim's own `Axes(...)`: the defaults table (D23, F-1009).

Rows AC-1 to AC-7, AC-9 and AC-10 of `docs/acceptance/10-axis-decoration.md`. The oracle
of every comparison is Manim's `Axes`, built with the same arguments in the same test;
the one difference asserted is the defaults table's fix, the tick under a tip.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
from manim import RED, UP, Axes, tempconfig

import manim_plots as mp
from manim_plots.core.scales import LogScale, SymLogScale
from manim_plots.mobjects.leaves import Leaf

from .helpers import RUN

ATOL = 1e-6

CASES: dict[str, dict[str, Any]] = {
    "default": {},
    "numbers": {"axis_config": {"include_numbers": True}},
    "even steps": {"x_range": (0, 10, 2), "axis_config": {"include_numbers": True}},
    "two places": {
        "axis_config": {
            "include_numbers": True,
            "decimal_number_config": {"num_decimal_places": 2},
        }
    },
    "font size": {"axis_config": {"include_numbers": True, "font_size": 24}},
    "label up": {"x_axis_config": {"include_numbers": True, "label_direction": UP}},
    "tick size": {"axis_config": {"tick_size": 0.2}},
    "elongated": {
        "axis_config": {"numbers_with_elongated_ticks": [2], "longer_tick_multiple": 3}
    },
    "no ticks": {"axis_config": {"include_ticks": False}},
    "include": {"axis_config": {"include_numbers": True, "numbers_to_include": [1, 3]}},
    "exclude": {"axis_config": {"include_numbers": True, "numbers_to_exclude": [2]}},
    "stroke": {"axis_config": {"stroke_width": 4}},
    "colour": {"axis_config": {"color": RED}},
    "no tips": {"tips": False},
}


def same_points(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and np.allclose(a, b, rtol=0, atol=ATOL)


def leaves(mob) -> list[Any]:
    return [m for m in mob.get_family() if m.has_points()]


def assert_style(ours, theirs) -> None:
    assert ours.get_stroke_width() == pytest.approx(theirs.get_stroke_width())
    assert ours.get_stroke_opacity() == pytest.approx(theirs.get_stroke_opacity())
    assert ours.get_fill_opacity() == pytest.approx(theirs.get_fill_opacity())
    if theirs.get_stroke_opacity() > 0 and theirs.get_stroke_width() > 0:
        assert ours.get_stroke_color() == theirs.get_stroke_color()
    if theirs.get_fill_opacity() > 0:
        assert ours.get_fill_color() == theirs.get_fill_color()


def assert_axis_matches(mine, manim_axis, *, tip: bool) -> None:
    np.testing.assert_allclose(mine.line.points, manim_axis.points, rtol=0, atol=ATOL)
    assert_style(mine.line, manim_axis)
    manim_ticks = list(getattr(manim_axis, "ticks", []))
    for tick in manim_ticks:
        match = [t for t in mine.ticks if same_points(t.points, tick.points)]
        assert match, f"no tick at {tick.get_center()}"
        assert_style(match[0], tick)
    if manim_ticks:
        assert len(mine.ticks) == len(manim_ticks) + (1 if tip else 0)
    if tip:
        np.testing.assert_allclose(
            mine.tip.points, manim_axis.tip.points, rtol=0, atol=ATOL
        )
        assert_style(mine.tip, manim_axis.tip)
    manim_numbers = list(getattr(manim_axis, "numbers", []))
    # Manim's numbers are all there; the one extra is under the tip, kept with its
    # tick (F-411), and only when the numbers follow the ticks.
    unmatched = [
        n
        for n in mine.numbers
        if not any(
            np.allclose(n.get_center(), t.get_center(), rtol=0, atol=ATOL)
            for t in manim_numbers
        )
    ]
    assert len(unmatched) <= (1 if tip else 0)
    for extra in unmatched:
        assert np.linalg.norm(extra.get_center() - mine.line.get_end()) < 1.0
    for theirs in manim_numbers:
        match = [
            n
            for n in mine.numbers
            if np.allclose(n.get_center(), theirs.get_center(), rtol=0, atol=ATOL)
        ]
        assert match, f"no number at {theirs.get_center()}"
        ours = match[0]
        our_glyphs, their_glyphs = leaves(ours), leaves(theirs)
        assert len(our_glyphs) == len(their_glyphs)
        for g, h in zip(our_glyphs, their_glyphs, strict=True):
            np.testing.assert_allclose(g.points, h.points, rtol=0, atol=ATOL)
            assert_style(g, h)
            assert isinstance(g, Leaf)


@pytest.mark.parametrize("name", list(CASES))
def test_ac4_every_default_row_matches_manims_axes(name):
    case = CASES[name]
    with tempconfig(RUN):
        ours, theirs = mp.Axes(**case), Axes(**case)
    tip = case.get("tips", True)
    assert_axis_matches(ours.x_axis, theirs.x_axis, tip=tip)
    assert_axis_matches(ours.y_axis, theirs.y_axis, tip=tip)
    np.testing.assert_allclose(ours.c2p(1, 1), theirs.c2p(1, 1), atol=1e-9)


def test_ac3_under_another_frame_the_ranges_follow_and_the_lengths_do_not():
    with tempconfig(RUN | {"frame_width": 10, "frame_height": 6}):
        ours, theirs = mp.Axes(), Axes()
    np.testing.assert_array_equal(ours.x.range.value, theirs.x_range[:2])
    np.testing.assert_array_equal(ours.y.range.value, theirs.y_range[:2])
    assert_axis_matches(ours.x_axis, theirs.x_axis, tip=True)
    assert_axis_matches(ours.y_axis, theirs.y_axis, tip=True)


def test_ac1_axis_config_then_the_per_axis_config_win():
    with tempconfig(RUN):
        case: dict[str, Any] = {
            "axis_config": {"stroke_width": 5},
            "y_axis_config": {"stroke_width": 1},
        }
        ours, theirs = mp.Axes(**case), Axes(**case)
    assert ours.x_axis.line.get_stroke_width() == theirs.x_axis.get_stroke_width() == 5
    assert ours.y_axis.line.get_stroke_width() == theirs.y_axis.get_stroke_width() == 1


@pytest.mark.parametrize(
    "key", ["rotation", "length", "numbers_font", "label_constructor", "bogus"]
)
def test_ac2_an_unknown_axis_config_key_raises_naming_it(key):
    with pytest.raises(ValueError, match=key):
        mp.Axes(axis_config={key: 1})


def test_ac2_the_per_axis_configs_are_checked_too():
    with pytest.raises(ValueError, match="bogus"):
        mp.Axes(x_axis_config={"bogus": 1})


def test_ac6_a_scientific_step_counts_its_exponent():
    # Manim prints 0 decimal places for a step of 1e-05; the fix prints 5.
    with tempconfig(RUN):
        ax = mp.Axes(x_range=(0, 5e-5, 1e-5), axis_config={"include_numbers": True})
    labels = ax.x_axis.formatter.format_ticks(np.array([1e-5, 2e-5])).text
    assert list(labels) == ["0.00001", "0.00002"]


def test_ac7_unit_size_wins_over_the_default_length():
    # Without tips: Manim shortens a line by its tip.
    ax = mp.Axes(x_range=(0, 4, 1), axis_config={"unit_size": 2}, tips=False)
    assert math.isclose(np.ptp(ax.x_axis.line.points[:, 0]), 8.0)


def test_ac7_unit_size_with_an_explicit_length_raises():
    with pytest.raises(ValueError, match="unit_size"):
        mp.Axes(x_range=(0, 4, 1), x_length=5, axis_config={"unit_size": 2})


def test_ac9_a_named_scale_takes_data_ranges():
    ax = mp.Axes(x_range=(0.1, 1000), x_scale="log")
    assert isinstance(ax.x.get_scale(), LogScale)
    np.testing.assert_allclose(ax.p2c(ax.c2p(10, 0))[0], 10)
    major = [ax.p2c(t.get_center())[0] for t in ax.x_axis.ticks]
    np.testing.assert_allclose(
        sorted(major), [0.1, 1, 10, 100, 1000][: len(major)], rtol=1e-9
    )
    assert len(ax.x_axis.minor_ticks) > 0
    assert isinstance(mp.Axes(x_scale="symlog").x.get_scale(), SymLogScale)


def test_ac9_a_range_wholly_outside_the_domain_raises():
    with pytest.raises(ValueError):
        mp.Axes(x_range=(-10, -1), x_scale="log")


def test_ac10_an_aspect_lock_adapts_the_length_not_given():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 5, 1), x_length=8, aspect=1.0)
    x_unit = ax.get_x_unit_size()
    y_unit = ax.get_y_unit_size()
    assert math.isclose(y_unit, x_unit)
    np.testing.assert_array_equal(ax.y.range.value, [0, 5])


def test_ac10_adjustable_range_keeps_both_lengths():
    ax = mp.Axes(
        x_range=(0, 10, 1),
        y_range=(0, 2, 1),
        x_length=8,
        y_length=4,
        aspect=1.0,
        adjustable="range",
        tips=False,
    )
    assert math.isclose(ax.get_x_unit_size(), ax.get_y_unit_size())
    assert math.isclose(np.ptp(ax.x_axis.line.points[:, 0]), 8)
    assert math.isclose(np.ptp(ax.y_axis.line.points[:, 1]), 4)


def test_ac10_an_over_constrained_lock_raises():
    with pytest.raises(ValueError):
        mp.Axes(x_length=8, y_length=4, aspect=1.0)
    with pytest.raises(ValueError):
        mp.Axes(aspect=1.0, adjustable="box")  # type: ignore[arg-type]
