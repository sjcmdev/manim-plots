"""Keyed axis parts and cached-glyph label placement and overlap."""

from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

import numpy as np
from manim import LogBase, MathTex, Tex, VGroup, VMobject

from manim_plots.core import FloatArray
from manim_plots.core.formatters import DecimalFormatter
from manim_plots.core.scales import LinearScale
from manim_plots.core.ticks import Level, round_key
from manim_plots.mobjects import axis as axis_module
from manim_plots.mobjects.leaves import Leaf, NumberLabel, _label

T = TypeVar("T", bound=VMobject)


# Bound method hints must also resolve without the declaring class's local namespace.
class _Parts(VGroup, Generic[T]):  # noqa: UP046
    def __init__(self, axis: axis_module.Axis, level: Level | None = "major") -> None:
        self._axis = axis
        self._level = level
        self._parts: dict[object, T] = {}
        super().__init__()

    def at(self, value: float) -> T:
        """Return the current part at a locator key.

        Parameters
        ----------
        value
            Data value whose locator key identifies the part.

        Raises
        ------
        KeyError
            If the part is absent, including hidden ticks or dropped labels.
        """
        self._axis._system._sync_data()
        axis = self._axis
        value = axis._part_value(value)
        levels: tuple[Level, ...] = (
            ("major", "minor") if self._level is None else (self._level,)
        )
        for level in levels:
            locator = axis.locator if level == "major" else axis.minor_locator
            keys: list[object] = [("fixed", round_key(value))]
            if locator is not None:
                try:
                    lo, hi = (
                        axis.range.value
                        if axis._secondary_of is None
                        else axis._tick_limits()
                    )
                    if locator.contains(
                        value,
                        float(lo),
                        float(hi),
                        axis._scale if axis._secondary_of is None else LinearScale(),
                        axis.max_ticks,
                    ):
                        keys.append(locator.key(value))
                except ValueError:
                    continue
            for key in keys:
                part = self._parts.get((level, key) if self._level is None else key)
                if part is not None and part in self.submobjects:
                    return part
        raise KeyError(value)

    def _replace(self, parts: dict[object, T]) -> None:
        self._parts = parts
        self.submobjects = list(parts.values())
        if self._axis._mirror_of is not None or self._axis._secondary_of is not None:
            self._axis._parts_version += 1


def _configure_numbers(axis: axis_module.Axis) -> None:
    axis._crossing_frame = -1
    items = axis._items or axis._drawn_items()
    for old_label in axis._number_leaves.values():
        _restore_overlap(old_label)
    major = [item for item in items if item.level == "major"]
    by_value = {item.value: item for item in items}
    explicit = {
        round_key(item.value): item.label for item in items if item.label is not None
    }
    candidates = (
        [item.value for item in major]
        if axis._number_values is None
        else axis._number_values
    )
    if not axis.include_numbers and axis._number_values is None:
        candidates = [item.value for item in items if item.label is not None]
    elif axis._number_values is None:
        candidates = [
            item.value
            for item in items
            if item.level == "major" or item.label is not None
        ]
    lo, hi = sorted(
        axis.range.value if axis._secondary_of is None else axis._tick_limits()
    )
    hides_zero = axis._hides_zero()
    excluded = axis.numbers_to_exclude
    if axis._default_exclusion and not hides_zero:
        excluded = tuple(x for x in excluded if x != 0)
    values = np.array(
        [
            float(x)
            for x in candidates
            if (
                x not in excluded
                and (lo <= x <= hi or (axis._pool is not None and axis._pool.building))
                and (x != 0 or not hides_zero)
            )
        ]
    )
    formatted = axis.formatter.format_ticks(values)
    if len(formatted.text) != len(values):
        raise ValueError("formatter must return one label per value")
    system = axis._system
    anchors = axis._anchors(values)
    mapping = system.frame.mapping
    current: dict[object, NumberLabel] = {}
    glyphs: list[Leaf] = []
    local_points: list[FloatArray] = []
    style_version = (
        axis.rotation.version,
        axis.offset.version,
        axis.justify.version,
        axis.overlap.version,
    )
    style_changed = getattr(axis, "_label_style_seen", None) != style_version
    for i, (x, anchor) in enumerate(zip(values, anchors, strict=True)):
        item = by_value.get(float(x))
        key = (
            ("major", axis._part_key(float(x)))
            if item is None
            else (item.level, item.key)
        )
        text = explicit.get(round_key(float(x)))
        mode = False if formatted.text_mode is None else formatted.text_mode[i]
        if text is None:
            text = formatted.text[i]
        content = (text, mode)
        label = axis._number_leaves.get(key)
        changed = axis._number_content.get(key) != content
        if label is None or changed or style_changed:
            if label is None:
                label = NumberLabel(
                    0.0
                    if isinstance(axis.scaling, LogBase) and axis.scaling.custom_labels
                    else float(x),
                    font_size=axis.font_size,
                    **axis.decimal_number_config,
                )
                if axis._decoration_color is not None:
                    label.set_color(axis._decoration_color)
            if (
                axis._formatter_custom
                or round_key(float(x)) in explicit
                or (
                    isinstance(axis.formatter, DecimalFormatter)
                    and axis.formatter.num_decimal_places is None
                )
            ):
                label._set_text(text, text_mode=mode)
            elif isinstance(axis.scaling, LogBase) and axis.scaling.custom_labels:
                exponent = float(axis._scale.forward(x))
                places = axis.decimal_number_config.get("num_decimal_places", 0)
                fresh = NumberLabel(
                    axis.scaling.base,
                    font_size=48,
                    num_decimal_places=0,
                    unit="^{" + f"{exponent:.{places}f}" + "}",
                )
                fresh.font_size = axis.font_size
                if key in axis._number_leaves:
                    fresh.match_style(label)
                label.submobjects = fresh.submobjects
            elif changed or style_changed:
                fresh = NumberLabel(
                    float(x),
                    font_size=axis._number_options.get("font_size", axis.font_size),
                    **{
                        **axis.decimal_number_config,
                        **{
                            k: v
                            for k, v in axis._number_options.items()
                            if k not in ("direction", "buff", "font_size")
                        },
                    },
                )
                fresh.match_style(label)
                label.submobjects = fresh.submobjects
            direction = axis._number_options.get(
                "direction", axis._number_direction(float(x))
            )
            label.next_to(
                anchor,
                direction=direction,
                buff=axis._number_options.get("buff", axis.line_to_number_buff),
            )
            if x < 0 and axis.label_direction[0] == 0 and label.submobjects:
                label.shift((-label[0].width / 2, 0, 0))
            rotation = axis.rotation.value + (
                np.pi / 4 if axis.overlap.value == "rotate" else 0
            )
            if rotation:
                label.rotate(rotation)
            tangent, across = axis._label_basis(float(x))
            shift = axis.offset.value[0] * tangent + axis.offset.value[1] * across
            if axis.justify.value != "center":
                projections = label.get_all_points() @ tangent
                target = (
                    np.min(projections)
                    if axis.justify.value == "left"
                    else np.max(projections)
                )
                shift += (anchor @ tangent - target) * tangent
            label.shift(shift)
            members = label.family_members_with_points()
            axis._number_members[key] = [cast(Leaf, member) for member in members]
            axis._number_offsets[key] = [
                cast(Leaf, member)._cache - anchor for member in members
            ]
            axis._number_content[key] = content
        for glyph, offset in zip(
            axis._number_members[key],
            axis._number_offsets[key],
            strict=True,
        ):
            leaf = glyph
            leaf._system = system
            glyphs.append(leaf)
            local_points.append(offset + anchor)
        label.number = float(x)
        label.text = text
        current[key] = label
    if local_points:
        placed = mapping.forward(np.concatenate(local_points))
        offset_index = 0
        for glyph, local in zip(glyphs, local_points, strict=True):
            glyph._axis_local = local
            glyph._cache = placed[offset_index : offset_index + len(local)]
            offset_index += len(local)
    if axis._pool is None:
        for removed_key in axis._number_leaves.keys() - current.keys():
            for glyph in axis._number_members.pop(removed_key):
                glyph._cache = np.empty((0, 3))
        axis._number_leaves = current
        axis._number_offsets = {key: axis._number_offsets[key] for key in current}
        axis._number_content = {key: axis._number_content[key] for key in current}
    else:
        axis._number_leaves.update(current)
    axis._numbers._replace(current)
    _layout_overlap(axis, axis._numbers)
    if axis._numbers not in axis.submobjects:
        axis.add(axis._numbers)
    axis._label_style_seen = style_version
    if isinstance(axis.scaling, LogBase) and axis.scaling.custom_labels:
        axis.labels = axis._numbers


def _restore_overlap(label: VMobject) -> None:
    old = getattr(label, "_overlap_opacity", None)
    if old is not None:
        for glyph, fill, stroke in old:
            glyph.set_fill(opacity=fill).set_stroke(opacity=stroke)
        delattr(label, "_overlap_opacity")


def _layout_overlap(axis: axis_module.Axis, group: _Parts[Any]) -> None:
    labels = list(group.submobjects)
    if not labels:
        return
    # Reset only opacity previously hidden by this policy, preserving user styling.
    for label in labels:
        _restore_overlap(label)
    outlines: list[FloatArray] = []
    sizes: list[int] = []
    for label in labels:
        family = (
            label.submobjects
            if all(
                isinstance(glyph, Leaf) and not glyph.submobjects
                for glyph in label.submobjects
            )
            else label.get_family()
        )
        parts = [
            glyph._cache
            for glyph in family
            if isinstance(glyph, Leaf) and len(glyph._cache)
        ]
        outlines.extend(parts)
        sizes.append(sum(len(part) for part in parts))
    bounds = np.zeros((len(labels), 2, 2))
    if outlines:
        points = np.concatenate(outlines)[:, [axis.index, 0 if axis.index else 1]]
        starts = np.cumsum([0, *sizes[:-1]])
        nonempty = np.asarray(sizes) != 0
        bounds[nonempty, 0] = np.minimum.reduceat(points, starts[nonempty], axis=0)
        bounds[nonempty, 1] = np.maximum.reduceat(points, starts[nonempty], axis=0)
    overlap = (bounds[:, None, 0] < bounds[None, :, 1]).all(axis=2)
    overlap &= overlap.T
    np.fill_diagonal(overlap, False)
    if not overlap.any():
        return

    visible = list(range(len(labels)))
    if axis.overlap.value == "drop":
        while overlap[np.ix_(visible, visible)].any():
            visible = visible[::2]
        group.submobjects = [labels[i] for i in visible]
        return
    visible = []
    for i, label in enumerate(labels):
        if overlap[i, visible].any():
            cast(Any, label)._overlap_opacity = [
                (label, label.get_fill_opacity(), label.get_stroke_opacity()),
                *(
                    (glyph, glyph.get_fill_opacity(), glyph.get_stroke_opacity())
                    for glyph in label.family_members_with_points()
                ),
            ]
            label.set_opacity(0)
        else:
            visible.append(i)


def _configure_labels(axis: axis_module.Axis) -> None:
    axis._crossing_frame = -1
    labels: dict[object, VGroup] = {}
    lo, hi = sorted(
        axis.range.value if axis._secondary_of is None else axis._tick_limits()
    )
    mapping = axis._system.frame.mapping
    style_version = (
        axis.rotation.version,
        axis.offset.version,
        axis.justify.version,
        axis.overlap.version,
    )
    for x, value in sorted(
        axis._label_values.items(), reverse=axis.range.value[0] > axis.range.value[1]
    ):
        if not lo <= x <= hi:
            continue
        key = axis._part_key(x)
        anchor = axis._anchors([x])[0]
        label = axis._labels._parts.get(key)
        changed = axis._label_content.get(key) is not value
        if label is None or changed or style_version != axis._custom_style_seen:
            size = axis._label_options["font_size"]
            constructor = axis._label_options["label_constructor"]
            if constructor is not None and not isinstance(value, VMobject):
                if constructor is MathTex and isinstance(value, str):
                    constructor = Tex
                if not callable(constructor):
                    raise TypeError("label_constructor must be callable")
                value = constructor(str(value))
            if isinstance(value, VMobject):
                if not hasattr(value, "font_size"):
                    raise AttributeError("label is not compatible with add_labels")
                cast(Any, value).font_size = size
            fresh = _label(value, text_mode=isinstance(value, str), font_size=size)
            if label is None:
                label = fresh
            else:
                _restore_overlap(label)
                fresh.match_style(label)
                label.submobjects = fresh.submobjects
            label.next_to(
                anchor,
                direction=axis._label_options["direction"],
                buff=axis._label_options["buff"],
            )
            rotation = axis.rotation.value + (
                np.pi / 4 if axis.overlap.value == "rotate" else 0
            )
            if rotation:
                label.rotate(rotation)
            tangent, across = axis._label_basis(x)
            shift = axis.offset.value[0] * tangent + axis.offset.value[1] * across
            if axis.justify.value != "center":
                projections = label.get_all_points() @ tangent
                edge = (
                    np.min(projections)
                    if axis.justify.value == "left"
                    else np.max(projections)
                )
                shift += (anchor @ tangent - edge) * tangent
            label.shift(shift)
            axis._label_offsets[key] = [
                cast(Leaf, member)._cache - anchor
                for member in label.family_members_with_points()
            ]
        for member, offset in zip(
            label.family_members_with_points(), axis._label_offsets[key], strict=True
        ):
            leaf = cast(Leaf, member)
            leaf._system = axis._system
            leaf._axis_local = offset + anchor
            leaf._cache = mapping.forward(leaf._axis_local)
        labels[key] = label
        axis._label_content[key] = axis._label_values[x]
    for key in axis._labels._parts.keys() - labels.keys():
        for member in axis._labels._parts[key].family_members_with_points():
            cast(Leaf, member)._cache = np.empty((0, 3))
    axis._labels._replace(labels)
    axis._label_offsets = {key: axis._label_offsets[key] for key in labels}
    axis._label_content = {key: axis._label_content[key] for key in labels}
    axis._custom_style_seen = style_version
    _layout_overlap(axis, axis._labels)
