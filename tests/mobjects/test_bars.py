"""Task 31: bars and categorical axes, rows BC, BA, GB, CA of
`docs/acceptance/31-bars.md`.

The oracles: Manim's own `BarChart` for BC, the rectangles of matplotlib's `bar`,
`barh` and `grouped_bar` written out from their documented geometry everywhere else.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import RED, BarChart, ManimColor, ValueTracker

import manim_plots as mp

from .helpers import probe


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def box(ax: Any, mob: Any) -> tuple[float, float, float, float]:
    """A bar's (x0, x1, y0, y1) in data."""
    d = data(ax, corners(mob))
    return (d[:, 0].min(), d[:, 0].max(), d[:, 1].min(), d[:, 1].max())


def fill_rgb(mob: Any) -> np.ndarray:
    return np.asarray(ManimColor(mob.get_fill_color()).to_rgb())


def text_of(mob: Any) -> str:
    return str(getattr(mob, "tex_string", None) or getattr(mob, "text", ""))


VALUES = [3.0, -1.0, 2.0, 0.0]
NAMES = ["a", "b", "c", "d"]


# --- BC -------------------------------------------------------------------------------


def test_bc1_bars_equal_manims():
    ours, theirs = (
        mp.BarChart(VALUES, bar_names=NAMES),
        BarChart(VALUES, bar_names=NAMES),
    )
    assert isinstance(ours, mp.CartesianAxes)
    assert len(ours.bars) == len(theirs.bars) == 4
    for a, b in zip(ours.bars, theirs.bars, strict=True):
        assert box(ours, a) == pytest.approx(box(ours, b), abs=1e-9)
        np.testing.assert_allclose(fill_rgb(a), fill_rgb(b), atol=1.5 / 255)


def test_bc1_names_sit_as_manims():
    ours, theirs = (
        mp.BarChart(VALUES, bar_names=NAMES),
        BarChart(VALUES, bar_names=NAMES),
    )
    assert ours.x_labels is not None
    for a, b in zip(ours.x_labels, theirs.x_axis.labels, strict=True):
        np.testing.assert_allclose(a.get_center(), b.get_center(), atol=1e-6)


def test_bc2_bars_follow_a_range_and_have_names():
    chart = mp.BarChart(VALUES, bar_names=NAMES)
    chart.set_y_range((-4, 4, 1))
    assert box(chart, chart.bars[0]) == pytest.approx((0.2, 0.8, 0, 3), abs=1e-9)
    assert chart.bars.at("c") is chart.bars[2]


def test_bc3_bar_labels_as_manims():
    ours, theirs = mp.BarChart(VALUES), BarChart(VALUES)
    a, b = ours.get_bar_labels(), theirs.get_bar_labels()
    assert [text_of(m) for m in a] == [text_of(m) for m in b]
    for x, y in zip(a, b, strict=True):
        np.testing.assert_allclose(x.get_center(), y.get_center(), atol=1e-6)


def test_bc4_change_bar_values_in_place_and_from_zero():
    chart = mp.BarChart(VALUES, y_range=(-4, 4, 1))
    first = chart.bars[3]
    chart.change_bar_values([1.0, 1.0, 1.0, 2.5])
    assert chart.bars[3] is first
    assert box(chart, first)[3] == pytest.approx(2.5, abs=1e-9)  # Manim keeps 0


def test_bc4_an_animated_change_shows_interpolated_values():
    chart = mp.BarChart([1.0, 2.0], y_range=(0, 4, 1))

    def tops() -> tuple[float, float]:
        return (box(chart, chart.bars[0])[3], box(chart, chart.bars[1])[3])

    builder: Any = chart.animate  # Manim types the builder's call as the method's None
    seen = probe(lambda s: s.play(builder.change_bar_values([3.0, 0.0])), tops)
    for a, b in seen:
        alpha = (a - 1) / 2
        assert b == pytest.approx(2 - 2 * alpha, abs=1e-6)  # one alpha for both bars
    assert tops() == pytest.approx((3, 0), abs=1e-6)  # after the play's finish


# --- BA -------------------------------------------------------------------------------


def axes(**kwargs: Any) -> Any:
    return mp.Axes(x_range=(-1, 5, 1), y_range=(-3, 5, 1), **kwargs)


def test_ba1_rectangles_in_data():
    ax = axes()
    bars = ax.bar([0, 1, 2], [3, -2, 1.5], width=0.5)
    assert isinstance(bars, mp.BarPlot)
    assert box(ax, bars[0]) == pytest.approx((-0.25, 0.25, 0, 3), abs=1e-9)
    assert box(ax, bars[1]) == pytest.approx((0.75, 1.25, -2, 0), abs=1e-9)
    edge = ax.bar([3], [2], width=0.5, align="edge", bottom=1)
    assert box(ax, edge[0]) == pytest.approx((3, 3.5, 1, 3), abs=1e-9)
    assert bars.at(1) is bars[1]


def test_ba2_horizontal_bars():
    ax = axes()
    bars = ax.barh([1, 2], [3, 1], height=0.4, left=0.5)
    assert box(ax, bars[0]) == pytest.approx((0.5, 3.5, 0.8, 1.2), abs=1e-9)


def test_ba3_stacking_by_bottom():
    ax = axes()
    low = ax.bar([0, 1], [1, 2])
    high = ax.bar([0, 1], [2, 1], bottom=[1, 2])
    assert box(ax, high[0])[2] == pytest.approx(box(ax, low[0])[3])
    assert box(ax, high[1]) == pytest.approx((0.6, 1.4, 2, 3), abs=1e-9)


def test_ba4_one_cycle_colour_or_colour_by_value():
    ax = axes()
    plain = ax.bar([0, 1], [1, 2])
    assert fill_rgb(plain[0]) == pytest.approx(fill_rgb(plain[1]))
    assert plain[0].get_fill_opacity() == pytest.approx(1)
    assert plain[0].get_stroke_width() == pytest.approx(0)
    valued = ax.bar([0, 1, 2], [1, 2, 3], c="height")
    viridis = mp.colormaps["viridis"]
    for bar, t in zip(valued, (0, 0.5, 1), strict=True):
        np.testing.assert_allclose(fill_rgb(bar), viridis(t), atol=1.5 / 255)
    mapping = valued.color_mapping
    assert mapping is not None
    assert (mapping.vmin, mapping.vmax) == pytest.approx((1, 3))
    assert tuple(ax.colorbar(valued).y_range[:2]) == pytest.approx((1, 3))
    own = ax.bar([0, 1], [1, 2], c=[10, 20], colorscale="plasma", vmin=0, vmax=20)
    np.testing.assert_allclose(fill_rgb(own[0]), mp.colormaps["plasma"](0.5), atol=0.01)


def test_ba5_bars_follow_ranges_data_and_trackers():
    ax = axes()
    bars = ax.bar([0, 1], [1, 2])
    first = bars[0]
    ax.set_y_range((-6, 6, 1))
    assert box(ax, first)[3] == pytest.approx(1, abs=1e-9)
    bars.set_data(x=[0, 1], height=[4, 0.5])
    assert bars[0] is first
    assert box(ax, first)[3] == pytest.approx(4, abs=1e-9)
    top = ValueTracker(1)
    live = ax.bar([3], [top])

    def gap() -> float:
        return float(abs(box(ax, live[0])[3] - top.get_value()))

    def construct(scene: Any) -> None:
        scene.add(ax, live)
        scene.play(top.animate.set_value(3))

    assert max(probe(construct, gap)) < 1e-9


def test_ba5_a_bar_is_cut_at_the_viewport():
    ax = axes()
    tall = ax.bar([0], [9])
    assert box(ax, tall[0])[3] == pytest.approx(5, abs=1e-6)


def test_ba5_log_axis_bottom_starts_at_the_edge():
    ax = mp.Axes(x_range=(0, 3, 1), y_range=(1, 1000), y_scale="log")
    bars = ax.bar([1], [100])
    assert box(ax, bars[0])[2] == pytest.approx(1, rel=1e-9)


def test_ba6_style_kept_and_a_legend_entry():
    ax = axes()
    bars = ax.bar([0, 1], [1, 2], label="sales")
    bars[1].set_fill(RED)
    ax.set_y_range((-6, 6, 1))
    np.testing.assert_allclose(fill_rgb(bars[1]), ManimColor(RED).to_rgb(), atol=1e-6)
    legend = ax.legend()
    assert len(legend.entries) == 1


def test_ba7_bar_labels_at_the_ends():
    ax = axes()
    bars = ax.bar([0, 1], [3, -2])
    labels = ax.bar_label(bars)
    assert [text_of(m) for m in labels] == ["3", "-2"]
    assert labels[0].get_bottom()[1] == pytest.approx(ax.c2p(0, 3)[1] + 0.1, abs=1e-6)
    assert labels[1].get_top()[1] == pytest.approx(ax.c2p(0, -2)[1] - 0.1, abs=1e-6)
    centred = ax.bar_label(bars, label_type="center", fmt="{:.1f}")
    assert text_of(centred[0]) == "3.0"
    np.testing.assert_allclose(centred[0].get_center(), ax.c2p(0, 1.5), atol=1e-6)
    bars.set_data(x=[0, 1], height=[4, -2])
    assert labels[0].get_bottom()[1] == pytest.approx(ax.c2p(0, 4)[1] + 0.1, abs=1e-6)


# --- GB -------------------------------------------------------------------------------


def test_gb1_matplotlibs_geometry():
    ax = axes()
    group = ax.grouped_bar([[1, 2, 3], [2, 1, 0.5]], labels=["A", "B"])
    assert isinstance(group, mp.GroupedBarPlot)
    m, gs, bs = 2, 1.5, 0.0
    w = 1 / (m + (m - 1) * bs + gs)
    big_w = m * w + (m - 1) * bs * w
    for j, plot in enumerate(group.bar_plots):
        for k in range(3):
            centre = k - big_w / 2 + w / 2 + j * w * (1 + bs)
            x0, x1, _, _ = box(ax, plot[k])
            assert (x0 + x1) / 2 == pytest.approx(centre, abs=1e-9)
            assert x1 - x0 == pytest.approx(w, abs=1e-9)


def test_gb2_labels_colours_and_categories():
    ax = axes()
    group = ax.grouped_bar({"A": [1, 2], "B": [2, 1]}, tick_labels=["x", "y"])
    a, b = group.bar_plots
    assert fill_rgb(a[0]) != pytest.approx(fill_rgb(b[0]))
    assert ax.x.categories == ("x", "y")
    assert len(ax.legend().entries) == 2  # the dict's keys are the labels
    flat = axes()  # ax's x axis is categorical now: (-0.5, 1.5)
    side = flat.grouped_bar([[1, 2]], orientation="horizontal")
    x0, x1, _, _ = box(flat, side.bar_plots[0][1])
    assert (x0, x1) == pytest.approx((0, 2), abs=1e-9)


# --- CA -------------------------------------------------------------------------------


def test_ca1_ca2_strings_make_the_axis_categorical():
    ax = mp.Axes()
    bars = ax.bar(["apples", "pears", "plums"], [3, 1, 2])
    assert ax.x.categories == ("apples", "pears", "plums")
    assert tuple(ax.x_range[:2]) == pytest.approx((-0.5, 2.5))
    assert box(ax, bars.at("pears"))[:2] == pytest.approx((0.6, 1.4), abs=1e-9)
    assert len(ax.x.ticks) == 3
    for k in range(3):
        np.testing.assert_allclose(
            ax.x.ticks.at(float(k)).get_center()[0], ax.c2p(k, 0)[0], atol=1e-9
        )
    assert text_of(ax.x.numbers.at(1.0)) == "pears"
    ax.bar(["figs"], [1])
    assert str(ax.x.categories[-1]) == "figs"  # str(): mypy keeps the narrowed tuple
    assert tuple(ax.x_range[:2]) == pytest.approx((-0.5, 3.5))


def test_ca2_fixed_categories_refuse_new_names():
    ax = mp.Axes()
    ax.x.set_categories(["a", "b"])
    with pytest.raises(ValueError, match="x"):
        ax.bar(["c"], [1])


def test_ca4_the_other_axis_moves_to_the_low_border():
    ax = mp.Axes(x_range=(0, 10, 2))
    ax.barh(["tea", "coffee"], [2, 4])
    line = np.array([ax.p2c(p) for p in ax.x.line.points])
    np.testing.assert_allclose(line[:, 1], -0.5, atol=1e-9)
    bars = mp.Axes(y_range=(0, 5, 1))
    bars.y.set_position(0.5)
    bars.bar(["a", "b"], [1, 2])
    line = np.array([bars.p2c(p) for p in bars.y.line.points])
    np.testing.assert_allclose(line[:, 0], 0.5, atol=1e-9)  # the user's position kept
    plain = mp.Axes(y_range=(0, 5, 1))
    plain.bar(["a", "b"], [1, 2])
    line = np.array([plain.p2c(p) for p in plain.y.line.points])
    np.testing.assert_allclose(line[:, 0], -0.5, atol=1e-9)


def test_ca3_other_artists_and_c2p_use_the_table():
    ax = mp.Axes()
    ax.bar(["a", "b", "c"], [1, 2, 3])
    dots = ax.scatter(["a", "c"], [1, 2])
    np.testing.assert_allclose(dots[1].get_center(), ax.c2p(2, 2), atol=1e-9)
    np.testing.assert_allclose(ax.c2p("b", 0), ax.c2p(1, 0), atol=1e-12)
