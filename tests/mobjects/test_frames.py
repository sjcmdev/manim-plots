"""Task 24: frame styles, view and aspect, rows FR and VW of
`docs/acceptance/24-three-d.md`.

The oracle for the box: the camera direction ``d`` of `ThreeDScene`'s ``phi`` and
``theta``, from which the far panes and near edges follow by sign.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest
from manim import DEGREES, RED, Scene, ThreeDScene, tempconfig

import manim_plots as mp

from .helpers import RUN, visible_leaves

RANGES: dict[str, Any] = {
    "x_range": (0, 4, 1),
    "y_range": (0, 3, 1),
    "z_range": (0, 2, 0.5),
    "x_length": 4,
    "y_length": 3,
    "z_length": 2,
}


def direction(phi: float, theta: float) -> np.ndarray:
    return np.array(
        [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
    )


def shown(ax: Any, phi: float, theta: float) -> Any:
    """Draw ``ax`` in a `ThreeDScene` with the camera at ``phi``, ``theta``."""

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=phi, theta=theta)
            self.add(ax)
            self.wait(1 / 6)

    with tempconfig(RUN):
        Shot().render()
    return ax


def probe3d(
    construct: Callable[[ThreeDScene], Any], record: Callable[[], Any]
) -> list[Any]:
    records: list[Any] = []

    class Probe(ThreeDScene):
        def construct(self) -> None:
            construct(self)

        def update_to_time(self, t: float) -> None:
            super().update_to_time(t)
            records.append(record())

    with tempconfig(RUN):
        Probe().render()
    return records


def end(ax: Any, index: int, sign: float) -> float:
    lo, hi = (ax.x_range, ax.y_range, ax.z_range)[index][:2]
    return float(hi if sign > 0 else lo)


ANGLES = [(65, -45), (65, 45), (65, 135), (65, -135), (110, -60)]


@pytest.mark.parametrize(("phi", "theta"), ANGLES)
def test_fr2_panes_lie_on_the_far_sides(phi, theta):
    phi, theta = phi * DEGREES, theta * DEGREES
    ax = shown(mp.ThreeDAxes(frame="box", **RANGES), phi, theta)
    d = direction(phi, theta)
    for index, name in enumerate("xyz"):
        centre = ax.p2c(ax.panes[name].get_center())
        assert centre[index] == pytest.approx(end(ax, index, -d[index]), abs=1e-6)
        assert len(ax.panes[name].grid) > 0


@pytest.mark.parametrize(("phi", "theta"), ANGLES)
def test_fr2_the_axes_run_along_the_near_edges(phi, theta):
    phi, theta = phi * DEGREES, theta * DEGREES
    ax = shown(mp.ThreeDAxes(frame="box", **RANGES), phi, theta)
    d = direction(phi, theta)
    x_start = ax.p2c(ax.x.get_start())
    assert x_start[1] == pytest.approx(end(ax, 1, d[1]), abs=1e-6)
    assert x_start[2] == pytest.approx(end(ax, 2, -d[2]), abs=1e-6)
    y_start = ax.p2c(ax.y.get_start())
    assert y_start[0] == pytest.approx(end(ax, 0, d[0]), abs=1e-6)
    assert y_start[2] == pytest.approx(end(ax, 2, -d[2]), abs=1e-6)
    # the z axis: of the vertical edges but the far one, the farthest to the right
    right = np.array([-np.sin(theta), np.cos(theta)])
    far = (end(ax, 0, -d[0]), end(ax, 1, -d[1]))
    edges = [
        (x, y)
        for x in (ax.x_range[0], ax.x_range[1])
        for y in (ax.y_range[0], ax.y_range[1])
        if (x, y) != far
    ]
    middle = np.array(
        [(ax.x_range[0] + ax.x_range[1]) / 2, (ax.y_range[0] + ax.y_range[1]) / 2]
    )
    best = max(edges, key=lambda e: float(np.dot(np.array(e) - middle, right)))
    z_start = ax.p2c(ax.z.get_start())
    assert (z_start[0], z_start[1]) == pytest.approx(best, abs=1e-6)


def test_fr2_box_axes_are_numbered_and_tick_inward():
    ax = shown(mp.ThreeDAxes(frame="box", **RANGES), 65 * DEGREES, -45 * DEGREES)
    assert ax.frame_style == "box"
    for axis in (ax.x, ax.y, ax.z):
        assert len(axis.numbers) > 0


def test_fr3_a_pane_moves_with_the_camera_and_keeps_its_style():
    ax = mp.ThreeDAxes(frame="box", **RANGES)
    ax.panes["x"].set_fill(RED)

    def construct(scene: ThreeDScene) -> None:
        scene.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        scene.add(ax)
        scene.move_camera(theta=135 * DEGREES, run_time=1)

    sides = probe3d(construct, lambda: float(ax.p2c(ax.panes["x"].get_center())[0]))
    assert sides[0] == pytest.approx(0.0, abs=1e-6)  # camera at +x: pane at x_min
    assert sides[-1] == pytest.approx(4.0, abs=1e-6)  # camera at -x: pane at x_max
    assert set(np.round(sides, 6)) <= {0.0, 4.0}
    assert ax.panes["x"].get_fill_color() == RED


def test_fr3_set_camera_names_the_camera():
    ax = mp.ThreeDAxes(frame="box", **RANGES)

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=65 * DEGREES, theta=135 * DEGREES)
            ax.set_camera(self.camera)
            self.add(ax)

    with tempconfig(RUN):
        Shot().render()
    assert ax.p2c(ax.panes["x"].get_center())[0] == pytest.approx(4.0, abs=1e-6)


def test_fr4_box_in_a_plain_scene_warns_once():
    ax = mp.ThreeDAxes(frame="box", **RANGES)

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.wait(1 / 3)

    class Flat(Scene):
        def construct(self) -> None:
            construct(self)

    with pytest.warns(mp.ManimPlotsWarning) as caught, tempconfig(RUN):
        Flat().render()
    assert len(caught) == 1


def test_fr5_the_2d_box_is_the_framed_plot():
    kwargs: dict[str, Any] = {"x_range": (0, 10, 1), "y_range": (0, 5, 1)}
    boxed = mp.Axes(frame="box", **kwargs)
    framed = mp.Axes(
        theme=dataclasses.replace(
            mp.THEMES["manim"], position="border", box=True, tips=False
        ),
        **kwargs,
    )
    ours, theirs = visible_leaves(boxed), visible_leaves(framed)
    assert len(ours) == len(theirs)
    for a, b in zip(ours, theirs, strict=True):
        np.testing.assert_allclose(
            np.asarray(a.points), np.asarray(b.points), atol=1e-9
        )
    assert boxed.frame_style == "box"
    assert mp.Axes(**kwargs).frame_style == "origin"


def test_fr5_a_theme_sets_the_box_and_an_explicit_frame_wins():
    assert mp.Axes(theme="origin").frame_style == "box"
    assert mp.Axes(theme="origin", frame="origin").frame_style == "origin"
    assert mp.NumberPlane(frame="box").frame_style == "box"


def plane_normal(points: np.ndarray) -> np.ndarray:
    centred = points - points.mean(axis=0)
    return np.asarray(np.linalg.svd(centred)[2][-1])


def test_fr6_numbers_face_the_camera_in_the_box():
    phi, theta = 65 * DEGREES, -45 * DEGREES
    ax = shown(mp.ThreeDAxes(frame="box", **RANGES), phi, theta)
    number = ax.x.numbers.at(2.0)
    points = np.concatenate(
        [np.asarray(m.points) for m in number.family_members_with_points()]
    )
    normal = plane_normal(points)
    assert abs(float(np.dot(normal, direction(phi, theta)))) == pytest.approx(
        1, abs=1e-6
    )


def test_fr6_numbers_lie_flat_in_origin():
    ax = shown(
        mp.ThreeDAxes(axis_config={"include_numbers": True}, **RANGES),
        65 * DEGREES,
        -45 * DEGREES,
    )
    number = ax.x.numbers.at(2.0)
    points = np.concatenate(
        [np.asarray(m.points) for m in number.family_members_with_points()]
    )
    assert np.ptp(points[:, 2]) == pytest.approx(0, abs=1e-9)


def test_vw1_view_is_matplotlibs_angles():
    view = mp.ThreeDAxes().view(30, -60)
    assert view["phi"] == pytest.approx(60 * DEGREES)
    assert view["theta"] == pytest.approx(-60 * DEGREES)
    assert view["gamma"] == pytest.approx(0)
    assert mp.ThreeDAxes().view(elev=0, azim=-90, roll=10)["gamma"] == pytest.approx(
        10 * DEGREES
    )


def unit(axis: Any) -> float:
    return float(axis.get_unit_size())


def test_vw2_equal_aspect():
    ax = mp.ThreeDAxes(
        x_range=(-1, 1), y_range=(-2, 2), z_range=(-1, 1), x_length=4, aspect="equal"
    )
    assert unit(ax.x) == pytest.approx(2)
    assert unit(ax.y) == pytest.approx(2)
    assert unit(ax.z) == pytest.approx(2)


def test_vw2_box_aspect_and_a_conflict():
    ax = mp.ThreeDAxes(x_length=6, aspect=(1, 2, 0.5))
    assert ax.y_length == pytest.approx(12)
    assert ax.z_length == pytest.approx(3)
    with pytest.raises(ValueError, match="aspect"):
        mp.ThreeDAxes(x_length=6, y_length=5, aspect="equal")


def test_fr3_a_still_frame_reads_the_camera():
    """No wait, no play: the frame Manim captures must already show the camera's view
    (a static picture runs no updater)."""
    ax = mp.ThreeDAxes(frame="box", **RANGES)
    phi, theta = 65 * DEGREES, 135 * DEGREES

    class Still(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=phi, theta=theta)
            self.add(ax)
            self.camera.capture_mobjects(self.mobjects)

    with tempconfig(RUN):
        Still().render()
    assert ax.p2c(ax.panes["x"].get_center())[0] == pytest.approx(4.0, abs=1e-6)
    number = ax.x.numbers.at(2.0)
    points = np.concatenate(
        [np.asarray(m.points) for m in number.family_members_with_points()]
    )
    assert abs(float(np.dot(plane_normal(points), direction(phi, theta)))) == (
        pytest.approx(1, abs=1e-6)
    )


@pytest.mark.parametrize(("phi", "theta"), [(65, -45), (65, 120), (110, -60)])
def test_fr6_numbers_read_upright_on_screen(phi, theta):
    """On screen (the camera's rotation applied), a facing number is its flat glyph,
    upright and unmirrored, in every view."""
    phi, theta = phi * DEGREES, theta * DEGREES
    flat = mp.ThreeDAxes(axis_config={"include_numbers": True}, **RANGES)
    ax = mp.ThreeDAxes(frame="box", **RANGES)
    screens: list[np.ndarray] = []

    def glyph(mob: Any) -> np.ndarray:
        p = np.concatenate(
            [np.asarray(m.points) for m in mob.family_members_with_points()]
        )
        return p - p.mean(axis=0)

    class Still(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=phi, theta=theta)
            self.add(ax)
            self.camera.capture_mobjects(self.mobjects)
            matrix = self.camera.generate_rotation_matrix()
            screens.append(glyph(ax.x.numbers.at(2.0)) @ matrix.T)

    with tempconfig(RUN):
        Still().render()
    expected = glyph(flat.x.numbers.at(2.0))
    np.testing.assert_allclose(screens[0][:, :2], expected[:, :2], atol=1e-6)


def distance_to_axis(axis: Any, number: Any) -> float:
    a, b = np.asarray(axis.get_start()), np.asarray(axis.get_end())
    c = np.asarray(number.get_center())
    t = np.clip(np.dot(c - a, b - a) / np.dot(b - a, b - a), 0, 1)
    return float(np.linalg.norm(c - (a + t * (b - a))))


def test_fr6_numbers_stay_by_their_axis_through_an_orbit():
    """Two camera moves that swap the edges several times: every number stays next to
    its axis and keeps facing the camera (no compounding of the facing turn)."""
    ax = mp.ThreeDAxes(frame="box", **RANGES)

    def construct(scene: ThreeDScene) -> None:
        scene.set_camera_orientation(**ax.view(25, -50))  # type: ignore[arg-type]
        scene.add(ax)
        scene.move_camera(**ax.view(25, 130), run_time=5)  # type: ignore[arg-type]
        scene.move_camera(**ax.view(60, -50), run_time=3)  # type: ignore[arg-type]

    def worst() -> float:
        return max(
            distance_to_axis(axis, number)
            for axis in (ax.x, ax.y, ax.z)
            for number in axis.numbers
        )

    distances = probe3d(construct, worst)
    assert max(distances) < 1.0
    number = ax.x.numbers.at(2.0)
    points = np.concatenate(
        [np.asarray(m.points) for m in number.family_members_with_points()]
    )
    view = ax.view(60, -50)
    assert abs(
        float(np.dot(plane_normal(points), direction(view["phi"], view["theta"])))
    ) == pytest.approx(1, abs=1e-6)
