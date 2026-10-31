"""Semantic entrances and restoring emphasis for statistical charts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import numpy as np
from manim import VMobject, there_and_back

from manim_plots.core import FloatArray
from manim_plots.mobjects.artists import LinePlot
from manim_plots.mobjects.helpers import FilledRegion
from manim_plots.mobjects.statistics import BoxPlot, PieChart, ViolinPlot, _Wedge

from .bars import _ChartPresentation


class _PiePresentation(_ChartPresentation):
    pie: PieChart

    def begin(self) -> None:
        self._points: dict[VMobject, FloatArray] = {}
        for part in self.mobject.get_family():
            if isinstance(part, VMobject):
                self._points[part] = part.points.copy()
        self._angles: list[tuple[float, float]] = [
            (float(cast(Any, w).start_angle), float(cast(Any, w).angle))
            for w in self.pie.wedges
        ]
        super().begin()

    def restore(self) -> None:
        super().restore()
        for part, points in self._points.items():
            part.points = points.copy()
        for wedge, (start, angle) in zip(self.pie.wedges, self._angles, strict=True):
            cast(_Wedge, wedge).start_angle, cast(_Wedge, wedge).angle = start, angle


class SweepPie(_PiePresentation):
    """Sweep the actual angular extent of a pie in wedge order.

    Parameters
    ----------
    pie
        Pie chart with canonical fractions, angles and explode offsets.
    lag_ratio, reverse, remover, **kwargs
        Wedge staggering, playback flags and native animation options.
    """

    def __init__(
        self,
        pie: PieChart,
        *,
        lag_ratio: float = 0,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        self.pie = pie
        super().__init__(
            pie, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Regenerate partial sectors while retaining canonical label placement."""
        self._alpha = alpha
        timing = 1 - alpha if self.reverse else alpha
        frontier = self.rate_func(timing) * float(self.pie.fractions.sum())
        previous = 0.0
        for i, fraction in enumerate(self.pie.fractions):
            factor = (
                self._progress(alpha, i, len(self.pie.wedges))
                if self.lag_ratio
                else (
                    float(np.clip((frontier - previous) / fraction, 0, 1))
                    if fraction
                    else 0.0
                )
            )
            wedge = cast(_Wedge, self.pie.wedges[i])
            wedge.start_angle, angle = self._angles[i]
            wedge.angle = angle * factor
            wedge.clear_points()
            wedge.generate_points()
            for group in (self.pie.texts, self.pie.autotexts):
                if group is not None:
                    self._fade(group[i], factor)
            previous += float(fraction)


class ExplodePie(_PiePresentation):
    """Temporarily displace selected wedges and labels along their bisectors.

    Parameters
    ----------
    pie, amount, indices
        Pie chart, displacement in radii and selected wedge indices (all by default).
    rate_func, **kwargs
        Emphasis easing and native animation options; cleanup always restores.
    """

    def __init__(
        self,
        pie: PieChart,
        *,
        amount: float = 0.1,
        indices: Sequence[int] | None = None,
        rate_func: Callable[[float], float] = there_and_back,
        **kwargs: object,
    ) -> None:
        selected = list(range(len(pie.wedges))) if indices is None else list(indices)
        if not np.isfinite(amount):
            raise ValueError("amount must be finite")
        if any(
            not isinstance(i, int)
            or isinstance(i, bool)
            or not 0 <= i < len(pie.wedges)
            for i in selected
        ):
            raise ValueError("wedge indices out of range")
        self.pie, self.amount, self.indices = pie, amount, selected
        kwargs.setdefault("introducer", False)
        super().__init__(
            pie,
            lag_ratio=0,
            remover=False,
            rate_func=rate_func,
            **cast(dict[str, Any], kwargs),
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply displacement from saved points, without accumulating transforms."""
        self._alpha = alpha
        for i in self.indices:
            start, angle = self._angles[i]
            middle = start + angle / 2
            offset = (
                self.pie.radius
                * self.amount
                * self.rate_func(alpha)
                * np.array([np.cos(middle), np.sin(middle), 0])
            )
            parts = [
                self.pie.wedges[i],
                *[g[i] for g in (self.pie.texts, self.pie.autotexts) if g is not None],
            ]
            for part in parts:
                for leaf in part.get_family():
                    if isinstance(leaf, VMobject):
                        leaf.points = self._points[leaf] + offset


def _reshape_region(
    part: FilledRegion, coordinate: int, origin: float, factor: float
) -> None:
    binding = part._binding
    binding.ensure()
    original = binding.boundaries[part._part]
    transformed = []
    for pair in original:
        boundaries = []
        for points in pair:
            data = binding.system._data.inverse(points)
            data[:, coordinate] = origin + factor * (data[:, coordinate] - origin)
            boundaries.append(binding.system._data.forward(data))
        transformed.append((boundaries[0], boundaries[1]))
    binding.boundaries[part._part] = transformed
    try:
        part._rebuild()
    finally:
        binding.boundaries[part._part] = original


def _reshape_line(
    part: LinePlot, coordinate: int, origin: float, factor: float
) -> None:
    from manim_plots.core.sources import ArraySource

    source = part.source
    assert isinstance(source, ArraySource)
    data = source.data.copy()
    data[:, coordinate] = origin + factor * (data[:, coordinate] - origin)
    part.source = ArraySource(data)
    try:
        part._rebuild()
    finally:
        part.source = source


class GrowBoxPlot(_ChartPresentation):
    """Expand boxes from their medians, then extend whiskers and show summaries.

    Parameters
    ----------
    plot
        Bound box plot with retained sample statistics.
    lag_ratio, box_ratio
        Dataset staggering and local fraction reserved for box expansion.
    reverse, remover, **kwargs
        Playback flags and native animation options.
    """

    def __init__(
        self,
        plot: BoxPlot,
        *,
        lag_ratio: float = 0.15,
        box_ratio: float = 0.5,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not np.isfinite(box_ratio) or not 0 < box_ratio < 1:
            raise ValueError("box_ratio must be strictly between zero and one")
        self.plot, self.box_ratio = plot, box_ratio
        super().__init__(
            plot, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Stage canonical quartiles, whiskers, caps and marker visibility."""
        self._alpha = alpha
        for i, box in enumerate(self.plot.boxes):
            p = self._progress(alpha, i, len(self.plot.boxes))
            b = float(np.clip(p / self.box_ratio, 0, 1))
            s = float(np.clip((p - self.box_ratio) / (1 - self.box_ratio), 0, 1))
            coordinate = 0 if box._binding.transpose else 1
            stats = self.plot.stats[i]
            _reshape_region(box, coordinate, stats["med"], b)
            self.plot.medians[i]._rebuild()
            self._fade(self.plot.medians[i], b)
            for j, quartile in enumerate((stats["q1"], stats["q3"])):
                whisker, cap = self.plot.whiskers[2 * i + j], self.plot.caps[2 * i + j]
                _reshape_line(whisker, coordinate, quartile, s)
                _reshape_line(cap, coordinate, quartile, s)
                self._fade(cap, s)
            for group in (self.plot.means, self.plot.fliers):
                if group:
                    for leaf in group[i].get_family():
                        if hasattr(type(leaf), "_rebuild"):
                            leaf._rebuild()
                    self._fade(group[i], s)


class UnfoldViolin(_ChartPresentation):
    """Unfold cached densities about their centre lines, then reveal summaries.

    Parameters
    ----------
    plot
        Bound violin plot with already sampled density bodies.
    lag_ratio, body_ratio
        Dataset staggering and local fraction reserved for unfolding.
    reverse, remover, **kwargs
        Playback flags and native animation options.
    """

    def __init__(
        self,
        plot: ViolinPlot,
        *,
        lag_ratio: float = 0.15,
        body_ratio: float = 0.5,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not np.isfinite(body_ratio) or not 0 < body_ratio < 1:
            raise ValueError("body_ratio must be strictly between zero and one")
        self.plot, self.body_ratio = plot, body_ratio
        super().__init__(
            plot, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def interpolate_mobject(self, alpha: float) -> None:
        """Scale body widths without reevaluating KDE or moving summaries."""
        self._alpha = alpha
        for i, body in enumerate(self.plot.bodies):
            p = self._progress(alpha, i, len(self.plot.bodies))
            b = float(np.clip(p / self.body_ratio, 0, 1))
            s = float(np.clip((p - self.body_ratio) / (1 - self.body_ratio), 0, 1))
            binding = body._binding
            binding.ensure()
            upper, lower = binding.boundaries[body._part][0]
            coordinate = 0 if binding.transpose else 1
            center = float(
                (
                    binding.system._data.inverse(upper)[0, coordinate]
                    + binding.system._data.inverse(lower)[0, coordinate]
                )
                / 2
            )
            _reshape_region(body, coordinate, center, b)
            for group in (
                self.plot.cbars,
                self.plot.cmins,
                self.plot.cmaxes,
                self.plot.cmeans,
                self.plot.cmedians,
            ):
                if group:
                    group[i]._rebuild()
                    self._fade(group[i], s)
