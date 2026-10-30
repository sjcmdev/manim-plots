"""Composed three-dimensional plot artists and bound annotations."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from manim import Arrow, ManimColor, Mobject, Text, ThreeDCamera, VGroup, VMobject
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.artists import LinePlot, _CurvePlot, _cycle_style
from manim_plots.mobjects.fields import _facing_basis, _VectorGroup
from manim_plots.mobjects.geometry import _data_point, _ensure_binding, _inputs, _read
from manim_plots.mobjects.helpers import HelperGroup, _Binding, _HelperShape
from manim_plots.mobjects.leaves import _ArtistOptions, _VMStyle
from manim_plots.mobjects.projections import _juggle
from manim_plots.mobjects.surfaces import SurfacePlot


class StemPlot(VGroup):
    """Join data points to a baseline with independently styled markers.

    Parameters
    ----------
    system, x, y, z, bottom, orientation, **style
        Owning axes, coordinate arrays, baseline coordinate, axis and style.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        *,
        bottom: float = 0,
        orientation: str = "z",
        **style: object,
    ) -> None:
        if orientation not in ("x", "y", "z"):
            raise ValueError("orientation must be x, y or z")
        points = _juggle(x, y, z, "z").reshape(-1, 3)
        floor = points.copy()
        floor[:, "xyz".index(orientation)] = bottom
        _cycle_style(system, cast(_VMStyle, style), scatter=True)
        self.stemlines = VGroup(
            *(
                system.line([a, b], **cast(dict[str, Any], style))
                for a, b in zip(floor, points, strict=True)
            )
        )
        self.markers = system.scatter(points, **cast(dict[str, Any], style))
        self.baseline = system.line(
            floor, color=system.x_axis.get_color(), stroke_width=1
        )
        super().__init__(self.stemlines, self.markers, self.baseline)


class _WaterfallFill(LinePlot):
    def __init__(
        self, system: mp.ThreeDAxes, points: FloatArray, axis: int, **style: object
    ) -> None:
        self._curve, self._floor_axis = points, axis
        super().__init__(points, system, **cast(_ArtistOptions, style))

    def _rebuild(self) -> None:
        assert self._system is not None
        floor = self._curve[::-1].copy()
        floor[:, self._floor_axis] = min(
            self._system._ranges[self._floor_axis].range.value
        )
        self.source = ArraySource(
            np.vstack((self._curve, floor, self._curve[:1])), dim=3
        )
        super()._rebuild()


class WaterfallPlot(VGroup):
    """Lay coloured curves and optional floor fills in parallel planes.

    Parameters
    ----------
    system, x, curves, positions, zdir, fill, **style
        Axes, shared abscissae, ordinates, planes, direction and style.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        x: ArrayLike,
        curves: ArrayLike,
        positions: ArrayLike | None = None,
        *,
        zdir: str = "y",
        fill: bool = True,
        **style: object,
    ) -> None:
        curves = np.asarray(curves, float)
        positions = (
            np.arange(len(curves)) if positions is None else np.asarray(positions)
        )
        if len(positions) != len(curves):
            raise ValueError("positions must match curves")
        self.lines: list[LinePlot] = []
        self.fills: list[LinePlot | None] = []
        for curve, position in zip(curves, positions, strict=True):
            options = style.copy()
            _cycle_style(system, cast(_VMStyle, options))
            points = _juggle(x, curve, position, zdir)
            line = system.line(points, **cast(dict[str, Any], options))
            self.lines.append(line)
            options.setdefault("fill_opacity", 0.5)
            options.setdefault("stroke_width", 0)
            polygon = (
                _WaterfallFill(system, points, 1 if zdir == "z" else 2, **options)
                if fill
                else None
            )
            if polygon is not None:
                system.add(polygon)
            self.fills.append(polygon)
        super().__init__(*(f for f in self.fills if f is not None), *self.lines)


class _BarSurface(SurfacePlot):
    def _derive(self) -> None:
        self._building = True
        try:
            self._corner_data = self._bar_corners
            self._centres = self._corner_data.mean(axis=1)
            mapped = self._system._data.forward(self._corner_data.reshape(-1, 3))
            self._local_faces = [
                VMobject().set_points_as_corners(np.vstack((c, c[:1]))).points
                for c in mapped.reshape(-1, 4, 3)
            ]
            self._clip_faces()
            self._place_faces()
        finally:
            self._building = False

    _bar_corners: FloatArray


class BarPlot3D(VGroup):
    """Draw six clipped, independently styleable faces per data box.

    Parameters
    ----------
    system, x, y, z, dx, dy, dz, color, shade, **style
        Axes, corners, side lengths, bar colours and fixed face lighting.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        dx: ArrayLike,
        dy: ArrayLike,
        dz: ArrayLike,
        color: object = None,
        shade: bool = True,
        **style: object,
    ) -> None:
        arrays = np.broadcast_arrays(
            *(np.asarray(a, float) for a in (x, y, z, dx, dy, dz))
        )
        if not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("bar coordinates and sizes must be finite")
        xyz = np.stack(arrays[:3], -1).reshape(-1, 3)
        sizes = np.stack(arrays[3:], -1).reshape(-1, 3)
        unit = np.array(
            [
                [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
                [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]],
                [[0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1]],
                [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]],
                [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]],
            ]
        )
        options = style.copy()
        if color is None:
            _cycle_style(system, cast(_VMStyle, options))
            color = options.pop("color")
        colors = (
            [color] * len(xyz)
            if isinstance(color, (str, ManimColor))
            else list(cast(Any, color))
        )
        if len(colors) != len(xyz):
            raise ValueError("color must contain one colour per bar")
        surface = _BarSurface.__new__(_BarSurface)
        surface._bar_corners = (
            xyz[:, None, None, :] + sizes[:, None, None, :] * unit
        ).reshape(-1, 4, 3)
        _BarSurface.__init__(
            surface,
            system,
            lambda u, v: 0,
            resolution=(len(xyz), 6),
            **cast(dict[str, Any], options),
        )
        normals = np.array(
            [[0, 0, -1], [0, 0, 1], [0, -1, 0], [0, 1, 0], [-1, 0, 0], [1, 0, 0]]
        )
        factors = 0.3 + 0.35 * (1 + normals @ (np.array([-2, -2, 1]) / 3))
        self.bars = VGroup()
        for i, c in enumerate(colors):
            faces = VGroup(*surface.faces.submobjects[6 * i : 6 * i + 6])
            for j, face in enumerate(faces):
                face.shade_in_3d = False
                face.set_fill(
                    ManimColor(
                        np.asarray(ManimColor(c).to_rgb())
                        * (factors[j] if shade else 1)
                    ),
                    opacity=cast(float, style.get("fill_opacity", 1)),
                )
            self.bars.add(faces)
        self._surface = surface
        super().__init__(self.bars)


class _TextDriver(_CurvePlot):
    def __init__(
        self,
        system: mp.ThreeDAxes,
        point: object,
        text: Mobject,
        zdir: str | None,
        offset: bool,
    ) -> None:
        if zdir is not None:
            _juggle(0, 0, 0, zdir)
        self.text, self.zdir, self.offset = text, zdir, offset
        anchor = text.get_center()
        self._flats = [
            (leaf, leaf.points.copy() - anchor)
            for leaf in text.family_members_with_points()
        ]
        self._binding = _Binding(
            system, lambda b: None, _inputs(_data_point(point, "xyz"), "xyz", system)
        )
        self._binding_seen = -1
        super().__init__(
            ArraySource(np.empty((0, 3)), dim=3), system, color="WHITE", clip=False
        )
        system.add(self)
        system._register_field_view(self)

    def _turn(self) -> None:
        self._dirty = True
        self._ensure()

    def _poll(self) -> None:
        self._binding.poll()

    def _needs_sync(self, moving: frozenset[Mobject]) -> bool:
        return self._binding.needs_sync(moving)

    def _ensure(self) -> None:
        if self.__dict__.get("_placing_text", False):
            return
        self._placing_text = True
        try:
            self._ensure_text()
        finally:
            self._placing_text = False

    def _ensure_text(self) -> None:
        _ensure_binding(self._binding)
        if self._binding_seen != self._binding.version or (
            self._system is not None and self._frame_seen != self._system.frame.version
        ):
            self._dirty = True
        super()._ensure()

    def _rebuild(self) -> None:
        system = cast(mp.ThreeDAxes, self._system)
        _ensure_binding(self._binding)
        anchor = system.c2p(*_read(self._binding, "xyz"))
        rotation = (
            system._camera.generate_rotation_matrix()
            if isinstance(system._camera, ThreeDCamera)
            else np.eye(3)
        )
        if self.offset:
            anchor += np.array([0.6, 0.6, 0]) @ rotation
        screen = np.eye(3)
        if self.zdir is not None:
            vector = np.eye(3)["xyz".index(self.zdir)]
            direction = (system.c2p(*vector) - system.c2p(0, 0, 0)) @ rotation.T
            angle = np.arctan2(direction[1], direction[0])
            c, s = np.cos(angle), np.sin(angle)
            screen = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        for leaf, flat in self._flats:
            leaf.set_points(anchor + flat @ screen @ rotation)
        self._binding_seen = self._binding.version
        self._data_seen, self._frame_seen = system._data_version, system.frame.version
        self._dirty = False


class _TextGlyph(VMobject):
    def __init__(self, native: VMobject, driver: _TextDriver) -> None:
        self._text_points = native.points.copy()
        super().__init__()
        self.set_points(native.points.copy())
        self.match_style(native)
        self._text_driver = driver

    @property
    def points(self) -> FloatArray:
        driver = self.__dict__.get("_text_driver")
        if driver is not None:
            driver._ensure()
        return self._text_points

    @points.setter
    def points(self, value: ArrayLike) -> None:
        self._text_points = np.asarray(value, float)


def _text(
    system: mp.ThreeDAxes,
    point: object,
    s: str | Mobject,
    zdir: str | None = None,
    *,
    offset: bool = False,
    **kwargs: object,
) -> Mobject:
    text = s if isinstance(s, Mobject) else Text(s, **cast(dict[str, Any], kwargs))
    driver = _TextDriver(system, point, text, zdir, offset)
    cast(Any, text)._plot_driver = driver
    if not len(text.points):
        flats = driver._flats
        glyphs = [_TextGlyph(cast(VMobject, leaf), driver) for leaf, _ in flats]
        text.submobjects = list(glyphs)
        driver._flats = [
            (glyph, flat) for glyph, (_, flat) in zip(glyphs, flats, strict=True)
        ]
    text.add_updater(lambda mob: driver._ensure())
    return text


def _annotate(
    system: mp.ThreeDAxes,
    s: str | Mobject,
    xyz: object,
    xyztext: object = None,
    *,
    arrow: bool = True,
    **kwargs: object,
) -> HelperGroup:
    point = _data_point(xyz, "xyz")
    label = _text(
        system,
        xyz if xyztext is None else xyztext,
        s,
        offset=xyztext is None,
        **cast(dict[str, Any], kwargs),
    )
    group = HelperGroup()
    cast(Any, group).text = label
    cast(Any, group).arrow = None
    group.add(cast(VMobject, label))
    if not arrow:
        return group
    previous: FloatArray | None = None

    def derive(binding: _Binding) -> None:
        nonlocal previous
        end = system.c2p(*_read(binding, "xyz"))
        center = label.get_center()
        delta = end - center
        length = float(np.linalg.norm(delta))
        unit = delta / max(length, 1e-12) if length else np.array([1.0, 0, 0])
        start = label.get_boundary_point(unit)
        length = float(np.linalg.norm(end - start))
        unit = (end - start) / max(length, 1e-12)
        width, previous = _facing_basis(system, unit[None, :], previous)
        flat = Arrow(np.zeros(3), [length, 0, 0], buff=0)
        basis = np.stack((unit, width[0], previous[0]))
        binding.parts["line"] = binding.scene(start + flat.points @ basis)
        binding.parts["tip"] = binding.scene(start + flat.tip.points @ basis)

    binding = _Binding(
        system, derive, {**_inputs(point, "xyz", system), "label": label.get_center}
    )
    binding.ensure()
    template = Arrow()
    shaft = _VectorGroup(binding, "line", template)
    shaft.tip = _HelperShape(binding, "tip", template.tip)
    shaft.add(shaft.tip)
    system._register_field_view(shaft)
    cast(Any, group).arrow = shaft
    group.add(shaft)
    return group
