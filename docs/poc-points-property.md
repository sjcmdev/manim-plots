# Points-property proof of concept

Measured on 2026-10-24 against the project's **Manim 0.21.0**, using
`.venv/Scripts/python.exe` directly. This is a disposable experiment, not an
implementation of `manim-plots`. All experiment code and generated evidence are in
[`poc/`](../poc/). No library modules or architecture decisions were changed.

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| H1: a `VMobject` points property supports the complete proposed direct-geometry surface | **FALSIFIED** | `test_bootstrap_cache_setter_and_cairo` gives identical pixels and cache identity, but `test_direct_geometry_and_order` loses `VMobject.apply_function` on rebuild (maximum error 0.864). |
| H2: shadow distinguishes temporary animation geometry; suspension supplies a sufficient replacement | **FALSIFIED** | `test_animation_matrix[Wiggle-A]` changes shared placement six times; B fixes that but fails `ShowPassingFlash`, the removal-buffer contract, and native `.animate.shift`. |
| H3: a property leaf can be copied, including a dirty-marking `__setattr__` | **CONFIRMED** | `test_deepcopy_registry_and_dirty_setattr`: 50 successful copies, median 0.586 ms; each copy also duplicates all four registered leaves and their sources. |
| H4: the minimal dirty pipeline can rebuild below 4 ms | **CONFIRMED** | `test_600_frame_rebuild_and_getter_cost`: 605 fully dirty Cairo frames at 1080p60, p95 rebuild 0.316 ms; this is only a lower bound for the eventual engine. |
| H5: converted `MathTex` glyphs and changing numeric labels meet the integration/cost assumptions | **FALSIFIED** | Conversion works (`test_mathtex_leaf_write_and_rotation`), but cold whole-string `MathTex` labels cost up to 3.16 s in one frame and 10.5 s per animation; even warm, frames that introduce labels exceed 4 ms at p95. |

## Experiment boundaries

[`poc/points.py`](../poc/points.py) contains one array source, a diagonal linear map,
an ordered placement list, and one `VMobject` leaf. Adjacent affines compose; a
callable node separates affine runs. The cache and its shadow are separate arrays.
The setter tolerates initialization before the pipeline exists, records an affine
only through the leaf's own operation, and otherwise adopts a transient array.
Non-affine operations whose function is known to the hook append that function.
The affine probe covers only the functions exercised here; it is not a proposed
general affine-recognition algorithm.

A uses only shadow equality for temporary geometry. B adds the requested
`suspend_updating` / `resume_updating` flag and performs pending rebuilds on resume.
Neither variant has animation-name detection, special cleanup handling, or a patch
for `VMobject.apply_function`. Warnings deliberately name `refresh()`.

Leaves share the coordinate system's placement tail and the system holds a strong
registry reference to them. This makes effects on `c2p`, siblings, and copying
observable. These are decoration/geometry leaves, not a proposed attached-artist
API: PLAN's attachment paragraph makes direct geometry on attached artists a
warned no-op, whereas this experiment explicitly needs direct leaf transforms.

The requested A3.2 `__setattr__` experiment is included, with an initialization guard
and one data parameter (`amplitude`). However, current PLAN and scope F-911 already
supersede that API sketch with descriptors. Successful copying here does not
constitute a decision to bring `__setattr__` back into the library design.

## H1 — property mechanics work; the two-hook geometry claim does not

`test_bootstrap_cache_setter_and_cairo` observes one pre-pipeline setter call during
construction, survives a subsequent `reset_points`, and asserts
`leaf.points is leaf.points`. A foreign whole-array translation remains transient;
`refresh()` discards it. Cairo renders the leaf and an ordinary `VMobject` made from
the same points at 320 × 180: **zero differing pixel channels**, with **786 nonblack
RGB channels**. The frames are `poc/media/property.png` and `poc/media/plain.png`.

Relevant installed code:

- `mobject.py::Mobject.__init__` (`:125`): `self.reset_points()`;
  `mobject.py::Mobject.reset_points` (`:458`):
  `self.points = np.zeros((0, self.dim))`.
- `camera.py::Camera.set_cairo_context_path` (`:713`):
  `points = self.transform_points_pre_display(vmobject, vmobject.points)`.

`test_direct_geometry_and_order` changes the source amplitude from 1 to 1.5 after
each direct operation. It checks both lazy data application and preservation after
an explicit forced rebuild:

| Direct operation | Placement nodes | Data applies lazily | Survives forced rebuild | Maximum error against the same operation on changed data |
| --- | ---: | --- | --- | ---: |
| `shift(RIGHT)` | 1 | yes | yes | 0 |
| `rotate(0.4)` | 1 | yes | yes | 0 |
| `scale(1.3)` | 1 | yes | yes | 0 |
| inherited `VMobject.apply_function(nonlinear)` | 0 | no | no | 0.864 |
| control: `Mobject.apply_function(leaf, nonlinear)` | 1 | yes | yes | 0 |

The nonlinear function adds `0.15 * x**2` to y. The control followed by `shift`
produces the ordered node sequence `function, affine`, with zero error against
`shift(nonlinear(points))`. This checks the interleaving requirement without
introducing a matrix-plus-callable-side-list shortcut.

The additional write path is
`vectorized_mobject.py::VMobject.apply_function` (`:1226-1228`):

```python
self.scale_handle_to_anchor_distances(factor)
super().apply_function(function)
self.scale_handle_to_anchor_distances(1.0 / factor)
```

`vectorized_mobject.py::VMobject.scale_handle_to_anchor_distances` (`:1273`)
calls `submob.set_anchors_and_handles(a1, new_h1, new_h2, a2)`. Thus a direct call
already has a modified buffer when the proposed geometric hook runs. A and B both
classify it as temporary, even outside an animation. Rebuilding loses the operation.

**Required design change:** retain the property/cached-object decision, but amend
PLAN's assertion that the two `Mobject` hooks cover the `VMobject` mutation surface.
Direct nonlinear transforms need an owned operation boundary covering handle
preconditioning as well as the map operation. ADR 0001 §4 must reference this wider
boundary; replacing only the animation detector cannot fix H1. The hypothesis as
phrased combines property feasibility, which succeeds, with geometry coverage,
which fails.

## H2 — neither A nor B satisfies the complete contract

### Real animation playback

`test_animation_matrix` runs all 18 animation/variant combinations through
`Scene.play`, Cairo, 320 × 180, 15 fps, 0.6 s. It preserves each animation's default
rate function; only the separate `ValueTracker` animation is linear. No movie is
written, no cached animation is used, and `skip_animations` is false.

Each case draws **9 frames**. Normal animation roots receive **11 `interpolate`
calls with 10 distinct alpha values**; the `Flash` and `Circumscribe` composition
roots receive **9 calls with 9 distinct values**. This is not endpoint-only testing.
A scene updater observes the tracker crossing 0.25 and changes the leaf amplitude
once, from 1 to 1.5, during playback. A second leaf on the same system has unchanged
source data. A no-op leaf updater keeps Cairo from treating scene-updater-only
geometry as a static cached image.

The following table records the final full-suite run. **P/F** mean pass/fail;
criterion 3 combines exact unchanged `c2p` and exact unchanged sibling points.
Criterion 2 uses `np.array_equal`, except that `Uncreate` must be degenerate.
For A, observing `points` after playback may trigger the planned deferred rebuild;
the JSON also records the untouched post-play buffer separately.

| Animation | A: 1 placement | A: 2 buffer | A: 3 isolation | A: 4 data | B: 1 placement | B: 2 buffer | B: 3 isolation | B: 4 data |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Create` | P | P* | P | P* | P | P | P | P |
| `Write` | P | P* | P | P* | P | P | P | P |
| `ShowPassingFlash` | P | P* | P | P* | P | F | P | F |
| `Indicate` | P | P | P | P | P | P | P | P |
| `Wiggle` | F | F | F | F | P | P | P | P |
| `ApplyWave` | P | F | P | F | P | P | P | P |
| `Flash` | P | P | P | P | P | P | P | P |
| `Circumscribe` | P | P | P | P | P | P | P | P |
| `Uncreate` | P | P: degenerate | P | F: deferred† | P | F: full geometry | P | P |

*These passes are observations, not stable guarantees. A legal allocation contents
test below reproduces a failure for `Create`; partial-buffer writes are also used
by `Write` and `ShowPassingFlash`.

†The requested unconditional criterion 4 conflicts with PLAN's explicit removal
contract: data dirtied during `Uncreate` stays deferred until `refresh()`. A follows
that contract, removes the object, and passes the explicit refresh assertion. B also
removes the object, but its resume rebuild replaces the degenerate removal buffer
with the full updated geometry. Treat removal and restoration as different
postconditions when rewriting the requirements.

### Why A fails

`indication.py::Wiggle.interpolate_submobject` (`:559`) writes
`submobject.points[:, :] = starting_submobject.points`, then calls `scale`
(`:560`) and `rotate` (`:564`). A clean restored buffer is not evidence that these
calls are permanent. In `test_animation_matrix[Wiggle-A]`, A makes **six placement
updates**, collapsed into one affine node. Maximum coordinate-component changes:
**0.000277655** for the `c2p` probes and **0.000517253** for the sibling. B makes zero
placement updates and both changes are exactly zero.

The premise about `Homotopy` needs qualification on a `VMobject`.
`movement.py::Homotopy.interpolate_submobject` (`:103-107`) first assigns
`submobject.points = starting_submobject.points` and then calls `apply_function`.
However, `VMobject` handle preconditioning intervenes before the geometric hook.
In this test `ApplyWave-A` does **not** append placement nodes; it instead leaves
data unapplied, with a **0.299872081** maximum difference from derived points.
It still falsifies the restoring contract, through a different path than the
paper prediction. B applies the deferred data and ends exactly clean.

There is also a mid-write ambiguity. In
`vectorized_mobject.py::VMobject.pointwise_become_partial` (`:2067`),
`self.points = np.empty(...)` precedes writes through getters into slices
(`:2070`, `:2077`, `:2082`). An allocated array can legally contain the previous
shadow bytes. If data is pending, A can then rebuild between allocation and slice
writes. The remaining writes put old animation points into the newly derived cache.
Its shadow now describes the new data, so the final old shape never goes clean.

`test_create_legal_empty_contents[A]` makes that allocator possibility deterministic:
it fills matching `np.empty` allocations with the original shadow, without replacing
animation interpolation or Cairo rendering. A fails criterion 2 and 4, with a
**0.299872081** maximum error; `[B]` passes. Ordinary `Create-A` was also observed
both passing and failing across local runs. Consequently the observational A matrix
does not assert its allocator-dependent passes as universal postconditions.

### Why B is useful but insufficient

`animation.py::Animation.begin` (`:206-213`) creates the starting copy, calls
`self.mobject.suspend_updating()` when enabled, then `self.interpolate(0)`.
`animation.py::Animation.finish` (`:226-227`) calls `resume_updating()` after the
final interpolation. `mobject.py::Mobject.suspend_updating` (`:1204-1207`) sets the
flag and recurses into submobjects. The seven matrix animations that directly
animate the leaf each call its suspension hook once.

But `ShowPassingFlash` has a later write:
`indication.py::ShowPassingFlash.clean_up_from_scene` (`:324-325`) calls
`submob.pointwise_become_partial(start, 0, 1)`. B has already rebuilt the changed
data during resume; cleanup restores the old starting points afterwards. Both
buffer equality and data application fail, with maximum error **0.299872081**.
As in stock Manim, this animation removes its subject by default; the test still
inspects the requested final leaf state.

`Flash` and `Circumscribe` call the tested leaf's suspension hook **zero times**:
they animate auxiliary lines/a surrounding frame. Their table passes do not prove
that B detects them; the original leaf simply keeps following its data pipeline.

### Animations without suspension

`test_animations_without_suspension` plays every case below for both A and B.
Each has **11 interpolation calls**, **9 rendered frames**, and **zero leaf
suspension calls**. The text reveal classes receive a glyph-like `VGroup` of PoC
leaves accepted by their runtime implementation; this checks their mutation and
suspension behavior, not `Text` or `MathTex` text shaping.

| Animation | Observed behavior, identical in A and B |
| --- | --- |
| `ShowIncreasingSubsets` | Changes opacity, zero placement writes; geometry stays clean. |
| `AddTextLetterByLetter` | Same: opacity/reveal changes, zero placement writes. |
| `RemoveTextLetterByLetter` | Same geometry result; group removed at completion. |
| `PhaseFlow` | Zero placement writes; first leaf has transient geometry, discarded by refresh. |
| `MoveAlongPath` | **11 placement writes**, collapsed into one affine; movement persists through refresh and changes the shared system. |

The explicit false defaults are in
`creation.py::ShowIncreasingSubsets.__init__` (`:511`),
`creation.py::AddTextLetterByLetter.__init__` (`:561`),
`creation.py::RemoveTextLetterByLetter.__init__` (`:609`),
`movement.py::PhaseFlow.__init__` (`:151`), and
`movement.py::MoveAlongPath.__init__` (`:192`).
`movement.py::PhaseFlow.interpolate_mobject` (`:169`) calls `apply_function`;
`movement.py::MoveAlongPath.interpolate_mobject` (`:202`) calls `move_to`.
Suspension therefore cannot be a general animation detector.

### Persistent geometry and F-908

`test_b_persistent_animate_shift[native]` plays exactly
`leaf.animate.shift(RIGHT)` on B. It looks correct after playback (maximum error
**2.22e-16**), but has **zero placement nodes**; refresh loses the entire translation
(error **1.0**). `transform.py::_MethodAnimation.finish` (`:449-450`) invokes the
real method **before** `super().finish()`, hence while B still considers geometry
temporary. Merely adding suspension hooks cannot make the native path permanent.

`test_b_persistent_animate_shift[override]` uses the same syntax on the leaf with
`override_animate`. Its callback interpolates translation in the live placement
tail. It ends with **one affine node**, survives refresh, and has error **2.22e-16**
both before and after refresh. Both paths draw nine frames.

`mobject.py::_AnimationBuilder.__getattr__` (`:3450-3456`) chooses
`method._override_animate(...)` instead of applying a method to the target. This
supports F-908's chosen channel. It does not remove copying: the builder's
constructor has already called `self.mobject.generate_target()` at
`mobject.py::_AnimationBuilder.__init__` (`:3418`).

**Required design changes:** replace PLAN rules 2–3 and ADR 0001 §4's assertion
that shadow distinguishes animation from direct geometry. Shadow is evidence of a
buffer edit, not an operation boundary. A tested lifecycle solution must cover the
whole begin/interpolate/finish/cleanup transaction, distinguish removing from
restoring animations, and preserve an explicitly owned permanent parameter channel.
Document the behavior of unsuspended animations. Keep F-908, and do not describe B
alone as the correction: cleanup, native method finish, manual suspension, and
buffer allocation all prevent that conclusion. Do not solve partial writes by
changing cache identity, which would violate F-902.

## H3 — guarded copying succeeds, but follows the entire registry

`test_deepcopy_registry_and_dirty_setattr` creates four leaves from **2,000 samples
each**. Straight cubic segments contain **7,996 control points per leaf**. Changing
the data parameter marks the original dirty before copying. All 50 calls to
`copy()` succeed without invoking the leaf initializer. Updating a copied parameter
also marks only the copy dirty.

Results: median **0.5859 ms**, p95 **0.67469 ms**. Copying one leaf creates a new
coordinate system containing all **four** registered leaves and distinct source
arrays. The registry's source/cache/shadow arrays alone total **2,302,848 bytes**;
this excludes Python objects, styles, and allocator overhead.

`mobject.py::Mobject.__deepcopy__` (`:446-450`) contains:

```python
result = cls.__new__(cls)
clone_from_id[id(self)] = result
for k, v in self.__dict__.items():
    setattr(result, k, copy.deepcopy(v, clone_from_id))
```

The guard uses `self.__dict__.get("_ready", False)` rather than assuming that fields
have already been restored. `mobject.py::Mobject.copy` (`:908`) returns
`copy.deepcopy(self)`; `animation.py::Animation.create_starting_mobject` (`:265`)
returns `self.mobject.copy()`. `generate_target` and the builder path cited above
mean these costs also exist before an overridden animation is selected.

**Design consequence:** no replacement of the points property is needed for H3.
ADR 0001 should nevertheless state clone ownership explicitly: immutable source
sharing, private mutable placement in animation copies, and whether a clone should
carry an artist registry. A normal strong reference copies the entire reachable
graph. Sharing the live mutable system wholesale to make copying cheap would let
`Indicate.create_target` scaling mutate the original; it is not a valid shortcut.
The measured cost is for this small minimal graph, not the future engine.

## H4 — minimal rebuild fits, with substantial unmeasured work remaining

`test_600_frame_rebuild_and_getter_cost` runs one linear tracker animation for
10.1 s at **1920 × 1080, 60 fps**, with actual Cairo rendering and no movie output.
There are four 2,000-sample leaves plus **10 tick leaves**: **32,024 control points**
in total. The tracker dirties all 14 leaf pipelines each frame. Of **606 rendered
frames**, **605** rebuild every leaf; the unchanged initial frame is excluded.
The benchmark uses A's ordinary clean-buffer data path; it does not animate the
geometry or its suspension flag.

Recorded machine: Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1,
24 logical CPUs; Python **3.13.2**, NumPy **2.5.2**, Manim **0.21.0**.

| Measurement | Median | p95 |
| --- | ---: | ---: |
| Sum of all leaf rebuilds per dirty frame, including copying shadows | 0.2602 ms | **0.31588 ms** |
| All shadow comparisons during that frame | 0.1244 ms | **0.17558 ms** |
| Rebuild + shadow comparison time, computed per frame | — | **0.48192 ms** |
| Getter calls per dirty frame | **28** | **28** |

The minimum and maximum getter counts are also 28: two reads per leaf on this
specific Cairo rendering path. `camera.py::Camera.set_cairo_context_path` (`:713`)
reads `vmobject.points` directly. These counts must not be generalized to geometry
queries, animation setup, or a different scene composition.

`test_shadow_microbenchmark` uses one 7,996-control-point leaf, 100 batches of 200
reads in each mode. The median clean getter is **4,291.5 ns** with shadow, versus
**215 ns** when the comparison is bypassed, a difference of **4,076.5 ns** per read.
Timings include measurement overhead; they are not a CPU-instruction-level profile.
Per-frame raw counters are saved in `poc/results/h4_frames.json`.

**This minimal pipeline is a lower bound on rebuild cost**, with no adaptive
sampling, clipping, discontinuity splitting, general scale compilation, tick
location/layout, or changing TeX labels. The 4 ms rebuild budget leaves approximately
**3.684 ms** for additional work on this machine (about **12.7×** the measured
rebuild cost in total). Charging shadow comparisons to that same budget leaves
approximately **3.518 ms** (about **8.3×** the measured combined cost in total).
Neither estimate is a promise that the omitted work fits; TeX cost is unknown.
Cairo rasterization and encoding are not included in the rebuild timer.

**Design consequence:** no performance-driven architecture change is justified by
this lower bound. Keep F-1001 and record this as a PoC baseline, not a library
baseline. There is no previous comparable engine baseline against which to certify
the **1.5×** regression requirement. Repeat the gate with the actual core, shape
processing, and labels before accepting the architecture's complete performance
claim. Benchmarks are machine- and load-dependent; later reruns overwrite the JSON
with their own measurements.

## H5 — glyph conversion works; per-string TeX does not fit the frame budget

Codex's sandbox could not run TeX: MiKTeX reported `It seems that this is a fresh TeX
installation` there, and the three TeX-dependent tests skipped. The numbers below come
from a rerun of the same, unmodified tests outside the sandbox on the same machine on
2026-10-24: **41 passed, no skips**. MiKTeX on Windows, Manim **0.21.0**.

**Conversion — confirmed.** `test_mathtex_leaf_write_and_rotation` turns each glyph of
a `MathTex` label into a PoC `Leaf` (glyph points become the source, style is copied),
asserts that every geometric leaf is a PoC type, plays `Write(label)` through real
interpolation (**11** `interpolate` calls, **9** rendered frames) with exact restored
buffers, and rotates the system so that every glyph follows through the shared
placement. F-1004 is achievable for `MathTex` labels.

**Cost — falsified.** The workload plays range `(0, 10)` → `(0, 1000)` over **2 s at
15 fps**: 30 rendered frames plus an explicit endpoint, so **31** label updates, with a
small MaxN-like locator (1/2/5/10 steps, at most six ticks). It produces **19** distinct
label strings and **8** distinct digits (`test_label_workload`). Each update times
generation, positioning and conversion to PoC leaves; a string already built in the
same run is reused. *Cold* is a fresh, empty media directory. *Warm* repeats the same
workload and directory with fresh in-process label dictionaries, so the TeX/SVG files
on disk are reused but nothing held in memory by the first run is.

| Strategy | TeX compiles | Cold median | Cold p95 | Cold max | Cold total | Warm p95 | Warm max | Warm total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| whole-string `MathTex` per label | 19 | 0.34 ms | **1,340 ms** | **3,156 ms** | **10,468 ms** | 5.31 ms | 8.43 ms | 45.8 ms |
| cached single-digit `MathTex`, assembled | 8 | 0.32 ms | 538 ms | 3,412 ms | 4,516 ms | 5.37 ms | 12.09 ms | 47.6 ms |

Per update, the medians sit at about 0.3 ms because most frames introduce no new label.
The cost is concentrated in the frames that do (`new_labels_per_update` in
`poc/results/h5_cost_*.json`: 6, 3, 1, 2, 0, 1, …).

What this means:

- **Whole-string `MathTex` scales with the data, not with the alphabet.** Every distinct
  string is one TeX run, at roughly 0.2-0.5 s each here, and an animated range can mint
  an unbounded number of them. Against a minimal rebuild p95 of 0.32 ms (H4), TeX is
  four orders of magnitude larger on the frames where it runs. Manim renders offline,
  so this is render time, not stutter, but F-1001's per-frame gate cannot be met on
  those frames.
- **A glyph cache bounds compilation to the alphabet.** This is the mechanism in
  `numbers.py::DecimalNumber._string_to_mob` (`:226-229`):

  ```python
  if string not in string_to_mob_map:
      string_to_mob_map[string] = mob_class(string, **kwargs)
  mob = string_to_mob_map[string].copy()
  ```

  Here it cut compiles from 19 to 8 and the cold total by more than half. For numeric
  labels the alphabet is closed (digits, sign, decimal point, exponent markers), so
  after warm-up no animated range compiles again. Digit assembly does not reproduce
  general TeX kerning or arbitrary formula layout; Manim's `DecimalNumber` accepts the
  same trade.
- **Even warm, frames that introduce labels exceed 4 ms at p95** (about 5.3 ms in both
  strategies), because the measurement includes SVG parsing and building fresh
  dictionaries. An in-process glyph cache that lives across frames, and keyed identity
  (D10) reusing every surviving label, should leave only genuinely new labels paying
  anything; that has not been measured.

**Required design changes:** keep ADR 0001's answer that a label string is LaTeX in math
mode, but split the path that renders it. Generated numeric labels are assembled from a
process-wide glyph cache in the `DecimalNumber` manner. Whole-string `MathTex` is
reserved for labels known at configuration time, such as explicit ticks (`r"\pi"`),
and is compiled then rather than in a frame. F-1001 must state whether label
generation is inside the 4 ms gate. If it is, the gate needs a warm in-process glyph
cache as a precondition, and first-time TeX compilation excluded explicitly.


## Reproduction

Run from the repository root in PowerShell. Nothing needs installing for H1–H4.
For H5, the existing TeX installation must already be able to compile Manim's
default template, which it cannot inside Codex's Windows sandbox. All media stays under
`poc/media`; tests have no `render` marker.

```powershell
# Full PoC suite: 41 passed outside the sandbox; 38 passed, 3 TeX skips inside it.
.venv\Scripts\python.exe -m pytest poc

# H1 and H3, including pixel parity and 50-copy measurements.
.venv\Scripts\python.exe -m pytest poc/test_points.py -v

# H2: complete natural-playback matrix and unsuspended cases.
.venv\Scripts\python.exe -m pytest poc/test_animations.py -v

# H2: deterministic legal allocator contents, and permanent animation channels.
.venv\Scripts\python.exe -m pytest poc/test_animations.py -k 'legal_empty or persistent' -v

# H4: 605 dirty frames and the separate shadow microbenchmark.
.venv\Scripts\python.exe -m pytest poc/test_cost.py -v

# H5: actual glyph conversion, workload counts, cold/warm strategies.
.venv\Scripts\python.exe -m pytest poc/test_labels.py -v -rs

# Installed source for the principal quotations, symbol followed by numbered lines.
.venv\Scripts\python.exe -m poc.evidence

.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

The managed environment denies writes to the existing root `.pytest_cache`, so the
literal requested pytest command may emit a cache warning. To avoid only that
warning, append `-o cache_dir=poc/.pytest_cache`; this does not change test selection
or rendering. The final measurements above used that option. Geometry warnings
naming `refresh()` are expected observations. Ruff check and format check pass.

Machine-readable evidence is in [`poc/results/`](../poc/results/): `h1_*`,
`h2_<variant>_<animation>`, `h2_no_suspend_*`, `h2_shift_*`, `h3_copy`, `h4_*`, and
`h5_*`. Results are overwritten when their tests rerun; the seeded-allocation cases
have separate filenames. The committed JSON is from the rerun outside the sandbox, so
the H1-H4 figures in it differ slightly from the text above, which reports Codex's
run: for example rebuild p95 is 0.347 ms there against 0.316 ms here, and copy p95
0.79 ms against 0.67 ms. No verdict changes.

Directories that `tempfile.mkdtemp` creates under `poc/media` from inside Codex's
elevated Windows sandbox are owned by the sandbox user and unreadable to the
maintainer's account, which breaks pytest collection. Delete them from an elevated
shell, or run with `-o "norecursedirs=media .pytest_cache results __pycache__"`.
