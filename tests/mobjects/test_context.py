"""Writes outside animations, attributed from the call stack (F-904, F-208, F-111).

Rows WR-1 to WR-7 of `docs/acceptance/09-leaves-context-frame.md`. The oracle is a plain
twin: plain `VMobject`s with the same points, in the same container, given the same
operation.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import DOWN, LEFT, ORIGIN, RIGHT, UP, Dot, VGroup

import manim_plots as mp

from .helpers import assert_same, assert_same_curve, plain, twins, visible_leaves


def system():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    return ax, ax.plot(np.sin)


def wave(p):
    return p + np.array([0.0, 0.15 * np.sin(p[0]), 0.0])


# Each takes a mobject and the pivot to use, so the twin turns about the same point.
OPERATIONS = {
    "shift": lambda m, c: m.shift(UP + 2 * RIGHT),
    "rotate": lambda m, c: m.rotate(0.6, about_point=c),
    "scale": lambda m, c: m.scale(0.7, about_point=c),
    "stretch": lambda m, c: m.stretch(1.8, 0, about_point=c),
    "flip": lambda m, c: m.flip(UP, about_point=c),
    "apply_matrix": lambda m, c: m.apply_matrix([[1, 0.3], [0.2, 1]], about_point=c),
    "move_to": lambda m, c: m.shift(UP - c),
    "next_to": lambda m, c: m.shift(np.array([2.0, -1.0, 0.0])),
}


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_wr1_an_operation_on_the_system_carries_its_artists(name):
    ax, curve = system()
    pivot = ax.get_center().copy()
    reference = VGroup(*twins(ax, curve))
    OPERATIONS[name](ax, pivot)
    OPERATIONS[name](reference, pivot)
    assert_same([*visible_leaves(ax), curve], reference.submobjects)


def test_wr1_methods_that_place_by_bounds_move_like_the_twin():
    for method in ("move_to", "to_corner", "next_to"):
        ax, _ = system()
        reference = VGroup(*twins(ax))
        if method == "move_to":
            ax.move_to(UP)
            reference.move_to(UP)
        elif method == "to_corner":
            ax.to_corner(UP + RIGHT)
            reference.to_corner(UP + RIGHT)
        else:
            ax.next_to(Dot(3 * RIGHT), DOWN)
            reference.next_to(Dot(3 * RIGHT), DOWN)
        assert_same(visible_leaves(ax), reference.submobjects)


def test_wr1_a_non_affine_function_bends_the_system_and_its_curve():
    ax, curve = system()
    _, reference = system()
    unmoved = mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    ax.apply_function(wave)
    anchors = curve.get_anchors()
    x = ax.p2c(anchors)[0]
    expected = np.array([wave(p) for p in np.asarray(unmoved.c2p(x, np.sin(x))).T])
    np.testing.assert_allclose(anchors, expected, atol=1e-2)
    assert reference is not curve


@pytest.mark.parametrize("order", ["system first", "curve first", "nested"])
def test_wr2_a_container_holding_the_system_moves_the_curve_once(order):
    ax, curve = system()
    reference = VGroup(*twins(ax, curve))
    if order == "system first":
        container = VGroup(ax, curve)
    elif order == "curve first":
        container = VGroup(curve, ax)
    else:
        container = VGroup(VGroup(ax), curve)
    container.shift(2 * RIGHT + DOWN)
    reference.shift(2 * RIGHT + DOWN)
    assert_same([*visible_leaves(ax), curve], reference.submobjects)


def test_wr3_another_container_gives_the_curve_its_own_transform():
    _, curve = system()
    dot = Dot(RIGHT)
    twin, dot_twin = plain(curve), Dot(RIGHT)
    VGroup(curve, dot).shift(UP)
    VGroup(twin, dot_twin).shift(UP)
    np.testing.assert_allclose(curve.points, twin.points, atol=1e-9)
    np.testing.assert_allclose(dot.get_center(), dot_twin.get_center())


def test_wr3_the_own_transform_survives_a_data_change():
    ax, curve = system()
    VGroup(curve, Dot()).shift(UP)
    ax.x.range = (-2, 2)
    fresh_ax = mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    fresh = fresh_ax.plot(np.sin)
    np.testing.assert_allclose(curve.points, fresh.points + UP, atol=1e-9)


def test_wr4_the_own_transform_lives_in_the_systems_space():
    ax, curve = system()
    curve.shift(UP)
    ax.shift(RIGHT)
    _, reference = system()
    np.testing.assert_allclose(curve.points, reference.points + UP + RIGHT, atol=1e-9)
    ax.rotate(0.5, about_point=ORIGIN)
    turned = plain(reference.shift(UP + RIGHT)).rotate(0.5, about_point=ORIGIN)
    np.testing.assert_allclose(curve.points, turned.points, atol=1e-9)


@pytest.mark.parametrize(
    "operation",
    [
        lambda m: m.rotate(0.4, about_point=ORIGIN),
        lambda m: m.scale(1.3, about_point=LEFT),
        lambda m: m.stretch(0.6, 1, about_point=ORIGIN),
        lambda m: m.apply_matrix([[1, 0.5], [0, 1]], about_point=ORIGIN),
    ],
    ids=["rotate", "scale", "stretch", "apply_matrix"],
)
def test_wr5_an_operation_on_the_curve_is_an_exact_own_transform(operation):
    ax, curve = system()
    operation(curve)
    ax.x.range = (-2, 2)
    fresh_ax = mp.Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
    expected = plain(fresh_ax.plot(np.sin))
    operation(expected)
    # Sampling follows the screen, so a scaled curve may hold other samples.
    assert_same_curve(curve.points, expected.points, atol=5e-3)


def test_wr6_a_bare_write_lasts_until_the_next_rebuild():
    _, curve = system()
    derived = np.array(curve.points, copy=True)
    curve.points[:, 1] += 0.5
    np.testing.assert_allclose(curve.points, derived + np.array([0, 0.5, 0]))
    curve.refresh()
    np.testing.assert_allclose(curve.points, derived, atol=1e-12)


def test_wr7_a_singular_frame_refuses_what_needs_its_inverse():
    ax, curve = system()
    ax.scale(0)
    with pytest.raises(ValueError, match="singular"):
        ax.p2c(ORIGIN)
    before = np.array(curve.points, copy=True)
    with pytest.raises(ValueError):
        curve.shift(UP)
    np.testing.assert_array_equal(curve.points, before)
