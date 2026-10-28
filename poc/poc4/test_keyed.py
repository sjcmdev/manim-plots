"""v4 experiments: native keyed families, lifecycle, source facts and costs."""

import inspect
from time import perf_counter_ns

import numpy as np
import pytest
from manim import (
    PI,
    RED,
    RIGHT,
    UP,
    ApplyPointwiseFunction,
    Create,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    Mobject,
    NumberPlane,
    ReplacementTransform,
    ShrinkToCenter,
    Transform,
    Uncreate,
    UpdateFromAlphaFunc,
    VGroup,
    VMobject,
    Write,
    linear,
    tempconfig,
    there_and_back,
)

from poc4.context import LAST_WRITES, last_points_write
from poc4.model import Decoration, MaxN, Multiple, System, error, path, record
from poc4.scene import ProbeScene, count_interpolation, pixels
from poc4.test_geometry import plain, wave


def ticks(ax):
    return {
        m.role[1]: m
        for m in ax.submobjects
        if isinstance(m, Decoration) and m.role[0] == "tick"
    }


def oracle(points, limits, grid, reference, probes):
    p = np.array(points, copy=True)
    p[:, 0] = (p[:, 0] - limits[0]) * 6 / np.ptp(limits) - 3
    affine = np.linalg.solve(np.c_[reference[probes, :2], np.ones(3)], grid[probes])
    return np.c_[p[:, :2], np.ones(len(p))] @ affine


CASES = ["shift_range", "range_shift", "scale_range_rotate", "maxn", "arc"]


def chain(mob, case, data=True):
    if case in {"shift_range", "arc"}:
        mob = mob.shift(RIGHT)
        return mob.set_x_range((0, 20)) if data else mob
    if case == "range_shift":
        if data:
            mob = mob.set_x_range((0, 20))
        return mob.shift(RIGHT)
    if case == "scale_range_rotate":
        mob = mob.scale(0.5)
        if data:
            mob = mob.set_x_range((-5, 5))
        return mob.rotate(PI / 6)
    return mob.set_x_range((0, 100)) if data else mob


@pytest.mark.parametrize("case", CASES)
def test_l1_native_chain(case):
    assert not hasattr(System.set_x_range, "_override_animate")
    ax = System(9, locator=MaxN() if case == "maxn" else Multiple())
    curve = ax.plot(samples=41)
    initial_range = ax.x_range.copy()
    target_range = np.array(
        [-5, 5]
        if case == "scale_range_rotate"
        else [0, 100]
        if case == "maxn"
        else [0, 20]
    )
    direct = ax.copy()
    chain(direct, case)
    native = plain(ax)
    native_target = plain(ax)
    chain(native_target, case, data=False)
    arc = PI / 3 if case == "arc" else 0
    native_scene = ProbeScene()
    native_scene.add(native)
    native_frames = []
    native_scene.renderer.observe = lambda _s: (
        native_frames.append(native[0].points.copy()) or {}
    )
    native_scene.play(
        Transform(native, native_target, path_arc=arc), run_time=0.6, rate_func=linear
    )
    scene = ProbeScene()
    scene.add(curve, ax)
    rows = []

    def observe(_scene):
        index = len(rows)
        expected_range = (1 - index / 9) * initial_range + index / 9 * target_range
        grid = native_frames[index]
        expected_values = ax.locator.values(expected_range)
        expected_keys = {ax.locator.key(v) for v in expected_values}
        active = {k for k, leaf in ticks(ax).items() if leaf.active}
        curve_expected = oracle(
            curve.source, expected_range, grid, ax.frame.reference, ax.frame.probes
        )
        maximum = error(curve.points, curve_expected)
        native_leaves = []
        for leaf in ax.submobjects[1:]:
            if leaf.role[0] == "x-axis":
                data = path([[expected_range[0], 0, 0], [expected_range[1], 0, 0]])
            elif leaf.role[0] == "y-axis":
                data = path([[0, -2, 0], [0, 2, 0]])
            else:
                key = leaf.role[1]
                if key not in expected_keys:
                    assert leaf.get_stroke_opacity() == 0
                    continue
                value = next(v for v in expected_values if ax.locator.key(v) == key)
                data = (
                    path([[value, -0.06, 0], [value, 0.06, 0]])
                    if leaf.role[0] == "tick"
                    else path(
                        [
                            [value - 0.04, -0.16, 0],
                            [value, -0.23, 0],
                            [value + 0.04, -0.16, 0],
                        ]
                    )
                )
            expected = oracle(
                data, expected_range, grid, ax.frame.reference, ax.frame.probes
            )
            maximum = max(maximum, error(leaf.points, expected))
            native_leaves.append(VMobject().set_points(expected).match_style(leaf))
        native_curve = VMobject().set_points(curve_expected).match_style(curve)
        difference = int(
            np.count_nonzero(pixels(curve, ax) != pixels(native_curve, *native_leaves))
        )
        families = list(animation.get_all_families_zipped())
        roles_match = all(
            getattr(a, "role", "frame")
            == getattr(b, "role", "frame")
            == getattr(c, "role", "frame")
            for a, b, c in families
        )
        rows.append(
            {
                "error": maximum,
                "range_error": float(np.max(abs(ax.x_range - expected_range))),
                "keys_correct": active == expected_keys,
                "roles_match": roles_match,
                "pool_size": len(ticks(ax)),
                "pixel_channels": difference,
                "keys": sorted(active),
                "partial_opacities": sum(
                    0 < leaf.get_stroke_opacity() < 1 for leaf in ticks(ax).values()
                ),
            }
        )
        return {}

    scene.renderer.observe = observe
    animation = chain(ax.animate(path_arc=arc), case).build()
    calls = count_interpolation(animation)
    scene.play(animation, run_time=0.6, rate_func=linear)
    final_error = max(
        error(a.points, b.points)
        for a, b in zip(ax.submobjects, direct.submobjects, strict=True)
    )
    record(
        f"l1_{case}",
        {
            "frames": rows,
            "calls": len(calls),
            "final_error": final_error,
            "final_range": ax.x_range.tolist(),
            "pool": ax.pool_evidence,
            "starting_inherited_pool": len(ticks(animation.starting_mobject))
            == len(ticks(animation.target_copy)),
            "final_leaves": len(ax.submobjects),
        },
    )
    assert len(rows) == 9 and len(calls) == 11
    assert all(
        r["error"] < 1e-9
        and r["range_error"] < 1e-9
        and r["keys_correct"]
        and r["roles_match"]
        and r["pixel_channels"] == 0
        for r in rows
    )
    assert final_error < 1e-9 and np.array_equal(ax.x_range, target_range)
    assert len({id(m) for m in ax.submobjects}) == len(ax.submobjects)
    assert len(ticks(ax)) == len(ax.values_by_key())
    if case == "maxn":
        assert len({tuple(r["keys"]) for r in rows[1:-1]}) > 2


def test_l2_identity_and_return():
    ax = System(9, locator=Multiple())
    tick = ticks(ax)[2]
    label = next(
        m
        for m in ax.submobjects
        if isinstance(m, Decoration) and m.role == ("label", 2)
    )
    tick.set_color(RED)
    label.set_color(RED)
    scene = ProbeScene()
    scene.add(ax)
    visibility = []
    scene.renderer.observe = lambda _s: visibility.append(tick.active) or {}
    scene.play(ax.animate.set_x_range((-1, 1)), run_time=0.6, rate_func=there_and_back)
    within = (
        ticks(ax)[2] is tick and tick.get_color() == RED and label.get_color() == RED
    )
    scene.play(ax.animate.shift(RIGHT).set_x_range((0, 20)), run_time=0.6)
    survivor = (
        ticks(ax)[2] is tick
        and label in ax.submobjects
        and tick.get_color() == RED
        and label.get_color() == RED
    )
    ax.set_x_range((3, 5))
    ax.set_x_range((0, 20))
    across = ticks(ax)[2] is tick
    record(
        "l2_identity",
        {
            "inactive_mid_animation": False in visibility,
            "same_object_and_style_within": within,
            "survives_l1": survivor,
            "same_object_after_separate_exit_return": across,
        },
    )
    assert False in visibility and within and survivor and not across
    assert ticks(ax)[2].get_color() != RED


@pytest.mark.parametrize("replacement", [False, True])
def test_l3_other_system(replacement):
    ax, target = System(9, locator=Multiple()), System(9, locator=Multiple())
    target.set_x_range((0, 20)).shift(RIGHT)
    curve = ax.plot(samples=41)
    native, native_target = plain(ax), plain(target)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(ax, curve)
    control.add(native)
    rows = []

    def observe(_s):
        index = len(rows)
        limits = (1 - index / 9) * np.array([-3, 3]) + index / 9 * np.array([0, 20])
        data = curve.source.copy()
        data[:, 0] = (data[:, 0] - limits[0]) * 6 / np.ptp(limits) - 3
        data += RIGHT * index / 9
        expected_values = ax.locator.values(limits)
        expected_keys = {ax.locator.key(v) for v in expected_values}
        tick_error = 0
        for key, tick in ticks(ax).items():
            if tick.active:
                value = next(v for v in expected_values if ax.locator.key(v) == key)
                expected = path([[value, -0.06, 0], [value, 0.06, 0]])
                expected[:, 0] = (expected[:, 0] - limits[0]) * 6 / np.ptp(limits) - 3
                tick_error = max(
                    tick_error, error(tick.points, expected + RIGHT * index / 9)
                )
        rows.append(
            {
                "curve_error": error(curve.points, data),
                "tick_error": tick_error,
                "keys_correct": {k for k, leaf in ticks(ax).items() if leaf.active}
                == expected_keys,
            }
        )
        return {}

    scene.renderer.observe = observe
    cls = ReplacementTransform if replacement else Transform
    anim = cls(ax, target)
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6, rate_func=linear)
    control.play(cls(native, native_target), run_time=0.6, rate_func=linear)
    final_error = max(
        error(a.points, b.points)
        for a, b in zip(ax.submobjects, target.submobjects, strict=True)
    )
    endpoint = curve.points.copy()
    target.shift(UP)
    target_motion = error(curve.points, endpoint)
    ax.shift(UP)
    old_motion = error(curve.points, endpoint + UP)
    record(
        f"l3_{replacement}",
        {
            "frames": rows,
            "calls": len(calls),
            "artist_owned_by_old": curve.system is ax,
            "final_system_error": final_error,
            "old_in_scene": ax in scene.mobjects,
            "target_in_scene": target in scene.mobjects,
            "native_old_in_scene": native in control.mobjects,
            "native_target_in_scene": native_target in control.mobjects,
            "motion_after_target_shift": target_motion,
            "error_after_old_shift": old_motion,
        },
    )
    assert all(
        r["curve_error"] < 1e-9 and r["tick_error"] < 1e-9 and r["keys_correct"]
        for r in rows
    )
    assert final_error < 1e-9
    assert curve.system is ax and target_motion == 0 and old_motion < 1e-9
    assert (target in scene.mobjects) == replacement
    assert (native_target in control.mobjects) == replacement


@pytest.mark.parametrize(
    "remover,force_remove",
    [
        (Uncreate, False),
        (FadeOut, False),
        (ShrinkToCenter, False),
        (ShrinkToCenter, True),
    ],
)
def test_l4_remover_state(remover, force_remove):
    ax = System(9)
    curve = ax.plot(samples=41)
    native = plain(curve)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve)
    control.add(native)
    options = {"remover": True} if force_remove else {}
    scene.play(remover(curve, **options), run_time=0.6)
    control.play(remover(native, **options), run_time=0.6)
    was_removed = curve not in scene.mobjects
    endpoint = curve.points.copy()
    equality = error(endpoint, native.points)
    scene.add(curve)
    control.add(native)
    pixel_channels = int(np.count_nonzero(pixels(curve) != pixels(native)))
    ax.set_x_range((0, 20))
    ax.shift(RIGHT)
    frozen = error(curve.points, endpoint)
    if remover is ShrinkToCenter and not force_remove:
        record(
            "l4_ShrinkToCenter_default",
            {
                "endpoint_error": equality,
                "readd_pixel_channels": pixel_channels,
                "detached": curve.detached,
                "removed": was_removed,
                "motion_after_data_and_frame": frozen,
            },
        )
        assert (
            not curve.detached
            and not was_removed
            and equality < 1e-9
            and pixel_channels == 0
        )
        return
    assert curve.detached
    curve.refresh()
    refreshed = error(curve.points, ax.c2p(curve.source))
    record(
        f"l4_{remover.__name__}",
        {
            "endpoint_error": equality,
            "readd_pixel_channels": pixel_channels,
            "motion_after_data_and_frame": frozen,
            "refresh_error": refreshed,
            "removed": was_removed,
            "degenerate": bool(np.all(endpoint == endpoint[0])),
        },
    )
    assert (
        equality < 1e-9
        and pixel_channels == 0
        and frozen == 0
        and refreshed < 1e-9
        and not curve.detached
    )


@pytest.mark.parametrize("introducer", [Create, Write, FadeIn, GrowFromCenter])
@pytest.mark.parametrize("remover", [Uncreate, FadeOut])
def test_l4_introducer_current_data(introducer, remover):
    ax = System(9)
    curve = ax.plot(samples=41)
    native = plain(curve)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve)
    control.add(native)
    scene.play(remover(curve), run_time=0.6)
    control.play(remover(native), run_time=0.6)
    old_native = native.points.copy()
    ax.set_x_range((-5, 5))
    expected = curve.source * [0.6, 1, 1]
    fresh = VMobject().set_points(expected).match_style(curve)
    current_control = ProbeScene()
    current_control.add(fresh)
    actual_frames, native_frames = [], []
    scene.renderer.observe = lambda _s: actual_frames.append(curve.points.copy()) or {}
    current_control.renderer.observe = lambda _s: (
        native_frames.append(fresh.points.copy()) or {}
    )
    scene.play(introducer(curve), run_time=0.6)
    current_control.play(introducer(fresh), run_time=0.6)
    control.play(introducer(native), run_time=0.6)
    frame_error = max(
        error(a, b) for a, b in zip(actual_frames, native_frames, strict=True)
    )
    record(
        f"l4_{remover.__name__}_{introducer.__name__}",
        {
            "endpoint_error": error(curve.points, expected),
            "fresh_native_frame_error": frame_error,
            "ordinary_readded_endpoint_error": error(curve.points, native.points),
            "ordinary_keeps_removed_state": error(native.points, old_native),
            "attached": not curve.detached,
        },
    )
    assert not curve.detached and error(curve.points, expected) < 1e-9
    assert frame_error < 1e-9


def polyline_error(mob, function, original):
    samples = np.linspace(0, 1, 10001)
    expected = np.array(
        [
            function(p)
            for p in (1 - samples[:, None]) * original[0]
            + samples[:, None] * original[-1]
        ]
    )
    controls = mob.points.reshape(-1, 4, 3)
    t = np.linspace(0, 1, 129)
    basis = np.array([(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3])
    actual = np.einsum("kt,ckd->ctd", basis, controls).reshape(-1, 3)
    from scipy.spatial import cKDTree

    def distances(query, polyline):
        polyline = polyline[np.r_[True, np.any(np.diff(polyline, axis=0) != 0, axis=1)]]
        _, index = cKDTree(polyline).query(query)
        result = np.full(len(query), np.inf)
        for offset in [-1, 0]:
            left = np.clip(index + offset, 0, len(polyline) - 2)
            a, b = polyline[left], polyline[left + 1]
            v = b - a
            norm = np.einsum("ij,ij->i", v, v)
            t = np.clip(
                np.einsum("ij,ij->i", query - a, v) / np.maximum(norm, 1e-30), 0, 1
            )
            result = np.minimum(
                result, np.linalg.norm(query - a - t[:, None] * v, axis=1)
            )
        return result

    return float(
        max(distances(actual, expected).max(), distances(expected, actual).max())
    )


@pytest.mark.parametrize("kind", ["wave", "square"])
def test_l5_densification(kind):
    function = (
        wave
        if kind == "wave"
        else lambda p: np.array([p[0] ** 2 - p[1] ** 2, 2 * p[0] * p[1], p[2]])
    )
    ax = System(65)
    originals = [m.source.copy() for m in ax.submobjects[1:]]
    affine_sizes = [len(m.points) for m in ax.submobjects[1:]]
    native_sparse = [plain(m) for m in ax.submobjects[1:]]
    native_dense = [plain(m) for m in ax.submobjects[1:]]
    for m in native_dense:
        NumberPlane.prepare_for_nonlinear_transform(VGroup(m), 64)
    for m in [*native_sparse, *native_dense]:
        if kind == "wave":
            m.apply_function(function)
        else:
            m.apply_complex_function(lambda z: z**2)
    scene = ProbeScene()
    scene.add(ax)
    if kind == "wave":
        scene.play(ApplyPointwiseFunction(function, ax), run_time=0.6)
    else:
        scene.play(ax.animate.apply_complex_function(lambda z: z**2), run_time=0.6)
    derived = ax.submobjects[1:]
    sparse_errors, dense_errors, native_errors, derived_sparse = [], [], [], []
    for leaf, sparse, dense, original in zip(
        derived, native_sparse, native_dense, originals, strict=True
    ):
        sparse_errors.append(polyline_error(sparse, function, original))
        before = VMobject().set_points(ax.c2p(original))
        derived_sparse.append(polyline_error(before, function, original))
        dense_errors.append(polyline_error(leaf, function, original))
        native_errors.append(polyline_error(dense, function, original))
    times = []
    for _ in range(30):
        start = perf_counter_ns()
        for leaf in derived:
            leaf._sample_key = None
            leaf.rebuild()
        times.append((perf_counter_ns() - start) / 1e6)
    affine = System(65)
    affine.shift(RIGHT).rotate(0.3).scale(0.5)
    affine_after = [len(m.points) for m in affine.submobjects[1:]]
    record(
        f"l5_{kind}",
        {
            "sparse_errors": sparse_errors,
            "derived_sparse_errors": derived_sparse,
            "derived_errors": dense_errors,
            "prepared_native_errors": native_errors,
            "affine_point_counts": affine_after,
            "dense_point_counts": [len(m.points) for m in derived],
            "rebuild_median_ms": float(np.median(times)),
            "rebuild_p95_ms": float(np.percentile(times, 95)),
        },
    )
    assert affine_after == affine_sizes == [4] * 12
    assert all(len(m.points) == 256 for m in derived)
    assert max(dense_errors) < max(sparse_errors)


def test_l6_source_lines_and_no_probes():
    lines = {}
    for method in [Mobject.shift, Mobject.apply_points_function_about_point]:
        source_lines, first = inspect.getsourcelines(method)
        source = "".join(source_lines)
        original = last_points_write(source, first)
        moved = last_points_write("\n" + source, first)
        assert moved == original + 1 and original == LAST_WRITES[method.__code__]
        lines[method.__name__] = {"original": original, "shifted": moved}
    ax = System(9)
    curve = ax.plot(samples=10)
    calls = []

    def arbitrary(p):
        calls.append(len(p))
        return p + UP

    curve.apply_points_function_about_point(arbitrary)
    assert calls == [len(curve.source)]
    assert callable(curve.placement[-1])
    for operation in [
        lambda m: m.rotate(0.3),
        lambda m: m.scale(0.7),
        lambda m: m.stretch(0.8, 1),
        lambda m: m.apply_matrix([[1, 0.2], [0.1, 1]]),
    ]:
        artist = ax.plot(samples=10)
        operation(artist)
        assert len(artist.placement) == 1 and not callable(artist.placement[0])
    record(
        "l6_facts", {"lines": lines, "arbitrary_call_sizes": calls, "probe_calls": 0}
    )


def test_l6_callback_simulation():
    ax = System(9)
    effects = []

    def callback(mob, alpha):
        effects.append(float(alpha))
        mob.shift(UP * alpha)

    anim = UpdateFromAlphaFunc(ax, callback, suspend_mobject_updating=True)
    assert ax.frame.simulate(anim)
    simulated = effects.copy()
    scene = ProbeScene()
    scene.add(ax)
    scene.play(anim, run_time=0.6)
    record(
        "l6_callbacks",
        {
            "explicit_simulation_effects": simulated,
            "all_effects": effects,
            "frames": len(scene.renderer.frames),
        },
    )
    assert simulated == [0, 1] and len(effects) > 13


def test_l7_parameter_cost():
    with tempconfig({"pixel_width": 1920, "pixel_height": 1080, "frame_rate": 60}):
        ax = System(33, locator=MaxN())
        curves = [
            ax.plot(lambda x, phase=k: np.sin(x + phase), samples=2000)
            for k in range(4)
        ]
        scene = ProbeScene()
        scene.add(*curves, ax)
        animation = ax.animate.set_x_range((0, 100)).build()
        calls = count_interpolation(animation)
        durations = []
        native_update = scene.update_to_time

        def update(t):
            start = perf_counter_ns()
            native_update(t)
            durations.append((perf_counter_ns() - start) / 1e6)

        scene.update_to_time = update
        scene.play(animation, run_time=10, rate_func=linear)
        frames = scene.renderer.frames
        rebuild = [f.get("rebuild_ns", 0) / 1e6 for f in frames]
        total = [
            update + f["render_ns"] / 1e6
            for update, f in zip(durations, frames, strict=True)
        ]
        record(
            "l7_parameter_cost",
            {
                "frames": len(frames),
                "calls": len(calls),
                "resolution": [1920, 1080],
                "fps": 60,
                "update_median_ms": float(np.median(durations)),
                "update_p95_ms": float(np.percentile(durations, 95)),
                "frame_with_cairo_p95_ms": float(np.percentile(total, 95)),
                "rebuild_p95_ms": float(np.percentile(rebuild, 95)),
                "pool": ax.pool_evidence,
            },
        )
        assert len(frames) == 600 and len(calls) == 602
