"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from manim import VMobject

import manim_plots as mp
from manim_plots.core import FloatArray
from manim_plots.core.shape import _restrict
from manim_plots.core.sources import ArraySource, ParametricSource
from manim_plots.mobjects.artists import LinePlot, _CurvePlot
from manim_plots.mobjects.leaves import Leaf

from ._base import MappedPresentation, flags
from ._spatial import _halfspace, _Spatial
from .curves import _index_spans


class GrowSurface(MappedPresentation):
    """Raise a bound surface from a coordinate plane.

    Parameters
    ----------
    surface, zdir, offset, **kwargs
        Surface, growth coordinate, starting plane and animation options.
    """

    def __init__(
        self,
        surface: mp.SurfacePlot,
        zdir: str = "z",
        offset: float | None = None,
        *,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if zdir not in ("x", "y", "z"):
            raise ValueError("zdir must be x, y or z")
        self.surface = surface
        self._axis = "xyz".index(zdir)
        self._offset = (
            min(surface._system._ranges[self._axis].range.value)
            if offset is None
            else float(offset)
        )
        if not np.isfinite(self._offset):
            raise ValueError("offset must be finite")
        scale = surface._system._ranges[self._axis]._scale
        if not np.isfinite(scale.forward(np.array([self._offset]))).all():
            raise ValueError("offset is outside the scale domain")
        self.reverse = reverse
        flags(reverse, remover, kwargs)
        super().__init__(surface, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Capture final data buffers before animation takes ownership."""
        surface = self.surface
        surface._driver._ensure()
        mapping = surface._system._mapping()
        self._final = [mapping.inverse(face.points.copy()) for face in surface.faces]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Map one shared growth fraction through the coordinate system.

        Parameters
        ----------
        alpha
            Animation progress before the rate function.
        """
        self._alpha = alpha
        progress = self.rate_func(1 - alpha if self.reverse else alpha)
        for face, final in zip(self.surface.faces, self._final, strict=True):
            data = final.copy()
            data[:, self._axis] = self._offset + progress * (
                data[:, self._axis] - self._offset
            )
            face.set_points(self.surface._system._mapping().to_screen(data))

    def finish(self) -> None:
        """Restore the bound surface with its final colours and no new updater."""
        super().finish()
        self.surface._building = False
        self.surface._driver._dirty = True
        self.surface._driver._ensure()


class ShrinkSurface(GrowSurface):
    """Lower a surface to its origin and remove it by default.

    Parameters
    ----------
    surface, zdir, offset, remover, **kwargs
        Bound surface, coordinate, origin, removal override and native options.
    """

    def __init__(
        self,
        surface: mp.SurfacePlot,
        zdir: str = "z",
        offset: float | None = None,
        *,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(surface, zdir, offset, reverse=True, remover=remover, **kwargs)


class GrowStems(_Spatial):
    """Grow stems and their markers from each stored baseline point.

    Parameters
    ----------
    stems, lag_ratio, reverse, remover, **kwargs
        Bound stems, stagger, playback flags and native options.
    """

    def __init__(
        self,
        stems: mp.StemPlot,
        *,
        lag_ratio: float = 0.05,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        self.stems = stems
        super().__init__(
            stems, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def begin(self) -> None:
        """Capture marker outlines without changing the stored stem data."""
        self._outlines = [
            [
                (leaf, leaf.points.copy() - marker.get_center())
                for leaf in marker.get_family()
            ]
            for marker in self.stems.markers
        ]
        super().begin()

    def _draw(self) -> None:
        for i, line in enumerate(
            cast(list[LinePlot], self.stems.stemlines.submobjects)
        ):
            system = line._system
            assert system is not None
            assert isinstance(line.source, ArraySource)
            data = line.source.data
            end = data[0] + self._progress(i, len(self.stems.stemlines)) * (
                data[-1] - data[0]
            )
            points = system._mapping().to_screen(np.array([data[0], end]))
            line.set_points_as_corners(points)
            for leaf, outline in self._outlines[i]:
                cast(VMobject, leaf).points = outline + system.c2p(*end)

    def restore(self) -> None:
        """Restore bound stems and marker geometry."""
        super().restore()
        for line in cast(list[LinePlot], self.stems.stemlines.submobjects):
            line.refresh()
        for marker in self.stems.markers:
            for leaf in marker.get_family():
                if isinstance(leaf, Leaf):
                    leaf.refresh()


class RevealWireframe(_Spatial):
    """Trace retained wireframe lines in the requested family order.

    Parameters
    ----------
    wireframe, families, lag_ratio, reverse, remover, **kwargs
        Bound wireframe, ordered families, stagger, playback flags and native options.
    """

    def __init__(
        self,
        wireframe: mp.WireframePlot,
        *,
        families: tuple[str, ...] = ("u", "v"),
        lag_ratio: float = 0.05,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if any(f not in ("u", "v") for f in families):
            raise ValueError("unknown wireframe family")
        self.wireframe, self.families = wireframe, families
        super().__init__(
            wireframe, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def begin(self) -> None:
        """Retain complete curves and their source-parameter intervals."""
        groups = {"u": self.wireframe.u_lines, "v": self.wireframe.v_lines}
        self._lines = cast(
            list[_CurvePlot], [line for name in self.families for line in groups[name]]
        )
        self._curves: dict[_CurvePlot, tuple[FloatArray, FloatArray]] = {}
        for line in cast(
            list[_CurvePlot], [*self.wireframe.u_lines, *self.wireframe.v_lines]
        ):
            assert line._system is not None
            data = line._system.p2c(line.points.copy())
            samples = cast(ParametricSource, line.source).at(np.linspace(0, 1, 2049))
            spans = _index_spans(data.reshape(-1, 4, 3), ArraySource(samples, dim=3))
            self._curves[line] = (data, spans)
        super().begin()

    def _draw(self) -> None:
        for line in self._curves:
            line.points = np.empty((0, 3))
        for i, line in enumerate(self._lines):
            assert line._system is not None
            data, spans = self._curves[line]
            curves = data.reshape(-1, 4, 3)
            p = self._progress(i, len(self._lines))
            count = int(np.searchsorted(spans[:, 1], p, side="right"))
            pieces = [curves[:count].reshape(-1, 3)]
            if count < len(curves) and spans[count, 0] < p:
                lo, hi = spans[count]
                pieces.append(
                    _restrict(
                        curves[count : count + 1],
                        np.array([0.0]),
                        np.array([(p - lo) / (hi - lo)]),
                    ).reshape(-1, 3)
                )
            line.points = line._system._mapping().to_screen(np.concatenate(pieces))

    def restore(self) -> None:
        """Restore both canonical line families."""
        super().restore()
        for line in self._curves:
            line.refresh()


class RevealWaterfall(_Spatial):
    """Trace waterfall planes and close their fills at the same front.

    Parameters
    ----------
    waterfall, lag_ratio, reverse, remover, **kwargs
        Bound waterfall, stagger, playback flags and native options.
    """

    def __init__(
        self,
        waterfall: mp.WaterfallPlot,
        *,
        lag_ratio: float = 0.15,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        self.waterfall = waterfall
        super().__init__(
            waterfall, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def _draw(self) -> None:
        from manim_plots.mobjects.plots3d import _WaterfallFill

        for i, line in enumerate(self.waterfall.lines):
            assert line._system is not None
            assert isinstance(line.source, ArraySource)
            p = self._progress(i, len(self.waterfall.lines))
            full = line.source.data
            amount = p * max(0, len(full) - 1)
            count = int(amount)
            data = full[: count + 1].copy()
            if count < len(full) - 1:
                data = np.vstack(
                    (
                        data,
                        full[count]
                        + (amount - count) * (full[count + 1] - full[count]),
                    )
                )
            if p <= 0:
                data = data[:0]
            line.set_points_as_corners(line._system._mapping().to_screen(data))
            fill = cast(_WaterfallFill | None, self.waterfall.fills[i])
            if fill is not None:
                floor = data[::-1].copy()
                floor[:, fill._floor_axis] = min(
                    line._system._ranges[fill._floor_axis].range.value
                )
                polygon = np.vstack((data, floor, data[:1]))
                fill.set_points_as_corners(line._system._mapping().to_screen(polygon))

    def restore(self) -> None:
        """Restore full curves and their viewport-floor fills."""
        super().restore()
        for part in [*self.waterfall.lines, *self.waterfall.fills]:
            if part is not None:
                part.refresh()


class SweepSurface(_Spatial):
    """Clip retained surface cells at a moving parameter or data front.

    Parameters
    ----------
    surface, axis, direction, reverse, remover, **kwargs
        Bound surface, parameter (u/v) or triangle coordinate (x/y/z),
        direction, playback flags and native animation options.
    """

    def __init__(
        self,
        surface: mp.SurfacePlot,
        *,
        axis: str = "u",
        direction: int = 1,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        allowed = ("x", "y", "z") if surface._kind == "triangles" else ("u", "v")
        if axis not in allowed:
            raise ValueError("unsupported surface axis")
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        self.surface, self.axis, self.direction = surface, axis, direction
        super().__init__(
            surface, reverse=reverse, remover=remover, **cast(dict[str, Any], kwargs)
        )

    def _draw(self) -> None:
        from manim_plots.mobjects.artists import _clip_axes, _clip_box

        surface = self.surface
        surface._building = False
        surface._driver._ensure()
        surface._building = True
        p = self._progress()
        data = surface._corner_data
        system = surface._system
        bounds = _clip_box(system, surface._clip)
        enabled = _clip_axes(surface._clip, 3)
        triangle = surface._kind == "triangles"
        dim = "xyz".index(self.axis) if triangle else "uv".index(self.axis)
        if triangle:
            vertices = data[..., dim]
            finite = vertices[np.isfinite(vertices)]
            lo, hi = (
                (float(finite.min()), float(finite.max()))
                if len(finite)
                else (0.0, 0.0)
            )
            front = lo + p * (hi - lo) if self.direction == 1 else hi - p * (hi - lo)
        else:
            count = surface._resolution[dim]
            front = p * count if self.direction == 1 else (1 - p) * count
        for k, face in enumerate(surface.faces):
            polygon = data[k].copy()
            if not np.isfinite(polygon).all() or p <= 0:
                face.points = np.empty((0, 3))
                continue
            if triangle:
                polygon = _halfspace(polygon, dim, front, -self.direction)
            else:
                i, j = divmod(k, surface._resolution[1])
                parameters = np.array(
                    [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]], float
                )
                polygon = _halfspace(
                    np.column_stack((polygon, parameters)),
                    3 + dim,
                    front,
                    -self.direction,
                )[:, :3]
            local = system._data.forward(polygon)
            if not np.isfinite(local).all():
                local = np.empty((0, 3))
            for axis, active in enumerate(enabled):
                if active is not False:
                    local = _halfspace(local, axis, bounds.lower[axis], 1)
                    local = _halfspace(local, axis, bounds.upper[axis], -1)
            points = system.frame.mapping.forward(local)
            face.set_points_as_corners(np.vstack((points, points[:1])))

    def restore(self) -> None:
        """Restore the full bound domain and current canonical colours."""
        super().restore()
        self.surface._building = False
        self.surface._driver._dirty = True
        self.surface._driver._ensure()
