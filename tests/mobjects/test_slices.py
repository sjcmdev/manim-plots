"""Task 28: slices, `plot_slice`, shadows and `zdir`, rows SC, PS, SH, ZD of
`docs/acceptance/28-slices.md`.

The oracles: the surface's function at the drawn points, matplotlib's `juggle_axes`
written out, the far pane's side read from the camera's angles as task 24 chooses it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import (
    DEGREES,
    PI,
    RED,
    Dot,
    ManimColor,
    ThreeDScene,
    ValueTracker,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, dense, probe


def anchors(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def saddle(u: Any, v: Any, a: float = 0.5) -> Any:
    return a * u * v


def surface(ax: Any, **kwargs: Any) -> Any:
    return ax.plot_surface(saddle, (-2, 2), (-2, 2), resolution=8, **kwargs)


def helix(t: float) -> np.ndarray:
    return np.array([np.cos(t), np.sin(t), t / 4])


# --- SC -------------------------------------------------------------------------------


def test_sc1_a_slice_lies_on_the_surface_exactly():
    ax = mp.ThreeDAxes()
    cut = surface(ax).slice(x=1)
    assert isinstance(cut, mp.ParametricPlot)
    drawn = data(ax, anchors(cut))
    np.testing.assert_allclose(drawn[:, 0], 1, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 2], 0.5 * drawn[:, 1], atol=1e-9)
    assert drawn[:, 1].min() == pytest.approx(-2)
    assert drawn[:, 1].max() == pytest.approx(2)


def test_sc1_along_x():
    ax = mp.ThreeDAxes()
    drawn = data(ax, anchors(surface(ax).slice(y=-1.5)))
    np.testing.assert_allclose(drawn[:, 1], -1.5, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 2], -0.75 * drawn[:, 0], atol=1e-9)


def test_sc2_a_height_slice_is_a_contour():
    ax = mp.ThreeDAxes()
    cut = surface(ax).slice(z=0.5)
    assert isinstance(cut, mp.ContourPlot)
    drawn = data(ax, anchors(cut.at(0.5)))
    np.testing.assert_allclose(drawn[:, 2], 0.5, atol=1e-9)
    np.testing.assert_allclose(0.5 * drawn[:, 0] * drawn[:, 1], 0.5, atol=1e-2)


def test_sc2_other_kinds_slice_by_contour():
    ax = mp.ThreeDAxes()
    ball = ax.plot_parametric_surface(
        lambda u, v: np.array(
            [np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)]
        ),
        (0, PI),
        (0, 2 * PI),
        resolution=16,
    )
    cut = ball.slice(x=0.5)
    assert isinstance(cut, mp.ContourPlot)
    drawn = data(ax, anchors(cut.at(0.5)))
    np.testing.assert_allclose(drawn[:, 0], 0.5, atol=1e-2)
    np.testing.assert_allclose(np.linalg.norm(drawn, axis=1), 1, atol=1e-9)


def test_sc3_one_coordinate_inside_the_surface():
    s = surface(mp.ThreeDAxes())
    with pytest.raises(ValueError, match="slice"):
        s.slice()
    with pytest.raises(ValueError, match="slice"):
        s.slice(x=1, y=1)
    with pytest.raises(ValueError, match="x"):
        s.slice(x=5)


def test_sc3_sc4_a_slice_follows_its_tracker_and_leaves_and_returns():
    ax = mp.ThreeDAxes()
    t = ValueTracker(-1)
    cut = surface(ax).slice(x=t)

    def gap() -> float:
        if not cut.has_points():
            return -1.0
        return float(np.max(np.abs(data(ax, anchors(cut))[:, 0] - t.get_value())))

    def construct(scene: Any) -> None:
        scene.add(ax, cut)
        scene.play(t.animate.set_value(1))
        scene.play(t.animate.set_value(3))
        scene.play(t.animate.set_value(0))

    gaps = probe(construct, gap)
    assert max(gaps) < 1e-9
    assert -1.0 in gaps  # empty while outside the surface
    assert gaps[-1] >= 0


def test_sc4_a_slice_follows_the_surface_parameters():
    ax = mp.ThreeDAxes()
    a = ValueTracker(0.5)
    s = surface(ax, a=a)
    cut = s.slice(x=1)

    def worst() -> float:
        drawn = data(ax, anchors(cut))
        return float(np.max(np.abs(drawn[:, 2] - a.get_value() * drawn[:, 1])))

    gaps = probe(lambda scene: scene.play(a.animate.set_value(1.5)), worst)
    assert max(gaps) < 1e-9


def test_sc4_style():
    ax = mp.ThreeDAxes()
    s = surface(ax)
    a, b = s.slice(x=1), s.slice(x=0.5)
    assert a.get_color() != b.get_color()
    assert a in ax.artists


# --- PS -------------------------------------------------------------------------------


def test_ps1_the_profile_agrees_with_the_slice():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1))
    s = surface(ax3)
    profile = ax2.plot_slice(s, x=1)
    assert isinstance(profile, mp.FunctionPlot)
    xy = np.array([ax2.p2c(p)[:2] for p in anchors(profile)])
    np.testing.assert_allclose(xy[:, 1], 0.5 * 1 * xy[:, 0], atol=1e-9)
    assert xy[:, 0].min() == pytest.approx(-2)
    assert xy[:, 0].max() == pytest.approx(2)
    other = ax2.plot_slice(s, y=-1)
    xy = np.array([ax2.p2c(p)[:2] for p in anchors(other)])
    np.testing.assert_allclose(xy[:, 1], -0.5 * xy[:, 0], atol=1e-9)


def test_ps2_the_profile_follows_its_tracker_and_the_surface():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes(x_range=(-2, 2, 1), y_range=(-4, 4, 1))
    a, t = ValueTracker(0.5), ValueTracker(-1)
    profile = ax2.plot_slice(surface(ax3, a=a), x=t)

    def worst() -> float:
        xy = np.array([ax2.p2c(p)[:2] for p in anchors(profile)])
        expected = a.get_value() * t.get_value() * xy[:, 0]
        return float(np.max(np.abs(xy[:, 1] - expected)))

    def construct(scene: Any) -> None:
        scene.add(ax2, profile)
        scene.play(t.animate.set_value(1.5))
        scene.play(a.animate.set_value(1))

    assert max(probe(construct, worst)) < 1e-9


def test_ps3_refusals():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes()
    ball = ax3.plot_parametric_surface(
        lambda u, v: np.array([u, v, 0 * u]), (0, 1), (0, 1), resolution=2
    )
    with pytest.raises(TypeError, match="plot_surface"):
        ax2.plot_slice(ball, x=0.5)
    with pytest.raises(NotImplementedError, match="ThreeDAxes"):
        ax3.plot_slice(surface(ax3), x=1)
    with pytest.raises(ValueError, match="plot_slice"):
        ax2.plot_slice(surface(ax3))


# --- SH -------------------------------------------------------------------------------


def test_sh1_a_curve_shadow_on_the_floor():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(0, 6))
    shade = ax.shadow(curve)
    assert isinstance(shade, mp.ParametricPlot)
    drawn = data(ax, anchors(shade))
    np.testing.assert_allclose(drawn[:, 2], -4, atol=1e-9)  # origin frame: the low end
    np.testing.assert_allclose(np.hypot(drawn[:, 0], drawn[:, 1]), 1, atol=1e-9)
    side = ax.shadow(curve, zdir="x", offset=2)
    drawn = data(ax, anchors(side))
    np.testing.assert_allclose(drawn[:, 0], 2, atol=1e-9)
    np.testing.assert_allclose(drawn[:, 1], np.sin(4 * drawn[:, 2]), atol=1e-9)


def test_sh1_points_and_refusals():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([1, 2], [0, 1], [2, 3])
    shade = ax.shadow(dots, zdir="y", offset=5)
    assert isinstance(shade, mp.ScatterPlot)
    np.testing.assert_allclose(shade[0].get_center(), ax.c2p(1, 5, 2), atol=1e-9)
    np.testing.assert_allclose(shade[1].get_center(), ax.c2p(2, 5, 3), atol=1e-9)
    with pytest.raises(TypeError, match="Dot"):
        ax.shadow(Dot())


def test_sh2_the_pane_in_a_box_and_its_refusal_at_the_origin():
    plain = mp.ThreeDAxes()
    with pytest.raises(ValueError, match="offset"):
        plain.shadow(plain.plot_parametric_curve(helix, t_range=(0, 6)), offset="pane")
    ax = mp.ThreeDAxes(frame="box")
    shade = ax.shadow(ax.plot_parametric_curve(helix, t_range=(0, 6)), zdir="x")
    seen: list[float] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
            self.add(ax, shade)
            self.wait(1 / 3)
            seen.append(float(data(ax, anchors(shade))[:, 0].mean()))
            self.move_camera(theta=135 * DEGREES, run_time=1 / 3)
            self.wait(1 / 3)
            seen.append(float(data(ax, anchors(shade))[:, 0].mean()))

    with tempconfig(RUN):
        Shot().render()
    assert seen == [pytest.approx(-6), pytest.approx(6)]  # the far x pane


def test_sh3_a_shadow_follows_its_artist():
    ax = mp.ThreeDAxes()
    k = ValueTracker(1.0)
    curve = ax.plot(lambda x, a=1.0: a * np.sin(x), x_range=(-3, 3), a=k)
    shade = ax.shadow(curve)  # on the floor z = -4

    def worst() -> float:
        drawn = data(ax, anchors(shade))
        return float(np.max(np.abs(drawn[:, 1] - k.get_value() * np.sin(drawn[:, 0]))))

    assert max(probe(lambda s: s.play(k.animate.set_value(2)), worst)) < 1e-9


def test_sh4_style():
    ax = mp.ThreeDAxes()
    curve = ax.plot_parametric_curve(helix, t_range=(0, 6), color=RED)
    shade = ax.shadow(curve)
    assert ManimColor(shade.get_stroke_color()).to_hex() == ManimColor(RED).to_hex()
    assert shade.get_stroke_opacity() == pytest.approx(0.35)
    dots = ax.shadow(ax.scatter([1], [1], [1], color=RED))
    assert dots[0].get_fill_opacity() == pytest.approx(0.35)
    assert ax.shadow(curve, stroke_opacity=1).get_stroke_opacity() == pytest.approx(1)


# --- ZD -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("zdir", "place"),
    [
        ("z", lambda u, v, c: (u, v, c)),
        ("y", lambda u, v, c: (u, c, v)),
        ("x", lambda u, v, c: (c, u, v)),
    ],
)
def test_zd1_plot_in_a_chosen_plane(zdir, place):
    ax = mp.ThreeDAxes()
    curve = ax.plot(np.sin, x_range=(-3, 3), zs=2, zdir=zdir)
    points = dense(np.asarray(curve.points), per_curve=32)
    for x in np.linspace(-3, 3, 13):
        target = ax.c2p(*place(x, np.sin(x), 2))
        assert np.min(np.linalg.norm(points - target, axis=1)) < 1e-3


def test_zd1_defaults_are_the_floor_of_z_zero():
    ax = mp.ThreeDAxes()
    drawn = data(ax, anchors(ax.plot(np.sin)))
    np.testing.assert_allclose(drawn[:, 2], 0, atol=1e-12)


def test_zd2_scatter_and_line_with_a_scalar_zs():
    ax = mp.ThreeDAxes()
    dots = ax.scatter([1, 2], [3, 4], zs=1, zdir="y")
    np.testing.assert_allclose(dots[0].get_center(), ax.c2p(1, 1, 3), atol=1e-9)
    np.testing.assert_allclose(dots[1].get_center(), ax.c2p(2, 1, 4), atol=1e-9)
    flat = ax.scatter([1, 2], [3, 4])
    np.testing.assert_allclose(flat[1].get_center(), ax.c2p(2, 4, 0), atol=1e-9)
    line = ax.line([0, 1], [1, 2], zs=-1, zdir="x")
    drawn = data(ax, anchors(line))
    np.testing.assert_allclose(drawn[:, 0], -1, atol=1e-9)


def test_zd3_unknown_direction():
    with pytest.raises(ValueError, match="zdir"):
        mp.ThreeDAxes().plot(np.sin, zdir="w")
