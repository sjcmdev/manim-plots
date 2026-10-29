"""Task 19: twin and multiple axes.

Rows TW and PO of `docs/acceptance/19-twin-axes.md`. The oracle is the map of the root
system: a twin shares its frame, so a twin's point is the root's point at the same x and
the y rescaled between the two ranges.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import DEGREES, RED, UP, Create, Scene, Transform

import manim_plots as mp

from .helpers import probe


def axes(**kwargs):
    """x in (0, 10), y in (0, 100), 8 by 4 scene units."""
    return mp.Axes(
        x_range=(0, 10, 1), y_range=(0, 100, 10), x_length=8, y_length=4, **kwargs
    )


def right(ax) -> float:
    return float(ax.c2p(10, 0)[0])


def top(ax) -> float:
    return float(ax.c2p(0, 100)[1])


def line_x(axis) -> float:
    return float(np.asarray(axis.line.points)[:, 0].mean())


def line_y(axis) -> float:
    return float(np.asarray(axis.line.points)[:, 1].mean())


# --- TW: twins ------------------------------------------------------------------------


def test_tw1_twinx_shares_x_and_owns_y():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1, 0.2))
    assert isinstance(twin, mp.CartesianAxes)
    assert twin.x is ax.x
    assert twin.y is not ax.y
    np.testing.assert_array_equal(twin.y.range.value, [0, 1])
    np.testing.assert_array_equal(ax.y.range.value, [0, 100])


def test_tw1_defaults_and_scales():
    ax = axes()
    np.testing.assert_array_equal(ax.twinx().y.range.value, [0, 100])
    logged = ax.twinx(y_range=(1, 1000), y_scale="log")
    assert logged.c2p(5, 10)[1] == pytest.approx(
        ax.c2p(0, 0)[1] + (top(ax) - ax.c2p(0, 0)[1]) / 3, abs=1e-9
    )


def test_tw1_twiny_shares_y():
    ax = axes()
    twin = ax.twiny(x_range=(0, 5, 1))
    assert twin.y is ax.y
    np.testing.assert_array_equal(twin.x.range.value, [0, 5])


def test_tw1_a_twin_of_a_twin_is_a_twin_of_the_root():
    ax = axes()
    first = ax.twinx(y_range=(0, 1))
    second = first.twinx(y_range=(0, 5))
    assert second.parent is ax
    assert ax.twins == (first, second)


def test_tw2_the_twins_axis_is_on_the_right_without_a_tip():
    ax = axes(axis_config={"include_numbers": True})
    ax.x.set_position("bottom")
    ax.y.set_position("left")
    twin = ax.twinx(y_range=(0, 1, 0.2), y_axis_config={"include_numbers": True})
    assert line_x(twin.y_axis) == pytest.approx(right(ax), abs=1e-9)
    assert twin.y_axis.tip is None
    assert len(twin.y_axis.numbers) > 0
    assert all(n.get_center()[0] > right(ax) for n in twin.y_axis.numbers)


def test_tw2_further_twins_are_offset_outward():
    ax = axes()
    first, second, third = ax.twinx(), ax.twinx(), ax.twinx(offset=1.5)
    assert line_x(first.y_axis) == pytest.approx(right(ax), abs=1e-9)
    assert line_x(second.y_axis) == pytest.approx(right(ax) + 0.9, abs=1e-9)
    assert line_x(third.y_axis) == pytest.approx(right(ax) + 0.9 + 1.5, abs=1e-9)


def test_tw2_twiny_is_on_top_and_the_shared_axis_is_drawn_once():
    ax = axes()
    twin = ax.twiny(x_range=(0, 5, 1))
    assert line_y(twin.x_axis) == pytest.approx(top(ax), abs=1e-9)
    assert twin.x_axis.tip is None
    assert ax.get_family().count(ax.y_axis) == 1
    assert ax.get_family().count(ax.x_axis) == 1


def test_tw3_a_twin_belongs_to_its_parents_family():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    assert twin.parent is ax and ax.parent is None
    assert ax.twins == (twin,)
    assert twin.y_axis in ax.get_family()


def test_tw3_create_draws_the_twins():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))

    def construct(scene: Scene) -> None:
        scene.play(Create(ax), run_time=1)

    probe(construct, lambda: None)
    assert twin.y_axis.line.get_stroke_opacity() > 0
    assert len(np.asarray(twin.y_axis.line.points)) > 0


def test_tw4_a_twins_map_rescales_y_on_the_shared_rectangle():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    for x, y in [(0, 0), (5, 0.5), (10, 1), (2.5, 0.8)]:
        np.testing.assert_allclose(twin.c2p(x, y), ax.c2p(x, 100 * y), atol=1e-9)
        np.testing.assert_allclose(twin.p2c(ax.c2p(x, 100 * y))[:2], [x, y], atol=1e-9)


def test_tw5_artists_bind_to_their_pair():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: x / 10)
    line = twin.line([0, 10], [0.2, 0.4])
    bars = twin.errorbar([5.0], [0.5], yerr=0.1)
    assert curve in twin.artists and curve not in ax.artists
    assert line in twin.artists
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(10, 100), atol=1e-6)
    np.testing.assert_allclose(np.asarray(line.points)[0], ax.c2p(0, 20), atol=1e-9)
    assert bars.markers is not None
    np.testing.assert_allclose(bars.markers[0].get_center(), ax.c2p(5, 50), atol=1e-9)
    label = twin.get_T_label(5, curve)
    np.testing.assert_allclose(
        np.asarray(label.line.points)[-1], ax.c2p(5, 50), atol=1e-6
    )


def test_tw6_twins_follow_the_parents_geometry():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: x / 10)
    ax.shift(UP).rotate(20 * DEGREES)
    np.testing.assert_allclose(twin.c2p(5, 0.5), ax.c2p(5, 50), atol=1e-9)
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(10, 100), atol=1e-6)
    assert line_x(twin.y_axis) == pytest.approx(float(ax.c2p(10, 50)[0]), abs=1e-6)


def test_tw6_twins_follow_an_animated_shift():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: x / 10)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.shift(2 * UP), run_time=1)

    frames = probe(
        construct,
        lambda: (
            np.array(curve.points, copy=True)[-1],
            np.array(ax.c2p(10, 100), copy=True),
        ),
    )
    for end, expected in frames:
        np.testing.assert_allclose(end, expected, atol=1e-6)


def test_tw6_geometry_on_a_twin_alone_raises():
    twin = axes().twinx()
    with pytest.raises(ValueError, match="parent"):
        twin.shift(UP)


def test_tw7_the_shared_range_moves_the_twins():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: x / 10)
    ax.set_x_range((0, 5))
    np.testing.assert_array_equal(twin.x.range.value, [0, 5])
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(5, 50), atol=1e-6)


def test_tw7_an_animated_shared_range_moves_the_twins_on_every_frame():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: 0.5 + 0 * x)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.set_x_range((0, 20)), run_time=1)

    frames = probe(
        construct,
        lambda: (
            float(np.asarray(curve.points)[:, 1].mean()),
            float(ax.c2p(0, 50)[1]),
            float(twin.x.range.value[1]),
            float(ax.x.range.value[1]),
        ),
    )
    for height, expected, twin_end, end in frames:
        assert height == pytest.approx(expected, abs=1e-6)
        assert twin_end == end
    assert ax.x.range.value[1] == 20


def test_tw7_a_twins_own_range_moves_only_it():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = ax.plot(lambda x: 10 * x)
    before = np.array(curve.points, copy=True)
    twin.set_y_range((0, 2))
    np.testing.assert_array_equal(ax.y.range.value, [0, 100])
    np.testing.assert_allclose(curve.points, before, atol=1e-12)
    np.testing.assert_allclose(twin.c2p(5, 1), ax.c2p(5, 50), atol=1e-9)


def test_tw7_a_chain_on_the_parent_is_one_animation():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: 0.5 + 0 * x)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(ax.animate.shift(UP).set_x_range((0, 20)), run_time=1)

    probe(construct, lambda: None)
    np.testing.assert_allclose(np.asarray(curve.points)[0], ax.c2p(0, 50), atol=1e-6)
    assert twin.x.range.value[1] == 20


def test_tw8_artists_clip_to_the_shared_rectangle():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    curve = twin.plot(lambda x: x / 5)  # leaves the top at x = 5
    assert np.asarray(curve.points)[:, 1].max() <= top(ax) + 1e-9
    free = twin.plot(lambda x: x / 5, clip=(True, False))
    assert np.asarray(free.points)[:, 1].max() > top(ax) + 1


def test_tw9_twins_continue_the_colour_cycle():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    assert ax.plot(np.sin).get_color() == mp.COLOR_CYCLE[0]
    assert twin.plot(np.cos).get_color() == mp.COLOR_CYCLE[1]
    assert ax.plot(np.tan).get_color() == mp.COLOR_CYCLE[2]


def test_tw10_the_parents_legend_collects_the_twins():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    ax.plot(lambda x: 10 * x, label="a")
    twin.plot(lambda x: x / 10, label="b")
    ax.plot(lambda x: 5 * x, label="c")
    assert ax.get_legend_handles_labels()[1] == ["a", "b", "c"]
    assert twin.get_legend_handles_labels()[1] == ["b"]
    assert len(ax.legend().entries) == 3


def test_tw11_a_copy_copies_the_twins():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    twin.plot(lambda x: x / 10)
    copied = ax.copy()
    assert len(copied.twins) == 1
    other = copied.twins[0]
    assert other is not twin and other.parent is copied and other.x is copied.x
    copied.set_x_range((0, 5))
    np.testing.assert_array_equal(twin.x.range.value, [0, 10])


def test_tw11_transform_pairs_twins_and_refuses_a_different_count():
    a, b = axes(), axes()
    a.twinx(y_range=(0, 1))
    b.twinx(y_range=(0, 2))
    c = axes()

    def pairs(scene: Scene) -> None:
        scene.add(a)
        scene.play(Transform(a, b), run_time=1)

    probe(pairs, lambda: None)
    np.testing.assert_array_equal(a.twins[0].y.range.value, [0, 2])

    def refuses(scene: Scene) -> None:
        scene.add(b)
        scene.play(Transform(b, c), run_time=1)

    with pytest.raises(ValueError, match="twins"):
        probe(refuses, lambda: None)


def test_tw12_a_twins_axis_takes_the_decoration_calls():
    ax = axes()
    twin = ax.twinx(y_range=(0, 1))
    twin.y_axis.set_color(RED)
    assert twin.y_axis.line.get_color() == RED
    label = twin.get_y_axis_label("T")
    assert label.get_center()[0] > right(ax)


# --- PO: outward positions ------------------------------------------------------------


def test_po1_an_axis_offset_outward_from_a_border():
    ax = axes(axis_config={"include_numbers": True})
    ax.y_axis.set_position("right", offset=0.5)
    assert line_x(ax.y_axis) == pytest.approx(right(ax) + 0.5, abs=1e-9)
    assert all(n.get_center()[0] > right(ax) + 0.5 for n in ax.y_axis.numbers)
    ax.x_axis.set_position("bottom", offset=0.3)
    assert line_y(ax.x_axis) == pytest.approx(float(ax.c2p(0, 0)[1]) - 0.3, abs=1e-9)


@pytest.mark.parametrize(
    ("where", "offset"), [("right", -0.1), ("right", float("inf")), ("origin", 1.0)]
)
def test_po1_bad_offsets_raise(where, offset):
    with pytest.raises(ValueError, match="offset"):
        axes().y_axis.set_position(where, offset=offset)
