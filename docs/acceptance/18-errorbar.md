# Acceptance table — task 18, error bars

**Status: Living until task 18 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §2 (error bars in x and y), §5 (matplotlib's
names), §9 (customisation); `docs/scope.md` F-104, F-114, F-202, F-311, F-705, F-706
(clipping per axis), F-711, F-801, F-805, F-908. Builds on tasks 06-17.

Modules: `src/manim_plots/mobjects/artists.py` (or a new `mobjects/errorbar.py`),
`mobjects/system.py`, `mobjects/legend.py` (the handle).

```python
class ErrorBars(VGroup):  # mp.ErrorBars, star-exported
    markers: ScatterPlot | None
    line: LinePlot | None
    ybars: Leaf | None  # one artist, one segment per point
    xbars: Leaf | None
    ycaps: Leaf | None
    xcaps: Leaf | None

    def set_data(self, x, y, yerr=None, xerr=None) -> Self: ...
    def get_label(self) -> str | None: ...
    def set_label(self, label: str | None) -> Self: ...
    def set_clip(self, value) -> Self: ...
    def get_clip(self): ...


class CartesianAxes:
    def errorbar(
        self,
        x,
        y,
        yerr=None,
        xerr=None,
        *,
        marker=Marker.DOT,
        line=False,
        ecolor=None,
        elinewidth=None,
        capsize=0.1,
        capthick=None,
        barsabove=False,
        errorevery=1,
        label=None,
        clip=True,
        **style,
    ) -> ErrorBars: ...
```

## EB — the artist (F-711, ADR 0004 §5)

| ID | Row |
|---|---|
| EB-1 | `ax.errorbar(x, y, yerr=None, xerr=None, ...)` registers an `ErrorBars`, matplotlib's name and meaning. `x` and `y` are one-dimensional arrays of one length `n`, or `x` a sequence of `(x, y)` pairs with `y` omitted, as `ax.line` takes them (F-703) |
| EB-2 | `yerr` and `xerr` are each `None`, a scalar, an array of `n` values, or an array of shape `(2, n)`: the lower and the upper error. The bar of point `i` runs from `y[i] - lower[i]` to `y[i] + upper[i]` in data (the same in x). A negative error raises `ValueError` naming `yerr` or `xerr`, as matplotlib does; a `NaN` error, a `NaN` coordinate or a non-finite point draws no bar for that point and warns once per data change (F-705's rule) |
| EB-3 | Bars are segments in data space mapped like a plot, so they are correct on log scales, reversed ranges, rotated axes and a warped frame. On a log scale, an end that leaves the domain (`y - lower <= 0`) runs to the viewport's edge on that side, never `NaN`, and that end has no cap |
| EB-4 | Caps are perpendicular to their bar, `capsize` long in scene units *(default taken: 0.1; matplotlib's default is no caps)*, centred on each bar end, drawn in scene units so they keep their size when the axes zoom. `capsize=0` draws none |
| EB-5 | Parts and customisation (ADR 0004 §9): `markers` is a `ScatterPlot` with `marker` (a `Marker`, a `Mobject` or `None` for none) and the call's `style`; `line` is a `LinePlot` through the points when `line=True`, else `None`; `ybars`, `xbars`, `ycaps`, `xcaps` are each one artist holding one segment per point, or `None` when that error is `None`. `ecolor` (default: the markers' colour), `elinewidth` (default 2) and `capthick` (default `elinewidth`) style the bars and caps; each part can also be styled on its own afterwards and keeps that style through `set_data`. `barsabove` puts the bars above the markers in the family order. `errorevery=k` or `(start, k)` draws the bars of every `k`-th point from `start`, as matplotlib's |
| EB-6 | Colour: an uncoloured `errorbar` takes the next colour of the system's cycle for the markers, the line and, through `ecolor`'s default, the bars (F-803) |
| EB-7 | Clipping (F-706, task 15): `clip` takes a bool, a margin or a pair, applied to the markers as to a scatter and to the line, bars and caps as to a line; `set_clip` and `get_clip` as on the artists |

## ED — data changes (F-104, F-908)

| ID | Row |
|---|---|
| ED-1 | `eb.set_data(x, y, yerr=None, xerr=None)` replaces the data, immutably (F-104), and re-derives every part; an error given as `None` keeps no bar of that kind. It validates as EB-1 and EB-2 and returns the artist |
| ED-2 | Under `.animate`, `eb.animate.set_data(...)` with the same `n` interpolates points and errors by index, so each bar moves and stretches to its new place; with a different `n` it raises `ValueError` naming `set_data`, and outside an animation any `n` is accepted *(default taken)* |
| ED-3 | The artist follows the system as every artist does: a changed range, `ax.animate.set_x_range`, a shift, a rotation |

## EL — the legend (F-801, F-802)

| ID | Row |
|---|---|
| EL-1 | With `label=`, `ax.legend()` shows one entry for the `ErrorBars`, whose handle is its marker with a vertical bar through it in the bars' style (and a short line when `line=True`) |

## Tests

`tests/mobjects/test_errorbar.py`:

- EB: both input shapes; every error shape against bar ends from `c2p`; the
  negative-error errors; a `NaN` error drawing no bar and warning; log axes with a lower
  end below 0 reaching the viewport's edge and no cap there; caps perpendicular on
  rotated axes and `capsize` long in scene units, the same after `ax.scale(2)`; the
  parts present or `None`; `ecolor`, `elinewidth`, `capthick`, `barsabove`, `errorevery`;
  the cycle; clipping per axis.
- ED: `set_data`, an animated `set_data` with intermediate frames between the two states,
  the different-`n` error under `.animate`, following `ax.animate.set_x_range`.
- EL: the handle's parts.
- Visual: `test_errorbars_in_x_and_y`, a picture with symmetric and asymmetric errors in
  both directions on linear axes beside the same data on a log y axis, and its
  `__manim` twin drawn by hand with `Line`s on Manim's `Axes` for the linear half.
- A frame-cost reading: 200 points with errors in x and y under `ax.animate.set_x_range`
  on F-1001's axes, recorded here, not gated.

## Frame-cost reading

2026-10-29, Codex's run: 200 points with x and y errors under `ax.animate.set_x_range` on
F-1001's decorated axes, Manim 0.21, 1080p60: `update` p95 36.7 ms, frame p95 61.8 ms.
The family holds 206 mobjects: the four bar and cap families are one leaf each, and the
cost is the scatter's 200 marker leaves, as for `ax.scatter` alone. For task 23's
performance pass.
