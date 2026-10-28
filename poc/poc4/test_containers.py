import numpy as np
import pytest
from manim import DOWN, PI, RIGHT, UP, Dot, Group, Rotate, ValueTracker, VGroup

from poc4.model import System, error, record, source
from poc4.scene import ProbeScene, count_interpolation
from poc4.test_geometry import plain, wave

CASES = [
    "shift",
    "rotate",
    "scale",
    "apply_matrix",
    "apply_function",
    "move_to",
    "next_to",
    "to_corner",
    "arrange",
    "Group",
    "nested",
    "two_systems",
]


@pytest.mark.parametrize("kind", CASES)
def test_k3_foreign_containers(kind):
    ax = System(33)
    tracker = ValueTracker(1)
    curve = ax.plot(samples=41, tracker=tracker)
    other_ax = System(33)
    second = (other_ax if kind == "two_systems" else ax).plot(
        np.cos, samples=41, tracker=tracker
    )
    dot = Dot([1, 1, 0])
    if kind == "nested":
        group = VGroup(VGroup(ax), curve)
    elif kind == "two_systems":
        group = VGroup(ax, curve, second)
    elif kind == "arrange":
        group = VGroup(curve, second)
    else:
        group = (Group if kind == "Group" else VGroup)(curve, dot)
    native = plain(group)
    native_curve = (
        native[-1]
        if kind == "nested"
        else native[1]
        if kind == "two_systems"
        else native[0]
    )
    initial_native = native_curve.points.copy()
    second_initial = second.points.copy()
    pivot = native.get_center().copy()

    def operation(mob):
        if kind == "rotate":
            return mob.rotate(0.4, about_point=pivot)
        if kind == "scale":
            return mob.scale(0.7, about_point=pivot)
        if kind == "apply_matrix":
            return mob.apply_matrix([[1, 0.3], [0.2, 1]])
        if kind == "apply_function":
            return mob.apply_function(wave)
        if kind == "move_to":
            return mob.move_to(UP)
        if kind == "next_to":
            return mob.next_to(Dot(2 * RIGHT), DOWN)
        if kind == "to_corner":
            return mob.to_corner(UP + RIGHT)
        if kind == "arrange":
            return mob.arrange(DOWN)
        return mob.shift(UP)

    operation(native)
    operation(group)
    immediate = error(curve.points, native_curve.points)
    second_native = (
        native[2] if kind == "two_systems" else native[1] if kind == "arrange" else None
    )
    second_error = (
        error(second.points, second_native.points) if second_native is not None else 0
    )
    ax.set_x_range([-2.5, 2.5])
    tracker.set_value(1.6)
    changed = source(41) * [1.2, 1.6, 1]
    expected = plain(curve).set_points(changed)
    if kind in {"rotate", "scale", "apply_matrix", "apply_function"}:
        operation(expected)
    else:
        expected.shift(native_curve.points[0] - initial_native[0])
    rebuilt = error(curve.points, expected.points)
    second_rebuilt = 0
    if second_native is not None:
        changed_second = source(41, np.cos) * [
            1 if kind == "two_systems" else 1.2,
            1.6,
            1,
        ]
        expected_second = changed_second + (second_native.points[0] - second_initial[0])
        second_rebuilt = error(second.points, expected_second)
    record(
        f"k3_static_{kind}",
        {
            "immediate_error": immediate,
            "rebuild_error": rebuilt,
            "second_immediate_error": second_error,
            "second_rebuild_error": second_rebuilt,
            "placement_nodes": len(curve.placement),
            "writer_events": curve.writer_events,
        },
    )
    assert max(immediate, rebuilt, second_error, second_rebuilt) < 1e-9
    assert error(curve.points, initial_native) > 0.1


@pytest.mark.parametrize("kind", ["animate", "Rotate"])
def test_k3_animated_foreign_container(kind):
    ax = System(9)
    curve = ax.plot(samples=41)
    group = VGroup(curve, Dot([1, 1, 0]))
    native = plain(group)
    initial_center = native.get_center().copy()
    scene, control = ProbeScene(), ProbeScene()
    scene.add(group)
    control.add(native)
    actual, expected = [], []
    scene.renderer.observe = lambda _s: actual.append(curve.points.copy()) or {}
    control.renderer.observe = lambda _s: expected.append(native[0].points.copy()) or {}

    def make(mob):
        return (
            mob.animate.shift(UP).build()
            if kind == "animate"
            else Rotate(mob, about_point=initial_center)
        )

    anim = make(group)
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    control.play(make(native), run_time=0.6)
    frames = max(error(a, b) for a, b in zip(actual, expected, strict=True))
    endpoint = error(curve.points, native[0].points)
    ax.set_x_range([-2.5, 2.5])
    expected_data = plain(curve).set_points(source(41) * [1.2, 1, 1])
    if kind == "animate":
        expected_data.shift(UP)
    else:
        expected_data.rotate(PI, about_point=initial_center)
    rebuilt = error(curve.points, expected_data.points)
    record(
        f"k3_animation_{kind}",
        {
            "frame_error": frames,
            "immediate_error": endpoint,
            "rebuild_error": rebuilt,
            "calls": len(calls),
            "frames": len(actual),
        },
    )
    assert max(frames, endpoint, rebuilt) < 1e-9 and len(calls) > 2


def test_k3_raw_write_keeps_v2_policy():
    ax = System(9)
    curve = ax.plot(samples=10)
    initial = curve.points.copy()
    curve.points += UP
    assert error(curve.points, initial) == 0
