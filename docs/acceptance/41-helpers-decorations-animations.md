# Acceptance table — task 41, 2D helpers and decorations

**Status: Draft, written 2026-10-31 before any code, per ADR 0003 §9.**
Contracts: ADR 0008 §§1–6 (package, flags, lifecycle, names); ADR 0004 §9
(customisation); task 34 AX-1 and LB-1; tasks 10, 12, 25, 35 and 37 (bound artists).
Choices not settled by the ADR are marked *(default taken)* and stand unless vetoed.
Task 40 owns `_base`: these tests use public animations, not its private hooks.

Modules: `manim_plots/animations/helpers.py`, `decorations.py`, `axes.py`, and
their package and top-level exports. Artist implementations remain in
`mobjects/helpers.py`, `errorbar.py`, `legend.py`, `colorbar.py` and `system.py`.
This specification changes only this table, its test file and the empty test package.

```python
class ExtendReference(Animation):
    def __init__(
        self, line, *, origin="start", reverse=False, remover=None, **kwargs
    ): ...


class GrowRegion(Animation):
    def __init__(self, region, *, axis=None, reverse=False, remover=None, **kwargs): ...


class SweepRegion(Animation):
    def __init__(
        self, region, *, axis="x", direction=1, reverse=False, remover=None, **kwargs
    ): ...


class SweepSpan(Animation):
    def __init__(self, span, *, direction=1, reverse=False, remover=None, **kwargs): ...


class GrowRiemann(Animation):
    def __init__(
        self, rectangles, *, lag_ratio=0.05, reverse=False, remover=None, **kwargs
    ): ...


class GrowErrorBars(Animation):
    def __init__(
        self,
        errors,
        *,
        lag_ratio=0.05,
        cap_lag=0.15,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class RevealAnnotation(AnimationGroup):
    def __init__(
        self,
        annotation,
        *,
        text_first=False,
        lag_ratio=0.3,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class RevealCrosshair(AnimationGroup):
    def __init__(
        self, crosshair, *, lag_ratio=0.15, reverse=False, remover=None, **kwargs
    ): ...


class RevealLegend(LaggedStart):
    def __init__(
        self,
        legend,
        *,
        lag_ratio=0.15,
        artist_animations=None,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...


class FillColorbar(AnimationGroup):
    def __init__(self, bar, *, lag_ratio=0, reverse=False, remover=None, **kwargs): ...


class BuildAxes(AnimationGroup):
    def __init__(
        self,
        ax,
        lag_ratio=0.5,
        *,
        stages=None,
        stage_animations=None,
        reverse=False,
        remover=None,
        **kwargs,
    ): ...
```

These are public constructor signatures, not an implementation prescription beyond
the Manim bases required by ADR 0008. `**kwargs` accepts native animation options
including `run_time` and `rate_func`. `BuildAxes` keeps its positional `lag_ratio`.
Defaults and option spellings in this block are *(default taken)* except the ADR's
`reverse=False`, `remover=None` contract, the existing `BuildAxes` lag default,
and GrowRegion's reviewed `axis=None` inference rule.

## Frame and lifecycle conventions

For one-second plays at the probe's 6 fps, record `i` has raw time `i/6`, not an
alpha-one finish. End oracles read the artist **after** `play`. Geometry oracles use
data coordinates through `ax.p2c` / `ax.c2p`, and Bezier anchors, including the end
of **each** disconnected curve. All ranges contain the supplied data (F-706).

For `n` equal-duration parts, lag `l`, raw whole-animation fraction `a`, and part
index `i`, `w_i = clip(a * (1 + (n-1)*l) - i*l, 0, 1)`; its progress is
`rate_func(w_i)`. A simple reveal uses `rate_func(a)`. Reverse uses the **whole
forward schedule at `1-a`**, preserving the selected origin/direction; it does not
merely reverse each part independently. Easing is applied once at the specified
window, not again to the group clock *(default taken, brainstorm §4)*. Linear
oracles therefore fix timing independently of any implementation helper.

An alpha-zero part may have no points or degenerate points at its specified
origin, but no visible ink. In a sweep it may be an empty polygon or a closed
zero-width frontier *(default taken)*. No topology/point-count oracle constrains
these equivalent representations. Artists retain their input order, labels,
sources, colours, fill/stroke opacities, clipping and independently styled parts.

Every `*-2` row below means: run the reverse, remove the complete target family
from the scene at cleanup, keep its registration/data/styles, and reintroduce the
**same object** to its full bound geometry. Every `*-3` row means: entrance
introduces the target, ends with exact pre-play geometry/styles, leaves all
pre-existing binding updaters and no new updater, and follows later range and
frame changes. The tests change x/y ranges and shift the axes, then compare
against the data, not a second invocation of the animation. Legend layout stays
in its own scene coordinates; it does not follow the axes *(existing contract)*.

The shared `tests/animations/conftest.py` substitutes Pango Text for MathTex only
when no latex executable is on PATH; the merge gate retains real TeX.
Numeric geometry is not an oracle here; the live colorbar still has real numbered leaves. No `_base` methods
are patched, no new name is imported at collection, no image baseline is needed,
and the probe's `dry_run` disables image/video file output.

## ER — reference and drop lines

| ID | Row |
|---|---|
| ER-1 | `ExtendReference` grows a reference line's currently visible data interval from `origin="start"`; `"end"` chooses the other endpoint and `"center"` grows both halves. For vertical data x=2 over y=[-4,12], alpha .5 gives [-4,4], [4,12], [0,8], respectively. Full endpoints are restored after play. These origin choices are *(default taken)*. |
| ER-2 | Reverse contracts toward the same selected origin, then removes; reintroduction preserves reference fractions and styles (lifecycle above). |
| ER-3 | Canonical finish; after y becomes [-6,14], a reference's .25/.75 viewport fractions become y=[-1,9], and x=2 survives a changed x map and shifted frame. |
| ER-4 | A solid vertical drop to data (3,8) grows from its axis intersection (3,0), reaching (3,4) at alpha .5. Unknown `origin` raises `ValueError` mentioning origin before any geometry/style changes *(default taken)*. |

## GR — paired-boundary region growth

| ID | Row |
|---|---|
| GR-1 | `GrowRegion` preserves the paired second boundary and replaces the first by `second + p*(first-second)` **in data**. With `axis=None` (the default), infer x for `fill_betweenx`, y for `fill_between` and `get_area`; an explicit axis overrides inference. `[0,4]`, first=6, second=2 has y=[2,4] at .5; `fill_betweenx` without an axis kwarg exchanges x/y. |
| GR-2 | Reverse collapses to the paired second boundary, removes, retains data/styles and can reintroduce the same region. |
| GR-3 | Canonical finish; range/frame changes still give x=[0,4], y=[2,6], with custom fill opacity .4. |
| GR-4 | Signed crossing growth keeps the crossing fixed: x=[0,2], first=[4,-2], second=1 has anchors (0,1), (0,2.5), (1,1), (2,-.5), (2,1) at .5. `get_area` between graph x+4 and bounded graph x+1 over [0,2] grows from that sloping baseline; at .5 every boundary anchor has y−x equal to 1 or 2.5. |

## SR — region sweeps

| ID | Row |
|---|---|
| SR-1 | `SweepRegion(axis="x", direction=1)` intersects the canonical region with a data half-space whose frontier runs from min to max. `direction=-1` runs from max to min. At .5 on x=[0,4], y=[2,6], the visible x interval is [0,2] or [2,4]; the front includes **both** boundary intersections and is closed. `axis="y"` exchanges coordinates. Axis/direction defaults and numeric ±1 directions are *(default taken)*. |
| SR-2 | Reverse retreats that frontier in the same direction's schedule, removes, and can reintroduce the unchanged region. |
| SR-3 | Canonical finish; subsequent range/frame changes recover the complete x=[0,4], y=[2,6] region. |

## SS — mixed-coordinate spans

| ID | Row |
|---|---|
| SS-1 | `SweepSpan` infers the data-interval axis from `axvspan`/`axhspan` and sweeps it in `direction` ±1 *(default taken)*. At .5 a data interval [1,5] becomes [1,3] or [3,5]. Orthogonal .25/.75 fractions stay viewport fractions: with ranges x=[-2,8], y=[-4,12], the orthogonal bounds are x=[.5,5.5] or y=[0,8]. |
| SS-2 | Reverse collapses the interval to the same chosen edge, removes, preserves both coordinate conventions and styles, and reintroduces. |
| SS-3 | Canonical finish; after changing the ranges/frame, x remains [1,5] for a vertical span while its orthogonal fractional y bounds become [-1,9]. |

## RI — Riemann rectangles

| ID | Row |
|---|---|
| RI-1 | `GrowRiemann` uses retained interval order and per-part windows; each rectangle keeps its x endpoints and grows from its own signed base to `base + p_i*(sample_height-base)`. Test graph x−1, interval [0,4], dx=1.5, width scale=1, `lag_ratio=.5`, left/center/right samples, times 1/3, 1/2, 2/3 (including lag boundaries). The existing artist has three **full-width** rectangles, the last ending at 4.5; this reveal does not repartition it. Default lag .05 and retained order are *(default taken)*. |
| RI-2 | Reverse shrinks signed heights with the complete reversed schedule, removes, retains sample rule/dx/colours, and reintroduces. |
| RI-3 | Canonical finish; graph x−1 with unit rectangles still gives `[i,i+1] × [min(0,i−1),max(0,i−1)]` after range/frame changes, including the zero-height rectangle. |

## EB — error bars

| ID | Row |
|---|---|
| EB-1 | `GrowErrorBars` grows asymmetric x/y endpoints from each sample as `sample ± p_i*error`. Retain zero errors and `errorevery`; with x=[1,2,3], y=[3,4,5], lower=[1,3,2], upper=[2,3,1], every=2 and zero lag, at .5 the y intervals at x=1/3 are [2.5,4]/[4,5.5], with no sample-2 bar. Caps restore their configured **full** scene width .12, not .24. Existing `xbars`, `ybars`, `xcaps`, `ycaps`, `markers`, `line` remain separately styleable. Sample order and lag .05 are *(default taken)*. |
| EB-2 | Reverse hides caps before retracting the errors, then removes the whole container. All original errors, markers/line, styles and registration survive reintroduction. |
| EB-3 | Canonical finish; asymmetric intervals [1,4] at x=1 and [3,6] at x=3 remain correct after mapping/frame changes. |
| EB-4 | `cap_lag=c` is the final fraction of each sample window reserved for growing cap width: `clip((p-(1-c))/c,0,1)` for c>0; c=0 gives full width once the sample starts *(default taken)*. With c=.5 and a .2 scene-width cap, at raw 1/3 it is hidden, at 2/3 width is .2/3, and after changing the orthogonal range final width is still .2. |
| EB-5 | A masked NaN error stays absent throughout growth; absent x errors remain None and capsize=0 stays empty. Optional marker opacity is canonical opacity times sample progress, and the optional connecting line traces in source order with whole-animation progress *(default taken)*. With zero lag, custom marker opacity .6 becomes .3 halfway and the line from (1,3) through (2,4) to (3,5) ends at (2,4). Independently customised bar/marker styles restore at finish. The existing invalid-input warning is consumed at construction, not reissued every frame. |

## AN — annotations

| ID | Row |
|---|---|
| AN-1 | `RevealAnnotation` extends `.arrow` from its canonical text-boundary end toward the current `xy` input, then writes `.text`; `text_first=True` swaps stages. Two equal windows with `lag_ratio=1` have only the first part visible at t=1/6. Preserve a caller-supplied red `Text("A")` by identity, final placement and style. Default order/lag .3 are *(default taken)*. |
| AN-2 | Reverse unwrites the last-entering part first and removes the entire annotation; custom text, arrow geometry, data placement and styles survive reintroduction. |
| AN-3 | Canonical finish; after mapping/frame changes `.text` is at c2p(4,6), `.arrow` ends at c2p(2,3), with the old binding updaters intact. |
| AN-4 | An `arrow=False` annotation writes only its custom text and keeps `.arrow is None`; no placeholder arrow is required *(default taken)*. |

## CH — crosshairs

| ID | Row |
|---|---|
| CH-1 | `RevealCrosshair` fades `.dot`, extends `.vline`/`.hline` outward from the **current** intersection, then fades `.readout`. These three equal stages and lag .15 are *(default taken)*. With zero lag and x tracker 1→4, y=3, at time p the vertical interval is `[3+p*(-4-3), 3+p*(12-3)]`, at that frame's tracked x. The dot is at c2p(x,3); final readout is `(4.00, 3.00)`. Replaced glyphs outside live scene families have no points (LB-1). |
| CH-2 | Reverse hides readout, retracts lines, hides dot, and removes the whole crosshair; bound values/styles survive reintroduction. |
| CH-3 | Canonical finish; dot follows c2p(2,3) and the complete vertical line still spans the updated viewport. |
| CH-4 | `readout=False` has no readout stage/object, still reveals the intersection, and keeps `.readout is None` *(default taken)*. |

## LE — legends

| ID | Row |
|---|---|
| LE-1 | `RevealLegend` draws each `entries[i].handle` and writes its `.label` together, entries in retained order, lag .15 *(default taken)*. With two entries and lag=1 only entry 0 has ink at t=1/6. An optional `.frame` is drawn once alongside the entry schedule *(default taken)*. No unsupplied artist animation is inferred; the linked artist's points/style remain unchanged. |
| LE-2 | Reverse unwrites entries in reverse schedule and erases the optional frame, removes the legend, and reintroduces it with original entries/styles/layout. |
| LE-3 | Canonical finish restores entries/frame exactly; changes of an artist's axes do not move the scene-positioned legend or replace its linked artist. |
| LE-4 | An empty legend is a safe empty reveal. Supplied `artist_animations` play with their corresponding entries: an explicit native shift by c2p(0,2)−c2p(0,0) on a line from (0,1) to (1,2) gives y=[2,3] halfway and [3,4] at finish; the legend does not silently replace or discard that animation. |

## CB — colorbars

| ID | Row |
|---|---|
| CB-1 | `FillColorbar` has two equal-duration stages: the strip, then `.axis` ticks/numbers/title. Stage overlap is Manim's `lag_ratio` (default 0); with lag=1 the stages are sequential *(default taken)*. Strip progress p gives cell k opacity `canonical_opacity * clip(64*p-k,0,1)` *(default taken)*. At raw t=1/6 strip progress=1/3: cells 0–20 full, cell 21 at 1/3, cells 22–63 hidden, ticks hidden. Log [1,1000] cell bottoms are `1000**(k/64)`; colours and seam-preventing overlap are unchanged at finish. |
| CB-2 | Reverse removes numbers/ticks/title before emptying the strip top-to-bottom when sequential, removes the bar, and reintroduces the same bar with mapping and styles intact. |
| CB-3 | Canonical finish; log [1,100] cell bottoms remain `100**(k/64)`, the strip follows the shifted parent's centre, and the bar's existing updater remains. |
| CB-4 | A colorbar beside `ThreeDAxes` remains registered as fixed in frame in a real `ThreeDScene` after `FillColorbar`; this 2D decoration reveal must not change its camera registration. |
| CB-5 | FillColorbar remains live while its mappable changes: heatmap values [1,3]→[2,6] give colorbar limits `[1+t,3+3*t]` on every linear frame, and strip cell 16's bottom is `1+t+(2+2*t)/4`. End limits are [2,6]. Cairo caching is enabled; all affected bar leaves are declared moving before static-frame compilation (F-915), and replaced number glyphs outside the scene retain no points (LB-1). |

## BA — staged axes

| ID | Row |
|---|---|
| BA-1 | `BuildAxes(stages=...)` accepts an ordered sequence of stage names; `("ticks","lines")` with lag=1 shows ticks and no line at t=1/6. An unknown name raises `ValueError` mentioning stage before changing any part. Omitted parts are untouched and final geometry/style is restored *(default taken)*. |
| BA-2 | Reverse unwinds the configured stages, removes the system family, and can reintroduce the same axes without discarding its registered artists or styles. |
| BA-3 | Canonical finish and later range/frame changes re-derive the axes: x-line endpoints equal c2p(current x limits, 0); no animation updater remains. `stages=None` preserves task 34's four groups: lines+tips, ticks, numbers, labels+grid. |
| BA-4 | Names are `lines`, `tips`, `ticks`, `minor_ticks`, `numbers`, `labels`, `grid`, `panes`, `breaks`; a nested tuple groups simultaneous names into one stage. Missing/empty parts are harmless. `stage_animations={name: factory}` chooses the animation for that named part group, passing its actual addressable parts once; default strokes use Create, numbers use fades, labels/grid/panes use fades, as in task 34 *(default taken)*. Test the complete vocabulary on axes without optional parts and a custom ticks factory receiving `ax.x.ticks.at(1)`. |
| BA-5 | Optional names select the real parts, not empty stand-ins: populated tips, minor ticks, numbers (explicitly added first), custom Text labels, major grid and broken-axis marks are each revealed before `lines` in sequential two-stage tests. The later line stage is hidden at t=1/6; every part is restored after play. |

## LC — shared observable contracts and edge cases

| ID | Row |
|---|---|
| LC-1 | All eleven entrances support the independent flags: `reverse=True, remover=False` leaves the canonical artist in scene; `reverse=False, remover=True` removes it after the forward reveal without destroying its geometry/style. Tests inspect scene membership and the target, never `_base`. |
| LC-2 | A non-monotone rate function does not accumulate: GrowRegion with `there_and_back` has equal data geometry at t=1/6 and 5/6, likewise 2/6 and 4/6, then restores the full canonical region at finish. |
| LC-3 | SweepRegion can run beside `ax.animate.set_x_range`; every observed frame has data cutoff `4*t` for x=[0,4] under the **current** mapping. No stale cached scene coordinates. |
| LC-4 | GrowRegion/SweepRegion retain crossings, signed areas and masked disconnected lobes; with samples x=0…4, top=[4,-1,5,-1,4], second=2 and where=[T,T,F,T,T], no subpath bridges (1,3). An all-false mask is a safe empty entrance and stays empty. These are the existing helper's retained boundaries, not a new interpretation of matplotlib's mask rules. |
| LC-5 | Every name in the signature block is a Manim Animation subclass exported as the identical class from `manim_plots`, `manim_plots.animations` and its declared family module. No new un/reverse class names. |
| LC-6 | At partial frames 1/6…5/6, reverse reference/region-sweep/Riemann geometry equals the independently computed data geometry for the whole schedule at `1-t`; with lag, later rectangles leave before earlier ones. |
| LC-7 | GrowRegion accepts `axis=None` for inference and explicit `"x"`/`"y"` overrides. Any other axis, sweep direction outside ±1, and a generic Polygon without paired boundaries fail before mutations (`ValueError` for option values, `TypeError` for a wrong target) *(default taken for error types)*. |
| LC-8 | Log axes still interpolate **data**, not transformed coordinates: growing first=81 from second=1 at .5 reaches 41, not 9, under y log [1,100]. No implicit zero baseline is introduced. |
| LC-9 | GrowRegion, SweepRegion and GrowRiemann do not resample their own unchanged graph function every frame (F-918): after canonical geometry is warm at the probe resolution, f(x)=x+2 over [0,2] has an unchanged call counter across the entrance. The retained graph and revealed artist are both in the scene. |

## MV — moving-object detection and sampling

| ID | Row |
|---|---|
| MV-1 | BuildAxes, FillColorbar and RevealLegend with an explicit linked artist animation declare all affected drawable parts before Cairo compiles its static background (F-915). `artist_animations` is an optional sequence paired by entry index *(default taken)*; supplied native animations are honored and their moving involvement propagates. In real scene `begin_animations` with caching enabled, affected leaves are moving; an earlier unrelated still axes/function plot remains static, and its function sample counter does not increase (F-918). No global activation. The dry run exercises Cairo's classification/static-frame path without writing a film. |

## Customisation, boundaries and review notes

Origins use `ExtendReference.origin`; region orientation is inferred when `axis=None`
and overridden by explicit `axis`; sweep travel
uses `direction`; per-part and stage overlap use `lag_ratio`; cap timing uses
`cap_lag`; annotation order uses `text_first`; axes order/grouping uses `stages`
and native factories use `stage_animations`. Legend/rectangle/error sample order
is retained data/container order; `reverse` unwinds that order, it never sorts data
*(default taken)*. Existing `.arrow/.text`, `.vline/.hline/.dot/.readout`, indexed
rectangles, error named parts, legend entries/frame, colorbar strip/axis and axis
decoration groups remain directly styleable; no copying styles back from a newly
constructed default artist.

Out of task: RefineRiemann (task 44), 3D error growth, inset entrances (task 43),
and `_base` ownership mechanics (task 40). The maintainer alone can veto the
default choices above, especially the spellings/grouping of stages, cap-lag
meaning and the two-stage strip
opacity schedule. No unanswered decision blocks these draft tests.

Every listed row has executable tests in `tests/animations/test_helpers_decorations.py`;
behavior beyond those rows (notably rendered visual quality and the complete
supported Python/Manim matrix) is left to Claude's implementation review/gate.
