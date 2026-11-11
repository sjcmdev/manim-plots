"""Task 41: public, pre-implementation oracles for ADR 0008's 2D reveals."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import (
    Animation,
    Create,
    Line,
    Scene,
    Text,
    ThreeDScene,
    ValueTracker,
    linear,
    tempconfig,
    there_and_back,
)

import manim_plots as library
from tests.mobjects.helpers import RUN, probe

# New names are deliberately looked up inside tests, after collection (task 40).
mp: Any = library
FAMILIES = (
    "ExtendReference",
    "GrowRegion",
    "SweepRegion",
    "SweepSpan",
    "GrowRiemann",
    "GrowErrorBars",
    "RevealAnnotation",
    "RevealCrosshair",
    "RevealLegend",
    "FillColorbar",
    "BuildAxes",
)


def axes():
    return mp.Axes(x_range=(-2, 8, 1), y_range=(-4, 12, 2), tips=False)


def anchors(ax, mob):
    return data_anchors(ax, mob.points)


def data_anchors(ax, points):
    p = np.asarray(points)
    if not len(p):
        return np.empty((0, 2))
    return np.asarray([ax.p2c(q)[:2] for q in np.vstack((p[::4], p[3::4], p[-1]))])


def box(ax, mob):
    p = anchors(ax, mob)
    assert len(p), "expected partial geometry, possibly collapsed to its origin"
    return np.array([*p.min(axis=0), *p.max(axis=0)])[[0, 2, 1, 3]]


def ink(mob):
    """Zero for hidden parts, including a full-size but transparent FadeIn target."""
    total = 0.0
    for leaf in mob.family_members_with_points():
        opacity = float(leaf.get_fill_opacity())
        if float(leaf.get_stroke_width()) > 0:
            opacity += float(leaf.get_stroke_opacity())
        total += (
            float(np.linalg.norm(np.diff(leaf.points, axis=0), axis=1).sum()) * opacity
        )
    return total


def snapshot(mob):
    return [
        (np.array(m.points, copy=True), m.get_style())
        for m in mob.family_members_with_points()
    ]


def assert_snapshot(mob, before):
    after = snapshot(mob)
    assert len(after) == len(before)
    for (p, style), (q, old_style) in zip(after, before, strict=True):
        np.testing.assert_allclose(p, q, atol=1e-8)
        assert style.keys() == old_style.keys()
        for key in style:
            if isinstance(style[key], np.ndarray):
                np.testing.assert_allclose(style[key], old_style[key])
            else:
                assert style[key] == old_style[key]


def factory(name):
    ax = axes()
    held = []  # axes hold registered artists weakly
    if name == "ExtendReference":
        obj = ax.axvline(2, 0.25, 0.75, stroke_opacity=0.7)
    elif name in ("GrowRegion", "SweepRegion"):
        obj = ax.fill_between([0, 4], 6, 2, fill_opacity=0.4)
    elif name == "SweepSpan":
        obj = ax.axvspan(1, 5, 0.25, 0.75, fill_opacity=0.4)
    elif name == "GrowRiemann":
        graph = ax.plot(lambda x: x - 1, x_range=(0, 4))
        held.append(graph)
        obj = ax.get_riemann_rectangles(graph, (0, 4), dx=1, width_scale_factor=1)
    elif name == "GrowErrorBars":
        obj = ax.errorbar([1, 3], [2, 5], yerr=[[1, 2], [2, 1]], capsize=0.1)
    elif name == "RevealAnnotation":
        obj = ax.annotate(Text("A"), (2, 3), (4, 6))
    elif name == "RevealCrosshair":
        obj = ax.crosshair(2, 3)
    elif name == "RevealLegend":
        line = ax.line([0, 1], [1, 2], label="A")
        held.append(line)
        obj = mp.Legend(line, frame=True)
    elif name == "FillColorbar":
        obj = ax.colorbar(colorscale="viridis", vmin=1, vmax=100, norm="log")
    else:
        assert name == "BuildAxes"
        obj = ax
    return ax, obj, held


def make_animation(name, obj, **kwargs):
    # Exercise the new parameter even on the already-existing BuildAxes class.
    if name == "BuildAxes":
        kwargs.setdefault("stages", None)
    return getattr(mp, name)(obj, **kwargs)


def assert_bound(name, ax, obj):
    if name == "ExtendReference":
        lo, hi = ax.y_range[:2]
        np.testing.assert_allclose(
            box(ax, obj), [2, 2, lo + (hi - lo) / 4, lo + 3 * (hi - lo) / 4], atol=1e-8
        )
    elif name in ("GrowRegion", "SweepRegion"):
        np.testing.assert_allclose(box(ax, obj), [0, 4, 2, 6], atol=1e-8)
    elif name == "SweepSpan":
        lo, hi = ax.y_range[:2]
        np.testing.assert_allclose(
            box(ax, obj), [1, 5, lo + (hi - lo) / 4, lo + 3 * (hi - lo) / 4], atol=1e-8
        )
    elif name == "GrowRiemann":
        for i, rect in enumerate(obj):
            np.testing.assert_allclose(
                box(ax, rect), [i, i + 1, min(0, i - 1), max(0, i - 1)], atol=1e-8
            )
    elif name == "GrowErrorBars":
        p = anchors(ax, obj.ybars)
        for x, lo, hi in ((1, 1, 4), (3, 3, 6)):
            y = p[np.isclose(p[:, 0], x), 1]
            np.testing.assert_allclose([y.min(), y.max()], [lo, hi], atol=1e-8)
    elif name == "RevealAnnotation":
        np.testing.assert_allclose(obj.text.get_center(), ax.c2p(4, 6), atol=1e-8)
        np.testing.assert_allclose(obj.arrow.get_end(), ax.c2p(2, 3), atol=1e-8)
    elif name == "RevealCrosshair":
        np.testing.assert_allclose(obj.dot.get_center(), ax.c2p(2, 3), atol=1e-8)
        np.testing.assert_allclose(
            box(ax, obj.vline), [2, 2, *ax.y_range[:2]], atol=1e-8
        )
    elif name == "RevealLegend":
        assert obj.entries[0].artist.get_label() == "A"
        assert ink(obj.entries[0].label) > 0
    elif name == "FillColorbar":
        for k, cell in enumerate(obj.strip):
            assert obj.p2c(cell.get_bottom())[1] == pytest.approx(
                100 ** (k / 64), rel=1e-7
            )
        assert obj.strip.get_center()[1] == pytest.approx(ax.get_center()[1])
    else:
        np.testing.assert_allclose(
            obj.x.line.points[0], ax.c2p(ax.x_range[0], 0), atol=1e-8
        )
        np.testing.assert_allclose(
            obj.x.line.points[-1], ax.c2p(ax.x_range[1], 0), atol=1e-8
        )


def canonical(name):
    ax, obj, held = factory(name)
    before = snapshot(obj)
    updaters = [(m, tuple(m.updaters)) for m in obj.get_family()]

    def construct(scene):
        if obj is not ax:
            scene.add(ax)
        scene.play(make_animation(name, obj, rate_func=linear, run_time=1))
        assert obj in scene.mobjects

    probe(construct, lambda: None)
    assert_snapshot(obj, before)  # after finish, never seen[-1]
    for m, updates in updaters:
        assert tuple(m.updaters) == updates
    assert sum(len(m.updaters) for m in obj.get_family()) == sum(
        len(u) for _, u in updaters
    )
    ax.set_x_range((-3, 9, 1))
    ax.set_y_range((-6, 14, 2))
    ax.shift(np.array([0.25, 0.4, 0]))
    ax.update(0)
    obj.update(0)
    assert_bound(name, ax, obj)
    assert held is not None


def exit_and_reenter(name):
    ax, obj, held = factory(name)
    if name == "RevealLegend":
        held.append(ax.line([0, 1], [2, 3], label="B"))
        obj = mp.Legend(*held, frame=True)
    before = snapshot(obj)
    updaters = [(m, tuple(m.updaters)) for m in obj.get_family()]
    registered = tuple(ax.artists)
    kwargs = {}
    if name in ("GrowRiemann", "GrowErrorBars"):
        kwargs["lag_ratio"] = 0
    first = None
    if name in (
        "RevealAnnotation",
        "RevealCrosshair",
        "RevealLegend",
        "FillColorbar",
        "BuildAxes",
    ):
        kwargs["lag_ratio"] = 1
        first = {
            "RevealAnnotation": lambda: obj.arrow,
            "RevealCrosshair": lambda: obj.dot,
            "RevealLegend": lambda: obj.entries[0].handle,
            "FillColorbar": lambda: obj.strip,
            "BuildAxes": lambda: obj.x.line,
        }[name]()
    first_ink = ink(first) if first is not None else None

    def construct(scene):
        scene.add(ax, obj)
        scene.play(
            make_animation(
                name, obj, reverse=True, rate_func=linear, run_time=1, **kwargs
            )
        )
        alive = {id(m) for top in scene.mobjects for m in top.get_family()}
        assert id(obj) not in alive
        assert_snapshot(obj, before)
        for m, updates in updaters:
            assert tuple(m.updaters) == updates
        assert tuple(ax.artists) == registered
        scene.play(make_animation(name, obj, rate_func=linear, run_time=1))
        assert obj in scene.mobjects

    def measure():
        if first is not None:
            return ink(first)
        if name == "GrowRiemann":
            return [box(ax, r) if r.has_points() else None for r in obj]
        if name == "GrowErrorBars":
            return anchors(ax, obj.ybars)
        return box(ax, obj) if obj.has_points() else None

    seen = probe(construct, measure)
    if first is not None:
        assert seen[1] == pytest.approx(first_ink, rel=1e-6, abs=1e-8)
    elif name == "GrowRiemann":
        for i, observed in enumerate(seen[3]):
            np.testing.assert_allclose(
                observed,
                [i, i + 1, min(0, (i - 1) / 2), max(0, (i - 1) / 2)],
                atol=1e-8,
            )
    elif name == "GrowErrorBars":
        p = seen[3]
        for x, lo, hi in ((1, 1.5, 3), (3, 4, 5.5)):
            y = p[np.isclose(p[:, 0], x), 1]
            np.testing.assert_allclose([y.min(), y.max()], [lo, hi], atol=1e-8)
    else:
        expected = {
            "ExtendReference": [2, 2, 0, 4],
            "GrowRegion": [0, 4, 2, 4],
            "SweepRegion": [0, 2, 2, 6],
            "SweepSpan": [1, 3, 0, 8],
        }[name]
        np.testing.assert_allclose(seen[3], expected, atol=1e-8)
    assert_snapshot(obj, before)
    assert sum(len(m.updaters) for m in obj.get_family()) == sum(
        len(u) for _, u in updaters
    )
    assert_bound(name, ax, obj)
    assert held is not None


@pytest.mark.parametrize(
    "origin,expected", [("start", (-4, 4)), ("end", (4, 12)), ("center", (0, 8))]
)
def test_er1_reference_origins(origin, expected):
    ax = axes()
    line = ax.axvline(2)

    def construct(s):
        s.add(ax)
        s.play(mp.ExtendReference(line, origin=origin, rate_func=linear, run_time=1))

    seen = probe(construct, lambda: box(ax, line) if line.has_points() else None)
    np.testing.assert_allclose(seen[3], [2, 2, *expected], atol=1e-8)
    np.testing.assert_allclose(box(ax, line), [2, 2, -4, 12], atol=1e-8)


def test_er4_drop_line_starts_at_axis_and_invalid_origin_is_atomic():
    ax = axes()
    line = ax.get_vertical_line(ax.c2p(3, 8), line_func=Line)
    before = snapshot(line)
    with pytest.raises(ValueError, match="origin"):
        mp.ExtendReference(line, origin="unknown")
    assert_snapshot(line, before)
    seen = probe(
        lambda s: s.play(mp.ExtendReference(line, rate_func=linear, run_time=1)),
        lambda: box(ax, line) if line.has_points() else None,
    )
    np.testing.assert_allclose(seen[3], [3, 3, 0, 4], atol=1e-8)


@pytest.mark.parametrize("horizontal", [False, True])
def test_gr1_paired_boundary_not_zero(horizontal):
    ax = axes()
    region = (ax.fill_betweenx if horizontal else ax.fill_between)([0, 4], 6, 2)
    seen = probe(
        lambda s: s.play(mp.GrowRegion(region, rate_func=linear, run_time=1)),
        lambda: box(ax, region) if region.has_points() else None,
    )
    np.testing.assert_allclose(
        seen[3], [2, 4, 0, 4] if horizontal else [0, 4, 2, 4], atol=1e-8
    )


@pytest.mark.parametrize("axis", [None, "x", "y"])
def test_lc7_valid_axis_options(axis):
    ax = axes()
    region = (ax.fill_betweenx if axis == "x" else ax.fill_between)([0, 4], 6, 2)
    seen = probe(
        lambda s: s.play(
            mp.GrowRegion(region, axis=axis, rate_func=linear, run_time=1)
        ),
        lambda: box(ax, region) if region.has_points() else None,
    )
    np.testing.assert_allclose(
        seen[3], [2, 4, 0, 4] if axis == "x" else [0, 4, 2, 4], atol=1e-8
    )


def test_gr4_crossing_and_area_from_graph_baseline():
    ax = axes()
    region = ax.fill_between([0, 2], [4, -2], 1)
    seen = probe(
        lambda s: s.play(mp.GrowRegion(region, rate_func=linear, run_time=1)),
        lambda: anchors(ax, region),
    )
    p = seen[3]
    for expected in ([0, 1], [0, 2.5], [1, 1], [2, -0.5], [2, 1]):
        assert np.any(np.all(np.isclose(p, expected, atol=1e-8), axis=1))
    graph = ax.plot(lambda x: x + 4, x_range=(0, 2), use_smoothing=False)
    base = ax.plot(lambda x: x + 1, x_range=(0, 2), use_smoothing=False)
    area = ax.get_area(graph, (0, 2), bounded_graph=base)
    seen = probe(
        lambda s: s.play(mp.GrowRegion(area, rate_func=linear, run_time=1)),
        lambda: anchors(ax, area),
    )
    p = seen[3]
    # Every anchor belongs to one of the two straight, parallel boundaries.
    delta = p[:, 1] - p[:, 0]
    assert np.all(np.isclose(delta, 1) | np.isclose(delta, 2.5))
    np.testing.assert_allclose([p[:, 0].min(), p[:, 0].max()], [0, 2], atol=1e-8)


@pytest.mark.parametrize("direction", [1, -1])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_sr1_exact_closed_front(axis, direction):
    ax = axes()
    region = (ax.fill_between if axis == "x" else ax.fill_betweenx)([0, 4], 6, 2)
    seen = probe(
        lambda s: s.play(
            mp.SweepRegion(
                region, axis=axis, direction=direction, rate_func=linear, run_time=1
            )
        ),
        lambda: anchors(ax, region),
    )
    p = seen[3]
    col = 0 if axis == "x" else 1
    np.testing.assert_allclose(
        [p[:, col].min(), p[:, col].max()],
        [0, 2] if direction == 1 else [2, 4],
        atol=1e-8,
    )
    front = p[np.isclose(p[:, col], 2), 1 - col]
    np.testing.assert_allclose([front.min(), front.max()], [2, 6], atol=1e-8)
    np.testing.assert_allclose(p[0], p[-1], atol=1e-8)


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("direction", [1, -1])
def test_ss1_mixed_coordinate_span(horizontal, direction):
    ax = axes()
    span = (ax.axhspan if horizontal else ax.axvspan)(1, 5, 0.25, 0.75)
    seen = probe(
        lambda s: s.play(
            mp.SweepSpan(span, direction=direction, rate_func=linear, run_time=1)
        ),
        lambda: box(ax, span) if span.has_points() else None,
    )
    interval = [1, 3] if direction == 1 else [3, 5]
    np.testing.assert_allclose(
        seen[3], [0.5, 5.5, *interval] if horizontal else [*interval, 0, 8], atol=1e-8
    )


@pytest.mark.parametrize(
    "sample,fraction", [("left", 0), ("center", 0.5), ("right", 1)]
)
def test_ri1_signed_rectangles_and_lag(sample, fraction):
    ax = axes()
    graph = ax.plot(lambda x: x - 1, x_range=(0, 5))
    rects = ax.get_riemann_rectangles(
        graph, (0, 4), dx=1.5, input_sample_type=sample, width_scale_factor=1
    )
    seen = probe(
        lambda s: s.play(
            mp.GrowRiemann(rects, lag_ratio=0.5, rate_func=linear, run_time=1)
        ),
        lambda: [box(ax, r) if r.has_points() else None for r in rects],
    )
    for frame in (2, 3, 4):
        for i, observed in enumerate(seen[frame]):
            x = 1.5 * i
            top = x + 1.5 * fraction - 1
            p = np.clip((frame / 6) * 2 - i * 0.5, 0, 1)
            if p == 0 and observed is None:
                continue
            np.testing.assert_allclose(
                observed, [x, x + 1.5, min(0, p * top), max(0, p * top)], atol=1e-8
            )
    assert len(rects) == 3  # keep the artist's existing full-width last rectangle


def test_eb1_asymmetric_errors_zero_and_every():
    ax = axes()
    errors = ax.errorbar(
        [1, 2, 3],
        [3, 4, 5],
        xerr=0,
        yerr=[[1, 3, 2], [2, 3, 1]],
        errorevery=2,
        capsize=0.12,
    )
    seen = probe(
        lambda s: s.play(
            mp.GrowErrorBars(
                errors, lag_ratio=0, cap_lag=0, rate_func=linear, run_time=1
            )
        ),
        lambda: anchors(ax, errors.ybars),
    )
    p = seen[3]
    np.testing.assert_allclose(np.unique(p[:, 0]), [1, 3], atol=1e-8)
    for x, lo, hi in [(1, 2.5, 4), (3, 4, 5.5)]:
        y = p[np.isclose(p[:, 0], x), 1]
        np.testing.assert_allclose([y.min(), y.max()], [lo, hi], atol=1e-8)
    assert np.isfinite(errors.xbars.points).all()
    for cap in errors.ycaps.get_subpaths():
        assert np.linalg.norm(cap[-1] - cap[0]) == pytest.approx(0.12)


def test_eb4_caps_finish_late_and_keep_scene_width():
    ax = axes()
    errors = ax.errorbar([2], [3], xerr=[[1], [2]], capsize=0.2)
    seen = probe(
        lambda s: s.play(
            mp.GrowErrorBars(
                errors, lag_ratio=0, cap_lag=0.5, rate_func=linear, run_time=1
            )
        ),
        lambda: [np.linalg.norm(p[-1] - p[0]) for p in errors.xcaps.get_subpaths()],
    )
    assert all(w < 1e-8 for w in seen[2])
    np.testing.assert_allclose(seen[4], [0.2 / 3] * 2, atol=1e-8)
    ax.set_y_range((-8, 16, 2))
    for cap in errors.xcaps.get_subpaths():
        assert np.linalg.norm(cap[-1] - cap[0]) == pytest.approx(0.2)


def test_eb5_optional_parts_invalid_mask_and_independent_styles():
    ax = axes()
    with pytest.warns(mp.ManimPlotsWarning):
        errors = ax.errorbar(
            [1, 2, 3], [3, 4, 5], yerr=[1, np.nan, 2], capsize=0, line=True
        )
    errors.ybars.set_stroke("#ff0000", opacity=0.4, width=3)
    errors.markers.set_fill("#00ff00", opacity=0.6)
    before = snapshot(errors)
    seen = probe(
        lambda s: s.play(mp.GrowErrorBars(errors, lag_ratio=0, run_time=1)),
        lambda: (
            anchors(ax, errors.ybars),
            float(errors.markers[0].get_fill_opacity()),
            ax.p2c(errors.line.points[-1])[:2] if errors.line.has_points() else None,
        ),
    )
    for p, _, _ in seen:
        assert np.isfinite(p).all()
        assert not np.any(np.isclose(p[:, 0], 2))
    assert seen[3][1] == pytest.approx(0.3)
    np.testing.assert_allclose(seen[3][2], [2, 4], atol=1e-8)
    assert errors.xbars is None and errors.xcaps is None
    assert not errors.ycaps.has_points()
    assert errors.line is not None and errors.markers is not None
    assert_snapshot(errors, before)


@pytest.mark.parametrize("text_first", [False, True])
def test_an1_arrow_and_custom_text_order(text_first):
    ax = axes()
    text = Text("A", color="#ff0000")
    ann = ax.annotate(text, (2, 3), (4, 6))
    arrow = ann.arrow
    before = snapshot(ann)
    seen = probe(
        lambda s: s.play(
            mp.RevealAnnotation(
                ann, text_first=text_first, lag_ratio=1, rate_func=linear, run_time=1
            )
        ),
        lambda: (ink(ann.text), ink(arrow)),
    )
    assert seen[1][0 if text_first else 1] > 0
    assert seen[1][1 if text_first else 0] < 1e-8
    assert ann.text is text
    assert_snapshot(ann, before)


def test_an4_text_only():
    ax = axes()
    ann = ax.annotate(Text("A"), (2, 3), arrow=False)
    probe(lambda s: s.play(mp.RevealAnnotation(ann)), lambda: None)
    assert ann.arrow is None
    assert ink(ann.text) > 0


def test_ch1_current_intersection_and_no_ghosts():
    ax = axes()
    tracker = ValueTracker(1)
    cross = ax.crosshair(tracker, 3)
    ghosts = []

    def construct(scene):
        scene.add(ax, cross)

        def check(_):
            alive = {id(m) for top in scene.mobjects for m in top.get_family()}
            ghosts.extend(
                m
                for m in scene.moving_mobjects
                if id(m) not in alive and m.has_points()
            )

        scene.add_updater(check)
        scene.play(
            mp.RevealCrosshair(cross, lag_ratio=0, rate_func=linear, run_time=1),
            cast(Any, tracker.animate)(rate_func=linear).set_value(4),
        )

    seen = probe(
        construct,
        lambda: (
            tracker.get_value(),
            cross.dot.get_center().copy(),
            box(ax, cross.vline) if cross.vline.has_points() else None,
        ),
    )
    for i, (x, center, observed) in enumerate(seen):
        np.testing.assert_allclose(center, ax.c2p(x, 3), atol=1e-8)
        if observed is not None:
            p = i / 6
            np.testing.assert_allclose(
                observed, [x, x, 3 - 7 * p, 3 + 9 * p], atol=1e-8
            )
    assert not ghosts
    assert cross.readout.text == "(4.00, 3.00)"


def test_ch4_optional_readout():
    ax = axes()
    cross = ax.crosshair(2, 3, readout=False)
    probe(lambda s: s.play(mp.RevealCrosshair(cross)), lambda: None)
    assert cross.readout is None
    np.testing.assert_allclose(cross.dot.get_center(), ax.c2p(2, 3), atol=1e-8)


def test_le1_entry_order_and_frame_without_implicit_artist_reveal():
    ax = axes()
    a = ax.line([0, 1], [1, 2], label="A")
    b = ax.line([0, 1], [2, 3], label="B")
    legend = mp.Legend(a, b, frame=True)
    original = snapshot(a)
    seen = probe(
        lambda s: s.play(
            mp.RevealLegend(legend, lag_ratio=1, rate_func=linear, run_time=1)
        ),
        lambda: [ink(e.handle) + ink(e.label) for e in legend.entries],
    )
    assert seen[1][0] > 0
    assert seen[1][1] < 1e-8
    assert_snapshot(a, original)
    assert legend.frame is not None and ink(legend.frame) > 0


def test_le4_empty_and_explicit_linked_animation():
    legend = mp.Legend()
    probe(lambda s: s.play(mp.RevealLegend(legend)), lambda: None)
    assert legend.entries == []
    ax = axes()
    line = ax.line([0, 1], [1, 2], label="A")
    legend = mp.Legend(line)
    seen = []

    def construct(scene):
        scene.add(ax, line)
        shift = ax.c2p(0, 2) - ax.c2p(0, 0)
        scene.play(
            mp.RevealLegend(
                legend,
                artist_animations=[line.animate(rate_func=linear).shift(shift).build()],
                lag_ratio=0,
                rate_func=linear,
                run_time=1,
            )
        )

    probe(construct, lambda: seen.append(box(ax, line)))
    np.testing.assert_allclose(seen[3], [0, 1, 2, 3], atol=1e-8)
    np.testing.assert_allclose(box(ax, line), [0, 1, 3, 4], atol=1e-8)


def test_cb1_normalized_cells_then_axis():
    ax = axes()
    bar = ax.colorbar(colorscale="viridis", vmin=1, vmax=1000, norm="log")
    before = snapshot(bar)
    seen = probe(
        lambda s: s.play(
            mp.FillColorbar(bar, lag_ratio=1, rate_func=linear, run_time=1)
        ),
        lambda: ([float(c.get_fill_opacity()) for c in bar.strip], ink(bar.axis.ticks)),
    )
    cells, ticks = seen[1]  # two equal stages; strip is one third full
    np.testing.assert_allclose(cells[:21], 1)
    assert cells[21] == pytest.approx(1 / 3)
    np.testing.assert_allclose(cells[22:], 0)
    assert ticks < 1e-8
    assert_snapshot(bar, before)
    for k, cell in enumerate(bar.strip):
        assert bar.p2c(cell.get_bottom())[1] == pytest.approx(
            1000 ** (k / 64), rel=1e-7
        )


def test_ba1_explicit_stages_and_atomic_validation():
    ax = axes()
    before = snapshot(ax)
    with pytest.raises(ValueError, match="stage"):
        mp.BuildAxes(ax, stages=("ticks", "unknown"))
    assert_snapshot(ax, before)
    seen = probe(
        lambda s: s.play(
            mp.BuildAxes(
                ax, stages=("ticks", "lines"), lag_ratio=1, rate_func=linear, run_time=1
            )
        ),
        lambda: (ink(ax.x.ticks), ink(ax.x.line)),
    )
    assert seen[1][0] > 0
    assert seen[1][1] < 1e-8
    assert_snapshot(ax, before)


def test_ba4_grouped_stages_factories_and_absent_parts():
    ax = axes()
    called = []

    def factory(parts):
        called.append(parts)
        return Create(parts)

    animation = mp.BuildAxes(
        ax,
        stages=(
            ("lines", "tips"),
            "ticks",
            "minor_ticks",
            "numbers",
            "labels",
            "grid",
            "panes",
            "breaks",
        ),
        stage_animations={"ticks": factory},
    )
    before = snapshot(ax)
    probe(lambda s: s.play(animation), lambda: None)
    assert len(called) == 1
    members = {id(m) for m in called[0].get_family()}
    assert id(ax.x.ticks.at(1)) in members
    assert_snapshot(ax, before)


@pytest.mark.parametrize(
    "stage", ["tips", "minor_ticks", "numbers", "labels", "grid", "breaks"]
)
def test_ba5_populated_optional_stage(stage):
    ax = mp.Axes(x_range=(-2, 8, 1), y_range=(-4, 12, 2))
    if stage == "minor_ticks":
        ax.x.set_locator(mp.MultipleLocator(2), minor=mp.MultipleLocator(1))
        part = ax.x.minor_ticks
    elif stage == "numbers":
        ax.x.add_numbers([1, 2, 3])
        part = ax.x.numbers
    elif stage == "labels":
        ax.x.add_labels({1: Text("A")})
        part = ax.x.labels
    elif stage == "grid":
        ax.x.set_grid("major", stroke_width=1)
        part = ax.x.grid
    elif stage == "breaks":
        ax.x.set_breaks([(2, 4)], gap=0.05)
        part = ax.x.break_marks
    else:
        part = ax.x.tip
    before = snapshot(ax)
    assert ink(part) > 0
    seen = probe(
        lambda s: s.play(
            mp.BuildAxes(
                ax, stages=(stage, "lines"), lag_ratio=1, rate_func=linear, run_time=1
            )
        ),
        lambda: (ink(part), ink(ax.x.line)),
    )
    assert seen[1][0] > 0
    assert seen[1][1] < 1e-8
    assert_snapshot(ax, before)


def test_ba3_none_preserves_existing_default_stage_schedule():
    ax = axes()
    ax.x.add_numbers([1])
    ax.x.set_grid("major", stroke_width=1)
    before = snapshot(ax)
    seen = probe(
        lambda s: s.play(mp.BuildAxes(ax, stages=None, rate_func=linear, run_time=1)),
        lambda: [ink(p) for p in (ax.x.line, ax.x.ticks, ax.x.numbers, ax.x.grid)],
    )
    assert seen[1][0] > 0
    np.testing.assert_allclose(seen[1][1:], 0, atol=1e-8)
    assert all(p > 0 for p in seen[3][:3])
    assert seen[3][3] < 1e-8
    assert_snapshot(ax, before)


@pytest.mark.parametrize("name", FAMILIES)
def test_lc1_flags_are_independent(name):
    ax, obj, held = factory(name)
    before = snapshot(obj)

    def construct(scene):
        scene.add(ax, obj)
        scene.play(make_animation(name, obj, reverse=True, remover=False, run_time=1))
        assert obj in scene.mobjects
        assert_snapshot(obj, before)
        scene.play(make_animation(name, obj, remover=True, run_time=1))
        assert obj not in scene.mobjects
        assert_snapshot(obj, before)

    probe(construct, lambda: None)
    assert held is not None


def test_lc2_nonmonotone_progress_does_not_accumulate():
    ax = axes()
    region = ax.fill_between([0, 4], 6, 2)
    seen = probe(
        lambda s: s.play(mp.GrowRegion(region, rate_func=there_and_back, run_time=1)),
        lambda: box(ax, region) if region.has_points() else None,
    )
    np.testing.assert_allclose(seen[1], seen[5], atol=1e-8)
    np.testing.assert_allclose(seen[2], seen[4], atol=1e-8)
    np.testing.assert_allclose(box(ax, region), [0, 4, 2, 6], atol=1e-8)


def test_lc3_concurrent_range_uses_current_map():
    ax = axes()
    region = ax.fill_between([0, 4], 6, 2)

    def construct(s):
        s.add(ax, region)
        s.play(
            mp.SweepRegion(region, rate_func=linear, run_time=1),
            ax.animate(rate_func=linear).set_x_range((-3, 9, 1)),
        )

    seen = probe(construct, lambda: box(ax, region) if region.has_points() else None)
    for i, observed in enumerate(seen):
        if observed is not None:
            np.testing.assert_allclose(observed, [0, 4 * i / 6, 2, 6], atol=1e-8)


@pytest.mark.parametrize("name", ["GrowRegion", "SweepRegion"])
def test_lc4_empty_mask_and_separate_crossing_lobes(name):
    ax = axes()
    region = ax.fill_between(
        [0, 1, 2, 3, 4], [4, -1, 5, -1, 4], 2, where=[True, True, False, True, True]
    )
    seen = probe(
        lambda s: s.play(getattr(mp, name)(region, rate_func=linear, run_time=1)),
        lambda: [data_anchors(ax, p) for p in region.get_subpaths()],
    )
    for paths in seen:
        for p in paths:
            assert p[:, 0].max() <= 1 + 1e-8 or p[:, 0].min() >= 3 - 1e-8
    empty = ax.fill_between([0, 1], 3, 1, where=[False, False])
    probe(lambda s: s.play(getattr(mp, name)(empty)), lambda: None)
    assert not empty.has_points()


def test_lc5_public_exports_and_native_classes():
    import importlib

    for name in FAMILIES:
        module = (
            "axes"
            if name == "BuildAxes"
            else "decorations"
            if name in ("RevealLegend", "FillColorbar")
            else "helpers"
        )
        cls = getattr(mp, name)
        assert issubclass(cls, Animation)
        assert cls is getattr(importlib.import_module("manim_plots.animations"), name)
        assert cls is getattr(
            importlib.import_module(f"manim_plots.animations.{module}"), name
        )


@pytest.mark.parametrize("name", ["ExtendReference", "SweepRegion", "GrowRiemann"])
def test_lc6_reverse_unwinds_geometry_and_lag(name):
    ax, obj, held = factory(name)
    kwargs = {"lag_ratio": 0.5} if name == "GrowRiemann" else {}

    def measure():
        parts = list(obj) if name == "GrowRiemann" else [obj]
        return [box(ax, p) if p.has_points() else None for p in parts]

    def reverse(scene):
        scene.add(obj)
        scene.play(
            make_animation(
                name, obj, reverse=True, rate_func=linear, run_time=1, **kwargs
            )
        )

    backward = probe(reverse, measure)
    for frame in (1, 2, 3, 4, 5):
        t = 1 - frame / 6
        for i, observed in enumerate(backward[frame]):
            if name == "ExtendReference":
                expected = [2, 2, 0, 8 * t]
            elif name == "SweepRegion":
                expected = [0, 4 * t, 2, 6]
            else:
                p = np.clip(t * 2.5 - i * 0.5, 0, 1)
                if p == 0 and observed is None:
                    continue
                expected = [i, i + 1, min(0, p * (i - 1)), max(0, p * (i - 1))]
            np.testing.assert_allclose(observed, expected, atol=1e-8)
    assert held is not None


@pytest.mark.parametrize("name", ["BuildAxes", "FillColorbar", "RevealLegend"])
def test_mv1_moving_detection_and_static_sampling(name):
    ax, obj, held = factory(name)
    still_ax = axes()
    calls = []

    def f(x):
        calls.append(x)
        return x / 2

    still = still_ax.plot(f)
    _ = still.points
    moving = []
    kwargs = {}
    target = obj
    if name == "RevealLegend":
        target = held[0]
        # Use an explicit animation on the legend's own linked line.
        kwargs["artist_animations"] = [
            target.animate.shift(np.array([0.2, 0, 0])).build()
        ]
    affected = {id(m) for m in target.family_members_with_points()}

    class Shot(Scene):
        def begin_animations(self):
            super().begin_animations()
            members = {id(m) for m in self.moving_mobjects}
            moving.append((affected <= members, id(still) not in members))

        def construct(self):
            self.add(still_ax, still, ax, obj, *held)
            self.play(make_animation(name, obj, rate_func=linear, run_time=1, **kwargs))

    with tempconfig(RUN | {"disable_caching": False}):
        _ = still.points
        count = len(calls)
        Shot().render()
    assert moving == [(True, True)]
    assert len(calls) == count


def test_cb4_fixed_in_frame_colorbar():
    ax = mp.ThreeDAxes()
    bar = ax.colorbar(colorscale="viridis", vmin=0, vmax=1)
    found = []

    class Shot(ThreeDScene):
        def construct(self):
            self.add(ax, bar)
            self.play(mp.FillColorbar(bar, run_time=1))
            found.append(bar in self.camera.fixed_in_frame_mobjects)

    with tempconfig(RUN):
        Shot().render()
    assert found == [True]


def test_cb5_live_mapping_moving_parts_and_replaced_numbers():
    ax = axes()
    img = ax.imshow(np.array([[1.0, 3.0]]))
    bar = ax.colorbar(img)
    affected = {id(m) for m in bar.family_members_with_points()}
    samples = []
    moving = []
    ghosts = []

    class Shot(Scene):
        def begin_animations(self):
            super().begin_animations()
            moving.append(affected <= {id(m) for m in self.moving_mobjects})

        def update_to_time(self, t):
            super().update_to_time(t)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            ghosts.extend(
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            )
            samples.append(
                (t, tuple(bar.y_range[:2]), bar.p2c(bar.strip[16].get_bottom())[1])
            )

        def construct(self):
            self.add(ax, img, bar)
            self.play(
                mp.FillColorbar(bar, lag_ratio=0, rate_func=linear, run_time=1),
                img.animate(rate_func=linear).set_data(np.array([[2.0, 6.0]])),
            )

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert moving == [True]
    assert samples and not ghosts
    for t, limits, edge in samples:
        np.testing.assert_allclose(limits, [1 + t, 3 + 3 * t], atol=1e-8)
        assert edge == pytest.approx(1 + t + (2 + 2 * t) / 4)
    np.testing.assert_allclose(bar.y_range[:2], [2, 6], atol=1e-8)


def test_lc7_invalid_options_do_not_change_artists():
    ax = axes()
    region = ax.fill_between([0, 4], 6, 2)
    before = snapshot(region)
    cases: list[tuple[str, dict[str, Any]]] = [
        ("GrowRegion", {"axis": "z"}),
        ("SweepRegion", {"direction": 0}),
        ("SweepSpan", {"direction": 2}),
    ]
    for name, options in cases:
        with pytest.raises(ValueError):
            getattr(mp, name)(region, **options)
        assert_snapshot(region, before)
    from manim import Polygon

    with pytest.raises(TypeError):
        mp.GrowRegion(Polygon(*[ax.c2p(x, y) for x, y in [(0, 0), (1, 0), (0, 1)]]))


def test_lc8_log_growth_is_in_data_not_log_space():
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(1, 100, 1), y_scale="log")
    region = ax.fill_between([0, 4], 81, 1)
    seen = probe(
        lambda s: s.play(mp.GrowRegion(region, rate_func=linear, run_time=1)),
        lambda: box(ax, region) if region.has_points() else None,
    )
    np.testing.assert_allclose(seen[3], [0, 4, 1, 41], atol=1e-7)


@pytest.mark.parametrize("name", ["GrowRegion", "SweepRegion", "GrowRiemann"])
def test_lc9_unchanged_own_graph_is_not_resampled_per_frame(name):
    calls = []

    def f(x):
        calls.append(x)
        return x + 2

    with tempconfig(RUN):
        ax = axes()
        graph = ax.plot(f, x_range=(0, 2), use_smoothing=False)
        obj = (
            ax.get_riemann_rectangles(graph, (0, 2), dx=1)
            if name == "GrowRiemann"
            else ax.get_area(graph, (0, 2))
        )
        for leaf in obj.family_members_with_points():
            _ = leaf.points
        _ = graph.points
        count = len(calls)

        def construct(scene):
            scene.add(ax, graph, obj)
            scene.play(getattr(mp, name)(obj, rate_func=linear, run_time=1))

        probe(construct, lambda: None)
    assert len(calls) == count


def test_er2_exit():
    exit_and_reenter("ExtendReference")


def test_er3_canonical():
    canonical("ExtendReference")


def test_gr2_exit():
    exit_and_reenter("GrowRegion")


def test_gr3_canonical():
    canonical("GrowRegion")


def test_sr2_exit():
    exit_and_reenter("SweepRegion")


def test_sr3_canonical():
    canonical("SweepRegion")


def test_ss2_exit():
    exit_and_reenter("SweepSpan")


def test_ss3_canonical():
    canonical("SweepSpan")


def test_ri2_exit():
    exit_and_reenter("GrowRiemann")


def test_ri3_canonical():
    canonical("GrowRiemann")


def test_eb2_exit():
    exit_and_reenter("GrowErrorBars")


def test_eb3_canonical():
    canonical("GrowErrorBars")


def test_an2_exit():
    exit_and_reenter("RevealAnnotation")


def test_an3_canonical():
    canonical("RevealAnnotation")


def test_ch2_exit():
    exit_and_reenter("RevealCrosshair")


def test_ch3_canonical():
    canonical("RevealCrosshair")


def test_le2_exit():
    exit_and_reenter("RevealLegend")


def test_le3_canonical():
    canonical("RevealLegend")


def test_cb2_exit():
    exit_and_reenter("FillColorbar")


def test_cb3_canonical():
    canonical("FillColorbar")


def test_ba2_exit():
    exit_and_reenter("BuildAxes")


def test_ba3_canonical():
    canonical("BuildAxes")
