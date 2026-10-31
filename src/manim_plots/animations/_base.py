"""Small shared tools for temporary, reversible presentation state."""

from __future__ import annotations

from typing import Any

import numpy as np
from manim import Animation, Scene


def flags(reverse: bool, remover: bool | None, kwargs: dict[str, Any]) -> None:
    """Keep playback direction independent from scene removal."""
    kwargs.setdefault("introducer", not reverse)
    kwargs["remover"] = reverse if remover is None else remover


def window(alpha: float, index: int, count: int, lag: float) -> float:
    """Return GrowBars' clipped per-part window before easing."""
    return float(np.clip(alpha * (1 + (count - 1) * lag) - index * lag, 0, 1))


class Presentation(Animation):
    """Restore temporary state at finish and cleanup, without owning updaters.

    Subclasses capture canonical state before calling begin and implement
    restore. Bindings remain the artist's responsibility. Declare only systems
    whose mapping changes through _involved_system, before begin (F-915).
    """

    def restore(self) -> None:
        """Restore the canonical state captured by the subclass."""

    def finish(self) -> None:
        """Finish native ownership before restoring canonical presentation."""
        super().finish()
        self.restore()

    def clean_up_from_scene(self, scene: Scene) -> None:
        """Restore reusable state even when the artist leaves the scene."""
        super().clean_up_from_scene(scene)
        self.restore()


class MappedPresentation(Presentation):
    """Reapply presentation on reads while native animation owns the buffers.

    Only transient leaves consult the hook, so bound systems without an
    animation keep their existing fast path. Release only hooks we acquired.
    """

    def begin(self) -> None:
        """Acquire a temporary presentation hook on the affected leaves."""
        self._alpha = 0.0
        self._applying = False
        self._presentation_leaves = self.mobject.get_family()
        if any("_presentation" in leaf.__dict__ for leaf in self._presentation_leaves):
            raise ValueError("concurrent presentation writer already owns this family")
        self._presentation_hook = lambda: self._present()
        for leaf in self._presentation_leaves:
            leaf.__dict__["_presentation"] = self._presentation_hook
        try:
            super().begin()
        except BaseException:
            self.restore()
            raise

    def _present(self) -> None:
        if not self._applying:
            self._applying = True
            try:
                self.interpolate_mobject(self._alpha)
            finally:
                self._applying = False

    def restore(self) -> None:
        """Release only presentation hooks acquired at begin."""
        for leaf in self._presentation_leaves:
            if leaf.__dict__.get("_presentation") is self._presentation_hook:
                leaf.__dict__.pop("_presentation")
