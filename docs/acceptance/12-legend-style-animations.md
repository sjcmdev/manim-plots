# Acceptance table — task 12, legend, style, library animations

**Status: Living until task 12 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-706, F-710, F-801-F-807, F-901, F-912, the
defaults table's row "Colour of `plot`"; `docs/plan.md`, *Morphing is per-artist*;
`docs/parity-survey.md` §2.1 (legend, colour cycle). Builds on tasks 06-11.

Modules: `src/manim_plots/mobjects/legend.py`, `mobjects/animations.py`,
`mobjects/artists.py` (labels, styles, markers, the cycle), `core/shape.py` (dashes,
the resampling `Morph` needs).

```python
class Legend(VGroup):  # mp.Legend, star-exported
    def __init__(self, *artists, font_size: float = 24, buff: float = 0.25) -> None: ...

    entries: list[LegendEntry]  # (artist, handle, label) in order

    def merge(self, *others: Legend) -> Legend: ...
    def split(self) -> list[Legend]: ...


class CartesianAxes:
    def legend(self, location: str = "upper right", **kwargs) -> Legend: ...
    def get_legend(self) -> Legend | None: ...
    def get_legend_handles_labels(self) -> tuple[list[Mobject], list[str]]: ...


class LineStyle(Enum):  # mp.LineStyle
    SOLID = ...
    DASHED = ...
    DOTTED = ...


class Marker(Enum):  # mp.Marker
    DOT = ...
    CIRCLE = ...
    SQUARE = ...
    TRIANGLE = ...
    CROSS = ...
    STAR = ...


COLOR_CYCLE: tuple[ManimColor, ...]  # mp.COLOR_CYCLE


class DrawAxes(Animation): ...  # DrawAxes(ax)


class TraceCurve(Animation): ...  # TraceCurve(artist)


class ShowPoints(Animation): ...  # ShowPoints(scatter)


class Morph(Animation): ...  # Morph(a, b)
```

## LG — legend (F-801, F-802, F-901)

| ID | Row |
|---|---|
| LG-1 | A label comes from the artist's keyword — `ax.plot(f, label="sin")`, `ax.line(..., label=...)`, `ax.scatter(..., label=...)`, `ax.plot_parametric_curve(..., label=...)` — or `artist.set_label("sin")`, and reads back as `artist.get_label()` (`None` when unset). `label` is not a style keyword and never reaches `VMobject` |
| LG-2 | `ax.legend()` collects the registered artists that have a label, in registration order, and returns a `Legend`; with none it raises `ValueError` naming `label`. `ax.get_legend()` returns the last legend `ax.legend()` made, or `None`. `ax.get_legend_handles_labels()` returns the handles and labels `ax.legend()` would use, without making one |
| LG-3 | An entry is a handle and a label in a row: the handle left, the label right of it at `buff`, entries stacked downward at `buff`, labels left-aligned. A line-like artist's handle is a horizontal segment of length `0.5` with the artist's stroke colour, width, opacity and line style; a scatter's handle is one copy of its marker. The label is laid out as Manim's `Text(label, font_size=font_size)` — the same width and height — in the artist's colour, its glyphs library leaves (LG-7) *(default taken)* |
| LG-4 | Placement *(default taken)*: `location` is one of `"upper right"`, `"upper left"`, `"lower left"`, `"lower right"`; the legend's matching corner sits `buff` inside the same corner of the axes' rectangle (the viewport through `c2p`). Another value raises `ValueError` listing the four. `ax.legend()` is bound to `ax` like a helper label (F-609): it follows `ax.shift`, `ax.rotate` and `ax.scale`, and keeps its corner across a range change |
| LG-5 | `Legend(*artists)` takes artists of any systems (F-801, defect 7) and is not bound; it sits at `ORIGIN` until placed. An artist without a label raises `ValueError` naming `label` |
| LG-6 | `a.merge(b, ...)` returns a new legend with `a`'s entries then those of `b`, ...; an artist already present is not repeated. `legend.split()` returns one legend per entry, in order. Neither changes `a`, `b` or the legend split |
| LG-7 | Every leaf of a legend with points — handles and label glyphs — is a library `Leaf` (F-901, F-1004) |

## CY — the colour cycle (F-803, the defaults table)

| ID | Row |
|---|---|
| CY-1 | `mp.COLOR_CYCLE` is `(WHITE, BLUE, YELLOW, GREEN, RED, PURPLE, ORANGE, TEAL)` — Manim's colours, the first white as the defaults table says *(default taken)* |
| CY-2 | Each system counts the artists it gives a colour: the k-th artist created on `ax` without a colour keyword (`color`, `stroke_color`, and for a scatter's default marker `fill_color`) takes `COLOR_CYCLE[k % 8]`; an artist with an explicit colour takes none and does not advance the count. `plot_line_graph` keeps Manim's `line_color` default and does not advance it |
| CY-3 | A scatter with the default marker takes the cycle colour as its markers' fill; a custom marker keeps its own style and does not advance the count |

## ST — style (F-804, F-806, F-807)

| ID | Row |
|---|---|
| ST-1 | `line_style=mp.LineStyle.DASHED` (any line-like artist) draws dashes of arc length `0.2` and gaps of `0.1`, `DOTTED` dashes of `0.03` and gaps of `0.07`, in scene units *(default taken)*; `dash=(on, off)` gives a custom pattern and wins over `line_style`. A string such as `"--"` raises `TypeError` naming `LineStyle` (F-804: no shorthand strings) |
| ST-2 | Dashes are measured by arc length on the final geometry and restart at each path piece (F-806, ADR 0003 §1): every dash but the last of a piece has arc length `on` within `1e-3`, and the same curve sampled more finely (`x_range=(lo, hi, 0.01)`) starts its dashes at the same points within `1e-2` |
| ST-3 | `marker=mp.Marker.X` on `ax.scatter` gives Manim's shape for it — `DOT` Manim's `Dot()`, `CIRCLE` an outline `Circle`, `SQUARE` a filled `Square`, `TRIANGLE` a filled `Triangle`, `CROSS` Manim's `Cross` of two lines, `STAR` a filled `Star` — each `2 * DEFAULT_DOT_RADIUS` wide and centred on the point; a named marker takes the cycle colour (CY-2) as its fill, or as its stroke for the outline `CIRCLE` and `CROSS` *(default taken)*. A string raises `TypeError` naming `Marker` |
| ST-4 | `ax.scale(2)` leaves every stroke width of `ax`'s leaves and of its artists as it was (Manim's default); `ax.scale(2, scale_stroke=True)` multiplies each by 2, as Manim does on a `VMobject` (F-807) |

## CL — clipping to the axes (F-706, F-114; asked for by the maintainer on 2026-10-29)

| ID | Row |
|---|---|
| CL-1 | Every artist takes `clip: bool \| float = True` — `ax.plot`, `ax.line`, `ax.scatter`, `ax.plot_parametric_curve` (and `plot_line_graph`'s parts through `**kwargs`). `True` clips to the axes' rectangle, as before; `False` never clips, as Manim draws; a number is a margin in scene units on every side of the rectangle, positive to widen it, negative to narrow it *(default taken: scene units, so the margin looks the same on both axes)*. A line-like artist's anchors then stay within the rectangle grown by the margin, and reach past the rectangle where the curve does; a scatter shows a point whose marker centre lies within it. A margin that narrows the rectangle to nothing raises `ValueError` naming `clip`. A pole still splits the path whatever `clip` is (F-705) |
| CL-2 | `artist.set_clip(value)` changes it later and rebuilds; `artist.get_clip()` reads it back |

## AN — the library's animations (F-912, F-710)

The oracle is again a plain twin (task 09) wherever Manim has the equivalent animation.

| ID | Row |
|---|---|
| AN-1 | `DrawAxes(ax)` is `Create` of `ax`'s visible leaves without the frame's lag slot (F-1008): on every frame each visible leaf of `ax` equals its twin under `Create` of a `VGroup` of the visible leaves' twins in family order; at the end every leaf is complete and the artists of `ax` are untouched |
| AN-2 | `TraceCurve(artist)` reveals the artist in data order (F-912): at every frame the drawn part of a `FunctionPlot` ends at `x0 + alpha * (x1 - x0)` in data, within one sample spacing, however its adaptive sampling is spread — where `Create` paces by curve count — and so after `curve.reverse_points()` too; a `LinePlot` in data-index order. At the end the artist is complete and attached |
| AN-3 | `ShowPoints(scatter)` reveals the markers in data order: on every frame a marker is at least as opaque as every later one, the first frame shows none, the end shows every valid marker at full opacity, and a marker hidden by AR-6 (outside the viewport or invalid) stays hidden |
| AN-4 | `Morph(a, b)` between line-like artists resamples `a` on `b`'s parameterisation along arc length (F-710): every frame has `b`'s point count (no inserted duplicates), and its point at arc fraction `s` is `a`'s and `b`'s points at `s` interpolated by alpha, within `1e-3`. At the end `a` draws `b`'s data on `b`'s system and follows it; `b` is unchanged |
| AN-5 | `Morph` raises `ValueError` before the play on a pair it cannot resample honestly: a scatter with a line-like artist, or two artists whose paths have different numbers of pieces (a curve split at a pole with an unbroken one) |
| AN-6 | `DrawAxes`, `TraceCurve`, `ShowPoints` and `Morph` are star-exported (A-1: Manim has none of the names), as are `Legend`, `LineStyle`, `Marker` and `COLOR_CYCLE` |

## Tests

| File | Rows |
|---|---|
| `tests/mobjects/test_legend.py` | LG-1 … LG-7 |
| `tests/mobjects/test_style.py` | CY-1 … CY-3, ST-1 … ST-4, CL-1, CL-2 |
| `tests/mobjects/test_animations.py` | AN-1 … AN-5 |
| `tests/test_public_api.py` | AN-6 |
| `tests/visual/test_style_pictures.py` | two curves and a scatter with the cycle and a legend; the line styles; the markers; every frame of `TraceCurve` and of `Morph` |
