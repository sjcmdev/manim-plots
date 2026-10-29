# Acceptance table — task 19, twin and multiple axes

**Status: Living until task 19 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §2 (an independent second scale and any
number of further axes), §5 (matplotlib's names), §8 (no tip on a twin's axis), §9
(customisation); `docs/scope.md` F-112, F-605, F-606, F-610 (amended here), F-706, F-801,
F-908, F-914, F-916; `docs/plan.md`, *A coordinate system is one mapping*: a secondary
axis is a second data map sharing the frame. Builds on tasks 06-18.

Modules: `src/manim_plots/mobjects/system.py`, `mobjects/axis.py`,
`mobjects/legend.py`.

```python
class CartesianAxes:
    def twinx(
        self,
        y_range=None,
        *,
        y_scale="linear",
        y_axis_config=None,
        offset=None,
    ) -> CartesianAxes: ...
    def twiny(
        self,
        x_range=None,
        *,
        x_scale="linear",
        x_axis_config=None,
        offset=None,
    ) -> CartesianAxes: ...

    twins: tuple[CartesianAxes, ...]  # in creation order
    parent: CartesianAxes | None  # the system a twin was made from


class Axis:
    def set_position(
        self,
        where="origin",
        *,
        fraction=None,
        offset=None,
    ) -> Self: ...  # offset: scene units outward from a border
```

## TW — twins (F-610, ADR 0004)

| ID | Row |
|---|---|
| TW-1 | `ax.twinx(...)` returns a new `CartesianAxes`, a *twin*, that shares `ax`'s frame and x axis and has its own y axis, matplotlib's name and meaning. `y_range` defaults to `ax`'s y range; `y_scale` takes what the constructor's `y_scale` takes (a scale or `"linear"`, `"log"`, `"symlog"`); `y_axis_config` takes the constructor's `y_axis_config` keys. `ax.twiny(...)` is the same with x and y swapped. A twin of a twin is a twin of the root system: `ax2.twinx()` equals `ax.twinx()` *(default taken)* |
| TW-2 | The twin's own axis is drawn at the opposite border: `twinx`'s on the right, `twiny`'s on the top, ticks and numbers on the outside (the right of a right axis, above a top one), and no arrow tip (ADR 0004 §8). A further twin on the same side is offset outward by `offset` scene units from the previous one, as Origin's `3Ys` and `4Ys` templates place them; `offset=None` is `0.9` *(default taken)*. The shared axis is not drawn again |
| TW-3 | The twin is part of `ax`'s family (its decoration is a submobject of `ax`), so `scene.add(ax)` shows every twin, `Create(ax)` and `DrawAxes(ax)` draw them, and `ax.twins` lists them in creation order; `twin.parent` is `ax` |
| TW-4 | Mapping: `twin.c2p(x, y)` maps `x` through the shared axis and `y` through the twin's own scale and range onto the same rectangle; `p2c` inverts it. `twin.x` is `ax.x` for a `twinx` (the same `Axis`, the same range parameter); `twin.y` is the twin's own |
| TW-5 | Artists bind to their pair: `twin.plot(...)`, `twin.line`, `twin.scatter`, `twin.errorbar`, the helpers of tasks 16-17, all registered with the twin, mapped through its y and the shared x. An artist of one twin is never in another's `artists` (F-112) |
| TW-6 | Following: a shift, rotation, scale or `apply_function` of `ax`, and `ax.animate` of any of them, moves every twin and every twin's artists exactly as `ax`'s (F-914, F-916); geometry on a twin alone raises `ValueError` naming `parent`, because the frame is `ax`'s *(default taken)* |
| TW-7 | Data: `ax.set_x_range(...)` and `ax.animate.set_x_range(...)` move every `twinx` twin's x with it, its artists included, in the same frame; `twin.set_y_range(...)` and `twin.animate.set_y_range(...)` move only that twin. A chained `ax.animate.shift(v).set_x_range(r)` is one animation for every twin (F-909) |
| TW-8 | Clipping per pair falls out of F-112: each artist clips to the shared rectangle through its own system's map, with `clip=(cx, cy)` as on any artist |
| TW-9 | Colour: a twin's uncoloured artists continue `ax`'s colour cycle, so curves on different axes differ without configuration *(default taken)* |
| TW-10 | The legend: `ax.legend()` collects the labelled artists of `ax` and of every twin, in registration order across them *(default taken)*; `twin.legend()` collects only the twin's |
| TW-11 | `copy()` of `ax` copies its twins with their artists' bindings, as a copy of `ax` copies `ax`'s; `Transform(ax, other)` between two systems with the same number of twins pairs the twins in order, and with a different number raises `ValueError` naming `twins` *(default taken)*; `ReplacementTransform(ax, other)` moves each twin's artists to the paired twin |
| TW-12 | Customisation (ADR 0004 §9): a twin's axis takes every `Axis` decoration call (`set_locator`, `set_formatter`, `set_ticks_direction`, `set_tips`, `set_grid`, colours and styles), so `ax2.y_axis.set_color(RED)` colours the axis of a red curve; `get_y_axis_label(...)` on a twin labels its axis on the outside |

## PO — outward positions (F-605)

| ID | Row |
|---|---|
| PO-1 | `axis.set_position("right", offset=d)` (and `"left"`, `"top"`, `"bottom"`) draws the axis `d` scene units outward from that border, beyond the rectangle; `offset` must be finite and `>= 0`, else `ValueError` naming `offset`; with `"origin"` or a data value it raises `ValueError` naming `offset` |
| PO-2 | An outward axis keeps its ticks, numbers and label on its outer side, and its line spans the rectangle's height (width) |

## Tests

`tests/mobjects/test_twin.py`:

- TW-1 to TW-4: the defaults, scales, the twin of a twin, the drawn side, the offsets of
  a second and third twin, `scene.add(ax)` and `Create(ax)` showing them, `c2p` and `p2c`
  through each twin against a hand-computed map.
- TW-5, TW-8, TW-9: artists of each kind on a twin; registration; clipping; the cycle.
- TW-6, TW-7: shift, rotate and `.animate` of `ax`, intermediate frames of
  `ax.animate.set_x_range` with an artist on a twin, a twin's own `set_y_range`, a chain;
  geometry on a twin raising.
- TW-10, TW-11: the legend across twins; copy, `Transform` and `ReplacementTransform`.
- PO: outward positions and their errors.
- Visual: `test_two_y_axes` (a temperature and a pressure curve, Origin's `DOUBLEY`
  layout) and `test_three_y_axes` (Origin's `3Ys_Y-YY`), no Manim twin: Manim has
  neither.
- A frame-cost reading: F-1001's four plots split across `ax` and one twin, under
  `ax.animate.set_x_range`, recorded here, not gated.
