# Functional scope

**Status: the 0.1 tier is frozen, 2026-10-24** (ADR 0001). Adding, removing or changing
a 0.1 requirement now needs a new ADR; 0.2 and later rows may still move. Amended on
2026-10-29 by ADR 0003, which closed the final reviews; each amended row or rule carries
*(ADR 0003)*.

The decision document for task/03, completed in task/04. Every requirement is an `F-*`
with a tier and the decision it follows from. `docs/parity-survey.md` is the source
material; `docs/plan.md` and `docs/grill-log.md` hold the reasoning;
`docs/defect-audit-0.21.md` holds the evidence for every defect cited here.

## How to read this

**Tiers.**

| Tier | Meaning |
|---|---|
| **0.1** | ships in the first release. The engine is complete in 0.1; the artist set is not |
| **0.2** | planned, not scheduled. Nothing in 0.2 may require breaking a 0.1 contract |
| **later** | wanted, no design yet |
| **non-goal** | deliberately never |

**Sources**, cited in the `From` column:

| Tag | Meaning |
|---|---|
| `D<n>` | decision *n* in `docs/grill-log.md` |
| `defect <n>` | finding *n* in `docs/defect-audit-0.21.md` |
| `A<n.n>` | the collaborator's answer *n.n* in `docs/api-sketch.md` |
| `mpl`, `gnuplot`, `origin`, `manim` | a row of the corresponding parity-survey section |
| `stress case <n>` | case *n* of the paper check at the end of this document |
| `PLAN`, `round <n>` | `docs/plan.md`; review round *n* in `docs/reviews/2026-09-05-plan-review-log.md` |
| `task/<nn>` | that task in `TODO.md` |
| `ADR <nnnn>` | an architecture decision record in `docs/adr/` |

A 0.1 verdict promises the capability **and, where Manim has one with the same
semantics, Manim's spelling** (D17, F-1009). This replaces the earlier rule that a verdict
promised the capability only.

---

## F-1xx — Pipeline and rebuild

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-101 | Points are derived by `Source -> Map -> Shape` on every rebuild and are never stored state | **0.1** | D4 |
| F-102 | Rebuild is lazy and dirt-driven: a setter marks a node dirty, the `points` getter performs the rebuild, and the cascade stops when nothing further is dirtied | **0.1** | D4, D8 |
| F-103 | A rebuild runs three ordered phases: the system compiles `Map` and publishes bounds; each source samples against those bounds; each artist runs `Shape` | **0.1** | D5 |
| F-104 | Source data is immutable. A range change resamples an analytic source and filters an array source; neither mutates the data | **0.1** | D5 |
| F-105 | `Map` is an ordered chain of nodes ending in the system's local space; an artist's own transform (F-904) follows it, and the system's frame (F-914) places the result. Adjacent affine nodes collapse to one matrix; a non-affine node is a barrier to that collapse | **0.1** | D5, D18, F-1001 |
| F-106 | `Shape` is artist-owned, may change the point count **and the geometry kind**, dispatches on the payload's declared kind, and returns a payload rather than a bare array (F-114) | **0.1** | D5, stress case 3 |
| F-107 | Clipping happens in the local space of the coordinate system, not in data space and not in scene space | **0.1** | defect 3, mpl 2.3 |
| F-108 | Adaptive refinement *density* may lag one frame; the samples themselves never lag. A test asserts that the drawn geometry is a correct plot of the current parameters | **0.1** | D5 |
| F-109 | Node contract: forward and inverse functions vectorized over `ndarray`, a declared monotonic direction, a declared dimensionality, and a domain | **0.1** | D6 |
| F-110 | Bound parameters are polled by version counter. A foreign binding is snapshotted immutably and compared NaN-aware (`np.array_equal(..., equal_nan=True)` for arrays); a callable binding is dirty once per frame, at the synchronisation updater's token, never on every read of `points` *(ADR 0003)* | **0.1** | D8, ADR 0003 |
| F-111 | `artist.refresh()` re-attaches a detached artist (F-905) and replaces a bare in-place edit of its points with a rebuild from the pipeline | **0.1** | D4, D19 |
| F-112 | An artist belongs to exactly one coordinate system. Binding an already-bound artist raises rather than silently rebinding; `ax.remove(artist)` unregisters it first *(ADR 0003)* | **0.1** | D11, ADR 0003 |
| F-113 | One source shown in two systems is two artists over one immutable source | **0.1** | D5 |
| F-115 | A shared view object, so one artist can be shown in two systems | **0.2** | D5 |
| F-114 | A `Source` returns a **payload**, not a bare array, and so does every stage that transforms one. The fields, their shapes and their invariants are specified below under *The Source payload*; the `region` branch is declared in 0.1 and implemented later. Its type is in ADR 0003; a field added later is optional with a default, which breaks no 0.1 consumer *(ADR 0003)* | **0.1** | stress case 3, ADR 0003 |

### The Source payload (F-114)

| Field | Shape and type | Invariant |
|---|---|---|
| `coords` | `(n, d)` float | the only field `Map` transforms |
| `kind` | `path`, `points` or `region` | decides what `Shape` does, and may change across `Shape` |
| `segments` | `(s, 2)` integer, half-open `[start, stop)` into `coords` | sorted ascending, non-overlapping, every range non-empty, in bounds. An unsplit payload has one segment covering everything; an empty payload has shape `(0, 2)`. `points` and `region` payloads carry exactly one segment, or none when empty |
| `topology` | `None`, or a `(rows, cols)` grid shape with `rows * cols == n`, or an `(m, k)` integer cell array | `None` for `path` and `points`; required for `region`. Cell indices lie in `[0, n)`, `k >= 3` is fixed per payload, a cell's corners are distinct, and the winding is consistent across the payload. A grid means **quad cells** derived in C order: cell `(r, c)` has corners `(r, c)`, `(r, c+1)`, `(r+1, c+1)`, `(r+1, c)`, giving `(rows-1) * (cols-1)` cells |
| `valid` | `(n,)` boolean, or `None` **only** when every sample is valid | **per sample**, never per cell. A cell counts as invalid when any of its corners is. It records validity and nothing else: 0.1 defines no reason vocabulary |

Three rules bind the fields together:

- **An invalid sample stays in `coords`, and `valid` is false at it.** Indices stay
  stable within a payload as it passes from stage to stage, so masking never removes and
  reindexes a sample. Identity across rebuilds comes from tick keys (F-413), not from
  coordinate indices, because resampling changes them. `valid` is the one channel that marks
  invalidity, on every kind; a payload with any invalid sample therefore cannot have
  `valid=None`. How the exclusion is *drawn* differs by kind: a `path` additionally
  leaves the sample covered by no segment, which is how F-705 splits at a pole, while
  `points` and `region` keep their single segment and are excluded by `valid` alone —
  a point is not drawn, and a cell is dropped when any corner is invalid.
- **`Map` transforms `coords` and owns validity** *(ADR 0003)*: each node combines the
  incoming `valid` mask with its own domain and finite-output mask and rebuilds the path
  segments; `kind` and `topology` pass through untouched.
- **`Shape` returns a payload of the same type**, with every field rebuilt to describe
  what it produced. A kind-changing operation builds a fresh payload rather than
  carrying old fields forward: isoline extraction from a region yields `kind="path"`,
  `topology=None`, its own `segments`, and `valid=None` unless it computes a new
  per-sample mask.

Region clipping in 0.1 is **conservative whole-cell removal**: a cell with any corner
outside the viewport is dropped whole, not trimmed. Geometry-accurate trimming is a later
`Shape` node emitting new `coords` and `topology`, which the payload already permits, so
choosing it later breaks nothing.

## F-2xx — Coordinate mapping

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-201 | `p2c` inverts `c2p` to within floating-point tolerance wherever the map is invertible: on every scale under an affine frame, over the whole range. Under a non-affine frame it inverts the frame's interpolant, raises when the inversion does not converge, and documents which branch it returns | **0.1** | defect 15c, D26 |
| F-202 | `c2p` and `p2c` raise on invalid input — a value outside the scale's domain included. They never return `NaN`, and they never clamp: clamping belongs to range configuration (F-311), never to a conversion | **0.1** | defect 8, defect 15c |
| F-203 | Where the axes cross is an explicit parameter of the mapping. By default an axis whose range excludes zero sits at the range edge, as in Manim; defect 13 is kept by default and fixable by the parameter *(ADR 0003)* | **0.1** | defect 13, gnuplot `set xzeroaxis`, ADR 0003 |
| F-204 | A unit size given for an axis is honoured wherever it is passed, or rejected — never accepted and ignored. In `axis_config` without a length it wins over the default length; with an explicit length it raises *(ADR 0003)* | **0.1** | defect 5, ADR 0003 |
| F-205 | Aspect lock is a `Map` node: locking it constrains the mapping rather than negotiating between two independent lengths. `adjustable="length"` (default) keeps the ranges and adapts the length not given; `adjustable="range"` keeps the lengths and widens a range; an over-constrained call raises *(ADR 0003)* | **0.1** | defect 4, mpl 2.2, ADR 0003 |
| F-206 | Axis lengths are constructor parameters (`x_length`, `y_length`), spelled close to Manim's | **0.1** | A1.2 |
| F-207 | `p2c` of a point off the system's plane projects it when the distance is within a tolerance relative to the system's size, and raises beyond it; it is never silently a projection presented as an inverse | **0.1** | defect 14 note, D26 |
| F-208 | Geometric operations never corrupt the mapping: they move the system's frame (F-914), and a regression test covers the operation set that broke Manim 0.19 | **0.1** | defect 14, D18 |
| F-209 | A reversed range (start greater than stop) is legal through the mapping, the locators and the formatters | **0.1** | mpl 2.2 |

## F-3xx — Scales

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-301 | Linear, log with an arbitrary base, and symlog ship in 0.1; symlog is matplotlib's `(base=10, linthresh=1, linscale=1)` *(ADR 0003)* | **0.1** | D9, gnuplot `set logscale`, ADR 0003 |
| F-302 | A user supplies a scale as a forward/inverse function pair with a domain; no enum of blessed scales | **0.1** | A1.3, gnuplot `set nonlinear`, origin scale list |
| F-303 | Scale naming is honest: the forward function is the scale transform, and the inverse is its inverse | **0.1** | defect 10 |
| F-304 | Scale functions are vectorized over `ndarray`; no scalar-only guard that turns an array into `NaN` | **0.1** | defect 8 |
| F-305 | Construction runs a sampled falsification of monotonicity and of round-trip inversion, documented as a heuristic that cannot see a reversal between samples | **0.1** | D6 |
| F-306 | Tick generation asserts that the forward images of the ticks about to be emitted are ordered, and raises if they are not | **0.1** | D6 |
| F-307 | A scale declares its domain; values outside it are handled by the invalid-input rule below | **0.1** | D6 |
| F-311 | A scale normalises a **range** that leaves its domain, so that `x=(0, 10)` under log becomes `(minpos, 10)` instead of propagating `-inf`, through `limit_range(lo, hi, minpos)`, with an unknown `minpos` taken as `1e-300` *(ADR 0003)*. This applies at range configuration only — construction, `set_range`, and each frame of an animated range — and the normalised value is what `ax.x.range.value` reads back. It never applies to a coordinate conversion (F-202), which raises | **0.1** | mpl `limit_range_for_scale` |
| F-312 | Logit, asinh, probability, probit, reciprocal and the rest of the Origin list ship as library scales | **0.2** | origin scale list |

## F-4xx — Tick location

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-401 | Locator protocol: given a range, a scale and an estimate of available label space, return tick values; `key(value)` gives each value an identity that depends on the value and the locator's configuration only, never on the range; membership — would this locator emit this value on this range at this density — is a separate query with the same arguments *(ADR 0003)* | **0.1** | D10, D25, mpl 2.4, ADR 0003 |
| F-402 | Tick values are computed without float accumulation — no `np.arange` over a step | **0.1** | defect 1 |
| F-403 | 0.1 locators: `MaxN`, `Multiple`, `Log` (decades **and** subdivisions between them), `SymLog` *(ADR 0003)*, `Fixed`, `Null`, and a minor-count locator | **0.1** | defect 9, mpl 2.4, origin, ADR 0003 |
| F-404 | A `Fixed` entry is `(value, label, level)`: an explicit list can place a minor tick, not only a major one. A `(value, label)` pair places a major tick *(ADR 0003)* | **0.1** | gnuplot tic list level, ADR 0003 |
| F-405 | Explicit ticks may either replace the generated set or be added to it. On `add`, the two sets are merged by key: an explicit entry **wins** over a generated one with the same key, and it wins whole — its value, its label and its level all survive, and the generated entry is discarded even where the two values differ in the last bit. The merged list is ordered along the axis, which means ascending for an ordinary range and descending for a reversed one (F-209), never input order. A key collision *between two explicit entries* is a user error and raises; a collision inside one generated set is a locator defect (F-413) | **0.1** | gnuplot `add`, origin Special Ticks |
| F-406 | A plain callable is accepted as a locator, and `set_ticks(...)` is sugar over `Fixed` | **0.1** | A3.3, D12 |
| F-407 | A minor tick coinciding with a major tick is removed. This is a distinct mechanism from label overlap | **0.1** | mpl `remove_overlapping_locs` |
| F-408 | The locator is given a label-space estimate derived from rendered label size, so a density-aware locator is possible | **0.1** | mpl `get_tick_space`, defect 11 |
| F-409 | A degenerate tick specification (zero or negative step, empty range) raises an error naming the parameter. During an animation an empty range is a transient state instead: no ticks, collapsed artists, and `p2c` raises in that frame *(ADR 0003)* | **0.1** | defect 15d, ADR 0003 |
| F-410 | A locator filters out-of-domain candidates rather than raising: an axis overhanging its scale's domain simply has no ticks out there | **0.1** | D6 |
| F-411 | Tick range and coordinate mapping are independent of whether an arrow tip is drawn | **0.1** | defect 2 |
| F-412 | Changing the range, the scale, the locator or the formatter regenerates the affected ticks; nothing goes stale | **0.1** | defect 6 |
| F-413 | Generated parts keep identity across rebuilds and through an animated range, keyed by the locator's `key(value)`. Two values yielding one key inside one locator is a defect in that locator and raises | **0.1** | D10, D25 |
| F-414 | Tick spacing does not determine curve sampling density, and curve sampling does not determine tick spacing | **0.1** | defect 15b |
| F-415 | Categorical axes: an index locator, and labels drawn from a dataset rather than from the coordinate. Explicit labels attached to *numeric* positions are 0.1 (`Fixed`); a category as the coordinate is not | **0.2** | mpl `IndexLocator`, origin text labels |

## F-5xx — Labels and formatters

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-501 | Formatter protocol: given the whole tick list, return one string per tick. It is separate from the scale, and it sees all the ticks so that context-dependent labelling is possible | **0.1** | defect 10, stress case 1 |
| F-502 | 0.1 formatters: decimal, format string, LaTeX/scientific, SI, fixed labels, and null | **0.1** | mpl 2.4, gnuplot `set format`, origin |
| F-503 | The formatter protocol also returns an optional axis-level offset string (the shared exponent). It is `None` in 0.1; the slot exists so that filling it in 0.2 is not a breaking change | **0.1** contract, **0.2** content | mpl `ScalarFormatter` |
| F-504 | A plain callable is accepted as a formatter, which covers prefix, suffix, division by a factor and custom expressions | **0.1** | A3.3, origin |
| F-505 | Label overlap has three answers, all in 0.1: drop colliding candidates, rotate, and hide | **0.1** | defect 11, origin |
| F-506 | A label whose value is outside the range is not emitted, and never placed off the end of the axis line | **0.1** | defect 15e |
| F-507 | Changing a formatter does not change a tick's key: the same mobject is relabelled in place | **0.1** | D10 |
| F-508 | Label rotation, offset and justification are parameters | **0.1** | gnuplot, origin |
| F-509 | Percent and logit formatters, text wrapping | **0.2** | mpl, origin |
| F-510 | Tick-label tables, multi-row label blocks | **non-goal** | origin |

## F-6xx — Axis decoration and grid

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-601 | An `Axis` is decoration — line, ticks, labels, locator, formatter — and does not own the mapping | **0.1** | D7 |
| F-602 | `ax.x` and `ax.x_axis` are equivalent properties | **0.1** | A3.1 |
| F-603 | Every generated part is addressable, in `NumberLine`'s vocabulary where Manim has one: `ax.x_axis.ticks` (major ticks), `ax.x_axis.minor_ticks`, `ax.x_axis.numbers` (tick labels), `ax.x_axis.labels` (custom labels from `add_labels`), `ax.x_axis.line`, `ax.x_axis.grid`, and `...at(value)` for one part | **0.1** | collaborator requirement 1, D10, D27, origin Special Ticks |
| F-604 | Tick direction is `IN`, `OUT` or `BOTH`, with length, width and colour set per level | **0.1** | defect 12, gnuplot, origin |
| F-605 | Axis position is `"origin"`, `"bottom"`, `"top"`, a data value, or a fractional offset | **0.1** | collaborator requirement 3, gnuplot `axis \| border`, origin |
| F-606 | A mirrored axis — the same mapping, a second decoration, unlabelled by default | **0.1** | collaborator requirement 5, gnuplot `mirror` |
| F-607 | Grid lines per level, major and minor configured separately | **0.1** | gnuplot `set grid`, origin Grids |
| F-608 | An arrow tip may be drawn at either end of an axis without affecting the mapping or the tick range | **0.1** | defect 2, origin arrows |
| F-609 | Axis title with placement. `get_axis_labels`, `get_x_axis_label` and `get_graph_label` return decorations bound to their system, which follow it as curves do | **0.1** | manim `get_axis_labels`, D27, origin Title |
| F-610 | An independent second scale (`x2` with its own range) | **0.2** | collaborator requirement 5, gnuplot `set link` |
| F-611 | Axis line and ticks limited to the extent of the data | **0.2** | gnuplot `rangelimited` |
| F-612 | Axis breaks | **0.2** | origin Breaks |

## F-7xx — Sources and artists

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-701 | 0.1 ships four artists: analytic function plot, array line, scatter, and parametric curve | **0.1** | D9, manim `plot_parametric_curve` |
| F-702 | `ax.plot(...)` dispatches on argument type; `ax.plot(f)`, `ax.line(xs, ys)` and `ax.scatter(...)` are the documented verbs, and `plot` is typed with overloads. A function's parameters are the names of its signature after the first; every other keyword is style, and a parameter named like a `VMobject` style keyword raises *(ADR 0003)* | **0.1** | A2.1, A2.2, D12, ADR 0003 |
| F-703 | Array input is normalised from either `[(x, y), ...]` or separate `xs`, `ys` | **0.1** | collaborator requirement 7 |
| F-704 | Analytic sources are sampled adaptively, with the density decided by the source and the map, not by the ticks. A step given in `plot`'s `x_range` caps the spacing; `use_smoothing` and `use_vectorized` keep Manim's meaning, and `use_vectorized=False` — one call per sample — is the default | **0.1** | defect 15b, D22, D27 |
| F-705 | A `NaN`, an infinity, an argument outside a node's domain, or a sign change between adjacent samples whose magnitude grows past the viewport splits the path there; `discontinuities` with `dt` forces splits. It warns once per artist per data change, through `ManimPlotsWarning`; an animated range is one data change per play *(ADR 0003)* | **0.1** | defect 15a, D6, D27, ADR 0003 |
| F-706 | Curves are clipped to the viewport | **0.1** | defect 3 |
| F-707 | `i2gp` / `i2gc` answer by evaluating the source and the map at the requested input, so a `Source` exposes point evaluation as well as range sampling. An analytic source is exact; an array source interpolates linearly in its parameter and raises on a non-monotone `x` query | **0.1** | manim `input_to_graph_point`, stress case 2, D26 |
| F-708 | `ax.add(artist)` and `ax.plot(...)` register; an artist is never a submobject of the coordinate system. A registered artist follows the system's frame and also has a geometric channel of its own (F-904). After `ReplacementTransform(ax, new_ax)` the artists bound to `ax` belong to `new_ax`. `ax.remove(artist)` unregisters *(ADR 0003)* | **0.1** | D11, D19, D20, A2.1, ADR 0003 |
| F-709 | Adding the coordinate system to a scene does not add or remove the artists, and adding an artist separately is allowed | **0.1** | A6.1, D11 |
| F-710 | `Morph(a, b)` resamples `a` on `b`'s parameterisation along arc length, and raises on a topology pair it cannot honestly resample | **0.1** | D8 |
| F-711 | Step, bars, histograms, error bars, filled regions, drop lines, reference lines, annotations | **0.2** | mpl 2.1, manim drop lines |
| F-712 | Field sources: implicit curves, contours, vector fields, stream lines, surfaces — one source, five artists | **later** | D15 |

## F-8xx — Legend, style, colour

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-801 | `ax.legend()` collects the registered artists; `Legend(*artists)` spans several systems; legends can be merged and split | **0.1** | A5.1, defect 7 |
| F-802 | A label comes from `ax.plot(f, label="sin")` preferably, and `artist.set_label(...)` is also accepted | **0.1** | A5.2 |
| F-803 | A minimal colour cycle, so that two curves and a legend are distinguishable without configuration | **0.1** | D15 backlog |
| F-804 | Style keywords are `VMobject`'s, plus enums for line styles and markers. No matplotlib shorthand strings | **0.1** | D13, D17, A4.2 |
| F-805 | A marker may be any `Mobject` | **0.1** | D13 |
| F-806 | Dashes are parameterised by arc length, not point index, so a pattern is stable across resampling | **0.1** | D13 |
| F-807 | `scale` leaves stroke width unchanged, as Manim does; Manim's own `scale_stroke=True` opts in | **0.1** | D17 (supersedes D13) |
| F-808 | Legend layout (columns, ordering, box styling), colour themes, value-mapped colour and colorbars | **0.2** | gnuplot `set key`, D15 backlog |

## F-9xx — Animation and Manim integration

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-901 | `points` is a property on **every** library-generated leaf — curve segments, ticks, labels, grid lines, legend entries — not only on the artist | **0.1** | D4 |
| F-902 | The getter returns the cache object itself while the pipeline is clean: not a copy, not a fresh array, not a read-only view. A test asserts object identity | **0.1** | D4 |
| F-903 | Between `suspend_updating` and `resume_updating` of an animation — and from `Transform.begin`'s `align_data` call when it comes first — a leaf's buffer is transient: writes land in it and nowhere else | **0.1** | D19 |
| F-904 | Outside animations, a geometric write is attributed by its writer on the call stack: a container whose family holds the system's frame is ignored, because the frame moved; any other container's operation becomes the artist's own transform, in the system's local space, with exact matrices read from `rotate`, `scale`, `stretch` and `apply_matrix`. A bare NumPy write is replaced at the next rebuild | **0.1** | D19 |
| F-905 | At the end of an animation, an artist adopts the target the animation ended on; a remover leaves it detached in the state it left; an introducer or `refresh()` re-attaches it; `become` adopts the other artist's state | **0.1** | D19 |
| F-906 | A regression matrix plays Manim's creation, indication, transform, movement and composition animations on systems and artists, and compares every end state with what Manim leaves on a plain `VMobject`, before and after the next rebuild. Sampled intermediate frames of `Create`, `Write`, `Uncreate`, `FadeIn`, `Transform` and `Indicate`, on artists and on axes, are compared with plain Manim run live, outside the differences F-1008 lists *(ADR 0003)* | **0.1** | D19, ADR 0003 |
| F-907 | After `Uncreate` an artist is detached and degenerate, so re-adding it shows what Manim shows. A later introducer draws the current curve, where Manim's draws nothing: the one intentional lifecycle difference, documented next to `Uncreate` | **0.1** | D19 |
| F-908 | `.animate` is Manim's own for geometry and data: no public method carries `override_animate`. The system aligns its family by role and tick key under `Transform.begin`, with a tick pool over the whole parameter path, and its leaves interpolate parameters, not points. Between systems whose locator configurations differ, ticks without a matching key fade out and in while the frame interpolates; a change of scale type raises, naming `FadeTransform` *(ADR 0003)* | **0.1** | D21, ADR 0003 |
| F-909 | Geometric and data methods chain under one `.animate`: `ax.animate.shift(v).set_x_range(r)` is one animation | **0.1** | D21 |
| F-910 | `mp.Group`, a broadcast handle for making container transforms permanent. Withdrawn: a container holding the system moves bound artists exactly (F-904, F-914) | **non-goal** | D18 |
| F-911 | Parameters are descriptors, not `__setattr__`: `ax.x.range = (0, 30)`, `.value`, `.tracker`, `.bind(t)`. Animating one is `self.play(ax.animate.set_x_range(...))` (F-908). `@` stays coordinate conversion only | **0.1** | D12, D21, A3.2, A4.1 |
| F-912 | Library animations in 0.1: `DrawAxes`, `TraceCurve` (data order, not path order), `ShowPoints`, `Morph`. The data channel is the native `.animate` (D21), not a class *(ADR 0003)* | **0.1** | D14, A7, ADR 0003 |
| F-913 | `AppendData`, `Rescale`, `HighlightTick` | **0.2** | D14 |
| F-914 | The system's placement is a hidden grid in its family: exact affine while the grid is affine, bilinear otherwise. It ignores partial drawing, stays invisible under every style call and contributes no boundary anchors. Under a non-affine grid, sparse derived leaves densify | **0.1** | D18 |
| F-915 | The system and each artist report a synchronisation updater without `dt` to Cairo's moving-object test only when the play being compiled involves their system or a tracker they are bound to, or when they hold a live function — exactly the cases of F-918 *(ADR 0003)*; otherwise they stay in the static background, as a Manim graph would, and a frozen `wait` stays frozen | **0.1** | D21, D26 |
| F-916 | Bound artists follow only permanent changes of their system: an animation that leaves the system where it found it, decided by simulating it on a copy, freezes the frame for the artists outside it | **0.1** | D20 |
| F-917 | Every Manim frame, local and line the mechanism reads from the call stack, every Manim method the library overrides and every animation attribute it assigns — `starting_mobject` and `outline` among them — is listed, with one source-hash pin set per supported Manim version; `Scene.get_moving_mobjects`, whose query differs between 0.21.0 and 0.22.0, is pinned with both *(ADR 0003)*. Line numbers are derived from source at import; Manim is never patched; an unpinned version warns at import | **0.1** | D19, D26 |
| F-918 | A plot's function is sampled at construction and whenever the data channel resamples it. It is sampled every rendered frame only when a parameter is bound to a tracker or to a callable *(ADR 0003)*, or under `always_redraw` | **0.1** | D8, D22, ADR 0003 |
| F-919 | The leaf lifecycle follows the state × event table of ADR 0001 §4: owners keyed by animation, attached animation copies, two kinds of detachment (removed, shaped), deferred `refresh()`, immediate `become`, `reverse_points` recorded as a direction, unregistered copies, and `ReplacementTransform` transferring registered artists | **0.1** | D24 |
| F-920 | The tick pool is built from the parameter path at four times the animation's frame density, with spare hidden leaves; a key first seen at render time takes a spare and fades in; out of spares, a render warns once through `ManimPlotsWarning`, which the test suite turns into an error *(ADR 0003)*. Inactive pool leaves contribute no boundary anchors | **0.1** | D24, D25 |
| F-921 | `mp.NumberPlane` follows Manim's `NumberPlane`: its signature, its defaults (the table below), its `background_line_style` and its faded lines *(ADR 0003)*. A standalone `NumberLine` and `ComplexPlane` | **0.1** / **0.2** | D27, ADR 0003 |
| F-922 | Library mobjects work with Manim's scene caching on, hashed by their derived state, and keep identity hashing | **0.1** | D27 |

## F-10xx — Quality gates

| ID | Requirement | Tier | From |
|---|---|---|---|
| F-1001 | Performance gate, end to end: `Scene.update_to_time` plus the camera's lazy rebuilds, rasterisation excluded. Four artists on one `CartesianAxes`, 2 000 samples each with `use_vectorized=True`, `MaxN` ticks with labels from a warm glyph cache, an animated range, 1080p60, Cairo, on the affine and on the non-affine frame path. p95 **<= 4 ms per frame**. Setup work per play — keyed alignment, simulation — is recorded, not gated. A second check: a static plot under an unrelated animation renders no slower than 1.5x the same scene in plain Manim. The relative baseline gate waits for a first release | **0.1** | PLAN gate, D26 |
| F-1002 | The public surface is fully annotated and type-checked, and the annotations agree with the implementation | **0.1** | defect 15f |
| F-1003 | Every Manim symbol cited in the design documents is imported by a test, so a rename fails loudly | **0.1** | PLAN, round 7 |
| F-1004 | Tests assert the **types** of generated leaves, not only rendered output | **0.1** | PLAN risk |
| F-1005 | The API is IDE-navigable: overloads on `plot`, typed descriptors, no string-keyed registry as the primary access path | **0.1** | A4.2 |
| F-1006 | The invalid-input table below is implemented and tested on every surface it lists | **0.1** | PLAN |
| F-1007 | Supported matrix for 0.1: Manim 0.21.0 and 0.22.0 exactly — another version is a review step (F-917) — Python >= 3.12, NumPy >= 2.5, Cairo renderer. Constructing a library mobject under the OpenGL renderer raises, naming Cairo | **0.1** | task/01, task/02, D26, D27 |
| F-1008 | The docs state each difference from plain Manim where users will meet it: the defect fixes of the defaults table; `Create` after `Uncreate` (F-907); curves following their system and only its permanent changes (F-916), `Rotate(ax, TAU)` included; the double move in code ported from Manim that animates both; bound helper labels (F-609); `c2p` and `p2c` raising where Manim returns `NaN`; late binding of loop variables on a resample (F-918); callbacks running once more under simulation; `refresh()` after a bare point edit; approximate non-affine frames; `PhaseFlow`-like callbacks growing an artist's transform; and *(ADR 0003)* ticks at integer multiples of the step where Manim anchors at `x_min`; the hidden frame's lag slot, so `Create(ax)` finishes its visible leaves at 24/25 of the run; partial drawing of an adaptively sampled curve paced by sample, not by `x`; `Transform` pairing ticks by key; `ax.add` registering where Manim parents; a singular frame refusing an operation that needs its inverse; and an unknown `axis_config` key raising | **0.1** | PLAN risk, D20, D22, D23, ADR 0003 |
| F-1009 | Every 0.1 capability with a Manim counterpart of the same semantics is reachable under Manim's name, signature and meaning: the `Axes` constructor with `axis_config` and the `NumberLine` keys listed in the defaults table, `mp.NumberPlane`, the 0.1 rows of the parity survey, and `plot`'s keywords (F-704). An `axis_config` key with no 0.1 capability raises, naming the key. Defaults follow the defaults table: Manim's except where its picture is a defect. `from manim_plots import *` exports `CartesianAxes`; `mp.Axes` is the same class. `p2n` and `point_to_number` take arrays, as in 0.22.0, and an unknown attribute on a library mobject raises `AttributeError` *(ADR 0003)* | **0.1** | D17, D23, D27, ADR 0003 |

---

## Defaults: Manim's, except where its picture is a defect (D23)

What `mp.Axes(...)` does with the arguments `Axes(...)` accepts, as checked against Manim
0.21.0. *Parity* means the same behaviour. *Fix* means a deliberate difference, listed in
F-1008. *Same spelling* means the same meaning even where the library's own spelling
differs. This table is the oracle of the parity test against Manim's own `Axes`.

| Default or argument | Manim 0.21.0 | manim-plots | Kind |
|---|---|---|---|
| Ranges when omitted | `x_range=[-7, 7, 1]`, `y_range=[-4, 4, 1]` (from the frame) | same | parity |
| Lengths | `round(frame_width) - 2`, `round(frame_height) - 2` | same | parity |
| `tips` | `True` | same | parity |
| A two-element range | step 1 | a `Multiple(1)` locator | parity |
| Tick positions | multiples of the step from 0 when the range contains 0, otherwise `x_min + k * step`, so `[0.001, 6, 1]` ticks at 0.001, 1.001, … *(ADR 0003)* | integer multiples `k * step` (F-402), so keys stay stable across an animated range (F-413) | difference, in F-1008 *(ADR 0003)* |
| The end tick under a tip | dropped | kept (F-411) | fix |
| A tick and a number where the axes cross | none (`exclude_origin_tick`, `numbers_to_exclude=[0]`) | none | parity |
| Tick shape | straddles the line, `tick_size=0.1`, `longer_tick_multiple=2` | same; direction configurable (F-604) | parity |
| Numbers | off (`include_numbers=False`), `font_size=36` | same | parity |
| Decimal places | the characters after the point in `str(step)`; `1e-05` gives 0 | same, except that a step in scientific notation counts its exponent: `1e-05` gives 5 *(ADR 0003)* | parity, plus a fix |
| Label direction | x `DOWN`, y `LEFT` | same | parity |
| An axis whose range excludes 0 | sits at the range edge | same; the crossing is a parameter (F-203) *(ADR 0003)* | parity |
| Centring *(ADR 0003)* | the midpoint of each range sits at the scene origin | same | parity |
| Axis line and tip *(ADR 0003)* | `stroke_width=2.0`; tip `0.35 × 0.35`; `line_to_number_buff=0.25`; the y axis rotated by 90° | same | parity |
| A curve outside the viewport | drawn | clipped (F-706) | fix |
| Colour of `plot` | white for every plot | a cycle whose first colour is white (F-803) | fix for the second plot on |
| Colour of `plot_line_graph` | `PURE_YELLOW` | same | parity |
| Labels that collide | overlap | the later one hidden (F-505) | fix |
| Tick numbers | `DecimalNumber` | numbers from a glyph cache, math mode | parity |
| String labels through `add_labels` | `Tex`, text mode | text mode | same spelling |
| `axis_config={"scaling": LogBase()}` | the range is in exponents: `y_range=[-2, 6]` spans 10⁻² to 10⁶ | same; the library's own `scale="log"` takes data values | same spelling |
| `axis_config` keys | `NumberLine.__init__` | honoured: `include_numbers`, `numbers_to_include`, `numbers_to_exclude`, `decimal_number_config`, `font_size`, `include_ticks`, `tick_size`, `longer_tick_multiple`, `numbers_with_elongated_ticks`, `exclude_origin_tick`, `include_tip`, `tip_shape`, `tip_width`, `tip_height`, `label_direction`, `line_to_number_buff`, `unit_size`, `scaling`, `stroke_width`, `color`. Any other key raises, naming it (F-1009) | parity |

What `mp.NumberPlane(...)` does against `NumberPlane(...)` (F-921) *(ADR 0003)*:

| Default or argument | Manim 0.21.0 | manim-plots | Kind |
|---|---|---|---|
| Ranges when omitted | `(-frame_x_radius, frame_x_radius, 1)`, `(-frame_y_radius, frame_y_radius, 1)` | same | parity |
| Lengths when omitted | from a unit size of 1, so the plane fills the frame | same | parity |
| Axes | `stroke_width=2`, no ticks, no tips, `line_to_number_buff=SMALL_BUFF`, numbers at `font_size=24`, `label_direction=DR` | same | parity |
| Background lines | `stroke_color=BLUE_D`, `stroke_width=2`, `stroke_opacity=1` | same | parity |
| Faded lines | `faded_line_ratio=1`; unless given, a faded copy of the background style | same | parity |

## Invalid input: one rule, surface by surface

**At construction, a malformed argument raises.** No warning, no repair, no partial
object; the exception names the parameter. A malformed value raises `ValueError` and a
wrong type `TypeError`; for an array the message names the first invalid index. A
warning at use is a `ManimPlotsWarning` *(ADR 0003)*.

| Malformed input at construction | Behaviour |
|---|---|
| Scale function not vectorized over `ndarray`, or the pair fails the sampled round trip (F-305) | raise |
| Declared domain malformed — empty, reversed, or `NaN`-bounded | raise |
| Non-finite value in a range, a length, a position, or a tick value | raise |
| `xs` and `ys` of different lengths, or an array of the wrong dimensionality for the artist | raise, naming both lengths |
| Malformed `Fixed` entry — wrong tuple arity, a level that is neither major nor minor, a non-finite value | raise |
| Two explicit tick entries sharing one key (F-405), or one locator emitting two values with one key (F-413) | raise |
| An artist bound to a second coordinate system (F-112) | raise |
| Payload `coords` not a float array, or not two-dimensional (F-114) | raise |
| Payload `segments` not `(s, 2)` integers, out of bounds, empty (`stop <= start`), unsorted, or overlapping | raise, naming the offending pair |
| Payload `topology` neither `None` nor a valid form: a grid shape whose product is not `n`, a cell array that is not `(m, k)` integers with `k >= 3`, a cell index out of `[0, n)`, a cell with a repeated corner, or inconsistent winding | raise, naming the offending cell |
| Payload `valid` not boolean, or not of shape `(n,)` | raise |
| Payload with a non-finite sample in `coords` while `valid` is `None`, or `valid` true at that sample | raise, naming the sample index |
| Payload of kind `path` with a sample that is covered by a segment while `valid` is false at it, or uncovered while `valid` is true | raise, naming the sample index |
| A `region` payload with `topology=None`, or a `path` or `points` payload with a topology | raise |

**At use, the surface decides**, because that is the only thing that differs between the
five *(ADR 0003)*.

| Surface | `NaN` or infinity from a source or node | Argument outside a node's domain | Configured range outside the scale's domain | Degenerate parameter |
|---|---|---|---|---|
| **Path sampling** (F-705) | split the path, warn once per artist per data change *(ADR 0003)* | split the path, warn once | normalised by the scale before sampling (F-311), so sampling never sees it | empty source: a `(0, 2)` segments array, draw nothing, warn once |
| **Tick generation** (F-410) | candidate dropped, no warning | candidate dropped, no warning | ticks are generated over the normalised range only | zero or negative step: **raise**, naming the parameter (F-409) |
| **`c2p` / `p2c`** (F-202) | **raise** | **raise** | not applicable — a conversion takes a value, not a range, and never clamps | **raise** |
| **Formatting** (F-501) | the tick never reaches the formatter | as above | as above | an empty tick list formats to an empty label list |
| **Point and region drawing** (F-114) | sample marked invalid in `valid` and not drawn — a region cell is dropped when any corner is invalid — warn once per artist per data change *(ADR 0003)* | as the column to the left | normalised by the scale (F-311) before sampling | empty payload: `(0, 2)` segments, draw nothing, warn once |

The asymmetry is deliberate. A path has a segment boundary to express the failure with,
a point set and a region have a per-sample mask, an axis has the option of simply having
no tick out there, and a scalar conversion has none of the three — and returning `NaN` from `p2c` is the defect being fixed (15c).

One consequence worth stating plainly, because it is the pair most easily confused: an
**animated** range is a sequence of configurations, so each frame is normalised by
F-311; a conversion inside that frame still raises on a value the scale cannot map.

---

## Paper-check of the 0.1 contracts

`docs/plan.md` makes this an acceptance criterion: the contracts freeze in 0.1 and are
stressed in 0.2, so each of the three cases that could force a redesign is checked here
in writing. Each ends in *fits* or *would force a redesign of X*.

### 1. A date/time axis

**Fits, with two contract consequences and one stated limitation.**

- *Values.* The pipeline is float-only, and that is a decision, not an omission:
  **everything numeric in the library — ranges, positions, tick values, locator input and
  output, `c2p` arguments — is a float in one declared epoch**, and 0.1 defines none of
  the conversion. A 0.2 date axis is an adapter *above* the engine that converts
  `datetime` to that float at every entry point a user touches (the range parameter, the
  axis position, an explicit tick list, a source column), exactly as matplotlib's unit
  converters sit above its transforms. Nothing inside `Map` or the node contract changes,
  and a user who wants dates before 0.2 converts to epoch seconds by hand. The limitation
  worth naming: float seconds lose sub-microsecond resolution around the present day, so
  the adapter, when it arrives, will pick its own epoch rather than inherit Unix time.
- *Non-constant steps.* A month is not a fixed number of seconds, so `Multiple(step)`
  cannot express "one tick per month". This is **not** a contract problem: the locator
  protocol (F-401) promises only candidates plus a key, never a constant step. A
  `DateLocator` is a new locator, not a new protocol.
- *Consequence 1 — the formatter must see the whole tick list.* "1 Jan / Feb / Mar" with
  the year only on the first tick cannot be produced one value at a time. F-501 therefore
  defines the formatter over the tick list rather than over a single value. Had the
  0.1 protocol been per-value, 0.2 would have broken it.
- *Consequence 2 — keys.* Tick identity is `key(value)` from the locator (F-413), and a
  date locator keys by `(year, month)` or similar, not by the float. This already works
  because the key function belongs to the locator.

### 2. The calculus toolkit

**Fits, and it is the reason `i2gp` ships in 0.1.**

- Tangents, secants, `T`-labels and antiderivative graphs all need the value of a source
  at a point that is not a sample. F-707 makes `Source` expose point evaluation
  alongside range sampling, so the query is exact and survives resampling.
- Riemann rectangles and shaded areas are artists that emit many mobjects from one
  source. The artist protocol already allows that, and F-106's declared geometry kind
  covers the fact that their output is a region rather than a path.
- Numerical differentiation needs no new contract: it is a `Source` wrapping another
  `Source`, which is the same composition the pipeline already performs.
- The one thing that would have forced a redesign — answering `i2gp` by searching the
  generated points — is exactly what the plan rules out.

### 3. Region sampling (`FieldSource`)

**This one did not fit. It forced a change to the `Source` output contract, which is now
F-114, and it fits with that change — a bare "declare a geometry kind" would not have
been enough.**

- A field source samples a 2D region and produces contours, arrows, isolines, a mesh or a
  filled region. `Map` transforming coordinates point-by-point holds unchanged; that part
  was never at risk.
- What was at risk is the *shape of what a source returns*. The plan said an array of
  points. An array of points cannot say which samples form a cell, which cells are
  masked, or whether the samples are a raster or a scattered cloud — and every one of
  those is needed before "clip a mesh" or "trace an isoline" means anything. Declaring
  only a `kind` label, as the first draft of F-106 did, names the problem without
  supplying the data to solve it.
- So the payload itself is frozen in 0.1, fields, shapes and invariants included — the
  table under *The Source payload* is that freeze. `Shape` dispatches on `kind` and
  returns a payload of the same type, which is what keeps a kind-changing operation
  inside the contract: isoline extraction builds a fresh `path` payload with its own
  segments rather than carrying region fields forward, and dropping masked cells returns
  a region with a rebuilt cell array.
- Two decisions were forced here rather than left open, because both are cheap now and
  breaking later. **Region clipping in 0.1 means conservative whole-cell removal** — a
  cell with any corner outside the viewport is dropped whole. It is the wrong answer for
  a coarse mesh at the viewport edge, and the right answer, trimming cell geometry, is a
  later `Shape` node emitting new `coords` and `topology`; the payload already permits
  that, so the upgrade is additive. And **a split path is `segments`, not sentinel `NaN`
  rows**, which matters in 0.1 already: F-705 splits at poles on the very first release.
- Only the *implementation* of the `region` branch is deferred. The branch itself and its
  `topology` ship in 0.1 as declared-and-unused. Field values for contours and vector
  fields arrive in 0.2 as optional payload fields with defaults, which breaks no 0.1
  consumer (ADR 0001 §3, D26) *(ADR 0003)*.
- Remaining risk, recorded rather than solved: general predicate domains and disjoint
  valid regions stay a 0.2 concern (D6). The validity mask in F-114 is what a predicate
  domain would eventually populate, so the shape is right even though the machinery is
  absent; a field over a non-rectangular domain is where that will first be felt.

---

## Deferred

**0.2:** autoscale and margins; an independent second scale; linked axes; polar; broken
axes; `fill_between`; error bars; `step`; histograms and bars; value-mapped colour and
colorbars; annotations and arrows; drop lines and reference lines; inset axes; date/time
axes; categorical axes; percent and logit formatters; label wrapping; rug plots; jitter;
legend layout; `AppendData`, `Rescale`, `HighlightTick`; one artist shared across two
systems; `rangelimited` axes; the Origin scale library.

**Later:** 3D; field sources and the five artists over them (implicit curves, contours,
vector fields, stream lines, surfaces); zoom plots; colour themes.

## Non-goals

Pie, box and violin plots; statistics and curve fitting; spectral transforms; unstructured
meshes; a GL backend; an interactive GUI; interaction and picking; subclassing Manim's
`Axes` / `NumberLine` / `NumberPlane`; matplotlib parity as an end in itself; figure
layout and subplot management; tick-label tables; copying settings between axes as an API.

---

## Traceability

### Every defect has a requirement

| Defect | Status on 0.21.0 | Requirement |
|---|---|---|
| 1 — float accumulation in tick generation | reproduces | F-402 |
| 2 — `include_tip` alters the tick range | partial | F-411, F-608 |
| 3 — curves escape the viewport | reproduces | F-706, F-107 |
| 4 — aspect distortion from independent lengths | reproduces | F-205, F-206 |
| 5 — `unit_size` ignored through `axis_config` | reproduces | F-204 |
| 6 — mutating `x_range` leaves ticks stale | reproduces | F-412 |
| 7 — no legend primitive | reproduces | F-801 |
| 8 — `LogBase.inverse_function` guard broken | reproduces | F-304, F-202 |
| 9 — no minor ticks between decades | reproduces | F-403 |
| 10 — `LogBase` naming inverted | reproduces | F-303 |
| 11 — label overlap | reproduces | F-505, F-408 |
| 12 — ticks centred on the axis line | reproduces | F-604 |
| 13 — `_origin_shift` clamps to the range minimum | reproduces; kept by default, fixable by a parameter *(ADR 0003)* | F-203 |
| 14 — geometric ops corrupt the mapping | gone in 0.21.0 | F-208 (regression test), F-207 (the projection note) |
| 15a — `plot()` joins across a pole | new | F-705 |
| 15b — tick step doubles as the sampling step | new | F-414, F-704 |
| 15c — `p2n` is not the inverse of `n2p` | new, severe | F-201, F-202 |
| 15d — zero tick step, unrelated error | new, minor | F-409 |
| 15e — out-of-range label placed off the line | new, minor | F-506 |
| 15f — annotations contradict the implementation | new | F-1002 |

### Every collaborator answer has a requirement

| Answer | Requirement |
|---|---|
| A1.1 — `from manim_plots import *`, no name collisions | D12 naming rule, F-702 |
| A1.2 — axis lengths, API close to Manim's | F-206, F-702 |
| A1.3 — user-supplied forward and backward functions | F-302 |
| A2.1 — separate verbs, and `ax.add(plot)` rather than `plot.attach(ax)` | F-702, F-708 |
| A2.2 — `ax.plot` supports nearly every plot type | F-702 |
| A3.1 — `ax.x` and `ax.x_axis` equivalent | F-602 |
| A3.2 — attribute assignment, not setter methods | F-911 (descriptors, same syntax) |
| A3.3 — explicit tick lists, and a generator function with regeneration | F-404, F-405, F-406, F-504 |
| A4.1 — operator-based parameter access with a step | F-911, and D12: `@` stays coordinate conversion; the step is a locator, not part of the range |
| A4.2 — IntelliSense support | F-1005, F-804 |
| A5.1 — `ax.legend()`, with merging and splitting | F-801 |
| A5.2 — `label=` preferred, `set_label` also | F-802 |
| A6.1 — adding the axes must not interfere with adding curves | F-709 |
| A7 — animations of our own for common cases | F-912 |
| Requirement list, D9 — controlled access to every part | F-603 |
| Requirement list, D9 — working control of the zero at the origin | F-203 |
| Requirement list, D9 — axes through the origin or at the borders | F-605 |
| Requirement list, D9 — gnuplot-style numbering | F-404, F-405, F-502, F-508 |
| Requirement list, D9 — dual axes on either side | F-606 (0.1 mirrored), F-610 (0.2 independent) |
| Requirement list, D9 — date/time ticks | deferred, with stress case 1 as the condition |
| Requirement list, D9 — time series and scatter from either array shape | F-703 |

### Every task/04 decision has a requirement

| Decision | Requirement |
|---|---|
| D17 — plain Manim is the reference: spelling, defaults, `mp.Axes`, `scale` leaves strokes alone | F-804, F-807, F-1009 |
| D18 — a hidden frame carries the system's placement | F-105, F-208, F-910, F-914 |
| D19 — the leaf lifecycle, with operation context from the call stack | F-111, F-903, F-904, F-905, F-906, F-907, F-917 |
| D20 — curves follow only permanent changes of their system | F-708, F-916, F-1008 |
| D21 — the data channel is native under `.animate` | F-908, F-909, F-911, F-915, F-918 |
| D22 — a plot function is sampled as Manim samples it; live is explicit | F-704, F-918 |
| D23 — defect fixes are the default; Manim's look is kept everywhere else | F-1008, F-1009, the defaults table |
| D24 — the leaf lifecycle, cell by cell | F-919, F-920 |
| D25 — tick identity is stable across ranges; the pool has spare leaves | F-401, F-413, F-920 |
| D26 — the contracts, closed before the freeze | F-201, F-207, F-707, F-915, F-917, F-1001, F-1007 |
| D27 — Manim's surface, case by case | F-603, F-609, F-704, F-705, F-921, F-922, F-1007 |
| ADR 0003 — the final reviews, closed | F-110, F-112, F-114, F-203, F-204, F-205, F-301, F-311, F-401, F-403, F-404, F-409, F-702, F-705, F-708, F-906, F-908, F-912, F-915, F-917, F-918, F-920, F-921, F-1008, F-1009 |

### The parity survey

Every Manim name with a **0.1** verdict in `docs/parity-survey.md` section 1 lands in
F-2xx (mapping), F-4xx and F-5xx (ticks and labels), F-6xx (decoration), F-7xx (artists)
or F-8xx (legend). The three matplotlib findings became F-311, F-407 and F-503; the two
gnuplot findings became F-404 and F-405; Origin contributed F-505's third answer and
F-605's value-based positioning.
