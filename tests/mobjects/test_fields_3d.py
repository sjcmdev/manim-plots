"""Task 27: fields in 3D, rows VT, ST, FT of `docs/acceptance/27-fields-3d.md`.

The oracles: the grid and the mapped vectors by hand, RK4 written out, the local unit
vectors of ISO 80000-2, the view direction of `ThreeDCamera`'s angles.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import numpy as np
import pytest
from manim import (
    DEGREES,
    PI,
    RED,
    Arrow3D,
    Dot,
    Line3D,
    ThreeDScene,
    ValueTracker,
    VGroup,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, probe


def cube(**kwargs: Any) -> Any:
    """Equal units: one scene unit per data unit on every axis, x, y, z in (-2, 2)."""
    return mp.ThreeDAxes(
        x_range=(-2, 2, 1),
        y_range=(-2, 2, 1),
        z_range=(-2, 2, 1),
        x_length=4,
        y_length=4,
        z_length=4,
        **kwargs,
    )


def helix(p: np.ndarray) -> np.ndarray:
    return np.array([-p[1], p[0], 0.2])


def uniform(p: np.ndarray) -> np.ndarray:
    return np.array([1.0, 0.5, -0.25])


def start(arrow: Any) -> np.ndarray:
    return np.asarray(np.asarray(arrow.points)[0])


def far(arrow: Any) -> np.ndarray:
    points = np.asarray(arrow.get_all_points())
    s = start(arrow)
    return np.asarray(points[np.argmax(np.linalg.norm(points - s, axis=1))])


def unit(v: Any) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    out: np.ndarray = v / np.linalg.norm(v)
    return out


def view(phi: float, theta: float) -> np.ndarray:
    """From the scene towards the camera, as `ThreeDCamera` places it."""
    return np.array(
        [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
    )


def facing_error(arrow: Any, towards: np.ndarray, origin: Any = None) -> float:
    """How far the arrow's points leave the plane through its axis that faces
    ``towards`` most."""
    points = np.asarray(arrow.get_all_points())
    s = start(arrow if origin is None else origin)
    d = unit(points[np.argmax(np.linalg.norm(points - s, axis=1))] - s)
    n = unit(towards - (towards @ d) * d)
    return float(np.max(np.abs((points - s) @ n)))


def rk4(f: Any, p: np.ndarray, dt: float) -> np.ndarray:
    k1 = f(p)
    k2 = f(p + dt / 2 * k1)
    k3 = f(p + dt / 2 * k2)
    k4 = f(p + dt * k3)
    out: np.ndarray = p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return out


# --- VT -------------------------------------------------------------------------------


def test_vt1_the_default_grid_holds_210_arrows_in_manims_order():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(uniform)
    assert isinstance(field, mp.ArrowVectorField)
    xs, ys, zs = np.arange(-6, 7, 2), np.arange(-5, 6, 2), np.arange(-4, 5, 2)
    assert len(field.arrows) == 210
    expected = [ax.c2p(x, y, z) for x in xs for y in ys for z in zs]
    for arrow, point in zip(field.arrows, expected, strict=True):
        np.testing.assert_allclose(start(arrow), point, atol=1e-9)


def test_vt1_ranges_set_the_grid():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(
        uniform, x_range=(-1, 1, 1), y_range=(0, 1, 1), z_range=(2, 2, 1)
    )
    expected = [ax.c2p(x, y, 2) for x in (-1, 0, 1) for y in (0, 1)]
    assert len(field.arrows) == len(expected)
    for arrow, point in zip(field.arrows, expected, strict=True):
        np.testing.assert_allclose(start(arrow), point, atol=1e-9)


def test_vt2_one_layer_at_z_zero():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(uniform, three_dimensions=False)
    assert len(field.arrows) == 7 * 6
    for arrow in field.arrows:
        assert ax.p2c(start(arrow))[2] == pytest.approx(0, abs=1e-9)


def test_vt3_direction_is_the_mapped_vector_and_length_the_length_func():
    ax = mp.ThreeDAxes()  # unequal units: 10.5 / 12, 10.5 / 10, 6.5 / 8
    field = ax.get_vector_field(uniform, length_func=lambda norm: 0.5)
    arrow = field.arrows[0]
    origin = np.asarray(ax.c2p(-6, -5, -4))
    mapped = np.asarray(ax.c2p(-5, -4.5, -4.25)) - origin
    np.testing.assert_allclose(unit(far(arrow) - start(arrow)), unit(mapped), atol=1e-6)
    assert np.linalg.norm(far(arrow) - start(arrow)) == pytest.approx(0.5, abs=1e-6)


def test_vt4_a_flat_arrow_faces_the_default_view():
    ax = cube()
    field = ax.get_vector_field(uniform)
    for arrow in field.arrows[:5]:
        assert facing_error(arrow, view(0, -PI / 2)) < 1e-9


def test_vt4_flat_arrows_turn_with_the_camera():
    ax = cube()
    field = ax.get_vector_field(helix)
    picked = [field.arrows[k] for k in (0, 7, 20)]
    errors: list[float] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
            self.add(ax, field)
            self.wait(1 / 3)
            errors.extend(
                facing_error(a, view(65 * DEGREES, -45 * DEGREES)) for a in picked
            )
            self.move_camera(phi=30 * DEGREES, theta=60 * DEGREES, run_time=1 / 3)
            self.wait(1 / 3)
            errors.extend(
                facing_error(a, view(30 * DEGREES, 60 * DEGREES)) for a in picked
            )

    with tempconfig(RUN):
        Shot().render()
    assert len(errors) == 6
    assert max(errors) < 1e-6


def test_vt5_three_d_arrows():
    ax = mp.ThreeDAxes()
    one = {"x_range": (-6, -6, 1), "y_range": (-5, -5, 1), "z_range": (-4, -4, 1)}
    field = ax.get_vector_field(
        uniform, arrow="3d", length_func=lambda norm: 1.0, **one
    )
    first = field.arrows[0]
    assert isinstance(first, Arrow3D)
    np.testing.assert_allclose(first.get_start(), ax.c2p(-6, -5, -4), atol=1e-9)
    mapped = np.asarray(ax.c2p(-5, -4.5, -4.25)) - np.asarray(ax.c2p(-6, -5, -4))
    np.testing.assert_allclose(
        first.get_end(), first.get_start() + unit(mapped), atol=1e-6
    )
    with pytest.raises(ValueError, match="arrow"):
        ax.get_vector_field(uniform, arrow="cone")


def test_vt5_a_short_three_d_arrow_keeps_its_tip_forward():
    ax = cube()
    one = {"x_range": (0, 0, 1), "y_range": (0, 0, 1), "z_range": (0, 0, 1)}
    field = ax.get_vector_field(
        uniform, arrow="3d", length_func=lambda norm: 0.1, **one
    )
    arrow = field.arrows[0]
    start_, end_ = np.asarray(arrow.get_start()), np.asarray(arrow.get_end())
    d = unit(end_ - start_)
    along = (np.asarray(arrow.get_all_points()) - start_) @ d
    assert along.min() > -1e-6  # nothing behind the start
    assert along.max() == pytest.approx(0.1, abs=1e-6)  # the tip at the end


def test_vt6_colour_style_and_ranges_as_in_2d():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(helix)
    assert (
        field.arrows[0].get_color() != field.arrows[len(field.arrows) // 2].get_color()
    )
    one = ax.get_vector_field(helix, color=RED)
    assert all(a.get_color() == RED for a in one.arrows)
    field.arrows[3].set_color(RED)
    ax.set_z_range((-2, 2, 1))
    assert field.arrows[3].get_color() == RED


def test_vt6_an_animated_z_range_moves_the_arrows():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(
        uniform, x_range=(0, 0, 1), y_range=(0, 0, 1), z_range=(2, 2, 1)
    )
    arrow = field.arrows[0]
    gaps = probe(
        lambda s: s.play(ax.animate.set_z_range((-2, 2, 1))),
        lambda: float(np.linalg.norm(start(arrow) - ax.c2p(0, 0, 2))),
    )
    assert max(gaps) < 1e-9


def test_vt7_spherical_components():
    ax = cube()
    field = ax.get_vector_field(lambda p: np.array([1.0, 0.0, 0.0]), coords="spherical")
    for arrow in field.arrows:
        p = ax.p2c(start(arrow))
        if np.linalg.norm(p) < 1e-9:
            continue
        np.testing.assert_allclose(unit(far(arrow) - start(arrow)), unit(p), atol=1e-6)


def test_vt7_the_input_point_is_spherical():
    ax = cube()
    seen: list[np.ndarray] = []

    def record(p: np.ndarray) -> np.ndarray:
        seen.append(np.array(p, dtype=float))
        return np.array([0.0, 0.0, 1.0])  # along phi-hat

    ax.get_vector_field(
        record,
        coords="spherical",
        x_range=(0, 0, 1),
        y_range=(2, 2, 1),
        z_range=(0, 0, 1),
    )
    np.testing.assert_allclose(seen[0], (2, PI / 2, PI / 2), atol=1e-9)


def test_vt7_cylindrical_components():
    ax = cube()
    field = ax.get_vector_field(
        lambda p: np.array([0.0, 1.0, 0.0]), coords="cylindrical"
    )
    for arrow in field.arrows:
        x, y, _ = ax.p2c(start(arrow))
        if np.hypot(x, y) < 1e-9:
            continue
        np.testing.assert_allclose(
            unit(far(arrow) - start(arrow)), unit((-y, x, 0)), atol=1e-6
        )


def test_vt7_unknown_coordinates():
    with pytest.raises(ValueError, match="coords"):
        cube().get_vector_field(uniform, coords="polar")


# --- ST -------------------------------------------------------------------------------


def test_st1_lines_follow_a_helix_field():
    ax = cube()
    lines = ax.get_stream_lines(
        helix,
        x_range=(1, 1, 1),
        y_range=(0, 0, 1),
        z_range=(-1, -1, 1),
        noise_factor=0,
        virtual_time=2,
        padding=0,
    )
    assert len(lines.stream_lines) == 1
    points = np.array(
        [ax.p2c(p) for p in np.asarray(lines.stream_lines[0].points)[::4]]
    )
    np.testing.assert_allclose(np.hypot(points[:, 0], points[:, 1]), 1, atol=1e-3)
    assert np.all(np.diff(points[:, 2]) >= -1e-9)
    assert points[-1, 2] == pytest.approx(-1 + 0.2 * 2, abs=1e-2)


def test_st1_the_start_grid_is_three_dimensional():
    ax = mp.ThreeDAxes()
    lines = ax.get_stream_lines(helix, virtual_time=0.2)
    assert len(lines.stream_lines) == 210
    flat = ax.get_stream_lines(helix, virtual_time=0.2, three_dimensions=False)
    assert len(flat.stream_lines) == 42


def test_st2_flat_lines_stay_in_the_padded_box():
    ax = cube()
    lines = ax.get_stream_lines(helix, padding=1)
    for line in lines.stream_lines:
        data = np.array([ax.p2c(p) for p in np.asarray(line.points)[::4]])
        assert np.all(np.abs(data) <= 2 + 1e-6)  # clipped to the box


def test_st3_three_d_lines():
    ax = cube()
    lines = ax.get_stream_lines(
        helix,
        x_range=(1, 1, 1),
        y_range=(0, 0, 1),
        z_range=(0, 0, 1),
        noise_factor=0,
        line="3d",
    )
    line = lines.stream_lines[0]
    assert isinstance(line, VGroup)
    segments = list(line)
    assert segments and all(isinstance(s, Line3D) for s in segments)
    for a, b in pairwise(segments):
        np.testing.assert_allclose(a.get_end(), b.get_start(), atol=1e-9)
    with pytest.raises(NotImplementedError, match="line"):
        lines.start_animation()
    with pytest.raises(ValueError, match="line"):
        ax.get_stream_lines(helix, line="tube")


# --- FT -------------------------------------------------------------------------------


def test_ft1_nudge_in_three_dimensions():
    ax = mp.ThreeDAxes()
    field = ax.get_vector_field(helix)
    dot = Dot(ax.c2p(1, 0, 0))
    field.nudge(dot, dt=0.5, substeps=2)
    p = np.array([1.0, 0.0, 0.0])
    for _ in range(2):
        p = rk4(helix, p, 0.25)
    np.testing.assert_allclose(dot.get_center(), ax.c2p(*p), atol=1e-9)


def test_ft1_flow_along_a_helix():
    ax = cube()
    field = ax.get_vector_field(helix)
    dot = Dot(ax.c2p(1, 0, 0))

    def construct(scene: Any) -> None:
        scene.add(ax, dot)
        scene.play(mp.Flow(field, dot, run_time=PI))

    radii = probe(
        construct, lambda: float(np.linalg.norm(ax.p2c(dot.get_center())[:2]))
    )
    np.testing.assert_allclose(radii, 1.0, atol=1e-3)
    np.testing.assert_allclose(dot.get_center(), ax.c2p(-1, 0, 0.2 * PI), atol=1e-3)


def test_ft2_get_vector_in_three_dimensions():
    ax = mp.ThreeDAxes()
    z = ValueTracker(3.0)
    vector = ax.get_vector((1, 2, z))
    assert isinstance(vector, mp.HelperGroup)
    np.testing.assert_allclose(start(vector.line), ax.c2p(0, 0, 0), atol=1e-9)
    np.testing.assert_allclose(far(vector), ax.c2p(1, 2, 3), atol=1e-6)
    assert facing_error(vector, view(0, -PI / 2), origin=vector.line) < 1e-9
    gaps = probe(
        lambda scene: scene.play(z.animate.set_value(-1)),
        lambda: float(np.linalg.norm(far(vector) - ax.c2p(1, 2, z.get_value()))),
    )
    assert max(gaps) < 1e-6


def test_ft3_implicit_curves_stay_refused():
    with pytest.raises(NotImplementedError, match="ThreeDAxes"):
        mp.ThreeDAxes().plot_implicit_curve(lambda x, y: x)
