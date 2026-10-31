"""Task 44 public topology-transition oracles, written before implementation."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest
from manim import RED, Animation, Scene, ValueTracker, linear

import manim_plots as library
from tests.mobjects.helpers import probe

mp = cast(Any, library)  # Future exports must fail in tests, not during collection.


def coords(ax: Any, mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    if not len(points):
        return np.empty((0, 3))
    return np.array([ax.p2c(p) for p in np.vstack((points[::4], points[-1:]))])


def leaves(mob: Any) -> list[Any]:
    return [m for m in mob.family_members_with_points() if not m.submobjects]


def bounds(ax: Any, mob: Any) -> np.ndarray:
    p = coords(ax, mob)
    assert len(p), "expected drawable geometry"
    return np.array([p.min(axis=0), p.max(axis=0)])


def play(ax: Any, artist: Any, animation: Any) -> list[Any]:
    def construct(scene: Scene) -> None:
        scene.add(ax, artist)
        scene.play(animation)

    return probe(construct, lambda: None)


def rectangles(rule: Any = "left", dx: Any = 1, end: float = 2) -> tuple[Any, Any, Any]:
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(-3, 4, 1))
    graph = ax.plot(lambda x: x - 1.1, x_range=(0, 4))
    rects = ax.get_riemann_rectangles(
        graph,
        x_range=(0, end),
        dx=dx,
        input_sample_type=rule,
        width_scale_factor=1,
        fill_opacity=0.6,
    )
    return ax, graph, rects


@pytest.mark.parametrize(
    "rule,fraction",
    [("left", 0), ("center", 0.5), ("right", 1), (lambda a, b: a + (b - a) / 4, 0.25)],
)
def test_rr1_nested_children_start_at_parent_height(rule, fraction):
    ax, graph, rects = rectangles(rule)
    animation = mp.RefineRiemann(rects, 0.5, rate_func=linear)
    seen: list[list[np.ndarray]] = []

    def construct(scene):
        scene.add(ax, graph, rects)
        scene.play(animation)

    probe(construct, lambda: seen.append([bounds(ax, r) for r in rects]))
    assert len(seen[0]) == 4
    for i, box in enumerate(seen[0]):
        parent = i // 2 + fraction - 1.1
        np.testing.assert_allclose(box[:, 0], [i / 2, (i + 1) / 2], atol=1e-8)
        np.testing.assert_allclose(box[:, 1], sorted([0, parent]), atol=1e-8)
    mid = seen[3]  # t=.5 at six frames/sec and run_time=1
    for i, box in enumerate(mid):
        height = 0.5 * (i // 2 + fraction - 1.1 + (i + fraction) / 2 - 1.1)
        np.testing.assert_allclose(box[:, 1], sorted([0, height]), atol=1e-8)
    for i, rect in enumerate(rects):
        height = (i + fraction) / 2 - 1.1
        np.testing.assert_allclose(
            bounds(ax, rect)[:, 1], sorted([0, height]), atol=1e-8
        )


def test_rr2_full_width_overshoot_and_canonical_tracker_binding():
    tracker = ValueTracker(1)
    ax, graph, rects = rectangles(dx=tracker, end=2.25)
    before = tuple(rects.updaters)
    seen: list[list[np.ndarray]] = []

    def construct(scene):
        scene.add(ax, graph, rects)
        scene.play(mp.RefineRiemann(rects, 0.5, rate_func=linear))

    probe(construct, lambda: seen.append([bounds(ax, r) for r in rects]))
    # The old last interval [2,3] contributes only the required child [2,2.5].
    np.testing.assert_allclose(seen[0][-1][:, 0], [2, 2.5], atol=1e-8)
    np.testing.assert_allclose(seen[0][-1][:, 1], [0, 0.9], atol=1e-8)
    assert tracker.get_value() == pytest.approx(0.5)
    assert len(rects) == 5
    assert bounds(ax, rects[-1])[1, 0] == pytest.approx(2.5)
    ax.set_x_range((0, 5, 1))
    assert bounds(ax, rects[-1])[1, 0] == pytest.approx(2.5)
    assert tuple(rects.updaters) == before
    tracker.set_value(0.25)
    assert len(rects) == 9
    assert bounds(ax, rects[-1])[1, 0] == pytest.approx(2.25)
    assert graph is not None


def test_rr3_inverse_and_invalid_partition_are_atomic():
    ax, graph, rects = rectangles(dx=0.5)
    play(ax, rects, mp.RefineRiemann(rects, 1))
    assert len(rects) == 2
    old = [r.points.copy() for r in rects]
    for dx in (0, -1, float("nan"), 0.6):
        with pytest.raises(ValueError):
            play(ax, rects, mp.RefineRiemann(rects, dx))
        for r, points in zip(rects, old, strict=True):
            np.testing.assert_allclose(r.points, points)
    assert graph is not None


@pytest.mark.parametrize("density", [False, True])
@pytest.mark.parametrize("histtype", ["bar", "step", "stepfilled"])
def test_rh1_exact_numpy_counts_and_inverse(density, histtype):
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(0, 12, 2))
    samples = np.array([0, 0.2, 1, 1.1, 2, 3, 4])
    weights = np.array([1, 2, 3, 1, 2, 1, 2])
    old, new = [0, 2, 4], [0, 1, 3, 4]
    hist = ax.hist(
        samples, bins=old, weights=weights, density=density, histtype=histtype
    )
    for edges in (new, old):
        play(ax, hist, mp.RebinHistogram(hist, edges))
        expected = np.histogram(samples, bins=edges, weights=weights, density=density)[
            0
        ]
        np.testing.assert_array_equal(hist.edges, edges)
        np.testing.assert_array_equal(hist.counts, expected)
        ax.set_x_range((-2, 6, 1))
        if histtype == "bar":
            for i, bar in enumerate(hist.bars):
                np.testing.assert_allclose(bounds(ax, bar)[:, 0], edges[i : i + 2])
                assert bounds(ax, bar)[1, 1] == pytest.approx(expected[i])
        else:
            xy = coords(ax, hist.outlines[0])
            for i, height in enumerate(expected):
                assert np.any(np.all(np.isclose(xy[:, :2], [edges[i], height]), axis=1))


@pytest.mark.parametrize("density", [False, True])
def test_rh2_union_pieces_conserve_mass(density):
    ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 10, 1))
    hist = ax.hist([0.1, 0.2, 1.5, 3.5], bins=[0, 2, 4], density=density)
    seen: list[float] = []
    frames: list[list[np.ndarray]] = []

    def record():
        boxes = sorted([bounds(ax, b) for b in leaves(hist)], key=lambda b: b[0, 0])
        frames.append(boxes)
        # Count pieces carry mass; density pieces carry mass divided by width.
        seen.append(
            sum(
                (b[1, 1] - b[0, 1]) * ((b[1, 0] - b[0, 0]) if density else 1)
                for b in boxes
            )
        )

    def construct(scene):
        scene.add(ax, hist)
        scene.play(mp.RebinHistogram(hist, [0, 1, 4], rate_func=linear))

    probe(construct, record)
    np.testing.assert_allclose(seen[1:], 1 if density else 4, atol=1e-8)
    expected_mass = (np.array([1.5, 1.5, 1]) + np.array([2, 2 / 3, 4 / 3])) / 2
    expected_height = (
        expected_mass / (4 * np.array([1, 1, 2])) if density else expected_mass
    )
    assert len(frames[3]) == 3
    for box, left, right, height in zip(
        frames[3], [0, 1, 2], [1, 2, 4], expected_height, strict=True
    ):
        np.testing.assert_allclose(box[:, 0], [left, right], atol=1e-8)
        assert box[1, 1] == pytest.approx(height)


def test_rh3_signed_weights_and_invalid_edges_rejected_atomically():
    ax = mp.Axes()
    hist = ax.hist([0.1, 0.8], bins=[0, 0.5, 1], weights=[1, -1])
    old = hist.counts.copy()
    with pytest.raises(ValueError, match="weight"):
        play(ax, hist, mp.RebinHistogram(hist, [0, 1]))
    np.testing.assert_array_equal(hist.counts, old)
    positive = ax.hist([0.1], bins=[0, 1])
    for edges in ([0, 0, 1], [1, 0], [0, float("nan")]):
        with pytest.raises(ValueError):
            play(ax, positive, mp.RebinHistogram(positive, edges))
        np.testing.assert_array_equal(positive.edges, [0, 1])


def voxel_fixture(axis="z"):
    ax = mp.ThreeDAxes(x_range=(0, 3, 1), y_range=(0, 3, 1), z_range=(0, 3, 1))
    shape = [1, 1, 1]
    shape["xyz".index(axis)] = 2
    block = ax.voxels(
        np.ones(shape, bool), shade=False, facecolors=RED, fill_opacity=0.6
    )
    return ax, block


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("direction", [-1, 1])
def test_sv1_active_occupancy_has_temporary_shared_faces(axis, direction):
    ax, block = voxel_fixture(axis)
    seen: list[list[np.ndarray]] = []

    def construct(scene):
        scene.add(ax)
        scene.play(
            mp.StackVoxels(
                block, axis=axis, direction=direction, lag_ratio=1, rate_func=linear
            )
        )

    probe(construct, lambda: seen.append([bounds(ax, f) for f in leaves(block)]))
    assert seen[0] == []
    assert len(seen[3]) == 6  # first layer complete, next starts at alpha .5
    k = "xyz".index(axis)
    assert min(b[0, k] for b in seen[3]) == pytest.approx(0 if direction == 1 else 1)
    assert len(leaves(block)) == 10
    # No face lies entirely on the internal plane after the second layer meets it.
    assert not any(np.allclose(coords(ax, f)[:, k], 1) for f in leaves(block))


def test_sv2_reverse_removal_reintroduction_and_canonical_finish():
    ax, block = voxel_fixture()
    face = block.at((0, 0, 0))[0]
    face.set_stroke(RED, width=4)
    before = tuple(block.updaters)
    counts: list[int] = []

    def construct(scene):
        scene.add(ax, block)
        scene.play(mp.StackVoxels(block, reverse=True, lag_ratio=1, rate_func=linear))
        assert block not in scene.mobjects
        scene.play(mp.StackVoxels(block, lag_ratio=1, rate_func=linear))
        assert block in scene.mobjects

    probe(construct, lambda: counts.append(len(leaves(block))))
    assert 6 in counts
    assert len(leaves(block)) == 10
    assert face in block.get_family()
    assert face.get_stroke_width() == 4
    assert tuple(block.updaters) == before
    ax.set_z_range((0, 4, 1))
    assert max(bounds(ax, f)[1, 2] for f in leaves(block)) == pytest.approx(2)


def test_sv3_remover_override_empty_and_invalid_options():
    ax, block = voxel_fixture()

    def construct(scene):
        scene.add(ax, block)
        scene.play(mp.StackVoxels(block, reverse=True, remover=False))
        assert block in scene.mobjects

    probe(construct, lambda: None)
    assert len(leaves(block)) == 10  # canonical restoration even when retained
    empty = ax.voxels(np.zeros((1, 1, 1), bool))
    play(ax, empty, mp.StackVoxels(empty))
    assert leaves(empty) == []
    for options in ({"axis": "q"}, {"direction": 0}, {"lag_ratio": -1}):
        with pytest.raises(ValueError):
            play(ax, block, mp.StackVoxels(block, **options))


def iso_fixture():
    ax = mp.ThreeDAxes(x_range=(0, 2, 1), y_range=(0, 2, 1), z_range=(0, 2, 1))
    x = np.indices((3, 3, 3), dtype=float)[0]
    return ax, ax.plot_isosurface(x, 0.25)


def test_si1_level_interpolates_in_data_and_commits_inverse():
    ax, surface = iso_fixture()
    seen: list[float] = []

    def record():
        points = np.concatenate([coords(ax, f) for f in leaves(surface)])
        assert np.ptp(points[:, 0]) < 1e-8
        seen.append(float(points[0, 0]))

    def construct(scene):
        scene.add(ax, surface)
        scene.play(mp.SweepIsovalue(surface, 1.75, rate_func=linear))

    probe(construct, record)
    np.testing.assert_allclose(seen, 0.25 + 1.5 * np.arange(6) / 6, atol=1e-8)
    assert bounds(ax, leaves(surface)[0])[0, 0] == pytest.approx(1.75)
    play(ax, surface, mp.SweepIsovalue(surface, 0.25))
    ax.set_x_range((0, 3, 1))
    assert bounds(ax, leaves(surface)[0])[0, 0] == pytest.approx(0.25)


def test_si2_empty_level_retires_all_old_triangles_and_returns():
    ax, surface = iso_fixture()
    old = leaves(surface)
    before = tuple(surface.updaters)
    play(ax, surface, mp.SweepIsovalue(surface, 3))
    assert leaves(surface) == []
    assert all(not f.has_points() for f in old if f not in surface.get_family())
    play(ax, surface, mp.SweepIsovalue(surface, 1))
    assert leaves(surface)
    assert tuple(surface.updaters) == before


def slice_fixture(tracked=True):
    ax = mp.ThreeDAxes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-3, 3, 1))
    surface = ax.plot_surface(lambda u, v: u * v / 2, (-2, 2), (-2, 2), resolution=4)
    tracker = ValueTracker(-1)
    profile_axes = mp.Axes(x_range=(-2, 2, 1), y_range=(-3, 3, 1))
    view = ax.slice_view(surface, x=tracker if tracked else -1, axes=profile_axes)
    return ax, surface, tracker, view


@pytest.mark.parametrize("tracked", [False, True])
def test_ss1_plane_cut_profile_share_each_frame_and_inverse(tracked):
    ax, surface, tracker, view = slice_fixture(tracked)
    seen: list[float] = []

    def record():
        wall, cut = coords(ax, view.plane), coords(ax, view.cut)
        profile = coords(view.axes, view.profile)
        c = float(wall[0, 0])
        np.testing.assert_allclose(wall[:, 0], c, atol=1e-8)
        np.testing.assert_allclose(cut[:, 0], c, atol=1e-8)
        np.testing.assert_allclose(cut[:, 2], c * cut[:, 1] / 2, atol=1e-8)
        np.testing.assert_allclose(profile[:, 1], c * profile[:, 0] / 2, atol=1e-8)
        seen.append(c)

    def construct(scene):
        scene.add(ax, surface, view)
        scene.play(mp.SweepSlice(view, 1, rate_func=linear))

    probe(construct, record)
    np.testing.assert_allclose(seen, -1 + 2 * np.arange(6) / 6, atol=1e-8)
    assert coords(ax, view.plane)[0, 0] == pytest.approx(1)
    play(ax, view, mp.SweepSlice(view, -1))
    if tracked:
        assert tracker.get_value() == pytest.approx(-1)
        tracker.set_value(0.5)

        def refresh(scene):
            scene.add(ax, surface, view)
            scene.wait(1 / 6)

        probe(refresh, lambda: None)
        assert coords(ax, view.cut)[0, 0] == pytest.approx(0.5)


@pytest.mark.parametrize(
    "name",
    ["RefineRiemann", "RebinHistogram", "StackVoxels", "SweepIsovalue", "SweepSlice"],
)
def test_tc1_public_exports_are_animation_classes(name):
    from importlib import import_module

    cls = getattr(mp, name)
    package = import_module("manim_plots.animations")
    module = (
        "helpers"
        if name == "RefineRiemann"
        else "bars"
        if name == "RebinHistogram"
        else "volumes"
    )
    assert cls is getattr(package, name)
    assert cls is getattr(import_module(f"manim_plots.animations.{module}"), name)
    assert issubclass(cls, Animation)


@pytest.mark.parametrize("family", ["riemann", "hist", "voxel", "iso", "slice"])
def test_tc2_repeated_alpha_is_deterministic_and_updaters_survive(family):
    if family == "riemann":
        ax, _held, artist = rectangles()
        animation = mp.RefineRiemann(artist, 0.5, rate_func=linear)
    elif family == "hist":
        ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 5, 1))
        artist = ax.hist([0.2, 1.2, 3.2], bins=[0, 2, 4])
        animation = mp.RebinHistogram(artist, [0, 1, 4], rate_func=linear)
    elif family == "voxel":
        ax, artist = voxel_fixture()
        animation = mp.StackVoxels(artist, rate_func=linear)
    elif family == "iso":
        ax, artist = iso_fixture()
        animation = mp.SweepIsovalue(artist, 1.75, rate_func=linear)
    else:
        ax, _held, _tracker, artist = slice_fixture()
        animation = mp.SweepSlice(artist, 1, rate_func=linear)
    before = tuple(artist.updaters)
    animation.begin()
    animation.interpolate(0.4)
    first = [m.points.copy() for m in leaves(artist)]
    animation.interpolate(0.8)
    animation.interpolate(0.4)
    second = [m.points.copy() for m in leaves(artist)]
    assert len(first) == len(second)
    for a, b in zip(first, second, strict=True):
        np.testing.assert_allclose(a, b, atol=1e-8)
    animation.finish()
    assert tuple(artist.updaters) == before
    assert ax is not None


def test_ss2_f915_dependencies_move_before_static_compilation():
    from manim import tempconfig

    from tests.mobjects.helpers import RUN

    ax, surface, tracker, view = slice_fixture()
    still_axes = mp.Axes()
    calls: list[float] = []

    def function(x):
        calls.append(float(x))
        return x

    still = still_axes.plot(function)
    moving: list[set[int]] = []
    ghosts: list[Any] = []

    class Shot(Scene):
        def begin_animations(self):
            super().begin_animations()
            moving.append({id(m) for m in self.moving_mobjects})

        def update_to_time(self, t):
            super().update_to_time(t)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            ghosts.extend(
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            )

        def construct(self):
            self.add(still_axes, still, ax, surface, view)  # Manim moves the suffix
            calls.clear()
            self.play(mp.SweepSlice(view, 1))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    for part in (view.plane, view.cut, view.profile):
        assert id(part) in moving[0]
    assert id(still) not in moving[0]
    assert calls == []
    assert ghosts == []
    assert tracker.get_value() == pytest.approx(1)


def test_tc3_concurrent_mapping_uses_current_frame_and_duplicate_writers_fail():
    ax, block = voxel_fixture()
    errors: list[float] = []

    def construct(scene):
        scene.add(ax, block)
        scene.play(
            mp.StackVoxels(block, lag_ratio=1, rate_func=linear),
            ax.animate(rate_func=linear).set_x_range((0, 5, 1)),
        )

    def record():
        for face in leaves(block):
            p = coords(ax, face)
            errors.append(float(np.max(np.abs(p[:, 0] - np.round(p[:, 0])))))

    probe(construct, record)
    assert errors and max(errors) < 1e-8
    iax, surface = iso_fixture()

    def conflict(scene):
        scene.add(iax, surface)
        scene.play(mp.SweepIsovalue(surface, 1), mp.SweepIsovalue(surface, 1.5))

    with pytest.raises(ValueError, match=r"(?i)(writer|conflict|simultaneous)"):
        probe(conflict, lambda: None)


def test_rr4_lag_orders_parent_windows():
    ax, graph, rects = rectangles()
    animation = mp.RefineRiemann(rects, 0.5, lag_ratio=1, rate_func=linear)
    animation.begin()
    animation.interpolate(0.25)
    # Two parent windows: progress .5 then 0.
    heights = [-1.1, -0.85, -0.1, -0.1]
    for rect, height in zip(rects, heights, strict=True):
        np.testing.assert_allclose(
            bounds(ax, rect)[:, 1], sorted([0, height]), atol=1e-8
        )
    animation.finish()
    assert graph is not None


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
@pytest.mark.parametrize("cumulative", [False, True, -1])
def test_rh4_dataset_options_and_styles_survive(orientation, cumulative):
    ax = mp.Axes(x_range=(-1, 15, 1), y_range=(-1, 15, 1))
    datasets = [[0.1, 0.2, 1.5, 3.5], [0.5, 2.5]]
    hist = ax.hist(
        datasets,
        bins=[0, 2, 4],
        stacked=True,
        bottom=1,
        orientation=orientation,
        cumulative=cumulative,
        color=[RED, RED],
        fill_opacity=0.4,
    )
    play(ax, hist, mp.RebinHistogram(hist, [0, 1, 3, 4]))
    expected = np.array([np.histogram(d, bins=[0, 1, 3, 4])[0] for d in datasets])
    if cumulative:
        expected = (
            np.cumsum(expected[:, ::-1], axis=1)[:, ::-1]
            if cumulative == -1
            else np.cumsum(expected, axis=1)
        )
    np.testing.assert_array_equal(hist.counts, expected)
    for j, bars in enumerate(hist.bars):
        for i, bar in enumerate(bars):
            box = bounds(ax, bar)
            k = 1 if orientation == "vertical" else 0
            bottom = 1 + expected[:j, i].sum()
            np.testing.assert_allclose(box[:, k], [bottom, bottom + expected[j, i]])
            assert bar.get_fill_opacity() == pytest.approx(0.4)
            assert bar.get_fill_color() == RED


def test_rh5_f915_linked_colorbar_and_canonical_mapping():
    from manim import tempconfig

    from tests.mobjects.helpers import RUN

    ax = mp.Axes(x_range=(0, 4, 1), y_range=(0, 6, 1))
    hist = ax.hist([0.1, 0.2, 0.3, 1.2, 3.5], bins=[0, 2, 4], color_by="count")
    bar = ax.colorbar(hist)
    moving: list[set[int]] = []
    ranges: list[tuple[float, float]] = []

    class Shot(Scene):
        def begin_animations(self):
            super().begin_animations()
            moving.append({id(m) for m in self.moving_mobjects})

        def update_to_time(self, t):
            super().update_to_time(t)
            ranges.append(tuple(bar.y_range[:2]))
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            assert not any(
                id(m) not in alive and m.has_points() for m in self.moving_mobjects
            )

        def construct(self):
            self.add(ax, hist, bar)
            self.play(mp.RebinHistogram(hist, [0, 1, 3, 4], rate_func=linear))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert id(bar) in moving[0] or id(bar.axis.line) in moving[0]
    assert any(r != ranges[0] for r in ranges[1:])
    assert tuple(bar.y_range[:2]) == pytest.approx((1, 3))
    for face, value in zip(hist.bars, [3, 1, 1], strict=True):
        from manim import ManimColor

        np.testing.assert_allclose(
            ManimColor(face.get_fill_color()).to_rgb(),
            mp.colormaps["viridis"]((value - 1) / 2),
            atol=2 / 255,
        )


def test_si3_disconnected_components_merge_from_retained_samples():
    ax = mp.ThreeDAxes(x_range=(0, 4, 1), y_range=(0, 2, 1), z_range=(0, 2, 1))
    calls: list[int] = []

    def field(x, y, z):
        calls.append(1)
        return np.minimum((x - 1) ** 2, (x - 3) ** 2) + (y - 1) ** 2 + (z - 1) ** 2

    surface = ax.plot_isosurface(field, 0.25, resolution=4)
    calls.clear()
    play(ax, surface, mp.SweepIsovalue(surface, 1.25))
    assert calls == []
    points = np.concatenate([coords(ax, f) for f in leaves(surface)])
    # At y=z=1, the sampled field is [1,0,1,0,1]; level 1.25 bridges x=2.
    assert np.any(np.isclose(points[:, 0], 2))
    assert points[:, 0].min() >= -1e-8
    play(ax, surface, mp.SweepIsovalue(surface, 0.25))
    points = np.concatenate([coords(ax, f) for f in leaves(surface)])
    assert not np.any(np.isclose(points[:, 0], 2))


@pytest.mark.parametrize("coordinate", ["x", "y", "z"])
def test_ss3_bare_slice_keeps_binding_and_can_leave_domain(coordinate):
    ax = mp.ThreeDAxes(x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-2, 2, 1))
    surface = ax.plot_surface(lambda u, v: u + v, (-1, 1), (-1, 1), resolution=4)
    tracker = ValueTracker(0)
    cut = surface.slice(**{coordinate: tracker})
    play(ax, cut, mp.SweepSlice(cut, 0.5))
    assert tracker.get_value() == pytest.approx(0.5)
    points = np.concatenate([coords(ax, f) for f in leaves(cut)])
    np.testing.assert_allclose(points[:, "xyz".index(coordinate)], 0.5, atol=1e-7)
    np.testing.assert_allclose(points[:, 2], points[:, 0] + points[:, 1], atol=1e-7)
    play(ax, cut, mp.SweepSlice(cut, 3))
    assert leaves(cut) == []
    play(ax, cut, mp.SweepSlice(cut, 0))
    assert leaves(cut)


def test_si4_invalid_level_is_atomic_and_surface_styles_survive():
    ax, surface = iso_fixture()
    surface.set_fill(RED, opacity=0.4)
    old = [f.points.copy() for f in leaves(surface)]
    for level in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            play(ax, surface, mp.SweepIsovalue(surface, level))
        for face, points in zip(leaves(surface), old, strict=True):
            np.testing.assert_array_equal(face.points, points)
    play(ax, surface, mp.SweepIsovalue(surface, 1.75))
    for face in leaves(surface):
        assert face.get_fill_opacity() == pytest.approx(0.4)


def test_ss4_styles_identity_and_invalid_stop_are_atomic():
    ax, surface, tracker, view = slice_fixture()
    parts = list(view)
    view.plane.set_fill(opacity=0.2)
    view.cut.set_stroke(width=7)
    view.profile.set_stroke(width=5)
    before = [tuple(p.updaters) for p in parts]
    for stop in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            play(ax, view, mp.SweepSlice(view, stop))
        assert tracker.get_value() == -1
    play(ax, view, mp.SweepSlice(view, 1))
    assert list(view) == parts
    assert view.plane.get_fill_opacity() == pytest.approx(0.2)
    assert view.cut.get_stroke_width() == 7
    assert view.profile.get_stroke_width() == 5
    assert [tuple(p.updaters) for p in parts] == before
    assert surface is not None


def test_rr5_parent_styles_reach_children():
    ax, graph, rects = rectangles()
    rects[0].set_fill(RED, opacity=0.3)
    rects[0].set_stroke(RED, width=5)
    play(ax, rects, mp.RefineRiemann(rects, 0.5))
    for child in list(rects)[:2]:
        assert child.get_fill_opacity() == pytest.approx(0.3)
        assert child.get_stroke_width() == 5
        assert child.get_fill_color() == RED
    assert graph is not None


def test_sv4_default_lag_opacity_and_sparse_layers():
    ax = mp.ThreeDAxes(x_range=(0, 2, 1), y_range=(0, 2, 1), z_range=(0, 4, 1))
    occupancy = np.array([[[True, False, True]]])
    block = ax.voxels(occupancy, facecolors=RED, shade=False, fill_opacity=0.6)
    animation = mp.StackVoxels(block, rate_func=linear)
    animation.begin()
    animation.interpolate(0.5)
    # Two occupied layers, default lag=.1: p0=.55, p1=.45.
    for key, opacity in [((0, 0, 0), 0.33), ((0, 0, 2), 0.27)]:
        assert len(block.at(key)) == 6
        for face in block.at(key):
            assert face.get_fill_opacity() == pytest.approx(opacity)
            assert face.get_fill_color() == RED
    animation.finish()
    assert len(leaves(block)) == 12


def test_si5_f915_no_retired_triangles_in_moving_list():
    from manim import tempconfig

    from tests.mobjects.helpers import RUN

    ax, surface = iso_fixture()
    checked: list[bool] = []

    class Shot(Scene):
        def update_to_time(self, t):
            super().update_to_time(t)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            checked.append(True)
            assert not any(
                id(m) not in alive and m.has_points() for m in self.moving_mobjects
            )

        def construct(self):
            self.add(ax, surface)
            self.play(mp.SweepIsovalue(surface, 3, rate_func=linear))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert checked
    assert leaves(surface) == []


def test_rr6_callable_parent_order_overrides_data_order():
    ax, graph, rects = rectangles()
    animation = mp.RefineRiemann(
        rects, 0.5, lag_ratio=1, order=lambda interval: -interval[0], rate_func=linear
    )
    animation.begin()
    animation.interpolate(0.25)
    for rect, height in zip(rects, [-1.1, -1.1, -0.1, 0.15], strict=True):
        np.testing.assert_allclose(
            bounds(ax, rect)[:, 1], sorted([0, height]), atol=1e-8
        )
    animation.finish()
    assert graph is not None
