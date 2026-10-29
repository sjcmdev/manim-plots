# Acceptance table — task 11, part A: the artists

**Status: Living until task 11 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-701-F-709, F-112, F-704, F-705,
F-805 (markers), F-919's copy row; ADR 0003 §4 (`plot`'s parameters) and §8 (`ax.remove`).
Part B (the data channel under `.animate`, `Transform` between systems,
`ReplacementTransform`, the F-906 matrix) follows in its own table.

Modules: `src/manim_plots/mobjects/artists.py`, `mobjects/system.py`.

## AR — the four artists (F-701)

```python
class FunctionPlot(Leaf): ...  # ax.plot(f)              — task 09


class LinePlot(Leaf): ...  # ax.line(xs, ys), ax.plot(xs, ys)


class ScatterPlot(VGroup): ...  # ax.scatter(xs, ys, marker=None)


class ParametricPlot(Leaf): ...  # ax.plot_parametric_curve(f, t_range=...)


class CartesianAxes:
    @overload
    def plot(
        self,
        function: Callable[..., float],
        x_range=None,
        use_vectorized=False,
        **kwargs,
    ) -> FunctionPlot: ...
    @overload
    def plot(
        self, xs: ArrayLike, ys: ArrayLike | None = None, **kwargs
    ) -> LinePlot: ...
    def line(self, xs, ys=None, **kwargs) -> LinePlot: ...
    def scatter(
        self, xs, ys=None, *, marker: Mobject | None = None, **kwargs
    ) -> ScatterPlot: ...
    def plot_parametric_curve(
        self, function, use_vectorized=False, **kwargs
    ) -> ParametricPlot: ...
    def plot_line_graph(
        self,
        x_values,
        y_values,
        z_values=None,
        line_color=PURE_YELLOW,
        add_vertex_dots=True,
        vertex_dot_radius=DEFAULT_DOT_RADIUS,
        vertex_dot_style=None,
        **kwargs,
    ) -> VDict: ...
    def remove(self, *artists) -> Self: ...
    def i2gp(self, x, graph) -> np.ndarray: ...  # input_to_graph_point
    def i2gc(self, x, graph) -> tuple[float, float]: ...  # input_to_graph_coords
```

| ID | Row |
|---|---|
| AR-1 | `FunctionPlot`, `LinePlot`, `ScatterPlot`, `ParametricPlot` are star-exported (A-1: Manim has none of the names) |
| AR-2 | `ax.plot` dispatches on its first argument (F-702): a callable gives a `FunctionPlot`, anything array-like a `LinePlot`; `typing.get_overloads(CartesianAxes.plot)` lists both overloads (F-1005) |
| AR-3 | `ax.plot(f, **kwargs)` (ADR 0003 §4): the names of `inspect.signature(f)` after the first are `f`'s parameters, taken from `kwargs` or `f`'s own defaults; every other keyword is a `VMobject` style keyword. A parameter named like a style keyword (`color`, `stroke_width`, `fill_opacity`, …) raises `ValueError` naming it. `plot.parameters` maps each name to a `Parameter` (task 07): `plot.parameters["a"].value = 3` resamples (F-918); a value that is a `ValueTracker` or a callable binds the parameter (F-918: sampled every frame) |
| AR-4 | `plot`'s keywords keep Manim's meaning (F-704): `x_range` with an optional step capping the spacing, `use_vectorized`, `use_smoothing` (`False` gives straight segments, `corners`), `discontinuities`, `dt` |
| AR-5 | `ax.line(xs, ys)` and `ax.line(pairs)` (F-703) draw the data through the frame: every anchor is `c2p` of a data point or a crossing of the viewport's side; `NaN` splits the line (F-705); the data is never changed (F-104); a range change filters, never resamples (F-104) |
| AR-6 | `ax.scatter(xs, ys, marker=None)`: one marker per point at `c2p(x, y)`; the default marker is Manim's `Dot()` (radius `DEFAULT_DOT_RADIUS`, its style) *(default taken)*. A custom marker may be any `Mobject` (F-805): each of its leaves becomes a library leaf with that leaf's outline and style, centred on the point. A point outside the viewport or invalid is not drawn (opacity 0, F-114); its marker keeps its place in the group, so marker `i` is always point `i` |
| AR-7 | `ax.plot_parametric_curve(f, t_range=..., use_vectorized=False, **kwargs)` — Manim's signature (`t_range` among the keywords, default `(0, 1)`): every anchor is `c2p(*f(t))` for its sample `t` |
| AR-8 | `plot_line_graph(...)` — Manim's signature and return: a `VDict` with `"line_graph"` (a `LinePlot`, `line_color` stroke) and, when `add_vertex_dots`, `"vertex_dots"` (a `ScatterPlot` of `Dot(radius=vertex_dot_radius, **vertex_dot_style)`); without clipping, the line's anchors and the dots' centres equal Manim's `plot_line_graph` on the same `Axes` within `1e-9` |
| AR-9 | `i2gp(x, graph)` / `input_to_graph_point` and `i2gc` / `input_to_graph_coords` (F-707) evaluate the source and the map: for a `FunctionPlot` exactly `c2p(x, f(x))`, between samples too, after a resample too; for a `LinePlot` the linear interpolation in `x`, raising `ValueError` on non-monotone `x` data; a graph bound to another system raises `ValueError` |
| AR-10 | `ax.remove(artist)` unregisters it (ADR 0003 §8): it no longer follows `ax` or its data and keeps its last points; it may then be added to another system, where it rebuilds from its source in that system *(default taken)*. Removing an artist that is not registered raises `ValueError` |
| AR-11 | `artist.copy()` (F-919's copy row) is attached to the same system and follows it, but is not registered: `ax.artists` (the registered ones, in order of registration) does not list it, and `ax.remove(copy)` raises. `ax.copy()` is a new system with no artists; the original's artists stay with the original |
| AR-12 | Every artist's points are library leaves (F-1004); `ScatterPlot`'s markers included |

## Tests

| File | Rows |
|---|---|
| `tests/mobjects/test_artists.py` | AR-1 … AR-9, AR-12 |
| `tests/mobjects/test_registration.py` | AR-10, AR-11, and F-112, F-708, F-709 across the four artists |
| `tests/visual/test_artist_pictures.py` | a line with a `NaN` gap, a scatter with a custom marker, a parametric spiral clipped by the axes, `plot_line_graph` with its `__manim` twin |
