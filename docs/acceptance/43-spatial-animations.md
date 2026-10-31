# Acceptance table — task 43, spatial construction

**Status: Draft, written 2026-10-31 before any code, per ADR 0003 §9.**
Contracts: ADR 0008 §§2–6 (spatial construction, reversible presentation state,
canonical finish, F-915 and F-918); ADR 0004 §9 (customisation); tasks 21/27
(fields), 22 (polar), 25/29 (surfaces and composed 3D artists), 35 (insets).
The brainstorm, sections 2–5, supplies candidate semantics, not another contract.
Every choice below not settled by ADR 0008 is marked *(default taken)*.
Task 40 owns `_base`, the existing `GrowSurface` move and its flags; these tests
use public animation lifecycle methods and scene behavior, never `_base`.

Modules: `manim_plots/animations/fields.py` (`GrowField`), `surfaces.py`
(`GrowStems`, `RevealWireframe`, `RevealWaterfall`, `SweepSurface`), `axes.py`
(`SweepPolar`), `decorations.py` (`OpenInset`, `CloseInset`). All eight names are
exported from `manim_plots.animations` and `manim_plots` as the same class objects.
This specification changes only this table and `tests/animations/`.

```python
# New signatures; every parameter default here is (default taken).
class GrowField(Animation):
    def __init__(
        self,
        field,
        *,
        order="data",
        lag_ratio=0.02,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class GrowStems(Animation):
    def __init__(
        self, stems, *, lag_ratio=0.05, reverse=False, remover=None, **kwargs
    ): ...


class RevealWireframe(Animation):
    def __init__(
        self,
        wireframe,
        *,
        families=("u", "v"),
        lag_ratio=0.05,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class RevealWaterfall(Animation):
    def __init__(
        self, waterfall, *, lag_ratio=0.15, reverse=False, remover=None, **kwargs
    ): ...


class SweepSurface(Animation):
    def __init__(
        self, surface, *, axis="u", direction=1, reverse=False, remover=None, **kwargs
    ): ...


class SweepPolar(Animation):
    def __init__(
        self,
        ax,
        *,
        start_angle=0,
        angle=2 * PI,
        lag_ratio=0,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class OpenInset(AnimationGroup):
    def __init__(
        self, inset, *, lag_ratio=0.25, reverse=False, remover=None, **kwargs
    ): ...


class CloseInset(OpenInset):
    def __init__(
        self, inset, *, lag_ratio=0.25, reverse=True, remover=None, **kwargs
    ): ...
```

`Animation` can be a subclass; `AnimationGroup` can be its `LaggedStart` or
`Succession` subclass. Large part collections have one driver, per ADR 0008 §2.
All accept native `run_time=1`, `rate_func=smooth` *(default taken)*.
Flags follow ADR 0008 §3: reverse defaults to removal, an explicit `remover`
wins, and cleanup restores canonical geometry even when kept in the scene.
`CloseInset(inset)` means `OpenInset(inset, reverse=True)`, not a second effect.

For n ordered parts, raw time a and lag l, use
`p_i = rate_func(clip(a * (1 + (n - 1) * l) - i * l, 0, 1))`;
reverse substitutes `1-a` before this complete schedule *(default taken)*.
This unwinds the last entrance first. `lag_ratio=0` is simultaneous. Easing is
applied once per window; sweeps without windows use `p=rate_func(a)`.
Geometry is evaluated through the mapping for that frame. Empty or zero-sized
parts do not produce NaNs; original per-part opacity is multiplied by visibility,
never reset to one *(default taken)*. Finish is read after `play`, never from the
last probe record. A reverse without removal still restores the canonical artist.

The origin is semantic, not an extra screen-space `origin` option *(default taken)*:
field tails come from the canonical arrow (including `vector_config.center`),
stems use their artist's `bottom` and `orientation`, waterfall fills use their
current viewport floor. Surface/polar starts and directions are the explicit
keywords above. Source-order stems and waterfall planes retain their stored order;
wireframe family order is chosen by `families`, and field order by `order`.
Named parts remain independently styleable: `field.arrows` (shaft and tip children),
`stems.stemlines`, `stems.markers`, `stems.baseline`, `wireframe.u_lines`/`v_lines`,
`waterfall.lines`/`fills`, `surface.faces.at(key)`, polar `circles.at(radius)` /
`spokes.at(angle)` and coordinate labels, inset `zoom_box`, `connectors`, `mirrored`.
No animation replaces these addressable parts or their individual styles.

## GF — vector fields

| ID | Row |
|---|---|
| GF-1 | `GrowField` grows every 2D or 3D arrow about its canonical mapped tail. The far tip is `tail + p_i * canonical_length * mapped_unit_vector`, using the artist's `length_func` on the original data vector; tips shrink with the arrow, never hang at the final endpoint. Data direction, original-vector colour and partial opacity stay canonical. Two arrows with lag 1 have progress `(0.5,0)` at a=0.25 and `(1,0.5)` at a=0.75 *(default taken)*. |
| GF-2 | Reverse retracts arrows and unwinds their schedule; the field leaves the scene by default, can be kept with `remover=False`, and reintroducing the same field preserves data, individual styles and binding updaters. |
| GF-3 | Forward introduces the field and finishes with canonical arrow geometry and no added updater; a later range/frame change remaps its tails and retains styles. |
| GF-4 | `order="data"` is stored grid order; `"x"`, `"y"`, `"z"` sort tail coordinates, `"value"` sorts data-vector norm, and a callable `order(tail, vector)` returns a sortable key. Resolve order at begin with stable ties; on flat fields, zero and nonfinite vectors retain their canonical hidden/degenerate behavior. Nonzero flat and solid 3D arrows use the same growth fraction *(default taken)*. |
| GF-5 | A solid 3D field containing a zero or nonfinite vector constructs without a `ZeroDivisionError` in `ArrowVectorField._solid_arrow`/Manim `Cone`. That arrow remains hidden or degenerate at its mapped tail, with finite drawable geometry, exactly as on flat fields; `GrowField` grows the other arrows from their tails with their canonical mapped directions and lengths. Cover zero, NaN and infinity, intermediate growth and canonical finish. This constructor defect belongs to task 43 (maintainer review). |

## GS — stems

| ID | Row |
|---|---|
| GS-1 | `GrowStems` grows `stemlines[i]` from its configured `bottom` in its `orientation` coordinate: `end = base + p_i*(point-base)`. Other coordinates are fixed. `markers[i]` follows this end; `baseline` keeps its geometry. Cover x/y/z orientations, signed displacements, nonzero bottoms and a point already on the baseline *(default taken)*. |
| GS-2 | Reverse retracts markers with stems, removes the container by default and preserves all three named parts, sources, styles and existing updaters for reintroduction; `remover=False` keeps it. |
| GS-3 | The entrance introduces the stems, leaves canonical points and markers, adds no persistent updater and a later range/frame change re-derives the same data. |

## RW — wireframes

| ID | Row |
|---|---|
| RW-1 | `RevealWireframe` traces constant-u `u_lines` then constant-v `v_lines`, using parameter fraction within each curve, with one lag window per line. `families=("v","u")` exchanges their schedule; a single-family selection leaves the other family hidden during the play. Curves retain source direction, gaps and separate styles. For z=u+v on [0,2]², resolution (1,1), v-first and lag 1, a=1/8 ends the first line at (1,0,1), all u-lines still hidden *(default taken)*. |
| RW-2 | Reverse untraces lines in reverse family/parameter schedule and removes the container; reintroduction retains sources, styles and bindings; explicit `remover=False` keeps it. |
| RW-3 | Forward introduces the wireframe, restores all canonical lines on finish and leaves no added updater; a later range/frame edit re-derives the lines. |

## WF — waterfalls

| ID | Row |
|---|---|
| WF-1 | `RevealWaterfall` traces `lines` in retained plane order, each by source-index fraction. The matching optional `fills[i]` closes only the revealed curve to its current viewport floor and back to its start; its front has the same abscissa as the line. With x=[0,2], curves [[1,3],[2,4]], positions [0,1], zdir="y", floor z=-2 and lag 1, a=0.25 ends line 0 at (1,0,2), its fill contains (1,0,2) and (1,0,-2), and line 1 is hidden. `fill=False` retains None entries *(default taken)*. |
| WF-2 | Reverse untraces the last plane first, withdraws its matching fill and removes the container; reintroduction preserves sources, styles, fills and bindings; explicit `remover=False` keeps it. |
| WF-3 | Forward introduces the waterfall, finishes with every canonical line/fill and no added updater; a later range/frame edit remaps the data. |

## SS — surfaces

| ID | Row |
|---|---|
| SS-1 | `SweepSurface(axis="u", direction=1)` restricts the grid/parametric/revolution parameter domain from its first endpoint towards its second; v works likewise, direction -1 starts at the other endpoint. Grid u/v are uniformly spaced row/column indices, interpolating within the original cell, not world x/y. Trim a straddling cell at the exact parameter front, retaining face keys/styles, holes and canonical colour values. For z=u+v on [0,2]² at p=0.375, a u-sweep ends at x=0.75; a negative v-sweep starts at y=1.25 *(default taken)*. |
| SS-2 | Reverse retreats the same domain front and removes the surface; reintroduction preserves source data, face styles, colour mapping and binding updaters; `remover=False` keeps it. |
| SS-3 | Forward introduces the surface, restores every canonical face on finish, adds no persistent updater and a later range/frame edit re-derives its full domain. |
| SS-4 | Triangle surfaces accept `axis="x"`, `"y"` or `"z"` and clip each original data triangle against a half-space whose front interpolates that coordinate's finite vertex min/max. Newly intersected vertices lie on the original triangle, not an axis plane. The triangle (0,0,0),(2,0,2),(0,2,2), x-swept halfway, has corners (0,0,0),(1,0,1),(1,1,2),(0,2,2) *(default taken)*. |
| SS-5 | Reversed parameter intervals retain their source direction. Missing/nonfinite cells stay holes rather than being bridged or resampled into validity. Clip the restricted surface to the current viewport after computing its parameter front; a u-front at x=1 with viewport x=[0.5,1.5] shows 0.5 <= x <= 1. For u=(2,0), z=NaN for u<1 and z=u+v otherwise, p=0.25 shows only 1.5≤u≤2; at p=0.9 no corner has u<1 *(default taken)*. |
| SS-6 | A sweep preserves per-face overrides, colour mapping limits and a linked colorbar's colours/range; it changes presentation, not scalar data. A colorbar which does not change need not be marked moving. Growing/sweeping alongside a bound height tracker uses its current value, and following survives finish (F-918). |

## SP — polar decorations

| ID | Row |
|---|---|
| SP-1 | `SweepPolar` accepts `PolarPlane` and `PolarAxes`. Reveal each circle over the directed source-angle interval from `start_angle` to `start_angle + p*angle`, and spokes once reached; reveal their coordinate labels with them. Existing Cartesian/radial decoration geometry and polar mappings do not change. With start=0, angle=2π at p=1/4 the radius-1 ring is the first quadrant ending at (0,1), spoke 0 is visible and spoke π hidden *(default taken)*. |
| SP-2 | Reverse retreats the angular front, withdraws labels and removes the system by default; reintroduction keeps mapping, plots, styles and binding updaters. Removing the system does not remove independently added artists; `remover=False` keeps the system. |
| SP-3 | Forward introduces the system, finishes with all bound decorations and no added updater; a later range/frame change rebuilds the full rings and spokes, not a leftover arc. |
| SP-4 | A negative `angle` sweeps clockwise in source-angle space; `azimuth_offset` and `azimuth_direction` still act in the map. Nonzero starts can cross the 2π seam without sorting by wrapped screen angle. Partial angles affect intermediate visibility; canonical finish restores the full bound system. `lag_ratio` delays successive rings (ascending radius); each spoke/label follows the corresponding angular front. With lag 0 all rings share a front *(default taken)*. |
| SP-5 | F-915: polar decoration leaves are moving before static-background compilation, while an unrelated still plot remains static. A sweep alongside a radial range change uses that frame's radial mapping and never changes a separately added polar curve's data or geometry except for that mapping. |

## OI — insets

| ID | Row |
|---|---|
| OI-1 | `OpenInset` draws `zoom_box`, expands the presentation viewport from its parent-data rectangle to its configured parent-relative bounds, then reveals `mirrored` artists; the three equal-duration stages overlap with `lag_ratio`. During expansion interpolate the lower-left and size in scene coordinates between those two rectangles computed from the current parent map. `lag_ratio=0` gives all stages the same progress. Connectors join corresponding current corners, and mirrored artists use the inset map, never the parent's *(default taken)*. |
| OI-2 | `OpenInset(reverse=True)` and `CloseInset()` collapse towards the live zoom box, withdraw connectors and box and remove the inset; explicit `remover=False` wins. Reopening with `OpenInset` preserves independent ranges, mirror sources, individual styles and the inset's existing parent-following updater. Mirrored scene roots are withdrawn too *(default taken)*. |
| OI-3 | Forward introduces the inset, leaves its configured bounds and full mirrored content at finish, and adds no persistent updater. A later parent range/frame change moves the viewport, box, connectors and mirrors through their respective maps. |
| OI-4 | F-915: inset frame, connectors and separately added mirrored artists enter the moving set before Cairo compiles its static background; an unrelated still plot remains static. While the parent range changes, connector endpoints lie on matching live box/viewport corners and mirrors use the same frame's inset map. No drawable ghost leaves the scene's families. |
| OI-5 | Empty mirrors and `connectors=False` are valid; opening still expands the independent viewport and leaves the existing following updater intact. The parent may move while it opens *(default taken)*. |

## SC — shared public behavior

| ID | Row |
|---|---|
| SC-1 | For each family, revisiting the same eased alpha after another alpha gives identical points, colours and opacities. A non-monotone `there_and_back` does not progressively truncate sources. |
| SC-2 | Each 3D family runs beside a range change and a camera move. On each probed partial frame, compare tails/endpoints/fronts with independently computed data passed to that frame's `ax.c2p`. Camera movement changes the view, never source order or progress. |
| SC-3 | F-915/F-918: the polar/inset entrance makes its changed systems/decorations moving, without marking an unrelated plot moving or resampling its static function each frame. No global activation. |
| SC-4 | Reject unknown field order/family/axis, direction other than ±1, negative or nonfinite lag, and nonfinite angular options with ValueError before changing any point or style. Parameter surfaces accept u/v; triangle surfaces accept x/y/z; unsupported combinations are errors *(default taken)*. No new baseline option is introduced; task 40 owns GrowSurface's invalid-log-origin coverage. |
| SC-5 | Reverse at a raw partial time uses the backwards whole schedule, not reversed data or a second application of easing; independent field, stem, line, surface, polar and inset geometry oracles still hold. Forward `remover=True` also removes after restoring canonical state. |
| SC-6 | All eight public classes have the same identity at top level, package and documented family module; instances are Manim Animation subclasses. This row does not retest task 40's legacy-path move. |

## Oracle and review notes

The tests use exact fractions via public `begin`/`interpolate`/`finish` plus dry-run
`probe` scenes at the house 6 fps; no output movies, pictures or baselines.
Cubic handles are excluded from arc/polygon coordinate oracles. Field tip distance
uses the actual farthest tip point. Scene finish is inspected after `play`.
The shared `tests/animations/conftest.py` substitutes Pango `Text` for `MathTex` only when no `latex` executable is on PATH; the merge gate retains real TeX.

Maintainer review: approve/veto the marked defaults, particularly the callable field
order record, partial-angle canonical finish and the inset three-stage schedule.
The solid-field constructor defect is included in task 43 under GF-5.
No maintainer decision is needed to run or collect the specification tests.
Raster occlusion/depth-sorting pictures, actual TeX glyph rendering and large-case
frame-cost readings are intentionally not rows here: camera/data behavior is tested,
but those require the later renderer/full-gate review. No task-40 internals are
assumed and no implementation or compatibility export is written by this task.
