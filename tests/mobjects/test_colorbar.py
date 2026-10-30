"""Task 25: the colorbar, rows CB of `docs/acceptance/25-surfaces.md`, in 2D and 3D."""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import numpy as np
import pytest
from manim import BLUE, MED_SMALL_BUFF, RED, UP, ManimColor, ThreeDScene, tempconfig

import manim_plots as mp

from .helpers import RUN, probe


def rgb(mob: Any) -> np.ndarray:
    return np.asarray(ManimColor(mob.get_fill_color()).to_rgb())


def test_cb1_a_bar_from_a_colorscale():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 5, 1))
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=10)
    assert isinstance(bar, mp.Colorbar)
    assert isinstance(bar, mp.CartesianAxes)
    assert bar.axis is bar.y
    assert tuple(bar.y_range[:2]) == (pytest.approx(0), pytest.approx(10))
    assert len(bar.axis.numbers) > 0


def test_cb1_neither_or_both_is_refused():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(
        lambda u, v: u + v, (0, 1), (0, 1), colorscale=[BLUE, RED]
    )
    with pytest.raises(ValueError):
        ax.colorbar()
    with pytest.raises(ValueError):
        ax.colorbar(surface, colorscale="viridis")


def test_cb1_a_log_mapping_gives_a_log_axis():
    ax = mp.Axes()
    bar = ax.colorbar(colorscale="viridis", vmin=1, vmax=1000, norm="log")
    # the strip's middle cell sits at the value 10 ** 1.5 on the bar's own axis
    middle = bar.strip[32].get_bottom()
    assert bar.p2c(middle)[1] == pytest.approx(10**1.5, rel=1e-6)


def test_cb1_every_tick_is_numbered_zero_included():
    ax = mp.Axes()
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=2)
    assert bar.y.numbers.at(0.0) is not None
    assert bar.y.numbers.at(2.0) is not None


def test_cb2_the_strip():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 5, 1))
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=10)
    assert len(bar.strip) == 64
    viridis = mp.colormaps["viridis"]
    np.testing.assert_allclose(rgb(bar.strip[0]), viridis(1 / 128), atol=1 / 255)
    np.testing.assert_allclose(rgb(bar.strip[-1]), viridis(127 / 128), atol=1 / 255)
    assert bar.strip.height == pytest.approx(ax.y_length)
    assert bar.strip.width == pytest.approx(0.25)
    assert all(cell.get_stroke_width() == 0 for cell in bar.strip)
    bottoms = [float(cell.get_bottom()[1]) for cell in bar.strip]
    assert all(b > a for a, b in pairwise(bottoms))


def test_cb3_placed_right_of_the_axes_and_kept_there():
    ax = mp.Axes(x_range=(0, 10, 1), y_range=(0, 5, 1))
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=10)
    assert bar.strip.get_left()[0] == pytest.approx(ax.get_right()[0] + MED_SMALL_BUFF)
    assert bar.strip.get_center()[1] == pytest.approx(ax.get_center()[1])

    def construct(scene: Any) -> None:
        scene.add(ax, bar)
        scene.play(ax.animate.shift(UP))

    gaps = probe(
        construct,
        lambda: float(bar.strip.get_center()[1] - ax.get_center()[1]),
    )
    assert gaps == pytest.approx([0.0] * len(gaps), abs=1e-6)
    assert bar.strip.get_center()[1] == pytest.approx(ax.get_center()[1])


def test_cb4_a_bar_follows_its_surface():
    ax = mp.ThreeDAxes()
    surface = ax.plot_surface(
        lambda u, v: u + v, (0, 1), (0, 1), colorscale=[BLUE, RED]
    )
    bar = ax.colorbar(surface)
    assert surface.color_mapping is not None
    assert tuple(bar.y_range[:2]) == (pytest.approx(-4), pytest.approx(4))
    np.testing.assert_allclose(
        rgb(bar.strip[0]),
        surface.color_mapping(np.array([-4 + 8 / 128]))[0],
        atol=1 / 255,
    )
    tops: list[float] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.add(ax, surface, bar)
            self.play(ax.animate.set_z_range((-8, 8, 1)))

        def update_to_time(self, t: float) -> None:
            super().update_to_time(t)
            tops.append(float(bar.y_range[1]))

    with tempconfig(RUN):
        Shot().render()
    assert bar.y_range[1] == pytest.approx(8)
    assert all(b >= a - 1e-9 for a, b in pairwise(tops))


def test_cb3_in_3d_the_bar_is_fixed_in_the_frame():
    ax = mp.ThreeDAxes()
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=1)
    found: list[bool] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.add(ax, bar)
            self.wait(1 / 3)
            found.append(bar in self.camera.fixed_in_frame_mobjects)

    with tempconfig(RUN):
        Shot().render()
    assert found == [True]
    assert bar.strip.height == pytest.approx(ax.z_length)


def test_cb4_a_field_has_a_mapping():
    ax = mp.Axes()
    field = ax.get_vector_field(lambda p: p)
    mapping = field.color_mapping
    assert isinstance(mapping, mp.ColorMapping)
    assert (mapping.vmin, mapping.vmax) == pytest.approx((0, 2))
    bar = ax.colorbar(field)
    assert tuple(bar.y_range[:2]) == (pytest.approx(0), pytest.approx(2))
