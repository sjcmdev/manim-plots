"""Task 18: error bars in x and y.

Rows EB, ED and EL of `docs/acceptance/18-errorbar.md`. Bar ends are computed with
`c2p` in the test; caps are measured in scene units.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import DEGREES, GREEN, RED, Scene

import manim_plots as mp

from .helpers import probe

X, Y = np.array([-2.0, 0.0, 2.0]), np.array([1.0, 2.0, 1.0])


def segments(part) -> list[tuple[np.ndarray, np.ndarray]]:
    return [
        (np.asarray(p[0]), np.asarray(p[-1])) for p in part.get_subpaths() if len(p)
    ]


def length(segment) -> float:
    return float(np.linalg.norm(segment[1] - segment[0]))


def unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def none_or_empty(part) -> bool:
    return part is None or not part.has_points()


# --- EB: the artist -------------------------------------------------------------------


def test_eb1_an_errorbar_is_registered_with_markers_at_the_points():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    assert isinstance(eb, mp.ErrorBars)
    assert isinstance(eb.markers, mp.ScatterPlot)
    centres = [m.get_center() for m in eb.markers]
    np.testing.assert_allclose(centres, np.asarray(ax.c2p(X, Y)).T, atol=1e-9)


def test_eb1_pairs_as_ax_line_takes_them():
    ax = mp.Axes()
    a = ax.errorbar(list(zip(X, Y, strict=True)), yerr=0.5)
    b = ax.errorbar(X, Y, yerr=0.5)
    for (s1, e1), (s2, e2) in zip(segments(a.ybars), segments(b.ybars), strict=True):
        np.testing.assert_allclose([s1, e1], [s2, e2], atol=1e-12)


@pytest.mark.parametrize(
    ("yerr", "lower", "upper"),
    [
        (0.5, [0.5] * 3, [0.5] * 3),
        ([0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]),
        ([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], [0.1, 0.2, 0.3], [0.4, 0.5, 0.6]),
    ],
    ids=["scalar", "per-point", "asymmetric"],
)
def test_eb2_bar_ends_from_every_error_shape(yerr, lower, upper):
    ax = mp.Axes()
    bars = segments(ax.errorbar(X, Y, yerr=yerr).ybars)
    assert len(bars) == 3
    for (start, end), x, y, lo, hi in zip(bars, X, Y, lower, upper, strict=True):
        np.testing.assert_allclose(start, ax.c2p(x, y - lo), atol=1e-9)
        np.testing.assert_allclose(end, ax.c2p(x, y + hi), atol=1e-9)


def test_eb2_x_errors_are_horizontal_bars():
    ax = mp.Axes()
    bars = segments(ax.errorbar(X, Y, xerr=[[0.2, 0.2, 0.2], [0.5, 0.5, 0.5]]).xbars)
    for (start, end), x, y in zip(bars, X, Y, strict=True):
        np.testing.assert_allclose(start, ax.c2p(x - 0.2, y), atol=1e-9)
        np.testing.assert_allclose(end, ax.c2p(x + 0.5, y), atol=1e-9)


@pytest.mark.parametrize("name", ["yerr", "xerr"])
def test_eb2_a_negative_error_raises(name):
    with pytest.raises(ValueError, match=name):
        mp.Axes().errorbar(X, Y, **{name: [0.1, -0.1, 0.1]})


def test_eb2_a_nan_error_draws_no_bar_and_warns():
    ax = mp.Axes()
    with pytest.warns(mp.ManimPlotsWarning):
        eb = ax.errorbar(X, Y, yerr=[0.1, np.nan, 0.1])
    assert len(segments(eb.ybars)) == 2


def test_eb3_a_lower_end_outside_a_log_domain_runs_to_the_edge():
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(1, 100, 1), y_scale="log")
    eb = ax.errorbar([1.0, 3.0], [2.0, 20.0], yerr=[5.0, 5.0])
    (s0, e0), (s1, _) = segments(eb.ybars)
    np.testing.assert_allclose(s0, ax.c2p(1, 1), atol=1e-9)  # the viewport's bottom
    np.testing.assert_allclose(e0, ax.c2p(1, 7), atol=1e-9)
    np.testing.assert_allclose(s1, ax.c2p(3, 15), atol=1e-9)
    assert len(segments(eb.ycaps)) == 3  # no cap at the end that left the domain


def test_eb4_caps_are_perpendicular_and_capsize_long_in_scene_units():
    ax = mp.Axes().rotate(30 * DEGREES)
    eb = ax.errorbar(X, Y, yerr=0.5, capsize=0.2)
    bars, caps = segments(eb.ybars), segments(eb.ycaps)
    assert len(caps) == 6
    for cap in caps:
        assert length(cap) == pytest.approx(0.2, abs=1e-9)
    direction = unit(bars[0][1] - bars[0][0])
    for cap in caps:
        assert abs(unit(cap[1] - cap[0]) @ direction) < 1e-9
    centres = np.array([(c[0] + c[1]) / 2 for c in caps])
    for bar in bars:
        for end in bar:
            assert np.min(np.linalg.norm(centres - end, axis=1)) < 1e-9


def test_eb4_caps_keep_their_size_when_the_axes_zoom():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    before = length(segments(eb.ybars)[0])
    ax.scale(2)
    assert length(segments(eb.ybars)[0]) == pytest.approx(2 * before, rel=1e-9)
    assert length(segments(eb.ycaps)[0]) == pytest.approx(0.1, abs=1e-9)


def test_eb4_capsize_zero_draws_no_caps():
    assert none_or_empty(mp.Axes().errorbar(X, Y, yerr=0.5, capsize=0).ycaps)


def test_eb5_parts_present_or_none():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    assert eb.xbars is None and eb.xcaps is None and eb.line is None
    assert eb.ybars is not None and eb.ycaps is not None
    both = ax.errorbar(X, Y, yerr=0.5, xerr=0.3, line=True, marker=None)
    assert both.markers is None
    assert isinstance(both.line, mp.LinePlot)
    np.testing.assert_allclose(
        np.asarray(both.line.points)[[0, -1]],
        np.asarray(ax.c2p(X[[0, -1]], Y[[0, -1]])).T,
        atol=1e-9,
    )


def test_eb5_bar_styles():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5, color=GREEN)
    assert eb.ybars.get_color() == GREEN  # ecolor defaults to the markers' colour
    assert eb.ybars.get_stroke_width() == 2
    assert eb.ycaps.get_stroke_width() == 2
    styled = ax.errorbar(X, Y, yerr=0.5, ecolor=RED, elinewidth=4)
    assert styled.ybars.get_color() == RED
    assert styled.ycaps.get_stroke_width() == 4
    thin = ax.errorbar(X, Y, yerr=0.5, elinewidth=4, capthick=1)
    assert thin.ycaps.get_stroke_width() == 1


def test_eb5_barsabove_orders_the_family():
    ax = mp.Axes()
    below = ax.errorbar(X, Y, yerr=0.5)
    above = ax.errorbar(X, Y, yerr=0.5, barsabove=True)
    assert list(below).index(below.ybars) < list(below).index(below.markers)
    assert list(above).index(above.ybars) > list(above).index(above.markers)


@pytest.mark.parametrize(("every", "kept"), [(2, [0, 2, 4]), ((1, 2), [1, 3])])
def test_eb5_errorevery(every, kept):
    ax = mp.Axes()
    xs = np.arange(5.0) - 2
    ys = np.ones(5)
    bars = segments(ax.errorbar(xs, ys, yerr=0.5, errorevery=every).ybars)
    np.testing.assert_allclose(
        [ax.p2c(start)[0] for start, _ in bars], xs[kept], atol=1e-9
    )


def test_eb5_a_style_on_a_part_survives_set_data():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    eb.ybars.set_color(GREEN)
    eb.set_data(X, Y + 1, yerr=0.2)
    assert eb.ybars.get_color() == GREEN


def test_eb6_an_uncoloured_errorbar_takes_the_cycle():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    assert eb.markers[0].get_color() == mp.COLOR_CYCLE[0]
    assert eb.ybars.get_color() == mp.COLOR_CYCLE[0]
    assert ax.plot(np.sin).get_color() == mp.COLOR_CYCLE[1]


def test_eb7_clipping_per_axis():
    ax = mp.Axes()  # y in (-4, 4)
    clipped = segments(ax.errorbar([0.0], [3.9], yerr=0.5).ybars)
    np.testing.assert_allclose(clipped[0][1], ax.c2p(0, 4), atol=1e-9)
    free = ax.errorbar([0.0], [3.9], yerr=0.5, clip=(True, False))
    np.testing.assert_allclose(segments(free.ybars)[0][1], ax.c2p(0, 4.4), atol=1e-9)
    assert free.get_clip() == (True, False)


# --- ED: data changes -----------------------------------------------------------------


def test_ed1_set_data_replaces_the_data():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    assert eb.set_data(X, Y + 1, yerr=0.2, xerr=0.1) is eb
    start, _ = segments(eb.ybars)[0]
    np.testing.assert_allclose(start, ax.c2p(X[0], Y[0] + 0.8), atol=1e-9)
    assert eb.xbars is not None and len(segments(eb.xbars)) == 3


def test_ed2_an_animated_set_data_moves_each_bar():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)

    def construct(scene: Scene) -> None:
        scene.add(ax, eb)
        scene.play(eb.animate.set_data(X, Y + 2, yerr=1.0), run_time=1)

    tops = probe(construct, lambda: float(ax.p2c(segments(eb.ybars)[0][1])[1]))
    assert tops[-1] == pytest.approx(Y[0] + 3, abs=1e-6)
    assert any(Y[0] + 0.5 + 1e-3 < t < Y[0] + 3 - 1e-3 for t in tops)


def test_ed2_a_different_count_under_animate_raises():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)

    def construct(scene: Scene) -> None:
        scene.add(ax, eb)
        scene.play(eb.animate.set_data(X[:2], Y[:2], yerr=0.5), run_time=1)

    with pytest.raises(ValueError, match="set_data"):
        probe(construct, lambda: None)
    eb.set_data(X[:2], Y[:2], yerr=0.5)  # accepted outside an animation
    assert len(segments(eb.ybars)) == 2


def test_ed3_an_errorbar_follows_the_range():
    ax = mp.Axes()
    eb = ax.errorbar(X, Y, yerr=0.5)
    ax.set_x_range((-3, 3))
    np.testing.assert_allclose(segments(eb.ybars)[0][0], ax.c2p(X[0], 0.5), atol=1e-9)


# --- EL: the legend -------------------------------------------------------------------


def test_el1_one_entry_with_a_bar_through_the_marker():
    ax = mp.Axes()
    ax.errorbar(X, Y, yerr=0.5, label="data")
    handles, labels = ax.get_legend_handles_labels()
    assert labels == ["data"]
    parts = [m for m in handles[0].get_family() if m.has_points()]
    assert any(p.width < 1e-6 < p.height for p in parts)  # the vertical bar
    assert len(parts) >= 2
