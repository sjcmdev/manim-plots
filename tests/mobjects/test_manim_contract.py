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

# Task 13: the animation family walk reads Manim's cached family (PF-1).
ADDED_BY_TASK_13 = ["Mobject.family_members_with_points"]

# Task 16: the bound helpers match Manim's on default axes, so a change to Manim's own
# helpers, or to the line and dash classes they build on, is a review step.
ADDED_BY_TASK_16 = [
    "CoordinateSystem.get_line_from_axis_to_point",
    "CoordinateSystem.get_vertical_line",
    "CoordinateSystem.get_horizontal_line",
    "CoordinateSystem.get_lines_to_point",
    "CoordinateSystem.get_vertical_lines_to_graph",
    "CoordinateSystem.get_T_label",
    "CoordinateSystem.angle_of_tangent",
    "CoordinateSystem.slope_of_tangent",
    "CoordinateSystem.get_secant_slope_group",
    "CoordinateSystem.plot_derivative_graph",
    "CoordinateSystem.plot_antiderivative_graph",
    "DashedLine.__init__",
    "DashedLine._calculate_num_dashes",
    "DashedVMobject.__init__",
    "TangentLine.__init__",
    "Line.__init__",
    "Line._account_for_buff",
]

# Task 17: the regions match Manim's get_area and get_riemann_rectangles, colours too.
ADDED_BY_TASK_17 = [
    "CoordinateSystem.get_area",
    "CoordinateSystem.get_riemann_rectangles",
    "color_gradient",
    "invert_color",
    "VMobject.set_color",
]

# Task 18: error bars read a scatter's markers through Manim's subpaths.
ADDED_BY_TASK_18 = ["VMobject.get_subpaths"]

# Task 19b: an axis colours its own parts and the mirrors that did not set a colour,
# through Manim's `Mobject.set_color` on itself alone. A decoration whose ticks change
# during `.animate` swaps its leaves while the renderer keeps the members it captured
# when the animation began; a retired leaf is emptied, and drawing an empty path relies
# on how Manim's scene and Cairo camera treat it.
ADDED_BY_TASK_19B = [
    "Mobject.set_color",
    "Scene.get_moving_and_static_mobjects",
    "Camera.set_cairo_context_color",
    "Camera.apply_fill",
]

# Task 21: field parity and native arrow/flash geometry.
ADDED_BY_TASK_21 = [
    "VectorField.__init__",
    "VectorField.fit_to_coordinate_system",
    "VectorField.nudge",
    "VectorField.nudge_submobjects",
    "VectorField.get_nudge_updater",
    "VectorField.start_submobject_movement",
    "VectorField.stop_submobject_movement",
    "VectorField.get_colored_background_image",
    "VectorField.get_vectorized_rgba_gradient_function",
    "ArrowVectorField.__init__",
    "ArrowVectorField.get_vector",
    "StreamLines.__init__",
    "StreamLines.create",
    "StreamLines.start_animation",
    "StreamLines.end_animation",
    "Vector.__init__",
    "Arrow.__init__",
    "ShowPassingFlash.__init__",
    "ShowPassingFlash._get_bounds",
    "NumberPlane.get_vector",
    "CoordinateSystem.plot_implicit_curve",
    "VectorField.shift_func",
    "VectorField.scale_func",
]

ADDED_BY_TASK_24 = [
    "Camera",
    "Camera.capture_mobjects",
    "Mobject.get_family",
    "ThreeDCamera.get_gamma",
    "ThreeDCamera.add_fixed_in_frame_mobjects",
    "ThreeDAxes.__init__",
    "ThreeDAxes._add_3d_pieces",
    "ThreeDAxes._set_axis_shading",
    "ThreeDAxes.get_y_axis_label",
    "ThreeDAxes.get_z_axis_label",
    "ThreeDAxes.get_axis_labels",
    "ThreeDCamera.__init__",
    "ThreeDCamera.get_phi",
    "ThreeDCamera.get_theta",
    "ThreeDCamera.get_rotation_matrix",
    "ThreeDCamera.reset_rotation_matrix",
    "ThreeDCamera.generate_rotation_matrix",
    "Scene.update_mobjects",
    "Mobject.get_pieces",
]

ADDED_BY_TASK_22 = [
    "VMobject.get_subpath_split_indices_from_points",
    "Camera.transform_points_pre_display",
    "PolarPlane._init_background_lines",
    "PolarPlane._get_lines",
    "PolarPlane.get_axes",
    "PolarPlane.get_vector",
    "PolarPlane.prepare_for_nonlinear_transform",
    "PolarPlane.get_coordinate_labels",
    "PolarPlane.add_coordinates",
    "PolarPlane.get_radian_label",
    "PolarPlane.__init__",
    "CoordinateSystem.polar_to_point",
    "CoordinateSystem.point_to_polar",
    "CoordinateSystem.pr2pt",
    "CoordinateSystem.pt2pr",
    "CoordinateSystem.plot_polar_graph",
]

ADDED_BY_TASK_25 = [
    "Surface",
    "Surface.__init__",
    "Surface._get_u_values_and_v_values",
    "Surface._setup_in_uv_space",
    "Surface.func",
    "Surface.set_fill_by_checkerboard",
    "Surface.set_fill_by_value",
    "CoordinateSystem.plot_surface",
    "ThreeDVMobject",
    "VMobject.set_points_as_corners",
    "VMobject.set_style",
    "VMobject.get_fill_color",
    "VMobject.get_stroke_color",
]

ADDED_BY_TASK_26: list[str] = []
ADDED_BY_TASK_28: list[str] = []
ADDED_BY_TASK_29: list[str] = []

ADDED_BY_TASK_27 = [
    "Arrow3D.get_end",
    "Arrow3D",
    "Arrow3D.__init__",
    "Line3D",
    "Line3D.__init__",
    "Line3D.get_start",
    "Line3D.get_end",
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
        + ADDED_BY_TASK_13
        + ADDED_BY_TASK_16
        + ADDED_BY_TASK_17
        + ADDED_BY_TASK_18
        + ADDED_BY_TASK_19B
        + ADDED_BY_TASK_21
        + ADDED_BY_TASK_22
        + ADDED_BY_TASK_24
        + ADDED_BY_TASK_25
        + ADDED_BY_TASK_26
        + ADDED_BY_TASK_27
        + ADDED_BY_TASK_28
        + ADDED_BY_TASK_29
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
