# Acceptance table — task 37, heatmaps

**Status: Living until task 37 merges, then Record.** Written 2026-10-31 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0007 §1-§2; ADR 0004 §9; task 21 (marching
squares in `core/shape.py`); task 25 (`ColorMapping`, `colorbar`, CS-1's colorscale
forms).

Modules: `mobjects/heatmaps.py` (new: `HeatmapPlot`, `HexbinPlot`, `ContourSetPlot`),
`core/shape.py` (filled marching squares), `mobjects/system.py` (the methods),
`src/manim_plots/__init__.py`.

```python
# on CartesianAxes (2D)
def imshow(
    self,
    Z,
    *,
    extent=None,
    origin="upper",
    colorscale="viridis",
    vmin=None,
    vmax=None,
    norm=None,
    **style,
) -> HeatmapPlot: ...
def pcolormesh(
    self,
    X,
    Y=None,
    C=None,
    *,
    shading="auto",
    colorscale="viridis",
    vmin=None,
    vmax=None,
    norm=None,
    **style,
) -> HeatmapPlot: ...
def hist2d(
    self,
    x,
    y,
    bins=10,
    *,
    range=None,
    density=False,
    weights=None,
    cmin=None,
    cmax=None,
    colorscale="viridis",
    **style,
) -> HeatmapPlot: ...
def hexbin(
    self,
    x,
    y,
    C=None,
    *,
    gridsize=10,
    reduce_C_function=np.mean,
    mincnt=None,
    extent=None,
    colorscale="viridis",
    **style,
) -> HexbinPlot: ...
def contour(
    self, X, Y, Z, levels=None, *, colorscale=None, **style
) -> ContourSetPlot: ...
def contourf(
    self, X, Y, Z, levels=None, *, colorscale="viridis", **style
) -> ContourSetPlot: ...


class HeatmapPlot(VGroup):  # mp.HeatmapPlot
    cells: FaceGroup  # .at((i, j)), row i, column j
    color_mapping: ColorMapping

    def set_data(self, C) -> Self: ...
    def label_cells(
        self, fmt="{:.2g}", colors=("black", "white"), threshold=None, **text_style
    ) -> VGroup: ...
```

## HM — `imshow` and `pcolormesh`

| ID | Row |
|---|---|
| HM-1 | `ax.imshow(Z)` draws one cell per value of the 2D array `Z` (`m` rows, `n` columns): by default cell `(i, j)` is the unit square centred on `(j, m − 1 − i)` with `origin="upper"` (row 0 at the top, matplotlib's), `(j, i)` with `origin="lower"`; `extent=(left, right, bottom, top)` stretches the grid onto that rectangle (with `origin="upper"` row 0 at `top`). It does not change the axes' ranges *(default taken: matplotlib resets them; here ranges are the user's)* |
| HM-2 | `ax.pcolormesh(X, Y, C)`: `X`, `Y` 2D corner grids of shape `(m + 1, n + 1)` or 1D edges of lengths `n + 1`, `m + 1`, and `C` of shape `(m, n)`, cell `(i, j)` the quadrilateral of corners `(i, j)`, `(i, j + 1)`, `(i + 1, j + 1)`, `(i + 1, j)`; with `X`, `Y` of the same shape as `C`, `shading="nearest"` (and `"auto"`) centres the cells on the points, edges halfway between them (matplotlib's) |
| HM-3 | Each cell is a filled polygon of its corners mapped by the system (straight edges), coloured through a `ColorMapping` of its value (CS-1's forms, default `"viridis"`; `vmin`, `vmax` default the finite values' extremes; `norm`), no stroke, fill opacity 1 *(default taken)*. `plot.color_mapping` makes `ax.colorbar(plot)` work. A `NaN` value draws no cell (it keeps its place, empty) |
| HM-4 | `plot.cells.at((i, j))` reaches a cell; a cell's own style is kept through re-derivation; `set_data(C)` (same shape) recolours the cells in place, and with `vmin`/`vmax` left to the data the mapping follows the new extremes |
| HM-5 | Cells are bound (ranges, animated, and moves) and clipped to the viewport as bars are (BA-5) |
| HM-6 | `plot.label_cells(fmt="{:.2g}")` puts `Text(fmt.format(value))` centred in every non-empty cell, `colors[0]` on light cells and `colors[1]` on dark ones: dark when the cell colour's relative luminance is below `threshold` (default 0.5) *(default taken: matplotlib's annotated-heatmap example)*; the labels follow the cells and `set_data` |

## HX — `hist2d` and `hexbin`

| ID | Row |
|---|---|
| HX-1 | `ax.hist2d(x, y, bins, range, density, weights)` is `numpy.histogram2d` with matplotlib's arguments drawn as `pcolormesh(xedges, yedges, counts.T)`: cell `(i, j)` covers y bin `i` and x bin `j`; cells with a count below `cmin` or above `cmax` are empty. Returns the `HeatmapPlot` with `plot.counts`, `plot.xedges`, `plot.yedges` |
| HX-2 | `ax.hexbin(x, y, C=None, gridsize=10)` bins the points into hexagons on matplotlib's two interleaved lattices (`gridsize` hexagons across the x extent); a cell's value is its count, or `reduce_C_function` of its `C` values; cells with fewer than `mincnt` points are omitted. Every point inside `extent` falls in exactly one drawn hexagon that contains it, so the counts sum to the number of points. Returns a `HexbinPlot` (`cells`, `color_mapping`, `values`, `centers`) |

## CT — `contour` and `contourf` on arrays

| ID | Row |
|---|---|
| CT2-1 | `ax.contour(X, Y, Z, levels)` draws the level lines of the gridded `Z` by marching squares (task 21's), one `VMobject` per level, `ContourSetPlot.at(level)`; `levels` as CT-2 (a sequence, a count `n` giving `n` nice levels inside the data's range, `None` giving 7) |
| CT2-2 | `ax.contourf(X, Y, Z, levels)` fills the bands between consecutive levels: band `k` (`levels[k] ≤ z < levels[k + 1]`) is one `VMobject` of closed paths, built by filled marching squares on each grid cell (each cell's polygon cut by the two levels, linearly interpolated on its edges), one closed subpath per grid cell that the band touches (cells are not merged, so no subpath is a hole), so the bands tile the grid's area with no gap or overlap within `1e-9`; band colours from the mapping at the band's middle value; `ContourSetPlot.at(k)` |
| CT2-3 | Both are bound and clipped as curves; both have `color_mapping` |

## Frame cost

Readings (p95 of `update`, ms) for the report: a 50 × 50 `imshow` under an animated
range; a 50 × 50 `set_data` per frame from a tracker; a `contourf` of 100 × 100 with 10
levels under an animated range. F-1001 is unchanged.
