# Stack-context proof of concept (v3)

Measured on 2026-10-24 with Manim **0.21.0**, Python 3.13.2, NumPy 2.5.2,
Cairo, Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1,
24 logical CPUs. This is a disposable experiment, not a production implementation
or an API proposal.

The starting directory was a copy of `poc/poc2/`. The implementation and all experiment
code live in [`poc/poc3/`](../../poc/poc3/). There are no imports from `poc2` or `poc`.
Only this report was added outside that directory. Production code, existing tests,
PLAN, ADRs and configuration were not edited. The working tree already contained
the `poc/poc3/*` Ruff exemption and the v3 prompt before this work. No installation,
network access, TeX, movie encoding or commit was used.

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| K1: stack context is complete for the requested matrix | **CONFIRMED** | Both v2 animation tables, six composition cases and nine unsuspended cases expose the expected animation/container, or have no geometric hook to expose. |
| K2: temporary axis animations are indistinguishable from ordinary Manim | **FALSIFIED** | Detachment succeeds in every frame, but Create/Write/Uncreate differ by 606/1356/606 pixel channels against visible axes without a grid. |
| K3: foreign containers preserve native artist motion and new data | **CONFIRMED** | All 14 container cases pass; maximum rebuild error is 2.22089e-14, including native nonlinear handle conditioning. |
| K4: the six v2 fixes work on the specified workload | **CONFIRMED** | Cleanup and larger targets work; local placement/bounds agree to roundoff; bilinear p95 is 3.724 ms; both two-second affine motion cases retain one placement node. |
| K5: a callable is sampled once per rendered frame | **CONFIRMED** | Nine frames each sample once, repeated reads sample zero times, and frozen wait(2) samples/renders zero times. |
| K6: the copied v2 experiments remain valid with explicit changed expectations | **CONFIRMED** | All 132 copied regression cases pass with the changes enumerated below; the complete suite has 257 passing cases. |

Passing tests include assertions of measured incompatibilities. They do **not**
mean that every behavior is compatible with Manim. Results are JSON files under
[`poc/poc3/results/`](../../poc/poc3/results/); `python -m poc3.summary` prints the report inputs.

## Measurement boundaries and implementation

[`model.py`](../../poc/poc3/model.py) retains the v2 VGroup system, derived VMobject leaves,
weak artist registry, native animation interpolation, and protected invisible grid.
An artist remains one VMobject with its own control points. The grid now contains
only planar nodes: **4*N*N** points, hence **324** at N=9 and **4356** at N=33.
Three noncollinear planar probes determine its affine image. A synthetic unit normal
provides an invertible extension where possible; this does not recover arbitrary
off-plane scaling. Planar affine geometry, including a plane rotated in 3D, remains
exact. The frame returns no boundary anchors, so its rectangle cannot alter visible
pivots during a nonlinear deformation or during Wiggle's successive leaf updates.

[`context.py`](../../poc/poc3/context.py) walks `sys._getframe()` and compares **code objects**,
not guessed function names or family traversal order. It copies the relevant local
objects/values and releases the Python frame references. No Manim class is patched.
The interpolation counter changes individual animation instances for instrumentation,
as in v2; its wrapper is a deepcopy-safe partial so simulation cannot increment or
invoke the live animation through a shared closure.

D deep-copies the animation, including its mobject, calls setup/begin/finish/cleanup
against a small scene double, then compares the copied frame before/after with
`rtol=0, atol=1e-9`. It uses no animation-name list to decide permanence. That tolerance
also means a permanent displacement below 1e-9 is outside this experiment's resolution.
The flags remover/introducer are not used to shortcut D. An animation that does not
contain the frame, such as ordinary Flash or Circumscribe, needs no detachment hook.

E records a complete operation at the **last** native write: the second shift write,
or the third apply-points write. It ignores writes if the writer's actual family
contains the artist's frame. Otherwise it conjugates the exact vector or function
and pivot into local placement. VMobject.apply_function additionally supplies its
native handle-conditioning operation. Reads inside set_anchors_and_handles use a
scratch buffer; otherwise its later NumPy slice writes would corrupt a freshly
rebuilt canonical buffer.

F opens the transient buffer at Transform.begin's align_data call, before suspension.
It first flushes dirty source/target caches; freezing an unflushed rejected write
would preserve a double-shifted target. Removers do not install a candidate target.

Ordinary animation scenes use **320x180, 15 fps, 0.6 seconds**, nine actual rendered
frames. Standalone animations normally have 11 interpolation calls, shifted FadeOut
has 12 including cleanup, and composition roots have nine. The cost scenes use
**1920x1080, 60 fps, 10.1 seconds**, 606 rendered frames and 608 interpolation calls.
All animations use Scene.play; endpoint-only calls occur solely in D's classifier.
Pixels count differing array **channels**, not pixels or perceptual distances.
Geometric errors are maximum Euclidean control-point distances; v2's symmetric
nearest-control-point fallback is retained for unequal array sizes.

## K1 — actual animation and writer objects are available

`test_k1_animation_tables` plays all **26 axis** and **18 artist** table entries.
Each recorded suspension verifies that the animation's subject family contains the
leaf, and each recorded writer verifies that the container contains the leaf.
TransformFromCopy is observed on its actual animated target, not just its source.
The result contains **292 leaf suspension observations** and **1968 matched geometric
write observations**. No observed suspension is attributed to a missing animation.

`test_k1_compositions` covers AnimationGroup, Succession and LaggedStart, each with
Indicate(ax) and Rotate(ax, PI/6), after a dot animation:

| Composition | Suspension sequence on the frame | When | D behavior |
| --- | --- | --- | --- |
| AnimationGroup | AnimationGroup, then Indicate/Rotate | Before rendered frames | Keep separate entries; the inner decision overrides the outer decision while active. |
| LaggedStart | LaggedStart, then Indicate/Rotate | Before rendered frames | Same nested-entry behavior; no duplicate permanent placement is installed. |
| Succession | Indicate/Rotate only | During playback, at t=0.333333 s | Classify and snapshot the frame when this child actually begins. |

All six cases finish with **zero active suspension entries**. Temporary cases have
zero curve error; permanent cases have maximum error below 9e-16. The next shift
reattaches correctly. Resume removes the entry matching the actual finishing
animation, rather than treating repeated suspension as a single Boolean transaction.

Installed evidence: `composition.py::AnimationGroup.begin` (`:94-96`) suspends the
group and then begins its children; `composition.py::AnimationGroup.finish`
(`:103-108`) finishes children before resuming the group.
`composition.py::Succession.update_active_animation` (`:271-273`) sets up and begins
the next child. The leaf suspension originates from
`animation.py::Animation.begin` (`:213`), with that child as `self`.

`test_k1_no_suspension` runs MoveAlongPath, ShowIncreasingSubsets and PhaseFlow on
the axes, an artist, and a foreign VGroup: **nine cases**. They produce no suspension
hook. On an artist, MoveAlongPath reaches its own shift hook and PhaseFlow its own
apply_function hook. On a foreign group, E sees the real group writer; on axes it
sees a writer whose family contains the frame. ShowIncreasingSubsets changes style,
not geometry, so there is no geometric writer to classify. Native artist/group
endpoint errors are below 1e-9.

Installed evidence: `movement.py::MoveAlongPath.__init__` (`:192`) disables
suspension, and `movement.py::MoveAlongPath.interpolate_mobject` (`:201-202`) moves
the subject. `movement.py::PhaseFlow.__init__` (`:151`) also disables suspension;
`movement.py::PhaseFlow.interpolate_mobject` (`:165-170`) applies its Euler step.
`creation.py::ShowIncreasingSubsets.__init__` (`:511`) disables suspension and its
`interpolate_mobject` (`:527-535`) updates the revealed subset.

Measured stack read cost, excluding simulation, family membership and geometry:

| Read | Observations | Median us | p95 us | Maximum us |
| --- | ---: | ---: | ---: | ---: |
| Matched leaf suspension | 292 | 0.900 | 3.045 | 4.900 |
| Matched geometric writer | 1968 | 4.700 | 6.200 | 181.900 |

`test_k1_stack_microcost` separately measures a complete unsuccessful stack search:
writer median/p95 **4.108/4.535 us**, animation median/p95 **17.119/18.515 us**.
These differ because matching suspension normally exits close to its caller.
They are Python/pytest-stack measurements, not a universal constant.

**PLAN / ADR 0001 changes:** replace the claim that local buffers cannot identify
their caller with this version-specific stack contract. Include composition-owned
suspensions and children beginning during play. Do not equate an unsuspended leaf
with an unanimated leaf. Keep both semantic tests and the source contract when
updating Manim; this confirms the named matrix, not every possible custom animation.

## K2 — the binding rule works, full visual equivalence does not

The user rule is: **Curves follow only permanent changes to the axes.**

`test_k2_axis_detachment` covers all v2 axis entries plus Rotate(ax, TAU): **27 cases**.
The 16 temporary cases have **exactly zero** curve motion in every rendered frame.
The 11 permanent cases follow the current grid, with maximum independent interpolation
error **9.69461e-16**. A subsequent ax.shift(RIGHT) has maximum error **4.44089e-16**.
All classifier probes preserve the original frame, curve points, registry identities,
artist count and scene membership. `test_k2_simulation_reverse_group_registry`
also checks the artist-first group-copy order, without waiting for garbage collection.
Rebinding such a copy removes its temporary registration from the original system.
`test_k2_artist_in_same_animation_is_not_frozen` compares an included artist with a
native group and verifies that it receives the animation normally.

The native pixel control contains ordinary visible axis VMobjects and an ordinary
external curve, **without the hidden grid**. C1 is correct curve geometry in each
frame; C2 is reattachment; C3 is simulation isolation; C4 is maximum differing
channels against this native control. For permanent rows, the external native curve
stays still by construction: their C4 differences express the intended binding
policy, not failure to follow the frame.

| Case | Policy | C1 error | C2 error | C3 | C4 channels | Manim does the same? |
| --- | --- | ---: | ---: | --- | ---: | --- |
| Indicate | Stand | 0 | 0 | Pass | 0 | Yes |
| Wiggle | Stand | 0 | 0 | Pass | 0 | Yes |
| ApplyWave | Stand | 0 | 0 | Pass | 0 | Yes |
| Circumscribe | Stand | 0 | 0 | Pass | 0 | Yes |
| Flash | Stand | 0 | 0 | Pass | 0 | Yes |
| FadeIn(shift=UP) | Stand | 0 | 0 | Pass | 0 | Yes |
| FadeOut(shift=DOWN) | Stand | 0 | 0 | Pass | 0 | Yes |
| FadeIn | Stand | 0 | 0 | Pass | 0 | Yes |
| FadeOut | Stand | 0 | 0 | Pass | 0 | Yes |
| GrowFromCenter | Stand | 0 | 0 | Pass | 0 | Yes |
| Create | Stand | 0 | 0 | Pass | 606 | No: axis drawing timing |
| Write | Stand | 0 | 0 | Pass | 1356 | No: axis drawing timing |
| Uncreate | Stand | 0 | 0 | Pass | 606 | No: axis drawing timing and protected removal buffer |
| DrawBorderThenFill | Stand | 0 | 0 | Pass | 0 | Yes |
| ShowPassingFlash | Stand | 0 | 0 | Pass | 0 | Yes |
| Rotate(TAU) | Stand | 0 | 0 | Pass | 0 | Yes |
| Rotate(PI/6) | Follow | 4.58e-16 | 0 | Pass | 1647 | No: intended binding |
| ScaleInPlace | Follow | 1.11e-16 | 0 | Pass | 1257 | No: intended binding |
| animate.shift(RIGHT).scale(0.5) | Follow | 8.95e-16 | 0 | Pass | 1527 | No: intended binding |
| MoveToTarget | Follow | 4.44e-16 | 0 | Pass | 1656 | No: intended binding |
| Transform to shifted copy | Follow | 4.44e-16 | 0 | Pass | 1656 | No: intended binding |
| ApplyMatrix | Follow | 5.55e-16 | 0 | Pass | 1392 | No: intended binding |
| ApplyPointwiseFunction | Follow | 9.69e-16 | 4.44e-16 | Pass | 3132 | No: binding and axis handles |
| Homotopy ending away from start | Follow | 9.49e-16 | 4.44e-16 | Pass | 1542 | No: intended binding |
| Restore to another state | Follow | 8.88e-16 | 0 | Pass | 1656 | No: intended binding |
| MoveAlongPath | Follow | 4.44e-16 | 0 | Pass | 1650 | No: intended binding |
| animate.rotate(PI/6) | Follow | 6.28e-16 | 0 | Pass | 1644 | No: intended binding |

The temporary pixel failures are reproducible negative assertions, not ignored
failures. The hidden frame contributes an extra family leaf. Native lag calculations
therefore allocate different intervals to the visible leaves. Maximum axis
control-point discrepancies are **3.82357** for Create/Uncreate and **2.13333** for
Write. Returning no frame boundary anchors fixes Wiggle pivots but does not remove
this family member from animation scheduling.

A separate permanent-path finding is visible in the recorded `axis_error`:
ApplyPointwiseFunction differs from the native visible axis control by **1.42309**.
Rebuilding axis control points through the grid is different from applying Manim's
handle preconditioning to a sparse axis path. E fixes this operation on a foreign
artist; it does not turn frame-derived axis geometry into native analytic handles.
The other permanent axis errors are below 1e-13.

Installed evidence: `animation.py::Animation.get_all_families_zipped` (`:284-286`)
includes point-bearing family members; `animation.py::Animation.get_sub_alpha`
(`:384-391`) uses their count and index for lagging.
`creation.py::ShowPartial.interpolate_submobject` (`:132-134`) applies partial
drawing, while `creation.py::DrawBorderThenFill.interpolate_submobject`
(`:283-288`) also interpolates styles/points. The frame still ignores partial drawing.
`vectorized_mobject.py::VMobject.apply_function` (`:1226-1228`) brackets the map
with handle scaling. `indication.py::Wiggle.interpolate_submobject` (`:559-567`)
resets points in place and repeatedly queries its parent's pivot.

The **24 actual frame classifier invocations** in the standalone matrix cost
median **6.5659 ms**, p95 **10.2610 ms**, maximum **14.4666 ms** per play. Flash,
Circumscribe and unsuspended MoveAlongPath have no such frame invocation. Composition
calls can cost more because a child copy includes active composition bookkeeping:
AnimationGroup(Indicate) records **38.9635 ms** total for its two classifiers;
LaggedStart(Rotate) records **40.9906 ms**. Succession's Indicate classifier costs
**5.7016 ms during playback**, not just before it. These are setup costs, outside the
rebuild timer. Arbitrary callbacks or callables with external side effects are not
sandboxed by deepcopy; isolation is established for the tested standard animations.

**PLAN / ADR 0001 changes:** adopt the one-sentence permanence rule, including the
explicit Rotate(TAU) consequence. Record classifier cost and during-play starts.
Do not claim complete ordinary-Manim rendering compatibility: a hidden family leaf
changes partial-animation timing, and sparse derived axis handles need a separate
solution. Neither was patched by fitting leaf deltas or guessing family-call order.

## K3 — foreign writers retain artist placement

`test_k3_foreign_containers` compares immediate control points with ordinary Manim,
then changes range **[-3,3] -> [-2.5,2.5]** and data amplitude **1 -> 1.6**.
The independent rebuilt controls apply the same native operation with the original
pivot/translation to the changed data. `test_k3_animated_foreign_container` compares
every frame of a group animate.shift(UP) and a default Rotate(group), then rebuilds
with the changed range. Both use 11 interpolations and nine frames.

C1 is immediate native geometry; C2 is transformed new data after rebuilding;
C3 is one application of the operation, including both curves where present.
Errors below include both artists in the arrange/two-system rows.

| Case | C1 error | C2 error | C3 | Manim does the same? |
| --- | ---: | ---: | --- | --- |
| VGroup(curve,dot).shift | 0 | 1.33e-15 | Pass | Yes |
| rotate | 4.97e-16 | 1.49e-15 | Pass | Yes |
| scale | 2.22e-16 | 8.88e-16 | Pass | Yes |
| apply_matrix | 0 | 1.33e-15 | Pass | Yes |
| apply_function(wave) | 0 | 2.22e-14 | Pass | Yes, handles included |
| move_to | 0 | 1.33e-15 | Pass | Yes |
| next_to | 0 | 8.88e-16 | Pass | Yes |
| to_corner | 0 | 8.88e-16 | Pass | Yes |
| VGroup(curve1,curve2).arrange(DOWN) | 8.88e-16 | 1.88e-15 | Pass | Yes |
| Group(curve,dot).shift | 0 | 1.33e-15 | Pass | Yes |
| VGroup(VGroup(ax),curve).shift | 0 | 1.33e-15 | Pass | Yes |
| VGroup(ax,curve,other-system-curve).shift | 0 | 1.33e-15 | Pass | Yes |
| VGroup(curve,dot).animate.shift(UP) | 0 | 1.33e-15 | Pass; frame error 0 | Yes |
| Rotate(VGroup(curve,dot)) | 2.48e-16 | 1.33e-15 | Pass; frame error 4.97e-16 | Yes |

The nested-system artist has **zero** own placement nodes: its writer moves its
frame. In the mixed-system group, that is true only for the first curve; `other`
receives its own placement because its frame is absent. Ordinary foreign affine
cases have one collapsed node. The nonlinear wave retains one callable operation.
The previous v1 handle failure is now **zero immediate error**, rather than 0.864.
Result names use `k3_static_*` and `k3_animation_*` to avoid Windows' case-insensitive
collision between `rotate` and `Rotate`.

`test_k3_raw_write_keeps_v2_policy` verifies the required fallback: manual
curve.points += UP is discarded on the next read. E does not infer an operation
from an array delta when no recognized writer frame exists.

Installed evidence: `mobject.py::Mobject.shift` (`:1282-1283`) writes twice per
family leaf; `mobject.py::Mobject.apply_points_function_about_point`
(`:1582-1584`) writes three times with `func` and `about_point` still in scope.
`vectorized_mobject.py::VMobject.apply_function` (`:1226-1228`) supplies the native
handle conditioning. `vectorized_mobject.py::VMobject.set_anchors_and_handles`
(`:844`, `:850-852`) first assigns an empty array, then fills four slices; treating
only the assignment as the operation would miss those writes.

**PLAN / ADR 0001 changes:** replace blanket rejection of foreign container writes
with membership in the **specific writer's** family. Keep raw NumPy fallback
explicit. Store artist placement in frame-local space and retain the exact native
handle operation for apply_function. D11's weak attachment and ordinary explicit
parenting remain distinct; no family-traversal-order transaction is needed.

## K4 — six pre-fix failures and their measured fixes

[`baseline_model.py`](../../poc/poc3/baseline_model.py) is the independent, frozen copy of
the v2 model. `python -m poc3.baseline` runs the six new regression tests against
it, catches their **six expected failures**, and records the original cost workload.
It substitutes only this experiment's module references, never Manim classes.

| Fix / test | Before | After |
| --- | --- | --- |
| `test_k4_fadeout_cleanup` | 1.0 scene-unit endpoint error | 0, including native cleanup |
| `test_k4_larger_target` | ValueError: shapes (36,3) and (196,3), before any rendered frame | 196 points, error 0, 11 interpolations and nine frames; target accepted |
| `test_k4_local_placement` | 1.41421356 error after shift(UP), then axis rotation PI/2 | 2.22045e-16 |
| `test_k4_cached_weights`, `test_g6_600_frame_cost[True]` | No sample-weight cache; p95 4.7991 ms | Zero weight rebuilds for ten frame-only changes; p95 3.7240 ms |
| `test_k4_no_offplane_probe` | Center error 0.5; rotation-pivot error 0.19866933 | Center 0; pivot 7.54210e-18 |
| `test_k4_placement_growth` | MoveAlongPath: 32 nodes; PhaseFlow: 31 nodes and error 34.0640 | One node each after two seconds; errors 1.99840e-15 / 5.58925e-13 |

The shifted FadeOut fix is target rejection for removers, not special restoration
based on point deltas. Installed evidence:
`fading.py::FadeOut.clean_up_from_scene` (`:190-192`) calls interpolate(0) **after**
ordinary cleanup; `animation.py::Animation.finish` (`:225-227`) resumes first.
`transform.py::Transform.begin` (`:211-212`) aligns **before** calling base begin;
`vectorized_mobject.py::VMobject.align_points` (`:1883-1894`) writes expanded arrays.
F therefore needs an earlier transaction boundary than suspension.

Placement runs after range mapping and before the live frame. A scene operation G
is retained as F_old^-1 o G o F_old in local space. For affine frames this is a
matrix, and adjacent matrices multiply into one node. The PhaseFlow test uses
the affine field **0.1*p + UP**; both two-second tests render 30 frames and have
32 interpolation calls. The result does not claim bounded storage for genuinely
nonlinear flows: nonlinear operations are composition barriers.

`test_k4_nonaffine_local_conjugation` quantifies the nonlinear limit at N=33, using
the wave y+=0.3*sin(2*x), own shift(RIGHT), then an axis rotation. Immediate scene
error is **1.98603e-15**, and later rotation error **3.99798e-15** against the same
initial grid-derived native curve. But the retained local coordinates differ from
**analytic** wave conjugation by **0.00764780** inside the grid, and **0.150995**
including the part shifted outside x=3. These are **1.03245 / 20.3843 px at 1080p**.
The larger number includes boundary-cell extrapolation; native-looking immediate
motion does not make nonlinear local coordinates exact.

Affine detection for artist operations evaluates the supplied function on eight
probe points, rather than fitting deltas between leaves. This is explicitly a PoC
shortcut: finite probes cannot certify an arbitrary callable's global affinity.
The tested affine operations collapse correctly; an adversarial callable could
alias those probes. That must not become an unqualified production guarantee.

The bilinear path caches a four-entry sparse interpolation row per local control
point. A rebuild with changed samples prepares its indices and weights once;
repeated reads or frame-only motion reuse them. A moving data parameter still
requires new weights for the changed coordinates. Fixed sampling x coordinates
and cubic corner construction are reused when polling a callable;
`test_corner_buffer_matches_native` verifies exact native corner-buffer equality.

| F-1001 path | Dirty/rendered frames | Interpolations | Median rebuild ms | p95 rebuild ms | p95 comparisons ms | 4 ms |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Affine | 606 | 608 | 2.2897 | 2.9065 | 0.3421 | Pass |
| Forced bilinear, N=33 | 606 | 608 | 2.7520 | 3.7240 | 0.3768 | Pass |

The scene contains four 2000-sample artists, ten ticks, two axis lines:
**16 derived leaves, 32032 derived control points**. Median comparison calls per
frame remain 60; four callable sources are sampled and four sample-weight matrices
are prepared per dirty frame. Comparison/rebuild timers overlap and must not be
added. Rasterization, encoding and D's classifier are outside the rebuild timer.
This is still a PoC lower bound, without production tick layout, clipping or labels.
The historical v1 1.5x baseline is not certified by these changed workloads.

`test_g6_copy_and_comparison` records group copy median/p95 **0.7792/1.5893 ms**.
Clean grid comparisons average **1.286 / 1.702 / 2.704 / 7.355 us** for
N=9/17/33/65. Its inherited `empty` updater label now means **active callable
polling**: manual group.update outside Scene.play costs 1.991 ms versus 0.00237 ms
without updaters, including eager source/rebuild work at that explicit boundary.
It is no longer a measurement of just an empty callback. During play, polling
only dirties the source and the camera-triggered rebuild does the sampling.

The affine normal extension is conventional once the off-plane probe is removed;
tests of inverse roundtrip still pass, but do not prove native off-plane scaling.
`vectorized_mobject.py::VMobject.get_points_defining_boundary` (`:1793-1797`)
uses family anchors; excluding grid anchors is why visible pivots agree.
`movement.py::PhaseFlow.interpolate_mobject` (`:165-170`) explains the repeated
operations that now collapse instead of retaining one affine node per step.

**PLAN / ADR 0001 changes:** move placement to local space, state nonlinear inverse
and extrapolation error, remove the off-plane representation requirement for planar
0.1, and specify visible bounds independently of hidden storage. Require affine
composition collapse and cached sample weights. Preserve the absolute performance
gate and a separately justified baseline; neither timings nor finite affinity probes
are proofs for arbitrary workloads/callables.

## K5 — callable sampling is driven by synchronization, not reads

`test_k5_callable_once_per_frame` uses the literal binding
ax.plot(lambda x: a.get_value()*np.sin(x)), then animates a from 1 to 2, without
always_redraw. Every rendered frame matches the current a with maximum error
**1.35064e-15**. Sampling passes per frame are **[1,1,1,1,1,1,1,1,1]**.
Twenty repeated center/points reads in each observation produce **zero** further
passes. One pass evaluates the vector of 41 x samples; it is not 41 Python calls.

There is one initial sampling pass and one additional **unrendered endpoint** pass
after play finishes. That endpoint refresh prevents a pending dirty callable from
being evaluated by the next frozen-wait capture. Subsequent wait(2) produces
**zero sampling calls and zero ProbeRenderer.render calls**.

The no-dt synchronization updater marks the source dirty once per Scene.update_to_time
token. It also flushes the final explicit update boundary. Dirtiness is consumed by
source sampling, not by every points getter. Copies share the binding callable;
accepted targets adopt the callable binding, not a permanently fixed array identity.

Installed evidence: `scene.py::Scene.update_to_time` (`:1704-1708`) interpolates
animations before updating scene mobjects. `scene.py::Scene.play_internal`
(`:1390-1393`) finishes/cleans animations and then updates mobjects at dt=0.
`scene.py::Scene.should_update_mobjects` (`:435-445`) distinguishes time-based
updaters for Wait; `cairo_renderer.py::CairoRenderer.play` (`:112-118`) takes the
frozen-frame branch instead of playing the frame loop.

**PLAN / ADR 0001 changes:** implement D8's always-dirty callable at the synchronization
boundary, with a frame token and endpoint synchronization. Do not make every lazy
read invalidate the callable. Preserve the no-dt updater choice so ordinary frozen
waits do not start sampling/rendering loops.

## K6 — copied v2 regression and changed expectations

The five copied test files contain **132 cases**, all passing. The complete suite
contains **257 cases**, passing in **35.44 s** in the recorded full run. Ruff check
and format check also pass. No copied test was deleted or skipped.

These are the changed assertions/oracles and their reasons:

| Copied experiment | Changed expectation | Reason |
| --- | --- | --- |
| `test_g2_axis_animation` | Derive from frozen frame for a temporary animation, live frame otherwise. | D; numerically changes Indicate, Wiggle, ApplyWave, shifted FadeIn/FadeOut and GrowFromCenter. Other temporary rows already had a stationary frame. |
| `test_g3_artist_animation[False-FadeOutShift]` | Native endpoint agreement now passes, rather than requiring a 1-unit failure. | F rejects the remover target; cleanup leaves original geometry. |
| `test_g3_artist_animation[True-FadeOutShift]` | Changed data has no DOWN offset. | Same F fix, while keeping live data. |
| `test_g3_target_with_more_points` | Require successful playback and native endpoint agreement, rather than an exception. | F makes pre-suspension alignment transient. |
| `test_g4_tracker_dot_parenting_and_simultaneous` | The foreign curve moves UP once and equals the native group; distance from its initial curve is now 1. | E captures a writer without the frame. Parenting/simultaneous-motion observations remain in the test. |
| `test_g4_invisible_marker_bounds` | Center error becomes 0, rotation error becomes roundoff. | Removal of the probe and exclusion of frame boundary anchors. |
| Independent affine oracles in G1/G2 | Solve three planar probes instead of four volumetric probes. | The representation has no off-plane sample. All original planar geometry accuracy requirements remain. |

Other recorded changes are deliberate consequences of the new experiment: N=9 has
324 rather than 328 frame points; active source polling replaces the old empty
updater's cost; callable sampling can replace the adopted source array, so the
recorded array-identity flag is no longer proof of target adoption. Binding and
geometry are the evidence. Copy registration is also cleaned up immediately when
an artist-first copy is rebound to the copied system.

Existing counterexamples remain tested: finite-grid aliasing; protected Uncreate
buffers; simultaneous axis/artist double displacement; native data-channel family
alignment failure; and the same-count tick-identity failure. K6 confirms preservation
of the experiments, not reversal of their negative verdicts.

Installed evidence: `transform.py::Transform.begin` (`:211`) and
`fading.py::FadeOut.clean_up_from_scene` (`:190-192`) account for the changed
lifecycle assertions. `mobject.py::Mobject.shift` (`:1282-1283`) accounts for the
foreign-container assertion. `mobject.py::Mobject.add_n_more_submobjects`
(`:3092-3098`) still aligns families by index, without frame/tick identities.

**PLAN / ADR 0001 changes:** replace the six obsolete failure expectations above,
but keep the surviving counterexamples and the distinction between experimental
regression success and user-facing compatibility. Native mixed data/geometry
chaining still needs a structural solution beyond D/E/F.

## Updated differences from ordinary Manim

| v2 difference | v3 status / user-visible result |
| --- | --- |
| Curves follow temporary axis indications/fades | **Removed** for the named cases: curve motion is exactly zero. |
| Curves follow permanent axis changes | **Retained intentional binding**: an independent ordinary curve would stay still. Rotate(TAU) is explicitly classified temporary. |
| Simultaneous independent axis/artist moves add twice | **Retained**: the curve moves two units when both channels request one unit; copied Manim code can still differ. |
| Foreign containers leave a curve behind | **Removed** on the K3 matrix, including two different systems and animated foreign groups. |
| Shifted FadeOut leaves an offset on re-add | **Removed**: native cleanup state and changed data survive. |
| Uncreate(curve) re-adds a full curve | **Retained rebuild policy**: native Manim leaves a degenerate buffer. |
| Uncreate(ax) keeps the grid usable | **Retained protection policy**: raw frame geometry does not become native degenerate geometry. |
| Larger Transform targets fail before play | **Removed** for 36 -> 196 points; F opens the buffer before alignment. |
| Finite grid approximation, folds, discontinuities, smooth aliasing | **Retained**: stack context supplies provenance, not missing geometric information. |
| Nonlinear inverse branches and singular collapsed frames | **Retained**: p2c remains approximate/nonunique or raises at a singular frame. |
| Own placement remains in scene coordinates | **Removed for affine frames**; nonlinear local conjugation is approximate, measured above. |
| Off-plane marker changes centers and pivots | **Removed**; off-plane geometry now uses a conventional normal extension, with a narrower guarantee. |
| Data/geometry override chains and tick/family semantics | **Retained**: the two v2 G7 counterexamples still pass as negative experiments. |
| Raw/in-place NumPy edits lack operation provenance | **Retained v2 fallback**: assignments are rejected; pure slice edits can remain in the cache until another rebuild. |
| Additional hidden leaf changes drawing timing | **Newly measured**: Create/Write/Uncreate axis pixels differ from a frame-free native hierarchy. |
| Derived sparse axis handles differ under ApplyPointwiseFunction | **Newly measured**: 1.42309 axis control-point error; exact foreign-artist handle capture does not fix frame-derived axes. |
| Artist-function affinity recognition uses finite probes | **New PoC shortcut**: arbitrary callables can alias these probes; one-node affine-flow results do not establish universal bounded storage. |

Weak registration/redraw, memo-aware copies, split paths, dot updaters and ordinary
Scene.add splicing continue to work. D/E/F remove the two targeted context gaps,
but do not establish unrestricted ordinary-Manim compatibility.

## Stack and source dependency contract

These are **all Manim frames read by the mechanism**, with the symbol before its
line. The first seven entries identify animation lifecycle frames; shared inherited
implementations also cover LaggedStart and Transform subclasses.

| Stack symbol | Relevant lines | Required locals / purpose |
| --- | --- | --- |
| `animation.py::Animation.begin` | `:213` | `self`: actual animation when suspending. |
| `transform.py::Transform.begin` | `:211` | `self`: early alignment transaction and remover decision. |
| `composition.py::AnimationGroup.begin` | `:94-96` | `self`: outer suspension, before child begins. |
| `composition.py::Succession.begin` | `:244` | `self`: recognized begin implementation; delegates rather than suspending the group. |
| `animation.py::Animation.finish` | `:225-227` | `self`: remove this animation's frozen-frame entry. |
| `composition.py::AnimationGroup.finish` | `:103-108` | `self`: remove the outer entry after children finish. |
| `composition.py::Succession.finish` | `:246-248` | `self`: recognized finishing composition; active children resume through their own finish. |
| `mobject.py::Mobject.shift` | `:1282-1283` | `self`, `total_vector`; commit E only at line 1283. |
| `mobject.py::Mobject.apply_points_function_about_point` | `:1582-1584` | `self`, `func`, copied `about_point`; commit E only at line 1584. |
| `vectorized_mobject.py::VMobject.apply_function` | `:1226-1228` | `self`, `function`; retain exact handle conditioning and its style flags. |
| `vectorized_mobject.py::VMobject.set_anchors_and_handles` | `:844`, `:850-852` | Immediate caller code: expose scratch during native slice construction. |
| `scene.py::Scene.update_to_time` | `:1700-1708` | `self`, `t`: callable frame token, also observes during-play child starts. |
| `scene.py::Scene.play_internal` | `:1390-1393` | `self`, renderer play count: distinguish endpoint synchronization from rendered frames. |

There are seven animation-lifecycle entries in the table; the remaining six cover
writer, handle and polling contexts. No frame named get_family is inspected.
Ordinary get_family is used only for actual object membership.

`test_k1_cited_manim_symbol` guards **54 cited/dependent symbols** against
[`manim_contract.json`](../../poc/poc3/manim_contract.json), checking Manim's version,
each symbol's first source line, and SHA-256 of its complete inspected source.
It covers the table and the creation, cleanup, family, renderer and updater symbols
cited throughout this report. [`evidence.py`](../../poc/poc3/evidence.py) writes the exact
installed source with symbol headings before numbered lines to
[`manim_sources.txt`](../../poc/poc3/results/manim_sources.txt).

Updating the frozen contract is an explicit review step (`--freeze`), never part
of pytest. A version update must also rerun the behavioral tests: an unchanged
signature or stack frame alone does not establish unchanged semantics.

## Review notes

Maintainer rerun outside the Codex sandbox: **257 passed in 35.86 s**, both Ruff checks
pass. Found by reading `poc/poc3/context.py` and `poc/poc3/model.py`:

- **The last-write test hard-codes line numbers.** `writer_context` treats a write as
  the end of an operation when `f_lineno == 1283` or `== 1584`. The contract test
  catches a source change, but production should derive these lines from the cited
  function's source when the module is imported, rather than embed them.
- **Affine recognition does not need probes.** The writer frame of
  `apply_points_function_about_point` has its own caller on the stack —
  `Mobject.rotate`, `Mobject.scale`, `Mobject.stretch`, `Mobject.apply_matrix` — whose
  locals give the exact matrix. Only `apply_function` and other callers of an
  arbitrary function remain non-affine nodes. That replaces the eight-probe shortcut
  with a fact read from the stack, the same kind of evidence D, E and F already use.
- **Simulation runs user callbacks.** `Frame.simulate` deep-copies the animation,
  but a callable is not copied, so `UpdateFromFunc`, `UpdateFromAlphaFunc` or a
  custom `interpolate_mobject` that writes to a tracker or any outside object performs
  that side effect once more, before the real playback. The tested matrix holds only
  pure animations. Production has to decide which animations may be simulated and
  what happens to the rest — for example, never simulate an animation whose behaviour
  is a user callback, and treat it as permanent.
- **The Create, Write and Uncreate pixel differences are measured against our own
  frame-free hierarchy, not Manim's `Axes`.** The hidden leaf takes one lag slot in
  `Animation.get_sub_alpha`. Manim's `Axes` has a different family anyway, so no user
  sees this as a difference from Manim. It is a scheduling cost: one empty slot out
  of the family size.

## Reproduction

Run in repository-root PowerShell. Media directories use ordinary Path.mkdir;
no tempfile helpers, tmp_path or render markers are involved. Result files are
overwritten by the corresponding experiments. For the exact tables after a full
run, print the summary rather than mixing result directories from different runs.

```powershell
# All experiments, including all 132 copied regression cases and source guards.
.venv\Scripts\python.exe -m pytest poc/poc3 -p no:cacheprovider

# Six failures before fixes, plus the original 606-frame bilinear workload.
.venv\Scripts\python.exe -m poc3.baseline

# K1: both complete animation tables, compositions, unsuspended cases, stack costs.
.venv\Scripts\python.exe -m pytest poc/poc3/test_context.py -p no:cacheprovider
# K2: every-frame detachment, native full-scene pixels, isolation and reattachment.
.venv\Scripts\python.exe -m pytest poc/poc3/test_detachment.py -p no:cacheprovider
# K3: every foreign-container case, new data/range, animated groups and raw fallback.
.venv\Scripts\python.exe -m pytest poc/poc3/test_containers.py -p no:cacheprovider
# K4: functional fixes, nonlinear conjugation, cached weights and actual 1080p60 cost.
.venv\Scripts\python.exe -m pytest poc/poc3/test_fixes.py poc/poc3/test_cost.py -p no:cacheprovider
# K5: callable sampling, repeated reads and frozen wait.
.venv\Scripts\python.exe -m pytest poc/poc3/test_callable.py -p no:cacheprovider
# K6: exactly the copied v2 regression files (132 cases).
.venv\Scripts\python.exe -m pytest poc/poc3/test_geometry.py poc/poc3/test_animations.py poc/poc3/test_idioms.py poc/poc3/test_cost.py poc/poc3/test_data_channel.py -p no:cacheprovider -k "not corner_buffer"

# Installed implementation and upgrade guard; do not freeze automatically on upgrade.
.venv\Scripts\python.exe -m poc3.evidence
.venv\Scripts\python.exe -m pytest poc/poc3/test_manim_contract.py -p no:cacheprovider
.venv\Scripts\python.exe -m poc3.summary
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```
