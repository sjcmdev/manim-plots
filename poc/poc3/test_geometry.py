from time import perf_counter_ns

import numpy as np
import pytest
from manim import DOWN, RED, RIGHT, UP, Dot, Group, VGroup, VMobject

from poc3.model import Frame, System, error, path, record
from poc3.scene import pixels


def wave(p):
    return p + np.array([0, 0.3 * np.sin(2 * p[0]), 0])


def bend(p):
    return p + np.array([0, 0.8 * p[0] ** 2, 0])


def jump(p):
    return p + np.array([0, 1 if p[0] >= 0.13 else -1, 0])


OPERATIONS = {
    "shift": lambda m: m.shift(RIGHT),
    "rotate": lambda m: m.rotate(0.4, axis=[1, 2, 3]),
    "scale": lambda m: m.scale(1.2),
    "stretch": lambda m: m.stretch(1.3, 0),
    "flip": lambda m: m.flip(UP),
    "apply_matrix": lambda m: m.apply_matrix([[1, 0.3, 0], [0.2, 1, 0], [0, 0, 1]]),
    "move_to": lambda m: m.move_to(UP),
    "next_to": lambda m: m.next_to(Dot(2 * RIGHT), DOWN),
    "to_corner": lambda m: m.to_corner(UP + RIGHT),
    "scale_to_fit_width": lambda m: m.scale_to_fit_width(4),
    "apply_function": lambda m: m.apply_function(wave),
    "apply_complex_function": lambda m: m.apply_complex_function(lambda z: z**2),
}


def plain(mobject):
    result = (
        VMobject().set_points(mobject.points.copy()).match_style(mobject)
        if isinstance(mobject, VMobject)
        else Group()
    )
    result.add(*(plain(m) for m in mobject.submobjects))
    return result


@pytest.mark.parametrize("name", OPERATIONS)
@pytest.mark.parametrize("wrapper", range(4))
def test_g1_native_operations(name, wrapper):
    ax = System(n=33)
    curve = ax.plot(samples=2001)
    dot = Dot([1, 1, 0])
    group = [ax, VGroup(ax), VGroup(ax, curve), VGroup(curve, ax, dot)][wrapper]
    reference = plain(group)
    native_frame = reference if wrapper == 0 else reference.submobjects[wrapper == 3]
    native_frame = native_frame.submobjects[0]
    original = ax.frame.reference.copy()
    OPERATIONS[name](reference)
    OPERATIONS[name](group)
    ax.set_x_range([-2.5, 2.5])
    coordinates = curve.data_points().copy()
    coordinates[:, 0] *= 1.2
    if name == "apply_function":
        expected = np.array([wave(p) for p in coordinates])
    elif name == "apply_complex_function":
        z = coordinates[:, 0] + 1j * coordinates[:, 1]
        expected = np.c_[(z**2).real, (z**2).imag, coordinates[:, 2]]
    else:
        probes = ax.frame.probes
        transform = np.linalg.solve(
            np.c_[original[probes, :2], np.ones(3)], native_frame.points[probes]
        )
        expected = np.c_[coordinates[:, :2], np.ones(len(coordinates))] @ transform
    maximum = error(curve.points, expected)
    dot_error = (
        error(dot.points, reference.submobjects[-1].points) if wrapper == 3 else 0
    )
    record(
        f"g1_{wrapper}_{name}",
        {"max_error": maximum, "dot_error": dot_error, "affine": ax.frame.is_affine},
    )
    assert dot_error < 1e-9
    if "function" not in name:
        assert maximum < 1e-9


def test_g1_grid_error_inverse_cost():
    rows = []
    x = np.linspace(-2.9, 2.9, 10001)
    dense = np.c_[x, np.sin(x), x * 0]
    for n in [9, 17, 33, 65]:
        for name, function in [
            ("wave", wave),
            (
                "square",
                lambda p: np.array([p[0] ** 2 - p[1] ** 2, 2 * p[0] * p[1], p[2]]),
            ),
            ("bend", bend),
            ("jump", jump),
        ]:
            ax = System(n)
            artist = ax.plot(samples=2000)
            if name == "square":
                ax.apply_complex_function(lambda z: z**2)
            else:
                ax.apply_function(function)
            expected = np.array([function(p) for p in dense])
            node_inputs = ax.frame.reference[::4]
            node_expected = np.array([function(p) for p in node_inputs])
            assert error(ax.frame.points[::4], node_expected) < 1e-9
            maximum = error(ax.c2p(dense), expected)
            batches = []
            for _ in range(30):
                start = perf_counter_ns()
                artist.rebuild()
                batches.append((perf_counter_ns() - start) / 1e6)
            probes = dense[::200]
            start = perf_counter_ns()
            inverse = ax.p2c(ax.c2p(probes))
            inverse_ms = (perf_counter_ns() - start) / 1e6
            rows.append(
                {
                    "n": n,
                    "function": name,
                    "max_scene_error": maximum,
                    "max_1080p_pixel_error": maximum * 1080 / 8,
                    "rebuild_median_ms": float(np.median(batches)),
                    "inverse_51_ms": inverse_ms,
                    "inverse_coordinate_error": error(inverse, probes),
                    "inverse_residual": error(ax.c2p(inverse), ax.c2p(probes)),
                }
            )
    record("g1_grid", rows)
    affine = Frame(17)
    affine.rotate(0.6, axis=[1, 2, 3]).shift(RIGHT).scale(0.8)
    probes = np.array([[8, -7, 3], [0.2, 0.1, 0]])
    start = perf_counter_ns()
    recovered = affine.inverse(affine.forward(probes))
    inverse_ms = (perf_counter_ns() - start) / 1e6
    affine_error = error(recovered, probes)
    record(
        "g1_affine_inverse",
        {
            "max_error": affine_error,
            "two_probes_ms": inverse_ms,
            "probes": probes.tolist(),
        },
    )
    assert affine_error < 1e-9


def test_frame_style_and_inplace_detection():
    ax = System()
    artist = ax.plot()
    assert artist.points is artist.points
    before = ax.frame.check()
    ax.frame.points[:] += RIGHT
    assert ax.frame.check() == before + 1
    for operation in [
        lambda: ax.set_opacity(1),
        lambda: ax.set_color(RED),
        lambda: ax.set_stroke(width=8),
    ]:
        operation()
        with_frame = pixels(ax)
        ax.remove(ax.frame)
        without_frame = pixels(ax)
        ax.add(ax.frame)
        assert np.array_equal(with_frame, without_frame)
    record("g1_frame", {"inplace_detected": True, "style_pixel_difference": 0})


def test_g1_smooth_aliasing_counterexample():
    ax = System(n=33)

    def alias(p):
        return p + np.array([0, 0.3 * np.sin(16 * np.pi * p[0] / 3), 0])

    ax.apply_function(alias)
    x = np.linspace(-3, 3, 10001)
    dense = np.c_[x, np.sin(x), x * 0]
    expected = np.array([alias(p) for p in dense])
    maximum = error(ax.c2p(dense), expected)
    record(
        "g1_aliasing",
        {
            "max_scene_error": maximum,
            "max_1080p_pixel_error": maximum * 135,
            "frame_classified_affine": ax.frame.is_affine,
        },
    )
    assert maximum > 0.299


def test_corner_buffer_matches_native():
    x = np.linspace(-3, 3, 2000)
    corners = np.c_[x, np.sin(x), x * 0]
    native = VMobject().set_points_as_corners(corners)
    assert error(path(corners), native.points) == 0
