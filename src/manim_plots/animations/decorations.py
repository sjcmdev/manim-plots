"""Construction of independent inset viewports."""

from __future__ import annotations

from typing import Any, cast

from manim import AnimationGroup, Group, Scene, VMobject, linear, smooth

from manim_plots.mobjects.inset import InsetAxes
from manim_plots.mobjects.leaves import Leaf

from ._base import flags
from ._spatial import _Spatial


class _InsetOpening(_Spatial):
    def __init__(self, inset: InsetAxes, **kwargs: object) -> None:
        self.inset = inset
        self._involved_system = inset
        parts = [part for part in inset.submobjects if part is not inset.frame]
        super().__init__(Group(*parts, *inset.mirrored), **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Keep the live box corners available while drawing its outline."""
        self._outline = Leaf(self.inset.zoom_box.points.copy())
        self._outline.match_style(self.inset.zoom_box)
        self.inset.zoom_box.add(self._outline)
        super().begin()

    def _draw(self) -> None:
        inset = self.inset
        inset.__dict__["_inset_expansion"] = self._progress(1, 3)
        inset._follow_parent()
        box = VMobject().set_points(inset.zoom_box.points.copy())
        self._outline.pointwise_become_partial(box, 0, self._progress(0, 3))
        self._visibility(inset.zoom_box, 0)
        self._visibility(self._outline, 1)
        for mirror in inset.mirrored:
            for leaf in mirror.get_family():
                if isinstance(leaf, Leaf):
                    leaf._rebuild()
            self._visibility(mirror, self._progress(2, 3))
        self._visibility(inset.connectors, self._progress(1, 3))

    def restore(self) -> None:
        """Restore the configured viewport and its bound content."""
        super().restore()
        self.inset.zoom_box.remove(self._outline)
        self.inset.__dict__.pop("_inset_expansion", None)
        self.inset._follow_parent()
        for mirror in self.inset.mirrored:
            for leaf in mirror.get_family():
                if isinstance(leaf, Leaf):
                    leaf.refresh()


class OpenInset(AnimationGroup):
    """Draw a zoom box, expand its viewport, then reveal mirrored artists.

    Parameters
    ----------
    inset, lag_ratio, reverse, remover, **kwargs
        Bound inset, stage overlap, playback flags and native animation options.
    """

    def __init__(
        self,
        inset: InsetAxes,
        *,
        lag_ratio: float = 0.25,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        self.inset = inset
        self._involved_system = inset
        options = dict(kwargs)
        easing = options.pop("rate_func", smooth)
        self._driver = _InsetOpening(
            inset, lag_ratio=lag_ratio, reverse=reverse, remover=False, rate_func=easing
        )
        flags(reverse, remover, options)
        options.setdefault("suspend_mobject_updating", False)
        options.setdefault("run_time", 1)
        super().__init__(
            self._driver,
            group=cast(Group, self._driver.mobject),
            rate_func=linear,
            **cast(dict[str, Any], options),
        )

    def _setup_scene(self, scene: Scene) -> None:
        if self.is_introducer():
            scene.add(self.inset, *self.inset.mirrored)

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Restore bound state and withdraw inset and mirror scene roots.

        Parameters
        ----------
        scene
            Scene owning the inset and any independently added mirrors.
        """
        super().clean_up_from_scene(scene)
        if self.is_remover():
            scene.remove(self.inset, *self.inset.mirrored)
        else:
            scene.add(self.inset, *self.inset.mirrored)


class CloseInset(OpenInset):
    """Collapse an inset towards its live zoom box and remove it by default.

    Parameters
    ----------
    inset, lag_ratio, reverse, remover, **kwargs
        Bound inset, stage overlap, playback flags and native animation options.
    """

    def __init__(
        self,
        inset: InsetAxes,
        *,
        lag_ratio: float = 0.25,
        reverse: bool = True,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            inset, lag_ratio=lag_ratio, reverse=reverse, remover=remover, **kwargs
        )
