"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from collections.abc import Callable
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

from manim_plots.mobjects.bars import BarPlot, _Bar

from ._base import MappedPresentation, flags, window


class GrowBars(MappedPresentation):
    """Grow bound bars from their bases in data order.

    Parameters
    ----------
    bars, lag_ratio, **kwargs
        Bar container, stagger between bars and native animation options.
    """

    def __init__(
        self,
        bars: VGroup,
        lag_ratio: float = 0.05,
        *,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        from manim_plots.mobjects.bars import _Bar
        from manim_plots.mobjects.plots3d import BarPlot3D

        self._container = bars
        self._surface = bars._surface if isinstance(bars, BarPlot3D) else None
        self._bars = [b for b in bars.submobjects if isinstance(b, _Bar)]
        if self._surface is None and len(self._bars) != len(bars):
            raise TypeError("bars must be a bound bar container")
        self.reverse = reverse
        self._legacy_shrink = False
        flags(reverse, remover, kwargs)
        super().__init__(bars, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs))

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply each bar's staggered progress to its drawn height.

        Parameters
        ----------
        alpha
            Native progress before the rate function.
        """
        self._alpha = alpha
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
