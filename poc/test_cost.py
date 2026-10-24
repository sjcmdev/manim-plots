import os
import platform
from time import perf_counter_ns

import numpy as np
from manim import ValueTracker, linear, tempconfig
from poc.points import Leaf, System, curve, record
from poc.scene import ProbeScene


def test_600_frame_rebuild_and_getter_cost():
    with tempconfig({"pixel_width": 1920, "pixel_height": 1080, "frame_rate": 60}):
        system = System()
        leaves = [Leaf(curve(2000, phase), system) for phase in range(4)]
        for x in np.linspace(-3, 3, 10):
            leaves.append(
                Leaf(
                    np.array([[x, -0.05, 0], [x, 0, 0], [x, 0, 0], [x, 0.05, 0]]),
                    system,
                )
            )
        scene = ProbeScene()
        for leaf in leaves:
            leaf.add_updater(lambda _mob: None)
        scene.add(*leaves)
        tracker = ValueTracker(1)

        def update_data(_dt):
            for leaf in leaves:
                leaf.amplitude = tracker.get_value()

        scene.add_updater(update_data)
        scene.play(tracker.animate.set_value(2), run_time=10.1, rate_func=linear)
        frames = [f for f in scene.renderer.frames if f.get("rebuilds") == len(leaves)]
        assert len(frames) >= 600
        assert not scene.renderer.skip_animations
        record("h4_frames", frames)
        rebuild_ms = np.array([f["rebuild_ns"] / 1e6 for f in frames])
        shadow_ms = np.array([f["shadow_ns"] / 1e6 for f in frames])
        getters = [f["getters"] for f in frames]
        record(
            "h4_cost",
            {
                "machine": platform.platform(),
                "processor": platform.processor(),
                "logical_cpus": os.cpu_count(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "resolution": [1920, 1080],
                "fps": 60,
                "rendered_frames": len(scene.renderer.frames),
                "fully_dirty_frames": len(frames),
                "leaves": len(leaves),
                "sample_count": 4 * 2000,
                "control_points": sum(len(leaf.source) for leaf in leaves),
                "getters_per_frame_min": min(getters),
                "getters_per_frame_median": float(np.median(getters)),
                "getters_per_frame_max": max(getters),
                "shadow_calls_per_frame": float(
                    np.median([f["shadow_calls"] for f in frames])
                ),
                "shadow_median_ms": float(np.median(shadow_ms)),
                "shadow_p95_ms": float(np.percentile(shadow_ms, 95)),
                "rebuild_plus_shadow_p95_ms": float(
                    np.percentile(rebuild_ms + shadow_ms, 95)
                ),
                "rebuild_median_ms": float(np.median(rebuild_ms)),
                "rebuild_p95_ms": float(np.percentile(rebuild_ms, 95)),
                "remaining_budget_ms": 4 - float(np.percentile(rebuild_ms, 95)),
                "passes_4ms": bool(np.percentile(rebuild_ms, 95) <= 4),
            },
        )


def test_shadow_microbenchmark():
    # Clean getter vs same getter without array_equal: isolate comparison overhead.
    leaf = Leaf(curve(2000))
    measurements = {}
    for mode in ("shadow", "no_shadow"):
        if mode == "no_shadow":
            leaf._clean = lambda: True
        batches = []
        for _ in range(100):
            start = perf_counter_ns()
            for _ in range(200):
                _points = leaf.points
            batches.append((perf_counter_ns() - start) / 200)
        measurements[mode + "_median_ns"] = float(np.median(batches))
    measurements["difference_ns"] = (
        measurements["shadow_median_ns"] - measurements["no_shadow_median_ns"]
    )
    record("h4_shadow_micro", measurements)
