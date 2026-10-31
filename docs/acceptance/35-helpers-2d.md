# Acceptance table — task 35, 2D helpers

**Status: Living until task 35 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1 (2D helpers); task 16 (HB rows: helpers
are bound artists, number inputs take trackers and callables); task 17 (`FilledRegion`,
FB rows of `fill_between`); task 29 (TX-2: `annotate` in 3D, whose meaning the 2D form
keeps); task 25 (CB-3: placing a system beside another).

Modules: `mobjects/helpers.py` (`annotate`, spans, `fill_betweenx`, crosshair, end
label), `mobjects/inset.py` (new: `InsetAxes`), `mobjects/system.py` (the methods),
`src/manim_plots/__init__.py`.

```python
# on CartesianAxes (2D)
def annotate(
    self, s, xy, xytext=None, *, arrow=True, buff=0.1, arrow_config=None, **text_style
) -> HelperGroup: ...  # .text, .arrow
def axvspan(self, xmin, xmax, ymin=0, ymax=1, **style) -> FilledRegion: ...
def axhspan(self, ymin, ymax, xmin=0, xmax=1, **style) -> FilledRegion: ...
def fill_betweenx(
    self, y, x1, x2=0, *, where=None, interpolate=False, **style
) -> FilledRegion: ...
def crosshair(
    self, x, y=None, *, graph=None, readout=True, fmt="({:.2f}, {:.2f})", **style
) -> HelperGroup:
    ...
    # .vline, .hline, .dot, .readout


def end_label(
    self, graph, label=None, *, fmt="{:.2f}", direction=RIGHT, buff=0.15, **text_style
) -> Mobject: ...
def inset(
    self, bounds, x_range, y_range, *, connectors=True, mirror=(), **axes_kwargs
) -> InsetAxes: ...


class InsetAxes(Axes):  # mp.InsetAxes
    parent: CartesianAxes
    zoom_box: VMobject  # the region on the parent, in its data
    connectors: VGroup  # two lines, empty with connectors=False
    mirrored: list[Mobject]  # the artists of `mirror`, re-plotted on the inset
```

## AN — `annotate` in 2D

| ID | Row |
|---|---|
| AN-1 | `ax.annotate(s, xy, xytext=None)` is a `HelperGroup` of `.text` and `.arrow` (TX-2's meaning in 2D): `s` a string gives `Text(s)` (font size 24, `text_style` passed), a `Mobject` is used as is; the text is centred at the data point `xytext`, or, when omitted, 0.6 scene units right of and 0.6 above `xy` on screen *(default taken, as TX-2)* |
| AN-2 | `.arrow` is Manim's `Arrow` with `buff=0` (styled by `arrow_config`) from the point where the segment from the text's centre to `xy` leaves the text's bounding box, moved `buff` further along the segment, to `xy` itself: its tip on the point. `arrow=False` gives no arrow (`.arrow` is `None`) |
| AN-3 | Bound as task 16's helpers: both follow ranges and moves of the axes; each coordinate of `xy` and `xytext` takes a number, a tracker or a zero-argument callable (HB-2), re-derived on the frames where one changed |

## SPN — spans

| ID | Row |
|---|---|
| SPN-1 | `ax.axvspan(xmin, xmax, ymin=0, ymax=1)` is matplotlib's: a `FilledRegion` rectangle from data `xmin` to `xmax` across, and from the fractions `ymin` to `ymax` of the viewport's height (so the full height by default, following y range changes); `axhspan` is the same turned. Default style: the next cycle colour, `fill_opacity=0.25`, no stroke *(default taken)*; style kwargs override. Bound (HB-2 inputs, ranges, moves) and cut to the viewport like every region |

## FX — `fill_betweenx`

| ID | Row |
|---|---|
| FX-1 | `ax.fill_betweenx(y, x1, x2=0, where=None, interpolate=False)` is task 17's FB rows with the roles of x and y exchanged: the region between the polylines through `(x1, y)` and `(x2, y)`, `where` a mask over `y`; a `FilledRegion` |

## CH — crosshair with a readout

| ID | Row |
|---|---|
| CH-1 | `ax.crosshair(x, y)` (each a number, tracker or callable) or `ax.crosshair(x, graph=g)` (`y = g`'s value at `x`) is a `HelperGroup` of `.vline` (as `axvline(x)`: the full viewport height), `.hline` (as `axhline(y)`), `.dot` (a Manim `Dot` at the point) and `.readout`. Lines default to stroke opacity 0.6 and width 2, dot and lines the axes' foreground colour *(default taken)* |
| CH-2 | `.readout` is `Text(fmt.format(x, y))` (font size 24) placed up-right of the dot (`next_to(dot, UR, buff=0.1)`); when that would leave the axes' box on the right or top it goes to the left or below instead, so it stays inside. Its text is rebuilt only on frames where the formatted string changed; `readout=False` gives `None` |
| CH-3 | Bound: on every frame of an animated tracker the dot is at `c2p(x, y)` of the current values and the lines run through it |

## EL — a label pinned to a curve's end

| ID | Row |
|---|---|
| EL-1 | `ax.end_label(graph)` is a `Text` placed `next_to(graph's last drawn point, direction, buff)`: the last point of its drawn geometry, so it follows `Create`, `TraceCurve`, `AppendData` (task 34), clipping and range changes. With `label=None` it shows `fmt.format(y)` of that point's data y, rebuilt when the string changes; a string or `Mobject` label is fixed. A text label takes the graph's stroke colour unless `text_style` sets one *(default taken; review: the label drew black)*. A graph with no points hides the label (no points) |

## IN — inset axes

| ID | Row |
|---|---|
| IN-1 | `ax.inset((x0, y0, w, h), x_range, y_range)` is an `mp.InsetAxes`, an `Axes` (`axes_kwargs` passed, tips off, no numbers, its x axis at the bottom border and its y axis at the left one by default *(default taken; review: axes through an origin outside the ranges drew away from the box)*) whose box occupies the fractions `(x0, y0, w, h)` of the parent's box (matplotlib's `inset_axes` bounds: lower-left corner and size), kept there when the parent moves or scales |
| IN-2 | `inset.zoom_box` is the rectangle `x_range × y_range` drawn on the parent in its data, following both systems' ranges (an `inset.animate.set_x_range(...)` pans the box); no fill, the foreground colour, stroke width 2 *(default taken)*. The zoom box and the connectors are submobjects of the inset, so adding the inset draws them; mirrored artists are artists of the inset and are added like any artist |
| IN-3 | `inset.connectors` are two lines, each from a corner of the zoom box to the same corner of the inset (lower-left to lower-left, …); of the four same-corner pairs the two drawn are those whose segments cross neither rectangle's interior (matplotlib's `indicate_inset_zoom` picture); they follow both. `connectors=False` leaves the group empty |
| IN-4 | `mirror=[a, b, …]` re-plots each artist on the inset with its data and style: a `FunctionPlot` (same function), a `LinePlot`, `ScatterPlot` or `ParametricPlot` (same data); `inset.mirrored[i]` is the new artist. Any other artist raises `TypeError` naming its class |

## Frame cost

Readings (p95 of `update`, ms) for the report: a crosshair on a tracker along a
function plot; an inset with a mirrored function plot under an animated parent range.
F-1001 is unchanged.
