"""The library's own animations: `DrawAxes`, `TraceCurve`, `ShowPoints`, `Morph`
(F-710, F-912).

Rows AN-1 to AN-5 of `docs/acceptance/12-legend-style-animations.md`. `DrawAxes` has a
Manim oracle (plain twins under `Create`); the others are checked against the data:
where the drawn part ends, which markers show, the arc-length correspondence.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from manim import RIGHT, UP, Create, Scene, VGroup, linear, smooth

import manim_plots as mp

from .helpers import along, plain, probe

FPS = 6


def axes():
    return mp.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)


def visible(ax):
    return [m for m in ax.family_members_with_points() if m is not ax.frame]


# --- AN-1 ----------------------------------------------------------------------------


def test_an1_draw_axes_is_create_without_the_frames_slot():
    ax = axes()
    curve = ax.plot(np.sin)
    curve_before = np.array(curve.points, copy=True)
    twins = VGroup(*[plain(m) for m in visible(ax)])

    def construct(scene: Scene) -> None:
        scene.add(curve)
        scene.play(mp.DrawAxes(ax), Create(twins))

    def record():
        return [np.array(m.points, copy=True) for m in visible(ax)], [
            np.array(t.points, copy=True) for t in twins
        ]

    frames = probe(construct, record)
    assert len(frames) >= 5
    for ours, theirs in frames:
        assert len(ours) == len(theirs)
        for a, b in zip(ours, theirs, strict=True):
            np.testing.assert_allclose(a, b, atol=1e-9)
    for leaf, twin in zip(visible(ax), twins, strict=True):
        np.testing.assert_allclose(leaf.points, twin.points, atol=1e-9)
    np.testing.assert_allclose(curve.points, curve_before, atol=1e-12)


# --- AN-2 ----------------------------------------------------------------------------


def drawn_x(ax, curve) -> tuple[float, float]:
    if not curve.has_points():
        return (np.nan, np.nan)
    xs = np.array([ax.p2c(p)[0] for p in curve.points])
    return float(xs.min()), float(xs.max())


def spacing(ax, curve) -> float:
    anchors = np.asarray(curve.points)[::4]
    xs = np.sort([ax.p2c(p)[0] for p in anchors])
    return float(np.diff(xs).max())


@pytest.mark.parametrize("reverse", [False, True], ids=["as sampled", "reversed"])
def test_an2_trace_curve_reveals_in_data_order(reverse):
    ax = axes()
    curve = ax.plot(lambda x: np.tanh(8 * x))  # dense samples near 0
    if reverse:
        curve.reverse_points()
    tol = spacing(ax, curve)
    full = np.array(curve.points, copy=True)

    def construct(scene: Scene) -> None:
        scene.add(ax, curve)
        scene.play(mp.TraceCurve(curve, rate_func=linear), run_time=1)

    frames = probe(construct, lambda: drawn_x(ax, curve))
    for k, (lo, hi) in enumerate(frames[1:], start=1):
        assert lo == pytest.approx(-3, abs=tol)
        assert hi == pytest.approx(-3 + 6 * k / FPS, abs=tol), (k, hi)
    np.testing.assert_allclose(curve.points, full, atol=1e-9)
    before = np.array(curve.points, copy=True)
    ax.x.range = (-2, 2)
    assert not np.array_equal(curve.points, before)


def test_an2_a_line_is_traced_in_data_index_order():
    ax = axes()
    xs = np.array([2.0, 1.0, 0.0, -1.0, -2.0])
    line = ax.line(xs, np.zeros_like(xs))

    def construct(scene: Scene) -> None:
        scene.add(ax, line)
        scene.play(mp.TraceCurve(line, rate_func=linear), run_time=1)

    frames = probe(construct, lambda: drawn_x(ax, line))
    for k, (lo, hi) in enumerate(frames[1:], start=1):
        assert hi == pytest.approx(2, abs=1e-6)
        assert lo == pytest.approx(2 - 4 * k / FPS, abs=1e-6)


# --- AN-3 ----------------------------------------------------------------------------


def test_an3_show_points_reveals_markers_in_data_order():
    ax = axes()
    scatter = ax.scatter([-2, -1, 10, 1, 2], [0, 1, 0, -1, 0])  # the third is outside

    def construct(scene: Scene) -> None:
        scene.add(ax, scatter)
        scene.play(mp.ShowPoints(scatter), run_time=1)

    frames = probe(
        construct, lambda: [float(m.get_fill_opacity()) for m in scatter.submobjects]
    )
    assert frames[0] == [0.0] * 5
    valid = [0, 1, 3, 4]
    for opacities in frames:
        assert opacities[2] == 0
        seq = [opacities[i] for i in valid]
        assert all(a >= b - 1e-9 for a, b in itertools.pairwise(seq)), seq
    end = [float(m.get_fill_opacity()) for m in scatter.submobjects]
    assert [end[i] for i in valid] == [1.0] * 4 and end[2] == 0


# --- AN-4, AN-5 ---------------------------------------------------------------------


def arc_param(points: np.ndarray, per_curve: int = 256):
    """Points along a path at arc fractions: a function of an array of fractions."""
    pts = along(points, per_curve)
    steps = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(steps)]) / steps.sum()

    def at(s: np.ndarray) -> np.ndarray:
        return np.stack([np.interp(s, cum, pts[:, k]) for k in range(3)], axis=1)

    return at, cum


def anchor_fractions(points: np.ndarray) -> np.ndarray:
    anchors = np.vstack([points[::4], points[-1:]])
    steps = []
    curves = points.reshape(-1, 4, 3)
    for curve in curves:
        d = along(curve.reshape(-1, 3), 256)
        steps.append(np.linalg.norm(np.diff(d, axis=0), axis=1).sum())
    cum = np.concatenate([[0.0], np.cumsum(steps)])
    assert len(cum) == len(anchors)
    return np.asarray(cum / cum[-1])


def test_an4_morph_resamples_by_arc_length_without_inserted_points():
    a_ax, b_ax = axes(), axes().shift(0.5 * UP)
    a = a_ax.line([-3, -1, 0, 1, 3], [0, 1, -1, 1, 0])
    xs = np.linspace(-3, 3, 50)
    b = b_ax.line(xs, np.sin(xs))
    a_path, b_path = np.array(a.points, copy=True), np.array(b.points, copy=True)
    a_at, _ = arc_param(a_path)
    b_at, _ = arc_param(b_path)
    # Both paths resampled at the union of their anchors' arc fractions.
    union = np.r_[anchor_fractions(a_path), anchor_fractions(b_path)]
    s = np.unique(np.round(union, 9))

    def construct(scene: Scene) -> None:
        scene.add(a_ax, b_ax, a, b)
        scene.play(mp.Morph(a, b), run_time=1)

    frames = probe(construct, lambda: np.array(a.points, copy=True))
    for k, points in enumerate(frames):
        assert len(points) == 4 * (len(s) - 1)
        anchors = np.vstack([points[::4], points[-1:]])
        assert (np.linalg.norm(np.diff(anchors, axis=0), axis=1) > 1e-9).all()
        alpha = smooth(k / FPS)
        expected = (1 - alpha) * a_at(s) + alpha * b_at(s)
        np.testing.assert_allclose(anchors, expected, atol=1e-3)
    # The first frame keeps a's corners: it traces a's path.
    np.testing.assert_allclose(frames[0][::4], a_at(s)[:-1], atol=1e-6)
    np.testing.assert_allclose(a.points, b.points, atol=1e-6)
    np.testing.assert_allclose(b.points, b_path, atol=1e-12)
    before = np.array(a.points, copy=True)
    b_ax.shift(RIGHT)
    np.testing.assert_allclose(a.points, before + RIGHT, atol=1e-9)
    moved = np.array(a.points, copy=True)
    a_ax.shift(UP)
    np.testing.assert_allclose(a.points, moved, atol=1e-12)


def test_an5_morph_refuses_a_scatter_and_a_line():
    ax = axes()
    with pytest.raises(ValueError):
        mp.Morph(ax.scatter([0, 1], [0, 1]), ax.line([0, 1], [0, 1]))


def test_an5_morph_refuses_paths_of_different_piece_counts():
    ax = mp.Axes(x_range=(-1, 10, 1), y_range=(-2, 2, 0.5))
    with pytest.warns(mp.ManimPlotsWarning):
        split = ax.plot(lambda x: 1 / (x - 4.5))
    with pytest.raises(ValueError):
        mp.Morph(split, ax.plot(np.sin))
