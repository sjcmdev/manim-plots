"""Task 30: occlusion, rows OC of `docs/acceptance/30-occlusion.md`.

The oracle: geometry. With equal units and the camera on an axis, which part of a curve
lies behind an opaque wall or floor is known exactly; the step must cut there within a
render pixel (tolerance 0.1 scene units at the probe's 427 pixels).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest
from manim import DEGREES, ThreeDScene, tempconfig

import manim_plots as mp

from .helpers import RUN

PIXEL = 0.1


def cube(**kwargs: Any) -> Any:
    return mp.ThreeDAxes(
        x_range=(-3, 3, 1),
        y_range=(-3, 3, 1),
        z_range=(-3, 3, 1),
        x_length=6,
        y_length=6,
        z_length=6,
        **kwargs,
    )


def data(ax: Any, points: np.ndarray) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(points)])


def drawn(ax: Any, mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    return data(ax, points) if len(points) else np.empty((0, 3))


def shoot(
    ax: Any, *mobs: Any, phi: float, theta: float, record: Callable[[], Any]
) -> Any:
    # The axes hold their artists weakly: a test keeps every occluder it makes and
    # passes it here, or the collector may take it before the frame.
    """Render one still frame of the axes and their artists from the given camera
    and return ``record()``."""
    out: list[Any] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.set_camera_orientation(phi=phi * DEGREES, theta=theta * DEGREES)
            self.add(ax, *ax.artists, *mobs)
            self.wait(1 / 6)
            out.append(record())

    with tempconfig(RUN):
        Shot().render()
    return out[0]


def engines() -> list[Any]:
    try:
        import moderngl

        moderngl.create_standalone_context().release()
        gpu: Any = "gpu"
    except Exception:  # no GL context on this machine
        gpu = pytest.param("gpu", marks=pytest.mark.skip(reason="no moderngl context"))
    return ["numpy", gpu]


# --- OC-1 -----------------------------------------------------------------------------


def test_oc1_the_keyword():
    with pytest.raises(ValueError, match="occlusion"):
        cube(occlusion="zbuffer")


@pytest.mark.parametrize("engine", engines())
def test_oc1_oc3_a_wall_hides_the_far_part_of_a_segment(engine):
    ax = cube(occlusion=engine)
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    xs = shoot(ax, wall, phi=90, theta=0, record=lambda: drawn(ax, seg)[:, 0])
    assert xs.min() == pytest.approx(0, abs=PIXEL)  # cut at the wall
    assert xs.max() == pytest.approx(3, abs=1e-9)


@pytest.mark.parametrize("engine", engines())
def test_oc3_from_the_other_side_the_other_part(engine):
    ax = cube(occlusion=engine)
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    xs = shoot(ax, wall, phi=90, theta=180, record=lambda: drawn(ax, seg)[:, 0])
    assert xs.max() == pytest.approx(0, abs=PIXEL)
    assert xs.min() == pytest.approx(-3, abs=1e-9)


def test_oc1_off_draws_everything():
    ax = cube(occlusion=False)
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    xs = shoot(ax, wall, phi=90, theta=0, record=lambda: drawn(ax, seg)[:, 0])
    assert xs.min() == pytest.approx(-3, abs=1e-9)


# --- OC-2 -----------------------------------------------------------------------------


def test_oc2_a_translucent_wall_hides_nothing():
    ax = cube()
    wall = ax.plane(x=0)  # fill_opacity 0.25 by default
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    xs = shoot(ax, wall, phi=90, theta=0, record=lambda: drawn(ax, seg)[:, 0])
    assert xs.min() == pytest.approx(-3, abs=1e-9)


def test_oc2_an_opaque_surface_hides_what_is_below_it():
    ax = cube()
    floor = ax.plot_surface(lambda u, v: 0 * u, (-3, 3), (-3, 3), resolution=4)
    helix = ax.plot_parametric_curve(
        lambda t: np.array([np.cos(t), np.sin(t), t / 3]), t_range=(-6, 6)
    )
    zs = shoot(ax, floor, phi=0, theta=-90, record=lambda: drawn(ax, helix)[:, 2])
    assert zs.min() == pytest.approx(0, abs=PIXEL)
    assert zs.max() == pytest.approx(2, abs=1e-6)


def test_oc3_a_curve_with_nothing_in_front_keeps_its_path():
    ax = cube()
    wall = ax.plane(x=-2, fill_opacity=1)  # behind everything seen from +x
    seg = ax.segment((-1, -2, 0), (3, 2, 0))
    before = np.asarray(seg.points).copy()
    after = shoot(
        ax, wall, phi=90, theta=0, record=lambda: np.asarray(seg.points).copy()
    )
    np.testing.assert_allclose(after, before, atol=1e-12)


def test_oc3_a_hidden_curve_draws_nothing():
    ax = cube()
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (-1, 2, 0))
    count = shoot(ax, wall, phi=90, theta=0, record=lambda: len(seg.points))
    assert count == 0


# --- OC-4 -----------------------------------------------------------------------------


def test_oc4_markers_behind_are_hidden_whole():
    ax = cube()
    wall = ax.plane(x=0, fill_opacity=1)
    dots = ax.scatter([-2, 2], [0, 0], [0, 0])
    opacities = shoot(
        ax,
        wall,
        phi=90,
        theta=0,
        record=lambda: [d.get_fill_opacity() for d in dots],
    )
    assert opacities[0] == 0
    assert opacities[1] > 0


def test_oc4_text_is_never_occluded():
    ax = cube(frame="box")
    wall = ax.plane(x=0, fill_opacity=1)
    label = ax.text(-2, 0, 0, "behind")
    count = shoot(ax, wall, phi=90, theta=0, record=lambda: len(label.get_all_points()))
    assert count > 0


# --- OC-5 -----------------------------------------------------------------------------


def test_oc5_the_data_and_later_derivations_are_untouched():
    ax = cube()
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    shoot(ax, wall, phi=90, theta=0, record=lambda: None)
    # outside the scene, no camera: the next derivation draws the whole segment
    ax.set_z_range((-4, 4, 1))
    xs = drawn(ax, seg)[:, 0]
    assert xs.min() == pytest.approx(-3, abs=1e-9)


def test_oc5_no_scene_no_step():
    ax = cube()
    wall = ax.plane(x=0, fill_opacity=1)
    seg = ax.segment((-3, -2, 0), (3, 2, 0))
    assert drawn(ax, seg)[:, 0].min() == pytest.approx(-3, abs=1e-9)
    assert wall.get_fill_opacity() == 1  # an opaque wall was there all along
