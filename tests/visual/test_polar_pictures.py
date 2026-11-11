"""Pictures of task 22's polar systems (`docs/acceptance/22-polar.md`), `mp.PolarPlane`
beside Manim's `PolarPlane` on the same scene; `mp.PolarAxes` has no Manim twin."""

from __future__ import annotations

import numpy as np
import pytest
from manim import ORANGE, PI, TAU, YELLOW, PolarPlane, Scene

import manim_plots as mp


def rose(theta):
    return 2 * np.sin(5 * theta)


@pytest.mark.render
def test_polar_plane(visual):
    """Manim's docs example: a π-radians plane of size 6 with coordinates and a rose
    `2 sin 5θ`."""

    def construct(scene: Scene) -> None:
        plane = mp.PolarPlane(
            azimuth_units="PI radians",
            size=6,
            azimuth_label_font_size=33.6,
            radius_config={"font_size": 33.6},
        ).add_coordinates()
        scene.add(plane, plane.plot_polar_graph(rose, [0, TAU], color=ORANGE))

    visual(construct)


@pytest.mark.render
def test_polar_plane__manim(visual):
    """Plain Manim, same scene."""

    def construct(scene: Scene) -> None:
        plane = PolarPlane(
            azimuth_units="PI radians",
            size=6,
            azimuth_label_font_size=33.6,
            radius_config={"font_size": 33.6},
        ).add_coordinates()
        scene.add(plane, plane.plot_polar_graph(rose, [0, TAU], color=ORANGE))

    visual(construct)


@pytest.mark.render
def test_polar_plane_degrees_cw(visual):
    """Degrees, clockwise from the top, faded lines; the dot at azimuth 30° sits on the
    spoke labelled 30° (Manim's misses it: PP-4)."""

    def construct(scene: Scene) -> None:
        plane = mp.PolarPlane(
            radius_max=3,
            size=6,
            azimuth_units="degrees",
            azimuth_step=12,
            azimuth_offset=PI / 2,
            azimuth_direction="CW",
            faded_line_ratio=2,
        ).add_coordinates()
        x, y = plane.p2c(plane.pr2pt(2.5, PI / 6))[:2]
        scene.add(plane, plane.scatter([x], [y], color=YELLOW))

    visual(construct)


@pytest.mark.render
def test_polar_plane_degrees_cw__manim(visual):
    """Plain Manim, same plane; its `pr2pt` ignores offset and direction."""

    def construct(scene: Scene) -> None:
        plane = PolarPlane(
            radius_max=3,
            size=6,
            azimuth_units="degrees",
            azimuth_step=12,
            azimuth_offset=PI / 2,
            azimuth_direction="CW",
            faded_line_ratio=2,
        ).add_coordinates()
        scene.add(plane)

    visual(construct)


@pytest.mark.render
def test_polar_axes_rose(visual):
    """A true polar system: a flower `1.5 + sin 5θ` and a cardioid on `r` in (0, 3),
    ticks on the rim pointing in, numbers in π radians, radial numbers at 22.5°."""

    def construct(scene: Scene) -> None:
        ax = mp.PolarAxes(r_range=(0, 3, 1), size=7)
        scene.add(
            ax, ax.plot(lambda t: 1.5 + np.sin(5 * t)), ax.plot(lambda t: 1 + np.cos(t))
        )

    visual(construct)


@pytest.mark.render
def test_polar_axes_log(visual):
    """A log radius from 0.1 to 100, circles at the decades, a spiral `r = 10^(θ/π)`
    and a scatter of 12 points at r = 1."""

    def construct(scene: Scene) -> None:
        ax = mp.PolarAxes(r_range=(0.1, 100), r_scale="log", azimuth_units="degrees")
        scene.add(
            ax,
            ax.plot(lambda t: 10 ** (t / PI - 0.5), theta_range=[0, 2.5 * PI]),
            ax.scatter(np.ones(12), np.arange(12) * TAU / 12),
        )

    visual(construct)


@pytest.mark.render
def test_polar_axes_clipped(visual):
    """A limaçon `1 + 2 cos θ` on `r` in (0, 2): cut at the rim and at the centre, and
    the same curve faint with `clip=False`."""

    def construct(scene: Scene) -> None:
        ax = mp.PolarAxes(r_range=(0, 2, 0.5), size=6)
        scene.add(
            ax,
            ax.plot(lambda t: 1 + 2 * np.cos(t)),
            ax.plot(lambda t: 1 + 2 * np.cos(t), clip=False, stroke_opacity=0.35),
        )

    visual(construct)
