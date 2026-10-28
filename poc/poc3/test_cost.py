import os
import platform
from time import perf_counter_ns

import manim
import numpy as np
import pytest
from manim import ValueTracker, VGroup, linear, tempconfig

from poc3.model import METRICS, System, record, sync_updater
from poc3.scene import ProbeScene, count_interpolation


@pytest.mark.parametrize("bilinear", [False, True])
def test_g6_600_frame_cost(bilinear):
    with tempconfig({"pixel_width": 1920, "pixel_height": 1080, "frame_rate": 60}):
        ax = System(n=33)
        ax.frame.force_bilinear = bilinear
        tracker = ValueTracker(1)
        artists = [
            ax.plot(
                lambda x, phase=phase: np.sin(x + phase), samples=2000, tracker=tracker
            )
            for phase in range(4)
        ]
        scene = ProbeScene()
        scene.add(*artists, ax)

        def dirty(_dt):
            for leaf in [*artists, *ax.submobjects[1:]]:
                leaf._dirty = True

        scene.add_updater(dirty)
        anim = tracker.animate(rate_func=linear).set_value(2).build()
        calls = count_interpolation(anim)
        scene.play(anim, run_time=10.1)
        frames = [f for f in scene.renderer.frames if f.get("rebuilds", 0) >= 16]
        assert len(frames) >= 600 and len(calls) > 600
        rebuild = [f["rebuild_ns"] / 1e6 for f in frames]
        compare = [f["compare_ns"] / 1e6 for f in frames]
        record(
            f"g6_{bilinear}",
            {
                "machine": platform.platform(),
                "processor": platform.processor(),
                "cpus": os.cpu_count(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "manim": manim.__version__,
                "resolution": [1920, 1080],
                "fps": 60,
                "calls": len(calls),
                "rendered_frames": len(scene.renderer.frames),
                "dirty_frames": len(frames),
                "rebuild_median_ms": float(np.median(rebuild)),
                "rebuild_p95_ms": float(np.percentile(rebuild, 95)),
                "comparison_p95_ms": float(np.percentile(compare, 95)),
                "comparison_calls_median": float(
                    np.median([f["compare_calls"] for f in frames])
                ),
                "passes_4ms": bool(np.percentile(rebuild, 95) <= 4),
                "frames": frames,
            },
        )


def test_g6_copy_and_comparison():
    ax = System(n=33)
    curves = [ax.plot(samples=2000) for _ in range(4)]
    group = VGroup(ax, *curves)
    times = []
    for _ in range(50):
        start = perf_counter_ns()
        clone = group.copy()
        times.append((perf_counter_ns() - start) / 1e6)
        assert all(c.system is clone[0] for c in clone.submobjects[1:])
    comparisons = {}
    for n in [9, 17, 33, 65]:
        system = System(n=n)
        system.frame.check()
        METRICS.clear()
        for _ in range(10000):
            system.frame.check()
        comparisons[n] = METRICS["compare_ns"] / METRICS["compare_calls"]
    update_times = {}
    for mode in ["none", "empty"]:
        for mob in [ax, *curves]:
            mob.clear_updaters(recursive=False)
            if mode == "empty":
                mob.add_updater(sync_updater)
        batches = []
        for _ in range(30):
            start = perf_counter_ns()
            for _ in range(100):
                group.update(1 / 60)
            batches.append((perf_counter_ns() - start) / 100)
        update_times[mode] = float(np.median(batches))
    record(
        "g6_micro",
        {
            "copy_median_ms": float(np.median(times)),
            "copy_p95_ms": float(np.percentile(times, 95)),
            "frame_comparison_ns": comparisons,
            "group_update_ns": update_times,
            "empty_updater_overhead_ns": update_times["empty"] - update_times["none"],
        },
    )
