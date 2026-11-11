# Acceptance table — task 15, clipping per axis

**Status: Living until task 15 merges, then Record.** Written 2026-10-29 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: `docs/scope.md` F-705, F-706 (amended here by
ADR 0004); task 12's CL-1 and CL-2, which this table extends and does not change. Builds
on tasks 06-14.

Modules: `src/manim_plots/mobjects/artists.py`.

```python
Clip = bool | float  # one axis: clip at the rectangle, never, or with a margin

class FunctionPlot, LinePlot, ScatterPlot, ParametricPlot:
    def set_clip(self, value: Clip | tuple[Clip, Clip]) -> Self: ...
    def get_clip(self) -> Clip | tuple[Clip, Clip]: ...

# and clip: Clip | tuple[Clip, Clip] = True on ax.plot, ax.line, ax.scatter,
# ax.plot_parametric_curve, and plot_line_graph's parts through **kwargs
```

## CP — clipping per axis (F-706, ADR 0004)

`rect` is the axes' rectangle in the system's local space, as in CL-1; its x interval
is `[x0, x1]`, its y interval `[y0, y1]`.

| ID | Row |
|---|---|
| CP-1 | `clip` also takes a pair `(cx, cy)`, a `tuple` or a `list` of two entries *(default taken: both sequence types)*, each `True`, `False` or a real margin in scene units. `cx` decides the x interval and `cy` the y interval, independently: `True` clips at the rectangle's edges on that axis, `False` never clips on that axis, a number widens (positive) or narrows (negative) that axis's interval by that margin on both of its sides. `True`, `False` and a single number keep their CL-1 meaning and equal `(True, True)`, `(False, False)` and `(m, m)` |
| CP-2 | A line-like artist (`plot`, `line`, `plot_parametric_curve`, `plot_line_graph`'s line) with an axis not clipped samples and draws past the viewport on that axis, as `clip=False` does today: a function plot with `cx=False` covers its own `x_range` where one is given, past `[x0, x1]` (without one it covers the viewport, as today); an array line covers all its data; with `cy=False` its anchors reach past `[y0, y1]` wherever the curve does. On a clipped axis its anchors stay within that axis's interval, grown by the margin, and reach past the rectangle where the curve does and the margin allows, as in CL-1 |
| CP-3 | A scatter shows a point whose marker centre lies within the interval of every clipped axis; an axis not clipped never hides a point |
| CP-4 | A pole still splits the path, whatever either entry is (F-705). With `cy=False` a pole's tails are drawn as far as the sampler reaches them, as with `clip=False` today |
| CP-5 | Errors, each naming `clip`: a pair whose length is not 2 raises `ValueError`; an entry that is neither a `bool` nor a real number raises `TypeError` (so does a value that is none of a `bool`, a real number, a tuple and a list); a non-finite entry raises `ValueError`; a margin that narrows a clipped axis's interval to nothing raises `ValueError`. They are raised at construction and by `set_clip`, before anything changes |
| CP-6 | `artist.set_clip(value)` takes a pair, rebuilds and returns the artist; `artist.get_clip()` returns the value as given, a pair as a `tuple` *(default taken: a list given comes back as a tuple)*. `become` and `Morph` take the other artist's clip over, as they take a bool or a margin today |
| CP-7 | Per pair of axes it falls out of F-112: an artist belongs to one system, so each system's artists clip to that system's rectangle. Nothing to implement before task 19 |

## Tests

`tests/mobjects/test_style.py`, beside CL-1 and CL-2, on `axes()` (`x_range=(-3, 3)`,
`y_range=(-2, 2)`, lengths 6 and 4, so the rectangle is `[-3, 3] x [-2, 2]` in scene
units):

- CP-1: `(True, False)` on `2.3 sin x` reaches `|y| ≈ 2.3` and stays within `|x| <= 3`;
  `(False, True)` with `x_range=(-5, 5)` reaches `|x| ≈ 5` and stays within `|y| <= 2`;
  `(0.2, False)`; the three single values equal their pairs, point for point.
- CP-2: on a line, a parametric curve and `plot_line_graph`'s line, each entry alone.
- CP-3: points outside on x only, on y only, on both, under every pair.
- CP-4: `1 / (x - 0.5)` with `(True, False)` splits into two pieces.
- CP-5: each error, at construction and through `set_clip`, the artist unchanged after a
  refused `set_clip`.
- CP-6: read-back, a list returned as a tuple, `become` taking a pair over.
- A visual baseline `test_clip_per_axis`: `2.3 sin x` over `(-5, 5)` with
  `clip=(True, False)`, beside the same curve clipped on both axes. No Manim twin: Manim
  has no clipping.

No frame-cost reading: clipping per axis changes the clip rectangle, not the work per
frame.
