import numpy as np
from manim import ValueTracker

from poc3.model import System, error, record, source
from poc3.scene import ProbeScene, count_interpolation


def test_k5_callable_once_per_frame():
    ax = System(9)
    a = ValueTracker(1)
    samples = []

    def function(x):
        samples.append(a.get_value())
        return a.get_value() * np.sin(x)

    curve = ax.plot(function, samples=41)
    scene = ProbeScene()
    scene.add(curve, ax)
    frame_counts, errors, rereads = [], [], []

    def observe(_scene):
        errors.append(error(curve.points, source(41) * [1, a.get_value(), 1]))
        frame_counts.append(len(samples))
        start = len(samples)
        for _ in range(20):
            curve.get_center()
            _ = curve.points
        rereads.append(len(samples) - start)
        return {}

    scene.renderer.observe = observe
    start = len(samples)
    anim = a.animate.set_value(2).build()
    calls = count_interpolation(anim)
    scene.play(anim, run_time=0.6)
    per_frame = np.diff([start, *frame_counts]).tolist()
    before_wait = len(samples)
    before_frames = len(scene.renderer.frames)
    scene.wait(2)
    wait_samples = len(samples) - before_wait
    wait_frames = len(scene.renderer.frames) - before_frames
    record(
        "k5_callable",
        {
            "max_error": max(errors),
            "samples_per_frame": per_frame,
            "samples_on_reread": rereads,
            "wait_samples": wait_samples,
            "wait_render_calls": wait_frames,
            "initial_sampling_passes": start,
            "endpoint_sampling_passes": before_wait - frame_counts[-1],
            "calls": len(calls),
            "frames": len(frame_counts),
        },
    )
    assert max(errors) < 1e-9 and per_frame == [1] * 9 and rereads == [0] * 9
    assert wait_samples == wait_frames == 0 and len(calls) > 2
