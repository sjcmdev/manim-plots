# Acceptance table — task 28, slices and projections

**Status: Living until task 28 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §8 (slices, `plot_slice` on a linked 2D
`mp.Axes` following a tracker, shadows on the panes, matplotlib's `zdir`); task 16
(HB-2: bound numbers); task 24 (panes, FR-3); task 25 (surfaces, CT rows: contours,
`offset="pane"`); task 26 (planes, intersections).

Modules: `mobjects/surfaces.py` (`slice`), `mobjects/projections.py` (new: the shadow
artists), `mobjects/system.py` (`plot_slice` on 2D systems), `mobjects/three_d.py`
(`shadow`, `zdir`).

```python
# on SurfacePlot
def slice(self, *, x=None, y=None, z=None, **style) -> ParametricPlot | ContourPlot: ...


# on CartesianAxes (2D)
def plot_slice(self, surface, *, x=None, y=None, **style) -> FunctionPlot: ...


# on ThreeDAxes
def shadow(
    self, artist, zdir="z", offset=None, **style
) -> ParametricPlot | ScatterPlot: ...
def plot(self, function, x_range=None, *, zs=0, zdir="z", **kwargs) -> FunctionPlot: ...
def scatter(self, xs, ys=None, zs=None, *, zdir="z", **kwargs) -> ScatterPlot: ...
def line(self, xs, ys=None, zs=None, *, zdir="z", **kwargs) -> LinePlot: ...
```

## SC — slices of a surface

| ID | Row |
|---|---|
| SC-1 | On a surface from `plot_surface` (z over x and y), `surface.slice(x=c)` is a `ParametricPlot` of `t ↦ (c, t, f(c, t))` over the surface's y range, sampled as a curve, so it lies on the surface exactly: every anchor's `z` equals `f(x, y)` within `1e-9` and its `x` equals `c`. `slice(y=c)` likewise along x |
| SC-2 | `slice(z=c)`, and every slice of the other surface kinds (parametric, revolution, `surface`, `plot_trisurf`), is the `ContourPlot` of one level `c` of that coordinate: CT-1's construction (`surface.contour([c], zdir=...)`) |
| SC-3 | Exactly one of `x`, `y`, `z`, else `ValueError` naming `slice`. `c` takes HB-2's forms (a tracker, a callable); a value outside the surface's range at the call raises `ValueError` naming the coordinate; during an animation the slice is empty on that frame and comes back (HB-7) |
| SC-4 | A slice is bound to its surface: it re-derives in the same frame when the surface does (its parameters, a range change, a move), and when `c` changes. Style: the next colour of the cycle and a plot's stroke *(default taken)*; `label=` puts it in the legend |

## PS — `plot_slice` on a linked 2D system

| ID | Row |
|---|---|
| PS-1 | `ax2d.plot_slice(surface, x=c)` on a 2D system draws `y ↦ f(c, y)` as a `FunctionPlot` over the surface's y range (`y=c`: `x ↦ f(x, c)` over its x range), so the 2D graph shows the profile that `surface.slice(x=c)` traces on the surface: at the same y the two values agree within `1e-9` |
| PS-2 | It is bound to `c` (HB-2) and to the surface's function parameters: a tracker moved during an animation redraws the profile on that frame, with no `always_redraw` |
| PS-3 | Only a surface from `plot_surface` has a profile: other kinds raise `TypeError` naming `plot_surface`. `plot_slice` on a `ThreeDAxes` raises `NotImplementedError` naming `ThreeDAxes`. Exactly one of `x`, `y`, else `ValueError` naming `plot_slice` |

## SH — shadows on the panes

| ID | Row |
|---|---|
| SH-1 | `ax.shadow(artist, zdir="z", offset=None)` is the artist's drawn data with the `zdir` coordinate replaced by `offset`, its other two kept: a curve artist (`plot`, `plot_parametric_curve`, `line`, `axline`, `segment`, a slice) gives a `ParametricPlot` through the same data points; a `ScatterPlot` gives a `ScatterPlot`. Anything else raises `TypeError` naming the artist's type |
| SH-2 | `offset=None` is `"pane"` in `frame="box"` — the `zdir` pane's current side, moving when the pane changes sides (FR-3, as CT-3) — and the low end of the `zdir` range in `frame="origin"` *(default taken)*; a number or a tracker puts it there; `"pane"` in `frame="origin"` raises `ValueError` naming `offset` |
| SH-3 | A shadow is bound to its artist: it re-derives in the same frame when the artist does (its parameters, its data, a range change, a move) and when the pane changes sides |
| SH-4 | Style: the artist's colour at `stroke_opacity=0.35` for curves and `fill_opacity=0.35` for markers, so it reads as a shadow *(default taken)*; any style keyword overrides it; clipped to the box as a curve |

## ZD — matplotlib's `zdir`

| ID | Row |
|---|---|
| ZD-1 | `ax.plot(f, zs=c, zdir="y")` lays the 2D graph in the plane `y = c`: matplotlib's `juggle_axes`, so 2D `(u, v)` goes to `(u, c, v)` for `zdir="y"`, `(c, u, v)` for `"x"`, `(u, v, c)` for `"z"`. `zs=0`, `zdir="z"` are the defaults, TA-5's picture. `zs` takes HB-2's forms |
| ZD-2 | `scatter(xs, ys, zs=c, zdir=...)` and `line(xs, ys, zs=c, zdir=...)` take a scalar `zs` broadcast to every point, or an array, laid by the same rule; with `zs` omitted it is 0 |
| ZD-3 | `zdir` other than `"x"`, `"y"`, `"z"` raises `ValueError` naming `zdir` |

## Frame cost

Readings (p95 of `update`, ms) for the report: a 32 × 32 surface with `slice(x=t)` and
`plot_slice(surface, x=t)` on a 2D axes under an animation of `t`; a helix with three
shadows under `move_camera` in `frame="box"`. F-1001 is unchanged.
