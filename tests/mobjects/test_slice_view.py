"""Task 28b: `plot_slice` by a plane and the slice view, rows PV and SV of
`docs/acceptance/28b-slice-view.md`.

The oracles: the surface's function along the plane's trace, written out; the parts'
identities and styles.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import (
    MED_LARGE_BUFF,
    RED,
    ManimColor,
    ThreeDScene,
    ValueTracker,
    tempconfig,
)

import manim_plots as mp

from .helpers import RUN, probe


def anchors(mob: Any) -> np.ndarray:
    return np.asarray(mob.points)[::4]


def saddle(u: Any, v: Any) -> Any:
    return u * v / 2


def surface(ax: Any) -> Any:
    return ax.plot_surface(saddle, (-2, 2), (-2, 2), resolution=8)


def profile_xy(axes: Any, profile: Any) -> np.ndarray:
    return np.array([axes.p2c(p)[:2] for p in anchors(profile)])


# --- PV -------------------------------------------------------------------------------


def test_pv1_an_axis_plane_drives_the_profile():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1))
    t = ValueTracker(-1)
    wall = ax3.plane(x=t)
    profile = ax2.plot_slice(surface(ax3), plane=wall)

    def worst() -> float:
        xy = profile_xy(ax2, profile)
        return float(np.max(np.abs(xy[:, 1] - t.get_value() * xy[:, 0] / 2)))

    def construct(scene: Any) -> None:
        scene.add(ax2, profile)
        scene.play(t.animate.set_value(1.5))

    assert max(probe(construct, worst)) < 1e-9


def test_pv2_an_oblique_vertical_plane():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
    wall = ax3.plane((0, 0, 0), (1, -1, 0))  # the vertical plane x = y
    profile = ax2.plot_slice(surface(ax3), plane=wall)
    xy = profile_xy(ax2, profile)
    # h = cross(z, n) normalised = (1, 1, 0) / √2: the trace is (s, s) / √2, z = s² / 4
    np.testing.assert_allclose(xy[:, 1], xy[:, 0] ** 2 / 4, atol=1e-9)
    ends = [ax2.p2c(p)[0] for p in np.asarray(profile.points)[[0, -1]]]
    assert sorted(ends) == pytest.approx([-2 * np.sqrt(2), 2 * np.sqrt(2)])


def test_pv2_pv3_refusals():
    ax3, ax2 = mp.ThreeDAxes(), mp.Axes()
    s = surface(ax3)
    with pytest.raises(ValueError, match="plane"):
        ax2.plot_slice(s, plane=ax3.plane(z=1))
    with pytest.raises(ValueError, match="plot_slice"):
        ax2.plot_slice(s, x=1, plane=ax3.plane(x=1))
    ball = ax3.plot_parametric_surface(
        lambda u, v: np.array([u, v, 0 * u]), (0, 1), (0, 1), resolution=2
    )
    with pytest.raises(TypeError, match="plot_surface"):
        ax2.plot_slice(ball, plane=ax3.plane(x=0.5))


# --- SV -------------------------------------------------------------------------------


def test_sv1_four_parts_one_tracker():
    ax = mp.ThreeDAxes()
    t = ValueTracker(-1)
    view = ax.slice_view(surface(ax), x=t)
    assert isinstance(view, mp.SliceView)
    assert isinstance(view.plane, mp.PlanePlot)
    assert isinstance(view.cut, mp.ParametricPlot)
    assert isinstance(view.axes, mp.Axes)
    assert isinstance(view.profile, mp.FunctionPlot)
    assert list(view) == [view.plane, view.cut, view.axes, view.profile]

    def worst() -> float:
        c = t.get_value()
        wall = np.array([ax.p2c(p) for p in anchors(view.plane)])
        cut = np.array([ax.p2c(p) for p in anchors(view.cut)])
        xy = profile_xy(view.axes, view.profile)
        return float(
            max(
                np.max(np.abs(wall[:, 0] - c)),
                np.max(np.abs(cut[:, 0] - c)),
                np.max(np.abs(xy[:, 1] - c * xy[:, 0] / 2)),
            )
        )

    def construct(scene: Any) -> None:
        scene.add(ax, view)
        scene.play(t.animate.set_value(1.5))

    assert max(probe(construct, worst)) < 1e-9


def test_sv1_a_plane_view_cuts_by_intersection():
    ax = mp.ThreeDAxes()
    wall = ax.plane((0, 0, 0), (1, -1, 0))
    view = ax.slice_view(surface(ax), plane=wall)
    assert view.plane is wall
    assert isinstance(view.cut, mp.ContourPlot)


def test_sv2_default_axes_and_their_config():
    ax = mp.ThreeDAxes(z_range=(-3, 3, 1))
    view = ax.slice_view(surface(ax), x=1, axes_config={"y_length": 2})
    assert tuple(view.axes.x_range[:2]) == pytest.approx((-2, 2))
    assert tuple(view.axes.y_range[:2]) == pytest.approx((-3, 3))
    assert view.axes.x_length == pytest.approx(4)
    assert view.axes.y_length == pytest.approx(2)
    mine = mp.Axes(x_range=(-5, 5, 1), y_range=(-1, 1, 1))
    assert ax.slice_view(surface(ax), y=0, axes=mine).axes is mine


def test_sv3_shared_colour_and_configs():
    ax = mp.ThreeDAxes()
    view = ax.slice_view(surface(ax), x=1)
    assert view.cut.get_color() == view.profile.get_color()
    styled = ax.slice_view(
        surface(ax),
        x=1,
        plane_config={"fill_opacity": 0.1},
        cut_config={"stroke_width": 8},
        profile_config={"color": RED},
    )
    assert styled.plane.get_fill_opacity() == pytest.approx(0.1)
    assert styled.cut.get_stroke_width() == pytest.approx(8)
    assert ManimColor(styled.profile.get_color()).to_hex() == ManimColor(RED).to_hex()


def test_sv4_beside_the_axes_in_2d_and_fixed_in_3d():
    ax = mp.ThreeDAxes()
    view = ax.slice_view(surface(ax), x=1)
    assert view.axes.get_left()[0] == pytest.approx(
        ax.get_right()[0] + MED_LARGE_BUFF, abs=1e-6
    )
    left = ax.slice_view(surface(ax), x=1, side="left")
    assert left.axes.get_right()[0] == pytest.approx(
        ax.get_left()[0] - MED_LARGE_BUFF, abs=1e-6
    )
    with pytest.raises(ValueError, match="side"):
        ax.slice_view(surface(ax), x=1, side="behind")
    found: list[bool] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.add(ax, view)
            self.wait(1 / 3)
            found.append(view.axes in self.camera.fixed_in_frame_mobjects)

    with tempconfig(RUN):
        Shot().render()
    assert found == [True]
    assert view.axes.get_center()[0] > 0  # against the frame's right side
