# Plan Review Log: manim-plots functional scope and public API (task/03)

Act 1 (grill) complete — plan locked with the maintainer. MAX_ROUNDS=5.
Act 2 (Codex adversarial review) has not run yet.

## Round 1 — Codex

- `PLAN.md:33-39` claims every geometric operation funnels through `apply_points_function_about_point`, but installed Manim 0.20’s `Mobject.shift()` mutates `points` directly; `VGroup.shift()` therefore bypasses the proposed `T` channel. Fix: integrate at every mutation path or explicitly forbid/group-wrap operations that bypass the hook.

- `PLAN.md:72-79` says attached-artist geometry is a warned no-op, but `VGroup(ax, curve).shift()` operates on family members directly and cannot invoke `curve.shift()`. Fix: define a supported group/container mechanism or make rebuild detect and reject externally mutated derived points.

- `PLAN.md:41-50` makes `Shape` artist-owned while `Map` owns clipping feedback, but adaptive sampling needs the mapped viewport and clipping needs the artist’s shape semantics; invalidation order and ownership are circular. Fix: specify an explicit two-phase compile contract: map bounds first, source sampling second, shape generation third.

- `PLAN.md:58-65` assumes lazy rebuild occurs “just before the camera reads points,” but Manim has no guaranteed camera-read callback; `get_center`, bounding-box queries, animations, scene family extraction, and updaters can read stale points earlier. Fix: define a concrete Manim lifecycle hook/updater contract and test every point-read path.

- `PLAN.md:67-70` overstates `Morph` correctness: resampling by arc length does not preserve semantic correspondence for discontinuities, scatter points, repeated/degenerate points, clipped paths, or different analytic domains. Fix: define per-artist morph semantics and reject unsupported topology changes instead of promising a universal `Morph`.

- `docs/grill-log.md:106-124` only gives `domain` as an interval, which cannot represent coupled 2D domains, disjoint valid regions, or custom scales with holes; the “warn/break” policy is also undefined for infinities and NaNs. Fix: make domain a general predicate/region with an explicit finite-output and segment-breaking policy.

- `docs/grill-log.md:348-350` defines custom scales with only forward/backward functions and a domain, but adaptive sampling, monotonic ticks, inversion, and range validation require vectorization, monotonicity, dimensionality, and error behavior. Fix: add those requirements to the scale protocol and validate them at construction.

- `docs/grill-log.md:343-347` says an `x_range=(0, 10, step)` triple installs a locator, but the locked text specifically says `Multiple(1)` rather than using the supplied third element. Fix: specify `Multiple(step)` and define precedence when `set_locator()` is later called.

- `docs/grill-log.md:279-297` keys generated parts by raw floating-point values, which is unstable for locator recomputation and cannot distinguish duplicate ticks or equivalent values produced by different generators. Fix: define canonicalized keys plus duplicate/order handling and decide whether user-modified parts survive temporary disappearance.

- `PLAN.md:94-95` requires coordinate scaling to scale stroke widths, but Manim’s point transformation hook does not scale style attributes; nonuniform aspect changes make “scale stroke width” ambiguous. Fix: specify a separate style-scaling policy and implement/test it independently of point transforms.

- `TODO.md:31-51` targets Manim 0.21.0, while the plan validates only installed 0.20.0 and `pyproject.toml:20` allows every version from 0.19 onward. Fix: choose and enforce a supported Manim version/matrix before using defect findings to define requirements.

- `PLAN.md:97-113` scopes a complete engine with adaptive sampling, multiple scales, tick systems, overlap resolution, clipping, trackers, morphing, animations, and three artists without performance budgets or acceptance thresholds. Fix: add measurable acceptance criteria, benchmarks, and a reduced 0.1 gate before freezing the architecture.

VERDICT: REVISE
### Claude's response

Verified against the installed Manim 0.20.0 before deciding.

**Accepted — the integration point was wrong (findings 1, 2, 4).**
`Mobject.shift()` (`mobject.py:1260-1264`) does *not* route through
`apply_points_function_about_point`; it writes `mob.points += total_vector`
directly. Worse, both that method and `apply_points_function_about_point`
(`mobject.py:1560-1563`) iterate `family_members_with_points()` and assign to each
leaf's `.points` attribute, so overriding a method on a leaf class intercepts
nothing when a parent `VGroup` is the caller. The plan's claim that
"every geometric operation and `.animate` funnels through
`apply_points_function_about_point`" is false, and with it the claim that
`VGroup(ax, curve).shift()` produces the right result — it produces a correct
first frame and then reverts at the next rebuild, because it overwrites derived
points that nothing recorded.

`points` is a plain instance attribute (`mobject.py:447`), never a property, so it
can be redefined as one on our own classes. That single hook answers three
findings at once: the getter is the lazy-rebuild trigger Codex correctly notes
Manim gives no other callback for (`get_center`, bounding boxes, animations,
scene family extraction and updaters all read `.points`), and the setter is the
one place every external geometric write — direct or through a parent container —
must pass. Direct method overrides on `shift` / `apply_points_function_about_point`
are kept as an exact fast path; the setter is the general fallback that recovers
the affine part where it can and warns and detaches where it cannot.
Only two write sites exist in `Mobject`, so the fast path covers the common case
and everything else degrades loudly instead of silently.

**Accepted — smaller corrections.**
- Three-phase compile contract (map bounds, then source sampling, then shape) to
  make the feedback edge an order rather than a cycle (finding 3).
- `Morph` is per-artist and rejects topology it cannot resample; the universal
  promise is withdrawn (finding 5).
- A non-finite policy for 0.1: `NaN` / `±inf` outputs break the path into
  segments rather than warning or drawing (part of finding 6).
- The scale protocol gains vectorization, declared monotonicity with a sampled
  construction-time check, declared dimensionality and a defined out-of-domain
  error (finding 7).
- `x_range=(0, 10, step)` installs `Multiple(step)`, not `Multiple(1)` — the plan
  quoted the literal from its own example. A later `set_locator()` wins; the
  triple is only a constructor default (finding 8).
- Generated-part keys are canonicalized (quantized to the locator's own step and
  rounded to a fixed number of significant digits), not raw floats, so
  `0.30000000000000004` and `0.3` are one key (finding 9).
- Stroke scaling gets a definition: `sqrt(|det A|)` of the recovered 2D affine
  part, applied wherever the affine is recoverable and skipped with a debug
  warning where it is not (finding 10).
- Manim version target pinned: 0.20.0, `manim>=0.20,<0.21` for 0.1. `TODO.md`
  still says 0.21.0 and `pyproject.toml` allows `>=0.19`; both are corrected as
  part of this task (finding 11).
- One measurable performance gate enters `docs/scope.md` as an `F-*` rather than
  staying an unquantified risk (part of finding 12).

**Rejected, with reasons.**
- *A general predicate/region domain for 0.1* (rest of finding 6). Coupled 2D
  domains and disjoint valid regions are the region-sampling stress case, already
  deferred to 0.2 and already scheduled as a paper check against the frozen
  contracts. Building the general form now would be designing for a case the plan
  deliberately validates on paper first. The non-finite policy, which does bite in
  0.1, is accepted above.
- *A reduced 0.1 gate before freezing the architecture* (rest of finding 12).
  This re-opens a decision the grill settled: the whole engine plus three artists
  is the 0.1 scope precisely because a smaller artist set tests the contracts no
  better and only delays finding out a contract is wrong. The measurable
  acceptance criteria are accepted; the scope cut is not.
- *"Reject externally mutated derived points"* as the answer to finding 2. Warning
  and detaching is enough; hard rejection would make a legitimate one-off
  `VGroup(...).shift()` an error in a library whose users reach for that reflex.

## Round 2 — Codex

Several prior findings are addressed: the plan now defines a three-phase rebuild, per-artist morph rules, custom-scale validation, canonical keys, stroke scaling, and a 0.20 pin. Material issues remain:

- `PLAN.md:44-71` claims the `points` property catches every external write, but Manim and user code can mutate array views directly (`points[:]`, `points[:, :]`, slice operations), bypassing the property setter entirely. Fix: make derived point buffers immutable/read-only and expose controlled mutation APIs, or explicitly audit and wrap every supported mutation path.

- `PLAN.md:51-59` only audits `Mobject` methods, but Manim animations such as partial creation and indication directly mutate submobject point arrays; `Create(curve)` from `docs/api-sketch.md:163-166` could therefore detach or corrupt an attached artist. Fix: define and test compatibility for `Create`, `Transform`, `Write`, and partial-path animations, or provide only library-owned animation adapters.

- `PLAN.md:66-71,128-138` says external translations fold into shared `T` once, but a parent operation iterates multiple leaves; each leaf setter may independently infer and apply the same translation. Fix: add a transaction/generation token so one parent operation is coalesced into one transform update.

- `PLAN.md:44-49` proposes redefining `points` as a property, but Manim initializes `self.points` during `Mobject.__init__` before the derived-point cache, dirty flags, and pipeline state can safely exist. Fix: specify an initialization-safe setter/getter protocol and test construction, copying, `become`, and empty mobjects.

- `PLAN.md:140-148` canonicalizes keys by quantizing to the locator step, but this is undefined for callable/custom locators, logarithmic locators, floating steps, zero/negative values, and values whose formatter changes while their numeric key remains constant. Fix: require every locator to provide a stable key function, with collision and formatter-update semantics.

- `PLAN.md:121-126` requires construction-time monotonicity checks over a sampled domain, but sampling cannot validate an unbounded or discontinuous custom scale and can accept a function that reverses between samples. Fix: document this as a heuristic validation, add runtime monotonicity/domain checks where required, and define failure behavior.

- `PLAN.md:109-126` has inconsistent invalid-input policy: non-finite function outputs split paths, while custom-scale domain violations raise. Fix: define whether domain violations become path breaks, artist errors, or warnings consistently across built-in and user-defined maps.

- `PLAN.md:84-89,187-189` knowingly permits a one-frame lag while claiming every rebuilt frame is a correct plot of the current parameters. Fix: either guarantee a same-frame map/sampling snapshot or explicitly weaken the frame-correctness invariant and test the chosen behavior.

- `PLAN.md:164-170` says the performance gate will be written later, but supplies no budget, hardware, renderer, curve count, point count, or percentile criterion. Fix: put the concrete benchmark scenario and pass/fail threshold in the plan before implementation begins.

- `PLAN.md:172-174` says the target is pinned, but `pyproject.toml:20` and `TODO.md:31-51` remain uncorrected in the repository, and the stated deliverable does not clearly include those changes. Fix: make dependency/task metadata correction an explicit acceptance criterion with the exact supported-version matrix.

VERDICT: REVISE
### Claude's response

Both point-write findings verified in the installed 0.20.0 before deciding, and they
are correct.

**Accepted — the setter's classification was wrong (findings 1, 2, 3).**
`VMobject.pointwise_become_partial` assigns a fresh buffer
(`vectorized_mobject.py:1967`) and then writes **into slices of it**
(`:1970`, `:1977`, `:1982`); `Indicate`'s restore is a pure in-place write with no
assignment at all (`indication.py:559`). A property setter therefore cannot see the
content of a `Create`, `Uncreate`, `Write` or `Indicate` frame, and the previous
revision's "warn and detach on a non-affine write" would have detached a curve the
moment anyone wrote `Create(curve)` — the single most common Manim idiom.

The fix removes the failure rather than guarding it. The getter returns *the cache
object itself* while the pipeline is clean, so an in-place write lands in the buffer
that will be drawn, and it survives until something dirties the pipeline. That is
exactly `Create`'s semantics, so no hook is needed for in-place writes at all. The
setter's job shrinks to classifying whole-array assignments into two cases — an
affine delta that folds into `T`, or a takeover that is adopted as a transient
override buffer and replaced at the next rebuild. Nothing detaches and nothing
raises; `Create`, `Transform`, `Write` and `Indicate` all fall into the second case
and work.

Coalescing (finding 3) is accepted as stated: a parent container writes to every
leaf, so the affine fold is keyed by a write-burst token — one operation folds into
the shared `T` once — with the documented ceiling that two identical shifts with no
intervening read collapse into one.

**Accepted — smaller corrections.**
- Initialization-safe protocol: the setter falls back to a plain store while the
  pipeline attributes do not yet exist, so `Mobject.__init__`, `copy`, `become` and
  empty mobjects behave (finding 4).
- Locators supply their own key function rather than the plan guessing a quantum
  from a step that log and callable locators do not have (finding 5).
- The monotonicity check is labelled a heuristic falsification, not a proof, with a
  defined failure behaviour (finding 6).
- One invalid-input policy across built-in and user-defined maps: contract
  violations raise at construction, out-of-range values encountered while sampling
  break the path exactly as non-finite outputs do (finding 7).
- The frame-correctness invariant is stated precisely instead of loosely: geometry
  is same-frame correct because phase 1 completes before phase 2 within one rebuild;
  only adaptive *refinement density* may lag a frame, which changes the sample count
  and not the correctness of what is drawn (finding 8).
- A concrete benchmark scenario and threshold, in the plan rather than promised to
  `docs/scope.md` (finding 9).
- The `pyproject.toml` and `TODO.md` corrections and the exact version matrix are an
  explicit acceptance criterion, not a step (finding 10).

**Not accepted as phrased.**
- *"Make derived point buffers immutable/read-only"* (fix offered for finding 1).
  Marking the array non-writeable turns `Create` and `Indicate` into a
  `ValueError: assignment destination is read-only` instead of making them work. The
  cache-object-identity rule above achieves the compatibility that a read-only
  buffer would forbid.
- *"Provide only library-owned animation adapters"* (alternative offered for finding
  2). Library-owned adapters exist for the data channel — `Morph` is the artist-aware
  answer to `Transform` — but Manim's creation and indication animations keep working
  on our mobjects rather than being banned.

## Round 3 — Codex

The major conceptual issues were addressed, but the revised point-integration design still has implementation-blocking gaps:

- `PLAN.md:73-101` treats the getter-returned cache as a universal compatibility mechanism, but Manim’s animation methods operate on each family leaf (`pointwise_become_partial`, `become`, `indication`), not necessarily on the artist object; a property on the artist cannot observe or coordinate those leaf mutations. Fix: define an explicit artist-owned leaf/proxy type or restrict supported animations to operations whose mutation target is the artist itself.

- `PLAN.md:87-101` says whole-array writes become transient overrides, but direct slice writes can leave the pipeline “clean” indefinitely; a later `get_center()` or render will observe animation-mutated geometry while the model still reports the old data. Fix: add an explicit animation/transient-generation lifecycle that marks and clears overrides, rather than using cache identity as implicit state.

- `PLAN.md:94-97` requires a write-burst token for arbitrary parent operations, but ordinary Manim `VGroup`/`Group` calls provide no callback or transaction boundary to the child objects. Fix: either require a library-owned container wrapper or state that external parent transforms are unsupported and cannot update shared `T` reliably.

- `PLAN.md:63-71` still overstates the mutation audit: it covers `Mobject` methods but not direct writes in `VMobject`, OpenGL classes, animation code, or user code that mutates returned NumPy views. Fix: define the supported renderer/animation surface and test every operation in that surface, with unsupported mutations explicitly documented.

- `docs/api-sketch.md:163-166` still presents `Create(curve)` as ordinary supported usage, while `PLAN.md:99-101` says shape-changing external writes are discarded on rebuild; if a bound parameter dirties during `Create`, the animation can reset mid-animation. Fix: specify whether data invalidation is deferred during transient animations or provide a stable animation snapshot.

- `PLAN.md:210-217` combines an absolute requirement of p95 ≤4 ms with a CI rule allowing 1.5× the recorded baseline; if the baseline is already above 4 ms, CI can pass while violating the stated gate. Fix: require both `p95 ≤4 ms` and `p95 ≤1.5× baseline`, and fail baseline creation when the absolute target is missed.

- `PLAN.md:146-155` says every out-of-domain map value breaks the path, but tick generation, `p2c`, and standalone coordinate conversion also traverse map nodes and are not paths; their behavior remains undefined. Fix: define separate behavior for sampled artist paths, ticks, `c2p`, and `p2c` in `docs/scope.md`.

- `PLAN.md:165-171` accepts sampled monotonicity as a heuristic, but a passed custom scale can still reverse between samples and produce invalid tick ordering or a non-invertible `p2c`; this is a correctness risk, not merely documentation detail. Fix: require a user-declared trust mode or runtime monotonicity checks on the actual sampled interval before generating ticks.

VERDICT: REVISE
### Claude's response

**Accepted — the write-burst token does not work, and is deleted rather than repaired
(finding 3).** `Mobject.shift` does `mob.points = mob.points.astype("float")` and then
`mob.points += total_vector`, and `+=` is a getter *followed by* a setter. The getter
therefore runs between every pair of leaves, so a burst that "ends at the next getter
call" ends after the first leaf and the shared `T` is folded once per leaf. Codex is
right that Manim offers no transaction boundary to a child, and the previous revision
invented one that its own mechanics contradict.

The replacement is a deletion. A foreign parent's write is simply the transient-override
case — visually correct immediately, and replaced at the next rebuild — and a
library-owned container, `mp.Group`, is the supported way to move a bound system and its
artists together permanently. `ax.shift(...)` and `ax.animate.shift(...)` already work
exactly, because those reach our own overrides. That is less machinery than the token,
not more, and it does not promise a boundary Manim does not provide.

**Accepted — the leaf type has to be ours (finding 1).** Manim's animations reach family
leaves, not the artist object, so the property has to live on the leaves. Every mobject
the library generates — curve segments, ticks, labels, grid lines, legend entries — is a
manim-plots type carrying the property. This is a requirement the plan had left implicit
and is now stated.

**Accepted — the supported mutation surface is named (finding 4).** Cairo renderer,
0.20.0, our own leaf types, Manim's creation and indication animations, and in-place
writes to the array the getter returns. OpenGL is already out of scope for 0.1; mutations
outside that surface are documented as unsupported rather than silently half-working.

**Accepted — invalidation is deferred while an override is live (finding 5).** A bound
parameter dirtying the pipeline mid-`Create` would otherwise reset the animation. The
dirty flag is recorded but the getter does not rebuild while a transient override is
live; the override clears on `artist.refresh()` or on the next whole-array write whose
shape matches the derived points, and the deferred rebuild then runs. Animating the data
channel and running a creation animation on the same artist at the same time remains two
writers for one buffer and is documented as unsupported rather than resolved.

**Accepted — the benchmark gate was self-contradictory (finding 6).** It now requires
both `p95 <= 4 ms` and `p95 <= 1.5x baseline`, and baseline creation fails if the absolute
target is missed, so a slow baseline cannot ratify itself.

**Accepted — invalid input needs a per-surface answer (finding 7).** Path sampling breaks
the path; a locator filters out-of-domain candidates instead of erroring; `c2p` and `p2c`
raise, because a scalar conversion has no segment to break. The full table lands in
`docs/scope.md`; the rule that decides it is in the plan.

**Accepted — monotonicity gets a runtime check where it actually matters (finding 8).**
Construction-time sampling stays a heuristic, and tick generation additionally asserts
that the forward images of the ticks it is about to emit are ordered. That is an O(n)
check on a small array on the path where a reversal would produce visibly wrong output,
and it converts a silent defect into an exception.

**Not accepted as phrased.**
- *An explicit animation/transient-generation lifecycle* (finding 2). During a `Create`,
  `get_center()` returning the partial path's centre is what every Manim mobject does,
  and matching it is correct rather than a divergence to be engineered away. The genuine
  sub-case — a user's own in-place write that never restores — is answered by the public
  `artist.refresh()` escape hatch and a documented statement that geometry may
  transiently differ from the model during animations by design. A lifecycle would have
  to be driven by callbacks Manim does not expose.

## Round 4 — Codex

The latest revision resolves the prior leaf-type and foreign-parent concerns, but two core animation paths are still architecturally wrong:

- `PLAN.md:91-93,226-237` claims `ax.animate.shift(v)` moves bound artists smoothly, but Manim’s `.animate` creates a deep-copied target and interpolates the original axes’ family leaves; registered artists are not in that family, so they remain stationary until the final method call, then jump. Fix: provide an overridden animation that interpolates the live shared `T` and invalidates all registered artists each frame.

- The same problem applies to `self.play(ax.animate.set_range(...))` from `docs/api-sketch.md:119-120`: the target copy owns a separate map/registry, while the original attached artists are outside the transformed family, so curves do not rebuild during the animation. Fix: make data-channel animation operate on the live coordinate-system parameter and registered-artist set, not Manim’s default target-copy interpolation.

- `PLAN.md:111-117` defers invalidation while an override is live, but `Indicate` performs `submobject.points[:, :] = ...` in place (`indication.py:559`) without invoking the setter; if a bound parameter becomes dirty during `Indicate`, there is no mechanism to mark the override live, so the getter can rebuild and erase the indication mid-animation. Fix: add an explicit supported-animation guard/snapshot for all in-place animations, or remove `Indicate` from the supported surface.

- `PLAN.md:102-109` declares `mp.Group(...).shift()` the permanent solution but does not define how that group discovers registered artists that are deliberately not submobjects; a normal family traversal cannot update them. Fix: specify `mp.Group` as a registry-aware container with an explicit shared-transform transaction, or make permanence unavailable for non-parented artists.

VERDICT: REVISE
### Claude's response

All four accepted. The first two are the sharpest findings of the review: verified in
0.20.0 and correct.

**`.animate` was assumed to work and does not (findings 1, 2).**
`_AnimationBuilder.__init__` calls `self.mobject.generate_target()` — a deep copy
(`mobject.py:3318`) — and `_MethodAnimation` is a `MoveToTarget`, so every intermediate
frame is a `Transform` interpolating the *original's family leaves* toward the copy's.
`_MethodAnimation.finish()` then calls the real method on the real mobject
(`transform.py:447-450`). So `ax.animate.shift(v)` ends in the right place and is wrong
for every frame before that: registered artists are not in `ax`'s family, so they sit
still and jump on the last frame. `ax.animate.set_range(...)` is worse — the copy owns a
separate map and registry, so the interpolation is exactly the point-alignment
interpolation this plan rejects, computed against artists that never rebuild.

Manim supplies the correct hook: `override_animate` is public (`mobject.py:3397`,
exported in `__all__`), and `_AnimationBuilder` consults `method._override_animate`
before falling back to the copy-and-transform path (`mobject.py:3341-3351`). Every
manim-plots method that touches `T`, the map, or a bound parameter carries it and returns
an animation that interpolates the value on the **live** object and lets the normal
dirty-and-rebuild path produce each frame. That is the mechanism the "interpolate
parameters, never points" decision always needed and never named.

Its documented limitation is inherited and becomes a stated ceiling: an overridden method
cannot be chained with another method under one `.animate` (`mobject.py:3410-3411`), so
`ax.animate.shift(v).set_range(...)` is two animations in an `AnimationGroup`, not one
chain.

**In-place animation writes are detected by comparison, not by a guard (finding 3).**
`Indicate`'s in-place write is invisible to the setter, so nothing can mark an override
live — Codex is right that a bound parameter dirtying mid-`Indicate` would let the getter
rebuild over it. Rather than remove `Indicate` from the supported surface, the rebuild
path compares the exposed buffer against a shadow copy of the last derived output before
it rebuilds; if they differ, someone wrote in place, and the rebuild defers exactly as it
does for an adopted override. The cost is one extra buffer and an O(n) comparison on a
path that is already O(n), well inside the 4 ms gate, and it closes the hole for every
in-place writer rather than for the one animation that was noticed.

**`mp.Group` is a broadcast handle, not a container (finding 4).** Codex is right that a
family traversal cannot reach registered artists. Making `mp.Group` a `VGroup` would also
reintroduce the parenting hazard D11 removed. So it is not a `Mobject` at all: it holds
its members and forwards a geometric call to each member's own method — `ax.shift(v)`,
which already carries the system's registered artists through the shared `T`. Its
`animate` broadcasts to the members' overridden animations inside an `AnimationGroup`.
That is a handful of lines and introduces no tree.

## Round 5 — Codex (final round, cap reached)

Two redesign-level issues remain:

- `PLAN.md:86-100,141-151` still cannot safely support `Indicate` on attached leaves: `Indicate` first mutates `points` in place, then calls `submobject.scale()` and `rotate()`; the plan’s leaf overrides will either treat those as permanent shared-`T` operations and distort the plot, or as attached-artist no-ops and make `Indicate` ineffective. Fix: define an explicit transient-animation mode in which leaf geometry operations mutate only the temporary buffer, and ensure it is entered before `Indicate` begins.

- `PLAN.md:141-151` detects in-place overrides only when a getter is reached, but `Indicate`’s scale/rotate calls occur after the in-place write and before any rebuild-triggering getter is guaranteed; therefore the operation can be classified under the clean pipeline and update `T` incorrectly. Fix: make supported in-place animations register their transient buffer before the first frame, or have every leaf geometric override compare/mark the shadow before changing state.

VERDICT: REVISE
### Claude's response

Both accepted; one factual correction to the attribution, which does not change the
finding.

**The animation is `Wiggle`, not `Indicate`.** `indication.py:559` sits inside
`Wiggle.interpolate_submobject` (class at `:488`). `Indicate` is a `Transform` subclass
(`:125`) whose `create_target` copies and scales (`:164-166`), so it writes whole arrays
through `mobject.py:3075` and lands in the setter's transient-override case, which
already works. Earlier rounds of this log named `Indicate` for that line; the mechanism
described was right and the name was wrong.

`Wiggle` is genuinely broken against this design, exactly as described: it writes
`submobject.points[:, :] = starting_submobject.points` in place, then calls
`submobject.scale(...)` and `submobject.rotate(...)` on the same leaf every frame. Those
two reach our fast-path overrides and fold into the shared `T`, permanently, once per
frame — the plot distorts and never comes back.

**Accepted, using Codex's second fix, which subsumes the first.** The shadow comparison
introduced last round is not only a rebuild-time check: it is the transient-mode test.
Every geometric override — `shift`, `apply_points_function_about_point`, and therefore
`scale`, `rotate` and the rest that route through them — compares the exposed buffer
against the shadow *before* changing any state. If they differ, an in-place write has
already happened, so the call is part of an in-flight animation and applies to the buffer
directly instead of folding into `T`. If they match, it is a genuine geometric operation
and folds as before.

That is one test, used by the getter and by the overrides, and it needs no animation
registry, no lifecycle and no list of blessed animations — `Wiggle`, `ApplyWave`'s
homotopy and anything else built the same way all fall out correctly. Its ceiling is
stated: a real `curve.shift(v)` issued while a buffer is still dirty from a finished
animation is treated as transient and lost at the next rebuild; `artist.refresh()` is the
escape hatch, and in a rendered scene the buffer is clean between plays.

**Round cap reached.** This revision was applied after Codex's fifth and final round, so
it has not itself been adversarially reviewed. The two findings it answers are recorded
above with the mechanism used; the maintainer decides whether that is enough or whether
the cap should be lifted for a sixth round.

_MAX_ROUNDS raised from 5 to 8 by the maintainer, 2026-09-05._

## Round 6 — Codex

The prior redesign-level issues are now addressed:

- Live `.animate` propagation uses `override_animate`.
- `mp.Group` is explicitly a registry-aware broadcast handle rather than a `Mobject`.
- The shadow comparison is consulted both before rebuilds and before geometric overrides, so `Wiggle`’s in-place write followed by scale/rotate remains transient.
- The supported surface and deliberate ceilings are explicit.

I found no remaining issue that would make the implementation wrong or require redesign.

VERDICT: APPROVED
### Claude's response

APPROVED, but this round is weak evidence on its own: the prompt handed Codex the fix and
the attribution correction before it read the file, which is leading the witness. Round 7
re-attacks the same plan without any steer and with an explicit instruction not to defer
to this verdict.

## Round 7 — Codex (uncontaminated re-attack)

Material flaws remain:

- `PLAN.md:52-56,95-103,183-192` cannot preserve arbitrary transform order with one affine tail `T`: after `apply_function(f); shift(v)`, Manim semantics require `shift(f(points))`, while replaying non-affine callables after `T` computes `f(shift(points))`. A non-affine barrier does not solve the ordering problem. Fix: store an ordered transform pipeline containing affine and non-affine operations, collapsing only adjacent affine runs, or explicitly forbid transforms after a non-affine operation.

- `PLAN.md:91-103,157-166` uses a shadow comparison as a transient-mode detector, but the same dirty buffer can represent either an animation’s temporary geometry or an ordinary user mutation; once any in-place mutation occurs, subsequent legitimate `shift`/`scale` calls are classified as transient until `refresh()`. The documented ceiling covers one case, but this makes ordinary composition semantically wrong, not merely inconvenient. Fix: separate animation-owned temporary writes from user geometry with an explicit animation context, or remove direct in-place mutation from the supported contract.

- `PLAN.md:157-166` says a deferred rebuild runs when the override clears, but the design has no reliable “clear” event for `Wiggle`, `ApplyWave`, or arbitrary user writes; `refresh()` is manual and the next matching whole-array write is not guaranteed. A dirty bound parameter can therefore remain unapplied indefinitely. Fix: use an animation cleanup hook or make every supported animation’s `finish()`/cleanup call `refresh()`.

- `PLAN.md:205-212` says bound parameters are detected by polling, but it does not define snapshot/equality semantics for NumPy arrays, vector trackers, callable bindings, or `NaN`. Direct comparison of array-valued bindings is ambiguous, and `NaN != NaN` causes perpetual rebuilds. Fix: require canonical immutable snapshots and a defined equality/NaN policy for every binding type.

- The plan’s registration model has no explicit cardinality rule for an artist: `ax2.add(curve)` historically rebinds it away from `ax1`, so one artist cannot simultaneously participate in two coordinate systems despite the plan’s intended shared-registration use cases. Fix: state single-owner binding as a hard invariant and provide separate view/binding objects for multi-system display.

- Several “verified” Manim citations are wrong in the installed 0.20.0 source: `generate_target` is around `mobject.py:910`, `override_animate` around `mobject.py:3495`, `_AnimationBuilder` dispatch around `mobject.py:3441`, and `pointwise_become_partial` around `vectorized_mobject.py:1992`, not the cited locations. Fix: correct the references and make the audit cite stable symbols/tests rather than fragile line numbers.

VERDICT: REVISE
### Claude's response

The uncontaminated round earned its keep. Round 6's APPROVED is withdrawn as evidence —
it was given after a prompt that supplied the answer.

**The citation finding is right, and its cause is worse than a typo.**
The project has its own `.venv` holding **manim 0.21.0**; the interpreter this review had
been reading (`~/Desktop/dev/Python/Lib/site-packages/manim`) holds 0.20.0. Codex was
reading the project environment and was right about every line number. So:

- **The target version is 0.21.0, not 0.20.0.** Round 1's finding that `TODO.md` (0.21.0),
  the plan (0.20.0) and `pyproject.toml` (`>=0.19`) disagreed was correct; the resolution
  went the wrong way. `TODO.md` was right all along. `pyproject.toml` gets
  `manim>=0.21,<0.22`, and the defect audit re-runs on 0.21.0 as originally planned.
- **Every behavioural claim was re-verified against 0.21.0 and every one still holds.**
  `points` is still a plain attribute (`mobject.py:458`); `shift` still writes
  `mob.points += total_vector` without going through `apply_points_function_about_point`
  (`:1282-1283`); both still iterate `family_members_with_points()` and assign to leaves
  (`:1582-1584`); those are still the only geometric writes in `Mobject`;
  `_AnimationBuilder.__init__` still calls `generate_target()` (`:3418`) and still
  consults `_override_animate` first (`:3441`); `Wiggle` still writes in place and then
  scales and rotates (`indication.py:559-567`). The design survives the version
  correction unchanged; only the numbers move.
- **Citations switch to symbols.** Every reference is now
  `file::Symbol` with the 0.21.0 line as a parenthesised hint, so the next version bump
  invalidates a hint rather than an argument.

**Accepted — transform ordering is a real bug in the model (finding 1).**
`apply_function(f); shift(v)` must be `shift(f(points))`, and a single affine `T` plus a
replayed list of non-affine callables computes `f(shift(points))`. The `Map` paragraph
already had the right structure — an ordered chain where adjacent affine nodes collapse
and non-affine nodes are barriers — and the "points are derived" paragraph contradicted
it by describing `T` as one matrix with a side list. `T` is now the same ordered chain,
and collapse is an optimisation over adjacent affine runs rather than a claim that all
placement is one matrix.

**Accepted, in a bounded form — the transient test needs a precondition, not a context
(findings 2, 3).** Codex is right that a dirty buffer is ambiguous between an animation's
temporary geometry and a user's own mutation. There is no hook to open an animation
context on animations we do not own, so the answer is a stated precondition instead:
**a supported animation must leave the buffer equal to the derived points when it ends.**
That is not a hope — `Create`, `Uncreate` and `Write` end at the full shape, and `Wiggle`,
`ApplyWave` and `Indicate` are there-and-back, so all six end clean, and each gets a test
asserting exactly that. An animation that does not restore is outside the supported
surface. This also supplies the missing clear event of finding 3: the buffer going clean
*is* the event, and the getter runs the deferred rebuild the moment it observes
buffer == shadow with a dirty flag pending. Any geometric call on a dirty buffer warns and
names `refresh()`, so the narrow remaining window is loud rather than silent.

**Accepted — polling needs defined equality (finding 4).** Our own parameters use a
version counter and never compare values. Foreign bindings are snapshotted immutably and
compared by type: scalars NaN-aware, so `NaN` equals `NaN` and does not rebuild forever;
arrays by `np.array_equal(..., equal_nan=True)`; callables always dirty.

**Accepted — binding cardinality is a hard invariant (finding 5).** One artist belongs to
one coordinate system. `ax2.add(curve)` on a curve already bound to `ax1` raises instead
of silently rebinding. Showing one dataset in two systems is a second artist over the same
source, and a shared-view object is deferred past 0.1.

## Round 8 — Codex

One implementation-breaking contradiction remains:

- `PLAN.md:130-141` requires every supported animation to end with the buffer equal to the derived geometry, but `.venv` Manim 0.21.0’s `Uncreate` is `Create` with a reversed rate function and removes the object; its final geometry is empty, not the full derived shape. A dirty bound parameter during or after `Uncreate` can therefore remain deferred or rebuild from an invalid empty override. Fix: remove `Uncreate`/other non-restoring animations from the supported surface, or define animation-specific cleanup that restores the derived buffer before removal.

- The same precondition is not valid for arbitrary supported “in-place writes”: `Wiggle` restores its points by construction, but user writes and future Manim animations have no guaranteed restoration. The plan calls this a warning/escape-hatch ceiling, yet the implementation cannot distinguish an unrestored user edit from a still-running animation and may indefinitely suppress rebuilds. Fix: make the supported contract apply only to named library-tested animations and reject or immediately mark arbitrary user in-place writes as requiring `refresh()` before data updates.

VERDICT: REVISE
### Claude's response

Both accepted, and the first is a genuine hole in the precondition this log invented two
rounds ago.

`creation.py::Uncreate` (`:180`) is `Create` with `reverse_rate_function=True` and
`remover=True` (`:200-208`), so it ends on degenerate geometry, not the full shape. Naming
it among the restoring animations was wrong.

The fix scopes the contract to a named, tested list instead of a category, and splits that
list in two. Restoring animations — `Create`, `Write`, `ShowPassingFlash`, `Indicate`,
`Wiggle`, `ApplyWave`, `Flash`, `Circumscribe` — end on the derived points and each carries
a test asserting it. Removing animations — `Uncreate` and anything built the same way — are
supported *as removals*: the buffer is left degenerate, which costs nothing because the
mobject leaves the scene, the data was never touched, and re-adding the artist requires
`artist.refresh()`. That is documented next to `Uncreate` and tested.

The second finding is accepted in the same move, which is also Codex's own fix: the
contract covers only the named animations. An arbitrary user in-place write is explicitly
not covered — it warns on the next geometric call, the docs require `refresh()` before the
data channel is used again, and the plan states plainly that the library cannot distinguish
an unrestored user edit from a running animation and does not try. The consequence, a plot
that stops responding to its own data until refreshed, is now written into the risk list
rather than left implicit in a ceiling.


## Round 9 — Codex

Cold re-review found no remaining implementation-breaking defect or redesign requirement.

The transient split now matches Manim 0.21.0: `Uncreate` reverses `Create`, removes the mobject, and is not restoring. The refresh requirement for arbitrary in-place writes is explicit and tested. The remaining ceilings and documentation placements are deliberate scope decisions.

VERDICT: APPROVED
### Resolution

APPROVED after nine rounds, and this one carries weight round 6's did not: the prompt
named what had changed but handed Codex no fix it had not itself proposed, and it
re-verified against the project's own `.venv` rather than the plan's citations.

Act 2 closed. No unresolved disagreement remains. The plan grew from 125 to roughly 400
lines, and four of its load-bearing claims were wrong when the review started.
