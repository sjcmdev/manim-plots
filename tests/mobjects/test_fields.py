"""Task 21: fields and flow, the Manim layer.

Rows VF, SL, FL and GV of `docs/acceptance/21-fields-flow.md`. Arrows and lines are
checked against values computed by hand from `c2p` and the field function.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import RED, Dot, Scene, ValueTracker

import manim_plots as mp

from .helpers import probe


def axes(**kwargs):
    """x in (-2, 2), y in (-1, 1), unequal units: 2 and 1.5 scene units per unit."""
    return mp.Axes(
        x_range=(-2, 2, 1), y_range=(-1, 1, 0.5), x_length=8, y_length=3, **kwargs
    )


def rotation(p):
    return np.array([-p[1], p[0], 0.0])


def uniform(p):
    return np.array([1.0, 0.5, 0.0])


def start(arrow) -> np.ndarray:
    return np.asarray(arrow.points)[0]


def far(arrow) -> np.ndarray:
    points = np.asarray(arrow.get_all_points())
    s = start(arrow)
    return points[np.argmax(np.linalg.norm(points - s, axis=1))]


def unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    out: np.ndarray = v / np.linalg.norm(v)
    return out


# --- VF ---------------------------------------------------------------------------


def test_vf1_one_arrow_per_grid_point_starting_on_it():
    ax = axes()
    field = ax.get_vector_field(uniform)
    assert isinstance(field, mp.ArrowVectorField)
    xs, ys = np.arange(-2.0, 2.5, 1.0), np.arange(-1.0, 1.25, 0.5)
    assert len(field.arrows) == len(xs) * len(ys)
    expected = [ax.c2p(x, y) for x in xs for y in ys]  # Manim's order: x outer
    for arrow, point in zip(field.arrows, expected, strict=True):
        np.testing.assert_allclose(start(arrow), point, atol=1e-9)


def test_vf1_direction_is_the_mapped_data_vector_and_length_the_length_func():
    ax = axes()
    field = ax.get_vector_field(uniform, length_func=lambda norm: 0.5)
    arrow = field.arrows[0]
    origin = np.asarray(ax.c2p(0, 0))
    mapped = np.asarray(ax.c2p(1.0, 0.5)) - origin  # unequal units bend the direction
    np.testing.assert_allclose(unit(far(arrow) - start(arrow)), unit(mapped), atol=1e-6)
    assert np.linalg.norm(far(arrow) - start(arrow)) == pytest.approx(0.5, abs=1e-6)


def test_vf1_the_default_length_is_manims():
    ax = axes()
    field = ax.get_vector_field(uniform)
    norm = float(np.hypot(1.0, 0.5))
    expected = 0.45 / (1 + np.exp(-norm))
    arrow = field.arrows[0]
    assert np.linalg.norm(far(arrow) - start(arrow)) == pytest.approx(
        expected, abs=1e-6
    )


def test_vf2_colours_by_norm_or_one_colour():
    ax = axes()
    field = ax.get_vector_field(rotation)
    centre = field.arrows[len(field.arrows) // 2]  # (0, 0): the zero vector
    corner = field.arrows[-1]
    assert centre.get_color() != corner.get_color()
    one = ax.get_vector_field(rotation, color=RED)
    assert all(a.get_color() == RED for a in one.arrows)


def test_vf3_a_style_on_one_arrow_survives_a_range_change():
    ax = axes()
    field = ax.get_vector_field(uniform)
    field.arrows[3].set_color(RED)
    ax.set_x_range((-2, 2))  # same grid, re-derived
    assert field.arrows[3].get_color() == RED


def test_fs4_an_animated_range_resamples_the_field():
    ax = axes()
    field = ax.get_vector_field(uniform)

    def construct(scene: Scene) -> None:
        scene.add(ax, field)
        scene.play(ax.animate.set_x_range((-4, 4, 2)), run_time=1)

    probe(construct, lambda: None)
    assert len(field.arrows) == 5 * 5
    np.testing.assert_allclose(start(field.arrows[0]), ax.c2p(-4, -1), atol=1e-6)


def test_fs2_a_vectorized_field():
    ax = axes()
    calls = []

    def batch(points):
        calls.append(np.shape(points))
        return np.column_stack((np.ones(len(points)), np.zeros(len(points))))

    field = ax.get_vector_field(batch, use_vectorized=True)
    assert len(calls) == 1 and calls[0] == (len(field.arrows), 3)


# --- SL ---------------------------------------------------------------------------


def test_sl1_stream_lines_stay_in_the_padded_box_and_are_clipped():
    ax = axes()
    lines = ax.get_stream_lines(rotation, x_range=(-2, 2, 1), y_range=(-1, 1, 1))
    assert isinstance(lines, mp.StreamLines)
    assert len(lines.stream_lines) == 5 * 3
    lower, upper = ax.bounds.lower, ax.bounds.upper
    for line in lines.stream_lines:
        points = np.asarray(line.points)
        if len(points):
            assert (points[:, :2] >= lower - 1e-9).all()
            assert (points[:, :2] <= upper + 1e-9).all()


def test_sl1_noise_is_seeded():
    ax = axes()
    a = ax.get_stream_lines(rotation, noise_factor=0.3)
    b = ax.get_stream_lines(rotation, noise_factor=0.3)
    for p, q in zip(a.stream_lines, b.stream_lines, strict=True):
        np.testing.assert_array_equal(p.points, q.points)


def test_sl1_a_rotation_field_line_follows_its_circle():
    ax = mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), x_length=6, y_length=6)
    lines = ax.get_stream_lines(
        rotation, x_range=(1, 1.5, 1), y_range=(0, 0.5, 1), virtual_time=6, dt=0.05
    )
    points = np.asarray(lines.stream_lines[0].get_anchors())
    radii = np.linalg.norm(np.array([ax.p2c(p)[:2] for p in points]), axis=1)
    np.testing.assert_allclose(radii, 1.0, atol=1e-3)


def test_sl3_create_and_the_flow_animation_run():
    ax = axes()
    lines = ax.get_stream_lines(rotation, x_range=(-2, 2, 2), y_range=(-1, 1, 1))

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(lines.create(), run_time=1)
        lines.start_animation(warm_up=False, flow_speed=1)
        scene.wait(0.5)
        scene.play(lines.end_animation())

    probe(construct, lambda: None)


# --- FL ---------------------------------------------------------------------------


def rk4(f, p, dt):
    k1 = f(p)
    k2 = f(p + dt / 2 * k1)
    k3 = f(p + dt / 2 * k2)
    k4 = f(p + dt * k3)
    return p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


def test_fl1_nudge_moves_a_mobject_by_rk4_in_data_space():
    ax = axes()
    field = ax.get_vector_field(rotation)
    dot = Dot(ax.c2p(1, 0))
    field.nudge(dot, dt=0.5, substeps=2)
    p = np.array([1.0, 0.0, 0.0])
    for _ in range(2):
        p = rk4(rotation, p, 0.25)
    np.testing.assert_allclose(dot.get_center(), ax.c2p(p[0], p[1]), atol=1e-9)


def test_fl2_flow_moves_a_dot_round_the_circle():
    ax = mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), x_length=6, y_length=6)
    field = ax.get_vector_field(rotation)
    dot = Dot(ax.c2p(1, 0))

    def construct(scene: Scene) -> None:
        scene.add(ax, dot)
        scene.play(mp.Flow(field, dot, speed=1, run_time=np.pi))

    radii = probe(
        construct, lambda: float(np.linalg.norm(ax.p2c(dot.get_center())[:2]))
    )
    np.testing.assert_allclose(radii, 1.0, atol=1e-3)
    np.testing.assert_allclose(dot.get_center(), ax.c2p(-1, 0), atol=1e-3)


def test_fl1_the_nudge_updater_and_submobject_movement():
    ax = axes()
    field = ax.get_vector_field(rotation)
    dot = Dot(ax.c2p(1, 0))
    dot.add_updater(field.get_nudge_updater(speed=1))

    def construct(scene: Scene) -> None:
        scene.add(ax, dot)
        scene.wait(1)

    probe(construct, lambda: None)
    assert np.linalg.norm(ax.p2c(dot.get_center())[:2] - [1, 0]) > 0.5


# --- GV ---------------------------------------------------------------------------


def test_gv1_get_vector_from_the_origin_follows_the_system():
    ax = axes()
    x = ValueTracker(1.0)
    vector = ax.get_vector((x, 0.5))
    assert isinstance(vector, mp.HelperGroup)
    np.testing.assert_allclose(start(vector.line), ax.c2p(0, 0), atol=1e-9)
    np.testing.assert_allclose(far(vector), ax.c2p(1, 0.5), atol=1e-6)
    ax.set_x_range((-4, 4))
    np.testing.assert_allclose(far(vector), ax.c2p(1, 0.5), atol=1e-6)


def test_gv2_the_implicit_circle():
    ax = mp.Axes()
    curve = ax.plot_implicit_curve(lambda x, y: x**2 + y**2 - 4)
    points = np.asarray(curve.get_anchors())
    radii = np.linalg.norm(np.array([ax.p2c(p)[:2] for p in points]), axis=1)
    np.testing.assert_allclose(radii, 2.0, atol=1e-3)
    assert len(points) > 16
