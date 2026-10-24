# Grill log — task/03 functional scope and API

Running record of decisions locked during the Act 1 interview (`/grill-me-codex`).
Not the deliverable. Feeds `PLAN.md`, which feeds `docs/scope.md` and the
architecture ADR. Nothing here is implemented yet.

## D1 — Scope filter

**Locked:** the library is a *coordinate-system engine* with a thin layer of data
artists (option C), and a feature enters scope only if it has an animated or
pedagogical payoff (filter A).

Rejected: matplotlib parity for its own sake — ~250 `Axes` methods, of which maybe
15 matter for mathematical and physical animation.

Consequence: matplotlib, gnuplot and OriginPro are surveyed mainly for *depth of
customisation* (ticks, grids, secondary axes, label control), not for additional
chart types. Static-only chart types (pie, box, violin) enter only on a concrete
request.

## D2 — Artist ownership

**Locked:** a data artist is a standalone mobject that holds its data in data space
and carries an explicit binding to a coordinate system, with `attach` / `detach` as
a public contract.

Manim's own `Axes.plot` cannot express this: it bakes the coordinate system into a
closure evaluated once at construction (`coordinate_systems.py:738`), so the points
are scene-space and no rebuild path exists. Consistency with `ParametricFunction`
and `ImplicitFunction` therefore means matching signatures and vocabulary
(`t_range`, `discontinuities`, `use_smoothing`, `use_vectorized`), not inheriting
from them.

## D3 — What `attach` does

**Locked:** `attach` is one operation that both binds the data and parents the
artist into the coordinate system's data layer; `detach` reverses both.

Rationale: Manim propagates geometric transformations through the submobject tree
(`mobject.py:1560`, `family_members_with_points()`), never through plain object
references — so a binding alone would not make `ax.shift(...)` carry its curves.
Parenting also hands clipping, z-order and legend collection the artist list for
free.

An unattached artist renders in the identity system (scene space). Attaching is a
rebinding, not a change of type.

Known cost: `self.add(ax, curve)` becomes unnecessary and would add the curve twice.
Documentation issue, possibly a warning.

## D4 — Points are derived, never stored state

**Locked:** `points = T · M(data)`, where `M` maps data to the coordinate system's
local space and `T` is the accumulated scene placement.

This turns the two-mutation-channel rule from a discipline into a consequence of the
data model:

- geometric channel (`.shift`, `.scale`, `.rotate`, `.animate`) writes only `T`;
- data channel (`.set_range`, `.set_locator`, `.set_data`) writes only the data or
  `M`.

Nothing is lost on rebuild because there is no state in which it could be lost.

Integration point with the renderer: every geometric transformation in Manim funnels
through `Mobject.apply_points_function_about_point` (`mobject.py:1548`), `.animate`
included. One override, not ten.

Non-affine user transformations (`apply_function`, `apply_complex_function`) are
recorded as an ordered list of callables replayed after rebuild. Deliberate ceiling:
the list is unbounded; add caching only if hundreds of such operations ever appear
in practice.

## D5 — One pipeline, three stages

**Locked:** `Source → Map → Shape`. Source data is immutable; range changes, axis
shifts and rescaling add, remove or modify a node, never the data.

- **Source** — `FunctionSource(f, sampler)` or `ArraySource(x, y)`. This is where the
  analytic/numeric distinction lives and the only place it lives: a range change
  *resamples* an analytic source and merely *filters* a numeric one.
- **Map** — the point-to-point chain, owned by the coordinate system:
  scale → range → aspect → `T`. `T` from D4 is simply the chain's tail, not a
  separate mechanism.
- **Shape** — viewport clipping, discontinuity splitting, smoothing. Owned by the
  artist, because it depends on the artist type, and kept out of Map because it
  changes the number of points, which is what breaks node composition.

A node is `points → points`. Affinity is an optimisation, not a separate kind:
adjacent affine nodes collapse into one matrix when the chain is compiled, non-affine
nodes are barriers to that collapse and otherwise ordinary nodes. Invalidation is
local — `ax.set_range()` invalidates the range node and everything downstream, and
nodes above it are not recomputed.

Clipping happens in the coordinate system's local space: in data space it produces
wrong bounds under a log scale, and in scene space it would change with every shift
of the axes. This is the fix for "plot curves escape the axes viewport".

Prior art: matplotlib's transform tree (`transData = transScale + transLimits +
transAxes`, `is_affine`, invalidation propagation) is the same design, in production
since 2007. Pipes and filters, not chain of responsibility — every node must pass
its output on, none may halt the chain.

## D6 — Node contract

**Locked:**

```
apply(points) -> points        # required
is_affine: bool                # required
matrix -> 4x4                  # required when is_affine
inverse() -> Node | None       # None means the chain is not invertible
domain -> interval | None      # advisory: where apply is defined
```

`inverse` exists because `point_to_coords` — cursor positions, annotation anchors, a
`Dot` riding a curve — has to walk the chain backwards. A non-affine node must
declare its inverse explicitly. The `LogBase.inverse_function` defect (negatives
silently becoming NaN) is exactly an inverse declared without its domain.

`domain` is **diagnostic, not a gate.** The user is never blocked from plotting
outside it. Deliberate: an animation explaining the construction of the logarithm
must be able to show what happens for negative arguments, including drawing the
wrong-but-intuitive curve. Undefined points produce a break in the path and a warning
once per artist, never a silent NaN and never a refusal. Policy is selectable per
artist (`warn` default, `raise`, `ignore`).

Source holds a read-only reference to the compiled Map, so sampling can adapt to
curvature *after* mapping. This is the pipeline's only feedback edge, taken
deliberately: uniform sampling in data space is not uniform on screen under a
non-affine node, which is the cause of Manim's own "may not produce accurate graphs"
warning on `plot`.

## D7 — A coordinate system is one mapping, not a bundle of axes

**Locked:** the coordinate system owns a single `R^n -> R^m` mapping. An `Axis` is a
*decoration* — line, ticks, labels, locator, formatter, bound to one dimension — and
does not own the mapping.

The decisive case is that polar is not separable: `(r, theta) -> (x, y)` couples both
dimensions, and no per-axis composition expresses it. The same holds for log-polar,
Smith charts, any cartographic projection, and any rotated frame. Making the
coordinate system a composition of axes would push all of these into a special-cased
code path — the exact stratification that makes Manim's own graphing module
unmaintainable.

Separable systems still *build* their mapping from per-dimension nodes, so a
Cartesian system with a log x and a linear y needs no ceremony. Non-separable systems
supply one coupled node. Same type, no branch in client code.

Falls out of this:

- a secondary y-axis is just another `Axis` decoration with its own locator, reading a
  different `Map` chain that shares the same `T`;
- an aspect-ratio lock is a node in `Map`, not a negotiation between two `Axis`
  objects — which removes the "aspect distortion from independent length
  parameterisation" defect at its source;
- locators and formatters live on the `Axis` decoration and have nothing to do with
  the mapping.

Supersedes the "composition per axis" sketch from 2026-09-02: composition survives as
a construction mechanism, not as the definition of a coordinate system.

## D8 — The data channel is animatable, by interpolating parameters

**Locked:** animating data never interpolates points. It interpolates the *arguments*
of a data-channel operation and rebuilds through the pipeline, so every intermediate
frame is a correct plot of a real intermediate state rather than a morph between two
plots.

Rejected: point interpolation with alignment (Manim's `Transform`). Different point
counts are unavoidable here — clipping, discontinuity splitting and resampling all
change `N` — and padding produces intermediate frames that are not plots of anything.
Parameter-space interpolation does not solve the point-count problem, it removes it.

### Parameters

Nodes expose named parameters (`range`, `base`, `aspect`). A parameter holds either a
value or a *binding*: our own tracker, a foreign Manim `ValueTracker`, or a plain
callable. No type is privileged — one read path for all three.

We ship our own tracker because it can carry what `ValueTracker` cannot: a
vector-valued parameter (a range is one animatable pair, not two loose scalars), a
name for diagnostics, and a type. The public API exposes both levels: read and write
the *value*, and read and write the *tracker object* bound to a parameter, so a user
can substitute their own.

### Invalidation — lazy, dirt-driven

A setter does not rebuild. It marks its node dirty. The rebuild happens once, just
before the camera reads points, and only from the highest dirty node downwards.

- five setters in one frame cost one rebuild, not five;
- an animated parameter dirties its node every frame, so per-frame rebuild happens
  because it is needed, not because a mode was switched on;
- when the animation ends nothing dirties anything, and regeneration stops by itself.

This is the dynamic-updater idea without an updater: laziness does the switching on
and off for free. One internal updater per artist checks a flag and returns.

Bound parameters are detected by **polling** — read the binding each frame, compare
with the previous value, mark dirty on change. Rejected: change notification with
subscriber registration. It buys nothing even for our own tracker (the cheapest
correct notification is a version counter, and reading an `int` costs what reading a
`float` costs) and it pays for that nothing with a dependency graph that has to be
torn down on `detach` and leaks if it isn't.

### Morphing — resample, don't pad

`Morph(a, b)` asks `a`'s Source to `resample_like(b)` first — regenerating `a` on
`b`'s parameterisation with the same point count and a comparable distribution — and
only then interpolates points. Exact for two analytic sources. For array sources of
differing length, resampling runs along **arc length**, which is where the smooth,
physical look comes from: an even distribution along the curve produces none of the
local bunching that makes `Transform` jitter. Manim's `align_points` inserts duplicate
points and is the cause of that jitter; we keep it only as a fallback for artists that
have no Source.

This means we write our own animation classes. Manim constrains only the endpoint:
the result must land in `points`.

Deliberate ceiling: rebuilding at frame rate is a real cost, not zero. Collapsing
adjacent affine nodes into a single matrix (D5) is therefore a performance
requirement, not an ornament.

## D9 — What 0.1 contains

**Locked.** The engine ships complete; the artists do not.

*Engine (no shortcuts — this is the product):* 2D Cartesian system; linear, log and
symlog scales; the `Source -> Map -> Shape` pipeline with lazy rebuild and affine
collapse; the node contract; `Axis` as decoration with major and minor ticks, tick
direction and grid; locator contract (`MaxN`, `Multiple`, `Log`, `Fixed`) and
formatter contract (number, LaTeX, SI, custom); label overlap resolution; viewport
clipping in local space; `c2p` / `p2c` with domain diagnostics; the animatable data
channel, trackers and `Morph`.

*Artists:* analytic function plot (adaptive sampling), array line plot, scatter.
Three different characters — analytic, tabular, point — which is what exercises the
contracts from three sides. Ten artists would not test them better, only delay the
moment we find out a contract is wrong.

*Plus:* legend.

**0.2 and later:** polar, 3D, an independent second scale (gnuplot's `x2`/`y2`),
broken axes, `fill_between`, error bars, `step`, histogram and bars, value-mapped
colour and colorbars, annotations and arrows, inset axes, date/time axes.

**Explicit non-goals:** pie, box and violin plots; statistics and curve fitting; a GL
backend; an interactive GUI; subclassing Manim's `Axes` / `NumberLine`; matplotlib
parity as an end in itself.

### Collaborator requirements, placed

From the collaborator's list, with gnuplot 6.0 `set xtics` / `set x2tics` as the
reference specification for tick control:

- controlled access to every part of the axes (lines, tick lines, tick labels) — 0.1,
  see D10;
- working control of the zero at the origin — 0.1, it is the `_origin_shift` defect and
  becomes a `Map` parameter;
- axes placed through the origin or at the borders — 0.1, free after D7: position is a
  parameter of the decoration, independent of the mapping;
- gnuplot-style numbering (explicit tick lists, (position, label) pairs, mirroring,
  rotation, minor tick counts) — 0.1, this is the locator and formatter contract;
- dual axes on either side — split in two: a *mirrored* decoration on the same `Map`
  is nearly free and ships in 0.1; an *independent* second scale needs a second `Map`
  chain sharing `T` and waits for 0.2;
- date/time ticks — 0.2, **with a condition**: the 0.1 contracts must be checked on
  paper against the temporal case before they are frozen. Nothing about it is linear
  or evenly spaced, and discovering in 0.2 that `domain` and the locator assume an
  ordered real axis with a constant step would be a redesign. This is an acceptance
  criterion, not a feature;
- time-series and scatter from `[(x1,y1), ...]` or from separate `[x...]`, `[y...]`
  lists — 0.1, one normalising function on `ArraySource`.

## D10 — Generated parts keep their identity, keyed by data value

**Locked:** every generated part (tick, label, grid line) is keyed by its value in
data space. A rebuild reuses the existing mobject for a key that still exists and only
corrects its position; new keys create mobjects, vanished keys drop them.

So `ax.x.labels.at(2.0).set_color(RED)` survives `ax.animate.set_range(...)`, because
the mobject survives.

Rejected: a style-override table on the decoration, reapplied after each rebuild. It
would be consistent with D4 but introduces a second language — the user would register
styles instead of calling `set_color` on a mobject — and it cannot express
`Indicate(ax.x.labels.at(2.0))`, adding a child arrow to a tick, or putting an updater
on a label. Keyed identity costs one `key -> mobject` dict per decoration, which is
less machinery, not more.

This does not contradict D4: points are still derived. What persists is object
identity, not geometry.

Deliberate ceiling: a tick that leaves the range and comes back gets a new mobject and
loses hand-applied styling. Fixable with a cache of recently seen keys if it ever
hurts.

## D11 — D3 revised: attachment is registration, not parenting

**Supersedes D3.** An artist is never a submobject of the coordinate system. Three
concerns that D3 wrongly fused are separated:

| Concern | Owner | Spelling |
|---|---|---|
| visibility in the scene | the user | `self.add(ax, curve)` — plain Manim idiom |
| data binding | the coordinate system | `ax.add(curve)` — registration |
| carrying transformations | the shared `T` | the artist computes through the axes' `Map` |

`ax.shift()` moves the curves not because they are children but because `T` changes,
and `T` is the tail of the `Map` every attached artist computes through (D4, D5). The
rebuild is more correct than transforming points: the curve is recomputed rather than
dragged as a stale shape.

This removes the whole `Scene.add` hazard that D3 carried: `Scene.add` calls
`restructure_mobjects`, which splices a parent out of the scene list and replaces it
with its remaining submobjects (`scene.py:513`, `family_ops.py:34-50`). With no
parenting, there is nothing to splice.

`ax.add(artist)` registers; anything that is not an artist falls through to Manim's
`Mobject.add`. `ax2.add(curve)` re-binds, detaching from `ax1`. `attach` / `detach`
remain as the underlying contract. *(Later superseded: after the Codex review, binding
an artist that already belongs to another system raises — F-112.)*

**Closing the double-transform trap:** an attached artist has **no geometric channel
of its own**. A geometric operation on it is a no-op with a one-time warning. This
matters because `VGroup(ax, curve).shift(...)` is every Manim user's reflex and would
otherwise move the curve twice — once through the axes' `T`, once through its own.
With the geometric channel disabled the old reflex produces the right result by
itself. A deliberate per-artist displacement is an explicit `curve.offset` parameter
instead.

Free (unattached) artists keep their own `T` and render in the identity system.

## D12 — Public API shape

Locked from the annotated `docs/api-sketch.md`. Names remain placeholders; semantics
do not.

- **Names do not collide with Manim's.** `from manim_plots import *` does not fix a
  collision, it hides it: with two `Axes` exported, import order decides the winner and
  the failure is a wrong object drawn, not an exception.
- **Ranges and lengths.** `CartesianAxes(x=(0, 10), y=(-1, 1), x_length=8, y_length=5)`.
  Manim's `x_range=(0, 10, 1)` triple is accepted for familiarity, but the third
  element is **sugar that installs a `Multiple(1)` locator**, not part of the range.
  Keeping the step inside the range is what lets `set_range` and `set_locator` fight
  over one field, which is the "ticks go stale after changing `x_range`" defect.
- **User-defined scales** are the D6 node contract with nothing added: a forward
  function, a backward function, a domain.
- **Artists.** `ax.plot(...)` is the familiar front door, dispatching on argument type;
  `ax.plot(f)` / `ax.line(xs, ys)` / `ax.scatter(...)` are the documented verbs. `plot`
  returns the `Artist` base type, with `@overload` for precise typing. Two spellings
  are accepted here deliberately: Manim users expect `plot`, and the docs steer to the
  verbs.
- **Axis access.** `ax.x` with `ax.x_axis` as an equivalent property.
- **Parameters are descriptors, not `__setattr__`.** Same syntax
  (`ax.x.ticks.direction = OUT`) but interception only on actual parameters.
  `__setattr__` would intercept every assignment, including the hundreds Manim performs
  inside `Mobject.__init__`. Descriptors also give the named-parameter registry and the
  typing for free:
  `ax.x.range = (0, 30)`, `ax.x.range.value`, `ax.x.range.tracker`,
  `ax.x.range.bind(t)`, `ax.x.range.animate_to((0, 30))`.
- **`@` for coordinate conversion**, matching Manim, which already defines it:
  `ax @ (2, 3)` is `c2p`, `point @ ax` is `p2c`, `ax.x @ 2.0` is `n2p`
  (`number_line.py:669`, `coordinate_systems.py:1864`). `@` is *not* used for parameter
  binding — one operator cannot mean both "convert coordinates" and "substitute a
  tracker".
- **Our tracker keeps `ValueTracker`'s API** (`get_value`, `set_value`,
  `.animate.set_value`) and extends it to vector values.
- **Explicit tick lists and generator functions** need no new machinery: `set_ticks(...)`
  is sugar over a `Fixed` locator, and `set_locator(callable)` accepts a plain function.
  Regeneration on a trigger with modifiers preserved is D8 plus D10.
- **Legend:** `ax.legend()` primary, `Legend(*artists)` for spanning several coordinate
  systems, with merge and split. Labels come from `ax.plot(f, label="sin")` preferably,
  `curve.set_label(...)` also allowed.

## D13 — Style channel

**Locked:** explicit named parameters, Manim colours, enums for line styles and
markers. No matplotlib shorthand — neither `"--"` nor `"r--o"`. Compact at the cost of
readability, and unreadable to an IDE, which contradicts the intellisense requirement.

A marker may be any `Mobject`, so a user can supply their own.

**Dashes are parameterised by arc length, not point index.** Manim's `DashedVMobject`
derives dashes from point indices; our point count changes on every rebuild (clipping,
resampling, discontinuity splitting), so index-derived dashes would crawl during a range
animation. Arc-length parameterisation makes the pattern stable at any sampling
density — the same parameterisation already chosen for `Morph` in D8. Dashing is
therefore a Shape-stage node.

**`scale` scales everything, including stroke width.** This is a deliberate divergence:
`VMobject.scale` defaults to `scale_stroke=False` (`vectorized_mobject.py:482`).
Recorded as a decision, not an oversight.

## D14 — Animations we write ourselves

0.1: `DrawAxes` (axis, ticks and labels in a sensible order rather than all at once),
`TraceCurve` (drawn in **data order** — Manim's `Create` on a curve split at
discontinuities draws the pieces in path order, which is arbitrary), `ShowPoints`
(scatter revealed in data order, composable with `TraceCurve` through an
`AnimationGroup`), `Morph` (D8), and the data-channel animation as a public class.

Later: `AppendData` (points arriving over time in a time series), `Rescale` as a
shorthand, `HighlightTick`.

## D15 — A third parity axis: parity with Manim itself

**Found late, and it outranks the other two.** Switching from Manim's `Axes` to ours
currently loses every one of these:

```
get_riemann_rectangles  get_area  get_secant_slope_group  angle_of_tangent
slope_of_tangent  plot_derivative_graph  plot_antiderivative_graph  get_T_label
get_vertical_lines_to_graph  i2gp / i2gc  plot_implicit_curve  plot_parametric_curve
plot_polar_graph  plot_surface  get_lines_to_point  add_coordinates  get_axis_labels
```

That is a regression list, not a wish list: an existing animation about a Riemann sum
raises `AttributeError` after the switch. Parity with matplotlib decides whether people
choose us; parity with Manim decides whether they *can move at all*, and with upstream
inclusion as a long-term goal it is a precondition rather than a nicety.

**Consequence for the deliverable:** `docs/scope.md` gets a third section in which every
public method of `CoordinateSystem` / `Axes` / `NumberLine` receives a verdict — have
it / equivalent under another name / deliberately not / later. Around 40 entries,
bounded and countable, unlike matplotlib.

The calculus cluster (Riemann rectangles, area, secant, tangent, `T_label`,
derivative) is the most valuable part of that list — it is precisely the 3Blue1Brown
audience. Targeted at 0.2, under the same condition as date/time axes: the 0.1
contracts must be checked on paper against it before they are frozen.

### Field artists unify into one pipeline head

Contours, vector fields, stream lines, area shading and 3D surfaces are one family: a
source that samples a function over a *region* instead of along a curve. That is a
third pipeline head beside `FunctionSource` and `ArraySource` — `FieldSource` — with
the artists differing only in what they do with the samples: arrows, stream lines,
isolines, fill, surface mesh. One source, five artists. Designed on paper in 0.1,
implemented later.

Note that Manim's `vector_field.py` knows nothing about axes and works in scene
coordinates; binding a vector field to a coordinate system is itself a fix relative to
Manim.

### Backlog added this session

0.2 or later: linked axes; zoom plots (a magnified region of a plot placed elsewhere in
the scene); colour presets and themes; **value-mapped curve colouring** (temperature
plots and similar); 3D; area shading; contours; vector fields; stream lines; objects
placed into a vector field or stream lines; sliders over a tracked value (Manim's
`get_T_label` pattern); Riemann rectangles; area under a curve.

**Colour cycle is 0.1, not later.** With two curves and a legend, no cycle means
everything is white and the legend distinguishes nothing. A minimal cycle ships; full
theming waits.

**3D** needs no change to the model — D7's `R^n -> R^m` mapping already admits it, and
the blocker is Manim's 3D rendering rather than our design. Still out of 0.1.

## D16 — Deliverable shape for task/03

**Locked:**

- `docs/parity-survey.md` — source material, three axes: matplotlib `Axes`, gnuplot
  `set` / OriginPro, and Manim's own coordinate systems (D15). Long, mechanical, ages
  with its subjects.
- `docs/scope.md` — the decision document: a list of `F-*` requirements, each with a
  tier (0.1 / later / non-goal), a rationale and a link to the decision it follows
  from. Short, important, stable.

Kept apart because folding one into the other means nobody reads either.

---

# Task 04 — decisions after the proofs of concept

Locked with the maintainer on 2026-10-24, after four proofs of concept:
`docs/poc-points-property.md` (v1), `docs/poc2-frame-lifecycle.md` (v2),
`docs/poc3-stack-context.md` (v3) and `docs/poc4-keyed-alignment.md` (v4). v1
falsified the shadow test of D4's integration, and each later one tested the
replacement. Where a decision below supersedes an earlier one, it says so.

## D17 — Plain Manim is the reference for every user-visible behaviour

**Locked:** the overriding usability goal is that, from the user's side, the library
behaves and is spelled as close to plain Manim as possible. D15 made Manim one parity
axis among three. This decision makes it the axis every other one yields to.

- **Manim's spelling wherever the semantics match.** This replaces the rule that a 0.1
  verdict "promises the capability, not the spelling". The constructor takes
  `x_range`, `y_range`, `x_length`, `y_length`, `axis_config`, `x_axis_config`,
  `y_axis_config` and `tips`, with the `NumberLine` keys under `axis_config`.
  `add_coordinates`, `get_graph_label`, `plot_line_graph`, `get_x_axis` and
  `x_axis.numbers` exist under those names. Style keywords are `VMobject`'s. The
  defaults are those of `Axes()`, so swapping the class keeps the picture. New names
  appear only for capabilities Manim lacks: locators, formatters, the legend, `Morph`
  and `set_x_range`.
- **Class name.** `from manim_plots import *` exports `CartesianAxes`; `mp.Axes` is the
  same class, reachable through the module and kept out of `*`. D12's reason stands —
  two star-exported `Axes` let import order pick the winner silently — and a user
  writing `mp.Axes` still writes Manim's name.
- **`scale` leaves stroke width alone, as Manim does.** Manim's own `scale_stroke=True`
  opts in. This supersedes D13's "`scale` scales everything".

## D18 — A hidden frame carries the system's placement

**Supersedes** the placement tail of D4 and D5: the system's transform is no longer a
chain the library keeps, but geometry Manim moves.

- The coordinate system's family holds an invisible grid, `N x N` nodes over the axes'
  rectangle. Manim moves it as it moves any leaf — methods, containers, animations,
  `.animate`. Placement is an exact affine solve while the grid is affine, and bilinear
  interpolation over its cells otherwise. `c2p` and `p2c` read it.
- The grid ignores partial drawing, stays invisible under every style call, and
  contributes no boundary anchors, so `Create(ax)` cannot truncate it and it never
  moves a pivot.
- Under a non-affine grid, sparse derived leaves (axis lines, ticks) densify by
  themselves. Manim requires a manual `prepare_for_nonlinear_transform` for the same
  result.
- Falls out: the system needs no geometric overrides, `ax.animate.shift(v).scale(s)`
  chains natively, and `VGroup(ax, curve).shift(v)` moves the curve once and for good.
  `mp.Group` is withdrawn.
- Accepted limits, measured in v2 and v4: a non-affine map is approximated, within
  about a pixel at 1080p for smooth maps at `N = 33`; a discontinuous map becomes a
  ramp; a map that vanishes on every node aliases; a non-affine `p2c` can pick another
  branch, and a collapsed grid raises.

## D19 — The leaf lifecycle, with operation context read from the call stack

**Supersedes** D4's shadow test and the setter classification. D11's "an attached
artist has no geometric channel of its own" is reversed as well.

- **Inside an animation** — from `Animation.begin` suspending the leaf to
  `Animation.finish` resuming it, and from `Transform.begin`'s `align_data` call when
  that comes first — a leaf's buffer is transient.
- **At the end:** the leaf adopts the animation's target if the animation ended on it,
  as `Transform`, `Rotate`, `MoveToTarget` and `.animate` do. A remover leaves it
  detached in whatever state it left, exactly as in Manim. An introducer or `refresh()`
  re-attaches it to its data. `become` adopts the other artist's state.
- **Outside animations, a write is attributed, not guessed.** The leaf reads the writing
  frame on the stack: `Mobject.shift` or `Mobject.apply_points_function_about_point`
  and the container in it. If that container's family holds the system's frame, the
  write is ignored, because the frame already moved. Otherwise the write becomes the
  artist's own transform, stored in the system's local space. Exact matrices come from
  the locals of `rotate`, `scale`, `stretch` and `apply_matrix`; any other function is
  a non-affine node. A bare NumPy write has no writer and is replaced at the next
  rebuild.
- Frames are matched by code object, and Manim is never patched. Every frame and local
  the mechanism reads is listed and pinned by a source-hash test, so an upgrade that
  moves them fails loudly.
- **Rejected:** inferring the transaction from deltas between leaves, and from the order
  of `get_family` calls. Both were tried on paper and dropped as sources of unexpected
  behaviour. A fact on the stack is not an inference.

## D20 — Curves follow only permanent changes of their system

- When the frame is suspended it receives the animation, simulates it on a deep copy
  (begin, finish, cleanup) and compares the end with the start. If the system comes
  back to where it was, the artists outside that animation read a frozen frame for its
  duration and stand still, as plain Manim curves would. Otherwise they follow every
  frame. All animations are simulated, user callbacks included, so a callback with a
  side effect runs that effect one more time. That cost is accepted.
- Consequence: `Rotate(ax, TAU)` does not turn the curves, because it is not permanent.
- `ReplacementTransform(ax, new_ax)` moves the bound artists to `new_ax`.
- Code ported from Manim that moves both — `self.play(ax.animate.shift(v),
  curve.animate.shift(v))` — moves the curve twice. That is documented and not
  detected.

## D21 — The data channel is native under `.animate`

**Supersedes** the requirement that every data mutator carry `override_animate`, and
the ceiling that chaining one with another must raise.

- When `Transform.begin` calls `align_data` on the system, the system aligns its own
  family by role and tick key, with a pool covering every key along the parameter
  path. The frame interpolates its points natively and the data parameters too;
  derived leaves rebuild from the interpolated parameters instead of interpolating
  points, and entering or leaving ticks fade. At the end the pool is trimmed, and every
  surviving tick is the object it was before.
- Falls out: `ax.animate.shift(v).set_x_range(r)` chains, and a tick's hand-applied
  style survives an exit and return inside one animation (qualifies D10).
- **The plot function is a callable binding** in D8's sense, so it is always dirty. It
  is sampled once per rendered frame, by the synchronisation updater, never once per
  read; a frozen `wait` samples nothing.
- **Every library mobject carries an updater without `dt`.** Cairo draws everything
  before the first animated or updating mobject once, as a static background
  (`scene.py::Scene.get_moving_mobjects`), which would freeze a bound artist through an
  animation it is not part of. An updater without `dt` keeps a frozen `wait` frozen.
- Accepted and documented: a generic callback that keeps transforming an artist outside
  suspension, such as `PhaseFlow`, adds one placement node per frame.

# Freeze review — decisions after two independent reviews

Locked on 2026-10-24 after `docs/reviews/2026-10-24-codex.md` and
`docs/reviews/2026-10-24-claude.md`. Both reviewers concluded "freeze after the listed
blockers". The decisions below close those blockers. Where the maintainer expressed no
preference, the reviewers' smallest fix was taken and is marked *(default taken)*.

## D22 — A plot function is sampled as Manim samples it; live is explicit

**Revises** D21's third bullet. Sampling a callable on every frame broke ordinary Python
closures: three `ax.plot(lambda x: k * np.sin(x))` built in a loop measured y-extents
`[2, 4, 6]` after construction and `[6, 6, 6]` after one `play`. It also cost Cairo its
static background.

- A function is sampled at construction and again whenever the data channel resamples
  it, for a range change or a parameter change. That is Manim's behaviour plus the
  resampling this library exists for.
- It is sampled every frame only when the user asks for it: a parameter bound to a
  tracker (`ax.plot(f, a=tracker)`) or `always_redraw`, which already works through
  `become`.
- The calling convention is Manim's. `use_vectorized=False` is the default and calls the
  function once per sample; `use_vectorized=True` calls it once on an array and is the
  fast path. F-1001 is measured on the fast path and says so.
- Late binding still applies to every resample. A loop that captures its variable by
  reference changes after a range change, so the migration notes show `lambda x, n=n:`.

## D23 — Defect fixes are the default; Manim's look is kept everywhere else

**Narrows** D17's "swapping the class keeps the picture". The library exists to fix the
defects in `docs/defect-audit-0.21.md`, so where Manim's picture *is* a defect, ours
differs on purpose.

- Fixed by default and listed in F-1008: the end tick stays under a tip (F-411); ticks
  are integer multiples of the step, not offsets from `x_min` (F-402); curves are clipped
  to the viewport (F-706); the origin is a parameter, not a clamp (F-203); colliding labels
  are hidden (F-505); several plots get distinct colours (F-803).
- Kept from Manim, because they are defaults and not defects: the ranges, lengths and
  tips of `Axes()`; no tick or label where the axes cross; ticks straddling the line;
  decimal places following the step; numbers off; an axis at the range edge when the
  range excludes zero.
- Same spelling means same meaning. `axis_config={"scaling": LogBase()}` keeps Manim's
  exponent ranges, and string labels given through `add_labels` render in text mode, as
  Manim's `Tex` does. The library's own `scale="log"` takes data values.
- `docs/scope.md` carries the full table, one row per default, which is also the oracle
  of a parity test against Manim's own `Axes`.

## D24 — The leaf lifecycle, cell by cell

**Completes** D19. ADR 0001 §4 holds the state × event table; the rules behind it are
these. Each one closes a cell that a reviewer found undefined or measured failing.

- **Owners, not a flag.** A leaf is transient while any animation owns it, keyed by
  animation identity. An inner finish does not end an outer one. When several owners
  ended on targets, the last to finish wins, as the last write wins in Manim.
- **Copies an animation makes stay attached.** The starting copy and the target copy
  derive from the live frame, so an artist animated while its axes move follows them
  every frame instead of lagging and jumping. Only the animated subject is transient.
- **Resume rebuilds from current data.** Adoption replaces only what the target owns:
  its source, its own transform, its style. Parameter values are always the live ones.
- **Two kinds of detachment.**
  - *Removed*, after a remover. The buffer is frozen exactly as Manim leaves it, and the
    artist is plain geometry: a container moves it once, and it does not follow its axes.
  - *Shaped*, after a plain target such as `Circle()`, or after a non-Transform animation
    that ends away from its start, such as a `Homotopy`. The final shape is kept in
    system-local coordinates and follows the axes but not the data.

  `refresh()` re-attaches either kind.
- **Introducers stay Manim's at construction** *(default taken)*. An introducer built on
  a removed artist sees the geometry it has, as in Manim, and re-attaches at begin. So
  `GrowFromCenter` grows from where the removed curve collapsed. The documented way to
  grow from the current centre is `refresh()` before constructing the animation. No list
  of animation classes is kept.
- **Inside an animation:**
  - `refresh()` is deferred until the last owner finishes;
  - `become` applies at once and cancels the pending targets, because it is the later
    write;
  - `become` with Manim's `match_*` and `stretch` keywords runs Manim's own
    preparation on a copy, then adopts it.
- **Writes without a geometric writer.**
  - `reverse_points` is recorded as a direction on the artist, read from its writer frame
    `Mobject.apply_over_attr_arrays`, so `Create` draws backwards as in Manim.
  - `make_smooth`, `change_anchor_mode`, `insert_n_curves` and `set_points*` are bare
    writes and last until the next rebuild.
- **Copies.** `artist.copy()` shares the source and bindings, is bound to the same system,
  and is *not* registered: it follows the axes, but stays out of the legend and out of a
  replacement's transfer until `ax.add(copy)`. Copies an animation makes are never
  registered. A copy of a removed artist is removed too.
- **Manual `suspend_updating()`**, with no animation on the stack, pauses updaters and
  changes no buffer ownership. An animation that never suspends — `MoveAlongPath`,
  `PhaseFlow` — is outside animations for the leaf, so its writes are attributed.
- **`ReplacementTransform(ax, new_ax)`.** At the system frame's resume, the animation on
  the stack declares that it replaces its mobject with its target, and the registered
  artists transfer to `new_ax`. Their own transforms carry over, because they live in
  local space, and the target's own artists keep theirs. `become` between two systems
  adopts the other's parameters and frame, and the artists stay bound.
- **Pool leaves that are inactive**, like the frame, contribute no boundary anchors.

## D25 — Tick identity is stable across ranges; the pool has spare leaves

**Revises** ADR 0001 Q3's acceptance that a `MaxN` key is relative to the current range.
A pool that is the union of keys along a parameter path needs keys that mean the same
value on every range.

- `Locator.key(value)` is a pure function of the value and the locator's configuration,
  never of the range. Membership — "would this locator emit this value on this range?" —
  is a separate query. Minor-on-major removal and explicit-over-generated merge use
  membership plus key.
- The pool is built at `Transform.begin` from the parameter path sampled at four times
  the frame density of the animation's own alpha. It also allocates spare hidden leaves,
  as many as the largest active count it saw.
- A key first seen at render time takes a spare and fades in. When the spares run out,
  tests raise, and a render warns once and draws that frame without the tick. Measured
  reason: inside `AnimationGroup(run_time=3)` the earlier schedule took 16 samples for 45
  frames and left 14 frames short of ticks.

## D26 — The contracts, closed before the freeze *(default taken)*

- **`Source` and `Payload` stay public, with their types defined** (ADR 0001 §3).
  - `CompiledMap` is a read-only view of the map: forward, inverse, affinity and domain
    mask.
  - `Bounds` is the clip region in local space: a box plus a containment predicate, so a
    disc fits.
  - `Source.at(t)` evaluates analytic sources exactly. Array sources interpolate linearly
    in their parameter and raise on a non-monotone `x` query.
  - `resample_like` is an optional method, required only by `Morph`.
  - The `region` branch is declared, not complete: adding an optional field to `Payload`
    later is not a breaking change.
- **`Map` owns validity.** Each node combines the incoming `valid` mask with its own
  domain and finite-output mask, and rebuilds path segments before the next stage.
  Stages exchange validated payloads.
- **`p2c` is exact where the map is invertible.** That means affine frames and injective
  scales. Under a non-affine frame it inverts the interpolant: it raises when Newton does
  not converge, and the branch it picks is documented. An off-plane point within a
  tolerance is projected; beyond it, `p2c` raises.
- **One pin set per supported Manim version**, and F-1007 names exact versions, 0.21.0
  and 0.22.0. At import, an unpinned version warns. The reviewers found every frame the
  mechanism reads byte-identical in 0.22.0, and all 228 behavioural tests of PoC 4 pass
  there.
- **The core may import SciPy.** Manim already depends on it, and the bilinear path's
  sparse product is 0.14 ms against 1.4-3.8 ms for NumPy gathers.
- **F-1001 is end to end.** It covers `Scene.update_to_time` plus the camera's lazy
  rebuilds, with rasterisation excluded. It runs on both frame paths, with labels from a
  warm glyph cache and an animated range. Setup work is recorded per play, not gated:
  keyed alignment, simulation and the writer's family test, which must be memoised per
  operation. A second check compares a static plot under an unrelated animation with
  plain Manim.
- **Synchronisation updaters only where something can move.** The system and each
  artist report updaters to `scene.py::Scene.get_moving_mobjects` only when the play
  being compiled involves their system or a tracker they are bound to, or when they hold
  a live function. Otherwise they stay in Cairo's static background, as a Manim graph
  would. The play's animations are read from that frame, as the other stack facts are.

## D27 — Manim's surface, case by case *(default taken)*

The reviewers walked 48 example scenes from Manim's own docstrings. These are the
answers D17 and D23 imply, written down so that implementation does not invent them.

- **`plot` keywords.** `use_smoothing` and `use_vectorized` are honoured. A step in
  `x_range` caps the sample spacing; adaptive sampling may go denser, never sparser.
  `discontinuities` with `dt` forces splits. `colorscale` is 0.2 and raises by name in
  0.1. `underlying_function` exists on analytic artists.
- **Poles between samples.** The sampler splits where adjacent samples change sign while
  their magnitude grows past the viewport, as well as at `NaN` and infinity. One warning
  per artist per data change, not per frame.
- **`NumberPlane` is 0.1** as `mp.NumberPlane`, an `mp.Axes` with the grid on and
  `background_line_style` mapped. A standalone `NumberLine` and `ComplexPlane` are 0.2.
  Standalone `FunctionGraph` and `ParametricFunction` stay Manim's own; nothing replaces
  them.
- **`ax.x_axis` speaks `NumberLine`.** `ticks` is the major tick group, `numbers` the
  tick labels, `labels` the custom labels of `add_labels`. The `ax.x.labels` of the API
  sketch becomes `ax.x.numbers`, minor ticks are `ax.x.minor_ticks`, and `get_tick`,
  `get_number_mobject`, `add_numbers` and `add_labels` keep their Manim meaning.
- **Helpers return bound decorations.** `get_graph_label`, `get_axis_labels` and
  `get_x_axis_label` return mobjects that follow their axes as curves do. A `VGroup`
  holding both moves them once. Animating them separately in ported code moves them
  twice, as with curves (D20).
- **`plot_line_graph`** returns Manim's `VDict` with `line_graph` and `vertex_dots`, and
  both are bound artists.
- **`Create(ax)` draws in Manim's order** — the x line, its tip and ticks, then y — and
  the frame is the last member of the family, so its empty lag slot falls at the end.
- **`c2p` and `p2c` on arrays** raise for the whole call and name the first invalid
  index. Raising where Manim returns `NaN` is listed in F-1008.
- **Infrastructure.** Manim's scene caching stays on and must hash a library mobject by
  its derived state. Library mobjects keep identity hashing, because 0.22 puts mobjects
  in a `set`. Constructing one under `--renderer=opengl` raises, naming Cairo.

---

# Next session (historical, end of task/03 Act 1)

Kept as it was written. Every item below was done in task/01 and task/03.

1. **Act 2 — Codex review.** `PLAN.md` is written. Check `codex --version` >= 0.130 and
   that Codex is authenticated, echo the active model, then run the adversarial review
   loop into `PLAN-REVIEW-LOG.md`, max 5 rounds. Codex attacks the *decisions*, not the
   parity tables.
2. **Parity survey** with context7 for matplotlib and Manim, gnuplot 6.0 docs for tick
   control -> `docs/parity-survey.md`.
3. **`docs/scope.md`** — the `F-*` list with tiers.
4. **Paper-check the 0.1 contracts** against the three cases that would force a
   redesign if they don't fit: a date/time axis (unordered, uneven, non-numeric), the
   calculus toolkit (D15), and `FieldSource` (region sampling). Acceptance criterion for
   task/03, not a feature.
5. **task/01 is still open** — re-validate the 15 defects against the *installed* Manim,
   which is **0.20.0**, not 0.21.0 as the earlier note claimed. Each confirmed defect
   becomes an `F-*`.
6. Commit the lot on `task/03-functional-scope`.
