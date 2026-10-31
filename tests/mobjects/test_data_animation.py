"""Task 34: data animation, rows GR, SD, SB, AP, AX of
`docs/acceptance/34-data-animation.md`.

The oracles: bar geometry from the data at every probed frame, `numpy.histogram`, and
the axes' state before and after each animation.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import ManimColor, Scene, Succession, ValueTracker, linear

import manim_plots as mp

from .helpers import probe


def corners(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def box(ax: Any, mob: Any) -> tuple[float, float, float, float]:
    if not mob.has_points():
        return (np.nan, np.nan, np.nan, np.nan)
    d = data(ax, corners(mob))
    return (d[:, 0].min(), d[:, 0].max(), d[:, 1].min(), d[:, 1].max())


def axes() -> Any:
    return mp.Axes(x_range=(-1, 5, 1), y_range=(0, 10, 2))


# --- GR -------------------------------------------------------------------------------


def test_gr1_bars_grow_from_their_base():
    ax = axes()
    bars = ax.bar([0, 1, 2], [4, 6, 8])
    seen: list[list[float]] = []

    def record() -> None:
        seen.append([box(ax, b)[3] if b.has_points() else 0.0 for b in bars])

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(mp.GrowBars(bars, lag_ratio=0.2, rate_func=linear))

    probe(construct, record)
    tops = np.array(seen)
    assert np.all(tops >= -1e-9)
    assert np.all(np.diff(tops, axis=0) >= -1e-9)  # never shrinking
    mid = tops[len(tops) // 2]
    assert mid[0] / 4 >= mid[2] / 8 - 1e-9  # the first bar leads
    final = [box(ax, b)[3] for b in bars]  # after the play's finish
    np.testing.assert_allclose(final, [4, 6, 8], atol=1e-9)
    for b in bars:
        assert box(ax, b)[2] == pytest.approx(0, abs=1e-9)
    ax.set_y_range((0, 20, 5))
    assert box(ax, bars[2])[3] == pytest.approx(8, abs=1e-9)


def test_gr2_shrink_removes_and_keeps_the_data():
    ax = axes()
    bars = ax.bar([0, 1], [4, 6])
    present: list[bool] = []

    class Shot(Scene):
        def construct(self) -> None:
            self.add(ax, bars)
            self.play(mp.ShrinkBars(bars))
            present.append(bars in self.mobjects)

    from manim import tempconfig

    from .helpers import RUN

    with tempconfig(RUN):
        Shot().render()
    assert present == [False]
    assert box(ax, bars[1])[3] == pytest.approx(6, abs=1e-9)


def test_gr1_histograms_and_3d_bars_grow():
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(0, 40, 10))  # counts reach 17
    h: Any = ax.hist(np.random.default_rng(0).normal(2, 1, 40), bins=4, range=(0, 4))
    probe(lambda s: s.play(mp.GrowBars(h.bars)), lambda: None)
    assert box(ax, h.bars[1])[3] == pytest.approx(h.counts[1], abs=1e-9)
    ax3 = mp.ThreeDAxes(z_range=(0, 10, 2))
    b3 = ax3.bar3d([0], [0], [0], 1, 1, 5)
    probe(lambda s: s.play(mp.GrowBars(b3)), lambda: None)
    top = np.array([ax3.p2c(p) for p in corners(b3.bars[0][1])])
    np.testing.assert_allclose(top[:, 2], 5, atol=1e-9)


# --- SD -------------------------------------------------------------------------------


def test_sd1_keyed_change_moves_grows_and_removes():
    ax = mp.Axes(y_range=(0, 10, 2))
    bars = ax.bar(["a", "b", "c"], [2, 4, 6])
    a, b = bars.at("a"), bars.at("b")
    seen: list[tuple[float, float]] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        scene.play(
            bars.animate(rate_func=linear).set_data(x=["b", "c", "d"], height=[8, 6, 4])
        )

    def record() -> None:
        seen.append((box(ax, b)[3], box(ax, a)[3] if a.has_points() else 0.0))

    probe(construct, record)
    tops_b = np.array([s[0] for s in seen])
    assert np.all(np.diff(tops_b) >= -1e-9)
    assert box(ax, b)[3] == pytest.approx(8, abs=1e-9)  # after the play's finish
    tops_a = np.array([s[1] for s in seen])
    assert np.all(np.diff(tops_a) <= 1e-9)
    assert a not in list(bars)
    d = bars.at("d")
    assert box(ax, d)[3] == pytest.approx(4, abs=1e-9)


def test_sd2_histogram_counts_interpolate():
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(0, 200, 50))  # no count is clipped
    rng = np.random.default_rng(1)
    first, second = rng.normal(1, 0.5, 200), rng.normal(3, 0.5, 200)
    h: Any = ax.hist(first, bins=4, range=(0, 4))
    start = h.counts.copy()
    end = np.histogram(second, 4, (0, 4))[0]
    seen: list[np.ndarray] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, h)
        scene.play(h.animate(rate_func=linear).set_data(second))

    probe(construct, lambda: seen.append(np.array([box(ax, b)[3] for b in h.bars])))
    for tops in seen:
        alpha = (tops - start) / np.where(end != start, end - start, 1)
        moving = end != start
        assert np.ptp(alpha[moving]) < 1e-6  # one alpha for every bin
    final = np.array([box(ax, b)[3] for b in h.bars])  # after the play's finish
    np.testing.assert_allclose(final, end, atol=1e-9)


def test_sd2_heatmap_values_interpolate_through_the_mapping():
    ax = axes()
    img = ax.imshow(np.array([[0.0, 1.0]]), vmin=0, vmax=1)
    viridis = mp.colormaps["viridis"]
    seen: list[np.ndarray] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, img)
        scene.play(img.animate(rate_func=linear).set_data(np.array([[1.0, 0.0]])))

    def record() -> None:
        from manim import ManimColor

        seen.append(
            np.asarray(ManimColor(img.cells.at((0, 0)).get_fill_color()).to_rgb())
        )

    probe(construct, record)
    mid = seen[len(seen) // 2]
    candidates = [viridis(t) for t in np.linspace(0, 1, 201)]
    assert min(float(np.max(np.abs(mid - c))) for c in candidates) < 2 / 255


# --- SB -------------------------------------------------------------------------------


def test_sb1_sorting_slides_bars_and_categories():
    ax = mp.Axes(y_range=(0, 10, 2))
    bars = ax.bar(["a", "b", "c"], [5, 9, 2])
    heights: list[list[float]] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        scene.play(mp.SortBars(bars, reverse=True))

    probe(construct, lambda: heights.append([box(ax, b)[3] for b in bars]))
    assert all(h == pytest.approx([5, 9, 2]) for h in heights)  # heights fixed
    assert ax.x.categories == ("b", "a", "c")
    centre = (box(ax, bars.at("b"))[0] + box(ax, bars.at("b"))[1]) / 2
    assert centre == pytest.approx(0, abs=1e-9)


def test_sb2_a_race():
    ax = mp.Axes(y_range=(0, 10, 2))
    bars = ax.bar(["a", "b", "c"], [1, 2, 3])
    steps = [[3, 1, 2], [2, 3, 1], [5, 4, 6]]

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        for values in steps:
            scene.play(
                Succession(
                    cast(Any, bars.animate).set_data(x=["a", "b", "c"], height=values),
                    mp.SortBars(bars, reverse=True),
                )
            )

    probe(construct, lambda: None)
    assert ax.x.categories == ("c", "a", "b")


def test_sb1_slots_follow_the_categories_after_several_sorts():
    names = ["a", "b", "c", "d", "e"]
    ax = mp.Axes(y_range=(0, 10, 2))
    bars = ax.bar(names, [3, 5, 2, 4, 1])

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        for values in ([4, 5, 6, 4, 3], [6, 5, 7, 8, 5]):
            scene.play(cast(Any, bars.animate).set_data(x=names, height=values))
            scene.play(mp.SortBars(bars, reverse=True))

    probe(construct, lambda: None)
    assert ax.x.categories == ("d", "c", "a", "b", "e")
    for name in names:
        x0, x1, _, _ = box(ax, bars.at(name))
        assert (x0 + x1) / 2 == pytest.approx(ax.x.categories.index(name), abs=1e-9)


def test_sd1_colour_by_height_follows_the_data():
    ax = mp.Axes(y_range=(0, 10, 2))
    bars = ax.bar(["a", "b"], [2, 8], c="height", vmin=0, vmax=10)
    viridis = mp.colormaps["viridis"]

    def colour(name: str) -> np.ndarray:
        return np.asarray(ManimColor(bars.at(name).get_fill_color()).to_rgb())

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        scene.play(cast(Any, bars.animate).set_data(x=["a", "b"], height=[8, 2]))

    probe(construct, lambda: None)
    np.testing.assert_allclose(colour("a"), viridis(0.8), atol=1.5 / 255)
    np.testing.assert_allclose(colour("b"), viridis(0.2), atol=1.5 / 255)
    bars.set_data(x=["a", "b"], height=[5, 5])
    np.testing.assert_allclose(colour("a"), viridis(0.5), atol=1.5 / 255)


# --- LB -------------------------------------------------------------------------------


def no_ghosts(scene: Scene) -> list[str]:
    """Names of moving mobjects that left every family but still have points."""
    alive = {id(m) for top in scene.mobjects for m in top.get_family()}
    return [
        type(m).__name__
        for m in scene.moving_mobjects
        if id(m) not in alive and m.has_points()
    ]


def test_lb1_rebuilt_labels_leave_no_ghosts():
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 10, 2))
    line = ax.line([0, 0.5, 1], [1, 1.2, 1.65])
    end = ax.end_label(line)
    bars = ax.bar([3], [2])
    values = ax.bar_label(bars)
    t = ValueTracker(0.5)
    cross = ax.crosshair(t, 2)
    ghosts: list[str] = []

    class Shot(Scene):
        def update_to_time(self, time: float) -> None:
            super().update_to_time(time)
            ghosts.extend(no_ghosts(self))

        def construct(self) -> None:
            self.add(ax, line, end, bars, values, cross)
            self.play(
                mp.AppendData(line, [2, 3], [5, 8]),
                cast(Any, bars.animate).set_data(x=[3], height=[9]),
                t.animate.set_value(3.5),
            )

    from manim import tempconfig

    from .helpers import RUN

    with tempconfig(RUN):
        Shot().render()
    assert ghosts == []


# --- AP -------------------------------------------------------------------------------


def test_ap1_append_draws_on():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 10, 1))
    line = ax.line([0, 1], [0, 1])
    lengths: list[int] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, line)
        scene.play(mp.AppendData(line, [2, 3, 4], [4, 9, 16 / 2], rate_func=linear))

    probe(construct, lambda: lengths.append(len(line.points)))
    assert lengths == sorted(lengths)
    np.testing.assert_allclose(ax.p2c(line.points[-1])[:2], (4, 8), atol=1e-9)


def test_ap2_margins_and_autoscale():
    ax = mp.Axes(x_range=(0, 1, 1), y_range=(0, 1, 1))
    assert ax.margins() == pytest.approx((0.05, 0.05))
    held = ax.line([0, 10], [-2, 2])  # the axes keep artists weakly
    ax.autoscale()
    assert tuple(ax.x_range[:2]) == pytest.approx((-0.5, 10.5))
    assert tuple(ax.y_range[:2]) == pytest.approx((-2.2, 2.2))
    ax.margins(0, 0.5)
    ax.autoscale(axis="y")
    assert tuple(ax.y_range[:2]) == pytest.approx((-4, 4))
    ax.autoscale(tight=True)
    assert tuple(ax.x_range[:2]) == pytest.approx((0, 10))
    assert held is not None


def test_ap3_append_with_autoscale_keeps_the_data_inside():
    ax = mp.Axes(x_range=(0, 2, 1), y_range=(0, 2, 1))
    line = ax.line([0, 1], [0, 1])
    inside: list[bool] = []

    def record() -> None:
        pts = np.array([ax.p2c(p) for p in np.asarray(line.points)[::4]])
        (x0, x1), (y0, y1) = ax.x_range[:2], ax.y_range[:2]
        inside.append(
            bool(
                pts[:, 0].min() >= x0 - 1e-9
                and pts[:, 0].max() <= x1 + 1e-9
                and pts[:, 1].min() >= y0 - 1e-9
                and pts[:, 1].max() <= y1 + 1e-9
            )
        )

    def construct(scene: Scene) -> None:
        scene.add(ax, line)
        scene.play(mp.AppendData(line, [2, 4, 8], [3, 5, 9], autoscale=True))

    probe(construct, record)
    assert all(inside)
    assert ax.x_range[1] >= 8 and ax.y_range[1] >= 9


def test_ap3_the_axes_are_redrawn_while_they_widen():
    ax = mp.Axes(x_range=(0, 2, 1), y_range=(0, 2, 1))
    line = ax.line([0, 1], [0, 1])
    moving: list[bool] = []
    ticks: list[float] = []

    class Shot(Scene):
        def begin_animations(self) -> None:
            super().begin_animations()
            members = {id(m) for m in self.moving_mobjects}
            moving.append(id(ax) in members or id(ax.x.line) in members)

        def update_to_time(self, time: float) -> None:
            super().update_to_time(time)
            ticks.append(float(ax.x.ticks.at(1.0).get_center()[0]))

        def construct(self) -> None:
            self.add(ax, line)
            self.play(mp.AppendData(line, [2, 4, 8], [3, 5, 9], autoscale=True))

    from manim import tempconfig

    from .helpers import RUN

    with tempconfig(RUN):
        Shot().render()
    assert moving == [True]  # not frozen in the static background (F-915)
    assert ticks[-1] < ticks[0] - 1e-3  # the tick at 1 slides left as x widens
    assert line is not None


# --- AX -------------------------------------------------------------------------------


def test_ax1_build_axes_ends_where_it_started():
    ax = axes()
    ax.x.add_numbers()
    before = [np.array(m.points, copy=True) for m in ax.family_members_with_points()]
    opacities: list[float] = []

    def construct(scene: Scene) -> None:
        scene.play(mp.BuildAxes(ax))

    number = ax.x.numbers.at(2.0)
    probe(construct, lambda: opacities.append(float(number.get_fill_opacity())))
    after = [np.array(m.points) for m in ax.family_members_with_points()]
    assert len(before) == len(after)
    for a, b in zip(before, after, strict=True):
        np.testing.assert_allclose(a, b, atol=1e-9)
    assert opacities[0] < opacities[-1]


def test_ax2_highlight_a_tick():
    ax = axes()
    tick = ax.x.ticks.at(2.0)
    before = np.array(tick.points, copy=True)
    probe(lambda s: s.play(mp.HighlightTick(ax.x, 2.0)), lambda: None)
    np.testing.assert_allclose(tick.points, before, atol=1e-9)
    with pytest.raises(KeyError):
        mp.HighlightTick(ax.x, 2.5)


def test_ax3_highlight_a_bar():
    ax = axes()
    bars = ax.bar([0, 1, 2], [4, 6, 8])
    dims: list[float] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, bars)
        scene.play(mp.HighlightBar(bars, 1))

    probe(construct, lambda: dims.append(float(bars[0].get_fill_opacity())))
    assert min(dims) == pytest.approx(0.25, abs=0.05)
    assert bars[0].get_fill_opacity() == pytest.approx(1)
