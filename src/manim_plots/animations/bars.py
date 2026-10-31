"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any, cast

import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    Indicate,
    Scene,
    Transform,
    VGroup,
    VMobject,
    there_and_back,
)

from manim_plots.core.params import Parameter
from manim_plots.core.sources import ArraySource
from manim_plots.mobjects.bars import BarPlot, _Bar
from manim_plots.mobjects.heatmaps import ContourSetPlot, HeatmapPlot, _Cell
from manim_plots.mobjects.histograms import HistPlot, _stairs_vertices

from ._base import MappedPresentation, Presentation, flags, window


class RebinHistogram(Presentation):
    """Transport histogram mass across the union of old and target bins.

    Parameters
    ----------
    hist, bins, **kwargs
        Bound histogram, NumPy bin specification and native animation options.
    """

    def __init__(self, hist: HistPlot, bins: object, **kwargs: object) -> None:
        if not isinstance(hist, HistPlot):
            raise TypeError("hist must be a HistPlot")
        self.hist, self.bins = hist, bins
        self._involved_system = hist._system if hist._color_by is not None else None
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(hist, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Validate retained samples and compute both atom mass distributions."""
        hist = self.hist
        if hist.__dict__.get("_data_writer") is not None:
            raise ValueError("concurrent histogram writers conflict")
        if any(w is not None and np.any(w < 0) for w in hist._weights):
            raise ValueError("negative weights cannot be rebinned")
        edges = np.histogram_bin_edges(
            np.concatenate(hist._samples),
            bins=cast(Any, self.bins),
            range=cast(Any, hist._range),
        )
        if not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0):
            raise ValueError("edges must be finite and strictly increasing")
        if not np.allclose(edges[[0, -1]], hist.edges[[0, -1]]):
            raise ValueError("rebinning requires common outer endpoints")
        self._old_edges = hist.edges.copy()
        self._old_counts = hist._counts.copy()
        self._target_edges = edges
        self._union = np.union1d(hist.edges, edges)
        masses = []
        for bins in (hist.edges, edges):
            counts = np.array(
                [
                    np.histogram(data, bins=bins, weights=weight)[0]
                    for data, weight in zip(hist._samples, hist._weights, strict=True)
                ],
                dtype=float,
            )
            if hist._density:
                totals = counts.sum(axis=1)
                if np.any(totals <= 0):
                    raise ValueError("density requires positive total weight")
                counts /= totals[:, None]
            indices = np.searchsorted(bins, self._union[:-1], side="right") - 1
            masses.append(
                counts[:, indices] * np.diff(self._union) / np.diff(bins)[indices]
            )
        self._masses = masses
        hist.__dict__["_data_writer"] = self
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Draw canonical endpoints or the absolute intermediate atom masses."""
        hist = self.hist
        p = self.rate_func(alpha)
        if p <= 0:
            hist.edges, hist._counts = self._old_edges, self._old_counts
        elif p >= 1:
            self._commit()
        else:
            hist.edges = self._union
            counts = (1 - p) * self._masses[0] + p * self._masses[1]
            if hist._cumulative:
                counts = (
                    np.cumsum(counts[:, ::-1], axis=1)[:, ::-1]
                    if hist._cumulative == -1
                    else np.cumsum(counts, axis=1)
                )
            elif hist._density:
                counts /= np.diff(self._union)
            hist._counts = counts
        hist.counts = hist._counts[0] if len(hist._counts) == 1 else hist._counts
        hist._draw()

    def _commit(self) -> None:
        hist = self.hist
        weights = None if all(w is None for w in hist._weights) else hist._weights
        hist._count(hist._samples, self._target_edges, weights)

    def restore(self) -> None:
        """Commit NumPy's target estimator and release the data writer."""
        if self.hist.__dict__.get("_data_writer") is self:
            self._commit()
            self.hist._draw()
            self.hist.__dict__.pop("_data_writer")


class GrowBars(MappedPresentation):
    """Grow bound bars from their bases in a stable semantic order.

    Parameters
    ----------
    bars, lag_ratio, **kwargs
        Bar container, stagger between bars and native animation options.
    order
        Data order, ascending signed height, or a key receiving each bound bar.
    reverse, remover
        Reverse the complete schedule and optionally remove the container.
    """

    def __init__(
        self,
        bars: VGroup,
        lag_ratio: float = 0.05,
        *,
        order: str | Callable[[_Bar], Any] = "data",
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.bars import _Bar
        from manim_plots.mobjects.plots3d import BarPlot3D

        if not callable(order) and order not in ("data", "height"):
            raise ValueError("unknown bar order")
        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        self.order = order
        self._container = bars
        self._hist = bars if isinstance(bars, HistPlot) else None
        self._surface = bars._surface if isinstance(bars, BarPlot3D) else None
        self._bars = [b for b in bars.get_family() if isinstance(b, _Bar)]
        if (
            self._hist is None
            and self._surface is None
            and len(self._bars) != len(bars)
        ):
            raise TypeError("bars must be a bound bar container")
        self.reverse = reverse
        self._legacy_shrink = False
        flags(reverse, remover, kwargs)
        super().__init__(bars, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Resolve stable bar timing from current data."""
        self._outline_sources = (
            [] if self._hist is None else [p.source for p in self._hist.outlines]
        )
        if self.order != "data":
            self._bars = sorted(
                self._bars,
                key=self.order
                if callable(self.order)
                else lambda b: float(b.parameters["height"].value),
            )
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply each bar's staggered progress to its drawn height.

        Parameters
        ----------
        alpha
            Native progress before the rate function.
        """
        self._alpha = alpha
        if self._hist is not None and self._hist.outlines:
            hist = self._hist
            count = len(hist.edges) - 1
            timing = 1 - alpha if self.reverse else alpha
            progress = np.array(
                [
                    self.rate_func(window(timing, i, count, self.lag_ratio))
                    for i in range(count)
                ]
            )
            if self._legacy_shrink:
                progress = 1 - progress
            base = np.broadcast_to(
                np.asarray(hist._bottom, dtype=float), (count,)
            ).copy()
            for outline, heights in zip(hist.outlines, hist._counts, strict=True):
                source = outline.source
                outline.source = ArraySource(
                    _stairs_vertices(
                        base + heights * progress,
                        hist.edges,
                        base,
                        hist._orientation,
                        hist._histtype == "stepfilled",
                    )
                )
                try:
                    outline._rebuild()
                finally:
                    outline.source = source
                if hist._stacked:
                    base += heights * progress
            return
        count = (
            len(self._bars)
            if self._surface is None
            else len(self._surface._bar_corners) // 6
        )
        if self.reverse:
            alpha = 1 - alpha
        progress = np.array(
            [
                self.rate_func(window(alpha, i, count, self.lag_ratio))
                for i in range(count)
            ]
        )
        if self._legacy_shrink:
            progress = 1 - progress
        if self._surface is not None:
            self._surface._growth = progress
            self._surface._derive()
        else:
            for bar, factor in zip(self._bars, progress, strict=True):
                assert bar._system is not None
                for parameter in bar.parameters.values():
                    parameter.poll(bar._system._token)
                bar._height_scale = factor
                bar._dirty = True
                bar._rebuild()

    def _restore_bars(self) -> None:
        if self._hist is not None:
            for outline, source in zip(
                self._hist.outlines, self._outline_sources, strict=True
            ):
                outline.source = source
                outline.refresh()
        if self._surface is not None:
            self._surface._growth = None
            self._surface._derive()
        for bar in self._bars:
            bar._height_scale = 1.0
            bar._dirty = True
            bar.refresh()

    def finish(self) -> None:
        """Restore canonical bound geometry after the animation."""
        super().finish()
        self._restore_bars()

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Remove shrinking bars and retain their original bound geometry.

        Parameters
        ----------
        scene
            Scene owning the animation.
        """
        super().clean_up_from_scene(scene)
        self._restore_bars()


class ShrinkBars(GrowBars):
    """Shrink bound bars to their bases and remove the container.

    Parameters
    ----------
    bars, lag_ratio, **kwargs
        Bar container, stagger and native animation options.
    """

    def __init__(self, bars: VGroup, lag_ratio: float = 0.05, **kwargs: object) -> None:
        kwargs.setdefault("introducer", False)
        kwargs.setdefault("remover", True)
        super().__init__(bars, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))
        self._legacy_shrink = True


class SortBars(Animation):
    """Slide bars into a stable order of their heights.

    Parameters
    ----------
    bars, key, reverse, **kwargs
        Bound bars, optional height key, descending flag and native options.
    """

    def __init__(
        self,
        bars: BarPlot,
        key: Callable[[float], Any] | None = None,
        reverse: bool = False,
        **kwargs: object,
    ) -> None:
        if not isinstance(bars, BarPlot):
            raise TypeError("bars must be a BarPlot")
        self.bars, self.key, self.reverse = bars, key, reverse
        super().__init__(bars, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Compute slots from the current data when the animation starts."""
        self._items = [cast(_Bar, b) for b in self.bars.submobjects]
        self._keys = list(self.bars._keys)
        self._order = sorted(
            range(len(self._items)),
            key=lambda i: (
                float(self._items[i].parameters["height"].value)
                if self.key is None
                else self.key(float(self._items[i].parameters["height"].value))
            ),
            reverse=self.reverse,
        )
        self._starts = np.array([b.parameters["x"].value for b in self._items])
        axis = self.bars._system.y if self.bars.horizontal else self.bars._system.x
        slots = (
            np.arange(len(self._items)) if axis.categories else np.sort(self._starts)
        )
        self._ends = self._starts.copy()
        for slot, index in enumerate(self._order):
            self._ends[index] = slots[slot]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Move category positions without changing heights.

        Parameters
        ----------
        alpha
            Native progress before the rate function.
        """
        progress = self.rate_func(alpha)
        for bar, position in zip(
            self._items,
            (1 - progress) * self._starts + progress * self._ends,
            strict=True,
        ):
            bar.parameters["x"].value = position
            bar._dirty = True
            bar._rebuild()

    def finish(self) -> None:
        """Publish the sorted group and categorical tick table."""
        super().finish()
        self.bars._keys = [self._keys[i] for i in self._order]
        self.bars.submobjects = [self._items[i] for i in self._order]
        axis = self.bars._system.y if self.bars.horizontal else self.bars._system.x
        if axis.categories:
            fixed = axis._categories_fixed
            axis.set_categories([str(k) for k in self.bars._keys])
            axis._categories_fixed = fixed
        for bar in self._items:
            bar.refresh()


class HighlightBar(AnimationGroup):
    """Indicate one keyed bar while temporarily dimming the others.

    Parameters
    ----------
    bars, key, dim_opacity, **kwargs
        Bar container, key, other bars' fill opacity and native group options.
    """

    def __init__(
        self, bars: BarPlot, key: object, dim_opacity: float = 0.25, **kwargs: object
    ) -> None:
        if not np.isfinite(dim_opacity) or not 0 <= dim_opacity <= 1:
            raise ValueError("dim_opacity must be between zero and one")
        selected = bars.at(key)
        self._fills = [
            (leaf, float(leaf.get_fill_opacity()))
            for bar in bars
            for leaf in bar.get_family()
            if isinstance(leaf, VMobject)
        ]
        animations = [
            Transform(
                bar, bar.copy().set_fill(opacity=dim_opacity), rate_func=there_and_back
            )
            for bar in bars
            if bar is not selected
        ]
        super().__init__(
            *animations, Indicate(selected), **cast(dict[str, Any], kwargs)
        )

    def finish(self) -> None:
        """Restore every original fill opacity after indicating the bar."""
        super().finish()
        for leaf, opacity in self._fills:
            leaf.set_fill(opacity=opacity, family=False)


class GrowStack(MappedPresentation):
    """Grow layer thicknesses on the preceding layers' animated support.

    Parameters
    ----------
    series
        StackPlot, stacked histogram, or group of bound bar layers.
    lag_ratio, reverse, remover, **kwargs
        Layer staggering, playback direction, removal and native options.
    """

    def __init__(
        self,
        series: VGroup,
        *,
        lag_ratio: float = 0.15,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.histograms import StackPlot

        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        self._regions = series.regions if isinstance(series, StackPlot) else []
        layers = series.bars if isinstance(series, HistPlot) else series.submobjects
        self._layers = (
            [] if self._regions else [cast(BarPlot, layer) for layer in (layers or [])]
        )
        if not self._regions and not all(
            isinstance(layer, BarPlot) for layer in self._layers
        ):
            raise TypeError("series must contain bound stack layers")
        self.reverse = reverse
        flags(reverse, remover, kwargs)
        super().__init__(series, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply local thicknesses without changing canonical layer data."""
        self._alpha = alpha
        count = len(self._regions or self._layers)
        timing = 1 - alpha if self.reverse else alpha
        progress = [
            self.rate_func(window(timing, i, count, self.lag_ratio))
            for i in range(count)
        ]
        if self._regions:
            support = None
            for region, factor in zip(self._regions, progress, strict=True):
                binding = region._binding
                binding.ensure()
                original = binding.boundaries[region._part]
                system = binding.system
                pairs = []
                for upper, lower in original:
                    top, bottom = (
                        system._data.inverse(upper),
                        system._data.inverse(lower),
                    )
                    if support is None:
                        support = bottom.copy()
                    end = support.copy()
                    end[:, 1] += factor * (top[:, 1] - bottom[:, 1])
                    pairs.append(
                        (system._data.forward(end), system._data.forward(support))
                    )
                    support = end
                binding.boundaries[region._part] = pairs
                try:
                    region._rebuild()
                finally:
                    binding.boundaries[region._part] = original
        else:
            final: dict[tuple[float, bool], float] = {}
            drawn: dict[tuple[float, bool], float] = {}
            for layer, factor in zip(self._layers, progress, strict=True):
                for item in layer:
                    bar = cast(_Bar, item)
                    height = float(bar.parameters["height"].value)
                    key = (float(bar.parameters["x"].value), height >= 0)
                    bar._height_scale = factor
                    parameters = bar.parameters
                    bar.parameters = {
                        **parameters,
                        "bottom": Parameter(
                            float(parameters["bottom"].value)
                            + drawn.get(key, 0)
                            - final.get(key, 0),
                            name="bottom",
                        ),
                    }
                    try:
                        bar._rebuild()
                    finally:
                        bar.parameters = parameters
                    final[key] = final.get(key, 0) + height
                    drawn[key] = drawn.get(key, 0) + factor * height

    def restore(self) -> None:
        """Release presentation ownership and rederive canonical layers."""
        super().restore()
        for region in self._regions:
            region.refresh()
        for layer in self._layers:
            for item in layer:
                bar = cast(_Bar, item)
                bar._height_scale = 1.0
                bar.refresh()


class _ChartPresentation(MappedPresentation):
    def __init__(
        self,
        artist: VGroup,
        *,
        lag_ratio: float,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not np.isfinite(lag_ratio) or lag_ratio < 0:
            raise ValueError("lag_ratio must be finite and nonnegative")
        self.reverse = reverse
        flags(reverse, remover, kwargs)
        super().__init__(artist, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        self._styles: dict[VMobject, dict[str, Any]] = {}
        self._style_ownership: dict[VMobject, dict[str, object]] = {}
        for part in self.mobject.get_family():
            if isinstance(part, VMobject):
                self._styles[part] = deepcopy(part.get_style())
                self._style_ownership[part] = {
                    name: part.__dict__[name]
                    for name in ("_styled", "_fill_color_set", "_stroke_color_set")
                    if name in part.__dict__
                }
        super().begin()

    def _progress(self, alpha: float, index: int, count: int) -> float:
        return float(
            self.rate_func(
                window(
                    1 - alpha if self.reverse else alpha, index, count, self.lag_ratio
                )
            )
        )

    def _fade(self, part: VMobject, factor: float) -> None:
        for leaf in part.get_family():
            if isinstance(leaf, VMobject):
                style = self._styles[leaf]
                VMobject.set_fill(
                    leaf,
                    opacity=cast(Any, np.asarray(style["fill_opacity"]) * factor),
                    family=False,
                )
                leaf.set_stroke(
                    opacity=cast(Any, np.asarray(style["stroke_opacity"]) * factor),
                    family=False,
                )
                leaf.set_stroke(
                    opacity=cast(
                        Any, np.asarray(style["background_stroke_opacity"]) * factor
                    ),
                    background=True,
                    family=False,
                )

    def restore(self) -> None:
        from manim_plots.mobjects.leaves import Leaf

        super().restore()
        for part, style in self._styles.items():
            part.set_style(**style, family=False)
            part.__dict__.update(self._style_ownership[part])
            if isinstance(part, Leaf):
                part.refresh()


class RevealCells(_ChartPresentation):
    """Fade scalar cells and their labels in a stable semantic order.

    Parameters
    ----------
    plot
        Heatmap, pcolormesh, histogram grid or hexbin artist.
    order, lag_ratio, reverse, remover, **kwargs
        Cell order, staggering, playback flags and native animation options.
    """

    def __init__(
        self,
        plot: HeatmapPlot,
        *,
        order: str | Callable[[tuple[int, int] | int, float], Any] = "row",
        lag_ratio: float = 0.02,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.heatmaps import HexbinPlot

        if not callable(order) and (
            order not in ("row", "column", "diagonal", "value")
            or (order == "diagonal" and isinstance(plot, HexbinPlot))
        ):
            raise ValueError("unknown cell order")
        self.plot, self.order = plot, order
        super().__init__(
            plot, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def begin(self) -> None:
        """Resolve cell order from current canonical scalar values."""
        from manim_plots.mobjects.heatmaps import HexbinPlot

        def key(item: tuple[tuple[int, int] | int, _Cell]) -> object:
            address, cell = item
            value = self.plot._values[cell._index]
            if callable(self.order):
                return self.order(address, value)
            if self.order == "value":
                return value
            row, column = (
                self.plot.centers[cast(int, address)][::-1]
                if isinstance(self.plot, HexbinPlot)
                else cast(tuple[int, int], address)
            )
            if self.order == "column":
                return column, row
            if self.order == "diagonal":
                return row + column, row, column
            return row, column

        self._cells = sorted(self.plot.cells._cells.items(), key=cast(Any, key))
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Multiply canonical opacity, leaving scalar maps and geometry intact."""
        self._alpha = alpha
        for i, (_, cell) in enumerate(self._cells):
            cell._rebuild()
            factor = self._progress(alpha, i, len(self._cells))
            self._fade(cell, factor)
            label = self.plot.__dict__.get("_label_objects", {}).get(cell._index)
            if label is not None:
                self._fade(label, factor)


class RevealContours(_ChartPresentation):
    """Fade filled bands or independently trace level curves.

    Parameters
    ----------
    contours
        Bound two-dimensional contour set.
    order, lag_ratio, reverse, remover, **kwargs
        Level order, staggering, playback flags and native options.
    """

    def __init__(
        self,
        contours: ContourSetPlot,
        *,
        order: str | Callable[[float], Any] = "level",
        lag_ratio: float = 0.15,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if not callable(order) and order != "level":
            raise ValueError("unknown contour order")
        self.contours, self.order = contours, order
        super().__init__(
            contours, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )

    def begin(self) -> None:
        """Resolve level timing while retaining exposed container order."""
        parts = list(self.contours._levels.values())
        levels = self.contours.levels
        values = (
            (levels[:-1] + levels[1:]) / 2 if parts and parts[0]._filled else levels
        )
        self._parts = [
            part
            for _, part in sorted(
                zip(values, parts, strict=True),
                key=lambda pair: (
                    self.order(float(pair[0])) if callable(self.order) else pair[0]
                ),
            )
        ]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply independent windows without joining canonical subpaths."""
        self._alpha = alpha
        for i, part in enumerate(self._parts):
            part._rebuild()
            factor = self._progress(alpha, i, len(self._parts))
            if part._filled:
                self._fade(part, factor)
            else:
                canonical = VMobject()
                canonical.points = part.points.copy()
                part.pointwise_become_partial(canonical, 0, factor)
