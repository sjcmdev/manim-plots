import numpy as np
import pytest
from manim import (
    DOWN,
    LEFT,
    PI,
    RIGHT,
    UP,
    ApplyMatrix,
    ApplyPointwiseFunction,
    ApplyWave,
    Circle,
    Circumscribe,
    Create,
    DrawBorderThenFill,
    FadeIn,
    FadeOut,
    Flash,
    GrowFromCenter,
    Homotopy,
    Indicate,
    Line,
    MoveAlongPath,
    MoveToTarget,
    ReplacementTransform,
    Restore,
    Rotate,
    ScaleInPlace,
    ShowPassingFlash,
    Transform,
    TransformFromCopy,
    Uncreate,
    ValueTracker,
    Wiggle,
    Write,
    linear,
)
from manim.animation.animation import prepare_animation
from manim.camera.camera import Camera
from scipy.interpolate import RegularGridInterpolator

from poc4.model import Frame, System, error, record
from poc4.scene import ProbeScene, count_interpolation
from poc4.test_geometry import plain, wave

COMMON = [
    "Create",
    "Write",
    "ShowPassingFlash",
    "Indicate",
    "Wiggle",
    "ApplyWave",
    "Flash",
    "Circumscribe",
    "Uncreate",
]
AX_ANIMATIONS = [
    *COMMON,
    "DrawBorderThenFill",
    "FadeIn",
    "FadeOut",
    "FadeInShift",
    "FadeOutShift",
    "GrowFromCenter",
    "Rotate",
    "ScaleInPlace",
    "MoveAlongPath",
    "Homotopy",
    "ApplyPointwiseFunction",
    "ApplyMatrix",
    "Transform",
    "MoveToTarget",
    "Restore",
    "animate_chain",
    "animate_rotate",
]
ARTIST_ANIMATIONS = [
    *COMMON,
    "Rotate",
    "animate_shift",
    "animate_chain",
    "MoveToTarget",
    "Transform",
    "ReplacementTransform",
    "TransformCircle",
    "TransformFromCopy",
    "FadeOutShift",
]


def animation(name, mob, target=None, axis=False):
    if name == "FadeInShift":
        result = FadeIn(mob, shift=UP)
    elif name == "FadeOutShift":
        result = FadeOut(mob, shift=DOWN)
    elif name == "Homotopy":
        result = Homotopy(lambda x, y, z, t: [x, y + 0.2 * t * np.sin(x), z], mob)
    elif name == "ApplyPointwiseFunction":
        result = ApplyPointwiseFunction(wave, mob)
    elif name == "ApplyMatrix":
        result = ApplyMatrix([[1, 0.2], [0.1, 1]], mob)
    elif name in {"Transform", "ReplacementTransform", "TransformFromCopy"}:
        cls = {
            "Transform": Transform,
            "ReplacementTransform": ReplacementTransform,
            "TransformFromCopy": TransformFromCopy,
        }[name]
        result = cls(mob, target if target is not None else mob.copy().shift(RIGHT))
    elif name == "TransformCircle":
        result = Transform(mob, Circle())
    elif name == "MoveToTarget":
        mob.generate_target()
        mob.target.shift(RIGHT)
        result = MoveToTarget(mob)
    elif name == "Restore":
        mob.save_state()
        mob.shift(RIGHT)
        result = Restore(mob)
    elif name == "animate_chain":
        result = mob.animate.shift(RIGHT).scale(0.5 if axis else 2)
    elif name == "animate_shift":
        result = mob.animate.shift(UP)
    elif name == "animate_rotate":
        result = mob.animate.rotate(PI / 6)
    elif name == "Rotate":
        result = Rotate(mob, PI / 6)
    elif name == "ScaleInPlace":
        result = ScaleInPlace(mob, 0.7)
    elif name == "MoveAlongPath":
        result = MoveAlongPath(mob, Line(LEFT, RIGHT))
    else:
        cls = {
            c.__name__: c
            for c in [
                Create,
                Write,
                ShowPassingFlash,
                Indicate,
                Wiggle,
                ApplyWave,
                Flash,
                Circumscribe,
                Uncreate,
                DrawBorderThenFill,
                FadeIn,
                FadeOut,
                GrowFromCenter,
            ]
        }[name]
        result = cls(mob)
    return prepare_animation(result)


def independent_derived(ax, artist, frame=None):
    p = artist.data_points().copy()
    p[:, 0] = (p[:, 0] - ax.x_range[0]) * 6 / np.ptp(ax.x_range) - 3
    frame = ax.frame if frame is None else frame
    reference = frame.reference
    nodes = frame.points
    idx = frame.probes
    affine = np.linalg.solve(np.c_[reference[idx, :2], np.ones(3)], nodes[idx])
    if error(np.c_[reference[:, :2], np.ones(len(reference))] @ affine, nodes) < 1e-10:
        return np.c_[p[:, :2], np.ones(len(p))] @ affine
    grid = nodes[::4].reshape(frame.n, frame.n, 3)
    interpolator = RegularGridInterpolator(
        (np.linspace(-2, 2, ax.frame.n), np.linspace(-3, 3, ax.frame.n)),
        grid,
        bounds_error=False,
        fill_value=None,
    )
    return interpolator(p[:, [1, 0]])


def frame_pixel_difference(scene):
    family = scene.get_mobject_family_members()
    camera = Camera()
    camera.capture_mobjects(family, include_submobjects=False)
    before = camera.pixel_array.copy()
    camera.reset()
    camera.capture_mobjects(
        [m for m in family if not isinstance(m, Frame)], include_submobjects=False
    )
    return int(np.count_nonzero(before != camera.pixel_array))


@pytest.mark.parametrize("name", AX_ANIMATIONS)
def test_g2_axis_animation(name):
    ax = System(n=9)
    artist = ax.plot(samples=101)
    artist_initial = artist.points.copy()
    native = plain(ax)
    native_frame = native.submobjects[0]
    native_external_artist = plain(artist)
    scene = ProbeScene()
    scene.add(artist, ax)
    singular = []

    def observe(scene):
        points = ax.frame.points
        corners = points[ax.frame.probes[:3]]
        area = np.linalg.norm(
            np.cross(corners[1] - corners[0], corners[2] - corners[0])
        )
        if area < 1e-12:
            try:
                ax.p2c([[0, 0, 0]])
                singular.append("returned")
            except np.linalg.LinAlgError as exc:
                singular.append(str(exc))
        return {
            "artist_error": error(
                artist.points, independent_derived(ax, artist, artist._frozen_frame)
            ),
            "artist_motion": error(artist.points, artist_initial),
            "nodes": len(points),
            "finite": bool(np.isfinite(points).all()),
            "area": float(area),
            "pixel_difference": frame_pixel_difference(scene),
        }

    scene.renderer.observe = observe
    anim = animation(name, ax, axis=True)
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    reference_scene = ProbeScene()
    reference_scene.add(native_external_artist, native)
    native_anim = animation(name, native, axis=True)
    native_calls = count_interpolation(native_anim)
    reference_scene.play(native_anim, run_time=0.6)
    frames = scene.renderer.frames
    maximum = max(f["artist_error"] for f in frames)
    native_error = error(ax.frame.points, native_frame.points)
    record(
        f"g2_{name}",
        {
            "calls": len(calls),
            "native_calls": len(native_calls),
            "frames": len(frames),
            "max_artist_error": maximum,
            "native_final_frame_error": native_error,
            "native_point_count_equal": len(ax.frame.points)
            == len(native_frame.points),
            "max_artist_motion": max(f["artist_motion"] for f in frames),
            "native_external_artist_motion": error(
                native_external_artist.points, artist_initial
            ),
            "finite": all(f["finite"] for f in frames),
            "point_count_stable": all(
                f["nodes"] == len(ax.frame.reference) for f in frames
            ),
            "min_area": min(f["area"] for f in frames),
            "max_pixel_difference": max(f["pixel_difference"] for f in frames),
            "singular_p2c": singular,
            "frame_measurements": frames,
            "artist_removed": artist not in scene.mobjects,
            "axis_removed": ax not in scene.mobjects,
        },
    )
    assert len(calls) > 2 and len(native_calls) > 2 and len(frames) >= 8
    assert maximum < 1e-9
    assert all(f["pixel_difference"] == 0 for f in frames)
    assert error(native_external_artist.points, artist_initial) == 0
    assert (native_error < 1e-9) == (name != "Uncreate")


def run_artist(name, changing_data):
    ax = System(n=9)
    tracker = ValueTracker(1)
    artist = ax.plot(samples=41, tracker=tracker if changing_data else None)
    sibling = ax.plot(np.cos, samples=41)
    untouched = sibling.points.copy()
    frame_before = ax.frame.points.copy()
    target = ax.plot(np.cos, samples=41).shift(UP).set_color("#FF0000")
    native = plain(artist)
    starting_points = native.points.copy()
    native_target = plain(target)
    scene = ProbeScene()
    scene.add(ax, artist, sibling)
    anim = animation(name, artist, target)
    calls = count_interpolation(anim)
    exception = None
    try:
        extra = (
            [tracker.animate(rate_func=linear).set_value(1.5)] if changing_data else []
        )
        scene.play(anim, *extra, run_time=0.6)
    except (ValueError, AssertionError) as exc:
        exception = type(exc).__name__ + ": " + str(exc)
    native_scene = ProbeScene()
    native_scene.add(native)
    native_anim = animation(name, native, native_target)
    native_calls = count_interpolation(native_anim)
    native_scene.play(native_anim, run_time=0.6)
    before = artist.points.copy()
    native_error = error(before, native.points)
    ax.set_x_range([-2.8, 2.8])
    rebuilt = artist.points.copy()
    # Return the map to its original range: accepted geometry must still be there.
    ax.set_x_range([-3, 3])
    persisted_error = error(artist.points, before)
    data_applied = error(artist.points, artist.derived())
    data_expected_error = None
    if changing_data:
        changed_source = starting_points * [1, 1.5, 1]
        if name in {"Transform", "ReplacementTransform"}:
            expected_data = native_target.points
        elif name == "TransformCircle" or artist.detached:
            expected_data = native.points
        else:
            affine = np.linalg.lstsq(
                np.c_[starting_points, np.ones(len(starting_points))],
                native.points,
                rcond=None,
            )[0]
            expected_data = np.c_[changed_source, np.ones(len(changed_source))] @ affine
        data_expected_error = error(artist.points, expected_data)
    result = {
        "exception": exception,
        "calls": len(calls),
        "native_calls": len(native_calls),
        "frames": len(scene.renderer.frames),
        "native_final_error": native_error,
        "persisted_error": persisted_error,
        "data_error": data_applied,
        "independent_data_error": data_expected_error,
        "tracker": tracker.get_value(),
        "detached": artist.detached,
        "placement_nodes": len(artist.placement),
        "frame_error": error(ax.frame.points, frame_before),
        "sibling_error": error(sibling.points, untouched),
        "removed": artist not in scene.mobjects,
        "native_removed": native not in native_scene.mobjects,
        "raw_degenerate": bool(np.all(before == before[0])),
        "native_degenerate": bool(np.all(native.points == native.points[0])),
        "point_count": len(before),
        "native_point_count": len(native.points),
        "range_changes_geometry": error(before, rebuilt),
        "style_equal": bool(np.allclose(artist.stroke_rgbas, native.stroke_rgbas)),
        "target_source_adopted": artist.source is target.source,
        "target_final_error": error(target.points, native_target.points),
    }
    if not changing_data:
        scene.add(artist)
        result["readd_full_shape"] = not bool(np.all(artist.points == artist.points[0]))
    record(f"g3_{name}_{'data' if changing_data else 'plain'}", result)
    assert len(native_calls) > 2
    assert result["frame_error"] == 0 and result["sibling_error"] == 0
    if exception is None:
        assert len(calls) > 2 and result["frames"] >= 8
        if not artist.detached:
            assert data_applied < 1e-9
        else:
            assert result["range_changes_geometry"] == 0
        if changing_data and not artist.detached:
            assert data_expected_error < 1e-9
        if artist.detached:
            assert persisted_error == 0
        if not changing_data:
            assert native_error < 1e-9
            assert persisted_error < 1e-9
    return result


@pytest.mark.parametrize("name", ARTIST_ANIMATIONS)
@pytest.mark.parametrize("changing_data", [False, True])
def test_g3_artist_animation(name, changing_data):
    run_artist(name, changing_data)


def test_g3_target_with_more_points():
    ax = System(n=9)
    artist = ax.plot(samples=10)
    target = ax.plot(np.cos, samples=50)
    native, native_target = plain(artist), plain(target)
    scene = ProbeScene()
    scene.add(ax, artist)
    anim = Transform(artist, target)
    calls = count_interpolation(anim)
    exception = None
    try:
        scene.play(anim, run_time=0.6)
    except ValueError as exc:
        exception = str(exc)
    native_scene = ProbeScene()
    native_scene.add(native)
    native_anim = Transform(native, native_target)
    native_calls = count_interpolation(native_anim)
    native_scene.play(native_anim, run_time=0.6)
    record(
        "g3_more_points",
        {
            "exception": exception,
            "calls": len(calls),
            "frames": len(scene.renderer.frames),
            "native_calls": len(native_calls),
            "native_frames": len(native_scene.renderer.frames),
        },
    )
    assert exception is None and len(native_calls) > 2
    assert error(artist.points, native.points) < 1e-9
