"""Task 35: 2D helpers, rows AN, SPN, FX, CH, EL, IN of
`docs/acceptance/35-helpers-2d.md`.

The oracles: `c2p`/`p2c` of the axes, the bounding-box exit point written out, the
shoelace area, and the fractions of the parent's box.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import RIGHT, Create, Scene, ValueTracker, linear

import manim_plots as mp

from .helpers import probe


def text_of(mob: Any) -> str:
    return str(getattr(mob, "tex_string", None) or getattr(mob, "text", ""))


def data(ax: Any, points: Any) -> np.ndarray:
    return np.array([ax.p2c(p) for p in np.atleast_2d(np.asarray(points))])


def area(ax: Any, mob: Any) -> float:
    total = 0.0
    for sub in mob.get_subpaths():
        poly = data(ax, np.asarray(sub)[::4])[:, :2]
        x, y = poly[:, 0], poly[:, 1]
        total += abs(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    return total


def axes() -> Any:
    return mp.Axes(x_range=(0, 10, 1), y_range=(0, 10, 1), x_length=6, y_length=6)


# --- AN -------------------------------------------------------------------------------


def test_an1_text_at_xytext_or_offset():
    ax = axes()
    note = ax.annotate("peak", (2, 3), (5, 6))
    assert isinstance(cast(object, note), mp.HelperGroup)
    np.testing.assert_allclose(note.text.get_center(), ax.c2p(5, 6), atol=1e-6)
    assert text_of(note.text) == "peak"
    near = ax.annotate("here", (2, 3))
    np.testing.assert_allclose(
        near.text.get_center(), ax.c2p(2, 3) + np.array([0.6, 0.6, 0]), atol=1e-6
    )
    plain = ax.annotate("x", (1, 1), arrow=False)
    assert plain.arrow is None


def test_an2_arrow_from_the_box_edge_to_the_point():
    ax = axes()
    note = ax.annotate("peak", (2, 3), (5, 6), buff=0.1)
    tip = note.arrow.get_end()
    np.testing.assert_allclose(tip, ax.c2p(2, 3), atol=1e-6)
    c, p = note.text.get_center(), ax.c2p(2, 3)
    d = p - c
    t = min(note.text.width / 2 / abs(d[0]), note.text.height / 2 / abs(d[1]))
    start = c + t * d + 0.1 * d / np.linalg.norm(d)
    np.testing.assert_allclose(note.arrow.get_start(), start, atol=1e-6)


def test_an3_bound_to_ranges_and_trackers():
    ax = axes()
    t = ValueTracker(2)
    note = ax.annotate("p", (t, 3), (5, 6))
    ax.set_x_range((0, 5, 1))
    np.testing.assert_allclose(note.text.get_center(), ax.c2p(5, 6), atol=1e-6)
    np.testing.assert_allclose(note.arrow.get_end(), ax.c2p(2, 3), atol=1e-6)

    def construct(scene: Scene) -> None:
        scene.add(ax, note)
        scene.play(t.animate.set_value(4), rate_func=linear)

    gaps = probe(
        construct,
        lambda: float(np.linalg.norm(note.arrow.get_end() - ax.c2p(t.get_value(), 3))),
    )
    assert max(gaps) < 1e-6


# --- SPN ------------------------------------------------------------------------------


def test_spn1_vertical_and_horizontal_spans():
    ax = axes()
    span = ax.axvspan(2, 4)
    assert isinstance(cast(object, span), mp.FilledRegion)
    d = data(ax, span.points)
    assert (d[:, 0].min(), d[:, 0].max()) == pytest.approx((2, 4), abs=1e-9)
    assert (d[:, 1].min(), d[:, 1].max()) == pytest.approx((0, 10), abs=1e-9)
    assert span.get_fill_opacity() == pytest.approx(0.25)
    assert span.get_stroke_width() == 0
    part = ax.axvspan(2, 4, 0.25, 0.5)
    ax.set_y_range((0, 20, 5))
    d = data(ax, part.points)
    assert (d[:, 1].min(), d[:, 1].max()) == pytest.approx((5, 10), abs=1e-9)
    d = data(ax, span.points)
    assert d[:, 1].max() == pytest.approx(20, abs=1e-9)
    band = ax.axhspan(1, 2)
    d = data(ax, band.points)
    assert (d[:, 1].min(), d[:, 1].max()) == pytest.approx((1, 2), abs=1e-9)
    assert (d[:, 0].min(), d[:, 0].max()) == pytest.approx((0, 10), abs=1e-9)


def test_spn1_cut_to_the_viewport():
    ax = axes()
    span = ax.axvspan(8, 12)
    assert data(ax, span.points)[:, 0].max() == pytest.approx(10, abs=1e-9)


# --- FX -------------------------------------------------------------------------------


def test_fx1_fill_betweenx_is_fill_between_turned():
    ax = axes()
    region = ax.fill_betweenx([0, 1, 2], [1, 2, 1])
    assert isinstance(cast(object, region), mp.FilledRegion)
    assert area(ax, region) == pytest.approx(3, rel=1e-6)
    d = data(ax, region.points)
    assert d[:, 0].max() == pytest.approx(2, abs=1e-9)
    kept = ax.fill_betweenx([0, 1, 2], [1, 2, 1], 0, where=[False, True, True])
    assert area(ax, kept) == pytest.approx(1.5, rel=1e-6)


# --- CH -------------------------------------------------------------------------------


def test_ch1_ch3_crosshair_on_a_graph_follows_a_tracker():
    ax = axes()
    g = ax.plot(lambda x: x**2 / 10)
    t = ValueTracker(2)
    cross = ax.crosshair(t, graph=g)
    assert isinstance(cast(object, cross), mp.HelperGroup)
    np.testing.assert_allclose(cross.dot.get_center(), ax.c2p(2, 0.4), atol=1e-6)
    v = data(ax, cross.vline.points)
    np.testing.assert_allclose(v[:, 0], 2, atol=1e-9)
    assert (v[:, 1].min(), v[:, 1].max()) == pytest.approx((0, 10), abs=1e-9)
    h = data(ax, cross.hline.points)
    np.testing.assert_allclose(h[:, 1], 0.4, atol=1e-9)
    assert cross.vline.get_stroke_opacity() == pytest.approx(0.6)

    def construct(scene: Scene) -> None:
        scene.add(ax, g, cross)
        scene.play(t.animate.set_value(8), rate_func=linear)

    def gap() -> float:
        x = t.get_value()
        return float(np.linalg.norm(cross.dot.get_center() - ax.c2p(x, x**2 / 10)))

    assert max(probe(construct, gap)) < 1e-6


def test_ch2_readout_text_and_placement():
    ax = axes()
    cross = ax.crosshair(2, 0.4)
    assert text_of(cross.readout).replace(" ", "") == "(2.00,0.40)"
    assert cross.readout.get_left()[0] > cross.dot.get_center()[0]
    assert cross.readout.get_bottom()[1] > cross.dot.get_center()[1]
    corner = ax.crosshair(9.9, 9.9)
    right, top = ax.c2p(10, 10)[:2]
    assert corner.readout.get_right()[0] <= right + 1e-6
    assert corner.readout.get_top()[1] <= top + 1e-6
    assert ax.crosshair(1, 1, readout=False).readout is None


# --- EL -------------------------------------------------------------------------------


def test_el1_label_at_the_end_shows_the_value():
    ax = axes()
    g = ax.plot(lambda x: x, x_range=(0, 5))
    label = ax.end_label(g)
    assert text_of(label) == "5.00"
    end = g.points[-1]
    assert label.get_left()[0] == pytest.approx(end[0] + 0.15, abs=1e-6)
    assert label.get_center()[1] == pytest.approx(end[1], abs=1e-6)
    fixed = ax.end_label(g, "f(x)")
    assert text_of(fixed) == "f(x)"


def test_el1_label_follows_create():
    ax = axes()
    g = ax.plot(lambda x: x, x_range=(0, 9))
    label = ax.end_label(g, direction=RIGHT)
    seen: list[tuple[float, str, float]] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, label)
        scene.play(Create(g), rate_func=linear)

    def record() -> None:
        if g.has_points() and np.ptp(g.points[:, 0]) > 1e-6:
            end = g.points[-1]
            seen.append((label.get_left()[0] - end[0], text_of(label), ax.p2c(end)[1]))

    probe(construct, record)
    assert len(seen) > 2
    for gap, text, y in seen:
        assert gap == pytest.approx(0.15, abs=1e-6)
        assert text == f"{y:.2f}"


# --- IN -------------------------------------------------------------------------------


def test_in1_inset_box_in_parent_fractions_and_follows_moves():
    ax = axes()
    ins = ax.inset((0.6, 0.6, 0.3, 0.3), x_range=(2, 3, 0.5), y_range=(2, 3, 0.5))
    assert isinstance(cast(object, ins), mp.InsetAxes)
    assert isinstance(cast(object, ins), mp.CartesianAxes)
    assert ins.parent is ax
    lo, hi = ax.c2p(0, 0), ax.c2p(10, 10)
    np.testing.assert_allclose(ins.c2p(2, 2), lo + 0.6 * (hi - lo), atol=1e-6)
    np.testing.assert_allclose(ins.c2p(3, 3), lo + 0.9 * (hi - lo), atol=1e-6)
    before = ins.c2p(2, 2)
    ax.shift(RIGHT)
    np.testing.assert_allclose(ins.c2p(2, 2), before + RIGHT, atol=1e-6)


def test_in2_zoom_box_follows_both_ranges():
    ax = axes()
    ins = ax.inset((0.6, 0.6, 0.3, 0.3), x_range=(2, 3, 0.5), y_range=(2, 3, 0.5))
    d = data(ax, ins.zoom_box.points)
    assert (d[:, 0].min(), d[:, 0].max()) == pytest.approx((2, 3), abs=1e-9)
    assert (d[:, 1].min(), d[:, 1].max()) == pytest.approx((2, 3), abs=1e-9)
    ins.set_x_range((2, 4, 1))
    d = data(ax, ins.zoom_box.points)
    assert (d[:, 0].min(), d[:, 0].max()) == pytest.approx((2, 4), abs=1e-9)
    ax.set_y_range((0, 20, 5))
    d = data(ax, ins.zoom_box.points)
    assert (d[:, 1].min(), d[:, 1].max()) == pytest.approx((2, 3), abs=1e-9)


def test_in3_two_connectors_join_matching_corners():
    ax = axes()
    ins = ax.inset((0.6, 0.6, 0.3, 0.3), x_range=(2, 3, 0.5), y_range=(2, 3, 0.5))
    assert len(ins.connectors) == 2
    box = np.array([ax.c2p(x, y) for x, y in ((2, 2), (3, 2), (3, 3), (2, 3))])
    inner = np.array([ins.c2p(x, y) for x, y in ((2, 2), (3, 2), (3, 3), (2, 3))])
    for line in ins.connectors:
        a, b = line.get_start(), line.get_end()
        i = int(np.argmin(np.linalg.norm(box - a, axis=1)))
        j = int(np.argmin(np.linalg.norm(inner - b, axis=1)))
        np.testing.assert_allclose(a, box[i], atol=1e-6)
        np.testing.assert_allclose(b, inner[j], atol=1e-6)
        assert i == j  # the same corner of both rectangles
        mid = (a + b) / 2
        for rect in (box, inner):
            inside = (
                rect[0][0] < mid[0] < rect[2][0] and rect[0][1] < mid[1] < rect[2][1]
            )
            assert not inside
    bare = ax.inset((0.1, 0.6, 0.3, 0.3), (5, 6, 1), (5, 6, 1), connectors=False)
    assert len(bare.connectors) == 0


def test_in4_mirrored_artists():
    ax = axes()
    g = ax.plot(np.sin, color="#ff0000")
    dots = ax.scatter([2.2, 2.8], [2.5, 2.6])
    ins = ax.inset((0.6, 0.6, 0.3, 0.3), (2, 3, 0.5), (-1, 3, 1), mirror=[g, dots])
    curve, marks = ins.mirrored
    assert isinstance(cast(object, curve), mp.FunctionPlot)
    assert curve.get_color() == g.get_color()
    pts = data(ins, curve.points)
    np.testing.assert_allclose(pts[:, 1], np.sin(pts[:, 0]), atol=1e-3)
    assert (pts[:, 0].min(), pts[:, 0].max()) == pytest.approx((2, 3), abs=1e-6)
    np.testing.assert_allclose(marks[0].get_center(), ins.c2p(2.2, 2.5), atol=1e-6)
    with pytest.raises(TypeError, match="FilledRegion"):
        ax.inset((0.1, 0.1, 0.2, 0.2), (0, 1, 1), (0, 1, 1), mirror=[ax.axvspan(1, 2)])
