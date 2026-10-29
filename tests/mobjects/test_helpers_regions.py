"""Task 17: bound helpers, regions.

Rows RG, AR, FB and RR of `docs/acceptance/17-helpers-regions.md`. Areas are checked
against integrals, and Manim's own helpers on Manim's own `Axes` are the oracle where
their picture is not a defect.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import (
    BLUE,
    DEGREES,
    GREEN,
    RED,
    Axes,
    Scene,
    ValueTracker,
)

import manim_plots as mp

from .helpers import along, probe

UNIT = (12 / 14) * (6 / 8)  # scene area of one data unit on the default axes


def quarter(x):
    return x**2 / 4


def signed(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def area(region) -> float:
    """The filled area, summed over the closed pieces of a region."""
    return sum(
        abs(signed(along(np.asarray(piece), 64)))
        for piece in region.get_subpaths()
        if len(piece)
    )


def closed(region) -> bool:
    return all(
        np.allclose(piece[0], piece[-1], atol=1e-9)
        for piece in region.get_subpaths()
        if len(piece)
    )


def run(construct) -> None:
    probe(construct, lambda: None)


# --- RG: filled regions ---------------------------------------------------------------


def test_rg1_a_region_is_one_registered_artist_without_a_label():
    ax = mp.Axes()
    region = ax.get_area(ax.plot(quarter), x_range=(0, 2))
    assert isinstance(region, mp.FilledRegion)
    assert region in ax.artists
    assert region not in ax.get_legend_handles_labels()[0]
    assert closed(region)


def test_rg2_the_area_is_the_integral():
    ax = mp.Axes()
    region = ax.get_area(ax.plot(quarter), x_range=(0, 2))
    assert area(region) == pytest.approx(2 / 3 * UNIT, rel=1e-3)


def test_rg3_a_region_is_clipped_to_the_rectangle():
    ax = mp.Axes()  # y in (-4, 4): x**2 / 4 leaves the top at x = 4
    region = ax.get_area(ax.plot(quarter, x_range=(2, 6)), x_range=(2, 6))
    assert area(region) == pytest.approx((56 / 12 + 8) * UNIT, rel=1e-3)
    assert region.get_top()[1] <= ax.c2p(0, 4)[1] + 1e-9
    assert closed(region)


def test_rg3_the_x_interval_is_restricted_to_the_viewport():
    ax = mp.Axes()  # x in (-7, 7)
    region = ax.get_area(ax.plot(quarter, x_range=(5, 9)), x_range=(5, 9))
    assert area(region) == pytest.approx(2 * 4 * UNIT, rel=1e-3)


def test_rg3_clipping_per_axis_and_off():
    ax = mp.Axes()
    graph = ax.plot(quarter, x_range=(2, 6))
    tall = ax.get_area(graph, x_range=(2, 6), clip=(True, False))
    assert area(tall) == pytest.approx(208 / 12 * UNIT, rel=1e-3)
    whole = ax.get_area(ax.plot(quarter, x_range=(5, 9)), x_range=(5, 9), clip=False)
    assert area(whole) == pytest.approx(604 / 12 * UNIT, rel=1e-3)


def test_rg4_crossing_boundaries_keep_both_lobes():
    ax = mp.Axes()
    xs = np.linspace(-3, 3, 61)
    region = ax.fill_between(xs, np.sin(xs), 0)
    assert region.get_top()[1] == pytest.approx(ax.c2p(0, 1)[1], abs=1e-2)
    assert region.get_bottom()[1] == pytest.approx(ax.c2p(0, -1)[1], abs=1e-2)


def test_rg_a_region_follows_its_graphs_parameters():
    ax = mp.Axes()
    graph = ax.plot(lambda x, a=1.0: a * x**2 / 4)
    region = ax.get_area(graph, x_range=(0, 2))
    graph.set_parameters(a=2.0)
    assert area(region) == pytest.approx(4 / 3 * UNIT, rel=1e-3)


def test_rg_a_tracker_end_sweeps_the_area_in():
    ax = mp.Axes()
    graph = ax.plot(quarter)
    end = ValueTracker(1.0)
    region = ax.get_area(graph, x_range=(0, end))

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, region)
        scene.play(end.animate.set_value(2.0), run_time=1)

    run(construct)
    assert area(region) == pytest.approx(2 / 3 * UNIT, rel=1e-3)


def test_rg5_a_style_survives_a_rederivation():
    ax = mp.Axes()
    graph = ax.plot(lambda x, a=1.0: a * x**2 / 4)
    region = ax.get_area(graph, x_range=(0, 2))
    region.set_fill(RED, opacity=0.8)
    graph.set_parameters(a=2.0)
    assert region.get_fill_color() == RED
    assert region.get_fill_opacity() == pytest.approx(0.8)


# --- AR: get_area ---------------------------------------------------------------------


def test_ar1_manims_defaults():
    ours, theirs = mp.Axes(), Axes()
    a = ours.get_area(ours.plot(quarter), x_range=(0, 2))
    b = theirs.get_area(theirs.plot(quarter), x_range=(0, 2))
    assert a.get_fill_opacity() == pytest.approx(b.get_fill_opacity())
    assert a.get_stroke_opacity() == pytest.approx(b.get_stroke_opacity())
    assert a.get_stroke_width() == pytest.approx(b.get_stroke_width())
    assert a.get_fill_colors() == b.get_fill_colors()


def test_ar1_ranges_that_do_not_overlap_raise():
    ax = mp.Axes()
    graph = ax.plot(quarter, x_range=(0, 2))
    with pytest.raises(ValueError, match="Ranges not matching"):
        ax.get_area(
            graph, x_range=(0, 2), bounded_graph=ax.plot(quarter, x_range=(3, 4))
        )


def test_ar2_area_and_box_equal_manims_on_default_axes():
    ours, theirs = mp.Axes(), Axes()
    a = ours.get_area(ours.plot(quarter), x_range=(-2, 3))
    b = theirs.get_area(theirs.plot(quarter), x_range=(-2, 3))
    assert area(a) == pytest.approx(abs(signed(np.asarray(b.get_vertices()))), rel=1e-3)
    for corner in ([-1, -1, 0], [1, 1, 0]):
        np.testing.assert_allclose(
            a.get_corner(corner), b.get_corner(corner), atol=1e-3
        )


def test_ar2_the_baseline_is_the_x_axis_where_it_is_drawn():
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(2, 10, 1))  # x axis at y = 2
    region = ax.get_area(ax.plot(lambda x: x + 3), x_range=(1, 3))
    assert region.get_bottom()[1] == pytest.approx(ax.c2p(0, 2)[1], abs=1e-9)
    assert area(region) == pytest.approx(6 * 3 * 0.75, rel=1e-3)


def test_ar2_between_two_graphs():
    ax = mp.Axes()
    region = ax.get_area(
        ax.plot(lambda x: x + 2), x_range=(0, 2), bounded_graph=ax.plot(quarter)
    )
    assert area(region) == pytest.approx((2 + 4 - 2 / 3) * UNIT, rel=1e-3)


def test_ar3_a_constant_bounded_graph():
    ax = mp.Axes()
    region = ax.get_area(ax.plot(lambda x: x + 2), x_range=(0, 2), bounded_graph=0.5)
    assert area(region) == pytest.approx((2 + 4 - 1) * UNIT, rel=1e-3)


# --- FB: fill_between -----------------------------------------------------------------


XS = np.linspace(0, 2, 21)


def test_fb1_arrays_and_a_scalar():
    ax = mp.Axes()
    assert area(ax.fill_between(XS, XS)) == pytest.approx(2 * UNIT, rel=1e-6)
    assert area(ax.fill_between(XS, XS + 1, 0.5)) == pytest.approx(3 * UNIT, rel=1e-6)


def test_fb2_where_keeps_the_true_stretches():
    ax = mp.Axes()
    kept = ax.fill_between(XS, XS, where=XS > 1)
    assert area(kept) == pytest.approx((4 - 1.21) / 2 * UNIT, rel=1e-6)


def test_fb2_interpolate_ends_at_the_crossing():
    ax = mp.Axes()
    y1 = XS - 1
    plain = ax.fill_between(XS, y1, 0, where=y1 > 0)
    exact = ax.fill_between(XS, y1, 0, where=y1 > 0, interpolate=True)
    assert area(plain) == pytest.approx(0.405 * UNIT, rel=1e-6)
    assert area(exact) == pytest.approx(0.5 * UNIT, rel=1e-6)


def test_fb3_a_graph_or_a_callable_as_a_boundary():
    ax = mp.Axes()
    expected = np.trapezoid(quarter(XS), XS) * UNIT
    assert area(ax.fill_between(XS, ax.plot(quarter))) == pytest.approx(
        expected, rel=1e-6
    )
    assert area(ax.fill_between(XS, quarter)) == pytest.approx(expected, rel=1e-6)


def test_fb4_defaults_take_the_cycle():
    ax = mp.Axes()
    region = ax.fill_between(XS, XS)
    assert region.get_fill_color() == mp.COLOR_CYCLE[0]
    assert region.get_fill_opacity() == pytest.approx(0.3)
    assert region.get_stroke_width() == 0
    assert ax.plot(quarter).get_color() == mp.COLOR_CYCLE[1]


@pytest.mark.parametrize(
    ("kwargs", "name"),
    [
        ({"x": XS, "y1": XS[:-1]}, "y1"),
        ({"x": XS, "y1": XS, "y2": XS[:-1]}, "y2"),
        ({"x": XS, "y1": XS, "where": XS[:-1] > 1}, "where"),
        ({"x": np.append(XS, np.nan), "y1": np.append(XS, 1.0)}, "x"),
    ],
)
def test_fb4_bad_arguments_raise(kwargs, name):
    with pytest.raises(ValueError, match=name):
        mp.Axes().fill_between(**kwargs)


# --- RR: get_riemann_rectangles -------------------------------------------------------


def test_rr1_a_group_of_regions():
    ax = mp.Axes()
    rects = ax.get_riemann_rectangles(ax.plot(quarter), x_range=(0, 2), dx=0.5)
    assert isinstance(rects, mp.HelperGroup)
    assert all(isinstance(r, mp.FilledRegion) for r in rects)
    xs = [r.get_left()[0] for r in rects]
    assert xs == sorted(xs)


def test_rr2_the_count_is_exact():
    ax = mp.Axes()
    graph = ax.plot(quarter)
    assert len(ax.get_riemann_rectangles(graph, x_range=[1, 1.3], dx=0.1)) == 3
    theirs = Axes()
    assert len(theirs.get_riemann_rectangles(theirs.plot(quarter), [1, 1.3], 0.1)) == 4


@pytest.mark.parametrize("sample", ["left", "right", "center"])
def test_rr4_corners_equal_manims_on_default_axes(sample):
    ours, theirs = mp.Axes(), Axes()
    a = ours.get_riemann_rectangles(
        ours.plot(quarter), x_range=(0.5, 2.5), dx=0.5, input_sample_type=sample
    )
    b = theirs.get_riemann_rectangles(
        theirs.plot(quarter), x_range=(0.5, 2.5), dx=0.5, input_sample_type=sample
    )
    assert len(a) == len(b) == 4
    for ours_rect, their_rect in zip(a, b, strict=True):
        for corner in ([-1, -1, 0], [1, 1, 0]):
            np.testing.assert_allclose(
                ours_rect.get_corner(corner), their_rect.get_corner(corner), atol=1e-6
            )


def test_rr3_the_bounded_graph_is_read_at_the_sample():
    ax = mp.Axes()
    rects = ax.get_riemann_rectangles(
        ax.plot(lambda x: quarter(x) + 1),
        x_range=(1, 2),
        dx=1,
        input_sample_type="right",
        bounded_graph=ax.plot(lambda x: x / 4),
    )
    assert rects[0].get_bottom()[1] == pytest.approx(ax.c2p(0, 0.5)[1], abs=1e-6)
    assert rects[0].get_top()[1] == pytest.approx(ax.c2p(0, 2)[1], abs=1e-6)


def test_rr5_colours_equal_manims():
    ours, theirs = mp.Axes(), Axes()

    def shifted(x):  # below the axis on the first two samples
        return quarter(x) - 1

    a = ours.get_riemann_rectangles(ours.plot(shifted), x_range=(0, 4), dx=1)
    b = theirs.get_riemann_rectangles(theirs.plot(shifted), x_range=(0, 4), dx=1)
    assert [r.get_fill_color() for r in a] == [r.get_fill_color() for r in b]
    assert [r.get_stroke_color() for r in a] == [r.get_stroke_color() for r in b]
    assert [r.get_stroke_width() for r in a] == [r.get_stroke_width() for r in b]


def test_rr5_blend_strokes_in_the_fill_colour():
    ax = mp.Axes()
    rects = ax.get_riemann_rectangles(
        ax.plot(quarter), x_range=(0, 2), dx=0.5, blend=True
    )
    assert all(r.get_stroke_color() == r.get_fill_color() for r in rects)


def test_rr4_rectangles_follow_rotated_axes():
    ax = mp.Axes().rotate(30 * DEGREES)
    rects = ax.get_riemann_rectangles(ax.plot(quarter), x_range=(1, 2), dx=1)
    bottom_left = ax.c2p(1, 0)
    bottom_right = ax.c2p(1 + 1.001, 0)
    points = np.asarray(rects[0].points)
    assert np.min(np.linalg.norm(points - bottom_left, axis=1)) < 1e-6
    assert np.min(np.linalg.norm(points - bottom_right, axis=1)) < 1e-6


def test_rr6_a_tracker_dx_changes_the_count_and_keeps_the_first():
    ax = mp.Axes()
    graph = ax.plot(quarter)
    dx = ValueTracker(0.5)
    rects = ax.get_riemann_rectangles(graph, x_range=(0, 2), dx=dx)
    first = rects[0]

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, rects)
        scene.play(dx.animate.set_value(0.25), run_time=1)

    run(construct)
    assert len(rects) == 8
    assert rects[0] is first


def test_rr7_errors():
    ax = mp.Axes()
    graph = ax.plot(quarter)
    with pytest.raises(ValueError):
        ax.get_riemann_rectangles(graph, x_range=(0, 2), input_sample_type="middle")
    with pytest.raises(ValueError, match="dx"):
        ax.get_riemann_rectangles(graph, x_range=(0, 2), dx=0)


def test_rr_colours_are_a_gradient_over_the_rectangles():
    ax = mp.Axes()
    rects = ax.get_riemann_rectangles(
        ax.plot(quarter), x_range=(0, 2), dx=0.5, color=(BLUE, GREEN)
    )
    assert rects[0].get_fill_color() == BLUE
    assert rects[-1].get_fill_color() == GREEN
