"""Small shared tools for temporary, reversible presentation state."""

from __future__ import annotations

from typing import Any

import numpy as np
from manim import Animation, Mobject, Scene


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
        self._presented_alpha: float | None = None
        self._presented_buffers: dict[int, object] = {}
        self._presentation_systems = {
            system
            for part in self._presentation_leaves
            if (system := getattr(part, "_system", None)) is not None
        }
        self._presented_revision: tuple[tuple[int, int, int], ...] = ()
        self._presented_parameters: dict[int, tuple[int, ...]] = {}
        self._presentation_hook = self._present
        for leaf in self._presentation_leaves:
            leaf.__dict__["_presentation"] = self._presentation_hook
        try:
            super().begin()
        except BaseException:
            self.restore()
            raise

    def _present(self, leaf: Mobject) -> None:
        if self._applying:
            return
        parameters = leaf.__dict__.get("parameters", {})
        system = leaf.__dict__.get("_system")
        versions = tuple(
            parameter.poll(system._token if system is not None else None)
            for parameter in parameters.values()
        )
        buffer = leaf.__dict__.get("_cache", leaf.__dict__.get("_face_points"))
        if (
            self._presented_alpha != self._alpha
            or self._presented_revision != self._revision()
            or self._presented_parameters.get(id(leaf), ()) != versions
            or self._presented_buffers.get(id(leaf)) is not buffer
        ):
            self.interpolate(self._alpha)

    def _revision(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(
            (system._token, system._data_version, system.frame.version)
            for system in self._presentation_systems
        )

    def interpolate(self, alpha: float) -> None:
        """Apply once, guarding reads until all family buffers are complete."""
        self._applying = True
        try:
            super().interpolate(alpha)
            self._presented_alpha = self._alpha
            self._presented_revision = self._revision()
            self._presented_parameters = {
                id(part): tuple(
                    parameter.version
                    for parameter in part.__dict__.get("parameters", {}).values()
                )
                for part in self._presentation_leaves
            }
            # Keep references: canonical rebuilds replace these buffers.
            self._presented_buffers = {
                id(part): part.__dict__.get("_cache", part.__dict__.get("_face_points"))
                for part in self._presentation_leaves
            }
        finally:
            self._applying = False

    def restore(self) -> None:
        """Release only presentation hooks acquired at begin."""
        for leaf in self._presentation_leaves:
            if leaf.__dict__.get("_presentation") is self._presentation_hook:
                leaf.__dict__.pop("_presentation")
