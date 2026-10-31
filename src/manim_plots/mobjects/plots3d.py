"""Composed three-dimensional plot artists and bound annotations."""

from __future__ import annotations

from typing import Any, Self, cast

import numpy as np
from manim import Arrow, ManimColor, Mobject, Text, ThreeDCamera, VGroup, VMobject
from manim.animation.transform import _MethodAnimation
from manim.typing import PathFuncType
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core.scales import Scale
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.artists import LinePlot, _CurvePlot, _cycle_style
from manim_plots.mobjects.colormaps import ColorMapping, resolve_colorscale
from manim_plots.mobjects.context import _drawing_camera, animation_context
from manim_plots.mobjects.fields import _facing_basis, _VectorGroup
from manim_plots.mobjects.geometry import _data_point, _ensure_binding, _inputs, _read
from manim_plots.mobjects.heatmaps import _mapping
from manim_plots.mobjects.helpers import HelperGroup, _Binding, _HelperShape
from manim_plots.mobjects.leaves import _STRAIGHT, _ArtistOptions, _VMStyle
from manim_plots.mobjects.projections import _juggle
from manim_plots.mobjects.surfaces import SurfacePlot, _Face

_BOX_FACES = np.array(
    [
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]],
        [[0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1]],
        [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]],
        [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]],
    ]
)


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


class _BarFace(_Face):
    pass


class _BarSurface(SurfacePlot):
    _growth: FloatArray | None = None
    _histogram: Hist3DPlot | None = None
    _depth_version = 0

    def _place_faces(self) -> None:
        super()._place_faces()
        self._depth_version += 1

    def _derive(self) -> None:
        self._building = True
        try:
            if self._histogram is not None:
                self._bar_corners = self._histogram._corners()
            self._corner_data = self._bar_corners.copy()
            growth = self.__dict__.get("_growth")
            if growth is not None:
                boxes = self._corner_data.reshape(-1, 6, 4, 3)
                base = boxes[:, 0, 0, 2].copy()
                boxes[..., 2] = base[:, None, None] + growth[:, None, None] * (
                    boxes[..., 2] - base[:, None, None]
                )
            self._centres = self._corner_data.mean(axis=1)
            mapped = self._system._data.forward(self._corner_data.reshape(-1, 3))
            self._local_faces = [
                VMobject().set_points_as_corners(np.vstack((c, c[:1]))).points
                for c in mapped.reshape(-1, 4, 3)
            ]
            self._clip_faces()
            if self._histogram is not None:
                for i, points in enumerate(self._local_faces):
                    if self._histogram.counts.ravel()[i // 6] < self._histogram._cmin:
                        self._local_faces[i] = points[:0]
            self._place_faces()
        finally:
            self._building = False

    _bar_corners: FloatArray


class _DepthOrderedPlot(VGroup):
    def get_family(self, recurse: bool = True) -> list[Mobject]:
        """Return the family after refreshing camera-space face depths.

        Parameters
        ----------
        recurse
            Passed through to Manim's family traversal.

        Returns
        -------
        list of Mobject
            The family with face identities and addressing unchanged.
        """
        surface = cast(_BarSurface | None, self.__dict__.get("_surface"))
        camera = _drawing_camera() if recurse and surface is not None else None
        if isinstance(camera, ThreeDCamera) and surface is not None:
            surface._driver._ensure()
            signature = (
                id(camera),
                camera.get_phi(),
                camera.get_theta(),
                camera.get_gamma(),
                surface._depth_version,
            )
            if self.__dict__.get("_depth_signature") != signature:
                rotation = camera.generate_rotation_matrix()
                for face in surface.faces:
                    face.z_index = float((face.get_center() @ rotation.T)[2])
                self._depth_signature = signature
        return super().get_family(recurse)


class BarPlot3D(_DepthOrderedPlot):
    """Draw six clipped, independently styleable faces per data box.

    Parameters
    ----------
    system, x, y, z, dx, dy, dz, color, shade, **style
        Axes, corners, side lengths, bar colours and fixed face lighting.
    c, colorscale, vmin, vmax, norm
        Per-bar values and colour normalization.
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
        *,
        c: object = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        **style: object,
    ) -> None:
        arrays = np.broadcast_arrays(
            *(np.asarray(a, float) for a in (x, y, z, dx, dy, dz))
        )
        if not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("bar coordinates and sizes must be finite")
        xyz = np.stack(arrays[:3], -1).reshape(-1, 3)
        sizes = np.stack(arrays[3:], -1).reshape(-1, 3)
        unit = _BOX_FACES
        self._color_mapping: mp.ColorMapping | None = None
        if c is not None:
            values = (
                arrays[5].ravel()
                if isinstance(c, str) and c == "height"
                else np.asarray(c, float)
            )
            if values.shape != (len(xyz),) or not np.isfinite(values).all():
                raise ValueError("c must contain one finite value per bar")
            self._color_mapping = resolve_colorscale(
                "viridis" if colorscale is None else colorscale,
                vmin=vmin,
                vmax=vmax,
                norm=cast(Any, norm),
                default_range=self._color_range(values),
            )
            color = self._color_mapping(values)
        self._shade = shade
        self._unit = unit
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
        for key, original in list(surface.faces._faces.items()):
            replacement = _BarFace(surface)
            replacement.match_style(original)
            replacement.points = original.points.copy()
            replacement._styled = False
            surface.faces._faces[key] = replacement
        surface.faces.submobjects = list(surface.faces._faces.values())
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

    def _color_range(self, values: FloatArray) -> tuple[float, float]:
        lo, hi = (
            (float(values.min()), float(values.max())) if len(values) else (0.0, 1.0)
        )
        return lo, hi if hi > lo else lo + 1

    @property
    def color_mapping(self) -> mp.ColorMapping | None:
        """Return the value colour mapping, when supplied."""
        return self._color_mapping


class Hist3DPlot(BarPlot3D):
    """Count paired samples into stable, shaded columns.

    Parameters
    ----------
    system, x, y, bins, range, density, weights
        Owning axes and NumPy histogram2d counting arguments.
    rwidth, cmin
        Relative cell width and minimum visible count.
    color, color_by, colorscale, vmin, vmax, norm, shade, **style
        Fixed colour, mapped values, normalization, lighting and face styles.
    """

    counts: FloatArray
    xedges: FloatArray
    yedges: FloatArray

    def __init__(
        self,
        system: mp.ThreeDAxes,
        x: ArrayLike,
        y: ArrayLike,
        bins: object = 10,
        *,
        range: object = None,
        density: bool = False,
        weights: ArrayLike | None = None,
        rwidth: float = 0.8,
        cmin: float = 1,
        color: object = None,
        color_by: str = "count",
        colorscale: object = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        shade: bool = True,
        **style: object,
    ) -> None:
        if color_by not in ("count", "x", "y"):
            raise ValueError("color_by must be count, x or y")
        if not np.isfinite([rwidth, cmin]).all() or rwidth < 0:
            raise ValueError("rwidth must be nonnegative and rwidth and cmin finite")
        self._hist_system = system
        self._density, self._rwidth, self._cmin = density, rwidth, cmin
        self._color_by, self._fixed_color = color_by, color
        self._mapping_options = dict(
            colorscale=colorscale, vmin=vmin, vmax=vmax, norm=norm
        )
        self.counts, self.xedges, self.yedges = np.histogram2d(
            np.asarray(x, float),
            np.asarray(y, float),
            bins=cast(Any, bins),
            range=cast(Any, range),
            density=density,
            weights=None if weights is None else np.asarray(weights, float),
        )
        cx, cy = np.meshgrid(
            (self.xedges[:-1] + self.xedges[1:]) / 2,
            (self.yedges[:-1] + self.yedges[1:]) / 2,
            indexing="ij",
        )
        wx, wy = np.meshgrid(
            np.diff(self.xedges) * rwidth, np.diff(self.yedges) * rwidth, indexing="ij"
        )
        self._xy, self._widths = (
            np.stack((cx - wx / 2, cy - wy / 2), -1),
            np.stack((wx, wy), -1),
        )
        values = self._values()
        super().__init__(
            system,
            cx - wx / 2,
            cy - wy / 2,
            self._floor(),
            wx,
            wy,
            self.counts,
            color,
            shade,
            c=values,
            **cast(Any, self._mapping_options),
            **cast(Any, style),
        )
        self._surface._histogram = self
        self._surface._derive()
        for face in self._surface.faces:
            cast(_Face, face)._styled = False

    def _floor(self) -> float:
        lo, hi = sorted(self._hist_system.z.range.value)
        return 0.0 if lo <= 0 <= hi else float(lo)

    def _color_range(self, values: FloatArray) -> tuple[float, float]:
        if self._color_by == "count":
            return super()._color_range(values[values >= self._cmin])
        edges = self.xedges if self._color_by == "x" else self.yedges
        return float(edges[0]), float(edges[-1])

    def _values(self) -> FloatArray | None:
        if self._fixed_color is not None:
            return None
        if self._color_by == "count":
            return self.counts.ravel()
        edges = self.xedges if self._color_by == "x" else self.yedges
        centres = (edges[:-1] + edges[1:]) / 2
        values: FloatArray = np.broadcast_to(
            centres[:, None] if self._color_by == "x" else centres[None, :],
            self.counts.shape,
        ).ravel()
        return values

    def _corners(self) -> FloatArray:
        xyz = np.column_stack(
            (self._xy.reshape(-1, 2), np.full(self.counts.size, self._floor()))
        )
        sizes = np.column_stack((self._widths.reshape(-1, 2), self.counts.ravel()))
        result: FloatArray = (
            xyz[:, None, None, :] + sizes[:, None, None, :] * self._unit
        ).reshape(-1, 4, 3)
        return result

    def at(self, key: tuple[int, int]) -> VGroup:
        """Return the six faces of a bin.

        Parameters
        ----------
        key
            X and y bin indices.
        """
        i, j = key
        if not (0 <= i < self.counts.shape[0] and 0 <= j < self.counts.shape[1]):
            raise KeyError(key)
        return cast(VGroup, self.bars[i * self.counts.shape[1] + j])

    def set_data(
        self, x: ArrayLike, y: ArrayLike, *, weights: ArrayLike | None = None
    ) -> Self:
        """Recount into stored edges and update existing faces.

        Parameters
        ----------
        x, y, weights
            Paired samples and optional sample weights.
        """
        self.counts = np.histogram2d(
            np.asarray(x, float),
            np.asarray(y, float),
            bins=cast(Any, (self.xedges, self.yedges)),
            density=self._density,
            weights=None if weights is None else np.asarray(weights, float),
        )[0]
        self._update_counts()
        return self

    def _update_counts(self) -> None:
        values = self._values()
        if values is not None:
            self._color_mapping = resolve_colorscale(
                default_range=self._color_range(values),
                **cast(Any, self._mapping_options),
            )
            colors = self._color_mapping(values)
            normals = np.array(
                [[0, 0, -1], [0, 0, 1], [0, -1, 0], [0, 1, 0], [-1, 0, 0], [1, 0, 0]]
            )
            factors = 0.3 + 0.35 * (1 + normals @ (np.array([-2, -2, 1]) / 3))
            for i, bar in enumerate(self.bars):
                for j, face in enumerate(bar):
                    if not face._styled:
                        face._paint(
                            ManimColor(colors[i] * (factors[j] if self._shade else 1))
                        )
        self._surface._derive()

    def align_data(self, mobject: Mobject, skip_point_alignment: bool = False) -> Self:
        """Select the data channel for native method animations.

        Parameters
        ----------
        mobject, skip_point_alignment
            Native target and alignment option.
        """
        active = isinstance(mobject, Hist3DPlot) and isinstance(
            animation_context(transform_only=True), _MethodAnimation
        )
        self._value_animation = active
        if isinstance(mobject, Hist3DPlot):
            mobject._value_animation = active
        super().align_data(mobject, skip_point_alignment)
        return self

    def family_members_with_points(self) -> list[Mobject]:
        """Rebuild bin geometry after native child interpolation."""
        if self.__dict__.get("_value_animation", False):
            return [
                m
                for m in self.get_family()
                if isinstance(m, _BarFace) or m.has_points()
            ] + [self]
        return super().family_members_with_points()

    def resume_updating(self, recursive: bool = True) -> Self:
        """Return derived bins to ordinary binding after interpolation.

        Parameters
        ----------
        recursive
            Whether to resume descendants.
        """
        super().resume_updating(recursive)
        self._value_animation = False
        self._update_counts()
        return self

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType = _STRAIGHT,
    ) -> Self:
        """Rebuild columns and their colours from interpolated bin counts.

        Parameters
        ----------
        mobject1, mobject2, alpha, path_func
            Native endpoints, progress and path.
        """
        if self.__dict__.get("_value_animation", False):
            assert isinstance(mobject1, Hist3DPlot) and isinstance(mobject2, Hist3DPlot)
            self.counts = (1 - alpha) * mobject1.counts + alpha * mobject2.counts
            self._update_counts()
            return self
        return super().interpolate(mobject1, mobject2, alpha, path_func)


class VoxelPlot(_DepthOrderedPlot):
    """Draw the exposed faces of a boolean voxel grid.

    Parameters
    ----------
    system, *args
        Owning axes and filled array, or x, y, z corner arrays and filled.
    facecolors, edgecolors, shade
        Per-voxel or uniform fill, edge colour and fixed face lighting.
    c, colorscale, vmin, vmax, norm, **style
        Per-voxel scalar values, colour normalisation and face style.
    """

    def __init__(
        self,
        system: mp.ThreeDAxes,
        *args: ArrayLike,
        facecolors: object = None,
        edgecolors: object = None,
        shade: bool = True,
        c: ArrayLike | None = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        **style: object,
    ) -> None:
        if len(args) not in (1, 4):
            raise TypeError("voxels expects filled or x, y, z, filled")
        filled = np.asarray(args[-1], bool)
        if filled.ndim != 3:
            raise ValueError("filled must be three-dimensional")
        shape = tuple(n + 1 for n in filled.shape)
        coordinates = (
            np.indices(shape, dtype=float)
            if len(args) == 1
            else np.stack(
                np.broadcast_arrays(*(np.asarray(a, float) for a in args[:3]))
            )
        )
        if coordinates.shape != (3, *shape) or not np.isfinite(coordinates).all():
            raise ValueError("corner arrays must match filled.shape + 1 and be finite")
        options = style.copy()
        self.color_mapping: ColorMapping | None = None
        if c is not None:
            if facecolors is not None:
                raise ValueError("c and facecolors are mutually exclusive")
            values = np.asarray(c, float)
            if values.shape != filled.shape or not np.isfinite(values[filled]).all():
                raise ValueError("c must match filled and be finite in filled voxels")
            self.color_mapping = _mapping(
                values[filled],
                "viridis" if colorscale is None else colorscale,
                vmin,
                vmax,
                norm,
            )
            colors = np.zeros((*filled.shape, 3))
            colors[filled] = self.color_mapping(values[filled])
        else:
            if facecolors is None:
                _cycle_style(system, cast(_VMStyle, options))
                facecolors = options.pop("color")
            if isinstance(facecolors, (str, ManimColor)):
                colors = np.broadcast_to(
                    ManimColor(facecolors).to_rgb(), (*filled.shape, 3)
                )
            else:
                supplied = np.asarray(facecolors)
                if supplied.shape in ((3,), (4,)) and supplied.dtype.kind in "biuf":
                    colors = np.broadcast_to(
                        ManimColor(supplied).to_rgb(), (*filled.shape, 3)
                    )
                elif supplied.shape == filled.shape or supplied.shape in (
                    (*filled.shape, 3),
                    (*filled.shape, 4),
                ):
                    colors = np.array(
                        [
                            ManimColor(v).to_rgb()
                            for v in supplied.reshape(
                                (-1,)
                                if supplied.shape == filled.shape
                                else (-1, supplied.shape[-1])
                            )
                        ]
                    ).reshape(*filled.shape, 3)
                else:
                    raise ValueError("facecolors must contain one colour per voxel")
        masks = []
        for axis, direction in ((2, -1), (2, 1), (1, -1), (1, 1), (0, -1), (0, 1)):
            neighbour = np.zeros_like(filled)
            target, source = [slice(None)] * 3, [slice(None)] * 3
            target[axis] = slice(1, None) if direction < 0 else slice(None, -1)
            source[axis] = slice(None, -1) if direction < 0 else slice(1, None)
            neighbour[tuple(target)] = filled[tuple(source)]
            masks.append(filled & ~neighbour)
        exposed = np.stack(masks, axis=-1)
        keys = np.argwhere(exposed)
        indices = keys[:, :3]
        corner_indices = indices[:, None, :] + _BOX_FACES[keys[:, 3]]
        corners = coordinates[
            tuple([slice(None), *corner_indices.transpose(2, 0, 1)])
        ].transpose(1, 2, 0)
        surface = _BarSurface.__new__(_BarSurface)
        surface._bar_corners = corners
        options.setdefault("stroke_width", 0 if edgecolors is None else 1)
        if edgecolors is not None:
            options["stroke_color"] = edgecolors
        _BarSurface.__init__(
            surface,
            system,
            lambda u, v: 0,
            resolution=(len(keys), 1),
            **cast(dict[str, Any], options),
        )
        normals = np.array(
            [[0, 0, -1], [0, 0, 1], [0, -1, 0], [0, 1, 0], [-1, 0, 0], [1, 0, 0]]
        )
        factors = 0.3 + 0.35 * (1 + normals @ (np.array([-2, -2, 1]) / 3))
        self._voxels: dict[tuple[int, int, int], VGroup] = {}
        for row, face in zip(keys, surface.faces, strict=True):
            key = (int(row[0]), int(row[1]), int(row[2]))
            self._voxels.setdefault(key, VGroup()).add(face)
            face.shade_in_3d = False
            face.set_fill(
                ManimColor(colors[key] * (factors[row[3]] if shade else 1)),
                opacity=cast(float, style.get("fill_opacity", 1)),
            )
            if edgecolors is not None:
                face.set_stroke(
                    cast(Any, edgecolors),
                    width=cast(float, options["stroke_width"]),
                )
        self._surface = surface
        super().__init__(surface)

    def at(self, key: tuple[int, int, int]) -> VGroup:
        """Return stable exposed faces in bottom, top, y, x order.

        Parameters
        ----------
        key
            Voxel indices; unfilled and interior voxels have no drawn faces.

        Returns
        -------
        VGroup
            Independently styleable faces of the voxel.
        """
        return self._voxels.get(key, VGroup())


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
