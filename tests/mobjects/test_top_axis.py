"""Task 19b: any pair of axes and an independent top axis.

Rows PA, SA, MI and RP of `docs/acceptance/19b-top-axis.md`. The oracle is the root's
map: every system shares its frame, so a point of a pair is the root's point with x and
y rescaled between the ranges.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import RED, UP, Scene

import manim_plots as mp
from manim_plots.mobjects.axis import Axis

from .helpers import probe

KELVIN = (lambda c: c + 273.15, lambda k: k - 273.15)
HC = 1239.84198  # eV nm
ELECTRONVOLT = (lambda nm: HC / nm, lambda ev: HC / ev)


def axes(**kwargs):
    """x in (0, 10), y in (0, 100), 8 by 4 scene units."""
    return mp.Axes(
        x_range=(0, 10, 1), y_range=(0, 100, 10), x_length=8, y_length=4, **kwargs
    )


def framed(**kwargs):
    ax = axes(**kwargs)
    ax.x.set_position("bottom")
    ax.y.set_position("left")
    return ax


def top(ax) -> float:
    return float(ax.c2p(0, 100)[1])


def right(ax) -> float:
    return float(ax.c2p(10, 0)[0])


def line_y(axis) -> float:
    return float(np.asarray(axis.line.points)[:, 1].mean())


def drawn(axis) -> bool:
    return len(np.asarray(axis.line.points)) > 0


def axes_on(ax, side: str) -> list[Axis]:
    """Every drawn axis line of the family lying on one border of the rectangle."""
    index, place = {
        "top": (1, top(ax)),
        "bottom": (1, float(ax.c2p(0, 0)[1])),
        "left": (0, float(ax.c2p(0, 0)[0])),
        "right": (0, right(ax)),
    }[side]
    found: dict[int, Axis] = {}
    for m in ax.get_family():
        if isinstance(m, Axis) and drawn(m):
            p = np.asarray(m.line.points)[:, index]
            if np.allclose(p, place, atol=1e-9):
                found[id(m)] = m
    return list(found.values())


def points(ax) -> int:
    return sum(len(m.points) for m in ax.get_family())


def tick_xs(axis) -> np.ndarray:
    return np.array([float(t.get_center()[0]) for t in axis.ticks])


def tick_ys(axis) -> np.ndarray:
    return np.array([float(t.get_center()[1]) for t in axis.ticks])


def tick_length(axis) -> float:
    return float(np.ptp(np.asarray(axis.ticks[0].points)[:, 1]))


def tick_side(axis) -> tuple[float, float]:
    """How far the first major tick reaches below and above its axis line."""
    tick = np.asarray(axis.ticks[0].points)
    middle = line_y(axis)
    return middle - float(tick[:, 1].min()), float(tick[:, 1].max()) - middle


# --- PA-1 -----------------------------------------------------------------------------


def test_pa1_a_twins_twiny_shares_the_twins_y():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    corner = right_.twiny(x_range=(0, 5, 1))
    assert corner.y is right_.y
    assert corner.x is not ax.x
    assert corner.parent is ax
    assert ax.twins == (right_, corner)
    curve = corner.plot(lambda x: x / 5)
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(10, 100), atol=1e-6)
    np.testing.assert_allclose(np.asarray(curve.points)[0], ax.c2p(0, 0), atol=1e-6)


def test_pa1_a_top_twins_twinx_shares_the_top_x():
    ax = axes()
    top_ = ax.twiny(x_range=(0, 5, 1))
    corner = top_.twinx(y_range=(0, 1))
    assert corner.x is top_.x and corner.y is not ax.y
    np.testing.assert_allclose(corner.c2p(5, 1), ax.c2p(10, 100), atol=1e-9)
    np.testing.assert_allclose(corner.c2p(2.5, 0.5), ax.c2p(5, 50), atol=1e-9)


def test_pa1_the_same_direction_is_unchanged():
    ax = axes()
    first = ax.twinx(y_range=(0, 1))
    second = first.twinx(y_range=(0, 5))
    assert second.x is ax.x and second.parent is ax


def test_pa1_the_new_axis_goes_after_the_axes_on_its_side():
    ax = axes()
    ax.twiny(x_range=(0, 5, 1))
    corner = ax.twinx(y_range=(0, 1)).twiny(x_range=(0, 2, 1))
    assert line_y(corner.x) == pytest.approx(top(ax) + 0.9, abs=1e-9)


# --- PA-2, PA-3 -----------------------------------------------------------------------


def test_pa2_twin_returns_the_system_of_a_pair():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    top_ = ax.twiny(x_range=(0, 5, 1))
    corner = ax.twin(x=top_, y=right_)
    assert corner.x is top_.x and corner.y is right_.y
    assert ax.twin(x=top_.x, y=right_.y) is corner
    assert ax.twin(x=top_, y=right_) is corner
    assert right_.twin(x=top_) is corner
    assert top_.twin(y=right_.y) is corner


def test_pa2_twin_returns_the_systems_that_already_exist():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    top_ = ax.twiny(x_range=(0, 5, 1))
    assert ax.twin() is ax
    assert ax.twin(y=right_) is right_
    assert ax.twin(x=top_.x) is top_
    assert ax.twin(x=ax.x, y=ax.y) is ax
    chained = right_.twiny(x_range=(0, 2, 1))
    assert ax.twin(x=chained, y=right_) is chained
    assert len(ax.twins) == 3


def test_pa3_errors():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    other = axes()
    with pytest.raises(ValueError, match="x"):
        ax.twin(x=other.x)
    with pytest.raises(ValueError, match="y"):
        ax.twin(y=other)
    with pytest.raises(ValueError, match="x"):
        ax.twin(x=right_.y)
    with pytest.raises(ValueError, match="y"):
        ax.twin(y=ax.x)
    mirror = ax.x.mirror()
    with pytest.raises(ValueError, match="x"):
        ax.twin(x=mirror)
    secondary = ax.secondary_xaxis()
    with pytest.raises(ValueError, match="x"):
        ax.twin(x=secondary)
    with pytest.raises(TypeError, match="x"):
        ax.twin(x=3)


# --- PA-4, PA-5 -----------------------------------------------------------------------


def four_corners():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    top_ = ax.twiny(x_range=(0, 5, 1))
    return ax, right_, top_, ax.twin(x=top_, y=right_)


def test_pa4_a_pair_draws_nothing_and_is_a_twin():
    ax = axes()
    right_ = ax.twinx(y_range=(0, 1))
    top_ = ax.twiny(x_range=(0, 5, 1))
    before = points(ax)
    corner = ax.twin(x=top_, y=right_)
    assert points(ax) == before
    assert corner.parent is ax and ax.twins == (right_, top_, corner)


def test_pa4_a_pair_maps_through_its_two_axes():
    ax, _, _, corner = four_corners()
    for x, y in [(0, 0), (5, 1), (2.5, 0.5), (1, 0.8)]:
        np.testing.assert_allclose(corner.c2p(x, y), ax.c2p(2 * x, 100 * y), atol=1e-9)
        np.testing.assert_allclose(
            corner.p2c(ax.c2p(2 * x, 100 * y))[:2], [x, y], atol=1e-9
        )


def test_pa4_artists_bind_to_the_pair():
    ax, right_, top_, corner = four_corners()
    curve = corner.plot(lambda x: x / 5)
    dots = corner.scatter([2.5], [0.5])
    assert curve in corner.artists
    assert curve not in ax.artists and curve not in right_.artists
    assert curve not in top_.artists
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(5, 50), atol=1e-9)


def test_pa4_artists_follow_each_axis_range():
    ax, right_, top_, corner = four_corners()
    curve = corner.plot(lambda x: x / 5, x_range=(0, 5))
    ax.set_x_range((0, 20))
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(20, 100), atol=1e-6)
    top_.set_x_range((0, 10))
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(10, 100), atol=1e-6)
    right_.set_y_range((0, 2))
    np.testing.assert_allclose(np.asarray(curve.points)[-1], ax.c2p(10, 50), atol=1e-6)


def test_pa4_an_animated_top_range_moves_the_pair_on_every_frame():
    ax, _, top_, corner = four_corners()
    mark = corner.scatter([1.0], [0.5])

    def construct(scene: Scene) -> None:
        scene.add(ax, mark)
        scene.play(top_.animate.set_x_range((0, 2)), run_time=1)

    frames = probe(
        construct,
        lambda: (
            float(mark[0].get_center()[0]),
            float(corner.c2p(1, 0.5)[0]),
            float(top_.x.range.value[1]),
        ),
    )
    for at, expected, _ in frames:
        assert at == pytest.approx(expected, abs=1e-6)
    assert len({end for *_, end in frames}) > 2
    np.testing.assert_allclose(mark[0].get_center(), ax.c2p(5, 50), atol=1e-6)


def test_pa4_the_pair_follows_the_roots_geometry():
    ax, _, _, corner = four_corners()
    curve = corner.plot(lambda x: x / 5)
    end = np.asarray(curve.points)[-1].copy()
    ax.shift(UP)
    np.testing.assert_allclose(np.asarray(curve.points)[-1], end + UP, atol=1e-6)


def test_pa4_the_legend_and_the_cycle():
    ax, right_, _, corner = four_corners()
    curves = [
        ax.plot(lambda x: 10 * x, label="left"),
        corner.plot(lambda x: x / 5, label="corner"),
        right_.plot(lambda x: x / 10, label="right"),
    ]
    assert ax.get_legend_handles_labels()[1] == ["left", "corner", "right"]
    assert [c.get_color() for c in curves] == list(mp.COLOR_CYCLE[:3])


def test_pa4_a_range_call_on_the_pair_changes_the_shared_axis():
    ax, _, top_, corner = four_corners()
    corner.set_x_range((0, 2))
    np.testing.assert_array_equal(top_.x.range.value, [0, 2])
    np.testing.assert_array_equal(ax.x.range.value, [0, 10])


def test_pa4_a_copy_keeps_the_pair():
    ax, _, _, corner = four_corners()
    corner.plot(lambda x: x / 5)
    copied = ax.copy()
    assert len(copied.twins) == 3
    right_, top_, pair = copied.twins
    assert pair.x is top_.x and pair.y is right_.y and pair.parent is copied


def test_pa5_every_pair_of_two_x_and_three_y_axes():
    ax = axes()
    near = ax.twinx(y_range=(0, 1))
    far = ax.twinx(y_range=(0, 1000))
    top_ = ax.twiny(x_range=(0, 5, 1))
    systems = set()
    for xs, span_x in ((ax, 10), (top_, 5)):
        for ys, span_y in ((ax, 100), (near, 1), (far, 1000)):
            pair = ax.twin(x=xs, y=ys)
            assert pair.x is xs.x and pair.y is ys.y
            np.testing.assert_allclose(
                pair.c2p(span_x / 2, span_y / 4), ax.c2p(5, 25), atol=1e-9
            )
            systems.add(id(pair))
    assert len(systems) == 6


# --- SA -------------------------------------------------------------------------------


def celsius(**kwargs):
    return mp.Axes(
        x_range=(0, 100, 20), y_range=(0, 1, 0.5), x_length=8, y_length=4, **kwargs
    )


def test_sa1_a_secondary_axis_is_an_axis_on_its_side():
    ax = framed()
    secondary = ax.secondary_xaxis()
    assert isinstance(secondary, Axis) and secondary in ax.get_family()
    assert line_y(secondary) == pytest.approx(top(ax), abs=1e-9)
    assert len(secondary.numbers) > 0
    side = ax.secondary_yaxis()
    assert float(np.asarray(side.line.points)[:, 0].mean()) == pytest.approx(
        right(ax), abs=1e-9
    )
    unnumbered = ax.secondary_xaxis("bottom", include_numbers=False, offset=0.5)
    assert len(unnumbered.numbers) == 0
    assert line_y(unnumbered) == pytest.approx(float(ax.c2p(0, 0)[1]) - 0.5, abs=1e-9)


@pytest.mark.parametrize(
    ("method", "location"),
    [("secondary_xaxis", "left"), ("secondary_yaxis", "top")],
)
def test_sa1_a_wrong_location_raises(method, location):
    with pytest.raises(ValueError, match="location"):
        getattr(axes(), method)(location)


def test_sa2_celsius_and_kelvin():
    ax = celsius()
    secondary = ax.secondary_xaxis("top", functions=KELVIN)
    secondary.set_locator(mp.MultipleLocator(20))
    values = [280, 300, 320, 340, 360]
    np.testing.assert_allclose(secondary.get_tick_range(), values, atol=1e-9)
    expected = [float(ax.c2p(v - 273.15, 0)[0]) for v in values]
    np.testing.assert_allclose(tick_xs(secondary), expected, atol=1e-9)
    numbers = sorted(float(n.number) for n in secondary.numbers)
    np.testing.assert_allclose(numbers, values, atol=1e-9)


def test_sa2_nanometres_and_electronvolts_decrease_along_the_axis():
    ax = mp.Axes(x_range=(400, 800, 100), y_range=(0, 1, 0.5), x_length=8, y_length=4)
    secondary = ax.secondary_xaxis("top", functions=ELECTRONVOLT)
    secondary.set_locator(mp.MultipleLocator(0.5))
    values = sorted(secondary.get_tick_range())
    np.testing.assert_allclose(values, [2.0, 2.5, 3.0], atol=1e-9)
    by_value = dict(
        zip(np.round(secondary.get_tick_range(), 9), tick_xs(secondary), strict=True)
    )
    assert by_value[3.0] < by_value[2.5] < by_value[2.0]
    for v in values:
        assert by_value[v] == pytest.approx(float(ax.c2p(HC / v, 0)[0]), abs=1e-9)


def test_sa2_the_identity_and_the_default_locator():
    ax = celsius()
    secondary = ax.secondary_xaxis()
    assert isinstance(secondary.locator, mp.MaxNLocator)
    values = secondary.get_tick_range()
    assert len(values) > 2
    expected = [float(ax.c2p(v, 0)[0]) for v in values]
    np.testing.assert_allclose(tick_xs(secondary), expected, atol=1e-9)


def test_sa2_a_log_base():
    ax = mp.Axes(x_range=(1, 1000), y_range=(0, 1, 0.5), x_scale="log")
    secondary = ax.secondary_xaxis(functions=(lambda x: 10 * x, lambda v: v / 10))
    secondary.set_locator(mp.FixedLocator([100.0, 1000.0]))
    np.testing.assert_allclose(
        tick_xs(secondary), [ax.c2p(10, 0)[0], ax.c2p(100, 0)[0]], atol=1e-9
    )


@pytest.mark.parametrize(
    "functions",
    [
        (lambda x: x**2, np.sqrt),  # not monotonic on (-2, 2)
        (lambda x: 2 * x, lambda v: v),  # not each other's inverse
        (lambda x: 0 * x, lambda v: v),  # constant
    ],
)
def test_sa3_bad_functions_raise(functions):
    ax = mp.Axes(x_range=(-2, 2, 1), y_range=(0, 1, 0.5))
    with pytest.raises(ValueError, match="functions"):
        ax.secondary_xaxis(functions=functions)


def test_sa3_a_later_range_is_checked_and_refused_whole():
    ax = mp.Axes(x_range=(1, 2, 0.5), y_range=(0, 1, 0.5))
    ax.secondary_xaxis(functions=(lambda x: x**2, np.sqrt))
    with pytest.raises(ValueError, match="functions"):
        ax.set_x_range((-2, 2))
    np.testing.assert_array_equal(ax.x.range.value, [1, 2])


def test_sa4_an_animated_range_carries_the_secondary_axis():
    ax = celsius()
    secondary = ax.secondary_xaxis(functions=KELVIN)
    secondary.set_locator(mp.MultipleLocator(20))

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(ax.animate.set_x_range((0, 200)), run_time=1)

    frames = probe(
        construct,
        lambda: (
            secondary.get_tick_range().tolist(),
            tick_xs(secondary).tolist(),
            [float(ax.c2p(v - 273.15, 0)[0]) for v in secondary.get_tick_range()],
        ),
    )
    for _, at, expected in frames:
        np.testing.assert_allclose(at, expected, atol=1e-6)
    assert len({len(values) for values, *_ in frames}) > 1
    assert max(secondary.get_tick_range()) == pytest.approx(460, abs=1e-9)


def drawn_numbers(axis) -> list[tuple[float, float]]:
    """The value and the centre x of every number of the axis that has points."""
    return [
        (float(n.number), float(n.get_center()[0]))
        for n in axis.numbers
        if any(len(m.points) for m in n.get_family())
    ]


def test_sa4_the_numbers_follow_an_animated_range_on_every_frame():
    ax = celsius()
    secondary = ax.secondary_xaxis(functions=KELVIN)
    secondary.set_locator(mp.MultipleLocator(20))

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(ax.animate.set_x_range((0, 200)), run_time=1)

    frames = probe(
        construct,
        lambda: [
            (at, float(ax.c2p(value - 273.15, 0)[0]))
            for value, at in drawn_numbers(secondary)
        ],
    )
    for frame in frames:
        assert len(frame) >= 3
        for at, expected in frame:
            assert at == pytest.approx(expected, abs=1e-6)
    values = sorted(value for value, _ in drawn_numbers(secondary))
    assert values[-1] == pytest.approx(460, abs=1e-9)


@pytest.mark.parametrize("kind", ["secondary", "mirror"])
def test_sa4_mi2_new_parts_are_rendered_on_every_frame(kind):
    """A decoration whose ticks change during an animated range draws every part it
    has: the renderer's members hold each of its leaves with points."""
    ax = mp.Axes(
        x_range=(400, 800, 100),
        y_range=(0, 1, 0.25),
        axis_config={"include_numbers": True},
    )
    ax.x.set_position("bottom")
    if kind == "secondary":
        decoration = ax.secondary_xaxis("top", functions=ELECTRONVOLT)
    else:
        decoration = ax.x.mirror(include_numbers=True)
    decoration.set_locator(mp.MaxNLocator(6))

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(ax.animate.set_x_range((500, 600)), run_time=1)

    def record() -> tuple[int, int]:
        rendered = {id(m) for m in ax.family_members_with_points()}
        parts = [
            m for m in decoration.get_family() if len(m.points) and not m.submobjects
        ]
        return len(parts), sum(id(m) in rendered for m in parts)

    for parts, rendered in probe(construct, record):
        assert rendered == parts > 0


def test_sa4_a_border_axis_without_a_tip_and_ticks_in():
    ax = framed()
    secondary = ax.secondary_xaxis()
    assert secondary.tip is None
    below, above = tick_side(secondary)
    assert below > 0 and above == pytest.approx(0, abs=1e-9)


def test_sa5_styled_apart_from_its_base():
    ax = framed()
    secondary = ax.secondary_xaxis()
    secondary.set_color(RED)
    secondary.set_ticks_direction(mp.TickDirection.OUT)
    assert secondary.line.get_color() == RED and ax.x.line.get_color() != RED
    below, above = tick_side(secondary)
    assert above > 0 and below == pytest.approx(0, abs=1e-9)
    below, above = tick_side(ax.x)
    assert above > 0 and below == pytest.approx(0, abs=1e-9)


# --- MI -------------------------------------------------------------------------------


def test_mi1_a_numbered_mirror():
    ax = framed()
    before = len(ax.x.numbers)
    mirror = ax.x.mirror(include_numbers=True)
    assert len(mirror.numbers) > 0
    assert len(ax.x.numbers) == before
    assert len(ax.y.mirror().numbers) == 0


def test_mi2_a_mirror_styled_alone_still_follows_what_it_did_not_set():
    ax = framed()
    mirror = ax.x.mirror()
    length = tick_length(ax.x)
    mirror.set_tick_style(length=0.4)
    assert tick_length(mirror) == pytest.approx(0.4)
    assert tick_length(ax.x) == pytest.approx(length)
    ax.x.set_tick_style(width=4)
    assert mirror.ticks[0].get_stroke_width() == pytest.approx(4)
    mirror.set_locator(mp.MultipleLocator(5))
    np.testing.assert_allclose(mirror.get_tick_range()[-2:], [5, 10])
    assert len(mirror.get_tick_range()) <= 3
    assert len(ax.x.get_tick_range()) >= 10
    mirror.set_ticks_direction(mp.TickDirection.OUT)
    below, above = tick_side(mirror)
    assert above > 0 and below == pytest.approx(0, abs=1e-9)
    below, above = tick_side(ax.x)
    assert above > 0 and below == pytest.approx(0, abs=1e-9)
    ax.set_x_range((0, 5))
    np.testing.assert_array_equal(mirror.range.value, [0, 5])


# --- RP -------------------------------------------------------------------------------


def test_rp1_twiny_takes_the_place_of_the_top_mirror_in_either_order():
    ax = framed()
    mirror = ax.x.mirror()
    top_ = ax.twiny(x_range=(0, 5, 1))
    assert axes_on(ax, "top") == [top_.x]
    assert not drawn(mirror)
    later = framed()
    twin = later.twiny(x_range=(0, 5, 1))
    hidden = later.x.mirror()
    assert axes_on(later, "top") == [twin.x] and not drawn(hidden)


def test_rp1_the_mirror_comes_back_when_the_twin_moves_out():
    ax = framed()
    mirror = ax.x.mirror()
    mirror.set_color(RED)
    top_ = ax.twiny(x_range=(0, 5, 1))
    top_.x.set_position("top", offset=0.5)
    assert drawn(mirror) and mirror.line.get_color() == RED
    assert axes_on(ax, "top") == [mirror]


def test_rp1_twinx_and_a_secondary_axis_too():
    ax = framed()
    ax.y.mirror()
    twin = ax.twinx(y_range=(0, 1))
    assert axes_on(ax, "right") == [twin.y]
    other = framed()
    other.x.mirror()
    secondary = other.secondary_xaxis()
    assert axes_on(other, "top") == [secondary]


def test_rp1_a_themes_box_follows_the_rule():
    ax = axes(theme="origin")
    twin = ax.twinx(y_range=(0, 1))
    assert axes_on(ax, "right") == [twin.y]
    assert len(axes_on(ax, "top")) == 1
