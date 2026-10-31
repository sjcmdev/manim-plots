"""Task 43 spatial construction: independent data-coordinate frame oracles."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, cast

import numpy as np
import pytest
from manim import (
    RED,
    Scene,
    ThreeDScene,
    ValueTracker,
    linear,
    tempconfig,
    there_and_back,
)

import manim_plots as mp
from tests.mobjects.helpers import RUN, probe

FAMILIES = [
    ("field", "GrowField"),
    ("stems", "GrowStems"),
    ("wire", "RevealWireframe"),
    ("waterfall", "RevealWaterfall"),
    ("surface", "SweepSurface"),
    ("polar", "SweepPolar"),
    ("inset", "OpenInset"),
]


def axes3() -> Any:
    return mp.ThreeDAxes(x_range=(-2, 4, 1), y_range=(-2, 4, 1), z_range=(-2, 6, 1))


def fixture(kind: str) -> tuple[Any, Any]:
    ax = axes3()
    if kind == "field":
        return ax, ax.get_vector_field(
            lambda p: np.array([1.0, 0.0, 0.0]),
            x_range=(0, 1, 1),
            y_range=(0, 0, 1),
            z_range=(0, 0, 1),
            length_func=lambda n: 0.5,
        )
    if kind == "stems":
        return ax, ax.stem([0, 1], [0, 1], [3, -1], bottom=1)
    if kind == "wire":
        return ax, ax.plot_wireframe(
            lambda u, v: u + v, (0, 2), (0, 2), resolution=(1, 1)
        )
    if kind == "waterfall":
        return ax, ax.waterfall([0, 2], [[1, 3], [2, 4]], [0, 1])
    if kind == "surface":
        return ax, ax.plot_surface(
            lambda u, v: u + v, (0, 2), (0, 2), resolution=(2, 2)
        )
    if kind == "polar":
        polar = mp.PolarPlane(radius_max=2, azimuth_units=None, azimuth_step=4)
        polar.add_coordinates(r_values=[], a_values=[0, 0.25, 0.5, 0.75])
        return polar, polar
    parent = mp.Axes(x_range=(0, 4, 1), y_range=(0, 4, 1))
    line = parent.line([1, 2], [1, 2])
    inset = parent.inset((0.6, 0.6, 0.3, 0.3), (1, 2, 0.5), (1, 2, 0.5), mirror=[line])
    # Retain the weakly registered source for the duration of this fixture.
    cast(Any, inset).source_line = line
    return parent, inset


def anchors(mob: Any) -> np.ndarray:
    points = np.asarray(mob.points)
    return np.vstack((points[::4], points[-1:]))


def coords(ax: Any, mob: Any) -> np.ndarray:
    return np.array([ax.p2c(p) for p in anchors(mob)])


def visible(mob: Any) -> bool:
    return any(
        m.has_points() and (m.get_stroke_opacity() > 0 or m.get_fill_opacity() > 0)
        for m in mob.family_members_with_points()
    )


def snapshot(mob: Any) -> list[tuple[Any, np.ndarray, Any, Any, Any]]:
    return [
        (
            m,
            np.array(m.points, copy=True),
            m.get_color(),
            m.get_fill_opacity(),
            m.get_stroke_opacity(),
        )
        for m in mob.family_members_with_points()
    ]


def assert_snapshot(saved: list[tuple[Any, np.ndarray, Any, Any, Any]]) -> None:
    for m, points, color, fill, stroke in saved:
        np.testing.assert_allclose(m.points, points, atol=1e-7)
        assert m.get_color() == color
        assert m.get_fill_opacity() == pytest.approx(fill)
        assert m.get_stroke_opacity() == pytest.approx(stroke)


def at(animation: Any, alpha: float) -> None:
    animation.interpolate(alpha)


def test_gf1_tails_direction_length_colour_and_lag():
    ax = mp.Axes(x_range=(-2, 4, 1), y_range=(-2, 2, 1))
    field = ax.get_vector_field(
        lambda p: np.array([1.0, 0.0, 0.0]),
        x_range=(0, 1, 1),
        y_range=(0, 0.1, 1),
        length_func=lambda n: 0.6,
        opacity=0.4,
    )
    animation = cast(Any, mp).GrowField(field, lag_ratio=1, rate_func=linear)
    colors = [a.get_color() for a in field.arrows]
    animation.begin()
    for alpha in (0, 0.25, 0.5, 0.75, 1):
        at(animation, alpha)
        for i, arrow in enumerate(field.arrows):
            p = np.clip(2 * alpha - i, 0, 1)
            tail = ax.c2p(i, 0)
            if p > 0:
                np.testing.assert_allclose(arrow.points[0], tail, atol=1e-7)
                distance = np.linalg.norm(arrow.get_all_points() - tail, axis=1).max()
                assert distance == pytest.approx(0.6 * p, abs=1e-6)
                assert arrow.get_color() == colors[i]
                assert arrow.get_stroke_opacity() == pytest.approx(0.4)
                points = arrow.get_all_points()
                far = points[np.argmax(np.linalg.norm(points - tail, axis=1))]
                direction = ax.c2p(i + 1, 0) - tail
                direction /= np.linalg.norm(direction)
                np.testing.assert_allclose(far, tail + 0.6 * p * direction, atol=1e-6)
            else:
                assert not visible(arrow) or np.allclose(arrow.get_all_points(), tail)
    animation.finish()


@pytest.mark.parametrize("orientation", ["x", "y", "z"])
def test_gs1_signed_stems_and_markers_follow_the_current_end(orientation):
    ax = axes3()
    points = np.array([[0, 0, 3], [1, 1, -1], [1, 1, 1]], float)
    stems = ax.stem(*points.T, bottom=1, orientation=orientation)
    baseline = np.array(stems.baseline.points, copy=True)
    animation = cast(Any, mp).GrowStems(stems, lag_ratio=0, rate_func=linear)
    animation.begin()
    axis = "xyz".index(orientation)
    for alpha in (0.25, 0.5, 1):
        at(animation, alpha)
        np.testing.assert_allclose(stems.baseline.points, baseline)
        for i, point in enumerate(points):
            base = point.copy()
            base[axis] = 1
            end = base + alpha * (point - base)
            np.testing.assert_allclose(
                coords(ax, stems.stemlines[i])[[0, -1]], [base, end], atol=1e-7
            )
            np.testing.assert_allclose(
                stems.markers[i].get_center(), ax.c2p(*end), atol=1e-7
            )
    animation.finish()


def test_rw1_families_and_parameter_direction_are_configurable():
    ax, wire = fixture("wire")
    animation = cast(Any, mp).RevealWireframe(
        wire, families=("v", "u"), lag_ratio=1, rate_func=linear
    )
    animation.begin()
    # Four lines: v=0, v=2, u=0, u=2; at 1/8 only first is half drawn.
    at(animation, 0.125)
    np.testing.assert_allclose(
        coords(ax, wire.v_lines[0])[[0, -1]], [[0, 0, 0], [1, 0, 1]], atol=1e-6
    )
    assert not visible(wire.u_lines[0])
    at(animation, 0.5)
    np.testing.assert_allclose(coords(ax, wire.v_lines[1])[-1], [2, 2, 4], atol=1e-6)
    animation.finish()


@pytest.mark.parametrize("fill", [False, True])
def test_wf1_curve_front_and_fill_close_at_the_same_abscissa(fill):
    ax = axes3()
    waterfall = ax.waterfall([0, 2], [[1, 3], [2, 4]], [0, 1], fill=fill)
    animation = cast(Any, mp).RevealWaterfall(waterfall, lag_ratio=1, rate_func=linear)
    animation.begin()
    at(animation, 0.25)
    np.testing.assert_allclose(coords(ax, waterfall.lines[0])[-1], [1, 0, 2], atol=1e-6)
    assert not visible(waterfall.lines[1])
    polygon = waterfall.fills[0]
    if fill:
        assert polygon is not None
        data = coords(ax, polygon)
        assert data[:, 0].max() == pytest.approx(1)
        assert data[:, 2].min() == pytest.approx(-2)  # viewport floor
        assert any(np.allclose(p, [1, 0, 2]) for p in data)
        assert any(np.allclose(p, [1, 0, -2]) for p in data)
    else:
        assert polygon is None
    animation.finish()


@pytest.mark.parametrize("axis,direction", [("u", 1), ("v", -1)])
def test_ss1_cells_are_trimmed_at_the_parameter_front(axis, direction):
    ax, surface = fixture("surface")
    animation = cast(Any, mp).SweepSurface(
        surface, axis=axis, direction=direction, rate_func=linear
    )
    animation.begin()
    at(animation, 0.375)
    dim = 0 if axis == "u" else 1
    points = np.vstack([coords(ax, f) for f in surface.faces if f.has_points()])
    assert len(points) > 0
    np.testing.assert_allclose(points[:, 2], points[:, 0] + points[:, 1], atol=1e-7)
    if direction == 1:
        assert points[:, dim].max() == pytest.approx(0.75)
        assert points[:, dim].min() == pytest.approx(0)
    else:
        assert points[:, dim].min() == pytest.approx(1.25)
        assert points[:, dim].max() == pytest.approx(2)
    animation.finish()


def test_sp1_angular_front_reveals_rings_and_reached_spokes():
    ax, _ = fixture("polar")
    animation = cast(Any, mp).SweepPolar(
        ax, start_angle=0, angle=np.pi * 2, lag_ratio=0, rate_func=linear
    )
    animation.begin()
    at(animation, 0.25)
    circle = ax.circles.at(1)
    data = np.array([ax.p2c(p) for p in anchors(circle)])
    np.testing.assert_allclose(data[:, 0] ** 2 + data[:, 1] ** 2, 1, atol=1e-6)
    assert data[:, 0].min() >= -1e-6 and data[:, 1].min() >= -1e-6
    np.testing.assert_allclose(data[-1, :2], [0, 1], atol=1e-6)
    assert visible(ax.spokes.at(0))
    assert not visible(ax.spokes.at(np.pi))
    assert visible(ax.coordinate_labels[1][0])
    assert not visible(ax.coordinate_labels[1][2])
    animation.finish()


def test_oi1_expansion_uses_separate_parent_and_inset_maps():
    parent, inset = fixture("inset")
    animation = cast(Any, mp).OpenInset(inset, lag_ratio=0, rate_func=linear)
    animation.begin()
    for alpha in (0.25, 0.5, 0.75):
        at(animation, alpha)
        lo, hi = parent.c2p(0, 0), parent.c2p(4, 4)
        origin = parent.c2p(1, 1)
        target = lo + np.array([0.6, 0.6, 0]) * (hi - lo)
        expected_lo = (1 - alpha) * origin + alpha * target
        expected_size = (1 - alpha) * (parent.c2p(2, 2) - origin)
        expected_size += alpha * np.array([0.3, 0.3, 0]) * (hi - lo)
        np.testing.assert_allclose(inset.c2p(1, 1), expected_lo, atol=1e-6)
        np.testing.assert_allclose(
            inset.c2p(2, 2), expected_lo + expected_size, atol=1e-6
        )
        mirror = inset.mirrored[0]
        np.testing.assert_allclose(mirror.points[0], inset.c2p(1, 1), atol=1e-6)
        np.testing.assert_allclose(mirror.points[-1], inset.c2p(2, 2), atol=1e-6)
        np.testing.assert_allclose(inset.zoom_box.points[0], origin, atol=1e-6)
    animation.finish()


def removal(kind: str, name: str) -> None:
    ax, artist = fixture(kind)
    artist.set_color(RED)
    saved = snapshot(artist)
    before = [(m, list(m.updaters)) for m in artist.get_family()]
    animation_type = getattr(mp, name)

    def construct(scene: Scene) -> None:
        scene.add(ax, artist)
        scene.play(animation_type(artist, reverse=True, rate_func=linear))
        assert artist not in scene.mobjects
        assert_snapshot(saved)
        scene.play(animation_type(artist, rate_func=linear))
        assert artist in scene.mobjects
        assert_snapshot(saved)
        scene.play(animation_type(artist, reverse=True, remover=False))
        assert artist in scene.mobjects

    probe(construct, lambda: None)
    for mob, updaters in before:
        assert mob.updaters == updaters


def canonical(kind: str, name: str) -> None:
    ax, artist = fixture(kind)
    saved = snapshot(artist)
    before = [(m, list(m.updaters)) for m in artist.get_family()]

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(getattr(mp, name)(artist))
        assert artist in scene.mobjects

    probe(construct, lambda: None)
    assert_snapshot(saved)
    ax.shift(np.array([0.4, 0.2, 0]))
    ax.set_x_range((-3, 5, 1))
    if kind == "stems":
        np.testing.assert_allclose(artist.stemlines[0].points[-1], ax.c2p(0, 0, 3))
    elif kind == "wire":
        np.testing.assert_allclose(artist.u_lines[0].points[-1], ax.c2p(0, 2, 2))
    elif kind == "waterfall":
        np.testing.assert_allclose(artist.lines[0].points[-1], ax.c2p(2, 0, 3))
    elif kind == "surface":
        points = np.vstack([coords(ax, f) for f in artist.faces if f.has_points()])
        np.testing.assert_allclose(points[:, 2], points[:, 0] + points[:, 1], atol=1e-6)
        assert points[:, 0].max() == pytest.approx(2)
    elif kind == "field":
        np.testing.assert_allclose(artist.arrows[0].points[0], ax.c2p(0, 0, 0))
    elif kind == "polar":
        points = coords(ax, artist.circles.at(1))
        np.testing.assert_allclose(points[:, 0] ** 2 + points[:, 1] ** 2, 1, atol=1e-6)
        np.testing.assert_allclose(points[:, :2].min(axis=0), [-1, -1], atol=1e-6)
        np.testing.assert_allclose(points[:, :2].max(axis=0), [1, 1], atol=1e-6)
    else:
        lo, hi = ax.c2p(-3, 0), ax.c2p(5, 4)
        np.testing.assert_allclose(
            artist.c2p(1, 1), lo + np.array([0.6, 0.6, 0]) * (hi - lo), atol=1e-6
        )
    for mob, updaters in before:
        assert mob.updaters == updaters


def test_gf2_reverse_removal_and_reintroduction():
    removal("field", "GrowField")


def test_gs2_reverse_removal_and_reintroduction():
    removal("stems", "GrowStems")


def test_rw2_reverse_removal_and_reintroduction():
    removal("wire", "RevealWireframe")


def test_wf2_reverse_removal_and_reintroduction():
    removal("waterfall", "RevealWaterfall")


def test_ss2_reverse_removal_and_reintroduction():
    removal("surface", "SweepSurface")


def test_sp2_reverse_removal_and_reintroduction():
    removal("polar", "SweepPolar")


def test_oi2_close_inset_removal_and_reintroduction():
    removal("inset", "OpenInset")
    parent, inset = fixture("inset")
    close = cast(Any, mp).CloseInset

    def construct(scene: Scene) -> None:
        scene.add(parent, inset, *inset.mirrored)
        scene.play(close(inset))
        assert inset not in scene.mobjects
        assert all(m not in scene.mobjects for m in inset.mirrored)
        scene.play(cast(Any, mp).OpenInset(inset))
        assert inset in scene.mobjects

    probe(construct, lambda: None)


def test_gf3_canonical_finish():
    canonical("field", "GrowField")


def test_gs3_canonical_finish():
    canonical("stems", "GrowStems")


def test_rw3_canonical_finish():
    canonical("wire", "RevealWireframe")


def test_wf3_canonical_finish():
    canonical("waterfall", "RevealWaterfall")


def test_ss3_canonical_finish():
    canonical("surface", "SweepSurface")


def test_sp3_canonical_finish():
    canonical("polar", "SweepPolar")


def test_oi3_canonical_finish():
    canonical("inset", "OpenInset")


@pytest.mark.parametrize("kind,name", FAMILIES)
@pytest.mark.parametrize("rate", [linear, there_and_back])
def test_sc1_repeated_alpha_has_identical_geometry_and_styles(kind, name, rate):
    _, artist = fixture(kind)
    options = {} if kind == "surface" else {"lag_ratio": 0}
    animation = getattr(mp, name)(artist, rate_func=rate, **options)
    animation.begin()
    at(animation, 0.2)
    saved = snapshot(artist)
    at(animation, 0.5)
    at(animation, 0.8 if rate is there_and_back else 0.2)
    assert_snapshot(saved)
    assert {id(m) for m in artist.family_members_with_points()} == {
        id(m) for m, *_ in saved
    }
    animation.finish()


@pytest.mark.parametrize("kind,name", FAMILIES[:5])
def test_sc2_range_change_and_camera_move_use_this_frames_mapping(kind, name):
    ax, artist = fixture(kind)
    progress = ValueTracker(0)
    seen: list[float] = []

    class Shot(ThreeDScene):
        def construct(self) -> None:
            self.add(ax, artist, progress)
            self.move_camera(
                phi=0.7,
                theta=0.4,
                added_anims=[
                    getattr(mp, name)(
                        artist,
                        rate_func=linear,
                        **({} if kind == "surface" else {"lag_ratio": 0}),
                    ),
                    ax.animate(rate_func=linear).set_x_range((-3, 5, 1)),
                    cast(Any, progress.animate)(rate_func=linear).set_value(1),
                ],
                run_time=1,
            )

        def update_to_time(self, time: float) -> None:
            super().update_to_time(time)
            p = progress.get_value()
            seen.append(p)
            if p <= 0:
                return
            if kind == "stems":
                np.testing.assert_allclose(
                    artist.stemlines[0].points[-1], ax.c2p(0, 0, 1 + 2 * p), atol=1e-6
                )
            elif kind == "field":
                np.testing.assert_allclose(
                    artist.arrows[0].points[0], ax.c2p(0, 0, 0), atol=1e-6
                )
                pts = artist.arrows[0].get_all_points()
                distance = np.linalg.norm(pts - ax.c2p(0, 0, 0), axis=1).max()
                assert distance == pytest.approx(0.5 * p, abs=1e-6)
            elif kind == "wire":
                np.testing.assert_allclose(
                    artist.u_lines[0].points[-1], ax.c2p(0, 2 * p, 2 * p), atol=1e-6
                )
            elif kind == "waterfall":
                np.testing.assert_allclose(
                    artist.lines[0].points[-1], ax.c2p(2 * p, 0, 1 + 2 * p), atol=1e-6
                )
            else:
                pts = np.vstack([coords(ax, f) for f in artist.faces if f.has_points()])
                assert pts[:, 0].max() == pytest.approx(2 * p, abs=1e-6)
                np.testing.assert_allclose(pts[:, 2], pts[:, 0] + pts[:, 1], atol=1e-6)

    with tempconfig(RUN):
        Shot().render()
    assert any(0 < p < 1 for p in seen)


def test_oi4_f915_mirrors_and_connectors_move_but_unrelated_plot_stays_static():
    parent, inset = fixture("inset")
    still = mp.Axes().shift(np.array([-3, -2, 0]))
    static_line = still.line([0, 1], [0, 1])
    state: list[tuple[bool, bool, bool]] = []
    progress = ValueTracker(0)

    class Shot(Scene):
        def begin_animations(self) -> None:
            super().begin_animations()
            moving = {id(m) for m in self.moving_mobjects}

            def involved(mob: Any) -> bool:
                return any(id(m) in moving for m in mob.family_members_with_points())

            state.append(
                (
                    involved(inset.mirrored[0]),
                    involved(inset.connectors),
                    involved(static_line),
                )
            )

        def construct(self) -> None:
            self.add(still, static_line, parent, inset, *inset.mirrored, progress)
            self.play(
                cast(Any, mp).OpenInset(inset, lag_ratio=0, rate_func=linear),
                parent.animate(rate_func=linear).set_x_range((0, 5, 1)),
                cast(Any, progress.animate)(rate_func=linear).set_value(1),
            )

        def update_to_time(self, time: float) -> None:
            super().update_to_time(time)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            assert not [
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            ]
            for line in inset.connectors:
                if not line.has_points():
                    continue
                box = anchors(inset.zoom_box)
                corners = np.array(
                    [inset.c2p(x, y) for x, y in [(1, 1), (2, 1), (2, 2), (1, 2)]]
                )
                assert np.linalg.norm(box - line.points[0], axis=1).min() < 1e-6
                assert np.linalg.norm(corners - line.points[-1], axis=1).min() < 1e-6
            if progress.get_value() > 0:
                np.testing.assert_allclose(
                    inset.mirrored[0].points[-1], inset.c2p(2, 2), atol=1e-6
                )

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert state == [(True, True, False)]


@pytest.mark.parametrize("kind,name", [("polar", "SweepPolar"), ("inset", "OpenInset")])
def test_sc3_system_entrances_declare_f915_and_preserve_static_sampling(kind, name):
    ax, artist = fixture(kind)
    calls: list[float] = []
    unrelated = mp.Axes()

    def function(x):
        calls.append(float(x))
        return x

    static = unrelated.plot(function)
    count = len(calls)
    states: list[tuple[bool, bool]] = []

    class Shot(Scene):
        def begin_animations(self) -> None:
            super().begin_animations()
            moving = {id(m) for m in self.moving_mobjects}
            states.append(
                (
                    any(id(m) in moving for m in artist.family_members_with_points()),
                    any(id(m) in moving for m in static.family_members_with_points()),
                )
            )

        def construct(self) -> None:
            self.add(unrelated, static, ax)
            self.play(getattr(mp, name)(artist))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert states == [(True, False)]
    assert len(calls) == count


def test_ss4_triangle_front_is_a_data_halfspace():
    ax = axes3()
    surface = ax.plot_trisurf([0, 2, 0], [0, 0, 2], [0, 2, 2], triangles=[[0, 1, 2]])
    animation = cast(Any, mp).SweepSurface(surface, axis="x", rate_func=linear)
    animation.begin()
    at(animation, 0.5)
    points = coords(ax, surface.faces[0])
    expected = np.array([[0, 0, 0], [1, 0, 1], [1, 1, 2], [0, 2, 2]])
    for p in expected:
        assert np.linalg.norm(points - p, axis=1).min() < 1e-6
    assert points[:, 0].max() == pytest.approx(1)
    animation.finish()


def test_ss5_reversed_intervals_and_holes_do_not_bridge_missing_cells():
    ax = axes3()
    surface = ax.plot_surface(
        lambda u, v: np.where(u < 1, np.nan, u + v),
        (2, 0),
        (0, 2),
        resolution=(2, 2),
    )
    animation = cast(Any, mp).SweepSurface(surface, rate_func=linear)
    animation.begin()
    at(animation, 0.25)
    points = np.vstack([coords(ax, f) for f in surface.faces if f.has_points()])
    assert points[:, 0].min() == pytest.approx(1.5)
    assert points[:, 0].max() == pytest.approx(2)
    at(animation, 0.9)
    points = np.vstack([coords(ax, f) for f in surface.faces if f.has_points()])
    assert points[:, 0].min() >= 1 - 1e-7
    animation.finish()


@pytest.mark.parametrize(
    "name,kind,options",
    [
        ("GrowField", "field", {"order": "unknown"}),
        ("GrowStems", "stems", {"lag_ratio": -1}),
        ("RevealWireframe", "wire", {"families": ("unknown",)}),
        ("RevealWaterfall", "waterfall", {"lag_ratio": -1}),
        ("SweepSurface", "surface", {"axis": "x"}),
        ("SweepSurface", "surface", {"direction": 0}),
        ("SweepPolar", "polar", {"angle": float("nan")}),
        ("OpenInset", "inset", {"lag_ratio": -1}),
        ("GrowField", "field", {"lag_ratio": float("nan")}),
        ("SweepPolar", "polar", {"start_angle": float("inf")}),
        ("SweepPolar", "polar", {"lag_ratio": float("inf")}),
    ],
)
def test_sc4_invalid_options_fail_before_changing_geometry(name, kind, options):
    _, artist = fixture(kind)
    saved = snapshot(artist)
    animation_type = getattr(mp, name)
    with pytest.raises(ValueError):
        animation = animation_type(artist, **options)
        animation.begin()
    assert_snapshot(saved)


@pytest.mark.parametrize("order", ["data", "x", "y", "z", "value", "callable", "ties"])
def test_gf4_order_is_stable_and_resolved_at_begin(order):
    ax = axes3()
    field = ax.get_vector_field(
        lambda p, sign=1: np.array([2 + sign * p[0], 0.0, 0.0]),
        x_range=(0, 1, 1),
        y_range=(0, 0, 1),
        z_range=(0, 0, 1),
        length_func=lambda n: 0.5,
    )
    key = (lambda tail, vector: -tail[0]) if order == "callable" else order
    if order == "ties":

        def key(tail, vector):
            return 0

    animation = cast(Any, mp).GrowField(field, order=key, lag_ratio=1, rate_func=linear)
    field.set_parameters(sign=-1)
    animation.begin()
    at(animation, 0.25)
    first = 1 if order in ("value", "callable") else 0
    tail = ax.c2p(first, 0, 0)
    points = field.arrows[first].get_all_points()
    assert np.linalg.norm(points - tail, axis=1).max() == pytest.approx(0.25, abs=1e-6)
    other = field.arrows[1 - first]
    if other.has_points():
        assert np.linalg.norm(
            other.get_all_points() - ax.c2p(1 - first, 0, 0), axis=1
        ).max() < 1e-6 or not visible(other)
    animation.finish()


def test_gf4_flat_zero_and_invalid_vectors_keep_canonical_semantics():
    ax = axes3()
    with pytest.warns(mp.ManimPlotsWarning, match="invalid"):
        field = ax.get_vector_field(
            lambda p: np.array([0.0 if p[0] == 0 else np.nan, 0.0, 0.0]),
            x_range=(0, 1, 1),
            y_range=(0, 0, 1),
            z_range=(0, 0, 1),
        )
    animation = cast(Any, mp).GrowField(field, lag_ratio=0, rate_func=linear)
    animation.begin()
    for alpha in (0, 0.5, 1):
        at(animation, alpha)
        assert all(np.isfinite(m.points).all() for m in field.get_family())
    animation.finish()


@pytest.mark.parametrize("bad", [0.0, np.nan, np.inf])
def test_gf5_solid_field_constructs_with_degenerate_vectors_and_grows_the_others(bad):
    ax = axes3()
    warning = (
        pytest.warns(mp.ManimPlotsWarning, match="invalid")
        if not np.isfinite(bad)
        else nullcontext()
    )
    with warning:
        field = ax.get_vector_field(
            lambda p: np.array([bad if p[0] == 0 else 1.0, 0.0, 0.0]),
            x_range=(0, 1, 1),
            y_range=(0, 0, 1),
            z_range=(0, 0, 1),
            arrow="3d",
            length_func=lambda n: 0.5,
        )
    assert len(field.arrows) == 2

    def assert_degenerate() -> None:
        arrow = field.arrows[0]
        assert all(np.isfinite(m.points).all() for m in arrow.get_family())
        if visible(arrow):
            points = arrow.get_all_points()
            assert np.linalg.norm(points - ax.c2p(0, 0, 0), axis=1).max() < 1e-6

    assert_degenerate()
    animation = cast(Any, mp).GrowField(field, lag_ratio=0, rate_func=linear)
    animation.begin()
    tail = ax.c2p(1, 0, 0)
    direction = ax.c2p(2, 0, 0) - tail
    direction /= np.linalg.norm(direction)
    for alpha in (0.25, 0.5, 1):
        at(animation, alpha)
        assert_degenerate()
        arrow = field.arrows[1]
        np.testing.assert_allclose(arrow.get_start(), tail, atol=1e-6)
        np.testing.assert_allclose(
            arrow.get_end(), tail + alpha * 0.5 * direction, atol=1e-6
        )
    animation.finish()
    assert_degenerate()
    np.testing.assert_allclose(
        field.arrows[1].get_end(), tail + 0.5 * direction, atol=1e-6
    )


def test_ss6_height_tracker_and_linked_colorbar_keep_canonical_colours():
    ax = axes3()
    height = ValueTracker(1)
    surface = ax.plot_surface(
        lambda u, v, h: h + 0 * u + 0 * v,
        (0, 2),
        (0, 2),
        h=height,
        resolution=(2, 2),
        colorscale="viridis",
        vmin=0,
        vmax=4,
    )
    bar = ax.colorbar(surface)
    face = surface.faces.at((0, 0))
    face.set_color(RED).set_fill(opacity=0.3)
    original_bar = snapshot(bar)
    progress = ValueTracker(0)
    seen: list[float] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, surface, bar, height, progress)
        scene.play(
            cast(Any, mp).SweepSurface(surface, rate_func=linear),
            cast(Any, height.animate)(rate_func=linear).set_value(3),
            cast(Any, progress.animate)(rate_func=linear).set_value(1),
        )

    def record() -> None:
        p = progress.get_value()
        if p <= 0:
            return
        seen.append(p)
        for cell in surface.faces:
            if cell.has_points():
                np.testing.assert_allclose(
                    coords(ax, cell)[:, 2], height.get_value(), atol=1e-6
                )
        for cell in surface.faces:
            if cell is not face and cell.has_points():
                np.testing.assert_allclose(
                    cell.get_fill_color().to_rgb(),
                    mp.colormaps["viridis"](height.get_value() / 4),
                    atol=1.5 / 255,
                )
        assert face.get_fill_color() == RED
        assert face.get_fill_opacity() == pytest.approx(0.3)
        mapping = surface.color_mapping
        assert mapping is not None
        assert mapping.vmin == pytest.approx(0)
        assert mapping.vmax == pytest.approx(4)
        assert_snapshot(original_bar)

    probe(construct, record)
    assert seen
    height.set_value(2)
    np.testing.assert_allclose(coords(ax, face)[:, 2], 2, atol=1e-6)
    assert face.get_fill_color() == RED


@pytest.mark.parametrize("polar_class", ["PolarPlane", "PolarAxes"])
@pytest.mark.parametrize("angle", [-np.pi * 2, -np.pi])
def test_sp4_negative_sweep_and_offset_follow_source_angles(polar_class, angle):
    ax: Any
    if polar_class == "PolarPlane":
        ax = mp.PolarPlane(
            radius_max=2,
            azimuth_units=None,
            azimuth_step=4,
            azimuth_offset=0.3,
            azimuth_direction="CW",
        )
    else:
        ax = mp.PolarAxes(
            (0, 2, 1),
            azimuth_units=None,
            azimuth_step=4,
            azimuth_offset=0.3,
            azimuth_direction="CW",
            r_axis_config={"include_numbers": False},
            azimuth_axis_config={"include_numbers": False},
        )
    saved = snapshot(ax)
    animation = cast(Any, mp).SweepPolar(
        ax, start_angle=np.pi / 2, angle=angle, lag_ratio=0, rate_func=linear
    )
    animation.begin()
    at(animation, 0.375)
    circle = ax.circles.at(1)
    start_angle, end_angle = np.pi / 2, np.pi / 2 + 0.375 * angle
    np.testing.assert_allclose(
        circle.points[0], ax.polar_to_point(1, start_angle), atol=1e-6
    )
    np.testing.assert_allclose(
        circle.points[-1], ax.polar_to_point(1, end_angle), atol=1e-6
    )
    animation.finish()
    assert_snapshot(saved)


def test_sp5_radial_range_changes_map_the_front_without_truncating_a_plot():
    ax = mp.PolarAxes(
        (0, 2, 1),
        azimuth_units=None,
        azimuth_step=4,
        r_axis_config={"include_numbers": False},
        azimuth_axis_config={"include_numbers": False},
    )
    curve = ax.plot_polar_graph(lambda theta: 1, theta_range=(0, np.pi))
    progress = ValueTracker(0)
    seen: list[float] = []

    def construct(scene: Scene) -> None:
        scene.add(ax, curve, progress)
        scene.play(
            cast(Any, mp).SweepPolar(ax, rate_func=linear),
            cast(Any, ax.animate)(rate_func=linear).set_r_range((0, 3, 1)),
            cast(Any, progress.animate)(rate_func=linear).set_value(1),
        )

    def record() -> None:
        p = progress.get_value()
        if p <= 0:
            return
        seen.append(p)
        np.testing.assert_allclose(
            ax.circles.at(1).points[-1], ax.polar_to_point(1, p * 2 * np.pi), atol=1e-6
        )
        np.testing.assert_allclose(
            curve.points[-1], ax.polar_to_point(1, np.pi), atol=1e-6
        )

    probe(construct, record)
    assert seen


def test_oi5_empty_inset_opens_while_parent_moves():
    parent = mp.Axes(x_range=(0, 4, 1), y_range=(0, 4, 1))
    inset = parent.inset(
        (0.6, 0.6, 0.3, 0.3), (1, 2, 0.5), (1, 2, 0.5), connectors=False
    )
    updaters = list(inset.updaters)
    progress = ValueTracker(0)
    seen: list[float] = []

    def construct(scene: Scene) -> None:
        scene.add(parent, inset, progress)
        scene.play(
            cast(Any, mp).OpenInset(inset, lag_ratio=0, rate_func=linear),
            parent.animate.shift(np.array([1, 0.5, 0])),
            cast(Any, progress.animate)(rate_func=linear).set_value(1),
        )

    def record() -> None:
        p = progress.get_value()
        seen.append(p)
        lo, hi = parent.c2p(0, 0), parent.c2p(4, 4)
        origin = parent.c2p(1, 1)
        target = lo + np.array([0.6, 0.6, 0]) * (hi - lo)
        np.testing.assert_allclose(
            inset.c2p(1, 1), (1 - p) * origin + p * target, atol=1e-6
        )

    probe(construct, record)
    assert any(0 < p < 1 for p in seen)
    assert len(inset.connectors) == 0 and inset.mirrored == []
    assert inset.updaters == updaters


@pytest.mark.parametrize("kind,name", FAMILIES)
def test_sc5_reverse_halfway_and_explicit_forward_removal(kind, name):
    ax, artist = fixture(kind)
    options = {} if kind == "surface" else {"lag_ratio": 0}
    animation = getattr(mp, name)(artist, reverse=True, rate_func=linear, **options)
    animation.begin()
    at(animation, 0.25)  # backwards progress is 0.75
    if kind == "field":
        tail = ax.c2p(0, 0, 0)
        distance = np.linalg.norm(
            artist.arrows[0].get_all_points() - tail, axis=1
        ).max()
        assert distance == pytest.approx(0.375, abs=1e-6)
    elif kind == "stems":
        np.testing.assert_allclose(artist.stemlines[0].points[-1], ax.c2p(0, 0, 2.5))
    elif kind == "wire":
        np.testing.assert_allclose(artist.u_lines[0].points[-1], ax.c2p(0, 1.5, 1.5))
    elif kind == "waterfall":
        np.testing.assert_allclose(artist.lines[0].points[-1], ax.c2p(1.5, 0, 2.5))
    elif kind == "surface":
        points = np.vstack([coords(ax, f) for f in artist.faces if f.has_points()])
        assert points[:, 0].max() == pytest.approx(1.5)
    elif kind == "polar":
        np.testing.assert_allclose(
            artist.circles.at(1).points[-1],
            ax.polar_to_point(1, 1.5 * np.pi),
            atol=1e-6,
        )
    else:
        start = ax.c2p(1, 1)
        lo, hi = ax.c2p(0, 0), ax.c2p(4, 4)
        target = lo + np.array([0.6, 0.6, 0]) * (hi - lo)
        np.testing.assert_allclose(artist.c2p(1, 1), 0.25 * start + 0.75 * target)
    animation.finish()

    def construct(scene: Scene) -> None:
        scene.add(ax)
        scene.play(getattr(mp, name)(artist, remover=True))
        assert artist not in scene.mobjects

    probe(construct, lambda: None)


def test_sc6_exports_and_native_animation_types():
    from importlib import import_module

    from manim import Animation

    modules = {
        "GrowField": "fields",
        "GrowStems": "surfaces",
        "RevealWireframe": "surfaces",
        "RevealWaterfall": "surfaces",
        "SweepSurface": "surfaces",
        "SweepPolar": "axes",
        "OpenInset": "decorations",
        "CloseInset": "decorations",
    }
    for name, module in modules.items():
        public = getattr(mp, name)  # Missing names fail here, never during collection.
        assert issubclass(public, Animation)
        package = import_module("manim_plots.animations")
        family = import_module(f"manim_plots.animations.{module}")
        assert public is getattr(package, name) is getattr(family, name)


@pytest.mark.parametrize("arrow", ["flat", "3d"])
def test_gf4_nonzero_3d_arrows_grow_with_the_same_mapped_direction(arrow):
    ax = axes3()
    vector = np.array([0.0, 1.0, 1.0])
    field = ax.get_vector_field(
        lambda p: vector,
        x_range=(0, 0, 1),
        y_range=(0, 0, 1),
        z_range=(0, 0, 1),
        arrow=arrow,
        length_func=lambda n: 0.8,
    )
    animation = cast(Any, mp).GrowField(field, lag_ratio=0, rate_func=linear)
    animation.begin()
    at(animation, 0.5)
    tail = ax.c2p(0, 0, 0)
    direction = ax.c2p(*vector) - tail
    direction /= np.linalg.norm(direction)
    part = field.arrows[0]
    if arrow == "3d":
        np.testing.assert_allclose(part.get_start(), tail, atol=1e-6)
        np.testing.assert_allclose(part.get_end(), tail + 0.4 * direction, atol=1e-6)
    else:
        points = part.get_all_points()
        far = points[np.argmax(np.linalg.norm(points - tail, axis=1))]
        np.testing.assert_allclose(part.points[0], tail, atol=1e-6)
        np.testing.assert_allclose(far, tail + 0.4 * direction, atol=1e-6)
    animation.finish()


@pytest.mark.parametrize("kind,name", FAMILIES[:4])
def test_sc5_reverse_unwinds_the_last_lag_window_first(kind, name):
    ax, artist = fixture(kind)
    count = 4 if kind == "wire" else 2
    animation = getattr(mp, name)(artist, lag_ratio=1, reverse=True, rate_func=linear)
    animation.begin()
    at(animation, 1 / (2 * count))
    if kind == "field":
        for i, length in enumerate([0.5, 0.25]):
            tail = ax.c2p(i, 0, 0)
            points = artist.arrows[i].get_all_points()
            assert np.linalg.norm(points - tail, axis=1).max() == pytest.approx(
                length, abs=1e-6
            )
    elif kind == "stems":
        np.testing.assert_allclose(artist.stemlines[0].points[-1], ax.c2p(0, 0, 3))
        np.testing.assert_allclose(artist.stemlines[1].points[-1], ax.c2p(1, 1, 0))
    elif kind == "wire":
        np.testing.assert_allclose(artist.u_lines[0].points[-1], ax.c2p(0, 2, 2))
        np.testing.assert_allclose(artist.v_lines[1].points[-1], ax.c2p(1, 2, 3))
    else:
        np.testing.assert_allclose(artist.lines[0].points[-1], ax.c2p(2, 0, 3))
        np.testing.assert_allclose(artist.lines[1].points[-1], ax.c2p(1, 1, 3))
    animation.finish()


def test_sc4_triangle_rejects_a_parameter_axis_without_mutating_faces():
    ax = axes3()
    surface = ax.plot_trisurf([0, 2, 0], [0, 0, 2], [0, 2, 2], triangles=[[0, 1, 2]])
    saved = snapshot(surface)
    animation_type = cast(Any, mp).SweepSurface
    with pytest.raises(ValueError):
        animation = animation_type(surface, axis="u")
        animation.begin()
    assert_snapshot(saved)


@pytest.mark.parametrize("kind", ["parametric", "grid", "revolution"])
def test_ss1_sweeps_retained_parameters_instead_of_world_coordinates(kind):
    ax = axes3()
    if kind == "parametric":
        surface = ax.plot_parametric_surface(
            lambda u, v: np.array([v, u, u + v]), (0, 2), (0, 2), resolution=(2, 2)
        )
    elif kind == "grid":
        # u is grid-row fraction, not the unequal physical distance between rows.
        u, v = np.meshgrid([0, 0.5, 2], [0, 1, 2], indexing="ij")
        surface = ax.surface(v, u, u + v)
    else:
        surface = ax.plot_surface_of_revolution(
            lambda u: 1 + 0 * u, (0, 2), angle_range=(0, np.pi / 2), resolution=(2, 2)
        )
    keys = [surface.faces.at((i, j)) for i in range(2) for j in range(2)]
    animation = cast(Any, mp).SweepSurface(surface, axis="u", rate_func=linear)
    animation.begin()
    at(animation, 0.25)
    points = np.vstack([coords(ax, f) for f in surface.faces if f.has_points()])
    if kind == "revolution":
        assert points[:, 2].max() == pytest.approx(0.5)
        assert points[:, 2].min() == pytest.approx(0)
    else:
        assert points[:, 1].max() == pytest.approx(0.25 if kind == "grid" else 0.5)
        assert points[:, 1].min() == pytest.approx(0)
        np.testing.assert_allclose(points[:, 2], points[:, 0] + points[:, 1], atol=1e-6)
    animation.finish()
    assert keys == [surface.faces.at((i, j)) for i in range(2) for j in range(2)]


def test_ss5_viewport_clipping_is_applied_after_the_parameter_restriction():
    ax = mp.ThreeDAxes(x_range=(0.5, 1.5, 0.5), y_range=(-1, 3, 1), z_range=(-1, 5, 1))
    surface = ax.plot_surface(lambda u, v: u + v, (0, 2), (0, 2), resolution=(2, 2))
    animation = cast(Any, mp).SweepSurface(surface, rate_func=linear)
    animation.begin()
    at(animation, 0.5)
    points = np.vstack([coords(ax, f) for f in surface.faces if f.has_points()])
    assert points[:, 0].min() == pytest.approx(0.5)
    assert points[:, 0].max() == pytest.approx(1)
    np.testing.assert_allclose(points[:, 2], points[:, 0] + points[:, 1], atol=1e-6)
    animation.finish()


def test_oi1_lag_boundaries_separate_box_expansion_and_content():
    parent, inset = fixture("inset")
    animation = cast(Any, mp).OpenInset(inset, lag_ratio=1, rate_func=linear)
    animation.begin()
    at(animation, 1 / 6)
    np.testing.assert_allclose(inset.c2p(1, 1), parent.c2p(1, 1), atol=1e-6)
    np.testing.assert_allclose(inset.c2p(2, 2), parent.c2p(2, 2), atol=1e-6)
    assert not visible(inset.mirrored[0])
    at(animation, 0.5)
    lo, hi = parent.c2p(0, 0), parent.c2p(4, 4)
    target = lo + np.array([0.6, 0.6, 0]) * (hi - lo)
    np.testing.assert_allclose(
        inset.c2p(1, 1), (parent.c2p(1, 1) + target) / 2, atol=1e-6
    )
    assert not visible(inset.mirrored[0])
    at(animation, 5 / 6)
    np.testing.assert_allclose(inset.c2p(1, 1), target, atol=1e-6)
    assert visible(inset.mirrored[0])
    animation.finish()
