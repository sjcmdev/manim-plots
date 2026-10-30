"""RGB colormaps and scale-aware mappings from data values to colours."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from manim import ManimColor
from numpy.typing import ArrayLike

from manim_plots.core import FloatArray
from manim_plots.core.scales import LinearScale, Scale
from manim_plots.mobjects.system import _scale


class Colormap:
    """Interpolate colours in RGB space.

    Parameters
    ----------
    colors
        Manim-compatible colours.
    positions
        Strictly increasing stop positions, starting at zero and ending at one.
    name
        Optional descriptive name.
    """

    def __init__(
        self,
        colors: Sequence[Any],
        positions: ArrayLike | None = None,
        name: str | None = None,
    ) -> None:
        self.colors = np.array([ManimColor(c).to_rgb() for c in colors])
        self.positions = (
            np.linspace(0, 1, len(colors))
            if positions is None
            else np.asarray(positions, dtype=float)
        )
        if (
            len(colors) < 2
            or self.positions.shape != (len(colors),)
            or self.positions[0] != 0
            or self.positions[-1] != 1
            or not np.all(np.diff(self.positions) > 0)
        ):
            raise ValueError("positions must increase from 0 to 1, one per colour")
        self.name = name

    def __call__(self, t: ArrayLike) -> FloatArray:
        """Return RGB values for clipped scalar or array positions.

        Parameters
        ----------
        t
            Positions in the unit interval.

        Returns
        -------
        ndarray
            RGB array with shape ``t.shape + (3,)``.
        """
        values = np.clip(np.asarray(t, float), 0, 1)
        return np.stack(
            [np.interp(values, self.positions, self.colors[:, c]) for c in range(3)],
            axis=-1,
        )


class _CallableColormap(Colormap):
    def __init__(self, function: Callable[[float], Sequence[float]]) -> None:
        self.function = function

    def __call__(self, t: ArrayLike) -> FloatArray:
        values = np.clip(np.asarray(t, float), 0, 1)
        return np.asarray(
            [self.function(float(v))[:3] for v in values.ravel()], dtype=float
        ).reshape((*values.shape, 3))


@dataclass(frozen=True)
class ColorMapping:
    """Map a data interval to RGB using a coordinate scale.

    Parameters
    ----------
    colormap
        Unit-interval RGB mapping.
    vmin, vmax
        Data endpoints.
    scale
        Scale used before normalisation.
    """

    colormap: Colormap
    vmin: float
    vmax: float
    scale: Scale

    def __call__(self, values: ArrayLike) -> FloatArray:
        """Return colours for data values.

        Parameters
        ----------
        values
            Scalar or array of data values.

        Returns
        -------
        ndarray
            RGB values with one trailing colour dimension.
        """
        lo, hi = self.scale.forward(np.asarray([self.vmin, self.vmax], float))
        return self.colormap(
            (self.scale.forward(np.asarray(values, float)) - lo) / (hi - lo)
        )


def resolve_colorscale(
    colorscale: object,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    norm: Scale | str | None = None,
    default_range: Sequence[float] | FloatArray = (0, 1),
    default_scale: Scale | None = None,
) -> ColorMapping:
    """Resolve a named, callable, colour-list or pivoted scale.

    Parameters
    ----------
    colorscale
        A colormap name, instance, callable or sequence of colours or pivots.
    vmin, vmax, norm
        Explicit normalisation bounds and scale.
    default_range, default_scale
        Bounds and scale used when omitted.

    Returns
    -------
    ColorMapping
        Resolved immutable mapping.
    """
    scale = (
        _scale(norm, "norm") if norm is not None else (default_scale or LinearScale())
    )
    lo = float(default_range[0] if vmin is None else vmin)
    hi = float(default_range[1] if vmax is None else vmax)
    if isinstance(colorscale, str):
        cmap = colormaps[colorscale]
    elif isinstance(colorscale, Colormap):
        cmap = colorscale
    elif callable(colorscale):
        cmap = _CallableColormap(cast(Callable[[float], Sequence[float]], colorscale))
    else:
        colors = list(cast(Sequence[Any], colorscale))
        if colors and isinstance(colors[0], tuple) and len(colors[0]) == 2:
            if vmin is not None or vmax is not None:
                raise ValueError("vmin and vmax cannot be combined with pivots")
            stops, pivots = zip(*colors, strict=True)
            lo, hi = float(pivots[0]), float(pivots[-1])
            transformed = scale.forward(np.asarray(pivots, float))
            cmap = Colormap(
                stops,
                (transformed - transformed[0]) / (transformed[-1] - transformed[0]),
            )
        else:
            cmap = Colormap(colors)
    if not np.isfinite([lo, hi]).all() or hi <= lo:
        raise ValueError("vmin must be finite and less than vmax")
    if not np.isfinite(scale.forward(np.array([lo, hi]))).all():
        raise ValueError("vmin and vmax must be in the norm domain")
    return ColorMapping(cmap, lo, hi, scale)


# fmt: off
STOPS = {
    "viridis": (
        "#440154", "#48186a", "#472d7b", "#424086", "#3b528b", "#33638d",
        "#2c728e", "#26828e", "#21918c", "#1fa088", "#28ae80", "#3fbc73",
        "#5ec962", "#84d44b", "#addc30", "#d8e219", "#fde725",
    ),
    "plasma": (
        "#0d0887", "#310597", "#4c02a1", "#6600a7", "#7e03a8", "#9511a1",
        "#aa2395", "#bc3587", "#cc4778", "#da5a6a", "#e66c5c", "#f0804e",
        "#f89540", "#fdac33", "#fdc527", "#f8df25", "#f0f921",
    ),
    "inferno": (
        "#000004", "#0b0724", "#210c4a", "#3d0965", "#57106e", "#71196e",
        "#8a226a", "#a32c61", "#bc3754", "#d24644", "#e45a31", "#f1731d",
        "#f98e09", "#fcac11", "#f9cb35", "#f2ea69", "#fcffa4",
    ),
    "magma": (
        "#000004", "#0a0822", "#1d1147", "#36106b", "#51127c", "#6a1c81",
        "#832681", "#9c2e7f", "#b73779", "#d0416f", "#e75263", "#f56b5c",
        "#fc8961", "#fea772", "#fec488", "#fde2a3", "#fcfdbf",
    ),
    "cividis": (
        "#00224e", "#002e6a", "#1a386f", "#32436d", "#434e6c", "#535a6d",
        "#61656f", "#6f7073", "#7d7c78", "#8c8878", "#9b9476", "#aba072",
        "#bcae6c", "#cdbb63", "#dec958", "#f0d846", "#fee838",
    ),
    "coolwarm": (
        "#3b4cc0", "#4e68d8", "#6282ea", "#779af7", "#8db0fe", "#a3c2fe",
        "#b9d0f9", "#ccd9ed", "#dddcdc", "#ecd3c5", "#f5c4ac", "#f7b093",
        "#f4987a", "#eb7d62", "#dd5f4b", "#ca3b37", "#b40426",
    ),
    "RdBu_r": (
        "#053061", "#175290", "#2a71b2", "#3f8ec0", "#6bacd1", "#9bc9e0",
        "#c2ddec", "#e0ecf3", "#f7f6f6", "#fbe5d8", "#fbccb4", "#f5aa89",
        "#e48066", "#d05548", "#ba2832", "#930e26", "#67001f",
    ),
    "gray": (
        "#000000", "#101010", "#202020", "#303030", "#404040", "#505050",
        "#606060", "#707070", "#808080", "#909090", "#a0a0a0", "#b0b0b0",
        "#c0c0c0", "#d0d0d0", "#e0e0e0", "#f0f0f0", "#ffffff",
    ),
}
# fmt: on


colormaps: dict[str, Colormap] = {}
"""Named appendix colormaps and their reversed variants."""
for _name, _colors in STOPS.items():
    colormaps[_name] = Colormap(_colors, name=_name)
    colormaps[_name + "_r"] = Colormap(_colors[::-1], name=_name + "_r")
