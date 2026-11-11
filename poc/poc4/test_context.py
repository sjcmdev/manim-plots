from time import perf_counter_ns

import numpy as np
import pytest
from manim import (
    PI,
    RIGHT,
    UP,
    AnimationGroup,
    Dot,
    Indicate,
    LaggedStart,
    MoveAlongPath,
    PhaseFlow,
    Rotate,
    ShowIncreasingSubsets,
    Succession,
    VGroup,
)

from poc4.context import animation_context, writer_context
from poc4.model import Derived, System, error, record
from poc4.scene import ProbeScene, count_interpolation
from poc4.test_animations import ARTIST_ANIMATIONS, AX_ANIMATIONS, animation
from poc4.test_geometry import plain


@pytest.mark.parametrize(
    "axis,names", [(True, AX_ANIMATIONS), (False, ARTIST_ANIMATIONS)]
)
def test_k1_animation_tables(axis, names):
    rows = []
    for name in names:
        ax = System(9)
        curve = ax.plot(samples=10)
        subject = ax if axis else curve
        target = ax.plot(np.cos, samples=10) if not axis else None
        scene = ProbeScene()
        scene.add(ax, curve)
        anim = animation(name, subject, target, axis=axis)
        calls = count_interpolation(anim)
        scene.play(anim, run_time=0.6)
        leaves = list(
            dict.fromkeys(
                [
                    *(ax.submobjects[1:] if axis else [curve]),
                    *[
                        leaf
                        for leaf in anim.mobject.get_family()
                        if isinstance(leaf, Derived)
                    ],
                ]
            )
        )
        events = [event for leaf in leaves for event in leaf.suspend_events]
        writers = [event for leaf in leaves for event in leaf.writer_events]
        row = {
            "name": name,
            "animation": type(anim).__name__,
            "suspends": events,
            "writes": writers,
            "frame_suspends": ax.frame.context_events,
            "calls": len(calls),
            "frames": len(scene.renderer.frames),
        }
        rows.append(row)
        assert all(event["animation"] is not None for event in events)
        assert all(event["animation_contains_leaf"] for event in events)
        assert all(event["container"] is not None for event in writers)
        assert all(event["container_contains_leaf"] for event in writers)
        if name not in {"Flash", "Circumscribe", "MoveAlongPath"}:
            assert any(event["animation"] == type(anim).__name__ for event in events)
        assert len(calls) > 2 and len(scene.renderer.frames) == 9
    record(f"k1_table_{axis}", rows)


@pytest.mark.parametrize("composition", [AnimationGroup, Succession, LaggedStart])
@pytest.mark.parametrize("permanent", [False, True])
def test_k1_compositions(composition, permanent):
    ax = System(9)
    curve = ax.plot(samples=10)
    original = curve.points.copy()
    dot = Dot()
    inner = Rotate(ax, PI / 6) if permanent else Indicate(ax)
    group = composition(dot.animate.shift(UP), inner)
    scene = ProbeScene()
    scene.add(curve, ax, dot)
    errors = []

    def observe(_scene):
        if permanent:
            theta = np.arctan2(
                ax.frame.points[ax.frame.probes[1], 1] - ax.frame.points[0, 1],
                ax.frame.points[ax.frame.probes[1], 0] - ax.frame.points[0, 0],
            )
            native = (
                plain(curve).set_points(original).rotate(theta, about_point=[0, 0, 0])
            )
            expected = native.points
        else:
            expected = original
        errors.append(error(curve.points, expected))
        return {}

    scene.renderer.observe = observe
    calls = count_interpolation(group)
    scene.play(group, run_time=0.6)
    endpoint = curve.points.copy()
    ax.shift(RIGHT)
    reattach = error(curve.points, endpoint + RIGHT)
    events = ax.frame.context_events
    record(
        f"k1_{composition.__name__}_{permanent}",
        {
            "events": events,
            "max_error": max(errors),
            "reattach_error": reattach,
            "calls": len(calls),
            "frames": len(errors),
            "remaining_suspensions": len(ax.frame._suspensions),
        },
    )
    assert max(errors) < 1e-9 and reattach < 1e-9 and not ax.frame._suspensions
    assert len(events) == (1 if composition is Succession else 2)
    assert events[-1]["animation"] == type(inner).__name__
    assert (events[-1]["playback"] is not None) == (composition is Succession)


@pytest.mark.parametrize(
    "kind", ["MoveAlongPath", "ShowIncreasingSubsets", "PhaseFlow"]
)
@pytest.mark.parametrize("subject_kind", ["axis", "artist", "foreign"])
def test_k1_no_suspension(kind, subject_kind):
    ax = System(9)
    curve = ax.plot(samples=10)
    subject = (
        ax
        if subject_kind == "axis"
        else curve
        if subject_kind == "artist"
        else VGroup(curve, Dot())
    )
    native = plain(subject)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve, subject)
    control.add(native)

    def make(mob):
        if kind == "MoveAlongPath":
            from manim import Line

            return MoveAlongPath(mob, Line(-RIGHT, RIGHT))
        if kind == "PhaseFlow":
            return PhaseFlow(lambda p: UP + 0.1 * p, mob)
        return ShowIncreasingSubsets(mob)

    anim = make(subject)
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    control.play(make(native), run_time=0.6)
    maximum = error(subject.points, native.points) if subject_kind == "artist" else 0
    if subject_kind == "foreign":
        maximum = error(curve.points, native[0].points)
    events = (
        [e for leaf in ax.submobjects[1:] for e in leaf.writer_events]
        if subject_kind == "axis"
        else curve.writer_events
    )
    record(
        f"k1_unsuspended_{kind}_{subject_kind}",
        {
            "suspends": curve.suspend_events,
            "frame_suspends": ax.frame.context_events,
            "writer_events": events,
            "error": maximum,
            "placement_nodes": len(curve.placement),
            "calls": len(calls),
            "frames": len(scene.renderer.frames),
        },
    )
    assert not curve.suspend_events and not ax.frame.context_events
    assert maximum < 1e-9 and len(calls) > 2


def test_k1_stack_microcost():
    timings = {}
    for function in [writer_context, animation_context]:
        batches = []
        for _ in range(30):
            start = perf_counter_ns()
            for _ in range(1000):
                function()
            batches.append((perf_counter_ns() - start) / 1000)
        timings[function.__name__] = {
            "median_ns": float(np.median(batches)),
            "p95_ns": float(np.percentile(batches, 95)),
        }
    record("k1_stack_cost", timings)


def test_k2_artist_in_same_animation_is_not_frozen():
    ax = System(9)
    curve = ax.plot(samples=10)
    group = VGroup(ax, curve)
    native = plain(group)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(group)
    control.add(native)
    actual, expected = [], []
    scene.renderer.observe = lambda _s: actual.append(curve.points.copy()) or {}
    control.renderer.observe = lambda _s: (
        expected.append(native[-1].points.copy()) or {}
    )
    scene.play(Indicate(group), run_time=0.6)
    control.play(Indicate(native), run_time=0.6)
    maximum = max(error(a, b) for a, b in zip(actual, expected, strict=True))
    record(
        "k2_included_artist",
        {
            "error": maximum,
            "excluded_artists": ax.frame.context_events[0]["excluded_artists"],
        },
    )
    assert maximum < 1e-9 and curve._frozen_frame is None


def test_k2_simulation_reverse_group_registry():
    ax = System(9)
    curve = ax.plot(samples=10)
    group = VGroup(curve, ax)
    anim = Indicate(group)
    before = set(ax.artists)
    ax.frame.simulate(anim)
    assert set(ax.artists) == before
