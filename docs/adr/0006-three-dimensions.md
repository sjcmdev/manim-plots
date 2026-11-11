# ADR 0006 — Three dimensions, in the first release

- **Status:** Accepted, 2026-10-30. Asked for by the maintainer after the stage 3 page
  ("rozpisywanie 3D"; "wydanie ma być kompletne"); the scope, the frame styles and the
  spherical convention are the maintainer's, from the same day's brainstorm. Items
  marked *(default taken)* were not asked and stand unless the maintainer vetoes them.
- **Builds on:** the grill log's D7 (*a coordinate system is one mapping*, which already
  admits `R^3 -> R^3`) and D15 (*field artists unify into one pipeline head*); ADR 0004
  §5 (matplotlib's names where Manim has none) and §9 (customisation); task 15
  (clipping per axis), task 20 (themes), task 21 (`FieldSource`, `rk4_step`), task 22
  (a coupled node).
- **Supersedes:** ADR 0004 §3's "3D ... stays after it": 3D joins the first release,
  and `0.1.0` is tagged after stage 4. The parity survey's *3D* section moves to 0.1.

## Context

Manim's `ThreeDAxes` is an `Axes` with a third `NumberLine` turned out of the plane, plus
`plot_surface` on every `CoordinateSystem`, drawn by `ThreeDScene`'s camera. It inherits
every defect the library fixed in 2D: a curve does not follow its axes, a range cannot
change, nothing is clipped (a probe on 2026-10-30 draws `sin u cos v`, and a helix to
`z = ±4.875`, past the box's `±3.25`), a log axis only through `LogBase`. Its axes always
cross at the origin; matplotlib draws a box with three back panes, a grid on them and the
axes on the box's edges, picking the panes and edges from the view.

The library's model was built for this. A system is one mapping (D7); a separable system
composes it from per-axis scale nodes and one affine node; sources sample in data space
and adapt to the mapped curvature; artists are leaves bound to the system. What is 2D
today is the code: about 150 places index axes as 0 and 1, slice `[:, :2]` or build a
rectangle. A probe shows the 2D `mp.Axes` already rendering in a `ThreeDScene`, projected
by Manim's camera.

Depth is the hard part. Manim's Cairo `ThreeDCamera` sorts whole mobjects by depth and
paints them back to front; a curve passing through a surface, or two surfaces crossing,
come out wrong. Manim's `experimental` branch (last commit 2026-06-24, unreleased) has an
OpenGL renderer with a depth buffer and a per-mobject `depth_test`, which solves this per
pixel; the library is Cairo-only today (`CartesianAxes` refuses OpenGL).

## Decision

### 1. One system, generalized by dimension

`mp.ThreeDAxes` is the third dimension of the same system, not a second engine: scale
nodes and the affine node take `dim=3`, bounds become boxes, `c2p` and `p2c` take three
coordinates, `x`, `y`, `z` are three `Axis` decorations, and the code that says 0 and 1
today says "for each axis". A 2D system is unchanged and pays nothing for it (F-1001).
Twins and secondary axes stay 2D *(default taken)*.

### 2. Manim's surface, Manim's meaning

`mp.ThreeDAxes` takes Manim's signature and defaults and is reached as
`mp.ThreeDAxes` outside `__all__`. Code written for Manim's `ThreeDAxes` runs unchanged
and draws the same picture on Manim's defaults. `get_z_axis`, `get_z_axis_label`,
`get_axis_labels(x, y, z)`, `plot` (in `z = 0`), `plot_parametric_curve` in 3D,
`plot_surface(function, u_range, v_range, colorscale, colorscale_axis, **kwargs)`, `c2p`,
`p2c`, `i2gp` keep Manim's meaning.

### 3. What the library adds, as in 2D

Everything bound: artists follow the axes' moves and every range change, `set_z_range`
included, animated; log and symlog on any axis; per-axis clipping to the box
(`clip=(x, y, z)`); every part styleable by key and kept through re-derivation (ADR 0004
§9); themes, the colour cycle, the legend.

### 4. Two frame styles, in 3D and in 2D

`frame="origin"` is Manim's: axes crossing at the origin of the data (or where
`set_position` puts them). `frame="box"` is matplotlib's: in 3D, three panes with a grid
on the far sides of the box, the axes and their numbers on the near edges, the panes and
edges chosen from the camera's `phi` and `theta` on every frame the camera moves; in 2D,
the four borders with ticks inward and mirrors (task 19b's framed plot, now one keyword).
`frame` defaults to `"origin"`, Manim's picture; a theme may set `"box"` (task 20's
`origin`, `base`, `paper` and `lab` do) *(the maintainer: "origin i box jest ok, to samo
dla osi w 2d")*. Panes, pane grids and each edge axis are parts, styleable and hideable
one by one. Numbers and labels face the camera in `"box"` and lie in their plane in
`"origin"`, as Manim's, a keyword either way.

The camera stays Manim's: the library reads `ThreeDScene`'s camera to choose panes,
edges and facing, and never moves it except through `ax.view(elev, azim)`, which sets
`ThreeDScene`'s camera with matplotlib's angles. Equal or set aspect is
`aspect=(1, 1, 1)` / `"equal"`, matplotlib's `set_box_aspect`.

### 5. Coordinates: ISO 80000-2

Spherical coordinates are `(r, θ, φ)` with θ the polar angle from `+z` and φ the azimuth
from `+x` in the xy-plane, as physics and mathematics write them (ISO 80000-2)
*(the maintainer: "fizyka i matematyka ma pierwszeństwo")*; Manim's
`spherical_to_cartesian`, which orders them otherwise, is not followed. Cylindrical are
`(ρ, φ, z)`. Every system gets `spherical_to_point`, `point_to_spherical`,
`cylindrical_to_point`, `point_to_cylindrical` and the short `sp2pt`, `pt2sp`, `cy2pt`,
`pt2cy` beside Manim's `pr2pt`. Functions, curves, surfaces and fields can be defined in
them: `coords="spherical"` or `"cylindrical"` on `plot_surface`,
`plot_parametric_curve`, the vector field and stream lines, so `r(θ, φ)` is a surface
and a field may return `(v_r, v_θ, v_φ)`.

### 6. The frame follows affine moves only

In 3D the system's frame is affine: shift, scale, rotation about any axis, `Rotate`,
`.animate.rotate`. `apply_function` on a `ThreeDAxes` raises `NotImplementedError`
*(default taken)*.

### 7. Depth: one occlusion step, replaceable

The library draws through Cairo and leaves the camera's sort in place, and adds one
occlusion step between its artists and the renderer: from the camera's current view it
computes which pieces of its curves, segments and faces are hidden, using a depth buffer,
and hands Manim only the visible pieces as ordinary vector paths, cut where visibility
changes. The depth buffer is drawn on the GPU through `moderngl` when a context opens
(Manim already depends on it; a compute or a fragment pass, whichever measures faster)
and in NumPy otherwise, so a headless machine draws the same picture more slowly. The
step runs only for frames where the camera, the axes or an artist changed, and only for
artists marked opaque; it is off by `occlusion=False`. It is one module behind one
interface, so when Manim releases the experimental renderer's depth test, a later task
can hand depth to Manim instead and remove the step *(default taken)*.

### 8. What joins the release

Everything of the 2026-10-30 brainstorm's tiers A and B:

- the system, both frame styles, `view`, `aspect`, camera-facing text;
- surfaces from functions or arrays, parametric surfaces, surfaces of revolution, from
  scattered points (Delaunay, `plot_trisurf`), wireframes; colour by height or by any
  function, colormaps and a colorbar (in 2D too); NaN holes, opacity, checkerboard;
  contours on a surface and projected on the panes;
- planes (`ax.plane(x=…)`, `ax.plane(point, normal)`), lines and segments in 3D,
  `xline`, `yline`, `zline` and `get_lines_to_point` to a point, intersections (plane and
  plane, line and plane, plane and surface);
- spherical and cylindrical coordinates and definitions in them (§5);
- vector fields in 3D (flat camera-facing arrows by default, `arrow="3d"` for Manim's
  3D arrows), stream lines in 3D (plain lines by default, `line="3d"` for `Line3D`),
  `Flow` in 3D;
- slices: `surface.slice(x=…)` as a curve on the surface, and `plot_slice` on a linked 2D
  `mp.Axes` following a tracker; shadows of curves and points on the panes; matplotlib's
  `zdir` (2D data laid on a chosen plane);
- `scatter` with colour and size by value, `stem`, waterfall and `fill_between` in 3D,
  `bar3d`, error bars in 3D, `ax.text` and `ax.annotate` at a 3D point;
- orthographic projection; growing and morphing surfaces;
- the occlusion step (§7).

Voxels, isosurfaces and stream tubes stay after it.

## Tasks

Stage 4, before the release; each task gets its acceptance table and tests first:

- **24 — the 3D system**: §1-§3, §6; `frame="origin"` and `"box"` in 3D and 2D (§4),
  `view`, `aspect`, camera-facing text; curves, `scatter` and `line` in 3D.
- **25 — surfaces**: functions, arrays, parametric, revolution, `plot_trisurf`,
  wireframe, colour by height and by hook, colormaps and the colorbar, contours on the
  surface and on the panes.
- **26 — geometry and coordinates**: planes, lines, segments, `x/y/zline`,
  intersections; spherical and cylindrical coordinates and definitions in them.
- **27 — fields in 3D**: vector fields, stream lines, `Flow`.
- **28 — slices and projections**: `slice`, `plot_slice` on linked axes, shadows on the
  panes, `zdir`.
- **29 — more plot types**: value-mapped `scatter`, `stem`, waterfall, `fill_between`,
  `bar3d`, error bars, `text`, `annotate`; orthographic projection; growing and morphing.
- **30 — occlusion** (§7), with frame-cost readings.
- **23 — the release**, last: the performance pass, the invalid-input table, types, the
  documentation of everything, the parity survey, the changelog; then the tag.

## Consequences

- The 2D code is generalized by dimension once, in task 24; every existing test must pass
  unchanged, and F-1001 gates the cost.
- The release moves back by tasks 24-30. Its public API includes 3D, so the 3D contracts
  are frozen with the rest.
- Supporting Manim's experimental OpenGL renderer is not in the release; §7 keeps the
  door open.
