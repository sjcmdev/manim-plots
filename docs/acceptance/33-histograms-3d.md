# Acceptance table — task 33, histograms and bars in 3D

**Status: Record (merged 2026-10-31).** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1-§2 (coloured 3D histograms asked for by
name); task 29 (BR rows: `bar3d`, matplotlib's shading); task 28 (ZD-1: `zs`, `zdir`);
task 31 (`BarPlot`); task 32 (`HistPlot`, HI rows); task 25 (`ColorMapping`).

Modules: `mobjects/plots3d.py` (`hist3d`, colour by value on `BarPlot3D`),
`mobjects/three_d.py` (the methods), `mobjects/bars.py` and `mobjects/histograms.py`
(the 3D lay-out of 2D bars), `src/manim_plots/__init__.py`.

```python
# on ThreeDAxes
def hist3d(
    self,
    x,
    y,
    bins=10,
    *,
    range=None,
    density=False,
    weights=None,
    rwidth=0.8,
    cmin=1,
    color=None,
    color_by="count",
    colorscale="viridis",
    vmin=None,
    vmax=None,
    norm=None,
    shade=True,
    **style,
) -> Hist3DPlot: ...
def bar3d(
    self,
    x,
    y,
    z,
    dx,
    dy,
    dz,
    color=None,
    shade=True,
    *,
    c=None,
    colorscale=None,
    vmin=None,
    vmax=None,
    norm=None,
    **style,
) -> BarPlot3D: ...
def bar(self, left, height, zs=0, zdir="z", *, width=0.8, **kwargs) -> BarPlot: ...
def hist(self, x, bins=10, *, zs=0, zdir="y", **kwargs) -> HistPlot: ...


class Hist3DPlot(BarPlot3D):  # mp.Hist3DPlot
    counts: ndarray  # (nx, ny), numpy.histogram2d's
    xedges: ndarray
    yedges: ndarray

    def at(self, key: tuple[int, int]) -> VGroup: ...  # bar of x bin i, y bin j
    def set_data(self, x, y, *, weights=None) -> Self: ...
```

## H3 — `hist3d`

| ID | Row |
|---|---|
| H3-1 | `ax.hist3d(x, y, bins, range, density, weights)` counts with `numpy.histogram2d` (its argument meanings) and draws bin `(i, j)` (x bin `i`, y bin `j`) as a `bar3d` column on the floor `z = 0` (the low end of the z range if 0 is outside it), centred in its cell and `rwidth` of the cell's width and depth, `counts[i, j]` high: matplotlib's 3D histogram example as one call. Bins with a count below `cmin` (1 by default: empty bins) draw no bar *(default taken)* |
| H3-2 | Colour by value: `color_by="count"` (default) colours every face of bar `(i, j)` through a `ColorMapping` of its count (`vmin`, `vmax` default the drawn counts' extremes; CS-1's colorscale forms, default `"viridis"`), then BR-2's shading multiplies it per face (`shade=False` leaves the mapped colour); `color_by="x"` / `"y"` maps the bin's centre along that axis; `color=` one colour for all (no mapping). `plot.color_mapping` makes `ax.colorbar(plot)` work |
| H3-3 | `plot.at((i, j))` reaches a bar (a `VGroup` of six faces, BR-1's order); a face's own style is kept through re-derivation; `plot.set_data(x, y)` re-counts into the same edges and rewrites the bars in place (bars of bins that become empty lose their points, bins that fill get them back); bound to ranges and moves, cut to the box (BR-3) |
| H3-4 | Draw order: the faces of a `BarPlot3D` (so of `bar3d`, `hist3d` and, later, voxels) are drawn far to near, by the camera-space depth of each face's centre (matplotlib's `zsort="average"`), re-sorted on frames where the camera turned or the bars changed; Manim's camera shading stays off. Test: in a `ThreeDScene` at `phi=65°, theta=−50°`, the faces in the camera's display order have non-decreasing depth *(review: an 8 × 8 histogram drew rear bars over front ones)* |

## B3 — colour by value on `bar3d`, 2D bars and histograms in planes

| ID | Row |
|---|---|
| B3-1 | `bar3d(..., c=values)` or `c="height"` (the `dz`) colours bar `i` through a `ColorMapping` (as H3-2, default `"viridis"`), shaded per face by BR-2; `plot.color_mapping` |
| B3-2 | `ax.bar(left, height, zs=0, zdir="z", width=0.8)` on a `ThreeDAxes` is matplotlib's `Axes3D.bar`: the 2D bars of task 31 laid in the plane `zdir = zs` by ZD-1's juggling (2D `(u, v)` to `(u, zs, v)` for `zdir="y"`), each a flat filled rectangle; `zs` a scalar or one per bar; colour by value as BA-4 |
| B3-3 | `ax.hist(x, bins, zs=0, zdir="y")` on a `ThreeDAxes` is task 32's histogram laid the same way; several calls with different `zs` give matplotlib's "histograms in planes" picture. HI rows hold (colour by count or by x, `set_data`) |

## Frame cost

Readings (p95 of `update`, ms) for the report: a 10 × 10 `hist3d` under `move_camera`;
the same with `set_data` from a growing sample every frame. F-1001 is unchanged.
