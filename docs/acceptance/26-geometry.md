# Acceptance table — task 26, geometry and coordinates

**Status: Living until task 26 merges, then Record.** Written 2026-10-30 before any code,
per ADR 0003 §9. Rows marked *(default taken)* were settled here without the maintainer
and stand unless vetoed. Contracts: ADR 0006 §5 (coordinates), §8; ADR 0004 §5 (names),
§6 (bound helpers), §9 (customisation); task 16 (HB rows: bound inputs, the transient
rule; DL rows: drop lines); task 24 (the box, clipping, panes); task 25 (surfaces,
contours). Fields in spherical coordinates are task 27.

Modules: `mobjects/geometry.py` (new: `PlanePlot`, `AxLinePlot`, the intersections),
`mobjects/three_d.py` (the methods, the coordinates), `mobjects/helpers.py` (drop lines
by dimension), `mobjects/surfaces.py` (`coords=`), `src/manim_plots/__init__.py`.

```python
# on ThreeDAxes
def plane(
    self, point=None, normal=None, *, x=None, y=None, z=None, **style
) -> PlanePlot: ...
def axline(self, xyz1, xyz2=None, *, direction=None, **style) -> AxLinePlot: ...
def segment(self, start, end, **style) -> AxLinePlot: ...
def xline(self, y, z, xmin=0, xmax=1, **style) -> AxLinePlot: ...  # parallel to x
def yline(self, x, z, ymin=0, ymax=1, **style) -> AxLinePlot: ...
def zline(self, x, y, zmin=0, zmax=1, **style) -> AxLinePlot: ...
def get_line_from_axis_to_point(
    self,
    index,
    point,
    line_func=DashedLine,
    line_config=None,
    color=None,
    stroke_width=2,
) -> HelperLine: ...
def get_lines_to_point(
    self, point, **kwargs
) -> HelperGroup: ...  # .x_line .y_line .z_line
def intersection(self, a, b, **style) -> AxLinePlot | ScatterPlot | ContourPlot: ...
def spherical_to_point(self, r, theta, phi): ...  # alias sp2pt
def point_to_spherical(self, point): ...  # alias pt2sp
def cylindrical_to_point(self, rho, phi, z): ...  # alias cy2pt
def point_to_cylindrical(self, point): ...  # alias pt2cy


# coords=None | "spherical" | "cylindrical" on plot_surface, plot_parametric_surface,
# plot_parametric_curve


class PlanePlot(
    _CurvePlot
): ...  # mp.PlanePlot: one closed polygon, the plane in the box


class AxLinePlot(ParametricPlot): ...  # mp.AxLinePlot: a straight line in data space
```

**Two kinds of point.** The verbs new to this task (`plane`, `axline`, `segment`) take a
**data point**: a sequence of three entries, each a number, a `ValueTracker` or a
zero-argument callable (HB-2); a zero-argument callable returning a data triple; or a
`Mobject`, whose centre is read every frame and converted with `p2c`. Manim's verbs
(`get_line_from_axis_to_point`, `get_lines_to_point`) keep Manim's **scene point** (HB-3).
A vector input (`normal`, `direction`) takes the data-point forms *(default taken)*.

## PL — planes

| ID | Row |
|---|---|
| PL-1 | `ax.plane(x=c)` (or `y=`, `z=`) is the box's cross-section at `x = c`: one closed polygon whose four corners are `(c, y0, z0)`, `(c, y1, z0)`, `(c, y1, z1)`, `(c, y0, z1)` of the current ranges, mapped by `c2p`, straight between them (`set_points_as_corners`). `c` takes HB-2's forms. Flat on any scale: an axis-aligned plane is allowed on log and symlog axes |
| PL-2 | `ax.plane(point, normal)` is the plane through the data point with that normal in data space, cut to the box: the convex polygon of its crossings with the box's twelve edges (3 to 6 corners), ordered around the normal, each corner on the plane within `1e-9` in data |
| PL-3 | Exactly one form: none, two of `x`/`y`/`z`, or `x` with `point` raise `ValueError` naming `plane`; `point` without `normal` (or the reverse) raises naming the missing one; a zero normal raises naming `normal`; `point, normal` on a system with a non-linear axis raises `ValueError` naming `normal` (the plane would curve) *(default taken)* |
| PL-4 | A plane that misses the box at the call raises `ValueError` naming its input (`x`, or `point`); during an animation it is empty on that frame and comes back (HB-7) |
| PL-5 | A plane is bound as a curve: it follows its trackers and callables, `set_x_range` / `set_y_range` / `set_z_range` (animated), and affine moves, on every frame, with no `always_redraw`; a still plane costs nothing per frame |
| PL-6 | Style: the next colour of the cycle, `fill_opacity=0.25`, `stroke_width=1` in the same colour *(default taken)*; `label=` puts it in the legend; a style the user sets (`set_fill`, `set_stroke`) is kept through re-derivation (ADR 0004 §9) |

## LN — lines and segments

| ID | Row |
|---|---|
| LN-1 | `ax.axline(xyz1, xyz2)` is the infinite line through the two data points, `ax.axline(xyz1, direction=d)` the line through `xyz1` along `d` (matplotlib's `axline`): drawn as the part inside the box, from one box face to another, straight in data space |
| LN-2 | `axline` with both `xyz2` and `direction`, or neither, raises `ValueError` naming `direction`; equal points or a zero direction raise naming `xyz2` or `direction` |
| LN-3 | `ax.segment(start, end)` joins two data points, straight in data space, cut to the box exactly as LN-1 cuts a line (the part of the segment inside). On a log axis it is the data line, so it curves on screen: every drawn point's `p2c` lies on the data segment within `1e-6` |
| LN-4 | `ax.xline(y, z, xmin=0, xmax=1)` is the line parallel to the x axis through `y`, `z`, from `xmin` to `xmax` of the x axis's drawn length (DL-4's fractions, matplotlib's `axhline` extended) *(default taken: the name reads as the direction)*; `yline(x, z, ...)` and `zline(x, y, ...)` likewise. Defaults as DL-4: solid, Manim's default colour, `stroke_width=2` |
| LN-5 | `axline` and `segment` take the next colour of the cycle and a plot's stroke, as `ax.line`; `label=` puts them in the legend. All four are bound (HB-2, PL-5) and are `AxLinePlot`s |

## DP — drop lines in 3D

| ID | Row |
|---|---|
| DP-1 | `get_line_from_axis_to_point(index, point, ...)` takes `index` 0, 1 or 2 and draws from the point with its other two coordinates set to where the axes cross (DL-1's `c`, per axis), to the point. On Manim's default `ThreeDAxes`, with the point in the first octant, its start and end equal Manim's to `1e-9`. `index` 3 raises `ValueError` naming `index` |
| DP-2 | `get_lines_to_point(point)` is a `HelperGroup` of three lines in this order: `.x_line` from `(cx, y, cz)` to `(x, y, cz)`, `.y_line` from `(x, cy, cz)` to `(x, y, cz)`, `.z_line` from `(x, y, cz)` to the point: the point's drop to the floor and the floor point's lines to the two walls, matplotlib's drop lines (Manim's two oblique lines from the x and y axes are not followed) *(default taken)*. `c` is the crossing in `frame="origin"`; in `frame="box"` it is the far pane's side, and the lines move when the pane changes sides (task 24, FR-3) |
| DP-3 | Both take `line_func`, `line_config`, `color`, `stroke_width` as DL-1, are bound as HB-3, and collapse while the point is outside the box (HB-7). `get_vertical_line`, `get_horizontal_line` and `get_vertical_lines_to_graph` stay refused in 3D (TS-3) |

## IX — intersections

| ID | Row |
|---|---|
| IX-1 | `ax.intersection(plane_a, plane_b)` is an `AxLinePlot` along their common line, cut to the box; parallel planes give no line |
| IX-2 | `ax.intersection(line, plane)` (an `AxLinePlot` from `axline`, `segment`, `xline`/`yline`/`zline` or IX-1) is a `ScatterPlot` of one marker at the crossing; a crossing outside a segment or outside the box is hidden as TK-3 hides a point (opacity 0) |
| IX-3 | `ax.intersection(plane, surface)` is a `ContourPlot` of one level: CT-1's construction on the zero level of `n · (p − p0)` over the surface's face-corner grid, each crossing mapped by the surface function, so it lies on the surface; for an axis-aligned plane on a function surface it lies on the plane within `1e-9` |
| IX-4 | The order of `a` and `b` does not matter. Any other pair (line and line, line and surface, surface and surface, anything not an artist of this system) raises `TypeError` naming both types. Inputs that do not meet at the call (parallel planes, a line parallel to a plane, a plane that misses the surface) raise `ValueError` naming `intersection`; during an animation the result is empty or hidden on that frame and comes back (HB-7). A line that would meet the plane outside its segment or outside the box is IX-2's hidden marker, not an error |
| IX-5 | An intersection is bound to both inputs: it re-derives in the same frame when either does (a tracker, a range, a move), and follows affine moves. Style: the next colour of the cycle; `label=` *(default taken)* |

## CO — spherical and cylindrical coordinates (ADR 0006 §5)

| ID | Row |
|---|---|
| CO-1 | `spherical_to_point(r, theta, phi)` is `c2p(r sin θ cos φ, r sin θ sin φ, r cos θ)`: θ the polar angle from `+z`, φ the azimuth from `+x` (ISO 80000-2). Arrays broadcast and return columns, as `c2p` (TS-1). `sp2pt` is the same method. Manim's `spherical_to_cartesian`, which orders them otherwise, is not followed |
| CO-2 | `point_to_spherical(point)` inverts it through `p2c`: `r ≥ 0`, `θ = arccos(z / r)` in `[0, π]`, `φ = arctan2(y, x)` in `(−π, π]`; at `r = 0` it is `(0, 0, 0)`; an `(n, 3)` array gives `(n, 3)`, as `p2c`. `pt2sp` is the same method |
| CO-3 | `cylindrical_to_point(rho, phi, z)` is `c2p(ρ cos φ, ρ sin φ, z)`; `point_to_cylindrical(point)` gives `ρ ≥ 0`, `φ = arctan2(y, x)`, `z`. `cy2pt`, `pt2cy` are the same methods |
| CO-4 | Only `ThreeDAxes` has them; 2D systems keep `pr2pt` / `pt2pr` (ADR 0006 §5's "every system" read as every 3D system) *(default taken)* |
| CO-5 | `plot_surface(f, coords="spherical")` is the surface `r = f(θ, φ)`, `u` = θ over `(0, π)` and `v` = φ over `(0, 2π)` by default; `coords="cylindrical"` is `z = f(ρ, φ)`, `u` = ρ over `(0, R)` with `R` the largest circle about the z axis inside the x and y ranges, `v` = φ over `(0, 2π)` *(default taken: matplotlib's surface on a disc)*; `R` when the z axis lies outside the x or y range raises `ValueError` asking for `u_range` |
| CO-6 | `plot_parametric_surface(f, u_range, v_range, coords=...)` takes `f` returning `(r, θ, φ)` or `(ρ, φ, z)`; `plot_parametric_curve(f, t_range, coords=...)` likewise. Each is converted to x, y, z in data before anything else, so faces, keys, colour by value (on the cartesian `colorscale_axis`), clipping, contours and binding are task 24's and 25's |
| CO-7 | `coords` other than `None`, `"spherical"`, `"cylindrical"` raises `ValueError` naming `coords` |

## Frame cost

Readings (p95 of `update`, ms) for the report: a plane bound to a tracker under an
animation of the tracker; the intersection of that plane with a 32 × 32 surface under the
same animation; three drop lines in `frame="box"` under `move_camera`. F-1001 is
unchanged.
