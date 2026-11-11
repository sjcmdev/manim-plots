import numpy as np
import pytest
from manim import (
    RIGHT,
    AddTextLetterByLetter,
    ApplyWave,
    Circumscribe,
    Create,
    Flash,
    Indicate,
    Line,
    MoveAlongPath,
    PhaseFlow,
    RemoveTextLetterByLetter,
    ShowIncreasingSubsets,
    ShowPassingFlash,
    Uncreate,
    ValueTracker,
    VGroup,
    Wiggle,
    Write,
    linear,
)

from poc1.points import Leaf, OverrideLeaf, System, curve, record
from poc1.scene import ProbeScene, count_interpolation

RESTORING = [
    Create,
    Write,
    ShowPassingFlash,
    Indicate,
    Wiggle,
    ApplyWave,
    Flash,
    Circumscribe,
]


@pytest.mark.parametrize("variant", ["A", "B"])
@pytest.mark.parametrize("animation_type", [*RESTORING, Uncreate])
def test_animation_matrix(variant, animation_type):
    run_animation_case(variant, animation_type)


def run_animation_case(variant, animation_type, suffix=""):
    system = System()
    leaf = Leaf(curve(), system, variant)
    sibling = Leaf(curve(31, 1.0), system, variant)
    sibling_points = sibling.points.copy()
    coordinates = np.array([[0, 0, 0], [1, 2, 0], [-1, -1, 0]])
    c2p = system.c2p(coordinates).copy()
    scene = ProbeScene()
    # Cairo otherwise treats scene-updater-only objects as static.
    leaf.add_updater(lambda _mob: None)
    scene.add(leaf, sibling)
    tracker = ValueTracker(0)
    changes = []

    def change_data(_dt):
        if tracker.get_value() >= 0.25 and leaf.amplitude == 1.0:
            leaf.amplitude = 1.5
            changes.append(tracker.get_value())

    scene.add_updater(change_data)
    animation = animation_type(leaf)
    calls = count_interpolation(animation)
    scene.play(animation, tracker.animate(rate_func=linear).set_value(1), run_time=0.6)
    assert not scene.renderer.skip_animations
    assert len(calls) > 2
    assert len(set(calls)) > 2
    assert len(scene.renderer.frames) >= 8
    assert changes
    # Observe the actual post-play buffer before allowing the getter to reconcile it.
    raw_clean = np.array_equal(leaf._cache, leaf.derived())
    points = leaf.points.copy()
    placement_ok = not system.placement
    clean = np.array_equal(points, leaf.derived())
    siblings_ok = np.array_equal(sibling.points, sibling_points)
    c2p_ok = np.array_equal(system.c2p(coordinates), c2p)
    applied = not leaf._dirty and clean
    degenerate = len(points) == 0 or np.all(points == points[0])
    expected = {
        "A": {
            "Wiggle": (False, False, False, False),
            "ApplyWave": (True, False, True, False),
            "Uncreate": (True, False, True, False),
        },
        "B": {"ShowPassingFlash": (True, False, True, False)},
    }
    if variant == "B" or animation_type.__name__ in expected[variant]:
        assert (placement_ok, clean, siblings_ok and c2p_ok, applied) == expected[
            variant
        ].get(animation_type.__name__, (True, True, True, True))
    if animation_type is Uncreate:
        assert bool(degenerate) == (variant == "A")
    result = {
        "placement_unchanged": placement_ok,
        "buffer_equals_derived": clean,
        "raw_buffer_equals_derived": raw_clean,
        "c2p_unchanged": c2p_ok,
        "sibling_unchanged": siblings_ok,
        "data_applied": applied,
        "data_changes": len(changes),
        "data_value": leaf.amplitude,
        "degenerate": bool(degenerate),
        "in_scene": leaf in scene.mobjects,
        "placement_nodes": len(system.placement),
        "placement_version": system.version,
        "max_c2p_delta": float(np.max(abs(system.c2p(coordinates) - c2p))),
        "max_sibling_delta": float(np.max(abs(sibling.points - sibling_points))),
        "buffer_shadow_max_delta": (
            float(np.max(abs(leaf._cache - leaf._shadow)))
            if leaf._cache.shape == leaf._shadow.shape
            else None
        ),
        "buffer_derived_max_delta": (
            float(np.max(abs(points - leaf.derived())))
            if points.shape == leaf.derived().shape
            else None
        ),
        "interpolate_calls": len(calls),
        "distinct_alphas": len(set(calls)),
        "rendered_frames": len(scene.renderer.frames),
        "leaf_suspend_calls": leaf._suspend_calls,
    }
    if animation_type is Uncreate:
        assert leaf not in scene.mobjects
        leaf.refresh()
        assert np.array_equal(leaf.points, leaf.derived())
        result["refresh_restores"] = True
    record(f"h2_{variant}_{animation_type.__name__}{suffix}", result)
    return result


@pytest.mark.parametrize("variant", ["A", "B"])
def test_create_legal_empty_contents(variant, monkeypatch):
    original_empty = np.empty
    shadow = Leaf(curve()).points.copy()

    def empty(shape, *args, **kwargs):
        result = original_empty(shape, *args, **kwargs)
        if result.shape == shadow.shape:
            result[:] = shadow
        return result

    # np.empty may legally return these bytes. Reproduce allocator-dependent behavior.
    monkeypatch.setattr(np, "empty", empty)
    result = run_animation_case(variant, Create, "_seeded_empty")
    assert result["data_applied"] == (variant == "B")


@pytest.mark.parametrize("kind", ["native", "override"])
def test_b_persistent_animate_shift(kind):
    leaf = (Leaf if kind == "native" else OverrideLeaf)(curve(), variant="B")
    initial = leaf.points.copy()
    scene = ProbeScene()
    scene.add(leaf)
    scene.play(leaf.animate.shift(RIGHT), run_time=0.6, rate_func=linear)
    before = leaf.points.copy()
    leaf.refresh()
    after = leaf.points.copy()
    persistent = np.allclose(after, initial + RIGHT)
    assert persistent == (kind == "override")
    record(
        f"h2_shift_{kind}",
        {
            "placement_nodes": len(leaf.system.placement),
            "before_refresh_max_error": float(np.max(abs(before - initial - RIGHT))),
            "after_refresh_max_error": float(np.max(abs(after - initial - RIGHT))),
            "persistent": persistent,
            "rendered_frames": len(scene.renderer.frames),
        },
    )


@pytest.mark.parametrize("variant", ["A", "B"])
@pytest.mark.parametrize(
    "name",
    [
        "ShowIncreasingSubsets",
        "AddTextLetterByLetter",
        "RemoveTextLetterByLetter",
        "PhaseFlow",
        "MoveAlongPath",
    ],
)
def test_animations_without_suspension(variant, name):
    system = System()
    leaves = [Leaf(curve(8, phase), system, variant) for phase in range(2)]
    group = VGroup(*leaves)
    if name == "PhaseFlow":
        animation = PhaseFlow(lambda _p: RIGHT, leaves[0])
    elif name == "MoveAlongPath":
        animation = MoveAlongPath(leaves[0], Line([0, 0, 0], [1, 0, 0]))
    else:
        cls = {
            "ShowIncreasingSubsets": ShowIncreasingSubsets,
            "AddTextLetterByLetter": AddTextLetterByLetter,
            "RemoveTextLetterByLetter": RemoveTextLetterByLetter,
        }[name]
        # These methods accept a glyph-like VGroup at runtime; no Text construction.
        animation = cls(group)
    assert animation.suspend_mobject_updating is False
    calls = count_interpolation(animation)
    scene = ProbeScene()
    scene.add(group)
    scene.play(animation, run_time=0.6, rate_func=linear)
    assert len(calls) > 2 and len(scene.renderer.frames) >= 8
    points = [leaf.points.copy() for leaf in leaves]
    clean_before_refresh = [
        np.array_equal(leaf.points, leaf.derived()) for leaf in leaves
    ]
    for leaf in leaves:
        leaf.refresh()
    record(
        f"h2_no_suspend_{variant}_{name}",
        {
            "placement_nodes": len(system.placement),
            "placement_version": system.version,
            "transient_flags": [leaf._transient for leaf in leaves],
            "clean_before_refresh": clean_before_refresh,
            "refresh_changed": [
                not np.array_equal(a, b.points)
                for a, b in zip(points, leaves, strict=True)
            ],
            "interpolate_calls": len(calls),
            "rendered_frames": len(scene.renderer.frames),
            "suspends": sum(leaf._suspend_calls for leaf in leaves),
        },
    )
