"""Bound cell grids, hexagonal bins and array contours."""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from typing import Any, Self, cast

import numpy as np
from manim import ManimColor, Text, VGroup, VMobject
from numpy.typing import ArrayLike

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core.nodes import FrameMap
from manim_plots.core.payload import Payload
from manim_plots.core.scales import Scale
from manim_plots.core.shape import (
    _assemble,
    _cut_polygon,
    corners,
    filled_marching_squares,
    marching_squares,
    smooth,
)
from manim_plots.core.shape import clip as clip_path
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.artists import _CurvePlot
from manim_plots.mobjects.colormaps import ColorMapping, resolve_colorscale
from manim_plots.mobjects.surfaces import _FaceStyle


def _label_color(
    background: ManimColor,
    colors: Sequence[str] = ("black", "white"),
    threshold: float = 0.5,
) -> str:
    return colors[
        int(np.dot(background.to_rgb(), [0.2126, 0.7152, 0.0722]) < threshold)
    ]


class _Cell(_FaceStyle, _CurvePlot):
    def __init__(
        self, owner: HeatmapPlot, polygon: FloatArray, index: int, **style: object
    ) -> None:
        self._owner, self._polygon, self._index = owner, polygon, index
        self._styled = False
        style.setdefault("color", "white")
        super().__init__(
            ArraySource(np.empty((0, 2))),
            owner._system,
            use_smoothing=False,
            **cast(dict[str, Any], style),
        )
        self._styled = False
        owner._system.add(self)

    def get_fill_color(self) -> ManimColor:
        self._ensure()
        return super().get_fill_color()

    def _rebuild(self) -> None:
        system = self._owner._system
        polygon = self._polygon.copy()
        if not np.isfinite(self._owner._values[self._index]):
            polygon = np.empty((0, 2))
        for axis, coordinate in enumerate(system._ranges):
            lo, hi = sorted(coordinate.range.value)
            polygon = _cut_polygon(
                _cut_polygon(polygon, axis, lo, True), axis, hi, False
            )
        if len(polygon):
            polygon = np.vstack((polygon, polygon[:1]))
        self._geometry_payload = corners(
            Payload.path(system._data.forward(polygon)), system.bounds
        )
        self._place(self._frame())
        self._data_seen = system._data_version
        self._dirty = False

    def _place(self, frame: FrameMap) -> None:
        super()._place(frame)
        label = self._owner.__dict__.get("_label_objects", {}).get(self._index)
        if label is not None:
            label.set_opacity(float(bool(len(self._geometry_payload.coords))))
            center = self._owner._system._data.forward(self._polygon.mean(axis=0)[None])
            label.move_to(frame.forward(center)[0])


class _CellGroup(VGroup):
    def __init__(self, cells: dict[tuple[int, int] | int, _Cell]) -> None:
        self._cells = cells
        super().__init__(*cells.values())

    def at(self, key: tuple[int, int] | int) -> _Cell:
        """Return the stable cell at a grid index or bin number.

        Parameters
        ----------
        key
            Row and column pair, or hexagonal bin index.
        """
        return self._cells[key]


def _matrix(value: ArrayLike) -> FloatArray:
    result = np.asarray(value, float)
    if result.ndim != 2 or not result.size:
        raise ValueError("values must be a nonempty two-dimensional array")
    return result


def _mapping(
    values: FloatArray,
    colorscale: object,
    vmin: float | None,
    vmax: float | None,
    norm: Scale | str | None,
) -> ColorMapping:
    finite = values[np.isfinite(values)]
    lo, hi = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
    if lo == hi:
        lo, hi = lo - 0.5, hi + 0.5
    return resolve_colorscale(
        colorscale, vmin=vmin, vmax=vmax, norm=norm, default_range=(lo, hi)
    )


class HeatmapPlot(VGroup):
    """Draw stable, individually styleable polygons of a scalar grid.

    Parameters
    ----------
    system
        Owning two-dimensional axes.
    X, Y, C
        Corner coordinate grids and cell values.
    colorscale, vmin, vmax, norm
        Colormap and value normalisation.
    **style
        Manim cell style.
    """

    counts: FloatArray
    xedges: FloatArray
    yedges: FloatArray

    def __init__(
        self,
        system: mp.CartesianAxes,
        X: ArrayLike,
        Y: ArrayLike,
        C: ArrayLike,
        *,
        colorscale: object = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        norm: Scale | str | None = None,
        **style: object,
    ) -> None:
        self._initialize(system, _matrix(C), colorscale, vmin, vmax, norm, style)
        xs, ys = np.asarray(X, float), np.asarray(Y, float)
        if xs.shape != ys.shape or xs.shape != tuple(n + 1 for n in self._data.shape):
            raise ValueError("corner grids must have shape (rows + 1, columns + 1)")
        if not np.isfinite(xs).all() or not np.isfinite(ys).all():
            raise ValueError("corners must be finite")
        grid = np.stack((xs, ys), axis=-1)
        polygons = np.stack(
            (grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]), axis=-2
        )
        self.cells = _CellGroup(
            {
                (i, j): _Cell(
                    self, polygons[i, j], i * self._data.shape[1] + j, **style
                )
                for i, j in np.ndindex(self._data.shape)
            }
        )
        self.add(self.cells)
        self._paint_cells()

    def _initialize(
        self,
        system: mp.CartesianAxes,
        C: ArrayLike,
        colorscale: object,
        vmin: float | None,
        vmax: float | None,
        norm: Scale | str | None,
        style: dict[str, Any],
    ) -> None:
        self._system = system
        self._data = np.asarray(C, float).copy()
        self._values = self._data.ravel()
        self._colorscale, self._vmin, self._vmax, self._norm = (
            colorscale,
            vmin,
            vmax,
            norm,
        )
        self._opacity = style.setdefault("fill_opacity", 1.0)
        style.setdefault("stroke_width", 0.0)
        self._color_mapping = _mapping(self._values, colorscale, vmin, vmax, norm)
        super().__init__()

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            result.__dict__[key] = (
                value if key == "_system" else copy.deepcopy(value, memo)
            )
        return result

    @property
    def color_mapping(self) -> ColorMapping:
        """Return the current scalar-to-colour mapping."""
        return self._color_mapping

    def _paint_cells(self) -> None:
        for cell in self.cells._cells.values():
            value = self._values[cell._index]
            if not cell._styled and np.isfinite(value):
                cell._paint(ManimColor.from_rgb(self._color_mapping(value)))

    def set_data(self, C: ArrayLike) -> Self:
        """Replace values in place, retaining the grid and individual styles.

        Parameters
        ----------
        C
            New values with the original shape.
        """
        values = _matrix(C)
        if values.shape != self._data.shape:
            raise ValueError("set_data requires the original shape")
        mapping = _mapping(values, self._colorscale, self._vmin, self._vmax, self._norm)
        self._data = values.copy()
        self._values = self._data.ravel()
        self._color_mapping = mapping
        for cell in self.cells._cells.values():
            cell._dirty = True
            cell._ensure()
        self._paint_cells()
        if hasattr(self, "_labels"):
            self._update_labels()
        return self

    def label_cells(
        self,
        fmt: str = "{:.2g}",
        colors: Sequence[str] = ("black", "white"),
        threshold: float | None = None,
        **text_style: object,
    ) -> VGroup:
        """Label visible cells using contrasting text that follows the grid.

        Parameters
        ----------
        fmt, colors, threshold
            Value format, light/dark text colours and luminance cutoff (0.5).
        **text_style
            Manim Text options.

        Returns
        -------
        VGroup
            Bound cell labels.
        """
        self._label_options = (
            fmt,
            colors,
            0.5 if threshold is None else threshold,
            text_style,
        )
        if not hasattr(self, "_labels"):
            self._labels = VGroup()
            self._label_objects: dict[int, Text] = {}
            self._labels.add_updater(lambda _: self._update_labels())
            self.add(self._labels)
        self._update_labels()
        return self._labels

    def _update_labels(self) -> None:
        fmt, colors, threshold, style = self._label_options
        visible: list[VMobject] = []
        for cell in self.cells._cells.values():
            if not cell.has_points():
                continue
            index = cell._index
            text = fmt.format(self._values[index])
            label = self._label_objects.get(index)
            if label is None:
                label = Text(text, **cast(dict[str, Any], style))
                self._label_objects[index] = label
            elif label.text != text:
                label.become(Text(text, **cast(dict[str, Any], style)))
                label.text = text
            label.set_color(_label_color(cell.get_fill_color(), colors, threshold))
            label.move_to(self._system.c2p(*cell._polygon.mean(axis=0)))
            visible.append(label)
        self._labels.submobjects = visible


def _imshow(
    system: mp.CartesianAxes,
    Z: ArrayLike,
    *,
    extent: Sequence[float] | None = None,
    origin: str = "upper",
    **style: object,
) -> HeatmapPlot:
    values = _matrix(Z)
    m, n = values.shape
    if origin not in {"upper", "lower"}:
        raise ValueError("origin must be upper or lower")
    left, right, bottom, top = (
        (-0.5, n - 0.5, -0.5, m - 0.5) if extent is None else extent
    )
    xs = np.linspace(left, right, n + 1)
    ys = np.linspace(bottom, top, m + 1)
    if origin == "upper":
        ys = ys[::-1]
    X, Y = np.meshgrid(xs, ys)
    return HeatmapPlot(system, X, Y, values, **cast(dict[str, Any], style))


def _edges(centres: FloatArray, axis: int) -> FloatArray:
    moved = np.moveaxis(centres, axis, 0)
    if len(moved) < 2:
        raise ValueError("nearest shading requires at least two centres per axis")
    middle = (moved[:-1] + moved[1:]) / 2
    return np.moveaxis(
        np.concatenate(
            (2 * moved[:1] - middle[:1], middle, 2 * moved[-1:] - middle[-1:])
        ),
        0,
        axis,
    )


def _pcolormesh(
    system: mp.CartesianAxes,
    X: ArrayLike,
    Y: ArrayLike | None = None,
    C: ArrayLike | None = None,
    *,
    shading: str = "auto",
    **style: object,
) -> HeatmapPlot:
    if shading not in {"auto", "flat", "nearest"}:
        raise ValueError("shading must be auto, flat or nearest")
    if C is None:
        if Y is not None:
            raise ValueError("C is required when Y is supplied")
        values = _matrix(X)
        X, Y = np.meshgrid(
            np.arange(values.shape[1] + 1), np.arange(values.shape[0] + 1)
        )
    else:
        values = _matrix(C)
    xs, ys = np.asarray(X, float), np.asarray(Y, float)
    if xs.ndim == ys.ndim == 1:
        xs, ys = np.meshgrid(xs, ys)
    if xs.shape == ys.shape == values.shape and shading in {"auto", "nearest"}:
        xs, ys = (_edges(_edges(grid, 1), 0) for grid in (xs, ys))
    elif shading == "nearest":
        raise ValueError("nearest shading requires matching centres and values")
    return HeatmapPlot(system, xs, ys, values, **cast(dict[str, Any], style))


class HexbinPlot(HeatmapPlot):
    """Draw occupied bins of two interleaved hexagonal lattices.

    Parameters
    ----------
    system, x, y, C
        Owning axes, sample coordinates and optional sample values.
    gridsize, reduce_C_function, mincnt, extent
        Horizontal lattice size, reducer, minimum occupancy and data rectangle.
    colorscale, **style
        Colour mapping and cell style.
    """

    def __init__(
        self,
        system: mp.CartesianAxes,
        x: ArrayLike,
        y: ArrayLike,
        C: ArrayLike | None = None,
        *,
        gridsize: int = 10,
        reduce_C_function: Callable[[FloatArray], float] = np.mean,
        mincnt: int | None = None,
        extent: Sequence[float] | None = None,
        colorscale: object = "viridis",
        **style: object,
    ) -> None:
        xs, ys = np.asarray(x, float), np.asarray(y, float)
        if xs.ndim != 1 or xs.shape != ys.shape:
            raise ValueError("x and y must be matching one-dimensional arrays")
        cs = None if C is None else np.asarray(C, float)
        if cs is not None and cs.shape != xs.shape:
            raise ValueError("C must match x and y")
        if isinstance(gridsize, bool) or not isinstance(gridsize, int) or gridsize < 2:
            raise ValueError("gridsize must be an integer of at least two")
        if mincnt is not None and mincnt < 0:
            raise ValueError("mincnt must be nonnegative")
        valid = np.isfinite(xs) & np.isfinite(ys)
        if cs is not None:
            valid &= np.isfinite(cs)
        if extent is None:
            if not valid.any():
                raise ValueError("extent is required for empty samples")
            limits = [
                float(xs[valid].min()),
                float(xs[valid].max()),
                float(ys[valid].min()),
                float(ys[valid].max()),
            ]
            for a in (0, 2):
                if limits[a] == limits[a + 1]:
                    limits[a] -= 0.5
                    limits[a + 1] += 0.5
        else:
            limits = list(extent)
        if len(limits) != 4 or not np.isfinite(limits).all():
            raise ValueError("extent must contain four finite bounds")
        xmin, xmax, ymin, ymax = limits
        if xmin >= xmax or ymin >= ymax:
            raise ValueError("extent must have positive width and height")
        nx, ny = gridsize, int(gridsize / np.sqrt(3))
        sx, sy = (xmax - xmin) / nx, (ymax - ymin) / ny
        valid &= (xs >= xmin) & (xs <= xmax) & (ys >= ymin) & (ys <= ymax)
        points = np.column_stack(((xs[valid] - xmin) / sx, (ys[valid] - ymin) / sy))
        first = np.rint(points)
        second = np.floor(points) + 0.5
        d1 = (points[:, 0] - first[:, 0]) ** 2 + 3 * (points[:, 1] - first[:, 1]) ** 2
        d2 = (points[:, 0] - second[:, 0]) ** 2 + 3 * (points[:, 1] - second[:, 1]) ** 2
        chosen = np.where((d1 < d2)[:, None], first, second)
        centres, inverse, counts = np.unique(
            chosen, axis=0, return_inverse=True, return_counts=True
        )
        keep = counts >= max(1, 0 if mincnt is None else mincnt)
        self.values = (
            counts.astype(float)
            if cs is None
            else np.array(
                [reduce_C_function(cs[valid][inverse == i]) for i in range(len(counts))]
            )
        )[keep]
        self.centers = centres[keep] * [sx, sy] + [xmin, ymin]
        self._initialize(
            system,
            self.values.reshape(1, -1),
            colorscale,
            cast(float | None, style.pop("vmin", None)),
            cast(float | None, style.pop("vmax", None)),
            cast(Scale | str | None, style.pop("norm", None)),
            style,
        )
        vertices = np.array(
            [
                [0.5, -1 / 6],
                [0.5, 1 / 6],
                [0, 1 / 3],
                [-0.5, 1 / 6],
                [-0.5, -1 / 6],
                [0, -1 / 3],
            ]
        ) * [sx, sy]
        self.cells = _CellGroup(
            {
                i: _Cell(self, center + vertices, i, **cast(dict[str, Any], style))
                for i, center in enumerate(self.centers)
            }
        )
        self.add(self.cells)
        self._paint_cells()


def _hist2d(
    system: mp.CartesianAxes,
    x: ArrayLike,
    y: ArrayLike,
    bins: int | Sequence[ArrayLike] = 10,
    *,
    range: Sequence[Sequence[float]] | None = None,
    density: bool = False,
    weights: ArrayLike | None = None,
    cmin: float | None = None,
    cmax: float | None = None,
    **style: object,
) -> HeatmapPlot:
    counts, xe, ye = np.histogram2d(
        np.asarray(x, float),
        np.asarray(y, float),
        bins=cast(Any, bins),
        range=range,
        density=density,
        weights=None if weights is None else np.asarray(weights, float),
    )
    values = counts.T.copy()
    if cmin is not None:
        values[values < cmin] = np.nan
    if cmax is not None:
        values[values > cmax] = np.nan
    result = _pcolormesh(system, xe, ye, values, **cast(dict[str, Any], style))
    result.counts, result.xedges, result.yedges = counts, xe, ye
    return result


class _ContourLevel(_CurvePlot):
    def __init__(
        self,
        system: mp.CartesianAxes,
        paths: list[FloatArray],
        filled: bool,
        **style: object,
    ) -> None:
        self._paths, self._filled = paths, filled
        super().__init__(
            ArraySource(np.empty((0, 2))), system, **cast(dict[str, Any], style)
        )
        system.add(self)

    def _rebuild(self) -> None:
        system = self._system
        assert system is not None
        paths = []
        for path in self._paths:
            if self._filled:
                path = path[:-1]
                for axis, coordinate in enumerate(system._ranges):
                    lo, hi = sorted(coordinate.range.value)
                    path = _cut_polygon(
                        _cut_polygon(path, axis, lo, True), axis, hi, False
                    )
                if len(path) < 3:
                    continue
                path = np.vstack((path, path[:1]))
            paths.append(system._data.forward(path))
        payload = _assemble(paths, 2)
        payload = (corners if self._filled else smooth)(payload, system.bounds)
        if not self._filled:
            payload = clip_path(payload, system.bounds)
        self._geometry_payload = payload
        self._place(self._frame())
        self._data_seen = system._data_version
        self._dirty = False


class ContourSetPlot(VGroup):
    """Draw bound level curves or filled scalar bands of an array grid.

    Parameters
    ----------
    system, X, Y, Z
        Owning axes, coordinate grids or vectors, and scalar values.
    levels
        Increasing levels, a positive count, or None for seven.
    filled, colorscale, **style
        Fill bands instead of lines, colormap, and Manim style.
    """

    def __init__(
        self,
        system: mp.CartesianAxes,
        X: ArrayLike,
        Y: ArrayLike,
        Z: ArrayLike,
        levels: Sequence[float] | int | None = None,
        *,
        filled: bool = False,
        colorscale: object = "viridis",
        **style: object,
    ) -> None:
        xs, ys, zs = np.asarray(X, float), np.asarray(Y, float), _matrix(Z)
        if xs.ndim == ys.ndim == 1:
            xs, ys = np.meshgrid(xs, ys)
        if xs.shape != zs.shape or ys.shape != zs.shape or min(zs.shape) < 2:
            raise ValueError(
                "X, Y and Z must define matching grids of at least two by two"
            )
        if not np.isfinite(xs).all() or not np.isfinite(ys).all():
            raise ValueError("coordinates must be finite")
        finite = zs[np.isfinite(zs)]
        if not finite.size:
            raise ValueError("Z must contain finite values")
        lo, hi = float(finite.min()), float(finite.max())
        if levels is None:
            levels = 7
        if isinstance(levels, int):
            if isinstance(levels, bool) or levels < 1 or hi <= lo:
                raise ValueError(
                    "level count requires a positive count and nonconstant data"
                )
            edges = (
                np.linspace(lo, hi, levels + 1)
                if filled
                else np.linspace(lo, hi, levels + 2)[1:-1]
            )
        else:
            edges = np.asarray(levels, float)
        if (
            edges.ndim != 1
            or len(edges) < (2 if filled else 1)
            or not np.isfinite(edges).all()
            or np.any(np.diff(edges) <= 0)
        ):
            raise ValueError("levels must be finite and strictly increasing")
        self.levels = edges
        self.color_mapping = _mapping(
            zs,
            "viridis" if colorscale is None else colorscale,
            cast(float | None, style.pop("vmin", None)),
            cast(float | None, style.pop("vmax", None)),
            cast(Scale | str | None, style.pop("norm", None)),
        )
        super().__init__()
        self._levels: dict[float | int, _ContourLevel] = {}
        grid = np.stack((xs, ys), axis=-1).reshape(-1, 2)
        for k, level in enumerate(edges[:-1] if filled else edges):
            options = style.copy()
            middle = (level + edges[k + 1]) / 2 if filled else level
            if colorscale is not None:
                options.setdefault(
                    "color", ManimColor.from_rgb(self.color_mapping(middle))
                )
            if filled:
                paths = filled_marching_squares(
                    xs, ys, zs, float(level), float(edges[k + 1])
                )
                options.setdefault("fill_opacity", 1.0)
                options.setdefault("stroke_width", 0.0)
            else:
                region = Payload(
                    "region",
                    grid,
                    np.array([[0, len(grid)]], dtype=np.intp),
                    zs.shape,
                    np.isfinite(zs).ravel(),
                    (zs - level).ravel(),
                )
                lines = marching_squares(region, system.bounds)
                paths = [lines.coords[a:b] for a, b in lines.segments]
            self._levels[k if filled else float(level)] = _ContourLevel(
                system, paths, filled, **options
            )
        self.add(*self._levels.values())

    def at(self, level: float | int) -> VMobject:
        """Return a level line or indexed filled band.

        Parameters
        ----------
        level
            Contour value for lines, or zero-based band index for fills.

        Returns
        -------
        VMobject
            Bound contour artist.
        """
        return self._levels[level]
