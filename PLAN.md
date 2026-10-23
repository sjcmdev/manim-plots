# Plan: manim-plots functional scope and public API (task/03)

_Locked via grill — by Claude + the maintainer, 2026-09-04/05._
_Revised after Codex review rounds 1-8, 2026-09-05._

Full reasoning and the rejected alternatives are in `docs/grill-log.md` (D1-D16).
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
  and 0.22.0, Python >= 3.12, NumPy >= 2.5, Cairo renderer. CI runs Python 3.12 and 3.13
  against both Manim versions.
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

**Points are derived, never stored.** `points = Chain(data)`, where the chain runs
`Source -> Map -> placement` in order. The data channel writes the source and the map's
data-space nodes; the geometric channel appends and edits the placement nodes at the
tail. Nothing is lost on rebuild because there is no state to lose.

**Placement is an ordered chain, not one matrix.** A single accumulated affine `T` plus a
replayed list of non-affine callables gets the order wrong: `apply_function(f)` then
`shift(v)` must compute `shift(f(points))`, and a matrix-plus-side-list computes
`f(shift(points))`. So the placement tail is the same ordered node chain as the rest of
`Map`: affine and non-affine nodes interleaved in call order, with adjacent affine runs
collapsed into one matrix as an optimisation. `T` in the rest of this document names that
tail, not a single matrix. Non-affine nodes are unbounded in number, deliberately.

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
at all (`:559`). No setter sees either. So four rules, not one:

1. **The getter returns the cache object itself** while the pipeline is clean — not a
   fresh array, not a copy, not a read-only view. An in-place write therefore lands in
   the buffer that gets drawn and survives until something dirties the pipeline. That is
   precisely what `Create`, `Uncreate`, `Write`, `ShowPassingFlash` and `Wiggle` need, so
   in-place writes need no hook at all.
2. **A shadow copy of the last derived output is the transient-mode test.** The exposed
   buffer differing from the shadow means somebody wrote in place, and that single O(n)
   comparison is what both the getter and the geometric overrides consult before they
   change any state. No animation registry, no lifecycle, no list of blessed animations.
3. **`shift` and `apply_points_function_about_point` are overridden** on our classes as
   an exact fast path — and they run the shadow test first. Buffer clean: a direct call
   knows its own affine and appends it to the placement chain, so `ax.shift(v)` is exact
   and permanent. Buffer dirty: the call is part of an in-flight animation, applies to the
   buffer instead, and warns naming `refresh()`. This is what makes `Wiggle` work, which
   writes points in place and *then* calls `submobject.scale(...)` and
   `submobject.rotate(...)` on the same leaf every frame
   (`indication.py::Wiggle.interpolate_submobject`, `:559-567`); appending those to the
   chain would distort the plot cumulatively and never restore it.
   `indication.py::ApplyWave`'s homotopy and anything else built the same way fall out
   correctly for the same reason.
4. **The setter classifies whole-array assignments into exactly two cases.** Same shape
   and a recoverable affine delta against the cache, arriving through our own override:
   append to the placement chain, permanently. Anything else — a shape change, a
   non-affine rewrite, a write from a foreign parent: adopt the array as a *transient
   override buffer*, leaving the pipeline intact, to be replaced at the next rebuild.
   Nothing detaches, nothing raises. `mobject.py::Mobject.interpolate`'s whole-array write
   (`:3173`) lands in the second case and works, and so does `indication.py::Indicate`,
   which is a `Transform` whose `create_target` copies and scales (`:164-168`).

**The transient contract covers a named list, not a category.** The shadow test cannot
tell an animation's temporary geometry from a user's own mutation, and Manim gives no hook
to open a context on an animation we do not own. So the contract is scoped to animations
the library names and tests, and everything else is explicitly the user's responsibility:

- **Restoring animations** — `Create`, `Write`, `ShowPassingFlash`, `Indicate`, `Wiggle`,
  `ApplyWave`, `Flash`, `Circumscribe`. Each ends with the buffer equal to the derived
  points, either by ending at the full shape or by being there-and-back, and each gets a
  test asserting exactly that. The buffer going clean *is* the clear event, so a rebuild
  deferred during the animation runs the moment the getter observes `buffer == shadow`
  with a dirty flag pending. Nothing manual is needed on this path.
- **Removing animations** — `Uncreate`, and anything else built the same way.
  `creation.py::Uncreate` (`:180`) is `Create` with `reverse_rate_function=True` and
  `remover=True` (`:200-208`), so it ends with degenerate geometry and takes the mobject
  out of the scene. It is supported *as a removal*: the buffer is left degenerate, which
  costs nothing because the mobject is no longer drawn, and any rebuild dirtied meanwhile
  stays deferred. Re-adding that artist to a scene requires `artist.refresh()`, which
  rebuilds from the pipeline — the data was never touched. This is stated in the API docs
  next to `Uncreate`, and tested.
- **Everything else, including a user's own in-place write** — not covered. A geometric
  call on a dirty buffer warns and names `refresh()`, and the docs state that a hand-write
  to `artist.points` must be followed by `refresh()` before the data channel is used
  again. The library does not attempt to distinguish an unrestored user edit from a
  running animation, because it cannot; it says so instead of guessing.

A future Manim release adding a non-restoring animation is caught by the per-animation
test on upgrade, not by runtime detection.

### The pipeline

**One pipeline: `Source -> Map -> Shape`.** Source data is immutable; a range change adds,
removes or modifies a node, never the data. `Source` is where analytic and numeric input
differ and the only place they differ — a range change *resamples* a function and merely
*filters* an array. `Map` is the point-to-point chain owned by the coordinate system,
with the placement chain as its tail; adjacent affine nodes collapse into one matrix,
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
view object is deferred past 0.1.

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

### `.animate` needs `override_animate`, not Manim's default

Manim's `.animate` is a copy-and-transform: `mobject.py::_AnimationBuilder.__init__`
calls `generate_target()`, a deep copy (`:3418`), `transform.py::_MethodAnimation` is a
`MoveToTarget` interpolating the original's family leaves toward the copy's, and only
`_MethodAnimation.finish` calls the real method on the real object (`:448-450`). Applied
to this design that is wrong twice over: registered artists are not in the system's
family, so `ax.animate.shift(v)` leaves them standing still and jumps them on the last
frame; and `ax.animate.set_range(...)` interpolates points between an original and a copy
that owns a *different* map and registry, which is exactly the point-alignment
interpolation this plan rejects.

Manim's supported hook is `mobject.py::override_animate` (`:3495`), consulted by
`_AnimationBuilder.__getattr__` before the copy path (`:3441`, `:3450`). **Every
manim-plots method that writes the placement chain, the map, or a bound parameter carries
it**, and returns an animation that interpolates the value on the *live* object, letting
the ordinary dirty-and-rebuild path draw each frame. This is the mechanism the
"interpolate parameters, never points" decision requires; without it that decision does
not survive contact with `.animate`.

Inherited ceiling: an overridden method cannot be chained with another under one
`.animate` (documented at `mobject.py:3510`), so `ax.animate.shift(v).set_range(...)` is
two animations in an `AnimationGroup`, not one chain, and attempting the chain must raise
a clear error rather than produce a confusing frame sequence.

### Containers and attachment

**A foreign parent's transform is transient, and `mp.Group` is the supported way to make
it permanent.** Manim gives a child no transaction boundary: `mob.points += v` is a getter
*followed by* a setter, so a container's loop over leaves cannot be recognised as one
operation from inside a leaf. Rather than infer a boundary that does not exist,
`VGroup(ax, curve).shift(v)` is accepted as the transient-override case — visually correct
at once, and replaced whenever the pipeline next rebuilds.

`mp.Group` is the permanent alternative, and it is **not a `Mobject`**. A family traversal
cannot reach registered artists — they are deliberately not submobjects — and making the
group a `VGroup` would reintroduce the parenting hazard D11 removed. It is a broadcast
handle: it holds its members and forwards a geometric call to each member's own method.
`mp.Group(ax, curve).shift(v)` calls `ax.shift(v)`, which already carries every artist
registered to `ax`. Its `animate` broadcasts to the members' overridden animations inside
an `AnimationGroup`.

**Attachment is registration, not parenting** (revises an earlier decision). An artist is
never a submobject of the coordinate system. Visibility is the user's
(`self.add(ax, curve)`), binding is `ax.add(curve)`, and transformations carry through the
system's placement chain rather than through the mobject tree. This removes the
`Scene.add` hazard entirely — `scene.py::Scene.add` (`:491`) splices a parent out of the
scene list via `family_ops.py::restructure_list_to_exclude_certain_family_members`
(`:22`). An attached artist has no geometric channel of its own: a direct geometric
operation on it is a warned no-op, because the system's chain is what moves it.
`ax.shift(v)` moves the system and every artist bound to it, exactly and permanently, and
`ax.animate.shift(v)` does the same per frame through its `override_animate`.

**Supported mutation surface for 0.1:** the Cairo renderer on Manim 0.21.0; our own leaf
types; Manim's geometric methods; the creation animations `Create`, `Uncreate`, `Write`
and `ShowPassingFlash`; the indication animations `Indicate`, `Wiggle`, `Flash`,
`Circumscribe` and `ApplyWave`; and in-place writes to the array the getter returns, for
as long as nothing rebuilds. OpenGL is already out of scope. Anything outside this surface
is documented as unsupported rather than silently half-working.

Deliberate ceilings, documented rather than prevented: a shape-changing external write is
discarded at the next rebuild — that is what makes `Create` work and what makes a
hand-edited point array not survive a range change; and geometry may transiently differ
from the model during an animation, which is what every Manim mobject does mid-`Create`.

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
not express `Indicate(...)` or an updater on a label. Unchanged deliberate ceiling (D10):
a part that leaves the range and returns gets a fresh mobject and loses hand-applied
styling.

### API

Names do not collide with Manim's. `ax.plot(...)` is the familiar front door dispatching
on argument type, with `ax.plot(f)` / `ax.line(xs, ys)` / `ax.scatter(...)` as the
documented verbs. Parameters are descriptors, not `__setattr__`. `@` means coordinate
conversion, matching Manim (`number_line.py::NumberLine.__matmul__`, `:674`;
`coordinate_systems.py::CoordinateSystem.__matmul__`, `:1864`), and is never used for
parameter binding. Manim's `x_range=(start, stop, step)` triple is accepted, but its third
element is sugar installing a `Multiple(step)` locator rather than part of the range; a
later `set_locator()` replaces it, and `set_range()` never touches it. Explicit named style
parameters and enums, no matplotlib shorthand. Dashes are parameterised by arc length, not
point index. `scale` scales stroke width too, deliberately diverging from
`vectorized_mobject.py::VMobject.scale`'s `scale_stroke=False` default (`:487`): the factor
is `sqrt(|det A|)` of the recovered 2D affine part, which is unambiguous under a nonuniform
scale, applied wherever the affine is recoverable and skipped with a debug warning where it
is not. `artist.refresh()` is the public escape hatch that clears a transient override and
forces a rebuild.

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
frame** — under a quarter of a 60 fps frame budget, leaving the renderer the rest. CI
checks **both** `p95 <= 4 ms` and `p95 <= 1.5x` the recorded baseline, and recording a
baseline fails if the absolute target is missed, so a slow baseline cannot ratify itself.
The benchmark records the machine it ran on, because CI hardware is not the maintainer's
machine. This is what makes affine collapse a requirement instead of an ornament.

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
- **Every mutating public method needs an `override_animate`, and forgetting one fails
  quietly** — `.animate` silently falls back to copy-and-transform and the artists stop
  following. The test is mechanical: assert that each public mutator on a coordinate
  system or artist has `_override_animate` set.
- **The restore contract is on animations we do not own.** A future Manim release could
  change one of the eight named animations so it no longer ends on the derived points, and
  nothing in our code would prevent it — only the per-animation test would catch it, on
  upgrade. `Uncreate` is already the exception that proves the rule.
- **An unrestored user write suppresses data rebuilds until `refresh()`.** The library
  cannot tell that case from a running animation and does not try. It warns on the
  geometric call and documents the requirement; a user who ignores both gets a plot that
  stops responding to its own data, which is the cost of supporting in-place animation
  writes at all.
- **`VGroup(ax, curve).shift()` is transient, and the reflex is universal.** It looks right
  and then reverts at the next rebuild. `mp.Group` is the answer, but discoverable only if
  the docs say so on the first page that shows a plot and a system together.
- **Getter-returns-the-cache is load-bearing.** It is what makes `Create` and `Wiggle`
  work. Any future optimisation that returns a copy or a read-only view silently breaks
  them, so it needs a test that asserts object identity, not just array equality.
- **Per-frame rebuild cost.** The gate above is a number, but it has not been measured and
  the first design may not meet it.
- **Adaptive refinement density lags one frame** when the map and the sampling density
  change together. Accepted; the drawn geometry does not lag.
- **Parity with Manim (D15) was found late.** Now inventoried: 73 public names, 43 of
  them 0.1. Still uncosted in time, but no longer unbounded.
- **The defect audit is verified** against 0.21.0 (`docs/defect-audit-0.21.md`), and
  every reproducing defect has an `F-*`.
- **Origin is unpinned evidence.** Its help page names no release, so no 0.1 requirement
  rests on it alone; see the note opening section 3 of the parity survey.
- **`self.add(curve)` on an attached artist** cannot be intercepted; it is documented as
  unnecessary rather than prevented.

## Out of scope

Pie, box and violin plots; statistics and curve fitting; a GL backend; an interactive
GUI; subclassing Manim's `Axes` / `NumberLine`; matplotlib parity as an end in itself.

Deferred to 0.2 or later: polar; 3D; an independent second scale; broken axes;
`fill_between`; error bars; `step`; histograms and bars; value-mapped colour and
colorbars; annotations; inset axes; date/time axes; linked axes; zoom plots; colour
themes; contours, vector fields and stream lines; Riemann rectangles and area; general
predicate or disjoint-region domains; one artist shared across two coordinate systems.
