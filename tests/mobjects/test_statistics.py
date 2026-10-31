"""Task 38: statistics, rows PI, BX, VI of `docs/acceptance/38-statistics.md`.

The oracles: wedge angles from the fractions, `numpy.percentile` and matplotlib's
whisker rule written out, and a Gaussian KDE with Scott's factor computed here.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import ORIGIN, RED, ManimColor

import manim_plots as mp

D = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 30], dtype=float)


def data(ax: Any, points: Any) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(np.asarray(points))])


def text_of(mob: Any) -> str:
    return str(getattr(mob, "tex_string", None) or getattr(mob, "text", ""))


def angles(mob: Any, centre: np.ndarray) -> np.ndarray:
    d = np.asarray(mob.points)[:, :2] - centre[:2]
    far = np.linalg.norm(d, axis=1) > 1e-6
    out: np.ndarray = np.mod(np.arctan2(d[far, 1], d[far, 0]), 2 * np.pi)
    return out


# --- PI -------------------------------------------------------------------------------


def test_pi1_wedges_follow_the_fractions():
    pie = mp.PieChart([1, 2, 1], radius=2)
    assert isinstance(cast(object, pie), mp.PieChart)
    assert len(pie.wedges) == 3
    a0, a1 = angles(pie.wedges[0], ORIGIN), angles(pie.wedges[1], ORIGIN)
    assert a0.min() >= -1e-6 and a0.max() <= np.pi / 2 + 1e-6
    assert a1.min() >= np.pi / 2 - 1e-6 and a1.max() <= 3 * np.pi / 2 + 1e-6
    radii = np.linalg.norm(np.asarray(pie.wedges[1].points)[:, :2], axis=1)
    assert radii.max() == pytest.approx(2, abs=1e-6)


def test_pi1_direction_start_and_partial():
    pie = mp.PieChart([1, 2, 1], startangle=90, counterclock=False)
    ys = np.asarray(pie.wedges[1].points)[:, 1]
    assert ys.max() <= 1e-6  # 0 to -180 degrees: the lower half
    half = mp.PieChart([0.25, 0.25], normalize=False)
    span = np.concatenate([angles(w, ORIGIN) for w in half.wedges])
    assert span.max() <= np.pi + 1e-6
    with pytest.raises(ValueError, match="normalize"):
        mp.PieChart([0.8, 0.8], normalize=False)
    with pytest.raises(ValueError):
        mp.PieChart([1, -1])


def test_pi2_explode_labels_and_percentages():
    pie = mp.PieChart(
        [1, 2, 1], explode=[0, 0.1, 0], labels=["a", "b", "c"], autopct="%1.1f%%"
    )
    pts = np.asarray(pie.wedges[1].points)[:, :2]
    apex = pts[np.argmin(np.linalg.norm(pts - (-0.2, 0), axis=1))]
    np.testing.assert_allclose(apex, (-0.2, 0), atol=1e-6)  # moved 0.1 * radius 2
    assert pie.texts is not None and pie.autotexts is not None
    np.testing.assert_allclose(
        pie.texts[0].get_center()[:2],
        2.2 * np.array([np.cos(np.pi / 4)] * 2),
        atol=1e-6,
    )
    assert text_of(pie.autotexts[1]) == "50.0%"
    np.testing.assert_allclose(
        pie.autotexts[1].get_center()[:2], (-0.2 - 1.2, 0), atol=1e-6
    )
    called = mp.PieChart([1, 3], autopct=lambda p: f"{p:.0f}")
    assert called.autotexts is not None
    assert text_of(called.autotexts[1]) == "75"
    assert mp.PieChart([1, 1]).texts is None


def test_pi3_style_and_pi4_set_data():
    pie = mp.PieChart([1, 2, 1], colors=[RED, "#00ff00", "#0000ff"])
    np.testing.assert_allclose(
        ManimColor(pie.wedges[0].get_fill_color()).to_rgb(), ManimColor(RED).to_rgb()
    )
    assert pie.wedges[0].get_fill_opacity() == pytest.approx(1)
    wedge = pie.wedges[1]
    wedge.set_stroke(width=5)
    pie.set_data([1, 1, 2])
    assert pie.wedges[1] is wedge
    assert wedge.get_stroke_width() == 5
    a1 = angles(wedge, ORIGIN)
    assert a1.min() >= np.pi / 2 - 1e-6 and a1.max() <= np.pi + 1e-6


# --- BX -------------------------------------------------------------------------------


def axes() -> Any:
    return mp.Axes(x_range=(0, 4, 1), y_range=(-5, 35, 5))


def test_bx1_stats_are_matplotlibs():
    ax = axes()
    box = ax.boxplot(D)
    assert isinstance(cast(object, box), mp.BoxPlot)
    s = box.stats[0]
    assert (s["q1"], s["med"], s["q3"]) == pytest.approx((3.25, 5.5, 7.75))
    assert (s["whislo"], s["whishi"]) == pytest.approx((1, 9))
    np.testing.assert_allclose(s["fliers"], [30])
    assert s["mean"] == pytest.approx(7.5)
    wide = ax.boxplot(D, whis=(0, 100))
    assert wide.stats[0]["whishi"] == pytest.approx(30)


def test_bx2_parts_in_data():
    ax = axes()
    box = ax.boxplot(D, showmeans=True)
    b = data(ax, box.boxes[0].points)
    assert (b[:, 0].min(), b[:, 0].max()) == pytest.approx((0.75, 1.25), abs=1e-9)
    assert (b[:, 1].min(), b[:, 1].max()) == pytest.approx((3.25, 7.75), abs=1e-9)
    m = data(ax, box.medians[0].points)
    np.testing.assert_allclose(m[:, 1], 5.5, atol=1e-9)
    assert (m[:, 0].min(), m[:, 0].max()) == pytest.approx((0.75, 1.25), abs=1e-9)
    low, high = (data(ax, w.points) for w in box.whiskers[:2])
    assert sorted([low[:, 1].min(), high[:, 1].max()]) == pytest.approx([1, 9])
    np.testing.assert_allclose(np.concatenate([low[:, 0], high[:, 0]]), 1, atol=1e-9)
    for cap, y in zip(box.caps[:2], (1, 9), strict=True):
        c = data(ax, cap.points)
        np.testing.assert_allclose(c[:, 1], y, atol=1e-9)
        assert (c[:, 0].min(), c[:, 0].max()) == pytest.approx((0.875, 1.125))
    np.testing.assert_allclose(box.fliers[0][0].get_center(), ax.c2p(1, 30), atol=1e-6)
    np.testing.assert_allclose(box.means[0].get_center(), ax.c2p(1, 7.5), atol=1e-6)


def test_bx2_several_horizontal_and_bound():
    ax = mp.Axes(x_range=(-5, 35, 5), y_range=(0, 4, 1))
    box = ax.boxplot([D, D + 2], orientation="horizontal")
    b = data(ax, box.boxes[1].points)
    assert (b[:, 1].min(), b[:, 1].max()) == pytest.approx((1.75, 2.25), abs=1e-9)
    assert (b[:, 0].min(), b[:, 0].max()) == pytest.approx((5.25, 9.75), abs=1e-9)
    ax.set_x_range((0, 8, 1))
    b = data(ax, box.boxes[1].points)
    assert b[:, 0].max() == pytest.approx(8, abs=1e-9)  # cut at the viewport


def test_bx3_style_parts_and_categories():
    ax = axes()
    box = ax.boxplot([D, D * 0.5], tick_labels=["a", "b"])
    assert ax.x.categories == ("a", "b")
    b = data(ax, box.boxes[1].points)
    assert (b[:, 0].min() + b[:, 0].max()) / 2 == pytest.approx(1, abs=1e-9)
    assert box.boxes[0].get_fill_opacity() == pytest.approx(0)
    assert ManimColor(box.medians[0].get_stroke_color()) != ManimColor(
        box.boxes[0].get_stroke_color()
    )
    box.medians[0].set_stroke(RED, width=6)
    ax.set_y_range((-10, 40, 10))
    assert box.medians[0].get_stroke_width() == 6


# --- VI -------------------------------------------------------------------------------


def kde(sample: np.ndarray, at: np.ndarray, factor: float) -> np.ndarray:
    bw = factor * np.std(sample, ddof=1)
    z = (at[:, None] - sample[None, :]) / bw
    out: np.ndarray = np.exp(-0.5 * z**2).sum(axis=1) / (
        len(sample) * bw * np.sqrt(2 * np.pi)
    )
    return out


def test_vi1_vi2_body_from_the_kde():
    rng = np.random.default_rng(3)
    sample = rng.normal(0, 1, 200)
    ax = mp.Axes(x_range=(0, 2, 1), y_range=(-4, 4, 1))
    v = ax.violinplot(sample)
    assert isinstance(cast(object, v), mp.ViolinPlot)
    body = data(ax, v.bodies[0].points)
    assert body[:, 1].min() == pytest.approx(sample.min(), abs=1e-6)
    assert body[:, 1].max() == pytest.approx(sample.max(), abs=1e-6)
    factor = len(sample) ** (-1 / 5)
    grid = np.linspace(sample.min(), sample.max(), 100)
    peak = kde(sample, grid, factor).max()
    right = body[body[:, 0] > 1 + 1e-9]
    expected = 0.25 * kde(sample, right[:, 1], factor) / peak
    np.testing.assert_allclose(right[:, 0] - 1, expected, atol=1e-3)
    assert (body[:, 0].max() - 1) == pytest.approx(0.25, abs=1e-6)
    narrow = ax.violinplot(sample, bw_method=0.2)
    assert not np.allclose(data(ax, narrow.bodies[0].points), body)


def test_vi2_lines_and_vi3_style():
    rng = np.random.default_rng(4)
    sample = rng.normal(0, 1, 100)
    ax = mp.Axes(x_range=(0, 2, 1), y_range=(-4, 4, 1))
    v = ax.violinplot(sample, showmedians=True)
    bar = data(ax, v.cbars[0].points)
    np.testing.assert_allclose(bar[:, 0], 1, atol=1e-9)
    assert (bar[:, 1].min(), bar[:, 1].max()) == pytest.approx(
        (sample.min(), sample.max()), abs=1e-6
    )
    top = data(ax, v.cmaxes[0].points)
    assert (top[:, 0].min(), top[:, 0].max()) == pytest.approx((0.875, 1.125))
    med = data(ax, v.cmedians[0].points)
    np.testing.assert_allclose(med[:, 1], np.median(sample), atol=1e-9)
    assert v.cmeans is None or len(v.cmeans) == 0
    assert v.bodies[0].get_fill_opacity() == pytest.approx(0.3)
