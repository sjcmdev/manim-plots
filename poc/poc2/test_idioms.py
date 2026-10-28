import gc
from time import perf_counter

import numpy as np
import pytest
from manim import (
    LEFT,
    PI,
    RIGHT,
    UP,
    Create,
    Dot,
    MoveAlongPath,
    ValueTracker,
    VGroup,
    always_redraw,
    linear,
)

from poc2.model import System, error, record, source
from poc2.scene import ProbeScene, count_interpolation
from poc2.test_geometry import plain


@pytest.mark.parametrize("idiom", ["always_redraw", "become"])
def test_g4_redraw_registry(idiom):
    ax = System(n=9)
    a = ValueTracker(1)

    def factory():
        return ax.plot(lambda x: a.get_value() * np.sin(x), samples=41)

    if idiom == "always_redraw":
        graph = always_redraw(factory)
    else:
        graph = factory()
        graph.add_updater(lambda m: m.become(factory()))

    def native_factory():
        return plain(factory())

    if idiom == "always_redraw":
        native = always_redraw(native_factory)
    else:
        native = native_factory()
        native.add_updater(lambda m: m.become(native_factory()))
    scene = ProbeScene()
    scene.add(ax, graph, native)
    errors = []
    registry = []

    def observe(_scene):
        expected = source(41) * [1, a.get_value(), 1]
        errors.append(error(graph.points, expected))
        assert error(graph.points, native.points) < 1e-9
        gc.collect()
        registry.append(len(ax.artists))
        return {}

    scene.renderer.observe = observe
    animation = a.animate(rate_func=linear).set_value(2).build()
    calls = count_interpolation(animation)
    scene.play(animation, run_time=0.6)
    gc.collect()
    record(
        f"g4_{idiom}",
        {
            "max_error": max(errors),
            "calls": len(calls),
            "registry_per_frame": registry,
            "registry_final": len(ax.artists),
        },
    )
    assert max(errors) < 1e-9 and len(ax.artists) == 1 and len(calls) > 2


@pytest.mark.parametrize("split", [False, True])
def test_g4_path_queries(split):
    ax = System(n=9)
    curve = ax.plot((lambda x: 1 / x) if split else np.sin, samples=100, split=split)
    native = plain(curve)
    dot, native_dot = Dot(), Dot()
    endpoints = [
        error(curve.get_end(), native.get_end()),
        error(curve.point_from_proportion(0.5), native.point_from_proportion(0.5)),
    ]
    dot.move_to(curve.get_end())
    assert error(dot.get_center(), curve.get_end()) < 1e-9
    scene = ProbeScene()
    scene.add(curve, dot)
    positions = []
    scene.renderer.observe = lambda _s: positions.append(dot.get_center().copy()) or {}
    anim = MoveAlongPath(dot, curve)
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    control = ProbeScene()
    control.add(native, native_dot)
    native_positions = []
    control.renderer.observe = lambda _s: (
        native_positions.append(native_dot.get_center().copy()) or {}
    )
    control.play(MoveAlongPath(native_dot, native), run_time=0.6)
    maximum = error(positions, native_positions)
    record(
        f"g4_path_{split}",
        {
            "query_errors": endpoints,
            "path_error": maximum,
            "subpaths": len(curve.get_subpaths()),
            "calls": len(calls),
        },
    )
    assert max(endpoints) < 1e-9 and maximum < 1e-9 and len(calls) > 2
    assert len(curve.get_subpaths()) == (2 if split else 1)


def test_g4_copy_ownership():
    rows = []
    for reverse in [False, True]:
        ax = System(n=9)
        curve = ax.plot()
        alone = curve.copy()
        assert alone.system is ax and alone.source is curve.source
        group = VGroup(*([curve, ax] if reverse else [ax, curve])).copy()
        copied_ax = group[1 if reverse else 0]
        copied_curve = group[0 if reverse else 1]
        assert copied_curve.system is copied_ax
        assert copied_curve.source is curve.source
        assert len(copied_ax.artists) == 1
        rows.append(
            {
                "reverse": reverse,
                "copied_registry": len(copied_ax.artists),
                "original_registry": len(ax.artists),
            }
        )
    record("g4_copy", rows)


def test_g4_tracker_dot_parenting_and_simultaneous():
    ax = System(n=9)
    curve = ax.plot(samples=41)
    dot = Dot()
    t = ValueTracker(0.8)
    dot.add_updater(lambda d: d.move_to(ax.c2p(t.get_value(), 0)))
    scene = ProbeScene()
    scene.add(curve, ax, dot)
    scene.renderer.observe = lambda _s: {
        "error": error(dot.get_center(), ax.c2p(0.8, 0))
    }
    rotation = ax.animate.rotate(PI / 6).build()
    calls = count_interpolation(rotation)
    scene.play(rotation, run_time=0.6)
    maximum = max(f["error"] for f in scene.renderer.frames)
    assert maximum < 1e-9 and len(calls) > 2

    ax = System(n=9)
    curve = ax.plot(samples=41)
    original = curve.points.copy()
    ax.add(curve)
    ax.shift(RIGHT)
    parenting_error = error(curve.points, original + RIGHT)
    scene = ProbeScene()
    scene.add(ax)
    before = [type(m).__name__ for m in scene.mobjects]
    scene.play(Create(curve), run_time=0.6)
    after = [type(m).__name__ for m in scene.mobjects]
    parent_retained_create = ax in scene.mobjects
    # Native control has the same parent/child relationship.
    native_ax = plain(ax)
    native_curve = native_ax.submobjects[-1]
    native_scene = ProbeScene()
    native_scene.add(native_ax)
    native_scene.play(Create(native_curve), run_time=0.6)
    native_parent_retained_create = native_ax in native_scene.mobjects
    scene.add(curve)
    explicit_splice = ax not in scene.mobjects
    native_scene.add(native_curve)
    native_explicit_splice = native_ax not in native_scene.mobjects

    ax = System(n=9)
    curve = ax.plot(samples=41)
    original = curve.points.copy()
    scene = ProbeScene()
    scene.add(ax, curve)
    simultaneous_flags = []
    original_suspend = curve.suspend_updating

    def suspend(recursive=True):
        simultaneous_flags.append(ax.updating_suspended)
        return original_suspend(recursive)

    curve.suspend_updating = suspend
    scene.play(ax.animate.shift(LEFT), curve.animate.shift(LEFT), run_time=0.6)
    displacement = np.mean(curve.points - original, axis=0)

    ax2 = System(n=9)
    curve2 = ax2.plot(samples=41)
    initial = curve2.points.copy()
    d = Dot()
    native_group = VGroup(plain(curve2), d.copy())
    native_group.shift(UP)
    VGroup(curve2, d).shift(UP)
    foreign_error = error(curve2.points, initial)
    record(
        "g4_interactions",
        {
            "tracker_dot_error": maximum,
            "parenting_shift_error": parenting_error,
            "scene_before_create": before,
            "scene_after_create": after,
            "parent_retained_create": parent_retained_create,
            "native_parent_retained_create": native_parent_retained_create,
            "explicit_add_splices": explicit_splice,
            "native_explicit_add_splices": native_explicit_splice,
            "simultaneous_displacement": displacement.tolist(),
            "axis_suspended_when_artist_starts": simultaneous_flags,
            "foreign_curve_displacement": np.mean(
                curve2.points - initial, axis=0
            ).tolist(),
            "native_foreign_displacement": np.mean(
                native_group[0].points - initial, axis=0
            ).tolist(),
            "foreign_curve_unchanged_error": foreign_error,
        },
    )
    assert parenting_error < 1e-9 and foreign_error == 0


@pytest.mark.parametrize("kind", ["axis", "tracker"])
@pytest.mark.parametrize("sync", [False, True])
def test_g5_static_freeze(kind, sync):
    ax = System(n=9, sync=sync)
    tracker = ValueTracker(1)
    curve = ax.plot(
        samples=101, tracker=tracker if kind == "tracker" else None, sync=sync
    )
    scene = ProbeScene()
    scene.add(curve, ax)
    differences = []

    def observe(scene):
        actual = scene.renderer.get_frame().copy()
        # A fresh full draw supplies current geometry without the static cache.
        camera = type(scene.camera)()
        camera.capture_mobjects(scene.mobjects)
        differences.append(int(np.count_nonzero(actual != camera.pixel_array)))
        return {}

    scene.renderer.observe = observe
    anim = (
        ax.animate.shift(RIGHT) if kind == "axis" else tracker.animate.set_value(2)
    ).build()
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6, rate_func=linear)
    middle = differences[2:-2]
    record(
        f"g5_{kind}_{sync}",
        {
            "pixel_differences": differences,
            "middle_max_difference": max(middle),
            "calls": len(calls),
        },
    )
    assert (max(middle) == 0) == sync


def test_g5_wait_overhead():
    rows = []
    for mode in ["none", "empty", "empty_dt"]:
        times, frames = [], []
        for _ in range(3):
            ax = System(n=9, sync=mode != "none")
            curve = ax.plot(sync=mode != "none")
            if mode == "empty_dt":
                curve.add_updater(lambda _mob, dt: None)
            scene = ProbeScene()
            scene.add(curve, ax)
            start = perf_counter()
            scene.wait(2)
            times.append(perf_counter() - start)
            frames.append(len(scene.renderer.frames))
        rows.append(
            {
                "mode": mode,
                "median_seconds": float(np.median(times)),
                "render_calls": frames,
            }
        )
    record("g5_wait", rows)


def test_g4_invisible_marker_bounds():
    ax = System(n=9)
    native = VGroup(*(plain(m) for m in ax.submobjects[1:]))
    before = error(ax.get_center(), native.get_center())
    ax.rotate(0.4, axis=RIGHT)
    native.rotate(0.4, axis=RIGHT)
    after = error(ax.submobjects[1].points, native[0].points)
    record("g4_marker_bounds", {"center_error": before, "rotated_axis_error": after})
    assert before == 0.5 and after > 0
