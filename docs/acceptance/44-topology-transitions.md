# Acceptance table — task 44, topology-changing transitions

**Status: Draft, written 2026-10-31 before any code, per ADR 0003 §9.**
Choices not settled by ADR 0008 are marked *(default taken)* and stand unless vetoed.
Contracts: ADR 0008 §§3–6 (inverse data transitions, reversible entrances, lifecycle,
exports); ADR 0004 §9 (customisation); F-706 (viewport clipping), F-915 (moving
bindings), F-918 (sampling); tasks 28/28b (slices), 32 (histograms), 39 (volumes).

Modules: `manim_plots/animations/helpers.py` (Riemann), `bars.py` (rebinning),
`volumes.py` (voxels, isovalue, slices), package and top-level exports. Artist changes
needed by implementation belong to their existing modules; this specification changes
no implementation. Task 40 supplies `_base`; all tests observe public behaviour.

```python
class RefineRiemann(Animation):
    def __init__(self, rectangles, dx, *, lag_ratio=0, order="data", **kwargs): ...
class RebinHistogram(Animation):
    def __init__(self, hist, bins, **kwargs): ...
class StackVoxels(Animation):
    def __init__(self, voxels, *, axis="z", direction=1, lag_ratio=0.1,
                 reverse=False, remover=None, **kwargs): ...
class SweepIsovalue(Animation):
    def __init__(self, surface, level, **kwargs): ...
class SweepSlice(Animation):
    def __init__(self, view, stop, **kwargs): ...
```

`kwargs` are Manim Animation options, including `run_time` and `rate_func`; the
default duration is one second *(default taken)*; frame fixtures use linear easing
and six frames/second. Data transitions
stay in the scene; their inverse is another call with the previous target, not a
`reverse`/`remover` mode. Source-dependent starts are resolved at `begin`, allowing
sequential plays. Finite targets and nonnegative finite lag are validated before any
mutation. No automatic axes autoscaling *(default taken)*. Targets are semantic data,
never scene-space transforms. No new origin option: Riemann uses its bound baseline,
histograms their bottom, voxels their supplied corner arrays; slice direction and
isovalue direction follow the signed difference to the target *(default taken)*.

## RR — Riemann refinement and coarsening

Let parent interval i have sampled height H_i above its bound baseline and child j
have target height h_j. Keep the existing helper partition: for interval [a,b] and
step dx, `n=max(0, ceil((b-a)/dx-1e-9))`, left edges `a+i*dx`, and full-width
intervals `[a+i*dx,a+(i+1)*dx]`; the last may overshoot b. Sampling uses that full
interval, and `width_scale_factor` scales the drawn width as before. Nested refinement
means each required child interval lies inside one parent interval; the two partitions
need not have the same overshooting right endpoint. The last parent supplies only the
children whose left edges belong to the target partition; its unused overshooting tail
is retired, not filled with extra children. For [0,2.25], dx=1 gives [0,1], [1,2],
[2,3]; dx=.5 gives five children ending at 2.5, so [2,3] supplies only [2,2.5].
Each target child starts on its parent's interval portion with the parent's height,
and its height becomes `(1-p_i)*H_i + p_i*h_j`; its target x edges are already present
at alpha zero *(default taken)*. Parent windows follow data order by default; `order` may instead be a callable key
on each parent (left, right) interval, stably sorted ascending *(default taken)*, with
`p_i = rate_func(clip(alpha*(1+(n-1)*lag_ratio)-i*lag_ratio, 0, 1))`.
Coarsening reverses this correspondence. No arbitrary nonnested morph *(default taken)*.

| ID | Row |
|---|---|
| RR-1 | Refining dx=1 to .5 over [0,2], f(x)=x−1.1, has four addressable rectangles at alpha zero with child x bounds and parent heights. At alpha .5 their tops are the arithmetic mean of parent and child samples. Left, right, centre and callable quarter-interval rules follow their original rule; signed heights cross or remain below the baseline correctly. |
| RR-2 | Refinement over [0,2.25] to dx=.5 finishes with five rectangles, last full-width interval [2,2.5], inherited from parent [2,3]. A bound ValueTracker is committed to .5 and remains the same input: setting it to .25 later gives nine full-width rectangles ending at 2.25. A later x-range change preserves the target partition in data; existing binding updaters survive. |
| RR-3 | Refining is invertible by supplying the coarser dx: .5 to 1 yields two rectangles over [0,2]. Zero, negative, NaN and nonnested dx=.6 raise ValueError without altering the old geometry *(default taken: nested-only applies in both directions)*. |
| RR-4 | `lag_ratio` chooses parent timing, default simultaneous. At alpha .25 with two parents and lag=1, first parent progress is .5 and second is zero. Children of a parent share its window; there is no independently ordered child animation *(default taken)*. |
| RR-5 | An explicitly styled parent passes its fill colour/opacity and stroke width to both refinement children; library gradient defaults must not replace overrides *(default taken: parent-to-child style inheritance)*. |
| RR-6 | A callable `order=lambda interval: -interval[0]` reverses parent timing without changing rectangle indexing or final geometry. With lag=1 at alpha .25, the second parent is half refined and the first untouched *(default taken)*. |

## RH — histogram rebinning

Retain the most recent samples and weights from construction or `set_data`, rather
than reconstructing observations from counts *(default taken)*. Compute target edges
with NumPy histogram_bin_edges and target counts with NumPy histogram on those retained
samples. The rightmost edge includes equal samples, exactly as NumPy does.

For a single noncumulative dataset with common outer endpoints, split by the sorted
union of old and new edges. An atom's old mass is old-bin mass times its width divided
by old-bin width; similarly its target mass is target-bin mass times its width divided
by target-bin width. At eased fraction p interpolate these masses linearly. For density,
normalise the masses by total weight and draw height=mass/atom-width; for counts draw
height=mass *(default taken)*. Canonical bins are drawn at alpha 0 and after finish;
strictly intermediate atoms are an explicit transition representation, not a new
histogram estimator. Summed mass remains constant. Unequal widths are intentional.
Different outer endpoints, empty-density normalisations and signed weights are rejected
before mutation *(default taken)*. Ordinary empty count bins are supported.
For stacked/cumulative or grouped datasets, the same per-dataset atom mass rule is
applied before baseline stacking/cumulation *(default taken)*.

| ID | Row |
|---|---|
| RH-1 | Rebin weighted samples including exact internal and final edges from [0,2,4] to [0,1,3,4] and back: public `edges` and `counts` equal independent NumPy results, for counts/density and bar/step/stepfilled. Final bars have the new edges and heights; outlines visit each bin's top-left corner. Later range changes rederive the committed geometry. |
| RH-2 | At strictly intermediate frames, union pieces conserve total mass: sample set [.1,.2,1.5,3.5] rebinned [0,2,4]→[0,1,4] sums to 4 in count mode or integrates to 1 in density mode. The atom masses follow the formula above, not a count of samples at interpolated edges *(default taken)*. |
| RH-3 | Signed weights and invalid edges (duplicates, reversed, nonfinite) raise ValueError before mutation, leaving counts and edges intact *(default taken: signed-mass transport is deferred rather than silently using absolute weights)*. |
| RH-4 | Retain dataset order, stacked baselines, nonzero bottom, orientation, cumulative direction, dataset colours and opacity. Two datasets rebin independently; heights are independent NumPy counts (or their forward/reverse cumulative sums), stacked above bottom=1. Horizontal bars exchange the geometric axes. Existing parts remain addressable through `bars`/`outlines`; rebuilt bins inherit dataset styles *(default taken)*. |
| RH-5 | A count-coloured histogram's linked colorbar is declared moving before static compilation (F-915). Its range changes during the play and finishes at the target counts' min/max, its bar colours use the committed mapping, and replaced drawable parts leave no ghosts outside live scene families (LB-1). This does not request autoscaling of the parent axes. |

## SV — stacking voxels

Layer order is selected by `axis` and `direction`, default z increasing. Layers mean
occupied index planes, skipping wholly empty planes *(default taken)*. There is no
independent origin: supplied voxel corner geometry is authoritative. A layer's window
uses the RR window formula with default lag=.1. Occupancy is active for progress>0;
active exposed faces fade with their voxel's progress, preserving original opacity as
a multiplier. At progress zero the voxel contributes no drawable faces. Shared faces
are retired as the next layer activates; this is temporary occupancy derivation,
not a reveal of the final exterior shell *(default taken: fade within each layer)*.
Faces remain addressable by `at((i,j,k))`; original exterior faces retain identity and
individual styles, temporary newly exposed faces inherit voxel styles *(default taken)*.

| ID | Row |
|---|---|
| SV-1 | Two adjacent cells stacked with lag=1 have no faces at alpha zero, six faces at alpha .5 (including the first cell's temporary interface face), and ten exterior faces after finish. No final face lies in their shared plane. This holds for x/y/z and directions ±1; direction −1 starts at the higher-index cell. |
| SV-2 | `reverse=True` reverses the schedule, exposes the lower layer's formerly shared face as upper occupancy leaves, and removes the artist from the scene by default. Playing it forward again reintroduces the same registered artist with all ten canonical faces, original exterior identity/style, data and binding updaters. A later range change rederives the full block. |
| SV-3 | Explicit `remover=False` retains the reverse-played artist and restores canonical geometry after the play. Empty occupancy is a no-op. Invalid axis, direction other than ±1, and negative lag raise ValueError before mutation *(default taken)*. |
| SV-4 | Empty index layers are skipped: occupied z layers 0 and 2 have default-lag progress .55 and .45 at alpha .5, multiplying fill opacity .6 to .33 and .27. Each isolated cell has six exposed, individually addressable faces and preserves its supplied colour; finish restores twelve fully styled faces *(default taken)*. |

## SI — scalar isovalue sweep

Retain the sampled volume, physical origin and spacing at creation; do not resample
an unchanged callable per frame *(default taken)*. Interpolate level in scalar data,
extract honestly at that level, and commit it. A surface not created by
`plot_isosurface` is rejected with TypeError *(default taken)*. Triangles are
addressable through the surface's existing faces, with no promise of correspondence
across extractions; new triangles inherit surface styling *(default taken)*.

| ID | Row |
|---|---|
| SI-1 | For samples F[i,j,k]=i over [0,2]³, sweeping .25→1.75 gives the plane x=.25+1.5p each frame. Final geometry is at 1.75; inverse sweep returns to .25 and a later range change retains it in data. |
| SI-2 | Sweeping beyond the sample maximum gives an empty surface. All retired triangles outside the live family have no drawable points; sweeping back produces triangles again, without losing original updaters. No stale initial triangles survive an empty extraction. |
| SI-3 | A sampled double-well field `min((x−1)²,(x−3)²)+(y−1)²+(z−1)²` on [0,4]×[0,2]² with resolution=4 starts with two separated components at .25, has a connected bridge crossing x=2 at 1.25, and separates again on inverse sweep. The retained callable is never evaluated during either play (F-918). |
| SI-4 | NaN/infinite targets fail before geometry changes; a valid sweep preserves explicit surface fill opacity on rebuilt triangles *(default taken)*. |
| SI-5 | Under the actual Cairo moving-list path with caching enabled, each frame of a sweep to an empty level has no retired drawable triangle outside live scene families (F-915/LB-1). |

## SS — moving slices and profiles

`view` accepts `SliceView` or a coordinate slice from `surface.slice(x/y/z=...)`
*(default taken)*. A SliceView must have an axis-aligned x/y plane; arbitrary oblique
planes have no unique scalar stop and raise ValueError *(default taken)*. The scalar
coordinate interpolates from its current value to stop. Existing trackers are written
in place; constant inputs become committed bound coordinates *(default taken)*.
Plane, cut, profile and profile axes retain their addressable public attributes.

| ID | Row |
|---|---|
| SS-1 | On z=xy/2, a SliceView swept x=−1→1 has plane and cut x=−1+2p and profile ordinate x*y/2 on that same frame. Finish is x=1, inverse returns to −1. Both constant and tracker inputs work, and an original tracker still drives the view after the sweep. |
| SS-2 | Plane, cut and profile participate in actual Cairo moving detection before static compilation (F-915, caching enabled). An unrelated still function remains static and is not resampled (F-918); no obsolete drawable parts are left outside current scene families. |
| SS-3 | Bare x/y/z slices preserve their tracker binding, lie on z=x+y at the swept coordinate, become empty outside the surface domain, and return when swept back. This includes contour slices whose number of parts can change. |
| SS-4 | Plane/cut/profile identities and separate style overrides survive the sweep; each part retains its original updaters. Nonfinite stops fail without changing the original tracker *(default taken)*. |

## TC — common public contract

| ID | Row |
|---|---|
| TC-1 | Each name is the identical Animation subclass exported at the top level, package and specified family module. No test imports a future name during collection. |
| TC-2 | For every family, interpolating .4, then .8, then .4 yields the same geometry, supporting non-monotone easing without accumulation. Finish leaves exactly the pre-existing artist updaters. |
| TC-3 | Stacking beside a native axes range animation uses that frame's mapping: integer voxel x coordinates stay integer in data throughout. Concurrent isovalue writers to one surface fail clearly with ValueError mentioning conflict/writers, instead of silently choosing a winner *(default taken: exception type)*. |

## Review notes and test limits

Tests use `tests.mobjects.helpers.probe`; its final record is alpha 5/6, so canonical
finish assertions inspect the artist after play.
The shared `tests/animations/conftest.py` substitutes Pango Text for MathTex only when
no latex executable is on PATH; the merge gate keeps real TeX.
All geometry oracles use data, NumPy and public c2p/p2c mappings, not `_base`.

The maintainer alone can veto the marked defaults, particularly count-mode atom presentation, rejection of
signed weights, and discrete active occupancy with per-layer fading. No unresolved
question blocks this draft. Every row has executable coverage; the full combinations
of per-face shading, camera sorting, oblique slice rejection, integer/automatic bin
selection, changing histogram outer support and large-volume frame cost are not
exhaustively covered here. Existing artist tests remain responsible for unchanged
rendering conventions; the implementation session must run the full merge gate.
