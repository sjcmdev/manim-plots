"""Task 24: the 3D system, rows TS, TA, TC, TF, TK of `docs/acceptance/24-three-d.md`.

The oracles: Manim's own `ThreeDAxes` where `mp.ThreeDAxes` keeps its behaviour, and
the separable map written out by hand everywhere else.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest
from manim import (
    DEGREES,
    DOWN,
    OUT,
    PI,
    RIGHT,
    UP,
    ManimColor,
    Rotate,
    ThreeDAxes,
    ThreeDScene,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, dense, probe


def pts(mob) -> np.ndarray:
    return np.asarray(mob.points)


def helix(t):
    return np.array([np.cos(t), np.sin(t), t])


# --- TS -------------------------------------------------------------------------------


@pytest.mark.parametrize("scale", ["linear", "log", "symlog"])
def test_ts1_c2p_and_p2c_are_inverse(scale):
    ax = mp.ThreeDAxes(
        x_range=(0.5, 8, 1), y_range=(-3, 3, 1), z_range=(1, 100, 1), z_scale=scale
    )
    for point in [(1, 0, 1), (2.5, -1.5, 10), (7, 2, 50)]:
        np.testing.assert_allclose(ax.p2c(ax.c2p(*point)), point, atol=1e-9)


def test_ts1_two_coordinates_mean_z_zero_and_arrays_broadcast():
    ax = mp.ThreeDAxes()
    np.testing.assert_allclose(ax.c2p(1, 2), ax.c2p(1, 2, 0))
    many = ax.c2p(np.array([1.0, 2.0]), np.array([0.0, 1.0]), np.array([1.0, -1.0]))
    np.testing.assert_allclose(many[:, 1], ax.c2p(2, 1, -1))  # columns, as Manim


def test_ts1_log_z_by_hand():
    ax = mp.ThreeDAxes(z_range=(1, 1000), z_scale="log")
    # z_length 6.5 centred on the origin; three decades
    assert ax.c2p(0, 0, 10)[2] == pytest.approx(-3.25 + 6.5 / 3)
    assert ax.c2p(0, 0, 1000)[2] == pytest.approx(3.25)


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("twinx", ()),
        ("twiny", ()),
        ("secondary_xaxis", ("top",)),
        ("get_area", (None,)),
        ("get_vertical_line", ((0, 0, 0),)),
    ],
)
def test_ts3_2d_only_methods_refuse(method, args):
    ax = mp.ThreeDAxes()
    with pytest.raises(NotImplementedError, match="ThreeDAxes"):
        getattr(ax, method)(*args)


def test_ts3_polar_helpers_keep_manims_meaning_in_the_plane():
    ours, theirs = mp.ThreeDAxes(), ThreeDAxes()
    np.testing.assert_allclose(ours.pr2pt(2, PI / 3), theirs.pr2pt(2, PI / 3))


def test_ts3_not_star_exported():
    assert "ThreeDAxes" not in mp.__all__
    assert mp.ThreeDAxes.__module__.startswith("manim_plots")


# --- TA -------------------------------------------------------------------------------


CUSTOM = {
    "x_range": (0, 4, 1),
    "y_range": (0, 4, 1),
    "z_range": (0, 2, 0.5),
    "x_length": 4,
    "y_length": 4,
    "z_length": 3,
}


@pytest.mark.parametrize("kwargs", [{}, CUSTOM, {"z_normal": RIGHT}])
def test_ta1_the_map_and_the_axes_are_manims(kwargs):
    ours, theirs = mp.ThreeDAxes(**kwargs), ThreeDAxes(**kwargs)
    for point in [(1, 2, 3), (0, 0, 0), (-2, 1, -1)]:
        np.testing.assert_allclose(ours.c2p(*point), theirs.c2p(*point), atol=1e-9)
    for a, b in zip(
        (ours.x_axis, ours.y_axis, ours.z_axis),
        (theirs.x_axis, theirs.y_axis, theirs.z_axis),
        strict=True,
    ):
        np.testing.assert_allclose(a.get_start(), b.get_start(), atol=1e-9)
        np.testing.assert_allclose(a.get_end(), b.get_end(), atol=1e-9)
        assert a.get_unit_size() == pytest.approx(b.get_unit_size())


def test_ta1_defaults_by_number():
    ax = mp.ThreeDAxes()
    np.testing.assert_allclose(ax.c2p(1, 2, 3), (0.875, 2.1, 2.4375), atol=1e-9)
    np.testing.assert_allclose(ax.z_range, (-4, 4, 1))


@pytest.mark.parametrize("normal", [DOWN, RIGHT])
def test_ta1_ta2_every_manim_tick_is_drawn_where_manims_is(normal):
    ours, theirs = mp.ThreeDAxes(z_normal=normal), ThreeDAxes(z_normal=normal)
    for a, b in zip(
        (ours.x, ours.y, ours.z),
        (theirs.x_axis, theirs.y_axis, theirs.z_axis),
        strict=True,
    ):
        for value, tick in zip(b.get_tick_range(), b.ticks, strict=True):
            mine = a.ticks.at(float(value))
            np.testing.assert_allclose(mine.get_center(), tick.get_center(), atol=1e-6)
            direction = pts(mine)[-1] - pts(mine)[0]
            theirs_direction = tick.get_end() - tick.get_start()
            assert abs(np.dot(direction, theirs_direction)) == pytest.approx(
                np.linalg.norm(direction) * np.linalg.norm(theirs_direction)
            )


def test_ta3_the_z_axis_is_an_axis_with_its_controls():
    ax = mp.ThreeDAxes(z_axis_config={"include_numbers": True})
    assert ax.get_z_axis() is ax.z_axis is ax.z
    with tempconfig(RUN):
        ax.z.set_locator(mp.MultipleLocator(2))
    assert len(ax.z.numbers) > 0
    assert all(float(v) % 2 == 0 for v in ax.z.get_tick_range())


def test_ta4_labels_are_placed_as_manims():
    with tempconfig(RUN):
        ours, theirs = mp.ThreeDAxes(), ThreeDAxes()
        np.testing.assert_allclose(
            ours.get_z_axis_label("z").get_center(),
            theirs.get_z_axis_label("z").get_center(),
            atol=0.05,
        )
        labels = ours.get_axis_labels()
    assert len(labels) == 3


def test_ta5_plot_lies_in_the_z_zero_plane_and_i2gp():
    ours, theirs = mp.ThreeDAxes(), ThreeDAxes()
    curve = ours.plot(np.sin)
    assert np.ptp(pts(curve)[:, 2]) == pytest.approx(0, abs=1e-12)
    np.testing.assert_allclose(
        ours.i2gp(1.0, curve), theirs.i2gp(1.0, theirs.plot(np.sin)), atol=1e-6
    )


# --- TC -------------------------------------------------------------------------------


def test_tc1_a_helix_against_its_analytic_points():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-3, 3))
    drawn = dense(pts(curve), per_curve=32)
    for t in np.linspace(-3, 3, 200):
        target = ax.c2p(*helix(t))
        assert np.min(np.linalg.norm(drawn - target, axis=1)) < 1e-3


def test_tc1_takes_the_cycle_and_a_label():
    ax = mp.ThreeDAxes()
    a = ax.plot_parametric_curve(helix, t_range=(-1, 1), label="helix")
    b = ax.plot(np.cos)
    assert a.get_color() != b.get_color()
    assert a in ax.artists and b in ax.artists


def test_tc2_scatter_and_line():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([1, 2], [0, 1], [2, -1])
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(1, 0, 2), atol=1e-9)
    np.testing.assert_allclose(dots[1].get_center(), ax.c2p(2, 1, -1), atol=1e-9)
    line = ax.line([0, 1, 2], [0, 1, 0], [0, 1, 2])
    for point in [(0, 0, 0), (1, 1, 1), (2, 0, 2)]:
        target = ax.c2p(*point)
        assert np.min(np.linalg.norm(pts(line) - target, axis=1)) < 1e-9


# --- TF -------------------------------------------------------------------------------


def test_tf1_artists_follow_a_shift_and_a_rotation():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-1, 1))
    dots = ax.scatter([1], [1], [1])
    ax.shift(RIGHT + OUT).rotate(PI / 3, axis=UP)
    np.testing.assert_allclose(pts(curve)[0], ax.c2p(*helix(-1)), atol=1e-6)
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(1, 1, 1), atol=1e-6)
    np.testing.assert_allclose(
        ax.z.ticks.at(1.0).get_center(), ax.c2p(0, 0, 1), atol=1e-6
    )


def test_tf1_artists_follow_an_animated_rotation():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-1, 1))
    gaps = probe(
        lambda s: s.play(Rotate(ax, PI / 2, axis=RIGHT)),
        lambda: float(np.linalg.norm(pts(curve)[0] - ax.c2p(*helix(-1)))),
    )
    assert max(gaps) < 1e-6


def test_tf2_apply_function_is_refused():
    ax = mp.ThreeDAxes()
    with pytest.raises(NotImplementedError, match="affine"):
        ax.apply_function(lambda p: p + 0.1 * p**2)


def test_tf3_set_z_range_moves_the_artists():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([0], [0], [2])
    tick = ax.z.ticks.at(2.0)
    ax.set_z_range((-2, 2, 1))
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(0, 0, 2), atol=1e-9)
    assert dots[0].get_center()[2] == pytest.approx(3.25)
    assert ax.z.ticks.at(2.0) is tick


def test_tf3_an_animated_z_range():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([0], [0], [2])
    heights = probe(
        lambda s: s.play(ax.animate.set_z_range((-2, 2, 1))),
        lambda: float(dots[0].get_center()[2]),
    )
    assert heights[0] == pytest.approx(1.625, abs=1e-6)
    assert all(b >= a - 1e-9 for a, b in pairwise(heights))
    assert dots[0].get_center()[2] == pytest.approx(3.25)


def test_tf4_a_z_range_outside_the_log_domain_is_refused():
    with pytest.raises(ValueError, match="z_range"):
        mp.ThreeDAxes(z_range=(0, 10), z_scale="log")


def test_tf5_a_theme_fills_the_defaults():
    ax = mp.ThreeDAxes(theme="origin")
    curve = ax.plot(np.sin)
    assert curve.get_color().to_hex() == ManimColor(mp.CYCLES["origin"][0]).to_hex()


# --- TK -------------------------------------------------------------------------------


def test_tk1_a_helix_is_cut_at_the_box():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-5, 5))
    z = dense(pts(curve))[:, 2]
    assert z.max() == pytest.approx(3.25, abs=1e-6)
    assert z.min() == pytest.approx(-3.25, abs=1e-6)
    loose = ax.plot_parametric_curve(helix, t_range=(-5, 5), clip=False)
    assert pts(loose)[:, 2].max() > 4


def test_tk2_clip_per_axis_takes_three_entries():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-5, 5), clip=(True, True, False))
    assert pts(curve)[:, 2].max() > 4
    with pytest.raises(ValueError, match="clip"):
        ax.plot_parametric_curve(helix, t_range=(-5, 5), clip=(True, True))


def test_tk3_scatter_outside_the_box_is_not_drawn():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([0, 0], [0, 0], [1, 9])
    # hidden as in 2D: the marker stays, its opacity drops to zero
    assert dots[0].get_fill_opacity() > 0
    assert dots[1].get_fill_opacity() == 0


def test_tc3_a_camera_move_changes_no_artist():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(-1, 1))
    before = pts(curve).copy()

    class Turn(ThreeDScene):
        def construct(self) -> None:
            self.add(ax, curve)
            self.move_camera(phi=60 * DEGREES, theta=-30 * DEGREES, run_time=0.5)

    with tempconfig(RUN):
        Turn().render()
    np.testing.assert_allclose(pts(curve), before)
