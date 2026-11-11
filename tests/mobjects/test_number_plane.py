"""`mp.NumberPlane` against Manim's `NumberPlane` (F-921, the plane's defaults table).

Rows NP-1 to NP-3 of `docs/acceptance/10-axis-decoration.md`; the oracle is Manim's own
`NumberPlane`, built with the same arguments in the same test.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import RED, NumberPlane, tempconfig

import manim_plots as mp

from .helpers import RUN

CASES: dict[str, dict[str, Any]] = {
    "default": {},
    "half steps": {"x_range": (-3, 3, 0.5), "y_range": (-2, 2, 0.5)},
    "faded": {"faded_line_ratio": 2},
    "style": {
        "background_line_style": {
            "stroke_color": RED,
            "stroke_width": 1,
            "stroke_opacity": 0.5,
        }
    },
}


def lines(group) -> list[np.ndarray]:
    return sorted(
        (np.round(m.points, 9) for m in group if m.has_points()),
        key=lambda p: tuple(p.ravel()),
    )


def assert_lines_match(ours, theirs) -> None:
    a, b = lines(ours), lines(theirs)
    assert len(a) == len(b)
    for p, q in zip(a, b, strict=True):
        np.testing.assert_allclose(p, q, rtol=0, atol=1e-6)


def our_lines(plane, level: str):
    grids = [plane.x_axis.grid, plane.y_axis.grid]
    members = [m for g in grids for m in g.get_family() if m.has_points()]
    return [m for m in members if getattr(m, "level", "major") == level]


@pytest.mark.parametrize("name", list(CASES))
def test_np2_background_and_faded_lines_are_manims(name):
    case = CASES[name]
    with tempconfig(RUN):
        ours, theirs = mp.NumberPlane(**case), NumberPlane(**case)
    assert_lines_match(our_lines(ours, "major"), theirs.background_lines)
    assert_lines_match(our_lines(ours, "minor"), theirs.faded_lines)
    for mine, manims in (
        (our_lines(ours, "major"), theirs.background_lines),
        (our_lines(ours, "minor"), theirs.faded_lines),
    ):
        if len(manims):
            assert mine[0].get_stroke_color() == manims[0].get_stroke_color()
            assert mine[0].get_stroke_width() == pytest.approx(
                manims[0].get_stroke_width()
            )
            assert mine[0].get_stroke_opacity() == pytest.approx(
                manims[0].get_stroke_opacity()
            )


def test_np1_defaults():
    with tempconfig(RUN):
        ours, theirs = mp.NumberPlane(), NumberPlane()
    np.testing.assert_allclose(ours.x.range.value, theirs.x_range[:2])
    np.testing.assert_allclose(ours.y.range.value, theirs.y_range[:2])
    np.testing.assert_allclose(ours.x_axis.line.points, theirs.x_axis.points, atol=1e-6)
    np.testing.assert_allclose(ours.y_axis.line.points, theirs.y_axis.points, atol=1e-6)
    assert ours.x_axis.line.get_stroke_width() == theirs.x_axis.get_stroke_width()
    assert len(ours.x_axis.ticks) == 0 and ours.x_axis.tip is None
    np.testing.assert_allclose(ours.c2p(1, 1), theirs.c2p(1, 1), atol=1e-9)


def test_np1_numbers_follow_the_plane_defaults():
    with tempconfig(RUN):
        ours, theirs = mp.NumberPlane(), NumberPlane()
        ours.add_coordinates()
        theirs.add_coordinates()
    assert len(ours.x_axis.numbers) == len(theirs.x_axis.numbers)
    for mine, manims in zip(ours.x_axis.numbers, theirs.x_axis.numbers, strict=True):
        np.testing.assert_allclose(mine.get_center(), manims.get_center(), atol=1e-6)


def test_np1_the_plane_is_not_star_exported():
    assert "NumberPlane" not in mp.__all__
    assert issubclass(mp.NumberPlane, mp.CartesianAxes)


def test_np3_a_range_change_regenerates_the_grid():
    with tempconfig(RUN):
        plane = mp.NumberPlane(x_range=(-3, 3, 1), y_range=(-2, 2, 1))
    before = len(our_lines(plane, "major"))
    plane.x.range = (-1, 1)
    assert len(our_lines(plane, "major")) < before
