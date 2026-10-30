# Acceptance table — task 25, surfaces and colour

**Status: Living until task 25 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §2, §3, §8; ADR 0004 §9 (customisation);
task 24 (the 3D system, clipping to the box, panes). Coordinates (`coords=`) are task
26; morphing and growing are task 29; occlusion is task 30.

Modules: `mobjects/surfaces.py` (new: the surface artists, contours), `core/colormaps.py`
(new: `Colormap`, `ColorMapping`, the named tables), `mobjects/colorbar.py` (new),
`mobjects/three_d.py` (the methods), `mobjects/fields.py` (`color_mapping`, CB-4),
`src/manim_plots/__init__.py`.

```python
# on ThreeDAxes
def plot_surface(
    self, function, u_range=None, v_range=None, colorscale=None, colorscale_axis=2,
    *, resolution=32, vmin=None, vmax=None, norm=None, clip=True, **kwargs,
) -> SurfacePlot: ...                      # z = function(x, y); Manim's signature first
def plot_parametric_surface(
    self, function, u_range, v_range, colorscale=None, colorscale_axis=2, *,
    resolution=32, vmin=None, vmax=None, norm=None, clip=True, **kwargs,
) -> SurfacePlot: ...                      # (x, y, z) = function(u, v)
def plot_surface_of_revolution(
    self, function, t_range=None, axis="z", angle_range=(0, TAU), colorscale=None,
    colorscale_axis=2, *, resolution=32, vmin=None, vmax=None, norm=None, clip=True,
    **kwargs,
) -> SurfacePlot: ...                      # radius = function(t) about axis
def surface(self, X, Y, Z, colorscale=None, colorscale_axis=2, *, vmin=None, vmax=None,
            norm=None, clip=True, **kwargs) -> SurfacePlot: ...   # grids, shape (m, n)
def plot_trisurf(self, x, y, z, triangles=None, colorscale=None, colorscale_axis=2, *,
                 vmin=None, vmax=None, norm=None, clip=True, **kwargs) -> SurfacePlot: ...
def plot_wireframe(self, function, u_range=None, v_range=None, *, resolution=10,
                   clip=True, **kwargs) -> WireframePlot: ...     # z = function(x, y)
def colorbar(self, mappable=None, *, colorscale=None, vmin=None, vmax=None, norm=None,
             label=None, length=None, width=0.25, buff=MED_SMALL_BUFF, **kwargs
) -> Colorbar: ...                         # also on CartesianAxes (2D)

class SurfacePlot(VGroup):
    faces: FaceGroup                       # .at((i, j)) for grids, .at(k) for triangles
    color_mapping: ColorMapping | None
    def set_colorscale(self, colorscale, colorscale_axis=2, *, vmin=None, vmax=None,
                       norm=None) -> Self: ...
    def set_fill_by_checkerboard(self, *colors, opacity=None) -> Self: ...  # Manim's
    def set_fill_by_value(self, axes, colorscale=None, axis=2, **kwargs) -> Self: ...
    def contour(self, levels=None, *, zdir="z", offset=None, colorscale=None,
                **kwargs) -> ContourPlot: ...

class WireframePlot(VGroup):
    u_lines: VGroup                        # .at(u): the line of constant u
    v_lines: VGroup                        # .at(v)

class ContourPlot(VGroup):                 # .at(level): one VMobject per level
    levels: tuple[float, ...]

class Colormap:                            # mp.Colormap
    def __init__(self, colors, positions=None, name=None): ...
    def __call__(self, t) -> np.ndarray: ...   # t in [0, 1], scalar or array -> (..., 3) rgb
colormaps: dict[str, Colormap]             # mp.colormaps

class ColorMapping:                        # mp.ColorMapping, what a colorbar reads
    colormap: Colormap
    vmin: float
    vmax: float
    scale: Scale
    def __call__(self, values) -> np.ndarray: ...  # (..., 3) rgb

class Colorbar(CartesianAxes):             # mp.Colorbar
    axis: Axis                             # the numbered axis (bar.y)
    strip: VGroup                          # the coloured cells, bottom to top
```

## SF — surfaces

| ID | Row |
|---|---|
| SF-1 | `ax.plot_surface(f, u_range, v_range)` on a `ThreeDAxes` draws Manim's surface: `resolution` (an int or a `(u, v)` pair, default 32, Manim's) cells per direction, face `(i, j)` the cell `[u_i, u_{i+1}] × [v_j, v_{j+1}]` of `np.linspace(*u_range, n_u + 1)` (Manim's order: `i` over u outer, `j` over v inner); each face's points are Manim's, the uv cell's outline as `set_points_as_corners` gives it (16 points), every point mapped by `(u, v) -> c2p(u, v, f(u, v))`. On Manim's defaults and a surface inside the box, every face's points equal Manim's `ThreeDAxes().plot_surface` within `1e-9` |
| SF-2 | Manim's defaults: checkerboard `BLUE_D`, `BLUE_E` by `(i + j) % 2`, `fill_opacity=1`, `stroke_color=LIGHT_GREY`, `stroke_width=0.5`; every `Surface` keyword (`fill_color`, `fill_opacity`, `checkerboard_colors`, `stroke_color`, `stroke_width`, `should_make_jagged`) keeps its meaning. `u_range` and `v_range` default to the x and y ranges (Manim raises `TypeError`); a default range follows `set_x_range` / `set_y_range`, an explicit one does not |
| SF-3 | `plot_parametric_surface(f, u_range, v_range)` with `f(u, v) -> (x, y, z)` in data; both ranges are required (`ValueError` naming `u_range` or `v_range`) |
| SF-4 | `plot_surface_of_revolution(f, t_range, axis)` turns the radius `f(t)` about the axis: for `axis="z"` the point `(f(t) cos φ, f(t) sin φ, t)`, for `"x"` `(t, f(t) cos φ, f(t) sin φ)`, for `"y"` `(f(t) sin φ, t, f(t) cos φ)`; u is `t`, v is `φ` over `angle_range`; `t_range` defaults to the range of `axis` |
| SF-5 | `ax.surface(X, Y, Z)` takes three grids of one shape `(m, n)` (matplotlib's `plot_surface` arrays): `(m - 1)(n - 1)` faces, face `(i, j)` with the corners `[i, j]`, `[i + 1, j]`, `[i + 1, j + 1]`, `[i, j + 1]`, straight between them; shapes that differ raise `ValueError` naming `Z` |
| SF-6 | `ax.plot_trisurf(x, y, z, triangles=None)`: one triangular face per triangle, from `scipy.spatial.Delaunay` of `(x, y)` when `triangles` is `None`, else the given `(k, 3)` index array as is; face `k` is `faces.at(k)`. The checkerboard is off for triangles: `fill_color` (default `BLUE_D`) |
| SF-7 | A face with a non-finite corner is a hole: it keeps its place in `faces` with no points *(default taken)* |
| SF-8 | On a 2D `CartesianAxes`, every surface method raises `NotImplementedError` naming `ThreeDAxes` *(default taken)* |

## CS — colour by value

| ID | Row |
|---|---|
| CS-1 | `colorscale` takes Manim's list of colours (evenly spaced), Manim's list of `(colour, pivot)` pairs, a name of `mp.colormaps`, an `mp.Colormap`, or any callable `t -> rgb or rgba` with `t` in `[0, 1]` (so `matplotlib.colormaps["turbo"]` works without the library importing matplotlib) |
| CS-2 | `colorscale_axis` is `0`, `1`, `2`, `"x"`, `"y"`, `"z"`, or a callable `(x, y, z) -> value` in data *(ADR 0004 §9's hook)*. A face's value is taken at its uv centre: the surface's point at `((u_i + u_{i+1}) / 2, (v_j + v_{j+1}) / 2)` for function surfaces, the mean of its corners' data points for `surface` and `plot_trisurf`; its coordinate on the axis, or the callable at it. *(Manim colours a face by the point half way along its outline, which is its far corner `(u_{i+1}, v_{j+1})`: a half-cell shift; fixed)* |
| CS-3 | `vmin` and `vmax` default to the range of `colorscale_axis` when it is an axis (Manim's), to the minimum and maximum of the faces' values when it is a callable; with pivots they are the first and last pivot, and an explicit `vmin` or `vmax` with pivots raises `ValueError` naming both. `norm` is `"linear"`, `"log"`, `"symlog"` or a `Scale` (task 15's scales), default the axis's scale, linear for a callable; `t = (S(value) - S(vmin)) / (S(vmax) - S(vmin))` clamped to `[0, 1]`. Colours are interpolated linearly in RGB between stops |
| CS-4 | A colour by value sets each face's fill and, unless `stroke_color` was passed, its stroke (as Manim's `set_color` does); `surface.color_mapping` is the `ColorMapping` in force, `None` for the checkerboard |
| CS-5 | Bound: when a range of the axes or a tracker the function reads changes, the values, and with an axis-range default `vmin` / `vmax`, the colours are re-derived on that frame. A face the user styled after creation (`set_fill`, `set_color`, `set_style` on the face) keeps that style through re-derivation; `set_colorscale`, `set_fill_by_checkerboard` and `set_fill_by_value` replace the surface's colour rule and clear those marks *(default taken)* |
| CS-6 | `mp.colormaps` holds `viridis`, `plasma`, `inferno`, `magma`, `cividis`, `coolwarm`, `RdBu_r`, `gray` as the 17 stops of the appendix (matplotlib's at `t = k / 16`), each also `name + "_r"` reversed; `mp.Colormap(colors, positions)` takes Manim colours and increasing positions from 0 to 1 (default evenly spaced); `Colormap(t)` takes a scalar or an array |

## SK — clipping and following

| ID | Row |
|---|---|
| SK-1 | Surfaces are clipped to the box by default as task 24's curves (TK-1, TK-2): each face is cut against the box planes (Sutherland-Hodgman on its corners, in the axes' scaled coordinates before the affine map), so the cut lies on the box face within `1e-9`; a face entirely outside keeps its place with no points; a cut face's outline is straight between its corners. `clip=False` draws it whole, `clip=(x, y, z)` per axis |
| SK-2 | Faces, their count and their order are stable under re-derivation: points are rewritten in place (`set_points`), so `faces.at((i, j))` is the same mobject before and after |
| SK-3 | A surface follows the axes' affine moves and `set_x_range`, `set_y_range`, `set_z_range`, animated, on every frame, as task 24's curves (TF-1, TF-3); a still surface costs nothing per frame |
| SK-4 | Each face is its own `VMobject` in the family, so `ThreeDCamera` sorts and shades faces as it does Manim's *(depth across artists: task 30)* |

## WF — wireframes

| ID | Row |
|---|---|
| WF-1 | `ax.plot_wireframe(f, u_range, v_range, resolution=10)` draws `n_u + 1` lines of constant u and `n_v + 1` of constant v at `np.linspace(*u_range, n_u + 1)` (and v), each an adaptive 3D curve of task 24 (TC-1) through `(u, v, f(u, v))`, clipped and following as curves; `u_lines.at(u)` and `v_lines.at(v)` address them. Colour: the next colour of the cycle, as a curve's *(matplotlib's)* |

## CT — contours

| ID | Row |
|---|---|
| CT-1 | `surface.contour(levels, zdir="z")` draws the level lines of the surface's `zdir` coordinate on the surface: marching squares (task 21's `marching_squares`) over the uv grid of face corners, each crossing point mapped by the surface function at its uv point, so it lies on the surface; for `surface` and `plot_trisurf` the crossing is interpolated linearly between corners. One `VMobject` per level, `contour.at(level)`, possibly several pieces |
| CT-2 | `levels`: a sequence of values; an int `n` gives `np.linspace(lo, hi, n + 2)[1:-1]` of the values' range; `None` gives the `zdir` axis's major tick values strictly inside that range *(default taken)* |
| CT-3 | `offset=c` lays every line in the plane `zdir = c` (its other two coordinates kept): matplotlib's projected contours; `offset="pane"` lays them on the `zdir` pane of a `frame="box"` system and moves them when the pane changes sides (task 24, FR-3); `"pane"` in `frame="origin"` raises `ValueError` naming `offset` |
| CT-4 | Colour: `color=` sets one colour; otherwise, when the surface has a colour mapping on the same axis as `zdir`, each level takes that mapping's colour at the level *(matplotlib's)*; otherwise the axes' line colour. `colorscale=` takes CS-1's forms over the levels' range |
| CT-5 | A contour is bound as the surface: it re-derives with it, is clipped as a curve, follows moves |

## CB — the colorbar (in 2D and 3D)

| ID | Row |
|---|---|
| CB-1 | `ax.colorbar(mappable)` reads `mappable.color_mapping`; `ax.colorbar(colorscale=..., vmin=..., vmax=..., norm=...)` builds one without a mappable (both raise `ValueError` when neither or both are given). The bar is an `mp.Colorbar`, a `CartesianAxes` whose y axis is the value axis on the mapping's scale (`y_range = (vmin, vmax)`, `y_scale` = the mapping's), placed on the right (`set_position("right")`), numbered by task 10's locator and formatter; the x axis is hidden. `bar.axis` is `bar.y`, with every control of task 10 |
| CB-2 | `bar.strip` is 64 cells *(default taken)* stacked bottom to top, cell `k` filled with the mapping's colour at the centre of its value interval (in the scale's space), no stroke; `width=0.25`, `length` defaults to the axes' `y_length` in 2D and `z_length` in 3D, label via `label=` as task 10's axis label |
| CB-3 | Placement: in 2D, the strip's left edge is `buff` right of the axes' right edge (`ax.get_right()`), its centre at the axes' centre height, kept there on every frame the axes move *(default taken)*. In a `ThreeDScene`, the bar is added to the camera's fixed-in-frame mobjects on its first frame (TF-5's mechanism) and placed at `RIGHT * (config.frame_width / 2 - 1)` |
| CB-4 | Bound: when the mapping changes (a range change of the surface's colour axis, `set_colorscale`), the bar's range and colours follow on that frame, animated with the change. `ArrowVectorField` and `StreamLines` gain `color_mapping` (their `colors` evenly spaced, `min_color_scheme_value`, `max_color_scheme_value`, linear), so `ax.colorbar(field)` works in 2D |

## Frame cost

Readings, p95 of `update` in ms: a 32 × 32 `plot_surface` with a colorscale under
`ax.animate.set_z_range`; the same surface under `move_camera` with the camera still for
the axes (a still surface must cost nothing); a `"pane"` contour under `move_camera`.

## Defects fixed (probed on 0.21.0, 2026-10-30)

Manim's `plot_surface` without `u_range` raises `TypeError: Value after * must be an
iterable, not NoneType`; it colours each face by its far corner (a probe of `u + v` on
`[0, 2]²` at resolution 2 colours face `(0, 0)` by the value 2, not its centre's 1); a
surface keeps its points when the axes change (no range can change); nothing is clipped
(`z = 9` on the defaults is drawn at scene `z = 7.31`, past the box's `3.25`); a colour
scale is a list of colours only, linear only, with no colorbar.

## Tests

`tests/mobjects/test_surfaces.py`: SF-1 parity with Manim's faces point for point; the
defaults; default ranges; parametric, revolution, arrays, trisurf against analytic
points; holes; the refusal in 2D; CS colours at uv centres against `interpolate_color`
by hand, pivots, names (against the appendix, `3 / 255`), a callable colormap, a
callable axis, `vmin` / `vmax` and `norm="log"`; CS-5 a styled face kept; SK clipping on
the box planes and `clip=False`, stable faces, following an animated `set_z_range`;
WF lines on the surface; CT levels, lines on the surface, `offset` and `"pane"`;
`tests/mobjects/test_colorbar.py`: CB in 2D and 3D, bound to a surface's range, a field.
Visual (`tests/visual/test_surface_pictures.py`, camera at `phi = 65°`, `theta = -45°`):
`test_surface_saddle` and its `__manim` twin, `test_surface_viridis_colorbar`,
`test_surface_clipped`, `test_trisurf`, `test_wireframe`, `test_surface_of_revolution`,
`test_contours_on_the_pane`, `test_colorbar_2d`.

## Appendix — the colormap stops (matplotlib 3.10, `to_hex(cmap(k / 16))`, k = 0..16)

```python
STOPS = {
    "viridis": (
        "#440154", "#48186a", "#472d7b", "#424086", "#3b528b", "#33638d",
        "#2c728e", "#26828e", "#21918c", "#1fa088", "#28ae80", "#3fbc73",
        "#5ec962", "#84d44b", "#addc30", "#d8e219", "#fde725",
    ),
    "plasma": (
        "#0d0887", "#310597", "#4c02a1", "#6600a7", "#7e03a8", "#9511a1",
        "#aa2395", "#bc3587", "#cc4778", "#da5a6a", "#e66c5c", "#f0804e",
        "#f89540", "#fdac33", "#fdc527", "#f8df25", "#f0f921",
    ),
    "inferno": (
        "#000004", "#0b0724", "#210c4a", "#3d0965", "#57106e", "#71196e",
        "#8a226a", "#a32c61", "#bc3754", "#d24644", "#e45a31", "#f1731d",
        "#f98e09", "#fcac11", "#f9cb35", "#f2ea69", "#fcffa4",
    ),
    "magma": (
        "#000004", "#0a0822", "#1d1147", "#36106b", "#51127c", "#6a1c81",
        "#832681", "#9c2e7f", "#b73779", "#d0416f", "#e75263", "#f56b5c",
        "#fc8961", "#fea772", "#fec488", "#fde2a3", "#fcfdbf",
    ),
    "cividis": (
        "#00224e", "#002e6a", "#1a386f", "#32436d", "#434e6c", "#535a6d",
        "#61656f", "#6f7073", "#7d7c78", "#8c8878", "#9b9476", "#aba072",
        "#bcae6c", "#cdbb63", "#dec958", "#f0d846", "#fee838",
    ),
    "coolwarm": (
        "#3b4cc0", "#4e68d8", "#6282ea", "#779af7", "#8db0fe", "#a3c2fe",
        "#b9d0f9", "#ccd9ed", "#dddcdc", "#ecd3c5", "#f5c4ac", "#f7b093",
        "#f4987a", "#eb7d62", "#dd5f4b", "#ca3b37", "#b40426",
    ),
    "RdBu_r": (
        "#053061", "#175290", "#2a71b2", "#3f8ec0", "#6bacd1", "#9bc9e0",
        "#c2ddec", "#e0ecf3", "#f7f6f6", "#fbe5d8", "#fbccb4", "#f5aa89",
        "#e48066", "#d05548", "#ba2832", "#930e26", "#67001f",
    ),
    "gray": (
        "#000000", "#101010", "#202020", "#303030", "#404040", "#505050",
        "#606060", "#707070", "#808080", "#909090", "#a0a0a0", "#b0b0b0",
        "#c0c0c0", "#d0d0d0", "#e0e0e0", "#f0f0f0", "#ffffff",
    ),
}
```

Checks taken from matplotlib on the same day: `viridis(0.3) = #355f8d`,
`coolwarm(0.7) = #f7ac8e`; 17-stop linear interpolation meets both within `3 / 255`.
