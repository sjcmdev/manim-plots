"""The pinned Manim internals (F-917).

Rows K-1 to K-6 of `docs/acceptance/06-core-contracts.md`. The inventory below is the
oracle: PoC 4's symbols (`poc/poc4/evidence.py::SYMBOLS`) and the two ADR 0003 added.
A Manim upgrade that moves one of them fails here by name before it can misbehave.
"""

from __future__ import annotations

import hashlib
import inspect
import re
from pathlib import Path

import manim
import pytest
from manim import Mobject, Scene, Square, VGroup, VMobject, tempconfig

import manim_plots
from manim_plots.mobjects import context

POC4_SYMBOLS = [
    "Mobject.rotate",
    "Mobject.scale",
    "Mobject.stretch",
    "Mobject.apply_matrix",
    "Animation.create_starting_mobject",
    "Animation.clean_up_from_scene",
    "Animation.is_remover",
    "Animation.is_introducer",
    "Transform.interpolate_submobject",
    "Transform.get_all_families_zipped",
    "GrowFromCenter.__init__",
    "GrowFromPoint.create_starting_mobject",
    "ShrinkToCenter.__init__",
    "NumberPlane.prepare_for_nonlinear_transform",
    "Mobject.shift",
    "Mobject.apply_points_function_about_point",
    "VMobject.apply_function",
    "VMobject.scale_handle_to_anchor_distances",
    "VMobject.get_anchors",
    "VMobject.get_points_defining_boundary",
    "VMobject.set_anchors_and_handles",
    "Mobject.__deepcopy__",
    "Mobject.copy",
    "Mobject.suspend_updating",
    "Mobject.resume_updating",
    "Mobject.become",
    "Mobject.align_data",
    "Mobject.align_submobjects",
    "Mobject.add_n_more_submobjects",
    "Mobject.interpolate",
    "VMobject.align_points",
    "Animation.begin",
    "Animation.finish",
    "Animation.get_all_families_zipped",
    "Animation.get_sub_alpha",
    "AnimationGroup.begin",
    "AnimationGroup.finish",
    "AnimationGroup.clean_up_from_scene",
    "Succession.begin",
    "Succession.finish",
    "Succession.update_active_animation",
    "ShowPartial.interpolate_submobject",
    "DrawBorderThenFill.interpolate_submobject",
    "Wiggle.interpolate_submobject",
    "Transform.begin",
    "Transform.clean_up_from_scene",
    "TransformFromCopy.__init__",
    "TransformFromCopy.interpolate",
    "_MethodAnimation.finish",
    "FadeOut.clean_up_from_scene",
    "ShowPassingFlash.clean_up_from_scene",
    "MoveAlongPath.__init__",
    "MoveAlongPath.interpolate_mobject",
    "PhaseFlow.__init__",
    "PhaseFlow.interpolate_mobject",
    "ShowIncreasingSubsets.__init__",
    "ShowIncreasingSubsets.interpolate_mobject",
    "_AnimationBuilder.__init__",
    "_AnimationBuilder.__getattr__",
    "always_redraw",
    "Scene.get_moving_mobjects",
    "Scene.should_update_mobjects",
    "Scene.update_to_time",
    "Scene.play_internal",
    "Scene.add",
    "Scene.add_mobjects_from_animations",
    "CairoRenderer.play",
    "Camera.set_cairo_context_path",
]

ADDED_BY_ADR_0003 = ["DrawBorderThenFill.begin", "Mobject.get_family_updaters"]
# The overrides the first Manim layer needs on its leaves and containers (task 09).
ADDED_BY_TASK_09 = [
    "Mobject.__getattr__",
    "Mobject.remove",
    "VGroup.add",
    "VMobject.set_fill",
    "VMobject.set_stroke",
    "VMobject.interpolate_color",
    "VMobject.pointwise_become_partial",
    "Mobject.reduce_across_dimension",
]
# Manim's own decoration code the axes reproduce, pinned so a change upstream is seen
# (task 10).
ADDED_BY_TASK_10 = [
    "NumberLine.__init__",
    "NumberLine.get_tick",
    "NumberLine.get_tick_range",
    "NumberLine.number_to_point",
    "NumberLine.point_to_number",
    "NumberLine.get_unit_size",
    "NumberLine.get_unit_vector",
    "NumberLine.get_number_mobject",
    "NumberLine.add_numbers",
    "NumberLine.add_labels",
    "NumberLine._create_label_tex",
    "NumberLine._decimal_places_from_step",
    "Axes.__init__",
    "Axes._create_axis",
    "Axes._origin_shift",
    "Axes.coords_to_point",
    "Axes.point_to_coords",
    "Axes.get_axis_labels",
    "CoordinateSystem.add_coordinates",
    "CoordinateSystem.get_x_axis_label",
    "CoordinateSystem.get_y_axis_label",
    "CoordinateSystem._get_axis_label",
    "CoordinateSystem.get_graph_label",
    "DecimalNumber._set_submobjects_from_number",
    "DecimalNumber._get_num_string",
    "DecimalNumber._get_formatter",
    "NumberPlane.__init__",
    "NumberPlane._init_background_lines",
    "NumberPlane._get_lines",
    "NumberPlane._get_lines_parallel_to_axis",
    "LogBase.get_custom_labels",
]
# Stroke scaling, dash splitting and the library's animations (task 12).
ADDED_BY_TASK_12 = [
    "VMobject.scale",
    "VMobject.split",
    "Animation.interpolate_mobject",
]

# Task 11 part B: Manim's scene caching hashes the play call (MX-3).
ADDED_BY_TASK_11 = [
    "get_json",
    "get_hash_from_play_call",
    "_CustomEncoder.default",
    "_Memoizer._handle_already_processed",
]

SUPPORTED = {"0.21.0", "0.22.0"}
SHA256 = re.compile(r"[0-9a-f]{64}")
MEDIA = Path(__file__).parents[1] / "visual" / "_out" / "media"


def names() -> list[str]:
    return [context.symbol_name(symbol) for symbol in context.SYMBOLS]


def test_k1_the_inventory_is_poc4s_plus_adr_0003s_plus_the_tasks():
    assert len(POC4_SYMBOLS) == 68
    assert sorted(names()) == sorted(
        POC4_SYMBOLS
        + ADDED_BY_ADR_0003
        + ADDED_BY_TASK_09
        + ADDED_BY_TASK_10
        + ADDED_BY_TASK_11
        + ADDED_BY_TASK_12
    )


def test_k1_no_symbol_twice():
    assert len(set(context.SYMBOLS)) == len(context.SYMBOLS)
    assert len(set(names())) == len(names())


def test_k2_hashes_are_sha256_of_the_source_lines():
    hashes = context.source_hashes()
    assert set(hashes) == set(names())
    for symbol in context.SYMBOLS:
        lines, _ = inspect.getsourcelines(symbol)
        expected = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        assert hashes[context.symbol_name(symbol)] == expected


def test_k3_both_supported_versions_are_pinned_in_full():
    assert set(context.PINS) == SUPPORTED
    for version, pins in context.PINS.items():
        assert set(pins) == set(names()), version


def test_k3_the_installed_version_matches_its_pins():
    assert manim.__version__ in SUPPORTED
    hashes = context.source_hashes()
    pins = context.PINS[manim.__version__]
    moved = sorted(name for name in hashes if hashes[name] != pins[name])
    assert not moved, f"Manim {manim.__version__} moved: {moved}"


def test_k3_the_two_versions_differ_where_adr_0003_says():
    a, b = context.PINS["0.21.0"], context.PINS["0.22.0"]
    assert a["Scene.get_moving_mobjects"] != b["Scene.get_moving_mobjects"]


def test_k4_an_unpinned_version_warns_naming_it_and_the_supported_ones():
    with pytest.warns(manim_plots.ManimPlotsWarning) as record:
        context.check_pins("0.20.0")
    message = str(record[0].message)
    assert "0.20.0" in message
    assert "0.21.0" in message and "0.22.0" in message


def test_k4_the_installed_pinned_version_is_silent(recwarn):
    context.check_pins()
    assert not [
        w for w in recwarn if issubclass(w.category, manim_plots.ManimPlotsWarning)
    ]


def test_k4_a_moved_symbol_on_a_pinned_version_warns_naming_it(monkeypatch):
    version = manim.__version__
    pins = {v: dict(p) for v, p in context.PINS.items()}
    pins[version]["Mobject.shift"] = "0" * 64
    monkeypatch.setattr(context, "PINS", pins)
    with pytest.warns(manim_plots.ManimPlotsWarning, match="Mobject.shift"):
        context.check_pins(version)


def test_k5_pins_hold_hashes_and_no_line_numbers():
    for pins in context.PINS.values():
        for value in pins.values():
            assert isinstance(value, str)
            assert SHA256.fullmatch(value)


def moving(*mobjects: VMobject) -> list[Mobject]:
    run = {"dry_run": True, "disable_caching": True, "media_dir": str(MEDIA)}
    with tempconfig(run | {"progress_bar": "none"}):
        scene = Scene()
        scene.add(*mobjects)
        return scene.get_moving_mobjects()


def test_k6_an_updater_without_dt_makes_its_mobject_move():
    static, bound = Square(), VMobject()
    bound.add_updater(lambda m: None)
    assert moving(static, bound)[0] is bound


def test_k6_an_updater_on_a_submobject_makes_its_parent_move():
    child = VMobject()
    child.add_updater(lambda m: None)
    parent = VGroup(child)
    result = moving(Square(), parent)
    assert result[0] is parent
    assert child in result


def test_k6_without_updaters_nothing_moves():
    assert moving(Square(), VGroup(VMobject())) == []
