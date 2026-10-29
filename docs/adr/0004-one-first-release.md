# ADR 0004 — One first release

- **Status:** Frozen, 2026-10-29; a change needs a new ADR. Accepted by the maintainer in
  the review session of 2026-10-29; items marked *(default taken)* were not asked and
  stand unless the maintainer vetoes them.
- **Builds on:** the maintainer's review of the stage 2 page and the answers of
  2026-10-29: clipping per axis, twin and multiple axes, presets and polar approved;
  error bars in x and y and Manim's remaining helpers asked for; 0.1 and 0.2 joined.
- **Supersedes:** the tier of the `docs/scope.md` rows named below, each amended in place
  by the task that implements it and marked *(ADR 0004)*; the release item of
  `task/14-docs-release` in `TODO.md`, which moves to task 23.

## Context

Stage 2 (tasks 06-14) delivered the frozen 0.1 tier in days rather than weeks; only
F-1001 is open. Releasing it now and 0.2 a few days later costs two release cycles, and
it freezes the public API before the features most likely to stress it — a second
scale, a coupled map, a field source — have been built on it.

## Decision

### 1. One release

The first release carries the 0.1 tier and the rows of §2. Its version is `0.1.0`
*(default taken)*. It is tagged after task 23, by the maintainer.

### 2. What joins the first release

| Capability | Scope row | Task |
|---|---|---|
| Clipping per axis: `clip=(x, y)`, each a bool or a margin. Per pair of axes it falls out of F-112: an artist belongs to one system | F-706 amended | 15 |
| Manim's drop lines: `get_vertical_line`, `get_horizontal_line`, `get_lines_to_point`, `get_line_from_axis_to_point`, `get_vertical_lines_to_graph`; reference lines `axvline`, `axhline` | F-711 in part | 16 |
| Manim's calculus cluster: `get_T_label`, `slope_of_tangent`, `angle_of_tangent`, `get_secant_slope_group`, `plot_derivative_graph`, `plot_antiderivative_graph`; tangent line and tangent vector | parity survey, *Calculus* | 16 |
| Filled regions: `fill_between`, `get_area`, `get_riemann_rectangles` | F-711 in part | 17 |
| Error bars in x and y, symmetric and asymmetric | F-711 in part | 18 |
| An independent second scale and any number of further axes: `twinx`, `twiny`, offset axes as in Origin's multi-Y templates | F-610 | 19 |
| Named presets: axis themes and colour cycles, the maintainer's Origin themes among them | F-808 in part | 20 |
| The field source with vector fields, stream lines and flow; `get_vector`; `plot_implicit_curve` if it falls out of the scalar field *(default taken)* | F-712 in part, F-114 `region` | 21 |
| Polar: `mp.PolarPlane`, `plot_polar_graph`, `polar_to_point`, `point_to_polar`, `pr2pt`, `pt2pr`, `get_coordinate_labels`, `get_radian_label`; `Node` public | parity survey, *Polar* | 22 |

### 3. What stays after it

3D; contours and surfaces; autoscale and margins; step, bars and histograms; annotations
and arrows; inset axes; date/time and categorical axes; percent and logit formatters;
label wrapping; rug plots; jitter; legend layout; value-mapped colour and colorbars;
`AppendData`, `Rescale`, `HighlightTick`; the shared view (F-115); `rangelimited` axes;
broken axes; the Origin scale library (F-312). Their rows keep tier **0.2** or **later**.

### 4. Contracts

The 0.1 contracts stay frozen. Until the first release, a contract change that a
capability of §2 forces is allowed, through an ADR that names it: no user depends on the
contract yet, and finding the change now is the point of joining the releases.

### 5. Names

D17 extended: Manim's name, signature and meaning where Manim has one; matplotlib's where
only matplotlib has one (`fill_between`, `errorbar`, `axhline`, `axvline`, `twinx`,
`twiny`); a new name in Manim's `get_*` style only where neither has one
(`get_tangent_line`, `get_tangent_vector`).

### 6. Bound helpers

Every helper of tasks 16 and 17 returns Manim's type with Manim's attribute names
(`dx_line`, `df_line`, `secant_line`, ...) and is bound to its system and its graph, as
`get_graph_label` is (F-609): it follows a changed range, the system's frame, `.animate`
and the graph's parameters. It accepts a `ValueTracker` wherever Manim takes a number
(`x`, `x_val`, `dx`, `x_range`), so the classic animations — a sliding `T` label, a
secant closing into a tangent, a Riemann sum refining — need no `always_redraw`. This is
the unification the maintainer asked for: one mechanism for every helper, not one per
helper.

The field artists of task 21 share one source and one integrator: arrows, stream lines
and the flow of points and mobjects all read the same sampled field, and every motion
along it is one RK4 step function.

### 7. Gate

F-1001 closes before task 16, so every later task measures against a passing gate. Each
task of §2 records one frame-cost reading of its own artists in its acceptance table;
the reading is not gated.

### 8. Axis tips

A mirrored axis and the axis of a twin system have no tip by default; `set_tips` gives
them one *(default taken)*. This answers the open question of the stage 2 page.

## Consequences

- The release moves back by tasks 15-23, and the public API it freezes has been
  exercised by a second scale, a coupled map and a region payload.
- `docs/scope.md`, `docs/parity-survey.md` and the documentation are amended task by task,
  not in one pass at the end.
- The parity survey's *Calculus*, *Drop lines* and *Polar* sections and `get_vector`
  move to tier 0.1; `plot_implicit_curve` moves only if task 21 delivers it.
