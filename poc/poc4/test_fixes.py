import numpy as np
from manim import (
    DOWN,
    PI,
    RIGHT,
    UP,
    FadeOut,
    Line,
    MoveAlongPath,
    PhaseFlow,
    Transform,
    VGroup,
)

from poc4.model import METRICS, System, error, record
from poc4.scene import ProbeScene, count_interpolation
from poc4.test_geometry import plain


def test_k4_fadeout_cleanup():
    ax = System(9)
    curve = ax.plot(samples=10)
    native = plain(curve)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve)
    control.add(native)
    scene.play(FadeOut(curve, shift=DOWN), run_time=0.6)
    control.play(FadeOut(native, shift=DOWN), run_time=0.6)
    maximum = error(curve.points, native.points)
    record("k4_fadeout", {"error": maximum})
    assert maximum < 1e-9


def test_k4_larger_target():
    ax = System(9)
    curve, target = ax.plot(samples=10), ax.plot(np.cos, samples=50)
    native, native_target = plain(curve), plain(target)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve)
    control.add(native)
    animation = Transform(curve, target)
    calls = count_interpolation(animation)
    scene.play(animation, run_time=0.6)
    control.play(Transform(native, native_target), run_time=0.6)
    maximum = error(curve.points, native.points)
    record(
        "k4_larger_target",
        {"error": maximum, "points": len(curve.points), "calls": len(calls)},
    )
    assert maximum < 1e-9 and len(curve.points) == 196 and len(calls) > 2


def test_k4_local_placement():
    ax = System(9)
    curve = ax.plot(samples=10)
    native_ax, native = plain(ax), plain(curve)
    curve.shift(UP)
    native.shift(UP)
    ax.rotate(PI / 2)
    VGroup(native_ax, native).rotate(PI / 2)
    maximum = error(curve.points, native.points)
    record("k4_local", {"error": maximum})
    assert maximum < 1e-9


def test_k4_no_offplane_probe():
    ax = System(9)
    native = VGroup(*(plain(m) for m in ax.submobjects[1:]))
    center = error(ax.get_center(), native.get_center())
    ax.rotate(0.4, axis=RIGHT)
    native.rotate(0.4, axis=RIGHT)
    pivot = error(ax[1].points, native[0].points)
    record("k4_bounds", {"center_error": center, "pivot_error": pivot})
    assert center < 1e-9 and pivot < 1e-9


def test_k4_placement_growth():
    rows = []
    for kind in ["MoveAlongPath", "PhaseFlow"]:
        ax = System(9)
        curve = ax.plot(samples=10)
        native = plain(curve)
        scene, control = ProbeScene(), ProbeScene()
        scene.add(curve)
        control.add(native)

        def make(mob, kind=kind):
            if kind == "MoveAlongPath":
                return MoveAlongPath(mob, Line(-RIGHT, RIGHT))
            return PhaseFlow(lambda p: 0.1 * p + UP, mob)

        anim = make(curve)
        calls = count_interpolation(anim)
        scene.play(anim, run_time=2)
        control.play(make(native), run_time=2)
        maximum = error(curve.points, native.points)
        rows.append(
            {
                "kind": kind,
                "nodes": len(curve.placement),
                "error": maximum,
                "calls": len(calls),
                "frames": len(scene.renderer.frames),
            }
        )
    record("k4_growth", rows)
    assert all(row["error"] < 1e-9 for row in rows)
    assert rows[0]["nodes"] == 1
    # Arbitrary callbacks are non-affine facts, even for this affine vector field.
    assert rows[1]["nodes"] > 1


def test_k4_cached_weights():
    ax = System(33)
    ax.frame.force_bilinear = True
    curve = ax.plot(samples=2000)
    curve.rebuild()
    METRICS.clear()
    for _ in range(10):
        ax.shift(RIGHT * 0.01)
        curve.rebuild()
    count = METRICS["weight_builds"]
    record("k4_weights", {"weight_builds_for_ten_frame_changes": count})
    assert hasattr(curve, "_weights") and count == 0
    assert error(curve.points, curve.source + RIGHT * 0.1) < 1e-9


def test_k4_nonaffine_local_conjugation():
    from poc4.test_geometry import wave

    ax = System(33)
    curve = ax.plot(samples=41)
    ax.apply_function(wave)
    before = curve.points.copy()
    data = curve.data_points()
    analytic = np.array([wave(p) for p in data]) + RIGHT
    analytic_local = analytic.copy()
    analytic_local[:, 1] -= 0.3 * np.sin(2 * analytic_local[:, 0])
    curve.shift(RIGHT)
    local_error = error(curve._local, analytic_local)
    interior = np.abs(analytic_local[:, 0]) <= 3
    interior_error = error(curve._local[interior], analytic_local[interior])
    immediate = error(curve.points, before + RIGHT)
    native = plain(curve)
    ax.rotate(PI / 2, about_point=[0, 0, 0])
    native.rotate(PI / 2, about_point=[0, 0, 0])
    rotated = error(curve.points, native.points)
    record(
        "k4_nonaffine_local",
        {
            "analytic_local_error": local_error,
            "interior_analytic_local_error": interior_error,
            "immediate_scene_error": immediate,
            "later_rotation_error": rotated,
        },
    )
    assert max(immediate, rotated) < 1e-9 and local_error > 1e-4
