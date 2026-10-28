import numpy as np
import pytest
from manim import RIGHT, TAU, Rotate

from poc3.model import System, error, record
from poc3.scene import ProbeScene, count_interpolation
from poc3.test_animations import AX_ANIMATIONS, animation, independent_derived
from poc3.test_geometry import plain

TEMPORARY = {
    "Indicate",
    "Wiggle",
    "ApplyWave",
    "Circumscribe",
    "Flash",
    "FadeIn",
    "FadeOut",
    "FadeInShift",
    "FadeOutShift",
    "GrowFromCenter",
    "Create",
    "Write",
    "Uncreate",
    "DrawBorderThenFill",
    "ShowPassingFlash",
    "RotateTAU",
}


def make(name, mob):
    return Rotate(mob, TAU) if name == "RotateTAU" else animation(name, mob, axis=True)


@pytest.mark.parametrize("name", [*AX_ANIMATIONS, "RotateTAU"])
def test_k2_axis_detachment(name):
    ax = System(9)
    curve = ax.plot(samples=41)
    native_axes = plain(ax)
    native_axes.remove(native_axes[0])
    native_curve = plain(curve)
    scene, control = ProbeScene(), ProbeScene()
    scene.add(curve, ax)
    control.add(native_curve, native_axes)
    scene.renderer.keep_pixels = True
    control.renderer.keep_pixels = True
    actual_animation = make(name, ax)
    native_animation = make(name, native_axes)
    initial = curve.points.copy()
    # Restore's factory changes the starting axes before play.
    reference = curve.points.copy()
    errors = []
    axis_points, native_points = [], []
    motions = []
    scene.renderer.observe = lambda _s: (
        errors.append(
            error(
                curve.points,
                reference if name in TEMPORARY else independent_derived(ax, curve),
            )
        )
        or motions.append(error(curve.points, reference))
        or axis_points.append([m.points.copy() for m in ax.submobjects[1:]])
        or {}
    )
    control.renderer.observe = lambda _s: (
        native_points.append([m.points.copy() for m in native_axes.submobjects]) or {}
    )
    before = (
        ax.frame.points.copy(),
        curve.points.copy(),
        set(ax.artists),
        list(scene.mobjects),
    )
    permanent = ax.frame.simulate(actual_animation)
    simulation_untouched = (
        np.array_equal(ax.frame.points, before[0])
        and np.array_equal(curve.points, before[1])
        and set(ax.artists) == before[2]
        and scene.mobjects == before[3]
    )
    calls = count_interpolation(actual_animation)
    scene.play(actual_animation, run_time=0.6)
    control.play(native_animation, run_time=0.6)
    pixels = [
        int(np.count_nonzero(a != b))
        for a, b in zip(scene.renderer.pixels, control.renderer.pixels, strict=True)
    ]
    axis_error = max(
        error(a, b)
        for aa, bb in zip(axis_points, native_points, strict=True)
        for a, b in zip(aa, bb, strict=True)
    )
    endpoint = curve.points.copy()
    ax.shift(RIGHT)
    reattach = error(curve.points, endpoint + RIGHT)
    record(
        f"k2_{name}",
        {
            "permanent": permanent,
            "max_frame_error": max(errors),
            "max_motion": max(motions),
            "reattach_error": reattach,
            "simulation_untouched": simulation_untouched,
            "pixel_channel_difference": max(pixels),
            "calls": len(calls),
            "frames": len(errors),
            "axis_error": axis_error,
            "poc_mid_axis": axis_points[4][0].tolist(),
            "native_mid_axis": native_points[4][0].tolist(),
            "context_events": ax.frame.context_events,
            "source_initial_motion": error(initial, reference),
        },
    )
    assert max(errors) < 1e-9 and reattach < 1e-9 and simulation_untouched
    assert permanent == (name not in TEMPORARY)
    assert len(calls) > 2 and len(errors) == 9
    if name in TEMPORARY:
        assert max(motions) < 1e-9
        if name in {"Create", "Write", "Uncreate"}:
            assert max(pixels) > 0
        else:
            assert max(pixels) == 0
