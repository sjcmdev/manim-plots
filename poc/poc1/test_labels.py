import tempfile
from pathlib import Path
from time import perf_counter_ns

import numpy as np
import pytest
from manim import MathTex, ValueTracker, VGroup, Write, linear, tempconfig

from poc1.points import ROOT, Leaf, System, record
from poc1.scene import ProbeScene, count_interpolation


class TexUnavailable(RuntimeError):
    pass


def mathtex(text):
    try:
        return MathTex(text)
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        raise TexUnavailable(str(error)) from error


def glyph_leaves(mobject, system):
    return VGroup(
        *[
            Leaf(glyph.points, system, "B").match_style(glyph)
            for glyph in mobject.family_members_with_points()
        ]
    )


def empty_media(prefix):
    (ROOT / "media").mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=ROOT / "media"))


def test_mathtex_leaf_write_and_rotation():
    media = empty_media("label-")
    with tempconfig({"media_dir": str(media)}):
        try:
            original = mathtex("123")
        except TexUnavailable as error:
            record(
                "h5_label",
                {
                    "status": "INCONCLUSIVE",
                    "error": str(error),
                    "media": str(media.relative_to(ROOT)),
                    "svg_files": len(list(media.rglob("*.svg"))),
                },
            )
            pytest.skip(str(error))
        system = System()
        system.matrix = np.eye(3)
        label = glyph_leaves(original, system)
        assert len(label) == len(original.family_members_with_points())
        assert all(
            isinstance(leaf, Leaf) for leaf in label.family_members_with_points()
        )
        expected = [leaf.points.copy() for leaf in label]
        scene = ProbeScene()
        scene.add(label)
        animation = Write(label)
        calls = count_interpolation(animation)
        scene.play(animation, run_time=0.6)
        assert len(calls) > 2
        assert all(
            np.array_equal(a, leaf.points)
            for a, leaf in zip(expected, label, strict=True)
        )
        rotation = system.rotate(0.4)
        assert all(
            np.allclose(a @ rotation.T, leaf.points)
            for a, leaf in zip(expected, label, strict=True)
        )
        scene.renderer.update_frame(scene)
        scene.renderer.camera.get_image().save(media / "rotated-label.png")
        record(
            "h5_label",
            {
                "status": "CONFIRMED",
                "leaves": len(label),
                "interpolate_calls": len(calls),
                "rendered_frames": len(scene.renderer.frames),
            },
        )


def maxn5(high):
    raw = high / 5
    unit = 10 ** np.floor(np.log10(raw))
    step = next(step * unit for step in [1, 2, 5, 10] if step * unit >= raw)
    return [int(k * step) for k in range(int(np.floor(high / step)) + 1)]


def test_label_workload():
    ticks = [maxn5(high) for high in np.linspace(10, 1000, 31)]
    strings = {str(value) for values in ticks for value in values}
    chars = set("".join(strings))
    assert len(strings) == 19 and len(chars) == 8
    record(
        "h5_workload",
        {
            "updates_including_endpoint": len(ticks),
            "unique_strings": sorted(strings),
            "unique_digits": sorted(chars),
            "max_ticks": max(map(len, ticks)),
        },
    )


def label_run(strategy, media):
    system = System()
    system.matrix = np.eye(3)
    labels = {}
    digits = {}
    measurements = []
    strings = set()
    new_counts = []
    tracker = ValueTracker(10)
    scene = ProbeScene()
    current = VGroup()
    # Scene updaters alone do not invalidate Cairo's static-family cache.
    current.add_updater(lambda _mob: None)
    scene.add(current)

    def update_labels(high):
        start = perf_counter_ns()
        values = maxn5(high)
        new = 0
        for value in values:
            text = str(value)
            strings.add(text)
            if text not in labels:
                if strategy == "whole_mathtex":
                    mob = mathtex(text)
                else:
                    for char in text:
                        if char not in digits:
                            digits[char] = mathtex(char)
                    # Same cache-and-copy mechanism as DecimalNumber._string_to_mob.
                    mob = VGroup(*(digits[char].copy() for char in text)).arrange(
                        buff=0.02
                    )
                mob.move_to([6 * value / high - 3, -0.5, 0])
                labels[text] = glyph_leaves(mob, system)
                new += 1
        # This experiment measures text generation, positioning and leaf conversion.
        # Position glyphs through the pipeline, avoiding VGroup's transient writes.
        for value in values:
            label = labels[str(value)]
            target = np.array([6 * value / high - 3, -0.5, 0])
            delta = target - label.get_center()
            for leaf in label:
                leaf.source = leaf.source + delta
                leaf._dirty = True
        current.submobjects = [labels[str(value)] for value in values]
        measurements.append((perf_counter_ns() - start) / 1e6)
        new_counts.append(new)

    scene.add_updater(lambda _dt: update_labels(tracker.get_value()))
    scene.play(tracker.animate.set_value(1000), run_time=2, rate_func=linear)
    # Finish sets the endpoint after the last scene updater.
    update_labels(1000)
    assert len(scene.renderer.frames) == 30
    assert len(measurements) == 31
    assert len(strings) > 6
    assert all(isinstance(leaf, Leaf) for leaf in current.family_members_with_points())
    return {
        "frames": len(scene.renderer.frames),
        "updates_including_endpoint": len(measurements),
        "unique_label_strings": len(strings),
        "unique_glyph_strings": len(digits),
        "new_labels_per_update": new_counts,
        "median_ms": float(np.median(measurements)),
        "p95_ms": float(np.percentile(measurements, 95)),
        "max_ms": max(measurements),
        "total_ms": sum(measurements),
        "tex_files": len(list(media.rglob("*.tex"))),
        "svg_files": len(list(media.rglob("*.svg"))),
    }


@pytest.mark.parametrize("strategy", ["whole_mathtex", "cached_digits"])
def test_range_label_cost(strategy):
    media = empty_media(strategy + "-")
    result = {"media": str(media.relative_to(ROOT)), "strategy": strategy}
    with tempconfig({"media_dir": str(media)}):
        for temperature in ["cold", "warm"]:
            try:
                result[temperature] = label_run(strategy, media)
            except TexUnavailable as error:
                result[temperature] = {"error": str(error), "status": "INCONCLUSIVE"}
                if temperature == "cold":
                    result["warm"] = {
                        "status": "INCONCLUSIVE",
                        "reason": "Cold run could not produce TeX cache.",
                    }
                record(f"h5_cost_{strategy}", result)
                pytest.skip(str(error))
    record(f"h5_cost_{strategy}", result)
