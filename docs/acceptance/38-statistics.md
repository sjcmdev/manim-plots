# Acceptance table — task 38, statistics: pie, box, violin

**Status: Record (merged 2026-10-31).** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1 (`pie`, `boxplot`, `violinplot` taken
into the release); ADR 0004 §9 (every part addressable and styleable); task 31 (bars,
BA-6's legend handle, CA rows); task 16 (bound helpers).

Modules: `mobjects/statistics.py` (new: `PieChart`, `BoxPlot`, `ViolinPlot`),
`mobjects/system.py` (`boxplot`, `violinplot`), `src/manim_plots/__init__.py`.

```python
class PieChart(VGroup):  # mp.PieChart — standalone, like Manim's BarChart
    def __init__(
        self,
        x,
        *,
        explode=None,
        labels=None,
        colors=None,
        autopct=None,
        pctdistance=0.6,
        labeldistance=1.1,
        startangle=0,
        radius=2,
        counterclock=True,
        normalize=True,
        center=ORIGIN,
        wedge_config=None,
        text_config=None,
    ): ...

    wedges: VGroup  # one Sector per value
    texts: VGroup | None  # labels
    autotexts: VGroup | None  # percentages

    def set_data(self, x) -> Self: ...


# on CartesianAxes (2D)
def boxplot(
    self,
    x,
    positions=None,
    *,
    widths=0.5,
    whis=1.5,
    orientation="vertical",
    showmeans=False,
    showfliers=True,
    tick_labels=None,
    **style,
) -> BoxPlot: ...
def violinplot(
    self,
    dataset,
    positions=None,
    *,
    widths=0.5,
    orientation="vertical",
    showmeans=False,
    showextrema=True,
    showmedians=False,
    points=100,
    bw_method=None,
    **style,
) -> ViolinPlot: ...


class BoxPlot(VGroup):  # mp.BoxPlot: lists, one item per dataset
    boxes, medians, whiskers, caps, fliers, means
    stats: list[dict]  # q1, med, q3, whislo, whishi, mean, fliers per dataset


class ViolinPlot(VGroup):  # mp.ViolinPlot
    bodies, cbars, cmins, cmaxes, cmeans, cmedians
```

## PI — `PieChart`

| ID | Row |
|---|---|
| PI-1 | Matplotlib's geometry in scene units: with `normalize=True` wedge `i` spans the fraction `x_i / Σx` of the full turn, the first starting at `startangle` degrees from +x, the next following counterclockwise (`counterclock=False`: clockwise). With `normalize=False` and `Σx < 1` the fractions are the values themselves (a partial pie); `Σx > 1` raises `ValueError` naming `normalize`. Negative values raise `ValueError`. Each wedge is a Manim `Sector` of `radius` about `center` |
| PI-2 | `explode[i]` moves wedge `i` by `explode[i] · radius` along its middle angle. `labels[i]` is a `Text` (font size 24) at `labeldistance · radius` along the middle angle (from the moved centre), aligned as matplotlib's: its left edge on that point when the middle angle points right (`cos ≥ 0`), its right edge when it points left, centred vertically *(review: centred labels overlapped their wedges)*; `autopct` (a `%`-style format as matplotlib's, `"%1.1f%%"`, or a callable of the percentage) gives `autotexts[i]` (font size 24) centred at `pctdistance · radius`, dark (`BLACK`) on a wedge whose relative luminance is at least 0.5 and light (`WHITE`) otherwise (HM-6's rule) unless `text_config` sets a colour *(review: white on a white wedge)*. `texts`/`autotexts` are `None` when not asked for |
| PI-3 | Style: wedges take `colors[i]` or the cycle (`COLOR_CYCLE` from its start), `fill_opacity=1`, stroke of the background colour width 2 *(default taken)*; `wedge_config` and `text_config` pass Manim style; each wedge and text is its own mobject, styled on its own |
| PI-4 | `pie.set_data(x)` re-derives the same wedges and texts in place (same count; styles kept); under `.animate` the fractions interpolate, so wedges sweep (task 34's data animation) |

## BX — `boxplot`

| ID | Row |
|---|---|
| BX-1 | Statistics are matplotlib's `boxplot_stats`: quartiles by `numpy.percentile` (linear), `IQR = q3 − q1`, whiskers at the most extreme data within `[q1 − whis·IQR, q3 + whis·IQR]` (`whis` a pair: the percentiles to reach), fliers the data beyond; `plot.stats[i]` holds `q1, med, q3, whislo, whishi, mean, fliers` |
| BX-2 | Drawing of dataset `i` at `positions[i]` (default `1 … n`) with width `w = widths[i]` (a scalar for all): the box a closed rectangle from `q1` to `q3` across `pos ± w/2`; the median a line across the box at `med`; two whiskers from the box ends to `whislo`/`whishi` at `pos`; two caps across `pos ± w/4` at the whisker ends (whiskers and caps two per dataset in `plot.whiskers`/`plot.caps`, low then high, matplotlib's order); fliers as scatter markers at `(pos, value)`; `showmeans` a marker at the mean. A dataset with no fliers gets an empty fliers part, with no warning *(review: the empty scatter warned)*. `orientation="horizontal"` exchanges x and y. All bound artists: they follow ranges and moves and are cut to the viewport |
| BX-3 | Default style: the box with no fill and stroke of the cycle's next colour, the median line in the next colour after it *(matplotlib's orange median)*, whiskers and caps as the box, fliers hollow circles *(default taken)*; `**style` applies to the boxes; each part is addressable (`plot.medians[i]`) and styleable. `tick_labels` makes the axis categorical (CA-1) with the datasets at the categories' positions |

## VI — `violinplot`

| ID | Row |
|---|---|
| VI-1 | Density of dataset `i` by a Gaussian KDE: bandwidth `bw = factor · std(ddof=1)`, `factor = n^(−1/5)` (Scott's, the default), or `bw_method` a scalar factor or a callable of the data returning one; evaluated at `points` values evenly spaced from the data's minimum to its maximum |
| VI-2 | Body `i` is a closed filled region whose half-width at value `y` is `0.5 · widths[i] · kde(y) / max(kde)` on each side of `positions[i]` (default `1 … n`); `cbars` a line from minimum to maximum at the position; `cmins`/`cmaxes` lines across `pos ± widths/4` at the extremes (`showextrema`); `cmeans`/`cmedians` likewise at the mean/median when asked. Horizontal orientation exchanges x and y. Bound and cut as BX-2 |
| VI-3 | Default style: bodies the cycle's next colour at `fill_opacity=0.3` with a stroke of width 1 in that colour, the lines in the same colour *(default taken)*; each part addressable and styleable |

## Frame cost

Readings (p95 of `update`, ms) for the report: five box plots and five violins of 1 000
points each under an animated range. F-1001 is unchanged.
