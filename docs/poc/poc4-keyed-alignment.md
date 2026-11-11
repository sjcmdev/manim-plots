# Keyed-alignment proof of concept (v4)

Measured on 2026-10-24 with **Manim 0.21.0**, Python 3.13.2, NumPy 2.5.2,
Cairo, Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1,
24 logical CPUs. This is a disposable experiment, not package implementation or
an API proposal. The starting directory was a copy of `poc/poc3/`; all imports were
changed to `poc4`. There are no imports from `poc3`, `poc2` or `poc`.

Implementation, tests, media and measurements are under [`poc/poc4/`](../../poc/poc4/).
This report is the only file added outside it. The existing `pyproject.toml`
modification and v4 prompt predated the experiment. Production source, existing
tests, previous PoCs, PLAN, TODO and ADRs were not edited. No installation,
network, TeX, movie encoding, Manim class monkeypatch or commit was used.

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| L1: native data/geometry chains | **CONFIRMED** | Five native chains render nine frames each with correct range, keys and geometry; maximum error 1.33487e-15 and zero differing channels against ordinary current-graph VMobjects. |
| L2: tick identity | **CONFIRMED** | A red tick and label retain identity and color, including exit/return within one animation; separate edits discard departed objects. |
| L3: another system | **CONFIRMED** | Both transform classes render correct ticks/artists, with zero endpoint system error; replacement retains ownership by the old system. |
| L4: remover/introducer lifecycle | **CONFIRMED** | Explicit removers retain native cleanup buffers, re-add with zero pixel differences, ignore data/frame changes and reattach through refresh or an introducer. |
| L5: nonlinear densification | **CONFIRMED** | Sparse leaves grow from 4 to 256 controls only for nonlinear frames; maximum wave-axis error falls from 0.303871 to 0.00131692, with a measurable grid error floor. |
| L6: source facts with unchanged K3/K4 results | **FALSIFIED** | Exact matrices and source-derived write lines work without probes, but PhaseFlow retains 31 nonlinear nodes instead of v3's one affine node. |
| L7: cost and regression | **CONFIRMED** | 296 tests pass; unchanged F-1001 p95 is 3.0707/3.7327 ms, and 600 parameter frames have update p95 3.9064 ms. |

Verdicts apply to the specified experiments and boundaries below. Replacement
does not transfer bindings, the nonlinear grid remains approximate, and full Cairo
frame cost exceeds a 60 fps budget. Passing tests include negative experiments.

## Boundaries and measurement

[`model.py`](../../poc/poc4/model.py) retains v3's derived points, invisible frame, weak
registry, local placement, polling and simulation. The original default System
with ten fixed tick leaves remains the unchanged F-1001/regression fixture.
New structural experiments explicitly use `System(locator=Multiple())` or MaxN.
These are experiment controls, not a proposed public API.

The keyed fixture owns a frame, x/y axis roles, `(tick, locator.key(v))` roles and
a few `(label, key)` roles. Labels are corner-path VMobjects without fonts or TeX.
Multiple uses integer multiples and integer keys. MaxN chooses a 1/2/5/10 step from
the current span and uses rounded numeric-value keys; its step changes during
playback. A 1e-12 locator boundary tolerance prevents ceil/floor membership changes
from roundoff at integral ticks. Duplicate keys raise. Only emitted values are
queried in this small locator experiment; it does not implement the full ADR
Locator protocol or propose changes to that protocol.

At the actual Transform.begin call, System.align_data builds a union of keys at
frame-sized parameter steps, including endpoints and the animation rate function.
It constructs the same semantic role order on both objects, reusing existing live
leaves. It bypasses Mobject.align_data for keyed families. No role is inferred from
geometry, deltas, or get_family call order. Inactive keys have zero opacity; active
keys near sampled birth/death boundaries also use partial opacity. This envelope
is an experimental transition, not a production opacity design.

The frame interpolates native points through Manim's path function and interpolates
the range. Decorations derive current geometry instead of interpolating leaf points.
Resume trims the pool. Tested systems have matching frame resolution and locator
rules. Heterogeneous frames, locator replacement, target style changes and extra
manually parented children in the keyed fixture are not established. Copied parenting
experiments still use the original fixture.

The pool covers the tested rendered schedule, not every real alpha of an arbitrary
discontinuous locator or custom animation. Changing the schedule or sampling between
prepared steps requires a new pool. A production pool lifetime/schedule contract
remains work for PLAN.

Ordinary scenes use **320x180, 15 fps, 0.6 s**, nine actual renders through Scene.play.
Chains/system transforms use linear easing; the identity-return case uses
there_and_back. Cost scenes use **1920x1080, 60 fps**. No render marker, movie,
caching or tempfile helpers are involved. Pixel differences count array channels.
Outside L5, errors are maximum control-point distances; the inherited unequal-size
helper uses symmetric nearest-control-point distance.

For L1, ordinary VMobjects undergo a separate real Transform, providing an
independent native frame trajectory, including path_arc. Numeric range mapping and
an independently solved planar affine map generate expected controls. Each render
is compared with fresh ordinary VMobjects at those expected positions. This is a
correct current-graph reference; ordinary VMobjects do not have a data-range setter.
L3 also plays native Transform/ReplacementTransform controls for scene identity.
L4 compares real native animation/cleanup and re-add pixels. JSON evidence is under
[`results/`](../../poc/poc4/results/); `python -m poc4.summary` prints report inputs.

## L1 — native data plus geometry

`test_l1_native_chain` plays all four requested expressions and an additional arc
case. Each has **11 interpolations / nine rendered frames**, matching role triples
in the zipped families, correct active keys and range, hidden inactive keys and
observed partially opaque active ticks. Entry/exit does not morph tick points.

| Case | Maximum frame geometry error | Range/keys/roles | Native reference channels | Final vs direct | Manim does the same? |
| --- | ---: | --- | ---: | ---: | --- |
| shift(RIGHT).set_x_range((0,20)) | 8.88e-16 | Pass | 0 | 0 | Yes for native trajectory/current ordinary graph; the data setter is added behavior. |
| set_x_range((0,20)).shift(RIGHT) | 8.88e-16 | Pass | 0 | 0 | Same qualification. |
| scale(.5).set_x_range((-5,5)).rotate(PI/6) | 1.33487e-15 | Pass | 0 | 0 | Same qualification; animate.rotate uses native endpoint interpolation. |
| set_x_range((0,100)), MaxN | 8.88e-16 | Pass, including intermediate step changes | 0 | 0 | Same geometry reference; native data-driven ticks are added behavior. |
| shift/range, path_arc=PI/3 | 8.90e-16 | Pass | 0 | 1.57e-16 | Yes: the frame follows the native curved path. |

In table order, pools contain **24/24/11/17/24 tick keys**, and align_data costs
**3.9179/3.9343/1.8454/7.4984/4.3502 ms**. All starting copies inherit the complete
pool. Final families contain **26/26/17/10/26** members including frame, axes and
labels, with unique identities and no surplus ticks. No exceptions occur.

System.set_x_range has no `_override_animate`. MethodAnimation.finish replays
methods while the pool exists; its following final interpolation sets the prepared
frame/range target. Direct-operation equality and unique-object counts prove no
doubled shift, scale, rotation or child insertion in these cases.

Copied `test_g7_native_parameter_interpolation_tick_alignment` now succeeds instead
of throwing the owner AttributeError. `test_g7_native_same_tick_count` now has correct
intermediate tick sets. The separate test-only OverrideRangeSystem still reproduces
Manim's override-chain rejection; that native rule was not altered.

Installed evidence: `mobject.py::_AnimationBuilder.__getattr__` (`:3443-3456`)
rejects override chains; `transform.py::Transform.begin` (`:200-212`) aligns before
base begin. `animation.py::Animation.begin` (`:205-214`) then creates the starting
copy; `animation.py::Animation.create_starting_mobject` (`:263-265`) copies it.
`transform.py::Transform.get_all_families_zipped` (`:232-240`) strictly zips live,
starting and target-copy families; `animation.py::Animation.get_all_families_zipped`
(`:279-286`) is the base variant. `transform.py::Transform.interpolate_submobject`
(`:242-250`) calls leaf interpolate. `transform.py::_MethodAnimation.finish`
(`:448-451`) replays methods before base finish. The index-based padding in
`mobject.py::Mobject.add_n_more_submobjects` (`:3079-3098`) is bypassed, not patched.

**PLAN / ADR 0001 changes:** replace mandatory data-mutator overrides and F-909's
no-chain ceiling with native copies, role/key alignment and parameter interpolation.
Specify pool scheduling/lifetime, structural copying, heterogeneous-system behavior
and endpoint pruning. Finite frame sampling does not prove arbitrary locator paths.

## L2 — identity through a pool

`test_l2_identity_and_return` colors tick key 2 and its label RED. A there_and_back
range animation makes that key inactive in the middle, then restores it. Both
objects and colors survive, including the following mixed shift/range chain.
Separate direct edits that remove key 2 and bring it back create a new unstyled tick.

| Event | Same object | Hand-applied style |
| --- | --- | --- |
| Survives L1 endpoint | Yes, tick and label | Retained |
| Leaves/returns within one prepared animation | Yes | Retained |
| Leaves/returns across separate edits | No | Lost |

No style-override table is involved. Installed evidence:
`animation.py::Animation.create_starting_mobject` (`:263-265`) copies references for
interpolation; `transform.py::Transform.get_all_families_zipped` (`:232-240`) requires
the matching structure. Identity comes from retaining the live leaf, not replacing
it with either copy.

**PLAN / ADR 0001 changes:** qualify D10 by pool lifetime: active-set departure is
not destruction while the pool owns the object. Keep Locator.key ownership and
uniqueness. Separate-edit exit/return still loses style as PLAN currently says.

## L3 — another system

`test_l3_other_system` uses a second System with range (0,20), shifted RIGHT. Both
classes render **nine frames / 11 interpolations**. Maximum curve/tick errors are
**8.88e-16 / 1.33227e-15**, with **zero** endpoint system error. The source's range
becomes (0,20), so registered artists follow its new mapping. Keys are correct in
every frame; the pool is trimmed.

| Case | Every-frame geometry/keys | Endpoint | Scene after cleanup | Ownership/later motion | Manim does the same? |
| --- | --- | --- | --- | --- | --- |
| Transform(ax,new_ax) | Pass | Equal to new_ax | ax present, new_ax absent | Artist belongs to ax; new_ax.shift has zero effect; ax.shift moves it once | Yes for scene/object identity; external-artist following is intentional binding. |
| ReplacementTransform(ax,new_ax) | Pass | Equal to new_ax | ax absent, new_ax present | Artist still belongs to ax; new_ax.shift has zero effect; removed ax.shift moves it once | Yes for native replacement identity; automatic binding transfer is absent. |

Both later-motion errors are **0**. Manim replaces scene objects without rewriting
external Python references, so source ownership follows native identity semantics.
However, users treating replacement as a transparent axes-rescaling idiom may expect
the visible new axes to own old curves. That expectation is **not met**: the curve's
system and visible system diverge. L3 confirms geometry and ownership measurement,
not transparent transfer.

Installed evidence: `transform.py::Transform.begin` (`:200-212`) prepares target_copy;
`transform.py::Transform.clean_up_from_scene` (`:219-222`) calls scene.replace only
for replacement. `mobject.py::Mobject.copy` (`:895-919`) uses deepcopy; scene replacement
is not Python reference rebinding.

**PLAN / ADR 0001 changes:** explicitly choose source ownership, as measured, or a
separately specified binding transfer. Role alignment alone cannot make replacement
a transparent rescale for subsequent updates. Transform is the tested rescale idiom.

## L4 — detached removal state and reattachment

`test_l4_remover_state` plays Uncreate, FadeOut and ShrinkToCenter(remover=True),
finishes cleanup, re-adds the same object, changes range and moves the frame.
All three have **0 native endpoint error, 0 re-add pixel-channel differences and
0 subsequent motion**. Uncreate and explicit Shrink leave degenerate buffers;
FadeOut cleanup restores the original full buffer. refresh attaches and reconstructs
the current curve with **0 error**. Detached getters/polling do not rebuild or sample.

ShrinkToCenter does **not** set remover=True by default in Manim 0.21. The separately
tested default stays present and attached, with accepted zero-scale placement;
a later frame shift moves the collapsed point one unit.

`test_l4_introducer_current_data` runs Create, Write, FadeIn and GrowFromCenter after
each of Uncreate and FadeOut, changing range while detached. All **eight** combinations
attach and draw the full current curve. Maximum endpoint error is **1.11e-15** and
maximum frame error against the same animation on a fresh ordinary current-geometry
VMobject is **1.33e-15**.

| Case | Retained/re-added state | Reacts while detached? | Reattachment | Manim does the same? |
| --- | --- | --- | --- | --- |
| Uncreate; add | Degenerate; zero differing channels | No | Add does not attach | Yes |
| Uncreate; data change | Same degenerate buffer | No | None | Yes for a retained ordinary buffer; ordinary Manim lacks data binding. |
| Uncreate; Create | Full current curve after drawing | — | At begin | **No: intentional regeneration.** Ordinary Uncreate + Create remains degenerate. |
| Uncreate; Write/FadeIn/GrowFromCenter | Full current curve | — | At begin | Same regeneration difference; animation matches a fresh ordinary current curve. |
| FadeOut; add | Original full cleanup buffer; zero differing channels | No | Add does not attach | Yes |
| FadeOut; FadeIn/other introducers | Full current curve | — | At begin | Yes on current geometry; applying pending data is the binding policy. |
| ShrinkToCenter(remover=True); add | Degenerate; zero differing channels | No | Add does not attach | Yes |
| ShrinkToCenter default | Collapsed, present and attached | Not detached | Unnecessary | Yes for endpoint/scene membership; bound frame motion is intentional. |
| refresh after explicit removal | Full current curve; zero error | — | Explicit | Added library behavior; ordinary buffers have no data refresh. |

Ordinary introducers after Uncreate keep the old degenerate buffer (endpoint
separation **4.80829** from our current curve); after FadeOut they retain old full
geometry (separation **1.2** after the range change). These are regeneration/binding
effects, not unexplained animation errors.

Two lifecycle details are essential. Transform introducers prepare targets before
suspension: alignment refreshes those buffers but keeps the live artist detached
until suspension. At that boundary the start is recreated, as is Write's outline.
GrowFromCenter captures its center in its constructor. Keeping that stale point
produced **3.00332** frame error after Uncreate despite a correct endpoint. The final
code recognizes the actual GrowFromCenter object and refreshes its stored center
before creating the start. Arbitrary GrowFromPoint points are untouched. All final
frame comparisons pass, without patching a Manim class.

Installed evidence: `animation.py::Animation.is_remover` (`:474-482`) and
`animation.py::Animation.is_introducer` (`:484-492`) expose flags.
`animation.py::Animation.finish` (`:225-227`) resumes before cleanup;
`animation.py::Animation.clean_up_from_scene` (`:229-245`) calls finish callbacks and
removal. `fading.py::FadeOut.clean_up_from_scene` (`:190-192`) then interpolates to zero.
`creation.py::ShowPartial.interpolate_submobject` (`:126-134`) uses starting geometry;
`creation.py::DrawBorderThenFill.begin` (`:253-255`) prepares an outline.
`growing.py::GrowFromCenter.__init__` (`:132-133`) stores the point;
`growing.py::GrowFromPoint.create_starting_mobject` (`:93-99`) uses it.
`transform.py::ShrinkToCenter.__init__` (`:594-595`) passes only scale factor zero.

**PLAN / ADR 0001 changes:** replace unconditional final rebuild with detached cleanup
buffer ownership. Require introducer/refresh reattachment, including targets, starting
copies, outlines and constructor-captured derived pivots. State the single intentional
lifecycle difference as regeneration after destructive removal; Uncreate + Create is
its simplest example. Never infer removal from a name. Already-detached adopted plain
targets also obey the no-auto-rebuild rule.

## L5 — densification and remaining grid error

`test_l5_densification` plays ApplyPointwiseFunction(wave, ax) and the native
animate.apply_complex_function(z**2) path, with frame **N=65**. Twelve axis/tick
leaves keep **4 controls** after affine shift/rotate/scale and use **256 controls**
(64 cubics) after nonlinear transformation. The existing frame check supplies
affinity, with no extra affine comparison pass or dense sample allocation.

Four constructions are compared with independent analytic truth: sparse frame-derived
controls before refinement, dense frame-derived geometry, ordinary sparse Manim
geometry and ordinary geometry prepared with
NumberPlane.prepare_for_nonlinear_transform(...,64). The last method runs Manim's
implementation on the ordinary VMobject group. Truth uses 10,001 analytic samples;
native cubic paths use 129 evaluations per curve. The metric is symmetric
sample-to-neighbor-segment distance, removing coincident segment endpoints before
projection. These are sampled geometric errors, not rigorous continuous bounds or
distances between unrelated control arrays.

| Function / subset | Derived sparse | Derived dense | Ordinary sparse | Ordinary prepared |
| --- | ---: | ---: | ---: | ---: |
| Wave, maximum axis error | 0.303871 | 0.00131692 | 0.551824 | 5.41410e-6 |
| Wave, maximum tick error | 0.00107469 | 0.00107469 | 5.55e-16 | 8.88e-16 |
| z**2, maximum axis error | 3.00146 | 4.34e-19 | 0.0300000 | 8.67e-19 |
| z**2, maximum tick error | 0.00202014 | 0.00217014 | 1.22183e-5 | 2.98294e-9 |

Densification fixes the severe sparse-axis failure, but not grid interpolation error.
Vertical wave ticks already have the correct straight shape and inherit grid offset.
Some square ticks have slightly larger analytic error after refinement because they
follow the approximate bilinear frame more faithfully. Ordinary prepared Manim
evaluates the analytic function directly and is more accurate. Nonlinear parity is
still approximate: worst dense errors are **0.1778/0.2930 pixels at 1080p** for
wave/square.

Forced full rebuilds of all twelve dense leaves, including new sample weights,
cost median/p95 **1.5072/1.8797 ms** for wave and **1.5962/2.4798 ms** for square,
with 30 observations each. The affine F-1001 path retains original point counts
and 60 median frame comparisons. No densification allocation or extra comparison
pass occurs there; this does not claim identical timing or zero branch instructions.

Installed evidence: `coordinate_systems.py::NumberPlane.prepare_for_nonlinear_transform`
(`:2950-2955`) inserts curves; `vectorized_mobject.py::VMobject.apply_function`
(`:1226-1228`) conditions handles around mapping.
`transform.py::Transform.interpolate_submobject` (`:249`) provides native frame
interpolation but does not refine derived lines.

**PLAN / ADR 0001 changes:** require conditional sparse-leaf refinement under nonlinear
frames. Distinguish shape density from frame-map accuracy and preserve finite-grid
error/extrapolation limits. Do not promise equality to prepared NumberPlane. The fixed
64-segment experiment does not settle adaptive sampling or propose a density API.

## L6 — exact facts and a changed K4 result

[`context.py`](../../poc/poc4/context.py) derives final points-write lines at import using
inspect and AST assignments, including augmented assignments. Active native caller
code objects/locals supply exact rotation, scale, stretch and matrix facts. Shift
supplies its exact vector. Other functions remain nonlinear nodes, even if
mathematically affine; no artist operation is evaluated on probe points. Three
planar frame anchors and the full-node frame-affinity check remain representation
checks, not probes of an artist operation.

`test_l6_source_lines_and_no_probes` calculates **1283/1584** from actual source.
Prepending one line to the supplied source text moves results to **1284/1585**,
without modifying Manim. An arbitrary batched function sees exactly **one 36-point
data buffer**, zero probe calls, and remains callable. Rotate/scale/stretch/apply_matrix
each retain one matrix node. K3's foreign-container/new-data maximum error remains
**2.22089e-14**. K4 local placement error is **2.22e-16**, bounds error zero, and ten
frame-only changes still build zero new artist weights.

The full L6 conjunction is **FALSIFIED**. In `test_k4_placement_growth`, MoveAlongPath
keeps **one** node after 30 frames, with **1.55e-15** error. PhaseFlow(lambda p: .1*p+UP)
keeps **31 callable nodes**, with zero native geometry error. None of the four exact
affine caller frames exists for that callback. Treating other functions as nonlinear
facts cannot preserve v3's probe-based one-node guarantee. No probe, bytecode guess
or point-delta fit was added to recover that claim.

`test_l6_callback_simulation` explicitly classifies once, recording [0,1], and then
plays the animation, which classifies again: **15 callback effects / nine rendered
frames**, comprising 11 native interpolations and four simulation calls.

**Callbacks with external side effects run during classification as well as playback,
so those effects occur extra times.** This is the maintainer's decision for all
animations, not an exclusion rule or isolation guarantee.

Installed evidence: `mobject.py::Mobject.rotate` (`:1410-1413`) supplies rot_matrix;
`mobject.py::Mobject.scale` (`:1335-1337`) supplies scale_factor;
`mobject.py::Mobject.stretch` (`:1451-1455`) supplies factor/dim;
`mobject.py::Mobject.apply_matrix` (`:1499-1504`) supplies full_matrix.
`mobject.py::Mobject.shift` (`:1282-1283`) and
`mobject.py::Mobject.apply_points_function_about_point` (`:1582-1584`) contain the
source-derived final writes. `movement.py::PhaseFlow.interpolate_mobject`
(`:165-170`) invokes a generic callback, not these affine methods.

**PLAN / ADR 0001 changes:** remove finite affinity probes and hard-coded write lines.
Restrict collapse guarantees to exact affine facts; arbitrary callback flows can grow
one node per step. Record unconditional callback simulation and its extra effects.
A broader bounded-storage guarantee requires another justified mechanism.

## L7 — cost and regression

The exact requested command passes **296 tests in 49.84 s**. Both repository-wide
Ruff checks pass. This includes all **257 original v3 cases**, **14 additional source
guards**, and **25 L cases**. No tests were deleted, skipped or xfailed.
[`full-final.log`](../../poc/poc4/full-final.log) records the run. Source guards check **68
symbols**: version, first source line and SHA-256 of complete inspected source.

F-1001 keeps four 2,000-sample artists, ten ticks, two axes, **606** rendered dirty
frames and **608** interpolations. The original fixture/workload is unchanged.

| Workload | Frames | Median rebuild ms | p95 rebuild ms | Absolute 4 ms gate |
| --- | ---: | ---: | ---: | --- |
| F-1001, affine | 606 | 2.3056 | 3.0707 | Pass |
| F-1001, forced bilinear N=33 | 606 | 2.7229 | 3.7327 | Pass |

`test_l7_parameter_cost` uses MaxN and four 2,000-sample callable artists for range
(-3,3) -> (0,100): **600 actual 1080p60 frames / 602 interpolations**. Alignment samples
**601** positions and prepares **21** tick keys, including intermediate-only keys.
One measured align_data call costs **12.7330 ms**.

| Parameter workload timer | Result |
| --- | ---: |
| Scene.update_to_time median/p95 | 2.8473 / 3.9064 ms |
| Accumulated pipeline rebuild per rendered frame, p95 | 2.8203 ms |
| Update plus Cairo render, p95 | 19.0558 ms |

Update includes interpolation and updating; render includes Cairo and lazy camera
rebuilds. Pipeline timing overlaps these timers, so do not add them independently.
Observation and JSON serialization are excluded. Alignment, copying and simulation
are setup costs. The full **19.0558 ms** frame exceeds **16.6667 ms**: passing the
pipeline gate does not prove end-to-end 60 fps. The old 1.5x baseline gate is not
newly certified by this PoC.

### Changed copied expectations

| Copied test/helper | Change from v3 | Reason |
| --- | --- | --- |
| All copied files | Imports/ROOT: poc3 -> poc4 | Independent copy, no imports from earlier PoCs. |
| RangeSystem/observe_range in test_data_channel | Use keyed System/Multiple; count active rather than hidden pool leaves | A changes structural lifetime and parameter ownership. Old Tick/ParameterFrame helpers were replaced, not tests removed. |
| test_g7_native_parameter_interpolation_tick_alignment | No owner exception; correct frames | Role/key alignment bypasses index padding. |
| test_g7_native_same_tick_count | Every intermediate key set is correct | Endpoint count no longer substitutes for identity. |
| test_g3_artist_animation, detached cases | Keep cleanup buffer across range changes rather than requiring new derived data | B1: Uncreate, ShowPassingFlash, FadeOutShift and already-detached plain targets obey frozen-state ownership. Uncreate now matches native degenerate endpoint/re-add. |
| Same test, data changing during removal | Assert zero persisted-buffer change; stop requiring the live-data oracle after detachment | Cleanup captures its actual buffer before later animations' final updates. Old-live-data errors remain recorded in JSON. |
| test_k4_placement_growth | PhaseFlow has more than one node; MoveAlongPath still has one; both match native geometry | B4 exact caller facts replace sampled affinity. PhaseFlow has no affine caller fact, falsifying that part of L6. |

The override-chain negative control still raises; it is a test-only subclass, not
the core method. Other assertions remain: protected axis Uncreate, raw writes,
aliasing, camera freezing, registry/copy, callable polling and double displacement.

Installed evidence: `scene.py::Scene.update_to_time` (`:1700-1708`) defines the
interpolation/update boundary; `scene.py::Scene.play_internal` (`:1390-1393`) finishes,
cleans up and flushes endpoints; `cairo_renderer.py::CairoRenderer.play` (`:112-118`)
handles frozen waits. Endpoint-only lifecycle calls are confined to D's classifier.

**PLAN / ADR 0001 changes:** keep the absolute pipeline gate distinct from complete
renderer timing, setup latency and the relative baseline. Replace the expectations
above and add keyed/source contracts to upgrades. Passing regression tests do not
turn the surviving negative experiments into compatibility guarantees.

## Updated differences from ordinary Manim

| v3 difference | v4 status |
| --- | --- |
| Curves follow temporary axis indications/fades | Removed on the copied matrix; binding still freezes them. |
| Curves follow permanent axis changes | Retained intentional binding; ordinary independent curves stay still. Rotate(TAU) stays temporary. |
| Simultaneous independent system/artist motion adds twice | Retained and tested. |
| Foreign containers leave artists behind | Removed on K3; exact affine facts and native nonlinear handles remain valid. |
| Shifted FadeOut leaves an offset on re-add | Removed; native cleanup buffer is retained, now detached. |
| Uncreate(curve) re-adds full | **Removed**; re-add is pixel-identical and degenerate like Manim. |
| Detached artists rebuild on data | **Removed**; data/frame changes have zero effect until reattachment. |
| Reintroducing a destructively removed curve remains degenerate | **Intentional regeneration**; Create/Write/FadeIn/GrowFromCenter rebuild current geometry, unlike the ordinary retained degenerate buffer. |
| Uncreate(ax) protects its invisible frame | Retained; raw hidden-frame geometry stays usable. |
| Larger targets fail before suspension | Removed on the copied 36 -> 196 point test. |
| Finite-grid errors, folds, discontinuities and aliasing | Retained; densification fixes sparse shape error, not missing map information. |
| Nonlinear inverse branches and singular frames | Retained approximate/nonunique/raising behavior. |
| Scene-coordinate placement and off-plane pivot marker | Removed on the copied affine/local/bounds matrix; conventional normal extension and nonlinear inverse limits remain. |
| Data/geometry overrides reject chains | **Removed for the keyed native System path**; ordinary Manim's override rejection is unchanged. |
| Equal tick count loses identity | **Removed for keyed families**. |
| D10 loses styling on every exit/return | **Qualified**: pool-local return retains style; separate-edit return loses it. |
| Replacement transfers bindings to visible new axes | **Not provided**; native replacement retains source ownership. |
| Raw/in-place NumPy writes lack provenance | Retained v3 fallback. |
| Hidden leaf consumes a drawing lag slot | Retained scheduling cost, as clarified in v3 Review notes; not a comparison against Manim Axes' different hierarchy. |
| Sparse derived axes deform incorrectly | Substantially improved; prepared native analytic geometry can still be more accurate than the frame. |
| Artist-operation affinity uses probes | **Removed**; arbitrary functions remain nonlinear and PhaseFlow placement grows. |
| Classifier callbacks are isolated from external state | No such guarantee: all animations are simulated, with extra external callback effects. |

## Updated stack and source contract

The mechanism matches code objects and retains copied values/actual objects, never
Python frames. No get_family frame is read; family traversal is only for actual
object membership and native rendering. Exact-affinity frames extend v3's contract.

| Stack symbol | Relevant lines | Required locals / dependency |
| --- | --- | --- |
| animation.py::Animation.begin | :205-214 | self: actual animation, suspension/introducer flags; starting_mobject exists. |
| transform.py::Transform.begin | :200-212 | self: early alignment, run_time/rate_func, target buffers; union before starting copy. |
| composition.py::AnimationGroup.begin | :94-96 | self: outer suspension before children. |
| composition.py::Succession.begin | :238-244 | self: child begins can occur during playback. |
| animation.py::Animation.finish | :225-227 | self: matching resume and remover state. |
| composition.py::AnimationGroup.finish | :103-108 | self: nested resume ownership. |
| composition.py::Succession.finish | :246-248 | self: child resume ownership. |
| mobject.py::Mobject.shift | :1282-1283 | self,total_vector; final write computed from inspect/AST at import. |
| mobject.py::Mobject.apply_points_function_about_point | :1582-1584 | self,func,about_point; source-derived final write. |
| mobject.py::Mobject.rotate | :1410-1413 | rot_matrix: exact matrix after transpose. |
| mobject.py::Mobject.scale | :1335-1337 | scale_factor: exact diagonal matrix. |
| mobject.py::Mobject.stretch | :1451-1455 | factor,dim: exact diagonal entry. |
| mobject.py::Mobject.apply_matrix | :1499-1504 | full_matrix: exact matrix after transpose. |
| vectorized_mobject.py::VMobject.apply_function | :1226-1228 | self,function: native handle conditioning. |
| vectorized_mobject.py::VMobject.set_anchors_and_handles | :844,:850-852 | Immediate caller code: scratch buffer during slice construction. |
| scene.py::Scene.update_to_time | :1700-1708 | self,t: callable synchronization token. |
| scene.py::Scene.play_internal | :1390-1393 | self, renderer play count: endpoint synchronization. |

Other symbol dependencies include strict family zip/leaf interpolation, copy/deepcopy,
cleanup ordering, remover/introducer flags, Write outline creation, GrowFromCenter's
stored point and curve insertion. GrowFromCenter is identified by its actual class:
a specific lifecycle dependency, not inferred affinity or a permanence whitelist.

[`manim_contract.json`](../../poc/poc4/manim_contract.json) guards **68 symbols**.
[`evidence.py`](../../poc/poc4/evidence.py) writes symbol headings before numbered installed
source to [`manim_sources.txt`](../../poc/poc4/results/manim_sources.txt). All 54 copied
contracts remain, with 14 added dependencies. Freezing is an explicit evidence
command, never part of pytest. A frozen hash only rejects changed source; the
shifted-source test separately proves the final-write calculation follows it.

## Review notes

Maintainer rerun outside the Codex sandbox: **296 passed in 49.93 s**, both Ruff checks
pass, and no Manim class attribute is assigned anywhere in `poc/poc4/`. Found by reading
`poc/poc4/model.py`:

- **Reattachment rewrites the animation object.** `Derived.suspend_updating` (around
  `:626-635`) rebuilds `animation.starting_mobject` and `animation.outline`, and for
  `GrowFromCenter` alone overwrites `animation.point`, matched by class. This patches
  an instance, not a class, but it is a list of one: `GrowFromEdge`,
  `GrowFromPoint` called with the old center, `SpinInFromNothing` and `GrowArrow` keep
  their constructor-time points too and are not tested. Production needs either the
  whole family of constructor-captured points named in the contract, or reattachment
  early enough that constructors read live geometry. The second is the only option
  that is not a list.
- **The 19 ms full-frame time is Cairo rasterising four 2,000-sample curves at
  1080p.** Manim renders offline, so this is not a real-time budget, and F-1001
  deliberately measures the pipeline alone. It is not a finding against the design.

## Reproduction

Run in repository-root PowerShell with the existing venv. Tests overwrite their
named JSON files in poc/poc4/results. Media directories use ordinary Path.mkdir.

```powershell
# Complete suite: copied v3 cases, new experiments and all 68 source guards.
.venv\Scripts\python.exe -m pytest poc/poc4 -p no:cacheprovider

# L1 and updated G7, including the separate override-chain control.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py poc/poc4/test_data_channel.py -p no:cacheprovider -k "l1 or g7"
# L2: object/label identity, style and both kinds of exit/return.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py -p no:cacheprovider -k l2
# L3: both transform classes, independent ticks and later ownership/motion.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py -p no:cacheprovider -k l3
# L4: cleanup/re-add pixels, refresh, default Shrink and eight introducer cases.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py -p no:cacheprovider -k l4
# L5: analytic errors, ordinary prepared controls and rebuild cost.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py -p no:cacheprovider -k l5
# L6: facts, shifted source, callbacks and K3/K4 comparison.
.venv\Scripts\python.exe -m pytest poc/poc4/test_keyed.py poc/poc4/test_containers.py poc/poc4/test_fixes.py -p no:cacheprovider -k "l6 or k3 or k4"
# L7: original F-1001 and 600-frame parameter scene.
.venv\Scripts\python.exe -m pytest poc/poc4/test_cost.py poc/poc4/test_keyed.py -p no:cacheprovider -k "g6 or l7"
# Original 203 behavioral cases plus expanded source guards: 271 cases.
.venv\Scripts\python.exe -m pytest poc/poc4 -p no:cacheprovider --ignore=poc/poc4/test_keyed.py

# Installed source and guarded contracts. Do not freeze automatically on upgrade.
.venv\Scripts\python.exe -m poc4.evidence
.venv\Scripts\python.exe -m pytest poc/poc4/test_manim_contract.py -p no:cacheprovider
.venv\Scripts\python.exe -m poc4.summary
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```
