# Acceptance table — task 16, bound helpers I: lines and tangents

**Status: Living until task 16 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §5 (names), §6 (bound helpers), §9
(customisation); `docs/scope.md` F-112, F-605, F-609, F-707, F-708, F-905, F-907, F-916,
F-1008, F-1009; the parity survey's *Calculus* and *Drop lines* sections. Builds on tasks
06-15.

Modules: `src/manim_plots/mobjects/helpers.py` (new), `mobjects/system.py` (the verbs),
`core/sources.py` (the derived sources), `src/manim_plots/__init__.py`.

The oracle is Manim's own helper on Manim's own `Axes` wherever Manim has one and its
picture is not a defect; otherwise geometry computed from `c2p` and `i2gp` in the test.

```python
class HelperLine(Leaf):  # mp.HelperLine, not star-exported
    """One line-like part of a helper: a registered artist with its own style."""


class HelperGroup(VGroup):  # mp.HelperGroup, not star-exported
    """A helper of several parts, each reachable by its Manim name."""


class CartesianAxes:
    # drop lines
    def get_line_from_axis_to_point(
        self, index, point, line_func=DashedLine, line_config=None, color=None,
        stroke_width=2,
    ) -> HelperLine: ...
    def get_vertical_line(self, point, **kwargs) -> HelperLine: ...
    def get_horizontal_line(self, point, **kwargs) -> HelperLine: ...
    def get_lines_to_point(self, point, **kwargs) -> HelperGroup: ...
    def get_vertical_lines_to_graph(
        self, graph, x_range=None, num_lines=20, **kwargs
    ) -> HelperGroup: ...
    def axvline(self, x, ymin=0, ymax=1, **style) -> HelperLine: ...
    def axhline(self, y, xmin=0, xmax=1, **style) -> HelperLine: ...

    # calculus
    def get_T_label(
        self, x_val, graph, label=None, label_color=None,
        triangle_size=MED_SMALL_BUFF, triangle_color=WHITE, line_func=Line,
        line_color=PURE_YELLOW, *, label_direction=DOWN, label_buff=MED_SMALL_BUFF,
    ) -> HelperGroup: ...
    def angle_of_tangent(self, x, graph, dx=1e-8) -> float: ...
    def slope_of_tangent(self, x, graph, **kwargs) -> float: ...
    def get_tangent_line(self, x, graph, length=1, **style) -> HelperLine: ...
    def get_tangent_vector(self, x, graph, length=1, **style) -> HelperGroup: ...
    def get_secant_slope_group(
        self, x, graph, dx=None, dx_line_color=PURE_YELLOW, dy_line_color=None,
        dx_label=None, dy_label=None, include_secant_line=True,
        secant_line_color=GREEN, secant_line_length=10, *,
        dx_label_direction=None, dy_label_direction=None,
    ) -> HelperGroup: ...
    def plot_derivative_graph(self, graph, color=GREEN, **kwargs) -> FunctionPlot: ...
    def plot_antiderivative_graph(
        self, graph, y_intercept=0, samples=50, use_vectorized=False, **kwargs
    ) -> FunctionPlot: ...
```

## HB — the bound-helper base (ADR 0004 §6, §9)

| ID | Row |
|---|---|
| HB-1 | Every line-like part of a helper is a `HelperLine`: an artist registered with the system that made it (F-708, F-112), with no label, so `ax.legend()` leaves it out unless `set_label` gives it one. It follows the system's permanent changes as a plot does (F-916) and takes Manim's creation and removal animations as a plot does (F-905, F-907) |
| HB-2 | A number input of a helper — `x`, `x_val`, `dx`, either end of `x_range`, `axvline`'s `x`, `axhline`'s `y` — also accepts a `ValueTracker` (anything with a callable `get_value`) or a zero-argument callable, bound as a plot's function parameter is (F-110, F-918): the helper is re-derived on every frame where the value changed, with no `always_redraw` |
| HB-3 | A `point` input of a drop line is a scene point, converted to data coordinates once at the call and then held in data, so the line follows a changed range or frame; a `Mobject`, whose centre is read every frame; or a zero-argument callable returning a scene point, read every frame *(default taken: the three forms)* |
| HB-4 | A helper bound to a `graph` follows that graph: a change of its parameters (`set_parameters`, a bound tracker), of its source (`become`) or of its own transform re-derives the helper in the same frame. A graph registered with another system raises `ValueError` naming `graph` |
| HB-5 | A helper is derived in data space and placed through the system's map and frame, so it is correct on log scales, reversed ranges, rotated axes and a warped frame, where Manim's scene-space construction is not |
| HB-6 | Customisation (ADR 0004 §9). Every part of a `HelperGroup` is reachable by its Manim name (`dx_line`, `df_line`, `dx_label`, `df_label`, `secant_line`) or by a name of this table where Manim has none, and is styled on its own; a style set on a part (`set_color`, `set_stroke`, `line_style`, `dash`, `clip`) survives every re-derivation, because a re-derivation replaces points, never style. Every default the helper picks is a keyword of its call. A label may be a callable `f(value) -> str \| Mobject`, re-rendered when the value it reads changes |
| HB-7 | When a bound input leaves the graph's domain or the axis range during an animation, the helper's parts collapse and are not drawn on that frame (the transient rule of F-409), and come back when it returns. At the call, a number outside raises `ValueError` naming the input |
| HB-8 | `line_func` accepts Manim's `Line` (solid) and `DashedLine` (dashed, with `line_config`'s `dash_length` and `dashed_ratio` as Manim's: `DEFAULT_DASH_LENGTH` and 0.5) and nothing else, raising `TypeError` naming `line_func` *(default taken)*. `line_config` takes those two keys, `VMobject` style keys and `buff` (Manim's `Line` buff, trimmed at both ends); another key raises `TypeError` naming it. A returned `HelperLine` is not an instance of `Line` or `DashedLine`: a difference listed under F-1008 |

## DL — drop lines and reference lines (parity survey, *Drop lines*)

| ID | Row |
|---|---|
| DL-1 | `get_line_from_axis_to_point(index, point, ...)` draws from the axis `index` to the point along the other axis's direction in data space: for `index=0`, from `(x, c)` to `(x, y)`, where `(x, y)` is the point in data and `c` is the y value at which the x axis is drawn (F-605: the crossing, a border, a data value). Manim's colour default (`VMobject().color`) and `stroke_width=2`. On Manim's default `Axes`, with the point in the first quadrant, its start and end equal Manim's to `1e-9` |
| DL-2 | `get_vertical_line(point, **kwargs)` is `index=0`, `get_horizontal_line(point, **kwargs)` is `index=1`, and `get_lines_to_point(point, **kwargs)` returns a `HelperGroup` of the horizontal then the vertical line, as Manim orders them, reachable also as `.horizontal_line` and `.vertical_line` |
| DL-3 | `get_vertical_lines_to_graph(graph, x_range=None, num_lines=20, **kwargs)` draws `num_lines` vertical lines from the x axis to the graph at `np.linspace(x_range[0], x_range[1], num_lines)`; `x_range` defaults to the system's x range, as in Manim, and then follows it. The lines follow the graph (HB-4). `num_lines` below 1 raises `ValueError` |
| DL-4 | `axvline(x, ymin=0, ymax=1, **style)` and `axhline(y, xmin=0, xmax=1, **style)`, matplotlib's meaning: `x` (`y`) in data coordinates, the extent in fractions of the viewport's height (width), drawn from `ymin` to `ymax` (`xmin` to `xmax`). Defaults: solid, Manim's default colour, `stroke_width=2` *(default taken)*. A fraction outside `[0, 1]` reaches past the viewport and is clipped like any artist |

## TL — the T label (parity survey, *Calculus*)

| ID | Row |
|---|---|
| TL-1 | `get_T_label(x_val, graph, ...)` keeps Manim's signature, defaults and part order — label (when given), triangle, vertical line — and adds `.label`, `.triangle`, `.line` *(default taken: the names)* |
| TL-2 | The triangle's top vertex sits on the x axis where it is drawn, at `x_val`, pointing up, `triangle_size` high; the vertical line runs from the axis to `graph` at `x_val`; the label sits next to the triangle in `label_direction` with `label_buff`. On Manim's default `Axes`, where the x axis is at `y = 0`, every part equals Manim's to `1e-6` |
| TL-3 | Manim defect fixed: in `Axes(x_range=[1, 5], y_range=[2, 10])` Manim puts the triangle's top at `y = 0`, 1.5 below the axis; here it touches the axis |
| TL-4 | With `x_val` a tracker the whole label slides; a callable `label` reads the current `x_val` |

## TG — slopes and tangents (parity survey, *Calculus*; ADR 0004 §5)

| ID | Row |
|---|---|
| TG-1 | `angle_of_tangent(x, graph, dx=1e-8)` keeps Manim's meaning: the angle of the data vector from `i2gc(x)` to `i2gc(x + dx)`. `slope_of_tangent(x, graph, **kwargs)` is its tangent. Because `i2gc` is exact here (F-707), the slope of `x**2` at 3 is `6` to `1e-6` |
| TG-2 | `get_tangent_line(x, graph, length=1, **style)` is a `HelperLine` of scene length `length`, centred on `i2gp(x, graph)`, along the drawn curve's direction there: the derivative of the mapped curve, by a central difference of `i2gp` *(default taken: the step, small against the viewport)*. It is tangent on a log scale and on a warped frame. `length=1` is Manim's `TangentLine` default |
| TG-3 | `get_tangent_vector(x, graph, length=1, **style)` is a `HelperGroup` of `.line` and `.tip`, an arrow from `i2gp(x)` along the same direction; `length` may also be a callable of the slope, so the arrow can scale with it. The tip is Manim's `ArrowTriangleFilledTip` shape at Manim's default tip size |

## SC — the secant slope group (parity survey, *Calculus*)

| ID | Row |
|---|---|
| SC-1 | `get_secant_slope_group(x, graph, dx=None, ...)` keeps Manim's signature, defaults, part order and attribute names: `dx_line`, `df_line`, `dx_label` and `df_label` when given, `secant_line` when `include_secant_line` |
| SC-2 | The legs follow the system's axes: `dx_line` from the graph at `x` to the data point `(x + dx, f(x))`, `df_line` from there to the graph at `x + dx`, each mapped like a plot. On Manim's default `Axes` every part equals Manim's to `1e-6`; on axes rotated by 30°, `dx_line` runs along the x axis, at 30°, where Manim's stays at 0° |
| SC-3 | `dx` defaults to a tenth of the x range's span, Manim's default, read at the call. `dx` may be a tracker. At `dx = 0` the legs collapse and the secant line is the tangent, its limit, so an animation of `dx` to 0 ends on the tangent; Manim silently replaces `dx=0` by the default *(default taken)* |
| SC-4 | Labels as Manim's: a string or number becomes `MathTex`, both labels shrink together to at most 0.8 of their leg, `dx_label` sits below `dx_line` and `df_label` right of `df_line`, flipped by the sign of `dx`, each in its leg's colour. `dx_label_direction` and `dy_label_direction` override the side. A label may be a callable of `dx` (HB-6) |
| SC-5 | `secant_line` passes through both graph points, is `secant_line_length` long in scene units and centred on their midpoint, as Manim scales it |

## DG — derived graphs (parity survey, *Calculus*)

| ID | Row |
|---|---|
| DG-1 | `plot_derivative_graph(graph, color=GREEN, **kwargs)` returns a `FunctionPlot` of the derivative of `graph`'s function, by a central difference in data space *(default taken: the step, `cbrt(eps) * max(1, |x|)`)*, vectorised when the parent is. Its x range defaults to the parent's, `kwargs` are `plot`'s, and it follows the parent (HB-4). The derivative of `x**2` equals `2 x` to `1e-6` over `[-3, 3]` |
| DG-2 | `plot_antiderivative_graph(graph, y_intercept=0, samples=50, use_vectorized=False, **kwargs)` returns a `FunctionPlot` of `y_intercept + ∫_0^x f`, Manim's meaning, integrated once per re-derivation over the whole range rather than once per sample. Where 0 lies outside the parent's x range or domain the integral starts at the start of the range, a difference listed under F-1008 *(default taken)*. `samples` is accepted for Manim's signature and has no effect *(default taken)*. The antiderivative of `cos` equals `sin` to `1e-6` over `[-3, 3]`, and of `1 / x` on `[1, 5]` equals `ln x` to `1e-6` |
| DG-3 | Both follow the parent's parameters and source (HB-4) |

## Tests

`tests/mobjects/test_helpers_lines.py`:

- HB: registration and the legend; a tracker `x` re-derives with no `always_redraw`; the
  three point forms; following `set_parameters`, `become`, a shift and a rotation of the
  system and `ax.animate.set_x_range`; a style set on a part surviving a re-derivation;
  the transient collapse; the call-time errors; `line_func` and `line_config`.
- DL, TL, SC: each against Manim's helper on Manim's default `Axes`, geometry equal; the
  defect cases of TL-3 and SC-2; `axvline`, `axhline`.
- TG, DG: the numbers above; tangency on a log x axis (the tangent line's direction
  equals the drawn curve's chord direction at a small step).
- Visual: `test_drop_lines_and_t_label`, `test_secant_and_tangent`,
  `test_derivative_and_antiderivative`, each with a `__manim` twin on Manim's `Axes`.
- A frame-cost reading: a sliding `T` label and a secant with a tracker `dx` on F-1001's
  axes, recorded in this table, not gated.
