"""Shared ownership and timing for spatial part collections."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from manim import Mobject, VMobject

from manim_plots.core import FloatArray

from ._base import MappedPresentation, flags, window


def _halfspace(polygon: FloatArray, axis: int, edge: float, sign: int) -> FloatArray:
    output = []
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0), strict=True):
        ia, ib = sign * (a[axis] - edge) >= 0, sign * (b[axis] - edge) >= 0
        if ia:
            output.append(a)
        if ia != ib:
            output.append(a + (edge - a[axis]) / (b[axis] - a[axis]) * (b - a))
    return np.asarray(output, float).reshape(-1, polygon.shape[1])


class _Spatial(MappedPresentation):
    def __init__(
        self,
        artist: Mobject,
        *,
        lag_ratio: float = 0,
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
        """Capture styles before native ownership begins."""
        self._styles = {
            m: (m.fill_rgbas.copy(), m.stroke_rgbas.copy())
            for m in cast(Mobject, self.mobject).get_family()
            if isinstance(m, VMobject)
        }
        super().begin()

    def _progress(self, index: int = 0, count: int = 1) -> float:
        alpha = 1 - self._alpha if self.reverse else self._alpha
        return float(self.rate_func(window(alpha, index, count, self.lag_ratio)))

    def interpolate_mobject(self, alpha: float) -> None:
        """Apply presentation from canonical data at the current raw time.

        Parameters
        ----------
        alpha
            Native animation time before easing.
        """
        self._alpha = alpha
        applying = self._applying
        self._applying = True
        try:
            self._draw()
        finally:
            self._applying = applying

    def _draw(self) -> None:
        raise NotImplementedError

    def _visibility(self, mob: Mobject, factor: float) -> None:
        for leaf in mob.get_family():
            if isinstance(leaf, VMobject) and leaf in self._styles:
                fill, stroke = self._styles[leaf]
                leaf.fill_rgbas = fill.copy()
                leaf.stroke_rgbas = stroke.copy()
                leaf.fill_rgbas[:, 3] *= factor
                leaf.stroke_rgbas[:, 3] *= factor

    def restore(self) -> None:
        """Release temporary ownership and restore original part styles."""
        super().restore()
        for leaf, (fill, stroke) in self._styles.items():
            leaf.fill_rgbas = fill.copy()
            leaf.stroke_rgbas = stroke.copy()
