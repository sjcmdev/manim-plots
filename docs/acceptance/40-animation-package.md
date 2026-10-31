# Acceptance table — task 40, animation package and reversible lifecycle

**Status: Draft, written 2026-10-31 before any code, per ADR 0003 §9.**
Rows marked *(default taken)* settle choices not fixed by ADR 0008 and stand unless
vetoed. Contracts: ADR 0008 §1–§4, §5 first bullet and §6; ADR 0004 §9
(addressable parts and overridable defaults); task 12 (existing artist animations);
task 34 GR-1, GR-2, AP-3 and LB-1; F-706 (clipping), F-915 (moving families),
F-918 (sampling activation). Task 40 establishes the common lifecycle; tasks 41–44
add the remaining families. `GrowBars(order=...)` belongs to task 42.

Modules, for the implementation session: `animations/__init__.py`, `_base.py`,
`curves.py`, `axes.py`, `bars.py`, `fields.py`, `surfaces.py`; compatibility exports
in `mobjects/animations.py`, `mobjects/fields.py`, `mobjects/surfaces.py` and the
package root. Artist derivation/binding hooks may need changes in `mobjects/`.
The specification session changes only this table, `tests/animations/` and the
explicitly requested `tests/test_layers.py` test change. No implementation, recipe
page, configuration, scope ledger or baseline is changed here.

`animations/` joins `mobjects/` in the **Manim layer**, above `core/`: it may import
Manim, core and artist definitions directly, but core may import neither Manim-layer
package. Absolute and relative imports are checked. The existing rule that only
`mobjects/context.py` reads the call stack also covers `animations/`. Family modules
must not import through `manim_plots` and create root-import cycles. The implementation
must add an `animations/*` exemption to Ruff's Manim-import ban; changing that config
is outside this specification edit. Empty future-family modules are unnecessary.

## Public signatures

All existing positional parameters remain positional-compatible. Existing native
`Animation`/`AnimationGroup` kwargs (`run_time`, `rate_func`, etc.) still work.
Types below describe the API; they are not extra public helper types.

```python
class TraceCurve(Animation):
    def __init__(
        self, artist, *, pacing="parameter", reverse=False, remover=None, **kwargs
    ): ...


class ShowPoints(Animation):
    def __init__(
        self,
        scatter,
        *,
        order="data",
        pop=False,
        lag_ratio=1.0,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class Morph(Animation):
    def __init__(self, a, b, **kwargs): ...


class AppendData(Animation):
    def __init__(self, artist, x, y=None, *, autoscale=False, **kwargs): ...


class DrawAxes(Create):
    def __init__(self, ax, *, reverse=False, remover=None, **kwargs): ...


class BuildAxes(AnimationGroup):
    def __init__(
        self, ax, lag_ratio=0.5, *, stages=None, reverse=False, remover=None, **kwargs
    ): ...


class HighlightTick(Indicate):
    def __init__(self, axis, value, color=YELLOW, scale_factor=1.5, **kwargs): ...


class GrowBars(Animation):
    def __init__(
        self, bars, lag_ratio=0.05, *, reverse=False, remover=None, **kwargs
    ): ...


class ShrinkBars(GrowBars):
    def __init__(self, bars, lag_ratio=0.05, **kwargs): ...


class SortBars(Animation):
    def __init__(self, bars, key=None, reverse=False, **kwargs): ...


class HighlightBar(AnimationGroup):
    def __init__(self, bars, key, dim_opacity=0.25, **kwargs): ...


class Flow(Animation):
    def __init__(self, field, *mobjects, speed=1, pointwise=False, **kwargs): ...


class GrowSurface(Animation):
    def __init__(
        self, surface, zdir="z", offset=None, *, reverse=False, remover=None, **kwargs
    ): ...


class ShrinkSurface(GrowSurface):
    def __init__(self, surface, zdir="z", offset=None, *, remover=None, **kwargs): ...
```

The `pacing` spelling and default `"parameter"`, the `"arc_length"` spelling,
`ShowPoints`' `order` callable taking one coordinate row, `pop=False` and boolean
pop semantics, and explicit `lag_ratio=1.0` preserving the old sequential reveal
are *(default taken)*. `ShrinkSurface` fixes reverse progress; it defaults to removal
and permits `remover=False` *(default taken)*. `SortBars.reverse` keeps its existing
meaning (descending sort). `AppendData` has no reverse/deletion operation.

`BuildAxes.stages=None` retains the current four stage slots (lines with tips,
ticks, numbers, labels with grid). This task requires unknown-stage validation;
task 41 specifies the full stage-selection/factory API. Recognised names are
`lines`, `tips`, `ticks`, `minor_ticks`, `numbers`, `labels`, `grid`, `panes`, `breaks`
(from the brainstorm); no new custom-stage behavior is specified here.

## Oracle conventions

Tests live in `tests/animations/test_package_lifecycle.py`, with one or more
`test_<id without hyphen lower>_...` tests per row. New names resolve inside test
functions. The package-resolution helper reports a missing package as `AttributeError`
without swallowing missing internal dependencies. This lets this preimplementation
suite collect and fail for the absent API rather than fail collection.

Geometry uses data coordinates through `ax.c2p`/`p2c` and NumPy, using cubic anchors
`points[::4]` (and final endpoints), never the handles of a curved/closed polygon.
The sole animation twins are **native Manim** operations on plain parts in AX-3;
no oracle invokes a library animation another way. A repeated-alpha state snapshot
is an observation of the earlier frame, not a second evaluation of its implementation.
Canonical snapshots include exact per-leaf styles and original updater identities.
Keep artists and axes strongly referenced. Scene probes use task 34's dry-run `probe`
and six frames per second. Read alpha-one state after the play, not the last record.
Tests with a simultaneous range change record alpha from that range or a separate
linear tracker, not from frame indices.

The shared `tests/animations/conftest.py` substitutes Pango `Text` for `MathTex` only when no `latex` executable is on PATH; the merge gate keeps real TeX.
Range choices contain the data unless a clipping test says otherwise.
F-915 probes call `Scene.get_moving_mobjects` before `begin`, with caching enabled;
unrelated still objects precede moving objects in scene order because Manim's
moving suffix legitimately includes subsequent objects.

## PK — migration and layers

| ID | Row |
|---|---|
| PK-1 | `manim_plots.animations.__all__` contains exactly the 14 names in the signatures, once each, for task 40. Family ownership is curves: TraceCurve, ShowPoints, Morph, AppendData; axes: DrawAxes, BuildAxes, HighlightTick; bars: GrowBars, ShrinkBars, SortBars, HighlightBar; fields: Flow; surfaces: GrowSurface, ShrinkSurface. Each is a Manim Animation subclass defined in its family module, and the family, package and top-level export are the same class object. Every previously supported old module path returns that same object. No wrapper class replaces an old export. Exact task-40 export set is *(default taken)*; later tasks extend it. |
| PK-2 | `forbidden_imports` in `tests/test_layers.py` rejects absolute and relative core imports of `animations` just as it rejects `mobjects`. Animation modules may use Manim/core/mobjects directly, may not import via the root package, and inherit the existing context-only stack-reading rule. Test fixtures exercise `import manim_plots.animations.curves`, `from manim_plots.animations import ...`, `from ..animations import ...`, and `from .. import animations`. |

## LC — lifecycle shared by the existing animations

| ID | Row |
|---|---|
| LC-1 | Each entrance (TraceCurve, ShowPoints, DrawAxes, BuildAxes, GrowBars, GrowSurface) finishes with the same bound geometry and per-leaf styles as before the play. A subsequent `set_x_range((-2,8,2))` remaps its data: curve endpoint (2,2), scatter row (1,3), bar height 6 at x=1, surface z=2+x+y, and keyed tick x=2. Axis decorations remain addressable through `ax.x.line`, `.ticks`, `.numbers`, `.labels`, `.grid`; markers, bars and `surface.faces` remain addressable. |
| LC-2 | Over **all 14 names**, finish/cleanup leaves precisely the preexisting updater identities on every surviving original family member; new members have no animation-owned updater. A sentinel updater survives, and binding updaters are retained, including on surface drivers. Shrink cleanup restores canonical geometry even though its target has left the scene. |
| LC-3 | Each entrance, ShrinkBars, ShrinkSurface, Morph, AppendData, SortBars, HighlightTick and HighlightBar has history-independent progress: under `there_and_back`, a second visit to 0.2 after 0.5 and 0.8 gives the frame of the first, including points and style (with lag, 0.2 and 0.8 differ: each part eases its own window). Numerical equality uses 1e-8 scene units *(default taken)*. Flow is exempt from this exact frame-equality contract: its state is the integral of the field over signed elapsed field time. With velocity `(x,0)`, a complete `there_and_back` play returns a dot to its starting position within 1e-3 scene units *(default taken)*. Data-change target commit is separately LC-9; emphasis restoration is LC-10. |
| LC-4 | TraceCurve, ShowPoints, GrowBars and GrowSurface run beside a linear x-range change and use that frame's mapping. Curve source-index progress ends on the piecewise-linear data curve; marker centres stay at their rows; bar ends follow `height*clip(alpha*1.1-i*.05,0,1)`; surface anchors satisfy `z=alpha*(2+x+y)` from offset 0. Probe partial frames with a linear clock; a two-point trace also checks exact `(4*alpha,4*alpha)` under its current range. DrawAxes/BuildAxes canonical mapping is LC-1 and their native partial-frame geometry is AX-2/AX-3. |
| LC-5 | Concurrent AppendData writers to the same line source raise `ValueError` with a writer/ownership/concurrency explanation before target data is committed; the source remains `[[0,1],[1,3],[2,2]]`. Error class, early atomic rejection, and message category are *(default taken)*. Presentation reveal and range change are allowed (LC-4), as are independent writers on distinct artists (LB-1 probes). |
| LC-6 | F-915: every existing animation participates through the real `Scene.get_moving_mobjects` path before static-background compilation; drawable target parts are moving. All six entrances include their affected drawable family. AppendData with autoscale declares owning axis lines and a separately added linked line, whose endpoint remaps to data (1,2); an explicitly fixed tick x=1 moves during the film. TraceCurve includes a separately added earlier endpoint label in the moving set. GrowSurface beside a z-range animation declares a separately added, earlier linked colorbar: its strip moves, its range follows 8→12 during the film. An unrelated earlier plot on another system remains static. Growth alone does not invent a change to its axes or color mapping. |
| LC-7 | F-918: for every existing animation, an ordinary function already sampled on the same system is not evaluated again merely because the animation runs. Count calls after initial geometry materialisation and after the play; equal counts are required. TraceCurve and GrowSurface also keep their own unchanged source-function call counts constant across the recorded frames (begin-time preparation is allowed). Existing sampling activation for genuine tracker/range changes remains intact (LC-11 and LC-4); the animation must not make unrelated functions implicitly live. |
| LC-8 | LB-1: AppendData rebuilding an end label, and a concurrent append/autoscale, bar-height change and crosshair tracker change with explicit axis numbers, leave no moving mobject with points outside current scene families on any probed frame. Use actual `scene.moving_mobjects`, not a private ownership flag. End label, bar labels and crosshair stay in the scene so bindings run. |
| LC-9 | Data effects commit canonical targets: Morph adopts the target curve's data (endpoint (2,3)) and follows later ranges while its target remains unchanged; AppendData commits old+new rows ending at (3,4), and follows later ranges; SortBars moves heights 2,4,6 to category slots 0,1,2; Flow with velocity (.25,0) moves a dot from data (0,1) to (.25,1) in one second. Flow on a plain dot commits its new placement; it does not create a data binding for that dot. |
| LC-10 | HighlightTick and HighlightBar restore exactly the stroke colours, widths, opacities, fill opacities and points found at begin, including different partial opacities on different bars and a custom tick colour/scale. Default emphasis colors and dimming are overridable through existing kwargs. |
| LC-11 | Removing a tracker-parameterised graph with reverse TraceCurve, changing its tracker while absent, introducing the same graph again and then animating its tracker leaves the binding alive: `y=h*x`, x in [0,2], h=2→3→4 ends at data (2,8), with `parameters['h'].value==4`. The artist is added to the scene for tracker playback. |

## RV — direction, scene membership and reuse

For a forward schedule `E(alpha)`, reverse means `E(1-alpha)`, including part order;
it does not merely replace growth by `1-local_progress` in the same order. A forward
play with `remover=True` still grows forward, then removes. `remover=False` overrides
reverse's default removal. Cleanup restores canonical bound state whether the object
remains in the scene or leaves *(default taken, following ADR §4)*.

| ID | Row |
|---|---|
| RV-1 | For every entrance, exercise `(reverse=True,remover=None)`, `(True,False)`, `(False,True)`. Cleanup membership is respectively absent, present, absent; original geometry/styles survive. Reintroducing the same instance with the default entrance adds it, preserves its canonical data/styles, and a later range change still remaps it. Removing axes removes the axes container and its visible decoration family, rather than leaving temporary animation groups in the scene. |
| RV-2 | At alpha 0,.2,.5,.8,1, reversed TraceCurve ends at source parameter `2*(1-alpha)` on [(0,1),(1,3),(2,2)] (empty at 1); ShowPoints row i has opacity `clip(3*(1-alpha)-i,0,1)`; GrowBars i has height `h_i*clip((1-alpha)*1.1-i*.05,0,1)`; GrowSurface anchors have z=`(1-alpha)*(2+x+y)`. No source values are shortened merely to obtain these frames. Reversed axes are checked against native removers in AX-3. |
| RV-3 | ShrinkSurface is the GrowSurface reverse/removal convenience, accepts zdir and offset and supports reintroduction with GrowSurface. At halfway from z=2+x+y towards offset 1 it has z=`1+.5*(1+x+y)`. ShrinkBars retains task 34's signature, default removal and old same-index shrinking formula `1-clip(alpha*(1+(n-1)*lag)-i*lag,0,1)`; it is deliberately not changed to the new reverse schedule. Both aliases remove their targets and preserve canonical data/styles for reintroduction. |
| RV-4 | GrowBars with `reverse=True`, lag .2, n=3 unwinds the whole forward schedule. At alpha 0,1/7,.5,6/7,1, bar i's factor is `clip((1-alpha)*1.4-i*.2,0,1)`; the last bar starts leaving first. This differs intentionally from unchanged ShrinkBars. |

## TC — curve pacing and edge cases

`pacing="parameter"` means x for a FunctionPlot, normalised input index for a LinePlot,
and t for a ParametricPlot; a source interval retains its declared direction.
`pacing="arc_length"` measures cumulative **mapped scene-space** length of valid
path pieces, excluding gaps *(default taken)*. Never pace by adaptive sample count.
The default parameter mode preserves data-x/index behavior; the new parameter
semantics for parametric curves are intentional. Pacing never joins disconnected pieces.

| ID | Row |
|---|---|
| TC-1 | On the collinear data [(0,0),(1,0),(4,0)] with linear easing at alpha .375, parameter pacing ends at (.75,0), while arc-length pacing ends at (1.5,0). Both use the current axes mapping. This distinguishes uneven source spacing from a sample-count reveal. FunctionPlot y=x² on [0,4] at alpha .5 reaches data (2,4), within .02 scene units of the retained curve *(default taken)*. |
| TC-2 | On `(t²,t)`, t in [0,3], alpha .5 reaches (2.25,1.5), within .02 scene units for the retained piecewise-linear approximation *(default taken)*. A two-turn spiral `r=1+t/10`, t in [0,4π] or [4π,0], at alpha .25 reaches its declared t-quarter point within .04 scene units *(default taken)*; turns do not collapse onto a single polar angle. |
| TC-3 | NaN-separated line pieces never acquire a cubic connecting x≤1 to x≥3 during a reveal, even after `reverse_points()`. Source-order progress remains independent of native buffer reversal; canonical reversal survives finish. Empty, singleton and repeated-identical-point inputs in either pacing mode finish without nonfinite points or changing their canonical geometry/styles. These cases do not divide by zero. The explicit pole gap around x=1 in 1/(x−1), dt=.1, is never bridged at partial frames in either pacing mode. |
| TC-4 | Unknown pacing (e.g. `"samples"`) raises ValueError naming pacing before mutating curve geometry/styles *(default taken)*. |

## SP — ordered points and pop

`order="data"` preserves row order; x/y/value sort ascending with stable ties; value
uses retained numeric `c` values rather than displayed RGB. A callable order receives
the original coordinate row and returns its sort key *(default taken)*. Sorting
changes only the presentation schedule, not source data or marker identities.
For n retained rows and lag L, `window_i=clip(alpha*(1+(n-1)*L)-i*L,0,1)` and
`progress_i=rate_func(window_i)`; n=0 is a no-op. The default L=1 reproduces the
old sequential reveal. Retained invalid/clipped rows occupy their original schedule
slots *(default taken, preserving the existing index-based behavior)*.
`pop=True` scales canonical marker geometry about its mapped centre by that same
progress, with no overshoot; `False` leaves size unchanged *(default taken)*.

| ID | Row |
|---|---|
| SP-1 | For x=[3,1,1], y=[2,3,1], c=[2,1,3], the order indices are data=[0,1,2], x=[1,2,0], y=[2,0,1], value=[1,0,2]. At alpha .5 with default lag, ranks have opacity [1,.5,0]. Callable `lambda row:-row[1]` introduces row 1 first. Stable ties retain data order; all final markers remain independently addressable. |
| SP-2 | A custom Square marker at data (1,2), original fill opacity .4, with `pop=True`, at alpha .5 has half its canonical width, unchanged mapped centre and fill opacity .2. Finish restores its exact width and .4 fill. Pop is independently overridable, and does not replace the supplied marker shape. |
| SP-3 | Input rows at x=10 outside [-1,4] and a NaN x stay hidden — their points kept at zero fill and stroke opacity, the scatter convention — throughout and after an x-ordered popping reveal. Source rows/markers are retained rather than deleted or made drawable by styling. |
| SP-4 | With n=3, lag .2 and alpha .5, factors are [.7,.5,.3]. Multiply each original fill, stroke and background-stroke opacity (.4,.6,.2) independently by its factor; do not replace any channel with the factor itself. |
| SP-5 | Unknown order or `order="value"` without retained numeric c raises ValueError naming order/value before geometry/style mutation *(default taken)*. |

## BA — existing bar semantics under the common lifecycle

| ID | Row |
|---|---|
| BA-1 | Vertical and horizontal bars with heights/widths [-3,4] and base/left=2 grow from that base: at alpha .5, lag 0, the growth coordinate spans sorted([2,2+h/2]); orientation chooses y or x. Canonical colour is unchanged while growth is presentation-only, including c='height'. Width in the orthogonal coordinate is unchanged. |

## SF — surface growth and valid origins

| ID | Row |
|---|---|
| SF-1 | GrowSurface supports existing zdir x/y/z and offset kwargs: at alpha .5 from explicit offset 0, only the chosen data coordinate is halved; reversing that one coordinate recovers z=2+x+y at every face anchor. Finish is canonical, and RV rows cover its exit. `offset=None` retains the existing lower endpoint of the selected coordinate range as origin. On a log-z system with offset 1 and surface z=10+x+y, halfway anchors satisfy z=1+.5*(9+x+y), rather than an interpolation of logarithms. |
| SF-2 | An explicit zero offset on a log-z system is rejected with ValueError naming origin/offset/domain/log before changing any face/style. Unknown zdir, NaN and infinite offsets are likewise rejected before mutation. Finite is insufficient: the scale domain must accept the plane. |
| SF-3 | Growth supports retained triangle faces, NaN holes and reversed parameter intervals. Face identities and the hole mask stay unchanged; existing anchors of z=2+x+y move to z=.5*(2+x+y) at alpha .5. Finish restores geometry and per-face styles; no temporary face filling, recolouring, topology change or bridge across a hole is allowed. |

## AX — native axes construction and reverse composition

| ID | Row |
|---|---|
| AX-1 | BuildAxes rejects an unknown explicit stage name before geometry/style mutation, with ValueError naming stages *(default taken)*. Stage factory and expanded ordering customization are specified in task 41; existing `lag_ratio` remains overridable here. |
| AX-2 | Default BuildAxes preserves the four-slot forward schedule and lag .5. At overall linear alpha .1 an axis line has started, while tick x=2 has no drawable extent yet. At finish the tick centre is exactly c2p(2,0), including when the numbers/labels stages are empty. |
| AX-3 | Reversed DrawAxes matches native Uncreate on plain copies of its visible leaves; reversed BuildAxes matches native AnimationGroup(FadeOut(labels+grid), FadeOut(numbers), Uncreate(ticks), Uncreate(lines+tips)), lag .5. At alpha 0,.2,.5,.8,1 compare points and fill/stroke opacity of each addressed leaf, including a NumberPlane grid. Child easing remains native, group easing is linear for the oracle. Cleanup restores canonical bound decorations and scene membership follows RV-1. |

## DO — native recipes

| ID | Row |
|---|---|
| DO-1 | `docs/site/animations.rst`, linked from the index, shows runnable native Create/FadeIn/Write recipes for exposed ticks, numbers (call add_numbers first), grid and an end_label, plus a ValueTracker-driven get_tangent_line helper. The text explains adding bound helpers/artists to the scene and animating their existing trackers. No dedicated tick/number/grid/end-label/follow animation is introduced. Filename and tangent representative are *(default taken)*. The existing tests/test_docs.py DO-3 word-presence and DO-4 runnable-RST-block patterns justify a docs test here: require named recipes and execute its Python blocks through the existing DO-4 helper. |

## Review boundaries

Every row has a test; full raster/camera/occlusion regressions, performance measurements,
serialisation of pre-move pickles and the supported interpreter/Manim matrix remain the
implementation/review gate, not new baselines in this specification. F-1001 stays
unchanged. There is no new public framework API for `_base`; its behavior is exercised
through the public classes. Internal helper names are intentionally not frozen.

Maintainer-only decisions, if these defaults are vetoed: whether arc length means
mapped or raw-data distance; the exact pacing/order/pop kwargs and callable-key shape;
whether invalid/clipped scatter rows consume schedule slots. The table chooses
mapped distance, the signatures above and retained slots. ShrinkBars keeps its legacy
timing as required by the task; that is not an unsettled default. No blocking
maintainer question remains.
