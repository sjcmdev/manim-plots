# Acceptance table — task 20, themes and colour cycles

**Status: Living until task 20 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed; the theme and cycle names are the maintainer's to refine.
Contracts: ADR 0004 §2 (named presets, the maintainer's Origin themes among them), §9
(presets only set defaults); ADR 0005 §1 (ticks at a border point inward, TH-11);
`docs/scope.md` F-603-F-608, F-801, F-803, F-808 (colour
themes, amended here); task 19 (twins). Builds on tasks 06-19.

Sources the maintainer supplied, in `D:\Aplications\Origin\User Files`: the graph
template `Base-plot.otpu` (a box, the major grid, a framed legend upper right) and the
colour lists `Themes/Graph/something.oth` (12 colours) and `Themes/Graph/S03 Fire.oth`
(9 colours), decoded on 2026-10-29.

Modules: `src/manim_plots/mobjects/themes.py` (new), `mobjects/system.py`,
`mobjects/legend.py`, `src/manim_plots/__init__.py`.

```python
@dataclass(frozen=True)
class Theme:  # mp.Theme, star-exported
    name: str
    position: Literal["origin", "border"] = "origin"
    box: bool = False                      # mirrors on the top and right
    tips: bool = True
    tick_direction: TickDirection | None = None  # None: TH-11's rule
    minor_ticks: int = 0                   # minor ticks between two majors
    grid: tuple[Level, ...] = ()           # (), ("major",) or ("major", "minor")
    grid_style: Mapping[str, Any] = ...    # VMobject style of the major grid
    minor_grid_style: Mapping[str, Any] = ...  # over grid_style for the minor grid
    legend_location: str = "upper right"
    legend_frame: bool = False
    cycle: str | tuple[ParsableManimColor, ...] = "manim"
    line_styles: tuple[LineStyle, ...] = ()   # cycled with the colours when given
    markers: tuple[Marker, ...] = ()          # cycled for scatters when given

THEMES: Mapping[str, Theme]                   # mp.THEMES
CYCLES: Mapping[str, tuple[ManimColor, ...]]  # mp.CYCLES

def set_theme(theme: str | Theme | None) -> None: ...  # mp.set_theme
def get_theme() -> Theme: ...                          # mp.get_theme

class CartesianAxes:
    def __init__(self, ..., *, theme: str | Theme | None = None,
                 cycle: str | Sequence[ParsableManimColor] | None = None, ...): ...
    theme: Theme

    def legend(self, location=None, *, font_size=24, buff=0.25,
               frame=None, frame_style=None) -> Legend: ...
```

## TH — themes (F-808, ADR 0004 §9)

| ID | Row |
|---|---|
| TH-1 | `theme="manim"`, the default, changes nothing: every system built without a theme is what task 19 builds, picture for picture |
| TH-2 | A theme sets only what the call leaves unset. A constructor argument (`tips=`, an `axis_config` key, `x_axis_config`, `y_axis_config`) wins over the theme, and every later decoration call (`set_position`, `set_tips`, `set_tick_style`, `set_grid`, `set_locator`, styles) wins over both. A theme is applied once, at construction; `ax.theme` reads it back |
| TH-3 | The five themes *(default taken: the names and their contents)*: |
| | `manim` — today's: axes through the origin, tips, ticks across the axis, no minor ticks, no grid, legend upper right without a frame, cycle `manim` |
| | `origin` — Origin's default 2D graph: axes at the left and bottom borders, a box (mirrored axes at the top and right, without numbers), no tips, ticks inward (TH-11), one minor tick between majors, no grid, a framed legend upper left, cycle `origin` |
| | `base` — the maintainer's `Base-plot.otpu`: `origin`, plus the major grid in a faint line (`stroke_opacity=0.35`, `stroke_width=1`) and the framed legend upper right |
| | `paper` — black and white for print: `origin` (ticks inward on all four sides), cycle `gray`, line styles cycling solid, dashed, dotted, markers cycling circle, square, triangle, cross |
| | `lab` — graph paper for measurements: `origin`, four minor ticks between majors, the major grid as `base`'s and the minor grid fainter (`stroke_opacity=0.15`, `stroke_width=0.5`), cycle `colorblind` |
| TH-4 | The cycles *(default taken: the names)*, each colour exact: `manim` (today's `COLOR_CYCLE`); `origin`, the maintainer's 12: `#515151 #F14040 #1A6FDF #37AD6B #B177DE #CC9900 #00CBCC #7D4E4E #8E8E00 #FB6501 #6699CC #6FB802`; `fire`, the maintainer's 9, dark red to yellow, for series ordered by a parameter: `#8B0800 #FF0000 #E51800 #FF3E1C #FF5B00 #FF9000 #F4A666 #FFC600 #FFFF7D`; `colorblind`, matplotlib's Petroff 10: `#3F90DA #FFA90E #BD1F01 #94A4A2 #832DB6 #A96B59 #E76300 #B9AC70 #717581 #92DADD`; `gray`: `#FFFFFF #BBBBBB #888888 #555555` |
| TH-5 | `cycle=` on the constructor takes a cycle's name or a sequence of colours and wins over the theme's; an uncoloured artist takes the next colour of it (F-803), and with the theme's `line_styles` or `markers` the next style or marker in step |
| TH-6 | A user theme is a `Theme`, made directly or from another with `dataclasses.replace(mp.THEMES["origin"], grid=("major",))`; a `dict` of `Theme` fields is accepted too *(default taken)*. An unknown name, field or cycle raises `ValueError` naming it |
| TH-7 | `mp.set_theme(name_or_theme)` sets the default for systems built afterwards, `mp.set_theme(None)` restores `manim`, `mp.get_theme()` reads it; a system's own `theme=` wins |
| TH-8 | A twin (task 19) takes its parent's theme: its axis follows the theme's ticks and tips rules, and its artists continue the parent's cycle |
| TH-9 | `ax.legend(location=None, frame=None, frame_style=None)`: `None` takes the theme's location and frame. `frame=True` draws a rectangle around the legend, `buff` away from its entries, in `frame_style` (default: the axes' line colour, `stroke_width=1`, no fill) *(default taken)*; the frame moves with the legend |
| TH-10 | `mp.NumberPlane` accepts `theme=` and `cycle=` for the colour cycle and the legend; its grid stays Manim's `background_line_style` unless the call sets one |
| TH-11 | Ticks at a border point inward (ADR 0005 §1). With no direction set, an axis placed at a named border by `set_position` (`"bottom"`, `"top"`, `"left"`, `"right"`, with or without `offset`), every mirror, a twin's own axis and every axis of a `position="border"` theme draws its major and minor ticks `IN`, toward the data rectangle: up at the bottom, down at the top, right on the left, left on the right, the numbers staying outside. An axis placed through the data (`"origin"`, a value, a `fraction`) keeps Manim's straddling ticks, also when a range that excludes zero puts it on the rectangle's edge. A set direction wins: `set_ticks_direction`, `set_tick_style(direction=...)`, a theme's `tick_direction`, a later `set_position` not undoing it. `Theme.tick_direction=None` is this rule, and every named theme takes it. Supersedes TW-2's outward ticks and the `OUT` default of an offset axis; the scope defaults row *Tick shape* is amended to say so |

## Tests

`tests/mobjects/test_themes.py`:

- TH-1: every family point and style of a scene with and without `theme="manim"`.
- TH-2, TH-3: each theme against the same system built with `theme="manim"` and the
  explicit calls the row lists; a constructor argument and a later call winning.
- TH-4, TH-5: every cycle's hex values; `cycle=` by name and as a list; line styles and
  markers in step on `paper`.
- TH-6, TH-7: a replaced theme, a dict, the three errors; `set_theme` and `get_theme`,
  reset afterwards in a `finally`.
- TH-8, TH-9, TH-10: a twin under `origin`; the legend frame and its following; a plane.
- TH-11: the tick side of a bottom, top, left and right axis placed at the border, of a
  mirror, of a twin and of an offset axis; an axis at the origin and Manim's default
  axes on a range without zero unchanged; a set direction winning, also over a later
  `set_position`.
- Visual: `test_theme_<name>` for the five themes, the same scene each time (two
  labelled curves, a scatter, axis labels, a legend); no Manim twin.
