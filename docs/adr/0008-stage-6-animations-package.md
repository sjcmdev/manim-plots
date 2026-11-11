# ADR 0008 — Stage 6: an animation package, an entrance and an exit for every artist

- **Status:** Accepted, 2026-10-31, by the maintainer. The request: "dobrze by też było
  dodać animacje dla pozostałych rzeczy, takie np. 2d helpers, praktycznie do wszystkiego,
  takie dodające jak i usuwające. Ale to poprzez dziedziczenie klas po Animation albo
  LaggedStart. I tak tutaj chyba sensownie zrobić cały osobny podmoduł." The answer to the
  proposal below: "Tak, wszystko co wymyśliłeś wchodzi." Items marked *(default taken)*
  were not asked and stand unless vetoed.
- **Builds on:** ADR 0007 (stage 5, tasks 31-39, all merged); task 34's animations and
  its LB-1 and AP-3 rows; F-915 (moving-object detection) and F-918 (per-frame sampling).
- **Amends:** `docs/scope.md` F-9xx: each task adds or amends its rows in place, marked
  *(ADR 0008)*.

## Context

Stage 5 left animations for bars, data changes and axes, and a few older ones
(`TraceCurve`, `ShowPoints`, `Morph`, `DrawAxes`, `Flow`, `GrowSurface`). Most artists
have none of their own: Manim's `Create`, `FadeIn` and `Write` work on them, but they do
not know what the artist means — an area that grows from its baseline, a box that opens
from its median, a pie swept by angle. Removal is uneven: `ShrinkBars` exists, nothing
else has an exit. A brainstorm with Codex (read-only, 2026-10-31) listed what each family
lacks; the maintainer took all of it into the release.

## Decision

### 1. One package

`manim_plots.animations` holds every animation of the library, one module per family
(`curves`, `helpers`, `axes`, `decorations`, `bars`, `fields`, `statistics`, `surfaces`,
`volumes`) and an internal `_base`. A module is created when its first animation arrives.
The existing animations move there with their names, signatures and behaviour unchanged;
the old import paths (`manim_plots.X`, `manim_plots.mobjects.animations.X`, `Flow` from
`mobjects.fields`, `GrowSurface` from `mobjects.surfaces`) keep working and give the same
class object. Every new name is exported from the package and the top level.

### 2. Classes of Manim's kinds

Every animation is an `Animation` subclass, or a `LaggedStart` / `AnimationGroup` subclass
when it is a small composition of parts that Manim's own animations already draw (an
annotation's arrow then its text). An animation over many parts (thousands of cells,
arrows or faces) is one `Animation` driving all parts with the per-part windows of
`GrowBars` (task 34 GR-1), not thousands of child animations. Two internal building
blocks in `_base`: an animation that applies an eased fraction to a temporary
presentation state and restores the canonical state at the end, and the per-part window
helper. Nothing more general (no adapter registry) until a structure repeats.

### 3. Entrance and exit by flags, not by pairs of classes

Every introducing animation takes `reverse=False` and `remover=None`. `reverse=True`
plays the entrance backwards — the last part in leaves first — and implies
`remover=True` unless `remover` is given, as Manim's `Uncreate` is `Create` reversed and
a remover *(default taken)*. A composition played in reverse uses `Uncreate`, `Unwrite`
and `FadeOut` children, not its introducers run backwards. `ShrinkBars` stays; two thin
aliases are added because the names read well: `ShrinkSurface` (`GrowSurface`
reversed) and `CloseInset` (`OpenInset` reversed). No other `Un…` classes.

Data changes (`RefineRiemann`, `RebinHistogram`, `SweepIsovalue`, `SweepSlice`,
`ExplodePie`) have inverse transitions — to the previous partition, edges, level or
position — not removers. `AppendData` gets no reverse.

Removing an artist from the scene does not unregister it from its axes: played again, it
comes back with its data and styles.

### 4. The lifecycle contract, for every animation

- **Canonical finish:** an entrance ends with the artist equal to its bound self; a
  later range, frame or tracker change re-derives it. An emphasis restores the exact
  styles and placement it found. A data change commits its target data.
- **No updater left** that the animation added; the artist's own binding updaters stay.
- **F-915:** the animation declares every system and binding it changes before the
  static background is compiled (task 34's `AppendData(autoscale=True)` fix is the
  model); an unrelated still plot stays static.
- **F-918:** no new per-frame sampling of functions that do not change.
- **LB-1:** text rebuilt during a play leaves no drawable glyph outside the scene.
- **Rate functions:** a non-monotone one (`there_and_back`) gives the same frame for
  the same alpha; it never accumulates.
- **Concurrent writers:** a reveal runs beside `ax.animate.set_x_range(…)` and uses that
  frame's mapping; two animations writing the same data parameter fail with a clear
  error.
- **Invalid explicit origins** (a baseline outside a log scale's domain, an unknown
  stage name) are rejected before anything changes.

### 5. What joins the release

All of the brainstorm's list, its *must*, *should* and *could* tiers:

- **Existing animations:** `reverse` and `remover` on `TraceCurve`, `ShowPoints`,
  `DrawAxes`, `BuildAxes`, `GrowBars`, `GrowSurface`; `TraceCurve` paced by the curve's
  parameter (a spiral traced by angle) as well as by arc length; `ShowPoints` in an
  order (data, x, y, value or a key) and with a pop.
- **2D helpers and decorations:** `ExtendReference` (reference and drop lines grow
  from an end), `GrowRegion` (a filled region grows from its paired boundary),
  `SweepRegion` (a region revealed along x or y), `SweepSpan`, `GrowRiemann`,
  `GrowErrorBars`, `RevealAnnotation`, `RevealCrosshair`, `RevealLegend`,
  `FillColorbar`, `BuildAxes(stages=…)`.
- **Chart families:** `GrowBars(order=…)`, `GrowStack`, `RevealCells`,
  `RevealContours`, `SweepPie`, `ExplodePie`, `GrowBoxPlot` (from the median),
  `UnfoldViolin` (from the centre line).
- **Spatial construction:** `GrowField`, `GrowStems`, `RevealWireframe`,
  `RevealWaterfall`, `SweepSurface`, `SweepPolar`, `OpenInset` / `CloseInset`.
- **Topology-changing transitions:** `RefineRiemann`, `RebinHistogram`,
  `StackVoxels`, `SweepIsovalue`, `SweepSlice`.

Rejected: animations for single ticks, numbers or grid lines (Manim's `Create`, `Write`
and `FadeIn` draw them, and `BuildAxes(stages=…)` orders them); `SlideTangent`,
`FollowCrosshair` and an end-label animation (animating the tracker the helper is bound
to does it); a generic morph between any two artists. The documentation shows the native
recipes for these.

### 6. Tasks

- **40 — the package and the reversible lifecycle.** The move, the compatible exports,
  `_base`, the §4 contract as tests over the existing animations, `reverse`/`remover`,
  `ShrinkSurface`, `TraceCurve` pacing, `ShowPoints` order and pop, the native recipes
  in the documentation.
- **41 — 2D helpers and decorations.**
- **42 — chart families.**
- **43 — spatial construction.**
- **44 — topology-changing transitions.**
- **23 — the release**, last.

40 comes first; 41-44 build on its `_base` and may run beside each other.

**Process** *(default taken, from the maintainer's "mocniej utylizujmy codex")*: Codex
drafts each acceptance table and its tests from this ADR in one session, and implements
it in another; Claude reviews the table and the oracles before any code, then renders,
runs the full gate and merges. An implementer that finds a test contradicting its row
says so; the oracle is checked first.

## Consequences

- The release moves back by tasks 40-44; its frozen API grows by about thirty names and
  two aliases.
- `manim_plots.mobjects.animations` becomes a compatibility module; the layer rules in
  `tests/test_layers.py` gain the new package.
- F-1001 must still pass: no animation may add cost to a system that does not use it.
