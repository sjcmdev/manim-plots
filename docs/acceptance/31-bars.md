# Acceptance table — task 31, bars and categorical axes

**Status: Living until task 31 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1-§2; ADR 0004 §9 (customisation); task 11a
(artists: cycle, legend, clip, keys); task 25 (`ColorMapping`, `colorbar`); task 29
(VS-1: `c=` on scatter, the same rule here).

Modules: `mobjects/bars.py` (new: `BarPlot`, `GroupedBarPlot`, `BarChart`, `bar_label`),
`mobjects/axis.py` (categories), `mobjects/system.py` (the methods),
`src/manim_plots/__init__.py`.

```python
class BarChart(CartesianAxes):  # mp.BarChart, an attribute only (Manim's name)
    def __init__(self, values, bar_names=None, y_range=None, x_length=None,
                 y_length=None, bar_colors=[...Manim's five...], bar_width=0.6,
                 bar_fill_opacity=0.7, bar_stroke_width=3, **kwargs): ...
    bars: BarPlot
    x_labels: VGroup | None
    def get_bar_labels(self, color=None, font_size=24, buff=MED_SMALL_BUFF,
                       label_constructor=Tex) -> VGroup: ...
    def change_bar_values(self, values, update_colors=True) -> None: ...

# on CartesianAxes
def bar(self, x, height, width=0.8, bottom=0, *, align="center", color=None, c=None,
        colorscale=None, vmin=None, vmax=None, norm=None, label=None, **style) -> BarPlot: ...
def barh(self, y, width, height=0.8, left=0, *, align="center", **same) -> BarPlot: ...
def grouped_bar(self, heights, positions=None, *, tick_labels=None, labels=None,
                group_spacing=1.5, bar_spacing=0, orientation="vertical", colors=None,
                **style) -> GroupedBarPlot: ...
def bar_label(self, container, labels=None, *, fmt="{:g}", label_type="edge",
              padding=0.1, **text_style) -> VGroup: ...

# on Axis
categories: tuple[str, ...]
def set_categories(self, names) -> Self: ...
```

## BC — Manim's `BarChart`

| ID | Row |
|---|---|
| BC-1 | `mp.BarChart` keeps Manim's signature and defaults (`x_range = [0, n, 1]`, the default `y_range` from the values, `y_length = frame_height − 4`, `x_length = min(n, frame_width − 2)`, no tips, `Tex` x labels at size 24, y numbers). On those defaults every bar's points equal Manim's `BarChart`'s within `1e-9`, its fill colour is Manim's gradient over `bar_colors`, and the bar names sit as Manim puts them (below the axis, above it for a negative value) |
| BC-2 | `chart.bars` is a `BarPlot` (BA rows): bar `i` from `(i + 0.5 − bar_width / 2, 0)` to `(i + 0.5 + bar_width / 2, values[i])` in data, so it follows ranges and moves as every artist; `chart.bars.at(name)` reaches a bar by its name when names are given |
| BC-3 | `get_bar_labels(...)` keeps Manim's signature, text (`str(value)`), colour rule and placement (`next_to` the bar's top, the bottom for a negative value, `buff`); the labels follow the bars when values or ranges change |
| BC-4 | `change_bar_values(values, update_colors=True)` rewrites the bars in place (the same mobjects, so a user style stays) from the new values; `chart.animate.change_bar_values(values)` interpolates the values, so every frame shows the bars of the interpolated values. Manim defect fixed: Manim's leaves a bar of value 0 at 0 forever (it scales by `new / old`); here it grows |

## BA — `bar` and `barh` (matplotlib's)

| ID | Row |
|---|---|
| BA-1 | `ax.bar(x, height, width=0.8, bottom=0, align="center")`: bar `i` is the rectangle from `(x − w/2, bottom)` to `(x + w/2, bottom + height)` in data (`align="edge"`: `x` to `x + w`), its four corners mapped by the system and joined straight; scalars broadcast; a negative height goes down from `bottom`. Returns a `BarPlot`; `bars[i]` is the rectangle of point `i`, `bars.at(key)` reaches it by its category name or its `x` |
| BA-2 | `ax.barh(y, width, height=0.8, left=0)` is the same turned: from `(left, y − h/2)` to `(left + width, y + h/2)` |
| BA-3 | Stacking is matplotlib's: `bottom=` (`left=` for `barh`) an array, so `ax.bar(x, b, bottom=a)` sits on `ax.bar(x, a)` |
| BA-4 | Colour: uncoloured, every bar takes one colour, the next of the cycle (matplotlib's); `color=` one colour or one per bar; `c=` values (one per bar) or `c="height"` colour each bar through a `ColorMapping` (CS-1's forms for `colorscale`, default `"viridis"`; `vmin`, `vmax` default the values' extremes; `norm`), exposed as `bars.color_mapping`, so `ax.colorbar(bars)` works. Fill opacity 1, no stroke *(default taken)*; `stroke_width`, `stroke_color` style the edges |
| BA-5 | Bars are bound: they follow ranges (animated), moves and `set_data(x=…, height=…, bottom=…)` (rewritten in place); clipped to the viewport by the artists' rule (a bar crossing the edge is cut there); on a log axis a `bottom ≤ 0` starts at the viewport's edge on that side |
| BA-6 | Customisation: each bar takes its own style, kept through re-derivation; `label=` gives one legend entry, a filled square in the bars' colour |
| BA-7 | `ax.bar_label(bars, labels=None, fmt="{:g}", label_type="edge", padding=0.1)` (matplotlib's): one `Text` per bar, `fmt.format(height)` or `labels[i]`, at the bar's far end outside it by `padding` scene units (`"center"`: at its centre); bound to the bars (it follows heights, ranges, moves) |

## GB — grouped bars (matplotlib 3.11's `grouped_bar`)

| ID | Row |
|---|---|
| GB-1 | `ax.grouped_bar(heights, positions=None, group_spacing=1.5, bar_spacing=0)`: `heights` a list of `m` datasets of `n` values each, or a dict `{label: values}`; group `k` is centred on `positions[k]` (default `k`). With `d` the distance between adjacent positions (1 by default), every bar has width `w = d / (m + (m − 1) · bar_spacing + group_spacing)`, and bar `j` of group `k` is centred at `positions[k] − W/2 + w/2 + j · w · (1 + bar_spacing)`, `W = m · w + (m − 1) · bar_spacing · w` |
| GB-2 | A `GroupedBarPlot` whose `bar_plots[j]` is the `BarPlot` of dataset `j`, labelled by `labels[j]` or the dict's key, coloured by `colors[j]` or the next colour of the cycle; `tick_labels` makes the axis categorical with those names at the positions; `orientation="horizontal"` uses `barh` |

## CA — categorical axes

| ID | Row |
|---|---|
| CA-1 | Strings as `x` in `bar` (`y` in `barh`, either in `grouped_bar`'s `tick_labels`) make that axis categorical: category `k`, in order of first appearance, sits at position `k`; the axis's ticks are exactly the positions, its numbers the names (`Tex`, the axis's number size), no minor ticks |
| CA-2 | The first categorical call sets the axis range to `(−0.5, n − 0.5)` with step 1; new names in a later call append and extend it. `ax.x.set_categories(names)` fixes the list (later unknown names raise `ValueError` naming `x`); `ax.x.categories` reads it |
| CA-3 | On a categorical axis every artist's string coordinates map through the same table (`ax.scatter(["a", "c"], [1, 2])`), numbers pass through, and `c2p("b", 0)` works |
| CA-4 | When an axis first becomes categorical, the other axis moves to its low border (`ax.y.set_position("left")` for a categorical x, `ax.x.set_position("bottom")` for a categorical y), so no axis line runs through the first category's bars; a position the user set earlier is kept *(default taken, found in review: the x axis crossed the middle of the first `barh` bar)* |

## Frame cost

Readings (p95 of `update`, ms) for the report: 100 bars under an animated y range; a
`BarChart` of 20 bars under `animate.change_bar_values`. F-1001 is unchanged.
