"""Standalone pies and bound statistical artists."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Self, cast

import numpy as np
from manim import LEFT, ORIGIN, RIGHT, Mobject, Sector, Text, VGroup, config
from manim.typing import PathFuncType

from manim_plots.core import FloatArray
from manim_plots.mobjects.artists import (
    COLOR_CYCLE,
    LinePlot,
    ScatterPlot,
    _cycle_style,
)
from manim_plots.mobjects.heatmaps import _label_color
from manim_plots.mobjects.helpers import FilledRegion
from manim_plots.mobjects.system import CartesianAxes


def _fractions(x: object, normalize: bool) -> FloatArray:
    values = np.asarray(x, dtype=float)
    if (
        values.ndim != 1
        or not len(values)
        or not np.isfinite(values).all()
        or np.any(values < 0)
    ):
        raise ValueError("pie values must be a nonempty finite nonnegative vector")
    total = float(values.sum())
    if normalize:
        if not np.isfinite(total) or total <= 0:
            raise ValueError("pie values must have a positive sum")
        return values / total
    if total > 1:
        raise ValueError("normalize=False requires a sum at most one")
    return values


class _Wedge(Sector):
    _pie_center: FloatArray
    _explode_distance: float

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFuncType | None = None,
    ) -> Self:
        if isinstance(mobject1, _Wedge) and isinstance(mobject2, _Wedge):
            self.start_angle = (
                1 - alpha
            ) * mobject1.start_angle + alpha * mobject2.start_angle
            self.angle = (1 - alpha) * mobject1.angle + alpha * mobject2.angle
            middle = self.start_angle + self.angle / 2
            self.arc_center = self._pie_center + self._explode_distance * np.array(
                [np.cos(middle), np.sin(middle), 0]
            )
            self.clear_points()
            self.generate_points()
            self.interpolate_color(mobject1, mobject2, alpha)
            return self
        return super().interpolate(
            mobject1,
            mobject2,
            alpha,
            **({} if path_func is None else {"path_func": path_func}),
        )


class PieChart(VGroup):
    """Draw sectors with stable identities and animated angular shares.

    Parameters
    ----------
    x, explode, labels, colors, autopct
        Nonnegative values, radial offsets, labels, colours and percent format.
    pctdistance, labeldistance, startangle, radius, counterclock, normalize, center
        Label radii, initial angle in degrees, geometry and normalization.
    wedge_config, text_config
        Native Manim styles for sectors and text.
    """

    def __init__(
        self,
        x: object,
        *,
        explode: object = None,
        labels: Sequence[str] | None = None,
        colors: Sequence[Any] | None = None,
        autopct: str | Callable[[float], str] | None = None,
        pctdistance: float = 0.6,
        labeldistance: float = 1.1,
        startangle: float = 0,
        radius: float = 2,
        counterclock: bool = True,
        normalize: bool = True,
        center: object = ORIGIN,
        wedge_config: dict[str, Any] | None = None,
        text_config: dict[str, Any] | None = None,
    ) -> None:
        self.fractions = _fractions(x, normalize)
        self.normalize, self.radius = normalize, radius
        self.startangle, self.counterclock = startangle, counterclock
        self._center = np.asarray(center, dtype=float)
        self.explode = (
            np.zeros(len(self.fractions))
            if explode is None
            else np.asarray(explode, dtype=float)
        )
        if (
            self.explode.shape != self.fractions.shape
            or not np.isfinite(self.explode).all()
        ):
            raise ValueError("explode must contain one finite offset per wedge")
        if (
            not np.isfinite(radius)
            or radius <= 0
            or self._center.shape != (3,)
            or not np.isfinite(self._center).all()
        ):
            raise ValueError("radius must be positive and center finite")
        if labels is not None and len(labels) != len(self.fractions):
            raise ValueError("labels must contain one string per wedge")
        if colors is not None and not len(colors):
            raise ValueError("colors must not be empty")
        self.autopct, self.pctdistance, self.labeldistance = (
            autopct,
            pctdistance,
            labeldistance,
        )
        self._text_config = {"font_size": 24, **(text_config or {})}
        palette = COLOR_CYCLE if colors is None else colors
        self.wedges = VGroup(
            *[
                _Wedge(
                    radius=radius,
                    **{
                        "color": palette[i % len(palette)],
                        "fill_opacity": 1,
                        "stroke_color": config.background_color,
                        "stroke_width": 2,
                        **(wedge_config or {}),
                    },
                )
                for i in range(len(self.fractions))
            ]
        )
        self.texts = (
            None
            if labels is None
            else VGroup(*[Text(label, **self._text_config) for label in labels])
        )
        self.autotexts = (
            None
            if autopct is None
            else VGroup(
                *[
                    Text(
                        self._percentage(float(f)),
                        **{
                            "color": _label_color(self.wedges[i].get_fill_color()),
                            **self._text_config,
                        },
                    )
                    for i, f in enumerate(self.fractions)
                ]
            )
        )
        super().__init__(
            self.wedges, *[g for g in (self.texts, self.autotexts) if g is not None]
        )
        self._rebuild()

    def _percentage(self, fraction: float) -> str:
        assert self.autopct is not None
        return (
            self.autopct(100 * fraction)
            if callable(self.autopct)
            else self.autopct % (100 * fraction)
        )

    def _rebuild(self) -> None:
        angle = np.deg2rad(self.startangle)
        for i, fraction in enumerate(self.fractions):
            sweep = (1 if self.counterclock else -1) * 2 * np.pi * fraction
            direction = np.array(
                [np.cos(angle + sweep / 2), np.sin(angle + sweep / 2), 0]
            )
            center = self._center + self.explode[i] * self.radius * direction
            wedge = cast(_Wedge, self.wedges[i])
            wedge._pie_center = self._center
            wedge._explode_distance = self.explode[i] * self.radius
            wedge.start_angle, wedge.angle, wedge.arc_center = angle, sweep, center
            wedge.clear_points()
            wedge.generate_points()
            if self.texts is not None:
                self.texts[i].move_to(
                    center + self.labeldistance * self.radius * direction,
                    aligned_edge=LEFT if direction[0] >= 0 else RIGHT,
                )
            if self.autotexts is not None:
                text = cast(Text, self.autotexts[i])
                fresh = Text(
                    self._percentage(float(fraction)), **self._text_config
                ).match_style(text)
                text.become(fresh)
                text.text = fresh.text
                text.move_to(center + self.pctdistance * self.radius * direction)
            angle += sweep

    def set_data(self, x: object) -> Self:
        """Replace values while retaining wedge and label identities.

        Parameters
        ----------
        x
            Nonnegative values with the original count.
        """
        fractions = _fractions(x, self.normalize)
        if fractions.shape != self.fractions.shape:
            raise ValueError("set_data must retain the wedge count")
        self.fractions = fractions
        self._rebuild()
        return self


def _samples(x: object) -> list[FloatArray]:
    entries = list(cast(Any, x))
    samples = (
        [np.asarray(entries, dtype=float)]
        if entries and np.isscalar(entries[0])
        else [np.asarray(v, dtype=float) for v in entries]
    )
    if not samples or any(
        v.ndim != 1 or not len(v) or not np.isfinite(v).all() for v in samples
    ):
        raise ValueError("datasets must be nonempty finite vectors")
    return samples


def _layout(
    n: int, positions: object, widths: object, orientation: str
) -> tuple[FloatArray, FloatArray]:
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation must be vertical or horizontal")
    pos = (
        np.arange(1, n + 1, dtype=float)
        if positions is None
        else np.asarray(positions, dtype=float)
    )
    width = np.broadcast_to(np.asarray(widths, dtype=float), (n,))
    if (
        pos.shape != (n,)
        or not np.isfinite(pos).all()
        or not np.isfinite(width).all()
        or np.any(width <= 0)
    ):
        raise ValueError("positions and positive widths must match datasets")
    return pos, width


def _coordinates(points: object, orientation: str) -> FloatArray:
    array = np.asarray(points, dtype=float).reshape(-1, 2)
    return array[:, ::-1] if orientation == "horizontal" else array


def _box_stats(sample: FloatArray, whis: object) -> dict[str, Any]:
    q1, med, q3 = np.percentile(sample, [25, 50, 75])
    if np.isscalar(whis):
        factor = float(cast(Any, whis))
        if not np.isfinite(factor) or factor < 0:
            raise ValueError("whis must be finite and nonnegative")
        lo, hi = q1 - factor * (q3 - q1), q3 + factor * (q3 - q1)
    else:
        percentiles = np.asarray(whis, dtype=float)
        if (
            percentiles.shape != (2,)
            or not 0 <= percentiles[0] <= percentiles[1] <= 100
        ):
            raise ValueError("whis must be an ordered percentile pair")
        lo, hi = np.percentile(sample, percentiles)
    lower, upper = sample[sample >= lo], sample[sample <= hi]
    whislo = min(q1, lower.min()) if len(lower) else q1
    whishi = max(q3, upper.max()) if len(upper) else q3
    return dict(
        q1=q1,
        med=med,
        q3=q3,
        whislo=whislo,
        whishi=whishi,
        mean=sample.mean(),
        fliers=sample[(sample < whislo) | (sample > whishi)],
    )


class BoxPlot(VGroup):
    """Build bound boxes, whiskers, caps and markers from sample statistics.

    Parameters
    ----------
    system, x, positions, widths, whis, orientation
        Axes, samples, positions, box widths, whisker rule and direction.
    showmeans, showfliers, tick_labels, **style
        Marker visibility, categorical labels and box styles.
    """

    def __init__(
        self,
        system: CartesianAxes,
        x: object,
        positions: object = None,
        *,
        widths: object = 0.5,
        whis: object = 1.5,
        orientation: str = "vertical",
        showmeans: bool = False,
        showfliers: bool = True,
        tick_labels: Sequence[str] | None = None,
        **style: object,
    ) -> None:
        from manim_plots.mobjects.artists import Marker
        from manim_plots.mobjects.axis import resolve_categories

        samples = _samples(x)
        pos, width = _layout(len(samples), positions, widths, orientation)
        self.stats = [_box_stats(sample, whis) for sample in samples]
        if tick_labels is not None:
            if len(tick_labels) != len(samples):
                raise ValueError("tick_labels must match datasets")
            axis = system.y if orientation == "horizontal" else system.x
            pos = np.asarray(resolve_categories(axis, tick_labels), dtype=float)
        self.boxes: list[FilledRegion] = []
        self.medians: list[LinePlot] = []
        self.whiskers: list[LinePlot] = []
        self.caps: list[LinePlot] = []
        self.fliers: list[ScatterPlot | VGroup] = []
        self.means: list[ScatterPlot] = []
        own = dict(style)
        _cycle_style(system, cast(Any, own))
        median_style: Any = {}
        _cycle_style(system, median_style)
        color = cast(Any, own.get("color", own.get("stroke_color")))
        super().__init__()
        for p, w, s in zip(pos, width, self.stats, strict=True):

            def line(points: object, **options: object) -> LinePlot:
                return system.line(
                    _coordinates(points, orientation), **cast(Any, options)
                )

            fill = (
                system.fill_betweenx
                if orientation == "horizontal"
                else system.fill_between
            )
            self.boxes.append(
                fill(
                    [p - w / 2, p + w / 2],
                    s["q3"],
                    s["q1"],
                    **cast(Any, {"fill_opacity": 0, "stroke_width": 2, **own}),
                )
            )
            self.medians.append(
                line([(p - w / 2, s["med"]), (p + w / 2, s["med"])], **median_style)
            )
            for end, quartile in ((s["whislo"], s["q1"]), (s["whishi"], s["q3"])):
                self.whiskers.append(line([(p, quartile), (p, end)], color=color))
                self.caps.append(
                    line([(p - w / 4, end), (p + w / 4, end)], color=color)
                )
            if showfliers:
                self.fliers.append(
                    system.scatter(
                        _coordinates([(p, v) for v in s["fliers"]], orientation),
                        marker=Marker.CIRCLE,
                        color=color,
                        fill_opacity=0,
                    )
                    if len(s["fliers"])
                    else VGroup()
                )
            if showmeans:
                self.means.append(
                    system.scatter(
                        _coordinates([(p, s["mean"])], orientation), color=color
                    )
                )
        self.add(
            *self.boxes,
            *self.medians,
            *self.whiskers,
            *self.caps,
            *self.fliers,
            *self.means,
        )


def _kde(
    sample: FloatArray, points: int, bw_method: object
) -> tuple[FloatArray, FloatArray]:
    factor = (
        len(sample) ** (-1 / 5)
        if bw_method is None
        else (bw_method(sample) if callable(bw_method) else bw_method)
    )
    bandwidth = (
        float(cast(Any, factor)) * float(np.std(sample, ddof=1))
        if len(sample) > 1
        else 0.0
    )
    if not np.isfinite(bandwidth) or bandwidth <= 0:
        raise ValueError("KDE requires positive finite bandwidth and sample variance")
    grid = np.linspace(sample.min(), sample.max(), points)
    z = (grid[:, None] - sample[None, :]) / bandwidth
    density = np.exp(-0.5 * z * z).mean(axis=1) / (bandwidth * np.sqrt(2 * np.pi))
    return grid, density


class ViolinPlot(VGroup):
    """Build bound violin polygons using NumPy Gaussian density estimates.

    Parameters
    ----------
    system, dataset, positions, widths, orientation
        Axes, samples, positions, body widths and direction.
    showmeans, showextrema, showmedians, points, bw_method, **style
        Summary visibility, grid size, bandwidth factor and native body styles.
    """

    def __init__(
        self,
        system: CartesianAxes,
        dataset: object,
        positions: object = None,
        *,
        widths: object = 0.5,
        orientation: str = "vertical",
        showmeans: bool = False,
        showextrema: bool = True,
        showmedians: bool = False,
        points: int = 100,
        bw_method: object = None,
        **style: object,
    ) -> None:
        if not isinstance(points, int) or points < 2:
            raise ValueError("points must be an integer at least two")
        samples = _samples(dataset)
        pos, width = _layout(len(samples), positions, widths, orientation)
        densities = [_kde(sample, points, bw_method) for sample in samples]
        self.bodies: list[FilledRegion] = []
        self.cbars: list[LinePlot] = []
        self.cmins: list[LinePlot] = []
        self.cmaxes: list[LinePlot] = []
        self.cmeans: list[LinePlot] = []
        self.cmedians: list[LinePlot] = []
        own = dict(style)
        _cycle_style(system, cast(Any, own))
        color = cast(Any, own.get("color", own.get("stroke_color")))
        super().__init__()
        for sample, p, w, (grid, density) in zip(
            samples, pos, width, densities, strict=True
        ):
            half = 0.5 * w * density / density.max()
            fill = (
                system.fill_between
                if orientation == "horizontal"
                else system.fill_betweenx
            )
            self.bodies.append(
                fill(
                    grid,
                    p + half,
                    p - half,
                    **cast(Any, {"fill_opacity": 0.3, "stroke_width": 1, **own}),
                )
            )

            def line(coords: object) -> LinePlot:
                return system.line(_coordinates(coords, orientation), color=color)

            if showextrema:
                self.cbars.append(line([(p, sample.min()), (p, sample.max())]))
                self.cmins.append(
                    line([(p - w / 4, sample.min()), (p + w / 4, sample.min())])
                )
                self.cmaxes.append(
                    line([(p - w / 4, sample.max()), (p + w / 4, sample.max())])
                )
            for show, value, parts in (
                (showmeans, sample.mean(), self.cmeans),
                (showmedians, np.median(sample), self.cmedians),
            ):
                if show:
                    parts.append(line([(p - w / 4, value), (p + w / 4, value)]))
        self.add(
            *self.bodies,
            *self.cbars,
            *self.cmins,
            *self.cmaxes,
            *self.cmeans,
            *self.cmedians,
        )
