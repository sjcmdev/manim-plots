"""Task 42 chart-family oracles; deliberately red before implementation."""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from typing import Any, cast

import numpy as np
import pytest
from manim import (
    RED,
    Animation,
    LaggedStart,
    Scene,
    VGroup,
    linear,
    tempconfig,
    there_and_back,
)

import manim_plots as mp

from ..mobjects.helpers import RUN, probe

API = cast(Any, mp)
FAMILIES = (
    "GrowBars",
    "GrowStack",
    "RevealCells",
    "RevealContours",
    "SweepPie",
    "GrowBoxPlot",
    "UnfoldViolin",
)


def axes():
    return mp.Axes(x_range=(-2, 12, 2), y_range=(-12, 40, 4))


def anchors(ax, part):
    pts = np.asarray(part.points)
    assert len(pts), "expected drawable geometry"
    return np.array([ax.p2c(p)[:2] for p in np.vstack((pts[::4], pts[-1:]))])


def bounds(ax, part):
    pts = anchors(ax, part)
    return np.array(
        [pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max()]
    )


def progress(alpha, rank, count, lag):
    # Independent statement of the accepted per-part schedule, with linear easing.
    return float(np.clip(alpha * (1 + (count - 1) * lag) - rank * lag, 0, 1))


def frames(scene, artist, animation):
    scene.add(artist)
    scene.play(animation)


def factory(name):
    ax: Any = axes()
    if name == "GrowBars":
        artist = ax.bar([1, 3], [4, -3], bottom=2)
    elif name == "GrowStack":
        artist = ax.stackplot([0, 2, 4], [2, 3, 2], [1, 2, 1])
    elif name == "RevealCells":
        artist = ax.imshow([[1, 2], [3, 4]], extent=(0, 4, 0, 4))
    elif name == "RevealContours":
        artist = ax.contourf(
            [0, 2, 4], [0, 2, 4], [[0, 1, 2], [1, 2, 3], [2, 3, 4]], levels=[0, 2, 4]
        )
    elif name == "SweepPie":
        artist = mp.PieChart([1, 0, 3], radius=1)
    elif name == "GrowBoxPlot":
        artist = ax.boxplot([1, 2, 3, 4, 5, 6, 7, 8, 9, 30], showmeans=True)
    else:
        assert name == "UnfoldViolin"
        artist = ax.violinplot([1, 2, 3, 4, 6], points=9, showmedians=True)
    return ax, artist


def snapshot(artist):
    return [
        (m, np.array(m.points, copy=True), deepcopy(m.get_style()), tuple(m.updaters))
        for m in artist.family_members_with_points()
    ]


def assert_restored(saved):
    for part, points, style, updaters in saved:
        np.testing.assert_allclose(part.points, points, atol=1e-8)
        np.testing.assert_equal(part.get_style(), style)
        assert tuple(part.updaters) == updaters


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("order,ranks", [("data", [0, 1, 2]), ("height", [2, 0, 1])])
def test_gb1_signed_nonzero_bottom_order(horizontal, order, ranks):
    ax: Any = axes()
    bars = (ax.barh if horizontal else ax.bar)(
        [1, 3, 5],
        [6, -2, 3],
        **({"left": 2} if horizontal else {"bottom": 2}),
        c="height",
        vmin=-2,
        vmax=6,
    )
    colors = [b.get_fill_color() for b in bars]
    ids = [id(b) for b in bars]
    anim = API.GrowBars(bars, order=order, lag_ratio=0.5, rate_func=linear)
    seen = probe(lambda s: frames(s, bars, anim), lambda: [bounds(ax, b) for b in bars])
    assert [b.get_fill_color() for b in bars] == colors
    for frame, boxes in enumerate(seen):
        for i, (h, rank) in enumerate(zip([6, -2, 3], ranks, strict=True)):
            p = progress(frame / 6, rank, 3, 0.5)
            end = 2 + p * h
            expected = [min(2, end), max(2, end)]
            b = boxes[i]
            np.testing.assert_allclose(
                b[:2] if horizontal else b[2:], expected, atol=1e-8
            )
            np.testing.assert_allclose(
                b[2:] if horizontal else b[:2],
                [1 + 2 * i - 0.4, 1 + 2 * i + 0.4],
                atol=1e-8,
            )
    assert [id(b) for b in bars] == ids
    assert [b.get_fill_color() for b in bars] == colors


def test_gb2_callable_stable_ties():
    ax = axes()
    bars = ax.bar([1, 3, 5], [4, 4, 2])
    anim = API.GrowBars(
        bars,
        order=lambda bar: -bar.parameters["height"].value,
        lag_ratio=1,
        rate_func=linear,
    )
    seen = probe(
        lambda s: frames(s, bars, anim), lambda: [bounds(ax, b)[3] for b in bars]
    )
    assert seen[2] == pytest.approx([4, 0, 0])
    assert seen[4] == pytest.approx([4, 4, 0])
    assert [b.parameters["height"].value for b in bars] == [4, 4, 2]


def test_gb3_grouped_bars_use_existing_growbars():
    ax = axes()
    group = ax.grouped_bar([[2, 4], [3, 1]])
    anim = LaggedStart(
        *[
            API.GrowBars(series, order="data", lag_ratio=0, rate_func=linear)
            for series in group.bar_plots
        ],
        lag_ratio=0,
        run_time=1,
        rate_func=linear,
    )
    seen = probe(
        lambda s: frames(s, group, anim),
        lambda: [[bounds(ax, b)[3] for b in series] for series in group.bar_plots],
    )
    np.testing.assert_allclose(seen[3], np.array([[1, 2], [1.5, 0.5]]), atol=1e-8)
    np.testing.assert_allclose(
        [[bounds(ax, b)[3] for b in series] for series in group.bar_plots],
        [[2, 4], [3, 1]],
    )


def test_gb4_step_histogram_grows_counts_not_trace_length():
    ax = axes()
    hist: Any = ax.hist([0.2, 0.4, 1.2], bins=[0, 1, 2], histtype="step", bottom=2)
    anim = API.GrowBars(hist, order="data", lag_ratio=0, rate_func=linear)
    seen = probe(lambda s: frames(s, hist, anim), lambda: anchors(ax, hist.outlines[0]))
    for i, pts in enumerate(seen):
        expected = np.array(
            [
                [0, 2],
                [0, 2 + 2 * i / 6],
                [1, 2 + 2 * i / 6],
                [1, 2 + i / 6],
                [2, 2 + i / 6],
                [2, 2],
            ]
        )
        for point in expected:
            assert np.min(np.linalg.norm(pts - point, axis=1)) < 1e-8
    np.testing.assert_array_equal(hist.counts, [2, 1])
    assert bounds(ax, hist.outlines[0])[3] == pytest.approx(4)


@pytest.mark.parametrize("baseline", ["zero", "sym"])
def test_gs1_stackplot_uses_animated_support(baseline):
    ax = axes()
    stack = ax.stackplot([0, 2, 4], [2, 2, 2], [4, 4, 4], baseline=baseline)
    anim = API.GrowStack(stack, lag_ratio=0.5, rate_func=linear)
    seen = probe(
        lambda s: frames(s, stack, anim),
        lambda: [bounds(ax, region)[2:] for region in stack.regions],
    )
    base = -3 if baseline == "sym" else 0
    for i, b in enumerate(seen):
        p0, p1 = (progress(i / 6, j, 2, 0.5) for j in range(2))
        np.testing.assert_allclose(
            b,
            [[base, base + 2 * p0], [base + 2 * p0, base + 2 * p0 + 4 * p1]],
            atol=1e-8,
        )


def test_gs2_signed_bar_layers_keep_separate_support():
    ax = axes()
    first = ax.bar([1, 3], [4, -2])
    second = ax.bar([1, 3], [3, -5], bottom=[4, -2])
    opposite = ax.bar([1, 3], [-1, 2])
    layers = VGroup(first, second, opposite)
    anim = API.GrowStack(layers, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, layers, anim),
        lambda: [[bounds(ax, b)[2:] for b in layer] for layer in layers],
    )
    np.testing.assert_allclose(
        seen[3],
        np.array([[[0, 2], [-1, 0]], [[2, 3.5], [-3.5, -1]], [[-0.5, 0], [0, 1]]]),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        [bounds(ax, b)[2:] for b in second], [[4, 7], [-7, -2]], atol=1e-12
    )


def test_gs3_stacked_histogram_numpy_counts():
    ax = axes()
    hist: Any = ax.hist(
        [[0.2, 0.3, 1.2], [0.1, 1.1, 1.2]], bins=[0, 1, 2], stacked=True
    )
    anim = API.GrowStack(hist, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, hist, anim),
        lambda: [[bounds(ax, b)[2:] for b in layer] for layer in hist.bars],
    )
    np.testing.assert_allclose(
        seen[3], np.array([[[0, 1], [0, 0.5]], [[1, 1.5], [0.5, 1.5]]]), atol=1e-12
    )
    np.testing.assert_allclose(
        [bounds(ax, b)[3] for b in hist.bars[1]], [3, 3], atol=1e-12
    )


@pytest.mark.parametrize(
    "order,ranks",
    [
        ("row", [0, 1, 2, 3, 4, 5]),
        ("column", [0, 2, 4, 1, 3, 5]),
        ("diagonal", [0, 1, 3, 2, 4, 5]),
        ("value", [4, 0, 2, 1, 3, 5]),
        (lambda key, value: -value, [1, 5, 2, 4, 3, 0]),
    ],
)
def test_rc1_cell_order_opacity_and_annotations(order, ranks):
    ax = axes()
    heat = ax.imshow([[4, 1, 3], [2, 3, 5]], extent=(0, 6, 0, 4), fill_opacity=0.4)
    labels = heat.label_cells()
    cells = [heat.cells.at(k) for k in np.ndindex(2, 3)]
    colors = [c.get_fill_color() for c in cells]
    anim = API.RevealCells(
        heat, order=order, lag_ratio=0.5, run_time=7 / 6, rate_func=linear
    )
    seen = probe(
        lambda s: frames(s, heat, anim),
        lambda: (
            [c.get_fill_opacity() for c in cells],
            [label.get_fill_opacity() for label in labels],
        ),
    )
    for i, (opacity, text_opacity) in enumerate(seen):
        p = [progress(i / 7, rank, 6, 0.5) for rank in ranks]
        np.testing.assert_allclose(opacity, np.array(p) * 0.4, atol=1e-8)
        np.testing.assert_allclose(text_opacity, p, atol=1e-8)
    assert [c.get_fill_color() for c in cells] == colors
    assert [c.get_fill_opacity() for c in cells] == pytest.approx([0.4] * 6)


def test_rc2_invalid_cells_stay_empty():
    ax = axes()
    heat = ax.imshow([[1, np.nan], [2, 3]], extent=(0, 4, 0, 4))
    anim = API.RevealCells(heat, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, heat, anim), lambda: heat.cells.at((0, 1)).has_points()
    )
    assert not any(seen)
    assert not heat.cells.at((0, 1)).has_points()


def test_ct1_filled_bands_fade_without_geometry_changes():
    _ax, contour = factory("RevealContours")
    bands = [contour.at(i) for i in range(2)]
    before = [np.array(b.points, copy=True) for b in bands]
    anim = API.RevealContours(contour, order="level", lag_ratio=1, rate_func=linear)
    seen = probe(
        lambda s: frames(s, contour, anim),
        lambda: [(np.array(b.points, copy=True), b.get_fill_opacity()) for b in bands],
    )
    for i, frame in enumerate(seen):
        for j, (points, opacity) in enumerate(frame):
            np.testing.assert_allclose(points, before[j], atol=1e-8)
            assert opacity == pytest.approx(progress(i / 6, j, 2, 1))


@pytest.mark.parametrize("clockwise", [False, True])
@pytest.mark.parametrize("lag", [0, 1])
def test_ps1_unequal_clockwise_zero_and_partial_pies(clockwise, lag):
    pie = mp.PieChart(
        [0.2, 0, 0.4],
        normalize=False,
        startangle=30,
        counterclock=not clockwise,
        labels=["a", "zero", "c"],
    )
    anim = API.SweepPie(pie, lag_ratio=lag, rate_func=linear)
    seen = probe(
        lambda s: frames(s, pie, anim),
        lambda: [(w.start_angle, w.angle) for w in pie.wedges],
    )
    shares = np.array([0.2, 0, 0.4])
    sign = -1 if clockwise else 1
    for i, frame in enumerate(seen):
        for j, (start, angle) in enumerate(frame):
            fraction = (
                np.clip(i / 6 * shares.sum() - shares[:j].sum(), 0, shares[j])
                if lag == 0
                else shares[j] * progress(i / 6, j, 3, lag)
            )
            assert start == pytest.approx(
                np.pi / 6 + sign * 2 * np.pi * shares[:j].sum()
            )
            assert angle == pytest.approx(sign * 2 * np.pi * fraction)
            wedge = pie.wedges[j]
            pts = np.asarray(wedge.points)
            if fraction > 0:
                arc = np.vstack((pts[::4], pts[-1:]))
                for theta in (start, start + angle):
                    endpoint = pie.radius * np.array([np.cos(theta), np.sin(theta), 0])
                    assert np.min(np.linalg.norm(arc - endpoint, axis=1)) < 1e-7
                radius = np.linalg.norm(arc[:, :2], axis=1)
                assert radius.max() <= pie.radius + 1e-7
    np.testing.assert_allclose(pie.fractions, shares)
    assert pie.wedges[2].angle == pytest.approx(sign * 0.8 * np.pi)


def test_pe1_explode_is_restoring_emphasis_on_selected_wedges():
    pie = mp.PieChart([1, 3], radius=2, explode=[0.1, 0.2], labels=["a", "b"])
    saved = snapshot(pie)
    original = [np.array(w.points, copy=True) for w in pie.wedges]
    assert pie.texts is not None
    label_points = [
        np.array(t.points, copy=True) for t in pie.texts.family_members_with_points()
    ]
    anim = API.ExplodePie(pie, indices=[0], amount=0.3)

    def construct(scene: Scene):
        frames(scene, pie, anim)
        assert pie in scene.mobjects

    seen = probe(
        construct,
        lambda: [np.array(w.points, copy=True) for w in pie.wedges],
    )
    for i, frame in enumerate(seen):
        offset = 0.6 * there_and_back(i / 6) * np.array([np.sqrt(0.5), np.sqrt(0.5), 0])
        np.testing.assert_allclose(frame[0], original[0] + offset, atol=1e-8)
        np.testing.assert_allclose(frame[1], original[1], atol=1e-8)
    assert_restored(saved)
    for part, points in zip(
        pie.texts.family_members_with_points(), label_points, strict=True
    ):
        np.testing.assert_allclose(part.points, points, atol=1e-8)


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("sample", [[1, 2, 3, 4, 5, 6, 7, 8, 9, 30], [4, 4, 4, 4]])
def test_bx1_box_grows_from_median_with_staged_whiskers(horizontal, sample):
    ax = axes()
    box = ax.boxplot(
        sample, orientation="horizontal" if horizontal else "vertical", showmeans=True
    )
    anim = API.GrowBoxPlot(box, lag_ratio=0, rate_func=linear)
    seen = probe(lambda s: frames(s, box, anim), lambda: bounds(ax, box.boxes[0]))
    q1, med, q3 = np.percentile(sample, [25, 50, 75])
    for i, b in enumerate(seen):
        p = min(2 * i / 6, 1)
        np.testing.assert_allclose(
            b[:2] if horizontal else b[2:],
            [med + p * (q1 - med), med + p * (q3 - med)],
            atol=1e-8,
        )
    assert len(box.means) == 1
    np.testing.assert_allclose(box.stats[0]["med"], med)


@pytest.mark.parametrize("horizontal", [False, True])
def test_vn1_density_width_unfolds_without_resampling(horizontal):
    ax = axes()
    sample = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
    grid = np.linspace(1, 6, 9)
    bw = len(sample) ** (-0.2) * np.std(sample, ddof=1)
    density = np.exp(-0.5 * ((grid[:, None] - sample) / bw) ** 2).mean(axis=1)
    half = 0.25 * density / density.max()
    violin = ax.violinplot(
        sample, points=9, orientation="horizontal" if horizontal else "vertical"
    )
    anim = API.UnfoldViolin(violin, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, violin, anim), lambda: anchors(ax, violin.bodies[0])
    )
    for i, pts in enumerate(seen):
        if horizontal:
            pts = pts[:, ::-1]
        for y, width in zip(grid, half, strict=True):
            for sign in (-1, 1):
                target = [1 + sign * min(2 * i / 6, 1) * width, y]
                assert np.min(np.linalg.norm(pts - target, axis=1)) < 1e-6


@pytest.mark.parametrize("name", FAMILIES)
def test_lc1_exit_reintroduction_and_explicit_remover(name):
    cls = getattr(API, name)
    ax, artist = factory(name)
    saved = snapshot(artist)

    def own_updater(m, dt):
        pass

    artist.add_updater(own_updater)

    def construct(scene: Scene):
        scene.add(ax, artist)
        scene.play(cls(artist, reverse=True, rate_func=linear))
        assert artist not in scene.mobjects
        assert_restored(saved)
        assert own_updater in artist.updaters
        scene.play(cls(artist, rate_func=linear))
        assert artist in scene.mobjects
        scene.play(cls(artist, reverse=True, remover=False, rate_func=linear))
        assert artist in scene.mobjects
        assert_restored(saved)
        scene.play(cls(artist, remover=True, rate_func=linear))
        assert artist not in scene.mobjects

    probe(construct, lambda: None)
    assert_restored(saved)
    assert artist.updaters == [own_updater]


@pytest.mark.parametrize("name", FAMILIES)
def test_lc2_finish_rederives_after_range_and_preserves_styles(name):
    cls = getattr(API, name)
    ax, artist = factory(name)
    part = artist.family_members_with_points()[0]
    part.set_stroke(RED, width=7)
    saved = snapshot(artist)

    def construct(scene: Scene):
        scene.add(ax)
        scene.play(cls(artist, order="data") if name == "GrowBars" else cls(artist))

    probe(construct, lambda: None)
    assert_restored(saved)
    if name == "SweepPie":
        artist.set_data([2, 0, 2])
        assert artist.wedges[0].angle == pytest.approx(np.pi)
    else:
        parts = (
            artist.boxes + artist.medians + artist.whiskers + artist.caps
            if name == "GrowBoxPlot"
            else artist.family_members_with_points()
        )
        before = [(m, anchors(ax, m)) for m in parts]
        markers = (
            [
                (m, ax.p2c(m.get_center())[:2])
                for group in artist.means + artist.fliers
                for m in group
            ]
            if name == "GrowBoxPlot"
            else []
        )
        ax.set_x_range((-4, 16, 2))
        ax.set_y_range((-16, 44, 4))
        for m, data in before:
            np.testing.assert_allclose(anchors(ax, m), data, atol=1e-7)
        for marker, centre in markers:
            np.testing.assert_allclose(
                ax.p2c(marker.get_center())[:2], centre, atol=1e-7
            )
    assert part.get_stroke_width() == 7


@pytest.mark.parametrize("name", FAMILIES)
def test_lc3_repeated_alpha_does_not_accumulate(name):
    cls = getattr(API, name)
    _, artist = factory(name)
    anim = cls(
        artist,
        rate_func=there_and_back,
        lag_ratio=0,
        **({"order": "data"} if name == "GrowBars" else {}),
    )
    anim.begin()
    anim.interpolate(0.35)
    first = [np.array(m.points, copy=True) for m in artist.family_members_with_points()]
    opacity = [m.get_fill_opacity() for m in artist.family_members_with_points()]
    anim.interpolate(0.65)
    mirrored = [
        np.array(m.points, copy=True) for m in artist.family_members_with_points()
    ]
    for points, other in zip(first, mirrored, strict=True):
        np.testing.assert_allclose(points, other, atol=1e-8)
    anim.interpolate(0.8)
    anim.interpolate(0.35)
    parts = artist.family_members_with_points()
    assert len(parts) == len(first)
    for m, points, fill in zip(parts, first, opacity, strict=True):
        np.testing.assert_allclose(m.points, points, atol=1e-8)
        assert m.get_fill_opacity() == pytest.approx(fill)
    anim.finish()


@pytest.mark.parametrize("name", FAMILIES)
def test_lc4_public_animation_class_and_package_exports(name):
    cls = getattr(API, name)
    _, artist = factory(name)
    cls(artist, reverse=False)
    package = import_module("manim_plots.animations")
    assert getattr(package, name) is cls
    module = (
        "statistics" if name in ("SweepPie", "GrowBoxPlot", "UnfoldViolin") else "bars"
    )
    assert getattr(import_module(f"manim_plots.animations.{module}"), name) is cls
    _, artist = factory(name)
    assert isinstance(cast(object, cls(artist, reverse=False)), Animation)


def test_pe2_explode_export_and_nondefault_easing_restores():
    cls = API.ExplodePie
    assert import_module("manim_plots.animations.statistics").ExplodePie is cls
    assert import_module("manim_plots.animations").ExplodePie is cls
    pie = mp.PieChart([1, 2])
    saved = snapshot(pie)
    probe(lambda s: frames(s, pie, cls(pie, rate_func=linear)), lambda: None)
    assert_restored(saved)


@pytest.mark.parametrize(
    "name",
    [
        "GrowBars",
        "GrowStack",
        "RevealCells",
        "RevealContours",
        "GrowBoxPlot",
        "UnfoldViolin",
    ],
)
def test_mv1_concurrent_range_uses_current_mapping(name):
    cls = getattr(API, name)
    ax, artist = factory(name)
    seen = []

    def construct(scene: Scene):
        scene.add(ax, artist)
        scene.play(
            cls(
                artist,
                rate_func=linear,
                lag_ratio=0,
                **({"order": "data"} if name == "GrowBars" else {}),
            ),
            ax.animate(rate_func=linear).set_x_range((-4, 16, 2)),
        )

    def record():
        seen.append(float(ax.x_range[1]))
        assert_factory_frame(name, ax, artist, (len(seen) - 1) / 6)
        # Full-height coordinate is unaffected by the concurrent x mapping.
        if name == "GrowBars":
            assert bounds(ax, artist[0])[0] == pytest.approx(0.6, abs=1e-7)

    probe(construct, record)
    assert seen[0] == pytest.approx(12)
    assert seen[3] == pytest.approx(14)
    assert ax.x_range[1] == pytest.approx(16)


def test_mv2_tracker_growth_keeps_binding_and_unrelated_function_static():
    from manim import ValueTracker

    ax = axes()
    height = ValueTracker(4)
    bars = ax.bar([1], [height], bottom=2)
    count = 0

    def function(x):
        nonlocal count
        count += 1
        return x

    still_ax = axes()
    still = still_ax.plot(function)
    _ = still.points
    before = count
    anim = API.GrowBars(bars, order="data", lag_ratio=0, rate_func=linear)
    seen = []

    def construct(scene: Scene):
        scene.add(ax, bars, still_ax, still)
        scene.play(anim, cast(Any, height.animate)(rate_func=linear).set_value(8))

    probe(construct, lambda: seen.append(bounds(ax, bars[0])[3]))
    np.testing.assert_allclose(seen, [2 + (i / 6) * (4 + 4 * i / 6) for i in range(6)])
    assert count == before
    height.set_value(6)
    bars.update(0)
    assert bounds(ax, bars[0])[3] == pytest.approx(8)


def assert_factory_frame(name, ax, artist, alpha, lag=0):
    """Numerical oracles for the small fixtures, independent of the animations."""
    if name == "GrowBars":
        for j, h in enumerate((4, -3)):
            end = 2 + h * progress(alpha, j, 2, lag)
            np.testing.assert_allclose(
                bounds(ax, artist[j])[2:], sorted((2, end)), atol=1e-7
            )
    elif name == "GrowStack":
        p0, p1 = (progress(alpha, j, 2, lag) for j in range(2))
        np.testing.assert_allclose(
            bounds(ax, artist.regions[0])[2:], [0, 3 * p0], atol=1e-7
        )
        np.testing.assert_allclose(
            bounds(ax, artist.regions[1])[2:], [2 * p0, 3 * p0 + 2 * p1], atol=1e-7
        )
    elif name == "RevealCells":
        for j, key in enumerate(np.ndindex(2, 2)):
            assert artist.cells.at(key).get_fill_opacity() == pytest.approx(
                progress(alpha, j, 4, lag), abs=1e-7
            )
    elif name == "RevealContours":
        for j in range(2):
            assert artist.at(j).get_fill_opacity() == pytest.approx(
                progress(alpha, j, 2, lag), abs=1e-7
            )
    elif name == "SweepPie":
        shares = [0.25, 0, 0.75]
        for j, share in enumerate(shares):
            revealed = (
                np.clip(alpha - sum(shares[:j]), 0, share)
                if lag == 0
                else share * progress(alpha, j, 3, lag)
            )
            assert artist.wedges[j].angle == pytest.approx(
                2 * np.pi * revealed, abs=1e-7
            )
    elif name == "GrowBoxPlot":
        p = min(2 * alpha, 1)
        np.testing.assert_allclose(
            bounds(ax, artist.boxes[0])[2:], [5.5 - 2.25 * p, 5.5 + 2.25 * p], atol=1e-7
        )
    else:
        assert name == "UnfoldViolin"
        p = min(2 * alpha, 1)
        np.testing.assert_allclose(
            bounds(ax, artist.bodies[0])[:2], [1 - 0.25 * p, 1 + 0.25 * p], atol=1e-7
        )


@pytest.mark.parametrize("name", FAMILIES)
def test_lc5_reverse_unwinds_whole_schedule(name):
    cls = getattr(API, name)
    ax, artist = factory(name)
    anim = cls(artist, lag_ratio=1, reverse=True, rate_func=linear)
    frame = 0

    def record():
        nonlocal frame
        assert_factory_frame(name, ax, artist, 1 - frame / 6, lag=1)
        frame += 1

    probe(lambda s: frames(s, artist, anim), record)
    assert frame == 6


@pytest.mark.parametrize("box_ratio", [0.5, 0.25])
@pytest.mark.parametrize("horizontal", [False, True])
def test_bx2_whiskers_caps_means_and_fliers_keep_real_statistics(box_ratio, horizontal):
    ax = axes()
    sample = np.array([4, 5, 5, 5, 5, 6, 6, 6, 6, 11])  # flier inside both ranges
    box = ax.boxplot(
        sample, showmeans=True, orientation="horizontal" if horizontal else "vertical"
    )
    stats = deepcopy(box.stats)
    anim = API.GrowBoxPlot(box, box_ratio=box_ratio, lag_ratio=0, rate_func=linear)
    q1, _, q3 = np.percentile(sample, [25, 50, 75])
    # Matplotlib 3.10.7 cbook.boxplot_stats: extrema inside Tukey fences,
    # falling back to quartiles, rather than drawing the fences themselves.
    low = min(q1, sample[sample >= q1 - 1.5 * (q3 - q1)].min())
    high = max(q3, sample[sample <= q3 + 1.5 * (q3 - q1)].max())
    t = 0

    def record():
        nonlocal t
        p = float(np.clip((t / 6 - box_ratio) / (1 - box_ratio), 0, 1))
        for j, (quartile, end) in enumerate(((q1, low), (q3, high))):
            b = bounds(ax, box.whiskers[j])
            np.testing.assert_allclose(
                b[:2] if horizontal else b[2:],
                sorted((quartile, quartile + p * (end - quartile))),
                atol=1e-7,
            )
            cap = bounds(ax, box.caps[j])
            np.testing.assert_allclose(
                cap[:2] if horizontal else cap[2:],
                [quartile + p * (end - quartile)] * 2,
                atol=1e-7,
            )
            assert box.caps[j].get_stroke_opacity() == pytest.approx(p)
        for marker in (box.means[0][0], box.fliers[0][0]):
            assert marker.get_stroke_opacity() == pytest.approx(p)

        def coordinate(y):
            return ax.c2p(y, 1) if horizontal else ax.c2p(1, y)

        np.testing.assert_allclose(
            box.means[0][0].get_center(), coordinate(sample.mean()), atol=1e-6
        )
        np.testing.assert_allclose(
            box.fliers[0][0].get_center(), coordinate(11), atol=1e-6
        )
        np.testing.assert_equal(box.stats, stats)
        t += 1

    probe(lambda s: frames(s, box, anim), record)


@pytest.mark.parametrize("body_ratio", [0.5, 0.25])
def test_vn2_summary_stage_and_retained_kde(body_ratio):
    ax = axes()
    calls = 0

    def bandwidth(sample):
        nonlocal calls
        calls += 1
        return 0.4

    violin = ax.violinplot(
        [1, 2, 3, 4, 6], points=9, bw_method=bandwidth, showmeans=True, showmedians=True
    )
    before = calls
    parts = (
        violin.cbars + violin.cmins + violin.cmaxes + violin.cmeans + violin.cmedians
    )
    anim = API.UnfoldViolin(
        violin, body_ratio=body_ratio, lag_ratio=0, rate_func=linear
    )
    seen = probe(
        lambda s: frames(s, violin, anim),
        lambda: [part.get_stroke_opacity() for part in parts],
    )
    for i, opacity in enumerate(seen):
        p = np.clip((i / 6 - body_ratio) / (1 - body_ratio), 0, 1)
        np.testing.assert_allclose(opacity, p, atol=1e-8)
    assert calls == before
    assert all(part.get_stroke_opacity() == 1 for part in parts)


@pytest.mark.parametrize("name", (*FAMILIES, "ExplodePie"))
def test_mv3_cached_scene_tracks_linked_parts_without_moving_unrelated_plot(name):
    cls = getattr(API, name)
    ax, artist = factory("SweepPie" if name == "ExplodePie" else name)
    if name in ("SweepPie", "ExplodePie"):
        artist = mp.PieChart([1, 3], labels=["a", "b"], autopct="%.0f%%")
    linked = ax.bar_label(artist) if name == "GrowBars" else VGroup()
    if name == "RevealCells":
        linked = artist.label_cells()
    still_ax = axes()
    still = still_ax.line([0, 1], [0, 1])
    animation = cls(artist, **({"order": "data"} if name == "GrowBars" else {}))
    checks = []
    positions = []
    ticks = []

    class Shot(Scene):
        def begin_animations(self):
            super().begin_animations()
            moving = {id(m) for m in self.moving_mobjects}
            static = {id(m) for m in self.static_mobjects}
            changed = [
                *artist.family_members_with_points(),
                *linked.family_members_with_points(),
            ]
            assert all(id(m) in moving for m in changed)
            assert id(still) in static
            if name not in ("SweepPie", "ExplodePie"):
                assert id(ax.x.ticks.at(2.0)) in moving
            checks.append(True)

        def update_to_time(self, time):
            super().update_to_time(time)
            if name not in ("SweepPie", "ExplodePie"):
                tick = ax.x.ticks.at(2.0)
                ticks.append(tick.get_center()[0])
                assert ax.p2c(tick.get_center())[0] == pytest.approx(2, abs=1e-7)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            assert not [
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            ]
            if name == "GrowBars":
                positions.append(linked[0].get_bottom()[1])
                assert linked[0].get_bottom()[1] == pytest.approx(
                    artist[0].get_top()[1] + 0.1, abs=1e-6
                )

        def construct(self):
            # Place the unrelated plot first: native Cairo caches a static prefix.
            self.add(still_ax, still, ax, artist, linked)
            if name in ("SweepPie", "ExplodePie"):
                self.play(animation)
            else:
                self.play(animation, ax.animate.set_x_range((-4, 16, 2)))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert checks == [True]
    if name == "GrowBars":
        assert positions[-1] > positions[0]
    if ticks:
        assert max(ticks) - min(ticks) > 1e-3


@pytest.mark.parametrize("name", FAMILIES)
def test_cu1_every_exposed_part_retains_its_own_style(name):
    cls = getattr(API, name)
    ax, artist = factory(name)
    for i, part in enumerate(artist.family_members_with_points()):
        part.set_stroke(RED, width=2 + i, opacity=0.6)
        part.set_fill(opacity=0.35)
    saved = snapshot(artist)
    anim = cls(artist, **({"order": "data"} if name == "GrowBars" else {}))
    probe(lambda s: frames(s, artist, anim), lambda: None)
    assert_restored(saved)
    assert ax is not None  # retain the weakly referenced owning system


@pytest.mark.parametrize(
    "name,options",
    [
        ("GrowBars", {"order": "unknown"}),
        ("RevealCells", {"order": "unknown"}),
        ("RevealContours", {"order": "unknown"}),
        ("GrowBoxPlot", {"box_ratio": 1}),
        ("UnfoldViolin", {"body_ratio": 0}),
        ("ExplodePie", {"amount": float("nan")}),
        ("ExplodePie", {"indices": [3]}),
    ],
)
def test_cu2_invalid_options_rejected_before_mutation(name, options):
    cls = getattr(API, name)
    _, artist = factory("SweepPie" if name == "ExplodePie" else name)
    # Require the new public signature first; pre-implementation TypeErrors must
    # not be mistaken for the validation expected from a completed implementation.
    cls(artist, **({"order": "data"} if name == "GrowBars" else {}))
    saved = snapshot(artist)
    with pytest.raises(ValueError):
        cls(artist, **options)
    assert_restored(saved)


@pytest.mark.parametrize("kind", ["pcolormesh", "hist2d", "hexbin"])
def test_rc3_other_cell_artists_keep_geometry_and_scalar_mapping(kind):
    ax = axes()
    if kind == "pcolormesh":
        heat = ax.pcolormesh([0, 1, 4], [0, 2, 5], [[1, 2], [3, 4]])
    elif kind == "hist2d":
        heat = ax.hist2d([0.2, 1.2, 1.3], [0.2, 1.2, 1.3], bins=([0, 1, 2], [0, 1, 2]))
    else:
        heat = ax.hexbin(
            [0.2, 1.2, 1.3], [0.2, 1.2, 1.3], gridsize=2, mincnt=1, extent=(0, 2, 0, 2)
        )
    cells = list(heat.cells)
    saved = snapshot(heat)
    mapping = heat.color_mapping
    rgba = [c.get_fill_color() for c in cells]
    anim = API.RevealCells(heat, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, heat, anim), lambda: [c.get_fill_opacity() for c in cells]
    )
    for i, opacity in enumerate(seen):
        np.testing.assert_allclose(opacity, i / 6, atol=1e-8)
    assert heat.color_mapping is mapping
    assert [c.get_fill_color() for c in cells] == rgba
    assert_restored(saved)


@pytest.mark.parametrize("islands", [False, True])
def test_ct2_holes_and_disconnected_bands_preserve_subpaths(islands):
    ax = axes()
    x, y = np.meshgrid(np.linspace(0, 6, 13), np.linspace(0, 4, 9))
    z = (
        (x - 3) ** 2 + (y - 2) ** 2
        if not islands
        else np.minimum((x - 1.5) ** 2 + (y - 2) ** 2, (x - 4.5) ** 2 + (y - 2) ** 2)
    )
    contour = ax.contourf(x, y, z, levels=[0.3, 1.5])
    band = contour.at(0)
    before = [np.array(path, copy=True) for path in band.get_subpaths()]
    assert len(before) >= 2  # inner/outer rings, or disconnected islands
    anim = API.RevealContours(contour, rate_func=linear)

    def record():
        paths = band.get_subpaths()
        assert len(paths) == len(before)
        for path, expected in zip(paths, before, strict=True):
            np.testing.assert_allclose(path, expected, atol=1e-8)

    probe(lambda s: frames(s, contour, anim), record)


def test_ct3_callable_orders_bands_by_level():
    _ax, contour = factory("RevealContours")
    anim = API.RevealContours(
        contour, order=lambda level: -level, lag_ratio=1, rate_func=linear
    )
    seen = probe(
        lambda s: frames(s, contour, anim),
        lambda: [contour.at(i).get_fill_opacity() for i in range(2)],
    )
    assert seen[3] == pytest.approx([0, 1])
    assert [contour.at(i).get_fill_opacity() for i in range(2)] == pytest.approx([1, 1])


def test_ct4_line_contours_draw_independently():
    ax = axes()
    contour = ax.contour([0, 2, 4], [0, 2, 4], [[0, 2, 4]] * 3, levels=[1, 3])
    anim = API.RevealContours(contour, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, contour, anim),
        lambda: [anchors(ax, contour.at(level)) for level in (1, 3)],
    )
    for i, paths in enumerate(seen):
        for level, pts in zip((1, 3), paths, strict=True):
            np.testing.assert_allclose(pts[:, 0], level, atol=1e-7)
            assert np.ptp(pts[:, 1]) == pytest.approx(4 * i / 6, abs=1e-7)
    for level in (1, 3):
        assert np.ptp(anchors(ax, contour.at(level))[:, 1]) == pytest.approx(4)


@pytest.mark.parametrize("zero", [False, True])
def test_ps2_labels_and_percentage_text_follow_wedge_visibility(zero):
    pie = mp.PieChart(
        [1, 0, 3] if zero else [1, 3],
        labels=["a", "zero", "b"] if zero else ["a", "b"],
        autopct="%.0f%%",
    )
    assert pie.texts is not None and pie.autotexts is not None
    text_groups = (pie.texts, pie.autotexts)
    anim = API.SweepPie(pie, rate_func=linear)
    seen = probe(
        lambda s: frames(s, pie, anim),
        lambda: [[t.get_fill_opacity() for t in group] for group in text_groups],
    )
    for i, opacity in enumerate(seen):
        p = [
            np.clip((i / 6 - start) / share, 0, 1)
            for start, share in ((0, 0.25), (0.25, 0.75))
        ]
        if zero:
            p.insert(1, 0)
        np.testing.assert_allclose(opacity, [p, p], atol=1e-8)
    assert [t.text for t in pie.autotexts] == (
        ["25%", "0%", "75%"] if zero else ["25%", "75%"]
    )
    for group in text_groups:
        assert [t.get_fill_opacity() for t in group] == pytest.approx([1] * len(group))


def test_pe3_explosion_moves_labels_and_default_selects_all():
    pie = mp.PieChart([1, 3], labels=["a", "b"], autopct="%.0f%%", radius=2)
    assert pie.texts is not None and pie.autotexts is not None
    parts = [[pie.wedges[i], pie.texts[i], pie.autotexts[i]] for i in range(2)]
    saved = [[p.get_all_points().copy() for p in wedge_parts] for wedge_parts in parts]
    anim = API.ExplodePie(pie)
    seen = probe(
        lambda s: frames(s, pie, anim),
        lambda: [
            [p.get_all_points().copy() for p in wedge_parts] for wedge_parts in parts
        ],
    )
    for frame, state in enumerate(seen):
        for i, angle in enumerate((np.pi / 4, 5 * np.pi / 4)):
            displacement = (
                0.2
                * there_and_back(frame / 6)
                * np.array([np.cos(angle), np.sin(angle), 0])
            )
            for pts, canonical in zip(state[i], saved[i], strict=True):
                np.testing.assert_allclose(pts, canonical + displacement, atol=1e-8)
    for i, wedge_parts in enumerate(parts):
        for part, canonical in zip(wedge_parts, saved[i], strict=True):
            np.testing.assert_allclose(part.get_all_points(), canonical, atol=1e-8)


@pytest.mark.parametrize("lag", [0, 1])
def test_bx3_boxes_stagger_by_dataset(lag):
    ax = axes()
    box = ax.boxplot([[1, 2, 3, 4, 5], [9, 10, 11, 12, 13]], positions=[1, 3])
    anim = API.GrowBoxPlot(box, lag_ratio=lag, rate_func=linear)
    seen = probe(
        lambda s: frames(s, box, anim),
        lambda: [bounds(ax, part)[2:] for part in box.boxes],
    )
    for frame, values in enumerate(seen):
        for j, med in enumerate((3, 11)):
            p = min(2 * progress(frame / 6, j, 2, lag), 1)
            np.testing.assert_allclose(values[j], [med - p, med + p], atol=1e-7)


@pytest.mark.parametrize("lag", [0, 1])
def test_vn3_violins_stagger_by_dataset(lag):
    ax = axes()
    violin = ax.violinplot(
        [[1, 2, 3, 4, 5], [9, 10, 11, 12, 13]],
        positions=[1, 3],
        points=9,
        showextrema=False,
    )
    anim = API.UnfoldViolin(violin, lag_ratio=lag, rate_func=linear)
    seen = probe(
        lambda s: frames(s, violin, anim),
        lambda: [bounds(ax, part)[:2] for part in violin.bodies],
    )
    for frame, values in enumerate(seen):
        for j, pos in enumerate((1, 3)):
            p = min(2 * progress(frame / 6, j, 2, lag), 1)
            np.testing.assert_allclose(
                values[j], [pos - 0.25 * p, pos + 0.25 * p], atol=1e-7
            )


def test_rc4_clipped_cells_reveal_only_inside_viewport():
    ax = axes()
    heat = ax.pcolormesh([-4, 0, 2], [0, 2], [[1, 2]])
    cell = heat.cells.at((0, 0))
    anim = API.RevealCells(heat, lag_ratio=0, rate_func=linear)
    seen = probe(
        lambda s: frames(s, heat, anim),
        lambda: (bounds(ax, cell), cell.get_fill_opacity()),
    )
    for i, (rectangle, opacity) in enumerate(seen):
        np.testing.assert_allclose(rectangle, [-2, 0, 0, 2], atol=1e-8)
        assert opacity == pytest.approx(i / 6)
    np.testing.assert_allclose(bounds(ax, cell), [-2, 0, 0, 2], atol=1e-8)
