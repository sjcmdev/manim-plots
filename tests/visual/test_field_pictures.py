"""Pictures of the fields of task 21, each beside plain Manim's own field on a
`NumberPlane`, where one data unit is one scene unit
(`docs/acceptance/21-fields-flow.md`)."""

from __future__ import annotations

import numpy as np
import pytest
from manim import BLUE, ArrowVectorField, NumberPlane, Scene, StreamLines

import manim_plots as mp


def swirl(p):
    x, y = p[0], p[1]
    return np.array([np.sin(y), np.cos(x) - 0.3 * y, 0.0])


@pytest.mark.render
def test_vector_field(visual):
    """An arrow field of a swirl on the default plane, coloured by norm; each arrow
    starts at its grid point (Manim centres it there)."""

    def construct(scene: Scene) -> None:
        plane = mp.NumberPlane()
        scene.add(plane, plane.get_vector_field(swirl))

    visual(construct)


@pytest.mark.render
def test_vector_field__manim(visual):
    """Plain Manim, same field."""

    def construct(scene: Scene) -> None:
        scene.add(
            NumberPlane(),
            ArrowVectorField(swirl, x_range=[-7, 7, 1], y_range=[-4, 4, 1]),
        )

    visual(construct)


@pytest.mark.render
def test_stream_lines(visual):
    """Stream lines of the same swirl, integrated with RK4 and clipped to the plane."""

    def construct(scene: Scene) -> None:
        plane = mp.NumberPlane()
        scene.add(plane, plane.get_stream_lines(swirl, stroke_width=2))

    visual(construct)


@pytest.mark.render
def test_stream_lines__manim(visual):
    """Plain Manim, same stream lines (integrated with Euler)."""

    def construct(scene: Scene) -> None:
        scene.add(NumberPlane(), StreamLines(swirl, stroke_width=2))

    visual(construct)


@pytest.mark.render
def test_implicit_curve(visual):
    """`plot_implicit_curve` of a lemniscate-like curve (x² + y²)² = 8 (x² - y²)."""

    def construct(scene: Scene) -> None:
        plane = mp.NumberPlane()
        curve = plane.plot_implicit_curve(
            lambda x, y: (x**2 + y**2) ** 2 - 8 * (x**2 - y**2), color=BLUE
        )
        scene.add(plane, curve)

    visual(construct)


@pytest.mark.render
def test_implicit_curve__manim(visual):
    """Plain Manim, same curve."""

    def construct(scene: Scene) -> None:
        plane = NumberPlane()
        curve = plane.plot_implicit_curve(
            lambda x, y: (x**2 + y**2) ** 2 - 8 * (x**2 - y**2), color=BLUE
        )
        scene.add(plane, curve)

    visual(construct)
