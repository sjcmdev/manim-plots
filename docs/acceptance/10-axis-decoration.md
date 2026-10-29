# Acceptance table — task 10, axis decoration

**Status: Living until task 10 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-203-F-206, F-408, F-411-F-413,
F-505-F-508, F-601-F-609, F-921, F-1009 and both defaults tables; ADR 0003 §6-§8;
`docs/parity-survey.md` section 1 (the 0.1 Manim names). Builds on task 09's
`CartesianAxes`, `Axis` and leaves.

Modules: `src/manim_plots/mobjects/axis.py`, `mobjects/system.py`, `mobjects/leaves.py`
(label leaves).

The table has two parts, implemented in two passes: **A — Manim's surface** (what
`Axes(...)` and `NumberPlane(...)` accept and draw, compared with Manim's own objects in
the same test) and **B — the library's own capabilities** (locators, parts, direction,
position, mirror, grid, overlap, aspect).

## Part A — Manim's surface

### AC — the constructor

```python
class CartesianAxes(VGroup):
    def __init__(
        self,
        x_range=None,
        y_range=None,
        x_length=None,
        y_length=None,
        axis_config=None,
        x_axis_config=None,
        y_axis_config=None,
        tips=True,
        *,
        x_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        y_scale: Scale | Literal["linear", "log", "symlog"] = "linear",
        aspect: float | None = None,
        adjustable: Literal["length", "range"] = "length",
        **kwargs,  # VGroup's, as in Manim
    ) -> None: ...
```

| ID | Row |
|---|---|
| AC-1 | Manim's signature and merge order: `axis_config` applies to both axes, then `x_axis_config` / `y_axis_config` override it, merged recursively (Manim's `merge_dicts_recursively`); `tips` is `axis_config`'s default `include_tip` |
| AC-2 | The honoured `axis_config` keys are exactly the defaults table's: `include_numbers`, `numbers_to_include`, `numbers_to_exclude`, `decimal_number_config`, `font_size`, `include_ticks`, `tick_size`, `longer_tick_multiple`, `numbers_with_elongated_ticks`, `exclude_origin_tick`, `include_tip`, `tip_shape`, `tip_width`, `tip_height`, `label_direction`, `line_to_number_buff`, `unit_size`, `scaling`, `stroke_width`, `color`. Any other key raises `ValueError` naming it (F-1009) |
| AC-3 | Defaults (D23): ranges when omitted from the frame radius **at construction**, rounded, as Manim does; lengths when omitted `round(frame_width) - 2` and `round(frame_height) - 2` **at import**, as Manim's signature evaluates them — so under a changed `tempconfig` the ranges follow and the lengths do not, exactly like Manim *(default taken: parity with Manim's quirk)* |
| AC-4 | Every row of the `Axes` defaults table holds against Manim's `Axes` built with the same arguments in the same test: lines, ticks, tips and numbers have Manim's points (within `1e-6`) and style (stroke colour, width, opacity; fill colour, opacity); a tick and a number where the axes cross are absent; the tick under a tip is kept (the fix); the midpoint of each range sits at the scene origin; the y axis is turned by 90°. Cases: the default; `include_numbers=True`; `x_range=(0, 10, 2)` with numbers; `decimal_number_config={"num_decimal_places": 2}`; `font_size=24`; `label_direction=UP`; `tick_size=0.2`; `numbers_with_elongated_ticks=[2]`; `include_ticks=False`; `numbers_to_include=[1, 3]`; `numbers_to_exclude=[2]`; `stroke_width=4`; `color=RED`; `tips=False`; each also under `tempconfig({"frame_width": 10, "frame_height": 6})` for the default |
| AC-5 | Numbers (F-603's `numbers`): `axis.numbers` is a `VGroup` of one `NumberLabel` per labelled tick, in axis order, each a `VGroup` of library glyph leaves, one leaf per glyph, placed as Manim's `DecimalNumber` places them: equal glyph outlines and centres within `1e-6` of Manim's `NumberLine.numbers` for the cases of AC-4. The cache compiles each glyph once per font size and colour-free outline (ADR 0001 §3) |
| AC-6 | Decimal places follow ADR 0003 §7: Manim's rule from the step, except that a step printed in scientific notation counts its exponent (`decimal_places` of task 08) |
| AC-7 | `unit_size` in `axis_config` without the axis's length wins over the default length; with an explicit length it raises `ValueError` naming both (F-204, ADR 0003 §6) |
| AC-8 | `axis_config={"scaling": LogBase()}` keeps Manim's meaning (D23): the range is in exponents (`x_range=[-2, 6]` spans 10⁻² to 10⁶), `c2p(100, y)` equals Manim's, ticks sit at the decades Manim draws (plus the one under a tip), and `LogBase(custom_labels=True)` gives `10^{k}` labels as Manim's do. `p2c` inverts `c2p` (defect 15c fixed): it equals Manim 0.22.0's and differs from 0.21.0's only by that fix |
| AC-9 | `x_scale="log"` (or a `Scale`) takes **data** ranges: `CartesianAxes(x_range=(0.1, 1000), x_scale="log")` spans 0.1 to 1000, with `LogLocator` major ticks and `LogLocator(subs=range(2, 10))` minor ticks by default (defect 9) *(default taken)*; `"symlog"` installs `SymLogScale()` and `SymLogLocator()`. A range leaving the scale's domain is normalised by `limit_range` with `MINPOS_UNKNOWN` (F-311); one wholly outside raises |
| AC-10 | `aspect=r` locks the ratio of a y unit to an x unit in scene length (F-205). `adjustable="length"` keeps the ranges and adapts the length that was not given; `adjustable="range"` keeps both lengths and widens one range about its midpoint. Both lengths given with `adjustable="length"`, or `adjustable` other than the two, raise `ValueError` (ADR 0003 §6) |

### HM — Manim's helper methods (F-1009, the parity survey's 0.1 rows)

| ID | Row |
|---|---|
| HM-1 | `coords_to_point`, `point_to_coords`, `get_origin` (no `_origin_shift` clamp beyond Manim's default placement, defect 13), `get_x_unit_size`, `get_y_unit_size`, `get_axes`, `get_axis(i)`, `get_x_axis`, `get_y_axis` — Manim's values on the cases of AC-4 |
| HM-2 | On an axis: `n2p`/`number_to_point`, `p2n`/`point_to_number` (arrays in and out, as 0.22.0's signature; `p2n` inverts `n2p` on every scale), `get_unit_size`, `get_unit_vector`, `rotate_about_number`, `rotate_about_zero`, `get_tick(x)`, `get_tick_marks()`, `get_tick_range()` (the locator's values, no `np.arange` drift), `get_number_mobject(x)`, `get_number_mobjects(*xs)`, `add_numbers(...)`, `add_ticks()`, `add_labels(dict)` (strings in text mode, D23), `get_labels()` |
| HM-3 | `add_coordinates(*axes_numbers)` — Manim's arguments (iterables or `{value: label}` dicts per axis); `get_axis_labels(x_label="x", y_label="y")`, `get_x_axis_label(...)`, `get_y_axis_label(...)` — Manim's positions within `1e-6` (F-609) — and `get_graph_label(graph, label, x_val, direction, buff, color, dot, dot_config)`; each returns decorations **bound** to the system: they follow `ax.shift`, `ax.rotate` and, for a graph label, the graph's range changes (F-609, D27) |
| HM-4 | An unknown attribute on a library mobject raises `AttributeError` (Manim's `get_`/`set_` shim is not offered on library types, ADR 0003 §7); Manim's own `get_x`, `set_color` and the rest keep working |

### NP — `mp.NumberPlane` (F-921, the `NumberPlane` defaults table)

```python
class NumberPlane(CartesianAxes):  # mp.NumberPlane; not star-exported
    def __init__(
        self,
        x_range=None,
        y_range=None,
        x_length=None,
        y_length=None,
        background_line_style=None,
        faded_line_style=None,
        faded_line_ratio=1,
        make_smooth_after_applying_functions=True,
        **kwargs,
    ) -> None: ...
```

| ID | Row |
|---|---|
| NP-1 | Manim's signature and defaults: ranges from the frame radius (unrounded, `(-frame_x_radius, frame_x_radius, 1)`), lengths from a unit size of 1, axes of `stroke_width=2` without ticks or tips, numbers at `font_size=24` with `label_direction=DR` and `line_to_number_buff=SMALL_BUFF` when asked, background lines `BLUE_D` at width 2 and opacity 1, faded lines from `faded_line_ratio` with a faded copy of the background style |
| NP-2 | The background lines and faded lines equal Manim's `NumberPlane`'s, line by line (points within `1e-6`, style equal), for the default, `x_range=(-3, 3, 0.5)`, `faded_line_ratio=2`, and a custom `background_line_style` |
| NP-3 | The background lines are the major grid and the faded lines the minor grid (`MinorCountLocator(n=faded_line_ratio - 1)`) of the two axes (`ax.x_axis.grid`, `ax.y_axis.grid`, DP-5); a range change regenerates them |

## Part B — the library's own capabilities

```python
class TickDirection(Enum):
    IN = "in"
    OUT = "out"
    BOTH = "both"


class Axis(VGroup):
    line
    ticks
    minor_ticks
    numbers
    labels
    grid
    tip
    tip_start
    range: Param
    locator: Locator
    minor_locator: Locator | None
    formatter: Formatter

    def set_locator(self, locator, minor=None) -> Self: ...
    def set_formatter(self, formatter) -> Self: ...
    def set_ticks(self, entries, mode="replace") -> Self: ...
    def set_tick_style(
        self, level="major", *, direction=None, length=None, width=None, color=None
    ) -> Self: ...
    def set_position(self, where="origin", *, fraction=None) -> Self: ...
    def set_tips(self, start=False, end=True) -> Self: ...
    def set_grid(self, level="major", visible=True, **style) -> Self: ...
    def set_label_style(
        self, *, rotation=0.0, offset=(0, 0), justify="center", overlap="hide"
    ) -> Self: ...
    def mirror(self) -> Axis: ...
```

### LB — locators, formatters, parts (F-406, F-412, F-413, F-507, F-603)

| ID | Row |
|---|---|
| LB-1 | `set_locator(locator, minor=None)` takes any `Locator` or plain callable (`as_locator`, task 08); `set_formatter` any `Formatter` or callable (`as_formatter`); `set_ticks(entries, mode)` is sugar over `FixedLocator` with `axis_ticks`' modes (F-406, F-405). Each regenerates the affected parts and nothing else (F-412) |
| LB-2 | Every part is addressable by value: `ax.x_axis.ticks.at(v)`, `.minor_ticks.at(v)`, `.numbers.at(v)`, `.grid.at(v)` return the part for the tick whose key is the locator's `key(v)`, or raise `KeyError`; `ax.x_axis.line` is the line (F-603) |
| LB-3 | Identity (F-413, D10): a part keeps its object across a rebuild while its key stays in the range — `ax.x.numbers.at(2.0).set_color(RED)` survives `ax.x.range = ...` that keeps 2 inside; a key that leaves and returns in a later, separate edit gets a fresh object (D10's ceiling) |
| LB-4 | Changing the formatter relabels the same number objects in place (F-507): `numbers.at(v)` is the same object before and after `set_formatter` |
| LB-5 | `max_ticks` (F-408) is the label space: `floor(length / (3 h))` on a horizontal axis and `floor(length / (2 h))` on a vertical one, `h` the height of the digit `0` at the axis's font size — matplotlib's `get_tick_space` factors *(default taken)* |
| LB-6 | A label whose value lies outside the range is never emitted (F-506) |

### DP — direction, position, tips, mirror, grid (F-203, F-604-F-608)

| ID | Row |
|---|---|
| DP-1 | `set_tick_style(level, direction, length, width, color)` per level (F-604): `BOTH` straddles the line (Manim's), `OUT` points away from the plot's interior (below an x axis at the bottom, left of a y axis at the left), `IN` toward it; a minor level defaults to half the major length *(default taken)* |
| DP-2 | `set_position(where, fraction=None)` (F-605, F-203): `"origin"` is Manim's default placement (at the other axis's zero when its range holds zero, else at its range edge), `"bottom"`/`"top"` for an x axis and `"left"`/`"right"` for a y axis put it at that end of the other range, a float puts it at that data value of the other axis, `fraction=f` at that fraction of the other axis's length. The mapping never changes, only the decoration moves |
| DP-3 | `set_tips(start, end)` draws a tip at either end (F-608); neither the mapping nor the tick range changes with a tip (F-411) |
| DP-4 | `mirror()` returns a second, unlabelled decoration of the same axis on the opposite side, bound to the same system and regenerated with it (F-606) |
| DP-5 | `set_grid(level, visible, **style)` draws grid lines across the other axis's range at that level's ticks, styled per level (F-607); hidden by default on `CartesianAxes`. Each grid line is a leaf in `axis.grid` with a `level` attribute, `"major"` or `"minor"`; there is no grid line where the other axis's line is |

### LL — label layout (F-505, F-508)

| ID | Row |
|---|---|
| LL-1 | Overlap (F-505), decided on the labels' bounding boxes in scene space after placement: `"hide"` (the default, the defaults table's "the later one hidden") gives each label that overlaps an earlier visible one opacity 0; `"drop"` leaves out every second label until none overlap; `"rotate"` turns every label by 45° and then hides what still overlaps |
| LL-2 | `rotation`, `offset` (in scene units along and across the axis) and `justify` (`"center"`, `"left"`, `"right"` of the label's anchor point at the tick) are parameters (F-508) |

## Benchmark and visual pairs

| ID | Row |
|---|---|
| BM-1 | `tests/benchmark/test_f1001.py` gains the labelled case: the four plots of task 09 with `axis_config={"include_numbers": True}` and `MaxNLocator` majors, the glyph cache warmed by a first play; recorded, not gated (task 13 gates it) |
| VP-1 | Visual pairs with `__manim` twins: numbers on default axes; `x_range=(0, 10, 2), y_range=(-1, 1, 0.25)` with numbers; a `LogBase` x axis with numbers; the default `NumberPlane`. Library-only baselines: a log axis by `x_scale="log"` with minor ticks, `OUT` ticks with the axes at the bottom-left, a mirrored x axis, a major and minor grid, `"rotate"` overlap on a dense axis, an aspect lock |

## Tests

| File | Rows |
|---|---|
| `tests/mobjects/test_defaults.py` | AC-1 … AC-7, AC-9, AC-10 |
| `tests/mobjects/test_log_axes.py` | AC-8, AC-9 |
| `tests/mobjects/test_helpers.py` | HM-1 … HM-4 |
| `tests/mobjects/test_number_plane.py` | NP-1 … NP-3 |
| `tests/mobjects/test_axis.py` | LB-1 … LB-6, DP-1 … DP-5, LL-1, LL-2 |
| `tests/visual/test_axes_pictures.py` | VP-1 |
| `tests/benchmark/test_f1001.py` | BM-1 |
