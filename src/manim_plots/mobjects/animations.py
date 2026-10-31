"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import Any, cast

import numpy as np
from manim import (
    YELLOW,
    Animation,
    AnimationGroup,
    Create,
    FadeIn,
    Group,
    Indicate,
    Mobject,
    Scene,
    Transform,
    VGroup,
    VMobject,
    there_and_back,
)
from manim.utils.color import ParsableManimColor
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.payload import Payload
from manim_plots.core.shape import _restrict, resample_pair
from manim_plots.core.sources import ArraySource, FunctionSource
from manim_plots.mobjects.artists import LinePlot, ScatterPlot, _CurvePlot, _MarkerLeaf
from manim_plots.mobjects.axis import Axis
from manim_plots.mobjects.bars import BarPlot, _Bar
from manim_plots.mobjects.leaves import FrameLeaf
from manim_plots.mobjects.system import CartesianAxes


class GrowBars(Animation):
    """Grow bound bars from their bases in data order.

    Parameters
    ----------
    bars, lag_ratio, **kwargs
        Bar container, stagger between bars and native animation options.
    """

    def __init__(self, bars: VGroup, lag_ratio: float = 0.05, **kwargs: object) -> None:
        from manim_plots.mobjects.bars import _Bar
        from manim_plots.mobjects.plots3d import BarPlot3D

        self._container = bars
        self._surface = bars._surface if isinstance(bars, BarPlot3D) else None
        self._bars = [b for b in bars.submobjects if isinstance(b, _Bar)]
        if self._surface is None and len(self._bars) != len(bars):
            raise TypeError("bars must be a bound bar container")
        kwargs.setdefault("introducer", True)
        super().__init__(bars, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply each bar's staggered progress to its drawn height.

        Parameters
        ----------
        alpha
            Native progress before the rate function.
        """
        count = (
            len(self._bars)
            if self._surface is None
            else len(self._surface._bar_corners) // 6
        )
        progress = np.array(
            [
                self.rate_func(
                    float(
                        np.clip(
                            alpha * (1 + (count - 1) * self.lag_ratio)
                            - i * self.lag_ratio,
                            0,
                            1,
                        )
                    )
                )
                for i in range(count)
            ]
        )
        if self.remover:
            progress = 1 - progress
        if self._surface is not None:
            self._surface._growth = progress
            self._surface._derive()
        else:
            for bar, factor in zip(self._bars, progress, strict=True):
                bar._height_scale = factor
                bar._dirty = True
                bar._rebuild()

    def _restore_bars(self) -> None:
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
        self._ends = self._starts.copy()
        for slot, index in enumerate(self._order):
            self._ends[index] = self._starts[slot]
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
        self._new = ArraySource(x, y, dim=len(artist._system._ranges)).data
        if not np.isfinite(self._new).all():
            raise ValueError("appended coordinates must be finite")
        super().__init__(artist, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Snapshot the current source and prepare stable new scatter markers."""
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
        if isinstance(self.artist, LinePlot):
            self.artist.refresh()
        else:
            for marker in self.artist.submobjects:
                for leaf in marker.get_family():
                    if isinstance(leaf, _MarkerLeaf):
                        leaf.refresh()


class _FadeInParts(FadeIn):
    def get_all_families_zipped(self) -> Iterable[tuple[Mobject, ...]]:
        # NumberLabel parents carry observable style despite having no points.
        return zip(
            *(
                m.get_family()
                for m in (self.mobject, self.starting_mobject, self.target_copy)
            ),
            strict=True,
        )


class BuildAxes(AnimationGroup):
    """Build axis lines, ticks, numbers, then labels and grid in stages.

    Parameters
    ----------
    ax, lag_ratio, **kwargs
        Coordinate system, stage stagger and native group options.
    """

    def __init__(
        self, ax: CartesianAxes, lag_ratio: float = 0.5, **kwargs: object
    ) -> None:
        lines = VGroup(
            *(
                part
                for axis in ax._ranges
                for part in (axis.line, axis.tip)
                if part is not None
            )
        )
        ticks = VGroup(*(axis.ticks for axis in ax._ranges))
        numbers = VGroup(*(axis.numbers for axis in ax._ranges))
        labels = VGroup(
            *(part for axis in ax._ranges for part in (axis.labels, axis.grid))
        )
        super().__init__(
            Create(lines),
            Create(ticks),
            _FadeInParts(numbers),
            FadeIn(labels),
            lag_ratio=lag_ratio,
            **cast(dict[str, Any], kwargs),
        )


class HighlightTick(Indicate):
    """Indicate a keyed tick and its number together.

    Parameters
    ----------
    axis, value, color, scale_factor, **kwargs
        Axis, tick value, highlight colour, size factor and native options.
    """

    def __init__(
        self,
        axis: Axis,
        value: float,
        color: ParsableManimColor = YELLOW,
        scale_factor: float = 1.5,
        **kwargs: object,
    ) -> None:
        tick = axis.ticks.at(value)
        parts: list[Mobject] = [tick]
        with suppress(KeyError):
            parts.append(axis.numbers.at(value))
        super().__init__(
            Group(*parts),
            color=color,
            scale_factor=scale_factor,
            **cast(dict[str, Any], kwargs),
        )


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
