# Acceptance table — task 34, data animation

**Status: Record (merged 2026-10-31).** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1 (data animation); task 11b (the data
channel under `.animate`, MX rows); task 12 (`DrawAxes`, `TraceCurve`, `ShowPoints`,
`Morph`); tasks 31-33 (bars, histograms, `set_data`); task 37 (heatmaps' `set_data`).

Modules: `mobjects/animations.py` (the animations), `mobjects/bars.py`,
`mobjects/histograms.py`, `mobjects/heatmaps.py`, `mobjects/plots3d.py` (keyed data
interpolation), `mobjects/system.py` (`autoscale`, `margins`),
`src/manim_plots/__init__.py`.

```python
class GrowBars(Animation):    # mp.GrowBars(bars, lag_ratio=0.05, **kwargs)
class ShrinkBars(Animation):  # mp.ShrinkBars(bars, lag_ratio=0.05, **kwargs), a remover
class SortBars(Animation):    # mp.SortBars(bars, key=None, reverse=False, **kwargs)
class AppendData(Animation):  # mp.AppendData(artist, x, y=None, *, autoscale=False, **kwargs)
class BuildAxes(AnimationGroup):  # mp.BuildAxes(ax, lag_ratio=0.5, **kwargs)
class HighlightTick(Animation):   # mp.HighlightTick(axis, value, color=YELLOW, scale_factor=1.5)
class HighlightBar(Animation):    # mp.HighlightBar(bars, key, dim_opacity=0.25)

# on CartesianAxes
def autoscale(self, axis="both", *, tight=False) -> Self: ...
def margins(self, x=None, y=None) -> Self | tuple[float, float]: ...
```

`bars` above is any bar container: a `BarPlot` (task 31), a `HistPlot`'s bars (task 32),
a `BarPlot3D` or `Hist3DPlot` (tasks 29, 33), or a `BarChart`'s `bars`.

## GR — growing and shrinking bars

| ID | Row |
|---|---|
| GR-1 | `mp.GrowBars(bars)` grows every bar from its base: on each frame bar `i`'s far end in data is `base + α_i · (end − base)`, its base and width fixed, with `α_i` the rate function of bar `i`'s window under `lag_ratio` (Manim's `LaggedStart` timing, bars in data order); bars of 3D containers grow along z. It is an introducer (the bars are added to the scene); at the end every bar is its bound self (a later range change re-derives it) and no updater remains |
| GR-2 | `mp.ShrinkBars(bars)` is the reverse and a remover: at the end the bars are removed from the scene and their data is untouched |

## SD — animated data changes by key

| ID | Row |
|---|---|
| SD-1 | `bars.animate.set_data(x=…, height=…)` on a `BarPlot` interpolates by key (the category name or the `x`): a key present before and after moves its height (and position, when its `x` changed) linearly in data with the rate function; a new key grows from its base as GR-1; a key that leaves shrinks to its base and its bar is removed at the end. On every frame each bar equals the bar of the interpolated data, its colour too when it is coloured by value (BA-4's `c="height"` maps the interpolated heights) *(review: the race kept its first colours)* |
| SD-2 | `hist.animate.set_data(x)` (task 32, same edges) interpolates the counts bin by bin; `hist3d.animate.set_data(x, y)` likewise; `heatmap.animate.set_data(C)` (task 37) interpolates the values, so the colours pass through the mapping of the interpolated values (not a colour blend) |
| SD-3 | `chart.animate.change_bar_values(values)` on a `BarChart` is SD-1 on its bars (BC-4) |

## SB — sorting (bar-chart races)

| ID | Row |
|---|---|
| SB-1 | `mp.SortBars(bars, key=None, reverse=False)` moves every bar to its place in the order of `key(height)` (heights by default; ascending, `reverse=True` descending): bar `i` slides along the category axis from its position to its new slot linearly, its height fixed; ties keep their order. On a categorical axis the category names travel with their bars and `ax.x.categories` is the new order at the end; after any number of sorts every bar sits at its category's index in `ax.x.categories` *(review: a second sort placed bars by their original order)* |
| SB-2 | Run after each `set_data` in a `Succession`, it gives a bar-chart race: test scene: three successive data sets, each `set_data` then `SortBars`, ends with the bars sorted by the last data |

## AP — appending data, autoscale and margins

| ID | Row |
|---|---|
| AP-1 | `mp.AppendData(line, x, y)` on a `LinePlot` (or `ScatterPlot`) adds the new points one after another over the run: at α the artist holds its old data plus the first `⌊α · k⌋` new points and a partial segment towards the next (for a scatter: the next marker fading in), so the curve draws on; at the end its data is old + new |
| AP-2 | `ax.margins(x, y)` sets the fractions added on each side when autoscaling (default `0.05` and `0.05`, matplotlib's); `ax.margins()` reads them. `ax.autoscale(axis="both", tight=False)` sets the ranges to the data limits of every registered artist, widened by the margins (`tight=True`: no margins), keeping each axis's step rule; a log axis widens by the margins in log space |
| AP-3 | `mp.AppendData(..., autoscale=True)` changes the ranges on every frame so that the data drawn so far stays inside with the margins, never shrinking them, and the system counts as moving for that play (F-915), so its line, ticks, numbers and grid are redrawn on every frame, not frozen in Cairo's static background *(review: the live-append film kept the start's ticks until the end)*; `ax.animate.autoscale()` animates to the autoscaled ranges as `ax.animate.set_x_range` does |

## AX — building and highlighting

| ID | Row |
|---|---|
| AX-1 | `mp.BuildAxes(ax, lag_ratio=0.5)` draws the system in stages with Manim's `Create`/`FadeIn`: the axis lines, then the ticks, then the numbers, then the axis labels and grid, each stage starting `lag_ratio` into the previous one; at the end every leaf is as before |
| AX-2 | `mp.HighlightTick(axis, value)` is Manim's `Indicate` on the tick at `value` and its number together (colour, `scale_factor`), and leaves them as before; a value with no tick raises `KeyError` |
| AX-3 | `mp.HighlightBar(bars, key)` dims every other bar to `dim_opacity` and indicates bar `key`, then restores every bar's opacity |

## LB — labels that change during a play

| ID | Row |
|---|---|
| LB-1 | A text that is rebuilt while a play runs — `end_label` (task 35), `bar_label` and `get_bar_labels` (task 31), the crosshair readout (task 35), axis numbers and colorbar numbers — leaves no replaced glyph that still has points. Manim takes a play's moving mobjects as a flat list at its start and draws that list every frame, so a glyph swapped out of the family but left with its points draws on as a ghost *(review: the live-append film showed the first value standing still)*. Test: on every frame, no mobject in `scene.moving_mobjects` that is outside the current families of the scene's mobjects has points |

## Frame cost

Readings (p95 of `update`, ms) for the report: `GrowBars` on 100 bars; a 20-bar race
step (`set_data` then `SortBars`); `AppendData` of 500 points with autoscale. F-1001 is
unchanged.
