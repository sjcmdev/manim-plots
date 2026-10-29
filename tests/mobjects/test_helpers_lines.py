"""Task 16: bound helpers, lines and tangents.

Rows HB, DL, TL, TG, SC and DG of `docs/acceptance/16-helpers-lines.md`. The oracle is
Manim's own helper on Manim's own `Axes` where Manim has one and its picture is not a
defect, and otherwise geometry computed from `c2p` and `i2gp`.
"""

from __future__ import annotations

import numpy as np
import pytest
from manim import (
    DEGREES,
    GREEN,
    RED,
    UP,
    Arrow,
    Axes,
    DashedLine,
    Dot,
    Line,
    Scene,
    ValueTracker,
)

import manim_plots as mp

from .helpers import probe


def quarter(x):
    return x**2 / 4


def pair():
    """Our default axes with x**2 / 4, and Manim's with the same."""
    ours, theirs = mp.Axes(), Axes()
    return ours, ours.plot(quarter), theirs, theirs.plot(quarter)


def ends(mob) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(mob.points)
    return points[0], points[-1]


def direction(start, end) -> np.ndarray:
    v = np.asarray(end) - np.asarray(start)
    return v / np.linalg.norm(v)


def collapsed(mob) -> bool:
    points = np.asarray(mob.points)
    return len(points) == 0 or float(np.ptp(points, axis=0).max()) == 0.0


def run(construct, record):
    return probe(construct, record)


# --- HB: the bound-helper base --------------------------------------------------------


def test_hb1_a_helper_line_is_a_registered_artist_without_a_label():
    ax, _, _, _ = pair()
    line = ax.get_vertical_line(ax.c2p(2, 1))
    assert isinstance(line, mp.HelperLine)
    assert line in ax.artists
    assert line not in ax.get_legend_handles_labels()[0]
    line.set_label("drop")
    assert line in ax.get_legend_handles_labels()[0]


def test_hb2_a_tracker_slides_a_t_label_with_no_always_redraw():
    ax, graph, _, _ = pair()
    t = ValueTracker(1.0)
    label = ax.get_T_label(t, graph)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, label)
        scene.play(t.animate.set_value(3.0), run_time=1)

    xs = run(construct, lambda: float(ax.p2c(label.triangle.get_top())[0]))
    assert xs[-1] == pytest.approx(3.0, abs=1e-6)
    assert len({round(x, 6) for x in xs}) > 3


def test_hb2_a_callable_input_is_read_every_frame():
    ax, _, _, _ = pair()
    t = ValueTracker(-1.0)
    line = ax.axvline(lambda: t.get_value())

    def construct(scene: Scene) -> None:
        scene.add(ax, line)
        scene.play(t.animate.set_value(2.0), run_time=1)

    xs = run(construct, lambda: float(ax.p2c(ends(line)[0])[0]))
    assert xs[-1] == pytest.approx(2.0, abs=1e-6)


def test_hb3_a_scene_point_is_held_in_data():
    ax, _, _, _ = pair()
    line = ax.get_vertical_line(ax.c2p(2, 1), line_func=Line)
    ax.set_x_range((-3, 3))
    start, end = ends(line)
    np.testing.assert_allclose(end, ax.c2p(2, 1), atol=1e-9)
    np.testing.assert_allclose(start, ax.c2p(2, 0), atol=1e-9)


def test_hb3_a_mobject_point_is_followed():
    ax, _, _, _ = pair()
    dot = Dot(ax.c2p(2, 1))
    line = ax.get_vertical_line(dot, line_func=Line)

    def construct(scene: Scene) -> None:
        scene.add(ax, line, dot)
        scene.play(dot.animate.move_to(ax.c2p(-1, 2)), run_time=1)

    run(construct, lambda: None)
    np.testing.assert_allclose(ends(line)[1], ax.c2p(-1, 2), atol=1e-6)
    np.testing.assert_allclose(ends(line)[0], ax.c2p(-1, 0), atol=1e-6)


def test_hb3_a_callable_point_is_read_every_frame():
    ax, graph, _, _ = pair()
    t = ValueTracker(1.0)
    line = ax.get_vertical_line(lambda: ax.i2gp(t.get_value(), graph), line_func=Line)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, line)
        scene.play(t.animate.set_value(2.5), run_time=1)

    run(construct, lambda: None)
    np.testing.assert_allclose(ends(line)[1], ax.c2p(2.5, quarter(2.5)), atol=1e-6)


def test_hb4_a_helper_follows_its_graphs_parameters():
    ax = mp.Axes()
    graph = ax.plot(lambda x, a=1.0: a * x**2 / 4)
    lines = ax.get_vertical_lines_to_graph(
        graph, x_range=(1, 3), num_lines=3, line_func=Line
    )
    graph.set_parameters(a=0.5)
    for x, line in zip((1.0, 2.0, 3.0), lines, strict=True):
        np.testing.assert_allclose(ends(line)[1], ax.c2p(x, x**2 / 8), atol=1e-6)


def test_hb4_a_helper_follows_become():
    ax, graph, _, _ = pair()
    line = ax.get_vertical_lines_to_graph(
        graph, x_range=(1, 2), num_lines=2, line_func=Line
    )
    graph.become(ax.plot(lambda x: x / 2))
    np.testing.assert_allclose(ends(line[1])[1], ax.c2p(2, 1), atol=1e-6)


def test_hb4_a_helper_follows_the_system():
    ax, graph, _, _ = pair()
    label = ax.get_T_label(2, graph)
    ax.shift(UP).rotate(20 * DEGREES)
    np.testing.assert_allclose(ends(label.line)[0], ax.c2p(2, 0), atol=1e-6)
    np.testing.assert_allclose(ends(label.line)[1], ax.c2p(2, 1), atol=1e-6)


def test_hb4_a_helper_follows_an_animated_range():
    ax, graph, _, _ = pair()
    label = ax.get_T_label(2, graph)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, label)
        scene.play(ax.animate.set_x_range((-3, 3)), run_time=1)

    run(construct, lambda: None)
    np.testing.assert_allclose(ends(label.line)[1], ax.c2p(2, 1), atol=1e-6)


def test_hb4_a_graph_of_another_system_raises():
    ax = mp.Axes()
    other = mp.Axes().plot(np.sin)
    with pytest.raises(ValueError, match="graph"):
        ax.get_T_label(1, other)
    with pytest.raises(ValueError, match="graph"):
        ax.get_secant_slope_group(1, other)


def test_hb5_a_drop_line_is_placed_through_a_log_scale():
    ax = mp.Axes(x_range=(1, 100, 1), y_range=(0, 4, 1), x_scale="log")
    line = ax.get_vertical_line(ax.c2p(10, 3), line_func=Line)
    np.testing.assert_allclose(ends(line)[0], ax.c2p(10, 0), atol=1e-9)
    np.testing.assert_allclose(ends(line)[1], ax.c2p(10, 3), atol=1e-9)


def test_hb5_a_drop_line_follows_rotated_axes():
    ax = mp.Axes().rotate(30 * DEGREES)
    line = ax.get_vertical_line(ax.c2p(2, 1), line_func=Line)
    np.testing.assert_allclose(ends(line)[0], ax.c2p(2, 0), atol=1e-9)


def test_hb6_a_style_on_a_part_survives_a_rederivation():
    ax, graph, _, _ = pair()
    dx = ValueTracker(1.0)
    group = ax.get_secant_slope_group(1, graph, dx=dx)
    group.dx_line.set_color(RED).set_stroke(width=7)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, group)
        scene.play(dx.animate.set_value(0.5), run_time=1)

    run(construct, lambda: None)
    assert group.dx_line.get_color() == RED
    assert group.dx_line.get_stroke_width() == 7
    np.testing.assert_allclose(
        ends(group.dx_line)[1], ax.c2p(1.5, quarter(1)), atol=1e-6
    )


def test_hb6_a_callable_label_reads_the_value():
    ax, graph, _, _ = pair()
    t = ValueTracker(1.0)
    live = ax.get_T_label(t, graph, label=lambda x: f"{x:.1f}")

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, live)
        scene.play(t.animate.set_value(2.5), run_time=1)

    run(construct, lambda: None)
    fixed = ax.get_T_label(2.5, graph, label="2.5")
    np.testing.assert_allclose(live.label.points, fixed.label.points, atol=1e-6)


def test_hb7_a_tracker_outside_the_graph_collapses_the_helper():
    ax = mp.Axes()
    graph = ax.plot(quarter, x_range=(-2, 2))
    t = ValueTracker(1.0)
    label = ax.get_T_label(t, graph)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, label)
        scene.play(t.animate.set_value(3.0), run_time=1)
        scene.play(t.animate.set_value(1.5), run_time=1)

    states = run(construct, lambda: (collapsed(label.line), collapsed(label.triangle)))
    assert (True, True) in states
    assert states[-1] == (False, False)


def test_hb7_a_number_outside_raises_at_the_call():
    ax = mp.Axes()
    graph = ax.plot(quarter, x_range=(-2, 2))
    with pytest.raises(ValueError, match="x_val"):
        ax.get_T_label(3.0, graph)
    with pytest.raises(ValueError, match="x"):
        ax.get_secant_slope_group(3.0, graph)


def test_hb8_dashed_line_is_manims_dash():
    ax, _, _, _ = pair()
    line = ax.get_vertical_line(ax.c2p(2, 1))
    assert line.line_style is mp.LineStyle.DASHED
    assert line.dash == pytest.approx((0.025, 0.025))
    custom = ax.get_vertical_line(
        ax.c2p(2, 1), line_config={"dash_length": 0.2, "dashed_ratio": 0.75}
    )
    assert custom.dash == pytest.approx((0.15, 0.05))
    solid = ax.get_vertical_line(ax.c2p(2, 1), line_func=Line)
    assert solid.line_style is mp.LineStyle.SOLID
    assert not isinstance(line, (Line, DashedLine))


def test_hb8_other_line_funcs_and_keys_raise():
    ax, _, _, _ = pair()
    with pytest.raises(TypeError, match="line_func"):
        ax.get_vertical_line(ax.c2p(2, 1), line_func=Arrow)
    with pytest.raises(TypeError, match="sparkle"):
        ax.get_vertical_line(ax.c2p(2, 1), line_config={"sparkle": 1})


# --- DL: drop lines and reference lines -----------------------------------------------


@pytest.mark.parametrize("index", [0, 1])
def test_dl1_a_line_from_an_axis_matches_manims(index):
    ours, _, theirs, _ = pair()
    a = ours.get_line_from_axis_to_point(index, ours.c2p(2, 1.5), line_func=Line)
    b = theirs.get_line_from_axis_to_point(index, theirs.c2p(2, 1.5), line_func=Line)
    np.testing.assert_allclose(ends(a), [b.get_start(), b.get_end()], atol=1e-9)
    assert a.get_stroke_width() == 2
    assert a.get_color() == b.get_color()


def test_dl1_the_line_starts_at_the_axis_where_it_is_drawn():
    ax = mp.Axes(x_range=(-3, 3, 1), y_range=(2, 10, 1))
    line = ax.get_vertical_line(ax.c2p(1, 6), line_func=Line)
    np.testing.assert_allclose(ends(line)[0], ax.c2p(1, 2), atol=1e-9)
    ax.x_axis.set_position("top")
    np.testing.assert_allclose(ends(line)[0], ax.c2p(1, 10), atol=1e-9)


def test_dl2_vertical_horizontal_and_both():
    ax, _, _, _ = pair()
    p = ax.c2p(2, 1)
    v = ax.get_vertical_line(p, line_func=Line)
    h = ax.get_horizontal_line(p, line_func=Line)
    np.testing.assert_allclose(ends(v), [ax.c2p(2, 0), p], atol=1e-9)
    np.testing.assert_allclose(ends(h), [ax.c2p(0, 1), p], atol=1e-9)
    both = ax.get_lines_to_point(p, line_func=Line)
    assert isinstance(both, mp.HelperGroup)
    assert list(both) == [both.horizontal_line, both.vertical_line]
    np.testing.assert_allclose(ends(both.horizontal_line), ends(h), atol=1e-9)
    np.testing.assert_allclose(ends(both.vertical_line), ends(v), atol=1e-9)


def test_dl3_vertical_lines_to_a_graph_match_manims():
    ours, graph, theirs, twin = pair()
    a = ours.get_vertical_lines_to_graph(
        graph, x_range=(1, 3), num_lines=5, line_func=Line
    )
    b = theirs.get_vertical_lines_to_graph(
        twin, x_range=(1, 3), num_lines=5, line_func=Line
    )
    assert len(a) == len(b) == 5
    for ours_line, their_line in zip(a, b, strict=True):
        np.testing.assert_allclose(
            ends(ours_line), [their_line.get_start(), their_line.get_end()], atol=1e-6
        )


def test_dl3_the_default_range_is_the_systems_and_follows_it():
    ax, graph, _, _ = pair()
    lines = ax.get_vertical_lines_to_graph(graph, line_func=Line)
    assert len(lines) == 20
    bottoms = [float(ax.p2c(ends(line)[0])[0]) for line in lines]
    np.testing.assert_allclose(bottoms, np.linspace(-7, 7, 20), atol=1e-9)
    ax.set_x_range((-3, 3))
    bottoms = [float(ax.p2c(ends(line)[0])[0]) for line in lines]
    np.testing.assert_allclose(bottoms, np.linspace(-3, 3, 20), atol=1e-9)


def test_dl3_no_lines_raises():
    ax, graph, _, _ = pair()
    with pytest.raises(ValueError, match="num_lines"):
        ax.get_vertical_lines_to_graph(graph, num_lines=0)


def test_dl4_axvline_and_axhline_in_viewport_fractions():
    ax, _, _, _ = pair()  # x in (-7, 7), y in (-4, 4)
    np.testing.assert_allclose(
        ends(ax.axvline(1)), [ax.c2p(1, -4), ax.c2p(1, 4)], atol=1e-9
    )
    np.testing.assert_allclose(
        ends(ax.axvline(1, ymin=0.25, ymax=0.75)),
        [ax.c2p(1, -2), ax.c2p(1, 2)],
        atol=1e-9,
    )
    h = ax.axhline(2, xmin=0.5)
    np.testing.assert_allclose(ends(h), [ax.c2p(0, 2), ax.c2p(7, 2)], atol=1e-9)
    assert h.line_style is mp.LineStyle.SOLID
    assert h.get_stroke_width() == 2


# --- TL: the T label ------------------------------------------------------------------


def corners(mob) -> np.ndarray:
    return np.array(
        [mob.get_top(), mob.get_corner([-1, -1, 0]), mob.get_corner([1, -1, 0])]
    )


def test_tl1_parts_in_manims_order_with_names():
    ax, graph, _, _ = pair()
    labelled = ax.get_T_label(2, graph, label="x")
    assert list(labelled) == [labelled.label, labelled.triangle, labelled.line]
    bare = ax.get_T_label(2, graph)
    assert list(bare) == [bare.triangle, bare.line]


def test_tl2_every_part_equals_manims_on_default_axes():
    ours, graph, theirs, twin = pair()
    a = ours.get_T_label(2, graph, label="x")
    b = theirs.get_T_label(x_val=2, graph=twin, label="x")
    their_label, their_triangle, their_line = b
    np.testing.assert_allclose(corners(a.triangle), corners(their_triangle), atol=1e-6)
    np.testing.assert_allclose(
        ends(a.line), [their_line.get_start(), their_line.get_end()], atol=1e-6
    )
    np.testing.assert_allclose(
        a.label.get_center(), their_label.get_center(), atol=1e-6
    )
    assert a.label.width == pytest.approx(their_label.width, abs=1e-6)


def test_tl3_the_triangle_touches_the_axis_when_the_range_excludes_zero():
    ours = mp.Axes(x_range=(1, 5, 1), y_range=(2, 10, 1))
    theirs = Axes(x_range=[1, 5], y_range=[2, 10])
    a = ours.get_T_label(3, ours.plot(lambda x: x + 3))
    b = theirs.get_T_label(3, theirs.plot(lambda x: x + 3))
    assert a.triangle.get_top()[1] == pytest.approx(ours.c2p(3, 2)[1], abs=1e-9)
    assert b[0].get_top()[1] < theirs.x_axis.get_center()[1] - 1  # Manim's defect


# --- TG: slopes and tangents ----------------------------------------------------------


def test_tg1_slope_and_angle_from_the_exact_graph():
    ax = mp.Axes()
    graph = ax.plot(lambda x: x**2)
    assert ax.slope_of_tangent(3, graph) == pytest.approx(6, abs=1e-6)
    assert ax.angle_of_tangent(3, graph) == pytest.approx(np.arctan(6), abs=1e-6)
    theirs = Axes()
    twin = theirs.plot(lambda x: x**2)
    assert ax.angle_of_tangent(1.5, graph) == pytest.approx(
        theirs.angle_of_tangent(1.5, twin), abs=1e-6
    )


def test_tg2_a_tangent_line_is_centred_and_tangent():
    ax, graph, _, _ = pair()
    line = ax.get_tangent_line(1, graph)
    start, end = ends(line)
    assert np.linalg.norm(end - start) == pytest.approx(1, abs=1e-6)
    np.testing.assert_allclose((start + end) / 2, ax.i2gp(1, graph), atol=1e-6)
    h = 1e-4
    chord = direction(ax.i2gp(1 - h, graph), ax.i2gp(1 + h, graph))
    np.testing.assert_allclose(direction(start, end), chord, atol=1e-6)
    longer = ends(ax.get_tangent_line(1, graph, length=3))
    assert np.linalg.norm(longer[1] - longer[0]) == pytest.approx(3, abs=1e-6)


def test_tg2_tangent_on_a_log_scale():
    ax = mp.Axes(x_range=(1, 100, 1), y_range=(0, 12, 1), x_scale="log")
    graph = ax.plot(np.sqrt)
    start, end = ends(ax.get_tangent_line(10, graph))
    h = 1e-4
    chord = direction(ax.i2gp(10 - h, graph), ax.i2gp(10 + h, graph))
    np.testing.assert_allclose(direction(start, end), chord, atol=1e-5)


def test_tg3_a_tangent_vector_starts_on_the_curve():
    ax, graph, _, _ = pair()
    arrow = ax.get_tangent_vector(1, graph)
    assert isinstance(arrow, mp.HelperGroup)
    start = ends(arrow.line)[0]
    np.testing.assert_allclose(start, ax.i2gp(1, graph), atol=1e-6)
    points = np.concatenate([arrow.line.points, arrow.tip.points])
    reach = np.linalg.norm(points - start, axis=1).max()
    assert reach == pytest.approx(1, abs=1e-6)
    tangent = direction(*ends(ax.get_tangent_line(1, graph)))
    far = points[np.argmax(np.linalg.norm(points - start, axis=1))]
    np.testing.assert_allclose(direction(start, far), tangent, atol=1e-6)


def test_tg3_a_callable_length_reads_the_slope():
    ax, graph, _, _ = pair()  # slope 0.5 at x = 1
    arrow = ax.get_tangent_vector(1, graph, length=lambda slope: 0.5 + slope)
    start = ends(arrow.line)[0]
    points = np.concatenate([arrow.line.points, arrow.tip.points])
    assert np.linalg.norm(points - start, axis=1).max() == pytest.approx(1, abs=1e-6)


# --- SC: the secant slope group -------------------------------------------------------


def test_sc1_parts_in_manims_order_with_manims_names():
    ax, graph, _, _ = pair()
    group = ax.get_secant_slope_group(1, graph, dx=1, dx_label="dx", dy_label="dy")
    assert list(group) == [
        group.dx_line,
        group.df_line,
        group.dx_label,
        group.df_label,
        group.secant_line,
    ]
    bare = ax.get_secant_slope_group(1, graph, dx=1, include_secant_line=False)
    assert list(bare) == [bare.dx_line, bare.df_line]


def test_sc2_every_part_equals_manims_on_default_axes():
    ours, graph, theirs, twin = pair()
    a = ours.get_secant_slope_group(1, graph, dx=1.5, dx_label="dx", dy_label="dy")
    b = theirs.get_secant_slope_group(1, twin, dx=1.5, dx_label="dx", dy_label="dy")
    for name in ("dx_line", "df_line", "secant_line"):
        theirs_part = getattr(b, name)
        np.testing.assert_allclose(
            ends(getattr(a, name)),
            [theirs_part.get_start(), theirs_part.get_end()],
            atol=1e-6,
        )
    for name in ("dx_label", "df_label"):
        np.testing.assert_allclose(
            getattr(a, name).get_center(), getattr(b, name).get_center(), atol=1e-6
        )
    assert a.df_line.get_color() == graph.get_color()


def test_sc2_the_legs_follow_rotated_axes():
    ax = mp.Axes().rotate(30 * DEGREES)
    graph = ax.plot(quarter)
    group = ax.get_secant_slope_group(1, graph, dx=1)
    start, end = ends(group.dx_line)
    angle = np.degrees(np.arctan2(end[1] - start[1], end[0] - start[0]))
    assert angle == pytest.approx(30, abs=1e-6)
    np.testing.assert_allclose(end, ax.c2p(2, quarter(1)), atol=1e-6)


def test_sc3_the_default_dx_is_a_tenth_of_the_span():
    ax, graph, _, _ = pair()
    group = ax.get_secant_slope_group(1, graph)
    np.testing.assert_allclose(
        ends(group.dx_line)[1], ax.c2p(2.4, quarter(1)), atol=1e-6
    )


def test_sc3_dx_zero_is_the_tangent():
    ax, graph, _, _ = pair()
    group = ax.get_secant_slope_group(1, graph, dx=0)
    assert collapsed(group.dx_line) and collapsed(group.df_line)
    tangent = direction(*ends(ax.get_tangent_line(1, graph)))
    secant = direction(*ends(group.secant_line))
    np.testing.assert_allclose(np.abs(secant @ tangent), 1, atol=1e-6)
    start, end = ends(group.secant_line)
    assert np.linalg.norm(end - start) == pytest.approx(10, abs=1e-6)


def test_sc3_a_tracker_dx_closes_into_the_tangent():
    ax, graph, _, _ = pair()
    dx = ValueTracker(2.0)
    group = ax.get_secant_slope_group(1, graph, dx=dx)

    def construct(scene: Scene) -> None:
        scene.add(ax, graph, group)
        scene.play(dx.animate.set_value(0), run_time=1)

    run(construct, lambda: None)
    tangent = direction(*ends(ax.get_tangent_line(1, graph)))
    secant = direction(*ends(group.secant_line))
    np.testing.assert_allclose(np.abs(secant @ tangent), 1, atol=1e-6)


def test_sc4_labels_flip_with_the_sign_of_dx_and_can_be_moved():
    ax, graph, _, _ = pair()
    right = ax.get_secant_slope_group(1, graph, dx=1, dx_label="dx")
    left = ax.get_secant_slope_group(1, graph, dx=-1, dx_label="dx")
    assert right.dx_label.get_center()[1] < right.dx_line.get_center()[1]
    assert left.dx_label.get_center()[1] > left.dx_line.get_center()[1]
    moved = ax.get_secant_slope_group(
        1, graph, dx=1, dx_label="dx", dx_label_direction=UP
    )
    assert moved.dx_label.get_center()[1] > moved.dx_line.get_center()[1]


def test_sc4_a_label_shrinks_to_its_leg():
    ax, graph, _, _ = pair()
    group = ax.get_secant_slope_group(1, graph, dx=0.5, dx_label="a long label")
    assert group.dx_label.width <= 0.8 * group.dx_line.width + 1e-9


def test_sc5_the_secant_line_through_both_points():
    ax, graph, _, _ = pair()
    group = ax.get_secant_slope_group(1, graph, dx=2, secant_line_length=4)
    start, end = ends(group.secant_line)
    p1, p2 = ax.i2gp(1, graph), ax.i2gp(3, graph)
    assert np.linalg.norm(end - start) == pytest.approx(4, abs=1e-6)
    np.testing.assert_allclose((start + end) / 2, (p1 + p2) / 2, atol=1e-6)
    np.testing.assert_allclose(direction(start, end), direction(p1, p2), atol=1e-6)


# --- DG: derived graphs ---------------------------------------------------------------


XS = np.linspace(-3, 3, 13)


def values(ax, graph, xs) -> np.ndarray:
    return np.array([ax.i2gc(float(x), graph)[1] for x in xs])


def test_dg1_the_derivative_of_x_squared():
    ax = mp.Axes()
    derivative = ax.plot_derivative_graph(ax.plot(lambda x: x**2))
    assert isinstance(derivative, mp.FunctionPlot)
    assert derivative.get_color() == GREEN
    np.testing.assert_allclose(values(ax, derivative, XS), 2 * XS, atol=1e-6)


def test_dg1_the_derivative_follows_its_parent():
    ax = mp.Axes()
    parent = ax.plot(lambda x, a=1.0: a * x**2)
    derivative = ax.plot_derivative_graph(parent)
    parent.set_parameters(a=2.0)
    np.testing.assert_allclose(values(ax, derivative, XS), 4 * XS, atol=1e-6)


def test_dg2_the_antiderivative_of_cos():
    ax = mp.Axes()
    integral = ax.plot_antiderivative_graph(ax.plot(np.cos))
    np.testing.assert_allclose(values(ax, integral, XS), np.sin(XS), atol=1e-6)
    lifted = ax.plot_antiderivative_graph(ax.plot(np.cos), y_intercept=2, samples=10)
    np.testing.assert_allclose(values(ax, lifted, XS), np.sin(XS) + 2, atol=1e-6)


def test_dg2_outside_zero_the_integral_starts_at_the_range():
    ax = mp.Axes()
    integral = ax.plot_antiderivative_graph(ax.plot(lambda x: 1 / x, x_range=(1, 5)))
    xs = np.linspace(1, 5, 9)
    np.testing.assert_allclose(values(ax, integral, xs), np.log(xs), atol=1e-6)


def test_dg3_the_antiderivative_follows_its_parent():
    ax = mp.Axes()
    parent = ax.plot(lambda x, a=1.0: a * np.cos(x))
    integral = ax.plot_antiderivative_graph(parent)
    parent.set_parameters(a=2.0)
    np.testing.assert_allclose(values(ax, integral, XS), 2 * np.sin(XS), atol=1e-6)
