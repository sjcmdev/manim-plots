"""Artist-aware creation, ordered reveals and arc-length morphing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np

if TYPE_CHECKING:
    from manim_plots.mobjects.surfaces import SurfacePlot

from ._base import MappedPresentation, flags


class GrowSurface(MappedPresentation):
    """Raise a bound surface from a coordinate plane.

    Parameters
    ----------
    surface, zdir, offset, **kwargs
        Surface, growth coordinate, starting plane and animation options.
    """

    def __init__(
        self,
        surface: SurfacePlot,
        zdir: str = "z",
        offset: float | None = None,
        *,
        reverse: bool = False,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        if zdir not in ("x", "y", "z"):
            raise ValueError("zdir must be x, y or z")
        self.surface = surface
        self._axis = "xyz".index(zdir)
        self._offset = (
            min(surface._system._ranges[self._axis].range.value)
            if offset is None
            else float(offset)
        )
        if not np.isfinite(self._offset):
            raise ValueError("offset must be finite")
        scale = surface._system._ranges[self._axis]._scale
        if not np.isfinite(scale.forward(np.array([self._offset]))).all():
            raise ValueError("offset is outside the scale domain")
        self.reverse = reverse
        flags(reverse, remover, kwargs)
        super().__init__(surface, **cast(dict[str, Any], kwargs))

    def begin(self) -> None:
        """Capture final data buffers before animation takes ownership."""
        surface = self.surface
        surface._driver._ensure()
        mapping = surface._system._mapping()
        self._final = [mapping.inverse(face.points.copy()) for face in surface.faces]
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        """Map one shared growth fraction through the coordinate system.

        Parameters
        ----------
        alpha
            Animation progress before the rate function.
        """
        self._alpha = alpha
        progress = self.rate_func(1 - alpha if self.reverse else alpha)
        for face, final in zip(self.surface.faces, self._final, strict=True):
            data = final.copy()
            data[:, self._axis] = self._offset + progress * (
                data[:, self._axis] - self._offset
            )
            face.set_points(self.surface._system._mapping().to_screen(data))

    def finish(self) -> None:
        """Restore the bound surface with its final colours and no new updater."""
        super().finish()
        self.surface._building = False
        self.surface._driver._dirty = True
        self.surface._driver._ensure()


class ShrinkSurface(GrowSurface):
    """Lower a surface to its origin and remove it by default.

    Parameters
    ----------
    surface, zdir, offset, remover, **kwargs
        Bound surface, coordinate, origin, removal override and native options.
    """

    def __init__(
        self,
        surface: SurfacePlot,
        zdir: str = "z",
        offset: float | None = None,
        *,
        remover: bool | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(surface, zdir, offset, reverse=True, remover=remover, **kwargs)
