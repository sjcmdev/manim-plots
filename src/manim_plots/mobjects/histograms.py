"""Histograms and cumulative filled series built from bound artists."""

from __future__ import annotations

from builtins import range as builtins_range
from collections.abc import Sequence
from typing import Any, Self, cast

import numpy as np
from manim import VGroup
from numpy.typing import NDArray

import manim_plots as mp
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.artists import LinePlot, _cycle_style
from manim_plots.mobjects.bars import BarPlot
from manim_plots.mobjects.helpers import FilledRegion
from manim_plots.mobjects.leaves import _VMStyle


def _datasets(x: object) -> list[NDArray[np.float64]]:
    if isinstance(x, np.ndarray) and x.ndim == 2:
        return [np.asarray(column, dtype=float) for column in x.T]
    rows = cast(Sequence[object], x)
    if len(rows) and np.asarray(rows[0]).ndim:
        return [np.asarray(row, dtype=float) for row in rows]
    return [np.asarray(x, dtype=float)]


def _step_vertices(x: object, y: object, where: str) -> NDArray[np.float64]:
    if where not in ("pre", "post", "mid"):
        raise ValueError("where must be pre, post or mid")
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if xs.ndim != 1 or ys.shape != xs.shape or not len(xs):
        raise ValueError("x and y must be matching nonempty one-dimensional arrays")
    if where == "mid":
        mid = (xs[:-1] + xs[1:]) / 2
        return np.column_stack(
            (np.r_[xs[0], np.repeat(mid, 2), xs[-1]], np.repeat(ys, 2))
        )
    if where == "pre":
        return np.column_stack((np.repeat(xs, 2)[:-1], np.repeat(ys, 2)[1:]))
    return np.column_stack((np.repeat(xs, 2)[1:], np.repeat(ys, 2)[:-1]))


def _stairs_vertices(
    values: object, edges: object, baseline: object, orientation: str, fill: bool
) -> NDArray[np.float64]:
    v = np.asarray(values, dtype=float)
    e = (
        np.arange(len(v) + 1, dtype=float)
        if edges is None
        else np.asarray(edges, dtype=float)
    )
    if v.ndim != 1 or not len(v) or e.shape != (len(v) + 1,):
        raise ValueError("edges must contain one more entry than values")
    if not np.isfinite(e).all() or not np.isfinite(v).all() or np.any(np.diff(e) <= 0):
        raise ValueError("values must be finite and edges must increase")
    if fill and baseline is None:
        raise ValueError("fill requires a baseline")
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation must be vertical or horizontal")
    points = np.column_stack((np.repeat(e, 2)[1:-1], np.repeat(v, 2)))
    if baseline is not None:
        base = np.broadcast_to(np.asarray(baseline, dtype=float), v.shape)
        if not np.isfinite(base).all():
            raise ValueError("baseline must be finite")
        points = np.vstack(([e[0], base[0]], points, [e[-1], base[-1]]))
        if fill:
            points = np.vstack(
                (points, np.column_stack((e[-2::-1], base[::-1])), points[0])
            )
    return points[:, ::-1] if orientation == "horizontal" else points


class HistPlot(VGroup):
    """Count samples with NumPy and draw bound bars or outlines.

    Parameters
    ----------
    system, x, bins
        Owning axes, samples and NumPy bin specification.
    range, density, weights, cumulative
        NumPy counting range, normalization, weights and cumulative direction.
    bottom, histtype, align, orientation, rwidth, stacked
        Baseline, representation, alignment, direction, relative width and stacking.
    color, color_by, colorscale, vmin, vmax, norm, label, **style
        Dataset colours, value mapping, legend labels and native artist styles.
    """

    def __init__(
        self,
        system: mp.CartesianAxes,
        x: object,
        bins: object = 10,
        *,
        range: object = None,
        density: bool = False,
        weights: object = None,
        cumulative: bool | int = False,
        bottom: object = None,
        histtype: str = "bar",
        align: str = "mid",
        orientation: str = "vertical",
        rwidth: float | None = None,
        stacked: bool = False,
        color: object = None,
        color_by: str | None = None,
        colorscale: object = None,
        vmin: float | None = None,
        vmax: float | None = None,
        norm: object = None,
        label: object = None,
        **style: object,
    ) -> None:
        if histtype not in ("bar", "barstacked", "step", "stepfilled"):
            raise ValueError("histtype must be bar, barstacked, step or stepfilled")
        if align not in ("left", "mid", "right"):
            raise ValueError("align must be left, mid or right")
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("orientation must be vertical or horizontal")
        if rwidth is not None and (not np.isfinite(rwidth) or rwidth < 0):
            raise ValueError("rwidth must be finite and nonnegative")
        if color_by not in (None, "count", "x") or (
            color_by is not None and histtype in ("step", "stepfilled")
        ):
            raise ValueError("color_by requires bars and must be count or x")
        self._system = system
        self._range, self._density, self._cumulative = range, density, cumulative
        self._bottom = 0 if bottom is None else bottom
        self._histtype, self._align, self._orientation = histtype, align, orientation
        self._rwidth, self._stacked = rwidth, stacked or histtype == "barstacked"
        self._color_by = color_by
        self._mapping_options = dict(
            colorscale=colorscale, vmin=vmin, vmax=vmax, norm=norm
        )
        self._styles: list[dict[str, Any]] = []
        self.bars: BarPlot | list[BarPlot] | None = None
        self.outlines: list[LinePlot | FilledRegion] = []
        self._count(x, bins, weights)
        if isinstance(label, (list, tuple)) and len(label) != len(self._counts):
            raise ValueError("label must contain one entry per dataset")
        for k in builtins_range(len(self._counts)):
            own = dict(style)
            if color is not None:
                own["color"] = (
                    cast(Sequence[object], color)[k]
                    if isinstance(color, (list, tuple)) and len(self._counts) > 1
                    else color
                )
            _cycle_style(system, cast(_VMStyle, own))
            own["label"] = label[k] if isinstance(label, (list, tuple)) else label
            self._styles.append(own)
        super().__init__()
        self._draw()

    def _count(self, x: object, bins: object, weights: object) -> None:
        datasets = _datasets(x)
        edges = np.histogram_bin_edges(
            np.concatenate(datasets), bins=cast(Any, bins), range=cast(Any, self._range)
        )
        ws = [None] * len(datasets) if weights is None else _datasets(weights)
        if len(ws) != len(datasets):
            raise ValueError("weights must match the datasets")
        counts = []
        for data, weight in zip(datasets, ws, strict=True):
            c = np.histogram(
                data, bins=edges, weights=weight, density=cast(Any, self._density)
            )[0].astype(float)
            if self._cumulative:
                if self._density:
                    c *= np.diff(edges)
                c = np.cumsum(c[::-1])[::-1] if self._cumulative == -1 else np.cumsum(c)
            counts.append(c)
        self.edges = edges
        self._counts = np.asarray(counts)
        self.counts = self._counts[0] if len(counts) == 1 else self._counts

    def _draw(self) -> None:
        previous = (
            []
            if self.bars is None
            else self.bars
            if isinstance(self.bars, list)
            else [self.bars]
        )
        plots: list[Any] = []
        widths = np.diff(self.edges)
        centres = (self.edges[:-1] + self.edges[1:]) / 2
        centres += {"left": -0.5, "mid": 0, "right": 0.5}[self._align] * widths
        base = np.broadcast_to(
            np.asarray(self._bottom, dtype=float), widths.shape
        ).copy()
        n = len(self._counts)
        for k, count in enumerate(self._counts):
            own = dict(self._styles[k])
            if self._histtype in ("step", "stepfilled"):
                points = _stairs_vertices(
                    base + count,
                    self.edges,
                    base,
                    self._orientation,
                    self._histtype == "stepfilled",
                )
                if self._histtype == "stepfilled":
                    own = {"fill_opacity": 1, "stroke_width": 0, **own}
                if self.outlines:
                    self.outlines[k].source = ArraySource(points)
                    self.outlines[k].refresh()
                else:
                    plots.append(self._system.line(points, **cast(Any, own)))
            else:
                dr = (
                    self._rwidth
                    if self._rwidth is not None
                    else 0.8
                    if n > 1 and not self._stacked
                    else 1.0
                )
                width = dr * widths
                position = centres.copy()
                if n > 1 and not self._stacked:
                    position += -width / 2 * (1 - 1 / n) + k * width / n
                    width = width / n
                c = (
                    count
                    if self._color_by == "count"
                    else (self.edges[:-1] + self.edges[1:]) / 2
                    if self._color_by == "x"
                    else None
                )
                mapping = dict(self._mapping_options)
                if self._color_by == "x":
                    if mapping["vmin"] is None:
                        mapping["vmin"] = float(self.edges[0])
                    if mapping["vmax"] is None:
                        mapping["vmax"] = float(self.edges[-1])
                if k < len(previous):
                    bars = previous[k]
                    if len(bars) > len(count):
                        self._system.remove(*bars.submobjects[len(count) :])
                        bars.submobjects = bars.submobjects[: len(count)]
                    if len(bars) < len(count):
                        method = (
                            self._system.barh
                            if self._orientation == "horizontal"
                            else self._system.bar
                        )
                        extra = method(
                            position[len(bars) :],
                            count[len(bars) :],
                            width[len(bars) :],
                            base[len(bars) :],
                            **cast(Any, {**own, "label": None}),
                        )
                        bars.add(*extra.submobjects)
                    bars.set_data(
                        x=position,
                        height=count,
                        width=width,
                        bottom=base,
                        c=c,
                        **cast(Any, mapping),
                    )
                else:
                    method = (
                        self._system.barh
                        if self._orientation == "horizontal"
                        else self._system.bar
                    )
                    bars = method(
                        position,
                        count,
                        width,
                        base,
                        c=c,
                        **cast(Any, mapping),
                        **cast(Any, own),
                    )
                    self.add(bars)
                plots.append(bars)
            if self._stacked:
                base = base + count
        if self._histtype in ("step", "stepfilled"):
            if plots:
                self.outlines = cast(list[LinePlot | FilledRegion], plots)
                self.add(*self.outlines)
        else:
            self.bars = plots[0] if n == 1 else plots

    @property
    def color_mapping(self) -> mp.ColorMapping | None:
        """Return the first dataset's bar colour mapping."""
        bars = self.bars[0] if isinstance(self.bars, list) else self.bars
        return None if bars is None else bars.color_mapping

    def set_data(
        self, x: object, *, bins: object = None, weights: object = None
    ) -> Self:
        """Recount samples, retaining edges unless bins are supplied.

        Parameters
        ----------
        x, bins, weights
            Replacement samples, optional new bins and sample weights.
        """
        if len(_datasets(x)) != len(self._counts):
            raise ValueError("set_data must retain the number of datasets")
        self._count(x, self.edges if bins is None else bins, weights)
        self._draw()
        return self


class StackPlot(VGroup):
    """Fill cumulative series on a zero or symmetric baseline.

    Parameters
    ----------
    system, x, ys
        Owning axes, sample coordinates and series.
    labels, colors, baseline, **style
        Legend labels, dataset colours, baseline and native fill styles.
    """

    def __init__(
        self,
        system: mp.CartesianAxes,
        x: object,
        ys: object,
        *,
        labels: Sequence[str] = (),
        colors: object = None,
        baseline: str = "zero",
        **style: object,
    ) -> None:
        values = np.asarray(ys, dtype=float)
        if baseline not in ("zero", "sym"):
            raise ValueError("baseline must be zero or sym")
        if (
            values.ndim != 2
            or not len(values)
            or values.shape[1:] != np.asarray(x).shape
            or not np.isfinite(values).all()
        ):
            raise ValueError("series must be finite and match x")
        if labels and len(labels) != len(values):
            raise ValueError("labels must match the series")
        if colors is not None and len(cast(Sequence[object], colors)) != len(values):
            raise ValueError("colors must match the series")
        base = (
            -values.sum(axis=0) / 2 if baseline == "sym" else np.zeros(values.shape[1])
        )
        self.regions = []
        for k, y in enumerate(values):
            own = {"fill_opacity": 1, **style}
            if colors is not None:
                own["color"] = cast(Sequence[object], colors)[k]
            if labels:
                own["label"] = labels[k]
            self.regions.append(
                system.fill_between(
                    np.asarray(x, dtype=float), base + y, base, **cast(Any, own)
                )
            )
            base = base + y
        super().__init__(*self.regions)
