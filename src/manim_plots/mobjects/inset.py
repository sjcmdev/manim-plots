"""Inset coordinate systems bound to a parent's viewport box."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

import numpy as np
from manim import Line, Mobject, VGroup

from manim_plots.core import FloatArray
from manim_plots.core.sources import ArraySource, FunctionSource, ParametricSource
from manim_plots.mobjects.artists import (
    FunctionPlot,
    LinePlot,
    ParametricPlot,
    ScatterPlot,
    _MarkerLeaf,
)
from manim_plots.mobjects.helpers import _LiveLine, _LiveShape, _NativeBinding
from manim_plots.mobjects.system import Axes, CartesianAxes


class InsetAxes(Axes):
    """Place independent axes in fractions of a parent's data box.

    Parameters
    ----------
    parent, bounds, x_range, y_range
        Parent axes, lower-left fractions and size, and inset data ranges.
    connectors, mirror, **axes_kwargs
        Draw corner connectors, re-plot supported artists and configure axes.

    Attributes
    ----------
    zoom_box, connectors, mirrored
        Parent data rectangle, connector lines and retained mirrored artists.
    """

    def __init__(
        self,
        parent: CartesianAxes,
        bounds: Sequence[float],
        x_range: Sequence[float],
        y_range: Sequence[float],
        *,
        connectors: bool = True,
        mirror: Iterable[Mobject] = (),
        **axes_kwargs: object,
    ) -> None:
        fractions = np.asarray(bounds, dtype=float)
        if (
            fractions.shape != (4,)
            or not np.isfinite(fractions).all()
            or np.any(fractions[2:] <= 0)
        ):
            raise ValueError(
                "bounds must contain finite x0, y0 and positive width, height"
            )
        self._inset_bounds = fractions
        self._following = True
        lo, hi = (
            parent.c2p(parent.x_range[0], parent.y_range[0]),
            parent.c2p(parent.x_range[1], parent.y_range[1]),
        )
        axes_kwargs.setdefault("tips", False)
        axes_kwargs.setdefault("axis_config", {"include_numbers": False})
        axes_kwargs["x_length"] = float(np.linalg.norm((hi - lo)[:1]) * fractions[2])
        axes_kwargs["y_length"] = float(abs(hi[1] - lo[1]) * fractions[3])
        super().__init__(
            x_range=x_range, y_range=y_range, **cast(dict[str, Any], axes_kwargs)
        )
        self.x.set_position("bottom")
        self.y.set_position("left")
        self.parent = parent
        self.zoom_box = _LiveShape(
            color=parent.x_axis.get_color(), fill_opacity=0, stroke_width=2
        )
        self.connectors = (
            VGroup(
                *(
                    _LiveLine(color=parent.x_axis.get_color(), stroke_width=2)
                    for _ in range(2)
                )
            )
            if connectors
            else VGroup()
        )
        self.submobjects.extend([self.zoom_box, self.connectors])
        self._following = False
        self._follow_parent()
        self._inset_driver = _NativeBinding(self.zoom_box, self._follow_parent)
        for line in self.connectors:
            line.__dict__["_helper_driver"] = self._inset_driver
        self.add_updater(lambda _: self._follow_parent())
        self.mirrored = [self._mirror(artist) for artist in mirror]

    def _data_dirty(self) -> bool:
        if not self.__dict__.get("_following", True):
            self._follow_parent()
        return super()._data_dirty()

    def _sync_data(self) -> None:
        super()._sync_data()
        if not self.__dict__.get("_following", True):
            self._follow_parent()

    def _follow_parent(self) -> None:
        if self._following:
            return
        self._following = True
        try:
            parent = self.parent
            assert parent is not None
            parent._sync_data()
            lo = parent.c2p(parent.x_range[0], parent.y_range[0])
            hi = parent.c2p(parent.x_range[1], parent.y_range[1])
            x0, y0, w, h = self._inset_bounds
            target = lo + np.array([x0, y0, 0]) * (hi - lo)
            frame_version = self.frame.version
            bottom = self.c2p(self.x_range[0], self.y_range[0])
            top = self.c2p(self.x_range[1], self.y_range[1])
            size = top - bottom
            desired = np.array([w, h, 0]) * (hi - lo)
            progress = self.__dict__.get("_inset_expansion", 1.0)
            if progress != 1:
                origin = parent.c2p(self.x_range[0], self.y_range[0])
                extent = parent.c2p(self.x_range[1], self.y_range[1]) - origin
                target = (1 - progress) * origin + progress * target
                desired = (1 - progress) * extent + progress * desired
            factors = np.divide(
                desired[:2], size[:2], out=np.ones(2), where=size[:2] != 0
            )
            if not np.allclose(factors, 1, rtol=1e-12, atol=1e-12):
                self.frame.stretch(float(factors[0]), 0, about_point=bottom)
                self.frame.stretch(float(factors[1]), 1, about_point=bottom)
            bottom = self.c2p(self.x_range[0], self.y_range[0])
            if not np.allclose(bottom, target, rtol=0, atol=1e-12):
                self.frame.shift(target - bottom)
            if self.frame.version != frame_version:
                for axis in self._owned_axes():
                    axis._configure(only_crossing=True)
                self._configure_grid()
            coords = [
                (self.x_range[i], self.y_range[j])
                for i, j in ((0, 0), (1, 0), (1, 1), (0, 1))
            ]
            box = np.array([parent.c2p(x, y) for x, y in coords])
            inner = np.array([self.c2p(x, y) for x, y in coords])
            self.zoom_box.set_points_as_corners(np.vstack((box, box[:1])))
            candidates = [
                i
                for i in range(4)
                if not any(
                    _crosses_interior(box[i], inner[i], rect) for rect in (box, inner)
                )
            ]
            for line, i in zip(self.connectors, candidates[:2], strict=False):
                cast(Line, line).set_points_as_corners([box[i], inner[i]])
        finally:
            self._following = False

    def _mirror(self, artist: Mobject) -> Mobject:
        result: Mobject
        if isinstance(artist, FunctionPlot) and isinstance(
            artist.source, FunctionSource
        ):
            source = artist.source
            result = self.plot(
                source.function,
                x_range=source._range,
                use_vectorized=source.use_vectorized,
                discontinuities=source.discontinuities,
                dt=source.dt,
                use_smoothing=artist.use_smoothing,
                line_style=artist.line_style,
                dash=artist.dash,
                clip=artist._clip,
            )
        elif isinstance(artist, ParametricPlot) and isinstance(
            artist.source, ParametricSource
        ):
            source_p = artist.source
            result = self.plot_parametric_curve(
                source_p.function,
                t_range=cast(Sequence[float], source_p._range),
                use_vectorized=source_p.use_vectorized,
                discontinuities=source_p.discontinuities,
                dt=source_p.dt,
                use_smoothing=artist.use_smoothing,
                line_style=artist.line_style,
                dash=artist.dash,
                clip=artist._clip,
            )
        elif isinstance(artist, (LinePlot, ScatterPlot)) and isinstance(
            artist.source, ArraySource
        ):
            data = artist.source.data
            result = (
                self.scatter(
                    data[:, 0],
                    data[:, 1],
                    marker=artist._marker_template,
                    clip=artist._clip,
                )
                if isinstance(artist, ScatterPlot)
                else self.line(
                    data[:, 0],
                    data[:, 1],
                    line_style=artist.line_style,
                    dash=artist.dash,
                    clip=artist._clip,
                )
            )
        else:
            raise TypeError(f"cannot mirror {type(artist).__name__}")
        result.match_style(artist)
        if isinstance(artist, ScatterPlot):
            for old, new in zip(artist.get_family(), result.get_family(), strict=True):
                if isinstance(old, _MarkerLeaf) and isinstance(new, _MarkerLeaf):
                    new._outline = old._outline.copy()
                    new.match_style(old)
                    new._dirty = True
        return result


def _crosses_interior(a: FloatArray, b: FloatArray, rectangle: FloatArray) -> bool:
    lower, upper = rectangle[:, :2].min(axis=0), rectangle[:, :2].max(axis=0)
    enter, leave = 0.0, 1.0
    for i in range(2):
        delta = b[i] - a[i]
        if abs(delta) < 1e-12:
            if not lower[i] < a[i] < upper[i]:
                return False
        else:
            ends = sorted(((lower[i] - a[i]) / delta, (upper[i] - a[i]) / delta))
            enter, leave = max(enter, ends[0]), min(leave, ends[1])
    return bool(enter + 1e-10 < leave)
