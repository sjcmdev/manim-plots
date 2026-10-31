"""Reveals for scene-positioned legends and live colorbars."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import numpy as np
from manim import (
    Animation,
    AnimationGroup,
    Create,
    LaggedStart,
    Scene,
    Uncreate,
    Unwrite,
    VGroup,
    VMobject,
    Write,
    linear,
)

from manim_plots.mobjects.colorbar import Colorbar, _colorbar_update
from manim_plots.mobjects.legend import Legend

from ._base import MappedPresentation, flags
from .helpers import _Composition, _LiveFadeIn, _LiveFadeOut


class RevealLegend(_Composition, LaggedStart):
    """Draw handles and write labels in retained entry order.

    Parameters
    ----------
    legend, lag_ratio
        Legend and overlap between equal entry windows.
    artist_animations
        Optional native animations paired with entries by index.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        legend: Legend,
        *,
        lag_ratio: float = 0.15,
        artist_animations: Sequence[Animation] | None = None,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        rate = cast(Callable[[float], float], kwargs.pop("rate_func", linear))
        linked = list(artist_animations or [])
        self._linked = linked
        if len(linked) > len(legend.entries):
            raise ValueError("artist_animations must correspond to legend entries")
        entries: list[Animation] = []
        for i, entry in enumerate(legend.entries):
            children = [
                (Uncreate if reverse else Create)(
                    entry.handle, run_time=1, rate_func=rate
                ),
                (Unwrite if reverse else Write)(
                    entry.label, run_time=1, rate_func=rate
                ),
            ]
            if i < len(linked):
                children.append(linked[i])
            entries.append(AnimationGroup(*children, run_time=1))
        if reverse:
            entries.reverse()
        schedule = (
            LaggedStart(*entries, lag_ratio=lag_ratio) if entries else Animation(legend)
        )
        children = [schedule]
        if legend.frame is not None:
            children.append(
                (Uncreate if reverse else Create)(
                    legend.frame, run_time=schedule.run_time, rate_func=rate
                )
            )
        flags(reverse, remover, kwargs)
        # Linked targets must be visible to Cairo before static-frame compilation.
        group = (
            VGroup(legend, *(cast(VMobject, a.mobject) for a in linked))
            if linked
            else legend
        )
        self.legend = legend
        super().__init__(*children, group=group, **cast(dict[str, Any], kwargs))
        cast(Any, self).mobject = legend

    def _setup_scene(self, scene: Scene) -> None:
        super()._setup_scene(scene)
        for animation in self._linked:
            animation._setup_scene(scene)

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Clean up the legend and every explicitly supplied artist animation.

        Parameters
        ----------
        scene
            Scene playing the legend and its linked animations.
        """
        super().clean_up_from_scene(scene)
        for animation in self._linked:
            animation.clean_up_from_scene(scene)


class _FillStrip(MappedPresentation):
    def __init__(self, bar: Colorbar, *, reverse: bool, **kwargs: object) -> None:
        self.bar, self.reverse = bar, reverse
        super().__init__(bar.strip, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        self._opacities = [float(cell.get_fill_opacity()) for cell in self.bar.strip]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        self._alpha = alpha
        _colorbar_update(self.bar, 0)
        p = self.rate_func(1 - alpha if self.reverse else alpha)
        for i, (cell, opacity) in enumerate(
            zip(self.bar.strip, self._opacities, strict=True)
        ):
            cell.set_fill(opacity=opacity * np.clip(64 * p - i, 0, 1))

    def restore(self) -> None:
        super().restore()
        for cell, opacity in zip(self.bar.strip, self._opacities, strict=True):
            cell.set_fill(opacity=opacity)


class FillColorbar(_Composition):
    """Fill normalized color cells, then reveal the value-axis decorations.

    Parameters
    ----------
    bar, lag_ratio
        Live colorbar and overlap of the two equal stages.
    reverse, remover, **kwargs
        Playback direction, scene removal and native animation options.
    """

    def __init__(
        self,
        bar: Colorbar,
        *,
        lag_ratio: float = 0,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        rate = cast(Callable[[float], float], kwargs.pop("rate_func", linear))
        self.bar = bar
        self._involved_system = bar
        decorations = VGroup(*(m for m in bar.submobjects if m is not bar.strip))
        children: list[Animation] = [
            _FillStrip(bar, reverse=reverse, run_time=1, rate_func=rate),
            (_LiveFadeOut if reverse else _LiveFadeIn)(
                decorations, run_time=1, rate_func=rate
            ),
        ]
        if reverse:
            children.reverse()
        flags(reverse, remover, kwargs)
        kwargs.setdefault("suspend_mobject_updating", False)
        super().__init__(
            *children, group=bar, lag_ratio=lag_ratio, **cast(dict[str, Any], kwargs)
        )

    def restore(self) -> None:
        """Keep the current mapping while restoring decoration styles."""
        for leaf, _, style in self._canonical:
            leaf.set_style(**style, family=False)
        _colorbar_update(self.bar, 0)
