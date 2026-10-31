"""Occupancy, scalar-level and coordinate transitions in three dimensions."""

from __future__ import annotations

import copy
from typing import Any, cast

import numpy as np
from manim import ManimColor, VGroup, VMobject

from manim_plots.core.params import Parameter
from manim_plots.core.shape import marching_cubes
from manim_plots.mobjects.artists import ParametricPlot
from manim_plots.mobjects.geometry import _ensure_binding
from manim_plots.mobjects.plots3d import _BOX_FACES, VoxelPlot
from manim_plots.mobjects.slice_view import SliceView
from manim_plots.mobjects.surfaces import ContourPlot, SurfacePlot, _Face

from ._base import MappedPresentation, Presentation, flags, window


class StackVoxels(MappedPresentation):
    """Fade successively occupied voxel layers and their exposed faces.

    Parameters
    ----------
    voxels, axis, direction, lag_ratio, reverse, remover, **kwargs
        Bound voxels, layer schedule, playback/removal flags and Manim options.
    """

    def __init__(
        self,
        voxels: VoxelPlot,
        *,
        axis: str = "z",
        direction: int = 1,
        lag_ratio: float = 0.1,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(voxels, VoxelPlot):
            raise TypeError("voxels must be a VoxelPlot")
        if axis not in ("x", "y", "z") or direction not in (-1, 1):
            raise ValueError("axis must be x/y/z and direction must be ±1")
        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        self.voxels, self.axis, self.direction, self.reverse = (
            voxels,
            "xyz".index(axis),
            direction,
            reverse,
        )
        flags(reverse, remover, kwargs)
        super().__init__(voxels, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Retain canonical faces and supply temporarily exposed interfaces."""
        block = self.voxels
        surface = block._surface
        self._canonical_faces = surface.faces._faces.copy()
        self._canonical_corners = surface._bar_corners
        self._canonical_voxels = block._voxels
        self._derive = surface._derive
        keys = np.argwhere(block._filled)
        self._layers = sorted(
            set(int(key[self.axis]) for key in keys), reverse=self.direction < 0
        )
        canonical = {
            tuple(row): cast(_Face, face)
            for row, face in zip(block._face_keys, surface.faces, strict=True)
        }
        self._keys = [
            (int(key[0]), int(key[1]), int(key[2]), side)
            for key in keys
            for side in range(6)
        ]
        self._faces: list[_Face] = []
        corners = []
        for key in self._keys:
            cell, side = (key[0], key[1], key[2]), key[3]
            face = canonical.get(key)
            if face is None:
                face = _Face(
                    surface,
                    fill_opacity=surface._opacity,
                    stroke_width=surface._stroke_width,
                )
                originals = block.at(cell)
                if len(originals):
                    face.match_style(originals[0])
                face.set_fill(ManimColor(block._voxel_colors[cell]))
                face._styled = True
            self._faces.append(face)
            indices = np.array(cell) + _BOX_FACES[side]
            corners.append(block._coordinates[tuple([slice(None), *indices.T])].T)
        self._styles = [copy.deepcopy(face.get_style()) for face in self._faces]
        surface.faces._faces = dict(enumerate(self._faces))
        surface.faces.submobjects = list(self._faces)
        surface._bar_corners = np.asarray(corners, float).reshape(-1, 4, 3)
        surface.__dict__["_derive"] = self._occupancy
        self._alpha = 0
        super().begin()

    def _occupancy(self) -> None:
        surface = self.voxels._surface
        self._derive()
        progress = {
            layer: self.rate_func(
                window(
                    1 - self._alpha if self.reverse else self._alpha,
                    i,
                    len(self._layers),
                    self.lag_ratio,
                )
            )
            for i, layer in enumerate(self._layers)
        }
        active = {key[:3] for key in self._keys if progress[key[self.axis]] > 0}
        groups: dict[tuple[int, int, int], VGroup] = {}
        directions = ((2, -1), (2, 1), (1, -1), (1, 1), (0, -1), (0, 1))
        for i, (key, face, style) in enumerate(
            zip(self._keys, self._faces, self._styles, strict=True)
        ):
            cell = (key[0], key[1], key[2])
            axis, direction = directions[key[3]]
            neighbour = list(cell)
            neighbour[axis] += direction
            visible = cell in active and tuple(neighbour) not in active
            if not visible:
                surface._local_faces[i] = np.empty((0, 3))
            else:
                groups.setdefault(cell, VGroup()).add(face)
            face.set_style(**style)
            p = progress[cell[self.axis]]
            VMobject.set_fill(face, opacity=style["fill_opacity"].copy() * p)
            face.set_stroke(opacity=style["stroke_opacity"] * p)
        self.voxels._voxels = groups
        surface._place_faces()

    def interpolate_mobject(self, alpha: float) -> None:
        """Derive exposed faces from absolute layer progress."""
        self._alpha = alpha
        self._occupancy()

    def restore(self) -> None:
        """Restore canonical occupancy, face identities and styles."""
        super().restore()
        surface = self.voxels._surface
        surface.__dict__.pop("_derive", None)
        for face, style in zip(self._faces, self._styles, strict=True):
            face.set_style(**style)
            if face not in self._canonical_faces.values():
                face.clear_points()
        surface.faces._faces = self._canonical_faces
        surface.faces.submobjects = list(self._canonical_faces.values())
        surface._bar_corners = self._canonical_corners
        self.voxels._voxels = self._canonical_voxels
        surface._driver._dirty = True
        surface._driver._ensure()


class SweepIsovalue(Presentation):
    """Extract each interpolated level from an isosurface's retained samples.

    Parameters
    ----------
    surface, level, **kwargs
        Isosurface, finite target scalar level and Manim options.
    """

    def __init__(self, surface: SurfacePlot, level: float, **kwargs: object) -> None:
        if not isinstance(surface, SurfacePlot) or "_isovalue" not in surface.__dict__:
            raise TypeError("surface must come from plot_isosurface")
        if not np.isfinite(level):
            raise ValueError("level must be finite")
        self.surface, self.level = surface, level
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(surface, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Acquire exclusive level ownership from the current scalar value."""
        if self.surface.__dict__.get("_data_writer") is not None:
            raise ValueError("concurrent isovalue writers conflict")
        self._start = float(self.surface.__dict__["_isovalue"])
        self.surface.__dict__["_data_writer"] = self
        self._style = self.surface.__dict__.get("_iso_style")
        if len(self.surface.faces):
            face = cast(_Face, self.surface.faces[0])
            if face._styled:
                self._style = copy.deepcopy(face.get_style())
        self.surface.__dict__["_iso_style"] = self._style
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Replace triangles with an honest extraction at the current level."""
        p = self.rate_func(alpha)
        level = (1 - p) * self._start + p * self.level
        self._set_level(level)

    def _set_level(self, level: float) -> None:
        surface = self.surface
        samples, spacing, origin = surface.__dict__["_iso_samples"]
        vertices, triangles = marching_cubes(samples, level, spacing, origin)
        surface._building = True
        try:
            for face in surface.faces:
                face.clear_points()
            faces: dict[tuple[int, int] | int, _Face] = {}
            for i in range(len(triangles)):
                face = _Face(
                    surface,
                    fill_opacity=surface._opacity,
                    stroke_width=surface._stroke_width,
                )
                if self._style is not None:
                    face.set_style(**self._style)
                faces[i] = face
            surface.faces._faces = faces
            surface.faces.submobjects = list(faces.values())
            surface._vertices, surface._triangles = vertices, triangles
            surface.__dict__["_isovalue"] = level
        finally:
            surface._building = False
        surface._driver._dirty = True
        surface._driver._ensure()

    def restore(self) -> None:
        """Commit the requested scalar level and release the writer."""
        if self.surface.__dict__.get("_data_writer") is self:
            self._set_level(self.level)
            self.surface.__dict__.pop("_data_writer")


class SweepSlice(Presentation):
    """Move a coordinate section and its optional plane and profile together.

    Parameters
    ----------
    view, stop, **kwargs
        SliceView or coordinate slice, finite target coordinate and Manim options.
    """

    def __init__(
        self,
        view: SliceView | ParametricPlot | ContourPlot,
        stop: float,
        **kwargs: object,
    ) -> None:
        if not np.isfinite(stop):
            raise ValueError("stop must be finite")
        self.view, self.stop = view, stop
        self._parameters: list[Parameter[Any]] = []
        self._bindings: list[Any] = []
        if isinstance(view, SliceView):
            name = view.plane._input_name
            if name not in ("x", "y"):
                raise ValueError("SliceView must have an axis-aligned x/y plane")
            axis = "xy".index(name)
            self._parameters.append(view.plane._binding.parameters[f"point{axis}"])
            self._bindings.append(view.plane._binding)
            parts = [view.cut, view.profile]
        else:
            parts = [view]
        for part in parts:
            lines = (
                list(part._lines.values()) if isinstance(part, ContourPlot) else [part]
            )
            for line in lines:
                binding = getattr(line, "_slice_binding", None) or getattr(
                    line, "_binding", None
                )
                if binding is None or "coordinate" not in binding.parameters:
                    raise TypeError("view must be a coordinate slice or SliceView")
                self._bindings.append(binding)
                self._parameters.append(binding.parameters["coordinate"])
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(view, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Read the current coordinate and retain all original tracker bindings."""
        if self.view.__dict__.get("_data_writer") is not None:
            raise ValueError("concurrent slice writers conflict")
        for binding in self._bindings:
            _ensure_binding(binding)
        self._start = float(self._parameters[0].value)
        self.view.__dict__["_data_writer"] = self
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Write one absolute coordinate before deriving all dependent parts."""
        p = self.rate_func(alpha)
        value = (1 - p) * self._start + p * self.stop
        self._set_coordinate(value)

    def _set_coordinate(self, value: float) -> None:
        for parameter in self._parameters:
            tracker = parameter.tracker
            setter = getattr(tracker, "set_value", None)
            if callable(setter):
                setter(value)
                parameter.poll()
            else:
                parameter.value = value
        for binding in self._bindings:
            _ensure_binding(binding)
        for part in self.view.get_family():
            refresh = getattr(part, "refresh", None)
            if callable(refresh):
                refresh()

    def restore(self) -> None:
        """Commit the target while leaving each part and updater in place."""
        if self.view.__dict__.get("_data_writer") is self:
            self._set_coordinate(self.stop)
            self.view.__dict__.pop("_data_writer")
