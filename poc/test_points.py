from time import perf_counter_ns

import manim
import numpy as np
from manim import RIGHT, Scene, VMobject
from poc.points import (
    METRICS,
    ROOT,
    Leaf,
    System,
    curve,
    nonlinear,
    pointwise_nonlinear,
    record,
)


def test_bootstrap_cache_setter_and_cairo():
    assert manim.__version__ == "0.21.0"
    before = METRICS["bootstrap_sets"]
    leaf = Leaf(curve(), stroke_width=4)
    assert METRICS["bootstrap_sets"] > before
    assert leaf.points is leaf.points
    plain = VMobject(stroke_width=4).set_points(leaf.derived())
    scene = Scene()
    scene.add(leaf)
    scene.renderer.update_frame(scene)
    actual = scene.renderer.get_frame().copy()
    scene.renderer.camera.get_image().save(ROOT / "media" / "property.png")
    scene.remove(leaf).add(plain)
    scene.renderer.update_frame(scene)
    expected = scene.renderer.get_frame().copy()
    scene.renderer.camera.get_image().save(ROOT / "media" / "plain.png")
    assert np.array_equal(actual, expected)
    assert np.count_nonzero(actual[:, :, :3]) > 0
    leaf.reset_points()
    assert leaf.points.shape == (0, 3)
    leaf.refresh()
    leaf.points = leaf.points + RIGHT  # Foreign whole-array affine stays transient.
    assert not leaf.system.placement
    leaf.refresh()
    assert np.array_equal(leaf.points, leaf.derived())
    record(
        "h1_render",
        {
            "different_pixels": int(np.count_nonzero(actual != expected)),
            "nonblack_channels": int(np.count_nonzero(actual[:, :, :3])),
            "bootstrap_sets": METRICS["bootstrap_sets"] - before,
        },
    )


def test_direct_geometry_and_order():
    results = {}
    operations = {
        "shift": lambda leaf: leaf.shift(RIGHT),
        "rotate": lambda leaf: leaf.rotate(0.4),
        "scale": lambda leaf: leaf.scale(1.3),
        "apply_function": lambda leaf: leaf.apply_function(nonlinear),
        "mobject_apply_function_control": pointwise_nonlinear,
    }
    for name, operation in operations.items():
        leaf = Leaf(curve())
        operation(leaf)
        transformed = leaf.points.copy()
        nodes = len(leaf.system.placement)
        leaf.amplitude = 1.5
        automatically_applied = np.array_equal(leaf.points, leaf.derived())
        assert automatically_applied == (name != "apply_function")
        leaf.refresh()
        control = Leaf(curve())
        control.amplitude = 1.5
        control.refresh()
        operation(control)
        survives = np.allclose(leaf.points, control.points, atol=1e-12)
        results[name] = {
            "nodes": nodes,
            "survives": survives,
            "data_automatically_applied": automatically_applied,
            "max_error": float(np.max(np.abs(leaf.points - control.points))),
            "initial_change": float(np.max(np.abs(transformed - Leaf(curve()).points))),
        }
        assert survives == (name != "apply_function")
    leaf = Leaf(curve())
    original = leaf.points.copy()
    pointwise_nonlinear(leaf)
    leaf.shift(RIGHT)
    expected = np.apply_along_axis(nonlinear, 1, original) + RIGHT
    assert np.allclose(leaf.points, expected)
    assert [kind for kind, _ in leaf.system.placement] == ["function", "affine"]
    results["nonlinear_then_shift_max_error"] = float(
        np.max(abs(leaf.points - expected))
    )
    record("h1_geometry", results)


def test_deepcopy_registry_and_dirty_setattr():
    system = System()
    leaves = [Leaf(curve(2000, phase), system) for phase in range(4)]
    leaf = leaves[0]
    leaf.amplitude = 1.1
    copy_times = []
    for _ in range(50):
        start = perf_counter_ns()
        clone = leaf.copy()
        copy_times.append((perf_counter_ns() - start) / 1e6)
    assert clone.system is not system
    assert len(clone.system.leaves) == 4
    assert clone.system.leaves[0] is clone
    assert all(
        a.source is not b.source
        for a, b in zip(leaves, clone.system.leaves, strict=True)
    )
    assert np.array_equal(clone.points, leaf.points)
    clone.amplitude = 1.7
    assert clone._dirty
    assert leaf.amplitude == 1.1
    record(
        "h3_copy",
        {
            "copies": len(copy_times),
            "median_ms": float(np.median(copy_times)),
            "p95_ms": float(np.percentile(copy_times, 95)),
            "registered_leaves_copied": len(clone.system.leaves),
            "samples_per_leaf": 2000,
            "control_points_per_leaf": len(leaf.points),
            "array_bytes_in_registry": sum(
                a.source.nbytes + a._cache.nbytes + a._shadow.nbytes
                for a in clone.system.leaves
            ),
        },
    )
