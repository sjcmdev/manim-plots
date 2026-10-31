# Acceptance table — task 32, histograms in 2D, `step`, `stairs`, `stackplot`

**Status: Living until task 32 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1-§2 (coloured histograms asked for by
name); task 31 (`BarPlot`, BA rows, categorical axes); task 17 (`fill_between`); task 25
(`ColorMapping`).

Modules: `mobjects/histograms.py` (new: `HistPlot`, `StackPlot`), `mobjects/system.py`
(the methods), `src/manim_plots/__init__.py`.

```python
# on CartesianAxes
def hist(
    self,
    x,
    bins=10,
    *,
    range=None,
    density=False,
    weights=None,
    cumulative=False,
    bottom=None,
    histtype="bar",
    align="mid",
    orientation="vertical",
    rwidth=None,
    stacked=False,
    color=None,
    color_by=None,
    colorscale=None,
    vmin=None,
    vmax=None,
    norm=None,
    label=None,
    **style,
) -> HistPlot: ...
def step(self, x, y, *, where="pre", **kwargs) -> LinePlot: ...
def stairs(
    self, values, edges=None, *, baseline=0, fill=False, orientation="vertical", **style
) -> LinePlot | FilledRegion: ...
def stackplot(
    self, x, *ys, labels=(), colors=None, baseline="zero", **style
) -> StackPlot: ...


class HistPlot(VGroup):  # mp.HistPlot
    counts: ndarray  # (n_bins,) or (n_datasets, n_bins)
    edges: ndarray
    bars: BarPlot | list[BarPlot] | None  # histtype "bar" / "barstacked"
    outlines: list[LinePlot | FilledRegion]  # histtype "step" / "stepfilled"
    color_mapping: ColorMapping | None

    def set_data(self, x, *, bins=None, weights=None) -> Self: ...
```

## HI — `hist`

| ID | Row |
|---|---|
| HI-1 | Counting is `numpy.histogram`'s: `bins` an int, a sequence of edges, or a rule name (`numpy.histogram_bin_edges`), `range`, `weights`, `density` (each dataset integrates to 1); `cumulative=True` sums from the left, `-1` from the right. `plot.counts` and `plot.edges` hold the result |
| HI-2 | `histtype="bar"`: bin `b` of a single dataset is a `BarPlot` bar from `edges[b]` to `edges[b + 1]` scaled by `rwidth` about its centre (`rwidth=None` gives 1, the bars touch), from `bottom` (0) to the count; `align="left"`/`"right"` shift the bars by half a bin |
| HI-3 | Several datasets (`x` a list of arrays, or a 2D array by columns), `histtype="bar"`, not stacked: matplotlib's side-by-side rule: `dr = rwidth` or 0.8, each dataset's bar width `dr · w / n` (`w` the bin width), dataset `k`'s bar centred at `edges[b] + w/2 − dr·w/2·(1 − 1/n) + k · dr·w/n`; each dataset the next colour of the cycle. `stacked=True` (or `histtype="barstacked"`) stacks them: dataset `k` starts on the sum of the earlier ones |
| HI-4 | `histtype="step"`: one `LinePlot` outline per dataset through `(e0, base), (e0, c0), (e1, c0), (e1, c1), …, (e_n, c_{n−1}), (e_n, base)`; `"stepfilled"`: the same closed and filled (`fill_opacity=1`, no stroke) *(matplotlib's)* |
| HI-5 | **Colour by value.** `color_by="count"` colours each bar through a `ColorMapping` of its count (`vmin`, `vmax` default the counts' extremes); `color_by="x"` by its bin centre, `vmin`, `vmax` defaulting to the first and last edge — the spectrum histogram; `colorscale` takes CS-1's forms (default `"viridis"`), `norm` as CS-1; `plot.color_mapping` makes `ax.colorbar(plot)` work. Without it: the cycle's next colour (or `color`) for all bars of a dataset. Only for `histtype="bar"`; with `"step"` it raises `ValueError` naming `color_by` |
| HI-6 | `orientation="horizontal"` draws the same with `barh` and the outlines turned |
| HI-7 | `plot.set_data(x)` re-counts into the same edges and rewrites the bars in place (same mobjects, styles kept, colours re-mapped); `set_data(x, bins=…)` re-bins (bars are added or removed at the end). Bound to ranges and moves; clipped as bars (BA-5); `label=` gives one legend entry per dataset |

## SP — `step`, `stairs`, `stackplot`

| ID | Row |
|---|---|
| SP-1 | `ax.step(x, y, where="pre")` is a `LinePlot` through matplotlib's vertices: `"pre"` `(x0, y0), (x0, y1), (x1, y1), (x1, y2), …`; `"post"` `(x0, y0), (x1, y0), (x1, y1), (x2, y1), …`; `"mid"` steps at the midpoints between the `x`. Any other `where` raises `ValueError` naming `where` |
| SP-2 | `ax.stairs(values, edges)` (edges default `0 … n`) draws the steps `(e_i, v_i)–(e_{i+1}, v_i)` joined by verticals, down to `baseline` at both ends; `fill=True` closes and fills it to the baseline; `orientation="horizontal"` swaps the axes |
| SP-3 | `ax.stackplot(x, y0, y1, …)` is a `StackPlot` of one `fill_between` region per series, region `k` between the cumulative sums `Σ_{j<k} y_j` and `Σ_{j≤k} y_j` (baseline `"zero"`), `"sym"` centring the stack on 0 (matplotlib's); each region the next colour of the cycle or `colors[k]`, labelled `labels[k]`; `stack.regions[k]` |

## Frame cost

Readings (p95 of `update`, ms) for the report: a 50-bin histogram re-counted every frame
from 10 000 samples (`set_data` in an updater); a 3-dataset stacked histogram under an
animated range. F-1001 is unchanged.
