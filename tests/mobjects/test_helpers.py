"""Manim's helper methods under their names and meanings (F-609, F-1009).

Rows HM-1 to HM-4 of `docs/acceptance/10-axis-decoration.md`. The oracle is Manim's own
`Axes`, built with the same arguments, except where the library fixes a defect: `p2n`
inverts `n2p` on every scale (15c), and a returned decoration follows its system (D27).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from manim import DOWN, RIGHT, UP, Axes, tempconfig

import manim_plots as mp

from .helpers import RUN

CASE: dict[str, Any] = {
    "x_range": (-1, 9, 1),
    "y_range": (-2, 3, 0.5),
    "x_length": 10,
    "y_length": 5,
}


def pair():
    with tempconfig(RUN):
        return mp.Axes(**CASE), Axes(**CASE)


def test_hm1_system_helpers_return_manims_values():
    ours, theirs = pair()
    np.testing.assert_allclose(ours.coords_to_point(2, 1), theirs.coords_to_point(2, 1))
    point = theirs.c2p(3, -1)
    np.testing.assert_allclose(
        ours.point_to_coords(point), theirs.point_to_coords(point)
    )
    np.testing.assert_allclose(ours.get_origin(), theirs.get_origin(), atol=1e-9)
    assert ours.get_x_unit_size() == pytest.approx(theirs.get_x_unit_size())
    assert ours.get_y_unit_size() == pytest.approx(theirs.get_y_unit_size())
    assert ours.get_x_axis() is ours.x_axis and ours.get_y_axis() is ours.y_axis
    assert ours.get_axis(0) is ours.x_axis and ours.get_axis(1) is ours.y_axis
    assert list(ours.get_axes()) == [ours.x_axis, ours.y_axis]


def test_hm2_axis_conversions_take_arrays_and_invert():
    ours, theirs = pair()
    xs = np.array([-1.0, 0.5, 4.0])
    np.testing.assert_allclose(ours.x_axis.n2p(xs), theirs.x_axis.n2p(xs), atol=1e-9)
    np.testing.assert_allclose(
        ours.x_axis.number_to_point(2.0), theirs.x_axis.n2p(2.0), atol=1e-9
    )
    points = ours.x_axis.n2p(xs)
    np.testing.assert_allclose(ours.x_axis.p2n(points), xs, atol=1e-9)
    assert ours.x_axis.point_to_number(ours.x_axis.n2p(3.0)) == pytest.approx(3.0)
    assert ours.x_axis.get_unit_size() == pytest.approx(theirs.x_axis.get_unit_size())
    np.testing.assert_allclose(
        ours.x_axis.get_unit_vector(), theirs.x_axis.get_unit_vector()
    )


def test_hm2_tick_queries():
    ours, theirs = pair()
    np.testing.assert_allclose(
        ours.x_axis.get_tick(3).points, theirs.x_axis.get_tick(3).points, atol=1e-9
    )
    # Manim's values without the origin; the end under the tip is left out (F-411).
    np.testing.assert_allclose(
        ours.x_axis.get_tick_range(), [-1.0, *np.arange(1, 9) * 1.0]
    )
    assert len(ours.x_axis.get_tick_marks()) == len(ours.x_axis.ticks)


def test_hm2_numbers_and_labels_on_an_axis():
    ours, theirs = pair()
    with tempconfig(RUN):
        ours.x_axis.add_numbers([1, 2, 3])
        theirs.x_axis.add_numbers([1, 2, 3])
        number = ours.x_axis.get_number_mobject(2)
        their_number = theirs.x_axis.get_number_mobject(2)
        np.testing.assert_allclose(
            number.get_center(), their_number.get_center(), atol=1e-6
        )
        assert len(ours.x_axis.get_number_mobjects(1, 2)) == 2
        ours.x_axis.add_labels({1: "one", 4: "four"})
        theirs.x_axis.add_labels({1: "one", 4: "four"})
        assert len(ours.x_axis.labels) == 2
        for mine, manims in zip(ours.x_axis.labels, theirs.x_axis.labels, strict=True):
            np.testing.assert_allclose(
                mine.get_center(), manims.get_center(), atol=1e-6
            )
        # Manim's get_labels means get_number_mobjects() of every tick, not the
        # added labels (its own call fails on 0.21: default_numbers_to_display).
        assert len(ours.x_axis.get_labels()) == len(ours.x_axis.get_tick_range())


def test_hm2_add_ticks_is_idempotent():
    ours, _ = pair()
    count = len(ours.x_axis.ticks)
    ours.x_axis.add_ticks()
    assert len(ours.x_axis.ticks) == count


def test_hm3_add_coordinates_with_manims_arguments():
    ours, theirs = pair()
    with tempconfig(RUN):
        ours.add_coordinates([1, 2, 3], {1: "a", 2: "b"})
        theirs.add_coordinates([1, 2, 3], {1: "a", 2: "b"})
    for mine, manims in (
        (ours.x_axis.numbers, theirs.x_axis.numbers),
        (ours.y_axis.labels, theirs.y_axis.labels),
    ):
        assert len(mine) == len(manims)
        for a, b in zip(mine, manims, strict=True):
            np.testing.assert_allclose(a.get_center(), b.get_center(), atol=1e-6)


def test_hm3_axis_labels_sit_where_manims_do():
    ours, theirs = pair()
    with tempconfig(RUN):
        mine, manims = ours.get_axis_labels(), theirs.get_axis_labels()
        for a, b in zip(mine, manims, strict=True):
            np.testing.assert_allclose(a.get_center(), b.get_center(), atol=1e-6)
        x_label = ours.get_x_axis_label("t", edge=DOWN, direction=DOWN)
        their_x = theirs.get_x_axis_label("t", edge=DOWN, direction=DOWN)
        np.testing.assert_allclose(
            x_label.get_center(), their_x.get_center(), atol=1e-6
        )
        y_label = ours.get_y_axis_label("v")
        np.testing.assert_allclose(
            y_label.get_center(), theirs.get_y_axis_label("v").get_center(), atol=1e-6
        )


def test_hm3_axis_labels_follow_their_system():
    ours, _ = pair()
    with tempconfig(RUN):
        labels = ours.get_axis_labels()
    before = [m.get_center().copy() for m in labels]
    ours.shift(2 * RIGHT + UP)
    for label, start in zip(labels, before, strict=True):
        np.testing.assert_allclose(
            label.get_center(), start + 2 * RIGHT + UP, atol=1e-9
        )


def test_hm3_a_graph_label_sits_where_manims_does_and_follows_the_graph():
    ours, theirs = pair()
    with tempconfig(RUN):
        graph, their_graph = ours.plot(np.sin), theirs.plot(np.sin)
        label = ours.get_graph_label(graph, "f(x)", x_val=2, direction=UP, dot=True)
        their_label = theirs.get_graph_label(
            their_graph, "f(x)", x_val=2, direction=UP, dot=True
        )
    np.testing.assert_allclose(label.get_center(), their_label.get_center(), atol=1e-6)
    ours.shift(RIGHT)
    np.testing.assert_allclose(
        label.get_center(), their_label.get_center() + RIGHT, atol=1e-6
    )


def test_hm4_a_misspelt_attribute_raises():
    ax = mp.Axes()
    with pytest.raises(AttributeError):
        ax.set_colour("#FF0000")
    with pytest.raises(AttributeError):
        _ = ax.x_axis.tick_lenght
    ax.set_color("#FF0000")
    assert ax.get_x() == pytest.approx(0.0, abs=1e-9)
