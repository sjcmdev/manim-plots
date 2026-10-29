# Acceptance table — task 17, bound helpers II: regions

**Status: Living until task 17 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0004 §5, §6, §9; `docs/scope.md` F-605, F-706
(clipping per axis), F-711 (filled regions), F-1008, F-1009; task 16's HB rows, which
apply here unchanged. Builds on tasks 06-16.

Modules: `src/manim_plots/mobjects/helpers.py`, `mobjects/system.py`, `core/shape.py`
(clipping a filled region).

```python
class FilledRegion(Leaf):  # mp.FilledRegion, not star-exported
    """A filled area between two boundaries over an x interval: one artist."""


class CartesianAxes:
    def get_area(
        self,
        graph,
        x_range=None,
        color=(BLUE, GREEN),
        opacity=0.3,
        bounded_graph=None,
        **kwargs,
    ) -> FilledRegion: ...
    def fill_between(
        self, x, y1, y2=0, *, where=None, interpolate=False, **style
    ) -> FilledRegion: ...
    def get_riemann_rectangles(
        self,
        graph,
        x_range=None,
        dx=0.1,
        input_sample_type="left",
        stroke_width=1,
        stroke_color=BLACK,
        fill_opacity=1,
        color=(BLUE, GREEN),
        show_signed_area=True,
        bounded_graph=None,
        blend=False,
        width_scale_factor=1.001,
    ) -> HelperGroup: ...
```

`baseline` below is the y value at which the x axis is drawn (F-605), as in task 16's
DL-1: 0 when the x axis crosses there, the range's edge when the range excludes 0, or
the border or value the axis was moved to.

## RG — filled regions (F-711, ADR 0004 §6)

| ID | Row |
|---|---|
| RG-1 | A `FilledRegion` is one registered artist with no label (HB-1): a closed path whose boundary is the upper boundary from left to right and the lower one back, filled. It follows its graphs, the system and bound inputs as task 16's helpers do (HB-2, HB-4, HB-5) |
| RG-2 | A boundary that is a graph is the graph's sampled and smoothed curve over the interval, before the graph's own clipping, and not its control points, so the drawn region's area equals the integral of the difference of its boundaries, in scene units, to `1e-3` relative |
| RG-3 | Clipping (F-706, task 15). A region is clipped by restricting its x interval to the viewport and clamping each boundary into the viewport's y interval, so the clipped region is the intersection of the region with the rectangle, still one closed, filled path per connected piece, and its area equals the integral of the clamped difference to `1e-3` relative. `clip=(cx, cy)` and margins work as on a line; `clip=False` draws it whole |
| RG-4 | Where the boundaries cross, the region keeps both lobes; a lobe is never inverted or lost |
| RG-5 | Customisation (ADR 0004 §9): style keywords of `VMobject` (`color`, `fill_color`, `fill_opacity`, `stroke_color`, `stroke_width`) on every verb; a colour tuple is Manim's gradient; a style set later survives every re-derivation |

## AR — `get_area` (parity survey, *Calculus*)

| ID | Row |
|---|---|
| AR-1 | `get_area(graph, x_range=None, color=(BLUE, GREEN), opacity=0.3, bounded_graph=None, **kwargs)` keeps Manim's signature and defaults; `x_range` defaults to the graph's x range, and with `bounded_graph` to the intersection of both, as Manim's. Manim's two errors for ranges that do not overlap stay `ValueError` with Manim's messages |
| AR-2 | Without `bounded_graph` the region lies between the graph and `baseline`; with it, between the two graphs. On Manim's default `Axes` the region's area and bounding box equal Manim's polygon's to `1e-3` |
| AR-3 | `bounded_graph` may also be a number, a constant lower boundary *(default taken)*. Either end of `x_range` may be a tracker (HB-2), so an area can sweep in |
| AR-4 | Manim defect fixed: Manim builds the polygon from the graph's Bézier control points and never clips; here the boundary is the drawn curve (RG-2) and the region is clipped (RG-3) |

## FB — `fill_between` (matplotlib's name, ADR 0004 §5)

| ID | Row |
|---|---|
| FB-1 | `fill_between(x, y1, y2=0, *, where=None, interpolate=False, **style)` has matplotlib's meaning: `x` a one-dimensional array, `y1` and `y2` arrays of its length or scalars, the region between the two polylines through `(x, y1)` and `(x, y2)` |
| FB-2 | `where`, a boolean array of `x`'s length, keeps the stretches where it is true, one closed piece per stretch; with `interpolate=True` a stretch ends where `y1` and `y2` cross between two samples, as matplotlib's does |
| FB-3 | `y1` or `y2` may also be a graph of the same system or a callable, evaluated at `x` *(default taken)* |
| FB-4 | Defaults: the next colour of the system's cycle, `fill_opacity=0.3` (Manim's `get_area` default), `stroke_width=0` *(default taken)*. Lengths that differ, a non-finite `x`, or a `where` of the wrong length raise `ValueError` naming the argument |

## RR — `get_riemann_rectangles` (parity survey, *Calculus*)

| ID | Row |
|---|---|
| RR-1 | Manim's signature and defaults. The result is a `HelperGroup` of `FilledRegion` rectangles in x order, each reachable by index and styled on its own |
| RR-2 | The count is exact: `n` rectangles with `n` the number of integers `k >= 0` for which `x0 + k * dx` lies below `x1` by more than `1e-9 * dx`; `x_range=[1, 1.3], dx=0.1` gives 3, where Manim's `np.arange` gives 4 |
| RR-3 | Rectangle `k` spans `[x0 + k dx, x0 + k dx + width_scale_factor * dx]` and reaches from its base to `f(s)`, with `s` the left end, the right end or the centre of `[x0 + k dx, x0 + (k + 1) dx]` by `input_sample_type`; the base is `baseline`, or `bounded_graph` at the same `s`. Manim evaluates `bounded_graph` at the left end whatever `input_sample_type` says |
| RR-4 | Every rectangle is a quadrilateral in data space mapped like a plot, so on rotated axes its sides stay parallel to the axes and on a warped frame they bend with it; on Manim's default `Axes` its corners equal Manim's to `1e-6` |
| RR-5 | Colours as Manim's: `color_gradient(color, n)` along the rectangles, inverted where `f(s)` lies below the base and `show_signed_area`; `blend` sets each stroke to its fill colour; `stroke_width`, `stroke_color`, `fill_opacity` as given |
| RR-6 | `dx` and either end of `x_range` may be trackers (HB-2). When the count changes, rectangles are added or removed at the end and keep their index, so `Transform` between two groups pairs them by index |
| RR-7 | An invalid `input_sample_type` raises `ValueError` as Manim's; `dx` not finite and `> 0` raises `ValueError` naming `dx` |

## Tests

`tests/mobjects/test_helpers_regions.py`:

- RG: the area of the drawn region against the integral (the shoelace over dense points
  of the boundary); clipping at each edge and with `clip=(True, False)`; crossing
  boundaries; following a parameter, `set_x_range` and a tracker end; style surviving.
- AR: Manim's defaults, the errors, parity with Manim's polygon on default axes, the
  baseline when the range excludes 0, a constant `bounded_graph`.
- FB: arrays and a scalar, `where` with and without `interpolate`, a graph as `y1`, the
  errors.
- RR: the counts, corners against Manim's on default axes, the bounded sample point,
  colours and `blend`, rotated axes, a tracker `dx` changing the count, the errors.
- Visual: `test_area_and_riemann_rectangles` with a `__manim` twin, and
  `test_fill_between_where` alone (Manim has no `fill_between`).
- A frame-cost reading: an area with a tracker end and a Riemann sum with a tracker `dx`
  on F-1001's axes, recorded in this table, not gated.

## Frame-cost reading

2026-10-29, Codex's run: F-1001's four plots under an animated range, plus an area whose
end is a tracker (2 to 4) and a Riemann sum whose `dx` is a tracker (0.5 to 0.25):
`update` p95 10.4 ms, frame p95 99.6 ms over 60 frames. Not gated, but far above the
plots alone (2.9-3.4 ms): re-deriving a region and the rectangles every frame is the
cost to cut in task 23's performance pass.
