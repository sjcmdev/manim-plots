"""The lifecycle under Manim's animations, and Cairo's static background (F-903, F-905,
F-907, F-915, F-916, F-918).

Rows AN-1 to AN-7 and SY-1 to SY-4 of `docs/acceptance/09-leaves-context-frame.md`. The
oracle is a plain twin animated by the same animation in the same play, or the curve's
own state before the animation. Task 11's F-906 matrix covers every animation; these
cover the mechanism.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import (
    ORIGIN,
    PI,
    RIGHT,
    Circle,
    Create,
    Dot,
    FadeOut,
    Indicate,
    Rotate,
    Scene,
    Square,
    Transform,
    Uncreate,
    Wiggle,
    tempconfig,
)
from manim.animation.animation import prepare_animation

import manim_plots as mp

from .helpers import RUN, plain, probe


def system():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    return ax, ax.plot(np.sin)


def rebuilt_after_a_range_change(ax, curve) -> bool:
    before = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    return not np.array_equal(curve.points, before)


def test_an1_create_draws_frame_by_frame_as_manim_and_ends_attached():
    ax, curve = system()
    twin = plain(curve)

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(Create(curve), Create(twin))

    frames = probe(construct, lambda: (np.array(curve.points), np.array(twin.points)))
    assert len(frames) >= 5
    for ours, theirs in frames:
        np.testing.assert_allclose(ours, theirs, atol=1e-9)
    assert rebuilt_after_a_range_change(ax, curve)


def test_an2_create_after_uncreate_draws_the_current_curve():
    ax, curve = system()
    original = np.array(curve.points, copy=True)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(Uncreate(curve))
        scene.play(Create(curve))

    probe(construct, lambda: None)
    np.testing.assert_allclose(curve.points, original, atol=1e-9)


def test_an3_fade_out_leaves_the_curve_removed_until_refresh():
    ax, curve = system()

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(FadeOut(curve))

    probe(construct, lambda: None)
    frozen = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    np.testing.assert_array_equal(curve.points, frozen)
    curve.refresh()
    assert not np.array_equal(curve.points, frozen)


def test_an4_a_plain_target_leaves_the_curve_shaped():
    ax, curve = system()
    twin = plain(curve)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, twin)
        scene.play(Transform(curve, Circle()), Transform(twin, Circle()))

    probe(construct, lambda: None)
    np.testing.assert_allclose(curve.points, twin.points, atol=1e-9)
    ax.shift(RIGHT)
    np.testing.assert_allclose(curve.points, twin.shift(RIGHT).points, atol=1e-9)
    shaped = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    np.testing.assert_allclose(curve.points, shaped, atol=1e-12)


def angle_of(ax) -> float:
    start, end = ax.x_axis.line.get_start(), ax.x_axis.line.get_end()
    direction = end - start
    return float(np.arctan2(direction[1], direction[0]))


def rotated(points: np.ndarray, angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.asarray(points @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]))


def test_an5_a_rotation_of_the_system_turns_the_curve_on_every_frame():
    ax, curve = system()
    original = np.array(curve.points, copy=True)

    def construct(scene: Scene) -> None:
        scene.add(curve, ax)
        scene.play(Rotate(ax, PI / 2, about_point=ORIGIN))

    frames = probe(construct, lambda: (angle_of(ax), np.array(curve.points)))
    for angle, points in frames:
        np.testing.assert_allclose(points, rotated(original, angle), atol=1e-6)
    np.testing.assert_allclose(curve.points, rotated(original, PI / 2), atol=1e-6)


def test_an5_a_temporary_animation_of_the_system_leaves_the_curve_still():
    ax, curve = system()
    original = np.array(curve.points, copy=True)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(Indicate(ax))

    for points in probe(construct, lambda: np.array(curve.points)):
        np.testing.assert_allclose(points, original, atol=1e-9)


def test_an6_the_curve_rides_along_with_animate_shift():
    ax, curve = system()
    original = np.array(curve.points, copy=True)
    start = ax.x_axis.line.get_center().copy()

    def construct(scene: Scene) -> None:
        scene.add(curve, ax)
        scene.play(ax.animate.shift(RIGHT))

    frames = probe(
        construct, lambda: (ax.x_axis.line.get_center() - start, np.array(curve.points))
    )
    assert any(0.1 < d[0] < 0.9 for d, _ in frames)
    for displacement, points in frames:
        np.testing.assert_allclose(points, original + displacement, atol=1e-9)
    np.testing.assert_allclose(curve.points, original + RIGHT, atol=1e-9)


def test_an7_wiggle_ends_where_it_started_and_attached():
    ax, curve = system()
    original = np.array(curve.points, copy=True)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(Wiggle(curve))

    probe(construct, lambda: None)
    np.testing.assert_allclose(curve.points, original, atol=1e-9)
    assert rebuilt_after_a_range_change(ax, curve)


# --- SY: the static background --------------------------------------------------------


@pytest.mark.parametrize(
    "curve_first", [True, False], ids=["curve first", "system first"]
)
def test_sy1_an_unrelated_play_leaves_the_plot_in_the_background(curve_first):
    with tempconfig(RUN):
        scene = Scene()
        ax, curve = system()
        square = Square()
        scene.add(*([curve, ax] if curve_first else [ax, curve]), square)
        moving = scene.get_moving_mobjects(Rotate(square, PI))
        assert curve not in moving
        assert not set(map(id, ax.get_family())) & set(map(id, moving))


def test_sy2_animating_the_system_moves_a_curve_added_before_it():
    with tempconfig(RUN):
        scene = Scene()
        ax, curve = system()
        scene.add(curve, ax)
        moving = scene.get_moving_mobjects(prepare_animation(ax.animate.shift(RIGHT)))
        assert moving and moving[0] is curve


def test_sy2_a_live_function_keeps_its_plot_moving():
    with tempconfig(RUN):
        scene = Scene()
        ax, curve = system()
        ax.x.range.bind(lambda: (-3, 3))
        square = Square()
        scene.add(curve, ax, square)
        assert curve in scene.get_moving_mobjects(Rotate(square, PI))


def test_sy3_a_frozen_wait_rebuilds_nothing():
    ax, curve = system()

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.wait(1)

    ids = probe(construct, lambda: id(curve.points))
    assert len(set(ids)) <= 1


def test_sy4_a_callable_range_is_read_once_per_frame():
    ax, curve = system()
    calls: list[int] = []

    def live_range():
        calls.append(1)
        return (-3, 3)

    ax.x.range.bind(live_range)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(Rotate(Dot(), PI), run_time=1)

    counts = probe(construct, lambda: len(calls))
    per_frame = np.diff(counts)
    assert (per_frame == 1).all(), counts
