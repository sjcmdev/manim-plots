# ADR 0006 — Three dimensions

- **Status:** Proposed, 2026-10-30. Asked for by the maintainer after the stage 3 page
  ("rozpisywanie 3D"). Items marked *(default taken)* were not asked and stand unless
  the maintainer vetoes them.
- **Builds on:** the grill log's D7 (*a coordinate system is one mapping*, which already
  admits `R^3 -> R^3`) and D15 (*field artists unify into one pipeline head*: surfaces
  are a `FieldSource` artist); ADR 0004 §5 (matplotlib's names where Manim has none) and
  §9 (customisation); task 15 (clipping per axis), task 20 (themes), task 21
  (`FieldSource`), task 22 (a coupled node).
- **Moves:** the parity survey's *3D* section (`get_z_axis`, `get_z_axis_label`,
  `plot_surface`) from **later** to **0.2**, with `ThreeDAxes` itself and F-712's
  surfaces.

## Context

Manim's `ThreeDAxes` is an `Axes` with a third `NumberLine` turned out of the plane, plus
`plot_surface` on every `CoordinateSystem`, drawn by `ThreeDScene`'s camera. It inherits
every defect the library fixed in 2D: a curve does not follow its axes, a range cannot
change, nothing is clipped (a probe on 2026-10-30 draws `sin u cos v` past the axes' box
on every side), a log axis only through `LogBase`, and the surface knows its axes only
through `c2p` at creation.

The library's model was built for this. A system is one mapping (D7); a separable system
composes it from per-axis scale nodes and one affine node; the source samples in data
space and adapts to the mapped curvature; artists are leaves bound to the system and
re-derived when it changes. What is 2D today is the code, not the model: about 150
places index axes as 0 and 1, slice `[:, :2]` or build a rectangle. A probe on the same
day shows the 2D `mp.Axes` already rendering in a `ThreeDScene`, projected by Manim's
camera, so the rendering path needs no change.

## Decision

### 1. One system, generalized by dimension

`mp.ThreeDAxes` is the third dimension of the same system, not a second engine: the
per-axis scale nodes and the affine node take `dim=3`, `Bounds` become boxes, `c2p` and
`p2c` take and return three coordinates, `x`, `y`, `z` are three `Axis` decorations, and
the code paths that say 0 and 1 today say "for each axis". A 2D system is unchanged and
pays nothing per frame for it (F-1001 gates that). Where a 2D rule has no 3D meaning
(twins, secondary axes, polar), `ThreeDAxes` refuses it by name *(default taken: no 3D
twins in 0.2)*.

### 2. Manim's surface, Manim's meaning

`mp.ThreeDAxes` takes Manim's signature and defaults (`x_range=(-6, 6, 1)`,
`y_range=(-5, 5, 1)`, `z_range=(-4, 4, 1)`, the three lengths, `z_axis_config`,
`z_normal`, `num_axis_pieces`, `light_source`, `depth`, `gloss`), and it is reached as
`mp.ThreeDAxes` outside `__all__`, because Manim has the name. Code written for Manim's
`ThreeDAxes` runs unchanged and draws the same picture on Manim's defaults, as `mp.Axes`
does. `get_z_axis`, `get_z_axis_label`, `get_axis_labels(x, y, z)`, `plot` (in the
`z = 0` plane, as Manim's), `plot_parametric_curve` with a three-component function,
`plot_surface(function, u_range, v_range, colorscale, colorscale_axis, **kwargs)` and
`c2p`, `p2c`, `i2gp` keep Manim's meaning.

### 3. What the library adds, as in 2D

Everything bound: curves, points and surfaces follow the axes when they move, rotate or
scale, and follow a changed or animated range on any axis, `set_z_range` included; log
and symlog on any axis, the z axis included; per-axis clipping to the box,
`clip=(x, y, z)` as task 15's `clip=(x, y)`; a surface cut at the box's faces rather
than drawn past them; every part styleable by key (a tick by its value, a surface face
by its `(i, j)` cell) and kept through re-derivation (ADR 0004 §9); themes and the
colour cycle; `scatter(x, y, z)` and `line(x, y, z)` *(default taken: matplotlib's
names, as in 2D)*.

### 4. The camera is Manim's

The library does not touch `ThreeDScene`, `ThreeDCamera`, depth sorting or shading.
Every leaf stays an ordinary `VMobject`, so the camera sorts and shades it as Manim's
own. A camera move is not a move of the axes, so nothing re-derives when only the
camera turns. Numbers and labels lie in their axis's plane, as Manim's do; a keyword
turns them to face the camera through Manim's own `add_fixed_orientation_mobjects`
*(default taken: Manim's flat labels by default)*. Scatter markers are flat dots facing
the camera, not `Dot3D` spheres *(default taken: a sphere costs a surface per point;
`marker="sphere"` gives Manim's `Dot3D`)*.

### 5. The frame follows affine moves only

The 2D frame follows non-affine deformations through a bilinear lattice. In 3D the frame
is affine: shift, scale, rotation about any axis, `Rotate`, `.animate.rotate` *(default
taken)*. An `apply_function` on a `ThreeDAxes` raises `NotImplementedError` naming it,
rather than following approximately; a trilinear frame can come later if asked.

### 6. Surfaces are a field artist

`plot_surface` samples `function(u, v)` on a `FieldSource` grid (task 21), maps it
through the system, and builds Manim's checkerboard of faces, each a leaf keyed by its
cell. `resolution`, `colorscale` and `colorscale_axis` keep Manim's meaning; the faces
are clipped against the box in data space, so a face crossing a wall is cut along it,
not dropped. A parametric surface (`function(u, v) -> (x, y, z)`) is the same artist
with a vector-valued function. Wireframe-only and per-face colour by a scalar hook are
§9 controls.

## Tasks

Stage 4, after the 0.1.0 release (task 23) *(default taken: the release does not wait
for 3D)*:

- **24 — 3D system.** `ThreeDAxes` on the generalized system (§1, §2, §5): the three
  axes and their decoration, `c2p`/`p2c`, curves in 3D, `scatter`/`line` in 3D, ranges
  and their animation, scales, clipping to the box, labels, themes. Parity pictures
  beside Manim's `ThreeDAxes` under a fixed camera.
- **25 — surfaces.** `plot_surface` as a field artist (§6), clipped, bound, keyed by
  cell, styleable; a parametric surface; F-1001-style frame-cost readings for a 32×32
  surface under an animated z range.
- **26 — camera-facing labels, demos, 0.2 documentation**: §4's keyword, the gallery's
  3D tab, *Coming from Manim* and *Differences* for 3D, the parity survey moved.

Each task gets its acceptance table and tests before code, as before.

## Consequences

- The 2D code is refactored by dimension once, in task 24; every existing test must pass
  unchanged, and F-1001 gates the cost.
- The first 3D cut has no twins, polar or field helpers in 3D (vector fields in 3D,
  contours on a surface); each can follow as its own task.
- The parity survey gains `ThreeDAxes`' own methods and moves its *3D* section.
