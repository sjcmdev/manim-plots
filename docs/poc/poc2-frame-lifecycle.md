# Frame and leaf-lifecycle proof of concept (v2)

Measured on 2026-10-24: **Manim 0.21.0**, Cairo, Python 3.13.2, NumPy 2.5.2,
Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1, 24 logical CPUs.
This is a disposable experiment, not a library implementation or API proposal.
No network, installation, TeX, or movie encoding was used; nothing was committed.

This report evaluates [`poc/poc2/model.py`](../../poc/poc2/model.py), with
[`scene.py`](../../poc/poc2/scene.py), `test_geometry.py`, `test_animations.py`,
`test_idioms.py`, `test_cost.py`, and `test_data_channel.py`. Each artist is **one
VMobject with its own points**, including multiple subpaths for a split curve.

A superseded run of the same task, started from an earlier draft of the prompt with a
point-free `Artist(VGroup)`, wrote into `poc/poc2/` at the same time. Its files were moved
out of the repository after both runs finished; nothing below depends on them.

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| G1: frame captures every transformation | **FALSIFIED** | The 48 named operation/wrapper cases work to measured precision, but `test_g1_smooth_aliasing_counterexample` loses a smooth transform by 0.3 scene units (40.5 px at 1080p). |
| G2: system animations meet all four criteria | **FALSIFIED** | All 26 preserve frame structure/invisibility and frame-following; protected Uncreate geometry contradicts the native degenerate endpoint. |
| G3: artist lifecycle preserves native states | **FALSIFIED** | Geometry chains and Circle adoption work, but shifted FadeOut leaves a 1-unit offset, Uncreate rebuilds full geometry, and a larger target fails before playback. |
| G4: Manim idioms remain interchangeable | **FALSIFIED** | Redraw, copies and paths work; simultaneous system/artist motion doubles displacement, and a group without the system drops curve motion. |
| G5: empty updater fixes Cairo freezing | **CONFIRMED** | Both freeze cases have differing middle-frame channels without updaters and exactly zero with them. |
| G6: rebuild fits 4 ms in both paths | **FALSIFIED** | Affine passes; forced bilinear N=33 exceeds 4 ms at p95 over 606 dirty 1080p60 frames. |
| G7.1: live data override | **CONFIRMED** | Nine correct frames and endpoint; both mixed chains raise the exact native override exception. |
| G7.2: local native interpolation overrides suffice | **FALSIFIED** | Family alignment duplicates the frame and pairs it with an axis leaf; playback raises before the first frame. |

## Experiment and measurement boundaries

System is a VGroup with a hidden frame, two derived axis lines and ten ticks.
Artists belong to a weak registry, not its submobject list, except in the explicit
ordinary-add test. Each logical grid node is encoded as **four coincident control
points**, one degenerate cubic: `4*(N*N+1)` stored points. A raw N*N+1 array breaks
the anchor pairs in `vectorized_mobject.py::VMobject.get_anchors` (`:1789-1791`).
Coincident handles also make native nonlinear handle preconditioning harmless,
including the parent's family loop in
`vectorized_mobject.py::VMobject.scale_handle_to_anchor_distances` (`:1251-1273`).
No delta fitting between derived leaves is used.

The frame ignores partial drawing and clamps fill/stroke/background stroke and
interpolated styles to invisibility. It compares its whole array with a saved copy
on reads. After a detected change, a four-probe affine solve is verified against
**all** stored points. The affine path supports 3D/extrapolation; bilinear mapping
extrapolates the boundary cell and extends z linearly using the off-plane probe.
General nonlinear 3D geometry cannot be represented by this planar grid and probe.

Derived leaves have no shadow. Clean getters return the cache itself. During
suspension writes remain transient; otherwise assignments dirty the buffer and
the next read derives it. Artist-owned geometric hooks retain functions after
the frame outside suspension and modify the buffer during suspension, without
geometry override_animate. Target state is copied **after** align_data returns;
resume accepts it on equal shapes and `allclose(rtol=0,atol=1e-10)`, then rebuilds.
This accommodates endpoint roundoff, not semantic target identity. become adopts
state explicitly. Copies share immutable sources/trackers, use memo to select the
copied system when present, and rebuild weak registration without copying every
otherwise registered artist.

Completed animations use actual Scene.play, Cairo, 320x180, 15 fps, 0.6 seconds,
no cache/movie: **nine rendered frames**, normally 11 interpolate calls, 12 with
fade cleanup, or nine for composition roots. Distinct alphas exceed one. Default
rate functions remain except explicitly linear parameter drivers. Two begin-time
failures necessarily have one attempted interpolation and no frames; native
controls complete 11 calls and nine frames. Endpoint-only playback is not used.

Errors are maximum Euclidean scene distances between corresponding control points
or independent dense samples. Unequal point counts use a symmetric maximum
nearest-control-point distance and record the count mismatch separately; this is
not a continuous curve Hausdorff certificate. Pixel differences count array
**channels**. Results are under [`poc/poc2/results/`](../../poc/poc2/results/).

## G1 — named operations succeed; finite-grid aliasing disproves universality

`test_g1_native_operations` covers all 12 requested operations in all four wrappers,
including both system/curve orders and a dot. Rotation uses a 3D axis. After each
operation, changing range (-3,3) to (-2.5,2.5) forces rebuilding. An ordinary native
VMobject hierarchy with identical initial geometry supplies independent affine
truth; nonlinear functions are evaluated directly on dense source points, without
using the frame interpolator. Neither container order retains double motion.


Maximum affine error **1.83103e-15**; maximum native dot error **0**.


`test_frame_style_and_inplace_detection` verifies cache identity, detects an
in-place frame write, and gives zero differing channels for set_opacity(1),
set_color(RED), set_stroke(width=8), with versus without the frame.

`test_g1_grid_error_inverse_cost` evaluates 10,001 independent points
`(x,sin(x),0)`, x in [-2.9,2.9]. Every grid node also matches its independently
evaluated function within 1e-9. Functions: wave `y+=0.3*sin(2*x)`, complex `z**2`,
strong bend `y+=0.8*x**2`, jump `y+=(-1 if x<0.13 else 1)`. Rebuild is the median
of 30 full rebuilds of one 2,000-sample artist (7,996 control points). Pixel
conversion is **135 px/scene unit** at 1080p, frame height 8; no subjective
invisibility threshold or camera-clipping claim is used.


| N | Function | Max scene error | 1080p px | Rebuild median ms | p2c / 51 points ms | Inverse coordinate error |
| --- | --- | --- | --- | --- | --- | --- |
| 9 | wave | 0.069515 | 9.38453 | 0.82195 | 2.3467 | 2.22114e-15 |
| 9 | square | 0.140523 | 18.9706 | 0.8144 | 27.9148 | 5.8197 |
| 9 | bend | 0.1125 | 15.1875 | 0.94835 | 1.4516 | 4.39648e-15 |
| 9 | jump | 1.652 | 223.02 | 1.22435 | 2.1769 | 2.22062e-15 |
| 17 | wave | 0.0205748 | 2.7776 | 0.9477 | 1.4124 | 1.33487e-15 |
| 17 | square | 0.0336734 | 4.5459 | 0.84585 | 17.5098 | 5.8197 |
| 17 | bend | 0.028125 | 3.79687 | 0.8919 | 1.976 | 2.77556e-15 |
| 17 | jump | 1.304 | 176.04 | 0.8573 | 1.436 | 1.35064e-15 |
| 33 | wave | 0.00525638 | 0.709611 | 1.3055 | 2.1641 | 2.27596e-15 |
| 33 | square | 0.0087629 | 1.18299 | 0.88185 | 20.5156 | 5.8197 |
| 33 | bend | 0.00703125 | 0.949219 | 0.83085 | 1.4497 | 2.59184e-15 |
| 33 | jump | 1.38581 | 187.085 | 0.92535 | 2.0182 | 2.22062e-15 |
| 65 | wave | 0.00131704 | 0.177801 | 0.84825 | 1.476 | 2.25914e-15 |
| 65 | square | 0.00217997 | 0.294297 | 0.9183 | 17.4217 | 5.8197 |
| 65 | bend | 0.00175781 | 0.237305 | 0.8746 | 1.7538 | 3.69055e-15 |
| 65 | jump | 1.216 | 164.16 | 0.88015 | 1.4854 | 2.22062e-15 |

Affine inverse probes include (8,-7,3), outside the rectangle: roundtrip error
**3.33433e-17**, **0.0906 ms** for two probes including forward mapping.
Newton uses finite differences and at most 20 steps. Wave/bend/jump roundtrips
are near roundoff. Complex square selects another branch for some points:
coordinate error about **5.82**, despite small forward residuals recorded in JSON.
There is no unique global inverse for that map. The jump becomes a ramp within
one cell; its max error does not reliably shrink as N doubles. Inverting the ramp
does not restore the original discontinuity.

At N=33, `test_g1_smooth_aliasing_counterexample` uses the smooth function
`y+=0.3*sin(16*pi*x/3)`, zero at every grid x node. The frame is classified affine,
but dense geometry error is **0.299999**, or
**40.4999 px**. Every finite grid admits such a function.
Thus G1 is FALSIFIED as an unrestricted claim, despite the named-case successes.


Installed evidence: `mobject.py::Mobject.shift` (`:1282-1283`) writes family
leaves; `mobject.py::Mobject.apply_points_function_about_point` (`:1581-1584`)
performs three writes per leaf; `vectorized_mobject.py::VMobject.apply_function`
(`:1226-1228`) preconditions handles around the map. These are native frame writes.

**PLAN / ADR 0001 changes:** any sampled frame replaces system placement only with
explicit approximation, dimensionality, extrapolation and inverse-branch semantics.
Keep the exact affine path; never claim arbitrary smooth functions are captured
or that increasing N solves discontinuities/folds/aliasing.

## G2 — system animation matrix

`test_g2_axis_animation` observes the unanimated artist after every rendered frame.
Independent affine solving or SciPy RegularGridInterpolator computes its current
derivative. A native scene has the same ordinary hierarchy and arguments, plus an
external artist that stays still. Fresh Cairo captures compare every frame with
a capture omitting all Frame instances, including auxiliary animation copies.

C1: every-frame artist correctness; C2: native frame endpoint; C3: count/finite/
nondegenerate frame; C4: invisible frame. “Same as Manim?” includes the external
artist. The native control includes the same hidden probe geometry; G4 separately
compares visible axes without that probe. P/F mean pass/fail.


| Animation | C1 max error | C2 endpoint | C3 frame | C4 channels | Same as Manim? |
| --- | --- | --- | --- | --- | --- |
| Create | P; 0 | P | P | P; 0 | Yes |
| Write | P; 0 | P | P | P; 0 | Yes |
| ShowPassingFlash | P; 0 | P | P | P; 0 | Yes |
| Indicate | P; 2.22045e-16 | P | P | P; 0 | No: curve follows |
| Wiggle | P; 9.15513e-16 | P | P | P; 0 | No: curve follows |
| ApplyWave | P; 9.48575e-16 | P | P | P; 0 | No: curve follows |
| Flash | P; 0 | P | P | P; 0 | Yes |
| Circumscribe | P; 0 | P | P | P; 0 | Yes |
| Uncreate | P; 0 | F; 7.2111 | P | P; 0 | No: protected frame |
| DrawBorderThenFill | P; 0 | P | P | P; 0 | Yes |
| FadeIn | P; 0 | P | P | P; 0 | Yes |
| FadeOut | P; 0 | P | P | P; 0 | Yes |
| FadeInShift | P; 2.22045e-16 | P | P | P; 0 | No: curve follows |
| FadeOutShift | P; 2.22045e-16 | P | P | P; 0 | No: curve follows |
| GrowFromCenter | P; 1.11022e-16 | P | P; singular at alpha=0 | P; 0 | No: curve follows |
| Rotate | P; 4.57757e-16 | P | P | P; 0 | No: curve follows |
| ScaleInPlace | P; 1.11022e-16 | P | P | P; 0 | No: curve follows |
| MoveAlongPath | P; 4.44089e-16 | P | P | P; 0 | No: curve follows |
| Homotopy | P; 9.48575e-16 | P | P | P; 0 | No: curve follows |
| ApplyPointwiseFunction | P; 1.33227e-15 | P | P | P; 0 | No: curve follows |
| ApplyMatrix | P; 4.96507e-16 | P | P | P; 0 | No: curve follows |
| Transform | P; 4.44089e-16 | P | P | P; 0 | No: curve follows |
| MoveToTarget | P; 4.44089e-16 | P | P | P; 0 | No: curve follows |
| Restore | P; 8.88178e-16 | P | P | P; 0 | No: curve follows |
| animate_chain | P; 8.9509e-16 | P | P | P; 0 | No: curve follows |
| animate_rotate | P; 4.96507e-16 | P | P | P; 0 | No: curve follows |

Maximum C1 error is **1.33227e-15**.
All N=9 frame arrays retain **328 points**, without NaNs. GrowFromCenter at alpha=0
collapses planar area; p2c raises **LinAlgError: Singular matrix**, then recovers
in subsequent frames. No fallback invents coordinates at this allowed singularity.

G2's literal requirements conflict: partial-drawing protection preserves the grid,
where native Uncreate leaves degenerate geometry. The protected endpoint differs
by **7.2111**, with unequal point counts. Both remove axes;
the external curve remains. This causes the overall FALSIFIED verdict.

What the user sees, compared with the native external curve's zero motion:

- FadeOut(ax,shift=DOWN): still-opaque curve follows the moving/fading axes and
  cleanup reset; sampled excursion **0.986454** scene units.
- Indicate(ax): unanimated curve expands/contracts with axes; excursion
  **0.600682**.
- Wiggle(ax): unanimated curve wiggles with them; excursion
  **0.292841**.


Installed evidence: `creation.py::ShowPartial.interpolate_submobject` (`:132-134`)
calls partial drawing; `creation.py::DrawBorderThenFill.interpolate_submobject`
(`:283-288`) uses both partial drawing/interpolation.
`indication.py::Wiggle.interpolate_submobject` (`:559-567`) restores points **in
place**, then scales/rotates. `animation.py::Animation.begin` (`:205-214`) suspends;
`animation.py::Animation.finish` (`:225-227`) interpolates then resumes.

**PLAN / ADR 0001 changes:** distinguish protected usable frames from native raw
removal buffers. Permit native geometry animate on the tested surface instead of
universal F-908 overrides. Document that frame binding carries indication/fade
geometry while artist opacity/visibility remains independently owned, and record
singular p2c behavior.

## G3 — artist animation matrix

`test_g3_artist_animation` compares each case with an ordinary VMobject with the
same points/style, then repeats with a tracker animated 1 -> 1.5 during play.
The frame and sibling are checked for exact isolation. Range changes and changes
back force rebuilds. The independent data control uses changed source geometry
and the native endpoint affine, or the selected target, rather than only comparing
the getter to its own pipeline. Replacing/detaching state makes the selected
target authoritative. Every target's endpoint geometry also matches its control.

C1: native final geometry/style without tracker; C2: correct native state survives
rebuilds; C3: frame/sibling isolation; C4: changed data or selected target. An
incorrect but stable state is F in C2. All completed rows render nine frames.


| Animation | C1 max error | C2 survives | C3 isolated | C4 data/target error | Same as Manim? |
| --- | --- | --- | --- | --- | --- |
| Create | P; 0 | P | P | P; 1.48952e-15 | Yes |
| Write | P; 0 | P | P | P; 1.48952e-15 | Yes |
| ShowPassingFlash | P; 0 | P | P | P; 1.48952e-15 | Yes |
| Indicate | P; 0 | P | P | P; 1.48952e-15 | Yes |
| Wiggle | P; 0 | P | P | P; 1.48952e-15 | Yes |
| ApplyWave | P; 1.78819e-14 | P | P | P; 1.27343e-15 | Yes |
| Flash | P; 0 | P | P | P; 1.48952e-15 | Yes |
| Circumscribe | P; 0 | P | P | P; 1.48952e-15 | Yes |
| Uncreate | F; 6.00663 | F; stable wrong state | P | P; 0 | No |
| Rotate | P; 4.96507e-16 | P | P | P; 2.97904e-15 | Yes |
| animate_shift | P; 0 | P | P | P; 2.22045e-15 | Yes |
| animate_chain | P; 0 | P | P | P; 2.97904e-15 | Yes |
| MoveToTarget | P; 0 | P | P | P; 1.89715e-15 | Yes |
| Transform | P; 0 | P | P | P; 0 | Yes |
| ReplacementTransform | P; 0 | P | P | P; 0 | Yes |
| TransformCircle | P; 6.10623e-16 | P | P | P; 6.10623e-16 | Yes |
| TransformFromCopy | P; 0 | P | P | P; 1.48952e-15 | Yes |
| FadeOutShift | F; 1 | F; stable wrong state | P | P; 0 | No |

Frame/sibling errors are **exactly zero**; max independent data/target error
is **2.97904e-15**.
Native shift/scale chains, Rotate, MoveToTarget and artist targets persist without
geometric overrides. Indicate does not adopt enlargement; Wiggle leaves no trace.

Transform(curve,Circle()) succeeds: source 160 points, Circle 32 aligned to 160.
Saving the target **after** alignment is essential; before alignment its shape
does not match the endpoint buffer. Accepted Circle points become local coordinates
via p2c, detached from the old source/tracker, and follow subsequent frame/range
changes. Endpoint error **6.10623e-16**.

The converse fails: `test_g3_target_with_more_points` transforms a 36-point artist
to 196 points. B discards pre-suspension source-alignment writes; exact exception:

```text
operands could not be broadcast together with shapes (36,3) (196,3)
```

There is one attempted interpolation and zero frames, versus 11 calls/nine native
frames. A real alignment transaction must start before suspension. No special
write exception or shape-delta heuristic was added to hide this failure.

FadeOut(curve,shift=DOWN) adopts its shifted target at resume, then cleanup restores
initial points **outside suspension**. B discards restoration: style matches but
geometry has a **1.0-unit downward error**, stable after rebuild/re-add.
Uncreate rebuilds full **160-point** geometry from the native **four-point
degenerate** buffer; final control-point distance **6.00663**.
Both remove the object. ShowPassingFlash's later restoration is also rejected,
but the rebuilt full curve has current data, fixing v1's cleanup-data failure.

Re-adding removed objects:

- Uncreate: PoC is already full; scene.add(artist) works without refresh. Native
  Manim requires restoring/replacing degenerate geometry first.
- ReplacementTransform: removed source retains accepted target source, parameters,
  placement/style. scene.add(artist) re-adds it while the real replacement target
  remains; its final geometry matches native Manim in this test.
- Shifted FadeOut: simple re-add exposes the permanent erroneous offset.


Installed evidence: `transform.py::Transform.begin` (`:204-212`) aligns before
suspension; `vectorized_mobject.py::VMobject.align_points` (`:1883-1894`) writes
resampled arrays; `mobject.py::Mobject.become` (`:3308-3311`) writes outside
suspension. `transform.py::_MethodAnimation.finish` (`:449-451`) replays methods
before endpoint/resume. `fading.py::FadeOut.clean_up_from_scene` (`:190-192`)
calls interpolate(0) after cleanup. `indication.py::ShowPassingFlash.clean_up_from_scene`
(`:324-325`) restores a full partial. `transform.py::TransformFromCopy.__init__`
(`:310-311`) animates the target; `transform.py::TransformFromCopy.interpolate`
(`:313-314`) reverses alpha: the original stays unchanged, as measured here.

**PLAN / ADR 0001 changes:** replace shadow classification only with a lifecycle
covering **alignment and cleanup**. Suspension alone remains insufficient. Separate
data validity from removal buffers: unconditional rebuilding violates F-907.
Specify target adoption, detachment and become. Same-length targets and the one
successful Circle case do not establish general Transform support.

## G4 — idioms, ownership and containers

`test_g4_redraw_registry[always_redraw/become]` runs the literal sine/tracker idioms
and ordinary VMobject controls. Every frame has exact expected/control geometry,
11 interpolations, and registry size **one** after gc.collect(), also after play.
`test_g4_copy_ownership` checks both system-first/artist-first group copy orders:
source sharing, artist-only binding to original system, group binding to copied
system, and copied registry size one (only the explicitly copied artist).

`test_g4_path_queries[False/True]` checks get_end, point_from_proportion(0.5),
dot.move_to(get_end()), and every rendered MoveAlongPath dot position against
ordinary Manim: all errors zero. 1/x has **two subpaths in one VMobject**. This
tests path mechanics, not pole detection or gap-aware traversal.

`test_g4_tracker_dot_parenting_and_simultaneous`: dot updater during axis rotation
has max error below **7e-18**. Ordinary ax.add(curve); ax.shift(RIGHT) moves the
child once, error zero. scene.add(ax); scene.play(Create(curve)) **retains the
parent in both implementations**. Explicit scene.add(curve) subsequently splices
it in both. The prompt's Create-splice assumption is false in this version:
`scene.py::Scene.add_mobjects_from_animations` (`:535-545`) checks the current
family and does not re-add an existing child; explicit `scene.py::Scene.add`
(`:525-526`) restructures the list.

play(ax.animate.shift(LEFT),curve.animate.shift(LEFT)) moves the curve **two units
left**, the axis one; native independent axes/curve code moves both one. The axis
is already suspended at the artist's hook in this argument order: a conservative
warning is cheap, but this alone is not reliable diagnosis. Begin order, manual
suspension, parenting and non-geometric indications also affect the flag; reliable
classification needs operation context absent from B.

VGroup(curve,dot).shift(UP) leaves the curve and moves the dot; native Manim moves
both. The setter can warn about rejection, but cannot reliably know whether the
same container moves the system before/after it. The same setter handles the
successful G1 groups; no local delta estimator supplies the missing transaction.

`test_g4_invisible_marker_bounds`: compared with the same visible native axes
without the marker, get_center differs by **0.5 in z**; rotating 0.4 about RIGHT
leaves an axis displacement **0.198669330795**. Invisible points affect bounds and
pivots; marker exclusion needs explicit boundary-query handling.

Installed evidence: `mobject_update_utils.py::always_redraw` (`:107-109`) creates
and becomes new objects; `mobject.py::Mobject.__deepcopy__` (`:444-451`) passes memo;
`mobject.py::Mobject.shift` (`:1282-1283`) writes children without calling their
shift. `movement.py::MoveAlongPath.__init__` (`:192`) disables suspension and
`movement.py::MoveAlongPath.interpolate_mobject` (`:201-202`) queries the path then
moves its subject. It works for an ordinary dot; suspension is not universal
animation detection.

**PLAN / ADR 0001 changes:** revise D11/F-708's no-op artist geometry rule and
document two-channel double motion. Distinguish weak registration from ordinary
add, correct the actual splice trigger, and specify copy/registry ownership.
Foreign groups without the system remain incompatible with B: blanket native
Manim compatibility is false.

## G5 — actual Cairo freezing and updater cost

`test_g5_static_freeze` uses scene.add(curve,ax). The tracker is not explicitly
added (Manim adds animation subjects itself). Actual renderer arrays are compared
with fresh full Cairo captures of current geometry: this catches stale pixels
even if reading curve.points would already give correct data.


| Driver | Empty updaters | Max middle-frame channel differences | Interpolations |
| --- | --- | --- | --- |
| axis | False | 1644 | 11 |
| axis | True | 0 | 11 |
| tracker | False | 1824 | 11 |
| tracker | True | 0 | 11 |

`test_g5_wait_overhead`: three fresh wait(2) scenes per mode, 320x180, 15 fps.


| Updater | Median wall ms | Render calls for wait(2) |
| --- | --- | --- |
| none | 1.1671 | [0, 0, 0] |
| empty | 1.1859 | [0, 0, 0] |
| empty_dt | 28.4699 | [30, 30, 30] |

The selected empty updater has **no dt argument**: it fixes moving-object
classification during play while preserving frozen waits. No-updater/no-dt modes
make zero per-frame wait renders; their sub-ms signed timing difference is noise,
not evidence of speedup. A dt updater forces 30 full renders. The no-dt choice
does not make time-driven updates run during frozen waits; those need a time-based
updater or always-update setting.

Installed evidence: `scene.py::Scene.get_moving_mobjects` (`:937-946`) starts the
moving suffix at animations/any family updater;
`cairo_renderer.py::CairoRenderer.play` (`:109-110`) caches the preceding image;
`scene.py::Scene.should_update_mobjects` (`:435-445`) checks **time-based** updaters
for Wait instead.

**PLAN / ADR 0001 changes:** require no-dt synchronization updaters on independent
bound artists, conservatively also the system, for this Cairo strategy. A lazy
points getter alone is insufficient. Document redraw versus Wait updater criteria.

## G6 — rebuild and ownership costs

`test_g6_600_frame_cost[False/True]`: 1920x1080, 60 fps, 10.1 seconds per path:
**606 rendered/dirty frames and 608 interpolations each**. Four artists have 2,000
samples/7,996 control points each, ten ticks and two lines: **16 derived leaves,
32,032 control points**. One tracker dirties pipelines every frame; a scene updater
explicitly dirties decorations too. N=33 frame is affine/stationary; the second
run forces the bilinear path.


| Path | Median rebuild ms | p95 rebuild ms | p95 all frame comparisons ms | 4 ms gate |
| --- | --- | --- | --- | --- |
| Affine | 0.684 | 0.7935 | 0.2537 | PASS |
| Forced bilinear | 3.8920 | 4.2447 | 0.2713 | FAIL |

These are the maintainer's rerun with nothing else running, and they match
`poc/poc2/results/g6_*.json`. The Codex run measured 1.73 ms and 6.86 ms p95 while the
superseded run was executing in parallel, so those numbers carried CPU contention. The
bilinear path in `Frame.forward` recomputes cell indices and weights on every call and
gathers four corner arrays per point. With the frame stationary between data changes,
those weights depend only on the samples, so the 4 ms miss is a cost of this
implementation, not yet evidence against bilinear placement.

Rebuild includes mapping, cache rebuilding, and frame checks within those calls.
The comparison counter also includes reads outside rebuilds: **columns overlap
and must not be added**. Median comparison calls/frame: **60**. Cairo rasterizing
and encoding are outside the timer. Adaptive sampling, clipping, pole discovery,
tick location/layout, labels, and G7 changing families are absent: this is still
a lower bound for production.

`test_g6_copy_and_comparison`: 50 system/four-artist group copies, median
**0.68805 ms**, p95 **1.59897 ms**; every artist binds to the copied system.
Ten thousand clean reads give these mean full-frame comparisons, including timer
overhead:


| N | Clean frame comparison ns/read |
| --- | --- |
| 9 | 2076.68 |
| 17 | 2803.33 |
| 33 | 4509.96 |
| 65 | 8935.47 |

The same F-1001 object group's update traversal costs
**2.423 us** without updaters, **29.733 us** with
five empty no-dt updaters: incremental **27.31 us/update**, over 30 batches of
100. This isolates CPU scheduling/callback cost, independent of resolution, not
additional Cairo cost. G5 quantifies wait behavior. Removing updaters during dirty
play can produce a frozen picture, not an equivalent-work rendering control.

V1 H4: p95 rebuild **0.31588 ms**, rebuild+shadow **0.48192 ms**, clean getter
**4291.5 ns**, median copy **0.5859 ms**. New affine/bilinear p95 rebuilds are
**5.48151x / 21.713x** that historical rebuild. V1 had 14 leaves and
no frame map: this is not a controlled 1.5x regression gate. Four points per grid
node increase O(N*N) comparisons. Changed-frame affine verification is not timed
by the stationary-frame read microbenchmark.


Installed evidence: `camera.py::Camera.set_cairo_context_path` (`:713`) reads
points; `mobject.py::Mobject.copy` (`:908`) calls deepcopy;
`mobject.py::Mobject.__deepcopy__` (`:447-449`) shares memo;
`indication.py::Wiggle.interpolate_submobject` (`:559`) demonstrates why setter-only
frame invalidation is insufficient.

**PLAN / ADR 0001 changes:** retain F-1001's absolute gate and record the bilinear
failure. Fast affine results do not certify nonlinear performance. Record the
machine/baseline; repeat comparable workloads before asserting a 1.5x gate. Weak
registration avoids copying all registered artists, not the cost of copies.

## G7 — live data overrides and native structural failure

`test_g7_override_and_chain_errors` uses a minimal setter and integer ticks. Its
UpdateFromAlphaFunc uses **suspend_mobject_updating=False**, updates the live range
and rebuilds the current tick set. All nine frames have correct integer tick sets
and independently correct mapped artist geometry, errors below 1e-9: **11 calls,
final range [-2,5]**. This demonstrates a data boundary, not a parameter API.

Both ax.animate.shift(RIGHT).set_x_range(...) and
ax.animate.set_x_range(...).shift(RIGHT) raise **NotImplementedError** exactly:

```text
Method chaining is currently not supported for overridden animations
```

The native experiment overrides interpolate on the frame to interpolate range
parameters, and on tick leaves to derive geometry rather than interpolate points.
The external curve follows the live map.
`test_g7_native_parameter_interpolation_tick_alignment`: range [-3,3] -> [-5,5]
causes alignment to insert faded duplicates throughout the shorter family. Source
starts `ParameterFrame,ParameterFrame,Derived,Derived,Derived,Tick,...`; target
starts `ParameterFrame,Derived,Derived,Tick,...`. The second frame pairs with an
axis leaf. Exact first-interpolation exception:

```text
AttributeError: Derived object has no attribute 'owner'
```

There is one attempted interpolation and zero frames; the same ordinary hierarchy
and target complete **11 calls/nine frames**. This falsifies local-overrides-only,
not every possible family-aware design. No role-matching layer was added to rescue it.
`test_g7_native_same_tick_count` also renders [-3,3] -> [-2,4], seven endpoint ticks
on each side: 11 calls/nine frames, roundoff-level artist geometry error, but tick
identities still represent the starting integers. Equal endpoint counts do not
solve intermediate parameter-derived structure changes.

Installed evidence: `mobject.py::_AnimationBuilder.__getattr__` (`:3443-3445`)
rejects chains and (`:3450-3456`) selects overrides;
`transform.py::Transform.begin` (`:211`) aligns before suspension;
`mobject.py::Mobject.align_data` (`:3019-3025`) recurses;
`mobject.py::Mobject.add_n_more_submobjects` (`:3092-3098`) distributes faded copies
by index, without knowing frame/tick roles. Local interpolation cannot undo that pairing.

**PLAN / ADR 0001 changes:** retain a separate live-data channel and F-909's current
no-chain ceiling. Relax F-908 for geometry, not data. Changing families need more
than frame/leaf interpolation; a structural identity mechanism needs its own PoC
before claiming native mixed-chain support.

## Differences from ordinary Manim

- Unanimated bound curves follow axis transforms/indications while retaining their
  opacity: **chosen binding policy**; native external curves stay still.
- Simultaneous system/artist motion doubles scene displacement: **two-channel
  consequence**, incompatible with copied independent-Manim code.
- Foreign groups without the system leave curves behind: **B limitation**, with
  insufficient operation context for reliable selective warnings.
- Shifted FadeOut leaves an offset on re-add: **lifecycle limitation** from cleanup
  restoring points after target acceptance, outside suspension.
- Uncreate(curve) re-adds full without refresh: **unconditional rebuild policy**,
  contrary to native degenerate buffers/F-907.
- Uncreate(ax) preserves the hidden grid: **required protection policy**, observable
  through coordinates/re-add rather than matching native raw removal geometry.
- Larger targets can raise before any frame: **pre-suspension alignment limitation**.
- Nonlinear maps are approximated, discontinuities become ramps, smooth transforms
  can alias completely: **finite-sampling limitation**, quantified in pixels.
- Nonlinear p2c may select another branch; collapsed frames raise: **inverse limitation**.
- Off-plane markers change bounds/pivots/3D motion: **representation limitation**
  pending explicit boundary-query treatment.
- Data/geometry chains fail through override_animate: **inherited Manim override
  ceiling**; the attempted native route currently fails tick/family semantics.
- Pure in-place edits outside suspension have no setter notification: **B limitation
  without a shadow**; rejecting tested container assignments is not rejection of
  every possible NumPy slice write.

Weak registration/redraw, memo-aware copies, split paths, dot updaters and ordinary
explicit Scene.add splicing work. They do not remove the differences above. No
production source, existing poc files, project configuration, PLAN, scope or ADR
was edited by this work.

## Reproduction

From the repository root in PowerShell, with ordinary Path.mkdir media directories,
no tempfile helpers or render markers. Results/timings are overwritten on rerun.

```powershell
# Full run.
.venv\Scripts\python.exe -m pytest poc/poc2 -p no:cacheprovider
# G1: operation/wrapper, dense table/inverse/cost, styles, smooth aliasing.
.venv\Scripts\python.exe -m pytest poc/poc2/test_geometry.py -p no:cacheprovider
# G2: 26 system animations, real frames and hidden-frame pixels.
.venv\Scripts\python.exe -m pytest poc/poc2/test_animations.py -k g2 -p no:cacheprovider
# G3: 18 artist animations with/without data, larger target failure/control.
.venv\Scripts\python.exe -m pytest poc/poc2/test_animations.py -k g3 -p no:cacheprovider
# G4: redraw/copies/weak registry/paths/dot/containers/marker bounds.
.venv\Scripts\python.exe -m pytest poc/poc2/test_idioms.py -k g4 -p no:cacheprovider
# G5: actual renderer/full Cairo arrays and no-dt/with-dt wait costs.
.venv\Scripts\python.exe -m pytest poc/poc2/test_idioms.py -k g5 -p no:cacheprovider
# G6: two 606-frame 1080p60 scenes, copies/comparisons/updater microbenchmarks.
.venv\Scripts\python.exe -m pytest poc/poc2/test_cost.py -p no:cacheprovider
# G7: live range, chain errors, native tick/family failures.
.venv\Scripts\python.exe -m pytest poc/poc2/test_data_channel.py -p no:cacheprovider
# Installed symbols and actual numbered lines, symbol first.
.venv\Scripts\python.exe -m poc2.evidence
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

Validation, maintainer rerun outside the Codex sandbox after the superseded files were
removed: **132 passed in 22.87 s**; both Ruff checks pass. The JSON under
`poc/poc2/results/` is from that rerun. Timings quoted in sections other than G6 are from
the Codex run and differ from the JSON by run-to-run noise and the contention noted
under G6; every non-timing number is deterministic and matches.

## Review notes

Found by reading `poc/poc2/model.py`, not by the tests:

- **The artist's own placement runs in scene space.** `Derived.derived` applies
  `self.placement` after `system.c2p`, so after `curve.shift(UP)` followed by
  `ax.rotate(PI / 2)` the offset still points up the screen instead of turning with the
  axes. Native Manim rotates a grouped graph together with its offset. No test combines
  an artist's own transform with a later system transform. The placement should be
  stored in the system's local space, conjugated through the frame (exact while the
  frame is affine).
- **The off-plane probe is not needed for 0.1.** Every 0.1 sample has `z = 0`, and an
  affine image of the plane is fully determined by the planar nodes. Dropping the probe
  removes the bounds and pivot shift `test_g4_invisible_marker_bounds` measured.
