# Acceptance table — task 29, more plot types

**Status: Living until task 29 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §8 (value-mapped `scatter`, `stem`,
waterfall, `fill_between`, `bar3d`, error bars, `text`, `annotate` at a 3D point;
orthographic projection; growing and morphing surfaces); ADR 0004 §9 (customisation);
task 11b (MX-4: `Transform` adopts its target); task 18 (EB rows); task 24 (facing
text, FR-6); task 25 (colour mapping, `surface`); task 28 (`zdir`, the floor).

Modules: `mobjects/artists.py` (`c=`, `s=` on `ScatterPlot`), `mobjects/plots3d.py`
(new: `StemPlot`, `WaterfallPlot`, `BarPlot3D`, the 3D text and annotation),
`mobjects/errorbar.py` (by dimension), `mobjects/surfaces.py` (`GrowSurface`,
`Transform` between surfaces), `mobjects/three_d.py` (the methods, `view`).

```python
# on every system
def scatter(
    self,
    xs,
    ys=None,
    zs=None,
    *,
    c=None,
    s=None,
    colorscale=None,
    vmin=None,
    vmax=None,
    norm=None,
    **kwargs,
) -> ScatterPlot: ...


# on ThreeDAxes
def stem(self, x, y, z, *, bottom=0, orientation="z", **style) -> StemPlot: ...
def waterfall(
    self, x, curves, positions=None, *, zdir="y", fill=True, **style
) -> WaterfallPlot: ...
def fill_between(self, x1, y1, z1, x2, y2, z2, **style) -> SurfacePlot: ...
def bar3d(self, x, y, z, dx, dy, dz, color=None, shade=True, **style) -> BarPlot3D: ...
def errorbar(
    self, x, y, z, zerr=None, yerr=None, xerr=None, *, capsize=0.1, **kwargs
) -> ErrorBars: ...
def text(self, x, y, z, s, zdir=None, **kwargs) -> VMobject: ...
def annotate(self, s, xyz, xyztext=None, *, arrow=True, **kwargs) -> HelperGroup: ...
def view(self, elev=30, azim=-60, roll=0, proj_type="persp") -> dict: ...


class GrowSurface(Animation):  # mp.GrowSurface
    def __init__(self, surface, zdir="z", offset=None, **kwargs): ...
```

## VS — scatter by value (2D and 3D)

| ID | Row |
|---|---|
| VS-1 | `scatter(..., c=values)` colours marker `i` by a `ColorMapping` (task 25, CS-1's forms for `colorscale`, default `"viridis"` as matplotlib's) of `values[i]`; `vmin` and `vmax` default to the values' minimum and maximum, `norm` to linear. `scatter.color_mapping` is that mapping, so `ax.colorbar(scatter)` works (CB-1). A `c` that is one colour (a string or a `ManimColor`) colours every marker; values of another length than the points raise `ValueError` naming `c` |
| VS-2 | `s=` is the marker radius in scene units, a scalar or one value per point *(default taken: matplotlib's `s` is an area in points²)*; omitted, Manim's `Dot` radius. Another length raises `ValueError` naming `s` |
| VS-3 | Per-marker style is kept through re-derivation as AR-6; without `c` and `s` the scatter is task 11a's, unchanged |

## SM — stems

| ID | Row |
|---|---|
| SM-1 | `ax.stem(x, y, z, bottom=0, orientation="z")` (matplotlib's `Axes3D.stem`) is a `StemPlot` of `.stemlines` (one line per point from `(x, y, bottom)` to `(x, y, z)`), `.markers` (a `ScatterPlot` at `(x, y, z)`) and `.baseline` (a `LinePlot` through the bottoms in data order); `orientation="x"` or `"y"` lays them along that axis by ZD-1's juggling |
| SM-2 | Stem lines and markers take the next colour of the cycle; the baseline takes the axes' line colour, `stroke_width=1` *(default taken)*; each part styleable, kept through re-derivation; bound to ranges and moves, clipped to the box |

## WT — waterfall

| ID | Row |
|---|---|
| WT-1 | `ax.waterfall(x, curves, positions=None, zdir="y")` lays curve `k`, the polyline through `(x, curves[k])`, in the plane `positions[k]` of `zdir` (ZD-1); `positions` defaults to `range(len(curves))`. With `fill=True` each curve gets a polygon from it down to the floor (the low end of the axis it rises along) |
| WT-2 | A `WaterfallPlot` with `.lines[k]` (`LinePlot`s) and `.fills[k]` (`None` without fill); each curve takes the next colour of the cycle, fills `fill_opacity=0.5` in their line's colour *(default taken)*; bound and clipped as lines |

## FB — `fill_between` in 3D

| ID | Row |
|---|---|
| FB3-1 | `ax.fill_between(x1, y1, z1, x2, y2, z2)` (matplotlib 3.10's) is the band between the two polylines: a `SurfacePlot` of task 25's array kind with the 2 × n grid `[[p1_0 … p1_n], [p2_0 … p2_n]]`, so face `(0, j)` joins points `j` and `j + 1` of both lines. Lengths must match, else `ValueError` naming `x2`. The next colour of the cycle at `fill_opacity=0.5` *(default taken)* |

## BR — 3D bars

| ID | Row |
|---|---|
| BR-1 | `ax.bar3d(x, y, z, dx, dy, dz)` (matplotlib's) draws bar `i` as the box with corner `(x, y, z)[i]` and sides `(dx, dy, dz)[i]` (each a scalar or an array), six faces in matplotlib's order: bottom, top, −y, +y, −x, +x. A `BarPlot3D`: `bars[i]` a `VGroup` of its six faces, each a `VMobject` styleable on its own |
| BR-2 | `shade=True` darkens each face as matplotlib's `_shade_colors`: its colour times `0.3 + 0.35 (1 + n · L)`, `n` the face's outward normal in data, `L = (−2, −2, 1) / 3` (matplotlib's default light, azimuth 225°, altitude 19.47°); Manim's camera shading is off for the faces either way. `color` one colour for every bar or one per bar; omitted, the next colour of the cycle |
| BR-3 | Bars are bound to ranges and moves; a bar's faces are cut to the box as surface faces are (SK-1) |

## EB — error bars in 3D

| ID | Row |
|---|---|
| EB3-1 | `ax.errorbar(x, y, z, zerr=None, yerr=None, xerr=None)` on a `ThreeDAxes` (matplotlib's argument order) is task 18's `ErrorBars` by dimension: errors as EB-2 per axis, bars as data segments (EB-3), parts `markers`, `line`, `xbars`, `ybars`, `zbars`, `xcaps`, `ycaps`, `zcaps`, colours as EB-6, clipping as EB-7, `set_data(x, y, z, zerr=…, yerr=…, xerr=…)` as ED-1 |
| EB3-2 | Caps are `capsize` long in scene units (EB-4's default 0.1), centred on each bar end, perpendicular to their bar and lying in the plane that faces the camera most (as VT-4's flat arrows), turned on frames where the camera moved |

## TX — text and annotations at a 3D point

| ID | Row |
|---|---|
| TX-1 | `ax.text(x, y, z, s)` places `Text(s)` (or `s` itself when it is a `Mobject`) centred at the data point and returns it; it follows ranges and moves as an artist. With `zdir=None` it faces the camera and reads upright on screen (FR-6's turn); `zdir="x"`, `"y"` or `"z"` turns it, still facing the camera, so its baseline runs along that axis's direction on screen (matplotlib's meaning) |
| TX-2 | `ax.annotate(s, xyz, xyztext=None)` is a `HelperGroup` of `.text` and `.arrow`: the text centred at the data point `xyztext`, or, when omitted, 0.6 scene units right of and 0.6 above the point on screen *(default taken)*; the arrow a flat camera-facing arrow (VT-4) from the text's edge to the point, its tip on the point. Both follow ranges, moves and the camera; inputs take task 26's data-point forms; `arrow=False` draws no arrow |

## PJ — orthographic projection

| ID | Row |
|---|---|
| PJ-1 | `ax.view(elev, azim, roll, proj_type="ortho")` adds `focal_distance=1e6` to the camera keywords, so `ThreeDCamera` projects parallel lines to parallel lines (within `1e-4` on screen); `proj_type="persp"` adds nothing (Manim's focal distance) *(default taken: matplotlib's names)*. Any other value raises `ValueError` naming `proj_type` |

## GM — growing and morphing surfaces

| ID | Row |
|---|---|
| GM-1 | `Create`, `FadeIn` and `FadeOut` on a `SurfacePlot` run as on Manim's `Surface` and end with every face as before |
| GM-2 | `mp.GrowSurface(surface, zdir="z", offset=None)` raises the surface from the plane `zdir = offset`: on every frame each face point's `zdir` data coordinate is `o + α (v − o)`, `α` the rate function's value and `v` the final value, the other two coordinates final; `offset=None` is the low end of the `zdir` range *(default taken)*. Colours are the final ones throughout. After it the surface is its bound self, with no updater left, and follows a later range change |
| GM-3 | `Transform(a, b)` and `ReplacementTransform(a, b)` between two `SurfacePlot`s: faces are aligned as Manim aligns two `VGroup`s, so on every frame `a`'s faces equal plain twins' under the same animation; afterwards `a` adopts `b` (MX-4, F-905): it draws `b`'s function and colour rule, and a later range change re-derives it as `b` |

## Frame cost

Readings (p95 of `update`, ms) for the report: 500 value-coloured markers under
`ax.animate.set_z_range`; 100 bars under `move_camera`; `GrowSurface` on a 32 × 32
surface. F-1001 is unchanged.
