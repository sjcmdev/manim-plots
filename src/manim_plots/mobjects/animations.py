"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from manim import Animation, Create, VGroup, VMobject

from manim_plots.core import FloatArray
from manim_plots.core.payload import Payload
from manim_plots.core.shape import _restrict, resample_pair
from manim_plots.core.sources import ArraySource, FunctionSource
from manim_plots.mobjects.artists import ScatterPlot, _CurvePlot, _MarkerLeaf
from manim_plots.mobjects.leaves import FrameLeaf
from manim_plots.mobjects.system import CartesianAxes


def _path(artist: _CurvePlot) -> Payload:
    artist._ensure()
    return Payload("path", artist.points.copy(), artist._render_segments)


class DrawAxes(Create):
    """Create visible axis leaves with Manim's native family timing.

    Parameters
    ----------
    ax
        Coordinate system; registered artists are left untouched.
    **kwargs
        Native Create animation options.
    """

    def __init__(self, ax: CartesianAxes, **kwargs: object) -> None:
        if not isinstance(ax, CartesianAxes):
            raise TypeError("ax must be a CartesianAxes")
        visible = [
            leaf
            for leaf in ax.family_members_with_points()
            if isinstance(leaf, VMobject) and not isinstance(leaf, FrameLeaf)
        ]
        super().__init__(VGroup(*visible), **cast(dict[str, Any], kwargs))


class TraceCurve(Animation):
    """Reveal a curve in source order, pacing function graphs by data x.

    Parameters
    ----------
    artist
        Function, array line or parametric artist to reveal.
    **kwargs
        Native Animation options, including rate_func.
    """

    def __init__(self, artist: _CurvePlot, **kwargs: object) -> None:
        if not isinstance(artist, _CurvePlot) or isinstance(artist, _MarkerLeaf):
            raise TypeError("artist must be a line-like artist")
        self.artist = artist
        kwargs.setdefault("introducer", True)
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
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Write a prefix ending at the current source parameter.

        Parameters
        ----------
        alpha
            Native animation progress before rate_func.
        """
        progress = float(np.clip(self.rate_func(alpha), 0, 1))
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
        if self._index_spans is not None:
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

    def finish(self) -> None:
        """Complete the reveal and restore the artist's data attachment."""
        super().finish()
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


class ShowPoints(Animation):
    """Reveal scatter markers in input order, retaining hidden rows.

    Parameters
    ----------
    scatter
        Scatter whose valid markers are revealed.
    **kwargs
        Native Animation options.
    """

    def __init__(self, scatter: ScatterPlot, **kwargs: object) -> None:
        if not isinstance(scatter, ScatterPlot):
            raise TypeError("scatter must be a ScatterPlot")
        self.scatter = scatter
        kwargs.setdefault("introducer", True)
        super().__init__(scatter, **cast(dict[str, Any], kwargs))

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
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Fade markers sequentially without exposing invalid or clipped rows.

        Parameters
        ----------
        alpha
            Native progress before rate_func.
        """
        amount = float(np.clip(self.rate_func(alpha), 0, 1)) * len(self._styles)
        for index, row in enumerate(self._styles):
            factor = float(np.clip(amount - index, 0, 1))
            for leaf, (fill, stroke, background) in row:
                leaf.set_fill(opacity=factor * fill, family=False)
                leaf.set_stroke(opacity=factor * stroke, family=False)
                leaf.set_stroke(
                    opacity=factor * background, background=True, family=False
                )


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
