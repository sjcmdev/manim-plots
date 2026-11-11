import numpy as np
from manim import RIGHT, UpdateFromAlphaFunc, override_animate

from poc3.model import Derived, Frame, System, error, path, record
from poc3.scene import ProbeScene, count_interpolation
from poc3.test_geometry import plain


class Tick(Derived):
    def __init__(self, value, system):
        self.value = value
        super().__init__(path([[value, -0.06, 0], [value, 0.06, 0]]), system)

    def interpolate(self, _start, _target, _alpha, _path_func=None):
        self._cache = self.derived()
        return self


class ParameterFrame(Frame):
    def interpolate(self, start, target, alpha, path_func):
        self.owner.x_range = (
            1 - alpha
        ) * start.owner.x_range + alpha * target.owner.x_range
        return super().interpolate(start, target, alpha, path_func)


class RangeSystem(System):
    def __init__(self):
        super().__init__(n=9, ticks=0)
        self.remove(self.frame)
        self.frame = ParameterFrame(9)
        self.frame.owner = self
        self.submobjects.insert(0, self.frame)
        self.set_x_range([-3, 3])

    def set_x_range(self, limits):
        super().set_x_range(limits)
        self.submobjects[:] = [m for m in self.submobjects if not isinstance(m, Tick)]
        for value in np.arange(np.ceil(limits[0]), np.floor(limits[1]) + 1):
            self.add(Tick(value, self))
        self.submobjects[1].source = path([[limits[0], 0, 0], [limits[1], 0, 0]])
        self.submobjects[1]._dirty = True
        return self


class OverrideRangeSystem(RangeSystem):
    def set_x_range(self, limits):
        return super().set_x_range(limits)

    @override_animate(set_x_range)
    def animate_range(self, limits, anim_args=None):
        initial = self.x_range.copy()

        def update(_mob, alpha):
            self.set_x_range((1 - alpha) * initial + alpha * np.array(limits))

        return UpdateFromAlphaFunc(
            self, update, suspend_mobject_updating=False, **(anim_args or {})
        )


def observe_range(ax, curve):
    expected_values = np.arange(np.ceil(ax.x_range[0]), np.floor(ax.x_range[1]) + 1)
    ticks = [m for m in ax.submobjects if isinstance(m, Tick)]
    actual_values = [m.value for m in ticks]
    tick_error = max((error(m.points, ax.c2p(m.source)) for m in ticks), default=0)
    expected_curve = curve.source.copy()
    expected_curve[:, 0] = (expected_curve[:, 0] - ax.x_range[0]) * 6 / np.ptp(
        ax.x_range
    ) - 3
    # This test only translates the frame; read its origin independently.
    expected_curve += ax.frame.points[0] - ax.frame.reference[0]
    return {
        "range": ax.x_range.tolist(),
        "tick_values": actual_values,
        "expected_tick_values": expected_values.tolist(),
        "tick_set_correct": actual_values == expected_values.tolist(),
        "tick_error": tick_error,
        "artist_error": error(curve.points, expected_curve),
    }


def test_g7_override_and_chain_errors():
    ax = OverrideRangeSystem()
    curve = ax.plot(samples=101)
    scene = ProbeScene()
    scene.add(curve, ax)
    scene.renderer.observe = lambda _s: observe_range(ax, curve)
    anim = ax.animate.set_x_range([-2, 5]).build()
    calls = count_interpolation(anim)
    assert not anim.suspend_mobject_updating
    scene.play(anim, run_time=0.6)
    exceptions = []
    for reverse in [False, True]:
        instance = OverrideRangeSystem()
        try:
            if reverse:
                instance.animate.set_x_range([-2, 5]).shift(RIGHT)
            else:
                instance.animate.shift(RIGHT).set_x_range([-2, 5])
        except NotImplementedError as exc:
            exceptions.append(str(exc))
    frames = scene.renderer.frames
    record(
        "g7_override",
        {
            "calls": len(calls),
            "frames": frames,
            "final_range": ax.x_range.tolist(),
            "chain_exceptions": exceptions,
        },
    )
    assert len(calls) > 2 and len(exceptions) == 2
    assert all(
        f["tick_set_correct"] and f["tick_error"] < 1e-9 and f["artist_error"] < 1e-9
        for f in frames
    )
    assert np.array_equal(ax.x_range, [-2, 5])


def test_g7_native_parameter_interpolation_tick_alignment():
    ax = RangeSystem()
    curve = ax.plot(samples=101)
    scene = ProbeScene()
    scene.add(curve, ax)
    scene.renderer.observe = lambda _s: observe_range(ax, curve)
    anim = ax.animate.shift(RIGHT).set_x_range([-5, 5]).build()
    native, native_target = plain(ax), plain(anim.target_mobject)
    calls = count_interpolation(anim)
    failure = None
    try:
        scene.play(anim, run_time=0.6)
    except AttributeError as exc:
        failure = str(exc)
    from manim import Transform

    native_scene = ProbeScene()
    native_scene.add(native)
    native_animation = Transform(native, native_target)
    native_calls = count_interpolation(native_animation)
    native_scene.play(native_animation, run_time=0.6)
    frames = scene.renderer.frames
    record(
        "g7_native",
        {
            "calls": len(calls),
            "frames": frames,
            "exception": failure,
            "native_calls": len(native_calls),
            "native_frames": len(native_scene.renderer.frames),
            "aligned_family": [type(m).__name__ for m in ax.submobjects],
            "target_family": [type(m).__name__ for m in anim.target_copy.submobjects],
            "final_range": ax.x_range.tolist(),
            "bad_tick_frames": sum(not f["tick_set_correct"] for f in frames),
            "max_artist_error": max((f["artist_error"] for f in frames), default=0),
        },
    )
    assert failure == "Derived object has no attribute 'owner'"
    assert len(native_calls) > 2


def test_g7_native_same_tick_count():
    ax = RangeSystem()
    curve = ax.plot(samples=101)
    scene = ProbeScene()
    scene.add(curve, ax)
    scene.renderer.observe = lambda _s: observe_range(ax, curve)
    anim = ax.animate.shift(RIGHT).set_x_range([-2, 4]).build()
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    frames = scene.renderer.frames
    record(
        "g7_native_same_count",
        {"calls": len(calls), "frames": frames, "final_range": ax.x_range.tolist()},
    )
    assert len(calls) > 2 and len(frames) >= 8
    assert any(not f["tick_set_correct"] for f in frames)
