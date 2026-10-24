# Plan: manim-plots functional scope and public API (task/03)

_Locked via grill — by Claude + the maintainer, 2026-09-04/05._
_Revised after Codex review rounds 1-8, 2026-09-05._
_Revised after the four task/04 proofs of concept, 2026-10-24 (D17-D21 in the grill
log). The shadow test, the placement chain kept by the library, `mp.Group` and the
data-mutator `override_animate` are gone; the sections below say what replaced them._

Full reasoning and the rejected alternatives are in `docs/grill-log.md` (D1-D21).
The annotated API sketch with the maintainer's own comments is `docs/api-sketch.md`.
The adversarial review, and what was accepted or rejected from it, is
`PLAN-REVIEW-LOG.md`.

**Citations in this document name a symbol first and a line second.** Everything cited is
verified against the Manim in the project's own `.venv` — **0.21.0** — with line numbers
as a parenthesised hint for that version only. Round 7 of the review caught this plan
citing a different interpreter's 0.20.0 by mistake; symbols survive a version bump,
line numbers do not.

## Goal

Decide what manim-plots is, what ships in 0.1, and what the public API looks like,
before any module layout or code exists. The library is a *coordinate-system engine*
for Manim with a thin layer of data artists, built from scratch on Manim primitives and
not subclassing `Axes` / `NumberLine` / `NumberPlane`. A feature enters scope only if it
has an animated or pedagogical payoff. The output of this task is
`docs/parity-survey.md` (source material) and `docs/scope.md` (the `F-*` requirement
list with tiers).

## Approach

1. Codex adversarially reviews this plan (read-only), into `PLAN-REVIEW-LOG.md`.
2. Parity survey across three axes: matplotlib's `Axes`, gnuplot 6.0 `set xtics` /
   OriginPro, and Manim's own `CoordinateSystem` / `Axes` / `NumberLine`.
3. `docs/scope.md`: every requirement as `F-*` with a tier (0.1 / later / non-goal), a
   rationale, and the decision it follows from.
4. Check the 0.1 contracts on paper against three cases that would force a redesign if
   they don't fit: a date/time axis, the calculus toolkit, and region sampling.
5. Re-validate the 15-defect audit against **Manim 0.21.0**, the version in the project's
   `.venv`; each confirmed defect becomes an `F-*`.

### Acceptance criteria for this task

- `docs/parity-survey.md` and `docs/scope.md` exist, and every `F-*` carries a tier and
  the decision it follows from. **Done**: three parity sections (Manim 0.21.0, matplotlib
  3.11.1, gnuplot 6.0 with OriginPro) and 110 `F-*` requirements with a traceability table
  covering all 18 defects and every collaborator answer.
- The three stress cases are checked against the 0.1 contracts in writing, each ending
  in "fits" or "would force a redesign of X". **Done**, and the third one did not fit:
  region sampling forced the `Source` return type to become a payload with a declared
  kind, segments and topology (`F-114`) before the contract could be frozen.
- The defect audit is re-run against 0.21.0 and written up as `docs/defect-audit-0.21.md`.
  **Done** on `task/01-revalidate-defects`: 12 of 14 reproduce, 1 partially, 1 is gone,
  and the sweep found six more, one of them severe.
- The version matrix is made consistent in the repository, not only in prose. **Done**:
  `pyproject.toml` says `manim>=0.21,<0.23`, `numpy>=2.5`, `requires-python = ">=3.12"`.
  The Python floor moved from 3.11 because NumPy 2.5 itself requires 3.12, so the old
  floor described an install that cannot happen. Supported matrix for 0.1: Manim 0.21.0
  and 0.22.0, Python >= 3.12, NumPy >= 2.5, Cairo renderer. `tools/check.py` runs
  Python 3.12 and 3.13 against both Manim versions.
- Every Manim citation in the design docs names a symbol, and a test imports each cited
  symbol so a rename fails loudly instead of rotting. **Done**:
  `tests/test_cited_symbols.py` walks every `file.py::Symbol` citation in `PLAN.md`,
  `docs/scope.md` and `docs/grill-log.md`.
- `docs/scope.md` carries the per-surface invalid-input table (path sampling, locators,
  `c2p`, `p2c`) that the rule below decides. **Done**, split in two: what raises at
  construction, and what each surface does at use.
- The performance gate below is an `F-*` with the numbers stated here, not a promise to
  pick numbers later.

## Key decisions & tradeoffs

**Plain Manim is the reference** (D17). From the user's side the library behaves and is
spelled as close to plain Manim as possible. Every decision below that diverges says so,
and why.

**Points are derived, never stored.** `points = Chain(data)`, where the chain runs
`Source -> Map -> placement` in order. The data channel writes the source and the map's
data-space nodes. The geometric channel is Manim itself moving the system's frame, plus
an artist's own transform. Nothing is lost on rebuild, because the only geometric state
is the frame, and Manim keeps that.

**The system's placement is a hidden frame, not a chain we keep** (D18). The coordinate
system's family holds an invisible grid of `N x N` nodes over the axes' rectangle.
Manim moves it as it moves any leaf: methods, containers, animations, `.animate`.
Placement is an exact affine solve while the grid is affine, and bilinear interpolation
over its cells otherwise (`N = 33`). `c2p` and `p2c` read it. So the system overrides no
geometric method at all, and `T` in the rest of this document names the frame's map.

The grid ignores partial drawing, stays invisible under every style call, and gives no
boundary anchors, so `Create(ax)` cannot truncate it and it never moves a pivot. Under a
non-affine grid, sparse derived leaves — axis lines, ticks — densify by themselves,
where Manim needs a manual `NumberPlane.prepare_for_nonlinear_transform`. A non-affine map
is still an approximation: within about a pixel at 1080p for smooth maps, a ramp across
one cell for a discontinuous one, and blind to a map that vanishes on every node
(`docs/poc2-frame-lifecycle.md`, `docs/poc4-keyed-alignment.md`).

**An artist's own transform is the one ordered chain left.** It lives in the system's
local space, between `Map` and the frame, so it turns with the axes. Order matters for
the reason it always did: `apply_function(f)` then `shift(v)` must compute
`shift(f(points))`. Adjacent affine nodes collapse into one matrix; any other function is
a barrier.

### Integration: the `points` property on library-owned leaves

`points` is a plain instance attribute in Manim (`mobject.py::Mobject.reset_points`,
`:458`), never a property, so our mobjects redefine it as one. The **getter** is the
lazy-rebuild trigger — Manim offers no camera-read callback, but `get_center`,
bounding-box queries, animations, scene family extraction and updaters all read
`.points`, so the getter is the callback.

The property must live on the **leaves**, not only on the artist. Manim's geometric and
animation code reaches `family_members_with_points()` and touches each leaf's `.points`,
never the container's method. So every mobject the library generates — curve segments,
ticks, labels, grid lines, legend entries — is a manim-plots type carrying the property.
That is a hard requirement of the design, not an implementation detail.

Method overrides alone are not enough. `mobject.py::Mobject.shift` (`:1282-1283`) writes
`mob.points += total_vector` directly rather than going through
`apply_points_function_about_point`, and *both* it and
`mobject.py::Mobject.apply_points_function_about_point` (`:1582-1584`) iterate
`family_members_with_points()` and assign to each leaf's `.points`. Those two are the
only geometric writes in `Mobject`; `scale`, `rotate`, `stretch`, `flip`, `apply_matrix`,
`apply_function`, `move_to`, `next_to`, `align_to` and `scale_to_fit_*` all route through
one of them.

The property is not a complete hook either, and the design depends on knowing where it
leaks. `vectorized_mobject.py::VMobject.pointwise_become_partial` assigns a fresh buffer
(`:2067`) and then writes **into slices of it** (`:2070`, `:2077`, `:2082`), and
`indication.py::Wiggle.interpolate_submobject` is a pure in-place write with no assignment
at all (`:559`). No setter sees either. So five rules, not one:

1. **The getter returns the cache object itself** while the pipeline is clean — not a
   fresh array, not a copy, not a read-only view. An in-place write therefore lands in
   the buffer that gets drawn and survives until something dirties the pipeline. That is
   precisely what `Create`, `Uncreate`, `Write`, `ShowPassingFlash` and `Wiggle` need, so
   in-place writes need no hook at all.
2. **Inside an animation the buffer is transient** (D19).
   `animation.py::Animation.begin` suspends the animated family (`:213`) and
   `animation.py::Animation.finish` resumes it (`:227`); our leaves override both, and
   between them a write lands in the buffer and nowhere else.
   `transform.py::Transform.begin` aligns before it suspends (`:211`), so when
   `Transform.begin` is on the stack the transient section opens at that `align_data`.
   This is what makes `Wiggle` work. It writes points in place and *then* calls
   `scale` and `rotate` on the same leaf every frame
   (`indication.py::Wiggle.interpolate_submobject`, `:559-567`). `ApplyWave`, `Indicate`
   and every `Transform` work for the same reason. The shadow test that used to decide
   this could not tell `Wiggle`'s restoring write from a direct call, and is gone
   (`docs/poc-points-property.md`, H2).
3. **At the end, the leaf takes the state Manim would leave.** If the animation ended on
   its target — `Transform`, `Rotate`, `MoveToTarget`, `.animate` — the artist adopts the
   target's source, parameters, own transform and style. A target that is not an artist
   detaches it into that shape, kept in system-local coordinates. A remover leaves it
   detached in whatever state the animation left: degenerate after `Uncreate`, restored
   after `FadeOut`, whose cleanup interpolates back
   (`fading.py::FadeOut.clean_up_from_scene`, `:190-192`). An introducer starting on a
   detached artist, or `refresh()`, re-attaches it. `become` adopts the other artist's
   state outright, because `mobject.py::Mobject.become` writes points outside any
   animation (`:3308-3310`).
4. **Outside animations, a write is attributed from the call stack, never guessed.** The
   setter finds the writing frame — `mobject.py::Mobject.shift` or
   `mobject.py::Mobject.apply_points_function_about_point` — and the container in it. If
   that container's family holds the system's frame, the write is ignored: the frame moved
   in the same operation, which is how `VGroup(ax, curve).shift(v)` moves the curve once.
   Otherwise the write is the artist's own transform: the exact vector from `shift`, the
   exact matrix from the locals of `rotate`, `scale`, `stretch` or `apply_matrix`, and any
   other function as a non-affine node. A bare NumPy write has no writer and is replaced
   at the next rebuild.
5. **The stack is a pinned contract.** Frames are matched by code object, their locals
   copied and the frames released; Manim is never patched. Every frame and local the
   mechanism reads is listed with its symbol, and a source-hash test fails on an upgrade
   that moves one (`docs/poc4-keyed-alignment.md`, *Updated stack and source contract*).
   Rejected: inferring the operation from deltas between leaves, or from the order of
   `get_family` calls (D19).

**No named list of supported animations.** The lifecycle depends on
`Animation.begin`, `Animation.finish` and two writer frames, not on which animation is
running, so an animation Manim adds later is covered as soon as it goes through them.
What stays per animation is a regression matrix: for each animation of the proofs of
concept, the end state is compared with what Manim leaves on a plain `VMobject`, before
and after the next rebuild. That matrix is a test, not a whitelist. A Manim release that
moves one of the frames is caught by the contract test of rule 5 on upgrade.

**One intentional difference in the lifecycle.** `creation.py::Uncreate` (`:180`) is
`Create` with `reverse_rate_function=True` and `remover=True` (`:200-208`), so it ends on
degenerate geometry. In Manim, a later `Create` of that mobject draws nothing, because it
draws from the degenerate buffer. Ours re-attaches at the introducer and draws the
current curve. Every other end state, re-adding after `Uncreate` included, is Manim's.

### The pipeline

**One pipeline: `Source -> Map -> Shape`.** Source data is immutable; a range change adds,
removes or modifies a node, never the data. `Source` is where analytic and numeric input
differ and the only place they differ — a range change *resamples* a function and merely
*filters* an array. `Map` is the point-to-point chain owned by the coordinate system,
ending in the system's local space; an artist's own transform follows it, and the frame
places the result in the scene. Adjacent affine nodes collapse into one matrix,
non-affine nodes are barriers to that collapse and otherwise ordinary. `Shape` (clipping,
discontinuity splitting, smoothing, dashing) is owned by the artist and kept out of `Map`
because it changes the point count. Clipping happens in the system's local space: data
space gives wrong bounds under a log scale, scene space would change on every shift. Same
design as matplotlib's transform tree.

**Rebuild is three ordered phases, not a cycle.** Adaptive sampling needs the compiled
map and clipping needs the artist's shape semantics, which reads as circular ownership
unless the order is fixed. It is fixed: (1) the coordinate system compiles `Map` and
publishes its bounds; (2) each source samples against those published bounds; (3) each
artist runs `Shape`. Phase 2 reads phase 1's output of the *same* rebuild, so the drawn
geometry is always a correct plot of the current parameters — there is no lag in what is
drawn. What may lag one frame is adaptive *refinement density*: the sampler chooses how
many points to spend using the error estimate from the previous frame's map. That
changes the sample count, never the correctness of the samples, and the test asserts
exactly that.

**One artist belongs to one coordinate system.** Binding is single-owner and it is a hard
invariant, not a convention: `ax2.add(curve)` on a curve already bound to `ax1` raises
rather than silently rebinding it. Showing one dataset in two systems is two artists over
one shared immutable source, which costs nothing because sources are immutable. A shared
view object is deferred past 0.1. The one rebinding a Manim idiom implies happens on its
own: after `ReplacementTransform(ax, new_ax)` the artists bound to `ax` belong to
`new_ax`, because that is the system left on screen (D20).

**The data channel is animatable by interpolating parameters, never points.** Point
counts change under clipping, splitting and resampling, so alignment-based interpolation
produces frames that are not plots of anything. Interpolating the *arguments* and
rebuilding makes every frame a correct plot. Rebuild is lazy and dirt-driven: a setter
marks a node dirty, the rebuild happens in the `points` getter, and stops by itself when
nothing dirties anything.

Bound parameters are detected by polling, not subscription — the cheapest correct
notification is a version counter, and reading an `int` costs what reading a `float`
costs. Our own parameters carry that counter and never compare values at all. A binding
to something foreign, such as a Manim `ValueTracker`, is snapshotted immutably and
compared by type, because sloppy equality here means either a missed frame or a rebuild
every frame forever: scalars compare NaN-aware, so `NaN` equals `NaN`; arrays compare with
`np.array_equal(..., equal_nan=True)` against a copy, never against a live view; a
callable binding is always dirty.

**The plot function is a callable binding** (D21), so it is always dirty. It is sampled
once per rendered frame, never once per read, which needs a per-frame tick. Cairo needs
one anyway: `scene.py::Scene.get_moving_mobjects` (`:937-946`) treats everything before
the first animated or updating mobject as static, and
`cairo_renderer.py::CairoRenderer.play` (`:110`) draws it once as a background. That
would freeze a bound artist through any animation it is not part of. So every library
mobject carries an updater without `dt`. The updater marks callable sources dirty once
per frame and keeps the artist out of the static background. Because it takes no `dt`, a
frozen `wait` stays frozen and samples nothing. `ax.plot(lambda x: a.get_value() * x)`
therefore follows `a` like an `always_redraw` would, and `always_redraw` still works.

**Morphing is per-artist and refuses what it cannot resample.** `Morph(a, b)` asks `a`'s
source to resample on `b`'s parameterisation before interpolating, along arc length for
array sources. That is correct for a continuous curve and wrong for scatter points,
discontinuous paths, degenerate or repeated points and disjoint analytic domains, so
each artist declares its own morph semantics and `Morph` raises on a pair whose topology
it cannot honestly resample rather than producing a plausible-looking wrong frame.
`Morph` is the artist-aware answer to `Transform`; Manim's `align_points` inserts
duplicate points, which is the source of its jitter, and stays only as an explicitly
requested fallback.

**One invalid-input rule, four surfaces.** A contract violation raises at construction
time — a non-vectorized scale function, a non-invertible pair, a malformed domain. A
value that turns out to be invalid *at use* is then handled by what the surface can
express, which is the only thing that differs:

- **Path sampling** — a `NaN` or `±inf` output, or an argument outside a map node's
  domain, breaks the path into segments at that point and warns once per artist per
  rebuild. Neither silently dropped nor drawn, because `ax.plot(lambda x: 1/x)` and
  `ax.plot(log, x=(-1, 10))` are both day-one cases and any other answer is wrong on one
  of them. This is what turns the audit's `LogBase.inverse_function` silent-`NaN` defect
  into something visible.
- **Tick generation** — a locator filters out-of-domain candidates rather than erroring;
  an axis whose range overhangs its scale's domain simply has no ticks out there.
- **`c2p` / `p2c`** — raise. A scalar conversion has no segment to break, and returning
  `NaN` is the defect being fixed.

The full table is written into `docs/scope.md`; the rule that decides it lives here.
General predicate domains and disjoint valid regions stay a 0.2 concern, checked on paper
against the frozen contracts before they are built.

### `.animate` is Manim's own, for geometry and data

Manim's `.animate` is a copy-and-transform: `mobject.py::_AnimationBuilder.__init__`
calls `generate_target()`, a deep copy (`:3418`), `transform.py::_MethodAnimation` is a
`MoveToTarget` interpolating the original's family leaves toward the copy's, and only
`_MethodAnimation.finish` calls the real method on the real object (`:448-450`). The
earlier plan put `override_animate` on every mutator. Manim refuses to chain an
overridden method with any other (`mobject.py::_AnimationBuilder.__getattr__`,
`:3443-3445`), so `ax.animate.shift(v).scale(s)` — the most common idiom there is —
would have raised. Nothing is overridden now (D18, D21):

- **Geometry needs nothing.** The copy's frame moves, the original's frame interpolates
  toward it, and the artists follow the live frame in every frame.
- **Data goes the same way.** When `transform.py::Transform.begin` calls `align_data` on
  the system (`:211`), the system aligns its own family by role and by tick key. Left to
  `mobject.py::Mobject.add_n_more_submobjects` (`:3079`), the alignment pads by index,
  which in v2 paired the frame with an axis line. The tick pool covers every key along
  the parameter path, so a tick that appears mid-animation has its leaf from the start.
  The frame interpolates its points and the data parameters. Derived leaves rebuild from
  the interpolated parameters instead of interpolating points, so "interpolate
  parameters, never points" survives, and ticks entering or leaving fade. At the end
  the pool is trimmed, and every surviving tick is the object it was before.
- **Nothing doubles.** `_MethodAnimation.finish` replays the methods before the final
  interpolation, and that interpolation then sets the prepared target.

So `ax.animate.shift(v).set_x_range(r)` is one chained animation, every frame of it is a
correct plot (`docs/poc4-keyed-alignment.md`, L1), and a tick's hand-applied style
survives an exit and return inside it. The pool is built from frame-sized samples of the
parameter path; a locator that changes between samples is the case its schedule contract
has to cover.

### Containers and attachment

**A container moves a bound artist exactly once, and permanently.** Manim gives a child
no transaction boundary — `mob.points += v` is a getter followed by a setter — but the
call stack does, and rule 4 of the integration section reads it. A container whose
family holds the system moves the frame, and the artist follows it:
`VGroup(ax, curve).shift(v)`, in either order and nested. A container without the
system moves the artist through its own transform: `VGroup(curve, dot).shift(v)` moves
both, as in Manim, and the curve keeps responding to its data. Both hold under
`.animate` and inside animations. The broadcast handle `mp.Group` that used to make the
first case permanent is withdrawn.

**Curves follow only permanent changes of their system** (D20). An artist outside the
running animation follows the frame every frame — through `Rotate(ax)`,
`ax.animate.shift(v)` or `Transform(ax, ...)` — unless the animation leaves the system
where it found it. The frame decides that when it is suspended: it simulates the
animation on a deep copy (begin, finish, cleanup) and compares the end with the start.
Through `Indicate(ax)`, `Wiggle(ax)`, `FadeOut(ax, shift=DOWN)` or `GrowFromCenter(ax)`
the artists read a frozen frame and stand still, as plain Manim curves would. Two
consequences are accepted. `Rotate(ax, TAU)` does not turn the curves. And every
animation is simulated, user callbacks included, so a callback with a side effect runs
it once more.

**Code ported from Manim can move a curve twice.** In Manim a graph is not carried by
its axes, so a scene moves both: `self.play(ax.animate.shift(v), graph.animate.shift(v))`.
Here the graph follows `ax` and also takes its own shift. The migration notes say so; the
library does not try to detect it.

**Attachment is registration, not parenting** (revises an earlier decision). An artist is
never a submobject of the coordinate system. Visibility is the user's
(`self.add(ax, curve)`), binding is `ax.add(curve)` or `ax.plot(...)`, and transformations carry through the
system's frame rather than through the mobject tree. This removes the
`Scene.add` hazard entirely — `scene.py::Scene.add` (`:491`) splices a parent out of the
scene list via `family_ops.py::restructure_list_to_exclude_certain_family_members`
(`:22`). An attached artist does have a geometric channel of its own, reversing D11:
`graph.shift(UP)` moves the graph relative to its axes, permanently, as the lesson on
shifting a function's graph expects. The transform lives in the system's local space,
so it turns with the axes afterwards. `ax.shift(v)` moves the system and every artist
bound to it, exactly and permanently, and `ax.animate.shift(v)` does the same frame by
frame.

**Supported mutation surface for 0.1:** the Cairo renderer on Manim 0.21 and 0.22; our
own leaf types; Manim's geometric methods; Manim's animations through the lifecycle
above, with the proofs-of-concept matrix as their regression test; and in-place writes
to the array the getter returns, for as long as nothing rebuilds. OpenGL is already out
of scope.

Deliberate ceilings, documented rather than prevented:
- a bare NumPy write to an artist's points is replaced at the next rebuild, and
  `refresh()` rebuilds on demand;
- a non-affine frame is approximate;
- a generic callback that keeps transforming an artist outside suspension, such as
  `PhaseFlow`, adds one placement node per frame;
- geometry may transiently differ from the model during an animation, which is what
  every Manim mobject does mid-`Create`.

### Coordinate system and decoration

**A coordinate system is one mapping, not a bundle of axes.** Polar is not separable, so
per-axis composition would make it a special case. `Axis` is decoration — line, ticks,
labels, locator, formatter — and does not own the mapping. Separable systems still build
their mapping from per-dimension nodes. Falls out: a mirrored or secondary axis is
another decoration; an aspect lock is a node, not a negotiation.

A user-defined scale is a `Map` node with an enforced contract: forward and backward
functions **vectorized** over a NumPy array, a **declared** monotonic direction, a
declared dimensionality, and a domain. Construction runs a sampled falsification of
monotonicity and round-trip inversion — a heuristic that catches the common mistake, not
a proof, and explicitly unable to see a reversal between samples or on an unbounded
domain. Because a reversal produces visibly wrong output rather than a slightly wrong one,
tick generation additionally asserts that the forward images of the ticks it is about to
emit are ordered, and raises if they are not. That is an O(n) check on a small array, on
the one path where the failure is both likely and unmistakable.

**Generated parts keep identity, and every locator supplies its own key function.**
A tick at `x=2.0` is the same mobject across rebuilds, so
`ax.x.labels.at(2.0).set_color(RED)` survives an animated range change. The key cannot be
the raw float — a recomputation yields `0.30000000000000004` where the user asked for
`0.3` — and it cannot be derived from a step, because log and callable locators have no
step. So `key(value)` is part of the locator protocol: `Multiple(step)` keys by the
integer multiple, a log locator keys by `(decade, mantissa_index)`, a callable locator
supplies its own or falls back to a fixed-significant-digit rounding. Two values that
produce one key out of one locator are a defect in that locator and raise. Formatter
changes do not change keys: a relabelled tick is the same tick, and its mobject is updated
in place. Rejected: a style-override table, which would need a second language and could
not express `Indicate(...)` or an updater on a label. Deliberate ceiling (D10), narrowed
by D21: a part that leaves the range in one edit and returns in a later one gets a fresh
mobject and loses hand-applied styling. Inside one animation the tick pool owns it, so
it returns as the same object.

### API

**Manim's spelling wherever the semantics match** (D17). The constructor takes
`x_range`, `y_range`, `x_length`, `y_length`, `axis_config`, `x_axis_config`,
`y_axis_config` and `tips`, with the `NumberLine` keys under `axis_config`. Its defaults
are those of `Axes()`, so swapping the class keeps the picture. `add_coordinates`,
`get_graph_label`, `plot_line_graph`, `get_x_axis`, `x_axis.numbers` and the rest of the
0.1 rows of the parity survey exist under their Manim names, built on the locator,
formatter and legend machinery rather than replaced by it. New names appear only for
capabilities Manim lacks. An `axis_config` key with no 0.1 capability raises at
construction, naming the key, as the invalid-input rule requires. Star exports do not
collide: `from manim_plots import *` exports `CartesianAxes`, and `mp.Axes` is the same
class under Manim's name. `ax.plot(...)` is the familiar front door dispatching
on argument type, with `ax.plot(f)` / `ax.line(xs, ys)` / `ax.scatter(...)` as the
documented verbs. Parameters are descriptors, not `__setattr__`. `@` means coordinate
conversion, matching Manim (`number_line.py::NumberLine.__matmul__`, `:674`;
`coordinate_systems.py::CoordinateSystem.__matmul__`, `:1864`), and is never used for
parameter binding. Manim's `x_range=(start, stop, step)` triple is accepted, but its third
element is sugar installing a `Multiple(step)` locator rather than part of the range; a
later `set_locator()` replaces it, and `set_x_range()` never touches it. Style keywords are
`VMobject`'s, plus enums for line styles and markers, and no matplotlib shorthand. Dashes
are parameterised by arc length, not point index. `scale` leaves stroke width alone, as
`vectorized_mobject.py::VMobject.scale` does by default (`scale_stroke=False`, `:487`), and
Manim's own `scale_stroke=True` opts in; this supersedes D13's rule that `scale` scales
stroke width. `artist.refresh()` stays public: it re-attaches a detached artist and
replaces a bare in-place edit with a rebuild.

### 0.1 contents and the gate

**0.1 contains the whole engine and four artists** — analytic plot, array line, scatter
and parametric curve — plus a legend and a minimal colour cycle. Ten artists would not
test the contracts better, only delay finding out a contract is wrong.

The parametric curve is the fourth on purpose, added once the Manim parity inventory
made the gap visible. It is the only one of the four whose source maps one parameter to
*two* coordinates, so it is the only one that exercises the `Source` contract on a
multi-component output before that contract is frozen. Leaving it out would also make
`plot_parametric_curve` a straight regression for anyone switching over.

**`input_to_graph_point` is a query against the pipeline, not a lookup in the points.**
`ax.i2gp(x, curve)` — the workhorse of a dot riding a curve, a tangent line, a label
pinned to a graph — answers by evaluating the source and the map at `x`, never by
searching the generated points. So it is exact between samples, it is unaffected by
adaptive resampling, and it survives a rebuild. That makes it part of the `Source`
contract rather than a convenience on top of it, which is why it ships in 0.1 even
though most of its callers, the calculus cluster, are 0.2.

The engine ships with a measurable gate, not an adjective. Scenario: four artists on one
`CartesianAxes`, 2 000 sample points each, one animated parameter dirtying the pipeline
every frame, 1080p60, Cairo renderer. Threshold: p95 pipeline rebuild time **<= 4 ms per
frame** — under a quarter of a 60 fps frame budget, leaving the renderer the rest. The
gate checks **both** `p95 <= 4 ms` and `p95 <= 1.5x` the recorded baseline, and recording
a baseline fails if the absolute target is missed, so a slow baseline cannot ratify itself.
The benchmark records the machine it ran on, because the maintainer works on more than
one machine and a baseline from one says nothing about the other. This is what makes affine collapse a requirement instead of an ornament.

**Target Manim is 0.21.0**, `manim>=0.21,<0.23` for 0.1 — the version in the project's own
`.venv`, which is also what `TODO.md` targets. Everything in this plan that cites Manim
source is verified against it. 0.22.0 is supported as well: the cited symbols and the
parity surface are unchanged on it, and so is every defect probe except two. 0.22.0
fixed 15c and the `point_to_number` half of 15f (ManimCommunity/manim#5039); the probes
assert whichever behaviour the installed version has. Our own F-201 does not change —
the library never calls Manim's conversions.

## Risks / open questions

- **The contracts are frozen in 0.1 and stressed only in 0.2.** Date/time axes, the
  calculus toolkit and region sampling all arrive later. The mitigation is a paper check
  before freezing, which is weaker than an implementation.
- **The plan was written against the wrong interpreter once already.** Every behavioural
  claim was re-verified on 0.21.0 and held, but the class of error is cheap to repeat, so
  the citation test is not optional.
- **Every generated leaf must be a library type.** The property design fails silently the
  day someone drops a plain `Line` or `MathTex` into a decoration, so the test suite has
  to assert leaf types, not only rendered output.
- **The mechanism reads Manim's call stack.** Which frames, which locals and which lines
  is a contract on internals Manim does not promise. It is pinned symbol by symbol with
  source hashes, so an upgrade that moves a frame fails a test instead of misbehaving,
  and the per-animation regression matrix is rerun on every supported version. What a
  hash cannot catch is a change in meaning at an unchanged line; only the matrix can.
- **Simulating every animation runs user callbacks once more.** A callback with a side
  effect — a tracker write, a counter, a print — sees it twice. Accepted (D20), and stated
  next to the rule that curves follow only permanent changes.
- **Introducers capture geometry in their constructors.** `GrowFromCenter` and its
  relatives store a point before `begin`. Re-attaching a detached artist at `begin` must
  refresh those, or re-attach early enough that the constructor reads live geometry. v4
  handled one class by name; the production fix must not be a list.
- **The tick pool covers a sampled parameter path.** It is built from frame-sized
  samples, so a locator whose output changes between two samples needs the pool's
  schedule contract. It is not written yet.
- **Code ported from Manim moves a curve twice** when it animates the axes and the curve
  together. Documented in the migration notes, not detected.
- **Getter-returns-the-cache is load-bearing.** It is what makes `Create` and `Wiggle`
  work. Any future optimisation that returns a copy or a read-only view silently breaks
  them, so it needs a test that asserts object identity, not just array equality.
- **Per-frame rebuild cost.** Measured on the proof of concept only: p95 3.1 ms on the
  affine path and 3.7 ms on the bilinear one against the 4 ms gate
  (`docs/poc4-keyed-alignment.md`, L7). That is a lower bound — no adaptive sampling,
  clipping, tick layout or labels — so the margin is thin.
- **Adaptive refinement density lags one frame** when the map and the sampling density
  change together. Accepted; the drawn geometry does not lag.
- **Parity with Manim (D15) was found late.** Now inventoried: 73 public names, 43 of
  them 0.1. Still uncosted in time, but no longer unbounded.
- **The defect audit is verified** against 0.21.0 (`docs/defect-audit-0.21.md`), and
  every reproducing defect has an `F-*`.
- **Origin is unpinned evidence.** Its help page names no release, so no 0.1 requirement
  rests on it alone; see the note opening section 3 of the parity survey.
- **Adding the system does not add its artists** (F-709), as with a Manim graph: a curve
  is added to the scene on its own.

## Out of scope

Pie, box and violin plots; statistics and curve fitting; a GL backend; an interactive
GUI; subclassing Manim's `Axes` / `NumberLine`; matplotlib parity as an end in itself.

Deferred to 0.2 or later: polar; 3D; an independent second scale; broken axes;
`fill_between`; error bars; `step`; histograms and bars; value-mapped colour and
colorbars; annotations; inset axes; date/time axes; linked axes; zoom plots; colour
themes; contours, vector fields and stream lines; Riemann rectangles and area; general
predicate or disjoint-region domains; one artist shared across two coordinate systems.
