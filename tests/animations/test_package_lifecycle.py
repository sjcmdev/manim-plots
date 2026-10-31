"""Task 40: package migration and the reversible animation lifecycle.

All new names are resolved inside tests. Missing package becomes AttributeError so
pre-implementation collection and helper failures remain distinguishable.
"""

from __future__ import annotations

import ast
import importlib
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from manim import (
    Animation,
    Dot,
    Scene,
    Square,
    Text,
    ValueTracker,
    linear,
    tempconfig,
    there_and_back,
)

import manim_plots as mp
from tests.mobjects.helpers import RUN, probe

FAMILIES = {
    "curves": ("TraceCurve", "ShowPoints", "Morph", "AppendData"),
    "axes": ("DrawAxes", "BuildAxes", "HighlightTick"),
    "bars": ("GrowBars", "ShrinkBars", "SortBars", "HighlightBar"),
    "fields": ("Flow",),
    "surfaces": ("GrowSurface", "ShrinkSurface"),
}
ENTRANCES = (
    "TraceCurve",
    "ShowPoints",
    "DrawAxes",
    "BuildAxes",
    "GrowBars",
    "GrowSurface",
)
ROOT = Path(__file__).parents[2]


def package() -> Any:
    try:
        return importlib.import_module("manim_plots.animations")
    except ModuleNotFoundError as exc:
        if exc.name != "manim_plots.animations":
            raise
        raise AttributeError("missing manim_plots.animations") from exc


def fixture(name: str) -> tuple[Any, Any]:
    ax: Any
    if name in {"GrowSurface", "ShrinkSurface"}:
        ax = mp.ThreeDAxes(x_range=(-1, 3, 1), y_range=(-1, 3, 1), z_range=(0, 8, 2))
        return ax, ax.plot_surface(lambda u, v: 2 + u + v, (0, 1), (0, 1), resolution=2)
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-2, 10, 2))
    if name == "ShowPoints":
        return ax, ax.scatter([0, 1, 2], [1, 3, 2])
    if name in {"GrowBars", "ShrinkBars", "SortBars", "HighlightBar"}:
        return ax, ax.bar([0, 1, 2], [2, 6, 4])
    if name in {"DrawAxes", "BuildAxes", "HighlightTick"}:
        return ax, ax
    return ax, ax.line([0, 1, 2], [1, 3, 2])


def state(mob: Any) -> list[tuple[np.ndarray, Any]]:
    return [
        (np.array(m.points, copy=True), deepcopy(m.get_style()))
        for m in mob.get_family()
        if hasattr(m, "get_style")
    ]


def assert_state(mob: Any, before: list[tuple[np.ndarray, Any]]) -> None:
    after = state(mob)
    assert len(after) == len(before)
    for (points, style), (old_points, old_style) in zip(after, before, strict=True):
        np.testing.assert_allclose(points, old_points, atol=1e-8)
        assert style.keys() == old_style.keys()
        for key in style:
            np.testing.assert_equal(style[key], old_style[key])


def drive(animation: Any, *alphas: float) -> None:
    animation.begin()
    for alpha in alphas:
        animation.interpolate(alpha)


def play(scene, ax, artist, animation, *extra):
    scene.add(ax, artist, *extra)
    scene.play(animation)


def existing(name: str) -> tuple[Any, Any, Any, list[Any]]:
    pkg = package()
    ax, artist = fixture(name)
    extra: list[Any] = []
    if name == "Morph":
        target = ax.line([0, 1, 2], [2, 4, 3])
        animation = pkg.Morph(artist, target)
        extra.append(target)
    elif name == "AppendData":
        animation = pkg.AppendData(artist, [3], [4])
    elif name == "HighlightTick":
        animation = pkg.HighlightTick(ax.x, 2)
    elif name == "HighlightBar":
        animation = pkg.HighlightBar(artist, 1)
    elif name == "Flow":
        field = ax.get_vector_field(
            lambda p: np.array([0.25, 0, 0]), x_range=(0, 1, 1), y_range=(0, 1, 1)
        )
        artist = Dot(ax.c2p(0, 1))
        extra.append(field)
        animation = pkg.Flow(field, artist)
    else:
        animation = getattr(pkg, name)(artist)
    return ax, artist, animation, extra


def test_pk1_exports_are_identical_classes():
    pkg = package()
    expected = {n for names in FAMILIES.values() for n in names}
    assert expected <= set(pkg.__all__)  # tasks 41-44 add their own names
    assert len(pkg.__all__) == len(set(pkg.__all__))
    old = importlib.import_module("manim_plots.mobjects.animations")
    for family, names in FAMILIES.items():
        module = importlib.import_module(f"manim_plots.animations.{family}")
        for name in names:
            cls = getattr(pkg, name)
            assert cls is getattr(mp, name) is getattr(module, name)
            assert issubclass(cls, Animation)
            assert cls.__module__ == module.__name__
            if family not in {"fields", "surfaces"}:
                assert cls is getattr(old, name)
    for family, name in (("fields", "Flow"), ("surfaces", "GrowSurface")):
        assert getattr(pkg, name) is getattr(
            importlib.import_module(f"manim_plots.mobjects.{family}"), name
        )


def test_pk2_layer_checker_recognises_animation_imports(monkeypatch):
    from tests import test_layers

    for source in (
        "import manim_plots.animations.curves",
        "from manim_plots.animations import TraceCurve",
        "from ..animations import TraceCurve",
        "from .. import animations",
    ):
        monkeypatch.setattr(
            test_layers, "tree", lambda path, source=source: ast.parse(source)
        )
        assert test_layers.forbidden_imports(Path("core.py")), source
    for path in (ROOT / "src/manim_plots/animations").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name != "manim_plots" for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "manim_plots" or node.level != 0


@pytest.mark.parametrize("name", ENTRANCES)
def test_lc1_canonical_finish_and_range_rederivation(name):
    cls = getattr(package(), name)
    ax, artist = fixture(name)
    before = state(artist)
    probe(lambda s: s.play(cls(artist)), lambda: None)
    assert_state(artist, before)
    ax.set_x_range((-2, 8, 2))
    if name == "TraceCurve":
        np.testing.assert_allclose(artist.points[-1], ax.c2p(2, 2), atol=1e-8)
    elif name == "ShowPoints":
        np.testing.assert_allclose(artist[1].get_center(), ax.c2p(1, 3), atol=1e-8)
    elif name == "GrowBars":
        d = np.array([ax.p2c(p) for p in artist[1].points[::4]])
        assert d[:, 1].max() == pytest.approx(6)
    elif name == "GrowSurface":
        for face in artist.faces:
            d = np.array([ax.p2c(p) for p in face.points[::4]])
            np.testing.assert_allclose(d[:, 2], 2 + d[:, 0] + d[:, 1], atol=1e-8)
    else:
        np.testing.assert_allclose(ax.x.ticks.at(2).get_center(), ax.c2p(2, 0))


@pytest.mark.parametrize("name", [n for ns in FAMILIES.values() for n in ns])
def test_lc2_no_animation_updater_and_binding_survives(name):
    ax, artist, animation, extra = existing(name)

    def sentinel(m, dt):
        pass

    artist.add_updater(sentinel)
    owners = [ax, artist, animation.mobject, *extra]
    if name in {"GrowSurface", "ShrinkSurface"}:
        owners.append(artist._driver)

    def resources():
        return {id(m): m for owner in owners for m in owner.get_family()}

    members = resources()
    before = {key: tuple(m.updaters) for key, m in members.items()}
    probe(lambda s: play(s, ax, artist, animation, *extra), lambda: None)
    for key, m in resources().items():
        assert tuple(m.updaters) == before.get(key, ())
    assert all(tuple(m.updaters) == before[key] for key, m in members.items())


@pytest.mark.parametrize("name", ENTRANCES)
@pytest.mark.parametrize(
    "reverse,remover", [(True, None), (True, False), (False, True)]
)
def test_rv1_removal_is_separate_from_reverse_and_reintroduction(
    name, reverse, remover
):
    cls = getattr(package(), name)
    ax, artist = fixture(name)
    before = state(artist)
    present: list[bool] = []

    def construct(scene):
        scene.add(ax, artist)
        scene.play(cls(artist, reverse=reverse, remover=remover))
        present.append(any(artist in top.get_family() for top in scene.mobjects))
        assert_state(artist, before)
        scene.play(cls(artist))
        present.append(any(artist in top.get_family() for top in scene.mobjects))

    probe(construct, lambda: None)
    assert present == [not (reverse if remover is None else remover), True]
    assert_state(artist, before)
    ax.set_x_range((-2, 8, 2))
    if name == "TraceCurve":
        np.testing.assert_allclose(artist.points[-1], ax.c2p(2, 2), atol=1e-8)
    elif name in {"ShowPoints", "GrowBars"}:
        np.testing.assert_allclose(artist[1].get_center(), ax.c2p(1, 3), atol=1e-8)
    elif name == "GrowSurface":
        for face in artist.faces:
            d = np.array([ax.p2c(p) for p in face.points[::4]])
            np.testing.assert_allclose(d[:, 2], 2 + d[:, 0] + d[:, 1], atol=1e-8)
    else:
        np.testing.assert_allclose(
            ax.x.ticks.at(2).get_center(), ax.c2p(2, 0), atol=1e-8
        )


@pytest.mark.parametrize(
    "name", ["TraceCurve", "ShowPoints", "GrowBars", "GrowSurface"]
)
def test_rv2_reverse_replays_the_data_schedule_backwards(name):
    cls = getattr(package(), name)
    ax, artist = fixture(name)
    a = cls(artist, reverse=True, remover=False, rate_func=linear)
    a.begin()
    for alpha in (0.0, 0.2, 0.5, 0.8, 1.0):
        a.interpolate(alpha)
        fraction = 1 - alpha
        if name == "TraceCurve":
            if fraction == 0:
                assert not artist.has_points()
            else:
                x = 2 * fraction
                y = 1 + 2 * x if x <= 1 else 4 - x
                np.testing.assert_allclose(artist.points[-1], ax.c2p(x, y), atol=1e-8)
        elif name == "ShowPoints":
            for i, marker in enumerate(artist):
                assert marker.get_fill_opacity() == pytest.approx(
                    np.clip(3 * fraction - i, 0, 1)
                )
        elif name == "GrowBars":
            for i, height in enumerate((2, 6, 4)):
                factor = np.clip(fraction * 1.1 - i * 0.05, 0, 1)
                d = np.array([ax.p2c(p) for p in artist[i].points[::4]])
                assert d[:, 1].max() == pytest.approx(height * factor)
        else:
            for face in artist.faces:
                d = np.array([ax.p2c(p) for p in face.points[::4]])
                np.testing.assert_allclose(
                    d[:, 2], fraction * (2 + d[:, 0] + d[:, 1]), atol=1e-8
                )
    a.finish()


def test_rv3_shrink_surface_alias_and_shrink_bars_unchanged():
    pkg = package()
    ax, surface = fixture("GrowSurface")
    before = state(surface)
    a = pkg.ShrinkSurface(surface, zdir="z", offset=1, rate_func=linear)
    drive(a, 0.5)
    for face in surface.faces:
        d = np.array([ax.p2c(p) for p in face.points[::4]])
        np.testing.assert_allclose(d[:, 2], 1 + 0.5 * (1 + d[:, 0] + d[:, 1]))
    a.finish()
    assert_state(surface, before)
    ax2, bars = fixture("GrowBars")
    b = pkg.ShrinkBars(bars, lag_ratio=0.2, rate_func=linear)
    drive(b, 0.5)
    for i, height in enumerate((2, 6, 4)):
        d = np.array([ax2.p2c(p) for p in bars[i].points[::4]])
        factor = 1 - np.clip(0.5 * 1.4 - i * 0.2, 0, 1)
        assert d[:, 1].max() == pytest.approx(height * factor)
    b.finish()


@pytest.mark.parametrize("name", (*ENTRANCES, "ShrinkBars", "ShrinkSurface"))
def test_lc3_nonmonotone_alpha_never_accumulates(name):
    cls = getattr(package(), name)
    _ax, artist = fixture(name)
    a = cls(artist, rate_func=there_and_back)
    drive(a, 0.2)
    before = state(artist)
    a.interpolate(0.5)
    a.interpolate(0.8)
    a.interpolate(0.2)
    assert_state(artist, before)
    a.finish()


def test_lc3_flow_returns_to_start_after_there_and_back():
    pkg = package()
    ax = mp.Axes(x_range=(0, 8), y_range=(-1, 2))
    field = ax.get_vector_field(
        lambda p: np.array([p[0], 0, 0]), x_range=(0, 1, 1), y_range=(0, 1, 1)
    )
    dot = Dot(ax.c2p(1, 0))
    start = dot.get_center().copy()
    animation = pkg.Flow(field, dot, rate_func=there_and_back)
    probe(lambda scene: play(scene, ax, dot, animation), lambda: None)
    assert np.linalg.norm(dot.get_center() - start) <= 1e-3


def test_lc4_concurrent_range_uses_current_mapping():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 5, 1))
    line = ax.line([0, 4], [0, 4])
    seen = []

    def construct(scene):
        scene.add(ax, line)
        scene.play(
            pkg.TraceCurve(line, pacing="parameter", rate_func=linear),
            cast(Any, ax.animate)(rate_func=linear).set_x_range((-1, 9, 1)),
        )

    def record():
        alpha = (ax.x_range[1] - 5) / 4
        seen.append(alpha)
        if len(line.points):
            np.testing.assert_allclose(
                line.points[-1], ax.c2p(4 * alpha, 4 * alpha), atol=1e-7
            )

    probe(construct, record)
    assert any(0 < a < 1 for a in seen)
    np.testing.assert_allclose(line.points[-1], ax.c2p(4, 4), atol=1e-8)


def test_lc5_two_data_writers_fail_without_committing():
    pkg = package()
    ax, line = fixture("TraceCurve")
    data = line.source.data.copy()

    def construct(scene):
        scene.add(ax, line)
        scene.play(pkg.AppendData(line, [3], [4]), pkg.AppendData(line, [4], [5]))

    with pytest.raises(ValueError, match=r"(?i)(writer|ownership|concurrent|already)"):
        probe(construct, lambda: None)
    np.testing.assert_array_equal(line.source.data, data)


def test_lc6_f915_autoscale_declares_dependents_and_excludes_still_system():
    pkg = package()
    ax = mp.NumberPlane(
        x_range=(0, 2, 1), y_range=(0, 3, 1), axis_config={"include_ticks": True}
    )
    ax.x.set_ticks([0, 1, 2])
    line = ax.line([0, 1], [0, 1])
    linked = ax.line([0, 1], [1, 2])
    still_ax = mp.Axes(x_range=(-1, 4, 1), y_range=(-1, 4, 1))
    still = still_ax.line([0, 1], [1, 0])
    moving = []
    ticks = []

    class Shot(Scene):
        def get_moving_mobjects(self, *animations):
            result = super().get_moving_mobjects(*animations)
            ids = {id(m) for top in result for m in top.get_family()}
            moving.append(ids)
            return result

        def update_to_time(self, t):
            super().update_to_time(t)
            ticks.append(ax.x.ticks.at(1).get_center().copy())

        def construct(self):
            self.add(still_ax, still, ax, linked, line)
            self.play(pkg.AppendData(line, [3, 6], [4, 8], autoscale=True))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert moving
    assert id(ax.x.line) in moving[0]
    assert id(linked) in moving[0]
    assert id(still) not in moving[0]
    assert not np.allclose(ticks[0], ticks[-1])
    np.testing.assert_allclose(linked.points[-1], ax.c2p(1, 2), atol=1e-8)


@pytest.mark.parametrize("name", ENTRANCES)
def test_lc6_f915_reveals_declare_only_their_affected_family(name):
    cls = getattr(package(), name)
    ax, artist = fixture(name)
    other_ax = mp.Axes()
    other = other_ax.line([0, 1], [1, 0])
    animation = cls(artist)
    with tempconfig(RUN):
        scene = Scene()
        scene.add(other_ax, other, ax, artist)
        moving = scene.get_moving_mobjects(animation)
    ids = {id(m) for top in moving for m in top.get_family()}
    drawable = {id(m) for m in artist.get_family() if m.has_points()}
    assert drawable <= ids
    assert id(other) not in ids


@pytest.mark.parametrize("name", [n for ns in FAMILIES.values() for n in ns])
def test_lc7_f918_static_functions_are_not_resampled(name):
    ax, artist, animation, extra = existing(name)
    calls = []

    def function(x):
        calls.append(1)
        return x * 0 + 1

    static = ax.plot(function, x_range=(0, 1))
    static.get_all_points()
    count = len(calls)
    probe(lambda s: play(s, ax, artist, animation, static, *extra), lambda: None)
    assert len(calls) == count


def test_lc8_lb1_retired_text_has_no_drawable_points():
    pkg = package()
    ax, line = fixture("TraceCurve")
    end = ax.end_label(line)
    violations = []

    class Shot(Scene):
        def update_to_time(self, t):
            super().update_to_time(t)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            violations.extend(
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            )

        def construct(self):
            self.add(ax, line, end)
            self.play(pkg.AppendData(line, [3, 4], [5, 8]))

    with tempconfig(RUN):
        Shot().render()
    assert violations == []


@pytest.mark.parametrize("pacing,endpoint", [("parameter", 0.75), ("arc_length", 1.5)])
def test_tc1_parameter_and_arc_length_are_distinct(pacing, endpoint):
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5), y_range=(-1, 4), x_length=6, y_length=5)
    line = ax.line([0, 1, 4], [0, 0, 0])
    a = pkg.TraceCurve(line, pacing=pacing, rate_func=linear)
    drive(a, 0.375)
    # Parameter is input index: .75 of segment 0; arc length is .375 * 4.
    np.testing.assert_allclose(line.points[-1], ax.c2p(endpoint, 0), atol=1e-8)
    a.finish()


def test_tc2_parametric_parameter_tracks_t_not_sample_count():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 10), y_range=(-1, 4))
    curve = ax.plot_parametric_curve(
        lambda t: np.array([t * t, t, 0]), t_range=(0, 3), use_smoothing=False
    )
    a = pkg.TraceCurve(curve, pacing="parameter", rate_func=linear)
    drive(a, 0.5)
    np.testing.assert_allclose(curve.points[-1], ax.c2p(2.25, 1.5), atol=0.02)
    a.finish()


def test_tc3_nan_gap_is_not_bridged_and_source_order_survives_reverse_points():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5), y_range=(-1, 5))
    with pytest.warns(mp.ManimPlotsWarning):
        line = ax.line([0, 1, np.nan, 3, 4], [0, 1, np.nan, 3, 4])
    line.reverse_points()
    before = state(line)
    a = pkg.TraceCurve(line, pacing="parameter", rate_func=linear)
    drive(a, 0.875)
    for cubic in line.points.reshape(-1, 4, 3):
        x = np.array([ax.p2c(p)[0] for p in cubic[[0, 3]]])
        assert not (x.min() <= 1 and x.max() >= 3)
    assert max(
        ax.p2c(p)[0] for p in [*line.points[::4], line.points[-1]]
    ) == pytest.approx(3.5)
    a.finish()
    assert_state(line, before)


@pytest.mark.parametrize(
    "order,indices",
    [("data", [0, 1, 2]), ("x", [1, 2, 0]), ("y", [2, 0, 1]), ("value", [1, 0, 2])],
)
def test_sp1_stable_orders_and_key(order, indices):
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5), y_range=(-1, 5))
    scatter = ax.scatter([3, 1, 1], [2, 3, 1], c=[2, 1, 3])
    marker_ids = [id(m) for m in scatter]
    data = scatter.source.data.copy()
    a = pkg.ShowPoints(scatter, order=order, rate_func=linear)
    drive(a, 0.5)
    for rank, index in enumerate(indices):
        assert scatter[index].get_fill_opacity() == pytest.approx(
            np.clip(1.5 - rank, 0, 1)
        )
    a.finish()
    b = pkg.ShowPoints(scatter, order=lambda row: -row[1], rate_func=linear)
    drive(b, 1 / 3)
    assert scatter[1].get_fill_opacity() == pytest.approx(1)
    assert scatter[0].get_fill_opacity() == pytest.approx(0)
    b.finish()
    assert [id(m) for m in scatter] == marker_ids
    np.testing.assert_array_equal(scatter.source.data, data)


def test_sp2_pop_scales_about_center_and_restores_custom_marker_style():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 4))
    scatter = ax.scatter([1], [2], marker=Square().set_fill(opacity=0.4))
    width = scatter[0].width
    a = pkg.ShowPoints(scatter, pop=True, rate_func=linear)
    drive(a, 0.5)
    assert scatter[0].width == pytest.approx(0.5 * width)
    np.testing.assert_allclose(scatter[0].get_center(), ax.c2p(1, 2), atol=1e-8)
    assert scatter[0].get_fill_opacity() == pytest.approx(0.2)
    a.finish()
    assert scatter[0].width == pytest.approx(width)
    assert scatter[0].get_fill_opacity() == pytest.approx(0.4)


def test_sp3_invalid_and_clipped_rows_stay_hidden():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 4))
    with pytest.warns(mp.ManimPlotsWarning):
        scatter = ax.scatter([0, 10, np.nan, 2], [1, 1, 1, 2])
    a = pkg.ShowPoints(scatter, order="x", pop=True, rate_func=linear)
    drive(a, 0.5)
    # A hidden marker keeps its points at zero opacity (the scatter convention).
    for i in (1, 2):
        assert scatter[i].get_fill_opacity() == 0
        assert scatter[i].get_stroke_opacity() == 0
    assert scatter[3].get_fill_opacity() == pytest.approx(1)
    a.finish()
    for i in (1, 2):
        assert scatter[i].get_fill_opacity() == 0
        assert scatter[i].get_stroke_opacity() == 0


@pytest.mark.parametrize("zdir", ["x", "y", "z"])
def test_sf1_growth_is_data_coordinate_interpolation(zdir):
    pkg = package()
    ax, surface = fixture("GrowSurface")
    a = pkg.GrowSurface(surface, zdir=zdir, offset=0, rate_func=linear)
    drive(a, 0.5)
    k = "xyz".index(zdir)
    for face in surface.faces:
        d = np.array([ax.p2c(p) for p in face.points[::4]])
        canonical = d.copy()
        canonical[:, k] *= 2
        np.testing.assert_allclose(
            canonical[:, 2], 2 + canonical[:, 0] + canonical[:, 1], atol=1e-8
        )
    a.finish()


def test_sf2_invalid_log_origin_rejected_before_mutation():
    pkg = package()
    ax = mp.ThreeDAxes(z_range=(1, 100), z_scale="log")
    surface = ax.plot_surface(lambda u, v: 10 + u + v, (0, 1), (0, 1), resolution=2)
    before = state(surface)
    with pytest.raises(ValueError, match=r"(?i)(offset|origin|domain|log)"):
        pkg.GrowSurface(surface, offset=0)
    assert_state(surface, before)


def test_ax1_unknown_stage_rejected_before_mutation():
    pkg = package()
    ax, _ = fixture("BuildAxes")
    before = state(ax)
    with pytest.raises(ValueError, match=r"(?i)stage"):
        pkg.BuildAxes(ax, stages=("lines", "unknown"))
    assert_state(ax, before)


def test_do1_native_recipe_page_has_executable_examples():
    package()
    import textwrap

    from tests.test_docs import BLOCK, page, test_do4_every_code_block_runs

    text = page("animations")
    for word in (
        "Create",
        "FadeIn",
        "Write",
        "ticks",
        "numbers",
        "grid",
        "end_label",
        "ValueTracker",
        "get_tangent_line",
    ):
        assert word in text
    matches = list(BLOCK.finditer(text))
    assert matches
    assert "animations" in page("index")
    for index, match in enumerate(matches):
        test_do4_every_code_block_runs(
            "animations", index, textwrap.dedent(match.group(1))
        )


@pytest.mark.parametrize("name", ["Morph", "AppendData", "SortBars", "Flow"])
def test_lc9_data_changes_commit_and_keep_their_mapping(name):
    ax, artist, animation, extra = existing(name)

    def construct(scene):
        play(scene, ax, artist, animation, *extra)

    probe(construct, lambda: None)
    if name == "Morph":
        np.testing.assert_allclose(artist.points[-1], ax.c2p(2, 3), atol=1e-8)
        ax.set_x_range((-2, 8, 2))
        np.testing.assert_allclose(artist.points[-1], ax.c2p(2, 3), atol=1e-8)
        np.testing.assert_allclose(extra[0].points[-1], ax.c2p(2, 3), atol=1e-8)
    elif name == "AppendData":
        np.testing.assert_array_equal(
            artist.source.data, [[0, 1], [1, 3], [2, 2], [3, 4]]
        )
        ax.set_x_range((-2, 8, 2))
        np.testing.assert_allclose(artist.points[-1], ax.c2p(3, 4), atol=1e-8)
    elif name == "SortBars":
        for i, height in enumerate((2, 4, 6)):
            d = np.array([ax.p2c(p) for p in artist[i].points[::4]])
            assert d[:, 0].mean() == pytest.approx(i)
            assert d[:, 1].max() == pytest.approx(height)
    else:
        np.testing.assert_allclose(artist.get_center(), ax.c2p(0.25, 1), atol=1e-6)


@pytest.mark.parametrize("name", ["HighlightTick", "HighlightBar"])
def test_lc10_emphasis_restores_original_styles_and_placement(name):
    pkg = package()
    ax, artist = fixture(name)
    target = ax.x.ticks.at(2) if name == "HighlightTick" else artist
    target.set_stroke(color="#124578", width=2, opacity=0.6)
    if name == "HighlightBar":
        artist[0].set_fill(opacity=0.35)
        artist[1].set_fill(opacity=0.7)
    before = state(target)
    animation = (
        pkg.HighlightTick(ax.x, 2, scale_factor=1.8, color="#ff0000")
        if name == "HighlightTick"
        else pkg.HighlightBar(artist, 1, dim_opacity=0.1)
    )
    probe(lambda s: play(s, ax, artist, animation), lambda: None)
    assert_state(target, before)


@pytest.mark.parametrize(
    "name", ["Morph", "AppendData", "SortBars", "HighlightTick", "HighlightBar"]
)
def test_lc3_existing_effects_revisit_the_same_fraction(name):
    ax, artist, animation, extra = existing(name)
    animation.rate_func = there_and_back
    drive(animation, 0.2)
    target = ax.x.ticks.at(2) if name == "HighlightTick" else artist
    before = state(target)
    animation.interpolate(0.5)
    animation.interpolate(0.8)
    animation.interpolate(0.2)
    assert_state(target, before)
    animation.finish()
    assert extra is not None


@pytest.mark.parametrize(
    "name", ["TraceCurve", "ShowPoints", "GrowBars", "GrowSurface"]
)
def test_lc4_reveal_and_range_share_the_current_frame(name):
    cls = getattr(package(), name)
    ax, artist = fixture(name)
    fractions = []
    clock = ValueTracker(0)

    def construct(scene):
        scene.add(ax, artist, clock)
        scene.play(
            cls(artist, rate_func=linear),
            ax.animate(rate_func=linear).set_x_range((-2, 8, 2)),
            cast(Any, clock.animate)(rate_func=linear).set_value(1),
        )

    def record():
        alpha = clock.get_value()
        fractions.append(alpha)
        if name == "ShowPoints":
            for marker, coords in zip(artist, [(0, 1), (1, 3), (2, 2)], strict=True):
                if marker.has_points():
                    np.testing.assert_allclose(
                        marker.get_center(), ax.c2p(*coords), atol=1e-7
                    )
        elif name == "GrowBars":
            for i, height in enumerate((2, 6, 4)):
                d = np.array([ax.p2c(p) for p in artist[i].points[::4]])
                factor = np.clip(alpha * 1.1 - i * 0.05, 0, 1)
                assert d[:, 1].max() == pytest.approx(height * factor, abs=1e-7)
        elif name == "GrowSurface":
            for face in artist.faces:
                d = np.array([ax.p2c(p) for p in face.points[::4]])
                np.testing.assert_allclose(
                    d[:, 2], alpha * (2 + d[:, 0] + d[:, 1]), atol=1e-7
                )
        elif len(artist.points):
            endpoint = 2 * alpha
            y_end = 1 + 2 * endpoint if endpoint <= 1 else 4 - endpoint
            np.testing.assert_allclose(
                artist.points[-1], ax.c2p(endpoint, y_end), atol=1e-7
            )

    probe(construct, record)
    assert any(0 < f < 1 for f in fractions)


def test_lc11_tracker_binding_survives_reverse_and_reintroduction():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 10))
    height = ValueTracker(2)
    curve = ax.plot(lambda x, h: h * x, x_range=(0, 2), h=height)

    def construct(scene):
        scene.add(ax, curve)
        scene.play(pkg.TraceCurve(curve, reverse=True))
        height.set_value(3)
        scene.play(pkg.TraceCurve(curve))
        scene.play(height.animate.set_value(4))

    probe(construct, lambda: None)
    np.testing.assert_allclose(curve.points[-1], ax.c2p(2, 8), atol=1e-7)
    assert curve.parameters["h"].value == pytest.approx(4)


def test_rv4_reverse_bars_unwinds_lag_windows_from_last_to_first():
    pkg = package()
    ax, bars = fixture("GrowBars")
    a = pkg.GrowBars(bars, lag_ratio=0.2, reverse=True, remover=False, rate_func=linear)
    a.begin()
    for alpha in (0, 1 / 7, 0.5, 6 / 7, 1):
        a.interpolate(alpha)
        for i, height in enumerate((2, 6, 4)):
            factor = np.clip((1 - alpha) * 1.4 - i * 0.2, 0, 1)
            d = np.array([ax.p2c(p) for p in bars[i].points[::4]])
            assert d[:, 1].max() == pytest.approx(height * factor)
    a.finish()


@pytest.mark.parametrize("horizontal", [False, True])
def test_ba1_growth_preserves_signed_heights_bases_and_canonical_colours(horizontal):
    pkg = package()
    ax = mp.Axes(x_range=(-5, 10), y_range=(-5, 10))
    bars = (
        ax.barh([0, 1], [-3, 4], left=2)
        if horizontal
        else ax.bar([0, 1], [-3, 4], bottom=2, c="height", vmin=-3, vmax=4)
    )
    colours = [b.get_fill_color() for b in bars]
    orthogonal = 1 if horizontal else 0
    widths = [np.ptp([ax.p2c(p)[orthogonal] for p in b.points[::4]]) for b in bars]
    a = pkg.GrowBars(bars, lag_ratio=0, rate_func=linear)
    drive(a, 0.5)
    k = 0 if horizontal else 1
    for i, height in enumerate((-3, 4)):
        d = np.array([ax.p2c(p) for p in bars[i].points[::4]])
        np.testing.assert_allclose(
            [d[:, k].min(), d[:, k].max()], sorted([2, 2 + height / 2])
        )
        assert bars[i].get_fill_color() == colours[i]
        assert np.ptp(d[:, orthogonal]) == pytest.approx(widths[i])
    a.finish()


def test_tc4_invalid_pacing_rejected_without_mutation():
    pkg = package()
    ax, curve = fixture("TraceCurve")
    before = state(curve)
    with pytest.raises(ValueError, match=r"(?i)pac"):
        pkg.TraceCurve(curve, pacing="samples")
    assert_state(curve, before)
    assert ax is not None


@pytest.mark.parametrize("reverse_range", [False, True])
def test_tc2_multiturn_curve_reveals_by_parameter_even_in_reversed_interval(
    reverse_range,
):
    pkg = package()
    ax = mp.Axes(x_range=(-4, 4), y_range=(-4, 4))
    interval = (4 * np.pi, 0) if reverse_range else (0, 4 * np.pi)
    curve = ax.plot_parametric_curve(
        lambda t: np.array([(1 + t / 10) * np.cos(t), (1 + t / 10) * np.sin(t), 0]),
        t_range=interval,
        use_smoothing=False,
    )
    a = pkg.TraceCurve(curve, pacing="parameter", rate_func=linear)
    drive(a, 0.25)
    t = interval[0] + 0.25 * (interval[1] - interval[0])
    np.testing.assert_allclose(
        curve.points[-1],
        ax.c2p((1 + t / 10) * np.cos(t), (1 + t / 10) * np.sin(t)),
        atol=0.04,
    )
    a.finish()


def test_sp4_lag_window_and_opacity_channels_are_independent():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 4))
    scatter = ax.scatter([0, 1, 2], [1, 2, 1])
    for marker in scatter:
        marker.set_fill(opacity=0.4)
        marker.set_stroke(opacity=0.6)
        marker.set_stroke(opacity=0.2, background=True)
    a = pkg.ShowPoints(scatter, lag_ratio=0.2, rate_func=linear)
    drive(a, 0.5)
    for i, marker in enumerate(scatter):
        factor = np.clip(0.5 * 1.4 - i * 0.2, 0, 1)
        assert marker.get_fill_opacity() == pytest.approx(0.4 * factor)
        assert marker.get_stroke_opacity() == pytest.approx(0.6 * factor)
        assert marker.get_stroke_opacity(background=True) == pytest.approx(0.2 * factor)
    a.finish()


@pytest.mark.parametrize("kind", ["triangles", "holes", "reversed"])
def test_sf3_growth_keeps_topology_holes_and_face_styles(kind):
    pkg = package()
    ax = mp.ThreeDAxes(x_range=(-1, 3), y_range=(-1, 3), z_range=(0, 8))
    if kind == "triangles":
        surface = ax.plot_trisurf(
            [0, 1, 0], [0, 0, 1], [2, 3, 3], triangles=[[0, 1, 2]]
        )
    else:

        def function(u, v):
            return np.where((u + v > 1) & (kind == "holes"), np.nan, 2 + u + v)

        surface = ax.plot_surface(
            function, (1, 0) if kind == "reversed" else (0, 1), (0, 1), resolution=2
        )
    canonical = state(surface)
    keys = [id(face) for face in surface.faces]
    hidden = [not face.has_points() for face in surface.faces]
    a = pkg.GrowSurface(surface, offset=0, rate_func=linear)
    drive(a, 0.5)
    assert [id(face) for face in surface.faces] == keys
    assert [not face.has_points() for face in surface.faces] == hidden
    for face in surface.faces:
        if face.has_points():
            d = np.array([ax.p2c(p) for p in face.points[::4]])
            np.testing.assert_allclose(d[:, 2], (2 + d[:, 0] + d[:, 1]) / 2, atol=1e-8)
    a.finish()
    assert_state(surface, canonical)


def test_ax2_default_build_schedule_draws_lines_before_ticks():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(-1, 5, 1))
    a = pkg.BuildAxes(ax, lag_ratio=0.5, rate_func=linear)
    drive(a, 0.1)
    assert ax.x.line.has_points()
    assert not ax.x.ticks.at(2).has_points() or ax.x.ticks.at(2).width < 1e-8
    a.finish()
    np.testing.assert_allclose(ax.x.ticks.at(2).get_center(), ax.c2p(2, 0), atol=1e-8)


@pytest.mark.parametrize("name", [n for ns in FAMILIES.values() for n in ns])
def test_lc6_f915_existing_animations_use_the_scene_query(name):
    ax, artist, animation, extra = existing(name)
    still_ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 4))
    still = still_ax.line([0, 1], [1, 0])
    queries = []
    targets = {id(m) for m in artist.get_family() if m.has_points()}

    class Shot(Scene):
        def get_moving_mobjects(self, *animations):
            result = super().get_moving_mobjects(*animations)
            queries.append({id(m) for top in result for m in top.get_family()})
            return result

        def construct(self):
            self.add(still_ax, still, ax, artist, *extra)
            self.play(animation)

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert queries
    assert id(still) not in queries[0]
    # This is the actual Cairo query before begin, not a private involvement flag.
    assert targets & queries[0]


def test_lc6_f915_surface_range_declares_linked_colorbar():
    pkg = package()
    ax, surface = fixture("GrowSurface")
    surface = ax.plot_surface(
        lambda u, v: 2 + u + v, (0, 1), (0, 1), resolution=2, colorscale="viridis"
    )
    colorbar = ax.colorbar(surface)
    still_ax = mp.Axes()
    still = still_ax.line([0, 1], [1, 0])
    queries = []
    ranges = []

    class Shot(Scene):
        def get_moving_mobjects(self, *animations):
            result = super().get_moving_mobjects(*animations)
            queries.append({id(m) for top in result for m in top.get_family()})
            return result

        def update_to_time(self, t):
            super().update_to_time(t)
            ranges.append(float(colorbar.y_range[1]))

        def construct(self):
            self.add(still_ax, still, colorbar, ax, surface)
            self.play(
                pkg.GrowSurface(surface),
                ax.animate.set_z_range((0, 12, 2)),
            )

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert queries
    assert any(id(m) in queries[0] for m in colorbar.strip.get_family())
    assert id(still) not in queries[0]
    assert any(8 < r < 12 for r in ranges)
    assert colorbar.y_range[1] == pytest.approx(12)


def test_lc8_lb1_bar_labels_crosshair_and_axis_numbers_retire_old_glyphs():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5, 1), y_range=(0, 10, 2))
    ax.x.add_numbers([1, 2, 3], label_constructor=Text)
    bars = ax.bar([1], [2])
    labels = ax.bar_label(bars)
    tracker = ValueTracker(1)
    cross = ax.crosshair(tracker, 2)
    line = ax.line([0, 1], [1, 2])
    ghosts = []
    frames = []

    class Shot(Scene):
        def update_to_time(self, t):
            super().update_to_time(t)
            frames.append(t)
            alive = {id(m) for top in self.mobjects for m in top.get_family()}
            ghosts.extend(
                m for m in self.moving_mobjects if id(m) not in alive and m.has_points()
            )

        def construct(self):
            self.add(ax, bars, labels, cross, line)
            self.play(
                pkg.AppendData(line, [3], [8], autoscale=True),
                bars.animate.set_data(x=[1], height=[7]),
                tracker.animate.set_value(3),
            )

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert len(frames) > 2
    assert ghosts == []


@pytest.mark.parametrize("pacing", ["parameter", "arc_length"])
@pytest.mark.parametrize("coords", [[], [[1, 1]], [[1, 1], [1, 1]]])
def test_tc3_empty_singleton_and_zero_length_paths_finish_canonically(pacing, coords):
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 4))
    with warnings.catch_warnings():
        # An empty source warns once at construction; that is not this row.
        warnings.simplefilter("ignore", mp.ManimPlotsWarning)
        curve = ax.line(np.array(coords).reshape(-1, 2))
    before = state(curve)
    a = pkg.TraceCurve(curve, pacing=pacing, rate_func=linear)
    drive(a, 0, 0.5, 1)
    assert np.isfinite(curve.points).all()
    a.finish()
    assert_state(curve, before)


@pytest.mark.parametrize("kwargs", [{"order": "unknown"}, {"order": "value"}])
def test_sp5_invalid_order_or_absent_values_fail_before_mutation(kwargs):
    pkg = package()
    ax, scatter = fixture("ShowPoints")
    before = state(scatter)
    with pytest.raises(ValueError, match=r"(?i)(order|value)"):
        pkg.ShowPoints(scatter, **kwargs)
    assert_state(scatter, before)
    assert ax is not None


@pytest.mark.parametrize(
    "kwargs", [{"zdir": "q"}, {"offset": np.nan}, {"offset": np.inf}]
)
def test_sf2_invalid_plane_rejected_before_mutation(kwargs):
    pkg = package()
    ax, surface = fixture("GrowSurface")
    before = state(surface)
    with pytest.raises(ValueError, match=r"(?i)(zdir|offset|finite)"):
        pkg.GrowSurface(surface, **kwargs)
    assert_state(surface, before)
    assert ax is not None


@pytest.mark.parametrize("name", ["DrawAxes", "BuildAxes"])
def test_ax3_reverse_matches_native_removal_of_plain_parts(name):
    from manim import AnimationGroup, FadeOut, Uncreate, VGroup

    from tests.mobjects.helpers import plain, visible_leaves

    cls = getattr(package(), name)
    ax = mp.NumberPlane(x_range=(-1, 5, 1), y_range=(-1, 5, 1))
    leaves = visible_leaves(ax)
    copies = {id(leaf): plain(leaf) for leaf in leaves}
    native: Any
    if name == "DrawAxes":
        native = Uncreate(VGroup(*copies.values()), rate_func=linear)
    else:

        def parts(*objects):
            return VGroup(
                *(
                    copies[id(leaf)]
                    for obj in objects
                    for leaf in obj.get_family()
                    if id(leaf) in copies
                )
            )

        lines = parts(
            *(
                part
                for axis in (ax.x, ax.y)
                for part in (axis.line, axis.tip)
                if part is not None
            )
        )
        ticks = parts(ax.x.ticks, ax.y.ticks)
        numbers = parts(ax.x.numbers, ax.y.numbers)
        labels_grid = parts(ax.x.labels, ax.y.labels, ax.x.grid, ax.y.grid)
        native = AnimationGroup(
            FadeOut(labels_grid),
            FadeOut(numbers),
            Uncreate(ticks),
            Uncreate(lines),
            lag_ratio=0.5,
            rate_func=linear,
        )
    ours = cls(ax, reverse=True, remover=False, rate_func=linear)
    ours.begin()
    native.begin()
    for alpha in (0, 0.2, 0.5, 0.8, 1):
        ours.interpolate(alpha)
        native.interpolate(alpha)
        for leaf in leaves:
            twin = copies[id(leaf)]
            np.testing.assert_allclose(leaf.points, twin.points, atol=1e-8)
            assert leaf.get_fill_opacity() == pytest.approx(twin.get_fill_opacity())
            assert leaf.get_stroke_opacity() == pytest.approx(twin.get_stroke_opacity())
    ours.finish()
    native.finish()


@pytest.mark.parametrize(
    "name,introducer", [("ShrinkBars", "GrowBars"), ("ShrinkSurface", "GrowSurface")]
)
def test_rv3_shrink_aliases_remove_and_can_be_reintroduced(name, introducer):
    pkg = package()
    ax, artist = fixture(introducer)
    before = state(artist)
    present = []

    def construct(scene):
        scene.add(ax, artist)
        scene.play(getattr(pkg, name)(artist))
        present.append(any(artist in top.get_family() for top in scene.mobjects))
        assert_state(artist, before)
        scene.play(getattr(pkg, introducer)(artist))
        present.append(any(artist in top.get_family() for top in scene.mobjects))

    probe(construct, lambda: None)
    assert present == [False, True]
    assert_state(artist, before)


@pytest.mark.parametrize("name", ["TraceCurve", "GrowSurface"])
def test_lc7_reveal_does_not_resample_its_own_unchanged_function(name):
    pkg = package()
    calls = []
    artist: Any
    if name == "TraceCurve":
        ax = mp.Axes(x_range=(-1, 4), y_range=(-1, 6))

        def function(x):
            calls.append(1)
            return x * x

        artist = ax.plot(function, x_range=(0, 2))
    else:
        ax = mp.ThreeDAxes(x_range=(-1, 3), y_range=(-1, 3), z_range=(0, 8))

        def height(u, v):
            calls.append(1)
            return 2 + u + v

        artist = ax.plot_surface(height, (0, 1), (0, 1), resolution=2)
    counts = []

    def construct(scene):
        scene.add(ax, artist)
        scene.play(getattr(pkg, name)(artist))

    probe(construct, lambda: counts.append(len(calls)))
    assert len(counts) > 2
    assert len(set(counts)) == 1


def test_lc6_trace_declares_an_earlier_endpoint_label():
    pkg = package()
    ax, curve = fixture("TraceCurve")
    label = ax.end_label(curve)
    moving = []

    class Shot(Scene):
        def get_moving_mobjects(self, *animations):
            result = super().get_moving_mobjects(*animations)
            moving.append({id(m) for top in result for m in top.get_family()})
            return result

        def construct(self):
            self.add(ax, label, curve)
            self.play(pkg.TraceCurve(curve))

    with tempconfig(RUN | {"disable_caching": False}):
        Shot().render()
    assert moving
    assert id(label) in moving[0] or any(id(m) in moving[0] for m in label.get_family())


@pytest.mark.parametrize("pacing", ["parameter", "arc_length"])
def test_tc3_explicit_pole_gap_never_acquires_a_bridge(pacing):
    pkg = package()
    ax = mp.Axes(x_range=(-1, 4), y_range=(-12, 12))
    curve = ax.plot(lambda x: 1 / (x - 1), x_range=(0, 3), discontinuities=[1], dt=0.1)
    before = state(curve)
    a = pkg.TraceCurve(curve, pacing=pacing, rate_func=linear)
    a.begin()
    for alpha in (0.2, 0.5, 0.8):
        a.interpolate(alpha)
        for cubic in curve.points.reshape(-1, 4, 3):
            x = np.array([ax.p2c(p)[0] for p in cubic[[0, 3]]])
            assert not (x.min() < 1 and x.max() > 1)
    a.finish()
    assert_state(curve, before)


def test_tc1_function_parameter_pacing_uses_data_x():
    pkg = package()
    ax = mp.Axes(x_range=(-1, 5), y_range=(-1, 18))
    curve = ax.plot(lambda x: x * x, x_range=(0, 4))
    a = pkg.TraceCurve(curve, pacing="parameter", rate_func=linear)
    drive(a, 0.5)
    np.testing.assert_allclose(curve.points[-1], ax.c2p(2, 4), atol=0.02)
    a.finish()


def test_sf1_log_growth_interpolates_data_not_logarithms():
    pkg = package()
    ax = mp.ThreeDAxes(z_range=(1, 100), z_scale="log")
    surface = ax.plot_surface(lambda u, v: 10 + u + v, (0, 1), (0, 1), resolution=2)
    a = pkg.GrowSurface(surface, offset=1, rate_func=linear)
    drive(a, 0.5)
    for face in surface.faces:
        d = np.array([ax.p2c(p) for p in face.points[::4]])
        np.testing.assert_allclose(
            d[:, 2], 1 + 0.5 * (9 + d[:, 0] + d[:, 1]), atol=1e-8
        )
    a.finish()
