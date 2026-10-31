"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import numpy as np
from manim import (
    Animation,
    VMobject,
)
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.payload import Payload
from manim_plots.core.shape import _restrict, resample_pair
from manim_plots.core.sources import ArraySource, FunctionSource, ParametricSource
from manim_plots.mobjects.artists import LinePlot, ScatterPlot, _CurvePlot, _MarkerLeaf

from ._base import MappedPresentation, flags, window


class AppendData(Animation):
    """Append points sequentially, optionally widening the owning axes.

    Parameters
    ----------
    artist, x, y
        Bound line or scatter and new coordinate pairs or separate arrays.
    autoscale, **kwargs
        Follow the drawn data with margins and native animation options.
    """

    def __init__(
        self,
        artist: LinePlot | ScatterPlot,
        x: ArrayLike,
        y: ArrayLike | None = None,
        *,
        autoscale: bool = False,
        **kwargs: object,
    ) -> None:
        if not isinstance(artist, (LinePlot, ScatterPlot)):
            raise TypeError("artist must be a LinePlot or ScatterPlot")
        if artist._system is None:
            raise ValueError("artist must be bound to axes")
        self.artist, self.autoscale = artist, autoscale
        self._involved_system = artist._system if autoscale else None
        self._new = ArraySource(x, y, dim=len(artist._system._ranges)).data
        if not np.isfinite(self._new).all():
            raise ValueError("appended coordinates must be finite")
        super().__init__(artist, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Snapshot the current source and prepare stable new scatter markers."""
        if self.artist.__dict__.get("_data_writer") is not None:
            raise ValueError("concurrent data writer already owns this artist")
        self.artist.__dict__["_data_writer"] = self
        assert isinstance(self.artist.source, ArraySource)
        self._old = self.artist.source.data.copy()
        self._full_data = np.concatenate((self._old, self._new))
        if isinstance(self.artist, ScatterPlot):
            assert self.artist._system is not None
            extra = ScatterPlot(
                self._full_data,
                self.artist._system,
                marker=self.artist._marker_template,
                clip=False,
            )
            self._markers = (
                self.artist.submobjects + extra.submobjects[len(self._old) :]
            )
            self._marker_styles = {
                leaf: (
                    float(leaf.get_fill_opacity()),
                    float(leaf.get_stroke_opacity()),
                    float(leaf.get_stroke_opacity(background=True)),
                )
                for marker in self._markers[len(self._old) :]
                for leaf in marker.get_family()
                if isinstance(leaf, _MarkerLeaf)
            }
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Draw a prefix and a partial segment or fading next marker.

        Parameters
        ----------
        alpha
            Native progress before the rate function.
        """
        amount = float(np.clip(self.rate_func(alpha), 0, 1)) * len(self._new)
        count, fraction = int(amount), amount % 1
        data = self._full_data[: len(self._old) + count].copy()
        scatter = isinstance(self.artist, ScatterPlot)
        if count < len(self._new) and (fraction > 0 or scatter):
            point = self._new[count]
            if not scatter and len(data):
                point = (1 - fraction) * data[-1] + fraction * point
            data = np.vstack((data, point))
        self.artist.source = ArraySource(
            data, kind="points" if scatter else "path", dim=data.shape[1]
        )
        system = self.artist._system
        assert system is not None
        if self.autoscale:
            previous = (system.x_range.copy(), system.y_range.copy())
            system.autoscale()
            for before, current, setter in zip(
                previous,
                (system.x_range, system.y_range),
                (system.set_x_range, system.set_y_range),
                strict=True,
            ):
                setter((min(before[0], current[0]), max(before[1], current[1])))
        if isinstance(self.artist, ScatterPlot):
            self.artist.submobjects = self._markers[: len(data)]
            for marker in self.artist.submobjects:
                for leaf in marker.get_family():
                    if isinstance(leaf, _MarkerLeaf):
                        leaf.source = self.artist.source
                        leaf._clip = self.artist._clip
                        leaf._dirty = True
                        leaf._rebuild()
                        if leaf in self._marker_styles:
                            factor = (
                                fraction
                                if leaf._index == len(self._old) + count
                                else 1.0
                            )
                            fill, stroke, background = self._marker_styles[leaf]
                            leaf.set_fill(opacity=fill * factor)
                            leaf.set_stroke(opacity=stroke * factor)
                            leaf.set_stroke(
                                opacity=background * factor, background=True
                            )
        else:
            self.artist._rebuild()

    def finish(self) -> None:
        """Retain the appended source as canonical bound data."""
        super().finish()
        self.artist.__dict__.pop("_data_writer", None)
        if isinstance(self.artist, LinePlot):
            self.artist.refresh()
        else:
            for marker in self.artist.submobjects:
                for leaf in marker.get_family():
                    if isinstance(leaf, _MarkerLeaf):
                        leaf.refresh()


def _path(artist: _CurvePlot) -> Payload:
    artist._ensure()
    return Payload("path", artist.points.copy(), artist._render_segments)


class TraceCurve(MappedPresentation):
    """Reveal a curve in source order, pacing function graphs by data x.

    Parameters
    ----------
    artist
        Function, array line or parametric artist to reveal.
    **kwargs
        Native Animation options, including rate_func.
    """

    def __init__(
        self,
        artist: _CurvePlot,
        *,
        pacing: str = "parameter",
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(artist, _CurvePlot) or isinstance(artist, _MarkerLeaf):
            raise TypeError("artist must be a line-like artist")
        if pacing not in {"parameter", "arc_length"}:
            raise ValueError("unknown pacing")
        self.pacing, self.reverse = pacing, reverse
        self.artist = artist
        assert artist._system is not None
        flags(reverse, remover, kwargs)
        super().__init__(artist, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Snapshot the source-order geometry before opening animation ownership."""
        canonical = self.artist.copy()
        canonical._reversed = False
        canonical._restore()
        self._full = canonical.points.copy()
        self._data_curves: FloatArray | None = None
        self._index_spans: FloatArray | None = None
        source = self.artist.source
        if (
            isinstance(source, (FunctionSource, ArraySource))
            and self.artist._system is not None
        ):
            system = self.artist._system
            local = canonical._frame().inverse(self._full)
            local = canonical._own.inverse(local)
            data = system._data.inverse(local[:, :2]).reshape(-1, 4, 2)
            if isinstance(source, FunctionSource):
                self._data_curves = data
                self._range = source._range or tuple(sorted(system.x_range))
            elif len(source.data) > 1:
                self._index_spans = _index_spans(data, source)
        if isinstance(source, ParametricSource) and self.artist._system is not None:
            assert source._range is not None
            # shortcut: project t from 2049 probes; retain sampled t for tighter pacing.
            samples = source.at(np.linspace(source._range[0], source._range[1], 2049))
            data = self.artist._system.p2c(self._full)[:, : source.dim].reshape(
                -1, 4, source.dim
            )
            self._index_spans = _index_spans(data, ArraySource(samples, dim=source.dim))
        self._full_data = None
        if self.artist._system is not None:
            self._full_data = self.artist._system.p2c(self._full)[
                :, : len(self.artist._system._ranges)
            ]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Write a prefix ending at the current source parameter.

        Parameters
        ----------
        alpha
            Native animation progress before rate_func.
        """
        self._alpha = alpha
        progress = float(
            np.clip(self.rate_func(1 - alpha if self.reverse else alpha), 0, 1)
        )
        if self._full_data is not None:
            assert self.artist._system is not None
            self._full = self.artist._system._mapping().to_screen(self._full_data)
        if progress >= 1:
            self.artist.points = (
                self._full[::-1] if self.artist._reversed else self._full
            ).copy()
            return
        if progress <= 0 or not len(self._full):
            self.artist.points = np.empty((0, 3))
            return
        curves = self._full.reshape(-1, 4, 3)
        data = self._data_curves
        if self.pacing == "arc_length":
            lengths = np.linalg.norm(np.diff(curves, axis=1), axis=2).sum(axis=1)
            edges = np.concatenate(([0.0], np.cumsum(lengths)))
            amount = progress * edges[-1]
            count = min(
                int(np.searchsorted(edges[1:], amount, side="right")), len(curves)
            )
            fraction = (
                float((amount - edges[count]) / lengths[count])
                if count < len(curves) and lengths[count] > 0
                else 0.0
            )
        elif self._index_spans is not None:
            spans = self._index_spans
            count = int(np.searchsorted(spans[:, 1], progress, side="right"))
            fraction = 0.0
            if count < len(curves) and spans[count, 0] <= progress:
                start, stop = spans[count]
                if stop > start:
                    fraction = float(np.clip((progress - start) / (stop - start), 0, 1))
        elif data is None:
            amount = progress * len(curves)
            count, fraction = int(amount), amount % 1
        else:
            x = self._range[0] + progress * (self._range[1] - self._range[0])
            count = int(np.searchsorted(data[:, 3, 0], x, side="right"))
            fraction = 0.0
            if count < len(curves) and x >= data[count, 0, 0]:
                p = data[count, :, 0]
                lo, hi = 0.0, 1.0
                for _ in range(40):
                    t = (lo + hi) / 2
                    value = (
                        (1 - t) ** 3 * p[0]
                        + 3 * (1 - t) ** 2 * t * p[1]
                        + 3 * (1 - t) * t * t * p[2]
                        + t**3 * p[3]
                    )
                    if value < x:
                        lo = t
                    else:
                        hi = t
                fraction = (lo + hi) / 2
        parts = [curves[:count].reshape(-1, 3)]
        if fraction > 0 and count < len(curves):
            parts.append(
                _restrict(
                    curves[count : count + 1], np.array([0.0]), np.array([fraction])
                ).reshape(-1, 3)
            )
        self.artist.points = np.concatenate(parts)

    def restore(self) -> None:
        """Restore the artist's data attachment."""
        super().restore()
        self.artist.refresh()


def _index_spans(curves: FloatArray, source: ArraySource) -> FloatArray:
    starts, deltas = source.data[:-1], np.diff(source.data, axis=0)
    sizes = np.sum(deltas * deltas, axis=1)
    valid = (
        np.isfinite(starts).all(axis=1) & np.isfinite(deltas).all(axis=1) & (sizes > 0)
    )
    result = np.empty((len(curves), 2))
    if not valid.any():
        edges = np.linspace(0, 1, len(curves) + 1)
        return np.column_stack((edges[:-1], edges[1:]))
    cursor = 0
    with np.errstate(all="ignore"):
        for index, curve in enumerate(curves):
            middle = (curve[0] + curve[3]) / 2
            fractions = np.clip(
                np.sum((middle - starts) * deltas, axis=1) / sizes, 0, 1
            )
            distances = np.sum(
                (starts + fractions[:, None] * deltas - middle) ** 2, axis=1
            )
            distances[~valid] = np.inf
            distances[:cursor] = np.inf
            cursor = int(np.argmin(distances))
            if not np.isfinite(distances[cursor]):
                raise ValueError("TraceCurve cannot locate the source data index")
            parameters = (
                (curve[[0, 3]] - starts[cursor]) @ deltas[cursor] / sizes[cursor]
            )
            result[index] = (cursor + parameters) / (len(source.data) - 1)
    return result


class ShowPoints(MappedPresentation):
    """Reveal scatter markers in input order, retaining hidden rows.

    Parameters
    ----------
    scatter
        Scatter whose valid markers are revealed.
    **kwargs
        Native Animation options.
    """

    def __init__(
        self,
        scatter: ScatterPlot,
        *,
        order: str | Callable[[FloatArray], Any] = "data",
        pop: bool = False,
        lag_ratio: float = 1.0,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not isinstance(scatter, ScatterPlot):
            raise TypeError("scatter must be a ScatterPlot")
        if not callable(order) and order not in {"data", "x", "y", "value"}:
            raise ValueError("unknown order")
        if order == "value" and scatter.__dict__.get("_color_mapping") is None:
            raise ValueError("value order requires numeric c")
        self.scatter = scatter
        self.order, self.pop, self.reverse = order, pop, reverse
        flags(reverse, remover, kwargs)
        super().__init__(scatter, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Save each visible marker leaf's three opacity channels."""
        self._styles: list[list[tuple[_MarkerLeaf, tuple[float, float, float]]]] = []
        for marker in self.scatter.submobjects:
            row = []
            for leaf in marker.get_family():
                if isinstance(leaf, _MarkerLeaf):
                    leaf._ensure()
                    row.append(
                        (
                            leaf,
                            (
                                float(leaf.get_fill_opacity()),
                                float(leaf.get_stroke_opacity()),
                                float(leaf.get_stroke_opacity(background=True)),
                            ),
                        )
                    )
            self._styles.append(row)
        data = self.scatter.source.data
        order = self.order
        if callable(order):
            self._order = sorted(range(len(data)), key=lambda i: order(data[i]))
        elif order == "data":
            self._order = list(range(len(data)))
        else:
            values = (
                self.scatter._color_values
                if order == "value"
                else data[:, "xy".index(order)]
            )
            assert values is not None
            self._order = list(np.argsort(values, kind="stable"))
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Fade markers sequentially without exposing invalid or clipped rows.

        Parameters
        ----------
        alpha
            Native progress before rate_func.
        """
        self._alpha = alpha
        alpha = 1 - alpha if self.reverse else alpha
        for rank, index in enumerate(self._order):
            row = self._styles[index]
            factor = self.rate_func(
                window(alpha, rank, len(self._styles), self.lag_ratio)
            )
            for leaf, (fill, stroke, background) in row:
                leaf._restore()
                if self.pop and len(leaf.points):
                    centre = leaf.get_center()
                    leaf.points = centre + factor * (leaf.points - centre)
                leaf.set_fill(opacity=factor * fill, family=False)
                leaf.set_stroke(opacity=factor * stroke, family=False)
                leaf.set_stroke(
                    opacity=factor * background, background=True, family=False
                )

    def restore(self) -> None:
        """Restore each marker's shape and independent opacity channels."""
        super().restore()
        for row in self._styles:
            for leaf, (fill, stroke, background) in row:
                leaf.refresh()
                leaf.set_fill(opacity=fill, family=False)
                leaf.set_stroke(opacity=stroke, family=False)
                leaf.set_stroke(opacity=background, background=True, family=False)


class Morph(Animation):
    """Interpolate compatible paths on their shared arc-length lattice.

    Parameters
    ----------
    a, b
        Line-like artists with matching nondegenerate path pieces. At the end a
        adopts b's source and system; b is unchanged.
    **kwargs
        Native Animation options.
    """

    def __init__(self, a: _CurvePlot, b: _CurvePlot, **kwargs: object) -> None:
        if (
            not isinstance(a, _CurvePlot)
            or not isinstance(b, _CurvePlot)
            or isinstance(a, _MarkerLeaf)
            or isinstance(b, _MarkerLeaf)
        ):
            raise ValueError(
                "Morph requires two line-like artists with matching pieces"
            )
        self.a, self.b = a, b
        self._prepare()
        super().__init__(a, **cast(dict[str, Any], kwargs))

    def _prepare(self) -> None:
        source, target = resample_pair(_path(self.a), _path(self.b))
        self._from, self._to = source.coords, target.coords

    def begin(self) -> None:
        """Resample once for the play, without native duplicate-point alignment."""
        self._prepare()
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Interpolate corresponding cubic points at a fixed shared point count.

        Parameters
        ----------
        alpha
            Native progress before rate_func.
        """
        progress = float(np.clip(self.rate_func(alpha), 0, 1))
        self.a.points = (1 - progress) * self._from + progress * self._to
        self.a.interpolate_color(
            cast(VMobject, self.starting_mobject), self.b, progress
        )

    def finish(self) -> None:
        """Adopt the target's source, ownership and placement after interpolation."""
        super().finish()
        target = self.b.copy()
        old, new = self.a._system, self.b._system
        if old is not new:
            if old is not None and self.a in old._artists:
                old._artists.remove(self.a)
            self.a._system = new
            if new is not None and self.a not in new._artists:
                new._artists.append(self.a)
        self.a.source = target.source
        self.a.parameters = target.parameters
        self.a._source_invalid = target._source_invalid
        self.a.use_smoothing = self.b.use_smoothing
        self.a._reversed = self.b._reversed
        self.a._clip = self.b._clip
        self.a._clip_has_margin = self.b._clip_has_margin
        self.a.line_style, self.a.dash, self.a._dash = (
            self.b.line_style,
            self.b.dash,
            self.b._dash,
        )
        self.a._own = target._own
        self.a._frozen_frame = None
        self.a._data_seen = -1
        self.a._parameter_token = -1
        self.a._frame_seen = -1
        self.a.match_style(cast(VMobject, self.b))
        self.a.refresh()
